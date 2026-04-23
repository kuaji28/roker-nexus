# Plan Maestro de Migración — GH Cars React vs Streamlit
> Generado: 23/04/2026 — Auditoría exhaustiva feature-por-feature

## RESUMEN EJECUTIVO

| # | Página Streamlit | React | Completitud | Prioridad |
|---|---|---|---|---|
| 01 | Catálogo | `Catalogo.jsx` | 55% | Alta |
| 02 | Ingreso | `Ingreso.jsx` | 45% | Alta |
| 03 | Ventas | `Ventas.jsx` | 40% | Alta |
| 04 | Detalle | `Detalle.jsx` | 60% | Alta |
| 05 | Documentación | Placeholder | 5% | Alta |
| 06 | Reportes | `Reportes.jsx` | 35% | Media |
| 07 | Clientes | `Clientes.jsx` | 55% | Media |
| 08 | Consignación | AUSENTE | 0% | Media |
| 09 | Buscar Para Cliente | `Buscar.jsx` | 50% | Media |
| 10 | Vendedores | `Vendedores.jsx` | 50% | Baja |
| 11 | Gastos | `Gastos.jsx` | 70% | Media |
| 12 | Leads | `Leads.jsx` | 65% | Media |
| 13 | Rotación | `Rotacion.jsx` | 75% | Baja |
| 14 | Catálogo Público | AUSENTE | 0% | Media |
| 15 | Panel Vendedor | AUSENTE | 0% | Baja |
| 16 | Dashboard Gerente | `Gerente.jsx` | 40% | Media |
| 17 | Cobranza | `Cobranza.jsx` | 40% | Media |

---

## BUGS CRÍTICOS (arreglar primero)

1. `Catalogo.jsx:30` — TC hardcodeado `const TC = 1415` — debe usar `useTc()`
2. `Ventas.jsx` — Solo acepta vehículos `disponible`, no acepta `señado`
3. `Ventas.jsx` — No cancela reservas activas al confirmar venta
4. `Cobranza.jsx` — `pagarCuota()` no guarda forma_cobro/moneda/TC/monto real
5. `supabase.js:382` — fecha_primera_cuota sin normalizar a medianoche local → bug de fecha

---

## BLOQUE 1 — Crítico

- [ ] Tab Docs en Detalle: 6 secciones (verificación policial, VTV, dominio, docs físicos, transferencia, multas)
- [ ] Fix TC dinámico en Catálogo (reemplazar hardcoded 1415)
- [ ] Ventas: incluir vehículos señados en selección
- [ ] Ventas: cancelar reservas activas al confirmar venta
- [ ] Cobranza: tab cuotas próximas (próximos N días), modal pago con metadatos

## BLOQUE 2 — Importante (visible al usuario)

- [ ] Catálogo: filtros numéricos (año, km, precio)
- [ ] Catálogo: edición rápida inline (estado, km, precio)
- [ ] Catálogo: TC dinámico (bug fix)
- [ ] Catálogo: info señas/comprador en tarjeta
- [ ] Catálogo: generador link público
- [ ] Ingreso: equipamiento completo (20+ campos: climatizador, multimedia, airbags, etc.)
- [ ] Ingreso: specs por tipo (moto, cuatriciclo, moto_de_agua)
- [ ] Ingreso: borradores (guardar y retomar)
- [ ] Ingreso: origen de operación (compra directa vs parte de pago)
- [ ] Vendedores: campos faltantes (DNI, WhatsApp, rol, comisión%, notas, telegram_chat_id)
- [ ] Leads: semáforo de días (verde<7 / amarillo<14 / naranja<30 / rojo>=30)
- [ ] Leads: filtros por vendedor y canal
- [ ] Leads: tab Resumen (breakdown canal/vendedor, tasa conversión)
- [ ] Clientes: tab Deudores (cuotas pendientes + cobro inline + WA recordatorio)
- [ ] Clientes: tab Notificaciones (Evolution API / WA masivo)
- [ ] Clientes: toggle solo activos, link WA directo, historial compras

## BLOQUE 3 — IA y automatizaciones

- [ ] Ingreso: tasación ArgAutos (endpoint /ai/tasacion)
- [ ] Ingreso: OCR cédula azul con detección de tipo
- [ ] Ventas: OCR DNI del comprador
- [ ] Buscar: IA ranking vehículos (/ai/ranking-vehiculos)
- [ ] Buscar: generador presupuesto para WA
- [ ] Buscar: texto libre de preferencias interpretado por IA
- [ ] Detalle: botón Tasar en header

## BLOQUE 4 — Pantallas nuevas

- [ ] `/doc` — Documentación global (alertas VTV + transferencias)
- [ ] `/consignacion` — Screen completa (3 tabs) + tabla en Supabase
- [ ] `/c/:token` — Catálogo público sin auth (modo cliente / modo vendedor)
- [ ] `/mi-panel` — Panel del vendedor logueado

## BLOQUE 5 — Análisis y reportes

- [ ] Reportes: selector de período (desde/hasta)
- [ ] Reportes: Tab Cuotas por período
- [ ] Reportes: Tab Stock pivot tipo×estado
- [ ] Reportes: Tab Pipeline (embudo de conversión)
- [ ] Rotación: scatter chart precio vs días (recharts)
- [ ] Gerente: gráfico bar por tipo, pie por estado, selector período
- [ ] Cobranza: proyección 30 días, top 5 deudores

---

## ESTADO CAPA IA (api.js)

### Implementados ✅
- `/ai/ocr-cedula` — OCR cédula verde
- `/ai/ocr-documento` — OCR DNI
- `/ai/completar-specs` — specs del vehículo
- `/ai/sugerir-precio` — sugerencia de precio
- `/ai/analizar-fotos` — análisis fotos Gemini
- `/ai/descripcion-ml` — descripción ML
- `/ai/mensaje-wsp` — mensaje WhatsApp

### Pendientes ❌
- `/ai/tasacion` — ArgAutos scraping + Gemini
- `/ai/ocr-cedula-azul` — con detección de tipo
- `/ai/ranking-vehiculos` — top 3 con score para cliente
- `/ai/presupuesto-wsp` — generador presupuesto WhatsApp

