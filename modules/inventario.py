"""
ROKER NEXUS — Módulo Inventario & Quiebres
Detección automática de quiebres entre depósitos y anomalías.
"""
from datetime import datetime, date, timedelta
from typing import Optional
import pandas as pd

from database import query_to_df, execute_query
from utils.horarios import dias_sin_stock
from config import STOCK_QUIEBRE_UMBRAL, DEPOSITO_CENTRAL, DEPOSITO_PRINCIPAL_VENTA


def get_resumen_stock() -> dict:
    """Retorna un resumen ejecutivo del estado de stock."""
    df_all = query_to_df("""
        SELECT s.codigo, s.deposito, s.stock, s.stock_minimo, s.fecha
        FROM stock_snapshots s
        JOIN (
            SELECT codigo, deposito, MAX(fecha) as mf
            FROM stock_snapshots GROUP BY codigo, deposito
        ) latest ON s.codigo=latest.codigo AND s.deposito=latest.deposito AND s.fecha=latest.mf
        LEFT JOIN articulos a ON s.codigo=a.codigo
        WHERE COALESCE(a.en_lista_negra, 0) = 0
    """)

    if df_all.empty:
        return {}

    return {
        "total_articulos":  df_all["codigo"].nunique(),
        "sin_stock":        int((df_all["stock"] == 0).sum()),
        "bajo_minimo":      int((df_all["stock"] < df_all["stock_minimo"]).sum()),
        "depositos_activos": df_all["deposito"].nunique(),
        "fecha_dato":       df_all["fecha"].max() if not df_all.empty else "—",
    }


def detectar_quiebres(umbral: int = STOCK_QUIEBRE_UMBRAL,
                      deposito: Optional[str] = None) -> pd.DataFrame:
    """
    Detecta artículos con stock en cero o por debajo del umbral.
    Clasifica por severidad y enriquece con datos de otros depósitos.
    """
    dep_filter = f"AND s.deposito = '{deposito}'" if deposito else ""

    df = query_to_df(f"""
        SELECT
            s.codigo, s.deposito, s.rubro, s.stock, s.stock_minimo, s.stock_optimo, s.fecha,
            a.descripcion, a.marca, a.en_lista_negra,
            p.lista_1 as precio_l1, p.lista_4 as precio_ml
        FROM stock_snapshots s
        JOIN (
            SELECT codigo, deposito, MAX(fecha) as mf
            FROM stock_snapshots GROUP BY codigo, deposito
        ) latest ON s.codigo=latest.codigo AND s.deposito=latest.deposito AND s.fecha=latest.mf
        LEFT JOIN articulos a ON s.codigo=a.codigo
        LEFT JOIN precios p ON s.codigo=p.codigo
        WHERE s.stock <= {umbral}
          AND COALESCE(a.en_lista_negra, 0) = 0
          {dep_filter}
        ORDER BY s.stock ASC, a.marca
    """)

    if df.empty:
        return df

    # Clasificar severidad
    df["severidad"] = df["stock"].apply(
        lambda x: "alta" if x == 0 else ("media" if x <= 5 else "baja")
    )

    # Enriquecer: ver si San José tiene stock del mismo artículo
    if deposito and deposito != DEPOSITO_CENTRAL:
        df = _enriquecer_con_deposito_central(df)

    return df


