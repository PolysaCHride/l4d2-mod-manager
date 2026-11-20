# L4D2 Mod Manager · 工程交接文档

> 写于 2026-11-20，前端重构第一期落地之后。
> **2026-11-20 第二轮更新**：补写发布流程、Node 侧契约测试、数据 format 文档，
> 并修掉 5 处新发现的假动作。改动集中在 §3.3 / §3.5 / §6.10-6.12 / §8 / §11。
> 面向：接管这个项目、但完全没有上下文的工程师团队。
>
> 本文档的目标不是「介绍项目」，而是**让你在最短时间内知道：什么东西能碰、什么东西碰了会炸、以及为什么当初这么做**。
> 项目里的设计文档质量不错，但工程文档基本为零 —— 这份文档补的是工程侧。

---

## 0. 先读这五条

如果你只有 3 分钟，读完这五条就够开工了。

1. **有两个入口，`main_web.py` 是未来。** `main.py`（PySide6）仍在发布，但不是主线。
2. **`app/core/` 是干净的，4234 行，与 UI 完全解耦。要改业务逻辑去那里，别在 UI 层改。**
3. **`app/webui/app.js` 是从演示页演化来的，混着真实现和假动作。** 本期已经修了主要的，但看到 `toast('已xxx')` 仍要确认它是否真的写了后端。
4. **不要执行 `scripts/patch_appjs.py`。** 它会用 1133 行的旧模板覆盖 1597 行的 `app.js`，静默丢掉几百行真实功能。
5. **`app/ui/`（5887 行旧 UI）暂时不要删。** 它是唯一的行为基准，且还有 6 个功能没移植过来。

---

## 1. 这个项目是什么

一个 Left 4 Dead 2 的模组管理器（Windows 桌面）。

**核心机制**：L4D2 通过 `left4dead2/addonlist.txt` 控制哪些 `.vpk` 启用。工具负责扫描 `addons/`、解析 VPK 元数据、分类、启停、导入压缩包、从创意工坊下载。

**一个特殊约束**：外观类模组（角色/特感/枪械/近战/医疗品/投掷）**同组互斥** —— 同一个 `(分类, 物品)` 只能启用一个。这是游戏机制决定的，不是产品设计选择。

---

## 2. 项目状态

### 2.1 技术栈

| 层 | 技术 | 状态 |
|---|---|---|
| 业务逻辑 | Python 3.14.7，纯标准库 + requests | **冻结**，不要动 |
| 旧 UI | PySide6 6.12.0 | 维护模式，仍在发布 |
| 新 UI | pywebview 6.2.1 + 系统 WebView2 | **主线**，本期完成第一期 |
| 打包 | PyInstaller 6.22.3 | 两套 spec 并存 |

### 2.2 为什么有两套 UI

原本是纯 PySide6。重做界面的动机是：QSS 写到 744 行已经难维护，设计稿（BLACKSITE 风格）用 Qt 实现成本高。

三条路线都实际做过原型并测了体积（见 `docs/redesign/proto/RESULTS.md`）：

| 路线 | 体积 | 结论 |
|---|---:|---|
| A. 继续用 PySide6 | 55 MB | 设计还原成本高 |
| B-1. PySide6 + QtWebEngine | **454 MB** | 否掉（`Qt6WebEngineCore.dll` 195MB 不可压缩） |
| **B-2. pywebview + 系统 WebView2** | **35 MB** | **采用** |

B-2 的代价是依赖系统 WebView2（Win10/11 自带）。

### 2.3 本期完成了什么

- `app/shell/` 桥接层，31 个 API 方法
- `app/webui/` 前端，1440×900 无边框窗口
- 主界面：6 分类、筛选、搜索、双击启停、Inspector 全套操作
- 长任务：扫描 / 导入压缩包 / 链接下载（真实进度 + 事件推送）
- 设置页、首次引导
- 打包 35 MB

### 2.4 本期没做

每一项的**结论与接入方案**见 `docs/LEGACY_UI.md` §二·五 —— 那里不再是「待定」。

| 项 | 说明 | 结论 |
|---|---|---|
| 工坊搜索 | 旧 UI 有 `SearchWorker`，新 UI 无 | 暂缓（需完整结果视图，非补缺） |
| 合集反查 | 旧 UI 的 `ParentCollectionWorker`（三路兜底），未移植 | 不做（主路径已覆盖；代码作知识资产保留） |
| 工坊订阅迁移 | 旧 UI 的 `MigrateWorker`，未移植 | **转正**，方案已给 |
| 便携 7zip 安装 | 旧 UI 的 `ArchiverInstallWorker`，未移植 | **不做**（发行包强制内嵌，场景不存在） |
| 预览图批量下载 | 旧 UI 的 `PreviewWorker`，未移植 | **转正**，方案已给（仅 3% 模组缺图） |
| **全量采纳 `adopt_all`** | 前端「整理」实际调 `rescan`，**语义不符** | **转正，最该先做** |
| 弹窗族美化 | 现在是 demo 期的简易版，未按 `states.html` 重做 | 未动 |
| 拖拽导入 | 页面接受 drop，但拿不到真实路径（WebView2 限制） | 未动 |
| 键盘快捷键 | 只有 Ctrl+K，Enter/Space 未做 | 未动 |

