# EL CELU — Contexto de empresa

## Qué hace
Venta mayorista y minorista de accesorios y repuestos para celulares en Argentina. Especialidad: módulos (pantallas LCD/OLED) de Samsung, Motorola, Xiaomi, iPhone. También: accesorios, cables, auriculares, smartwatches, herramientas de reparación.

## Estructura de depósitos
| Depósito | Tipo | Rol |
|----------|------|-----|
| DEPOSITO SAN JOSE | Principal/Hub | Mayor stock, surte a todos los demás |
| LARREA NUEVO | Local al público | ~6km de SAN JOSE, flete externo privado |
| DEPOSITO SARMIENTO NUEVO2 | Local/depósito | Maneja módulos también |
| DEPOSITO FULL ML | MercadoLibre Full | Logística de ML |
| DEPÓSITO MERCADO LIBRE | ML estándar | Canal ML |
| DEPOSITO MUESTRAS | Muestras | Artículos de exhibición |
| USO INTERNO | Interno | Consumo propio |
| DEP. TRANSITORIO DEV ML | Devoluciones ML | Pendiente analizar |
| DEPOSITO TRANS. DE RMA | RMA en tránsito | Devoluciones en proceso |

## Software
- **Flexxus ERP**: stock, ventas, compras, RMA, remitos. Sistema lento, acceso remoto.
- **Roker Nexus**: sistema propio en construcción (Streamlit + Supabase).
- **MercadoLibre**: canal de venta online importante.

## Proveedores principales
- **AI-TECH (AITECH)**: proveedor principal de módulos. China. Códigos empiezan con letra (AIFR...). Fabrica en Guangzhou. Cotización en RMB. 15 días desde Chile para armar pedido.
- **GUANGZHOU LANGYI TECHNOLOGY CO., LTD**: proveedor de módulos (visto en historial).
- **DMW BAIRENDA LIMITED**: proveedor (visto en historial).
- **INTER BROKERS SRL**: proveedor local.

## Canales de venta
- **Mayorista**: Lista 1 (precio base, más bajo). A veces con descuento 5% por cliente.
- **Minorista / mostrador**: Listas 2, 3, 5 (más margen que mayorista).
- **MercadoLibre**: Lista 4 (precio ya incluye comisión ML).
- **Presupuesto**: Lista 4 o variable.

## Problemáticas identificadas
1. **Presupuesto cortado**: desde diciembre 2024, de niveles anteriores a U$S 250k/mes. Causó stockout en 101 módulos con demanda activa.
2. **Demanda invisible**: productos con stock=0 en Flexxus muestran demanda=0 → subestima reposición necesaria.
3. **Grey zone remitos**: TODOS los 504 ítems de remitos internos tienen Entregada=0 → mercadería puede perderse en tránsito SAN JOSE → LARREA sin detección.
4. **RMA sin control de precios**: Pablo/Mariano pueden modificar precio en RMA. Sistema debería bloquearlo.
5. **Movimientos eliminados**: históricamente desaparecieron movimientos del sistema Flexxus (no se puede demostrar ahora).
6. **Ajustes MD sin justificación**: ajustes de inventario por Lorena, Ezequiel, Matias — algunos sospechosos.
7. **Acceso limitado de Roker**: no tiene acceso a todos los depósitos, no puede ver Venta x Artículo x Mes fácilmente.

## Flujo de pedidos a proveedor
1. Cotización (solicitud de precio) → 15 días para armar desde Chile
2. Confirmación del pedido
3. En vuelo (enviado desde origen)
4. Ingresado (llegó a Argentina / SAN JOSE)
Roker puede agregar/modificar durante los 15 días de armado.

## Protocolo de análisis de órdenes de compra

