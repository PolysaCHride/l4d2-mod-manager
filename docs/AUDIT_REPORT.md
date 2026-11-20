# 认知成本审计报告

> 2026-11-20 · 四个独立审计并行完成
> 目的：量化一个「能力很强但完全不了解项目」的团队接手需要多少成本，并定位成本来源。
>
> 本报告是 `HANDOFF.md` 的支撑材料。交接文档给结论，这里给证据。

---

## 审计方法

分四路并行，各自负责不重叠的范围：

| 审计 | 范围 | 方法 |
|---|---|---|
| 前端 | `app/webui/` 全部 | 逐函数读 + 交叉验证 bridge/events/api |
| 后端 | `app/shell/` + `main_web.py` + spec | 与 `app/ui/workers.py` 逐行对比 |
| 契约 | 前后端字段流转 | 逐字段追踪 + 30 个 API 方法逐个核对 |
| 文档 | 仓库状态 + 可复现性 | 模拟新人从零上手 |

**共同约束**：只读，不修改文件，不运行程序（避免脏数据污染判断）。

---

## 一、总体结论

### 1.1 认知成本量化

| 模块 | 行数 | 读懂所需 | 瓶颈 |
|---|---:|---|---|
| `app/shell/` | 1206 | **1.5 工作日** | 必须读 pywebview 源码确认反射机制；合集 bug 要从模糊报错逆推 |
| `app/webui/app.js` | 1597 | **1.5–2 周** | 「每处行为都要独立验证真假」，约 30% 交互路径是假动作 |
| 前后端契约 | — | **2–3 天** | 3 次改名 + 4 个字段静默丢弃 + 6 处枚举副本 |
| 工程流程 | — | **1–2 天** | 跑/测/打/发四条链路全断 |
| **合计** | | **约 3 周** | 同规模、职责清晰的项目通常 3–5 天 |

### 1.2 六倍差距的来源

不是代码行数，不是技术难度。核心是：

> **这个项目里，几乎每一处行为都需要独立验证「它是不是真的」。**

因为演示期留下的假动作（只弹 toast 不写后端）在外观上与真动作**完全一致**。

---

## 二、最严重的问题（P0）

按「会不会导致用户数据错误」排序。

### P0-1 写操作不落盘 —— 已修

**发现的规模**：

```
全文件对 bridge.toggle_mod 的调用：1 处（app.js:672，还是嵌套在 data-pick 分支里）
其余的启停/别名/删除：全部只改内存 + toast
```

**真实表现**：
- 双击启用 → 卡片亮起、Inspector 变绿 → **`.vpk` 一个字都没变，游戏里不生效**
- 重启应用 → 状态复原 → 用户以为「保存失效」
- 删除 → 卡片消失、提示「已移到回收站」→ **文件还在，回收站是空的**

**为什么能长期存活**：界面自洽。没有任何机制会报错。

**修复**：`toggleMod` / `insAlias` / `insDelete` / `insFolder` 全部改为 `await bridge.xxx()` 成功后再改本地状态。

### P0-2 `start_scan` 不发 `job.done` —— 已修

```python
# 修复前
def run(job):
    tasks.scan(job, self._library)
    self._emit("mods.changed", {"mods": mods})
    # ← 没有 job.done
```

**连锁后果**：
1. 前端 `runJob` 的 `onDone` 永不触发
2. `events.js` 的 `statusSink.idle()` 永不执行 → 状态栏永久「扫描中」
3. 首屏「开始整理」按钮永久 `disabled`，文案卡在「正在整理…」

### P0-3 `added` 取错源字段 —— 已修

```python
"added": int(rec.get("mtime") or 0)     # mtime = 文件修改时间
```

而 `store` 里明明有 `added_at`，旧 UI 用的正是它。前端把这个值标成「入库时间」—— **错误的陈述**：用户移动文件，「入库时间」就跳变。

**附带发现（core 侧）**：`library.py:141` 每次重扫都 `new_mod_record()`，`added_at` 被重置，`if old:` 分支不保留它。所以 `added_at` 本身也不可靠。

