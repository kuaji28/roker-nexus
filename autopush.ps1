# ROKER NEXUS - Auto Push
# Corre en segundo plano, detecta cambios y pushea solo

$repo = "C:\Users\kuaji\Documents\roker_nexus"
$intervalo = 30
$logFile = "$repo\autopush.log"

function Log($msg) {
    $ts = Get-Date -Format "dd/MM HH:mm:ss"
    $linea = "$ts - $msg"
    Add-Content -Path $logFile -Value $linea
    Write-Host $linea
}

Log "=== AutoPush iniciado ==="
Set-Location $repo

while ($true) {
    try {
        $status = git status --porcelain 2>$null
        if ($status) {
            Log "Cambios detectados"
            git add -A 2>$null
            $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
            $msg = "auto: actualizacion $ts"
            git commit -m $msg 2>$null
            git push 2>$null
            if ($LASTEXITCODE -eq 0) {
                Log "Push exitoso"
            } else {
                Log "Error en push"
            }
        }
    }
    catch {
        Log "Error: $_"
    }
    Start-Sleep -Seconds $intervalo
}
