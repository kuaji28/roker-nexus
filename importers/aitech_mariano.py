"""
ROKER NEXUS — Importador: AI-TECH y archivo de Mariano
"""
import sqlite3
import re
from datetime import datetime
import pandas as pd

from importers.base import ImportadorBase
from utils.matching import tipo_codigo


class ImportadorAITECH(ImportadorBase):

    NOMBRE = "cotizacion_aitech"
    FLEXXUS_MODULO = "Proveedor AI-TECH"
    ARCHIVO_DESCARGA = "cotizacion_[INVOICE]_YYYYMMDD.xlsx"
    COLUMNAS_REQUERIDAS = []

    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        # Deduplicar columnas siempre
        df = df.loc[:, ~df.columns.duplicated()].copy()
        df.columns = [str(c).strip() for c in df.columns]

        nombre = getattr(uploaded_file, "name", "") if uploaded_file else ""
        invoice_id = self._extraer_invoice(nombre)
        col_map = self._mapear_columnas(df)

        def safe_serie(key, default):
            col = col_map.get(key)
            if col and col in df.columns:
                s = df[col]
                if isinstance(s, pd.DataFrame):
                    s = s.iloc[:, 0]
                return s
            return pd.Series([default] * len(df), index=df.index)

        df_out = pd.DataFrame(index=df.index)
        df_out["codigo"]        = safe_serie("codigo", "").astype(str).str.strip()
        df_out["descripcion"]   = safe_serie("descripcion", "").astype(str).str.strip()
        df_out["precio_usd"]    = pd.to_numeric(safe_serie("precio", 0),   errors="coerce").fillna(0)
        df_out["cantidad_caja"] = pd.to_numeric(safe_serie("cantidad", 1), errors="coerce").fillna(1).astype(int)

        # Todos los códigos numéricos en AI-TECH = mecánicos
        df_out["tipo"] = df_out["codigo"].apply(tipo_codigo)

        # Cotización parent
        self._invoice_id = invoice_id
        self._nombre = nombre

        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[df_out["codigo"] != "nan"]
        df_out = df_out[df_out["precio_usd"] > 0]

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
            "codigo":      find("CÓDIGO", "CODIGO", "SKU", "ITEM") or (df.columns[0] if len(df.columns) > 0 else None),
            "descripcion": find("DESCRIPCIÓN", "DESCRIPCION", "ARTÍCULO", "NOMBRE"),
            "precio":      find("PRECIO", "PRICE", "USD", "UNIT"),
            "cantidad":    find("CANTIDAD", "QTY", "PCS", "CAJA"),
        }

    def _extraer_invoice(self, nombre: str) -> str:
        match = re.search(r'0\d{2,}', nombre)
        return match.group(0) if match else "SIN_INVOICE"

    def _guardar(self, df: pd.DataFrame) -> int:
        conn = sqlite3.connect("roker_nexus.db")
        now = datetime.now().isoformat()

        # Crear cotización parent
        cur = conn.execute("""
            INSERT INTO cotizaciones (proveedor, invoice_id, fecha, total_usd)
            VALUES (?, ?, ?, ?)
        """, ("AITECH", getattr(self, "_invoice_id", ""), datetime.now().date().isoformat(),
              float(df["precio_usd"].sum())))
        cotizacion_id = cur.lastrowid

        # Insertar items
        df["cotizacion_id"] = cotizacion_id
        items_df = df.rename(columns={"codigo": "codigo", "descripcion": "descripcion",
                                       "precio_usd": "precio_usd", "cantidad_caja": "cantidad_caja"})
        cols = ["cotizacion_id", "codigo", "descripcion", "precio_usd", "cantidad_caja"]
        items_df[cols].to_sql("cotizacion_items", conn, if_exists="append", index=False)

        conn.commit()
        count = len(df)
        conn.close()
        return count


