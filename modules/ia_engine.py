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
