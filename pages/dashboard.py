"""
ROKER NEXUS — Dashboard
Vista ejecutiva del estado del sistema.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from database import (
    query_to_df, get_quiebres, get_ultima_importacion,
    get_resumen_stats
)
from utils.horarios import ahora, hoy, label_horario
from utils.helpers import fmt_usd, fmt_ars, fmt_num, color_stock


def render():
    # ── Header ───────────────────────────────────────────────
    col_tit, col_fecha = st.columns([3, 1])
    with col_tit:
        st.markdown("""
        <h1 style="margin:0;font-size:28px;font-weight:700;
                   background:linear-gradient(90deg,var(--nx-accent),var(--nx-purple));
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            Dashboard
        </h1>
        <p style="margin:4px 0 20px;color:var(--nx-text2);font-size:14px;">
            Estado general del sistema
        </p>
        """, unsafe_allow_html=True)
    with col_fecha:
        st.markdown(f"""
        <div style="text-align:right;padding-top:8px">
            <div style="font-size:13px;color:var(--nx-text2)">{ahora().strftime('%A %d/%m/%Y')}</div>
            <div style="font-size:20px;font-weight:700;color:var(--nx-text)">{ahora().strftime('%H:%M')}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Stats ────────────────────────────────────────────────
    stats = get_resumen_stats()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sin_stock = stats.get("sin_stock", 0)
        delta_color = "inverse" if sin_stock > 0 else "normal"
        st.metric("Sin Stock 🔴", sin_stock,
                  help="Artículos con stock = 0")
    with c2:
        bajo_min = stats.get("bajo_minimo", 0)
        st.metric("Bajo Mínimo 🟡", bajo_min,
                  help="Stock menor al mínimo configurado")
    with c3:
        total_arts = stats.get("total_articulos", 0)
        st.metric("Artículos Activos", fmt_num(total_arts))
    with c4:
        ultima_imp = stats.get("ultima_importacion", "—")
        st.metric("Última Importación", ultima_imp)

    st.divider()

    # ── Dos columnas principales ──────────────────────────────
    col_izq, col_der = st.columns([3, 2])

    with col_izq:
        st.markdown("#### 🔴 Quiebres urgentes")
        df_q = get_quiebres(umbral=0)

        if df_q.empty:
            st.success("✅ Sin quiebres en stock cero al momento.")
        else:
            # Tabla compacta
            cols_show = ["codigo", "descripcion", "deposito", "stock", "stock_minimo"]
            cols_show = [c for c in cols_show if c in df_q.columns]
            df_show = df_q[cols_show].head(15).copy()

            if "stock" in df_show.columns:
                df_show.insert(0, "🚦", df_show["stock"].apply(color_stock))

            st.dataframe(
                df_show,
                width="stretch",
                hide_index=True,
                column_config={
                    "🚦": st.column_config.TextColumn("", width="small"),
                    "codigo": st.column_config.TextColumn("Código", width="medium"),
                    "descripcion": st.column_config.TextColumn("Artículo", width="large"),
                    "deposito": st.column_config.TextColumn("Depósito", width="medium"),
                    "stock": st.column_config.NumberColumn("Stock", format="%d"),
                    "stock_minimo": st.column_config.NumberColumn("Mínimo", format="%d"),
                }
            )

            if len(df_q) > 15:
                st.caption(f"Mostrando 15 de {len(df_q)} quiebres. Ver todos en 📦 Inventario.")

    with col_der:
        st.markdown("#### 📊 Stock por depósito")
        _grafico_depositos()

        st.markdown("#### 📅 Próximas actualizaciones")
        _panel_horarios()

    # ── Log de importaciones recientes ───────────────────────
    st.divider()
    st.markdown("#### 📥 Últimas importaciones")
    df_log = query_to_df("""
        SELECT tipo_archivo, nombre_archivo, filas_importadas,
               estado, importado_en
        FROM importaciones_log
        ORDER BY importado_en DESC LIMIT 10
    """)
    if df_log.empty:
        st.info("No hay importaciones registradas. Cargá tu primer archivo en 📥 Cargar Archivos.")
    else:
        st.dataframe(df_log, width="stretch", hide_index=True)


def _grafico_depositos():
    try:
        df = query_to_df("""
            SELECT s.deposito,
                   COUNT(*) as articulos,
                   SUM(CASE WHEN s.stock=0 THEN 1 ELSE 0 END) as sin_stock,
                   SUM(CASE WHEN s.stock>0 AND s.stock<s.stock_minimo THEN 1 ELSE 0 END) as bajo_min
            FROM stock_snapshots s
            JOIN (
                SELECT codigo, deposito, MAX(fecha) as mf
                FROM stock_snapshots GROUP BY codigo, deposito
            ) latest ON s.codigo=latest.codigo AND s.deposito=latest.deposito AND s.fecha=latest.mf
            GROUP BY s.deposito
        """)
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        st.caption("Sin datos de stock. Cargá archivos primero.")
        return

    fig = go.Figure()
    depositos = df["deposito"].tolist()
    fig.add_bar(name="Sin stock", x=depositos, y=df["sin_stock"],
                marker_color="#ff5252")
    fig.add_bar(name="Bajo mínimo", x=depositos, y=df["bajo_min"],
                marker_color="#ffab40")
    ok = df["articulos"] - df["sin_stock"] - df["bajo_min"]
    fig.add_bar(name="OK", x=depositos, y=ok, marker_color="#00e676")

    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Space Grotesk", size=11, color="#8b95a8"),
        height=200,
        margin=dict(l=0, r=0, t=10, b=30),
        legend=dict(orientation="h", y=-0.3, font_size=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _panel_horarios():
    from config import ACTUALIZACIONES_SUGERIDAS
    ahora_h = ahora()
    hoy_dow = ahora_h.weekday()

    st.markdown("""
    <style>
    .hor-row{display:flex;align-items:center;gap:10px;padding:5px 0;
             border-bottom:1px solid var(--nx-border);font-size:12px}
    .hor-row:last-child{border-bottom:none}
    .hor-time{font-family:monospace;color:var(--nx-accent);min-width:45px}
    .hor-task{color:var(--nx-text2);flex:1}
    .hor-freq{font-size:10px;color:var(--nx-text3)}
    </style>
    """, unsafe_allow_html=True)

    rows_html = ""
    for a in ACTUALIZACIONES_SUGERIDAS[:5]:
        rows_html += f"""
        <div class="hor-row">
            <span class="hor-time">{a['hora']}</span>
            <span class="hor-task">{a['tarea']}</span>
            <span class="hor-freq">{a['frecuencia']}</span>
        </div>"""
    st.markdown(f'<div class="nx-card">{rows_html}</div>', unsafe_allow_html=True)
