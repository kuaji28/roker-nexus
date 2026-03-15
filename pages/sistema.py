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



def _seccion_backups():
    """Gestión de backups automáticos de la base de datos."""
    st.markdown("### 💾 Backups & Restauración")

    import os, shutil, glob
    from datetime import datetime
    from database import SQLITE_PATH

    backup_dir = os.path.join(os.path.dirname(SQLITE_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)

    col_b1, col_b2, col_b3 = st.columns(3)

    with col_b1:
        if st.button("💾 Crear Backup ahora", width='stretch', type="primary"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(backup_dir, f"roker_nexus_backup_{ts}.db")
            shutil.copy2(SQLITE_PATH, dest)
            # Mantener solo las 3 más recientes
            backups = sorted(glob.glob(os.path.join(backup_dir, "*.db")))
            while len(backups) > 3:
                os.remove(backups.pop(0))
            st.success(f"✅ Backup creado: {os.path.basename(dest)}")
            st.rerun()

    # Listar backups disponibles
    backups = sorted(glob.glob(os.path.join(backup_dir, "*.db")), reverse=True)
    if backups:
        st.markdown(f"**{len(backups)} backup(s) disponibles:**")
        for i, bp in enumerate(backups):
            nombre = os.path.basename(bp)
            size_kb = os.path.getsize(bp) // 1024
            ts_str = nombre.replace("roker_nexus_backup_","").replace(".db","")
            try:
                dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                fecha_label = dt.strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                fecha_label = ts_str

            col_info, col_rest, col_dl = st.columns([4, 2, 2])
            col_info.markdown(f"📦 `{nombre}` · {size_kb} KB · {fecha_label}")
            with col_rest:
                if st.button(f"🔄 Restaurar", key=f"rest_{i}", width='stretch'):
                    # Hacer backup del actual antes de restaurar
                    ts2 = datetime.now().strftime("%Y%m%d_%H%M%S")
                    shutil.copy2(SQLITE_PATH, os.path.join(backup_dir, f"pre_restore_{ts2}.db"))
                    shutil.copy2(bp, SQLITE_PATH)
                    st.success(f"✅ Restaurado desde {fecha_label}. Reiniciá la app.")
                    st.balloons()
            with col_dl:
                with open(bp, "rb") as f:
                    st.download_button(
                        "⬇️ Descargar", data=f.read(),
                        file_name=nombre, mime="application/octet-stream",
                        key=f"dl_{i}", width='stretch'
                    )
    else:
        st.info("No hay backups todavía. Creá el primero con el botón de arriba.")

    st.markdown("---")
    st.caption("💡 Los backups se crean automáticamente en acciones importantes. "
               "Se conservan las 3 más recientes.")

