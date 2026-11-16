# -*- coding: utf-8 -*-
import unittest

from app.ui.main_window import mod_count_text, sort_item_entries


class MainWindowHelperTests(unittest.TestCase):
    def test_mod_count_text_counts_enabled_and_disabled(self):
        mods = {
            "1.vpk": {"enabled": True},
            "2.vpk": {"enabled": False},
            "3.vpk": {},
            "4.vpk": {"enabled": True},
        }
        self.assertEqual(mod_count_text(mods),
                         "Mod数 4 · 已启用 2 · 已禁用 2")

    def test_item_entries_sort_by_name_with_fixed_first_two(self):
        entries = [
            ("全部 (9)", "all", None),
            ("Zoey(佐伊) (1)", "item", "Zoey(佐伊)"),
            ("AK-47(AK) (3)", "item", "AK-47(AK)"),
            ("未指定 / 多项 (2)", "item", ""),
            ("📁 The Bloody Moors (2)", "collection", "ws_1"),
            ("AWP(大狙) (1)", "item", "AWP(大狙)"),
        ]
        ordered = sort_item_entries(entries, {"ws_1": "The Bloody Moors"})
        self.assertEqual([entry[2] for entry in ordered],
                         [None, "", "AK-47(AK)", "AWP(大狙)",
                          "ws_1", "Zoey(佐伊)"])


if __name__ == "__main__":
    unittest.main()
