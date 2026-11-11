# -*- coding: utf-8 -*-
"""工坊下载：SteamCMD 匿名下载为主，file_url 直连兜底。

SteamCMD 安装在 <data>/steamcmd/，首次使用自动下载官方 zip 并自更新。
下载落盘在 <steamcmd>/steamapps/workshop/content/550/<id>/。
"""
import os
import re
import shutil
import subprocess
import tempfile
import zipfile

from . import steam_api
from .classify import AUTO_ENABLE_CATEGORIES as _AUTO_ENABLE

STEAMCMD_URL = "https://client-update.steamstatic.com/installer/steamcmd.zip"
APPID = "550"


class DownloadError(Exception):
    pass


def steamcmd_root():
    """SteamCMD 安装目录。SteamCMD 限制：所在路径必须纯 ASCII，
    因此不能放在本项目目录（路径含中文/空格），改用系统级目录。"""
    cands = []
    la = os.environ.get("LOCALAPPDATA")
    if la:
        cands.append(os.path.join(la, "L4D2ModManager"))
    pd = os.environ.get("PROGRAMDATA")
    if pd:
        cands.append(os.path.join(pd, "L4D2ModManager"))
    cands.append(os.path.join(tempfile.gettempdir(), "L4D2ModManager"))
    for c in cands:
        if c.encode("ascii", "ignore").decode("ascii") == c:
            return os.path.join(c, "steamcmd")
    return os.path.join(tempfile.gettempdir(), "L4D2ModManager", "steamcmd")


def steamcmd_exe(store=None):
    return os.path.join(steamcmd_root(), "steamcmd.exe")


def ensure_steamcmd(store, log=None, progress=None):
    """确保 SteamCMD 可用。返回 steamcmd.exe 路径。"""
    exe = steamcmd_exe(store)
    if os.path.isfile(exe):
        return exe
    dest_zip = os.path.join(store.data_dir, "steamcmd.zip")
    steamcmd_dir = os.path.dirname(exe)
    os.makedirs(steamcmd_dir, exist_ok=True)

    def _zip_ok(path):
        try:
            with zipfile.ZipFile(path) as z:
                return z.testzip() is None
        except (OSError, zipfile.BadZipFile):
            return False

    if not (os.path.isfile(dest_zip) and _zip_ok(dest_zip)):
        if log:
            log("下载 SteamCMD…")
        _download_with_progress(STEAMCMD_URL, dest_zip, progress)
        if not _zip_ok(dest_zip):
            raise DownloadError("SteamCMD 下载失败（包不完整或损坏），请检查网络后重试")
    if log:
        log("解压 SteamCMD…")
    try:
        with zipfile.ZipFile(dest_zip) as z:
            z.extractall(steamcmd_dir)
    except (OSError, zipfile.BadZipFile) as e:
        raise DownloadError("SteamCMD 解压失败：%s" % e)
    try:
        os.remove(dest_zip)
    except OSError:
        pass
    if not os.path.isfile(exe):
        raise DownloadError("SteamCMD 解压失败（未找到 steamcmd.exe）")
    # 清理旧版残留（曾装在项目 data/ 下，路径含中文会导致 SteamCMD 无法运行）
    try:
        legacy = os.path.join(store.data_dir, "steamcmd")
        if os.path.isdir(legacy) and os.path.abspath(legacy).lower() != os.path.abspath(steamcmd_dir).lower():
            shutil.rmtree(legacy, ignore_errors=True)
    except Exception:
        pass
    # 首次运行触发自更新（必须以 SteamCMD 自身目录为 cwd）
    if log:
        log("SteamCMD 首次自更新…")
    try:
        subprocess.run([exe, "+quit"], capture_output=True, text=True, timeout=180,
                       cwd=steamcmd_root())
    except subprocess.TimeoutExpired:
        pass
    return exe


