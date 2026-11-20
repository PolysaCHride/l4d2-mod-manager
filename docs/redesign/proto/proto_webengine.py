# -*- coding: utf-8 -*-
"""路线 B 验证：QtWebEngine 承载现有前端。

验证项：
  1. 渲染 demo.html，与浏览器逐像素一致
  2. QWebChannel 双向通信
  3. 无边框窗口 + 自定义标题栏

用法：
    .venv/Scripts/python.exe proto_webengine.py                 # 打开 demo
    .venv/Scripts/python.exe proto_webengine.py --shot a.png    # 截图后退出
    .venv/Scripts/python.exe proto_webengine.py --page x.html   # 指定页面
"""
import json
import os
import sys

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

HERE = os.path.dirname(os.path.abspath(__file__))

FAKE_MODS = [
    {"id": "m1", "name": "Koharu [Replace Ellis]", "alias": "", "cat": "角色",
     "item": "Ellis", "size": 116.1, "enabled": False, "file": "3668116708.vpk",
     "img": "../assets/mods/mod1.webp", "added": "2 天前"},
    {"id": "m3", "name": "VRC プラム Plum replace ellis", "alias": "夏日甜点屋",
     "cat": "角色", "item": "Ellis", "size": 34.1, "enabled": True,
     "file": "3659210344.vpk", "img": "../assets/mods/mod3.webp", "added": "1 周前"},
    {"id": "m4", "name": "[Gakuen IDOLM@STER] Fujita", "alias": "", "cat": "角色",
     "item": "Ellis", "size": 146.4, "enabled": False, "file": "3671024551.vpk",
     "img": "../assets/mods/mod4.webp", "added": "1 周前"},
]


class Bridge(QObject):
    """暴露给 JS 的数据与命令。方法名与 demo.js 的调用约定一致。"""

    def __init__(self):
        super().__init__()
        self.mods = [dict(m) for m in FAKE_MODS]

    @Slot(result=str)
    def getMods(self):
        print("[PY] getMods", flush=True)
        return json.dumps(self.mods, ensure_ascii=False)

    @Slot(str, result=str)
    def toggleMod(self, mod_id):
        for m in self.mods:
            if m["id"] == mod_id:
                m["enabled"] = not m["enabled"]
                print(f"[PY] toggleMod {mod_id} -> {m['enabled']}", flush=True)
                return json.dumps({"ok": True, "enabled": m["enabled"]})
        return json.dumps({"ok": False})

    @Slot(str, result=str)
    def setAlias(self, payload):
        data = json.loads(payload)
        print(f"[PY] setAlias {data}", flush=True)
        for m in self.mods:
            if m["id"] == data["id"]:
                m["alias"] = data.get("alias", "")
                return json.dumps({"ok": True})
        return json.dumps({"ok": False})

    @Slot(result=str)
    def ping(self):
        print("[PY] ping", flush=True)
        return "pong"


class Window(QMainWindow):
    def __init__(self, page, shot=""):
        super().__init__()
        self.setWindowTitle("L4D2 Mod Manager · WebEngine 原型")
        self.resize(1440, 900)
        self.shot = shot

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = QWebEngineView()
        layout.addWidget(self.view)
        self.setCentralWidget(central)

        bridge = Bridge()
        self._bridge = bridge  # 防止被 GC
        self.channel = QWebChannel()
        self.channel.registerObject("pybridge", bridge)
        self.view.page().setWebChannel(self.channel)
        self.view.page().javaScriptConsoleMessage = self._on_console

        self.view.loadFinished.connect(self._on_load)
        self.view.load(QUrl.fromLocalFile(page))

    @staticmethod
    def _on_console(level, message, line, source):
        print(f"[JS:{line}] {message}", flush=True)

    def _on_load(self, ok):
        print(f"[PY] loadFinished ok={ok}", flush=True)
        if self.shot:
            QTimer.singleShot(3000, self._grab)

    def _grab(self):
        pix = self.grab()
        pix.save(self.shot)
        print(f"[PY] saved {self.shot} {pix.width()}x{pix.height()}", flush=True)
        QTimer.singleShot(300, QApplication.instance().quit)


def main():
    page = os.path.normpath(os.path.join(HERE, "..", "final", "demo.html"))
    shot = ""
    if "--page" in sys.argv:
        page = os.path.abspath(sys.argv[sys.argv.index("--page") + 1])
    if "--shot" in sys.argv:
        shot = sys.argv[sys.argv.index("--shot") + 1]

    print("[PY] page:", page, flush=True)
    app = QApplication(sys.argv)
    win = Window(page, shot)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
