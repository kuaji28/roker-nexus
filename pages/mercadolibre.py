"""
ROKER NEXUS — Módulo MercadoLibre
Comparador de precios, MLA IDs anclados, editor masivo, búsqueda por tienda.

Tienda FR (AITECH): mercadolibre.com.ar/tienda/aitech
Tienda MECÁNICO:    mercadolibre.com.ar/tienda/mecanico
Lista 1 = precio mayorista USD · Lista 4 = precio ML publicado ARS
"""
import streamlit as st
import pandas as pd
import requests
import re
import time
from io import BytesIO
from datetime import datetime

from database import query_to_df, execute_query, get_config
try:
    from modules.ml_motor import (
        calcular_precio_publicacion, calcular_comision_implicita,
        buscar_con_cache, analizar_competencia, generar_termino,
        get_termino_aprendido, _redondear
    )
    _MOTOR_OK = True
except Exception:
    _MOTOR_OK = False
from utils.helpers import fmt_usd, fmt_num
from utils.matching import tipo_codigo

# ── Constantes ───────────────────────────────────────────────
TIENDA_FR  = "aitech"
TIENDA_MEC = "mecanico"
ML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,application/xhtml+xml,*/*",
    "Accept-Language": "es-AR,es;q=0.9",
}

# ── Asegurar columnas ML en DB ────────────────────────────────
def _init_ml_columns():
    """Agrega columnas MLA si no existen (migración lazy)."""
    cols_nuevas = [
        ("ALTER TABLE articulos ADD COLUMN mla_id_fr TEXT", "mla_id_fr"),
        ("ALTER TABLE articulos ADD COLUMN mla_id_mec TEXT", "mla_id_mec"),
        ("ALTER TABLE articulos ADD COLUMN ml_termino_busqueda TEXT", "ml_termino_busqueda"),
        ("ALTER TABLE articulos ADD COLUMN ml_termino_anclado INTEGER DEFAULT 0", "ml_termino_anclado"),
    ]
    for sql, col in cols_nuevas:
        try:
            execute_query(sql, fetch=False)
        except Exception:
            pass  # Ya existe


def render():
    _init_ml_columns()

    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        🛒 MercadoLibre
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:20px">
        Comparador de precios · Tienda FR (aitech) y Mecánico · Editor masivo
    </p>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "🧮 Calculadora",
        "📊 Precios & Comparador",
        "✏️ Editor Masivo",
        "🆚 Precios Competencia",
        "📥 Importar MLA IDs",
        "📈 Reporte Acumulativo",
    ])

    with tabs[0]:
        _tab_calculadora()
    with tabs[1]:
        _tab_comparador()
    with tabs[2]:
        _tab_editor_masivo()
    with tabs[3]:
        _tab_competencia()
    with tabs[4]:
        _tab_importar_mla()
    with tabs[5]:
        _tab_reporte()


# ─────────────────────────────────────────────────────────────
# TAB 1 — COMPARADOR
# ─────────────────────────────────────────────────────────────
def _tab_comparador():
    tasa = float(get_config("tasa_usd_ars", float) or 1420)

    col1, col2, col3 = st.columns(3)
    filtro_tipo = col1.selectbox("Tipo", ["TODOS", "FR (letra)", "MECÁNICO (número)"])
    filtro_stock = col2.selectbox("Stock", ["Con stock", "Sin stock", "Todos"])
    top_n = col3.selectbox("Mostrar", [20, 50, 100, 200, "Todos"], index=0)

    df = _cargar_tabla_precios(tasa, filtro_tipo, filtro_stock, top_n)

    if df.empty:
        st.info("Sin datos. Cargá primero la Lista de Precios y el Stock desde **Cargar**.")
        return

    # Métricas rápidas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total artículos", len(df))
    con_l4 = int((df.get("lista_4", pd.Series(0)) > 0).sum())
    c2.metric("Con precio ML", con_l4)
    sin_mla = int((df.get("mla_id", pd.Series("")).fillna("") == "").sum())
    c3.metric("Sin MLA vinculado", sin_mla, delta=f"de {len(df)}", delta_color="inverse")
    if "diferencia_pct" in df.columns:
        bajo_precio = int((df["diferencia_pct"] < -5).sum())
        c4.metric("Bajo precio vs ML", bajo_precio, delta_color="inverse")

    st.markdown("---")

    # Tabla principal
    cols_show = [c for c in [
        "codigo", "descripcion", "tipo", "stock",
        "lista_1_usd", "lista_1_ars", "lista_4_ars",
        "mla_id", "ml_termino", "anclado"
    ] if c in df.columns]

    df_show = df[cols_show].copy()

    df_edit = st.data_editor(
        df_show,
        hide_index=True,
        width='stretch',
        column_config={
            "codigo":       st.column_config.TextColumn("Código", disabled=True),
            "descripcion":  st.column_config.TextColumn("Artículo", disabled=True, width="large"),
            "tipo":         st.column_config.TextColumn("Tipo", disabled=True, width="small"),
            "stock":        st.column_config.NumberColumn("Stock", format="%d", disabled=True),
            "lista_1_usd":  st.column_config.NumberColumn("L1 USD", format="$%.2f", disabled=True),
            "lista_1_ars":  st.column_config.NumberColumn("L1 ARS", format="$%,.0f", disabled=True),
            "lista_4_ars":  st.column_config.NumberColumn("L4 ML ARS", format="$%,.0f", disabled=True),
            "mla_id":       st.column_config.TextColumn("MLA ID", help="Ej: MLA1234567"),
            "ml_termino":   st.column_config.TextColumn("Término búsqueda ML", help="Editar para anclar"),
            "anclado":      st.column_config.CheckboxColumn("⚓", help="Término anclado"),
        },
        key="tabla_ml_comparador"
    )

    col_save, col_buscar, _ = st.columns([2, 2, 6])

    with col_save:
        if st.button("💾 Guardar cambios", width='stretch'):
            _guardar_cambios_ml(df_show, df_edit)
            st.success("✅ Guardado")
            st.rerun()

    with col_buscar:
        if st.button("🔍 Buscar en ML (seleccionados)", width='stretch'):
            st.session_state["ml_buscar_trigger"] = True

    # Panel de búsqueda ML
    st.markdown("---")
    st.markdown("### 🔍 Comparar precio en MercadoLibre")

    codigo_buscar = st.selectbox(
        "Elegí un artículo para comparar",
        options=df["codigo"].tolist(),
        format_func=lambda c: f"{c} — {df[df['codigo']==c]['descripcion'].values[0][:50] if not df[df['codigo']==c].empty else ''}"
    )

    if codigo_buscar:
        row = df[df["codigo"] == codigo_buscar]
        if not row.empty:
            row = row.iloc[0]
            tipo = row.get("tipo", "")
            tienda = TIENDA_FR if "FR" in str(tipo) else TIENDA_MEC

            termino = str(row.get("ml_termino") or "")
            if not termino or termino == "nan":
                termino = _generar_termino(str(row.get("descripcion", "")))

            termino_edit = st.text_input(
                "Término de búsqueda (editá si es incorrecto, se guardará ⚓)",
                value=termino,
                key=f"termino_{codigo_buscar}"
            )

            col_b1, col_b2 = st.columns(2)
            buscar_tienda = col_b1.button(f"🏪 Buscar en tienda {tienda}", width='stretch')
            buscar_global = col_b2.button("🌐 Buscar en toda ML", width='stretch')

            if buscar_tienda or buscar_global:
                if termino_edit != termino:
                    # Anclar el nuevo término
                    execute_query(
                        "UPDATE articulos SET ml_termino_busqueda=?, ml_termino_anclado=1 WHERE codigo=?",
                        (termino_edit, codigo_buscar), fetch=False
                    )
                    st.info(f"⚓ Término anclado: *{termino_edit}*")

                seller_id = tienda if buscar_tienda else None
                with st.spinner("Buscando en MercadoLibre..."):
                    resultados = _buscar_ml(termino_edit, seller_id=seller_id)

                if resultados:
                    precio_propio = float(row.get("lista_4_ars") or 0)
                    _mostrar_resultados_ml(resultados, precio_propio, codigo_buscar, tienda)
                else:
                    st.warning("Sin resultados. Intentá con otro término de búsqueda.")


# ─────────────────────────────────────────────────────────────
# TAB 2 — EDITOR MASIVO
# ─────────────────────────────────────────────────────────────
def _tab_editor_masivo():
    tasa = float(get_config("tasa_usd_ars", float) or 1420)
    com_fr  = float(get_config("comision_ml_fr",  float) or 14.0) / 100
    com_mec = float(get_config("comision_ml_mecanico", float) or 13.0) / 100

    st.markdown("### ✏️ Editor masivo de precios ML")
    st.markdown(
        "<span style='font-size:13px;color:var(--nx-text2)'>Editá el precio nuevo en la columna "
        "**Precio nuevo ARS**. El sistema calcula el margen neto en tiempo real. "
        "Al exportar genera el Excel para cargar en Flexxus.</span>",
        unsafe_allow_html=True
    )

    filtro = st.selectbox("Filtrar", ["Con stock", "Todos", "Solo FR", "Solo Mecánico"])

    sql = """
        SELECT p.codigo, a.descripcion, a.marca,
               p.lista_1 as lista_1_usd,
               p.lista_4 as lista_4_ars,
               COALESCE(s.stock, 0) as stock,
               COALESCE(a.mla_id_fr, '') as mla_id_fr,
               COALESCE(a.mla_id_mec, '') as mla_id_mec
        FROM precios p
        LEFT JOIN articulos a ON p.codigo = a.codigo
        LEFT JOIN (
            SELECT codigo, SUM(stock) as stock
            FROM stock_snapshots ss
            JOIN (SELECT codigo, MAX(fecha) mf FROM stock_snapshots GROUP BY codigo) lx
              ON ss.codigo=lx.codigo AND ss.fecha=lx.mf
            GROUP BY codigo
        ) s ON p.codigo = s.codigo
        WHERE p.lista_1 > 0
        ORDER BY a.descripcion
    """
    df = query_to_df(sql)
    if df.empty:
        st.info("Sin datos de precios. Cargá la Lista de Precios primero.")
        return

    # Clasificar
    df["tipo"] = df["codigo"].apply(lambda c: "FR" if str(c)[0:1].isalpha() else "MECÁNICO")
    df["comision"] = df["tipo"].apply(lambda t: com_fr if t == "FR" else com_mec)
    df["lista_1_ars"] = (df["lista_1_usd"] * tasa).round(0)
    df["precio_sugerido"] = (df["lista_1_ars"] / (1 - df["comision"])).round(0)
    df["precio_nuevo"] = df["lista_4_ars"]  # editable

    # Filtrar
    if filtro == "Con stock":
        df = df[df["stock"] > 0]
    elif filtro == "Solo FR":
        df = df[df["tipo"] == "FR"]
    elif filtro == "Solo Mecánico":
        df = df[df["tipo"] == "MECÁNICO"]

    st.metric("Artículos a editar", len(df))

    df_edit = st.data_editor(
        df[["codigo", "descripcion", "tipo", "stock",
            "lista_1_usd", "lista_1_ars", "precio_sugerido",
            "lista_4_ars", "precio_nuevo"]].copy(),
        hide_index=True,
        width='stretch',
        column_config={
            "codigo":          st.column_config.TextColumn("Código", disabled=True),
            "descripcion":     st.column_config.TextColumn("Artículo", disabled=True, width="large"),
            "tipo":            st.column_config.TextColumn("Tipo", disabled=True),
            "stock":           st.column_config.NumberColumn("Stock", format="%d", disabled=True),
            "lista_1_usd":     st.column_config.NumberColumn("L1 USD", format="$%.2f", disabled=True),
            "lista_1_ars":     st.column_config.NumberColumn("L1 ARS", format="$%,.0f", disabled=True),
            "precio_sugerido": st.column_config.NumberColumn("Sugerido ML", format="$%,.0f", disabled=True),
            "lista_4_ars":     st.column_config.NumberColumn("Precio actual ML", format="$%,.0f", disabled=True),
            "precio_nuevo":    st.column_config.NumberColumn("⭐ Precio nuevo ARS", format="$%,.0f"),
        },
        key="editor_masivo_ml"
    )

    # Calcular margen en vivo
    df_edit["margen_neto"] = (
        (df_edit["precio_nuevo"] * (1 - df["comision"].values[:len(df_edit)]) - df_edit["lista_1_ars"])
        / df_edit["lista_1_ars"] * 100
    ).round(1)

    modificados = df_edit[df_edit["precio_nuevo"] != df_edit["lista_4_ars"]]

    if not modificados.empty:
        st.markdown(f"**{len(modificados)} precios modificados** · Margen promedio nuevo: "
                    f"{modificados['margen_neto'].mean():.1f}%")

    col_exp, col_save, _ = st.columns([2, 2, 4])

    with col_exp:
        if not modificados.empty:
            buf = BytesIO()
            export_df = modificados[["codigo", "descripcion", "tipo", "stock",
                                      "lista_1_usd", "lista_4_ars", "precio_nuevo", "margen_neto"]].copy()
            export_df.columns = ["Código", "Artículo", "Tipo", "Stock",
                                  "Lista 1 USD", "Precio actual ARS", "Precio nuevo ARS", "Margen neto %"]
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                export_df.to_excel(w, index=False, sheet_name="Precios ML")
            buf.seek(0)
            st.download_button(
                "📥 Exportar Excel para Flexxus",
                data=buf,
                file_name=f"precios_ml_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
            )

    with col_save:
        if not modificados.empty:
            if st.button("💾 Guardar precios nuevos", type="primary", width='stretch'):
                for _, row in modificados.iterrows():
                    execute_query(
                        "UPDATE precios SET lista_4=? WHERE codigo=?",
                        (float(row["precio_nuevo"]), row["codigo"]), fetch=False
                    )
                st.success(f"✅ {len(modificados)} precios actualizados")
                st.rerun()




# ─────────────────────────────────────────────────────────────
# TAB 3 — PRECIOS COMPETENCIA
# ─────────────────────────────────────────────────────────────
def _tab_competencia():
    """
    Permite cargar manualmente los precios de competidores.
    El matching se hace por nombre/descripción, no por código.
    """
    st.markdown("### 🆚 Precios de la Competencia")
    st.markdown(
        "<span style='font-size:13px;color:var(--nx-text2)'>"
        "Cargá los precios de competidores desde un Excel o manualmente. "
        "El sistema cruza por nombre de producto (no por código). "
        "Después podés comparar tu precio vs el de la competencia.</span>",
        unsafe_allow_html=True
    )

    _init_tabla_competencia()

    sub_tabs = st.tabs(["📥 Cargar precios", "📊 Ver comparación", "✏️ Editar manual"])

    # ── Sub-tab: Cargar archivo ──────────────────────────────
    with sub_tabs[0]:
        st.markdown("#### Subir Excel de competencia")
        st.markdown(
            "**Columnas esperadas:** `descripcion` (nombre del producto) y `precio` (ARS). "
            "Opcional: `competidor` (nombre del vendedor), `link` (URL de la publicación)."
        )
        ejemplo_df = pd.DataFrame({
            "descripcion": ["Modulo Samsung A12 Mecanico", "Modulo iPhone 13 Oled"],
            "precio": [18500, 95000],
            "competidor": ["repuestosarg", "piedrascell"],
            "link": ["https://ml.com/...", "https://ml.com/..."]
        })
        with st.expander("Ver formato de ejemplo"):
            st.dataframe(ejemplo_df, hide_index=True)

        archivo = st.file_uploader("Excel de precios competencia", type=["xlsx", "xls"],
                                    key="uploader_competencia")

        if archivo:
            try:
                df_comp = pd.read_excel(archivo, engine="openpyxl")
                df_comp.columns = [c.lower().strip().replace(" ", "_") for c in df_comp.columns]

                # Detectar columnas
                col_desc  = next((c for c in df_comp.columns if "desc" in c or "nombre" in c or "model" in c), None)
                col_precio = next((c for c in df_comp.columns if "prec" in c or "price" in c or "valor" in c), None)
                col_comp  = next((c for c in df_comp.columns if "comp" in c or "vend" in c or "tienda" in c), None)
                col_link  = next((c for c in df_comp.columns if "link" in c or "url" in c or "pub" in c), None)

                if not col_desc or not col_precio:
                    st.error(f"No encontré columnas de descripción/precio. Columnas: {list(df_comp.columns)}")
                else:
                    df_comp["_descripcion"] = df_comp[col_desc].astype(str)
                    df_comp["_precio"]      = pd.to_numeric(df_comp[col_precio], errors="coerce").fillna(0)
                    df_comp["_competidor"]  = df_comp[col_comp].astype(str) if col_comp else "Competidor"
                    df_comp["_link"]        = df_comp[col_link].astype(str) if col_link else ""

                    df_comp = df_comp[df_comp["_precio"] > 0]
                    st.success(f"✅ {len(df_comp)} registros encontrados")
                    st.dataframe(df_comp[["_descripcion","_precio","_competidor","_link"]].head(10),
                                  hide_index=True)

                    if st.button("💾 Importar precios", type="primary"):
                        ok = 0
                        for _, row in df_comp.iterrows():
                            execute_query("""
                                INSERT OR REPLACE INTO ml_precios_competencia
                                (descripcion, precio_ars, competidor, link, fecha_carga)
                                VALUES (?,?,?,?,date('now'))
                            """, (row["_descripcion"], float(row["_precio"]),
                                  row["_competidor"], row["_link"]), fetch=False)
                            ok += 1
                        st.success(f"✅ {ok} precios de competidores importados")
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # ── Sub-tab: Ver comparación ──────────────────────────────
    with sub_tabs[1]:
        tasa = float(get_config("tasa_usd_ars", float) or 1420)

        df_comp_db = query_to_df("""
            SELECT descripcion, precio_ars, competidor, link, fecha_carga
            FROM ml_precios_competencia
            ORDER BY fecha_carga DESC, descripcion
        """)

        if df_comp_db.empty:
            st.info("Sin precios de competidores cargados. Usá la pestaña **Cargar precios**.")
        else:
            st.metric("Productos competencia", len(df_comp_db))

            # Buscar equivalente en nuestro catálogo por nombre similar
            df_nuestros = query_to_df("""
                SELECT a.descripcion as desc_nuestro, p.lista_1 as l1_usd,
                       p.lista_4 as l4_ars, a.codigo
                FROM precios p JOIN articulos a ON p.codigo=a.codigo
                WHERE p.lista_4 > 0
            """)

            if not df_nuestros.empty:
                # Match fuzzy simple por palabras clave
                comparaciones = []
                for _, comp_row in df_comp_db.iterrows():
                    desc_comp = str(comp_row["descripcion"]).upper()
                    mejor_match = None
                    mejor_score = 0
                    for _, nuestro_row in df_nuestros.iterrows():
                        desc_n = str(nuestro_row["desc_nuestro"]).upper()
                        # Score: palabras en común
                        words_c = set(desc_comp.split())
                        words_n = set(desc_n.split())
                        comunes = len(words_c & words_n)
                        score = comunes / max(len(words_c), len(words_n), 1) * 100
                        if score > mejor_score:
                            mejor_score = score
                            mejor_match = nuestro_row

                    if mejor_match is not None and mejor_score > 40:
                        nuestro_precio = float(mejor_match.get("l4_ars") or 0)
                        comp_precio = float(comp_row["precio_ars"])
                        diff_pct = ((comp_precio - nuestro_precio) / nuestro_precio * 100
                                    if nuestro_precio > 0 else 0)
                        comparaciones.append({
                            "Competidor": comp_row["competidor"],
                            "Producto Competidor": comp_row["descripcion"][:40],
                            "Precio Competidor ARS": comp_precio,
                            "Nuestro Código": mejor_match["codigo"],
                            "Nuestro Producto": str(mejor_match["desc_nuestro"])[:40],
                            "Nuestro L4 ARS": nuestro_precio,
                            "Diferencia %": round(diff_pct, 1),
                            "Score match": round(mejor_score),
                            "Link": comp_row.get("link",""),
                        })

                if comparaciones:
                    df_comp_result = pd.DataFrame(comparaciones)
                    # Colorear diferencia
                    st.dataframe(
                        df_comp_result,
                        hide_index=True,
                        width='stretch',
                        column_config={
                            "Precio Competidor ARS": st.column_config.NumberColumn(format="$%,.0f"),
                            "Nuestro L4 ARS":        st.column_config.NumberColumn(format="$%,.0f"),
                            "Diferencia %":          st.column_config.NumberColumn(format="%.1f%%"),
                            "Score match":           st.column_config.NumberColumn(format="%d%%"),
                        }
                    )
                    buf = BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as w:
                        df_comp_result.to_excel(w, index=False, sheet_name="Competencia")
                    buf.seek(0)
                    st.download_button("📥 Exportar comparación",
                                        data=buf, file_name="competencia_ml.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.dataframe(df_comp_db, hide_index=True)

    # ── Sub-tab: Editar manual ────────────────────────────────
    with sub_tabs[2]:
        df_edit_db = query_to_df("""
            SELECT id, descripcion, precio_ars, competidor, link
            FROM ml_precios_competencia ORDER BY descripcion LIMIT 100
        """)
        if df_edit_db.empty:
            st.info("Sin datos. Cargá primero desde la pestaña Cargar precios.")
        else:
            df_ed = st.data_editor(
                df_edit_db,
                hide_index=True,
                width='stretch',
                column_config={
                    "id":          st.column_config.NumberColumn("ID", disabled=True),
                    "descripcion": st.column_config.TextColumn("Descripción"),
                    "precio_ars":  st.column_config.NumberColumn("Precio ARS", format="$%,.0f"),
                    "competidor":  st.column_config.TextColumn("Competidor"),
                    "link":        st.column_config.TextColumn("Link ML"),
                },
                key="editor_competencia"
            )
            if st.button("💾 Guardar cambios"):
                for _, row in df_ed.iterrows():
                    execute_query(
                        "UPDATE ml_precios_competencia SET descripcion=?, precio_ars=?, competidor=?, link=? WHERE id=?",
                        (row["descripcion"], float(row["precio_ars"]), row["competidor"], row["link"], int(row["id"])),
                        fetch=False
                    )
                st.success("✅ Guardado")
                st.rerun()


def _init_tabla_competencia():
    """Crea tabla de precios de competencia si no existe."""
    execute_query("""
        CREATE TABLE IF NOT EXISTS ml_precios_competencia (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            precio_ars  REAL DEFAULT 0,
            competidor  TEXT,
            link        TEXT,
            fecha_carga TEXT DEFAULT (date('now')),
            UNIQUE(descripcion, competidor)
        )
    """, fetch=False)


# ─────────────────────────────────────────────────────────────
# TAB 4 — IMPORTAR MLA IDs
# ─────────────────────────────────────────────────────────────
def _tab_importar_mla():
    st.markdown("### 📥 Importar MLA IDs desde Excel")
    st.markdown(
        "<span style='font-size:13px;color:var(--nx-text2)'>"
        "Subí un Excel con columnas: **codigo** y **mla_id** (ej: MLA1234567). "
        "El sistema detecta automáticamente si es de tienda FR o Mecánico según el código Flexxus.</span>",
        unsafe_allow_html=True
    )

    archivo = st.file_uploader("Excel con MLA IDs", type=["xlsx", "xls"], key="uploader_mla")

    if archivo:
        try:
            df_mla = pd.read_excel(archivo, engine="openpyxl")
            df_mla.columns = [c.lower().strip() for c in df_mla.columns]

            # Detectar columnas
            col_cod = next((c for c in df_mla.columns if "codi" in c or c == "sku"), None)
            col_mla = next((c for c in df_mla.columns if "mla" in c or "id" in c or "public" in c), None)

            if not col_cod or not col_mla:
                st.error(f"Columnas no reconocidas: {list(df_mla.columns)}. Necesito 'codigo' y 'mla_id'.")
                return

            df_mla["codigo"] = df_mla[col_cod].astype(str).str.strip()
            df_mla["mla_id"] = df_mla[col_mla].astype(str).str.strip().str.upper()
            df_mla = df_mla[df_mla["codigo"].str.len() > 1]
            df_mla["tipo"] = df_mla["codigo"].apply(lambda c: "FR" if c[0:1].isalpha() else "MECÁNICO")

            st.success(f"✅ {len(df_mla)} registros encontrados")
            st.dataframe(df_mla[["codigo", "tipo", "mla_id"]].head(20), hide_index=True)

            if st.button("💾 Importar MLA IDs", type="primary"):
                ok = 0
                for _, row in df_mla.iterrows():
                    cod = row["codigo"]
                    mla = row["mla_id"]
                    tipo = row["tipo"]
                    if tipo == "FR":
                        execute_query("UPDATE articulos SET mla_id_fr=? WHERE codigo=?",
                                      (mla, cod), fetch=False)
                    else:
                        execute_query("UPDATE articulos SET mla_id_mec=? WHERE codigo=?",
                                      (mla, cod), fetch=False)
                    ok += 1
                st.success(f"✅ {ok} MLA IDs importados")
                st.rerun()

        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

    st.markdown("---")
    st.markdown("**Formato esperado del Excel:**")
    ejemplo = pd.DataFrame({
        "codigo": ["MSAMA72.", "2401251688"],
        "mla_id": ["MLA1234567", "MLA7654321"]
    })
    st.dataframe(ejemplo, hide_index=True, width='content')


# ─────────────────────────────────────────────────────────────
# TAB 5 — REPORTE ACUMULATIVO
# ─────────────────────────────────────────────────────────────
def _tab_reporte():
    st.markdown("### 📈 Reporte de comparaciones guardadas")
    st.markdown(
        "<span style='font-size:13px;color:var(--nx-text2)'>"
        "Cada vez que comparás un artículo y le das ✅ OK, se acumula acá para generar reportes.</span>",
        unsafe_allow_html=True
    )

    _init_tabla_reporte()

    df_rep = query_to_df("""
        SELECT codigo, descripcion, tipo_tienda, termino_busqueda,
               nuestro_precio, mejor_competidor_precio, diferencia_pct,
               link_competidor, fecha_comparacion, observaciones
        FROM ml_reporte_comparaciones
        ORDER BY fecha_comparacion DESC
        LIMIT 200
    """)

    if df_rep.empty:
        st.info("Aún no hay comparaciones guardadas. Usá el comparador y hacé click en **✅ Agregar al reporte**.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Comparaciones", len(df_rep))
    bajo = int((df_rep["diferencia_pct"].fillna(0) < -5).sum())
    c2.metric("Somos más caros (>5%)", bajo)
    alto = int((df_rep["diferencia_pct"].fillna(0) > 5).sum())
    c3.metric("Somos más baratos", alto)

    st.dataframe(df_rep, hide_index=True, width='stretch')

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_rep.to_excel(w, index=False, sheet_name="Reporte ML")
    buf.seek(0)
    st.download_button(
        "📥 Exportar reporte completo",
        data=buf,
        file_name=f"reporte_ml_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _cargar_tabla_precios(tasa: float, filtro_tipo: str, filtro_stock: str, top_n) -> pd.DataFrame:
    sql = """
        SELECT p.codigo, a.descripcion, a.marca,
               p.lista_1 as lista_1_usd,
               p.lista_4 as lista_4_ars,
               COALESCE(s.stock, 0) as stock,
               COALESCE(a.mla_id_fr, '') as mla_id_fr,
               COALESCE(a.mla_id_mec, '') as mla_id_mec,
               COALESCE(a.ml_termino_busqueda, '') as ml_termino,
               COALESCE(a.ml_termino_anclado, 0) as anclado
        FROM precios p
        LEFT JOIN articulos a ON p.codigo = a.codigo
        LEFT JOIN (
            SELECT codigo, SUM(stock) as stock
            FROM stock_snapshots ss
            JOIN (SELECT codigo, MAX(fecha) mf FROM stock_snapshots GROUP BY codigo) lx
              ON ss.codigo=lx.codigo AND ss.fecha=lx.mf
            GROUP BY codigo
        ) s ON p.codigo = s.codigo
        WHERE p.lista_1 > 0
        ORDER BY a.descripcion
    """
    df = query_to_df(sql)
    if df.empty:
        return df

    df["tipo"] = df["codigo"].apply(lambda c: "FR" if str(c)[0:1].isalpha() else "MECÁNICO")
    df["lista_1_ars"] = (df["lista_1_usd"] * tasa).round(0)
    df["mla_id"] = df.apply(
        lambda r: r["mla_id_fr"] if r["tipo"] == "FR" else r["mla_id_mec"], axis=1
    )

    # Filtros
    if "FR" in filtro_tipo:
        df = df[df["tipo"] == "FR"]
    elif "MECÁNICO" in filtro_tipo:
        df = df[df["tipo"] == "MECÁNICO"]
    if filtro_stock == "Con stock":
        df = df[df["stock"] > 0]
    elif filtro_stock == "Sin stock":
        df = df[df["stock"] == 0]

    if top_n != "Todos":
        df = df.head(int(top_n))

    return df.reset_index(drop=True)


def _guardar_cambios_ml(df_original: pd.DataFrame, df_editado: pd.DataFrame):
    """Guarda MLA IDs y términos de búsqueda editados."""
    for i in range(min(len(df_original), len(df_editado))):
        orig = df_original.iloc[i]
        edit = df_editado.iloc[i]
        cod = orig["codigo"]
        tipo = orig.get("tipo", "")

        # Guardar MLA ID si cambió
        if str(edit.get("mla_id", "")) != str(orig.get("mla_id", "")):
            mla = str(edit["mla_id"]).strip()
            if "FR" in str(tipo):
                execute_query("UPDATE articulos SET mla_id_fr=? WHERE codigo=?", (mla, cod), fetch=False)
            else:
                execute_query("UPDATE articulos SET mla_id_mec=? WHERE codigo=?", (mla, cod), fetch=False)

        # Guardar término de búsqueda si cambió
        termino_nuevo = str(edit.get("ml_termino", "")).strip()
        termino_orig  = str(orig.get("ml_termino", "")).strip()
        if termino_nuevo and termino_nuevo != termino_orig:
            execute_query(
                "UPDATE articulos SET ml_termino_busqueda=?, ml_termino_anclado=1 WHERE codigo=?",
                (termino_nuevo, cod), fetch=False
            )


def _generar_termino(descripcion: str) -> str:
    """Genera un término de búsqueda ML desde la descripción de Flexxus."""
    desc = descripcion.upper()
    # Quitar palabras irrelevantes
    quitar = ["MODULO", "MÓDULO", "PANTALLA", "DISPLAY", "AMP", "MECANICO",
              "MECÁNICO", "FR", "W/F", "C/MARCO", "LCD", "OLED", "TFT",
              "ORIGINAL", "GENERICO", "GENÉRICO"]
    tokens = [t for t in desc.split() if t not in quitar]
    return " ".join(tokens[:6]).lower()


def _buscar_ml(termino: str, seller_id: str = None, max_results: int = 8) -> list:
    """Busca en la API pública de MercadoLibre Argentina."""
    try:
        # Intentar con API oficial primero
        url = "https://api.mercadolibre.com/sites/MLA/search"
        params = {
            "q": termino,
            "limit": max_results,
            "condition": "new",
        }
        if seller_id:
            params["nickname"] = seller_id.upper()

        resp = requests.get(url, params=params, headers=ML_HEADERS, timeout=8)

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("results", [])
            return [_parsear_item_ml(i) for i in items if i.get("price")]

        # Fallback: scraping web
        return _buscar_web_ml(termino, seller_id, max_results)

    except Exception as e:
        st.warning(f"Error buscando en ML: {e}")
        return []


def _buscar_web_ml(termino: str, tienda: str = None, max_results: int = 8) -> list:
    """Fallback: scraping básico del sitio web de ML."""
    try:
        query = termino.replace(" ", "-")
        if tienda:
            url = f"https://listado.mercadolibre.com.ar/{query}_Tienda_{tienda.upper()}"
        else:
            url = f"https://listado.mercadolibre.com.ar/{query}"

        resp = requests.get(url, headers=ML_HEADERS, timeout=10)
        if resp.status_code != 200:
            return []

        html = resp.text
        # Extraer precios y títulos con regex
        precios = re.findall(r'"price":(\d+)', html)
        titulos = re.findall(r'"title":"([^"]{10,80})"', html)
        links   = re.findall(r'"permalink":"(https://www\.mercadolibre\.com\.ar/[^"]+)"', html)
        vendedores = re.findall(r'"nickname":"([^"]{2,30})"', html)

        resultados = []
        for i in range(min(max_results, len(precios), len(titulos))):
            resultados.append({
                "titulo":   titulos[i] if i < len(titulos) else "Sin título",
                "precio":   int(precios[i]) if i < len(precios) else 0,
                "vendedor": vendedores[i] if i < len(vendedores) else "?",
                "link":     links[i] if i < len(links) else "",
                "mla_id":   "",
            })
        return resultados

    except Exception:
        return []


def _parsear_item_ml(item: dict) -> dict:
    return {
        "titulo":   item.get("title", ""),
        "precio":   int(item.get("price", 0)),
        "vendedor": item.get("seller", {}).get("nickname", "?"),
        "link":     item.get("permalink", ""),
        "mla_id":   item.get("id", ""),
        "reputacion": item.get("seller", {}).get("seller_reputation", {}).get("level_id", "?"),
        "ventas":   item.get("sold_quantity", 0),
    }


def _mostrar_resultados_ml(resultados: list, precio_propio: float, codigo: str, tienda: str):
    """Muestra tabla de comparación con botón para agregar al reporte."""
    st.markdown(f"#### Resultados en ML — {len(resultados)} encontrados")

    for r in resultados:
        precio_comp = r["precio"]
        vendedor = r["vendedor"]
        link = r.get("link", "")
        es_nuestro = tienda.upper() in vendedor.upper()

        if precio_propio > 0 and precio_comp > 0:
            diff_pct = (precio_comp - precio_propio) / precio_propio * 100
            diff_str = f"{'🟢' if diff_pct >= 0 else '🔴'} {diff_pct:+.1f}%"
        else:
            diff_pct = 0
            diff_str = "—"

        icon = "✅" if es_nuestro else "❌"
        link_str = f"[🔗 Ver]({link})" if link else "Sin link"

        col_info, col_accion = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"**{icon} {vendedor}** — "
                f"**${precio_comp:,.0f}** ARS · "
                f"vs nuestro ${precio_propio:,.0f} → {diff_str} · "
                f"{link_str}",
                unsafe_allow_html=False
            )
        with col_accion:
            if st.button("✅ Guardar", key=f"rep_{codigo}_{precio_comp}_{vendedor[:5]}"):
                _guardar_en_reporte(codigo, tienda, r, precio_propio, diff_pct)
                st.success("Guardado en reporte")


def _init_tabla_reporte():
    execute_query("""
        CREATE TABLE IF NOT EXISTS ml_reporte_comparaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            descripcion TEXT,
            tipo_tienda TEXT,
            termino_busqueda TEXT,
            nuestro_precio REAL,
            mejor_competidor_precio REAL,
            diferencia_pct REAL,
            link_competidor TEXT,
            fecha_comparacion TEXT DEFAULT (datetime('now')),
            observaciones TEXT
        )
    """, fetch=False)


def _guardar_en_reporte(codigo: str, tienda: str, resultado: dict, precio_propio: float, diff_pct: float):
    _init_tabla_reporte()
    # Obtener descripción
    rows = execute_query("SELECT descripcion FROM articulos WHERE codigo=?", (codigo,))
    desc = rows[0]["descripcion"] if rows else codigo

    execute_query("""
        INSERT INTO ml_reporte_comparaciones
        (codigo, descripcion, tipo_tienda, nuestro_precio, mejor_competidor_precio,
         diferencia_pct, link_competidor)
        VALUES (?,?,?,?,?,?,?)
    """, (
        codigo, desc, tienda,
        precio_propio, resultado["precio"],
        round(diff_pct, 2), resultado.get("link", "")
    ), fetch=False)


def _tab_calculadora():
    """Calculadora de precios ML paso a paso con detector de comisión implícita."""
    st.markdown("### 🧮 Calculadora de Precios ML")

    if not _MOTOR_OK:
        st.error("Motor ML no disponible. Verificá el archivo modules/ml_motor.py")
        return

    tasa    = float(get_config("tasa_usd_ars", float) or 1420)
    com_fr  = float(get_config("comision_ml_fr", float) or 14.0)
    com_mec = float(get_config("comision_ml_mecanico", float) or 13.0)
    m_fr    = float(get_config("margen_extra_ml_fr", float) or 0.0)
    m_mec   = float(get_config("margen_extra_ml_mec", float) or 0.0)

    st.markdown(f"""
    <div style="background:rgba(10,132,255,.08);border:1px solid rgba(10,132,255,.2);
                border-radius:10px;padding:10px 16px;margin-bottom:16px;font-size:13px">
        💡 Tienda <strong>FR</strong>: comisión {com_fr}% + margen extra {m_fr}% &nbsp;|&nbsp;
        Tienda <strong>Mecánico</strong>: comisión {com_mec}% + margen extra {m_mec}% &nbsp;|&nbsp;
        Tasa: ${tasa:,.0f} ARS/USD
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.markdown("**Ingresá el precio de Lista 1**")
        lista1_usd = st.number_input("Lista 1 (USD)", min_value=0.0, value=0.0,
                                      step=1.0, format="%.2f", key="calc_l1_usd")
        lista1_ars = lista1_usd * tasa if lista1_usd > 0 else 0

        tipo_tienda = st.radio("Tienda", ["FR (aitech)", "Mecánico"],
                                horizontal=True, key="calc_tienda")
        es_fr = "FR" in tipo_tienda
        com_base = com_fr if es_fr else com_mec
        m_base   = m_fr   if es_fr else m_mec

        com_adj = st.slider("Comisión ML (%)", 0.0, 30.0, com_base, 0.5, key="calc_com")
        m_adj   = st.slider("Margen extra (%)", 0.0, 30.0, m_base, 0.5, key="calc_mex")

        if lista1_ars > 0:
            st.markdown(f"Lista 1: **USD {lista1_usd:.2f}** = **ARS ${lista1_ars:,.0f}**")

    with col2:
        if lista1_ars > 0:
            cal = calcular_precio_publicacion(lista1_ars, com_adj, m_adj)
            st.markdown("**Desglose del cálculo**")
            filas = [
                ("📋 Lista 1 (base)",         f"USD {lista1_usd:.2f} = ARS ${lista1_ars:,.0f}", ""),
                ("➕ Margen extra",            f"{m_adj}%",       f"→ ARS ${cal['precio_base_ars']:,.0f}"),
                ("➗ Absorber comisión ML",    f"{com_adj}%",      "÷ (1 − comisión)"),
                ("🏷️ Precio a publicar",       f"**ARS ${cal['precio_ml_ars']:,.0f}**", f"≈ USD {cal['precio_ml_ars']/tasa:,.0f}"),
                ("💫 Precio psicológico",      f"**ARS ${cal['precio_ml_redondeado']:,}**", "Termina en 99"),
                ("💸 Comisión que pagás",      f"ARS ${cal['comision_pagada_ars']:,.0f}", ""),
                ("✅ Ganancia neta",            f"ARS ${cal['ganancia_neta_ars']:,.0f}", ""),
                ("📊 Margen real sobre L1",    f"{cal['margen_real_pct']}%", ""),
            ]
            for lbl, val, nota in filas:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:6px 0;
                            border-bottom:1px solid rgba(255,255,255,.06);font-size:13px">
                    <span style="color:var(--nx-text2)">{lbl}</span>
                    <span><strong>{val}</strong>
                    <span style="color:var(--nx-text3);font-size:11px;margin-left:6px">{nota}</span></span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Ingresá el precio de Lista 1 en USD para ver el desglose.")

    st.markdown("---")
    st.markdown("#### 🔍 ¿Qué comisión está usando la empresa?")
    st.caption("Ingresá el precio publicado actual y la Lista 1 para calcular la comisión implícita.")
    ci1, ci2 = st.columns(2)
    with ci1:
        precio_pub = st.number_input("Precio publicado en ML (ARS)", 0.0, step=100.0, key="calc_pub")
    with ci2:
        l1_check = st.number_input("Lista 1 (ARS)", 0.0, step=100.0, key="calc_l1_check")
    if precio_pub > 0 and l1_check > 0:
        com_imp = calcular_comision_implicita(precio_pub, l1_check)
        color = "#ff375f" if com_imp > 20 else "#ff9f0a" if com_imp > 15 else "#32d74b"
        st.markdown(f"""
        <div style="background:rgba(191,90,242,.1);border:1px solid rgba(191,90,242,.3);
                    border-radius:10px;padding:12px 16px;margin-top:8px;font-size:14px">
            Con precio ARS ${precio_pub:,.0f} y Lista 1 ARS ${l1_check:,.0f},
            la comisión implícita es
            <strong style="color:{color};font-size:18px">{com_imp}%</strong>
        </div>
        """, unsafe_allow_html=True)

