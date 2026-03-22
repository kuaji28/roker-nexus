# ROKER NEXUS — Handoff para Cowork
## Documento de contexto completo para continuar el proyecto

---

## 🎯 QUÉ ES ESTE SISTEMA

**ROKER NEXUS** es un sistema de gestión de inventario para "El Celu", empresa de repuestos de celulares en Argentina (propietario: Sergio).

**Stack:**
- **Frontend/App:** Python + Streamlit → deploy en Streamlit Cloud
- **Base de datos:** SQLite local (problema: se borra al rebootear) → migrar a Supabase
- **Bot:** python-telegram-bot → deploy en Railway
- **Repo:** github.com/kuaji28/roker-nexus (branch: main)
- **AutoPush:** autopush.ps1 detecta cambios cada 30s y pushea automático

**URLs activas:**
- App: https://roker-nexus-nefssaldut8wppicwhw9sd.streamlit.app
- Bot: @Rokeriabot (Chat ID: 5427210648)

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
roker_nexus/
├── app.py                    ← Entrada principal, nav horizontal + sidebar
├── config.py                 ← Lee env vars (.env + st.secrets + Railway vars)
├── database.py               ← SQLite/Supabase, todas las funciones de DB
├── version.py                ← Control de versiones (actual: v2.1.0)
├── requirements.txt          ← Dependencias (incluye plotly, telegram, supabase)
├── telegram_bot.py           ← Bot Telegram (corre en Railway separado)
├── autopush.ps1              ← Script AutoPush Windows
├── nixpacks.toml             ← VACÍO (Railway usa requirements.txt directo)
├── supabase_schema.sql       ← Schema para ejecutar en Supabase SQL Editor
├── INSTRUCCIONES_SUPABASE.md ← Paso a paso para activar Supabase
├── pages/
│   ├── dashboard.py          ← Vista ejecutiva de módulos FR + Mecánico
│   ├── importar.py           ← Carga archivos Flexxus
│   ├── compras.py            ← Lotes de compra L1/L2/L3
│   ├── borrador.py           ← Borrador de pedido sin código ERP
│   ├── cotizaciones.py       ← Cotizaciones AI-TECH + tránsito
│   ├── mercadolibre.py       ← Comparador ML + calculadora + editor
│   ├── inventario.py         ← Inventario + quiebres + anomalías
│   ├── precios.py            ← Lista 1 vs Lista 4 ML
│   ├── asistente.py          ← Chat IA (Claude/Gemini)
│   ├── sistema.py            ← Estado del sistema + conexiones
│   ├── demanda_manual.py     ← Override demanda cuando ERP muestra 0
│   ├── ghost_skus.py         ← Módulos pedidos sin código ERP
│   └── lista_negra.py        ← Modelos que no se vuelven a pedir
├── modules/
│   ├── ia_engine.py          ← Motor IA: Claude + Gemini + GPT
│   ├── ml_motor.py           ← Motor ML: búsqueda, caché, calculadora
│   └── inventario.py         ← Detección quiebres y anomalías
├── importers/
│   ├── flexxus_optimizacion.py ← Parser Optimización de Stock
│   ├── flexxus_lista_precios.py ← Parser Lista de Precios
│   ├── flexxus_stock.py      ← Parser Planilla de Stock (depósitos)
│   ├── flexxus_ventas.py     ← Parser Planilla de Ventas
│   ├── aitech_mariano.py     ← Parser cotización Mariano
│   └── aitech_orderlist.py   ← Parser Order List AI-TECH
└── utils/
    ├── helpers.py            ← fmt_usd, fmt_ars, fmt_num, check_apis
    ├── matching.py           ← Fuzzy matching para artículos
    └── horarios.py           ← Timezone Argentina
