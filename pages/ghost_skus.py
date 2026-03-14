"""ROKER NEXUS — Ghost SKUs"""
import streamlit as st
from database import execute_query, query_to_df

def _ensure():
    execute_query("""CREATE TABLE IF NOT EXISTS ghost_skus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo_descripcion TEXT NOT NULL, proveedor_tipo TEXT DEFAULT 'MECÁNICO',
        cantidad_estimada REAL DEFAULT 0, estado TEXT DEFAULT 'PENDIENTE',
        codigo_vinculado TEXT DEFAULT '', notas TEXT DEFAULT '',
        origen TEXT DEFAULT 'WEB', fecha_creacion TEXT DEFAULT (datetime('now')),
        fecha_vinculacion TEXT)""", fetch=False)

def render():
    _ensure()
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700">👻 Ghost SKUs</h1>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
    Módulos pedidos antes de tener código asignado en Flexxus.</p>
    """, unsafe_allow_html=True)

    if st.toggle("➕ Agregar Ghost SKU", key="gs_toggle"):
        c1, c2, c3 = st.columns([3,1.5,1])
        with c1: modelo = st.text_input("Descripción *", placeholder="Ej: Samsung A06 módulo OLED", key="gs_mod")
        with c2: prov   = st.selectbox("Proveedor", ["MECÁNICO","FR"], key="gs_prov")
        with c3: qty    = st.number_input("Cant.", 0, value=0, step=10, key="gs_qty")
        notas = st.text_area("Notas", height=60, key="gs_notas")
        if st.button("👻 Crear", type="primary", key="gs_crear"):
            if not modelo.strip(): st.error("Ingresá la descripción.")
            else:
                execute_query("INSERT INTO ghost_skus (modelo_descripcion,proveedor_tipo,cantidad_estimada,notas) VALUES(?,?,?,?)",
                    (modelo, prov, float(qty), notas), fetch=False)
                st.success("✅ Ghost SKU creado"); st.rerun()

    st.divider()
    filtro_e = st.selectbox("Estado", ["PENDIENTE","VINCULADO","CANCELADO","Todos"], key="gs_est")
    w = f"WHERE estado='{filtro_e}'" if filtro_e != "Todos" else ""
    df_g = query_to_df(f"SELECT * FROM ghost_skus {w} ORDER BY fecha_creacion DESC")

    if df_g.empty: st.info(f"No hay Ghost SKUs en {filtro_e}."); return
    st.caption(f"{len(df_g)} Ghost SKU(s)")

    for _, row in df_g.iterrows():
        gid = int(row["id"]); mod = str(row["modelo_descripcion"])
        prov = str(row["proveedor_tipo"]); qty = int(row.get("cantidad_estimada",0) or 0)
        est  = str(row["estado"]); vinc = str(row.get("codigo_vinculado","") or "")
        notas = str(row.get("notas","") or "")
        emoji = {"PENDIENTE":"🟡","VINCULADO":"🟢","CANCELADO":"⛔"}.get(est,"⚪")
        with st.container():
            st.markdown(f"**{emoji} ID {gid}** — {mod[:60]} | {prov} | {qty} u")
            c1, c2 = st.columns([3,2])
            with c1:
                st.write(f"**Estado:** {est} | **Prov:** {prov}")
                if notas: st.write(f"**Notas:** {notas}")
                if vinc:  st.write(f"**Código vinculado:** `{vinc}`")
            with c2:
                if est == "PENDIENTE":
                    cod = st.text_input("Código ERP", key=f"gs_c_{gid}", placeholder="Ej: MSAMA06.")
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button("🔗 Vincular", key=f"gs_v_{gid}"):
                            if cod.strip():
                                execute_query("UPDATE ghost_skus SET estado='VINCULADO', codigo_vinculado=?, fecha_vinculacion=datetime('now') WHERE id=?", (cod.strip(), gid), fetch=False)
                                st.success("✅"); st.rerun()
                    with cb:
                        if st.button("❌ Cancelar", key=f"gs_x_{gid}"):
                            execute_query("UPDATE ghost_skus SET estado='CANCELADO' WHERE id=?", (gid,), fetch=False); st.rerun()
