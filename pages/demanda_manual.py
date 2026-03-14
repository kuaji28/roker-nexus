"""ROKER NEXUS — Demanda Manual"""
import streamlit as st
from database import query_to_df, execute_query, get_config

def set_demanda_manual(codigo, demanda, nota=""):
    try:
        execute_query("CREATE TABLE IF NOT EXISTS demanda_manual (codigo TEXT PRIMARY KEY, demanda_manual REAL NOT NULL, nota TEXT, actualizado TEXT DEFAULT (datetime('now')))", fetch=False)
        if demanda <= 0:
            execute_query("DELETE FROM demanda_manual WHERE codigo=?", (codigo,), fetch=False)
        else:
            execute_query("""INSERT INTO demanda_manual (codigo,demanda_manual,nota,actualizado)
                VALUES(?,?,?,datetime('now')) ON CONFLICT(codigo) DO UPDATE SET
                demanda_manual=excluded.demanda_manual, nota=excluded.nota, actualizado=datetime('now')
            """, (codigo, demanda, nota), fetch=False)
    except Exception as e:
        raise e

def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700">✏️ Demanda Manual</h1>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
    Override cuando el ERP muestra 0 por quiebre de stock real. La demanda manual tiene prioridad.</p>
    """, unsafe_allow_html=True)

    st.info("💡 Usá esto cuando Flexxus muestra 0 ventas porque te quedaste sin stock. Ingresá la demanda mensual real.")

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: filtro = st.text_input("🔍 Filtrar", "", key="dm_f")
    with c2: solo_cero = st.checkbox("Solo ERP=0", True, key="dm_z")
    with c3: prov_f = st.selectbox("Proveedor", ["Todos","FR","Mecánico"], key="dm_p")

    try:
        execute_query("CREATE TABLE IF NOT EXISTS demanda_manual (codigo TEXT PRIMARY KEY, demanda_manual REAL NOT NULL, nota TEXT, actualizado TEXT DEFAULT (datetime('now')))", fetch=False)
        df = query_to_df("""
            SELECT o.codigo, COALESCE(a.descripcion, o.descripcion) as articulo,
                   o.demanda_promedio as dem_erp, o.stock_actual,
                   COALESCE(dm.demanda_manual, 0) as dem_manual,
                   CASE WHEN o.codigo GLOB '[0-9]*' THEN 'Mecánico' ELSE 'FR' END as proveedor
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo=a.codigo
            LEFT JOIN demanda_manual dm ON o.codigo=dm.codigo
            ORDER BY o.demanda_promedio ASC, o.codigo
        """)
    except Exception as e:
        st.error(f"Error: {e}"); return

    if df.empty:
        st.info("Sin datos. Cargá primero el archivo de Optimización de Stock.")
        return

    if filtro:
        m = (df["articulo"].str.upper().str.contains(filtro.upper(),na=False) |
             df["codigo"].str.upper().str.contains(filtro.upper(),na=False))
        df = df[m]
    if solo_cero: df = df[df["dem_erp"] == 0]
    if prov_f != "Todos": df = df[df["proveedor"] == prov_f]

    st.caption(f"{len(df):,} artículos")
    df_e = df[["codigo","articulo","proveedor","stock_actual","dem_erp","dem_manual"]].reset_index(drop=True)

    edited = st.data_editor(df_e, width='stretch', hide_index=True, height=500,
        column_config={
            "codigo":       st.column_config.TextColumn("Código", disabled=True),
            "articulo":     st.column_config.TextColumn("Artículo", disabled=True, width="large"),
            "proveedor":    st.column_config.TextColumn("Prov.", disabled=True, width="small"),
            "stock_actual": st.column_config.NumberColumn("Stock", disabled=True, format="%d"),
            "dem_erp":      st.column_config.NumberColumn("Dem. ERP", disabled=True, format="%.1f"),
            "dem_manual":   st.column_config.NumberColumn("Dem. Manual ✏️", min_value=0, format="%.1f",
                                help="0 = eliminar override"),
        }, num_rows="fixed", key="dm_editor")

    if st.button("💾 Guardar cambios", type="primary"):
        cambios = 0
        for i, row in edited.iterrows():
            nueva = float(row["dem_manual"] or 0)
            vieja = float(df_e.iloc[i]["dem_manual"] or 0)
            if abs(nueva - vieja) > 0.01:
                set_demanda_manual(row["codigo"], nueva)
                cambios += 1
        if cambios: st.success(f"✅ {cambios} override(s) guardados."); st.rerun()
        else: st.info("Sin cambios.")
