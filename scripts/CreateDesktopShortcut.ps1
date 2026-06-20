$WScriptShell = New-Object -ComObject WScript.Shell
$ShortcutPath = "$env:USERPROFILE\Desktop\Start-Assets-EquityBCDC.lnk"
$TargetPath = "F:\Asset-Equity\Start-Assets-EquityBCDC.bat"
$WorkingDirectory = "F:\Asset-Equity"
$IconLocation = "F:\Asset-Equity\frontend\public\favicon.ico"
$shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $TargetPath
$shortcut.WorkingDirectory = $WorkingDirectory
$shortcut.WindowStyle = 1
$shortcut.IconLocation = $IconLocation
$shortcut.Save()
Write-Host "Shortcut created at $ShortcutPath" 
