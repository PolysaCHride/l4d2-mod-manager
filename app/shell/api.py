# -*- coding: utf-8 -*-
"""WebUI 桥接层：把 app/core 暴露给前端。

设计原则：
- 一个文件能读完，不拆成碎片，便于审查。
- 不 import PySide6，只依赖标准库 + app.core。
- 所有公开方法返回 dict，绝不把异常抛给 JS。

前端调用约定见 app/webui/bridge.js。
"""
import json
import os
import re
import sys
import threading
import time

# 允许直接 `python -m app.shell.api` 方式运行
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.core import app_paths, paths as paths_core  # noqa: E402
from app.core.classify import CONFLICT_CATEGORIES  # noqa: E402
from app.core.library import Library  # noqa: E402
from app.core.store import Store  # noqa: E402
from app.shell import tasks  # noqa: E402
from app.shell.jobs import JobRunner  # noqa: E402

APP_VERSION = "1.2.1"
REPO_SLUG = "PolysaCHride/l4d2-mod-manager"


def _ok(**kw):
    d = {"ok": True}
    d.update(kw)
    return d


def _err(message):
    return {"ok": False, "error": str(message)}


_THUMB_CACHE = {}


def _thumb_url(preview_path, max_bytes=400 * 1024):
    """把本地预览图转成 data URI。

    为什么不直接用 file://：页面本身是 file:// 协议，
    跨盘符（D: 页面 → E: 图片）会被 WebView2 的策略拦截，
    表现为全部裂图。data URI 没有这个限制，且体积可控。
    """
    if not preview_path:
        return ""
    p = os.path.abspath(preview_path)
    if not os.path.isfile(p):
        return ""

    key = (p, os.path.getmtime(p))
    cached = _THUMB_CACHE.get(key)
    if cached is not None:
        return cached

    try:
        size = os.path.getsize(p)
        # 大图必须先压缩：JPEG 不能截断，截断出来就是坏图（浏览器裂图）。
        # 没装 Pillow 时宁可不显示，也不要给出坏图。
        if size > max_bytes:
            try:
                from PIL import Image
                import io
                img = Image.open(p)
                img.thumbnail((320, 180))
                buf = io.BytesIO()
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(buf, format="JPEG", quality=78)
                data = buf.getvalue()
                uri = "data:image/jpeg;base64," + __import__("base64").b64encode(data).decode("ascii")
                _THUMB_CACHE[key] = uri
                return uri
            except ImportError:
                # 没装 Pillow：返回空串让前端画占位，不要给截断的坏 JPEG
                print("[shell] 缺少 Pillow，跳过超过 %dKB 的缩略图" % (max_bytes // 1024),
                      file=sys.stderr)
                return ""
            except Exception:
                return ""
        with open(p, "rb") as f:
            raw = f.read(max_bytes)
        ext = os.path.splitext(p)[1].lower()
        mime = {".png": "image/png", ".gif": "image/gif",
                ".webp": "image/webp"}.get(ext, "image/jpeg")
        uri = "data:%s;base64,%s" % (mime, __import__("base64").b64encode(raw).decode("ascii"))
        _THUMB_CACHE[key] = uri
        return uri
    except Exception:
        return ""


_WIKI_CACHE = {}


def _safe_asset_name(name):
    """把物品/分类名转成 assets/wiki 下的安全文件名。

    与 app/ui/util._safe_name 保持一致的规则：只保留字母数字和少量安全字符，
    其余替换成下划线。这样 'AK-47' 能命中 'AK-47.png'。
    """
    out = []
    for ch in str(name or ""):
        if ch.isalnum() or ch in "-_ .":
            out.append(ch)
        elif ch in "\\/:*?\"<>|":
            out.append("_")
        else:
            out.append("_")
    return "".join(out).strip() or "_"


def _wiki_image_path(item, category):
    """按 物品 → 分类 顺序找 assets/wiki 下的占位图。

    与 app/ui/util.wiki_image_path 同样的查找顺序。
    这是旧 UI 的预览图兜底资产（70 张），新 UI 之前完全没用上。
    """
    wiki_dir = app_paths.asset_path("wiki")
    for name in (item, category):
        if not name:
            continue
        p = os.path.join(wiki_dir, _safe_asset_name(name) + ".png")
        if os.path.isfile(p):
            return p
    return ""


def _wiki_thumb(item, category):
    """wiki 占位图的 data URI（跨盘 file:// 会被 WebView2 拦截，所以也要转 base64）。"""
    p = _wiki_image_path(item, category)
    if not p:
        return ""
    key = os.path.basename(p)
    cached = _WIKI_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        with open(p, "rb") as f:
            raw = f.read()
        uri = "data:image/png;base64," + __import__("base64").b64encode(raw).decode("ascii")
        _WIKI_CACHE[key] = uri
        return uri
    except Exception:
        return ""


def _fmt_size(n):
    """字节 → 人类可读。与 app/ui/util.fmt_size 输出保持一致。"""
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        n = 0.0
    if n <= 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            if unit == "B":
                return "%d %s" % (int(n), unit)
            return "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f GB" % n


def _fmt_ago(ts):
    """时间戳 → 「2 天前」这类相对时间。"""
    try:
        ts = float(ts or 0)
    except (TypeError, ValueError):
        return ""
    if ts <= 0:
        return ""
    delta = time.time() - ts
    if delta < 3600:
        return "刚刚"
    if delta < 86400:
        return "%d 小时前" % int(delta // 3600)
    days = int(delta // 86400)
    if days < 30:
        return "%d 天前" % days
    if days < 365:
        return "%d 个月前" % int(days // 30)
    return "%d 年前" % int(days // 365)


class Api(object):
    """pywebview 的 js_api 对象。方法名即 JS 侧调用的 api.xxx()。

    pywebview 反射遍历 js_api 生成函数表时，会在 getattr 之前跳过
    `name.startswith('_')` 的属性（见 webview/util.py 的 get_functions）。
    所以 window / store / library 一律用下划线前缀：既不会暴露给 JS，
    也不会递归展开 WebView2 的 COM 属性链。

    不要在类上加 `_serializable = False` —— 那会让整个 Api 对象不被注册，
    表现为前端拿不到任何方法（我们踩过这个坑）。
    """

    def __init__(self):
        self._window = None         # 由 main_web 注入；下划线前缀让 pywebview 反射时跳过
        self._store = None
        self._library = None
        self._game_paths = None
        self._lock = threading.Lock()
        self._runner = JobRunner(self._emit_job)
        self._import_batches = {}


    # ---------------------------------------------------------------- 初始化

    def attach_window(self, window):
        self._window = window

    def _ensure(self):
        """懒加载 Store / Library。首次调用时读磁盘。"""
        if self._store is not None:
            return
        with self._lock:
            if self._store is not None:
                return
            store = Store(app_paths.data_dir())
            # 用已存设置初始化进程级全局状态
            try:
                from app.core import steam_api
                steam_api.set_proxy(store.settings().get("proxy", "") or "")
            except Exception:
                pass
            gd = store.settings().get("game_dir", "")
            gp = paths_core.GamePaths(gd) if gd else None
            self._store = store
            self._game_paths = gp
            self._library = Library(store, gp) if gp and gp.valid() else None

    # ---------------------------------------------------------------- 事件推送

    def _emit(self, event_type, payload):
        if self._window is None:
            return
        try:
            data = json.dumps(payload, ensure_ascii=False)
            js = "window.__dsh && window.__dsh.emit(%s, %s);" % (
                json.dumps(event_type), data)
            self._window.evaluate_js(js)
        except Exception as exc:  # 推送失败不应影响业务
            print("[shell] emit failed:", exc, file=sys.stderr)

    def _emit_job(self, event_type, payload):
        """JobRunner 的回调，复用自己的事件推送。"""
        self._emit(event_type, payload)

    # ---------------------------------------------------------------- 数据转换

    def _to_mod(self, rec):
        """后端记录 → 前端 Mod 模型（见 bridge.js 的字段约定）。"""
        title = rec.get("title") or rec.get("file", "")
        category = rec.get("category", "") or "未分类"
        item = rec.get("item", "") or ""
        # 预览图三级兜底（与旧 UI util.load_thumb 一致）：
        #   1. mod 自带的 preview（后端转成 data URI）
        #   2. assets/wiki 下的物品图（如 Ellis.png / AK-47.png）
        #   3. assets/wiki 下的分类图（如 角色.png）
        # 都没有才留空，前端画渐变占位。
        thumb = _thumb_url(rec.get("preview"))
        if not thumb:
            thumb = _wiki_thumb(item, category)
        return {
            "file": rec.get("file", ""),
            "title": title,
            "alias": rec.get("alias", "") or "",
            "category": category,
            "item": item,
            "size": int(rec.get("size") or 0),
            "sizeText": _fmt_size(rec.get("size")),
            "enabled": bool(rec.get("enabled")),
            "workshop_id": str(rec.get("workshop_id") or ""),
            "thumb": thumb,
            # 入库时间用 added_at（真正的登记时间）；mtime 是文件修改时间，
            # 用户移动/重下文件就会变。added_at 缺失时退回 mtime。
            "added": int(rec.get("added_at") or rec.get("mtime") or 0),
            "addedText": _fmt_ago(rec.get("added_at") or rec.get("mtime")),
            "pinned": bool(rec.get("pinned")),
            # 排序/分组辅助
            "mutex": (rec.get("category") in CONFLICT_CATEGORIES),
            # 分类器原本给出的分类。用户手工改过分类后（pinned），
            # category/item 变成用户值，auto_* 保留「管理器认为它是什么」。
            # 没用过用户分类时为 None —— 前端据此决定要不要置灰展示。
            "autoCategory": rec.get("auto_category"),
            "autoItem": rec.get("auto_item"),
            # 所属合集 ID（"ws_<数字>"）。只有地图多部件会用，没归属时为空。
            "collection": rec.get("collection", "") or "",
        }

    def _all_mods(self):
        self._ensure()
        if self._store is None:
            return []
        return [self._to_mod(r) for r in self._store.mods().values()]

    def _find(self, file_name):
        self._ensure()
        if self._store is None:
            return None
        return self._store.get_mod(file_name)

    # ---------------------------------------------------------------- 读

    def bootstrap(self):
        """一次性返回前端启动所需的全部数据。"""
        try:
            self._ensure()
            mods = self._all_mods()
            settings = self._store.settings() if self._store else {}
            enabled = sum(1 for m in mods if m["enabled"])
            gd = settings.get("game_dir", "")
            gp = self._game_paths
            running = False
            game_check_failed = False
            try:
                from app.core import game as game_core
                running = bool(game_core.is_l4d2_running())
            except Exception:
                # 检测失败时不能当成「没运行」——那会让前端放行写入，
                # 而游戏运行中写 addonlist.txt 会失败或损坏。
                game_check_failed = True
            return _ok(
                mods=mods,
                settings={
                    "game_dir": gd,
                    "proxy": settings.get("proxy", "") or "",
                    "archiver_path": settings.get("archiver_path", "") or "",
                    "palette": settings.get("palette", "blacksite") or "blacksite",
                    "motion": bool(settings.get("motion", True)),
                },
                stats={"total": len(mods), "enabled": enabled},
                game={"running": running, "unknown": game_check_failed},
                paths={
                    "addons": gp.addons_dir if gp else "",
                    "valid": bool(gp and gp.valid()),
                },
                version=APP_VERSION,
            )
        except Exception as exc:
            return _err(exc)

    def get_mods(self):
        try:
            return _ok(mods=self._all_mods())
        except Exception as exc:
            return _err(exc)

    def get_stats(self):
        try:
            mods = self._all_mods()
            return _ok(total=len(mods), enabled=sum(1 for m in mods if m["enabled"]))
        except Exception as exc:
            return _err(exc)

    # ---------------------------------------------------------------- 写

    def toggle_mod(self, file_name, enabled):
        """启用/停用。同组互斥时返回被连带停用的兄弟项。"""
        try:
            self._ensure()
            rec = self._find(file_name)
            if rec is None:
                return _err("找不到模组：%s" % file_name)
            if self._library is None:
                return _err("未配置游戏目录")

            enabled = bool(enabled)
            # zone 互斥由 core 负责，它已经算出被停用的兄弟项并返回。
            # 这里不要自己再扫一遍 —— 那样会和 core 的规则静默分叉。
            disabled = self._library.set_enabled(file_name, enabled, mutex=True) or []
            if disabled:
                self._emit("mods.changed", {"mods": self._all_mods()})
            return _ok(enabled=enabled, disabled_siblings=list(disabled))
        except Exception as exc:
            return _err(exc)

    def set_alias(self, file_name, alias):
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            if self._find(file_name) is None:
                return _err("找不到模组：%s" % file_name)
            self._library.set_alias(file_name, alias or "")
            return _ok(alias=alias or "")
        except Exception as exc:
            return _err(exc)

    def set_category(self, file_name, category, item):
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            if self._find(file_name) is None:
                return _err("找不到模组：%s" % file_name)
            self._library.set_category(file_name, category, item or "", pinned=True)
            return _ok()
        except Exception as exc:
            return _err(exc)

    def delete_mod(self, file_name):
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            if self._find(file_name) is None:
                return _err("找不到模组：%s" % file_name)
            self._library.delete_mod(file_name)
            return _ok(trashed=True)
        except Exception as exc:
            return _err(exc)

    # ---------------------------------------------------------------- 外部动作

    def reveal_mod(self, file_name):
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            self._library.reveal_mod(file_name)
            return _ok()
        except Exception as exc:
            return _err(exc)

    def open_workshop(self, workshop_id):
        try:
            from app.core import game as game_core
            game_core.open_workshop_page(str(workshop_id))
            return _ok()
        except Exception as exc:
            return _err(exc)

    def open_path(self, path):
        try:
            if not path or not os.path.exists(path):
                return _err("路径不存在")
            os.startfile(path)  # noqa: S606 - Windows 专用
            return _ok()
        except Exception as exc:
            return _err(exc)

    def launch_game(self):
        try:
            from app.core import game as game_core
            game_core.launch_game()
            return _ok()
        except Exception as exc:
            return _err(exc)

    # ---------------------------------------------------------------- 长任务

    def start_scan(self):
        """扫描 addons 顶层，进度通过 job.progress 推送。

        只读：重建已有记录 + 从 addonlist.txt 同步启用状态。
        **不移动任何文件、不处理子目录、不碰 workshop/**（那是 start_adopt）。
        """
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")

            def run(job):
                stats = tasks.scan(job, self._library)
                mods = self._all_mods()
                self._emit("mods.changed", {"mods": mods})
                # 必须发 done，否则前端 runJob 的 onDone 永不触发，
                # 状态栏卡在「扫描中」、首屏引导按钮永久禁用。
                job.done(stats if isinstance(stats, dict) else {"count": len(mods)})

            job_id = self._runner.start("scan", run)
            return _ok(job_id=job_id)
        except Exception as exc:
            return _err(exc)

    def start_adopt(self):
        """全量采纳：把 addons 下所有 vpk 纳入管理（core 的 adopt_all）。

        和 start_scan 的关键区别 —— 这个**会移动文件**：
          · 顶层未登记的 vpk       → 补记进库，addonlist 记 "1"
          · 非 workshop 的子目录    → 整组移到顶层，记 "0"（禁用）
          · workshop/ 子目录        → 走迁移逻辑，保留启用状态
        所以前端必须先弹确认框，且游戏运行中禁止调用（调用方负责，这里再兜一层）。
        返回 stats: {adopted, moved, migrated, deduped, conflicts, errors, ...}
        """
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")

            # 会移动文件，游戏占用 addons 时绝不能动
            try:
                from app.core import game as game_core
                if game_core.is_l4d2_running():
                    return _err("游戏运行中，无法整理（会移动 vpk 文件）")
            except Exception:
                return _err("无法确认游戏是否运行，为安全起见已取消整理")

            def run(job):
                stats = tasks.adopt_all(job, self._library)
                mods = self._all_mods()
                self._emit("mods.changed", {"mods": mods})
                job.done(stats if isinstance(stats, dict) else {})

            job_id = self._runner.start("adopt", run)
            return _ok(job_id=job_id)
        except Exception as exc:
            return _err(exc)

    def analyze_archives(self, paths):
        """解析压缩包。paths 为空时前端会先弹文件选择框。"""
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            paths = [p for p in (paths or []) if p and os.path.isfile(p)]
            if not paths:
                return _err("没有选择压缩包")

            archiver = None
            try:
                from app.core import archiver as archiver_core
                archiver = archiver_core.find_archiver()
            except Exception:
                archiver = None

            holder = {}

            def run(job):
                batch = tasks.analyze_archives(job, self._library, paths, archiver)
                holder["batch"] = batch
                # 只回传前端需要的字段（batch 里有临时目录路径，不必外传）
                cands = []
                for c in batch.get("candidates", []):
                    cands.append({
                        "stem": c.get("stem", ""),
                        "title": c.get("title", ""),
                        "category": c.get("category", ""),
                        "item": c.get("item", ""),
                        "size": int(c.get("size") or 0),
                        "sizeText": _fmt_size(c.get("size")),
                        "thumb": _thumb_url(c.get("preview")),
                        "selected": bool(c.get("selected")),
                        "duplicate": bool(c.get("duplicate_reason")),
                        "duplicateOf": c.get("duplicate_of", ""),
                        "parseError": c.get("parse_error", ""),
                        "archive": c.get("archive_name", ""),
                    })
                job.done({"candidates": cands,
                          "duplicates": int(batch.get("duplicate_count") or 0)})

            job_id = self._runner.start("import-analyze", run)
            self._import_batches[job_id] = holder
            return _ok(job_id=job_id)
        except Exception as exc:
            return _err(exc)

    def choose_archives(self):
        """原生文件选择框。返回路径列表。"""
        try:
            import webview
            if self._window is None:
                return _err("窗口未就绪")
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=True,
                file_types=("压缩包 (*.zip;*.7z;*.rar)", "所有文件 (*.*)"))
            return _ok(paths=list(result or []))
        except Exception as exc:
            return _err(exc)

    def commit_import(self, job_id, stems):
        """把勾选的候选写入库。stems 是候选的 stem 列表。"""
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            holder = self._import_batches.get(job_id)
            if not holder or "batch" not in holder:
                return _err("找不到解析结果，请重新解析")
            batch = holder["batch"]
            wanted = set(stems or [])
            picked = [c for c in batch.get("candidates", [])
                      if c.get("stem") in wanted and c.get("selected", True)]
            if not picked:
                return _err("没有可导入的项")

            def run(job):
                try:
                    records = tasks.commit_import(job, self._library, batch, picked)
                    self._emit("mods.changed", {"mods": self._all_mods()})
                    job.done({"imported": len(records)})
                finally:
                    # 必须清理：stage_archives 在 data/tmp 下解压了完整副本，
                    # 不删会一直堆积（一个 3GB 的包就留 3GB 垃圾）。
                    try:
                        from app.core import importer
                        importer.cleanup_staged(batch)
                    except Exception:
                        pass
                    self._import_batches.pop(job_id, None)
                job.done({"imported": len(records)})

            new_id = self._runner.start("import-commit", run)
            return _ok(job_id=new_id)
        except Exception as exc:
            return _err(exc)

    def parse_links(self, text):
        """解析链接，返回物品 ID 列表。"""
        try:
            ids = tasks.parse_links(text or "")
            return _ok(ids=list(ids))
        except Exception as exc:
            return _err(exc)

    def fetch_details(self, ids):
        """读取工坊详情（含合集展开）。"""
        try:
            self._ensure()
            ids = [str(i) for i in (ids or []) if i]
            if not ids:
                return _err("没有物品 ID")
            data = tasks.fetch_details(ids, self._library)
            return _ok(items=data["items"], collection=data["collection"])
        except Exception as exc:
            return _err(exc)

    def start_download(self, ids, collection=None):
        """下载并导入工坊物品。"""
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            ids = [str(i) for i in (ids or []) if i]
            if not ids:
                return _err("没有选择要下载的物品")

            def run(job):
                result = tasks.download(job, self._store, self._library, ids, collection)
                self._emit("mods.changed", {"mods": self._all_mods()})
                job.done(result or {})

            job_id = self._runner.start("download", run)
            return _ok(job_id=job_id)
        except Exception as exc:
            return _err(exc)

    def cancel_job(self, job_id):
        try:
            return _ok(cancelled=self._runner.cancel(job_id))
        except Exception as exc:
            return _err(exc)

    # ---------------------------------------------------------------- 设置

    def save_setting(self, key, value):
        try:
            self._ensure()
            if self._store is None:
                return _err("数据目录不可用")
            self._store.set_setting(key, value)
            if key == "proxy":
                # steam_api 的代理是进程级全局变量，只存 settings 不会生效
                from app.core import steam_api
                steam_api.set_proxy(value or "")
            if key == "game_dir":
                # 目录变了要重建 Library
                with self._lock:
                    self._store = None
                    self._library = None
                    self._game_paths = None
                self._ensure()
            return _ok()
        except Exception as exc:
            return _err(exc)

    def detect_game_dir(self):
        try:
            gd = paths_core.find_game_dir() if hasattr(paths_core, "find_game_dir") else ""
            return _ok(game_dir=gd or "")
        except Exception as exc:
            return _err(exc)

    def choose_dir(self):
        """原生目录选择框。"""
        try:
            import webview
            if self._window is None:
                return _err("窗口未就绪")
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if not result:
                return _ok(path="")
            p = result[0] if isinstance(result, (list, tuple)) else result
            return _ok(path=str(p))
        except Exception as exc:
            return _err(exc)

    def clean_cache(self):
        """清理临时解压目录与缩略图缓存。"""
        try:
            self._ensure()
            import shutil
            freed = 0
            targets = []
            if self._store is not None:
                targets.append(getattr(self._store, "tmp_dir", ""))
            targets.append(os.path.join(app_paths.data_dir(), "thumb-cache"))
            for d in targets:
                if d and os.path.isdir(d):
                    for root, _dirs, files in os.walk(d):
                        for f in files:
                            try:
                                freed += os.path.getsize(os.path.join(root, f))
                            except OSError:
                                pass
                    try:
                        shutil.rmtree(d, ignore_errors=True)
                    except Exception:
                        pass
            return _ok(freed=freed)
        except Exception as exc:
            return _err(exc)

    def check_update(self):
        """检查 GitHub releases/latest。失败返回当前版本，不报错。"""
        import json as _json
        try:
            from app.core import steam_api
            _get, _post, _body = steam_api._http()
            url = "https://api.github.com/repos/%s/releases/latest" % REPO_SLUG
            text = _get(url, timeout=20)
            data = _json.loads(text)
            latest = str(data.get("tag_name") or "").lstrip("vV")
            return _ok(latest=latest or APP_VERSION,
                       url=str(data.get("html_url") or ""))
        except Exception as exc:
            return _err(exc)

    # ---------------------------------------------------------------- 窗口控制

    def win_minimize(self):
        try:
            self._window.minimize()
            return _ok()
        except Exception as exc:
            return _err(exc)

    def win_toggle_maximize(self):
        """在最大化与还原之间切换。返回当前是否最大化。"""
        try:
            if getattr(self, "_maximized", False):
                self._window.restore()
                self._maximized = False
            else:
                self._window.maximize()
                self._maximized = True
            return _ok(maximized=self._maximized)
        except Exception as exc:
            return _err(exc)

    def win_close(self):
        try:
            self._window.destroy()
            return _ok()
        except Exception as exc:
            return _err(exc)

    def win_start_drag(self):
        """无边框窗口：拖动由 pywebview 的 easy_drag 负责，这里只做占位。"""
        return _ok()

    def log(self, message):
        """前端主动汇报日志。打包后没有控制台时靠它排查。"""
        line = "[web] %s" % (message,)
        print(line, flush=True)
        try:
            import time as _t
            path = os.path.join(app_paths.data_dir(), "webui.log")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("%s %s\n" % (_t.strftime("%H:%M:%S"), message))
        except Exception:
            pass
        return _ok()

    def set_palette(self, name):
        """配色切换，前端暂不暴露入口。"""
        try:
            allow = {"blacksite", "safehouse", "workshop", "index"}
            if name not in allow:
                return _err("未知配色：%s" % name)
            self._ensure()
            self._store.set_setting("palette", name)
            return _ok(palette=name)
        except Exception as exc:
            return _err(exc)
