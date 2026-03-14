"""
ROKER NEXUS — Business Logic
Motor de cálculo de inventario, KPIs, lotes y cruces FR/MEC.
Migrado de roker_business_logic.py v3.0
"""
import pandas as pd
import numpy as np
import re
from database import get_config, get_all_config, query_to_df, execute_query

PRIORIDAD_CRITICO = "🔴 CRÍTICO"
PRIORIDAD_URGENTE = "🟠 URGENTE"
PRIORIDAD_NORMAL  = "🟡 NORMAL"
PRIORIDAD_OK      = "🟢 OK"
PRIORIDAD_EXCESO  = "🔵 EXCESO"

PROVEEDOR_FR       = "FR"
PROVEEDOR_MECANICO = "MECÁNICO"

ORDEN_PRIORIDAD = {
    PRIORIDAD_CRITICO: 0, PRIORIDAD_URGENTE: 1,
    PRIORIDAD_NORMAL: 2,  PRIORIDAD_OK: 3, PRIORIDAD_EXCESO: 4,
}


def clasificar_proveedor(codigo: str) -> str:
    """Primer carácter DÍGITO → MECÁNICO | LETRA → FR"""
    if not codigo:
        return PROVEEDOR_MECANICO
    primer = str(codigo).strip()[0]
    return PROVEEDOR_MECANICO if primer.isdigit() else PROVEEDOR_FR


def calcular_inventario_completo() -> pd.DataFrame:
    """
    Calcula el inventario completo con Stock Real (stock + tránsito),
    demanda efectiva, días de cobertura y prioridades.
    """
    cfg = get_all_config()

    def cv(k, t=float):
        try: return t(cfg.get(k, {}).get("valor", 0))
        except: return 0

    lead_time    = cv("lead_time_dias") or 45
    coef_min     = cv("coef_stock_min") or 1.0
    coef_opt     = cv("coef_stock_opt") or 1.2
    coef_max     = cv("coef_stock_max") or 1.4
    tasa_usd_ars = cv("tasa_usd_ars")   or 1420
    margen_venta = cv("margen_venta_pct") or 120

    # Leer de optimizacion (ya importada de Flexxus)
    df = query_to_df("""
        SELECT o.codigo,
               COALESCE(a.descripcion, o.descripcion) as articulo,
               o.stock_actual, o.demanda_promedio,
               o.stock_optimo, o.costo_reposicion as precio_compra,
               COALESCE(p.lista_1, 0) as precio_lista1,
               COALESCE(p.lista_4, 0) as precio_lista4,
               COALESCE(a.en_lista_negra, 0) as en_lista_negra,
               COALESCE(a.en_transito, 0) as en_transito
        FROM optimizacion o
        LEFT JOIN articulos a ON o.codigo=a.codigo
        LEFT JOIN precios p ON o.codigo=p.codigo
        WHERE COALESCE(a.en_lista_negra, 0) = 0
    """)

    if df.empty:
        return df

    df["proveedor"]        = df["codigo"].apply(clasificar_proveedor)
    df["stock_actual"]     = df["stock_actual"].fillna(0).astype(float)
    df["demanda_promedio"] = df["demanda_promedio"].fillna(0).clip(lower=0)
    df["precio_compra"]    = df["precio_compra"].fillna(0).astype(float)
    df["en_transito"]      = df["en_transito"].fillna(0).astype(float)

    # Demanda manual override
    dm = query_to_df("SELECT codigo, demanda_manual FROM demanda_manual WHERE demanda_manual > 0")
    if not dm.empty:
        dm_map = dm.set_index("codigo")["demanda_manual"].to_dict()
        df["demanda_manual_guardada"] = df["codigo"].map(dm_map).fillna(0)
    else:
        df["demanda_manual_guardada"] = 0.0

    df["demanda_efectiva"] = df.apply(
        lambda r: r["demanda_manual_guardada"] if r["demanda_manual_guardada"] > 0
                  else r["demanda_promedio"], axis=1
    )
    df["tiene_override"] = df["demanda_manual_guardada"] > 0

    # Stock Real = físico + tránsito
    df["stock_real"] = df["stock_actual"] + df["en_transito"]
    df["tiene_transito"] = df["en_transito"] > 0

    # Días de cobertura sobre stock_real
    df["dias_cobertura"] = df.apply(
        lambda r: (r["stock_real"] / (r["demanda_efectiva"] / 30))
                  if r["demanda_efectiva"] > 0 else 999.0, axis=1
    )

    df["stock_minimo_calc"] = df["demanda_efectiva"] * coef_min
    df["stock_optimo_calc"] = df["demanda_efectiva"] * coef_opt
    df["stock_maximo_calc"] = df["demanda_efectiva"] * coef_max

    df["cantidad_a_comprar"] = (
        df["stock_optimo_calc"] - df["stock_real"]
    ).clip(lower=0).apply(np.ceil)

    df["costo_compra_usd"] = df["cantidad_a_comprar"] * df["precio_compra"]
    df["prioridad"] = df.apply(lambda r: _prioridad(r, lead_time), axis=1)

    # Márgenes
    df["costo_ars"] = df["precio_compra"] * tasa_usd_ars
    df["margen_lista1_pct"] = df.apply(
        lambda r: round((float(r.get("precio_lista1", 0) or 0) - r["costo_ars"])
                        / r["costo_ars"] * 100, 1) if r["costo_ars"] > 0 else 0.0, axis=1
    )
    df["margen_lista4_pct"] = df.apply(
        lambda r: round((float(r.get("precio_lista4", 0) or 0) - r["costo_ars"])
                        / r["costo_ars"] * 100, 1) if r["costo_ars"] > 0 else 0.0, axis=1
    )

    return df


