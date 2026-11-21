# L4D2 Mod Manager · 工程交接文档

> 写于 2026-11-20，前端重构第一期落地之后。
> **2026-11-20 第二轮更新**：补写发布流程、Node 侧契约测试、数据 format 文档，
> 并修掉 5 处新发现的假动作。改动集中在 §3.3 / §3.5 / §6.10-6.12 / §8 / §11。
> **2026-11-21 第五、六轮更新**：互斥机制整体拆除（§6.5 重写、§8.6）；
> 打包加冒烟测试、`.ps1` 补 BOM（§3.5）；P2 整洁 + B-3 实测结论（§8.3 / §8.7）。
> **2026-11-21 第七轮**：合集展示（A-1）落地在详情「更多」里，见 §8.8。
> 面向：接管这个项目、但完全没有上下文的工程师团队。
>
> 本文档的目标不是「介绍项目」，而是**让你在最短时间内知道：什么东西能碰、什么东西碰了会炸、以及为什么当初这么做**。
> 项目里的设计文档质量不错，但工程文档基本为零 —— 这份文档补的是工程侧。

---

## 0. 先读这五条

如果你只有 3 分钟，读完这五条就够开工了。

1. **只有一个发布入口：`main_web.py`。** `main.py`（PySide6 旧界面）已于 2026-11-21 归档，不再发版。
2. **`app/core/` 是干净的，4234 行，与 UI 完全解耦。要改业务逻辑去那里，别在 UI 层改。**
3. **`app/webui/app.js` 是从演示页演化来的，混着真实现和假动作。** 本期已经修了主要的，但看到 `toast('已xxx')` 仍要确认它是否真的写了后端。
4. **不要执行 `scripts/patch_appjs.py`。** 它会用 1133 行的旧模板覆盖 1597 行的 `app.js`，静默丢掉几百行真实功能。
5. **`app/ui/`（5887 行旧 UI）已归档：不得删除、不得修改。** 它是行为基准，也是 6 个未移植功能的
   领域知识载体。存档标签 `archive/legacy-ui-2026-11-21`。
6. **做减法。** 界面上只留「状态」和「动作」，不留标语、提示句、说明段落。
   一个东西如果非得靠文字解释才看得懂，就去改布局，别加字。
   每个决定要同时提升 **UX / DX / AX**，并且不能弄坏已有功能（见 §6.14）。

---

## 1. 这个项目是什么

一个 Left 4 Dead 2 的模组管理器（Windows 桌面）。

**核心机制**：L4D2 通过 `left4dead2/addonlist.txt` 控制哪些 `.vpk` 启用。工具负责扫描 `addons/`、解析 VPK 元数据、分类、启停、导入压缩包、从创意工坊下载。

**一个曾经的设计约束（2026-11-21 已拆除）**：原来外观类模组（角色/特感/枪械/近战/医疗品/投掷）按 `(分类, 物品)` 做「同组互斥」—— 同组只允许启用一个，理由是「游戏机制决定」。

这个理由站不住：游戏本身允许同槽位的多个 VPK 同时启用（实际生效的是加载顺序靠后的那个），管理器再拦一层，用户想「两个皮肤都留着、需要时临时切」反而做不到。现在**由用户自行管理冲突**，管理器不再阻止任何组合。详见 §6.5。

---

## 2. 项目状态

### 2.1 技术栈

| 层 | 技术 | 状态 |
|---|---|---|
| 业务逻辑 | Python 3.14.7，纯标准库 + requests | **冻结**，不要动 |
| 旧 UI | PySide6 6.12.0 | 维护模式，仍在发布 |
| 新 UI | pywebview 6.2.1 + 系统 WebView2 | **主线**，本期完成第一期 |
| 打包 | PyInstaller 6.22.3 | 两套 spec 并存 |

### 2.2 新界面唯一，旧界面已归档

**现状（2026-11-21 起）：只发新界面。** `app/ui/`（PySide6，5887 行）与 `main.py`
原地保留但已归档：不再维护、不再发版、不得删除也不得修改。存档标签
`archive/legacy-ui-2026-11-21`，需要完整可发版的旧界面时 `git checkout` 到那个标签。

`build_release.ps1 -Target legacy` 仍能构建它（会先打印醒目警告），只为查阅/对照。

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
# 业务逻辑单测 + 前后端契约测试（85 个，用隔离临时目录，不碰真实游戏目录）
.\.venv\Scripts\python -X utf8 -m unittest discover -s tests -v

# 前端契约测试单独跑（52 项，Node 直跑，不需要 Python）
node tests\adapt_contract.js

# 桥接层自测（不需要窗口，用假 window 验证事件推送）
.\.venv\Scripts\python -X utf8 -m app.shell._selftest

# 前端语法
node --check app/webui/app.js
node --check app/webui/bridge.js

# 端到端（真实数据 + 真实桥接 + 真实界面）
.\.venv\Scripts\python -X utf8 docs\redesign\proto\e2e_check.py

# 合集/子分类：卡片 (x/5) 标签、「更多」常驻与部件列表、
# 两级改分类 + 归回工坊合集（会真写一次再还原）
.\.venv\Scripts\python -X utf8 docs\redesign\proto\coll_check.py

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
# 默认就是新界面（等价于 -Target web）：自动带 7-Zip、自动冒烟、自动校验产物
.\build_release.ps1

# 无 GUI 的环境（CI）关掉冒烟
.\build_release.ps1 -NoSmoke

# 不重新打包，只校验现有产物 —— 同样默认冒烟
.\build_release.ps1 -VerifyOnly

