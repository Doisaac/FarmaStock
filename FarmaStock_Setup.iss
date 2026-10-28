; FarmaStock 1.0.0
; Instalador para Windows 64 bits
; Non-commercial use only

#define MyAppName "FarmaStock"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "FarmaStock"
#define MyAppExeName "FarmaStock.exe"
#define MyAppIconName "FarmaStock.ico"

[Setup]
AppId={{C06CCAC0-A73B-4E25-9933-587CA9F874AA}

AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin

; Windows 64 bits
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Icono mostrado en Aplicaciones instaladas / Desinstalador
UninstallDisplayIcon={app}\{#MyAppIconName}

; Carpeta donde se genera el instalador
OutputDir=C:\Users\Ricardo\Desktop\MATERIAS CICLO II - 2026\APR135 -  Asesoría Profesional\Trbajo\Proyecto_funcional\FarmaStock\installer

; Nombre del instalador final
OutputBaseFilename=FarmaStock_Setup_1.0.0

; Icono del propio instalador
SetupIconFile=C:\Users\Ricardo\Desktop\MATERIAS CICLO II - 2026\APR135 -  Asesoría Profesional\Trbajo\Proyecto_funcional\FarmaStock\FarmaStock.ico

; Información del instalador
VersionInfoVersion=1.0.0.0
VersionInfoProductName=FarmaStock
VersionInfoProductVersion=1.0.0
VersionInfoDescription=Instalador de FarmaStock
VersionInfoCompany=FarmaStock

SolidCompression=yes
WizardStyle=modern dynamic

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; \
Description: "{cm:CreateDesktopIcon}"; \
GroupDescription: "{cm:AdditionalIcons}"; \
Flags: unchecked

[Files]

; Ejecutable principal
Source: "C:\Users\Ricardo\Desktop\MATERIAS CICLO II - 2026\APR135 -  Asesoría Profesional\Trbajo\Proyecto_funcional\FarmaStock\dist\FarmaStock\{#MyAppExeName}"; \
DestDir: "{app}"; \
Flags: ignoreversion

; Dependencias generadas por PyInstaller
Source: "C:\Users\Ricardo\Desktop\MATERIAS CICLO II - 2026\APR135 -  Asesoría Profesional\Trbajo\Proyecto_funcional\FarmaStock\dist\FarmaStock\_internal\*"; \
DestDir: "{app}\_internal"; \
Flags: ignoreversion recursesubdirs createallsubdirs

; Logo/icono de FarmaStock para accesos directos y Windows
Source: "C:\Users\Ricardo\Desktop\MATERIAS CICLO II - 2026\APR135 -  Asesoría Profesional\Trbajo\Proyecto_funcional\FarmaStock\FarmaStock.ico"; \
DestDir: "{app}"; \
Flags: ignoreversion

[Icons]

; Acceso directo en menú Inicio
Name: "{autoprograms}\{#MyAppName}"; \
Filename: "{app}\{#MyAppExeName}"; \
IconFilename: "{app}\{#MyAppIconName}"

; Acceso directo opcional en escritorio
Name: "{autodesktop}\{#MyAppName}"; \
Filename: "{app}\{#MyAppExeName}"; \
IconFilename: "{app}\{#MyAppIconName}"; \
Tasks: desktopicon

[Run]

; Permitir abrir FarmaStock al finalizar la instalación
Filename: "{app}\{#MyAppExeName}"; \
Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
Flags: nowait postinstall skipifsilent
