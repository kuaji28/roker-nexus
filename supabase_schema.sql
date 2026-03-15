
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
    ('tasa_usd_ars',         '1420',  'USD a ARS'),
    ('tasa_rmb_usd',         '6.9',   'RMB a USD'),
    ('lead_time_dias',       '45',    'Dias transito China'),
    ('presupuesto_lote_1',   '15000', 'Presupuesto Lote 1 USD'),
    ('presupuesto_lote_2',   '10000', 'Presupuesto Lote 2 USD'),
    ('presupuesto_lote_3',   '8000',  'Presupuesto Lote 3 USD'),
    ('coef_stock_min',       '1.0',   'Coeficiente stock minimo'),
    ('coef_stock_opt',       '1.2',   'Coeficiente stock optimo'),
    ('coef_stock_max',       '1.4',   'Coeficiente stock maximo'),
    ('comision_ml_fr',       '14.0',  'Comision ML FR %'),
    ('comision_ml_mecanico', '13.0',  'Comision ML Mecanico %'),
    ('margen_extra_ml_fr',   '0.0',   'Margen extra ML FR %'),
    ('margen_extra_ml_mec',  '0.0',   'Margen extra ML Mecanico %'),
    ('umbral_quiebre_stock', '10',    'Stock minimo alerta')
ON CONFLICT (clave) DO NOTHING;

-- TABLAS NUEVAS v1.8+ (agregar si no existen)

CREATE TABLE IF NOT EXISTS remitos_internos (
    id SERIAL PRIMARY KEY,
    numero TEXT,
    fecha TEXT,
    origen TEXT,
    destino TEXT,
    articulos_count INTEGER DEFAULT 0,
    importado_en TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS filename TEXT;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS fecha_pendiente TEXT;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS fecha_transito TEXT;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS fecha_ingresado TEXT;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS fecha_estimada_llegada TEXT;

ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS brand TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS codigo_proveedor TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS modelo_universal TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS modelo_sticker TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS specification TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS type_lcd TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS quality TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS colour TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS seccion TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS cantidad_pedida INTEGER DEFAULT 0;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS cantidad_recibida INTEGER DEFAULT 0;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS subtotal_usd REAL DEFAULT 0;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS descripcion_flexxus TEXT;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS match_score INTEGER DEFAULT 0;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS match_confirmado INTEGER DEFAULT 0;
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS estado_item TEXT DEFAULT 'pendiente';

ALTER TABLE articulos ADD COLUMN IF NOT EXISTS mla_id_fr TEXT;
ALTER TABLE articulos ADD COLUMN IF NOT EXISTS mla_id_mec TEXT;
ALTER TABLE articulos ADD COLUMN IF NOT EXISTS ml_termino_busqueda TEXT;
ALTER TABLE articulos ADD COLUMN IF NOT EXISTS ml_termino_anclado INTEGER DEFAULT 0;

-- Archivo de Mariano (referencia de auditoría — no afecta cálculos del sistema)
CREATE TABLE IF NOT EXISTS mariano_repuestos (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    descripcion TEXT,
    demanda_total REAL DEFAULT 0,
    demanda_prom REAL DEFAULT 0,
    stock_actual REAL DEFAULT 0,
    a_pedir REAL DEFAULT 0,
    stock_optimo REAL DEFAULT 0,
    importado_en TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ml_reporte_comparaciones (
    id SERIAL PRIMARY KEY,
    codigo TEXT,
    descripcion TEXT,
    tipo_tienda TEXT,
    termino_busqueda TEXT,
    nuestro_precio REAL,
    mejor_competidor_precio REAL,
    diferencia_pct REAL,
    link_competidor TEXT,
    fecha_comparacion TIMESTAMPTZ DEFAULT NOW(),
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS ml_precios_competencia (
    id SERIAL PRIMARY KEY,
    descripcion TEXT NOT NULL,
    precio_ars REAL DEFAULT 0,
    competidor TEXT,
    link TEXT,
    fecha_carga DATE DEFAULT CURRENT_DATE,
    UNIQUE(descripcion, competidor)
);

-- TABLAS v2.0 (borrador, demanda manual, ghost SKUs, historial)

CREATE TABLE IF NOT EXISTS borrador_pedido (
    id SERIAL PRIMARY KEY,
    texto_original TEXT NOT NULL,
    codigo_flexxus TEXT,
    descripcion TEXT,
    tipo_codigo TEXT,
    match_score INTEGER DEFAULT 0,
    match_confirmado INTEGER DEFAULT 0,
    cantidad INTEGER DEFAULT 0,
    precio_usd REAL DEFAULT 0,
    subtotal_usd REAL DEFAULT 0,
    stock_fr_disponible INTEGER DEFAULT 0,
    codigo_fr_alternativo TEXT,
    estado TEXT DEFAULT 'pendiente',
    notas TEXT,
    origen TEXT DEFAULT 'web',
    sesion_id TEXT,
    creado_en TIMESTAMPTZ DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS demanda_manual (
    codigo TEXT PRIMARY KEY,
    demanda_manual REAL NOT NULL,
    nota TEXT,
    actualizado TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ghost_skus (
    id SERIAL PRIMARY KEY,
    modelo_descripcion TEXT NOT NULL,
    proveedor_tipo TEXT DEFAULT 'MECÁNICO',
    cantidad_estimada REAL DEFAULT 0,
    estado TEXT DEFAULT 'PENDIENTE',
    codigo_vinculado TEXT DEFAULT '',
    notas TEXT DEFAULT '',
    origen TEXT DEFAULT 'WEB',
    fecha_creacion TIMESTAMPTZ DEFAULT NOW(),
    fecha_vinculacion TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS historial_stock (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    deposito TEXT NOT NULL DEFAULT 'GENERAL',
    stock REAL DEFAULT 0,
    demanda REAL DEFAULT 0,
    fecha TEXT NOT NULL,
    fecha_carga TIMESTAMPTZ DEFAULT NOW(),
    tipo_proveedor TEXT DEFAULT 'mecanico',
    UNIQUE(codigo, deposito, fecha)
);

CREATE INDEX IF NOT EXISTS idx_hist_codigo ON historial_stock(codigo);
CREATE INDEX IF NOT EXISTS idx_hist_fecha ON historial_stock(fecha);

-- lista_negra (tabla separada usada desde Dashboard)
CREATE TABLE IF NOT EXISTS lista_negra (
    id SERIAL PRIMARY KEY,
    codigo TEXT UNIQUE NOT NULL,
    descripcion TEXT,
    notas TEXT,
    agregado_en TIMESTAMPTZ DEFAULT NOW()
);

-- Columna kodigo_flexxus en cotizacion_items (si no fue agregada)
ALTER TABLE cotizacion_items ADD COLUMN IF NOT EXISTS codigo_flexxus TEXT;
