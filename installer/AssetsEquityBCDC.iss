#define MyAppName "Assets Equity BCDC"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Equity BCDC"
#define MyAppExeName "AssetsEquityBCDC.exe"

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
SetupIconFile=..\Pictures\assets-equity-logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\AssetsEquityBCDC\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\Pictures\*"; DestDir: "{app}\Pictures"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\backend\mysql-init.sql"; DestDir: "{app}\database"; Flags: ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\scripts\BackupMySql.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\Assets Equity BCDC\data"; Permissions: users-modify
Name: "{commonappdata}\Assets Equity BCDC\logs"; Permissions: users-modify

[Icons]
Name: "{autodesktop}\Assets Equity BCDC"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\Pictures\assets-equity-logo.ico"
Name: "{group}\Assets Equity BCDC"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\Pictures\assets-equity-logo.ico"
Name: "{group}\Guide installation FR-EN"; Filename: "{app}\docs\INSTALLATION_GUIDE_FR_EN.txt"
Name: "{group}\Description application FR-EN"; Filename: "{app}\docs\APPLICATION_OVERVIEW_FR_EN.txt"
Name: "{group}\Dossier Assets Equity BCDC"; Filename: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer Assets Equity BCDC"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
