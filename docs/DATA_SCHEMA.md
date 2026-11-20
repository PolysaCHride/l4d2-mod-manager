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
| `item` | str | 具体物品（`AK-47`、`Ellis`）。空 = 该分类整体 | 分类器 / 用户 |
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
| `collection` | str | 所属合集 ID（带 `ws_` 前缀） | 下载/导入 |
| `pinned` | bool | 用户手工改过分类，扫描不再覆盖 | `set_category` |
| `clfv` | int | **分类器版本**，见 §3 —— 改错会让全部模组重算 | 扫描 |

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
CLF_VERSION = 14
```

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
  "motion": true                // 动画开关
}
```

**注意**：`proxy` 不只在 `settings.json` 里生效 ——
`api.save_setting('proxy', ...)` 会同时调 `steam_api.set_proxy()` 改**进程级全局变量**。
只改 json 文件、不重启应用，代理不会生效。

`game_dir` 改了会**重建 `Library` 实例**（`api.save_setting` 里置 None 再懒加载）。

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
| 改 `category` / `item` | ⚠️ 同时设 `"pinned": true`，否则下次扫描会被分类器覆盖 |
| 删掉某条记录 | ✅ 安全，等于让扫描重新登记它（但会丢 alias/pinned） |
| 改 `enabled` | ❌ **没用**。启用状态从 `addonlist.txt` 同步，扫描会覆盖回来 |
| 改 `clfv` | ⚠️ 见 §3，会触发全量重算 |
| 改 `mtime` / `size` | ⚠️ 会误导缓存判断，可能让扫描跳过实际已变化的 vpk |
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

### 7.3 合集 ID 的前缀

`collections` 的键是 `"ws_<数字>"`，而 mod 记录里的 `collection`
字段也带同样的前缀。**别把它当成纯数字 ID 去和工坊接口比较。**

---

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
| `collection` 非空 | 6 |
| `workshop_id` 为空 | 1 |
| `preview` 为空 | 6 |
| `chapters` 存在 | 197（其中非空 48） |
