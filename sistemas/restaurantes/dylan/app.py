"""
Restaurante Peruano Dylan - Sistema de Gestión
Pollería & Cevichería
"""
import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import hashlib
import os
import uuid
from datetime import datetime, timedelta
from contextlib import contextmanager
try:
    from streamlit_autorefresh import st_autorefresh
    _HAS_AUTOREFRESH = True
except ImportError:
    _HAS_AUTOREFRESH = False
# ─── CONFIG ────────────────────────────────────────────────────────────────────
# En Railway/nube usa /data/dylan.db (volumen persistente), local usa dylan.db
_data_dir = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_data_dir, "dylan.db")
st.set_page_config(
    page_title="DYLAN - Restaurante Peruano",
    page_icon="🍗",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# Force-hide sidebar completely — navigation is now on top
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)
# ─── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global brand colors */
:root {
    --dylan-burgundy: #5C1A1B;
    --dylan-dark: #3A0F10;
    --dylan-gold: #D4A843;
    --dylan-light-gold: #F5E6C8;
    --dylan-cream: #FFF8EC;
    --dylan-green: #2E7D32;
    --dylan-yellow-alert: #F9A825;
    --dylan-red-alert: #C62828;
}
/* Header styling */
.dylan-header {
    background: linear-gradient(135deg, #5C1A1B 0%, #3A0F10 100%);
    color: #D4A843;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 1rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.dylan-header h1 {
    font-size: 2.5rem;
    margin: 0;
    letter-spacing: 6px;
    font-weight: 800;
    color: #D4A843 !important;
}
.dylan-header p {
    color: #F5E6C8;
    margin: 0.2rem 0 0 0;
    font-size: 0.95rem;
    letter-spacing: 2px;
}
/* Menu item cards */
.menu-item-card {
    background: #FFF8EC;
    border: 2px solid #D4A843;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: all 0.2s;
}
.menu-item-card:hover {
    border-color: #5C1A1B;
    box-shadow: 0 2px 8px rgba(92,26,27,0.2);
}
.item-name { font-weight: 600; color: #3A0F10; font-size: 0.95rem; }
.item-price { font-weight: 700; color: #5C1A1B; font-size: 1.1rem; }
/* Category header */
.cat-header {
    background: linear-gradient(90deg, #5C1A1B, #7A2526);
    color: #D4A843;
    padding: 0.6rem 1.2rem;
    border-radius: 8px;
    font-weight: 700;
    font-size: 1.1rem;
    margin: 1rem 0 0.5rem 0;
    letter-spacing: 1px;
}
/* Big action buttons */
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    padding: 0.5rem 1.5rem;
    transition: all 0.2s;
}
/* Order status badges */
.status-pendiente {
    background: #FFF3E0; color: #E65100;
    padding: 3px 10px; border-radius: 12px;
    font-weight: 600; font-size: 0.85rem;
}
.status-preparando {
    background: #E3F2FD; color: #1565C0;
    padding: 3px 10px; border-radius: 12px;
    font-weight: 600; font-size: 0.85rem;
}
.status-listo {
    background: #E8F5E9; color: #2E7D32;
    padding: 3px 10px; border-radius: 12px;
    font-weight: 600; font-size: 0.85rem;
}
.status-entregado {
    background: #F3E5F5; color: #7B1FA2;
    padding: 3px 10px; border-radius: 12px;
    font-weight: 600; font-size: 0.85rem;
}
.status-cancelado {
    background: #FFEBEE; color: #C62828;
    padding: 3px 10px; border-radius: 12px;
    font-weight: 600; font-size: 0.85rem;
}
/* Kitchen timer colors */
.timer-green { color: #2E7D32; font-weight: 700; }
.timer-yellow { color: #F9A825; font-weight: 700; }
.timer-red { color: #C62828; font-weight: 700; font-size: 1.1rem; }
/* Remove Streamlit default top spacing */
header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
.block-container {
    padding-top: 0 !important;
    padding-bottom: 1rem !important;
}
/* Mobile-friendly — optimized for mozo on phone */
@media (max-width: 768px) {
    .dylan-header h1 { font-size: 1.5rem; letter-spacing: 3px; }
    .dylan-header p { font-size: 0.7rem; }
    .dylan-header { padding: 0.5rem 1rem; margin-bottom: 0.5rem; }
    /* Bigger touch targets on mobile */
    .stButton > button {
        min-height: 52px !important;
        font-size: 1rem !important;
        padding: 0.6rem 0.8rem !important;
    }
    /* Tighter spacing */
    .block-container { padding: 0.5rem 0.8rem !important; }
    /* Category radio as pills */
    .stRadio > div { gap: 0.3rem !important; }
    .stRadio label { font-size: 0.85rem !important; }
}
/* Login card */
.login-box {
    max-width: 400px;
    margin: 2rem auto;
    padding: 2rem;
    background: white;
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    border-top: 4px solid #D4A843;
}
/* Ticket styling for thermal printer */
.ticket-preview {
    font-family: 'Courier New', monospace;
    font-size: 12px;
    background: white;
    color: black;
    padding: 15px;
    border: 2px dashed #ccc;
    max-width: 280px;
    margin: 0 auto;
    line-height: 1.4;
    white-space: pre-wrap;
}
/* Hide Streamlit menu and footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
# ─── DATABASE ──────────────────────────────────────────────────────────────────
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'dueno', 'mozo')),
            display_name TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_type TEXT NOT NULL DEFAULT 'mesa'
                CHECK(order_type IN ('mesa','mostrador','para_llevar')),
            table_num TEXT NOT NULL DEFAULT '',
            customer_name TEXT DEFAULT '',
            mozo_id INTEGER NOT NULL,
            status TEXT DEFAULT 'preparando'
                CHECK(status IN ('pendiente','preparando','listo','entregado','cancelado')),
            notes TEXT DEFAULT '',
            total REAL DEFAULT 0,
            payment_method TEXT DEFAULT ''
                CHECK(payment_method IN ('','efectivo','transferencia','pendiente')),
            payment_amount REAL DEFAULT 0,
            payment_change REAL DEFAULT 0,
            paid INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mozo_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cash_registers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opened_by INTEGER NOT NULL,
            opening_amount REAL NOT NULL DEFAULT 0,
            closing_amount_real REAL DEFAULT 0,
            closing_amount_expected REAL DEFAULT 0,
            difference REAL DEFAULT 0,
            total_cash_sales REAL DEFAULT 0,
            total_transfer_sales REAL DEFAULT 0,
            total_pending REAL DEFAULT 0,
            total_change_given REAL DEFAULT 0,
            orders_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open' CHECK(status IN ('open','closed')),
            notes TEXT DEFAULT '',
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (opened_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()
def get_setting(key, default=""):
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default
def set_setting(key, value):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
def get_num_tables():
    return int(get_setting("num_tables", "10"))
def seed_data():
    with get_db() as conn:
        # Default settings — always ensure these exist
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('num_tables', '10')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('restaurant_name', 'DYLAN')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_price', '10000')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_active', '1')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_description', 'Menú del Día (consultar plato)')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delivery_fee', '100')")
        # Menú del Día ítems 2, 3, 4
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_2_active', '1')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_2_price', '10000')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_2_description', 'Ítem 2 del Día (consultar)')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_3_active', '1')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_3_price', '10000')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_3_description', 'Ítem 3 del Día (consultar)')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_4_active', '1')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_4_price', '10000')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_4_description', 'Ítem 4 del Día (consultar)')")
        # Master admin (Roker — llave maestra, no se puede borrar ni desactivar)
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, plain_pw, role, display_name) VALUES (?,?,?,?,?)",
            ("roker", hash_pw("99107001"), "99107001", "admin", "Roker (Admin)"),
        )
        # Default users — always ensure these exist (INSERT OR IGNORE is safe)
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, plain_pw, role, display_name) VALUES (?,?,?,?,?)",
            ("dylan", hash_pw("dylan2024"), "dylan2024", "dueno", "Dylan (Dueño)"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, plain_pw, role, display_name) VALUES (?,?,?,?,?)",
            ("mozo1", hash_pw("mozo1"), "mozo1", "mozo", "Mozo 1"),
        )
        # Fill plain_pw for existing users that don't have it saved yet
        conn.execute("UPDATE users SET plain_pw='(resetear desde Ajustes)' WHERE (plain_pw IS NULL OR plain_pw='') AND username NOT IN ('roker','dylan','mozo1')")
        # Categories and items
        menu = {
            "POLLO A LA BRASA": [
                ("Pollo Entero + Papas + Ensalada + Salsas", 32000),
                ("1/2 Pollo + Papas + Ensalada + Salsas", 22000),
                ("1/4 Pollo + Papas + Ensalada + Salsas", 14500),
            ],
            "PROMOS": [
                ("Promo Familiar (1 pollo entero + fritas + ensalada + arroz chaufa + gaseosa grande + aderezos)", 47000),
                ("Mega Broaster (1 broaster entero + fritas + ensalada + arroz + gaseosa grande + aderezos)", 42500),
                ("Mega Mostrito (1 broaster entero + fritas + ensalada + arroz chaufa + gaseosa grande + aderezos)", 47000),
            ],
            "PLATOS CRIOLLOS": [
                ("Lomo Salteado de Pollo", 17000),
                ("Lomo Salteado de Carne o Mixto", 17000),
                ("Arroz Chaufa de Pollo", 17000),
                ("Arroz Chaufa de Carne o Mixto", 17000),
                ("Tallarín Salteado de Pollo", 17000),
                ("Tallarín Salteado de Carne o Mixto", 17000),
                ("Aeropuerto de Pollo", 17500),
                ("Aeropuerto de Carne o Mixto", 17500),
                ("Pollo Broaster", 16000),
                ("Bistec a lo Pobre", 17500),
                ("Tallarines Verdes c/Churrasco", 17000),
                ("Chicharrón de Pollo", 18000),
                ("Churrasco c/Fritas y Ensalada", 16000),
                ("Salchipapa Completa", 14000),
                ("Mostrito", 17000),
                ("Pollada", 17000),
                ("Tallarines Verdes c/Pollo Frito", 17000),
                ("Lomo a lo Pobre", 17000),
            ],
            "PESCADOS Y MARISCOS": [
                ("Ceviche con Chicharrón", 29000),
                ("Ceviche de Pescado", 23000),
                ("Ceviche Mixto", 28000),
                ("Chicharrón de Pescado", 23000),
                ("Jalea Mixta", 27000),
                ("Rabas", 26000),
                ("Arroz con Mariscos", 27000),
                ("Chaufa de Mariscos", 26000),
                ("Leche de Tigre", 16000),
                ("Parihuela", 30000),
                ("Sudado de Mero", 22000),
                ("Filete de Pescado c/Arroz y Mandioca", 17000),
            ],
            "GUARNICIONES": [
                ("Ensalada Mixta", 7000),
                ("Ensalada Criolla", 5000),
                ("Porción de Papas Fritas", 12000),
                ("Porción de Arroz", 7000),
                ("Porción de Cancha", 2000),
                ("Huevo Frito Extra", 2000),
            ],
            "BEBIDAS CON ALCOHOL": [
                ("Brahma", 6500),
                ("Stella", 8000),
                ("Corona Chica", 4000),
                ("Corona Grande", 16500),
                ("Brahma Lata", 3500),
                ("Miller", 7500),
            ],
            "BEBIDAS SIN ALCOHOL": [
                ("Coca-Cola 500ml", 3000),
                ("Sprite 500ml", 3000),
                ("Fanta 500ml", 3000),
                ("Coca-Cola 1.5L", 14000),
                ("Levite", 4500),
                ("Sprite 1.5L", 4500),
            ],
            "VINOS": [
                ("Alma Mora", 12000),
                ("La Colonia", 12000),
                ("Uxmal Malbec", 12000),
                ("Del Fin del Mundo", 12000),
                ("Postillón", 12000),
                ("Don Valentín", 10000),
            ],
        }
        # Only seed menu if no categories exist yet
        cat_count = conn.execute("SELECT COUNT(*) c FROM categories").fetchone()["c"]
        if cat_count == 0:
            for sort_idx, (cat_name, items) in enumerate(menu.items()):
                conn.execute(
                    "INSERT INTO categories (name, sort_order) VALUES (?,?)",
                    (cat_name, sort_idx),
                )
                cat_id = conn.execute(
                    "SELECT id FROM categories WHERE name=?", (cat_name,)
                ).fetchone()["id"]
                for item_name, price in items:
                    conn.execute(
                        "INSERT INTO menu_items (category_id, name, price) VALUES (?,?,?)",
                        (cat_id, item_name, price),
                    )
# ─── ENCARGADO PERMISSIONS ─────────────────────────────────────────────────────
ENCARGADO_PERMS = {
    "cocina":          "👨‍🍳 Vista Cocina",
    "nuevo_pedido":    "🛒 Tomar Pedidos",
    "todos_pedidos":   "📦 Todos los Pedidos",
    "cobrar":          "💰 Cobrar pedidos",
    "caja":            "💰 Ver Caja",
    "reporte":         "📄 Reporte del Día",
    "historial":       "🧾 Historial de Tickets",
    "editar_menu":     "🍽️ Editar Menú",
    "gestionar_mozos": "👥 Gestionar Mozos",
}
def has_permission(permission: str) -> bool:
    """Check if the current logged-in user has a given permission.
    - admin / dueno  → always True
    - encargado      → True unless explicitly disabled in user_permissions
    - mozo           → always False (mozos use fixed minimal nav)
    """
    user = st.session_state.get("user") or {}
    role = user.get("role", "mozo")
    if role in ("admin", "dueno"):
        return True
    if role != "encargado":
        return False
    uid = user.get("id")
    if not uid:
        return False
    with get_db() as conn:
        row = conn.execute(
            "SELECT allowed FROM user_permissions WHERE user_id=? AND permission=?",
            (uid, permission),
        ).fetchone()
    return bool(row["allowed"]) if row else True  # default: allowed
# ─── HELPERS ───────────────────────────────────────────────────────────────────
def fmt_price(price: float) -> str:
    return f"${price:,.0f}".replace(",", ".")
def get_unprinted_count() -> int:
    """Count of today's orders that haven't been printed yet (excl. cancelled)."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        row = conn.execute("""
            SELECT COUNT(*) FROM orders
            WHERE date(created_at) = ?
              AND printed_at IS NULL
              AND status != 'cancelado'
        """, (today,)).fetchone()
    return row[0] if row else 0
def render_bell_sound(current_count: int):
    """
    Plays a notification beep when unprinted order count increases.
    Tracks previous count in session state. Renders as a 0-height component.
    """
    prev_key = "_bell_prev_count"
    prev = st.session_state.get(prev_key, current_count)
    should_beep = current_count > prev
    st.session_state[prev_key] = current_count
    if should_beep:
        # Web Audio API beep — no external assets needed
        components.html("""<script>
(function() {
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    function beep(freq, start, dur) {
      var o = ctx.createOscillator();
      var g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = freq;
      o.type = 'sine';
      g.gain.setValueAtTime(0.4, ctx.currentTime + start);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
      o.start(ctx.currentTime + start);
      o.stop(ctx.currentTime + start + dur + 0.05);
    }
    beep(880, 0,    0.12);
    beep(880, 0.15, 0.12);
    beep(1100, 0.3, 0.2);
  } catch(e) {}
})();
</script>""", height=0)
def get_menu():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT mi.id, mi.name, mi.price, mi.active, mi.avg_cook_minutes,
                   c.name as category, c.sort_order, c.id as cat_id
            FROM menu_items mi
            JOIN categories c ON mi.category_id = c.id
            ORDER BY c.sort_order, mi.name
        """).fetchall()
    return [dict(r) for r in rows]
def get_categories():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
    return [dict(r) for r in rows]
def display_item_name(name: str) -> str:
    """Convert internal names to display names."""
    if name == "__menu_del_dia__":
        return get_setting("menu_del_dia_description", "Menú del Día")
    if name == "__mdd_2__":
        return get_setting("menu_del_dia_2_description", "Ítem 2 del Día")
    if name == "__mdd_3__":
        return get_setting("menu_del_dia_3_description", "Ítem 3 del Día")
    if name == "__mdd_4__":
        return get_setting("menu_del_dia_4_description", "Ítem 4 del Día")
    return name
def status_badge(status: str) -> str:
    return f'<span class="status-{status}">{status.upper()}</span>'
def time_color(minutes: float) -> str:
    if minutes < 15:
        return "timer-green"
    elif minutes < 30:
        return "timer-yellow"
    return "timer-red"
def generate_ticket_text(order_id: int) -> str:
    with get_db() as conn:
        order = conn.execute("""
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE o.id = ?
        """, (order_id,)).fetchone()
        items = conn.execute("""
            SELECT oi.*, mi.name as item_name
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
        """, (order_id,)).fetchall()
    if not order:
        return ""
    w = 32  # 58mm printer ~ 32 chars
    sep = "-" * w
    dsep = "=" * w
    type_labels = {"mesa": "MESA", "mostrador": "BARRA", "barra": "BARRA", "para_llevar": "PARA LLEVAR/DELIVERY"}
    lines = []
    lines.append("DYLAN".center(w))
    lines.append("Polleria & Cevicheria".center(w))
    lines.append(dsep)
    lines.append(f"Pedido: #{order['id']}")
    order_type = order['order_type'] if 'order_type' in order.keys() else 'mesa'
    lines.append(f"Tipo: {type_labels.get(order_type, 'MESA')}")
    lines.append(f"Ubic: {order['table_num']}")
    if order["customer_name"]:
        lines.append(f"Cliente: {order['customer_name']}")
    lines.append(f"Mozo: {order['mozo_name']}")
    lines.append(f"Fecha: {order['created_at'][:16]}")
    lines.append(dsep)
    for it in items:
        name = it["item_name"]
        if name == "__menu_del_dia__":
            name = "Menú del Día"
        qty = it["quantity"]
        price = it["unit_price"] * qty
        line1 = f"{qty}x {name}"
        line2 = f"   {fmt_price(price)}"
        lines.append(line1)
        lines.append(line2)
        if it["notes"]:
            lines.append(f"   >> {it['notes']}")
    lines.append(sep)
    lines.append(f"{'TOTAL:':>{w-12}} {fmt_price(order['total']):>10}")
    lines.append(dsep)
    # Payment info
    pay_method = order['payment_method'] if 'payment_method' in order.keys() else ''
    if pay_method == 'efectivo':
        lines.append(f"PAGO: EFECTIVO")
        pay_amt = order['payment_amount'] if 'payment_amount' in order.keys() else 0
        pay_chg = order['payment_change'] if 'payment_change' in order.keys() else 0
        if pay_amt > 0:
            lines.append(f"Recibido: {fmt_price(pay_amt)}")
            lines.append(f"Vuelto:   {fmt_price(pay_chg)}")
    elif pay_method == 'transferencia':
        lines.append(f"PAGO: TRANSFERENCIA")
    elif pay_method == 'pendiente':
        lines.append(f"*** PAGO PENDIENTE ***")
    if order["notes"]:
        lines.append(sep)
        lines.append(f"NOTAS: {order['notes']}")
    lines.append(sep)
    lines.append("Gracias por su preferencia!".center(w))
    lines.append("")
    return "\n".join(lines)
def generate_receipt_html(order_id: int) -> str:
    """Generate a print-ready HTML receipt formatted for 58mm thermal paper."""
    with get_db() as conn:
        order = conn.execute("""
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE o.id = ?
        """, (order_id,)).fetchone()
        items = conn.execute("""
            SELECT oi.*, mi.name as item_name
            FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
        """, (order_id,)).fetchall()
    if not order:
        return "<p>Pedido no encontrado.</p>"
    order = dict(order)
    type_labels = {"mesa": "MESA", "mostrador": "BARRA", "barra": "BARRA", "para_llevar": "PARA LLEVAR"}
    def price(v):
        return f"${int(v):,}".replace(",", ".")
    _mdd_names = {
        "__menu_del_dia__": "Menú del Día",
        "__mdd_2__": get_setting("menu_del_dia_2_description", "Ítem 2 del Día"),
        "__mdd_3__": get_setting("menu_del_dia_3_description", "Ítem 3 del Día"),
        "__mdd_4__": get_setting("menu_del_dia_4_description", "Ítem 4 del Día"),
    }
    tipo = type_labels.get(order.get("order_type", "mesa"), "MESA")
    items_html = ""
    for it in items:
        name = _mdd_names.get(it["item_name"], it["item_name"]).upper()
        subtotal = price(it["unit_price"] * it["quantity"])
        items_html += f"""
<table class="item"><tr>
  <td class="qty">{it['quantity']}x</td>
  <td class="name">{name}</td>
  <td class="item-price">{subtotal}</td>
</tr></table>"""
        if it["notes"]:
            items_html += f'<div class="nota">** {it["notes"]}</div>'
    pay_lines = ""
    pm = order.get("payment_method", "")
    if pm == "efectivo":
        pay_lines = "EFECTIVO"
        if order.get("payment_amount", 0) > 0:
            pay_lines += f"<br>Recibido: {price(order['payment_amount'])}"
            if order.get("payment_change", 0) > 0:
                pay_lines += f"<br>Vuelto: {price(order['payment_change'])}"
    elif pm == "transferencia":
        pay_lines = "TRANSFERENCIA"
    elif pm == "mixto":
        cash_p  = order.get("payment_cash", 0) or 0
        trans_p = order.get("payment_transfer", 0) or 0
        ch      = order.get("payment_change", 0) or 0
        pay_lines = f"MIXTO<br>Efectivo: {price(cash_p)}<br>Transfer: {price(trans_p)}"
        if ch > 0:
            pay_lines += f"<br>Vuelto: {price(ch)}"
    customer_html = f'<div class="meta">Cliente: {order["customer_name"]}</div>' if order.get("customer_name") else ""
    notes_html = f'<div class="order-nota">NOTAS: {order["notes"]}</div>' if order.get("notes") else ""
    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  @page {{ size: 58mm auto; margin: 0mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{
    font-family: Arial, sans-serif;
    background: #fff;
    color: #000;
  }}
  body {{
    font-family: Arial, sans-serif;
    /* 48mm content + 2mm left pad + 2mm right pad = 52mm body.
       Chrome adds ~3-5mm extra margin per side on physical printers.
       52mm + ~6mm chrome margin = 58mm paper. Safe zone guaranteed. */
    width: 52mm;
    max-width: 52mm;
    margin: 0;
    padding: 2mm 2mm 4mm 2mm;
    background: #fff;
    color: #000;
    overflow: hidden;
  }}
  .header {{
    text-align: center;
    border-bottom: 3px solid #000;
    padding-bottom: 5px;
    margin-bottom: 6px;
  }}
  .brand {{ font-size: 20pt; font-weight: 900; letter-spacing: 2px; }}
  .sub {{ font-size: 7pt; margin-top: 1px; }}
  .order-num {{
    font-size: 26pt; font-weight: 900; letter-spacing: 1px;
    text-align: center; margin: 4px 0 2px 0;
  }}
  /* THERMAL-SAFE: no backgrounds, no colors — only black on white */
  .ubicacion {{
    font-size: 14pt; font-weight: 900;
    color: #000;
    border-top: 3px solid #000;
    border-bottom: 3px solid #000;
    padding: 3px 0;
    display: block; margin: 4px 0;
    text-align: center; width: 100%;
  }}
  .meta {{ font-size: 8pt; color: #000; margin: 1px 0; }}
  .sep {{ border: none; border-top: 1px dashed #000; margin: 5px 0; }}
  .sep2 {{ border: none; border-top: 2px solid #000; margin: 5px 0; }}
  /* Item layout: qty | name (wraps) | price — percentage columns never clip */
  .item {{
    width: 100%; border-collapse: collapse;
    border-bottom: 1px dashed #000;
    margin: 0; padding: 0;
  }}
  .item td {{ vertical-align: top; padding: 4px 1px 3px 1px; }}
  .qty {{
    width: 14%; font-size: 14pt; font-weight: 900;
    white-space: nowrap; padding-right: 2px;
  }}
  .name {{
    font-size: 10pt; font-weight: 700;
    line-height: 1.3; word-break: break-word;
  }}
  .item-price {{
    width: 30%; font-size: 10pt; font-weight: 900;
    text-align: right; white-space: nowrap;
  }}
  .nota {{ font-size: 8pt; font-style: italic; font-weight: 700; padding: 1px 0 3px 26px; }}
  .total-block {{
    margin-top: 5px;
    border-top: 3px solid #000;
    padding-top: 4px;
  }}
  .total-row {{ display: flex; justify-content: space-between; align-items: center; }}
  .total-label {{ font-size: 15pt; font-weight: 900; }}
  .total-amount {{ font-size: 17pt; font-weight: 900; }}
  .pay-block {{
    margin-top: 5px;
    font-size: 9pt;
    font-weight: 700;
    line-height: 1.5;
    border-top: 1px dashed #000;
    padding-top: 4px;
  }}
  .order-nota {{
    margin-top: 5px; font-size: 9pt; font-weight: 900;
    border: 2px solid #000; padding: 3px 5px;
  }}
  .footer {{ text-align: center; font-size: 8pt; margin-top: 8px; font-weight: 700; }}
</style>
</head><body>
<div class="header">
  <div class="brand">DYLAN</div>
  <div class="sub">Polleria &amp; Cevicheria Peruana</div>
</div>
<div class="order-num">#{order['id']}</div>
<div style="text-align:center"><span class="ubicacion">{tipo} — {order['table_num']}</span></div>
{customer_html}
<div class="meta">Mozo: {order['mozo_name']}</div>
<div class="meta">Fecha: {order['created_at'][:16]}</div>
<hr class="sep2">
{items_html}
<div class="total-block">
  <div class="total-row">
    <span class="total-label">TOTAL</span>
    <span class="total-amount">{price(order['total'])}</span>
  </div>
</div>
{'<div class="pay-block">PAGO: ' + pay_lines + '</div>' if pay_lines else ''}
{notes_html}
<div class="footer">--- Gracias por su preferencia! ---</div>
</body></html>"""
    return html
def generate_kitchen_html(order_id: int) -> str:
    """Generate a large-text kitchen ticket (comanda) for the cook. No prices."""
    with get_db() as conn:
        order = conn.execute("""
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE o.id = ?
        """, (order_id,)).fetchone()
        items = conn.execute("""
            SELECT oi.quantity, oi.notes, mi.name as item_name
            FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
        """, (order_id,)).fetchall()
    if not order:
        return "<p>Pedido no encontrado.</p>"
    order = dict(order)
    type_labels = {"mesa": "MESA", "mostrador": "BARRA", "barra": "BARRA", "para_llevar": "DELIVERY"}
    tipo = type_labels.get(order.get("order_type", "mesa"), "MESA")
    items_html = ""
    for it in items:
        name = "MENÚ DEL DÍA" if it["item_name"] == "__menu_del_dia__" else it["item_name"].upper()
        items_html += f"""
        <div class="item">
            <span class="qty">{it['quantity']}x</span>
            <span class="name">{name}</span>
        </div>"""
        if it["notes"]:
            items_html += f'<div class="nota">** {it["notes"]}</div>'
    notes_html = f'<div class="order-nota">NOTA: {order["notes"]}</div>' if order.get("notes") else ""
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  @page {{ size: 58mm auto; margin: 0mm; }}
  body {{
    font-family: Arial, sans-serif;
    width: 52mm;
    max-width: 52mm;
    margin: 0;
    padding: 2mm 2mm 4mm 2mm;
  }}
  .header {{
    text-align: center;
    border-bottom: 3px solid #000;
    padding-bottom: 6px;
    margin-bottom: 8px;
  }}
  .order-num {{
    font-size: 28pt;
    font-weight: 900;
    letter-spacing: 2px;
  }}
  /* THERMAL-SAFE: no backgrounds, no colors */
  .ubicacion {{
    font-size: 16pt;
    font-weight: 900;
    color: #000;
    border-top: 3px solid #000;
    border-bottom: 3px solid #000;
    padding: 3px 0;
    display: block;
    text-align: center;
    margin: 4px 0;
    width: 100%;
  }}
  .tipo {{
    font-size: 11pt;
    font-weight: 700;
    color: #000;
  }}
  .mozo {{
    font-size: 9pt;
    color: #000;
    margin-top: 2px;
  }}
  .item {{
    display: flex;
    align-items: baseline;
    gap: 6px;
    border-bottom: 1px dashed #000;
    padding: 5px 0;
  }}
  .qty {{
    font-size: 18pt;
    font-weight: 900;
    min-width: 28px;
    color: #000;
  }}
  .name {{
    font-size: 13pt;
    font-weight: 700;
    line-height: 1.2;
    word-break: break-word;
  }}
  .nota {{
    font-size: 10pt;
    font-style: italic;
    font-weight: 700;
    padding: 2px 4px 4px 34px;
  }}
  .order-nota {{
    margin-top: 8px;
    font-size: 11pt;
    font-weight: 900;
    border: 2px solid #000;
    padding: 4px 6px;
  }}
  .time {{
    text-align: right;
    font-size: 8pt;
    color: #000;
    margin-top: 6px;
  }}
</style>
</head><body>
<div class="header">
  <div class="order-num">#{order['id']}</div>
  <div class="ubicacion">{order['table_num']}</div>
  <div class="tipo">{tipo}</div>
  <div class="mozo">Mozo: {order['mozo_name']}</div>
</div>
{items_html}
{notes_html}
<div class="time">{order['created_at'][11:16]}</div>
</body></html>"""
def render_print_button(order_id: int, key_suffix: str = "", kitchen: bool = False,
                        already_printed: bool = False, track_db: bool = False):
    """
    Print button inside an iframe so window.open() fires on a direct user gesture
    and is never blocked by the browser.
    - already_printed : starts green if True (order has printed_at in DB)
    - track_db        : unused here; DB is updated via render_print_section's Marcar button
    After clicking: button turns green in-session (JS). On refresh: stays green if already_printed.
    """
    import base64
    html_content = generate_kitchen_html(order_id) if kitchen else generate_receipt_html(order_id)
    encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    if kitchen:
        label_idle = "&#x1F373; Imprimir comanda"
        label_done = "&#x2705; Comanda impresa"
        color_idle = "#B71C1C"
    else:
        label_idle = "&#x1F5A8; Ticket cliente"
        label_done = "&#x2705; Ticket impreso"
        color_idle = "#1565C0"
    color_done  = "#2E7D32"
    start_green = "true" if already_printed else "false"
    fn = f"doPrint_{order_id}_{key_suffix}_{'k' if kitchen else 'r'}".replace("-", "_")
    components.html(f"""<!DOCTYPE html>
<html><head><style>
  body {{ margin:0; padding:2px; font-family:sans-serif; }}
  #btn {{
    color:white; border:none; padding:9px 12px; border-radius:6px;
    font-size:13px; cursor:pointer; width:100%;
    display:flex; align-items:center; justify-content:center; gap:6px;
    transition: background 0.25s;
  }}
  #btn:hover {{ opacity:0.88; }}
</style></head><body>
<button id="btn">{label_idle}</button>
<script>
var btn = document.getElementById('btn');
var startGreen = {start_green};
btn.style.background = startGreen ? '{color_done}' : '{color_idle}';
if (startGreen) btn.innerHTML = '{label_done}';
btn.addEventListener('click', function() {{
  var b64 = "{encoded}";
  var html = decodeURIComponent(escape(atob(b64)));
  var w = window.open('about:blank', '_blank', 'width=380,height=650,scrollbars=yes');
  if (!w) {{ alert('Habilitá los popups para imprimir.'); return; }}
  w.document.open(); w.document.write(html); w.document.close();
  w.focus();
  setTimeout(function() {{ w.print(); }}, 600);
  // Turn green immediately
  btn.style.background = '{color_done}';
  btn.innerHTML = '{label_done}';
}});
</script>
</body></html>""", height=48)
# ─── COMBINED TICKET (cocina + cliente) ────────────────────────────────────────
def generate_combined_html(order_id: int) -> str:
    """Single print job: kitchen comanda (page 1) + customer receipt (page 2).
    Thermal printer prints both and cuts between them."""
    with get_db() as conn:
        order = conn.execute("""
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE o.id = ?
        """, (order_id,)).fetchone()
        items = conn.execute("""
            SELECT oi.quantity, oi.unit_price, oi.notes, mi.name as item_name
            FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
        """, (order_id,)).fetchall()
    if not order:
        return "<p>Pedido no encontrado.</p>"
    order = dict(order)
    type_labels = {"mesa": "MESA", "mostrador": "BARRA", "barra": "BARRA", "para_llevar": "DELIVERY"}
    tipo = type_labels.get(order.get("order_type", "mesa"), "MESA")
    pay_labels = {"efectivo": "EFECTIVO", "transferencia": "TRANSFERENCIA", "pendiente": "PENDIENTE"}
    # ── Kitchen section ──
    kitchen_items = ""
    for it in items:
        name = "MENÚ DEL DÍA" if it["item_name"] == "__menu_del_dia__" else it["item_name"].upper()
        kitchen_items += f"""
        <div class="k-item">
            <span class="k-qty">{it['quantity']}x</span>
            <span class="k-name">{name}</span>
        </div>"""
        if it["notes"]:
            kitchen_items += f'<div class="k-nota">** {it["notes"]}</div>'
    kitchen_order_nota = f'<div class="k-order-nota">NOTA: {order["notes"]}</div>' if order.get("notes") else ""
    # ── Receipt section ──
    receipt_items = ""
    total = 0
    for it in items:
        line_total = it["unit_price"] * it["quantity"]
        total += line_total
        name = "Menú del Día" if it["item_name"] == "__menu_del_dia__" else it["item_name"]
        receipt_items += f"""
        <tr>
            <td>{it['quantity']}x {name}"""
        if it["notes"]:
            receipt_items += f"<br><small>({it['notes']})</small>"
        receipt_items += f"</td><td style='text-align:right'>${line_total:,.0f}</td></tr>"
    pay_method = pay_labels.get(order.get("payment_method", ""), "—")
    pay_html = ""
    if order.get("payment_method") == "efectivo" and order.get("payment_amount", 0) > 0:
        pay_html = f"""
        <tr><td>Recibido:</td><td style='text-align:right'>${order['payment_amount']:,.0f}</td></tr>
        <tr><td><b>Vuelto:</b></td><td style='text-align:right'><b>${order.get('payment_change',0):,.0f}</b></td></tr>"""
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  @page {{ size: 58mm auto; margin: 1mm 2mm; }}
  * {{ box-sizing:border-box; word-wrap:break-word; overflow-wrap:break-word; }}
  body {{ font-family: Arial, sans-serif; width: 52mm; max-width:52mm; margin: 0; padding: 1mm 2mm; overflow:hidden; }}
  /* ── Page break between tickets ── */
  .page-break {{ page-break-after: always; padding-bottom: 6mm; }}
  /* ── Kitchen styles — THERMAL-SAFE: no backgrounds, no colors ── */
  .k-header {{ text-align:center; border-bottom:3px solid #000; padding-bottom:6px; margin-bottom:8px; }}
  .k-order-num {{ font-size:26pt; font-weight:900; letter-spacing:2px; }}
  .k-ubicacion {{ font-size:14pt; font-weight:900; color:#000;
                  border-top:3px solid #000; border-bottom:3px solid #000;
                  padding:3px 0; display:block; text-align:center;
                  margin:4px 0; width:100%; word-break:break-word; }}
  .k-tipo {{ font-size:10pt; font-weight:700; color:#000; }}
  .k-mozo {{ font-size:8.5pt; color:#000; margin-top:2px; }}
  .k-item {{ display:flex; align-items:baseline; gap:5px;
             border-bottom:1px dashed #000; padding:4px 0; }}
  .k-qty {{ font-size:16pt; font-weight:900; min-width:26px; color:#000; flex-shrink:0; }}
  .k-name {{ font-size:12pt; font-weight:700; line-height:1.2; word-break:break-word; }}
  .k-nota {{ font-size:9.5pt; font-style:italic; font-weight:700; color:#000;
             padding:2px 4px 4px 30px; word-break:break-word; }}
  .k-order-nota {{ margin-top:6px; font-size:10.5pt; font-weight:900; color:#000;
                   border:2px solid #000; padding:4px 5px; word-break:break-word; }}
  .k-time {{ text-align:right; font-size:7.5pt; color:#000; margin-top:5px; }}
  /* ── Receipt styles ── */
  .r-center {{ text-align:center; }}
  .r-title {{ font-size:13pt; font-weight:900; letter-spacing:3px; }}
  .r-sub {{ font-size:7pt; letter-spacing:0px; white-space:normal; }}
  .r-sep {{ border-top:1px solid #000; margin:3px 0; }}
  .r-sep2 {{ border-top:2px solid #000; margin:3px 0; }}
  .r-items {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:3px 0; table-layout:fixed; }}
  .r-items td {{ padding:1px 0; vertical-align:top; word-break:break-word; }}
  .r-items td:last-child {{ width:30%; text-align:right; white-space:nowrap; }}
  .r-items td:first-child {{ width:70%; }}
  .r-total {{ width:100%; border-collapse:collapse; font-size:10pt; font-weight:700; table-layout:fixed; }}
  .r-total td {{ padding:1px 0; }}
  .r-total td:last-child {{ text-align:right; white-space:nowrap; width:35%; }}
  .r-pago {{ font-size:8.5pt; margin-top:3px; word-break:break-word; }}
  .r-footer {{ text-align:center; font-size:7.5pt; margin-top:5px; font-style:italic; }}
</style>
</head><body>
<!-- ══ TICKET COCINA (página 1) ══ -->
<div class="page-break">
  <div class="k-header">
    <div class="k-order-num">#{order['id']}</div>
    <div class="k-ubicacion">{order['table_num']}</div>
    <div class="k-tipo">{tipo}</div>
    <div class="k-mozo">Mozo: {order['mozo_name']}</div>
  </div>
  {kitchen_items}
  {kitchen_order_nota}
  <div class="k-time">{order['created_at'][11:16]}</div>
</div>
<!-- ══ TICKET CLIENTE (página 2) ══ -->
<div>
  <div class="r-center">
    <div class="r-title">DYLAN</div>
    <div class="r-sub">Pollería &amp; Cevichería Peruana</div>
  </div>
  <div class="r-sep2"></div>
  <div style="font-size:8pt">
    Pedido: #{order['id']} | {tipo}: {order['table_num']}<br>
    {"Cliente: " + order['customer_name'] + "<br>" if order.get('customer_name') else ""}
    Mozo: {order['mozo_name']}<br>
    Fecha: {order['created_at'][:16]}
  </div>
  <div class="r-sep"></div>
  <table class="r-items">
    {receipt_items}
  </table>
  <div class="r-sep2"></div>
  <table class="r-total">
    <tr><td>TOTAL:</td><td style='text-align:right'>${total:,.0f}</td></tr>
  </table>
  <div class="r-sep"></div>
  <div class="r-pago">
    PAGO: {pay_method}
    {pay_html}
  </div>
  <div class="r-sep2"></div>
  <div class="r-footer">¡Gracias por su preferencia!</div>
</div>
</body></html>"""
def render_combined_print_button(order_id: int, key_suffix: str = ""):
    """Single button that prints kitchen comanda + customer receipt in one job."""
    import base64
    html_content = generate_combined_html(order_id)
    encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    fn_name = f"doPrintCombined_{order_id}_{key_suffix}"
    components.html(f"""<!DOCTYPE html>
<html><head><style>
  body {{ margin:0; padding:2px; font-family:sans-serif; }}
  button {{
    background:#2E7D32; color:white; border:none; padding:11px 14px;
    border-radius:8px; font-size:15px; font-weight:700; cursor:pointer;
    width:100%; display:flex; align-items:center; justify-content:center; gap:8px;
  }}
  button:hover {{ opacity:0.88; }}
</style></head>
<body>
<script>
function {fn_name}() {{
  var b64 = "{encoded}";
  var html = decodeURIComponent(escape(atob(b64)));
  var w = window.open('about:blank', '_blank', 'width=380,height=700,scrollbars=yes');
  if (!w) {{ alert('Habilitá los popups para imprimir. (Configuración del navegador)'); return; }}
  w.document.open();
  w.document.write(html);
  w.document.close();
  w.focus();
  setTimeout(function() {{ w.print(); }}, 600);
}}
</script>
<button onclick="{fn_name}()">🖨️ IMPRIMIR TICKETS (Cocina + Cliente)</button>
</body></html>""", height=56)
# ─── SHARED: EDIT ORDER PANEL ─────────────────────────────────────────────────
def render_edit_panel(order: dict, key_prefix: str = ""):
    """
    Reusable inline edit panel for an order.
    - Quitar ítems (dueño/admin/encargado)
    - Agregar ítems (todos)
    - Editar notas del pedido
    - Disponible mientras el pedido no esté cobrado (paid=0) ni cancelado.
    Call from: page_kitchen, page_tables_cobrar, page_my_orders.
    """
    if order.get("paid") or order.get("status") == "cancelado":
        return  # Nothing to edit on closed orders
    role = st.session_state.user.get("role", "mozo")
    can_remove = role in ("admin", "dueno", "encargado")
    order_id = order["id"]
    edit_key = f"{key_prefix}edit_panel_{order_id}"
    btn_label = "✏️ Editar pedido" if can_remove else "➕ Agregar ítem"
    if st.button(btn_label, key=f"{key_prefix}edit_open_{order_id}", use_container_width=True):
        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
        st.rerun()
    if not st.session_state.get(edit_key):
        return
    with st.container(border=True):
        st.markdown(f"**✏️ Editar Pedido #{order_id}**")
        # ── QUITAR ÍTEMS (dueño/encargado) ──
        if can_remove:
            st.markdown("**🗑️ Quitar ítems:**")
            with get_db() as conn:
                edit_items = conn.execute("""
                    SELECT oi.id as oi_id, oi.quantity, oi.notes,
                           mi.name as item_name, oi.unit_price
                    FROM order_items oi
                    JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE oi.order_id = ?
                """, (order_id,)).fetchall()
            for ei in edit_items:
                ea, eb = st.columns([5, 1])
                ea.write(f"{ei['quantity']}x {display_item_name(ei['item_name'])}"
                         + (f" — _{ei['notes']}_" if ei["notes"] else ""))
                if eb.button("🗑️", key=f"{key_prefix}rm_{ei['oi_id']}"):
                    with get_db() as conn:
                        conn.execute("DELETE FROM order_items WHERE id=?", (ei["oi_id"],))
                        new_total = conn.execute(
                            "SELECT COALESCE(SUM(quantity*unit_price),0) FROM order_items WHERE order_id=?",
                            (order_id,),
                        ).fetchone()[0]
                        conn.execute(
                            "UPDATE orders SET total=?, updated_at=? WHERE id=?",
                            (new_total, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id),
                        )
                    st.rerun()
            st.divider()
        # ── AGREGAR ÍTEM ──
        st.markdown("**➕ Agregar ítem:**")
        with get_db() as conn:
            add_cats = conn.execute(
                "SELECT * FROM categories ORDER BY sort_order, name"
            ).fetchall()
        if not add_cats:
            st.warning("No hay categorías en el menú.")
        else:
            sel_cat = st.selectbox(
                "Categoría", [c["name"] for c in add_cats],
                key=f"{key_prefix}add_cat_{order_id}",
            )
            sel_cat_id = next(c["id"] for c in add_cats if c["name"] == sel_cat)
            with get_db() as conn:
                add_menu = conn.execute(
                    "SELECT * FROM menu_items WHERE category_id=? AND active=1 ORDER BY name",
                    (sel_cat_id,),
                ).fetchall()
            if add_menu:
                item_labels = [
                    f"{display_item_name(m['name'])} — {fmt_price(m['price'])}"
                    for m in add_menu
                ]
                sel_mi = st.selectbox(
                    "Ítem", range(len(item_labels)),
                    format_func=lambda i: item_labels[i],
                    key=f"{key_prefix}add_mi_{order_id}",
                )
                add_qty = st.number_input(
                    "Cantidad", min_value=1, value=1, step=1,
                    key=f"{key_prefix}add_qty_{order_id}",
                )
                add_notes = st.text_input(
                    "Notas del ítem", placeholder="sin sal, extra picante...",
                    key=f"{key_prefix}add_notes_{order_id}",
                )
                if st.button("➕ Confirmar agregar", key=f"{key_prefix}add_confirm_{order_id}",
                             type="primary", use_container_width=True):
                    chosen = add_menu[sel_mi]
                    with get_db() as conn:
                        conn.execute(
                            "INSERT INTO order_items "
                            "(order_id, menu_item_id, quantity, unit_price, notes) "
                            "VALUES (?,?,?,?,?)",
                            (order_id, chosen["id"], add_qty, chosen["price"], add_notes),
                        )
                        new_total = conn.execute(
                            "SELECT COALESCE(SUM(quantity*unit_price),0) "
                            "FROM order_items WHERE order_id=?",
                            (order_id,),
                        ).fetchone()[0]
                        # If already entregado, reopen to preparando so kitchen sees it again
                        new_status = (
                            "preparando"
                            if order.get("status") in ("entregado", "listo")
                            else order.get("status", "pendiente")
                        )
                        conn.execute(
                            "UPDATE orders SET total=?, status=?, updated_at=? WHERE id=?",
                            (new_total, new_status,
                             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id),
                        )
                    st.session_state[edit_key] = False
                    st.success(f"✅ {add_qty}x {display_item_name(chosen['name'])} agregado al pedido.")
                    st.rerun()
            else:
                st.info("No hay ítems activos en esta categoría.")
        st.divider()
        # ── EDITAR NOTAS DEL PEDIDO ──
        st.markdown("**📝 Notas del pedido:**")
        current_notes = order.get("notes") or ""
        new_notes = st.text_area(
            "Notas", value=current_notes,
            placeholder="Alergias, indicaciones especiales...",
            key=f"{key_prefix}notes_{order_id}",
            height=80, label_visibility="collapsed",
        )
        nc1, nc2 = st.columns(2)
        with nc1:
            if st.button("💾 Guardar notas", key=f"{key_prefix}save_notes_{order_id}",
                         use_container_width=True):
                with get_db() as conn:
                    conn.execute(
                        "UPDATE orders SET notes=?, updated_at=? WHERE id=?",
                        (new_notes.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id),
                    )
                st.success("Notas actualizadas.")
                st.rerun()
        with nc2:
            if st.button("✖ Cerrar", key=f"{key_prefix}edit_close_{order_id}",
                         use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()
# ─── PRINT SECTION (owner/cashier only — mozos do NOT print) ───────────────────
def render_print_section(order_id: int, key_prefix: str):
    """
    Two print buttons (kitchen + receipt) for owner/cashier PC views.
    Each button:
      - Opens its own print dialog → thermal printer cuts between tickets
      - Turns green (✅) after clicking, both in this session and across refreshes
      - Writes printed_at to DB automatically on first click
    Never call from mozo views.
    """
    with get_db() as conn:
        row = conn.execute("SELECT printed_at FROM orders WHERE id=?", (order_id,)).fetchone()
        printed_at = row["printed_at"] if row else None
    already = bool(printed_at)
    if already:
        st.markdown(
            f'<span style="color:#2E7D32;font-size:0.82rem;font-weight:600">'
            f'✅ Impreso {printed_at[11:16]}</span>',
            unsafe_allow_html=True,
        )
    pp1, pp2 = st.columns(2)
    with pp1:
        render_print_button(order_id, key_suffix=f"{key_prefix}_k",
                            kitchen=True, already_printed=already, track_db=True)
    with pp2:
        render_print_button(order_id, key_suffix=f"{key_prefix}_r",
                            kitchen=False, already_printed=already, track_db=True)
# ─── CASH REGISTER HELPERS ─────────────────────────────────────────────────────
def get_open_register():
    """Get the currently open cash register, or None."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM cash_registers WHERE status='open' ORDER BY opened_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None
def get_register_live_totals(register_id):
    """Calculate live totals from orders since register was opened."""
    with get_db() as conn:
        reg = conn.execute("SELECT * FROM cash_registers WHERE id=?", (register_id,)).fetchone()
        if not reg:
            return {}
        opened_at = reg["opened_at"]
        stats = conn.execute("""
            SELECT
                COUNT(CASE WHEN status != 'cancelado' THEN 1 END) as orders_count,
                COALESCE(SUM(CASE WHEN status != 'cancelado' THEN total ELSE 0 END), 0) as total_sales,
                COALESCE(SUM(CASE WHEN status != 'cancelado' AND payment_method='efectivo' THEN total ELSE 0 END), 0) as cash_sales,
                COALESCE(SUM(CASE WHEN status != 'cancelado' AND payment_method='transferencia' THEN total ELSE 0 END), 0) as transfer_sales,
                COALESCE(SUM(CASE WHEN status != 'cancelado' AND payment_method='mixto' THEN payment_cash ELSE 0 END), 0) as mixto_cash,
                COALESCE(SUM(CASE WHEN status != 'cancelado' AND payment_method='mixto' THEN payment_transfer ELSE 0 END), 0) as mixto_transfer,
                COALESCE(SUM(CASE WHEN status != 'cancelado' AND payment_method='pendiente' THEN total ELSE 0 END), 0) as pending_sales,
                COALESCE(SUM(CASE WHEN status != 'cancelado' AND payment_method IN ('efectivo','mixto') THEN payment_change ELSE 0 END), 0) as change_given,
                COALESCE(AVG(CASE WHEN status != 'cancelado' THEN total END), 0) as avg_ticket,
                COALESCE(SUM(CASE WHEN status='cancelado' AND refund_amount > 0 THEN refund_amount ELSE 0 END), 0) as total_refunds,
                COALESCE(SUM(CASE WHEN status='cancelado' AND payment_method='efectivo' AND refund_amount > 0 THEN refund_amount ELSE 0 END), 0) as cash_refunds,
                COALESCE(SUM(CASE WHEN status='cancelado' AND payment_method='transferencia' AND refund_amount > 0 THEN refund_amount ELSE 0 END), 0) as transfer_refunds,
                COUNT(CASE WHEN status='cancelado' AND refund_amount > 0 THEN 1 END) as refund_count
            FROM orders
            WHERE created_at >= ?
        """, (opened_at,)).fetchone()
    net_cash = stats["cash_sales"] + stats["mixto_cash"] - stats["cash_refunds"]
    net_transfer = stats["transfer_sales"] + stats["mixto_transfer"] - stats["transfer_refunds"]
    net_total = stats["total_sales"] - stats["total_refunds"]
    return {
        "orders_count": stats["orders_count"],
        "total_sales": net_total,
        "cash_sales": net_cash,
        "transfer_sales": net_transfer,
        "pending_sales": stats["pending_sales"],
        "change_given": stats["change_given"],
        "avg_ticket": stats["avg_ticket"],
        "opening_amount": reg["opening_amount"],
        "expected_cash": reg["opening_amount"] + net_cash - stats["change_given"],
        "total_refunds": stats["total_refunds"],
        "refund_count": stats["refund_count"],
    }
# ─── INIT ──────────────────────────────────────────────────────────────────────
init_db()
# Migration: add new columns if upgrading from v1
def migrate_db():
    with get_db() as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()]
        if "order_type" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN order_type TEXT DEFAULT 'mesa'")
        if "payment_method" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT ''")
        if "payment_amount" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_amount REAL DEFAULT 0")
        if "payment_change" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_change REAL DEFAULT 0")
        if "paid" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN paid INTEGER DEFAULT 0")
migrate_db()
# Migration: settings table
def migrate_settings():
    with get_db() as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "settings" not in tables:
            conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('num_tables', '10')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('restaurant_name', 'DYLAN')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_price', '10000')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_active', '1')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('menu_del_dia_description', 'Menú del Día (consultar plato)')")
migrate_settings()
# Migration: rebuild users table to support 'admin' role, then ensure master admin exists
def migrate_admin():
    with get_db() as conn:
        # Check if admin user already exists
        admin_exists = conn.execute("SELECT COUNT(*) c FROM users WHERE username='roker'").fetchone()["c"]
        if admin_exists:
            return  # Already migrated
        # Check if old constraint blocks us
        table_sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        if table_sql and "admin" not in table_sql["sql"]:
            # Clean up any leftover temp tables from failed previous attempts
            conn.execute("DROP TABLE IF EXISTS users_new")
            conn.execute("DROP TABLE IF EXISTS users_backup")
            # Rebuild: rename old → backup, create new with admin role, copy data, drop backup
            conn.execute("ALTER TABLE users RENAME TO users_backup")
            conn.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'dueno', 'mozo')),
                    display_name TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT INTO users (id, username, password_hash, role, display_name, active, created_at)
                SELECT id, username, password_hash, role, display_name, active, created_at FROM users_backup
            """)
            conn.execute("DROP TABLE users_backup")
        # Now insert admin
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role, display_name) VALUES (?,?,?,?)",
            ("roker", hash_pw("99107001"), "admin", "Roker (Admin)"),
        )
migrate_admin()
# Migration: sessions table
def migrate_sessions_table():
    with get_db() as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "sessions" not in tables:
            conn.execute("""CREATE TABLE sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
migrate_sessions_table()
# Migration: cash_registers table
def migrate_cash_registers():
    with get_db() as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "cash_registers" not in tables:
            conn.execute("""CREATE TABLE cash_registers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opened_by INTEGER NOT NULL,
                opening_amount REAL NOT NULL DEFAULT 0,
                closing_amount_real REAL DEFAULT 0,
                closing_amount_expected REAL DEFAULT 0,
                difference REAL DEFAULT 0,
                total_cash_sales REAL DEFAULT 0,
                total_transfer_sales REAL DEFAULT 0,
                total_pending REAL DEFAULT 0,
                total_change_given REAL DEFAULT 0,
                orders_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open' CHECK(status IN ('open','closed')),
                notes TEXT DEFAULT '',
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (opened_by) REFERENCES users(id)
            )""")
migrate_cash_registers()
# Migration: refund columns on orders
def migrate_refund_columns():
    with get_db() as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()]
        if "refund_amount" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN refund_amount REAL DEFAULT 0")
        if "refund_reason" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN refund_reason TEXT DEFAULT ''")
migrate_refund_columns()
def migrate_fix_orders_fk():
    """Fix orders and order_items FKs that may point to renamed backup tables after migrations."""
    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        # Fix orders if FK points to users_backup instead of users
        schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='orders'").fetchone()
        if schema and 'users_backup' in schema[0]:
            conn.execute("ALTER TABLE orders RENAME TO orders_fk_fix_backup")
            conn.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_type TEXT NOT NULL DEFAULT 'mesa'
                    CHECK(order_type IN ('mesa','mostrador','para_llevar')),
                table_num TEXT NOT NULL DEFAULT '',
                customer_name TEXT DEFAULT '',
                mozo_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pendiente'
                    CHECK(status IN ('pendiente','preparando','listo','entregado','cancelado')),
                notes TEXT DEFAULT '',
                total REAL DEFAULT 0,
                payment_method TEXT DEFAULT '',
                payment_amount REAL DEFAULT 0,
                payment_change REAL DEFAULT 0,
                paid INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                refund_amount REAL DEFAULT 0,
                refund_reason TEXT DEFAULT '',
                FOREIGN KEY (mozo_id) REFERENCES users(id)
            )""")
            conn.execute("""
            INSERT INTO orders (id, order_type, table_num, customer_name, mozo_id, status, notes,
                total, payment_method, payment_amount, payment_change, paid, created_at, updated_at,
                refund_amount, refund_reason)
            SELECT id, order_type, table_num, customer_name, mozo_id, status, notes,
                total, payment_method, payment_amount, payment_change, paid, created_at, updated_at,
                COALESCE(refund_amount, 0), COALESCE(refund_reason, '')
            FROM orders_fk_fix_backup
            """)
            conn.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM orders) WHERE name = 'orders'")
            conn.execute("DROP TABLE orders_fk_fix_backup")
        # Fix order_items if FK points to any backup table instead of orders
        oi_schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='order_items'").fetchone()
        if oi_schema and 'orders_backup' in oi_schema[0]:
            conn.execute("ALTER TABLE order_items RENAME TO order_items_fk_fix_backup")
            conn.execute("""
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                menu_item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL,
                notes TEXT DEFAULT '',
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
            )""")
            conn.execute("""
            INSERT INTO order_items (id, order_id, menu_item_id, quantity, unit_price, notes)
            SELECT id, order_id, menu_item_id, quantity, unit_price, notes
            FROM order_items_fk_fix_backup
            """)
            conn.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM order_items) WHERE name = 'order_items'")
            conn.execute("DROP TABLE order_items_fk_fix_backup")
        conn.execute("PRAGMA foreign_keys=ON")
migrate_fix_orders_fk()
def migrate_cook_times():
    """Add cooking time learning: cooking_started_at on orders, avg_cook_minutes on menu_items."""
    with get_db() as conn:
        order_cols = [r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()]
        if "cooking_started_at" not in order_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN cooking_started_at TIMESTAMP")
        menu_cols = [r[1] for r in conn.execute("PRAGMA table_info(menu_items)").fetchall()]
        if "avg_cook_minutes" not in menu_cols:
            conn.execute("ALTER TABLE menu_items ADD COLUMN avg_cook_minutes REAL")
migrate_cook_times()
def migrate_printed_at():
    """Add printed_at column to track which orders have been printed from the cashier PC."""
    with get_db() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()]
        if "printed_at" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN printed_at TIMESTAMP DEFAULT NULL")
migrate_printed_at()
def migrate_plain_pw():
    """Add plain_pw column so admin can see/recover all user passwords."""
    with get_db() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "plain_pw" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN plain_pw TEXT DEFAULT ''")
migrate_plain_pw()
def migrate_mixed_payment():
    """Add payment_cash and payment_transfer columns for split payments."""
    with get_db() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()]
        if "payment_cash" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_cash REAL DEFAULT 0")
        if "payment_transfer" not in cols:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_transfer REAL DEFAULT 0")
migrate_mixed_payment()
def migrate_sessions_no_fk():
    """Recreate sessions table without FOREIGN KEY constraint (fixes login bug after migrate_encargado)."""
    with get_db() as conn:
        table_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchone()
        if table_sql and "FOREIGN KEY" in table_sql["sql"]:
            conn.execute("DROP TABLE IF EXISTS _sessions_bkp")
            conn.execute("ALTER TABLE sessions RENAME TO _sessions_bkp")
            conn.execute("""
                CREATE TABLE sessions (
                    token      TEXT PRIMARY KEY,
                    user_id    INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT INTO sessions (token, user_id, created_at)
                SELECT token, user_id, created_at FROM _sessions_bkp
            """)
            conn.execute("DROP TABLE _sessions_bkp")

def migrate_encargado():
    """Add 'encargado' role to users CHECK constraint and create user_permissions table."""
    with get_db() as conn:
        # 1. Create user_permissions table (idempotent)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id   INTEGER NOT NULL,
                permission TEXT NOT NULL,
                allowed   INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, permission)
            )
        """)
        # 2. Rebuild users table only if 'encargado' not yet in CHECK constraint
        table_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if table_sql and "encargado" not in table_sql["sql"]:
            conn.execute("DROP TABLE IF EXISTS _users_enc_bkp")
            conn.execute("ALTER TABLE users RENAME TO _users_enc_bkp")
            conn.execute("""
                CREATE TABLE users (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    username     TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    plain_pw     TEXT DEFAULT '',
                    role         TEXT NOT NULL
                                 CHECK(role IN ('admin','dueno','encargado','mozo')),
                    display_name TEXT NOT NULL,
                    active       INTEGER DEFAULT 1,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT INTO users
                    (id, username, password_hash, plain_pw, role, display_name, active, created_at)
                SELECT
                    id, username, password_hash,
                    COALESCE(plain_pw,''), role, display_name, active, created_at
                FROM _users_enc_bkp
            """)
            conn.execute("DROP TABLE _users_enc_bkp")
migrate_encargado()
migrate_sessions_no_fk()
seed_data()
# ─── SESSION PERSISTENCE (survives F5 refresh) ────────────────────────────────
def create_session(user_id):
    """Create a persistent session token in DB and URL."""
    token = uuid.uuid4().hex
    with get_db() as conn:
        # Clean old sessions for this user
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?,?)", (token, user_id))
    st.query_params["s"] = token
    return token
def restore_session():
    """Try to restore session from URL query param."""
    token = st.query_params.get("s", "")
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute("""
            SELECT u.* FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND u.active = 1
        """, (token,)).fetchone()
    if row:
        return dict(row)
    return None
def destroy_session():
    """Remove session from DB and URL."""
    token = st.query_params.get("s", "")
    if token:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    st.query_params.clear()
# ─── INIT SESSION STATE ───────────────────────────────────────────────────────
# Try to restore session from URL if not already logged in
if "user" not in st.session_state or st.session_state.user is None:
    restored = restore_session()
    if restored:
        st.session_state["user"] = restored
    else:
        st.session_state["user"] = None
st.session_state.setdefault("user", None)
st.session_state.setdefault("page", "menu")
st.session_state.setdefault("cart", [])
st.session_state.setdefault("order_type", None)
st.session_state.setdefault("order_table_num", "")
st.session_state.setdefault("confirm_order", False)
st.session_state.setdefault("last_order_id", 0)
# ─── HEADER ────────────────────────────────────────────────────────────────────
def render_header():
    st.html("""
    <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                display:flex; align-items:center; justify-content:space-between;
                padding:0.7rem 1.2rem; border-bottom:2px solid #D4A843;">
        <div style="text-align:left; min-width:160px;">
            <div style="font-size:0.6rem; color:#aaa; letter-spacing:2px; text-transform:uppercase; font-family:sans-serif;">Powered by</div>
            <div style="font-size:1rem; font-weight:800; color:#D4A843; letter-spacing:2px; font-family:sans-serif;">&#9889; SISTEMA ROKER</div>
            <div style="font-size:0.78rem; color:#25D366; margin-top:4px; font-family:sans-serif;">&#128172; WhatsApp</div>
            <div style="font-size:0.78rem; color:#F5E6C8; font-family:sans-serif;">11 5383-9101</div>
        </div>
        <div style="text-align:center; flex:1;">
            <div style="font-size:2rem; margin:0; letter-spacing:6px; font-weight:800; color:#D4A843; font-family:Georgia,serif;">DYLAN</div>
            <div style="color:#F5E6C8; font-size:0.68rem; margin:0.1rem 0 0 0; letter-spacing:3px; font-family:sans-serif;">POLLERIA &amp; CEVICHERIA PERUANA</div>
        </div>
    </div>
    """)
# ─── LOGIN ─────────────────────────────────────────────────────────────────────
def login_page():
    render_header()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### Iniciar Sesión")
            username = st.text_input("Usuario", key="login_user", placeholder="Ingrese su usuario")
            password = st.text_input("Contraseña", type="password", key="login_pw", placeholder="Ingrese su contraseña")
            if st.button("Ingresar", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("Complete todos los campos")
                    return
                with get_db() as conn:
                    user = conn.execute(
                        "SELECT * FROM users WHERE username=? AND password_hash=? AND active=1",
                        (username.strip(), hash_pw(password)),
                    ).fetchone()
                if user:
                    st.session_state.user = dict(user)
                    create_session(user["id"])
                    st.session_state.page = "kitchen" if user["role"] in ("admin", "dueno") else "new_order"
                    st.session_state.cart = []
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        # Branding Sistema Roker
        st.markdown("""
        <div style="text-align:center; margin-top:1.2rem;">
            <div style="font-size:0.75rem; color:#888; letter-spacing:2px; text-transform:uppercase;">
                Powered by
            </div>
            <div style="font-size:1.3rem; font-weight:800; color:#D4A843; letter-spacing:3px; margin:0.2rem 0;">
                ⚡ SISTEMA ROKER
            </div>
            <div style="font-size:0.85rem; color:#aaa;">
                📞 11 5383-9101
            </div>
        </div>
        """, unsafe_allow_html=True)
# ─── NAVIGATION (TOP BAR — always visible, no sidebar) ────────────────────────
def _nav_button(label, target_page, current_page):
    """Render a nav button. Highlighted if it's the current page."""
    is_active = current_page == target_page
    if st.button(label, use_container_width=True, type="primary" if is_active else "secondary"):
        # Reset order state when navigating to new_order
        if target_page == "new_order":
            st.session_state.order_type = None
            st.session_state.order_table_num = ""
            st.session_state.cart = []
            st.session_state.confirm_order = False
            st.session_state.pop("pay_method_selected", None)
        st.session_state.page = target_page
        st.session_state.show_more_menu = False
        st.rerun()
def render_nav():
    user = st.session_state.user
    role = user["role"]
    is_owner = role in ("admin", "dueno")
    current = st.session_state.page
    # Helper for logout button (reused)
    def _logout_btn():
        if st.button("🚪 Salir", use_container_width=True):
            destroy_session()
            st.session_state.user = None
            st.session_state.page = "menu"
            st.session_state.cart = []
            st.rerun()
    # ── Row 1: Main actions (always visible) ──
    if is_owner:
        # Bell badge — count of unprinted orders today
        pending_print = get_unprinted_count()
        render_bell_sound(pending_print)
        bell_label = f"🔔 ({pending_print}) IMPRIMIR" if pending_print > 0 else "📦 PEDIDOS"
        nav_cols = st.columns([1, 1, 1, 1, 1, 1, 1])
        with nav_cols[0]:
            _nav_button("👨‍🍳 COCINA", "kitchen", current)
        with nav_cols[1]:
            _nav_button("🛒 PEDIDO", "new_order", current)
        with nav_cols[2]:
            _nav_button("🪑 MESAS", "tables_cobrar", current)
        with nav_cols[3]:
            # Bell button — highlights when there are pending print jobs
            if pending_print > 0:
                if st.button(bell_label, use_container_width=True, type="primary",
                             key="nav_bell_pending"):
                    st.session_state.page = "all_orders"
                    st.rerun()
            else:
                _nav_button("📦 PEDIDOS", "all_orders", current)
        with nav_cols[4]:
            _nav_button("💰 CAJA", "dashboard", current)
        with nav_cols[5]:
            if st.button("⚙️ MÁS", use_container_width=True):
                st.session_state.show_more_menu = not st.session_state.get("show_more_menu", False)
                st.rerun()
        with nav_cols[6]:
            _logout_btn()
        # ── Row 2: Secondary menu (toggle) ──
        if st.session_state.get("show_more_menu", False):
            extra_cols = st.columns([1, 1, 1, 1, 1, 1])
            with extra_cols[0]:
                _nav_button("📄 Reporte", "daily_report", current)
            with extra_cols[1]:
                _nav_button("🧾 Tickets", "ticket_history", current)
            with extra_cols[2]:
                _nav_button("🍽️ Editar Menú", "edit_menu", current)
            with extra_cols[3]:
                _nav_button("👥 Mozos", "manage_mozos", current)
            with extra_cols[4]:
                _nav_button("⚙️ Ajustes", "settings", current)
            with extra_cols[5]:
                _nav_button("📋 Ver Menú", "menu", current)
    elif role == "encargado":
        # Encargado: dueño-like nav filtered by permissions
        pending_print = get_unprinted_count()
        render_bell_sound(pending_print)
        enc_primary = []
        if has_permission("cocina"):
            enc_primary.append(("👨‍🍳 COCINA", "kitchen"))
        if has_permission("nuevo_pedido"):
            enc_primary.append(("🛒 PEDIDO", "new_order"))
        if has_permission("cobrar"):
            enc_primary.append(("🪑 MESAS", "tables_cobrar"))
        if has_permission("todos_pedidos"):
            bell_label = f"🔔({pending_print}) IMPRIMIR" if pending_print > 0 else "📦 PEDIDOS"
            enc_primary.append((bell_label, "all_orders"))
        if has_permission("caja"):
            enc_primary.append(("💰 CAJA", "dashboard"))
        enc_primary.append(("⚙️ MÁS", "__more__"))
        enc_primary.append(("🚪 Salir", "__logout__"))
        nav_cols = st.columns([1] * len(enc_primary))
        for i, (label, target) in enumerate(enc_primary):
            with nav_cols[i]:
                if target == "__logout__":
                    _logout_btn()
                elif target == "__more__":
                    if st.button("⚙️ MÁS", use_container_width=True):
                        st.session_state.show_more_menu = not st.session_state.get("show_more_menu", False)
                        st.rerun()
                elif target == "all_orders" and pending_print > 0:
                    if st.button(label, use_container_width=True, type="primary", key="nav_enc_bell"):
                        st.session_state.page = "all_orders"
                        st.rerun()
                else:
                    _nav_button(label, target, current)
        if st.session_state.get("show_more_menu", False):
            enc_secondary = []
            if has_permission("reporte"):
                enc_secondary.append(("📄 Reporte", "daily_report"))
            if has_permission("historial"):
                enc_secondary.append(("🧾 Tickets", "ticket_history"))
            if has_permission("editar_menu"):
                enc_secondary.append(("🍽️ Editar Menú", "edit_menu"))
            if has_permission("gestionar_mozos"):
                enc_secondary.append(("👥 Mozos", "manage_mozos"))
            enc_secondary.append(("📋 Ver Menú", "menu"))
            if enc_secondary:
                ex_cols = st.columns([1] * min(len(enc_secondary), 6))
                for i, (label, target) in enumerate(enc_secondary):
                    with ex_cols[i % 6]:
                        _nav_button(label, target, current)
    else:
        # Mozo: fewer options
        nav_cols = st.columns([1, 1, 1, 1])
        with nav_cols[0]:
            _nav_button("🛒 PEDIDO", "new_order", current)
        with nav_cols[1]:
            _nav_button("📦 MIS PEDIDOS", "my_orders", current)
        with nav_cols[2]:
            _nav_button("📋 MENÚ", "menu", current)
        with nav_cols[3]:
            _logout_btn()
# ─── PAGE: MENU ───────────────────────────────────────────────────────────────
def page_menu():
    st.markdown("## 📋 Menú")
    # Menú del día highlight — muestra todos los ítems activos
    _mdd_defs = [
        ("menu_del_dia_active","menu_del_dia_price","menu_del_dia_description","Menú del Día (consultar plato)"),
        ("menu_del_dia_2_active","menu_del_dia_2_price","menu_del_dia_2_description","Ítem 2 del Día"),
        ("menu_del_dia_3_active","menu_del_dia_3_price","menu_del_dia_3_description","Ítem 3 del Día"),
        ("menu_del_dia_4_active","menu_del_dia_4_price","menu_del_dia_4_description","Ítem 4 del Día"),
    ]
    _mdd_active_items = [(get_setting(kp,"10000"), get_setting(kd,dd))
                         for ka,kp,kd,dd in _mdd_defs if get_setting(ka,"1")=="1"]
    if _mdd_active_items:
        lines = " &nbsp;|&nbsp; ".join(f"⭐ {d} — {fmt_price(float(p))}" for p,d in _mdd_active_items)
        st.markdown(f'<div style="background:linear-gradient(90deg,#5C1A1B,#7A2526);color:#D4A843;padding:0.8rem 1.2rem;border-radius:10px;font-weight:700;font-size:1rem;margin-bottom:1rem;text-align:center;">{lines}</div>', unsafe_allow_html=True)
    menu = get_menu()
    categories_seen = {}
    for item in menu:
        if not item["active"] or item["name"] in {"__menu_del_dia__","__mdd_2__","__mdd_3__","__mdd_4__"}:
            continue
        cat = item["category"]
        if cat not in categories_seen:
            categories_seen[cat] = []
        categories_seen[cat].append(item)
    for cat_name, items in categories_seen.items():
        st.markdown(f'<div class="cat-header">{cat_name}</div>', unsafe_allow_html=True)
        for item in items:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{item['name']}**")
            with col2:
                st.markdown(f"**{fmt_price(item['price'])}**")
# ─── PAGE: NEW ORDER ──────────────────────────────────────────────────────────
def page_new_order():
    # CSS: sticky right cart column + compact menu items
    st.markdown("""
    <style>
    /* Sticky cart panel — targets the container marked with #dylan-cart-anchor */
    [data-testid="stVerticalBlock"]:has(#dylan-cart-anchor) {
        position: sticky;
        top: 56px;
        max-height: calc(100vh - 60px);
        overflow-y: auto;
        padding-bottom: 2rem;
        scrollbar-width: thin;
    }
    /* Let the two-col layout stretch to top so sticky works */
    [data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }
    /* Compact menu item cards on order page */
    .order-item-card {
        background: #FFF8EC;
        border: 1.5px solid #D4A843;
        border-radius: 8px;
        padding: 0.4rem 0.6rem;
        margin-bottom: 0.3rem;
    }
    /* Cart item rows */
    .cart-row {
        border-bottom: 1px solid #F5E6C8;
        padding: 0.3rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    # Back button always visible for mozos (no nav bar in fullscreen)
    if st.button("← Volver a mis pedidos", key="back_new_order"):
        st.session_state.order_type = None
        st.session_state.order_table_num = ""
        st.session_state.page = "my_orders"
        st.rerun()
    st.markdown("## 🛒 Tomar Pedido")
    if "order_type" not in st.session_state:
        st.session_state.order_type = None
    if "order_table_num" not in st.session_state:
        st.session_state.order_table_num = ""
    order_type = st.session_state.order_type
    # ── STEP 1: Choose type ──
    if order_type is None:
        st.markdown("### ¿Dónde es el pedido?")
        ct1, ct2, ct3 = st.columns(3)
        with ct1:
            if st.button("🪑 MESA", use_container_width=True, type="primary"):
                st.session_state.order_type = "mesa"
                st.rerun()
        with ct2:
            if st.button("🧍 BARRA", use_container_width=True, type="primary"):
                # Auto-number barra orders for the day (order_type stays 'mostrador' for DB constraint)
                with get_db() as conn:
                    count = conn.execute("""
                        SELECT COUNT(*) c FROM orders
                        WHERE order_type='mostrador' AND date(created_at)=date('now','localtime')
                    """).fetchone()["c"]
                st.session_state.order_type = "mostrador"
                st.session_state.order_table_num = f"Barra #{count + 1}"
                st.rerun()
        with ct3:
            if st.button("🛍️ PARA LLEVAR / DELIVERY", use_container_width=True, type="primary"):
                with get_db() as conn:
                    count_dl = conn.execute("""
                        SELECT COUNT(*) c FROM orders
                        WHERE order_type='para_llevar' AND date(created_at)=date('now','localtime')
                    """).fetchone()["c"]
                st.session_state.order_type = "para_llevar"
                st.session_state.order_table_num = f"Delivery #{count_dl + 1}"
                st.rerun()
        return
    # ── STEP 2: Choose table (mesa only) ──
    if order_type == "mesa" and st.session_state.order_table_num == "":
        st.markdown("### ¿Qué mesa?")
        num_tables = get_num_tables()
        # Get currently occupied tables (any active order not yet delivered/cancelled)
        with get_db() as conn:
            occupied_rows = conn.execute("""
                SELECT o.table_num, u.display_name as mozo_name
                FROM orders o JOIN users u ON o.mozo_id = u.id
                WHERE o.status IN ('pendiente','preparando','listo','entregado')
                  AND o.paid = 0
                  AND o.order_type = 'mesa'
            """).fetchall()
        occupied_map = {row["table_num"]: row["mozo_name"] for row in occupied_rows}
        cols_per_row = 5
        for row_start in range(0, num_tables, cols_per_row):
            mesa_cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = row_start + j
                if idx < num_tables:
                    table_name = f"Mesa {idx+1}"
                    is_occupied = table_name in occupied_map
                    with mesa_cols[j]:
                        if is_occupied:
                            st.button(
                                f"🔴 {idx+1}",
                                key=f"mesa_btn_{idx+1}",
                                use_container_width=True,
                                disabled=True,
                                help=f"Ocupada — {occupied_map[table_name]}",
                            )
                        else:
                            if st.button(f"🪑 {idx+1}", key=f"mesa_btn_{idx+1}", use_container_width=True, type="primary"):
                                st.session_state.order_table_num = table_name
                                st.rerun()
        # Barra — also check if occupied
        barra_occupied = "Barra" in occupied_map
        if barra_occupied:
            st.button(f"🔴 BARRA — {occupied_map['Barra']}", use_container_width=True, disabled=True)
        else:
            if st.button("🍺 BARRA", use_container_width=True):
                st.session_state.order_table_num = "Barra"
                st.rerun()
        if occupied_map:
            st.caption("🔴 Mesa ocupada — se libera al cobrar el pedido")
        if st.button("⬅️ Volver", use_container_width=True):
            st.session_state.order_type = None
            st.rerun()
        return
    # ── STEP 3: Main order screen — two column layout ──
    type_labels = {"mesa": "🪑 Mesa", "mostrador": "🧍 Barra", "para_llevar": "🛍️ Para llevar/Delivery"}
    # Top bar: info + change
    with st.container(border=True):
        tc1, tc2, tc3 = st.columns([2, 2, 1])
        with tc1:
            st.markdown(f"**{type_labels.get(order_type, '')}** — **{st.session_state.order_table_num}**")
        with tc2:
            customer = st.text_input("Cliente", key="sel_customer", placeholder="Nombre cliente (opcional)", label_visibility="collapsed")
        with tc3:
            if st.button("✏️ Cambiar", key="change_type", use_container_width=True):
                st.session_state.order_type = None
                st.session_state.order_table_num = ""
                st.session_state.cart = []
                st.rerun()
    order_notes = st.text_input("Notas del pedido", key="sel_order_notes", placeholder="Alergias, indicaciones especiales...")
    # ── TWO COLUMNS: left=menu, right=cart (sticky) ──
    col_menu, col_cart = st.columns([3, 2])
    # ════════════════════════════════════════
    # LEFT COLUMN — menu de selección
    # ════════════════════════════════════════
    with col_menu:
        # ── BARRA DE BÚSQUEDA — siempre visible arriba ──
        search_query = st.text_input(
            "🔍 Buscar en la carta",
            key="menu_search",
            placeholder="Escribí el nombre del plato...",
            label_visibility="visible",
        )
        # Build full menu map (needed for both search and normal view)
        menu = get_menu()
        categories_map = {}
        _mdd_placeholders = {"__menu_del_dia__", "__mdd_2__", "__mdd_3__", "__mdd_4__"}
        all_menu_items = []
        for item in menu:
            if not item["active"] or item["name"] in _mdd_placeholders:
                continue
            cat = item["category"]
            if cat not in categories_map:
                categories_map[cat] = []
            categories_map[cat].append(item)
            all_menu_items.append(item)
        # Menú del día — solo se muestra si NO hay búsqueda activa
        _mdd_order_defs = [
            (-1,  "menu_del_dia_active",  "menu_del_dia_price",  "menu_del_dia_description",  "Menú del Día"),
            (-2,  "menu_del_dia_2_active", "menu_del_dia_2_price", "menu_del_dia_2_description", "Ítem 2 del Día"),
            (-3,  "menu_del_dia_3_active", "menu_del_dia_3_price", "menu_del_dia_3_description", "Ítem 3 del Día"),
            (-4,  "menu_del_dia_4_active", "menu_del_dia_4_price", "menu_del_dia_4_description", "Ítem 4 del Día"),
        ]
        _any_mdd = any(get_setting(ka,"1")=="1" for _,ka,*_ in _mdd_order_defs)
        if _any_mdd and not search_query.strip():
            with st.container(border=True):
                st.markdown(
                    '<div style="background:linear-gradient(90deg,#5C1A1B,#7A2526);color:#D4A843;'
                    'padding:0.35rem 0.8rem;border-radius:6px;font-weight:700;font-size:0.95rem;'
                    'margin-bottom:0.4rem;">⭐ MENÚ DEL DÍA</div>',
                    unsafe_allow_html=True,
                )
                for mid_val, ka, kp, kd, dd in _mdd_order_defs:
                    if get_setting(ka, "1") != "1":
                        continue
                    item_price = float(get_setting(kp, "10000"))
                    item_desc  = get_setting(kd, dd)
                    slug = str(abs(mid_val))
                    mc1, mc2, mc3 = st.columns([3, 1, 1])
                    with mc1:
                        st.markdown(f"**{item_desc}** — {fmt_price(item_price)}")
                    with mc2:
                        qty_val = st.number_input("", min_value=1, max_value=20, value=1,
                                                  key=f"qty_mdd_{slug}", label_visibility="collapsed")
                    with mc3:
                        if st.button("➕", key=f"add_mdd_{slug}", use_container_width=True):
                            note_val = st.session_state.get(f"note_mdd_{slug}", "")
                            st.session_state.cart.append({
                                "menu_item_id": mid_val,
                                "name": item_desc,
                                "price": item_price,
                                "quantity": qty_val,
                                "notes": note_val,
                            })
                            st.rerun()
                    st.text_input("Nota", key=f"note_mdd_{slug}",
                                  placeholder="Detalle...", label_visibility="collapsed")
        cat_names = list(categories_map.keys())
        if not cat_names:
            st.warning("No hay items activos en el menú.")
        elif search_query.strip():
            # MODO BÚSQUEDA — muestra resultados de todas las categorías
            q = search_query.strip().lower()
            search_results = [it for it in all_menu_items if q in it["name"].lower()]
            if not search_results:
                st.info("No se encontraron platos con ese nombre.")
            else:
                st.caption(f"**{len(search_results)} resultado(s)** para \"{search_query}\"")
            for item in search_results:
                with st.container(border=True):
                    r1, r2 = st.columns([3, 1])
                    with r1:
                        st.markdown(f"**{item['name']}**")
                        st.caption(f"📂 {item['category']}")
                    with r2:
                        st.markdown(f"**{fmt_price(item['price'])}**")
                    r3, r4, r5 = st.columns([3, 1, 1])
                    with r3:
                        st.text_input(
                            "Nota", key=f"note_{item['id']}",
                            placeholder="sin sal, bien cocido...",
                            label_visibility="collapsed",
                        )
                    with r4:
                        qty = st.number_input(
                            "Cant.", min_value=1, max_value=20, value=1,
                            key=f"qty_{item['id']}",
                            label_visibility="collapsed",
                        )
                    with r5:
                        if st.button("➕", key=f"add_{item['id']}", use_container_width=True):
                            note = st.session_state.get(f"note_{item['id']}", "")
                            st.session_state.cart.append({
                                "menu_item_id": item["id"],
                                "name": item["name"],
                                "price": item["price"],
                                "quantity": qty,
                                "notes": note,
                            })
                            st.rerun()
        else:
            # MODO NORMAL — navegación por categorías
            selected_cat = st.radio(
                "Categoría",
                cat_names,
                horizontal=True,
                key="order_cat_radio",
                label_visibility="collapsed",
            )
            items_in_cat = categories_map.get(selected_cat, [])
            for item in items_in_cat:
                with st.container(border=True):
                    r1, r2 = st.columns([3, 1])
                    with r1:
                        st.markdown(f"**{item['name']}**")
                    with r2:
                        st.markdown(f"**{fmt_price(item['price'])}**")
                    r3, r4, r5 = st.columns([3, 1, 1])
                    with r3:
                        st.text_input(
                            "Nota", key=f"note_{item['id']}",
                            placeholder="sin sal, bien cocido...",
                            label_visibility="collapsed",
                        )
                    with r4:
                        qty = st.number_input(
                            "Cant.", min_value=1, max_value=20, value=1,
                            key=f"qty_{item['id']}",
                            label_visibility="collapsed",
                        )
                    with r5:
                        if st.button("➕", key=f"add_{item['id']}", use_container_width=True):
                            note = st.session_state.get(f"note_{item['id']}", "")
                            st.session_state.cart.append({
                                "menu_item_id": item["id"],
                                "name": item["name"],
                                "price": item["price"],
                                "quantity": qty,
                                "notes": note,
                            })
                            st.rerun()
    # ════════════════════════════════════════
    # RIGHT COLUMN — carrito sticky
    # ════════════════════════════════════════
    with col_cart:
        # Invisible anchor so CSS :has() can target this column
        st.markdown('<div id="dylan-cart-anchor"></div>', unsafe_allow_html=True)
        cart = st.session_state.cart
        items_total = sum(ci["price"] * ci["quantity"] for ci in cart)
        # ── Delivery fee (only for para_llevar orders) ──
        delivery_fee = 0
        if order_type == "para_llevar":
            default_fee = int(get_setting("delivery_fee", "100"))
            delivery_fee = st.number_input(
                "🛍️ Recargo delivery ($)",
                min_value=0, step=100,
                value=st.session_state.get("_delivery_fee_input", default_fee),
                key="_delivery_fee_input",
                help="Recargo automático por delivery. Editá si el monto es distinto.",
            )
        total = items_total + delivery_fee
        st.markdown("### 🧾 Carrito")
        if not cart:
            st.info("← Agregá items del menú")
        else:
            items_to_remove = []
            for i, ci in enumerate(cart):
                subtotal = ci["price"] * ci["quantity"]
                with st.container(border=True):
                    cc1, cc2 = st.columns([4, 1])
                    with cc1:
                        label = f"**{ci['quantity']}x** {ci['name']}"
                        st.markdown(label)
                        line2 = fmt_price(subtotal)
                        if ci["notes"]:
                            line2 += f" · _{ci['notes']}_"
                        st.caption(line2)
                    with cc2:
                        if st.button("✕", key=f"rm_{i}", use_container_width=True):
                            items_to_remove.append(i)
            if items_to_remove:
                for idx in sorted(items_to_remove, reverse=True):
                    st.session_state.cart.pop(idx)
                st.rerun()
            # Total
            if delivery_fee > 0:
                st.caption(f"Subtotal: {fmt_price(items_total)} + Delivery: {fmt_price(delivery_fee)}")
            st.markdown(f"### 💰 {fmt_price(total)}")
            # ── Confirm / Vaciar ──
            if not st.session_state.get("confirm_order", False):
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✅ CONFIRMAR", type="primary", use_container_width=True):
                        st.session_state.confirm_order = True
                        st.session_state.confirm_total = total
                        st.rerun()
                with cc2:
                    if st.button("🗑️ Vaciar", use_container_width=True):
                        st.session_state.cart = []
                        st.rerun()
            # ── Payment flow (inside cart column) ──
            if st.session_state.get("confirm_order", False):
                st.divider()
                st.markdown(f"**¿Cómo paga?**")
                pay_cols = st.columns(3)
                with pay_cols[0]:
                    if st.button("⏳\nDESPUÉS", key="pay_later", use_container_width=True):
                        st.session_state.pay_method_selected = "pendiente"
                        st.rerun()
                with pay_cols[1]:
                    if st.button("💵\nEFECTIVO", key="pay_cash", use_container_width=True, type="primary"):
                        st.session_state.pay_method_selected = "efectivo"
                        st.rerun()
                with pay_cols[2]:
                    if st.button("📱\nTRANSF.", key="pay_transfer", use_container_width=True, type="primary"):
                        st.session_state.pay_method_selected = "transferencia"
                        st.rerun()
                selected_pay = st.session_state.get("pay_method_selected", "")
                if selected_pay == "efectivo":
                    st.markdown("**💵 Efectivo**")
                    cash_amount = st.number_input(
                        "¿Con cuánto paga?", min_value=0, step=1000,
                        value=int(total), key="cash_input",
                    )
                    change = cash_amount - total
                    if change >= 0:
                        st.success(f"**Vuelto: {fmt_price(change)}**")
                    else:
                        st.error(f"Falta {fmt_price(abs(change))}")
                    if st.button("✅ CONFIRMAR PEDIDO", key="confirm_cash", use_container_width=True, type="primary"):
                        if change >= 0:
                            order_id = _save_order(order_type, st.session_state.order_table_num,
                                                   customer, order_notes, total, cart,
                                                   "efectivo", 0, cash_amount, change)
                            _post_confirm(order_id)
                elif selected_pay == "transferencia":
                    st.markdown("**📱 Transferencia**")
                    st.success(f"Total: **{fmt_price(total)}**")
                    if st.button("✅ CONFIRMAR PEDIDO", key="confirm_transfer", use_container_width=True, type="primary"):
                        order_id = _save_order(order_type, st.session_state.order_table_num,
                                               customer, order_notes, total, cart,
                                               "transferencia", 0, total, 0)
                        _post_confirm(order_id)
                elif selected_pay == "pendiente":
                    st.markdown("**⏳ Paga al retirar**")
                    if st.button("✅ CONFIRMAR PEDIDO", key="confirm_later", use_container_width=True, type="primary"):
                        order_id = _save_order(order_type, st.session_state.order_table_num,
                                               customer, order_notes, total, cart,
                                               "pendiente", 0, 0, 0)
                        _post_confirm(order_id)
                if st.button("⬅️ Volver al carrito", key="cancel_confirm", use_container_width=True):
                    st.session_state.confirm_order = False
                    st.session_state.pop("pay_method_selected", None)
                    st.rerun()
def _save_order(order_type, table_num, customer, notes, total, cart,
                payment_method, paid, payment_amount, payment_change,
                payment_cash=0, payment_transfer=0):
    """Save order to DB with status 'preparando' (goes straight to kitchen)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute(
            """INSERT INTO orders
               (order_type, table_num, customer_name, mozo_id, status, notes, total,
                payment_method, paid, payment_amount, payment_change,
                payment_cash, payment_transfer, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                order_type, table_num, customer or "",
                st.session_state.user["id"],
                "preparando",  # Goes straight to kitchen!
                notes or "", total,
                payment_method, paid, payment_amount, payment_change,
                payment_cash, payment_transfer,
                now, now,
            ),
        )
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Map negative MDD ids → DB placeholder names
        _mdd_placeholder_map = {
            -1: "__menu_del_dia__",
            -2: "__mdd_2__",
            -3: "__mdd_3__",
            -4: "__mdd_4__",
        }
        for ci in cart:
            mid = ci["menu_item_id"]
            if mid in _mdd_placeholder_map:
                ph_name = _mdd_placeholder_map[mid]
                placeholder = conn.execute("SELECT id FROM menu_items WHERE name=?", (ph_name,)).fetchone()
                if not placeholder:
                    cat1 = conn.execute("SELECT id FROM categories LIMIT 1").fetchone()
                    cat_id = cat1["id"] if cat1 else 1
                    conn.execute("INSERT INTO menu_items (category_id, name, price, active) VALUES (?,?,?,?)",
                                 (cat_id, ph_name, ci["price"], 0))
                    mid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                else:
                    mid = placeholder["id"]
            conn.execute(
                "INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price, notes) VALUES (?,?,?,?,?)",
                (order_id, mid, ci["quantity"], ci["price"], ci["notes"]),
            )
    return order_id
def _post_confirm(order_id, print_ticket=False):  # print_ticket kept for compat, buttons always shown
    """Clean up state after order confirmed. Print buttons always visible on order_confirmed page."""
    st.session_state.cart = []
    st.session_state.confirm_order = False
    st.session_state.order_type = None
    st.session_state.order_table_num = ""
    st.session_state.pop("pay_method_selected", None)
    st.session_state.last_order_id = order_id
    st.session_state.page = "order_confirmed"
    st.rerun()
# ─── PAGE: ORDER CONFIRMED ─────────────────────────────────────────────────────
def page_order_confirmed():
    order_id = st.session_state.get("last_order_id", 0)
    if not order_id:
        st.session_state.page = "new_order"
        st.rerun()
        return
    st.markdown("## ✅ ¡Pedido Confirmado!")
    with get_db() as conn:
        order = conn.execute("""
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE o.id = ?
        """, (order_id,)).fetchone()
    if order:
        order = dict(order)
        type_labels = {"mesa": "🪑 Mesa", "mostrador": "🧍 Barra", "para_llevar": "🛍️ Para llevar/Delivery"}
        pay_labels = {"efectivo": "💵 Efectivo", "transferencia": "📱 Transferencia", "pendiente": "⏳ Pendiente"}
        is_owner_view = st.session_state.user.get("role") in ("admin", "dueno")
        is_delivery = order.get("order_type") == "para_llevar"
        with st.container(border=True):
            st.markdown(f"### Pedido #{order['id']}")
            st.markdown(f"**Tipo:** {type_labels.get(order['order_type'], order['order_type'])}")
            st.markdown(f"**Ubicación:** {order['table_num']}")
            if order['customer_name']:
                st.markdown(f"**Cliente:** {order['customer_name']}")
            st.markdown(f"**Total:** {fmt_price(order['total'])}")
            st.markdown(f"**Pago:** {pay_labels.get(order['payment_method'], 'N/A')}")
            if order['payment_method'] == 'efectivo' and order['payment_change'] > 0:
                st.markdown(f"**Pagó con:** {fmt_price(order['payment_amount'])} → **Vuelto: {fmt_price(order['payment_change'])}**")
            st.markdown(f"**Estado:** EN PREPARACIÓN 🔥")
        # ── Auto-print comanda delivery (dueño/PC only) ──
        if is_delivery and is_owner_view:
            import base64
            kitchen_html = generate_kitchen_html(order['id'])
            encoded = base64.b64encode(kitchen_html.encode("utf-8")).decode("ascii")
            st.markdown("### 🖨️ IMPRIMIR COMANDA DELIVERY")
            st.markdown("Hacé clic para enviar la comanda a cocina:")
            components.html(f"""<!DOCTYPE html>
<html><head><style>
  body {{ margin:0; padding:4px; font-family:sans-serif; }}
  #btn {{
    background:#C62828; color:white; border:none; padding:14px 18px;
    border-radius:8px; font-size:16px; font-weight:800; cursor:pointer;
    width:100%; display:flex; align-items:center; justify-content:center; gap:8px;
    transition: background 0.25s;
  }}
  #btn:hover {{ opacity:0.88; }}
  #btn.done {{ background:#2E7D32; }}
</style></head><body>
<button id="btn" onclick="doPrint()">🖨️ IMPRIMIR COMANDA COCINA</button>
<script>
function doPrint() {{
  var b64 = "{encoded}";
  var html = decodeURIComponent(escape(atob(b64)));
  var w = window.open('about:blank', '_blank', 'width=380,height=700,scrollbars=yes');
  if (!w) {{ alert('Habilitá los popups para imprimir.'); return; }}
  w.document.open(); w.document.write(html); w.document.close();
  w.focus();
  setTimeout(function() {{ w.print(); }}, 600);
  var btn = document.getElementById('btn');
  btn.style.background = '#2E7D32';
  btn.innerHTML = '✅ Comanda enviada a cocina';
}}
// Auto-trigger on load (works if popups are allowed)
window.addEventListener('load', function() {{ setTimeout(doPrint, 400); }});
</script>
</body></html>""", height=58)
    elif not is_owner_view:
        # Impresión solo desde la PC (caja) — no desde el celular del mozo
        st.info("🖨️ El ticket se imprime desde la caja (PC). Aparece en la cola de impresión del dueño.")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🛒 NUEVO PEDIDO", type="primary", use_container_width=True):
            st.session_state.order_type = None
            st.session_state.order_table_num = ""
            st.session_state.cart = []
            st.session_state.confirm_order = False
            st.session_state.pop("pay_method_selected", None)
            st.session_state.page = "new_order"
            st.rerun()
    with c2:
        if st.button("📦 VER MIS PEDIDOS", use_container_width=True):
            st.session_state.page = "my_orders"
            st.rerun()
# ─── CANCEL + REFUND HELPER ───────────────────────────────────────────────────
def _show_cancel_refund_ui(order, key_prefix):
    """
    Shows cancel button. If order was paid, asks for refund amount + reason.
    Handles DB update. Returns True if cancelled (caller should st.rerun()).
    """
    order_id = order["id"]
    was_paid = order.get("paid", 0) == 1
    already_cancelling = st.session_state.get(f"cancelling_{key_prefix}_{order_id}", False)
    if not already_cancelling:
        if st.button(f"❌ Anular Pedido #{order_id}", key=f"cancel_btn_{key_prefix}_{order_id}", use_container_width=True):
            st.session_state[f"cancelling_{key_prefix}_{order_id}"] = True
            st.rerun()
        return False
    # Show cancellation form
    with st.container(border=True):
        st.markdown(f"**⚠️ Anular Pedido #{order_id}**")
        if was_paid:
            pay_label = {"efectivo": "💵 Efectivo", "transferencia": "📱 Transferencia", "pendiente": "⏳ Pendiente"}.get(order.get("payment_method", ""), "")
            st.warning(f"Este pedido fue cobrado ({pay_label} — {fmt_price(order['total'])}). ¿Corresponde devolver dinero?")
            refund_yn = st.radio(
                "¿Registrar devolución?",
                ["Sí, devolver dinero", "No, no hubo devolución"],
                key=f"refund_yn_{key_prefix}_{order_id}",
                horizontal=True,
            )
            if refund_yn == "Sí, devolver dinero":
                refund_amount = st.number_input(
                    "Monto a devolver ($)",
                    min_value=0.0, max_value=float(order["total"]),
                    value=float(order["total"]),
                    step=1000.0,
                    key=f"refund_amt_{key_prefix}_{order_id}",
                )
            else:
                refund_amount = 0.0
        else:
            refund_amount = 0.0
        refund_reason = st.text_input(
            "Motivo de la anulación",
            key=f"refund_reason_{key_prefix}_{order_id}",
            placeholder="Ej: cliente se arrepintió, error en pedido...",
        )
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("✅ Confirmar Anulación", key=f"confirm_cancel_{key_prefix}_{order_id}", type="primary", use_container_width=True):
                if not refund_reason.strip():
                    st.error("Ingresá el motivo de la anulación.")
                else:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE orders SET status='cancelado', refund_amount=?, refund_reason=?, updated_at=? WHERE id=?",
                            (refund_amount, refund_reason.strip(), now, order_id),
                        )
                    del st.session_state[f"cancelling_{key_prefix}_{order_id}"]
                    if was_paid and refund_amount > 0:
                        st.success(f"Pedido #{order_id} anulado. Devolución registrada: {fmt_price(refund_amount)}")
                    else:
                        st.success(f"Pedido #{order_id} anulado.")
                    st.rerun()
                    return True
        with cc2:
            if st.button("⬅️ No anular", key=f"abort_cancel_{key_prefix}_{order_id}", use_container_width=True):
                del st.session_state[f"cancelling_{key_prefix}_{order_id}"]
                st.rerun()
    return False
# ─── PAGE: MY ORDERS ──────────────────────────────────────────────────────────
def page_my_orders():
    mozo_id = st.session_state.user["id"]
    now = datetime.now()
    with get_db() as conn:
        all_orders = conn.execute("""
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE o.mozo_id = ?
              AND date(o.created_at) = date('now','localtime')
            ORDER BY
                CASE o.status
                    WHEN 'listo'      THEN 1
                    WHEN 'pendiente'  THEN 2
                    WHEN 'preparando' THEN 3
                    WHEN 'entregado'  THEN 4
                    WHEN 'cancelado'  THEN 5
                END,
                o.created_at DESC
        """, (mozo_id,)).fetchall()
    # entregado+no cobrado sigue siendo "activo" (kitchen done, pending payment)
    activos   = [o for o in all_orders if not o["paid"] and o["status"] != "cancelado"]
    cerrados  = [o for o in all_orders if o["paid"] or o["status"] == "cancelado"]
    # ── Refresh button ──
    if st.button("🔄 Actualizar", use_container_width=True, type="primary"):
        st.rerun()
    # ── Alert: orders ready (kitchen done, pending payment/pickup) ──
    listos = [o for o in activos if o["status"] in ("listo", "entregado")]
    if listos:
        mesas = ", ".join(o["table_num"] for o in listos)
        st.markdown(
            f'<div style="background:#2E7D32;color:white;padding:0.8rem 1rem;'
            f'border-radius:10px;font-weight:700;font-size:1.1rem;text-align:center;margin-bottom:0.8rem;">'
            f'🔔 ¡LISTO PARA COBRAR! → {mesas}</div>',
            unsafe_allow_html=True,
        )
    # ── Summary counts ──
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Activos", len(activos))
    sc2.metric("Listos 🔔", len(listos))
    sc3.metric("Entregados hoy", len([o for o in cerrados if o["status"] == "entregado"]))
    st.divider()
    # ── Active orders ──
    if not activos:
        st.info("No tenés pedidos activos ahora.")
    else:
        st.markdown("### 🟡 En curso")
        for order in activos:
            order = dict(order)
            created = datetime.strptime(order["created_at"], "%Y-%m-%d %H:%M:%S")
            elapsed = int((now - created).total_seconds() / 60)
            is_listo = order["status"] in ("listo", "entregado")  # kitchen done, needs payment
            border_color = "#2E7D32" if is_listo else "#F9A825" if order["status"] == "preparando" else "#555"
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**Pedido #{order['id']}** — {order['table_num']}")
                    if order["customer_name"]:
                        st.caption(f"Cliente: {order['customer_name']}")
                with c2:
                    st.markdown(status_badge(order["status"]), unsafe_allow_html=True)
                with c3:
                    tc = time_color(elapsed)
                    st.markdown(f'<span class="{tc}">{elapsed} min</span>', unsafe_allow_html=True)
                    st.markdown(f"**{fmt_price(order['total'])}**")
                # Items
                with get_db() as conn:
                    items = conn.execute("""
                        SELECT oi.*, mi.name as item_name
                        FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
                        WHERE oi.order_id = ?
                    """, (order["id"],)).fetchall()
                for it in items:
                    line = f"• **{it['quantity']}x** {display_item_name(it['item_name'])}"
                    if it["notes"]:
                        line += f" _{it['notes']}_"
                    st.markdown(line)
                if order["notes"]:
                    st.warning(f"📝 {order['notes']}")
                # ── EDITAR PEDIDO ──
                render_edit_panel(order, key_prefix=f"mo_{order['id']}_")
                # ── COBRAR ──
                cobrar_key = f"cobrar_{order['id']}"
                if order.get("paid"):
                    st.success("✅ Ya cobrado")
                elif not st.session_state.get(cobrar_key):
                    btn_label = "💰 COBRAR" if is_listo else "💰 Cobrar"
                    btn_type = "primary" if is_listo else "secondary"
                    if st.button(btn_label, key=f"cobrar_btn_{order['id']}",
                                 use_container_width=True, type=btn_type):
                        st.session_state[cobrar_key] = True
                        st.rerun()
                else:
                    st.markdown(f"**💰 Cobrar — Pedido #{order['id']} — {fmt_price(order['total'])}**")
                    method = st.radio(
                        "Método", ["efectivo", "transferencia", "mixto"],
                        key=f"cobrar_method_{order['id']}", horizontal=True,
                    )
                    cash_paid = 0.0
                    transfer_paid = 0.0
                    if method == "efectivo":
                        amount = st.number_input(
                            "Recibido $", min_value=float(order["total"]),
                            value=float(order["total"]), step=1000.0,
                            key=f"cobrar_amt_{order['id']}",
                        )
                        change = amount - order["total"]
                        cash_paid = amount
                        if change > 0:
                            st.success(f"Vuelto: **{fmt_price(change)}**")
                    elif method == "transferencia":
                        amount = float(order["total"])
                        change = 0.0
                        transfer_paid = amount
                    else:  # mixto
                        mx1, mx2 = st.columns(2)
                        with mx1:
                            cash_paid = st.number_input(
                                "💵 Efectivo $", min_value=0.0, value=0.0, step=1000.0,
                                key=f"cobrar_cash_{order['id']}",
                            )
                        with mx2:
                            transfer_default = max(0.0, float(order["total"]) - cash_paid)
                            transfer_paid = st.number_input(
                                "📱 Transferencia $", min_value=0.0,
                                value=transfer_default, step=1000.0,
                                key=f"cobrar_transfer_{order['id']}",
                            )
                        amount = cash_paid + transfer_paid
                        change = amount - order["total"]
                        if change > 0:
                            st.success(f"Vuelto: **{fmt_price(change)}**")
                        elif change < 0:
                            st.error(f"Falta: **{fmt_price(-change)}**")
                        else:
                            st.success("✅ Monto exacto")
                    can_confirm = (method != "mixto") or (cash_paid + transfer_paid >= float(order["total"]))
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("✅ Confirmar cobro", key=f"cobrar_ok_{order['id']}",
                                     type="primary", use_container_width=True,
                                     disabled=not can_confirm):
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            with get_db() as conn:
                                conn.execute("""
                                    UPDATE orders SET
                                        status='entregado', paid=1,
                                        payment_method=?, payment_amount=?,
                                        payment_change=?, payment_cash=?,
                                        payment_transfer=?, updated_at=?
                                    WHERE id=?
                                """, (method, amount, max(0.0, change),
                                      cash_paid, transfer_paid, now_str, order["id"]))
                            del st.session_state[cobrar_key]
                            st.success(f"✅ ¡Cobrado! {fmt_price(order['total'])}")
                            st.rerun()
                    with cc2:
                        if st.button("Cancelar", key=f"cobrar_cancel_{order['id']}",
                                     use_container_width=True):
                            del st.session_state[cobrar_key]
                            st.rerun()
                _show_cancel_refund_ui(order, "myorders")
    # ── Delivered today ──
    if cerrados:
        with st.expander(f"✅ Historial de hoy ({len(cerrados)} pedidos)"):
            for order in cerrados:
                order = dict(order)
                icon = "✅" if order["status"] == "entregado" else "❌"
                st.markdown(
                    f"{icon} **#{order['id']}** — {order['table_num']} — "
                    f"{fmt_price(order['total'])} — {order['status']}"
                )
# ─── PAGE: CAJA (OWNER) ───────────────────────────────────────────────────────
def page_dashboard():
    reg = get_open_register()
    # ── No register open: show OPEN button ──
    if reg is None:
        st.markdown("## 💰 Caja — Cerrada")
        st.info("La caja está cerrada. Abrila para empezar a registrar ventas.")
        with st.container(border=True):
            st.markdown("### Abrir Caja")
            opening = st.number_input(
                "Fondo de caja inicial ($)",
                min_value=0, step=5000, value=50000,
                key="caja_opening",
            )
            if st.button("💰 ABRIR CAJA", type="primary", use_container_width=True):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO cash_registers (opened_by, opening_amount, opened_at) VALUES (?,?,?)",
                        (st.session_state.user["id"], opening, now),
                    )
                st.success(f"Caja abierta con fondo de {fmt_price(opening)}")
                st.rerun()
        # Show history
        _show_register_history()
        return
    # ── Register is open: show live dashboard ──
    st.markdown("## 💰 Caja — Abierta")
    totals = get_register_live_totals(reg["id"])
    # Status bar
    opened_time = reg["opened_at"][:16] if reg["opened_at"] else ""
    st.caption(f"Abierta desde: {opened_time} | Fondo inicial: {fmt_price(reg['opening_amount'])}")
    # KPIs
    with st.container(horizontal=True):
        st.metric("Ventas Totales", fmt_price(totals["total_sales"]), border=True)
        st.metric("Pedidos", str(totals["orders_count"]), border=True)
        st.metric("Ticket Promedio", fmt_price(totals["avg_ticket"]), border=True)
    with st.container(horizontal=True):
        st.metric("💵 Efectivo", fmt_price(totals["cash_sales"]), border=True)
        st.metric("📱 Transferencias", fmt_price(totals["transfer_sales"]), border=True)
        st.metric("⏳ Pendiente", fmt_price(totals["pending_sales"]), border=True)
    if totals.get("refund_count", 0) > 0:
        with st.container(border=True):
            st.markdown(f"**⚠️ Devoluciones registradas:** {totals['refund_count']} pedido(s) — Total devuelto: **{fmt_price(totals['total_refunds'])}**")
            st.caption("Las ventas y el efectivo esperado ya descontaron estas devoluciones.")
    with st.container(border=True):
        st.markdown(f"**Efectivo esperado en caja:** {fmt_price(totals['expected_cash'])}")
        st.caption(f"(Fondo {fmt_price(reg['opening_amount'])} + Efectivo neto {fmt_price(totals['cash_sales'])} - Vueltos {fmt_price(totals['change_given'])})")
    # Refresh
    if st.button("🔄 Actualizar", use_container_width=True):
        st.rerun()
    # Top items
    st.markdown("### Platos más vendidos")
    with get_db() as conn:
        top_items = conn.execute("""
            SELECT mi.name, SUM(oi.quantity) as qty, SUM(oi.quantity * oi.unit_price) as revenue
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.created_at >= ? AND o.status != 'cancelado'
            GROUP BY mi.name ORDER BY qty DESC LIMIT 10
        """, (reg["opened_at"],)).fetchall()
    if top_items:
        import pandas as pd
        df = pd.DataFrame([dict(r) for r in top_items])
        df.columns = ["Plato", "Cantidad", "Ingresos"]
        df["Ingresos"] = df["Ingresos"].apply(fmt_price)
        st.dataframe(df, hide_index=True, use_container_width=True)
    # ── CLOSE REGISTER ──
    st.divider()
    st.markdown("### 🔒 Cerrar Caja")
    if st.button("🔒 CERRAR CAJA", use_container_width=True):
        st.session_state.closing_register = True
        st.rerun()
    if st.session_state.get("closing_register", False):
        with st.container(border=True):
            st.markdown("**Arqueo de caja — Contá el dinero real:**")
            real_cash = st.number_input(
                "¿Cuánto hay en la caja? ($)",
                min_value=0, step=1000, value=int(totals["expected_cash"]),
                key="closing_real_cash",
            )
            expected = totals["expected_cash"]
            diff = real_cash - expected
            if diff > 0:
                st.success(f"Sobrante: +{fmt_price(diff)}")
            elif diff < 0:
                st.error(f"Faltante: {fmt_price(diff)}")
            else:
                st.success("La caja cuadra perfectamente.")
            closing_notes = st.text_input("Notas del cierre (opcional)", key="closing_notes")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ CONFIRMAR CIERRE", type="primary", use_container_width=True):
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with get_db() as conn:
                        conn.execute("""
                            UPDATE cash_registers SET
                                status='closed',
                                closing_amount_real=?,
                                closing_amount_expected=?,
                                difference=?,
                                total_cash_sales=?,
                                total_transfer_sales=?,
                                total_pending=?,
                                total_change_given=?,
                                orders_count=?,
                                notes=?,
                                closed_at=?
                            WHERE id=?
                        """, (
                            real_cash, expected, diff,
                            totals["cash_sales"], totals["transfer_sales"],
                            totals["pending_sales"], totals["change_given"],
                            totals["orders_count"], closing_notes or "", now,
                            reg["id"],
                        ))
                    st.session_state.closing_register = False
                    st.success("Caja cerrada correctamente!")
                    st.rerun()
            with c2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.closing_register = False
                    st.rerun()
    # History
    _show_register_history()
def _show_register_history():
    """Show past cash register closings."""
    st.divider()
    st.markdown("### 📋 Historial de Cierres")
    with get_db() as conn:
        history = conn.execute("""
            SELECT cr.*, u.display_name as opened_by_name
            FROM cash_registers cr
            JOIN users u ON cr.opened_by = u.id
            WHERE cr.status = 'closed'
            ORDER BY cr.closed_at DESC
            LIMIT 15
        """).fetchall()
    if not history:
        st.caption("No hay cierres de caja registrados.")
        return
    for h in history:
        h = dict(h)
        closed_date = h["closed_at"][:16] if h["closed_at"] else "?"
        opened_date = h["opened_at"][:16] if h["opened_at"] else "?"
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"**{closed_date}**")
                st.caption(f"Abierta: {opened_date} | Por: {h['opened_by_name']}")
            with c2:
                st.markdown(f"**Ventas: {fmt_price(h['total_cash_sales'] + h['total_transfer_sales'])}**")
                st.caption(f"Efectivo: {fmt_price(h['total_cash_sales'])} | Transf: {fmt_price(h['total_transfer_sales'])}")
            with c3:
                diff = h["difference"]
                if diff > 0:
                    st.markdown(f"**Sobrante: +{fmt_price(diff)}**")
                elif diff < 0:
                    st.markdown(f"**Faltante: {fmt_price(diff)}**")
                else:
                    st.markdown("**Cuadra ✅**")
                st.caption(f"Pedidos: {h['orders_count']}")
            if h["notes"]:
                st.caption(f"Notas: {h['notes']}")
# ─── PAGE: EDIT MENU (OWNER) ──────────────────────────────────────────────────
def page_edit_menu():
    st.markdown("## 🍽️ Editar Menú")
    tab_edit, tab_add, tab_mdd = st.tabs(["Editar Items", "Agregar Item", "🍽️ Menú del Día"])
    with tab_edit:
        menu = get_menu()
        categories_map = {}
        for item in menu:
            cat = item["category"]
            if cat not in categories_map:
                categories_map[cat] = []
            categories_map[cat].append(item)
        if st.session_state.get("_menu_msg"):
            st.success(st.session_state.pop("_menu_msg"))
        st.caption("⏱ = tiempo estimado de preparación en minutos (0 = sin estimación). El sistema lo aprende automáticamente cuando se completan pedidos.")
        for cat_name, items in categories_map.items():
            st.markdown(f'<div class="cat-header">{cat_name}</div>', unsafe_allow_html=True)
            for item in items:
                with st.container(border=True):
                    c1, c2, c3, c4, c5, c6 = st.columns([3, 1.5, 0.8, 1, 0.6, 0.6])
                    with c1:
                        new_name = st.text_input(
                            "Nombre", value=item["name"],
                            key=f"edit_name_{item['id']}",
                            label_visibility="collapsed",
                        )
                    with c2:
                        new_price = st.number_input(
                            "Precio", value=int(item["price"]),
                            min_value=0, step=500,
                            key=f"edit_price_{item['id']}",
                            label_visibility="collapsed",
                        )
                    with c3:
                        # Cook time: show current avg or 0 if None
                        current_time = int(item["avg_cook_minutes"]) if item["avg_cook_minutes"] else 0
                        new_cook_time = st.number_input(
                            "⏱ min",
                            value=current_time,
                            min_value=0, max_value=120, step=1,
                            key=f"edit_cook_{item['id']}",
                            help="Tiempo de preparación estimado (minutos). 0 = sin estimación.",
                        )
                    with c4:
                        active = st.checkbox(
                            "Activo",
                            value=bool(item["active"]),
                            key=f"edit_active_{item['id']}",
                        )
                    with c5:
                        if st.button("💾", key=f"save_{item['id']}", help="Guardar cambios"):
                            cook_val = float(new_cook_time) if new_cook_time > 0 else None
                            with get_db() as conn:
                                conn.execute(
                                    "UPDATE menu_items SET name=?, price=?, active=?, avg_cook_minutes=? WHERE id=?",
                                    (new_name, new_price, 1 if active else 0, cook_val, item["id"]),
                                )
                            st.session_state["_menu_msg"] = f"✅ '{new_name}' actualizado!"
                            st.rerun()
                    with c6:
                        if st.button("🗑️", key=f"del_{item['id']}", help="Eliminar plato"):
                            with get_db() as conn:
                                used = conn.execute(
                                    "SELECT COUNT(*) c FROM order_items WHERE menu_item_id=?",
                                    (item["id"],)
                                ).fetchone()["c"]
                                if used == 0:
                                    conn.execute("DELETE FROM menu_items WHERE id=?", (item["id"],))
                                    st.session_state["_menu_msg"] = f"🗑️ '{item['name']}' eliminado."
                                else:
                                    conn.execute("UPDATE menu_items SET active=0 WHERE id=?", (item["id"],))
                                    st.session_state["_menu_msg"] = f"⚠️ '{item['name']}' desactivado (tiene pedidos históricos)."
                            st.rerun()
    with tab_add:
        with st.container(border=True):
            st.markdown("### Agregar nuevo item")
            cats = get_categories()
            cat_options = {c["name"]: c["id"] for c in cats}
            new_cat = st.selectbox("Categoría", list(cat_options.keys()), key="new_item_cat")
            new_item_name = st.text_input("Nombre del plato", key="new_item_name")
            new_item_price = st.number_input("Precio ($)", min_value=0, step=500, key="new_item_price")
            if st.button("Agregar al Menú", type="primary", use_container_width=True):
                if new_item_name and new_item_price > 0:
                    with get_db() as conn:
                        conn.execute(
                            "INSERT INTO menu_items (category_id, name, price) VALUES (?,?,?)",
                            (cat_options[new_cat], new_item_name, new_item_price),
                        )
                    st.success(f"'{new_item_name}' agregado!")
                    st.rerun()
                else:
                    st.error("Complete nombre y precio.")
        # Add category — wrapped in form to avoid Streamlit state issues
        with st.container(border=True):
            st.markdown("### Agregar nueva categoría")
            if st.session_state.get("_cat_created_msg"):
                st.success(st.session_state.pop("_cat_created_msg"))
            with st.form("form_nueva_categoria", clear_on_submit=True):
                new_cat_name = st.text_input("Nombre de la categoría", placeholder="Ej: ENTRADAS")
                submitted_cat = st.form_submit_button("➕ Crear Categoría", use_container_width=True, type="primary")
            if submitted_cat:
                if new_cat_name.strip():
                    with get_db() as conn:
                        existing = conn.execute("SELECT COUNT(*) c FROM categories WHERE name=?", (new_cat_name.strip().upper(),)).fetchone()
                        if existing["c"] == 0:
                            max_order = conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 as m FROM categories").fetchone()["m"]
                            conn.execute("INSERT INTO categories (name, sort_order) VALUES (?,?)", (new_cat_name.strip().upper(), max_order))
                            st.session_state["_cat_created_msg"] = f"✅ Categoría '{new_cat_name.strip().upper()}' creada!"
                            st.rerun()
                        else:
                            st.warning("Esa categoría ya existe.")
                else:
                    st.error("Ingrese un nombre.")
    with tab_mdd:
        if st.session_state.get("_mdd_msg"):
            st.success(st.session_state.pop("_mdd_msg"))
        # Los 4 ítems del Menú del Día
        mdd_items = [
            ("1", "menu_del_dia_active",   "menu_del_dia_price",   "menu_del_dia_description",   "Menú del Día (consultar plato)"),
            ("2", "menu_del_dia_2_active",  "menu_del_dia_2_price",  "menu_del_dia_2_description",  "Ítem 2 del Día (consultar)"),
            ("3", "menu_del_dia_3_active",  "menu_del_dia_3_price",  "menu_del_dia_3_description",  "Ítem 3 del Día (consultar)"),
            ("4", "menu_del_dia_4_active",  "menu_del_dia_4_price",  "menu_del_dia_4_description",  "Ítem 4 del Día (consultar)"),
        ]
        for num, key_active, key_price, key_desc, default_desc in mdd_items:
            with st.container(border=True):
                st.markdown(f"#### Ítem {num}")
                cur_active = get_setting(key_active, "1") == "1"
                cur_price  = int(get_setting(key_price, "10000"))
                cur_desc   = get_setting(key_desc, default_desc)
                col_a, col_b, col_c = st.columns([3, 1.5, 1])
                with col_a:
                    new_desc = st.text_input("Descripción", value=cur_desc, key=f"mdd_desc_{num}")
                with col_b:
                    new_price = st.number_input("Precio ($)", min_value=0, step=500, value=cur_price, key=f"mdd_price_{num}")
                with col_c:
                    new_active = st.checkbox("Activo", value=cur_active, key=f"mdd_active_{num}")
                if st.button(f"💾 Guardar Ítem {num}", key=f"mdd_save_{num}", use_container_width=True, type="primary"):
                    set_setting(key_active, "1" if new_active else "0")
                    set_setting(key_price,  str(int(new_price)))
                    set_setting(key_desc,   new_desc)
                    st.session_state["_mdd_msg"] = f"✅ Ítem {num}: {new_desc} — {fmt_price(new_price)}"
                    st.rerun()
# ─── PAGE: ALL ORDERS (OWNER) ─────────────────────────────────────────────────
def _render_order_list(orders):
    """Render a list of orders as cards with action buttons."""
    if not orders:
        st.info("No hay pedidos para mostrar.")
        return
    for order in orders:
        order = dict(order)
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"**Pedido #{order['id']}** — {order['table_num']}")
                st.caption(f"Mozo: {order['mozo_name']} | {order['created_at'][:16]}")
                if order["customer_name"]:
                    st.caption(f"Cliente: {order['customer_name']}")
            with c2:
                st.markdown(status_badge(order["status"]), unsafe_allow_html=True)
            with c3:
                st.markdown(f"**{fmt_price(order['total'])}**")
            # Items
            with get_db() as conn:
                items = conn.execute("""
                    SELECT oi.*, mi.name as item_name
                    FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE oi.order_id = ?
                """, (order["id"],)).fetchall()
            for it in items:
                line = f"  {it['quantity']}x {display_item_name(it['item_name'])}"
                if it["notes"]:
                    line += f" _({it['notes']})_"
                st.markdown(line)
            # Show refund info if order was cancelled with refund
            if order["status"] == "cancelado" and order.get("refund_amount", 0) > 0:
                st.markdown(f'<span style="color:#C62828;font-weight:600;">↩ Devuelto: {fmt_price(order["refund_amount"])} — {order.get("refund_reason","")}</span>', unsafe_allow_html=True)
            elif order["status"] == "cancelado" and order.get("refund_reason", ""):
                st.caption(f"Motivo cancelación: {order['refund_reason']}")
            # Status change buttons + ticket
            # Note: LISTO/ENTREGADO buttons removed — only kitchen (Vista Cocina) handles those transitions
            status = order["status"]
            # ── COBRAR (dueño/caja — para pedidos sin cobrar) ──
            if status != "cancelado" and not order.get("paid"):
                cobrar_key = f"ao_cobrar_{order['id']}"
                if not st.session_state.get(cobrar_key):
                    _ao_listo = status in ("listo", "entregado")
                    btn_label = "💰 COBRAR" if _ao_listo else "💰 Cobrar"
                    btn_type = "primary" if _ao_listo else "secondary"
                    if st.button(btn_label, key=f"ao_cobrar_btn_{order['id']}",
                                 use_container_width=True, type=btn_type):
                        st.session_state[cobrar_key] = True
                        st.rerun()
                else:
                    with st.container(border=True):
                        st.markdown(f"**💰 Cobrar — Pedido #{order['id']} — {fmt_price(order['total'])}**")
                        method = st.radio(
                            "Método de pago", ["efectivo", "transferencia", "mixto"],
                            key=f"ao_cobrar_method_{order['id']}", horizontal=True,
                        )
                        ao_cash_paid = 0.0
                        ao_transfer_paid = 0.0
                        if method == "efectivo":
                            amount = st.number_input(
                                "Recibido $", min_value=float(order["total"]),
                                value=float(order["total"]), step=1000.0,
                                key=f"ao_cobrar_amt_{order['id']}",
                            )
                            change = amount - order["total"]
                            ao_cash_paid = amount
                            if change > 0:
                                st.success(f"Vuelto: **{fmt_price(change)}**")
                        elif method == "transferencia":
                            amount = float(order["total"])
                            change = 0.0
                            ao_transfer_paid = amount
                        else:  # mixto
                            amx1, amx2 = st.columns(2)
                            with amx1:
                                ao_cash_paid = st.number_input(
                                    "💵 Efectivo $", min_value=0.0, value=0.0, step=1000.0,
                                    key=f"ao_cobrar_cash_{order['id']}",
                                )
                            with amx2:
                                ao_transfer_default = max(0.0, float(order["total"]) - ao_cash_paid)
                                ao_transfer_paid = st.number_input(
                                    "📱 Transferencia $", min_value=0.0,
                                    value=ao_transfer_default, step=1000.0,
                                    key=f"ao_cobrar_transfer_{order['id']}",
                                )
                            amount = ao_cash_paid + ao_transfer_paid
                            change = amount - order["total"]
                            if change > 0:
                                st.success(f"Vuelto: **{fmt_price(change)}**")
                            elif change < 0:
                                st.error(f"Falta: **{fmt_price(-change)}**")
                            else:
                                st.success("✅ Monto exacto")
                        ao_can_confirm = (method != "mixto") or (ao_cash_paid + ao_transfer_paid >= float(order["total"]))
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("✅ Confirmar cobro", key=f"ao_cobrar_ok_{order['id']}",
                                         type="primary", use_container_width=True,
                                         disabled=not ao_can_confirm):
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                with get_db() as conn:
                                    conn.execute("""
                                        UPDATE orders SET
                                            status='entregado', paid=1,
                                            payment_method=?, payment_amount=?,
                                            payment_change=?, payment_cash=?,
                                            payment_transfer=?, updated_at=?
                                        WHERE id=?
                                    """, (method, amount, max(0.0, change),
                                          ao_cash_paid, ao_transfer_paid, now_str, order["id"]))
                                del st.session_state[cobrar_key]
                                st.success(f"✅ ¡Cobrado! {fmt_price(order['total'])}")
                                st.rerun()
                        with cc2:
                            if st.button("Cancelar", key=f"ao_cobrar_cancel_{order['id']}",
                                         use_container_width=True):
                                del st.session_state[cobrar_key]
                                st.rerun()
            elif order.get("paid"):
                pay_labels = {"efectivo": "💵 Efectivo", "transferencia": "📱 Transferencia",
                              "mixto": "💳 Mixto", "pendiente": "⏳ Pendiente"}
                st.success(f"✅ Cobrado — {pay_labels.get(order.get('payment_method',''), '')}")
            # Anular con devolución (todos los estados salvo ya cancelado)
            if status != "cancelado":
                _show_cancel_refund_ui(order, "allorders")
            # Print section with status tracking (owner/cashier only)
            render_print_section(order["id"], key_prefix=f"ao_{order['id']}")
def page_all_orders():
    st.markdown("## 📦 Todos los Pedidos")
    # Auto-refresh every 30 seconds so new orders appear automatically
    if _HAS_AUTOREFRESH:
        st_autorefresh(interval=30_000, limit=None, key="all_orders_refresh")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_status = st.selectbox(
            "Filtrar por estado",
            ["Todos", "pendiente", "preparando", "listo", "entregado", "cancelado"],
            key="filter_status",
        )
    with col_f2:
        filter_date = st.date_input("Fecha", value=datetime.now().date(), key="filter_date")
    date_str = filter_date.strftime("%Y-%m-%d")
    def fetch_orders(types):
        placeholders = ",".join("?" * len(types))
        q = f"""
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE date(o.created_at) = ? AND o.order_type IN ({placeholders})
        """
        params = [date_str] + list(types)
        if filter_status != "Todos":
            q += " AND o.status = ?"
            params.append(filter_status)
        q += " ORDER BY o.created_at DESC"
        with get_db() as conn:
            return conn.execute(q, params).fetchall()
    tab_print, tab_mesa, tab_barra, tab_delivery = st.tabs([
        "🖨️ Cola de Impresión", "🪑 Mesas", "🧍 Barra", "🛍️ Delivery"
    ])
    with tab_print:
        # Show all orders from today not yet printed (except cancelled)
        with get_db() as conn:
            pending_print = conn.execute("""
                SELECT o.*, u.display_name as mozo_name
                FROM orders o JOIN users u ON o.mozo_id = u.id
                WHERE date(o.created_at) = ?
                  AND o.printed_at IS NULL
                  AND o.status != 'cancelado'
                ORDER BY o.created_at ASC
            """, (date_str,)).fetchall()
        if not pending_print:
            st.success("✅ Todo impreso al día.")
        else:
            type_labels = {"mesa": "🪑 Mesa", "mostrador": "🧍 Barra", "barra": "🧍 Barra", "para_llevar": "🛍️ Delivery"}
            st.warning(f"**{len(pending_print)} pedido(s) pendientes de imprimir**")
            for order in [dict(o) for o in pending_print]:
                with st.container(border=True):
                    ci1, ci2 = st.columns([3, 1])
                    with ci1:
                        st.markdown(f"**#{order['id']}** — {type_labels.get(order['order_type'], '')} — **{order['table_num']}**")
                        st.caption(f"Mozo: {order['mozo_name']} | {order['created_at'][11:16]} | {fmt_price(order['total'])}")
                        if order.get("customer_name"):
                            st.caption(f"Cliente: {order['customer_name']}")
                    with ci2:
                        st.markdown(status_badge(order["status"]), unsafe_allow_html=True)
                    render_print_section(order["id"], key_prefix=f"cola_{order['id']}")
                    # ── "Ya salió" para delivery ──
                    if order.get("order_type") == "para_llevar" and order["status"] != "entregado":
                        if st.button(f"🛍️ Ya salió el delivery — #{order['id']}",
                                     key=f"cola_salida_{order['id']}", use_container_width=True, type="primary"):
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            with get_db() as conn:
                                conn.execute(
                                    "UPDATE orders SET status='entregado', updated_at=? WHERE id=?",
                                    (now_str, order["id"]))
                            st.success(f"✅ Delivery #{order['id']} marcado como entregado.")
                            st.rerun()
    with tab_mesa:
        _render_order_list(fetch_orders(["mesa"]))
    with tab_barra:
        _render_order_list(fetch_orders(["barra", "mostrador"]))
    with tab_delivery:
        _render_order_list(fetch_orders(["para_llevar"]))
# ─── PAGE: KITCHEN VIEW (OWNER) ───────────────────────────────────────────────
def page_kitchen():
    st.markdown("## 👨‍🍳 Vista Cocina")
    # Auto-refresh every 30 seconds
    if _HAS_AUTOREFRESH:
        st_autorefresh(interval=30_000, limit=None, key="kitchen_refresh")
    else:
        st.caption("Actualice la página para ver nuevos pedidos.")
        if st.button("🔄 Actualizar", use_container_width=True, type="primary"):
            st.rerun()
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now()
    with get_db() as conn:
        orders = conn.execute("""
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE o.status IN ('pendiente','preparando','listo')
              AND o.paid = 0
              AND date(o.created_at) = ?
            ORDER BY
                CASE o.status
                    WHEN 'pendiente' THEN 1
                    WHEN 'preparando' THEN 2
                    WHEN 'listo' THEN 3
                END,
                o.created_at ASC
        """, (today,)).fetchall()
    if not orders:
        st.success("No hay pedidos pendientes en cocina.")
        return
    for order in orders:
        order = dict(order)
        created = datetime.strptime(order["created_at"], "%Y-%m-%d %H:%M:%S")
        elapsed = (now - created).total_seconds() / 60
        tc = time_color(elapsed)
        border_color = "#2E7D32" if elapsed < 15 else ("#F9A825" if elapsed < 30 else "#C62828")
        # Get estimated cook time from learned averages
        with get_db() as conn:
            items = conn.execute("""
                SELECT oi.*, mi.name as item_name, mi.avg_cook_minutes
                FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE oi.order_id = ?
            """, (order["id"],)).fetchall()
        # Estimated time = max of individual item averages (slowest item = bottleneck)
        known_times = [it["avg_cook_minutes"] for it in items if it["avg_cook_minutes"]]
        est_total = int(max(known_times)) if known_times else None
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"**Pedido #{order['id']}** — {order['table_num']}")
                st.caption(f"Mozo: {order['mozo_name']}")
                if order["customer_name"]:
                    st.caption(f"Cliente: {order['customer_name']}")
            with c2:
                st.markdown(status_badge(order["status"]), unsafe_allow_html=True)
                if est_total and order["status"] in ("pendiente", "preparando"):
                    remaining = est_total - int(elapsed)
                    if remaining > 0:
                        st.caption(f"⏱ ~{est_total} min total · faltan ~{remaining} min")
                    else:
                        st.caption(f"⏱ Estimado: {est_total} min — ¡debería estar listo!")
            with c3:
                st.markdown(f'<span class="{tc}">{int(elapsed)} min</span>', unsafe_allow_html=True)
            # Items with individual time estimates
            for it in items:
                name = display_item_name(it['item_name'])
                line = f"**{it['quantity']}x** {name}"
                if it["notes"]:
                    line += f" — _{it['notes']}_"
                if it["avg_cook_minutes"]:
                    line += f" &nbsp;`⏱ ~{int(it['avg_cook_minutes'])} min`"
                st.markdown(line, unsafe_allow_html=True)
            if order["notes"]:
                st.warning(f"NOTAS: {order['notes']}")
            # Action buttons
            status = order["status"]
            bc1, bc2, bc3, bc4 = st.columns(4)
            if status == "pendiente":
                with bc1:
                    if st.button("🔥 Preparar", key=f"k_prep_{order['id']}", use_container_width=True):
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE orders SET status='preparando', cooking_started_at=?, updated_at=? WHERE id=?",
                                (now_str, now_str, order["id"]))
                        st.rerun()
            if status == "preparando":
                with bc2:
                    if st.button("✅ ¡Listo! Entregar", key=f"k_ready_{order['id']}", use_container_width=True, type="primary"):
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with get_db() as conn:
                            # Learn cooking time
                            row = conn.execute(
                                "SELECT cooking_started_at FROM orders WHERE id=?", (order["id"],)).fetchone()
                            if row and row["cooking_started_at"]:
                                started = datetime.strptime(row["cooking_started_at"], "%Y-%m-%d %H:%M:%S")
                                cook_min = (datetime.now() - started).total_seconds() / 60
                                if 1 <= cook_min <= 120:  # sanity check
                                    # Collect current estimates for each unique item in the order
                                    item_data = []
                                    for it in items:
                                        mid = it["menu_item_id"]
                                        cur = conn.execute(
                                            "SELECT avg_cook_minutes FROM menu_items WHERE id=?", (mid,)).fetchone()
                                        est = cur["avg_cook_minutes"] if cur else None
                                        item_data.append((mid, est))
                                    # Pro-rate: the measured time belongs to the SLOWEST item.
                                    # Faster items get a proportionally smaller time update.
                                    known_ests = [e for _, e in item_data if e is not None]
                                    max_est = max(known_ests) if known_ests else None
                                    for mid, est in item_data:
                                        if est is not None and max_est and max_est > 0:
                                            # Scale: this item's share of total time = measured * (its_est / max_est)
                                            prorated = cook_min * (est / max_est)
                                            new_avg = round(0.7 * est + 0.3 * prorated, 1)
                                        else:
                                            # No prior estimate → use measured time as seed
                                            new_avg = round(cook_min, 1)
                                        conn.execute(
                                            "UPDATE menu_items SET avg_cook_minutes=? WHERE id=?", (new_avg, mid))
                            # LISTO = ENTREGADO: skip intermediate state, mark directly as delivered
                            conn.execute("UPDATE orders SET status='entregado', updated_at=? WHERE id=?",
                                         (now_str, order["id"]))
                        st.rerun()
            # ── Editar pedido desde cocina ──
            render_edit_panel(order, key_prefix=f"kv_{order['id']}_")
            # Print section with status tracking (owner/cashier only)
            render_print_section(order["id"], key_prefix=f"kv_{order['id']}")
# ─── PAGE: TICKET HISTORY (OWNER) ─────────────────────────────────────────────
def page_ticket_history():
    st.markdown("## 🧾 Historial de Tickets")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        hist_date = st.date_input("Fecha", value=datetime.now().date(), key="hist_date")
    with col_f2:
        hist_type = st.selectbox("Tipo", ["Todos", "mesa", "mostrador", "para_llevar"], key="hist_type")
    with col_f3:
        hist_pay = st.selectbox("Pago", ["Todos", "efectivo", "transferencia", "pendiente"], key="hist_pay")
    date_str = hist_date.strftime("%Y-%m-%d")
    with get_db() as conn:
        query = """
            SELECT o.*, u.display_name as mozo_name
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE date(o.created_at) = ?
        """
        params = [date_str]
        if hist_type != "Todos":
            query += " AND o.order_type = ?"
            params.append(hist_type)
        if hist_pay != "Todos":
            query += " AND o.payment_method = ?"
            params.append(hist_pay)
        query += " ORDER BY o.created_at DESC"
        orders = conn.execute(query, params).fetchall()
    if not orders:
        st.info("No hay tickets para la fecha seleccionada.")
        return
    # Summary row
    valid = [dict(o) for o in orders if o["status"] != "cancelado"]
    total_revenue = sum(o["total"] for o in valid)
    st.markdown(f"**{len(orders)} tickets** encontrados — Total válido: **{fmt_price(total_revenue)}**")
    for order in orders:
        order = dict(order)
        type_labels = {"mesa": "🪑 Mesa", "mostrador": "🧍 Barra", "para_llevar": "🛍️ Para llevar/Delivery"}
        pay_labels = {"efectivo": "💵 Efectivo", "transferencia": "📱 Transferencia", "pendiente": "⏳ Pendiente", "": "—"}
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**#{order['id']}** — {type_labels.get(order['order_type'], order['order_type'])} — {order['table_num']}")
                st.caption(f"Mozo: {order['mozo_name']} | {order['created_at'][:16]}")
                if order["customer_name"]:
                    st.caption(f"Cliente: {order['customer_name']}")
            with c2:
                st.markdown(status_badge(order["status"]), unsafe_allow_html=True)
                st.caption(pay_labels.get(order["payment_method"], "—"))
            with c3:
                st.markdown(f"**{fmt_price(order['total'])}**")
                if order["payment_method"] == "efectivo" and order.get("payment_change", 0) > 0:
                    st.caption(f"Vuelto: {fmt_price(order['payment_change'])}")
            # Expand ticket
            with st.expander("Ver detalle / imprimir"):
                with get_db() as conn:
                    items = conn.execute("""
                        SELECT oi.*, mi.name as item_name
                        FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
                        WHERE oi.order_id = ?
                    """, (order["id"],)).fetchall()
                for it in items:
                    line = f"  {it['quantity']}x {display_item_name(it['item_name'])} — {fmt_price(it['unit_price'] * it['quantity'])}"
                    if it["notes"]:
                        line += f" _({it['notes']})_"
                    st.markdown(line)
                if order["notes"]:
                    st.caption(f"Notas: {order['notes']}")
                st.divider()
                th1, th2 = st.columns(2)
                with th1:
                    render_print_button(order["id"], key_suffix=f"hist_kitchen_{order['id']}", kitchen=True)
                with th2:
                    render_print_button(order["id"], key_suffix=f"hist_receipt_{order['id']}", kitchen=False)
# ─── PAGE: DAILY REPORT (OWNER) ───────────────────────────────────────────────
def page_daily_report():
    st.markdown("## 📄 Reporte Diario")
    report_date = st.date_input("Fecha del reporte", value=datetime.now().date(), key="report_date")
    date_str = report_date.strftime("%Y-%m-%d")
    with get_db() as conn:
        # Summary
        summary = conn.execute("""
            SELECT
                COUNT(*) as total_orders,
                COUNT(CASE WHEN status != 'cancelado' THEN 1 END) as valid_orders,
                COUNT(CASE WHEN status = 'cancelado' THEN 1 END) as cancelled,
                COALESCE(SUM(CASE WHEN status != 'cancelado' THEN total ELSE 0 END), 0) as total_revenue,
                COALESCE(AVG(CASE WHEN status != 'cancelado' THEN total END), 0) as avg_ticket,
                COALESCE(MAX(CASE WHEN status != 'cancelado' THEN total END), 0) as max_ticket,
                COALESCE(MIN(CASE WHEN status != 'cancelado' THEN total END), 0) as min_ticket
            FROM orders WHERE date(created_at) = ?
        """, (date_str,)).fetchone()
        # By mozo
        by_mozo = conn.execute("""
            SELECT u.display_name, COUNT(*) as orders,
                   SUM(CASE WHEN o.status != 'cancelado' THEN o.total ELSE 0 END) as revenue
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE date(o.created_at) = ?
            GROUP BY u.display_name
            ORDER BY revenue DESC
        """, (date_str,)).fetchall()
        # By category
        by_cat = conn.execute("""
            SELECT c.name, SUM(oi.quantity) as qty,
                   SUM(oi.quantity * oi.unit_price) as revenue
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            JOIN categories c ON mi.category_id = c.id
            JOIN orders o ON oi.order_id = o.id
            WHERE date(o.created_at) = ? AND o.status != 'cancelado'
            GROUP BY c.name
            ORDER BY revenue DESC
        """, (date_str,)).fetchall()
        # Top items
        top_items = conn.execute("""
            SELECT mi.name, SUM(oi.quantity) as qty,
                   SUM(oi.quantity * oi.unit_price) as revenue
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            JOIN orders o ON oi.order_id = o.id
            WHERE date(o.created_at) = ? AND o.status != 'cancelado'
            GROUP BY mi.name ORDER BY qty DESC LIMIT 15
        """, (date_str,)).fetchall()
    # Display
    st.markdown(f"### Resumen del {report_date.strftime('%d/%m/%Y')}")
    with st.container(horizontal=True):
        st.metric("Ingresos Totales", fmt_price(summary["total_revenue"]), border=True)
        st.metric("Pedidos Válidos", str(summary["valid_orders"]), border=True)
        st.metric("Cancelados", str(summary["cancelled"]), border=True)
    with st.container(horizontal=True):
        st.metric("Ticket Promedio", fmt_price(summary["avg_ticket"]), border=True)
        st.metric("Ticket Máximo", fmt_price(summary["max_ticket"]), border=True)
        st.metric("Ticket Mínimo", fmt_price(summary["min_ticket"]), border=True)
    if by_mozo:
        import pandas as pd
        st.markdown("### Ventas por Mozo")
        df_mozo = pd.DataFrame([dict(r) for r in by_mozo])
        df_mozo.columns = ["Mozo", "Pedidos", "Ingresos"]
        df_mozo["Ingresos"] = df_mozo["Ingresos"].apply(fmt_price)
        st.dataframe(df_mozo, hide_index=True, use_container_width=True)
    if by_cat:
        import pandas as pd
        st.markdown("### Ventas por Categoría")
        df_cat = pd.DataFrame([dict(r) for r in by_cat])
        df_cat.columns = ["Categoría", "Cantidad", "Ingresos"]
        df_cat["Ingresos"] = df_cat["Ingresos"].apply(fmt_price)
        st.dataframe(df_cat, hide_index=True, use_container_width=True)
    if top_items:
        import pandas as pd
        st.markdown("### Top 15 Platos")
        df_top = pd.DataFrame([dict(r) for r in top_items])
        df_top.columns = ["Plato", "Cantidad", "Ingresos"]
        df_top["Ingresos"] = df_top["Ingresos"].apply(fmt_price)
        st.dataframe(df_top, hide_index=True, use_container_width=True)
    # Generate printable report
    if st.button("📥 Descargar Reporte", use_container_width=True):
        report_lines = []
        report_lines.append("=" * 40)
        report_lines.append("DYLAN - REPORTE DIARIO".center(40))
        report_lines.append("Polleria & Cevicheria".center(40))
        report_lines.append("=" * 40)
        report_lines.append(f"Fecha: {report_date.strftime('%d/%m/%Y')}")
        report_lines.append("-" * 40)
        report_lines.append(f"Ingresos Totales: {fmt_price(summary['total_revenue'])}")
        report_lines.append(f"Pedidos Válidos: {summary['valid_orders']}")
        report_lines.append(f"Pedidos Cancelados: {summary['cancelled']}")
        report_lines.append(f"Ticket Promedio: {fmt_price(summary['avg_ticket'])}")
        report_lines.append("-" * 40)
        if by_mozo:
            report_lines.append("\nVENTAS POR MOZO:")
            for r in by_mozo:
                report_lines.append(f"  {r['display_name']}: {r['orders']} pedidos - {fmt_price(r['revenue'])}")
        if top_items:
            report_lines.append("\nTOP PLATOS:")
            for r in top_items:
                report_lines.append(f"  {r['name']}: {r['qty']}x - {fmt_price(r['revenue'])}")
        report_lines.append("\n" + "=" * 40)
        report_text = "\n".join(report_lines)
        st.download_button(
            "📄 Descargar TXT",
            report_text,
            file_name=f"reporte_dylan_{date_str}.txt",
            mime="text/plain",
        )
# ─── PAGE: MESAS — visual table map + cobrar ──────────────────────────────────
def page_tables_cobrar():
    """Visual table grid: red=occupied, green=free. Click → see items → cobrar."""
    st.markdown("## 🪑 Estado de Mesas")
    num_tables = get_num_tables()
    # ── Load all unpaid orders today ──
    with get_db() as conn:
        raw_orders = conn.execute("""
            SELECT o.id, o.table_num, o.total, o.status, o.order_type,
                   o.payment_method, o.payment_cash, o.payment_transfer,
                   o.payment_amount, o.payment_change, o.notes, o.customer_name,
                   u.display_name as mozo_name, o.created_at
            FROM orders o JOIN users u ON o.mozo_id = u.id
            WHERE o.paid = 0 AND o.status != 'cancelado'
            ORDER BY o.created_at
        """).fetchall()
    # Separate mesa orders vs barra/delivery
    mesa_orders   = {}   # table_name → order dict (latest unpaid)
    other_orders  = []
    for o in raw_orders:
        o = dict(o)
        if o["order_type"] == "mesa":
            mesa_orders[o["table_num"]] = o
        else:
            other_orders.append(o)
    # ── Legend ──
    leg1, leg2 = st.columns(2)
    leg1.markdown(
        '<div style="background:#C62828;color:#fff;border-radius:8px;padding:6px 12px;'
        'text-align:center;font-weight:700;">🔴 Ocupada — click para cobrar</div>',
        unsafe_allow_html=True,
    )
    leg2.markdown(
        '<div style="background:#2E7D32;color:#fff;border-radius:8px;padding:6px 12px;'
        'text-align:center;font-weight:700;">🟢 Libre</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    # ── Table grid ──
    selected = st.session_state.get("cobrar_table")
    COLS = 5
    status_icon = {"pendiente": "⏳", "preparando": "🔥",
                   "listo": "✅", "entregado": "✅"}
    for row_start in range(0, num_tables, COLS):
        row_cols = st.columns(COLS)
        for j in range(COLS):
            tidx = row_start + j
            if tidx >= num_tables:
                break
            tname = f"Mesa {tidx + 1}"
            order = mesa_orders.get(tname)
            with row_cols[j]:
                if order:
                    ico  = status_icon.get(order["status"], "•")
                    tot  = f"${int(order['total']):,}".replace(",", ".")
                    lbl  = f"{ico} Mesa {tidx+1}\n{tot}"
                    is_sel = (selected == tname)
                    btn_t = "primary"
                    # Inject red color for occupied (Streamlit primary is already red ✓)
                    if st.button(lbl, key=f"ctbl_{tidx+1}",
                                 use_container_width=True, type=btn_t):
                        st.session_state.cobrar_table = None if is_sel else tname
                        if not is_sel:
                            st.session_state.cobrar_pay_open = {}
                        st.rerun()
                else:
                    # Free: green decorative HTML (no button needed)
                    st.markdown(
                        f'<div style="background:#2E7D32;color:#fff;border-radius:8px;'
                        f'padding:10px 4px;text-align:center;font-weight:700;'
                        f'font-size:0.95rem;line-height:1.3;">🟢 Mesa {tidx+1}'
                        f'<br><span style="font-size:0.75rem;font-weight:400">Libre</span></div>',
                        unsafe_allow_html=True,
                    )
    # ── Barra / Delivery pending ──
    if other_orders:
        st.divider()
        st.markdown("#### 🧾 Barra / Delivery sin cobrar")
        for o in other_orders:
            tipo_lbl = {"mostrador": "🧍 Barra", "para_llevar": "🛍️ Delivery"}.get(o["order_type"], o["order_type"])
            is_sel = selected == f"__other_{o['id']}"
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(f"**#{o['id']} — {tipo_lbl} {o['table_num']}** | {fmt_price(o['total'])} | {o['mozo_name']}")
            with col_b:
                if st.button("💰 Cobrar", key=f"cobrar_other_{o['id']}", use_container_width=True, type="primary"):
                    st.session_state.cobrar_table = f"__other_{o['id']}"
                    st.session_state.cobrar_pay_open = {}
                    st.rerun()
    # ── Selected table: order detail + cobrar form ──
    if not selected:
        return
    # Resolve order from selection
    if selected.startswith("__other_"):
        oid = int(selected.split("_")[-1])
        order = next((o for o in other_orders if o["id"] == oid), None)
    else:
        order = mesa_orders.get(selected)
    if not order:
        st.session_state.cobrar_table = None
        st.rerun()
    st.divider()
    with st.container(border=True):
        hdr1, hdr2 = st.columns([5, 1])
        with hdr1:
            tipo_display = {"mesa": "🪑 Mesa", "mostrador": "🧍 Barra",
                            "para_llevar": "🛍️ Delivery"}.get(order["order_type"], "")
            status_lbl = {"pendiente": "⏳ Pendiente", "preparando": "🔥 En cocina",
                          "listo": "✅ Listo", "entregado": "✅ Entregado"}.get(order["status"], order["status"])
            st.markdown(f"### {tipo_display} — {order['table_num']}")
            st.caption(f"Pedido #{order['id']} | {status_lbl} | Mozo: {order['mozo_name']} | {order['created_at'][:16]}")
        with hdr2:
            if st.button("✖ Cerrar", key="cobrar_close_panel", use_container_width=True):
                st.session_state.cobrar_table = None
                st.rerun()
        # Items
        with get_db() as conn:
            items = conn.execute("""
                SELECT oi.quantity, oi.unit_price, oi.notes, mi.name as item_name
                FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE oi.order_id = ?
            """, (order["id"],)).fetchall()
        st.markdown("**Ítems del pedido:**")
        for it in items:
            subtotal = it["quantity"] * it["unit_price"]
            line = f"**{it['quantity']}x** {display_item_name(it['item_name'])} — {fmt_price(subtotal)}"
            if it["notes"]:
                line += f" _(** {it['notes']})_"
            st.markdown(line)
        st.markdown(f"---\n**TOTAL: {fmt_price(order['total'])}**")
        if order.get("notes"):
            st.warning(f"NOTA: {order['notes']}")
        # ── Editar pedido ──
        render_edit_panel(order, key_prefix=f"tbl_{order['id']}_")
        # ── Cobrar form ──
        cobrar_key = f"cobrar_tbl_{order['id']}"
        if not st.session_state.get(cobrar_key):
            if st.button("💰 COBRAR ESTA MESA", key=f"cobrar_tbl_open_{order['id']}",
                         use_container_width=True, type="primary"):
                st.session_state[cobrar_key] = True
                st.rerun()
        else:
            with st.container(border=True):
                st.markdown(f"**💰 Cobrar — {fmt_price(order['total'])}**")
                method = st.radio(
                    "Método de pago", ["efectivo", "transferencia", "mixto"],
                    key=f"ctbl_method_{order['id']}", horizontal=True,
                )
                cash_paid = 0.0
                transfer_paid = 0.0
                if method == "efectivo":
                    amount = st.number_input(
                        "Recibido $", min_value=float(order["total"]),
                        value=float(order["total"]), step=1000.0,
                        key=f"ctbl_amt_{order['id']}",
                    )
                    cash_paid = amount
                    change = amount - order["total"]
                    if change > 0:
                        st.info(f"Vuelto: {fmt_price(change)}")
                    else:
                        change = 0.0
                elif method == "transferencia":
                    amount = float(order["total"])
                    change = 0.0
                    transfer_paid = amount
                else:  # mixto
                    cash_paid = st.number_input(
                        "💵 Efectivo $", min_value=0.0, value=float(order["total"]),
                        step=1000.0, key=f"ctbl_cash_{order['id']}",
                    )
                    transfer_paid = st.number_input(
                        "📱 Transferencia $", min_value=0.0,
                        value=max(0.0, float(order["total"]) - cash_paid),
                        step=1000.0, key=f"ctbl_transf_{order['id']}",
                    )
                    amount = cash_paid + transfer_paid
                    change = max(0.0, amount - float(order["total"]))
                    st.info(f"Total ingresado: {fmt_price(amount)} | Vuelto: {fmt_price(change)}")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✅ CONFIRMAR PAGO", key=f"ctbl_confirm_{order['id']}",
                                 use_container_width=True, type="primary"):
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with get_db() as conn:
                            conn.execute("""
                                UPDATE orders SET
                                    paid=1, payment_method=?,
                                    payment_cash=?, payment_transfer=?,
                                    payment_amount=?, payment_change=?,
                                    status='entregado', updated_at=?
                                WHERE id=?
                            """, (method, cash_paid, transfer_paid,
                                  amount, change, now_str, order["id"]))
                        st.session_state[cobrar_key] = False
                        st.session_state.cobrar_table = None
                        st.success(f"✅ Mesa {order['table_num']} cobrada y liberada!")
                        st.rerun()
                with cc2:
                    if st.button("❌ Cancelar", key=f"ctbl_cancel_{order['id']}",
                                 use_container_width=True):
                        st.session_state[cobrar_key] = False
                        st.rerun()
        # Print receipt option
        render_print_section(order["id"], key_prefix=f"tbl_cobrar_{order['id']}")
# ─── PAGE: GESTIÓN MOZOS (OWNER) ──────────────────────────────────────────────
def page_manage_mozos():
    st.markdown("## 👥 Gestión de Personal")
    tab_list, tab_add = st.tabs(["Personal Actual", "Agregar Usuario"])
    with tab_list:
        with get_db() as conn:
            users = conn.execute(
                "SELECT * FROM users WHERE role IN ('mozo','encargado') ORDER BY role, display_name"
            ).fetchall()
        if not users:
            st.info("No hay personal registrado.")
        else:
            role_icons = {"mozo": "🧑 Mozo", "encargado": "🗝️ Encargado"}
            for u in users:
                u = dict(u)
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                    with c1:
                        st.markdown(f"**{u['display_name']}** — {role_icons.get(u['role'], u['role'])}")
                        st.caption(f"Usuario: {u['username']}")
                    with c2:
                        new_name = st.text_input(
                            "Nombre", value=u["display_name"],
                            key=f"mozo_name_{u['id']}",
                            label_visibility="collapsed",
                        )
                    with c3:
                        active = st.checkbox(
                            "Activo",
                            value=bool(u["active"]),
                            key=f"mozo_active_{u['id']}",
                        )
                    with c4:
                        if st.button("💾", key=f"mozo_save_{u['id']}"):
                            with get_db() as conn:
                                conn.execute(
                                    "UPDATE users SET display_name=?, active=? WHERE id=?",
                                    (new_name, 1 if active else 0, u["id"]),
                                )
                            st.success(f"Mozo actualizado!")
                            st.rerun()
                    with c5:
                        if st.button("🗑️", key=f"mozo_del_{u['id']}", help="Eliminar mozo"):
                            st.session_state[f"confirm_del_mozo_{u['id']}"] = True
                    if st.session_state.get(f"confirm_del_mozo_{u['id']}"):
                        with get_db() as conn:
                            order_count = conn.execute(
                                "SELECT COUNT(*) c FROM orders WHERE mozo_id=?", (u["id"],)).fetchone()["c"]
                        if order_count > 0:
                            st.warning(f"⚠️ {u['display_name']} tiene {order_count} pedido(s) histórico(s). Se desactivará en lugar de eliminar.")
                            cd1, cd2 = st.columns(2)
                            with cd1:
                                if st.button("✅ Desactivar", key=f"mozo_deact_{u['id']}", use_container_width=True):
                                    with get_db() as conn:
                                        conn.execute("UPDATE users SET active=0 WHERE id=?", (u["id"],))
                                    del st.session_state[f"confirm_del_mozo_{u['id']}"]
                                    st.rerun()
                            with cd2:
                                if st.button("❌ Cancelar", key=f"mozo_delcancel_{u['id']}", use_container_width=True):
                                    del st.session_state[f"confirm_del_mozo_{u['id']}"]
                                    st.rerun()
                        else:
                            st.warning(f"⚠️ ¿Eliminar a **{u['display_name']}** definitivamente?")
                            cd1, cd2 = st.columns(2)
                            with cd1:
                                if st.button("🗑️ Eliminar", key=f"mozo_delconfirm_{u['id']}", use_container_width=True, type="primary"):
                                    with get_db() as conn:
                                        # Delete sessions first to avoid FK constraint error
                                        conn.execute("DELETE FROM sessions WHERE user_id=?", (u["id"],))
                                        conn.execute("DELETE FROM users WHERE id=?", (u["id"],))
                                    st.rerun()
                            with cd2:
                                if st.button("❌ Cancelar", key=f"mozo_delcancel2_{u['id']}", use_container_width=True):
                                    del st.session_state[f"confirm_del_mozo_{u['id']}"]
                                    st.rerun()
                    # Reset password
                    new_pw = st.text_input(
                        "Nueva contraseña",
                        key=f"mozo_pw_{u['id']}",
                        placeholder="Dejar vacío para no cambiar",
                        type="password",
                    )
                    if new_pw:
                        if st.button(f"🔑 Cambiar contraseña", key=f"mozo_pwbtn_{u['id']}"):
                            with get_db() as conn:
                                conn.execute(
                                    "UPDATE users SET password_hash=?, plain_pw=? WHERE id=?",
                                    (hash_pw(new_pw), new_pw, u["id"]),
                                )
                            st.success(f"Contraseña de {u['display_name']} actualizada!")
                            st.rerun()
    with tab_add:
        with st.form("form_crear_mozo", clear_on_submit=True, border=True):
            st.markdown("### Agregar nuevo usuario")
            new_display = st.text_input("Nombre completo", placeholder="Ej: Juan Pérez")
            new_user = st.text_input("Usuario (para login)", placeholder="Ej: juan")
            new_pass = st.text_input("Contraseña", placeholder="Clave fácil de recordar")
            new_role = st.selectbox("Rol", ["mozo", "encargado"],
                                    format_func=lambda r: "🧑 Mozo" if r == "mozo" else "🗝️ Encargado")
            submitted = st.form_submit_button("👤 Crear Usuario", type="primary", use_container_width=True)
        # Process OUTSIDE the form block so DB commit completes
        if submitted:
            if new_display and new_user and new_pass:
                try:
                    with get_db() as conn:
                        existing = conn.execute("SELECT COUNT(*) c FROM users WHERE username=?", (new_user.strip().lower(),)).fetchone()
                        if existing["c"] > 0:
                            st.error("Ese usuario ya existe.")
                        else:
                            conn.execute(
                                "INSERT INTO users (username, password_hash, plain_pw, role, display_name) VALUES (?,?,?,?,?)",
                                (new_user.strip().lower(), hash_pw(new_pass), new_pass, new_role, new_display),
                            )
                    st.success(f"✅ Mozo '{new_display}' creado! Usuario: **{new_user.strip().lower()}** / Clave: **{new_pass}**")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al crear mozo: {e}")
            else:
                st.error("Completá todos los campos.")
# ─── PAGE: AJUSTES (OWNER) ───────────────────────────────────────────────────
def page_settings():
    st.markdown("## ⚙️ Ajustes del Restaurante")
    with st.container(border=True):
        st.markdown("### 🛍️ Recargo Delivery")
        current_fee = int(get_setting("delivery_fee", "100"))
        new_fee = st.number_input(
            "Recargo automático para pedidos Para Llevar/Delivery ($)",
            min_value=0, step=100, value=current_fee,
            key="settings_delivery_fee",
        )
        if st.button("💾 Guardar Recargo", use_container_width=True, key="save_delivery_fee"):
            set_setting("delivery_fee", str(int(new_fee)))
            st.success(f"Recargo delivery actualizado: {fmt_price(new_fee)}")
            st.rerun()
    with st.container(border=True):
        st.markdown("### 🪑 Cantidad de Mesas")
        current_tables = get_num_tables()
        new_tables = st.number_input(
            "¿Cuántas mesas tiene el restaurante?",
            min_value=1, max_value=50, value=current_tables,
            key="settings_num_tables",
        )
        if st.button("💾 Guardar Mesas", use_container_width=True):
            set_setting("num_tables", new_tables)
            st.success(f"Ahora el sistema tiene {new_tables} mesas.")
            st.rerun()
    with st.container(border=True):
        st.markdown("### ✏️ Cambiar Usuario")
        st.caption(f"Usuario actual: **{st.session_state.user['username']}**")
        new_username = st.text_input("Nuevo usuario", key="settings_new_username", placeholder="Nuevo nombre de usuario")
        if st.button("💾 Cambiar Usuario", use_container_width=True):
            if not new_username:
                st.error("Ingresá un usuario.")
            elif new_username.strip().lower() == "roker":
                st.error("Ese usuario está reservado.")
            else:
                with get_db() as conn:
                    existing = conn.execute("SELECT COUNT(*) c FROM users WHERE username=? AND id!=?",
                                            (new_username.strip().lower(), st.session_state.user["id"])).fetchone()
                    if existing["c"] > 0:
                        st.error("Ese usuario ya existe.")
                    else:
                        conn.execute("UPDATE users SET username=? WHERE id=?",
                                     (new_username.strip().lower(), st.session_state.user["id"]))
                        st.session_state.user["username"] = new_username.strip().lower()
                        st.success(f"Usuario cambiado a: {new_username.strip().lower()}")
                        st.rerun()
    with st.container(border=True):
        st.markdown("### 🔑 Cambiar Contraseña")
        current_pw = st.text_input("Contraseña actual", type="password", key="owner_current_pw")
        new_pw1 = st.text_input("Nueva contraseña", type="password", key="owner_new_pw1")
        new_pw2 = st.text_input("Repetir nueva contraseña", type="password", key="owner_new_pw2")
        if st.button("🔑 Cambiar Contraseña", use_container_width=True):
            if not current_pw or not new_pw1:
                st.error("Completá todos los campos.")
            elif new_pw1 != new_pw2:
                st.error("Las contraseñas no coinciden.")
            else:
                with get_db() as conn:
                    user = conn.execute(
                        "SELECT * FROM users WHERE id=? AND password_hash=?",
                        (st.session_state.user["id"], hash_pw(current_pw)),
                    ).fetchone()
                    if user:
                        conn.execute(
                            "UPDATE users SET password_hash=?, plain_pw=? WHERE id=?",
                            (hash_pw(new_pw1), new_pw1, st.session_state.user["id"]),
                        )
                        st.success("Contraseña actualizada!")
                    else:
                        st.error("Contraseña actual incorrecta.")
    # ── PERMISOS DE ENCARGADOS (solo dueño/admin) ──
    _cur_role = st.session_state.user.get("role")
    if _cur_role in ("admin", "dueno"):
        st.divider()
        with st.container(border=True):
            st.markdown("### 🔐 Permisos de Encargados")
            st.caption("Configurá qué puede ver y hacer cada encargado. Por defecto todo habilitado.")
            with get_db() as conn:
                encargados = conn.execute(
                    "SELECT * FROM users WHERE role='encargado' AND active=1 ORDER BY display_name"
                ).fetchall()
            if not encargados:
                st.info("No hay encargados creados. Podés agregar uno en 👥 Gestionar Mozos.")
            else:
                for enc in encargados:
                    enc = dict(enc)
                    with st.expander(f"🗝️ {enc['display_name']} (@{enc['username']})"):
                        st.caption("Desmarcá los accesos que querés restringir:")
                        perm_cols = st.columns(2)
                        for idx, (perm_key, perm_label) in enumerate(ENCARGADO_PERMS.items()):
                            with get_db() as conn:
                                row = conn.execute(
                                    "SELECT allowed FROM user_permissions WHERE user_id=? AND permission=?",
                                    (enc["id"], perm_key),
                                ).fetchone()
                            cur_val = bool(row["allowed"]) if row else True
                            with perm_cols[idx % 2]:
                                new_val = st.checkbox(
                                    perm_label, value=cur_val,
                                    key=f"perm_{enc['id']}_{perm_key}"
                                )
                            if new_val != cur_val:
                                with get_db() as conn:
                                    conn.execute(
                                        "INSERT OR REPLACE INTO user_permissions (user_id, permission, allowed) VALUES (?,?,?)",
                                        (enc["id"], perm_key, int(new_val)),
                                    )
                                st.rerun()
    # ── VER TODOS LOS USUARIOS Y CONTRASEÑAS (admin ve todos; dueño ve mozos) ──
    _cur_role = st.session_state.user.get("role")
    if _cur_role in ("admin", "dueno"):
        st.divider()
        with st.container(border=True):
            if _cur_role == "admin":
                st.markdown("### 👁️ Ver todos los usuarios y contraseñas")
                st.caption("Visible solo para Roker (admin). Las contraseñas se guardan cuando se crean o cambian desde el sistema.")
                _user_filter = None  # admin ve todos
            else:
                st.markdown("### 👁️ Ver contraseñas de mozos")
                st.caption("El dueño puede ver y cambiar las contraseñas de los mozos.")
                _user_filter = "mozo"  # dueño solo ve mozos
            with get_db() as conn:
                if _user_filter:
                    all_users = conn.execute(
                        "SELECT id, username, display_name, role, plain_pw, active FROM users WHERE role=? ORDER BY display_name",
                        (_user_filter,),
                    ).fetchall()
                else:
                    all_users = conn.execute(
                        "SELECT id, username, display_name, role, plain_pw, active FROM users ORDER BY role, display_name"
                    ).fetchall()
            role_icons = {"admin": "🔑 Admin", "dueno": "👑 Dueño", "mozo": "🧑 Mozo"}
            for u in all_users:
                u = dict(u)
                active_str = "✅ Activo" if u["active"] else "❌ Inactivo"
                pw_display = u["plain_pw"] if u["plain_pw"] else "(no registrada)"
                with st.container(border=True):
                    ua, ub, uc, ud = st.columns([2, 2, 2, 1])
                    with ua:
                        st.markdown(f"**{u['display_name']}**")
                        st.caption(f"{role_icons.get(u['role'], u['role'])} — {active_str}")
                    with ub:
                        st.markdown(f"👤 `{u['username']}`")
                    with uc:
                        st.markdown(f"🔑 `{pw_display}`")
                    with ud:
                        # Admin/dueño can reset passwords from here
                        new_pw_admin = st.text_input(
                            "Nueva clave",
                            key=f"admin_pw_reset_{u['id']}",
                            placeholder="Nueva...",
                            label_visibility="collapsed",
                        )
                        if new_pw_admin:
                            if st.button("💾", key=f"admin_pw_save_{u['id']}", help="Guardar nueva contraseña"):
                                with get_db() as conn:
                                    conn.execute(
                                        "UPDATE users SET password_hash=?, plain_pw=? WHERE id=?",
                                        (hash_pw(new_pw_admin), new_pw_admin, u["id"]),
                                    )
                                st.success(f"✅ Contraseña de {u['display_name']} actualizada: `{new_pw_admin}`")
                                st.rerun()
    # ── ZONA DE PELIGRO: Reset total ──
    st.divider()
    with st.container(border=True):
        st.markdown("### 🗑️ Resetear Sistema")
        st.markdown(
            "Borra **todos los pedidos, historial y registros de caja** del sistema. "
            "El menú, las categorías y los usuarios **NO se borran**."
        )
        st.error(
            "⚠️ Esta acción es IRREVERSIBLE. Una vez ejecutada no se puede deshacer."
        )
        step_key = "_reset_step"
        if st.session_state.get(step_key, 0) == 0:
            if st.button("🗑️ Resetear todo el sistema", use_container_width=True):
                st.session_state[step_key] = 1
                st.rerun()
        elif st.session_state.get(step_key) == 1:
            st.warning("**Paso 1 de 2** — Para confirmar, escribí exactamente: BORRAR TODO")
            confirm_text = st.text_input(
                "Escribí BORRAR TODO para continuar",
                key="_reset_confirm_text",
                placeholder="BORRAR TODO",
            )
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ Continuar", use_container_width=True, type="primary"):
                    if confirm_text.strip() == "BORRAR TODO":
                        st.session_state[step_key] = 2
                        st.rerun()
                    else:
                        st.error("El texto no coincide. Escribí exactamente: BORRAR TODO")
            with cc2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state[step_key] = 0
                    st.rerun()
        elif st.session_state.get(step_key) == 2:
            st.error("**Paso 2 de 2 — ÚLTIMA ADVERTENCIA**")
            st.markdown("Se van a borrar **todos los pedidos e historial**. El menú y usuarios quedan intactos.")
            fc1, fc2 = st.columns(2)
            with fc1:
                if st.button("☢️ SÍ, BORRAR TODO AHORA", use_container_width=True, type="primary"):
                    with get_db() as conn:
                        conn.execute("DELETE FROM order_items")
                        conn.execute("DELETE FROM orders")
                        conn.execute("DELETE FROM cash_registers")
                        # Reset autoincrement counters
                        for tbl in ("orders", "order_items", "cash_registers"):
                            conn.execute(
                                "DELETE FROM sqlite_sequence WHERE name=?", (tbl,)
                            )
                    # Clear all order-related session state
                    for k in list(st.session_state.keys()):
                        if any(x in k for x in ("cart", "order_", "cobrar_", "last_order",
                                                  "confirm_order", "pay_method", "cancelling_",
                                                  "_bell_prev", "_reset_")):
                            st.session_state.pop(k, None)
                    st.session_state["_reset_done"] = True
                    st.rerun()
            with fc2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state[step_key] = 0
                    st.rerun()
        # Show success after reset
        if st.session_state.pop("_reset_done", False):
            st.success("✅ Sistema reseteado. Todos los pedidos y registros fueron borrados.")
# ─── MAIN ROUTER ──────────────────────────────────────────────────────────────
def main():
    if st.session_state.user is None:
        login_page()
        return
    page = st.session_state.page
    role = st.session_state.user["role"]
    is_owner = role in ("admin", "dueno", "encargado")
    # Hide header+nav only for mozos during order taking (owners always see nav)
    mozo_fullscreen = not is_owner and page in {"new_order", "order_confirmed"}
    if not mozo_fullscreen:
        render_header()
        render_nav()
    # Route pages
    if page == "menu":
        page_menu()
    elif page == "new_order":
        page_new_order()
    elif page == "order_confirmed":
        page_order_confirmed()
    elif page == "my_orders":
        page_my_orders()
    elif page == "dashboard" and is_owner:
        page_dashboard()
    elif page == "edit_menu" and is_owner:
        page_edit_menu()
    elif page == "tables_cobrar" and is_owner:
        page_tables_cobrar()
    elif page == "all_orders" and is_owner:
        page_all_orders()
    elif page == "kitchen" and is_owner:
        page_kitchen()
    elif page == "ticket_history" and is_owner:
        page_ticket_history()
    elif page == "daily_report" and is_owner:
        page_daily_report()
    elif page == "manage_mozos" and is_owner:
        page_manage_mozos()
    elif page == "settings" and is_owner:
        page_settings()
    else:
        page_menu()
if __name__ == "__main__":
    main()