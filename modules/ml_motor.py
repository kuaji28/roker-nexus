"""
ROKER NEXUS — Motor ML
Migrado de roker_ml.py v3.0
Búsqueda, caché, calculadora y análisis de competencia.
"""
import re
import json
import requests
from database import get_ml_cache, guardar_ml_cache, guardar_termino_aprendido

ML_SEARCH_URL = "https://api.mercadolibre.com/sites/MLA/search"
ML_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Referer":         "https://www.mercadolibre.com.ar/",
}

TIENDA_FR       = "aitech"
TIENDA_MECANICO = "mecanico"

MARCA_ML = {
    "MOT": "motorola", "M": "motorola",
    "SAM": "samsung",  "SA": "samsung",
    "LG":  "lg",       "L": "lg",
    "XIA": "xiaomi",   "X": "xiaomi",
    "IPH": "iphone",   "APL": "iphone",
    "IN":  "infinix",  "TE": "tecno",
    "HUA": "huawei",   "HU": "huawei",
    "NOK": "nokia",    "TCL": "tcl",
    "ZTE": "zte",      "ALC": "alcatel",
    "OP":  "oppo",     "RE": "realme",
}

PALABRAS_RUIDO = {
    "AMP","AMM","ASS","T2O","W/F","S/MARCO","C/MARCO","LCD","COMPLETE",
    "TOUCH","OLED","INCELL","AMOLED","HIGH","COPY","ORIGINAL","FRAME",
    "BLACK","WHITE","LISTO","MECANICO","DISPLAY","PANTALLA","MODULO",
}
PALABRAS_CLAVE = {
    "PLUS","PRO","MAX","ULTRA","POWER","PLAY","LITE","5G","4G",
    "MINI","NOTE","EDGE","FOLD","5","5C","12","13","14","15","16",
}


def generar_termino_busqueda(proveedor_raw: str, descripcion: str) -> str:
    """Genera término de búsqueda limpio para ML."""
    marca_key = str(proveedor_raw).strip().upper()[:3]
    marca_ml  = MARCA_ML.get(marca_key, marca_key.lower())

    modelo = str(descripcion).upper()
    for pref in ["SAM ", "MOT ", "LG ", "XIA ", "IPH ", "HUA ", "IN ", "TE ",
                 "ALC ", "TCL ", "ZTE ", "RE ", "OP "]:
        if modelo.startswith(pref):
            modelo = modelo[len(pref):]
            break

    tokens = re.split(r'[\s/,]+', modelo)
    tokens_limpios = []
    for t in tokens:
        t = t.strip().rstrip(".")
        if not t: continue
        if re.match(r'^\d+', t) or t in PALABRAS_CLAVE:
            tokens_limpios.append(t.lower())
        elif t in PALABRAS_RUIDO:
            continue
        elif len(t) >= 2:
            tokens_limpios.append(t.lower())

    tiene_marco = any(p in descripcion.upper() for p in ["C/MARCO", "W/F", "FRAME"])
    termino_modelo = " ".join(tokens_limpios[:4])
    if tiene_marco:
        return f"modulo {marca_ml} {termino_modelo} con marco".strip()
    return f"modulo {marca_ml} {termino_modelo} mecanico".strip()


def limpiar_termino_manual(termino: str) -> str:
    return " ".join(termino.strip().lower().split())


def buscar_en_ml(termino: str, limit: int = 10, timeout: int = 12) -> list:
    """Búsqueda ML con fallback automático API → scraping web."""
    resultados = _buscar_api(termino, limit, timeout)
    if resultados is not None:
        return resultados
    resultados = _buscar_web(termino, limit, timeout)
    if resultados is not None:
        return resultados
    raise requests.RequestException(
        "Mercado Libre no respondió. Esperá 2-3 minutos y volvé a intentar."
    )


def buscar_con_cache(codigo: str, termino: str, forzar: bool = False) -> list:
    """Búsqueda con caché de 6hs para no saturar ML."""
    if not forzar:
        cached = get_ml_cache(codigo)
        if cached:
            return cached
    try:
        resultados = buscar_en_ml(termino)
        guardar_ml_cache(codigo, termino, resultados)
        guardar_termino_aprendido(codigo, termino)
        return resultados
    except requests.Timeout:
        raise ConnectionError("ML tardó demasiado. Verificá tu conexión.")
    except requests.ConnectionError:
        raise ConnectionError("Sin conexión a internet.")
    except requests.HTTPError as e:
        raise ConnectionError(f"Error ML: {e}")


