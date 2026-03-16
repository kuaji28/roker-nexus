"""
ROKER NEXUS — Página: Cargar Archivos
Importación drag & drop con detección automática del tipo de archivo.
"""
import re
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

# ── Guía detallada por tipo de archivo ────────────────────────
# Incluye: cómo configurar en Flexxus, qué filtros aplicar,
# qué nombre tiene el archivo que genera Flexxus,
# cómo renombrarlo antes de subir, y errores comunes.
GUIA_DETALLADA = {
    "stock_sj": {
        "titulo": "📦 Stock SAN JOSE",
        "urgencia": "URGENTE · Semanal",
        "color": "#FF9F0A",
        "flexxus_ruta": "Stock → Listado General",
        "nombre_genera_flexxus": "Planilla de Stock_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_correcto": "SJ_stock_YYYY-MM-DD.xlsx",
        "nombre_alternativo": "SJ Planilla de Stock_DD-MM-YYYY HH-MM-SS.xlsx",
        "pasos": [
            "1️⃣  Ir a Flexxus: módulo **Stock → Listado General**",
            "2️⃣  En el filtro **Depósito**, seleccionar solo: **SAN JOSE**",
            "3️⃣  No aplicar filtro de fecha (muestra stock actual)",
            "4️⃣  No filtrar por rubro — descargar **TODOS los artículos** del depósito",
            "5️⃣  Clic en Exportar / Excel → guarda el archivo",
            "6️⃣  **Renombrar** el archivo a: `SJ_stock_YYYY-MM-DD.xlsx`",
            "   ✅ Ejemplo: `SJ_stock_2026-03-15.xlsx`",
            "   ⚡ Atajo: agregar `SJ ` al INICIO del nombre original también funciona",
        ],
        "errores_comunes": [
            "❌ No filtrar por depósito → el sistema no sabe de qué depósito es",
            "❌ No renombrar → el sistema no puede identificar el depósito",
            "❌ Filtrar por rubro MODULOS → se pierden todos los demás artículos",
        ],
    },
    "stock_lar": {
        "titulo": "📦 Stock LARREA",
        "urgencia": "URGENTE · Semanal",
        "color": "#FF9F0A",
        "flexxus_ruta": "Stock → Listado General",
        "nombre_genera_flexxus": "Planilla de Stock_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_correcto": "LAR_stock_YYYY-MM-DD.xlsx",
        "nombre_alternativo": "LAR Planilla de Stock_DD-MM-YYYY HH-MM-SS.xlsx",
        "pasos": [
            "1️⃣  Ir a Flexxus: módulo **Stock → Listado General**",
            "2️⃣  En el filtro **Depósito**, seleccionar solo: **LARREA NUEVO** (o ES LOCAL)",
            "3️⃣  No aplicar filtro de fecha — es stock actual",
            "4️⃣  Sin filtro de rubro — descargar TODOS los artículos",
            "5️⃣  Exportar a Excel → guarda el archivo",
            "6️⃣  **Renombrar** a: `LAR_stock_YYYY-MM-DD.xlsx`",
            "   ✅ Ejemplo: `LAR_stock_2026-03-15.xlsx`",
        ],
        "errores_comunes": [
            "❌ Confundir LARREA con ES LOCAL — son el mismo local, pero verificar cuál es en Flexxus",
            "❌ No renombrar → sistema lo procesa como San José por defecto",
        ],
    },
    "stock_eslocal": {
        "titulo": "📦 Stock ES LOCAL",
        "urgencia": "URGENTE · Semanal",
        "color": "#FF9F0A",
        "flexxus_ruta": "Stock → Listado General",
        "nombre_genera_flexxus": "Planilla de Stock_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_correcto": "ESLOCAL_stock_YYYY-MM-DD.xlsx",
        "nombre_alternativo": "LAR Planilla de Stock_DD-MM-YYYY HH-MM-SS.xlsx",
        "pasos": [
            "1️⃣  Ir a Flexxus: módulo **Stock → Listado General**",
            "2️⃣  En el filtro **Depósito**, seleccionar: **ES LOCAL** (SARMIENTO / segundo local)",
            "3️⃣  Sin filtro de fecha — stock actual",
            "4️⃣  Sin filtro de rubro — todos los artículos",
            "5️⃣  Exportar a Excel",
            "6️⃣  **Renombrar** a: `ESLOCAL_stock_YYYY-MM-DD.xlsx`",
            "   ⚡ Alternativa: `LAR Planilla de Stock...` (el sistema lo procesa igual que Larrea)",
        ],
        "errores_comunes": [
            "❌ Subir sin renombrar → el sistema no distingue de SJ o LAR",
        ],
    },
    "optimizacion": {
        "titulo": "📊 Optimización de Stock",
        "urgencia": "Mensual",
        "color": "#0A84FF",
        "flexxus_ruta": "Stock → Optimización de Stock",
        "nombre_genera_flexxus": "Optimizacin de Stock_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_correcto": "Optimizacin de Stock_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_alternativo": "— (no necesita renombrado)",
        "pasos": [
            "1️⃣  Ir a Flexxus: módulo **Stock → Optimización de Stock**",
            "2️⃣  **Super Rubro:** MODULOS (seleccionar solo módulos)",
            "3️⃣  **Período de análisis:** 6 meses",
            "4️⃣  **Demanda promedio:** 30 días",
            "5️⃣  Sin filtro de depósito (analiza stock total combinado)",
            "6️⃣  Ejecutar → Exportar a Excel",
            "   ✅ El nombre que genera Flexxus ya es reconocido automáticamente",
            "   ⚠️ Atención: Flexxus escribe 'Optimizacin' (sin 'ó') — es normal",
        ],
        "errores_comunes": [
            "❌ Cambiar período a menos de 3 meses → demanda subestimada",
            "❌ No seleccionar Super Rubro MODULOS → archivo muy grande y lento",
            "❌ Renombrar el archivo → el sistema no lo va a reconocer",
        ],
    },
    "lista_precios": {
        "titulo": "💰 Lista de Precios",
        "urgencia": "Al cambiar precios",
        "color": "#32D74B",
        "flexxus_ruta": "Ventas → Lista de Precios Editable",
        "nombre_genera_flexxus": "Lista de Precios_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_correcto": "Lista de Precios_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_alternativo": "— (no necesita renombrado)",
        "pasos": [
            "1️⃣  Ir a Flexxus: **Ventas → Lista de Precios Editable**",
            "2️⃣  Sin filtro de artículo — exportar TODA la lista",
            "3️⃣  **Incluir todas las listas:** 1 (mayorista), 2, 3, 4 (ML), 5",
            "4️⃣  **Moneda:** USD (dólares) — NO pesos",
            "5️⃣  Incluir columna **P.Comp** (precio de compra)",
            "6️⃣  Exportar a Excel",
            "   ✅ El nombre que genera Flexxus ya es reconocido automáticamente",
        ],
        "errores_comunes": [
            "❌ Exportar en ARS en vez de USD → todos los precios van a estar mal",
            "❌ Exportar solo lista 1 → se pierde Lista 4 (MercadoLibre)",
            "❌ No incluir P.Comp → sin costo no se calculan márgenes",
        ],
    },
    "ventas": {
        "titulo": "📈 Ventas por Artículo",
        "urgencia": "Mensual / al cierre",
        "color": "#BF5AF2",
        "flexxus_ruta": "Informes → Ventas por Artículo (Resumida)",
        "nombre_genera_flexxus": "...Resumida_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_correcto": "...Resumida_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_alternativo": "— (no necesita renombrado)",
        "pasos": [
            "1️⃣  Ir a Flexxus: **Informes → Ventas por Artículo**",
            "2️⃣  Seleccionar la vista **'Resumida'** (no la detallada)",
            "3️⃣  **Rango de fechas:** últimos 30-90 días (ej: 01/01/2026 al 15/03/2026)",
            "4️⃣  Sin filtro de artículo — exportar TODAS las ventas",
            "5️⃣  Sin filtro de depósito — ventas de todos los locales",
            "6️⃣  Exportar a Excel",
            "   ✅ El nombre con 'Resumida' es reconocido automáticamente",
            "   📅 Para análisis de 6 meses: desde el 01/10/2025",
        ],
        "errores_comunes": [
            "❌ Usar la vista detallada (sin 'Resumida') → el sistema no la reconoce",
            "❌ Filtrar por un solo depósito → se pierden ventas de Larrea o SAN JOSE",
            "❌ Rango muy corto (7 días) → demanda promedio poco representativa",
        ],
    },
    "compras": {
        "titulo": "🛍️ Compras por Marca",
        "urgencia": "Mensual",
        "color": "#BF5AF2",
        "flexxus_ruta": "Informes → Compras por Marca",
        "nombre_genera_flexxus": "...por Marca_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_correcto": "...por Marca_DD-MM-YYYY HH-MM-SS.xlsx",
        "nombre_alternativo": "— (no necesita renombrado)",
        "pasos": [
            "1️⃣  Ir a Flexxus: **Informes → Compras → Por Marca** (o similar)",
            "2️⃣  **Activar:** Facturas (FA/FB) + Notas de Crédito (NC)",
            "3️⃣  **Activar:** Remitos de Entrada (RE)",
            "4️⃣  Rango de fechas: el mes completo que querés analizar",
            "5️⃣  Sin filtro de marca — todas las marcas",
            "6️⃣  Exportar a Excel",
            "   ✅ El nombre con 'por Marca' es reconocido automáticamente",
            "   ⚠️ NO usar la versión 'Resumida' — ese nombre lo confunde con Ventas",
        ],
        "errores_comunes": [
            "❌ No activar Remitos RE → no aparecen las compras de mercadería",
            "❌ El nombre tiene 'Resumida' → el sistema lo confunde con Ventas",
        ],
    },
    "cotizacion_aitech": {
        "titulo": "🏭 Cotización AI-TECH (FR)",
        "urgencia": "Al recibirla",
        "color": "#0A84FF",
        "flexxus_ruta": "Proveedor externo (archivo que manda FR)",
        "nombre_genera_flexxus": "cotizacion_XXX.xlsx (lo manda el proveedor)",
        "nombre_correcto": "cotizacion_NUMERO.xlsx",
        "nombre_alternativo": "cualquier nombre con 'cotizacion' o 'ai-tech'",
        "pasos": [
            "1️⃣  FR (AI-TECH) manda el archivo Excel por WhatsApp o email",
            "2️⃣  El archivo trae: código, descripción, precio en RMB o USD",
            "3️⃣  Guardar el archivo — NO modificar el contenido",
            "4️⃣  El nombre puede quedar igual (si tiene 'cotizacion' en el nombre)",
            "   ✅ El sistema lo reconoce si el nombre contiene: 'cotizacion', 'ai-tech' o 'ai_tech'",
            "5️⃣  Subir al sistema → carga precios de compra de FR",
            "   ⚠️ Recordar: FR está suspendido temporalmente (solo Mecánico activo)",
        ],
        "errores_comunes": [
            "❌ Modificar el archivo (agregar columnas) → puede romperse la lectura",
            "❌ Nombre sin 'cotizacion' → el sistema no lo reconoce",
        ],
    },
    "mariano": {
        "titulo": "📋 Archivo Mariano (Optimización interna)",
        "urgencia": "Mensual / mes y medio",
        "color": "#32D74B",
        "flexxus_ruta": "Interno — no es de Flexxus directamente",
        "nombre_genera_flexxus": "optimizacion_FECHA.xlsx (lo genera Mariano)",
        "nombre_correcto": "optimizacion_FECHA.xlsx",
        "nombre_alternativo": "cualquier nombre con 'optimizacion' (sin 'stock')",
        "pasos": [
            "1️⃣  Este archivo lo genera Mariano (sub-gerente), no viene de Flexxus directamente",
            "2️⃣  Tiene **múltiples hojas**: Repuestos · PROV 1 FR · Lista de Precios · Stock",
            "3️⃣  El sistema lee todas las hojas automáticamente",
            "4️⃣  El nombre debe tener 'optimizacion' pero NO 'stock' (para no confundirse)",
            "   ✅ Ejemplo válido: `optimizacion_marzo_2026.xlsx`",
        ],
        "errores_comunes": [
            "❌ Subir como si fuera Optimización de Stock de Flexxus → son formatos distintos",
            "❌ El nombre tiene 'stock' → el sistema lo confunde con Planilla de Stock",
        ],
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

    tab_auto, tab_manual, tab_historial, tab_guia = st.tabs([
        "⚡ Carga automática",
        "🗂️ Por tipo de archivo",
        "📋 Historial",
        "📖 Guía de archivos",
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
    with tab_guia:
        _tab_guia()

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


def _tab_guia():
    """
    Tab Guía de archivos:
    - Herramienta renombrador (pegar nombre Flexxus → obtener nombre correcto)
    - Tarjetas expandibles por tipo de archivo con pasos + errores comunes
    """
    # ── Renombrador ────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(10,132,255,.15),rgba(50,215,75,.1));
                border:1px solid rgba(10,132,255,.3);border-radius:12px;padding:16px 20px;margin-bottom:24px">
        <div style="font-size:15px;font-weight:700;color:var(--nx-text);margin-bottom:4px">
            ✏️ Renombrador rápido
        </div>
        <div style="font-size:12px;color:var(--nx-text2)">
            Pegá el nombre que genera Flexxus → el sistema te dice cómo renombrarlo.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_dep, col_nombre = st.columns([1, 2])
    with col_dep:
        deposito_sel = st.selectbox(
            "Depósito",
            options=["SAN JOSE (SJ)", "LARREA (LAR)", "ES LOCAL (ESLOCAL)", "Otro / No aplica"],
            key="guia_dep_sel",
            help="¿Para qué depósito es la Planilla de Stock?"
        )
    with col_nombre:
        nombre_original = st.text_input(
            "Nombre que genera Flexxus",
            placeholder="Ej: Planilla de Stock_15-03-2026 10-22-45.xlsx",
            key="guia_nombre_original",
        )

    if nombre_original.strip():
        nombre_base = nombre_original.strip()
        # Extraer fecha del nombre si tiene el patrón DD-MM-YYYY
        import re
        fecha_iso = None
        m = re.search(r"(\d{2})-(\d{2})-(\d{4})", nombre_base)
        if m:
            d, mo, y = m.group(1), m.group(2), m.group(3)
            fecha_iso = f"{y}-{mo}-{d}"

        fecha_str = fecha_iso or datetime.now().strftime("%Y-%m-%d")
        dep_code_map = {
            "SAN JOSE (SJ)": "SJ",
            "LARREA (LAR)": "LAR",
            "ES LOCAL (ESLOCAL)": "ESLOCAL",
            "Otro / No aplica": None,
        }
        dep_code = dep_code_map.get(deposito_sel)

        # Determinar nombre correcto
        es_planilla_stock = "planilla" in nombre_base.lower() and "stock" in nombre_base.lower()
        es_optimizacion = "optimizac" in nombre_base.lower()
        es_ventas = "resumida" in nombre_base.lower()
        es_lista = "lista de precio" in nombre_base.lower()
        es_compras = "por marca" in nombre_base.lower() or "compras" in nombre_base.lower()

        if es_planilla_stock and dep_code:
            nombre_correcto = f"{dep_code}_stock_{fecha_str}.xlsx"
            nombre_atajo   = f"{dep_code} {nombre_base}"
            color_ok = "#32D74B"
            label_tipo = f"📦 Stock {deposito_sel.split(' (')[0]}"
            necesita_renombrar = True
        elif es_planilla_stock and not dep_code:
            nombre_correcto = "— Seleccioná el depósito arriba →"
            nombre_atajo = None
            color_ok = "#FF9F0A"
            label_tipo = "📦 Planilla de Stock (depósito desconocido)"
            necesita_renombrar = True
        elif es_optimizacion:
            nombre_correcto = nombre_base  # ya es reconocido
            nombre_atajo = None
            color_ok = "#32D74B"
            label_tipo = "📊 Optimización de Stock"
            necesita_renombrar = False
        elif es_ventas:
            nombre_correcto = nombre_base
            nombre_atajo = None
            color_ok = "#32D74B"
            label_tipo = "📈 Ventas por Artículo"
            necesita_renombrar = False
        elif es_lista:
            nombre_correcto = nombre_base
            nombre_atajo = None
            color_ok = "#32D74B"
            label_tipo = "💰 Lista de Precios"
            necesita_renombrar = False
        elif es_compras:
            nombre_correcto = nombre_base
            nombre_atajo = None
            color_ok = "#32D74B"
            label_tipo = "🛍️ Compras por Marca"
            necesita_renombrar = False
        else:
            nombre_correcto = "⚠️ No reconocido — verificá el nombre"
            nombre_atajo = None
            color_ok = "#FF3B30"
            label_tipo = "❓ Tipo desconocido"
            necesita_renombrar = True

        # Resultado visual
        st.markdown(f"""
        <div style="background:var(--nx-surface2,#1c1c1e);border:1px solid {color_ok}33;
                    border-radius:10px;padding:14px 18px;margin-top:8px">
            <div style="font-size:11px;color:var(--nx-text3);margin-bottom:6px">
                {label_tipo}
            </div>
        """, unsafe_allow_html=True)

        if necesita_renombrar and dep_code:
            st.markdown(f"""
            <div style="margin-bottom:6px">
                <span style="font-size:11px;color:var(--nx-text2)">Nombre correcto:</span><br>
                <code style="font-size:14px;color:{color_ok};background:rgba(50,215,75,.1);
                             padding:4px 10px;border-radius:6px;display:inline-block;margin-top:2px">
                    {nombre_correcto}
                </code>
            </div>
            """, unsafe_allow_html=True)
            if nombre_atajo:
                st.markdown(f"""
                <div>
                    <span style="font-size:11px;color:var(--nx-text3)">
                        ⚡ Atajo (también funciona): <code>{nombre_atajo[:60]}{'...' if len(nombre_atajo)>60 else ''}</code>
                    </span>
                </div>
                """, unsafe_allow_html=True)
        elif not necesita_renombrar:
            st.markdown(f"""
            <div>
                <span style="font-size:12px;color:{color_ok}">✅ El nombre ya es correcto, no necesita renombrarse.</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div>
                <span style="font-size:12px;color:{color_ok}">{nombre_correcto}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Selector de categoría ──────────────────────────────────
    st.markdown("""
    <div style="font-size:14px;font-weight:700;color:var(--nx-text);margin-bottom:12px">
        📋 Guía paso a paso por tipo de archivo
    </div>
    """, unsafe_allow_html=True)

    # Agrupar guías por categoría
    GRUPOS_GUIA = {
        "📦 Stock por Depósito": ["stock_sj", "stock_lar", "stock_eslocal"],
        "📊 Análisis y Precios": ["optimizacion", "lista_precios"],
        "📈 Ventas y Compras": ["ventas", "compras"],
        "🏭 Externos": ["cotizacion_aitech", "mariano"],
    }

    for grupo_label, claves in GRUPOS_GUIA.items():
        st.markdown(f"""
        <div style="font-size:12px;font-weight:700;color:var(--nx-text3);
                    text-transform:uppercase;letter-spacing:.06em;
                    margin:16px 0 6px;padding-bottom:4px;
                    border-bottom:1px solid var(--nx-border,#3a3a3c)">
            {grupo_label}
        </div>
        """, unsafe_allow_html=True)

        for clave in claves:
            guia = GUIA_DETALLADA.get(clave)
            if not guia:
                continue

            color = guia.get("color", "#8E8E93")
            with st.expander(f"{guia['titulo']}  —  {guia['urgencia']}"):

                # Nombre archivos
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"""
                    <div style="background:var(--nx-surface2);border-radius:8px;padding:10px 12px">
                        <div style="font-size:10px;color:var(--nx-text3);margin-bottom:4px;text-transform:uppercase">
                            📁 Ruta Flexxus
                        </div>
                        <code style="font-size:12px;color:var(--nx-accent)">{guia['flexxus_ruta']}</code>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    st.markdown(f"""
                    <div style="background:var(--nx-surface2);border-radius:8px;padding:10px 12px">
                        <div style="font-size:10px;color:var(--nx-text3);margin-bottom:4px;text-transform:uppercase">
                            💾 Flexxus genera
                        </div>
                        <code style="font-size:12px;color:var(--nx-text2)">{guia['nombre_genera_flexxus']}</code>
                    </div>
                    """, unsafe_allow_html=True)

                # Nombre correcto con badge color
                nombre_c = guia["nombre_correcto"]
                no_renombrar = nombre_c == guia["nombre_genera_flexxus"] or "no necesita" in guia.get("nombre_alternativo","").lower()
                badge_color = "#32D74B" if no_renombrar else color
                badge_text  = "✅ Sin renombrar" if no_renombrar else "✏️ Renombrar a:"
                st.markdown(f"""
                <div style="background:rgba(50,215,75,.08);border:1px solid {badge_color}44;
                            border-radius:8px;padding:8px 12px;margin:8px 0">
                    <span style="font-size:11px;color:var(--nx-text3)">{badge_text} </span>
                    <code style="font-size:13px;color:{badge_color}">{nombre_c}</code>
                    {"<br><span style='font-size:10px;color:var(--nx-text3)'>⚡ Alternativa: " + guia['nombre_alternativo'] + "</span>" if guia.get('nombre_alternativo') and "no necesita" not in guia['nombre_alternativo'].lower() and guia['nombre_alternativo'] != "— (no necesita renombrado)" else ""}
                </div>
                """, unsafe_allow_html=True)

                # Pasos
                st.markdown("<div style='font-size:12px;font-weight:600;color:var(--nx-text);margin:10px 0 6px'>Pasos:</div>", unsafe_allow_html=True)
                pasos_html = ""
                for paso in guia["pasos"]:
                    # Negrita para texto entre **
                    paso_fmt = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", paso)
                    # backtick code
                    paso_fmt = re.sub(r"`(.+?)`", r"<code>\1</code>", paso_fmt)
                    pasos_html += f"<div style='padding:3px 0;color:var(--nx-text2);line-height:1.5'>{paso_fmt}</div>"
                st.markdown(f"<div style='font-size:12px'>{pasos_html}</div>", unsafe_allow_html=True)

                # Errores comunes
                if guia.get("errores_comunes"):
                    st.markdown("<div style='font-size:12px;font-weight:600;color:#FF3B30;margin:10px 0 4px'>⚠️ Errores comunes:</div>", unsafe_allow_html=True)
                    err_html = ""
                    for err in guia["errores_comunes"]:
                        err_html += f"<div style='padding:2px 0;color:rgba(255,59,48,.8)'>{err}</div>"
                    st.markdown(f"<div style='font-size:12px;background:rgba(255,59,48,.06);border-radius:6px;padding:8px 10px'>{err_html}</div>", unsafe_allow_html=True)


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
                st.warning("⚠️ Tipo no reconocido")

        if not tipo:
            # Ofrecer selección manual de tipo + depósito
            st.markdown(f"""
            <div style="background:rgba(255,159,10,.1);border:1px solid rgba(255,159,10,.3);
                        border-radius:8px;padding:12px 16px;margin:4px 0 8px">
                <div style="font-size:12px;font-weight:600;color:#FF9F0A;margin-bottom:6px">
                    ❓ No se pudo detectar el tipo de archivo automáticamente
                </div>
                <div style="font-size:11px;color:var(--nx-text2)">
                    El nombre <code>{f.name}</code> no coincide con ningún patrón conocido.<br>
                    Seleccioná el tipo manualmente para continuar, o renombrá el archivo y volvé a subirlo.
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_forzar_tipo, col_forzar_dep = st.columns([2, 1])
            with col_forzar_tipo:
                tipo_forzado = st.selectbox(
                    "¿Qué tipo de archivo es?",
                    options=[""] + list(INSTRUCCIONES.keys()),
                    format_func=lambda k: (
                        "— Seleccioná el tipo —" if k == ""
                        else f"{INSTRUCCIONES[k]['icono']} {INSTRUCCIONES[k]['titulo']}"
                    ),
                    key=f"forzar_tipo_{f.name}",
                )
            with col_forzar_dep:
                dep_forzado = st.selectbox(
                    "Depósito (si es Stock)",
                    options=["Auto", "SAN JOSE", "LARREA", "ESLOCAL"],
                    key=f"forzar_dep_{f.name}",
                    help="Solo relevante para archivos de stock",
                )

            if tipo_forzado:
                if st.button(f"Importar como {INSTRUCCIONES[tipo_forzado]['titulo']}", key=f"btn_forzar_{f.name}"):
                    # Si es stock, renombrar internamente con prefijo de depósito
                    if tipo_forzado == "stock" and dep_forzado != "Auto":
                        import io
                        prefixed_name = f"{dep_forzado} {f.name}"
                        # Crear objeto compatible con el importador
                        class _FakeFile:
                            def __init__(self, orig, new_name):
                                self._orig = orig
                                self.name = new_name
                            def read(self): return self._orig.read()
                            def seek(self, *a): return self._orig.seek(*a)
                            def getvalue(self): return self._orig.getvalue()
                        f_wrapped = _FakeFile(f, prefixed_name)
                        _procesar_archivo(f_wrapped, forzar_tipo=tipo_forzado)
                    else:
                        _procesar_archivo(f, forzar_tipo=tipo_forzado)
            else:
                st.caption("💡 También podés ir a la pestaña **📖 Guía de archivos** para saber cómo renombrarlo.")
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
