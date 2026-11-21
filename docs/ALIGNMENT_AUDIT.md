# 旧后端 / 旧 UI ↔ 新前端 · 对齐审查

> 2026-11-20 生成。**第一版只做审查，不改代码。**
> 方法：四层逐项对照 —— `app/core/`（能力）→ `app/shell/`（暴露面）
> → `app/webui/`（消费面）→ `app/ui/`（旧行为基准）。
> 每条结论都对着真实代码或真实数据核实过，标注了证据位置。

---

## 处理状态（2026-11-20 第二轮，用户裁定后）

用户已对全部 12 项给出裁定，**已全部落地或明确关闭**（A-1 第七轮完成、B-3 实测后关闭）。

| 项 | 裁定 | 状态 |
|---|---|---|
| A-1 合集 | 合集=纯展示分组、不参与管理逻辑；**UI 暂时搁置** | ✅ **2026-11-21 已做**：详情下方「更多」里展示合集与部件（HANDOFF §8.8） |
| A-2 工坊搜索 | **确认丢弃** | ✅ `SearchWorker` 已删；core 的 `search_workshop` 保留（冻结期不动） |
| B-1 全量采纳 | **改用 `adopt_all`** | ✅ 新增 `start_adopt` + `tasks.adopt_all`；「整理」与「刷新」已分离 |
| B-2 订阅迁移 | **随 `adopt_all` 自动调用** | ✅ 无需单独入口（`adopt_all` 内部第 1 步就是 `migrate_from_workshop`） |
| B-3 预览图下载 | **推后**（先做 E-3 兜底） | ⬜ **2026-11-21 复测后决定不做**：实测只影响 6/200 条，见下 B-3 节 |
| B-4 合集反查 | 随合集 UI 一起，暂不移植 | ⬜ 未实现 |
| C 分类置灰 | **允许改 core 加字段** | ✅ `auto_category`/`auto_item` + 前端置灰展示 |
| D 整理按钮 | 同 B-1 | ✅ 已修 |
| E-1 单击/双击 | 单击选中、双击启停 | ✅ 原本就符合，无需改动 |
| E-2 快捷键 | 只留 F5 / Ctrl+K / Esc | ✅ 已收敛；卡片 Space 启停已移除 |
| E-3 预览图兜底 | **用旧 UI 的 wiki 占位图** | ✅ 已接；`hasThumb` 194 → 200 |

### 本轮修正的两处审查错误（自查更正）

1. **B-3 不是「已实现待移植」**。`PreviewWorker` 在旧 UI 里**从未被实例化**，
   旧 UI 根本没有「下载预览图」入口。它是死代码，所以 B-3 是**首次实现**，
   不是移植 —— 这改变了它的成本估计，因此你裁定推后是合理的。

2. **A-2 的清理比预想简单**。`SearchWorker` 同样从未被实例化；
   旧 UI 的搜索一直是**本地过滤**（`_filtered_mods`），不是在线搜索。
   所以 A-2 只是删一段死代码。

---

## 摘要（第一版审查，保留备查）

| 等级 | 数量 | 含义 |
|---|---:|---|
| **A. 功能域整体缺失** | 2 | 一个完整功能域在新 UI 完全没有入口 |
| **B. 单项功能缺失** | 4 | 具体能力缺失，core 齐备 |
| **C. 字段级静默丢弃** | 2 | 后端传了、前端丢了，**不会报错** |
| **D. 已知语义不符** | 1 | 有入口但行为与承诺不一致 |
| **E. 行为基准差异** | 3 | 交互模型不同，可能是有意改动但未记录 |
| 合计 | 12 | |

**最重要的一条**：合集（Collection）是旧 UI 的一等功能，
在新前端**连字段都没有**（`_to_mod` 直接丢弃 `collection`）。
真实库里有 2 个合集、6 个模组归属 —— 这些数据现在新 UI 完全看不见。

---

## A. 功能域整体缺失

### A-1 合集管理（Collection）—— 完全缺失

这是本次审查发现的**最大缺口**。合集不是一个小功能，
旧 UI 为它建了完整的一等公民：侧栏可筛选、右键可操作、卡片菜单可管理。

**旧 UI 的合集能力（全部核实自代码）**

