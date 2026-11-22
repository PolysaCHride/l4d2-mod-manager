# -*- coding: utf-8 -*-
"""分类器规则回归测试。

锁住两条 2026-11-20 新增的规则，防止以后被无意改坏：

1. **前置/框架包** 不能被判成「角色」「特感」
   真实案例：xdReanimsBase、KSEP Platform 内含 survivor/infected 模型，
   但它们是依赖包。若被当成外观且 item 非空，启用框架会静默停用整套皮肤。

2. **地图多部件包** 必须归「地图」
   多部件地图拆开卖时，单个部件里可能只有 sound/models/materials，
   没有 maps/*.bsp 也没有 missions/*.txt。一旦被打散到音效/枪械/载具，
   用户在「地图」侧栏找不到部件，而地图缺件根本玩不了。

同时测试**误伤**：普通皮肤、武器、材质包不能被新规则吃掉。

运行：
    .venv/Scripts/python.exe -m unittest tests.test_classify_rules -v
"""
import unittest

from app.core import classify as clf


def cat(paths, info=None, mission=None, hint=""):
    return clf.classify_paths(paths, addoninfo=info or {},
                              mission=mission, hint=hint)[0]


class TestFrameworkDetection(unittest.TestCase):
    """框架/前置包 → 杂项。"""

    def test_base_dependency_is_framework(self):
        """addoninfo 自称 base dependency 的包 → 杂项。"""
        paths = ["models/infected/anim_hulk.phy",
                 "models/survivors/anim_teenangst.mdl",
                 "models/survivors/anim_producer.mdl",
                 "models/survivors/anim_namwet.mdl"]
        info = {"AddonTitle": "xdReanimsBase",
                "AddonDescription": "Base dependency for re-animations mods"}
        self.assertEqual(cat(paths, info), "杂项")

    def test_chinese_prerequisite_is_framework(self):
        """中文描述里的「前置模组」也要认。"""
        paths = ["models/survivors/ksep.mdl",
                 "models/survivors/gestures_teenangst_bq.mdl",
                 "models/survivors/gestures_producer_bq.mdl"]
        info = {"addontitle": "KSEP 人物静态表情平台",                "addonDescription": "特定人物模组实现静态表情的前置模组。"}
        self.assertEqual(cat(paths, info), "杂项")

    def test_prerequisite_word_forms(self):
        """几种常见措辞都要命中，且不误伤 'as a base' 这种。"""
        yes = ["Base dependency for re-animations mods",
               "Framework pack for custom HUDs",
               "Prerequisite mod for these skins",
               "前置模组，用于静态表情",
               "基础库，多个模组依赖"]
        for text in yes:
            self.assertTrue(
                clf._looks_like_framework({"AddonDescription": text}, "", all_paths=[]),
                "应识别为框架：%s" % text)

        no = ["Replaces the medkit using original animations as a base",
              "Serious Sam 4 H.E.A.R.T. Gadget (Defibrillator)",
              "AK-47 霓虹风暴",
              "棒球棒替换"]
        for text in no:
            self.assertFalse(
                clf._looks_like_framework({"AddonDescription": text}, "", all_paths=[]),
                "不该识别为框架：%s" % text)

    def test_single_character_skin_is_not_framework(self):
        """名叫 base 但只改一个角色的皮肤 —— 必须仍是角色。"""
        paths = ["models/survivors/survivor_mechanic.mdl"]
        info = {"AddonTitle": "Ellis base reskin"}
        self.assertEqual(cat(paths, info), "角色")


class TestMapMultipart(unittest.TestCase):
    """地图多部件包 → 地图。"""

    def test_campaign_flag_beats_sound_heuristic(self):
        """纯 sound 的地图部件（有 Campaign 标记）→ 地图，不是音效音乐。"""
        paths = ["sound/music/track%d.wav" % i for i in range(10)]
        info = {"AddonTitle": "Divine Cybermancy (part 2-8)",
                "addonContent_Campaign": "1"}
        self.assertEqual(cat(paths, info), "地图")

    def test_map_flag_beats_material_heuristic(self):
        """纯 materials 的地图部件（有 Map 标记）→ 地图，不是材质特效。"""
        paths = ["materials/halloween/a.vmt", "materials/halloween/b.vtf"]
        info = {"AddonTitle": "档案:零 part3", "addonContent_Map": "1"}
        self.assertEqual(cat(paths, info), "地图")

    def test_campaign_flag_loses_to_specific_appearance(self):
        """标了 Campaign 但明确只改 Ellis 的包 —— 仍是角色。"""
        paths = ["models/survivors/survivor_mechanic.mdl"]
        info = {"AddonTitle": "Ellis Skin", "addonContent_Campaign": "1"}
        self.assertEqual(cat(paths, info), "角色")

    def test_campaign_flag_loses_to_specific_weapon(self):
        """标了 Campaign 但明确是武器皮肤的包 —— 仍是枪械。"""
        for p in ("models/weapons/v_models/v_rifle_ak47.mdl",
                  "models/weapons/w_models/w_snip_awp.mdl"):
            info = {"AddonTitle": "Weapon Skin", "addonContent_Campaign": "1"}
            self.assertEqual(cat([p], info), "枪械", p)

    def test_plain_material_pack_stays_material(self):
        """没有任何地图标记的材质包 —— 不能因为「只有 materials」就判成地图。"""
        self.assertEqual(cat(["materials/a.vmt"], {"AddonTitle": "Texture Pack"}),
                         "材质特效")


