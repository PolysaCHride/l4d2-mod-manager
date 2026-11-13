# -*- coding: utf-8 -*-
"""压缩包导入：zip 用 zipfile；7z/rar 调 7-Zip/WinRAR 命令行。

导入分两步：先解包到 data/tmp/ 下的独立暂存目录并解析候选，用户确认后
才复制到 addons。zip 条目做路径穿越校验；解出的 vpk 只解析数据，不执行任何内容。
"""
import os
import hashlib
import shutil
import subprocess
import tempfile
import zipfile

from . import archiver as archiver_core
from . import vpk as vpkmod
from . import classify as clf

ZIP_EXTS = (".zip",)


class ImporterError(Exception):
    pass


def supported_ext(path):
    return path.lower().endswith(ZIP_EXTS + (".7z", ".rar"))


def find_archiver(remembered_path=""):
    return archiver_core.find_archiver(remembered_path)


def extract_archive(archive, dest_dir, log=None, archiver_info=None):
    """解压 archive 到 dest_dir。返回解出的文件数。"""
    lower = archive.lower()
    if lower.endswith(ZIP_EXTS):
        n = 0
        with zipfile.ZipFile(archive) as z:
            dest_abs = os.path.abspath(dest_dir)
            for info in z.infolist():
                if info.is_dir():
                    continue
                target = os.path.abspath(os.path.join(dest_dir, info.filename))
                if not target.startswith(dest_abs + os.sep) and target != dest_abs:
                    raise ImporterError("压缩包内含非法路径: " + info.filename)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
                n += 1
                if log and n % 200 == 0:
                    log("解压 %d 个文件…" % n)
        return n
    if lower.endswith((".7z", ".rar")):
        info = archiver_info or find_archiver()
        if not info:
            raise ImporterError(
                "未找到 7-Zip/WinRAR，无法解压 %s 文件"
                % os.path.splitext(archive)[1])
        os.makedirs(dest_dir, exist_ok=True)
        cmd = info.extract_command(archive, dest_dir)
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        if proc.returncode != 0:
            raise ImporterError("解压失败（%s）：%s" %
                                (os.path.basename(info.path),
                                 (proc.stderr or proc.stdout or "")[-200:]))
        return sum(len(fs) for _, _, fs in os.walk(dest_dir))
    raise ImporterError("不支持的压缩格式: " + os.path.splitext(archive)[1])


def find_vpk_sets(root):
    """递归找出目录下全部 vpk 集合，返回 [代表 _dir 或单文件绝对路径]。"""
    all_vpk = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".vpk"):
                all_vpk.append(os.path.join(dirpath, f))
    reps = []
    seen = set()
    for p in all_vpk:
        parts = vpkmod.vpk_parts(p)
        rep = parts[0] if parts[0].lower().endswith("_dir.vpk") else p
        rep = os.path.abspath(rep)
        if rep not in seen:
            seen.add(rep)
            reps.append(rep)
    return reps


def _part_kind(part_path):
    """返回 (stem, kind)：kind 为 'dir' / 'vol' / 'single'。"""
    s = os.path.basename(part_path)[:-4]  # 去 .vpk
    low = s.lower()
    if low.endswith("_dir"):
        return s[:-4], "dir"
    idx = s.rfind("_")
    if idx > 0 and len(s) - idx - 1 == 3 and s[idx + 1:].isdigit():
        return s[:idx], "vol"
    return s, "single"


def _part_target_name(part_path, new_stem):
    _stem, kind = _part_kind(part_path)
    if kind == "dir":
        return new_stem + "_dir.vpk"
    if kind == "vol":
        tail = os.path.basename(part_path)[:-4].rsplit("_", 1)[1]
        return "%s_%s.vpk" % (new_stem, tail)
    return new_stem + ".vpk"


def _part_role(part_path):
    """内容指纹用的稳定角色：目录索引 / 单文件 / 第 N 个数据分卷。"""
    _stem, kind = _part_kind(part_path)
    if kind == "vol":
        tail = os.path.basename(part_path)[:-4].rsplit("_", 1)[-1]
        return kind, int(tail)
    return kind, 0


