-- migration_v7b.sql
-- Agrega stage, canal_origen, tiempo_respuesta_min, fecha_proximo_contacto, vendedor_id a prospectos
-- Ejecutar en Supabase SQL Editor

ALTER TABLE prospectos
  ADD COLUMN IF NOT EXISTS stage TEXT DEFAULT 'nuevo',
  -- valores: 'nuevo' | 'en_contacto' | 'con_propuesta' | 'cerrado' | 'perdido'
  ADD COLUMN IF NOT EXISTS canal_origen TEXT DEFAULT 'whatsapp',
  -- valores: 'mercadolibre' | 'instagram' | 'facebook' | 'whatsapp' | 'referido' | 'showroom' | 'web'
  ADD COLUMN IF NOT EXISTS tiempo_respuesta_min INTEGER,
  ADD COLUMN IF NOT EXISTS fecha_proximo_contacto DATE;

-- Nota: vendedor_id ya existe en prospectos como FK a vendedores(id).
-- Si no existe, descomentar la línea siguiente:
-- ALTER TABLE prospectos ADD COLUMN IF NOT EXISTS vendedor_id UUID REFERENCES vendedores(id);

-- Migrar valores de estado existentes a stage
-- Los estados anteriores: nuevo, contactado, visita_agendada, visita_realizada, convertido, descartado
UPDATE prospectos SET stage = 'nuevo'         WHERE estado = 'nuevo'            AND stage IS NULL;
UPDATE prospectos SET stage = 'en_contacto'   WHERE estado = 'contactado'       AND stage IS NULL;
UPDATE prospectos SET stage = 'con_propuesta' WHERE estado IN ('visita_agendada','visita_realizada') AND stage IS NULL;
UPDATE prospectos SET stage = 'cerrado'       WHERE estado = 'convertido'       AND stage IS NULL;
UPDATE prospectos SET stage = 'perdido'       WHERE estado = 'descartado'       AND stage IS NULL;

-- Para los que queden NULL, asignar 'nuevo'
UPDATE prospectos SET stage = 'nuevo' WHERE stage IS NULL;

-- Agregar constraint
ALTER TABLE prospectos
  ADD CONSTRAINT prospectos_stage_check
    CHECK (stage IN ('nuevo','en_contacto','con_propuesta','cerrado','perdido'));

ALTER TABLE prospectos
  ADD CONSTRAINT prospectos_canal_origen_check
    CHECK (canal_origen IN ('mercadolibre','instagram','facebook','whatsapp','referido','showroom','web'));
