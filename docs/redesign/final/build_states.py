# -*- coding: utf-8 -*-
"""Build the state board: every blocking dialog + every import / download stage.

Output: states.html (review artifact, static mockups in BLACKSITE style).
"""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- primitives

def dialog(title, body, actions, tone="neutral", width=520, extra=""):
    """One blocking dialog mockup."""
    buttons = []
    for label, kind in actions:
        cls = "dlg-btn"
        if kind == "primary":
            cls += " primary"
        elif kind == "danger":
            cls += " danger"
        buttons.append(f'<button class="{cls}" type="button">{escape(label)}</button>')
    return f'''
<div class="dlg tone-{tone}" style="width:{width}px">
  <div class="dlg-head">
    <span class="dlg-dot"></span>
    <h4>{escape(title)}</h4>
    <button class="dlg-close" type="button" aria-label="关闭">✕</button>
  </div>
  <div class="dlg-body">{body}</div>
  <div class="dlg-foot">{"".join(buttons)}</div>
</div>'''


def p(text):
    return f'<p class="dlg-text">{escape(text)}</p>'


def rows(items):
    out = []
    for name, meta, flag in items:
        tag = f'<span class="dlg-tag {flag}">{escape(meta)}</span>' if meta else ""
        out.append(f'<div class="dlg-row"><span class="dlg-row-name">{escape(name)}</span>{tag}</div>')
    return '<div class="dlg-rows">' + "".join(out) + "</div>"


def check_row(text):
    return (f'<label class="dlg-check"><input type="checkbox">'
            f'<span>{escape(text)}</span></label>')


def step(num, name, state, note, mock, wide=False):
    """state 用作说明用途的一句话；note 作为小字补充。"""
    cls = "state-card wide" if wide else "state-card"
    body = f'<p class="state-note">{escape(note)}</p>' if note else ""
    return f'''
<article class="{cls}">
  <div class="state-meta">
    <span class="state-num">{num}</span>
    <span class="state-name">{escape(name)}</span>
    <span class="state-state">{escape(state)}</span>
  </div>
  <div class="state-canvas">{mock}</div>
  {body}
</article>'''


def panel(title, inner, foot="", cls=""):
    foot_html = f'<div class="panel-foot">{foot}</div>' if foot else ""
    return f'''
<div class="panel {cls}">
  <div class="panel-head">{title}</div>
  <div class="panel-body">{inner}</div>
  {foot_html}
</div>'''


# ---------------------------------------------------------------- dialogs

