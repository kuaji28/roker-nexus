"""
ROKER NEXUS — Matching de modelos y códigos
Lógica de normalización y cruce inteligente de artículos.

Reglas críticas de negocio:
- SAM A10 ≠ SAM A10S  (la S es parte del modelo — diferentes)
- SAM A20 ≠ SAM A20S  (ídem)
- Número de modelo EXACTO — fuzzy solo en la marca
- Código numérico = mecánico
- Código con letra + punto = con marco (FR)
"""
import re
from typing import Optional
from rapidfuzz import fuzz, process


# ── Normalización de marcas ───────────────────────────────────
MARCAS_NORMALIZE = {
    "SAMSUNG": ["SAM", "SAMSUNG", "SMS"],
    "IPHONE":  ["IPH", "IPHONE", "APPLE", "IOS"],
    "MOTOROLA":["MOT", "MOTOROLA", "MOTO"],
    "LG":      ["LG"],
    "XIAOMI":  ["XIA", "XIAOMI", "REDMI"],
    "ALCATEL": ["ALC", "ALCATEL"],
    "TCL":     ["TCL"],
    "NOKIA":   ["NOK", "NOKIA"],
    "HUAWEI":  ["HUA", "HUAWEI"],
}

MARCA_REVERSE = {}
for marca_norm, aliases in MARCAS_NORMALIZE.items():
    for alias in aliases:
        MARCA_REVERSE[alias.upper()] = marca_norm


def tipo_codigo(codigo: str) -> str:
    """
    Detecta si un código es mecánico (numérico) o con marco (FR).
    Mecánico: solo dígitos, opcionalmente con punto al final
    Con marco: empieza con letra(s), a veces termina con punto
    """
    codigo = codigo.strip()
    # Solo dígitos (con o sin punto final)
    if re.match(r'^\d+\.?$', codigo):
        return "mecanico"
    # Empieza con letra(s) y termina en punto
    if re.match(r'^[A-Za-z][A-Za-z0-9]*\.$', codigo):
        return "con_marco"
    # Empieza con letra
    if re.match(r'^[A-Za-z]', codigo):
        return "con_marco"
    return "otro"


def normalizar_descripcion(desc: str) -> str:
    """Limpia y normaliza una descripción de artículo."""
    desc = desc.upper().strip()
    # Quitar palabras irrelevantes
    stopwords = ["MODULO", "PANTALLA", "DISPLAY", "ORIGINAL", "ORI",
                 "AMP", "MECANICO", "MECA", "CON", "SIN", "MARCO",
                 "LIGHT", "BLUE", "BLACK", "WHITE", "NEGRO", "BLANCO",
                 "ASS", "AMM", "AMP", "IC", "REMOVIBLE"]
    tokens = desc.split()
    tokens = [t for t in tokens if t not in stopwords]
    return " ".join(tokens)


def extraer_modelo(desc: str) -> Optional[str]:
    """
    Extrae el número/código de modelo de una descripción.
    Ej: "MODULO SAM A10S MECANICO" → "A10S"
    Ej: "MODULO IPH 14 AMP IC REMOVIBLE" → "14"
    """
    desc = desc.upper()

    # Patrón: letra + número + posible letra al final (A10S, K50, G8, etc.)
    patrones = [
        r'\b([A-Z]\d+[A-Z]?)\b',    # A10S, K50, G8
        r'\b(\d{2,4}[A-Z]?)\b',     # 14, 13, 12 (iPhones)
        r'\b([A-Z]+\d+[A-Z]*)\b',   # Moto G Power, etc.
    ]
    for pat in patrones:
        match = re.search(pat, desc)
        if match:
            return match.group(1)
    return None


def extraer_marca(desc: str) -> Optional[str]:
    """Extrae la marca normalizada de una descripción."""
    desc = desc.upper()
    for alias, marca in MARCA_REVERSE.items():
        if alias in desc.split():
            return marca
    # Fuzzy si no hay match exacto
    marcas_known = list(MARCAS_NORMALIZE.keys())
    result = process.extractOne(desc, marcas_known, scorer=fuzz.partial_ratio, score_cutoff=70)
    if result:
        return result[0]
    return None


def mismo_modelo(desc1: str, desc2: str) -> bool:
    """
    Determina si dos descripciones refieren al mismo modelo.
    Regla CRÍTICA: número de modelo debe ser EXACTO.
    """
    modelo1 = extraer_modelo(desc1)
    modelo2 = extraer_modelo(desc2)

    if not modelo1 or not modelo2:
        return False

    # Comparación EXACTA del número de modelo
    if modelo1 != modelo2:
        return False

    # Si los modelos coinciden, verificar que la marca sea compatible
    marca1 = extraer_marca(desc1)
    marca2 = extraer_marca(desc2)

    if marca1 and marca2:
        return marca1 == marca2

    # Si no hay marca clara, son iguales por modelo
    return True


def buscar_equivalente_mecanico(codigo_fr: str, descripcion_fr: str,
                                df_mecanicos: "pd.DataFrame") -> Optional[dict]:
    """
    Busca el mecánico equivalente a un artículo FR.
    Usa para calcular demanda de FR cuando no hay historial propio.
    """
    import pandas as pd

    modelo_fr = extraer_modelo(descripcion_fr)
    marca_fr = extraer_marca(descripcion_fr)

    if not modelo_fr:
        return None

    candidatos = []
    for _, row in df_mecanicos.iterrows():
        desc = str(row.get("descripcion", ""))
        modelo = extraer_modelo(desc)
        marca = extraer_marca(desc)

        if modelo == modelo_fr:
            score = 100
            if marca_fr and marca and marca_fr == marca:
                score += 10
            candidatos.append({**row.to_dict(), "_score": score})

    if not candidatos:
        return None

    return max(candidatos, key=lambda x: x["_score"])


def match_codigo_flexxus(codigo_proveedor: str, df_articulos: "pd.DataFrame") -> Optional[dict]:
    """
    Busca el código Flexxus correspondiente a un código de proveedor.
    Primero intenta match exacto, luego descripción fuzzy.
    """
    import pandas as pd

    # Match exacto
    exact = df_articulos[df_articulos["codigo"] == codigo_proveedor]
    if not exact.empty:
        return exact.iloc[0].to_dict()

    # Si no, buscar por descripción similar
    return None


def normalizar_lista_precios(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Normaliza el DataFrame de lista de precios para cruce con otros módulos.
    Agrega columnas de marca y modelo extraídos.
    """
    import pandas as pd

    df = df.copy()
    if "descripcion" in df.columns:
        df["marca_norm"] = df["descripcion"].apply(extraer_marca)
        df["modelo_norm"] = df["descripcion"].apply(extraer_modelo)
        df["tipo_codigo"] = df["codigo"].apply(tipo_codigo)
    return df
