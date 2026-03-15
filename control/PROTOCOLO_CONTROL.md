# PROTOCOLO DE CONTROL — ROKER NEXUS
*Última actualización: 15/03/2026*
*Propósito: verificación estricta antes de cualquier presentación a gerencia*

---

## 1. ESTRUCTURA DE CARPETAS

```
control/
├── archivos_raw/     ← Copias exactas de los archivos exportados de Flexxus
├── resultados/       ← Outputs del sistema Nexus para comparar
├── presentacion/     ← Archivos finales validados para presentar
└── PROTOCOLO_CONTROL.md  ← Este archivo
```

**Regla de oro:** Antes de presentar cualquier número, verificar contra el archivo raw en `archivos_raw/`.

---

## 2. PROTOCOLO DE EXPORTACIÓN DESDE FLEXXUS

### STOCK — Listado General (por depósito)
- **Ruta Flexxus:** Stock → Listado General
- **Filtros obligatorios:**
  - Depósito: seleccionar UNO por vez (LARREA NUEVO o DEPOSITO SAN JOSE)
  - Super Rubro: TODOS (o MODULOS si solo querés módulos)
  - Fecha: hasta HOY
  - Stock: TODOS
- **Formato exportación:** Archivo Excel (.xlsx) o .XLS (ambos funcionan)
- **Nombre sugerido:** `STOCK_LARREA_YYYYMMDD.xlsx` / `STOCK_SANJOSE_YYYYMMDD.xlsx`
- **⚠️ NUNCA exportar ambos depósitos juntos** — el sistema los necesita separados

### STOCK — Optimización de Stock
- **Ruta Flexxus:** Stock → Optimización de Stock
- **Filtros recomendados:**
  - Período: últimos 6 meses (ajustar según necesidad)
  - Cantidad de días: 30
  - Super Rubro: MODULOS
  - Coeficientes: Mínimo 1.0 / Óptimo 1.2 / Máximo 1.4
  - Incluir: Facturas ✓, Notas Crédito ✓, Notas Débito ✓, Remitos ✓, Ventas no realizadas ✓
- **⚠️ IMPORTANTE:** Si el período es muy corto y un producto tuvo stock=0, su demanda aparece como 0 aunque tenga historial. Usar al menos 3-6 meses de período.

### VENTAS — Planilla por Marca
- **Ruta Flexxus:** Informes → Ventas por Marca
- **Filtros obligatorios:**
  - Desde/Hasta: definir período completo (NO solo "último mes" si querés comparar)
  - Super Rubro: TODOS para balance total, o MODULOS para análisis específico
  - Depósito: TODOS
- **Formato:** Excel (.xlsx)

### COMPRAS — Planilla por Marca
- **Ruta Flexxus:** Informes → Compras por Marca
- **Filtros:** igual que Ventas, definir período completo
- **⚠️ ATENCIÓN:** El archivo se llama "Compras" pero Flexxus puede guardarlo como "Ventas por Marca" — verificar el contenido

### LISTA DE PRECIOS
- **Ruta Flexxus:** (Lista de Precios)
- **Filtros:** Todos, Stock Real, MONEDA PROPIA, Ver precios con IVA ✓
- **⚠️ Este archivo tiene header en FILA 0** (distinto al resto)
- **Usar para:** cruce de precios, márgenes, validación RMA

### RMA — Seguimiento
- **Ruta Flexxus:** RMA → Movimientos de RMA
- **Filtros:** Desde/Hasta período completo, Todos los movimientos
- **⚠️ Exportar período amplio** — si exportás solo el mes perdés historial de casos abiertos
- **⚠️ Algunos registros tienen costo $0** — son items sin precio de compra registrado (artículos viejos previos al nuevo sistema de gestión)

---

## 3. PROTOCOLO DE COLUMNAS FLEXXUS (BUG CONOCIDO)

**Flexxus tiene un bug de desplazamiento de columnas** en los archivos Excel.
El encabezado de columna no siempre coincide con la posición real del dato.

| Archivo | Header en fila | Columna con dato clave | Nota |
|---------|---------------|----------------------|------|
| Listado General (Stock) | 8 | **Col 7** = Stock real | Col 8 dice "Stock" pero tiene ceros |
| Optimización de Stock | 11 | **Col 8** = S.Actual | Col 7 = Demanda Prom |
| Lista de Precios | 0 | **Col 13** = Stock Actual | Header limpio, sin offset |
| Ventas por Marca Resumida | 8 | **Col 7** = Total Vta. | Mismo patrón offset |
| Compras por Marca | 7 | **Col 10** = Cantidad | Mismo bug |
| RMA Seguimiento | 4 | **Col 13** = Costo | Col 5=Código, Col 7=Artículo |

**Protocolo de verificación de columnas:**
1. Abrir archivo raw en Python con `header=None`
2. Recorrer columnas buscando cuál tiene la mayor suma de valores numéricos positivos
3. Comparar contra el total que muestra Flexxus en pantalla (pie de tabla)
4. Si no coincide → ajustar mapping

---

## 4. VALIDACIONES CRUZADAS OBLIGATORIAS

### Antes de importar stock:
- [ ] Total de unidades en archivo = Total que muestra Flexxus en pantalla
- [ ] Depósito correcto en nombre del archivo
- [ ] Fecha del archivo = fecha de exportación (no fecha anterior)
- [ ] ¿Ya existe un snapshot de hoy para este depósito? Si sí → preguntar si reemplazar

