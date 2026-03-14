"""
ROKER NEXUS v1.6.1 — El Celu
Navegación horizontal — sin depender del sidebar
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

APP_VERSION = "v1.6.1"
APP_BUILD   = "2026-03-13"

st.set_page_config(
    page_title="Roker Nexus",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
:root {
    --bg:#1C1C1E;--bg2:#161618;--card:#2C2C2E;--card2:#3A3A3C;--card3:#48484A;
    --line:rgba(255,255,255,0.07);--line2:rgba(255,255,255,0.12);
    --text:#F2F2F7;--text2:#8E8E93;--text3:#545458;
    --blue:#0A84FF;--blue-l:#64B5FF;--blue-bg:rgba(10,132,255,0.14);--blue-bg2:rgba(10,132,255,0.08);
    --green:#32D74B;--green-bg:rgba(50,215,75,0.12);
    --amber:#FF9F0A;--amber-bg:rgba(255,159,10,0.12);
    --red:#FF375F;--red-bg:rgba(255,55,95,0.12);
    --purple:#BF5AF2;--purple-bg:rgba(191,90,242,0.12);
    --r-xs:10px;--r-sm:14px;--r-md:18px;--r-lg:22px;--r-xl:28px;--r-pill:100px;
    --shadow:0 4px 24px rgba(0,0,0,0.28);--shadow-sm:0 2px 10px rgba(0,0,0,0.18);
}
*,*::before,*::after{font-family:'Inter',-apple-system,sans-serif!important;-webkit-font-smoothing:antialiased!important}
html,body,.stApp{background:var(--bg)!important}
.main .block-container{padding:0 0 28px 0!important;max-width:100%!important}
#MainMenu,footer,header,[data-testid="stToolbar"],.stDeployButton,
[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important}

/* ── TOPBAR ── */
.nx-topbar{
    position:sticky;top:0;z-index:9999;
    background:rgba(22,22,24,0.92);
    backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
    border-bottom:.5px solid var(--line2);
    padding:0 20px;
    display:flex;align-items:center;gap:0;
    height:56px;
}
.nx-logo{
    display:flex;align-items:center;gap:10px;
    padding-right:20px;border-right:.5px solid var(--line2);
    margin-right:16px;min-width:fit-content;
}
.nx-logo-icon{
    width:34px;height:34px;border-radius:11px;
    background:linear-gradient(135deg,#0A84FF 0%,#5AC8FA 100%);
    display:flex;align-items:center;justify-content:center;
    font-size:17px;box-shadow:0 3px 12px rgba(10,132,255,.4);
}
.nx-logo-text{font-size:14px;font-weight:700;color:#F2F2F7;letter-spacing:-.2px;white-space:nowrap}
.nx-logo-sub{font-size:9px;color:#545458;letter-spacing:.4px;white-space:nowrap}
.nx-version-tag{
    font-size:9px;font-weight:700;color:var(--blue-l);
    background:var(--blue-bg);border:.5px solid rgba(10,132,255,.25);
    border-radius:var(--r-pill);padding:2px 8px;margin-left:6px;white-space:nowrap;
}
.nx-nav{display:flex;align-items:center;gap:4px;flex:1;overflow-x:auto;scrollbar-width:none}
.nx-nav::-webkit-scrollbar{display:none}
.nx-nav-item{
    padding:7px 14px;border-radius:var(--r-md);
    font-size:12px;font-weight:500;color:var(--text2);
    white-space:nowrap;cursor:pointer;border:none;background:transparent;
    transition:all .15s;flex-shrink:0;
}
.nx-nav-item:hover{background:var(--card);color:var(--text)}
.nx-nav-item.active{
    background:var(--blue-bg);color:var(--blue-l);font-weight:600;
    border:.5px solid rgba(10,132,255,.2);
}
.nx-status{
    display:flex;align-items:center;gap:8px;
    padding-left:16px;border-left:.5px solid var(--line2);
    margin-left:auto;flex-shrink:0;
}
.nx-dot{width:6px;height:6px;border-radius:50%}
.nx-dot-green{background:#32D74B;box-shadow:0 0 6px rgba(50,215,75,.6)}
.nx-dot-red{background:#FF375F;box-shadow:0 0 6px rgba(255,55,95,.6)}

/* ── CONTENIDO ── */
.nx-content{padding:24px 28px}

/* ── MÉTRICAS ── */
[data-testid="metric-container"]{
    background:var(--card)!important;border:.5px solid var(--line2)!important;
    border-radius:var(--r-lg)!important;padding:20px 22px!important;
    box-shadow:var(--shadow-sm)!important;transition:transform .15s,box-shadow .15s!important;
}
[data-testid="metric-container"]:hover{transform:translateY(-2px)!important;box-shadow:var(--shadow)!important}
[data-testid="metric-container"] label{color:var(--text2)!important;font-size:11px!important;font-weight:500!important;text-transform:uppercase!important;letter-spacing:.6px!important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:var(--text)!important;font-size:28px!important;font-weight:700!important;letter-spacing:-.8px!important}

/* ── BOTONES ── */
.stButton>button{background:var(--blue-bg)!important;color:var(--blue-l)!important;border:1px solid rgba(10,132,255,.22)!important;border-radius:var(--r-pill)!important;font-weight:600!important;font-size:13px!important;padding:9px 22px!important;transition:all .18s!important}
.stButton>button:hover{background:var(--blue)!important;color:#fff!important;border-color:var(--blue)!important;transform:scale(1.02)!important;box-shadow:0 4px 18px rgba(10,132,255,.35)!important}
.stButton>button[kind="primary"]{background:var(--blue)!important;color:#fff!important;border-color:var(--blue)!important;box-shadow:0 2px 12px rgba(10,132,255,.3)!important}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{background:var(--card)!important;border-radius:var(--r-xl)!important;padding:5px!important;gap:3px!important;border:none!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:var(--r-lg)!important;color:var(--text2)!important;font-size:13px!important;font-weight:500!important;padding:8px 18px!important;border:none!important}
.stTabs [aria-selected="true"]{background:var(--blue)!important;color:#fff!important;font-weight:600!important}

/* ── INPUTS ── */
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stTextArea textarea{background:var(--card)!important;border:.5px solid var(--line2)!important;border-radius:var(--r-md)!important;color:var(--text)!important;font-size:14px!important;padding:11px 15px!important}
.stTextInput>div>div>input:focus,.stNumberInput>div>div>input:focus,.stTextArea textarea:focus{border-color:var(--blue)!important;box-shadow:0 0 0 3px rgba(10,132,255,.18)!important}
.stSelectbox>div>div,.stMultiSelect>div>div{background:var(--card)!important;border:.5px solid var(--line2)!important;border-radius:var(--r-md)!important}
label{color:var(--text2)!important;font-size:12px!important;font-weight:500!important}
h1{font-size:24px!important;font-weight:700!important;color:var(--text)!important}
h2{font-size:18px!important;font-weight:600!important;color:var(--text)!important}
h3{font-size:15px!important;font-weight:600!important;color:var(--text)!important}

/* ── FILE UPLOAD ── */
[data-testid="stFileUploader"]{background:var(--card)!important;border:1.5px dashed var(--line2)!important;border-radius:var(--r-xl)!important;padding:12px!important}
[data-testid="stFileUploader"]:hover{border-color:var(--blue)!important;background:var(--blue-bg2)!important}

/* ── DATAFRAME ── */
[data-testid="stDataFrame"]{border:.5px solid var(--line2)!important;border-radius:var(--r-lg)!important;overflow:hidden!important}

/* ── EXPANDER ── */
[data-testid="stExpander"]{background:var(--card)!important;border:.5px solid var(--line)!important;border-radius:var(--r-lg)!important;overflow:hidden!important}

/* ── ALERTS ── */
.stSuccess{background:var(--green-bg)!important;border:.5px solid rgba(50,215,75,.3)!important;border-radius:var(--r-md)!important}
.stWarning{background:var(--amber-bg)!important;border:.5px solid rgba(255,159,10,.3)!important;border-radius:var(--r-md)!important}
.stError{background:var(--red-bg)!important;border:.5px solid rgba(255,55,95,.3)!important;border-radius:var(--r-md)!important}
.stInfo{background:var(--blue-bg2)!important;border:.5px solid rgba(10,132,255,.3)!important;border-radius:var(--r-md)!important}

/* ── CHAT ── */
[data-testid="stChatMessage"]{background:var(--card)!important;border-radius:var(--r-xl)!important;border:.5px solid var(--line)!important;margin-bottom:10px!important}

/* ── MISC ── */
.stSpinner>div{border-top-color:var(--blue)!important}
hr{border-color:var(--line)!important;margin:24px 0!important}
::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-thumb{background:var(--card2);border-radius:10px}

/* ── CARDS / BADGES ── */
.nx-card{background:var(--card);border:.5px solid var(--line2);border-radius:var(--r-lg);padding:18px 22px;margin-bottom:12px;box-shadow:var(--shadow-sm);transition:transform .15s,box-shadow .15s}
.nx-card:hover{transform:translateY(-1px);box-shadow:var(--shadow)}
.nx-card-blue{border-left:3px solid var(--blue)!important}
.nx-card-green{border-left:3px solid var(--green)!important}
.nx-card-amber{border-left:3px solid var(--amber)!important}
.nx-card-red{border-left:3px solid var(--red)!important}
.nx-badge{display:inline-block;padding:3px 11px;border-radius:var(--r-pill);font-size:11px;font-weight:600}
.nx-badge-blue{background:var(--blue-bg);color:var(--blue-l)}
.nx-badge-green{background:var(--green-bg);color:var(--green)}
.nx-badge-amber{background:var(--amber-bg);color:var(--amber)}
.nx-badge-red{background:var(--red-bg);color:var(--red)}
</style>
""", unsafe_allow_html=True)

