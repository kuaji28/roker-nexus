"""
ROKER NEXUS — Módulo: Defensa de Presupuesto
=============================================
Análisis antes/después de diciembre 2025 (ingreso de Mariano como sub-gerente).
Palancas: stockouts, pérdidas RMA, remitos sin confirmar, tendencia de ventas.

Uso estratégico: presentar a Diego y Walter los datos que justifican
mantener o aumentar el presupuesto de módulos.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

from database import query_to_df, get_config
from utils.helpers import fmt_usd, fmt_num


# ── Números validados (baseline auditado 15/03/2026) ───────────
_BASELINE = {
    "modulos_pct_ventas":   35.1,
    "unidades_30d":         28_224,
    "stock_costo_usd":      517_620,
    "stock_lista1_usd":     826_265,
    "margen_pct":           118,
    "rma_loss_2_5m":        24_708,
    "rma_loss_anual_proy":  118_601,
    "presupuesto_actual":   250_000,
    "presupuesto_historico":400_000,   # estimado pre-dic 2025
    "stockout_activos":     101,
    "remitos_sin_confirmar":504,
    "fecha_corte":          "15/03/2026",
    "fecha_mariano":        "01/12/2025",
}

_MARIANO_MES = date(2025, 12, 1)
_HOY         = date(2026, 3, 15)
_MESES_BAJO_MARIANO = 3.5   # dic 2025 – mar 2026


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        🛡️ Defensa de Presupuesto de Módulos
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:4px">
        Análisis antes / después de diciembre 2025 · Datos para Diego y Walter
    </p>
    <div style="font-size:12px;color:var(--nx-text3);margin-bottom:20px;
                background:rgba(10,132,255,.08);border:1px solid rgba(10,132,255,.2);
                border-radius:8px;padding:8px 12px;display:inline-block">
        📅 Baseline: <strong>ene–nov 2025</strong> (sin Mariano)
        &nbsp;·&nbsp; Comparación: <strong>dic 2025 – mar 2026</strong> (gestión Mariano+Pablo)
    </div>
    """, unsafe_allow_html=True)

    tasa = float(get_config("tasa_usd_ars", float) or 1415)

    _seccion_kpis_principales(tasa)
    st.divider()
    _seccion_stockout(tasa)
    st.divider()
    _seccion_rma(tasa)
    st.divider()
    _seccion_remitos()
    st.divider()
    _seccion_argumento_estrategico()
    st.divider()
    _seccion_datos_live()

    # ── IA contextual ──────────────────────────────────────────
    from utils.ia_widget import nx_ai_widget, ctx_defensa
    nx_ai_widget(
        page_key  = "defensa",
        titulo    = "🤖 Construir argumento con IA",
        subtitulo = "Preparate para la presentación con Diego y Walter",
        sugeridas = [
            ("🛡️ Argumento principal",    "Construí el argumento más sólido para defender el presupuesto de módulos ante Diego y Walter."),
            ("📊 Cuantificar el daño",    "¿Cuánto costó en ventas perdidas el recorte de presupuesto desde diciembre 2025?"),
            ("🎯 Rebatir a Pablo/Mariano","¿Cómo rebato el argumento de 'los módulos tienen márgenes bajos' con los datos actuales?"),
            ("📋 Preparar presentación",  "Redactá un guion ejecutivo de 5 minutos para presentar a Diego. Directo, con números."),
        ],
        context_fn = ctx_defensa,
        collapsed  = False,
    )


# ══════════════════════════════════════════════════════════════
# SECCIÓN 1 — KPIs Principales
# ══════════════════════════════════════════════════════════════

