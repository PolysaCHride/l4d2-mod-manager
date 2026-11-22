# `data/` 数据格式说明

> 面向：需要读、排查、或**手工修**这个工具数据文件的人。
> 事实来源是代码（`app/core/store.py`、`app/core/library.py`）+ 一份真实的 200 条库。
> 本文档只描述现状，不描述理想状态。

---

## 一、`data/` 里有什么

| 路径 | 是什么 | 能删吗 |
|---|---|---|
| `library.json` | **模组库缓存**。所有登记过的模组、分类、别名、合集 | 能，但会丢掉别名/手工分类/入库时间（见 §3） |
| `library.json.bak` | 上一次 `save_library()` 之前的旧文件，每次保存自动轮换 | 能 |
| `settings.json` | 用户设置（游戏目录、代理、配色、7-Zip 路径） | 能，等于恢复默认 |
| `settings.json.bak` | 同上，旧版本 | 能 |
| `previews/` | 下载回来的预览图 | 能（下次扫描/下载会重新取） |
| `trash/` | `delete_mod` 移进来的 vpk（**不是真删**） | 能，但删了就真没了 |
| `tmp/` | 压缩包导入时的解压暂存 | 能（应用会自己清，见 §5） |
| `thumb-cache/` | >400KB 预览图压出来的 320×180 小图（`<hash>.jpg`）。键 = 路径+mtime+大小 | 能（下次启动重新生成一次，约 3.8s；`clean_cache` 会清掉） |
| `backups/` | 库文件的历史备份 | 能 |
| `webui.log` | 前端日志。**打包版 `console=False`，只有这个文件能看** | 能 |

⚠️ `data/` 整个目录**不进发行包**（`build_release.ps1` 会检查并拒绝）。
   它可能包含本机游戏路径和用户的模组清单。

---

## 二、`library.json` 结构

```jsonc
{
  "version": 1,                 // 文件格式版本，目前恒为 1
  "mods": {                     // 键 = file（addons 顶层的 vpk 文件名）
    "1127584577.vpk": { ...一条记录... }
  },
  "collections": {              // 键 = "ws_<工坊ID>"
    "ws_2969172769": {
      "name": "Test Collection",
      "workshop_id": "2969172769",
      "files": ["2987256131.vpk"]     // 属于这个合集的 vpk 文件名
    }
  }
}
```

**`mods` 用文件名当键，不是数组。** 这样 `get_mod(file)` 是 O(1)，
代价是顺序不保证 —— 排序由 `store.mod_name_sort_key` 在读取时做。

### 2.1 单条 mod 记录的字段

| 字段 | 类型 | 含义 | 谁写它 |
|---|---|---|---|
| `file` | str | addons 顶层文件名，**主键** | 扫描/导入/下载 |
| `title` | str | 显示名。addoninfo → mission 标题 → 工坊 ID → 文件名 | 扫描/在线补全 |
| `alias` | str | 用户自定义别名，**优先于 title 显示** | 用户（`set_alias`） |
| `category` | str | 分类，取值见 `classify.CATEGORIES` | 分类器 / 用户 |
| `item` | str | 具体物品（`AK-47(AK)`、`Ellis(艾利斯)`）。**空 = 该分类整体/未指定**（见 §7.5：目录外的名字会被分类器归空） | 分类器 / 用户 |
| `tags` | list[str] | 分类器给出的辅助标签，**新 UI 不消费**，旧 UI 用于搜索 | 分类器 |
| `size` | int | vpk 字节数 | 扫描 |
| `mtime` | int | 文件 mtime（epoch 秒）。用于判断是否需要重解析 | 扫描 |
| `workshop_id` | str | 工坊 ID，非工坊来源为空串 | 扫描/下载 |
| `preview` | str | **预览图的绝对路径**（不是 base64） | 扫描/下载 |
| `enabled` | bool | 是否启用。**从 `addonlist.txt` 同步而来**，不是权威 | `set_enabled` / 扫描 |
| `chapters` | list | 地图章节。**当前代码库里没有任何地方读或写它**，见 §2.3 | 遗留 |
| `added_at` | int | 首次登记时间（epoch 秒） | `new_mod_record` |
| `updated_at` | int | 预留，当前恒为 0 | — |
| `source` | str | `scan`/`adopt`/`migrate`/`import`/`download` | 各写入路径 |
| `collection` | str | 所属合集 ID（带 `ws_` 前缀）。**不可靠，会被重扫抹成空串** —— 权威来源是 `collections[cid].files`，见 §7.3 | 下载/导入 |
| `pinned` | bool | 用户手工改过分类，扫描不再覆盖 | `set_category` |
| `title_locked` | bool | **标题来自工坊在线补全**，重扫时不覆盖 | `_enrich_from_workshop` |
| `auto_category` | str | **分类器原本给出的分类**。用户第一次改分类时捕获，之后不再变 | `set_category`（仅首次） |
| `auto_item` | str | 同上，对应 `item` | `set_category`（仅首次） |
| `clfv` | int | **分类器版本**，见 §3 —— 改错会让全部模组重算 | 扫描 |

