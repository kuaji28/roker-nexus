# Metodología de Cálculo — Pedidos y Demanda

## Fuentes de datos

| Dato | Archivo |
|------|---------|
| Demanda histórica | `ventas/por_mes/YYYY-MM_ventas.xlsx` o `ventas/acumulado/` |
| Stock actual | `stock/san_jose/SJ_stock_YYYY-MM-DD.xlsx` + depósitos |
| Stock entrante (container) | Archivo del container/pedido previo |
| Precio unitario | `precios/lista_precios_YYYY-MM-DD.xlsx` |
| Cotización proveedor | `pedidos/cotizaciones/` |

---

## Paso 1 — Demanda diaria

```
dem_diaria = total_unidades_vendidas ÷ días_del_período
dem_total  = dem_diaria_MEC + dem_diaria_FR (mismo modelo)
```

**Regla crítica:** Cada código Mecánico se cruza SOLO con su FR equivalente específico.
NO usar códigos FR genéricos que cubran múltiples modelos para un solo MEC.

### Mapeo FR-Mecánico confirmado (módulos principales)

| Código MEC | Modelo | FR equivalente | Tecnología |
|-----------|--------|---------------|-----------|
| 2401251379 | SAM A02S/A03/A03S/A04E Universal | MSAMA02S | AMM |
| 2401050043 | SAM A12 Universal | MSAMA12SM | AMM |
| 2401231950 | SAM A03 Core | LA03CROLB | AMM |
| 2404090163 | SAM A03 C/MARCO | MSAMA03CM | AMM |
| 2401250109 | SAM A21S | MSAMA21SSM | AMM |
| 2401251874 | SAM A21S C/MARCO | MSAMA21SSCM | AMM |
| 2408230013 | MOT G24/G24 Power/E14/G04 | MMOTG24 | AMM |
| 2401251698 | MOT G13/G23/G34/G53 | MMOTG13 | AMM |
| 2401251682 | SAM A22 5G | MSAMA22 | AMM |
| 2403090035 | SAM A13 4G / M13 / A23 | MSAMA13 | AMM |

> ⚠️ OLED ≠ AMM — son calidades distintas, precios distintos, no son sustitutos directos.

### Corrección por demanda invisible (stockouts)

Si un producto estuvo sin stock X días del período:
```
dem_real = dem_observada × (días_total / días_con_stock)
```
Para identificar días sin stock: usar ventas mes a mes — los meses con 0 ventas = probable stockout.

---

## Paso 2 — Stock disponible

```python
fr_activo = stk_SJ + stk_LAR + stk_SAR + stk_FML   # NUNCA incluir MER/RMA/DTM/DML
stk_total = stk_mec + fr_activo + fr_container
```

---

## Paso 3 — Cantidad a pedir

```
qty = máx(0, días_cobertura × dem_total − stk_total)
usd = qty × precio_usd_mecánico
```

---

## Regla de los 20 días (cuándo NO pedir)

```
días_FR = fr_activo ÷ dem_total
Si días_FR ≥ 20  →  ELIMINAR del pedido (FR lo cubre)
Si días_FR < 20  →  PEDIR
```

---

## Análisis mensual de ventas — reglas (validadas 17/03/2026)

### Ventas negativas en la planilla mensual
Son normales — corresponden a devoluciones (NCA, NCB, RE revertidos). No son errores.
Para calcular ventas reales positivas: `df[df['total_unid'] > 0]`

### Interpretación de spikes y crashes
- **Spike de ventas** en un mes → verificar si coincide con entrada de stock nuevo (container/pedido)
- **Crash de ventas** en un mes → verificar si hubo stockout (stock=0 ese período). Si sí → la "demanda" está subestimada
- **Liquidación** = spike enorme seguido de crash = todo el stock vendido en un mes + nada queda para el siguiente

### Precaución con dem_corr en modelos con stockouts recientes
Si un modelo tuvo stock=0 por 1+ meses → su dem_corr está subestimada.
Usar `dem_corr = promedio solo de meses con ventas > 0.5u/día`.
Para modelos en liquidación (MSAMA02S en ene-2026): excluir ese mes del promedio (inflado artificialmente).

## Sistema de pedidos rolling (semanal)

**Lead time aéreo:** ~22 días promedio (según Diego).

**Punto de reorden:**
```
ROP = dem_diaria × lead_time = dem_diaria × 22
Cuando stk_total ≤ ROP → incluir en pedido semanal
```

**Cantidad rolling:**
```
qty = dem_diaria × (lead_time + cobertura_deseada) − stk_total
     = dem_diaria × (22 + 30) − stk_total   [con cobertura de 30 días]
```

**Proceso semanal (cada lunes/martes):**
1. Descargar stock actualizado → `stock/san_jose/SJ_stock_YYYY-MM-DD.xlsx`
2. Descargar ventas del mes en curso → `ventas/por_mes/YYYY-MM_ventas.xlsx`
3. Calcular dem_diaria con los últimos 30 días (más preciso que 165 días para modelos en tendencia)
4. Filtrar productos con `stk_total ≤ ROP`
5. Calcular qty para cada uno → generar pedido
6. Enviar a Mecánico

---

## Coberturas y presupuesto orientativo (59 items, demanda corregida)

| Cobertura | Unidades | USD | % del budget $300K |
|-----------|----------|-----|-------------------|
| 30 días | ~12.250 | ~U$S 75K | 25% |
| 45 días | ~19.200 | ~U$S 117K | 39% |
| 60 días | ~26.200 | ~U$S 159K | 53% |
| **90 días** | **~40.200** | **~U$S 244K** | **81%** ← recomendado |
| 120 días | ~54.200 | ~U$S 329K | 110% (excede budget) |

**Recomendación:** 90 días usa el 81% del budget y da colchón para un pedido semanal sin apuros.

---

## Grupos Marco / Sin Marco

16 grupos donde C/MARCO y S/MARCO comparten el mismo modelo base.
Si una variante tiene alto FR activo → puede reducir la qty a pedir de la otra.

---

## Slow movers / Dead stock

**Disparadores:**
- Cobertura > 90 días con demanda actual
- Ventas < 20% de lo esperado en el período
- Stock nuevo llegó y en 2 semanas no se movió casi nada

**Proceso:**
1. Verificar historial (RE/FA/RI) → ¿producto nuevo o en caída?
2. Calcular precio piso = P.Comp × (1 + margen mínimo aceptable)
3. Proponer descuento escalonado: -10% sem1 → -20% sem2 → -30% si persiste
4. Evaluar transferencia a LARREA para más exposición

---

## Reglas de comparación FR vs Mecánico

Al presentar cualquier cruce FR vs Mecánico, siempre mostrar:
- **Código** del FR y del Mecánico
- **Descripción completa** de ambos
- **Motivo del cruce** (por qué se vincularon)
- **Con marco / sin marco** — variante exacta
- **Calidad** — OLED vs AMM vs otras sub-calidades (un precio más bajo ≠ equivalencia)
