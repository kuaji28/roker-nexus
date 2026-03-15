"""
ROKER NEXUS — Base de Datos
Soporte dual: Supabase (producción cloud) y SQLite (desarrollo local).
Cambia automáticamente según si las credenciales están configuradas.
"""
import os
import sqlite3
import json
from datetime import datetime, date
from typing import Optional
import pandas as pd

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Leer directamente sin importar config (evita circular import)
def _env(key, default=""):
    val = os.getenv(key, "")
    if val: return val
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val: return str(val)
    except Exception:
        pass
    return default

SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_KEY = _env("SUPABASE_KEY")
DEBUG = _env("DEBUG", "False").lower() == "true"

# ── Detección de backend ─────────────────────────────────────
USE_SUPABASE = SUPABASE_AVAILABLE and bool(SUPABASE_URL) and bool(SUPABASE_KEY)
import os as _os
SQLITE_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "roker_nexus.db")

# ── PostgreSQL directo (Supabase connection string) ──────────
# Más robusto que el cliente REST: soporta todas las queries existentes.
# Configurar con: DATABASE_URL = "postgresql://postgres:[PASS]@db.xxx.supabase.co:5432/postgres"
import re as _re_db
DATABASE_URL = _env("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

_supabase: Optional[object] = None


def get_supabase() -> Optional[object]:
    global _supabase
    if USE_SUPABASE and _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def get_sqlite() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg_conn():
    """Conexión directa a PostgreSQL (Supabase). Requiere DATABASE_URL."""
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


def _sql_pg(sql: str) -> str:
    """Convierte SQL SQLite a PostgreSQL: placeholders y conflictos."""
    # ? → %s  (estilo psycopg2)
    sql = sql.replace('?', '%s')
    # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    if _re_db.search(r'INSERT\s+OR\s+IGNORE', sql, _re_db.IGNORECASE):
        sql = _re_db.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', sql, flags=_re_db.IGNORECASE)
        sql = sql.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    # INSERT OR REPLACE → ON CONFLICT DO UPDATE
    if _re_db.search(r'INSERT\s+OR\s+REPLACE', sql, _re_db.IGNORECASE):
        sql = _re_db.sub(r'INSERT\s+OR\s+REPLACE\s+INTO', 'INSERT INTO', sql, flags=_re_db.IGNORECASE)
        if 'configuracion' in sql.lower():
            sql = (sql.rstrip().rstrip(';')
                   + ' ON CONFLICT (clave) DO UPDATE SET valor=EXCLUDED.valor, actualizado_en=now()')
        else:
            sql = sql.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    return sql


# ── Schema SQL ────────────────────────────────────────────────
SCHEMA_SQL = """

-- Catalogo maestro de articulos
CREATE TABLE IF NOT EXISTS articulos (
    codigo          TEXT PRIMARY KEY,
    descripcion     TEXT NOT NULL,
    marca           TEXT,
    rubro           TEXT,
    super_rubro     TEXT,
    tipo_codigo     TEXT CHECK(tipo_codigo IN ('mecanico','con_marco','otro')),
    activo          INTEGER DEFAULT 1,
    en_lista_negra  INTEGER DEFAULT 0,
    motivo_negra    TEXT,
    fecha_negra     TEXT,
    creado_en       TEXT DEFAULT (datetime('now')),
    actualizado_en  TEXT DEFAULT (datetime('now'))
);

-- Snapshots de stock por deposito y fecha
CREATE TABLE IF NOT EXISTS stock_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL,
    deposito        TEXT NOT NULL,
    descripcion     TEXT DEFAULT '',
    rubro           TEXT DEFAULT '',
    stock           REAL DEFAULT 0,
    stock_minimo    REAL DEFAULT 0,
    stock_optimo    REAL DEFAULT 0,
    stock_maximo    REAL DEFAULT 0,
    fecha           TEXT NOT NULL,
    fecha_snapshot  TEXT DEFAULT (datetime('now')),
    importado_en    TEXT DEFAULT (datetime('now')),
    UNIQUE(codigo, deposito, fecha)
);


-- Lista de precios (todas las listas)
CREATE TABLE IF NOT EXISTS precios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL,
    lista_1         REAL DEFAULT 0,
    lista_2         REAL DEFAULT 0,
    lista_3         REAL DEFAULT 0,
    lista_4         REAL DEFAULT 0,
    lista_5         REAL DEFAULT 0,
    moneda          TEXT DEFAULT 'USD',
    fecha           TEXT NOT NULL,
    importado_en    TEXT DEFAULT (datetime('now')),
    UNIQUE(codigo, fecha)
);

-- Datos de optimizacion de stock (de Flexxus)
CREATE TABLE IF NOT EXISTS optimizacion (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo              TEXT NOT NULL,
    descripcion         TEXT,
    demanda_total       REAL DEFAULT 0,
    demanda_promedio    REAL DEFAULT 0,
    stock_actual        REAL DEFAULT 0,
    stock_minimo        REAL DEFAULT 0,
    stock_optimo        REAL DEFAULT 0,
    stock_maximo        REAL DEFAULT 0,
    costo_reposicion    REAL DEFAULT 0,
    moneda              TEXT DEFAULT 'USD',
    r_minimo            REAL DEFAULT 0,
    r_optimo            REAL DEFAULT 0,
    r_maximo            REAL DEFAULT 0,
    periodo_desde       TEXT,
    periodo_hasta       TEXT,
    dias_promedio       INTEGER DEFAULT 30,
    importado_en        TEXT DEFAULT (datetime('now')),
    UNIQUE(codigo, importado_en)
);

-- Historial de ventas por articulo
CREATE TABLE IF NOT EXISTS ventas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL,
    descripcion     TEXT,
    total_venta_ars REAL DEFAULT 0,
    marca           TEXT,
    super_rubro     TEXT,
    fecha_desde     TEXT NOT NULL,
    fecha_hasta     TEXT NOT NULL,
    importado_en    TEXT DEFAULT (datetime('now')),
    UNIQUE(codigo, fecha_desde, fecha_hasta)
);

-- Historial de compras por marca
CREATE TABLE IF NOT EXISTS compras_historial (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL,
    descripcion     TEXT,
    marca           TEXT,
    rubro           TEXT,
    cantidad        REAL DEFAULT 0,
    fecha_desde     TEXT NOT NULL,
    fecha_hasta     TEXT NOT NULL,
    importado_en    TEXT DEFAULT (datetime('now')),
    UNIQUE(codigo, fecha_desde, fecha_hasta)
);

-- Remitos internos entre depositos
CREATE TABLE IF NOT EXISTS remitos_internos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    numero          TEXT,
    fecha           TEXT,
    deposito_origen TEXT,
    deposito_destino TEXT,
    cliente         TEXT,
    monto           REAL DEFAULT 0,
    facturado       TEXT,
    responsable     TEXT,
    importado_en    TEXT DEFAULT (datetime('now'))
);

-- Cotizaciones de proveedores
CREATE TABLE IF NOT EXISTS cotizaciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor       TEXT NOT NULL DEFAULT 'AI-TECH',
    invoice_id      TEXT,
    filename        TEXT,
    fecha           TEXT NOT NULL,
    total_usd       REAL DEFAULT 0,
    estado          TEXT DEFAULT 'pendiente',
    fecha_pendiente TEXT DEFAULT (datetime('now')),
    fecha_transito  TEXT,
    fecha_ingresado TEXT,
    notas           TEXT,
    importado_en    TEXT DEFAULT (datetime('now'))
);

-- Items de cada cotizacion (Order List de Diego)
CREATE TABLE IF NOT EXISTS cotizacion_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cotizacion_id       INTEGER REFERENCES cotizaciones(id) ON DELETE CASCADE,
    -- Datos del Order List
    brand               TEXT,
    codigo_proveedor    TEXT NOT NULL,
    modelo_universal    TEXT,
    modelo_sticker      TEXT,
    specification       TEXT,
    type_lcd            TEXT,
    quality             TEXT,
    colour              TEXT,
    seccion             TEXT,
    -- Cantidades
    cantidad_pedida     INTEGER DEFAULT 0,
    cantidad_recibida   INTEGER DEFAULT 0,
    -- Precios
    precio_usd          REAL DEFAULT 0,
    subtotal_usd        REAL DEFAULT 0,
    -- Matching Flexxus
    codigo_flexxus      TEXT,
    descripcion_flexxus TEXT,
    match_score         INTEGER DEFAULT 0,
    match_confirmado    INTEGER DEFAULT 0,
    -- Estado del ítem
    estado_item         TEXT DEFAULT 'pendiente',
    -- Legacy (mantener compatibilidad)
    descripcion         TEXT,
    precio_usd_legacy   REAL DEFAULT 0,
    cantidad_caja       INTEGER DEFAULT 1,
    cantidad_sugerida   INTEGER DEFAULT 0,
    en_lista_negra      INTEGER DEFAULT 0,
    notas               TEXT
);

-- Lotes de pedido (batches de compra)
CREATE TABLE IF NOT EXISTS pedidos_lotes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    proveedor       TEXT NOT NULL,
    tope_usd        REAL DEFAULT 0,
    total_usd       REAL DEFAULT 0,
    estado          TEXT DEFAULT 'borrador',
    cotizacion_id   INTEGER REFERENCES cotizaciones(id),
    fecha_creado    TEXT DEFAULT (datetime('now')),
    fecha_enviado   TEXT,
    notas           TEXT
);

-- Items de cada lote de pedido
CREATE TABLE IF NOT EXISTS pedidos_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lote_id         INTEGER REFERENCES pedidos_lotes(id),
    codigo          TEXT NOT NULL,
    descripcion     TEXT,
    precio_usd      REAL DEFAULT 0,
    cantidad        INTEGER DEFAULT 0,
    subtotal_usd    REAL DEFAULT 0,
    motivo_inclusion TEXT,
    editado_manual  INTEGER DEFAULT 0
);

-- Pedidos en transito
CREATE TABLE IF NOT EXISTS pedidos_transito (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lote_id         INTEGER REFERENCES pedidos_lotes(id),
    invoice_id      TEXT,
    proveedor       TEXT,
    fecha_pedido    TEXT,
    fecha_estimada  TEXT,
    fecha_ingreso   TEXT,
    estado          TEXT DEFAULT 'en_transito',
    total_usd       REAL DEFAULT 0,
    notas           TEXT
);

-- Historial de stock para detectar anomalías (PERSISTE entre cargas)
CREATE TABLE IF NOT EXISTS historial_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL,
    deposito TEXT NOT NULL DEFAULT 'GENERAL',
    stock REAL DEFAULT 0,
    demanda REAL DEFAULT 0,
    fecha TEXT NOT NULL,
    fecha_carga TEXT DEFAULT (datetime('now')),
    tipo_proveedor TEXT DEFAULT 'mecanico',
    UNIQUE(codigo, deposito, fecha)
);

CREATE INDEX IF NOT EXISTS idx_hist_codigo ON historial_stock(codigo);
CREATE INDEX IF NOT EXISTS idx_hist_fecha ON historial_stock(fecha);

-- Anomalias detectadas
CREATE TABLE IF NOT EXISTS anomalias (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL,
    deposito        TEXT,
    tipo            TEXT,
    descripcion     TEXT,
    severidad       TEXT DEFAULT 'media',
    estado          TEXT DEFAULT 'abierta',
    detectada_en    TEXT DEFAULT (datetime('now')),
    resuelta_en     TEXT,
    notas           TEXT
);

-- Tasa de cambio USD/ARS historico
CREATE TABLE IF NOT EXISTS tasas_cambio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT NOT NULL UNIQUE,
    usd_ars         REAL NOT NULL,
    fuente          TEXT DEFAULT 'manual'
);

-- Log de importaciones
CREATE TABLE IF NOT EXISTS importaciones_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_archivo    TEXT NOT NULL,
    nombre_archivo  TEXT,
    filas_importadas INTEGER DEFAULT 0,
    filas_error     INTEGER DEFAULT 0,
    estado          TEXT DEFAULT 'ok',
    mensaje         TEXT,
    importado_en    TEXT DEFAULT (datetime('now'))
);


-- Configuración del sistema
CREATE TABLE IF NOT EXISTS configuracion (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    clave       TEXT UNIQUE NOT NULL,
    valor       TEXT NOT NULL,
    descripcion TEXT,
    actualizado_en TEXT DEFAULT (datetime('now'))
);


-- Borrador de pedido (anotaciones conversacionales sin código todavía)
CREATE TABLE IF NOT EXISTS borrador_pedido (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Input del usuario (puede ser texto libre)
    texto_original  TEXT NOT NULL,
    -- Resultado del matching
    codigo_flexxus  TEXT,        -- NULL si todavía no se confirmó
    descripcion     TEXT,
    tipo_codigo     TEXT,        -- 'fr' | 'mecanico' | NULL
    match_score     INTEGER DEFAULT 0,
    match_confirmado INTEGER DEFAULT 0,
    -- Negocio
    cantidad        INTEGER DEFAULT 0,
    precio_usd      REAL DEFAULT 0,
    subtotal_usd    REAL DEFAULT 0,
    -- Alerta FR: si el modelo tiene stock FR disponible
    stock_fr_disponible INTEGER DEFAULT 0,
    codigo_fr_alternativo TEXT,
    -- Estado del item
    estado          TEXT DEFAULT 'pendiente',  -- pendiente | confirmado | descartado
    notas           TEXT,
    -- Origen: 'web' | 'telegram'
    origen          TEXT DEFAULT 'web',
    sesion_id       TEXT,
    creado_en       TEXT DEFAULT (datetime('now')),
    actualizado_en  TEXT DEFAULT (datetime('now'))
);

-- Índice para búsqueda por sesión
CREATE INDEX IF NOT EXISTS idx_borrador_sesion ON borrador_pedido(sesion_id);
CREATE INDEX IF NOT EXISTS idx_borrador_estado ON borrador_pedido(estado);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_stock_codigo ON stock_snapshots(codigo);
CREATE INDEX IF NOT EXISTS idx_stock_fecha ON stock_snapshots(fecha);
CREATE INDEX IF NOT EXISTS idx_stock_deposito ON stock_snapshots(deposito);
CREATE INDEX IF NOT EXISTS idx_precios_codigo ON precios(codigo);
CREATE INDEX IF NOT EXISTS idx_optimizacion_codigo ON optimizacion(codigo);
CREATE INDEX IF NOT EXISTS idx_ventas_codigo ON ventas(codigo);
CREATE INDEX IF NOT EXISTS idx_anomalias_estado ON anomalias(estado);
"""


CONFIG_DEFAULTS = [
    ("tasa_usd_ars",          "1420",  "USD → ARS tipo de cambio"),
    ("tasa_rmb_usd",          "6.9",   "RMB (Yuan) → ARS (precio directo)"),
    ("margen_venta_pct",      "120",   "Margen venta sobre costo (%)"),
    ("comision_ml_fr",        "14.0",  "Comisión ML Tienda FR (%)"),
    ("comision_ml_mecanico",  "13.0",  "Comisión ML Tienda Mecánico (%)"),
    ("margen_extra_ml_fr",    "0.0",   "Margen adicional ML FR (%)"),
    ("margen_extra_ml_mec",   "0.0",   "Margen adicional ML Mecánico (%)"),
    ("presupuesto_lote_1",    "15000", "Presupuesto Lote 1 (USD)"),
    ("presupuesto_lote_2",    "10000", "Presupuesto Lote 2 (USD)"),
    ("presupuesto_lote_3",    "8000",  "Presupuesto Lote 3 (USD)"),
    ("coef_stock_min",        "1.0",   "Coeficiente stock mínimo"),
    ("coef_stock_opt",        "1.2",   "Coeficiente stock óptimo"),
    ("coef_stock_max",        "1.4",   "Coeficiente stock máximo"),
    ("umbral_quiebre_stock",  "10",    "Stock mínimo antes de alerta quiebre"),
    ("umbral_margen_minimo",  "40",    "Margen mínimo (%): alerta si cae debajo"),
    ("lead_time_dias",        "45",    "Días de tránsito desde proveedor"),
]


def get_config(clave: str, tipo=str):
    """Obtiene un valor de configuración."""
    try:
        rows = execute_query("SELECT valor FROM configuracion WHERE clave=?", (clave,))
        if rows:
            return tipo(rows[0]["valor"])
    except Exception:
        pass
    # Buscar en defaults
    for k, v, _ in CONFIG_DEFAULTS:
        if k == clave:
            return tipo(v)
    return tipo()


def set_config(clave: str, valor) -> bool:
    """Guarda un valor de configuración."""
    try:
        execute_query(
            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
            (clave, str(valor)), fetch=False
        )
        return True
    except Exception:
        return False


def get_all_config() -> dict:
    """Retorna toda la configuración como dict."""
    result = {}
    # Defaults primero
    for k, v, _ in CONFIG_DEFAULTS:
        result[k] = v
    # Sobreescribir con valores guardados
    try:
        rows = execute_query("SELECT clave, valor FROM configuracion")
        for r in rows:
            result[r["clave"]] = r["valor"]
    except Exception:
        pass
    return result




def _migrar_db():
    """
    Migración incremental: agrega columnas/tablas nuevas a DBs existentes.
    Se ejecuta siempre en init_db() — es idempotente (usa try/except por columna).
    """
    conn = get_sqlite()
    migraciones = [
        # cotizaciones: columnas nuevas de v1.8
        "ALTER TABLE cotizaciones ADD COLUMN filename TEXT",
        "ALTER TABLE cotizaciones ADD COLUMN fecha_pendiente TEXT",
        "ALTER TABLE cotizaciones ADD COLUMN fecha_transito TEXT",
        "ALTER TABLE cotizaciones ADD COLUMN fecha_ingresado TEXT",
        # cotizacion_items: campos del Order List
        "ALTER TABLE cotizacion_items ADD COLUMN brand TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN codigo_proveedor TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN modelo_universal TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN modelo_sticker TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN specification TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN type_lcd TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN quality TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN colour TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN seccion TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN cantidad_pedida INTEGER DEFAULT 0",
        "ALTER TABLE cotizacion_items ADD COLUMN cantidad_recibida INTEGER DEFAULT 0",
        "ALTER TABLE cotizacion_items ADD COLUMN subtotal_usd REAL DEFAULT 0",
        "ALTER TABLE cotizacion_items ADD COLUMN descripcion_flexxus TEXT",
        "ALTER TABLE cotizacion_items ADD COLUMN match_score INTEGER DEFAULT 0",
        "ALTER TABLE cotizacion_items ADD COLUMN match_confirmado INTEGER DEFAULT 0",
        "ALTER TABLE cotizacion_items ADD COLUMN estado_item TEXT DEFAULT 'pendiente'",
        # articulos: campos ML
        "ALTER TABLE articulos ADD COLUMN mla_id_fr TEXT",
        "ALTER TABLE articulos ADD COLUMN mla_id_mec TEXT",
        "ALTER TABLE articulos ADD COLUMN ml_termino_busqueda TEXT",
        "ALTER TABLE articulos ADD COLUMN ml_termino_anclado INTEGER DEFAULT 0",
        # Precios competencia
        """CREATE TABLE IF NOT EXISTS ml_precios_competencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL, precio_ars REAL DEFAULT 0,
            competidor TEXT, link TEXT,
            fecha_carga TEXT DEFAULT (date('now')),
            UNIQUE(descripcion, competidor)
        )""",
        # Columnas faltantes en cotizacion_items
        """ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS codigo TEXT""",
        """ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS codigo_flexxus TEXT""",
        # Borrador de pedido
        """CREATE TABLE IF NOT EXISTS borrador_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            texto_original TEXT NOT NULL,
            codigo_flexxus TEXT, descripcion TEXT,
            tipo_codigo TEXT, match_score INTEGER DEFAULT 0,
            match_confirmado INTEGER DEFAULT 0,
            cantidad INTEGER DEFAULT 0, precio_usd REAL DEFAULT 0,
            subtotal_usd REAL DEFAULT 0,
            stock_fr_disponible INTEGER DEFAULT 0,
            codigo_fr_alternativo TEXT,
            estado TEXT DEFAULT 'pendiente',
            notas TEXT, origen TEXT DEFAULT 'web', sesion_id TEXT,
            creado_en TEXT DEFAULT (datetime('now')),
            actualizado_en TEXT DEFAULT (datetime('now'))
        )""",
        # Columnas sidebar que pueden faltar
        "ALTER TABLE configuracion ADD COLUMN descripcion TEXT",
        # Tabla demanda_manual
        """CREATE TABLE IF NOT EXISTS demanda_manual (
            codigo TEXT PRIMARY KEY, demanda_manual REAL NOT NULL,
            nota TEXT, actualizado TEXT DEFAULT (datetime('now')))""",
        # Tabla ghost_skus
        """CREATE TABLE IF NOT EXISTS ghost_skus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo_descripcion TEXT NOT NULL, proveedor_tipo TEXT DEFAULT 'MECÁNICO',
            cantidad_estimada REAL DEFAULT 0, estado TEXT DEFAULT 'PENDIENTE',
            codigo_vinculado TEXT DEFAULT '', notas TEXT DEFAULT '',
            origen TEXT DEFAULT 'WEB', fecha_creacion TEXT DEFAULT (datetime('now')),
            fecha_vinculacion TEXT)""",
        # Historial stock (para anomalías)
        """CREATE TABLE IF NOT EXISTS historial_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL, deposito TEXT NOT NULL DEFAULT 'GENERAL',
            stock REAL DEFAULT 0, demanda REAL DEFAULT 0, fecha TEXT NOT NULL,
            fecha_carga TEXT DEFAULT (datetime('now')),
            tipo_proveedor TEXT DEFAULT 'mecanico',
            UNIQUE(codigo, deposito, fecha)
        )""",
        # Archivo de Mariano (referencia de auditoría — no afecta cálculos)
        """CREATE TABLE IF NOT EXISTS mariano_repuestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            descripcion TEXT,
            demanda_total REAL DEFAULT 0,
            demanda_prom REAL DEFAULT 0,
            stock_actual REAL DEFAULT 0,
            a_pedir REAL DEFAULT 0,
            stock_optimo REAL DEFAULT 0,
            importado_en TEXT DEFAULT (datetime('now'))
        )""",
        # Ingresos reales de mercadería (packing de China)
        """CREATE TABLE IF NOT EXISTS ingresos_mercaderia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id INTEGER,
            invoice_id TEXT,
            codigo TEXT NOT NULL,
            descripcion TEXT,
            cantidad_pedida INTEGER DEFAULT 0,
            cantidad_ingresada INTEGER DEFAULT 0,
            diferencia INTEGER DEFAULT 0,
            fecha_ingreso TEXT,
            fecha_flexxus TEXT,
            confirmado INTEGER DEFAULT 0,
            notas TEXT,
            creado_en TEXT DEFAULT (datetime('now'))
        )""",
        # Alertas de stock (subidas y caídas detectadas al importar)
        """CREATE TABLE IF NOT EXISTS stock_alertas (
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
        )""",
        # ML reporte (tabla completa si no existe)
        """CREATE TABLE IF NOT EXISTS ml_reporte_comparaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT, descripcion TEXT, tipo_tienda TEXT,
            termino_busqueda TEXT, nuestro_precio REAL,
            mejor_competidor_precio REAL, diferencia_pct REAL,
            link_competidor TEXT,
            fecha_comparacion TEXT DEFAULT (datetime('now')),
            observaciones TEXT
        )""",
    ]
    for sql in migraciones:
        try:
            conn.execute(sql)
        except Exception:
            pass  # Columna/tabla ya existe — normal
    conn.commit()
    conn.close()

def init_db():
    """Inicializa la base de datos con el schema completo."""
    if USE_POSTGRES:
        # PostgreSQL directo: schema ya fue creado en Supabase SQL Editor.
        # Solo necesitamos sembrar la configuración por defecto.
        try:
            import psycopg2
            conn = get_pg_conn()
            cur = conn.cursor()
            for k, v, d in CONFIG_DEFAULTS:
                cur.execute(
                    "INSERT INTO configuracion (clave, valor, descripcion) VALUES (%s, %s, %s) "
                    "ON CONFLICT (clave) DO NOTHING",
                    (k, v, d)
                )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            if DEBUG:
                print(f"PostgreSQL init_db error: {e}, cayendo a SQLite")
            # Fall through a SQLite como fallback de emergencia

    if USE_SUPABASE:
        # Con Supabase REST: verificar conexión y crear tablas si no existen
        try:
            sb = get_supabase()
            sb.table("articulos").select("count", count="exact").execute()
            return True
        except Exception as e:
            if DEBUG:
                print(f"Supabase error, usando SQLite: {e}")

    # SQLite local
    conn = get_sqlite()
    # Ejecutar schema completo
    try:
        conn.executescript(SCHEMA_SQL)
    except Exception as e:
        # Fallback: sentencia por sentencia
        for stmt in SCHEMA_SQL.split(';'):
            stmt = stmt.strip()
            if stmt:
                try:
                    conn.execute(stmt)
                except Exception:
                    pass
        conn.commit()
    # Insertar configuración por defecto (tabla ya creada por schema)
    try:
        for k, v, d in CONFIG_DEFAULTS:
            conn.execute(
                "INSERT OR IGNORE INTO configuracion (clave, valor, descripcion) VALUES (?,?,?)",
                (k, v, d)
            )
        conn.commit()
    except Exception as e:
        print(f"Config defaults warning: {e}")
    conn.close()
    try:
        _migrar_db()
    except Exception:
        pass
    return True


def execute_query(sql: str, params: tuple = (), fetch: bool = True):
    """Ejecuta una query en PostgreSQL o SQLite según configuración."""
    if USE_POSTGRES:
        pg_conn = None
        try:
            import psycopg2
            import psycopg2.extras
            pg_conn = get_pg_conn()
            cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(_sql_pg(sql), params if params else None)
            if fetch:
                rows = [dict(r) for r in cur.fetchall()]
                pg_conn.close()
                return rows
            else:
                pg_conn.commit()
                rowcount = cur.rowcount
                pg_conn.close()
                return rowcount
        except Exception as e:
            if DEBUG:
                print(f"PostgreSQL execute_query error: {e}")
            try:
                if pg_conn:
                    pg_conn.close()
            except Exception:
                pass
            return [] if fetch else 0

    # SQLite
    conn = get_sqlite()
    try:
        cur = conn.execute(sql, params)
        if fetch:
            rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        else:
            conn.commit()
            rowcount = cur.rowcount
            conn.close()
            return rowcount
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        if fetch:
            return []
        return 0


def df_to_db(df: pd.DataFrame, table: str, if_exists: str = "append") -> int:
    """Inserta un DataFrame en la base de datos. Usa ON CONFLICT DO NOTHING para evitar UNIQUE errors."""
    import math

    # Limpiar NaN/Inf (aplica a todos los backends)
    df_clean = df.copy()
    for col in df_clean.select_dtypes(include=['float', 'float64']).columns:
        df_clean[col] = df_clean[col].apply(
            lambda x: None if (x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))) else x
        )
    df_clean = df_clean.where(df_clean.notna(), None)

    if USE_POSTGRES:
        pg_conn = None
        try:
            import psycopg2
            import psycopg2.extras
            pg_conn = get_pg_conn()
            cur = pg_conn.cursor()
            cols = ", ".join(df_clean.columns)
            phs = ", ".join(["%s"] * len(df_clean.columns))
            sql = f"INSERT INTO {table} ({cols}) VALUES ({phs}) ON CONFLICT DO NOTHING"
            records = [tuple(r) for r in df_clean.itertuples(index=False, name=None)]
            psycopg2.extras.execute_batch(cur, sql, records, page_size=500)
            pg_conn.commit()
            count = len(records)
            pg_conn.close()
            return count
        except Exception as e:
            print(f"PostgreSQL df_to_db error: {e}, cayendo a SQLite")
            try:
                if pg_conn:
                    pg_conn.close()
            except Exception:
                pass

    # SQLite
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        cols = ", ".join(df_clean.columns)
        placeholders = ", ".join(["?" for _ in df_clean.columns])
        sql = f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})"
        data = [tuple(row) for row in df_clean.itertuples(index=False, name=None)]
        conn.executemany(sql, data)
        conn.commit()
        count = len(data)
    except Exception as e:
        print(f"df_to_db fallback error: {e}")
        try:
            df.to_sql(table, conn, if_exists=if_exists, index=False, method="multi")
            conn.commit()
            count = len(df)
        except Exception as e2:
            print(f"df_to_db to_sql error: {e2}")
            count = 0
    conn.close()
    return count