DIALOGS = [
    ("信息", "info", "导入完成 / 自动检测结果等一次性结果通知",
     dialog(
        "导入完成",
        p("已加入模组库 2 个。"),
        [("知道了", "primary")],
        tone="info", width=460)),
    ("警告", "warning", "游戏运行中、目录缺失、格式不支持等前置拦截",
     dialog(
        "游戏运行中",
        p("游戏运行时无法修改模组配置，请先退出游戏。"),
        [("知道了", "primary")],
        tone="warning", width=460)),
    ("错误", "danger", "下载失败、导入失败、写入被拒等不可继续的错误",
     dialog(
        "下载失败",
        p("写入 addons 目录时被拒绝（磁盘空间不足）。"),
        [("重试", ""), ("关闭", "primary")],
        tone="danger", width=480)),
    ("确认", "question", "一键整理、清理缓存、合集归组等需要用户同意才执行的动作",
     dialog(
        "整理现有模组",
        p("将扫描 addons 与 workshop：登记未入库模组、把 workshop 内容移入顶层、"
          "同组外观只保留一个启用项。")
        + rows([("登记未入库", "预计 12 个", ""),
                ("workshop 迁移", "预计 8 个", ""),
                ("外观互斥", "预计停用 5 个", "warn")]),
        [("取消", ""), ("开始整理", "primary")],
        tone="question", width=520)),
    ("危险确认", "danger", "删除模组、解散合集等不可逆操作；带「今日不再提醒」",
     dialog(
        "删除模组",
        p("《VRC プラム Plum replace ellis》将从模组库移除，文件移入回收站。")
        + check_row("今日不再提醒"),
        [("取消", ""), ("移到回收站", "danger")],
        tone="danger", width=520)),
    ("部分失败", "warning", "批量任务里有成功也有失败时，逐项列出结果而不是只报总数",
     dialog(
        "部分下载未完成",
        p("已导入 2 个，失败 1 个。") + rows([
            ("[Gakuen IDOLM@STER] Fujita", "已导入", "ok"),
            ("雨衣替换 Ellis", "已导入", "ok"),
            ("死亡中心 · 重制版", "连接超时", "bad"),
        ]),
        [("查看日志", ""), ("关闭", "primary")],
        tone="warning", width=560)),
    ("缺少解压组件", "warning", "导入 7z / RAR 但没有可用解压程序时，提供两条修复路径",
     dialog(
        "需要 7-Zip 解压组件",
        p("当前没有可用的 7-Zip 或 WinRAR，无法读取 7z / RAR。")
        + rows([("自动下载安装", "官方组件 · 装到软件目录", "ok"),
                ("手动指定 7z.exe", "使用已有的解压程序", "")]),
        [("取消", ""), ("手动选择", ""), ("自动下载", "primary")],
        tone="warning", width=560)),
    ("未配置", "warning", "未指定游戏目录时，所有写入类操作的第一道拦截",
     dialog(
        "未配置游戏目录",
        p("请先在设置中指定 L4D2 安装目录。"),
        [("去设置", ""), ("知道了", "primary")],
        tone="warning", width=460)),
    ("退订提示", "info", "纯提示：列出已迁移的物品，由用户自行去 Steam 处理，界面不做任何跳转",
     dialog(
        "已迁移 8 个工坊物品",
        p("已移到 addons 顶层。请在 Steam 中取消这些物品的订阅，避免游戏再次下载。")
        + rows([("Koharu [Replace Ellis]", "3671024551", "muted"),
                ("VRC lime 甜点屋 打歌服", "3664792140", "muted"),
                ("雨衣替换 Ellis", "3639905428", "muted")]),
        [("知道了", "primary")],
        tone="info", width=560)),
    ("进行中", "busy", "组件安装等不可关闭但可取消的等待；进度可量化",
     dialog(
        "正在下载 7-Zip",
        p("下载并校验官方组件，完成后自动继续导入。")
        + '<div class="dlg-progress"><i style="width:62%"></i></div>'
        + '<div class="dlg-progress-meta">62% · 1.2 MB / 1.9 MB</div>',
        [("取消", "")],
        tone="busy", width=520)),
]

# ---------------------------------------------------------------- import stages

DROP = '''
<div class="drop-zone">
  <span class="drop-icon">＋</span>
  <span class="drop-title">选择压缩包</span>
  <span class="drop-hint">ZIP / 7z / RAR</span>
</div>'''

IMPORT_STAGES = [
    ("空态", "未选择文件", "只给一个拖放区；没有说明文字，也没有空列表占位。",
     panel("导入压缩包", DROP + '<div class="panel-actions"><button class="btn primary" disabled>加入模组库</button></div>')),
    ("解析中", "解压 + 读取 VPK", "拖放区收起为一行进度，避免占位跳动。",
     panel("导入压缩包",
           '<div class="inline-progress"><span class="inline-label">正在解析 VRC_lime.7z</span>'
           '<span class="inline-bar"><i style="width:34%"></i></span></div>'
           '<div class="inline-meta">34% · 正在解压</div>',
           '<span class="foot-note">可取消</span><button class="btn" disabled>加入模组库</button>')),
    ("解析完成", "可加入列表", "重复项直接显示为禁用行，不额外弹窗。",
     panel("可加入的模组",
           rows([("VRC lime 甜点屋 打歌服", "角色 / Ellis · 93.0 MB", ""),
                 ("【原神】菲谢尔 极夜真梦", "角色 / Ellis · 38.3 MB", ""),
                 ("VRC プラム Plum replace ellis", "已在库", "muted")])
           .replace('class="dlg-rows"', 'class="dlg-rows panel-rows"'),
           '<button class="btn primary">加入模组库（2）</button>')),
    ("正在导入", "写入模组库", "按钮进入不可用态，进度替换列表标题。",
     panel("正在导入 2 个模组",
           '<div class="inline-progress"><span class="inline-label">VRC lime 甜点屋 打歌服</span>'
           '<span class="inline-bar"><i style="width:50%"></i></span></div>'
           '<div class="inline-meta">1 / 2</div>',
           '<button class="btn primary" disabled>加入模组库（2）</button>')),
]

