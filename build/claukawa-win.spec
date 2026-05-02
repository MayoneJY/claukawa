# PyInstaller spec for Windows. Run from project root:
#     pyinstaller build/claukawa-win.spec
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent  # type: ignore[name-defined]
SRC = PROJECT_ROOT / "src"
ASSETS = SRC / "claukawa" / "assets"

datas = [
    (str(ASSETS / "gifs" / "default"), "claukawa/assets/gifs/default"),
    (str(ASSETS / "tray_icon.ico"), "claukawa/assets"),
    (str(ASSETS / "tray_icon.png"), "claukawa/assets"),
    (str(ASSETS / "tray_icon_template.png"), "claukawa/assets"),
]

a = Analysis(
    [str(SRC / "claukawa" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name="Claukawa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS / "tray_icon.ico"),
)