---

## 3. 五分钟跑起来

### 3.1 环境

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

`requirements.txt` 现在包含两套依赖：
- 旧 UI：`PySide6`、`requests`
- 新 UI：`pywebview`、`pythonnet`、`pywin32-ctypes`
- 打包：`pyinstaller`
- **必需**：`pillow`（见 6.3，不装会导致缩略图裂图）

**Python 版本**：当前 venv 是 3.14.7。建议 3.11+。

### 3.2 启动

```powershell
# 新界面（主线）
.\.venv\Scripts\python main_web.py

# 旧界面（对照用）
.\.venv\Scripts\python main.py
```

### 3.3 验证

```powershell
# 业务逻辑单测 + 前后端契约测试（36 个，用隔离临时目录，不碰真实游戏目录）
.\.venv\Scripts\python -X utf8 -m unittest discover -s tests -v

# 前端契约测试单独跑（23 项，Node 直跑，不需要 Python）
node tests\adapt_contract.js

# 桥接层自测（不需要窗口，用假 window 验证事件推送）
.\.venv\Scripts\python -X utf8 -m app.shell._selftest

# 前端语法
node --check app/webui/app.js
node --check app/webui/bridge.js

# 端到端（真实数据 + 真实桥接 + 真实界面）
.\.venv\Scripts\python -X utf8 docs\redesign\proto\e2e_check.py

# 启停写盘验证（先记原状态，toggle 两次回滚）
.\.venv\Scripts\python -X utf8 docs\redesign\proto\toggle_check.py
```

### 3.4 调试开关

`main_web.py` 支持这些环境变量：

| 变量 | 作用 |
|---|---|
| `L4D2_DEBUG=1` | 打开 DevTools |
| `L4D2_RAIL=weapon` | 启动后直接落到某个分类 |
| `L4D2_SHOT=<路径>` | 界面稳定后截图（BMP，不依赖 Pillow） |
| `L4D2_VERIFY=1` | 跑一轮 DOM 断言 |

诊断代码在 `app/shell/devtools.py`，入口只有 106 行是因为这部分被搬出去了。

**前端日志**：`data/webui.log`。打包版 `console=False`，控制台输出全部丢失，只有这个文件能看。

### 3.5 打包

```powershell
# 新栈（主线）—— 自动带 7-Zip、自动校验产物
.\build_release.ps1 -Target web

# 旧栈
.\build_release.ps1 -Target legacy

# 两套一起
.\build_release.ps1 -Target both
```

产出：
```
release/L4D2 Mod Manager-v<版本>-win64-web/        目录版
release/L4D2 Mod Manager-v<版本>-win64-web.zip    压缩包
release/L4D2 Mod Manager-v<版本>-win64/           旧栈（无 -web 后缀）
```

版本号**自动从 `packaging/version_info.txt` 读**，不用手工传。

⚠️ **两个 spec 的输出目录名不同**（`(WebUI)` 后缀），这是刻意改的 —— 原来两个都叫 `L4D2 Mod Manager`，先后构建会静默互相覆盖。

✅ **`build_release.ps1` 现在两套栈都支持**（本期修复）。原来只打旧 spec，新栈没有任何自动化发版路径。

#### 7-Zip 的双重保险

`third_party/7zip/` 被 `.gitignore` 忽略（不进仓库），干净 clone 后**目录不存在**。
原来两个 spec 都是 `if os.path.isdir(...)` 静默跳过 —— 打出来的包缺 `7z.exe`，
装到用户机器上「导入压缩包」全部失败，而且构建过程一句警告都没有。

现在：

| 位置 | 行为 |
|---|---|
| `build_release.ps1` → `Assert-7Zip` | 构建前先跑 `packaging/fetch_7zip.ps1` 补齐，缺文件直接 throw |
| `L4D2ModManagerWeb.spec` | 缺 `7z.exe`/`7z.dll`/`License.txt` 任一 → `SystemExit` 中止 |
| `build_release.ps1` → `Test-Package` | 打包后复查 `_internal/7zip/`，同时拒绝 `data/` 和文档文件进包 |

**已实测**：把 `third_party/7zip` 移走再构建，会报
`打包中止：缺少 7-Zip 组件 7z.exe, 7z.dll, License.txt` 并退出，
**不会**产出一个残缺的包。

> 单独跑 PyInstaller（不经过 build_release.ps1）时，spec 里那道检查仍然生效：
> ```powershell
> .\.venv\Scripts\python -m PyInstaller L4D2ModManagerWeb.spec --noconfirm
> ```
> 但**先自己确保** `third_party/7zip/` 有货，否则直接中止。