def _open_stream(url, timeout=60):
    """打开下载流：直连失败时自动尝试本地代理（clash 等）。"""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except Exception:
        proxy = steam_api._pick_proxy()
        if not proxy:
            raise
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        return urllib.request.build_opener(handler).open(req, timeout=timeout)


def _remove_with_retry(path, attempts=4):
    """删除文件；被安全软件扫描锁占用时退避重试。"""
    import time as _time
    last = None
    for i in range(attempts):
        try:
            os.remove(path)
            return
        except PermissionError as e:
            last = e
            _time.sleep(0.3 * (i + 1))
    raise last


def _download_with_progress(url, dest, progress=None):
    """流式下载到 dest。progress(done_bytes, total_bytes|0)。"""
    with _open_stream(url) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    return dest


def steamcmd_download(store, item_id, log=None, progress=None):
    """SteamCMD 匿名下载。返回内容目录；失败抛 DownloadError。

    SteamCMD 首次自更新后当次进程可能不执行命令就退出，故未产出内容时重试一次。
    """
    exe = ensure_steamcmd(store, log=log, progress=progress)
    content_dir = os.path.join(steamcmd_root(), "steamapps", "workshop",
                               "content", APPID, str(item_id))
    cmd = [exe, "+login", "anonymous", "+workshop_download_item", APPID, str(item_id), "+quit"]
    for attempt in (1, 2):
        if os.path.isdir(content_dir):
            shutil.rmtree(content_dir, ignore_errors=True)
        if log:
            log("SteamCMD 拉取物品 %s…%s" % (item_id, "（重试）" if attempt == 2 else ""))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                cwd=steamcmd_root())
        for line in proc.stdout or []:
            line = line.rstrip()
            if line:
                if log:
                    log(line)
                if progress:
                    m = re.search(r"(\d+)%", line)
                    if m:
                        progress(int(m.group(1)), 100)
        proc.wait()
        if os.path.isdir(content_dir) and os.listdir(content_dir):
            return content_dir
    raise DownloadError("SteamCMD 未产出内容目录（匿名下载可能被该物品拒绝，或网络受限）")


def http_fallback_download(item_id, detail, dest_vpk, log=None, progress=None):
    """file_url 直连下载（主通道）。先写 .part 并校验 VPK 魔数，通过后才就位，
    避免把子合集预览图等无效内容写进 addons。"""
    file_url = (detail or {}).get("file_url") or ""
    if not file_url:
        raise DownloadError("该物品没有可用的直连地址（file_url 为空）")
    if log:
        log("使用直连下载 %s…" % item_id)
    tmp = dest_vpk + ".part"
    _download_with_progress(file_url, tmp,
                            progress=(lambda done, total: progress(done, total)) if progress else None)
    try:
        with open(tmp, "rb") as f:
            if f.read(4) != b"\x34\x12\xaa\x55":
                raise DownloadError("直连内容不是有效的 VPK（可能是子合集或预览资源）")
        os.replace(tmp, dest_vpk)
    except Exception:
        _remove_with_retry(tmp)
        raise


def pick_vpk_in_dir(content_dir):
    """从下载目录挑出 vpk（优先 addon.vpk；兼容无扩展名/_legacy.bin——按魔数判断）。"""
    vpks = []
    for dirpath, _dirs, files in os.walk(content_dir):
        for f in files:
            p = os.path.join(dirpath, f)
            lower = f.lower()
            if lower.endswith(".vpk"):
                vpks.append(p)
            elif not lower.endswith((".jpg", ".jpeg", ".png", ".txt", ".json")):
                # 可能是改名的 vpk，检查魔数
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) == b"\x34\x12\xaa\x55":
                            vpks.append(p)
                except OSError:
                    pass
    if not vpks:
        return [], ""
    addon = next((p for p in vpks if os.path.basename(p).lower() == "addon.vpk"), None)
    main = addon or max(vpks, key=os.path.getsize)
    return vpks, main


