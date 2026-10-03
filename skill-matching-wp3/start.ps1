$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$venvPath = Join-Path $PSScriptRoot 'venv'
$pythonPath = Join-Path $venvPath 'Scripts\python.exe'
$activatePath = Join-Path $venvPath 'Scripts\Activate.ps1'
$requirementsPath = Join-Path $PSScriptRoot 'requirements.txt'
$frontendPath = Join-Path $PSScriptRoot 'frontend'
$pidFile = Join-Path $PSScriptRoot '.mahara-match.pids.json'

if (Test-Path $pidFile) {
    Write-Host 'Un fichier de processus existe déjà. Lancez d’abord .\stop.ps1, puis réessayez.' -ForegroundColor Yellow
    exit 1
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not (Test-Path $pythonPath -PathType Leaf)) {
    if (-not $pythonCommand) {
        Write-Host 'Python est introuvable. Installez Python puis relancez ce script.' -ForegroundColor Red
        exit 1
    }

    Write-Host 'Création de l’environnement virtuel...' -ForegroundColor Cyan
    & $pythonCommand.Source -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'La création de l’environnement virtuel a échoué.' -ForegroundColor Red
        exit $LASTEXITCODE
    }

    Write-Host 'Installation des dépendances Python...' -ForegroundColor Cyan
    & $pythonPath -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'L’installation des dépendances Python a échoué.' -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path $activatePath -PathType Leaf)) {
    Write-Host "Script d’activation introuvable : $activatePath" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host 'Node.js et npm sont requis. Installez Node.js, puis relancez ce script.' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $frontendPath 'package.json') -PathType Leaf)) {
    Write-Host "Le fichier frontend\package.json est introuvable : $frontendPath" -ForegroundColor Red
    exit 1
}

function ConvertTo-PowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function ConvertTo-EncodedCommand {
    param([string]$Command)
    return [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
}

function Save-ProcessRecords {
    param([object[]]$Records)
    $Records | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
}

$shellExecutable = if ($PSVersionTable.PSEdition -eq 'Core') { 'pwsh.exe' } else { 'powershell.exe' }
$rootLiteral = ConvertTo-PowerShellLiteral $PSScriptRoot
$activateLiteral = ConvertTo-PowerShellLiteral $activatePath
$frontendLiteral = ConvertTo-PowerShellLiteral $frontendPath

Write-Host 'Démarrage du backend...' -ForegroundColor Cyan
$backendCommand = @"
. $activateLiteral
Set-Location $rootLiteral
python main.py
"@
$backendWindow = Start-Process -FilePath $shellExecutable -ArgumentList @(
    '-NoExit', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', (ConvertTo-EncodedCommand $backendCommand)
) -PassThru

$processRecords = @(
    [pscustomobject]@{
        Role = 'backend'
        ProcessId = $backendWindow.Id
        StartTimeUtcTicks = $backendWindow.StartTime.ToUniversalTime().Ticks
    }
)
Save-ProcessRecords $processRecords

Write-Host 'Démarrage du frontend...' -ForegroundColor Cyan
$frontendCommand = @"
Set-Location $frontendLiteral
if (-not (Test-Path 'node_modules' -PathType Container)) {
    Write-Host 'Installation des dépendances du frontend...'
    npm install
    if (`$LASTEXITCODE -ne 0) {
        Write-Host 'L’installation npm a échoué.' -ForegroundColor Red
        Read-Host 'Appuyez sur Entrée pour fermer cette fenêtre'
        exit `$LASTEXITCODE
    }
}
npm run dev
"@
$frontendWindow = Start-Process -FilePath $shellExecutable -ArgumentList @(
    '-NoExit', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', (ConvertTo-EncodedCommand $frontendCommand)
) -PassThru

$processRecords += [pscustomobject]@{
    Role = 'frontend'
    ProcessId = $frontendWindow.Id
    StartTimeUtcTicks = $frontendWindow.StartTime.ToUniversalTime().Ticks
}
Save-ProcessRecords $processRecords

Write-Host 'Attente du backend sur http://localhost:8000 ...' -ForegroundColor Cyan
$backendReady = $false
$deadline = [DateTime]::UtcNow.AddSeconds(30)
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $null = Invoke-RestMethod -Uri 'http://localhost:8000/' -TimeoutSec 1
        $backendReady = $true
        break
    }
    catch {
        if ([DateTime]::UtcNow -lt $deadline) {
            Start-Sleep -Seconds 1
        }
    }
}

if ($backendReady) {
    Write-Host 'Backend prêt : http://localhost:8000' -ForegroundColor Green
}
else {
    Write-Host 'Avertissement : le backend ne répond pas après 30 secondes. Le frontend va quand même être ouvert.' -ForegroundColor Yellow
}

Write-Host 'Frontend : http://localhost:5173' -ForegroundColor Green
Write-Host 'Documentation API : http://localhost:8000/docs' -ForegroundColor Green
Write-Host 'Pour arrêter les services lancés, exécutez .\stop.ps1.' -ForegroundColor Gray
Start-Process 'http://localhost:5173'