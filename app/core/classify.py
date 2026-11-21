# -*- coding: utf-8 -*-
"""mod 分类引擎：根据 VPK 内容路径判断 (类别, 物品)。

分类优先级：
  missions/*.txt（战役） > maps/*.bsp > 幸存者/特感/近战/医疗品/投掷/武器
  > 弹药/载具/动作/UI/音效音乐 > 材质特效/杂项（addoninfo 标签兜底） > 未分类

L4D2 资源路径特征（经实测库验证）：
  - 武器模型在 models/v_models/（第一人称）与 models/w_models/（世界模型），
    且常带 weapons/ 子目录；材质在 materials/models/v_models|w_models、materials/weapons
  - 文件/目录名含武器关键词：v_rifle_ak47、w_desert_eagle、v_shotgun_spas、w_sniper_military…
  - 人物在 models/survivors/survivor_<内部名>；特感在 models/infected/<内部名>
  - 近战在 models/weapons/melee/ 与 scripts/melee/；自定义近战常在 w_models 下
  - 战役 mission txt 的标题键是 DisplayTitle（不是 DisplayName）
"""

import re

from . import classify_data as _cdata

# 分类引擎版本号：表格/规则变更时 +1，库缓存据此强制重解析
#
# 16 (2026-11-21)：
#   · 标题提取改为忽略大小写查 addoninfo 的键
#     （`AddonTitle` / `addontitle` 两种写法都常见，原来只认后者的大写形式，
#      导致真实库 4 个模组的标题退化成工坊 ID，如 "3009143766"）
# 15 (2026-11-20)：
#   · 新增「前置/框架包」识别（xdReanimsBase、KSEP Platform 这类包，
#     内含 survivor/infected 模型但其实是依赖包，原被误判为角色/特感）
#   · 新增「addoninfo 明示 Campaign/Map → 归地图」前置规则
#     （地图多部件包拆开卖时无 bsp/mission，原被误判为音效/枪械/载具）
#   改版本号会触发全库重解析（200 个 vpk），这是刻意的 —— 上面这些
#   必须回填到已有记录，否则老模组继续显示错分类 / 错标题。
CLF_VERSION = 16

# 会互相冲突的类别（仅分类器内部用于标注「这是外观类」）。
#
# ⚠️ 2026-11-20 起**互斥机制已整体拆除**：用户要求自行管理冲突，
# 启停模组不再自动停用同组其它项（core/shell/前端都不再消费这个集合去互斥）。
# 常量保留是因为分类逻辑仍需要它做「外观类」判定 —— 不是 UI 概念了。
# 详见 docs/PLAN_REMOVE_MUTEX.md。
CONFLICT_CATEGORIES = {"角色", "特感", "枪械", "近战", "医疗品", "投掷"}

# 类别顺序即 UI 图标栏顺序（角色/枪械/地图 为一级，其余收进「其他」二级）
CATEGORIES = [
    "角色", "特感", "枪械", "近战", "医疗品", "投掷",
    "UI", "音效音乐", "载具", "弹药", "材质特效", "动作",
    "地图", "杂项", "其他", "未分类",
]

SURVIVOR_NAMES = {
    "gambler": "Nick(尼克)", "producer": "Rochelle(罗谢尔)", "coach": "Coach(教练)",
    "mechanic": "Ellis(艾利斯)", "namvet": "Bill(比尔)", "teenangst": "Zoey(佐伊)",
    "biker": "Francis(弗朗西斯)", "manager": "Louis(路易斯)",
}

SPECIAL_NAMES = {
    "hunter": "Hunter", "smoker": "Smoker", "boomer": "Boomer", "charger": "Charger",
    "spitter": "Spitter", "jockey": "Jockey", "tank": "Tank", "witch": "Witch",
    "common": "普通感染者", "common_male": "普通感染者", "common_female": "普通感染者",
}

