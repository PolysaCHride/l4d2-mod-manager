# -*- coding: utf-8 -*-
"""JSON 持久化：mod 库与设置的原子读写。

库（library.json）只是缓存，磁盘文件与 addonlist.txt 才是事实源。
"""
import json
import os
import threading
import time


def _atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    # 写完再替换，避免中途崩溃损坏数据
    bak = path + ".bak"
    if os.path.exists(path):
        try:
            os.replace(path, bak)
        except OSError:
            pass
    os.replace(tmp, path)


def new_mod_record(file_name):
    return {
        "file": file_name,           # 相对 addons 顶层的 vpk 文件名，如 "1127584577.vpk"
        "title": "",                 # 显示名（addoninfo / 工坊标题 / 文件名）
        "alias": "",                 # 用户自定义别名
        "category": "未分类",
        "item": "",                  # 具体物品（如 "AK-47"），空表示该类别下多项/整体
        "tags": [],
        "size": 0,
        "mtime": 0,
        "workshop_id": "",           # 数字字符串，非工坊来源为空
        "preview": "",               # 预览图绝对路径（可为空）
        "enabled": False,
        "added_at": int(time.time()),
        "updated_at": 0,
        "source": "",                # "import" / "download" / "migrate" / "scan" / "adopt"
        "collection": "",            # 所属合集 cid（地图 parts 用）
    }


def mod_display_name(record):
    """模组在列表中的显示名：用户别名 > 标题 > 文件名。"""
    alias = str(record.get("alias") or "").strip()
    title = str(record.get("title") or "").strip()
    file_name = str(record.get("file") or "").strip()
    return alias or title or file_name


def mod_name_sort_key(record):
    """名称排序键；同名时用文件名保证顺序稳定。"""
    return (mod_display_name(record).casefold(),
            str(record.get("file") or "").casefold())


class Store(object):
    """data/library.json + data/settings.json 的内存镜像与落盘。"""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.library_path = os.path.join(data_dir, "library.json")
        self.settings_path = os.path.join(data_dir, "settings.json")
        self.previews_dir = os.path.join(data_dir, "previews")
        self.trash_dir = os.path.join(data_dir, "trash")
        self.tmp_dir = os.path.join(data_dir, "tmp")
        self._lock = threading.Lock()
        self._settings = {}
        self._mods = {}          # file_name -> record
        self._collections = {}   # cid -> {name, workshop_id, files:[vpk文件名]}

        for d in (data_dir, self.previews_dir, self.trash_dir, self.tmp_dir):
            try:
                os.makedirs(d, exist_ok=True)
            except OSError:
                pass
        self._load()

    # ---------- 加载 ----------
    def _load(self):
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                self._settings = json.load(f)
        except (OSError, ValueError):
            self._settings = {}
        try:
            with open(self.library_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            mods = data.get("mods", {})
            if isinstance(mods, dict):
                self._mods = mods
            cols = data.get("collections", {})
            self._collections = cols if isinstance(cols, dict) else {}
        except (OSError, ValueError):
            self._mods = {}
            self._collections = {}

    # ---------- 设置 ----------
    def settings(self):
        return self._settings

    def set_setting(self, key, value):
        self._settings[key] = value
        self.save_settings()

    def save_settings(self):
        with self._lock:
            _atomic_write_json(self.settings_path, self._settings)

    # ---------- 库 ----------
    def mods(self):
        return self._mods

    def get_mod(self, file_name):
        return self._mods.get(file_name)

    def upsert_mod(self, record):
        self._mods[record["file"]] = record

    def remove_mod(self, file_name):
        self._mods.pop(file_name, None)

    # ---------- 合集 ----------
    def collections(self):
        return self._collections

    def get_collection(self, cid):
        return self._collections.get(cid)

    def upsert_collection(self, cid, info):
        self._collections[cid] = info

    def remove_collection(self, cid):
        self._collections.pop(cid, None)

    def save_library(self):
        with self._lock:
            _atomic_write_json(self.library_path,
                               {"version": 1, "mods": self._mods,
                                "collections": self._collections})
