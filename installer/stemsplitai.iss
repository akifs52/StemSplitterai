; ============================================================
; StemSplitAI — Inno Setup Installer Script
; ============================================================
; Compile with: iscc installer\stemsplitai.iss
; Requires Inno Setup 6.x  —  https://jrsoftware.org/isinfo.php
; ============================================================

#define MyAppName      "StemSplitAI"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Akifs52"
#define MyAppURL       "https://github.com/akifs52/StemSplitterai"
#define MyAppExeName   "StemSplitAI.exe"

[Setup]
; Unique application GUID — do NOT change after first release
AppId={{8F3C2A1E-5D4B-4E7A-9C6F-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Output settings
OutputDir=..\dist
OutputBaseFilename=StemSplitAI-Setup-{#MyAppVersion}
; Visual settings
SetupIconFile=..\assets\icons\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Privileges — install per-user by default, allow elevation
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Misc
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=
; Close running instances before install
CloseApplications=force
CloseApplicationsFilter=*.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Bundle the entire PyInstaller output folder
Source: "..\dist\StemSplitAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
