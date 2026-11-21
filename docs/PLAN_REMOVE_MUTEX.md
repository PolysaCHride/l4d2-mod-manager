# 拆除互斥机制 · 执行计划

> 2026-11-20。需求边界已与用户确认：
> **放弃互斥组实现，让用户自行管理冲突模组。**
> 具体裁定：
> 1. 「备份后删除组级互斥开关的一切代码，并去掉 inspector 中的同组展示」
> 2. 「不提示、不管互斥、去掉开关」
> 3. **core 里两处自动停用也一起拆**（方案 A，见第五节）

---

## 执行结果（2026-11-21 已完成）

| 步骤 | 结果 |
|---|---|
| 备份 | ✅ `dde9690` + `.tmp/mutex_removal_backup.patch`（40KB，10 文件） |
| core 拆除 | ✅ `enable_new_mods` 去互斥段；`_settle_conflict_selections`、`_enabled_before_adopt` 删除 |
| 后端拆除 | ✅ `_mutex_group_key`、`_mutex_disabled_groups`、`_mutex_enabled`、`set/get_group_mutex` 删除 |
| 前端拆除 | ✅ 10 处全删（含 Inspector 整块同组面板、冲突提示、批量处理、确认框） |
| CSS 清理 | ✅ 减少 2093 字符 |
| 测试 | ✅ 64 Python + 21 Node 全绿；`test_conflict_group_switches_to_latest_new_mod` 改写为相反的断言 |
| 真实数据验证 | ✅ 启用同组两个 → 两个都是 `"1"`，`disabled_siblings` 为空 |
| 数据清理 | ✅ `settings.json` 里遗留的 `mutex_off_groups` 已删 |

### 验证清单结果（对应第八节）

| # | 验证点 | 结果 |
|---|---|---|
| 1 | 启用同组第二个，第一个不被改成 `"0"` | ✅ 实测 `addonlist.txt` |
| 2 | 启用时不弹确认框 | ✅ WebView 实测 `noDialog: true` |
| 3 | Inspector 无同组面板 | ✅ `noGroupPanel: true` |
| 4 | 筛选栏无「N 组待处理」 | ✅ `noConflictLine: true` |
| 5 | 导入多个同组压包全部启用 | ✅ 单测 `test_same_group_mods_all_stay_enabled` |
| 6 | 「整理」不再收敛冲突 | ✅ `_settle_conflict_selections` 已删 |
| 7 | 数据完整性 | ✅ 200 mods / 163 enabled / 1 pinned / 2 collections |

---

## 决策记录

| 问题 | 裁定 | 影响 |
|---|---|---|
| 拆到什么程度 | 全拆（前端 + 后端 + core） | 净删约 385 行 |
| RAIL 放什么开关 | 不放开关，不提示冲突 | 无需新 UI |
| Inspector 同组面板 | 整块删除 | 少一块 UI |
| core 自动停用 | **A. 一起拆** | 导入/下载/整理均不再自动停用 |

> 方案 A 的已知副作用：一次导入 5 个 Ellis 皮肤会**5 个全启用**。
> 这是「用户自行管理」的直接结果，用户已确认接受。

---

## 一、现状盘点（实测确认，不是推测）

### 1.1 前端里跟"互斥"有关的东西一共 10 处

| # | 位置 | 作用 | 处置 |
|---:|---|---|---|
| 1 | `MUTEX_CATEGORIES`（app.js:101） | 判断哪些分类参与互斥 | ❌ 删 |
| 2 | `isSameGroup` / `sameGroup`（:350/:367） | 找"同组"模组 | ❌ 删 |
| 3 | `countConflictsOf` / `countConflicts`（:528/:538） | 统计冲突组数 | ❌ 删 |
| 4 | `conflict-line` 渲染（:441-444） | 筛选栏「N 组待处理」 | ❌ 删 |
| 5 | `data-conflict` 绑定（:475-476） | 点开冲突处理对话框 | ❌ 删 |
| 6 | `showConflictDialog`（:1122+） | 「每组保留最新的一项」批量停用 | ❌ 删 |
| 7 | Inspector 同组面板（:647, :672-675, :700-714） | 同组列表 + 组互斥开关 | ❌ **整块删**（用户明确要求） |
| 8 | `data-pick` 绑定（:878-903） | 点同组兄弟项 | ❌ 删（面板没了） |
| 9 | `toggleMod` 的同组确认框（:1088-1110） | 「会停用同组 X 个」 | ❌ 删 |
| 10 | `adapt()` 的 mutex/groupMutex/mutexApplicable（:954-965） | 字段映射 | ❌ 删 |

