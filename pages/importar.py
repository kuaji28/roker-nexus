"""
ROKER NEXUS — Página: Cargar Archivos
Importación drag & drop con detección automática del tipo de archivo.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from importers import importar_archivo, IMPORTADORES
from utils.helpers import detectar_tipo_flexxus, fmt_num


# Instrucciones por tipo de archivo
INSTRUCCIONES = {
    "optimizacion": {
        "titulo": "Optimización de Stock",
        "modulo": "Stock → Optimización de Stock",
        "config": "Super Rubro: MODULOS · Período: 6 meses · Dem.prom: 30 días",
        "frecuencia": "📅 Mensual",
        "icono": "📊",
        "color": "blue",
    },
    "lista_precios": {
        "titulo": "Lista de Precios",
        "modulo": "Ventas → Lista de Precios Editable",
        "config": "Exportar todas las listas (1 a 5) en USD",
        "frecuencia": "📅 Al cambiar precios",
        "icono": "💰",
        "color": "green",
    },
    "stock": {
        "titulo": "Stock por Depósito",
        "modulo": "Stock → Listado General",
        "config": "⚠️ Exportar 3 veces: SAN JOSE · LARREA NUEVO · ES LOCAL",
        "frecuencia": "📅 Semanal o ante quiebre",
        "icono": "📦",
        "color": "amber",
    },
    "ventas": {
        "titulo": "Ventas por Artículo",
        "modulo": "Informes → Ventas por Artículo",
        "config": "Archivo lleva 'Resumida' en el nombre",
        "frecuencia": "📅 Mensual / al cierre",
        "icono": "📈",
        "color": "purple",
    },
    "compras": {
        "titulo": "Compras por Marca",
        "modulo": "Informes → Compras por Marca",
        "config": "Activar Facturas y NC + Remitos RE · Sin 'Resumida' en el nombre",
        "frecuencia": "📅 Mensual",
        "icono": "🛍️",
        "color": "purple",
    },
    "cotizacion_aitech": {
        "titulo": "Cotización AI-TECH",
        "modulo": "Proveedor directo",
        "config": "Archivo Excel de cotización con invoice number",
        "frecuencia": "📅 Al recibir cotización",
        "icono": "🏭",
        "color": "blue",
    },
    "mariano": {
        "titulo": "Archivo de Mariano",
        "modulo": "Interno (optimización mensual)",
        "config": "Multi-hoja: Repuestos · PROV 1 FR · Lista de Precios · Stock",
        "frecuencia": "📅 Mensual / mes y medio",
        "icono": "📋",
        "color": "green",
    },
}


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        📥 Cargar Archivos
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:24px">
        El sistema detecta automáticamente el tipo de archivo. Solo arrastrá y soltá.
    </p>
    """, unsafe_allow_html=True)

    tab_auto, tab_manual, tab_historial = st.tabs([
        "⚡ Carga automática",
        "🗂️ Por tipo de archivo",
        "📋 Historial"
    ])

    # ── Tab 1: Carga automática ───────────────────────────────
    with tab_auto:
        st.markdown("### Arrastrá uno o varios archivos")
        st.markdown(
            "<p style='color:var(--nx-text2);font-size:13px;margin-bottom:16px'>"
            "El sistema detecta si es de Flexxus, AI-TECH o Mariano automáticamente."
            "</p>",
            unsafe_allow_html=True
        )

        uploaded = st.file_uploader(
            "Soltá tus archivos acá",
            type=["xls", "xlsx"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="uploader_auto"
        )

        if uploaded:
            st.markdown("---")
            for f in uploaded:
                _procesar_archivo(f)

        # Checklist de archivos necesarios
        with st.expander("📋 ¿Qué archivos necesito cargar?"):
            _checklist_archivos()

    # ── Tab 2: Por tipo ───────────────────────────────────────
    with tab_manual:
        tipo_sel = st.selectbox(
            "Seleccioná el tipo de archivo",
            options=list(INSTRUCCIONES.keys()),
            format_func=lambda k: f"{INSTRUCCIONES[k]['icono']} {INSTRUCCIONES[k]['titulo']}",
            key="sel_tipo"
        )

        info = INSTRUCCIONES[tipo_sel]
        col_info, col_upload = st.columns([1, 1])

        with col_info:
            color_map = {
                "blue": "var(--nx-accent)",
                "green": "var(--nx-green)",
                "amber": "var(--nx-amber)",
                "purple": "var(--nx-purple)",
            }
            border_color = color_map.get(info["color"], "var(--nx-accent)")
            st.markdown(f"""
            <div class="nx-card" style="border-left: 3px solid {border_color}">
                <div style="font-size:13px;font-weight:600;color:var(--nx-text);margin-bottom:10px">
                    {info['icono']} {info['titulo']}
                </div>
                <div style="font-size:12px;color:var(--nx-text2);margin-bottom:6px">
                    <b>Módulo Flexxus:</b><br>
                    <span style="font-family:monospace;color:var(--nx-accent)">{info['modulo']}</span>
                </div>
                <div style="font-size:12px;color:var(--nx-text2);margin-bottom:6px">
                    <b>Configuración:</b><br>{info['config']}
                </div>
                <div style="font-size:12px;color:var(--nx-text3)">
                    {info['frecuencia']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_upload:
            f_manual = st.file_uploader(
                f"Subir {info['titulo']}",
                type=["xls", "xlsx"],
                key=f"upload_{tipo_sel}"
            )
            if f_manual:
                _procesar_archivo(f_manual, forzar_tipo=tipo_sel)

    # ── Tab 3: Historial ──────────────────────────────────────
    with tab_historial:
        from database import query_to_df
        df_log = query_to_df("""
            SELECT
                tipo_archivo as "Tipo",
                nombre_archivo as "Archivo",
                filas_importadas as "Filas",
                filas_error as "Errores",
                estado as "Estado",
                importado_en as "Fecha"
            FROM importaciones_log
            ORDER BY importado_en DESC
            LIMIT 50
        """)
        if df_log.empty:
            st.info("No hay importaciones registradas todavía.")
        else:
            st.dataframe(df_log, use_container_width=True, hide_index=True)
            st.caption(f"Últimas 50 importaciones. Total: {len(df_log)}")


def _procesar_archivo(f, forzar_tipo: str = None):
    """Procesa un archivo subido y muestra el resultado."""
    nombre = f.name

    # Detectar tipo
    tipo = forzar_tipo or detectar_tipo_flexxus(nombre)

    with st.container():
        col_icon, col_info, col_status = st.columns([1, 8, 3])

        with col_icon:
            icono = INSTRUCCIONES.get(tipo, {}).get("icono", "📄") if tipo else "❓"
            st.markdown(f"<div style='font-size:28px;text-align:center;padding-top:8px'>{icono}</div>",
                        unsafe_allow_html=True)

        with col_info:
            titulo = INSTRUCCIONES.get(tipo, {}).get("titulo", "Tipo desconocido") if tipo else "Tipo no reconocido"
            st.markdown(f"**{nombre}**")
            st.markdown(f"<span style='font-size:12px;color:var(--nx-text2)'>{titulo}</span>",
                        unsafe_allow_html=True)

        with col_status:
            if not tipo:
                st.error("No reconocido")
                st.caption("Verificá el nombre del archivo")
                return

            with st.spinner("Importando..."):
                from importers import get_importador
                imp = get_importador(tipo)
                if imp:
                    resultado = imp.importar(f)
                else:
                    st.error("Sin importador")
                    return

            if resultado.exitoso:
                st.success(f"✅ {fmt_num(resultado.filas_ok)} filas")
                # Mostrar metadata
                if resultado.metadata:
                    _mostrar_metadata(resultado.metadata, tipo)
            else:
                st.error(f"❌ {resultado.mensaje}")

        st.divider()


def _mostrar_metadata(meta: dict, tipo: str):
    """Muestra información relevante post-importación."""
    if tipo == "stock":
        dep = meta.get("deposito", "?")
        sin = meta.get("sin_stock", 0)
        st.markdown(f"""
        <div style="background:var(--nx-surface2);border-radius:6px;padding:8px 12px;
                    font-size:12px;margin-top:8px">
            📍 <b>{dep}</b> · 🔴 {sin} sin stock
        </div>""", unsafe_allow_html=True)

    elif tipo == "optimizacion":
        bajo = meta.get("bajo_minimo", 0)
        costo = meta.get("costo_total_usd", 0)
        st.markdown(f"""
        <div style="background:var(--nx-surface2);border-radius:6px;padding:8px 12px;
                    font-size:12px;margin-top:8px">
            🟡 {bajo} bajo mínimo · Costo reposi. <b>USD {costo:,.0f}</b>
        </div>""", unsafe_allow_html=True)

    elif tipo == "mariano":
        hojas = meta.get("hojas_encontradas", [])
        a_pedir = meta.get("a_pedir", 0)
        st.markdown(f"""
        <div style="background:var(--nx-surface2);border-radius:6px;padding:8px 12px;
                    font-size:12px;margin-top:8px">
            📑 {len(hojas)} hojas · {a_pedir} uds a pedir
        </div>""", unsafe_allow_html=True)


def _checklist_archivos():
    """Muestra qué archivos cargar y con qué frecuencia."""
    items = [
        ("📦", "Stock SAN JOSE",    "Planilla_de_Stock_SANJOSE.XLS",    "Semanal",  True),
        ("📦", "Stock LARREA",      "Planilla_de_Stock_LARREA.XLS",     "Semanal",  True),
        ("📦", "Stock ES LOCAL",    "Planilla_de_Stock_ESLOCAL.XLS",    "Semanal",  True),
        ("📊", "Optimización",      "Optimizacin_de_Stock_FECHA.XLS",   "Mensual",  False),
        ("💰", "Lista de Precios",  "Lista de Precios_FECHA.XLS",       "Al cambiar", False),
        ("📈", "Ventas",            "...Resumida_FECHA.XLS",            "Mensual",  False),
        ("🛍️", "Compras",          "...por Marca_FECHA.XLS",           "Mensual",  False),
        ("🏭", "Cotización AITECH", "cotizacion_XXX.xlsx",              "Al recibirla", False),
        ("📋", "Archivo Mariano",   "optimizacion_FECHA.xlsx",          "Mensual",  False),
    ]
    html = '<div style="font-size:12px">'
    for icono, titulo, archivo, freq, urgente in items:
        border = "var(--nx-red)" if urgente else "var(--nx-border)"
        badge = '<span style="background:rgba(255,82,82,.15);color:var(--nx-red);font-size:10px;padding:1px 6px;border-radius:8px;margin-left:6px">URGENTE</span>' if urgente else ""
        html += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:6px 0;
                    border-bottom:1px solid var(--nx-border)">
            <span style="font-size:16px">{icono}</span>
            <div style="flex:1">
                <b style="color:var(--nx-text)">{titulo}</b>{badge}
                <div style="font-family:monospace;font-size:10px;color:var(--nx-text3)">{archivo}</div>
            </div>
            <span style="font-size:10px;color:var(--nx-text2)">{freq}</span>
        </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
