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
CLF_VERSION = 14

# 会互相冲突、需要同物品互斥的类别（下载/导入后默认禁用，由用户挑选）
CONFLICT_CATEGORIES = {"角色", "特感", "枪械", "近战", "医疗品", "投掷"}

# 下载/导入后直接启用的“下载即用”类别（地图/脚本/音效等叠加型内容）
AUTO_ENABLE_CATEGORIES = {"地图", "UI", "音效音乐", "载具", "弹药", "材质特效", "动作", "杂项"}
# 其余（未分类等无法判断用途的）保持禁用

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


def classify_paths(paths, addoninfo=None, mission=None, hint=""):
    """返回 (category, item, tags)。item 为空串表示多项/整体/不细分。"""
    paths = [p.lower() for p in paths]
    tags = []

    # 1) 战役（mission 文件是最强信号），标题优先 DisplayTitle
    if mission and isinstance(mission, dict):
        name = mission.get("DisplayTitle") or mission.get("DisplayName") \
            or mission.get("Name") or ""
        return ("地图", str(name), tags)

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
