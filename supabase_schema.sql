
-- ROKER NEXUS — Schema Supabase
-- Pegar en: https://supabase.com/dashboard → SQL Editor → New query → Run

CREATE TABLE IF NOT EXISTS articulos (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    tipo_codigo TEXT DEFAULT 'otro',
    marca TEXT,
    rubro TEXT,
    en_lista_negra INTEGER DEFAULT 0,
    notas TEXT,
    creado_en TIMESTAMPTZ DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock_snapshots (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    deposito TEXT NOT NULL,
    descripcion TEXT DEFAULT '',
    rubro TEXT DEFAULT '',
    stock REAL DEFAULT 0,
    stock_minimo REAL DEFAULT 0,
    stock_optimo REAL DEFAULT 0,
    stock_maximo REAL DEFAULT 0,
    fecha TEXT NOT NULL,
    fecha_snapshot TIMESTAMPTZ DEFAULT NOW(),
    importado_en TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(codigo, deposito, fecha)
);

CREATE TABLE IF NOT EXISTS precios (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    lista_1 REAL DEFAULT 0,
    lista_2 REAL DEFAULT 0,
    lista_3 REAL DEFAULT 0,
    lista_4 REAL DEFAULT 0,
    lista_5 REAL DEFAULT 0,
    moneda TEXT DEFAULT 'USD',
    fecha TEXT NOT NULL,
    importado_en TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(codigo, fecha)
);

CREATE TABLE IF NOT EXISTS optimizacion (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    descripcion TEXT,
    demanda_total REAL DEFAULT 0,
    demanda_promedio REAL DEFAULT 0,
    stock_actual REAL DEFAULT 0,
    stock_minimo REAL DEFAULT 0,
    stock_optimo REAL DEFAULT 0,
    stock_maximo REAL DEFAULT 0,
    costo_reposicion REAL DEFAULT 0,
    moneda TEXT DEFAULT 'USD',
    periodo_desde TEXT,
    periodo_hasta TEXT,
    dias_promedio INTEGER DEFAULT 30,
    importado_en TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(codigo, importado_en)
);

CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    codigo TEXT,
    marca TEXT,
    descripcion TEXT,
    cantidad INTEGER DEFAULT 0,
    total_venta_ars REAL DEFAULT 0,
    fecha_desde TEXT,
    fecha_hasta TEXT,
    importado_en TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(codigo, fecha_desde, fecha_hasta)
);

CREATE TABLE IF NOT EXISTS compras_historial (
    id SERIAL PRIMARY KEY,
    codigo TEXT,
    marca TEXT,
    descripcion TEXT,
    cantidad INTEGER DEFAULT 0,
    precio_usd REAL DEFAULT 0,
    fecha_desde TEXT,
    fecha_hasta TEXT,
    importado_en TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(codigo, fecha_desde, fecha_hasta)
);

CREATE TABLE IF NOT EXISTS cotizaciones (
    id SERIAL PRIMARY KEY,
    proveedor TEXT NOT NULL,
    invoice_id TEXT,
    fecha TEXT NOT NULL,
    total_usd REAL DEFAULT 0,
    estado TEXT DEFAULT 'pendiente',
    notas TEXT,
    archivo_origen TEXT,
    hoja_origen TEXT,
    importado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cotizacion_items (
    id SERIAL PRIMARY KEY,
    cotizacion_id INTEGER REFERENCES cotizaciones(id),
    codigo TEXT NOT NULL,
    descripcion TEXT,
    precio_usd REAL DEFAULT 0,
    cantidad_caja INTEGER DEFAULT 1,
    cantidad_sugerida INTEGER DEFAULT 0,
    en_lista_negra INTEGER DEFAULT 0,
    notas TEXT
);

CREATE TABLE IF NOT EXISTS pedidos_lotes (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    proveedor TEXT NOT NULL,
    tope_usd REAL DEFAULT 0,
    total_usd REAL DEFAULT 0,
    estado TEXT DEFAULT 'borrador',
    cotizacion_id INTEGER,
    fecha_creado TIMESTAMPTZ DEFAULT NOW(),
    fecha_enviado TIMESTAMPTZ,
    notas TEXT
);

CREATE TABLE IF NOT EXISTS pedidos_items (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER REFERENCES pedidos_lotes(id),
    codigo TEXT NOT NULL,
    descripcion TEXT,
    cantidad INTEGER DEFAULT 0,
    precio_usd REAL DEFAULT 0,
    subtotal_usd REAL DEFAULT 0,
    notas TEXT
);

CREATE TABLE IF NOT EXISTS pedidos_transito (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    cantidad REAL DEFAULT 0,
    proveedor TEXT,
    fecha_pedido TEXT,
    fecha_estimada TEXT,
    estado TEXT DEFAULT 'en_transito',
    archivo_origen TEXT,
    hoja_origen TEXT,
    renglon_origen INTEGER,
    notas TEXT
);

CREATE TABLE IF NOT EXISTS anomalias (
    id SERIAL PRIMARY KEY,
    codigo TEXT,
    tipo TEXT,
    descripcion TEXT,
    valor_anterior REAL,
    valor_nuevo REAL,
    estado TEXT DEFAULT 'pendiente',
    detectado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasas_cambio (
    id SERIAL PRIMARY KEY,
    moneda TEXT NOT NULL,
    usd_ars REAL NOT NULL,
    rmb_usd REAL DEFAULT 0.138,
    fecha TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS importaciones_log (
    id SERIAL PRIMARY KEY,
    tipo_archivo TEXT NOT NULL,
    nombre_archivo TEXT,
    filas_importadas INTEGER DEFAULT 0,
    filas_error INTEGER DEFAULT 0,
    estado TEXT DEFAULT 'ok',
    mensaje TEXT,
    importado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL DEFAULT '',
    descripcion TEXT DEFAULT ''
);

-- Datos iniciales
INSERT INTO configuracion (clave, valor, descripcion) VALUES
    ('tasa_usd_ars', '1420', 'USD a ARS'),
    ('tasa_rmb_usd', '6.9', 'RMB a ARS'),
    ('umbral_quiebre_stock', '10', 'Stock minimo alerta'),
    ('lead_time_dias', '45', 'Dias transito China')
ON CONFLICT (clave) DO NOTHING;
