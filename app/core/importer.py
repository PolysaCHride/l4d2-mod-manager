# -*- coding: utf-8 -*-
"""压缩包导入：zip 用 zipfile；7z/rar 调 WinRAR/7-Zip 命令行。

安全约定：解包目标固定在 data/tmp/ 下的新目录；zip 条目做路径穿越校验；
解出的 vpk 只解析数据，不执行任何内容。
"""
import os
import shutil
import subprocess
import zipfile

from . import vpk as vpkmod
from . import classify as clf

ZIP_EXTS = (".zip",)


class ImporterError(Exception):
    pass


def supported_ext(path):
    return path.lower().endswith(ZIP_EXTS + (".7z", ".rar"))


def find_archiver():
    from . import paths as _paths
    return _paths.find_archiver()


def extract_archive(archive, dest_dir, log=None):
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
        exe, kind = find_archiver()
        if not exe:
            raise ImporterError("未找到 WinRAR/7-Zip，无法解压 %s 文件" % os.path.splitext(archive)[1])
        os.makedirs(dest_dir, exist_ok=True)
        if kind == "winrar":
            cmd = [exe, "x", "-ibck", "-y", "--", archive, dest_dir + os.sep]
        else:
            cmd = [exe, "x", "-y", "-o" + dest_dir, "--", archive]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        if proc.returncode != 0:
            raise ImporterError("解压失败（%s）：%s" %
                                (os.path.basename(exe), (proc.stderr or proc.stdout or "")[-200:]))
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


def import_archive(archive, library, log=None, progress=None):
    """完整导入一个压缩包。返回导入记录列表。"""
    tmp_root = library.store.tmp_dir
    work = os.path.join(tmp_root, "import_%d" % os.getpid())
    if os.path.isdir(work):
        shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    try:
        if log:
            log("解压 %s…" % os.path.basename(archive))
        extract_archive(archive, work, log=log)
        reps = find_vpk_sets(work)
        if not reps:
            raise ImporterError("压缩包内未找到 .vpk 文件")
        results = []
        total = len(reps)
        for i, rep in enumerate(reps):
            if progress:
                progress(i + 1, total, os.path.basename(rep))
            parts = vpkmod.vpk_parts(rep)
            stem, kind = _part_kind(parts[0])
            suffix = "_dir.vpk" if kind == "dir" else ".vpk"

            # 目标名唯一化（同时避开单文件名与 _dir 集名的冲突）
            new_stem = stem
            n = 2
            while (os.path.exists(os.path.join(library.paths.addons_dir, new_stem + suffix))
                   or os.path.exists(os.path.join(library.paths.addons_dir, new_stem + ".vpk"))
                   or os.path.exists(os.path.join(library.paths.addons_dir, new_stem + "_dir.vpk"))):
                new_stem = "%s (%d)" % (stem, n)
                n += 1
                if n > 99:
                    raise ImporterError("重名过多: " + os.path.basename(rep))

            for p in parts:
                shutil.copy2(p, os.path.join(library.paths.addons_dir,
                                             _part_target_name(p, new_stem)))

            # 顺带导入旁边的预览图（xxx_dir.jpg / xxx.jpg）
            prev_src = ""
            candidates = [os.path.splitext(rep)[0]]
            if kind == "dir":
                candidates.append(os.path.join(os.path.dirname(rep), stem))
            for ext in (".jpg", ".jpeg", ".png"):
                for c in candidates:
                    if c and os.path.isfile(c + ext):
                        prev_src = c + ext
                        break
                if prev_src:
                    break
            if prev_src:
                shutil.copy2(prev_src, os.path.join(
                    library.paths.addons_dir, new_stem + os.path.splitext(prev_src)[1]))

            # 解析归类（读已拷入 addons 的目标文件）
            dir_path = os.path.join(library.paths.addons_dir, new_stem + suffix)
            vpk = vpkmod.parse_vpk_dir(dir_path)
            info = vpkmod.extract_addoninfo(vpk)
            mission, _m = vpkmod.extract_mission(vpk)
            category, item, tags = clf.classify_paths(vpk.paths(), addoninfo=info, mission=mission)
            title = ""
            if isinstance(info, dict):
                title = str(info.get("addonTitle") or "").strip()
            if not title and mission:
                title = str(mission.get("DisplayTitle") or mission.get("Name") or "").strip()
            rec = library.register_new(new_stem + suffix, source="import",
                                       enabled=False, title=title)
            rec["category"], rec["item"], rec["tags"] = category, item, tags
            # 下载即用类（地图/音效等）导入即启用；冲突类/未分类默认禁用
            if category in clf.AUTO_ENABLE_CATEGORIES:
                try:
                    library.set_enabled(rec["file"], True)
                    rec["enabled"] = True
                except Exception:
                    pass
            results.append(rec)
        library.store.save_library()
        return results
    finally:
        shutil.rmtree(work, ignore_errors=True)
