# -*- coding: utf-8 -*-
"""QThread 工作线程：扫描 / 导入 / 下载 / 在线搜索 / 迁移 / 预览图。"""
from PySide6.QtCore import QThread, Signal

from ..core import downloader, importer, steam_api


class ScanWorker(QThread):
    progress = Signal(int, int, str)
    done = Signal(dict)
    error = Signal(str)

    def __init__(self, library, parent=None):
        super().__init__(parent)
        self.library = library

    def run(self):
        try:
            stats = self.library.rescan(progress=lambda i, n, s: self.progress.emit(i, n, s))
            self.done.emit(stats)
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))


class ImportWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int, str)
    done = Signal(list)
    error = Signal(str)

    def __init__(self, library, archive_paths, parent=None):
        super().__init__(parent)
        self.library = library
        self.archives = archive_paths

    def run(self):
        try:
            all_recs = []
            for arc in self.archives:
                recs = importer.import_archive(
                    arc, self.library,
                    log=lambda s: self.log.emit(s),
                    progress=lambda i, n, s: self.progress.emit(i, n, s))
                all_recs.extend(recs)
            self.done.emit(all_recs)
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))


class DownloadWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int)   # done, total(0=未知)
    done = Signal(object)
    error = Signal(str)

    def __init__(self, store, library, item_ids, collection=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.library = library
        self.item_ids = item_ids
        self.collection = collection  # {"cid","name","workshop_id"} 或 None
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            recs = []
            for wid in self.item_ids:
                if self._stop:
                    break
                rec = downloader.download_and_import(
                    self.store, self.library, wid,
                    log=lambda s: self.log.emit(str(s)),
                    progress=lambda done, total: self.progress.emit(int(done), int(total)),
                    collection=self.collection)
                recs.append(rec)
            self.done.emit(recs)
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))


class SearchWorker(QThread):
    done = Signal(list, str)
    error = Signal(str)

    def __init__(self, query, page=1, sort="text", parent=None):
        super().__init__(parent)
        self.query = query
        self.page = page
        self.sort = sort

    def run(self):
        try:
            items, total = steam_api.search_workshop(self.query, page=self.page, sort=self.sort)
            self.done.emit(items, total)
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))


class DetailsWorker(QThread):
    """批量拉取工坊详情（链接解析 / 合集展开用）。"""
    done = Signal(list)
    error = Signal(str)

    def __init__(self, item_ids, resolve_collections=False, parent=None):
        super().__init__(parent)
        self.item_ids = item_ids
        self.resolve_collections = resolve_collections

    def run(self):
        try:
            details = steam_api.get_details(self.item_ids)
            if self.resolve_collections:
                steam_api.resolve_collection_details(details)
            self.done.emit(details)
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))


class PreviewWorker(QThread):
    done = Signal(str, bytes)   # item_id, bytes

    def __init__(self, item_id, url, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.url = url

    def run(self):
        data = steam_api.fetch_preview_bytes(self.url)
        self.done.emit(self.item_id, data)


class ParentCollectionWorker(QThread):
    """尽力反查一个物品所属的工坊合集：描述链接 → 作者工坊页 → 标题搜索。

    Steam 没有官方反查接口，三路尝试都失败时发 notfound。
    """
    found = Signal(str, str, int, list)   # col_id, col_title, n_children, children_details
    notfound = Signal(str)                # item_id

    def __init__(self, item_id, title, parent=None):
        super().__init__(parent)
        self.item_id = str(item_id)
        self.title = title or ""

    def _check_batch(self, cand):
        details = steam_api.get_details(cand)
        steam_api.resolve_collection_details(details)
        for dd in details:
            if dd.get("result") != 1:
                continue
            ch = steam_api.collection_children(dd)
            if ch and self.item_id in ch:
                return dd, ch
        return None, None

    def run(self):
        import re as _re
        try:
            cand = []
            details = steam_api.get_details([self.item_id])
            d = details[0] if details else {}
            for x in steam_api.extract_ids(d.get("file_description") or ""):
                if x != self.item_id and x not in cand:
                    cand.append(x)
            creator = d.get("creator")
            if creator:
                try:
                    _g, _p, _b = steam_api._http()
                    html = _g("https://steamcommunity.com/profiles/%s/myworkshopfiles/?appid=550&numperpage=50"
                              % creator, timeout=25)
                    for x in steam_api.extract_ids(html):
                        if x != self.item_id and x not in cand and len(cand) < 60:
                            cand.append(x)
                except Exception:
                    pass
            dd = ch = None
            for i in range(0, len(cand), 50):
                dd, ch = self._check_batch(cand[i:i + 50])
                if dd:
                    break
            if not dd:
                core = _re.sub(r"[\[\(（【].*?[\]\)）】]", " ", self.title)
                core = _re.sub(r"\b(pt|part|v\d+)\s*\d*", " ", core, flags=_re.I)
                core = _re.sub(r"\s+", " ", core).strip()
                if core:
                    items, _t = steam_api.search_workshop(core, page=1, num=20)
                    cand2 = [it["id"] for it in items if it["id"] != self.item_id][:20]
                    if cand2:
                        dd, ch = self._check_batch(cand2)
            if not dd:
                self.notfound.emit(self.item_id)
                return
            # 拉取子物品详情（标题/大小/是否已在库由 UI 判断）
            children = [str(c) for c in ch]
            child_details = []
            for i in range(0, len(children), 100):
                for cd in steam_api.get_details(children[i:i + 100]):
                    if cd.get("result") == 1:
                        child_details.append({
                            "id": str(cd.get("publishedfileid")),
                            "title": str(cd.get("title") or ""),
                            "size": int(cd.get("file_size") or 0)})
            self.found.emit(str(dd["publishedfileid"]),
                            str(dd.get("title") or "合集"), len(children), child_details)
        except Exception:
            self.notfound.emit(self.item_id)


class UpdateCheckWorker(QThread):
    """检查更新：请求仓库的 releases/latest（GitHub API）或 update.json。"""
    done = Signal(str, str)   # latest_version, release_url
    error = Signal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            _g, _p, _b = steam_api._http()
            text = _g(self.url, timeout=20)
            import json as _json
            data = _json.loads(text)
            self.done.emit(str(data.get("tag_name") or ""),
                           str(data.get("html_url") or self.url))
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))


class MigrateWorker(QThread):
    progress = Signal(int, int, str)
    done = Signal(list, list)   # moved[(file, enabled)], errors[(file, reason)]
    error = Signal(str)

    def __init__(self, library, files, parent=None):
        super().__init__(parent)
        self.library = library
        self.files = files

    def run(self):
        try:
            moved, errors = self.library.migrate_from_workshop(
                self.files, progress=lambda i, n, s: self.progress.emit(i, n, s))
            self.done.emit(moved, errors)
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))
