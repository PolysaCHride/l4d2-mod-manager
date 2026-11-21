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
| 新 UI 状态 | ❌ 没移植（**2026-11-21 实测后确认不做**：200 条里 194 条自带图、
5 条走 wiki 兜底、0 条全黑，补下载只值 6 张图，见 `docs/ALIGNMENT_AUDIT.md` B-3） |

### 2.3 **反查物品所属合集**

| | |
|---|---|
| 旧实现 | `app/ui/workers.py:311` `ParentCollectionWorker` |
| 新 UI 状态 | ❌ 没移植（合集**展示**已做，见 HANDOFF §8.8；反查仍未做） |

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

## 二·五、六项功能的结论（2026-11-20 定）

每一项给出**处置**而不是「待定」。处置有四档，各自含义写死：

| 档位 | 含义 | 对删除 `app/ui/` 的影响 |
|---|---|---|
| **已移植** | 新 UI 有等价能力并已接线 | 不阻塞 |
| **不做** | 产品决定放弃，且理由成立 | 不阻塞 |
| **暂缓** | 明确要做，但不在本期；core 能力保留 | **阻塞**（需求还活着） |
| **转正** | 已确认 core 里有、只差前端入口，给出接入方案 | **阻塞**（工作量已知） |

### 2.1 工坊在线搜索 → **不做（已删代码）**

- 旧实现：`app/ui/workers.py:275` `SearchWorker`
- ⚠️ **更正（2026-11-20 复核）**：`SearchWorker` 在旧 UI 里**从未被实例化** ——
  旧 UI 的搜索一直是**本地过滤**（`main_window.py:1192 _filtered_mods`），
  按 title/alias/category/item/file/tags 匹配，根本不联网。
  所以这个 Worker 是纯死代码。
- 裁定：**确认丢弃工坊在线搜索**。`SearchWorker` 已从 `app/ui/workers.py` 删除。
- core 的 `steam_api.search_workshop()` **保留**：core 冻结期不动，
  且 `ParentCollectionWorker` 的反查逻辑理论上会用它。
- **阻塞删除**：否

### 2.2 预览图批量下载 → **转正（但要先知道它不是移植）**

- 旧实现：`app/ui/workers.py:298` `PreviewWorker`
- ⚠️ **更正（2026-11-20 复核）**：`PreviewWorker` 在旧 UI 里**从未被实例化** ——
  它是死代码，旧 UI 根本没有「下载预览图」的入口。
  所以这一项**不是移植，而是首次实现**，需要自己设计：
  下载的图存哪（`data/previews/`？）、文件名规则、怎么回写 `preview` 字段。
- core 能力：`steam_api.fetch_preview_bytes(url)` 只能拿字节，不管落盘。
- **当前先做的是兜底而不是下载**：`assets/wiki/` 有 70 张现成占位图，
  已接进新栈（E-3），`hasThumb` 从 194 → **200**，缺图的 6 个模组都有图了。
- 真正「从工坊下载真图」仍待实现。
- **阻塞删除**：否（已有兜底；下载属增强）

### 2.3 反查物品所属合集 → **暂缓**

- 旧实现：`app/ui/workers.py:311-386` `ParentCollectionWorker`，三路兜底
- 新 UI 现状：无入口
- 为什么暂缓：三路兜底的目的，是补上「用户只给了单个物品、
  但它属于某个合集」这个场景。而新 UI 的下载流程**直接支持粘贴合集链接**
  （`fetch_details` 会经 `collection_children` 展开），主路径已覆盖。
- 但这是**纯领域知识**（Steam 没有官方反查接口），删掉就永久丢失。
  代码必须留在 `workers.py` 里，并保留那三段注释。
- **阻塞删除**：否（不做，但代码作为知识资产保留）

### 2.4 工坊订阅迁移 → **转正**

- 旧实现：`app/ui/workers.py:409` `MigrateWorker`
- core 能力：`library.migrate_from_workshop(...)` **完好**，
  且 `adopt_all()` 内部也会走迁移逻辑（`library.py:630`）
- 新 UI 现状：无入口。但**已有 5 条 `source="migrate"` 的真实记录**，
  说明这个能力被用过
- 接入方案：设置页加一个「迁移工坊订阅」按钮 → 直接调 `start_scan` 之外的
  一个 `start_migrate`，内部走 `tasks.migrate`（需新增）→ `library.migrate_from_workshop`
- **阻塞删除**：是

### 2.5 便携 7-Zip 安装 → **不做**

- 旧实现：`app/ui/workers.py:77` `ArchiverInstallWorker`
- 新 UI 现状：找不到解压器时报错
- **为什么不做**：发行的包里已强制内嵌 `_internal/7zip/`，
  且 `build_release.ps1` + `L4D2ModManagerWeb.spec` 双重校验
  缺 7z.exe 就让构建失败（见本期 P0 修复）。
  也就是说「用户机器没有 7-Zip」这个场景在正式发行版里**不存在**。
  为一个不可能发生的场景维护一套下载安装器不划算。
