# ROKER NEXUS - Instalar AutoPush como tarea programada
# Ejecutar UNA SOLA VEZ como Administrador

$scriptPath = "C:\Users\kuaji\Documents\roker_nexus\autopush.ps1"
$taskName = "RokerNexus_AutoPush"

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File $scriptPath"

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force

Start-ScheduledTask -TaskName $taskName

Write-Host ""
Write-Host "AutoPush instalado y corriendo en segundo plano"
Write-Host "Cada 30 segundos revisa cambios y pushea solo"
Write-Host "Se inicia automaticamente con Windows"
Write-Host ""
Write-Host "Para ver el log abri este archivo:"
Write-Host "C:\Users\kuaji\Documents\roker_nexus\autopush.log"
