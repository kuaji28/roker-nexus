"""
ROKER NEXUS — App Principal
Sistema de gestión comercial para El Celu
"""
import streamlit as st
import pandas as pd
from datetime import datetime

# ── Configuración de página (debe ir primero) ─────────────────
st.set_page_config(
    page_title="Roker Nexus",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Global — dark/light mode adaptativo ───────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Samsung+Sans:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

/* ── One UI 8 — Variables ── */
:root {
    --bg:        #1C1C1E;
    --surface:   #2C2C2E;
    --surface2:  #3A3A3C;
    --surface3:  #48484A;
    --border:    rgba(255,255,255,0.06);
    --border2:   rgba(255,255,255,0.10);
    --text:      #F5F5F7;
    --text2:     #98989E;
    --text3:     #636366;
    --blue:      #4EADFF;
    --blue2:     #0A84FF;
    --blue-soft: rgba(78,173,255,0.12);
    --green:     #34C759;
    --green-soft:rgba(52,199,89,0.12);
    --amber:     #FF9F0A;
    --amber-soft:rgba(255,159,10,0.12);
    --red:       #FF453A;
    --red-soft:  rgba(255,69,58,0.12);
    --purple:    #BF5AF2;
    --r-sm:  14px;
    --r-md:  18px;
    --r-lg:  22px;
    --r-xl:  28px;
}

/* ── Botón abrir/cerrar sidebar — MUY VISIBLE ── */
[data-testid="collapsedControl"] {
    background: var(--blue2) !important;
    border-radius: 0 12px 12px 0 !important;
    width: 24px !important;
    top: 50% !important;
    box-shadow: 2px 0 12px rgba(10,132,255,0.4) !important;
}
[data-testid="collapsedControl"]:hover {
    background: var(--blue) !important;
    width: 28px !important;
}
[data-testid="collapsedControl"] svg {
    fill: white !important;
}

/* ── Botón colapsar dentro del sidebar ── */
[data-testid="stSidebarCollapseButton"] button {
    background: var(--surface2) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
}

/* ── Base ── */
html, body, [class*="css"], * {
    font-family: 'Inter', -apple-system, 'SF Pro Display', sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}

/* ── Fondo ── */
.stApp, .main {
    background: var(--bg) !important;
}

/* ── Sidebar — One UI drawer style ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 0.5px solid var(--border2) !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.3) !important;
}
[data-testid="stSidebar"] > div {
    padding: 0 !important;
}

/* ── Ocultar chrome de Streamlit ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
[data-testid="stToolbar"] { display: none; }

/* ── Títulos ── */
h1, h2, h3 {
    color: var(--text) !important;
    font-weight: 600 !important;
    letter-spacing: -0.3px !important;
}

/* ── Métricas — One UI card style ── */
[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 0.5px solid var(--border2) !important;
    border-radius: var(--r-lg) !important;
    padding: 18px 20px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2) !important;
    transition: transform 0.15s ease !important;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
}
[data-testid="metric-container"] label {
    color: var(--text2) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.2px !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
}

/* ── Botones — One UI pill style ── */
.stButton > button {
    background: var(--blue-soft) !important;
    color: var(--blue) !important;
    border: 1px solid rgba(78,173,255,0.25) !important;
    border-radius: var(--r-xl) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 9px 20px !important;
    transition: all 0.18s ease !important;
    letter-spacing: 0.1px !important;
}
.stButton > button:hover {
    background: var(--blue2) !important;
    color: #fff !important;
    border-color: var(--blue2) !important;
    transform: scale(1.02) !important;
    box-shadow: 0 4px 16px rgba(10,132,255,0.3) !important;
}
.stButton > button[kind="primary"] {
    background: var(--blue2) !important;
    color: #fff !important;
    border-color: var(--blue2) !important;
}

/* ── Tabs — One UI segmented control ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface2) !important;
    border-radius: var(--r-xl) !important;
    padding: 4px !important;
    gap: 2px !important;
    border: none !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 20px !important;
    color: var(--text2) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 7px 16px !important;
    transition: all 0.18s !important;
}
.stTabs [aria-selected="true"] {
    background: var(--surface) !important;
    color: var(--text) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
    font-weight: 600 !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea textarea {
    background: var(--surface2) !important;
    border: 0.5px solid var(--border2) !important;
    border-radius: var(--r-md) !important;
    color: var(--text) !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    transition: border-color 0.15s !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(78,173,255,0.15) !important;
}
.stSelectbox > div > div {
    background: var(--surface2) !important;
    border: 0.5px solid var(--border2) !important;
    border-radius: var(--r-md) !important;
    color: var(--text) !important;
}

/* ── Upload ── */
[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 1.5px dashed var(--border2) !important;
    border-radius: var(--r-lg) !important;
    transition: all 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--blue) !important;
    background: var(--blue-soft) !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border: 0.5px solid var(--border2) !important;
    border-radius: var(--r-lg) !important;
    overflow: hidden !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 0.5px solid var(--border) !important;
    border-radius: var(--r-lg) !important;
}