def _prioridad(row, lead_time: float) -> str:
    if row["demanda_efectiva"] == 0: return PRIORIDAD_OK
    cob = row["dias_cobertura"]
    if cob <= 0 or cob < lead_time:           return PRIORIDAD_CRITICO
    if cob < lead_time * 1.3:                 return PRIORIDAD_URGENTE
    if row["stock_real"] < row["stock_optimo_calc"]: return PRIORIDAD_NORMAL
    if row["stock_real"] > row["stock_maximo_calc"]: return PRIORIDAD_EXCESO
    return PRIORIDAD_OK


def calcular_kpis(df: pd.DataFrame) -> dict:
    """6 KPIs operativos + 4 financieros."""
    if df.empty:
        return {k: 0 for k in [
            "total_productos","criticos","urgentes","sin_stock",
            "en_transito_items","cobertura_promedio_dias",
            "valor_inventario_usd","inversion_requerida_usd",
            "costo_oportunidad_usd","productos_con_override",
        ]}

    df_fp = query_to_df("SELECT costo_total_usd FROM oportunidades_perdidas")
    costo_op = float(df_fp["costo_total_usd"].sum()) if not df_fp.empty else 0

    return {
        "total_productos":          len(df),
        "criticos":                 int((df["prioridad"] == PRIORIDAD_CRITICO).sum()),
        "urgentes":                 int((df["prioridad"] == PRIORIDAD_URGENTE).sum()),
        "sin_stock":                int((df["stock_actual"] == 0).sum()),
        "en_transito_items":        int((df.get("en_transito", 0) > 0).sum()),
        "cobertura_promedio_dias":  float(
            df[df["demanda_efectiva"] > 0]["dias_cobertura"]
            .replace(999, np.nan).mean() or 0
        ),
        "valor_inventario_usd":     float((df["stock_actual"] * df["precio_compra"]).sum()),
        "inversion_requerida_usd":  float(df["costo_compra_usd"].sum()),
        "costo_oportunidad_usd":    costo_op,
        "productos_con_override":   int(df["tiene_override"].sum()),
    }


