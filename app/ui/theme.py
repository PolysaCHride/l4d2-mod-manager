# -*- coding: utf-8 -*-
"""末世风主题：QSS + 危险条纹 pixmap + 类别配色 + 图标资源路径。"""
import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPixmap, QPen, QPolygonF

from ..core import app_paths

_ASSETS_DIR = app_paths.asset_path()


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


def caption_icon(kind, size=14, color="#f0f0f0"):
    """Windows 风格标题栏按钮图标（最小化/最大化/关闭）。"""
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
    elif kind == "restore":
        p.drawRect(QRectF(2.5, 4.5, size - 6, size - 7))
        p.drawRect(QRectF(4.5, 2.5, size - 6, size - 7))
    else:
        p.drawLine(QPointF(3, 3), QPointF(size - 3, size - 3))
        p.drawLine(QPointF(size - 3, 3), QPointF(3, size - 3))
    p.end()
    return QIcon(pm)

# ---- 调色板 ----
BG = "#0b0d09"        # 窗口底
PANEL = "#151810"     # 面板
PANEL2 = "#0e100b"    # 更深面板（标题栏/状态栏）
BORDER = "#2b3125"
BORDER_L = "#455037"
TEXT = "#dde2d1"
TEXT_DIM = "#8b937f"
GREEN = "#b5d35f"
GREEN_L = "#d4e99d"
GREEN_BG = "#252f19"
RED = "#bd402c"
RED_L = "#ea6b50"
ROW_HOVER = "#1c2117"

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

/* ---- 工坊下载：合并任务卡 + 当前模组提示 ---- */
QFrame#DownloadProgressPanel {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                              stop:0 #12160c, stop:1 #171c0f);
  border: 1px solid #30381e; border-radius: 6px;
}
#ProgressTitle {
  color: #dfe6c6; font-size: 12px; font-weight: bold; letter-spacing: 1px;
  background: transparent;
}
#ProgressMeta {
  color: %(GREEN_L)s; font-size: 11px; background: transparent;
}
#ProgressCurrent {
  color: %(TEXT_DIM)s; font-size: 11px; background: transparent;
}
#LogTitle {
  color: #c5cfaa; font-size: 12px; font-weight: bold; letter-spacing: 1px;
  background: transparent;
}
QProgressBar#DownloadProgress {
  background: #090b06; border: 1px solid #3b4724; border-radius: 9px;
  padding: 3px; min-height: 25px; max-height: 25px;
  color: #eff5dc; font-size: 11px; font-weight: bold; text-align: center;
}
QProgressBar#DownloadProgress::chunk {
  border-radius: 6px;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                              stop:0 #65772a, stop:0.55 #98b441, stop:1 #cadf72);
}

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
QPlainTextEdit#TaskLog {
  background: #090b06; border: 1px solid #29301b; border-left: 2px solid #526329;
  border-radius: 4px; padding: 5px 7px; color: #aeb89a;
  selection-background-color: #3c4920; selection-color: #eef4dc;
}
QTreeWidget { background: %(PANEL)s; border: 1px solid %(BORDER)s; }
QTreeWidget::item { padding: 5px; }
QTreeWidget::item:selected { background: %(GREEN_BG)s; color: %(GREEN_L)s; }
QHeaderView::section { background: %(PANEL2)s; color: %(TEXT_DIM)s; border: none; border-bottom: 1px solid %(BORDER)s; padding: 5px; }
QTableWidget { background: %(PANEL)s; border: 1px solid %(BORDER)s; gridline-color: %(BORDER)s; }
QLabel#DlgTitle { color: %(GREEN_L)s; font-size: 15px; font-weight: bold; letter-spacing: 2px; }
QLabel#Hint { color: %(TEXT_DIM)s; font-size: 11px; }

