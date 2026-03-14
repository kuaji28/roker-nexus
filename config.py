"""
ROKER NEXUS — Configuración Central
Todos los parámetros del sistema en un solo lugar.
"""
import os
from datetime import time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# ── Empresa ─────────────────────────────────────────────────
EMPRESA_NOMBRE = os.getenv("EMPRESA_NOMBRE", "El Celu")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires"))

# ── Helper para leer secrets ────────────────────────────────
def _get_secret(key: str, default: str = "") -> str:
    """Lee de st.secrets (Streamlit Cloud) o de variables de entorno."""
    # 1. Variables de entorno (Railway, local)
    env_val = os.getenv(key, "")
    if env_val:
        return env_val
    # 2. st.secrets (Streamlit Cloud)
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    return default

# ── APIs ────────────────────────────────────────────────────
SUPABASE_URL      = _get_secret("SUPABASE_URL")
SUPABASE_KEY      = _get_secret("SUPABASE_KEY")
ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
GEMINI_API_KEY    = _get_secret("GEMINI_API_KEY")
TELEGRAM_TOKEN    = _get_secret("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID  = _get_secret("TELEGRAM_CHAT_ID")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# ── Modelo IA ────────────────────────────────────────────────
MODO_IA = os.getenv("MODO_IA", "claude")          # claude | gemini | ambos
MODELO_CLAUDE = "claude-sonnet-4-6"
MODELO_GEMINI = "gemini-1.5-pro"

# ── Moneda ───────────────────────────────────────────────────
MONEDA_USD_ARS = float(os.getenv("MONEDA_USD_ARS", "1200"))

# ── Depósitos ────────────────────────────────────────────────
DEPOSITOS = {
    "SAN_JOSE": "San José",
    "LARREA":   "Larrea Nuevo",
    "ES_LOCAL": "ES Local",
}
DEPOSITO_CENTRAL = "SAN_JOSE"
DEPOSITO_PRINCIPAL_VENTA = "LARREA"

# ── Horarios de operación ────────────────────────────────────
HORARIO_SEMANA = {
    "apertura": time(8, 30),
    "cierre":   time(18, 30),
    "dias":     [0, 1, 2, 3, 4],   # Lun–Vie (0=Lunes)
}
HORARIO_SABADO = {
    "apertura": time(9, 0),
    "cierre":   time(13, 0),
    "dias":     [5],                # Sáb
}
# Feriados Argentina 2026 (actualizables)
FERIADOS_2026 = {
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-03-24",
    "2026-04-02", "2026-04-03", "2026-04-05", "2026-05-01",
    "2026-05-25", "2026-06-15", "2026-06-20", "2026-07-09",
    "2026-08-17", "2026-10-12", "2026-11-20", "2026-12-08",
    "2026-12-25",
}

# ── Horarios sugeridos de actualización ──────────────────────
ACTUALIZACIONES_SUGERIDAS = [
    {"hora": "08:00", "tarea": "Stock por Depósito (3 archivos)",         "frecuencia": "Lun–Vie"},
    {"hora": "08:00", "tarea": "Optimización de Stock",                   "frecuencia": "Lunes"},
    {"hora": "13:00", "tarea": "Análisis automático de quiebres (bot)",   "frecuencia": "Lun–Vie"},
    {"hora": "18:30", "tarea": "Ventas por Artículo del día",             "frecuencia": "Lun–Vie"},
    {"hora": "08:45", "tarea": "Stock por Depósito",                      "frecuencia": "Sábado"},
    {"hora": "13:15", "tarea": "Ventas de la semana",                     "frecuencia": "Sábado"},
    {"hora": "08:00", "tarea": "Lista de Precios (si hay cambios)",       "frecuencia": "Lunes"},
]

# ── Lógica de stock / compras ────────────────────────────────
STOCK_QUIEBRE_UMBRAL = 10          # Unidades — por debajo = alerta
STOCK_DIAS_QUIEBRE_ALERTA = 3      # Días sin stock = anomalía
LOTES_COMPRA = ["Lote 1", "Lote 2", "Lote 3"]
TOPE_USD_DEFAULT = {
    "Lote 1": 5000,
    "Lote 2": 8000,
    "Lote 3": 12000,
}

# ── Coeficientes stock ────────────────────────────────────────
COEF_STOCK_MIN = 1.0
COEF_STOCK_OPT = 1.2
COEF_STOCK_MAX = 1.4
DIAS_DEMANDA_PROMEDIO = 30

# ── Listas de precios ─────────────────────────────────────────
LISTA_MAYORISTA   = "Lista 1"
LISTA_MERCADOLIBRE = "Lista 4"

# ── Nombres de archivos Flexxus (para detección automática) ──
FLEXXUS_ARCHIVOS = {
    "optimizacion":   "Optimizacin_de_Stock",      # typo intencional de Flexxus
    "lista_precios":  "Lista de Precios",
    "ventas":         "Planilla de Ventas por Marca Resumida",
    "compras":        "Planilla de Ventas por Marca",  # sin "Resumida" = compras
    "stock":          "Planilla_de_Stock",
    "remitos":        "Planilla Detallada de Remitos - Remitos Internos",
}

# ── Proveedores ───────────────────────────────────────────────
PROVEEDORES = {
    "AITECH": {
        "nombre": "AI-TECH",
        "tipo":   "mecanicos",
        "moneda": "USD",
    },
    "FR": {
        "nombre": "Proveedor FR",
        "tipo":   "con_marco",
        "moneda": "USD",
        "activo": False,   # pausado
    },
}

# ── Drive — subcarpetas ───────────────────────────────────────
DRIVE_SUBCARPETAS = {
    "flexxus":      "imports/flexxus",
    "proveedores":  "imports/proveedores",
    "mariano":      "imports/mariano",
    "exports":      "exports",
    "backups":      "backups",
}

# ── Debug ─────────────────────────────────────────────────────
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
