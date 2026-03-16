"""ROKER NEXUS — Control de versiones"""
APP_VERSION = "v2.3.0"
APP_BUILD   = "2026-03-15"

CHANGELOG = [
    {
        "version": "v2.3.0",
        "fecha": "2026-03-15",
        "cambios": [
            "🤖 IA contextual en 9 páginas: Dashboard, Alertas, Inventario, Auditoría, Cotizaciones, Precios, ML, Borrador, Defensa",
            "📖 Importar: nuevo tab Guía de archivos con renombrador rápido y pasos paso a paso",
            "📥 Importar: selector manual de tipo cuando el archivo no es reconocido automáticamente",
            "🧠 SYSTEM_PROMPT actualizado con contexto completo del negocio (Roker, El Celu, situación actual)",
            "🐛 Fix: código muerto en _procesar_archivo (spinner después del return) corregido",
        ]
    },
    {
        "version": "v2.2.0",
        "fecha": "2026-03-15",
        "cambios": [
            "🗂️ Navegación lateral agrupada: 5 grupos funcionales (Operaciones, Análisis, Precios & ML, Inventario, Sistema)",
            "✏️ Demanda Manual integrada como tab en Inventario",
            "🔗 Alias de Códigos: nuevo gestor de apodos → mejora fuzzy matching en Borrador",
            "👻 Ghost SKUs integrado como tab en Borrador de Pedido",
            "🛡️ Defensa de Presupuesto: nuevo módulo estratégico antes/después dic 2025",
            "🧹 Calidad de Datos: filtro 'Últimos 3 meses' activado por defecto",
        ]
    },
    {
        "version": "v2.0.3",
        "fecha": "2026-03-15",
        "cambios": [
            "📊 Dashboard: Críticos y Urgentes ahora como tabla con multiselect bulk actions",
            "✈️ Cotizaciones: tab 'SKUs en Tránsito' con detalle por código + exportar CSV",
            "🧮 ML Calculadora: selector de producto desde DB (Lista 1 se autocompleta)",
            "🧮 ML Calculadora: comparación vs Lista 4 actual + detector comisión auto-completa",
            "🚀 Fix carga: importadores reemplazados con bulk insert — sin loops individuales",
        ]
    },
    {
        "version": "v2.0.2",
        "fecha": "2026-03-15",
        "cambios": [
            "🐛 Fix Dashboard: tránsito mostraba 0 (campo codigo_flexxus corregido)",
            "📊 Dashboard: default filtro cambiado a Mecánico",
            "🗄️ DB: Soporte PostgreSQL directo vía DATABASE_URL (Supabase)",
            "📦 requirements: psycopg2-binary para conexión Supabase",
        ]
    },
    {
        "version": "v2.0.0",
        "fecha": "2026-03-14",
        "cambios": [
            "📊 Sidebar global: Lead Time, Presupuestos L1/L2/L3, USD/ARS, RMB/USD",
            "🧠 Sidebar: Selector IA Claude/Gemini/GPT con API Keys",
            "📊 Dashboard: Banner tránsito + 6 KPIs operativos + 4 KPIs financieros",
            "🧮 ML: Calculadora paso a paso Lista1 → precio a publicar",
            "✏️ Demanda Manual: override cuando ERP muestra 0 por quiebre",
            "👻 Ghost SKUs: módulos pedidos sin código ERP todavía",
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