/* ---- 压缩包导入向导 ---- */
QFrame#ArchiveDropZone {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                              stop:0 #14180d, stop:1 #0e1108);
  border: 1px dashed #46532b; border-radius: 6px;
}
QFrame#ArchiveDropZone:hover { background: #181d0f; border-color: %(GREEN)s; }
QFrame#ArchiveDropZone[dragActive="true"] {
  background: #1d2411; border: 1px solid %(GREEN)s;
}
QLabel#ImportDropIcon {
  background: %(GREEN_BG)s; color: %(GREEN_L)s; border: 1px solid #435329;
  border-radius: 23px; font-size: 26px; font-weight: normal;
}
QLabel#ImportDropTitle { color: #dce4c4; font-size: 14px; font-weight: bold; background: transparent; }
QLabel#ImportDropHint { color: %(TEXT_DIM)s; font-size: 11px; background: transparent; }
QFrame#ImportStatusPanel { background: #12160c; border: 1px solid #2d351d; border-radius: 5px; }
QLabel#ImportStatus { color: #d6dfbb; font-size: 12px; font-weight: bold; background: transparent; }
QProgressBar#ImportProgress {
  background: #090b06; border: 1px solid #394424; border-radius: 4px;
  min-height: 7px; max-height: 7px; padding: 1px;
}
QProgressBar#ImportProgress::chunk { background: %(GREEN)s; border-radius: 3px; }
QLabel#ImportResultTitle { color: #d9e1c2; font-size: 13px; font-weight: bold; letter-spacing: 1px; }
QScrollArea#ImportResultsScroll { background: transparent; border: none; }
QWidget#ImportResultsHost { background: transparent; }
QLabel#ImportEmpty {
  color: %(TEXT_DIM)s; background: #11140b; border: 1px solid #242b19;
  border-radius: 5px; font-size: 12px;
}
QFrame#ImportCandidate {
  background: #14180d; border: 1px solid #252c19; border-radius: 5px;
}
QFrame#ImportCandidate:hover { background: #191e10; border-color: #46582a; }
QFrame#ImportCandidate[duplicate="true"] { background: #101208; border-color: #202517; }
QFrame#ImportCandidate QLabel { background: transparent; }
QCheckBox#ImportSelect::indicator {
  width: 18px; height: 18px; border-radius: 3px;
  background: #0b0e07; border: 1px solid #536337;
}
QCheckBox#ImportSelect::indicator:hover { border-color: %(GREEN_L)s; }
QCheckBox#ImportSelect::indicator:checked { background: %(GREEN)s; border: 1px solid %(GREEN_L)s; }
QCheckBox#ImportSelect::indicator:disabled { background: #151811; border-color: #2e3422; }
QLabel#ImportThumb { background: #0b0e07; border: 1px solid #29301c; border-radius: 3px; }
QLabel#ImportCandidateTitle { color: #e0e7ca; font-size: 13px; font-weight: bold; }
QLabel#ImportCandidateMeta { color: #a5af90; font-size: 11px; }
QLabel#ImportCandidateSource { color: %(TEXT_DIM)s; font-size: 10px; }
QLabel#ImportReady {
  color: %(GREEN_L)s; background: %(GREEN_BG)s; border: 1px solid #425329;
  border-radius: 3px; padding: 3px 7px; font-size: 10px;
}
QLabel#ImportDuplicate {
  color: #bf8d75; background: #21150e; border: 1px solid #4a2b1e;
  border-radius: 3px; padding: 3px 7px; font-size: 10px;
}

/* ---- 设置页：分组 + 卡片行 ---- */
#SettingsPage { background: %(BG)s; }
#SettingsPage QLabel { background: transparent; }
#SettingsSection { color: %(TEXT)s; font-size: 15px; font-weight: bold; letter-spacing: 2px; background: transparent; }
#SettingsCard { background: #14170d; border: 1px solid #232819; border-radius: 4px; }
#SettingsCard:hover { border-color: #4a5a2c; }
#SettingsTitle { color: #d7ddba; font-weight: bold; font-size: 13px; }
#SettingsSub { color: %(TEXT_DIM)s; font-size: 11px; }
QWidget#SettingsActionHost { background: transparent; border: none; }
"""


# 新版界面样式放在旧版之后，按完整窗口层级重排圆角、间距和交互状态。
QSS = """
* { outline: none; }
QWidget {
  background: %(BG)s; color: %(TEXT)s;
  font-family: "Microsoft YaHei UI", "Microsoft YaHei";
  font-size: 13px;
}
QLabel { background: transparent; }
QMainWindow#AppWindow, QDialog#TransparentDialog, QWidget#WindowCanvas,
QWidget#WindowBody, QWidget#PageStack, QWidget#MessageExtra {
  background: transparent; border: none;
}
QFrame#AppSurface {
  background: #11140d; border: 1px solid #343a2d; border-radius: 16px;
}
QFrame#AppSurface[windowMaximized="true"] { border-radius: 0; }
QFrame#DialogSurface {
  background: #11140d; border: 1px solid #3a4231; border-radius: 16px;
}
QWidget#DialogContent {
  background: #11140d;
  border-bottom-left-radius: 15px; border-bottom-right-radius: 15px;
}