def download_and_import(store, library, item_id, log=None, progress=None, collection=None):
    """完整链路：SteamCMD → 失败则 file_url 直连 → 拷入 addons → 解析入库。
    collection={"cid","name","workshop_id"} 时将 mod 归入该合集。"""
    details = steam_api.get_details([item_id])
    detail = details[0] if details else {}
    if detail.get("result") not in (1, None) and detail.get("result") != 1:
        if detail.get("result") == -100:
            raise DownloadError("该物品不属于 L4D2")
        if log:
            log("物品详情 result=%s（继续尝试下载）" % detail.get("result"))
    title = str(detail.get("title") or "") or str(item_id)
    size_total = int(detail.get("file_size") or 0)

    dest_vpk = os.path.join(library.paths.addons_dir, "%s.vpk" % item_id)
    got = False
    # 首选 file_url 直连（快且不依赖 SteamCMD；本机火绒会隔离 SteamCMD 写入的文件）
    file_url = str((detail or {}).get("file_url") or "")
    if file_url:
        try:
            http_fallback_download(item_id, detail, dest_vpk, log=log,
                                   progress=(lambda done, total: progress(done, total)) if progress else None)
            got = True
        except DownloadError as e:
            if log:
                log("直连下载失败：%s" % e)
    if not got:
        try:
            content_dir = steamcmd_download(store, item_id, log=log, progress=progress)
            vpks, main_vpk = pick_vpk_in_dir(content_dir)
            if not vpks:
                raise DownloadError("下载内容中没有 VPK 文件")
            if os.path.exists(dest_vpk):
                os.remove(dest_vpk)
            shutil.copy2(main_vpk, dest_vpk)
            got = True
        except DownloadError as e:
            if log:
                log("SteamCMD 失败：%s" % e)
    if not got:
        raise DownloadError("两条下载通道均失败（file_url 与 SteamCMD）")
    # VPK 魔数校验兜底（file_url 路径已在 .part 上校验过；SteamCMD 路径在此兜底）
    try:
        with open(dest_vpk, "rb") as f:
            if f.read(4) != b"\x34\x12\xaa\x55":
                _remove_with_retry(dest_vpk)
                raise DownloadError("下载内容不是有效的 VPK 文件（可能被安全软件拦截）")
    except DownloadError:
        raise
    except OSError as e:
        raise DownloadError("校验下载文件失败：%s" % e)

    # 预览图
    preview_path = ""
    pv = str(detail.get("preview_url") or "")
    if pv:
        data = steam_api.fetch_preview_bytes(pv)
        if data:
            preview_path = os.path.join(store.previews_dir, "%s.jpg" % item_id)
            with open(preview_path, "wb") as f:
                f.write(data)

    rec = library.register_new(
        os.path.basename(dest_vpk), source="download", enabled=False,
        preview=preview_path, title=title, workshop_id=str(item_id))
    # 下载即用类（地图/脚本/音效等）下载后直接启用；冲突类/未分类默认禁用
    if rec.get("category") in _AUTO_ENABLE:
        try:
            library.set_enabled(rec["file"], True)
            rec["enabled"] = True
            if log:
                log("已自动启用（%s，非冲突类）" % rec["category"])
        except Exception:
            pass
    if collection:
        cid = str(collection.get("cid") or "")
        children = [str(c) for c in (collection.get("children") or [])]
        # 只把合集自己的子物品归组（普通物品与合集混传时不误伤）
        if cid and (not children or str(item_id) in children):
            rec["collection"] = cid
            info = store.get_collection(cid) or {
                "name": str(collection.get("name") or ""),
                "workshop_id": str(collection.get("workshop_id") or ""),
                "files": []}
            if rec["file"] not in info["files"]:
                info["files"].append(rec["file"])
            store.upsert_collection(cid, info)
            store.save_library()
    if log:
        log("已导入：%s（%s）" % (rec["title"], "已启用" if rec.get("enabled") else "默认禁用"))
    return rec
