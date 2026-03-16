"""
ROKER NEXUS — Widget de IA Contextual
======================================
Panel de IA embebido que puede insertarse en cualquier página del sistema.
Cada página pasa su propio contexto de datos y preguntas sugeridas.

Uso:
    from utils.ia_widget import nx_ai_widget

    nx_ai_widget(
        page_key    = "inventario",
        titulo      = "🤖 Analizar con IA",
        sugeridas   = [
            ("🔴 ¿Qué reponer ahora?", "¿Qué artículos necesito reponer con más urgencia?"),
            ("⚠️ ¿Hay anomalías?",     "¿Ves algo raro en el inventario actual?"),
        ],
        context_fn  = lambda: {"stockouts": 42, "articulos_criticos": [...]},
        collapsed   = True,    # empieza cerrado
        mode        = "claude" # claude | gemini | auto
    )
"""
from __future__ import annotations
import streamlit as st
from typing import Callable, Optional


# ── Estilos CSS para el widget (inyectados una sola vez por sesión) ──────────
_CSS_KEY = "_nx_ia_widget_css_injected"

_WIDGET_CSS = """
<style>
.nx-ia-badge {
    display:inline-flex;align-items:center;gap:6px;
    background:linear-gradient(135deg,rgba(10,132,255,.18),rgba(10,132,255,.08));
    border:1px solid rgba(10,132,255,.35);border-radius:20px;
    padding:5px 12px;font-size:12px;font-weight:600;color:#0a84ff;
    cursor:pointer;transition:all .2s;
}
.nx-ia-badge:hover { background:rgba(10,132,255,.25); }
.nx-ia-quick-btn {
    background:rgba(10,132,255,.08);border:1px solid rgba(10,132,255,.2);
    border-radius:8px;padding:6px 10px;font-size:12px;color:var(--nx-text2,#aeaeb2);
    cursor:pointer;width:100%;text-align:left;margin-bottom:4px;
    transition:background .15s;
}
.nx-ia-quick-btn:hover { background:rgba(10,132,255,.18);color:#fff; }
</style>
"""


def _inject_css():
    if not st.session_state.get(_CSS_KEY):
        st.markdown(_WIDGET_CSS, unsafe_allow_html=True)
        st.session_state[_CSS_KEY] = True


# ── Función principal ─────────────────────────────────────────────────────────

def nx_ai_widget(
    page_key: str,
    titulo: str = "🤖 Analizar con IA",
    subtitulo: str = "Consultá sobre los datos de esta página",
    sugeridas: Optional[list[tuple[str, str]]] = None,
    context_fn: Optional[Callable[[], dict]] = None,
    collapsed: bool = True,
    mode: str = "auto",
):
    """
    Renderiza el widget de IA contextual.

    Parameters
    ----------
    page_key   : Identificador único de la página (para keys de session_state)
    titulo     : Título del expander
    subtitulo  : Subtítulo descriptivo
    sugeridas  : Lista de tuplas (label_botón, pregunta_real)
    context_fn : Función que retorna dict con contexto de datos (se llama lazy)
    collapsed  : Si el expander arranca cerrado
    mode       : 'claude' | 'gemini' | 'auto'
    """
    _inject_css()

    sugeridas = sugeridas or []
    hist_key  = f"_nx_ia_hist_{page_key}"
    inp_key   = f"_nx_ia_inp_{page_key}"

    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    # ── Comprobar disponibilidad ─────────────────────────────────────
    try:
        from modules.ia_engine import motor_ia
        ia_ok = motor_ia.claude_disponible or motor_ia.gemini_disponible
    except Exception:
        ia_ok = False

    # ── Determinar modo efectivo ─────────────────────────────────────
    def _modo_efectivo() -> str:
        if mode != "auto":
            return mode
        try:
            from modules.ia_engine import motor_ia
            if motor_ia.claude_disponible:
                return "claude"
            if motor_ia.gemini_disponible:
                return "gemini"
        except Exception:
            pass
        return "claude"

    # ── Widget expander ──────────────────────────────────────────────
    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)

    with st.expander(titulo, expanded=not collapsed):
        st.markdown(
            f"<p style='font-size:12px;color:var(--nx-text2);margin-bottom:12px'>{subtitulo}</p>",
            unsafe_allow_html=True
        )

        if not ia_ok:
            st.warning("⚠️ IA no configurada — agregá una API key en **⚙️ Sistema → Inteligencia IA**")
            return

        # ── Preguntas rápidas ────────────────────────────────────────
        if sugeridas:
            st.markdown(
                "<div style='font-size:11px;font-weight:600;color:var(--nx-text3);"
                "text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px'>"
                "Consultas rápidas</div>",
                unsafe_allow_html=True
            )
            # Dividir en dos columnas
            mid = (len(sugeridas) + 1) // 2
            col_q1, col_q2 = st.columns(2)
            for i, (label, pregunta) in enumerate(sugeridas):
                col = col_q1 if i < mid else col_q2
                with col:
                    if st.button(label, key=f"nx_ia_q_{page_key}_{i}", use_container_width=True):
                        _enviar_pregunta(hist_key, pregunta, context_fn, _modo_efectivo())

        # ── Historial de chat ────────────────────────────────────────
        hist = st.session_state.get(hist_key, [])
        if hist:
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            for msg in hist[-8:]:  # máximo últimos 8 mensajes para no sobrecargar
                role = msg.get("role", "user")
                with st.chat_message(role):
                    st.markdown(msg.get("content", ""), unsafe_allow_html=False)

        # ── Input libre ──────────────────────────────────────────────
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        with st.form(key=f"nx_ia_form_{page_key}", clear_on_submit=True):
            col_in, col_btn = st.columns([6, 1])
            with col_in:
                user_input = st.text_input(
                    "Preguntá algo",
                    placeholder="Ej: ¿Qué artículo tiene mayor riesgo de quiebre esta semana?",
                    label_visibility="collapsed",
                    key=f"nx_ia_txt_{page_key}",
                )
            with col_btn:
                enviado = st.form_submit_button("↑", use_container_width=True)

        if enviado and user_input:
            _enviar_pregunta(hist_key, user_input, context_fn, _modo_efectivo())

        # ── Botón limpiar ────────────────────────────────────────────
        if hist:
            if st.button("🗑️ Limpiar", key=f"nx_ia_clear_{page_key}"):
                st.session_state[hist_key] = []
                st.rerun()


