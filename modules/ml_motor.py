"""
ROKER NEXUS — Motor ML
Búsqueda, caché, calculadora y análisis de competencia.
"""
import re, json, requests
from database import execute_query, query_to_df

ML_SEARCH_URL = "https://api.mercadolibre.com/sites/MLA/search"
ML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.mercadolibre.com.ar/",
}
TIENDA_FR  = "aitech"
TIENDA_MEC = "mecanico"

MARCA_ML = {
    "MOT":"motorola","M":"motorola","SAM":"samsung","SA":"samsung",
    "LG":"lg","L":"lg","XIA":"xiaomi","X":"xiaomi","IPH":"iphone",
    "IN":"infinix","TE":"tecno","HUA":"huawei","HU":"huawei",
    "NOK":"nokia","TCL":"tcl","ZTE":"zte","ALC":"alcatel","OP":"oppo","RE":"realme",
}
PALABRAS_RUIDO = {"AMP","AMM","W/F","S/MARCO","C/MARCO","LCD","TOUCH","OLED",
                  "INCELL","AMOLED","HIGH","COPY","ORIGINAL","FRAME","BLACK",
                  "WHITE","LISTO","MECANICO","DISPLAY","PANTALLA","MODULO"}
PALABRAS_CLAVE = {"PLUS","PRO","MAX","ULTRA","POWER","PLAY","LITE","5G","4G",
                  "MINI","NOTE","EDGE","FOLD"}

def _ensure_tables():
    execute_query("""CREATE TABLE IF NOT EXISTS ml_terminos_aprendidos (
        codigo TEXT PRIMARY KEY, termino_busqueda TEXT NOT NULL,
        ultima_busqueda TEXT DEFAULT (datetime('now')), total_busquedas INTEGER DEFAULT 0
    )""", fetch=False)
    execute_query("""CREATE TABLE IF NOT EXISTS ml_resultados_cache (
        codigo TEXT PRIMARY KEY, termino TEXT,
        resultados TEXT, timestamp TEXT DEFAULT (datetime('now'))
    )""", fetch=False)

def generar_termino(proveedor_raw: str, descripcion: str) -> str:
    marca_key = str(proveedor_raw).strip().upper()[:3]
    marca_ml  = MARCA_ML.get(marca_key, marca_key.lower())
    modelo = str(descripcion).upper()
    for pref in ["SAM ","MOT ","LG ","XIA ","IPH ","HUA ","IN ","TE ","ALC ","TCL ","ZTE ","RE ","OP "]:
        if modelo.startswith(pref): modelo = modelo[len(pref):]; break
    tokens = re.split(r'[\s/,]+', modelo)
    limpios = []
    for t in tokens:
        t = t.strip().rstrip(".")
        if not t: continue
        if re.match(r'^\d+', t) or t in PALABRAS_CLAVE: limpios.append(t.lower())
        elif t in PALABRAS_RUIDO: continue
        elif len(t) >= 2: limpios.append(t.lower())
    tiene_marco = any(p in descripcion.upper() for p in ["C/MARCO","W/F","FRAME"])
    modelo_str = " ".join(limpios[:4])
    if tiene_marco: return f"modulo {marca_ml} {modelo_str} con marco".strip()
    return f"modulo {marca_ml} {modelo_str} mecanico".strip()

def buscar_en_ml(termino: str, limit: int = 10, timeout: int = 12) -> list:
    res = _buscar_api(termino, limit, timeout)
    if res is not None: return res
    res = _buscar_web(termino, limit, timeout)
    if res is not None: return res
    raise requests.RequestException("ML no respondió. Esperá 2-3 min y reintentá.")

def buscar_con_cache(codigo: str, termino: str, forzar: bool = False) -> list:
    _ensure_tables()
    if not forzar:
        rows = execute_query("SELECT resultados, timestamp FROM ml_resultados_cache WHERE codigo=?", (codigo,))
        if rows:
            try:
                from datetime import datetime
                ts = datetime.fromisoformat(rows[0]["timestamp"])
                if (datetime.now()-ts).total_seconds() < 6*3600:
                    return json.loads(rows[0]["resultados"])
            except Exception: pass
    resultados = buscar_en_ml(termino)
    execute_query("""INSERT INTO ml_resultados_cache (codigo,termino,resultados,timestamp)
        VALUES(?,?,?,datetime('now')) ON CONFLICT(codigo) DO UPDATE SET
        termino=excluded.termino, resultados=excluded.resultados, timestamp=datetime('now')
    """, (codigo, termino, json.dumps(resultados, ensure_ascii=False)), fetch=False)
    execute_query("""INSERT INTO ml_terminos_aprendidos (codigo,termino_busqueda,ultima_busqueda,total_busquedas)
        VALUES(?,?,datetime('now'),1) ON CONFLICT(codigo) DO UPDATE SET
        termino_busqueda=excluded.termino_busqueda, ultima_busqueda=datetime('now'),
        total_busquedas=total_busquedas+1
    """, (codigo, termino), fetch=False)
    return resultados

def _buscar_api(termino, limit, timeout):
    try:
        r = requests.get(ML_SEARCH_URL, params={"q":termino,"limit":min(limit,50)},
                         headers=ML_HEADERS, timeout=timeout)
        if r.status_code == 403: return None
        r.raise_for_status()
        return _parsear_api(r.json())
    except requests.HTTPError: return None
    except (requests.ConnectionError, requests.Timeout) as e:
        raise requests.RequestException(f"Sin conexión: {e}")

