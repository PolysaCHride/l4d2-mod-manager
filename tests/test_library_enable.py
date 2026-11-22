# -*- coding: utf-8 -*-
"""导入 / 下载后默认启用。

2026-11-22 起互斥回来了，但**按子分类各开各关**：
`enable_new_mods` 默认遵守每个组自己的开关（新库默认全开）。
所以要测「不互斥」的行为，先把那个组关掉 —— 见 `_off()`。
"""
import os
import tempfile
import unittest

from app.core.addonlist import AddonList
from app.core.library import Library
from app.core.paths import GamePaths
from app.core.store import Store


class EnableNewModsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name
        self.game_dir = os.path.join(root, "Left 4 Dead 2")
        self.addons = os.path.join(self.game_dir, "left4dead2", "addons")
        os.makedirs(self.addons)
        self.store = Store(os.path.join(root, "data"))
        self.library = Library(self.store, GamePaths(self.game_dir))
        self.addCleanup(self._tmp.cleanup)

    def _add_mod(self, name, category, item=""):
        path = os.path.join(self.addons, name)
        with open(path, "wb") as f:
            f.write(b"\x34\x12\xaa\x55" + b"\x00" * 32)
        rec = self.library.register_new(name, source="import", enabled=False)
        rec["category"] = category
        rec["item"] = item
        self.store.save_library()
        return rec

    def _off(self, category, item):
        """关掉某个子分类的互斥（模拟用户在界面上把那个开关拨掉）。"""
        self.library.set_group_mutex(category, item, False)

    def _enabled(self, name):
        return bool(self.store.get_mod(name).get("enabled"))

    def _addon_value(self, name):
        return AddonList.load(self.library.paths.addonlist_file).get(name)

    def test_new_mods_are_enabled_by_default(self):
        map_mod = self._add_mod("map.vpk", "地图")
        skin = self._add_mod("ak.vpk", "枪械", "AK-47")

        self.library.enable_new_mods([map_mod["file"], skin["file"]])

        self.assertTrue(self._enabled(map_mod["file"]))
        self.assertTrue(self._enabled(skin["file"]))
        self.assertEqual(self._addon_value(map_mod["file"]), "1")
        self.assertEqual(self._addon_value(skin["file"]), "1")

    def test_same_group_mods_all_stay_enabled(self):
        """把某个子分类的互斥关掉后，同组的多个模组全部保持启用。

        互斥是按子分类独立的，所以这条既是「关掉就不互斥」的证明，
        也是「关一个不影响别的组」的侧面证明（别的组仍然按各自开关走）。
        """
        self._off("枪械", "AK-47")
        old = self._add_mod("old_ak.vpk", "枪械", "AK-47")
        self.library.enable_new_mods([old["file"]])

        first = self._add_mod("first_ak.vpk", "枪械", "AK-47")
        latest = self._add_mod("latest_ak.vpk", "枪械", "AK-47")
        disabled = self.library.enable_new_mods([first["file"], latest["file"]])

        # 三个同组模组全部启用
        self.assertTrue(self._enabled(old["file"]))
        self.assertTrue(self._enabled(first["file"]))
        self.assertTrue(self._enabled(latest["file"]))
        self.assertEqual(self._addon_value(old["file"]), "1")
        self.assertEqual(self._addon_value(first["file"]), "1")
        self.assertEqual(self._addon_value(latest["file"]), "1")
        # 不再返回任何被自动停用的文件
        self.assertEqual(disabled, [])

    def test_other_items_and_non_conflict_mods_stay_enabled(self):
        ak = self._add_mod("ak.vpk", "枪械", "AK-47")
        awp = self._add_mod("awp.vpk", "枪械", "AWP(大狙)")
        sound = self._add_mod("sound.vpk", "音效音乐")

        self.library.enable_new_mods([ak["file"], awp["file"], sound["file"]])

        self.assertTrue(self._enabled(ak["file"]))
        self.assertTrue(self._enabled(awp["file"]))
        self.assertTrue(self._enabled(sound["file"]))

    def test_toggle_does_not_disable_siblings(self):
        """该组互斥关着时，启用一个不动同组其它模组。"""
        self._off("枪械", "AK-47")
        a = self._add_mod("a_ak.vpk", "枪械", "AK-47")
        b = self._add_mod("b_ak.vpk", "枪械", "AK-47")

        self.library.enable_new_mods([a["file"], b["file"]])
        self.assertTrue(self._enabled(a["file"]))
        self.assertTrue(self._enabled(b["file"]))

        disabled = self.library.set_enabled(b["file"], True)
        self.assertEqual(disabled, [])
        self.assertTrue(self._enabled(a["file"]), "启用 b 不该关掉 a")


if __name__ == "__main__":
    unittest.main()