---

## 4. 代码地图

```
app/core/          4234 行  ★ 业务逻辑，冻结，与 UI 无关
├── library.py             模组库：扫描、启停、互斥、别名、分类、删除
├── store.py               JSON 持久化（library.json / settings.json）
├── importer.py            压缩包解析与写入
├── downloader.py          工坊下载
├── steam_api.py           Steam WebAPI 封装
├── classify.py            分类推断（含 CONFLICT_CATEGORIES）
├── vpk.py                 VPK 格式解析
├── addonlist.py           addonlist.txt 读写
├── paths.py               GamePaths（游戏目录派生路径）
├── app_paths.py           资源/数据目录
├── archiver.py            7-Zip 查找与调用
└── game.py                游戏运行检测、启动、打开工坊

app/shell/         1206 行  ★ 桥接层（本期新增）
├── api.py          705 行   31 个公开方法，Js API 对象
├── tasks.py        267 行   长任务的业务逻辑（纯函数）
├── jobs.py          97 行   线程 + 事件推送
├── devtools.py     216 行   截图/UI 断言（诊断用）
└── _selftest.py     97 行   无窗口自测

app/webui/         2802 行  ★ 前端（本期新增）
├── app.js         1597 行   主逻辑
├── app.css         763 行   样式
├── bridge.js       367 行   前后端桥 + mock 降级
├── events.js        75 行   事件总线
├── index.html             结构
└── tokens.css              语义色彩变量（4 套色板）

app/ui/            5887 行  ★ 旧 PySide6 UI（保留作基准）
├── main_window.py         主窗口
├── workers.py             长任务（QThread 版）
├── dialogs.py             各种对话框
├── components.py          卡片等组件
└── theme.py               744 行 QSS

main.py                    旧入口
main_web.py        106 行  新入口
```

---

## 5. 数据流

一条模组数据从磁盘到屏幕，经过 **三次字段改名**。这是理解前端的钥匙。

```
library.json
  │  {"file":"1127584577.vpk", "title":"...", "category":"地图",
  │   "mtime":1729087521, "preview":"E:\\...\\1127584577.jpg", "enabled":true}
  ↓  app/shell/api.py  _to_mod()
  │  {"file", "title", "alias", "category", "item", "size", "sizeText",
  │   "enabled", "workshop_id", "thumb"(data URI), "added"(秒), "addedText",
  │   "pinned", "mutex"}
  ↓  app/webui/bridge.js  原样透传
  ↓  app/webui/app.js  adapt()
  │  {"id", "name", "alias", "cat", "item", "size"(MB), "img",
  │   "enabled", "added"(天), "addedDate", "file", "ws", "mutex"}
  ↓  界面
```

### 字段对照表

| 后端 | 前端 | 说明 |
|---|---|---|
| `file` | `id` + `file` | 同一个值存了两份（历史遗留） |
| `title` | `name` | |
| `category` | `cat` | |
| `thumb` | `img` | 后端已转成 data URI |
| `workshop_id` | `ws` | |
| `size` (字节) | `size` (MB) | 前端除以 1048576 |
| `added` (epoch 秒) | `added` (**几天前**) | **同名不同义，最容易踩** |

### 为什么 thumb 是 data URI

页面是 `file://` 协议。图片在 E: 盘、页面在 D: 盘时，WebView2 会拦截跨盘 `file://` 资源 —— 表现为**全部裂图**。所以后端把预览图读出来转成 base64（超过 400KB 先用 Pillow 压到 320×180）。

代价：`bootstrap()` 一次要传 ~5MB 的 base64。这是当前最大的性能开销。

---

## 6. 认知陷阱清单

这一节是本文档的核心。**每一条都是真实踩过的坑**，不是理论。

### 6.1 ⚠️ `app.js` 里真假行为混杂

`app/webui/app.js` 从演示页 `demo.js` 演化而来。演示期有大量「只弹 toast、不写后端」的假动作。本期修了主要的，但**判断某个操作是否真的生效，必须去 `bridge.js` 数调用**，不能看 UI 表现。

已经修好的：启停、别名、删除、打开文件夹、扫描、设置页显示。
**第二轮又修了 5 处**（启动游戏 / 打开工坊页 / 打开 addons 目录 / 排序 / 修改分类），
逐条对照见 §6.11。

**仍需注意**：任何 `toast('已...')` 后面有没有 `await window.bridge.xxx()`。

**验证方式**：改完之后，直接去看 `data/library.json` 或 `addonlist.txt` 有没有变。
本轮修完的每一处都做了真实写盘验证 + 回滚（`addonlist.txt` 的 `"1"`/`"0"`、
`library.json` 的 `alias`/`category`/`pinned`）。

### 6.2 ⚠️ `job.done` 谁发？—— 本期已统一

