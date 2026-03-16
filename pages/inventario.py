"""
ROKER NEXUS — Página: Inventario & Quiebres
"""
import streamlit as st
import pandas as pd

from modules.inventario import (
    detectar_quiebres, detectar_quiebre_entre_depositos,
    agregar_a_lista_negra, quitar_de_lista_negra,
    get_lista_negra, get_resumen_stock, get_anomalias_abiertas
)
from database import query_to_df
from utils.helpers import fmt_usd, fmt_num, color_stock, severidad_badge
from config import DEPOSITOS


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        📦 Inventario & Quiebres
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:20px">
        Detección automática de quiebres, anomalías y lista negra
    </p>
    """, unsafe_allow_html=True)

    # ── Resumen rápido ────────────────────────────────────────
    resumen = get_resumen_stock()
    if resumen:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total artículos", fmt_num(resumen.get("total_articulos", 0)))
        c2.metric("Sin stock 🔴", resumen.get("sin_stock", 0))
        c3.metric("Bajo mínimo 🟡", resumen.get("bajo_minimo", 0))
        c4.metric("Depósitos activos", resumen.get("depositos_activos", 0))
        st.divider()

    tabs = st.tabs([
        "🔴 Quiebres",
        "⚡ Larrea vs San José",
        "🔍 Investigar",
        "⛔ Lista Negra",
        "📋 Anomalías",
        "✏️ Demanda Manual",
        "🔗 Alias de Códigos",
    ])

    # ── Tab Quiebres ──────────────────────────────────────────
    with tabs[0]:
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
        with col_f1:
            deposito_sel = st.selectbox(
                "Depósito",
                ["Todos"] + list(DEPOSITOS.keys()),
                format_func=lambda k: DEPOSITOS.get(k, k) if k != "Todos" else "Todos",
            )
        with col_f2:
            umbral = st.slider("Umbral de stock", 0, 50, 10)
        with col_f3:
            try:
                from database import execute_query
                rubros_rows = execute_query("SELECT DISTINCT rubro FROM stock_snapshots WHERE rubro IS NOT NULL AND rubro != '' ORDER BY rubro")
                rubros_opts = ["Todos"] + [r["rubro"] for r in rubros_rows if r.get("rubro")]
            except Exception:
                rubros_opts = ["Todos"]
            rubros_sel = st.multiselect("Rubro(s)", rubros_opts[1:], placeholder="Todos los rubros")
        with col_f4:
            solo_cero = st.checkbox("Solo stock=0", value=False)

        dep = deposito_sel if deposito_sel != "Todos" else None
        umb = 0 if solo_cero else umbral

        df_q = detectar_quiebres(umbral=umb, deposito=dep)
        # Filtrar por rubros seleccionados
        if rubros_sel and "rubro" in df_q.columns:
            df_q = df_q[df_q["rubro"].isin(rubros_sel)]

        if df_q.empty:
            st.success("✅ No hay quiebres con los filtros actuales.")
        else:
            st.markdown(f"**{len(df_q)} artículos** con stock ≤ {umb}")

            # Botones de acción rápida
            col_a, col_b, col_c = st.columns([2, 2, 4])
            with col_a:
                if st.button("📤 Exportar Excel", width="stretch"):
                    _exportar_excel(df_q, "quiebres")
            with col_b:
                if st.button("🤖 Analizar con IA", width="stretch"):
                    st.session_state["analizar_quiebres"] = True

            # Tabla principal
            cols_show = [c for c in [
                "codigo", "descripcion", "deposito", "marca",
                "stock", "stock_minimo", "severidad",
                "stock_central", "accion_sugerida"
            ] if c in df_q.columns]

            df_show = df_q[cols_show].copy()
            df_show.insert(0, "🚦", df_show["stock"].apply(color_stock))

            st.dataframe(
                df_show,
                width="stretch",
                hide_index=True,
                column_config={
                    "🚦": st.column_config.TextColumn("", width="small"),
                    "codigo": st.column_config.TextColumn("Código"),
                    "descripcion": st.column_config.TextColumn("Artículo", width="large"),
                    "stock": st.column_config.NumberColumn("Stock", format="%d"),
                    "stock_minimo": st.column_config.NumberColumn("Mínimo", format="%d"),
                    "stock_central": st.column_config.NumberColumn("San José", format="%d"),
                    "accion_sugerida": st.column_config.TextColumn("Acción sugerida", width="large"),
                }
            )

            # Análisis IA
            if st.session_state.get("analizar_quiebres"):
                with st.spinner("🤖 Analizando quiebres con Claude..."):
                    from modules.ia_engine import motor_ia
                    analisis = motor_ia.analizar_quiebres(df_q)
                    st.info(analisis)
                st.session_state["analizar_quiebres"] = False

    # ── Tab Larrea vs San José ────────────────────────────────
    with tabs[1]:
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:16px">
            Detecta artículos donde <b>Larrea tiene stock cero</b> pero
            <b>San José tiene stock disponible</b> — posible falla de reposición interna.
        </div>
        """, unsafe_allow_html=True)

        df_cruce = detectar_quiebre_entre_depositos()

        if df_cruce.empty:
            st.success("✅ No hay quiebres de reposición interna detectados.")
        else:
            st.warning(f"⚠️ {len(df_cruce)} artículos en Larrea sin stock cuando San José tiene stock")

            for _, row in df_cruce.head(20).iterrows():
                col1, col2, col3 = st.columns([4, 2, 2])
                with col1:
                    desc = row.get("descripcion") or row.get("codigo", "?")
                    st.markdown(f"**{desc}** `{row.get('codigo','')}`")
                with col2:
                    st.markdown(f"🔴 Larrea: **{int(row.get('stock_larrea',0))} uds**")
                with col3:
                    st.markdown(f"🟢 San José: **{int(row.get('stock_san_jose',0))} uds**")

                col_btn1, col_btn2, _ = st.columns([2, 2, 4])
                with col_btn1:
                    if st.button(f"⚡ Marcar para remito", key=f"remito_{row.get('codigo','')}"):
                        st.success(f"Marcado ✓")
                with col_btn2:
                    if st.button(f"🔍 Investigar", key=f"inv_{row.get('codigo','')}"):
                        st.session_state["investigar_codigo"] = row.get("codigo", "")
                st.divider()

    # ── Tab Investigar ────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 🔍 Ficha de investigación de artículo")
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:16px">
            Ingresá el código para ver el historial completo del artículo en todos los depósitos.
        </div>
        """, unsafe_allow_html=True)

        codigo_inv = st.text_input(
            "Código del artículo",
            value=st.session_state.get("investigar_codigo", ""),
            placeholder="Ej: 2401251672 o MSAMA10S.",
            key="input_investigar"
        )

        if codigo_inv:
            _ficha_investigacion(codigo_inv)

    # ── Tab Lista Negra ───────────────────────────────────────
    with tabs[3]:
        st.markdown("### ⛔ Lista Negra")
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:16px">
            Artículos excluidos de sugerencias de compra. Se pueden reactivar en cualquier momento.
        </div>
        """, unsafe_allow_html=True)

        # Subir Excel de lista negra
        with st.expander("📤 Cargar lista negra desde Excel"):
            st.caption("El archivo debe llamarse 'lista negra.xlsx' · Col A = Código · Col B = Descripción (opcional)")
            f_negra = st.file_uploader("Archivo Excel", type=["xlsx","xls"], key="upload_negra")
            if f_negra and st.button("⛔ Cargar lista negra", type="primary"):
                import pandas as pd
                try:
                    df_upload = pd.read_excel(f_negra, header=None)
                    agregados = 0
                    for _, row in df_upload.iterrows():
                        cod = str(row.iloc[0]).strip()
                        desc = str(row.iloc[1]).strip() if len(row) > 1 else ""
                        if cod and cod != "nan" and len(cod) > 1:
                            if agregar_a_lista_negra(cod, desc):
                                agregados += 1
                    st.success(f"✅ {agregados} artículos agregados a lista negra")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        # Agregar manualmente
        with st.expander("➕ Agregar artículo manualmente"):
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                codigo_neg = st.text_input("Código", key="input_negro_cod")
            with col2:
                motivo_neg = st.text_input("Motivo (opcional)", key="input_negro_mot")
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Agregar ⛔", width="stretch"):
                    if codigo_neg:
                        if agregar_a_lista_negra(codigo_neg.strip(), motivo_neg):
                            st.success(f"✅ {codigo_neg} agregado a lista negra")
                            st.rerun()

        df_neg = get_lista_negra()
        if df_neg.empty:
            st.info("La lista negra está vacía.")
        else:
            st.markdown(f"**{len(df_neg)} artículos** en lista negra")
            for _, row in df_neg.iterrows():
                col1, col2, col3, col4 = st.columns([2, 3, 3, 1])
                with col1:
                    st.markdown(f"`{row.get('codigo','')}`")
                with col2:
                    st.markdown(f"<span style='font-size:13px'>{row.get('descripcion','') or '—'}</span>",
                                unsafe_allow_html=True)
                with col3:
                    st.markdown(f"<span style='font-size:12px;color:var(--nx-text2)'>{row.get('motivo_negra','') or '—'}</span>",
                                unsafe_allow_html=True)
                with col4:
                    if st.button("↩️", key=f"quitar_{row.get('codigo','')}",
                                 help="Quitar de lista negra"):
                        quitar_de_lista_negra(row.get("codigo", ""))
                        st.rerun()

    # ── Tab Anomalías ─────────────────────────────────────────
    with tabs[4]:
        df_an = get_anomalias_abiertas()
        if df_an.empty:
            st.success("✅ No hay anomalías abiertas.")
        else:
            st.warning(f"⚠️ {len(df_an)} anomalías abiertas")
            for _, row in df_an.iterrows():
                sev = row.get("severidad", "media")
                border = {"alta": "var(--nx-red)", "media": "var(--nx-amber)"}.get(sev, "var(--nx-border)")
                st.markdown(f"""
                <div class="nx-card" style="border-left:3px solid {border}">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <span style="font-size:13px;font-weight:500;color:var(--nx-text)">
                            {row.get('codigo','')} — {row.get('tipo','')}
                        </span>
                        {severidad_badge(sev)}
                    </div>
                    <div style="font-size:12px;color:var(--nx-text2);margin-top:4px">
                        {row.get('descripcion','')} | {row.get('deposito','')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── Tab Demanda Manual ────────────────────────────────────
    with tabs[5]:
        _tab_demanda_manual()

    # ── Tab Alias de Códigos ──────────────────────────────────
    with tabs[6]:
        _tab_alias_codigos()


def _tab_demanda_manual():
    """Demanda manual integrada — override de demanda cuando Flexxus muestra 0."""
    from database import execute_query as _exec

    st.markdown("""
    <h3 style="margin:0 0 4px">✏️ Demanda Manual</h3>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
    Override cuando el ERP muestra 0 por quiebre de stock real. La demanda manual tiene prioridad.</p>
    """, unsafe_allow_html=True)

    st.info("💡 Usá esto cuando Flexxus muestra 0 ventas porque te quedaste sin stock. Ingresá la demanda mensual real.")

    # Asegurar tabla
    try:
        _exec("""CREATE TABLE IF NOT EXISTS demanda_manual (
            codigo TEXT PRIMARY KEY, demanda_manual REAL NOT NULL,
            nota TEXT, actualizado TEXT DEFAULT (datetime('now')))""", fetch=False)
    except Exception:
        pass

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: filtro_dm = st.text_input("🔍 Filtrar", "", key="inv_dm_f")
    with c2: solo_cero_dm = st.checkbox("Solo ERP=0", True, key="inv_dm_z")
    with c3: prov_dm = st.selectbox("Proveedor", ["Todos", "AI-TECH", "Mecánico"], key="inv_dm_p")

    try:
        df_dm = query_to_df("""
            SELECT o.codigo, COALESCE(a.descripcion, o.descripcion) as articulo,
                   o.demanda_promedio as dem_erp, o.stock_actual,
                   COALESCE(dm.demanda_manual, 0) as dem_manual,
                   CASE WHEN SUBSTR(o.codigo,1,1) BETWEEN '0' AND '9' THEN 'Mecánico' ELSE 'AI-TECH' END as proveedor
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo=a.codigo
            LEFT JOIN demanda_manual dm ON o.codigo=dm.codigo
            ORDER BY o.demanda_promedio ASC, o.codigo
        """)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if df_dm.empty:
        st.info("Sin datos. Cargá primero el archivo de Optimización de Stock.")
        return

    if filtro_dm:
        mask = (df_dm["articulo"].str.upper().str.contains(filtro_dm.upper(), na=False) |
                df_dm["codigo"].str.upper().str.contains(filtro_dm.upper(), na=False))
        df_dm = df_dm[mask]
    if solo_cero_dm:
        df_dm = df_dm[df_dm["dem_erp"] == 0]
    if prov_dm != "Todos":
        df_dm = df_dm[df_dm["proveedor"] == prov_dm]

    st.caption(f"{len(df_dm):,} artículos")
    df_dm_e = df_dm[["codigo", "articulo", "proveedor", "stock_actual", "dem_erp", "dem_manual"]].reset_index(drop=True)

    edited_dm = st.data_editor(df_dm_e, width="stretch", hide_index=True, height=500,
        column_config={
            "codigo":       st.column_config.TextColumn("Código", disabled=True),
            "articulo":     st.column_config.TextColumn("Artículo", disabled=True, width="large"),
            "proveedor":    st.column_config.TextColumn("Prov.", disabled=True, width="small"),
            "stock_actual": st.column_config.NumberColumn("Stock", disabled=True, format="%d"),
            "dem_erp":      st.column_config.NumberColumn("Dem. ERP", disabled=True, format="%.1f"),
            "dem_manual":   st.column_config.NumberColumn("Dem. Manual ✏️", min_value=0, format="%.1f",
                                help="0 = eliminar override"),
        }, num_rows="fixed", key="inv_dm_editor")

    if st.button("💾 Guardar cambios", type="primary", key="inv_dm_save"):
        cambios_dm = 0
        for i, row in edited_dm.iterrows():
            nueva_dm = float(row["dem_manual"] or 0)
            vieja_dm = float(df_dm_e.iloc[i]["dem_manual"] or 0)
            if abs(nueva_dm - vieja_dm) > 0.01:
                try:
                    if nueva_dm <= 0:
                        _exec("DELETE FROM demanda_manual WHERE codigo=?", (row["codigo"],), fetch=False)
                    else:
                        _exec("""INSERT INTO demanda_manual (codigo,demanda_manual,nota,actualizado)
                            VALUES(?,?,?,datetime('now')) ON CONFLICT(codigo) DO UPDATE SET
                            demanda_manual=excluded.demanda_manual, actualizado=datetime('now')
                        """, (row["codigo"], nueva_dm, ""), fetch=False)
                    cambios_dm += 1
                except Exception as e:
                    st.error(f"Error guardando {row['codigo']}: {e}")
        if cambios_dm:
            st.success(f"✅ {cambios_dm} override(s) guardados.")
            st.rerun()
        else:
            st.info("Sin cambios.")


def _tab_alias_codigos():
    """Gestor de alias de códigos — mapeo de nombres alternativos a códigos Flexxus."""
    from database import execute_query as _exec

    st.markdown("""
    <h3 style="margin:0 0 4px">🔗 Alias de Códigos</h3>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
    Asocia nombres alternativos (apodos, modelos cortos) a códigos Flexxus reales.
    Mejora el matching fuzzy en el Borrador de Pedido.</p>
    """, unsafe_allow_html=True)

    # Asegurar tabla
    try:
        _exec("""CREATE TABLE IF NOT EXISTS codigo_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_flexxus TEXT NOT NULL,
            alias TEXT NOT NULL,
            descripcion TEXT DEFAULT '',
            activo INTEGER DEFAULT 1,
            creado_en TEXT DEFAULT (datetime('now')),
            UNIQUE(codigo_flexxus, alias))""", fetch=False)
    except Exception:
        pass

    # Agregar nuevo alias
    with st.expander("➕ Agregar alias", expanded=False):
        col_a1, col_a2, col_a3, col_a4 = st.columns([2, 2, 3, 1])
        with col_a1:
            nuevo_cod = st.text_input("Código Flexxus", placeholder="Ej: MSAMA06.", key="alias_cod")
        with col_a2:
            nuevo_alias = st.text_input("Alias / Apodo", placeholder="Ej: sam a06 oled", key="alias_txt")
        with col_a3:
            nuevo_desc = st.text_input("Descripción (opcional)", key="alias_desc")
        with col_a4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Agregar", key="alias_add", type="primary"):
                if nuevo_cod.strip() and nuevo_alias.strip():
                    try:
                        _exec("""INSERT OR IGNORE INTO codigo_aliases
                            (codigo_flexxus, alias, descripcion)
                            VALUES (?, ?, ?)""",
                            (nuevo_cod.strip().upper(), nuevo_alias.strip().lower(), nuevo_desc.strip()),
                            fetch=False)
                        st.success(f"✅ Alias '{nuevo_alias}' → {nuevo_cod.upper()} agregado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Completá código y alias.")

    # Búsqueda y tabla
    buscar_alias = st.text_input("🔍 Buscar en alias", placeholder="Ej: a06, moto g, iphone...", key="alias_buscar")

    try:
        if buscar_alias:
            df_al = query_to_df("""
                SELECT id, codigo_flexxus, alias, descripcion, activo, creado_en
                FROM codigo_aliases
                WHERE (UPPER(alias) LIKE ? OR UPPER(codigo_flexxus) LIKE ?)
                  AND activo = 1
                ORDER BY codigo_flexxus, alias
            """, (f"%{buscar_alias.upper()}%", f"%{buscar_alias.upper()}%"))
        else:
            df_al = query_to_df("""
                SELECT id, codigo_flexxus, alias, descripcion, activo, creado_en
                FROM codigo_aliases
                WHERE activo = 1
                ORDER BY codigo_flexxus, alias
            """)
    except Exception as e:
        st.error(f"Error cargando aliases: {e}")
        return

    if df_al.empty:
        st.info("No hay alias cargados todavía. Usá el formulario de arriba para agregar.")
        return

    st.caption(f"{len(df_al)} alias activos")

    # Tabla con opción de borrar
    for _, row in df_al.iterrows():
        col1, col2, col3, col4 = st.columns([2, 3, 3, 1])
        with col1:
            st.markdown(f"`{row.get('codigo_flexxus','')}`")
        with col2:
            st.markdown(f"<span style='font-size:13px;color:var(--text)'>{row.get('alias','')}</span>",
                        unsafe_allow_html=True)
        with col3:
            st.markdown(f"<span style='font-size:12px;color:var(--text2)'>{row.get('descripcion','') or '—'}</span>",
                        unsafe_allow_html=True)
        with col4:
            if st.button("🗑️", key=f"del_alias_{row['id']}", help="Eliminar alias"):
                try:
                    _exec("UPDATE codigo_aliases SET activo=0 WHERE id=?", (int(row["id"]),), fetch=False)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Importar aliases desde Excel
    with st.expander("📤 Importar aliases desde Excel"):
        st.caption("Col A = Código Flexxus · Col B = Alias · Col C = Descripción (opcional)")
        f_al = st.file_uploader("Archivo Excel", type=["xlsx", "xls"], key="upload_aliases")
        if f_al and st.button("📥 Importar", type="primary", key="import_aliases"):
            import pandas as pd
            try:
                df_imp = pd.read_excel(f_al, header=None)
                agregados_al = 0
                for _, row_imp in df_imp.iterrows():
                    cod_imp = str(row_imp.iloc[0]).strip().upper()
                    al_imp  = str(row_imp.iloc[1]).strip().lower() if len(row_imp) > 1 else ""
                    desc_imp = str(row_imp.iloc[2]).strip() if len(row_imp) > 2 else ""
                    if cod_imp and al_imp and cod_imp != "NAN" and al_imp != "nan":
                        try:
                            _exec("""INSERT OR IGNORE INTO codigo_aliases
                                (codigo_flexxus, alias, descripcion) VALUES (?,?,?)""",
                                (cod_imp, al_imp, desc_imp), fetch=False)
                            agregados_al += 1
                        except Exception:
                            pass
                st.success(f"✅ {agregados_al} aliases importados")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def _ficha_investigacion(codigo: str):
    """Muestra historial completo de un artículo."""
    # Info básica
    df_art = query_to_df(
        "SELECT * FROM articulos WHERE codigo=?", (codigo,)
    )
    if not df_art.empty:
        row = df_art.iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Artículo:** {row.get('descripcion','—')}")
            st.markdown(f"**Marca:** {row.get('marca','—')}")
        with col2:
            st.markdown(f"**Tipo:** {row.get('tipo_codigo','—')}")
            neg = "⛔ En lista negra" if row.get("en_lista_negra") else "✅ Activo"
            st.markdown(f"**Estado:** {neg}")

    # Historial de stock por depósito
    df_hist = query_to_df("""
        SELECT deposito, stock, fecha
        FROM stock_snapshots
        WHERE codigo=?
        ORDER BY fecha DESC, deposito
        LIMIT 60
    """, (codigo,))

    if not df_hist.empty:
        st.markdown("**📊 Historial de stock:**")
        import plotly.express as px
        fig = px.line(
            df_hist, x="fecha", y="stock", color="deposito",
            color_discrete_sequence=["#00d2ff", "#00e676", "#ffab40"],
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Space Grotesk", size=11, color="#8b95a8"),
            height=200, margin=dict(l=0,r=0,t=10,b=30),
            legend=dict(orientation="h", y=-0.4, font_size=10),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    else:
        st.info("Sin historial de stock para este código.")

    # Precio
    df_precio = query_to_df(
        "SELECT lista_1, lista_4, fecha FROM precios WHERE codigo=? ORDER BY fecha DESC LIMIT 1",
        (codigo,)
    )
    if not df_precio.empty:
        p = df_precio.iloc[0]
        col1, col2 = st.columns(2)
        col1.metric("Lista 1 (mayorista)", fmt_usd(p.get("lista_1", 0)))
        col2.metric("Lista 4 (MercadoLibre)", fmt_usd(p.get("lista_4", 0)))


def _exportar_excel(df: pd.DataFrame, nombre: str):
    """Exporta un DataFrame a Excel y ofrece descarga."""
    from io import BytesIO
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Datos")
    buf.seek(0)
    fecha = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        f"⬇️ Descargar {nombre}_{fecha}.xlsx",
        data=buf,
        file_name=f"{nombre}_{fecha}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