# 完整模型段名（高精度，优先于关键词）
WEAPON_SEG_NAMES = {
    "w_rif_ak47": "AK-47(AK)", "w_rif_m16a2": "M16A2(M4)", "w_rif_desert": "沙漠步枪 SCAR(三连发)",
    "w_rif_sg552": "SG552", "w_snip_awp": "AWP(大狙)", "w_snip_military": "军用狙击枪(连狙)",
    "w_snip_scout": "侦察步枪(鸟狙)", "w_snip_hunting": "猎枪(木狙)", "w_smg_uzi": "Uzi 冲锋枪(乌兹)",
    "w_smg_mp5": "MP5", "w_smg_silenced": "消音冲锋枪(MAC-10)", "w_shotgun_chrome": "泵动霰弹枪(木喷/铁喷)",
    "w_shotgun_spas": "SPAS-12(二代连喷)", "w_shotgun_auto": "自动霰弹枪(一代连喷)",
    "w_grenade_launcher": "榴弹发射器(榴弹枪)", "w_m60": "M60(机枪)", "w_chainsaw": "电锯",
    "w_pistol": "手枪", "w_pistol_351": "马格南手枪(马格南)",
}

# 武器上下文路径内的关键词 -> (类别键, 显示名)。
# 每条路径只取第一个命中的关键词，故顺序 = 优先级（长的/更具体的在前）。
KEYWORDS = [
    # 医疗品 / 投掷（先于武器，避免 eq_* 掉进武器混合分支）
    ("eq_medkit", "med", "急救包(医疗包)"), ("medkit", "med", "急救包(医疗包)"),
    ("eq_defibrillator", "med", "除颤器(电击器)"), ("defibrillator", "med", "除颤器(电击器)"),
    ("eq_adrenaline", "med", "肾上腺素"), ("adrenaline", "med", "肾上腺素"),
    ("eq_painpills", "med", "止痛药"), ("painpills", "med", "止痛药"),
    ("eq_molotov", "thr", "燃烧瓶"), ("molotov", "thr", "燃烧瓶"),
    ("eq_pipebomb", "thr", "土制炸弹"), ("pipebomb", "thr", "土制炸弹"),
    ("eq_vomitjar", "thr", "胆汁罐"), ("vomitjar", "thr", "胆汁罐"),
    ("bile_flask", "thr", "胆汁罐"), ("bile", "thr", "胆汁罐"),
    # 武器：具体型号优先
    ("desert_eagle", "wpn", "马格南手枪(马格南)"), ("eagle", "wpn", "马格南手枪(马格南)"),
    ("pumpshotgun", "wpn", "泵动霰弹枪(木喷/铁喷)"), ("chrome", "wpn", "泵动霰弹枪(木喷/铁喷)"),
    ("autoshotgun", "wpn", "自动霰弹枪(一代连喷)"), ("autoshot", "wpn", "自动霰弹枪(一代连喷)"),
    ("shotgun_spas", "wpn", "SPAS-12(二代连喷)"), ("spas", "wpn", "SPAS-12(二代连喷)"),
    ("ak47", "wpn", "AK-47(AK)"), ("ak_47", "wpn", "AK-47(AK)"),
    ("m16a2", "wpn", "M16A2(M4)"), ("m16", "wpn", "M16A2(M4)"),
    ("sg552", "wpn", "SG552"),
    ("sniper_military", "wpn", "军用狙击枪(连狙)"), ("military_sniper", "wpn", "军用狙击枪(连狙)"),
    ("snip_military", "wpn", "军用狙击枪(连狙)"),
    ("sniper_awp", "wpn", "AWP(大狙)"), ("awp", "wpn", "AWP(大狙)"),
    ("sniper_scout", "wpn", "侦察步枪(鸟狙)"), ("scout", "wpn", "侦察步枪(鸟狙)"),
    ("hunting_rifle", "wpn", "猎枪(木狙)"), ("hunting", "wpn", "猎枪(木狙)"),
    ("grenade_launcher", "wpn", "榴弹发射器(榴弹枪)"),
    ("silenced_smg", "wpn", "消音冲锋枪(MAC-10)"), ("smg_silenced", "wpn", "消音冲锋枪(MAC-10)"),
    ("mp5", "wpn", "MP5(MP5)"), ("uzi", "wpn", "Uzi 冲锋枪(乌兹)"),
    ("desert_rifle", "wpn", "沙漠步枪 SCAR(三连发)"), ("scar", "wpn", "沙漠步枪 SCAR(三连发)"),
    ("m60", "wpn", "M60(机枪)"), ("chainsaw", "wpn", "电锯"),
    ("pistol_351", "wpn", "马格南手枪"), ("magnum", "wpn", "马格南手枪(马格南)"),
    ("minigun", "wpn", "迷你炮(加特林)"),
    # 武器：泛化兜底（放最后）
    ("knife_t", "mel", "小刀"), ("knife", "mel", "小刀"),
    ("w_bat", "mel", "棒球棒"), ("baseball_bat", "mel", "棒球棒"),
    ("sniper", "wpn", "狙击枪(狙)"), ("pump", "wpn", "泵动式霰弹枪(木喷)"),
    ("shotgun", "wpn", "霰弹枪(木喷/铁喷)"), ("smg", "wpn", "冲锋枪(乌兹/MAC-10)"),
    ("rifle", "wpn", "步枪(M4)"), ("pistol", "wpn", "手枪"),
]

