# -*- coding: utf-8 -*-
"""对话框集合：工坊搜索下载 / 迁移向导 / 归类 / 设置 / 详情。"""
import os
import re
import time

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal,
)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QCheckBox, QFrame, QGraphicsOpacityEffect, QLabel, QListWidget,
    QListWidgetItem, QPlainTextEdit,
    QPushButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QAbstractItemView,
    QScrollArea,
)

from ..core import game as gamemod
from ..core import archiver as archiver_core
from ..core import importer
from ..core import steam_api
from ..core.classify import CATEGORIES, MELEE_NAMES, MED_NAMES, SPECIAL_NAMES, SURVIVOR_NAMES, WEAPON_SEG_NAMES
from . import theme, util
from .components import (
    AnimatedProgressBar, AppDialog, AppMessageBox as QMessageBox, motion_enabled,
)
from .workers import (
    ArchiverInstallWorker, DetailsWorker, DownloadWorker, ImportAnalyzeWorker,
    ImportCommitWorker, MigrateWorker, ParentCollectionWorker,
)

L4D2_APPID = steam_api.L4D2_APPID
WORKSHOP_APP_NAMES = {
    440: "Team Fortress 2",
    550: "Left 4 Dead 2",
    570: "Dota 2",
    730: "Counter-Strike 2（CS2 / CS:GO）",
}


# ---------------------------------------------------------------- 压缩包导入
class ArchiveDropZone(QFrame):
    clicked = Signal()
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ArchiveDropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(138)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 18, 24, 18)
        v.setSpacing(5)
        v.setAlignment(Qt.AlignCenter)

        self.icon = QLabel("＋")
        self.icon.setObjectName("ImportDropIcon")
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setFixedSize(46, 46)
        self.icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._icon_effect = QGraphicsOpacityEffect(self.icon)
        self._icon_effect.setOpacity(1.0)
        self.icon.setGraphicsEffect(self._icon_effect)
        self._icon_pulse = QPropertyAnimation(self._icon_effect, b"opacity", self)
        self._icon_pulse.setDuration(520)
        self._icon_pulse.setStartValue(1.0)
        self._icon_pulse.setKeyValueAt(0.5, 0.45)
        self._icon_pulse.setEndValue(1.0)
        self._icon_pulse.setEasingCurve(QEasingCurve.InOutSine)
        v.addWidget(self.icon, 0, Qt.AlignHCenter)

        self.title = QLabel("点击选择压缩包")
        self.title.setObjectName("ImportDropTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
        v.addWidget(self.title)

        self.hint = QLabel("也可以将 ZIP / 7z / RAR 直接拖到这里")
        self.hint.setObjectName("ImportDropHint")
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setAttribute(Qt.WA_TransparentForMouseEvents)
        v.addWidget(self.hint)

    @staticmethod
    def _paths(mime):
        paths = []
        if not mime.hasUrls():
            return paths
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if os.path.isfile(path) and importer.supported_ext(path):
                paths.append(path)
        return paths

    def _set_drag_active(self, active):
        self.setProperty("dragActive", bool(active))
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon.setText("↓" if active else "＋")
        if active and motion_enabled():
            self._icon_pulse.start()
        elif not active:
            self._icon_pulse.stop()
            self._icon_effect.setOpacity(1.0)
        self.update()

    def dragEnterEvent(self, event):
        if self._paths(event.mimeData()):
            self._set_drag_active(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)
        event.accept()

    def dropEvent(self, event):
        paths = self._paths(event.mimeData())
        self._set_drag_active(False)
        if paths:
            self.filesDropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class MissingArchiverDialog(AppDialog):
    """7z/RAR import fallback when no usable archiver can be found."""

    def __init__(self, main):
        super().__init__(main, "缺少解压组件")
        self.main = main
        self.archiver_path = ""
        self._worker = None
        self.resize(590, 390)
        self.setMinimumSize(540, 360)

        root = QVBoxLayout(self.content)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("需要 7-Zip 解压组件")
        title.setObjectName("ImportResultTitle")
        root.addWidget(title)

        body = QLabel(
            "当前没有找到可用的 7-Zip 或 WinRAR，无法读取 7z / RAR 压缩包。\n"
            "可以自动下载并校验 7-Zip 官方组件，安装到软件自己的数据目录，"
            "不会修改系统环境；也可以手动指定已有的 7z.exe。")
        body.setObjectName("Hint")
        body.setWordWrap(True)
        root.addWidget(body)

        self.status_label = QLabel("请选择处理方式")
        self.status_label.setObjectName("ImportStatus")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.progress = AnimatedProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        root.addWidget(self.progress)
        root.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(9)
        self.btn_cancel = QPushButton("取消")
        self.btn_choose = QPushButton("手动选择 7z.exe")
        self.btn_download = QPushButton("自动下载安装")
        self.btn_download.setProperty("accent", "primary")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_choose.clicked.connect(self._choose_executable)
        self.btn_download.clicked.connect(self._start_download)
        actions.addStretch(1)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_choose)
        actions.addWidget(self.btn_download)
        root.addLayout(actions)

    def _set_busy(self, busy):
        self.btn_cancel.setEnabled(not busy)
        self.btn_choose.setEnabled(not busy)
        self.btn_download.setEnabled(not busy)
        self.progress.setVisible(busy)

    def _choose_executable(self):
        start = os.path.dirname(self.archiver_path) if self.archiver_path else ""
        if not start and self.main.archiver:
            start = os.path.dirname(self.main.archiver.path)
        selected, _filter = QFileDialog.getOpenFileName(
            self, "选择解压程序", start,
            "7-Zip / WinRAR (7z.exe 7zz.exe WinRAR.exe rar.exe);;程序 (*.exe)")
        if not selected:
            return
        info = archiver_core.from_path(selected, source="manual")
        if info is None:
            QMessageBox.warning(
                self, "程序不可用",
                "请选择有效的 7z.exe、7zz.exe、WinRAR.exe 或 rar.exe。")
            return
        self.archiver_path = info.path
        self.accept()

    def _start_download(self):
        if self._worker is not None and self._worker.isRunning():
            return
        self._set_busy(True)
        self.status_label.setText("正在准备下载 7-Zip…")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        dest = os.path.join(self.main.store.data_dir, "tools", "7zip")
        worker = ArchiverInstallWorker(dest, self)
        self._worker = worker
        worker.progress.connect(self._on_download_progress)
        worker.done.connect(self._on_download_done)
        worker.error.connect(self._on_download_error)
        worker.finished.connect(lambda w=worker: self._release_worker(w))
        worker.start()

    def _on_download_progress(self, percent, text):
        self.progress.setValue(percent)
        self.status_label.setText(text)

    def _on_download_done(self, path):
        info = archiver_core.from_path(path, source="downloaded")
        if info is None:
            self._on_download_error("7-Zip 安装完成后未找到可用的 7z.exe")
            return
        self.archiver_path = info.path
        self.accept()

    def _on_download_error(self, message):
        self._set_busy(False)
        self.status_label.setText("自动安装失败，可改用“手动选择 7z.exe”")
        QMessageBox.warning(
            self, "自动安装失败",
            "%s\n\n也可以手动选择已下载的 7z.exe。" % message)

    def _release_worker(self, worker):
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    def reject(self):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "正在安装", "请等待 7-Zip 安装完成")
            return
        super().reject()

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "正在安装", "请等待 7-Zip 安装完成")
            event.ignore()
            return
        super().closeEvent(event)


