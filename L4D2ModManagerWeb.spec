# -*- mode: python ; coding: utf-8 -*-
"""WebUI 版本打包配置。

体积目标 < 100MB。pywebview 用系统 WebView2，不打包 Chromium。
"""
import os

HERE = os.path.dirname(os.path.abspath(SPEC))
ROOT = os.path.abspath(HERE)          # spec 放在项目根，HERE 就是根
WEBUI = os.path.join(ROOT, "app", "webui")

datas = [
    (WEBUI, "webui"),
    (os.path.join(ROOT, "assets", "icon.ico"), "."),
]

# 7-Zip 必须打进包：干净机器上没有它，压缩包导入会直接失败。
# 查找顺序见 app/core/archiver.py（bundled → remembered → installed → PATH）。
ZIP_TOOLS = os.path.join(ROOT, "third_party", "7zip")
if os.path.isdir(ZIP_TOOLS):
    datas.append((ZIP_TOOLS, "7zip"))

a = Analysis(
    [os.path.join(ROOT, "main_web.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "clr",
        "app.shell",
        "app.shell.api",
        "app.shell.tasks",
        "app.shell.jobs",
        "app.core.library",
        "app.core.store",
        "app.core.paths",
        "app.core.app_paths",
        "app.core.importer",
        "app.core.downloader",
        "app.core.steam_api",
        "app.core.classify",
        "app.core.vpk",
        "app.core.game",
        "app.core.archiver",
        "app.core.addonlist",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "unittest", "doctest", "test",
        "numpy", "pandas", "matplotlib", "scipy",
        "setuptools", "pip", "pydoc_data", "lib2to3",
        "PySide6", "PyQt5", "PyQt6",     # 新入口不依赖 Qt
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="L4D2 Mod Manager (WebUI)",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "assets", "icon.ico"),
    version=os.path.join(ROOT, "packaging", "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="L4D2 Mod Manager (WebUI)",
)
