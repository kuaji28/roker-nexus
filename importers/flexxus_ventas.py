"""
ROKER NEXUS — Importador: Ventas por Artículo y Compras por Marca
Ventas: Flexxus Informes → Ventas por Artículo
        Archivo: Planilla de Ventas por Marca Resumida_FECHA.XLS
Compras: Flexxus Informes → Compras por Marca
         Archivo: Planilla de Ventas por Marca_FECHA.XLS  (sin "Resumida")
"""
import sqlite3
import re
from datetime import datetime
import pandas as pd

from importers.base import ImportadorBase


class ImportadorVentas(ImportadorBase):

    NOMBRE = "ventas"
    FLEXXUS_MODULO = "Informes → Ventas por Artículo"
    ARCHIVO_DESCARGA = "Planilla de Ventas por Marca Resumida_FECHA.XLS"
    COLUMNAS_REQUERIDAS = ["Código", "Artículo"]

    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        # Deduplicar columnas por si Flexxus repite nombres
        df = df.loc[:, ~df.columns.duplicated()].copy()
        col_map = self._mapear_columnas(df)

        df_out = pd.DataFrame()
        df_out["codigo"]          = df[col_map["codigo"]].astype(str).str.strip()
        df_out["descripcion"]     = df.get(col_map.get("descripcion"), pd.Series(dtype=str))
        df_out["total_venta_ars"] = pd.to_numeric(
            df.get(col_map.get("total"), 0), errors="coerce"
        ).fillna(0)
        df_out["marca"]           = df.get(col_map.get("marca"), None)
        df_out["super_rubro"]     = df.get(col_map.get("super_rubro"), None)

        # Extraer fechas del archivo si están en el encabezado
        df_out["fecha_desde"]     = self._extraer_fecha_desde
        df_out["fecha_hasta"]     = datetime.now().date().isoformat()

        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[df_out["codigo"] != "nan"]
        return df_out

    def _mapear_columnas(self, df: pd.DataFrame) -> dict:
        cols = {c.upper(): c for c in df.columns}
        def find(*kws):
            for kw in kws:
                for cu, co in cols.items():
                    if kw.upper() in cu:
                        return co
            return None

        return {
            "codigo":      find("CÓDIGO", "CODIGO") or df.columns[0],
            "descripcion": find("ARTÍCULO", "ARTICULO"),
            "total":       find("TOTAL VTA", "TOTAL_VTA", "TOTAL"),
            "marca":       find("MARCA"),
            "super_rubro": find("SUPER RUBRO", "SUPE"),
        }

    @property
    def _extraer_fecha_desde(self):
        return "2026-01-01"  # Valor por defecto

    def _guardar(self, df: pd.DataFrame) -> int:
        from database import df_to_db, execute_query
        try:
            if "fecha_desde" in df.columns and "fecha_hasta" in df.columns and len(df):
                fd = str(df["fecha_desde"].iloc[0])
                fh = str(df["fecha_hasta"].iloc[0])
                if fd and fh and fd != "None":
                    execute_query("DELETE FROM ventas WHERE fecha_desde=? AND fecha_hasta=?",
                                  (fd, fh), fetch=False)
                else:
                    execute_query("DELETE FROM ventas", fetch=False)
            else:
                execute_query("DELETE FROM ventas", fetch=False)
        except Exception:
            pass
        return df_to_db(df, "ventas")

    def _metadata(self, df: pd.DataFrame) -> dict:
        total = df["total_venta_ars"].sum() if "total_venta_ars" in df.columns else 0
        return {
            "total_registros":  len(df),
            "total_venta_ars":  round(float(total), 2),
            "marcas_distintas": df["marca"].nunique() if "marca" in df.columns else 0,
        }


class ImportadorCompras(ImportadorBase):

    NOMBRE = "compras"
    FLEXXUS_MODULO = "Informes → Compras por Marca"
    ARCHIVO_DESCARGA = "Planilla de Ventas por Marca_FECHA.XLS"
    COLUMNAS_REQUERIDAS = ["Código", "Artículo", "Cantidad"]

    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        # Deduplicar columnas por si Flexxus repite nombres
        df = df.loc[:, ~df.columns.duplicated()].copy()
        col_map = self._mapear_columnas(df)

        df_out = pd.DataFrame()
        df_out["codigo"]      = df[col_map["codigo"]].astype(str).str.strip()
        df_out["descripcion"] = df.get(col_map.get("descripcion"), None)
        df_out["marca"]       = df.get(col_map.get("marca"), None)
        df_out["rubro"]       = df.get(col_map.get("rubro"), None)
        df_out["cantidad"]    = pd.to_numeric(
            df.get(col_map.get("cantidad"), 0), errors="coerce"
        ).fillna(0)
        df_out["fecha_desde"] = "2026-01-01"
        df_out["fecha_hasta"] = datetime.now().date().isoformat()

        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[df_out["codigo"] != "nan"]
        return df_out

    def _mapear_columnas(self, df: pd.DataFrame) -> dict:
        cols = {c.upper(): c for c in df.columns}
        def find(*kws):
            for kw in kws:
                for cu, co in cols.items():
                    if kw.upper() in cu:
                        return co
            return None
        return {
            "codigo":      find("CÓDIGO", "CODIGO") or df.columns[0],
            "descripcion": find("ARTÍCULO", "ARTICULO"),
            "marca":       find("MARCA"),
            "rubro":       find("RUBRO"),
            "cantidad":    find("CANTIDAD"),
        }

    def _guardar(self, df: pd.DataFrame) -> int:
        from database import df_to_db, execute_query
        if "fecha_desde" in df.columns and "fecha_hasta" in df.columns and len(df):
            fd, fh = df["fecha_desde"].iloc[0], df["fecha_hasta"].iloc[0]
            if fd and fh:
                execute_query("DELETE FROM compras_historial WHERE fecha_desde=? AND fecha_hasta=?",
                              (str(fd), str(fh)), fetch=False)
            else:
                execute_query("DELETE FROM compras_historial", fetch=False)
        else:
            execute_query("DELETE FROM compras_historial", fetch=False)
        return df_to_db(df, "compras_historial")

    def _metadata(self, df: pd.DataFrame) -> dict:
        return {
            "total_registros":  len(df),
            "total_unidades":   int(df["cantidad"].sum()) if "cantidad" in df.columns else 0,
            "marcas_distintas": df["marca"].nunique() if "marca" in df.columns else 0,
        }
