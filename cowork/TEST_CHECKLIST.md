# ROKER NEXUS — Lista de Testeo Completo
**Completar en orden. Marcar ✅ o ❌ con el error.**

---

## 1. CARGA DE ARCHIVOS

### 1.1 Optimización de Stock
- [ ] Subir `Optimizacin_de_Stock_*.XLS` → debe mostrar `✅ 877 filas` (o similar)
- [ ] Subir el mismo archivo dos veces → debe avisar duplicado
- [ ] Dashboard muestra Artículos Activos > 0 después de subir

### 1.2 Lista de Precios
- [ ] Subir `Lista de Precios_*.XLS` → debe mostrar `✅ 8952 filas`
- [ ] Subir dos veces → sin error UNIQUE

### 1.3 Cotización AI-TECH
- [ ] Subir `LA COTIZACION DE AI-TECH *.xlsx` → debe mostrar `✅ N filas`
- [ ] Subir mismo invoice dos veces → sin error, sobreescribe

### 1.4 Ventas Resumida
- [ ] Subir `Planilla de Ventas por Marca Resumida_*.XLS` → `✅ N filas`
- [ ] Sin error UNIQUE

### 1.5 Compras por Marca
- [ ] Subir `Planilla de Ventas por Marca_*.XLS` (sin "Resumida") → `✅ N filas`
- [ ] Sin error UNIQUE

### 1.6 Stock por Depósito ⚠️ PENDIENTE
- [ ] Subir `Planilla_de_Stock_SAN JOSE_*.XLS` → detecta depósito San José
- [ ] Subir `Planilla_de_Stock_LARREA_*.XLS` → detecta depósito Larrea
- [ ] Dashboard muestra stock por depósito

---

## 2. DASHBOARD

- [ ] Sin Stock muestra número correcto
- [ ] Bajo Mínimo muestra número correcto
- [ ] Artículos Activos > 0
- [ ] Última Importación muestra fecha reciente
- [ ] Quiebres urgentes lista artículos (con stock cargado)
- [ ] Stock por depósito muestra gráfico (con stock cargado)
- [ ] Próximas actualizaciones lista horarios

---

## 3. BOT TELEGRAM (@Rokeriabot)

### 3.1 Menú principal
- [ ] Escribir "Hola" → muestra 8 botones
- [ ] Botón 📦 Stock → pide artículo
- [ ] Botón 💰 Precio → pide artículo
- [ ] Botón 🔴 Quiebres → pide depósito
- [ ] Botón 🚚 Tránsito → muestra pedidos
- [ ] Botón ⛔ Lista negra → muestra lista + botón agregar
- [ ] Botón 📊 Resumen → muestra stats
- [ ] Botón 💵 Tipo de cambio → pide valor
- [ ] Botón 🤖 Preguntarle a IA → pide consulta

### 3.2 Búsqueda por nombre
- [ ] Escribir "samsung" → muestra lista de modelos
- [ ] Seleccionar modelo → muestra opciones (stock/precio/tránsito/lista negra)
- [ ] Escribir "a02s" → encuentra artículo directo
- [ ] Escribir "moto g" → muestra múltiples modelos

### 3.3 Stock
- [ ] `/stock a02s` → muestra stock por depósito
- [ ] Botón "Stock San José" → muestra solo ese depósito
- [ ] Botón "Stock Larrea" → muestra solo ese depósito

### 3.4 Precio
- [ ] `/precio a02s` → muestra Lista 1 y ML en USD y ARS
- [ ] Precio ARS = precio USD × tipo de cambio

### 3.5 Quiebres
- [ ] `/quiebres` → pide depósito
- [ ] Elegir San José Top 10 → lista top 10
- [ ] Elegir Todos Top 20 → lista top 20

### 3.6 Tránsito/Pedido
- [ ] `/pedido a02s` → muestra si está en tránsito o cotización
- [ ] Muestra archivo, hoja y renglón

### 3.7 Lista negra
- [ ] `/negra samsung` → busca y pide confirmación
- [ ] Confirmar → agrega a lista negra
- [ ] `/negra` solo → muestra lista actual

### 3.8 Tipo de cambio
- [ ] 💵 Tipo de cambio → muestra valor actual
- [ ] Escribir 1420 → guarda y confirma
- [ ] Precio en bot refleja nuevo tipo de cambio

### 3.9 IA
- [ ] "¿Qué artículos tengo bajo mínimo?" → responde Claude
- [ ] "¿Cuánto vale el A02s en pesos?" → responde con precio actualizado

### 3.10 Notificaciones automáticas
- [ ] Al hacer push → llega mensaje de versión en 5 segundos
- [ ] Alerta de quiebres llega a las 13:00 (Lun-Vie)

---

## 4. PÁGINAS DEL SISTEMA

### 4.1 Inventario
- [ ] Muestra lista de artículos (después de cargar archivos)
- [ ] Filtros por marca funcionan
- [ ] Filtro por depósito funciona

### 4.2 Precios & ML
- [ ] Muestra lista de precios cargados
- [ ] Conversión USD → ARS usa tipo de cambio actual
- [ ] Diferencia con precio ML visible

### 4.3 Compras
- [ ] Sugerencias de compra basadas en optimización
- [ ] Filtro por monto funciona
- [ ] Lista negra excluye artículos correctamente

### 4.4 Asistente IA
- [ ] Input de texto visible (no pisado por chat_input)
- [ ] Botón Enviar funciona
- [ ] Claude responde consultas

---

## 5. SISTEMA GENERAL

- [ ] Versión visible en barra superior (v1.4.x)
- [ ] "Sin conexión" / "Sistema OK" en esquina superior derecha
- [ ] Navegación entre páginas funciona
- [ ] No hay texto pisado en la barra inferior

---

## PENDIENTES PARA PRÓXIMA SESIÓN

- [ ] Integración MercadoLibre (publicaciones, precios, stock ML)
- [ ] Auto-sincronización Google Drive → importación automática
- [ ] Stock por Depósito (falta subir archivos Flexxus de stock)
- [ ] Tipo de cambio RMB (yuan chino) en bot
- [ ] Página de cotizaciones (ver AI-TECH importadas)
- [ ] Alertas personalizadas (umbral por artículo)

