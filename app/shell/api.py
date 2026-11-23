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
from app.core.library import Library, conflict_key, group_key_str  # noqa: E402
from app.core.store import Store  # noqa: E402
from app.shell import tasks  # noqa: E402
from app.shell.fmt import fmt_size  # noqa: E402
from app.shell.jobs import JobRunner  # noqa: E402

APP_VERSION = "1.3"
# 与 app/core/game.py 的 GAME_EXE 保持一致（core 冻结，只能抄一份常量）
_GAME_EXE = "left4dead2.exe"
REPO_SLUG = "PolysaCHride/l4d2-mod-manager"


def _ok(**kw):
    d = {"ok": True}
    d.update(kw)
    return d


def _err(message):
    return {"ok": False, "error": str(message)}


_THUMB_CACHE = {}      # (绝对路径, mtime) -> 给 <img src> 的 URL
_THUMB_DIR = None      # data/thumb-cache，懒建


def _file_url(path):
    """绝对路径 → 百分号编码过的 file:// URL。

    必须用 Path.as_uri()：手拼 "file:///" + path 遇到中文/空格会 404
    （实测：22 张里唯一加载失败的那张就是路径没编码）。
    """
    try:
        from pathlib import Path
        return Path(path).resolve().as_uri()
    except Exception:
        return ""


def _thumb_cache_dir():
    global _THUMB_DIR
    if _THUMB_DIR is None:
        _THUMB_DIR = os.path.join(app_paths.data_dir(), "thumb-cache")
        try:
            os.makedirs(_THUMB_DIR, exist_ok=True)
        except OSError:
            pass
    return _THUMB_DIR


def _cached_thumb(path, mtime, size, max_bytes=400 * 1024):
    """大图压成 320×180 存到 data/thumb-cache，返回缓存文件路径（失败返回 ""）。

    缓存键 = 路径 + mtime + 大小 的哈希：换图或改图会自动失效。
    这一步只在**第一次**遇到这张图时发生；之后只是 stat 一下。
    （2026-11-21 之前是每次 bootstrap 都现压——71 张大图，光压图就要 2s+。）
    """
    import hashlib
    d = _thumb_cache_dir()
    if not d:
        return ""
    key = hashlib.sha1(("%s|%d|%d" % (path, mtime, size)).encode("utf-8")).hexdigest()[:16]
    out = os.path.join(d, key + ".jpg")
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return out
    try:
        from PIL import Image
        # with 必须用：bootstrap 会对每条记录跑一遍，不关闭句柄会攒一堆
        # 未释放的文件描述符（Windows 上还会锁住预览图）。
        with Image.open(path) as im:
            im.thumbnail((320, 180))
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            tmp = out + ".tmp"
            im.save(tmp, format="JPEG", quality=78)
        os.replace(tmp, out)
        return out
    except Exception:
        return ""


def _thumb_url(preview_path, max_bytes=400 * 1024):
    """预览图 → 给 `<img src>` 的 URL（file:// 或空串）。

    **2026-11-21 改**：不再转 base64。原来的依据是「跨盘 file:// 会被
    WebView2 拦截」，实测不成立 —— 页面在 D:、图片在 E:，22 张跨盘图
    21 张直载成功（唯一的失败是路径没做百分号编码）。

    base64 的代价是 `bootstrap` 一次要过 18MB 的桥（实测 3.1s / 18.2MB）。
    现在只传 URL：大图（> 400KB）先压成 320×180 落盘缓存，其余直接给原图 URL。
    渲染端 `loading="lazy"`，只有看得见的卡片才会真的读盘。
    """
    if not preview_path:
        return ""
    p = os.path.abspath(preview_path)
    if not os.path.isfile(p):
        return ""
    try:
        mtime = os.path.getmtime(p)
        size = os.path.getsize(p)
    except OSError:
        return ""

    key = (p, mtime, size)
    cached = _THUMB_CACHE.get(key)
    if cached is not None:
        return cached

    url = ""
    if size > max_bytes:
        # 大图：压成小图再给 URL，别让渲染端去解一张 8504×8504 的 JPEG
        small = _cached_thumb(p, mtime, size, max_bytes)
        url = _file_url(small) if small else _file_url(p)
    else:
        url = _file_url(p)
    _THUMB_CACHE[key] = url
    return url


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
    """wiki 占位图的 file:// URL（同跨盘可直载，见 _thumb_url 的说明）。"""
    p = _wiki_image_path(item, category)
    if not p:
        return ""
    key = os.path.basename(p)
    cached = _WIKI_CACHE.get(key)
    if cached is not None:
        return cached
    url = _file_url(p)
    _WIKI_CACHE[key] = url
    return url


