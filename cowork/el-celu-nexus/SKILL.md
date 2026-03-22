---
name: el-celu-nexus
description: >
  Contexto completo de trabajo para Roker en EL CELU (Argentina), tienda de accesorios y
  repuestos de celulares. Usar SIEMPRE que Roker mencione: módulos, pedidos, Mecánico,
  AI-TECH, FR, Flexxus, stock, ventas, Diego, Pablo, Mariano, cotización, demanda,
  depósitos, SAN JOSE, LARREA, SARMIENTO, RMA, o cualquier cosa relacionada con
  inventario/compras/reportes de EL CELU. También usar cuando pida armar un pedido,
  analizar ventas, hacer un reporte para Diego, o hablar de los proveedores de módulos.
  Este skill da contexto inmediato para no tener que re-explicar cada vez.
---

# El Celu Nexus — Contexto de Trabajo de Roker

## Cómo usar este skill

Al activarse, leer inmediatamente los tres archivos de referencia según lo que Roker necesite:

- **Siempre leer primero:** `references/contexto.md` — personas, empresa, estrategia, terminología
- **Si hay archivos Flexxus involucrados:** `references/archivos.md` — cómo leer cada tipo de archivo
- **Si hay cálculos de pedido o demanda:** `references/metodologia.md` — fórmulas y reglas

## Quién es Roker

Roker (kuaji28@gmail.com) trabaja de forma **externa** para EL CELU. Ex-empleado reconvocado. Su ventaja competitiva es el análisis de datos — hace lo que Mariano y Pablo no pueden. Su objetivo: demostrar valor irremplazable a Diego y Walter para negociar más honorarios.

## Contexto urgente (siempre presente)

- Proveedor activo de módulos: **SOLO MECÁNICO** (FR/AITECH pausado por Diego)
- Presupuesto módulos: U$S 300K (dividible en 2 lotes)
- Lead time aéreo: ~22 días promedio
- Pedido 039 en análisis — cobertura a confirmar con Roker
- Prioridades actuales: cerrar pedido 039 → reportes para Diego → mejoras sistema Nexus

## Reglas permanentes

1. **No crear archivos sin orden explícita de Roker** — análisis sí, archivos solo si lo pide
2. Antes de acciones importantes, hacer 1-2 preguntas de verificación
3. Precios siempre en USD como moneda base
4. FR activo = SJ + LAR + SAR + FML (NUNCA incluir MER, RMA, DTM, DML)
5. Demanda = ventas FR + ventas Mecánico del mismo modelo (sin mezclar códigos genéricos)

## Estado del sistema Nexus

- App Streamlit en producción: Streamlit Cloud
- Repo: github.com/kuaji28/roker-nexus
- DB: Supabase (PostgreSQL)
- Archivos de trabajo en: `/roker_nexus/` (carpeta workspace de Cowork)
- Registro de archivos: ver `REGISTRO.md` en la raíz del workspace

## Archivos de referencia de este skill

Lee los archivos según necesidad — no hace falta cargar todo en cada consulta:

| Archivo | Cuándo leerlo |
|---------|--------------|
| `references/contexto.md` | Siempre — personas, empresa, terminología |
| `references/archivos.md` | Cuando haya archivos Flexxus para analizar |
| `references/metodologia.md` | Cuando haya que calcular pedidos o demanda |