# 旧界面（已归档）：能构建，但会先打印「不保证可用、不再发版」
.\build_release.ps1 -Target legacy
```

产出：
```
release/L4D2 Mod Manager-v<版本>-win64-web/        目录版
release/L4D2 Mod Manager-v<版本>-win64-web.zip    压缩包
release/L4D2 Mod Manager-v<版本>-win64/           旧界面（已归档，-Target legacy 才产出）
```

> `-Target both` 已删除：旧界面归档后没有「两套一起发」的场景。

版本号**自动从 `packaging/version_info.txt` 读**，不用手工传。

⚠️ **两个 spec 的输出目录名不同**（`(WebUI)` 后缀），这是刻意改的 —— 原来两个都叫 `L4D2 Mod Manager`，先后构建会静默互相覆盖。

> 历史：`build_release.ps1` 原来只打旧 spec，新栈没有任何自动化发版路径（2026-11-20 修复）。
> 现在**只打新界面**，旧界面的构建路径仅作归档用途保留。

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

#### 冒烟测试（`-Smoke`，2026-11-21 新增）

为什么需要：spec / `hiddenimports` 少带一个模块时，**构建成功、包完整、所有静态检查全绿**，
只有双击运行那一刻才崩。这类问题没法靠读代码发现，只能真的启一次。

`-Smoke` 只对 web 栈生效，做四件事：

1. 先跑一遍 `Test-Package`（7-Zip 齐全、拒绝 `data/` 与文档文件）
2. 用 `main_web.py` 的 `L4D2_SHOT` 钩子启动包里的 exe，最多等 90s 截图落地
3. 断言 stdout 里有 `boot ... ok=true` —— **只看截图不算数**，空壳窗口也能截出 4.9MB 的图
4. 收掉进程、删掉冒烟产生的 `data/`（里面有本地游戏路径）、再跑一遍 `Test-Package`

**冒烟默认开启**（2026-11-21 起）：不弹窗就不算构建过。它会短暂弹一次窗口，
无 GUI 的环境用 `-NoSmoke` 关掉 —— 跳过时会打印一行「已跳过冒烟（-NoSmoke）」，
不静默。冒烟失败**必须**让构建以非零码退出（`Invoke-SmokeTest` 直接 throw，
实测 `-VerifyOnly` 下拿掉 exe 会 EXIT=1），不能降级成警告。

#### 产物搬运/压缩要带重试

刚写完的 46MB 产物会被 Defender / 索引器短暂独占，`Move-Item` 直接抛
`Access to the path ... is denied`。第一次遇到时排查了半天 —— 手动重跑同一个
`Move-Item` 就成功了，纯属瞬态。

现在 `Remove-Item`（旧产物 / 旧 zip）、`Move-Item`、`Compress-Archive`
都包了 `Invoke-WithRetry`（最多 6 次，间隔递增）。失败信息会带上
「哪个步骤 + 试了几次」，而不是丢一个裸的 IOException。

#### ⚠️ `.ps1` 必须是 UTF-8 **with BOM**

`build_release.ps1` 和 `packaging/fetch_7zip.ps1` 里都有中文。Windows PowerShell 5.1
（系统默认那个）**不带 BOM 就按 GBK 解码**，中文注释会把字符串截断，整个脚本解析失败：

```
Missing expression after ','.
The string is missing the terminator: '.
```

这两个文件在此前一直是「无 BOM」状态，只是从没人用 5.1 跑过（`pwsh` 7.x 默认按 UTF-8
读，能跑通，所以文档里的 `.\build_release.ps1` 对 5.1 用户其实是坏的）。
2026-11-21 已补 BOM + CRLF，5.1 与 7.x 都能过。

**改这两个文件时别把 BOM 丢掉**（编辑器另存为「UTF-8 with BOM」，或 python 显式
`encoding="utf-8-sig"`）。验证：

```powershell
powershell -NoProfile -Command "`$e=`$null; [void][System.Management.Automation.Language.Parser]::ParseFile('D:\项目\L4D2 Mod Manager\build_release.ps1',[ref]`$null,[ref]`$e); `$e.Count"
```

返回 `0` 才算好。

---

## 4. 代码地图

```
app/core/          4234 行  ★ 业务逻辑，冻结，与 UI 无关
├── library.py             模组库：扫描、启停、别名、分类、删除
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

### 为什么 thumb 是 file:// URL（2026-11-21 改）

原本是 base64，依据是「跨盘 `file://` 会被 WebView2 拦截」。**这条经验是错的**：
实测页面在 D:、图片在 E:，22 张跨盘图 **21 张直载成功**，唯一失败的那张
是路径没做百分号编码。

base64 的真实代价实测出来很大：`bootstrap()` 一次过桥 **18.2MB / 3.13s**。

现在的做法（`api._thumb_url`）：

| 情况 | 返回 |
|---|---|
| 预览图 > 400KB | 压成 320×180 存 `data/thumb-cache/<hash>.jpg`，返回它的 URL |
| 预览图 ≤ 400KB | 直接返回原图的 URL |
| 没有图 | 退回 `assets/wiki` 占位图 URL；都没有才空串 |

- URL 一律走 `pathlib.Path(p).resolve().as_uri()` —— 手拼字符串遇到中文/空格会 404
- 缓存键 = 路径 + mtime + 大小：换图自动失效；第二次启动只 stat，不重新压图
- 前端 `loading="lazy"`：只有看得见的卡片才会真的读盘

