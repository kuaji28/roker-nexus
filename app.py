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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif !important;
}

/* ── Variables de color ── */
:root {
    --nx-bg: #0a0e1a;
    --nx-surface: #111827;
    --nx-surface2: #1c2333;
    --nx-border: rgba(255,255,255,0.08);
    --nx-border2: rgba(255,255,255,0.14);
    --nx-text: #e8edf5;
    --nx-text2: #8b95a8;
    --nx-text3: #4f5a6b;
    --nx-accent: #00d2ff;
    --nx-accent2: #0099cc;
    --nx-green: #00e676;
    --nx-green2: #00b248;
    --nx-amber: #ffab40;
    --nx-red: #ff5252;
    --nx-purple: #b388ff;
    --nx-radius: 10px;
    --nx-radius-lg: 14px;
}

/* Light mode override */
@media (prefers-color-scheme: light) {
    :root {
        --nx-bg: #f0f4ff;
        --nx-surface: #ffffff;
        --nx-surface2: #e8eef8;
        --nx-border: rgba(0,0,0,0.08);
        --nx-border2: rgba(0,0,0,0.14);
        --nx-text: #0d1117;
        --nx-text2: #5a6478;
        --nx-text3: #9aa3b0;
        --nx-accent: #0077cc;
        --nx-accent2: #005599;
        --nx-green: #00875a;
        --nx-green2: #006644;
        --nx-amber: #c07800;
        --nx-red: #cc0000;
        --nx-purple: #6f42c1;
    }
}

/* ── Fondo principal ── */
.stApp {
    background: var(--nx-bg) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--nx-surface) !important;
    border-right: 1px solid var(--nx-border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--nx-text) !important;
}

/* ── Ocultar elementos de Streamlit ── */
#MainMenu, footer, header {visibility: hidden;}
.stDeployButton {display: none;}

/* ── Títulos ── */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: var(--nx-text) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* ── Métricas ── */
[data-testid="metric-container"] {
    background: var(--nx-surface) !important;
    border: 1px solid var(--nx-border) !important;
    border-radius: var(--nx-radius) !important;
    padding: 16px !important;
}
[data-testid="metric-container"] label {
    color: var(--nx-text2) !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: .6px !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--nx-text) !important;
    font-size: 28px !important;
    font-weight: 700 !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--nx-border) !important;
    border-radius: var(--nx-radius) !important;
    overflow: hidden !important;
}

/* ── Botones ── */
.stButton > button {
    background: var(--nx-accent) !important;
    color: #000 !important;
    border: none !important;
    border-radius: var(--nx-radius) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 8px 18px !important;
    transition: all .2s !important;
}
.stButton > button:hover {
    background: var(--nx-accent2) !important;
    transform: translateY(-1px) !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background: var(--nx-surface2) !important;
    border: 1px solid var(--nx-border2) !important;
    border-radius: var(--nx-radius) !important;
    color: var(--nx-text) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--nx-surface) !important;
    border-radius: var(--nx-radius) !important;
    padding: 4px !important;
    gap: 2px !important;
    border: 1px solid var(--nx-border) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 8px !important;
    color: var(--nx-text2) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    background: var(--nx-accent) !important;
    color: #000 !important;
}

/* ── Upload zone ── */
[data-testid="stFileUploader"] {
    background: var(--nx-surface) !important;
    border: 2px dashed var(--nx-border2) !important;
    border-radius: var(--nx-radius-lg) !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--nx-accent) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--nx-surface) !important;
    border: 1px solid var(--nx-border) !important;
    border-radius: var(--nx-radius) !important;
}

/* ── Alert boxes ── */
.stSuccess { background: rgba(0,230,118,.08) !important; border-color: var(--nx-green) !important; }
.stWarning { background: rgba(255,171,64,.08) !important; border-color: var(--nx-amber) !important; }
.stError   { background: rgba(255,82,82,.08)  !important; border-color: var(--nx-red)   !important; }
.stInfo    { background: rgba(0,210,255,.08)  !important; border-color: var(--nx-accent) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--nx-bg); }
::-webkit-scrollbar-thumb { background: var(--nx-border2); border-radius: 10px; }

/* ── Cards custom ── */
.nx-card {
    background: var(--nx-surface);
    border: 1px solid var(--nx-border);
    border-radius: var(--nx-radius-lg);
    padding: 16px 20px;
    margin-bottom: 12px;
}
.nx-stat-red   { border-left: 3px solid var(--nx-red)    !important; }
.nx-stat-amber { border-left: 3px solid var(--nx-amber)  !important; }
.nx-stat-green { border-left: 3px solid var(--nx-green)  !important; }
.nx-stat-blue  { border-left: 3px solid var(--nx-accent) !important; }

/* ── Badge ── */
.nx-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}
.nx-badge-red    { background: rgba(255,82,82,.15);    color: var(--nx-red); }
.nx-badge-amber  { background: rgba(255,171,64,.15);   color: var(--nx-amber); }
.nx-badge-green  { background: rgba(0,230,118,.15);    color: var(--nx-green); }
.nx-badge-blue   { background: rgba(0,210,255,.15);    color: var(--nx-accent); }
.nx-badge-purple { background: rgba(179,136,255,.15);  color: var(--nx-purple); }
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
            use_container_width=True,
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
