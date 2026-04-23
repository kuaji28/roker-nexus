-- migration_v7d.sql
-- Agrega precio_lista y precio_lista_ars a vehiculos
-- precio de venta al público (lo que se muestra en ML, catálogo público)
-- si NULL, usar precio_base como fallback

ALTER TABLE vehiculos
  ADD COLUMN IF NOT EXISTS precio_lista NUMERIC,
  ADD COLUMN IF NOT EXISTS precio_lista_ars NUMERIC;

-- precio_lista: precio de venta al público en USD (visible para clientes)
-- precio_lista_ars: opcional, precio directo en ARS si se quiere fijar manualmente
