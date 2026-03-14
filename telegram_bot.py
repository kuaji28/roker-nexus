import os
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

# Configuración — lee de Railway Variables (env vars) primero
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Railway Variables tienen prioridad
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MONEDA_USD_ARS   = float(os.getenv("TASA_USD_ARS", "1420"))

# Si no están en env vars, leer de la DB local
if not TELEGRAM_TOKEN:
    try:
        from database import get_config as _gc_tg
        TELEGRAM_TOKEN   = str(_gc_tg("telegram_token")   or "")
        TELEGRAM_CHAT_ID = str(_gc_tg("telegram_admin_id") or TELEGRAM_CHAT_ID)
        MONEDA_USD_ARS   = float(_gc_tg("tasa_usd_ars", float) or MONEDA_USD_ARS)
    except Exception:
        pass
# Adaptar database para v3.0
try:
    from database import (
        get_quiebres, get_lista_negra,
        agregar_a_lista_negra, quitar_de_lista_negra,
        query_to_df, execute_query, init_db
    )
except ImportError:
    import roker_database as _rdb2
    import pandas as _pd2
    def query_to_df(sql, params=()):
        conn = _rdb2.get_connection()
        try:
            df = _pd2.read_sql_query(sql, conn, params=params if params else None)
        except Exception:
            df = _pd2.DataFrame()
        finally:
            conn.close()
        return df
    def execute_query(sql, params=(), fetch=True):
        conn = _rdb2.get_connection()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            if fetch:
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception:
            pass
        finally:
            conn.close()
        return []
    def get_quiebres(umbral=10, deposito=None):
        return _pd2.DataFrame()
    def get_lista_negra():
        return _rdb2.get_lista_negra()
    def agregar_a_lista_negra(codigo, desc=""):
        _rdb2.agregar_lista_negra(desc, codigo)
    def quitar_de_lista_negra(codigo):
        pass
    def init_db():
        _rdb2.inicializar_db()
try:
    from utils.helpers import fmt_usd, fmt_num, color_stock
except ImportError:
    def fmt_usd(v): return f"USD {float(v or 0):,.2f}"
    def fmt_num(v): return f"{int(v or 0):,}"
    def color_stock(s, m=0): return "🔴" if float(s or 0)==0 else ("🟡" if float(s or 0)<float(m or 0) else "🟢")
try:
    from modules.inventario import detectar_quiebre_entre_depositos
except ImportError:
    def detectar_quiebre_entre_depositos(*a, **k): return None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
import functools