### 2.1.1 `auto_category` / `auto_item` 的语义（2026-11-20 新增）

这两个字段**只在用户第一次手工改分类时写入**，用来回答一个问题：
「管理器当初认为它是什么？」

```
用户没改过分类：
  category='角色'  item='Ellis'   auto_category=(不存在)

用户把「角色/Ellis」改成「杂项」：
  category='杂项'  item=''        auto_category='角色'  auto_item='Ellis'
                                   ↑ 首次改分类时捕获的原值
用户又改成「音效音乐」：
  category='音效音乐'             auto_category='角色'  ← 不变，仍是首次捕获值
```

前端（`_to_mod` → `autoCategory`/`autoItem`）据此在详情栏把
「识别为 角色 / Ellis」**置灰**显示在用户值下面，让用户看得见自己覆盖了什么。

**为什么只在首次捕获**：如果每次都覆盖，`auto_*` 就退化成「上一次的用户选择」，
失去了「管理器认为它是什么」的含义。

**为什么不用 `clfv` 重算**：重算要重新解析每个 vpk（200 个大文件，几分钟），
而在改分类那一瞬间旧值就在手里，存下来是零成本。

**重扫时保留**：`_scan_one` 的 `old` 分支会保住 `auto_*`，
否则一次扫描就让所有模组丢失「识别结果」。

### 2.1.2 `title_locked`：标题来源标记（2026-11-21 新增）

**为什么需要它**：标题有两个来源，质量差很多：

| 来源 | 质量 | 例子 |
|---|---|---|
| `addoninfo.txt`（作者写包里的） | 参差，常带版本号/括号/多语言混排 | `AK-47 Saratoga`、`Pokeball.` |
| 工坊 API（`_enrich_from_workshop`） | 好，作者上传时填的干净名字 | `CSGO AK47 \| Azur Lane-Saratoga(Glowing)` |

`title_locked = true` 表示这个标题来自工坊 API，**重扫时不许被 addoninfo 覆盖**。

**踩过的坑（真实事故）**：修 `addoninfo` 键名大小写 bug 后 `CLF_VERSION` +1，
全库重扫让 **136 个标题变化**，其中 11 组变成「多个不同文件同名」
（`Divine Cybermancy × 4`、`地心引力 × 4`…）—— 用户完全分不清谁是谁。
根因就是重扫无条件用 addoninfo 覆盖了工坊结果。

**当时的回滚**：`data/library.json` 恢复到重扫前，然后做了一次性迁移
把 195 条（有 workshop_id 且标题非纯数字）标记为 `title_locked`，再重扫。
结果：**只 4 条标题变化**（4 个纯数字标题被修好），其余全部保持。

**注意**：`title_locked` 自己也要跨重扫保留（`_scan_one` 的 `old` 分支），
否则第二次重扫又开始用 addoninfo 的差标题。

### 2.2 哪些字段是真·权威

`library.json` 整体只是**缓存**。真正的权威是磁盘：

