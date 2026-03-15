"""
ROKER NEXUS — Módulo de Alertas de Stock

Detecta automáticamente al importar archivos de stock:
  - AUMENTO: stock de un SKU subió → puede significar que llegó mercadería
    sin aviso. El sistema avisa para que Roker pueda reclamar si no le avisaron.
  - CAIDA_MASIVA: muchos SKUs bajaron al mismo tiempo → probablemente una
    venta masiva o pedido. Se registra para auditoría.
  - QUIEBRE: SKU pasó de stock positivo a 0.

Notificaciones vía Telegram (si está configurado).
Se guarda en tabla stock_alertas para consulta posterior.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
import pandas as pd

from database import execute_query, df_to_db, query_to_df


# ─────────────────────────────────────────────────────────────────────────────
# UMBRALES (se pueden ajustar o sobreescribir desde config)
# ─────────────────────────────────────────────────────────────────────────────

UMBRAL_AUMENTO_UNIDADES   = 3      # mínimo de unidades que tiene que subir para generar alerta
UMBRAL_AUMENTO_PCT        = 20     # mínimo % de aumento sobre stock anterior
UMBRAL_CAIDA_SKUs         = 10     # si caen ≥ N SKUs en la misma importación → caída masiva
UMBRAL_CAIDA_PCT          = 30     # caída de al menos este % en cada SKU para contar en "masiva"


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL — llamar desde flexxus_stock.py después de guardar
# ─────────────────────────────────────────────────────────────────────────────

def analizar_y_alertar(df_nuevo: pd.DataFrame, deposito: str) -> dict:
    """
    Compara el nuevo snapshot de stock contra el snapshot anterior del mismo
    depósito y genera alertas.

    Args:
        df_nuevo  : DataFrame con columnas [codigo, descripcion, stock, deposito]
                    que ACABA de importarse (ya guardado en stock_snapshots).
        deposito  : Nombre del depósito (ej. 'SAN_JOSE', 'LARREA').

    Returns:
        dict con conteos: {"aumentos": int, "quiebres": int, "caida_masiva": bool,
                           "total_alertas": int}
    """
    _ensure_table()

    # ── Obtener snapshot anterior (el más reciente antes de hoy) ──────────────
    hoy = datetime.now().date().isoformat()
    df_ant = _obtener_snapshot_anterior(deposito, hoy)

    if df_ant.empty:
        # Sin historial previo → no hay con qué comparar
        return {"aumentos": 0, "quiebres": 0, "caida_masiva": False, "total_alertas": 0}

    # ── Merge por código ──────────────────────────────────────────────────────
    df_cmp = df_nuevo[["codigo","descripcion","stock"]].copy()
    df_cmp.columns = ["codigo","descripcion","stock_nuevo"]

    df_ant_s = df_ant[["codigo","stock"]].copy()
    df_ant_s.columns = ["codigo","stock_anterior"]

    df = df_cmp.merge(df_ant_s, on="codigo", how="left")
    df["stock_anterior"] = df["stock_anterior"].fillna(0)
    df["diferencia"]     = df["stock_nuevo"] - df["stock_anterior"]

    alertas = []

    # ── 1. AUMENTOS DE STOCK ──────────────────────────────────────────────────
    aumentos = df[
        (df["diferencia"] >= UMBRAL_AUMENTO_UNIDADES) &
        (
            (df["stock_anterior"] == 0) |
            (df["diferencia"] / df["stock_anterior"].replace(0, 1) * 100 >= UMBRAL_AUMENTO_PCT)
        )
    ].copy()

    for _, row in aumentos.iterrows():
        sev = "warning" if row["stock_anterior"] == 0 else "info"
        alertas.append({
            "codigo":          row["codigo"],
            "descripcion":     row["descripcion"] or "",
            "deposito":        deposito,
            "stock_anterior":  float(row["stock_anterior"]),
            "stock_nuevo":     float(row["stock_nuevo"]),
            "diferencia":      float(row["diferencia"]),
            "tipo_alerta":     "AUMENTO",
            "severidad":       sev,
            "visto":           0,
            "fecha":           datetime.now().isoformat(),
        })

    # ── 2. QUIEBRES (pasó a 0) ────────────────────────────────────────────────
    quiebres = df[
        (df["stock_anterior"] > 0) &
        (df["stock_nuevo"] == 0)
    ].copy()

    for _, row in quiebres.iterrows():
        alertas.append({
            "codigo":          row["codigo"],
            "descripcion":     row["descripcion"] or "",
            "deposito":        deposito,
            "stock_anterior":  float(row["stock_anterior"]),
            "stock_nuevo":     0.0,
            "diferencia":      -float(row["stock_anterior"]),
            "tipo_alerta":     "QUIEBRE",
            "severidad":       "error",
            "visto":           0,
            "fecha":           datetime.now().isoformat(),
        })

    # ── 3. CAÍDA MASIVA ───────────────────────────────────────────────────────
    caidas_significativas = df[
        (df["diferencia"] < 0) &
        (df["stock_anterior"] > 0) &
        (-df["diferencia"] / df["stock_anterior"] * 100 >= UMBRAL_CAIDA_PCT)
    ]
    caida_masiva = len(caidas_significativas) >= UMBRAL_CAIDA_SKUs

    if caida_masiva:
        alertas.append({
            "codigo":          "MASIVO",
            "descripcion":     f"Caída masiva detectada: {len(caidas_significativas)} SKUs bajaron ≥{UMBRAL_CAIDA_PCT}% en {deposito}",
            "deposito":        deposito,
            "stock_anterior":  0.0,
            "stock_nuevo":     0.0,
            "diferencia":      float(-len(caidas_significativas)),
            "tipo_alerta":     "CAIDA_MASIVA",
            "severidad":       "warning",
            "visto":           0,
            "fecha":           datetime.now().isoformat(),
        })

    # ── Guardar alertas en DB ─────────────────────────────────────────────────
    if alertas:
        df_alertas = pd.DataFrame(alertas)
        df_to_db(df_alertas, "stock_alertas")

    # ── Notificar por Telegram ────────────────────────────────────────────────
    if alertas:
        _notificar(alertas, deposito)

    return {
        "aumentos":      len(aumentos),
        "quiebres":      len(quiebres),
        "caida_masiva":  caida_masiva,
        "total_alertas": len(alertas),
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_table():
    """Crea la tabla si no existe (por si la migración no corrió todavía)."""
    execute_query("""CREATE TABLE IF NOT EXISTS stock_alertas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL,
        descripcion TEXT,
        deposito TEXT,
        stock_anterior REAL DEFAULT 0,
        stock_nuevo REAL DEFAULT 0,
        diferencia REAL DEFAULT 0,
        tipo_alerta TEXT NOT NULL,
        severidad TEXT DEFAULT 'info',
        visto INTEGER DEFAULT 0,
        fecha TEXT DEFAULT (datetime('now'))
    )""", fetch=False)


def _obtener_snapshot_anterior(deposito: str, hoy: str) -> pd.DataFrame:
    """Obtiene el snapshot más reciente anterior a hoy para un depósito."""
    try:
        # Buscar la fecha del último snapshot ANTES de hoy
        rows = execute_query(
            "SELECT MAX(fecha) as ultima FROM stock_snapshots WHERE deposito=? AND fecha<?",
            (deposito, hoy), fetch=True
        )
        if not rows or not rows[0]["ultima"]:
            return pd.DataFrame()

        ultima = rows[0]["ultima"]
        return query_to_df(
            "SELECT codigo, stock FROM stock_snapshots WHERE deposito=? AND fecha=?",
            params=(deposito, ultima)
        )
    except Exception:
        return pd.DataFrame()


def _notificar(alertas: list, deposito: str):
    """Envía resumen de alertas por Telegram."""
    try:
        from utils.helpers import notificar_telegram

        aumentos   = [a for a in alertas if a["tipo_alerta"] == "AUMENTO"]
        quiebres   = [a for a in alertas if a["tipo_alerta"] == "QUIEBRE"]
        masiva     = [a for a in alertas if a["tipo_alerta"] == "CAIDA_MASIVA"]

        lineas = [f"📦 *Actualización de stock — {deposito}*\n"]

        if aumentos:
            lineas.append(f"📈 *{len(aumentos)} artículo(s) subieron de stock* (verificá si te avisaron la llegada):")
            for a in aumentos[:5]:
                lineas.append(
                    f"  • `{a['codigo']}` {str(a['descripcion'])[:30]}\n"
                    f"    {int(a['stock_anterior'])} → {int(a['stock_nuevo'])} "
                    f"(+{int(a['diferencia'])} uds.)"
                )
            if len(aumentos) > 5:
                lineas.append(f"  _(y {len(aumentos)-5} más)_")

        if masiva:
            lineas.append(f"\n⚠️ *Caída masiva detectada* — revisá si hubo un pedido o compra no reportada.")
            for m in masiva:
                lineas.append(f"  {m['descripcion']}")

        if quiebres:
            lineas.append(f"\n🔴 *{len(quiebres)} artículo(s) llegaron a 0*")
            for q in quiebres[:3]:
                lineas.append(f"  • `{q['codigo']}` {str(q['descripcion'])[:30]}")
            if len(quiebres) > 3:
                lineas.append(f"  _(y {len(quiebres)-3} más)_")

        if len(lineas) > 1:
            notificar_telegram("\n".join(lineas))
    except Exception:
        pass  # Telegram es opcional


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES PARA LA UI
# ─────────────────────────────────────────────────────────────────────────────

def get_alertas_sin_ver(limit: int = 50) -> pd.DataFrame:
    """Retorna alertas no vistas para mostrar en el dashboard."""
    try:
        _ensure_table()
        return query_to_df(
            "SELECT * FROM stock_alertas WHERE visto=0 ORDER BY fecha DESC LIMIT ?",
            params=(limit,)
        )
    except Exception:
        return pd.DataFrame()


def get_todas_alertas(dias: int = 30, limit: int = 200) -> pd.DataFrame:
    """Retorna alertas de los últimos N días."""
    try:
        _ensure_table()
        return query_to_df(
            """SELECT * FROM stock_alertas
               WHERE fecha >= datetime('now', ?)
               ORDER BY fecha DESC LIMIT ?""",
            params=(f"-{dias} days", limit)
        )
    except Exception:
        return pd.DataFrame()


def marcar_vistas(ids: list):
    """Marca alertas como vistas por sus IDs."""
    if not ids:
        return
    try:
        _ensure_table()
        for aid in ids:
            execute_query("UPDATE stock_alertas SET visto=1 WHERE id=?", (aid,), fetch=False)
    except Exception:
        pass


def count_alertas_sin_ver() -> int:
    """Cuenta alertas pendientes de ver. Útil para badge en la nav."""
    try:
        _ensure_table()
        rows = execute_query(
            "SELECT COUNT(*) as n FROM stock_alertas WHERE visto=0", fetch=True
        )
        return int(rows[0]["n"]) if rows else 0
    except Exception:
        return 0