def query_to_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Ejecuta una query y retorna un DataFrame. Usa PostgreSQL si DATABASE_URL está configurado."""
    if USE_POSTGRES:
        try:
            import psycopg2
            import warnings
            pg_conn = get_pg_conn()
            pg_sql = _sql_pg(sql)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                df = pd.read_sql_query(pg_sql, pg_conn, params=list(params) if params else None)
            pg_conn.close()
            return df
        except Exception as e:
            if DEBUG:
                print(f"PostgreSQL query_to_df error: {e}")
    # SQLite
    try:
        conn = get_sqlite()
        df = pd.read_sql_query(sql, conn, params=list(params) if params else [])
        conn.close()
        return df
    except Exception as e:
        print(f"query_to_df error: {e}")
        return pd.DataFrame()


def log_importacion(tipo: str, nombre: str, filas_ok: int, filas_err: int = 0,
                    estado: str = "ok", mensaje: str = ""):
    """Registra una importación en el log."""
    try:
        execute_query(
            """INSERT INTO importaciones_log
               (tipo_archivo, nombre_archivo, filas_importadas, filas_error, estado, mensaje)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tipo, nombre, filas_ok, filas_err, estado, mensaje),
            fetch=False
        )
    except Exception:
        pass  # Log no es critico


def get_ultima_importacion(tipo: str) -> Optional[dict]:
    """Retorna la última importación de un tipo dado."""
    rows = execute_query(
        "SELECT * FROM importaciones_log WHERE tipo_archivo=? ORDER BY importado_en DESC LIMIT 1",
        (tipo,)
    )
    return rows[0] if rows else None