| 事实 | 权威来源 |
|---|---|
| 有哪些模组 | `left4dead2/addons/` 目录里实际存在的 `*.vpk` |
| 哪些启用 | `left4dead2/addonlist.txt` |
| 预览图 | `addons/<stem>.jpg/png` 等 |

所以：**删掉 `library.json` 不会丢模组**，只会丢掉「用户手工投入的信息」
（`alias` / `pinned`+手工分类 / `added_at`）。

### 2.3 ⚠️ `chapters` 是遗留字段

真实库里 200 条记录有 **197 条**带 `chapters`（其中 48 条非空），
但**整个 `app/core/` 里搜不到 `chapters`** —— 没有代码读它，也没有代码写它。

含义：它是早期版本（地图分章节功能）留下的字段，现在的分类器不再产出。
它不影响正确性（没人读），但会让契约测试误以为「这是 core 关心的事」。
**不要基于它加功能，除非先把生产它的代码找回来。**

---

## 三、`clfv`：分类器版本（最容易踩的一处）

```python
# app/core/classify.py
CLF_VERSION = 17
```

### 版本历史

| 版本 | 变更 | 影响 |
|---:|---|---|
| 17（2026-11-21） | 近战表只留官方 15 把；新增 `_normalize_item`：**目录外的 item 一律归「未指定」**；自制近战目录 `models/weapons/<作者>/melee/` 进近战分支；`category_catalog()` 收进 core | 全库重扫，真实库 200 个模组**分类零变化**（见下） |
| 16（2026-11-21） | 标题提取忽略 `addoninfo` 键的大小写；mission 标题优先于 addoninfo（当它更完整时） | 只修好 4 个纯数字标题，其余靠 `title_locked` 保护不动 |
| 15（2026-11-20） | 新增「前置/框架包」识别；新增「addoninfo 明示 Campaign/Map → 归地图」前置规则 | 全库重扫，200 个模组中 17 个分类变化（见下） |
| 14 | 之前 | — |

**17 版为什么「零变化」**：真实库里没有任何模组真的被分到洋葱/乒乓球拍这类
自制近战上（200 个里一个都没有），所以删掉它们不影响已有记录。这一版的价值
在**防止未来发生**：任何人装了带自制近战的地图，那些名字只会变成「未指定」，
不会再作为子分类污染目录。同时把「分类器写得出、目录里没有」的 7 个孤儿名
（`前置/框架`、`音乐`、`MP5(MP5)` 等）收进目录。

**15 版实际带来的变化**（真实库实测）：

```
144941725  杂项/涂鸦      → 地图/I Hate Mountains      ← 地图部件修回
144943915  载具/''        → 地图/I Hate Mountains      ← 地图部件修回
2813703467 特感/Tank      → 地图/Divine Cybermancy     ← 地图部件修回
3824638277 载具/''        → 地图/太原市beta             ← 地图部件修回
2121557118 特感/''        → 杂项/前置/框架             ← 框架修正
3062523298 角色/''        → 杂项/前置/框架             ← 框架修正
```

结果：4 个地图多部件包回归完整（Divine Cybermancy 15 部件、
The Bloody Moors 5、I Hate Mountains 4、地心引力 4，分类全部统一）。

### 它怎么起作用

`library._scan_one()` 里判断要不要**重新解析 vpk**：

```python
if (old and old.get("mtime") == mtime and old.get("size") == size
        and old.get("clfv") == clf.CLF_VERSION):
    return old, False        # 命中缓存，不解析
# 否则重新解析整个 vpk（可能几百 MB），重算 category/item/tags
```

也就是说：**mtime、size、clfv 三者全一致才走缓存。**
任一项不同 → 这个 vpk 被完整重解析。

### 为什么改它很危险

| 你做的事 | 后果 |
|---|---|
| 改分类规则（`classify.py` / `classify_data.py`）但**没 +1** | 老记录继续用旧分类，新规则只对新模组生效。**永远不会自愈** |
| **+1** | 下次扫描时 **全部 200 个模组** 重新解析 vpk。首次扫描会明显变慢（大库几分钟） |
| 手工改成别的数字 | 等同于 +1，触发全量重算 |
| 把 `clfv` 整个删掉 | `old.get("clfv") == 14` 为 False → 同样触发全量重算 |