效果：payload **18.2MB → 0.09MB**，`bootstrap()` **3.13s → 0.11s**。
`thumb-cache/` 是纯缓存，`clean_cache` 会整目录删掉（删了下次启动重新生成一次）。

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

### 6.5 ⚠️ 互斥机制已整体拆除（2026-11-21）

**这一节原来讲的是「互斥类别有 4 份副本」的风险。现在情况变了：互斥机制被完全拆掉了。**

用户裁定：**放弃互斥组实现，让用户自行管理冲突模组。** 具体：

| 拆掉的 | 位置 |
|---|---|
| 组级互斥开关（`settings.json` 的 `mutex_off_groups`） | 全链删除 |
| 启用时自动停用同组其它项 | `api.toggle_mod` 固定 `mutex=False` |
| 导入/下载后自动切换到新模组 | `library.enable_new_mods` 去掉互斥段 |
| 「整理」时每组强制只留一个 | `library._settle_conflict_selections` 整个删除 |
| 前端「N 组待处理」提示 + 批量处理对话框 | 删除 |
| Inspector 的「同组」面板 | 整块删除 |
| 启用前的「会停用同组 X 个」确认框 | 删除 |

**保留的**：`classify.CONFLICT_CATEGORIES` 常量 —— 分类器内部仍用它标注
「这是外观类」，只是不再是 UI 概念、不再驱动启停行为。

**行为变化（用户可感知）**：

- 启用任意模组都**不会**连带停用任何东西
- 同一「分类+物品」可以同时启用多个（游戏里通常后加载的覆盖前面的）
- 导入 5 个同组皮肤 → 5 个全启用，不再只留最后一个

完整方案与验证清单见 `docs/PLAN_REMOVE_MUTEX.md`。
回滚：`git revert <commit>` 或 `git show dde9690:app/webui/app.js`。

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

### 6.11 ⚠️ 假动作清单（共 6 处）

`app.js` 里有一类「看起来有功能、实际只弹提示」的代码。本期审计
31 个 API 方法 × 前端调用点，共找出 6 处：5 处接上了真实现，
1 处（归入合集）确认本来就不该有动作，直接删除：

| 位置 | 原来的行为 | 现在 |
|---|---|---|
| `#launchBtn` | `infoDialog('演示环境不会真的启动 L4D2')` | `bridge.launch_game()` → `steam://rungameid/550` |
| `#insWorkshop` | `infoDialog('演示环境不会真的打开浏览器')` | `bridge.open_workshop(id)` → `steam://url/CommunityFilePage/<id>` |
| `#statusPath` | `toast('已在资源管理器中打开 addons 目录')` | `bridge.open_path(addonsDir)` → 真的打开 |
| `#sortBtn` | 只给「最近添加」一个选项，选了等于没选 | 三档循环（最近添加 / 名称 / 大小），都真的生效 |
| `修改分类` | `infoDialog('实际实现会打开分类选择对话框')` | `bridge.set_category()`，落盘且置 `pinned` |
| `归入合集` | `infoDialog('合集归属尚未迁移到新界面')` | **没有对应动作，直接删掉**：合集是展示不是操作，见 §8.8 |

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

### 6.14 界面文字规约（2026-11-21，用户明确要求长期遵守）

目标：**目标简单、架构简单、设计简单、实现简单。** 参照 Linear 官网 / 苹果备忘录那种干净度。

**只允许两类文字**：

| 类型 | 例子 | 说明 |
|---|---|---|
| 状态 | `已启用` / `未启用` / `不属于任何合集` / `未指定` | 描述「现在是什么」，不可省 |
| 动作 | `保存` / `工坊页` / `＋ 新建子分类` | 点了会发生什么，不可省 |

**不允许**：标语、口号、提示句、说明段落、「你正在做 X」这种转述。
典型该删的句子：`手工指定后会标记为「已固定」，重扫不再改它`、
`合集只是展示分组，管理器不会因为它自动启停`、`留空 = 不细分`。
如果删掉之后用户看不懂 —— 那是布局的问题，不是缺一句提示。

**把入口做成内容本身**，不要在旁边挂按钮：

```
✗ 子分类   The Bloody Moors   [修改]      ← 多一个次要标签
✓ 子分类   The Bloody Moors              ← 值本身就是按钮
```

**冗余即噪音**：同一个名字在一个块里出现两次（合集名 + 子分类值）就只留一处。

#### 三赢检查表（每次动 UI 都过一遍）

- **UX**：少一次点击 / 少一处猜测 / 不引入歧义。删掉的入口必须有等价路径
  （例：删掉「归回工坊合集」按钮，是因为选择器里就能选到合集名那一行）。
- **DX**：状态来源唯一（`displayItem()`、`subItemsOf()`、`fmt_size()`），
  改动只需改一处；不新增会漂移的副本。
- **AX**：稳定钩子 —— 带 `id` / `data-*` 的元素可被脚本直接定位，不靠读文案。
  探针用的钩子清单见 §9.8。**改钩子名必须同时改探针**（`coll_check.py` 会红）。

**不能弄坏任何东西**：任何「简化」都要能指出被删能力的等价替代，否则不准删。

## 7. 那些看起来奇怪的设计决定

### 7.1 为什么扫描是只读的

`library.rescan()` 只读 `addons/` 目录重建记录，**不动 `addonlist.txt`**。启停状态从 `addonlist.txt` 同步过来。

这是刻意的：用户可能在游戏内或别的工具里改过状态，扫描应该尊重磁盘现状而不是覆盖它。

### 7.2 为什么游戏运行时禁止写入

