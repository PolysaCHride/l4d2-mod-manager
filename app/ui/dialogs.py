# -*- coding: utf-8 -*-
"""对话框集合：工坊搜索下载 / 迁移向导 / 章节进图 / 归类 / 设置 / 详情。"""
import os
import re

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QAbstractItemView,
    QHeaderView,
)

from ..core import game as gamemod
from ..core import paths as pathsmod
from ..core import steam_api
from ..core.classify import CATEGORIES, MELEE_NAMES, MED_NAMES, SPECIAL_NAMES, SURVIVOR_NAMES, WEAPON_SEG_NAMES
from . import util
from .workers import (
    DetailsWorker, DownloadWorker, MigrateWorker, ParentCollectionWorker,
    PreviewWorker, SearchWorker,
)

THUMB_W, THUMB_H = 92, 52


# ---------------------------------------------------------------- 工坊搜索下载
class WorkshopDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("工坊下载")
        self.resize(760, 620)
        self._worker = None
        self._search_worker = None
        self._parent_checked = set()   # 已做过父合集反查的物品 id
        self._parent_worker = None
        self._page = 1
        self._last_query = ""
        self._sort = "text"
        self._icons = {}       # id -> QPixmap
        self._previews = {}    # id -> url
        self._preview_threads = []

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # ---- 在线搜索 tab ----
        tab1 = QWidget()
        v1 = QVBoxLayout(tab1)
        bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索创意工坊：名称关键词…")
        self.search_edit.returnPressed.connect(self.do_search)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["相关度", "订阅最多", "最新发布"])
        btn = QPushButton("搜 索")
        btn.clicked.connect(self.do_search)
        bar.addWidget(self.search_edit, 1)
        bar.addWidget(self.sort_combo)
        bar.addWidget(btn)
        v1.addLayout(bar)

        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(lambda _it: self.download_selected())
        v1.addWidget(self.result_list, 1)

        pager = QHBoxLayout()
        self.btn_prev = QPushButton("上一页")
        self.btn_next = QPushButton("下一页")
        self.page_label = QLabel("第 1 页")
        self.page_label.setObjectName("Hint")
        self.btn_prev.clicked.connect(lambda: self.turn_page(-1))
        self.btn_next.clicked.connect(lambda: self.turn_page(1))
        pager.addWidget(self.btn_prev)
        pager.addWidget(self.page_label)
        pager.addWidget(self.btn_next)
        pager.addStretch(1)
        self.result_info = QLabel("")
        self.result_info.setObjectName("Hint")
        pager.addWidget(self.result_info)
        v1.addLayout(pager)
        self.tabs.addTab(tab1, "在线搜索")

        # ---- 粘贴链接 tab ----
        tab2 = QWidget()
        v2 = QVBoxLayout(tab2)
        v2.addWidget(QLabel("粘贴创意工坊链接或物品 ID（每行一个，支持合集链接，自动展开子物品）："))
        self.link_edit = QPlainTextEdit()
        self.link_edit.setPlaceholderText(
            "https://steamcommunity.com/sharedfiles/filedetails/?id=xxxxxxxxx\n或直接输入 ID")
        v2.addWidget(self.link_edit, 1)
        parse_btn = QPushButton("解析链接")
        parse_btn.clicked.connect(self.parse_links)
        self.link_list = QListWidget()
        v2.addWidget(parse_btn)
        v2.addWidget(self.link_list, 1)
        self.tabs.addTab(tab2, "粘贴链接 / ID")

        # ---- 底部：进度 + 按钮 ----
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(110)
        self.log_box.setPlaceholderText("操作日志…")
        btns = QHBoxLayout()
        self.btn_download = QPushButton("下载所选（地图等自动启用，外观类默认禁用）")
        self.btn_download.setProperty("accent", "primary")
        self.btn_download.clicked.connect(self.download_selected)
        btn_open = QPushButton("打开工坊页")
        btn_open.clicked.connect(self.open_page)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.reject)
        btns.addWidget(self.btn_download, 1)
        btns.addWidget(btn_open)
        btns.addWidget(btn_close)
        root.addWidget(self.progress)
        root.addWidget(self.log_box)
        root.addLayout(btns)

    # ---------- 搜索 ----------
    def do_search(self):
        q = self.search_edit.text().strip()
        if not q:
            return
        self._last_query = q
        self._page = 1
        sort = ["text", "mostsub", "mostrecent"][self.sort_combo.currentIndex()]
        self._sort = sort
        self._search(q, 1, sort)

    def turn_page(self, d):
        if not self._last_query:
            return
        self._page = max(1, self._page + d)
        self._search(self._last_query, self._page, self._sort)

    def _search(self, q, page, sort):
        self.result_info.setText("搜索中…")
        self.result_list.clear()
        self._search_worker = SearchWorker(q, page=page, sort=sort)
        self._search_worker.done.connect(self._on_search_done)
        self._search_worker.error.connect(lambda e: self.result_info.setText("搜索失败：" + e))
        self._search_worker.start()

    def _on_search_done(self, items, total_text):
        if not items:
            self.result_info.setText("无结果（工坊页面结构可能已改版，或网络受限）")
            return
        self.result_info.setText(("共 %s 条 · " % total_text) if total_text else "")
        self.page_label.setText("第 %d 页" % self._page)
        for it in items:
            wid = it["id"]
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(6, 4, 6, 4)
            thumb = QLabel()
            thumb.setFixedSize(THUMB_W, THUMB_H)
            thumb.setObjectName("CardThumb")
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setText("…")
            h.addWidget(thumb)
            info = QWidget()
            iv = QVBoxLayout(info)
            iv.setContentsMargins(0, 0, 0, 0)
            iv.setSpacing(2)
            title = QLabel(it["title"] or ("ID " + wid))
            title.setObjectName("CardTitle")
            sub = QLabel("作者 %s · 订阅 %s · ID %s" % (it.get("author") or "-", it.get("subs") or "-", wid))
            sub.setObjectName("Hint")
            iv.addWidget(title)
            iv.addWidget(sub)
            h.addWidget(info, 1)
            li = QListWidgetItem()
            li.setData(Qt.UserRole, it)
            li.setSizeHint(row.sizeHint().expandedTo(QSize(0, THUMB_H + 14)))
            self.result_list.addItem(li)
            self.result_list.setItemWidget(li, row)
            if it.get("preview"):
                self._previews[wid] = it["preview"]
                if wid in self._icons:
                    thumb.setPixmap(self._icons[wid])
                else:
                    t = PreviewWorker(wid, it["preview"])
                    t.done.connect(self._on_preview)
                    self._preview_threads.append(t)
                    t.start()

    def _on_preview(self, wid, data):
        if not data:
            return
        pm = QPixmap()
        if pm.loadFromData(data):
            pm = pm.scaled(THUMB_W, THUMB_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self._icons[wid] = pm
            for i in range(self.result_list.count()):
                it = self.result_list.item(i)
                if it.data(Qt.UserRole) and it.data(Qt.UserRole).get("id") == wid:
                    w = self.result_list.itemWidget(it)
                    if w:
                        lab = w.findChild(QLabel)
                        if lab:
                            lab.setPixmap(pm)
                    break

    # ---------- 链接解析 ----------
    def parse_links(self):
        text = self.link_edit.toPlainText()
        ids = steam_api.extract_ids(text)
        if not ids:
            QMessageBox.information(self, "解析", "未找到有效的物品 ID")
            return
        self.link_list.clear()
        self.btn_download.setEnabled(False)
        self._details_worker = DetailsWorker(ids, resolve_collections=True)
        self._details_worker.done.connect(self._on_details)
        self._details_worker.error.connect(lambda e: QMessageBox.warning(self, "解析失败", e))
        self._details_worker.start()

    def _on_details(self, details):
        child_ids = []   # 合集的子物品（需要二次展开）
        self._pending_collection = None
        for d in details:
            if d.get("result") != 1:
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
            else:
                # 普通物品：只在这里添加一次，不再进入二次展开
                self._append_link_item("%s（%.1f MB）" % (d.get("title", "?"), int(d.get("file_size") or 0) / 1048576.0),
                                       d.get("publishedfileid"))
                self._maybe_find_parent(str(d.get("publishedfileid")), str(d.get("title") or ""))
        # 子物品去重后展开
        uniq = []
        for x in child_ids:
            if x not in uniq:
                uniq.append(x)
        if uniq:
            self._child_worker = DetailsWorker(uniq)
            self._child_worker.done.connect(self._on_children)
            self._child_worker.error.connect(lambda e: QMessageBox.warning(self, "解析失败", e))
            self._child_worker.start()

    def _on_children(self, details):
        for d in details:
            if d.get("result") != 1:
                continue
            if steam_api.collection_children(d):
                continue  # 嵌套合集忽略
            self._append_link_item("%s（%.1f MB）" % (d.get("title", "?"), int(d.get("file_size") or 0) / 1048576.0),
                                   d.get("publishedfileid"))
        self.btn_download.setEnabled(True)

    def _append_link_item(self, text, wid, children=False):
        wid = str(wid)
        # 同一物品只添加一次
        for i in range(self.link_list.count()):
            d = self.link_list.item(i).data(Qt.UserRole) or {}
            if d.get("id") == wid:
                return
        it = QListWidgetItem(text)
        if children:
            # 合集摘要只用于说明来源，不参与勾选和下载。
            it.setFlags(Qt.ItemIsEnabled)
            it.setToolTip("下载时只处理下方识别出的合集中子物品")
        else:
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
        it.setData(Qt.UserRole, {"id": wid, "collection": children})
        self.link_list.addItem(it)

    # ---------- 下载 ----------
    def _selected_ids(self):
        ids = []
        for i in range(self.result_list.count()):
            it = self.result_list.item(i)
            d = it.data(Qt.UserRole)
            if d:
                ids.append(d["id"])
        if ids:
            return ids
        for i in range(self.link_list.count()):
            it = self.link_list.item(i)
            d = it.data(Qt.UserRole)
            if d and it.checkState() == Qt.Checked and not d.get("collection"):
                ids.append(d["id"])
        return ids

    def download_selected(self):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "下载", "请先搜索并等待结果，或勾选要下载的链接条目")
            return
        if gamemod.is_l4d2_running():
            QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再下载导入 mod")
            return
        self.btn_download.setEnabled(False)
        self.progress.setRange(0, 0)
        collection = None
        col = getattr(self, "_pending_collection", None)
        if col:
            collection = {"cid": "ws_" + col["workshop_id"], "name": col["name"],
                          "workshop_id": col["workshop_id"]}
        self._worker = DownloadWorker(self.main.store, self.main.library, ids, collection=collection)
        self._worker.log.connect(lambda s: self.log_box.appendPlainText(str(s)[:200]))
        self._worker.progress.connect(self._on_dl_progress)
        self._worker.done.connect(self._on_dl_done)
        self._worker.error.connect(self._on_dl_error)
        self._worker.start()

    def _on_dl_progress(self, done, total):
        if total:
            self.progress.setRange(0, 100)
            self.progress.setValue(int(done * 100 / total))
        else:
            self.progress.setRange(0, 0)

    def _on_dl_done(self, recs):
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.btn_download.setEnabled(True)
        names = "、".join(r["title"] for r in recs) if recs else "无"
        QMessageBox.information(self, "下载完成", "已导入 %d 个 mod（默认禁用）：\n%s" % (len(recs), names))
        self.main.refresh_all()

    def _on_dl_error(self, e):
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.btn_download.setEnabled(True)
        self.log_box.appendPlainText("下载失败：" + e)
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
                    self.log_box.appendPlainText(
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
        existing = {}
        for m in store.mods().values():
            if m.get("workshop_id"):
                existing[str(m["workshop_id"])] = m
        to_download = []
        grouped = []
        for c in children_details:
            m = existing.get(c["id"])
            if m:
                m["collection"] = col["cid"]
                grouped.append(m["file"])
            else:
                to_download.append(c["id"])
        info = {"name": col["name"], "workshop_id": col["workshop_id"],
                "files": list(dict.fromkeys(grouped))}
        old = store.get_collection(col["cid"])
        if old:
            info["files"] = list(dict.fromkeys(old.get("files", []) + info["files"]))
        store.upsert_collection(col["cid"], info)
        store.save_library()
        self.log_box.appendPlainText("合集《%s》：已在库 %d 个（已归组），待下载 %d 个"
                                     % (col["name"], len(grouped), len(to_download)))
        if to_download:
            if gamemod.is_l4d2_running():
                QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再下载导入 mod")
                return
            self.btn_download.setEnabled(False)
            self.progress.setRange(0, 0)
            self._worker = DownloadWorker(store, self.main.library, to_download, collection=col)
            self._worker.log.connect(lambda s: self.log_box.appendPlainText(str(s)[:200]))
            self._worker.progress.connect(self._on_dl_progress)
            self._worker.done.connect(self._on_dl_done)
            self._worker.error.connect(self._on_dl_error)
            self._worker.start()
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
class MigrateDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("迁移工坊订阅 mod")
        self.resize(620, 520)
        v = QVBoxLayout(self)
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


# ---------------------------------------------------------------- 章节 / 一键进图
class ChaptersDialog(QDialog):
    def __init__(self, main, rec):
        super().__init__(main)
        self.main = main
        self.rec = rec
        self.setWindowTitle("章节 - %s" % (rec.get("alias") or rec["title"]))
        self.resize(520, 380)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("战役《%s》共 %d 章（解析自 mission 文件）" % (rec["title"], len(rec.get("chapters", [])))))
        self.table = QTableWidget(len(rec.get("chapters", [])), 2)
        self.table.setHorizontalHeaderLabels(["章节显示名", "地图名"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemDoubleClicked.connect(lambda _it: self.launch(0))
        for r, ch in enumerate(rec.get("chapters", [])):
            self.table.setItem(r, 0, QTableWidgetItem(ch.get("name", "")))
            self.table.setItem(r, 1, QTableWidgetItem(ch.get("map", "")))
        v.addWidget(self.table, 1)
        btns = QHBoxLayout()
        b1 = QPushButton("进入第一章")
        b1.setProperty("accent", "primary")
        b1.clicked.connect(lambda: self.launch(0))
        b_close = QPushButton("关闭")
        b_close.clicked.connect(self.reject)
        btns.addWidget(b1)
        btns.addStretch(1)
        btns.addWidget(b_close)
        v.addLayout(btns)

    def launch(self, row):
        chs = self.rec.get("chapters", [])
        if row >= len(chs):
            return
        map_name = chs[row]["map"]
        if not self.rec.get("enabled"):
            if QMessageBox.question(self, "启用 mod", "该战役当前为禁用状态，先启用再进入？") == QMessageBox.Yes:
                self.main.library.set_enabled(self.rec["file"], True)
                self.main.refresh_all()
            else:
                return
        steam_exe = pathsmod.find_steam_exe()
        gamemod.launch_map(map_name, steam_exe)
        QMessageBox.information(self, "启动", "已发送启动指令：+map %s" % map_name)


# ---------------------------------------------------------------- 归类
ITEM_SUGGESTIONS = {
    "角色": sorted(set(SURVIVOR_NAMES.values())) + ["整体替换"],
    "特感": sorted(set(SPECIAL_NAMES.values())),
    "枪械": sorted(set(WEAPON_SEG_NAMES.values())),
    "近战": sorted(set(MELEE_NAMES.values())),
    "医疗品": sorted(set(MED_NAMES.values())),
    "投掷": ["燃烧瓶", "土制炸弹", "胆汁罐"],
}


class CategoryDialog(QDialog):
    def __init__(self, main, rec):
        super().__init__(main)
        self.main = main
        self.rec = rec
        self.setWindowTitle("修改分类 - %s" % (rec.get("alias") or rec["title"]))
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(CATEGORIES)
        self.cat_combo.setCurrentText(rec["category"])
        self.item_combo = QComboBox()
        self.item_combo.setEditable(True)
        self._fill_items()
        self.cat_combo.currentTextChanged.connect(lambda _s: self._fill_items())
        form.addRow("类别", self.cat_combo)
        form.addRow("具体物品", self.item_combo)
        v.addLayout(form)
        hint = QLabel("同一「类别 + 物品」下的 mod 互相排斥（启用一个自动禁用其余）。\n留空物品表示多项/整体，不参与互斥。")
        hint.setObjectName("Hint")
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
class DetailDialog(QDialog):
    def __init__(self, main, rec):
        super().__init__(main)
        self.setWindowTitle("mod 详情")
        self.resize(460, 320)
        v = QVBoxLayout(self)
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
        if rec.get("chapters"):
            rows.append(("章节", "、".join(c["name"] for c in rec["chapters"])))
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
        b.clicked.connect(lambda: gamemod.open_folder(main.library.paths.addons_dir))
        btns.addWidget(b)
        btns.addStretch(1)
        b_close = QPushButton("关闭")
        b_close.clicked.connect(self.accept)
        btns.addWidget(b_close)
        v.addLayout(btns)
