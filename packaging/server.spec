# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH).parent


a = Analysis(
    ['phase1_server/server_entry.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Keep config external; include only example template for first-run setup.
        (str(project_root / 'packaging' / 'nitmexs.example.yaml'), '.'),
    ],
    hiddenimports=['uvicorn.logging'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NITMEXS-Server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
