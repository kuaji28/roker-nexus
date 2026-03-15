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

            # Input — usamos text_input dentro de form para evitar que
            # aparezca en el footer de otras páginas (bug de st.chat_input)
            with st.form(key="chat_form", clear_on_submit=True):
                col_inp, col_btn = st.columns([5, 1])
                with col_inp:
                    prompt = st.text_input(
                        "Mensaje",
                        placeholder="Preguntale al sistema... (Ej: ¿qué artículos necesito reponer?)",
                        label_visibility="collapsed",
                    )
                with col_btn:
                    enviado = st.form_submit_button("Enviar", width='stretch')
            if enviado and prompt:
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

        from database import get_config, set_config

        claude_ok = motor_ia.claude_disponible
        gemini_ok = motor_ia.gemini_disponible

        # Estado
        c1, c2, c3 = st.columns(3)
        with c1:
            color_c = "#32d74b" if claude_ok else "#ff375f"
            st.markdown(f"""<div style="background:rgba(50,215,75,.07) if {claude_ok} else rgba(255,55,95,.07);
                border:1px solid {color_c}40;border-radius:10px;padding:12px 14px">
                <div style="font-size:11px;color:{color_c};font-weight:700">CLAUDE</div>
                <div style="font-size:14px;font-weight:600">{'🟢 Conectado' if claude_ok else '🔴 Sin key'}</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            color_g = "#32d74b" if gemini_ok else "#ff9f0a"
            st.markdown(f"""<div style="border:1px solid {color_g}40;border-radius:10px;padding:12px 14px">
                <div style="font-size:11px;color:{color_g};font-weight:700">GEMINI</div>
                <div style="font-size:14px;font-weight:600">{'🟢 Conectado' if gemini_ok else '🟡 Sin key'}</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div style="border:1px solid rgba(10,132,255,.3);border-radius:10px;padding:12px 14px">
                <div style="font-size:11px;color:#0a84ff;font-weight:700">MODO</div>
                <div style="font-size:14px;font-weight:600">{MODO_IA.upper()}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🔑 Ingresar API Keys")
        st.markdown("""<div style="background:rgba(10,132,255,.07);border:1px solid rgba(10,132,255,.2);
            border-radius:10px;padding:12px 16px;font-size:13px;margin-bottom:16px">
            💡 Podés guardar las keys acá o desde el panel lateral <strong>🧠 Inteligencia IA</strong>.<br>
            Para Streamlit Cloud también podés agregarlas en <strong>Settings → Secrets</strong> como
            <code>ANTHROPIC_API_KEY</code> y <code>GEMINI_API_KEY</code>.
        </div>""", unsafe_allow_html=True)

        # Leer keys actuales (enmascaradas)
        key_claude_actual = get_config("claude_api_key") or ""
        key_gemini_actual = get_config("gemini_api_key") or ""

        col_k1, col_k2 = st.columns(2)
        with col_k1:
            st.markdown("**Claude (Anthropic)**")
            nueva_claude = st.text_input(
                "Claude API Key",
                value=key_claude_actual,
                type="password",
                placeholder="sk-ant-api03-...",
                key="ia_cfg_claude_key",
                label_visibility="collapsed"
            )
            if st.button("💾 Guardar key Claude", key="ia_save_claude", use_container_width=True):
                set_config("claude_api_key", nueva_claude.strip())
                # Invalidar el cliente cacheado para que lo recree
                motor_ia._claude_client = None
                st.success("✅ Key Claude guardada"); st.rerun()

        with col_k2:
            st.markdown("**Gemini (Google)**")
            nueva_gemini = st.text_input(
                "Gemini API Key",
                value=key_gemini_actual,
                type="password",
                placeholder="AIzaSy...",
                key="ia_cfg_gemini_key",
                label_visibility="collapsed"
            )
            if st.button("💾 Guardar key Gemini", key="ia_save_gemini", use_container_width=True):
                set_config("gemini_api_key", nueva_gemini.strip())
                motor_ia._gemini_model = None
                st.success("✅ Key Gemini guardada"); st.rerun()

        # Test rápido
        st.markdown("---")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            if st.button("🧪 Probar Claude", use_container_width=True, type="primary"):
                motor_ia._claude_client = None  # forzar recreación con key actualizada
                with st.spinner("Conectando con Claude..."):
                    resp = motor_ia.consultar("Respondé solo: 'Roker Nexus con Claude ✅'", modo="claude")
                if "Error" in resp or "⚠️" in resp:
                    st.error(resp)
                else:
                    st.success(resp)
        with col_t2:
            if st.button("🧪 Probar Gemini", use_container_width=True):
                motor_ia._gemini_model = None  # forzar recreación
                with st.spinner("Conectando con Gemini..."):
                    resp = motor_ia.consultar("Respondé solo: 'Roker Nexus con Gemini ✅'", modo="gemini")
                if "Error" in resp or "⚠️" in resp:
                    st.error(resp)
                else:
                    st.success(resp)


def _actualizar_config(clave: str, valor):
    """Guarda configuración en la base de datos."""
    from database import execute_query
    execute_query(
        "INSERT OR REPLACE INTO tasas_cambio (fecha, usd_ars) VALUES (date('now'), ?)",
        (float(valor),),
        fetch=False
    )
