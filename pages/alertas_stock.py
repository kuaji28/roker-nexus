"""
ROKER NEXUS — Alertas de Stock

Muestra las alertas generadas automáticamente cada vez que se importa
un archivo de stock:
  🟢 AUMENTO   → stock subió → verificar si llegó mercadería sin aviso
  🔴 QUIEBRE   → SKU pasó de positivo a 0 → quedó sin stock
  ⚠️ CAÍDA MASIVA → muchos SKUs bajaron a la vez → revisar si hubo pedido
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from database import execute_query


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700">🔔 Alertas de Stock</h1>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
    Detecciones automáticas al importar archivos de stock.
    <b>AUMENTO</b>: llegó mercadería (verificá si te avisaron).
    <b>QUIEBRE</b>: SKU llegó a 0.
    <b>CAÍDA MASIVA</b>: muchos SKUs bajaron juntos.</p>
    """, unsafe_allow_html=True)

    try:
        from modules.stock_alertas import (
            get_todas_alertas, get_alertas_sin_ver,
            marcar_vistas, count_alertas_sin_ver
        )
    except Exception as e:
        st.error(f"Error al cargar módulo de alertas: {e}")
        return

    # ── Filtros ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        solo_sin_ver = st.checkbox("Solo sin ver", value=True, key="alerta_sv")
    with c2:
        tipo_f = st.selectbox("Tipo", ["Todos","AUMENTO","QUIEBRE","CAIDA_MASIVA"], key="alerta_t")
    with c3:
        dep_f  = st.selectbox("Depósito", ["Todos","SAN_JOSE","LARREA","GENERAL"], key="alerta_d")
    with c4:
        dias_f = st.selectbox("Período", [7, 14, 30, 60, 90], index=1, key="alerta_per",
                              format_func=lambda x: f"Últimos {x} días")

    # ── Cargar alertas ────────────────────────────────────────────────────────
    df = get_todas_alertas(dias=dias_f, limit=500)
    if df.empty:
        st.info("✅ Sin alertas registradas para este período.")
        st.caption("Las alertas se generan automáticamente al importar archivos de stock.")
        return

    # Filtros
    if solo_sin_ver:
        df = df[df["visto"] == 0]
    if tipo_f != "Todos":
        df = df[df["tipo_alerta"] == tipo_f]
    if dep_f != "Todos":
        df = df[df["deposito"] == dep_f]

    if df.empty:
        st.info("✅ Sin alertas con los filtros aplicados.")
        return

    # ── KPIs rápidos ──────────────────────────────────────────────────────────
    total_sin_ver = count_alertas_sin_ver()
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1:
        n_aum = int((df["tipo_alerta"] == "AUMENTO").sum())
        st.metric("📈 Aumentos", n_aum, help="Stock subió → verificar recepción")
    with col_k2:
        n_qui = int((df["tipo_alerta"] == "QUIEBRE").sum())
        st.metric("🔴 Quiebres", n_qui, help="SKU llegó a 0 unidades")
    with col_k3:
        n_mas = int((df["tipo_alerta"] == "CAIDA_MASIVA").sum())
        st.metric("⚠️ Caídas masivas", n_mas, help="Muchos SKUs bajaron a la vez")
    with col_k4:
        st.metric("🔔 Sin ver (total)", total_sin_ver)

    st.divider()

    # ── Tabla de alertas ──────────────────────────────────────────────────────
    def _fmt_tipo(t):
        return {"AUMENTO":"📈 Aumento","QUIEBRE":"🔴 Quiebre",
                "CAIDA_MASIVA":"⚠️ Caída masiva"}.get(t, t)

    def _fmt_sev(s):
        return {"error":"🔴","warning":"🟡","info":"🟢"}.get(s, "⚪")

    df_show = df.copy()
    df_show["Tipo"]       = df_show["tipo_alerta"].apply(_fmt_tipo)
    df_show["Sev."]       = df_show["severidad"].apply(_fmt_sev)
    df_show["Fecha"]      = pd.to_datetime(df_show["fecha"], errors="coerce").dt.strftime("%d/%m %H:%M")
    df_show["Depósito"]   = df_show["deposito"].fillna("—")
    df_show["Ant."]       = df_show["stock_anterior"].apply(lambda x: f"{int(x):,}")
    df_show["Nuevo"]      = df_show["stock_nuevo"].apply(lambda x: f"{int(x):,}")
    df_show["Dif."]       = df_show["diferencia"].apply(
        lambda x: f"+{int(x)}" if x > 0 else f"{int(x)}")

    cols_show = ["Sev.","Tipo","codigo","descripcion","Depósito","Ant.","Nuevo","Dif.","Fecha"]
    df_display = df_show[[c for c in cols_show if c in df_show.columns]].rename(columns={
        "codigo": "Código", "descripcion": "Artículo"
    })

    st.dataframe(
        df_display,
        hide_index=True,
        use_container_width=True,
        height=400,
        column_config={
            "Sev.":     st.column_config.TextColumn("", width="small"),
            "Tipo":     st.column_config.TextColumn("Tipo", width="medium"),
            "Código":   st.column_config.TextColumn("Código", width="small"),
            "Artículo": st.column_config.TextColumn("Artículo", width="large"),
            "Depósito": st.column_config.TextColumn("Depósito", width="small"),
            "Ant.":     st.column_config.TextColumn("Ant.", width="small"),
            "Nuevo":    st.column_config.TextColumn("Nuevo", width="small"),
            "Dif.":     st.column_config.TextColumn("Dif.", width="small"),
            "Fecha":    st.column_config.TextColumn("Fecha", width="small"),
        }
    )

    st.caption(f"{len(df_display):,} alertas mostradas")

    # ── Acciones ──────────────────────────────────────────────────────────────
    col_a1, col_a2, _ = st.columns([2, 2, 6])
    with col_a1:
        if st.button("✅ Marcar todas como vistas", type="primary", width="stretch"):
            ids = df["id"].tolist() if "id" in df.columns else []
            marcar_vistas(ids)
            st.success("Alertas marcadas como vistas.")
            st.rerun()
    with col_a2:
        if st.button("🗑️ Borrar vistas (>30 días)", width="stretch"):
            try:
                execute_query(
                    "DELETE FROM stock_alertas WHERE visto=1 AND fecha < datetime('now','-30 days')",
                    fetch=False
                )
                st.success("Alertas antiguas eliminadas.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # ── Sección informativa ───────────────────────────────────────────────────
    with st.expander("ℹ️ ¿Cómo funcionan las alertas?"):
        st.markdown("""
**📈 AUMENTO de stock**
Se detecta cuando un SKU tiene más unidades que en el snapshot anterior.
Mínimo: +3 unidades y +20% de aumento.
→ Significa que probablemente llegó mercadería. Si nadie te avisó, reclamá.

**🔴 QUIEBRE**
El SKU pasó de tener stock positivo a 0 unidades.
→ Quedaste sin ese artículo. Revisá si hay pedido pendiente o si hay que pedir.

**⚠️ CAÍDA MASIVA**
Muchos SKUs (≥10) bajaron al menos un 30% al mismo tiempo.
→ Probablemente hubo una venta mayorista o un movimiento de stock no reportado.

**🔔 Notificaciones Telegram**
Si configuraste el bot de Telegram en el sidebar, las alertas también se envían
al chat configurado en tiempo real cuando importás el archivo.
        """)

    # ── IA contextual ──────────────────────────────────────────
    from utils.ia_widget import nx_ai_widget
    nx_ai_widget(
        page_key  = "alertas",
        titulo    = "🤖 Analizar alertas con IA",
        subtitulo = "Interpretá las alertas y priorizá acciones",
        sugeridas = [
            ("🎯 Priorizar alertas",    "¿Cuál de estas alertas es más crítica y por qué? ¿Por dónde arranco?"),
            ("📦 ¿Qué pedir urgente?",  "Basándote en las alertas activas, ¿qué artículos deberían ir en el próximo pedido?"),
            ("⚠️ Anomalías recientes",  "¿Hay alguna caída de stock que no se explica solo por ventas?"),
            ("📋 Redactar informe",     "Redactá un resumen de las alertas actuales para reportar a Diego."),
        ],
        collapsed = True,
    )
