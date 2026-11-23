# -*- coding: utf-8 -*-
"""mod 库管理：扫描、启停（同物品互斥，可开关）、别名/归类、删除、工坊订阅迁移。

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
from .store import mod_display_name, mod_name_sort_key, new_mod_record

WS_KEY_PREFIX = "workshop\\"


MUTEX_OFF_SETTING = "mutex_off_groups"


def group_key_str(key):
    """把 `(分类, 物品)` 压成能进 JSON 的字符串键（NUL 分隔，名字里不会有）。"""
    if not key:
        return ""
    return "\u0000".join([str(key[0]), str(key[1])])


def group_key_tuple(raw):
    """`group_key_str` 的逆运算；形状不对返回 None。"""
    parts = str(raw or "").split("\u0000")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return (parts[0], parts[1])


def conflict_key(rec):
    """互斥组键 `(分类, 物品)`；这个模组不参与互斥时返回 None。

    参与条件（三条全满足）：
      · 分类在 `clf.CONFLICT_CATEGORIES` 里（角色/特感/枪械/近战/医疗品/投掷）
        —— 这些是「同一物品换同一份资源」的外观类，同时启用只有最后一个生效；
        地图/音效/UI 等是叠加型内容，本来就能共存。
      · `item` 非空 —— 「未指定」是个垃圾桶，里面可能是完全不同的东西
        （一个 UI 皮肤 + 一个音效包），强行互斥会误伤。
      · 记录本身存在。

    ⚠️ 组键是 `(分类, 物品)` —— 也就是**一个具体子分类**（Nick / AK-47 …）。
    互斥开关是按这个组各开各关的（`mutex_on`），不是全局一个。
    """
    if not rec:
        return None
    cat = rec.get("category")
    item = rec.get("item")
    if not item or cat not in clf.CONFLICT_CATEGORIES:
        return None
    return (cat, item)


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
        old_title = str((old or {}).get("title") or "").strip()

        # ---- 标题的优先级（2026-11-21 修正）----
        # 1. addoninfo 的标题（作者自己写在包里的，通常是繁体/多语言混排的原始名）
        # 2. mission 的 DisplayTitle（战役名）
        # 3. 工坊 ID / 文件名
        # 4. **已有的旧标题 —— 但如果它来自工坊在线补全，要保住**
        #
        # 为什么需要 4：`_enrich_from_workshop()` 会用工坊接口拉到**更干净**的标题
        # （作者上传时填的英文名），比 vpk 里的 addoninfo 更可读。
        # 重扫时若无条件用 addoninfo 覆盖，会把这批在线结果冲掉 ——
        # 实测一次重扫让 136 个标题变化，其中 11 组变成「多个不同文件同名」
        # （Divine Cybermancy × 4、地心引力 × 4 …），用户完全分不清谁是谁。
        #
        # 判定「旧标题更值得保留」的依据：旧标题非空、不是纯数字/文件名，
        # 且新标题为空或是纯数字（即取不到好名字）。
        # 反之，旧标题是纯数字而新标题有内容 → 采信新标题（这是本次修的大小写 bug）。
        def _is_junk(t):
            """标题是不是"没信息量"的：空、纯数字、或就是文件名主干。"""
            t = str(t or "").strip()
            if not t:
                return True
            if t.isdigit():
                return True
            if t.lower() == stem.lower():
                return True
            return False

        title = ""
        if isinstance(info, dict):
            # 键名大小写不统一（AddonTitle / addontitle 都常见），必须忽略大小写查。
            # 只写 info.get("addonTitle") 会让后者全部退化成工坊 ID。
            title = str(vpkmod.lookup_ci(info, "AddonTitle") or "").strip()
        if not title and mission:
            title = str(mission.get("DisplayTitle") or mission.get("Name") or "").strip()
        if not title:
            title = workshop_id or stem

        # mission 的 DisplayTitle 是**游戏里显示的战役名**，比 addoninfo 更权威。
        # 但多部件地图的每个部件共用同一个 mission（DisplayTitle 相同），
        # 而 addoninfo 常带 "Part 2/4" 这类区分信息 —— 所以只在
        # 「mission 标题是在 addoninfo 标题基础上补充信息」时才采信 mission。
        #   例："We Don't Go To Ravenholm"（addoninfo）
        #       vs "We Don't Go To Ravenholm 2"（mission）→ 用 mission
        if isinstance(mission, dict) and title:
            m_title = str(mission.get("DisplayTitle") or mission.get("Name") or "").strip()
            if m_title and m_title != title and m_title.startswith(title):
                title = m_title

        # 旧标题更好时保住它（详见上面 4 的说明）
        if old_title and not _is_junk(old_title) and _is_junk(title):
            title = old_title
        if not title or title.isdigit():
            title = old_title or title

        # `title_locked`：该标题来自工坊在线补全（或用户手工改过），重扫时不覆盖。
        # 这是在 2026-11-21 修标题 bug 时引入的 —— 因为库里没有记录标题来源，
        # 无法事后区分「vpk 自带的」和「在线拉的」，只能显式标记一次。
        # 迁移脚本见 docs/DATA_SCHEMA.md §2.4。
        if (old or {}).get("title_locked"):
            title = old_title or title

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
            # 用户改过分类：记录的分类器结果要跨重扫保住，否则重扫后
            # 前端就分不清「哪个是管理器识别的、哪个是用户设的」。
            if "auto_category" in old:
                rec["auto_category"] = old["auto_category"]
                rec["auto_item"] = old.get("auto_item", "")
            # 标题来自工坊在线补全 → 重扫不要覆盖，且下次重扫仍然要认得这个标记。
            # 不保留的话，一次重扫就把标记冲掉，第二次重扫又开始用 addoninfo 的差标题。
            if old.get("title_locked"):
                rec["title_locked"] = True
                if old.get("title"):
                    rec["title"] = old["title"]
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
                # 标记这个标题来自工坊 API，重扫时不要被 vpk 里的 addoninfo 覆盖
                r["title_locked"] = True
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

    # ---------- 同组互斥开关（按子分类各开各关） ----------
    def mutex_off_groups(self):
        """被用户**关掉**互斥的组键集合。缺省为空 = 每个组都开着。

        存的是「关掉的」而不是「打开的」：新出现的子分类（新武器、新角色）
        默认就带互斥，不需要用户一个个去开。
        """
        raw = self.store.settings().get(MUTEX_OFF_SETTING) or []
        out = set()
        for item in raw:
            key = group_key_tuple(item)
            if key:
                out.add(key)
        return out

    def mutex_on(self, key):
        """这个互斥组的开关是否打开；`key` 为 None（不参与互斥）时恒 False。"""
        if not key:
            return False
        return key not in self.mutex_off_groups()

    def set_group_mutex(self, category, item, enabled):
        """单独设置某个 `(分类, 物品)` 的互斥开关，返回写后的值。

        只动这一个组，不碰别的子分类 —— 用户在 Nick 里关掉，AK-47 那边
        仍然是开着（用户 2026-11-22 的明确要求）。
        """
        key = (str(category or ""), str(item or ""))
        if not key[0] or not key[1]:
            raise LibraryError("缺少分类或子分类，无法设置互斥")
        off = self.mutex_off_groups()
        if enabled:
            off.discard(key)
        else:
            off.add(key)
        self.store.set_setting(MUTEX_OFF_SETTING,
                               sorted(group_key_str(k) for k in off))
        return bool(enabled)

    def set_enabled(self, file_name, enabled, mutex=None):
        """启用 = addonlist 记 "1"；禁用 = addonlist 记 "0"。mod 文件不移动。

        `mutex=None`（默认）时按**该子分类自己的开关**（`mutex_on`）决定；
        传 True/False 则强制开/关（测试与旧调用点用）。

        互斥生效且本次是**启用**时，会把同 `(分类, 物品)` 其余已启用的模组
        一并记为 "0"，并把它们的文件名作为返回值交出去，让界面能说清
        「顺带停用了谁」。

        互斥只作用于 `CONFLICT_CATEGORIES` 里那些外观类、且 item 非空的模组
        （见 `conflict_key`）。地图 / 音效 / UI 等叠加型内容不互斥，
        「未指定」也不互斥。
        """
        rec = self.store.get_mod(file_name)
        if rec is None:
            raise LibraryError("未知 mod: " + file_name)
        if not os.path.isfile(os.path.join(self.paths.addons_dir, file_name)):
            raise LibraryError("mod 文件不存在: " + file_name)
        disabled = []
        key = conflict_key(rec) if enabled else None
        if key is not None:
            # mutex=None（默认）：看不传，按这个组**自己的**开关决定。
            # 显式传 True/False 时以调用方为准（旧调用点、测试用）。
            on = self.mutex_on(key) if mutex is None else bool(mutex)
            if not on:
                key = None

        def mutate(al):
            al.set(file_name, "1" if enabled else "0")
            if key is None:
                return
            for other in list(self.store.mods().values()):
                if (other["file"] != file_name
                        and conflict_key(other) == key
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

    def restore_auto_category(self, file_name):
        """把被用户手工改过的分类恢复成分类器原本的判定。

        用户改错分类是很常见的（尤其看到「识别为 X」才发现自己选错了）。
        没有这个出口的话，一旦 set_category 就把 auto_* 冻结、category 变成用户值，
        用户只能手工再选一次分类 —— 而那等于又写了一份用户值，回不到「自动」。

        前提：auto_category 必须存在（即用户确实改过分类）。
        恢复后清掉 pinned，让后续重扫重新接管这个模组的分类。
        """
        rec = self.store.get_mod(file_name)
        if rec is None:
            raise LibraryError("未知 mod: " + file_name)
        if "auto_category" not in rec:
            raise LibraryError("该 mod 的分类从未被手工修改过: " + file_name)
        rec["category"] = rec.get("auto_category", "") or "未分类"
        rec["item"] = rec.get("auto_item", "") or ""
        rec.pop("auto_category", None)
        rec.pop("auto_item", None)
        rec.pop("pinned", None)
        self.store.save_library()

    def set_category(self, file_name, category, item, pinned=True):
        rec = self.store.get_mod(file_name)
        if rec is None:
            raise LibraryError("未知 mod: " + file_name)
        # 用户第一次手工改分类时，把分类器原本给出的结果留一份到 auto_*。
        # 之后 category/item 归用户所有，auto_* 不再被覆盖 —— 它是「管理器认为它是什么」。
        # 前端据此把识别结果置灰展示，让用户看得见自己覆盖掉了什么。
        # 只在第一次捕获：重复修改分类不应把 auto_* 改成上一次的用户值。
        if "auto_category" not in rec:
            rec["auto_category"] = rec.get("category", "")
            rec["auto_item"] = rec.get("item", "")
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

    def enable_new_mods(self, file_names, mutex=None):
        """批量启用新入库的 mod，返回被自动停用的文件名列表。

        `mutex=False`（界面上的「同组互斥」关着）：
            全部设为启用，谁也不动。返回值恒为空。

        `mutex=True`（开关打开）：按用户 2026-11-22 裁定的三条规则：
          1. 某个互斥组在这次导入**之前**已经有启用项 → 这批里的同组新模组
             **只入库不启用**（用户已明确表示过用哪个，新来的不顶掉它）。
          2. 某个互斥组之前一个启用项都没有 → 这批里的同组模组**自动启用**，
             但一组只留一个，按**名称排序取第一个**（确定性最强，和 v1.2.1 一致）。
          3. 不参与互斥的分类（地图/音效/UI/未指定…）照旧全部启用。

        注意「之前」的判定：先把本批文件从 `enabled` 视图里排除，再判断组里
        是否还有别的启用项。否则同批第二个模组会把第一个当成「已有启用」。
        """
        names = [str(name) for name in file_names if name]
        if not names:
            return []
        al = AddonList.load(self.paths.addonlist_file)
        batch = set(names)

        # 参与互斥的组 = 有空 item、且在 CONFLICT_CATEGORIES 里、且**该组开关是开的**。
        # mutex 参数是「全局开关」（False = 一律不互斥，只给测试/旧调用点用）；
        # 默认 None 表示逐组按 `mutex_on()` 判断 —— 这样关掉 Nick 的互斥
        # 不会影响 AK-47。
        def _active(key):
            if key is None:
                return False
            return self.mutex_on(key) if mutex is None else bool(mutex)

        # 每个互斥组在这次导入之前是否已经有人启用
        pre_enabled = {}
        for other in list(self.store.mods().values()):
            if other["file"] in batch or not other.get("enabled"):
                continue
            key = conflict_key(other)
            if _active(key):
                pre_enabled[key] = True

        # 同批里按组挑一个「赢家」：名称排序第一个
        winners = {}
        groups = {}
        for name in names:
            key = conflict_key(self.store.get_mod(name))
            if _active(key):
                groups.setdefault(key, []).append(name)
        for key, files in groups.items():
            if pre_enabled.get(key):
                continue                        # 组里已有用户的选择，本批全部不启用
            ordered = sorted(
                files,
                key=lambda f: mod_name_sort_key(self.store.get_mod(f) or {"file": f}))
            winners[key] = ordered[0]           # 名称第一个

        disabled = []
        for name in names:
            rec = self.store.get_mod(name)
            if rec is None:
                continue
            key = conflict_key(rec)
            enable = True
            if _active(key):
                enable = (winners.get(key) == name)
                if not enable and rec.get("enabled"):
                    disabled.append(name)
            al.set(name, "1" if enable else "0")
            rec["enabled"] = enable
            if enable and _active(key):
                # 组内其余已启用的（含本批之外的老模组）一并停用 ——
                # 只在「组里之前没人启用」的分支才会走到这里，
                # 所以这里实际最多命中同一批的落选者，不会误伤用户的选择。
                for other in list(self.store.mods().values()):
                    if (other["file"] != name and conflict_key(other) == key
                            and other.get("enabled")):
                        al.set(other["file"], "0")
                        other["enabled"] = False
                        disabled.append(other["file"])
        al.save(self.paths.addonlist_file)
        self.store.save_library()
        return disabled

    # ---------- 一键纳入管理 ----------
    def adopt_all(self, progress=None, mutex=False):
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

        # 1) workshop 子目录 → 迁移（全部订阅项移出并纳管）
        ws_items = [it["file"] for it in self.workshop_items()]
        if ws_items:
            if progress:
                # progress 签名统一为 (text, done, total)：这里总数未知，给 0。
                # 原来少传一个参数，任何按 (text, i, n) 实现的回调都会在这里 TypeError。
                progress("迁移 workshop 订阅项…", 0, 0)
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

        # 4) 顶层未登记文件 → 补记（保持游戏里的加载状态）
        #
        # ⚠️ 这里的「已登记」判的是**管理器自己的库**（store），不是 addonlist.txt。
        # addonlist.txt 是游戏自己维护的：只要装过 / 订阅过模组，里面就已经有
        # 全部条目。以前这里写的是 `if name in al.entries: continue`，
        # 结果真实游戏目录（首次整理时 addonlist 早已填满）会把每一个 vpk 都跳过，
        # 整理完库还是空的 —— v1.3 发行版实测就是这个现象。
        top_names = self.list_addon_files()
        for i, name in enumerate(top_names):
            if progress:
                progress("登记顶层 mod…", i + 1, name)
            if self.store.get_mod(name) is not None:
                continue          # 已在库里，启用状态由 rescan 维护，不重复解析
            rec, _rb = self._scan_one(name)
            if rec is None:
                continue
            # 以 addonlist 为准：里面记着 "0" 的，整理之后仍然停用。
            # 以前无条件写 True，会把用户在游戏里手动关掉的模组又打开。
            rec["enabled"] = al.get(name, "1").strip() == "1"
            rec["source"] = rec.get("source") or "adopt"
            self.store.upsert_mod(rec)
            if name not in al.entries:
                al.set(name, "1")
                rec["enabled"] = True
            stats["adopted"] += 1

        # 2026-11-22：互斥回归，但**由界面开关决定**（用户裁定「以管理器自己的
        # addonlist 快照为准，冲突时以管理器为第一视角」）。
        # 开关打开时，整理会把每个互斥组收敛到一个启用项：
        #   · 组里原本就记着启用的那些 → 保留（多个时取名称排序第一个）
        #   · 组里一个都没启用 → 保持全停用，不主动帮你开
        # 只改启用状态，不动任何文件。
        # 只收敛「开关开着」的组；用户单独关掉的那个子分类不许动。
        # 互斥按子分类独立（用户 2026-11-22），所以这里逐组查开关，
        # 不再有「全局开 / 关」这一层。
        open_keys = [k for k in self._all_conflict_keys() if self.mutex_on(k)]
        disabled, enabled_extra = self._settle_conflicts(al, only=open_keys)
        stats["auto_disabled"] = len(disabled)
        stats["auto_enabled"] = len(enabled_extra)
        al.save(self.paths.addonlist_file)
        self.store.save_library()
        return stats

    def _settle_conflicts(self, al, only=None, winner=None):
        """把每个互斥组收敛到只剩一个启用项，返回 (被停用, 被启用) 文件名列表。

        `only` 为 `(分类, 物品)` 或键的集合时只处理这些组（界面上「只收敛
        当前子分类」用）；省略则处理全库（「整理」用）。

        `winner` 指定要保留哪个文件（界面上用户在冲突弹窗里点选的那个）；
        省略时按名称排序取第一个。指定的那一项如果当前是停用的，会被**启用**
        （用户在弹窗里明确选了它，就该按他选的来）。

        取舍规则（用户 2026-11-22 裁定「保留管理器原本记着启用的那个」）：
          1. 组里只有一个启用项 → 不动它；
          2. 组里有多个启用项 → 保留 winner，其余写 "0"；
          3. 组里一个都没启用 → 全组保持停用，**不主动启用任何东西**
             （整理是「接管现有文件」，不是「帮你开始玩」）。
        """
        wanted = None
        if only is not None:
            if isinstance(only, tuple):
                wanted = {only}
            else:
                wanted = set(tuple(k) for k in only if k)

        groups = {}
        for rec in list(self.store.mods().values()):
            key = conflict_key(rec)
            if key is None:
                continue
            if wanted is not None and key not in wanted:
                continue
            groups.setdefault(key, []).append(rec)

        disabled, enabled_extra = [], []
        for key, members in groups.items():
            # 用户在弹窗里点选了要保留的那个 → 优先
            chosen = None
            if winner:
                chosen = next((r for r in members if r["file"] == winner), None)
            if chosen is not None:
                if not chosen.get("enabled"):
                    al.set(chosen["file"], "1")
                    chosen["enabled"] = True
                    enabled_extra.append(chosen["file"])
                for rec in members:
                    if rec["file"] == chosen["file"] or not rec.get("enabled"):
                        continue
                    al.set(rec["file"], "0")
                    rec["enabled"] = False
                    disabled.append(rec["file"])
                continue

            active = [r for r in members if r.get("enabled")]
            if len(active) <= 1:
                continue                      # 0 个或 1 个都无需收敛
            keep = sorted(active, key=mod_name_sort_key)[0]
            for rec in active:
                if rec["file"] == keep["file"]:
                    continue
                al.set(rec["file"], "0")
                rec["enabled"] = False
                disabled.append(rec["file"])
        return disabled, enabled_extra

    def _all_conflict_keys(self):
        """库里出现过的全部互斥组键（不管开没开）。"""
        keys = set()
        for rec in list(self.store.mods().values()):
            key = conflict_key(rec)
            if key is not None:
                keys.add(key)
        return keys

    def conflict_groups(self, only=None):
        """列出**当前存在冲突**的互斥组（一组里两个及以上启用）。

        `only` 可以是 `(分类, 物品)` 或一组这样的键 —— 只检查这些组。
        界面在某个子分类里点开关时只该看到那个子分类的冲突，
        不能再把别的子分类（甚至别的分类）的问题推到用户面前。

        `winner` 的取舍与 `_settle_conflicts` 完全一致（名称排序第一个），
        这样弹窗里说「将启用 X」和真正执行后的结果不可能对不上。
        """
        wanted = None
        if only is not None:
            if isinstance(only, tuple):
                wanted = {only}
            else:
                wanted = set(tuple(k) for k in only if k)
        groups = {}
        for rec in list(self.store.mods().values()):
            if not rec.get("enabled"):
                continue
            key = conflict_key(rec)
            if key is None:
                continue
            if wanted is not None and key not in wanted:
                continue
            groups.setdefault(key, []).append(rec)

        out = []
        for key in sorted(groups):
            members = groups[key]
            if len(members) < 2:
                continue
            ordered = sorted(members, key=mod_name_sort_key)
            winner = ordered[0]

            def _brief(r):
                return {"file": r["file"],
                        "title": mod_display_name(r),
                        "enabled": bool(r.get("enabled"))}

            out.append({
                "category": key[0],
                "item": key[1],
                "winner": _brief(winner),
                "members": [_brief(r) for r in ordered],
            })
        return out