def _game_running_fast():
    """用 Toolhelp 进程快照找 left4dead2.exe：~1ms。

    `app/core/game.is_l4d2_running()` 走 `tasklist` 子进程，实测 **0.49s**，
    占掉 bootstrap 之后剩下的九成时间。core 是冻结层不能改，所以在 shell
    这边补一条快路径；**任何异常都返回 None**，让调用方退回 core 的实现，
    不自己猜结果。
    """
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        TH32CS_SNAPPROCESS = 0x2
        INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260),
            ]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        k32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
        k32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]

        snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if not snap or snap == INVALID_HANDLE_VALUE:
            return None
        try:
            entry = PROCESSENTRY32()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
            target = _GAME_EXE.lower().encode("ascii")
            ok = k32.Process32First(snap, ctypes.byref(entry))
            while ok:
                if bytes(entry.szExeFile).split(b"\x00")[0].lower() == target:
                    return True
                ok = k32.Process32Next(snap, ctypes.byref(entry))
            return False
        finally:
            k32.CloseHandle(snap)
    except Exception:
        return None


def _game_running():
    """游戏是否在运行；返回 None 表示「检测失败」（调用方要按 unknown 处理）。"""
    fast = _game_running_fast()
    if fast is not None:
        return fast
    try:
        from app.core import game as game_core
        return bool(game_core.is_l4d2_running())
    except Exception:
        return None


_CATALOG = None


