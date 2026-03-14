"""ROKER NEXUS — Lista Negra"""
import streamlit as st
from database import query_to_df, execute_query, get_config, set_config

def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700">🚫 Lista Negra</h1>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
    Modelos que no se vuelven a pedir.</p>
    """, unsafe_allow_html=True)

    MODOS = ["SOLO_COMPRAS","GRISADO","INVISIBLE"]
    MODOS_DESC = {
        "SOLO_COMPRAS": "⚠️ Oculto en compras, visible en inventario",
        "GRISADO":      "🔲 Visible con badge 🚫, oculto en compras",
        "INVISIBLE":    "🚫 Desaparece de todo el sistema",
    }

    with st.expander("⚙️ Modo global", expanded=False):
        mg = get_config("lista_negra_modo_global") or "SOLO_COMPRAS"
        nm = st.selectbox("Modo por defecto", MODOS, index=MODOS.index(mg) if mg in MODOS else 0, key="ln_mg")
        st.caption(MODOS_DESC.get(nm,""))
        if st.button("💾 Guardar", key="ln_mg_s"): set_config("lista_negra_modo_global", nm); st.success("✓")

    st.divider()
    with st.expander("➕ Agregar a lista negra", expanded=False):
        c1, c2 = st.columns([3,1])
        with c1:
            art  = st.text_input("Artículo *", key="ln_art", placeholder="Samsung A22 mecánico")
            cod  = st.text_input("Código ERP (opcional)", key="ln_cod")
        with c2:
            modo_i  = st.selectbox("Modo", ["(usar global)"]+MODOS, key="ln_modi")
            motivo  = st.text_input("Motivo", key="ln_mot")
        if st.button("🚫 Agregar", type="primary", key="ln_add"):
            if not art.strip(): st.error("Ingresá la descripción.")
            else:
                execute_query("INSERT INTO lista_negra (codigo, descripcion, notas) VALUES(?,?,?)",
                    (cod.strip(), art.strip(), motivo.strip()), fetch=False)
                st.success("✅ Agregado"); st.rerun()

    st.divider()
    solo_act = st.checkbox("Solo activos", True, key="ln_sa")
    w = "WHERE en_lista_negra=1" if solo_act else ""
    df_ln = query_to_df(f"SELECT id, codigo, descripcion, notas, en_lista_negra FROM lista_negra {w} ORDER BY descripcion")
    if df_ln.empty: st.info("Lista negra vacía."); return
    st.caption(f"{len(df_ln)} ítem(s)")
    for _, row in df_ln.iterrows():
        iid = int(row["id"]); art = str(row.get("descripcion",""))
        cod = str(row.get("codigo","") or ""); notas = str(row.get("notas","") or "")
        act = int(row.get("en_lista_negra",1) or 1)
        ico = "🟢" if act else "⛔"
        with st.expander(f"{ico} {art} {('`'+cod+'`') if cod else ''}", expanded=False):
            c1, c2 = st.columns([3,1])
            with c1: new_n = st.text_input("Notas", value=notas, key=f"ln_n_{iid}")
            with c2:
                if st.button("🔄 Activar/Pausar", key=f"ln_t_{iid}"):
                    execute_query("UPDATE lista_negra SET en_lista_negra=? WHERE id=?", (0 if act else 1, iid), fetch=False); st.rerun()
                if st.button("💾 Guardar", key=f"ln_s_{iid}"):
                    execute_query("UPDATE lista_negra SET notas=? WHERE id=?", (new_n, iid), fetch=False); st.success("✓")
                if st.button("🗑️ Eliminar", key=f"ln_d_{iid}"):
                    execute_query("DELETE FROM lista_negra WHERE id=?", (iid,), fetch=False); st.rerun()
