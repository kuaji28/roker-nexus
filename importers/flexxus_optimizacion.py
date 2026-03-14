"""
ROKER NEXUS — Importador: Optimización de Stock
Flexxus: Stock → Optimización de Stock
Archivo: Optimizacin_de_Stock_FECHA.XLS  (typo intencional de Flexxus)
"""
import re
from datetime import datetime
import pandas as pd

from importers.base import ImportadorBase
from database import execute_query, query_to_df
from utils.matching import tipo_codigo


class ImportadorOptimizacion(ImportadorBase):

    NOMBRE = "optimizacion"
    FLEXXUS_MODULO = "Stock → Optimización de Stock"
    ARCHIVO_DESCARGA = "Optimizacin_de_Stock_FECHA.XLS"
    COLUMNAS_REQUERIDAS = ["Código", "Artículo"]

    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        """
        Formato real Flexxus Optimización de Stock:
        Fila 11: headers = Código | Artículo | _ | _ | _ | Demanda Total | _ | Demanda Prom. | S.Actual | S.Mín | S.Opt | S.Máx
        Col:       0          1      2   3   4       5         6               7            8        9      10      11
        NO tiene columna de costo — se cruza con lista de precios después
        """
        # Encontrar fila de headers
        header_row = None
        for i, row in df.iterrows():
            if str(row.iloc[0]).strip() == "Código":
                header_row = i
                break

        if header_row is None:
            return pd.DataFrame()

        df_data = df.iloc[header_row + 1:].copy()
        df_data.columns = range(len(df_data.columns))
        df_data = df_data.dropna(subset=[0])

        def safe_num(col_idx, default=0):
            if col_idx >= len(df_data.columns):
                return pd.Series([default] * len(df_data))
            return pd.to_numeric(df_data[col_idx], errors="coerce").fillna(default)

        df_out = pd.DataFrame()
        df_out["codigo"]           = df_data[0].astype(str).str.strip()
        df_out["descripcion"]      = df_data[1].astype(str).str.strip() if 1 < len(df_data.columns) else ""
        df_out["demanda_total"]    = safe_num(5)
        df_out["demanda_promedio"] = safe_num(7)
        df_out["stock_actual"]     = safe_num(8)
        df_out["stock_minimo"]     = safe_num(9)
        df_out["stock_optimo"]     = safe_num(10)
        df_out["stock_maximo"]     = safe_num(11)
        df_out["costo_reposicion"] = 0.0  # Se cruza con Lista de Precios
        df_out["moneda"]           = "USD"
        df_out["periodo_desde"]    = None
        df_out["periodo_hasta"]    = None
        df_out["dias_promedio"]    = 30

        # Timestamp único por fila
        from datetime import timedelta
        base_ts = datetime.now()
        df_out["importado_en"] = [
            (base_ts + timedelta(microseconds=i)).isoformat()
            for i in range(len(df_out))
        ]

        # Filtrar filas inválidas
        df_out = df_out[df_out["codigo"].str.len() > 2]
        df_out = df_out[df_out["codigo"] != "nan"]
        df_out = df_out[~df_out["codigo"].str.startswith("nan")]

        # Cruzar costo con Lista de Precios si existe
        try:
            from database import execute_query
            rows = execute_query("SELECT codigo, lista_1 FROM precios WHERE lista_1 > 0")
            if rows:
                import pandas as _pd
                df_precios = _pd.DataFrame(rows)
                df_out = df_out.merge(
                    df_precios.rename(columns={"lista_1": "costo_ref"}),
                    on="codigo", how="left"
                )
                mask = df_out["costo_ref"].notna() & (df_out["costo_ref"] > 0)
                df_out.loc[mask, "costo_reposicion"] = df_out.loc[mask, "costo_ref"]
                df_out = df_out.drop(columns=["costo_ref"])
        except Exception:
            pass

        return df_out


    def _mapear_columnas(self, df: pd.DataFrame) -> dict:
        """Mapea columnas del archivo a campos internos de forma flexible."""
        cols = {c.upper(): c for c in df.columns}
        def find(keywords):
            for kw in keywords:
                for col_up, col_orig in cols.items():
                    if kw in col_up:
                        return col_orig
            return None

        return {
            "codigo":      find(["CÓDIGO", "CODIGO", "CÓD", "COD"]) or df.columns[0],
            "descripcion": find(["ARTÍCULO", "ARTICULO", "DESCRIPCION", "DESC"]),
            "dem_total":   find(["DEMANDA TOTA", "DEM TOTAL", "DEMANDA_TOTA"]),
            "dem_prom":    find(["DEMANDA PROM", "DEM PROM", "DEMANDA_PROM"]),
            "stock":       find(["S. ACTUAL", "STOCK ACTUAL", "S.ACTUAL", "ACTUAL"]),
            "s_min":       find(["S. MÍNIMO", "S. MINIMO", "STOCK MIN", "MÍNIMO"]),
            "s_opt":       find(["S. OPTIMO", "S. ÓPTIMO", "STOCK OPT", "ÓPTIMO"]),
            "s_max":       find(["S. MÁXIMO", "S. MAXIMO", "STOCK MAX", "MÁXIMO"]),
            "costo":       find(["COSTO REPO", "COSTO"]),
            "moneda":      find(["MONEDA"]),
            "r_min":       find(["R. MÍNIMO", "R. MINIMO", "R.MINIMO"]),
            "r_opt":       find(["R. OPTIMO", "R. ÓPTIMO", "R.OPTIMO"]),
            "r_max":       find(["R. MÁXIMO", "R. MAXIMO", "R.MAXIMO"]),
        }

    def _guardar(self, df: pd.DataFrame) -> int:
        from database import df_to_db, execute_query
        # Limpiar tabla completa antes de insertar (es un snapshot)
        execute_query("DELETE FROM optimizacion", fetch=False)
        return df_to_db(df, "optimizacion")

    def _metadata(self, df: pd.DataFrame) -> dict:
        return {
            "total": len(df),
            "sin_stock": int((df["stock_actual"] == 0).sum()),
            "bajo_minimo": int((df["stock_actual"] < df["stock_minimo"]).sum()),
            "costo_total_usd": round(df["costo_reposicion"].sum(), 2),
        }

    def get_sugerencias_compra(self, tope_usd: float = 0, proveedor: str = "TODOS") -> pd.DataFrame:
        """
        Retorna artículos que necesitan reposición, filtrados por proveedor.
        FR (AITECH): códigos que empiezan con LETRA
        MECÁNICO: códigos que empiezan con NÚMERO
        """
        sql = """
            SELECT o.codigo, o.descripcion, o.stock_actual, o.stock_optimo,
                   o.demanda_promedio, o.costo_reposicion, o.moneda,
                   (o.stock_optimo - o.stock_actual) as a_pedir,
                   ((o.stock_optimo - o.stock_actual) * o.costo_reposicion) as subtotal_usd,
                   COALESCE(a.en_lista_negra, 0) as en_lista_negra
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo = a.codigo
            WHERE o.stock_actual < o.stock_optimo
              AND COALESCE(a.en_lista_negra, 0) = 0
              AND (o.stock_optimo - o.stock_actual) > 0
            ORDER BY (o.stock_optimo - o.stock_actual) * o.costo_reposicion DESC
        """
        df = query_to_df(sql)
        if df.empty:
            return df

        # Filtrar por proveedor según primera letra del código
        prov_up = proveedor.upper()
        if "MECÁNICO" in prov_up or "MECANICO" in prov_up:
            df = df[df["codigo"].str[0].str.isdigit()]
        elif "FR" in prov_up or "AITECH" in prov_up:
            df = df[df["codigo"].str[0].str.isalpha()]
        # Si es "TODOS" o cualquier otro, no filtra

        if tope_usd > 0:
            df = df[df["subtotal_usd"] > 0]  # Solo con costo conocido primero
            df["acumulado"] = df["subtotal_usd"].cumsum()
            df = df[df["acumulado"] <= tope_usd]

        return df