### 正确做法

改了任何影响分类的东西（`classify_data.py` 的表格、`classify.py` 的规则、
`vpk.py` 的元数据提取），**必须在提交里把 `CLF_VERSION` +1**，
并在 commit message 里写清「为什么现有记录需要重算」。

当前真实库（200 条）里 `clfv` 全部 = 14，说明没有被手工改过。

---

## 四、`settings.json`

```jsonc
{
  "game_dir": "E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2",
  "proxy": "",                  // 留空则按环境自动探测
  "archiver_path": "",          // 手工指定的 7z.exe；空则自动查找
  "palette": "blacksite",       // blacksite/safehouse/workshop/index
  "motion": true,               // 动画开关
  "mutex": true                 // 同组互斥开关（缺省 = true；见 §7.6）
}
```

**注意**：`proxy` 不只在 `settings.json` 里生效 ——
`api.save_setting('proxy', ...)` 会同时调 `steam_api.set_proxy()` 改**进程级全局变量**。
只改 json 文件、不重启应用，代理不会生效。

`game_dir` 改了会**重建 `Library` 实例**（`api.save_setting` 里置 None 再懒加载）。

### 4.1 `mutex`：同组互斥开关（2026-11-22）

**单一个布尔值，管全部外观类模组**，不是「按组开关」（那是已废弃的 `mutex_off_groups`）。
缺省视为 `true`：新装用户与升级用户都从「同组只允许启用一个」起步。

| 值 | 行为 |
|---|---|
| `true` | 手动启用 A 会停用同 `(分类, 物品)` 的其它模组；导入/下载遵守「组里已有启用项 → 新模组只入库不启用」；「整理」会把每组收敛到一个（保留管理器原本记着启用的那个） |
| `false` | 以上全部不生效，谁都不动 |

参与范围：`classify.CONFLICT_CATEGORIES` 六类外观模组 **且** `item` 非空。
「未指定」不参与；地图/音效/UI/载具等叠加型内容也不参与。

> **`mutex_off_groups` 已废弃。** 2026-11-20 曾加过「按组开关」，2026-11-21 整体拆除，
> 2026-11-22 改成现在这个全局开关。旧 `settings.json` 里如果还有 `mutex_off_groups`，
> 可以安全删除（程序不再读它）。

边界与实现见 `HANDOFF.md §8.17`。

---

## 五、写入与备份策略

`store._atomic_write_json()` 的顺序：

```
1. 写 <name>.tmp
2. 把现有 <name> 改名成 <name>.bak   （失败则忽略）
3. 把 .tmp 改名成 <name>
```

这是**先写临时文件再原子替换**，中途崩溃不会产生半个 JSON。
代价是失败时可能留下一个 `.tmp` 文件（无害，可以删）。

⚠️ 已知限制：`Store` **没有加锁**（`store.mods()` 直接返回内部 dict 引用）。
当前靠「同一时间只有一个任务在跑」避免迭代时被修改。
如果将来允许并发任务，必须先加锁 —— 否则会
`RuntimeError: dictionary changed size during iteration`。

---

## 六、能不能手工改

**能，但要知道边界：**

| 操作 | 安全吗 |
|---|---|
| 改 `alias`（别名） | ✅ 安全，下次扫描会保留 |
| 改 `category` / `item` | ⚠️ 同时设 `"pinned": true`，否则下次扫描会被分类器覆盖；还应设 `auto_category`/`auto_item` 保留识别结果 |
| 删掉某条记录 | ✅ 安全，等于让扫描重新登记它（但会丢 alias/pinned） |
| 改 `enabled` | ❌ **没用**。启用状态从 `addonlist.txt` 同步，扫描会覆盖回来 |
| 改 `clfv` | ⚠️ 见 §3，会触发全量重算 |
| 改 `mtime` / `size` | ⚠️ 会误导缓存判断，可能让扫描跳过实际已变化的 vpk |
| 改 `auto_category` | ⚠️ 只影响界面显示的「识别为…」，不影响任何分类逻辑 |
| 整个文件删掉 | ✅ 会重建，但丢 alias / pinned / added_at |