| 能力 | 旧实现位置 | 新 UI |
|---|---|---|
| 侧栏按合集筛选（`kind == "collection"`） | `main_window.py:1117` `sort_item_entries` | ❌ 无 |
| 归入合集（粘贴链接自动识别 / 选已有） | `main_window.py:1562` `assign_collection_flow` | ❌ 只有提示弹窗 |
| 移出合集 | `main_window.py:1692/1716`（右键 `a_leave` 分支） | ❌ 无 |
| 重命名合集 | `main_window.py:1552` `rename_collection` | ❌ 无 |
| 解散合集（保留模组） | `main_window.py:1542` `dissolve_collection` | ❌ 无 |
| 删除合集（连同部件进回收站） | `main_window.py:1519` `delete_collection_flow` | ❌ 无 |

**core 能力其实全都在**（`store.py` 有完整 CRUD）：

```python
Store.collections()          # 列全部
Store.get_collection(cid)    # 查一个
Store.upsert_collection(cid, info)   # 建/改
Store.remove_collection(cid)         # 删
```

**但 shell 层一个都没暴露**（`app/shell/api.py` 里搜不到 `collection` 的写入调用），
更关键的是 `_to_mod()` **不输出 `collection` 字段**：

```python
# app/shell/api.py  _to_mod() 的实际输出
{file, title, alias, category, item, size, sizeText,
 enabled, workshop_id, thumb, added, addedText, pinned, mutex}
                                                     ↑ 没有 collection
```

所以前端连「这个模组属于哪个合集」都不知道，谈不上 UI。

**真实数据佐证**（当前 `data/library.json`）：

```
ws_2969172769 -> Test Collection    files=['2987256131.vpk']
ws_189971863  -> The Bloody Moors   files=[189941645, 189949153, 189953956,
                                           189966504, 189970619]
带 collection 字段的 mod 数: 6
```

也就是说：**用户已有的 2 个合集、6 个模组归属，在新 UI 里是隐形的。**
数据没丢（还在 json 里），但界面完全看不见，也无法维护。

**影响**：地图类模组的多部件管理（一个自定义地图拆成多个 VPK）在新 UI 里无法操作。
`_to_mod` 丢弃 `collection` 这件事**没有任何报错**，符合 HANDOFF §6.10 描述的
「静默降级」形态 —— 这大概也是它一直没被发现的原因。

### A-2 工坊在线搜索 —— 完全缺失

| | |
|---|---|
| 旧实现 | `workers.py:275` `SearchWorker` |
| core 能力 | `steam_api.search_workshop(query, page, num, sort)` **完好** |
| shell 暴露 | ❌ 无 |
| 新 UI | ❌ 无入口 |

**影响**：用户必须离开工具去网页找链接，再回来粘贴。
现存的下载流程（粘链接 → 解析 → 勾选）**能覆盖「已知 ID」的场景**，
但没法「按关键词发现」。

---

## B. 单项功能缺失

### B-1 全量采纳 `adopt_all`（且当前有语义不符）

| | |
|---|---|
| 旧实现 | `main_window.py:1422` `adopt_all_flow` ← 侧栏「整理」按钮 |
| core 能力 | `Library.adopt_all(progress)` 完好 |
| 新 UI | ❌ 「整理」按钮实际调 `rescan` |

**已实测确认的调用链**：

```
新 UI「整理」(#tidyBtn) / 「开始整理」(#onboardStart)
  → runScan() → bridge.start_scan()
  → api.start_scan() → tasks.scan() → library.rescan()     ← rescan，不是 adopt_all
```

两者行为差异（核实自 `library.py:162` vs `:630`）：

| | `rescan()` | `adopt_all()` |
|---|---|---|
| 重建已有记录 | ✅ | ✅ |
| 顶层未登记 vpk | ❌ 不管 | ✅ 补记 + addonlist 记 `"1"` |
| 子目录里的 vpk（非 workshop） | ❌ 不管 | ✅ 移到顶层，记 `"0"` |
| `workshop/` 子目录 | ❌ 不管 | ✅ 走迁移，保留启用状态 |

**影响**：用户把 vpk 放进 `addons/子目录/` 后点「整理」，模组**不会出现**
（游戏本身也不扫子目录，所以这也解释了为什么「明明放了却加载不到」）。
按钮文案承诺的正是 `adopt_all` 的行为。