/* ---- 标题栏 ---- */
#TitleBar {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                              stop:0 #141810, stop:0.62 #11140d, stop:1 #151a11);
  border: none; border-top-left-radius: 15px; border-top-right-radius: 15px;
}
#TitleBar[windowMaximized="true"] { border-radius: 0; }
#TitleBar QLabel { background: transparent; }
#TitleIcon {
  background: transparent; border: none; border-radius: 0;
}
QLabel#AppTitle {
  color: %(TEXT)s; font-size: 14px; font-weight: 700; letter-spacing: 1px;
}
QWidget#CaptionControls { background: transparent; border: none; }
QPushButton[role="window"] {
  background: transparent; border: none;
  border-radius: 0; padding: 0;
}
QPushButton[role="window"]:hover {
  background: #2d2d2d; border: none;
}
QPushButton[role="window"]:pressed { background: #383838; }
QPushButton[role="window"]:focus {
  background: transparent; border: none;
}
QPushButton#btnClose:hover {
  background: #c42b1c; border: none;
  border-top-right-radius: 15px;
}
QPushButton#btnClose:pressed {
  background: #b12518; border: none;
  border-top-right-radius: 15px;
}
QPushButton#btnClose[windowMaximized="true"]:hover,
QPushButton#btnClose[windowMaximized="true"]:pressed {
  border-radius: 0;
}
QPushButton#btnClose:focus {
  background: transparent; border: none;
}
#HazardDivider { background: #0d100b; border: none; }

/* ---- 对话框标题栏 ---- */
#DialogTitleBar {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                              stop:0 #171c12, stop:1 #11140d);
  border-top-left-radius: 15px; border-top-right-radius: 15px;
}
#DialogTitleBar QLabel { background: transparent; }
QLabel#DialogIcon {
  background: transparent; border: none; border-radius: 0;
}
QLabel#DialogTitle {
  color: %(TEXT)s; font-size: 13px; font-weight: 700; letter-spacing: 1px;
}
QSizeGrip#DialogSizeGrip { background: transparent; width: 18px; height: 18px; }

