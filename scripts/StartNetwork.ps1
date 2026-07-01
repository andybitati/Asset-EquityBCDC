param(
    [int]$Port = 48620,
    [string]$HostName = "0.0.0.0",
    [string]$EnvFile = "backend\network.env",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Get-LanAddress {
    $addresses = @(Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.PrefixOrigin -ne "WellKnown"
        } |
        Sort-Object InterfaceMetric |
        Select-Object -ExpandProperty IPAddress)

    if ($addresses) {
        return $addresses[0]
    }
    return "ADRESSE_IP_DU_SERVEUR"
}

function Import-EnvFile([string]$Path) {
    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or $line -notmatch "=") {
            return
        }
        $name, $value = $line.Split("=", 2)
        $name = $name.Trim()
        $value = $value.Trim().Trim('"').Trim("'")
        if ($name) {
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

Import-EnvFile $EnvFile

$lanAddress = Get-LanAddress
$networkUrl = $env:ASSET_EQUITY_PUBLIC_URL
if (-not $networkUrl) {
    $networkUrl = "http://$lanAddress`:$Port"
}
$networkUrl = $networkUrl.TrimEnd("/")

$env:ASSET_EQUITY_HOST = $HostName
$env:ASSET_EQUITY_PORT = "$Port"
$env:ASSET_EQUITY_PUBLIC_URL = $networkUrl
if (-not $env:ASSET_EQUITY_OPEN_BROWSER) {
    $env:ASSET_EQUITY_OPEN_BROWSER = "true"
}
if (-not $env:CORS_ORIGINS) {
    $env:CORS_ORIGINS = $networkUrl
}

if (-not $SkipBuild) {
    Push-Location frontend
    try {
        npm run build
    }
    finally {
        Pop-Location
    }
}

if (Test-Path "venv\Scripts\python.exe") {
    $python = "venv\Scripts\python.exe"
}
else {
    $python = "python"
}

Write-Host ""
Write-Host "Assets Equity BCDC - version reseau"
Write-Host "Lien local  : http://127.0.0.1:$Port"
Write-Host "Lien reseau : $networkUrl"
Write-Host ""
Write-Host "Laissez cette fenetre ouverte pendant l'utilisation de l'application."
Write-Host ""

& $python production_server.py
