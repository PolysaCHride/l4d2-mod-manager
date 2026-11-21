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

# wiki 占位图（70 张）：预览图兜底的第 2/3 级。
# api._wiki_thumb 会按「物品 → 分类」找 assets/wiki/<name>.png，
# 不打进包的话打包版对没有预览图的模组只会显示渐变占位。
WIKI_DIR = os.path.join(ROOT, "assets", "wiki")
if os.path.isdir(WIKI_DIR):
    datas.append((WIKI_DIR, os.path.join("assets", "wiki")))

# 7-Zip 必须打进包：干净机器上没有它，压缩包导入会直接失败。
# 查找顺序见 app/core/archiver.py（bundled → remembered → installed → PATH）。
#
# 这里**故意不做 `if os.path.isdir(...)` 的静默跳过**：
# third_party/7zip/ 被 .gitignore 忽略（不进仓库），干净 clone 后目录根本不存在。
# 早期写法遇到这种情况会安静地打出一个缺 7z.exe 的包，装上才发现导入全挂。
# 现在缺文件就让构建直接失败；build_release.ps1 会提前跑 packaging/fetch_7zip.ps1 补齐。
ZIP_TOOLS = os.path.join(ROOT, "third_party", "7zip")
ZIP_REQUIRED = ("7z.exe", "7z.dll", "License.txt")
_missing_zip = [n for n in ZIP_REQUIRED
                if not os.path.isfile(os.path.join(ZIP_TOOLS, n))]
if _missing_zip:
    raise SystemExit(
        "打包中止：缺少 7-Zip 组件 " + ", ".join(_missing_zip) + "\n"
        "  期望目录: " + ZIP_TOOLS + "\n"
        "  修复: powershell -ExecutionPolicy Bypass "
        "-File packaging\\fetch_7zip.ps1")
datas.append((ZIP_TOOLS, "7zip"))

a = Analysis(
    [os.path.join(ROOT, "main_web.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # 只有这 3 项是「运行时动态加载」，静态分析看不到，必须写进来。
        # webview/platforms/__init__.py 按平台字符串 importlib 对应模块，
        # edgechromium 再 import pythonnet 的 clr。
        #
        # 其余 app.* 一律**不要**在这里重复列：
        # main_web.py → app.shell.api → app.core.* 全是静态 import，
        # PyInstaller 自己会跟进去；手写一遍只会让两处清单漂移
        # （以前列了 18 项，其中 15 项是多余的，加新模块时又常忘同步）。
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "clr",
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
