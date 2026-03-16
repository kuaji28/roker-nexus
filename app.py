"""
ROKER NEXUS v2.2.0 — El Celu
Navegación lateral agrupada por función
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

APP_VERSION = "v2.2.0"
APP_BUILD   = "2026-03-15-a"

st.set_page_config(
    page_title="Roker Nexus",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* FIX Streamlit 1.55: elimina arrow en expanders */
[data-testid="stExpander"] details>summary>div:first-child{display:none!important}
[data-testid="stExpander"] details>summary p{display:none!important}
[data-testid="stExpander"] details>summary [data-testid]{display:none!important}
[data-testid="stExpander"] summary{list-style:none}
[data-testid="stExpander"] summary::-webkit-details-marker{display:none}
[data-testid="stExpander"] summary::before{
    content:"▶ ";font-size:9px;opacity:.55;margin-right:4px
}
[data-testid="stExpander"] details[open] summary::before{content:"▼ "}

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
#MainMenu,footer,header,[data-testid="stToolbar"],.stDeployButton{display:none!important}

/* ── Sidebar — SIEMPRE VISIBLE ── */
[data-testid="stSidebar"],
section[data-testid="stSidebar"],
section[data-testid="stSidebar"][aria-expanded="false"],
section[data-testid="stSidebar"][aria-expanded="true"] {
    transform: none !important;
    margin-left: 0 !important;
    min-width: 220px !important;
    max-width: 280px !important;
    width: 240px !important;
    background:#1c1c1e!important;
    border-right:.5px solid rgba(255,255,255,.12)!important;
    display:flex!important;
    flex-direction:column!important;
    visibility:visible!important;
    opacity:1!important;
    position:relative!important;
    z-index:10!important;
    overflow-y:auto!important;
}
/* Botón de colapso — hacerlo grande y visible */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[data-testid="baseButton-header"],
section[data-testid="stSidebar"] + div > button {
    display:flex!important;
    visibility:visible!important;
    opacity:1!important;
    pointer-events:auto!important;
    background:#2c2c2e!important;
    border-right:.5px solid rgba(255,255,255,.08)!important;
    z-index:999!important;
    width:32px!important;
    height:32px!important;
    min-width:32px!important;
}
[data-testid="stSidebar"] .stExpander{
    border:1px solid rgba(255,255,255,.07)!important;
    border-radius:10px!important;margin-bottom:6px!important;
}
[data-testid="stSidebar"] .stNumberInput input{
    background:#2c2c2e!important;
    border:1px solid rgba(255,255,255,.12)!important;
    border-radius:8px!important;
}
[data-testid="stSidebar"] label{color:#8e8e93!important;font-size:11px!important}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{font-size:13px!important}

/* ── Nav group labels in sidebar ── */
.nx-nav-group-label {
    font-size:9px !important;
    font-weight:700 !important;
    color:#545458 !important;
    letter-spacing:.1em !important;
    text-transform:uppercase !important;
    margin:14px 0 4px 4px !important;
    display:block !important;
}
/* Nav buttons in sidebar - active state */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background:var(--blue-bg) !important;
    color:var(--blue-l) !important;
    border:1px solid rgba(10,132,255,.25) !important;
    border-radius:var(--r-md) !important;
    font-weight:600 !important;
    font-size:13px !important;
    text-align:left !important;
    justify-content:flex-start !important;
    padding:8px 14px !important;
    margin-bottom:2px !important;
}
/* Nav buttons in sidebar - inactive state */
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background:transparent !important;
    color:var(--text2) !important;
    border:1px solid transparent !important;
    border-radius:var(--r-md) !important;
    font-weight:500 !important;
    font-size:13px !important;
    text-align:left !important;
    justify-content:flex-start !important;
    padding:8px 14px !important;
    margin-bottom:2px !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background:var(--card) !important;
    color:var(--text) !important;
    border-color:var(--line2) !important;
}

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

header[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; overflow: visible !important; }
header[data-testid="stHeader"] > * { display: none !important; }
.main .block-container { padding-top: 0.5rem !important; padding-bottom: 1rem !important; }
</style>
""", unsafe_allow_html=True)

