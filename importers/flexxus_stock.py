"""
ROKER NEXUS — Importador: Stock por Depósito
Flexxus: Stock → Listado General
Archivo: Planilla_de_Stock_FECHA.XLS
Se exporta 1 por depósito: SAN JOSE | LARREA NUEVO | ES LOCAL
"""
import sqlite3
from datetime import datetime
import pandas as pd

from importers.base import ImportadorBase
from utils.helpers import detectar_deposito_del_nombre


class ImportadorStock(ImportadorBase):

    NOMBRE = "stock"
    FLEXXUS_MODULO = "Stock → Listado General"
    ARCHIVO_DESCARGA = "Planilla_de_Stock_DEPOSITO_FECHA.XLS"
    COLUMNAS_REQUERIDAS = ["Código", "Stock"]

    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        nombre = getattr(uploaded_file, "name", "") if uploaded_file else ""
        deposito = detectar_deposito_del_nombre(nombre) or "DESCONOCIDO"

        col_map = self._mapear_columnas(df)

        df_out = pd.DataFrame()
        df_out["codigo"]       = df[col_map["codigo"]].astype(str).str.strip()
        df_out["deposito"]     = deposito
        df_out["stock"]        = pd.to_numeric(df.get(col_map.get("stock"), 0), errors="coerce").fillna(0)
        df_out["stock_minimo"] = pd.to_numeric(df.get(col_map.get("s_min"), 0), errors="coerce").fillna(0)
        df_out["stock_optimo"] = pd.to_numeric(df.get(col_map.get("s_opt"), 0), errors="coerce").fillna(0)
        df_out["stock_maximo"] = pd.to_numeric(df.get(col_map.get("s_max"), 0), errors="coerce").fillna(0)
        df_out["fecha"]        = datetime.now().date().isoformat()

        # Actualizar catálogo si hay descripción
        if col_map.get("descripcion"):
            df_out["_descripcion"] = df[col_map["descripcion"]].astype(str)
            self._upsert_articulos(df_out)
            df_out = df_out.drop(columns=["_descripcion"], errors="ignore")

        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[df_out["codigo"] != "nan"]

        self._deposito_detectado = deposito
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
            "descripcion": find("ARTÍCULO", "ARTICULO", "DESCRIPCION"),
            "stock":       find("STOCK", "S. ACTUAL"),
            "s_min":       find("S.MÍNIMO", "S. MÍNIMO", "MÍNIMO", "MINIMO"),
            "s_opt":       find("S.ÓPTIMO", "S. ÓPTIMO", "ÓPTIMO", "OPTIMO"),
            "s_max":       find("S.MÁXIMO", "S. MÁXIMO", "MÁXIMO", "MAXIMO"),
        }

    def _upsert_articulos(self, df: pd.DataFrame):
        conn = sqlite3.connect("roker_nexus.db")
        for _, row in df.iterrows():
            codigo = str(row["codigo"]).strip()
            desc = str(row.get("_descripcion", "")).strip()
            if not codigo or codigo == "nan":
                continue
            conn.execute(
                "INSERT OR IGNORE INTO articulos (codigo, descripcion) VALUES (?, ?)",
                (codigo, desc)
            )
        conn.commit()
        conn.close()

    def _guardar(self, df: pd.DataFrame) -> int:
        conn = sqlite3.connect("roker_nexus.db")
        deposito = df["deposito"].iloc[0] if not df.empty else "DESCONOCIDO"
        hoy = datetime.now().date().isoformat()
        # Borrar snapshot de hoy para este depósito y reinsertar
        conn.execute(
            "DELETE FROM stock_snapshots WHERE deposito=? AND fecha=?",
            (deposito, hoy)
        )
        df.to_sql("stock_snapshots", conn, if_exists="append", index=False, method="multi")
        conn.commit()
        count = len(df)
        conn.close()
        return count

    def _metadata(self, df: pd.DataFrame) -> dict:
        dep = getattr(self, "_deposito_detectado", "?")
        return {
            "deposito":   dep,
            "total":      len(df),
            "sin_stock":  int((df["stock"] == 0).sum()),
            "bajo_min":   int((df["stock"] < df["stock_minimo"]).sum()),
            "stock_total": round(float(df["stock"].sum()), 0),
        }
