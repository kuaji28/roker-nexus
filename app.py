"""
ROKER NEXUS — App Principal v1.4.0
Samsung One UI 8 Design System
"""
import streamlit as st
from datetime import datetime

APP_VERSION = "v1.4.0"
APP_BUILD   = "2026-03-13"

st.set_page_config(
    page_title="Roker Nexus",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
:root {
    --bg:#1C1C1E; --bg2:#161618; --card:#2C2C2E; --card2:#3A3A3C; --card3:#48484A;
    --line:rgba(255,255,255,0.07); --line2:rgba(255,255,255,0.12);
    --text:#F2F2F7; --text2:#8E8E93; --text3:#545458;
    --blue:#0A84FF; --blue-l:#64B5FF; --blue-bg:rgba(10,132,255,0.14); --blue-bg2:rgba(10,132,255,0.08);
    --green:#32D74B; --green-bg:rgba(50,215,75,0.12);
    --amber:#FF9F0A; --amber-bg:rgba(255,159,10,0.12);
    --red:#FF375F; --red-bg:rgba(255,55,95,0.12);
    --purple:#BF5AF2; --purple-bg:rgba(191,90,242,0.12);
    --r-xs:10px; --r-sm:14px; --r-md:18px; --r-lg:22px; --r-xl:28px; --r-pill:100px;
    --shadow:0 4px 24px rgba(0,0,0,0.28); --shadow-sm:0 2px 10px rgba(0,0,0,0.18);
}
*,*::before,*::after{font-family:'Inter',-apple-system,'SF Pro Display',sans-serif!important;-webkit-font-smoothing:antialiased!important;box-sizing:border-box}
html,body,.stApp{background:var(--bg)!important}
.main .block-container{padding:20px 28px!important;max-width:100%!important}
#MainMenu,footer,header,[data-testid="stToolbar"],.stDeployButton{display:none!important}

/* SIDEBAR */
[data-testid="stSidebar"]{background:var(--bg2)!important;border-right:0.5px solid var(--line2)!important;box-shadow:2px 0 20px rgba(0,0,0,0.3)!important}
[data-testid="stSidebar"]>div:first-child{padding:0 0 24px 0!important}

/* BOTON SIDEBAR - SIEMPRE VISIBLE */
[data-testid="collapsedControl"]{background:var(--blue)!important;width:26px!important;min-height:52px!important;border-radius:0 16px 16px 0!important;top:42%!important;left:0!important;position:fixed!important;z-index:9999999!important;box-shadow:3px 0 18px rgba(10,132,255,0.55)!important;border:none!important;opacity:1!important;display:flex!important;align-items:center!important;justify-content:center!important;cursor:pointer!important;transition:width 0.2s ease!important}
[data-testid="collapsedControl"]:hover{width:34px!important;background:var(--blue-l)!important}
[data-testid="collapsedControl"] svg,[data-testid="collapsedControl"] *{fill:white!important;color:white!important;opacity:1!important;visibility:visible!important}
[data-testid="stSidebarCollapseButton"]{display:block!important}
[data-testid="stSidebarCollapseButton"] button{background:var(--card)!important;border-radius:var(--r-sm)!important;border:0.5px solid var(--line2)!important;color:var(--text2)!important;margin:12px 16px!important}

/* TIPOGRAFIA */
h1{font-size:28px!important;font-weight:700!important;letter-spacing:-0.5px!important;color:var(--text)!important}
h2{font-size:20px!important;font-weight:600!important;color:var(--text)!important}
h3{font-size:16px!important;font-weight:600!important;color:var(--text)!important}
p,li{color:var(--text2)!important;font-size:14px!important}
label{color:var(--text2)!important;font-size:12px!important;font-weight:500!important}

/* METRICAS */
[data-testid="metric-container"]{background:var(--card)!important;border:0.5px solid var(--line2)!important;border-radius:var(--r-lg)!important;padding:20px 22px!important;box-shadow:var(--shadow-sm)!important;transition:transform 0.15s,box-shadow 0.15s!important}
[data-testid="metric-container"]:hover{transform:translateY(-2px)!important;box-shadow:var(--shadow)!important}
[data-testid="metric-container"] label{color:var(--text2)!important;font-size:11px!important;font-weight:500!important;text-transform:uppercase!important;letter-spacing:0.6px!important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:var(--text)!important;font-size:28px!important;font-weight:700!important;letter-spacing:-0.8px!important}

/* BOTONES */
.stButton>button{background:var(--blue-bg)!important;color:var(--blue-l)!important;border:1px solid rgba(10,132,255,0.22)!important;border-radius:var(--r-pill)!important;font-weight:600!important;font-size:13px!important;padding:9px 22px!important;transition:all 0.18s!important}
.stButton>button:hover{background:var(--blue)!important;color:#fff!important;border-color:var(--blue)!important;transform:scale(1.02)!important;box-shadow:0 4px 18px rgba(10,132,255,0.35)!important}
.stButton>button[kind="primary"]{background:var(--blue)!important;color:#fff!important;border-color:var(--blue)!important;box-shadow:0 2px 12px rgba(10,132,255,0.3)!important}

/* TABS */
.stTabs [data-baseweb="tab-list"]{background:var(--card)!important;border-radius:var(--r-xl)!important;padding:5px!important;gap:3px!important;border:none!important;box-shadow:var(--shadow-sm)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:var(--r-lg)!important;color:var(--text2)!important;font-size:13px!important;font-weight:500!important;padding:8px 18px!important;transition:all 0.18s!important;border:none!important}
.stTabs [aria-selected="true"]{background:var(--blue)!important;color:#fff!important;box-shadow:0 2px 10px rgba(10,132,255,0.3)!important;font-weight:600!important}

/* INPUTS */
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stTextArea textarea{background:var(--card)!important;border:0.5px solid var(--line2)!important;border-radius:var(--r-md)!important;color:var(--text)!important;font-size:14px!important;padding:11px 15px!important;transition:border-color 0.15s,box-shadow 0.15s!important}
.stTextInput>div>div>input:focus,.stNumberInput>div>div>input:focus,.stTextArea textarea:focus{border-color:var(--blue)!important;box-shadow:0 0 0 3px rgba(10,132,255,0.18)!important;outline:none!important}
.stSelectbox>div>div,.stMultiSelect>div>div{background:var(--card)!important;border:0.5px solid var(--line2)!important;border-radius:var(--r-md)!important;color:var(--text)!important}

/* UPLOAD */
[data-testid="stFileUploader"]{background:var(--card)!important;border:1.5px dashed var(--line2)!important;border-radius:var(--r-xl)!important;transition:all 0.2s!important;padding:12px!important}
[data-testid="stFileUploader"]:hover{border-color:var(--blue)!important;background:var(--blue-bg2)!important}

/* DATAFRAME */
[data-testid="stDataFrame"]{border:0.5px solid var(--line2)!important;border-radius:var(--r-lg)!important;overflow:hidden!important;box-shadow:var(--shadow-sm)!important}

/* EXPANDER */
[data-testid="stExpander"]{background:var(--card)!important;border:0.5px solid var(--line)!important;border-radius:var(--r-lg)!important;overflow:hidden!important}

/* ALERTS */
.stSuccess{background:var(--green-bg)!important;border:0.5px solid rgba(50,215,75,0.3)!important;border-radius:var(--r-md)!important;color:var(--green)!important}
.stWarning{background:var(--amber-bg)!important;border:0.5px solid rgba(255,159,10,0.3)!important;border-radius:var(--r-md)!important}
.stError{background:var(--red-bg)!important;border:0.5px solid rgba(255,55,95,0.3)!important;border-radius:var(--r-md)!important}
.stInfo{background:var(--blue-bg2)!important;border:0.5px solid rgba(10,132,255,0.3)!important;border-radius:var(--r-md)!important}

/* CHAT */
[data-testid="stChatMessage"]{background:var(--card)!important;border-radius:var(--r-xl)!important;border:0.5px solid var(--line)!important;margin-bottom:10px!important;padding:14px 18px!important}

/* MISC */
.stSpinner>div{border-top-color:var(--blue)!important}
hr{border-color:var(--line)!important;margin:24px 0!important}
::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--card2);border-radius:10px}

/* CARDS CUSTOM */
.nx-card{background:var(--card);border:0.5px solid var(--line2);border-radius:var(--r-lg);padding:18px 22px;margin-bottom:12px;box-shadow:var(--shadow-sm);transition:transform 0.15s,box-shadow 0.15s}
.nx-card:hover{transform:translateY(-1px);box-shadow:var(--shadow)}
.nx-card-blue{border-left:3px solid var(--blue)!important}
.nx-card-green{border-left:3px solid var(--green)!important}
.nx-card-amber{border-left:3px solid var(--amber)!important}
.nx-card-red{border-left:3px solid var(--red)!important}
.nx-card-purple{border-left:3px solid var(--purple)!important}
.nx-badge{display:inline-block;padding:3px 11px;border-radius:var(--r-pill);font-size:11px;font-weight:600;letter-spacing:0.2px}
.nx-badge-blue{background:var(--blue-bg);color:var(--blue-l)}
.nx-badge-green{background:var(--green-bg);color:var(--green)}
.nx-badge-amber{background:var(--amber-bg);color:var(--amber)}
.nx-badge-red{background:var(--red-bg);color:var(--red)}
.nx-badge-purple{background:var(--purple-bg);color:var(--purple)}
.nx-version{display:inline-block;background:var(--blue-bg);color:var(--blue-l);border:0.5px solid rgba(10,132,255,0.25);border-radius:var(--r-pill);font-size:10px;font-weight:700;padding:2px 9px;letter-spacing:0.3px}
</style>
""", unsafe_allow_html=True)


# ── Botón hamburguesa — sidebar toggle garantizado ───────────
st.markdown("""
<div id="nx-menu-btn" onclick="toggleSidebar()" title="Menú"
  style="position:fixed;top:50%;left:0;transform:translateY(-50%);
         width:36px;height:72px;background:#0A84FF;
         border-radius:0 20px 20px 0;z-index:9999999;
         display:flex;flex-direction:column;align-items:center;
         justify-content:center;gap:5px;cursor:pointer;
         box-shadow:4px 0 20px rgba(10,132,255,0.6);
         transition:width .2s ease;">
  <div style="width:14px;height:2px;background:#fff;border-radius:2px"></div>
  <div style="width:14px;height:2px;background:#fff;border-radius:2px"></div>
  <div style="width:14px;height:2px;background:#fff;border-radius:2px"></div>
</div>
<script>
function toggleSidebar() {
  // Método 1: botón nativo de Streamlit
  var btn = window.parent.document.querySelector('[data-testid="collapsedControl"]');
  if (btn) { btn.click(); return; }
  // Método 2: botón colapsar dentro del sidebar
  var btn2 = window.parent.document.querySelector('[data-testid="stSidebarCollapseButton"] button');
  if (btn2) { btn2.click(); return; }
  // Método 3: cualquier botón con ícono de sidebar
  var btns = window.parent.document.querySelectorAll('button');
  for (var b of btns) {
    if (b.getAttribute('aria-label') && b.getAttribute('aria-label').toLowerCase().includes('sidebar')) {
      b.click(); return;
    }
  }
}
// Auto-reposicionar si el sidebar se abre
setInterval(function() {
  var sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
  var menuBtn = document.getElementById('nx-menu-btn');
  if (!menuBtn) return;
  if (sidebar && sidebar.offsetWidth > 50) {
    menuBtn.style.left = sidebar.offsetWidth + 'px';
    menuBtn.style.background = '#FF375F';
  } else {
    menuBtn.style.left = '0';
    menuBtn.style.background = '#0A84FF';
  }
}, 300);
</script>
""", unsafe_allow_html=True)

# ── Imports internos ──────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_resumen_stats
from utils.horarios import label_horario, ahora
from utils.helpers import check_apis, fmt_usd, fmt_ars, fmt_num
import pages.importar   as pg_importar
import pages.compras    as pg_compras
import pages.inventario as pg_inventario
import pages.precios    as pg_precios
import pages.dashboard  as pg_dashboard
import pages.asistente  as pg_asistente

init_db()

if "pagina" not in st.session_state:
    st.session_state.pagina = "Dashboard"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:20px 16px 16px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <div style="width:40px;height:40px;border-radius:13px;background:linear-gradient(135deg,#0A84FF 0%,#5AC8FA 100%);display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 14px rgba(10,132,255,0.4)">⚡</div>
        <div>
          <div style="font-size:16px;font-weight:700;color:#F2F2F7;letter-spacing:-0.3px">ROKER NEXUS</div>
          <div style="font-size:10px;color:#545458;letter-spacing:0.5px">EL CELU · COMERCIAL</div>
        </div>
      </div>
      <span class="nx-version">{APP_VERSION}</span>
      <span style="font-size:10px;color:#48484A;margin-left:6px">{APP_BUILD}</span>
    </div>
    <div style="height:0.5px;background:rgba(255,255,255,0.07);margin:0 16px 14px"></div>
    """, unsafe_allow_html=True)

    horario = label_horario()
    st.markdown(f"""
    <div style="margin:0 12px 16px;background:#2C2C2E;border-radius:14px;padding:10px 14px;border:0.5px solid rgba(255,255,255,0.12)">
      <div style="font-size:12px;color:#8E8E93">{horario}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="padding:0 16px;font-size:10px;font-weight:600;color:#545458;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px">NAVEGACIÓN</div>', unsafe_allow_html=True)

    paginas = {
        "📊 Dashboard":          "Dashboard",
        "📥 Cargar Archivos":    "Importar",
        "🛒 Gestión de Compras": "Compras",
        "📦 Inventario":         "Inventario",
        "💰 Precios & ML":       "Precios",
        "🤖 Asistente IA":       "Asistente",
    }

    for label, key in paginas.items():
        activo = st.session_state.pagina == key
        if st.button(label, key=f"nav_{key}", width="stretch",
                     type="primary" if activo else "secondary"):
            st.session_state.pagina = key
            st.rerun()

    st.markdown("""
    <div style="height:0.5px;background:rgba(255,255,255,0.07);margin:16px 16px 14px"></div>
    <div style="padding:0 16px;font-size:10px;font-weight:600;color:#545458;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:8px">SISTEMA</div>
    """, unsafe_allow_html=True)

    apis = check_apis()
    for nombre, ok in [("Claude AI", apis["claude"]), ("Supabase", apis["supabase"]), ("Telegram", apis["telegram"])]:
        color  = "#32D74B" if ok else "#FF375F"
        bg     = "rgba(50,215,75,0.1)" if ok else "rgba(255,55,95,0.1)"
        estado = "Activo" if ok else "Offline"
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 16px">
          <span style="font-size:12px;color:#8E8E93">{nombre}</span>
          <span style="font-size:10px;font-weight:600;color:{color};background:{bg};padding:2px 9px;border-radius:20px">{estado}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="height:0.5px;background:rgba(255,255,255,0.07);margin:14px 16px 10px"></div>
    <div style="padding:0 16px 8px;font-size:10px;color:#48484A;text-align:center">
      {ahora().strftime('%d/%m/%Y %H:%M')} · Buenos Aires
    </div>""", unsafe_allow_html=True)

# ── Ruteo ─────────────────────────────────────────────────────
p = st.session_state.pagina
if   p == "Dashboard":  pg_dashboard.render()
elif p == "Importar":   pg_importar.render()
elif p == "Compras":    pg_compras.render()
elif p == "Inventario": pg_inventario.render()
elif p == "Precios":    pg_precios.render()
elif p == "Asistente":  pg_asistente.render()