def _buscar_web(termino, limit, timeout):
    try:
        url = f"https://listado.mercadolibre.com.ar/{termino.replace(' ','-')}"
        r = requests.get(url, headers={**ML_HEADERS,"Accept":"text/html,*/*"}, timeout=timeout)
        if r.status_code != 200: return None
        return _parsear_html(r.text, limit)
    except Exception: return None

def _parsear_api(data):
    res = []
    for item in data.get("results",[]):
        s = item.get("seller",{})
        nick = s.get("nickname","")
        res.append({"ml_id":item.get("id",""),"titulo":item.get("title",""),
                    "precio_ars":float(item.get("price",0)),
                    "vendedor_nick":nick,"tipo_tienda":_tipo_tienda(nick),
                    "reputacion":item.get("seller_reputation",{}).get("level_id",""),
                    "link":item.get("permalink","")})
    return res

def _parsear_html(html, limit):
    import re as _re, html as _html
    titulos = _re.findall(r'"title"\s*:\s*"([^"]{10,100})"', html)
    precios  = _re.findall(r'"price"\s*:\s*(\d+(?:\.\d+)?)', html)
    links    = _re.findall(r'"permalink"\s*:\s*"(https://www\.mercadolibre\.com\.ar/[^"]+)"', html)
    nicks    = _re.findall(r'"nickname"\s*:\s*"([^"]{3,40})"', html)
    res = []
    for i in range(min(len(titulos),len(precios),limit)):
        nick = nicks[i] if i<len(nicks) else ""
        res.append({"ml_id":"","titulo":_html.unescape(titulos[i]),
                    "precio_ars":float(precios[i]),"vendedor_nick":nick,
                    "tipo_tienda":_tipo_tienda(nick),
                    "reputacion":"","link":links[i] if i<len(links) else ""})
    return res or None

def _tipo_tienda(nick):
    n = nick.upper()
    if TIENDA_FR.upper() in n: return "AI-TECH"
    if TIENDA_MEC.upper() in n: return "MECANICO"
    return "COMPETIDOR"

def calcular_precio_publicacion(lista1_ars: float, comision_ml_pct: float,
                                  margen_extra_pct: float = 0.0) -> dict:
    if lista1_ars <= 0:
        return {"lista1_ars":0,"precio_base_ars":0,"precio_ml_ars":0,
                "precio_ml_redondeado":0,"comision_pagada_ars":0,"ganancia_neta_ars":0,"margen_real_pct":0}
    precio_base = lista1_ars * (1 + margen_extra_pct/100)
    cf = comision_ml_pct/100
    precio_ml = precio_base / (1-cf) if cf < 1 else precio_base*2
    com_pag = precio_ml * cf
    gan = precio_ml - com_pag
    return {
        "lista1_ars": round(lista1_ars,2),
        "precio_base_ars": round(precio_base,2),
        "precio_ml_ars": round(precio_ml,2),
        "precio_ml_redondeado": _redondear(precio_ml),
        "comision_pagada_ars": round(com_pag,2),
        "ganancia_neta_ars": round(gan,2),
        "margen_real_pct": round((gan/lista1_ars-1)*100,1),
    }

def calcular_comision_implicita(precio_pub: float, lista1: float) -> float:
    if precio_pub <= 0 or lista1 <= 0: return 0.0
    return round((1 - lista1/precio_pub)*100, 2)

def _redondear(precio: float) -> int:
    if precio < 1000: return int(precio)
    elif precio < 10000:  base=int(precio/100)*100;  return base-1
    elif precio < 100000: base=int(precio/1000)*1000; return base-1
    else:                 base=int(precio/5000)*5000; return base-1

def analizar_competencia(resultados, nuestro_fr=0, nuestro_mec=0):
    REP = {"5_green":"⭐⭐⭐⭐⭐ Excelente","4_light_green":"⭐⭐⭐⭐ Muy bueno",
           "3_yellow":"⭐⭐⭐ Bueno","2_orange":"⭐⭐ Regular","1_red":"⭐ Malo"}
    out = []
    for item in resultados:
        pml  = item["precio_ars"]
        tipo = item["tipo_tienda"]
        nuestro = (nuestro_fr if tipo=="AI-TECH" else nuestro_mec if tipo=="MECANICO"
                   else nuestro_fr or nuestro_mec)
        if nuestro > 0 and pml > 0:
            diff = (pml-nuestro)/nuestro*100
            estado = "🟢 SOMOS MÁS BARATOS" if diff>5 else "🔴 NOS SUPERAN" if diff<-5 else "🟡 PRECIO SIMILAR"
        else:
            diff, estado = 0, "—"
        out.append({**item,
            "diferencia_pct":round(diff,1),"estado_vs_nos":estado,
            "reputacion_str":REP.get(item.get("reputacion",""),item.get("reputacion","")),
            "es_nuestra_tienda": tipo in ("FR","MECANICO")})
    out.sort(key=lambda x: (not x["es_nuestra_tienda"], x["precio_ars"]))
    return out

def get_termino_aprendido(codigo: str):
    _ensure_tables()
    rows = execute_query("SELECT termino_busqueda FROM ml_terminos_aprendidos WHERE codigo=?", (codigo,))
    return rows[0]["termino_busqueda"] if rows else None