def get_stock_actual(deposito: Optional[str] = None) -> pd.DataFrame:
    """Retorna el stock más reciente por código y depósito."""
    if deposito:
        sql = """
            SELECT s.*, a.descripcion, a.marca, a.rubro
            FROM stock_snapshots s
            JOIN (
                SELECT codigo, deposito, MAX(fecha) as max_fecha
                FROM stock_snapshots WHERE deposito=?
                GROUP BY codigo, deposito
            ) latest ON s.codigo=latest.codigo AND s.deposito=latest.deposito AND s.fecha=latest.max_fecha
            LEFT JOIN articulos a ON s.codigo=a.codigo
            ORDER BY s.stock ASC
        """
        return query_to_df(sql, (deposito,))
    else:
        sql = """
            SELECT s.*, a.descripcion, a.marca, a.rubro
            FROM stock_snapshots s
            JOIN (
                SELECT codigo, deposito, MAX(fecha) as max_fecha
                FROM stock_snapshots
                GROUP BY codigo, deposito
            ) latest ON s.codigo=latest.codigo AND s.deposito=latest.deposito AND s.fecha=latest.max_fecha
            LEFT JOIN articulos a ON s.codigo=a.codigo
            ORDER BY s.deposito, s.stock ASC
        """
        return query_to_df(sql)


