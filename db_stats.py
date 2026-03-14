"""
ROKER NEXUS — Database helpers adicionales
Función get_resumen_stats - delega a database.py para consistencia.
"""


def get_resumen_stats() -> dict:
    """Retorna estadísticas resumidas para el dashboard."""
    try:
        from database import get_resumen_stats as _grs
        return _grs()
    except Exception:
        return {
            "total_articulos": 0,
            "sin_stock": 0,
            "bajo_minimo": 0,
            "depositos_activos": 0,
            "ultima_importacion": "—",
        }