/* ---- 主界面分区 ---- */
#Rail {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #171b12, stop:1 #10130d);
  border: 1px solid %(BORDER)s; border-radius: 13px;
}
#Rail QPushButton {
  background: transparent; color: %(TEXT_DIM)s; border: none; border-radius: 10px;
  min-height: 42px; text-align: center; padding: 2px 0; font-weight: 700;
}
#Rail QPushButton:hover { background: %(ROW_HOVER)s; color: %(TEXT)s; }
#Rail QPushButton:checked {
  background: %(GREEN_BG)s; color: %(GREEN_L)s; border: 1px solid #46582e;
}
#Rail QPushButton#RailUtility {
  background: #141810; color: %(TEXT_DIM)s; border: 1px dashed #353d2b;
  border-radius: 10px; font-size: 11px; font-weight: 600;
}
#Rail QPushButton#RailUtility:hover {
  background: #1d2317; color: %(GREEN_L)s; border-color: #52643a;
}
QWidget#SidePane, QWidget#BrowserPane {
  background: #12150e; border: 1px solid %(BORDER)s; border-radius: 13px;
}
QLabel#PaneTitle {
  color: %(TEXT_DIM)s; font-size: 10px; font-weight: 700;
  letter-spacing: 1px; padding: 1px 3px;
}
QFrame#ActionBar {
  background: #171b13; border: 1px solid #30372a; border-radius: 12px;
}
QStackedWidget#PageStack { background: transparent; border: none; }
QSplitter#WorkspaceSplitter { background: transparent; }
QSplitter::handle { background: transparent; }
QSplitter::handle:hover { background: #313a2b; border-radius: 2px; }
QSplitter::handle:horizontal { width: 8px; }
QSplitter::handle:vertical { height: 8px; }

/* ---- 列表 ---- */
QListWidget {
  background: transparent; border: none; border-radius: 9px;
  padding: 3px; font-size: 13px;
}
QListWidget::item {
  color: %(TEXT)s; padding: 9px 10px; border-radius: 8px; margin: 1px 0;
}
QListWidget::item:hover { background: %(ROW_HOVER)s; }
QListWidget::item:selected {
  background: %(GREEN_BG)s; color: %(GREEN_L)s;
  border: 1px solid #3d4d29;
}
QListWidget::item:disabled { color: %(TEXT_DIM)s; }

/* ---- 输入 ---- */
QLineEdit {
  background: %(PANEL2)s; border: 1px solid #343b2d; border-radius: 9px;
  padding: 7px 11px; color: %(TEXT)s;
  selection-background-color: %(GREEN)s; selection-color: %(PANEL2)s;
}
QLineEdit:hover { border-color: %(BORDER_L)s; }
QLineEdit:focus { border-color: %(GREEN)s; background: #10130d; }
QLineEdit#SearchField { padding-left: 13px; font-size: 13px; }
QComboBox {
  background: %(PANEL2)s; border: 1px solid #343b2d; border-radius: 9px;
  padding: 6px 32px 6px 11px; min-width: 92px;
}
QComboBox:hover { border-color: %(BORDER_L)s; }
QComboBox:focus { border-color: %(GREEN)s; }
QComboBox::drop-down {
  subcontrol-origin: padding; subcontrol-position: top right;
  width: 28px; border: none; background: transparent;
}
QComboBox::down-arrow {
  image: url("%(ARROW)s"); width: 12px; height: 8px;
}
QComboBox QAbstractItemView {
  background: #171b13; border: 1px solid %(BORDER_L)s; border-radius: 8px;
  selection-background-color: %(GREEN_BG)s; color: %(TEXT)s; padding: 4px;
}
QSpinBox {
  background: %(PANEL2)s; border: 1px solid #343b2d; border-radius: 8px;
  padding: 5px 7px;
}

/* ---- 选项卡 ---- */
QTabWidget::pane {
  background: #12150e; border: 1px solid %(BORDER)s; border-radius: 12px;
  top: -1px;
}
QTabBar::tab {
  background: transparent; color: %(TEXT_DIM)s; padding: 8px 18px;
  border: 1px solid transparent; border-radius: 8px; margin-right: 4px;
  font-weight: 600;
}
QTabBar::tab:selected {
  background: %(GREEN_BG)s; color: %(GREEN_L)s; border-color: #40502b;
}
QTabBar::tab:!selected:hover { background: %(ROW_HOVER)s; color: %(TEXT)s; }

/* ---- 按钮 ---- */
QPushButton {
  background: #1b2016; color: %(GREEN)s; border: 1px solid #3f4a31;
  border-radius: 9px; padding: 7px 15px; font-weight: 700; letter-spacing: 0.5px;
}
QPushButton:hover {
  background: %(GREEN_BG)s; color: %(GREEN_L)s; border-color: #5a6c3c;
}
QPushButton:pressed { background: #1b2413; }
QPushButton:focus { border-color: %(GREEN_L)s; }
QPushButton:disabled {
  color: #596051; border-color: #2a3024; background: #14170f;
}
QPushButton[accent="primary"] {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                              stop:0 #c54a34, stop:1 #a93423);
  border-color: #e06a50; color: #fff4ed;
}
QPushButton[accent="primary"]:hover {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                              stop:0 #d75b43, stop:1 #b83b27);
  border-color: #f08368;
}
QPushButton[accent="primary"]:pressed { background: #9e2e1d; }
QPushButton[accent="danger"] {
  background: transparent; border-color: #743428; color: #dc8a75;
}
QPushButton[accent="danger"]:hover {
  background: #2a1510; border-color: #a64c3a; color: #ffac98;
}

/* ---- 开关 ---- */
QCheckBox::indicator {
  width: 34px; height: 16px; border-radius: 8px;
  background: %(PANEL2)s; border: 1px solid %(BORDER_L)s;
}
QCheckBox::indicator:hover { border-color: %(GREEN)s; }
QCheckBox::indicator:checked { background: %(GREEN)s; border-color: %(GREEN_L)s; }
QCheckBox::indicator:disabled { background: #14170f; border-color: %(BORDER)s; }

/* ---- MOD 卡片 ---- */
#ModCard {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #181c13, stop:1 #141710);
  border: 1px solid #30362a; border-radius: 12px;
}
#ModCard:hover { background: #1c2117; border-color: #53633b; }
#ModCard[state="off"] { background: #11140e; border-color: #272d22; }
#ModCard QLabel { background: transparent; }
#CardTitle {
  color: #e2e7d5; font-weight: 700; font-size: 13px; padding: 0 2px;
}
#CardAlias { color: %(GREEN)s; font-size: 11px; padding: 0 2px; }
#CardMeta { color: %(TEXT_DIM)s; font-size: 10px; padding: 0 2px; }
#CardThumb { border: none; border-radius: 9px; background: #0b0e08; }

/* ---- 标签 chip ---- */
#TagOn {
  background: %(GREEN)s; color: #12150e; font-size: 10px; font-weight: 700;
  padding: 2px 8px; border-radius: 6px; letter-spacing: 1px;
}
#TagOff {
  background: transparent; color: %(TEXT_DIM)s; font-size: 10px;
  padding: 2px 8px; border: 1px solid %(BORDER_L)s;
  border-radius: 6px; letter-spacing: 1px;
}

/* ---- 菜单 / 提示 ---- */
QMenu {
  background: #171b13; border: 1px solid %(BORDER_L)s;
  border-radius: 10px; padding: 5px;
}
QMenu::item { padding: 8px 24px; border-radius: 7px; }
QMenu::item:selected { background: %(GREEN_BG)s; color: %(GREEN_L)s; }
QToolTip {
  background: #1b2016; color: %(TEXT)s; border: 1px solid %(BORDER_L)s;
  border-radius: 7px; padding: 5px 7px;
}

/* ---- 进度条 ---- */
QProgressBar {
  background: #090b07; border: 1px solid #333b2c; border-radius: 10px;
  padding: 3px; min-height: 20px; max-height: 20px;
  text-align: center; color: %(TEXT)s; font-size: 10px;
}
QProgressBar::chunk {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                              stop:0 #7f9a3c, stop:1 %(GREEN)s);
  border-radius: 6px;
}
QFrame#DownloadProgressPanel {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                              stop:0 #141810, stop:1 #191e15);
  border: 1px solid #353e2c; border-radius: 11px;
}
#ProgressTitle {
  color: #e3e9d4; font-size: 12px; font-weight: 700;
  letter-spacing: 0.8px; background: transparent;
}
#ProgressMeta { color: %(GREEN_L)s; font-size: 11px; background: transparent; }
#ProgressCurrent { color: %(TEXT_DIM)s; font-size: 11px; background: transparent; }
#LogTitle {
  color: #cad3b7; font-size: 12px; font-weight: 700;
  letter-spacing: 0.8px; background: transparent;
}
QProgressBar#DownloadProgress {
  background: #090b07; border: 1px solid #40502e; border-radius: 10px;
  padding: 3px; min-height: 25px; max-height: 25px;
  color: #f1f6e4; font-size: 11px; font-weight: 700; text-align: center;
}
QProgressBar#DownloadProgress::chunk {
  border-radius: 7px;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                              stop:0 #718632, stop:0.55 #9dbb48, stop:1 #d2e982);
}

