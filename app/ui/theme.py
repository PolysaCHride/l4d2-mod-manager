# -*- coding: utf-8 -*-
"""末世风主题：QSS + 危险条纹 pixmap + 类别配色 + 图标资源路径。"""
import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPixmap, QPen, QPolygonF

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")


def icon_path(name="icon.ico"):
    return os.path.join(_ASSETS_DIR, name)


def check_badge_pixmap(size=22, bg=None, fg="#14170f"):
    """启用徽章：绿色实心圆 + 深色对勾。"""
    bg = bg or GREEN
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(bg))
    p.drawEllipse(1, 1, size - 2, size - 2)
    pen = QPen(QColor(fg))
    pen.setWidthF(max(2.0, size / 9.0))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.drawPolyline(QPolygonF([
        QPointF(size * 0.27, size * 0.54),
        QPointF(size * 0.44, size * 0.70),
        QPointF(size * 0.74, size * 0.32),
    ]))
    p.end()
    return pm


def trash_pixmap(size=16, color="#d97b6c"):
    """垃圾桶线性图标（删除按钮用）。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.4)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    s = size
    p.drawRect(QRectF(s * 0.40, s * 0.10, s * 0.20, s * 0.12))       # 提手
    p.drawLine(QPointF(s * 0.14, s * 0.26), QPointF(s * 0.86, s * 0.26))  # 盖沿
    p.drawRoundedRect(QRectF(s * 0.24, s * 0.30, s * 0.52, s * 0.58), 2, 2)  # 桶身
    p.drawLine(QPointF(s * 0.42, s * 0.44), QPointF(s * 0.42, s * 0.74))
    p.drawLine(QPointF(s * 0.58, s * 0.44), QPointF(s * 0.58, s * 0.74))
    p.end()
    return pm


def caption_icon(kind, size=14, color="#c9cfb4"):
    """自绘标题栏按钮图标（最小化/最大化/关闭），基线稳定。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.5)
    p.setPen(pen)
    if kind == "min":
        y = size - 3.5
        p.drawLine(QPointF(2, y), QPointF(size - 2, y))
    elif kind == "max":
        p.drawRect(QRectF(2.5, 2.5, size - 5, size - 5))
    else:
        p.drawLine(QPointF(3, 3), QPointF(size - 3, size - 3))
        p.drawLine(QPointF(size - 3, 3), QPointF(3, size - 3))
    p.end()
    return QIcon(pm)

# ---- 调色板 ----
BG = "#101208"        # 窗口底
PANEL = "#161a10"     # 面板
PANEL2 = "#0c0e07"    # 更深面板（标题栏/状态栏）
BORDER = "#2a2f1c"
BORDER_L = "#3d4a24"
TEXT = "#c9cfb4"
TEXT_DIM = "#77806a"
GREEN = "#a3c24a"
GREEN_L = "#c6e37e"
GREEN_BG = "#232c15"
RED = "#b3311f"
RED_L = "#d24a35"
ROW_HOVER = "#191e10"

CAT_COLORS = {
    "幸存者": ("#4a148c", "#9c27b0", "👥"),
    "特感": ("#7a1f1f", "#b3311f", "☣"),
    "武器": ("#37474f", "#78909c", "🎯"),
    "近战": ("#5d4037", "#8d6e63", "🔪"),
    "医疗品": ("#1b5e20", "#689f38", "💉"),
    "投掷": ("#e65100", "#ffb300", "💣"),
    "UI": ("#263238", "#546e7a", "🖥"),
    "音效音乐": ("#311b92", "#7e57c2", "🎵"),
    "载具": ("#263238", "#607d8b", "🚗"),
    "弹药": ("#33691e", "#7cb342", "🧰"),
    "材质特效": ("#455a64", "#90a4ae", "✨"),
    "动作": ("#4e342e", "#795548", "🏃"),
    "地图": ("#1b5e20", "#558b2f", "🗺"),
    "杂项": ("#424242", "#757575", "📦"),
    "其他": ("#37474f", "#607d8b", "❔"),
    "未分类": ("#212121", "#4e4e4e", "❔"),
}

