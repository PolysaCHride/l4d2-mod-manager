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
            # 2026-11-20 新增：
            # autoCategory/autoItem —— 用户改过分类后，保留分类器原本的结果
            # （前端把识别结果置灰展示，见 ALIGNMENT_AUDIT C）
            "autoCategory", "autoItem",
            # collection —— 所属合集 ID，之前被丢弃导致合集在新 UI 完全隐形
            # （见 ALIGNMENT_AUDIT A-1）
            "collection",
            # 组级互斥开关（2026-11-20）：
            #   mutexApplicable = 这类模组参与互斥（互斥类别 + item 非空）
            #   groupMutex      = 它所在的那个「分类+物品」组当前是否真的在互斥
            "mutexApplicable", "groupMutex",
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
        # auto_category / auto_item 是 set_category 时才写入的，同样不在 new_mod_record 里
        # （它们走 autoCategory / autoItem 传给前端，不在此列）
        # collection 已于 2026-11-20 改为传给前端（A-1），从丢弃清单移出
        DROPPED = {"tags", "added_at", "updated_at", "source",
                   "preview", "mtime"}

        self.assertEqual(core_fields - out, DROPPED,
                         "core 加了新字段，或者改了丢弃清单")

    def test_auto_fields_absent_when_never_overridden(self):
        """没用过用户分类时，autoCategory/autoItem 必须是 None。

        前端靠 None 判断「要不要置灰展示识别结果」。
        如果这里变成空串，前端会把空分类也画出来。
        """
        out = self.api._to_mod(self._rec())
        self.assertIsNone(out["autoCategory"])
        self.assertIsNone(out["autoItem"])

    def test_auto_fields_present_after_manual_override(self):
        """用户改过分类后，auto_* 要原样透出，且与当前分类不同。"""
        rec = self._rec(category="杂项", auto_category="角色", auto_item="Ellis")
        out = self.api._to_mod(rec)
        self.assertEqual(out["category"], "杂项")
        self.assertEqual(out["autoCategory"], "角色")
        self.assertEqual(out["autoItem"], "Ellis")

    def test_collection_is_passed_through(self):
        """合集归属必须透出，否则新 UI 完全看不见合集（A-1 的根因）。"""
        rec = self._rec(collection="ws_189971863")
        self.assertEqual(self.api._to_mod(rec)["collection"], "ws_189971863")
        # 没有归属时是空串，不是 None —— 前端用 === '' 判断
        self.assertEqual(self.api._to_mod(self._rec())["collection"], "")



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

        注意（2026-11-20 起）：没有 mod 自带预览图时，会退回 assets/wiki 的
        物品图/分类图（旧 UI 的四级兜底搬到新栈）。所以「无 preview」不等于
        「thumb 为空」—— 只有 wiki 里也没有对应图时才是空串。
        """
        # 一个既无 preview、物品名和分类在 wiki 里都不存在的记录 → 空串
        rec = self._rec(preview="", category="绝对不存在的分类",
                        item="绝对不存在的物品")
        thumb = self.api._to_mod(rec)["thumb"]
        self.assertEqual(thumb, "")

    def test_thumb_falls_back_to_wiki_asset(self):
        """mod 无预览图时，应该退到 assets/wiki 的占位图（data URI）。"""
        rec = self._rec(preview="", category="角色", item="Ellis")
        thumb = self.api._to_mod(rec)["thumb"]
        self.assertTrue(
            thumb.startswith("data:image/png;base64,"),
            "应退回 wiki 物品图，实际是 %r" % (thumb[:60] or thumb))

    def test_thumb_is_never_a_bare_path(self):
        """任何情况下都不能把裸文件路径当 thumb 传给前端。"""
        for preview in ("", "E:\\nonexistent\\x.jpg", "/not/exist.png"):
            thumb = self.api._to_mod(
                self._rec(preview=preview, category="角色", item="Ellis"))["thumb"]
            self.assertFalse(
                thumb.startswith(("E:", "C:", "/", "file:")),
                "thumb 不能是裸路径：%r" % thumb[:60])

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


class TestAutoCategoryRoundTrip(unittest.TestCase):
    """auto_category 的完整生命周期：捕获 → 透出 → 恢复。

    这是 C 功能的核心契约。用户改错分类后必须能退回自动判定，
    否则「允许用户改分类」就变成了单向不可逆操作。
    """

    def setUp(self):
        import tempfile
        from app.core.store import Store
        from app.core.library import Library

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = Store(self._tmp.name)
        rec = new_mod_record("x.vpk")
        rec.update({"category": "角色", "item": "Ellis"})
        self.store.upsert_mod(rec)
        self.store.save_library()

        # 只借用 set_category / restore_auto_category，不需要真实游戏目录
        self.lib = Library.__new__(Library)
        self.lib.store = self.store
        self.lib.paths = None

    def test_override_captures_auto_once(self):
        """首次改分类捕获原值；再次修改不覆盖。"""
        self.lib.set_category("x.vpk", "杂项", "")
        rec = self.store.get_mod("x.vpk")
        self.assertEqual(rec["auto_category"], "角色")
        self.assertEqual(rec["auto_item"], "Ellis")

        self.lib.set_category("x.vpk", "音效音乐", "")
        rec = self.store.get_mod("x.vpk")
        self.assertEqual(rec["auto_category"], "角色",
                         "第二次改分类不应把 auto_* 变成上一次的用户值")

    def test_restore_brings_back_auto(self):
        """恢复后：category 回到识别值，auto_* 与 pinned 都清掉。"""
        self.lib.set_category("x.vpk", "杂项", "")
        self.lib.restore_auto_category("x.vpk")
        rec = self.store.get_mod("x.vpk")
        self.assertEqual(rec["category"], "角色")
        self.assertEqual(rec["item"], "Ellis")
        self.assertNotIn("auto_category", rec)
        self.assertNotIn("pinned", rec,
                         "恢复后必须清掉 pinned，否则重扫仍不会接管")

    def test_restore_refuses_when_never_overridden(self):
        """没改过分类的模组调用恢复应报错，而不是悄悄做点什么。"""
        from app.core.library import LibraryError
        with self.assertRaises(LibraryError):
            self.lib.restore_auto_category("x.vpk")


if __name__ == "__main__":
    unittest.main()
