; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Kathara"
#define MyAppVersion "3.7.9"
#define MyAppPublisher "Kathara Team"
#define MyAppURL "https://www.kathara.org"
#define MyAppExeName "kathara.exe"

#include "Assets\environment.iss"

[Setup]
DisableWelcomePage=no
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{58CBACC8-FC29-4D5A-9C4D-3AD345884720}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
OutputBaseFilename=Kathara-windows-installer-{#MyArchitecture}-{#MyAppVersion}
SetupIconFile=Assets\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=True
ArchitecturesInstallIn64BitMode={#MyArchitecture}
UninstallDisplayIcon={app}\Kathara.exe

[Messages]
WelcomeLabel2=Kathara is a lightweight container-based network emulation tool.%n%nThis will install [name/ver] on your computer.%n%nYou will be guided through the steps necessary to install this software.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\src\kathara.dist\kathara.exe"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Tasks]
Name: envPath; Description: "Add to PATH variable (Recommended)" 

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
    if (CurStep = ssPostInstall) and WizardIsTaskSelected('envPath')
    then EnvAddPath(ExpandConstant('{app}'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
    if CurUninstallStep = usPostUninstall
    then EnvRemovePath(ExpandConstant('{app}'));
end;
 