def _seccion_kpis_principales(tasa: float):
    st.markdown("### 📊 Situación actual — Módulos")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Módulos % ventas totales",
        f"{_BASELINE['modulos_pct_ventas']}%",
        help="Categoría #1. Calculado sobre facturación total 30 días.",
    )
    c2.metric(
        "Unidades vendidas / 30 días",
        fmt_num(_BASELINE["unidades_30d"]),
        help="Demanda real del mercado.",
    )
    c3.metric(
        "Stock módulos a Lista 1",
        fmt_usd(_BASELINE["stock_lista1_usd"]),
        help="Valorización a precio mayorista.",
    )
    c4.metric(
        "Margen promedio módulos",
        f"{_BASELINE['margen_pct']}%",
        help="Margen sobre Lista 1 (no sobre costo).",
    )

    st.markdown("")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric(
        "Presupuesto actual / mes",
        fmt_usd(_BASELINE["presupuesto_actual"]),
        delta=fmt_usd(_BASELINE["presupuesto_actual"] - _BASELINE["presupuesto_historico"]),
        delta_color="inverse",
        help="Recortado desde dic 2025.",
    )
    c6.metric(
        "Stockouts activos (stock=0)",
        _BASELINE["stockout_activos"],
        delta="↑ por recorte",
        delta_color="inverse",
        help="Módulos con demanda > 0 y stock = 0.",
    )
    c7.metric(
        "Pérdida RMA (2.5 meses)",
        fmt_usd(_BASELINE["rma_loss_2_5m"]),
        help="Capital + renta no percibida.",
    )
    c8.metric(
        "Proyección RMA anual",
        fmt_usd(_BASELINE["rma_loss_anual_proy"]),
        delta="↑ acelerado",
        delta_color="inverse",
    )

    st.markdown("""
    <div style="background:rgba(255,55,95,.08);border:1px solid rgba(255,55,95,.25);
                border-radius:12px;padding:14px 18px;margin-top:12px">
        <strong style="color:#ff375f">⚠️ Situación crítica:</strong>
        <span style="font-size:13px;color:#f2f2f7">
        El recorte de presupuesto desde diciembre 2025 generó
        <strong>101 stockouts activos</strong>, pérdidas RMA de
        <strong>USD 24.708 en solo 2.5 meses</strong>, y 504 remitos internos
        sin confirmar. Los módulos representan el <strong>35% de ventas totales</strong>
        — cortar su presupuesto no reduce costos, aumenta pérdidas.
        </span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SECCIÓN 2 — Stockout Analysis
# ══════════════════════════════════════════════════════════════

def _seccion_stockout(tasa: float):
    st.markdown("### 🔴 Stockouts — Costo de oportunidad")

    # Intentar leer datos live
    df_live = _leer_stockouts_live()

    if not df_live.empty:
        n_stockout = len(df_live)
        ventas_dia_total = df_live["ventas_dia"].sum() if "ventas_dia" in df_live.columns else 0
        perdida_dia = ventas_dia_total * df_live.get("lista1", pd.Series([0])).mean() if not df_live.empty else 0
    else:
        n_stockout = _BASELINE["stockout_activos"]
        ventas_dia_total = 0
        perdida_dia = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Módulos en stockout", n_stockout,
              help="Demanda > 0 y stock = 0 → ventas perdidas invisibles.")
    c2.metric("Presupuesto recortado",
              fmt_usd(_BASELINE["presupuesto_historico"] - _BASELINE["presupuesto_actual"]),
              help="Diferencia mensual vs presupuesto pre-Mariano (estimado).")
    c3.metric("Meses con nuevo presupuesto", f"{_MESES_BAJO_MARIANO:.1f}",
              help="Dic 2025 a Mar 2026.")

    st.markdown("""
    <div style="background:rgba(255,159,10,.08);border:1px solid rgba(255,159,10,.25);
                border-radius:12px;padding:14px 18px;margin-top:12px">
        <strong style="color:#ff9f0a">💡 El problema del stock=0:</strong>
        <span style="font-size:13px;color:#f2f2f7">
        Cuando un módulo tiene stock=0, Flexxus muestra demanda=0.
        Esto crea una <strong>"demanda invisible"</strong> — el sistema parece que no se necesita
        el producto, cuando en realidad no se puede vender porque no hay stock.
        Por eso los 101 stockouts son especialmente peligrosos: subestiman la demanda real
        y validan el recorte de presupuesto con datos falsos.
        </span>
    </div>
    """, unsafe_allow_html=True)

    if not df_live.empty and "ventas_dia" in df_live.columns:
        st.markdown("**Top módulos en stockout por rotación histórica:**")
        top_stockout = df_live.nlargest(15, "ventas_dia")[
            [c for c in ["codigo", "descripcion", "ventas_dia", "lista1", "valor_l1"] if c in df_live.columns]
        ].reset_index(drop=True)
        col_cfg = {}
        if "ventas_dia" in top_stockout.columns:
            col_cfg["ventas_dia"] = st.column_config.NumberColumn("Venta/día", format="%.1f")
        if "lista1" in top_stockout.columns:
            col_cfg["lista1"] = st.column_config.NumberColumn("Lista 1 USD", format="$%.2f")
        if "valor_l1" in top_stockout.columns:
            col_cfg["valor_l1"] = st.column_config.NumberColumn("Valor stock L1", format="$%.0f")
        st.dataframe(top_stockout, hide_index=True, use_container_width=True,
                     column_config=col_cfg)


# ══════════════════════════════════════════════════════════════
# SECCIÓN 3 — Pérdidas RMA
# ══════════════════════════════════════════════════════════════

def _seccion_rma(tasa: float):
    st.markdown("### 🔄 Pérdidas RMA (devoluciones)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pérdida total RMA (2.5m)", fmt_usd(_BASELINE["rma_loss_2_5m"]))
    c2.metric("Proyección anual", fmt_usd(_BASELINE["rma_loss_anual_proy"]))

    perdida_mensual = _BASELINE["rma_loss_2_5m"] / _MESES_BAJO_MARIANO
    c3.metric("Pérdida mensual promedio", fmt_usd(perdida_mensual))
    c4.metric("En ARS (blue)",
              f"$ {_BASELINE['rma_loss_anual_proy'] * tasa:,.0f}".replace(",", "."),
              help=f"TC blue: $ {tasa:,.0f}")

    st.markdown("""
    <div style="background:rgba(255,55,95,.08);border:1px solid rgba(255,55,95,.25);
                border-radius:12px;padding:14px 18px;margin-top:12px">
        <strong style="color:#ff375f">💰 Costo real de las devoluciones:</strong>
        <span style="font-size:13px;color:#f2f2f7">
        Cada RMA no es solo el reembolso al cliente — es el costo del módulo (capital inmovilizado)
        más la <strong>renta no percibida</strong> (margen que se perdió).
        Con un margen promedio de 118%, una devolución de USD 10 de costo
        representa en realidad ~USD 22 de pérdida total.
        Proyectado anualmente: <strong>USD 118.601</strong> solo en RMA.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Datos live si están disponibles
    try:
        df_rma = query_to_df("""
            SELECT codigo, SUM(ABS(stock)) as unidades_rma
            FROM stock_snapshots
            WHERE deposito LIKE '%RMA%' OR deposito LIKE '%DEV%'
            GROUP BY codigo
            ORDER BY unidades_rma DESC
            LIMIT 10
        """)
        if not df_rma.empty:
            st.markdown("**Top artículos en depósito RMA/DEV (desde DB):**")
            st.dataframe(df_rma, hide_index=True, use_container_width=True,
                         column_config={
                             "codigo": st.column_config.TextColumn("Código"),
                             "unidades_rma": st.column_config.NumberColumn("Uds en RMA", format="%d"),
                         })
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# SECCIÓN 4 — Remitos sin confirmar
# ══════════════════════════════════════════════════════════════

def _seccion_remitos():
    st.markdown("### 📦 Remitos internos sin confirmar")

    c1, c2 = st.columns(2)
    c1.metric("Ítems con Entregada=0", _BASELINE["remitos_sin_confirmar"],
              help="Todos los remitos internos relevados tienen cantidad entregada = 0.")
    c2.metric("% confirmados", "0%", delta="Riesgo operativo alto", delta_color="inverse")

    st.markdown("""
    <div style="background:rgba(255,159,10,.08);border:1px solid rgba(255,159,10,.25);
                border-radius:12px;padding:14px 18px;margin-top:12px">
        <strong style="color:#ff9f0a">⚠️ Zona gris operativa:</strong>
        <span style="font-size:13px;color:#f2f2f7">
        504 ítems de remitos internos (transferencias SAN JOSE → LARREA / SARMIENTO)
        aparecen con <strong>cantidad entregada = 0</strong>.
        Esto significa que el sistema no sabe si la mercadería llegó o no.
        Impacto: stock virtualizado que puede no existir físicamente,
        imposibilidad de auditar el inventario real, y potencial diferencia
        de inventario no detectada.
        </span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SECCIÓN 5 — Argumento estratégico
# ══════════════════════════════════════════════════════════════

def _seccion_argumento_estrategico():
    st.markdown("### 🎯 El argumento para Diego y Walter")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="background:rgba(255,55,95,.08);border:1px solid rgba(255,55,95,.25);
                    border-radius:12px;padding:16px 18px">
            <div style="font-weight:700;font-size:14px;color:#ff375f;margin-bottom:8px">
                ❌ La lógica de Pablo/Mariano (recortar módulos)
            </div>
            <ul style="font-size:13px;color:#f2f2f7;margin:0;padding-left:18px;line-height:1.8">
                <li>Márgenes por unidad bajaron (apertura importaciones)</li>
                <li>Pivotar a electrodomésticos tipo Frávega</li>
                <li>Reducir presupuesto de USD 400k → 250k/mes</li>
                <li>Resultado: 101 stockouts, ventas perdidas, clientes sin atender</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background:rgba(50,215,75,.08);border:1px solid rgba(50,215,75,.25);
                    border-radius:12px;padding:16px 18px">
            <div style="font-weight:700;font-size:14px;color:#32d74b;margin-bottom:8px">
                ✅ La realidad del negocio (argumento Roker)
            </div>
            <ul style="font-size:13px;color:#f2f2f7;margin:0;padding-left:18px;line-height:1.8">
                <li>Módulos = 35% ventas totales → <strong>categoría #1</strong></li>
                <li>Son el <strong>anchor product</strong>: el técnico que compra módulo
                    también compra flex, adhesivo, vidrio, herramientas</li>
                <li>Sin módulos → el cliente va a la competencia y <strong>lleva todo</strong></li>
                <li>Frávega requiere capital, escala y marca que EL CELU no tiene</li>
                <li>USD 118.601/año en pérdidas RMA + costo de oportunidad de 101 stockouts</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("""
    <div style="background:rgba(10,132,255,.08);border:1px solid rgba(10,132,255,.25);
                border-radius:12px;padding:16px 18px;margin-top:4px">
        <div style="font-weight:700;font-size:14px;color:#64b5ff;margin-bottom:8px">
            💡 Propuesta concreta
        </div>
        <div style="font-size:13px;color:#f2f2f7;line-height:1.8">
            <strong>Presupuesto mínimo recomendado: USD 350.000/mes</strong> (para cubrir demanda real sin stockouts).<br>
            En términos de ROI: cada USD invertido en módulos genera ~2.18x de retorno (margen 118%).
            El costo de <em>no comprar</em> es mayor que el costo de comprar:
            un mes sin módulos genera ventas perdidas estimadas en
            <strong>USD {:.0f}</strong> solo por la demanda actual.
        </div>
    </div>
    """.format(_BASELINE["unidades_30d"] / 30 * 30 * 8.5), unsafe_allow_html=True)
    # 8.5 = precio promedio módulo estimado


# ══════════════════════════════════════════════════════════════
# SECCIÓN 6 — Datos en vivo desde DB
# ══════════════════════════════════════════════════════════════

def _seccion_datos_live():
    st.markdown("### 📡 Datos en vivo — Análisis desde la base de datos")

    col_btn, _ = st.columns([2, 8])
    with col_btn:
        correr = st.button("🔄 Analizar datos DB", type="primary", use_container_width=True,
                           help="Calcula KPIs directamente desde los snapshots importados.")

    if not correr and not st.session_state.get("defensa_analisis_corrido"):
        st.info("Hacé clic en **Analizar datos DB** para cargar los KPIs desde los snapshots importados.")
        return

    st.session_state["defensa_analisis_corrido"] = True

    # Módulos en stockout (live)
    df_so = _leer_stockouts_live()
    if not df_so.empty:
        st.markdown(f"**🔴 {len(df_so)} módulos con stock=0 en la DB actual:**")
        show_cols = [c for c in ["codigo", "descripcion", "lista1", "ventas_dia"] if c in df_so.columns]
        if show_cols:
            st.dataframe(df_so[show_cols].head(30), hide_index=True, use_container_width=True,
                         column_config={
                             "lista1": st.column_config.NumberColumn("Lista 1 USD", format="$%.2f"),
                             "ventas_dia": st.column_config.NumberColumn("Venta/día", format="%.1f"),
                         })
    else:
        st.info("No hay datos de stock cargados en la DB o no hay módulos en stockout.")

    # Distribución de stock por depósito
    try:
        df_dep = query_to_df("""
            SELECT deposito, COUNT(DISTINCT codigo) as skus, SUM(stock) as unidades
            FROM stock_snapshots
            WHERE fecha = (SELECT MAX(fecha) FROM stock_snapshots)
            GROUP BY deposito
            ORDER BY unidades DESC
        """)
        if not df_dep.empty:
            st.markdown("**📦 Stock por depósito (último snapshot):**")
            st.dataframe(df_dep, hide_index=True, use_container_width=True,
                         column_config={
                             "deposito":  st.column_config.TextColumn("Depósito"),
                             "skus":      st.column_config.NumberColumn("SKUs", format="%d"),
                             "unidades":  st.column_config.NumberColumn("Unidades", format="%d"),
                         })
    except Exception as e:
        st.caption(f"Error cargando stock por depósito: {e}")

    # RMA vivo
    try:
        df_rma_live = query_to_df("""
            SELECT COUNT(DISTINCT codigo) as skus_rma, SUM(ABS(stock)) as uds_rma
            FROM stock_snapshots
            WHERE deposito LIKE '%RMA%' OR deposito LIKE '%DEV%'
        """)
        if not df_rma_live.empty and df_rma_live.iloc[0]["skus_rma"]:
            r = df_rma_live.iloc[0]
            st.metric("SKUs en depósito RMA/DEV (live)", int(r.get("skus_rma", 0)),
                      help="Desde snapshots importados.")
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _leer_stockouts_live() -> pd.DataFrame:
    """Lee módulos con stock=0 desde la DB."""
    try:
        df = query_to_df("""
            SELECT s.codigo,
                   COALESCE(a.descripcion, s.descripcion) as descripcion,
                   COALESCE(p.lista_1, 0) as lista1,
                   COALESCE(p.lista_4, 0) as lista4,
                   s.stock
            FROM stock_snapshots s
            LEFT JOIN articulos a ON s.codigo = a.codigo
            LEFT JOIN precios p ON s.codigo = p.codigo
            LEFT JOIN (
                SELECT codigo, MAX(fecha) mf FROM stock_snapshots GROUP BY codigo
            ) lx ON s.codigo = lx.codigo AND s.fecha = lx.mf
            WHERE s.deposito = 'SJ'
              AND s.stock = 0
              AND UPPER(COALESCE(a.descripcion, s.descripcion, '')) LIKE '%MODULO%'
              AND COALESCE(a.en_lista_negra, 0) = 0
            ORDER BY s.codigo
        """)
        # Intentar unir con demanda si está disponible
        try:
            df_dem = query_to_df("""
                SELECT codigo,
                       COALESCE(dm.demanda_manual, o.demanda_promedio, 0) as ventas_dia
                FROM optimizacion o
                LEFT JOIN demanda_manual dm ON o.codigo = dm.codigo
                WHERE demanda_promedio > 0 OR dm.demanda_manual > 0
            """)
            if not df_dem.empty and not df.empty:
                df = df.merge(df_dem, on="codigo", how="left")
                df["ventas_dia"] = df["ventas_dia"].fillna(0)
        except Exception:
            pass
        return df
    except Exception:
        return pd.DataFrame()


if __name__ == "__main__":
    render()