MED_NAMES = dict((k, v) for k, (_, v) in
                 [(kw, (kind, disp)) for kw, kind, disp in KEYWORDS if kind == "med"])

MELEE_NAMES = {
    "crowbar": "撬棍", "axe": "消防斧", "fireaxe": "消防斧", "katana": "武士刀",
    "machete": "砍刀", "baseball_bat": "棒球棒", "frying_pan": "平底锅",
    "electric_guitar": "电吉他", "tonfa": "警棍", "golfclub": "高尔夫球杆",
    "cricket_bat": "板球棒", "knife": "小刀", "pitchfork": "草叉", "shovel": "铁锹",
    "riot_shield": "防暴盾", "bat": "棒球棒",
    # 国内自制近战武器常见拼音名
    "caidao": "菜刀", "hammer": "锤子", "wrench": "扳手", "pingpang": "乒乓球拍",
    "onion": "洋葱", "chair": "椅子", "guizi": "柜子", "xiguapi": "西瓜皮",
}


def _norm_key(s):
    """归一化比较键：仅保留字母数字与中日韩字符，小写。"""
    return re.sub(r"[^0-9a-z一-鿿]+", "", (s or "").lower())


def _resolve_candidates(cands, hint=""):
    """解析白名单候选：唯一物品 / 单一大类 / 标题消歧。
    返回 (category, item) 或 None（多类混合，交启发式处理）。"""
    nonempty = {(c, i) for c, i in cands if i}
    # 唯一的具体物品命中 → 直接采用（忽略伴随的 UI/杂项 等泛化命中）
    if len(nonempty) == 1:
        return next(iter(nonempty))
    cats = set(c for c, _i in cands)
    if len(cats) != 1:
        return None
    cat = next(iter(cats))
    items = set(i for _c, i in cands)
    if len(items) == 1:
        return (cat, items.pop())
    # 多物品：用标题/提示消歧（如整合包资源里命中多种武器，标题指明 M60）
    hkey = _norm_key(hint)
    if hkey:
        matched = set()
        for i in items:
            full = _norm_key(i)
            base = _norm_key(i.split("(")[0])  # 基本名（括号前）
            if (full and full in hkey) or (base and base in hkey):
                matched.add(i)
        if len(matched) == 1:
            return (cat, matched.pop())
    return (cat, "")


def _has_specific_appearance_signal(paths):
    """这个包里是否有「明确指向某个具体人物/武器」的外观替换信号。

    用于决定 addonContent_Campaign 标记该不该被内容启发式覆盖。

    只有出现**能锁定到具体物品**的证据才算数：
      · models/survivors/survivor_<名> / models/infected/<名>（具体人物模型）
      · 武器 v_/w_models 的已知型号

    单纯的 sound/ materials/ 或泛泛的 models/ 不算 —— 地图包本来就带这些。
    """
    if not paths:
        return False
    for p in paths:
        # 具体幸存者模型
        if p.startswith("models/survivors/") or p.startswith("materials/models/survivors/"):
            for seg in p.split("/"):
                stem = seg.split(".")[0]
                if stem.startswith("survivor_"):
                    return True
                if stem in SURVIVOR_NAMES:
                    return True
        # 具体特感模型
        if p.startswith("models/infected/") or p.startswith("materials/models/infected/"):
            for seg in p.split("/"):
                stem = seg.split(".")[0]
                if stem in SPECIAL_NAMES:
                    return True
        # 具体武器型号
        if _is_weapon_context(p):
            for seg in p.split("/"):
                stem = seg.split(".")[0]
                # 段名写法多样：w_rifle_ak47 / v_rifle_ak47 / rifle_ak47 / w_rif_ak47，
                # 而 WEAPON_SEG_NAMES 的键统一是 w_<缩写>_<型号> 这种形式。
                # 所以先剥掉 w_/v_，再把 rifle_/shotgun_… 缩写成 rif_/snip_，
                # 最后补回 w_ 前缀去查表。
                base = stem
                for pfx in ("w_", "v_"):
                    if base.startswith(pfx):
                        base = base[len(pfx):]
                cands = {stem, base, "w_" + base, "v_" + base}
                for mid, short in (("rifle_", "rif_"), ("shotgun_", "shotgun_"),
                                   ("sniper_", "snip_"), ("smg_", "smg_"),
                                   ("pistol_", "pistol_")):
                    if base.startswith(mid):
                        rest = base[len(mid):]
                        cands.add("w_" + short + rest)
                        cands.add("w_" + base)
                if cands & set(WEAPON_SEG_NAMES):
                    return True
    return False