def _enriquecer_con_deposito_central(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columna con el stock en San José para cada artículo."""
    codigos = df["codigo"].tolist()
    if not codigos:
        return df

    placeholders = ",".join("?" * len(codigos))
    df_central = query_to_df(f"""
        SELECT s.codigo, s.stock as stock_central
        FROM stock_snapshots s
        JOIN (
            SELECT codigo, MAX(fecha) as mf
            FROM stock_snapshots WHERE deposito='{DEPOSITO_CENTRAL}'
            GROUP BY codigo
        ) latest ON s.codigo=latest.codigo AND s.fecha=latest.mf
        WHERE s.deposito='{DEPOSITO_CENTRAL}' AND s.codigo IN ({placeholders})
    """, tuple(codigos))

    if not df_central.empty:
        df = df.merge(df_central, on="codigo", how="left")
        df["stock_central"] = df["stock_central"].fillna(0)
        df["accion_sugerida"] = df.apply(_sugerir_accion, axis=1)
    else:
        df["stock_central"] = 0
        df["accion_sugerida"] = "Investigar"

    return df


def _sugerir_accion(row) -> str:
    """Sugiere acción basada en stock local y central."""
    stock_central = row.get("stock_central", 0)
    if row["stock"] == 0:
        if stock_central > 0:
            return f"⚡ Pedir remito — San José tiene {int(stock_central)} uds"
        else:
            return "🛒 Incluir en próximo pedido"
    else:
        return "📉 Stock bajo — monitorear"


def detectar_quiebre_entre_depositos() -> pd.DataFrame:
    """
    Detecta situaciones donde Larrea está en cero pero San José tiene stock.
    Esto indica una falla de reposición.
    """
    df = query_to_df(f"""
        SELECT
            l.codigo,
            a.descripcion, a.marca,
            l.stock as stock_larrea,
            l.fecha as fecha_larrea,
            s.stock as stock_san_jose,
            s.fecha as fecha_san_jose
        FROM stock_snapshots l
        JOIN (
            SELECT codigo, MAX(fecha) as mf FROM stock_snapshots
            WHERE deposito='{DEPOSITO_PRINCIPAL_VENTA}' GROUP BY codigo
        ) ll ON l.codigo=ll.codigo AND l.fecha=ll.mf
        JOIN stock_snapshots s ON l.codigo=s.codigo
        JOIN (
            SELECT codigo, MAX(fecha) as mf FROM stock_snapshots
            WHERE deposito='{DEPOSITO_CENTRAL}' GROUP BY codigo
        ) sl ON s.codigo=sl.codigo AND s.fecha=sl.mf
        LEFT JOIN articulos a ON l.codigo=a.codigo
        WHERE l.deposito='{DEPOSITO_PRINCIPAL_VENTA}'
          AND s.deposito='{DEPOSITO_CENTRAL}'
          AND l.stock = 0
          AND s.stock > 0
          AND COALESCE(a.en_lista_negra, 0) = 0
        ORDER BY s.stock DESC
    """)

    if not df.empty:
        df["alerta"] = df.apply(
            lambda r: f"⚠️ {r['descripcion'] or r['codigo']} — "
                      f"Larrea sin stock, San José tiene {int(r['stock_san_jose'])} uds",
            axis=1
        )
    return df


def agregar_a_lista_negra(codigo: str, motivo: str = "") -> bool:
    """Agrega un artículo a la lista negra."""
    try:
        execute_query(
            """UPDATE articulos SET en_lista_negra=1, motivo_negra=?, fecha_negra=?
               WHERE codigo=?""",
            (motivo, date.today().isoformat(), codigo),
            fetch=False
        )
        return True
    except Exception:
        return False


def quitar_de_lista_negra(codigo: str) -> bool:
    """Quita un artículo de la lista negra."""
    try:
        execute_query(
            "UPDATE articulos SET en_lista_negra=0, motivo_negra=NULL WHERE codigo=?",
            (codigo,),
            fetch=False
        )
        return True
    except Exception:
        return False


def get_lista_negra() -> pd.DataFrame:
    """Retorna todos los artículos en lista negra."""
    return query_to_df("""
        SELECT codigo, descripcion, marca, motivo_negra, fecha_negra
        FROM articulos WHERE en_lista_negra=1
        ORDER BY fecha_negra DESC
    """)


def registrar_anomalia(codigo: str, deposito: str, tipo: str,
                       descripcion: str, severidad: str = "media") -> int:
    """Registra una anomalía detectada."""
    result = execute_query(
        """INSERT INTO anomalias (codigo, deposito, tipo, descripcion, severidad)
           VALUES (?, ?, ?, ?, ?)""",
        (codigo, deposito, tipo, descripcion, severidad),
        fetch=False
    )
    return result


def get_anomalias_abiertas() -> pd.DataFrame:
    """Retorna anomalías sin resolver."""
    return query_to_df("""
        SELECT id, codigo, deposito, tipo, descripcion, severidad, detectada_en
        FROM anomalias WHERE estado='abierta'
        ORDER BY
            CASE severidad WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END,
            detectada_en DESC
    """)