QSS = """
* { outline: none; }
QWidget { background: %(BG)s; color: %(TEXT)s; font-family: "Microsoft YaHei"; font-size: 13px; }
QMainWindow, QDialog { background: %(BG)s; }

/* ---- 标题栏 ---- */
#TitleBar { background: %(PANEL2)s; border-bottom: 1px solid %(BORDER)s; }
#TitleBar QLabel { background: transparent; color: %(GREEN)s; font-size: 14px; font-weight: bold; letter-spacing: 3px; }
#TitleBar QPushButton {
  background: transparent; color: %(TEXT_DIM)s; border: none; border-radius: 0;
}
#TitleBar QPushButton:hover { background: %(BORDER)s; }
#TitleBar QPushButton#btnClose:hover { background: #c42b1c; }

/* ---- 左侧分类栏 ---- */
#Rail { background: %(PANEL2)s; border-right: 1px solid %(BORDER)s; }
#Rail QPushButton {
  background: transparent; color: %(TEXT_DIM)s; border: none; border-radius: 4px;
  min-height: 34px; text-align: center; padding: 2px 0; font-weight: bold;
}
#Rail QPushButton:hover { background: %(ROW_HOVER)s; color: %(GREEN)s; }
#Rail QPushButton:checked { background: %(GREEN_BG)s; color: %(GREEN_L)s; border-left: 3px solid %(GREEN)s; }

/* ---- 物品列表 / 通用列表 ---- */
QListWidget {
  background: %(PANEL)s; border: 1px solid %(BORDER)s; border-radius: 4px;
  padding: 4px; font-size: 13px;
}
QListWidget::item { color: %(TEXT)s; padding: 7px 8px; border-radius: 3px; }
QListWidget::item:hover { background: %(ROW_HOVER)s; }
QListWidget::item:selected { background: %(GREEN_BG)s; color: %(GREEN_L)s; border-left: 3px solid %(GREEN)s; }

/* ---- 输入 ---- */
QLineEdit {
  background: %(PANEL2)s; border: 1px solid %(BORDER)s; border-radius: 3px;
  padding: 6px 10px; color: %(TEXT)s; selection-background-color: %(GREEN)s; selection-color: %(PANEL2)s;
}
QLineEdit:focus { border-color: %(GREEN)s; }
QComboBox {
  background: %(PANEL2)s; border: 1px solid %(BORDER)s; border-radius: 3px; padding: 5px 10px;
}
QComboBox:hover { border-color: %(BORDER_L)s; }
QComboBox QAbstractItemView { background: %(PANEL)s; border: 1px solid %(BORDER)s; selection-background-color: %(GREEN_BG)s; color: %(TEXT)s; }
QSpinBox { background: %(PANEL2)s; border: 1px solid %(BORDER)s; padding: 4px; }

/* ---- 选项卡：选中态高亮 ---- */
QTabWidget::pane { border: 1px solid %(BORDER)s; border-radius: 3px; top: -1px; }
QTabBar::tab {
  background: %(PANEL2)s; color: %(TEXT_DIM)s; padding: 7px 20px;
  border: 1px solid %(BORDER)s; border-bottom: 2px solid %(BORDER)s;
  border-top-left-radius: 4px; border-top-right-radius: 4px;
  margin-right: 4px;
}
QTabBar::tab:selected { background: %(PANEL)s; color: %(GREEN_L)s; border-bottom: 2px solid %(GREEN)s; }
QTabBar::tab:!selected:hover { background: %(ROW_HOVER)s; color: %(TEXT)s; }

/* ---- 按钮 ---- */
QPushButton {
  background: #1a1f12; color: %(GREEN)s; border: 1px solid %(BORDER_L)s; border-radius: 3px;
  padding: 7px 16px; font-weight: bold; letter-spacing: 1px;
}
QPushButton:hover { background: %(GREEN_BG)s; color: %(GREEN_L)s; }
QPushButton:disabled { color: #4a5140; border-color: %(BORDER)s; }
QPushButton[accent="primary"] { background: %(RED)s; border-color: %(RED_L)s; color: #f4e8dd; }
QPushButton[accent="primary"]:hover { background: #c93e2a; color: #ffffff; }
QPushButton[accent="danger"] { background: transparent; border-color: #7a2a1f; color: #d97b6c; }
QPushButton[accent="danger"]:hover { background: #2a120d; color: #ff9b8a; }

/* ---- 开关（QCheckBox） ---- */
QCheckBox::indicator {
  width: 34px; height: 16px; border-radius: 8px;
  background: %(PANEL2)s; border: 1px solid %(BORDER_L)s;
}
QCheckBox::indicator:hover { border-color: %(GREEN)s; }
QCheckBox::indicator:checked { background: %(GREEN)s; border-color: %(GREEN_L)s; }
QCheckBox::indicator:disabled { background: #14170f; border-color: %(BORDER)s; }

/* ---- 卡片 ---- */
#ModCard {
  background: #14170d; border: 1px solid #232819; border-radius: 4px;
}
#ModCard:hover { border-color: #4a5a2c; background: #191e10; }
#ModCard[state="off"] { background: #101208; }
#ModCard QLabel { background: transparent; }
#CardTitle { color: #d7ddba; font-weight: bold; font-size: 13px; }
#CardAlias { color: %(GREEN)s; font-size: 11px; }
#CardMeta { color: %(TEXT_DIM)s; font-size: 11px; }
#CardThumb { border: 1px solid #232819; border-radius: 3px; background: #0c0e07; }

/* ---- 标签 chip ---- */
#TagOn  { background: %(GREEN)s; color: #14170f; font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 2px; letter-spacing: 2px; }
#TagOff { background: transparent; color: %(TEXT_DIM)s; font-size: 10px; padding: 2px 8px; border: 1px solid %(BORDER_L)s; border-radius: 2px; letter-spacing: 2px; }

/* ---- 菜单 / 提示 ---- */
QMenu { background: %(PANEL)s; border: 1px solid %(BORDER_L)s; padding: 4px; }
QMenu::item { padding: 7px 22px; border-radius: 3px; }
QMenu::item:selected { background: %(GREEN_BG)s; color: %(GREEN_L)s; }
QToolTip { background: %(PANEL)s; color: %(TEXT)s; border: 1px solid %(BORDER_L)s; padding: 4px; }

/* ---- 进度条：胶囊型，轨道与背景同色，填充内缩留缝 ---- */
QProgressBar {
  background: %(BG)s; border: 1px solid %(BORDER)s; border-radius: 10px;
  padding: 3px; min-height: 20px; max-height: 20px;
  text-align: center; color: %(TEXT)s; font-size: 10px;
}
QProgressBar::chunk { background: %(GREEN)s; border-radius: 6px; }

/* ---- 滚动条：透明轨道融入面板，胶囊滑块内缩 ---- */
QScrollBar:vertical { background: transparent; width: 14px; border: none; margin: 3px 2px; }
QScrollBar::handle:vertical { background: #39412a; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: %(BORDER_L)s; }
QScrollBar:horizontal { background: transparent; height: 14px; border: none; margin: 2px 3px; }
QScrollBar::handle:horizontal { background: #39412a; border-radius: 5px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: %(BORDER_L)s; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---- 状态栏 / 日志 ---- */
#StatusBar { background: %(PANEL2)s; border-top: 1px solid %(BORDER)s; }
#StatusBar QLabel { background: transparent; color: %(TEXT_DIM)s; font-size: 11px; }
/* ---- 分栏拖拽把手 ---- */
QSplitter::handle { background: %(PANEL2)s; }
QSplitter::handle:hover { background: %(BORDER_L)s; }
QSplitter::handle:horizontal { width: 5px; }
QSplitter::handle:vertical { height: 5px; }

QPlainTextEdit, QTextEdit {
  background: %(PANEL2)s; border: 1px solid %(BORDER)s; color: %(TEXT)s;
  font-family: "Microsoft YaHei"; font-size: 12px;
}
QTreeWidget { background: %(PANEL)s; border: 1px solid %(BORDER)s; }
QTreeWidget::item { padding: 5px; }
QTreeWidget::item:selected { background: %(GREEN_BG)s; color: %(GREEN_L)s; }
QHeaderView::section { background: %(PANEL2)s; color: %(TEXT_DIM)s; border: none; border-bottom: 1px solid %(BORDER)s; padding: 5px; }
QTableWidget { background: %(PANEL)s; border: 1px solid %(BORDER)s; gridline-color: %(BORDER)s; }
QLabel#DlgTitle { color: %(GREEN_L)s; font-size: 15px; font-weight: bold; letter-spacing: 2px; }
QLabel#Hint { color: %(TEXT_DIM)s; font-size: 11px; }

/* ---- 设置页：分组 + 卡片行 ---- */
#SettingsPage { background: %(BG)s; }
#SettingsPage QLabel { background: transparent; }
#SettingsSection { color: %(TEXT)s; font-size: 15px; font-weight: bold; letter-spacing: 2px; background: transparent; }
#SettingsCard { background: #14170d; border: 1px solid #232819; border-radius: 4px; }
#SettingsCard:hover { border-color: #4a5a2c; }
#SettingsTitle { color: #d7ddba; font-weight: bold; font-size: 13px; }
#SettingsSub { color: %(TEXT_DIM)s; font-size: 11px; }
"""