IMPORT_ERRORS = [
    ("格式不支持", "拖入非 ZIP / 7z / RAR 的文件",
     dialog(
        "无法导入",
        p("只支持 ZIP、7z 和 RAR。"),
        [("知道了", "primary")], tone="warning", width=440)),
    ("导入失败", "写入 mod 库时权限不足或磁盘已满",
     dialog(
        "导入失败",
        p("写入 addons 目录时失败：权限不足。")
        + rows([("VRC lime 甜点屋 打歌服", "未写入", "bad")]),
        [("重试", ""), ("关闭", "primary")], tone="danger", width=500)),
]

# ---------------------------------------------------------------- download stages

DL_STAGES = [
    ("空态", "等待链接", "输入框 + 一个解析按钮，没有其他提示。",
     panel("链接下载",
           '<div class="link-row"><span class="link-icon">🔗</span>'
           '<span class="link-placeholder">创意工坊链接或物品 ID</span>'
           '<button class="btn">解析</button></div>',
           '<button class="btn primary" disabled>开始下载</button>')),
    ("解析中", "读取工坊详情", "不可勾选，进度条表示解析而非下载。",
     panel("链接下载",
           '<div class="link-row"><span class="link-icon">🔗</span>'
           '<span class="link-value">https://steamcommunity.com/sharedfiles/filedetails/?id=3671024551</span>'
           '<button class="btn" disabled>解析</button></div>'
           '<div class="inline-progress"><span class="inline-label">正在读取工坊物品详情</span>'
           '<span class="inline-bar"><i style="width:28%"></i></span></div>',
           '<button class="btn primary" disabled>开始下载</button>')),
    ("展开合集", "识别到合集", "合集行单独显示，不参与勾选。",
     panel("链接下载",
           '<div class="link-row"><span class="link-icon">🔗</span>'
           '<span class="link-value">…/workshop/collection/3671</span>'
           '<button class="btn" disabled>解析</button></div>'
           + rows([("《Ellis 夏日合集》", "合集 · 2 个部件", "muted"),
                 ("[Gakuen IDOLM@STER] Fujita", "角色 / Ellis · 146.4 MB", ""),
                 ("雨衣替换 Ellis", "角色 / Ellis · 246.6 MB", "")])
           .replace('class="dlg-rows"', 'class="dlg-rows panel-rows"'),
           '<button class="btn primary">开始下载（2）</button>')),
    ("已在库", "全部重复", "不弹窗；列表内直接标记，按钮置灰。",
     panel("链接下载",
           rows([("[Gakuen IDOLM@STER] Fujita", "已在库", "muted"),
                 ("雨衣替换 Ellis", "已在库", "muted")])
           .replace('class="dlg-rows"', 'class="dlg-rows panel-rows"')
           + '<div class="inline-meta">所选模组均已在库</div>',
           '<button class="btn primary" disabled>开始下载</button>')),
    ("下载中", "逐项下载", "当前模组 + 总进度 + 常驻日志区。",
     panel("正在下载 2 个模组",
           '<div class="inline-progress"><span class="inline-label">[Gakuen IDOLM@STER] Fujita</span>'
           '<span class="inline-bar"><i style="width:72%"></i></span></div>'
           '<div class="inline-meta">第 1 / 2 项 · 146.4 MB · 失败自动切换 SteamCMD</div>'
           '<div class="log-box"><div>[20:14:02] 正在获取下载地址…</div>'
           '<div>[20:14:09] file_url 直连可用</div>'
           '<div>[20:14:31] 正在写入 addons</div></div>',
           '<button class="btn" disabled>取消</button><button class="btn primary" disabled>开始下载</button>')),
    ("完成", "全部成功", "结果直接在面板内，不再弹二次确认。",
     panel("已完成 2 个模组",
           rows([("[Gakuen IDOLM@STER] Fujita", "已启用", "ok"),
                 ("雨衣替换 Ellis", "已启用", "ok"),
                 ("VRC プラム Plum replace ellis", "同组已停用", "muted")])
           .replace('class="dlg-rows"', 'class="dlg-rows panel-rows"'),
           '<button class="btn">查看日志</button><button class="btn primary">完成</button>')),
    ("部分失败", "混合结果", "失败项内联展开错误原因。",
     panel("已完成 1 个，失败 1 个",
           rows([("[Gakuen IDOLM@STER] Fujita", "已启用", "ok"),
                 ("雨衣替换 Ellis", "连接超时", "bad")])
           .replace('class="dlg-rows"', 'class="dlg-rows panel-rows"'),
           '<button class="btn">查看日志</button><button class="btn primary">完成</button>')),
]

