"""
VERIFICADOR DE ARCHIVOS FLEXXUS — ROKER NEXUS
Uso: python3 control/verificar_archivo.py <archivo.xlsx>
Detecta automáticamente el tipo y valida columnas, totales y anomalías.
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# ── Configuración de tipos de archivo ────────────────────────────────────────
TIPOS = {
    "stock_general": {
        "keywords": ["listado stock", "stock larrea", "stock san jose", "stock sarmiento"],
        "header_fila": 8,
        "cols": {0: "codigo", 2: "articulo", 5: "rubro", 7: "stock", 9: "s_min", 10: "s_max"},
        "col_total": 7,
        "col_verificar": "stock",
    },
    "optimizacion": {
        "keywords": ["optimizacion", "optimización", "stock minimo", "stock mínimo"],
        "header_fila": 11,
        "cols": {0: "codigo", 1: "articulo", 5: "demanda_total", 7: "demanda_prom", 8: "s_actual", 9: "s_min", 10: "s_opt", 11: "s_max"},
        "col_total": 8,
        "col_verificar": "s_actual",
    },
    "lista_precios": {
        "keywords": ["lista 1", "lista1", "p. comp", "mg.1"],
        "header_fila": 0,
        "cols": {0: "codigo", 1: "articulo", 2: "lista1", 9: "p_comp", 13: "stock_actual"},
        "col_total": 13,
        "col_verificar": "stock_actual",
    },
    "ventas_marca": {
        "keywords": ["planilla de ventas por marca", "total vta", "total unid"],
        "header_fila": 8,
        "cols": {0: "codigo", 1: "articulo", 5: "rubro", 7: "total_vta", 10: "total_uds"},
        "col_total": 7,
        "col_verificar": "total_vta",
    },
    "compras_marca": {
        "keywords": ["planilla de compras por marca", "compras por marca"],
        "header_fila": 7,
        "cols": {0: "codigo", 1: "articulo", 5: "rubro", 8: "marca", 10: "cantidad"},
        "col_total": 10,
        "col_verificar": "cantidad",
    },
    "rma": {
        "keywords": ["seguimiento rma", "nro. rma", "rma anulados"],
        "header_fila": 4,
        "cols": {0: "fecha", 1: "nro_rma", 2: "cliente", 5: "codigo", 7: "articulo", 10: "proveedor", 13: "costo", 14: "defecto"},
        "col_total": 13,
        "col_verificar": "costo",
    },
}

def detectar_tipo(df_raw, nombre_archivo):
    """Detecta el tipo de archivo por nombre y contenido."""
    nombre = nombre_archivo.lower()
    contenido = " ".join(df_raw.head(15).fillna("").astype(str).values.flatten()).lower()
    texto = nombre + " " + contenido

    for tipo, cfg in TIPOS.items():
        if any(kw in texto for kw in cfg["keywords"]):
            return tipo, cfg
    return None, None

def leer_datos(df_raw, cfg):
    """Extrae datos según configuración del tipo."""
    hf = cfg["header_fila"]
    data = df_raw.iloc[hf + 1:].copy().reset_index(drop=True)

    resultado = pd.DataFrame()
    for col_idx, col_nombre in cfg["cols"].items():
        if col_idx < len(data.columns):
            resultado[col_nombre] = data.iloc[:, col_idx]

    # Limpiar código
    if "codigo" in resultado.columns:
        resultado["codigo"] = resultado["codigo"].astype(str).str.strip().str.rstrip(".")
        resultado = resultado[resultado["codigo"].str.len() > 2]
        resultado = resultado[~resultado["codigo"].str.startswith("nan")]
        resultado = resultado[~resultado["codigo"].str.startswith("Cantidad")]
        resultado = resultado[~resultado["codigo"].str.contains(r"^\d{2}/\d{2}/\d{4}$", regex=True, na=False)]

    # Convertir columna principal a numérico
    col_v = cfg["col_verificar"]
    if col_v in resultado.columns:
        resultado[col_v] = resultado[col_v].apply(
            lambda x: pd.to_numeric(str(x).replace(".","").replace(",","."), errors="coerce")
        ).fillna(0)

    return resultado

def verificar(archivo):
    print(f"\n{'='*60}")
    print(f"VERIFICADOR ROKER NEXUS")
    print(f"Archivo: {Path(archivo).name}")
    print(f"{'='*60}")

    try:
        ext = Path(archivo).suffix.lower()
        engine = "xlrd" if ext == ".xls" else "openpyxl"
        df_raw = pd.read_excel(archivo, header=None, engine=engine)
    except Exception as e:
        print(f"❌ ERROR leyendo archivo: {e}")
        return

    tipo, cfg = detectar_tipo(df_raw, Path(archivo).name)
    if not tipo:
        print("⚠️  No se pudo detectar el tipo de archivo automáticamente.")
        print("   Tipos soportados:", list(TIPOS.keys()))
        return

    print(f"✅ Tipo detectado: {tipo.upper()}")
    print(f"   Header en fila: {cfg['header_fila']}")

    data = leer_datos(df_raw, cfg)
    col_v = cfg["col_verificar"]

    print(f"\n📊 RESUMEN:")
    print(f"   Total filas de datos: {len(data)}")
    if col_v in data.columns:
        total = data[col_v].sum()
        con_valor = (data[col_v] > 0).sum()
        sin_valor = (data[col_v] == 0).sum()
        print(f"   Total {col_v}: {total:,.2f}")
        print(f"   Con valor > 0: {con_valor}")
        print(f"   Con valor = 0: {sin_valor}")

    # Análisis de módulos
    if "articulo" in data.columns:
        mods = data[data["articulo"].astype(str).str.upper().str.startswith("MODULO")]
        print(f"\n📦 MÓDULOS:")
        print(f"   Total SKUs módulos: {len(mods)}")
        if col_v in mods.columns:
            print(f"   {col_v} módulos: {mods[col_v].sum():,.2f}")
            print(f"   Módulos con valor > 0: {(mods[col_v] > 0).sum()}")
            print(f"   Módulos con valor = 0: {(mods[col_v] == 0).sum()}")

    # Alertas
    print(f"\n⚠️  ALERTAS:")
    alertas = 0

    # Ceros en RMA
    if tipo == "rma" and "costo" in data.columns and "articulo" in data.columns:
        ceros = data[(data["costo"] == 0) & (data["articulo"].str.len() > 3)]
        if len(ceros) > 0:
            print(f"   🔴 {len(ceros)} devoluciones con costo $0 (pérdida no registrada)")
            alertas += 1

    # Duplicados de código
    if "codigo" in data.columns:
        dupes = data[data.duplicated(subset=["codigo"], keep=False)]
        if tipo not in ["rma", "ventas_marca"] and len(dupes) > 0:
            print(f"   🟡 {len(dupes)} códigos duplicados (puede ser normal en ventas/RMA)")
            alertas += 1

    # Columna principal toda en cero
    if col_v in data.columns and data[col_v].sum() == 0:
        print(f"   🔴 CRÍTICO: columna '{col_v}' suma 0 — posible error de columna")
        alertas += 1
        # Sugerir columna alternativa
        print("   🔍 Buscando columna con valores...")
        raw_data = df_raw.iloc[cfg["header_fila"]+1:]
        for i in range(min(15, len(df_raw.columns))):
            vals = pd.to_numeric(raw_data.iloc[:,i].astype(str).str.replace(".","").str.replace(",","."), errors="coerce").dropna()
            nz = vals[vals > 0]
            if len(nz) > 10:
                print(f"      → Col {i} tiene {len(nz)} valores positivos, suma={nz.sum():.0f}")

    if alertas == 0:
        print("   ✅ Sin alertas críticas")

    print(f"\n{'='*60}")
    print("Verificación completa. Guardar captura de este output")
    print("como respaldo antes de importar al sistema.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 control/verificar_archivo.py <archivo.xlsx>")
        print("Ejemplo: python3 control/verificar_archivo.py control/archivos_raw/STOCK_LARREA_20260315.xlsx")
    else:
        verificar(sys.argv[1])