`addonlist.txt` 被游戏独占。运行中写入会失败或损坏。所以所有写操作前都要检查 `state.gameRunning`。

⚠️ `api.py` 里 `is_l4d2_running()` 失败时被 `except: pass` 吞成 `False` —— 意味着检测失败时会**放行写入**。这是个已知隐患，见 9.2。

### 7.3 ~~为什么 Inspector 的同组切换有确认框，而双击没有~~（已作废）

> **2026-11-21：互斥机制已整体拆除，这条不再成立。**
> 现在启用任何模组都不弹同组确认框，也不停用任何东西。
> 见 §6.5 与 `docs/PLAN_REMOVE_MUTEX.md`。

原本两处走同一套逻辑：启用外观模组时若同组已有启用的，先告诉用户会被顶掉。

### 7.4 为什么「入库时间」用 `added_at` 而不是 `mtime`

`mtime` 是文件修改时间 —— 用户移动文件、重新下载都会变。
`added_at` 是首次登记时间 —— 这才是「入库时间」。

⚠️ 但 `app/core/library.py:141` 每次重扫都会 `new_mod_record()`，`added_at` 被重置为 `now`，`if old:` 分支只保留 `alias`/`enabled`/`pinned`，**不保留 `added_at`**。

所以这个字段目前在**每次重扫后都会丢失**。这是 core 的 bug，但 core 是冻结的。`_to_mod` 已经做了 `added_at or mtime` 的兜底。

**如果哪天允许改 core，第一件该做的就是保住 `added_at`。**

### 7.5 缩略图：file:// URL + 磁盘缓存（旧结论已推翻）

~~跨盘 `file://` 被 WebView2 拦截~~ —— 2026-11-21 实测不成立，见 §5。
改成 URL 之后 bootstrap 从 18.2MB/3.13s 降到 0.09MB/0.11s。

留两个坑提醒：

1. **必须 `Path.as_uri()`**。手拼 `"file:///" + path` 遇到中文/空格会 404，
   而且浏览器只会表现为「这张图裂了」，不会有任何报错。
2. **超大原图要压**。`addons/` 里有 8504×8504、13MB 的 jpg；200 张原图共 151MB。
   > 400KB 的会压成 320×180 落盘缓存，别指望渲染端硬解。

如果哪天又出现「全部裂图」，先查这两条，再查 WebView2 版本策略。

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
| 14 | ~~`_fmt_size` 有三份实现~~ | ✅ **第六轮收中间层两份**：抽到 `app/shell/fmt.py`，`app/ui/util.py` 那份随旧界面冻结不动（行为差异见 §8.7） |
| 15 | ~~`spec` 的 `hiddenimports` 18 项里 15 项多余~~ | ✅ **第六轮删到 3 项**，并用 `-Smoke` 实测打包能跑 |
| 16 | `app/webui/assets/mods/*.webp` 6 张图只用于 mock | ✅ **裁定保留**：`bridge.js` 的浏览器 mock 在用，删了预览就成空白块 |
| 17 | ~~`app.js` 里的 `DEMO_MODS`（29 行演示数据）~~ | ✅ **第六轮删除**（是死代码，`bridge.bootstrap()` 在 mock 下必定成功） |
| 18 | `chapters` 是无人读写的遗留字段（197/200 条带它） | ⬜ 已记录进 `DATA_SCHEMA.md` §2.3 |
| 19 | `api.py` 的 `Image.open` 不关闭句柄（bootstrap 里每条记录跑一遍） | ✅ **第六轮修复**：改 `with` 语句，Windows 上不再锁预览图 |

### 8.7 第六轮（2026-11-21）：P2 整洁 + 打包冒烟

| 项 | 结果 |
|---|---|
| 体积格式化 | 三份 → 两份：`app/shell/fmt.py:fmt_size`，`api`/`tasks` 都引用它（`assertIs` 锁死） |
| `hiddenimports` | 18 → 3（只留 `webview.platforms.winforms` / `edgechromium` / `clr` 这 3 项真的是运行期动态加载的） |
| `DEMO_MODS` | 删 29 行死代码 + 删掉「bootstrap 失败就用假数据」的兜底（会拿假模组盖住真错误） |
| `Image.open` | 改 `with`，`bootstrap` 不再漏 200 个文件句柄 |
| `build_release.ps1` | 新增 `-Smoke`；`.ps1` 补 UTF-8 BOM + CRLF，PS 5.1 也能跑（见 §3.5） |
| 测试 | 64 → **67**（新增 `TestSizeFormat` 3 条），Node 契约 21 项不变 |
| 打包实测 | 5.1 下 `-Target web` → 46.4 MB / zip 22 MB，`-Smoke` 断言 `boot ok=true` 通过 |

#### 体积格式化的两份为什么不能合成一份

`app/ui/util.fmt_size`（旧界面，冻结）和 `app/shell/fmt.fmt_size`（新界面）**行为不同**：

| 输入 | 旧界面 | 新界面 |
|---|---|---|
| `1536` | `1 KB`（`%.0f`） | `1.5 KB`（`%.1f`） |
| `"abc"` / `None` | `?` | `0 B` |

旧那份要跟着 `app/ui/` 一起冻结（HANDOFF 铁律 8），所以**保留两套输出、只收掉中间层重复的那一份**。
`app/shell/fmt.py` 的 docstring 里写明了这个差异是有意的，别再拿「统一格式」当理由去改冻结代码。

#### B-3（预览图真下载）的实测结论：不值得做

用真实库量了一遍预览图来源（200 条）：

