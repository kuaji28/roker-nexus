"""
ROKER NEXUS — Auditoría de Stock

El punto central del sistema: NO depender 100% de Flexxus.

Lógica de reconciliación por SKU:
  Stock anterior
  + Ingresos registrados (packing de China)
  - Ventas (Flexxus ventas)
  = Stock esperado

  Si Stock esperado ≠ Stock actual en Flexxus → ANOMALÍA

Ejemplo:
  Entraron 500 unidades. Se vendieron 300.
  Flexxus dice que hay 0.
  → Faltan 200 unidades. ¿Dónde están?

Flujo:
  1. Registrás el ingreso de mercadería (packing de China)
  2. El sistema compara con ventas y stock actual
  3. Detecta discrepancias y las muestra con severidad
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

from database import query_to_df, execute_query, df_to_db


# ── Helpers ─────────────────────────────────────────────────────────────────

def _ensure_tables():
    execute_query("""CREATE TABLE IF NOT EXISTS ingresos_mercaderia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER,
        invoice_id TEXT,
        codigo TEXT NOT NULL,
        descripcion TEXT,
        cantidad_pedida INTEGER DEFAULT 0,
        cantidad_ingresada INTEGER DEFAULT 0,
        diferencia INTEGER DEFAULT 0,
        fecha_ingreso TEXT,
        fecha_flexxus TEXT,
        confirmado INTEGER DEFAULT 0,
        notas TEXT,
        creado_en TEXT DEFAULT (datetime('now'))
    )""", fetch=False)


def _stock_actual_por_codigo() -> dict:
    """Retorna stock total (todos los depósitos) por código."""
    try:
        df = query_to_df("""
            SELECT s.codigo, SUM(s.stock) as stock_total
            FROM stock_snapshots s
            JOIN (
                SELECT codigo, deposito, MAX(fecha) as mf
                FROM stock_snapshots GROUP BY codigo, deposito
            ) lx ON s.codigo=lx.codigo AND s.deposito=lx.deposito AND s.fecha=lx.mf
            GROUP BY s.codigo
        """)
        if df.empty:
            return {}
        return dict(zip(df["codigo"], df["stock_total"].fillna(0)))
    except Exception:
        return {}


def _ventas_por_codigo(fecha_desde: str = None) -> dict:
    """Retorna total vendido por código desde una fecha."""
    try:
        params = ()
        where  = ""
        if fecha_desde:
            where  = "WHERE v.fecha >= ?"
            params = (fecha_desde,)
        df = query_to_df(
            f"SELECT codigo, SUM(cantidad) as vendido FROM ventas {where} GROUP BY codigo",
            params=params
        )
        if df.empty:
            return {}
        return dict(zip(df["codigo"], df["vendido"].fillna(0)))
    except Exception:
        return {}


def _ingresos_desde(fecha_desde: str = None) -> pd.DataFrame:
    """Retorna ingresos registrados desde una fecha."""
    try:
        params = ()
        where  = ""
        if fecha_desde:
            where  = "WHERE fecha_ingreso >= ?"
            params = (fecha_desde,)
        return query_to_df(
            f"SELECT * FROM ingresos_mercaderia {where} ORDER BY fecha_ingreso DESC",
            params=params
        )
    except Exception:
        return pd.DataFrame()


# ── Render principal ─────────────────────────────────────────────────────────

def render():
    _ensure_tables()

    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700">🔍 Auditoría de Stock</h1>
    <p style="color:var(--nx-text2);font-size:13px;margin-bottom:12px">
    No te fiés solo de Flexxus. Registrá cada ingreso de mercadería y el sistema
    verifica automáticamente que los números cierren:
    <b>Stock anterior + Ingresos − Ventas = Stock esperado en Flexxus.</b></p>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📥 Registrar Ingreso",
        "📊 Reconciliación",
        "🚨 Anomalías",
        "📋 Historial",
    ])

    with tabs[0]:
        _tab_registrar_ingreso()
    with tabs[1]:
        _tab_reconciliacion()
    with tabs[2]:
        _tab_anomalias()
    with tabs[3]:
        _tab_historial()


# ── Tab 1: Registrar Ingreso ─────────────────────────────────────────────────

def _tab_registrar_ingreso():
    st.markdown("### 📥 Registrar ingreso de mercadería")
    st.info(
        "Cada vez que llega un paquete de China, registrá cuántas unidades "
        "entraron realmente. El sistema compara contra lo pedido y contra Flexxus."
    )

    # ── Formulario de ingreso manual por SKU ────────────────────────────────
    with st.form("form_ingreso", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            codigo_ing = st.text_input("Código del artículo *", "").strip().upper()
        with c2:
            cant_ped  = st.number_input("Cant. pedida", min_value=0, value=0, step=1)
        with c3:
            cant_ing  = st.number_input("Cant. ingresada real *", min_value=0, value=0, step=1)

        c4, c5 = st.columns([1, 2])
        with c4:
            fecha_ing = st.date_input("Fecha de ingreso", value=date.today())
        with c5:
            invoice_ing = st.text_input("Invoice / Lote (opcional)", "")

        notas_ing = st.text_area("Notas", "", height=60)

        if st.form_submit_button("💾 Guardar ingreso", type="primary"):
            if not codigo_ing:
                st.error("El código es obligatorio.")
            elif cant_ing <= 0:
                st.error("La cantidad ingresada debe ser mayor a 0.")
            else:
                diferencia = cant_ped - cant_ing
                execute_query("""
                    INSERT INTO ingresos_mercaderia
                      (invoice_id, codigo, cantidad_pedida, cantidad_ingresada,
                       diferencia, fecha_ingreso, confirmado, notas, creado_en)
                    VALUES (?,?,?,?,?,?,0,?,datetime('now'))
                """, (invoice_ing or None, codigo_ing, int(cant_ped),
                      int(cant_ing), int(diferencia),
                      fecha_ing.isoformat(), notas_ing or None),
                    fetch=False)
                st.success(f"✅ Ingreso de `{codigo_ing}` guardado: {cant_ing} uds.")
                if diferencia != 0:
                    emoji = "⚠️ Faltan" if diferencia > 0 else "⚠️ Vinieron de más"
                    st.warning(f"{emoji} {abs(diferencia)} unidades vs lo pedido.")

    st.divider()

    # ── Carga masiva desde Excel ─────────────────────────────────────────────
    st.markdown("#### 📄 O cargá un archivo de packing list")
    st.caption("Excel con columnas: Código, Cantidad Pedida, Cantidad Ingresada (y opcionalmente: Descripción, Notas)")
    file = st.file_uploader("Subí el packing list (.xlsx / .xls)", type=["xlsx","xls"], key="pack_upload")
    if file:
        _procesar_packing_list(file)


def _procesar_packing_list(file):
    """Procesa un archivo Excel de packing list."""
    try:
        nombre = getattr(file, "name", "")
        ext = nombre.split(".")[-1].lower()
        engine = "xlrd" if ext == "xls" else "openpyxl"
        df = pd.read_excel(file, engine=engine)
        df.columns = [str(c).strip().upper() for c in df.columns]

        # Buscar columnas
        def find_col(*keys):
            for k in keys:
                for c in df.columns:
                    if k.upper() in c:
                        return c
            return None

        cod_col  = find_col("CÓDIGO","CODIGO","COD","SKU")
        ped_col  = find_col("PEDIDA","PEDIDO","ORDENADA","ORDEN","SOLICITADA")
        ing_col  = find_col("INGRESADA","RECIBIDA","REAL","LLEGADA","ENTREGADA","INGRESADO")
        desc_col = find_col("DESCRIPCION","DESCRIPCIÓN","ARTÍCULO","ARTICULO")

        if not cod_col or not ing_col:
            st.error("No se encontraron las columnas Código e Ingresada. "
                     "Renombrálas así en el Excel.")
            return

        fecha_hoy = date.today().isoformat()
        registros = []
        for _, row in df.iterrows():
            cod = str(row[cod_col]).strip().upper()
            if not cod or cod in ("NAN","NONE",""):
                continue
            cant_i = int(pd.to_numeric(row[ing_col], errors="coerce") or 0)
            cant_p = int(pd.to_numeric(row[ped_col], errors="coerce") or 0) if ped_col else 0
            desc   = str(row[desc_col]).strip() if desc_col and pd.notna(row.get(desc_col)) else ""
            registros.append({
                "codigo":            cod,
                "descripcion":       desc,
                "cantidad_pedida":   cant_p,
                "cantidad_ingresada":cant_i,
                "diferencia":        cant_p - cant_i,
                "fecha_ingreso":     fecha_hoy,
                "confirmado":        0,
            })

        if not registros:
            st.warning("El archivo no contiene filas válidas.")
            return

        df_save = pd.DataFrame(registros)
        st.dataframe(df_save[["codigo","descripcion","cantidad_pedida",
                               "cantidad_ingresada","diferencia"]],
                     hide_index=True, use_container_width=True)

        if st.button(f"💾 Confirmar {len(registros)} ingresos", type="primary"):
            df_to_db(df_save, "ingresos_mercaderia")
            st.success(f"✅ {len(registros)} ingresos guardados.")
            st.rerun()
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")


# ── Tab 2: Reconciliación ────────────────────────────────────────────────────

def _tab_reconciliacion():
    st.markdown("### 📊 Reconciliación por artículo")
    st.caption(
        "Fórmula: **Ingresos registrados − Ventas Flexxus = Debería haber en stock**. "
        "Si Flexxus dice algo distinto, hay una anomalía."
    )

    c1, c2 = st.columns([2, 2])
    with c1:
        fecha_desde = st.date_input("Desde", value=date(date.today().year, 1, 1),
                                    key="rec_desde")
    with c2:
        umbral_diff = st.number_input("Mostrar solo si diferencia ≥", min_value=0,
                                       value=1, step=1, key="rec_umbral")

    df_ing = _ingresos_desde(fecha_desde.isoformat())
    if df_ing.empty:
        st.info("Sin ingresos registrados para el período. "
                "Registrá los ingresos en la pestaña '📥 Registrar Ingreso'.")
        return

    # Agrupar ingresos por código
    df_ing_g = df_ing.groupby("codigo").agg(
        ingresado=("cantidad_ingresada", "sum"),
        pedido=("cantidad_pedida", "sum"),
        descripcion=("descripcion", "first"),
    ).reset_index()

    # Ventas en el período
    ventas = _ventas_por_codigo(fecha_desde.isoformat())

    # Stock actual en Flexxus
    stock_actual = _stock_actual_por_codigo()

    # Construir tabla de reconciliación
    filas = []
    for _, r in df_ing_g.iterrows():
        cod       = r["codigo"]
        ingresado = int(r["ingresado"])
        vendido   = int(ventas.get(cod, 0))
        stock_esp = ingresado - vendido          # debería haber en Flexxus
        stock_fle = int(stock_actual.get(cod, 0)) # lo que dice Flexxus
        discrepancia = stock_esp - stock_fle     # positivo = faltan en Flexxus

        if abs(discrepancia) < umbral_diff:
            continue

        if discrepancia > 10:
            estado = "🔴 Faltan unidades"
        elif discrepancia < -10:
            estado = "🟡 Hay de más"
        elif abs(discrepancia) <= 2:
            estado = "🟢 OK"
        else:
            estado = "🟡 Revisar"

        filas.append({
            "Código":       cod,
            "Artículo":     str(r["descripcion"])[:40],
            "Ingresó":      ingresado,
            "Vendido":      vendido,
            "Esperado":     stock_esp,
            "Flexxus":      stock_fle,
            "Diferencia":   discrepancia,
            "Estado":       estado,
        })

    if not filas:
        st.success("✅ Sin discrepancias encontradas para el período y umbral seleccionados.")
        return

    df_rec = pd.DataFrame(filas)
    df_rec = df_rec.sort_values("Diferencia", ascending=False)

    # Métricas
    n_falta  = int((df_rec["Diferencia"] > 0).sum())
    n_demás  = int((df_rec["Diferencia"] < 0).sum())
    n_ok     = len(df_rec) - n_falta - n_demás

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 Faltan unidades", n_falta)
    c2.metric("🟡 Hay de más",      n_demás)
    c3.metric("🟢 OK / sin diff.",   n_ok)

    st.dataframe(df_rec, hide_index=True, use_container_width=True, height=420,
        column_config={
            "Código":     st.column_config.TextColumn(width="small"),
            "Artículo":   st.column_config.TextColumn(width="large"),
            "Ingresó":    st.column_config.NumberColumn(format="%d"),
            "Vendido":    st.column_config.NumberColumn(format="%d"),
            "Esperado":   st.column_config.NumberColumn(format="%d"),
            "Flexxus":    st.column_config.NumberColumn(format="%d"),
            "Diferencia": st.column_config.NumberColumn(format="%+d"),
            "Estado":     st.column_config.TextColumn(width="medium"),
        })

    # Descarga como Excel
    try:
        from io import BytesIO
        buf = BytesIO()
        df_rec.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            "📥 Descargar reconciliación (.xlsx)",
            data=buf.getvalue(),
            file_name=f"reconciliacion_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception:
        pass


# ── Tab 3: Anomalías ─────────────────────────────────────────────────────────

def _tab_anomalias():
    st.markdown("### 🚨 Anomalías detectadas")
    st.caption(
        "Se analizan todos los artículos con ingreso registrado. "
        "Si los números no cierran, aparecen acá."
    )

    fecha_desde = st.date_input("Analizar desde", value=date(date.today().year, 1, 1),
                                key="anom_desde")

    df_ing = _ingresos_desde(fecha_desde.isoformat())
    if df_ing.empty:
        st.info("Sin ingresos registrados para analizar.")
        return

    df_ing_g = df_ing.groupby("codigo").agg(
        ingresado=("cantidad_ingresada","sum"),
        pedido=("cantidad_pedida","sum"),
        descripcion=("descripcion","first"),
    ).reset_index()

    ventas       = _ventas_por_codigo(fecha_desde.isoformat())
    stock_actual = _stock_actual_por_codigo()

    anomalias = []
    for _, r in df_ing_g.iterrows():
        cod       = r["codigo"]
        ingresado = int(r["ingresado"])
        vendido   = int(ventas.get(cod, 0))
        stock_esp = ingresado - vendido
        stock_fle = int(stock_actual.get(cod, 0))
        discrepancia = stock_esp - stock_fle

        if discrepancia > 5:
            tipo_anom = "FALTANTE"
            sev       = "alta" if discrepancia > 20 else "media"
            desc_anom = (
                f"Ingresaron {ingresado} uds. Se vendieron {vendido}. "
                f"Deberían quedar {stock_esp} en Flexxus, pero hay {stock_fle}. "
                f"Faltan {discrepancia} unidades — ¿dónde están?"
            )
        elif discrepancia < -5:
            tipo_anom = "EXCEDENTE"
            sev       = "baja"
            desc_anom = (
                f"Flexxus muestra {stock_fle} uds., pero según ingresos y ventas "
                f"deberían ser {stock_esp}. Hay {abs(discrepancia)} unidades de más."
            )
        else:
            continue  # OK

        anomalias.append({
            "Severidad":  {"alta":"🔴 Alta","media":"🟡 Media","baja":"🟢 Baja"}.get(sev,""),
            "Tipo":       tipo_anom,
            "Código":     cod,
            "Artículo":   str(r["descripcion"])[:40],
            "Ingresó":    ingresado,
            "Vendido":    vendido,
            "Esperado":   stock_esp,
            "Flexxus":    stock_fle,
            "Diferencia": discrepancia,
            "Detalle":    desc_anom,
        })

    if not anomalias:
        st.success("✅ Sin anomalías detectadas para el período.")
        return

    df_anom = pd.DataFrame(anomalias).sort_values(
        ["Tipo","Diferencia"], ascending=[True, False])

    # Faltantes (crítico)
    faltantes = df_anom[df_anom["Tipo"] == "FALTANTE"]
    if not faltantes.empty:
        st.error(f"🔴 {len(faltantes)} artículo(s) con unidades FALTANTES")
        for _, row in faltantes.iterrows():
            with st.expander(
                f"{row['Severidad']} `{row['Código']}` — {row['Artículo']} "
                f"(diferencia: {row['Diferencia']:+d} uds.)"
            ):
                st.markdown(f"**{row['Detalle']}**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ingresó",  row["Ingresó"])
                c2.metric("Vendido",  row["Vendido"])
                c3.metric("Esperado", row["Esperado"])
                c4.metric("Flexxus",  row["Flexxus"])

    # Excedentes (informativo)
    excedentes = df_anom[df_anom["Tipo"] == "EXCEDENTE"]
    if not excedentes.empty:
        with st.expander(f"🟡 {len(excedentes)} artículo(s) con excedente en Flexxus"):
            for _, row in excedentes.iterrows():
                st.markdown(
                    f"- `{row['Código']}` {row['Artículo']}: "
                    f"Flexxus dice {row['Flexxus']}, esperado {row['Esperado']} "
                    f"(hay {abs(row['Diferencia'])} de más)"
                )

    # Tabla resumen descargable
    st.divider()
    st.caption(f"Total: {len(df_anom)} anomalías")
    try:
        from io import BytesIO
        buf = BytesIO()
        df_anom[["Severidad","Tipo","Código","Artículo","Ingresó","Vendido",
                 "Esperado","Flexxus","Diferencia","Detalle"]].to_excel(
            buf, index=False, engine="openpyxl")
        st.download_button(
            "📥 Descargar reporte de anomalías (.xlsx)",
            data=buf.getvalue(),
            file_name=f"anomalias_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception:
        pass


# ── Tab 4: Historial ─────────────────────────────────────────────────────────

def _tab_historial():
    st.markdown("### 📋 Historial de ingresos registrados")

    df = _ingresos_desde()
    if df.empty:
        st.info("Sin ingresos registrados.")
        return

    # Formatear para display
    df_show = df.copy()
    if "creado_en" in df_show.columns:
        df_show["Registrado"] = pd.to_datetime(
            df_show["creado_en"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")
    if "fecha_ingreso" in df_show.columns:
        df_show["Fecha ingreso"] = df_show["fecha_ingreso"]

    df_show["Estado"] = df_show.apply(
        lambda r: "✅ Completo" if r["diferencia"] == 0
                  else (f"⚠️ Faltan {r['diferencia']}" if r["diferencia"] > 0
                        else f"📦 Excedente {abs(r['diferencia'])}"), axis=1)

    cols_show = ["codigo","descripcion","cantidad_pedida","cantidad_ingresada",
                 "diferencia","Fecha ingreso","invoice_id","Estado","Registrado"]
    df_display = df_show[[c for c in cols_show if c in df_show.columns]].rename(columns={
        "codigo":"Código","descripcion":"Artículo","cantidad_pedida":"Pedido",
        "cantidad_ingresada":"Ingresó","diferencia":"Dif.","invoice_id":"Invoice",
    })

    st.dataframe(df_display, hide_index=True, use_container_width=True, height=450)
    st.caption(f"{len(df_display):,} registros")

    # Opción de eliminar registros
    st.divider()
    if st.button("🗑️ Borrar ingresos de más de 90 días", type="secondary"):
        execute_query(
            "DELETE FROM ingresos_mercaderia WHERE creado_en < datetime('now','-90 days')",
            fetch=False
        )
        st.success("Registros antiguos eliminados.")
        st.rerun()