/* ── Alerts — suaves ── */
.stSuccess {
    background: var(--green-soft) !important;
    border: 0.5px solid rgba(52,199,89,0.3) !important;
    border-radius: var(--r-md) !important;
    color: var(--green) !important;
}
.stWarning {
    background: var(--amber-soft) !important;
    border: 0.5px solid rgba(255,159,10,0.3) !important;
    border-radius: var(--r-md) !important;
}
.stError {
    background: var(--red-soft) !important;
    border: 0.5px solid rgba(255,69,58,0.3) !important;
    border-radius: var(--r-md) !important;
}
.stInfo {
    background: var(--blue-soft) !important;
    border: 0.5px solid rgba(78,173,255,0.3) !important;
    border-radius: var(--r-md) !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 20px 0 !important; }

/* ── Scrollbar minimalista ── */
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surface3); border-radius: 10px; }

/* ── Cards custom ── */
.nx-card {
    background: var(--surface);
    border: 0.5px solid var(--border2);
    border-radius: var(--r-lg);
    padding: 16px 20px;
    margin-bottom: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.15);
}
.nx-stat-red   { border-left: 3px solid var(--red)   !important; }
.nx-stat-amber { border-left: 3px solid var(--amber) !important; }
.nx-stat-green { border-left: 3px solid var(--green) !important; }
.nx-stat-blue  { border-left: 3px solid var(--blue)  !important; }

/* ── Badges ── */
.nx-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2px;
}
.nx-badge-red    { background: var(--red-soft);   color: var(--red);    }
.nx-badge-amber  { background: var(--amber-soft); color: var(--amber);  }
.nx-badge-green  { background: var(--green-soft); color: var(--green);  }
.nx-badge-blue   { background: var(--blue-soft);  color: var(--blue);   }
.nx-badge-purple { background: rgba(191,90,242,.12); color: var(--purple); }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: var(--surface) !important;
    border-radius: var(--r-lg) !important;
    border: 0.5px solid var(--border) !important;
    margin-bottom: 8px !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--blue) !important; }
</style>
""", unsafe_allow_html=True)

# ── Imports internos ──────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_resumen_stats
from utils.horarios import label_horario, ahora
from utils.helpers import check_apis, fmt_usd, fmt_ars, fmt_num
import pages.importar as pg_importar
import pages.compras as pg_compras
import pages.inventario as pg_inventario
import pages.precios as pg_precios
import pages.dashboard as pg_dashboard
import pages.asistente as pg_asistente

# ── Inicializar DB ────────────────────────────────────────────
init_db()

# ── Session state ─────────────────────────────────────────────
if "pagina" not in st.session_state:
    st.session_state.pagina = "Dashboard"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown("""
    <div style="padding: 8px 0 20px; border-bottom: 1px solid var(--nx-border); margin-bottom: 20px;">
        <div style="font-size: 22px; font-weight: 700; color: var(--nx-accent); letter-spacing: -0.5px;">
            ⚡ ROKER NEXUS
        </div>
        <div style="font-size: 11px; color: var(--nx-text2); margin-top: 2px; letter-spacing: .5px;">
            EL CELU · SISTEMA COMERCIAL
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Estado del negocio
    horario = label_horario()
    st.markdown(f"""
    <div style="background: var(--nx-surface2); border-radius: 8px; padding: 8px 12px;
                margin-bottom: 16px; font-size: 12px; color: var(--nx-text2);">
        {horario}
    </div>
    """, unsafe_allow_html=True)

    # Navegación
    st.markdown('<div style="font-size:10px;font-weight:600;color:var(--nx-text3);letter-spacing:.8px;text-transform:uppercase;margin-bottom:8px">NAVEGACIÓN</div>', unsafe_allow_html=True)

    paginas = {
        "📊 Dashboard":         "Dashboard",
        "📥 Cargar Archivos":   "Importar",
        "🛒 Gestión de Compras":"Compras",
        "📦 Inventario":        "Inventario",
        "💰 Precios & ML":      "Precios",
        "🤖 Asistente IA":      "Asistente",
    }

    for label, key in paginas.items():
        activo = st.session_state.pagina == key
        if st.button(
            label,
            key=f"nav_{key}",
            width="stretch",
            type="primary" if activo else "secondary",
        ):
            st.session_state.pagina = key
            st.rerun()

    # Estado APIs
    st.markdown('<div style="font-size:10px;font-weight:600;color:var(--nx-text3);letter-spacing:.8px;text-transform:uppercase;margin:20px 0 8px">ESTADO DEL SISTEMA</div>', unsafe_allow_html=True)

    apis = check_apis()
    for nombre, activo in [
        ("Claude API", apis["claude"]),
        ("Supabase",   apis["supabase"]),
        ("Telegram",   apis["telegram"]),
        ("Gemini",     apis.get("gemini", False)),
    ]:
        dot = "🟢" if activo else "🔴"
        st.markdown(f'<div style="font-size:11px;color:var(--nx-text2);padding:3px 0">{dot} {nombre}</div>', unsafe_allow_html=True)

    # Última actualización
    st.markdown(f"""
    <div style="position:absolute;bottom:16px;left:16px;right:16px;
                font-size:10px;color:var(--nx-text3);text-align:center;">
        {ahora().strftime('%d/%m/%Y %H:%M')}
    </div>
    """, unsafe_allow_html=True)

# ── Ruteo de páginas ──────────────────────────────────────────
pagina = st.session_state.pagina

if pagina == "Dashboard":
    pg_dashboard.render()
elif pagina == "Importar":
    pg_importar.render()
elif pagina == "Compras":
    pg_compras.render()
elif pagina == "Inventario":
    pg_inventario.render()
elif pagina == "Precios":
    pg_precios.render()
elif pagina == "Asistente":
    pg_asistente.render()