`_to_mod` 现在做 `added_at or mtime` 兜底。

### P0-4 合集子项类型错误 —— 已修

```python
# 修复前（tasks.py）
child_ids = [str(c.get("publishedfileid")) for c in children ...]
```

而 `steam_api.collection_children()` 返回的是 `list[str]`。

实测复现：
```
children -> ['111']
RAISES -> AttributeError: 'str' object has no attribute 'get'
```

**触发条件**：任何工坊**合集**链接。被 `_err(exc)` 吞成「解析失败: 'str' object has no attribute 'get'」，**没有任何线索指向合集**。

### P0-5 `commit_import` 不清理临时目录 —— 已修

`stage_archives` 在 `data/tmp` 下解压**完整副本**。原版 `importer.import_archive` 有 `finally: cleanup_staged(batch)`，`dialogs.py` 有 4 处调用。

新的 `api.commit_import` 只 `pop` 了内存 dict，**临时目录从未删除**。一个 3GB 的包就留 3GB。

### P0-6 PIL 被排除但代码依赖 —— 已修

```python
# spec: excludes 里有 "PIL"
# api.py: from PIL import Image
```

降级路径是「直接读前 400KB」—— **对 JPEG 来说这不是一张图，是坏掉的片段**。

实测影响：
```
200 个模组，72 个预览图 > 400KB
无 PIL 时 base64 总字节：54.0 MB
```

修复：Pillow 转为必需依赖；无 PIL 时返回空串而非坏图。

### P0-7 后端失败时静默显示空库 —— 已修

`loadFromBridge` 失败时只 `console.warn`，而打包版 `console=False` 看不到。

用户看到：空白模组库 + 「开始整理」按钮。**会以为 200 个模组丢了。**

修复：走 `setStatus('error', { text, action })`，这个分支之前写好了但从未被调用。

---

## 三、次要问题（P1）

### 3.1 契约层

| 问题 | 位置 | 说明 |
|---|---|---|
| `tags` 字段丢失 | `_to_mod` | 旧 UI 搜索含 tags，新 UI 搜不到 |
| `collection` 字段丢弃 | `_to_mod` | 地图合集功能在新 UI 完全不可用 |
| `sizeText` / `addedText` 白算 | `_to_mod` | 后端算了，前端不用，自己重算且算法不同 |
| `mutex` 算了不用 | `_to_mod:214` | 前端仍用硬编码常量 |
| `pinned` 未映射 | `adapt()` | 后端传了，前端无字段承接 |

### 3.2 枚举重复

**互斥类别 4 份**（取值当前一致）：
```
app/core/classify.py:25      CONFLICT_CATEGORIES   ← 源头
app/shell/api.py:33          MUTEX_CATS
app/ui/main_window.py:48     MUTEX_CATS
app/webui/app.js:106         MUTEX_CATEGORIES
```

**分类映射 2 份**（同一文件内 160 行距离）：
```
app.js:64-74    RAIL_DEFS
app.js:224      modsInRail 内联 map
```

**`_fmt_size` 3 份**：
```
app/shell/api.py:101
app/shell/tasks.py:13
app/ui/util.py:34
```

风险：改一处忘其余。特别是互斥类别 —— 后端会静默停用，前端不弹确认。

### 3.3 职责混乱

| 问题 | 位置 |
|---|---|
| `renderInspector` 166 行，做 4 件事（拼 HTML + 绑 8 组事件 + 发请求 + 改 MODS） | `app.js:530-695` |
| `renderFilters` 100 行，渲染时写 `state.openGroups` | `app.js:272-371` |
| `renderSettings` 122 行，6 种动作分派 | `app.js:1215-1336` |
| `tasks.download` 自己发 `job.done`（与其余 3 处相反） | `tasks.py:99,187` |
| `toggle_mod` 重新实现互斥逻辑，丢弃 core 的返回值 | `api.py:300-309` |

### 3.4 错误处理

