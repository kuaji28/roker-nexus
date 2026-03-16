"""
ROKER NEXUS — Auditoría de Stock (v2)

Estrategia práctica: comparás un archivo de stock contra el anterior.
El sistema calcula la diferencia y cruza con ventas del período.

Fórmula clave (por módulo):
  Ingreso implícito = (Stock_N - Stock_N-1) + Ventas_período

  · Si Ingreso_implícito > 0 → llegó mercadería (¿te avisaron?)
  · Si Stock bajó mucho más que las ventas → posible anomalía
  · Si Stock bajó exactamente lo que se vendió → OK

FOCO: Módulos (código empieza con letra = proveedor AI-TECH / FR)
La mercadería general solo entra en la vista de rentabilidad para
defender el presupuesto de módulos.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

from database import query_to_df, execute_query


# ─────────────────────────────────────────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────────────────────────────────────────

def _fechas_disponibles_stock(deposito: str = None) -> list:
    """Retorna las fechas de snapshot disponibles, ordenadas desc."""
    try:
        where  = "WHERE deposito=?" if deposito and deposito != "Todos" else ""
        params = (deposito,) if deposito and deposito != "Todos" else ()
        rows   = execute_query(
            f"SELECT DISTINCT fecha FROM stock_snapshots {where} ORDER BY fecha DESC",
            params, fetch=True
        )
        return [r["fecha"] for r in rows] if rows else []
    except Exception:
        return []


def _depositos_disponibles() -> list:
    """Lista de depósitos con snaps."""
    try:
        rows = execute_query(
            "SELECT DISTINCT deposito FROM stock_snapshots ORDER BY deposito", fetch=True
        )
        return ["Todos"] + [r["deposito"] for r in rows] if rows else ["Todos"]
    except Exception:
        return ["Todos"]


def _snapshot(fecha: str, deposito: str = None) -> pd.DataFrame:
    """Retorna snapshot de stock para una fecha y (opcionalmente) depósito."""
    try:
        if deposito and deposito != "Todos":
            return query_to_df(
                "SELECT codigo, descripcion, stock FROM stock_snapshots WHERE fecha=? AND deposito=?",
                params=(fecha, deposito)
            )
        return query_to_df(
            """SELECT codigo, descripcion, SUM(stock) as stock
               FROM stock_snapshots WHERE fecha=? GROUP BY codigo, descripcion""",
            params=(fecha,)
        )
    except Exception:
        return pd.DataFrame()


def _ventas_periodo(fecha_desde: str, fecha_hasta: str) -> pd.DataFrame:
    """Ventas en ARS (y cantidad si está disponible) entre dos fechas."""
    try:
        return query_to_df(
            """SELECT codigo, descripcion,
                      SUM(COALESCE(cantidad, 0)) as uds_vendidas,
                      SUM(total_venta_ars) as venta_ars
               FROM ventas
               WHERE fecha_hasta >= ? AND fecha_desde <= ?
               GROUP BY codigo""",
            params=(fecha_desde, fecha_hasta)
        )
    except Exception:
        return pd.DataFrame()


def _es_modulo(codigo: str) -> bool:
    """True si el código es de módulo (empieza con letra = AI-TECH/FR)."""
    c = str(codigo).strip()
    return bool(c) and c[0].isalpha()


# ─────────────────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700">🔍 Auditoría de Stock</h1>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
    Comparás dos archivos de stock. El sistema detecta diferencias y cruza
    con ventas para calcular <b>ingresos implícitos</b> y anomalías.<br>
    <b>Fórmula:</b> Ingreso implícito = (Stock nuevo − Stock anterior) + Ventas del período</p>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📊 Comparación de archivos",
        "🚨 Anomalías",
        "💰 Rentabilidad módulos",
        "ℹ️ Cómo funciona",
    ])

    with tabs[0]:
        _tab_comparacion()
    with tabs[1]:
        _tab_anomalias()
    with tabs[2]:
        _tab_rentabilidad()
    with tabs[3]:
        _tab_ayuda()

    # ── IA contextual ──────────────────────────────────────────
    from utils.ia_widget import nx_ai_widget, ctx_auditoria
    nx_ai_widget(
        page_key  = "auditoria",
        titulo    = "🤖 Auditoría asistida con IA",
        subtitulo = "Interpretá variaciones, detectá anomalías y construí el argumento para Diego",
        sugeridas = [
            ("🔍 Explicar variaciones",   "¿Qué pueden explicar las variaciones de stock que ves? ¿Son normales o sospechosas?"),
            ("🚨 ¿Algo raro?",            "¿Hay algún movimiento de stock que no se justifica con las ventas registradas?"),
            ("📋 Redactar hallazgos",     "Redactá un resumen de hallazgos de auditoría para reportar a Diego y Walter."),
            ("🛡️ Argumento presupuesto",  "¿Cómo uso estos datos para defender el presupuesto de módulos ante Diego?"),
        ],
        context_fn = ctx_auditoria,
        collapsed  = True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: COMPARACIÓN DE ARCHIVOS
# ─────────────────────────────────────────────────────────────────────────────

def _tab_comparacion():
    st.markdown("### 📊 Compará dos archivos de stock")
    st.caption(
        "Elegí dos fechas de las que subiste archivos de stock. "
        "El sistema calcula diferencias y cruza con ventas del período."
    )

    depositos = _depositos_disponibles()
    col_dep, col_a, col_b = st.columns([2, 2, 2])

    with col_dep:
        dep = st.selectbox("Depósito", depositos, key="aud_dep")
    fechas = _fechas_disponibles_stock(dep if dep != "Todos" else None)

    if len(fechas) < 1:
        st.info("Sin snapshots de stock. Importá al menos un archivo de stock primero.")
        return

    with col_a:
        if len(fechas) >= 2:
            fecha_b_idx = 0  # más reciente
            fecha_a_idx = 1  # anterior
        else:
            fecha_a_idx = fecha_b_idx = 0

        fecha_a = st.selectbox(
            "Archivo ANTERIOR (base)", fechas,
            index=min(fecha_a_idx, len(fechas)-1),
            key="aud_fa",
            format_func=lambda f: f"📄 {f}"
        )
    with col_b:
        fecha_b = st.selectbox(
            "Archivo NUEVO (actual)", fechas,
            index=fecha_b_idx,
            key="aud_fb",
            format_func=lambda f: f"📄 {f}"
        )

    c1, c2, _ = st.columns([2, 2, 6])
    with c1:
        solo_modulos = st.checkbox("Solo módulos (AI-TECH/FR)", value=True, key="aud_mod")
    with c2:
        umbral_diff  = st.number_input("Dif. mínima a mostrar", min_value=0,
                                        value=1, step=1, key="aud_umb")

    if fecha_a == fecha_b:
        st.warning("Elegí dos fechas distintas para comparar.")
        return

    # ── Cargar snapshots ──────────────────────────────────────────────────────
    with st.spinner("Cargando datos..."):
        df_a = _snapshot(fecha_a, dep if dep != "Todos" else None)
        df_b = _snapshot(fecha_b, dep if dep != "Todos" else None)
        df_v = _ventas_periodo(
            min(fecha_a, fecha_b),
            max(fecha_a, fecha_b)
        )

    if df_a.empty or df_b.empty:
        st.error("No se encontraron datos para las fechas seleccionadas.")
        return

    # ── Construir tabla de comparación ───────────────────────────────────────
    df_a = df_a.rename(columns={"stock": "stock_a", "descripcion": "descripcion_a"})
    df_b = df_b.rename(columns={"stock": "stock_b", "descripcion": "descripcion"})

    df = df_b.merge(df_a[["codigo","stock_a"]], on="codigo", how="outer")
    df["stock_a"] = df["stock_a"].fillna(0)
    df["stock_b"] = df["stock_b"].fillna(0)
    df["descripcion"] = df["descripcion"].fillna(df.get("descripcion_a",""))

    # Ventas
    if not df_v.empty:
        df = df.merge(df_v[["codigo","uds_vendidas","venta_ars"]], on="codigo", how="left")
        df["uds_vendidas"] = df["uds_vendidas"].fillna(0)
        df["venta_ars"]    = df["venta_ars"].fillna(0)
    else:
        df["uds_vendidas"] = 0
        df["venta_ars"]    = 0

    # Delta y métricas derivadas
    df["delta"]             = df["stock_b"] - df["stock_a"]
    df["ingreso_implicito"] = df["delta"] + df["uds_vendidas"]  # si >0: llegó mercadería
    df["tipo"]              = df["codigo"].apply(lambda c: "módulo" if _es_modulo(c) else "merch.")

    # Filtros
    if solo_modulos:
        df = df[df["tipo"] == "módulo"]
    if umbral_diff > 0:
        df = df[df["delta"].abs() >= umbral_diff]

    if df.empty:
        st.success("✅ Sin diferencias para los filtros aplicados.")
        return

    # ── KPIs ─────────────────────────────────────────────────────────────────
    subida = df[df["delta"] > 0]
    bajada = df[df["delta"] < 0]
    sin_cambio = df[df["delta"] == 0]

    ck1, ck2, ck3, ck4 = st.columns(4)
    ck1.metric("📈 Con aumento de stock", len(subida),
               help="Posible llegada de mercadería no avisada")
    ck2.metric("📉 Con baja de stock",   len(bajada))
    ck3.metric("➡️ Sin cambio",          len(sin_cambio))
    ck4.metric("🔢 Total SKUs",          len(df))

    st.divider()

    # ── Estado por fila ───────────────────────────────────────────────────────
    def _estado(row):
        d = row["delta"]
        ing = row["ingreso_implicito"]
        if d > 0 and ing > 0:   return "📈 Llegó mercadería"
        if d > 0 and ing <= 0:  return "🔄 Subió (posible devolución)"
        if d < 0 and abs(d) <= row["uds_vendidas"] + 1:
                                 return "🟢 OK (venta normal)"
        if d < 0:                return "⚠️ Bajó más que las ventas"
        return "➡️ Sin cambio"

    df["Estado"] = df.apply(_estado, axis=1)

    # ── Tabla ─────────────────────────────────────────────────────────────────
    df_show = df.copy()
    df_show["delta_fmt"] = df_show["delta"].apply(
        lambda x: f"+{int(x)}" if x > 0 else f"{int(x)}" if x != 0 else "—")
    df_show["ing_fmt"] = df_show["ingreso_implicito"].apply(
        lambda x: f"+{int(x)} uds." if x > 1 else ("—" if x == 0 else f"{int(x)} uds."))
    df_show["venta_fmt"] = df_show["venta_ars"].apply(
        lambda x: f"${x:,.0f}" if x > 0 else "—")

    cols_display = {
        "codigo":     "Código",
        "descripcion":"Artículo",
        "stock_a":    f"Stock {fecha_a}",
        "stock_b":    f"Stock {fecha_b}",
        "delta_fmt":  "Diferencia",
        "uds_vendidas":"Uds. vendidas",
        "ing_fmt":    "Ingreso implícito",
        "venta_fmt":  "Venta ARS",
        "Estado":     "Estado",
    }
    df_table = df_show[[c for c in cols_display if c in df_show.columns]].rename(columns=cols_display)

    # Ordenar: aumentos primero
    df_table = df_table.sort_values(
        f"Stock {fecha_b}", ascending=False, ignore_index=True
    )
    # Resaltado de subidas
    def _highlight(row):
        if "Llegó" in str(row.get("Estado","")):
            return ["background-color: #1a3a2a; color: #7aff9e"] * len(row)
        if "más que" in str(row.get("Estado","")):
            return ["background-color: #3a1a1a; color: #ff8a8a"] * len(row)
        return [""] * len(row)

    try:
        styled = df_table.style.apply(_highlight, axis=1)
        st.dataframe(styled, hide_index=True, use_container_width=True, height=430)
    except Exception:
        st.dataframe(df_table, hide_index=True, use_container_width=True, height=430)

    st.caption(f"{len(df_table):,} SKUs · Período: {fecha_a} → {fecha_b}")

    # ── Botones de acción ─────────────────────────────────────────────────────
    col_dl, col_ia, _ = st.columns([2, 2, 6])
    with col_dl:
        try:
            from io import BytesIO
            buf = BytesIO()
            df_table.to_excel(buf, index=False, engine="openpyxl")
            st.download_button(
                "📥 Exportar (.xlsx)",
                data=buf.getvalue(),
                file_name=f"auditoria_{fecha_a}_vs_{fecha_b}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            pass
    with col_ia:
        if st.button("🤖 Analizar con IA", type="primary", key="aud_ia_btn"):
            _enviar_a_ia(df_show, fecha_a, fecha_b, dep)

    # Resultado IA
    if st.session_state.get("aud_ia_resultado"):
        st.divider()
        st.markdown("### 🤖 Análisis de IA")
        st.markdown(st.session_state["aud_ia_resultado"])
        if st.button("Limpiar análisis", key="aud_ia_clear"):
            st.session_state["aud_ia_resultado"] = ""
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: ANOMALÍAS
# ─────────────────────────────────────────────────────────────────────────────

def _tab_anomalias():
    st.markdown("### 🚨 Detección de anomalías entre archivos")
    st.caption(
        "Analiza los dos últimos archivos de stock automáticamente. "
        "Detecta situaciones que requieren tu atención."
    )

    depositos = _depositos_disponibles()
    dep = st.selectbox("Depósito", depositos, key="anom_dep")
    solo_modulos = st.checkbox("Solo módulos", value=True, key="anom_mod")

    fechas = _fechas_disponibles_stock(dep if dep != "Todos" else None)
    if len(fechas) < 2:
        st.info("Necesitás al menos 2 archivos de stock importados para detectar anomalías.")
        return

    fecha_b = fechas[0]  # más reciente
    fecha_a = fechas[1]  # anterior

    st.info(f"Comparando: **{fecha_a}** (anterior) → **{fecha_b}** (actual)")

    with st.spinner("Analizando..."):
        df_a = _snapshot(fecha_a, dep if dep != "Todos" else None)
        df_b = _snapshot(fecha_b, dep if dep != "Todos" else None)
        df_v = _ventas_periodo(fecha_a, fecha_b)

    if df_a.empty or df_b.empty:
        st.error("Sin datos para el período.")
        return

    df_a = df_a.rename(columns={"stock": "stock_a"})
    df_b = df_b.rename(columns={"stock": "stock_b"})
    df = df_b.merge(df_a[["codigo","stock_a"]], on="codigo", how="outer")
    df["stock_a"] = df["stock_a"].fillna(0)
    df["stock_b"] = df["stock_b"].fillna(0)

    if not df_v.empty:
        df = df.merge(df_v[["codigo","uds_vendidas","venta_ars"]], on="codigo", how="left")
        df["uds_vendidas"] = df["uds_vendidas"].fillna(0)
    else:
        df["uds_vendidas"] = 0

    df["delta"]             = df["stock_b"] - df["stock_a"]
    df["ingreso_implicito"] = df["delta"] + df["uds_vendidas"]
    df["tipo"]              = df["codigo"].apply(lambda c: "módulo" if _es_modulo(c) else "merch.")

    if solo_modulos:
        df = df[df["tipo"] == "módulo"]

    # ── Categorizar anomalías ─────────────────────────────────────────────────
    llegadas    = df[df["ingreso_implicito"] >= 3].copy()   # llegó mercadería
    caidas_anom = df[
        (df["delta"] < 0) &
        (df["uds_vendidas"] > 0) &
        (-df["delta"] > df["uds_vendidas"] * 1.5)           # bajó 50% más que lo vendido
    ].copy()
    nuevos_cero = df[
        (df["stock_a"] > 0) &
        (df["stock_b"] == 0)
    ].copy()

    # ── Sección: Llegadas de mercadería ──────────────────────────────────────
    if not llegadas.empty:
        st.error(
            f"📦 **{len(llegadas)} módulo(s) subieron de stock** → "
            f"posible llegada de mercadería. ¿Te avisaron?"
        )
        for _, r in llegadas.head(10).iterrows():
            st.markdown(
                f"- `{r['codigo']}` {str(r.get('descripcion',''))[:35]} — "
                f"Stock: **{int(r['stock_a'])} → {int(r['stock_b'])}** "
                f"(+{int(r['delta'])} uds. · Ingreso implícito: +{int(r['ingreso_implicito'])} uds.)"
            )
        if len(llegadas) > 10:
            st.caption(f"_(y {len(llegadas)-10} más)_")
    else:
        st.success("✅ Sin llegadas de mercadería detectadas en este período.")

    st.divider()

    # ── Sección: Caídas anómalas ──────────────────────────────────────────────
    if not caidas_anom.empty:
        st.warning(
            f"⚠️ **{len(caidas_anom)} módulo(s) bajaron más de lo esperado por ventas.** "
            f"Revisá si hubo movimiento no registrado."
        )
        for _, r in caidas_anom.head(8).iterrows():
            ventas_str = f"| vendido: {int(r['uds_vendidas'])} uds." if r['uds_vendidas'] > 0 else ""
            st.markdown(
                f"- `{r['codigo']}` {str(r.get('descripcion',''))[:35]} — "
                f"Stock: {int(r['stock_a'])} → {int(r['stock_b'])} "
                f"(bajó {abs(int(r['delta']))} uds. {ventas_str})"
            )
    else:
        st.success("✅ Sin caídas anómalas de stock.")

    st.divider()

    # ── Sección: Nuevos quiebres ──────────────────────────────────────────────
    if not nuevos_cero.empty:
        st.warning(f"🔴 **{len(nuevos_cero)} módulo(s) llegaron a 0 unidades.**")
        for _, r in nuevos_cero.head(8).iterrows():
            st.markdown(
                f"- `{r['codigo']}` {str(r.get('descripcion',''))[:35]} "
                f"(tenía {int(r['stock_a'])} uds.)"
            )
    else:
        st.success("✅ Sin nuevos quiebres de módulos.")

    # ── Botón IA ──────────────────────────────────────────────────────────────
    if (not llegadas.empty or not caidas_anom.empty) and st.button(
        "🤖 Que la IA analice estas anomalías", type="primary", key="anom_ia_btn"
    ):
        _enviar_anomalias_a_ia(llegadas, caidas_anom, nuevos_cero, fecha_a, fecha_b)

    if st.session_state.get("anom_ia_resultado"):
        st.divider()
        st.markdown("### 🤖 Análisis de IA")
        st.markdown(st.session_state["anom_ia_resultado"])
        if st.button("Limpiar", key="anom_ia_clear"):
            st.session_state["anom_ia_resultado"] = ""
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: RENTABILIDAD MÓDULOS
# ─────────────────────────────────────────────────────────────────────────────

def _tab_rentabilidad():
    st.markdown("### 💰 Rentabilidad de módulos")
    st.caption(
        "Para defender el presupuesto de módulos. "
        "Muestra ventas en ARS, rotación y contribución por módulo."
    )

    # Cargar ventas de módulos
    try:
        df_v = query_to_df("""
            SELECT v.codigo, v.descripcion, v.marca,
                   SUM(v.total_venta_ars) as venta_total_ars,
                   SUM(COALESCE(v.cantidad, 0)) as uds_vendidas,
                   COUNT(DISTINCT v.fecha_desde) as periodos
            FROM ventas v
            GROUP BY v.codigo
            ORDER BY venta_total_ars DESC
        """)
    except Exception:
        df_v = pd.DataFrame()

    if df_v.empty:
        st.info("Sin datos de ventas. Importá archivos de ventas de Flexxus primero.")
        return

    # Filtrar solo módulos
    df_v["es_modulo"] = df_v["codigo"].apply(_es_modulo)
    df_mod = df_v[df_v["es_modulo"]].copy()
    df_gen = df_v[~df_v["es_modulo"]].copy()

    # Stock actual de módulos
    try:
        df_stock = query_to_df("""
            SELECT s.codigo, SUM(s.stock) as stock_actual
            FROM stock_snapshots s
            JOIN (
                SELECT codigo, MAX(fecha) mf FROM stock_snapshots GROUP BY codigo
            ) lx ON s.codigo=lx.codigo AND s.fecha=lx.mf
            WHERE SUBSTR(s.codigo,1,1) BETWEEN 'A' AND 'Z' OR SUBSTR(s.codigo,1,1) BETWEEN 'a' AND 'z'
            GROUP BY s.codigo
        """)
        if not df_stock.empty:
            df_mod = df_mod.merge(df_stock, on="codigo", how="left")
            df_mod["stock_actual"] = df_mod["stock_actual"].fillna(0)
    except Exception:
        df_mod["stock_actual"] = 0

    # KPIs comparativos
    venta_mod = df_mod["venta_total_ars"].sum()
    venta_gen = df_gen["venta_total_ars"].sum()
    venta_tot = venta_mod + venta_gen
    pct_mod   = (venta_mod / venta_tot * 100) if venta_tot > 0 else 0

    ck1, ck2, ck3, ck4 = st.columns(4)
    ck1.metric("💰 Venta módulos",     f"${venta_mod:,.0f}",
               help="Total ventas en ARS de SKUs tipo módulo (código letra)")
    ck2.metric("🛍️ Venta mercadería",  f"${venta_gen:,.0f}")
    ck3.metric("📊 % módulos / total", f"{pct_mod:.1f}%",
               help="Participación de módulos en el total de ventas")
    ck4.metric("📦 SKUs activos",      len(df_mod[df_mod["venta_total_ars"] > 0]))

    st.divider()

    # Top módulos por venta
    st.markdown("#### Top módulos por venta ARS")
    df_top = df_mod[["codigo","descripcion","marca",
                     "uds_vendidas","venta_total_ars","stock_actual"]].copy()
    df_top = df_top.sort_values("venta_total_ars", ascending=False).head(50).reset_index(drop=True)
    df_top["venta_fmt"] = df_top["venta_total_ars"].apply(lambda x: f"${x:,.0f}")
    df_top["rotacion"]  = df_top.apply(
        lambda r: f"{r['uds_vendidas']:.0f} / {r['stock_actual']:.0f}"
        if r["stock_actual"] > 0 else f"{r['uds_vendidas']:.0f} (s/stock)", axis=1
    )

    st.dataframe(
        df_top[["codigo","descripcion","marca","venta_fmt","rotacion"]].rename(columns={
            "codigo":"Código","descripcion":"Artículo","marca":"Marca",
            "venta_fmt":"Venta ARS","rotacion":"Vend./Stock actual"
        }),
        hide_index=True, use_container_width=True, height=400
    )

    # Descarga para defensa de presupuesto
    try:
        from io import BytesIO
        buf = BytesIO()
        df_top.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            "📥 Exportar rentabilidad módulos (.xlsx)",
            data=buf.getvalue(),
            file_name=f"rentabilidad_modulos_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception:
        pass

    # Botón IA para defender presupuesto
    if st.button("🤖 Generar argumentos para defender el presupuesto de módulos",
                 type="primary", key="rent_ia_btn"):
        _ia_defender_presupuesto(df_mod, venta_mod, venta_tot, pct_mod)

    if st.session_state.get("rent_ia_resultado"):
        st.divider()
        st.markdown("### 🤖 Argumentos para la reunión")
        st.markdown(st.session_state["rent_ia_resultado"])
        if st.button("Limpiar", key="rent_ia_clear"):
            st.session_state["rent_ia_resultado"] = ""
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: AYUDA
# ─────────────────────────────────────────────────────────────────────────────

def _tab_ayuda():
    st.markdown("""
