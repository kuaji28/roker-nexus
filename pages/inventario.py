"""
ROKER NEXUS — Página: Inventario & Quiebres
"""
import streamlit as st
import pandas as pd

from modules.inventario import (
    detectar_quiebres, detectar_quiebre_entre_depositos,
    agregar_a_lista_negra, quitar_de_lista_negra,
    get_lista_negra, get_resumen_stock, get_anomalias_abiertas
)
from database import query_to_df
from utils.helpers import fmt_usd, fmt_num, color_stock, severidad_badge
from config import DEPOSITOS


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        📦 Inventario & Quiebres
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:20px">
        Detección automática de quiebres, anomalías y lista negra
    </p>
    """, unsafe_allow_html=True)

    # ── Resumen rápido ────────────────────────────────────────
    resumen = get_resumen_stock()
    if resumen:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total artículos", fmt_num(resumen.get("total_articulos", 0)))
        c2.metric("Sin stock 🔴", resumen.get("sin_stock", 0))
        c3.metric("Bajo mínimo 🟡", resumen.get("bajo_minimo", 0))
        c4.metric("Depósitos activos", resumen.get("depositos_activos", 0))
        st.divider()

    tabs = st.tabs([
        "🔴 Quiebres",
        "⚡ Larrea vs San José",
        "🔍 Investigar",
        "⛔ Lista Negra",
        "📋 Anomalías",
    ])

    # ── Tab Quiebres ──────────────────────────────────────────
    with tabs[0]:
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        with col_f1:
            deposito_sel = st.selectbox(
                "Depósito",
                ["Todos"] + list(DEPOSITOS.keys()),
                format_func=lambda k: DEPOSITOS.get(k, k) if k != "Todos" else "Todos",
            )
        with col_f2:
            umbral = st.slider("Umbral de stock", 0, 50, 10)
        with col_f3:
            solo_cero = st.checkbox("Solo stock=0", value=False)

        dep = deposito_sel if deposito_sel != "Todos" else None
        umb = 0 if solo_cero else umbral

        df_q = detectar_quiebres(umbral=umb, deposito=dep)

        if df_q.empty:
            st.success("✅ No hay quiebres con los filtros actuales.")
        else:
            st.markdown(f"**{len(df_q)} artículos** con stock ≤ {umb}")

            # Botones de acción rápida
            col_a, col_b, col_c = st.columns([2, 2, 4])
            with col_a:
                if st.button("📤 Exportar Excel", width="stretch"):
                    _exportar_excel(df_q, "quiebres")
            with col_b:
                if st.button("🤖 Analizar con IA", width="stretch"):
                    st.session_state["analizar_quiebres"] = True

            # Tabla principal
            cols_show = [c for c in [
                "codigo", "descripcion", "deposito", "marca",
                "stock", "stock_minimo", "severidad",
                "stock_central", "accion_sugerida"
            ] if c in df_q.columns]

            df_show = df_q[cols_show].copy()
            df_show.insert(0, "🚦", df_show["stock"].apply(color_stock))

            st.dataframe(
                df_show,
                width="stretch",
                hide_index=True,
                column_config={
                    "🚦": st.column_config.TextColumn("", width="small"),
                    "codigo": st.column_config.TextColumn("Código"),
                    "descripcion": st.column_config.TextColumn("Artículo", width="large"),
                    "stock": st.column_config.NumberColumn("Stock", format="%d"),
                    "stock_minimo": st.column_config.NumberColumn("Mínimo", format="%d"),
                    "stock_central": st.column_config.NumberColumn("San José", format="%d"),
                    "accion_sugerida": st.column_config.TextColumn("Acción sugerida", width="large"),
                }
            )

            # Análisis IA
            if st.session_state.get("analizar_quiebres"):
                with st.spinner("🤖 Analizando quiebres con Claude..."):
                    from modules.ia_engine import motor_ia
                    analisis = motor_ia.analizar_quiebres(df_q)
                    st.info(analisis)
                st.session_state["analizar_quiebres"] = False

    # ── Tab Larrea vs San José ────────────────────────────────
    with tabs[1]:
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:16px">
            Detecta artículos donde <b>Larrea tiene stock cero</b> pero
            <b>San José tiene stock disponible</b> — posible falla de reposición interna.
        </div>
        """, unsafe_allow_html=True)

        df_cruce = detectar_quiebre_entre_depositos()

        if df_cruce.empty:
            st.success("✅ No hay quiebres de reposición interna detectados.")
        else:
            st.warning(f"⚠️ {len(df_cruce)} artículos en Larrea sin stock cuando San José tiene stock")

            for _, row in df_cruce.head(20).iterrows():
                col1, col2, col3 = st.columns([4, 2, 2])
                with col1:
                    desc = row.get("descripcion") or row.get("codigo", "?")
                    st.markdown(f"**{desc}** `{row.get('codigo','')}`")
                with col2:
                    st.markdown(f"🔴 Larrea: **{int(row.get('stock_larrea',0))} uds**")
                with col3:
                    st.markdown(f"🟢 San José: **{int(row.get('stock_san_jose',0))} uds**")

                col_btn1, col_btn2, _ = st.columns([2, 2, 4])
                with col_btn1:
                    if st.button(f"⚡ Marcar para remito", key=f"remito_{row.get('codigo','')}"):
                        st.success(f"Marcado ✓")
                with col_btn2:
                    if st.button(f"🔍 Investigar", key=f"inv_{row.get('codigo','')}"):
                        st.session_state["investigar_codigo"] = row.get("codigo", "")
                st.divider()

    # ── Tab Investigar ────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 🔍 Ficha de investigación de artículo")
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:16px">
            Ingresá el código para ver el historial completo del artículo en todos los depósitos.
        </div>
        """, unsafe_allow_html=True)

        codigo_inv = st.text_input(
            "Código del artículo",
            value=st.session_state.get("investigar_codigo", ""),
            placeholder="Ej: 2401251672 o MSAMA10S.",
            key="input_investigar"
        )

        if codigo_inv:
            _ficha_investigacion(codigo_inv)

    # ── Tab Lista Negra ───────────────────────────────────────
    with tabs[3]:
        st.markdown("### ⛔ Lista Negra")
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:16px">
            Artículos excluidos de sugerencias de compra. Se pueden reactivar en cualquier momento.
        </div>
        """, unsafe_allow_html=True)

        # Agregar manualmente
        with st.expander("➕ Agregar artículo a lista negra"):
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                codigo_neg = st.text_input("Código", key="input_negro_cod")
            with col2:
                motivo_neg = st.text_input("Motivo (opcional)", key="input_negro_mot")
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Agregar ⛔", width="stretch"):
                    if codigo_neg:
                        if agregar_a_lista_negra(codigo_neg.strip(), motivo_neg):
                            st.success(f"✅ {codigo_neg} agregado a lista negra")
                            st.rerun()

        df_neg = get_lista_negra()
        if df_neg.empty:
            st.info("La lista negra está vacía.")
        else:
            st.markdown(f"**{len(df_neg)} artículos** en lista negra")
            for _, row in df_neg.iterrows():
                col1, col2, col3, col4 = st.columns([2, 3, 3, 1])
                with col1:
                    st.markdown(f"`{row.get('codigo','')}`")
                with col2:
                    st.markdown(f"<span style='font-size:13px'>{row.get('descripcion','') or '—'}</span>",
                                unsafe_allow_html=True)
                with col3:
                    st.markdown(f"<span style='font-size:12px;color:var(--nx-text2)'>{row.get('motivo_negra','') or '—'}</span>",
                                unsafe_allow_html=True)
                with col4:
                    if st.button("↩️", key=f"quitar_{row.get('codigo','')}",
                                 help="Quitar de lista negra"):
                        quitar_de_lista_negra(row.get("codigo", ""))
                        st.rerun()

    # ── Tab Anomalías ─────────────────────────────────────────
    with tabs[4]:
        df_an = get_anomalias_abiertas()
        if df_an.empty:
            st.success("✅ No hay anomalías abiertas.")
        else:
            st.warning(f"⚠️ {len(df_an)} anomalías abiertas")
            for _, row in df_an.iterrows():
                sev = row.get("severidad", "media")
                border = {"alta": "var(--nx-red)", "media": "var(--nx-amber)"}.get(sev, "var(--nx-border)")
                st.markdown(f"""
                <div class="nx-card" style="border-left:3px solid {border}">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <span style="font-size:13px;font-weight:500;color:var(--nx-text)">
                            {row.get('codigo','')} — {row.get('tipo','')}
                        </span>
                        {severidad_badge(sev)}
                    </div>
                    <div style="font-size:12px;color:var(--nx-text2);margin-top:4px">
                        {row.get('descripcion','')} | {row.get('deposito','')}
                    </div>
                </div>
                """, unsafe_allow_html=True)