/* ---- 滚动条 ---- */
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical {
  background: transparent; width: 14px; border: none; margin: 3px 2px;
}
QScrollBar::handle:vertical {
  background: #3d472f; border-radius: 5px; min-height: 34px;
}
QScrollBar::handle:vertical:hover { background: #52633c; }
QScrollBar:horizontal {
  background: transparent; height: 14px; border: none; margin: 2px 3px;
}
QScrollBar::handle:horizontal {
  background: #3d472f; border-radius: 5px; min-width: 34px;
}
QScrollBar::handle:horizontal:hover { background: #52633c; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---- 状态栏 / 文本 ---- */
#StatusBar {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #151910, stop:1 #10130d);
  border: none; border-top: 1px solid #2d3327;
  border-bottom-left-radius: 15px; border-bottom-right-radius: 15px;
}
#StatusBar[windowMaximized="true"] { border-radius: 0; }
#StatusBar QLabel {
  background: transparent; color: %(TEXT_DIM)s; font-size: 10px;
  letter-spacing: 0.3px;
}
QPlainTextEdit, QTextEdit {
  background: %(PANEL2)s; border: 1px solid %(BORDER)s;
  border-radius: 9px; color: %(TEXT)s;
  font-family: "Cascadia Mono", "Microsoft YaHei UI"; font-size: 12px;
}
QPlainTextEdit#TaskLog {
  background: #090b07; border: 1px solid #2c3324;
  border-left: 2px solid #52642f; border-radius: 9px;
  padding: 7px 9px; color: #aeb89a;
  selection-background-color: #3d4c21; selection-color: #eff5df;
}
QPlainTextEdit#LinkInput {
  background: #0a0d08; border: 1px solid #39432d; border-radius: 12px;
  padding: 10px 12px; color: #cbd3bb;
  selection-background-color: #3d4c21; selection-color: #eff5df;
}
QPlainTextEdit#LinkInput:hover { border-color: #4b5938; }
QPlainTextEdit#LinkInput:focus { border-color: %(GREEN)s; }
QPlainTextEdit#LinkInput QWidget { background: transparent; border: none; }
QTreeWidget, QTableWidget {
  background: #12150e; border: 1px solid %(BORDER)s;
  border-radius: 9px; gridline-color: #242a1e;
}
QTreeWidget::item { padding: 6px; border-radius: 6px; }
QTreeWidget::item:selected { background: %(GREEN_BG)s; color: %(GREEN_L)s; }
QHeaderView::section {
  background: #171b13; color: %(TEXT_DIM)s; border: none;
  border-bottom: 1px solid %(BORDER)s; padding: 6px;
}
QLabel#DlgTitle {
  color: %(GREEN_L)s; font-size: 17px; font-weight: 700; letter-spacing: 1px;
}
QLabel#Hint { color: %(TEXT_DIM)s; font-size: 11px; }

