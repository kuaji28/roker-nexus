"""
ROKER NEXUS — Página: Gestión de Compras
Lotes de pedido, sugerencias por IA, topes USD, exportación.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from database import query_to_df, execute_query
from utils.helpers import fmt_usd, fmt_num
from config import TOPE_USD_DEFAULT, LOTES_COMPRA
from importers.flexxus_optimizacion import ImportadorOptimizacion


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        🛒 Gestión de Compras
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:20px">
        Armado de lotes, sugerencias inteligentes y exportación
    </p>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📋 Nuevo Lote",
        "📦 Lotes Activos",
        "🚢 En Tránsito",
        "💸 Oportunidades Perdidas",
    ])

    # ── Tab: Nuevo Lote ───────────────────────────────────────
    with tabs[0]:
        col_conf, col_prev = st.columns([1, 2])

        with col_conf:
            st.markdown("### Configurar lote")
            nombre_lote = st.text_input("Nombre del lote", value=f"Lote {datetime.now().strftime('%d/%m/%Y')}")
            proveedor = st.selectbox("Proveedor", ["TODOS", "MECÁNICO", "FR (AITECH)", "AI-TECH", "Otro"])
            tope_usd = st.number_input(
                "Tope USD",
                min_value=0,
                max_value=100000,
                value=TOPE_USD_DEFAULT.get("Lote 1", 5000),
                step=500,
            )

            incluir = st.multiselect(
                "Incluir artículos",
                ["Bajo stock mínimo", "Stock en cero", "Demanda alta", "Cotización AITECH"],
                default=["Bajo stock mínimo", "Stock en cero"],
            )

            modo_ia = st.radio(
                "Modo sugerencia",
                ["Por fórmula (rápido)", "Con IA Claude (inteligente)"],
                index=0,
            )

            if st.button("⚡ Generar sugerencias", width="stretch", type="primary"):
                st.session_state["generar_lote"] = {
                    "nombre": nombre_lote,
                    "proveedor": proveedor,
                    "tope": tope_usd,
                    "incluir": incluir,
                    "modo_ia": modo_ia,
                }

        with col_prev:
            if "generar_lote" in st.session_state:
                config = st.session_state["generar_lote"]
                st.markdown(f"### Sugerencias — {config['nombre']}")
                st.markdown(f"<span style='font-size:12px;color:var(--nx-text2)'>Tope: <b>USD {config['tope']:,}</b> · Proveedor: <b>{config['proveedor']}</b></span>", unsafe_allow_html=True)

                with st.spinner("Calculando..."):
                    imp = ImportadorOptimizacion()
                    df_sug = imp.get_sugerencias_compra(tope_usd=config["tope"], proveedor=config.get("proveedor","TODOS"))

                if df_sug.empty:
                    st.info("Sin sugerencias. Cargá primero el archivo de Optimización de Stock.")
                else:
                    total_usd = df_sug.get("subtotal_usd", pd.Series()).sum()
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("Artículos sugeridos", len(df_sug))
                    col_m2.metric("Total estimado", fmt_usd(total_usd))
                    col_m3.metric("Tope restante", fmt_usd(max(0, config["tope"] - total_usd)))

                    if "Con IA Claude" in config.get("modo_ia", ""):
                        with st.spinner("🤖 Claude analizando el lote..."):
                            from modules.ia_engine import motor_ia
                            analisis = motor_ia.sugerir_lote_compra(df_sug, config["tope"])
                        st.info(analisis)

                    # Tabla editable
                    cols_show = [c for c in [
                        "codigo", "descripcion", "stock_actual",
                        "stock_optimo", "a_pedir", "costo_reposicion", "subtotal_usd"
                    ] if c in df_sug.columns]

                    df_edit = st.data_editor(
                        df_sug[cols_show].copy(),
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "codigo": st.column_config.TextColumn("Código"),
                            "descripcion": st.column_config.TextColumn("Artículo", width="large"),
                            "stock_actual": st.column_config.NumberColumn("Stock", format="%d"),
                            "stock_optimo": st.column_config.NumberColumn("Óptimo", format="%d"),
                            "a_pedir": st.column_config.NumberColumn("A pedir", format="%d"),
                            "costo_reposicion": st.column_config.NumberColumn("Precio USD", format="$%.2f"),
                            "subtotal_usd": st.column_config.NumberColumn("Subtotal USD", format="$%.2f"),
                        }
                    )

                    col_save, col_exp, _ = st.columns([2, 2, 4])
                    with col_save:
                        if st.button("💾 Guardar lote", width="stretch"):
                            _guardar_lote(config, df_edit)
                            st.success("✅ Lote guardado")
                    with col_exp:
                        if st.button("📤 Exportar Excel", width="stretch"):
                            _exportar_lote_excel(df_edit, config["nombre"])
            else:
                st.markdown("""
                <div style="height:200px;display:flex;align-items:center;justify-content:center;
                            color:var(--nx-text3);font-size:14px;border:1px dashed var(--nx-border);
                            border-radius:var(--nx-radius-lg)">
                    Configurá el lote y clickeá "Generar sugerencias"
                </div>
                """, unsafe_allow_html=True)

    # ── Tab: Lotes Activos ────────────────────────────────────
    with tabs[1]:
        df_lotes = query_to_df("""
            SELECT l.id, l.nombre, l.proveedor, l.tope_usd, l.total_usd,
                   l.estado, l.fecha_creado,
                   COUNT(i.id) as items
            FROM pedidos_lotes l
            LEFT JOIN pedidos_items i ON l.id = i.lote_id
            GROUP BY l.id
            ORDER BY l.fecha_creado DESC
        """)

        if df_lotes.empty:
            st.info("No hay lotes creados todavía. Creá el primero en la pestaña **Nuevo Lote**.")
        else:
            for _, row in df_lotes.iterrows():
                _card_lote(row)

    # ── Tab: En Tránsito ──────────────────────────────────────
    with tabs[2]:
        df_tr = query_to_df("""
            SELECT t.*, l.nombre as lote_nombre
            FROM pedidos_transito t
            LEFT JOIN pedidos_lotes l ON t.lote_id = l.id
            ORDER BY t.fecha_pedido DESC
        """)

        if df_tr.empty:
            st.info("No hay pedidos en tránsito registrados.")
        else:
            for _, row in df_tr.iterrows():
                _card_transito(row)

    # ── Tab: Oportunidades Perdidas ───────────────────────────
    with tabs[3]:
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:16px">
            Artículos que tuvieron quiebre de stock y probablemente perdiste ventas.
            Se calcula cruzando stock=0 con demanda histórica.
        </div>
        """, unsafe_allow_html=True)

        df_op = query_to_df("""
            SELECT
                a.codigo, a.descripcion, a.marca,
                o.demanda_promedio,
                o.costo_reposicion,
                s.stock,
                s.fecha as fecha_quiebre
            FROM articulos a
            JOIN optimizacion o ON a.codigo = o.codigo
            JOIN (
                SELECT codigo, deposito, MAX(fecha) as mf
                FROM stock_snapshots GROUP BY codigo, deposito
            ) latest ON a.codigo = latest.codigo
            JOIN stock_snapshots s ON a.codigo = s.codigo AND s.fecha = latest.mf
            WHERE s.stock = 0
              AND o.demanda_promedio > 0
              AND a.en_lista_negra = 0
            ORDER BY o.demanda_promedio DESC
            LIMIT 50
        """)

        if df_op.empty:
            st.success("✅ Sin oportunidades perdidas detectadas (necesitás cargar datos de stock y optimización).")
        else:
            df_op["venta_perdida_usd"] = df_op["demanda_promedio"] * df_op["costo_reposicion"]
            total_perdido = df_op["venta_perdida_usd"].sum()
            st.error(f"💸 Oportunidad perdida estimada: **{fmt_usd(total_perdido)}/mes** en {len(df_op)} artículos")
            st.dataframe(df_op, width="stretch", hide_index=True)


