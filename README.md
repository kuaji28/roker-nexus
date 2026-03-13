# ⚡ ROKER NEXUS

Sistema de gestión comercial para El Celu — repuestos de celulares, Argentina.

---

## 🚀 Instalación en 5 minutos

### 1. Clonar y configurar
```bash
git clone https://github.com/TU_USUARIO/roker-nexus.git
cd roker-nexus
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus claves (ver sección Configuración)
```

### 4. Inicializar base de datos
```bash
python -c "from database import init_db; init_db(); print('✅ BD lista')"
```

### 5. Ejecutar la app
```bash
streamlit run app.py
```

---

## 🔑 Configuración (.env)

```env
SUPABASE_URL=https://zjrabazzvckvxhufppoa.supabase.co
SUPABASE_KEY=eyJhbGci...               # anon public key
ANTHROPIC_API_KEY=sk-ant-api03-...     # Claude API
TELEGRAM_TOKEN=8600755595:AAE...       # Token del bot
TELEGRAM_CHAT_ID=TU_CHAT_ID           # Tu ID personal
GEMINI_API_KEY=                        # Opcional
MONEDA_USD_ARS=1200
```

---

## 📁 Estructura del proyecto

```
roker-nexus/
├── app.py                    # App principal Streamlit
├── config.py                 # Configuración centralizada
├── database.py               # Base de datos (SQLite/Supabase)
├── telegram_bot.py           # Bot de Telegram (proceso separado)
├── requirements.txt
├── .env                      # Variables de entorno (NO subir a GitHub)
├── importers/
│   ├── flexxus_optimizacion.py
│   ├── flexxus_lista_precios.py
│   ├── flexxus_stock.py
│   ├── flexxus_ventas.py
│   └── aitech_mariano.py
├── modules/
│   ├── ia_engine.py          # Claude + Gemini
│   └── inventario.py         # Lógica de quiebres
├── pages/
│   ├── dashboard.py
│   ├── importar.py
│   ├── compras.py
│   ├── inventario.py
│   ├── precios.py
│   └── asistente.py
└── utils/
    ├── helpers.py
    ├── horarios.py
    └── matching.py
```

---

## 📊 Archivos de Flexxus

| Archivo | Módulo Flexxus | Frecuencia |
|---------|---------------|------------|
| `Optimizacin_de_Stock_FECHA.XLS` | Stock → Optimización de Stock | Mensual |
| `Lista de Precios_FECHA.XLS` | Ventas → Lista de Precios Editable | Al cambiar |
| `Planilla_de_Stock_DEPOSITO.XLS` | Stock → Listado General (×3) | Semanal |
| `Planilla de Ventas por Marca Resumida_FECHA.XLS` | Informes → Ventas | Mensual |
| `Planilla de Ventas por Marca_FECHA.XLS` | Informes → Compras | Mensual |
| `Planilla Detallada de Remitos - Remitos Internos_FECHA.XLS` | Remitos Internos | Ante quiebre |

---

## 🤖 Bot de Telegram

Ejecutar en proceso separado:
```bash
python telegram_bot.py
```

Comandos disponibles:
- `/stock [código]` — Stock en todos los depósitos
- `/precio [código]` — Precios Lista 1 y ML
- `/quiebres` — Top 10 urgentes
- `/sinstock` — Lista completa sin stock
- `/transito` — Pedidos en tránsito
- `/negra [código]` — Agregar a lista negra
- `/config tasa_usd [valor]` — Actualizar tipo de cambio
- `/resumen` — Estado ejecutivo
- `/ia [consulta]` — Preguntarle a Claude

---

## 🌐 Deploy en Streamlit Cloud

1. Subir código a GitHub (privado)
2. Ir a [share.streamlit.io](https://share.streamlit.io)
3. Conectar repo `roker-nexus`
4. File: `app.py`
5. En **Secrets**, pegar el contenido del `.env`:
```toml
SUPABASE_URL = "https://..."
SUPABASE_KEY = "eyJ..."
ANTHROPIC_API_KEY = "sk-ant-..."
TELEGRAM_TOKEN = "860..."
TELEGRAM_CHAT_ID = "123456789"
MONEDA_USD_ARS = "1200"
```

---

## ⚡ Actualizaciones rápidas por Telegram

Para cambios de configuración sin tocar código:
```
/config tasa_usd 1250
/config umbral_quiebre 15
```

---

Desarrollado con ❤️ para El Celu · Quilmes, Buenos Aires
