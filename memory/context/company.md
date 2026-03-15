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

## Tipo de cambio (al 15/03/2026)
- USD/ARS: 1.415 (dólar blue) — auto-fetch dolarapi.com, override manual
- USD/RMB: 6.9 (tasa del cambista) — siempre manual
