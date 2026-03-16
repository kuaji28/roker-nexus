"""
ROKER NEXUS — Dashboard v2.1
Vista ejecutiva de MÓDULOS — FR + Mecánico.
Filtros: FR/Mecánico/Ambos | Top N configurable | Agregar a lista negra/borrador
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from database import query_to_df, get_config, set_config, execute_query
from utils.horarios import ahora
from utils.helpers import fmt_usd, fmt_ars, fmt_num


def _es_modulo(desc: str) -> bool:
    """
    Módulos = pantallas de celular (display + touch).
    Filtro POSITIVO: la descripción DEBE contener alguna de las palabras clave.
    Baterías, pins, placas, cables, auriculares, etc. no las contienen → quedan fuera.
    """
    d = str(desc or "").upper().strip()
    return any(p in d for p in ("MODULO", "MODULE", "DISPLAY", "PANTALLA"))

def _tipo(codigo: str) -> str:
    c = str(codigo or "").strip()
    return "fr" if (c and c[0].isalpha()) else "mecanico"


def _get_transito_por_codigo() -> dict:
    """Lee ítems en tránsito desde cotizacion_items (fuente real)."""
    try:
        df = query_to_df("""
            SELECT ci.codigo_flexxus as codigo, SUM(ci.cantidad_pedida - COALESCE(ci.cantidad_recibida,0)) as en_transito
            FROM cotizacion_items ci
            JOIN cotizaciones c ON ci.cotizacion_id = c.id
            WHERE c.estado = 'en_transito'
              AND ci.codigo_flexxus IS NOT NULL
              AND ci.codigo_flexxus != ''
            GROUP BY ci.codigo_flexxus
            HAVING en_transito > 0
        """)
        if df.empty:
            return {}
        return df.set_index("codigo")["en_transito"].to_dict()
    except Exception:
        return {}


def _get_kpis(filtro_prov: str = "Ambos") -> dict:
    """KPIs reales filtrados a módulos."""
    try:
        tasa = float(get_config("tasa_usd_ars", float) or 1420)

        df = query_to_df("""
            SELECT o.codigo,
                   COALESCE(a.descripcion, o.descripcion) as descripcion,
                   o.demanda_promedio, o.stock_actual,
                   o.stock_optimo, o.costo_reposicion,
                   p.lista_1, p.lista_4,
                   COALESCE(a.en_lista_negra, 0) as en_lista_negra
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo=a.codigo
            LEFT JOIN precios p ON o.codigo=p.codigo
            WHERE COALESCE(a.en_lista_negra, 0) = 0
        """)

        if df.empty:
            return {"ok": False}

        # Filtrar módulos
        df = df[df["descripcion"].apply(_es_modulo)].copy()
        df["tipo"] = df["codigo"].apply(_tipo)

        # Aplicar filtro proveedor
        if filtro_prov == "AI-TECH":
            df = df[df["tipo"] == "fr"]
        elif filtro_prov == "Mecánico":
            df = df[df["tipo"] == "mecanico"]

        if df.empty:
            return {"ok": False, "error": "Sin módulos para el filtro seleccionado"}

        # Datos numéricos
        df["stock_actual"]     = df["stock_actual"].fillna(0).astype(float)
        df["demanda_promedio"] = df["demanda_promedio"].fillna(0).clip(lower=0)
        df["costo_reposicion"] = df["costo_reposicion"].fillna(0)
        df["lista_4"]          = df["lista_4"].fillna(0)

        # Tránsito real desde cotizaciones
        transito_map = _get_transito_por_codigo()
        df["en_transito"] = df["codigo"].map(transito_map).fillna(0)
        df["stock_real"]   = df["stock_actual"] + df["en_transito"]

        # Métricas
        total_mods    = len(df)
        fr_total      = int((df["tipo"]=="fr").sum())
        mec_total     = int((df["tipo"]=="mecanico").sum())
        sin_stock     = df[df["stock_actual"]==0]
        fr_sin        = int((sin_stock["tipo"]=="fr").sum())
        mec_sin       = int((sin_stock["tipo"]=="mecanico").sum())
        bajo_min      = df[(df["stock_actual"]>0)&(df["stock_actual"]<df["stock_optimo"])]
        fr_bajo       = int((bajo_min["tipo"]=="fr").sum())
        mec_bajo      = int((bajo_min["tipo"]=="mecanico").sum())

        # En tránsito
        en_transito_items = int((df["en_transito"]>0).sum())
        en_transito_usd   = float((df["en_transito"]*df["costo_reposicion"]).sum())

        # Inversión
        df["a_pedir"]   = (df["stock_optimo"] - df["stock_real"]).clip(lower=0)
        df["inversion"] = df["a_pedir"] * df["costo_reposicion"]
        inv_fr  = float(df[df["tipo"]=="fr"]["inversion"].sum())
        inv_mec = float(df[df["tipo"]=="mecanico"]["inversion"].sum())
        inv_tot = inv_fr + inv_mec

        # Venta perdida
        vp = df[(df["stock_actual"]==0)&(df["demanda_promedio"]>0)].copy()
        vp["vp_ars"] = vp.apply(
            lambda r: r["demanda_promedio"]*r["lista_4"] if r["lista_4"]>0
            else r["demanda_promedio"]*r["costo_reposicion"]*tasa*1.8, axis=1)
        vp_usd = float(vp["vp_ars"].sum()/tasa)

        # Valor inventario
        valor_inv = float((df["stock_actual"]*df["costo_reposicion"]).sum())

        # Cobertura promedio
        df_dem = df[df["demanda_promedio"]>0].copy()
        df_dem["dias"] = (df_dem["stock_real"]/(df_dem["demanda_promedio"]/30))
        cob_prom = float(df_dem["dias"].clip(upper=999).mean()) if not df_dem.empty else 0

        # Overrides
        try:
            ov = query_to_df("SELECT COUNT(*) as n FROM demanda_manual")
            overrides = int(ov.iloc[0]["n"]) if not ov.empty else 0
        except Exception:
            overrides = 0

        # Críticos y urgentes
        criticos = df[df["stock_actual"]==0].sort_values("demanda_promedio",ascending=False)
        urgentes = df[(df["stock_actual"]>0)&(df["stock_actual"]<df["stock_optimo"])&(df["demanda_promedio"]>0)].copy()
        urgentes["dias_cob"] = (urgentes["stock_actual"]/(urgentes["demanda_promedio"]/30)).round(0)
        urgentes = urgentes.sort_values("dias_cob")

        return {
            "ok": True, "tasa": tasa, "df": df,
            "total_mods": total_mods, "fr_total": fr_total, "mec_total": mec_total,
            "fr_sin": fr_sin, "mec_sin": mec_sin,
            "fr_bajo": fr_bajo, "mec_bajo": mec_bajo,
            "en_transito_items": en_transito_items, "en_transito_usd": en_transito_usd,
            "inv_fr": inv_fr, "inv_mec": inv_mec, "inv_tot": inv_tot,
            "vp_usd": vp_usd, "valor_inv": valor_inv,
            "cob_prom": cob_prom, "overrides": overrides,
            "criticos": criticos, "urgentes": urgentes,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _kpi(titulo, valor, sub, color):
    COLS = {"rojo":("#ff375f","rgba(255,55,95,.12)","rgba(255,55,95,.25)"),
            "verde":("#32d74b","rgba(50,215,75,.12)","rgba(50,215,75,.25)"),
            "amarillo":("#ff9f0a","rgba(255,159,10,.12)","rgba(255,159,10,.25)"),
            "azul":("#0a84ff","rgba(10,132,255,.12)","rgba(10,132,255,.25)"),
            "teal":("#5ac8fa","rgba(90,200,250,.12)","rgba(90,200,250,.25)"),
            "purp":("#bf5af2","rgba(191,90,242,.12)","rgba(191,90,242,.25)")}
    c,bg,brd = COLS.get(color,COLS["azul"])
    st.markdown(f"""<div style="background:{bg};border:1px solid {brd};border-top:3px solid {c};
        border-radius:12px;padding:12px 14px;min-height:90px">
        <div style="font-size:10px;color:var(--nx-text2);font-weight:700;text-transform:uppercase;
                    letter-spacing:.6px;margin-bottom:4px">{titulo}</div>
        <div style="font-size:22px;font-weight:700;color:{c};line-height:1.1">{valor}</div>
        <div style="font-size:11px;color:var(--nx-text3);margin-top:3px">{sub}</div>
    </div>""", unsafe_allow_html=True)


def _panel_salud_datos():
    """Widget compacto de salud de datos — siempre visible en la parte superior del Dashboard."""
    try:
        from database import get_file_health
        slots = get_file_health()
    except Exception:
        return  # Silencioso si la tabla aún no existe

    total    = len(slots)
    ok_count = sum(1 for s in slots if s["estado"] == "ok")
    stale    = [s for s in slots if s["estado"] in ("stale", "critico")]
    nunca    = [s for s in slots if s["estado"] == "nunca"]
    criticos = [s for s in stale if s["critico"]]

    # Si todo está bien: sólo muestra badge verde discreto
    if ok_count == total:
        st.markdown(
            f'<div style="text-align:right;margin-bottom:4px">'
            f'<span style="font-size:11px;color:#34C759">✅ Todos los datos al día ({total}/{total})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    # Si hay problemas: expandible con detalle
    resumen_parts = []
    if criticos:
        nombres = ", ".join(s["label"] for s in criticos[:2])
        resumen_parts.append(f"🔴 **{len(criticos)} crítico(s):** {nombres}")
    if nunca:
        nombres = ", ".join(s["label"] for s in nunca[:3])
        resumen_parts.append(f"⚫ **{len(nunca)} sin cargar:** {nombres}")
    resumen = " · ".join(resumen_parts) if resumen_parts else f"{ok_count}/{total} al día"

    pct = int(ok_count / total * 100)
    color = "#FF3B30" if pct < 40 else ("#FF9F0A" if pct < 80 else "#34C759")

    with st.expander(f"📁 Datos: {ok_count}/{total} archivos al día · {resumen}", expanded=bool(criticos)):
        COLORES = {
            "ok":      ("#34C759", "🟢"),
            "stale":   ("#FF9F0A", "🟡"),
            "critico": ("#FF3B30", "🔴"),
            "nunca":   ("#8E8E93", "⚫"),
        }
        cols = st.columns(2)
        for i, s in enumerate(slots):
            color_s, dot = COLORES.get(s["estado"], ("#8E8E93", "⚫"))
            dias_txt = (f"hace {s['dias_sin_cargar']}d" if s.get("dias_sin_cargar") and s["dias_sin_cargar"] > 0
                        else ("hoy" if s.get("dias_sin_cargar") == 0 else "—"))
            with cols[i % 2]:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:3px 0;'
                    f'border-bottom:1px solid var(--nx-border,#3a3a3c);font-size:12px">'
                    f'<span>{s["icono"]} {s["label"]}</span>'
                    f'<span style="color:{color_s};font-weight:600">{dot} {dias_txt}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown(
            '<div style="text-align:right;margin-top:8px">'
            '<span style="font-size:11px;color:var(--nx-text3)">Actualizá desde la pestaña ▶ Cargar</span>'
            '</div>',
            unsafe_allow_html=True,
        )


def render():
    # ── Header con filtros ─────────────────────────────────────
    c_h, c_f1, c_f2, c_ref = st.columns([2.5, 1.2, 1, 0.5])
    with c_h:
        st.markdown("""
        <h1 style="margin:0 0 2px;font-size:24px;font-weight:700">📊 Dashboard</h1>
        <p style="color:var(--nx-text2);font-size:12px;margin:0">Vista ejecutiva de módulos — AI-TECH + Mecánico</p>
        """, unsafe_allow_html=True)
    with c_f1:
        filtro_prov = st.selectbox("Proveedor", ["Ambos","AI-TECH","Mecánico"], index=0, key="dash_prov",
                                    label_visibility="collapsed")
    with c_f2:
        top_n = st.selectbox("Top", [5,10,15,20,30,50], index=1, key="dash_topn",
                              label_visibility="collapsed",
                              format_func=lambda x: f"Top {x}")
    with c_ref:
        if st.button("🔄", help="Actualizar"):
            st.rerun()

    # ── Panel salud de datos (compacto) ───────────────────────
    _panel_salud_datos()

    kpis = _get_kpis(filtro_prov)

    if not kpis.get("ok"):
        err = kpis.get("error","")
        if "no such table" in err or not err:
            st.info("📥 **Sin datos todavía.** Cargá el archivo de **Optimización de Stock** desde la pestaña Cargar.")
        else:
            st.error(f"Error: {err}")
        _panel_vacio()
        return

    tasa = kpis["tasa"]

    # ── Banner tránsito ───────────────────────────────────────
    if kpis["en_transito_items"] > 0:
        st.markdown(f"""<div style="background:rgba(90,200,250,.08);border:1px solid rgba(90,200,250,.25);
            border-radius:10px;padding:9px 16px;margin-bottom:10px;
            display:flex;justify-content:space-between;align-items:center">
            <span style="color:#5ac8fa;font-size:13px;font-weight:600">
                ✈️ {kpis['en_transito_items']} SKU(s) en tránsito</span>
            <span style="color:var(--nx-text3);font-size:12px">
                Valor: USD ${kpis['en_transito_usd']:,.2f} — stock_real ya incluye estas unidades</span>
        </div>""", unsafe_allow_html=True)

    # ── Semáforo 4 tarjetas ───────────────────────────────────
    st.markdown("### 🚦 Estado de Módulos")
    c1,c2,c3,c4 = st.columns(4)
    with c1: _kpi("📦 FR sin stock", kpis["fr_sin"],
                   f"de {kpis['fr_total']} FR · +{kpis['fr_bajo']} bajo mín.",
                   "rojo" if kpis["fr_sin"]>20 else "verde")
    with c2: _kpi("📦 Mecánico sin stock", kpis["mec_sin"],
                   f"de {kpis['mec_total']} MEC · +{kpis['mec_bajo']} bajo mín.",
                   "rojo" if kpis["mec_sin"]>5 else "verde")
    with c3: _kpi("💸 Venta perdida/mes", f"USD {kpis['vp_usd']:,.0f}",
                   f"≈ ARS ${kpis['vp_usd']*tasa:,.0f}", "rojo" if kpis["vp_usd"]>1000 else "amarillo")
    with c4: _kpi("💰 Inversión requerida", f"USD {kpis['inv_tot']:,.0f}",
                   f"FR ${kpis['inv_fr']:,.0f} · MEC ${kpis['inv_mec']:,.0f}", "amarillo")

    st.markdown("---")

    # ── 6 KPIs operativos ────────────────────────────────────
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    with k1: _kpi("Total", kpis["total_mods"], "AI-TECH + Mecánico", "azul")
    with k2: _kpi("Sin Stock", kpis["fr_sin"]+kpis["mec_sin"], "Acción inmediata", "rojo")
    with k3: _kpi("Bajo Mínimo", kpis["fr_bajo"]+kpis["mec_bajo"], "Próxima compra", "amarillo")
    with k4: _kpi("✈️ En Tránsito", kpis["en_transito_items"], "SKUs con pedido", "teal")
    with k5: _kpi("Cob. Promedio", f"{kpis['cob_prom']:.0f}d", "Días cobertura global", "verde")
    with k6: _kpi("Overrides", kpis["overrides"], "Demanda manual", "azul")

    # ── 4 KPIs financieros ───────────────────────────────────
    f1,f2,f3,f4 = st.columns(4)
    with f1: _kpi("💼 Valor Inventario", f"USD {kpis['valor_inv']:,.0f}",
                   f"≈ ARS ${kpis['valor_inv']*tasa:,.0f}", "purp")
    with f2: _kpi("💳 Inversión Req.", f"USD {kpis['inv_tot']:,.0f}",
                   f"≈ ARS ${kpis['inv_tot']*tasa:,.0f}", "amarillo")
    with f3: _kpi("💸 Costo Oport.", f"USD {kpis['vp_usd']:,.0f}",
                   "Stock=0 con demanda activa", "rojo")
    with f4: _kpi(f"FR {kpis['fr_total']} / MEC {kpis['mec_total']}",
                   "", "Distribución proveedores", "verde")

    st.markdown("---")

    # ── AI-TECH vs Mecánico ─────────────────────────────────
    st.markdown("### 📊 AI-TECH vs Mecánico")
    col_fr, col_mec = st.columns(2)
    with col_fr:
        ok_fr = kpis["fr_total"] - kpis["fr_sin"] - kpis["fr_bajo"]
        st.markdown(f"""<div style="background:rgba(10,132,255,.08);border:1px solid rgba(10,132,255,.2);
            border-left:3px solid #0a84ff;border-radius:12px;padding:14px 16px">
            <div style="font-size:10px;color:#0a84ff;font-weight:700;text-transform:uppercase;letter-spacing:.8px">
                FR (AITECH) — Código con letra</div>
            <div style="display:flex;gap:20px;margin-top:10px">
                <div><div style="font-size:22px;font-weight:700">{kpis['fr_total']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Total</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#32d74b">{ok_fr}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Con stock OK</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#ff9f0a">{kpis['fr_bajo']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Bajo mínimo</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#ff375f">{kpis['fr_sin']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Sin stock</div></div>
            </div>
            <div style="margin-top:10px;height:6px;background:rgba(255,255,255,.08);border-radius:3px;overflow:hidden">
                <div style="height:100%;width:{ok_fr/max(kpis['fr_total'],1)*100:.0f}%;background:#32d74b;border-radius:3px"></div>
            </div>
            <div style="font-size:10px;color:var(--nx-text3);margin-top:4px">{ok_fr/max(kpis['fr_total'],1)*100:.0f}% con stock suficiente</div>
        </div>""", unsafe_allow_html=True)
    with col_mec:
        ok_mec = kpis["mec_total"] - kpis["mec_sin"] - kpis["mec_bajo"]
        st.markdown(f"""<div style="background:rgba(255,159,10,.08);border:1px solid rgba(255,159,10,.2);
            border-left:3px solid #ff9f0a;border-radius:12px;padding:14px 16px">
            <div style="font-size:10px;color:#ff9f0a;font-weight:700;text-transform:uppercase;letter-spacing:.8px">
                MECÁNICO — Código con número</div>
            <div style="display:flex;gap:20px;margin-top:10px">
                <div><div style="font-size:22px;font-weight:700">{kpis['mec_total']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Total</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#32d74b">{ok_mec}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Con stock OK</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#ff9f0a">{kpis['mec_bajo']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Bajo mínimo</div></div>
                <div><div style="font-size:22px;font-weight:700;color:#ff375f">{kpis['mec_sin']}</div>
                     <div style="font-size:11px;color:var(--nx-text2)">Sin stock</div></div>
            </div>
            <div style="margin-top:10px;height:6px;background:rgba(255,255,255,.08);border-radius:3px;overflow:hidden">
                <div style="height:100%;width:{ok_mec/max(kpis['mec_total'],1)*100:.0f}%;background:#32d74b;border-radius:3px"></div>
            </div>
            <div style="font-size:10px;color:var(--nx-text3);margin-top:4px">{ok_mec/max(kpis['mec_total'],1)*100:.0f}% con stock suficiente</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Críticos y Urgentes con acciones ─────────────────────
    col_crit, col_urg = st.columns(2)

    with col_crit:
        criticos = kpis["criticos"].head(top_n)
        st.markdown(f"### 🔴 Top {top_n} Críticos — stock = 0")
        if criticos.empty:
            st.success("✅ Sin críticos")
        else:
            df_c = criticos.copy()
            df_c["Tipo"]     = df_c["tipo"].map({"fr": "FR", "mecanico": "MEC"})
            df_c["Artículo"] = df_c["descripcion"].str[:45]
            df_c["Dem/mes"]  = df_c["demanda_promedio"].round(1)
            df_c["Tránsito"] = df_c["en_transito"].fillna(0).astype(int)
            df_c["USD perd"] = (df_c["demanda_promedio"] * df_c["costo_reposicion"]).round(0)
            st.dataframe(
                df_c[["codigo","Tipo","Artículo","Dem/mes","Tránsito","USD perd"]],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "codigo":    st.column_config.TextColumn("Código", width="small"),
                    "Tipo":      st.column_config.TextColumn("Tipo",   width="small"),
                    "Artículo":  st.column_config.TextColumn("Artículo"),
                    "Dem/mes":   st.column_config.NumberColumn("Dem/mes", format="%.1f"),
                    "Tránsito":  st.column_config.NumberColumn("✈️ Tráns.", format="%d"),
                    "USD perd":  st.column_config.NumberColumn("USD perdido", format="$%.0f"),
                }
            )
            sel_c = st.multiselect("Seleccionar para accionar →",
                                   criticos["codigo"].tolist(), key="crit_sel",
                                   format_func=lambda c: f"{c} — {criticos[criticos['codigo']==c]['descripcion'].values[0][:35]}" if len(criticos[criticos['codigo']==c]) else c)
            if sel_c:
                ca, cb = st.columns(2)
                with ca:
                    if st.button("🚫 Lista negra", key="crit_ln_bulk", use_container_width=True):
                        for cod in sel_c:
                            desc = criticos[criticos["codigo"]==cod]["descripcion"].values[0][:40] if len(criticos[criticos["codigo"]==cod]) else cod
                            execute_query("INSERT OR IGNORE INTO lista_negra (codigo, descripcion, notas) VALUES(?,?,?)",
                                (cod, desc, "Dashboard"), fetch=False)
                        st.success(f"✅ {len(sel_c)} en lista negra"); st.rerun()
                with cb:
                    if st.button("📝 Al borrador", key="crit_bd_bulk", use_container_width=True):
                        for cod in sel_c:
                            row = criticos[criticos["codigo"]==cod]
                            if len(row):
                                r = row.iloc[0]
                                desc = str(r["descripcion"])[:40]
                                execute_query("""INSERT INTO borrador_pedido (texto_original, codigo_flexxus, descripcion, tipo_codigo, estado) VALUES(?,?,?,?,?)""",
                                    (desc, cod, desc, r["tipo"], "pendiente"), fetch=False)
                        st.success(f"✅ {len(sel_c)} al borrador"); st.rerun()

    with col_urg:
        urgentes = kpis["urgentes"].head(top_n)
        st.markdown(f"### 🟡 Top {top_n} Urgentes — bajo mínimo")
        if urgentes.empty:
            st.success("✅ Sin urgentes")
        else:
            df_u = urgentes.copy()
            df_u["Tipo"]      = df_u["tipo"].map({"fr": "FR", "mecanico": "MEC"})
            df_u["Artículo"]  = df_u["descripcion"].str[:45]
            df_u["Stock"]     = df_u["stock_actual"].fillna(0).astype(int)
            df_u["Tránsito"]  = df_u["en_transito"].fillna(0).astype(int)
            df_u["Días cob."] = df_u["dias_cob"].fillna(0).astype(int)
            df_u["Dem/mes"]   = df_u["demanda_promedio"].round(1)
            st.dataframe(
                df_u[["codigo","Tipo","Artículo","Stock","Tránsito","Días cob.","Dem/mes"]],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "codigo":    st.column_config.TextColumn("Código",    width="small"),
                    "Tipo":      st.column_config.TextColumn("Tipo",      width="small"),
                    "Artículo":  st.column_config.TextColumn("Artículo"),
                    "Stock":     st.column_config.NumberColumn("Stock",    format="%d"),
                    "Tránsito":  st.column_config.NumberColumn("✈️ Tráns.", format="%d"),
                    "Días cob.": st.column_config.NumberColumn("Días cob.", format="%d"),
                    "Dem/mes":   st.column_config.NumberColumn("Dem/mes",  format="%.1f"),
                }
            )
            sel_u = st.multiselect("Seleccionar para accionar →",
                                   urgentes["codigo"].tolist(), key="urg_sel",
                                   format_func=lambda c: f"{c} — {urgentes[urgentes['codigo']==c]['descripcion'].values[0][:35]}" if len(urgentes[urgentes['codigo']==c]) else c)
            if sel_u:
                ua, ub = st.columns(2)
                with ua:
                    if st.button("🚫 Lista negra", key="urg_ln_bulk", use_container_width=True):
                        for cod in sel_u:
                            desc = urgentes[urgentes["codigo"]==cod]["descripcion"].values[0][:40] if len(urgentes[urgentes["codigo"]==cod]) else cod
                            execute_query("INSERT OR IGNORE INTO lista_negra (codigo, descripcion, notas) VALUES(?,?,?)",
                                (cod, desc, "Dashboard"), fetch=False)
                        st.success(f"✅ {len(sel_u)} en lista negra"); st.rerun()
                with ub:
                    if st.button("📝 Al borrador", key="urg_bd_bulk", use_container_width=True):
                        for cod in sel_u:
                            row = urgentes[urgentes["codigo"]==cod]
                            if len(row):
                                r = row.iloc[0]
                                desc = str(r["descripcion"])[:40]
                                execute_query("""INSERT INTO borrador_pedido (texto_original, codigo_flexxus, descripcion, tipo_codigo, estado) VALUES(?,?,?,?,?)""",
                                    (desc, cod, desc, r["tipo"], "pendiente"), fetch=False)
                        st.success(f"✅ {len(sel_u)} al borrador"); st.rerun()

    # ── Gráfico marcas ────────────────────────────────────────
    st.markdown("---")
    col_gr, col_cfg = st.columns([3,2])
    with col_gr:
        st.markdown("### 📈 Stock por marca (módulos)")
        _grafico_marcas(kpis["df"])
    with col_cfg:
        st.markdown("### ⚡ Config rápida")
        _panel_config_rapida(tasa)

    # ── Últimas importaciones ─────────────────────────────────
    st.markdown("---")
    st.markdown("**📥 Últimas importaciones**")
    df_log = query_to_df("SELECT tipo_archivo, nombre_archivo, filas_importadas, estado, importado_en FROM importaciones_log ORDER BY importado_en DESC LIMIT 8")
    if df_log.empty:
        st.info("Sin importaciones registradas.")
    else:
        st.dataframe(df_log, hide_index=True, width="stretch")

    # ── IA contextual ──────────────────────────────────────────
    from utils.ia_widget import nx_ai_widget, ctx_dashboard
    nx_ai_widget(
        page_key  = "dashboard",
        titulo    = "🤖 Resumen ejecutivo con IA",
        subtitulo = "Preguntale al sistema sobre el estado general del negocio",
        sugeridas = [
            ("📊 Resumen del día",    "Dame un resumen ejecutivo del estado actual del sistema: stock, alertas, pedidos en tránsito."),
            ("🔴 Stockouts urgentes", "¿Qué artículos están en cero y tienen alta demanda? Ordená por urgencia."),
            ("💡 ¿Qué haría ahora?",  "Dada la situación actual, ¿cuál es la acción más importante que debería tomar hoy?"),
            ("📈 Oportunidades",      "¿Hay alguna oportunidad de venta o reposición que estoy perdiendo según los datos?"),
        ],
        context_fn = ctx_dashboard,
        collapsed  = True,
    )


