"""
ROKER NEXUS — Importador: AI-TECH y archivo de Mariano
"""
import re
from datetime import datetime
import pandas as pd

from importers.base import ImportadorBase
from utils.matching import tipo_codigo


class ImportadorAITECH(ImportadorBase):
    """
    Formato real AI-TECH (PI sheet):
      Fila 0: Invoice header
      Fila 1: Brand | codigo | MODELO UNIVERSAL | MODELO STICKER | Spec | ... | QTY | PRICE | Total
      Fila 2: Categoría (LCD+TOUCH, etc.)
      Fila 3+: Datos
    """
    NOMBRE = "cotizacion_aitech"
    FLEXXUS_MODULO = "Proveedor AI-TECH"
    ARCHIVO_DESCARGA = "LA COTIZACION DE AI-TECH XXX-YYYYMMDD.xlsx"
    COLUMNAS_REQUERIDAS = []

    def _leer(self, uploaded_file) -> pd.DataFrame:
        """Lee sin header — el formato es fijo por posición de columna."""
        import pandas as pd
        nombre = getattr(uploaded_file, "name", "")
        ext = nombre.split(".")[-1].lower()
        engine = "xlrd" if ext == "xls" else "openpyxl"
        try:
            return pd.read_excel(uploaded_file, header=None, engine=engine)
        except Exception:
            return pd.read_excel(uploaded_file, header=None)

    def _detectar_y_setear_headers(self, df):
        return df  # No tocar — manejamos por posición

    def _validar_columnas(self, df):
        return True, ""

    def _limpiar(self, df):
        return df  # No limpiar aquí — lo hacemos en _transformar

    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        nombre = getattr(uploaded_file, "name", "") if uploaded_file else ""
        self._invoice_id = self._extraer_invoice(nombre)
        self._nombre = nombre

        # Formato fijo por posición:
        # col 0: brand prefix | col 1: codigo | col 2: descripcion
        # col 8: QTY | col 9: PRICE | col 10: Total
        registros = []
        for i, row in df.iterrows():
            # Saltar filas de header/categoria (sin precio numérico)
            precio = pd.to_numeric(row.iloc[9] if len(row) > 9 else None, errors="coerce")
            if pd.isna(precio) or precio <= 0:
                continue
            codigo_raw = row.iloc[1] if len(row) > 1 else None
            if pd.isna(codigo_raw):
                continue
            codigo = str(int(float(codigo_raw))) if isinstance(codigo_raw, float) else str(codigo_raw).strip()
            desc   = str(row.iloc[2]).strip() if len(row) > 2 and not pd.isna(row.iloc[2]) else ""
            qty    = int(pd.to_numeric(row.iloc[8], errors="coerce") or 1) if len(row) > 8 else 1
            registros.append({
                "codigo":       codigo,
                "descripcion":  desc,
                "precio_usd":   float(precio),
                "cantidad_caja": qty,
            })

        if not registros:
            return pd.DataFrame(columns=["codigo","descripcion","precio_usd","cantidad_caja"])

        df_out = pd.DataFrame(registros)
        df_out["tipo"] = df_out["codigo"].apply(tipo_codigo)
        return df_out

    def _extraer_invoice(self, nombre: str) -> str:
        match = re.search(r'0\d{2,}', nombre)
        return match.group(0) if match else "SIN_INVOICE"

    def _guardar(self, df: pd.DataFrame) -> int:
        from database import execute_query, df_to_db
        invoice_id = getattr(self, "_invoice_id", "SIN_INVOICE")
        fecha_hoy  = datetime.now().date().isoformat()
        total_usd  = float(df["precio_usd"].sum())

        # ¿Ya existe esta cotización?
        rows = execute_query(
            "SELECT id FROM cotizaciones WHERE invoice_id=? AND proveedor='AITECH'",
            (invoice_id,), fetch=True
        )
        if rows:
            cotizacion_id = rows[0]["id"]
            execute_query("DELETE FROM cotizacion_items WHERE cotizacion_id=?",
                          (cotizacion_id,), fetch=False)
            execute_query(
                "UPDATE cotizaciones SET total_usd=?, fecha=? WHERE id=?",
                (total_usd, fecha_hoy, cotizacion_id), fetch=False
            )
        else:
            execute_query(
                "INSERT INTO cotizaciones (proveedor, invoice_id, fecha, total_usd, estado) "
                "VALUES (?,?,?,?,'pendiente')",
                ("AITECH", invoice_id, fecha_hoy, total_usd), fetch=False
            )
            # Obtener el ID recién insertado
            rows2 = execute_query(
                "SELECT id FROM cotizaciones WHERE invoice_id=? AND proveedor='AITECH'",
                (invoice_id,), fetch=True
            )
            cotizacion_id = rows2[0]["id"] if rows2 else None

        if cotizacion_id:
            df2 = df[["codigo","descripcion","precio_usd","cantidad_caja"]].copy()
            df2["cotizacion_id"] = cotizacion_id
            df_to_db(df2, "cotizacion_items")

        return len(df)