| 来源 | 条数 |
|---|---|
| 模组自带 / 工坊订阅时落在 addons 旁的 `.jpg` | **194** |
| `assets/wiki` 占位图兜底 | 5 |
| 完全没图 | 0 |

只有 **6 条**（5 条有工坊 ID、1 条手装地图）拿不到真图，其余 194 条本来就有。
`PreviewWorker` 是旧界面里**从未被实例化**的代码，移植它最多补 6 张图 ——
性价比不成立，**建议关闭该项**，除非以后出现「新增模组普遍缺图」的情况再回头看。


### 8.6 第五轮（2026-11-21）：拆除互斥机制 + 标题回归修复

| 项 | 结果 |
|---|---|
| 互斥机制整体拆除 | ✅ 前端 10 处 + 后端 4 处 + core 2 处全部删除，净删约 385 行 |
| 清单与验证 | ✅ `docs/PLAN_REMOVE_MUTEX.md`，8 条验证全部实测 |
| 备份 | ✅ `dde9690` + `.tmp/mutex_removal_backup.patch` |
| ~~标题 bug 修复~~ | ✅ `addoninfo` 键大小写（`addontitle` 被漏掉，4 个标题退化成工坊 ID） |
| **标题回归** | ⚠️ **踩了一次坑并已修正**，见下 |

#### ⚠️ 第五轮的真实事故：修 bug 引发更大回归

修好大小写 bug 后 `CLF_VERSION` +1 → 全库重扫 → **136 个标题变化**：

```
2050209573  CSGO AK47 | Azur Lane-Saratoga(Glowing)  →  AK-47 Saratoga
241776737   Go! Pokeball! (Vomit jar)                →  Pokeball.
```

更糟的是出现 **11 组「多个不同文件同名」**（`Divine Cybermancy × 4`、
`地心引力 × 4`…），用户分不清谁是谁。

**根因**：这些标题原来是 `_enrich_from_workshop()` 从工坊 API 拉的，
比 `addoninfo` 里的好得多。重扫无条件用 addoninfo 覆盖，把它们冲掉了。

**修复**：
1. 回滚 `library.json` 到重扫前
2. 加 `title_locked` 字段，一次性迁移把 195 条（有 workshop_id 且标题非纯数字）加锁
3. `_scan_one` 的 `old` 分支保留 `title_locked` 与锁定标题
4. 再重扫 → **只 4 个标题变化**，全是原来退化成工坊 ID 的，全部修好

**教训（写进 `DATA_SCHEMA.md` §2.1.2）**：
改分类器/标题逻辑前，先想清楚「重扫会不会覆盖掉在线补全的结果」。
`title_locked` 就是给这类「外部来源优于包内元数据」的字段准备的机制。

> 分类规则回归测试见 `tests/test_classify_rules.py`（21 项），
> 包含误伤防护 + `title_locked` 跨重扫保留。

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
| ~~A-1 合集 UI~~ | ✅ **第七轮已做**（展示在详情下方「更多」里），见 §8.8 |
| ~~B-3 预览图真下载~~ | ✅ **实测后关闭**：补下载只值 6/200 张图，见 §8.7 |
| B-4 合集反查 | 仍未移植；新 UI 的下载流程直接支持粘贴合集链接，主路径已覆盖（见 `docs/LEGACY_UI.md` §2.3） |

### 8.9 第八轮（2026-11-21）：新界面收口

用户逐条确认的七项，全部落地。**旧界面从此不再发版。**

| 项 | 结果 |
|---|---|
| §1 归档旧界面 | ✅ `git tag archive/legacy-ui-2026-11-21`；`app/ui/` 与 `main.py` 原地保留 + ARCHIVED 注释；`-Target` 收敛为 `web`/`legacy`，删掉 `both`；legacy 构建先打印「不保证可用、不再发版」 |
| §2 冒烟默认开 | ✅ `-Target web` 与 `-VerifyOnly` 默认跑冒烟，`-NoSmoke` 关掉（会打印「已跳过冒烟」）；失败非零退出（实测拿掉 exe → EXIT=1） |
| §6 标题三层兜底 | ✅ `displayTitle()`：别名 → 标题 → **完整 vpk 文件名**；卡片/详情/搜索/部件列表统一走它；与 core 的 `store.mod_display_name()` 结果一致（契约测试锁死） |
| §6 别名入口 | ✅ 底部功能栏图标改为带文字的「自定义标题」；编辑改用自绘 `textDialog`（`window.prompt` 在 WebView2 里不可靠） |
| §4 「更多」常驻 | ✅ 无合集时显示「不属于任何合集」；折叠条不再显示「合集 · 0 个部件」 |
| §3 卡片合集标签 | ✅ `The Bloody Moors (3/5)`，序号前端算（`collections[cid].files`），不给 `_to_mod` 加字段 |
| §5 合集=子分类 | ✅ `displayItem()`：`item` 为空时**只读**回落到合集名；「修改分类」升级为两级（分类 → 子分类，可手填）；新增「归回工坊合集」；**不写 collections** |
| §7 缓存引用清理 | ✅ `clean_cache` 增加 `previews/` 孤儿清理（只删没被任何记录引用的文件）。实跑：41 个文件里 10 个被引用、31 个孤儿 → 释放 **31.3MB**，二次执行 0 字节 |

**为什么要清理 previews**：工坊缩略图下载到 `data/previews/`，记录里的 `preview`
存绝对路径。删模组/重导入后这些图就成孤儿，而它既不在 `tmp/` 也不在
`thumb-cache/`，原来的 `clean_cache` 从来没碰过。用户主动点「清理缓存」才动，
启动时不扫。