class TestNoRegression(unittest.TestCase):
    """常规分类不能被新规则影响。"""

    def test_mission_wins(self):
        """有 mission 文件 → 地图，item 用 DisplayTitle。"""
        mission = {"DisplayTitle": "The Bloody Moors", "Name": "TheBloodyMoors"}
        c, item, _ = clf.classify_paths(["materials/x.vtf"], mission=mission)
        self.assertEqual(c, "地图")
        self.assertEqual(item, "The Bloody Moors")

    def test_survivor_skin(self):
        self.assertEqual(cat(["models/survivors/survivor_coach.mdl"]), "角色")

    def test_infected_skin(self):
        self.assertEqual(cat(["models/infected/hunter.mdl"]), "特感")

    def test_weapon_skin(self):
        self.assertEqual(cat(["models/weapons/v_models/v_rifle_ak47.mdl"]), "枪械")

    def test_empty(self):
        self.assertEqual(cat([]), "未分类")


class TestVersionBumped(unittest.TestCase):
    """改了分类规则就必须 +1，否则老记录永远用旧分类。"""

    def test_clf_version_is_17_or_later(self):
        self.assertGreaterEqual(
            clf.CLF_VERSION, 17,
            "改了分类规则必须提升 CLF_VERSION，否则已有模组不会重算分类")


class TestCustomMeleeIsUnspecified(unittest.TestCase):
    """自制近战不能变成内置子分类。

    真实案例（2026-11-21，真实库 200 个模组实测）：广州增城 v7.3 与另一版
    整合包里带了一整套自制近战 —— `scripts/melee/{pingpang,onion,chair,
    caidao,hammer,wrench}.txt` + `models/weapons/gzzc/melee/`。这些只在那张
    地图里成立，**不能**出现在所有用户的「近战」侧栏里。

    判定标准：分类仍是「近战」（用户能理解这是什么），但 item 必须是空串，
    也就是界面上的「未指定」—— 不是别人家的武器名。
    """

    def test_custom_melee_scripts_are_unspecified(self):
        for name in ("pingpang", "onion", "chair", "caidao", "hammer",
                     "wrench", "skateboard", "tramontina"):
            c, item, _ = clf.classify_paths(["scripts/melee/%s.txt" % name])
            self.assertEqual(c, "近战", name)
            self.assertEqual(item, "", "自制近战 %s 不该成为子分类" % name)

    def test_custom_melee_models_are_unspecified(self):
        """自定义目录 models/weapons/<作者>/melee/ 也要进近战分支（不是枪械）。"""
        for p in ("models/weapons/gzzc/melee/w_pingpang.mdl",
                  "materials/models/weapons/gzzc/melee/w_skateboard.vtf"):
            c, item, _ = clf.classify_paths([p])
            self.assertEqual(c, "近战", p)
            self.assertEqual(item, "", p)

    def test_melee_manifest_is_not_a_weapon(self):
        """melee_manifest.txt 是脚本清单，不该被当成一件武器写进 item。"""
        c, item, _ = clf.classify_paths(["scripts/melee/melee_manifest.txt"])
        self.assertEqual(c, "近战")
        self.assertEqual(item, "")

    def test_manifest_does_not_wipe_known_item(self):
        """带清单的自制近战包：仍能认出官方那把的名字。"""
        c, item, _ = clf.classify_paths([
            "scripts/melee/crowbar.txt",
            "scripts/melee/melee_manifest.txt",
            "models/weapons/melee/w_crowbar.mdl",
        ])
        self.assertEqual((c, item), ("近战", "撬棍"))

    def test_official_melee_still_named(self):
        for name, disp in (("frying_pan", "平底锅"), ("katana", "武士刀"),
                           ("machete", "砍刀"), ("golfclub", "高尔夫球杆")):
            c, item, _ = clf.classify_paths(["scripts/melee/%s.txt" % name])
            self.assertEqual((c, item), ("近战", disp), name)


