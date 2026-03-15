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
        """
        Formato confirmado Flexxus Planilla de Stock:
        - Header real: fila 8 (contiene "Código", "Artículo", etc.)
        - Datos desde: fila 9
        - col 0: Código
        - col 2: Artículo/Descripción
        - col 5: Rubro
        - col 7: Stock (⚠️ no col 8)
        - col 9: S.Mínimo
        - col 10: S.Máximo
        - col 11: S.Óptimo
        - Sin columna de depósito — se infiere del nombre del archivo
        """
        nombre = getattr(uploaded_file, "name", "") if uploaded_file else ""
        deposito = detectar_deposito_del_nombre(nombre) or "GENERAL"

        registros = []
        en_datos = False

        for i, row in df.iterrows():
            val0 = str(row.iloc[0]).strip() if len(row) > 0 else ""

            # Detectar fila de headers (fila 8)
            if val0 == "Código":
                en_datos = True
                continue

            if not en_datos:
                continue

            # Saltar filas vacías, totales o fechas
            if not val0 or val0 in ("nan", "") or val0.startswith("Cantidad") or val0.startswith("13/") or val0.startswith("14/"):
                continue

            try:
                codigo   = val0
                articulo = str(row.iloc[2]).strip()  if len(row) > 2  else ""
                rubro    = str(row.iloc[5]).strip()  if len(row) > 5  else ""
                stock    = pd.to_numeric(row.iloc[7],  errors="coerce") if len(row) > 7  else 0
                s_min    = pd.to_numeric(row.iloc[9],  errors="coerce") if len(row) > 9  else 0
                s_max    = pd.to_numeric(row.iloc[10], errors="coerce") if len(row) > 10 else 0
                s_opt    = pd.to_numeric(row.iloc[11], errors="coerce") if len(row) > 11 else 0

                if pd.isna(stock): stock = 0
                if pd.isna(s_min): s_min = 0
                if pd.isna(s_max): s_max = 0
                if pd.isna(s_opt): s_opt = 0

                if not codigo or codigo == "nan":
                    continue
                # Saltar si parece una fila de página (contiene "/" tipo fecha)
                if "/" in codigo and len(codigo) < 12:
                    continue

                registros.append({
                    "codigo":         codigo,
                    "deposito":       deposito,
                    "descripcion":    articulo,
                    "rubro":          rubro,
                    "stock":          float(stock),
                    "stock_minimo":   float(s_min),
                    "stock_maximo":   float(s_max),
                    "stock_optimo":   float(s_opt),
                    "fecha":          datetime.now().date().isoformat(),
                    "fecha_snapshot": datetime.now().isoformat(),
                })
            except Exception:
                continue

        if not registros:
            return pd.DataFrame()

        df_out = pd.DataFrame(registros)
        self._upsert_articulos(df_out)
        return df_out
    def _upsert_articulos(self, df: pd.DataFrame):
        """Inserta artículos nuevos en el catálogo maestro (bulk, PostgreSQL-compatible)."""
        from database import df_to_db
        from utils.matching import tipo_codigo
        try:
            df_arts = df[["codigo","descripcion"]].copy()
            df_arts["codigo"] = df_arts["codigo"].astype(str).str.strip()
            df_arts = df_arts[df_arts["codigo"].str.len() > 0]
            df_arts = df_arts[df_arts["codigo"] != "nan"]
            df_arts["descripcion"] = df_arts["descripcion"].astype(str).str.strip()
            df_arts["tipo_codigo"] = df_arts["codigo"].apply(tipo_codigo)
            df_to_db(df_arts, "articulos")
        except Exception:
            pass


    def _guardar(self, df: pd.DataFrame) -> int:
        from database import df_to_db, execute_query
        if df.empty:
            return 0
        deposito = df["deposito"].iloc[0]
        hoy = datetime.now().date().isoformat()
        # Borrar snapshot de hoy para este depósito
        execute_query(
            "DELETE FROM stock_snapshots WHERE deposito=? AND fecha=?",
            (deposito, hoy), fetch=False
        )
        # Asegurar columnas correctas
        cols = ["codigo","deposito","descripcion","rubro",
                "stock","stock_minimo","stock_maximo","stock_optimo",
                "fecha","fecha_snapshot"]
        df_save = df[[c for c in cols if c in df.columns]]
        n = df_to_db(df_save, "stock_snapshots")

        # ── Alertas de stock ──────────────────────────────────────────────────
        try:
            from modules.stock_alertas import analizar_y_alertar
            self._resultado_alertas = analizar_y_alertar(df, deposito)
        except Exception:
            self._resultado_alertas = {}

        return n
    def _metadata(self, df: pd.DataFrame) -> dict:
        dep = getattr(self, "_deposito_detectado", "?")
        return {
            "deposito":   dep,
            "total":      len(df),
            "sin_stock":  int((df["stock"] == 0).sum()),
            "bajo_min":   int((df["stock"] < df["stock_minimo"]).sum()),
            "stock_total": round(float(df["stock"].sum()), 0),
        }
