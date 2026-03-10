; NITMEXS Server Installer Template (Inno Setup)
[Setup]
AppName=NITMEXS Server
AppVersion=1.0.0
DefaultDirName={autopf}\NITMEXS\Server
DefaultGroupName=NITMEXS Server
OutputDir=.
OutputBaseFilename=nitmexs-server-installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\NITMEXS-Server.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "packaging\nitmexs.example.yaml"; DestDir: "{app}"; DestName: "nitmexs.yaml"; Flags: onlyifdoesntexist

[Dirs]
Name: "{app}\logs"
Name: "{app}\data"

[Icons]
Name: "{group}\NITMEXS Server"; Filename: "{app}\NITMEXS-Server.exe"

[Run]
Filename: "{app}\NITMEXS-Server.exe"; Description: "Run NITMEXS Server"; Flags: nowait postinstall skipifsilent
