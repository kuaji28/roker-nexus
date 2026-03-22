# Archivos Flexxus — Cómo leerlos

## Estructura de carpetas del workspace

```
roker_nexus/
├── CLAUDE.md              ← Memoria del proyecto (leer siempre)
├── REGISTRO.md            ← Qué archivos hay y cuáles faltan
├── METODOLOGIA.md         ← Fórmulas y reglas de cálculo
├── ventas/
│   ├── por_mes/           ← YYYY-MM_ventas.xlsx (un archivo por mes)
│   └── acumulado/         ← períodos largos (ej: 165 días)
├── stock/
│   ├── san_jose/          ← SJ_stock_YYYY-MM-DD.xlsx
│   ├── larrea/            ← LAR_stock_YYYY-MM-DD.xlsx
│   ├── full_ml/           ← FML_stock_YYYY-MM-DD.xlsx
│   └── sarmiento/         ← SAR_stock_YYYY-MM-DD.xlsx
├── pedidos/
│   ├── cotizaciones/      ← cotizaciones de proveedores
│   └── ordenes/           ← pedidos armados
├── precios/               ← lista_precios_YYYY-MM-DD.xlsx
├── reportes/
│   ├── para_diego/        ← presentaciones ejecutivas
│   └── analisis/          ← análisis internos
└── Archivos flexxus/
    └── ARCHIVOS PARA COWORK/  ← archivos crudos de Flexxus
```

## Cómo leer cada tipo de archivo

### Planilla de Stock (SJ.xlsx, LAR.xlsx, etc.)
```python
df = pd.read_excel(path, header=None)
# Header real en fila ÍNDICE 8 (fila 9 visible)
# Usar: skiprows=8, header=0
# Columnas: [0]=Código, [2]=Artículo, [5]=Rubro, [7]=Stock
# ⚠️ Stock en columna ÍNDICE 7, NO columna 8 aunque el header diga "Stock"
```

### Planilla de Ventas por Marca Resumida
```python
df = pd.read_excel(path, header=8)
# ⚠️ El archivo tiene 11 columnas (no 9). Usar índices positionales:
# [0]=codigo, [1]=articulo, [2]=superrubro, [3]=unnamed, [4]=rubro,
# [5]=marca, [6]=total_vta, [7]=total_unid, [8]=bultos, [9]=familia, [10]=unnamed
df2 = df.iloc[:, [0,1,2,4,5,6,7,9]].copy()
df2.columns = ['codigo','articulo','superrubro','rubro','marca','total_vta','total_unid','familia']
df2 = df2[df2['codigo'].notna() & ~df2['codigo'].astype(str).str.contains('Conceptos', na=False)]
# total_unid viene como string con coma decimal:
df2['total_unid'] = pd.to_numeric(df2['total_unid'].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
df2['total_vta'] = pd.to_numeric(df2['total_vta'].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
```

### Optimización de Stock
```python
df = pd.read_excel(path, header=11)
# Columnas: Código, Artículo, ..., Demanda Total, Demanda Prom. (mensual), S. Actual
# Demanda Prom. = promedio MENSUAL (dividir por 30 para obtener diario)
# Período implícito: ~6 meses (Demanda Total / Demanda Prom. ≈ 6)
```

### Cotización AI-TECH / Mecánico 039
```python
df = pd.read_excel(path, header=1)
# Columna marca: requiere ffill() — viene con celdas combinadas
# Columnas: marca, mec_code, mec_nombre, fr_equiv, spec, tipo, calidad,
#           color, qty, precio_rmb, total_rmb
# mec_code puede tener sufijo .0 por conversión float → limpiar con .str.replace(r'\.0$','')
```

### Listado Histórico de Artículos (por producto)
```python
df = pd.read_excel(path, header=6)
# Columnas: Comprobante, Fecha, Cliente/Proveedor/Usuario, Ingreso, Egreso, Saldo, ...
# Excluir filas TOTALES: df[~df['Comprobante'].astype(str).str.startswith('TOTAL')]
# Fechas: pd.to_datetime(col, dayfirst=True)
```

### Lista de Precios
```python
df = pd.read_excel(path)
# Columnas incluyen: Código, Descripción, Lista 1, Lista 4, P. Comp.
# Los precios ya están en USD (moneda base)
```

## Detección de módulos

```python
es_modulo = (
    df['articulo'].str.upper().str.contains('MODULO', na=False) |
    df['codigo'].str.match(r'^[A-Z]{1,2}[A-Z]', na=False)
)
# Código numérico → Mecánico
# Código alfabético → FR/AITECH
```

## Depósitos activos vs contaminados

| Para sumar en FR_activo | Para EXCLUIR |
|------------------------|-------------|
| SJ, LAR, SAR, FML | MER, RMA, DTM, DML |

## Problemas conocidos

- **Archivos XLS:** `xlrd` no disponible en la VM → pedirle a Roker que exporte como .xlsx
- **CRC errors en xlsx:** usar `zf.ZipExtFile._update_crc = lambda self, newdata: None`
- **Archivos subidos:** pueden llegar a `/mnt/uploads/` o a `Archivos flexxus/ARCHIVOS PARA COWORK/`
- **Nombres Flexxus:** siempre genera "Planilla de Stock_DD-MM-YYYY HH-MM-SS.xlsx" — usar etiquetar.py para renombrar

## Convención de nombres de archivo

```
[TIPO]_[SIGLA]_YYYY-MM-DD.xlsx

Tipos:   stock | ventas | precios | pedido | cotizacion
Siglas:  SJ | LAR | FML | SAR | MEC (mecánico) | FR (AITECH)

Ejemplos:
  SJ_stock_2026-03-15.xlsx
  2026-02_ventas.xlsx
  MECANICO_039_cotizacion_2026-03-05.xlsx
```
