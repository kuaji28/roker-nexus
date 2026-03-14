"""
ROKER NEXUS — Bot de Telegram
Comandos de consulta, alertas automáticas y actualizaciones de configuración.
Ejecutar como proceso separado: python telegram_bot.py
"""
import asyncio
import logging
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, MONEDA_USD_ARS
from database import (
    get_quiebres, get_lista_negra,
    agregar_a_lista_negra, quitar_de_lista_negra,
    query_to_df, execute_query, init_db
)
from utils.helpers import fmt_usd, fmt_num, color_stock
from modules.inventario import detectar_quiebre_entre_depositos

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
import functools

# ── Seguridad: solo responde al chat autorizado ───────────────
def autorizado(update: Update) -> bool:
    return str(update.effective_chat.id) == str(TELEGRAM_CHAT_ID)


def auth_required(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not autorizado(update):
            await update.message.reply_text("⛔ No autorizado.")
            return
        await func(update, context)
    return wrapper


# ── /start ────────────────────────────────────────────────────
@auth_required
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _enviar_menu_principal(update.message)


async def _enviar_menu_principal(msg, edit=False):
    """Envía o edita el menú principal con botones."""
    nombre = msg.chat.first_name if hasattr(msg.chat, 'first_name') and msg.chat.first_name else "Sergio"
    texto = (
        f"⚡ *ROKER NEXUS*\n"
        f"Hola {nombre}, ¿qué necesitás?\n\n"
        f"_Podés tocar un botón o escribir directamente._"
    )
    keyboard = [
        [
            InlineKeyboardButton("📦 Stock",       callback_data="menu_stock"),
            InlineKeyboardButton("💰 Precio",      callback_data="menu_precio"),
        ],
        [
            InlineKeyboardButton("🔴 Quiebres",    callback_data="menu_quiebres"),
            InlineKeyboardButton("🚚 Tránsito",    callback_data="menu_transito"),
        ],
        [
            InlineKeyboardButton("⛔ Lista negra", callback_data="menu_negra"),
            InlineKeyboardButton("📊 Resumen",     callback_data="menu_resumen"),
        ],
        [
            InlineKeyboardButton("💵 Tipo de cambio", callback_data="menu_dolar"),
            InlineKeyboardButton("🤖 Preguntarle a IA", callback_data="menu_ia"),
        ],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await msg.edit_text(texto, parse_mode="Markdown", reply_markup=markup)
    else:
        await msg.reply_text(texto, parse_mode="Markdown", reply_markup=markup)


# ── /stock ────────────────────────────────────────────────────
@auth_required
async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        # Sin argumento: elegir depósito para ver resumen
        keyboard = [
            [
                InlineKeyboardButton("🏭 San José", callback_data="stock_dep_SAN_JOSE"),
                InlineKeyboardButton("🏪 Larrea", callback_data="stock_dep_LARREA"),
            ],
            [InlineKeyboardButton("📊 Todos los depósitos", callback_data="stock_dep_TODOS")],
        ]
        await update.message.reply_text(
            "📦 *¿Qué depósito querés ver?*\n\n"
            "O buscá un artículo por código o descripción:\n"
            "`/stock samsung a15` o `/stock SM-A156`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    query = " ".join(args).strip()
    await _buscar_y_mostrar_stock(update.message, query, context)


async def _buscar_articulos(query: str) -> list:
    """Busca artículos por código exacto o descripción parcial. Retorna lista de (codigo, descripcion, marca)."""
    import sqlite3 as _sq
    conn = _sq.connect("roker_nexus.db")
    q = query.upper()
    # Primero intenta código exacto
    cur = conn.execute(
        "SELECT codigo, descripcion, marca FROM articulos WHERE UPPER(codigo)=? LIMIT 1", (q,)
    )
    row = cur.fetchone()
    if row:
        conn.close()
        return [row]
    # Búsqueda por descripción o marca
    palabras = q.split()
    like = "%" + "%".join(palabras) + "%"
    cur = conn.execute(
        "SELECT codigo, descripcion, marca FROM articulos WHERE UPPER(descripcion) LIKE ? OR UPPER(marca) LIKE ? ORDER BY descripcion LIMIT 10",
        (like, like)
    )
    rows = cur.fetchall()
    # Si no encontró, buscar palabras sueltas
    if not rows:
        cur = conn.execute(
            "SELECT codigo, descripcion, marca FROM articulos WHERE " +
            " AND ".join(["UPPER(descripcion) LIKE ?" for _ in palabras]),
            ["%" + p + "%" for p in palabras]
        )
        rows = cur.fetchall()
    conn.close()
    return rows


async def _buscar_y_mostrar_stock(message, query: str, context):
    """Busca artículos y muestra stock o lista de coincidencias."""
    resultados = await _buscar_articulos(query)

    if not resultados:
        await message.reply_text(
            f"❓ No encontré artículos con *{query}*.\n\nIntentá con otro código o descripción.",
            parse_mode="Markdown"
        )
        return

    if len(resultados) == 1:
        await _mostrar_stock_codigo(message, resultados[0][0])
        return

    # Múltiples resultados → mostrar botones para elegir
    lineas = [f"🔍 Encontré *{len(resultados)}* artículos. ¿Cuál es?\n"]
    keyboard = []
    for codigo, desc, marca in resultados:
        label = f"{desc[:30]} ({marca or '?'})"
        lineas.append(f"`{codigo}` — {desc[:40]}")
        keyboard.append([InlineKeyboardButton(f"{codigo} — {desc[:35]}", callback_data=f"stock_cod_{codigo}")])

    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
    await message.reply_text(
        "\n".join(lineas),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _mostrar_stock_codigo(message, codigo: str):
    """Muestra stock de un código específico en todos los depósitos."""
    import sqlite3 as _sq
    conn = _sq.connect("roker_nexus.db")
    cur = conn.execute("""
        SELECT s.deposito, s.stock, s.stock_minimo
        FROM stock_snapshots s
        JOIN (
            SELECT deposito, MAX(fecha) as mf FROM stock_snapshots
            WHERE codigo=? GROUP BY deposito
        ) lx ON s.deposito=lx.deposito AND s.fecha=lx.mf
        WHERE s.codigo=?
        ORDER BY CASE s.deposito
            WHEN 'SAN_JOSE' THEN 1
            WHEN 'LARREA' THEN 2
            ELSE 3 END
    """, (codigo, codigo))
    rows = cur.fetchall()
    cur2 = conn.execute("SELECT descripcion, marca FROM articulos WHERE codigo=?", (codigo,))
    art = cur2.fetchone()
    conn.close()

    if not rows:
        await message.reply_text(f"❓ Sin datos de stock para `{codigo}`.", parse_mode="Markdown")
        return

    desc = f"{art[0]}" if art else codigo
    marca = f" ({art[1]})" if art and art[1] else ""
    nombres_dep = {"SAN_JOSE": "🏭 San José", "LARREA": "🏪 Larrea", "ES_LOCAL": "🏬 Local"}
    lineas = [f"📦 *{desc}*{marca}\n`{codigo}`\n"]
    for deposito, stock, minimo in rows:
        icono = color_stock(stock, minimo)
        nombre = nombres_dep.get(deposito, deposito)
        lineas.append(f"{icono} *{nombre}*: {int(stock)} uds _(mín: {int(minimo)})_")

    await message.reply_text("\n".join(lineas), parse_mode="Markdown")


# ── /precio ───────────────────────────────────────────────────
@auth_required
async def cmd_precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Buscá por código o descripción:\n`/precio samsung a15` o `/precio SM-A156`",
            parse_mode="Markdown"
        )
        return

    query = " ".join(args).strip()
    resultados = await _buscar_articulos(query)

    if not resultados:
        await update.message.reply_text(f"❓ No encontré artículos con *{query}*.", parse_mode="Markdown")
        return

    if len(resultados) == 1:
        await _mostrar_precio_codigo(update.message, resultados[0][0])
        return

    keyboard = []
    lineas = [f"🔍 *{len(resultados)}* coincidencias. ¿Cuál?\n"]
    for codigo, desc, marca in resultados:
        lineas.append(f"`{codigo}` — {desc[:40]}")
        keyboard.append([InlineKeyboardButton(f"{codigo} — {desc[:35]}", callback_data=f"precio_cod_{codigo}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def _mostrar_precio_codigo(message, codigo: str):
    conn = sqlite3.connect("roker_nexus.db")
    cur = conn.execute("SELECT lista_1, lista_4, moneda FROM precios WHERE codigo=? ORDER BY fecha DESC LIMIT 1", (codigo,))
    row = cur.fetchone()
    cur2 = conn.execute("SELECT descripcion, marca FROM articulos WHERE codigo=?", (codigo,))
    art = cur2.fetchone()
    conn.close()

    if not row:
        await message.reply_text(f"❓ Sin precios para `{codigo}`.", parse_mode="Markdown")
        return

    desc = f"{art[0]}" if art else codigo
    marca = f" ({art[1]})" if art and art[1] else ""
    tasa = _get_tasa()
    l1, l4 = row[0] or 0, row[1] or 0
    texto = (
        f"💰 *{desc}*{marca}\n`{codigo}`\n\n"
        f"📋 Lista 1 (mayorista): *USD {l1:,.2f}* = ${l1*tasa:,.0f} ARS\n"
        f"🛒 Lista 4 (ML): *USD {l4:,.2f}* = ${l4*tasa:,.0f} ARS"
    )
    await message.reply_text(texto, parse_mode="Markdown")


# ── /quiebres ─────────────────────────────────────────────────
@auth_required
async def cmd_quiebres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Top 10", callback_data="quiebres_top_10"),
            InlineKeyboardButton("Top 20", callback_data="quiebres_top_20"),
            InlineKeyboardButton("Top 30", callback_data="quiebres_top_30"),
            InlineKeyboardButton("Top 50", callback_data="quiebres_top_50"),
        ],
        [
            InlineKeyboardButton("🏭 San José", callback_data="quiebres_dep_SAN_JOSE"),
            InlineKeyboardButton("🏪 Larrea", callback_data="quiebres_dep_LARREA"),
            InlineKeyboardButton("📊 Todos", callback_data="quiebres_dep_TODOS"),
        ],
    ]
    await update.message.reply_text(
        "🔴 *Quiebres de stock*\n\n¿Cuántos querés ver y de qué depósito?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _mostrar_quiebres(message, top: int = 10, deposito: str = None):
    df = get_quiebres(deposito=deposito, umbral=0)
    if df.empty:
        await message.reply_text("✅ No hay quiebres de stock en este momento.")
        return
    total = len(df)
    df = df.head(top)
    dep_label = {"SAN_JOSE": "San José", "LARREA": "Larrea", None: "todos los depósitos"}.get(deposito, deposito)
    lineas = [f"🔴 *Top {top} quiebres — {dep_label}* ({total} total)\n"]
    for _, row in df.iterrows():
        desc = (row.get("descripcion") or row.get("codigo", "?"))[:35]
        cod = row.get("codigo", "")
        dep = row.get("deposito", "")
        lineas.append(f"`{cod}` {desc} _({dep})_")
    keyboard = [[InlineKeyboardButton("🤖 Analizar con IA", callback_data="ia_quiebres")]]
    await message.reply_text("\n".join(lineas), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ── /sinstock ─────────────────────────────────────────────────
@auth_required
async def cmd_sinstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = get_quiebres(umbral=0)
    if df.empty:
        await update.message.reply_text("✅ Todo con stock.")
        return

    lineas = [f"🔴 *{len(df)} artículos sin stock*\n"]
    for _, row in df.head(20).iterrows():
        desc = (row.get("descripcion") or row.get("codigo", "?"))[:35]
        lineas.append(f"`{row.get('codigo','')}` {desc}")

    if len(df) > 20:
        lineas.append(f"\n_...y {len(df)-20} más._")

    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


# ── /transito ─────────────────────────────────────────────────
@auth_required
async def cmd_transito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("roker_nexus.db")
    cur = conn.execute("""
        SELECT t.invoice_id, t.proveedor, t.estado, t.total_usd,
               t.fecha_pedido, t.fecha_estimada
        FROM pedidos_transito t ORDER BY t.fecha_pedido DESC LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📭 No hay pedidos en tránsito registrados.")
        return

    lineas = ["🚢 *Pedidos en tránsito*\n"]
    for inv, prov, estado, total, f_ped, f_est in rows:
        lineas.append(
            f"• {inv or '?'} ({prov}) — {estado}\n"
            f"  USD {total:,.0f} · Est: {str(f_est or '?')[:10]}"
        )

    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


# ── /negra ────────────────────────────────────────────────────
@auth_required
async def cmd_negra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        # Sin args: mostrar lista negra actual
        df = get_lista_negra()
        if df.empty:
            await update.message.reply_text(
                "📋 Lista negra vacía.\n\nPara agregar: `/negra samsung a05`",
                parse_mode="Markdown"
            )
            return
        lineas = [f"⛔ *Lista negra — {len(df)} artículos*\n"]
        for _, row in df.iterrows():
            motivo = f" _{row.get('motivo','')}_" if row.get('motivo') else ""
            lineas.append(f"`{row['codigo']}` {row.get('descripcion','')[:35]}{motivo}")
        await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")
        return

    query = " ".join(args).strip()
    resultados = await _buscar_articulos(query)

    if not resultados:
        await update.message.reply_text(
            f"❓ No encontré artículos con *{query}*.\nVerificá el código o la descripción.",
            parse_mode="Markdown"
        )
        return

    if len(resultados) == 1:
        codigo, desc, marca = resultados[0]
        marca_str = f" ({marca})" if marca else ""
        keyboard = [[
            InlineKeyboardButton(f"⛔ Sí, bloquear", callback_data=f"negra_ok_{codigo}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar"),
        ]]
        await update.message.reply_text(
            f"¿Agregar a lista negra?\n\n"
            f"📦 *{desc}*{marca_str}\n`{codigo}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Múltiples coincidencias
    lineas = [f"🔍 Encontré *{len(resultados)}* artículos. ¿Cuál querés bloquear?\n"]
    keyboard = []
    for codigo, desc, marca in resultados:
        marca_str = f" ({marca})" if marca else ""
        lineas.append(f"`{codigo}` — {desc[:40]}{marca_str}")
        keyboard.append([InlineKeyboardButton(
            f"⛔ {codigo} — {desc[:30]}",
            callback_data=f"negra_ok_{codigo}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
    await update.message.reply_text(
        "\n".join(lineas),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ── Estado de conversación por usuario ───────────────────────
# Guarda qué está esperando el bot de cada usuario
# { user_id: { "esperando": "tasa_usd" | "umbral" | "stock_buscar" | ... } }
_estado_usuario: dict = {}

def _set_estado(user_id: int, clave: str, extra: dict = None):
    _estado_usuario[user_id] = {"esperando": clave, **(extra or {})}

def _get_estado(user_id: int) -> dict:
    return _estado_usuario.get(user_id, {})

def _clear_estado(user_id: int):
    _estado_usuario.pop(user_id, None)


# ── /menu — panel rápido con botones ─────────────────────────
@auth_required
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Ver quiebres", callback_data="menu_quiebres"),
         InlineKeyboardButton("📦 Stock rápido", callback_data="menu_stock")],
        [InlineKeyboardButton("💵 Cambiar dólar", callback_data="menu_dolar"),
         InlineKeyboardButton("💱 Cambiar RMB", callback_data="menu_rmb")],
        [InlineKeyboardButton("⚡ Resumen del día", callback_data="menu_resumen"),
         InlineKeyboardButton("🔴 Lista negra", callback_data="menu_negra")],
        [InlineKeyboardButton("🛒 Pedidos en tránsito", callback_data="menu_transito")],
    ]
    await update.message.reply_text(
        "⚡ *Roker Nexus* — ¿Qué necesitás?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ── /config — interactivo con botones ────────────────────────
@auth_required
async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Si viene con args directos, modo clásico
    args = context.args
    if len(args) >= 2:
        clave = args[0].lower()
        try:
            valor = float(args[1])
        except ValueError:
            await update.message.reply_text("El valor debe ser un número.")
            return
        await _guardar_config(update.message, clave, valor)
        return

    # Sin args → mostrar botones
    keyboard = [
        [InlineKeyboardButton("💵 Tipo de cambio USD", callback_data="cfg_tasa_usd")],
        [InlineKeyboardButton("🟡 Umbral de quiebre", callback_data="cfg_umbral")],
        [InlineKeyboardButton("📦 Tope lote 1 (USD)", callback_data="cfg_tope_lote1")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")],
    ]
    await update.message.reply_text(
        "⚙️ *Configuración* — ¿Qué querés cambiar?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _guardar_config(message, clave: str, valor: float):
    """Guarda un valor de configuración y confirma."""
    if clave == "tasa_usd":
        conn = sqlite3.connect("roker_nexus.db")
        conn.execute(
            "INSERT OR REPLACE INTO tasas_cambio (fecha, usd_ars) VALUES (date('now'), ?)",
            (valor,)
        )
        conn.commit()
        conn.close()
        await message.reply_text(
            f"✅ *Dólar actualizado*\n💵 USD/ARS = *${valor:,.0f}*",
            parse_mode="Markdown"
        )
    elif clave == "umbral":
        await message.reply_text(
            f"✅ *Umbral de quiebre actualizado*\n🟡 Stock mínimo = *{int(valor)} unidades*",
            parse_mode="Markdown"
        )
    elif clave == "tope_lote1":
        await message.reply_text(
            f"✅ *Tope Lote 1 actualizado*\n📦 Tope = *USD {valor:,.0f}*",
            parse_mode="Markdown"
        )
    elif clave == "rmb":
        await message.reply_text(
            f"✅ *Yuan actualizado*\n💱 RMB/ARS = *${valor:,.2f}*",
            parse_mode="Markdown"
        )


# ── /resumen ──────────────────────────────────────────────────
@auth_required
async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_resumen_stats
    stats = get_resumen_stats()

    texto = (
        f"⚡ *Roker Nexus — Resumen*\n"
        f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n"
        f"📦 Artículos activos: *{stats.get('total_articulos',0):,}*\n"
        f"🔴 Sin stock: *{stats.get('sin_stock',0)}*\n"
        f"🟡 Bajo mínimo: *{stats.get('bajo_minimo',0)}*\n"
        f"🕐 Última importación: {stats.get('ultima_importacion','—')}\n"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


# ── /ia ───────────────────────────────────────────────────────
@auth_required
async def cmd_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = " ".join(context.args) if context.args else ""
    if not consulta:
        await update.message.reply_text("Uso: /ia [tu pregunta]\nEj: /ia ¿qué artículos Samsung están en quiebre?")
        return

    await update.message.reply_text("🤖 Consultando a Claude...")
    from modules.ia_engine import motor_ia
    respuesta = motor_ia.consultar(consulta)
    await update.message.reply_text(respuesta[:4000])  # Telegram max


# ── Callbacks de botones ──────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ── Cancelar ──
    if data == "cancelar":
        _clear_estado(user_id)
        await query.message.edit_text("❌ Cancelado.")

    # ── MENÚ PRINCIPAL ──
    elif data == "menu_quiebres":
        keyboard = [[
            InlineKeyboardButton("🏭 San José", callback_data="quiebres_dep_SAN_JOSE"),
            InlineKeyboardButton("🏪 Larrea",   callback_data="quiebres_dep_LARREA"),
            InlineKeyboardButton("📋 Todos",    callback_data="quiebres_dep_TODOS"),
        ], [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
        await query.message.edit_text("📊 *Quiebres* — ¿Qué depósito?", parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "menu_stock":
        _set_estado(user_id, "buscar_stock")
        await query.message.edit_text("📦 *Buscar stock*\n\nEscribí el nombre o código del artículo:",
                                       parse_mode="Markdown")

    elif data == "menu_dolar":
        _set_estado(user_id, "tasa_usd")
        try:
            import sqlite3 as _sq2
            conn2 = _sq2.connect("roker_nexus.db")
            cur2 = conn2.execute("SELECT usd_ars FROM tasas_cambio ORDER BY fecha DESC LIMIT 1")
            row2 = cur2.fetchone(); conn2.close()
            actual = f"${row2[0]:,.0f}" if row2 else "no registrado"
        except Exception:
            actual = "no registrado"
        kb = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
        try:
            await query.message.edit_text(
                f"💵 *Tipo de cambio USD*\nValor actual: *{actual}*\n\nEscribí el nuevo valor:",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception:
            await query.message.reply_text(
                f"💵 *Tipo de cambio USD*\nValor actual: *{actual}*\n\nEscribí el nuevo valor:",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
            )

    elif data == "menu_rmb":
        _set_estado(user_id, "rmb")
        await query.message.edit_text(
            "💱 *Tipo de cambio RMB (Yuan)*\n\nEscribí el nuevo valor en ARS:",
            parse_mode="Markdown"
        )

    elif data == "menu_resumen":
        from database import get_resumen_stats
        stats = get_resumen_stats()
        texto = (
            f"⚡ *Roker Nexus — Resumen*\n"
            f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n"
            f"📦 Artículos activos: *{stats.get('total_articulos',0):,}*\n"
            f"🔴 Sin stock: *{stats.get('sin_stock',0)}*\n"
            f"🟡 Bajo mínimo: *{stats.get('bajo_minimo',0)}*\n"
            f"🕐 Última importación: {stats.get('ultima_importacion','—')}\n"
        )
        keyboard = [[InlineKeyboardButton("🔄 Actualizar", callback_data="menu_resumen"),
                     InlineKeyboardButton("🔙 Menú", callback_data="menu_volver")]]
        await query.message.edit_text(texto, parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "menu_negra":
        from database import get_lista_negra
        lista = get_lista_negra()
        kb = [
            [InlineKeyboardButton("➕ Agregar artículo", callback_data="negra_buscar")],
            [InlineKeyboardButton("🔙 Menú", callback_data="menu_volver")],
        ]
        if not lista:
            texto_n = "⛔ *Lista negra* — Está vacía.\n\n_Agregá artículos para excluirlos de compras._"
        else:
            lineas = [f"⛔ *Lista negra* — {len(lista)} artículos:\n"]
            for cod, desc in lista[:20]:
                lineas.append(f"• `{cod}` — {desc or 'sin descripción'}")
            if len(lista) > 20:
                lineas.append(f"\n_...y {len(lista)-20} más_")
            texto_n = "\n".join(lineas)
        try:
            await query.message.edit_text(texto_n, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(kb))
        except Exception:
            await query.message.reply_text(texto_n, parse_mode="Markdown",
                                           reply_markup=InlineKeyboardMarkup(kb))

    elif data == "menu_transito":
        await query.message.edit_text("🔄 Consultando tránsito...")
        # reusar lógica de cmd_transito
        import sqlite3 as _sq
        conn = _sq.connect("roker_nexus.db")
        cur = conn.execute("""
            SELECT p.codigo, a.descripcion, p.cantidad, p.proveedor, p.fecha_estimada
            FROM pedidos_transito p
            LEFT JOIN articulos a ON p.codigo=a.codigo
            WHERE p.estado='en_transito'
            ORDER BY p.fecha_estimada LIMIT 20
        """)
        rows = cur.fetchall(); conn.close()
        if not rows:
            await query.message.edit_text("🚚 Sin pedidos en tránsito al momento.")
        else:
            lineas = ["🚚 *Pedidos en tránsito:*\n"]
            for cod, desc, cant, prov, fecha in rows:
                lineas.append(f"• `{cod}` {desc or ''}\n  {int(cant)} uds | {prov or '?'} | eta {fecha or '?'}")
            await query.message.edit_text("\n".join(lineas), parse_mode="Markdown")

    # ── Rastrear pedido/tránsito ──
    elif data.startswith("pedido_cod_"):
        cod = data.replace("pedido_cod_", "")
        resultados = await _buscar_articulos(cod)
        desc = resultados[0][1] if resultados else cod
        await _mostrar_pedido_codigo(query.message, cod, desc or "")

    # ── Opciones de un artículo específico (desde lista múltiple) ──
    elif data.startswith("art_opciones_"):
        cod = data.replace("art_opciones_", "")
        resultados = await _buscar_articulos(cod)
        desc = resultados[0][1] if resultados else cod
        keyboard = [
            [
                InlineKeyboardButton("📦 Ver stock",      callback_data=f"stock_cod_{cod}"),
                InlineKeyboardButton("💰 Ver precio",     callback_data=f"precio_cod_{cod}"),
            ],
            [
                InlineKeyboardButton("📦 Stock San José", callback_data=f"stock_dep_{cod}_SAN_JOSE"),
                InlineKeyboardButton("📦 Stock Larrea",   callback_data=f"stock_dep_{cod}_LARREA"),
            ],
            [
                InlineKeyboardButton("⛔ Lista negra",    callback_data=f"negra_add_{cod}"),
                InlineKeyboardButton("🔙 Volver",         callback_data="menu_volver"),
            ],
        ]
        await query.message.edit_text(
            f"📱 *{desc}*\n`{cod}`\n\n¿Qué querés saber?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── Stock de un depósito específico ──
    elif data.startswith("stock_dep_"):
        partes = data.replace("stock_dep_", "").rsplit("_", 1)
        if len(partes) == 2:
            cod, dep = partes[0], partes[1]
            dep_real = dep.replace("_", " ")
        else:
            cod, dep_real = partes[0], "TODOS"
        texto_resp = _stock_texto(cod, dep_real if dep_real != "TODOS" else None)
        keyboard = [
            [
                InlineKeyboardButton("💰 Ver precio", callback_data=f"precio_cod_{cod}"),
                InlineKeyboardButton("🔙 Menú",       callback_data="menu_volver"),
            ]
        ]
        await query.message.edit_text(texto_resp, parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    # ── Menu precio ──
    elif data == "menu_precio":
        _set_estado(query.from_user.id, "buscar_precio")
        await query.message.edit_text(
            "💰 *Buscar precio*\n\nEscribí el nombre o código del artículo:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]])
        )

    # ── Menu IA ──
    elif data == "menu_ia":
        _set_estado(query.from_user.id, "ia_consulta")
        await query.message.edit_text(
            "🤖 *Asistente IA*\n\nEscribí tu consulta y Claude te responde:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]])
        )

    elif data == "menu_volver":
        await _enviar_menu_principal(query.message, edit=True)

    # ── CONFIG desde botones ──
    elif data == "cfg_tasa_usd":
        _set_estado(user_id, "tasa_usd")
        conn = sqlite3.connect("roker_nexus.db")
        cur = conn.execute("SELECT usd_ars FROM tasas_cambio ORDER BY fecha DESC LIMIT 1")
        row = cur.fetchone(); conn.close()
        actual = f"${row[0]:,.0f}" if row else "no registrado"
        await query.message.edit_text(
            f"💵 *Tipo de cambio USD*\nValor actual: *{actual}*\n\nEscribí el nuevo valor:",
            parse_mode="Markdown"
        )

    elif data == "cfg_umbral":
        _set_estado(user_id, "umbral")
        await query.message.edit_text(
            "🟡 *Umbral de quiebre*\n\nEscribí la cantidad mínima de stock (ej: 10):",
            parse_mode="Markdown"
        )

    elif data == "cfg_tope_lote1":
        _set_estado(user_id, "tope_lote1")
        await query.message.edit_text(
            "📦 *Tope Lote 1*\n\nEscribí el nuevo tope en USD (ej: 5000):",
            parse_mode="Markdown"
        )

    # ── Stock: selección de depósito para resumen ──
    elif data.startswith("stock_dep_"):
        deposito = data.replace("stock_dep_", "")
        import sqlite3 as _sq
        conn = _sq.connect("roker_nexus.db")
        if deposito == "TODOS":
            cur = conn.execute("""
                SELECT s.deposito,
                       COUNT(*) as total,
                       SUM(CASE WHEN s.stock=0 THEN 1 ELSE 0 END) as sin_stock,
                       SUM(CASE WHEN s.stock>0 AND s.stock<s.stock_minimo THEN 1 ELSE 0 END) as bajo_min
                FROM stock_snapshots s
                JOIN (SELECT codigo, deposito, MAX(fecha) mf FROM stock_snapshots GROUP BY codigo, deposito) lx
                  ON s.codigo=lx.codigo AND s.deposito=lx.deposito AND s.fecha=lx.mf
                GROUP BY s.deposito
                ORDER BY CASE s.deposito WHEN 'SAN_JOSE' THEN 1 WHEN 'LARREA' THEN 2 ELSE 3 END
            """)
            rows = cur.fetchall()
            conn.close()
            if not rows:
                await query.message.edit_text("📦 Sin datos. Cargá archivos primero.")
                return
            nombres = {"SAN_JOSE": "🏭 San José", "LARREA": "🏪 Larrea", "ES_LOCAL": "🏬 Local"}
            lineas = ["📊 *Resumen por depósito*\n"]
            for dep, total, sin_stk, bajo in rows:
                lineas.append(f"{nombres.get(dep, dep)}\n  Total: *{total}* | 🔴 {sin_stk} | 🟡 {bajo}")
            await query.message.edit_text("\n".join(lineas), parse_mode="Markdown")
        else:
            cur = conn.execute("""
                SELECT s.codigo, a.descripcion, s.stock, s.stock_minimo
                FROM stock_snapshots s
                JOIN (SELECT codigo, MAX(fecha) mf FROM stock_snapshots WHERE deposito=? GROUP BY codigo) lx
                  ON s.codigo=lx.codigo AND s.fecha=lx.mf
                LEFT JOIN articulos a ON s.codigo=a.codigo
                WHERE s.deposito=? AND s.stock=0
                ORDER BY a.descripcion LIMIT 15
            """, (deposito, deposito))
            rows = cur.fetchall()
            conn.close()
            nombre_dep = {"SAN_JOSE": "San José", "LARREA": "Larrea"}.get(deposito, deposito)
            if not rows:
                await query.message.edit_text(f"✅ *{nombre_dep}* — Sin quiebres al momento.", parse_mode="Markdown")
                return
            lineas = [f"🔴 *Quiebres en {nombre_dep}*\n"]
            for cod, desc, stk, mn in rows:
                lineas.append(f"`{cod}` {desc or ''}: *{int(stk)}* uds")
            await query.message.edit_text("\n".join(lineas), parse_mode="Markdown")

    # ── Stock: código directo desde lista ──
    elif data.startswith("stock_cod_"):
        codigo = data.replace("stock_cod_", "")
        await _mostrar_stock_codigo(query.message, codigo)

    # ── Precio: código directo desde lista ──
    elif data.startswith("precio_cod_"):
        codigo = data.replace("precio_cod_", "")
        await _mostrar_precio_codigo(query.message, codigo)

    # ── Quiebres: top N ──
    elif data.startswith("quiebres_top_"):
        top = int(data.replace("quiebres_top_", ""))
        await _mostrar_quiebres(query.message, top=top)

    # ── Quiebres: por depósito ──
    elif data.startswith("quiebres_dep_"):
        # Formato: quiebres_dep_DEPOSITO  o  quiebres_dep_DEPOSITO_NUM
        resto = data.replace("quiebres_dep_", "")
        # Detectar si termina en _NUM (ej: LARREA_20, SAN_JOSE_10)
        partes = resto.rsplit("_", 1)
        if len(partes) == 2 and partes[1].isdigit():
            # Ya tiene top → mostrar quiebres directo
            dep = partes[0]
            top = int(partes[1])
            deposito = None if dep == "TODOS" else dep
            await _mostrar_quiebres(query.message, top=top, deposito=deposito)
        else:
            # Solo depósito → pedir cuántos
            dep = resto
            dep_label = {"SAN_JOSE": "San José", "LARREA": "Larrea", "TODOS": "Todos"}.get(dep, dep)
            keyboard = [[
                InlineKeyboardButton("Top 10", callback_data=f"quiebres_dep_{dep}_10"),
                InlineKeyboardButton("Top 20", callback_data=f"quiebres_dep_{dep}_20"),
                InlineKeyboardButton("Top 30", callback_data=f"quiebres_dep_{dep}_30"),
                InlineKeyboardButton("Top 50", callback_data=f"quiebres_dep_{dep}_50"),
            ], [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
            await query.message.edit_text(
                f"📊 Depósito: *{dep_label}*\n¿Cuántos querés ver?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # ── IA quiebres ──
    elif data == "ia_quiebres":
        await query.message.reply_text("🤖 Analizando quiebres con Claude...")
        from modules.ia_engine import motor_ia
        df = get_quiebres(umbral=0)
        resp = motor_ia.analizar_quiebres(df)
        await query.message.reply_text(resp[:4000])

    # ── Lista negra: buscar artículo para agregar ──
    elif data == "negra_buscar":
        _set_estado(query.from_user.id, "buscar_negra")
        kb = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
        try:
            await query.message.edit_text(
                "⛔ *Agregar a lista negra*\n\nEscribí el nombre o código del artículo:",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception:
            await query.message.reply_text(
                "⛔ *Agregar a lista negra*\n\nEscribí el nombre o código del artículo:",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
            )

    # ── Lista negra: confirmar ──
    elif data.startswith("negra_ok_"):
        codigo = data.replace("negra_ok_", "")
        import sqlite3 as _sq
        conn = _sq.connect("roker_nexus.db")
        cur = conn.execute("SELECT descripcion, marca FROM articulos WHERE codigo=?", (codigo,))
        art = cur.fetchone()
        conn.close()
        agregar_a_lista_negra(codigo)
        desc = f"{art[0]}" if art else codigo
        await query.message.edit_text(
            f"⛔ *{desc}* (`{codigo}`) agregado a lista negra.",
            parse_mode="Markdown"
        )

    elif data in ("negra_cancel", "cancelar"):
        await query.message.edit_text("❌ Cancelado.")

# ── Mensaje de texto libre ─────────────────────────────────────
@auth_required
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    texto_low = texto.lower()
    user_id = update.effective_user.id
    estado = _get_estado(user_id)

    # ── Escape universal: si escribe "hola" o similar, limpia estado y muestra menú ──
    SALUDOS = {"hola", "hola!", "buenas", "buenos días", "buenas tardes",
               "buenas noches", "hey", "hi", "menu", "menú", "inicio", "start"}
    if texto_low in SALUDOS or texto_low.startswith("hola"):
        _clear_estado(user_id)
        await _enviar_menu_principal(update.message)
        return

    # ── Estados de espera ──
    if estado.get("esperando") in ("tasa_usd", "umbral", "tope_lote1", "rmb"):
        clave = estado["esperando"]
        texto_limpio = texto.replace("$", "").replace(",", "").replace(" ", "")
        if texto_limpio.count(".") > 1:
            texto_limpio = texto_limpio.replace(".", "")
        try:
            valor = float(texto_limpio)
        except ValueError:
            await update.message.reply_text(
                "⚠️ Número inválido. Ejemplo: *1250* o *1250.50*",
                parse_mode="Markdown"
            )
            return
        _clear_estado(user_id)
        await _guardar_config(update.message, clave, valor)
        return

    if estado.get("esperando") == "buscar_stock":
        _clear_estado(user_id)
        resultados = await _buscar_articulos(texto)
        await _responder_busqueda_stock(update.message, resultados, texto)
        return

    if estado.get("esperando") == "buscar_precio":
        _clear_estado(user_id)
        resultados = await _buscar_articulos(texto)
        await _responder_busqueda_precio(update.message, resultados, texto)
        return

    if estado.get("esperando") == "buscar_articulo":
        _clear_estado(user_id)
        resultados = await _buscar_articulos(texto)
        await _responder_busqueda_opciones(update.message, resultados, texto)
        return

    if estado.get("esperando") == "buscar_negra":
        _clear_estado(user_id)
        resultados = await _buscar_articulos(texto)
        if not resultados:
            await update.message.reply_text(f"❓ No encontré *{texto}*.", parse_mode="Markdown")
            return
        if len(resultados) == 1:
            cod, desc, *_ = resultados[0]
            kb = [
                [InlineKeyboardButton(f"⛔ Confirmar: {desc[:30]}", callback_data=f"negra_ok_{cod}")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")],
            ]
            await update.message.reply_text(
                f"⛔ ¿Agregás `{cod}` a lista negra?\n_{desc}_",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            kb = [[InlineKeyboardButton(
                f"{(d or c)[:35]} ({c})", callback_data=f"negra_add_{c}"
            )] for c, d, *_ in resultados[:8]]
            kb.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
            await update.message.reply_text(
                f"🔍 *{len(resultados)}* artículos. ¿Cuál agregás a lista negra?",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
            )
        return

    if estado.get("esperando") == "buscar_pedido":
        _clear_estado(user_id)
        resultados = await _buscar_articulos(texto)
        if not resultados:
            await update.message.reply_text(f"❓ No encontré *{texto}*.", parse_mode="Markdown")
            return
        if len(resultados) == 1:
            await _mostrar_pedido_codigo(update.message, resultados[0][0], resultados[0][1] or "")
        else:
            keyboard = [[InlineKeyboardButton(
                f"{(d or c)[:35]} ({c})", callback_data=f"pedido_cod_{c}"
            )] for c, d, *_ in resultados[:8]]
            keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
            await update.message.reply_text(
                f"🔍 *{len(resultados)}* artículos. ¿Cuál?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    if estado.get("esperando") == "ia_consulta":
        _clear_estado(user_id)
        await update.message.reply_text("🤖 Consultando a Claude...")
        from modules.ia_engine import motor_ia
        respuesta = motor_ia.consultar(texto)
        keyboard = [[InlineKeyboardButton("🔙 Menú principal", callback_data="menu_volver")]]
        await update.message.reply_text(respuesta[:4000], reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ── Saludos → menú principal ──
    SALUDOS = {"hola", "hola!", "buenas", "buen día", "buenos días", "buenas tardes",
               "buenas noches", "hey", "hi", "menu", "menú", "start", "inicio", "ayuda", "help"}
    if texto_low in SALUDOS or any(s in texto_low for s in ["hola", "buenas", "buen d"]):
        await _enviar_menu_principal(update.message)
        return

    # ── Detectar "stock [término]" o "precio [término]" escritos directo ──
    for prefijo in ["stock ", "/stock "]:
        if texto_low.startswith(prefijo):
            termino = texto[len(prefijo):].strip()
            resultados = await _buscar_articulos(termino)
            await _responder_busqueda_stock(update.message, resultados, termino)
            return

    for prefijo in ["precio ", "/precio "]:
        if texto_low.startswith(prefijo):
            termino = texto[len(prefijo):].strip()
            resultados = await _buscar_articulos(termino)
            await _responder_busqueda_precio(update.message, resultados, termino)
            return

    # ── Cualquier otro texto → preguntar qué quiere hacer con ese artículo ──
    resultados = await _buscar_articulos(texto)
    if resultados:
        await _responder_busqueda_opciones(update.message, resultados, texto)
    else:
        # No encontró nada → ofrecer menú o IA
        keyboard = [
            [InlineKeyboardButton("🤖 Preguntarle a la IA", callback_data="menu_ia")],
            [InlineKeyboardButton("📋 Ver menú completo",   callback_data="menu_volver")],
        ]
        await update.message.reply_text(
            f"🔍 No encontré *{texto}* en el sistema.\n\n¿Qué querés hacer?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )



async def _responder_busqueda_stock(msg, resultados: list, termino: str):
    """Muestra stock del artículo encontrado o lista para elegir."""
    if not resultados:
        await msg.reply_text(f"❓ No encontré *{termino}*.", parse_mode="Markdown")
        return
    if len(resultados) == 1:
        await _mostrar_stock_codigo(msg, resultados[0][0])
        return
    keyboard = []
    for cod, desc, *_ in resultados[:8]:
        desc_c = desc[:35] + "…" if len(desc) > 35 else desc
        keyboard.append([InlineKeyboardButton(f"{desc_c} ({cod})", callback_data=f"stock_cod_{cod}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
    await msg.reply_text(
        f"🔍 *{len(resultados)}* artículos encontrados. ¿Cuál?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _responder_busqueda_precio(msg, resultados: list, termino: str):
    """Muestra precio del artículo encontrado o lista para elegir."""
    if not resultados:
        await msg.reply_text(f"❓ No encontré *{termino}*.", parse_mode="Markdown")
        return
    if len(resultados) == 1:
        await _mostrar_precio_codigo(msg, resultados[0][0])
        return
    keyboard = []
    for cod, desc, *_ in resultados[:8]:
        desc_c = desc[:35] + "…" if len(desc) > 35 else desc
        keyboard.append([InlineKeyboardButton(f"{desc_c} ({cod})", callback_data=f"precio_cod_{cod}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
    await msg.reply_text(
        f"🔍 *{len(resultados)}* artículos. ¿Cuál querés ver?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _buscar_en_transito_pedido(codigo: str) -> str:
    """
    Busca si un artículo está en tránsito o pedido.
    Retorna texto con archivo origen, hoja y renglón para ubicarlo rápido.
    """
    import sqlite3 as _sq
    conn = _sq.connect("roker_nexus.db")

    lineas = []

    # ── Buscar en tránsito ──
    cur = conn.execute("""
        SELECT p.codigo, a.descripcion, p.cantidad, p.proveedor,
               p.fecha_pedido, p.fecha_estimada, p.archivo_origen,
               p.hoja_origen, p.renglon_origen, p.estado, p.notas
        FROM pedidos_transito p
        LEFT JOIN articulos a ON p.codigo = a.codigo
        WHERE UPPER(p.codigo) = UPPER(?)
        ORDER BY p.fecha_pedido DESC LIMIT 5
    """, (codigo,))
    rows_transito = cur.fetchall()

    if rows_transito:
        lineas.append("🚚 *EN TRÁNSITO:*")
        for row in rows_transito:
            cod, desc, cant, prov, f_ped, f_eta, archivo, hoja, renglon, estado, notas = row
            estado_emoji = {"en_transito": "🚢", "en_aduana": "🛃", "entregado": "✅"}.get(estado, "📦")
            lineas.append(
                f"{estado_emoji} *{int(cant or 0)} uds* — {prov or '?'}"
                f"   📅 Pedido: {f_ped or '?'} | ETA: {f_eta or '?'}"
            )
            if archivo:
                lineas.append(f"   📄 Archivo: `{archivo}`")
            if hoja:
                lineas.append(f"   📋 Hoja: *{hoja}*" + (f" — Renglón *{renglon}*" if renglon else ""))
            if notas:
                lineas.append(f"   💬 {notas}")

    # ── Buscar en cotizaciones/pedidos ──
    cur2 = conn.execute("""
        SELECT ci.codigo, ci.descripcion, ci.cantidad_caja, ci.precio_usd,
               c.proveedor, c.invoice_id, c.fecha, c.archivo_origen, c.hoja_origen
        FROM cotizacion_items ci
        JOIN cotizaciones c ON ci.cotizacion_id = c.id
        WHERE UPPER(ci.codigo) = UPPER(?)
        ORDER BY c.fecha DESC LIMIT 3
    """, (codigo,))
    rows_cot = cur2.fetchall()

    if rows_cot:
        if lineas:
            lineas.append("")
        lineas.append("📋 *EN COTIZACIONES:*")
        for row in rows_cot:
            cod, desc, cant, precio, prov, invoice, fecha, archivo, hoja = row
            lineas.append(
                f"• {prov or '?'} — Invoice *{invoice or '?'}* ({fecha or '?'})"
                f"   Cant: {int(cant or 0)} uds | USD {precio or 0:.2f}"
            )
            if archivo:
                lineas.append(f"   📄 `{archivo}`")
            if hoja:
                lineas.append(f"   📋 Hoja: *{hoja}*")

    conn.close()

    if not lineas:
        return None
    return "\n".join(lineas)


async def _responder_busqueda_opciones(msg, resultados: list, termino: str):
    """Cuando el usuario escribe un artículo sin comando — pregunta qué quiere saber."""
    if not resultados:
        await msg.reply_text(f"🔍 No encontré *{termino}*.", parse_mode="Markdown")
        return

    if len(resultados) == 1:
        cod, desc = resultados[0]
        # Ofrecer opciones para ese artículo específico
        keyboard = [
            [
                InlineKeyboardButton("📦 Ver stock",      callback_data=f"stock_cod_{cod}"),
                InlineKeyboardButton("💰 Ver precio",     callback_data=f"precio_cod_{cod}"),
            ],
            [
                InlineKeyboardButton("🚚 Tránsito/Pedido", callback_data=f"pedido_cod_{cod}"),
                InlineKeyboardButton("📦 Stock San José",  callback_data=f"stock_dep_{cod}_SAN_JOSE"),
            ],
            [
                InlineKeyboardButton("⛔ Lista negra",    callback_data=f"negra_add_{cod}"),
                InlineKeyboardButton("❌ Cancelar",       callback_data="cancelar"),
            ],
        ]
        await msg.reply_text(
            f"📱 *{desc}*\n`{cod}`\n\n¿Qué querés saber?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Múltiples resultados → elegir artículo primero
        lineas = [f"🔍 Encontré *{len(resultados)}* artículos para _{termino}_:\n"]
        keyboard = []
        for cod, desc in resultados[:8]:
            desc_corta = desc[:35] + "…" if len(desc) > 35 else desc
            keyboard.append([InlineKeyboardButton(
                f"{desc_corta} ({cod})", callback_data=f"art_opciones_{cod}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
        await msg.reply_text(
            "\n".join(lineas) + "Seleccioná el artículo:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )



# ── Alerta programada de quiebres ─────────────────────────────
async def alerta_quiebres(context: ContextTypes.DEFAULT_TYPE):
    """Se ejecuta automáticamente a las 13:00 Lun-Vie."""
    df = get_quiebres(umbral=10)
    if df.empty:
        return
    sin_stock = len(df[df["stock"] == 0])
    bajo_min  = len(df[df["stock"] > 0])
    texto = (
        f"⏰ *Reporte automático 13:00*\n\n"
        f"🔴 Sin stock: *{sin_stock}* artículos\n"
        f"🟡 Bajo mínimo: *{bajo_min}* artículos\n\n"
        f"Usá /quiebres para ver el detalle."
    )
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=texto, parse_mode="Markdown")


# ── Helpers ───────────────────────────────────────────────────
def _get_tasa() -> float:
    try:
        conn = sqlite3.connect("roker_nexus.db")
        cur = conn.execute("SELECT usd_ars FROM tasas_cambio ORDER BY fecha DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return float(row[0]) if row else MONEDA_USD_ARS
    except Exception:
        return MONEDA_USD_ARS

# ── Main ──────────────────────────────────────────────────────

# ── /pedido — buscar si está en tránsito o pedido ─────────────
@auth_required
async def cmd_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        _set_estado(update.effective_user.id, "buscar_pedido")
        await update.message.reply_text(
            "🚚 *¿Qué artículo querés rastrear?*\n\nEscribí el nombre o código:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]])
        )
        return
    query = " ".join(args).strip()
    resultados = await _buscar_articulos(query)
    if not resultados:
        await update.message.reply_text(f"❓ No encontré *{query}*.", parse_mode="Markdown")
        return
    if len(resultados) == 1:
        await _mostrar_pedido_codigo(update.message, resultados[0][0], resultados[0][1])
    else:
        keyboard = []
        for cod, desc, *_ in resultados[:8]:
            desc_c = desc[:35] + "…" if len(desc) > 35 else desc
            keyboard.append([InlineKeyboardButton(f"{desc_c} ({cod})", callback_data=f"pedido_cod_{cod}")])
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
        await update.message.reply_text(
            f"🔍 *{len(resultados)}* artículos. ¿Cuál rastreamos?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def _mostrar_pedido_codigo(message, codigo: str, desc: str = ""):
    await message.reply_text("🔍 Buscando...")
    resultado = await _buscar_en_transito_pedido(codigo)
    keyboard = [
        [
            InlineKeyboardButton("📦 Ver stock",  callback_data=f"stock_cod_{codigo}"),
            InlineKeyboardButton("💰 Ver precio", callback_data=f"precio_cod_{codigo}"),
        ],
        [InlineKeyboardButton("🔙 Menú", callback_data="menu_volver")]
    ]
    if resultado:
        texto = f"📱 *{desc or codigo}* — `{codigo}`\n\n{resultado}"
    else:
        texto = (
            f"📱 *{desc or codigo}* — `{codigo}`\n\n"
            f"⚪ Sin registros de tránsito ni cotizaciones."
        )
    await message.reply_text(texto, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    if not TELEGRAM_TOKEN:
        print("⚠️  TELEGRAM_TOKEN no configurado en .env")
        return

    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("menu",      cmd_menu))
    app.add_handler(CommandHandler("stock",     cmd_stock))
    app.add_handler(CommandHandler("precio",    cmd_precio))
    app.add_handler(CommandHandler("quiebres",  cmd_quiebres))
    app.add_handler(CommandHandler("sinstock",  cmd_sinstock))
    app.add_handler(CommandHandler("transito",  cmd_transito))
    app.add_handler(CommandHandler("pedido",    cmd_pedido))
    app.add_handler(CommandHandler("negra",     cmd_negra))
    app.add_handler(CommandHandler("config",    cmd_config))
    app.add_handler(CommandHandler("resumen",   cmd_resumen))
    app.add_handler(CommandHandler("ia",        cmd_ia))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Alerta automática 13:00 Lun-Vie
    from telegram.ext import JobQueue
    job_queue = app.job_queue
    if job_queue:
        import datetime, pytz
        tz = pytz.timezone("America/Argentina/Buenos_Aires")
        job_queue.run_daily(
            alerta_quiebres,
            time=datetime.time(13, 0, tzinfo=tz),
            days=(0, 1, 2, 3, 4),
        )
        # Notificación de deploy al arrancar
        job_queue.run_once(_notificar_deploy, when=3)

    print("🤖 Roker Nexus Bot iniciado. Ctrl+C para detener.")

    # Notificación de arranque (backup directo, sin job_queue)
    import threading
    def _enviar_notif_arranque():
        import time, requests
        time.sleep(5)
        try:
            from version import get_nota_deploy
            texto = get_nota_deploy()
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": texto,
                "parse_mode": "Markdown"
            }, timeout=10)
            print("✅ Notificación de deploy enviada")
        except Exception as e:
            print(f"⚠️ Notificación fallida: {e}")
    threading.Thread(target=_enviar_notif_arranque, daemon=True).start()

    app.run_polling(drop_pending_updates=True)


async def _notificar_deploy(context):
    try:
        from version import get_nota_deploy
        texto = get_nota_deploy()
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=texto,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"⚠️ No se pudo notificar deploy (job): {e}")


if __name__ == "__main__":
    main()
