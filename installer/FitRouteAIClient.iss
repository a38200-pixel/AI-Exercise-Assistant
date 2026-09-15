#define MyAppName "FitRoute AI Client"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "FitRoute"
#define MyAppExeName "FitRouteLauncher.exe"

[Setup]
AppId={{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\FitRoute AI Client
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\installer_output
OutputBaseFilename=FitRoute-AI-Client-Setup-{#MyAppVersion}
Compression=lzma2/normal
SolidCompression=yes
DiskSpanning=no
CloseApplications=no
RestartApplications=no
AppMutex=Local\FitRouteAIClientCamera

[InstallDelete]
Type: filesandordirs; Name: "{app}\ai_client"

[Files]
Source: "..\desktop_launcher\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.production.json"; DestDir: "{app}"; DestName: "config.json"; Flags: ignoreversion
Source: "..\dist_candidate_protoc\FitRouteAIClient\*"; DestDir: "{app}\ai_client"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
Root: HKCU; Subkey: "Software\Classes\fitroute"; ValueType: string; ValueName: ""; ValueData: "URL:FitRoute Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\fitroute"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\fitroute\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\fitroute\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--logout"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "FitRouteDesktopCredentialLogout"

[UninstallDelete]
Type: files; Name: "{app}\launcher.log"
Type: dirifempty; Name: "{app}"