def _hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _set_signature(parts):
    """按文件角色而不是文件名生成集合指纹，改写 vpk 文件名后仍可去重。"""
    rows = []
    total_size = 0
    for path in parts:
        size = os.path.getsize(path)
        total_size += size
        rows.append((_part_role(path), size, _hash_file(path)))
    h = hashlib.sha256()
    for (kind, index), size, digest in sorted(rows):
        h.update(("%s:%d:%d:%s\n" % (kind, index, size, digest)).encode("ascii"))
    return h.hexdigest(), total_size


def _find_preview(rep, stem, kind):
    candidates = [os.path.splitext(rep)[0]]
    if kind == "dir":
        candidates.append(os.path.join(os.path.dirname(rep), stem))
    for ext in (".jpg", ".jpeg", ".png"):
        for candidate in candidates:
            if candidate and os.path.isfile(candidate + ext):
                return candidate + ext
    return ""


def _inspect_candidate(rep, archive, library):
    parts = vpkmod.vpk_parts(rep)
    stem, kind = _part_kind(parts[0])
    suffix = "_dir.vpk" if kind == "dir" else ".vpk"
    signature, total_size = _set_signature(parts)
    title = stem
    category, item, tags = "未分类", "", []
    parse_error = ""
    try:
        vpk = vpkmod.parse_vpk_dir(rep)
        info = vpkmod.extract_addoninfo(vpk)
        mission, _mission_path = vpkmod.extract_mission(vpk)
        category, item, tags = clf.classify_paths(
            vpk.paths(), addoninfo=info, mission=mission)
        if isinstance(info, dict):
            title = str(info.get("addonTitle") or "").strip() or title
        if title == stem and mission:
            title = (str(mission.get("DisplayTitle") or mission.get("Name") or "").strip()
                     or title)
    except Exception as e:  # 损坏 mod 仍展示，但禁止勾选
        parse_error = "%s: %s" % (type(e).__name__, e)
    return {
        "rep": rep,
        "parts": parts,
        "stem": stem,
        "kind": kind,
        "suffix": suffix,
        "title": title,
        "category": category,
        "item": item,
        "tags": tags,
        "size": total_size,
        "preview": _find_preview(rep, stem, kind),
        "signature": signature,
        "source_archive": archive,
        "archive_name": os.path.basename(archive),
        "parse_error": parse_error,
        "duplicate_reason": "",
        "duplicate_of": "",
        "selected": not parse_error,
    }


def _existing_sets(library):
    """返回库内及工坊订阅中的 vpk 集合，供按大小分桶后计算内容指纹。"""
    result = []
    seen_reps = set()
    for file_name in library.list_addon_files():
        rep = os.path.join(library.paths.addons_dir, file_name)
        if not os.path.isfile(rep):
            continue
        parts = vpkmod.vpk_parts(rep)
        try:
            total_size = sum(os.path.getsize(path) for path in parts)
        except OSError:
            continue
        result.append({
            "file": file_name,
            "parts": parts,
            "count": len(parts),
            "total_size": total_size,
            "signature": "",
            "source": "addons",
            "workshop_id": "",
        })
        seen_reps.add(os.path.abspath(parts[0]))
    for item in library.workshop_items():
        rep = os.path.join(library.paths.workshop_addons_dir, item["file"])
        if not os.path.isfile(rep):
            continue
        parts = vpkmod.vpk_parts(rep)
        rep = os.path.abspath(parts[0])
        if rep in seen_reps:
            continue
        try:
            total_size = sum(os.path.getsize(path) for path in parts)
        except OSError:
            continue
        workshop_id = item.get("id") or ""
        if not workshop_id:
            part_stem, _part_type = _part_kind(parts[0])
            workshop_id = part_stem if part_stem.isdigit() else ""
        result.append({
            "file": item["file"],
            "parts": parts,
            "count": len(parts),
            "total_size": total_size,
            "signature": "",
            "source": "workshop",
            "workshop_id": workshop_id,
        })
        seen_reps.add(rep)
    return result


