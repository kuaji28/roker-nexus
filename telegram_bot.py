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
    texto = (
        "⚡ *ROKER NEXUS* — Bot activo\n\n"
        "Comandos disponibles:\n"
        "/stock `[código]` — Stock en todos los depósitos\n"
        "/precio `[código]` — Precios Lista 1 y ML\n"
        "/quiebres — Top 10 quiebres urgentes\n"
        "/sinstock — Lista completa sin stock\n"
        "/transito — Pedidos en tránsito\n"
        "/negra `[código]` — Agregar a lista negra\n"
        "/config `[clave] [valor]` — Actualizar configuración\n"
        "/resumen — Estado ejecutivo del sistema\n"
        "/ia `[consulta]` — Preguntarle a Claude\n"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


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


# ── /config ───────────────────────────────────────────────────
@auth_required
async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Uso: /config [clave] [valor]\n\n"
            "Claves disponibles:\n"
            "• `tasa_usd [valor]` — Tipo de cambio\n"
            "• `umbral_quiebre [valor]` — Umbral stock\n"
            "• `tope_lote1 [valor]` — Tope USD Lote 1\n",
            parse_mode="Markdown"
        )
        return

    clave = args[0].lower()
    try:
        valor = float(args[1])
    except ValueError:
        await update.message.reply_text("El valor debe ser un número.")
        return

    if clave == "tasa_usd":
        conn = sqlite3.connect("roker_nexus.db")
        conn.execute(
            "INSERT OR REPLACE INTO tasas_cambio (fecha, usd_ars) VALUES (date('now'), ?)",
            (valor,)
        )
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Tasa USD/ARS actualizada a *${valor:,.0f}*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"Clave `{clave}` no reconocida.", parse_mode="Markdown")


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

    # ── Cancelar ──
    if data == "cancelar":
        await query.message.edit_text("❌ Cancelado.")

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
        dep = data.replace("quiebres_dep_", "")
        deposito = None if dep == "TODOS" else dep
        keyboard = [[
            InlineKeyboardButton("Top 10", callback_data=f"quiebres_dep_{dep}_10"),
            InlineKeyboardButton("Top 20", callback_data=f"quiebres_dep_{dep}_20"),
            InlineKeyboardButton("Top 30", callback_data=f"quiebres_dep_{dep}_30"),
            InlineKeyboardButton("Top 50", callback_data=f"quiebres_dep_{dep}_50"),
        ]]
        dep_label = {"SAN_JOSE": "San José", "LARREA": "Larrea", "TODOS": "todos"}.get(dep, dep)
        await query.message.edit_text(
            f"📊 Depósito: *{dep_label}*\n¿Cuántos querés ver?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("quiebres_dep_") and data.count("_") >= 3:
        parts = data.split("_")
        dep = parts[2]
        top = int(parts[3]) if len(parts) > 3 else 10
        deposito = None if dep == "TODOS" else dep
        await _mostrar_quiebres(query.message, top=top, deposito=deposito)

    # ── IA quiebres ──
    elif data == "ia_quiebres":
        await query.message.reply_text("🤖 Analizando quiebres con Claude...")
        from modules.ia_engine import motor_ia
        df = get_quiebres(umbral=0)
        resp = motor_ia.analizar_quiebres(df)
        await query.message.reply_text(resp[:4000])

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
    """Responde mensajes de texto libres con IA."""
    texto = update.message.text
    from modules.ia_engine import motor_ia
    respuesta = motor_ia.consultar(texto)
    await update.message.reply_text(respuesta[:4000])


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
def main():
    if not TELEGRAM_TOKEN:
        print("⚠️  TELEGRAM_TOKEN no configurado en .env")
        return

    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("stock",     cmd_stock))
    app.add_handler(CommandHandler("precio",    cmd_precio))
    app.add_handler(CommandHandler("quiebres",  cmd_quiebres))
    app.add_handler(CommandHandler("sinstock",  cmd_sinstock))
    app.add_handler(CommandHandler("transito",  cmd_transito))
    app.add_handler(CommandHandler("negra",     cmd_negra))
    app.add_handler(CommandHandler("config",    cmd_config))
    app.add_handler(CommandHandler("resumen",   cmd_resumen))
    app.add_handler(CommandHandler("ia",        cmd_ia))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Alerta automática 13:00 todos los días
    from telegram.ext import JobQueue
    job_queue = app.job_queue
    if job_queue:
        import datetime, pytz
        tz = pytz.timezone("America/Argentina/Buenos_Aires")
        job_queue.run_daily(
            alerta_quiebres,
            time=datetime.time(13, 0, tzinfo=tz),
            days=(0, 1, 2, 3, 4),  # Lun-Vie
        )

    print("🤖 Roker Nexus Bot iniciado. Ctrl+C para detener.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
