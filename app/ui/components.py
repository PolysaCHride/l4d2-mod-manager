# -*- coding: utf-8 -*-
"""共享窗口组件：无边框圆角对话框、消息框、平滑进度条。"""
import ctypes
import os
import sys

from PySide6.QtCore import (
    QAbstractAnimation, QEasingCurve, QEvent, QPoint, QPropertyAnimation, Property,
    QRect, QSize, Qt, QTimer,
)
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel,
    QMessageBox as NativeMessageBox, QProgressBar, QPushButton, QSizeGrip,
    QVBoxLayout, QWidget,
)

from . import theme


def motion_enabled():
    """尊重 Windows 的“显示动画”设置，并允许用环境变量强制关闭。"""
    override = os.environ.get("L4D2_MM_REDUCE_MOTION", "").strip().lower()
    if override in ("1", "true", "yes", "on"):
        return False
    if override in ("0", "false", "no", "off"):
        return True
    if sys.platform != "win32":
        return True
    try:
        enabled = ctypes.c_bool(True)
        # SPI_GETCLIENTAREAANIMATION
        ok = ctypes.windll.user32.SystemParametersInfoW(
            0x1042, 0, ctypes.byref(enabled), 0)
        return bool(enabled.value) if ok else True
    except Exception:
        return True


def fade_in_window(window, duration=180, start_opacity=0.0):
    if not motion_enabled():
        window.setWindowOpacity(1.0)
        return None
    window.setWindowOpacity(start_opacity)
    anim = QPropertyAnimation(window, b"windowOpacity", window)
    anim.setDuration(duration)
    anim.setStartValue(start_opacity)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start(QAbstractAnimation.DeleteWhenStopped)
    return anim


def fade_in_widget(widget, duration=180, start_opacity=0.0):
    """给列表或结果区域做一次轻量淡入，不保留常驻图形特效。"""
    if not motion_enabled():
        old = getattr(widget, "_motion_fade_animation", None)
        if old is not None:
            old.stop()
        widget.setGraphicsEffect(None)
        return None
    old = getattr(widget, "_motion_fade_animation", None)
    if old is not None:
        old.stop()
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(start_opacity)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start_opacity)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def cleanup():
        if widget.graphicsEffect() is effect:
            widget.setGraphicsEffect(None)

    anim.finished.connect(cleanup)
    anim.start(QAbstractAnimation.DeleteWhenStopped)
    widget._motion_fade_animation = anim
    return anim


