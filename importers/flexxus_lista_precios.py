"""
ROKER NEXUS — Importador: Lista de Precios
Flexxus: Ventas → Lista de Precios Editable
Archivo: Lista de Precios_FECHA.XLS
Lista 1 = Mayorista | Lista 4 = MercadoLibre
"""
import sqlite3
from datetime import datetime
import pandas as pd

from importers.base import ImportadorBase
from utils.matching import tipo_codigo, extraer_marca, extraer_modelo


class ImportadorListaPrecios(ImportadorBase):

    NOMBRE = "lista_precios"
    FLEXXUS_MODULO = "Ventas → Lista de Precios Editable"
    ARCHIVO_DESCARGA = "Lista de Precios_FECHA.XLS"
    COLUMNAS_REQUERIDAS = ["Código", "Lista 1"]

    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        # Deduplicar columnas por si Flexxus repite nombres
        df = df.loc[:, ~df.columns.duplicated()].copy()
        col_map = self._mapear_columnas(df)

        df_out = pd.DataFrame()
        df_out["codigo"]      = df[col_map["codigo"]].astype(str).str.strip()
        df_out["descripcion"] = df.get(col_map.get("descripcion"), pd.Series(dtype=str))
        df_out["lista_1"]     = pd.to_numeric(df.get(col_map.get("l1"), 0), errors="coerce").fillna(0)
        df_out["lista_2"]     = pd.to_numeric(df.get(col_map.get("l2"), 0), errors="coerce").fillna(0)
        df_out["lista_3"]     = pd.to_numeric(df.get(col_map.get("l3"), 0), errors="coerce").fillna(0)
        df_out["lista_4"]     = pd.to_numeric(df.get(col_map.get("l4"), 0), errors="coerce").fillna(0)
        df_out["lista_5"]     = pd.to_numeric(df.get(col_map.get("l5"), 0), errors="coerce").fillna(0)
        df_out["moneda"]      = "USD"
        df_out["fecha"]       = datetime.now().date().isoformat()

        # Filtrar inválidos
        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[df_out["codigo"] != "nan"]

        # Actualizar catálogo de artículos con lo que no exista
        self._upsert_articulos(df_out)

        return df_out

    def _mapear_columnas(self, df: pd.DataFrame) -> dict:
        cols = {c.upper(): c for c in df.columns}
        def find(*keywords):
            for kw in keywords:
                for cu, co in cols.items():
                    if kw.upper() in cu:
                        return co
            return None

        return {
            "codigo":      find("CÓDIGO", "CODIGO") or df.columns[0],
            "descripcion": find("DESCRIPCIÓN", "DESCRIPCION", "ARTÍCULO"),
            "l1": find("LISTA 1", "LIST 1", "L1"),
            "l2": find("LISTA 2", "LIST 2", "L2"),
            "l3": find("LISTA 3", "LIST 3", "L3"),
            "l4": find("LISTA 4", "LIST 4", "L4"),
            "l5": find("LISTA 5", "LIST 5", "L5"),
        }

    def _upsert_articulos(self, df: pd.DataFrame):
        """Inserta artículos nuevos en el catálogo maestro."""
        import os as _os_lp
        _db_path = _os_lp.path.join(_os_lp.path.dirname(_os_lp.path.abspath(__file__)), "..", "roker_nexus.db")
        conn = sqlite3.connect(_db_path)
        for _, row in df.iterrows():
            codigo = str(row.get("codigo", "")).strip()
            desc   = str(row.get("descripcion", "")).strip()
            if not codigo or codigo == "nan":
                continue
            t = tipo_codigo(codigo)
            marca = extraer_marca(desc) if desc else None
            conn.execute("""
                INSERT OR IGNORE INTO articulos
                    (codigo, descripcion, tipo_codigo, marca)
                VALUES (?, ?, ?, ?)
            """, (codigo, desc, t, marca))
        conn.commit()
        conn.close()

    def _guardar(self, df: pd.DataFrame) -> int:
        from database import df_to_db, execute_query
        hoy = datetime.now().date().isoformat()
        execute_query("DELETE FROM precios WHERE fecha=?", (hoy,), fetch=False)
        cols_validas = ["codigo", "lista_1", "lista_2", "lista_3", "lista_4", "lista_5", "moneda", "fecha"]
        df_save = df[[c for c in cols_validas if c in df.columns]]
        return df_to_db(df_save, "precios")

    def _metadata(self, df: pd.DataFrame) -> dict:
        return {
            "total": len(df),
            "con_precio_ml":  int((df["lista_4"] > 0).sum()),
            "sin_precio_ml":  int((df["lista_4"] == 0).sum()),
            "precio_max_l1":  round(float(df["lista_1"].max()), 2),
            "precio_prom_l1": round(float(df["lista_1"].mean()), 2),
        }