def _looks_like_framework(addoninfo, hint, all_paths=None):
    """判断这个 vpk 是不是「前置/框架/基础库」包，而不是具体物品的外观替换。

    ★ 必须非常保守：误判会把正常皮肤丢进「杂项」，用户完全找不到它。
    所以只认「包自己明确声明是依赖包」的证据，不看内容特征。

    证据来源（任一即可）：
      A. addoninfo 的标题或描述里出现依赖类措辞（英文 base/framework/dependency…、
         中文「前置模组」「基础库」「框架」…）
      B. 文件名/标题 hint 里出现框架关键词

    并且要求：**这个包没有锁定到单一具体物品**（item 为空）。
    如果一个包自称 base 但同时明确只改 Ellis，那它更可能是「Ellis 皮肤包」，
    按外观处理更安全。
    """
    # 依赖类措辞。刻意收窄，避免误伤。真实踩过的坑：
    #   "using Theuaredead's port of the original medkit animations as a base"
    #   —— 这是「基于某人的移植作品」，不是「前置依赖包」。
    #   所以不接受裸的 "as a base"，只接受 "base mod/base dependency/
    #   base pack/base library/base file" 这类明确指向包的组合。
    _EN = re.compile(
        r"\bbase\s+(?:mod|dependency|pack|library|file|addon)\b"
        r"|\b(?:framework|dependency|prerequisite|prereq)\s+(?:mod|pack|for)\b"
        r"|\brequired\s+for\b|\brequires\s+this\b"
        r"|\bdependency\s+for\b",
        re.I)
    # 中文按子串，但要求成词（避免「平台包」之外的零散命中）
    _ZH = re.compile(r"前置(?:模组|模块|包|依赖)?|基础库|框架(?:包|模组)?|依赖包|基础包")

    texts = []
    if isinstance(addoninfo, dict):
        # addoninfo 的键大小写不统一（AddonTitle / addontitle 都出现过）
        for k, v in addoninfo.items():
            kl = str(k).lower()
            if kl in ("addontitle", "addondescription", "addontag", "addonnotes"):
                texts.append(str(v or ""))
    if hint:
        texts.append(str(hint))

    if not texts:
        return False
    blob = " ".join(texts)

    hit_en = bool(_EN.search(blob))
    hit_zh = bool(_ZH.search(blob))
    if not (hit_en or hit_zh):
        return False

    # 「自称框架」还不够：必须确实锁不到单一具体物品。
    # 这里不复用 _single_item（它需要已解析的集合），只用路径粗判：
    # 若包内含多个不同人物的模型 → 更像是跨人物的框架，而不是单个皮肤。
    if all_paths:
        people = set()
        for p in all_paths:
            if "models/survivors/" in p or "models/infected/" in p:
                for seg in p.split("/"):
                    stem = seg.split(".")[0]
                    if stem.startswith("survivor_"):
                        people.add(stem)
                    elif stem in SURVIVOR_NAMES or stem in SPECIAL_NAMES:
                        people.add(stem)
        # 覆盖 3 个以上不同人物 → 明显是通用框架，不是单人物皮肤
        if len(people) >= 3:
            return True
        # 一个人物都没识别出来（如 ksep.mdl / gestures_*）也是框架特征
        if len(people) == 0:
            return True
        # 只覆盖 1~2 个人物：可能是正常皮肤包，交给后续分类
        return False

    return True