class DialogTitleBar(QWidget):
    """对话框的轻量标题栏：可拖动，只保留关闭按钮。"""

    def __init__(self, dialog, title):
        super().__init__(dialog)
        self._dialog = dialog
        self._drag = None
        self.setObjectName("DialogTitleBar")
        self.setFixedHeight(48)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 0, 0)
        row.setSpacing(0)

        icon = QLabel()
        icon.setObjectName("DialogIcon")
        icon.setFixedSize(24, 24)
        pm = QPixmap(theme.icon_path("icon_32.png"))
        if not pm.isNull():
            icon.setPixmap(pm.scaled(
                18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row.addWidget(icon)
        row.addSpacing(10)

        self.title = QLabel(title)
        self.title.setObjectName("DialogTitle")
        row.addWidget(self.title)
        row.addStretch(1)

        close = QPushButton()
        close.setObjectName("btnClose")
        close.setProperty("role", "window")
        close.setFocusPolicy(Qt.NoFocus)
        close.setFixedSize(46, 32)
        close.setIcon(theme.caption_icon("close"))
        close.setIconSize(QSize(14, 14))
        close.setToolTip("关闭")
        close.clicked.connect(dialog.reject)
        row.addWidget(close, 0, Qt.AlignTop)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag and event.buttons() & Qt.LeftButton:
            self._dialog.move(event.globalPosition().toPoint() - self._drag)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag = None
        super().mouseReleaseEvent(event)


class AppDialog(QDialog):
    """与主窗口统一的无边框圆角对话框。子类把内容放进 self.content。"""

    _EDGE = 8
    _CURSORS = {
        1: Qt.SizeHorCursor, 2: Qt.SizeHorCursor,
        4: Qt.SizeVerCursor, 8: Qt.SizeVerCursor,
        5: Qt.SizeFDiagCursor, 10: Qt.SizeFDiagCursor,
        6: Qt.SizeBDiagCursor, 9: Qt.SizeBDiagCursor,
    }

    def __init__(self, parent=None, title=""):
        owner = parent.window() if isinstance(parent, QWidget) else None
        # Windows 只会把没有 owner 的顶层窗口列入任务栏悬停预览。
        # 保留 owner 仅用于居中，不能把弹窗设置为主窗口的 Qt 子级。
        super().__init__(None)
        self._owner_window = owner
        self.setWindowTitle(title)
        self.setObjectName("TransparentDialog")
        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint
            | Qt.WindowTitleHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        self._centered_once = False
        self._resize_filter_installed = False
        self._resizing = False
        self._resize_dir = 0
        self._resize_origin = QPoint()
        self._resize_geom = QRect()
        self._edge_cursor_active = False
        self._mouse_grabbed = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.shell = QFrame()
        self.shell.setObjectName("DialogSurface")
        outer.addWidget(self.shell)

        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        self.titlebar = DialogTitleBar(self, title)
        shell_layout.addWidget(self.titlebar)

        hazard = QLabel()
        hazard.setObjectName("HazardDivider")
        hazard.setFixedHeight(4)
        hazard.setPixmap(theme.hazard_pixmap(1600, 4))
        hazard.setScaledContents(True)
        shell_layout.addWidget(hazard)

        self.content = QWidget()
        self.content.setObjectName("DialogContent")
        shell_layout.addWidget(self.content, 1)

        self._grip = QSizeGrip(self.shell)
        self._grip.setObjectName("DialogSizeGrip")
        self._grip.resize(18, 18)
        self._grip.show()

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, "titlebar"):
            self.titlebar.title.setText(title)

    def showEvent(self, event):
        super().showEvent(event)
        app = QApplication.instance()
        if app is not None and not self._resize_filter_installed:
            app.installEventFilter(self)
            self._resize_filter_installed = True
        if not self._centered_once:
            self._centered_once = True
            target = self._owner_window
            if target is not None and target.isVisible():
                frame = target.frameGeometry()
                x = frame.x() + (frame.width() - self.width()) // 2
                y = frame.y() + (frame.height() - self.height()) // 2
                self.move(x, y)
        QTimer.singleShot(0, lambda: fade_in_window(self, duration=170))

    def hideEvent(self, event):
        self._finish_resize()
        app = QApplication.instance()
        if app is not None and self._resize_filter_installed:
            app.removeEventFilter(self)
            self._resize_filter_installed = False
        super().hideEvent(event)

    def _edges_at(self, gp):
        if (not self.isVisible() or self.isMaximized()
                or QApplication.activeWindow() is not self):
            return 0
        p = self.mapFromGlobal(gp)
        if not self.rect().contains(p):
            return 0
        edges = 0
        if p.x() < self._EDGE:
            edges |= 1
        if self.rect().right() - p.x() < self._EDGE:
            edges |= 2
        if p.y() < self._EDGE:
            edges |= 4
        if self.rect().bottom() - p.y() < self._EDGE:
            edges |= 8
        return edges

    def _set_edge_cursor(self, edges):
        if edges:
            cursor = QCursor(self._CURSORS.get(edges, Qt.ArrowCursor))
            if self._edge_cursor_active:
                QApplication.changeOverrideCursor(cursor)
            else:
                QApplication.setOverrideCursor(cursor)
                self._edge_cursor_active = True
        elif self._edge_cursor_active:
            QApplication.restoreOverrideCursor()
            self._edge_cursor_active = False

    def _finish_resize(self):
        if self._mouse_grabbed:
            self.releaseMouse()
            self._mouse_grabbed = False
        self._resizing = False
        self._resize_dir = 0
        self._set_edge_cursor(0)

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

    def eventFilter(self, obj, event):
        if (not self.isVisible() or not isinstance(obj, QWidget)
                or obj.window() is not self):
            return super().eventFilter(obj, event)
        et = event.type()
        if et == QEvent.MouseMove:
            gp = event.globalPosition().toPoint()
            if self._resizing:
                self._apply_resize(gp)
                return True
            self._set_edge_cursor(self._edges_at(gp))
        elif et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            gp = event.globalPosition().toPoint()
            edges = self._edges_at(gp)
            if edges:
                self._resizing = True
                self._resize_dir = edges
                self._resize_origin = gp
                self._resize_geom = self.geometry()
                self.grabMouse()
                self._mouse_grabbed = True
                self._set_edge_cursor(edges)
                return True
        elif et == QEvent.MouseButtonRelease and self._resizing:
            self._finish_resize()
            return True
        elif et == QEvent.Leave and not self._resizing:
            self._set_edge_cursor(0)
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_grip"):
            self._grip.move(self.shell.width() - self._grip.width() - 2,
                            self.shell.height() - self._grip.height() - 2)
            self._grip.raise_()


class AppMessageBox(AppDialog):
    """保持 QMessageBox 常用 API 的圆角消息框，避免系统白色标题栏。"""

    NoButton = NativeMessageBox.NoButton
    Ok = NativeMessageBox.Ok
    Save = NativeMessageBox.Save
    Cancel = NativeMessageBox.Cancel
    Yes = NativeMessageBox.Yes
    No = NativeMessageBox.No
    Abort = NativeMessageBox.Abort
    Retry = NativeMessageBox.Retry
    Ignore = NativeMessageBox.Ignore
    Close = NativeMessageBox.Close

    NoIcon = NativeMessageBox.NoIcon
    Question = NativeMessageBox.Question
    Information = NativeMessageBox.Information
    Warning = NativeMessageBox.Warning
    Critical = NativeMessageBox.Critical

    InvalidRole = NativeMessageBox.InvalidRole
    AcceptRole = NativeMessageBox.AcceptRole
    RejectRole = NativeMessageBox.RejectRole
    DestructiveRole = NativeMessageBox.DestructiveRole
    ActionRole = NativeMessageBox.ActionRole
    HelpRole = NativeMessageBox.HelpRole
    YesRole = NativeMessageBox.YesRole
    NoRole = NativeMessageBox.NoRole
    ResetRole = NativeMessageBox.ResetRole
    ApplyRole = NativeMessageBox.ApplyRole

    def __init__(self, parent=None, title=""):
        super().__init__(parent, title)
        self._standard_buttons = self.NoButton
        self._default_button = None
        self._clicked_button = None
        self._result_value = self.NoButton

        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(12)
        self.icon_label = QLabel("?")
        self.icon_label.setObjectName("MessageIcon")
        self.icon_label.setProperty("tone", "question")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(36, 36)
        head.addWidget(self.icon_label, 0, Qt.AlignTop)

        title_label = QLabel(title or "提示")
        title_label.setObjectName("MessageTitle")
        title_label.setWordWrap(True)
        head.addWidget(title_label, 1)
        self._title_label = title_label
        layout.addLayout(head)

        self.text_label = QLabel("")
        self.text_label.setObjectName("MessageText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text_label.setMinimumWidth(380)
        layout.addWidget(self.text_label)

        self._extra_host = QWidget()
        self._extra_host.setObjectName("MessageExtra")
        self._extra_layout = QVBoxLayout(self._extra_host)
        self._extra_layout.setContentsMargins(0, 0, 0, 0)
        self._extra_layout.setSpacing(8)
        layout.addWidget(self._extra_host)

        self._button_row = QHBoxLayout()
        self._button_row.setContentsMargins(0, 2, 0, 0)
        self._button_row.setSpacing(8)
        self._button_row.addStretch(1)
        layout.addLayout(self._button_row)
        self.setMinimumWidth(500)
        self.setMaximumWidth(700)
        self.resize(560, max(190, self.sizeHint().height()))

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, "_title_label"):
            self._title_label.setText(title or "提示")

    def setIcon(self, icon):
        tone = "question"
        glyph = "?"
        if icon == self.Warning:
            tone, glyph = "warning", "!"
        elif icon == self.Information:
            tone, glyph = "information", "i"
        elif icon == self.Critical:
            tone, glyph = "critical", "×"
        elif icon == self.NoIcon:
            tone, glyph = "neutral", "·"
        self.icon_label.setText(glyph)
        self.icon_label.setProperty("tone", tone)
        self.icon_label.style().unpolish(self.icon_label)
        self.icon_label.style().polish(self.icon_label)

    def setText(self, text):
        self.text_label.setText(str(text))

    def setInformativeText(self, text):
        self.text_label.setText(self.text_label.text() + "\n\n" + str(text))

    def setCheckBox(self, checkbox):
        self._extra_layout.addWidget(checkbox)

    def _button_text(self, standard):
        return {
            self.Yes: "继续",
            self.No: "取消",
            self.Ok: "确定",
            self.Cancel: "取消",
            self.Close: "关闭",
        }.get(standard, "确定")

    def _add_standard_button(self, standard, primary=False, destructive=False):
        button = QPushButton(self._button_text(standard))
        if primary:
            button.setProperty("accent", "primary")
        elif destructive:
            button.setProperty("accent", "danger")
        button.clicked.connect(lambda _checked=False, value=standard:
                               self._finish_standard(value))
        self._button_row.addWidget(button)
        if standard == self._default_button:
            button.setDefault(True)
            button.setFocus()
        return button

    def setStandardButtons(self, buttons):
        self._standard_buttons = buttons
        # 取消在左、确认在右，符合桌面应用的决策顺序。
        if buttons & self.No:
            self._add_standard_button(self.No)
        if buttons & self.Cancel:
            self._add_standard_button(self.Cancel)
        if buttons & self.Yes:
            self._add_standard_button(self.Yes, primary=True)
        elif buttons & self.Ok:
            self._add_standard_button(self.Ok, primary=True)
        elif buttons & self.Save:
            self._add_standard_button(self.Save, primary=True)
        elif buttons & self.Close:
            self._add_standard_button(self.Close)
        return self

    def setDefaultButton(self, button):
        self._default_button = button
        if isinstance(button, QPushButton):
            button.setDefault(True)
            button.setFocus()
        return self

    def addButton(self, text, role):
        button = QPushButton(str(text))
        if role == self.DestructiveRole:
            button.setProperty("accent", "danger")
        elif role == self.AcceptRole:
            button.setProperty("accent", "primary")
        button.clicked.connect(
            lambda _checked=False, target=button: self._finish_custom(target))
        self._button_row.addWidget(button)
        return button

    def _finish_standard(self, value):
        self._result_value = value
        self.accept()

    def _finish_custom(self, button):
        self._clicked_button = button
        self._result_value = self.Ok
        self.accept()

    def clickedButton(self):
        return self._clicked_button

    def exec(self):
        super().exec()
        return self._result_value

    @classmethod
    def _show(cls, parent, title, text, icon, buttons, default_button):
        box = cls(parent, title)
        box.setIcon(icon)
        box.setText(text)
        box.setStandardButtons(buttons)
        if default_button != cls.NoButton:
            box.setDefaultButton(default_button)
        return box.exec()

    @classmethod
    def information(cls, parent, title, text, buttons=None,
                    defaultButton=None):
        buttons = cls.Ok if buttons is None else buttons
        defaultButton = cls.Ok if defaultButton is None else defaultButton
        return cls._show(parent, title, text, cls.Information, buttons, defaultButton)

    @classmethod
    def warning(cls, parent, title, text, buttons=None, defaultButton=None):
        buttons = cls.Ok if buttons is None else buttons
        defaultButton = cls.Ok if defaultButton is None else defaultButton
        return cls._show(parent, title, text, cls.Warning, buttons, defaultButton)

    @classmethod
    def critical(cls, parent, title, text, buttons=None, defaultButton=None):
        buttons = cls.Ok if buttons is None else buttons
        defaultButton = cls.Ok if defaultButton is None else defaultButton
        return cls._show(parent, title, text, cls.Critical, buttons, defaultButton)

    @classmethod
    def question(cls, parent, title, text, buttons=None,
                 defaultButton=None):
        buttons = (cls.Yes | cls.No) if buttons is None else buttons
        defaultButton = cls.No if defaultButton is None else defaultButton
        return cls._show(parent, title, text, cls.Question, buttons, defaultButton)


class AnimatedProgressBar(QProgressBar):
    """数值变化平滑过渡；不确定进度仍使用系统自带的滚动动画。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value_anim = QPropertyAnimation(self, b"animatedValue", self)
        self._value_anim.setDuration(240)
        self._value_anim.setEasingCurve(QEasingCurve.OutCubic)

    @Property(int)
    def animatedValue(self):
        return self.value()

    @animatedValue.setter
    def animatedValue(self, value):
        QProgressBar.setValue(self, int(value))

    def setValue(self, value):
        target = int(value)
        if not motion_enabled() or self.maximum() <= self.minimum():
            self._value_anim.stop()
            QProgressBar.setValue(self, target)
            return
        self._value_anim.stop()
        self._value_anim.setStartValue(self.value())
        self._value_anim.setEndValue(target)
        self._value_anim.start()
