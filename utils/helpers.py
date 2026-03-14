"""
ROKER NEXUS — Helpers generales
Funciones de formato, detección de archivos, y utilidades comunes.
"""
import re
import os
from datetime import datetime
from typing import Optional
import pandas as pd
import streamlit as st

try:
    from config import FLEXXUS_ARCHIVOS, MONEDA_USD_ARS
except Exception:
    FLEXXUS_ARCHIVOS = []
    MONEDA_USD_ARS = 1420.0


# ── Formateo de valores ───────────────────────────────────────

def fmt_usd(v: float, decimales: int = 2) -> str:
    """Formatea un valor en USD."""
    if pd.isna(v):
        return "—"
    return f"USD {v:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_ars(v: float) -> str:
    """Formatea un valor en ARS."""
    if pd.isna(v):
        return "—"
    return f"$ {v:,.0f}".replace(",", ".")


def fmt_num(v: float, decimales: int = 0) -> str:
    """Formatea un número con separador de miles."""
    if pd.isna(v):
        return "—"
    return f"{v:,.{decimales}f}".replace(",", ".")


def usd_a_ars(usd: float, tasa: Optional[float] = None) -> float:
    """Convierte USD a ARS."""
    t = tasa or MONEDA_USD_ARS
    return usd * t


def ars_a_usd(ars: float, tasa: Optional[float] = None) -> float:
    """Convierte ARS a USD."""
    t = tasa or MONEDA_USD_ARS
    return ars / t if t else 0


# ── Detección de tipo de archivo Flexxus ─────────────────────

def detectar_tipo_flexxus(nombre_archivo: str) -> Optional[str]:
    """
    Detecta qué tipo de archivo Flexxus es por el nombre.
    Retorna la clave del tipo o None si no reconoce.
    """
    nombre = nombre_archivo.strip()
    nombre_up = nombre.upper()
    # Normalizar: reemplazar espacios y guiones por nada para comparar
    nombre_norm = nombre_up.replace(" ", "").replace("_", "").replace("-", "")

    if "REMITOS" in nombre_up and "INTERNOS" in nombre_up:
        return "remitos"
    if "RESUMIDA" in nombre_up:
        return "ventas"
    if "VENTASPORMARCA" in nombre_norm:
        return "compras"
    if "LISTADEPRECIOS" in nombre_norm:
        return "lista_precios"
    if "OPTIMIZACIN" in nombre_norm or "OPTIMIZACION" in nombre_norm:
        return "optimizacion"
    # Stock: "Planilla de Stock" o "Planilla_de_Stock" — NO es ventas
    # Stock: nombre largo "Planilla de Stock..." o nombre corto "Stock san jose.XLS"
    if "PLANILLA" in nombre_norm and "STOCK" in nombre_norm and "VENTAS" not in nombre_norm:
        return "stock"
    if nombre_norm.startswith("STOCK") or nombre_up.startswith("STOCK ") or nombre_up.startswith("STOCK_"):
        return "stock"

    # Archivos de proveedores
    if "cotizacion" in nombre.lower() or "ai-tech" in nombre.lower() or "ai_tech" in nombre.lower():
        return "cotizacion_aitech"
    if "optimizacion" in nombre.lower() and "stock" not in nombre.lower():
        return "mariano"

    return None


def detectar_deposito_del_nombre(nombre: str) -> Optional[str]:
    """Detecta el depósito por el nombre del archivo de stock."""
    nombre_up = nombre.upper()
    if "SAN" in nombre_up and "JOSE" in nombre_up:
        return "SAN_JOSE"
    if "LARREA" in nombre_up:
        return "LARREA"
    if "LOCAL" in nombre_up or "ES_LOCAL" in nombre_up:
        return "ES_LOCAL"
    return None


# ── Lectura inteligente de XLS/XLSX ──────────────────────────

def leer_excel(uploaded_file, header_row: int = 0) -> pd.DataFrame:
    """
    Lee un archivo Excel/XLS subido via Streamlit.
    Maneja formatos .XLS (antiguo) y .XLSX automáticamente.
    """
    nombre = uploaded_file.name if hasattr(uploaded_file, "name") else "archivo"
    ext = os.path.splitext(nombre)[1].lower()

    try:
        if ext == ".xls":
            df = pd.read_excel(uploaded_file, engine="xlrd", header=header_row)
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl", header=header_row)

        # Limpiar columnas vacías y filas completamente vacías
        df = df.dropna(how="all", axis=1)
        df = df.dropna(how="all", axis=0)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al leer {nombre}: {e}")
        return pd.DataFrame()


def encontrar_fila_header(df: pd.DataFrame, palabras_clave: list) -> int:
    """
    Busca la fila que contiene los headers reales (Flexxus a veces tiene
    filas de título antes de los datos).
    """
    for i, row in df.head(15).iterrows():
        row_str = " ".join(str(v).upper() for v in row.values)
        hits = sum(1 for p in palabras_clave if p.upper() in row_str)
        if hits >= len(palabras_clave) // 2 + 1:
            return i
    return 0


# ── Colores para estados ──────────────────────────────────────

def color_stock(stock: float, minimo: float = 0) -> str:
    """Retorna un emoji/color según el nivel de stock."""
    if stock == 0:
        return "🔴"
    if stock <= 10 or (minimo > 0 and stock < minimo):
        return "🟡"
    return "🟢"


def severidad_badge(sev: str) -> str:
    """HTML badge para severidad."""
    colores = {
        "alta":  ("#f85149", "#fff1f1"),
        "media": ("#d29922", "#fff8e1"),
        "baja":  ("#3fb950", "#e8f5e9"),
    }
    fg, bg = colores.get(sev.lower(), ("#888", "#eee"))
    return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:500">{sev.upper()}</span>'


# ── Estado de APIs ────────────────────────────────────────────

def check_apis() -> dict:
    """Verifica qué APIs están configuradas."""
    from config import ANTHROPIC_API_KEY, GEMINI_API_KEY, TELEGRAM_TOKEN, SUPABASE_URL
    return {
        "claude":    bool(ANTHROPIC_API_KEY),
        "gemini":    bool(GEMINI_API_KEY),
        "telegram":  bool(TELEGRAM_TOKEN),
        "supabase":  bool(SUPABASE_URL),
    }
