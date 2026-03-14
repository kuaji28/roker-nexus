"""
ROKER NEXUS — Demanda Manual
Override de demanda cuando el ERP muestra 0 por quiebre de stock real.
"""
import streamlit as st
import pandas as pd
from database import get_config, set_demanda_manual, query_to_df, execute_query


def render():
    st.markdown("""
    <h2 style="margin:0 0 4px;font-size:22px;font-weight:700">✏️ Demanda Manual</h2>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:8px">
    Override de demanda cuando el ERP muestra 0 por quiebre de stock real.
    La demanda manual tiene prioridad sobre el promedio del ERP.</p>
    """, unsafe_allow_html=True)

    st.info("💡 Usá esto cuando Flexxus muestra 0 ventas porque te quedaste sin stock. "
            "Escribí la demanda mensual real para que los cálculos de reposición sean correctos.")

    # Filtros
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: filtro = st.text_input("🔍 Filtrar artículo o código", "", key="dm_filtro")
    with c2: solo_cero = st.checkbox("Solo ERP = 0", value=True, key="dm_solo_cero")
    with c3:
        proveedor_f = st.selectbox("Proveedor", ["Todos", "FR", "MECÁNICO"], key="dm_prov")

    # Cargar datos
    df = query_to_df("""
        SELECT o.codigo,
               COALESCE(a.descripcion, o.descripcion) as articulo,
               o.demanda_promedio as dem_erp,
               o.stock_actual,
               COALESCE(dm.demanda_manual, 0) as dem_manual,
               CASE WHEN o.codigo GLOB '[0-9]*' THEN 'MECÁNICO' ELSE 'FR' END as proveedor
        FROM optimizacion o
        LEFT JOIN articulos a ON o.codigo=a.codigo
        LEFT JOIN demanda_manual dm ON o.codigo=dm.codigo
        WHERE COALESCE(a.en_lista_negra, 0) = 0
        ORDER BY o.demanda_promedio ASC, o.codigo
    """)

    if df.empty:
        st.info("Sin datos. Cargá primero el archivo de Optimización de Stock.")
        return

    if filtro:
        m = (df["articulo"].str.upper().str.contains(filtro.upper(), na=False) |
             df["codigo"].str.upper().str.contains(filtro.upper(), na=False))
        df = df[m]
    if solo_cero:
        df = df[df["dem_erp"] == 0]
    if proveedor_f != "Todos":
        df = df[df["proveedor"] == proveedor_f]

    st.caption(f"Mostrando {len(df):,} artículos")

    df_edit = df[["codigo","articulo","proveedor","stock_actual","dem_erp","dem_manual"]].copy()
    df_edit = df_edit.reset_index(drop=True)

    edited = st.data_editor(
        df_edit,
        width='stretch',
        hide_index=True,
        height=520,
        column_config={
            "codigo":       st.column_config.TextColumn("Código", disabled=True, width="small"),
            "articulo":     st.column_config.TextColumn("Artículo", disabled=True, width="large"),
            "proveedor":    st.column_config.TextColumn("Prov.", disabled=True, width="small"),
            "stock_actual": st.column_config.NumberColumn("Stock", disabled=True, format="%d"),
            "dem_erp":      st.column_config.NumberColumn("Dem. ERP", disabled=True, format="%.1f"),
            "dem_manual":   st.column_config.NumberColumn(
                "Dem. Manual ✏️", min_value=0, format="%.1f",
                help="Demanda mensual real. 0 = sin override."
            ),
        },
        num_rows="fixed",
        key="editor_demanda"
    )

    if st.button("💾 Guardar cambios", type="primary"):
        cambios = 0
        for i, row in edited.iterrows():
            cod   = row["codigo"]
            nueva = float(row["dem_manual"] or 0)
            vieja = float(df_edit.iloc[i]["dem_manual"] or 0)
            if abs(nueva - vieja) > 0.01:
                set_demanda_manual(cod, nueva)
                cambios += 1
        if cambios:
            st.success(f"✅ {cambios} override(s) guardados.")
            st.rerun()
        else:
            st.info("Sin cambios.")
