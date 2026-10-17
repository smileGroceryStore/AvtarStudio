#ifndef ReleaseDir
  #define ReleaseDir "..\release-passthrough\AvatarStudio"
#endif
#define AppVersion "0.8.0"

[Setup]
AppId={{9B22BE89-79D1-456B-B39C-9B3DB34E776D}
AppName=映身 · Avatar Studio
AppVersion={#AppVersion}
AppPublisher=Avatar Studio
DefaultDirName={localappdata}\Programs\AvatarStudio
DefaultGroupName=映身 · Avatar Studio
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\installers
OutputBaseFilename=AvatarStudio-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\desktop-assets\app.ico
UninstallDisplayIcon={app}\AvatarStudio.exe
UninstallDisplayName=映身 · Avatar Studio
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
InfoBeforeFile=README.txt

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："
Name: "widgeticon"; Description: "创建桌面挂件快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Files]
Source: "{#ReleaseDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\映身"; Filename: "{app}\AvatarStudio.exe"; WorkingDir: "{app}"
Name: "{group}\映身 · 桌面挂件"; Filename: "{app}\AvatarStudio.exe"; Parameters: "--widget"; WorkingDir: "{app}"
Name: "{group}\卸载映身"; Filename: "{uninstallexe}"
Name: "{autodesktop}\映身"; Filename: "{app}\AvatarStudio.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\映身桌面挂件"; Filename: "{app}\AvatarStudio.exe"; Parameters: "--widget"; WorkingDir: "{app}"; Tasks: widgeticon

[Run]
Filename: "{app}\AvatarStudio.exe"; Description: "启动映身"; Flags: nowait postinstall skipifsilent

; User avatars/settings live separately in LOCALAPPDATA\AvatarStudio.
; Uninstall deliberately removes only installer-owned application files.
