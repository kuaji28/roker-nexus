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
        await update.message.reply_text("Uso: /stock [código]\nEj: /stock 2401251672")
        return

    codigo = args[0].strip().upper()
    conn = sqlite3.connect("roker_nexus.db")
    cur = conn.execute("""
        SELECT s.deposito, s.stock, s.stock_minimo
        FROM stock_snapshots s
        JOIN (
            SELECT deposito, MAX(fecha) as mf FROM stock_snapshots
            WHERE codigo=? GROUP BY deposito
        ) lx ON s.deposito=lx.deposito AND s.fecha=lx.mf
        WHERE s.codigo=?
    """, (codigo, codigo))
    rows = cur.fetchall()

    # Descripción
    cur2 = conn.execute("SELECT descripcion, marca FROM articulos WHERE codigo=?", (codigo,))
    art = cur2.fetchone()
    conn.close()

    if not rows:
        await update.message.reply_text(f"❓ Código `{codigo}` no encontrado.", parse_mode="Markdown")
        return

    desc = f"{art[0]} ({art[1]})" if art else codigo
    lineas = [f"📦 *{desc}*\n`{codigo}`\n"]
    for deposito, stock, minimo in rows:
        icono = color_stock(stock, minimo)
        lineas.append(f"{icono} {deposito}: *{int(stock)}* uds (min: {int(minimo)})")

    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


# ── /precio ───────────────────────────────────────────────────
@auth_required
async def cmd_precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /precio [código]")
        return

    codigo = args[0].strip().upper()
    conn = sqlite3.connect("roker_nexus.db")
    cur = conn.execute("""
        SELECT lista_1, lista_4, moneda FROM precios
        WHERE codigo=? ORDER BY fecha DESC LIMIT 1
    """, (codigo,))
    row = cur.fetchone()
    cur2 = conn.execute("SELECT descripcion FROM articulos WHERE codigo=?", (codigo,))
    art = cur2.fetchone()
    conn.close()

    if not row:
        await update.message.reply_text(f"❓ Sin precios para `{codigo}`.", parse_mode="Markdown")
        return

    desc = art[0] if art else codigo
    tasa = _get_tasa()
    l1, l4 = row[0] or 0, row[1] or 0
    texto = (
        f"💰 *{desc}*\n`{codigo}`\n\n"
        f"📋 Lista 1 (mayorista): *{fmt_usd(l1)}* = ${l1*tasa:,.0f} ARS\n"
        f"🛒 Lista 4 (ML): *{fmt_usd(l4)}* = ${l4*tasa:,.0f} ARS"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


# ── /quiebres ─────────────────────────────────────────────────
@auth_required
async def cmd_quiebres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = get_quiebres(umbral=0)
    if df.empty:
        await update.message.reply_text("✅ No hay quiebres de stock en cero.")
        return

    lineas = [f"🔴 *{len(df)} artículos sin stock*\n"]
    for _, row in df.head(10).iterrows():
        desc = row.get("descripcion") or row.get("codigo", "?")
        dep = row.get("deposito", "")
        lineas.append(f"• {desc[:30]} ({dep})")

    keyboard = [[
        InlineKeyboardButton("🔍 Ver todos", callback_data="ver_quiebres"),
        InlineKeyboardButton("🤖 Analizar con IA", callback_data="ia_quiebres"),
    ]]
    await update.message.reply_text(
        "\n".join(lineas),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


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
        await update.message.reply_text("Uso: /negra [código] [motivo opcional]")
        return

    codigo = args[0].strip().upper()
    motivo = " ".join(args[1:]) if len(args) > 1 else ""

    keyboard = [[
        InlineKeyboardButton(f"⛔ Confirmar: agregar {codigo}", callback_data=f"negra_ok_{codigo}_{motivo}"),
        InlineKeyboardButton("❌ Cancelar", callback_data="negra_cancel"),
    ]]
    await update.message.reply_text(
        f"¿Agregar `{codigo}` a lista negra?\nMotivo: _{motivo or 'no especificado'}_",
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

    if data == "ia_quiebres":
        await query.message.reply_text("🤖 Analizando quiebres...")
        from modules.ia_engine import motor_ia
        df = get_quiebres(umbral=0)
        resp = motor_ia.analizar_quiebres(df)
        await query.message.reply_text(resp[:4000])

    elif data.startswith("negra_ok_"):
        parts = data.split("_", 4)
        if len(parts) >= 4:
            codigo = parts[3]
            motivo = parts[4] if len(parts) > 4 else ""
            agregar_a_lista_negra(codigo, motivo)
            await query.message.edit_text(f"⛔ `{codigo}` agregado a lista negra.", parse_mode="Markdown")

    elif data == "negra_cancel":
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
