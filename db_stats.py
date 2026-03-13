"""
ROKER NEXUS — Database helpers adicionales
Función get_resumen_stats para el dashboard.
"""


def get_resumen_stats() -> dict:
    """Retorna estadísticas resumidas para el dashboard."""
    try:
        from database import query_to_df, get_ultima_importacion
        import sqlite3

        conn = sqlite3.connect("roker_nexus.db")

        # Total artículos únicos con stock
        try:
            cur = conn.execute("SELECT COUNT(DISTINCT codigo) FROM stock_snapshots")
            total = cur.fetchone()[0] or 0
        except Exception:
            total = 0

        # Sin stock
        try:
            cur = conn.execute("""
                SELECT COUNT(*) FROM stock_snapshots s
                JOIN (
                    SELECT codigo, deposito, MAX(fecha) as mf
                    FROM stock_snapshots GROUP BY codigo, deposito
                ) lx ON s.codigo=lx.codigo AND s.deposito=lx.deposito AND s.fecha=lx.mf
                WHERE s.stock = 0
            """)
            sin_stock = cur.fetchone()[0] or 0
        except Exception:
            sin_stock = 0

        # Bajo mínimo
        try:
            cur = conn.execute("""
                SELECT COUNT(*) FROM stock_snapshots s
                JOIN (
                    SELECT codigo, deposito, MAX(fecha) as mf
                    FROM stock_snapshots GROUP BY codigo, deposito
                ) lx ON s.codigo=lx.codigo AND s.deposito=lx.deposito AND s.fecha=lx.mf
                WHERE s.stock > 0 AND s.stock < s.stock_minimo AND s.stock_minimo > 0
            """)
            bajo_min = cur.fetchone()[0] or 0
        except Exception:
            bajo_min = 0

        # Última importación
        try:
            cur = conn.execute(
                "SELECT importado_en FROM importaciones_log ORDER BY importado_en DESC LIMIT 1"
            )
            row = cur.fetchone()
            ultima = row[0][:16] if row else "—"
        except Exception:
            ultima = "—"

        conn.close()
        return {
            "total_articulos":   total,
            "sin_stock":         sin_stock,
            "bajo_minimo":       bajo_min,
            "depositos_activos": 3,
            "ultima_importacion": ultima,
        }
    except Exception:
        return {}