class ImportArchiveDialog(AppDialog):
    """压缩包导入向导：点击或拖入，解析预览，勾选确认后入库。"""

    def __init__(self, main):
        super().__init__(main, "导入压缩包")
        self.main = main
        self.imported = []
        self.duplicate_count = 0
        self._batch = None
        self._worker = None

        self.resize(820, 780)
        self.setMinimumSize(690, 640)
        self.setAcceptDrops(True)

        root = QVBoxLayout(self.content)
        root.setContentsMargins(22, 16, 22, 18)
        root.setSpacing(12)

        subtitle = QLabel("支持 ZIP / 7z / RAR；解析完成后可以逐项选择要加入 mod 库的内容。")
        subtitle.setObjectName("Hint")
        root.addWidget(subtitle)

        self.drop_zone = ArchiveDropZone()
        self.drop_zone.clicked.connect(self.choose_archives)
        self.drop_zone.filesDropped.connect(self.start_analysis)
        root.addWidget(self.drop_zone)

        status_panel = QFrame()
        status_panel.setObjectName("ImportStatusPanel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(12, 8, 12, 9)
        status_layout.setSpacing(5)
        status_head = QHBoxLayout()
        self.status_label = QLabel("等待选择压缩包")
        self.status_label.setObjectName("ImportStatus")
        self.status_meta = QLabel("")
        self.status_meta.setObjectName("Hint")
        self.status_meta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_head.addWidget(self.status_label, 1)
        status_head.addWidget(self.status_meta)
        status_layout.addLayout(status_head)
        self.progress = AnimatedProgressBar()
        self.progress.setObjectName("ImportProgress")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        status_layout.addWidget(self.progress)
        root.addWidget(status_panel)

        result_head = QHBoxLayout()
        self.result_title = QLabel("可加入的 Mod")
        self.result_title.setObjectName("ImportResultTitle")
        self.btn_all = QPushButton("全选")
        self.btn_none = QPushButton("清空")
        self.btn_all.clicked.connect(lambda: self._set_all(True))
        self.btn_none.clicked.connect(lambda: self._set_all(False))
        self.btn_all.setEnabled(False)
        self.btn_none.setEnabled(False)
        result_head.addWidget(self.result_title)
        result_head.addStretch(1)
        result_head.addWidget(self.btn_all)
        result_head.addWidget(self.btn_none)
        root.addLayout(result_head)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ImportResultsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.result_host = QWidget()
        self.result_host.setObjectName("ImportResultsHost")
        self.result_layout = QVBoxLayout(self.result_host)
        self.result_layout.setContentsMargins(0, 0, 4, 0)
        self.result_layout.setSpacing(7)
        self.result_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.result_host)
        root.addWidget(self.scroll, 1)
        self._show_empty_results("选择或拖入压缩包后，可加入的 mod 会显示在这里")

        footer = QHBoxLayout()
        self.selection_label = QLabel("尚未解析内容")
        self.selection_label.setObjectName("Hint")
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_import = QPushButton("导入所选")
        self.btn_import.setProperty("accent", "primary")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self.confirm_import)
        footer.addWidget(self.selection_label, 1)
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_import)
        root.addLayout(footer)

    def _worker_running(self):
        return self._worker is not None and self._worker.isRunning()

    def _show_empty_results(self, text):
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        empty = QLabel(text)
        empty.setObjectName("ImportEmpty")
        empty.setAlignment(Qt.AlignCenter)
        empty.setWordWrap(True)
        empty.setMinimumHeight(130)
        self.result_layout.addWidget(empty)

    def _clear_results(self):
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def choose_archives(self):
        if self._worker_running():
            return
        files, _selected_filter = QFileDialog.getOpenFileNames(
            None, "选择压缩包", "", "压缩包 (*.zip *.7z *.rar)")
        if files:
            self.start_analysis(files)

    def start_analysis(self, paths):
        if self._worker_running():
            return
        valid = [os.path.abspath(path) for path in paths
                 if os.path.isfile(path) and importer.supported_ext(path)]
        if not valid:
            QMessageBox.warning(self, "格式不支持", "请选择 ZIP、7z 或 RAR 压缩包")
            return
        needs_external = any(
            path.lower().endswith((".7z", ".rar")) for path in valid)
        if needs_external and self.main.ensure_archiver() is None:
            self.status_label.setText("需要解压组件")
            self.status_meta.setText("未选择 7z / RAR 解压程序")
            return
        importer.cleanup_staged(self._batch)
        self._batch = None
        self.imported = []
        self.duplicate_count = 0
        self._clear_results()
        self._show_empty_results("正在解压并解析压缩包，请稍候…")
        self._set_busy(True, "analyze")
        self.status_label.setText("正在读取 %d 个压缩包…" % len(valid))
        self.status_meta.setText("")
        self.drop_zone.title.setText("正在解压并解析…")
        self.drop_zone.hint.setText("完成后会在下方列出可加入的 mod")
        self.result_title.setText("可加入的 Mod")
        self.selection_label.setText("正在解析内容")

        worker = ImportAnalyzeWorker(
            self.main.library, valid,
            archiver_info=self.main.archiver, parent=self)
        self._worker = worker
        worker.log.connect(lambda text: self.status_label.setText(str(text)))
        worker.progress.connect(self._on_analysis_progress)
        worker.done.connect(self._on_analysis_done)
        worker.error.connect(self._on_analysis_error)
        worker.finished.connect(lambda w=worker: self._release_worker(w))
        worker.start()

    def _on_analysis_progress(self, done, total, text):
        self.status_label.setText(text)
        self.status_meta.setText("%d / %d" % (done, total))

    def _on_analysis_done(self, batch):
        self._batch = batch
        candidates = batch.get("candidates", [])
        self.duplicate_count = int(batch.get("duplicate_count") or 0)
        self._clear_results()
        for index, candidate in enumerate(candidates):
            self.result_layout.addWidget(self._candidate_row(index, candidate))
        self.result_layout.addStretch(1)
        selectable = sum(1 for c in candidates if self._selectable(c))
        parse_errors = sum(1 for c in candidates if c.get("parse_error"))
        self.drop_zone.title.setText("重新选择压缩包")
        self.drop_zone.hint.setText("点击打开，或拖入新的压缩包替换当前结果")
        self.result_title.setText("可加入的 Mod · %d" % selectable)
        self.status_label.setText(
            "解析完成：%d 个可导入，%d 个重复项已自动跳过"
            % (selectable, self.duplicate_count))
        if parse_errors:
            self.status_label.setText(
                self.status_label.text() + "，%d 个文件无法解析" % parse_errors)
        self.status_meta.setText("默认全选" if selectable else "没有新增可导入项")
        self.btn_all.setEnabled(selectable > 0)
        self.btn_none.setEnabled(selectable > 0)
        self._set_busy(False)
        self._refresh_selection()

    def _on_analysis_error(self, message):
        self._batch = None
        self._show_empty_results("未能解析这个压缩包，请检查文件是否完整")
        self.status_label.setText("解析失败")
        self.status_meta.setText(str(message)[:180])
        self.drop_zone.title.setText("点击选择压缩包")
        self.drop_zone.hint.setText("也可以将 ZIP / 7z / RAR 直接拖到这里")
        self.selection_label.setText("尚未解析内容")
        self._set_busy(False)
        QMessageBox.warning(self, "导入失败", str(message))

    @staticmethod
    def _selectable(candidate):
        return not candidate.get("duplicate_reason") and not candidate.get("parse_error")

    def _candidate_row(self, index, candidate):
        row = QFrame()
        row.setObjectName("ImportCandidate")
        row.setProperty("duplicate", bool(candidate.get("duplicate_reason")
                                          or candidate.get("parse_error")))
        h = QHBoxLayout(row)
        h.setContentsMargins(11, 8, 12, 8)
        h.setSpacing(10)

        check = QCheckBox()
        check.setObjectName("ImportSelect")
        check.setChecked(bool(candidate.get("selected")))
        check.setEnabled(self._selectable(candidate))
        check.stateChanged.connect(
            lambda state, item=candidate: self._candidate_toggled(item, state))
        h.addWidget(check)

        thumb = QLabel()
        thumb.setObjectName("ImportThumb")
        thumb.setFixedSize(78, 44)
        thumb.setAlignment(Qt.AlignCenter)
        preview = candidate.get("preview") or ""
        pixmap = QPixmap(preview) if preview else QPixmap()
        if pixmap.isNull():
            pixmap = theme.thumb_pixmap(78, 44, candidate.get("category"))
        pixmap = pixmap.scaled(
            78, 44, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        thumb.setPixmap(util.rounded_pixmap(pixmap, 7))
        h.addWidget(thumb)

        info = QVBoxLayout()
        info.setSpacing(2)
        title = QLabel(candidate.get("title") or candidate.get("stem") or "未命名 mod")
        title.setObjectName("ImportCandidateTitle")
        title.setToolTip(title.text())
        title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        meta_text = "%s / %s · %s" % (
            candidate.get("category") or "未分类",
            candidate.get("item") or "—",
            util.fmt_size(candidate.get("size") or 0))
        meta = QLabel(meta_text)
        meta.setObjectName("ImportCandidateMeta")
        source = QLabel("%s  ·  %s%s" % (
            candidate.get("archive_name") or "",
            candidate.get("stem") or "",
            candidate.get("suffix") or ""))
        source.setObjectName("ImportCandidateSource")
        source.setToolTip(source.text())
        info.addWidget(title)
        info.addWidget(meta)
        info.addWidget(source)
        h.addLayout(info, 1)

        reason = candidate.get("duplicate_reason") or ""
        if not reason and candidate.get("parse_error"):
            reason = "无法解析"
        if reason:
            status_text = reason
            if candidate.get("duplicate_of"):
                status_text += "\n%s" % candidate["duplicate_of"]
            badge = QLabel(status_text)
            badge.setObjectName("ImportDuplicate")
            badge.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            badge.setWordWrap(True)
            badge.setMaximumWidth(190)
            if candidate.get("parse_error"):
                badge.setToolTip(candidate["parse_error"])
            h.addWidget(badge)
        else:
            tag = QLabel("可导入")
            tag.setObjectName("ImportReady")
            tag.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            h.addWidget(tag)
        return row

    def _candidate_toggled(self, candidate, state):
        candidate["selected"] = bool(state)
        self._refresh_selection()

    def _set_all(self, selected):
        for candidate in (self._batch or {}).get("candidates", []):
            if self._selectable(candidate):
                candidate["selected"] = bool(selected)
        # 重新渲染让复选框与候选状态保持一致
        batch = self._batch
        if batch:
            self._on_analysis_done(batch)

    def _refresh_selection(self):
        candidates = (self._batch or {}).get("candidates", [])
        selected = sum(1 for c in candidates if c.get("selected") and self._selectable(c))
        self.selection_label.setText("已选择 %d 个 mod" % selected)
        self.btn_import.setText("导入所选（%d）" % selected)
        self.btn_import.setEnabled(selected > 0 and not self._worker_running())

    def _set_busy(self, busy, kind=""):
        has_selectable = any(
            self._selectable(c)
            for c in (self._batch or {}).get("candidates", []))
        self.drop_zone.setEnabled(not busy)
        self.btn_all.setEnabled(not busy and has_selectable)
        self.btn_none.setEnabled(not busy and has_selectable)
        self.btn_cancel.setEnabled(not busy)
        self.btn_import.setEnabled(not busy and bool(
            [c for c in (self._batch or {}).get("candidates", [])
             if c.get("selected") and self._selectable(c)]))
        self.scroll.setEnabled(not busy)
        self.progress.setVisible(busy)
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(100 if kind == "commit" else 0)

    def confirm_import(self):
        if self._worker_running() or not self._batch:
            return
        selected = [c for c in self._batch.get("candidates", [])
                    if c.get("selected") and self._selectable(c)]
        if not selected:
            return
        self._set_busy(True, "commit")
        self.status_label.setText("正在写入 mod 库…")
        self.status_meta.setText("0 / %d" % len(selected))
        self.drop_zone.title.setText("正在导入所选 mod…")
        self.drop_zone.hint.setText("请稍候，完成后窗口会自动关闭")
        worker = ImportCommitWorker(
            self.main.library, self._batch, selected, self)
        self._worker = worker
        worker.progress.connect(self._on_commit_progress)
        worker.done.connect(self._on_commit_done)
        worker.error.connect(self._on_commit_error)
        worker.finished.connect(lambda w=worker: self._release_worker(w))
        worker.start()

    def _on_commit_progress(self, done, total, title):
        self.status_label.setText("正在导入：%s" % title)
        self.status_meta.setText("%d / %d" % (done, total))
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(done)

    def _on_commit_done(self, records):
        self.imported = list(records or [])
        importer.cleanup_staged(self._batch)
        self._batch = None
        self.accept()

    def _on_commit_error(self, message):
        self.status_label.setText("导入失败")
        self.status_meta.setText(str(message)[:180])
        self.drop_zone.title.setText("重新选择压缩包")
        self.drop_zone.hint.setText("点击打开，或拖入新的压缩包替换当前结果")
        self._set_busy(False)
        self._refresh_selection()
        QMessageBox.warning(self, "导入失败", str(message))

    def _release_worker(self, worker):
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()
        if self._batch:
            self._set_busy(False)
            self._refresh_selection()

    def reject(self):
        if self._worker_running():
            QMessageBox.information(self, "正在处理", "请等待当前导入任务完成")
            return
        importer.cleanup_staged(self._batch)
        self._batch = None
        super().reject()

    def closeEvent(self, event):
        if self._worker_running():
            QMessageBox.information(self, "正在处理", "请等待当前导入任务完成")
            event.ignore()
            return
        importer.cleanup_staged(self._batch)
        self._batch = None
        super().closeEvent(event)


# ---------------------------------------------------------------- 工坊搜索下载
class WorkshopDialog(AppDialog):
    def __init__(self, main):
        super().__init__(main, "工坊下载")
        self.main = main
        self.resize(860, 740)
        self.setMinimumSize(700, 620)
        self._worker = None
        self._parent_checked = set()   # 已做过父合集反查的物品 id
        self._parent_worker = None
        self._unsupported_links = []
        self._unsupported_report_shown = False

        root = QVBoxLayout(self.content)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(10)
        source_panel = QFrame()
        source_panel.setObjectName("WorkshopInputPanel")
        source_layout = QVBoxLayout(source_panel)
        source_layout.setContentsMargins(15, 13, 15, 14)
        source_layout.setSpacing(9)

        source_title = QLabel("粘贴创意工坊链接或物品 ID")
        source_title.setObjectName("WorkshopSectionTitle")
        source_layout.addWidget(source_title)
        source_hint = QLabel("每行一个链接或 ID；支持合集链接，会自动展开并列出子物品。")
        source_hint.setObjectName("Hint")
        source_hint.setWordWrap(True)
        source_layout.addWidget(source_hint)

        self.link_edit = QPlainTextEdit()
        self.link_edit.setObjectName("LinkInput")
        self.link_edit.setFrameShape(QFrame.NoFrame)
        self.link_edit.setMinimumHeight(112)
        self.link_edit.setMaximumHeight(150)
        self.link_edit.setPlaceholderText(
            "https://steamcommunity.com/sharedfiles/filedetails/?id=xxxxxxxxx\n或直接输入 ID")
        source_layout.addWidget(self.link_edit)

        source_actions = QHBoxLayout()
        source_actions.setSpacing(9)
        input_note = QLabel("不会自动下载；解析后可逐项勾选。")
        input_note.setObjectName("Hint")
        parse_btn = QPushButton("解析链接")
        parse_btn.setMinimumHeight(36)
        parse_btn.clicked.connect(self.parse_links)
        source_actions.addWidget(input_note, 1)
        source_actions.addWidget(parse_btn)
        source_layout.addLayout(source_actions)
        root.addWidget(source_panel)

        list_head = QHBoxLayout()
        list_head.setContentsMargins(2, 2, 2, 0)
        list_title = QLabel("待下载物品")
        list_title.setObjectName("LogTitle")
        list_hint = QLabel("双击条目可立即开始下载所选内容")
        list_hint.setObjectName("Hint")
        list_head.addWidget(list_title)
        list_head.addStretch(1)
        list_head.addWidget(list_hint)
        root.addLayout(list_head)

        self.link_list = QListWidget()
        self.link_list.setObjectName("WorkshopLinkList")
        self.link_list.itemDoubleClicked.connect(lambda _it: self.download_selected())
        root.addWidget(self.link_list, 1)
        self.link_list.itemChanged.connect(lambda _it: self._refresh_download_button())

        # ---- 底部：进度 + 按钮 ----
        progress_panel = QFrame()
        progress_panel.setObjectName("DownloadProgressPanel")
        progress_layout = QVBoxLayout(progress_panel)
        progress_layout.setContentsMargins(12, 9, 12, 10)
        progress_layout.setSpacing(6)
        progress_head = QHBoxLayout()
        progress_head.setContentsMargins(0, 0, 0, 0)
        self.progress_title = QLabel("等待任务")
        self.progress_title.setObjectName("ProgressTitle")
        self.progress_meta = QLabel("准备就绪")
        self.progress_meta.setObjectName("ProgressMeta")
        self.progress_meta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        progress_head.addWidget(self.progress_title)
        progress_head.addStretch(1)
        progress_head.addWidget(self.progress_meta)
        progress_layout.addLayout(progress_head)
        self.progress = AnimatedProgressBar()
        self.progress.setObjectName("DownloadProgress")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        progress_layout.addWidget(self.progress)
        self.progress_current = QLabel("解析链接后，任务阶段与当前模组会显示在这里")
        self.progress_current.setObjectName("ProgressCurrent")
        self.progress_current.setWordWrap(True)
        progress_layout.addWidget(self.progress_current)

        log_head = QHBoxLayout()
        log_head.setContentsMargins(2, 2, 2, 0)
        log_title = QLabel("任务日志")
        log_title.setObjectName("LogTitle")
        log_hint = QLabel("实时显示解析、下载通道、校验与入库进度")
        log_hint.setObjectName("Hint")
        log_head.addWidget(log_title)
        log_head.addStretch(1)
        log_head.addWidget(log_hint)
        self.log_box = QPlainTextEdit()
        self.log_box.setObjectName("TaskLog")
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(125)
        self.log_box.setMaximumHeight(180)
        self.log_box.document().setMaximumBlockCount(500)
        self.log_box.setPlaceholderText("任务开始后，这里会逐条显示当前正在执行的步骤…")
        btns = QHBoxLayout()
        self.btn_download = QPushButton("下载所选（地图等自动启用，外观类默认禁用）")
        self.btn_download.setProperty("accent", "primary")
        self.btn_download.setEnabled(False)
        self.btn_download.clicked.connect(self.download_selected)
        btn_open = QPushButton("打开工坊页")
        btn_open.clicked.connect(self.open_page)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.reject)
        btns.addWidget(self.btn_download, 1)
        btns.addWidget(btn_open)
        btns.addWidget(btn_close)
        root.addWidget(progress_panel)
        root.addLayout(log_head)
        root.addWidget(self.log_box)
        root.addLayout(btns)

    # ---------- 任务状态 / 日志 ----------
    def _append_log(self, message):
        stamp = time.strftime("%H:%M:%S")
        lines = str(message).replace("\r", "").splitlines() or [""]
        for line in lines:
            self.log_box.appendPlainText("[%s] %s" % (stamp, line[:500]))
        bar = self.log_box.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_progress(self, value, title, meta="", current=""):
        self.progress.setRange(0, 100)
        self.progress.setValue(max(0, min(100, int(value))))
        self.progress_title.setText(title)
        self.progress_meta.setText(meta)
        if current:
            self.progress_current.setText(current)

    def _set_progress_busy(self, title, current, meta="处理中"):
        self.progress.setRange(0, 0)
        self.progress_title.setText(title)
        self.progress_meta.setText(meta)
        self.progress_current.setText(current)

    def _set_progress_idle(self, title="等待任务", current="准备就绪", meta=""):
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_title.setText(title)
        self.progress_meta.setText(meta)
        self.progress_current.setText(current)

    # ---------- 链接解析 ----------
    def parse_links(self):
        text = self.link_edit.toPlainText()
        ids = steam_api.extract_ids(text)
        if not ids:
            QMessageBox.information(self, "解析", "未找到有效的物品 ID")
            return
        self._parse_ids = ids
        self._unsupported_links = []
        self._unsupported_report_shown = False
        self.link_list.clear()
        self.btn_download.setEnabled(False)
        self._append_log("正在解析链接：识别到 %d 个物品 ID" % len(ids))
        self._set_progress_busy("正在解析链接", "读取工坊物品详情与合集结构…",
                                "%d 个输入项" % len(ids))
        self._details_worker = DetailsWorker(ids, resolve_collections=True)
        self._details_worker.status.connect(self._append_log)
        self._details_worker.done.connect(self._on_details)
        self._details_worker.error.connect(self._on_details_error)
        self._details_worker.start()

    @staticmethod
    def _workshop_app_id(detail):
        raw = (detail or {}).get("consumer_app_id")
        if raw in (None, ""):
            raw = (detail or {}).get("consumer_appid")
        try:
            return int(raw) if raw not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def _collect_unsupported_link(self, detail):
        appid = self._workshop_app_id(detail)
        if appid in (None, 0, L4D2_APPID):
            return False
        item_id = str(detail.get("publishedfileid") or "?")
        title = str(detail.get("title") or item_id)
        self._unsupported_links.append({
            "id": item_id,
            "title": title,
            "app_id": appid,
            "app_name": WORKSHOP_APP_NAMES.get(appid, "其他游戏"),
        })
        self._append_log("不支持：%s (%s) 属于 %s（AppID %s），不是 Left 4 Dead 2（AppID 550）"
                         % (title, item_id, WORKSHOP_APP_NAMES.get(appid, "其他游戏"), appid))
        return True

    def _show_unsupported_links(self):
        if self._unsupported_report_shown or not self._unsupported_links:
            return
        self._unsupported_report_shown = True
        items = list(self._unsupported_links)

        def _show():
            detail = "\n".join(
                "· %s (%s)\n  属于 %s（AppID %s）"
                % (x["title"], x["id"], x["app_name"], x["app_id"])
                for x in items[:8])
            if len(items) > 8:
                detail += "\n…另有 %d 个不支持的物品" % (len(items) - 8)
            QMessageBox.critical(
                self, "不是 L4D2 模组",
                "以下工坊物品不属于 Left 4 Dead 2（AppID 550），已停止处理：\n\n%s"
                % detail)

        QTimer.singleShot(0, _show)

    def _on_details(self, details):
        child_ids = []   # 合集的子物品（需要二次展开）
        self._pending_collection = None
        self._append_log("工坊详情读取完成：收到 %d 项结果，正在解析合集内容" % len(details))
        invalid = 0
        for d in details:
            if self._collect_unsupported_link(d):
                continue
            if d.get("result") != 1:
                invalid += 1
                self._append_log("无法解析物品 %s：工坊返回 result=%s"
                                 % (d.get("publishedfileid") or "?", d.get("result")))
                continue
            children = steam_api.collection_children(d)
            if children:
                child_ids.extend(children)
                self._pending_collection = {
                    "workshop_id": str(d.get("publishedfileid")),
                    "name": str(d.get("title") or "未命名合集"),
                    "children": [str(c) for c in children]}
                self._append_link_item("合集说明：%s · 已识别 %d 个子物品"
                                       % (d.get("title", d.get("publishedfileid")), len(children)),
                                       d.get("publishedfileid"), children=True)
                self._append_log("正在解析合集内容：《%s》 · 发现 %d 个子物品"
                                 % (d.get("title") or d.get("publishedfileid"), len(children)))
            else:
                # 普通物品：只在这里添加一次，不再进入二次展开
                self._append_link_item("%s（%.1f MB）" % (d.get("title", "?"), int(d.get("file_size") or 0) / 1048576.0),
                                       d.get("publishedfileid"),
                                       title=str(d.get("title") or ""))
                self._maybe_find_parent(str(d.get("publishedfileid")), str(d.get("title") or ""))
        # 子物品去重后展开
        uniq = []
        for x in child_ids:
            if x not in uniq:
                uniq.append(x)
        if uniq:
            self._append_log("正在获取合集部件信息：共 %d 个唯一子物品" % len(uniq))
            self._set_progress_busy("正在展开合集", "读取 %d 个部件详情…" % len(uniq),
                                    "已识别 %d 个" % len(uniq))
            self._child_worker = DetailsWorker(uniq)
            self._child_worker.done.connect(self._on_children)
            self._child_worker.error.connect(self._on_details_error)
            self._child_worker.start()
        else:
            identified = sum(1 for i in range(self.link_list.count())
                             if not (self.link_list.item(i).data(Qt.UserRole) or {}).get("collection"))
            checked = self._link_checked_count()
            self.btn_download.setEnabled(bool(checked))
            note = "已识别 %d 个模组 · 已勾选 %d 个" % (identified, checked)
            if invalid:
                note += " · %d 个无法读取" % invalid
            self._set_progress(0, "解析完成", note, "可勾选需要下载的模组")
            self._append_log("链接解析完成：%s" % note)
            self._show_unsupported_links()

    def _on_children(self, details):
        valid_count = 0
        for d in details:
            if self._collect_unsupported_link(d):
                continue
            if d.get("result") != 1:
                self._append_log("无法读取合集部件 %s：result=%s"
                                 % (d.get("publishedfileid") or "?", d.get("result")))
                continue
            if steam_api.collection_children(d):
                self._append_log("跳过嵌套合集：%s" % (d.get("title") or d.get("publishedfileid")))
                continue  # 嵌套合集忽略
            self._append_link_item("%s（%.1f MB）" % (d.get("title", "?"), int(d.get("file_size") or 0) / 1048576.0),
                                   d.get("publishedfileid"),
                                   title=str(d.get("title") or ""))
            valid_count += 1
        checked = self._link_checked_count()
        self.btn_download.setEnabled(bool(checked))
        self._set_progress(0, "解析完成", "已勾选 %d 个" % checked,
                           "合集展开完成；已在库条目已自动取消勾选")
        self._append_log("合集解析完成：%d 个部件可下载，当前勾选 %d 个"
                         % (valid_count, checked))
        self._show_unsupported_links()

    def _on_details_error(self, error):
        self._append_log("链接解析失败：%s" % error)
        self._set_progress_idle("解析失败", error, "请检查链接或网络后重试")
        self._refresh_download_button(force=True)
        QMessageBox.warning(self, "解析失败", error)

    def _append_link_item(self, text, wid, children=False, title=""):
        wid = str(wid)
        # 同一物品只添加一次
        for i in range(self.link_list.count()):
            d = self.link_list.item(i).data(Qt.UserRole) or {}
            if d.get("id") == wid:
                return
        existing = None if children else self.main.library.find_existing_workshop(wid)
        label = text + (" · 已在库" if existing else "")
        it = QListWidgetItem(label)
        if children:
            # 合集摘要只用于说明来源，不参与勾选和下载。
            it.setFlags(Qt.ItemIsEnabled)
            it.setToolTip("下载时只处理下方识别出的合集中子物品")
        else:
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked if existing else Qt.Checked)
            if existing:
                it.setToolTip("该模组已在本地库中（%s），下载时会自动跳过"
                              % (existing.get("file") or existing.get("title") or wid))
                self._append_log("已在库，已取消勾选：%s (%s)"
                                 % (existing.get("title") or title or wid, wid))
        it.setData(Qt.UserRole, {
            "id": wid,
            "collection": children,
            "title": title or (existing or {}).get("title") or "",
            "existing": bool(existing),
        })
        self.link_list.addItem(it)

    # ---------- 下载 ----------
    def _link_checked_count(self):
        return sum(
            1 for i in range(self.link_list.count())
            if self.link_list.item(i).checkState() == Qt.Checked
            and not (self.link_list.item(i).data(Qt.UserRole) or {}).get("collection"))

    def _refresh_download_button(self, force=False):
        if not force and self._worker and self._worker.isRunning():
            return
        count = len(self._selected_ids())
        self.btn_download.setEnabled(bool(count))
        if self.progress_title.text() == "解析完成":
            self.progress_meta.setText("已勾选 %d 个" % count)

    def _mark_workshop_items_existing(self, ids):
        ids = set(str(wid) for wid in ids if wid)
        if not ids:
            return
        for index in range(self.link_list.count()):
            item = self.link_list.item(index)
            data = item.data(Qt.UserRole) or {}
            if str(data.get("id") or "") not in ids:
                continue
            data["existing"] = True
            item.setData(Qt.UserRole, data)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip("该模组已在本地库中，下载时会自动跳过")
            if "已在库" not in item.text():
                item.setText(item.text() + " · 已在库")
        self._refresh_download_button(force=True)

    def _selected_ids(self):
        ids = []
        for i in range(self.link_list.count()):
            it = self.link_list.item(i)
            d = it.data(Qt.UserRole)
            if d and it.checkState() == Qt.Checked and not d.get("collection") \
                    and not d.get("existing"):
                ids.append(d["id"])
        return ids

    def download_selected(self):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "下载", "请先粘贴链接并解析，再勾选要下载的物品")
            return
        if gamemod.is_l4d2_running():
            QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再下载导入 mod")
            return
        collection = None
        col = getattr(self, "_pending_collection", None)
        if col:
            collection = {"cid": "ws_" + col["workshop_id"], "name": col["name"],
                          "workshop_id": col["workshop_id"]}
        self._start_download(ids, collection)

    def _start_download(self, ids, collection=None):
        self._append_log("下载前复查本地库：共选择 %d 个模组" % len(ids))
        pending = []
        skipped = []
        for wid in ids:
            existing = self.main.library.find_existing_workshop(wid)
            if existing:
                skipped.append((wid, existing.get("title") or existing.get("file") or wid))
            elif str(wid) not in pending:
                pending.append(str(wid))
        if skipped:
            self._append_log("本地库已存在，跳过 %d 个：%s"
                             % (len(skipped), "、".join("%s (%s)" % (name, wid)
                                                       for wid, name in skipped[:8])))
        if not pending:
            self._set_progress(100, "无需下载", "所选模组均已在库",
                               "没有重复写入本地文件")
            self._append_log("任务结束：所选模组均已在库，无需下载")
            QMessageBox.information(self, "无需下载", "所选模组均已在库，已自动跳过。")
            return

        self.btn_download.setEnabled(False)
        self._set_progress_busy("正在准备下载", "检查下载通道与待下载队列…",
                                "%d 个待下载" % len(pending))
        self._append_log("准备下载 %d 个新模组；总进度将合并计算所有勾选项" % len(pending))
        worker = DownloadWorker(self.main.store, self.main.library, pending,
                                collection=collection)
        worker.preflight_skipped = skipped
        self._worker = worker
        worker.log.connect(self._append_log)
        worker.progress.connect(self._on_dl_progress)
        worker.done.connect(lambda recs, w=worker: self._on_dl_done(recs, w))
        worker.error.connect(lambda e, w=worker: self._on_dl_error(e, w))
        worker.finished.connect(lambda w=worker: self._finish_download_worker(w))
        worker.start()

    def _on_dl_progress(self, percent, phase, current):
        self._set_progress(percent, phase, "所有勾选项合并计算", current)

    def _finish_download_worker(self, worker):
        worker.deleteLater()
        if self._worker is worker:
            self._worker = None

    def _on_dl_done(self, recs, worker=None):
        skipped = list(getattr(worker, "preflight_skipped", []) or [])
        skipped += list(getattr(worker, "skipped", []) or [])
        failures = list(getattr(worker, "failures", []) or [])
        installed_ids = [r.get("workshop_id") for r in recs]
        installed_ids += [x.get("id") if isinstance(x, dict) else x[0] for x in skipped]
        self._mark_workshop_items_existing(installed_ids)
        self._set_progress(100, "任务完成",
                           "已导入 %d · 跳过 %d · 失败 %d"
                           % (len(recs), len(skipped), len(failures)),
                           "所有勾选模组均已处理")
        self._refresh_download_button(force=True)
        names = "、".join(r["title"] for r in recs) if recs else "无"
        self._append_log("任务汇总：已导入 %d 个，跳过 %d 个，失败 %d 个"
                         % (len(recs), len(skipped), len(failures)))
        if recs:
            self._append_log("本次导入：%s" % names)
        if failures:
            detail = "\n".join("· %s (%s)：%s" % (x["title"], x["id"], x["error"])
                               for x in failures[:8])
            QMessageBox.warning(
                self, "部分下载未完成",
                "已导入 %d 个 mod；失败 %d 个。\n\n%s"
                % (len(recs), len(failures), detail))
        else:
            QMessageBox.information(
                self, "下载完成",
                "已导入 %d 个 mod。\n\n%s%s"
                % (len(recs), names,
                   ("\n\n已跳过库内已有的 %d 个模组。" % len(skipped)) if skipped else ""))
        self.main.refresh_all()

    def _on_dl_error(self, e, worker=None):
        self._set_progress(0, "下载任务失败", "发生未预期错误", e)
        self._refresh_download_button(force=True)
        self._append_log("下载失败：" + e)
        QMessageBox.warning(self, "下载失败", e)

    # ---------- 父合集识别（粘贴单个部件链接时） ----------
    def _maybe_find_parent(self, wid, title):
        if wid in self._parent_checked or self._pending_collection:
            return
        self._parent_checked.add(wid)
        self._parent_worker = ParentCollectionWorker(wid, title)
        self._parent_worker.found.connect(self._on_parent_found)
        self._parent_worker.notfound.connect(self._on_parent_notfound)
        self._parent_worker.start()

    def _on_parent_notfound(self, wid):
        for i in range(self.link_list.count()):
            it = self.link_list.item(i)
            d = it.data(Qt.UserRole) or {}
            if d.get("id") == wid:
                text = it.text()
                if re.search(r"\b(pt|part)\s*\d+", text.lower()) \
                        or re.search(r"第\s*[一二三四五六七八九十\d]+\s*[部章分]", text):
                    self._append_log(
                        "提示：该物品疑似地图分部（pt/part），未自动找到所属合集；"
                        "可粘贴合集链接一次下载全部并自动归组。")
                break

    def _on_parent_found(self, item_id, col_id, col_title, n_children, children_details):
        cur = [(self.link_list.item(i).data(Qt.UserRole) or {}).get("id")
               for i in range(self.link_list.count())]
        if item_id not in cur:
            return
        msg = ("《%s》是合集《%s》的一个部件（共 %d 个子物品）。\n\n要下载整个合集吗？\n"
               "· 已在库中的部件 → 直接归入合集\n"
               "· 缺失部件 → 立即下载并归组\n"
               "· 地图等非冲突类下载后自动启用") % (item_id, col_title, n_children)
        if QMessageBox.question(self, "发现所属合集", msg) != QMessageBox.Yes:
            return
        col = {"cid": "ws_" + col_id, "name": col_title, "workshop_id": col_id,
               "children": [c["id"] for c in children_details]}
        self._download_collection(col, children_details)

    def _download_collection(self, col, children_details):
        store = self.main.store
        to_download = []
        grouped = []
        for c in children_details:
            m = self.main.library.find_existing_workshop(c["id"])
            if m:
                actual = store.get_mod(m.get("file") or "")
                if actual:
                    actual["collection"] = col["cid"]
                    grouped.append(actual["file"])
                elif m.get("file"):
                    grouped.append(m["file"])
            else:
                to_download.append(str(c["id"]))
        info = {"name": col["name"], "workshop_id": col["workshop_id"],
                "files": list(dict.fromkeys(grouped))}
        old = store.get_collection(col["cid"])
        if old:
            info["files"] = list(dict.fromkeys(old.get("files", []) + info["files"]))
        store.upsert_collection(col["cid"], info)
        store.save_library()
        self._append_log("合集《%s》：已在库 %d 个（已归组），待下载 %d 个"
                         % (col["name"], len(grouped), len(to_download)))
        if to_download:
            if gamemod.is_l4d2_running():
                QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再下载导入 mod")
                return
            self._start_download(to_download, col)
        else:
            QMessageBox.information(self, "合集", "合集内部件均已在库，已全部归组。")
        self.main.refresh_items()
        self.main.refresh_cards()

    def open_page(self):
        ids = self._selected_ids()
        if ids:
            gamemod.open_workshop_page(ids[0])

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
        event.accept()