### Después de importar stock:
- [ ] Cantidad de SKUs importados coincide con filas del archivo raw
- [ ] Stock total importado coincide con total del archivo
- [ ] Módulos con stock > 0: contar en raw y comparar con sistema

### Validación RMA vs Lista de Precios:
- [ ] Cruzar código RMA con Lista de Precios
- [ ] Si costo RMA = 0 y artículo tiene precio → alertar pérdida no registrada
- [ ] Si costo RMA > P.Comp × 1.5 → posible error manual de carga
- [ ] Si costo RMA = P.Comp → correcto (Flexxus usa costo de compra)

### Validación Compras vs Ventas:
- [ ] Período igual en ambos archivos antes de comparar
- [ ] Total unidades compradas vs vendidas por módulo (rotación)
- [ ] Módulos con ventas >> compras en período → potencial quiebre de stock

---

## 5. REGLAS DE NEGOCIO DOCUMENTADAS

### Tipos de código:
- Código empieza con **letra** → módulo AI-TECH (FR)
- Código empieza con **número** → mecánico / otro proveedor

### Depósitos confirmados:
- **DEPOSITO SAN JOSE** → depósito principal, mayor stock, surte a Larrea
- **LARREA NUEVO** → local al público, stock mínimo, recibe de San José
- **DEP. TRANSITORIO DEV** → devoluciones en tránsito (pendiente analizar)
- **SARMIENTO** → depósito adicional (pendiente confirmar si maneja módulos)

### Fórmula ingreso implícito (auditoría):
```
Ingreso implícito = (Stock_nuevo - Stock_anterior) + Ventas_período
```
Si resultado > 0 → llegó mercadería
Si resultado < 0 → posible pérdida o discrepancia

### Cálculo pérdida por devolución:
```
Pérdida capital    = P.Comp al momento de compra
Pérdida renta      = Lista 1 - P.Comp (ganancia no percibida)
Pérdida total real = Pérdida capital + Pérdida renta
```

### Problema "demanda invisible" por stockout:
Si un SKU tuvo stock = 0 durante parte del período de análisis,
su demanda calculada está SUBESTIMADA. No confiar en la sugerencia
de Flexxus para esos artículos. Revisar historial previo al quiebre.

---

## 6. CHECKLIST PRE-PRESENTACIÓN A GERENCIA

**Ejecutar SIEMPRE antes de mostrar cualquier número:**

- [ ] Verificar que todos los archivos usados son de la misma fecha/período
- [ ] Correr script `verificar_totales.py` contra cada archivo
- [ ] Cruzar números clave con Flexxus en pantalla (capturas de pantalla como respaldo)
- [ ] Verificar que módulos problemáticos (alta devolución) están identificados
- [ ] Confirmar que los números de ventas en ARS están convertidos a USD correctamente
- [ ] Revisar que el período de ventas vs período de compras sea comparable
- [ ] Tener el archivo raw disponible por si preguntan "¿de dónde sale ese número?"

---

## 7. NÚMEROS CLAVE VALIDADOS (al 15/03/2026)

| Métrica | Valor | Fuente | Período |
|---------|-------|--------|---------|
| Módulos % ventas totales | **35.1%** | Ventas por Marca | Feb-Mar 2026 |
| Módulos = categoría #1 | ✅ | Ventas por Marca | Feb-Mar 2026 |
| Unidades módulos vendidas | 28.224 uds | Ventas por Marca | 30 días |
| Stock módulos (valor costo) | U$S 517.620 | Lista de Precios | 15/03/2026 |
| Stock módulos (valor Lista 1) | U$S 826.265 | Lista de Precios | 15/03/2026 |
| Margen promedio módulos | 118% (Lista 1) | Lista de Precios | 15/03/2026 |
| Módulos comprados (2.5 meses) | 57.870 uds | Compras por Marca | Ene-Mar 2026 |
| Pérdida total RMA | U$S 24.708 | RMA + Lista Precios | Ene-Mar 2026 |
| Pérdida RMA módulos | U$S 15.976 | RMA + Lista Precios | Ene-Mar 2026 |
| Proyección pérdida anual | U$S 118.601 | Calculado | Estimación |
| Presupuesto actual módulos | U$S 250.000/mes | Gerencia | Desde dic 2024 |

---

## 8. MÓDULOS EN LISTA DE SEGUIMIENTO

### Alta tasa de devolución (candidatos a revisar con proveedor):
1. SAM A55 OLED C/MARCO — 11 devoluciones, U$S 505 pérdida total
2. SAM A15 OLED C/MARCO — 11 devoluciones, U$S 479 pérdida total
3. SAM A32 OLED 4G — 12 devoluciones, U$S 392 pérdida total
4. SAM A02S/A03/A03S — 34 devoluciones (más frecuente), U$S 308 pérdida total
5. SAM S22 ULTRA — 2 devoluciones pero U$S 151/unidad ⚠️ más caro por unidad

### Demanda con stock en cero (pendiente de pedido):
- SAM A03 CORE/A032 → 519 uds/mes demanda, stock 0
- SAM A04 ORI → 309 uds/mes demanda, stock 0
- XIA REDMI 13C → 201 uds/mes demanda, stock 0
- SAM A05/A055 → 144 uds/mes demanda, stock 0
- MOT G15 → 87 uds/mes demanda, stock 0
*(101 módulos en total con demanda pero sin stock)*
