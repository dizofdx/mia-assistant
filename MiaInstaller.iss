; Script generated for Inno Setup 6
; Мия AI Ассистент — Инсталлятор для Windows
#define MyAppName "Мия AI Ассистент"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "MIA Team"
#define MyAppURL "http://localhost:8000"
#define MyAppExeName "Mia.exe"

[Setup]
AppId={{5796EBE1-9A38-4F29-8736-EA45E999D5C4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\MiaAssistant
DisableProgramGroupPage=yes
OutputDir=D:\assistant\dist
OutputBaseFilename=MiaInstaller
SetupIconFile=D:\assistant\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\app.ico

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Запускать Мию автоматически при входе в Windows"; GroupDescription: "Автозагрузка:"; Flags: unchecked

[Files]
Source: "D:\assistant\Mia.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\assistant\app.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\assistant\*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\assistant\web_ui.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\assistant\run_mia_silent.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\assistant\static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "D:\assistant\sounds\*"; DestDir: "{app}\sounds"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "D:\assistant\scenarios\*"; DestDir: "{app}\scenarios"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "D:\assistant\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
