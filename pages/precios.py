"""
ROKER NEXUS — Página: Precios & MercadoLibre
Comparador de precios, liquidación de clavos, links ML.
"""
import streamlit as st
import pandas as pd
from database import query_to_df, execute_query
from utils.helpers import fmt_usd, fmt_ars, fmt_num, usd_a_ars
from config import MONEDA_USD_ARS


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        💰 Precios & MercadoLibre
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:20px">
        Lista 1 (mayorista) vs Lista 4 (MercadoLibre) · Liquidación de clavos
    </p>
    """, unsafe_allow_html=True)

    # Tipo de cambio actualizable
    col_tc, _ = st.columns([2, 6])
    with col_tc:
        tasa = st.number_input(
            "💱 USD/ARS",
            min_value=100.0,
            max_value=99999.0,
            value=float(MONEDA_USD_ARS),
            step=50.0,
            help="Tipo de cambio para convertir precios USD → ARS",
        )

    tabs = st.tabs([
        "📊 Comparador L1 vs ML",
        "🗑️ Liquidación de clavos",
        "🔍 Buscar artículo",
    ])

    # ── Tab: Comparador ───────────────────────────────────────
    with tabs[0]:
        st.markdown("### Lista 1 (mayorista) vs Lista 4 (MercadoLibre)")

        df = query_to_df("""
            SELECT
                p.codigo, a.descripcion, a.marca,
                p.lista_1, p.lista_4,
                s.stock
            FROM precios p
            JOIN (
                SELECT codigo, MAX(fecha) as mf FROM precios GROUP BY codigo
            ) latest ON p.codigo=latest.codigo AND p.fecha=latest.mf
            LEFT JOIN articulos a ON p.codigo=a.codigo
            LEFT JOIN (
                SELECT codigo, SUM(stock) as stock
                FROM stock_snapshots
                JOIN (
                    SELECT codigo, deposito, MAX(fecha) as mf
                    FROM stock_snapshots GROUP BY codigo, deposito
                ) lx ON stock_snapshots.codigo=lx.codigo AND stock_snapshots.deposito=lx.deposito AND stock_snapshots.fecha=lx.mf
                GROUP BY codigo
            ) s ON p.codigo=s.codigo
            WHERE COALESCE(a.en_lista_negra,0)=0
            ORDER BY p.lista_1 DESC
        """)

        if df.empty:
            st.info("Sin datos de precios. Cargá el archivo Lista de Precios desde 📥 Cargar Archivos.")
        else:
            # Filtros
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                marca_filter = st.multiselect(
                    "Marca",
                    options=sorted(df["marca"].dropna().unique().tolist()),
                )
            with col_f2:
                sin_ml = st.checkbox("Solo sin precio ML (Lista 4 = 0)", value=False)
            with col_f3:
                con_stock = st.checkbox("Solo con stock > 0", value=False)

            df_show = df.copy()
            if marca_filter:
                df_show = df_show[df_show["marca"].isin(marca_filter)]
            if sin_ml:
                df_show = df_show[df_show["lista_4"] == 0]
            if con_stock:
                df_show = df_show[df_show["stock"] > 0]

            # Calcular diferencia
            df_show["dif_usd"] = df_show["lista_4"] - df_show["lista_1"]
            df_show["lista_1_ars"] = df_show["lista_1"].apply(lambda x: usd_a_ars(x, tasa))
            df_show["lista_4_ars"] = df_show["lista_4"].apply(lambda x: usd_a_ars(x, tasa))

            st.markdown(f"**{len(df_show)} artículos** · {int((df_show['lista_4']==0).sum())} sin precio ML")

            st.dataframe(
                df_show[[
                    "codigo", "descripcion", "marca", "stock",
                    "lista_1", "lista_1_ars", "lista_4", "lista_4_ars", "dif_usd"
                ]],
                width="stretch",
                hide_index=True,
                column_config={
                    "codigo": st.column_config.TextColumn("Código"),
                    "descripcion": st.column_config.TextColumn("Artículo", width="large"),
                    "marca": st.column_config.TextColumn("Marca"),
                    "stock": st.column_config.NumberColumn("Stock", format="%d"),
                    "lista_1": st.column_config.NumberColumn("L1 USD", format="$%.2f"),
                    "lista_1_ars": st.column_config.NumberColumn("L1 ARS", format="$%.0f"),
                    "lista_4": st.column_config.NumberColumn("ML USD", format="$%.2f"),
                    "lista_4_ars": st.column_config.NumberColumn("ML ARS", format="$%.0f"),
                    "dif_usd": st.column_config.NumberColumn("Dif USD", format="$%.2f"),
                }
            )

    # ── Tab: Clavos ───────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 🗑️ Liquidación de clavos")
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:16px">
            Artículos con stock alto pero demanda muy baja — candidatos a liquidar.
        </div>
        """, unsafe_allow_html=True)

        df_clavos = query_to_df("""
            SELECT
                a.codigo, a.descripcion, a.marca,
                s.stock,
                COALESCE(o.demanda_promedio,0) as demanda_prom,
                p.lista_1, p.lista_4
            FROM articulos a
            JOIN (
                SELECT codigo, SUM(stock) as stock
                FROM stock_snapshots
                JOIN (
                    SELECT codigo, deposito, MAX(fecha) as mf
                    FROM stock_snapshots GROUP BY codigo, deposito
                ) lx ON stock_snapshots.codigo=lx.codigo AND stock_snapshots.deposito=lx.deposito AND stock_snapshots.fecha=lx.mf
                GROUP BY codigo
            ) s ON a.codigo=s.codigo
            LEFT JOIN optimizacion o ON a.codigo=o.codigo
            LEFT JOIN (
                SELECT codigo, lista_1, lista_4, MAX(fecha) as mf FROM precios GROUP BY codigo
            ) p ON a.codigo=p.codigo
            WHERE s.stock > 20
              AND COALESCE(o.demanda_promedio,0) < 2
              AND COALESCE(a.en_lista_negra,0) = 0
            ORDER BY s.stock DESC
            LIMIT 50
        """)

        if df_clavos.empty:
            st.success("✅ No se detectaron clavos (necesitás datos de stock y optimización).")
        else:
            st.warning(f"⚠️ {len(df_clavos)} artículos detectados como posibles clavos")

            modo_liq = st.radio(
                "Modo de liquidación",
                [
                    "Descuento % sobre Lista 1",
                    "Al costo (precio de compra)",
                    "Precio libre manual",
                    "🤖 Sugerencia por IA",
                ],
                horizontal=True,
            )

            if "Descuento" in modo_liq:
                descuento = st.slider("Descuento %", 10, 80, 30)
                df_clavos["precio_liq"] = df_clavos["lista_1"] * (1 - descuento / 100)
            elif "costo" in modo_liq:
                df_clavos["precio_liq"] = df_clavos["lista_1"] * 0.7  # estimado
            elif "IA" in modo_liq:
                if st.button("🤖 Calcular con Claude"):
                    with st.spinner("Analizando..."):
                        from modules.ia_engine import motor_ia
                        resp = motor_ia.consultar(
                            "Sugerí precios de liquidación para estos artículos con alta acumulación:",
                            contexto_datos={"clavos": df_clavos.head(10).to_dict("records")}
                        )
                    st.info(resp)
            else:
                df_clavos["precio_liq"] = df_clavos["lista_1"]

            if "precio_liq" in df_clavos.columns:
                df_clavos["precio_liq_ars"] = df_clavos["precio_liq"].apply(lambda x: usd_a_ars(x, tasa))

            st.dataframe(
                df_clavos,
                width="stretch",
                hide_index=True,
                column_config={
                    "stock": st.column_config.NumberColumn("Stock", format="%d"),
                    "demanda_prom": st.column_config.NumberColumn("Demanda/mes", format="%.1f"),
                    "lista_1": st.column_config.NumberColumn("L1 USD", format="$%.2f"),
                    "precio_liq": st.column_config.NumberColumn("Precio liq. USD", format="$%.2f"),
                    "precio_liq_ars": st.column_config.NumberColumn("Precio liq. ARS", format="$%.0f"),
                }
            )

    # ── Tab: Buscar ───────────────────────────────────────────
    with tabs[2]:
        busqueda = st.text_input("🔍 Buscar por código o descripción",
                                 placeholder="Ej: SAM A10 o 2401251672")
        if busqueda:
            df_bus = query_to_df("""
                SELECT
                    p.codigo, a.descripcion, a.marca,
                    p.lista_1, p.lista_2, p.lista_3, p.lista_4, p.lista_5,
                    s.stock
                FROM precios p
                JOIN (
                    SELECT codigo, MAX(fecha) as mf FROM precios GROUP BY codigo
                ) latest ON p.codigo=latest.codigo AND p.fecha=latest.mf
                LEFT JOIN articulos a ON p.codigo=a.codigo
                LEFT JOIN (
                    SELECT codigo, SUM(stock) as stock FROM stock_snapshots
                    JOIN (
                        SELECT codigo, deposito, MAX(fecha) as mf
                        FROM stock_snapshots GROUP BY codigo, deposito
                    ) lx ON stock_snapshots.codigo=lx.codigo AND stock_snapshots.deposito=lx.deposito AND stock_snapshots.fecha=lx.mf
                    GROUP BY codigo
                ) s ON p.codigo=s.codigo
                WHERE p.codigo LIKE ? OR UPPER(a.descripcion) LIKE ?
                LIMIT 30
            """, (f"%{busqueda}%", f"%{busqueda.upper()}%"))

            if df_bus.empty:
                st.warning("Sin resultados.")
            else:
                st.success(f"{len(df_bus)} resultado(s)")
                for _, row in df_bus.iterrows():
                    with st.expander(f"`{row.get('codigo','')}` — {row.get('descripcion','—')} · Stock: {int(row.get('stock',0) or 0)}"):
                        c1, c2, c3, c4, c5 = st.columns(5)
                        c1.metric("Lista 1", fmt_usd(row.get("lista_1",0)))
                        c2.metric("Lista 2", fmt_usd(row.get("lista_2",0)))
                        c3.metric("Lista 3", fmt_usd(row.get("lista_3",0)))
                        c4.metric("Lista 4 (ML)", fmt_usd(row.get("lista_4",0)))
                        c5.metric("Lista 5", fmt_usd(row.get("lista_5",0)))
                        st.markdown(f"**ARS (L1):** {fmt_ars(usd_a_ars(row.get('lista_1',0), tasa))} · **ARS (ML):** {fmt_ars(usd_a_ars(row.get('lista_4',0), tasa))}")

    # ── IA contextual ──────────────────────────────────────────
    from utils.ia_widget import nx_ai_widget, ctx_precios
    nx_ai_widget(
        page_key  = "precios",
        titulo    = "🤖 Analizar precios con IA",
        subtitulo = "Consultá sobre competitividad, márgenes y estrategia de precios",
        sugeridas = [
            ("💰 ¿Precios competitivos?",  "¿Nuestros precios de Lista 1 y Lista 4 son competitivos en el mercado actual?"),
            ("📉 Márgenes bajos",          "¿Qué artículos tienen márgenes muy bajos o negativos en Lista 4 (ML)?"),
            ("🏷️ Sugerencia de precios",   "Sugerí ajustes de precio para mejorar el margen en MercadoLibre sin perder ventas."),
            ("⚖️ L1 vs ML",               "¿Vale la pena vender en ML frente al canal mayorista considerando las comisiones?"),
        ],
        context_fn = ctx_precios,
        collapsed  = True,
    )