### Fuentes de stock a consultar SIEMPRE (las 4 en conjunto)
1. **Stock en depósitos**: SJ_stock, LAR_stock, SAR_stock (+ DTM, RMA, MUE, FML)
2. **FR Activo**: mercadería en tránsito por barco (campo "FR Activo" en archivos de análisis `pedidos/analisis/`)
3. **Orden 39 / 109 BOX**: lo que ya está pedido en la orden anterior (`pedidos/ordenes/109_BOX_MODIFICADO_*.xlsx`). Ojo: verificar si tiene items marcados CANCELAR.
4. **Orden 40**: lo que ya está en la orden actual (`pedidos/ordenes/ORDEN_40_*.xlsx`)

### Regla clave: productos nuevos sin SKU
**NUNCA excluir un producto de la orden por no tener SKU en la lista de precios.**
Si un producto es nuevo o no figura en la lista de precios local, igual se agrega a la orden con:
- SKU en blanco (columna B vacía)
- Nombre y especificación correctos
- Cantidad y precio en 0 (el proveedor cotiza)
El proveedor confirma disponibilidad y precio. Excluir un producto nuevo es un error operativo.

### Criterio para agregar a la orden
- ❌ **Agregar**: sin stock en depósitos + sin FR activo + no está en orden 39 ni 40
- ⚠️ **Agregar igual**: stock muy bajo (< 20-30 unidades para modelos de alta rotación), o spec incorrecta en órdenes existentes (ej: pidieron c/marco pero el cliente quiere s/marco)
- ✅ **No agregar**: stock suficiente O FR activo significativo O bien cubierto en O39/O40

### Formato de la orden (invoice de AITECH)
| Col | Campo | Ejemplo |
|-----|-------|---------|
| A | Brand | SA / M / X / IPH |
| B | SKU (código MEC) | 2401252342 (o vacío si nuevo) |
| C | Modelo Universal | SA A32 4G, SA A325 |
| D | Modelo Sticker (descripción) | SAM A32 AMM 4G W/F MECANICO |
| E | Specification | LCD Complete / LCD Complete+Frame |
| F | Type | AMP / AMM / ASS / T2O |
| G | Quality | OLED / 6.36 inch / INCELL / HIGH COPY |
| H | Color | Black |
| I | QTY | cantidad |
| J | PRICE | precio FOB en USD |
| K | Total | =I*J |

Al agregar modelos faltantes, siempre añadir **al final** (antes del TOTAL) con una **fila en blanco como separador** para que sean fácilmente diferenciables del cuerpo original de la orden.

## Tipo de cambio (al 15/03/2026)
- USD/ARS: 1.415 (dólar blue) — auto-fetch dolarapi.com, override manual
- USD/RMB: 6.9 (tasa del cambista) — siempre manual

## Migración de códigos (agosto-septiembre 2025)
**Contexto crítico para el análisis de stock:**

Hasta agosto/septiembre 2025, todos los proveedores usaban códigos genéricos numéricos (ej: 2401251379). A partir de esa fecha se empezó a separar por proveedor:
- Productos AITECH → código nuevo empieza con letra (MSAMA02S, AICP..., etc.)
- Mecánicos/otros → código original numérico o con punto

**Efecto en el stock:**
- El mismo módulo físico puede aparecer bajo DOS códigos distintos en Flexxus
- Stock fragmentado entre código viejo y código nuevo hasta que se complete la migración
- El inventario de diciembre 2025 dejó remanentes sin migrar
- Los ajustes CS "STOCK ACTUAL" de enero 2026 en adelante son en parte migraciones de código

**Ejemplo documentado:**
- Código viejo: 2401251379 (SAM A02S mecánico)
- Código nuevo: MSAMA02S (SAM A02S AITECH)
- EFIRMAPAZ migró 20 unidades el 26/01/2026 con CS 0000-00212070

**Impacto en análisis de stockouts:**
Los "101 módulos con stock=0" pueden estar subestimados o sobreestimados según qué código se mire.
El sistema DEBE consolidar aliases para dar stock real por producto físico.
