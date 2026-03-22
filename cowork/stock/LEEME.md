# 📁 stock/

## Estructura
```
stock/
├── san_jose/     ← SJ_stock_YYYY-MM-DD.xlsx   (depósito principal)
├── larrea/       ← LAR_stock_YYYY-MM-DD.xlsx  (local público)
├── full_ml/      ← FML_stock_YYYY-MM-DD.xlsx  (MercadoLibre Fulfillment)
└── sarmiento/    ← SAR_stock_YYYY-MM-DD.xlsx  (depósito adicional)
```

## Convención de nombre
`[SIGLA]_stock_YYYY-MM-DD.xlsx`

Siglas: `SJ` | `LAR` | `FML` | `SAR`

## Cómo descargar en Flexxus
Stock → Planilla de Stock → seleccionar depósito → exportar XLSX

## ⚠️ Importante al leer el archivo
- Header real en **fila índice 8** (fila 9 visible)
- Stock real en **columna índice 7** (aunque el header diga "Stock" en col 8)
- Columnas: [0]=Código, [2]=Artículo, [5]=Rubro, [7]=Stock

## Archivos disponibles (al 17/03/2026)
| Depósito | Archivo | Fecha | Estado |
|----------|---------|-------|--------|
| SAN JOSE | JS STOCK.xlsx | 15/03/2026 | ✅ En ARCHIVOS PARA COWORK |
| LARREA | LAR.xlsx | 15/03/2026 | ✅ En ARCHIVOS PARA COWORK |
| FULL ML | FULLML.xlsx | 15/03/2026 | ✅ En ARCHIVOS PARA COWORK |
| SARMIENTO | SAR.xlsx | 15/03/2026 | ✅ En ARCHIVOS PARA COWORK |