/* ---- 消息框 ---- */
QLabel#MessageIcon { border-radius: 12px; font-size: 20px; font-weight: 700; }
QLabel#MessageIcon[tone="question"] {
  background: #25301a; border: 1px solid #52643a; color: %(GREEN_L)s;
}
QLabel#MessageIcon[tone="information"] {
  background: #1d2a2f; border: 1px solid #3f6570; color: #9ad3df;
}
QLabel#MessageIcon[tone="warning"] {
  background: #302615; border: 1px solid #6c5525; color: #e2bb69;
}
QLabel#MessageIcon[tone="critical"] {
  background: #331711; border: 1px solid #713629; color: #ff9c84;
}
QLabel#MessageIcon[tone="neutral"] {
  background: #20251b; border: 1px solid %(BORDER_L)s; color: %(TEXT_DIM)s;
}
QLabel#MessageTitle {
  color: #edf1e3; font-size: 16px; font-weight: 700; letter-spacing: 0.5px;
}
QLabel#MessageText { color: #bcc4ad; font-size: 12px; }

/* ---- 压缩包导入向导 ---- */
QFrame#ArchiveDropZone {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                              stop:0 #181d13, stop:1 #10130d);
  border: 1px dashed #4d5d36; border-radius: 12px;
}
QFrame#ArchiveDropZone:hover { background: #1b2116; border-color: %(GREEN)s; }
QFrame#ArchiveDropZone[dragActive="true"] {
  background: #222b17; border: 1px solid %(GREEN)s;
}
QLabel#ImportDropIcon {
  background: %(GREEN_BG)s; color: %(GREEN_L)s; border: 1px solid #52663a;
  border-radius: 24px; font-size: 26px; font-weight: normal;
}
QLabel#ImportDropTitle {
  color: #e5ead9; font-size: 14px; font-weight: 700; background: transparent;
}
QLabel#ImportDropHint {
  color: %(TEXT_DIM)s; font-size: 11px; background: transparent;
}
QFrame#ImportStatusPanel {
  background: #151a11; border: 1px solid #323a2a; border-radius: 10px;
}
QLabel#ImportStatus {
  color: #dce4c8; font-size: 12px; font-weight: 700; background: transparent;
}
QProgressBar#ImportProgress {
  background: #090b07; border: 1px solid #3a4629; border-radius: 4px;
  min-height: 7px; max-height: 7px; padding: 1px;
}
QProgressBar#ImportProgress::chunk { background: %(GREEN)s; border-radius: 3px; }
QLabel#ImportResultTitle {
  color: #e1e7d3; font-size: 13px; font-weight: 700; letter-spacing: 0.7px;
}
QScrollArea#ImportResultsScroll { background: transparent; border: none; }
QWidget#ImportResultsHost { background: transparent; }
QLabel#ImportEmpty {
  color: %(TEXT_DIM)s; background: #12150e; border: 1px solid #293022;
  border-radius: 10px; font-size: 12px;
}
QFrame#ImportCandidate {
  background: #171b12; border: 1px solid #2d3426; border-radius: 10px;
}
QFrame#ImportCandidate:hover { background: #1c2117; border-color: #52643a; }
QFrame#ImportCandidate[duplicate="true"] {
  background: #11140e; border-color: #252b20;
}
QFrame#ImportCandidate QLabel { background: transparent; }
QCheckBox#ImportSelect::indicator {
  width: 18px; height: 18px; border-radius: 5px;
  background: #0b0e07; border: 1px solid #5a6d3e;
}
QCheckBox#ImportSelect::indicator:hover { border-color: %(GREEN_L)s; }
QCheckBox#ImportSelect::indicator:checked {
  background: %(GREEN)s; border: 1px solid %(GREEN_L)s;
}
QCheckBox#ImportSelect::indicator:disabled {
  background: #151811; border-color: #303725;
}
QLabel#ImportThumb {
  background: #0b0e07; border: 1px solid #303725; border-radius: 7px;
}
QLabel#ImportCandidateTitle {
  color: #e7ecd9; font-size: 13px; font-weight: 700;
}
QLabel#ImportCandidateMeta { color: #aeb8a0; font-size: 11px; }
QLabel#ImportCandidateSource { color: %(TEXT_DIM)s; font-size: 10px; }
QLabel#ImportReady {
  color: %(GREEN_L)s; background: %(GREEN_BG)s; border: 1px solid #4b6030;
  border-radius: 6px; padding: 3px 8px; font-size: 10px;
}
QLabel#ImportDuplicate {
  color: #c79780; background: #24150f; border: 1px solid #583025;
  border-radius: 6px; padding: 3px 8px; font-size: 10px;
}

