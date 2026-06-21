#define MyAppName "Assets Equity BCDC"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Equity BCDC"
#define MyAppExeName "start-all.bat"

[Setup]
AppId={{A99A9F14-33E8-4F87-BB75-000000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Assets Equity BCDC
DefaultGroupName={#MyAppName}
OutputDir=.
OutputBaseFilename=AssetsEquityBCDC-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Files]
Source: "..\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\Pictures\*"; DestDir: "{app}\Pictures"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\package.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\start-all.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build-exe.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\Assets Equity BCDC"; Filename: "{app}\start-all.bat"; WorkingDir: "{app}"; IconFilename: "{app}\frontend\public\favicon.ico"
Name: "{group}\Assets Equity BCDC"; Filename: "{app}\start-all.bat"; WorkingDir: "{app}"; IconFilename: "{app}\frontend\public\favicon.ico"
Name: "{group}\Dossier Assets Equity BCDC"; Filename: "{app}"

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\scripts\InstallDependencies.ps1"""; Flags: postinstall runascurrentuser; Description: "Installer les dépendances Python/Node"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backend\logs"