**改之前先备份**，并且**保证应用没在运行**（否则内存里的副本会覆盖你的修改）。

改完用 `python -m json.tool data/library.json` 验证 JSON 合法 —— 非法 JSON
会被 `Store._load()` 静默当成空库（`except (OSError, ValueError)`），
表现是「模组全没了」，且**日志里没有任何报错**。

---

## 七、已知的坑

### 7.1 `added_at` 每次重扫都会丢

`library.py` 的 `_scan_one()` 每次都 `new_mod_record()`（它把 `added_at`
设成 `now`），`if old:` 分支只保留 `alias` / `enabled` / `pinned`，
**不保留 `added_at`**。

所以「入库时间」这个字段实际含义是「最近一次被重解析的时间」。
`api._to_mod()` 做了 `added_at or mtime` 兜底。

这是 core 的 bug。core 冻结期间只能接受；**如果哪天允许改 core，
第一件该做的就是保住 `added_at`**。

### 7.2 预览图路径失效是正常的

`preview` 存的是绝对路径。用户移动了 `addons/` 里的图片，
或换了盘符，路径就失效。扫描时命中缓存会顺手修正（`_scan_one` 里那段
`if not pv or not os.path.isfile(pv)`），但换盘符需要重新扫描。

`preview` 为空不是错误 —— 前端会画占位渐变。

### 7.3 合集归属：以 `collections` 表为准，别信 mod 记录上的 `collection`

`collections` 的键是 `"ws_<数字>"`（别当纯数字去和工坊接口比较）。

**坑**：mod 记录里也有个 `collection` 字段，看着像是权威来源 —— 并不是。

`_scan_one` 重建记录时只保留 `auto_category` / `auto_item` / `title_locked` /
`pinned`，**不保留 `collection`**。所以只要重扫一次，所有归属都会被抹成空串：

```
2026-11-20 采样：collection 非空 6 条
2026-11-21 实测：collection 非空 0 条（重扫过）
而 collections 表里那 6 条归属始终完好
```

正确做法是**反查**（`app/shell/api.py` 的 `_collection_index()`）：

```python
for cid, info in store.collections().items():
    for f in info["files"]:
        idx[f] = cid          # vpk 文件名 → 合集 ID
```

`_to_mod` 优先用这个索引，记录上的 `collection` 只当兜底（覆盖「刚下载、
还没重扫」的窗口期）。前端拿到的 `collection` 字段因此是准的。

`app/core/` 是冻结层，没有去改 `_scan_one` 的保留字段 —— 反查方式不依赖
记录字段是否同步，重扫多少次都不影响。

前端通过 `bootstrap().collections` 拿到整张表（`api._collections_payload()`），
在模组详情下方的「更多」里显示「合集名 + 各部件（标题/体积/启用状态）」。


---

### 7.4 `item`（子分类）与 `collection`（合集）谁说了算

两者都能表达「这张图属于哪个合集」，但职责不同，别混：

| | `item`（子分类） | `collection`（合集归属） |
|---|---|---|
| 是什么 | 分类器给的第二层分类，**用户可以改** | 工坊合集的成员关系 |
| 存在哪 | `mods[file].item` | `collections[cid].files`（**记录上的同名字段不可信**，见 §7.3） |
| 谁写 | 分类器；用户改分类时 `set_category` | `downloader.download_and_import(..., collection=...)` |
| 会被重扫覆盖吗 | 用户改过（`pinned`）就不覆盖 | 表本身不受重扫影响；记录上的缓存会被抹成空 |
| 界面上的位置 | 过滤树第二层、「分类 / 子分类」 | 卡片上的 `合集名 (x/x)`、详情「更多」里的部件列表 |

**四条规则**：

1. 显示时 `item` 优先；`item` 为空且属于合集 → **前端显示层**回落到合集名
   （只读，不写库）。真实数据里 The Bloody Moors 的 5 个部件 `item` 与合集名
   本来就一致，所以天然对齐。
