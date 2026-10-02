$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$pidFile = Join-Path $PSScriptRoot '.mahara-match.pids.json'
if (-not (Test-Path $pidFile -PathType Leaf)) {
    Write-Host 'Aucun fichier de processus trouvé. Les services n’ont peut-être pas été lancés par start.ps1.' -ForegroundColor Yellow
    exit 0
}

$records = @(Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json)
foreach ($record in @($records)) {
    if ($null -eq $record) {
        continue
    }

    $rawProcessId = $record.ProcessId
    if ($rawProcessId -is [System.Array]) {
        $rawProcessId = $rawProcessId[0]
    }

    $parsedProcessId = 0
    if (-not [int]::TryParse([string]$rawProcessId, [ref]$parsedProcessId)) {
        Write-Host "PID ignoré : valeur invalide pour $($record.Role) : $rawProcessId" -ForegroundColor Yellow
        continue
    }

    $processId = $parsedProcessId
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (-not $process) {
        continue
    }

    $expectedStartTicks = [long]$record.StartTimeUtcTicks
    $actualStartTicks = $process.StartTime.ToUniversalTime().Ticks
    if ($actualStartTicks -ne $expectedStartTicks -or $process.ProcessName -notin @('powershell', 'pwsh')) {
        Write-Host "PID $processId ignoré : le processus ne correspond plus à la fenêtre lancée par start.ps1." -ForegroundColor Yellow
        continue
    }

    Write-Host "Arrêt du $($record.Role) (PID $processId)..." -ForegroundColor Cyan
    & taskkill.exe /PID $processId /T /F | Out-Null
}

Remove-Item -LiteralPath $pidFile -Force
Write-Host 'Les services lancés par start.ps1 ont été arrêtés.' -ForegroundColor Green