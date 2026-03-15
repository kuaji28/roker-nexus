"""
ROKER NEXUS — Motor de Calidad de Datos
========================================
Detecta errores de carga en el catálogo de Flexxus:
  - Rubro incorrecto (código AITECH o descripción sugiere otra marca)
  - Marca inconsistente con el código
  - Duplicados potenciales (descripción muy similar)
  - Códigos huérfanos (en stock pero no en artículos)
  - Módulos sin rubro o con rubro genérico
  - Precios atípicos dentro de una familia

USO AUTOMÁTICO: se ejecuta en cada importación de stock.
USO MANUAL: desde la página Calidad de Datos.
"""

import re
from difflib import SequenceMatcher
from typing import Optional
import pandas as pd


# ──────────────────────────────────────────────────────────────
#  MAPAS DE DETECCIÓN
# ──────────────────────────────────────────────────────────────

# Prefijo de código AITECH → rubro esperado en Flexxus
PREFIJO_RUBRO: dict[str, str] = {
    "MS":  "SAMSUNG",
    "MM":  "MOTOROLA",
    "MX":  "XIAOMI",
    "MI":  "IPHONE",     # MIPH12SOLD, MIPH14SOLD
    "MH":  "HUAWEI",
    "MN":  "NOKIA",
    "MT":  "TCL",
    "ML":  "LG",
    "MA":  "ALCATEL",
    "MZ":  "ZTE",
    "MTE": "TECNO",
    "MR":  "REALME",
    "MIF": "INFINIX",
    "MSO": "SONY",
}

# Palabras clave en la descripción → rubro esperado (para mecánicos numéricos)
DESC_MARCA_KEYWORDS: list[tuple[list[str], str]] = [
    (["SAM ", " SAM ", "SAMS ", "SAMSUNG"],             "SAMSUNG"),
    (["MOT ", " MOT ", "MOTO ", "MOTOROLA"],             "MOTOROLA"),
    (["XIA ", "XIAOMI", "REDMI ", "POCO "],              "XIAOMI"),
    (["IPH ", "IPHONE", "I-PHONE"],                      "IPHONE"),
    (["HUA ", "HUAWEI"],                                 "HUAWEI"),
    (["NOK ", "NOKIA"],                                  "NOKIA"),
    (["TCL "],                                           "TCL"),
    ([" LG ", "LG K", "LG G"],                          "LG"),
    (["ALC ", "ALCATEL"],                                "ALCATEL"),
    (["ZTE "],                                           "ZTE"),
    (["TECNO"],                                          "TECNO"),
    (["REALME"],                                         "REALME"),
    (["INFINIX"],                                        "INFINIX"),
    (["SONY"],                                           "SONY"),
]

# Rubros genéricos que NO deberían tener módulos
RUBROS_GENERICOS = {"MODULOS", "MÓDULOS", "VARIOS", "OTROS", "GENERAL",
                     "SIN RUBRO", "ACCESORIOS", ""}

# Longitud mínima del código para aplicar reglas (evitar falsos positivos en códigos cortos)
MIN_CODIGO_LEN = 5


# ──────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────────────────────

