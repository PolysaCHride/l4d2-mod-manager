# 旧 UI（`app/ui/`）的去留清单

> 5887 行 PySide6 代码。新架构完全不 import 它。
> **但它现在不能删。** 这份文档说明为什么，以及什么时候可以删。

---

## 一、为什么暂时保留

### 1. 它是唯一的行为基准

`app/shell/tasks.py` 是从 `app/ui/workers.py` **重写**的（因为新入口不依赖 Qt）。验证重写是否正确，唯一的办法是对比着看。

这次重写过程中，通过对比发现的实际问题：

| 问题 | 怎么发现的 |
|---|---|
| `cleanup_staged` 漏抄 | 对比 `importer.import_archive` 的 `finally` 分支 |
| 合集子项类型传错 | 对比 `DownloadWorker` 里 `children` 的处理方式 |
| `job.done` 归属不一致 | 对比 `_settle_conflict_selections` 的调用位置 |

**删掉 `workers.py` = 删掉唯一的回归测试。**

### 2. 现有测试依赖它

`tests/test_main_window_helpers.py` 第 4 行：
```python
from app.ui.main_window import mod_count_text, sort_item_entries
```

删 `app/ui/` 会直接让这个测试失败。

### 3. 还有 6 个功能没移植

见下一节。

---

## 二、未移植到新 UI 的功能

### 2.1 工坊在线搜索

| | |
|---|---|
| 旧实现 | `app/ui/workers.py:257` `SearchWorker` |
| 依赖 | `steam_api.search_workshop(query, page, num, sort)` |
| 新 UI 状态 | ❌ 没有入口 |

用户价值：不用离开工具就能搜创意工坊。

### 2.2 预览图批量下载

| | |
|---|---|
| 旧实现 | `app/ui/workers.py:298` `PreviewWorker` |
| 作用 | 给没有本地预览图的模组下载工坊缩略图 |
| 新 UI 状态 | ❌ 没移植 |

影响：新 UI 里无预览图的模组显示占位渐变。

### 2.3 **反查物品所属合集**

| | |
|---|---|
| 旧实现 | `app/ui/workers.py:311` `ParentCollectionWorker` |
| 新 UI 状态 | ❌ 没移植 |

**这是最值得保留的一项。** 它实现了「Steam 没有官方反查接口，于是三路尝试」：

```
1. 从物品描述的 HTML 里找 collection 链接
2. 爬作者工坊页，找包含该物品的合集
3. 用物品标题去搜合集
```

这是**纯领域知识** —— 重写一遍要把这三个坑重新踩一遍。代码在 `workers.py:311-386`，逐路都有注释说明为什么这么做。

### 2.4 工坊订阅迁移

| | |
|---|---|
| 旧实现 | `app/ui/workers.py:409` `MigrateWorker` |
| 作用 | 把用户已订阅的工坊物品从 `addons/workshop/` 迁移到顶层并接管 |
| 核心逻辑 | `library.migrate_from_workshop(...)`（在 core 里，**没有丢**） |
| 新 UI 状态 | ❌ 没入口 |

注意：核心能力在 `library.py` 里完好，只是新 UI 没有触发它的按钮。

### 2.5 便携 7-Zip 安装

| | |
|---|---|
| 旧实现 | `app/ui/workers.py:77` `ArchiverInstallWorker` |
| 作用 | 用户机器没有 7-Zip 时，引导下载便携版 |
| 新 UI 状态 | ❌ 没移植 |

新 UI 现在的行为：找不到解压器时报错。如果包里带了 `_internal/7zip/`，这个场景基本不出现。

### 2.6 全量采纳（adopt_all）

| | |
|---|---|
| 旧实现 | `library.adopt_all(progress=cb)`（core 里） |
| 作用 | 把 `addons/` 里所有未登记的 vpk 补记进库 |
| 新 UI 状态 | ⚠️ 部分 — `start_scan` 走的是 `library.rescan()`，不是 `adopt_all` |

**这两个不是一回事**：

- `rescan()` — 重建已有记录，不动未登记的
- `adopt_all()` — 把未登记的也纳入

新 UI 的「整理」按钮文案暗示的是 `adopt_all`，实际调用的是 `rescan`。**这是一个语义不符，需要确认到底要哪个。**

---

## 三、旧 UI 独有的行为参考

除了功能，`app/ui/` 还记录了这些「怎么做才对」：

| 行为 | 旧实现位置 | 说明 |
|---|---|---|
| `set_enabled` 返回值怎么用 | `main_window.py:1414` | `disabled = self.library.set_enabled(...)` 直接用返回值，不自己算 |
| `sync_enabled_from_addonlist` 何时调 | `main_window.py` 启动时 | 从 addonlist 回读真实状态 |
| 预览图四级兜底 | `util.load_thumb` | mod 自带 → wiki 物品图 → wiki 类别图 → 渐变占位 |
| 名称排序 | `store.mod_name_sort_key` | casefold + file 兜底 |
| 互斥单击切换 | `main_window.py:488` | 旧版单击即切，新版改双击（**合理改动，但没文档记录**） |

---

## 四、什么条件下可以删

**明确的、可执行的标准**：

```markdown
- [ ] 2.1 工坊搜索      → 已移植 / 明确不做
- [ ] 2.2 预览图下载    → 已移植 / 明确不做
- [ ] 2.3 合集反查      → 已移植 / 明确不做
- [ ] 2.4 订阅迁移      → 已移植 / 明确不做
- [ ] 2.5 便携 7zip     → 已移植 / 明确不做
- [ ] 2.6 全量采纳      → 已移植 / 明确不做（先确认 rescan vs adopt_all）
- [ ] tests/test_main_window_helpers.py 已改写为不依赖 app/ui/
```

六项全部有结论后，才可以：

```powershell
git rm -r app/ui/
# 同时删掉：main.py、L4D2ModManager.spec、build_release.ps1 里对旧栈的引用
```

**在那之前，删 `app/ui/` 是纯粹的损失。**

---

## 五、现在就该做的隔离

不用等，现在就可以做这三件事：

### 5.1 在 `app/ui/__init__.py` 加警告

```python
"""旧 PySide6 UI —— 保留作行为基准与功能参考，新架构不依赖此包。

⚠️ 不要在新代码里 import 本包。
⚠️ 未移植功能清单见 docs/LEGACY_UI.md。
⚠️ tests/test_main_window_helpers.py 仍依赖本包。
"""
```

**不要加 `raise ImportError`** —— 会让现有测试失败。

### 5.2 给 `workers.py` 顶部加对照索引

在 `app/ui/workers.py` 顶部注明「本文件是 `app/shell/tasks.py` 的对照基准」，
并列出已移植 / 未移植的对应关系，避免新人以为还有 6 个 worker 要搬。

### 5.3 CI 里排除它

打包的时候 `excludes` 已经排掉了 `PySide6`，所以 `app/ui/` 不会进包。
但要确保**不要**在 `main_web.py` 的 import 链里意外引入它。