原来有三种约定并存（`start_scan` 不发、`download` 自己发、其余调用方发）。现已统一为：**`tasks.py` 只返回结果，`api.py` 负责发 `job.done`**。

如果你新增长任务，照 `start_download` 的写法：

```python
def run(job):
    result = tasks.your_task(job, ...)
    job.done(result or {})
job_id = self._runner.start("your-kind", run)
```

**不发 `job.done` 的后果**：前端 `runJob` 的 `onDone` 永不触发，状态栏永久停在「扫描中」，按钮永久禁用。

### 6.3 ⚠️ Pillow 是必需依赖，不是可选

`api.py` 的 `_thumb_url` 会压缩超过 400KB 的预览图。没有 Pillow 时：

- 旧行为：截断读前 400KB → **坏 JPEG → 浏览器裂图**
- 实测影响：200 个模组里 **72 个**会裂
- 且 `bootstrap` 要传 **54MB** base64

现在没有 Pillow 时会**跳过并返回空串**（前端画占位），不会给坏图。但正确做法是装 Pillow。

**不要把 `PIL` 加回 spec 的 `excludes`。**

### 6.4 ⚠️ `collection_children` 返回 `list[str]`，不是 `list[dict]`

`app/core/steam_api.py` 的 `collection_children(detail)` 返回的是 **id 字符串列表**。

本期曾在 `tasks.py` 里写成 `c.get("publishedfileid")`，导致**任何工坊合集链接都会崩**（`'str' object has no attribute 'get'`），而且被 `_err(exc)` 吞成一句模糊报错。

已修。如果你要碰合集相关代码，记住这个类型。

### 6.5 ⚠️ 互斥类别有 4 份定义

```
app/core/classify.py:25      CONFLICT_CATEGORIES   ← 真正的源头
app/shell/api.py:33          MUTEX_CATS            ← 副本
app/ui/main_window.py:48     MUTEX_CATS            ← 副本
app/webui/app.js:106         MUTEX_CATEGORIES      ← 副本
```

**当前四处取值完全一致**，但改一处忘三处 → 后端会静默停用用户的模组，而前端不弹确认框。这种 bug 极难复现。

真正该做的是从 core 生成一份注入前端（`bootstrap` 里加 `enums` 字段）。本期没做。

### 6.6 ⚠️ `app/ui/` 不要急着删

它看起来是 5887 行的死代码，但：

1. **它是唯一的行为基准。** `tasks.py` 是从 `workers.py` 重写的，验证正确性只能对比着看。本期发现的「进度算法抄对了、`cleanup_staged` 漏抄了、合集类型传错」全部来自对比。
2. **`tests/test_main_window_helpers.py` 直接 import 它。**
3. **还有 6 个功能没移植**（见 2.4），`ParentCollectionWorker` 那种三路兜底是纯领域知识，删了就永久丢失。

**删它的时机**：等 2.4 那 6 项都有明确结论（移植或明确不做）之后。

### 6.7 ⚠️ 两个 spec 输出同名（已修）

原来两个 spec 都产出 `dist/L4D2 Mod Manager/`，先后构建会静默覆盖，你无法分辨 dist 里是哪个版本。

现在 Web 版叫 `L4D2 Mod Manager (WebUI)`。

### 6.8 ⚠️ 无边框窗口的拖动机制

`pywebview` 的 `easy_drag` **不是**「整页可拖」，它只认 `.pywebview-drag-region` 这个选择器（`webview/settings.py` 的 `DRAG_REGION_SELECTOR`）。

所以 `index.html` 里顶栏是：

```html
<header class="topbar pywebview-drag-region">
```

**如果你想改拖动区域，改这个类名，不要指望 pywebview 提供别的接口。**

### 6.9 ⚠️ `evaluate_js` 不等待 Promise

```python
# 这样拿到的是 {}，不是结果
window.evaluate_js("(async () => { return await x(); })()")

# 正确做法：写全局变量再轮询
window.evaluate_js("window.__r = null; (async()=>{ window.__r = await x(); })();")
for _ in range(30):
    time.sleep(0.3)
    r = window.evaluate_js("window.__r")
```

`app/shell/devtools.py` 里的 `verify_ui` 和 `selftest` 都是这个模式。

### 6.10 ⚠️ 后端改名必须同步前端 `adapt()`

`_to_mod()` 和 `adapt()` 是一对。改了左边不改右边，前端拿到 `undefined`，然后被 `|| ''` / `|| 0` 兜底 —— **界面照常渲染，只是数据错了**，不会报任何错。

这是最危险的一类问题：静默降级。

**现在有两层保护**（本期补齐）：

| 层 | 文件 | 锁什么 |
|---|---|---|
| Python | `tests/test_webui_contract.py` | `_to_mod` 的**输出字段集** |
| Node | `tests/adapt_contract.js` | `adapt` 的**输入字段名** + 单位换算 + 枚举一致性 |

