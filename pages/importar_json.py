"""importar_json.py - Carga masiva desde manifest JSON (Nexus Push Data)"""
import streamlit as st
import json
import requests

def render():
    st.title("Carga Masiva JSON -> Supabase")
    st.warning("Pagina de mantenimiento - uso interno solamente")

    uploaded = st.file_uploader(
        "Selecciona nexus_push_data.json",
        type=["json"],
    )

    if not uploaded:
        st.info("Subi el archivo nexus_push_data.json para iniciar la carga.")
        return

    st.write(f"Archivo: **{uploaded.name}** ({uploaded.size / 1e6:.1f} MB)")

    if not st.button("Iniciar carga a Supabase", type="primary"):
        return

    with st.spinner("Leyendo manifest..."):
        try:
            manifest = json.loads(uploaded.read().decode("utf-8"))
        except Exception as e:
            st.error(f"Error leyendo JSON: {e}")
            return

    total_batches = manifest.get("batch_count", 0)
    total_rows    = manifest.get("total_rows", 0)
    batches       = manifest.get("batches", [])
    supa_url      = manifest.get("supa_url", "")
    supa_key      = manifest.get("supa_key", "")

    st.write(f"Cargando **{total_batches} batches** / **{total_rows:,} filas**")

    headers = {
        "apikey":        supa_key,
        "Authorization": f"Bearer {supa_key}",
        "Content-Type":  "application/json",
    }

    progress = st.progress(0.0)
    status   = st.empty()
    pushed   = 0
    errors   = 0

    for i, batch in enumerate(batches):
        table      = batch["table"]
        resolution = batch["resolution"]
        rows       = batch["rows"]

        h = {**headers, "Prefer": f"return=minimal,resolution={resolution}"}
        try:
            r = requests.post(
                f"{supa_url}/rest/v1/{table}",
                headers=h,
                data=json.dumps(rows, default=str),
                timeout=60,
            )
            if 200 <= r.status_code < 300:
                pushed += len(rows)
            else:
                errors += 1
                if errors <= 5:
                    st.warning(f"Batch {i+1} HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            errors += 1
            if errors <= 5:
                st.warning(f"Batch {i+1} error: {e}")

        if i % 10 == 0 or i == len(batches) - 1:
            pct = (i + 1) / len(batches)
            progress.progress(pct)
            status.write(f"**{i+1}/{len(batches)}** batches | **{pushed:,}** filas OK | {errors} errores")

    if errors == 0:
        st.success(f"Carga completa: {pushed:,} filas en {len(batches)} batches")
    else:
        st.warning(f"Completado con {errors} errores: {pushed:,}/{total_rows:,} filas")

render()
