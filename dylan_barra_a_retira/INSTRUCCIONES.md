# Dylan Restaurant — Cambio Barra → Retira

## Estado
- **Archivo modificado descargado** en tu carpeta de Descargas como `app.py`
- Si no lo encontrás, usá el script de abajo para regenerarlo

## Qué se cambió (34 reemplazos)
- Todos los textos visibles: "BARRA" → "RETIRA", "Barra" → "Retira"
- Botones: "🧍 BARRA" → "🧍 RETIRA", "🍺 BARRA" → "🍺 RETIRA"
- Tabs: "🧍 Barra" → "🧍 Retira"
- Headers: "🧾 Barra / Delivery" → "🧾 Retira / Delivery"
- Variables internas: `barra_occupied` → `retira_occupied`, `tab_barra` → `tab_retira`
- Comentarios actualizados

## Qué NO se cambió (7 ocurrencias correctas)
- Dict keys `"barra":` en type_labels (mapea valor DB a label — la key queda igual)
- `fetch_orders(["barra", "mostrador"])` — query a la DB
- `# ── BARRA DE BÚSQUEDA` — es la search bar, nada que ver con pedidos

## Para subir a GitHub
1. Andá a: https://github.com/kuaji28/dylan-restaurant/edit/main/app.py
2. Ctrl+A (seleccionar todo) → Ctrl+V (pegar el contenido del app.py descargado)
3. Click "Commit changes" → mensaje: "Reemplazar Barra por Retira en toda la UI"
4. Railway auto-deploya

## Alternativa: regenerar con script
Si perdiste el archivo descargado, corré `apply_replacements.py` (en esta misma carpeta).