from database import init_db, get_resumen_stats
from utils.horarios import label_horario, ahora
from utils.helpers import check_apis, fmt_usd, fmt_ars, fmt_num
import pages.importar   as pg_importar
import pages.compras    as pg_compras
import pages.inventario as pg_inventario
import pages.precios    as pg_precios
import pages.dashboard  as pg_dashboard
import pages.asistente  as pg_asistente
import pages.sistema    as pg_sistema

init_db()

if "pagina" not in st.session_state:
    st.session_state.pagina = "Dashboard"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Estado APIs (rápido, para el topbar) ─────────────────────
apis = check_apis()
sistema_ok = apis.get("supabase", False) and apis.get("claude", False)

# ── Top Navigation Bar ────────────────────────────────────────
paginas = [
    ("📊", "Dashboard",  "Dashboard"),
    ("📥", "Cargar",     "Importar"),
    ("🛒", "Compras",    "Compras"),
    ("📦", "Inventario", "Inventario"),
    ("💰", "Precios",    "Precios"),
    ("🤖", "IA",         "Asistente"),
    ("🔌", "Sistema",    "Sistema"),
]

p_actual = st.session_state.pagina

# Construir nav HTML
nav_items = ""
for icono, nombre, key in paginas:
    cls = "nx-nav-item active" if p_actual == key else "nx-nav-item"
    nav_items += f'<span class="{cls}" data-page="{key}">{icono} {nombre}</span>'

dot_color  = "nx-dot-green" if sistema_ok else "nx-dot-red"
dot_estado = "Sistema OK" if sistema_ok else "Sin conexión"

# ── Botones de navegación reales (invisibles, accionados por HTML) ──
cols = st.columns(len(paginas))
for i, (icono, nombre, key) in enumerate(paginas):
    with cols[i]:
        if st.button(f"{icono} {nombre}", key=f"nav_{key}",
                     type="primary" if p_actual == key else "secondary"):
            st.session_state.pagina = key
            st.rerun()

st.markdown('<div class="nx-content">', unsafe_allow_html=True)

# ── Ruteo ─────────────────────────────────────────────────────
p = st.session_state.pagina
if   p == "Dashboard":  pg_dashboard.render()
elif p == "Importar":   pg_importar.render()
elif p == "Compras":    pg_compras.render()
elif p == "Inventario": pg_inventario.render()
elif p == "Precios":    pg_precios.render()
elif p == "Asistente":  pg_asistente.render()
elif p == "Sistema":    pg_sistema.render()

st.markdown('</div>', unsafe_allow_html=True)