def apply_qss(app):
    app.setStyleSheet(QSS % {
        "BG": BG, "PANEL": PANEL, "PANEL2": PANEL2, "BORDER": BORDER,
        "BORDER_L": BORDER_L, "TEXT": TEXT, "TEXT_DIM": TEXT_DIM,
        "GREEN": GREEN, "GREEN_L": GREEN_L, "GREEN_BG": GREEN_BG,
        "RED": RED, "RED_L": RED_L, "ROW_HOVER": ROW_HOVER,
    })


def hazard_pixmap(w, h):
    """45° 血红/暗黑危险条纹。"""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF
    pm = QPixmap(w, h)
    pm.fill(QColor(PANEL2))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(RED))
    step = 22
    x = -h
    while x < w + h:
        p.drawPolygon(QPolygonF([QPointF(x, h), QPointF(x + h, 0),
                                 QPointF(x + h + 9, 0), QPointF(x + 9, h)]))
        x += step
    p.end()
    return pm


def thumb_pixmap(width, height, category, emoji=None):
    """无预览图时的占位缩略图：类别渐变 + emoji。"""
    c1, c2, em = CAT_COLORS.get(category, ("#424242", "#757575", "❔"))
    pm = QPixmap(width, height)
    pm.fill(QColor("#0c0e07"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, width, height)
    g.setColorAt(0, QColor(c1))
    g.setColorAt(1, QColor(c2))
    p.fillRect(0, 0, width, height, g)
    p.setPen(QPen(QColor(0, 0, 0, 60), 2))
    p.setFont(__import__("PySide6.QtGui", fromlist=["QFont"]).QFont("Segoe UI Emoji", int(height * 0.32)))
    p.drawText(pm.rect(), Qt.AlignCenter, emoji or em)
    p.end()
    return pm
