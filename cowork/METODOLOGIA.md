# 📐 METODOLOGÍA — Cómo calculo el pedido

> Este documento explica paso a paso cómo se arma cada pedido de módulos.
> Sirve para que Roker pueda validar los números frente a Mariano o Pablo.

---

## FUENTES DE DATOS

| Dato | Archivo Flexxus | Dónde descargarlo |
|------|----------------|-------------------|
| Demanda histórica | Planilla de Ventas por Marca Resumida | Ventas → Planilla por Marca Resumida |
| Stock actual | Planilla de Stock (por depósito) | Stock → Planilla de Stock → elegir depósito |
| Stock entrante (container/pedido previo) | Archivo del container/pedido | Externo (proveedor) |
| Precio unitario | Lista de Precios | Precios → Lista de Precios |
| Cotización proveedor | Cotización Mecánico | Recibido de proveedor |

---

## PASO 1 — CALCULAR DEMANDA DIARIA

**Fórmula:**
```
dem_diaria = total_unidades_vendidas ÷ días_del_período
```

**Ejemplo (A02S Universal):**
- Ventas MEC (2401251379): 10.423 uds en 165 días = **63.2 uds/día**
- Ventas FR (MSAMA02S): 12.202 uds en 165 días = **74.0 uds/día**
- **dem_total = 63.2 + 74.0 = 137.2 uds/día**

### ⚠️ PROBLEMA: Demanda subestimada por stockouts
Si un producto estuvo sin stock X días, esos días muestra 0 ventas.
Ejemplo: A02S sin stock ~75 días de los 165 → dem_real ≈ 137 × (165/90) ≈ **250/día**

**Corrección posible:** descargar ventas mes a mes → calcular dem_diaria solo en los meses que tuvo stock.

### ⚠️ REGLA CRÍTICA: No mezclar FR genérico con MEC específico
- El código MSAMA02S ("A02S/A03/A03S/A04E Universal") cubre CUATRO modelos distintos
- Su demanda NO puede asignarse entera a un solo código Mecánico
- Cada MEC se cruza SOLO con su FR equivalente específico

| Código MEC | Descripción | FR equivalente correcto |
|-----------|-------------|------------------------|
| 2401251379 | A02S Universal s/marco | MSAMA02S |
| 2401050043 | A12 Universal s/marco | MSAMA12SM |
| 2401231950 | A03 Core s/marco | LA03CROLB |
| 2404090163 | A03 C/MARCO | MSAMA03CM |
| 2401250109 | A21S s/marco | MSAMA21SSM |
| 2408230013 | MOT G24 | MMOTG24 |

---

## PASO 2 — STOCK DISPONIBLE

**Stock activo (FR) = depósitos que cuentan:**
```
fr_activo = SJ + LAR + SAR + FML
```
**NO incluir:** MER (mermas), RMA (devoluciones), DTM (tránsito), DML (segundo ML)

**Stock total disponible:**
```
stk_total = stk_mec + fr_activo + fr_container
```

---

## PASO 3 — CALCULAR CANTIDAD A PEDIR

**Fórmula:**
```
qty_a_pedir = máx(0 , días_cobertura × dem_diaria − stk_total)
```

**Ejemplo (A02S, 60 días cobertura):**
```
qty = máx(0, 60 × 137.2 − 937) = máx(0, 8.232 − 937) = 7.295 uds
```

**Costo:**
```
usd = qty × precio_usd_mecánico
```

---

## PASO 4 — REGLA DE LOS 20 DÍAS (cuándo NO pedir)

Si el FR activo ya cubre ≥20 días de demanda → **no pedir Mecánico** (el FR lo cubre).

```
días_fr = fr_activo ÷ dem_diaria
Si días_fr ≥ 20 → ELIMINAR del pedido
Si días_fr < 20 → PEDIR
```

---

## SISTEMA DE PEDIDOS ROLLING (semanal)

### Concepto
En vez de un pedido grande cada 2-3 meses, hacer **pedidos chicos cada 7-10 días**.
Cada pedido cubre exactamente los productos que van a quedarse sin stock en los próximos ~22 días (lead time del proveedor).

### Punto de reorden
```
reorder_point = dem_diaria × lead_time_días
```
Ejemplo (A02S, lead time 22 días):
```
reorder_point = 137 × 22 = 3.014 uds
```
Cuando `stk_total ≤ 3.014` → incluir en el próximo pedido semanal.

### Cantidad a pedir (rolling)
```
qty = dem_diaria × (lead_time + días_cobertura_deseados) − stk_total
```
Con lead_time=22 y cobertura deseada=30:
```
qty = dem_diaria × 52 − stk_total
```

### Proceso semanal (cada lunes o martes)
1. Descargar stock actualizado (SJ + LAR + FML) → `stock/san_jose/SJ_stock_YYYY-MM-DD.xlsx`
2. Descargar ventas del mes en curso → `ventas/por_mes/YYYY-MM_ventas.xlsx`
3. Actualizar dem_diaria con los datos más recientes (últimos 30 días > últimos 165 días para modelos con tendencia)
4. Filtrar productos con `stk_total ≤ reorder_point`
5. Calcular qty para cada uno
6. Enviar pedido a Mecánico

---

## COMPARACIÓN: Roker vs. Mariano

| | **Roker (sistema Nexus)** | **Mariano (manual)** |
|--|--------------------------|----------------------|
| Fuente de demanda | Ventas Flexxus 165 días (FR + MEC combinado) | Posiblemente solo ventas internas o estimado manual |
| Corrección stockouts | Pendiente (necesita ventas mes a mes) | Desconocido |
| Stock disponible | SJ + LAR + SAR + FML + container FR | Posiblemente solo SJ |
| Automatización | Semi-automático (con Python) | Manual en Excel |
| Transparencia | Auditable — cada número tiene fuente | Caja negra |
| Frecuencia | Rolling semanal (propuesto) | A demanda |

---

## DATOS QUE HACEN FALTA PARA MEJORAR EL ANÁLISIS

| Dato faltante | Para qué sirve | Cómo obtenerlo |
|--------------|---------------|----------------|
| Ventas mes a mes | Detectar tendencias, corregir stockouts | Descargar de Flexxus por mes |
| Historial de artículo por producto | Saber exactamente cuándo hubo stockout | Flexxus → Listado Histórico de Artículos |
| Lead time real por pedido | Calibrar punto de reorden | Registro de fechas de pedido vs recepción |
| Año de lanzamiento del celular | Detectar modelos en caída de demanda | Google / GSMArena |