def _ficha_investigacion(codigo: str):
    """Muestra historial completo de un artículo."""
    # Info básica
    df_art = query_to_df(
        "SELECT * FROM articulos WHERE codigo=?", (codigo,)
    )
    if not df_art.empty:
        row = df_art.iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Artículo:** {row.get('descripcion','—')}")
            st.markdown(f"**Marca:** {row.get('marca','—')}")
        with col2:
            st.markdown(f"**Tipo:** {row.get('tipo_codigo','—')}")
            neg = "⛔ En lista negra" if row.get("en_lista_negra") else "✅ Activo"
            st.markdown(f"**Estado:** {neg}")

    # Historial de stock por depósito
    df_hist = query_to_df("""
        SELECT deposito, stock, fecha
        FROM stock_snapshots
        WHERE codigo=?
        ORDER BY fecha DESC, deposito
        LIMIT 60
    """, (codigo,))

    if not df_hist.empty:
        st.markdown("**📊 Historial de stock:**")
        import plotly.express as px
        fig = px.line(
            df_hist, x="fecha", y="stock", color="deposito",
            color_discrete_sequence=["#00d2ff", "#00e676", "#ffab40"],
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Space Grotesk", size=11, color="#8b95a8"),
            height=200, margin=dict(l=0,r=0,t=10,b=30),
            legend=dict(orientation="h", y=-0.4, font_size=10),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    else:
        st.info("Sin historial de stock para este código.")

    # Precio
    df_precio = query_to_df(
        "SELECT lista_1, lista_4, fecha FROM precios WHERE codigo=? ORDER BY fecha DESC LIMIT 1",
        (codigo,)
    )
    if not df_precio.empty:
        p = df_precio.iloc[0]
        col1, col2 = st.columns(2)
        col1.metric("Lista 1 (mayorista)", fmt_usd(p.get("lista_1", 0)))
        col2.metric("Lista 4 (MercadoLibre)", fmt_usd(p.get("lista_4", 0)))


def _exportar_excel(df: pd.DataFrame, nombre: str):
    """Exporta un DataFrame a Excel y ofrece descarga."""
    from io import BytesIO
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Datos")
    buf.seek(0)
    fecha = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        f"⬇️ Descargar {nombre}_{fecha}.xlsx",
        data=buf,
        file_name=f"{nombre}_{fecha}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