/* ---- 工坊结果行 ---- */
QFrame#WorkshopInputPanel {
  background: #141810; border: 1px solid #30382a; border-radius: 12px;
}
QLabel#WorkshopSectionTitle {
  color: #e3e9d5; font-size: 13px; font-weight: 700; letter-spacing: 0.4px;
}
QListWidget#WorkshopLinkList {
  background: #0e110b; border: 1px solid #30382a; border-radius: 12px;
  padding: 5px;
}
QFrame#WorkshopResult {
  background: #161a12; border: 1px solid #2b3224; border-radius: 10px;
}
QFrame#WorkshopResult:hover { background: #1b2117; border-color: #4d5e37; }
QFrame#WorkshopResult QWidget, QFrame#WorkshopResult QLabel {
  background: transparent;
}

/* ---- 设置页 ---- */
#SettingsPage { background: transparent; }
#SettingsPage QLabel { background: transparent; }
#SettingsSection {
  color: %(TEXT)s; font-size: 14px; font-weight: 700;
  letter-spacing: 1px; background: transparent; padding-top: 3px;
}
#SettingsCard {
  background: #151911; border: 1px solid #2c3326; border-radius: 11px;
}
#SettingsCard:hover { border-color: #4a5935; background: #181d14; }
#SettingsTitle { color: #e1e6d4; font-weight: 700; font-size: 13px; }
#SettingsSub { color: %(TEXT_DIM)s; font-size: 11px; }
QWidget#SettingsActionHost { background: transparent; border: none; }
"""


def apply_qss(app):
    app.setStyleSheet(QSS % {
        "BG": BG, "PANEL": PANEL, "PANEL2": PANEL2, "BORDER": BORDER,
        "BORDER_L": BORDER_L, "TEXT": TEXT, "TEXT_DIM": TEXT_DIM,
        "GREEN": GREEN, "GREEN_L": GREEN_L, "GREEN_BG": GREEN_BG,
        "RED": RED, "RED_L": RED_L, "ROW_HOVER": ROW_HOVER,
        "ARROW": icon_path("chevron_down.svg").replace("\\", "/"),
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
