; Windows installer for video-dl, built with Inno Setup.
;
; Per-user install, no administrator rights. It goes to %LOCALAPPDATA%\Programs so
; the app can update itself in place: tufup rewrites the exe where it sits, and a
; Program Files install would need elevation it does not have.
;
; AppVersion and SourceDir are passed on the command line by the build workflow
; (iscc /DAppVersion=... /DSourceDir=...), so the version has one source, version.py.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "."
#endif

#define AppName "video-dl"
#define AppExe "video-dl.exe"
#define AppPublisher "Kenshin9977"
#define AppUrl "https://github.com/Kenshin9977/video-dl"

[Setup]
; A stable AppId is what lets an installer upgrade a previous install instead of
; stacking a second copy. Never change it.
AppId={{6F3A2C41-8B7D-4E29-9C15-video-dl-0001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#SourceDir}
OutputBaseFilename=video-dl-windows-setup
SetupIconFile={#SourceDir}\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; The bundled exe is already Authenticode-signed and is ~75 MB, so re-verifying it
; on every launch of the installer buys nothing.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\video-dl.exe"; DestDir: "{app}"; Flags: ignoreversion
; root.json is the trust anchor for the auto-updater. In the onefile exe it lives
; inside the archive, but the updater looks for it next to the exe, so it has to be
; installed alongside or the update channel never bootstraps.
Source: "{#SourceDir}\root.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Directly under Programs, not in a one-app subfolder, so the Start Menu shows a
; single "video-dl" entry rather than a video-dl folder holding one shortcut.
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; tufup writes updated binaries and its metadata cache next to the exe as the app
; runs, so an uninstall must clear the whole install dir, not just what was laid down.
Type: filesandordirs; Name: "{app}"
