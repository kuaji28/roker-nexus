# Memory — Roker Nexus

## Yo
**Roker** (kuaji28@gmail.com) — trabaja de forma externa para EL CELU, empresa de venta de accesorios y repuestos de celulares en Argentina. Ex-empleado reconvocado porque no pudieron reemplazar su forma de hacer los pedidos. Maneja módulos (pantallas) de Samsung, Motorola, Xiaomi y otros.

## Personas clave
| Quién | Rol | Notas |
|-------|-----|-------|
| **Diego** | Dueño (co-owner) | Roker se maneja más con él. Destinatario principal de presentaciones. |
| **Walter** | Dueño (co-owner) | Segundo dueño. Recibe las presentaciones con Diego. |
| **Pablo** | Gerente | Puede estar mostrando números selectivos. Tiene acceso Flexxus amplio. |
| **Mariano** | Sub-gerente | Ídem Pablo. Posible zona gris en manejo de datos. |
| **Lorena Rodriguez** | Staff | Hace ajustes MD en Flexxus (inventario). |
| **Ezequiel Firmapaz** | Staff | Hace ajustes MD en Flexxus. |
| **Matias Toledano** | Staff | Hace ajustes MD en Flexxus. |
| **Rocio Sisco** | Vendedora | Vende desde LARREA. |
| **GGARCIA** | Staff | Maneja devoluciones RMA en el sistema. |
| **LTROVATO** | Usuario Flexxus | Aparece en facturas de LARREA. |

## Términos clave
| Término | Significado |
|---------|-------------|
| **Módulos** | Pantallas de celular (display + touch). Categoría #1 en ventas (35%). |
| **AI-TECH / AITECH** | Proveedor principal de módulos. Códigos empiezan con letra (ej: AIFR...) |
| **Mecánico** | Módulo de otro proveedor. Código empieza con número. |
| **Flexxus** | ERP argentino usado por EL CELU para stock, ventas, compras, RMA. |
| **SAN JOSE** | Depósito principal/hub. Mayor stock. Surte a LARREA y SARMIENTO. |
| **LARREA** | Local al público (~6km de SAN JOSE). Recibe por flete externo. |
| **SARMIENTO** | Depósito adicional / local. |
| **DEP. FULL ML** | Depósito MercadoLibre Full (logística de ML). |
| **DEP. MERCADO LIBRE** | Segundo depósito ML. |
| **DEP. TRANSITORIO DEV** | Devoluciones en tránsito (pendiente analizar). |
| **Lista 1** | Precio MAYORISTA (el más bajo, base). |
| **Lista 4** | Precio MercadoLibre (incluye comisión ML). |
| **P.Comp** | Precio de compra (costo). Relativamente estable. |
| **RMA** | Devoluciones de clientes. Pérdida = capital + renta no percibida. |
| **Remito interno** | Transferencia SAN JOSE → LARREA/SARMIENTO por flete externo. |
| **MD** | Movimiento de depósito / ajuste de inventario en Flexxus. |
| **RE** | Remito de entrada (ingreso de mercadería). |
| **RI** | Remito interno (transferencia entre depósitos). |
| **FA/FB** | Factura A / Factura B (ventas). |
| **Demanda invisible** | Producto con stock=0 muestra demanda=0 en Flexxus → subestima necesidad. |
| **Lista Negra** | Módulos obsoletos definitivos — no reordenar. |
| **RMB** | Yuan chino. Conversión manual. Hoy: 1 USD = 6.9 RMB. |
| **Dólar blue** | Tipo de cambio informal ARG. Hoy: 1 USD = $1.415 ARS. Auto-fetch dolarapi.com. |
| **Auditoría silenciosa** | Verificación independiente de datos para presentar a Walter/Diego sin pasar por Pablo/Mariano. |

## Proyectos
| Nombre | Descripción |
|--------|-------------|
| **Roker Nexus** | Sistema de gestión inventario en Streamlit + Supabase. En producción en Streamlit Cloud. |
| **Bot Telegram** | Bot para consultas móviles de stock, precios, pedidos, tipo de cambio. Pendiente construir. |
| **Auditoría v1** | Presentación para Walter y Diego: déficit presupuesto módulos, pérdidas RMA, grey zone remitos. |
| **Guía Operativa** | Documentación paso a paso con capturas Flexxus para delegar tareas. |

## Números validados (al 15/03/2026)
- Módulos = 35.1% de ventas totales (categoría #1)
- 28.224 unidades módulos vendidas en 30 días
- Stock módulos a costo: U$S 517.620 | a Lista 1: U$S 826.265
- Margen promedio módulos: 118% (sobre Lista 1)
- Pérdida total RMA (2.5 meses): U$S 24.708 → proyección anual U$S 118.601
- Presupuesto actual módulos: U$S 250.000/mes (recortado desde dic 2024)
- 101 módulos con demanda>0 y stock=0 (stockout por presupuesto)
- Remitos internos: 504 ítems, TODOS con Entregada=0 (nunca confirmados)
- Último inventario: diciembre 2025 → base para historial

## Mapa de depósitos relevado (15/03/2026)
| Depósito | Código | SKUs | Unidades | Notas |
|----------|--------|------|----------|-------|
| SAN JOSE | SJ | 1.948 | 639.078 | Hub. Módulos: 360 SKUs / 51.687 uds |
| LARREA | LAR | pendiente | pendiente | Local público |
| SARMIENTO | SAR | — | ~3 módulos | Solo accesorios |
| FULL ML | FML | 79 | 9.592 | Stock protegido ML Fulfillment |
| DEP. ML | DML | 79 | 9.592 | Idéntico a FML (mismo export posible) |
| MERMAS GENERALES | MER | — | 18.644 | Incl. 1.862 módulos — parte migración |
| DEP. TRANSITORIO RMA | RMA | — | 1.080 | Parlantes defecto fábrica |
| MUESTRAS | MUE | — | 990 | Muestras exhibición |

## MSAMA02S (SAM A02S/A03/A04E) — módulo top ventas
- Migración confirmada: CS 212070+212071 el 26/01/2026 por EFIRMAPAZ (limpio)
- Enero 2026: liquidación total — 6.313 → -8 (FLOTOM SAS compró 1.884 uds)
- Stock actual 15/03: 7 uds totales — CRÍTICO
- Patrón histórico: vende en compromiso (457 filas saldo negativo en historial)

## Problema naming Flexxus — RESUELTO con etiquetar.py
- Flexxus: siempre genera "Planilla de Stock_DD-MM-YYYY HH-MM-SS.xlsx" sin importar depósito
- El archivo no dice adentro qué depósito es
- Solución: script etiquetar.py — renombra + inyecta fila amarilla en el xlsx
- Convención: [CODIGO]_stock_YYYY-MM-DD.xlsx (ej: SJ_stock_2026-03-15.xlsx)
- Carpeta destino: exports_flexxus/

## Preferencias del sistema
- Precios en USD como moneda base
- Mostrar siempre: P.Comp / Lista 1 / Lista 4 (ML)
- Tipo de cambio USD: auto-fetch dolarapi.com + override manual
- Tipo de cambio RMB: manual siempre (cambista propio)
- Alertas: stock crítico, variación inexplicada, tránsito >48hs sin confirmar
- Interfaz: Streamlit (web) + Telegram bot (móvil)
- Acceso externo: trabaja desde remoto, no siempre en computadora
