# ROKER NEXUS - Auto Push con limpieza de log
# Corre en segundo plano, detecta cambios y pushea solo

$repo = "C:\Users\kuaji\Documents\roker_nexus"
$intervalo = 30
$logFile = "$repo\autopush.log"
$maxLineasLog = 200

function Log($msg) {
    $ts = Get-Date -Format "dd/MM HH:mm:ss"
    $linea = "$ts - $msg"
    Add-Content -Path $logFile -Value $linea
    Write-Host $linea
}

function LimpiarLog() {
    if (Test-Path $logFile) {
        $lineas = Get-Content $logFile
        if ($lineas.Count -gt $maxLineasLog) {
            # Conservar solo las ultimas 200 lineas
            $lineas | Select-Object -Last $maxLineasLog | Set-Content $logFile
            Log "Log limpiado - conservadas ultimas $maxLineasLog lineas"
        }
    }
}

function LimpiarCommitsViejos() {
    # Cada domingo a las 3am, squash de commits automaticos viejos
    $hora = (Get-Date).Hour
    $diaSemana = (Get-Date).DayOfWeek
    if ($diaSemana -eq "Sunday" -and $hora -eq 3) {
        Log "Limpieza semanal de commits iniciada"
        # Mantener solo los ultimos 50 commits
        $count = (git rev-list --count HEAD 2>$null)
        if ($count -gt 50) {
            git gc --prune=now --aggressive 2>$null
            Log "Git optimizado - $count commits compactados"
        }
    }
}

Log "=== AutoPush iniciado ==="
Set-Location $repo

$contador = 0

while ($true) {
    try {
        $status = git status --porcelain 2>$null
        if ($status) {
            Log "Cambios detectados"
            git add -A 2>$null
            $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
            $msg = "auto: $ts"
            git commit -m $msg 2>$null
            git push 2>$null
            if ($LASTEXITCODE -eq 0) {
                Log "Push exitoso"
            } else {
                Log "Error en push - reintentando en 30s"
            }
        }

        # Cada 100 ciclos (~50 minutos) limpia el log
        $contador++
        if ($contador -ge 100) {
            LimpiarLog
            LimpiarCommitsViejos
            $contador = 0
        }
    }
    catch {
        Log "Error: $_"
    }
    Start-Sleep -Seconds $intervalo
}