def get_quiebres(deposito: Optional[str] = None, umbral: int = 10) -> pd.DataFrame:
    """Retorna artículos con stock bajo o en cero."""
    dep_filter = "AND s.deposito=?" if deposito else ""
    params = (umbral, deposito) if deposito else (umbral,)
    sql = f"""
        SELECT s.codigo, s.deposito, s.stock, s.stock_minimo, s.fecha,
               a.descripcion, a.marca, a.en_lista_negra,
               p.lista_1 as precio_lista1, p.lista_4 as precio_ml
        FROM stock_snapshots s
        JOIN (
            SELECT codigo, deposito, MAX(fecha) as max_fecha
            FROM stock_snapshots GROUP BY codigo, deposito
        ) latest ON s.codigo=latest.codigo AND s.deposito=latest.deposito AND s.fecha=latest.max_fecha
        LEFT JOIN articulos a ON s.codigo=a.codigo
        LEFT JOIN precios p ON s.codigo=p.codigo
        WHERE s.stock <= ? AND a.en_lista_negra=0 {dep_filter}
        ORDER BY s.stock ASC, a.marca
    """
    return query_to_df(sql, params)


# Inicializar al importar
# init_db() se llama desde app.py


def get_resumen_stats() -> dict:
    """Retorna estadísticas resumidas para el dashboard."""
    try:
        conn = get_sqlite()
        
        def safe_count(sql):
            try:
                cur = conn.execute(sql)
                return cur.fetchone()[0] or 0
            except Exception:
                return 0

        # Si hay stock_snapshots usamos eso; si no, caemos a articulos/optimizacion
        total_stock = safe_count("SELECT COUNT(DISTINCT codigo) FROM stock_snapshots")
        if total_stock > 0:
            total = total_stock
            sin_stk  = safe_count("""
                SELECT COUNT(*) FROM stock_snapshots s
                JOIN (SELECT codigo,deposito,MAX(fecha) mf FROM stock_snapshots GROUP BY codigo,deposito) lx
                  ON s.codigo=lx.codigo AND s.deposito=lx.deposito AND s.fecha=lx.mf
                WHERE s.stock=0""")
            bajo_min = safe_count("""
                SELECT COUNT(*) FROM stock_snapshots s
                JOIN (SELECT codigo,deposito,MAX(fecha) mf FROM stock_snapshots GROUP BY codigo,deposito) lx
                  ON s.codigo=lx.codigo AND s.deposito=lx.deposito AND s.fecha=lx.mf
                WHERE s.stock>0 AND s.stock<s.stock_minimo AND s.stock_minimo>0""")
        else:
            # Usar optimizacion como fuente alternativa
            total    = safe_count("SELECT COUNT(DISTINCT codigo) FROM optimizacion WHERE UPPER(descripcion) LIKE 'MODULO%'")
            sin_stk  = safe_count("SELECT COUNT(*) FROM optimizacion WHERE stock_actual=0 AND UPPER(descripcion) LIKE 'MODULO%'")
            bajo_min = safe_count("SELECT COUNT(*) FROM optimizacion WHERE stock_actual>0 AND stock_actual<stock_minimo AND stock_minimo>0 AND UPPER(descripcion) LIKE 'MODULO%'")

        try:
            cur = conn.execute("SELECT importado_en FROM importaciones_log ORDER BY importado_en DESC LIMIT 1")
            row = cur.fetchone()
            ultima = str(row[0])[:16] if row else "—"
        except Exception:
            ultima = "—"
        conn.close()
        return {"total_articulos": total, "sin_stock": sin_stk,
                "bajo_minimo": bajo_min, "depositos_activos": 3,
                "ultima_importacion": ultima}
    except Exception:
        return {}


def get_lista_negra() -> pd.DataFrame:
    """Retorna todos los artículos en lista negra."""
    try:
        conn = get_sqlite()
        df = pd.read_sql_query(
            "SELECT codigo, descripcion, motivo, agregado_en FROM articulos WHERE en_lista_negra=1 ORDER BY agregado_en DESC",
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["codigo", "descripcion", "motivo", "agregado_en"])


def agregar_a_lista_negra(codigo: str, motivo: str = "") -> bool:
    """Agrega un artículo a lista negra."""
    try:
        conn = get_sqlite()
        from datetime import datetime
        conn.execute("""
            INSERT INTO articulos (codigo, en_lista_negra, motivo, agregado_en)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(codigo) DO UPDATE SET
                en_lista_negra=1, motivo=excluded.motivo, agregado_en=excluded.agregado_en
        """, (codigo.strip().upper(), motivo, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def quitar_de_lista_negra(codigo: str) -> bool:
    """Quita un artículo de lista negra."""
    try:
        conn = get_sqlite()
        conn.execute(
            "UPDATE articulos SET en_lista_negra=0 WHERE codigo=?",
            (codigo.strip().upper(),)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
