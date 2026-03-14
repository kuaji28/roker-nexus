"""
ROKER NEXUS — Ghost SKUs
Módulos pedidos antes de tener código asignado en el ERP.
"""
import streamlit as st
from database import crear_ghost_sku, get_ghost_skus, vincular_ghost_sku, actualizar_ghost_sku


def render():
    st.markdown("""
    <h2 style="margin:0 0 4px;font-size:22px;font-weight:700">👻 Ghost SKUs</h2>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:8px">
    Módulos pedidos antes de tener código asignado en Flexxus.</p>
    """, unsafe_allow_html=True)

    # Formulario nuevo
    with st.expander("➕ Agregar nuevo Ghost SKU", expanded=False):
        c1, c2, c3 = st.columns([3, 1.5, 1])
        with c1: modelo = st.text_input("Descripción *", placeholder="Ej: Samsung Galaxy A06 módulo OLED", key="gs_mod")
        with c2: prov   = st.selectbox("Proveedor", ["MECÁNICO", "FR"], key="gs_prov")
        with c3: qty    = st.number_input("Cant. estimada", min_value=0, value=0, step=10, key="gs_qty")
        notas = st.text_area("Notas", height=60, placeholder="Info adicional...", key="gs_notas")
        if st.button("👻 Crear Ghost SKU", type="primary", key="gs_crear"):
            if not modelo.strip():
                st.error("Ingresá la descripción del modelo.")
            else:
                gid = crear_ghost_sku(modelo, prov, float(qty), notas)
                st.success(f"✅ Ghost SKU creado (ID {gid})")
                st.rerun()

    st.divider()

    filtro_estado = st.selectbox("Estado", ["PENDIENTE", "VINCULADO", "CANCELADO", "Todos"], key="gs_filtro")
    estado_q = None if filtro_estado == "Todos" else filtro_estado
    df_g = get_ghost_skus(estado=estado_q)

    if df_g.empty:
        st.info(f"No hay Ghost SKUs en estado {filtro_estado}.")
        return

    st.caption(f"{len(df_g)} Ghost SKU(s)")

    for _, row in df_g.iterrows():
        gid   = int(row["id"])
        mod   = str(row["modelo_descripcion"])
        prov  = str(row["proveedor_tipo"])
        qty   = int(row.get("cantidad_estimada", 0) or 0)
        est   = str(row["estado"])
        notas = str(row.get("notas","") or "")
        vinc  = str(row.get("codigo_vinculado","") or "")
        fecha = str(row.get("fecha_creacion",""))[:10]
        emoji = {"PENDIENTE":"🟡","VINCULADO":"🟢","CANCELADO":"⛔"}.get(est,"⚪")

        with st.expander(f"{emoji} **ID {gid}** — {mod[:60]} | {prov} | {qty} u", expanded=(est=="PENDIENTE")):
            c1, c2 = st.columns([3,2])
            with c1:
                st.markdown(f"**Estado:** {est} | **Proveedor:** {prov} | **Fecha:** {fecha}")
                if notas: st.markdown(f"**Notas:** {notas}")
                if vinc:  st.markdown(f"**Código vinculado:** `{vinc}`")
            with c2:
                if est == "PENDIENTE":
                    nuevo_cod = st.text_input("Vincular código ERP", key=f"gs_cod_{gid}", placeholder="Ej: MSAMA06.")
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button("🔗 Vincular", key=f"gs_link_{gid}"):
                            if nuevo_cod.strip():
                                vincular_ghost_sku(gid, nuevo_cod.strip())
                                st.success("✅ Vinculado")
                                st.rerun()
                            else:
                                st.warning("Ingresá el código.")
                    with cb:
                        if st.button("❌ Cancelar", key=f"gs_cancel_{gid}"):
                            actualizar_ghost_sku(gid, estado="CANCELADO")
                            st.rerun()