def _card_lote(row):
    estado_color = {
        "borrador": "var(--nx-amber)",
        "enviado": "var(--nx-accent)",
        "confirmado": "var(--nx-green)",
    }.get(str(row.get("estado", "")), "var(--nx-text3)")

    with st.container():
        st.markdown(f"""
        <div class="nx-card" style="border-left:3px solid {estado_color}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:14px;font-weight:600;color:var(--nx-text)">
                    {row.get('nombre','')}
                </span>
                <span style="font-size:12px;color:{estado_color};font-weight:500;text-transform:uppercase">
                    {row.get('estado','')}
                </span>
            </div>
            <div style="font-size:12px;color:var(--nx-text2);margin-top:6px;display:flex;gap:20px">
                <span>🏭 {row.get('proveedor','')}</span>
                <span>📦 {row.get('items',0)} artículos</span>
                <span>💰 Tope: {fmt_usd(row.get('tope_usd',0))}</span>
                <span>📅 {str(row.get('fecha_creado',''))[:10]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _card_transito(row):
    with st.container():
        st.markdown(f"""
        <div class="nx-card" style="border-left:3px solid var(--nx-accent)">
            <div style="font-size:14px;font-weight:600;color:var(--nx-text)">
                {row.get('lote_nombre','')} — {row.get('invoice_id','')}
            </div>
            <div style="font-size:12px;color:var(--nx-text2);margin-top:6px;display:flex;gap:20px">
                <span>🚢 {row.get('estado','')}</span>
                <span>💰 {fmt_usd(row.get('total_usd',0))}</span>
                <span>📅 Pedido: {str(row.get('fecha_pedido',''))[:10]}</span>
                <span>📦 Estimado: {str(row.get('fecha_estimada',''))[:10]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _guardar_lote(config: dict, df: pd.DataFrame):
    from database import execute_query
    now = datetime.now().isoformat()
    cur = execute_query(
        """INSERT INTO pedidos_lotes (nombre, proveedor, tope_usd, total_usd, estado)
           VALUES (?, ?, ?, ?, 'borrador')""",
        (config["nombre"], config["proveedor"],
         config["tope"], float(df.get("subtotal_usd", pd.Series()).sum())),
        fetch=False
    )


def _exportar_lote_excel(df: pd.DataFrame, nombre: str):
    from io import BytesIO
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Lote")
    buf.seek(0)
    fecha = datetime.now().strftime("%Y%m%d")
    st.download_button(
        f"⬇️ Descargar {nombre}_{fecha}.xlsx",
        data=buf,
        file_name=f"lote_{fecha}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
