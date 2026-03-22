# Flexxus ERP — Guía de exportación y bugs conocidos

## Bug de offset de columnas
Flexxus tiene un desplazamiento sistemático entre el header y los datos reales en Excel.

| Archivo | Header en fila | Columna REAL del dato clave | Nota |
|---------|---------------|----------------------------|------|
| Listado General (Stock) | 8 | **Col 7** = Stock real | Col 8 dice "Stock" pero tiene ceros |
| Optimización de Stock | 11 | **Col 8** = S.Actual | Col 7 = Demanda Prom |
| Lista de Precios | 0 | **Col 13** = Stock Actual | Sin offset |
| Ventas por Marca | 8 | **Col 7** = Total Vta. | Mismo patrón |
| Compras por Marca | 7 | **Col 10** = Cantidad | Mismo bug |
| RMA Seguimiento | 4 | **Col 13** = Costo | Col 5=Código, Col 7=Artículo |

## Rutas de exportación

### Stock → Listado General (por depósito)
- Ruta: Stock → Listado General
- Filtro OBLIGATORIO: Depósito = UNO por vez (si no, sale todo vacío)
- Exportar: Excel (.xlsx o .xls, ambos funcionan)
- Validar: total unidades = lo que muestra Flexxus en pantalla

### Stock → Optimización de Stock
- Ruta: Stock → Optimización de Stock
- Período: 6 meses mínimo (si es corto, stockouts dan demanda=0)
- Coeficientes: Min 1.0 / Óptimo 1.2 / Máx 1.4

### Stock → Histórico de Artículos (NUEVO — muy importante para auditoría)
- Ruta: Stock → Histórico de Artículos
- Filtro: artículo UNO por vez (no hay export masivo)
- Depósito: "Todos" para ver todos los movimientos
- Usar para: detectar movimientos eliminados, auditar MD sospechosos
- Estrategia: exportar solo Top 20 módulos por volumen desde diciembre

## Tipos de comprobante en Histórico
| Código | Tipo |
|--------|------|
| FA | Factura A (venta a responsable inscripto) |
| FB | Factura B (venta a consumidor final) |
| FE | Factura Electrónica (compra/ingreso de proveedor) |
| RE | Remito de Entrada (ingreso físico de mercadería) |
| RI | Remito Interno (transferencia entre depósitos) |
| MD | Movimiento de Depósito (ajuste de inventario) |
| NC/NCA/NCB | Nota de Crédito (devolución, crédito a cliente) |
| CS | Comprobante de Stock (relacionado a RMA) |

## Alertas en Histórico
- MD siempre vienen en pares (egreso + ingreso mismo número) → normal
- Gap de saldo = saldo[n] ≠ saldo[n-1] + ingreso[n] - egreso[n] → posible movimiento eliminado
- Verificar por depósito: con "Todos" los gaps pueden ser por cambio de depósito (normal)
- Con filtro de UN depósito: gap real → investigar

## Depósitos en Flexxus (nombre exacto)
- DEPOSITO SAN JOSE
- LARREA NUEVO
- DEPOSITO SARMIENTO NUEVO2
- DEPOSITO FULL ML
- DEPÓSITO MERCADO LIBRE
- DEPOSITO MUESTRAS
- USO INTERNO
- DEP. TRASITORIO DEV ML (aparece así en exports)
- DEPOSITO TRANS. DE RMA
