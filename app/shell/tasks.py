# -*- coding: utf-8 -*-
"""把 app/ui/workers.py 里的长任务逻辑重写成纯 Python 版。

为什么不直接复用：原版继承 QThread 并用 Signal 通信，而新入口不依赖 Qt。
这里保留**完全相同的业务调用顺序**（同样的 core 函数、同样的进度算法），
只是把 emit 换成 job 回调。
"""
import os

from app.core import downloader, importer, steam_api
from app.shell.fmt import fmt_size


def scan(job, library):
    """扫描 addons 顶层。返回统计。"""
    job.progress("正在扫描", 0, 1, phase="scan")

    def progress(i, n, text):
        job.progress(text, i, n, phase="scan")

    stats = library.rescan(progress=progress)
    job.progress("扫描完成", 1, 1, phase="scan")
    return stats


def _count_adopt_work(library):
    """粗算 adopt_all 的工作量，只用于进度条分母。

    统计三部分：顶层 vpk 数 + 子目录里的 vpk 组数 + workshop 订阅项数。
    不精确也没关系 —— 进度条只是参考，core 的实际推进会自报 done。
    """
    import os as _os
    from app.core import vpk as _vpk

    addons = library.paths.addons_dir
    top = len(library.list_addon_files())
    sub = 0
    try:
        for dirpath, dirs, files in _os.walk(addons):
            rel = _os.path.relpath(dirpath, addons).lower()
            if rel == "workshop" or rel.startswith("workshop" + _os.sep):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d.lower() != "workshop"]
            if _os.path.abspath(dirpath).lower() == _os.path.abspath(addons).lower():
                continue   # 顶层单独算
            for f in files:
                if f.lower().endswith(".vpk"):
                    sub += 1
                    break  # 一个子目录算一组
    except OSError:
        pass
    try:
        ws = len(library.workshop_items())
    except Exception:
        ws = 0
    return max(top + sub + ws, 1)


def adopt_all(job, library):
    """全量采纳（library.adopt_all）：把 addons 下所有 vpk 纳入管理。

    与 scan() 的区别：**这个会移动文件**。
      · 顶层未登记的 vpk    → 补记进库（addonlist 记 "1"，保持游戏当前行为）
      · 非 workshop 子目录   → 整组移到顶层（记 "0"，禁用 —— 游戏本就不扫子目录）
      · workshop/ 子目录     → 走迁移，保留启用状态

    返回 core 的 stats：{adopted, moved, migrated, deduped,
                        auto_enabled, auto_disabled, migrated_ids,
                        conflicts, errors}
    """
    # core 的 adopt_all 不预先统计总数，progress 第三参是「当前项名字」。
    # 但 job.progress 需要 total 才算百分比，所以这里先粗算一个工作总量：
    # 顶层 vpk 数 + 子目录 vpk 组数 + workshop 项数。只是进度参考，不影响业务。
    try:
        total_work = _count_adopt_work(library)
    except Exception:
        total_work = 1
    state = {"done": 0}

    job.progress("正在整理", 0, total_work, phase="adopt")

    def progress(text, done=0, current=""):
        # ⚠️ core 里 progress 约定是 (text, done, current_name)，
        # 第三参是**名字**不是总数（library.py:699/731）。
        # 把第三参当 total 会 `int(done * 100 / total)` 拿字符串做除法 → TypeError。
        state["done"] = max(state["done"], int(done or 0))
        job.progress(text, min(state["done"], total_work), total_work, phase="adopt")

    stats = library.adopt_all(progress=progress)
    job.progress("整理完成", 1, 1, phase="adopt")
    return stats


def analyze_archives(job, library, archive_paths, archiver_info=None):
    """解压并解析压缩包，返回批次。"""
    job.log("开始解析 %d 个压缩包" % len(archive_paths))

    def log(text):
        job.log(text)

    def progress(i, n, text):
        job.progress(text, i, n, phase="import-analyze")

    batch = importer.stage_archives(
        archive_paths, library,
        log=log, progress=progress, archiver_info=archiver_info)

    candidates = batch.get("candidates", [])
    job.log("解析完成：%d 个候选" % len(candidates))
    return batch


def commit_import(job, library, batch, candidates):
    """把勾选的候选写入模组库。"""
    def progress(i, n, text):
        job.progress(text, i, n, phase="import-commit")

    records = importer.commit_staged(batch, library, candidates, progress=progress)
    job.log("已写入 %d 个模组" % len(records))
    return records


