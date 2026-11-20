# -*- mode: python ; coding: utf-8 -*-
"""路线 B 原型打包：验证分发体积与冷启动。

只打包一个最小的 WebEngine 窗口，不接业务逻辑。
目的是拿到两个数字：体积、启动时间。
"""
import os

HERE = os.path.dirname(os.path.abspath(SPEC))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

FIN = os.path.join(ROOT, "docs", "redesign", "final")
datas = [
    (os.path.join(FIN, "demo.html"), "webui"),
    (os.path.join(FIN, "demo.css"), "webui"),
    (os.path.join(FIN, "demo.js"), "webui"),
    (os.path.join(FIN, "tokens.css"), "webui"),
    (os.path.join(ROOT, "docs", "redesign", "assets", "app-icon.png"), "webui/assets"),
    (os.path.join(ROOT, "docs", "redesign", "assets", "mods"), "webui/assets/mods"),
]

a = Analysis(
    [os.path.join(HERE, "proto_webengine.py")],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["PySide6.QtWebChannel"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 裁掉用不到的大件
    # 只排除确定用不到、且体量大的；WebEngine 依赖链很深，宁可不排除
    excludes=[
        "tkinter", "unittest", "doctest", "test",
        "numpy", "pandas", "matplotlib", "PIL",
        "setuptools", "pip", "pydoc_data",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DAnimation",
        "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DExtras",
        "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
        "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtSerialBus",
        "PySide6.QtTest", "PySide6.QtSql", "PySide6.QtDesigner",
        "PySide6.QtHelp", "PySide6.QtScxml", "PySide6.QtSpatialAudio",
        "PySide6.QtTextToSpeech", "PySide6.QtUiTools",
        "PySide6.QtRemoteObjects", "PySide6.QtStateMachine",
        "PySide6.QtHttpServer", "PySide6.QtGraphs", "PySide6.QtGraphsWidgets",
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
    name="L4D2Proto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="L4D2Proto",
)