跑 `python -m unittest discover -s tests` 会同时跑两边
（`tests/test_adapt_contract_js.py` 是桥；没装 node 时跳过而不是失败）。

### 6.11 ⚠️ 假动作清单（本期又找出 5 处）

`app.js` 里有一类「看起来有功能、实际只弹提示」的代码。本期审计
31 个 API 方法 × 前端调用点，又找出 5 处，全部已接线：

| 位置 | 原来的行为 | 现在 |
|---|---|---|
| `#launchBtn` | `infoDialog('演示环境不会真的启动 L4D2')` | `bridge.launch_game()` → `steam://rungameid/550` |
| `#insWorkshop` | `infoDialog('演示环境不会真的打开浏览器')` | `bridge.open_workshop(id)` → `steam://url/CommunityFilePage/<id>` |
| `#statusPath` | `toast('已在资源管理器中打开 addons 目录')` | `bridge.open_path(addonsDir)` → 真的打开 |
| `#sortBtn` | 只给「最近添加」一个选项，选了等于没选 | 三档循环（最近添加 / 名称 / 大小），都真的生效 |
| `修改分类` | `infoDialog('实际实现会打开分类选择对话框')` | `bridge.set_category()`，落盘且置 `pinned` |

**验证方法**：判断真假只能去 `bridge.js` 数调用，不能看 UI 表现。
本轮改完每个都跑过真实写盘（`addonlist.txt` 的 `"1"`/`"0"`、
`library.json` 的 `alias`/`category`/`pinned`），并做了回滚。

**第三轮又修了一处（最隐蔽的）**：「刷新」和「整理」两个按钮
**调的是同一个 `runScan()`**，都走 `rescan` —— 按钮文案不同，行为完全一样。
而「整理」承诺的是 `adopt_all`（会把子目录 / workshop 里的 vpk 移到顶层）。
现在 `#tidyBtn` 和首屏「开始整理」都走 `start_adopt`，会移动文件所以带确认框；
`#refreshBtn` 保持只读的 `rescan`。

### 6.12 ⚠️ `game.unknown` 必须被前端消费

`api.bootstrap()` 在 `is_l4d2_running()` 抛异常时返回 `game: {running: false, unknown: true}`。
**`unknown=true` 不等于「没在运行」** —— 它表示「不知道」。

原来的前端只读 `res.game.running`，`unknown` 完全没用上 ——
等于检测失败时会**放行写入**，而游戏运行中写 `addonlist.txt` 会失败或损坏。

现在：

```js
state.gameUnknown = !!(res.game && res.game.unknown);
// 所有写入前都走这一个闸门
function writeBlockedOf(running, unknown) {
  if (running) return '游戏运行时无法修改模组配置，请先退出游戏。';
  if (unknown) return '无法确认游戏是否正在运行，为避免损坏 addonlist.txt，已暂停写入。…';
  return '';
}
```

覆盖点：`toggleMod` / `commitImport` / `startDownload` 三处。
顶栏状态灯的 `unknown` 态用警告色（`--warning`）区别于正常的灰点。

**注意**：`writeBlockedOf` 是纯函数并已导出到 Node 契约测试
（`tests/adapt_contract.js` 里有三条断言钉住它），改判定逻辑会立刻测试失败。

### 6.13 ⚠️ `adopt_all` 的 progress 第三参是「名字」，不是「总数」

本轮接 `start_adopt` 时踩到的，**会直接崩**：

```python
# app/core/library.py 里 progress 的实际调用
progress("迁移 workshop 订阅项…", 0, 0)                          # 664 行
progress("移动子目录 mod…", i + 1, os.path.basename(parts[0]))   # 699 行
progress("登记顶层 mod…", i + 1, name)                           # 731 行
                                  ↑ 第三参是当前项的名字（字符串）
```

而 `Job.progress(label, done, total)` 要做 `int(done * 100 / total)` ——
把名字当 `total` 传就是：

```
TypeError: unsupported operand type(s) for /: 'int' and 'str'
```

**两种签名都不能直接适配**：664 行少传一个参数，699/731 行第三参是字符串。
`tasks.adopt_all` 的解法是自己先数一遍工作量当分母、忽略第三参：

```python
def progress(text, done=0, current=""):
    state["done"] = max(state["done"], int(done or 0))
    job.progress(text, min(state["done"], total_work), total_work, phase="adopt")
```

同时把 `library.py:664` 补成 `progress(..., 0, 0)`，消掉「少传参数」这一类。

**新增长任务时**：先确认 core 那个函数到底按什么签名调 `progress`，
不要假设是 `(text, i, n)`。

---

## 7. 那些看起来奇怪的设计决定

### 7.1 为什么扫描是只读的

`library.rescan()` 只读 `addons/` 目录重建记录，**不动 `addonlist.txt`**。启停状态从 `addonlist.txt` 同步过来。

