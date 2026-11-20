# WebUI 重构 · 第一块落地记录

> 时间：2026-11-20
> 原则：**先做一个能跑通的最小闭环，验证通过再扩展。** 不一次性铺开八个并行任务。

---

## 已完成

### 1. 桥接层 `app/shell/api.py`

真实数据跑通：**200 个 mod、161 个启用、13 个分类、194 张缩略图**。

| 方法 | 状态 | 说明 |
|---|---|---|
| `bootstrap()` | ✅ | 返回 mods/settings/stats/game/paths/version |
| `get_stats()` | ✅ | |
| `toggle_mod(file, enabled)` | ✅ | 真实写入 addonlist.txt，返回 `disabled_siblings` |
| `set_alias` | ✅ | 参数校验通过 |
| `set_category` | ✅ | |
| `delete_mod` | ✅ | 移入回收站 |
| `reveal_mod` / `open_workshop` / `open_path` / `launch_game` | ✅ | |
| `start_scan` | ✅ | 线程 + 事件推送 |
| `save_setting` / `detect_game_dir` / `set_palette` | ✅ | |

**关键修正**：
- `gamemod` → 正确的模块名是 `app.core.game`
- `delete_mod` 无返回值，不是 `(ok, detail)`
- pywebview 反射 `js_api` 会递归展开 COM 属性链 → 加 `_serializable = False` + 日志过滤

### 2. 前端桥 `app/webui/bridge.js` + `events.js`

- 双模式：pywebview 环境走真实 api，浏览器里走 mock
- 7 种事件订阅，`window.__dsh.emit/on`
- 字段适配层（`title→name`、`category→cat`、`thumb→img`）

### 3. 承载层 `main_web.py`

- pywebview 6.2.1 + 系统 WebView2 157
- 已过滤无害噪音日志
- 与旧入口 `main.py` 并存

### 4. 界面 `app/webui/`

- `index.html` / `app.css` / `app.js` 从设计产物搬入
- 启动时 `bridge.bootstrap()` 取真实数据
- 视觉零改动

---

## 验证结果

### 端到端（`e2e_check.py`）

```json
{"mode":"live","ok":true,"mods":200,"enabled":161,"version":"1.2.1",
 "valid":true,"hasThumb":194,"categories":13,"cards":6,
 "brand":"L4D2 // ARMORY"}
```

`cards: 6` = 角色分类下 6 个 Ellis 模组，与真实数据吻合。

### 双向启停（`toggle_check.py`）

```json
{"steps":[{"step":"enable","ok":true,"enabled":true,"siblings":1},
          {"step":"disable","ok":true,"enabled":false}],
 "file":"2846688382.vpk","enabledAfter":true,"restored":true,"pass":true}
```

`siblings: 1` 证明同组互斥真的生效——启用一个 Ellis 皮肤时，另一个被自动停用。

**数据已完整回滚**：addonlist.txt 203 行与原文件逐行一致，library.json 恢复为 200/161。

---

## 发现的问题（已修）

| 问题 | 原因 | 处理 |
|---|---|---|
| pywebview 刷屏报错 | 反射 `js_api` 展开 COM 属性链 | `_serializable=False` + 日志过滤 |
| `evaluate_js` 返回 `{}` | 不 await Promise | 写全局变量后轮询 |
| 卡片仍显示 8 张假数据 | app.js 未接 bootstrap | 加适配层 + async boot |
| `gamemod` 模块不存在 | 实际叫 `game` | 改正 |
| `delete_mod` 返回 None | 误以为返回元组 | 改正 |

---

## 还没做

| 项 | 说明 |
|---|---|
| 长任务完整链路 | 导入/下载/扫描的 UI 反馈还没接 |
| 弹窗族 | 现在用的还是 demo.js 的简易版 |
| 设置页 | 界面在，未接真实命令 |
| 首次引导 | 空库引导未做 |
| 无边框窗口 | 现在用系统标题栏 |
| 打包 | 未做，预计 30MB 左右 |

---

## 文件清单

```text
main_web.py                     入口
app/shell/__init__.py
app/shell/api.py                桥接层（约 480 行）
app/shell/_selftest.py          无窗口自测
app/webui/index.html
app/webui/app.css
app/webui/app.js
app/webui/bridge.js
app/webui/events.js
app/webui/tokens.css
app/webui/assets/               图标 + 8 张演示缩略图

docs/redesign/proto/
  probe_pywebview.py            噪音诊断
  e2e_check.py                  端到端
  toggle_check.py               启停验证
```

---

## 下一步

1. 接长任务（扫描/导入/下载）的真实进度
2. 弹窗族组件化
3. 设置页接命令
4. 打包实测体积
5. 逐项回归

**顺序理由**：先打通"写"（启停已通），再打通"长任务"，最后补"边角"。这样每一步都能立刻验证。