DL_ERRORS = [
    ("游戏运行中", "所有下载与导入前的统一前置拦截",
     dialog(
        "游戏运行中",
        p("请先关闭游戏，再下载导入模组。"),
        [("知道了", "primary")], tone="warning", width=440)),
    ("发现所属合集", "粘贴单个部件链接时，询问是否下载整个合集",
     dialog(
        "这是合集的一个部件",
        p("《死亡中心》是《死亡中心 · 重制版》的一个部件，共 3 个。")
        + rows([("已在库的部件", "1 个 · 直接归组", "ok"),
                ("待下载的部件", "2 个", "")]),
        [("只下载这一个", ""), ("下载整个合集", "primary")],
        tone="question", width=520)),
    ("链接不属于 L4D2", "工坊链接指向其它游戏时拒绝并说明",
     dialog(
        "无法下载",
        p("这个物品属于 Counter-Strike 2，不是 Left 4 Dead 2。")
        + rows([("跳过该物品", "1 个", "muted")]),
        [("知道了", "primary")], tone="danger", width=500)),
]

# ---------------------------------------------------------------- page

CSS = r"""
:root {
  --canvas: #08090b;
  --surface: #0f1114;
  --raised: #171b20;
  --sunken: #0b0d10;
  --line: #242930;
  --line-2: #303740;
  --text: #e8ebe5;
  --muted: #929a91;
  --dim: #6f7a6f;
  --accent: #d6f45d;
  --accent-ink: #151900;
  --ok: #9bb34e;
  --warn: #eab46f;
  --bad: #ff6854;
  --sans: "Noto Sans SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
  --mono: "Cascadia Mono", "Consolas", monospace;
  --serif: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background:
    radial-gradient(900px 500px at 70% -8%, rgba(214,244,93,.05), transparent 66%),
    var(--canvas);
  color: var(--text);
  font-family: var(--sans);
  font-size: 13px;
  line-height: 1.5;
}
.topbar {
  display: flex; align-items: center; gap: 18px;
  height: 48px; padding: 0 30px;
  border-bottom: 1px solid var(--line);
  background: rgba(8,9,11,.94);
  position: sticky; top: 0; z-index: 20;
}
.brand { display: flex; align-items: center; gap: 9px; font-family: var(--mono); font-size: 9px; letter-spacing: .12em; color: var(--dim); }
.brand img { width: 18px; height: 18px; }
.brand b { color: var(--text); font-weight: 400; }
.topbar nav { display: flex; gap: 16px; margin-left: 14px; }
.topbar nav a { color: var(--dim); font-size: 9.5px; text-decoration: none; }
.topbar nav a:hover { color: var(--accent); }
.topbar .right { margin-left: auto; font-family: var(--mono); font-size: 8.5px; color: var(--dim); }
.wrap { width: min(1400px, calc(100% - 60px)); margin: 0 auto; padding-bottom: 64px; }
.hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 40px; padding: 34px 0 26px; border-bottom: 1px solid var(--line); }
.hero .kicker { color: var(--accent); font-family: var(--mono); font-size: 9px; letter-spacing: .15em; }
.hero h1 { margin: 10px 0 0; font-family: var(--serif); font-size: 40px; font-weight: 900; letter-spacing: -.03em; }
.hero p { margin: 10px 0 0; max-width: 640px; color: var(--muted); font-size: 10.5px; line-height: 1.8; }
.hero .legend { display: flex; gap: 14px; flex-wrap: wrap; justify-content: flex-end; max-width: 420px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; color: var(--dim); font-size: 9px; }
.legend i { width: 6px; height: 6px; border-radius: 50%; }
.legend i.info { background: var(--accent); }
.legend i.warn { background: var(--warn); }
.legend i.bad { background: var(--bad); }

.section { padding-top: 34px; }
.section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; margin-bottom: 16px; }
.section-head .label { color: var(--accent); font-family: var(--mono); font-size: 8.5px; letter-spacing: .14em; }
.section-head h2 { margin: 6px 0 0; font-family: var(--serif); font-size: 26px; font-weight: 900; letter-spacing: -.02em; }
.section-head p { margin: 0 0 1px; max-width: 460px; color: var(--muted); font-size: 9.5px; line-height: 1.7; text-align: right; }

.grid { display: grid; gap: 16px; }
.grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }

.state-card {
  min-width: 0;
  border: 1px solid var(--line);
  background: var(--surface);
  display: flex; flex-direction: column;
}
.state-meta { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--line); }
.state-num { color: var(--accent); font-family: var(--mono); font-size: 8.5px; }
.state-name { color: var(--text); font-size: 11px; font-weight: 600; }
.state-state { margin-left: auto; color: var(--dim); font-family: var(--mono); font-size: 8px; }
.state-canvas {
  min-height: 210px;
  padding: 22px 18px;
  display: flex; align-items: center; justify-content: center;
  background:
    linear-gradient(rgba(255,255,255,.014) 1px, transparent 1px) 0 0 / 100% 24px,
    var(--sunken);
}
.state-note { margin: 0; padding: 9px 12px; border-top: 1px solid var(--line); color: var(--dim); font-size: 9px; line-height: 1.6; }

/* ---------- dialog ---------- */
.dlg {
  display: flex; flex-direction: column;
  background: var(--raised);
  border: 1px solid var(--line-2);
  border-radius: 7px;
  box-shadow: 0 18px 48px rgba(0,0,0,.45);
  overflow: hidden;
}
.dlg-head { display: flex; align-items: center; gap: 9px; padding: 13px 15px 0; }
.dlg-dot { width: 6px; height: 6px; border-radius: 50%; flex: none; background: var(--accent); }
.tone-warning .dlg-dot { background: var(--warn); }
.tone-danger .dlg-dot { background: var(--bad); }
.tone-busy .dlg-dot { background: var(--accent); animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: .3 } }
.dlg-head h4 { margin: 0; flex: 1; font-size: 13px; font-weight: 600; color: #f2f5ee; }
.dlg-close { background: none; border: 0; color: var(--dim); font-size: 11px; cursor: pointer; padding: 2px 4px; }
.dlg-close:hover { color: var(--text); }
.dlg-body { padding: 9px 15px 4px; }
.dlg-text { margin: 0; color: var(--muted); font-size: 10.5px; line-height: 1.75; }
.dlg-rows { margin-top: 10px; border-top: 1px solid var(--line); }
.dlg-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid #1c221e; }
.dlg-row:last-child { border-bottom: 0; }
.dlg-row-name { flex: 1; min-width: 0; color: #c8d1c2; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dlg-tag { flex: none; color: var(--dim); font-family: var(--mono); font-size: 8.5px; }
.dlg-tag.ok { color: var(--ok); }
.dlg-tag.warn { color: var(--warn); }
.dlg-tag.bad { color: var(--bad); }
.dlg-tag.muted { color: #5c665e; }
.dlg-check { display: flex; align-items: center; gap: 7px; margin-top: 11px; color: var(--muted); font-size: 9.5px; }
.dlg-check input { accent-color: var(--accent); width: 12px; height: 12px; }
.dlg-progress { height: 5px; margin-top: 12px; border-radius: 3px; background: #0a0c08; overflow: hidden; }
.dlg-progress i { display: block; height: 100%; background: var(--accent); border-radius: inherit; }
.dlg-progress-meta { margin-top: 6px; color: var(--dim); font-family: var(--mono); font-size: 8.5px; }
.dlg-foot { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 15px 14px; }
.dlg-btn {
  height: 30px; padding: 0 14px;
  border: 1px solid var(--line-2); border-radius: 5px;
  background: #141814; color: #b8c2b0;
  font-size: 10px; font-family: var(--sans); cursor: pointer;
}
.dlg-btn:hover { border-color: #46523a; color: #eef2e7; }
.dlg-btn.primary { border-color: var(--accent); background: var(--accent); color: var(--accent-ink); font-weight: 650; }
.dlg-btn.primary:hover { background: #e6ff7a; }
.dlg-btn.danger { border-color: #7a2f24; background: #241210; color: #ff9c8b; }
.dlg-btn.danger:hover { background: #30150f; border-color: #a03a2a; }

/* ---------- task panel (import / download) ---------- */
.panel {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
  overflow: hidden;
}
.panel-head {
  padding: 11px 13px;
  border-bottom: 1px solid var(--line);
  color: #c9d2c2; font-size: 10.5px; font-weight: 600;
}
.panel-body { padding: 12px 13px; }
.panel-rows { margin-top: 0; border-top: 0; }
.panel-foot {
  display: flex; justify-content: flex-end; align-items: center; gap: 8px;
  padding: 10px 13px; border-top: 1px solid var(--line);
}
.panel-actions { display: flex; justify-content: flex-end; margin-top: 12px; }
.btn {
  height: 30px; padding: 0 13px;
  border: 1px solid var(--line-2); border-radius: 5px;
  background: #141814; color: #b8c2b0; font-size: 10px; cursor: pointer;
}
.btn:hover { border-color: #46523a; color: #eef2e7; }
.btn.primary { border-color: var(--accent); background: var(--accent); color: var(--accent-ink); font-weight: 650; }
.btn[disabled] { opacity: .42; cursor: default; }
.foot-note { margin-right: auto; color: var(--dim); font-size: 9px; }

.drop-zone {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px;
  min-height: 108px; border: 1px dashed #46532b; border-radius: 6px;
  background: #10140c; cursor: pointer;
}
.drop-icon {
  width: 32px; height: 32px; display: grid; place-items: center;
  border: 1px solid #435329; border-radius: 50%; background: #1a2111;
  color: var(--accent); font-size: 15px;
}
.drop-title { color: #d6dfc6; font-size: 11.5px; font-weight: 600; }
.drop-hint { color: #6f7a6e; font-size: 9px; }

.inline-progress { display: flex; align-items: center; gap: 9px; margin-top: 10px; }
.inline-label { flex: none; max-width: 52%; color: #c4cfba; font-size: 9.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.inline-bar { flex: 1; height: 4px; border-radius: 3px; background: #1e261a; overflow: hidden; }
.inline-bar i { display: block; height: 100%; background: var(--accent); }
.inline-meta { margin-top: 6px; color: var(--dim); font-family: var(--mono); font-size: 8.5px; }

.link-row {
  display: flex; align-items: center; gap: 8px;
  height: 34px; padding: 0 5px 0 10px;
  border: 1px solid var(--line); border-radius: 5px;
  background: #0c0f0c;
}
.link-icon { font-size: 10px; opacity: .6; }
.link-placeholder { flex: 1; color: #5f6a5e; font-size: 10px; }
.link-value { flex: 1; color: #c2cdb8; font-family: var(--mono); font-size: 8.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.log-box {
  margin-top: 10px; padding: 8px 9px;
  border: 1px solid #232a1c; border-left: 2px solid #526329; border-radius: 4px;
  background: #090b06; color: #8d9880;
  font-family: var(--mono); font-size: 8px; line-height: 1.7;
}

.footer { margin-top: 34px; padding-top: 14px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; color: var(--dim); font-family: var(--mono); font-size: 8px; }
.footer a { color: var(--accent); text-decoration: none; }
@media (max-width: 1080px) {
  .grid.two, .grid.three { grid-template-columns: 1fr; }
  .wrap { width: calc(100% - 32px); }
  .hero { flex-direction: column; align-items: flex-start; gap: 16px; }
  .section-head { flex-direction: column; align-items: flex-start; gap: 8px; }
  .section-head p { text-align: left; }
}
"""


