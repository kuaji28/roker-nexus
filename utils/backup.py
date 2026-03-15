"""
ROKER NEXUS — Sistema de Backup y Restore

Exporta todas las tablas de datos a un ZIP con CSVs.
Permite restaurar desde ese ZIP si se pierde la base de datos.

TABLAS INCLUIDAS EN BACKUP:
  - stock_snapshots     (stock histórico por depósito)
  - optimizacion        (parámetros de reposición)
  - articulos           (catálogo maestro)
  - precios             (listas de precios)
  - ventas              (historial de ventas)
  - compras_historial   (historial de compras)
  - cotizaciones        (pedidos/órdenes)
  - cotizacion_items    (items de cada orden)
  - pedidos_lotes       (lotes de pedido)
  - pedidos_items       (items de lote)
  - pedidos_transito    (en tránsito)
  - configuracion       (settings del sistema)
  - borrador_pedido     (borrador actual)
  - demanda_manual      (overrides de demanda)
  - stock_alertas       (alertas generadas)
  - ingresos_mercaderia (auditoría ingresos)
  - mariano_repuestos   (archivo de Mariano)
  - importaciones_log   (historial de importaciones)
"""

from __future__ import annotations
import io
import zipfile
from datetime import datetime

import pandas as pd

from database import query_to_df, df_to_db, execute_query


# Tablas en orden de restauración (respeta dependencias de FK)
TABLAS_BACKUP = [
    "configuracion",
    "articulos",
    "precios",
    "optimizacion",
    "ventas",
    "compras_historial",
    "stock_snapshots",
    "cotizaciones",
    "cotizacion_items",
    "pedidos_lotes",
    "pedidos_items",
    "pedidos_transito",
    "borrador_pedido",
    "demanda_manual",
    "stock_alertas",
    "ingresos_mercaderia",
    "mariano_repuestos",
    "importaciones_log",
]

# Tablas que se limpian antes de restaurar (para no duplicar)
TABLAS_LIMPIAR_AL_RESTAURAR = [
    "articulos", "precios", "optimizacion", "ventas",
    "compras_historial", "stock_snapshots",
    "cotizacion_items", "cotizaciones",
    "pedidos_items", "pedidos_lotes", "pedidos_transito",
    "borrador_pedido", "demanda_manual",
    "stock_alertas", "ingresos_mercaderia",
    "mariano_repuestos",
]

# Configuración: solo restaurar si el usuario lo pide explícitamente
TABLAS_SOLO_MERGE = ["configuracion"]  # no limpiar, hacer merge


# ─────────────────────────────────────────────────────────────────────────────
# EXPORTAR
# ─────────────────────────────────────────────────────────────────────────────

def exportar_backup() -> bytes:
    """
    Exporta todas las tablas a un archivo ZIP con un CSV por tabla.
    Retorna bytes del ZIP para descargar.
    """
    buf = io.BytesIO()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    stats = {}

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Metadata
        meta_lines = [
            f"ROKER NEXUS — Backup",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Versión: 2.1.0",
            "",
            "Tablas incluidas:",
        ]

        for tabla in TABLAS_BACKUP:
            try:
                df = query_to_df(f"SELECT * FROM {tabla}")
                n = len(df)
                stats[tabla] = n
                if n > 0:
                    csv_buf = io.StringIO()
                    df.to_csv(csv_buf, index=False, encoding="utf-8")
                    zf.writestr(f"{tabla}.csv", csv_buf.getvalue())
                    meta_lines.append(f"  {tabla}: {n} filas")
                else:
                    meta_lines.append(f"  {tabla}: vacía (no incluida)")
            except Exception as e:
                meta_lines.append(f"  {tabla}: ERROR — {e}")

        # Archivo de metadata
        zf.writestr("_metadata.txt", "\n".join(meta_lines))

    buf.seek(0)
    return buf.read()


def get_stats_backup() -> dict:
    """Retorna conteo de filas por tabla para mostrar en UI antes de descargar."""
    stats = {}
    for tabla in TABLAS_BACKUP:
        try:
            rows = execute_query(f"SELECT COUNT(*) as n FROM {tabla}", fetch=True)
            stats[tabla] = int(rows[0]["n"]) if rows else 0
        except Exception:
            stats[tabla] = -1  # tabla no existe
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# IMPORTAR / RESTAURAR
# ─────────────────────────────────────────────────────────────────────────────

def restaurar_backup(zip_bytes: bytes, tablas_seleccionadas: list = None) -> dict:
    """
    Restaura datos desde un ZIP de backup.

    Args:
        zip_bytes: Contenido del archivo ZIP descargado anteriormente.
        tablas_seleccionadas: Lista de tablas a restaurar (None = todas).

    Returns:
        dict con resultados por tabla: {"tabla": {"filas": int, "error": str}}
    """
    resultados = {}
    tablas_a_restaurar = tablas_seleccionadas or TABLAS_BACKUP

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        archivos_en_zip = {
            name.replace(".csv", ""): name
            for name in zf.namelist()
            if name.endswith(".csv") and not name.startswith("_")
        }

        for tabla in tablas_a_restaurar:
            if tabla not in archivos_en_zip:
                resultados[tabla] = {"filas": 0, "estado": "no_en_backup"}
                continue

            try:
                csv_content = zf.read(archivos_en_zip[tabla]).decode("utf-8")
                df = pd.read_csv(io.StringIO(csv_content))

                if df.empty:
                    resultados[tabla] = {"filas": 0, "estado": "vacia"}
                    continue

                # Limpiar columna id/serial para que la DB asigne IDs nuevos
                if tabla not in TABLAS_SOLO_MERGE:
                    # Limpiar tabla destino antes de insertar
                    if tabla in TABLAS_LIMPIAR_AL_RESTAURAR:
                        try:
                            execute_query(f"DELETE FROM {tabla}", fetch=False)
                        except Exception:
                            pass

                    # Remover columnas auto-generadas que no se deben insertar
                    for auto_col in ["id", "importado_en", "creado_en", "fecha_carga"]:
                        if auto_col in df.columns:
                            df = df.drop(columns=[auto_col])

                filas = df_to_db(df, tabla)
                resultados[tabla] = {"filas": filas, "estado": "ok"}

            except Exception as e:
                resultados[tabla] = {"filas": 0, "estado": "error", "error": str(e)[:100]}

    return resultados


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-BACKUP POST-IMPORTACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def guardar_autobackup_session():
    """
    Guarda en st.session_state el ZIP de backup del estado actual.
    Se llama automáticamente después de cada importación exitosa.
    Solo se ejecuta si no hay DATABASE_URL (SQLite mode).
    """
    try:
        from database import USE_POSTGRES
        if USE_POSTGRES:
            return  # En Supabase no es necesario — datos ya persisten

        import streamlit as st
        zip_bytes = exportar_backup()
        st.session_state["_autobackup_zip"]  = zip_bytes
        st.session_state["_autobackup_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
