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

## 🟡 FASE 2 — Rediseño Nexus v2.0
- [ ] Diseñar esquema completo de base de datos (10 tablas nuevas)
- [ ] Presentar plan completo a Roker para aprobación antes de codear
- [ ] Migrar/adaptar importadores existentes al nuevo esquema
- [ ] Crear importadores faltantes: ventas, compras, remitos, histórico artículos

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
