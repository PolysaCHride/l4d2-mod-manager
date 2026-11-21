# -*- coding: utf-8 -*-
"""前后端契约测试。

为什么需要这个：
`api._to_mod()` 与 `app.js` 的 `adapt()` 是一对。改一边忘另一边，
前端会拿到 undefined，然后被 `|| ''` / `|| 0` 兜底 ——
**界面照常渲染，只是数据错了**，不会有任何报错。

这里锁死三件事：
1. `_to_mod` 的字段集合（加字段必须显式改这里）
2. core 里被丢弃的字段必须列在 DROPPED 里（显式声明）
3. 体积文本的格式（前端直接显示，两处实现必须同一份）

运行：
    .venv/Scripts/python.exe -m unittest tests.test_webui_contract -v
"""
import os
import re
import unittest
from pathlib import Path
from unittest import mock

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
            "added", "addedText", "pinned",
            # 2026-11-20 新增：
            # autoCategory/autoItem —— 用户改过分类后，保留分类器原本的结果
            # （前端把识别结果置灰展示，见 ALIGNMENT_AUDIT C）
            "autoCategory", "autoItem",
            # collection —— 所属合集 ID，之前被丢弃导致合集在新 UI 完全隐形
            # （见 ALIGNMENT_AUDIT A-1）
            "collection",
            # 注：2026-11-20 起 interop 已**没有** mutex / mutexApplicable /
            # groupMutex —— 互斥机制整体拆除（见 docs/PLAN_REMOVE_MUTEX.md）。
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

    def test_collection_derived_from_store_not_record(self):
        """归属以 collections 表为准，不信记录上的 collection 字段。

        真实库 200 条记录的 collection **全是空串**（重扫会把它抹掉），
        而 collections 表里 6 条归属是完好的。只信记录字段的话，
        合集在界面上永远不会出现 —— 这是 A-1 一直「看不见」的真正原因。
        """
        idx = {"a.vpk": "ws_1"}
        rec = self._rec(file="a.vpk", collection="")
        self.assertEqual(self.api._to_mod(rec, idx)["collection"], "ws_1")

    def test_record_collection_still_works_without_index(self):
        """索引里没有时退回记录值（刚下载、还没重扫的窗口期）。"""
        rec = self._rec(file="b.vpk", collection="ws_2")
        self.assertEqual(self.api._to_mod(rec, {})["collection"], "ws_2")
        self.assertEqual(self.api._to_mod(rec)["collection"], "ws_2")



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


    def test_title_falls_back_to_full_file_name(self):
        """标题最后一层兜底是**完整 vpk 文件名**（含扩展名）。

        前端 displayTitle 的第三层拿到的就是这个值；给成去掉扩展名的
        stem 会让用户没法拿它去 addons 目录里对文件。
        """
        rec = self._rec(file="189941645.vpk")
        rec["title"] = ""
        out = self.api._to_mod(rec)
        self.assertEqual(out["title"], "189941645.vpk")
        self.assertTrue(out["title"].endswith(".vpk"))

    def test_title_chain_matches_core_display_name(self):
        """三层兜底必须与 core 的 mod_display_name 一致。

        core 早在 `store.mod_display_name()` 里定了这条规则
        （alias > title > file）。新前端 displayTitle 是它的镜像 ——
        两边一旦不一致，同一个模组在两个界面/搜索结果里会叫两个名字。
        """
        from app.core.store import mod_display_name
        cases = [
            {"file": "a.vpk", "title": "The Bloody Moors", "alias": "沼泽地图"},
            {"file": "a.vpk", "title": "The Bloody Moors", "alias": ""},
            {"file": "189941645.vpk", "title": "", "alias": ""},
        ]
        for case in cases:
            rec = self._rec(**case)
            out = self.api._to_mod(rec)
            # 前端拿到 alias + title 后自己拼：alias || title
            frontend = (out["alias"] or "").strip() or out["title"]
            self.assertEqual(frontend, mod_display_name(rec), case)


    def test_item_is_never_filled_from_collection(self):
        """`item` 不许由 `collection` 兜底 —— 兜底只发生在前端显示层。

        §5 的概念统一是「子分类显示时回落到合集名」。如果这里（API 层）
        就把 item 填成合集名，等于让 collections 覆盖 item，会和
        auto_item / pinned 打架，而且重扫会把这个假 item 当用户值固化下来。
        """
        rec = self._rec(file="a.vpk", collection="ws_189971863")
        out = self.api._to_mod(rec)
        self.assertEqual(out["item"], "", "API 层不能拿合集名填 item")
        self.assertEqual(out["collection"], "ws_189971863", "归属仍要透出")

    def test_item_kept_when_present(self):
        """有 item 时原样透出，不受所属合集影响。"""
        rec = self._rec(file="a.vpk", item="Ellis", collection="ws_1")
        self.assertEqual(self.api._to_mod(rec)["item"], "Ellis")


