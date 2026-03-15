"""
⚠️  ARCHIVO DEPRECADO — NO USAR
Versión antigua de cotizaciones (sin tab "SKUs en Tránsito").
Usar: pages/cotizaciones.py  (versión activa v2)

ROKER NEXUS — Módulo Cotizaciones y Tránsito
Gestión completa de pedidos a China (AI-TECH / Diego).

Estados: PENDIENTE → EN TRÁNSITO → INGRESADO
Funcionalidades:
  - Importar Order List (xlsx con "AI-TECH" en nombre)
  - Fuzzy matching automático contra artículos Flexxus
  - Confirmación manual de matches dudosos
  - Marcar tránsito / Registrar ingreso (total o parcial)
  - Exportar para Diego (C/MARCO → W/F automático)
  - Fechas de cada movimiento de estado
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

from database import query_to_df, execute_query
from utils.helpers import fmt_usd, fmt_num
from importers.aitech_orderlist import (
    es_orderlist_aitech, parsear_orderlist, hacer_matching_fuzzy,
    exportar_para_diego, aplicar_conversion_wf
)


# ── Colores de estado ─────────────────────────────────────────
ESTADO_COLOR = {
    "pendiente":    "var(--nx-amber)",
    "en_transito":  "var(--nx-accent)",
    "ingresado":    "var(--nx-green)",
    "anulado":      "var(--nx-text3)",
}
ESTADO_LABEL = {
    "pendiente":    "⏳ Pendiente",
    "en_transito":  "✈️ En Tránsito",
    "ingresado":    "✅ Ingresado",
    "anulado":      "❌ Anulado",
}


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        ✈️ Cotizaciones y Tránsito
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:20px">
        Pedidos a China — AI-TECH / Diego
    </p>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📥 Nuevo Pedido",
        "✈️ En Tránsito",
        "✅ Historial",
    ])

    with tabs[0]:
        _tab_nuevo_pedido()

    with tabs[1]:
        _tab_en_transito()

    with tabs[2]:
        _tab_historial()


# ─────────────────────────────────────────────────────────────
# TAB 1 — NUEVO PEDIDO
# ─────────────────────────────────────────────────────────────
def _tab_nuevo_pedido():
    st.markdown("### Cargar Order List de Diego")
    st.markdown(
        "<span style='font-size:13px;color:var(--nx-text2)'>"
        "Subí el archivo xlsx que manda Diego. El sistema detecta automáticamente "
        "que es de AI-TECH si el nombre contiene esa palabra.</span>",
        unsafe_allow_html=True
    )

    archivo = st.file_uploader(
        "Archivo xlsx / xls",
        type=["xlsx", "xls"],
        key="uploader_cotizacion"
    )

    if not archivo:
        st.markdown("""
        <div style="height:120px;display:flex;align-items:center;justify-content:center;
                    color:var(--nx-text3);font-size:13px;border:1px dashed var(--nx-border);
                    border-radius:var(--nx-radius-lg);margin-top:16px">
            Arrastrá el Order List acá · Debe contener "AI-TECH" en el nombre
        </div>
        """, unsafe_allow_html=True)
        return

    # Validar que sea AI-TECH
    if not es_orderlist_aitech(archivo.name):
        st.warning(
            f"⚠️ El archivo **{archivo.name}** no parece ser un Order List de AI-TECH. "
            "El nombre debe contener la palabra 'AI-TECH'."
        )
        return

    # Parsear
    with st.spinner("Leyendo archivo..."):
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(archivo.read())
            tmp_path = tmp.name

        try:
            datos = parsear_orderlist(tmp_path)
        finally:
            os.unlink(tmp_path)

    if not datos["items"]:
        st.error("No se encontraron ítems en el archivo. Verificá el formato.")
        return

    # Preview del pedido
    st.success(f"✅ **Invoice #{datos['invoice_id']}** — {datos['total_items']} ítems · Total: {fmt_usd(datos['total_usd'])}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ítems", datos["total_items"])
    col2.metric("Total USD", fmt_usd(datos["total_usd"]))
    col3.metric("Invoice", f"#{datos['invoice_id']}")
    col4.metric("Fecha", datos["fecha"])

    # Hacer matching fuzzy con artículos Flexxus
    with st.spinner("Buscando equivalencias en Flexxus..."):
        df_arts = query_to_df("SELECT codigo, descripcion FROM articulos LIMIT 5000")
        items_con_match = hacer_matching_fuzzy(datos["items"], df_arts)

    # Separar automáticos vs requieren confirmación
    auto_ok = [i for i in items_con_match if i["match_confirmado"]]
    a_confirmar = [i for i in items_con_match if not i["match_confirmado"] and i["codigo_flexxus"]]
    sin_match = [i for i in items_con_match if not i["codigo_flexxus"]]

    st.markdown("---")
    st.markdown("### Verificación de matches")

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Match automático", len(auto_ok))
    c2.metric("⚠️ A confirmar", len(a_confirmar))
    c3.metric("❓ Sin match", len(sin_match))

    # Tabla para confirmar matches dudosos
    if a_confirmar:
        st.markdown("#### ⚠️ Confirmar matches dudosos")
        st.markdown(
            "<span style='font-size:12px;color:var(--nx-text2)'>Estos ítems tienen coincidencia parcial. "
            "Verificá que el código Flexxus sea correcto.</span>",
            unsafe_allow_html=True
        )

        df_confirmar = pd.DataFrame([{
            "✓": True,
            "Modelo Order List":    i["modelo_universal"],
            "Código Flexxus":       i["codigo_flexxus"] or "",
            "Descripción Flexxus":  i["descripcion_flexxus"] or "",
            "Score":                i["match_score"],
            "Cant.":                i["cantidad_pedida"],
            "Precio USD":           i["precio_usd"],
            "_idx":                 items_con_match.index(i),
        } for i in a_confirmar])

        df_edit = st.data_editor(
            df_confirmar.drop(columns=["_idx"]),
            hide_index=True,
            width="stretch",
            column_config={
                "✓": st.column_config.CheckboxColumn("Confirmar", default=True),
                "Score": st.column_config.NumberColumn("Score", format="%d%%"),
                "Precio USD": st.column_config.NumberColumn("Precio", format="$%.2f"),
                "Cant.": st.column_config.NumberColumn("Cant.", format="%d"),
            }
        )
        # Actualizar confirmaciones
        for i, row in df_edit.iterrows():
            orig_idx = df_confirmar.iloc[i]["_idx"]
            items_con_match[orig_idx]["match_confirmado"] = bool(row["✓"])

    # Tabla preview completa
    with st.expander(f"Ver todos los {datos['total_items']} ítems", expanded=False):
        df_preview = pd.DataFrame([{
            "Brand":        i["brand"],
            "Modelo":       i["modelo_universal"][:40] if i["modelo_universal"] else "",
            "Spec":         i["specification"],
            "Cant.":        i["cantidad_pedida"],
            "Precio":       i["precio_usd"],
            "Subtotal":     i["subtotal_usd"],
            "Flexxus":      i["codigo_flexxus"] or "❓",
            "Score":        i["match_score"] if i["codigo_flexxus"] else 0,
        } for i in items_con_match])
        st.dataframe(df_preview, hide_index=True, width='stretch')

    st.markdown("---")

    # Botón guardar
    col_save, col_export, _ = st.columns([2, 2, 4])

    with col_save:
        if st.button("💾 Guardar pedido", type="primary", width='stretch'):
            _guardar_cotizacion(datos, items_con_match)
            st.success(f"✅ Pedido #{datos['invoice_id']} guardado como PENDIENTE")
            st.rerun()

    with col_export:
        df_diego = exportar_para_diego(items_con_match, datos["invoice_id"])
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_diego.to_excel(writer, index=False, sheet_name="Order")
        buf.seek(0)
        st.download_button(
            "📤 Exportar para Diego",
            data=buf,
            file_name=f"AI-TECH_{datos['invoice_id']}_WF.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
        )


# ─────────────────────────────────────────────────────────────
# TAB 2 — EN TRÁNSITO
# ─────────────────────────────────────────────────────────────
def _tab_en_transito():
    df_cots = query_to_df("""
        SELECT id, invoice_id, fecha, total_usd, estado,
               fecha_pendiente, fecha_transito, fecha_ingresado,
               filename, notas
        FROM cotizaciones
        WHERE estado IN ('pendiente', 'en_transito')
        ORDER BY fecha DESC
    """)

    if df_cots.empty:
        st.info("No hay pedidos pendientes ni en tránsito. Cargá un Order List en la pestaña **Nuevo Pedido**.")
        return

    for _, cot in df_cots.iterrows():
        _card_cotizacion_activa(cot)


def _card_cotizacion_activa(cot):
    estado = str(cot.get("estado", "pendiente"))
    color = ESTADO_COLOR.get(estado, "var(--nx-text3)")
    label = ESTADO_LABEL.get(estado, estado)
    cot_id = int(cot["id"])

    # Fechas de movimiento
    fechas_html = ""
    if cot.get("fecha_pendiente"):
        fechas_html += f"📅 Creado: {str(cot['fecha_pendiente'])[:10]} &nbsp;"
    if cot.get("fecha_transito"):
        fechas_html += f"✈️ Tránsito: {str(cot['fecha_transito'])[:10]} &nbsp;"
    if cot.get("fecha_ingresado"):
        fechas_html += f"✅ Ingresado: {str(cot['fecha_ingresado'])[:10]}"

    with st.container():
        st.markdown(f"""
        <div class="nx-card" style="border-left:3px solid {color};margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:15px;font-weight:700;color:var(--nx-text)">
                    Invoice #{cot.get('invoice_id','?')}
                </span>
                <span style="font-size:12px;color:{color};font-weight:600;text-transform:uppercase">
                    {label}
                </span>
            </div>
            <div style="font-size:12px;color:var(--nx-text2);margin-top:4px;display:flex;gap:16px">
                <span>💰 {fmt_usd(cot.get('total_usd', 0))}</span>
                <span>📄 {cot.get('filename','') or ''}</span>
            </div>
            <div style="font-size:11px;color:var(--nx-text3);margin-top:4px">{fechas_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Botones de acción según estado
        col_b1, col_b2, col_b3, col_b4, _ = st.columns([2, 2, 2, 2, 4])

        with col_b1:
            if estado == "pendiente":
                if st.button("✈️ Marcar Tránsito", key=f"tran_{cot_id}", width='stretch'):
                    _cambiar_estado(cot_id, "en_transito")
                    st.rerun()
            elif estado == "en_transito":
                if st.button("✅ Ingresar Todo", key=f"ing_{cot_id}", width='stretch', type="primary"):
                    _ingresar_completo(cot_id)
                    st.rerun()

        with col_b2:
            if estado == "en_transito":
                if st.button("📦 Ingreso Parcial", key=f"parc_{cot_id}", width='stretch'):
                    st.session_state[f"mostrar_parcial_{cot_id}"] = True

        with col_b3:
            if st.button("👁 Ver ítems", key=f"ver_{cot_id}", width='stretch'):
                st.session_state[f"mostrar_items_{cot_id}"] = not st.session_state.get(f"mostrar_items_{cot_id}", False)

        with col_b4:
            if estado != "anulado":
                if st.button("❌ Anular", key=f"anul_{cot_id}", width='stretch'):
                    _cambiar_estado(cot_id, "anulado")
                    st.rerun()

        # Panel de ítems
        if st.session_state.get(f"mostrar_items_{cot_id}"):
            _panel_items(cot_id, estado)

        # Panel de ingreso parcial
        if st.session_state.get(f"mostrar_parcial_{cot_id}"):
            _panel_ingreso_parcial(cot_id)


def _panel_items(cot_id: int, estado: str):
    df_items = query_to_df("""
        SELECT brand, modelo_universal, specification, quality,
               cantidad_pedida, cantidad_recibida, precio_usd, subtotal_usd,
               codigo_flexxus, match_score, match_confirmado, estado_item
        FROM cotizacion_items
        WHERE cotizacion_id = ?
        ORDER BY seccion, rowid
    """, (cot_id,))

    if df_items.empty:
        st.info("Sin ítems registrados.")
        return

    st.dataframe(
        df_items,
        hide_index=True,
        width='stretch',
        column_config={
            "cantidad_pedida":  st.column_config.NumberColumn("Pedido", format="%d"),
            "cantidad_recibida": st.column_config.NumberColumn("Recibido", format="%d"),
            "precio_usd":       st.column_config.NumberColumn("Precio USD", format="$%.2f"),
            "subtotal_usd":     st.column_config.NumberColumn("Subtotal", format="$%.2f"),
            "match_score":      st.column_config.NumberColumn("Match%", format="%d"),
            "match_confirmado": st.column_config.CheckboxColumn("Confirmado"),
        }
    )


def _panel_ingreso_parcial(cot_id: int):
    st.markdown("#### 📦 Registrar ingreso parcial")

    df_items = query_to_df("""
        SELECT id, modelo_universal, cantidad_pedida, cantidad_recibida
        FROM cotizacion_items
        WHERE cotizacion_id = ? AND cantidad_recibida < cantidad_pedida
        ORDER BY rowid
    """, (cot_id,))

    if df_items.empty:
        st.info("Todos los ítems ya fueron ingresados.")
        st.session_state[f"mostrar_parcial_{cot_id}"] = False
        return

    df_items["recibir_ahora"] = df_items["cantidad_pedida"] - df_items["cantidad_recibida"]

    df_edit = st.data_editor(
        df_items[["modelo_universal", "cantidad_pedida", "cantidad_recibida", "recibir_ahora"]],
        hide_index=True,
        width='stretch',
        column_config={
            "modelo_universal":   st.column_config.TextColumn("Modelo", disabled=True),
            "cantidad_pedida":    st.column_config.NumberColumn("Pedido", format="%d", disabled=True),
            "cantidad_recibida":  st.column_config.NumberColumn("Ya recibido", format="%d", disabled=True),
            "recibir_ahora":      st.column_config.NumberColumn("Recibir ahora", format="%d"),
        }
    )

    col_ok, col_cancel, _ = st.columns([2, 2, 6])
    with col_ok:
        if st.button("✅ Registrar ingreso", key=f"ok_parc_{cot_id}", type="primary", width='stretch'):
            for i, row in df_edit.iterrows():
                item_id = int(df_items.iloc[i]["id"])
                nueva_cantidad = int(df_items.iloc[i]["cantidad_recibida"]) + int(row["recibir_ahora"])
                execute_query(
                    "UPDATE cotizacion_items SET cantidad_recibida=? WHERE id=?",
                    (nueva_cantidad, item_id), fetch=False
                )
            # Si todos los ítems están completados, marcar cotización como ingresada
            _verificar_ingreso_completo(cot_id)
            st.session_state[f"mostrar_parcial_{cot_id}"] = False
            st.success("✅ Ingreso parcial registrado")
            st.rerun()

    with col_cancel:
        if st.button("Cancelar", key=f"cancel_parc_{cot_id}", width='stretch'):
            st.session_state[f"mostrar_parcial_{cot_id}"] = False
            st.rerun()


# ─────────────────────────────────────────────────────────────
# TAB 3 — HISTORIAL
# ─────────────────────────────────────────────────────────────
def _tab_historial():
    df = query_to_df("""
        SELECT id, invoice_id, fecha, total_usd, estado,
               fecha_pendiente, fecha_transito, fecha_ingresado,
               filename
        FROM cotizaciones
        ORDER BY fecha DESC
        LIMIT 50
    """)

    if df.empty:
        st.info("No hay cotizaciones registradas todavía.")
        return

    # Resumen rápido
    total_ingresado = df[df["estado"] == "ingresado"]["total_usd"].sum()
    total_transito = df[df["estado"] == "en_transito"]["total_usd"].sum()
    total_pendiente = df[df["estado"] == "pendiente"]["total_usd"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Ingresado (total)", fmt_usd(total_ingresado))
    c2.metric("✈️ En tránsito", fmt_usd(total_transito))
    c3.metric("⏳ Pendiente", fmt_usd(total_pendiente))

    st.markdown("---")

    # Tabla con todas las cotizaciones
    df_show = df.copy()
    df_show["estado"] = df_show["estado"].map(ESTADO_LABEL).fillna(df_show["estado"])
    df_show["total_usd"] = df_show["total_usd"].apply(fmt_usd)

    st.dataframe(
        df_show[[
            "invoice_id", "fecha", "total_usd", "estado",
            "fecha_pendiente", "fecha_transito", "fecha_ingresado"
        ]],
        hide_index=True,
        width='stretch',
        column_config={
            "invoice_id":       st.column_config.TextColumn("Invoice"),
            "fecha":            st.column_config.TextColumn("Fecha"),
            "total_usd":        st.column_config.TextColumn("Total"),
            "estado":           st.column_config.TextColumn("Estado"),
            "fecha_pendiente":  st.column_config.TextColumn("Creado"),
            "fecha_transito":   st.column_config.TextColumn("Tránsito"),
            "fecha_ingresado":  st.column_config.TextColumn("Ingresado"),
        }
    )


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _guardar_cotizacion(datos: dict, items: list):
    """Guarda la cotización y sus ítems en la base de datos."""
    now = datetime.now().isoformat()

    # Insertar cotización
    result = execute_query(
        """INSERT INTO cotizaciones
           (proveedor, invoice_id, filename, fecha, total_usd, estado, fecha_pendiente)
           VALUES (?, ?, ?, ?, ?, 'pendiente', ?)""",
        (
            datos["proveedor"],
            datos["invoice_id"],
            datos["filename"],
            datos["fecha"],
            datos["total_usd"],
            now,
        ),
        fetch=False
    )

    # Obtener el ID insertado
    rows = execute_query(
        "SELECT id FROM cotizaciones WHERE invoice_id=? ORDER BY id DESC LIMIT 1",
        (datos["invoice_id"],)
    )
    if not rows:
        return
    cot_id = rows[0]["id"]

    # Insertar ítems
    for item in items:
        execute_query(
            """INSERT INTO cotizacion_items
               (cotizacion_id, brand, codigo_proveedor, modelo_universal, modelo_sticker,
                specification, type_lcd, quality, colour, seccion,
                cantidad_pedida, cantidad_recibida, precio_usd, subtotal_usd,
                codigo_flexxus, descripcion_flexxus, match_score, match_confirmado,
                estado_item)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?,?)""",
            (
                cot_id,
                item.get("brand", ""),
                item.get("codigo_proveedor", ""),
                item.get("modelo_universal", ""),
                item.get("modelo_sticker", ""),
                item.get("specification", ""),
                item.get("type", ""),
                item.get("quality", ""),
                item.get("colour", ""),
                item.get("seccion", ""),
                item.get("cantidad_pedida", 0),
                item.get("precio_usd", 0.0),
                item.get("subtotal_usd", 0.0),
                item.get("codigo_flexxus"),
                item.get("descripcion_flexxus"),
                item.get("match_score", 0),
                1 if item.get("match_confirmado") else 0,
                "pendiente",
            ),
            fetch=False
        )


def _cambiar_estado(cot_id: int, nuevo_estado: str):
    """Cambia el estado de una cotización y registra la fecha."""
    now = datetime.now().isoformat()
    campo_fecha = {
        "en_transito": "fecha_transito",
        "ingresado":   "fecha_ingresado",
        "anulado":     None,
    }.get(nuevo_estado)

    if campo_fecha:
        execute_query(
            f"UPDATE cotizaciones SET estado=?, {campo_fecha}=? WHERE id=?",
            (nuevo_estado, now, cot_id), fetch=False
        )
    else:
        execute_query(
            "UPDATE cotizaciones SET estado=? WHERE id=?",
            (nuevo_estado, cot_id), fetch=False
        )

    # Si pasa a tránsito, actualizar todos los ítems
    if nuevo_estado == "en_transito":
        execute_query(
            "UPDATE cotizacion_items SET estado_item='en_transito' WHERE cotizacion_id=?",
            (cot_id,), fetch=False
        )


def _ingresar_completo(cot_id: int):
    """Marca todos los ítems como ingresados con cantidad completa."""
    execute_query(
        """UPDATE cotizacion_items
           SET cantidad_recibida = cantidad_pedida, estado_item = 'ingresado'
           WHERE cotizacion_id = ?""",
        (cot_id,), fetch=False
    )
    _cambiar_estado(cot_id, "ingresado")


def _verificar_ingreso_completo(cot_id: int):
    """Si todos los ítems tienen cantidad_recibida >= cantidad_pedida, cierra la cotización."""
    rows = execute_query(
        """SELECT COUNT(*) as pendientes
           FROM cotizacion_items
           WHERE cotizacion_id = ? AND cantidad_recibida < cantidad_pedida""",
        (cot_id,)
    )
    if rows and rows[0]["pendientes"] == 0:
        _cambiar_estado(cot_id, "ingresado")