2. **API 层（`_to_mod`）不许拿合集名填 `item`**。否则等于 collections 覆盖 item，
   会和 `auto_item`/`pinned` 打架，重扫还会把这个假 item 当用户值固化。
   契约测试 `test_item_is_never_filled_from_collection` 锁死这条。
3. 用户改子分类只写 `category`/`item`（`set_category` 置 `pinned`），
   **永远不写 `collections`** —— 那是工坊结构，删了就不可再生。
4. 「归回工坊合集」= 把 `item` 写回合集名，不是删合集、也不是改合集。

**子分类不落库**：数据库里没有「子分类表」，界面上的子分类是
`mods` 的 `item`（+ 合集名回落）现算出来的投影（`app.js` 的 `subItemsOf()`）。
因此：

- 用户新建的子分类 = 某个模组被设成了这个 `item`；最后一个模组移走后它**自动消失**，
  不需要任何清理逻辑。
- 管理器自带的子分类不会因为「空了」被删 —— 没有任何代码会去改别的模组的 `item`。

**「自带的」子分类从哪来**：`bootstrap` 的 `catalog` 字段，由
`app/core/classify.category_catalog()` 现算 —— 人物/特感/枪械/近战/医疗名单、
`classify_data.WHITELIST_STEMS`（每条规则的目标）、`PREFIX_RULES` /
`REGEX_RULES`，以及少数不由词表产出的桶（`EXTRA_ITEMS`：`前置/框架`、`音乐`）。
`api._category_catalog()` 只是转发 + 异常兜底，**不再自己抄一份**。
UI 只负责把它和库里的值并起来渲染。

所以「特感」即使只有 2 个模组，树上也会列出 Boomer/Charger/Hunter/Jockey/
Smoker/Spitter/Tank/Witch/普通感染者/语音 全部 10 项（空项不显示数量，
点进去是空列表）。分类器以后加了新武器，这里自动出现，不需要改前端。

### 7.5 哪些名字能进目录（2026-11-21 收紧）

**目录 = 管理器向所有用户承诺的子分类清单。** 只有管理器自己能担保的物品
才允许出现，判据是 `_normalize_item()`：

| 分类 | item 的合法来源 |
|---|---|
| 角色 / 特感 / 枪械 / 近战 / 医疗品 / 投掷 | 只能来自词表；**目录外的名字一律归空串**（界面显示「未指定」） |
| 杂项 / 载具 / UI / 弹药 / 动作 / 音效音乐 / 材质特效 | 同上，目录外的归「未指定」 |
| 地图 | **例外**：item 是工坊/mission 里扫出来的战役名，每人不同，不校验 |

为什么必须收紧：某些地图/整合包自带自制近战（`scripts/melee/pingpang.txt`、
`models/weapons/gzzc/melee/w_onion.mdl` 这种），它们只在那一张图里成立。
若让这些名字漏进 `item`，前端会把它们当子分类列出来 —— 等于把别人的自制
内容当管理器内置分类发布给所有用户。现在它们的分类仍是「近战」，但
item 为空 → 落在「未指定」里，用户自己看得见、也能手工改名。

对应用例见 `tests/test_classify_rules.py` 的 `TestCustomMeleeIsUnspecified`
与 `TestCatalogIsManagerOwned`。

`app/core/` 未参与这套统一（冻结层）：全部落在 `app/shell/api.py` 与前端显示层。

## 八、真实数据一览（2026-11-20 采样）

了解「正常长什么样」，排查时才有对照：

| 指标 | 值 |
|---|---|
| 模组数 | 200 |
| 合集数 | 2 |
| 全部 `clfv` | 14（一致，没被手工改过） |
| `enabled=true` | 161 |
| `source` 分布 | scan 152 / adopt 31 / download 10 / migrate 5 / import 2 |
| `alias` 非空 | 0 |
| `pinned=true` | 1 |
| `updated_at` 非 0 | 0（该字段从未被写过） |
| `collection` 非空 | 6（**2026-11-21 重扫后变 0**，见 §7.3） |
| `workshop_id` 为空 | 1 |
| `preview` 为空 | 6 |
| `chapters` 存在 | 197（其中非空 48） |