def armar_lotes(df: pd.DataFrame, filtro_proveedor: str = "AMBOS") -> dict:
    """Arma hasta 3 lotes respetando presupuestos L1/L2/L3."""
    cfg = get_all_config()
    def p(k):
        try: return float(cfg.get(k, {}).get("valor", 0))
        except: return 0

    presupuestos = {
        1: p("presupuesto_lote_1") or 15000,
        2: p("presupuesto_lote_2") or 10000,
        3: p("presupuesto_lote_3") or 8000,
    }

    df_pool = df[df["cantidad_a_comprar"] > 0].copy()
    if filtro_proveedor == PROVEEDOR_FR:
        df_pool = df_pool[df_pool["proveedor"] == PROVEEDOR_FR]
    elif filtro_proveedor == PROVEEDOR_MECANICO:
        df_pool = df_pool[df_pool["proveedor"] == PROVEEDOR_MECANICO]

    if df_pool.empty:
        return {1: pd.DataFrame(), 2: pd.DataFrame(), 3: pd.DataFrame(), "fp": pd.DataFrame()}

    df_pool["_ord"] = df_pool["prioridad"].map(ORDEN_PRIORIDAD).fillna(5)
    df_pool = df_pool.sort_values(["_ord", "costo_compra_usd"], ascending=[True, False]).reset_index(drop=True)

    lotes = {}
    usados = set()

    for num, pres_max in presupuestos.items():
        pendientes = df_pool[~df_pool["codigo"].isin(usados)].copy()
        if pendientes.empty:
            lotes[num] = pd.DataFrame()
            continue

        items = []; acum = 0.0
        for _, row in pendientes.iterrows():
            costo = float(row["costo_compra_usd"])
            if pres_max > 0 and acum + costo > pres_max:
                disponible = pres_max - acum
                pu = float(row["precio_compra"])
                if disponible >= pu > 0:
                    qty_p = int(disponible / pu)
                    if qty_p > 0:
                        r = row.copy()
                        r["cantidad_a_comprar"] = qty_p
                        r["costo_compra_usd"]   = qty_p * pu
                        items.append(r); acum += r["costo_compra_usd"]
                        usados.add(row["codigo"])
                continue
            items.append(row); acum += costo; usados.add(row["codigo"])
            if pres_max > 0 and acum >= pres_max:
                break

        if items:
            df_l = pd.DataFrame(items).drop(columns=["_ord"], errors="ignore")
            df_l["numero_lote"] = num
            lotes[num] = df_l
        else:
            lotes[num] = pd.DataFrame()

    df_fp = df_pool[~df_pool["codigo"].isin(usados)].copy()
    lotes["fp"] = df_fp.drop(columns=["_ord"], errors="ignore")

    # Guardar oportunidades perdidas
    if not df_fp.empty:
        execute_query("DELETE FROM oportunidades_perdidas", fetch=False)
        for _, r in df_fp.iterrows():
            execute_query("""
                INSERT OR IGNORE INTO oportunidades_perdidas
                (codigo, descripcion, proveedor, stock_actual, cantidad_a_comprar,
                 precio_usd, subtotal_usd, prioridad)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                str(r.get("codigo","")), str(r.get("articulo","")),
                str(r.get("proveedor","")),
                float(r.get("stock_actual",0)), float(r.get("cantidad_a_comprar",0)),
                float(r.get("precio_compra",0)), float(r.get("costo_compra_usd",0)),
                str(r.get("prioridad","")),
            ), fetch=False)

    return lotes


def cruzar_fr_mec(df: pd.DataFrame) -> list:
    """
    Detecta mecánicos candidatos a comprar que tienen stock FR del mismo modelo.
    Retorna lista de dicts para alertar antes de confirmar pedido.
    """
    if df.empty:
        return []

    umbral = int(get_config("cruce_fr_mec_umbral_similitud") or 75)

    candidatos_mec = df[
        (df["proveedor"] == PROVEEDOR_MECANICO) & (df["cantidad_a_comprar"] > 0)
    ].copy()

    fr_con_stock = df[
        (df["proveedor"] == PROVEEDOR_FR) & (df["stock_real"] > 0)
    ].copy()

    if candidatos_mec.empty or fr_con_stock.empty:
        return []

    def normalizar(texto):
        t = str(texto).upper()
        t = re.sub(r'\b(MECANICO|MECÁNICO|CON MARCO|C/MARCO|W/F|FR)\b', '', t)
        t = re.sub(r'\b(OLED|INCELL|TFT|AMOLED)\b', '', t)
        t = re.sub(r'[^A-Z0-9\s]', ' ', t)
        return re.sub(r'\s+', ' ', t).strip()

    def similitud(a, b):
        ta, tb = set(a.split()), set(b.split())
        if not ta or not tb: return 0
        return int(len(ta & tb) / len(ta | tb) * 100)

    candidatos_mec["_n"] = candidatos_mec["articulo"].apply(normalizar)
    fr_con_stock["_n"]   = fr_con_stock["articulo"].apply(normalizar)

    cruces = []
    for _, mec in candidatos_mec.iterrows():
        for _, fr in fr_con_stock.iterrows():
            s = similitud(mec["_n"], fr["_n"])
            if s >= umbral:
                cruces.append({
                    "codigo_mec":         mec["codigo"],
                    "articulo_mec":       mec["articulo"],
                    "dias_cobertura_mec": float(mec.get("dias_cobertura", 0) or 0),
                    "cantidad_sugerida":  float(mec.get("cantidad_a_comprar", 0) or 0),
                    "codigo_fr":          fr["codigo"],
                    "articulo_fr":        fr["articulo"],
                    "stock_fr":           float(fr.get("stock_real", 0) or 0),
                    "similitud":          s,
                })

    vistos = set()
    resultado = []
    for c in sorted(cruces, key=lambda x: -x["similitud"]):
        if c["codigo_mec"] not in vistos:
            vistos.add(c["codigo_mec"])
            resultado.append(c)
    return resultado