def download(job, store, library, item_ids, collection=None):
    """批量下载并导入工坊物品。

    进度按工坊 file_size 加权合并，与原版保持一致。
    """
    recs = []
    skipped = []
    failures = []

    ids = []
    for wid in item_ids:
        wid = str(wid)
        if wid and wid not in ids:
            ids.append(wid)

    # 先剔除已在库的
    pending = []
    for wid in ids:
        existing = library.find_existing_workshop(wid)
        if existing:
            skipped.append({"id": wid,
                            "title": existing.get("title") or existing.get("file") or wid,
                            "file": existing.get("file") or ""})
            job.log("已在库，跳过：%s (%s)" % (
                existing.get("title") or existing.get("file") or wid, wid))
        else:
            pending.append(wid)

    if not pending:
        job.progress("没有需要下载的新模组", 100, 100, phase="download",
                     extra={"skipped": len(skipped)})
        # job.done 由调用方（api.start_download）统一发送，这里只返回结果
        return {"records": [], "skipped": skipped, "failures": []}

    job.log("待下载 %d 个，已跳过 %d 个" % (len(pending), len(skipped)))

    # 批量取详情
    details = {}
    for start in range(0, len(pending), 100):
        if job.stopped():
            break
        chunk = pending[start:start + 100]
        job.log("正在获取下载地址（%d/%d）" % (min(start + 100, len(pending)), len(pending)))
        try:
            for detail in steam_api.get_details(chunk):
                wid = str(detail.get("publishedfileid") or "")
                if wid:
                    details[wid] = detail
        except Exception as exc:
            job.log("批量获取失败：%s；稍后逐项重试" % exc)

    # 按 file_size 加权
    known = [int((details.get(w) or {}).get("file_size") or 0) for w in pending]
    known = [s for s in known if s > 0]
    fallback = max(1, sum(known) // len(known)) if known else 1
    weights = []
    for wid in pending:
        size = int((details.get(wid) or {}).get("file_size") or 0)
        weights.append(size if size > 0 else fallback)
    total_weight = sum(weights) or 1
    finished = 0
    shown = 0

    for index, wid in enumerate(pending, 1):
        if job.stopped():
            job.log("已停止下载：后续模组未处理")
            break
        detail = details.get(wid)
        title = str((detail or {}).get("title") or wid)
        weight = weights[index - 1]
        item_fraction = 0.0

        job.log("开始处理 %d/%d：%s (%s)" % (index, len(pending), title, wid))
        job.progress("正在准备 %d/%d" % (index, len(pending)), shown, 100,
                     phase="download", extra={"current": title})

        def on_progress(done, total, _base=finished, _weight=weight,
                        _title=title, _index=index):
            nonlocal item_fraction, shown
            if total:
                frac = max(0.0, min(1.0, float(done) / float(total)))
            elif _weight > 1:
                frac = max(0.0, min(1.0, float(done) / float(_weight)))
            else:
                frac = 0.0
            item_fraction = max(item_fraction, frac)
            pct = int(round(100.0 * (_base + _weight * item_fraction) / total_weight))
            shown = max(shown, min(99, pct))
            job.progress("正在下载 %d/%d" % (_index, len(pending)), shown, 100,
                         phase="download", extra={"current": _title})

        try:
            rec = downloader.download_and_import(
                store, library, wid,
                log=lambda s: job.log(str(s)),
                progress=on_progress,
                collection=collection,
                detail=detail)
            recs.append(rec)
        except Exception as exc:
            failures.append({"id": wid, "title": title,
                             "error": "%s: %s" % (type(exc).__name__, exc)})
            job.log("下载失败：%s (%s) · %s" % (title, wid, exc))

        finished += weight
        shown = max(shown, min(100, int(round(100.0 * finished / total_weight))))
        job.progress("已完成 %d/%d" % (index, len(pending)), shown, 100,
                     phase="download",
                     extra={"current": "已导入 %d 个，失败 %d 个"
                            % (len(recs), len(failures))})

    result = {
        "records": recs,
        "skipped": skipped,
        "failures": failures,
        "stopped": job.stopped(),
    }
    job.progress("下载任务已停止" if job.stopped() else "全部处理完成",
                 100, 100, phase="download")
    return result


def parse_links(text):
    """解析工坊链接，返回去重后的物品 ID。纯函数，不需要 job。"""
    return steam_api.extract_ids(text or "")


def fetch_details(ids, library, max_items=300):
    """取工坊详情，展开合集，标注是否已在库。

    复用 core 的 resolve_collection_details —— 合集子项有两条接口兜底。
    返回 {items: [...], collection: {id,name}|None}
    """
    rows = list(steam_api.get_details(list(ids)[:100]))
    if not rows:
        return {"items": [], "collection": None}

    # 合集展开
    try:
        rows = steam_api.resolve_collection_details(rows)
    except Exception:
        pass

    collection = None
    expanded_rows = []
    for detail in rows:
        wid = str(detail.get("publishedfileid") or "")
        # 注意：collection_children() 返回的是 id 字符串列表，不是 dict 列表
        children = steam_api.collection_children(detail)
        if children:
            if collection is None:
                # 形状必须与 app/core/downloader.py:308 的期望一致，
                # 否则 cid 为空，子项永远不会归入合集。
                collection = {
                    "cid": "ws_" + wid,
                    "name": str(detail.get("title") or "合集"),
                    "workshop_id": wid,
                    "children": [],
                }
            child_ids = [str(c) for c in children if c][:max_items]
            collection["children"] = child_ids
            if child_ids:
                try:
                    expanded_rows.extend(steam_api.get_details(child_ids))
                except Exception:
                    pass

    if expanded_rows:
        seen = {str(d.get("publishedfileid")) for d in rows}
        rows.extend([d for d in expanded_rows
                     if str(d.get("publishedfileid")) not in seen])

    items = []
    seen_ids = set()
    for detail in rows:
        if detail.get("result") not in (1, None):
            continue
        wid = str(detail.get("publishedfileid") or "")
        if not wid or wid in seen_ids:
            continue
        children = detail.get("children")
        if children:
            continue                     # 合集本身不下载
        seen_ids.add(wid)

        existing = library.find_existing_workshop(wid) if library else None
        size = int(detail.get("file_size") or 0)
        items.append({
            "id": wid,
            "title": str(detail.get("title") or wid),
            "category": "",
            "item": "",
            "size": size,
            "sizeText": fmt_size(size),
            "thumb": "",
            "existing": bool(existing),
            "appId": detail.get("consumer_app_id"),
        })
    return {"items": items, "collection": collection}