class ImportadorMariano(ImportadorBase):
    """
    Importa el archivo de Mariano (Repuestos al DD.MM.YYYY.xlsx).
    Formato real:
      - Hoja "Repuestos al ..." : headers en fila 4 (índice 3), datos desde fila 5
        Columnas clave: Código, Artículo, Demanda Total, Demanda Prom.(90 dias),
                        S.Actual, A Pedir, S.Optimo
        Filas 1-2: metadata del período (no se usan como headers)
      - Hoja "Lista de Precios": headers en fila 2, Código / Descripción / Lista 1 / P.Comp.

    Los datos se guardan en la tabla mariano_repuestos (NUNCA en optimizacion).
    Sirve como referencia de auditoría — no afecta cálculos del sistema.
    """

    NOMBRE = "mariano"
    FLEXXUS_MODULO = "Interno — archivo de Mariano"
    ARCHIVO_DESCARGA = "Repuestos al DD.MM.YYYY.xlsx"
    COLUMNAS_REQUERIDAS = []

    # ── Lectura ────────────────────────────────────────────────
    def _leer(self, uploaded_file) -> pd.DataFrame:
        """Lee todas las hojas del archivo. Retorna la hoja de Repuestos."""
        nombre = getattr(uploaded_file, "name", "")
        ext = nombre.split(".")[-1].lower()
        engine = "xlrd" if ext == "xls" else "openpyxl"

        self._hojas_raw = {}
        try:
            xls = pd.ExcelFile(uploaded_file, engine=engine)
            for hoja in xls.sheet_names:
                # Leer sin header para manejar el offset de filas
                self._hojas_raw[hoja] = xls.parse(hoja, header=None)
        except Exception:
            pass

        # Retorna la hoja de Repuestos (para que el pipeline base no falle)
        for key in self._hojas_raw:
            if "repuesto" in key.lower():
                return self._hojas_raw[key]
        if self._hojas_raw:
            return list(self._hojas_raw.values())[0]
        return pd.DataFrame()

    def _detectar_y_setear_headers(self, df):
        return df  # Manejamos headers manualmente en _transformar

    def _validar_columnas(self, df: pd.DataFrame) -> tuple:
        return True, ""

    def _limpiar(self, df: pd.DataFrame) -> pd.DataFrame:
        return df  # Sin limpieza en esta etapa

    # ── Transformación ─────────────────────────────────────────
    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        """Procesa la hoja de Repuestos (formato real con headers en fila 4)."""
        hoja_rep = self._get_hoja_repuestos()
        hoja_precios = self._get_hoja_precios()

        self._precios_df = self._procesar_precios(hoja_precios) if hoja_precios is not None else None
        return self._procesar_repuestos(hoja_rep) if hoja_rep is not None else pd.DataFrame()

    def _get_hoja_repuestos(self):
        for k, v in self._hojas_raw.items():
            if "repuesto" in k.lower():
                return v
        return None

    def _get_hoja_precios(self):
        for k, v in self._hojas_raw.items():
            if "lista" in k.lower() and "precio" in k.lower():
                return v
            if "precio" in k.lower():
                return v
        return None

    def _procesar_repuestos(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        El archivo real tiene:
          Filas 0-1: metadata del período
          Fila 2:    vacía
          Fila 3:    headers reales (Código, Artículo, Demanda Total, ...)
          Fila 4+:   datos
        """
        # Buscar la fila de headers buscando "Código" o "Artículo"
        header_row = 3  # default
        for i in range(min(8, len(df_raw))):
            fila_str = " ".join(str(v).upper() for v in df_raw.iloc[i].values if pd.notna(v))
            if "CÓDIGO" in fila_str or "CODIGO" in fila_str or "ARTÍCULO" in fila_str:
                header_row = i
                break

        df = df_raw.iloc[header_row:].copy()
        df.columns = [str(c).strip() if pd.notna(c) else f"_col{i}"
                      for i, c in enumerate(df.iloc[0])]
        df = df.iloc[1:].reset_index(drop=True)

        # Normalizar nombres de columna para búsqueda
        cols = {}
        for c in df.columns:
            cols[str(c).upper().replace("\n", " ").strip()] = c

        def find(*kws):
            for kw in kws:
                kw_u = kw.upper()
                for cu, co in cols.items():
                    if kw_u in cu:
                        return co
            return None

        cod_col  = find("CÓDIGO", "CODIGO") or df.columns[0]
        art_col  = find("ARTÍCULO", "ARTICULO")
        dem_tot  = find("DEMANDA TOTAL", "DEM TOTAL", "DEMANDA\nTOTAL")
        dem_prom = find("DEMANDA PROM", "DEM PROM", "PROM. (90", "PROM (90")
        s_actual = find("S. ACTUAL", "S.ACTUAL", "STOCK ACTUAL")
        a_pedir  = find("A PEDIR")
        s_optimo = find("S. OPTIMO", "S.OPTIMO", "ÓPTIMO", "OPTIMO")

        df_out = pd.DataFrame()
        df_out["codigo"]         = df[cod_col].astype(str).str.strip()
        df_out["descripcion"]    = df[art_col].astype(str).str.strip() if art_col else ""
        df_out["demanda_total"]  = pd.to_numeric(df[dem_tot],  errors="coerce").fillna(0) if dem_tot  else 0.0
        df_out["demanda_prom"]   = pd.to_numeric(df[dem_prom], errors="coerce").fillna(0) if dem_prom else 0.0
        df_out["stock_actual"]   = pd.to_numeric(df[s_actual], errors="coerce").fillna(0) if s_actual else 0.0
        df_out["a_pedir"]        = pd.to_numeric(df[a_pedir],  errors="coerce").fillna(0) if a_pedir  else 0.0
        df_out["stock_optimo"]   = pd.to_numeric(df[s_optimo], errors="coerce").fillna(0) if s_optimo else 0.0
        df_out["importado_en"]   = datetime.now().isoformat()

        # Filtrar filas sin código válido
        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[~df_out["codigo"].isin(["nan", "None", "NaN"])]
        df_out = df_out[df_out["codigo"].str.match(r'^[A-Za-z0-9]')]
        return df_out.reset_index(drop=True)

    def _procesar_precios(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Lista de Precios: headers en fila 2 (índice 1)."""
        # Buscar fila de headers
        header_row = 1
        for i in range(min(5, len(df_raw))):
            fila_str = " ".join(str(v).upper() for v in df_raw.iloc[i].values if pd.notna(v))
            if "CÓDIGO" in fila_str or "CODIGO" in fila_str:
                header_row = i
                break

        df = df_raw.iloc[header_row:].copy()
        df.columns = [str(c).strip() if pd.notna(c) else f"_col{i}"
                      for i, c in enumerate(df.iloc[0])]
        df = df.iloc[1:].reset_index(drop=True)

        cols = {str(c).upper(): c for c in df.columns}
        def find(*kws):
            for kw in kws:
                for cu, co in cols.items():
                    if kw.upper() in cu:
                        return co
            return None

        cod_col = find("CÓDIGO", "CODIGO") or df.columns[0]
        df_out = pd.DataFrame()
        df_out["codigo"]      = df[cod_col].astype(str).str.strip()
        df_out["lista_1"]     = pd.to_numeric(df[find("LISTA 1", "LIST 1")], errors="coerce").fillna(0) if find("LISTA 1", "LIST 1") else 0.0
        df_out["precio_comp"] = pd.to_numeric(df[find("P. COMP", "COSTO")],  errors="coerce").fillna(0) if find("P. COMP", "COSTO") else 0.0

        df_out = df_out[df_out["codigo"].str.len() > 1]
        df_out = df_out[~df_out["codigo"].isin(["nan", "None", "NaN"])]
        return df_out.reset_index(drop=True)

    # ── Guardado ───────────────────────────────────────────────
    def _guardar(self, df: pd.DataFrame) -> int:
        """
        Guarda en tabla mariano_repuestos (NO toca optimizacion).
        Borra los registros anteriores y reemplaza con el nuevo lote.
        """
        from database import execute_query, df_to_db
        total = 0

        if not df.empty:
            # Reemplazar todo (son datos de referencia, no histórico)
            execute_query("DELETE FROM mariano_repuestos", fetch=False)
            df_to_db(df, "mariano_repuestos")
            total += len(df)

        return total

    def _metadata(self, df: pd.DataFrame) -> dict:
        hojas = list(getattr(self, "_hojas_raw", {}).keys())
        total_a_pedir = int(df["a_pedir"].sum()) if "a_pedir" in df.columns else 0
        return {
            "hojas_encontradas": hojas,
            "total_articulos":   len(df),
            "total_a_pedir":     total_a_pedir,
            "fuente":            "Archivo de Mariano (referencia — no afecta cálculos del sistema)",
        }