# ---------------------------------------------------------------- 迁移向导
class MigrateDialog(AppDialog):
    def __init__(self, main):
        super().__init__(main, "迁移工坊订阅 mod")
        self.main = main
        self.resize(620, 520)
        v = QVBoxLayout(self.content)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(10)
        hint = QLabel(
            "addons/workshop/ 下的订阅 mod 会在每次进游戏时被 Steam 重新检测，拖慢加载。\n"
            "迁移会把 vpk 前移一级到 addons 顶层并保留启用状态；完成后建议在 Steam 中退订对应物品\n"
            "（双击已迁移条目可打开其工坊页），否则 Steam 可能把文件重新同步回 workshop 目录。")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        v.addWidget(hint)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["物品", "文件"])
        self.tree.setColumnWidth(0, 380)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        v.addWidget(self.tree, 1)

        self.moved_tree = QTreeWidget()
        self.moved_tree.setHeaderLabels(["已迁移（双击打开工坊页退订）", "状态"])
        self.moved_tree.setColumnWidth(0, 380)
        self.moved_tree.setMaximumHeight(140)
        self.moved_tree.itemDoubleClicked.connect(self._open_moved)
        v.addWidget(self.moved_tree)

        btns = QHBoxLayout()
        b_all = QPushButton("全选")
        b_all.clicked.connect(lambda: self._set_all(Qt.Checked))
        b_none = QPushButton("全不选")
        b_none.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        b_page = QPushButton("打开工坊页")
        b_page.clicked.connect(self._open_selected)
        self.btn_go = QPushButton("迁移所选")
        self.btn_go.setProperty("accent", "primary")
        self.btn_go.clicked.connect(self.do_migrate)
        b_close = QPushButton("关闭")
        b_close.clicked.connect(self.reject)
        btns.addWidget(b_all)
        btns.addWidget(b_none)
        btns.addWidget(b_page)
        btns.addStretch(1)
        btns.addWidget(self.btn_go)
        btns.addWidget(b_close)
        v.addLayout(btns)
        self.reload()

    def reload(self):
        self.tree.clear()
        for it in self.main.library.workshop_items():
            node = QTreeWidgetItem(["(ID %s) %s" % (it["id"] or "?", it["file"]), it["file"]])
            node.setFlags(node.flags() | Qt.ItemIsUserCheckable)
            node.setCheckState(0, Qt.Checked)
            node.setData(0, Qt.UserRole, it)
            if it["jpg"]:
                pm = QPixmap(it["jpg"])
                if not pm.isNull():
                    node.setIcon(0, pm.scaled(48, 27, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.tree.addTopLevelItem(node)

    def _set_all(self, state):
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(0, state)

    def _checked(self):
        out = []
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.checkState(0) == Qt.Checked:
                out.append(it.data(0, Qt.UserRole)["file"])
        return out

    def do_migrate(self):
        files = self._checked()
        if not files:
            QMessageBox.information(self, "迁移", "请先勾选要迁移的物品")
            return
        if gamemod.is_l4d2_running():
            QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再迁移")
            return
        self.btn_go.setEnabled(False)
        self._worker = MigrateWorker(self.main.library, files)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(lambda e: (QMessageBox.warning(self, "迁移失败", e), self.btn_go.setEnabled(True)))
        self._worker.start()

    def _on_done(self, moved, errors):
        self.btn_go.setEnabled(True)
        for f, enabled in moved:
            it = self.main.library.workshop_items()
            node = QTreeWidgetItem([f, "已迁移 · %s" % ("启用" if enabled else "禁用")])
            stem = os.path.splitext(f)[0]
            node.setData(0, Qt.UserRole, stem if stem.isdigit() else "")
            self.moved_tree.addTopLevelItem(node)
        if errors:
            msg = "\n".join("%s: %s" % (f, r) for f, r in errors[:10])
            QMessageBox.warning(self, "迁移完成（部分失败）", "成功 %d 个，失败 %d 个：\n%s" % (len(moved), len(errors), msg))
        elif moved:
            QMessageBox.information(self, "迁移完成", "已迁移 %d 个 mod 到 addons 顶层。\n建议退订对应物品，避免 Steam 重新同步。" % len(moved))
        self.reload()
        self.main.refresh_all()

    def _open_moved(self, item, _col):
        wid = item.data(0, Qt.UserRole)
        if wid:
            gamemod.open_workshop_page(wid)

    def _open_selected(self):
        sel = self.tree.currentItem()
        if sel:
            wid = (sel.data(0, Qt.UserRole) or {}).get("id")
            if wid:
                gamemod.open_workshop_page(wid)


# ---------------------------------------------------------------- 归类
ITEM_SUGGESTIONS = {
    "角色": sorted(set(SURVIVOR_NAMES.values())) + ["整体替换"],
    "特感": sorted(set(SPECIAL_NAMES.values())),
    "枪械": sorted(set(WEAPON_SEG_NAMES.values())),
    "近战": sorted(set(MELEE_NAMES.values())),
    "医疗品": sorted(set(MED_NAMES.values())),
    "投掷": ["燃烧瓶", "土制炸弹", "胆汁罐"],
}


class CategoryDialog(AppDialog):
    def __init__(self, main, rec):
        super().__init__(main, "修改分类 - %s" % (rec.get("alias") or rec["title"]))
        self.main = main
        self.rec = rec
        v = QVBoxLayout(self.content)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(10)
        form = QFormLayout()
        self.cat_combo = QComboBox()
        self.cat_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cat_combo.setMinimumContentsLength(18)
        self.cat_combo.setMaximumWidth(480)
        self.cat_combo.addItems(CATEGORIES)
        self.cat_combo.setCurrentText(rec["category"])
        self.item_combo = QComboBox()
        self.item_combo.setEditable(True)
        self.item_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.item_combo.setMinimumContentsLength(18)
        self.item_combo.setMaximumWidth(480)
        self._fill_items()
        self.cat_combo.currentTextChanged.connect(lambda _s: self._fill_items())
        form.addRow("类别", self.cat_combo)
        form.addRow("具体物品", self.item_combo)
        v.addLayout(form)
        hint = QLabel("同一「类别 + 物品」下的 mod 互相排斥（启用一个自动禁用其余）。\n留空物品表示多项/整体，不参与互斥。")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        v.addWidget(hint)
        btns = QHBoxLayout()
        ok = QPushButton("保存")
        ok.setProperty("accent", "primary")
        ok.clicked.connect(self._save)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        v.addLayout(btns)
        self.setMinimumWidth(480)
        self.setMaximumWidth(680)
        self.resize(560, max(240, self.sizeHint().height()))

    def _fill_items(self):
        cat = self.cat_combo.currentText()
        self.item_combo.clear()
        self.item_combo.addItem("")
        for it in ITEM_SUGGESTIONS.get(cat, []):
            self.item_combo.addItem(it)
        # 补充库内已有的物品名
        for r in self.main.store.mods().values():
            if r["category"] == cat and r["item"] and self.item_combo.findText(r["item"]) < 0:
                self.item_combo.addItem(r["item"])
        self.item_combo.setCurrentText(self.rec["item"] if self.rec["category"] == cat else "")

    def _save(self):
        self.main.library.set_category(
            self.rec["file"], self.cat_combo.currentText(), self.item_combo.currentText().strip())
        self.main.refresh_all()
        self.accept()


# ---------------------------------------------------------------- 详情
class DetailDialog(AppDialog):
    def __init__(self, main, rec):
        super().__init__(main, "mod 详情")
        self.resize(460, 320)
        v = QVBoxLayout(self.content)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(10)
        form = QFormLayout()
        rows = [
            ("显示名", rec.get("title", "")),
            ("别名", rec.get("alias", "") or "-"),
            ("类别 / 物品", "%s / %s" % (rec.get("category", ""), rec.get("item") or "—")),
            ("文件", rec.get("file", "")),
            ("大小", util.fmt_size(rec.get("size", 0))),
            ("工坊 ID", rec.get("workshop_id") or "-"),
            ("来源", rec.get("source", "")),
            ("状态", "启用" if rec.get("enabled") else "禁用"),
        ]
        for k, val in rows:
            lab = QLabel(str(val))
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(QLabel(k + "："), lab)
        v.addLayout(form)
        btns = QHBoxLayout()
        if rec.get("workshop_id"):
            b = QPushButton("打开工坊页")
            b.clicked.connect(lambda: gamemod.open_workshop_page(rec["workshop_id"]))
            btns.addWidget(b)
        b = QPushButton("打开文件位置")
        b.clicked.connect(lambda: main.library.reveal_mod(rec["file"]))
        btns.addWidget(b)
        btns.addStretch(1)
        b_close = QPushButton("关闭")
        b_close.clicked.connect(self.accept)
        btns.addWidget(b_close)
        v.addLayout(btns)