### 1.2 后端里的一共 4 处

| # | 位置 | 处置 |
|---:|---|---|
| 1 | `_mutex_group_key()`（api.py:174） | ❌ 删 |
| 2 | `_mutex_disabled_groups` / `_mutex_enabled`（api.py:721-739） | ❌ 删 |
| 3 | `set_group_mutex` / `get_group_mutex`（api.py:741-781） | ❌ 删 |
| 4 | `toggle_mod` 的 mutex 分支（api.py:410-420） | 改为固定 `mutex=False` |

### 1.3 ⚠️ core 里还有两处会**自动停用**模组 —— 裁定：一起拆

| 位置 | 触发时机 | 行为 | 处置 |
|---|---|---|---|
| `library.enable_new_mods`（:582） | 导入压缩包 / 工坊下载完成后 | 新模组启用时把同组旧模组记为 `"0"` | **去掉互斥段**，只保留「设为启用」 |
| `library._settle_conflict_selections`（:637） | 「整理」按钮内部 | 每组强制只留一个 | **整个方法删除**，调用点同步去掉 |

**不拆的后果**（用户已确认不要）：
- 下载一个新 Ellis 皮肤 → 旧的被静默关掉
- 点一次「整理」→ 同组多启用被打回只留一个

这与「让用户自行管理」直接矛盾，所以一起拆。

---

## 二、执行步骤

### 步骤 0：备份（已完成）

```bash
git format-patch -1 dde9690 --stdout > .tmp/mutex_removal_backup.patch
```

- 互斥代码已在 `dde9690` 提交，**git 本身就是完整备份**
- 另存了一份可读补丁 `.tmp/mutex_removal_backup.patch`（40KB，10 个文件）
- 想回看任何一段实现：`git show dde9690:app/webui/app.js`

### 步骤 1：后端先拆（api.py + bridge.js）

1. 删 `_mutex_group_key()`、`_mutex_disabled_groups()`、`_mutex_enabled()`、
   `set_group_mutex()`、`get_group_mutex()`
2. `toggle_mod` 里的 mutex 判定改成固定 `mutex=False`：
   ```python
   disabled = self._library.set_enabled(file_name, enabled, mutex=False) or []
   ```
   → 返回的 `disabled_siblings` 永远为空（字段保留，前端旧代码不炸）
3. `_to_mod` 删掉 `mutexApplicable` / `groupMutex` 两个字段
   **保留** `mutex`（=「这个分类属于互斥类别」）？
   → **删掉**。既然不用互斥了，这个字段只会误导后来的人。
4. `bridge.js` 删 `set_group_mutex` / `get_group_mutex`

### 步骤 2：前端拆（app.js）

1. 删 `MUTEX_CATEGORIES`、`isSameGroup`、`sameGroup`、`countConflictsOf`、
   `countConflicts`、`showConflictDialog`
2. 删筛选栏的 `conflict-line` 渲染与 `data-conflict` 绑定
3. **删 Inspector 的整块同组面板**（:700-714）+ `group`/`groupRows` 变量（:647, :672-675）
4. 删 `data-pick` 绑定（:878-903）
5. `toggleMod` 里删掉「会停用同组 X 个」的确认框，启用就是启用
6. `adapt()` 删 mutex/groupMutex/mutexApplicable
7. 删测试钩子里的 `isSameGroup` / `countConflictsOf` / `MUTEX_CATEGORIES`

