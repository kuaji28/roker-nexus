# Contexto — EL CELU y Roker

## La empresa

**EL CELU** — tienda argentina de accesorios y repuestos de celulares.
Sistema ERP: **Flexxus** (argentino). Tres ubicaciones principales:

| Depósito | Código | Rol |
|----------|--------|-----|
| SAN JOSE | SJ | Hub principal. Mayor stock. Surte a LARREA y SARMIENTO. |
| LARREA | LAR | Local al público (~6km de SAN JOSE). Recibe por flete externo. |
| SARMIENTO | SAR | Depósito adicional / local. |
| FULL ML | FML | MercadoLibre Fulfillment (stock protegido). |
| DEP. ML | DML | Segundo depósito ML — considerar contaminado para análisis. |
| MERMAS | MER | Mermas y descartados — **NO usar para stock activo**. |
| DEP. TRANSITORIO RMA | RMA | Devoluciones en tránsito — **NO usar para stock activo**. |

## Personas clave

| Quién | Rol | Relación con Roker |
|-------|-----|--------------------|
| **Diego Majlis** | Dueño (co-owner) | Contacto EXCLUSIVO de Roker. Solo él da órdenes. Destinatario principal de reportes. |
| **Walter Majlis** | Dueño (co-owner) | Hermano de Diego. Recibe presentaciones junto a Diego. |
| **Pablo Bue** | Gerente | Puede mostrar números selectivos. No es interlocutor directo de Roker. |
| **Mariano** | Sub-gerente | Ingresó dic 2025. Impulsó recorte de presupuesto módulos. Roker debe estar un paso adelante. |
| **Ezequiel Firmapaz** | Staff activo | Hace ajustes MD en Flexxus. Usuario: EFIRMAPAZ. |
| **Lorena Rodriguez** | Ex-staff | Se fue mediados dic 2025. **Su usuario Flexxus sigue activo** — bandera de control. |
| **Matias Toledano** | Staff | Posible encargado depósito SAN JOSE / logística. |
| **Rocio Sisco** | Vendedora | Vende desde LARREA. |
| **GGARCIA** | Staff | Maneja devoluciones RMA. |

> ⚠️ Los usuarios Flexxus no siempre se actualizan cuando alguien se va. No confiar en el nombre de usuario como indicador de quién hizo una operación.

## Terminología clave

| Término | Significado |
|---------|-------------|
| **Módulos** | Pantallas de celular (display + touch). Categoría #1 en ventas (35%). |
| **FR / AI-TECH / AITECH** | Proveedor histórico de módulos. Códigos empiezan con letra (MS..., MM..., MX...). SUSPENDIDO temporalmente. |
| **Mecánico** | Proveedor activo. Códigos numéricos (ej: 2401251379). ÚNICO proveedor autorizado hoy. |
| **FR activo** | Stock real disponible: SJ + LAR + SAR + FML. NO incluir MER, RMA, DTM, DML. |
| **MD** | Movimiento de depósito / ajuste manual de inventario. |
| **RE** | Remito de entrada (ingreso de mercadería). |
| **RI** | Remito interno (transferencia entre depósitos). |
| **FA / FB** | Factura A / Factura B (ventas). |
| **RMA** | Devoluciones de clientes. Pérdida = capital + renta no percibida. |
| **Demanda invisible** | Stock=0 → ventas=0 aunque haya demanda real. Subestima necesidad. |
| **Lista 1** | Precio MAYORISTA (el más bajo, base). |
| **Lista 4** | Precio MercadoLibre (incluye comisión ML). |
| **P.Comp** | Precio de compra (costo). |
| **RMB** | Yuan chino. 1 USD = 6.9 RMB (manual). |
| **Dólar blue** | Tipo de cambio informal ARG. 1 USD = ~$1.415 ARS. Auto-fetch dolarapi.com. |

## Estrategia y contexto político interno

- **Pablo y Mariano** impulsan pivot a electrodomésticos (modelo Frávega) y recortaron presupuesto de módulos desde dic 2025.
- **El error de ese argumento:** los módulos son el *anchor product* — sin módulos el técnico va a la competencia y lleva todo lo demás.
- **La tarea de Roker:** demostrar el valor indirecto de los módulos (tráfico, ventas cruzadas) y el costo de oportunidad de los stockouts.
- **Auditoría silenciosa:** verificación independiente de datos para presentar a Diego/Walter sin pasar por Pablo/Mariano.
- **Baseline:** ene–nov 2025 (antes de Mariano). Comparación: dic 2025 – mar 2026.

## Números validados (al 15/03/2026)

- Módulos = 35.1% de ventas totales (categoría #1)
- 28.224 unidades módulos vendidas en 30 días
- Stock módulos a costo: U$S 517.620 | a Lista 1: U$S 826.265
- Margen promedio módulos: 118% (sobre Lista 1)
- Pérdida total RMA (2.5 meses): U$S 24.708 → proyección anual U$S 118.601
- Presupuesto actual módulos: U$S 250.000/mes (recortado desde dic 2025)
- 101 módulos con demanda>0 y stock=0 (stockout por presupuesto)

## Proyectos activos

| Proyecto | Estado |
|---------|--------|
| **Roker Nexus** | App Streamlit + Supabase en producción. Secundario por ahora. |
| **Pedido Mecánico 039** | En análisis. Presupuesto $300K. Prioridad #1. |
| **Auditoría v1** | Para Diego/Walter: déficit presupuesto, pérdidas RMA, remitos sin confirmar. |
| **Bot Telegram** | Pendiente construir. |

## Timeline crítico

| Período | Qué pasó |
|---------|----------|
| Antes de ago 2025 | Todo bajo código FR numérico. |
| Ago–sep 2025 | Mecánico migra a códigos numéricos propios. FR pasa a códigos alfabéticos. |
| **Dic 2025** | Mariano ingresa como sub-gerente. Recorte presupuesto módulos. |
| Mediados dic 2025 | Lorena Rodriguez se va. Inventario post-Lorena = baseline limpio. |
| Ene 2026 | Liquidación masiva SAM A02S (6.313→-8u). |
| 24/02/2026 | Container MFRS Bairenda (78 cajas, 26.154u) empieza a ingresar. |
| 15/03/2026 | Fecha de relevamiento actual. |
| 17/03/2026 | Análisis Pedido Mecánico 039 en curso. |