```python
def _err(message):
    return {"ok": False, "error": str(message)}
```

27 个方法全部 `except Exception as exc: return _err(exc)` —— **无 traceback**。

对 `AttributeError` 只给 `'str' object has no attribute 'get'`，没有文件、没有行号。P0-4 的合集 bug 之所以难查，就是因为这个。

`except: pass` 的点位（关键的几个）：

| 位置 | 吞掉什么 | 危险度 |
|---|---|---|
| `api.py:252` | `is_l4d2_running` 失败 → `False` | **高**：游戏真在跑时会放行写入 |
| `api.py:175` | `set_proxy` 失败 → 代理静默失效 | 中 |
| `tasks.py:209` | 合集展开失败 → 静默当作「没有子项」 | 中 |

### 3.5 线程

- `JobRunner._jobs` 的读写无锁（`cancel` 可能静默失效）
- 每个 job 起一个 `threading.Timer(60)` 线程
- 无并发上限：两个 `start_scan` 同时跑会让 `Store` 的 dict 在迭代时被修改

---

## 四、文档与流程

### 4.1 仓库状态（审计时）

```
未提交：1239 个文件 / 364.8 MB
其中 Chrome 缓存：291 MB（.qa/ 151MB + .chrome-qa/ 140MB，未被 gitignore）
```

**如果新人 `git clone`**：看不到 `app/shell/`、`app/webui/`、`main_web.py` —— 拿到的是 4 天前的旧版本。

**如果拿到整个目录**：无法分辨哪些是产品、哪些是垃圾，一个 `git add .` 会提交 364MB。

**已处理**：删除 291MB 缓存 + 垃圾文件，补 `.gitignore`，提交 `caf8283`。未跟踪文件从 1239 降到 197。

### 4.2 可复现性

| 问题 | 审计时 | 现在 |
|---|---|---|
| 怎么跑起来 | 只有旧栈可复现，新栈必崩（缺 pywebview） | ✅ `requirements.txt` 补全 |
| 怎么打包 | 两个 spec 无解释，输出同名覆盖 | ✅ 改名区分 + 补 7zip |
| 依赖 | 缺 5 个关键包 | ✅ 已补 |
| 怎么测试 | **完全空白** | ⬜ 仍无文档（脚本存在但未文档化） |
| 数据 schema | 零文档 | ⬜ 待补 |
| 发版 | `build_release.ps1` 只打旧栈 | ⬜ 待补 |

### 4.3 文档冲突

| 冲突 | A 说 | B 说 | 谁对 |
|---|---|---|---|
| 技术路线 | `FRONTEND_PLAN.md` §五推荐 QtWebEngine | `RESULTS.md` 实测 454MB 已否决 | **B** |
| 体积预算 | `REQUIREMENTS_LOCK.md` 100MB | `RESULTS.md` 300MB | 都没超，需统一 |
| FilterPanel 职责 | `BLACKSITE_DECOMPOSITION.md` 含「容量提示」 | `03-FILTERPANEL.md` 已移除 | **B** |

### 4.4 版本漂移（文档 ≠ 代码）

| 文档说 | 实际 |
|---|---|
| `api.py` 27 个方法 | **31 个** |
| `app.js` 1370 行 | **1597 行** |
| TitleBar 56px / StatusBar 30px | **54 / 28** |
| 断点 1100 | **1180** |
| 「改进：只用 token」 | `app.css` 有 **209 处**硬编码 hex |

**模式**：漂移集中在「数字类」和「命名类」，不在「设计意图」上。说明意图维护得好，但没有机制把代码事实回写文档。

### 4.5 危险脚本

`scripts/patch_appjs.py`（574 行）会：
```python
s = SOURCE.read_text()          # demo.js，1133 行
...
TARGET.write_text(s)            # 覆盖 app.js，无条件
```

`app.js` 现在 1597 行，其中几百行是生成后手工加的（导入/下载/设置/引导全链路）。**执行这个脚本会静默丢掉它们。**

而 `WEBUI_DELIVERY.md` 曾写它是「可复现」的生成器。

