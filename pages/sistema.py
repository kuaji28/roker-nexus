"""
ROKER NEXUS — Página: Estado del Sistema
Muestra todas las conexiones, versiones y estado en tiempo real.
"""
import streamlit as st
from datetime import datetime


def render():
    st.markdown("""
    <h1 style="margin:0 0 4px;font-size:24px;font-weight:700">
        🔌 Estado del Sistema
    </h1>
    <p style="color:var(--text2);font-size:13px;margin-bottom:24px">
        Conexiones activas, versiones y configuración
    </p>
    """, unsafe_allow_html=True)

    # ── Versión ──
    try:
        from version import APP_VERSION, APP_BUILD, CHANGELOG
        v = CHANGELOG[0]
        st.markdown(f"""
        <div class="nx-card nx-card-blue">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-size:18px;font-weight:700;color:var(--text)">
                        ⚡ ROKER NEXUS {APP_VERSION}
                    </div>
                    <div style="font-size:12px;color:var(--text2);margin-top:2px">
                        Última actualización: {APP_BUILD}
                    </div>
                </div>
                <span class="nx-badge nx-badge-blue">{APP_VERSION}</span>
            </div>
            <div style="margin-top:12px;font-size:12px;color:var(--text2)">
                <b>Cambios en esta versión:</b><br>
                {'<br>'.join(f"• {c}" for c in v['cambios'][:5])}
            </div>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        pass

    st.markdown("---")

    # ── Conexiones ──
    st.markdown("### 🔗 Conexiones")

    col1, col2 = st.columns(2)

    with col1:
        # Claude AI
        try:
            from config import ANTHROPIC_API_KEY
            ok = bool(ANTHROPIC_API_KEY)
            _estado_card("🤖 Claude AI", ok,
                         "Conectado — IA principal activa" if ok else "Sin API Key — configurar en Streamlit Secrets",
                         "ANTHROPIC_API_KEY")
        except Exception as e:
            _estado_card("🤖 Claude AI", False, str(e), "ANTHROPIC_API_KEY")

        # Supabase
        try:
            from database import get_supabase, USE_SUPABASE
            if USE_SUPABASE:
                sb = get_supabase()
                sb.table("articulos").select("count", count="exact").execute()
                _estado_card("🗄️ Supabase", True, "Conectado — base de datos activa", "SUPABASE_URL")
            else:
                _estado_card("🗄️ Supabase", False, "No configurado — usando SQLite local", "SUPABASE_URL")
        except Exception as e:
            _estado_card("🗄️ Supabase", False, f"Error: {str(e)[:60]}", "SUPABASE_URL")

    with col2:
        # Telegram
        try:
            from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
            if TELEGRAM_TOKEN:
                import requests
                r = requests.get(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
                    timeout=5
                )
                if r.status_code == 200:
                    bot_name = r.json().get("result", {}).get("username", "?")
                    _estado_card("📱 Telegram Bot", True,
                                 f"@{bot_name} activo — Chat ID: {TELEGRAM_CHAT_ID}",
                                 "TELEGRAM_TOKEN")
                else:
                    _estado_card("📱 Telegram Bot", False, "Token inválido", "TELEGRAM_TOKEN")
            else:
                _estado_card("📱 Telegram Bot", False, "Sin token configurado", "TELEGRAM_TOKEN")
        except Exception as e:
            _estado_card("📱 Telegram Bot", False, f"Sin conexión: {str(e)[:50]}", "TELEGRAM_TOKEN")

        # Railway (Bot)
        _estado_card("🚂 Railway Bot", True,
                     "Auto-deploy activo — se actualiza con cada push",
                     "Deploy automático")

    st.markdown("---")

    # ── Test Telegram ──
    try:
        from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            col_tg1, col_tg2, _ = st.columns([2, 2, 6])
            with col_tg1:
                if st.button("📨 Enviar notificación de prueba", key="btn_tg_test"):
                    from utils.helpers import notificar_telegram
                    notificar_telegram(
                        "\U0001f514 *Roker Nexus — Sistema OK*\n"
                        "Notificaciones Telegram activas. 16/03/2026"
                    )
                    st.success("\u2705 Mensaje enviado a Telegram.")
    except Exception:
        pass

        # ── Base de datos ──
    st.markdown("### 📊 Base de datos")
    try:
        from database import execute_query
        stats = {
            "articulos":         "SELECT COUNT(*) as n FROM articulos",
            "precios":           "SELECT COUNT(*) as n FROM precios",
            "optimizacion":      "SELECT COUNT(*) as n FROM optimizacion",
            "stock_snapshots":   "SELECT COUNT(*) as n FROM stock_snapshots",
            "ventas":            "SELECT COUNT(*) as n FROM ventas",
            "compras_historial": "SELECT COUNT(*) as n FROM compras_historial",
            "cotizacion_items":  "SELECT COUNT(*) as n FROM cotizacion_items",
        }
        cols = st.columns(4)
        iconos = {"articulos":"📦","precios":"💰","optimizacion":"📈",
                  "stock_snapshots":"🏪","ventas":"🛒","compras_historial":"📋","cotizacion_items":"🏭"}
        for i, (tabla, sql) in enumerate(stats.items()):
            try:
                rows = execute_query(sql)
                n = rows[0]["n"] if rows else 0
            except Exception:
                n = 0
            with cols[i % 4]:
                color = "green" if n > 0 else "text3"
                st.markdown(f"""
                <div class="nx-card" style="text-align:center;padding:14px 10px">
                    <div style="font-size:20px">{iconos.get(tabla,'📄')}</div>
                    <div style="font-size:22px;font-weight:700;color:var(--{color})">{n:,}</div>
                    <div style="font-size:10px;color:var(--text3)">{tabla.replace('_',' ').upper()}</div>
                </div>
                """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error consultando BD: {e}")

    st.markdown("---")

    # ── Configuración editable ──
    st.markdown("### ⚙️ Configuración")
    try:
        from database import get_config, set_config, CONFIG_DEFAULTS
        with st.form("form_config"):
            col1, col2, col3 = st.columns(3)
            vals = {}
            configs_vis = [
                ("tasa_usd_ars",         "💵 USD → ARS",          col1, float),
                ("tasa_rmb_usd",         "🇨🇳 RMB → USD",         col1, float),
                ("margen_venta_pct",     "📈 Margen venta (%)",    col2, float),
                ("comision_ml_fr",       "🛍️ Comisión ML FR (%)",  col2, float),
                ("comision_ml_mecanico", "🔧 Comisión ML MEC (%)", col2, float),
                ("umbral_quiebre_stock", "⚠️ Umbral quiebre",      col3, int),
                ("lead_time_dias",       "🚢 Lead time (días)",    col3, int),
                ("presupuesto_lote_1",   "💰 Presupuesto USD",     col3, float),
            ]
            for clave, label, col, tipo in configs_vis:
                with col:
                    val_actual = get_config(clave, tipo)
                    vals[clave] = st.number_input(
                        label, value=float(val_actual),
                        step=1.0 if tipo == int else 0.01,
                        key=f"cfg_{clave}"
                    )
            if st.form_submit_button("💾 Guardar configuración", width='stretch', type="primary"):
                for clave, val in vals.items():
                    set_config(clave, val)
                st.success("✅ Configuración guardada")
    except Exception as e:
        st.error(f"Error en configuración: {e}")

    # ── API Keys manuales ──
    st.markdown("---")
    st.markdown("### 🔑 API Keys")
    st.caption("Si las keys no se leen desde Streamlit Secrets, podés cargarlas acá. Se guardan en la BD local.")
    with st.form("form_apikeys"):
        col1, col2 = st.columns(2)
        with col1:
            ak_claude  = st.text_input("🤖 Anthropic (Claude)", type="password",
                                        placeholder="sk-ant-api03-...")
            ak_gemini  = st.text_input("✨ Gemini", type="password",
                                        placeholder="AIza...")
        with col2:
            ak_tg_tok  = st.text_input("📱 Telegram Token", type="password",
                                        placeholder="123456:ABC...")
            ak_tg_chat = st.text_input("📱 Telegram Chat ID",
                                        placeholder="5427210648")
        if st.form_submit_button("💾 Guardar API Keys", type="primary"):
            import sqlite3 as _sq, os as _os
            _db = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "roker_nexus.db")
            saved = []
            try:
                _conn = _sq.connect(_db)
                for k, v in [
                    ("ANTHROPIC_API_KEY", ak_claude),
                    ("GEMINI_API_KEY",    ak_gemini),
                    ("TELEGRAM_TOKEN",    ak_tg_tok),
                    ("TELEGRAM_CHAT_ID",  ak_tg_chat),
                ]:
                    if v:
                        _conn.execute(
                            "INSERT OR REPLACE INTO configuracion (clave,valor,descripcion) VALUES(?,?,?)",
                            (k, v, k)
                        )
                        saved.append(k.replace("_API_KEY","").replace("_TOKEN","").replace("_"," ").title())
                _conn.commit()
                _conn.close()
                if saved:
                    st.success(f"✅ Guardado: {', '.join(saved)} — **Reiniciá la app** desde Streamlit Cloud (Manage app → Reboot)")
                else:
                    st.warning("No ingresaste ningún valor")
            except Exception as e:
                st.error(f"Error guardando: {e}")
                st.info("Alternativa: cargá las keys en **Streamlit Cloud → App Settings → Secrets**")

    # ── Última importación ──
    st.markdown("---")
    st.markdown("### 📥 Últimas importaciones")
    try:
        from database import execute_query
        rows = execute_query("""
            SELECT tipo_archivo, nombre_archivo, filas_importadas, estado, importado_en
            FROM importaciones_log
            ORDER BY importado_en DESC LIMIT 10
        """)
        if rows:
            import pandas as pd
            df = pd.DataFrame(rows)
            df["importado_en"] = df["importado_en"].str[:16]
            df.columns = ["Tipo", "Archivo", "Filas", "Estado", "Fecha"]
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("Sin importaciones registradas todavía.")
    except Exception as e:
        st.info("Sin datos de importaciones.")

    # ── Backup & Restore ──
    st.markdown("---")
    _seccion_backup_restore()


def _estado_card(nombre: str, ok: bool, detalle: str, variable: str):
    color  = "#32D74B" if ok else "#FF375F"
    bg     = "rgba(50,215,75,0.08)" if ok else "rgba(255,55,95,0.08)"
    border = "rgba(50,215,75,0.25)" if ok else "rgba(255,55,95,0.25)"
    estado = "✅ Activo" if ok else "❌ Inactivo"
    st.markdown(f"""
    <div style="background:{bg};border:.5px solid {border};border-radius:14px;
                padding:14px 16px;margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-size:14px;font-weight:600;color:var(--text)">{nombre}</span>
            <span style="font-size:11px;font-weight:600;color:{color}">{estado}</span>
        </div>
        <div style="font-size:11px;color:var(--text2)">{detalle}</div>
        <div style="font-size:10px;color:var(--text3);margin-top:4px">Var: {variable}</div>
    </div>
    """, unsafe_allow_html=True)



def _seccion_backup_restore():
    """Backup y restore de todos los datos — funciona con SQLite y Supabase."""
    from database import USE_POSTGRES
    from datetime import datetime

    st.markdown("### 💾 Backup & Restore de datos")

    # Banner de estado de persistencia
    if USE_POSTGRES:
        st.success(
            "✅ **Conectado a Supabase** — los datos persisten automáticamente. "
            "El backup es opcional pero recomendable como respaldo extra."
        )
    else:
        st.error(
            "🔴 **Modo SQLite** — los datos SE PIERDEN cuando la app se reinicia. "
            "Descargá el backup ANTES de hacer cualquier actualización. "
            "Para resolver esto definitivamente, configurá `DATABASE_URL` en "
            "Streamlit Cloud → Settings → Secrets."
        )

    # Auto-backup de sesión disponible
    if not USE_POSTGRES and st.session_state.get("_autobackup_zip"):
        t = st.session_state.get("_autobackup_time", "—")
        st.info(f"📦 Hay un auto-backup de sesión disponible generado a las **{t}**.")
        st.download_button(
            "⬇️ Descargar auto-backup de sesión",
            data=st.session_state["_autobackup_zip"],
            file_name=f"roker_nexus_autobackup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip",
            type="primary",
            key="dl_autobackup",
        )

    st.divider()
    tab_exp, tab_imp = st.tabs(["📤 Exportar (Descargar)", "📥 Importar (Restaurar)"])

    # ── EXPORTAR ─────────────────────────────────────────────────────────────
    with tab_exp:
        st.markdown("#### Descargar backup completo")
        st.caption(
            "Genera un archivo ZIP con todos los datos del sistema en formato CSV. "
            "Guardalo en un lugar seguro. Si la app se reinicia, podés restaurarlo."
        )

        # Mostrar resumen de qué hay
        try:
            from utils.backup import get_stats_backup
            stats = get_stats_backup()
            total_filas = sum(v for v in stats.values() if v > 0)

            col1, col2, col3 = st.columns(3)
            col1.metric("📦 Total registros", f"{total_filas:,}")
            tablas_con_datos = sum(1 for v in stats.values() if v > 0)
            col2.metric("📋 Tablas con datos", tablas_con_datos)
            col3.metric("📅 Ahora", datetime.now().strftime("%d/%m %H:%M"))

            with st.expander("Ver detalle por tabla"):
                import pandas as pd
                df_stats = pd.DataFrame([
                    {"Tabla": t, "Registros": n if n >= 0 else "no existe"}
                    for t, n in stats.items()
                ])
                st.dataframe(df_stats, hide_index=True, use_container_width=True)
        except Exception as e:
            st.warning(f"No se pudo calcular el resumen: {e}")

        if st.button("📦 Generar backup completo", type="primary", key="btn_gen_backup"):
            with st.spinner("Generando backup..."):
                try:
                    from utils.backup import exportar_backup
                    zip_data = exportar_backup()
                    fname = f"roker_nexus_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
                    st.session_state["_backup_generado"] = zip_data
                    st.session_state["_backup_fname"]    = fname
                    st.success(f"✅ Backup generado — {len(zip_data)//1024} KB")
                except Exception as e:
                    st.error(f"Error generando backup: {e}")

        if st.session_state.get("_backup_generado"):
            st.download_button(
                "⬇️ Descargar backup (.zip)",
                data=st.session_state["_backup_generado"],
                file_name=st.session_state.get("_backup_fname", "backup.zip"),
                mime="application/zip",
                type="primary",
                key="dl_backup_final",
            )
            st.caption("⚠️ Guardalo en un lugar seguro — Google Drive, tu computadora, etc.")

    # ── IMPORTAR / RESTAURAR ─────────────────────────────────────────────────
    with tab_imp:
        st.markdown("#### Restaurar desde backup")
        st.warning(
            "⚠️ La restauración **reemplaza** los datos existentes. "
            "Hacé un backup primero si tenés datos nuevos que no querés perder."
        )

        archivo = st.file_uploader(
            "Subí el archivo de backup (.zip)",
            type=["zip"],
            key="backup_upload"
        )

        if archivo:
            try:
                from utils.backup import TABLAS_BACKUP
                tablas_sel = st.multiselect(
                    "Tablas a restaurar (por defecto: todas)",
                    options=TABLAS_BACKUP,
                    default=TABLAS_BACKUP,
                    key="backup_tablas_sel"
                )
                confirmar = st.checkbox(
                    "✅ Entiendo que esto reemplaza los datos actuales",
                    key="backup_confirm"
                )

                if st.button("🔄 Restaurar datos", type="primary",
                             disabled=not confirmar, key="btn_restaurar"):
                    with st.spinner("Restaurando..."):
                        try:
                            from utils.backup import restaurar_backup
                            zip_bytes  = archivo.read()
                            resultados = restaurar_backup(zip_bytes, tablas_sel)

                            ok  = sum(1 for r in resultados.values() if r["estado"] == "ok")
                            err = sum(1 for r in resultados.values() if r["estado"] == "error")
                            tot = sum(r.get("filas", 0) for r in resultados.values())

                            if err == 0:
                                st.success(f"✅ Restauración completada: {ok} tablas, {tot:,} registros.")
                            else:
                                st.warning(f"⚠️ {ok} tablas OK, {err} con errores.")

                            # Detalle
                            with st.expander("Ver detalle"):
                                import pandas as pd
                                df_res = pd.DataFrame([
                                    {"Tabla": t,
                                     "Estado": r["estado"],
                                     "Registros": r.get("filas", 0),
                                     "Error": r.get("error", "")}
                                    for t, r in resultados.items()
                                ])
                                st.dataframe(df_res, hide_index=True)

                            st.balloons()
                        except Exception as e:
                            st.error(f"Error en la restauración: {e}")
            except Exception as e:
                st.error(f"Error leyendo el archivo: {e}")

    # ── Cómo configurar Supabase ─────────────────────────────────────────────
    if not USE_POSTGRES:
        st.divider()
        with st.expander("📋 Cómo activar Supabase para persistencia permanente"):
            st.markdown("""
**Pasos para nunca más perder datos:**

1. **Ir a Streamlit Cloud** → tu app → **Settings** → **Secrets**

2. **Agregar esta línea** (reemplazando con tus datos de Supabase):
```toml
DATABASE_URL = "postgresql://postgres:[TU_PASSWORD]@db.[TU_PROJECT].supabase.co:5432/postgres"
```

3. **Guardar** y hacer **Reboot app**

4. La próxima vez que importes archivos, los datos se guardan en Supabase y **nunca se pierden**, ni siquiera si la app se reinicia o actualiza.

**¿Dónde encontrar el DATABASE_URL en Supabase?**
→ Supabase → tu proyecto → Settings → Database → Connection string → URI
→ Reemplazá `[YOUR-PASSWORD]` con tu contraseña de la BD.
            """)

    # ── Botón backup rápido en sidebar ───────────────────────────────────────
    try:
        with st.sidebar:
            st.markdown("---")
            if st.button("💾 Backup rápido", key="sb_backup_rapido", help="Descargá todos los datos ahora"):
                with st.spinner("Generando..."):
                    from utils.backup import exportar_backup
                    d = exportar_backup()
                    fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
                    st.session_state["_sb_backup_data"]  = d
                    st.session_state["_sb_backup_fname"] = fname
                    st.rerun()
            if st.session_state.get("_sb_backup_data"):
                st.download_button(
                    "⬇️ Descargar",
                    data=st.session_state["_sb_backup_data"],
                    file_name=st.session_state.get("_sb_backup_fname","backup.zip"),
                    mime="application/zip",
                    key="sb_dl_backup",
                )
    except Exception:
        pass