def build():
    dialogs = "".join(
        step(f"D{i+1:02d}", name, kind, purpose, mock, wide=False)
        for i, (name, kind, purpose, mock) in enumerate(DIALOGS)
    )

    import_flow = "".join(
        step(f"I{i+1:02d}", name, state, note, mock)
        for i, (name, state, note, mock) in enumerate(IMPORT_STAGES)
    )
    import_err = "".join(
        step(f"IE{i+1:02d}", name, "阻塞弹窗", purpose, mock)
        for i, (name, purpose, mock) in enumerate(IMPORT_ERRORS)
    )
    dl_flow = "".join(
        step(f"W{i+1:02d}", name, state, note, mock)
        for i, (name, state, note, mock) in enumerate(DL_STAGES)
    )
    dl_err = "".join(
        step(f"DE{i+1:02d}", name, "阻塞弹窗", purpose, mock)
        for i, (name, purpose, mock) in enumerate(DL_ERRORS)
    )

    body = f'''
<header class="topbar">
  <div class="brand"><img src="../assets/app-icon.png" alt=""><b>L4D2 // ARMORY</b><span>/ STATES</span></div>
  <nav><a href="preview.html">主界面</a><a href="states.html">状态板</a><a href="palettes.html">配色</a><a href="DESIGN_PRINCIPLES.md">原则</a></nav>
  <div class="right">BLACKSITE · 2026-11-19</div>
</header>

<main class="wrap">
  <div class="hero">
    <div>
      <div class="kicker">STATE BOARD / 全量状态</div>
      <h1>每一个弹窗，<br>每一个阶段。</h1>
      <p>覆盖 10 种阻塞弹窗、导入压缩包 4 个阶段 + 2 种错误、链接下载 7 个阶段 + 3 种阻塞弹窗。
         所有状态共用同一套语义与节奏，没有说明文字堆砌。</p>
    </div>
    <div class="legend">
      <span><i class="info"></i>普通 / 进度</span>
      <span><i class="warn"></i>需要用户行动</span>
      <span><i class="bad"></i>失败 / 不可逆</span>
    </div>
  </div>

  <section class="section">
    <div class="section-head">
      <div><div class="label">01 / BLOCKING DIALOGS</div><h2>阻塞弹窗</h2></div>
      <p>标题 + 一句话正文 + 右对齐按钮。危险操作用红色描边按钮，主操作永远在最右。</p>
    </div>
    <div class="grid two">{dialogs}</div>
  </section>

  <section class="section">
    <div class="section-head">
      <div><div class="label">02 / IMPORT FLOW</div><h2>导入压缩包</h2></div>
      <p>主按钮始终贴在列表下方，不做页面底部操作条。重复项在列表里直接禁用，不弹窗告知。</p>
    </div>
    <div class="grid two">{import_flow}</div>
    <div class="grid two" style="margin-top:16px">{import_err}</div>
  </section>

  <section class="section">
    <div class="section-head">
      <div><div class="label">03 / DOWNLOAD FLOW</div><h2>链接下载</h2></div>
      <p>解析与下载是两个进度语义：解析时不可勾选，下载时逐项推进并显示当前模组。</p>
    </div>
    <div class="grid two">{dl_flow}</div>
    <div class="grid three" style="margin-top:16px">{dl_err}</div>
  </section>

  <div class="footer">
    <span>L4D2 MOD MANAGER · STATE BOARD</span>
    <span><a href="preview.html">主界面预览</a> · <a href="DESIGN_PRINCIPLES.md">设计原则</a></span>
  </div>
</main>
'''

    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>L4D2 Mod Manager · 全量状态板</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
'''
    out = ROOT / "states.html"
    out.write_text(html, encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    build()
