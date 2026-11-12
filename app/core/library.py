# -*- coding: utf-8 -*-
"""mod 库管理：扫描、启停（同物品互斥）、别名/归类、删除、工坊订阅迁移。

事实源是磁盘文件 + addonlist.txt；JSON 库为缓存。
启用/禁用只改写 addonlist.txt 的 "1"/"0"，mod 文件始终留在 addons 顶层。
所有会写游戏目录的操作都要求游戏处于关闭状态（调用方先检查 game.is_l4d2_running）。
"""
import os
import shutil

from . import vpk as vpkmod
from . import classify as clf
from .addonlist import AddonList
from .importer import _part_kind, _part_target_name
from .store import mod_name_sort_key, new_mod_record

WS_KEY_PREFIX = "workshop\\"


class LibraryError(Exception):
    pass


class Library(object):
    def __init__(self, store, game_paths):
        self.store = store
        self.paths = game_paths

    # ---------- 文件枚举 ----------
    def list_addon_files(self, base=None):
        """base 目录顶层 vpk 的代表文件名（多卷集合由 _dir.vpk 代表）。"""
        d = base or self.paths.addons_dir
        names = []
        if not os.path.isdir(d):
            return names
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".vpk"):
                continue
            stem = f[:-4]
            if stem.lower().endswith("_dir"):
                names.append(f)
                continue
            # 数据分卷且有对应 _dir 时跳过
            idx = stem.rfind("_")
            if idx > 0 and stem[idx + 1:].isdigit() and len(stem) - idx - 1 == 3:
                dirf = stem[:idx] + "_dir.vpk"
                if os.path.isfile(os.path.join(d, dirf)):
                    continue
            names.append(f)
        return names

    def preview_for(self, file_name):
        """预览图查找：优先磁盘上的同名图片（兼容 xxx_dir.vpk ↔ xxx.jpg）。"""
        stem0 = os.path.splitext(file_name)[0]
        stems = [stem0]
        if stem0.lower().endswith("_dir"):
            stems.append(stem0[:-4])
        for stem in stems:
            for ext in (".jpg", ".jpeg", ".png"):
                p = os.path.join(self.paths.addons_dir, stem + ext)
                if os.path.isfile(p):
                    return p
        rec = self.store.get_mod(file_name)
        if rec and rec.get("preview") and os.path.isfile(rec["preview"]):
            return rec["preview"]
        return ""

    def reveal_mod(self, file_name):
        """在资源管理器中定位 mod 及同目录封面。"""
        from . import game
        path = os.path.join(self.paths.addons_dir, file_name)
        return game.reveal_files([path, self.preview_for(file_name)])

    def find_existing_workshop(self, workshop_id):
        """按工坊 ID 查找库内已有模组；未登记但磁盘上已有目标 VPK 时也算存在。"""
        wid = str(workshop_id or "").strip()
        if not wid:
            return None
        for rec in self.store.mods().values():
            if str(rec.get("workshop_id") or "").strip() == wid:
                return rec
        # 下载流程固定落盘为 <工坊ID>.vpk；库缓存滞后时仍应避免重复下载。
        for file_name in ("%s.vpk" % wid, "%s_dir.vpk" % wid):
            if os.path.isfile(os.path.join(self.paths.addons_dir, file_name)):
                return self.store.get_mod(file_name) or new_mod_record(file_name)
        return None

    # ---------- 扫描 ----------
    def _scan_one(self, file_name):
        """返回 (record, rebuilt)。rebuilt=True 表示重新解析了 vpk。"""
        path = os.path.join(self.paths.addons_dir, file_name)
        old = self.store.get_mod(file_name)
        try:
            st = os.stat(path)
        except OSError:
            return old, False
        mtime, size = int(st.st_mtime), st.st_size
        if (old and old.get("mtime") == mtime and old.get("size") == size
                and old.get("clfv") == clf.CLF_VERSION):
            # 预览图路径可能因外部移动失效，命中缓存时顺手修正
            pv = old.get("preview") or ""
            if not pv or not os.path.isfile(pv):
                new_pv = self.preview_for(file_name)
                if new_pv != pv:
                    old["preview"] = new_pv
            return old, False

        parts = vpkmod.vpk_parts(path)
        dir_path = parts[0] if parts[0].lower().endswith("_dir.vpk") else path
        try:
            vpk = vpkmod.parse_vpk_dir(dir_path)
        except Exception as e:
            # 损坏/伪装的 vpk：按未分类占位入库（不阻断整体扫描，用户可见可删）
            rec = new_mod_record(file_name)
            try:
                st2 = os.stat(path)
                rec.update({"size": st2.st_size, "mtime": int(st2.st_mtime),
                            "title": os.path.splitext(file_name)[0]})
            except OSError:
                pass
            rec["clfv"] = clf.CLF_VERSION
            return rec, True
        info = vpkmod.extract_addoninfo(vpk)
        mission, _mpath = vpkmod.extract_mission(vpk)
        hint = (old or {}).get("title", "") or os.path.splitext(file_name)[0]
        category, item, tags = clf.classify_paths(vpk.paths(), addoninfo=info,
                                                  mission=mission, hint=hint)

        stem = os.path.splitext(file_name)[0]
        workshop_id = stem if stem.isdigit() else ""
        title = ""
        if isinstance(info, dict):
            title = str(info.get("addonTitle") or "").strip()
        if not title and mission:
            title = str(mission.get("DisplayTitle") or mission.get("Name") or "").strip()
        if not title:
            title = workshop_id or stem
        if not title or title.isdigit():
            title = (old or {}).get("title") or title  # 保留在线补全过的标题

        rec = new_mod_record(file_name)
        preview = self.preview_for(file_name) or (old or {}).get("preview", "")
        rec.update({
            "title": title,
            "category": category,
            "item": item,
            "tags": tags,
            "size": size,
            "mtime": mtime,
            "workshop_id": workshop_id,
            "clfv": clf.CLF_VERSION,
            "source": (old or {}).get("source", "scan"),
            "preview": preview or (old or {}).get("preview", ""),
        })
        if old:  # 保留用户手工设置
            rec["alias"] = old.get("alias", "")
            rec["enabled"] = old.get("enabled", False)
            if old.get("pinned"):
                rec.update({"pinned": True, "category": old["category"], "item": old["item"]})
        return rec, True

    def rescan(self, progress=None):
        """扫描 addons 顶层，启用状态以 addonlist.txt 为准。

        条目缺失按游戏行为视为启用，并在游戏关闭时补记 "1"。
        """
        from . import game as _game
        if not os.path.isdir(self.paths.addons_dir):
            # 目录不可访问（盘未挂载/被占用）时禁止差分：否则视为空库，
            # 会把全部记录连同用户别名与手工分类一并清掉
            raise LibraryError("addons 目录不可访问: %s" % self.paths.addons_dir)
        game_running = _game.is_l4d2_running()
        al = AddonList.load(self.paths.addonlist_file)
        names = self.list_addon_files()
        total = len(names)
        parsed = 0
        for i, name in enumerate(names):
            rec, rebuilt = self._scan_one(name)
            if rec is not None:
                rec["enabled"] = al.get(name, "1").strip() == "1"
                self.store.upsert_mod(rec)
                if rebuilt:
                    parsed += 1
            if progress:
                progress(i + 1, total, name)
        known = set(names)
        for name in list(self.store.mods().keys()):
            if name not in known:
                self.store.remove_mod(name)
        # 游戏关闭时补齐缺失条目（游戏会把未登记文件当新 addon 启用）
        if not game_running:
            mutate = False
            for name in names:
                if name not in al.entries:
                    al.set(name, "1")
                    mutate = True
            if mutate:
                al.save(self.paths.addonlist_file)
        self._promote_map_parts()
        self._enrich_from_workshop(progress)
        self.store.save_library()
        return {"total": total, "parsed": parsed}

    # 地图分部资源包常被误判的“模糊类别”，满足条件时提升为所属战役
    AMBIGUOUS_CATS = {"UI", "杂项", "材质特效", "未分类", "音效音乐", "其他", "载具"}

    @staticmethod
    def _core_name(name):
        import re as _re
        return _re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", (name or "").lower())

    @staticmethod
    def _title_match(map_item, mod_title):
        """地图物品名与分部标题的模糊匹配：完整核心 / ASCII核心(≥6) / 中文核心(≥2) 任一包含。"""
        mc = Library._core_name(map_item)
        tc = Library._core_name(mod_title)
        if not mc or not tc:
            return False
        if mc in tc:
            return True
        m_ascii = "".join(ch for ch in mc if not ("\u4e00" <= ch <= "\u9fff"))
        t_ascii = "".join(ch for ch in tc if not ("\u4e00" <= ch <= "\u9fff"))
        if len(m_ascii) >= 6 and m_ascii in t_ascii:
            return True
        m_cjk = "".join(ch for ch in mc if "\u4e00" <= ch <= "\u9fff")
        t_cjk = "".join(ch for ch in tc if "\u4e00" <= ch <= "\u9fff")
        if len(m_cjk) >= 2 and m_cjk in t_cjk:
            return True
        return False

    def _promote_map_parts(self):
        """地图分部（只含材质/模型的 part 资源包）继承所属战役：
        a) 合集内任一成员是具名地图 → 模糊类别的成员提升为该地图；
        b) 标题带 part/pt/第N部分 且核心名与某地图物品名匹配 → 同上。"""
        mods = self.store.mods()
        map_items = {}
        for m in mods.values():
            if m.get("category") == "地图" and m.get("item"):
                core = self._core_name(m["item"])
                if len(core) >= 4:
                    map_items[core] = m["item"]
        if not map_items:
            return 0
        import re as _re
        changed = 0
        for m in mods.values():
            if m.get("pinned"):
                continue
            # 已是地图但无具体战役名的分部（含 bsp 无 mission）也补全 item；
            # 枪械/近战-未指定（地图分部常自带自定义武器资源被误判）同样可提升
            is_map_no_item = m.get("category") == "地图" and not m.get("item")
            is_unresolved_weapon = (m.get("category") in ("枪械", "近战")
                                    and not m.get("item"))
            if not is_map_no_item and not is_unresolved_weapon \
                    and m.get("category") not in self.AMBIGUOUS_CATS:
                continue
            new_item = None
            cid = m.get("collection")
            if cid:
                info = self.store.get_collection(cid) or {}
                for f in info.get("files", []):
                    r = mods.get(f)
                    if r and r.get("category") == "地图" and r.get("item"):
                        new_item = r["item"]
                        break
            if new_item is None:
                title = m.get("title", "")
                has_marker = _re.search(r"\b(part|pt)\s*\d+", title.lower()) \
                    or _re.search(r"第\s*[一二三四五六七八九十\d]+\s*[部章分]", title)
                for _mc, item in map_items.items():
                    # 带分部标记 → 模糊匹配；无标记 → 要求标题与战役名完全同核
                    if has_marker:
                        hit = self._title_match(item, title)
                    else:
                        hit = self._core_name(item) == self._core_name(title) and len(self._core_name(title)) >= 4
                    if hit:
                        new_item = item
                        break
            if new_item:
                m["category"], m["item"] = "地图", new_item
                changed += 1
        return changed

    def _enrich_from_workshop(self, progress=None):
        """对标题缺失（数字 ID）的工坊 mod 批量拉取真实标题与预览图。离线时静默跳过。"""
        need = [r for r in self.store.mods().values()
                if r.get("workshop_id") and (not r.get("title") or r.get("title", "").isdigit())]
        if not need:
            return
        try:
            from . import steam_api
        except Exception:
            return
        ids = [r["workshop_id"] for r in need]
        details = {}
        try:
            for i in range(0, len(ids), 100):
                if progress:
                    n_done = min(i + 100, len(ids))
                    progress(n_done, len(ids), "在线补全 mod 信息 %d/%d" % (n_done, len(ids)))
                for d in steam_api.get_details(ids[i:i + 100]):
                    if d.get("result") == 1:
                        details[str(d.get("publishedfileid"))] = d
        except Exception:
            return  # 离线 / 被墙：保留现状，下次再试
        changed = False
        for r in need:
            d = details.get(r["workshop_id"])
            if not d:
                continue
            title = str(d.get("title") or "").strip()
            if title:
                r["title"] = title
                changed = True
            if not r.get("preview") and d.get("preview_url"):
                try:
                    data = steam_api.fetch_preview_bytes(str(d.get("preview_url")))
                    if data:
                        pv = os.path.join(self.store.previews_dir, "%s.jpg" % r["workshop_id"])
                        with open(pv, "wb") as f:
                            f.write(data)
                        r["preview"] = pv
                        changed = True
                except Exception:
                    pass

    def sync_enabled_from_addonlist(self):
        """只读 addonlist 校正记录状态（不写 addonlist）。"""
        al = AddonList.load(self.paths.addonlist_file)
        changed = False
        for name, rec in self.store.mods().items():
            enabled = al.get(name, "1").strip() != "0"
            if rec.get("enabled") != enabled:
                rec["enabled"] = enabled
                changed = True
        if changed:
            self.store.save_library()

    # ---------- 启停 ----------
    def _save_addonlist(self, mutate):
        al = AddonList.load(self.paths.addonlist_file)
        mutate(al)
        al.save(self.paths.addonlist_file)

    def set_enabled(self, file_name, enabled, mutex=True):
        """启用 = addonlist 记 "1"；禁用 = addonlist 记 "0"。mod 文件不移动。

        enabled=True 且该 mod 属于具体物品时，自动把同物品其余 mod 记为 "0"。
        """
        rec = self.store.get_mod(file_name)
        if rec is None:
            raise LibraryError("未知 mod: " + file_name)
        if not os.path.isfile(os.path.join(self.paths.addons_dir, file_name)):
            raise LibraryError("mod 文件不存在: " + file_name)
        disabled = []

        def mutate(al):
            al.set(file_name, "1" if enabled else "0")
            # 互斥只作用于外观类（同物品替换同一资源）；地图等叠加型内容不互斥
            if (enabled and mutex and rec.get("item")
                    and rec.get("category") in clf.CONFLICT_CATEGORIES):
                for other in list(self.store.mods().values()):
                    if (other["file"] != file_name
                            and other.get("category") == rec["category"]
                            and other.get("item") == rec["item"]
                            and other.get("enabled")):
                        al.set(other["file"], "0")
                        other["enabled"] = False
                        disabled.append(other["file"])

        self._save_addonlist(mutate)
        rec["enabled"] = enabled
        self.store.save_library()
        return disabled

    # ---------- 别名 / 归类 ----------
    def set_alias(self, file_name, alias):
        rec = self.store.get_mod(file_name)
        if rec is None:
            raise LibraryError("未知 mod: " + file_name)
        rec["alias"] = alias.strip()
        self.store.save_library()

    def set_category(self, file_name, category, item, pinned=True):
        rec = self.store.get_mod(file_name)
        if rec is None:
            raise LibraryError("未知 mod: " + file_name)
        rec["category"] = category
        rec["item"] = item or ""
        if pinned:
            rec["pinned"] = True
        self.store.save_library()

    # ---------- 删除 ----------
    def delete_mod(self, file_name):
        """移入 data/trash/（不直接删除），同时清理 addonlist 条目与合集。"""
        rec = self.store.get_mod(file_name)
        src = os.path.join(self.paths.addons_dir, file_name)
        parts = vpkmod.vpk_parts(src) if os.path.isfile(src) else []
        stem0 = os.path.splitext(file_name)[0]
        stems = [stem0]
        if stem0.lower().endswith("_dir"):
            stems.append(stem0[:-4])
        trash = self.store.trash_dir
        targets = list(parts)
        for stem in stems:
            for ext in (".jpg", ".jpeg", ".png"):
                targets.append(os.path.join(self.paths.addons_dir, stem + ext))
        for p_ in targets:
            if os.path.isfile(p_):
                dst = os.path.join(trash, os.path.basename(p_))
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.move(p_, dst)
                except OSError:
                    pass
        self._save_addonlist(lambda al: al.remove(file_name))
        # 从所属合集中摘除
        cid = (rec or {}).get("collection")
        if cid:
            info = self.store.get_collection(cid)
            if info:
                if file_name in info.get("files", []):
                    info["files"].remove(file_name)
                if not info.get("files"):
                    self.store.remove_collection(cid)
            self.store.save_library()
        if rec:
            self.store.remove_mod(file_name)
        self.store.save_library()

    # ---------- 工坊订阅迁移 ----------
    def workshop_items(self):
        """addons/workshop/ 下的订阅项 [{file, id, jpg}]。"""
        d = self.paths.workshop_addons_dir
        out = []
        if not os.path.isdir(d):
            return out
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".vpk"):
                continue
            stem = os.path.splitext(f)[0]
            jpg = ""
            for ext in (".jpg", ".jpeg", ".png"):
                p = os.path.join(d, stem + ext)
                if os.path.isfile(p):
                    jpg = p
                    break
            out.append({"file": f, "id": stem if stem.isdigit() else "", "jpg": jpg})
        return out

    def migrate_from_workshop(self, file_names, progress=None):
        """把 addons/workshop/ 的 vpk(+jpg) 移到 addons 顶层，保留其启用状态。

        若顶层已存在同名同大小的文件（Steam 把移走的 mod 重新同步回来的副本），
        直接清理 workshop 侧的重复副本（Steam 云端有源可随时重下）。
        无 addonlist 条目时按启用处理（workshop 目录本来就会被游戏加载）。
        """
        moved, errors, deduped = [], [], []
        al = AddonList.load(self.paths.addonlist_file)
        for i, f in enumerate(file_names):
            src = os.path.join(self.paths.workshop_addons_dir, f)
            dst = os.path.join(self.paths.addons_dir, f)
            if progress:
                progress(i + 1, len(file_names), f)
            if not os.path.isfile(src):
                errors.append((f, "源文件不存在"))
                continue
            ws_key = WS_KEY_PREFIX + f
            has_old = ws_key in al.entries
            old_val = al.get(ws_key, "1") if has_old else "1"
            if os.path.exists(dst):
                # 顶层已有同名文件：同大小 → Steam 重新同步的重复副本，清理之
                try:
                    same = (os.path.getsize(src) == os.path.getsize(dst))
                except OSError:
                    same = False
                if same:
                    try:
                        os.remove(src)
                        stem0 = os.path.splitext(f)[0]
                        for ext in (".jpg", ".jpeg", ".png"):
                            j = os.path.join(self.paths.workshop_addons_dir, stem0 + ext)
                            if os.path.isfile(j):
                                os.remove(j)
                        if has_old:
                            al.remove(ws_key)
                        if f not in al.entries:
                            al.set(f, "1")
                        deduped.append(f)
                        continue
                    except OSError as e:
                        errors.append((f, "清理重复副本失败: %s" % e))
                        continue
                errors.append((f, "addons 顶层已存在同名文件"))
                continue
            try:
                shutil.move(src, dst)
            except OSError as e:
                errors.append((f, "移动失败: %s" % e))
                continue
            stem = os.path.splitext(f)[0]
            for ext in (".jpg", ".jpeg", ".png"):
                j = os.path.join(self.paths.workshop_addons_dir, stem + ext)
                if os.path.isfile(j):
                    try:
                        shutil.move(j, os.path.join(self.paths.addons_dir, stem + ext))
                    except OSError:
                        pass
                    break
            enabled = old_val.strip() == "1"
            if has_old:
                al.rename_key(ws_key, f)
            al.set(f, "1" if enabled else "0")
            moved.append((f, enabled))
        al.save(self.paths.addonlist_file)
        # 重建这批文件的记录
        for f, enabled in moved:
            rec, _rebuilt = self._scan_one(f)
            if rec is None:
                rec = new_mod_record(f)
            rec["enabled"] = enabled
            rec["source"] = "migrate"
            self.store.upsert_mod(rec)
        self.store.save_library()
        return moved, errors, deduped

    # ---------- 新 mod 入库（下载 / 导入后调用） ----------
    def register_new(self, file_name, source, enabled=False, preview="", title="",
                     workshop_id=""):
        """addons 顶层已有文件 → 解析归类 → 记录 → addonlist 登记（1/0）。"""
        rec, _rebuilt = self._scan_one(file_name)
        if rec is None:
            rec = new_mod_record(file_name)
        rec["source"] = source
        rec["enabled"] = enabled
        rec["workshop_id"] = workshop_id or rec.get("workshop_id", "")
        if title:
            rec["title"] = title
        if preview:
            rec["preview"] = preview
        self.store.upsert_mod(rec)
        self._save_addonlist(lambda al: al.set(file_name, "1" if enabled else "0"))
        self.store.save_library()
        return rec

    # ---------- 一键纳入管理 ----------
    def _enabled_before_adopt(self, al):
        """记录一键整理前会生效的顶层/工坊文件名。"""
        before = set()
        for key, value in al.entries.items():
            if str(value).strip() != "1":
                continue
            if key.lower().startswith(WS_KEY_PREFIX):
                before.add(key[len(WS_KEY_PREFIX):])
            else:
                before.add(key)
        # 游戏把 addonlist 中缺失的顶层条目视为启用。
        for name in self.list_addon_files():
            if name not in al.entries:
                before.add(name)
        # workshop 中的新订阅即使暂未写入 addonlist，也会被游戏加载。
        for item in self.workshop_items():
            file_name = item["file"]
            ws_key = WS_KEY_PREFIX + file_name
            if ws_key not in al.entries or al.get(ws_key) == "1":
                before.add(file_name)
        return before

    def _settle_conflict_selections(self, al, before_enabled):
        """保证外观冲突组只启用一个，并返回本次被自动禁用的文件名。"""
        groups = {}
        for rec in self.store.mods().values():
            category = rec.get("category")
            item = rec.get("item")
            if category in clf.CONFLICT_CATEGORIES and item:
                groups.setdefault((category, item), []).append(rec)

        disabled = []
        for candidates in groups.values():
            if len(candidates) < 2:
                continue
            ordered = sorted(candidates, key=mod_name_sort_key)
            enabled = [r for r in candidates if r.get("enabled")]
            preferred = [r for r in enabled if r["file"] in before_enabled]
            winner = (preferred or enabled or ordered)[0]
            winner_file = winner["file"]
            for rec in candidates:
                want = rec["file"] == winner_file
                was_enabled = bool(rec.get("enabled"))
                if was_enabled and not want:
                    disabled.append(rec["file"])
                rec["enabled"] = want
                al.set(rec["file"], "1" if want else "0")
        return disabled

    def adopt_all(self, progress=None):
        """递归扫描 addons 目录，把所有 vpk 纳入管理策略。

        - 顶层未登记文件：补记 addonlist（值 "1"，保持游戏当前加载行为）
        - 子目录（非 workshop）：游戏本就不扫描，整组移到顶层并记 "0"（禁用）
        - workshop 子目录：走迁移逻辑（保留启用状态、改写键名）
        返回 stats：{adopted, moved, migrated, conflicts, errors}
        """
        stats = {"adopted": 0, "moved": 0, "migrated": 0, "deduped": 0,
                 "auto_enabled": 0, "auto_disabled": 0,
                 "migrated_ids": [], "conflicts": [], "errors": []}
        if not self.paths.valid():
            raise LibraryError("游戏目录无效")
        al = AddonList.load(self.paths.addonlist_file)
        before_enabled = self._enabled_before_adopt(al)

        # 1) workshop 子目录 → 迁移（全部订阅项移出并纳管）
        ws_items = [it["file"] for it in self.workshop_items()]
        if ws_items:
            if progress:
                progress("迁移 workshop 订阅项…", 0)
            moved, errors, deduped = self.migrate_from_workshop(ws_items)
            stats["migrated"] = len(moved)
            stats["deduped"] = len(deduped)
            ids = [os.path.splitext(f)[0] for f, _e in moved]
            ids += [os.path.splitext(f)[0] for f in deduped]
            stats["migrated_ids"] = [i for i in ids if i.isdigit()]
            stats["errors"].extend("%s: %s" % e for e in errors)
            al = AddonList.load(self.paths.addonlist_file)  # migrate 内部已保存，重载

        # 2) 递归找子目录里的 vpk 集合（排除 workshop）
        subdir_reps = []
        seen = set()
        for dirpath, dirs, files in os.walk(self.paths.addons_dir):
            rel = os.path.relpath(dirpath, self.paths.addons_dir).lower()
            if rel == "workshop" or rel.startswith("workshop" + os.sep):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d.lower() != "workshop"]
            for f in sorted(files):
                if not f.lower().endswith(".vpk"):
                    continue
                full = os.path.join(dirpath, f)
                parts = vpkmod.vpk_parts(full)
                rep = os.path.abspath(parts[0])
                if rep in seen:
                    continue
                seen.add(rep)
                if os.path.dirname(rep).lower() == os.path.abspath(self.paths.addons_dir).lower():
                    continue  # 顶层文件走第 3 步
                subdir_reps.append(parts)

        # 3) 子目录集合移到顶层
        for i, parts in enumerate(subdir_reps):
            if progress:
                progress("移动子目录 mod…", i + 1, os.path.basename(parts[0]))
            stem, kind = _part_kind(parts[0])
            suffix = "_dir.vpk" if kind == "dir" else ".vpk"
            new_stem = stem
            n = 2
            while os.path.exists(os.path.join(self.paths.addons_dir, new_stem + suffix)):
                new_stem = "%s (%d)" % (stem, n)
                n += 1
            try:
                for p_ in parts:
                    dst = os.path.join(self.paths.addons_dir, _part_target_name(p_, new_stem))
                    if os.path.exists(dst):
                        raise OSError("目标已存在: " + os.path.basename(dst))
                for p_ in parts:  # 先全部确认再移动（子目录 mod 默认禁用 → addonlist 记 0）
                    shutil.move(p_, os.path.join(self.paths.addons_dir,
                                                 _part_target_name(p_, new_stem)))
            except OSError as e:
                stats["errors"].append(str(e))
                continue
            name = new_stem + suffix
            al.set(name, "0")
            rec, _rb = self._scan_one(name)
            if rec is not None:
                rec["enabled"] = False
                rec["source"] = "adopt"
                self.store.upsert_mod(rec)
            stats["moved"] += 1

        # 4) 顶层未登记文件 → 补记（保持加载状态）
        top_names = self.list_addon_files()
        for i, name in enumerate(top_names):
            if progress:
                progress("登记顶层 mod…", i + 1, name)
            if name in al.entries:
                continue
            rec, _rb = self._scan_one(name)
            if rec is None:
                continue
            rec["enabled"] = True
            rec["source"] = rec.get("source") or "adopt"
            self.store.upsert_mod(rec)
            al.set(name, "1")
            stats["adopted"] += 1

        enabled_before_settle = set(r["file"] for r in self.store.mods().values()
                                    if r.get("enabled"))
        disabled = self._settle_conflict_selections(al, before_enabled)
        stats["auto_disabled"] = len(disabled)
        stats["auto_enabled"] = sum(
            1 for rec in self.store.mods().values()
            if rec.get("enabled") and rec["file"] not in enabled_before_settle)
        al.save(self.paths.addonlist_file)
        self.store.save_library()
        return stats
