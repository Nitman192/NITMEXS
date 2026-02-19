; NITMEXS Client Installer Template (Inno Setup)
[Setup]
AppName=NITMEXS Client
AppVersion=1.0.0
DefaultDirName={autopf}\NITMEXS\Client
DefaultGroupName=NITMEXS Client
OutputDir=.
OutputBaseFilename=nitmexs-client-installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\NITMEXS-Client.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\logs"

[Icons]
Name: "{group}\NITMEXS Client"; Filename: "{app}\NITMEXS-Client.exe"

[Run]
Filename: "{app}\NITMEXS-Client.exe"; Description: "Run NITMEXS Client"; Flags: nowait postinstall skipifsilent