# ── Seguridad: solo responde al chat autorizado ───────────────
def autorizado(update: Update) -> bool:
    # Si no hay CHAT_ID configurado, acepta cualquier mensaje (modo debug)
    # En producción, configurar TELEGRAM_CHAT_ID en Railway Variables
    if not TELEGRAM_CHAT_ID:
        return True
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
            InlineKeyboardButton("📝 Borrador pedido", callback_data="menu_borrador"),
            InlineKeyboardButton("🤖 Preguntarle a IA", callback_data="menu_ia"),
        ],
        [
            InlineKeyboardButton("💵 Tipo de cambio", callback_data="menu_dolar"),
            InlineKeyboardButton("📊 KPIs", callback_data="menu_kpis_fast"),
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
    """Muestra stock completo: depósitos, precios L1/L4, tránsito, último ingreso, sugerencia."""
    import sqlite3 as _sq, os as _os_s
    _db = _os_s.path.join(_os_s.path.dirname(_os_s.path.abspath(__file__)), "roker_nexus.db")
    conn = _sq.connect(_db)

    # Stock por depósito
    cur = conn.execute("""
        SELECT s.deposito, s.stock, s.stock_minimo, s.stock_optimo
        FROM stock_snapshots s
        JOIN (SELECT deposito, MAX(fecha) mf FROM stock_snapshots WHERE codigo=? GROUP BY deposito) lx
          ON s.deposito=lx.deposito AND s.fecha=lx.mf
        WHERE s.codigo=?
        ORDER BY CASE s.deposito WHEN 'SAN_JOSE' THEN 1 WHEN 'LARREA' THEN 2 ELSE 3 END
    """, (codigo, codigo))
    rows_stock = cur.fetchall()

    # Artículo + precios
    cur2 = conn.execute("""
        SELECT a.descripcion, a.marca, p.lista_1, p.lista_4
        FROM articulos a
        LEFT JOIN precios p ON a.codigo=p.codigo
        WHERE a.codigo=?
        ORDER BY p.fecha DESC LIMIT 1
    """, (codigo,))
    art = cur2.fetchone()

    # En tránsito (cotizaciones)
    cur3 = conn.execute("""
        SELECT SUM(ci.cantidad_pedida - COALESCE(ci.cantidad_recibida,0)) as en_transito,
               c.invoice_id, c.fecha
        FROM cotizacion_items ci
        JOIN cotizaciones c ON ci.cotizacion_id=c.id
        WHERE (ci.codigo_flexxus=? OR ci.codigo_proveedor=?)
          AND c.estado IN ('pendiente','en_transito')
          AND ci.cantidad_pedida > COALESCE(ci.cantidad_recibida,0)
        GROUP BY c.id ORDER BY c.fecha DESC LIMIT 1
    """, (codigo, codigo))
    transito = cur3.fetchone()

    # Optimización (sugerencia y demanda)
    cur4 = conn.execute("""
        SELECT demanda_promedio, stock_actual, stock_optimo, costo_reposicion
        FROM optimizacion WHERE codigo=? LIMIT 1
    """, (codigo,))
    opt = cur4.fetchone()

    conn.close()

    if not rows_stock and not art:
        await message.reply_text(f"❓ Sin datos para `{codigo}`.", parse_mode="Markdown")
        return

    desc = art[0] if art else codigo
    marca_str = f" ({art[1]})" if art and art[1] else ""
    l1_usd = float(art[2] or 0) if art else 0
    l4_ars = float(art[3] or 0) if art else 0

    # Obtener tasa
    try:
        from database import get_config  # noqa as _gc
        tasa = float(_gc("tasa_usd_ars", float) or 1420)
    except Exception:
        tasa = 1420

    l1_ars = l1_usd * tasa
    nombres_dep = {"SAN_JOSE": "🏭 San José", "LARREA": "🏪 Larrea", "ES_LOCAL": "🏬 Local"}

    lineas = [f"📦 *{desc}*{marca_str}\n`{codigo}`\n"]

    # Stock por depósito
    stock_total = 0
    for dep, stk, minn, opt_s in rows_stock:
        stk = int(stk or 0)
        minn = int(minn or 0)
        stock_total += stk
        icono = color_stock(stk, minn)
        nombre = nombres_dep.get(dep, dep)
        lineas.append(f"{icono} *{nombre}*: {stk} u _(mín: {minn})_")

    # Precios
    lineas.append("")
    if l1_usd > 0:
        lineas.append(f"💵 Lista 1: *USD {l1_usd:.2f}* = *${l1_ars:,.0f} ARS*")
    if l4_ars > 0:
        alerta = " ⚠️ _bajo stock_" if stock_total <= 3 and stock_total > 0 else ""
        lineas.append(f"🛒 Precio ML (L4): *${l4_ars:,.0f} ARS*{alerta}")
    elif l1_usd > 0:
        lineas.append(f"🛒 Precio ML: _sin precio L4 cargado_")

    # En tránsito
    if transito and transito[0] and int(transito[0]) > 0:
        lineas.append(f"\n✈️ En tránsito: *{int(transito[0])} uds* (Invoice {transito[1] or '?'}, {str(transito[2] or '')[:10]})")
    else:
        lineas.append(f"\n✈️ En tránsito: _ninguno_")

    # Sugerencia IA
    if opt:
        dem = max(0.0, float(opt[0] or 0))
        stk_actual = float(opt[1] or 0)
        stk_opt = float(opt[2] or 0)
        costo = float(opt[3] or 0)
        if dem > 0 and stk_actual < stk_opt:
            dias = int(stk_actual / (dem / 30)) if dem > 0 else 999
            a_pedir = int(stk_opt - stk_actual)
            subtotal = a_pedir * costo
            lineas.append(f"\n🧠 *Sugerencia:* pedir *{a_pedir} uds* | Cobertura actual: *{dias} días* | Costo: USD {subtotal:.0f}")
        elif stk_actual >= stk_opt:
            lineas.append(f"\n🧠 Stock OK — cobertura suficiente")

    kb = [[
        InlineKeyboardButton("💰 Ver precio", callback_data=f"precio_cod_{codigo}"),
        InlineKeyboardButton("🔙 Menú", callback_data="menu_volver"),
    ]]
    await message.reply_text("\n".join(lineas), parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


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
    import os as _osp
    _db = _osp.path.join(_osp.path.dirname(_osp.path.abspath(__file__)), "roker_nexus.db")
    conn = sqlite3.connect(_db)
    cur = conn.execute("SELECT lista_1, lista_4 FROM precios WHERE codigo=? ORDER BY fecha DESC LIMIT 1", (codigo,))
    row = cur.fetchone()
    cur2 = conn.execute("SELECT descripcion, marca FROM articulos WHERE codigo=?", (codigo,))
    art = cur2.fetchone()
    # Stock total
    cur3 = conn.execute("""
        SELECT SUM(s.stock) FROM stock_snapshots s
        JOIN (SELECT codigo, MAX(fecha) mf FROM stock_snapshots WHERE codigo=? GROUP BY 1) lx
          ON s.codigo=lx.codigo AND s.fecha=lx.mf
        WHERE s.codigo=?
    """, (codigo, codigo))
    stk_row = cur3.fetchone()
    conn.close()

    if not row:
        await message.reply_text(f"❓ Sin precios para `{codigo}`.", parse_mode="Markdown")
        return

    desc = art[0] if art else codigo
    marca = f" ({art[1]})" if art and art[1] else ""
    tasa = _get_tasa()
    l1_usd = float(row[0] or 0)
    l4_ars = float(row[1] or 0)
    l1_ars = l1_usd * tasa
    stock = int(stk_row[0] or 0) if stk_row else 0

    # Alerta si bajo stock
    alerta_stock = ""
    if stock == 0:
        alerta_stock = "\n\n🔴 *SIN STOCK* — artículo en quiebre"
    elif stock <= 5:
        alerta_stock = f"\n\n🟡 *Stock bajo:* solo {stock} unidades"

    # Calcular margen ML
    margen_info = ""
    if l1_ars > 0 and l4_ars > 0:
        margen_pct = (l4_ars - l1_ars) / l4_ars * 100
        emoji_mg = "🟢" if margen_pct >= 30 else ("🟡" if margen_pct >= 15 else "🔴")
        margen_info = f"\n{emoji_mg} Margen ML: *{margen_pct:.1f}%*"

    texto = (
        f"💰 *{desc}*{marca}\n`{codigo}`\n\n"
        f"📋 Lista 1 (mayorista): *USD {l1_usd:.2f}* = *${l1_ars:,.0f} ARS*\n"
        f"🛒 Lista 4 (ML): *${l4_ars:,.0f} ARS*"
        f"{margen_info}"
        f"{alerta_stock}"
    )
    kb = [[
        InlineKeyboardButton("📦 Ver stock", callback_data=f"stock_cod_{codigo}"),
        InlineKeyboardButton("🔙 Menú", callback_data="menu_volver"),
    ]]
    await message.reply_text(texto, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


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
    """Lista completa de cotizaciones en tránsito con detalle de ítems."""
    df_cots = query_to_df("""
        SELECT c.id, c.invoice_id, c.proveedor, c.fecha, c.total_usd, c.estado,
               c.fecha_transito, c.fecha_estimada_llegada,
               COUNT(ci.id) as items,
               SUM(ci.cantidad_pedida) as unidades,
               SUM(ci.cantidad_recibida) as recibidas
        FROM cotizaciones c
        LEFT JOIN cotizacion_items ci ON c.id=ci.cotizacion_id
        WHERE c.estado IN ('pendiente','en_transito')
        GROUP BY c.id
        ORDER BY c.fecha DESC
    """)

    if df_cots.empty:
        await update.message.reply_text("📭 No hay pedidos pendientes ni en tránsito.")
        return

    lineas = [f"✈️ *Pedidos activos* — {len(df_cots)} invoices\n"]
    for _, r in df_cots.iterrows():
        estado = str(r.get("estado",""))
        emoji = "✈️" if estado == "en_transito" else "⏳"
        inv = r.get("invoice_id","?")
        total = float(r.get("total_usd") or 0)
        items = int(r.get("items") or 0)
        uds = int(r.get("unidades") or 0)
        rec = int(r.get("recibidas") or 0)
        pendiente = uds - rec
        fecha = str(r.get("fecha_transito") or r.get("fecha","?"))[:10]
        eta = str(r.get("fecha_estimada_llegada") or "—")[:10]

        lineas.append(
            f"{emoji} *Invoice #{inv}*\n"
            f"  {items} ítems | {uds} uds pedidas | {pendiente} pendientes\n"
            f"  USD {total:,.0f} | Fecha: {fecha} | ETA: {eta}"
        )

    kb = [[InlineKeyboardButton("🔙 Menú", callback_data="menu_volver")]]
    # Telegram tiene límite de 4096 chars
    texto = "\n".join(lineas)
    if len(texto) > 3900:
        texto = texto[:3900] + "\n_...y más_"
    await update.message.reply_text(texto, parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(kb))


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
        _db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roker_nexus.db")
        conn = sqlite3.connect(_db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO tasas_cambio (moneda, fecha, usd_ars) VALUES ('USD', date('now'), ?)",
                (valor,)
            )
        except Exception:
            conn.execute(
                "INSERT OR REPLACE INTO tasas_cambio (fecha, usd_ars) VALUES (date('now'), ?)",
                (valor,)
            )
        conn.execute("INSERT OR REPLACE INTO configuracion (clave,valor,descripcion) VALUES(?,?,?)",
                    ("tasa_usd_ars", str(int(valor)), "USD a ARS"))
        conn.commit()
        conn.close()
        await message.reply_text(
            f"✅ *Dólar actualizado*\n💵 USD/ARS = *${valor:,.0f}*",
            parse_mode="Markdown"
        )
        # Alertar si algún producto perdió margen
        try:
            from modules.ia_engine import motor_ia
            alertas = motor_ia.alertas_margen_dolar(valor)
            if alertas:
                lineas = [f"⚠️ *{len(alertas)} artículos con margen bajo ({valor:,.0f} ARS/USD)*\n"]
                for a in alertas[:5]:
                    lineas.append(
                        f"• `{a['codigo']}` {a['descripcion']}\n"
                        f"  Margen: *{a['margen_actual_pct']:.1f}%* → Precio sugerido: ${a['precio_sugerido']:,.0f}"
                    )
                await message.reply_text("\n".join(lineas), parse_mode="Markdown")
        except Exception:
            pass
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
        import sqlite3 as _sq3, os as _os3
        _db3 = _os3.path.join(_os3.path.dirname(_os3.path.abspath(__file__)), "roker_nexus.db")
        _c3 = _sq3.connect(_db3)
        _c3.execute("INSERT OR REPLACE INTO configuracion (clave,valor,descripcion) VALUES(?,?,?)",
                    ("tasa_rmb_usd", str(valor), "RMB Yuan a ARS"))
        _c3.commit()
        _c3.close()
        await message.reply_text(
            f"✅ *Yuan actualizado*\n🇨🇳 RMB/ARS = *${valor:,.2f}*",
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
        kb = [
            [InlineKeyboardButton("💵 USD → ARS",   callback_data="cfg_tasa_usd")],
            [InlineKeyboardButton("🇨🇳 RMB → ARS",  callback_data="cfg_tasa_rmb")],
            [InlineKeyboardButton("❌ Cancelar",    callback_data="cancelar")],
        ]
        try:
            await query.message.edit_text(
                "💱 *Tipo de cambio*\n¿Cuál querés actualizar?",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception:
            await query.message.reply_text(
                "💱 *Tipo de cambio*\n¿Cuál querés actualizar?",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
            )

    elif data == "menu_rmb":
        _set_estado(user_id, "rmb")
        await query.message.edit_text(
            "💱 *Tipo de cambio RMB (Yuan)*\n\nEscribí el nuevo valor en ARS:",
            parse_mode="Markdown"
        )

    elif data == "menu_resumen":
        try:
            from database import get_resumen_stats
            stats = get_resumen_stats()
        except Exception:
            stats = {}
        total = stats.get('total_articulos', 0)
        nota = "" if total > 0 else "\n\n_Subí los archivos Flexxus desde la app web para ver datos._"
        texto = (
            f"⚡ *Roker Nexus — Resumen*\n"
            f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n"
            f"📦 Artículos activos: *{total:,}*\n"
            f"🔴 Sin stock: *{stats.get('sin_stock',0)}*\n"
            f"🟡 Bajo mínimo: *{stats.get('bajo_minimo',0)}*\n"
            f"🕐 Última importación: {stats.get('ultima_importacion','—')}"
            f"{nota}\n"
        )
        keyboard = [[InlineKeyboardButton("🔄 Actualizar", callback_data="menu_resumen"),
                     InlineKeyboardButton("🔙 Menú", callback_data="menu_volver")]]
        await query.message.edit_text(texto, parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "menu_negra":
        try:
            from database import get_lista_negra
            lista = get_lista_negra()
        except Exception:
            lista = []
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
        try:
            await query.message.edit_text("🔄 Consultando tránsito...")
        except Exception:
            pass
        import sqlite3 as _sq, os as _ost
        _db = _ost.path.join(_ost.path.dirname(_ost.path.abspath(__file__)), "roker_nexus.db")
        conn = _sq.connect(_db)
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

    # ── Stock de un depósito específico (artículo + depósito) ──
    elif data.startswith("stock_dep_") and not any(data == f"stock_dep_{d}" for d in ("SAN_JOSE", "LARREA", "TODOS")):
        partes = data.replace("stock_dep_", "").rsplit("_", 1)
        if len(partes) == 2 and not partes[1].isdigit():
            cod = partes[0]
        else:
            cod = partes[0]
        await _mostrar_stock_codigo(query.message, cod)

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
    elif data in ("cfg_tasa_rmb", "menu_rmb"):
        _set_estado(user_id, "rmb")
        try:
            await query.message.edit_text(
                "🇨🇳 *Tipo de cambio RMB (Yuan)*\n\nEscribí el nuevo valor ARS por RMB (ej: 200):",
                parse_mode="Markdown"
            )
        except Exception:
            await query.message.reply_text(
                "🇨🇳 *Tipo de cambio RMB (Yuan)*\n\nEscribí el nuevo valor ARS por RMB:",
                parse_mode="Markdown"
            )

    elif data == "cfg_tasa_usd":
        _set_estado(user_id, "tasa_usd")
        conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "roker_nexus.db"))
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

    # ── Lista negra: negra_add_ (alias de negra_ok_) ──
    elif data.startswith("negra_add_"):
        codigo = data.replace("negra_add_", "")
        import sqlite3 as _sq2
        _conn2 = _sq2.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "roker_nexus.db"))
        _cur2 = _conn2.execute("SELECT descripcion FROM articulos WHERE codigo=?", (codigo,))
        _art2 = _cur2.fetchone()
        _conn2.close()
        _desc2 = _art2[0] if _art2 else codigo
        keyboard_neg = [[
            InlineKeyboardButton(f"⛔ Sí, bloquear", callback_data=f"negra_ok_{codigo}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar"),
        ]]
        try:
            await query.message.edit_text(
                f"⛔ ¿Agregás `{codigo}` a lista negra?\n_{_desc2}_",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard_neg)
            )
        except Exception:
            await query.message.reply_text(
                f"⛔ ¿Agregás `{codigo}` a lista negra?\n_{_desc2}_",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard_neg)
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

    elif data == "menu_borrador":
        _set_estado(query.from_user.id, "borrador_buscar")
        kb = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
        await query.message.edit_text(
            "📝 *Borrador de pedido*\n\nEscribí el nombre del modelo que querés agregar:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "borrador_ver":
        df_b = query_to_df("SELECT descripcion, cantidad, precio_usd, estado FROM borrador_pedido WHERE estado!='descartado' ORDER BY estado,descripcion LIMIT 20")
        if df_b.empty:
            await query.message.edit_text("📝 Borrador vacío.")
        else:
            lineas = ["📝 *Borrador actual:*\n"]
            for _, r in df_b.iterrows():
                e = "✅" if r["estado"]=="confirmado" else "⏳"
                lineas.append(f"{e} {str(r.get('descripcion',''))[:35]} | {int(r.get('cantidad',0))} u | USD {float(r.get('precio_usd',0)):.0f}")
            await query.message.edit_text("\n".join(lineas), parse_mode="Markdown")

    elif data == "borrador_matching":
        await query.message.reply_text("🔍 Usá la app web para completar el matching de ítems pendientes.")

    elif data.startswith("bor_add_"):
        # bor_add_CODIGO_QUERY
        resto = data.replace("bor_add_", "")
        partes = resto.split("_", 1)
        codigo = partes[0]
        query_orig = partes[1] if len(partes) > 1 else codigo
        df_art = query_to_df("SELECT descripcion, lista_1 as precio FROM precios p JOIN articulos a ON p.codigo=a.codigo WHERE a.codigo=? LIMIT 1", (codigo,))
        desc = df_art.iloc[0]["descripcion"] if not df_art.empty else codigo
        precio = float(df_art.iloc[0]["precio"] or 0) if not df_art.empty else 0
        from database import execute_query as _eq2
        _eq2("""INSERT INTO borrador_pedido
                (texto_original, codigo_flexxus, descripcion, tipo_codigo,
                 cantidad, precio_usd, subtotal_usd, match_confirmado, estado, origen)
                VALUES (?,?,?,'mecanico',1,?,?,1,'confirmado','telegram')""",
             (query_orig, codigo, desc, precio, precio), fetch=False)
        await query.message.edit_text(
            f"✅ *{desc[:40]}* agregado al borrador.\n`{codigo}` | USD {precio:.2f}\n\n"
            f"Usá `/borrador` para ver el borrador completo.",
            parse_mode="Markdown"
        )

    elif data.startswith("bor_sinc_"):
        query_orig = data.replace("bor_sinc_", "")
        from database import execute_query as _eq3
        _eq3("""INSERT INTO borrador_pedido
                (texto_original, descripcion, estado, origen)
                VALUES (?,?,'pendiente','telegram')""",
             (query_orig, query_orig.upper()), fetch=False)
        await query.message.edit_text(f"📝 *{query_orig}* agregado como pendiente.\nCompletá el código desde la app web.", parse_mode="Markdown")

    elif data == "sinstock_mov":
        await _mostrar_sinstock(query.message, con_mov=True)
    elif data == "sinstock_sinmov":
        await _mostrar_sinstock(query.message, con_mov=False)
    elif data == "sinstock_todos":
        await _mostrar_sinstock(query.message, con_mov=None)

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
        try:
            from modules.ia_engine import motor_ia
            respuesta = motor_ia.consultar(texto)
            if "401" in str(respuesta) or "authentication" in str(respuesta).lower():
                respuesta = "⚠️ API Key de Claude no configurada en Railway.\nAndá a Railway → Variables → agregá ANTHROPIC_API_KEY"
        except Exception as e:
            respuesta = f"⚠️ Error IA: {str(e)[:200]}"
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
            f"🔍 No encontré *{texto[:30]}* en el sistema.\n\n¿Qué querés hacer?",
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
        cod, desc, *_ = resultados[0]
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





# ── /ia2 — consulta en paralelo (Claude + Gemini + GPT activos) ───────────
@auth_required
async def cmd_ia2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = " ".join(context.args) if context.args else ""
    if not consulta:
        await update.message.reply_text(
            "🤖 */ia2* — Consulta a todos los modelos IA activos en paralelo.\n"
            "Uso: `/ia2 ¿qué artículos Samsung están en quiebre?`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(f"🤖🤖 Consultando a todos los IAs: _{consulta}_\nEsperá...",
                                     parse_mode="Markdown")
    from modules.ia_engine import motor_ia
    respuestas = motor_ia.consultar_paralelo(consulta)

    for nombre, respuesta in respuestas.items():
        emoji = {"claude": "🤖", "gemini": "✨", "gpt": "💡"}.get(nombre.lower(), "🧠")
        texto = f"{emoji} *{nombre.upper()}:*\n{respuesta[:3500]}"
        try:
            await update.message.reply_text(texto, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(texto)


# ── /tasa — sin argumentos muestra menú, con número actualiza directo ──────────────────
@auth_required
async def cmd_tasa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        kb = [
            [InlineKeyboardButton("💵 USD → ARS", callback_data="cfg_tasa_usd")],
            [InlineKeyboardButton("🇨🇳 RMB → ARS", callback_data="cfg_tasa_rmb")],
            [InlineKeyboardButton("❌ Cancelar",   callback_data="cancelar")],
        ]
        await update.message.reply_text(
            "💱 *¿Qué tasa querés actualizar?*",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    if args[0].upper() == "RMB" and len(args) > 1:
        try:
            valor = float(args[1].replace(",", "."))
            await _guardar_config(update.message, "rmb", valor)
        except ValueError:
            await update.message.reply_text("Uso: /tasa RMB 7.3")
    else:
        try:
            valor = float(args[0].replace(".", "").replace(",", "."))
            await _guardar_config(update.message, "tasa_usd", valor)
        except ValueError:
            await update.message.reply_text("Uso: /tasa 1420")


# ── /criticos ──────────────────────────────────────────────────────────────────────────
@auth_required
async def cmd_criticos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
    df = query_to_df("""
        SELECT o.codigo, COALESCE(a.descripcion, o.descripcion) as descripcion,
               o.stock_actual, o.demanda_promedio, o.costo_reposicion,
               (o.stock_optimo - o.stock_actual) as a_pedir,
               ((o.stock_optimo - o.stock_actual) * o.costo_reposicion) as subtotal
        FROM optimizacion o LEFT JOIN articulos a ON o.codigo=a.codigo
        WHERE o.stock_actual = 0 AND o.demanda_promedio > 0
          AND COALESCE(a.en_lista_negra, 0) = 0
        ORDER BY o.demanda_promedio DESC
    """)
    if df.empty:
        await update.message.reply_text("✅ Sin críticos (stock=0) al momento.")
        return
    df = df.head(top)
    lineas = [f"🔴 *Top {top} Críticos* (stock = 0)\n"]
    total_usd = 0.0
    for _, r in df.iterrows():
        desc = str(r.get("descripcion") or r.get("codigo","?"))[:30]
        dem = max(0.0, float(r.get("demanda_promedio") or 0))
        sub = float(r.get("subtotal") or 0)
        pedir = int(r.get("a_pedir") or 0)
        total_usd += sub
        lineas.append(f"`{r['codigo']}` {desc}\n  Dem: {dem:.1f}/mes | Pedir: {pedir}u | ${sub:.0f}")
    lineas.append(f"\n💰 *Total: USD {total_usd:,.0f}*")
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


# ── /urgentes ─────────────────────────────────────────────────────────────────────────
@auth_required
async def cmd_urgentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
    df = query_to_df("""
        SELECT o.codigo, COALESCE(a.descripcion, o.descripcion) as descripcion,
               o.stock_actual, o.stock_optimo, o.demanda_promedio, o.costo_reposicion,
               CASE WHEN o.demanda_promedio > 0
                    THEN ROUND(o.stock_actual / (o.demanda_promedio / 30.0), 0)
                    ELSE 999 END as dias_cobertura
        FROM optimizacion o LEFT JOIN articulos a ON o.codigo=a.codigo
        WHERE o.stock_actual > 0 AND o.stock_actual < o.stock_optimo
          AND o.demanda_promedio > 0 AND COALESCE(a.en_lista_negra, 0) = 0
        ORDER BY dias_cobertura ASC
    """)
    if df.empty:
        await update.message.reply_text("✅ Sin urgentes al momento.")
        return
    df = df.head(top)
    lineas = [f"🟡 *Top {top} Urgentes* (bajo mínimo)\n"]
    for _, r in df.iterrows():
        desc = str(r.get("descripcion") or r.get("codigo","?"))[:30]
        dias = int(r.get("dias_cobertura") or 0)
        stk = int(r.get("stock_actual") or 0)
        emoji = "🔴" if dias < 7 else "🟡"
        lineas.append(f"{emoji} `{r['codigo']}` {desc}\n  Stock: {stk}u | Cobertura: {dias} días")
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


# ── /kpis ─────────────────────────────────────────────────────────────────────────────
@auth_required
async def cmd_kpis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_resumen_stats, get_config as _gcfg
    stats = get_resumen_stats()
    tasa = float(_gcfg("tasa_usd_ars", float) or 1420)
    df_inv = query_to_df("""
        SELECT SUM((stock_optimo - stock_actual) * costo_reposicion) as total_usd
        FROM optimizacion
        WHERE stock_actual < stock_optimo AND demanda_promedio > 0 AND costo_reposicion > 0
    """)
    inversion = float(df_inv.iloc[0]["total_usd"] or 0) if not df_inv.empty else 0
    texto = (
        f"📊 *KPIs — {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n\n"
        f"📦 Artículos activos: *{stats.get('total_articulos',0):,}*\n"
        f"🔴 Sin stock: *{stats.get('sin_stock',0)}*\n"
        f"🟡 Bajo mínimo: *{stats.get('bajo_minimo',0)}*\n"
        f"💰 Inversión requerida: *USD {inversion:,.0f}* = *${inversion*tasa:,.0f} ARS*\n"
        f"💵 Tasa USD/ARS: *${tasa:,.0f}*\n"
        f"🕐 Última importación: {stats.get('ultima_importacion','—')}"
    )
    kb = [[InlineKeyboardButton("🔄 Actualizar", callback_data="menu_resumen"),
           InlineKeyboardButton("🔴 Críticos", callback_data="menu_quiebres")]]
    await update.message.reply_text(texto, parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(kb))


# ── /lotes ────────────────────────────────────────────────────────────────────────────
@auth_required
async def cmd_lotes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = query_to_df("""
        SELECT l.nombre, l.proveedor, l.tope_usd, l.total_usd, l.estado,
               COUNT(i.id) as items
        FROM pedidos_lotes l
        LEFT JOIN pedidos_items i ON l.id=i.lote_id
        GROUP BY l.id ORDER BY l.fecha_creado DESC LIMIT 5
    """)
    if df.empty:
        await update.message.reply_text("📭 Sin lotes. Creá uno desde la app web.")
        return
    lineas = ["🛒 *Lotes recientes*\n"]
    for _, r in df.iterrows():
        e = {"borrador":"📝","enviado":"📤","confirmado":"✅","en_transito":"✈️"}.get(str(r.get("estado","")),"📋")
        lineas.append(
            f"{e} *{r.get('nombre','')}*\n"
            f"  {r.get('proveedor','')} | {r.get('items',0)} ítems | "
            f"USD {float(r.get('total_usd') or 0):,.0f}"
        )
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


# ── Callbacks de sinstock ─────────────────────────────────────────────────────────────
async def _mostrar_sinstock(message, con_mov: bool = None):
    if con_mov is True:
        df = query_to_df("""
            SELECT o.codigo, COALESCE(a.descripcion,o.descripcion) as descripcion, o.demanda_promedio
            FROM optimizacion o LEFT JOIN articulos a ON o.codigo=a.codigo
            WHERE o.stock_actual=0 AND o.demanda_promedio>0
            ORDER BY o.demanda_promedio DESC LIMIT 20
        """)
        titulo = "🔴 *Sin stock CON movimiento*"
    elif con_mov is False:
        df = query_to_df("""
            SELECT o.codigo, COALESCE(a.descripcion,o.descripcion) as descripcion, o.demanda_promedio
            FROM optimizacion o LEFT JOIN articulos a ON o.codigo=a.codigo
            WHERE o.stock_actual=0 AND (o.demanda_promedio=0 OR o.demanda_promedio IS NULL)
            ORDER BY a.descripcion LIMIT 20
        """)
        titulo = "⚪ *Sin stock SIN movimiento*"
    else:
        df = query_to_df("""
            SELECT o.codigo, COALESCE(a.descripcion,o.descripcion) as descripcion, o.demanda_promedio
            FROM optimizacion o LEFT JOIN articulos a ON o.codigo=a.codigo
            WHERE o.stock_actual=0 ORDER BY o.demanda_promedio DESC LIMIT 20
        """)
        titulo = "🔴 *Sin stock — todos*"
    if df.empty:
        await message.reply_text("✅ Sin artículos en esa categoría.")
        return
    lineas = [titulo + "\n"]
    for _, r in df.iterrows():
        desc = str(r.get("descripcion") or r.get("codigo","?"))[:35]
        dem = float(r.get("demanda_promedio") or 0)
        suffix = f" | {dem:.1f}/mes" if con_mov is True and dem > 0 else ""
        lineas.append(f"`{r['codigo']}` {desc}{suffix}")
    await message.reply_text("\n".join(lineas), parse_mode="Markdown")




# ── /borrador — Agregar modelos al borrador de pedido ─────────────────────────
@auth_required
async def cmd_borrador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agrega un modelo al borrador de pedido desde Telegram."""
    args = context.args
    if not args:
        # Sin args: mostrar resumen del borrador actual
        df = query_to_df("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN estado='confirmado' THEN 1 ELSE 0 END) as confirmados,
                   SUM(CASE WHEN estado='pendiente' THEN 1 ELSE 0 END) as pendientes,
                   SUM(CASE WHEN estado='confirmado' THEN subtotal_usd ELSE 0 END) as total_usd
            FROM borrador_pedido WHERE estado != 'descartado'
        """)
        if df.empty or int(df.iloc[0].get("total") or 0) == 0:
            await update.message.reply_text(
                "📝 *Borrador vacío*\n\n"
                "Usá `/borrador moto g13` para agregar un modelo.\n"
                "Podés escribir el nombre como lo conocés.",
                parse_mode="Markdown"
            )
        else:
            r = df.iloc[0]
            total = int(r.get("total") or 0)
            conf  = int(r.get("confirmados") or 0)
            pend  = int(r.get("pendientes") or 0)
            usd   = float(r.get("total_usd") or 0)
            kb = [[
                InlineKeyboardButton("📋 Ver borrador completo", callback_data="borrador_ver"),
                InlineKeyboardButton("🔍 Hacer matching", callback_data="borrador_matching"),
            ]]
            await update.message.reply_text(
                f"📝 *Borrador de pedido*\n\n"
                f"📦 Total ítems: *{total}*\n"
                f"✅ Confirmados: *{conf}*\n"
                f"⏳ Pendientes: *{pend}*\n"
                f"💰 Total: *USD {usd:,.0f}*\n\n"
                f"Usá `/borrador [modelo]` para agregar más.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        return

    # Con args: buscar el modelo y agregar
    query = " ".join(args).strip()
    _set_estado(update.effective_user.id, "borrador_cant", {"query": query})
    
    # Buscar candidatos mecánicos
    from rapidfuzz import fuzz, process as rfp
    df_arts = query_to_df("""
        SELECT a.codigo, a.descripcion, COALESCE(s.stock,0) as stock,
               COALESCE(p.lista_1,0) as precio_usd
        FROM articulos a
        LEFT JOIN (SELECT codigo, SUM(stock) as stock FROM stock_snapshots
                   JOIN (SELECT codigo,MAX(fecha) mf FROM stock_snapshots GROUP BY codigo) lx
                   ON stock_snapshots.codigo=lx.codigo AND stock_snapshots.fecha=lx.mf
                   GROUP BY codigo) s ON a.codigo=s.codigo
        LEFT JOIN precios p ON a.codigo=p.codigo
        WHERE UPPER(a.descripcion) LIKE 'MODULO%'
          AND COALESCE(a.en_lista_negra,0)=0
    """)
    df_arts = df_arts[df_arts["codigo"].apply(lambda c: str(c)[0:1].isdigit())]

    if df_arts.empty:
        # Guardar como pendiente sin código
        from database import execute_query as _eq
        _eq("""INSERT INTO borrador_pedido
               (texto_original, descripcion, estado, origen, sesion_id)
               VALUES (?,?,'pendiente','telegram',?)""",
            (query, query.upper(), str(update.effective_user.id)), fetch=False)
        await update.message.reply_text(
            f"📝 *{query}* agregado como pendiente.\n"
            "Completá el código desde la app web.",
            parse_mode="Markdown"
        )
        return

    descs = df_arts["descripcion"].tolist()
    matches = rfp.extract(query.upper(), descs, scorer=fuzz.token_set_ratio,
                           limit=5, score_cutoff=40)

    if not matches:
        from database import execute_query as _eq
        _eq("""INSERT INTO borrador_pedido
               (texto_original, descripcion, estado, origen, sesion_id)
               VALUES (?,?,'pendiente','telegram',?)""",
            (query, query.upper(), str(update.effective_user.id)), fetch=False)
        await update.message.reply_text(
            f"❓ No encontré mecánico para *{query}*.\n"
            "Agregado como pendiente — completá desde la app.",
            parse_mode="Markdown"
        )
        return

    # Mostrar candidatos como botones
    lineas = [f"🔍 Encontré {len(matches)} opciones para _{query}_:\n"]
    keyboard = []
    for desc, score, idx in matches:
        row = df_arts.iloc[idx]
        stk = int(row.get("stock") or 0)
        precio = float(row.get("precio_usd") or 0)
        stk_e = "🔴" if stk == 0 else ("🟡" if stk < 5 else "🟢")
        lineas.append(f"{stk_e} `{row['codigo']}` {desc[:35]} | USD {precio:.0f}")
        keyboard.append([InlineKeyboardButton(
            f"{row['codigo']} — {desc[:30]}",
            callback_data=f"bor_add_{row['codigo']}_{query[:20]}"
        )])
    keyboard.append([InlineKeyboardButton("📝 Agregar sin código", callback_data=f"bor_sinc_{query[:30]}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])

    await update.message.reply_text(
        "\n".join(lineas),
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
        conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "roker_nexus.db"))
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


def _get_tasa_str() -> str:
    """Retorna la tasa USD/ARS como string formateado."""
    try:
        import sqlite3 as _sq, os as _os
        db = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "roker_nexus.db")
        conn = _sq.connect(db)
        row = conn.execute("SELECT usd_ars FROM tasas_cambio ORDER BY fecha DESC LIMIT 1").fetchone()
        conn.close()
        return f"${row[0]:,.0f}" if row else "no registrado"
    except Exception:
        return "no registrado"




@auth_required
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra todos los comandos disponibles."""
    texto = (
        "⚡ *ROKER NEXUS — Comandos*\n\n"
        "📦 *Stock e inventario*\n"
        "/stock [modelo] — Stock, precios, tránsito\n"
        "/precio [modelo] — Lista 1 USD/ARS + ML\n"
        "/quiebres — Artículos en quiebre\n"
        "/sinstock — Sin stock con demanda\n"
        "/criticos [N] — Top N críticos\n"
        "/urgentes [N] — Top N bajo mínimo\n"
        "/pedido [código] — Estado de pedido\n\n"
        "✈️ *Tránsito*\n"
        "/transito — Lista completa en tránsito\n"
        "/lotes — Últimos lotes de compra\n\n"
        "📊 *Reportes*\n"
        "/kpis — KPIs ejecutivos\n"
        "/resumen — Resumen del sistema\n\n"
        "🤖 *IA*\n"
        "/ia [pregunta] — Consultar IA activa\n"
        "/ia2 [pregunta] — Paralelo todos los IAs\n\n"
        "⚙️ *Configuración*\n"
        "/tasa [número] — Actualizar USD/ARS\n"
        "/tasa RMB [número] — Actualizar RMB\n"
        "/config — Ver configuración\n"
        "/negra — Lista negra\n\n"
        "📝 *Pedidos*\n"
        "/borrador [modelo] — Agregar al borrador\n\n"
        "_También podés escribir cualquier modelo o código directamente._"
    )
    kb = [[InlineKeyboardButton("🔙 Menú principal", callback_data="menu_volver")]]
    await update.message.reply_text(
        texto, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

def main():
    if not TELEGRAM_TOKEN:
        print("⚠️  TELEGRAM_TOKEN no configurado en .env")
        return

    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
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
    app.add_handler(CommandHandler("tasa",      cmd_tasa))
    app.add_handler(CommandHandler("ia2",       cmd_ia2))
    app.add_handler(CommandHandler("borrador",  cmd_borrador))
    app.add_handler(CommandHandler("criticos",  cmd_criticos))
    app.add_handler(CommandHandler("urgentes",  cmd_urgentes))
    app.add_handler(CommandHandler("kpis",      cmd_kpis))
    app.add_handler(CommandHandler("lotes",     cmd_lotes))
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
            from version import get_nota_deploy, APP_VERSION
            # Solo notificar si cambió la versión (evitar spam en reinicios)
            import sqlite3 as _sq, os as _os_n
            _db_n = _os_n.path.join(_os_n.path.dirname(_os_n.path.abspath(__file__)), "roker_nexus.db")
            try:
                _conn_n = _sq.connect(_db_n)
                _row_n = _conn_n.execute(
                    "SELECT valor FROM configuracion WHERE clave='ultima_version_notif'"
                ).fetchone()
                _ultima = _row_n[0] if _row_n else ""
                _conn_n.close()
            except Exception:
                _ultima = ""

            if _ultima == APP_VERSION:
                print(f"ℹ️  Versión {APP_VERSION} ya notificada, omitiendo")
                return

            texto = get_nota_deploy()
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            r = requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": texto,
                "parse_mode": "Markdown"
            }, timeout=10)
            if r.status_code == 200:
                # Guardar versión notificada
                try:
                    _conn2 = _sq.connect(_db_n)
                    _conn2.execute(
                        "INSERT OR REPLACE INTO configuracion (clave, valor, descripcion) VALUES (?,?,?)",
                        ("ultima_version_notif", APP_VERSION, "Última versión notificada por Telegram")
                    )
                    _conn2.commit()
                    _conn2.close()
                except Exception:
                    pass
                print(f"✅ Notificación deploy {APP_VERSION} enviada")
            else:
                print(f"⚠️ Telegram respondió: {r.status_code} — {r.text[:200]}")
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