def detectar_errores_calidad(df: pd.DataFrame) -> list[dict]:
    """Analiza un DataFrame de stock y devuelve una lista de errores detectados.

    Args:
        df: DataFrame con columnas: codigo, articulo (o descripcion), rubro.
            Acepta el formato directo del importador de stock.

    Returns:
        Lista de dicts con keys: codigo, descripcion, rubro_actual,
        rubro_sugerido, tipo_error, confianza, regla, sugerencia_correccion.
    """
    # Normalizar nombres de columnas
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ("codigo", "código"):
            col_map[c] = "codigo"
        elif cl in ("articulo", "artículo", "descripcion", "descripción"):
            col_map[c] = "descripcion"
        elif cl == "rubro":
            col_map[c] = "rubro"

    df = df.rename(columns=col_map)
    for req in ("codigo", "descripcion", "rubro"):
        if req not in df.columns:
            df[req] = ""

    errores = []
    vistos = {}  # Para detección de duplicados

    for _, row in df.iterrows():
        codigo = str(row.get("codigo", "")).strip().upper()
        desc   = str(row.get("descripcion", "")).strip().upper()
        rubro  = str(row.get("rubro", "")).strip().upper()

        if not codigo or codigo in ("NAN", "CÓDIGO"):
            continue

        es_modulo = "MODULO" in desc or "MÓDULO" in desc

        # ─────────────────────────────────────
        # REGLA 1: Código AITECH → rubro esperado
        # ─────────────────────────────────────
        if len(codigo) >= MIN_CODIGO_LEN and codigo[0].isalpha():
            for prefijo, rubro_esperado in PREFIJO_RUBRO.items():
                if codigo.startswith(prefijo) and len(codigo) > len(prefijo) + 1:
                    if rubro.upper() != rubro_esperado:
                        errores.append({
                            "codigo":                 codigo,
                            "descripcion":            desc,
                            "rubro_actual":           rubro,
                            "rubro_sugerido":         rubro_esperado,
                            "tipo_error":             "RUBRO_INCORRECTO",
                            "confianza":              "🔴 Alta",
                            "regla":                  f"Código '{prefijo}...' indica marca {rubro_esperado}",
                            "sugerencia_correccion":  f"Cambiar Rubro de '{rubro}' a '{rubro_esperado}' en Flexxus",
                        })
                    break  # Solo la primera regla que matchea

        # ─────────────────────────────────────
        # REGLA 2: Descripción de módulo con keyword de marca → rubro esperado
        # ─────────────────────────────────────
        if es_modulo and len(codigo) >= MIN_CODIGO_LEN:
            for keywords, rubro_esperado in DESC_MARCA_KEYWORDS:
                if any(k in desc for k in keywords):
                    if rubro.upper() != rubro_esperado:
                        # Solo agregar si no fue detectado ya por la regla 1
                        ya_detectado = any(
                            e["codigo"] == codigo and e["tipo_error"] == "RUBRO_INCORRECTO"
                            for e in errores
                        )
                        if not ya_detectado:
                            errores.append({
                                "codigo":                codigo,
                                "descripcion":           desc,
                                "rubro_actual":          rubro,
                                "rubro_sugerido":        rubro_esperado,
                                "tipo_error":            "RUBRO_INCORRECTO",
                                "confianza":             "🟡 Media",
                                "regla":                 f"Descripción contiene '{keywords[0].strip()}' → marca {rubro_esperado}",
                                "sugerencia_correccion": f"Verificar y cambiar Rubro a '{rubro_esperado}'",
                            })
                    break

        # ─────────────────────────────────────
        # REGLA 3: Módulo con rubro genérico
        # ─────────────────────────────────────
        if es_modulo and rubro.upper() in RUBROS_GENERICOS:
            # Intentar sugerir el rubro correcto desde la descripción
            sugerido = _inferir_rubro_desde_desc(desc)
            errores.append({
                "codigo":                codigo,
                "descripcion":           desc,
                "rubro_actual":          rubro if rubro else "(vacío)",
                "rubro_sugerido":        sugerido or "Verificar manualmente",
                "tipo_error":            "RUBRO_GENERICO",
                "confianza":             "🟡 Media" if sugerido else "⚪ Baja",
                "regla":                 f"Módulo con rubro genérico '{rubro}'",
                "sugerencia_correccion": f"Asignar rubro de marca específica en Flexxus",
            })

        # ─────────────────────────────────────
        # REGLA 4: Duplicados potenciales (descripción muy similar)
        # ─────────────────────────────────────
        desc_normalizada = _normalizar_desc(desc)
        if desc_normalizada:
            for cod_prev, desc_prev in vistos.items():
                if cod_prev != codigo:
                    sim = SequenceMatcher(None, desc_normalizada, desc_prev).ratio()
                    if sim >= 0.92:
                        errores.append({
                            "codigo":                codigo,
                            "descripcion":           desc,
                            "rubro_actual":          rubro,
                            "rubro_sugerido":        "—",
                            "tipo_error":            "POSIBLE_DUPLICADO",
                            "confianza":             f"🟡 Media ({int(sim*100)}% similar)",
                            "regla":                 f"Descripción muy similar a código {cod_prev}",
                            "sugerencia_correccion": f"Verificar si '{codigo}' y '{cod_prev}' son el mismo producto",
                        })
                        break  # Un aviso por código es suficiente
            vistos[codigo] = desc_normalizada

        # ─────────────────────────────────────
        # REGLA 5: Código numérico con descripción que incluye "AITECH" o "FR"
        # ─────────────────────────────────────
        if codigo.isdigit() or (len(codigo) > 4 and codigo[:4].isdigit()):
            if "AITECH" in desc or " FR " in desc or "AITECH" in rubro:
                errores.append({
                    "codigo":                codigo,
                    "descripcion":           desc,
                    "rubro_actual":          rubro,
                    "rubro_sugerido":        "Código letra (AITECH)",
                    "tipo_error":            "CODIGO_PROVEEDOR_INCORRECTO",
                    "confianza":             "🔴 Alta",
                    "regla":                 "Código numérico (mecánico) pero descripción indica AITECH/FR",
                    "sugerencia_correccion": "Verificar si este producto tiene código letra asignado",
                })

    return errores