def _mark_duplicates(candidates, library):
    """标记库内工坊 ID、完整内容指纹与压缩包内部重复项。"""
    existing = _existing_sets(library)
    buckets = {}
    for entry in existing:
        buckets.setdefault((entry["count"], entry["total_size"]), []).append(entry)

    staged_seen = {}
    duplicate_count = 0
    workshop_ids = {entry["workshop_id"] for entry in existing
                    if entry["source"] == "workshop" and entry["workshop_id"]}
    for candidate in candidates:
        reason = ""
        duplicate_of = ""
        stem = candidate["stem"]
        if stem.isdigit():
            if stem in workshop_ids:
                reason = "已在工坊订阅中"
                duplicate_of = "订阅 ID " + stem
            else:
                try:
                    match = library.find_existing_workshop(stem)
                except Exception:
                    match = None
                if match:
                    reason = "库中已有同一工坊物品"
                    duplicate_of = match.get("title") or match.get("file") or stem

        if not reason:
            bucket = buckets.get((len(candidate["parts"]), candidate["size"]), [])
            for entry in bucket:
                if not entry["signature"]:
                    entry["signature"], _size = _set_signature(entry["parts"])
                if entry["signature"] == candidate["signature"]:
                    if entry["source"] == "workshop":
                        reason = "工坊订阅中已有相同内容"
                        duplicate_of = "订阅 " + (entry["workshop_id"] or entry["file"])
                    else:
                        reason = "库中已有内容相同的 mod"
                        rec = library.store.get_mod(entry["file"]) or {}
                        duplicate_of = rec.get("title") or entry["file"]
                    break

        if not reason and candidate["signature"] in staged_seen:
            first = staged_seen[candidate["signature"]]
            reason = "压缩包内内容重复"
            duplicate_of = first["title"]

        staged_seen.setdefault(candidate["signature"], candidate)
        candidate["duplicate_reason"] = reason
        candidate["duplicate_of"] = duplicate_of
        candidate["selected"] = not reason and not candidate["parse_error"]
        if reason:
            duplicate_count += 1
    return duplicate_count


def stage_archives(archives, library, log=None, progress=None, archiver_info=None):
    """解压并解析压缩包，不在确认前写入游戏目录。"""
    archives = [os.path.abspath(path) for path in archives]
    if not archives:
        raise ImporterError("未选择压缩包")
    tmp_root = library.store.tmp_dir
    os.makedirs(tmp_root, exist_ok=True)
    work = tempfile.mkdtemp(prefix="import_", dir=tmp_root)
    batch = {"root": work, "tmp_root": tmp_root, "candidates": []}
    try:
        candidates = []
        for archive_index, archive in enumerate(archives, 1):
            if not os.path.isfile(archive):
                raise ImporterError("压缩包不存在: " + archive)
            if not supported_ext(archive):
                raise ImporterError("不支持的压缩格式: " + os.path.splitext(archive)[1])
            if progress:
                progress(archive_index, len(archives),
                         "正在解压 %s…" % os.path.basename(archive))
            if log:
                log("解压 %s…" % os.path.basename(archive))
            dest = os.path.join(work, "archive_%02d" % archive_index)
            os.makedirs(dest, exist_ok=True)
            extract_archive(archive, dest, log=log, archiver_info=archiver_info)
            reps = find_vpk_sets(dest)
            if not reps:
                raise ImporterError("%s 内未找到 .vpk 文件" % os.path.basename(archive))
            for mod_index, rep in enumerate(reps, 1):
                if progress:
                    progress(mod_index, len(reps),
                             "正在解析 %s（%d/%d）…"
                             % (os.path.basename(rep), mod_index, len(reps)))
                if log:
                    log("解析 %s" % os.path.basename(rep))
                candidates.append(_inspect_candidate(rep, archive, library))
        if not candidates:
            raise ImporterError("压缩包内未找到可导入的 mod")
        duplicate_count = _mark_duplicates(candidates, library)
        batch["candidates"] = candidates
        batch["duplicate_count"] = duplicate_count
        return batch
    except Exception:
        cleanup_staged(batch)
        raise


