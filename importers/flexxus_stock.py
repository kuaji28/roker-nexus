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
        Formato real Flexxus Planilla de Stock:
        Filas 0-7: cabecera con filtros aplicados
        Fila 8 (y repetida cada ~54 filas): headers = Código,,Artículo,,,Rubro,,,Stock,S. Mínimo,S. Máximo,S. Optimo
        Fila N+: datos  col0=código, col2=artículo, col5=rubro, col8=stock, col9=s.min, col10=s.max, col11=s.opt
        """
        nombre = getattr(uploaded_file, "name", "") if uploaded_file else ""
        deposito = detectar_deposito_del_nombre(nombre) or "GENERAL"

        HEADER_MARKER = "Código"
        registros = []
        en_datos = False

        for i, row in df.iterrows():
            val0 = str(row.iloc[0]).strip() if len(row) > 0 else ""

            # Detectar fila de headers
            if val0 == HEADER_MARKER:
                en_datos = True
                continue

            if not en_datos:
                continue

            # Saltar filas de fecha/totales/vacías
            if not val0 or val0.startswith("13/") or val0.startswith("Cantidad"):
                continue

            # Extraer campos por posición
            try:
                codigo = val0
                articulo = str(row.iloc[2]).strip() if len(row) > 2 else ""
                rubro    = str(row.iloc[5]).strip() if len(row) > 5 else ""
                stock    = pd.to_numeric(row.iloc[8],  errors="coerce") if len(row) > 8  else 0
                s_min    = pd.to_numeric(row.iloc[9],  errors="coerce") if len(row) > 9  else 0
                s_max    = pd.to_numeric(row.iloc[10], errors="coerce") if len(row) > 10 else 0
                s_opt    = pd.to_numeric(row.iloc[11], errors="coerce") if len(row) > 11 else 0

                if pd.isna(stock): stock = 0
                if pd.isna(s_min): s_min = 0
                if pd.isna(s_max): s_max = 0
                if pd.isna(s_opt): s_opt = 0

                if not codigo or codigo == "nan":
                    continue

                registros.append({
                    "codigo":        codigo,
                    "deposito":      deposito,
                    "descripcion":   articulo,
                    "rubro":         rubro,
                    "stock":         float(stock),
                    "stock_minimo":  float(s_min),
                    "stock_maximo":  float(s_max),
                    "stock_optimo":  float(s_opt),
                    "fecha":         datetime.now().date().isoformat(),
                    "fecha_snapshot": datetime.now().isoformat(),
                })
            except Exception:
                continue

        if not registros:
            return pd.DataFrame()

        df_out = pd.DataFrame(registros)
        # Actualizar catálogo de artículos
        self._upsert_articulos(df_out)
        return df_out

    def _upsert_articulos(self, df: pd.DataFrame):
        from utils.matching import tipo_codigo
        try:
            conn = __import__('sqlite3').connect("roker_nexus.db")
            for _, row in df.iterrows():
                cod  = str(row.get("codigo","")).strip()
                desc = str(row.get("descripcion","")).strip()
                if not cod or cod == "nan": continue
                conn.execute(
                    "INSERT OR IGNORE INTO articulos (codigo, descripcion) VALUES (?, ?)",
                    (cod, desc)
                )
            conn.commit()
            conn.close()
        except Exception:
            pass


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