> ⚠️ 任务书里写的是「200 条记录 0 条引用」，实测是 **10 条引用**。
> 实现按引用比对（绝对路径 + `normcase`），所以两种情况下都不会误删 ——
> 这也说明「先量再删」比照抄数字可靠。

#### 合集与子分类的关系（本轮最重要的概念统一）

用户视角只有一套层级：**分类 → 子分类**。地图下一个合集就是这张图的向下细分。

- `item` 是子分类（可改）；`collection` 是工坊结构（不可改、界面不写）
- `item` 为空且属于合集时，前端**显示层**回落到合集名；API 层绝不回填
- 用户改子分类只写 `category`/`item`；「归回工坊合集」= 把 `item` 写回合集名

详见 `docs/DATA_SCHEMA.md` §7.4。

### 8.11 第十轮（2026-11-21）：做减法

用户要求：像 Linear / 苹果备忘录那样干净；**砍掉标语、提示文字和次要标签**；
一个页面非得靠这些才看得懂就去改布局。

| 项 | 结果 |
|---|---|
| 排序 | 确认「**中文在前、英文在后**」（`localeCompare(zh)`，中文内部按拼音）；已钉进 Node 契约测试 |
| 选择器 | 「＋ 新建子分类」固定**列表第一行**（不用滚才找得到）；点开在同一位置变输入框，回车即建、Esc 撤回；「不细分」只在有值时出现；全对话框只剩「保存」一个按钮 |
| 删文字 | 分类/子分类/标题对话框的说明段落、「更多」里的两段解释、折叠条上的「合集 · N 个部件」摘要 |
| 删按钮 | 「修改」（值本身可点）、「归回工坊合集」（选择器里能选到合集名那行）、「取消」（X / Esc / 点遮罩） |
| 去冗余 | 合集名原本在「子分类」和「合集标题」重复出现 → 只留子分类值；合集行改成 `合集  5 个部件  [工坊页]` |
| 规则化 | 写进 §0 第 6 条、§6.14（界面文字规约 + 三赢检查表）、§9.8（稳定钩子） |

**等价值表**（删任何东西都必须能指出替代路径，否则不准删）：

| 删掉 | 替代 |
|---|---|
| 「归回工坊合集」按钮 | 选择器里点合集名那一行 → 保存 |
| 「修改」按钮 | 点子分类的值 |
| 「取消」按钮 | X / Esc / 点遮罩 |
| 全部说明文字 | 布局本身：列表就是选项，值就是入口 |

### 8.10 第九轮（2026-11-21）：子分类排序 + 选择器 + 隐形预留入口

| 项 | 结果 |
|---|---|
| 子分类按名称排序 | ✅ 一级分类下的子分类一律 `localeCompare(zh)` 排序；不再按数量降序（数量天天变，位置跟着跳） |
| 子分类单一来源 | ✅ 新增 `subItemsOf(cat, mods, colls)`：树、单层列表、分组列表、选择器全走它（顺带去掉两处重复的收集逻辑） |
| 子分类选择器 | ✅ 改分类第二步从「纯输入框」升级为「可滚动现有列表」（**第十轮又改成行内新建，见 §8.11**） |
| 用户新建的子分类自动清除 | ✅ 子分类**不落库**（从 `item` / 合集名现算），最后一个模组被移走时自然消失；管理器自带的不会被谁清掉（没人改别的模组的 item） |
| 「⋯ 更多操作」隐藏 | ✅ 带 `hidden` + `data-reserved-entry`，DOM/事件保留，见 §9.7 |
| 测试 | ✅ Node 39 → **45**（subItemsOf 排序/去重/分类过滤/合集回落/自动消失）；coll_check 增加 6 条实机断言（选择器可滚动、已排序、点选填充、树排序、新建项自动消失、自带项保留、⋯ 不可见） |

**为什么子分类不落库**：一旦存进 settings/library，就要自己维护
「空了的要不要删、自带的要不要留」，而且会和 `item` 形成两个真相来源。
现在它纯粹是 `mods` 的投影 —— 这也正好满足「移走所有模组后自动清除」。

### 8.12 第十一轮（2026-11-21）：启动性能 + 对话框放大

用户反馈：启用软件有点慢；改子分类的窗口太小、显得狭窄。

#### 启动慢的根因：缩略图走了 base64

`bootstrap()` 实测 **3.13s / 18.2MB**，其中 18.1MB 是 200 张缩略图的 base64。
这个开销**一定会出现在其他用户机器上**：与模组数量和图片体积成正比，
用户模组更多就更慢（500 条大概 45MB）。

| 改动 | 效果 |
|---|---|
| 缩略图改传 `file://` URL（`Path.as_uri()`），>400KB 的压 320×180 落盘缓存 | payload **18.2MB → 0.09MB** |
| `bootstrap()` | **3.13s → 0.11s**（二次/热缓存） |
| 首次启动（71 张大图要压一次） | 3.8s，之后 0.11s |
| 进程启动 → 首屏卡片 | **~1.9s**（其中 ~1.2s 是 WebView2 初始化、0.38s 是 import，都不是数据） |

#### 顺带修掉第二个瓶颈：游戏进程检测

`bootstrap` 里同步调 `app/core/game.is_l4d2_running()`，它起 `tasklist` 子进程，
实测 **0.49s** —— 占掉缩略图修好之后剩下的九成时间。