def cleanup_staged(batch):
    """只清理本模块创建在 data/tmp 下的暂存目录。"""
    if not batch:
        return
    root = os.path.abspath(batch.get("root") or "")
    tmp_root = os.path.abspath(batch.get("tmp_root") or "")
    if not root or not tmp_root or not os.path.isdir(root):
        return
    try:
        safe = (os.path.commonpath([root, tmp_root]) == tmp_root
                and os.path.basename(root).startswith("import_"))
    except ValueError:
        safe = False
    if safe:
        shutil.rmtree(root, ignore_errors=True)
    batch["root"] = ""
    batch["candidates"] = []


def _target_file_exists(addons_dir, stem, reserved=None):
    reserved = reserved or set()
    names = (stem + ".vpk", stem + "_dir.vpk")
    return any(name.casefold() in reserved or os.path.exists(
        os.path.join(addons_dir, name)) for name in names)


def _unique_target_stem(addons_dir, stem, reserved):
    if not _target_file_exists(addons_dir, stem, reserved):
        return stem
    number = 2
    while number <= 999:
        candidate = "%s (%d)" % (stem, number)
        if not _target_file_exists(addons_dir, candidate, reserved):
            return candidate
        number += 1
    raise ImporterError("重名过多: " + stem)


def commit_staged(batch, library, candidates=None, progress=None):
    """把用户勾选的暂存 mod 复制入库。返回新 mod 记录。"""
    selected = candidates
    if selected is None:
        selected = [c for c in batch.get("candidates", []) if c.get("selected")]
    selected = [c for c in selected
                if c.get("selected") and not c.get("duplicate_reason")
                and not c.get("parse_error")]
    if not selected:
        return []

    addons_dir = library.paths.addons_dir
    os.makedirs(addons_dir, exist_ok=True)
    reserved = set()
    assignments = []
    copied = []
    try:
        for candidate in selected:
            new_stem = _unique_target_stem(addons_dir, candidate["stem"], reserved)
            new_file = new_stem + candidate["suffix"]
            reserved.add(new_file.casefold())
            preview_target = ""
            for part in candidate["parts"]:
                target_name = _part_target_name(part, new_stem)
                target = os.path.join(addons_dir, target_name)
                reserved.add(target_name.casefold())
                shutil.copy2(part, target)
                copied.append(target)
            preview_source = candidate.get("preview") or ""
            if preview_source and os.path.isfile(preview_source):
                preview_target = os.path.join(
                    addons_dir, new_stem + os.path.splitext(preview_source)[1])
                shutil.copy2(preview_source, preview_target)
                copied.append(preview_target)
            assignments.append((candidate, new_file, preview_target))
    except Exception:
        for path in copied:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass
        raise

    results = []
    total = len(assignments)
    for index, (candidate, file_name, preview_target) in enumerate(assignments, 1):
        if progress:
            progress(index, total, candidate["title"])
        rec = library.register_new(
            file_name, source="import", enabled=False,
            preview=preview_target, title=candidate["title"])
        rec["category"] = candidate["category"]
        rec["item"] = candidate["item"]
        rec["tags"] = candidate["tags"]
        if candidate["category"] in clf.AUTO_ENABLE_CATEGORIES:
            try:
                library.set_enabled(rec["file"], True)
                rec["enabled"] = True
            except Exception:
                pass
        results.append(rec)
    library.store.save_library()
    return results


def import_archive(archive, library, log=None, progress=None, archiver_info=None):
    """兼容旧调用：完整导入一个压缩包并自动去重。"""
    batch = stage_archives(
        [archive], library, log=log, progress=progress,
        archiver_info=archiver_info)
    try:
        return commit_staged(batch, library, progress=progress)
    finally:
        cleanup_staged(batch)
