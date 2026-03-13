"""
ROKER NEXUS — Control de versiones
Cada entrada = un deploy. El bot notifica al arrancar.
"""

APP_VERSION = "v1.4.0"

CHANGELOG = [
    {
        "version": "v1.4.0",
        "fecha": "2026-03-13",
        "cambios": [
            "🎨 Diseño One UI 8 completo — paleta Samsung auténtica",
            "🔵 Botón sidebar azul fijo, siempre visible",
            "🔍 /stock y /precio: búsqueda por nombre o código",
            "📊 /quiebres: elegís depósito y Top 10/20/30/50",
            "⛔ /negra: muestra nombre completo antes de confirmar",
            "📋 /negra sin args: muestra lista negra actual",
            "🏷️ Versión visible en sidebar",
            "✅ Notificaciones de deploy por Telegram",
        ]
    },
    {
        "version": "v1.3.0",
        "fecha": "2026-03-13",
        "cambios": [
            "🤖 Bot Telegram 24/7 en Railway",
            "🔧 Fix SQL ambiguous column en Dashboard",
            "🔧 Fix importador Optimización de Stock",
            "🔧 Funciones lista negra en database",
        ]
    },
    {
        "version": "v1.0.0",
        "fecha": "2026-03-13",
        "cambios": [
            "🚀 Sistema Roker Nexus lanzado",
            "📊 Dashboard con métricas en tiempo real",
            "📥 Importador Flexxus multi-archivo",
            "💰 Gestión de precios y ML",
            "🛒 Gestión de compras y tránsito",
        ]
    },
]

def get_nota_deploy() -> str:
    """Genera el mensaje de Telegram para notificar un nuevo deploy."""
    v = CHANGELOG[0]
    cambios = "\n".join(f"  • {c}" for c in v["cambios"])
    return (
        f"🚀 *ROKER NEXUS actualizado*\n"
        f"*{v['version']}* · {v['fecha']}\n\n"
        f"*Novedades:*\n{cambios}\n\n"
        f"_Sistema operativo ✅_"
    )
