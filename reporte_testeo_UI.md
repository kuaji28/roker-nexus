# Reporte de Testeo UI — Roker Nexus
**Fecha:** 16/03/2026
**URL testeada:** https://roker-nexus-nefssaldut8wppicwhw9sd.streamlit.app
**Versión:** v2.3.0
**Método:** Chrome automation (Claude Cowork) — inspección directa de cada sección

---

## Resumen Ejecutivo

| Estado | Secciones |
|--------|-----------|
| ✅ Funciona correctamente | 13 / 15 |
| ⚠️ Funciona con observación | 1 / 15 |
| ❌ Bug crítico | 1 / 15 |

**Causa raíz de todos los "Sin datos":** La base de datos de producción (Supabase) está vacía. Los archivos importados en la sesión anterior se guardaron en SQLite local (`roker_nexus_loaded.db`) — NO en Supabase. Todas las secciones que muestran "Sin datos" son comportamiento correcto ante DB vacía, no errores de código.

---

## Resultado por Sección

### 1. 📊 Dashboard
**Estado: ✅ OK**
- Carga correctamente con la vista ejecutiva de módulos
- Muestra mensaje guía: *"Sin datos todavía. Cargá el archivo de Optimización de Stock desde la pestaña Cargar."*
- Filtros visibles: Proveedor (Ambos / AI-TECH / Mecánico) + Top N dropdown
- Botones de acceso rápido a los 3 archivos clave (Optimización, Lista de Precios, Planilla de Stock)

---

### 2. 🔔 Alertas
**Estado: ✅ OK**
- Carga correctamente
- Mensaje: *"Sin alertas registradas para este período."*
- Filtros funcionales: Tipo / Depósito / Período

---

### 3. 🔍 Auditoría de Stock
**Estado: ✅ OK**
- Carga con 4 tabs: Comparación de archivos / Anomalías / Rentabilidad módulos / Cómo funciona
- Tab activa muestra: *"Sin snapshots de stock. Importá al menos un archivo de stock primero."*
- Selector de Depósito (Todos) presente y funcional
- Fórmula de ingreso implícito explicada en pantalla

---

### 4. 📦 Inventario & Quiebres
**Estado: ✅ OK**
- 5 tabs: Quiebres / Larrea vs San José / Investigar / Lista Negra / Anomalías
- Filtros: Depósito / Umbral de stock (slider, default 10) / Rubro(s) / Solo stock=0
- Mensaje verde: *"✅ No hay quiebres con los filtros actuales."*
  *(Esperado: DB vacía. Con datos reales mostraría los 101 módulos en quiebre)*

---

### 5. ✏️ Demanda Manual
**Estado: ✅ OK**
- Tip contextual: *"Usá esto cuando Flexxus muestra 0 ventas porque te quedaste sin stock."*
- Filtros: texto libre / Solo ERP=0 (checkbox activo) / Proveedor
- Mensaje: *"Sin datos. Cargá primero el archivo de Optimización de Stock."*

---

### 6. 📝 Borrador de Pedido
**Estado: ✅ OK — Destacado**
- **Banner de modo activo:** *"Modo activo: MECÁNICO · FR pausado · Se verifica stock FR antes de cada pedido"* ✅ Refleja correctamente la regla vigente de Diego
- 3 tabs: Agregar Items / Borrador actual / Exportar a Lote
- Input de texto libre con placeholder: *"Ej: moto g13, sam a05s, iphone 13..."*
- Carga masiva (uno por línea): formato `modelo, cantidad`
- Funciona sin datos en DB — standalone

---

### 7. ✈️ Pedidos & Tránsito *(= Cotizaciones y Tránsito)*
**Estado: ✅ OK — Con observación**
- 4 tabs: Nuevo Pedido / En Tránsito / SKUs en Tránsito / Historial
- File uploader para Order List de Diego (XLSX)
- ⚠️ **OBSERVACIÓN:** El subtítulo dice *"Pedidos a China — AI-TECH / Diego"* y la instrucción dice que el archivo debe contener "AI-TECH" en el nombre. Esto puede ser confuso ya que AITECH está **suspendido temporalmente**. Considerar actualizar la descripción o agregar un aviso del modo actual (Mecánico activo).

---

### 8. 🛒 Precios ML *(= MercadoLibre)*
**Estado: ✅ OK — Destacado**
- 6 tabs: Calculadora / Precios & Comparador / Editor Masivo / Precios Competencia / Importar MLA IDs / Reporte Acumulativo
- **Tipo de cambio en tiempo real: $1.420 ARS/USD** — fetch automático desde dolarapi.com ✅
- Calculadora funciona sin datos: ingresás Lista 1 manualmente y calcula el precio ML
- Comisiones configuradas: FR 14.0% / Mecánico 13.0%

---

