# ROKER NEXUS — Solución de Persistencia con Supabase

## EL PROBLEMA
Streamlit Cloud borra el archivo SQLite cada vez que hace un reboot.
Resultado: se pierden todos los datos importados.

## LA SOLUCIÓN: Activar Supabase (ya tenés cuenta)

### PASO 1 — Ejecutar el schema en Supabase
1. Ir a: https://supabase.com/dashboard → tu proyecto zjrabazzvckvxhufppoa
2. SQL Editor → New query
3. Pegar el contenido de: supabase_schema.sql (ya está en tu repo)
4. Click "Run"

### PASO 2 — Configurar Streamlit Cloud
1. Ir a: https://share.streamlit.io
2. Tu app → Manage app → Settings → Secrets
3. Agregar exactamente esto (reemplazando con tus valores reales):

```toml
SUPABASE_URL = "https://zjrabazzvckvxhufppoa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
ANTHROPIC_API_KEY = "sk-ant-api03-..."
GEMINI_API_KEY = ""
TELEGRAM_TOKEN = "8600755595:AAEfMyQKYNI_wrCORNKTJB6u2xsW3JanFJg"
TELEGRAM_CHAT_ID = "5427210648"
MONEDA_USD_ARS = "1420"
```

4. Save → Streamlit reinicia automáticamente
5. La próxima vez que cargues los archivos de Flexxus, se guardan en Supabase
   y NO se pierden nunca más, aunque haga reboot.

### MIENTRAS TANTO (sin Supabase)
- Los datos persisten DENTRO de una sesión de Streamlit
- Se pierden solo si Streamlit hace "reboot" o deploy nuevo
- Solución manual: cargar los archivos de Flexxus después de cada reboot
  (tarda menos de 1 minuto)

### NUEVO CHAT SIN PERDER CONTEXTO
1. Ir a claude.ai → Projects → New Project
2. Subir los archivos del repo al proyecto (1 vez)
3. Abrir nuevas conversaciones dentro del proyecto
4. Todos los chats del proyecto comparten los archivos
