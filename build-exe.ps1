# PowerShell script to build the production AssetsEquityBCDC executable.
# Run this from project root:
# .\build-exe.ps1

$ErrorActionPreference = 'Stop'
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ROOT

# Use venv python if present
$venvPython = Join-Path $ROOT 'venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = 'python'
}
Write-Host "Using python: $python"

& npm --prefix frontend run build

& $python -m PyInstaller --noconfirm AssetsEquityBCDC.spec

$packageDir = Join-Path $ROOT 'dist\AssetsEquityBCDC'
Copy-Item -LiteralPath (Join-Path $ROOT 'README.md') -Destination $packageDir -Force
Copy-Item -LiteralPath (Join-Path $ROOT 'docs\INSTALLATION_OFFLINE_FR.txt') -Destination $packageDir -Force
Copy-Item -LiteralPath (Join-Path $ROOT 'docs\INSTALLATION_OFFLINE_EN.txt') -Destination $packageDir -Force
New-Item -ItemType Directory -Force -Path (Join-Path $packageDir 'tools') | Out-Null
Copy-Item -LiteralPath (Join-Path $ROOT 'scripts\create-local-https-cert.ps1') -Destination (Join-Path $packageDir 'tools') -Force

$zipPath = Join-Path $ROOT 'dist\AssetsEquityBCDC-package.zip'
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $packageDir '*') -DestinationPath $zipPath -Force

Write-Host "Build finished. Executable in dist\AssetsEquityBCDC\AssetsEquityBCDC.exe"
Write-Host "Offline package: dist\AssetsEquityBCDC-package.zip"