这是刻意的：用户可能在游戏内或别的工具里改过状态，扫描应该尊重磁盘现状而不是覆盖它。

### 7.2 为什么游戏运行时禁止写入

`addonlist.txt` 被游戏独占。运行中写入会失败或损坏。所以所有写操作前都要检查 `state.gameRunning`。

⚠️ `api.py` 里 `is_l4d2_running()` 失败时被 `except: pass` 吞成 `False` —— 意味着检测失败时会**放行写入**。这是个已知隐患，见 9.2。

### 7.3 为什么 Inspector 的同组切换有确认框，而双击没有

都有。两处走同一套逻辑（本期统一了）。原则是：**启用一个外观模组时，如果有同组已启用的，先告诉用户会被顶掉。**

### 7.4 为什么「入库时间」用 `added_at` 而不是 `mtime`

`mtime` 是文件修改时间 —— 用户移动文件、重新下载都会变。
`added_at` 是首次登记时间 —— 这才是「入库时间」。

⚠️ 但 `app/core/library.py:141` 每次重扫都会 `new_mod_record()`，`added_at` 被重置为 `now`，`if old:` 分支只保留 `alias`/`enabled`/`pinned`，**不保留 `added_at`**。

所以这个字段目前在**每次重扫后都会丢失**。这是 core 的 bug，但 core 是冻结的。`_to_mod` 已经做了 `added_at or mtime` 的兜底。

**如果哪天允许改 core，第一件该做的就是保住 `added_at`。**

### 7.5 为什么缩略图是 base64 而不是文件路径

见第 5 节。跨盘 `file://` 被 WebView2 拦截。

代价是 `bootstrap` 慢、内存占用高。如果以后要优化，方向是：把缩略图缓存到 `_internal` 同盘目录，或者用 pywebview 的本地 HTTP server。

### 7.6 为什么前端有 mock 降级

`bridge.js` 在检测不到 `window.pywebview` 时会走内存 mock。这样**直接双击 `index.html` 用浏览器打开也能看界面**，调样式很快。

⚠️ 但 mock 数据里 `added` 的单位是毫秒，真实后端是秒 —— 导致浏览器模式下所有卡片都显示「今天」。这个不一致本期没修（mock 只为调样式，本就不该拿来验证数据逻辑）。

---

## 8. 待办与建议

### 8.1 P0（交接前必须知道）

| # | 事项 | 状态 |
|---|---|---|
| 1 | ~~`app/shell/` 未提交，`git clean` 即销毁~~ | ✅ 已提交 `caf8283` |
| 2 | ~~`excludes` 排掉 PIL 导致裂图~~ | ✅ 已修 |
| 3 | ~~合集子项类型错误~~ | ✅ 已修 |
| 4 | ~~`commit_import` 不清理临时目录~~ | ✅ 已修 |
| 5 | ~~Web 包缺 7-Zip~~ | ✅ 已修 |
| 6 | ~~`build_release.ps1` 不打新 spec~~ | ✅ **本期修复**，见 §3.5 |
| 7 | ~~`launch_game` / `open_workshop` / `statusPath` / `sortBtn` / 分类修改 是假动作~~ | ✅ **本期修复**，见 §6.11 |

### 8.2 P1（决定改得对不对）

| # | 事项 | 状态 |
|---|---|---|
| 8 | **契约测试（Python 侧）** | ✅ 已有 11 条（`tests/test_webui_contract.py`） |
| 9 | ~~**契约测试（Node 侧）**~~ | ✅ **本期补齐**：`tests/adapt_contract.js` 23 项 + `tests/test_adapt_contract_js.py` 挂进 unittest |
| 10 | ~~枚举一致性测试~~ | ✅ 已有 + 本期扩到 `CATEGORY_OPTIONS` / `RAIL_DEFS` 覆盖检查 |
| 11 | ~~`data/library.json` schema 文档~~ | ✅ **本期补齐**：`docs/DATA_SCHEMA.md` |
| 12 | ~~6 个未移植功能的清单~~ | ✅ **本期补齐**：`docs/LEGACY_UI.md` §二·五，逐条给结论 |
| 13 | ~~`is_l4d2_running` 失败时前端不消费 `game.unknown`~~ | ✅ **本期修复**，见 §6.12 |

### 8.3 P2（整洁）

| # | 事项 | 状态 |
|---|---|---|
| 14 | `_fmt_size` 有三份实现（api.py / tasks.py / ui/util.py） | ⬜ 未动（core 冻结，只能收中间层两份） |
| 15 | `spec` 的 `hiddenimports` 18 项里 15 项多余 | ⬜ 未动 |
| 16 | `app/webui/assets/mods/*.webp` 6 张图只用于 mock | ⬜ 未动 |
| 17 | `app.js` 里的 `DEMO_MODS`（29 行演示数据）与 mock 重复 | ⬜ 未动，可随 P2 一起清 |
| 18 | `chapters` 是无人读写的遗留字段（197/200 条带它） | ⬜ 已记录进 `DATA_SCHEMA.md` §2.3 |

