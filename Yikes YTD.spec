import sys
import os

# OS Detection
is_win = sys.platform.startswith('win')
is_mac = sys.platform == 'darwin'

# Icon Selection
icon_path = 'app-images/icon.ico'
if not os.path.exists(icon_path):
    icon_path = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('app-images', 'app-images')],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Yikes YTD.exe' if is_win else 'Yikes YTD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

# MacOS Bundle Support
if is_mac:
    app = BUNDLE(
        exe,
        name='Yikes YTD.app',
        icon=icon_path,
        bundle_identifier='com.kuzzi.yikesytd',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'NSPrincipalClass': 'NSApplication',
        },
    )
