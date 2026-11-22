# -*- coding: utf-8 -*-
"""互斥开关（v1.3 新增）的行为契约。

用户 2026-11-22 裁定的边界：
  1. 开关打开（默认）：同一 (分类, 物品) 只允许一个启用项。
  2. 手动切换：开一个就关同组其它，被关的名单要回传给界面。
  3. 导入/下载：同组已有启用 → 新模组只入库不启用；
               同组全空 → 自动启用；同批多个同组 → 按名称取第一个。
  4. 整理：也遵守互斥，冲突时保留「管理器原本记着启用的那个」。
  5. 「未指定」（item 为空）和地图/音效/UI 等叠加型内容不参与互斥。
  6. 开关关闭：以上全部不生效，谁都不动。
"""
import os
import tempfile
import unittest

from app.core.addonlist import AddonList
from app.core.library import Library, conflict_key
from app.core.paths import GamePaths
from app.core.store import Store


class MutexBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name
        self.game_dir = os.path.join(root, "Left 4 Dead 2")
        self.addons = os.path.join(self.game_dir, "left4dead2", "addons")
        os.makedirs(self.addons)
        self.store = Store(os.path.join(root, "data"))
        self.library = Library(self.store, GamePaths(self.game_dir))
        self.addCleanup(self._tmp.cleanup)

    def _add(self, name, category, item="", enabled=False, title=None):
        with open(os.path.join(self.addons, name), "wb") as f:
            f.write(b"\x34\x12\xaa\x55" + b"\x00" * 32)
        rec = self.library.register_new(name, source="import", enabled=enabled)
        rec["category"] = category
        rec["item"] = item
        if title is not None:
            rec["title"] = title
        self.store.save_library()
        return rec

    def _enabled(self, name):
        return bool(self.store.get_mod(name).get("enabled"))

    def _addon(self, name):
        return AddonList.load(self.library.paths.addonlist_file).get(name)


class ConflictKeyTests(unittest.TestCase):
    """哪些模组参与互斥 —— 这是全功能的入口判定。"""

    def test_appearance_categories_with_item_participate(self):
        for cat in ("角色", "特感", "枪械", "近战", "医疗品", "投掷"):
            self.assertEqual(conflict_key({"category": cat, "item": "X"}), (cat, "X"))

    def test_unset_item_never_participates(self):
        # 「未指定」是垃圾桶：里面可能是完全不同类型的东西
        self.assertIsNone(conflict_key({"category": "枪械", "item": ""}))
        self.assertIsNone(conflict_key({"category": "角色", "item": None}))

    def test_overlay_categories_never_participate(self):
        """地图与「其他」下的所有分类都不参与互斥。

        2026-11-22 用户特别强调：**地图绝对不要加互斥** ——
        同一张图的多个部件（`xxx_dir.vpk` + `xxx_001.vpk`）本来就该共存，
        被互斥掉的话地图会「缺块」。
        """
        for cat in ("地图", "音效音乐", "UI", "弹药", "材质特效",
                    "载具", "动作", "杂项", "其他", "未分类"):
            self.assertIsNone(conflict_key({"category": cat, "item": "X"}), cat)

    def test_map_with_item_never_joins_a_group(self):
        """地图即使有 item（战役名）也不能互斥。"""
        a = {"category": "地图", "item": "The Bloody Moors", "file": "a.vpk"}
        b = {"category": "地图", "item": "The Bloody Moors", "file": "b.vpk"}
        self.assertIsNone(conflict_key(a))
        self.assertIsNone(conflict_key(b))


class ManualToggleTests(MutexBase):
    def test_enabling_one_disables_siblings(self):
        a = self._add("a.vpk", "枪械", "AK-47")
        b = self._add("b.vpk", "枪械", "AK-47")
        self.library.set_enabled(a["file"], True, mutex=True)
        self.assertEqual(self._addon(a["file"]), "1")

        disabled = self.library.set_enabled(b["file"], True, mutex=True)
        self.assertEqual(disabled, [a["file"]], "要回传被停用的兄弟")
        self.assertFalse(self._enabled(a["file"]))
        self.assertEqual(self._addon(a["file"]), "0")
        self.assertTrue(self._enabled(b["file"]))

    def test_other_items_untouched(self):
        ak = self._add("ak.vpk", "枪械", "AK-47")
        awp = self._add("awp.vpk", "枪械", "AWP(大狙)")
        self.library.set_enabled(ak["file"], True, mutex=True)
        disabled = self.library.set_enabled(awp["file"], True, mutex=True)
        self.assertEqual(disabled, [])
        self.assertTrue(self._enabled(ak["file"]))

    def test_unset_group_never_mutexes(self):
        a = self._add("u1.vpk", "枪械", "")
        b = self._add("u2.vpk", "枪械", "")
        self.library.set_enabled(a["file"], True, mutex=True)
        disabled = self.library.set_enabled(b["file"], True, mutex=True)
        self.assertEqual(disabled, [])
        self.assertTrue(self._enabled(a["file"]))

    def test_mutex_off_leaves_everyone_alone(self):
        a = self._add("a.vpk", "枪械", "AK-47")
        b = self._add("b.vpk", "枪械", "AK-47")
        self.library.set_enabled(a["file"], True, mutex=False)
        disabled = self.library.set_enabled(b["file"], True, mutex=False)
        self.assertEqual(disabled, [])
        self.assertTrue(self._enabled(a["file"]))
        self.assertTrue(self._enabled(b["file"]))

    def test_disabling_never_touches_siblings(self):
        a = self._add("a.vpk", "枪械", "AK-47")
        b = self._add("b.vpk", "枪械", "AK-47")
        self.library.set_enabled(a["file"], True, mutex=True)
        self.library.set_enabled(b["file"], True, mutex=True)   # a 被顶掉
        self.library.set_enabled(b["file"], False, mutex=True)
        self.assertFalse(self._enabled(b["file"]))
        self.assertFalse(self._enabled(a["file"]), "停用不该顺手把别人打开")


