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
            # Detectar archivos duplicados en la misma carga
            nombres_vistos = {}
            for f in uploaded:
                nombre_limpio = f.name.rsplit("_", 2)[0]  # ignorar timestamp al final
                if nombre_limpio in nombres_vistos:
                    st.warning(
                        f"⚠️ **Posible duplicado detectado:** `{f.name}` parece ser el mismo "
                        f"archivo que `{nombres_vistos[nombre_limpio]}`. "
                        f"Solo se procesará una vez."
                    )
                    continue
                nombres_vistos[nombre_limpio] = f.name
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
            st.dataframe(df_log, width="stretch", hide_index=True)
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
                # Registrar en file tracker
                try:
                    from database import update_archivo_tracker
                    deposito = resultado.metadata.get("deposito", "") if resultado.metadata else ""
                    update_archivo_tracker(tipo, deposito, resultado.filas_ok, f.name)
                except Exception:
                    pass
                # Notificación Telegram
                try:
                    from utils.helpers import notificar_telegram, notificar_picos_demanda
                    import threading
                    _msg = (f"📥 *Archivo cargado*\n`{f.name}`\n"
                            f"✅ {resultado.filas_ok} filas importadas")
                    notificar_telegram(_msg)
                    threading.Thread(target=notificar_picos_demanda, daemon=True).start()
                except Exception:
                    pass
                # Backup automático
                try:
                    from pages.sistema import _llamar_backup_auto
                    _llamar_backup_auto()
                except Exception:
                    pass
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
    """Panel dinámico de salud de datos — lee el archivo_tracker de la DB."""
    from database import get_file_health

    slots = get_file_health()
    total = len(slots)
    ok    = sum(1 for s in slots if s["estado"] == "ok")
    pct   = int(ok / total * 100) if total else 0

    # ── Barra de progreso ──
    color_barra = "#34C759" if pct >= 80 else ("#FF9F0A" if pct >= 40 else "#FF3B30")
    st.markdown(
        f"""<div style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-size:13px;font-weight:600">📁 Salud de datos</span>
                <span style="font-size:13px;color:{color_barra};font-weight:700">{ok}/{total} archivos al día</span>
            </div>
            <div style="background:var(--nx-bg2,#2c2c2e);border-radius:4px;height:6px">
                <div style="width:{pct}%;background:{color_barra};height:6px;border-radius:4px;transition:width .3s"></div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Tabla de slots ──
    COLORES = {
        "ok":      ("#34C759", "🟢", "Al día"),
        "stale":   ("#FF9F0A", "🟡", "Actualizar pronto"),
        "critico": ("#FF3B30", "🔴", "Desactualizado"),
        "nunca":   ("#8E8E93", "⚫", "Nunca cargado"),
    }

    html = '<div style="font-size:12px">'
    for s in slots:
        color, dot, estado_label = COLORES.get(s["estado"], ("#8E8E93", "⚫", "?"))
        badge_critico = (
            '<span style="background:rgba(255,59,48,.15);color:#FF3B30;font-size:10px;'
            'padding:1px 6px;border-radius:8px;margin-left:6px">CRÍTICO</span>'
            if s["critico"] else ""
        )
        if s["dias_sin_cargar"] is not None:
            dias_txt = f"hace {s['dias_sin_cargar']}d" if s["dias_sin_cargar"] > 0 else "hoy"
        else:
            dias_txt = "—"

        filas_txt = f"{s['filas']:,} filas" if s["filas"] else ""

        html += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:7px 0;
                    border-bottom:1px solid var(--nx-border,#3a3a3c)">
            <span style="font-size:18px;min-width:24px;text-align:center">{s['icono']}</span>
            <div style="flex:1;min-width:0">
                <b style="color:var(--nx-text,#fff)">{s['label']}</b>{badge_critico}
                <div style="font-size:10px;color:var(--nx-text3,#888);margin-top:1px">{filas_txt}</div>
            </div>
            <div style="text-align:right;white-space:nowrap">
                <div style="color:{color};font-size:12px;font-weight:600">{dot} {dias_txt}</div>
                <div style="font-size:10px;color:var(--nx-text3,#888)">{estado_label}</div>
            </div>
        </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