def _grafico_marcas(df: pd.DataFrame):
    if df.empty: st.caption("Sin datos"); return
    def marca(desc):
        desc = str(desc).upper()
        for k,l in [("SAM","Samsung"),("IPH","iPhone"),("MOT","Motorola"),
                    ("LG","LG"),("XIA","Xiaomi"),("ALC","Alcatel"),
                    ("HUA","Huawei"),("TCL","TCL"),("INF","Infinix"),
                    ("TE ","Tecno"),("NOK","Nokia"),("OPPO","OPPO")]:
            if k in desc: return l
        return "Otros"
    df = df.copy()
    df["marca"] = df["descripcion"].apply(marca)
    resumen = df.groupby("marca").agg(total=("codigo","count"),sin_stock=("stock_actual",lambda x:(x==0).sum())).reset_index()
    resumen["con_stock"] = resumen["total"] - resumen["sin_stock"]
    resumen = resumen.sort_values("total",ascending=True).tail(12)
    fig = go.Figure()
    fig.add_bar(name="Con stock",y=resumen["marca"],x=resumen["con_stock"],orientation="h",marker_color="#32d74b",marker_opacity=0.8)
    fig.add_bar(name="Sin stock",y=resumen["marca"],x=resumen["sin_stock"],orientation="h",marker_color="#ff375f",marker_opacity=0.9)
    fig.update_layout(barmode="stack",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11,color="#8b95a8"),height=320,margin=dict(l=0,r=10,t=10,b=10),
        legend=dict(orientation="h",y=-0.08,font_size=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)",zeroline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _panel_config_rapida(tasa_actual: float):
    from database import set_config, get_config
    st.markdown(f"<div style='font-size:12px;color:var(--nx-text2);margin-bottom:8px'>💵 Tasa: <strong style='color:var(--nx-text)'>${tasa_actual:,.0f} ARS/USD</strong></div>", unsafe_allow_html=True)
    nueva_tasa = st.number_input("Actualizar USD/ARS",100.0,99999.0,tasa_actual,50.0,key="dash_tasa",label_visibility="collapsed")
    if st.button("💾 Guardar tasa", key="dash_save_tasa"):
        set_config("tasa_usd_ars", str(int(nueva_tasa)))
        st.success(f"✅ Tasa: ${nueva_tasa:,.0f}"); st.rerun()
    st.markdown("---")
    lead = int(get_config("lead_time_dias",int) or 30)
    st.markdown(f"⏱️ Lead time: **{lead} días**")
    nuevo_lead = st.slider("Lead time (días)",7,120,lead,key="dash_lead")
    if nuevo_lead != lead: set_config("lead_time_dias", str(nuevo_lead))
    st.markdown("---")
    ultima = query_to_df("SELECT importado_en FROM importaciones_log ORDER BY importado_en DESC LIMIT 1")
    if not ultima.empty:
        st.markdown(f"🕐 Última carga: **{str(ultima.iloc[0]['importado_en'])[:16]}**")