### ℹ️ Cómo funciona la Auditoría

**¿Qué necesitás?**
1. Tener importados al menos 2 archivos de stock de Flexxus (en diferentes fechas)
2. Tener importados archivos de ventas del período (opcional, pero mejora el análisis)

---

**📊 Comparación de archivos**

Elegís dos fechas de las que importaste stock. Para cada módulo:

| Columna | Qué significa |
|---|---|
| Stock anterior | Lo que había en la fecha A |
| Stock actual | Lo que hay en la fecha B |
| Diferencia | stock_B − stock_A |
| Uds. vendidas | Lo que Flexxus registró como vendido en el período |
| **Ingreso implícito** | (stock_B − stock_A) + vendido = cuánto llegó |
| Estado | Interpretación automática |

**Ejemplos:**
- Stock pasó de 10 a 25. Vendiste 5 → Ingreso implícito = 20 unidades llegaron. **¿Te avisaron?**
- Stock pasó de 20 a 5. Vendiste 10 → Bajó 15 pero solo vendiste 10 → **Anomalía: faltan 5**
- Stock pasó de 20 a 10. Vendiste 10 → OK, es exactamente lo que se vendió.

---

**💰 Rentabilidad módulos**

Muestra qué porcentaje del total de ventas viene de módulos.
Útil para responder: *"¿Por qué necesitamos más crédito para módulos?"*

