# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['production_server.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend\\dist', 'frontend\\dist'), ('backend\\mysql-init.sql', 'backend'), ('Pictures\\assets-equity-logo.ico', 'Pictures')],
    hiddenimports=['pymysql', 'sqlalchemy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AssetsEquityBCDC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Pictures\\assets-equity-logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AssetsEquityBCDC',
)
