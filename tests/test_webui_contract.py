# -*- coding: utf-8 -*-
"""前后端契约测试。

为什么需要这个：
`api._to_mod()` 与 `app.js` 的 `adapt()` 是一对。改一边忘另一边，
前端会拿到 undefined，然后被 `|| ''` / `|| 0` 兜底 ——
**界面照常渲染，只是数据错了**，不会有任何报错。

这里锁死三件事：
1. `_to_mod` 的字段集合（加字段必须显式改这里）
2. core 里被丢弃的字段必须列在 DROPPED 里（显式声明）
3. 互斥类别在所有副本里必须一致

运行：
    .venv/Scripts/python.exe -m unittest tests.test_webui_contract -v
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from app.core.store import new_mod_record  # noqa: E402
from app.shell.api import Api  # noqa: E402


class TestToModContract(unittest.TestCase):
    """_to_mod 是前端数据的唯一来源，字段集必须稳定。"""

    def setUp(self):
        self.api = Api()

    def _rec(self, **kw):
        rec = new_mod_record("test.vpk")
        rec.update(kw)
        return rec

    def test_field_set_is_frozen(self):
        """加字段必须显式改这个断言，避免前端静默拿到 undefined。"""
        out = self.api._to_mod(self._rec())
        self.assertEqual(set(out), {
            "file", "title", "alias", "category", "item",
            "size", "sizeText", "enabled", "workshop_id", "thumb",
            "added", "addedText", "pinned", "mutex",
        })

    def test_dropped_fields_are_explicit(self):
        """core 有但没传给前端的字段，必须在这里声明。

        如果有人给 core 加了新字段却忘了往 _to_mod 传，
        这个测试会失败，提醒他做决定。
        """
        core_fields = set(new_mod_record("test.vpk"))
        out = set(self.api._to_mod(self._rec()))

        # 有意不传给前端的字段
        # clfv 是 library 扫描时才算出来的分类器版本标记，不在 new_mod_record 里
        DROPPED = {"tags", "added_at", "updated_at", "source",
                   "collection", "preview", "mtime"}

        self.assertEqual(core_fields - out, DROPPED,
                         "core 加了新字段，或者改了丢弃清单")

    def test_added_uses_added_at(self):
        """入库时间必须用 added_at，不能用文件 mtime。"""
        rec = self._rec(added_at=1000, mtime=999999)
        self.assertEqual(self.api._to_mod(rec)["added"], 1000)

    def test_added_falls_back_to_mtime(self):
        """added_at 缺失时才退回 mtime（core 重扫会丢 added_at）。"""
        rec = self._rec(added_at=0, mtime=888)
        self.assertEqual(self.api._to_mod(rec)["added"], 888)

    def test_thumb_is_data_uri_or_empty(self):
        """缩略图必须是 data URI 或空串 —— 不能是裸文件路径。

        裸 file:// 路径在页面跨盘符时会被 WebView2 拦截，表现为全部裂图。
        """
        thumb = self.api._to_mod(self._rec(preview=""))["thumb"]
        self.assertEqual(thumb, "")

    def test_enabled_is_bool(self):
        """前端依赖严格的布尔值（用的是 !!x 和 ===）。"""
        self.assertIs(self.api._to_mod(self._rec(enabled=1))["enabled"], True)
        self.assertIs(self.api._to_mod(self._rec(enabled=0))["enabled"], False)

    def test_mutex_matches_core(self):
        """mutex 标记必须与 core 的冲突类别一致。"""
        from app.core.classify import CONFLICT_CATEGORIES
        for cat in ("角色", "枪械", "地图", "杂项"):
            got = self.api._to_mod(self._rec(category=cat))["mutex"]
            self.assertEqual(got, cat in CONFLICT_CATEGORIES, cat)


class TestEnumConsistency(unittest.TestCase):
    """枚举在多处定义，必须保持一致。"""

    def test_mutex_categories_match_core(self):
        from app.core.classify import CONFLICT_CATEGORIES

        # 前端那份
        js = (ROOT / "app" / "webui" / "app.js").read_text(encoding="utf-8")
        m = re.search(r"MUTEX_CATEGORIES\s*=\s*new Set\(\[([^\]]+)\]\)", js)
        self.assertIsNotNone(m, "前端找不到 MUTEX_CATEGORIES")
        js_set = {s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()}

        self.assertEqual(CONFLICT_CATEGORIES, js_set,
                         "前端互斥类别与 core 不一致 —— "
                         "会导致后端静默停用但前端不弹确认")

    def test_frontend_covers_all_core_categories(self):
        """前端 rail 的并集必须覆盖 core 的所有分类，否则模组会「消失」。"""
        from app.core.classify import CATEGORIES

        js = (ROOT / "app" / "webui" / "app.js").read_text(encoding="utf-8")
        # RAIL_DEFS 里所有 cats: [...] 的字面量
        found = set()
        for block in re.findall(r"cats:\s*\[([^\]]*)\]", js):
            for s in block.split(","):
                s = s.strip().strip("'\"")
                if s:
                    found.add(s)

        missing = set(CATEGORIES) - found
        self.assertEqual(missing, set(),
                         "前端缺少这些分类，对应模组在专属分类里看不见：%s" % missing)


class TestBootstrapShape(unittest.TestCase):
    """bootstrap 的顶层结构是前端启动的契约。"""

    def test_bootstrap_keys(self):
        r = Api().bootstrap()
        self.assertTrue(r.get("ok"))
        for k in ("mods", "settings", "stats", "game", "paths", "version"):
            self.assertIn(k, r, "bootstrap 缺字段：%s" % k)

    def test_bootstrap_stats_match_mods(self):
        r = Api().bootstrap()
        mods = r["mods"]
        self.assertEqual(r["stats"]["total"], len(mods))
        self.assertEqual(r["stats"]["enabled"],
                         sum(1 for m in mods if m["enabled"]))


if __name__ == "__main__":
    unittest.main()
