"""
ROKER NEXUS — Control de versiones
"""

APP_VERSION = "v2.5.0"
APP_BUILD   = "2026-03-14"

CHANGELOG = [
    {
        "version": "v2.5.0",
        "fecha": "2026-03-14",
        "cambios": [
            "🛒 Módulo MercadoLibre — comparador, editor masivo, MLA IDs, reporte",
            "🔍 Búsqueda ML por tienda FR (aitech) y Mecánico con fallback web",
            "⚓ Términos de búsqueda anclados por código",
            "📥 Importar MLA IDs desde Excel (FR y Mecánico separados)",
            "✏️ Editor masivo de precios con cálculo de margen neto en vivo",
            "📈 Reporte acumulativo de comparaciones exportable a Excel",
            "🔧 BUG: tabla 'configuracion' agregada al SCHEMA_SQL (no such table)",
            "🔧 BUG: 'no such table: articulos' en Lista Precios — path absoluto",
            "🔧 BUG: filtro proveedor FR/Mecánico en sugerencias corregido",
            "🔧 BUG: cotizaciones AI-TECH ahora guardan estado='pendiente'",
            "🔧 BUG: tab Tránsito ahora muestra cotizaciones correctamente",
            "🔧 BUG: archivos duplicados en raíz eliminados",
        ]
    },
    {
        "version": "v1.8.1",
        "fecha": "2026-03-14",
        "cambios": [
            "✈️ Módulo Cotizaciones/Tránsito completo",
            "📥 Importador Order List AI-TECH con fuzzy matching",
            "🤖 Fix Telegram: 4 callbacks sin handler corregidos",
            "🧭 Navegación: tabs Cotizaciones en barra principal",
        ]
    },
    {
        "version": "v1.7.1",
        "fecha": "2026-03-13",
        "cambios": [
            "🔍 Detector archivos Flexxus — Planilla de Stock corregido",
            "📦 Planilla de Stock — columnas corregidas (stock en col 7)",
            "🔒 INSERT OR IGNORE — UNIQUE constraint resuelto",
        ]
    },
]


def get_nota_deploy() -> str:
    v = CHANGELOG[0]
    cambios = "\n".join(f"  • {c}" for c in v["cambios"])
    return (
        f"🚀 *ROKER NEXUS actualizado*\n"
        f"*{v['version']}* · {v['fecha']}\n\n"
        f"*Cambios:*\n{cambios}\n\n"
        f"_Sistema operativo ✅_"
    )