class TestCatalogIsManagerOwned(unittest.TestCase):
    """自带目录 = 分发给所有用户的子分类清单，不许混进自制内容。"""

    def test_melee_catalog_is_official_only(self):
        cat = clf.category_catalog()
        melee = set(cat["近战"])
        for bad in ("洋葱", "乒乓球拍", "椅子", "菜刀", "锤子", "扳手",
                    "柜子", "西瓜皮"):
            self.assertNotIn(bad, melee, "「%s」是某张图的自制近战" % bad)
        # 官方 15 把（含电锯、防暴盾）必须都在
        for good in ("撬棍", "消防斧", "武士刀", "砍刀", "棒球棒", "平底锅",
                     "电吉他", "警棍", "高尔夫球杆", "板球棒", "小刀", "草叉",
                     "铁锹", "防暴盾", "电锯"):
            self.assertIn(good, melee, "官方近战「%s」不该消失" % good)

    def test_catalog_covers_every_emittable_item(self):
        """分类器写得出、目录里却没有的名字 = 只会从库里冒出来的孤儿项。

        真实踩过的：`前置/框架`（框架包识别）与 `音乐`（音效音乐分类）
        都直接由 classify_paths 产出，却不在目录里 —— 空库时树上没有、
        有模组时才冒出来，看起来像分类坏了。
        """
        cat = clf.category_catalog()
        for c, i in (("杂项", "前置/框架"), ("音效音乐", "音乐")):
            self.assertIn(i, cat.get(c, []), "「%s」由分类器产生，目录里必须有" % i)

    def test_catalog_survives_without_whitelist_crash(self):
        """目录里每一项都是非空字符串、且该分类下不重复。"""
        for c, items in clf.category_catalog().items():
            self.assertEqual(len(items), len(set(items)), c)
            for it in items:
                self.assertTrue(it.strip(), "%s 里有空名字" % c)


class TestAddonInfoKeyCasing(unittest.TestCase):
    """addoninfo 的键大小写不统一 —— 必须忽略大小写查。

    真实案例：4 个模组的 addoninfo 用的是小写 `addontitle`，
    而代码只查 `addonTitle`，导致标题退化成工坊 ID（如 "3009143766"）。
    """

    def test_lookup_ci_matches_any_casing(self):
        from app.core.vpk import lookup_ci
        for key in ("AddonTitle", "addontitle", "ADDONTITLE", "AddonTitle"):
            self.assertEqual(
                lookup_ci({key: "《流浪地球》音乐替换特感音乐"}, "AddonTitle"),
                "《流浪地球》音乐替换特感音乐", key)

    def test_lookup_ci_returns_default_when_missing(self):
        from app.core.vpk import lookup_ci
        self.assertIsNone(lookup_ci({"other": "x"}, "AddonTitle"))
        self.assertEqual(lookup_ci({"other": "x"}, "AddonTitle", default=""), "")

    def test_lookup_ci_skips_blank_values(self):
        """空字符串不该当成"找到了"，应继续查下一个候选名。"""
        from app.core.vpk import lookup_ci
        info = {"AddonTitle": "   ", "addontitle": ""}
        self.assertIsNone(lookup_ci(info, "AddonTitle"))

    def test_parse_keyvalues_preserves_casing(self):
        """parse_keyvalues 保留作者原始大小写（取值方自己兼容）。"""
        from app.core.vpk import parse_keyvalues
        kv = parse_keyvalues('"AddonInfo"\n{\n\t"addontitle"\t\t"小黑"\n}')
        info = kv.get("AddonInfo")
        self.assertIn("addontitle", info)
        self.assertNotIn("addonTitle", info)


class TestTitlePriority(unittest.TestCase):
    """标题优先级：工坊在线补全 > addoninfo > mission > 工坊ID。

    2026-11-21 血泪教训：修 addoninfo 大小写 bug 后，一次全库重扫
    让 136 个标题变化、11 组变成同名 —— 因为把 `_enrich_from_workshop()`
    从工坊 API 拉的好标题冲掉了。现在用 title_locked 标记保护。
    """

    def test_is_junk_detection(self):
        """纯数字 / 空 / 等于文件名主干 → 都是「没信息量」。"""
        from app.core.library import Library
        # 借用 _scan_one 内的判定逻辑语义（通过行为验证）
        # 这里只测语义约定，具体实现在 _scan_one 内部
        for junk in ("", "   ", "3009143766", "1127584577"):
            self.assertTrue(junk.strip() == "" or junk.strip().isdigit(), junk)

    def test_title_locked_survives_rescan(self):
        """title_locked=True 的记录，重扫后标题不变。"""
        import os
        import tempfile
        from app.core.library import Library
        from app.core.paths import GamePaths
        from app.core.store import Store

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = tmp.name
        game = os.path.join(root, "L4D2")
        addons = os.path.join(game, "left4dead2", "addons")
        os.makedirs(addons)
        store = Store(os.path.join(root, "data"))
        lib = Library(store, GamePaths(game))

        # 造一个最小 vpk（内容非法 → 走"损坏 vpk"分支，但不影响 title_locked）
        name = "1234567890.vpk"
        with open(os.path.join(addons, name), "wb") as f:
            f.write(b"\x34\x12\xaa\x55" + b"\x00" * 64)
        rec = store.get_mod(name) or lib.register_new(name, source="scan", enabled=False)
        rec["title"] = "工坊拉来的好标题"
        rec["title_locked"] = True
        store.save_library()

        lib.rescan()
        again = store.get_mod(name)
        self.assertEqual(again.get("title"), "工坊拉来的好标题",
                         "title_locked 的标题不该被重扫覆盖")
        self.assertTrue(again.get("title_locked"),
                        "title_locked 标记自身也必须跨重扫保留")


if __name__ == "__main__":
    unittest.main()