> 这条我已写进 `docs/LEGACY_UI.md` §2.6，是本轮审查之前就确认过的。

### B-2 工坊订阅迁移

| | |
|---|---|
| 旧实现 | `workers.py:427` `MigrateWorker` |
| core 能力 | `Library.migrate_from_workshop()` **完好** |
| 新 UI | ❌ 无入口 |

**真实数据佐证**：库里已有 **5 条 `source="migrate"`** 记录，说明这个能力真的被用过。

**影响**：用户在 Steam 订阅的工坊 mod 落在 `addons/workshop/` 子目录里，
新 UI 无法把它们迁移到顶层纳管。这些订阅项在新 UI 里**完全不可见**
（`rescan` 只扫顶层）。

### B-3 预览图批量下载

| | |
|---|---|
| 旧实现 | `workers.py:316` `PreviewWorker` |
| core 能力 | `steam_api.fetch_preview_bytes()` **完好** |
| 新 UI | ❌ 无 |

**影响面（真实数据）**：200 条里 **6 条 `preview` 为空**（3%）。
前端会画占位渐变，不算崩溃，但这 6 个模组永远没有图。

> **2026-11-21 复测结论：不做。**
> 重新按「预览图最终来源」逐条统计（200 条）：
>
> | 来源 | 条数 |
> |---|---|
> | 模组自带 / 工坊订阅落在 addons 旁的 `.jpg` | 194 |
> | `assets/wiki` 占位图兜底（E-3 已接） | 5 |
> | 完全没图 | 0 |
>
> 补下载最多只改善 **6 张图**（与上表估计的 3% 一致），而 `PreviewWorker`
> 在旧 UI 里从未被实例化 —— 这是**首次实现**，要处理网络失败、限速、
> 磁盘缓存、重试，成本远大于收益。除非以后出现「新装模组普遍缺图」，否则关闭。

### B-4 反查物品所属合集

| | |
|---|---|
| 旧实现 | `workers.py:329` `ParentCollectionWorker`，**三路兜底** |
| 新 UI | ❌ 无 |

三路兜底（描述链接 → 作者工坊页 → 标题搜索）是纯领域知识 ——
Steam 没有官方反查接口。**这段代码是知识资产，删掉就永久丢失。**

**影响面**：属于 A-1 合集功能的子能力，单独看影响小。

---

## C. 字段级静默丢弃（最危险的一类）

`_to_mod()` 和 `adapt()` 是两道转换闸门，各丢了一批字段。
**丢弃不会有任何报错** —— 界面照常渲染，只是信息少了。

### C-1 `_to_mod` 丢弃 8 个字段

核实方式：对 `new_mod_record()` 全字段做集合差。

| 丢弃字段 | 值示例 | 有没有真影响 |
|---|---|---|
| `collection` | `'ws_189971863'` | 🔴 **有** —— 导致 A-1 整体缺失 |
| `tags` | `['a']` | 🟡 **有** —— 见下方「搜索字段对比」 |
| `preview` | `''` | 🟢 无 —— 已转成 `thumb`（data URI） |
| `added_at` | `1795168008` | 🟢 无 —— 已转成 `added` |
| `mtime` | `0` | 🟢 无 —— `added` 里有兜底 |
| `source` | `''` | 🟡 轻微 —— 无法区分「扫描来的」还是「下载来的」 |
| `chapters` | `[1]` | 🟢 无 —— 遗留字段，core 里没人读写 |
| `updated_at` | `0` | 🟢 无 —— 该字段从未被写过 |

**当前 `tests/test_webui_contract.py` 的 `DROPPED` 集合把这些全都登记为「有意丢弃」** ——
包括 `collection`。也就是说测试把「功能缺失」固化成了「设计决定」。
这是需要你裁定的地方：`collection` 到底是有意不做，还是当初漏了？

#### 搜索字段对比（`tags` 丢弃的实际后果）

| | 旧 UI | 新 UI |
|---|---|---|
| 搜索覆盖 | `title` / `item` / `file` / **`tags`** | `name` / `alias` / `file` / `item` |
| 证据 | `main_window.py:1199` `" ".join(m.get("tags", []))` | `app.js:305` `m.name + ' ' + m.alias + ' ' + m.file + ' ' + m.item` |

