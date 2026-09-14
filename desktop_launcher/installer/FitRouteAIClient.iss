#define MyAppName "FitRoute AI Client"
#define MyAppVersion "0.1.0-dev"
#define MyAppPublisher "FitRoute"
#define MyAppExeName "FitRouteLauncher.exe"

[Setup]
AppId={{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\FitRoute
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=FitRoute-AI-Client-Setup
Compression=lzma
SolidCompression=yes
UninstallDisplayName={#MyAppName}

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\config.json"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKCU; Subkey: "Software\Classes\fitroute"; ValueType: string; ValueName: ""; ValueData: "URL:FitRoute Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\fitroute"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\fitroute\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\fitroute\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
