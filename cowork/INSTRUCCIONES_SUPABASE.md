# ROKER NEXUS — Activar Persistencia con Supabase PostgreSQL

## EL PROBLEMA
Streamlit Cloud borra el archivo SQLite cada vez que hace un reboot.
Resultado: se pierden todos los datos importados.

## LA SOLUCIÓN: Conexión directa a PostgreSQL de Supabase

---

## PASO 1 — Crear las tablas en Supabase

1. Ir a: https://supabase.com/dashboard → proyecto `zjrabazzvckvxhufppoa`
2. SQL Editor → New query
3. Pegar el contenido completo de `supabase_schema.sql`
4. Click **Run** → debería decir "Success. No rows returned"

---

## PASO 2 — Obtener el DATABASE_URL

1. En Supabase Dashboard → **Project Settings** (ícono engranaje) → **Database**
2. Scroll hasta la sección **Connection string**
3. Seleccionar **URI**
4. Copiar la cadena completa — se ve así:
   ```
   postgresql://postgres:[TU-PASSWORD]@db.zjrabazzvckvxhufppoa.supabase.co:5432/postgres
   ```
5. ⚠️ Reemplazar `[YOUR-PASSWORD]` con la contraseña real de tu proyecto Supabase

---

## PASO 3 — Configurar Streamlit Cloud

1. Ir a: https://share.streamlit.io
2. Tu app → **Manage app** → **Settings** → **Secrets**
3. Agregar exactamente esto:

```toml
DATABASE_URL = "postgresql://postgres:[TU-PASSWORD]@db.zjrabazzvckvxhufppoa.supabase.co:5432/postgres"
ANTHROPIC_API_KEY = "sk-ant-api03-..."
GEMINI_API_KEY = ""
TELEGRAM_TOKEN = "8600755595:AAEfMyQKYNI_wrCORNKTJB6u2xsW3JanFJg"
TELEGRAM_CHAT_ID = "5427210648"
MONEDA_USD_ARS = "1420"
```

4. **Save** → Streamlit reinicia automáticamente

---

## PASO 4 — Configurar Railway (bot Telegram)

1. Railway → tu proyecto → **Variables**
2. Agregar:
   ```
   DATABASE_URL = "postgresql://postgres:[TU-PASSWORD]@db.zjrabazzvckvxhufppoa.supabase.co:5432/postgres"
   TELEGRAM_TOKEN = "8600755595:..."
   TELEGRAM_CHAT_ID = "5427210648"
   ```
3. Railway → **Settings** → **Build Command** → dejar **VACÍO** → Save → Deploy

---

## PASO 5 — Verificar que funciona

1. Abrir la app en Streamlit Cloud
2. Ir a **Sistema** → verificar que dice "PostgreSQL" en el estado de DB
3. Cargar los archivos de Flexxus una vez
4. Esperar a que Streamlit haga un reboot (o forzarlo desde Manage app → Reboot)
5. Los datos deben seguir ahí ✅

---

## CÓMO FUNCIONA (resumen técnico)

```
database.py detecta DATABASE_URL en el entorno
       ↓
USE_POSTGRES = True
       ↓
Todas las queries van a PostgreSQL de Supabase
       ↓
Los datos sobreviven cualquier reboot de Streamlit Cloud
       ↓
Railway y Streamlit Cloud comparten la misma base de datos
```

Si DATABASE_URL NO está configurado → cae a SQLite local (modo desarrollo).

---

## TROUBLESHOOTING

**"connection refused" o "SSL error":**
- Agregar `?sslmode=require` al final del DATABASE_URL
- Ejemplo: `postgresql://postgres:...@db.xxx.supabase.co:5432/postgres?sslmode=require`

**"relation does not exist":**
- Las tablas no fueron creadas → repetir PASO 1

**Los datos siguen desapareciendo:**
- Verificar en Sistema que dice "PostgreSQL" (no "SQLite")
- Si dice "SQLite", el DATABASE_URL no fue configurado correctamente

---
*Actualizado: 2026-03-15*

---

## TABLAS NUEVAS — Ejecutar en Supabase SQL Editor

Copiá y pegá esto en el SQL Editor de Supabase para crear las tablas nuevas:

```sql
-- Tabla de ingresos de mercadería (packing China vs Flexxus)
CREATE TABLE IF NOT EXISTS ingresos_mercaderia (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER,
    invoice_id TEXT,
    codigo TEXT NOT NULL,
    descripcion TEXT,
    cantidad_pedida INTEGER DEFAULT 0,
    cantidad_ingresada INTEGER DEFAULT 0,
    diferencia INTEGER DEFAULT 0,
    fecha_ingreso TEXT,
    fecha_flexxus TEXT,
    confirmado INTEGER DEFAULT 0,
    notas TEXT,
    creado_en TIMESTAMPTZ DEFAULT now()
);

-- Tabla de alertas de stock (subidas y caídas detectadas al importar)
CREATE TABLE IF NOT EXISTS stock_alertas (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    descripcion TEXT,
    deposito TEXT,
    stock_anterior REAL DEFAULT 0,
    stock_nuevo REAL DEFAULT 0,
    diferencia REAL DEFAULT 0,
    tipo_alerta TEXT NOT NULL,
    severidad TEXT DEFAULT 'info',
    visto INTEGER DEFAULT 0,
    fecha TIMESTAMPTZ DEFAULT now()
);
```