### 步骤 3：CSS 清理

删这些已无引用的类：
`.group-panel` `.group-head` `.group-count` `.group-mini` `.group-mutex`
`.group-mutex-copy` `.conflict-line` `.switch.sm`

### 步骤 4：契约测试同步

| 文件 | 改动 |
|---|---|
| `tests/test_webui_contract.py` | 字段集去掉 `mutex`/`mutexApplicable`/`groupMutex`；删 `test_mutex_matches_core`、`test_mutex_categories_match_core` |
| `tests/adapt_contract.js` | 字段集同步；删「同组判定」整节（7 条）、删 `MUTEX_CATEGORIES` 一致性断言 |

> ⚠️ `test_mutex_categories_match_core` 删掉后，**枚举一致性就少一条保护**。
> 但既然前端不再有 `MUTEX_CATEGORIES` 副本，这条保护本来也没对象了。

### 步骤 5：文档同步

| 文件 | 改动 |
|---|---|
| `HANDOFF.md` §6.5 | 「互斥类别有 4 份定义」→ 改为「互斥机制已拆除，core 的 `CONFLICT_CATEGORIES` 仅剩 core 内部使用」 |
| `HANDOFF.md` §7.3 | 「为什么 Inspector 的同组切换有确认框」→ 删或改写 |
| `HANDOFF.md` §8.5 | 标注组级互斥开关已移除 |
| `docs/DATA_SCHEMA.md` §4.1 | 删 `mutex_off_groups` 一节 |
| `docs/SCENARIO_ANALYSIS.md` | 更新：互斥相关建议作废 |
| `docs/ALIGNMENT_AUDIT.md` | 更新 A-1/E-1 里涉及互斥的叙述 |

### 步骤 6：验证

```bash
# 单元测试（应仍全绿，只是用例变少）
.venv/Scripts/python -X utf8 -m unittest discover -s tests

# Node 契约
node tests/adapt_contract.js

# 语法
node --check app/webui/app.js && node --check app/webui/bridge.js

# 端到端
.venv/Scripts/python -X utf8 docs/redesign/proto/e2e_check.py

# 真实行为验证（关键）
# 1) 启用两个同组模组 → 两个都保持 "1"，没有确认框
# 2) Inspector 里不再有「同组」面板
# 3) 筛选栏不再有「N 组待处理」
```

**验证必须看 `addonlist.txt` 本体**，不能只看界面。

---

## 三、影响面（用户可感知的变化）

### 会消失的

| 功能 | 之前 | 之后 |
|---|---|---|
| 「N 组待处理」提示 | 筛选栏显示冲突组数 | 无 |
| 批量处理冲突 | 「每组保留最新的一项」一键停用 | 无 |
| 同组面板 | Inspector 列出同组模组 + 开关 | **整块消失** |
| 启用确认 | 「会停用同组 X 个，继续？」 | **直接启用，不弹框** |
| 下载/导入后 | 自动切到新模组（旧的关掉） | 取决于第五节决策 |
| 「整理」后 | 每组强制只留一个 | 取决于第五节决策 |

### 保留的

- `addonlist.txt` 的读写、启停本身 **完全不变**
- 互斥类别仍存在于 `classify.CONFLICT_CATEGORIES`（分类器内部还会用到它判断类别归属）
- 用户想避免冲突，靠**自己看分类**（模组名/分类在卡片和详情里都还在）

---

## 四、风险与对策

| 风险 | 说明 | 对策 |
|---|---|---|
| **用户同时启用互相替换的皮肤** | 游戏内表现可能异常（两个 Ellis 皮肤同时加载，看谁赢） | 这是用户明确要的：「让用户自行管理」 |
| core 侧仍自动停用（第 1.3 节） | 下载/整理时仍会静默关掉模组，与「自行管理」矛盾 | **见第五节** |
| 删 `mutex` 字段可能破坏旧前端 | 无外部消费者 | 保留 `disabled_siblings` 字段返回空数组，兼容 |
| 枚举一致性测试少一条 | 前端不再有副本 | 无实际损失 |
| 用户后悔 | — | git `dde9690` 完整可回滚 |

