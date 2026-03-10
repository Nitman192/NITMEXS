# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None

repo_root = Path(SPECPATH).parent


a = Analysis(
    [str(repo_root / 'phase1_server' / 'server_entry.py')],
    pathex=[str(repo_root)],
    binaries=[],
    datas=[
        # Keep config external; include only example template for first-run setup.
        (str(repo_root / 'packaging' / 'nitmexs.example.yaml'), '.'),
        (str(repo_root / 'phase1_server' / 'web' / 'index.html'), 'phase1_server/web'),
        (str(repo_root / 'phase1_server' / 'web' / 'app.js'), 'phase1_server/web'),
    ],
    hiddenimports=['uvicorn.logging', 'phase1_server.app'],
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
