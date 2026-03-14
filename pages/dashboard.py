"""
ROKER NEXUS — Dashboard v2.0
Vista ejecutiva enfocada en MÓDULOS (el producto principal del negocio).

Lógica de clasificación:
  - MÓDULO = descripción empieza con "MODULO" en la tabla optimizacion
  - FR      = código empieza con LETRA  (M, L, P...) → proveedor AITECH
  - MECÁNICO = código empieza con NÚMERO               → proveedor MECÁNICO
  - Todo lo demás (accesorios, etc.) se excluye del dashboard principal

El stock general de Flexxus tiene 17.000+ artículos porque incluye TODO el catálogo.
Solo hay ~850 módulos — eso es lo que importa para las compras.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from database import query_to_df, get_config, execute_query
from utils.horarios import ahora
from utils.helpers import fmt_usd, fmt_ars, fmt_num


# ── Helpers ──────────────────────────────────────────────────
def _es_modulo(descripcion: str) -> bool:
    return str(descripcion or "").upper().strip().startswith("MODULO")

def _tipo_codigo(codigo: str) -> str:
    c = str(codigo or "").strip()
    if not c or c == "nan": return "otro"
    return "fr" if c[0].isalpha() else "mecanico"


def _get_kpis_modulos() -> dict:
    """KPIs reales filtrados a módulos únicamente."""
    try:
        tasa = float(get_config("tasa_usd_ars", float) or 1420)

        df = query_to_df("""
            SELECT o.codigo,
                   COALESCE(a.descripcion, o.descripcion) as descripcion,
                   o.demanda_promedio, o.stock_actual,
                   o.stock_optimo, o.costo_reposicion,
                   p.lista_1, p.lista_4,
                   COALESCE(a.en_lista_negra, 0) as en_lista_negra,
                   COALESCE(a.en_transito, 0) as en_transito
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo=a.codigo
            LEFT JOIN precios p ON o.codigo=p.codigo
            WHERE COALESCE(a.en_lista_negra, 0) = 0
        """)

        if df.empty:
            return {"ok": False}

        # Filtrar solo módulos
        df = df[df["descripcion"].apply(_es_modulo)].copy()
        df["tipo"] = df["codigo"].apply(_tipo_codigo)
        df["stock_actual"] = df["stock_actual"].fillna(0)
        df["demanda_promedio"] = df["demanda_promedio"].fillna(0).clip(lower=0)
        df["costo_reposicion"] = df["costo_reposicion"].fillna(0)
        df["lista_4"] = df["lista_4"].fillna(0)
        df["en_transito"] = df["en_transito"].fillna(0) if "en_transito" in df.columns else 0
        df["stock_real"] = df["stock_actual"] + df["en_transito"]

        total_mods = len(df)
        fr_total   = int((df["tipo"] == "fr").sum())
        mec_total  = int((df["tipo"] == "mecanico").sum())

        sin_stock     = df[df["stock_actual"] == 0]
        fr_sin_stock  = int((sin_stock["tipo"] == "fr").sum())
        mec_sin_stock = int((sin_stock["tipo"] == "mecanico").sum())

        bajo_min = df[(df["stock_actual"] > 0) & (df["stock_actual"] < df["stock_optimo"])]
        fr_bajo  = int((bajo_min["tipo"] == "fr").sum())
        mec_bajo = int((bajo_min["tipo"] == "mecanico").sum())

        # Inversión requerida
        df["a_pedir"]   = (df["stock_optimo"] - df["stock_actual"]).clip(lower=0)
        df["inversion"] = df["a_pedir"] * df["costo_reposicion"]
        inversion_fr  = float(df[df["tipo"] == "fr"]["inversion"].sum())
        inversion_mec = float(df[df["tipo"] == "mecanico"]["inversion"].sum())
        inversion_tot = inversion_fr + inversion_mec

        # Venta perdida (stock=0 con demanda)
        vp = df[(df["stock_actual"] == 0) & (df["demanda_promedio"] > 0)].copy()
        vp["vp_ars"] = vp.apply(
            lambda r: r["demanda_promedio"] * r["lista_4"] if r["lista_4"] > 0
            else r["demanda_promedio"] * r["costo_reposicion"] * tasa * 1.8,
            axis=1
        )
        venta_perdida_usd = float(vp["vp_ars"].sum() / tasa)

        # Top 10 críticos (stock=0, mayor demanda)
        criticos = df[df["stock_actual"] == 0].sort_values(
            "demanda_promedio", ascending=False
        ).head(10)

        # Top 10 urgentes (bajo mínimo)
        urgentes = df[
            (df["stock_actual"] > 0) &
            (df["stock_actual"] < df["stock_optimo"]) &
            (df["demanda_promedio"] > 0)
        ].copy()
        urgentes["dias_cob"] = (urgentes["stock_actual"] / (urgentes["demanda_promedio"] / 30)).round(0)
        urgentes = urgentes.sort_values("dias_cob").head(10)

        # KPIs de tránsito
        en_transito_items = int((df["en_transito"] > 0).sum())
        en_transito_usd = float((df["en_transito"] * df["costo_reposicion"]).sum())

        # Valor inventario
        valor_inv_usd = float((df["stock_actual"] * df["costo_reposicion"]).sum())

        # Cobertura promedio (solo módulos con demanda)
        df_con_dem = df[df["demanda_promedio"] > 0].copy()
        df_con_dem["dias_cob"] = (df_con_dem["stock_real"] / (df_con_dem["demanda_promedio"] / 30))
        cob_prom = float(df_con_dem["dias_cob"].clip(upper=999).mean()) if not df_con_dem.empty else 0

        # Overrides demanda
        try:
            df_ov = query_to_df("SELECT COUNT(*) as n FROM demanda_manual")
            overrides = int(df_ov.iloc[0]["n"]) if not df_ov.empty else 0
        except Exception:
            overrides = 0

        return {
            "ok": True, "tasa": tasa,
            "total_mods": total_mods, "fr_total": fr_total, "mec_total": mec_total,
            "fr_sin_stock": fr_sin_stock, "mec_sin_stock": mec_sin_stock,
            "fr_bajo": fr_bajo, "mec_bajo": mec_bajo,
            "inversion_fr": inversion_fr, "inversion_mec": inversion_mec,
            "inversion_tot": inversion_tot,
            "venta_perdida_usd": venta_perdida_usd,
            "en_transito_items": en_transito_items,
            "en_transito_usd": en_transito_usd,
            "valor_inv_usd": valor_inv_usd,
            "cob_prom_dias": cob_prom,
            "overrides": overrides,
            "criticos": criticos, "urgentes": urgentes,
            "df_modulos": df,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def render():
    # ── Refresh ───────────────────────────────────────────────
    col_h, col_ref = st.columns([5, 1])
    with col_h:
        st.markdown("""
        <h1 style="margin:0 0 2px;font-size:26px;font-weight:700;color:var(--nx-text)">
            📊 Dashboard
        </h1>
        <p style="color:var(--nx-text2);font-size:13px;margin-bottom:16px">
            Vista ejecutiva de <strong>módulos</strong> — FR + Mecánico
        </p>
        """, unsafe_allow_html=True)
    with col_ref:
        if st.button("🔄", help="Actualizar datos", width='stretch'):
            st.rerun()

    kpis = _get_kpis_modulos()

    # ── Banner tránsito ───────────────────────────────────────
    if kpis.get("ok") and kpis.get("en_transito_items", 0) > 0:
        n_t = kpis["en_transito_items"]
        v_t = kpis["en_transito_usd"]
        st.markdown(f"""
        <div style="background:rgba(90,200,250,.08);border:1px solid rgba(90,200,250,.2);
                    border-radius:10px;padding:10px 16px;margin-bottom:12px;
                    display:flex;align-items:center;justify-content:space-between">
            <span style="font-size:13px;color:#5ac8fa;font-weight:600">
                ✈️ {n_t} SKUs en tránsito
            </span>
            <span style="font-size:12px;color:var(--nx-text2)">
                Valor: USD ${v_t:,.2f} — stock_real ya incluye estas unidades en todos los cálculos
            </span>
        </div>
        """, unsafe_allow_html=True)

    if not kpis.get("ok"):
        err = kpis.get("error", "")
        if "no such table" in err or not err:
            st.info("📥 **Sin datos todavía.** Cargá primero el archivo de **Optimización de Stock** desde la pestaña Cargar.")
        else:
            st.error(f"Error cargando datos: {err}")
        _panel_sin_datos()
        return

    tasa = kpis["tasa"]

    # ════════════════════════════════════════════════════════
    # BLOQUE 1 — SEMÁFORO PRINCIPAL (tarjetas grandes)
    # ════════════════════════════════════════════════════════
    st.markdown("### 🚦 Estado de Módulos")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        _kpi_card(
            "📦 FR sin stock",
            kpis["fr_sin_stock"],
            f"de {kpis['fr_total']} FR totales",
            "rojo" if kpis["fr_sin_stock"] > 20 else "verde",
            detalle=f"+ {kpis['fr_bajo']} bajo mínimo"
        )
    with c2:
        _kpi_card(
            "📦 Mecánico sin stock",
            kpis["mec_sin_stock"],
            f"de {kpis['mec_total']} Mecánico totales",
            "rojo" if kpis["mec_sin_stock"] > 10 else "verde",
            detalle=f"+ {kpis['mec_bajo']} bajo mínimo"
        )
    with c3:
        _kpi_card(
            "💸 Venta perdida/mes",
            f"USD {kpis['venta_perdida_usd']:,.0f}",
            f"= ${kpis['venta_perdida_usd']*tasa:,.0f} ARS",
            "rojo" if kpis["venta_perdida_usd"] > 1000 else "amarillo",
            detalle=f"stock=0 con demanda activa"
        )
    with c4:
        _kpi_card(
            "💰 Inversión requerida",
            f"USD {kpis['inversion_tot']:,.0f}",
            f"= ${kpis['inversion_tot']*tasa:,.0f} ARS",
            "amarillo",
            detalle=f"FR: ${kpis['inversion_fr']:,.0f} | Mec: ${kpis['inversion_mec']:,.0f}"
        )

    # ════════════════════════════════════════════════════════
    # BLOQUE 1b — KPIs OPERATIVOS (6 métricas)
    # ════════════════════════════════════════════════════════
    st.markdown("---")
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    with k1: _kpi_card("Total Módulos", kpis["total_mods"], "FR + Mecánico", "azul")
    with k2: _kpi_card("🔴 Sin Stock", kpis["fr_sin_stock"]+kpis["mec_sin_stock"], "Acción inmediata", "rojo")
    with k3: _kpi_card("🟡 Bajo Mínimo", kpis["fr_bajo"]+kpis["mec_bajo"], "Próxima compra", "amarillo")
    with k4: _kpi_card("✈️ En Tránsito", kpis.get("en_transito_items",0), "SKUs con pedido", "azul")
    with k5: _kpi_card("Cob. Promedio", f"{kpis.get('cob_prom_dias',0):.0f}d", "Días cobertura global", "verde")
    with k6: _kpi_card("Overrides", kpis.get("overrides",0), "Demanda manual", "azul")

    # ── KPIs FINANCIEROS (4 métricas) ──
    st.markdown("---")
    f1,f2,f3,f4 = st.columns(4)
    val = kpis.get("valor_inv_usd",0)
    req = kpis.get("inversion_tot",0)
    vp  = kpis.get("venta_perdida_usd",0)
    with f1: _kpi_card("💼 Valor Inventario", f"USD {val:,.0f}", f"≈ ARS ${val*tasa:,.0f}", "azul")
    with f2: _kpi_card("💳 Inversión Requerida", f"USD {req:,.0f}", f"≈ ARS ${req*tasa:,.0f}", "amarillo")
    with f3: _kpi_card("💸 Costo Oportunidad", f"USD {vp:,.0f}", "Stock=0 con demanda activa", "rojo")
    with f4: _kpi_card("FR vs MEC", f"FR {kpis['fr_total']} / MEC {kpis['mec_total']}", "Distribución proveedores", "verde")

    # ════════════════════════════════════════════════════════
    # BLOQUE 2 — DESGLOSE FR vs MECÁNICO
    # ════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📊 FR vs Mecánico")

    col_fr, col_mec = st.columns(2)

    with col_fr:
        total_fr = kpis["fr_total"]
        ok_fr = total_fr - kpis["fr_sin_stock"] - kpis["fr_bajo"]
        st.markdown(f"""
        <div style="background:rgba(10,132,255,.08);border:1px solid rgba(10,132,255,.2);
                    border-left:3px solid #0a84ff;border-radius:12px;padding:14px 16px">
            <div style="font-size:11px;color:#0a84ff;font-weight:700;text-transform:uppercase;letter-spacing:.8px">
                FR (AITECH) — Código con letra</div>
            <div style="display:flex;gap:20px;margin-top:10px">
                <div><div style="font-size:22px;font-weight:700;color:var(--nx-text)">{total_fr}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Total</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#32d74b">{ok_fr}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Con stock OK</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#ff9f0a">{kpis['fr_bajo']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Bajo mínimo</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#ff375f">{kpis['fr_sin_stock']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Sin stock</div></div>
            </div>
            <div style="margin-top:10px">
                <div style="height:6px;background:var(--nx-border);border-radius:3px;overflow:hidden">
                    <div style="height:100%;width:{ok_fr/max(total_fr,1)*100:.0f}%;background:#32d74b;border-radius:3px"></div>
                </div>
                <div style="font-size:10px;color:var(--nx-text3);margin-top:4px">
                    {ok_fr/max(total_fr,1)*100:.0f}% con stock suficiente</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_mec:
        total_mec = kpis["mec_total"]
        ok_mec = total_mec - kpis["mec_sin_stock"] - kpis["mec_bajo"]
        st.markdown(f"""
        <div style="background:rgba(255,159,10,.08);border:1px solid rgba(255,159,10,.2);
                    border-left:3px solid #ff9f0a;border-radius:12px;padding:14px 16px">
            <div style="font-size:11px;color:#ff9f0a;font-weight:700;text-transform:uppercase;letter-spacing:.8px">
                MECÁNICO — Código con número</div>
            <div style="display:flex;gap:20px;margin-top:10px">
                <div><div style="font-size:22px;font-weight:700;color:var(--nx-text)">{total_mec}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Total</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#32d74b">{ok_mec}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Con stock OK</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#ff9f0a">{kpis['mec_bajo']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Bajo mínimo</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#ff375f">{kpis['mec_sin_stock']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Sin stock</div></div>
            </div>
            <div style="margin-top:10px">
                <div style="height:6px;background:var(--nx-border);border-radius:3px;overflow:hidden">
                    <div style="height:100%;width:{ok_mec/max(total_mec,1)*100:.0f}%;background:#32d74b;border-radius:3px"></div>
                </div>
                <div style="font-size:10px;color:var(--nx-text3);margin-top:4px">
                    {ok_mec/max(total_mec,1)*100:.0f}% con stock suficiente</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # BLOQUE 3 — CRÍTICOS EXPANDIBLES
    # ════════════════════════════════════════════════════════
    st.markdown("---")

    col_crit, col_urg = st.columns(2)

    with col_crit:
        criticos = kpis["criticos"]
        st.markdown(f"### 🔴 Top 10 Críticos — stock = 0")
        if criticos.empty:
            st.success("✅ Sin críticos ahora mismo")
        else:
            with st.expander(f"Ver {len(criticos)} críticos (click para expandir)", expanded=True):
                for _, r in criticos.iterrows():
                    desc = str(r.get("descripcion",""))[:35]
                    dem  = float(r.get("demanda_promedio") or 0)
                    costo = float(r.get("costo_reposicion") or 0)
                    tipo = "🔵 FR" if _tipo_codigo(r["codigo"]) == "fr" else "🟡 MEC"
                    vp_mes = dem * costo if costo > 0 else 0
                    st.markdown(f"""
                    <div style="padding:8px 0;border-bottom:1px solid var(--nx-border)">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <span style="font-size:10px;color:var(--nx-text3)">{tipo}</span>
                                <span style="font-size:13px;font-weight:600;color:var(--nx-text);margin-left:8px">{desc}</span>
                            </div>
                            <div style="text-align:right">
                                <div style="font-size:12px;font-weight:600;color:#ff375f">STOCK 0</div>
                                <div style="font-size:10px;color:var(--nx-text3)">{dem:.1f}/mes · ${vp_mes:.0f} USD/mes perdido</div>
                            </div>
                        </div>
                        <div style="font-size:10px;color:var(--nx-text3);margin-top:2px">`{r['codigo']}`</div>
                    </div>
                    """, unsafe_allow_html=True)

    with col_urg:
        urgentes = kpis["urgentes"]
        st.markdown(f"### 🟡 Top 10 Urgentes — bajo mínimo")
        if urgentes.empty:
            st.success("✅ Sin urgentes ahora mismo")
        else:
            with st.expander(f"Ver {len(urgentes)} urgentes (click para expandir)", expanded=True):
                for _, r in urgentes.iterrows():
                    desc = str(r.get("descripcion",""))[:35]
                    stk  = int(r.get("stock_actual") or 0)
                    dias = int(r.get("dias_cob") or 0)
                    tipo = "🔵 FR" if _tipo_codigo(r["codigo"]) == "fr" else "🟡 MEC"
                    color = "#ff375f" if dias < 7 else "#ff9f0a"
                    st.markdown(f"""
                    <div style="padding:8px 0;border-bottom:1px solid var(--nx-border)">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <span style="font-size:10px;color:var(--nx-text3)">{tipo}</span>
                                <span style="font-size:13px;font-weight:600;color:var(--nx-text);margin-left:8px">{desc}</span>
                            </div>
                            <div style="text-align:right">
                                <div style="font-size:12px;font-weight:600;color:{color}">{dias} días</div>
                                <div style="font-size:10px;color:var(--nx-text3)">{stk} uds en stock</div>
                            </div>
                        </div>
                        <div style="font-size:10px;color:var(--nx-text3);margin-top:2px">`{r['codigo']}`</div>
                    </div>
                    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # BLOQUE 4 — GRÁFICO POR MARCA + CONFIG RÁPIDA
    # ════════════════════════════════════════════════════════
    st.markdown("---")
    col_graf, col_conf = st.columns([3, 2])

    with col_graf:
        st.markdown("### 📈 Stock por marca (módulos)")
        _grafico_marcas(kpis["df_modulos"])

    with col_conf:
        st.markdown("### ⚡ Config rápida")
        _panel_config_rapida(tasa)

    # ════════════════════════════════════════════════════════
    # BLOQUE 5 — ÚLTIMAS IMPORTACIONES
    # ════════════════════════════════════════════════════════
    st.markdown("---")
    with st.expander("📥 Últimas importaciones", expanded=False):
        df_log = query_to_df("""
            SELECT tipo_archivo, nombre_archivo, filas_importadas, estado, importado_en
            FROM importaciones_log ORDER BY importado_en DESC LIMIT 8
        """)
        if df_log.empty:
            st.info("Sin importaciones registradas.")
        else:
            st.dataframe(df_log, hide_index=True, width='stretch')


def _kpi_card(titulo: str, valor, subtitulo: str, color: str, detalle: str = ""):
    colores = {
        "rojo":    ("#ff375f", "rgba(255,55,95,.12)", "rgba(255,55,95,.25)"),
        "verde":   ("#32d74b", "rgba(50,215,75,.12)",  "rgba(50,215,75,.25)"),
        "amarillo":("#ff9f0a", "rgba(255,159,10,.12)", "rgba(255,159,10,.25)"),
        "azul":    ("#0a84ff", "rgba(10,132,255,.12)", "rgba(10,132,255,.25)"),
    }
    c, bg, border = colores.get(color, colores["azul"])
    det_html = f'<div style="font-size:10px;color:var(--nx-text3);margin-top:2px">{detalle}</div>' if detalle else ""
    st.markdown(f"""
    <div style="background:{bg};border:1px solid {border};border-top:3px solid {c};
                border-radius:12px;padding:14px 16px;height:110px">
        <div style="font-size:11px;color:var(--nx-text2);font-weight:600;
                    text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px">{titulo}</div>
        <div style="font-size:24px;font-weight:700;color:{c};line-height:1.1">{valor}</div>
        <div style="font-size:11px;color:var(--nx-text2);margin-top:4px">{subtitulo}</div>
        {det_html}
    </div>
    """, unsafe_allow_html=True)


def _grafico_marcas(df: pd.DataFrame):
    """Gráfico de barras por marca — sin stock vs con stock."""
    if df.empty:
        st.caption("Sin datos")
        return

    def extraer_marca(desc):
        desc = str(desc).upper()
        marcas = [("SAM","Samsung"),("IPH","iPhone"),("MOT","Motorola"),
                  ("LG","LG"),("XIA","Xiaomi"),("ALC","Alcatel"),
                  ("HUA","Huawei"),("TCL","TCL"),("INF","Infinix"),
                  ("TE ","Tecno"),("NOK","Nokia"),("OPPO","OPPO")]
        for key, label in marcas:
            if key in desc: return label
        return "Otros"

    df = df.copy()
    df["marca"] = df["descripcion"].apply(extraer_marca)
    df["stock_actual"] = df["stock_actual"].fillna(0)

    resumen = df.groupby("marca").agg(
        total=("codigo","count"),
        sin_stock=("stock_actual", lambda x: (x==0).sum())
    ).reset_index()
    resumen["con_stock"] = resumen["total"] - resumen["sin_stock"]
    resumen = resumen.sort_values("total", ascending=True).tail(12)

    fig = go.Figure()
    fig.add_bar(
        name="Con stock", y=resumen["marca"], x=resumen["con_stock"],
        orientation="h", marker_color="#32d74b", marker_opacity=0.8
    )
    fig.add_bar(
        name="Sin stock", y=resumen["marca"], x=resumen["sin_stock"],
        orientation="h", marker_color="#ff375f", marker_opacity=0.9
    )
    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11, color="#8b95a8"),
        height=320, margin=dict(l=0, r=10, t=10, b=10),
        legend=dict(orientation="h", y=-0.08, font_size=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _panel_config_rapida(tasa_actual: float):
    """Panel de configuración rápida en el dashboard."""
    from database import set_config, get_config

    st.markdown(f"""
    <div style="font-size:12px;color:var(--nx-text2);margin-bottom:8px">
        💵 Tasa actual: <strong style="color:var(--nx-text)">${tasa_actual:,.0f} ARS/USD</strong>
    </div>
    """, unsafe_allow_html=True)

    nueva_tasa = st.number_input(
        "Actualizar USD/ARS", min_value=100.0, max_value=99999.0,
        value=tasa_actual, step=50.0, key="dash_tasa",
        label_visibility="collapsed"
    )
    if st.button("💾 Guardar tasa", width='stretch', key="dash_save_tasa"):
        set_config("tasa_usd_ars", str(int(nueva_tasa)))
        try:
            from utils.helpers import notificar_telegram, notificar_picos_demanda
            from modules.ia_engine import motor_ia
            import threading
            alertas = motor_ia.alertas_margen_dolar(nueva_tasa)
            msg = f"💵 *Tasa actualizada:* ${nueva_tasa:,.0f} ARS/USD"
            if alertas:
                msg += f"\n⚠️ {len(alertas)} artículos con margen caído"
            notificar_telegram(msg)
            threading.Thread(target=notificar_picos_demanda, daemon=True).start()
        except Exception:
            pass
        st.success(f"✅ Tasa guardada: ${nueva_tasa:,.0f}")
        st.rerun()

    st.markdown("---")

    lead = int(get_config("lead_time_dias", int) or 30)
    st.markdown(f"⏱️ Lead time actual: **{lead} días**")
    nuevo_lead = st.slider("Lead time (días)", 7, 120, lead, key="dash_lead")
    if nuevo_lead != lead:
        set_config("lead_time_dias", str(nuevo_lead))

    st.markdown("---")
    ultima = query_to_df(
        "SELECT importado_en FROM importaciones_log ORDER BY importado_en DESC LIMIT 1"
    )
    if not ultima.empty:
        st.markdown(f"🕐 Última carga: **{str(ultima.iloc[0]['importado_en'])[:16]}**")
    st.markdown(
        "<a href='?page=Importar' style='font-size:13px;color:var(--nx-accent);text-decoration:none'>"
        "📥 Cargar nuevos archivos →</a>",
        unsafe_allow_html=True
    )


def _panel_sin_datos():
    """Panel de bienvenida cuando no hay datos."""
    st.markdown("""
    <div style="background:var(--nx-card);border:1px solid var(--nx-border);
                border-radius:16px;padding:32px;text-align:center;margin-top:16px">
        <div style="font-size:48px;margin-bottom:16px">📦</div>
        <div style="font-size:18px;font-weight:700;color:var(--nx-text);margin-bottom:8px">
            Empezá cargando tus datos de Flexxus</div>
        <div style="font-size:14px;color:var(--nx-text2);margin-bottom:24px">
            El sistema necesita al menos el archivo de <strong>Optimización de Stock</strong>
            para mostrarte los KPIs de módulos.
        </div>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
            <div style="background:rgba(10,132,255,.1);border:1px solid rgba(10,132,255,.3);
                        border-radius:10px;padding:12px 20px;font-size:13px;color:var(--nx-text2)">
                1️⃣ <strong>Optimización de Stock</strong><br>
                <span style="font-size:11px">Módulos, demanda, stock actual</span>
            </div>
            <div style="background:rgba(10,132,255,.1);border:1px solid rgba(10,132,255,.3);
                        border-radius:10px;padding:12px 20px;font-size:13px;color:var(--nx-text2)">
                2️⃣ <strong>Lista de Precios</strong><br>
                <span style="font-size:11px">Lista 1 USD · Lista 4 ML ARS</span>
            </div>
            <div style="background:rgba(10,132,255,.1);border:1px solid rgba(10,132,255,.3);
                        border-radius:10px;padding:12px 20px;font-size:13px;color:var(--nx-text2)">
                3️⃣ <strong>Planilla de Stock</strong><br>
                <span style="font-size:11px">San José · Larrea</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