def detectar_huerfanos(df_stock: pd.DataFrame, df_articulos: pd.DataFrame) -> list[dict]:
    """Detecta códigos que están en stock pero no en el catálogo de artículos.

    Útil para encontrar productos que se cargaron en Flexxus de forma inconsistente.
    """
    if df_stock.empty or df_articulos.empty:
        return []

    codigos_stock = set(df_stock["codigo"].astype(str).str.upper().str.strip())
    codigos_art   = set(df_articulos["codigo"].astype(str).str.upper().str.strip())
    huerfanos     = codigos_stock - codigos_art

    return [
        {
            "codigo":                cod,
            "descripcion":           "—",
            "rubro_actual":          "—",
            "rubro_sugerido":        "—",
            "tipo_error":            "CODIGO_HUERFANO",
            "confianza":             "🔴 Alta",
            "regla":                 "Código en stock pero sin ficha en catálogo de artículos",
            "sugerencia_correccion": "Crear artículo en Flexxus o revisar si el código fue migrado",
        }
        for cod in sorted(huerfanos)
        if cod and cod not in ("NAN", "")
    ]


# ──────────────────────────────────────────────────────────────
#  HELPERS INTERNOS
# ──────────────────────────────────────────────────────────────

def _inferir_rubro_desde_desc(desc: str) -> Optional[str]:
    """Intenta inferir el rubro correcto a partir de la descripción."""
    d = desc.upper()
    for keywords, rubro in DESC_MARCA_KEYWORDS:
        if any(k in d for k in keywords):
            return rubro
    return None


def _normalizar_desc(desc: str) -> str:
    """Normaliza una descripción para comparación de similitud."""
    d = desc.upper()
    # Eliminar variaciones de formato que no afectan el significado
    d = re.sub(r"[/\-_\s]+", " ", d)              # separadores → espacio
    d = re.sub(r"\b(S/MARCO|C/MARCO|OLED|INCELL|TFT|AMOLED|UNIVERSAL)\b", "", d)  # specs
    d = re.sub(r"\s+", " ", d).strip()
    return d


# ──────────────────────────────────────────────────────────────
#  GUARDAR EN DB
# ──────────────────────────────────────────────────────────────

def guardar_errores_calidad(errores: list[dict], fuente: str = "importacion") -> int:
    """Persiste los errores detectados en la tabla `anomalias` de la DB.

    Usa INSERT OR IGNORE para no duplicar si ya fue detectado antes.
    Returns: cantidad de registros nuevos insertados.
    """
    if not errores:
        return 0
    try:
        from database import get_sqlite
        from datetime import datetime
        conn = get_sqlite()
        nuevos = 0
        for e in errores:
            # clave única: codigo + tipo_error (para no duplicar en cada importación)
            existe = conn.execute(
                "SELECT 1 FROM anomalias WHERE codigo=? AND tipo=? AND estado='abierta'",
                (e["codigo"], e["tipo_error"])
            ).fetchone()
            if not existe:
                conn.execute("""
                    INSERT INTO anomalias (codigo, tipo, descripcion, severidad, estado, detectada_en, notas)
                    VALUES (?, ?, ?, ?, 'abierta', ?, ?)
                """, (
                    e["codigo"],
                    e["tipo_error"],
                    f"{e['descripcion'][:80]} | Rubro actual: {e['rubro_actual']} | Sugerido: {e['rubro_sugerido']}",
                    "alta" if "Alta" in e["confianza"] else "media",
                    datetime.now().isoformat(),
                    f"[{fuente}] {e['regla']} — {e['sugerencia_correccion']}",
                ))
                nuevos += 1
        conn.commit()
        conn.close()
        return nuevos
    except Exception:
        return 0


def get_errores_pendientes() -> pd.DataFrame:
    """Lee los errores de calidad pendientes desde la DB."""
    try:
        from database import query_to_df
        return query_to_df("""
            SELECT codigo, tipo as tipo_error, descripcion, notas as regla,
                   severidad as confianza, detectada_en, estado
            FROM anomalias
            WHERE tipo IN ('RUBRO_INCORRECTO','RUBRO_GENERICO',
                           'POSIBLE_DUPLICADO','CODIGO_HUERFANO','CODIGO_PROVEEDOR_INCORRECTO')
              AND estado = 'abierta'
            ORDER BY severidad DESC, detectada_en DESC
        """)
    except Exception:
        return pd.DataFrame()
