# 📁 pedidos/

## Estructura
```
pedidos/
├── cotizaciones/    ← Cotizaciones recibidas de Mecánico / AI-TECH
└── ordenes/         ← Pedidos armados y listos para enviar al proveedor
```

## Convención de nombre
- Cotización: `PROVEEDOR_NRO_YYYY-MM-DD.xlsx`
  Ejemplo: `MECANICO_039_2026-03-05.xlsx`
- Orden: `PEDIDO_NRO_YYYY-MM-DD.xlsx`
  Ejemplo: `PEDIDO_039_2026-03-17.xlsx`

## Pedidos activos (al 17/03/2026)
| # | Proveedor | Items | USD | Estado | Notas |
|---|-----------|-------|-----|--------|-------|
| 039 | Mecánico | 59 items a definir | ~$120-250K | 🔄 EN ANÁLISIS | Presupuesto $300K, cobertura a confirmar |

## Reglas
- Proveedor activo: **SOLO MECÁNICO** (FR/AITECH suspendido por Diego)
- Regla de reposición: dem × días_cobertura − stock_actual − stock_FR_activo
- FR activo = SJ + LAR + SAR + FML (NO incluir MER, RMA, DTM)
