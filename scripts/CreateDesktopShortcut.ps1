$WScriptShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $DesktopPath "Start-Assets-EquityBCDC.lnk"
$TargetPath = "F:\Asset-Equity\start-all.bat"
$WorkingDirectory = "F:\Asset-Equity"
$IconLocation = "F:\Asset-Equity\frontend\public\favicon.ico"
$shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $TargetPath
$shortcut.WorkingDirectory = $WorkingDirectory
$shortcut.WindowStyle = 1
$shortcut.IconLocation = $IconLocation
$shortcut.Save()
Write-Host "Shortcut created at $ShortcutPath" 