core 是冻结层，所以在 `app/shell/api.py` 加了一条快路径
`_game_running_fast()`：用 `CreateToolhelp32Snapshot` 遍历进程表，**11ms**，
结果与 core 完全一致；任何异常返回 `None`，退回 core 的实现，不自己猜。
检测失败仍然按 `unknown=true` 处理（前端会挡住写入），语义没变。

#### 子分类对话框放大

`max-width` 420 → **560px**，列表 `max-height` 220 → **420px**，
行高/字号也放宽（5px/10px → 7px/11px）。原来 40 项要滚 6 屏，现在 3 屏。

#### 教训

`docs` 里写着「跨盘 file:// 被 WebView2 拦截」—— 一条**没被验证过的经验**，
代价是整个 bootstrap 每次启动多花 3 秒。凡是写在文档里的"平台限制"，
最好附上复现命令；这次复用 22 张跨盘图的探针一测就推翻了。

### 8.13 第十二轮（2026-11-21）：子分类补全（空的也显示）

用户反馈：特感少了子分类。真实库里特感只有 Tank / 普通感染者两个有模组，
树上就只剩这两项，看起来像分类坏了。

| 项 | 结果 |
|---|---|
| 目录来源 | `api._category_catalog()` 从 core 词表现算（`WHITELIST_STEMS`、`PREFIX_RULES`、`REGEX_RULES`、人物/武器/近战/医疗名单），**不手抄** |
| 覆盖 | 角色 9 / 特感 10 / 枪械 23 / 近战 23 / 医疗品 6 / 投掷 3 / 载具 19 / 杂项 17（含「语音」这类特殊桶） |
| 合并 | 库里出现过的值一律保留；catalog 项与已采用的「括号前基本名」相同则跳过（`急救包` vs `急救包(医疗包)`）。**只对 catalog 合并**——地图的 `Divine Cybermancy （Part1-2）/（Part2-2）` 基本名相同但确实是两张图 |
| 空项 | 不显示数量、可点击（进去是空列表 + 空状态） |
| picker | 选择器也列全目录，所以可以把模组直接分到「目前还空着」的子分类 |
| 消失规则不变 | 用户新建的（只存在于数据里）最后一个模组移走后自动消失；catalog 项永远在 |

**为什么从 core 读而不是写死一张表**：那些名字就是分类器会写进 `item` 的值。
写死迟早漂（新武器忘加、同一把枪两种叫法），而且没人会记得同步两处。
core 是冻结层，但**读它的常量**不算改它。

### 8.5 第四轮（分类器修复 + 组级互斥开关）

| 项 | 结果 |
|---|---|
| 框架/前置包误分类 | ✅ 新增 `_looks_like_framework`：`xdReanimsBase`、`KSEP Platform` 从「特感/角色」改为「杂项/前置框架」 |
| 地图多部件被打散 | ✅ 新增「addoninfo 明示 Campaign/Map → 归地图」前置规则：4 个部件修回地图，4 个地图家族恢复完整 |
| `CLF_VERSION` | ✅ 14 → **15**，真实库 200/200 已重扫到 15 |
| 组级互斥开关 | ✅ 详情页「同组」面板新增拨动开关，按 `(分类, 物品)` 关闭互斥；状态存 `settings.json` 的 `mutex_off_groups`（**第五轮已整体拆除**） |

**已知边界（无法自动修）**：`The Parish Halloween` 的 2 个 models/materials 部件
既无 addoninfo、也无 mission、也无 bsp，单看内容无法判断属于哪张地图，
分类器只能给「材质特效」。这类请让用户手工改分类（会自动置 `pinned`）。

> 分类规则回归测试见 `tests/test_classify_rules.py`（15 项），
> 包含「名叫 base 但只改一个角色的皮肤仍是角色」这类误伤防护。

### 8.8 第七轮（2026-11-21）：合集展示（A-1）

用户定位：**合集 = 纯展示分组，不参与任何管理逻辑**，收纳进模组详情下方的「更多」。

| 项 | 结果 |
|---|---|
| 归属数据源 | ✅ 改为**反查 `collections[cid].files`**（`api._collection_index()`）。记录上的 `collection` 字段会被重扫抹掉，真实库 200 条全是空串 —— 这是合集「一直看不见」的真正原因 |
| 接口 | ✅ `bootstrap()` 新增 `collections` 字段（`_collections_payload()`），`_to_mod` 的 `collection` 现在一定准 |
| UI | ✅ 详情下方新增可折叠「更多」，只有**属于合集**的模组才渲染（200 条里 6 条）；折叠时标题栏就显示「合集 · N 个部件」 |
| 部件区分 | ✅ 同图 5 个部件标题完全一样，靠**体积**区分（165.5 / 197.5 / 158.6 / 196.4 / 122.6 MB），点一下切过去 |
| 假动作 | ✅ 删掉菜单里那条「归入合集」（原来只弹「尚未迁移」） |
| 契约测试 | ✅ 24 项（+4）：归属反查、记录兜底、bootstrap 结构、两源一致性 |
| 实机验证 | ✅ 探针跑真库：`hasMore=true`、5 个部件、当前项正确、非合集模组不渲染、展开状态跨重渲染保留 |

**为什么不做「手工归入合集」**：合集由下载流程按工坊结构建立（`downloader` 写
`collections[cid].files`），不是用户手工编组的概念。加一个手工归组 UI 等于
引入第二个真相来源，而用户已经明确「合集不参与管理逻辑」。

