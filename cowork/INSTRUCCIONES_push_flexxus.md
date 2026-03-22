# Cómo subir datos de Flexxus a Supabase — push_flexxus.py

> **Propósito:** Importar los archivos `.xlsx` de Flexxus directamente a Supabase (stock, artículos y ventas) con un doble-click. Sin necesidad de abrir el sistema Nexus.

---

## Cuándo usar este script

- Cuando actualizaste los archivos de stock en Flexxus y querés subirlos a Nexus sin pasar por la interfaz web.
- Para actualizaciones masivas o automáticas (ej: tarea programada en Windows).
- Como alternativa más rápida al botón "Importar" del sistema.

---

## Requisitos previos (solo la primera vez)

1. **Python** instalado en Windows (verificar: abrir cmd → `python --version`)
2. Instalar dependencias:
   ```
   pip install requests openpyxl pandas
   ```

---

## Preparar los archivos

Colocá los archivos en la carpeta:
```
C:\Users\kuaji\Documents\roker_nexus\Archivos flexxus\ARCHIVOS PARA COWORK\
```

### Archivos de stock (deben tener exactamente estos nombres):

| Archivo | Depósito |
|---------|----------|
| `JS.xlsx` | SAN JOSE (SJ) |
| `LAR.xlsx` | LARREA |
| `SAR.xlsx` | SARMIENTO |
| `FULLML.xlsx` | DEP. FULL ML |
| `ML.xlsx` | DEP. ML |
| `MERG.xlsx` | MERMAS |
| `RM.xlsx` | DEP. TRANSITORIO RMA |

> ⚠️ **Nombres exactos.** Si Flexxus genera "Planilla de Stock_15-03-2026 14-42-37.xlsx",
> primero pasalo por `etiquetar.py` o renombralo manualmente al código corto (ej: `SJ.xlsx`).

### Archivo de ventas:

Debe contener la palabra **"Resumida"** en el nombre.
Ejemplo: `Planilla de Ventas por Marca Resumida_15-03-2026.xlsx`

Si el nombre tiene fecha en formato `DD-MM-YYYY`, el script la detecta automáticamente.

---

## Ejecutar el script

**Opción A — Doble click:**
Hacé doble-click en `push_flexxus.py`. Windows abre una ventana de comandos y arranca automáticamente.

**Opción B — Desde la terminal:**
```bash
cd C:\Users\kuaji\Documents\roker_nexus
python push_flexxus.py
```

---

## Qué hace el script paso a paso

```
[1/3] STOCK SNAPSHOTS
  → JS.xlsx (SJ)     → tabla stock_snapshots
  → LAR.xlsx (LAR)   → tabla stock_snapshots
  ... (cada depósito)

[2/3] ARTÍCULOS (catálogo maestro)
  → Actualiza descripcion y tipo_codigo en tabla articulos

[3/3] VENTAS
  → *Resumida*.xlsx  → tabla ventas

LISTO. Total OK=XXXX  ERRORES=0
```

---

## Qué hacer si hay errores

| Mensaje | Causa | Solución |
|---------|-------|----------|
| `SKIP JS.xlsx (no encontrado)` | El archivo no está en la carpeta | Verificar nombre y ubicación |
| `HTTP 409` | Fila duplicada (ya existía) | Normal — el script usa upsert, continúa |
| `HTTP 422` | Datos inválidos (tipo de dato) | Abrí el xlsx y verificá que no haya filas corruptas |
| `ERROR: 'requests' no instalado` | Faltan dependencias | `pip install requests openpyxl pandas` |
| `ERROR: Carpeta no encontrada` | Ruta incorrecta | Asegurate que el script esté en la misma carpeta que `Archivos flexxus\` |

---

## Tablas que actualiza en Supabase

| Tabla | Clave única (upsert) | Datos |
|-------|---------------------|-------|
| `stock_snapshots` | `codigo + deposito + fecha` | Stock por depósito por día |
| `articulos` | `codigo` | Descripción y tipo de código |
| `ventas` | `codigo + fecha_desde + fecha_hasta` | Ventas del período |

Los datos **nunca se duplican**: si subís el mismo archivo dos veces, el segundo update reemplaza al primero (upsert).

---

## Notas importantes

- El script lee las planillas tal cual las exporta Flexxus (sin modificarlas).
- La fecha del snapshot se toma del nombre del archivo si tiene formato `DD-MM-YYYY`, o usa la fecha del día si no.
- Si `etiquetar.py` ya inyectó el nombre del depósito en el xlsx, el script lo detecta automáticamente.
- Los depósitos "contaminados" (MERMAS, RMA) se importan igual — el sistema Nexus los filtra al mostrar el stock activo.

---

*Generado automáticamente — Roker Nexus v2.3.0 — 17/03/2026*