**已处理**：两个 patch 脚本顶部加了醒目警告。

---

## 五、值得肯定的部分

审计不能只列问题。以下代码质量明显高于周围：

1. **`app/shell/jobs.py`（97 行）** —— 职责单一，`Job` 抽象干净，不知道任何业务。三个 shell 文件里质量最高。

2. **`tasks.py` 的进度加权算法** —— 与 `workers.py` **逐行等价**，包括 `max()` 单调性、`nonlocal` 捕获、默认参数陷阱这些最容易抄错的细节，全部正确。

3. **`runJob`（`app.js:754-770`）** —— 事件订阅、按 `job_id` 过滤、`cleanup()` 统一退订。全文件最干净的一段。

4. **`esc()` 严格转义** —— 通读所有 `innerHTML` 拼接，**没有一处漏转义**。在 1597 行字符串拼 HTML 的文件里很难得。

5. **`app/shell/_selftest.py`** —— 97 行、无窗口、用 `FakeWindow` 验证事件推送，验证了错误路径且不碰真实数据。**最好的测试资产。**

6. **设计文档的诚实度** —— `final/README.md` 24 条已确认决定可直接当验收清单；`03-FILTERPANEL.md` 敢写「这些数字是我编的」；`DEMO.md` 有「演示页 vs 真实应用」差异表。**这种诚实度在交接材料里是稀缺品。**

7. **`bootstrap` / `commit_import` 的契约** —— 顶层结构、批次句柄传递、`job.progress` payload 完全对得上。说明作者在「看得见的地方」是仔细的。

---

## 六、给接手团队的三条建议

如果只做三件事：

### 第一件：补契约测试（约 120 行，半天）

`_to_mod` 与 `adapt` 之间没有任何保护。改一边忘另一边，前端拿到 `undefined`，被 `|| ''` 兜底，**界面照常渲染只是数据错了**。

```python
# tests/test_webui_contract.py
def test_to_mod_field_set_is_frozen():
    rec = new_mod_record("x.vpk")
    out = Api()._to_mod(rec)
    assert set(out) == {"file","title","alias","category","item","size",
                        "sizeText","enabled","workshop_id","thumb","added",
                        "addedText","pinned","mutex"}
```

```js
// tests/adapt_contract.js —— node 直接跑，不需要浏览器
const out = adapt(apiMod);
if (JSON.stringify(Object.keys(out)) !== JSON.stringify(EXPECT)) process.exit(1);
```

同时加一条枚举一致性断言，把 4 份互斥类别钉死。

### 第二件：写 `docs/LEGACY_UI.md`

列全 `app/ui/` 里 6 个未移植功能的「旧实现位置 + 新实现状态」。

这一步认知收益最高 —— 让新人不必读 5887 行才发现「哦，搜索功能没做」。

### 第三件：补 `data/` 的 schema 文档

`library.json` 的字段含义、`clfv`（分类器版本，`classify.CLF_VERSION=14`，改错会让 200 个模组分类全部重算）、备份策略、能否手改。

---

## 七、结论

**这个项目的文档不是「很乱」，而是「两种文档混在一起，缺了第三种」。**

- **设计文档**：A- 水平。逐区定稿、有实测、有诚实声明
- **用户文档**：B+。互斥/一键管理/addonlist 同步讲得比多数同类工具清楚
- **工程文档**：D。跑/测/打/发四条链路全断

新人拿到仓库：**看得懂「要做成什么样」，但不知道「怎么把它跑起来、怎么确认没改坏、怎么发出去」。**

补的成本不高（8 个验证脚本已存在、31 个 API 结构规整、依赖只缺 4 个包），**最大的成本是先把未提交的改动正确地提交进去**。

**已在本次交接准备中完成**：提交基线、清理 291MB 垃圾、补全依赖、修复 7 个 P0、给危险脚本加警告、入口从 245 行降到 106 行。

**当前状态：可交接。** 剩余待办见 `HANDOFF.md` §8。