# ── Helper interno ────────────────────────────────────────────────────────────

def _enviar_pregunta(
    hist_key: str,
    pregunta: str,
    context_fn: Optional[Callable[[], dict]],
    modo: str,
):
    """Agrega pregunta al historial, llama a la IA y guarda respuesta."""
    # Construir prompt enriquecido con contexto de la página
    contexto_str = ""
    if context_fn:
        try:
            ctx = context_fn()
            if ctx:
                import json
                contexto_str = (
                    "\n\n[DATOS ACTUALES DE LA PÁGINA]\n"
                    + json.dumps(ctx, ensure_ascii=False, default=str)
                    + "\n[FIN DATOS]\n"
                )
        except Exception:
            pass

    prompt_completo = f"{contexto_str}\n{pregunta}" if contexto_str else pregunta

    hist = st.session_state.get(hist_key, [])
    hist.append({"role": "user", "content": pregunta})  # guardar solo la pregunta limpia
    st.session_state[hist_key] = hist

    try:
        from modules.ia_engine import chat_con_ia
        with st.spinner("Pensando..."):
            # Pasar historial previo (sin el que acabamos de agregar)
            respuesta = chat_con_ia(
                historial=hist[:-1],
                nuevo_mensaje=prompt_completo,
                modo=modo,
            )
    except Exception as e:
        respuesta = f"⚠️ Error al consultar IA: {e}"

    hist.append({"role": "assistant", "content": respuesta})
    st.session_state[hist_key] = hist
    st.rerun()


# ── Context builders por página (helpers reutilizables) ──────────────────────

def ctx_inventario() -> dict:
    """Contexto para la página de Inventario."""
    try:
        from database import execute_query, query_to_df
        # Stockouts módulos
        stockouts = execute_query(
            "SELECT COUNT(*) as n FROM stock_snapshots ss "
            "JOIN (SELECT codigo,deposito,MAX(fecha) mf FROM stock_snapshots GROUP BY codigo,deposito) lx "
            "ON ss.codigo=lx.codigo AND ss.deposito=lx.deposito AND ss.fecha=lx.mf "
            "WHERE ss.stock=0 AND ss.deposito='SAN JOSE' AND ss.codigo GLOB '[A-Z]*'",
            fetch=True
        )
        # Top 5 con más demanda y poco stock
        df = query_to_df("""
            SELECT s.codigo, a.descripcion, s.stock,
                   COALESCE(dm.demanda_manual,0) as demanda
            FROM stock_snapshots s
            JOIN (SELECT codigo,deposito,MAX(fecha) mf FROM stock_snapshots
                  GROUP BY codigo,deposito) lx
              ON s.codigo=lx.codigo AND s.deposito=lx.deposito AND s.fecha=lx.mf
            LEFT JOIN articulos a ON s.codigo=a.codigo
            LEFT JOIN demanda_manual dm ON s.codigo=dm.codigo
            WHERE s.deposito='SAN JOSE' AND s.stock < 10 AND s.codigo GLOB '[A-Z]*'
            ORDER BY demanda DESC
            LIMIT 10
        """)
        criticos = df.to_dict("records") if not df.empty else []
        return {
            "stockouts_sj": stockouts[0]["n"] if stockouts else "?",
            "top_criticos": criticos,
        }
    except Exception:
        return {}


def ctx_auditoria() -> dict:
    """Contexto para la página de Auditoría."""
    try:
        from database import execute_query
        # Fechas disponibles
        fechas = execute_query(
            "SELECT DISTINCT fecha FROM stock_snapshots ORDER BY fecha DESC LIMIT 5",
            fetch=True
        )
        return {
            "snapshots_disponibles": [r["fecha"] for r in fechas] if fechas else [],
            "instruccion_extra": "Analizá variaciones inexplicables entre períodos "
                                 "y posibles movimientos de stock sin respaldo de ventas.",
        }
    except Exception:
        return {}


