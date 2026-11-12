# -*- coding: utf-8 -*-
"""主窗口：标题栏 + 分类栏 + 物品栏 + 卡片网格 + 状态栏。"""
import base64
import os
import time

from PySide6.QtCore import (
    QAbstractAnimation, QByteArray, QEasingCurve, QEvent, QPoint, QPropertyAnimation,
    QRect, QSize, Qt, QTimer, Signal, Property,
)
from PySide6.QtGui import QColor, QPainter, QPen, QFontMetrics, QIcon, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QGraphicsOpacityEffect, QHBoxLayout, QLabel, QInputDialog, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QPushButton, QScrollArea, QComboBox,
    QSizePolicy, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

from ..core import game as gamemod
from ..core import paths as pathsmod
from ..core import steam_api
from ..core import app_paths
from ..core.classify import CATEGORIES
from ..core.library import Library
from ..core.paths import GamePaths
from ..core.store import Store, mod_name_sort_key
from . import theme, util
from .dialogs import (
    CategoryDialog, DetailDialog, ImportArchiveDialog,
    WorkshopDialog,
)
from .components import (
    AppDialog, AppMessageBox as QMessageBox, fade_in_window, motion_enabled,
)
from .workers import DetailsWorker, DownloadWorker, ScanWorker, UpdateCheckWorker

APP_TITLE = "L4D2 MOD 军械库"
APP_VERSION = "1.0"
# 项目仓库主页（设置页展示为超链接，检查更新基于它的 releases/latest）
REPO_URL = "https://github.com/PolysaCHride/l4d2-mod-manager"
CARD_W, CARD_H = 230, 234
THUMB_W, THUMB_H = 208, 122
GRID_MIN_GAP = 10

# 单击卡片即启用切换（同物品互斥）的类别
MUTEX_CATS = {"角色", "特感", "枪械", "近战", "医疗品", "投掷"}


