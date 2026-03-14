"""
ROKER NEXUS — Motor de IA
Claude como motor principal, Gemini como secundario activable.
"""
import json
from typing import Optional
import streamlit as st

from config import (
    ANTHROPIC_API_KEY, GEMINI_API_KEY,
    MODELO_CLAUDE, MODELO_GEMINI, MODO_IA, EMPRESA_NOMBRE
)

SYSTEM_PROMPT = f"""Sos el asistente de inteligencia comercial de {EMPRESA_NOMBRE}, una empresa de repuestos de celulares en Argentina.
Tu rol es ayudar a Sergio (el encargado de compras y gestión de stock) a tomar decisiones inteligentes.

Contexto del negocio:
- Vendés módulos y repuestos de celulares (Samsung, iPhone, Motorola, LG, Xiaomi, Alcatel)
- Tenés 3 depósitos: San José (central), Larrea Nuevo (local principal), ES Local
- Los precios están en USD pero se vende en ARS
- Lista 1 = precio mayorista, Lista 4 = MercadoLibre
- Hay dos tipos de artículos: Mecánicos (código numérico) y Con Marco/FR (código con letra)
- Los FR están pausados actualmente

Reglas críticas:
- SAM A10 ≠ SAM A10S (modelos distintos, nunca los confundas)
- Stock 0 no siempre es porque no se vende — puede haber habido quiebre
- San José abastece a Larrea — si Larrea quiebra, preguntar si San José tiene stock

Siempre respondé en español rioplatense, de forma directa y útil.
Cuando hay números, dá análisis concretos con recomendaciones de acción.
"""


