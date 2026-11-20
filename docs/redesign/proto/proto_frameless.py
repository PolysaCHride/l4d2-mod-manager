# -*- coding: utf-8 -*-
"""验证无边框窗口 + 自定义标题栏 + JS 调用窗口控制。

这是路线 B 最容易翻车的地方：WebEngine 与 WA_TranslucentBackground 的兼容性。
"""
import os
import sys

from PySide6.QtCore import QObject, QPoint, QTimer, QUrl, Slot, Qt
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(HERE, "..", "final", "demo.html"))


class WindowBridge(QObject):
    """窗口控制桥：JS 通过它驱动原生窗口。"""

    def __init__(self, win):
        super().__init__()
        self.win = win

    @Slot()
    def minimize(self):
        print("[PY] minimize", flush=True)
        self.win.showMinimized()

    @Slot()
    def toggleMaximize(self):
        if self.win.isMaximized():
            self.win.showNormal()
            print("[PY] restore", flush=True)
        else:
            self.win.showMaximized()
            print("[PY] maximize", flush=True)
        return self.win.isMaximized()

    @Slot()
    def close(self):
        print("[PY] close", flush=True)
        self.win.close()

    @Slot(int, int)
    def startDrag(self, x, y):
        """记录拖动起点，由 Python 侧移动窗口。"""
        self._drag_origin = QPoint(x, y)
        self._win_origin = self.win.pos()
        print(f"[PY] drag start at {x},{y}", flush=True)

    @Slot(int, int)
    def moveDrag(self, x, y):
        if not hasattr(self, "_drag_origin"):
            return
        delta = QPoint(x, y) - self._drag_origin
        self.win.move(self._win_origin + delta)


class Window(QMainWindow):
    def __init__(self, shot=""):
        super().__init__()
        self.shot = shot
        # 无边框 + 透明背景（自绘圆角需要）
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1440, 900)

        central = QWidget()
        central.setObjectName("Root")
        central.setStyleSheet("#Root { background: #08090b; border-radius: 8px; }")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = QWebEngineView()
        self.view.setStyleSheet("background: transparent;")
        self.view.page().setBackgroundColor(Qt.transparent)
        layout.addWidget(self.view)
        self.setCentralWidget(central)

        wb = WindowBridge(self)
        self._wb = wb
        ch = QWebChannel()
        ch.registerObject("pywin", wb)
        self.view.page().setWebChannel(ch)

        self.view.page().javaScriptConsoleMessage = self._on_console
        self.view.loadFinished.connect(self._on_load)
        self.view.load(QUrl.fromLocalFile(PAGE))

    @staticmethod
    def _on_console(level, message, line, source):
        print(f"[JS:{line}] {message}", flush=True)

    def _on_load(self, ok):
        print(f"[PY] loadFinished ok={ok}", flush=True)
        if self.shot:
            QTimer.singleShot(2500, self._grab)

    def _grab(self):
        pix = self.grab()
        pix.save(self.shot)
        print(f"[PY] saved {self.shot} {pix.width()}x{pix.height()}", flush=True)
        QTimer.singleShot(300, QApplication.instance().quit)


def main():
    shot = ""
    if "--shot" in sys.argv:
        shot = sys.argv[sys.argv.index("--shot") + 1]
    app = QApplication(sys.argv)
    win = Window(shot)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
