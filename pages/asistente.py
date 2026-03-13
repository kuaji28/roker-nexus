"""
ROKER NEXUS — Página: Asistente IA
Chat con Claude/Gemini + panel de actualización por Telegram.
"""
import streamlit as st
from modules.ia_engine import chat_con_ia, motor_ia, SYSTEM_PROMPT
from config import MODO_IA


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:700;color:var(--nx-text)">
        🤖 Asistente IA
    </h1>
    <p style="color:var(--nx-text2);font-size:14px;margin-bottom:20px">
        Consultá al sistema, analizá datos, pedí sugerencias
    </p>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "💬 Chat",
        "⚡ Actualizaciones",
        "⚙️ Configuración IA",
    ])

    # ── Tab: Chat ─────────────────────────────────────────────
    with tabs[0]:
        col_chat, col_acc = st.columns([3, 1])

        with col_chat:
            # Selector de motor
            modo = st.radio(
                "Motor de IA",
                ["Claude (principal)", "Gemini (secundario)"],
                horizontal=True,
                label_visibility="collapsed",
                key="radio_modo_ia",
            )
            modo_key = "claude" if "Claude" in modo else "gemini"

            # Disponibilidad
            if modo_key == "claude" and not motor_ia.claude_disponible:
                st.error("⚠️ Claude no configurado. Verificá ANTHROPIC_API_KEY en .env")
            elif modo_key == "gemini" and not motor_ia.gemini_disponible:
                st.warning("⚠️ Gemini no configurado. Agregá GEMINI_API_KEY en .env")

            # Historial de chat
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.get("chat_history", []):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    with st.chat_message(role):
                        st.markdown(content)

            # Input
            prompt = st.chat_input("Preguntale al sistema... (Ej: ¿qué artículos necesito reponer urgente?)")
            if prompt:
                # Mostrar mensaje del usuario
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Agregar al historial
                if "chat_history" not in st.session_state:
                    st.session_state.chat_history = []
                st.session_state.chat_history.append({"role": "user", "content": prompt})

                # Respuesta IA
                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        respuesta = chat_con_ia(
                            st.session_state.chat_history[:-1],
                            prompt,
                            modo=modo_key
                        )
                    st.markdown(respuesta)

                st.session_state.chat_history.append({"role": "assistant", "content": respuesta})
                st.rerun()

        with col_acc:
            st.markdown("**Consultas rápidas**")
            consultas = [
                ("🔴 ¿Qué está en cero?", "Mostrame los artículos con stock en cero ahora mismo"),
                ("🟡 ¿Qué reponer?", "¿Qué artículos necesito reponer con más urgencia?"),
                ("💰 ¿Qué comprar?", "Sugerí un lote de compra para esta semana considerando stock y demanda"),
                ("📊 Resumen del día", "Dame un resumen ejecutivo del estado actual del negocio"),
                ("⚠️ Anomalías", "¿Hay algo raro en los datos de stock que debería investigar?"),
            ]
            for label, pregunta in consultas:
                if st.button(label, width="stretch", key=f"quick_{label[:8]}"):
                    if "chat_history" not in st.session_state:
                        st.session_state.chat_history = []
                    st.session_state.chat_history.append({"role": "user", "content": pregunta})
                    with st.spinner("..."):
                        resp = chat_con_ia(st.session_state.chat_history[:-1], pregunta, modo=modo_key)
                    st.session_state.chat_history.append({"role": "assistant", "content": resp})
                    st.rerun()

            if st.button("🗑️ Limpiar chat", width="stretch"):
                st.session_state.chat_history = []
                st.rerun()

    # ── Tab: Actualizaciones ──────────────────────────────────
    with tabs[1]:
        st.markdown("### ⚡ Actualizaciones por Telegram o desde acá")
        st.markdown("""
        <div style="font-size:13px;color:var(--nx-text2);margin-bottom:20px">
            Podés pedirle al sistema que actualice configuraciones directamente desde Telegram
            enviando mensajes al bot. También podés hacerlo desde acá.
        </div>
        """, unsafe_allow_html=True)

        # Comandos disponibles
        with st.expander("📋 Comandos disponibles en Telegram"):
            comandos = [
                ("/stock [código]", "Ver stock de un artículo en todos los depósitos"),
                ("/precio [código]", "Ver precios Lista 1 y Lista 4 de un artículo"),
                ("/quiebres", "Ver los 10 quiebres más urgentes"),
                ("/transito [modelo]", "Ver si hay pedido en tránsito para un modelo"),
                ("/sinstock", "Lista completa de artículos sin stock"),
                ("/negra [código]", "Agregar artículo a lista negra"),
                ("/config tasa_usd [valor]", "Actualizar tipo de cambio USD/ARS"),
                ("/config tope_lote1 [valor]", "Actualizar tope USD del Lote 1"),
                ("/resumen", "Resumen ejecutivo del estado del sistema"),
            ]
            for cmd, desc in comandos:
                st.markdown(f"""
                <div style="display:flex;gap:12px;padding:5px 0;border-bottom:1px solid var(--nx-border);font-size:12px">
                    <span style="font-family:monospace;color:var(--nx-accent);min-width:220px">{cmd}</span>
                    <span style="color:var(--nx-text2)">{desc}</span>
                </div>
                """, unsafe_allow_html=True)

        # Panel de configuración rápida
        st.markdown("### 🔧 Actualizar configuración")
        col1, col2 = st.columns(2)
        with col1:
            nuevo_tasa = st.number_input("💱 Tipo de cambio USD/ARS", value=1200.0, step=50.0)
            if st.button("Actualizar tasa", width="stretch"):
                _actualizar_config("tasa_usd", nuevo_tasa)
                st.success(f"✅ Tasa actualizada a ${nuevo_tasa:,.0f}")

        with col2:
            nuevo_umbral = st.number_input("📦 Umbral quiebre (unidades)", value=10, step=1)
            if st.button("Actualizar umbral", width="stretch"):
                _actualizar_config("umbral_quiebre", nuevo_umbral)
                st.success(f"✅ Umbral actualizado a {nuevo_umbral} uds")

    # ── Tab: Config ───────────────────────────────────────────
    with tabs[2]:
        st.markdown("### ⚙️ Configuración del motor de IA")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Estado actual:**")
            claude_ok = motor_ia.claude_disponible
            gemini_ok = motor_ia.gemini_disponible
            st.markdown(f"{'🟢' if claude_ok else '🔴'} Claude API — {'Configurado' if claude_ok else 'No configurado'}")
            st.markdown(f"{'🟢' if gemini_ok else '🔴'} Gemini API — {'Configurado' if gemini_ok else 'No configurado'}")

        with col2:
            st.markdown("**Modo activo:**")
            modo_actual = MODO_IA
            st.markdown(f"Motor principal: **{modo_actual.upper()}**")
            if not claude_ok and not gemini_ok:
                st.error("⚠️ Configurá al menos una API en el archivo .env")

        # Test rápido
        st.markdown("---")
        if st.button("🧪 Probar conexión con Claude"):
            with st.spinner("Probando..."):
                resp = motor_ia.consultar("Respondé solo con: 'Roker Nexus operativo ✅'")
            st.success(resp)


def _actualizar_config(clave: str, valor):
    """Guarda configuración en la base de datos."""
    from database import execute_query
    execute_query(
        "INSERT OR REPLACE INTO tasas_cambio (fecha, usd_ars) VALUES (date('now'), ?)",
        (float(valor),),
        fetch=False
    )
