"""
ROKER NEXUS — Borrador de Pedido
Módulo conversacional para anotar pedidos sin necesitar el código exacto.

Reglas de negocio:
  - Solo trabajamos con MECÁNICO (números) por defecto
  - ANTES de confirmar un mecánico, verificar si hay stock FR del mismo modelo
  - Si hay stock FR → alerta "tenés FR disponible, ¿igual pedís mecánico?"
  - Fuzzy matching: el usuario escribe "moto g13" y el sistema sugiere candidatos
  - El borrador se puede exportar al lote de compras una vez confirmado
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

from database import query_to_df, execute_query, get_config
from utils.helpers import fmt_usd, fmt_num
from utils.matching import extraer_modelo, extraer_marca, tipo_codigo


# ── Constantes ───────────────────────────────────────────────
ESTADOS = {
    "pendiente":  ("⏳", "var(--nx-amber)"),
    "confirmado": ("✅", "var(--nx-green)"),
    "descartado": ("❌", "var(--nx-text3)"),
}


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        📝 Borrador de Pedido
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:4px">
        Anotá modelos sin necesitar el código. El sistema los busca y vos confirmás.
    </p>
    <div style="font-size:12px;color:var(--nx-text3);margin-bottom:20px;
                background:rgba(255,159,10,.08);border:1px solid rgba(255,159,10,.2);
                border-radius:8px;padding:8px 12px;display:inline-block">
        ⚙️ Modo activo: <strong style="color:#ff9f0a">MECÁNICO</strong>
        · FR pausado · Se verifica stock FR antes de cada pedido
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "✏️ Agregar ítems",
        "📋 Borrador actual",
        "📤 Exportar a Lote",
        "👻 Ghost SKUs",
    ])

    with tabs[0]:
        _tab_agregar()
    with tabs[1]:
        _tab_borrador()
    with tabs[2]:
        _tab_exportar()
    with tabs[3]:
        _tab_ghost_skus()


# ─────────────────────────────────────────────────────────────
# TAB 1 — AGREGAR ÍTEMS
# ─────────────────────────────────────────────────────────────
def _tab_agregar():
    st.markdown("### Agregar modelo al borrador")
    st.markdown(
        "<span style='font-size:13px;color:var(--nx-text2)'>"
        "Escribí el nombre del modelo como lo conocés. "
        "El sistema busca el código automáticamente y te muestra las opciones.</span>",
        unsafe_allow_html=True
    )

    col_inp, col_cant = st.columns([4, 1])
    with col_inp:
        texto = st.text_input(
            "Modelo / descripción",
            placeholder="Ej: moto g13, sam a05s, iphone 13...",
            key="borrador_texto"
        )
    with col_cant:
        cantidad = st.number_input("Cantidad", min_value=1, max_value=9999,
                                    value=1, key="borrador_cant")

    if texto and len(texto.strip()) >= 3:
        _buscar_y_mostrar_candidatos(texto.strip(), int(cantidad))
    elif texto:
        st.warning("Escribí al menos 3 caracteres para buscar.")

    st.markdown("---")
    st.markdown("**O agregá múltiples ítems de una vez (uno por línea):**")
    st.markdown(
        "<span style='font-size:12px;color:var(--nx-text3)'>"
        "Formato: `modelo, cantidad` — Ej: `moto g13, 50`</span>",
        unsafe_allow_html=True
    )
    texto_multi = st.text_area(
        "Lista de modelos",
        placeholder="moto g13, 50\nsamsung a05s, 30\niphone 13 mecanico, 20",
        height=120,
        key="borrador_multi",
        label_visibility="collapsed"
    )
    if st.button("📥 Agregar lista", width='content'):
        _agregar_lista(texto_multi)


def _buscar_y_mostrar_candidatos(query: str, cantidad: int):
    """Busca candidatos y muestra con alerta FR si aplica."""
    candidatos = _buscar_mecanicos(query)
    candidatos_fr = _buscar_fr_mismo_modelo(query)

    if not candidatos:
        st.info(f"No encontré mecánicos para **{query}**. "
                "El ítem se agrega como pendiente de matching.")
        if st.button("➕ Agregar sin código (confirmar después)",
                      key=f"add_sin_cod_{query}"):
            _guardar_borrador_item(
                texto_original=query,
                codigo=None,
                descripcion=query.upper(),
                cantidad=cantidad,
                precio=0,
                match_confirmado=False
            )
            st.success(f"✅ '{query}' agregado como pendiente")
            st.rerun()
        return

    # Alerta FR si hay stock disponible
    if candidatos_fr:
        st.warning(
            f"⚠️ **Hay stock FR disponible** para este modelo antes de pedir mecánico:\n\n" +
            "\n".join([f"• `{r['codigo']}` {r['descripcion'][:40]} — Stock: **{int(r['stock'])} uds**"
                       for r in candidatos_fr[:3]])
        )

    st.markdown(f"**{len(candidatos)} coincidencias mecánico** — Elegí cuál agregar:")

    for i, c in enumerate(candidatos[:8]):
        stock = int(c.get("stock", 0))
        precio = float(c.get("precio_usd", 0))
        stock_color = "🔴" if stock == 0 else ("🟡" if stock < 5 else "🟢")

        col_info, col_add = st.columns([5, 1])
        with col_info:
            fr_alt = ""
            if candidatos_fr:
                fr_alt = f' <span style="color:#ff9f0a;font-size:10px">· FR disponible</span>'
            st.markdown(
                f"""<div style="padding:8px;background:var(--nx-card);border-radius:8px;
                    border:1px solid var(--nx-border);margin-bottom:4px">
                    <span style="font-size:12px;font-weight:600;color:var(--nx-text)">{c['descripcion'][:50]}</span>
                    <span style="font-size:10px;color:var(--nx-text3);margin-left:8px">`{c['codigo']}`</span>
                    {fr_alt}<br>
                    <span style="font-size:11px;color:var(--nx-text2)">
                        {stock_color} Stock: {stock} u &nbsp;|&nbsp;
                        💵 USD {precio:.2f}
                    </span>
                </div>""",
                unsafe_allow_html=True
            )
        with col_add:
            if st.button("➕", key=f"add_{c['codigo']}_{i}", width='stretch',
                          help=f"Agregar {c['codigo']}"):
                _guardar_borrador_item(
                    texto_original=query,
                    codigo=c["codigo"],
                    descripcion=c["descripcion"],
                    cantidad=cantidad,
                    precio=precio,
                    match_confirmado=True,
                    stock_fr=len(candidatos_fr) > 0,
                    cod_fr=candidatos_fr[0]["codigo"] if candidatos_fr else None
                )
                st.success(f"✅ `{c['codigo']}` — {c['descripcion'][:40]} agregado")
                st.rerun()


def _agregar_lista(texto: str):
    """Agrega múltiples ítems desde texto multilínea."""
    if not texto.strip():
        return
    lineas = [l.strip() for l in texto.strip().splitlines() if l.strip()]
    agregados = 0
    for linea in lineas:
        partes = linea.split(",")
        modelo = partes[0].strip()
        try:
            cant = int(partes[1].strip()) if len(partes) > 1 else 1
        except ValueError:
            cant = 1

        if modelo:
            _guardar_borrador_item(
                texto_original=linea,
                codigo=None,
                descripcion=modelo.upper(),
                cantidad=cant,
                precio=0,
                match_confirmado=False
            )
            agregados += 1

    if agregados:
        st.success(f"✅ {agregados} ítems agregados al borrador como pendientes de matching")
        st.rerun()


# ─────────────────────────────────────────────────────────────
# TAB 2 — BORRADOR ACTUAL
# ─────────────────────────────────────────────────────────────
def _tab_borrador():
    df = query_to_df("""
        SELECT id, texto_original, codigo_flexxus, descripcion,
               tipo_codigo, cantidad, precio_usd, subtotal_usd,
               stock_fr_disponible, codigo_fr_alternativo,
               estado, match_confirmado, creado_en
        FROM borrador_pedido
        WHERE estado != 'descartado'
        ORDER BY creado_en DESC
    """)

    if df.empty:
        st.info("El borrador está vacío. Agregá ítems en la pestaña **✏️ Agregar ítems**.")
        return

    # Métricas
    confirmados = df[df["estado"] == "confirmado"]
    pendientes  = df[df["estado"] == "pendiente"]
    total_usd   = float(confirmados["subtotal_usd"].fillna(0).sum())
    tasa = float(get_config("tasa_usd_ars", float) or 1420)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total ítems", len(df))
    c2.metric("✅ Confirmados", len(confirmados))
    c3.metric("⏳ Pendientes", len(pendientes))
    c4.metric("💰 Total USD", f"${total_usd:,.0f}")

    # Alertas FR pendientes
    con_fr = df[df["stock_fr_disponible"] == 1]
    if not con_fr.empty:
        st.warning(
            f"⚠️ **{len(con_fr)} ítems** tienen stock FR disponible — "
            "verificá si realmente necesitás pedir mecánico."
        )

    st.markdown("---")

    # Tabla editable
    df_edit = df.copy()
    df_edit["cantidad"] = df_edit["cantidad"].fillna(0).astype(int)
    df_edit["precio_usd"] = df_edit["precio_usd"].fillna(0)

    df_editado = st.data_editor(
        df_edit[[
            "id", "descripcion", "codigo_flexxus", "cantidad",
            "precio_usd", "subtotal_usd", "estado",
            "stock_fr_disponible", "texto_original"
        ]],
        hide_index=True,
        width='stretch',
        column_config={
            "id":                  st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "descripcion":         st.column_config.TextColumn("Descripción", disabled=True, width="large"),
            "codigo_flexxus":      st.column_config.TextColumn("Código Flexxus", help="Completá si el matching fue incorrecto"),
            "cantidad":            st.column_config.NumberColumn("Cant.", format="%d"),
            "precio_usd":          st.column_config.NumberColumn("Precio USD", format="$%.2f"),
            "subtotal_usd":        st.column_config.NumberColumn("Subtotal USD", format="$%.2f", disabled=True),
            "estado":              st.column_config.SelectboxColumn("Estado", options=["pendiente","confirmado","descartado"]),
            "stock_fr_disponible": st.column_config.CheckboxColumn("⚠️ FR disp.", disabled=True),
            "texto_original":      st.column_config.TextColumn("Texto original", disabled=True),
        },
        key="editor_borrador"
    )

    col_s, col_del, col_match, _ = st.columns([2, 2, 2, 4])

    with col_s:
        if st.button("💾 Guardar cambios", width='stretch', type="primary"):
            _guardar_cambios_borrador(df_edit, df_editado)
            st.success("✅ Guardado")
            st.rerun()

    with col_del:
        if st.button("🗑️ Limpiar descartados", width='stretch'):
            execute_query(
                "UPDATE borrador_pedido SET estado='descartado' WHERE estado='pendiente' AND codigo_flexxus IS NULL",
                fetch=False
            )
            st.rerun()

    with col_match:
        if st.button("🔍 Re-matching pendientes", width='stretch'):
            _rematching_pendientes()
            st.rerun()

    # Panel de matching manual para pendientes sin código
    pendientes_sin_cod = df[(df["estado"] == "pendiente") & (df["codigo_flexxus"].isna())]
    if not pendientes_sin_cod.empty:
        st.markdown("---")
        st.markdown(f"### 🔍 {len(pendientes_sin_cod)} ítems sin código — Matching manual")
        for _, row in pendientes_sin_cod.iterrows():
            with st.expander(f"⏳ {row['texto_original']}", expanded=False):
                _panel_matching_manual(int(row["id"]), str(row["texto_original"]))


def _panel_matching_manual(item_id: int, texto: str):
    """Panel para buscar y confirmar el código de un ítem pendiente."""
    query = st.text_input("Buscar modelo", value=texto, key=f"match_q_{item_id}")
    candidatos = _buscar_mecanicos(query) if query else []

    if candidatos:
        for i, c in enumerate(candidatos[:5]):
            col_i, col_b = st.columns([5, 1])
            col_i.markdown(f"`{c['codigo']}` — {c['descripcion'][:45]} (Stock: {int(c.get('stock',0))})")
            if col_b.button("✅", key=f"confirm_{item_id}_{i}"):
                precio = float(c.get("precio_usd", 0))
                cant_row = query_to_df(f"SELECT cantidad FROM borrador_pedido WHERE id={item_id}")
                cant = int(cant_row.iloc[0]["cantidad"]) if not cant_row.empty else 1
                execute_query(
                    """UPDATE borrador_pedido
                       SET codigo_flexxus=?, descripcion=?, precio_usd=?,
                           subtotal_usd=?, tipo_codigo='mecanico',
                           match_confirmado=1, estado='confirmado',
                           actualizado_en=datetime('now')
                       WHERE id=?""",
                    (c["codigo"], c["descripcion"], precio, precio*cant, item_id),
                    fetch=False
                )
                st.success(f"✅ Confirmado: {c['codigo']}")
                st.rerun()


# ─────────────────────────────────────────────────────────────
# TAB 3 — EXPORTAR A LOTE
# ─────────────────────────────────────────────────────────────
def _tab_exportar():
    df_conf = query_to_df("""
        SELECT id, codigo_flexxus as codigo, descripcion, cantidad,
               precio_usd, subtotal_usd, stock_fr_disponible
        FROM borrador_pedido
        WHERE estado = 'confirmado' AND codigo_flexxus IS NOT NULL
        ORDER BY descripcion
    """)

    if df_conf.empty:
        st.info("No hay ítems confirmados todavía. Confirmá los ítems en **📋 Borrador actual**.")
        return

    tasa = float(get_config("tasa_usd_ars", float) or 1420)
    total = float(df_conf["subtotal_usd"].fillna(0).sum())
    tope  = float(get_config("presupuesto_lote_1", float) or 100000)

    # ── KPIs ─────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ítems confirmados", len(df_conf))
    c2.metric("Total USD", f"${total:,.0f}")
    c3.metric("Presupuesto", f"${tope:,.0f}")
    color_tope = "🔴" if total > tope else "🟢"
    c4.metric(f"{color_tope} vs presupuesto",
               f"${total - tope:+,.0f}" if total != tope else "Exacto")

    if total > tope:
        exceso = total - tope
        st.error(
            f"⚠️ El borrador supera el presupuesto en **USD {exceso:,.0f}**. "
            "El sistema puede recortar automáticamente por ROI."
        )
        if st.button("🤖 Optimizar por ROI (recortar hasta presupuesto)", type="primary"):
            df_conf = _optimizar_roi(df_conf, tope)
            st.success(f"✅ Optimizado: {len(df_conf)} ítems · USD {df_conf['subtotal_usd'].sum():,.0f}")

    # ── Tabla de ítems con advertencias FR ───────────────────
    con_fr = df_conf[df_conf["stock_fr_disponible"] == 1]
    if not con_fr.empty:
        st.warning(
            f"⚠️ **{len(con_fr)} ítems** tienen stock FR disponible — "
            "considerá no pedirlos si el FR cubre la demanda."
        )

    st.dataframe(
        df_conf[["codigo", "descripcion", "cantidad", "precio_usd", "subtotal_usd", "stock_fr_disponible"]],
        hide_index=True, width='stretch',
        column_config={
            "codigo":              st.column_config.TextColumn("Código"),
            "descripcion":         st.column_config.TextColumn("Artículo", width="large"),
            "cantidad":            st.column_config.NumberColumn("Cant.", format="%d"),
            "precio_usd":          st.column_config.NumberColumn("USD u.", format="$%.2f"),
            "subtotal_usd":        st.column_config.NumberColumn("Subtotal USD", format="$%.2f"),
            "stock_fr_disponible": st.column_config.CheckboxColumn("⚠️ FR disp."),
        }
    )

    st.markdown("---")

    col_e1, col_e2, col_lote = st.columns(3)

    # Exportar Excel para Diego (con C/MARCO → W/F)
    with col_e1:
        buf = BytesIO()
        df_diego = df_conf[["codigo","descripcion","cantidad","precio_usd","subtotal_usd"]].copy()
        df_diego["descripcion"] = df_diego["descripcion"].str.replace(
            "C/MARCO", "W/F", regex=False
        ).str.replace("CON MARCO", "WITH FRAME", regex=False)
        df_diego.columns = ["Código","Artículo","Cantidad","Precio USD","Subtotal USD"]
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df_diego.to_excel(w, index=False, sheet_name="Pedido")
        buf.seek(0)
        fecha = datetime.now().strftime("%Y%m%d")
        st.download_button(
            "📤 Excel para Diego (C/MARCO→W/F)",
            data=buf,
            file_name=f"pedido_mecanico_{fecha}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch'
        )

    # Exportar Excel interno (con códigos Flexxus)
    with col_e2:
        buf2 = BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as w:
            df_conf.to_excel(w, index=False, sheet_name="Borrador")
        buf2.seek(0)
        st.download_button(
            "📥 Excel interno (códigos Flexxus)",
            data=buf2,
            file_name=f"borrador_flexxus_{fecha}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch'
        )

    # Pasar a lote de compra
    with col_lote:
        nombre_lote = st.text_input(
            "Nombre del lote",
            value=f"Lote Mecánico {datetime.now().strftime('%d/%m/%Y')}",
            key="nom_lote_borrador",
            label_visibility="collapsed"
        )
        if st.button("🛒 Crear lote de compra", width='stretch', type="primary"):
            _crear_lote_desde_borrador(df_conf, nombre_lote, total)
            # Marcar borrador como enviado
            execute_query(
                "UPDATE borrador_pedido SET estado='descartado' WHERE estado='confirmado'",
                fetch=False
            )
            st.success(f"✅ Lote creado: **{nombre_lote}** — USD {total:,.0f}")
            st.rerun()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _buscar_mecanicos(query: str) -> list:
    """Busca artículos MECÁNICOS (código numérico) que coincidan con el query."""
    from rapidfuzz import fuzz, process

    df = query_to_df("""
        SELECT a.codigo, a.descripcion,
               COALESCE(s.stock, 0) as stock,
               COALESCE(p.lista_1, 0) as precio_usd
        FROM articulos a
        LEFT JOIN (
            SELECT codigo, SUM(stock) as stock
            FROM stock_snapshots ss
            JOIN (SELECT codigo, MAX(fecha) mf FROM stock_snapshots GROUP BY codigo) lx
              ON ss.codigo=lx.codigo AND ss.fecha=lx.mf
            GROUP BY codigo
        ) s ON a.codigo=s.codigo
        LEFT JOIN precios p ON a.codigo=p.codigo
        WHERE UPPER(a.descripcion) LIKE 'MODULO%'
          AND COALESCE(a.en_lista_negra, 0) = 0
        ORDER BY a.descripcion
    """)

    if df.empty:
        return []

    # Filtrar solo mecánicos (código empieza con número)
    df = df[df["codigo"].apply(lambda c: str(c)[0:1].isdigit())]

    if df.empty:
        return []

    # Búsqueda fuzzy
    query_up = query.upper()
    descs = df["descripcion"].tolist()
    matches = process.extract(
        query_up, descs,
        scorer=fuzz.token_set_ratio,
        limit=10,
        score_cutoff=45
    )

    resultados = []
    for desc, score, idx in matches:
        row = df.iloc[idx]
        resultados.append({
            "codigo":      row["codigo"],
            "descripcion": row["descripcion"],
            "stock":       int(row["stock"] or 0),
            "precio_usd":  float(row["precio_usd"] or 0),
            "score":       score,
        })

    return sorted(resultados, key=lambda x: -x["score"])


def _buscar_fr_mismo_modelo(query: str) -> list:
    """Busca si el mismo modelo tiene stock en artículos FR (letra)."""
    from rapidfuzz import fuzz, process

    df = query_to_df("""
        SELECT a.codigo, a.descripcion,
               COALESCE(s.stock, 0) as stock
        FROM articulos a
        LEFT JOIN (
            SELECT codigo, SUM(stock) as stock
            FROM stock_snapshots ss
            JOIN (SELECT codigo, MAX(fecha) mf FROM stock_snapshots GROUP BY codigo) lx
              ON ss.codigo=lx.codigo AND ss.fecha=lx.mf
            GROUP BY codigo
        ) s ON a.codigo=s.codigo
        WHERE UPPER(a.descripcion) LIKE 'MODULO%'
          AND COALESCE(s.stock, 0) > 3
          AND COALESCE(a.en_lista_negra, 0) = 0
    """)

    if df.empty:
        return []

    # Solo FR (código empieza con letra)
    df = df[df["codigo"].apply(lambda c: str(c)[0:1].isalpha())]
    if df.empty:
        return []

    query_up = query.upper()
    descs = df["descripcion"].tolist()
    matches = process.extract(
        query_up, descs, scorer=fuzz.token_set_ratio, limit=3, score_cutoff=60
    )

    resultados = []
    for desc, score, idx in matches:
        row = df.iloc[idx]
        resultados.append({
            "codigo":      row["codigo"],
            "descripcion": row["descripcion"],
            "stock":       int(row["stock"] or 0),
        })
    return resultados


def _guardar_borrador_item(texto_original: str, codigo, descripcion: str,
                            cantidad: int, precio: float,
                            match_confirmado: bool,
                            stock_fr: bool = False,
                            cod_fr: str = None):
    subtotal = precio * cantidad if precio > 0 else 0
    tipo = tipo_codigo(codigo) if codigo else None
    estado = "confirmado" if (match_confirmado and codigo) else "pendiente"

    execute_query("""
        INSERT INTO borrador_pedido
        (texto_original, codigo_flexxus, descripcion, tipo_codigo,
         cantidad, precio_usd, subtotal_usd,
         match_confirmado, stock_fr_disponible, codigo_fr_alternativo,
         estado, origen)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,'web')
    """, (
        texto_original, codigo, descripcion, tipo,
        cantidad, precio, subtotal,
        1 if match_confirmado else 0,
        1 if stock_fr else 0, cod_fr,
        estado
    ), fetch=False)


def _guardar_cambios_borrador(df_orig: pd.DataFrame, df_edit: pd.DataFrame):
    """Guarda los cambios editados en la tabla."""
    for i in range(min(len(df_orig), len(df_edit))):
        item_id = int(df_orig.iloc[i]["id"])
        cod     = str(df_edit.iloc[i].get("codigo_flexxus", "") or "").strip() or None
        cant    = int(df_edit.iloc[i].get("cantidad", 0) or 0)
        precio  = float(df_edit.iloc[i].get("precio_usd", 0) or 0)
        estado  = str(df_edit.iloc[i].get("estado", "pendiente"))
        sub     = precio * cant

        execute_query("""
            UPDATE borrador_pedido
            SET codigo_flexxus=?, cantidad=?, precio_usd=?,
                subtotal_usd=?, estado=?, actualizado_en=datetime('now')
            WHERE id=?
        """, (cod, cant, precio, sub, estado, item_id), fetch=False)


def _rematching_pendientes():
    """Re-ejecuta fuzzy matching en todos los ítems pendientes sin código."""
    pendientes = query_to_df("""
        SELECT id, texto_original FROM borrador_pedido
        WHERE estado='pendiente' AND (codigo_flexxus IS NULL OR codigo_flexxus='')
    """)
    if pendientes.empty:
        return

    for _, row in pendientes.iterrows():
        candidatos = _buscar_mecanicos(str(row["texto_original"]))
        if candidatos and candidatos[0]["score"] >= 85:
            mejor = candidatos[0]
            cant_r = query_to_df(f"SELECT cantidad FROM borrador_pedido WHERE id={row['id']}")
            cant = int(cant_r.iloc[0]["cantidad"]) if not cant_r.empty else 1
            precio = float(mejor["precio_usd"])
            execute_query("""
                UPDATE borrador_pedido
                SET codigo_flexxus=?, descripcion=?, tipo_codigo='mecanico',
                    precio_usd=?, subtotal_usd=?, match_score=?,
                    match_confirmado=1, estado='confirmado',
                    actualizado_en=datetime('now')
                WHERE id=?
            """, (mejor["codigo"], mejor["descripcion"], precio,
                  precio*cant, mejor["score"], int(row["id"])), fetch=False)
    st.info(f"Re-matching completado para {len(pendientes)} ítems")


def _optimizar_roi(df: pd.DataFrame, tope: float) -> pd.DataFrame:
    """Recorta el borrador hasta el tope usando score ROI."""
    df = df.copy()
    df["precio_usd"] = df["precio_usd"].fillna(0)
    df["subtotal_usd"] = df["subtotal_usd"].fillna(0)

    # Score simple: priorizar mayor precio (mayor margen) + mayor cantidad
    df["score"] = df["precio_usd"] * 0.6 + df["cantidad"] * 0.4
    df = df.sort_values("score", ascending=False)

    seleccionados = []
    acumulado = 0.0
    for _, r in df.iterrows():
        sub = float(r["subtotal_usd"])
        if acumulado + sub <= tope:
            seleccionados.append(r)
            acumulado += sub

    return pd.DataFrame(seleccionados) if seleccionados else df.head(0)


def _crear_lote_desde_borrador(df: pd.DataFrame, nombre: str, total: float):
    """Crea un lote de compra en pedidos_lotes desde el borrador confirmado."""
    tope = float(get_config("presupuesto_lote_1", float) or 100000)

    # Insertar lote
    execute_query("""
        INSERT INTO pedidos_lotes (nombre, proveedor, tope_usd, total_usd, estado)
        VALUES (?, 'MECÁNICO', ?, ?, 'borrador')
    """, (nombre, tope, total), fetch=False)

    # Obtener ID del lote recién creado
    rows = execute_query(
        "SELECT id FROM pedidos_lotes WHERE nombre=? ORDER BY id DESC LIMIT 1",
        (nombre,)
    )
    if not rows:
        return
    lote_id = rows[0]["id"]

    # Insertar ítems
    for _, r in df.iterrows():
        execute_query("""
            INSERT INTO pedidos_items
            (lote_id, codigo, descripcion, precio_usd, cantidad, subtotal_usd)
            VALUES (?,?,?,?,?,?)
        """, (
            lote_id,
            str(r.get("codigo", "")),
            str(r.get("descripcion", "")),
            float(r.get("precio_usd", 0)),
            int(r.get("cantidad", 0)),
            float(r.get("subtotal_usd", 0))
        ), fetch=False)
