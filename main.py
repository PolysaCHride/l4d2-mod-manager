# -*- coding: utf-8 -*-
"""旧界面入口（PySide6）—— **ARCHIVED 2026-11-21：仅供查阅，不再维护、不再发版。**

新界面入口是 `main_web.py`（pywebview + 系统 WebView2），这也是唯一发布路径。
本文件原地保留，`build_release.ps1 -Target legacy` 仍能构建它（会先警告），
取回完整可发版的旧界面：`git checkout archive/legacy-ui-2026-11-21`
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from app.ui import theme
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("L4D2 Mod Manager")
    app.setApplicationDisplayName("L4D2 Mod Manager")
    app.setWindowIcon(QIcon(theme.icon_path()))
    app.setFont(QFont("Microsoft YaHei", 9))
    theme.apply_qss(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