---

## 五、执行中需要我自己判断的两点（已定，记录决策依据）

### 5.1 core 两处自动停用：**A. 一起拆**（用户已确认）

| 方案 | 效果 | 代价 |
|---|---|---|
| **A. 一起拆** ✅ 采纳 | 真正的「用户全权管理」：导入/下载/整理都不再自动停用 | 导入一批同组皮肤会**全部启用** |
| B. 只拆 UI 层 | 手动启停不互斥，但导入/下载/整理仍自动停用 | 行为不一致，用户困惑 |
| C. 折中 | 拆整理、保留导入/下载 | 半拆 |

**采纳 A 的理由**：用户要的是「自行管理」，半拆会造成「点启用不管、下载却自动关了」
这种自相矛盾的行为，比全拆更难理解。

**已知副作用（用户已接受）**：一次导入 5 个 Ellis 皮肤 → 5 个全启用。
游戏内表现由引擎决定（通常后加载的覆盖前面的），但这是用户明确要的自主权。

### 5.2 `CONFLICT_CATEGORIES`：保留

它是 `classify.py` 里的常量，core 内部还有用途：

| 使用者 | 用途 | 拆除后是否还需要 |
|---|---|---|
| `library.set_enabled` | 判断要不要停用兄弟项 | ❌ 不再需要（改 `mutex=False`） |
| `library.enable_new_mods` | 同上 | ❌ 删除互斥段后不再需要 |
| `library._settle_conflict_selections` | 分组 | ❌ 整个方法删除 |
| `classify.py` 自身 | **分类器内部**用它标注「这是外观类」 | ✅ **仍需保留** |

所以：**常量保留，只拆消费它的那三处逻辑**。
这样如果以后要恢复互斥，规则源头还在，不用重新推导。

---

## 六、预计改动规模

| 文件 | 增 | 删（约） |
|---|---:|---:|
| `app/shell/api.py` | 5 | 90 |
| `app/webui/app.js` | 5 | 130 |
| `app/webui/app.css` | 0 | 45 |
| `app/webui/bridge.js` | 0 | 10 |
| `tests/test_webui_contract.py` | 5 | 25 |
| `tests/adapt_contract.js` | 5 | 55 |
| 文档 | 40 | 30 |
| **合计** | **~60** | **~385** |

**净删除约 325 行** —— 这是一次减法。

---

## 七、执行顺序

```
0. 备份 ✅ 已完成
1. core 拆（enable_new_mods 去掉互斥段；删 _settle_conflict_selections 及调用点）
2. 后端拆（api.py + bridge.js）
3. 前端拆（app.js）
4. CSS 清理
5. 测试同步 + 全绿
6. 真实数据验证（看 addonlist.txt）
7. 文档同步
8. 提交（独立 commit，便于回滚）
```

---

## 八、验证清单（必须逐条实测）

拆完之后必须证明这几件事，**每一条都要看 `addonlist.txt` 本体，不能只看界面**：

| # | 验证点 | 期望 |
|---|---|---|
| 1 | 启用同组第二个模组 | `addonlist.txt` 里两个都是 `"1"`，第一个**不被改成 `"0"`** |
| 2 | 启用时是否弹确认框 | 不弹 |
| 3 | Inspector | 没有「同组」面板 |
| 4 | 筛选栏 | 没有「N 组待处理」 |
| 5 | 导入多个同组压缩包 | 全部启用，无任何自动停用 |
| 6 | 点「整理」 | `_settle_conflict_selections` 不再运行，同组多启用保持原状 |
| 7 | 现有数据完整性 | 200 mods / 161 enabled 前后一致 |

---

## 九、回滚方式

```bash
# 完整回滚到拆除前
git revert <本次 commit>

# 或者只捡回某一处实现
git show dde9690:app/webui/app.js | grep -A 20 "isSameGroup"
```