def ctx_cotizaciones() -> dict:
    """Contexto para la página de Cotizaciones/Tránsito."""
    try:
        from database import query_to_df
        df = query_to_df("""
            SELECT ci.codigo_flexxus, ci.descripcion, ci.cantidad, ci.precio_usd,
                   c.estado, c.proveedor, c.fecha_pedido
            FROM cotizacion_items ci
            JOIN cotizaciones c ON ci.cotizacion_id=c.id
            WHERE c.estado IN ('en_transito','pendiente')
            LIMIT 30
        """)
        pedidos_activos = df.to_dict("records") if not df.empty else []
        return {
            "pedidos_activos": pedidos_activos,
            "instruccion_extra": "Ayudá a estimar fechas de llegada, prioridades de pago "
                                  "y posibles riesgos de demora en tránsito.",
        }
    except Exception:
        return {}


def ctx_precios() -> dict:
    """Contexto para la página de Precios."""
    try:
        from database import query_to_df
        from config import MONEDA_USD_ARS
        df = query_to_df("""
            SELECT p.codigo, a.descripcion, p.lista_1, p.lista_4, p.p_comp
            FROM precios p
            JOIN (SELECT codigo, MAX(fecha) mf FROM precios GROUP BY codigo) lx
              ON p.codigo=lx.codigo AND p.fecha=lx.mf
            LEFT JOIN articulos a ON p.codigo=a.codigo
            WHERE p.lista_1 > 0
            ORDER BY p.lista_1 DESC
            LIMIT 20
        """)
        return {
            "tasa_usd_ars": MONEDA_USD_ARS,
            "muestra_precios": df.to_dict("records") if not df.empty else [],
        }
    except Exception:
        return {}


def ctx_mercadolibre() -> dict:
    """Contexto para la página de MercadoLibre."""
    try:
        from database import query_to_df
        df = query_to_df("""
            SELECT a.codigo, a.descripcion, p.lista_4,
                   a.mla_id_mec, a.mla_id_fr
            FROM articulos a
            LEFT JOIN (
                SELECT codigo, lista_4 FROM precios p2
                JOIN (SELECT codigo, MAX(fecha) mf FROM precios GROUP BY codigo) lx
                  ON p2.codigo=lx.codigo AND p2.fecha=lx.mf
            ) p ON a.codigo=p.codigo
            WHERE a.activo=1 AND (a.mla_id_mec IS NOT NULL OR a.mla_id_fr IS NOT NULL)
            LIMIT 20
        """)
        return {
            "publicaciones_ancladas": df.to_dict("records") if not df.empty else [],
            "instruccion_extra": "El proveedor activo es Mecánico (códigos numéricos). "
                                  "FR/AITECH está pausado temporalmente.",
        }
    except Exception:
        return {}


def ctx_borrador() -> dict:
    """Contexto para la página de Borrador de Pedido."""
    try:
        from database import query_to_df
        df = query_to_df("""
            SELECT b.codigo, b.descripcion, b.cantidad_sugerida,
                   b.precio_usd, b.prioridad
            FROM borrador_pedido b
            WHERE b.activo=1
            ORDER BY b.prioridad DESC
            LIMIT 30
        """)
        return {
            "items_borrador": df.to_dict("records") if not df.empty else [],
        }
    except Exception:
        return {}


def ctx_dashboard() -> dict:
    """Contexto para el Dashboard principal."""
    try:
        from database import execute_query
        rows = execute_query(
            "SELECT clave, valor FROM configuracion WHERE clave IN "
            "('ultimo_import_stock','ultimo_import_ventas','ultimo_import_precios')",
            fetch=True
        )
        cfg = {r["clave"]: r["valor"] for r in rows} if rows else {}
        # Resumen stockouts
        sq = execute_query(
            "SELECT COUNT(*) as n FROM stock_snapshots ss "
            "JOIN (SELECT codigo,deposito,MAX(fecha) mf FROM stock_snapshots GROUP BY codigo,deposito) lx "
            "ON ss.codigo=lx.codigo AND ss.deposito=lx.deposito AND ss.fecha=lx.mf "
            "WHERE ss.stock=0",
            fetch=True
        )
        return {
            "ultima_importacion": cfg,
            "total_stockouts": sq[0]["n"] if sq else "?",
        }
    except Exception:
        return {}


def ctx_defensa() -> dict:
    """Contexto para la página de Defensa de Presupuesto."""
    return {
        "modulos_pct_ventas": 35.1,
        "unidades_30d": 28224,
        "rma_loss_2_5m_usd": 24708,
        "rma_loss_anual_proy_usd": 118601,
        "presupuesto_actual_usd": 250000,
        "stockout_activos": 101,
        "remitos_sin_confirmar": 504,
        "baseline": "enero-noviembre 2025 (antes de Mariano)",
        "instruccion_extra": "Ayudame a construir argumentos sólidos para presentar "
                              "a Diego y Walter sobre el valor estratégico de los módulos. "
                              "Los módulos son el anchor product: el técnico que compra un módulo "
                              "también compra flex, adhesivo, vidrio, herramientas.",
    }