def _panel_vacio():
    st.markdown("""<div style="background:var(--nx-card);border:1px solid var(--nx-border);
        border-radius:16px;padding:32px;text-align:center;margin-top:16px">
        <div style="font-size:48px;margin-bottom:16px">📦</div>
        <div style="font-size:18px;font-weight:700;margin-bottom:8px">Empezá cargando tus datos de Flexxus</div>
        <div style="font-size:14px;color:var(--nx-text2);margin-bottom:24px">
            El sistema necesita al menos el archivo de <strong>Optimización de Stock</strong>.</div>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
            <div style="background:rgba(10,132,255,.1);border:1px solid rgba(10,132,255,.3);border-radius:10px;padding:12px 20px;font-size:13px">
                1️⃣ <strong>Optimización de Stock</strong><br><span style="font-size:11px">Módulos, demanda, stock actual</span></div>
            <div style="background:rgba(10,132,255,.1);border:1px solid rgba(10,132,255,.3);border-radius:10px;padding:12px 20px;font-size:13px">
                2️⃣ <strong>Lista de Precios</strong><br><span style="font-size:11px">Lista 1 USD · Lista 4 ML ARS</span></div>
            <div style="background:rgba(10,132,255,.1);border:1px solid rgba(10,132,255,.3);border-radius:10px;padding:12px 20px;font-size:13px">
                3️⃣ <strong>Planilla de Stock</strong><br><span style="font-size:11px">San José · Larrea</span></div>
        </div>
    </div>""", unsafe_allow_html=True)