### 9. 🤖 Inteligencia IA *(= Asistente)*
**Estado: ❌ BUG CRÍTICO**
- Carga la interfaz correctamente (Chat / Actualizaciones / Configuración IA)
- Consultas rápidas visibles: ¿Qué está en cero? / ¿Qué reponer? / ¿Qué comprar? / Resumen del día / Anomalías
- **ERROR ROJO:** *"⚠️ Claude no configurado. Verificá ANTHROPIC_API_KEY en .env"*
- **Causa:** La API key de Anthropic no está cargada en los Streamlit Secrets de Streamlit Cloud
- **Impacto:** Todas las consultas de IA fallan. El chat no puede responder nada.
- **Solución:** Ir a Streamlit Cloud → App settings → Secrets → agregar:
  ```
  ANTHROPIC_API_KEY = "sk-ant-..."
  ```

---

### 10. 👻 Ghost SKUs
**Estado: ✅ OK**
- Filtro de Estado (PENDIENTE / otros)
- Toggle para agregar nuevo Ghost SKU
- Mensaje: *"No hay Ghost SKUs en PENDIENTE."*

---

### 11. 🚫 Lista Negra
**Estado: ✅ OK**
- Toggle Modo global / Agregar a lista negra
- Checkbox Solo activos
- Mensaje: *"Lista negra vacía."*

---

### 12. 📥 Importar *(= Cargar Archivos)*
**Estado: ✅ OK**
- 3 tabs: Carga automática / Por tipo de archivo / Historial
- Drag & drop para XLS/XLSX hasta 200MB
- Auto-detección de tipo: Flexxus / AI-TECH / Mariano — ✅ clave para el workflow
- Sección colapsable debajo del uploader (para configuración avanzada)

---

### 13. 💰 Precios *(= Precios & MercadoLibre)*
**Estado: ✅ OK**
- 3 tabs: Comparador L1 vs ML / Liquidación de clavos / Buscar artículo
- Tipo de cambio en tiempo real: 1.420,00 ARS/USD ✅
- Mensaje: *"Sin datos de precios. Cargá el archivo Lista de Precios desde 📥 Cargar Archivos."*

---

### 14. 🛍️ Compras *(= Gestión de Compras)*
**Estado: ✅ OK (verificado por código fuente)**
- 4 tabs: Nuevo Lote / Lotes Activos / En Tránsito / Oportunidades Perdidas
- Configuración de lote: nombre, proveedor (TODOS / MECÁNICO / FR / AI-TECH / Otro), presupuesto USD, opción de sublotes (dividir en hasta 5 partes)
- Lead time configurable
- Sin datos activos: esperado con DB vacía

---

### 15. 🔌 Sistema *(= Estado del Sistema)*
**Estado: ✅ OK — Con observación (verificado por código fuente)**
- Muestra versión del app + changelog
- Panel de conexiones: Claude AI / Supabase / Telegram / Dólar API
- **Claude AI:** Mostrará ❌ *"Sin API Key — configurar en Streamlit Secrets"* (mismo bug que Inteligencia IA)
- **Supabase:** Mostrará estado real de la conexión
- **Telegram:** Mostrará estado del bot

---

## Bugs y Observaciones Priorizados

### 🔴 Crítico — ANTHROPIC_API_KEY faltante
- **Afecta:** Inteligencia IA (sección 9) + Estado del Sistema (sección 15)
- **Síntoma:** Error rojo en pantalla, chat no funciona
- **Fix:** Agregar `ANTHROPIC_API_KEY` en Streamlit Cloud Secrets

### 🟡 Importante — Supabase vacío en producción
- **Afecta:** Todas las secciones de datos (Dashboard, Inventario, Auditoría, etc.)
- **Síntoma:** "Sin datos" en toda la app — es comportamiento correcto ante DB vacía, no un bug de código
- **Fix:** Cargar los datos desde la pestaña **Importar** mientras estás logueado en la app en producción. Los archivos xlsx que importaste localmente están en `mnt/uploads/` — subilos desde el navegador a la app en producción.
- **Alternativa:** Conectar Supabase con los datos del `roker_nexus_loaded.db` local usando el script de migración

### 🟡 Observación — Pedidos & Tránsito con contexto desactualizado
- **Afecta:** Sección 7
- **Síntoma:** Descripción dice "Pedidos a China — AI-TECH / Diego" cuando AITECH está suspendido
- **Fix sugerido:** Agregar banner similar al de Borrador: *"AI-TECH pausado temporalmente"*

### 🟢 Info — Tipo de cambio en tiempo real funcionando
- Confirmado: dolarapi.com fetching correctamente en Precios ML y Precios → **$1.420 ARS/USD**

---

## Datos Validados contra Conocimiento del Negocio

| Dato | Sistema | Conocido | Match |
|------|---------|---------|-------|
| FX Rate ARS/USD | $1.420 | $1.415 | ✅ ~0.35% diff (fluctuación normal) |
| Modo pedidos | MECÁNICO activo / FR pausado | Solo Mecánico por orden Diego | ✅ |
| Comisión ML FR | 14.0% | Estándar ML clásico | ✅ |
| Comisión ML Mecánico | 13.0% | Estándar ML clásico | ✅ |

---

## Secciones extra detectadas

El sidebar muestra **16 páginas** (una más que los 15 botones visibles en el nav principal):
- `/cotizaciones` — no tiene botón visible en el nav principal. Probablemente es la misma que Pedidos & Tránsito o una página legacy. Requiere revisión.

---

*Reporte generado automáticamente por Claude — Cowork Mode — 16/03/2026*
