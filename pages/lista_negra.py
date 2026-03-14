"""
ROKER NEXUS — Lista Negra
Modelos que no se vuelven a pedir, con modos INVISIBLE/GRISADO/SOLO_COMPRAS.
"""
import streamlit as st
from database import (
    get_lista_negra_full, agregar_lista_negra_full,
    actualizar_lista_negra_item, eliminar_lista_negra_item,
    get_config, set_config
)


MODOS = ["SOLO_COMPRAS", "GRISADO", "INVISIBLE"]
MODOS_DESC = {
    "SOLO_COMPRAS": "⚠️ Oculto en compras — visible en inventario",
    "GRISADO":      "🔲 Visible con badge 🚫 — oculto en compras",
    "INVISIBLE":    "🚫 Desaparece de todo el sistema",
}


def render():
    st.markdown("""
    <h2 style="margin:0 0 4px;font-size:22px;font-weight:700">🚫 Lista Negra</h2>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:8px">
    Modelos que no se vuelven a pedir.</p>
    """, unsafe_allow_html=True)

    # Config global
    with st.expander("⚙️ Configuración global", expanded=False):
        modo_global = get_config("lista_negra_modo_global") or "SOLO_COMPRAS"
        nuevo_modo = st.selectbox(
            "Modo por defecto", MODOS,
            index=MODOS.index(modo_global) if modo_global in MODOS else 0,
            key="ln_modo_global"
        )
        st.caption(MODOS_DESC.get(nuevo_modo, ""))
        if st.button("💾 Guardar modo global", key="ln_save_global"):
            set_config("lista_negra_modo_global", nuevo_modo)
            st.success(f"✅ Modo global: {nuevo_modo}")

    st.divider()

    # Agregar ítem
    with st.expander("➕ Agregar a lista negra", expanded=False):
        c1, c2 = st.columns([3,1])
        with c1:
            nuevo_art = st.text_input("Artículo / descripción *", key="ln_art",
                                       placeholder="Ej: Samsung A22 mecánico")
            nuevo_cod = st.text_input("Código ERP (opcional)", key="ln_cod",
                                       placeholder="Ej: 2401251853")
        with c2:
            nuevo_modo_item = st.selectbox("Modo", ["(usar global)"] + MODOS, key="ln_modo_item")
            nuevo_motivo    = st.text_input("Motivo", key="ln_motivo",
                                             placeholder="Descontinuado, falla frecuente...")
        if st.button("🚫 Agregar", type="primary", key="ln_agregar"):
            if not nuevo_art.strip():
                st.error("Ingresá la descripción del artículo.")
            else:
                modo_f = nuevo_modo_item if nuevo_modo_item != "(usar global)" else ""
                agregar_lista_negra_full(nuevo_art, nuevo_cod, nuevo_motivo, modo_f)
                st.success("✅ Agregado a lista negra")
                st.rerun()

    st.divider()

    solo_activos = st.checkbox("Solo activos", value=True, key="ln_solo_activos")
    df_ln = get_lista_negra_full(solo_activos=solo_activos)

    if df_ln.empty:
        st.info("Lista negra vacía.")
        return

    st.caption(f"{len(df_ln)} ítem(s)")

    for _, row in df_ln.iterrows():
        iid    = int(row["id"])
        art    = str(row.get("descripcion",""))
        cod    = str(row.get("codigo","") or "")
        notas  = str(row.get("notas","") or "")
        activo = int(row.get("en_lista_negra", 1) or 1)
        fecha  = str(row.get("fecha",""))[:10] if "fecha" in row.index else ""
        ico    = "🟢" if activo else "⛔"

        with st.expander(f"{ico} **{art}** {('`'+cod+'`') if cod else ''}", expanded=False):
            c1, c2 = st.columns([3,1])
            with c1:
                new_notas = st.text_input("Motivo/notas", value=notas, key=f"ln_n_{iid}")
            with c2:
                if st.button("🔄 Activar/Pausar", key=f"ln_toggle_{iid}"):
                    actualizar_lista_negra_item(iid, activo=(0 if activo else 1))
                    st.rerun()
                if st.button("💾 Guardar", key=f"ln_save_{iid}"):
                    actualizar_lista_negra_item(iid, motivo=new_notas)
                    st.success("✅")
                if st.button("🗑️ Eliminar", key=f"ln_del_{iid}"):
                    eliminar_lista_negra_item(iid)
                    st.rerun()
