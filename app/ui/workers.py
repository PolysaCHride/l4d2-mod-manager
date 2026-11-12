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


class ImportAnalyzeWorker(QThread):
    """解压压缩包并解析候选 mod；确认前不写入游戏目录。"""
    log = Signal(str)
    progress = Signal(int, int, str)
    done = Signal(object)
    error = Signal(str)

    def __init__(self, library, archive_paths, parent=None):
        super().__init__(parent)
        self.library = library
        self.archives = archive_paths

    def run(self):
        try:
            batch = importer.stage_archives(
                self.archives, self.library,
                log=lambda text: self.log.emit(str(text)),
                progress=lambda i, n, text: self.progress.emit(i, n, str(text)))
            self.done.emit(batch)
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))


class ImportCommitWorker(QThread):
    """把候选列表中的勾选项复制并登记进 mod 库。"""
    progress = Signal(int, int, str)
    done = Signal(list)
    error = Signal(str)

    def __init__(self, library, batch, candidates, parent=None):
        super().__init__(parent)
        self.library = library
        self.batch = batch
        self.candidates = candidates

    def run(self):
        try:
            records = importer.commit_staged(
                self.batch, self.library, self.candidates,
                progress=lambda i, n, title: self.progress.emit(i, n, str(title)))
            self.done.emit(records)
        except Exception as e:  # noqa: BLE001
            self.error.emit("%s: %s" % (type(e).__name__, e))


class DownloadWorker(QThread):
    log = Signal(str)
    progress = Signal(int, str, str)   # 总进度百分比、阶段、当前模组
    done = Signal(object)
    error = Signal(str)

    def __init__(self, store, library, item_ids, collection=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.library = library
        self.item_ids = item_ids
        self.collection = collection  # {"cid","name","workshop_id"} 或 None
        self._stop = False
        self.skipped = []
        self.failures = []

    def stop(self):
        self._stop = True

    def run(self):
        try:
            recs = []
            item_ids = []
            for wid in self.item_ids:
                wid = str(wid)
                if wid and wid not in item_ids:
                    item_ids.append(wid)

            pending = []
            for wid in item_ids:
                existing = self.library.find_existing_workshop(wid)
                if existing:
                    self.skipped.append({
                        "id": wid,
                        "title": existing.get("title") or existing.get("file") or wid,
                        "file": existing.get("file") or ""})
                    self.log.emit("已在库，跳过：%s (%s)"
                                  % (existing.get("title") or existing.get("file") or wid, wid))
                else:
                    pending.append(wid)
            if self.skipped:
                self.log.emit("本地库检查完成：跳过 %d 个已有模组，待下载 %d 个"
                              % (len(self.skipped), len(pending)))
            if not pending:
                self.progress.emit(100, "没有需要下载的新模组", "所选模组均已在库")
                self.done.emit(recs)
                return
            if self._stop:
                self.done.emit(recs)
                return

            details = {}
            for start in range(0, len(pending), 100):
                if self._stop:
                    break
                chunk = pending[start:start + 100]
                end = min(start + 100, len(pending))
                self.log.emit("正在获取下载地址（%d/%d）：读取工坊物品信息…"
                              % (end, len(pending)))
                try:
                    for detail in steam_api.get_details(chunk):
                        wid = str(detail.get("publishedfileid") or "")
                        if wid:
                            details[wid] = detail
                except Exception as e:  # 单批失败时继续逐项尝试
                    self.log.emit("批量获取下载地址失败：%s；稍后逐项重试" % e)

            known_sizes = [int((details.get(wid) or {}).get("file_size") or 0)
                           for wid in pending]
            known_sizes = [size for size in known_sizes if size > 0]
            fallback_size = max(1, sum(known_sizes) // len(known_sizes)) if known_sizes else 1
            weights = []
            for wid in pending:
                size = int((details.get(wid) or {}).get("file_size") or 0)
                weights.append(size if size > 0 else fallback_size)
            total_weight = sum(weights)
            finished_weight = 0
            shown_percent = 0

            for index, wid in enumerate(pending, 1):
                if self._stop:
                    break
                detail = details.get(wid)
                title = str((detail or {}).get("title") or wid)
                weight = weights[index - 1]
                item_fraction = 0.0

                def _on_item_progress(done, total, _base=finished_weight,
                                      _weight=weight, _title=title, _index=index):
                    nonlocal item_fraction, shown_percent
                    if total:
                        fraction = max(0.0, min(1.0, float(done) / float(total)))
                    elif _weight > 1:
                        # 服务端未给 Content-Length 时，用工坊 file_size 估算。
                        fraction = max(0.0, min(1.0, float(done) / float(_weight)))
                    else:
                        fraction = 0.0
                    # 直连失败切到 SteamCMD 时进度会从 0 重新开始，界面保持单调。
                    item_fraction = max(item_fraction, fraction)
                    percent = int(round(100.0 * (
                        _base + _weight * item_fraction) / total_weight))
                    shown_percent = max(shown_percent, min(99, percent))
                    self.progress.emit(shown_percent, "正在下载 %d/%d" % (_index, len(pending)),
                                       _title)

                self.log.emit("开始处理 %d/%d：%s (%s)" % (index, len(pending), title, wid))
                self.progress.emit(shown_percent, "正在准备 %d/%d" % (index, len(pending)), title)
                try:
                    rec = downloader.download_and_import(
                        self.store, self.library, wid,
                        log=lambda s: self.log.emit(str(s)),
                        progress=_on_item_progress,
                        collection=self.collection,
                        detail=detail)
                    recs.append(rec)
                except Exception as e:  # 单个失败不阻断其余勾选项
                    self.failures.append({"id": wid, "title": title,
                                          "error": "%s: %s" % (type(e).__name__, e)})
                    self.log.emit("下载失败，继续处理其余模组：%s (%s) · %s"
                                  % (title, wid, e))
                finished_weight += weight
                shown_percent = max(shown_percent, min(100, int(round(
                    100.0 * finished_weight / total_weight))))
                self.progress.emit(shown_percent,
                                   "已完成 %d/%d" % (index, len(pending)),
                                   "已导入 %d 个，失败 %d 个"
                                   % (len(recs), len(self.failures)))
            if self._stop:
                self.log.emit("已停止下载：后续模组未处理")
            self.progress.emit(shown_percent if self._stop else 100,
                               "下载任务已停止" if self._stop else "全部处理完成",
                               "已导入 %d 个 · 跳过 %d 个 · 失败 %d 个"
                               % (len(recs), len(self.skipped), len(self.failures)))
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
    status = Signal(str)
    done = Signal(list)
    error = Signal(str)

    def __init__(self, item_ids, resolve_collections=False, parent=None):
        super().__init__(parent)
        self.item_ids = item_ids
        self.resolve_collections = resolve_collections

    def run(self):
        try:
            self.status.emit("正在获取工坊物品详情（%d 项）…" % len(self.item_ids))
            details = steam_api.get_details(self.item_ids)
            if self.resolve_collections:
                self.status.emit("工坊详情已获取，正在解析合集内容…")
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