### 8.4 对齐审查（2026-11-20 第三轮）的落地情况

完整审查见 `docs/ALIGNMENT_AUDIT.md`。用户裁定后已落地 8 项：

| 项 | 结果 |
|---|---|
| A-2 工坊搜索 | ✅ 确认丢弃，`SearchWorker` 死代码已删 |
| B-1/D 全量采纳 | ✅ 新增 `start_adopt`；「整理」不再等于「刷新」 |
| B-2 订阅迁移 | ✅ 随 `adopt_all` 自动生效，无需单独入口 |
| C 分类置灰 | ✅ core 加 `auto_category`/`auto_item`；详情栏置灰展示「识别为…」 |
| E-2 快捷键 | ✅ 收敛为 F5 / Ctrl+K（+Ctrl+F）/ Esc；卡片 Space 启停已移除 |
| E-3 预览图兜底 | ✅ 接上 `assets/wiki` 70 张图；`hasThumb` 194 → 200 |

**仍待做**：

| 项 | 说明 |
|---|---|
| A-1 合集 UI | 数据层已修（`collection` 已透出），UI 按用户要求**暂时搁置**。定位已确认：合集 = 纯展示分组，不参与互斥 |
| B-3 预览图真下载 | 用户裁定推后；注意这是**首次实现**不是移植（`PreviewWorker` 从未被实例化） |
| B-4 合集反查 | 随合集 UI 一起，暂不移植 |

### 8.5 第四轮（分类器修复 + 组级互斥开关）

| 项 | 结果 |
|---|---|
| 框架/前置包误分类 | ✅ 新增 `_looks_like_framework`：`xdReanimsBase`、`KSEP Platform` 从「特感/角色」改为「杂项/前置框架」 |
| 地图多部件被打散 | ✅ 新增「addoninfo 明示 Campaign/Map → 归地图」前置规则：4 个部件修回地图，4 个地图家族恢复完整 |
| `CLF_VERSION` | ✅ 14 → **15**，真实库 200/200 已重扫到 15 |
| 组级互斥开关 | ✅ 详情页「同组」面板新增拨动开关，按 `(分类, 物品)` 关闭互斥；状态存 `settings.json` 的 `mutex_off_groups` |

**已知边界（无法自动修）**：`The Parish Halloween` 的 2 个 models/materials 部件
既无 addoninfo、也无 mission、也无 bsp，单看内容无法判断属于哪张地图，
分类器只能给「材质特效」。这类请让用户手工改分类（会自动置 `pinned`）。

> 分类规则回归测试见 `tests/test_classify_rules.py`（15 项），
> 包含「名叫 base 但只改一个角色的皮肤仍是角色」这类误伤防护。

---

## 9. 已知的坑（实现细节）

### 9.1 `_serializable` —— 已经不需要了

曾遇到过：pywebview 反射 `js_api` 对象时递归展开 WebView2 的 COM 属性链，导致整个 API 注册失败，前端拿不到任何方法。

当时的解法是在类上加 `_serializable = False` —— **这反而更糟，会让整个 Api 对象不被注册**。

**真正的原因**：pywebview 的 `get_functions` 在 `getattr` 之前就跳过 `name.startswith('_')` 的属性。所以只要把 `window`/`store`/`library` 都改成下划线前缀就够了，**不需要 `_serializable`**。

代码里现在是 `_window` / `_store` / `_library`，正确。**不要加回 `_serializable`。**

### 9.2 `_ensure()` 的懒加载

`Api` 不在 `__init__` 里读盘（那会让 `create_window` 卡住），而是第一次调用时懒加载，用双检锁保护。

⚠️ **重建路径有隐患**：`save_setting('game_dir')` 时会把 `_store/_library` 置 None 再 `_ensure()`。如果此时后台线程正持有旧 `Library`，会出现两个 Library 操作同一批 json。

当前没有实际触发（改目录时通常没有任务在跑），但这是个雷。

### 9.3 `evaluate_js` 从后台线程调用

`_emit` 会被 job 线程调用。pywebview 内部用 `Control.Invoke` marshal 到 UI 线程，**设计上是允许的**，但 `semaphore.acquire()` 没有超时。

如果 UI 线程正在弹模态文件选择框，后台 job 的进度推送会阻塞排队。

### 9.4 `Store` 没有锁

`store.mods()` 直接返回内部 dict 引用。`_to_mod` 遍历它的同时如果另一个线程在 `upsert_mod`，会 `RuntimeError: dictionary changed size during iteration`。

**目前靠「同一时间只有一个任务在跑」避免**。如果以后允许并发任务，必须先加锁。

---

## 10. 交接检查清单

接手第一周建议按这个顺序做：