class EnableNewModsTests(MutexBase):
    """导入 / 下载：组里已有启用项 → 只入库不启用。"""

    def test_existing_enabled_blocks_newcomer(self):
        old = self._add("old.vpk", "角色", "Ellis")
        self.library.set_enabled(old["file"], True, mutex=True)

        new = self._add("new.vpk", "角色", "Ellis")
        disabled = self.library.enable_new_mods([new["file"]], mutex=True)

        self.assertFalse(self._enabled(new["file"]), "同组已有启用，新模组不该抢位")
        self.assertEqual(self._addon(new["file"]), "0")
        self.assertTrue(self._enabled(old["file"]), "旧的不动")
        self.assertEqual(disabled, [])

    def test_empty_group_enables_first_by_name(self):
        """组里一个都没启用 → 自动启用，一组只留名称排序第一个。"""
        b = self._add("b.vpk", "枪械", "AK-47", title="B 皮肤")
        a = self._add("a.vpk", "枪械", "AK-47", title="A 皮肤")

        self.library.enable_new_mods([b["file"], a["file"]], mutex=True)

        self.assertTrue(self._enabled(a["file"]), "名称排序第一个（A 皮肤）要启用")
        self.assertFalse(self._enabled(b["file"]))
        self.assertEqual(self._addon(a["file"]), "1")
        self.assertEqual(self._addon(b["file"]), "0")

    def test_mutex_off_enables_everything(self):
        old = self._add("old_ak.vpk", "枪械", "AK-47", enabled=True)
        first = self._add("first_ak.vpk", "枪械", "AK-47")
        latest = self._add("latest_ak.vpk", "枪械", "AK-47")

        disabled = self.library.enable_new_mods(
            [first["file"], latest["file"]], mutex=False)

        for name in (old["file"], first["file"], latest["file"]):
            self.assertTrue(self._enabled(name), name)
            self.assertEqual(self._addon(name), "1")
        self.assertEqual(disabled, [])

    def test_non_conflict_categories_all_enabled(self):
        m1 = self._add("map1.vpk", "地图", "Yama")
        m2 = self._add("map2.vpk", "地图", "Yama")
        sound = self._add("snd.vpk", "音效音乐", "音乐")
        self.library.enable_new_mods([m1["file"], m2["file"], sound["file"]], mutex=True)
        for name in (m1["file"], m2["file"], sound["file"]):
            self.assertTrue(self._enabled(name), name)


class ConflictGroupTests(MutexBase):
    def test_groups_only_list_real_conflicts(self):
        a = self._add("a.vpk", "枪械", "AK-47", enabled=True, title="A")
        b = self._add("b.vpk", "枪械", "AK-47", enabled=True, title="B")
        c = self._add("c.vpk", "枪械", "AWP(大狙)", enabled=True, title="C")

        groups = self.library.conflict_groups()

        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual((g["category"], g["item"]), ("枪械", "AK-47"))
        self.assertEqual(len(g["members"]), 2)
        self.assertEqual(g["winner"]["file"], a["file"], "名称 A 排第一")
        files = {m["file"] for m in g["members"]}
        self.assertEqual(files, {a["file"], b["file"]})
        self.assertNotIn(c["file"], files)

    def test_settle_keeps_one_and_reports(self):
        a = self._add("a.vpk", "枪械", "AK-47", enabled=True, title="A")
        b = self._add("b.vpk", "枪械", "AK-47", enabled=True, title="B")

        disabled, enabled_extra = self.library._settle_conflicts(
            AddonList.load(self.library.paths.addonlist_file))

        self.assertEqual(disabled, [b["file"]])
        self.assertEqual(enabled_extra, [])
        self.assertTrue(a.get("enabled"))
        self.assertFalse(b.get("enabled"))

    def test_settle_leaves_empty_group_alone(self):
        self._add("a.vpk", "枪械", "AK-47", enabled=False)
        self._add("b.vpk", "枪械", "AK-47", enabled=False)
        disabled, enabled_extra = self.library._settle_conflicts(
            AddonList.load(self.library.paths.addonlist_file))
        self.assertEqual((disabled, enabled_extra), ([], []))


if __name__ == "__main__":
    unittest.main()