def classify_paths(paths, addoninfo=None, mission=None, hint=""):
    """返回 (category, item, tags)。item 为空串表示多项/整体/不细分。"""
    paths = [p.lower() for p in paths]
    tags = []

    # 1) 战役（mission 文件是最强信号），标题优先 DisplayTitle
    if mission and isinstance(mission, dict):
        name = mission.get("DisplayTitle") or mission.get("DisplayName") \
            or mission.get("Name") or ""
        return ("地图", str(name), tags)

    # 1.5) 框架 / 前置依赖包 → 杂项
    #
    # 为什么要在实体分类之前判：这类包的 vpk 里**天然含有** survivor/infected 模型
    # （它们要覆盖这些人的动画），所以会被下面的 `if survivors:` / `if infected:`
    # 抢先命中，错误地出现在「角色」/「特感」侧栏里。
    #
    # 真实案例（2026-11-20 实测库）：
    #   2121557118  xdReanimsBase      59 条路径里 40 条 infected、56 条 anim
    #               addoninfo: "Base dependency for re-animations mods"
    #   3062523298  KSEP Platform      16 条 survivors 路径，但无任何具体人物名
    #               addoninfo: "特定人物模组实现静态表情的前置模组"
    #
    # 危害：若被当成外观且 item 非空，启用框架会**静默停用整套皮肤**；
    # item 为空时侥幸不触发互斥，但用户会在「特感」里看到一个框架，无法理解。
    #
    # 判定很保守，只认「明确自称框架」的包，宁可漏判也不误伤正常皮肤：
    #   ① addoninfo 的标题/描述里出现依赖类措辞，或标题里出现框架关键词，且
    #   ② 该包覆盖的人物数量不像「单个皮肤」（0 个识别不出 / ≥3 个跨人物）
    if _looks_like_framework(addoninfo, hint, all_paths=paths):
        return ("杂项", "前置/框架", tags)

    # 1.6) addoninfo 明确声明「这是战役 / 地图」→ 直接归地图，优先于内容启发式
    #
    # 为什么必须前置：地图的多部件包（Part1/2、Part2/2…）拆开卖时，
    # 单个 vpk 里常常只有 sound/models/materials，**没有 maps/*.bsp、也没有
    # missions/*.txt**，于是被内容启发式判成音效音乐/枪械/载具。
    # 一旦被打散，用户在「地图」侧栏就找不到这些部件，而地图缺件根本玩不了。
    #
    # 真实案例（2026-11-20 实测库，12 个部件里 10 个命中此规则）：
    #   2813701533  Divine Cybermancy part2-8  168 条全是 sound/ → 曾判成音效音乐
    #               addoninfo: addonContent_Campaign=1  ← 它自己说得很清楚
    #   3825198598  档案:零 part2              addonContent_Map=1
    #
    # ⚠️ 已知边界：有 2 个部件（The Parish Halloween 的 models/materials 包）
    # **既无 addoninfo、也无 mission、也无 bsp**，纯素材包。单看内容无法判定
    # 它属于哪张地图，分类器只能给出「材质特效」。
    # 它们的正确归属要靠「同作者/同路径族」推断，而那需要跨 vpk 知识，
    # 不属于单 vpk 分类器的职责 —— 这类包请让用户手工归入（pinned）。
    if isinstance(addoninfo, dict):
        _is_map_flag = (_flag(addoninfo, "addonContent_Campaign")
                        or _flag(addoninfo, "addonContent_Map"))
        if _is_map_flag and not _has_specific_appearance_signal(paths):
            name = ""
            for k, v in addoninfo.items():
                if str(k).lower() in ("addontitle", "addontitle_multi"):
                    name = str(v or "").strip()
                    break
            if not name:
                name = str(hint or "").strip()
            return ("地图", name, tags)

    has_bsp = any(p.startswith("maps/") and p.endswith(".bsp") for p in paths)

    survivors = set()
    infected = set()
    weapons = set()
    melee = set()
    meds = set()
    throws = set()
    ui = False
    sound = False
    music = False
    vehicles = False
    ammo = False
    particles = False
    anim = False
    any_weapon_ctx = False
    weapon_mdl_paths = []
    weapon_other_paths = []
    only_materials = bool(paths)

    for p in paths:
        if not p.startswith("materials/"):
            only_materials = False

        if p.startswith("models/survivors/") or p.startswith("materials/models/survivors/"):
            matched = False
            for seg in p.split("/"):
                stem = seg.split(".")[0]
                if stem.startswith("survivor_"):
                    tail = stem[len("survivor_"):]
                    for _suf in ("_light", "_low", "_hq"):
                        if tail.endswith(_suf):
                            tail = tail[: -len(_suf)]
                    survivors.add(SURVIVOR_NAMES.get(tail, tail))
                    matched = True
                elif stem in SURVIVOR_NAMES:
                    survivors.add(SURVIVOR_NAMES[stem])
                    matched = True
                elif stem.startswith("anim_") or stem == "animations":
                    anim = True
                    matched = True
            if not matched:
                survivors.add("")  # 幸存者相关但未识别具体人物
        elif p.startswith("models/weapons/melee/") or p.startswith("materials/models/weapons/melee/"):
            # 近战模型有 w_（世界）/v_（第一人称）/w_melee_/v_melee_ 多种前缀
            for seg in p.split("/"):
                stem = seg.split(".")[0]
                for pfx in ("w_melee_", "v_melee_", "w_", "v_"):
                    if stem.startswith(pfx):
                        stem = stem[len(pfx):]
                        break
                if stem in MELEE_NAMES:
                    melee.add(MELEE_NAMES[stem])
                elif stem.startswith("melee_"):
                    melee.add(_display_name(MELEE_NAMES, stem[len("melee_"):]))
        elif p.startswith("scripts/melee/"):
            fname = p.split("/")[-1]
            melee.add(_display_name(MELEE_NAMES, fname[:-4] if fname.endswith(".txt") else fname))
        elif p.startswith("models/infected/") or p.startswith("materials/models/infected/"):
            matched = False
            for seg in p.split("/"):
                stem = seg.split(".")[0]
                if stem in SPECIAL_NAMES:
                    infected.add(SPECIAL_NAMES[stem])
                    matched = True
            if not matched:
                infected.add("")  # 特感相关但未识别
        elif _is_weapon_context(p):
            any_weapon_ctx = True
            if p.endswith(".mdl"):
                weapon_mdl_paths.append(p)
            else:
                weapon_other_paths.append(p)
        if p.startswith("scripts/") and "hud" in p:
            ui = True
        if p.startswith("resource/ui/") or "clientscheme" in p:
            ui = True
        if p.startswith("materials/vgui/"):
            ui = True
        if p.startswith("sound/"):
            sound = True
            if "/music/" in p or p.startswith("sound/music/"):
                music = True
        if "props_vehicles" in p:
            vehicles = True
        if not ammo:
            for seg in p.split("/"):
                if seg == "ammo" or seg.startswith("ammo_") or seg.endswith("_ammo"):
                    ammo = True
                    break
        if p.startswith("particles/") or "particle_manifest" in p:
            particles = True
        if "animations" in p.split("/"):
            anim = True

    # 1.5) 武器/近战判定：以 .mdl 文件名为权威信号，全文件族取最具体关键词
    if any_weapon_ctx and not (weapons or meds or throws or melee):
        generic_start = next(i for i, (kw, k, d) in enumerate(KEYWORDS) if kw == "sniper")
        all_hits = []
        for mp in weapon_mdl_paths:
            hit = None
            for seg in mp.split("/"):
                stem = seg.split(".")[0]
                if stem in WEAPON_SEG_NAMES:
                    hit = (-1, "wpn", WEAPON_SEG_NAMES[stem])
                    break
            if hit is None:
                for i, (kw, kind, d) in enumerate(KEYWORDS):
                    if kw in mp:
                        hit = (i, kind, d)
                        break
            if hit:
                all_hits.append(hit)
        if not all_hits:
            for mp in weapon_other_paths:
                for i, (kw, kind, d) in enumerate(KEYWORDS):
                    if kw in mp:
                        all_hits.append((i, kind, d))
                        break
        if all_hits:
            kinds = set(k for _i, k, _d in all_hits)
            if len(kinds) == 1:
                kind = kinds.pop()
                disps = set(d for _i, k, d in all_hits if k == kind)
                spec = set(d for i, k, d in all_hits
                           if k == kind and (i == -1 or i < generic_start))
                target = melee if kind == "mel" else                     meds if kind == "med" else throws if kind == "thr" else weapons
                if len(disps) == 1:
                    target.add(disps.pop())
                elif len(spec) == 1:
                    target.add(spec.pop())
                else:
                    target.add("")  # 多项武器包
            else:
                weapons.add("")  # 医疗/投掷/武器混合包
        _dbg_unused = 0 and print("[DBG] hits:", all_hits, "| weapons:", weapons, "| meds:", meds,
              "| throws:", throws, "| melee:", melee, "| ctx:", any_weapon_ctx, flush=True)
    # 2) 单张地图（有 bsp 无 mission）
    if has_bsp:
        return ("地图", "", tags)

    # 2.5) 官方资源白名单
    cands = set()
    for p in paths:
        base = p.rsplit("/", 1)[-1]
        stem = base.split(".")[0]
        for cand in (_cdata.lookup_stem(stem) or ()):
            cands.add(cand)
    if cands:
        resolved = _resolve_candidates(cands, hint)
        if resolved is not None:
            cat, item = resolved
            return (cat, item, tags)
        # 多大类混合包 → 落到启发式


    # 3) 实体内容类别
    if survivors:
        return ("角色", _single_item(survivors), tags)
    if infected:
        return ("特感", _single_item(infected), tags)
    if melee:
        return ("近战", _single_item(melee), tags)
    if meds or throws or weapons:
        if meds and not throws and not weapons:
            return ("医疗品", _single_item(meds), tags)
        if throws and not meds and not weapons:
            return ("投掷", _single_item(throws), tags)
        if weapons and not meds and not throws:
            return ("枪械", _single_item(weapons), tags)
        return ("枪械", "", tags)  # 混合包
    if any_weapon_ctx:
        return ("枪械", "", tags)  # 武器相关但未识别型号
    if ui:
        return ("UI", "", tags)
    if ammo:
        return ("弹药", "", tags)
    if vehicles:
        return ("载具", "", tags)
    if anim:
        return ("动作", "", tags)
    if sound:
        return ("音效音乐", "音乐" if music else "", tags)

    # 3.5) 白名单路径规则（启发式未解决时：脚本/语音/杂项道具等）
    rule_hits = _cdata.match_rules(paths)
    if rule_hits:
        resolved = _resolve_candidates(rule_hits, hint)
        if resolved is not None:
            cat, item = resolved
            return (cat, item, tags)

    # 4) addoninfo 标签兜底
    if addoninfo and isinstance(addoninfo, dict):
        for key in addoninfo:
            k = key.lower()
            if k.startswith("addoncontent_"):
                tags.append(k[len("addoncontent_"):])
        if _flag(addoninfo, "addonContent_Campaign"):
            return ("地图", "", tags)
        if _flag(addoninfo, "addonContent_Survivor"):
            return ("角色", "", tags)
        if _flag(addoninfo, "addonContent_BossInfected") or _flag(addoninfo, "addonContent_Infected"):
            return ("特感", "", tags)
        if _flag(addoninfo, "addonContent_weapon"):
            return ("枪械", "", tags)
        if _flag(addoninfo, "addonContent_Sound") or _flag(addoninfo, "addonContent_Music"):
            return ("音效音乐", "", tags)
        if _flag(addoninfo, "addonContent_Prop"):
            return ("杂项", "", tags)

    # 5) 其余
    if particles or only_materials:
        return ("材质特效", "", tags)
    if paths:
        return ("杂项", "", tags)
    return ("未分类", "", tags)