class TitleBar(QWidget):
    """品牌标题区 + 贴边的 Windows 风格窗口按钮。"""

    def __init__(self, window):
        super().__init__(window)
        self._win = window   # 注意：不能用 self.window，会遮蔽 QWidget.window() 方法
        self.setObjectName("TitleBar")
        self.setFixedHeight(52)
        self._drag = None

        h = QHBoxLayout(self)
        h.setContentsMargins(16, 0, 0, 0)
        h.setSpacing(0)

        self.icon_lab = QLabel()
        self.icon_lab.setObjectName("TitleIcon")
        self.icon_lab.setFixedSize(30, 30)
        self.icon_lab.setAlignment(Qt.AlignCenter)
        icon_pm = QPixmap(theme.icon_path("icon_32.png"))
        if not icon_pm.isNull():
            self.icon_lab.setPixmap(icon_pm.scaled(
                20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.title = QLabel(APP_TITLE)
        self.title.setObjectName("AppTitle")
        h.addWidget(self.icon_lab)
        h.addSpacing(10)
        h.addWidget(self.title)
        h.addStretch(1)

        self._caption_controls = QWidget(self)
        self._caption_controls.setObjectName("CaptionControls")
        captions = QHBoxLayout(self._caption_controls)
        captions.setContentsMargins(0, 0, 0, 0)
        captions.setSpacing(0)

        self.btn_min = QPushButton()
        self.btn_max = QPushButton()
        self.btn_close = QPushButton()
        self.btn_close.setObjectName("btnClose")
        for b, kind, fn in ((self.btn_min, "min", self._min),
                            (self.btn_max, "max", self._max),
                            (self.btn_close, "close", self._close)):
            b.setProperty("role", "window")
            b.setFocusPolicy(Qt.NoFocus)
            b.setFixedSize(46, 32)
            b.setIcon(theme.caption_icon(kind))
            b.setIconSize(QSize(14, 14))
            b.clicked.connect(fn)
            captions.addWidget(b)
        h.addWidget(self._caption_controls, 0, Qt.AlignTop)

    # --- 拖拽 ---
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            gp = e.globalPosition().toPoint()
            f = self._win.frameGeometry()
            # 靠近窗口边缘 8px 内交给边缘缩放处理
            if (gp.x() - f.left() <= 8 or f.right() - gp.x() <= 8
                    or gp.y() - f.top() <= 8):
                return
            self._drag = gp - f.topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def mouseDoubleClickEvent(self, _e):
        self._max()

    def _min(self):
        self._win.showMinimized()

    def _max(self):
        if hasattr(self._win, "_toggle_maximized"):
            self._win._toggle_maximized()
        elif self._win.isMaximized():
            self._win.showNormal()
        else:
            self._win.showMaximized()

    def _close(self):
        self._win.close()


class CheckCircle(QWidget):
    """带平滑填充过渡的启用指示器。"""

    toggled = Signal(bool)

    def __init__(self, checked=False, size=20, parent=None):
        super().__init__(parent)
        self._checked = bool(checked)
        self._progress = 1.0 if checked else 0.0
        self._hover = False
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("启用 / 禁用")
        self._animation = QPropertyAnimation(self, b"checkProgress", self)
        self._animation.setDuration(190)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != bool(checked):
            self._checked = bool(checked)
            self._animate_to(1.0 if self._checked else 0.0)

    @Property(float)
    def checkProgress(self):
        return self._progress

    @checkProgress.setter
    def checkProgress(self, value):
        self._progress = max(0.0, min(1.0, float(value)))
        self.update()

    def _animate_to(self, value):
        self._animation.stop()
        if not motion_enabled():
            self.checkProgress = value
            return
        self._animation.setStartValue(self._progress)
        self._animation.setEndValue(value)
        self._animation.start()

    def sizeHint(self):
        return QSize(self._size, self._size)

    def enterEvent(self, _e):
        self._hover = True
        self.update()

    def leaveEvent(self, _e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._checked = not self._checked
            self._animate_to(1.0 if self._checked else 0.0)
            self.toggled.emit(self._checked)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        progress = self._progress
        ring = QColor(theme.BORDER_L)
        if self._hover:
            ring = QColor(theme.GREEN)
        fill = QColor(theme.GREEN)
        fill.setAlpha(int(38 + 207 * progress))
        pen = QPen(ring)
        pen.setWidthF(1.5 + 0.3 * progress)
        p.setPen(pen)
        p.setBrush(fill if progress > 0 else QColor("#0c0e07"))
        p.drawEllipse(1, 1, self._size - 2, self._size - 2)
        if progress > 0.01:
            check = QPen(QColor(theme.PANEL2))
            check.setWidthF(2.0)
            check.setCapStyle(Qt.RoundCap)
            check.setJoinStyle(Qt.RoundJoin)
            check.setColor(QColor(20, 24, 14, int(255 * progress)))
            p.setPen(check)
            s = self._size
            p.drawLine(QPoint(int(s * 0.28), int(s * 0.52)),
                       QPoint(int(s * 0.44), int(s * 0.68)))
            p.drawLine(QPoint(int(s * 0.44), int(s * 0.68)),
                       QPoint(int(s * 0.73), int(s * 0.34)))
        p.end()


class ModCard(QFrame):
    def __init__(self, main, rec):
        super().__init__()
        self.main = main
        self.rec = rec
        self.setObjectName("ModCard")
        self.setFixedSize(CARD_W, CARD_H)
        self._updating = False
        self._hover_progress = 0.0
        self.setAttribute(Qt.WA_Hover, True)
        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(150)
        self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)

        v = QVBoxLayout(self)
        v.setContentsMargins(9, 9, 9, 8)
        v.setSpacing(4)
        self.thumb = QLabel()
        self.thumb.setObjectName("CardThumb")
        self.thumb.setFixedSize(THUMB_W, THUMB_H)
        self.thumb.setAlignment(Qt.AlignCenter)
        v.addWidget(self.thumb)

        fm = QFontMetrics(self.font())
        self.title = QLabel(util.elide(rec.get("alias") or rec.get("title") or rec["file"], THUMB_W - 4, fm))
        self.title.setObjectName("CardTitle")
        self.title.setToolTip(rec.get("title") or rec["file"])
        self.alias = QLabel(("别名：%s" % rec["alias"]) if rec.get("alias") else
                            (rec.get("category", "") + ((" · " + rec["item"]) if rec.get("item") else "")))
        self.alias.setObjectName("CardAlias")
        self.meta = QLabel("%s · %s" % (util.fmt_size(rec.get("size", 0)), util.fmt_time(rec.get("added_at"))))
        self.meta.setObjectName("CardMeta")

        row = QHBoxLayout()
        self.switch = CheckCircle(bool(rec.get("enabled")), size=20)
        self.btn_del = QPushButton()
        self.btn_del.setProperty("accent", "danger")
        self.btn_del.setFixedSize(30, 22)
        self.btn_del.setIcon(QIcon(theme.trash_pixmap(14)))
        self.btn_del.setIconSize(QSize(14, 14))
        self.btn_del.setToolTip("移入回收站（data/trash）")
        self.btn_del.clicked.connect(lambda: self.main.delete_mod_flow(self.rec["file"]))
        row.addWidget(self.switch)
        row.addStretch(1)
        row.addWidget(self.btn_del)
        v.addWidget(self.title)
        v.addWidget(self.alias)
        v.addWidget(self.meta)
        v.addLayout(row)

        self.setCursor(Qt.PointingHandCursor)
        self.switch.toggled.connect(self._on_toggle)
        self._apply_state()

    @Property(float)
    def hoverProgress(self):
        return self._hover_progress

    @hoverProgress.setter
    def hoverProgress(self, value):
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    def _animate_hover(self, target):
        self._hover_animation.stop()
        if not motion_enabled():
            self.hoverProgress = target
            return
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def enterEvent(self, event):
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._hover_progress <= 0.01:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        border = QColor(theme.GREEN)
        border.setAlpha(int(60 + 125 * self._hover_progress))
        pen = QPen(border)
        pen.setWidthF(1.0 + self._hover_progress * 0.35)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)
        p.end()

    def _apply_state(self):
        on = bool(self.rec.get("enabled"))
        new_state = "on" if on else "off"
        if self.property("state") != new_state:
            self.setProperty("state", new_state)
            self.style().unpolish(self)
            self.style().polish(self)
        self.thumb.setPixmap(util.load_thumb(
            self.rec.get("preview") or "", THUMB_W - 2, THUMB_H - 2,
            self.rec.get("category", "未分类"), item=self.rec.get("item") or "",
            radius=9))

    def refresh_record(self, rec):
        self.rec = rec
        self._updating = True
        self.switch.setChecked(bool(rec.get("enabled")))
        self._updating = False
        fm = QFontMetrics(self.font())
        self.title.setText(util.elide(rec.get("alias") or rec.get("title") or rec["file"], THUMB_W - 4, fm))
        self.alias.setText(("别名：%s" % rec["alias"]) if rec.get("alias") else
                           (rec.get("category", "") + ((" · " + rec["item"]) if rec.get("item") else "")))
        self.meta.setText("%s · %s" % (util.fmt_size(rec.get("size", 0)), util.fmt_time(rec.get("added_at"))))
        self._apply_state()

    def _on_toggle(self, checked):
        if self._updating:
            return
        self.main.toggle_mod(self.rec["file"], checked)

    def mousePressEvent(self, e):
        # 互斥类别：单击卡片直接启用（快速切换，同物品其余自动禁用）
        if e.button() == Qt.LeftButton and self.rec.get("category") in MUTEX_CATS:
            if not self.rec.get("enabled"):
                self.main.toggle_mod(self.rec["file"], True)
            return
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self.switch.toggle()

    def contextMenuEvent(self, e):
        self.main.show_card_menu(self, e.globalPos())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setObjectName("AppWindow")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(theme.icon_path()))
        self.resize(1320, 820)
        self.setMinimumSize(1100, 700)
        self._intro_shown = False
        self._page_animation = None

        self.store = Store(self._data_dir())
        steam_api.set_proxy(self.store.settings().get("proxy", ""))
        self.paths = None
        self.library = None
        self._scan_worker = None
        self._rescan_pending = False
        self._dl_worker = None
        self._assign_worker = None
        self._update_worker = None
        self._current_top = "全部"      # 一级：全部/角色/枪械/地图/其他
        self._current_category = "全部"  # 实际过滤类别（其他 → 由二级栏决定）
        self._current_kind = "all"      # 三级面板选中类型：all / item / collection
        self._current_item = None
        self._current_collection = None
        self._cards = {}   # file -> ModCard（diff 复用，避免全量重建卡顿）
        self._resizing = False
        self._resize_dir = 0
        self._resize_origin = QPoint()
        self._resize_geom = QRect()
        self._edge_hover = False
        self._grid_order = []
        self._grid_columns = 0
        self._grid_gap = float(GRID_MIN_GAP)
        self._grid_target_gap = GRID_MIN_GAP
        self._grid_applied_gap = GRID_MIN_GAP
        self._grid_animation_timer = QTimer(self)
        self._grid_animation_timer.setInterval(16)
        self._grid_animation_timer.timeout.connect(self._step_cards_animation)

        self._build_ui()
        self._build_shortcuts()
        self._restore_layout()
        QApplication.instance().installEventFilter(self)
        self.apply_game_dir(first=True)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_game_status)
        self._status_timer.start(5000)
        self._update_game_status()

        # 自动监视：addons 顶层 / addonlist 有变化时自动重扫（拾取新下载的 mod）
        self._watch_snapshot = None
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(4000)
        self._watch_timer.timeout.connect(self._watch_dirs)
        self._watch_timer.start()

    # ---------- 路径 ----------
    def _data_dir(self):
        return app_paths.data_dir()

    def apply_game_dir(self, first=False):
        gd = self.store.settings().get("game_dir", "")
        if not pathsmod.is_game_dir(gd):
            gd = pathsmod.find_game_dir()
            if gd:
                self.store.set_setting("game_dir", gd)
        if pathsmod.is_game_dir(gd):
            self.paths = GamePaths(gd)
            self.library = Library(self.store, self.paths)
            self.path_label.setText("库 " + self.paths.addons_dir)
        else:
            self.paths = None
            self.library = None
            self.path_label.setText("未找到游戏目录，请到 设置 中指定")
            if first:
                self.show_settings()
        self.start_rescan()

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("WindowCanvas")
        self._window_layout = QVBoxLayout(central)
        # 可见边框必须贴住窗口矩形；在边框外额外留透明投影区会让
        # DWM 的实际窗口边界与用户看到的边框错位，缩放热区也无法对齐。
        self._window_layout.setContentsMargins(0, 0, 0, 0)
        self._window_layout.setSpacing(0)

        self.surface = QFrame()
        self.surface.setObjectName("AppSurface")
        self._window_layout.addWidget(self.surface)

        root = QVBoxLayout(self.surface)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.titlebar = TitleBar(self)
        root.addWidget(self.titlebar)

        hazard = QLabel()
        hazard.setObjectName("HazardDivider")
        hazard.setFixedHeight(4)
        hazard.setPixmap(theme.hazard_pixmap(1600, 4))
        hazard.setScaledContents(True)
        root.addWidget(hazard)

        body = QWidget()
        body.setObjectName("WindowBody")
        outer = QVBoxLayout(body)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        root.addWidget(body, 1)

        # 一级导航栏常驻左侧；右侧为页面堆栈（mod 浏览 / 设置）
        content = QHBoxLayout()
        content.setContentsMargins(10, 10, 10, 10)
        content.setSpacing(8)
        outer.addLayout(content, 1)

        # ---- 分类栏：角色/枪械/地图 一级，其余收进「其他」二级 ----
        rail = QWidget()
        rail.setObjectName("Rail")
        rail.setFixedWidth(78)
        rv = QVBoxLayout(rail)
        rv.setContentsMargins(7, 14, 7, 12)
        rv.setSpacing(6)
        self.rail_buttons = {}
        for c in ("全部", "角色", "武器", "地图", "其他"):
            b = QPushButton(c)
            b.setObjectName("RailButton")
            b.setCheckable(True)
            b.setFixedHeight(44)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, cat=c: self.select_category(cat))
            rv.addWidget(b)
            self.rail_buttons[c] = b
        rv.addStretch(1)
        b_adopt = QPushButton("一键\n管理")
        b_adopt.setObjectName("RailUtility")
        b_adopt.setFixedHeight(48)
        b_adopt.setToolTip("把所有 mod 纳入管理：workshop 订阅全部移出并前移一级、\n"
                           "子目录 vpk 收拢、未登记的顶层 mod 补记。\n"
                           "冲突外观组按名称只启用一个（完成后提示退订）")
        b_adopt.clicked.connect(self.adopt_all_flow)
        self.btn_settings_nav = QPushButton("设置")
        self.btn_settings_nav.setObjectName("RailButton")
        self.btn_settings_nav.setCheckable(True)
        self.btn_settings_nav.setFixedHeight(44)
        self.btn_settings_nav.setCursor(Qt.PointingHandCursor)
        self.btn_settings_nav.clicked.connect(self.show_settings)
        rv.addWidget(b_adopt)
        rv.addWidget(self.btn_settings_nav)
        content.addWidget(rail)

        # 右侧页面堆栈：page0 = 三栏浏览器，page1 = 设置页
        self.stack = QStackedWidget()
        self.stack.setObjectName("PageStack")
        content.addWidget(self.stack, 1)

        # 三栏改用 QSplitter：边界可拖拽调宽
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("WorkspaceSplitter")
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)

        # ---- 二级分类栏（仅「其他」时向右展开） ----
        catpane = QWidget()
        catpane.setObjectName("SidePane")
        catpane.setMinimumWidth(150)
        cv = QVBoxLayout(catpane)
        cv.setContentsMargins(12, 14, 12, 12)
        cv.setSpacing(8)
        self.cat_title = QLabel("其他")
        self.cat_title.setObjectName("PaneTitle")
        cv.addWidget(self.cat_title)
        self.cat_list = QListWidget()
        self.cat_list.currentRowChanged.connect(self._on_sub_selected)
        cv.addWidget(self.cat_list, 1)
        catpane.setVisible(False)
        self.catpane = catpane
        self.splitter.addWidget(catpane)

        # ---- 物品栏 ----
        itempane = QWidget()
        itempane.setObjectName("SidePane")
        itempane.setMinimumWidth(150)
        iv = QVBoxLayout(itempane)
        iv.setContentsMargins(12, 14, 12, 12)
        iv.setSpacing(8)
        self.item_title = QLabel("物品")
        self.item_title.setObjectName("PaneTitle")
        iv.addWidget(self.item_title)
        self.item_list = QListWidget()
        self.item_list.currentRowChanged.connect(self._on_item_selected)
        self.item_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self._item_menu)
        iv.addWidget(self.item_list, 1)
        self.splitter.addWidget(itempane)

        # ---- 主区 ----
        mainpane = QWidget()
        mainpane.setObjectName("BrowserPane")
        mv = QVBoxLayout(mainpane)
        mv.setContentsMargins(10, 10, 10, 10)
        mv.setSpacing(10)
        action_bar = QFrame()
        action_bar.setObjectName("ActionBar")
        bar = QHBoxLayout(action_bar)
        bar.setContentsMargins(9, 9, 9, 9)
        bar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setObjectName("SearchField")
        self.search.setMinimumHeight(36)
        self.search.setPlaceholderText("搜索名称、别名、标签、物品…")
        self.search.setToolTip("在当前分类 / 物品内搜索")
        # 输入防抖：停止输入 250ms 后再刷新，避免每个字符全量重排
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh_cards)
        self.search.textChanged.connect(lambda _s: self._search_timer.start())
        self.sort_combo = QComboBox()
        self.sort_combo.setMinimumHeight(36)
        self.sort_combo.setMinimumWidth(112)
        self.sort_combo.addItems(["名称", "最近添加", "大小", "启用优先"])
        self.sort_combo.currentIndexChanged.connect(lambda _i: self.refresh_cards())
        b_refresh = QPushButton("刷新")
        b_refresh.setObjectName("ToolButton")
        b_refresh.setMinimumHeight(36)
        b_refresh.setToolTip("重新扫描 addons 顶层：拾取手动放入的新 mod、\n"
                             "同步游戏内菜单的启用/禁用改动（快捷键 F5）\n"
                             "Steam 新订阅在 addons/workshop，请用左侧「一键管理」纳管")
        b_refresh.clicked.connect(self.start_rescan)
        b_import = QPushButton("导入压缩包")
        b_import.setObjectName("ToolButton")
        b_import.setMinimumHeight(36)
        b_import.clicked.connect(self.do_import)
        b_ws = QPushButton("工坊下载")
        b_ws.setObjectName("ToolButton")
        b_ws.setMinimumHeight(36)
        b_ws.clicked.connect(self.open_workshop)
        b_launch = QPushButton("▶ 启动游戏")
        b_launch.setObjectName("LaunchButton")
        b_launch.setMinimumHeight(36)
        b_launch.setProperty("accent", "primary")
        b_launch.clicked.connect(self.launch_game)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.sort_combo)
        bar.addWidget(b_refresh)
        bar.addWidget(b_import)
        bar.addWidget(b_ws)
        bar.addWidget(b_launch)
        mv.addWidget(action_bar)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("CardScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        grid_host = QWidget()
        self.grid = QGridLayout(grid_host)
        self.grid.setContentsMargins(
            GRID_MIN_GAP, GRID_MIN_GAP, GRID_MIN_GAP, GRID_MIN_GAP)
        self.grid.setSpacing(GRID_MIN_GAP)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll.setWidget(grid_host)
        mv.addWidget(self.scroll, 1)
        mainpane.setMinimumWidth(420)
        self.splitter.addWidget(mainpane)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setSizes([190, 150, 940])
        self.splitter.splitterMoved.connect(self._update_cards_layout)
        self.stack.addWidget(self.splitter)

        # page1：设置页
        self.stack.addWidget(self._build_settings_page())

        # ---- 状态栏 ----
        status = QWidget()
        status.setObjectName("StatusBar")
        status.setFixedHeight(34)
        self.status_bar = status
        sh = QHBoxLayout(status)
        sh.setContentsMargins(16, 0, 16, 0)
        self.game_label = QLabel("● 检测中")
        self.count_label = QLabel("")
        self.path_label = QLabel("")
        sh.addWidget(self.game_label)
        sh.addWidget(self.count_label)
        sh.addStretch(1)
        sh.addWidget(self.path_label)
        root.addWidget(status)

        self.setCentralWidget(central)

    def _build_shortcuts(self):
        s1 = QShortcut("F5", self)
        s1.activated.connect(self.start_rescan)
        s2 = QShortcut("Ctrl+F", self)
        s2.activated.connect(self._focus_search)

    def _focus_search(self):
        self.search.setFocus()
        self.search.selectAll()

    # ---------- 布局记忆 ----------
    def _restore_layout(self):
        s = self.store.settings()
        geo = s.get("geometry_b64")
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode("ascii")))
            except Exception:
                pass
        sp = s.get("splitter_b64_v2")
        if sp:
            try:
                self.splitter.restoreState(QByteArray.fromBase64(sp.encode("ascii")))
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        if not self._intro_shown:
            self._intro_shown = True
            QTimer.singleShot(0, lambda: fade_in_window(self, duration=220, start_opacity=0.0))

    def _toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        QTimer.singleShot(0, self._sync_window_chrome)

    def _sync_window_chrome(self):
        if not hasattr(self, "surface"):
            return
        maximized = self.isMaximized()
        self._window_layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self.surface, self.titlebar, getattr(self, "status_bar", None)):
            if widget is None:
                continue
            widget.setProperty("windowMaximized", maximized)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.titlebar.btn_close.setProperty("windowMaximized", maximized)
        self.titlebar.btn_close.style().unpolish(self.titlebar.btn_close)
        self.titlebar.btn_close.style().polish(self.titlebar.btn_close)
        self.titlebar.btn_max.setIcon(theme.caption_icon(
            "restore" if maximized else "max"))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._sync_window_chrome()

    def _animate_page_switch(self):
        if not motion_enabled() or not hasattr(self, "stack"):
            return
        old_anim = getattr(self, "_page_animation", None)
        if old_anim is not None:
            old_anim.stop()
        effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(170)
        anim.setStartValue(0.35)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def cleanup():
            if self._page_animation is anim:
                self.stack.setGraphicsEffect(None)
                self._page_animation = None

        anim.finished.connect(cleanup)
        self._page_animation = anim
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    # ---------- 无边框窗口边缘缩放 ----------
    _EDGE = 8
    _CURSORS = {
        1: Qt.SizeHorCursor, 2: Qt.SizeHorCursor,
        4: Qt.SizeVerCursor, 8: Qt.SizeVerCursor,
        5: Qt.SizeFDiagCursor, 10: Qt.SizeFDiagCursor,
        6: Qt.SizeBDiagCursor, 9: Qt.SizeBDiagCursor,
    }

    def _edges_at(self, gp):
        if self.isMaximized() or QApplication.activeWindow() is not self:
            return 0
        # 用窗口自身坐标计算，和 QSS 绘制出来的可见边框使用同一矩形。
        # frameGeometry() 在 Windows 无边框/透明窗口上可能包含不可见边缘，
        # 正是它导致了“看得到边框，却拖不到”的问题。
        p = self.mapFromGlobal(gp)
        if not self.rect().contains(p):
            return 0
        left = p.x() < self._EDGE
        right = self.rect().right() - p.x() < self._EDGE
        top = p.y() < self._EDGE
        bottom = self.rect().bottom() - p.y() < self._EDGE
        v = 0
        if left:
            v |= 1
        if right:
            v |= 2
        if top:
            v |= 4
        if bottom:
            v |= 8
        return v

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QEvent.MouseMove:
            gp = event.globalPosition().toPoint()
            if self._resizing:
                self._apply_resize(gp)
            else:
                e = self._edges_at(gp)
                if e:
                    self.setCursor(self._CURSORS.get(e, Qt.ArrowCursor))
                    self._edge_hover = True
                elif self._edge_hover:
                    self.setCursor(Qt.ArrowCursor)
                    self._edge_hover = False
        elif et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            gp = event.globalPosition().toPoint()
            e = self._edges_at(gp)
            if e:
                self._resizing = True
                self._resize_dir = e
                self._resize_origin = gp
                self._resize_geom = self.geometry()
        elif et == QEvent.MouseButtonRelease and self._resizing:
            self._resizing = False
            self._resize_dir = 0
        return super().eventFilter(obj, event)

    def _apply_resize(self, gp):
        d = self._resize_dir
        g = QRect(self._resize_geom)
        minw, minh = self.minimumWidth(), self.minimumHeight()
        dx = gp.x() - self._resize_origin.x()
        dy = gp.y() - self._resize_origin.y()
        if d & 1:
            g.setLeft(min(g.left() + dx, g.right() - minw))
        if d & 2:
            g.setRight(max(g.right() + dx, g.left() + minw))
        if d & 4:
            g.setTop(min(g.top() + dy, g.bottom() - minh))
        if d & 8:
            g.setBottom(max(g.bottom() + dy, g.top() + minh))
        self.setGeometry(g)

    # ---------- 数据刷新 ----------
    def start_rescan(self):
        if self.library is None:
            self._render_empty("未配置游戏目录")
            return
        if self._scan_worker is not None and self._scan_worker.isRunning():
            # 扫描进行中再点刷新：不并行开新线程（旧线程会被 GC 销毁导致闪退），
            # 只记一个待办，等当前扫描结束后补扫一次，确保期间新增的文件也被拾取。
            self._rescan_pending = True
            return
        self._rescan_pending = False
        self.count_label.setText("扫描中…")
        worker = ScanWorker(self.library)
        self._scan_worker = worker
        worker.progress.connect(
            lambda i, n, s: self.count_label.setText("扫描中 %d/%d" % (i, n)))
        worker.done.connect(self._on_scan_done)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(lambda w=worker: self._finish_scan_worker(w))
        worker.start()

    def _finish_scan_worker(self, worker):
        worker.deleteLater()
        if self._scan_worker is not worker:
            return  # 已被更新的扫描接替
        self._scan_worker = None
        if self._rescan_pending:
            self._rescan_pending = False
            QTimer.singleShot(0, self.start_rescan)

    def _release_worker(self, worker, attr):
        """一次性后台线程（识别/下载/导入/检查更新）结束后的兜底清理。

        运行中的 QThread 必须持有 Python 引用，否则被 GC 时会直接终止进程。
        """
        worker.deleteLater()
        if getattr(self, attr, None) is worker:
            setattr(self, attr, None)

    def _current_snapshot(self):
        """库目录快照：addons 顶层 vpk 文件名 + addonlist 修改时间。"""
        if self.library is None or self.paths is None:
            return None
        try:
            snap = set(self.library.list_addon_files())
        except OSError:
            return None
        try:
            st = os.stat(self.paths.addonlist_file)
            snap.add(("addonlist", st.st_mtime))
        except OSError:
            snap.add(("addonlist", -1))
        return snap

    def _refresh_snapshot(self):
        self._watch_snapshot = self._current_snapshot()

    def _watch_dirs(self):
        """自动监视：目录/addonlist 变化 → 自动重扫（无工作线程运行时）。"""
        if self.library is None or self.paths is None:
            return
        if self._scan_worker and self._scan_worker.isRunning():
            return
        snap = self._current_snapshot()
        if snap is None:
            return
        if self._watch_snapshot is None:
            self._watch_snapshot = snap
            return
        if snap != self._watch_snapshot:
            self._watch_snapshot = snap
            self.start_rescan()

    def _on_scan_done(self, stats):
        self._refresh_snapshot()
        self.refresh_items()
        self.refresh_cards()
        self.count_label.setText("共 %d 个 mod · 解析 %d" % (stats.get("total", 0), stats.get("parsed", 0)))

    def _on_scan_error(self, e):
        QMessageBox.warning(self, "扫描失败", e)
        self.count_label.setText("扫描失败")

    def refresh_all(self):
        """轻刷新：以 addonlist 校正状态 + 重建界面（不重新解析 vpk）。"""
        if self.library:
            try:
                self.library.sync_enabled_from_addonlist()
            except Exception:
                pass
        self._refresh_snapshot()
        self.refresh_items()
        self.refresh_cards()
        self._update_game_status()

    def refresh_items(self):
        self.item_list.blockSignals(True)
        self.item_list.clear()
        cat = self._current_category
        mods = list(self.store.mods().values())
        if cat not in ("全部", None):
            mods = [m for m in mods if m["category"] == cat]
        byfile = set(m["file"] for m in mods)
        entries = [("全部 (%d)" % len(mods), "all", None)]
        collection_file_sets = set()
        # 地图分类下：合集以文件夹形态展示
        if cat == "地图":
            for cid, info in self.store.collections().items():
                files = [f for f in info.get("files", []) if f in byfile]
                if files:
                    collection_file_sets.add(frozenset(files))
                    entries.append(("📁 %s (%d)" % (info.get("name", "合集"), len(files)),
                                    "collection", cid))
        item_files = {}
        for m in mods:
            item_files.setdefault(m.get("item", ""), set()).add(m["file"])
        ordered = sorted(item_files.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        if "" in item_files and frozenset(item_files[""]) not in collection_file_sets:
            entries.append(("未指定 / 多项 (%d)" % len(item_files[""]), "item", ""))
        for name, group_files in ordered:
            if name and frozenset(group_files) not in collection_file_sets:
                entries.append(("%s (%d)" % (name, len(group_files)), "item", name))
        self._item_entries = entries
        for label, _kind, _val in entries:
            QListWidgetItem(label, self.item_list)
        # 刷新不应把下钻视图跳回「全部」：尽量保留原选中项，不存在时回落到第一行
        want = None
        if self._current_kind == "collection":
            want = ("collection", self._current_collection)
        elif self._current_kind == "item":
            want = ("item", self._current_item)
        row = 0
        if want is not None:
            for i, (_label, kind, val) in enumerate(entries):
                if (kind, val) == want:
                    row = i
                    break
        self.item_list.setCurrentRow(row)
        self.item_list.blockSignals(False)
        # 信号被屏蔽期间手动同步选中状态（不触发 refresh_cards，由调用方统一刷新）
        self._apply_item_selection(row)

    def _apply_item_selection(self, row):
        """同步三级面板选中状态到过滤变量与标题（不刷新卡片）。"""
        e = getattr(self, "_item_entries", [])
        if 0 <= row < len(e):
            _label, kind, val = e[row]
            self._current_kind = kind
            self._current_item = val if kind == "item" else None
            self._current_collection = val if kind == "collection" else None
            if kind == "collection":
                info = self.store.get_collection(val) or {}
                self.item_title.setText("📁 %s" % info.get("name", "合集"))
            else:
                self.item_title.setText(self._current_category)
        else:
            self._current_kind = "all"
            self._current_item = None
            self._current_collection = None

    def _on_item_selected(self, row):
        self._apply_item_selection(row)
        self.refresh_cards()

    def _item_menu(self, pos):
        row = self.item_list.currentRow()
        e = getattr(self, "_item_entries", [])
        if not (0 <= row < len(e)) or e[row][1] != "collection":
            return
        cid = e[row][2]
        menu = QMenu(self)
        a_del = menu.addAction("删除合集…")
        a_dissolve = menu.addAction("解散合集（保留部件）")
        a_rename = menu.addAction("重命名合集…")
        act = menu.exec(self.item_list.mapToGlobal(pos))
        if act == a_del:
            self.delete_collection_flow(cid)
        elif act == a_dissolve:
            self.dissolve_collection(cid)
        elif act == a_rename:
            self.rename_collection(cid)

    # ---------- 卡片 ----------
    def _sort_mods(self, mods):
        sort = self.sort_combo.currentIndex()
        if sort == 0:  # 名称
            mods.sort(key=mod_name_sort_key)
        elif sort == 1:  # 最近添加
            mods.sort(key=lambda m: -m.get("added_at", 0))
        elif sort == 2:  # 大小
            mods.sort(key=lambda m: -m.get("size", 0))
        else:  # 启用优先
            mods.sort(key=lambda m: (0 if m.get("enabled") else 1,
                                     m.get("category", ""), mod_name_sort_key(m)))
        return mods

    def _filtered_mods(self):
        mods = list(self.store.mods().values())
        q = self.search.text().strip().lower()
        if q:
            def match(m):
                hay = " ".join([
                    m.get("title", ""), m.get("alias", ""), m.get("category", ""),
                    m.get("item", ""), m.get("file", ""), " ".join(m.get("tags", [])),
                ]).lower()
                return q in hay
            mods = [m for m in mods if match(m)]
        cat = self._current_category
        if cat != "全部":
            mods = [m for m in mods if m["category"] == cat]
        if getattr(self, "_current_kind", "all") == "collection":
            cid = self._current_collection
            mods = [m for m in mods if m.get("collection") == cid]
            mods.sort(key=mod_name_sort_key)
            return mods
        if self._current_item is not None and self._current_item != "":
            mods = [m for m in mods if m.get("item") == self._current_item]
        elif self._current_item == "":
            mods = [m for m in mods if not m.get("item")]
        return self._sort_mods(mods)

    def refresh_cards(self):
        mods = self._filtered_mods()
        byfile = dict((m["file"], m) for m in mods)
        self._grid_animation_timer.stop()
        # 移除不再显示的卡片
        for f in list(self._cards.keys()):
            if f not in byfile:
                self._cards.pop(f).deleteLater()
        # 清空布局（不销毁 widget），复用/新建后重新排布
        while self.grid.count():
            self.grid.takeAt(0)
        cols, gap = self._grid_layout_metrics()
        self._grid_columns = cols
        self._grid_gap = float(gap)
        self._grid_target_gap = gap
        self._apply_grid_gap(gap)
        for m in mods:
            card = self._cards.get(m["file"])
            if card is None:
                card = ModCard(self, m)
                self._cards[m["file"]] = card
            else:
                card.refresh_record(m)
        self._grid_order = [m["file"] for m in mods]
        self._layout_cards()
        self._refresh_snapshot()
        self.count_label.setText("显示 %d / %d 个 mod" % (len(mods), len(self.store.mods())))

    def _layout_cards(self):
        """按当前列数重新排列已创建的卡片，不重建预览图。"""
        while self.grid.count():
            self.grid.takeAt(0)
        if not self._grid_columns:
            return
        for i, file_name in enumerate(self._grid_order):
            card = self._cards.get(file_name)
            if card is not None:
                self.grid.addWidget(
                    card, i // self._grid_columns, i % self._grid_columns)

    def _apply_grid_gap(self, gap):
        gap = int(gap)
        if gap == self._grid_applied_gap:
            return
        self._grid_applied_gap = gap
        self.grid.setContentsMargins(gap, gap, gap, gap)
        self.grid.setSpacing(gap)

    def _grid_layout_metrics(self):
        """计算列数和统一间距，为即将出现的纵向滚动条预留空间。"""
        width = self.scroll.viewport().width()
        vbar = self.scroll.verticalScrollBar()
        if vbar is not None and not vbar.isVisible():
            width -= max(vbar.sizeHint().width(), 14)
        cols = max(1, (width - GRID_MIN_GAP) // (CARD_W + GRID_MIN_GAP))
        gap = max(GRID_MIN_GAP, (width - cols * CARD_W) // (cols + 1))
        return cols, gap

    def _render_empty(self, text):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        lab = QLabel(text)
        lab.setObjectName("Hint")
        self.grid.addWidget(lab, 0, 0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_cards_layout()

    def _update_cards_layout(self, *_args):
        """窗口或分栏变化时更新目标间距；动画会在拖动过程中持续追踪。"""
        if not hasattr(self, "grid") or not self._grid_order:
            return
        cols, gap = self._grid_layout_metrics()
        if cols != self._grid_columns:
            self._grid_columns = cols
            self._layout_cards()
        self._grid_target_gap = gap
        if abs(self._grid_gap - gap) < 0.6:
            self._grid_gap = float(gap)
            self._apply_grid_gap(gap)
            self._grid_animation_timer.stop()
        elif not self._grid_animation_timer.isActive():
            self._grid_animation_timer.start()

    def _step_cards_animation(self):
        if not self._grid_order:
            self._grid_animation_timer.stop()
            return
        delta = self._grid_target_gap - self._grid_gap
        if abs(delta) < 0.6:
            self._grid_gap = float(self._grid_target_gap)
            self._apply_grid_gap(self._grid_target_gap)
            self._grid_animation_timer.stop()
            return
        self._grid_gap += delta * 0.3
        self._apply_grid_gap(round(self._grid_gap))

    # ---------- 操作 ----------
    # ---------- 三级面板导航：一级 rail → 二级分类栏（武器/其他）→ 三级物品栏 ----------
    # 「武器」分支：枪械 + 近战 + 医疗品 + 投掷
    WEAPON_BRANCH = ("枪械", "近战", "医疗品", "投掷")

    def _other_categories(self):
        return [c for c in CATEGORIES
                if c not in ("角色",) + self.WEAPON_BRANCH + ("地图",)]

    def _catpane_entries(self):
        if self._current_top == "武器":
            return list(self.WEAPON_BRANCH)
        return self._other_categories()

    def select_category(self, cat):
        """导航入口：一级类别直接选；子类别先展开所属分支再选。"""
        self.stack.setCurrentIndex(0)
        self._animate_page_switch()
        self.btn_settings_nav.setChecked(False)
        if cat in ("全部", "角色", "武器", "地图", "其他"):
            self._select_top(cat)
        elif cat in self.WEAPON_BRANCH:
            self._select_top("武器")
            self._select_sub(cat)
        else:
            self._select_top("其他")
            self._select_sub(cat)

    def _select_top(self, top):
        self._current_top = top
        for c, b in self.rail_buttons.items():
            b.setChecked(c == top)
        self.search.clear()
        if top in ("其他", "武器"):
            self.catpane.setVisible(True)
            self._adjust_splitter()
            self._sync_catpane()
            subs = self._catpane_entries()
            if self._current_category not in subs:
                self._select_sub(subs[0])
            else:
                self._sync_catpane_selection()
                self.refresh_items()
                self.refresh_cards()
        else:
            self.catpane.setVisible(False)
            self._adjust_splitter()
            self._current_category = top
            self.refresh_items()
            self.refresh_cards()

    def _select_sub(self, cat):
        self._current_category = cat
        self._sync_catpane_selection()
        self.refresh_items()
        self.refresh_cards()

    def _sync_catpane(self):
        counts = {}
        for m in self.store.mods().values():
            c = m.get("category", "未分类")
            counts[c] = counts.get(c, 0) + 1
        self._cat_entries = self._catpane_entries()
        self.cat_title.setText(self._current_top)
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        for cat in self._cat_entries:
            QListWidgetItem("%s (%d)" % (cat, counts.get(cat, 0)), self.cat_list)
        self.cat_list.blockSignals(False)

    def _sync_catpane_selection(self):
        rows = getattr(self, "_cat_entries", [])
        row = rows.index(self._current_category) if self._current_category in rows else 0
        self.cat_list.blockSignals(True)
        self.cat_list.setCurrentRow(row)
        self.cat_list.blockSignals(False)

    def _on_sub_selected(self, row):
        if 0 <= row < len(getattr(self, "_cat_entries", [])):
            self._select_sub(self._cat_entries[row])

    def _adjust_splitter(self):
        total = sum(self.splitter.sizes())
        if self.catpane.isVisible():
            self.splitter.setSizes([160, 150, max(420, total - 310)])
        else:
            self.splitter.setSizes([0, 150, max(420, total - 150)])

    def toggle_mod(self, file_name, enabled):
        if self.library is None:
            return
        if gamemod.is_l4d2_running():
            QMessageBox.warning(self, "游戏运行中", "游戏运行时无法修改 mod 配置，请先退出游戏")
            self.refresh_cards()
            return
        try:
            disabled = self.library.set_enabled(file_name, enabled)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "操作失败", str(e))
            self.refresh_cards()
            return
        self._refresh_snapshot()
        self.refresh_cards()
        if disabled:
            self.count_label.setText("已启用 %s（互斥禁用 %d 个同类）" % (file_name, len(disabled)))

    def adopt_all_flow(self):
        if self.library is None:
            QMessageBox.warning(self, "未配置", "请先在设置中指定游戏目录")
            return
        if not self.ensure_game_closed():
            return
        if QMessageBox.question(
                self, "一键纳入管理",
                "将递归扫描 addons 目录并把所有 vpk(mod文件) 加入到模组管理器中：\n\n"
                "· 登记addons中没有登记在模组管理器中的mod\n"
                "· 将workshop中的mod全部往外移至addons中，避免每次进入游戏需要验证mod文件 \n（建议移出mod文件后将模组取消订阅，避免重复下载）\n"
                "· 武器外观、人物外观类会冲突的mod默认只启用一个\n\n"
                "继续？") != QMessageBox.Yes:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            stats = self.library.adopt_all(progress=lambda *a: None)
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "纳入失败", str(e))
            return
        QApplication.restoreOverrideCursor()
        self.refresh_items()
        self.refresh_cards()
        self._refresh_snapshot()
        msg = "补记顶层 %d 个 · 子目录移入 %d 个 · workshop 迁移 %d 个" % (
            stats["adopted"], stats["moved"], stats["migrated"])
        if stats.get("auto_enabled") or stats.get("auto_disabled"):
            msg += "\n\n冲突处理：自动启用 %d 个，自动禁用 %d 个" % (
                stats["auto_enabled"], stats["auto_disabled"])
        if stats["conflicts"] or stats["errors"]:
            msg += "\n\n问题：\n" + "\n".join((stats["errors"] + stats["conflicts"])[:8])
        QMessageBox.information(self, "一键管理完成", msg)
        if stats.get("migrated_ids"):
            self._show_unsubscribe_dialog(stats["migrated_ids"])

    def _confirm_delete(self, title, text):
        """删除确认弹窗，支持勾选「今日不再提醒」。"""
        today = time.strftime("%Y-%m-%d")
        if self.store.settings().get("delete_warn_off_date") == today:
            return True
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        cb = QCheckBox("今日不再提醒")
        box.setCheckBox(cb)
        ok = box.exec() == QMessageBox.Yes
        if ok and cb.isChecked():
            self.store.set_setting("delete_warn_off_date", today)
        return ok

    def delete_mod_flow(self, file_name):
        if not self.ensure_game_closed():
            return
        rec = self.store.get_mod(file_name) or {}
        cid = rec.get("collection")
        info = self.store.get_collection(cid) if cid else None
        others = []
        if info:
            others = [f for f in info.get("files", [])
                      if f != file_name and self.store.get_mod(f)]
        if info and others:
            # 属于合集：询问是只删这一个还是删整个合集
            box = QMessageBox(self)
            box.setWindowTitle("删除 mod")
            box.setText("《%s》属于合集《%s》（共 %d 个部件）。\n要如何处理？"
                        % (rec.get("alias") or rec.get("title") or file_name,
                           info.get("name", "合集"), len(others) + 1))
            b_all = box.addButton("删除整个合集", QMessageBox.DestructiveRole)
            b_one = box.addButton("仅删除此 mod", QMessageBox.AcceptRole)
            box.addButton("取消", QMessageBox.RejectRole)
            box.setDefaultButton(b_one)
            box.exec()
            clicked = box.clickedButton()
            if clicked is b_all:
                self.delete_collection_flow(cid)
                return
            if clicked is not b_one:
                return
        if not self._confirm_delete("删除 mod", "将 %s 移入回收站（data/trash），确定？" % file_name):
            return
        try:
            self.library.delete_mod(file_name)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "删除失败", str(e))
            return
        self.refresh_items()
        self.refresh_cards()

    # ---------- 合集 ----------
    def _collection_files(self, cid):
        info = self.store.get_collection(cid) or {}
        return [f for f in info.get("files", []) if self.store.get_mod(f)]

    def delete_collection_flow(self, cid):
        info = self.store.get_collection(cid) or {}
        files = self._collection_files(cid)
        if not files:
            self.store.remove_collection(cid)
            self.store.save_library()
            return
        if not self.ensure_game_closed():
            return
        if not self._confirm_delete("删除合集",
                                    "将合集《%s》内 %d 个部件全部移入回收站（data/trash）？"
                                    % (info.get("name", "合集"), len(files))):
            return
        for f in files:
            try:
                self.library.delete_mod(f)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self, "删除失败", "%s: %s" % (f, e))
        self.store.remove_collection(cid)
        self.store.save_library()
        self.refresh_items()
        self.refresh_cards()

    def dissolve_collection(self, cid):
        for f in self._collection_files(cid):
            rec = self.store.get_mod(f)
            if rec:
                rec["collection"] = ""
        self.store.remove_collection(cid)
        self.store.save_library()
        self.refresh_items()
        self.refresh_cards()

    def rename_collection(self, cid):
        info = self.store.get_collection(cid) or {}
        text, ok = QInputDialog.getText(
            None, "重命名合集", "合集名称：", text=info.get("name", ""))
        if ok and text.strip():
            info["name"] = text.strip()
            self.store.upsert_collection(cid, info)
            self.store.save_library()
            self.refresh_items()

    def assign_collection_flow(self, rec):
        """把地图 mod 归入合集：粘贴合集链接自动识别，或选择已有合集。"""
        if rec.get("collection"):
            QMessageBox.information(self, "归入合集", "该 mod 已在合集《%s》中，如需更换请先移出。"
                                    % (self.store.get_collection(rec["collection"]) or {}).get("name", "?"))
            return
        if self._assign_worker is not None and self._assign_worker.isRunning():
            QMessageBox.information(self, "识别中", "正在识别上一个合集链接，请稍候")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("归入合集")
        dlg.setMinimumWidth(460)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("粘贴该地图**合集**的创意工坊链接或 ID，\n自动识别并把已在库的部件归入同一合集："))
        edit = QLineEdit()
        edit.setPlaceholderText("https://steamcommunity.com/sharedfiles/filedetails/?id=xxxxx")
        v.addWidget(edit)
        existing = sorted(self.store.collections().items(), key=lambda kv: kv[1].get("name", ""))
        combo = None
        if existing:
            v.addWidget(QLabel("或选择已有合集："))
            combo = QComboBox()
            combo.addItem("（粘贴链接新建 / 更新）", "")
            for cid, info in existing:
                combo.addItem("📁 %s" % info.get("name", cid), cid)
            v.addWidget(combo)
        btns = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setProperty("accent", "primary")
        cancel = QPushButton("取消")
        btns.addStretch(1)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel)
        v.addLayout(btns)
        result = {"mode": None}
        ok_btn.clicked.connect(lambda: result.update(mode=("existing" if (combo and combo.currentData()) else "link")))
        cancel.clicked.connect(dlg.reject)
        ok_btn.clicked.connect(dlg.accept)
        if dlg.exec() != QDialog.Accepted or not result["mode"]:
            return

        if result["mode"] == "existing":
            cid = combo.currentData()
            info = self.store.get_collection(cid) or {"name": cid, "workshop_id": "", "files": []}
            if rec["file"] not in info["files"]:
                info["files"].append(rec["file"])
            self.store.upsert_collection(cid, info)
            rec["collection"] = cid
            self.store.save_library()
            self.refresh_items()
            self.refresh_cards()
            return

        ids = steam_api.extract_ids(edit.text())
        if not ids:
            QMessageBox.information(self, "归入合集", "未找到有效链接/ID")
            return
        self.count_label.setText("识别合集中…")
        worker = DetailsWorker(ids, resolve_collections=True)
        self._assign_worker = worker
        worker.done.connect(lambda details: self._on_assign_details(rec, details))
        worker.error.connect(lambda e: QMessageBox.warning(self, "识别失败", e))
        worker.finished.connect(lambda w=worker: self._release_worker(w, "_assign_worker"))
        worker.start()

    def _on_assign_details(self, rec, details):
        collection = None
        children = []
        for d in details:
            if d.get("result") == 1 and steam_api.collection_children(d):
                collection = {
                    "cid": "ws_" + str(d.get("publishedfileid")),
                    "name": str(d.get("title") or "未命名合集"),
                    "workshop_id": str(d.get("publishedfileid"))}
                children = steam_api.collection_children(d)
                break
        if not collection:
            QMessageBox.information(self, "归入合集", "该链接不是合集（或没有子物品）")
            return
        cid = collection["cid"]
        by_wid = {}
        for m in self.store.mods().values():
            if m.get("workshop_id"):
                by_wid[m["workshop_id"]] = m["file"]
        files = []
        missing = []
        for wid in children:
            f = by_wid.get(str(wid))
            if f:
                files.append(f)
                r = self.store.get_mod(f)
                r["collection"] = cid
            else:
                missing.append(str(wid))
        if rec["file"] not in files:
            files.append(rec["file"])
            self.store.get_mod(rec["file"])["collection"] = cid
        info = {"name": collection["name"], "workshop_id": collection["workshop_id"], "files": files}
        self.store.upsert_collection(cid, info)
        self.store.save_library()
        self.refresh_items()
        self.refresh_cards()
        msg = "已归组 %d 个部件到《%s》" % (len(files), collection["name"])
        if missing:
            msg += "\n\n另有 %d 个部件未在库中，是否立即下载？" % len(missing)
            if QMessageBox.question(self, "归入合集", msg) == QMessageBox.Yes:
                if gamemod.is_l4d2_running():
                    QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再下载")
                    return
                if self._dl_worker is not None and self._dl_worker.isRunning():
                    QMessageBox.warning(self, "下载中", "已有下载任务在进行，请等它完成")
                    return
                worker = DownloadWorker(self.store, self.library, missing, collection=collection)
                self._dl_worker = worker
                worker.done.connect(lambda recs: (self.refresh_items(), self.refresh_cards()))
                worker.error.connect(lambda e: QMessageBox.warning(self, "下载失败", e))
                worker.finished.connect(lambda w=worker: self._release_worker(w, "_dl_worker"))
                worker.start()
        else:
            QMessageBox.information(self, "归入合集", msg)

    def show_card_menu(self, card, global_pos):
        rec = card.rec
        menu = QMenu(self)
        a_alias = menu.addAction("设置别名")
        a_cat = menu.addAction("修改分类")
        a_assign = a_leave = None
        if rec.get("category") == "地图":
            menu.addSeparator()
            if rec.get("collection"):
                a_leave = menu.addAction("移出合集")
            else:
                a_assign = menu.addAction("归入合集…")
        menu.addSeparator()
        a_detail = menu.addAction("详情")
        a_page = menu.addAction("打开工坊页") if rec.get("workshop_id") else None
        a_folder = menu.addAction("打开 mod 所在位置")
        menu.addSeparator()
        a_del = menu.addAction("删除（移入回收站）")
        act = menu.exec(global_pos)
        if act is None:
            return
        if act == a_alias:
            text, ok = QInputDialog.getText(None, "设置别名",
                                            "别名（留空清除）：", text=rec.get("alias", ""))
            if ok:
                self.library.set_alias(rec["file"], text)
                self.refresh_cards()
        elif act == a_cat:
            dlg = CategoryDialog(self, rec)
            dlg.exec()
            self.refresh_cards()
        elif a_assign and act == a_assign:
            self.assign_collection_flow(rec)
        elif a_leave and act == a_leave:
            info = self.store.get_collection(rec["collection"])
            if info and rec["file"] in info.get("files", []):
                info["files"].remove(rec["file"])
                if not info.get("files"):
                    self.store.remove_collection(rec["collection"])
                self.store.save_library()
            rec["collection"] = ""
            self.store.save_library()
            self.refresh_items()
            self.refresh_cards()
        elif act == a_detail:
            DetailDialog(self, self.store.get_mod(rec["file"]) or rec).exec()
        elif a_page and act == a_page:
            gamemod.open_workshop_page(rec["workshop_id"])
        elif act == a_folder:
            self.library.reveal_mod(rec["file"])
        elif act == a_del:
            self.delete_mod_flow(rec["file"])

    def ensure_game_closed(self):
        if gamemod.is_l4d2_running():
            QMessageBox.warning(self, "游戏运行中", "该操作需要先关闭游戏")
            return False
        return True

    def do_import(self):
        if self.library is None:
            QMessageBox.warning(self, "未配置", "请先在设置中指定游戏目录")
            return
        if not self.ensure_game_closed():
            return
        dialog = ImportArchiveDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._on_import_done(dialog.imported, dialog.duplicate_count)

    def _on_import_done(self, recs, duplicate_count=0):
        self.count_label.setText("导入完成：%d 个 mod" % len(recs))
        self.refresh_items()
        self.refresh_cards()
        if recs:
            names = "\n".join("· %s（%s / %s）" % (r["title"] or r["file"], r["category"], r["item"] or "—")
                              for r in recs[:12])
            duplicate_note = ("\n已自动跳过 %d 个重复 mod。" % duplicate_count
                              if duplicate_count else "")
            QMessageBox.information(self, "导入完成",
                                    "已导入 %d 个 mod：\n%s%s"
                                    % (len(recs), names, duplicate_note))

    def open_workshop(self):
        if self.library is None:
            QMessageBox.warning(self, "未配置", "请先在设置中指定游戏目录")
            return
        WorkshopDialog(self).exec()
        self.refresh_items()
        self.refresh_cards()

    def _show_unsubscribe_dialog(self, ids):
        """一键管理迁移了 workshop 订阅项后，提示退订（防 Steam 重新同步）。"""
        dlg = AppDialog(self, "退订已迁移的工坊物品")
        dlg.setMinimumSize(430, 330)
        v = QVBoxLayout(dlg.content)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(10)
        hint = QLabel("以下物品已从 addons/workshop 迁入管理。\n"
                      "建议在 Steam 中退订，否则 Steam 可能把文件重新同步回 workshop 目录。\n"
                      "双击条目或点「打开全部工坊页」逐个退订。")
        hint.setObjectName("Hint")
        v.addWidget(hint)
        lst = QListWidget()
        for wid in ids:
            QListWidgetItem("工坊物品 ID %s" % wid, lst)
        lst.itemDoubleClicked.connect(
            lambda it: gamemod.open_workshop_page(it.text().split()[-1]))
        v.addWidget(lst, 1)
        btns = QHBoxLayout()
        b_all = QPushButton("打开全部工坊页")
        b_all.clicked.connect(lambda: [gamemod.open_workshop_page(w) for w in ids])
        b_close = QPushButton("关闭")
        b_close.clicked.connect(dlg.reject)
        btns.addStretch(1)
        btns.addWidget(b_all)
        btns.addWidget(b_close)
        v.addLayout(btns)
        dlg.exec()

    # ---------- 设置页 ----------
    def show_settings(self):
        self.stack.setCurrentIndex(1)
        self._animate_page_switch()
        for b in self.rail_buttons.values():
            b.setChecked(False)
        self.btn_settings_nav.setChecked(True)
        self._refresh_settings_subs()

    def _settings_row(self, icon, title_text, sub_widget, right=None):
        """参考布局：全宽卡片行 = 图标 + 标题/副标题 + 右侧操作。"""
        card = QFrame()
        card.setObjectName("SettingsCard")
        h = QHBoxLayout(card)
        h.setContentsMargins(14, 10, 14, 10)
        h.setSpacing(12)
        ic = QLabel(icon)
        ic.setStyleSheet("font-size:16px; background:transparent; border:none;")
        h.addWidget(ic)
        box = QVBoxLayout()
        box.setSpacing(2)
        t = QLabel(title_text)
        t.setObjectName("SettingsTitle")
        t.setStyleSheet("background:transparent;")
        box.addWidget(t)
        sub_widget.setStyleSheet("background:transparent;")
        box.addWidget(sub_widget)
        h.addLayout(box, 1)
        if right is not None:
            h.addWidget(right)
        return card

    def _settings_section(self, outer, text):
        lab = QLabel(text)
        lab.setObjectName("SettingsSection")
        outer.addWidget(lab)
        outer.addSpacing(2)

    def _sub_label(self, text=""):
        lab = QLabel(text)
        lab.setObjectName("SettingsSub")
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return lab

    def _build_settings_page(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(28, 22, 28, 16)
        outer.setSpacing(10)

        title = QLabel("设置")
        title.setObjectName("DlgTitle")
        outer.addWidget(title)
        outer.addSpacing(2)

        # ---- 配置目录 ----
        self._settings_section(outer, "配置目录")
        self._st_game_sub = self._sub_label()
        right1 = QWidget()
        right1.setObjectName("SettingsActionHost")
        h1 = QHBoxLayout(right1)
        h1.setContentsMargins(0, 0, 0, 0)
        h1.setSpacing(6)
        b_detect = QPushButton("自动检测")
        b_detect.clicked.connect(self._detect_game)
        b_browse = QPushButton("更改目录")
        b_browse.clicked.connect(self._browse_game)
        h1.addWidget(b_detect)
        h1.addWidget(b_browse)
        outer.addWidget(self._settings_row("📁", "L4D2 目录", self._st_game_sub, right1))

        self._st_proxy_sub = self._sub_label()
        b_proxy = QPushButton("设置代理")
        b_proxy.clicked.connect(self._edit_proxy)
        outer.addWidget(self._settings_row("🌐", "网络代理", self._st_proxy_sub, b_proxy))

        # ---- 缓存 ----
        self._settings_section(outer, "缓存")
        self._st_cache_sub = self._sub_label()
        b_clean = QPushButton("清理")
        b_clean.clicked.connect(self._clean_cache)
        outer.addWidget(self._settings_row("🧹", "清理缓存", self._st_cache_sub, b_clean))

        # ---- 更新 ----
        self._settings_section(outer, "更新")
        self._st_autocheck = QCheckBox()
        self._st_autocheck.setChecked(bool(self.store.settings().get("check_update_on_start", False)))
        right_auto = QWidget()
        right_auto.setObjectName("SettingsActionHost")
        ha = QHBoxLayout(right_auto)
        ha.setContentsMargins(0, 0, 0, 0)
        ha.setSpacing(8)
        self._st_auto_lab = QLabel("关")
        self._st_auto_lab.setObjectName("SettingsSub")
        self._st_auto_lab.setStyleSheet("background:transparent;")
        ha.addWidget(self._st_auto_lab)
        ha.addWidget(self._st_autocheck)
        self._st_autocheck.toggled.connect(self._on_autocheck_toggled)
        outer.addWidget(self._settings_row("🔄", "启动检查", self._sub_label("启动程序时检查更新"), right_auto))

        self._st_update_sub = self._sub_label("当前版本 v%s" % APP_VERSION)
        b_check = QPushButton("检查更新")
        b_check.clicked.connect(self._check_update)
        outer.addWidget(self._settings_row("⬇", "检查更新", self._st_update_sub, b_check))

        # ---- 关于 ----
        self._settings_section(outer, "关于")
        self._st_repo_sub = self._sub_label(REPO_URL or "仓库链接待发布")
        right_repo = None
        if REPO_URL:
            right_repo = QWidget()
            right_repo.setObjectName("SettingsActionHost")
            hr = QHBoxLayout(right_repo)
            hr.setContentsMargins(0, 0, 0, 0)
            link = QLabel('<a href="%s" style="color:%s; text-decoration:none;">打开 github 项目</a>'
                          % (REPO_URL, theme.GREEN))
            link.setOpenExternalLinks(True)
            hr.addWidget(link)
        outer.addWidget(self._settings_row("⭐", "仓库项目", self._st_repo_sub, right_repo))

        self._st_about_sub = self._sub_label("© 2026 L4D2 Mod Manager · 当前版本 v%s" % APP_VERSION)
        outer.addWidget(self._settings_row("ℹ", "About", self._st_about_sub))

        outer.addStretch(1)
        self._refresh_settings_subs()
        return page

    def _on_autocheck_toggled(self, on):
        self.store.set_setting("check_update_on_start", bool(on))
        self._st_auto_lab.setText("开" if on else "关")

    def _refresh_settings_subs(self):
        if not hasattr(self, "_st_game_sub"):
            return
        gd = self.store.settings().get("game_dir", "")
        ok = pathsmod.is_game_dir(gd)
        self._st_game_sub.setText(("✔ " if ok else "✘ ") + (gd or "未配置"))
        proxy = self.store.settings().get("proxy", "")
        self._st_proxy_sub.setText(proxy if proxy else "自动探测本地代理（clash 7890 等）")
        try:
            total = 0
            for d in (self.store.trash_dir, self.store.tmp_dir):
                for dp, _dn, fn in os.walk(d):
                    for f in fn:
                        try:
                            total += os.path.getsize(os.path.join(dp, f))
                        except OSError:
                            pass
            self._st_cache_sub.setText("清理回收站与临时文件 · 当前占用 %.1f MB" % (total / 1048576.0))
        except Exception:
            self._st_cache_sub.setText("清理回收站与临时文件")

    def _browse_game(self):
        d = QFileDialog.getExistingDirectory(
            None, "选择 L4D2 游戏目录（含 left4dead2 文件夹）")
        if not d:
            return
        if not pathsmod.is_game_dir(d):
            QMessageBox.warning(self, "无效路径", "该目录不是有效的 L4D2 游戏目录")
            return
        self.store.set_setting("game_dir", d)
        self.apply_game_dir()
        self._refresh_settings_subs()

    def _detect_game(self):
        d = pathsmod.find_game_dir()
        if not d:
            QMessageBox.information(self, "自动检测", "未能自动定位游戏目录，请手动选择")
            return
        self.store.set_setting("game_dir", d)
        self.apply_game_dir()
        self._refresh_settings_subs()

    def _edit_proxy(self):
        cur = self.store.settings().get("proxy", "")
        text, ok = QInputDialog.getText(None, "网络代理",
                                        "代理地址（留空 = 自动探测本地代理）：", text=cur)
        if not ok:
            return
        self.store.set_setting("proxy", text.strip())
        steam_api.set_proxy(text.strip())
        self._refresh_settings_subs()

    def _clean_cache(self):
        total = 0
        files = []
        for d in (self.store.trash_dir, self.store.tmp_dir):
            for dp, _dn, fn in os.walk(d):
                for f in fn:
                    p = os.path.join(dp, f)
                    try:
                        total += os.path.getsize(p)
                        files.append(p)
                    except OSError:
                        pass
        if not files:
            QMessageBox.information(self, "清理缓存", "没有可清理的文件")
            return
        if QMessageBox.question(self, "清理缓存",
                                "将删除回收站与临时文件共 %d 个（%.1f MB），确定？"
                                % (len(files), total / 1048576.0)) != QMessageBox.Yes:
            return
        freed = 0
        for p in files:
            try:
                freed += os.path.getsize(p)
                os.remove(p)
            except OSError:
                pass
        self._refresh_settings_subs()
        QMessageBox.information(self, "清理缓存", "已释放 %.1f MB" % (freed / 1048576.0))

    def _check_update(self):
        repo = REPO_URL.strip().rstrip("/")
        if not repo:
            self._st_update_sub.setText("仓库链接尚未配置，无法检查更新")
            return
        if self._update_worker is not None and self._update_worker.isRunning():
            return
        self._st_update_sub.setText("检查中…")
        if "github.com/" in repo:
            owner_repo = repo.split("github.com/", 1)[1].strip("/")
            url = "https://api.github.com/repos/%s/releases/latest" % owner_repo
        else:
            url = repo + "/update.json"
        worker = UpdateCheckWorker(url)
        self._update_worker = worker
        worker.done.connect(self._on_update_check)
        worker.error.connect(
            lambda e: self._st_update_sub.setText("检查失败：%s" % e[:80]))
        worker.finished.connect(lambda w=worker: self._release_worker(w, "_update_worker"))
        worker.start()

    def _on_update_check(self, latest, release_url):
        latest_clean = latest.lstrip("vV")
        if latest_clean and latest_clean != APP_VERSION:
            self._st_update_sub.setText("发现新版本 %s（当前 v%s）" % (latest, APP_VERSION))
            if release_url:
                gamemod.open_folder(release_url)
        else:
            self._st_update_sub.setText("已是最新版本 v%s" % APP_VERSION)

    def launch_game(self):
        gamemod.launch_game()
        self._update_game_status()

    def _update_game_status(self):
        running = gamemod.is_l4d2_running()
        if running:
            self.game_label.setText("● 游戏运行中")
            self.game_label.setStyleSheet("color: %s;" % theme.GREEN)
        else:
            self.game_label.setText("● 游戏未运行")
            self.game_label.setStyleSheet("")

    # ---------- 退出 ----------
    def closeEvent(self, e):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.wait(2000)
        try:
            self.store.set_setting("geometry_b64",
                                   bytes(self.saveGeometry().toBase64()).decode("ascii"))
            self.store.set_setting("splitter_b64_v2",
                                   bytes(self.splitter.saveState().toBase64()).decode("ascii"))
        except Exception:
            pass
        self.store.save_library()
        self.store.save_settings()
        e.accept()
