"""
ROKER NEXUS — Control de versiones
Cada entrada = un deploy con cambios reales.
"""

APP_VERSION = "v1.6.0"
APP_BUILD   = "2026-03-13"

CHANGELOG = [
    {
        "version": "v1.6.0",
        "fecha": "2026-03-13",
        "cambios": [
            "🔍 Detector archivos Flexxus — Planilla de Stock corregido",
            "🤖 Fix Claude IA — ahora lee API Key de Streamlit Secrets",
            "📦 Planilla de Stock — columnas corregidas (stock en col 7)",
            "🏪 Stock con 1.931 artículos se carga correctamente",
            "🔌 Nueva página Sistema — estado de todas las conexiones",
            "⚙️ Configuración editable — USD/ARS, RMB, márgenes, comisiones ML",
            "🔒 INSERT OR IGNORE — UNIQUE constraint resuelto definitivamente",
            "🗄️ Dashboard ahora muestra datos de Optimización de Stock",
            "📦 Importador Stock por Depósito — formato real Flexxus",
            "⚙️ Sistema de configuración: márgenes, RMB, comisiones ML",
            "🔧 query_to_df corregido — datos persisten entre deploys",
            "🔕 Notificación Telegram solo cuando cambia versión",
            "📊 Página Precios — error DatabaseError corregido",
            "📥 Ventas y Compras — error UNIQUE corregido",
        ]
    },
    {
        "version": "v1.6.0",
        "fecha": "2026-03-13",
        "cambios": [
            "🎨 Diseño One UI 8 completo — paleta Samsung auténtica",
            "🤖 Bot interactivo con menú de botones",
            "🔍 /stock y /precio búsqueda por nombre o código",
            "📊 /quiebres con selector de depósito y Top",
            "⛔ /negra muestra nombre completo antes de confirmar",
            "🚚 /pedido — rastrear tránsito con archivo y renglón",
            "✅ Notificaciones de deploy por Telegram",
            "⚙️ AutoPush — sube cambios solo cada 30 segundos",
        ]
    },
    {
        "version": "v1.6.0",
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
    v = CHANGELOG[0]
    cambios = "\n".join(f"  • {c}" for c in v["cambios"])
    return (
        f"🚀 *ROKER NEXUS actualizado*\n"
        f"*{v['version']}* · {v['fecha']}\n\n"
        f"*Cambios:*\n{cambios}\n\n"
        f"_Sistema operativo ✅_"
    )