class ImportadorMariano(ImportadorBase):
    """
    Importa el archivo mensual de Mariano.
    Tiene múltiples hojas: Repuestos, PROV 1 FR, Lista de Precios, Stock.
    """

    NOMBRE = "mariano"
    FLEXXUS_MODULO = "Interno — archivo de Mariano"
    ARCHIVO_DESCARGA = "optimizacion_YYYYMMDD.xlsx"
    COLUMNAS_REQUERIDAS = []

    def _leer(self, uploaded_file) -> pd.DataFrame:
        """Override — necesitamos leer múltiples hojas."""
        import pandas as pd
        nombre = getattr(uploaded_file, "name", "")
        ext = nombre.split(".")[-1].lower()
        engine = "xlrd" if ext == "xls" else "openpyxl"

        self._hojas = {}
        try:
            xls = pd.ExcelFile(uploaded_file, engine=engine)
            for hoja in xls.sheet_names:
                self._hojas[hoja] = xls.parse(hoja)
        except Exception as e:
            pass

        # Retorna la hoja principal (Repuestos)
        for key in self._hojas:
            if "repuesto" in key.lower():
                return self._hojas[key]
        # Si no, la primera
        if self._hojas:
            return list(self._hojas.values())[0]
        return pd.DataFrame()

    def _validar_columnas(self, df: pd.DataFrame) -> tuple:
        # Flexible — Mariano no tiene estructura fija de headers
        return True, ""

    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        """
        Procesa las hojas del archivo de Mariano.
        """
        results = {}

        # Hoja 1: Repuestos (demanda y stock)
        hoja_rep = self._get_hoja_repuestos()
        if hoja_rep is not None:
            results["repuestos"] = self._procesar_repuestos(hoja_rep)

        # Hoja 3: Lista de Precios
        hoja_precios = self._get_hoja_precios()
        if hoja_precios is not None:
            results["precios"] = self._procesar_precios(hoja_precios)

        self._resultados_hojas = results

        # Retornar la hoja de repuestos como principal
        return results.get("repuestos", pd.DataFrame())

    def _get_hoja_repuestos(self):
        for k, v in self._hojas.items():
            if "repuesto" in k.lower():
                return v
        return None

    def _get_hoja_precios(self):
        for k, v in self._hojas.items():
            if "precio" in k.lower() or "lista" in k.lower():
                return v
        return None

    def _procesar_repuestos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Procesa la hoja de repuestos de Mariano."""
        # Buscar fila de headers
        from utils.helpers import encontrar_fila_header
        fila_h = encontrar_fila_header(df, ["Código", "Artículo", "Demanda"])
        if fila_h > 0:
            df.columns = df.iloc[fila_h]
            df = df.iloc[fila_h+1:].reset_index(drop=True)
            df.columns = [str(c).strip() for c in df.columns]

        cols = {c.upper(): c for c in df.columns}
        def find(*kws):
            for kw in kws:
                for cu, co in cols.items():
                    if kw.upper() in cu:
                        return co
            return None

        df_out = pd.DataFrame()
        cod_col = find("CÓDIGO", "CODIGO") or df.columns[0]
        df_out["codigo"]           = df[cod_col].astype(str).str.strip()
        df_out["descripcion"]      = df.get(find("ARTÍCULO", "ARTICULO"), None)
        df_out["demanda_total"]    = pd.to_numeric(df.get(find("DEMANDA TOTAL", "DEM TOTAL"), 0), errors="coerce").fillna(0)
        df_out["demanda_promedio"] = pd.to_numeric(df.get(find("DEMANDA PROM", "DEM PROM"), 0), errors="coerce").fillna(0)
        df_out["stock_actual"]     = pd.to_numeric(df.get(find("S. ACTUAL", "STOCK ACTUAL", "S.ACTUAL"), 0), errors="coerce").fillna(0)
        df_out["stock_minimo"]     = pd.to_numeric(df.get(find("STOCK MÍNIMO", "S. MÍNIMO", "MÍNIMO"), 0), errors="coerce").fillna(0)
        df_out["a_pedir"]          = pd.to_numeric(df.get(find("A PEDIR"), 0), errors="coerce").fillna(0)
        df_out["importado_en"]     = datetime.now().isoformat()

        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[df_out["codigo"] != "nan"]
        return df_out

    def _procesar_precios(self, df: pd.DataFrame) -> pd.DataFrame:
        """Procesa la hoja de lista de precios de Mariano."""
        from utils.helpers import encontrar_fila_header
        fila_h = encontrar_fila_header(df, ["Código", "Lista 1", "Descripción"])
        if fila_h > 0:
            df.columns = df.iloc[fila_h]
            df = df.iloc[fila_h+1:].reset_index(drop=True)
            df.columns = [str(c).strip() for c in df.columns]

        cols = {c.upper(): c for c in df.columns}
        def find(*kws):
            for kw in kws:
                for cu, co in cols.items():
                    if kw.upper() in cu:
                        return co
            return None

        df_out = pd.DataFrame()
        cod_col = find("CÓDIGO", "CODIGO") or df.columns[0]
        df_out["codigo"]      = df[cod_col].astype(str).str.strip()
        df_out["descripcion"] = df.get(find("DESCRIPCIÓN", "DESCRIPCION"), None)
        df_out["lista_1"]     = pd.to_numeric(df.get(find("LISTA 1", "LIST 1"), 0), errors="coerce").fillna(0)
        df_out["precio_comp"] = pd.to_numeric(df.get(find("P. COMP", "PRECIO COMP", "COSTO"), 0), errors="coerce").fillna(0)
        df_out["moneda"]      = df.get(find("MON", "MONEDA"), "USD").fillna("USD")
        df_out["fecha"]       = datetime.now().date().isoformat()

        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[df_out["codigo"] != "nan"]
        return df_out

    def _guardar(self, df: pd.DataFrame) -> int:
        conn = sqlite3.connect("roker_nexus.db")
        total = 0

        # Guardar repuestos en tabla optimizacion
        if not df.empty and "demanda_total" in df.columns:
            hoy = datetime.now().date().isoformat()
            conn.execute("DELETE FROM optimizacion WHERE date(importado_en)=?", (hoy,))
            df.to_sql("optimizacion", conn, if_exists="append", index=False, method="multi")
            total += len(df)

        # Guardar precios si están disponibles
        precios_df = getattr(self, "_resultados_hojas", {}).get("precios")
        if precios_df is not None and not precios_df.empty:
            hoy = datetime.now().date().isoformat()
            conn.execute("DELETE FROM precios WHERE fecha=?", (hoy,))
            cols_precio = [c for c in ["codigo", "descripcion", "lista_1", "moneda", "fecha"]
                          if c in precios_df.columns]
            precios_df[cols_precio].to_sql("precios", conn, if_exists="append", index=False)

        conn.commit()
        conn.close()
        return total

    def _metadata(self, df: pd.DataFrame) -> dict:
        hojas = list(getattr(self, "_hojas", {}).keys())
        return {
            "hojas_encontradas": hojas,
            "total_articulos":   len(df),
            "a_pedir":           int(df["a_pedir"].sum()) if "a_pedir" in df.columns else 0,
        }
