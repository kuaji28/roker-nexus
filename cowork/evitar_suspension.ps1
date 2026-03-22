# ============================================================
# ROKER NEXUS — Evitar que la PC se duerma o apague
# Ejecutar UNA SOLA VEZ como Administrador
# ============================================================

Write-Host "Configurando Windows para nunca suspenderse..."

# Nunca apagar pantalla (enchufado)
powercfg /change monitor-timeout-ac 0
# Nunca suspender (enchufado)
powercfg /change standby-timeout-ac 0
# Nunca hibernar
powercfg /change hibernate-timeout-ac 0
# Nunca apagar disco
powercfg /change disk-timeout-ac 0

# Desactivar hibernación completamente
powercfg /hibernate off

Write-Host ""
Write-Host "✅ PC configurada para nunca suspenderse"
Write-Host "   Podés cerrar la tapa del notebook sin que se duerma"
Write-Host ""
Write-Host "⚠️  Recordá dejarla enchufada para que no se quede sin batería"