class MotorIA:
    """Motor de IA con soporte Claude + Gemini."""

    def __init__(self):
        self._claude_client = None
        self._gemini_model = None

    @property
    def claude_disponible(self) -> bool:
        return bool(ANTHROPIC_API_KEY)

    @property
    def gemini_disponible(self) -> bool:
        return bool(GEMINI_API_KEY)

    def _get_claude(self):
        if self._claude_client is None and self.claude_disponible:
            try:
                import anthropic
                self._claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            except Exception:
                pass
        return self._claude_client

    def _get_gemini(self):
        if self._gemini_model is None and self.gemini_disponible:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                self._gemini_model = genai.GenerativeModel(
                    model_name=MODELO_GEMINI,
                    system_instruction=SYSTEM_PROMPT
                )
            except Exception:
                pass
        return self._gemini_model

    def consultar(self, prompt: str, modo: Optional[str] = None,
                  contexto_datos: Optional[dict] = None) -> str:
        """
        Envía una consulta al motor de IA.
        modo: 'claude' | 'gemini' | None (usa config global)
        """
        modo = modo or MODO_IA

        # Enriquecer prompt con contexto de datos si está disponible
        prompt_completo = prompt
        if contexto_datos:
            ctx_str = json.dumps(contexto_datos, ensure_ascii=False, indent=2)
            prompt_completo = f"Datos del sistema:\n```json\n{ctx_str}\n```\n\n{prompt}"

        if modo == "claude" and self.claude_disponible:
            return self._consultar_claude(prompt_completo)
        elif modo == "gemini" and self.gemini_disponible:
            return self._consultar_gemini(prompt_completo)
        elif self.claude_disponible:
            return self._consultar_claude(prompt_completo)
        elif self.gemini_disponible:
            return self._consultar_gemini(prompt_completo)
        else:
            return "⚠️ No hay IA configurada. Configurá ANTHROPIC_API_KEY o GEMINI_API_KEY en .env"

    def _consultar_claude(self, prompt: str) -> str:
        try:
            client = self._get_claude()
            response = client.messages.create(
                model=MODELO_CLAUDE,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Error Claude: {e}"

    def _consultar_gemini(self, prompt: str) -> str:
        try:
            model = self._get_gemini()
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error Gemini: {e}"

    def analizar_quiebres(self, df_quiebres) -> str:
        """Analiza el DataFrame de quiebres y da recomendaciones."""
        if df_quiebres.empty:
            return "✅ No hay quiebres detectados."
        resumen = df_quiebres.head(20).to_dict("records")
        return self.consultar(
            f"Analizá estos {len(df_quiebres)} artículos con quiebre o stock bajo. "
            f"Identificá los más urgentes y qué acción tomar:",
            contexto_datos={"quiebres": resumen}
        )

    def sugerir_lote_compra(self, df_sugerencias, tope_usd: float) -> str:
        """Sugiere qué comprar dado un tope de USD."""
        resumen = df_sugerencias.head(30).to_dict("records")
        return self.consultar(
            f"Con un tope de USD {tope_usd:,.0f}, ¿qué artículos recomendás priorizar en el próximo lote de compra? "
            f"Considerá demanda, stock actual y costo de reposición.",
            contexto_datos={"articulos_a_reponer": resumen}
        )

    def analizar_cotizacion(self, df_cotizacion) -> str:
        """Analiza una cotización de proveedor."""
        resumen = df_cotizacion.head(20).to_dict("records")
        total = df_cotizacion["precio_usd"].sum() if "precio_usd" in df_cotizacion.columns else 0
        return self.consultar(
            f"Tengo una cotización de AI-TECH por USD {total:,.0f}. "
            f"Analizá cuáles artículos vale la pena incluir en el pedido considerando stock actual:",
            contexto_datos={"cotizacion": resumen}
        )



    def consultar_paralelo(self, prompt: str) -> dict:
        """
        Consulta en paralelo a todos los IAs disponibles.
        Retorna dict {nombre_ia: respuesta}
        """
        import threading
        resultados = {}
        lock = threading.Lock()

        def _llamar(nombre, fn):
            try:
                resp = fn(prompt)
                with lock:
                    resultados[nombre] = resp
            except Exception as e:
                with lock:
                    resultados[nombre] = f"Error: {e}"

        threads = []
        if self.claude_disponible:
            t = threading.Thread(target=_llamar, args=("Claude", self._consultar_claude))
            threads.append(t)
        if self.gemini_disponible:
            t = threading.Thread(target=_llamar, args=("Gemini", self._consultar_gemini))
            threads.append(t)

        # GPT si está configurado
        from config import _get_secret
        gpt_key = _get_secret("OPENAI_API_KEY")
        if gpt_key:
            def _gpt(p):
                try:
                    import openai
                    client = openai.OpenAI(api_key=gpt_key)
                    r = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": p}
                        ],
                        max_tokens=1000
                    )
                    return r.choices[0].message.content
                except Exception as e:
                    return f"Error GPT: {e}"
            t = threading.Thread(target=_llamar, args=("GPT", _gpt))
            threads.append(t)

        if not threads:
            return {"Sin IA": "⚠️ No hay claves de IA configuradas."}

        for t in threads: t.start()
        for t in threads: t.join(timeout=30)

        if not resultados:
            return {"Error": "Tiempo agotado o sin respuesta."}
        return resultados

    def calcular_ventas_fantasmas(self) -> list:
        """
        Detecta productos donde el ERP muestra 0 ventas por quiebre de stock.
        Si la demanda cayó a 0 en el mismo período en que el stock era 0,
        proyecta la demanda latente.
        Retorna lista de dicts con: codigo, descripcion, demanda_proyectada, impacto_usd_mes
        """
        from database import query_to_df
        df = query_to_df("""
            SELECT o.codigo, COALESCE(a.descripcion, o.descripcion) as descripcion,
                   o.demanda_promedio, o.stock_actual, o.costo_reposicion,
                   a.marca
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo=a.codigo
            WHERE o.stock_actual = 0
              AND (o.demanda_promedio = 0 OR o.demanda_promedio IS NULL)
              AND COALESCE(a.en_lista_negra, 0) = 0
            ORDER BY o.costo_reposicion DESC
        """)
        if df.empty:
            return []

        # Buscar el promedio histórico de artículos similares de la misma marca/rubro
        df_hist = query_to_df("""
            SELECT a.marca, AVG(o.demanda_promedio) as dem_prom_marca
            FROM optimizacion o JOIN articulos a ON o.codigo=a.codigo
            WHERE o.demanda_promedio > 0 AND o.stock_actual > 0
            GROUP BY a.marca
        """)
        prom_marca = {}
        if not df_hist.empty:
            for _, r in df_hist.iterrows():
                prom_marca[str(r.get("marca",""))] = float(r.get("dem_prom_marca") or 0)

        fantasmas = []
        for _, r in df.iterrows():
            marca = str(r.get("marca",""))
            dem_ref = prom_marca.get(marca, 3.0)  # default 3 uds/mes si no hay referencia
            costo = float(r.get("costo_reposicion") or 0)
            impacto = dem_ref * costo

            fantasmas.append({
                "codigo":              r["codigo"],
                "descripcion":         str(r.get("descripcion",""))[:40],
                "marca":               marca,
                "dem_proyectada_mes":  round(dem_ref, 1),
                "impacto_usd_mes":     round(impacto, 2),
                "confianza":           "Media" if marca in prom_marca else "Baja",
            })

        return sorted(fantasmas, key=lambda x: -x["impacto_usd_mes"])[:50]

    def detectar_picos_demanda(self, umbral_pct: float = 50.0) -> list:
        """
        Detecta productos donde la demanda del último período es
        X% mayor que el promedio histórico.
        """
        from database import query_to_df
        # Comparar optimizacion (período actual) vs promedio histórico de ventas
        df = query_to_df("""
            SELECT o.codigo, COALESCE(a.descripcion, o.descripcion) as descripcion,
                   o.demanda_promedio as dem_actual,
                   o.stock_actual, o.stock_optimo, o.costo_reposicion,
                   CASE WHEN o.stock_actual < o.stock_optimo * 0.3 THEN 1 ELSE 0 END as critico
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo=a.codigo
            WHERE o.demanda_promedio > 0
              AND o.stock_actual >= 0
              AND COALESCE(a.en_lista_negra, 0) = 0
            ORDER BY o.demanda_promedio DESC
            LIMIT 200
        """)
        if df.empty:
            return []

        picos = []
        # Sin historial previo usamos el promedio general como referencia
        promedio_general = float(df["dem_actual"].mean())

        for _, r in df.iterrows():
            dem = float(r.get("dem_actual") or 0)
            if dem > promedio_general * (1 + umbral_pct/100):
                stk = float(r.get("stock_actual") or 0)
                dem_mes = dem
                dias_cobertura = int(stk / (dem_mes/30)) if dem_mes > 0 else 999
                picos.append({
                    "codigo":          r["codigo"],
                    "descripcion":     str(r.get("descripcion",""))[:40],
                    "dem_actual":      round(dem, 1),
                    "pct_sobre_media": round((dem/promedio_general - 1)*100, 1),
                    "dias_cobertura":  dias_cobertura,
                    "alerta":          dias_cobertura < 15,
                })
        return sorted(picos, key=lambda x: -x["pct_sobre_media"])

    def optimizar_lote_roi(self, tope_usd: float, proveedor: str = "TODOS") -> list:
        """
        Optimizador de lote por ROI.
        Score = 60% margen + 40% rotación (demanda).
        Los críticos (stock=0) siempre entran primero.
        """
        from database import query_to_df
        df = query_to_df("""
            SELECT o.codigo, COALESCE(a.descripcion, o.descripcion) as descripcion,
                   o.stock_actual, o.stock_optimo, o.demanda_promedio,
                   o.costo_reposicion,
                   p.lista_1 as precio_lista1,
                   (o.stock_optimo - o.stock_actual) as a_pedir,
                   ((o.stock_optimo - o.stock_actual) * o.costo_reposicion) as subtotal_usd
            FROM optimizacion o
            LEFT JOIN articulos a ON o.codigo=a.codigo
            LEFT JOIN precios p ON o.codigo=p.codigo
            WHERE o.stock_actual < o.stock_optimo
              AND o.costo_reposicion > 0
              AND (o.stock_optimo - o.stock_actual) > 0
              AND COALESCE(a.en_lista_negra, 0) = 0
        """)
        if df.empty:
            return []

        # Filtrar por proveedor
        if "MECÁNICO" in proveedor.upper() or "MECANICO" in proveedor.upper():
            df = df[df["codigo"].str[0].str.isdigit()]
        elif "FR" in proveedor.upper() or "AITECH" in proveedor.upper():
            df = df[df["codigo"].str[0].str.isalpha()]

        # Calcular score ROI
        max_dem = float(df["demanda_promedio"].max() or 1)
        max_costo = float(df["costo_reposicion"].max() or 1)

        def score(r):
            dem = max(0.0, float(r.get("demanda_promedio") or 0))
            costo = float(r.get("costo_reposicion") or 0)
            l1 = float(r.get("precio_lista1") or 0)
            # Margen estimado
            margen = (l1 - costo) / l1 if l1 > 0 else 0
            margen = max(0, min(1, margen))
            # Rotación normalizada
            rotacion = dem / max_dem if max_dem > 0 else 0
            # Críticos (stock=0) → bonus
            critico_bonus = 0.3 if float(r.get("stock_actual") or 0) == 0 else 0
            return round(0.6 * margen + 0.4 * rotacion + critico_bonus, 4)

        df["score_roi"] = df.apply(score, axis=1)
        df = df.sort_values("score_roi", ascending=False)

        # Llenar hasta el tope
        seleccionados = []
        acumulado = 0.0
        for _, r in df.iterrows():
            sub = float(r.get("subtotal_usd") or 0)
            if acumulado + sub <= tope_usd:
                seleccionados.append({
                    "codigo":        r["codigo"],
                    "descripcion":   str(r.get("descripcion",""))[:40],
                    "a_pedir":       int(r.get("a_pedir") or 0),
                    "precio_usd":    float(r.get("costo_reposicion") or 0),
                    "subtotal_usd":  round(sub, 2),
                    "score_roi":     float(r.get("score_roi") or 0),
                    "es_critico":    float(r.get("stock_actual") or 0) == 0,
                })
                acumulado += sub
        return seleccionados

    def alertas_margen_dolar(self, tasa_nueva: float) -> list:
        """
        Cuando cambia la tasa USD/ARS, detecta artículos donde
        el margen cae por debajo del umbral configurado.
        """
        from database import query_to_df, get_config
        umbral = float(get_config("umbral_margen_minimo", float) or 40)

        df = query_to_df("""
            SELECT p.codigo, a.descripcion, p.lista_1, p.lista_4
            FROM precios p JOIN articulos a ON p.codigo=a.codigo
            WHERE p.lista_1 > 0 AND p.lista_4 > 0
        """)
        if df.empty:
            return []

        alertas = []
        for _, r in df.iterrows():
            l1_usd = float(r.get("lista_1") or 0)
            l4_ars = float(r.get("lista_4") or 0)
            costo_ars = l1_usd * tasa_nueva
            if l4_ars > 0 and costo_ars > 0:
                margen_pct = (l4_ars - costo_ars) / l4_ars * 100
                if margen_pct < umbral:
                    precio_sugerido = costo_ars / (1 - umbral/100)
                    alertas.append({
                        "codigo":           r["codigo"],
                        "descripcion":      str(r.get("descripcion",""))[:35],
                        "l1_usd":           l1_usd,
                        "precio_ml_actual": l4_ars,
                        "margen_actual_pct": round(margen_pct, 1),
                        "precio_sugerido":  round(precio_sugerido, 0),
                    })
        return sorted(alertas, key=lambda x: x["margen_actual_pct"])[:20]


# Instancia global
motor_ia = MotorIA()


def chat_con_ia(historial: list, nuevo_mensaje: str,
                modo: Optional[str] = None) -> str:
    """
    Chat con contexto de conversación (para el chatbot del sistema).
    historial: lista de dicts {"role": "user"|"assistant", "content": "..."}
    """
    if not historial:
        return motor_ia.consultar(nuevo_mensaje, modo=modo)

    if motor_ia.claude_disponible and (modo is None or modo == "claude"):
        try:
            import anthropic
            client = motor_ia._get_claude()
            messages = historial + [{"role": "user", "content": nuevo_mensaje}]
            response = client.messages.create(
                model=MODELO_CLAUDE,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            return f"Error: {e}"

    return motor_ia.consultar(nuevo_mensaje, modo=modo)