from database import init_db, get_resumen_stats
from utils.horarios import label_horario, ahora
from utils.helpers import check_apis, fmt_usd, fmt_ars, fmt_num

# ══════════════════════════════════════════════════════════════════
# CRÍTICO: Inicializar DB ANTES de importar cualquier página
# ══════════════════════════════════════════════════════════════════
try:
    init_db()
except Exception as _init_err:
    pass  # Tablas ya existen o Supabase activo

# ── Banner: advertencia de base de datos ──────────────────────
from database import USE_POSTGRES
if not USE_POSTGRES:
    st.markdown("""
    <div style="
        background:linear-gradient(135deg,#7c2020,#4a1010);
        border:1.5px solid #ff375f;border-radius:14px;
        padding:14px 20px;margin:8px 0 12px 0;
        display:flex;align-items:flex-start;gap:14px;
    ">
      <div style="font-size:22px;line-height:1.2">🔴</div>
      <div>
        <div style="font-weight:700;font-size:14px;color:#ff8fa3;margin-bottom:4px">
          DATOS EN MODO LOCAL — SE PIERDEN AL REINICIAR
        </div>
        <div style="font-size:12px;color:#ffb3bf;line-height:1.5">
          El sistema está usando SQLite (archivo temporal). Cuando la app se reinicia o actualiza,
          <b>todos los datos importados desaparecen</b>. Para que los datos persistan:
          <ol style="margin:6px 0 0 16px;padding:0">
            <li>Andá a <b>🔌 Sistema → Backup / Restore</b></li>
            <li>Descargá el backup de los datos actuales</li>
            <li>Configurá <b>DATABASE_URL</b> en Streamlit Cloud → Settings → Secrets</li>
            <li>Una vez conectado a Supabase, restaurá desde el backup</li>
          </ol>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# BOT TELEGRAM — Singleton 24/7
# Arranca UNA sola vez por proceso de Streamlit.
# El flag _BOT_STARTED es a nivel módulo: si Streamlit hace rerun
# del script, la variable de módulo ya está seteada → no arranca dos veces.
# ══════════════════════════════════════════════════════════════════
_BOT_STARTED = False

def _start_telegram_bot():
    """Lanza el bot de Telegram en un thread daemon. Solo corre una vez por proceso."""
    global _BOT_STARTED
    if _BOT_STARTED:
        return
    try:
        from config import TELEGRAM_TOKEN as _TK
        if not _TK:
            return  # Sin token configurado, no arranca
    except Exception:
        import os
        if not os.getenv("TELEGRAM_TOKEN", ""):
            return

    try:
        import threading
        import asyncio

        def _run_bot():
            try:
                # Crear nuevo event loop para el thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                from telegram_bot import main as _bot_main
                _bot_main()
            except Exception as _bot_err:
                print(f"⚠️ Bot Telegram detenido: {_bot_err}")

        t = threading.Thread(target=_run_bot, name="TelegramBot", daemon=True)
        t.start()
        _BOT_STARTED = True
        print("🤖 Bot Telegram arrancado en background")
    except Exception as e:
        print(f"⚠️ No se pudo iniciar el bot: {e}")

_start_telegram_bot()

# ── Importar páginas ───────────────────────────────────────────
import pages.importar      as pg_importar
import pages.compras       as pg_compras
import pages.borrador      as pg_borrador
import pages.cotizaciones  as pg_cotizaciones
import pages.mercadolibre  as pg_mercadolibre
import pages.inventario    as pg_inventario
import pages.precios       as pg_precios
import pages.dashboard     as pg_dashboard
import pages.asistente     as pg_asistente
import pages.sistema       as pg_sistema

try:
    import pages.lista_negra as pg_lista_negra
    _HAS_LISTA_NEGRA = True
except ImportError:
    _HAS_LISTA_NEGRA = False

try:
    import pages.alertas_stock   as pg_alertas
    import pages.auditoria_stock as pg_auditoria
    _HAS_ALERTAS = True
except ImportError:
    _HAS_ALERTAS = False
    pg_auditoria = None

try:
    import pages.calidad_datos as pg_calidad
    _HAS_CALIDAD = True
except ImportError:
    _HAS_CALIDAD = False
    pg_calidad = None

try:
    import pages.defensa_presupuesto as pg_defensa
    _HAS_DEFENSA = True
except ImportError:
    _HAS_DEFENSA = False
    pg_defensa = None

# ── Session state ──────────────────────────────────────────────
if "pagina" not in st.session_state:
    st.session_state.pagina = "Dashboard"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Calcular badges ANTES de renderizar sidebar ────────────────
_alerta_badge = ""
_n_alertas = 0
if _HAS_ALERTAS:
    try:
        from modules.stock_alertas import count_alertas_sin_ver
        _n_alertas = count_alertas_sin_ver()
        if _n_alertas > 0:
            _alerta_badge = f" ({_n_alertas})"
    except Exception:
        pass

_calidad_badge = ""
_n_calidad = 0
if _HAS_CALIDAD:
    try:
        from database import execute_query as _eq
        _rows = _eq("SELECT COUNT(*) as c FROM anomalias WHERE estado='abierta'", fetch=True)
        _n_calidad = _rows[0]["c"] if _rows else 0
        if _n_calidad > 0:
            _calidad_badge = f" ({_n_calidad})"
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# SIDEBAR: Navegación + Configuración
# ══════════════════════════════════════════════════════════════
def _render_sidebar():
    from database import get_all_config, set_config
    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:.8rem;
                    padding-bottom:.8rem;border-bottom:.5px solid rgba(255,255,255,.08)">
          <div style="width:34px;height:34px;border-radius:10px;
                      background:linear-gradient(135deg,#0A84FF,#5AC8FA);
                      display:flex;align-items:center;justify-content:center;font-size:17px">⚡</div>
          <div>
            <div style="font-weight:700;font-size:.9rem;color:#F2F2F7">ROKER NEXUS</div>
            <div style="font-size:.6rem;color:#545458;letter-spacing:.08em">{APP_VERSION} · El Celu</div>
          </div>
        </div>""", unsafe_allow_html=True)

        p_actual = st.session_state.pagina

        # ── Grupos de navegación ───────────────────────────────
        grupos_nav = [
            ("📈 OPERACIONES", [
                ("📊", "Dashboard",               "Dashboard"),
                ("🔔", f"Alertas{_alerta_badge}", "Alertas"),
                ("🛍️", "Compras",                 "Compras"),
                ("✈️", "Pedidos & Tránsito",       "Cotizaciones"),
            ]),
            ("🔍 ANÁLISIS", [
                ("🔍", "Auditoría",                    "Auditoria"),
                ("🧹", f"Calidad{_calidad_badge}",     "Calidad"),
                ("🛡️", "Defensa de Presupuesto",       "Defensa"),
            ]),
            ("💲 PRECIOS & ML", [
                ("💰", "Precios",     "Precios"),
                ("🛒", "Precios ML",  "MercadoLibre"),
            ]),
            ("📦 INVENTARIO", [
                ("📦", "Inventario",  "Inventario"),
                ("📝", "Borrador",    "Borrador"),
                ("🚫", "Lista Negra", "Lista Negra"),
            ]),
            ("⚙️ SISTEMA", [
                ("📥", "Importar",        "Importar"),
                ("🤖", "Inteligencia IA", "Asistente"),
                ("🔌", "Sistema",         "Sistema"),
            ]),
        ]

        for grp_label, items in grupos_nav:
            st.markdown(
                f'<span class="nx-nav-group-label">{grp_label}</span>',
                unsafe_allow_html=True,
            )
            for emoji, nombre, key in items:
                is_active = (p_actual == key)
                if st.button(
                    f"{emoji}  {nombre}",
                    key=f"nav_{key}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.pagina = key
                    st.rerun()

        st.markdown("---")

        # ── Configuración ─────────────────────────────────────
        cfg = get_all_config()
        def v(k, t=float, d=0):
            try: return t(cfg.get(k, {}).get("valor", d) or d)
            except:
                try: return t(d)
                except: return d

        with st.expander("🚚 Logística", expanded=False):
            lt = st.number_input("Lead Time (días)", 1, 365, int(v("lead_time_dias", float, 30)), key="sb_lt")
            if st.button("💾 Guardar", key="sb_lt_s"):
                set_config("lead_time_dias", lt); st.success("✓")

        with st.expander("💰 Presupuestos (USD)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                p1 = st.number_input("Lote 1", 0, value=int(v("presupuesto_lote_1", float, 15000)), step=500, key="sb_p1")
                p3 = st.number_input("Lote 3", 0, value=int(v("presupuesto_lote_3", float, 8000)),  step=500, key="sb_p3")
            with c2:
                p2 = st.number_input("Lote 2", 0, value=int(v("presupuesto_lote_2", float, 10000)), step=500, key="sb_p2")
            if st.button("💾 Guardar", key="sb_p_s"):
                for k, val in [("presupuesto_lote_1", p1), ("presupuesto_lote_2", p2), ("presupuesto_lote_3", p3)]:
                    set_config(k, val)
                st.success("✓")

        with st.expander("💱 Tasas de cambio", expanded=True):
            ars = st.number_input("USD → ARS", 100.0, 99999.0, v("tasa_usd_ars", float, 1420.0), step=10.0, format="%.0f", key="sb_ars")
            rmb = st.number_input("RMB → USD", .01, 99.0, v("tasa_rmb_usd", float, 7.3), step=.01, format="%.4f", key="sb_rmb")
            if st.button("💾 Guardar", key="sb_fx_s"):
                set_config("tasa_usd_ars", ars)
                set_config("tasa_rmb_usd", rmb)
                st.success("✓")

        with st.expander("🛒 Comisiones ML", expanded=False):
            cf  = st.number_input("AI-TECH (%)",              0.0, 50.0, v("comision_ml_fr", float, 14.0),        .5, "%.1f", key="sb_cf")
            cm_ = st.number_input("Mecánico (%)",             0.0, 50.0, v("comision_ml_mecanico", float, 13.0),  .5, "%.1f", key="sb_cm")
            mf  = st.number_input("Margen extra AI-TECH (%)", 0.0, 50.0, v("margen_extra_ml_fr", float, 0.0),   1.0, "%.1f", key="sb_mf")
            mm  = st.number_input("Margen extra MEC (%)",     0.0, 50.0, v("margen_extra_ml_mec", float, 0.0),  1.0, "%.1f", key="sb_mm")
            if st.button("💾 Guardar", key="sb_ml_s"):
                for k, val in [("comision_ml_fr", cf), ("comision_ml_mecanico", cm_),
                                ("margen_extra_ml_fr", mf), ("margen_extra_ml_mec", mm)]:
                    set_config(k, val)
                st.success("✓")

        with st.expander("📊 Coeficientes Stock", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1: cmin = st.number_input("Mín", .1, 5., v("coef_stock_min", float, 1.0), .1, "%.1f", key="sb_cmin")
            with c2: copt = st.number_input("Opt", .1, 5., v("coef_stock_opt", float, 1.2), .1, "%.1f", key="sb_copt")
            with c3: cmax = st.number_input("Máx", .1, 5., v("coef_stock_max", float, 1.4), .1, "%.1f", key="sb_cmax")
            if st.button("💾 Guardar", key="sb_coef_s"):
                for k, val in [("coef_stock_min", cmin), ("coef_stock_opt", copt), ("coef_stock_max", cmax)]:
                    set_config(k, val)
                st.success("✓")

        with st.expander("🧠 Inteligencia IA", expanded=False):
            cfg2 = get_all_config()
            prov_act = str(cfg2.get("ia_proveedor", {}).get("valor", "claude") or "claude")
            opciones = ["claude", "gemini", "gpt"]
            labels   = ["🤖 Claude Pro", "✨ Gemini Pro", "💬 ChatGPT"]
            idx = opciones.index(prov_act) if prov_act in opciones else 0
            sel = st.radio("Proveedor IA", opciones,
                           format_func=lambda x: labels[opciones.index(x)],
                           index=idx, horizontal=True, key="sb_prov")
            if sel != prov_act:
                set_config("ia_proveedor", sel); st.rerun()
            for prov, lbl, ph in [
                ("claude", "Claude API Key", "sk-ant-api03-..."),
                ("gemini", "Gemini API Key", "AIzaSy..."),
                ("gpt",    "OpenAI API Key", "sk-..."),
            ]:
                kk  = f"{prov}_api_key"
                val = str(cfg2.get(kk, {}).get("valor", "") or "")
                ico = "✅" if val else "⬜"
                nueva = st.text_input(f"{ico} {lbl}", value=val, type="password",
                                      placeholder=ph, key=f"sb_k_{prov}")
                if st.button(f"💾 Guardar", key=f"sb_ks_{prov}"):
                    set_config(kk, nueva.strip())
                    try:
                        from modules.ia_engine import motor_ia
                        if prov == "claude":  motor_ia._claude_client = None
                        if prov == "gemini":  motor_ia._gemini_model  = None
                    except Exception:
                        pass
                    st.success("✅ Guardado — recargando...")
                    st.rerun()

        st.markdown("---")
        try:
            from utils.horarios import ahora
            st.caption(f"🕐 {ahora().strftime('%d/%m %H:%M')}")
        except Exception:
            from datetime import datetime
            st.caption(f"🕐 {datetime.now().strftime('%d/%m %H:%M')}")


# ── Renderizar sidebar ─────────────────────────────────────────
try:
    _render_sidebar()
except Exception as _sb_err:
    with st.sidebar:
        st.error(f"⚠️ Error en sidebar: {_sb_err}")
        st.caption("Recargá la página para reintentar.")

# ── Contenido principal ────────────────────────────────────────
st.markdown('<div class="nx-content">', unsafe_allow_html=True)

p = st.session_state.pagina

if   p == "Dashboard":    pg_dashboard.render()
elif p == "Importar":     pg_importar.render()
elif p == "Compras":      pg_compras.render()
elif p == "Borrador":     pg_borrador.render()
elif p == "Cotizaciones": pg_cotizaciones.render()
elif p == "Inventario":   pg_inventario.render()
elif p == "Precios":      pg_precios.render()
elif p == "MercadoLibre": pg_mercadolibre.render()
elif p == "Asistente":    pg_asistente.render()
elif p == "Sistema":      pg_sistema.render()
elif p == "Lista Negra"  and _HAS_LISTA_NEGRA:              pg_lista_negra.render()
elif p == "Alertas"      and _HAS_ALERTAS:                  pg_alertas.render()
elif p == "Auditoria"    and pg_auditoria is not None:      pg_auditoria.render()
elif p == "Calidad"      and _HAS_CALIDAD:                  pg_calidad.render()
elif p == "Defensa"      and _HAS_DEFENSA:                  pg_defensa.render()
elif p == "Defensa"      and not _HAS_DEFENSA:
    st.info("📦 Módulo Defensa de Presupuesto no disponible.")

st.markdown('</div>', unsafe_allow_html=True)
