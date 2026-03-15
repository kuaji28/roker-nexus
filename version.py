"""ROKER NEXUS — Control de versiones"""
APP_VERSION = "v2.0.3"
APP_BUILD   = "2026-03-15"

CHANGELOG = [
    {
        "version": "v2.0.3",
        "fecha": "2026-03-15",
        "cambios": [
            "📊 Dashboard: Críticos y Urgentes ahora como tabla con multiselect bulk actions",
            "✈️ Cotizaciones: tab 'SKUs en Tránsito' con detalle por código + exportar CSV",
            "🧮 ML Calculadora: selector de producto desde DB (Lista 1 se autocompleta)",
            "🧮 ML Calculadora: comparación vs Lista 4 actual + detector comisión auto-completa",
            "🚀 Fix carga: importadores reemplazados con bulk insert — sin loops individuales",
            "🚀 Fix: _upsert_articulos en Lista Precios y Stock escribe a PostgreSQL correctamente",
        ]
    },
    {
        "version": "v2.0.2",
        "fecha": "2026-03-15",
        "cambios": [
            "🐛 Fix Dashboard: tránsito mostraba 0 (campo codigo_flexxus corregido)",
            "📊 Dashboard: default filtro cambiado a Mecánico",
            "📊 Dashboard: Top 30 y Top 50 agregados al selector",
            "🗄️ DB: Soporte PostgreSQL directo vía DATABASE_URL (Supabase)",
            "📦 requirements: psycopg2-binary para conexión Supabase",
        ]
    },
    {
        "version": "v2.0.0",
        "fecha": "2026-03-14",
        "cambios": [
            "📊 Sidebar global: Lead Time, Presupuestos L1/L2/L3, USD/ARS, RMB/USD",
            "🛒 Sidebar: Comisiones ML FR/MEC + Margen extra + Coeficientes Stock",
            "🧠 Sidebar: Selector IA Claude/Gemini/GPT con API Keys",
            "📊 Dashboard: Banner tránsito + 6 KPIs operativos + 4 KPIs financieros",
            "📊 Dashboard: Stock Real = stock + tránsito en tabla críticos",
            "🧮 ML: Calculadora paso a paso Lista1 → precio a publicar",
            "🧮 ML: Detector comisión implícita + precio psicológico",
            "🔍 ML: Motor búsqueda API + fallback web + caché 6hs",
            "📊 ML: Análisis competencia con estado verde/rojo vs precios nuestros",
            "✏️ Demanda Manual: override cuando ERP muestra 0 por quiebre",
            "👻 Ghost SKUs: módulos pedidos sin código ERP todavía",
            "🚫 Lista Negra: modos INVISIBLE/GRISADO/SOLO_COMPRAS",
            "🔧 Fix: plotly en requirements.txt",
            "🔧 Fix: use_container_width → width compatible con Streamlit 1.55",
        ]
    },
]

def get_nota_deploy() -> str:
    v = CHANGELOG[0]
    cambios = "\n".join(f"  • {c}" for c in v["cambios"][:5])
    return (
        f"🚀 *ROKER NEXUS actualizado*\n"
        f"*{v['version']}* · {v['fecha']}\n\n"
        f"*Cambios:*\n{cambios}\n\n"
        f"_Sistema operativo ✅_"
    )