El botón 🤖 genera argumentos listos para usar en una reunión.

---

**🔔 Alertas automáticas**

Cada vez que importás un archivo de stock, el sistema compara automáticamente
con el anterior y genera alertas en la pestaña **🔔 Alertas** de la navegación.
No hace falta entrar acá para recibir las alertas.
""")


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRACIÓN IA
# ─────────────────────────────────────────────────────────────────────────────

def _enviar_a_ia(df: pd.DataFrame, fecha_a: str, fecha_b: str, dep: str):
    """Genera análisis IA del resultado de comparación."""
    try:
        import anthropic
        from database import get_config

        api_key = get_config("anthropic_api_key") or get_config("claude_api_key")
        if not api_key:
            st.warning("Configurá la API de Claude en Sistema → APIs para usar el análisis IA.")
            return

        llegadas = df[df["ingreso_implicito"] >= 3]
        anomalas = df[(df["delta"] < 0) & (-df["delta"] > df["uds_vendidas"].fillna(0) * 1.5)]

        resumen = _resumen_texto(df, fecha_a, fecha_b, dep)
        prompt  = (
            f"Sos el asistente de inventario de AI-TECH (El Celu), negocio de módulos de celulares.\n"
            f"Analizá este reporte de auditoría de stock y generá un análisis claro y accionable.\n\n"
            f"{resumen}\n\n"
            f"Identificá:\n"
            f"1. Qué módulos parecen haber recibido mercadería sin aviso\n"
            f"2. Qué módulos tienen anomalías (bajaron más que las ventas)\n"
            f"3. Qué acciones concretas recomendar (en ese orden)\n"
            f"Sé directo, sin rodeos. Máximo 300 palabras. Usá bullet points."
        )

        client = anthropic.Anthropic(api_key=api_key)
        msg    = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role":"user","content":prompt}]
        )
        st.session_state["aud_ia_resultado"] = msg.content[0].text
        st.rerun()
    except ImportError:
        _ia_fallback(df, fecha_a, fecha_b)
    except Exception as e:
        st.error(f"Error IA: {e}")


def _enviar_anomalias_a_ia(llegadas, caidas, quiebres, fecha_a, fecha_b):
    try:
        import anthropic
        from database import get_config

        api_key = get_config("anthropic_api_key") or get_config("claude_api_key")
        if not api_key:
            _ia_fallback_anomalias(llegadas, caidas, quiebres, fecha_a, fecha_b)
            return

        items_llegadas = "\n".join(
            f"  - {r['codigo']}: stock {int(r['stock_a'])}→{int(r['stock_b'])} (+{int(r['ingreso_implicito'])} implícito)"
            for _, r in llegadas.head(5).iterrows()
        ) or "Ninguna"

        items_caidas = "\n".join(
            f"  - {r['codigo']}: bajó {abs(int(r['delta']))} uds., vendido {int(r['uds_vendidas'])}"
            for _, r in caidas.head(5).iterrows()
        ) or "Ninguna"

        prompt = (
            f"Analizá estas anomalías de stock de AI-TECH entre {fecha_a} y {fecha_b}.\n\n"
            f"LLEGADAS sin aviso:\n{items_llegadas}\n\n"
            f"CAÍDAS anómalas:\n{items_caidas}\n\n"
            f"¿Qué deberías hacer? ¿A quién le reclamarías? Sé concreto. Máx 200 palabras."
        )

        client = anthropic.Anthropic(api_key=api_key)
        msg    = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role":"user","content":prompt}]
        )
        st.session_state["anom_ia_resultado"] = msg.content[0].text
        st.rerun()
    except Exception as e:
        _ia_fallback_anomalias(llegadas, caidas, quiebres, fecha_a, fecha_b)


def _ia_defender_presupuesto(df_mod: pd.DataFrame, venta_mod: float,
                              venta_tot: float, pct_mod: float):
    try:
        import anthropic
        from database import get_config

        api_key = get_config("anthropic_api_key") or get_config("claude_api_key")
        if not api_key:
            _ia_fallback_presupuesto(df_mod, venta_mod, venta_tot, pct_mod)
            return

        top5 = df_mod.nlargest(5, "venta_total_ars")[
            ["codigo","descripcion","venta_total_ars"]
        ].to_dict("records")
        top5_txt = "\n".join(
            f"  - {r['codigo']} {r['descripcion']}: ${r['venta_total_ars']:,.0f}"
            for r in top5
        )

        prompt = (
            f"Sos asesor de negocios de AI-TECH (El Celu), importador de módulos de celulares.\n"
            f"Los directivos están bajando el crédito/presupuesto para comprar módulos.\n\n"
            f"Datos de ventas:\n"
            f"- Ventas de módulos: ${venta_mod:,.0f} ARS\n"
            f"- Total ventas: ${venta_tot:,.0f} ARS\n"
            f"- Módulos = {pct_mod:.1f}% de todas las ventas\n"
            f"- Top 5 módulos más vendidos:\n{top5_txt}\n\n"
            f"Generá 3-5 argumentos concretos y convincentes para defender que "
            f"se mantenga o aumente el crédito de módulos. "
            f"Incluí los datos en los argumentos. Máx 250 palabras."
        )

        client = anthropic.Anthropic(api_key=api_key)
        msg    = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role":"user","content":prompt}]
        )
        st.session_state["rent_ia_resultado"] = msg.content[0].text
        st.rerun()
    except Exception:
        _ia_fallback_presupuesto(df_mod, venta_mod, venta_tot, pct_mod)


# ── Fallbacks sin API ─────────────────────────────────────────────────────────

def _ia_fallback(df, fecha_a, fecha_b):
    llegadas = df[df["ingreso_implicito"] >= 3]
    anom     = df[(df["delta"] < 0) & (-df["delta"] > df.get("uds_vendidas", 0) * 1.5)]
    lineas   = [f"**Análisis: {fecha_a} → {fecha_b}**\n"]
    if not llegadas.empty:
        lineas.append(f"📦 **{len(llegadas)} módulos recibieron mercadería sin aviso aparente.**")
        for _, r in llegadas.head(3).iterrows():
            lineas.append(f"  - `{r['codigo']}`: +{int(r['ingreso_implicito'])} uds. → Verificá si te avisaron.")
    if not anom.empty:
        lineas.append(f"⚠️ **{len(anom)} módulos bajaron más de lo que explican las ventas.**")
        for _, r in anom.head(3).iterrows():
            lineas.append(f"  - `{r['codigo']}`: bajó {abs(int(r['delta']))} uds. → Revisar movimiento.")
    if not llegadas.empty and not anom.empty:
        pass
    elif llegadas.empty and anom.empty:
        lineas.append("✅ Sin anomalías detectadas.")
    st.session_state["aud_ia_resultado"] = "\n".join(lineas)
    st.rerun()


def _ia_fallback_anomalias(llegadas, caidas, quiebres, fecha_a, fecha_b):
    lineas = [f"**Análisis automático {fecha_a} → {fecha_b}**\n"]
    if not llegadas.empty:
        lineas.append(f"📦 **Llegó mercadería en {len(llegadas)} módulos sin aviso:**")
        for _, r in llegadas.head(5).iterrows():
            lineas.append(f"  - `{r['codigo']}`: +{int(r['ingreso_implicito'])} uds. → Reclamar aviso al depósito.")
    if not caidas.empty:
        lineas.append(f"⚠️ **Caídas anómalas en {len(caidas)} módulos:**")
        for _, r in caidas.head(5).iterrows():
            lineas.append(f"  - `{r['codigo']}`: bajó {abs(int(r['delta']))} uds. vs {int(r['uds_vendidas'])} vendidas.")
    st.session_state["anom_ia_resultado"] = "\n".join(lineas)
    st.rerun()


def _ia_fallback_presupuesto(df_mod, venta_mod, venta_tot, pct_mod):
    top3 = df_mod.nlargest(3, "venta_total_ars")[["codigo","descripcion","venta_total_ars"]]
    lineas = [
        "**Argumentos para defender el presupuesto de módulos:**\n",
        f"1. Los módulos representan **{pct_mod:.1f}%** del total de ventas (${venta_mod:,.0f} ARS). "
        f"Bajar el crédito impacta directamente ese porcentaje.",
        f"2. Los 3 módulos más vendidos generan en conjunto ${top3['venta_total_ars'].sum():,.0f} ARS. "
        f"Sin stock suficiente, se pierden esas ventas.",
    ]
    for _, r in top3.iterrows():
        lineas.append(f"   - `{r['codigo']}` {r['descripcion']}: ${r['venta_total_ars']:,.0f}")
    lineas.append("3. La rotación de módulos es alta — el capital invertido vuelve rápido.")
    st.session_state["rent_ia_resultado"] = "\n".join(lineas)
    st.rerun()


def _resumen_texto(df, fecha_a, fecha_b, dep):
    llegadas = df[df["ingreso_implicito"] >= 3]
    anom     = df[(df["delta"] < 0) & (-df["delta"] > df.get("uds_vendidas", pd.Series()).fillna(0) * 1.5)]
    return (
        f"Depósito: {dep} | Período: {fecha_a} → {fecha_b}\n"
        f"Total SKUs analizados: {len(df)}\n"
        f"Con aumento de stock (posible llegada): {len(llegadas)}\n"
        f"Con caída anómala: {len(anom)}\n"
        f"Top llegadas: " +
        ", ".join(f"{r['codigo']}(+{int(r['ingreso_implicito'])})"
                  for _, r in llegadas.head(5).iterrows())
    )
