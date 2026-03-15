# TASKS — Roker Nexus
*Última actualización: 15/03/2026*

## 🔴 FASE 1 — Relevamiento pendiente (ANTES de tocar código)
- [ ] Exportar Stock SARMIENTO con filtro depósito correcto (igual que LARREA)
- [ ] Exportar Stock DEP. TRANSITORIO DEVOLUCIONES
- [ ] Exportar Stock DEPOSITO FULL ML y DEPÓSITO MERCADO LIBRE
- [ ] Captura/export Venta x Artículo x Mes con año=2025 (mostrar caída desde dic)
- [ ] Captura pantalla Pedidos/Órdenes de compra a proveedor (si existe en Flexxus)
- [ ] Captura configuración de usuarios/permisos en Flexxus
- [ ] Exportar Histórico de Artículos para Top 20 módulos (desde dic 2025)

## 🟡 FASE 2 — Rediseño Nexus v2.2 (EN PROGRESO)
- [x] ~~Diseñar esquema completo~~ → Plan de rediseño completo aprobado 15/03
- [x] Tabla `archivo_tracker` agregada a database.py (+ `codigo_aliases`)
- [x] Funciones `update_archivo_tracker()` + `get_file_health()` implementadas
- [x] `_checklist_archivos()` en importar.py → dinámico (lee DB, semáforo 🟢🟡🔴)
- [x] `_panel_salud_datos()` agregado al Dashboard (compacto, expandible)
- [x] Bug `archivo.name` → `f.name` corregido en importar.py
- [x] NEXUS_META reader en flexxus_stock.py (detecta depósito desde etiquetar.py)
- [x] cotizaciones.py root deprecado (versión activa = pages/cotizaciones.py)
- [ ] Integrar Demanda Manual como tab en Inventario (eliminar página standalone)
- [ ] Integrar Ghost SKUs en Borrador (eliminar página standalone)
- [ ] Navegación rediseñada (grupos: Análisis / Operaciones / Auditoría / Sistema)
- [ ] Gestor de Alias de Códigos (tabla codigo_aliases ya creada, falta UI)
- [ ] Módulo Defensa de Presupuesto (curva antes/después Mariano dic 2025)
- [ ] Clasificador Barco vs. Avión en tabla articulos

## 🟡 FASE 3 — Bot de Telegram
- [ ] Setup bot en @BotFather y configurar token
- [ ] Comando /consulta: fuzzy match modelo → stock + precio + estado pedido
- [ ] Comando /dolar y /rmb: actualizar tipo de cambio (USD auto + override, RMB manual)
- [ ] Parser de texto WhatsApp: pegar mensaje → detectar modelos → lookup
- [ ] Comando /pedido: top recomendaciones por presupuesto + días
- [ ] Alertas push automáticas: stock crítico, anomalías, tránsito sin confirmar
- [ ] Consulta precio ML en vivo (API pública MercadoLibre)

## 🟠 FASE 4 — Motor de Auditoría
- [ ] Motor de variación diaria de stock (delta + ventas → diferencia inexplicada)
- [ ] Detector de gaps en Histórico de Artículos (movimientos eliminados)
- [ ] Tracker MD: quién ajusta, cuánto, cuándo
- [ ] Alerta tránsito: remito enviado → stock destino no aumentó en 48hs
- [ ] Cross-reference: remitos internos vs stock snapshots (quantificar pérdida)

## 🟠 FASE 5 — Features adicionales Nexus
- [ ] Lista Negra: obsoletos definitivos, pausas, recuperables
- [ ] Comparador precios ML (API pública)
- [ ] Integración tipo de cambio automático (dolarapi.com)
- [ ] Dashboard multi-depósito: todos los depósitos consolidados
- [ ] Detección duplicados en importación de archivos

## 🔵 FASE 6 — Presentación y documentación
- [ ] Guía Operativa: paso a paso con capturas Flexxus, delegable
- [ ] Protocolo continuidad: qué hacer si AI no disponible por 1 semana
- [ ] Presentación Walter + Diego: defensa presupuesto módulos con datos auditados
- [ ] Actualizar PROTOCOLO_CONTROL.md con Histórico de Artículos y tipo de cambio

## ✅ Completado
- [x] Mapeo completo depósitos (7 depósitos identificados)
- [x] Validación stock LARREA (21.187 uds, col 7 ✅)
- [x] Análisis RMA: U$S 24.708 pérdida en 2.5 meses
- [x] Identificar bug columnas Flexxus (offset sistemático)
- [x] Crear PROTOCOLO_CONTROL.md y verificar_archivo.py
- [x] Análisis remitos internos: 504 ítems, todos Entregada=0
- [x] Análisis Histórico de Artículos SAM A02S (1.294 movimientos)
- [x] Decisión: Telegram > WhatsApp para el bot (gratuito, sin límites)
- [x] Diseño tipo de cambio: USD auto-fetch + override, RMB manual
- [x] Instalar plugins: finance, data, operations, productivity