def _buscar_api(termino: str, limit: int, timeout: int):
    params = {"q": termino, "limit": min(limit, 50)}
    try:
        r = requests.get(ML_SEARCH_URL, params=params, headers=ML_HEADERS, timeout=timeout)
        if r.status_code == 403:
            return None
        r.raise_for_status()
        return _parsear_respuesta_api(r.json())
    except requests.HTTPError:
        return None
    except (requests.ConnectionError, requests.Timeout) as e:
        raise requests.RequestException(f"Sin conexión: {e}")


def _buscar_web(termino: str, limit: int, timeout: int):
    import html as _html
    try:
        termino_url = termino.strip().replace(" ", "-")
        url = f"https://listado.mercadolibre.com.ar/{termino_url}"
        headers_web = {**ML_HEADERS, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
        r = requests.get(url, headers=headers_web, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None
        return _parsear_html_ml(r.text, limit)
    except Exception:
        return None


def _parsear_html_ml(html: str, limit: int) -> list:
    import html as _html, json as _json
    resultados = []
    for pattern in [
        r'"results"\s*:\s*(\[.*?\])\s*,\s*"paging"',
        r'window\.__PRELOADED_STATE__\s*=\s*(\{.+?\})\s*;?\s*</script>',
    ]:
        m = re.search(pattern, html, re.DOTALL)
        if m:
            try:
                raw = m.group(1)
                if raw.startswith("["):
                    items = _json.loads(raw)
                else:
                    obj = _json.loads(raw)
                    items = obj.get("initialState", obj).get("results", [])
                if items:
                    return _parsear_items_web(items[:limit])
            except Exception:
                continue

    titulos = re.findall(r'"title"\s*:\s*"([^"]{10,100})"', html)
    precios  = re.findall(r'"price"\s*:\s*(\d+(?:\.\d+)?)', html)
    links    = re.findall(r'"permalink"\s*:\s*"(https://www\.mercadolibre\.com\.ar/[^"]+)"', html)
    nicks    = re.findall(r'"nickname"\s*:\s*"([^"]{3,40})"', html)

    for i in range(min(len(titulos), len(precios), limit)):
        nick = nicks[i] if i < len(nicks) else ""
        resultados.append({
            "ml_id": "", "titulo": _html.unescape(titulos[i]),
            "precio_ars": float(precios[i]),
            "vendedor_nick": _html.unescape(nick),
            "tipo_tienda": _identificar_tienda(nick),
            "reputacion": "", "ventas_totales": 0,
            "link": links[i] if i < len(links) else "",
        })
    return resultados or None


def _parsear_items_web(items: list) -> list:
    resultados = []
    for item in items:
        try:
            seller = item.get("seller", {})
            nick   = seller.get("nickname", "")
            resultados.append({
                "ml_id": item.get("id",""), "titulo": item.get("title",""),
                "precio_ars": float(item.get("price", 0)),
                "vendedor_nick": nick, "tipo_tienda": _identificar_tienda(nick),
                "reputacion": "", "ventas_totales": 0,
                "link": item.get("permalink",""),
            })
        except Exception:
            continue
    return resultados or None


def _parsear_respuesta_api(data: dict) -> list:
    resultados = []
    for item in data.get("results", []):
        seller = item.get("seller", {})
        nick   = seller.get("nickname", "")
        resultados.append({
            "ml_id": item.get("id",""), "titulo": item.get("title",""),
            "precio_ars": float(item.get("price", 0)),
            "vendedor_nick": nick, "vendedor_id": str(seller.get("id","")),
            "tipo_tienda": _identificar_tienda(nick),
            "reputacion": item.get("seller_reputation",{}).get("level_id",""),
            "ventas_totales": item.get("seller_reputation",{}).get("transactions",{}).get("completed",0),
            "link": item.get("permalink",""),
        })
    return resultados


def _identificar_tienda(nickname: str) -> str:
    n = nickname.upper()
    if TIENDA_FR.upper() in n:       return "FR"
    if TIENDA_MECANICO.upper() in n: return "MECANICO"
    return "COMPETIDOR"


def calcular_precio_publicacion(lista1_ars: float, comision_ml_pct: float,
                                  margen_extra_pct: float = 0.0) -> dict:
    """
    Fórmula correcta:
      precio_base = lista1 × (1 + margen_extra/100)
      precio_ml   = precio_base ÷ (1 - comision/100)
    """
    if lista1_ars <= 0:
        return {"lista1_ars":0,"precio_base_ars":0,"precio_ml_ars":0,
                "precio_ml_redondeado":0,"comision_pagada_ars":0,
                "ganancia_neta_ars":0,"margen_real_pct":0}

    precio_base     = lista1_ars * (1 + margen_extra_pct / 100)
    comision_factor = comision_ml_pct / 100
    precio_ml       = precio_base / (1 - comision_factor) if comision_factor < 1 else precio_base * 2
    comision_pagada = precio_ml * comision_factor
    ganancia_neta   = precio_ml - comision_pagada

    return {
        "lista1_ars":           round(lista1_ars, 2),
        "precio_base_ars":      round(precio_base, 2),
        "precio_ml_ars":        round(precio_ml, 2),
        "precio_ml_redondeado": _redondear_precio_ml(precio_ml),
        "comision_pagada_ars":  round(comision_pagada, 2),
        "ganancia_neta_ars":    round(ganancia_neta, 2),
        "margen_real_pct":      round((ganancia_neta / lista1_ars - 1) * 100, 1),
    }


def calcular_comision_implicita(precio_publicado: float, precio_lista1: float) -> float:
    """Dado precio publicado y L1, calcula la comisión que está usando la empresa."""
    if precio_publicado <= 0 or precio_lista1 <= 0:
        return 0.0
    return round((1 - precio_lista1 / precio_publicado) * 100, 2)


def _redondear_precio_ml(precio: float) -> int:
    """Precio psicológico: 14.235 → 14.199, 89.500 → 89.499"""
    if precio < 1000:    return int(precio)
    elif precio < 10000:  base = int(precio / 100) * 100;  return base - 1
    elif precio < 100000: base = int(precio / 1000) * 1000; return base - 1
    else:                 base = int(precio / 5000) * 5000; return base - 1


def analizar_competencia(resultados_ml: list,
                          nuestro_precio_fr: float = 0,
                          nuestro_precio_mec: float = 0) -> list:
    """Enriquece resultados ML con comparación vs nuestros precios."""
    REP_MAP = {
        "5_green": "⭐⭐⭐⭐⭐ Excelente",
        "4_light_green": "⭐⭐⭐⭐ Muy bueno",
        "3_yellow": "⭐⭐⭐ Bueno",
        "2_orange": "⭐⭐ Regular",
        "1_red":    "⭐ Malo",
    }
    enriquecidos = []
    for item in resultados_ml:
        pml  = item["precio_ars"]
        tipo = item["tipo_tienda"]
        nuestro = (nuestro_precio_fr if tipo == "FR"
                   else nuestro_precio_mec if tipo == "MECANICO"
                   else nuestro_precio_fr or nuestro_precio_mec)
        if nuestro > 0 and pml > 0:
            diff = (pml - nuestro) / nuestro * 100
            estado = ("🟢 SOMOS MÁS BARATOS" if diff > 5
                      else "🔴 NOS SUPERAN" if diff < -5
                      else "🟡 PRECIO SIMILAR")
        else:
            diff, estado = 0, "—"
        enriquecidos.append({
            **item,
            "diferencia_pct":   round(diff, 1),
            "estado_vs_nos":    estado,
            "reputacion_str":   REP_MAP.get(item.get("reputacion",""), item.get("reputacion","")),
            "es_nuestra_tienda": tipo in ("FR", "MECANICO"),
        })
    enriquecidos.sort(key=lambda x: (not x["es_nuestra_tienda"], x["precio_ars"]))
    return enriquecidos


def formato_resultado_telegram(resultados: list, termino: str, max_items: int = 5) -> str:
    if not resultados:
        return f"❌ Sin resultados para: _{termino}_"
    lineas = [f"🔍 *ML: {termino}*\n"]
    for i, r in enumerate(resultados[:max_items], 1):
        emoji = "🏪 *NUESTRA TIENDA*" if r["es_nuestra_tienda"] else f"🏬 {r['vendedor_nick'][:20]}"
        lineas.append(
            f"{i}. {emoji}\n"
            f"   💵 ${r['precio_ars']:,.0f} ARS\n"
            f"   {r['estado_vs_nos']}\n"
            f"   🔗 {r.get('link','')}\n"
        )
    return "\n".join(lineas)