旧 UI 能靠 tags 搜到（分类器给的辅助标签，如武器类别、角色特征），
新 UI 搜不到 —— 而且**不是搜索逻辑漏了字段，是 `adapt()` 根本没接收 `tags`**。
所以补这个不能只改搜索那行，得先让 `_to_mod` → `adapt` 把 `tags` 传过来。

> 新 UI 多支持了 `alias`（旧 UI 的搜索不含 alias）。这是个改进，但不抵消 tags 的缺失。

### C-2 `adapt()` 丢弃 `pinned`

实测确认（`node -e` 直接调 `adapt()`）：

```
adapt 输出字段: id, name, alias, cat, item, size, img, enabled,
                added, addedDate, file, ws, mutex
pinned 是否被接收: false
后端传了 pinned=true，前端拿到: undefined
```

**影响**：用户手工改过分类的模组会置 `pinned=True`（重扫不覆盖）。
但前端**没有任何视觉标识**表示「这个模组被我固定过」。
用户改完分类后，下次扫描分类保住了，界面上却看不出是保住的还是碰巧相同。

真实数据里 `pinned=true` 有 1 条 —— 样本小，但机制上每个用户都会遇到。

---

## D. 语义不符（有入口，但行为与承诺不一致）

### D-1 「整理」按钮 = `rescan`，不是 `adopt_all`

已在 **B-1** 详述。这里单独列出，因为它是**唯一一处「有按钮但做错事」**的问题，
比其他「没按钮」的问题更容易误导用户。

同类还有两处按钮语义需要你确认：

| 按钮 | 文案承诺 | 实际行为 | 判断 |
|---|---|---|---|
| `#refreshBtn`（刷新） | 刷新 | `runScan()` → `rescan` | ✅ 一致 |
| `#tidyBtn`（整理） | 整理 | `runScan()` → `rescan` | ❌ **不一致** |
| `#onboardStart`（开始整理） | 整理 | `runScan()` → `rescan` | ❌ **不一致** |

> 「刷新」和「整理」现在**调的是同一个函数**，两个按钮没有任何区别。
> 这是 `app.js` 里可以直接看到的：
> ```js
> $('#refreshBtn').addEventListener('click', () => runScan());   // 第 1615 行
> $('#tidyBtn').addEventListener('click', () => runScan());      // 第 1616 行
> ```

---

## E. 行为基准差异（可能有意，但未记录）

### E-1 单击 vs 双击启停

| | 旧 UI | 新 UI |
|---|---|---|
| 启停操作 | **单击**即切换 | **双击**才切换，单击只选中 |

`docs/LEGACY_UI.md` 第三节把这条标为「**合理改动，但没文档记录**」。
我认同改动合理（单击选中 + 双击操作是更常见的桌面范式），
但**没有文档记录**本身是问题：后来的人会以为是 bug。

### E-2 键盘快捷键

| 快捷键 | 旧 UI | 新 UI |
|---|---|---|
| `F5` 刷新 | ✅ `_build_shortcuts` | ❌ 无 |
| `Ctrl+F` 聚焦搜索 | ✅ | ❌ 无（新 UI 用 `Ctrl+K`） |
| `Ctrl+K` 聚焦搜索 | ❌ | ✅ |
| `Enter` / `Space` 操作卡片 | — | ✅ |
| `Esc` 关弹窗 | — | ✅ |

**影响小**，但 `Ctrl+F` 是 Windows 用户的肌肉记忆，`Ctrl+K` 更像开发者习惯。
两者都支持的成本很低。

### E-3 预览图兜底层级

| 层级 | 旧 UI（`util.load_thumb`） | 新 UI |
|---|---|---|
| 1. mod 自带/已下载预览 | ✅ | ✅（`thumb` data URI） |
| 2. **wiki 物品图** | ✅ `assets/wiki/<item>.png` | ❌ 无 |
| 3. **wiki 类别图** | ✅ `assets/wiki/<category>.png` | ❌ 无 |
| 4. 渐变占位 | ✅ | ✅（空 `img`） |

**`assets/wiki/` 里有 70 张现成的图**（`AK-47.png`、`Bill.png`、`Boomer.png` …），
是旧 UI 一直在用的资产。新前端完全没利用。