def _is_weapon_context(p):
    return (
        "/v_models/" in p or p.startswith("v_models/")
        or "/w_models/" in p or p.startswith("w_models/")
        or p.startswith("materials/weapons/")
        or p.startswith("models/weapons/")
        or p.startswith("materials/models/weapons/")
    )


def _single_item(items):
    """集合只有一个非空元素时返回它，否则空串。"""
    nonempty = {i for i in items if i}
    if len(items) == 1 and "" in items:
        return ""
    if len(nonempty) == 1:
        return next(iter(nonempty))
    return ""


def _display_name(table, token):
    return table.get(token, token)


def _flag(addoninfo, key):
    try:
        v = addoninfo.get(key, addoninfo.get(key.lower(), 0))
        return str(v) in ("1", "true", "True")
    except AttributeError:
        return False


def classify_vpk(vpk, addoninfo=None):
    """便捷入口：直接用 VpkDir 分类。返回 (category, item, tags, mission)。"""
    from . import vpk as _vpk  # 局部导入避免循环
    mission, _mpath = _vpk.extract_mission(vpk)
    if addoninfo is None:
        addoninfo = _vpk.extract_addoninfo(vpk)
    category, item, tags = classify_paths(vpk.paths(), addoninfo=addoninfo, mission=mission)
    return category, item, tags, mission