- [ ] 读本文档第 0、5、6 节
- [ ] `pip install -r requirements.txt`，跑起 `main_web.py`
- [ ] 跑 `python -m unittest discover -s tests -v`，确认 **36 个全绿**
- [ ] 跑 `node tests/adapt_contract.js`，确认 23 项全过
- [ ] 跑 `python -X utf8 docs/redesign/proto/e2e_check.py`，确认 `mode: live`
- [ ] 打开一次 DevTools（`L4D2_DEBUG=1`），看有没有 console 错误
- [ ] 双击一个模组，**去 `addonlist.txt` 确认真的写了 `0`/`1`**
- [ ] 点顶栏的「启动」，确认真的拉起了 Steam（这是本轮修好的 5 处之一）
- [ ] 跑一次 `.\build_release.ps1 -Target web`，确认
      `release/L4D2 Mod Manager-v*-win64-web/_internal/7zip/7z.exe` 存在
- [ ] 把 `third_party/7zip` 临时移走再构建，确认**构建失败**而不是产出残缺包
- [ ] 读 `docs/DATA_SCHEMA.md`（改分类规则前必读 `clfv` 那节）
- [ ] 读 `docs/redesign/proto/RESULTS.md`（为什么选 pywebview）
- [ ] 读 `docs/redesign/final/README.md`（24 条已确认的设计决定）
- [ ] 决定 `app/ui/` 的去留（先读 `docs/LEGACY_UI.md` §二·五 的六项结论）

---

## 11. 文档索引

**必读**：
- `docs/ALIGNMENT_AUDIT.md` —— 旧后端/旧 UI ↔ 新前端的 12 项对齐审查 + 裁定结果
- `docs/DATA_SCHEMA.md` —— `data/` 数据格式、`clfv` 机制、`auto_category`、哪些字段能手改
- `docs/LEGACY_UI.md` —— 旧 UI 六项未移植功能的**逐条结论**（§二·五）
- `docs/redesign/proto/RESULTS.md` —— 三条路线的实测报告，解释为什么是现在这个架构
- `docs/redesign/final/README.md` —— 24 条已确认的设计决定，可当验收清单
- `docs/redesign/final/DESIGN_PRINCIPLES.md` —— 四条硬规则

**有用但要小心**：
- `docs/redesign/final/FRONTEND_PLAN.md` —— §五推荐的是 **QtWebEngine，已被实测否掉**。§一/§二的现状分析仍然准确
- `docs/redesign/final/WEBUI_DELIVERY.md` —— 「踩过的坑」和「已知限制」两节很有价值，但里面的行数/方法数已过期
- `docs/redesign/final/WEBUI_SLICE1.md` —— 第一块落地的记录，部分内容已被 DELIVERY 取代

**设计参考**：
- `docs/redesign/final/BLACKSITE_DECOMPOSITION.md`（513 行，逐区拆解，但 §1 的尺寸表已过时）
- `docs/redesign/final/03-FILTERPANEL.md` / `04-06-WORKSPACE.md` / `08-STATUSBAR.md`
- `docs/redesign/final/states.html` —— 26 种状态的定稿设计

**注意矛盾**：
- 体积预算：`REQUIREMENTS_LOCK.md` 写 100MB，`RESULTS.md` 写 300MB。实测 35MB，都没超
- 断点：设计验收是 1100，`app.css` 实现是 1180
- 尺寸：`BLACKSITE_DECOMPOSITION.md` §1 写 TitleBar 56 / StatusBar 30，实际是 54 / 28

---

## 12. 一句话总结

**业务逻辑是干净的，设计文档是好懂的，脏的是中间那层 —— 从演示页长出来、边调试边打补丁的前端，以及从来没被写下来的「怎么跑、怎么测、怎么发」。**

已清理的：写操作接真实后端、危险脚本加警告、垃圾文件清理、291MB 缓存删除、基线提交。
本期（2026-11-20 第二轮）又推进了三件系统性工作：

| 项 | 结果 |
|---|---|
| **发布流程** | `build_release.ps1` 支持新栈；7-Zip 三重校验；缺组件构建**直接失败**而不是静默产出残缺包 |
| **契约保护** | Node 侧 23 项 `adapt()` 契约 + 挂进 unittest；前后端字段契约现在两层都有断言 |
| **假动作** | 又找出并修复 5 处；`game.unknown` 真正接到写入闸门上 |

还剩的（按建议顺序）：

1. **`adopt_all` 接线**（`LEGACY_UI.md` §2.6）—— 前端「整理」按钮承诺的是
   `adopt_all`，实际调的是 `rescan`。这是**语义不符**，不是缺功能。
2. 预览图批量下载 / 订阅迁移（方案已给，见 §2.2 / §2.4）
3. P2 整洁项（`_fmt_size` 三份、`hiddenimports` 15 项多余）

**判断改得对不对，现在有三条独立命令**，不需要打开界面：
`unittest`（36 项）、`node tests/adapt_contract.js`（23 项）、`e2e_check.py`（真实数据）。
