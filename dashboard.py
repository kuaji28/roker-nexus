"""
ROKER NEXUS — Dashboard v2.5
- Filtro FR / Mecánico / Ambos
- TOP configurable por el usuario
- Checkboxes: Agregar a Pedido / Borrador / Lista Negra
- Sin texto pisado
- Solo módulos
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from database import query_to_df, get_config, set_config, execute_query


def _tipo(codigo: str) -> str:
    c = str(codigo or "").strip()
    return "fr" if c and c[0].isalpha() else "mecanico"


@st.cache_data(ttl=120)
def _cargar_modulos() -> pd.DataFrame:
    df = query_to_df("""
        SELECT o.codigo,
               COALESCE(a.descripcion, o.descripcion) as descripcion,
               o.demanda_promedio, o.stock_actual,
               o.stock_optimo, o.costo_reposicion,
               COALESCE(p.lista_1, 0) as lista_1,
               COALESCE(p.lista_4, 0) as lista_4,
               COALESCE(a.en_lista_negra, 0) as en_lista_negra
        FROM optimizacion o
        LEFT JOIN articulos a ON o.codigo=a.codigo
        LEFT JOIN precios p ON o.codigo=p.codigo
        WHERE UPPER(COALESCE(a.descripcion, o.descripcion)) LIKE 'MODULO%'
          AND COALESCE(a.en_lista_negra, 0) = 0
    """)
    if df.empty:
        return df
    df["tipo"] = df["codigo"].apply(_tipo)
    df["stock_actual"]     = df["stock_actual"].fillna(0)
    df["demanda_promedio"] = df["demanda_promedio"].fillna(0).clip(lower=0)
    df["costo_reposicion"] = df["costo_reposicion"].fillna(0)
    df["a_pedir"]   = (df["stock_optimo"].fillna(0) - df["stock_actual"]).clip(lower=0)
    df["inversion"] = df["a_pedir"] * df["costo_reposicion"]
    return df


def render():
    # ── Header + controles ───────────────────────────────────
    col_h, col_r = st.columns([5, 1])
    with col_h:
        st.markdown("""
        <h1 style="margin:0 0 4px;font-size:26px;font-weight:700">📊 Dashboard</h1>
        <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
        Vista ejecutiva de módulos · Solo FR + Mecánico</p>
        """, unsafe_allow_html=True)
    with col_r:
        if st.button("🔄", width='stretch', help="Actualizar"):
            st.cache_data.clear()
            st.rerun()

    # ── Filtros ──────────────────────────────────────────────
    col_prov, col_top, _ = st.columns([2, 2, 4])
    with col_prov:
        filtro_prov = st.radio(
            "Proveedor",
            ["🔵 FR", "🟡 Mecánico", "⚫ Ambos"],
            index=2, horizontal=True, key="dash_prov"
        )
    with col_top:
        n_top = st.number_input("Top N", min_value=5, max_value=100,
                                 value=10, step=5, key="dash_top")

    df_all = _cargar_modulos()

    if df_all.empty:
        _panel_sin_datos()
        return

    # Aplicar filtro proveedor
    if "FR" in filtro_prov:
        df = df_all[df_all["tipo"] == "fr"]
    elif "Mec" in filtro_prov:
        df = df_all[df_all["tipo"] == "mecanico"]
    else:
        df = df_all.copy()

    tasa = float(get_config("tasa_usd_ars", float) or 1420)

    # ── KPIs ────────────────────────────────────────────────
    sin_stock   = df[df["stock_actual"] == 0]
    bajo_min    = df[(df["stock_actual"] > 0) & (df["stock_actual"] < df["stock_optimo"])]
    inv_tot     = float(df["inversion"].sum())
    vp = df[(df["stock_actual"] == 0) & (df["demanda_promedio"] > 0)].copy()
    vp["vp"] = vp.apply(
        lambda r: r["demanda_promedio"] * r["lista_4"] if r["lista_4"] > 0
        else r["demanda_promedio"] * r["costo_reposicion"] * tasa * 1.8,
        axis=1
    )
    venta_perdida_usd = float(vp["vp"].sum() / tasa) if tasa > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    _kpi(c1, "🔴 Sin stock",    len(sin_stock),  f"de {len(df)} módulos",     "rojo")
    _kpi(c2, "🟡 Bajo mínimo",  len(bajo_min),   f"con stock insuficiente",   "amarillo")
    _kpi(c3, "💸 Venta perdida/mes", f"USD {venta_perdida_usd:,.0f}",
              f"≈ ${venta_perdida_usd*tasa:,.0f} ARS", "rojo" if venta_perdida_usd > 500 else "amarillo")
    _kpi(c4, "💰 Inversión req.", f"USD {inv_tot:,.0f}",
              f"≈ ${inv_tot*tasa:,.0f} ARS", "azul")

    # ── Bloques FR vs Mecánico ───────────────────────────────
    if "Ambos" in filtro_prov:
        st.markdown("---")
        _bloques_fr_mec(df_all, tasa)

    # ── Top Críticos ─────────────────────────────────────────
    st.markdown("---")
    col_crit, col_urg = st.columns(2)

    with col_crit:
        st.markdown(f"### 🔴 Top {int(n_top)} Críticos — stock = 0")
        criticos = df[df["stock_actual"] == 0].sort_values(
            "demanda_promedio", ascending=False
        ).head(int(n_top))
        _tabla_acciones(criticos, "crit", tasa)

    with col_urg:
        st.markdown(f"### 🟡 Top {int(n_top)} Urgentes — bajo mínimo")
        urg = df[(df["stock_actual"] > 0) & (df["stock_actual"] < df["stock_optimo"])
                  & (df["demanda_promedio"] > 0)].copy()
        if not urg.empty:
            urg["dias_cob"] = (urg["stock_actual"] / (urg["demanda_promedio"] / 30)).round(0)
            urg = urg.sort_values("dias_cob").head(int(n_top))
        _tabla_acciones(urg, "urg", tasa)

    # ── Gráfico + Config rápida ──────────────────────────────
    st.markdown("---")
    col_g, col_c = st.columns([3, 2])
    with col_g:
        st.markdown("### 📈 Stock por marca")
        _grafico_marcas(df)
    with col_c:
        st.markdown("### ⚡ Config rápida")
        _config_rapida(tasa)

    # ── Últimas importaciones ────────────────────────────────
    with st.expander("📥 Últimas importaciones", expanded=False):
        df_log = query_to_df(
            "SELECT tipo_archivo, nombre_archivo, filas_importadas, estado, importado_en "
            "FROM importaciones_log ORDER BY importado_en DESC LIMIT 8"
        )
        if df_log.empty:
            st.info("Sin importaciones.")
        else:
            st.dataframe(df_log, hide_index=True, width='stretch')


def _tabla_acciones(df: pd.DataFrame, prefix: str, tasa: float):
    """Tabla con checkboxes y acciones: Borrador / Lista Negra."""
    if df.empty:
        st.success("✅ Sin artículos en esta categoría")
        return

    seleccionados = []

    for idx, (_, r) in enumerate(df.iterrows()):
        codigo   = str(r["codigo"])
        desc     = str(r.get("descripcion", ""))[:40]
        tipo_lbl = "🔵 FR" if r["tipo"] == "fr" else "🟡 MEC"
        dem      = float(r.get("demanda_promedio") or 0)
        stk      = float(r.get("stock_actual") or 0)
        costo    = float(r.get("costo_reposicion") or 0)
        dias     = int(r.get("dias_cob", 0)) if "dias_cob" in r.index else 0

        col_cb, col_info = st.columns([1, 10])
        sel = col_cb.checkbox("", key=f"sel_{prefix}_{idx}")
        if sel:
            seleccionados.append(r)

        with col_info:
            if stk == 0:
                badge = '<span style="color:#ff375f;font-weight:700">STOCK 0</span>'
                sub   = f"{dem:.1f}/mes"
            else:
                color = "#ff375f" if dias < 7 else "#ff9f0a"
                badge = f'<span style="color:{color};font-weight:700">{dias} días</span>'
                sub   = f"{int(stk)} uds"

            st.markdown(
                f'<div style="padding:4px 0;border-bottom:1px solid var(--nx-border)">'
                f'<span style="font-size:10px;color:var(--nx-text3)">{tipo_lbl}</span> '
                f'<span style="font-size:13px;font-weight:600">{desc}</span> '
                f'{badge}<br>'
                f'<span style="font-size:10px;color:var(--nx-text3)">{codigo} · {sub}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # Acciones sobre seleccionados
    if seleccionados:
        n = len(seleccionados)
        st.markdown(f"**{n} artículo(s) seleccionado(s):**")
        ca, cb, cc = st.columns(3)

        if ca.button("📝 → Borrador", key=f"btn_bor_{prefix}", width='stretch'):
            for r in seleccionados:
                execute_query("""
                    INSERT OR IGNORE INTO borrador_pedido
                    (texto_original, codigo_flexxus, descripcion, tipo_codigo,
                     cantidad, precio_usd, subtotal_usd, match_confirmado, estado, origen)
                    VALUES (?,?,?,?,1,?,?,1,'confirmado','dashboard')
                """, (str(r["codigo"]), str(r["codigo"]), str(r.get("descripcion","")),
                      str(r["tipo"]), float(r.get("costo_reposicion",0)),
                      float(r.get("costo_reposicion",0))), fetch=False)
            st.success(f"✅ {n} artículos → Borrador")

        if cb.button("🚫 Lista negra", key=f"btn_neg_{prefix}", width='stretch'):
            for r in seleccionados:
                execute_query(
                    "UPDATE articulos SET en_lista_negra=1 WHERE codigo=?",
                    (str(r["codigo"]),), fetch=False
                )
            st.cache_data.clear()
            st.success(f"✅ {n} artículos → Lista Negra")
            st.rerun()

        if cc.button("📋 Ver códigos", key=f"btn_cod_{prefix}", width='stretch'):
            for r in seleccionados:
                st.code(str(r["codigo"]))


def _bloques_fr_mec(df: pd.DataFrame, tasa: float):
    col_fr, col_mec = st.columns(2)

    for col, tipo, label, color, border in [
        (col_fr,  "fr",       "FR (AITECH) — letra",  "#0a84ff", "rgba(10,132,255,.2)"),
        (col_mec, "mecanico", "MECÁNICO — número",    "#ff9f0a", "rgba(255,159,10,.2)"),
    ]:
        sub = df[df["tipo"] == tipo]
        total   = len(sub)
        ok      = int((sub["stock_actual"] >= sub["stock_optimo"]).sum())
        bajo    = int(((sub["stock_actual"] > 0) & (sub["stock_actual"] < sub["stock_optimo"])).sum())
        sin_stk = int((sub["stock_actual"] == 0).sum())
        pct     = round(ok / max(total, 1) * 100)

        with col:
            st.markdown(f"""
            <div style="background:rgba(0,0,0,.15);border:1px solid {border};
                        border-left:3px solid {color};border-radius:12px;padding:14px 16px">
                <div style="font-size:11px;color:{color};font-weight:700;
                            text-transform:uppercase;letter-spacing:.8px">{label}</div>
                <div style="display:flex;gap:16px;margin-top:10px;flex-wrap:wrap">
                    <div><div style="font-size:20px;font-weight:700">{total}</div>
                         <div style="font-size:11px;color:var(--nx-text2)">Total</div></div>
                    <div><div style="font-size:20px;font-weight:700;color:#32d74b">{ok}</div>
                         <div style="font-size:11px;color:var(--nx-text2)">Stock OK</div></div>
                    <div><div style="font-size:20px;font-weight:700;color:#ff9f0a">{bajo}</div>
                         <div style="font-size:11px;color:var(--nx-text2)">Bajo mín.</div></div>
                    <div><div style="font-size:20px;font-weight:700;color:#ff375f">{sin_stk}</div>
                         <div style="font-size:11px;color:var(--nx-text2)">Sin stock</div></div>
                </div>
                <div style="margin-top:10px;height:5px;background:var(--nx-border);
                            border-radius:3px;overflow:hidden">
                    <div style="height:100%;width:{pct}%;background:#32d74b"></div>
                </div>
                <div style="font-size:10px;color:var(--nx-text3);margin-top:3px">
                    {pct}% con stock suficiente</div>
            </div>""", unsafe_allow_html=True)


def _kpi(col, titulo: str, valor, sub: str, color: str):
    colores = {
        "rojo":     ("#ff375f", "rgba(255,55,95,.1)",  "rgba(255,55,95,.25)"),
        "amarillo": ("#ff9f0a", "rgba(255,159,10,.1)", "rgba(255,159,10,.25)"),
        "azul":     ("#0a84ff", "rgba(10,132,255,.1)", "rgba(10,132,255,.25)"),
        "verde":    ("#32d74b", "rgba(50,215,75,.1)",  "rgba(50,215,75,.25)"),
    }
    c, bg, bord = colores.get(color, colores["azul"])
    col.markdown(f"""
    <div style="background:{bg};border:1px solid {bord};border-top:3px solid {c};
                border-radius:12px;padding:12px 14px;min-height:90px">
        <div style="font-size:10px;color:var(--nx-text2);font-weight:600;
                    text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px">{titulo}</div>
        <div style="font-size:22px;font-weight:700;color:{c};line-height:1.1">{valor}</div>
        <div style="font-size:11px;color:var(--nx-text2);margin-top:3px">{sub}</div>
    </div>""", unsafe_allow_html=True)


def _grafico_marcas(df: pd.DataFrame):
    if df.empty:
        st.caption("Sin datos")
        return

    def marca(desc):
        d = str(desc).upper()
        for k, l in [("SAM","Samsung"),("IPH","iPhone"),("MOT","Motorola"),
                      ("LG","LG"),("XIA","Xiaomi"),("ALC","Alcatel"),
                      ("HUA","Huawei"),("TCL","TCL"),("INF","Infinix"),
                      ("NOK","Nokia"),("OPPO","OPPO"),("TECNO","Tecno")]:
            if k in d: return l
        return "Otros"

    df = df.copy()
    df["marca"] = df["descripcion"].apply(marca)
    r = df.groupby("marca").agg(
        total=("codigo","count"),
        sin=("stock_actual", lambda x: (x==0).sum())
    ).reset_index()
    r["ok"] = r["total"] - r["sin"]
    r = r.sort_values("total", ascending=True).tail(12)

    fig = go.Figure()
    fig.add_bar(name="Con stock", y=r["marca"], x=r["ok"],
                orientation="h", marker_color="#32d74b", marker_opacity=.8)
    fig.add_bar(name="Sin stock", y=r["marca"], x=r["sin"],
                orientation="h", marker_color="#ff375f", marker_opacity=.9)
    fig.update_layout(
        barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11, color="#8b95a8"), height=300,
        margin=dict(l=0, r=10, t=5, b=5),
        legend=dict(orientation="h", y=-0.1, font_size=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _config_rapida(tasa: float):
    nueva = st.number_input("💵 USD/ARS", min_value=100.0, max_value=99999.0,
                             value=tasa, step=50.0, key="dash_tasa",
                             label_visibility="visible")
    if st.button("💾 Guardar tasa", width='stretch', type="primary", key="dash_save"):
        set_config("tasa_usd_ars", str(int(nueva)))
        try:
            from utils.helpers import notificar_telegram
            from modules.ia_engine import motor_ia
            alertas = motor_ia.alertas_margen_dolar(nueva)
            msg = f"💵 *Tasa actualizada:* ${nueva:,.0f} ARS/USD"
            if alertas:
                msg += f"\n⚠️ {len(alertas)} artículos con margen caído"
            notificar_telegram(msg)
        except Exception:
            pass
        st.cache_data.clear()
        st.success(f"✅ ${nueva:,.0f}")
        st.rerun()

    st.markdown("---")
    lead = int(get_config("lead_time_dias", int) or 30)
    nuevo_lead = st.slider("⏱️ Lead time (días)", 7, 120, lead, key="dash_lead")
    if nuevo_lead != lead:
        set_config("lead_time_dias", str(nuevo_lead))

    st.markdown("---")
    ult = query_to_df(
        "SELECT importado_en FROM importaciones_log ORDER BY importado_en DESC LIMIT 1"
    )
    if not ult.empty:
        st.caption(f"🕐 Última carga: {str(ult.iloc[0]['importado_en'])[:16]}")


def _panel_sin_datos():
    st.info("📥 **Sin datos.** Cargá primero el archivo de **Optimización de Stock** desde Cargar.")
