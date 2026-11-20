# -*- mode: python ; coding: utf-8 -*-
"""pywebview 原型打包：对比路线 B 的两种承载层。"""
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
    [os.path.join(HERE, "proto_pywebview.py")],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["webview.platforms.winforms", "clr"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "unittest", "doctest", "test",
        "numpy", "pandas", "matplotlib", "PIL",
        "setuptools", "pip", "pydoc_data",
        "PySide6",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="L4D2Web",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, upx=False,
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="L4D2Web")
