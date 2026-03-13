"""
ROKER NEXUS — Importador Base
Clase base con lógica compartida por todos los importadores.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd
import streamlit as st

from database import log_importacion


@dataclass
class ResultadoImportacion:
    tipo: str
    archivo: str
    filas_ok: int = 0
    filas_error: int = 0
    estado: str = "ok"
    mensaje: str = ""
    df: Optional[pd.DataFrame] = None
    metadata: dict = field(default_factory=dict)

    @property
    def exitoso(self) -> bool:
        return self.estado == "ok" and self.filas_ok > 0

    def __str__(self):
        if self.exitoso:
            return f"✅ {self.tipo}: {self.filas_ok} registros importados"
        return f"❌ {self.tipo}: {self.mensaje}"


class ImportadorBase(ABC):
    """
    Clase base para todos los importadores de archivos.
    Cada importador sabe:
    - Qué columnas espera
    - Cómo limpiar y validar los datos
    - Cómo guardar en la base de datos
    """

    NOMBRE = "Importador"
    FLEXXUS_MODULO = ""
    ARCHIVO_DESCARGA = ""
    COLUMNAS_REQUERIDAS: list = []

    def importar(self, uploaded_file) -> ResultadoImportacion:
        """Pipeline completo de importación."""
        nombre = getattr(uploaded_file, "name", "archivo")
        resultado = ResultadoImportacion(tipo=self.NOMBRE, archivo=nombre)

        try:
            # 1. Leer
            df_raw = self._leer(uploaded_file)
            if df_raw.empty:
                resultado.estado = "error"
                resultado.mensaje = "Archivo vacío o no se pudo leer"
                return resultado

            # 2. Detectar headers reales
            df = self._detectar_y_setear_headers(df_raw)

            # 3. Validar columnas
            ok, msg = self._validar_columnas(df)
            if not ok:
                resultado.estado = "error"
                resultado.mensaje = msg
                return resultado

            # 4. Limpiar
            df = self._limpiar(df)

            # 5. Transformar
            df_final = self._transformar(df, uploaded_file)

            # 6. Guardar
            filas = self._guardar(df_final)
            resultado.filas_ok = filas
            resultado.df = df_final

            # 7. Metadata
            resultado.metadata = self._metadata(df_final)

            # 8. Log
            log_importacion(self.NOMBRE, nombre, filas)

        except Exception as e:
            resultado.estado = "error"
            resultado.mensaje = str(e)
            log_importacion(self.NOMBRE, nombre, 0, 1, "error", str(e))

        return resultado

    def _leer(self, uploaded_file) -> pd.DataFrame:
        from utils.helpers import leer_excel
        return leer_excel(uploaded_file)

    def _detectar_y_setear_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        from utils.helpers import encontrar_fila_header
        if self.COLUMNAS_REQUERIDAS:
            fila = encontrar_fila_header(df, self.COLUMNAS_REQUERIDAS)
            if fila > 0:
                df.columns = df.iloc[fila]
                df = df.iloc[fila + 1:].reset_index(drop=True)
        # Normalizar nombres de columna
        df.columns = [str(c).strip() for c in df.columns]
        # CRÍTICO: deduplicar columnas SIEMPRE (Flexxus repite nombres)
        seen = {}
        new_cols = []
        for c in df.columns:
            if c in seen:
                seen[c] += 1
                new_cols.append(f"{c}_{seen[c]}")
            else:
                seen[c] = 0
                new_cols.append(c)
        df.columns = new_cols
        return df

    def _validar_columnas(self, df: pd.DataFrame) -> tuple:
        cols_upper = [c.upper() for c in df.columns]
        faltantes = []
        for req in self.COLUMNAS_REQUERIDAS:
            if not any(req.upper() in c for c in cols_upper):
                faltantes.append(req)
        if faltantes:
            return False, f"Columnas no encontradas: {', '.join(faltantes)}"
        return True, ""

    def _limpiar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpieza básica — override para personalizar."""
        df = df.copy()
        # Quitar filas completamente vacías
        df = df.dropna(how="all")
        # Convertir columnas de texto a string de forma defensiva
        for col in df.select_dtypes(include="object").columns:
            serie = df[col]
            # Si por columnas duplicadas devuelve DataFrame, tomar primera columna
            if isinstance(serie, pd.DataFrame):
                serie = serie.iloc[:, 0]
                df[col] = serie
            df[col] = serie.astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "": None})
        return df

    @abstractmethod
    def _transformar(self, df: pd.DataFrame, uploaded_file=None) -> pd.DataFrame:
        """Transforma el DataFrame al schema de la BD."""
        pass

    @abstractmethod
    def _guardar(self, df: pd.DataFrame) -> int:
        """Guarda en la base de datos. Retorna cantidad de filas."""
        pass

    def _metadata(self, df: pd.DataFrame) -> dict:
        """Metadata opcional para mostrar al usuario."""
        return {"total_filas": len(df)}

    def instrucciones_flexxus(self) -> str:
        """Instrucciones para exportar este archivo desde Flexxus."""
        return f"Módulo: **{self.FLEXXUS_MODULO}** → Archivo: `{self.ARCHIVO_DESCARGA}`"
