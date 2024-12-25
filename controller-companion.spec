# -*- mode: python ; coding: utf-8 -*-


a_cli = Analysis(
    ['controller_companion/launch.py'],
    pathex=[],
    binaries=[],
    datas=[('controller_companion/app/res', 'controller_companion/app/res')],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz_cli = PYZ(a_cli.pure)

a_app = Analysis(
    ['controller_companion/app/app.py'],
    pathex=[],
    binaries=[],
    datas=[('controller_companion/app/res', 'controller_companion/app/res')],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz_app = PYZ(a_app.pure)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name='controller-companion-cli',
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
    icon=['controller_companion/app/res/app.png'],
)
all_exe = [exe_cli]
exe_app = EXE(
    pyz_app,
    a_app.scripts,
    [],
    exclude_binaries=True,
    name='controller-companion',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['controller_companion/app/res/app.png'],
)
all_exe += [exe_app]
coll = COLLECT(
    *all_exe,
    a_cli.binaries,
    a_cli.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='controller-companion',
)