class TestBootstrapShape(unittest.TestCase):
    """bootstrap 的顶层结构是前端启动的契约。"""

    def test_bootstrap_keys(self):
        r = Api().bootstrap()
        self.assertTrue(r.get("ok"))
        for k in ("mods", "settings", "stats", "game", "paths", "version", "collections"):
            self.assertIn(k, r, "bootstrap 缺字段：%s" % k)

    def test_bootstrap_collections_shape(self):
        """合集表是 {cid: {name, workshop_id, files}}，前端按 cid 直接用。"""
        r = Api().bootstrap()
        cols = r["collections"]
        self.assertIsInstance(cols, dict)
        for cid, info in cols.items():
            self.assertTrue(cid.startswith("ws_"), "合集 ID 形如 ws_<数字>：%r" % cid)
            for k in ("name", "workshop_id", "files"):
                self.assertIn(k, info, "合集 %s 缺字段 %s" % (cid, k))
            self.assertIsInstance(info["files"], list)
            self.assertIsInstance(info["workshop_id"], str)

    def test_collection_members_resolve_into_mods(self):
        """合集里的文件必须能在 mods 里找到归属（两条数据源对得上）。"""
        r = Api().bootstrap()
        by_file = {m["file"]: m for m in r["mods"]}
        for cid, info in r["collections"].items():
            for f in info["files"]:
                m = by_file.get(f)
                if m is None:
                    continue      # 合集里有已删除的部件是正常的
                self.assertEqual(m["collection"], cid,
                                 "%s 属于 %s，但前端拿到的归属是 %r"
                                 % (f, cid, m["collection"]))

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


class TestSizeFormat(unittest.TestCase):
    """体积文本是用户直接看到的东西，锁死输出。

    这条测试存在的意义不只是「测一个格式化函数」，而是钉住
    `api.py` 与 `tasks.py` 共用同一份实现这件事：模组列表里的
    "1.5 MB" 和下载进度里的 "1.5 MB" 必须由同一个函数产生。
    """

    def test_units(self):
        from app.shell.fmt import fmt_size
        self.assertEqual(fmt_size(0), "0 B")
        self.assertEqual(fmt_size(512), "512 B")
        self.assertEqual(fmt_size(1536), "1.5 KB")
        self.assertEqual(fmt_size(1024 * 1024), "1.0 MB")
        self.assertEqual(fmt_size(int(1.5 * 1024 ** 3)), "1.5 GB")

    def test_bad_input_is_zero_not_question_mark(self):
        """缺失/脏数据一律 0 B；不能用 "?" 冒充「加载失败」。"""
        from app.shell.fmt import fmt_size
        for bad in (None, "", "abc", -1, {}):
            self.assertEqual(fmt_size(bad), "0 B", "输入 %r" % (bad,))

    def test_both_modules_share_one_implementation(self):
        """api 与 tasks 引用的必须是 fmt 里那一个，不能再各留一份拷贝。"""
        from app.shell import api, fmt, tasks
        self.assertIs(api.fmt_size, fmt.fmt_size)
        self.assertIs(tasks.fmt_size, fmt.fmt_size)
        self.assertFalse(hasattr(api, "_fmt_size"),
                         "api 里不该再有私有的 _fmt_size 拷贝")
        self.assertFalse(hasattr(tasks, "_fmt_size"),
                         "tasks 里不该再有私有的 _fmt_size 拷贝")


class TestCleanCachePreviews(unittest.TestCase):
    """`clean_cache` 要清掉 `data/previews/` 里没人引用的图。

    背景：工坊缩略图下载到 previews/，记录里的 `preview` 存绝对路径。
    删模组/重导入之后这些图就成孤儿 —— 实测 41 个文件 / 38MB、0 条引用，
    而它既不在 tmp/ 也不在 thumb-cache/，原来的 clean_cache 从来没碰过。
    """

    def setUp(self):
        import tempfile
        from app.core.store import Store

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = Store(self._tmp.name)
        self.previews = self.store.previews_dir

        self.api = Api()
        self.api._store = self.store      # 跳过 _ensure()，不碰真实 data/
        self.api._library = None

        patcher = mock.patch("app.shell.api.app_paths.data_dir",
                             return_value=self._tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _touch(self, name, size=10):
        p = os.path.join(self.previews, name)
        with open(p, "wb") as f:
            f.write(b"x" * size)
        return p

    def test_deletes_only_orphans(self):
        keep = self._touch("keep.jpg", 100)
        orphan = self._touch("orphan.jpg", 50)
        rec = new_mod_record("x.vpk")
        rec["preview"] = keep
        self.store.upsert_mod(rec)

        r = self.api.clean_cache()
        self.assertTrue(r.get("ok"), r)
        self.assertTrue(os.path.isfile(keep), "被引用的预览图一个都不能少")
        self.assertFalse(os.path.exists(orphan), "没人引用的预览图应该被删掉")
        self.assertGreaterEqual(r.get("freed") or 0, 50, "释放字节数要算进去")

    def test_idempotent(self):
        self._touch("orphan.jpg", 30)
        self.assertTrue(self.api.clean_cache().get("ok"))
        r2 = self.api.clean_cache()
        self.assertTrue(r2.get("ok"), r2)
        self.assertEqual(r2.get("freed"), 0, "第二次不该再释放任何字节")

    def test_keeps_directories(self):
        """只删文件：previews 目录本身与子目录都不动。"""
        sub = os.path.join(self.previews, "sub")
        os.makedirs(sub, exist_ok=True)
        inner = os.path.join(sub, "inner.jpg")
        with open(inner, "wb") as f:
            f.write(b"x")

        self.assertTrue(self.api.clean_cache().get("ok"))
        self.assertTrue(os.path.isdir(self.previews), "previews 目录要保留")
        self.assertTrue(os.path.isfile(inner), "子目录不在清理范围内")

    def test_reference_match_is_case_folded(self):
        """Windows 上大小写不敏感：记录里存小写也要认得出同一个文件。"""
        keep = self._touch("Keep.JPG", 20)
        rec = new_mod_record("x.vpk")
        rec["preview"] = keep.lower()
        self.store.upsert_mod(rec)

        self.assertTrue(self.api.clean_cache().get("ok"))
        self.assertTrue(os.path.isfile(keep), "大小写不同也是同一个文件")


if __name__ == "__main__":
    unittest.main()