- 兜底：`archiver.find_archiver()` 仍会依次尝试
  bundled → remembered → installed → PATH，
  用户在设置里手工指定 `archiver_path` 也能用
- **阻塞删除**：否

### 2.6 全量采纳（adopt_all）→ **转正（本项最重要）**

**先纠正一个语义不符 —— 已实测确认：**

```
前端「整理」按钮 (#tidyBtn) 和首屏「开始整理」(#onboardStart)
    → runScan() → bridge.start_scan()
    → api.start_scan() → tasks.scan() → library.rescan()      ← 实际是 rescan
```

而 `rescan()` 与 `adopt_all()` **不是一回事**：

| | `rescan()` | `adopt_all()` |
|---|---|---|
| 重建已有记录 | ✅ | ✅ |
| **顶层未登记的 vpk** | ❌ 不管 | ✅ 补记进库 + addonlist 记 `"1"` |
| **子目录里的 vpk**（非 workshop） | ❌ 不管 | ✅ 整组移到顶层，记 `"0"`（禁用） |
| **`workshop/` 子目录** | ❌ 不管 | ✅ 走迁移，保留启用状态 |

**按钮文案「整理」承诺的是 `adopt_all` 的行为，实际做的是 `rescan`。**
用户把 vpk 丢进 `addons/some_subdir/` 后点「整理」，
会发现这些模组**根本没出现** —— 因为游戏本身也不扫描子目录。

- 结论：**要接 `adopt_all`**，并且把两个操作分开：
  - 「刷新」→ `start_scan`（rescan，快，只同步状态）
  - 「整理」→ `start_adopt`（adopt_all，慢，会移动文件，需确认框）
- 注意：`adopt_all` 会**真的移动文件**（`library.py:693` `shutil.move`），
  已实测确认其行为：
  - `workshop/` 子目录 → 全部移出纳管（保留启用状态）
  - 其他子目录 → 整组移到顶层，**默认禁用**（记 `"0"`，因为游戏本就不扫子目录）
  - 目标重名时自动加 ` (2)` ` (3)` 后缀，不会覆盖
  - 移动前会先把整组目标路径都确认一遍，再统一移（避免移一半）
  所以必须：① 游戏未运行时才允许（`writeBlocked()` 已有闸门）
  ② 执行前弹确认框说明「子目录里的 vpk 会被移到顶层」
  ③ 结果里 `moved`/`errors` 要如实展示，不能只报成功数
- 接入方案：
  ```python
  def start_adopt(self):
      def run(job):
          stats = library.adopt_all(progress=...)
          self._emit("mods.changed", {"mods": self._all_mods()})
          job.done(stats or {})
      return _ok(job_id=self._runner.start("adopt", run))
  ```
- **阻塞删除**：是（**这是六项里最该先做的**）

---

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

**明确的、可执行的标准**（按 §二·五 的结论更新）：

```markdown
- [x] 2.1 工坊搜索      → **不做**（确认丢弃；SearchWorker 已删，旧 UI 搜索本是本地过滤）
- [ ] 2.2 预览图下载    → **转正**（是首次实现不是移植；E-3 wiki 兜底已做，真下载待做）
- [x] 2.3 合集反查      → **不做**（合集**展示**已在 2026-11-21 落地，见 HANDOFF §8.8；
                           反查这份领域知识仍保留在 `workers.py`）
- [ ] 2.4 订阅迁移      → **转正**（已随 adopt_all 自动生效，无需单独入口）
- [x] 2.5 便携 7zip     → **不做**（发行包强制内嵌 7-Zip）
- [ ] 2.6 全量采纳      → **已完成**（新增 start_adopt，「整理」与「刷新」已分离）
- [ ] tests/test_main_window_helpers.py 已改写为不依赖 app/ui/
```

> 「结论已给」≠「可以删」。上表中 2.1/2.2/2.4/2.6 仍是**活需求**，
> 它们的存在依然构成对 `app/ui/` 的依赖理由（作为行为基准）。
> 只有当 2.2 / 2.4 / 2.6 **真正移植进新 UI**、
> 2.1 有明确产品结论之后，`app/ui/` 才可以动。

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

---

## 六、本期（2026-11-20）对本文档的更新

| 变更 | 说明 |
|---|---|
| 补 §二·五 | 六项功能逐条给结论，不再「待定」 |
| 确认 2.6 语义不符 | 实测：`#tidyBtn` / `#onboardStart` 走的是 `rescan`，不是 `adopt_all` |
| 修正 2.5 的理由 | 不是「没时间做」，而是发行包强制内嵌 7-Zip 后该场景不存在 |
| 校正删除清单 | 区分「已给结论」与「可以删除」，两者不是一回事 |

> 本期**没有**移植任何一项到新 UI。本文档只把「不确定」变成「确定」，
> 并给出每一项的接入方案，让后续实现不用重新调研。