**残留的观感问题（已知、不修）**：网格里那 5 张卡片标题一模一样，
只有点开详情才能看到「更多 → 合集」区分。要根治得在卡片上加合集角标，
但那会把「纯展示」的东西重新推回第一层界面，与本次收纳的要求相反。

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

### 9.5 `previews/` 只能按引用删，不能整目录 rmtree

`data/previews/` 里既有被引用的缩略图，也有孤儿。判断依据只能是
**记录的 `preview` 绝对路径**（`normcase` 折叠大小写），不能用文件名规则
（如「跟 workshop_id 同名」）—— 实测 10 条引用里就有不按 id 命名的。

`clean_cache` 里因此分成两类：`tmp/`、`thumb-cache/` 整目录 rmtree，
`previews/` 逐个文件比对后再删。不要图省事把 previews 也塞进
`targets` —— 那会把正在用的预览图全删掉。

### 9.6 合集名不能在 API 层回填 `item`

`displayItem()` 的「item 为空 → 回落合集名」只能发生在前端**显示层**。
如果哪天有人觉得「反正 API 层也能算」，把 `_to_mod` 的 `item` 填成合集名：

- 重扫会把这个值当成用户值（`pinned` 之后不再更新）
- `auto_item` 会记录一个用户从没选过的值，`restore_auto_category` 之后
  分类回到合集名而不是分类器结果
- 「归回工坊合集」与「恢复自动」两个动作的语义会混在一起

契约测试 `test_item_is_never_filled_from_collection` 就是防这一手。

### 9.7 详情栏的「⋯ 更多操作」是**故意隐藏**的

`renderInspector()` 里的 `.more-wrap` 现在带 `hidden` 和
`data-reserved-entry="insMore"`。里面只剩一项「修改分类」，而它的入口已经
移到「更多 → 子分类 → 修改」，所以这个三点按钮没有独占功能了。

**别删它**：DOM、`#insMore` 的事件绑定、`.more-menu` 的收起逻辑都完整保留着，
将来往详情栏加新操作时，把 `hidden` 去掉、往菜单里加 `<button data-more="...">`
即可。顺手重写一套只会重复那段「点外部收起 / Esc 收起 / 滚动收起」的绑定。

验证：`docs/redesign/proto/coll_check.py` 里有一条断言它确实不可见。

### 9.8 稳定钩子（探针 / 智能体用）

脚本（`docs/redesign/proto/*.py`）不读文案、不猜坐标，只认这些钩子：

| 选择器 | 含义 |
|---|---|
| `.mod-card[data-mod="<file>"]` | 网格卡片，值是 vpk 文件名 |
| `.mod-card .mod-name` / `.mod-coll` | 卡片标题 / 合集标签 |
| `#insSwitch` | 详情里的启用开关 |
| `#insSub` | 「更多」里的子分类值（点它打开选择器） |
| `#subList` / `.sub-item[data-sub]` / `#subCreate` / `#dlgInput` | 子分类选择器 |
| `.ins-more[open]` | 「更多」展开状态 |
| `.coll-part[data-part]` | 合集部件行（值是 vpk 文件名） |
| `[data-reserved-entry="insMore"]` | 已隐藏的「⋯」入口（见 §9.7） |
| `[data-rail="map"]` / `[data-mode="on"]` | 左侧 rail / 过滤模式 |

改这些名字必须同时改探针 —— `coll_check.py` 会立刻红，这是故意的。

## 10. 交接检查清单

接手第一周建议按这个顺序做：

- [ ] 读本文档第 0、5、6 节
- [ ] `pip install -r requirements.txt`，跑起 `main_web.py`
- [ ] 跑 `python -m unittest discover -s tests -v`，确认 **85 个全绿**
- [ ] 跑 `node tests/adapt_contract.js`，确认 **52 项**全过
- [ ] 跑 `python -X utf8 docs/redesign/proto/e2e_check.py`，确认 `mode: live`
- [ ] 打开一次 DevTools（`L4D2_DEBUG=1`），看有没有 console 错误
- [ ] 双击一个模组，**去 `addonlist.txt` 确认真的写了 `0`/`1`**
- [ ] 点顶栏的「启动」，确认真的拉起了 Steam（这是本轮修好的 5 处之一）
- [ ] 跑一次 `.\build_release.ps1 -Target web`，确认
      `release/L4D2 Mod Manager-v*-win64-web/_internal/7zip/7z.exe` 存在
- [ ] 跑一次 `.\build_release.ps1`（默认就冒烟，会弹一次窗），确认 exe 真的能启动
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
2026-11-21 收口之后的状态：

| 项 | 结果 |
|---|---|
| **发布流程** | 只有新界面一条路；7-Zip 三重校验；缺组件**直接失败**；冒烟默认开启（`-NoSmoke` 关） |
| **契约保护** | Python 85 项 + Node 52 项，字段契约、标题兜底、合集/子分类三层都有断言 |
| **实机可验** | `e2e_check.py` / `coll_check.py` / `toggle_check.py` 都跑真实库，不需要人眼看 |
| **界面收口** | 卡片 `合集名 (x/5)`、详情「更多」常驻、标题三层兜底、自定义标题入口可见 |
| **数据卫生** | `clean_cache` 清理 previews 孤儿（实测 31.3MB），重启不自动扫 |

剩下的（都不阻塞发版）：

1. **B-4 合集反查**：不做，代码随旧界面归档保留（`LEGACY_UI.md` §2.3）
2. `chapters` 遗留字段：保留（唯一的地图章节线索）
3. `title_locked` 手工解锁入口：暂不做（别名已能覆盖显示）