```

---

## 🏢 REGLAS DE NEGOCIO CRÍTICAS

### Clasificación de proveedores (NUNCA cambiar esta lógica)
- Código empieza con **LETRA** (M, L, P...) → **FR** (proveedor AITECH)
  - Ejemplo: `MSAMA72CM.`, `LGKXX.`, `MIPH13CM.`
- Código empieza con **NÚMERO** → **MECÁNICO** (proveedor MECÁNICO)
  - Ejemplo: `2401230629`, `2506110003`, `30013.`

### Estado actual de proveedores
- **FR: PAUSADO** — no se pide al proveedor FR actualmente
- Antes de pedir MECÁNICO, verificar si hay stock FR del mismo modelo (cruce FR/MEC)
- El sistema avisa automáticamente cuando hay stock FR disponible

### Precios
- **Lista 1** = precio mayorista en USD
- **Lista 4** = precio ML publicado en ARS (directo, sin conversión)
- **Tasa USD/ARS**: configurable desde Sidebar (default: 1420)
- **RMB/USD**: configurable desde Sidebar (default: 7.30)

### Archivos Flexxus
El sistema detecta automáticamente el tipo de archivo por nombre:
- "Optimizacin de Stock" → optimizacion (nota: typo intencional de Flexxus)
- "Lista de Precios" → precios
- "Planilla de Ventas por Marca Resumida" → ventas resumidas
- "Planilla de Ventas por Marca" → ventas detalle
- "Planilla_de_Stock" o "stock larrea/san jose" → stock por depósito

### Depósitos
- **SAN_JOSE** = depósito central (abastece a Larrea)
- **LARREA** = local principal de venta
- Si Larrea quiebra, verificar si San José tiene stock antes de pedir

### Quiebres de stock
- SAM A10 ≠ SAM A10S (son modelos distintos, nunca confundir)
- Stock 0 no siempre es falta de demanda → puede ser quiebre real
- El historial_stock acumula un registro por día para detectar anomalías

---

## 🔧 PROBLEMAS PENDIENTES (en orden de prioridad)

### 1. SUPABASE — CRÍTICO (datos se pierden al rebootear)
- **Problema:** SQLite se borra cada vez que Streamlit Cloud hace reboot
- **Solución:** Activar Supabase (ya tiene cuenta: zjrabazzvckvxhufppoa.supabase.co)
- **Paso 1:** Ejecutar `supabase_schema.sql` en Supabase SQL Editor
- **Paso 2:** En Streamlit Cloud → Manage app → Secrets → agregar:
  ```
  SUPABASE_URL = "https://zjrabazzvckvxhufppoa.supabase.co"
  SUPABASE_KEY = "eyJhbGci..."
  ANTHROPIC_API_KEY = "sk-ant-api03-..."
  TELEGRAM_TOKEN = "8600755595:..."
  TELEGRAM_CHAT_ID = "5427210648"
  ```
- Ver: `INSTRUCCIONES_SUPABASE.md`

### 2. RAILWAY (bot Telegram no buildea)
- **Problema:** `"pip install -r requirements-railway.txt" did not complete: exit code 127`
- **Estado:** nixpacks.toml está vacío ✅, requirements-railway.txt borrado ✅
- **Pendiente:** En Railway → Settings → "Build Command" → dejar VACÍO → Save → Deploy
- Variables Railway necesarias:
  - `TELEGRAM_TOKEN` = token del bot
  - `TELEGRAM_CHAT_ID` = 5427210648

### 3. TELEGRAM (bot responde pero no da información)
- El bot muestra el menú pero cuando busca artículos no encuentra en DB
- **Causa:** Railway tiene su propia DB vacía (sin datos de Flexxus)
- **Solución:** Una vez activo Supabase, Railway y Streamlit comparten la misma DB

### 4. PERSISTENCIA — CRÍTICO (misma causa que punto 1)
- Cada reboot de Streamlit Cloud borra SQLite → hay que cargar todos los archivos desde cero
- **Solución definitiva:** Activar Supabase (ver punto 1)
- **Workaround temporal:** Nada funcional sin Supabase

### 5. MERCADOLIBRE (tab no se despliega bien)
- El módulo tiene 6 tabs: Calculadora, Comparador, Editor Masivo, Competencia, MLA IDs, Reporte
- El comparador busca en la API de ML con fallback a scraping web
- Si la API da 403, usa el fallback automáticamente
- Puede tardar 5-10 segundos en responder

### 5. DASHBOARD (entrega reciente)
- Filtro FR/Mecánico/Ambos → selectbox en header
- Top N configurable → selectbox (5/10/15/20)
- Botones 🚫 (lista negra) y 📝 (borrador) en cada crítico/urgente
- Tránsito leído desde cotizacion_items (no desde articulos.en_transito)

---

## ✅ FIXES APLICADOS (2026-03-15)

- **dashboard.py**: Bug tránsito = 0 → query usaba `descripcion_flexxus` (descripción) en lugar de `codigo_flexxus` (código ERP). Corregido.
- **dashboard.py**: Default filtro proveedor cambiado de "Ambos" → "Mecánico" (index=2).
- Top N (5/10/15/20) y filtro FR/Mecánico/Ambos ya estaban implementados y funcionan correctamente.
- **database.py**: Soporte PostgreSQL directo vía `DATABASE_URL`. Agrega `DATABASE_URL` a los secrets de Streamlit Cloud y Railway para activar persistencia permanente. Ver `INSTRUCCIONES_SUPABASE.md`.
- **requirements.txt**: Agregado `psycopg2-binary` para conexión PostgreSQL.

---

## ⚠️ ERRORES COMETIDOS ANTES — NO REPETIR

1. **NO sobreescribir archivos que funcionan** sin preguntar primero
2. **NO crear módulos nuevos** cuando se puede agregar funciones al archivo existente
3. **NO cambiar la estructura de carpetas** — todo está en su lugar correcto
4. **NO reemplazar app.py completo** — solo modificar lo necesario
5. **NO agregar imports** sin verificar que el módulo existe en el proyecto
6. **Antes de cualquier cambio:** leer el archivo completo, identificar exactamente dónde insertar, preguntar si no está seguro
7. **Entrega:** siempre un solo ZIP con todos los archivos modificados juntos
8. **CSS:** Streamlit 1.55 tiene bug que muestra "arröw_right/down" en expanders — el fix CSS ya está en app.py, no remover

---

## 💻 FLUJO DE TRABAJO CON COWORK

Cowork tiene acceso directo a `C:\Users\kuaji\Documents\roker_nexus\`

El flujo es:
1. Cowork lee el archivo a modificar
2. Hace los cambios directamente en la carpeta
3. AutoPush detecta el cambio en 30 segundos y pushea a GitHub
4. Streamlit Cloud actualiza la app automáticamente
5. Railway redeploya el bot automáticamente

**NO necesitás ZIPs cuando usás Cowork** — edita directo en la carpeta.

---

## 🔑 CONFIGURACIONES (Sidebar)

El sidebar izquierdo tiene estos panels (expandibles):
- 🚚 **Logística:** Lead Time (días)
- 💰 **Presupuestos (USD):** Lote 1 / Lote 2 / Lote 3
- 💱 **Tasas:** USD→ARS · RMB→USD
- 🛒 **Comisiones ML:** FR (14%) · Mecánico (13%) · Margen extra FR/MEC
- 📊 **Coeficientes Stock:** Mín (1.0) · Opt (1.2) · Máx (1.4)
- 🧠 **IA:** Selector Claude/Gemini/GPT · API Keys · Toggle paralelo

Todas las configs se guardan en la tabla `configuracion` de la DB.

---

## 📊 ESTADO DE LA APP

| Módulo | Estado |
|---|---|
| Dashboard | ✅ Funcionando con datos reales |
| Cargar archivos | ✅ Detecta Flexxus automáticamente |
| Compras/Lotes | ✅ L1/L2/L3 con presupuestos |
| Borrador pedido | ✅ Fuzzy matching con artículos |
| Cotizaciones/Tránsito | ✅ Estados PENDIENTE→TRÁNSITO→INGRESADO |
| MercadoLibre | ⚠️ Funciona pero lento (API ML) |
| Inventario | ✅ Con quiebres y anomalías |
| Precios | ✅ L1 vs L4 ML |
| IA Asistente | ⚠️ Necesita API key en Secrets |
| Demanda Manual | ✅ Nuevo en v2.1.0 |
| Ghost SKUs | ✅ Nuevo en v2.1.0 |
| Lista Negra | ✅ Con búsqueda de artículos |
| Sistema | ✅ Muestra estado de conexiones |
| Telegram Bot | ❌ Railway no buildea |
| Persistencia | ❌ Datos se pierden al reboot |

---

## 🚀 PRÓXIMOS PASOS EN ORDEN

1. Activar Supabase (ver INSTRUCCIONES_SUPABASE.md)
2. Configurar Railway (Settings → Build Command vacío)
3. Agregar secrets en Streamlit Cloud
4. Testear bot Telegram con /start
5. Testear importación de archivos Flexxus

---
*Última actualización: 2026-03-15 16:00 | Versión: v2.0.2*
