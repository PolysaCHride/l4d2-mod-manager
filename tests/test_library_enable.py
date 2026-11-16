# -*- coding: utf-8 -*-
"""导入 / 下载后默认启用，以及同物品互斥组切换到最新加入的 mod。"""
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

    def test_conflict_group_switches_to_latest_new_mod(self):
        old = self._add_mod("old_ak.vpk", "枪械", "AK-47")
        self.library.enable_new_mods([old["file"]])

        first = self._add_mod("first_ak.vpk", "枪械", "AK-47")
        latest = self._add_mod("latest_ak.vpk", "枪械", "AK-47")
        disabled = self.library.enable_new_mods([first["file"], latest["file"]])

        self.assertFalse(self._enabled(old["file"]))
        self.assertFalse(self._enabled(first["file"]))
        self.assertTrue(self._enabled(latest["file"]))
        self.assertEqual(sorted(disabled), sorted([old["file"], first["file"]]))
        self.assertEqual(self._addon_value(old["file"]), "0")
        self.assertEqual(self._addon_value(first["file"]), "0")
        self.assertEqual(self._addon_value(latest["file"]), "1")

    def test_other_items_and_non_conflict_mods_stay_enabled(self):
        ak = self._add_mod("ak.vpk", "枪械", "AK-47")
        awp = self._add_mod("awp.vpk", "枪械", "AWP(大狙)")
        sound = self._add_mod("sound.vpk", "音效音乐")

        self.library.enable_new_mods([ak["file"], awp["file"], sound["file"]])

        self.assertTrue(self._enabled(ak["file"]))
        self.assertTrue(self._enabled(awp["file"]))
        self.assertTrue(self._enabled(sound["file"]))


if __name__ == "__main__":
    unittest.main()
