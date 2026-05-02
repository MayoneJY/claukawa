# PyInstaller spec for macOS. Run from project root:
#     pyinstaller build/claukawa-mac.spec
# -*- mode: python ; coding: utf-8 -*-
#
# Notes:
# - Produces dist/Claukawa.app (a .app bundle).
# - LSUIElement=True hides the Dock icon; we live in the menu bar instead.
# - This build is unsigned. On first launch users must right-click -> Open
#   to bypass Gatekeeper. For wider distribution add Apple codesign + notarize.
# - For tray_icon.icns generation see README.

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent  # type: ignore[name-defined]
SRC = PROJECT_ROOT / "src"
ASSETS = SRC / "claukawa" / "assets"

datas = [
    (str(ASSETS / "gifs" / "default"), "claukawa/assets/gifs/default"),
    (str(ASSETS / "tray_icon.png"), "claukawa/assets"),
    (str(ASSETS / "tray_icon_template.png"), "claukawa/assets"),
]

icns_path = ASSETS / "tray_icon.icns"
if icns_path.exists():
    datas.append((str(icns_path), "claukawa/assets"))

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
    [],
    exclude_binaries=True,
    name="Claukawa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icns_path) if icns_path.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Claukawa",
)

app = BUNDLE(
    coll,
    name="Claukawa.app",
    icon=str(icns_path) if icns_path.exists() else None,
    bundle_identifier="com.claukawa",
    info_plist={
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "CFBundleName": "Claukawa",
        "CFBundleDisplayName": "Claukawa",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
    },
)