def _category_catalog():
    """分类 → 该分类下**可能出现的全部子分类**（含目前没有模组的那种）。

    名字不是手抄的：直接取 `app/core/classify.category_catalog()` —— 那是
    分类器真正会写进 `item` 的值，也是「管理器自带子分类」的唯一定义。

    ★ 2026-11-21：这份逻辑原来在 shell 里重抄了一遍（自己再拼 WHITELIST /
    PREFIX / REGEX / 各张名单），于是出现两套真相：core 里删掉的自制近战
    还在目录里、分类器能写出的「前置/框架」「音乐」又不在目录里。现在只留
    core 那一份，shell 只负责转发 + 异常兜底。

    为什么要它：分类器只给自己的结果，`bootstrap` 只带**库里出现过**的值，
    于是「特感」里只剩 Tank / 普通感染者，Hunter 那些一个都看不见 ——
    用户会以为分类坏了。
    """
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG
    try:
        from app.core import classify as C
        _CATALOG = C.category_catalog()
    except Exception as exc:      # core 词表改结构时别把启动搞挂
        print("[shell] 读取分类词表失败：%s" % exc, file=sys.stderr)
        _CATALOG = {}
    return _CATALOG


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

    def _to_mod(self, rec, coll_idx=None):
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
            "sizeText": fmt_size(rec.get("size")),
            "enabled": bool(rec.get("enabled")),
            "workshop_id": str(rec.get("workshop_id") or ""),
            "thumb": thumb,
            # 入库时间用 added_at（真正的登记时间）；mtime 是文件修改时间，
            # 用户移动/重下文件就会变。added_at 缺失时退回 mtime。
            "added": int(rec.get("added_at") or rec.get("mtime") or 0),
            "addedText": _fmt_ago(rec.get("added_at") or rec.get("mtime")),
            "pinned": bool(rec.get("pinned")),
            # ⚠️ 2026-11-20 起不再向前端传 mutex / mutexApplicable / groupMutex：
            # 互斥机制已整体拆除，用户自行管理冲突。
            # 分类器内部的 CONFLICT_CATEGORIES 仍保留（分类逻辑要用），
            # 但它不再是 UI 概念。
            #
            # 分类器原本给出的分类。用户手工改过分类后（pinned），
            # category/item 变成用户值，auto_* 保留「管理器认为它是什么」。
            # 没用过用户分类时为 None —— 前端据此决定要不要置灰展示。
            "autoCategory": rec.get("auto_category"),
            "autoItem": rec.get("auto_item"),
            # 所属合集 ID（"ws_<数字>"）。没有归属时为空串。
            # 取值见 _collection_index()：**以 collections 表为准**，
            # 记录上的 collection 字段只是一份会被重扫抹掉的缓存。
            "collection": (coll_idx or {}).get(rec.get("file", ""))
                          or rec.get("collection", "") or "",
        }

    def _collection_index(self):
        """vpk 文件名 → 所属合集 ID。

        权威来源是 `store.collections()[cid]["files"]`。mod 记录上的
        `collection` 字段只是一份冗余缓存 —— `_scan_one` 重扫时只保留
        auto_* / title_locked / pinned，会把 collection 抹成空串。

        这不是推测：真实库里 200 条记录的 `collection` 全是空，
        而 collections 表里 6 条归属（1 + 5）完好无损。
        只信记录字段的话，合集在界面上永远不会出现。
        """
        idx = {}
        if self._store is None:
            return idx
        for cid, info in (self._store.collections() or {}).items():
            for name in (info.get("files") or []):
                idx[str(name)] = cid
        return idx

    def _collections_payload(self):
        """合集表：`{cid: {name, workshop_id, files}}`，给前端做**纯展示**。

        合集不参与启用/停用判定（用户裁定：合集 = 展示分组），
        这里只把「有哪些合集、各含哪些文件」原样交出去。
        """
        out = {}
        if self._store is None:
            return out
        for cid, info in (self._store.collections() or {}).items():
            out[str(cid)] = {
                "name": str(info.get("name") or ""),
                "workshop_id": str(info.get("workshop_id") or ""),
                "files": [str(f) for f in (info.get("files") or [])],
            }
        return out

    def _all_mods(self):
        self._ensure()
        if self._store is None:
            return []
        idx = self._collection_index()
        return [self._to_mod(r, idx) for r in self._store.mods().values()]

    def _find(self, file_name):
        self._ensure()
        if self._store is None:
            return None
        return self._store.get_mod(file_name)

    # ------------------------------------------------------- 文件拖拽（WebView2）
    #
    # 为什么需要这一层：浏览器安全模型里 `File` 对象只有 name/size/type，
    # **没有绝对路径**（Chrome/WebView2 都故意不给）。而导入压缩包要真实路径
    # 去调 7-Zip，所以前端那个 `dataTransfer.files[0].path` 永远是 undefined。
    #
    # pywebview 留了一条后门：只要**由 Python 侧** `Element.on('drop', cb)`
    # 注册监听，`_dnd_state['num_listeners']` 就会 +1，WebView2 才会走
    # `postMessageWithAdditionalObjects('FilesDropped', files)` 这个分支，
    # 传的是带 `.Path` 的 CoreWebView2File；pywebview 再把绝对路径回填到
    # 事件里每个 file 的 `pywebviewFullPath` 字段。
    #
    # 光在 JS 里 addEventListener('drop') 不触发这条通道 —— 这就是「拖拽
    # 看起来支持、实际拿不到路径」的根因。

    DROP_EXTS = (".zip", ".7z", ".rar")

    def on_file_drop(self, event):
        """pywebview 的 DOM drop 回调：从事件里挖出绝对路径，推给前端。

        由 `main_web._arm_file_drop` 在 Python 侧注册；**不要改成 JS 监听**，
        否则拿不到 `pywebviewFullPath`。
        """
        try:
            files = ((event or {}).get("dataTransfer") or {}).get("files") or []
            paths, rejected = [], []
            for item in files:
                if not isinstance(item, dict):
                    continue
                path = item.get("pywebviewFullPath") or item.get("path") or ""
                name = item.get("name") or os.path.basename(path)
                if not path:
                    # 拿不到路径的条目直接归类为「不支持」，不要静默丢掉
                    rejected.append(name or "(未知文件)")
                    continue
                if not path.lower().endswith(self.DROP_EXTS):
                    rejected.append(name)
                    continue
                if not os.path.isfile(path):
                    rejected.append(name)
                    continue
                paths.append(path)
            self._emit("files.dropped", {"paths": paths, "rejected": rejected})
            return _ok(paths=paths, rejected=rejected)
        except Exception as exc:
            return _err(exc)

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
            # 检测失败时不能当成「没运行」——那会让前端放行写入，
            # 而游戏运行中写 addonlist.txt 会失败或损坏。
            state = _game_running()
            running = bool(state)
            game_check_failed = state is None
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
                # 合集表：模组详情里「更多 → 合集」用，纯展示。
                collections=self._collections_payload(),
                # 分类 → 全部可能的子分类。用来把「没有模组的子分类」也画出来
                # （特感只有 2 个的时候，用户会以为分类坏了）。
                catalog=_category_catalog(),
                # 同组互斥是**按子分类**各开各关的，所以下发的是「被关掉的那些组」
                # （格式 "分类\u0000物品"）。前端按当前子分类查这条清单决定开关状态。
                # 不要在这里下发全局布尔值 —— 没有全局开关这个概念。
                mutex_off=(sorted(group_key_str(k) for k in self._library.mutex_off_groups())
                           if self._library is not None else []),
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
        """启用/停用。

        2026-11-22 起互斥**由界面开关决定**（`settings.mutex`，默认开）：
          · 开：启用 A 会把同 `(分类, 物品)` 里已启用的其它模组一并停用，
                 被停用的文件名放在 `disabled_siblings` 里，让界面能说清
                 「顺带停用了谁」；
          · 关：启用就是启用，不动任何人。
        停用永远不影响其它模组。
        """
        try:
            self._ensure()
            rec = self._find(file_name)
            if rec is None:
                return _err("找不到模组：%s" % file_name)
            if self._library is None:
                return _err("未配置游戏目录")

            enabled = bool(enabled)
            # 后端再兜一层：前端状态可能过期（先开管理器后开游戏），
            # 而游戏运行中写 addonlist.txt 会被游戏覆盖，甚至写坏。
            state = _game_running()
            if state is None:
                return _err("无法确认游戏是否在运行，为避免损坏 addonlist.txt，已取消写入。")
            if state:
                return _err("游戏运行中，无法修改模组配置，请先退出游戏。")
            # mutex=None → 由 core 按该模组**自己的子分类开关**判断，
            # 不再传一个全局值。这样关掉 Nick 的互斥不影响 AK-47。
            disabled = self._library.set_enabled(file_name, enabled)
            key = conflict_key(rec)
            return _ok(enabled=enabled, disabled_siblings=list(disabled or []),
                       mutex=(self._library.mutex_on(key) if key else False))
        except Exception as exc:
            return _err(exc)

    # ---------------------------------------------------------------- 互斥开关

    def get_mutex(self, category=None, item=None):
        """读某个子分类的互斥开关 + 该组当前的存量冲突。

        `category` / `item` 都给了 → 只看这一个组（界面在 Nick 里点开关时用）；
        省略 → 返回全库的按组开关映射（`groups`）供界面判断每个子分类的状态。
        """
        try:
            self._ensure()
            if self._library is None:
                return _ok(mutex=False, applicable=False, groups={}, conflicts=[])

            lib = self._library
            if category and item:
                key = (str(category), str(item))
                return _ok(mutex=lib.mutex_on(key), applicable=True,
                           group={"category": key[0], "item": key[1]},
                           conflicts=lib.conflict_groups(only=key))

            # 不带范围：把「哪些组被关掉了」整体交出去，界面自己按当前子分类取
            off = lib.mutex_off_groups()
            return _ok(mutex=True, applicable=False,
                       off=[group_key_str(k) for k in sorted(off)],
                       conflicts=[])
        except Exception as exc:
            return _err(exc)

    def set_mutex(self, enabled, category=None, item=None):
        """设置某个子分类的互斥开关。

        必须给 `category` + `item` —— 互斥是**按子分类**独立的，
        没有「全局开关」这个概念（用户 2026-11-22 明确要求）。
        打开时**不自动收敛**已有冲突，界面要先调 `resolve_conflicts`
        或让用户确认。
        """
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            if not (category and item):
                return _err("缺少分类或子分类，无法设置互斥")
            # 开/关互斥本身只写 settings，但**打开时会立刻收敛**（停用同组其它），
            # 那是写 addonlist —— 所以同样要拦。
            state = _game_running()
            if state is None:
                return _err("无法确认游戏是否在运行，为避免损坏 addonlist.txt，已取消。")
            if state:
                return _err("游戏运行中，无法修改同组互斥，请先退出游戏。")
            lib = self._library
            value = lib.set_group_mutex(category, item, bool(enabled))
            key = (str(category), str(item))
            return _ok(mutex=value, group={"category": key[0], "item": key[1]},
                       conflicts=(lib.conflict_groups(only=key) if value else []))
        except Exception as exc:
            return _err(exc)

    def resolve_conflicts(self, category=None, item=None, winner=None):
        """把冲突收敛到一个启用项（保留名称排序第一个）。

        给了 `category` + `item` → 只收敛这一个组（界面里「默认启用」用）；
        省略 → 收敛全库（「整理」用）。

        只改 addonlist 与库里的 enabled 字段，**不动文件**。
        返回被停用的文件名列表，方便界面说明。
        """
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            if self._game_running():
                return _err("游戏运行中，无法修改模组配置，请先退出游戏。")

            lib = self._library
            from app.core.addonlist import AddonList
            only = ((str(category), str(item))
                    if (category and item) else None)
            al = AddonList.load(lib.paths.addonlist_file)
            disabled, _enabled = lib._settle_conflicts(al, only=only, winner=winner)
            al.save(lib.paths.addonlist_file)
            lib.store.save_library()
            mods = self._all_mods()
            self._emit("mods.changed", {"mods": mods})
            return _ok(disabled=disabled, count=len(disabled), mods=mods)
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

    def restore_auto_category(self, file_name):
        """把分类恢复成分类器原本的判定（撤销用户的手工分类）。

        只对「用户改过分类」的模组有效（auto_category 存在）。
        恢复后清掉 pinned，之后重扫会重新接管。
        """
        try:
            self._ensure()
            if self._library is None:
                return _err("未配置游戏目录")
            if self._find(file_name) is None:
                return _err("找不到模组：%s" % file_name)
            self._library.restore_auto_category(file_name)
            rec = self._find(file_name) or {}
            return _ok(category=rec.get("category", ""), item=rec.get("item", ""))
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

    def start_adopt(self, autodetect=True):
        """全量采纳：把 addons 下所有 vpk 纳入管理（core 的 adopt_all）。

        和 start_scan 的关键区别 —— 这个**会移动文件**：
          · 顶层未登记的 vpk       → 补记进库，addonlist 记 "1"
          · 非 workshop 的子目录    → 整组移到顶层，记 "0"（禁用）
          · workshop/ 子目录        → 走迁移逻辑，保留启用状态
        所以前端必须先弹确认框，且游戏运行中禁止调用（调用方负责，这里再兜一层）。

        没配游戏目录时**先自己找一遍**（`autodetect=True`）：
        用户点「开始整理」的意图是「让我能用」，不是「让我先填设置」。
        只有自动检测也失败，才把配置游戏目录这件事交回给用户。
        """
        try:
            self._ensure()
            if self._library is None:
                # 还没配目录 → 先自动检测一次，能认出来就直接用
                if autodetect:
                    found = self.autodetect_game_dir(silent=True)
                    if found:
                        self._ensure()      # save_setting 里已经重置过，重新建 Library
                if self._library is None:
                    return _err("GAME_DIR_REQUIRED")

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
                        "sizeText": fmt_size(c.get("size")),
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

    def autodetect_game_dir(self, silent=False):
        """自动找游戏目录，找到就**写进设置并重建 Library**，返回路径（找不到返回空串）。

        与 `detect_game_dir` 的分工：那个只查不写（设置页「自动检测」按钮用，
        点完还要用户确认）；这个直接落盘，给「整理」这类必须马上能用的场景用。
        """
        try:
            self._ensure()
            found = paths_core.find_game_dir() if hasattr(paths_core, "find_game_dir") else ""
            if not found or not paths_core.is_game_dir(found):
                return ""
            if self._store is None:
                return ""
            self._store.set_setting("game_dir", found)
            with self._lock:
                self._store = None
                self._library = None
                self._game_paths = None
            self._ensure()
            if not silent:
                print("[shell] 自动检测到游戏目录:", found, flush=True)
            return found
        except Exception as exc:
            if not silent:
                print("[shell] 自动检测游戏目录失败:", exc, flush=True)
            return ""

    def get_game_state(self):
        """即时查询游戏是否在运行。前端在**每次写操作前**和定时轮询时调。

        为什么需要：`bootstrap` 只在启动时算一次，用户先开管理器再开游戏时，
        前端那个 `state.gameRunning` 永远是 false —— 于是一路放行写入，
        而游戏运行中写 `addonlist.txt` 会被游戏覆盖甚至损坏。
        这个接口没有任何缓存，每次都现查（Toolhelp 快照约 1ms）。
        """
        try:
            state = _game_running()
            return _ok(running=bool(state), unknown=state is None)
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

    def _clean_orphan_previews(self):
        """删掉 `data/previews/` 里**没有任何模组记录引用**的图片，返回释放字节数。

        为什么需要：`download_and_import` 会把工坊缩略图落到
        `data/previews/<id>.jpg`，而记录的 `preview` 存的是绝对路径。
        用户删掉模组、或重新导入之后，这些图就成了孤儿 ——
        实测 41 个文件 / 约 38MB，200 条记录里 0 条引用。
        它既不在 `tmp/` 也不在 `thumb-cache/`，所以 before 这段代码
        `clean_cache` 从来碰不到这里。

        **只在用户主动「清理缓存」时执行**，不在启动时自动跑。

        安全约束：
          - 只删文件（目录、链接一律跳过），`previews/` 目录本身保留
          - 路径必须真的落在 previews 目录内（`abspath` + 前缀比对，防 `..`）
          - 引用比对用绝对路径 + `normcase`（Windows 大小写不敏感）
        """
        if self._store is None:
            return 0
        d = getattr(self._store, "previews_dir", "")
        if not d or not os.path.isdir(d):
            return 0
        base = os.path.normcase(os.path.abspath(d))
        prefix = base + os.sep

        referenced = set()
        for rec in self._store.mods().values():
            p = rec.get("preview") or ""
            if p:
                referenced.add(os.path.normcase(os.path.abspath(p)))

        freed = 0
        try:
            names = os.listdir(d)
        except OSError:
            return 0
        for name in names:
            full = os.path.join(d, name)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            ap = os.path.normcase(os.path.abspath(full))
            if ap != base and not ap.startswith(prefix):
                continue                      # 防 .. 之类的路径逃逸
            if ap in referenced:
                continue                      # 被引用的一个都不能少
            try:
                size = os.path.getsize(full)
                os.remove(full)
                freed += size
            except OSError:
                pass
        return freed

    def clean_cache(self):
        """清理临时解压目录、缩略图缓存，以及 previews 里没人引用的图。"""
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
            # previews/ 只能按引用文件删，不能整目录 rmtree
            freed += self._clean_orphan_previews()
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
