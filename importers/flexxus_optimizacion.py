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
        # Deduplicar columnas (Flexxus a veces repite nombres)
        df = df.loc[:, ~df.columns.duplicated()].copy()
        df.columns = [str(c).strip() for c in df.columns]

        col_map = self._mapear_columnas(df)

        # Helper seguro: devuelve Serie aunque la columna no exista
        def col_serie(key, default=0):
            c = col_map.get(key)
            if c and c in df.columns:
                s = df[c]
                # Si por alguna razón retorna DataFrame, tomar primera columna
                if isinstance(s, pd.DataFrame):
                    s = s.iloc[:, 0]
                return s
            return pd.Series([default] * len(df), index=df.index)

        df_out = pd.DataFrame(index=df.index)
        df_out["codigo"]           = col_serie("codigo", "").astype(str).str.strip()
        df_out["descripcion"]      = col_serie("descripcion", "").astype(str).str.strip()
        df_out["demanda_total"]    = pd.to_numeric(col_serie("dem_total"),  errors="coerce").fillna(0)
        df_out["demanda_promedio"] = pd.to_numeric(col_serie("dem_prom"),   errors="coerce").fillna(0)
        df_out["stock_actual"]     = pd.to_numeric(col_serie("stock"),      errors="coerce").fillna(0)
        df_out["stock_minimo"]     = pd.to_numeric(col_serie("s_min"),      errors="coerce").fillna(0)
        df_out["stock_optimo"]     = pd.to_numeric(col_serie("s_opt"),      errors="coerce").fillna(0)
        df_out["stock_maximo"]     = pd.to_numeric(col_serie("s_max"),      errors="coerce").fillna(0)
        df_out["costo_reposicion"] = pd.to_numeric(col_serie("costo"),      errors="coerce").fillna(0)
        df_out["r_minimo"]         = pd.to_numeric(col_serie("r_min"),      errors="coerce").fillna(0)
        df_out["r_optimo"]         = pd.to_numeric(col_serie("r_opt"),      errors="coerce").fillna(0)
        df_out["r_maximo"]         = pd.to_numeric(col_serie("r_max"),      errors="coerce").fillna(0)

        moneda_col = col_serie("moneda", "USD").astype(str)
        df_out["moneda"] = moneda_col.where(moneda_col.str.strip() != "", "USD")

        df_out["periodo_desde"] = None
        df_out["periodo_hasta"] = None
        df_out["dias_promedio"] = 30
        df_out["importado_en"]  = datetime.now().isoformat()

        # Filtrar filas sin código válido
        df_out = df_out[df_out["codigo"].str.len() > 2]
        df_out = df_out[df_out["codigo"] != "nan"]
        df_out = df_out[df_out["codigo"].str.strip() != ""]

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
        conn_str = "roker_nexus.db"
        import sqlite3
        conn = sqlite3.connect(conn_str)
        # Upsert manual: borrar registros del mismo día y reinsertar
        hoy = datetime.now().date().isoformat()
        conn.execute("DELETE FROM optimizacion WHERE date(importado_en)=?", (hoy,))
        df.to_sql("optimizacion", conn, if_exists="append", index=False, method="multi")
        conn.commit()
        count = len(df)
        conn.close()
        return count

    def _metadata(self, df: pd.DataFrame) -> dict:
        return {
            "total": len(df),
            "sin_stock": int((df["stock_actual"] == 0).sum()),
            "bajo_minimo": int((df["stock_actual"] < df["stock_minimo"]).sum()),
            "costo_total_usd": round(df["costo_reposicion"].sum(), 2),
        }

    def get_sugerencias_compra(self, tope_usd: float = 0) -> pd.DataFrame:
        """
        Retorna artículos que necesitan reposición, ordenados por prioridad.
        Si tope_usd > 0, limita el total a ese monto.
        """
        sql = """
            SELECT o.codigo, o.descripcion, o.stock_actual, o.stock_optimo,
                   o.demanda_promedio, o.costo_reposicion, o.moneda,
                   (o.stock_optimo - o.stock_actual) as a_pedir,
                   ((o.stock_optimo - o.stock_actual) * o.costo_reposicion) as subtotal_usd,
                   a.en_lista_negra
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo = a.codigo
            WHERE o.stock_actual < o.stock_optimo
              AND COALESCE(a.en_lista_negra, 0) = 0
            ORDER BY (o.stock_optimo - o.stock_actual) * o.costo_reposicion DESC
        """
        df = query_to_df(sql)
        if df.empty:
            return df

        if tope_usd > 0:
            df["acumulado"] = df["subtotal_usd"].cumsum()
            df = df[df["acumulado"] <= tope_usd]

        return df