**影响**：6 个无预览图的模组，旧 UI 会显示「AK-47 的物品图」这种有意义占位，
新 UI 只有一片渐变。视觉信息量差很多。

> 注意：这 70 张图**不在 WebUI 包里**（`L4D2ModManagerWeb.spec` 的 `datas`
> 只打了 `webui/` 和 `icon.ico`，没打根 `assets/`）。
> 要启用这个能力，得同时改 spec。

---

## 附：已对齐的部分（确认过，不用再查）

避免你重复劳动，以下是**确认已经对上的**：

| 能力 | 旧实现 | 新栈 |
|---|---|---|
| 扫描 | `ScanWorker` | `start_scan` → `tasks.scan` ✅ |
| 导入（分析） | `ImportAnalyzeWorker` | `analyze_archives` ✅ |
| 导入（提交） | `ImportCommitWorker` | `commit_import` ✅ |
| 下载 | `DownloadWorker` | `start_download` ✅ |
| 拉详情/展开合集 | `DetailsWorker` | `fetch_details` ✅ |
| 检查更新 | `UpdateCheckWorker` | `check_update`（同步）✅ |
| 启停 | `toggle_mod` | `toggle_mod` ✅（含互斥） |
| 别名 | `set_alias` | `set_alias` ✅ |
| 改分类 | `CategoryDialog` | `set_category` ✅（本轮刚接） |
| 删除 | `delete_mod_flow` | `delete_mod` ✅ |
| 打开 mod 位置 | `reveal_mod` | `reveal_mod` ✅ |
| 打开工坊页 | `open_workshop_page` | `open_workshop` ✅（本轮刚接） |
| 启动游戏 | `launch_game` | `launch_game` ✅（本轮刚接） |
| 游戏运行检测 | `is_l4d2_running` | `bootstrap.game` ✅ |

两个**刻意**的差异，不是缺口：

- `ImportWorker`（旧的一键导入）在新栈拆成了「分析 → 勾选 → 提交」两步。
  这是**设计改进**（用户能看到候选再决定），不是功能缺失。
- `archiver.install_portable_7zip` 未移植 —— 发行包已强制内嵌 7-Zip，
  该场景在正式版不存在（见 `LEGACY_UI.md` §2.5）。

---

## 建议的处理顺序

按「用户可感知的影响 × 实现成本」排：

| 顺序 | 事项 | 理由 | 预估 |
|---|---|---|---|
| 1 | **A-1 合集**：先让 `_to_mod` 输出 `collection` | 数据已经在库里，只是没传出去。这是所有合集 UI 的前提 | 小 |
| 2 | **D-1** 把「整理」拆成 `start_adopt`，与「刷新」区分 | 语义不符最误导用户；`adopt_all` 能力现成 | 小 |
| 3 | **B-2** 订阅迁移入口 | 有 5 条真实 migrate 记录，能力现成 | 小 |
| 4 | **C-2** `adapt()` 接收 `pinned` 并显示标识 | 一行代码 + 一个角标 | 极小 |
| 5 | **A-1** 合集的 CRUD UI（归入/移出/重命名/解散） | 依赖第 1 项 | 中 |
| 6 | ~~**B-3** 预览图批量下载~~ | 影响 6/200 条，**实测后关闭** | ~~中~~ |
| 7 | **E-3** wiki 图兜底 | 资产现成，但要改 spec 打包 | 中 |
| 8 | **A-2** 工坊搜索 | 需要新视图 + 分页 | 大 |
| 9 | **E-2** `F5` / `Ctrl+F` | 成本极低，随时可加 | 极小 |

---

## 需要你裁定的三个问题

1. **`collection` 是有意不做，还是当初漏了？**
   它现在被 `test_webui_contract.py` 的 `DROPPED` 集合登记为「有意丢弃」。
   如果是漏的，那条测试就是在**把 bug 固化成契约**。

2. **「整理」和「刷新」要不要合成一个？**
   如果产品上认为「整理」就该是轻量刷新，那应该改的是**按钮文案**而不是加功能；
   如果应该是 `adopt_all`，那 `adopt_all` 会**移动文件**，需要确认框。

3. **`assets/wiki/` 那 70 张图还要不要？**
   要 → 新前端接上 + 改 spec 打包；
   不要 → 从仓库删掉，减少 70 个文件（当前只有旧 UI 在用）。
