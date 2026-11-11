# -*- coding: utf-8 -*-
"""L4D2 Mod Manager 入口。"""
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
