-- ============================================================
-- MIGRATION v7 — GH Cars — Mejoras completas
-- Ejecutar en Supabase SQL Editor: https://supabase.com/dashboard/project/zjrabazzvckvxhufppoa/sql
-- ============================================================

-- 1. VEHICULOS — campos faltantes
ALTER TABLE vehiculos
  ADD COLUMN IF NOT EXISTS ubicacion TEXT DEFAULT 'showroom',
  ADD COLUMN IF NOT EXISTS descripcion_publica TEXT,
  ADD COLUMN IF NOT EXISTS drive_folder_id TEXT,
  ADD COLUMN IF NOT EXISTS estado_recon TEXT DEFAULT 'ingresado';

-- ubicacion: 'showroom' | 'taller' | 'cochera' | 'traslado' | 'cliente'
-- estado_recon: 'ingresado' | 'inspeccion' | 'mecanica' | 'detailing' | 'fotos_pendientes' | 'listo' | 'publicado'

-- 2. MEDIA — campos para Supabase Storage
ALTER TABLE media
  ADD COLUMN IF NOT EXISTS storage_path TEXT,
  ADD COLUMN IF NOT EXISTS storage_bucket TEXT DEFAULT 'vehiculos',
  ADD COLUMN IF NOT EXISTS tipo_shot TEXT;

-- tipo_shot: 'frente_3_4_izq' | 'frente_3_4_der' | 'lateral_izq' | 'lateral_der' |
--   'trasero_3_4' | 'tablero' | 'asientos_del' | 'asientos_tras' |
--   'baul' | 'odometro' | 'llantas' | 'motor' | 'extra'

-- 3. DOCUMENTACION — campos para alertas de vencimiento
ALTER TABLE documentacion
  ADD COLUMN IF NOT EXISTS vtv_vencimiento_calculado DATE,
  ADD COLUMN IF NOT EXISTS patente_proxima_cuota DATE,
  ADD COLUMN IF NOT EXISTS patente_deuda_estimada NUMERIC,
  ADD COLUMN IF NOT EXISTS alerta_vtv_enviada BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS alerta_patente_enviada BOOLEAN DEFAULT FALSE;

-- 4. HISTORIAL DE ESTADOS (timeline de la unidad)
CREATE TABLE IF NOT EXISTS vehiculos_historial (
  id SERIAL PRIMARY KEY,
  vehiculo_id INTEGER REFERENCES vehiculos(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL,
  descripcion TEXT NOT NULL,
  datos_extra JSONB DEFAULT '{}',
  vendedor_id UUID REFERENCES vendedores(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- tipo: 'estado_cambio' | 'ingreso' | 'foto_agregada' | 'doc_subido' |
--   'venta' | 'seña' | 'lead' | 'prueba_manejo' | 'publicado' |
--   'precio_cambio' | 'ubicacion_cambio' | 'gasto' | 'nota'
-- datos_extra ej: {"estado_anterior": "disponible", "estado_nuevo": "señado", "precio_anterior": 15000}

CREATE INDEX IF NOT EXISTS idx_historial_vehiculo ON vehiculos_historial(vehiculo_id, created_at DESC);
ALTER TABLE vehiculos_historial ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role full access historial"
  ON vehiculos_historial FOR ALL USING (true);

-- 5. AGENDA / TURNOS
CREATE TABLE IF NOT EXISTS agenda (
  id SERIAL PRIMARY KEY,
  tipo TEXT NOT NULL DEFAULT 'prueba_manejo',
  vehiculo_id INTEGER REFERENCES vehiculos(id) ON DELETE SET NULL,
  prospecto_id INTEGER REFERENCES prospectos(id) ON DELETE SET NULL,
  cliente_id UUID REFERENCES clientes(id) ON DELETE SET NULL,
  vendedor_id UUID REFERENCES vendedores(id),
  titulo TEXT,
  fecha DATE NOT NULL,
  hora TIME,
  duracion_min INTEGER DEFAULT 60,
  estado TEXT DEFAULT 'programado',
  notas TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- tipo: 'prueba_manejo' | 'entrega' | 'servicio' | 'visita' | 'llamada'
-- estado: 'programado' | 'confirmado' | 'realizado' | 'cancelado' | 'no_asistio'

CREATE INDEX IF NOT EXISTS idx_agenda_fecha ON agenda(fecha, estado);
CREATE INDEX IF NOT EXISTS idx_agenda_vehiculo ON agenda(vehiculo_id);
ALTER TABLE agenda ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role full access agenda"
  ON agenda FOR ALL USING (true);

-- 6. SEGUIMIENTOS (follow-up clientes financiados)
CREATE TABLE IF NOT EXISTS seguimientos (
  id SERIAL PRIMARY KEY,
  cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
  venta_id INTEGER REFERENCES con_ventas(id) ON DELETE SET NULL,
  tipo TEXT DEFAULT 'financiamiento',
  estado TEXT DEFAULT 'pendiente',
  fecha_programada DATE NOT NULL,
  fecha_contacto DATE,
  canal TEXT DEFAULT 'whatsapp',
  notas TEXT,
  mensaje_enviado TEXT,
  vendedor_id UUID REFERENCES vendedores(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- tipo: 'financiamiento' | 'prospecto' | 'posventa' | 'recupero'
-- estado: 'pendiente' | 'contactado' | 'sin_respuesta' | 'resuelto' | 'recupero_iniciado'

CREATE INDEX IF NOT EXISTS idx_seguimientos_fecha ON seguimientos(fecha_programada, estado);
CREATE INDEX IF NOT EXISTS idx_seguimientos_cliente ON seguimientos(cliente_id);
ALTER TABLE seguimientos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role full access seguimientos"
  ON seguimientos FOR ALL USING (true);

-- 7. SPECS GIN index para búsqueda por equipamiento
CREATE INDEX IF NOT EXISTS idx_vehiculos_specs ON vehiculos USING GIN (specs);

-- 8. Verificación final — ejecutar después del resto para confirmar
SELECT
  (SELECT count(*) FROM information_schema.columns
    WHERE table_name='vehiculos' AND column_name='ubicacion') AS col_ubicacion,
  (SELECT count(*) FROM information_schema.columns
    WHERE table_name='vehiculos' AND column_name='estado_recon') AS col_recon,
  (SELECT count(*) FROM information_schema.columns
    WHERE table_name='media' AND column_name='storage_path') AS col_storage_path,
  (SELECT count(*) FROM information_schema.tables
    WHERE table_name='vehiculos_historial') AS tabla_historial,
  (SELECT count(*) FROM information_schema.tables
    WHERE table_name='agenda') AS tabla_agenda,
  (SELECT count(*) FROM information_schema.tables
    WHERE table_name='seguimientos') AS tabla_seguimientos;
-- Resultado esperado: todos los valores = 1
