param(
  [string]$OutputDirectory = "F:\Asset-Equity\backups",
  [string]$Database = "asset_equity",
  [string]$User = "asset_equity_user",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 3306
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $OutputDirectory)) {
  New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $OutputDirectory "$Database-$timestamp.sql"

Write-Host "MySQL backup target: $backupPath"
Write-Host "Enter MySQL password for user '$User' when prompted."

& mysqldump `
  --host=$HostName `
  --port=$Port `
  --user=$User `
  --password `
  --single-transaction `
  --routines `
  --triggers `
  $Database `
  --result-file=$backupPath

Write-Host "Backup created: $backupPath"
Write-Host "Store this file in a secured, encrypted backup location."
