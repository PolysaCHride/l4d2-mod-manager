# -*- coding: utf-8 -*-
"""Build the five visual directions for the L4D2 Mod Manager redesign review."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPRITE = (ROOT / "assets" / "icons.svg").read_text(encoding="utf-8")
FONT = '"Noto Sans SC", "Microsoft YaHei UI", "Segoe UI", sans-serif'
MONO = '"Cascadia Mono", "Consolas", monospace'
SERIF = '"Noto Serif SC", "Source Han Serif SC", "SimSun", serif'

MODS = [
    dict(img="mod1.webp", title="Koharu [Replace Ellis]", short="Koharu", cat="角色", item="Ellis",
         size="116.1 MB", date="2 天前", file="3668116708.vpk", on=False, tone="rose"),
    dict(img="mod2.webp", title="VRC lime 甜点屋 打歌服", short="VRC lime 甜点屋", cat="角色", item="Ellis",
         size="93.0 MB", date="4 天前", file="3664792140.vpk", on=False, tone="cyan"),
    dict(img="mod3.webp", title="VRC プラム Plum replace ellis", short="VRC Plum", cat="角色", item="Ellis",
         size="34.1 MB", date="本周", file="3659210344.vpk", on=True, tone="rose"),
    dict(img="mod4.webp", title="[Gakuen IDOLM@STER] Fujita", short="Gakuen IDOLM@STER", cat="角色", item="Ellis",
         size="146.4 MB", date="1 周前", file="3671024551.vpk", on=False, tone="gold"),
    dict(img="mod5.webp", title="【原神】菲谢尔 极夜真梦", short="菲谢尔 极夜真梦", cat="角色", item="Ellis",
         size="38.3 MB", date="2 周前", file="3648830117.vpk", on=False, tone="violet"),
    dict(img="mod6.webp", title="雨衣替换 Ellis", short="雨衣替换 Ellis", cat="角色", item="Ellis",
         size="246.6 MB", date="3 周前", file="3639905428.vpk", on=False, tone="blue"),
]

EXTRA_MODS = [
    dict(img="mod2.webp", title="AK-47 | 霓虹风暴", short="AK-47 | 霓虹风暴", cat="武器", item="AK-47",
         size="56.8 MB", date="今天", file="3680021947.vpk", on=True, tone="cyan"),
    dict(img="mod4.webp", title="M4A1 | 废土涂装", short="M4A1 | 废土涂装", cat="武器", item="M4A1",
         size="73.2 MB", date="3 天前", file="3675500132.vpk", on=False, tone="gold"),
    dict(img="mod6.webp", title="死亡中心 · 重制版", short="死亡中心 · 重制版", cat="地图", item="死亡中心",
         size="1.2 GB", date="上周", file="3674110256.vpk", on=True, tone="blue"),
    dict(img="mod5.webp", title="寂静岭 · 雾中街区", short="寂静岭 · 雾中街区", cat="地图", item="自定义",
         size="3.4 GB", date="2 周前", file="3661004421.vpk", on=False, tone="violet"),
    dict(img="mod4.webp", title="Coach | 警长制服", short="Coach | 警长制服", cat="角色", item="Coach",
         size="78.2 MB", date="5 天前", file="3678823160.vpk", on=False, tone="gold"),
    dict(img="mod2.webp", title="M60 | 旧日余晖", short="M60 | 旧日余晖", cat="武器", item="M60",
         size="91.5 MB", date="1 周前", file="3675311204.vpk", on=False, tone="cyan"),
]


def icon(name, cls="i"):
    return f'<svg class="{cls}" aria-hidden="true"><use href="#i-{name}"></use></svg>'


def switch(on=False, toast=True, label="启用"):
    attrs = ' data-switch'
    if toast:
        attrs += ' data-toast-on="已启用，同组旧模组已自动停用" data-toast-off="已停用"'
    return (f'<button type="button" class="switch {"on" if on else ""}" role="switch" '
            f'aria-checked="{"true" if on else "false"}" aria-label="{escape(label)}"{attrs}>'
            f'<span class="switch-knob"></span></button>')


def page(title, cls, css, body):
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · L4D2 Mod Manager</title>
<link rel="stylesheet" href="assets/base.css">
<style>{css}</style>
</head>
<body class="{cls}">
{SPRITE}
{body}
<script src="assets/base.js"></script>
</body>
</html>
"""


def card_v1(m, selected=False):
    state = "已启用" if m["on"] else "未启用"
    return f"""
<article class="mod-card{' is-selected' if selected else ''}" data-select tabindex="0"
  data-title="{escape(m['title'])}" data-meta="{escape(m['cat'] + ' / ' + m['item'])}"
  data-size="{escape(m['size'])}" data-date="{escape(m['date'])}" data-file="{escape(m['file'])}"
  data-img="assets/mods/{m['img']}" aria-label="{escape(m['title'])}">
  <div class="mod-thumb">
    <img src="assets/mods/{m['img']}" alt="{escape(m['title'])} 预览">
    <span class="mod-state {'on' if m['on'] else ''}">{state}</span>
    <button class="thumb-more" type="button" aria-label="更多操作" data-toast="更多操作">{icon('more')}</button>
  </div>
  <div class="mod-copy">
    <div class="mod-name">{escape(m['title'])}</div>
    <div class="mod-sub">{escape(m['cat'])} <span>/</span> {escape(m['item'])}</div>
    <div class="mod-foot"><span>{escape(m['size'])}</span><span class="mod-date">{escape(m['date'])}</span></div>
  </div>
</article>"""


def card_v2(m, selected=False, index=1):
    return f"""
<article class="poster-card{' is-selected' if selected else ''}" data-select tabindex="0"
  data-title="{escape(m['title'])}" data-meta="{escape(m['cat'] + ' / ' + m['item'])}"
  data-size="{escape(m['size'])}" data-date="{escape(m['date'])}" data-file="{escape(m['file'])}"
  data-img="assets/mods/{m['img']}" aria-label="{escape(m['title'])}">
  <div class="poster-image">
    <img src="assets/mods/{m['img']}" alt="{escape(m['title'])} 预览">
    <span class="poster-index">{index:02d}</span>
    {'<span class="stamp">使用中</span>' if m['on'] else ''}
  </div>
  <div class="poster-copy">
    <h3>{escape(m['title'])}</h3>
    <p>{escape(m['cat'])} <span>·</span> {escape(m['item'])} <span>·</span> {escape(m['size'])}</p>
    <div class="poster-foot">
      <span class="poster-state {'on' if m['on'] else ''}"><i></i>{'已启用' if m['on'] else '未启用'}</span>
      <span class="poster-date">{escape(m['date'])}</span>
      {switch(m['on'], label='切换 %s' % m['title'])}
    </div>
  </div>
</article>"""


# ---------------------------------------------------------------- V1 BLACKSITE
V1_CSS = r"""
:root {
  --bg: #08090b;
  --panel: #0f1114;
  --panel-2: #13161a;
  --panel-3: #171b20;
  --line: #242930;
  --line-2: #303740;
  --text: #e8ebe5;
  --muted: #929a91;
  --dim: #667067;
  --accent: #d6f45d;
  --accent-2: #b8d947;
  --accent-ink: #151900;
  --danger: #ff6854;
  --amber: #eab46f;
  --focus: #d6f45d;
  --selection: rgba(214, 244, 93, .25);
}
body.v1 {
  background: #050607;
  color: var(--text);
  font-family: "Noto Sans SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
}
.v1 .app {
  height: 100vh;
  background:
    radial-gradient(900px 500px at 72% -10%, rgba(214,244,93,.045), transparent 65%),
    var(--bg);
  display: flex;
  flex-direction: column;
  min-width: 1180px;
}
.v1 .topbar {
  height: 56px;
  flex: none;
  display: flex;
  align-items: center;
  padding: 0 18px 0 16px;
  border-bottom: 1px solid var(--line);
  background: rgba(9, 11, 13, .96);
  gap: 22px;
}
.v1 .brand { display: flex; align-items: center; gap: 10px; width: 204px; flex: none; }
.v1 .brand img { width: 28px; height: 28px; filter: saturate(.7) contrast(1.06); }
.v1 .brand-name {
  font-family: "Bahnschrift SemiBold", "Segoe UI", sans-serif;
  font-size: 15px;
  letter-spacing: .16em;
  line-height: 1;
  color: #f1f4eb;
}
.v1 .brand-sub {
  margin-top: 4px;
  font-family: "Cascadia Mono", monospace;
  font-size: 9px;
  letter-spacing: .18em;
  color: var(--dim);
}
.v1 .top-search {
  display: flex;
  align-items: center;
  gap: 9px;
  width: min(370px, 31vw);
  height: 32px;
  padding: 0 10px;
  color: var(--dim);
  border: 1px solid #262c33;
  border-radius: 4px;
  background: #0c0e11;
  transition: border-color .16s ease, background .16s ease;
}
.v1 .top-search:hover { border-color: #3b444d; background: #0f1216; }
.v1 .top-search input {
  flex: 1 1 auto;
  width: auto;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  font-size: 12px;
}
.v1 .top-search input::placeholder { color: #626b65; }
.v1 .top-search .i { width: 15px; height: 15px; color: #7b857d; }
.v1 .top-search .kbd { margin-left: auto; }
.v1 .top-actions { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.v1 .game-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid #2b312d;
  border-radius: 3px;
  color: #9aa398;
  font-size: 11px;
  letter-spacing: .02em;
  white-space: nowrap;
}
.v1 .game-status .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #59615a; box-shadow: 0 0 0 3px rgba(89,97,90,.1);
}
.v1 .icon-button {
  position: relative;
  width: 30px; height: 30px;
  display: grid; place-items: center;
  border: 1px solid transparent;
  border-radius: 4px;
  color: #858e87;
}
.v1 .icon-button:hover { background: #161a1f; border-color: #2a3037; color: var(--text); }
.v1 .icon-button .notif {
  position: absolute; top: 4px; right: 3px;
  min-width: 13px; height: 13px; padding: 0 3px;
  display: grid; place-items: center;
  border-radius: 7px; background: var(--danger); color: #1b0b08;
  font-family: "Cascadia Mono", monospace; font-size: 8px; font-weight: 700;
}
.v1 .avatar {
  width: 28px; height: 28px; margin-left: 2px;
  border-radius: 50%;
  background: linear-gradient(145deg, #cadb72, #6e8338);
  color: #1a1c0c;
  font-family: "Bahnschrift", sans-serif;
  font-size: 12px; font-weight: 700;
  display: grid; place-items: center;
  border: 1px solid #d9ed8b;
}
.v1 .body { min-height: 0; flex: 1; display: flex; }
.v1 .rail {
  width: 68px; flex: none;
  padding: 16px 8px 12px;
  border-right: 1px solid var(--line);
  background: #0a0c0f;
  display: flex; flex-direction: column;
}
.v1 .rail-nav { display: flex; flex-direction: column; gap: 5px; }
.v1 .rail-button {
  position: relative;
  height: 56px;
  border-radius: 4px;
  color: #707a72;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 10px;
  letter-spacing: .04em;
  transition: color .16s ease, background .16s ease;
}
.v1 .rail-button .i { width: 18px; height: 18px; }
.v1 .rail-button:hover { color: #cbd2c7; background: #111419; }
.v1 .rail-button.active { color: var(--accent); background: #141a0d; }
.v1 .rail-button.active::before {
  content: "";
  position: absolute; left: -8px; top: 13px; bottom: 13px;
  width: 2px; border-radius: 2px; background: var(--accent);
}
.v1 .rail-spacer { flex: 1; }
.v1 .rail-utility {
  width: 100%;
  height: 55px;
  border: 1px solid #2d3521;
  border-radius: 4px;
  color: #c3d58e;
  background: #10140b;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 4px;
  font-size: 10px; line-height: 1.25;
}
.v1 .rail-utility:hover { border-color: #536b1f; background: #151b0d; color: var(--accent); }
.v1 .rail-utility .i { width: 16px; height: 16px; }
.v1 .rail-settings { margin-top: 6px; }
.v1 .filters {
  width: 256px; flex: none;
  border-right: 1px solid var(--line);
  background: var(--panel);
  padding: 18px 14px 14px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.v1 .eyebrow {
  font-family: "Cascadia Mono", monospace;
  font-size: 9px;
  letter-spacing: .17em;
  color: #6f7a6c;
  text-transform: uppercase;
}
.v1 .filter-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 14px; }
.v1 .filter-head h2 {
  margin: 4px 0 0;
  font-size: 20px;
  font-weight: 650;
  letter-spacing: -.02em;
  color: #f0f2ec;
}
.v1 .filter-head .total {
  font-family: "Cascadia Mono", monospace;
  font-size: 11px;
  color: #80897e;
}
.v1 .lib-search {
  display: flex; align-items: center; gap: 8px;
  height: 33px; padding: 0 9px;
  border: 1px solid #292f36;
  border-radius: 4px;
  background: #0b0d10;
  color: #6f7a70;
}
.v1 .lib-search input { width: 100%; min-width: 0; outline: 0; border: 0; background: transparent; font-size: 11.5px; }
.v1 .lib-search input::placeholder { color: #5e6860; }
.v1 .segmented {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 2px; margin: 11px 0 15px;
  padding: 2px; border: 1px solid #252b31; border-radius: 4px; background: #0b0d10;
}
.v1 .segmented button {
  height: 26px; border-radius: 2px;
  color: #737d74; font-size: 10.5px;
}
.v1 .segmented button.active { background: #20271a; color: var(--accent); }
.v1 .group-label {
  display: flex; align-items: center; justify-content: space-between;
  margin: 0 3px 6px;
  font-family: "Cascadia Mono", monospace;
  font-size: 9px; letter-spacing: .12em; color: #626c65;
  text-transform: uppercase;
}
.v1 .filter-list { display: flex; flex-direction: column; gap: 1px; }
.v1 .filter-row {
  display: flex; align-items: center; gap: 8px;
  height: 30px; padding: 0 7px;
  border-radius: 3px; color: #89938a; font-size: 11.5px;
  text-align: left;
}
.v1 .filter-row .i { width: 15px; height: 15px; color: #626d63; }
.v1 .filter-row .count { margin-left: auto; font-family: "Cascadia Mono", monospace; font-size: 10px; color: #59635b; }
.v1 .filter-row:hover { background: #161a17; color: #d0d6ca; }
.v1 .filter-row.active { background: #1a2111; color: var(--accent); }
.v1 .filter-row.active .i { color: var(--accent); }
.v1 .filter-row.active .count { color: #a5b86a; }
.v1 .filter-row.item-row { height: 29px; padding-left: 8px; }
.v1 .filter-row.item-row.active { background: #1c2312; }
.v1 .filter-row .active-mark {
  margin-left: 6px; width: 5px; height: 5px; border-radius: 50%; background: var(--accent);
  box-shadow: 0 0 8px rgba(214,244,93,.5);
}
.v1 .filter-gap { height: 10px; }
.v1 .conflict-card {
  margin-top: auto;
  border: 1px solid #3b3320;
  border-radius: 4px;
  padding: 10px 10px 9px;
  background: #15130d;
}
.v1 .conflict-head { display: flex; align-items: center; gap: 7px; color: var(--amber); font-size: 10px; letter-spacing: .02em; }
.v1 .conflict-head .i { width: 14px; height: 14px; }
.v1 .conflict-title { margin: 7px 0 3px; color: #d7d3c2; font-size: 11px; }
.v1 .conflict-copy { color: #807b6c; font-size: 10px; line-height: 1.5; }
.v1 .conflict-link { margin-top: 7px; display: inline-flex; align-items: center; gap: 4px; color: #d7b775; font-size: 10px; }
.v1 .conflict-link:hover { color: #ffd48a; }
.v1 .storage {
  margin-top: 13px;
  padding: 10px 2px 0;
  border-top: 1px solid #252b26;
}
.v1 .storage-head { display: flex; justify-content: space-between; color: #6e786f; font-size: 9.5px; }
.v1 .storage-head strong { color: #aab4a2; font-family: "Cascadia Mono", monospace; font-weight: 400; }
.v1 .meter { height: 4px; margin: 8px 0 6px; border-radius: 4px; background: #222821; overflow: hidden; }
.v1 .meter span { display: block; height: 100%; width: 18%; background: #707e3f; border-radius: inherit; }
.v1 .storage-foot { font-family: "Cascadia Mono", monospace; color: #515b52; font-size: 9px; }

.v1 .main {
  min-width: 0; flex: 1;
  display: flex; flex-direction: column;
  background:
    linear-gradient(rgba(255,255,255,.015) 1px, transparent 1px) 0 0 / 100% 28px,
    #0b0d0f;
}
.v1 .main-head { padding: 21px 24px 0; }
.v1 .crumb { display: flex; align-items: center; gap: 7px; color: #606b62; font-size: 10.5px; letter-spacing: .04em; }
.v1 .crumb .i { width: 11px; height: 11px; color: #4f5a51; }
.v1 .crumb strong { color: #a9b2a7; font-weight: 500; }
.v1 .title-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-top: 10px; }
.v1 .title-row h1 {
  margin: 0;
  font-family: "Bahnschrift SemiBold", "Noto Sans SC", sans-serif;
  font-size: 28px; line-height: 1.15; font-weight: 600; letter-spacing: -.02em; color: #f0f3e9;
}
.v1 .title-row h1 span { margin-left: 8px; color: #778176; font-family: "Noto Sans SC", sans-serif; font-size: 15px; font-weight: 400; letter-spacing: 0; }
.v1 .title-row p { margin: 6px 0 0; color: #7a857b; font-size: 11px; }
.v1 .title-row p b { color: var(--accent); font-weight: 500; }
.v1 .head-actions { display: flex; align-items: center; gap: 8px; padding-bottom: 2px; }
.v1 .button {
  height: 32px; display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  padding: 0 12px;
  border: 1px solid #303729; border-radius: 3px;
  background: #11150e; color: #bdc7ad;
  font-size: 11px; letter-spacing: .02em; white-space: nowrap;
  transition: border-color .16s ease, background .16s ease, color .16s ease;
}
.v1 .button .i { width: 14px; height: 14px; }
.v1 .button:hover { border-color: #4a5731; background: #171d10; color: #f0f4e2; }
.v1 .button.primary { border-color: var(--accent); background: var(--accent); color: var(--accent-ink); font-weight: 650; }
.v1 .button.primary:hover { background: #e6ff7a; border-color: #e6ff7a; color: #111500; }
.v1 .button.subtle { border-color: #252b31; background: transparent; color: #778179; }
.v1 .toggle-group { display: inline-flex; padding: 2px; border: 1px solid #282f35; border-radius: 3px; background: #0a0c0f; }
.v1 .toggle-group button { width: 26px; height: 24px; display: grid; place-items: center; border-radius: 2px; color: #606b62; }
.v1 .toggle-group button.active { color: var(--accent); background: #1a2111; }
.v1 .toggle-group .i { width: 13px; height: 13px; }
.v1 .toolbar {
  min-height: 48px;
  margin-top: 2px; padding: 8px 24px;
  display: flex; align-items: center; gap: 8px;
}
.v1 .toolbar-meta { color: #606b62; font-size: 10px; }
.v1 .toolbar-meta strong { color: #b9c2b1; font-family: "Cascadia Mono", monospace; font-weight: 400; }
.v1 .toolbar-spacer { flex: 1; }
.v1 .select-wrap {
  height: 27px; display: flex; align-items: center; gap: 5px;
  padding: 0 8px; border: 1px solid #262c33; border-radius: 3px;
  color: #929c93; font-size: 10.5px;
}
.v1 .select-wrap .i { width: 12px; height: 12px; color: #667168; }
.v1 .chip {
  height: 27px; padding: 0 9px;
  display: inline-flex; align-items: center; gap: 5px;
  border: 1px solid transparent; border-radius: 3px;
  color: #7b867d; font-size: 10.5px;
}
.v1 .chip:hover { color: #c4ccc0; background: #13171b; }
.v1 .chip.active { color: var(--accent); border-color: #35431f; background: #161d0f; }
.v1 .chip .i { width: 12px; height: 12px; }
.v1 .grid-wrap { min-height: 0; flex: 1; padding: 4px 24px 18px; overflow-y: auto; }
.v1 .grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  align-content: start;
}
.v1 .mod-card {
  position: relative;
  min-width: 0;
  border: 1px solid #232a2b;
  border-radius: 4px;
  background: #101311;
  overflow: hidden;
  cursor: pointer;
  transition: border-color .16s ease, background .16s ease, transform .16s ease;
}
.v1 .mod-card:hover { border-color: #4b5931; background: #131711; transform: translateY(-1px); }
.v1 .mod-card.is-selected { border-color: #6d8330; background: #141a11; box-shadow: 0 0 0 1px rgba(214,244,93,.08) inset; }
.v1 .mod-card.is-selected::after {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 2px; background: var(--accent);
}
.v1 .mod-thumb { position: relative; aspect-ratio: 16 / 8.8; overflow: hidden; background: #0b0e0c; }
.v1 .mod-thumb::after {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0,0,0,.02) 45%, rgba(5,8,5,.5) 100%);
  pointer-events: none;
}
.v1 .mod-thumb img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.78) contrast(1.04); transition: transform .35s ease, filter .35s ease; }
.v1 .mod-card:hover .mod-thumb img { transform: scale(1.025); filter: saturate(.95) contrast(1.02); }
.v1 .mod-state {
  position: absolute; z-index: 1; left: 8px; top: 8px;
  height: 18px; padding: 0 6px;
  display: inline-flex; align-items: center;
  border: 1px solid rgba(255,255,255,.16); border-radius: 2px;
  color: rgba(255,255,255,.76); background: rgba(8,10,8,.58);
  backdrop-filter: blur(4px);
  font-family: "Cascadia Mono", monospace; font-size: 8px; letter-spacing: .05em;
}
.v1 .mod-state.on { border-color: var(--accent); background: var(--accent); color: #121700; font-weight: 700; }
.v1 .thumb-more {
  position: absolute; z-index: 2; right: 6px; top: 6px;
  width: 24px; height: 24px; display: grid; place-items: center;
  border-radius: 3px; color: rgba(255,255,255,.6); background: rgba(6,8,6,.38);
  opacity: 0; transition: opacity .16s ease, background .16s ease;
}
.v1 .mod-card:hover .thumb-more, .v1 .mod-card:focus-within .thumb-more { opacity: 1; }
.v1 .thumb-more:hover { background: rgba(0,0,0,.7); color: #fff; }
.v1 .thumb-more .i { width: 14px; height: 14px; }
.v1 .mod-copy { padding: 10px 10px 9px; }
.v1 .mod-name { color: #dce2d4; font-size: 12px; font-weight: 600; line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v1 .mod-sub { margin-top: 4px; color: #747f75; font-size: 10px; }
.v1 .mod-sub span { color: #434d46; margin: 0 3px; }
.v1 .mod-foot {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 8px; padding-top: 7px; border-top: 1px solid #202622;
  color: #657066; font-family: "Cascadia Mono", monospace; font-size: 9px;
}
.v1 .mod-date { color: #4f5a51; }
.v1 .grid-hint {
  display: flex; align-items: center; gap: 8px;
  margin: 16px 2px 0; color: #4f5a51; font-size: 10px;
}
.v1 .grid-hint .i { width: 13px; height: 13px; }
.v1 .grid-hint b { color: #7b867d; font-weight: 400; }
.v1 .library-summary {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px; margin: 18px 0 2px;
}
.v1 .summary-box {
  min-width: 0; padding: 11px 12px 10px;
  border: 1px solid #222925; border-radius: 3px; background: #0e1110;
}
.v1 .summary-box .eyebrow { color: #576158; font-size: 8px; }
.v1 .summary-value {
  margin-top: 5px; display: flex; align-items: baseline; gap: 5px;
  color: #c5cebd; font-family: "Bahnschrift", sans-serif; font-size: 17px; letter-spacing: .02em;
}
.v1 .summary-value span { color: #59645b; font-family: "Noto Sans SC", sans-serif; font-size: 9px; letter-spacing: 0; }
.v1 .summary-line { height: 3px; margin-top: 8px; border-radius: 3px; background: #202721; overflow: hidden; }
.v1 .summary-line i { display: block; height: 100%; border-radius: inherit; background: #70833d; }
.v1 .summary-line.amber i { background: #a47b3e; width: 22%; }
.v1 .summary-line.blue i { background: #4e6470; width: 38%; }
.v1 .inspector {
  width: 326px; flex: none;
  min-height: 0;
  border-left: 1px solid var(--line);
  background: #0c0e11;
  padding: 16px 16px 14px;
  display: flex; flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}
.v1 .inspector-head { display: flex; align-items: center; justify-content: space-between; }
.v1 .inspector-head .eyebrow { color: #59635b; }
.v1 .inspector-head .close { width: 22px; height: 22px; color: #59635b; display: grid; place-items: center; border-radius: 3px; }
.v1 .inspector-head .close:hover { color: #c1c9bc; background: #181d22; }
.v1 .preview {
  position: relative;
  aspect-ratio: 16 / 9.2;
  border: 1px solid #2b322d;
  border-radius: 3px;
  overflow: hidden;
  background: #090b09;
}
.v1 .preview img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.86) contrast(1.05); }
.v1 .preview::after {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 58%, rgba(5,7,5,.62));
}
.v1 .preview-tag {
  position: absolute; z-index: 1; left: 8px; bottom: 8px;
  font-family: "Cascadia Mono", monospace; font-size: 8px; letter-spacing: .08em; color: #d8e0cf;
}
.v1 .preview-play {
  position: absolute; z-index: 1; right: 8px; bottom: 8px;
  width: 25px; height: 25px; display: grid; place-items: center;
  border: 1px solid rgba(255,255,255,.2); border-radius: 50%;
  background: rgba(8,10,8,.5); color: #eef3e8;
}
.v1 .preview-play .i { width: 11px; height: 11px; }
.v1 .detail-title { margin: 0; color: #edf1e7; font-size: 17px; line-height: 1.35; font-weight: 600; letter-spacing: -.01em; }
.v1 .detail-meta { margin: 5px 0 0; color: #7b867d; font-size: 10.5px; }
.v1 .detail-meta span { color: #455046; margin: 0 4px; }
.v1 .status-card {
  padding: 11px;
  border: 1px solid #303a22;
  border-radius: 4px;
  background: #13170d;
}
.v1 .status-top { display: flex; align-items: center; justify-content: space-between; }
.v1 .status-label { display: flex; align-items: center; gap: 7px; color: #c8d8a0; font-size: 11px; }
.v1 .status-label .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px rgba(214,244,93,.55); }
.v1 .status-sub { margin-top: 5px; color: #707b64; font-size: 9.5px; line-height: 1.45; }
.v1 .switch {
  position: relative; width: 34px; height: 19px; flex: none;
  border: 1px solid #3d4730; border-radius: 10px;
  background: #22281c;
  transition: background .16s ease, border-color .16s ease;
}
.v1 .switch .switch-knob {
  position: absolute; top: 2px; left: 2px; width: 13px; height: 13px;
  border-radius: 50%; background: #758064; transition: transform .16s ease, background .16s ease;
}
.v1 .switch.on { background: var(--accent); border-color: var(--accent); }
.v1 .switch.on .switch-knob { transform: translateX(15px); background: #151900; }
.v1 .spec-list { display: flex; flex-direction: column; gap: 0; border-top: 1px solid #222824; }
.v1 .spec-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid #1d231f; }
.v1 .spec-row .k { color: #68736a; font-size: 10px; }
.v1 .spec-row .v { color: #aeb8ab; font-size: 10px; text-align: right; font-family: "Cascadia Mono", monospace; }
.v1 .group-panel { padding: 11px; border: 1px solid #252c27; border-radius: 4px; background: #0f1210; }
.v1 .group-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.v1 .group-head span { color: #a9b3a8; font-size: 10.5px; }
.v1 .group-head b { color: #707b6f; font-family: "Cascadia Mono", monospace; font-size: 9px; font-weight: 400; }
.v1 .group-mini { display: flex; align-items: center; gap: 7px; padding: 4px 0; color: #6f7a71; font-size: 10px; }
.v1 .group-mini img { width: 26px; height: 22px; object-fit: cover; border-radius: 2px; filter: saturate(.6); }
.v1 .group-mini.active { color: #b9ca8c; }
.v1 .group-mini .mini-check { margin-left: auto; color: var(--accent); }
.v1 .group-mini .mini-check .i { width: 12px; height: 12px; }
.v1 .inspector-actions { margin-top: auto; padding-top: 2px; display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
.v1 .action-button {
  height: 32px; display: flex; align-items: center; justify-content: center; gap: 6px;
  border: 1px solid #2b3329; border-radius: 3px; color: #9ba695; background: #11150f;
  font-size: 10px;
}
.v1 .action-button:hover { border-color: #475531; color: #e0e7d6; background: #161b11; }
.v1 .action-button.danger:hover { border-color: #633427; color: #ff9a8a; background: #1b0f0c; }
.v1 .action-button .i { width: 13px; height: 13px; }
.v1 .statusbar {
  height: 30px; flex: none;
  display: flex; align-items: center; gap: 15px;
  padding: 0 16px;
  border-top: 1px solid var(--line);
  background: #090b0d;
  color: #5f6a61;
  font-family: "Cascadia Mono", monospace;
  font-size: 9px;
}
.v1 .statusbar .ok { display: flex; align-items: center; gap: 6px; color: #8d9c70; }
.v1 .statusbar .ok .dot { width: 5px; height: 5px; border-radius: 50%; background: #9bb34e; }
.v1 .statusbar .spacer { flex: 1; }
.v1 .statusbar .path { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; max-width: 44%; }
@media (max-width: 1280px) {
  .v1 .inspector { width: 292px; }
  .v1 .filters { width: 236px; }
  .v1 .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
"""


def build_v1():
    cards = "\n".join(card_v1(m, selected=(m["title"] == MODS[2]["title"])) for m in MODS)
    selected = MODS[2]
    body = f"""
<div class="app">
  <header class="topbar">
    <div class="brand">
      <img src="assets/app-icon.png" alt="">
      <div>
        <div class="brand-name">L4D2 // ARMORY</div>
        <div class="brand-sub">LOCAL MOD COMMAND</div>
      </div>
    </div>
    <label class="top-search">
      {icon('search')}
      <input data-search placeholder="搜索模组、别名、标签、文件…" aria-label="搜索模组">
      <span class="kbd">Ctrl K</span>
    </label>
    <div class="top-actions">
      <span class="game-status"><span class="dot"></span>游戏未运行</span>
      <button class="icon-button" type="button" aria-label="通知" data-toast="2 条待处理提醒">{icon('bell')}<span class="notif">2</span></button>
      <button class="icon-button" type="button" aria-label="设置" data-toast="打开设置">{icon('settings')}</button>
      <button class="avatar" type="button" aria-label="账户">P</button>
    </div>
  </header>
  <div class="body">
    <nav class="rail" aria-label="主导航">
      <div class="rail-nav">
        <button class="rail-button" data-nav type="button">{icon('grid')}<span>全部</span></button>
        <button class="rail-button active" data-nav aria-current="page" type="button">{icon('users')}<span>角色</span></button>
        <button class="rail-button" data-nav type="button">{icon('crosshair')}<span>武器</span></button>
        <button class="rail-button" data-nav type="button">{icon('map')}<span>地图</span></button>
        <button class="rail-button" data-nav type="button">{icon('layers')}<span>合集</span></button>
      </div>
      <div class="rail-spacer"></div>
      <button class="rail-utility" type="button" data-toast="将扫描 workshop 与 addons 顶层">{icon('shield')}<span>一键<br>管理</span></button>
      <button class="rail-button rail-settings" type="button" data-toast="打开设置">{icon('settings')}<span>设置</span></button>
    </nav>
    <aside class="filters" aria-label="筛选">
      <div class="filter-head">
        <div><div class="eyebrow">LIBRARY INDEX</div><h2>模组库</h2></div>
        <span class="total">128 ITEMS</span>
      </div>
      <label class="lib-search">{icon('search')}<input data-search placeholder="筛选当前库…" aria-label="筛选当前库"></label>
      <div class="segmented" data-nav-group>
        <button class="active" type="button" data-nav>全部</button>
        <button type="button" data-nav>已启用 <span>43</span></button>
        <button type="button" data-nav>已停用 <span>85</span></button>
      </div>
      <div class="group-label"><span>分类</span><span>128</span></div>
      <div class="filter-list" data-nav-group>
        <button class="filter-row active" data-nav type="button">{icon('grid')}<span>全部模组</span><span class="count">128</span></button>
        <button class="filter-row" data-nav type="button">{icon('users')}<span>角色 / 幸存者</span><span class="count">42</span></button>
        <button class="filter-row" data-nav type="button">{icon('crosshair')}<span>武器</span><span class="count">36</span></button>
        <button class="filter-row" data-nav type="button">{icon('map')}<span>地图</span><span class="count">18</span></button>
        <button class="filter-row" data-nav type="button">{icon('layers')}<span>其他内容</span><span class="count">32</span></button>
      </div>
      <div class="filter-gap"></div>
      <div class="group-label"><span>物品 · 角色</span><span>42</span></div>
      <div class="filter-list" data-nav-group>
        <button class="filter-row item-row" data-nav type="button"><span>全部角色</span><span class="count">42</span></button>
        <button class="filter-row item-row active" data-nav type="button"><span>Ellis（艾利斯）</span><span class="count">6</span><span class="active-mark"></span></button>
        <button class="filter-row item-row" data-nav type="button"><span>Nick（尼克）</span><span class="count">5</span></button>
        <button class="filter-row item-row" data-nav type="button"><span>Coach（教练）</span><span class="count">4</span></button>
        <button class="filter-row item-row" data-nav type="button"><span>Bill（比尔）</span><span class="count">3</span></button>
        <button class="filter-row item-row" data-nav type="button"><span>Zoey（佐伊）</span><span class="count">3</span></button>
        <button class="filter-row item-row" data-nav type="button"><span>Louis（路易斯）</span><span class="count">3</span></button>
      </div>
      <div class="conflict-card">
        <div class="conflict-head">{icon('alert')} 互斥组提醒</div>
        <div class="conflict-title">1 个外观组存在旧启用项</div>
        <div class="conflict-copy">启用新模组时，同物品的旧模组会按规则自动停用。</div>
        <button class="conflict-link" type="button" data-toast="已显示冲突组：Ellis">查看冲突组 {icon('arrow-up-right')}</button>
      </div>
      <div class="storage">
        <div class="storage-head"><span>模组库占用</span><strong>4.8 GB</strong></div>
        <div class="meter"><span></span></div>
        <div class="storage-foot">78.2 GB FREE · 128 FILES</div>
      </div>
    </aside>
    <main class="main">
      <div class="main-head">
        <div class="crumb">模组库 {icon('chevron-right')} 角色 {icon('chevron-right')} <strong>Ellis</strong></div>
        <div class="title-row">
          <div>
            <h1>ELLIS <span>艾利斯</span></h1>
            <p><b>6</b> 个外观模组 · <b>1</b> 个已启用 · 同组自动互斥</p>
          </div>
          <div class="head-actions">
            <button class="button" type="button" data-toast="整理规则已准备好">{icon('sliders')}整理规则</button>
            <button class="button primary" type="button" data-toast="打开导入面板">{icon('plus')}导入模组</button>
          </div>
        </div>
      </div>
      <div class="toolbar">
        <span class="toolbar-meta"><strong>06</strong> / 06 项</span>
        <div class="toggle-group" aria-label="视图">
          <button class="active" type="button" aria-label="网格视图" data-toast="网格视图">{icon('grid')}</button>
          <button type="button" aria-label="列表视图" data-toast="列表视图">{icon('list')}</button>
        </div>
        <div class="toolbar-spacer"></div>
        <button class="chip active" type="button" data-chip>{icon('dot')}全部</button>
        <button class="chip" type="button" data-chip>已启用 1</button>
        <button class="chip" type="button" data-chip>未启用 5</button>
        <button class="select-wrap" type="button" data-toast="按最近添加排序">最近添加 {icon('chevron-down')}</button>
        <button class="icon-button" type="button" aria-label="刷新" data-toast="已重新扫描 addons">{icon('refresh')}</button>
      </div>
      <div class="grid-wrap scroll-y">
        <div class="grid">
          {cards}
        </div>
        <div class="library-summary">
          <div class="summary-box">
            <div class="eyebrow">SOURCE HEALTH</div>
            <div class="summary-value">128 <span>已纳管</span></div>
            <div class="summary-line"><i style="width:86%"></i></div>
          </div>
          <div class="summary-box">
            <div class="eyebrow">CONFLICT WATCH</div>
            <div class="summary-value">1 <span>个互斥组提醒</span></div>
            <div class="summary-line amber"><i></i></div>
          </div>
          <div class="summary-box">
            <div class="eyebrow">LIBRARY STORAGE</div>
            <div class="summary-value">4.8 GB <span>/ 可用 78.2 GB</span></div>
            <div class="summary-line blue"><i></i></div>
          </div>
        </div>
        <div class="grid-hint">{icon('keyboard')}<span>点击卡片查看详情，<b>Enter</b> 启用当前模组，<b>Space</b> 快速切换</span></div>
      </div>
    </main>
    <aside class="inspector" aria-label="模组详情">
      <div class="inspector-head">
        <div class="eyebrow">SELECTED / 001</div>
        <button class="close" type="button" aria-label="关闭详情" data-toast="详情面板可收起">{icon('x')}</button>
      </div>
      <div class="preview">
        <img data-detail-img src="assets/mods/{selected['img']}" alt="已选模组预览">
        <span class="preview-tag">VPK / THUMBNAIL</span>
        <button class="preview-play" type="button" aria-label="预览">{icon('play')}</button>
      </div>
      <div>
        <h2 class="detail-title" data-detail-title>{escape(selected['title'])}</h2>
        <p class="detail-meta"><span data-detail-meta>{selected['cat']} / {selected['item']}</span> <span>·</span> <span data-detail-size>{selected['size']}</span></p>
      </div>
      <div class="status-card">
        <div class="status-top">
          <div>
            <div class="status-label"><span class="dot"></span>已启用 · ACTIVE</div>
            <div class="status-sub">同组仅保留一个启用项<br>游戏内附加内容菜单已同步</div>
          </div>
          {switch(True, label='切换 VRC Plum 启用状态')}
        </div>
      </div>
      <div class="spec-list">
        <div class="spec-row"><span class="k">文件</span><span class="v" data-detail-file>{selected['file']}</span></div>
        <div class="spec-row"><span class="k">入库时间</span><span class="v">2026-11-07</span></div>
        <div class="spec-row"><span class="k">来源</span><span class="v">本地导入</span></div>
        <div class="spec-row"><span class="k">冲突组</span><span class="v">Ellis · 外观</span></div>
      </div>
      <div class="group-panel">
        <div class="group-head"><span>同组模组</span><b>1 / 6 ACTIVE</b></div>
        <div class="group-mini active"><img src="assets/mods/mod3.webp" alt=""><span>VRC Plum</span><span class="mini-check">{icon('check')}</span></div>
        <div class="group-mini"><img src="assets/mods/mod1.webp" alt=""><span>Koharu</span></div>
        <div class="group-mini"><img src="assets/mods/mod2.webp" alt=""><span>VRC lime</span></div>
      </div>
      <div class="inspector-actions">
        <button class="action-button" type="button" data-toast="已在资源管理器中显示">{icon('folder')}在文件夹中显示</button>
        <button class="action-button danger" type="button" data-toast="删除前会移动到回收站">{icon('trash')}移入回收站</button>
      </div>
    </aside>
  </div>
  <footer class="statusbar">
    <span class="ok"><span class="dot"></span>LOCAL LIBRARY CONNECTED</span>
    <span>128 MODS · 43 ENABLED</span>
    <span>GAME CLOSED</span>
    <span class="spacer"></span>
    <span class="path">E:\SteamLibrary\steamapps\common\Left 4 Dead 2\left4dead2\addons</span>
    <span>v1.2.1</span>
  </footer>
</div>
"""
    return page("01 BLACKSITE / 战术档案", "v1", V1_CSS, body)


# ---------------------------------------------------------------- V2 SAFEHOUSE
V2_CSS = r"""
:root {
  --paper: #f1eadc;
  --paper-2: #e9dfcd;
  --paper-3: #faf5e9;
  --ink: #1b1d16;
  --ink-soft: #33362b;
  --muted: #666856;
  --line: #cfc2ad;
  --line-strong: #9f937f;
  --red: #b52b1d;
  --red-deep: #8d1d13;
  --olive: #4d573c;
  --olive-soft: #dfe2cf;
  --focus: #b52b1d;
  --selection: rgba(181, 43, 29, .18);
}
body.v2 {
  background:
    radial-gradient(rgba(27,29,22,.052) .55px, transparent .65px) 0 0 / 4px 4px,
    var(--paper);
  color: var(--ink);
  font-family: "Noto Sans SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
}
.v2 .app { height: 100vh; display: flex; min-width: 1180px; background: var(--paper); }
.v2 .sidebar {
  width: 268px; flex: none;
  padding: 22px 16px 14px;
  border-right: 1px solid var(--line-strong);
  background:
    linear-gradient(90deg, rgba(255,255,255,.25), transparent 50%),
    var(--paper-2);
  display: flex; flex-direction: column;
  min-height: 0;
}
.v2 .brand { display: flex; align-items: flex-start; gap: 11px; padding: 0 6px 20px; border-bottom: 1px solid var(--line); }
.v2 .brand img { width: 34px; height: 34px; filter: grayscale(1) contrast(1.15); opacity: .84; }
.v2 .brand-main { min-width: 0; }
.v2 .brand-serif {
  font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
  font-size: 25px; font-weight: 900; line-height: 1.1; letter-spacing: .03em;
}
.v2 .brand-eng {
  margin-top: 4px;
  font-family: "Cascadia Mono", monospace;
  font-size: 8.5px; letter-spacing: .23em; color: var(--muted);
}
.v2 .brand-eng b { color: var(--red); font-weight: 700; }
.v2 .side-search {
  height: 34px; margin: 15px 0 14px;
  display: flex; align-items: center; gap: 8px;
  padding: 0 9px;
  border: 1px solid var(--line-strong); border-radius: 2px;
  background: var(--paper-3);
  color: var(--muted);
  box-shadow: 2px 2px 0 rgba(27,29,22,.05);
}
.v2 .side-search input { width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; font-size: 11px; color: var(--ink); }
.v2 .side-search input::placeholder { color: #98927f; }
.v2 .side-search .i { width: 14px; height: 14px; }
.v2 .section-label {
  display: flex; align-items: center; justify-content: space-between;
  margin: 4px 7px 6px;
  font-family: "Cascadia Mono", monospace;
  font-size: 8.5px; letter-spacing: .13em; color: #8a8a76;
  text-transform: uppercase;
}
.v2 .section-label span:last-child { font-family: "Noto Sans SC", sans-serif; letter-spacing: 0; }
.v2 .side-nav { display: flex; flex-direction: column; gap: 1px; }
.v2 .side-link {
  position: relative;
  height: 32px;
  display: flex; align-items: center; gap: 9px;
  padding: 0 8px;
  border-radius: 2px;
  color: #5d604f;
  font-size: 11.5px;
  text-align: left;
}
.v2 .side-link .i { width: 15px; height: 15px; color: #8a8c75; }
.v2 .side-link .n {
  margin-left: auto;
  font-family: "Cascadia Mono", monospace;
  font-size: 9.5px; color: #9b9985;
}
.v2 .side-link:hover { background: rgba(255,255,255,.36); color: var(--ink); }
.v2 .side-link.active { color: var(--red-deep); background: var(--paper-3); box-shadow: inset 2px 0 0 var(--red); font-weight: 600; }
.v2 .side-link.active .i { color: var(--red); }
.v2 .side-link.active .n { color: var(--red); }
.v2 .nav-divider { height: 1px; margin: 13px 7px; background: var(--line); }
.v2 .collections { display: flex; flex-direction: column; gap: 2px; }
.v2 .collection-row {
  display: flex; align-items: center; gap: 8px;
  height: 30px; padding: 0 8px;
  color: #626552; font-size: 11px; border-radius: 2px; text-align: left;
}
.v2 .collection-row:hover { background: rgba(255,255,255,.3); color: var(--ink); }
.v2 .collection-dot { width: 6px; height: 6px; border-radius: 50%; background: #b79a6e; }
.v2 .collection-row:nth-child(2) .collection-dot { background: var(--red); }
.v2 .collection-row:nth-child(3) .collection-dot { background: var(--olive); }
.v2 .collection-row .n { margin-left: auto; font-family: "Cascadia Mono", monospace; font-size: 9px; color: #9b9985; }
.v2 .side-spacer { flex: 1; }
.v2 .side-action {
  margin-top: 12px;
  padding: 11px 10px;
  border: 1px solid var(--line-strong);
  background: var(--paper-3);
  box-shadow: 3px 3px 0 rgba(27,29,22,.06);
}
.v2 .side-action-head { display: flex; align-items: center; gap: 7px; font-size: 11px; font-weight: 700; }
.v2 .side-action-head .i { width: 14px; height: 14px; color: var(--red); }
.v2 .side-action p { margin: 6px 0 9px; color: #777864; font-size: 9.5px; line-height: 1.55; }
.v2 .side-action button {
  height: 27px; padding: 0 9px;
  border: 1px solid var(--ink); background: var(--ink); color: var(--paper);
  font-size: 9.5px; letter-spacing: .02em;
}
.v2 .side-action button:hover { background: var(--red); border-color: var(--red); }
.v2 .side-foot {
  display: flex; align-items: center; justify-content: space-between;
  padding: 13px 7px 0;
  color: #898876; font-family: "Cascadia Mono", monospace; font-size: 8.5px;
}
.v2 .side-foot .online { display: inline-flex; align-items: center; gap: 5px; color: #5f6d49; }
.v2 .side-foot .online i { width: 5px; height: 5px; border-radius: 50%; background: #708b44; }
.v2 .content { min-width: 0; flex: 1; display: flex; flex-direction: column; }
.v2 .topbar {
  height: 62px; flex: none;
  display: flex; align-items: center; gap: 16px;
  padding: 0 30px;
  border-bottom: 1px solid var(--line);
  background: rgba(250,245,233,.38);
}
.v2 .topbar .crumb { display: flex; align-items: center; gap: 7px; color: #827f6a; font-size: 10.5px; white-space: nowrap; }
.v2 .topbar .crumb .i { width: 11px; height: 11px; color: #a6a18c; }
.v2 .topbar .crumb strong { color: var(--ink); font-weight: 600; }
.v2 .topbar-spacer { flex: 1; }
.v2 .scan-note { display: flex; align-items: center; gap: 6px; color: #777864; font-size: 9.5px; white-space: nowrap; }
.v2 .scan-note .i { width: 13px; height: 13px; }
.v2 .topbar .icon-button {
  width: 30px; height: 30px; display: grid; place-items: center;
  border: 1px solid transparent; border-radius: 2px; color: #7b7c68;
}
.v2 .topbar .icon-button:hover { border-color: var(--line-strong); color: var(--ink); background: rgba(255,255,255,.4); }
.v2 .topbar .launch {
  height: 33px; display: inline-flex; align-items: center; gap: 7px;
  padding: 0 14px;
  border: 1px solid var(--red-deep);
  background: var(--red); color: #fff3e6;
  font-size: 11px; font-weight: 650; letter-spacing: .04em;
  box-shadow: 3px 3px 0 rgba(107, 20, 12, .2);
}
.v2 .topbar .launch:hover { background: var(--red-deep); }
.v2 .topbar .launch .i { width: 14px; height: 14px; }
.v2 .page-body { min-height: 0; flex: 1; padding: 21px 30px 18px; display: flex; flex-direction: column; }
.v2 .page-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; }
.v2 .page-head .eyebrow {
  display: flex; align-items: center; gap: 8px;
  font-family: "Cascadia Mono", monospace; font-size: 9px; letter-spacing: .15em; color: var(--red);
}
.v2 .page-head .eyebrow::before { content: ""; width: 17px; height: 1px; background: var(--red); }
.v2 .page-head h1 {
  margin: 7px 0 0;
  font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
  font-size: 36px; line-height: 1.14; font-weight: 900; letter-spacing: .02em;
}
.v2 .page-head h1 span { margin-left: 10px; color: #8a8973; font-family: "Noto Sans SC", sans-serif; font-size: 13px; font-weight: 400; letter-spacing: .02em; }
.v2 .page-head p { margin: 7px 0 0; color: #666856; font-size: 10.5px; }
.v2 .page-head p b { color: var(--red-deep); font-weight: 700; }
.v2 .head-actions { display: flex; align-items: center; gap: 7px; padding-bottom: 3px; }
.v2 .ghost-button {
  height: 32px; display: inline-flex; align-items: center; gap: 6px;
  padding: 0 11px;
  border: 1px solid var(--line-strong);
  background: transparent; color: #5e604d;
  font-size: 10.5px;
}
.v2 .ghost-button:hover { border-color: var(--ink); color: var(--ink); background: rgba(255,255,255,.32); }
.v2 .ghost-button .i { width: 14px; height: 14px; }
.v2 .filterbar {
  display: flex; align-items: center; gap: 6px;
  min-height: 46px; margin-top: 10px; padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
}
.v2 .item-chip {
  height: 27px; padding: 0 9px;
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid transparent; border-radius: 2px;
  color: #666856; font-size: 10.5px;
}
.v2 .item-chip .n { font-family: "Cascadia Mono", monospace; font-size: 8.5px; color: #a09d87; }
.v2 .item-chip:hover { color: var(--ink); background: rgba(255,255,255,.37); }
.v2 .item-chip.active { border-color: var(--ink); background: var(--ink); color: var(--paper-3); }
.v2 .item-chip.active .n { color: #d2c9b7; }
.v2 .filterbar-spacer { flex: 1; }
.v2 .sort-button {
  display: inline-flex; align-items: center; gap: 5px;
  color: #777763; font-size: 10px; white-space: nowrap;
}
.v2 .sort-button:hover { color: var(--ink); }
.v2 .sort-button .i { width: 12px; height: 12px; }
.v2 .view-toggle { display: inline-flex; gap: 2px; padding-left: 9px; border-left: 1px solid var(--line); }
.v2 .view-toggle button { width: 25px; height: 24px; display: grid; place-items: center; color: #989782; border-radius: 2px; }
.v2 .view-toggle button.active { color: var(--ink); background: rgba(255,255,255,.48); }
.v2 .view-toggle .i { width: 13px; height: 13px; }
.v2 .grid-wrap { min-height: 0; flex: 1; overflow-y: auto; padding: 16px 2px 8px 0; }
.v2 .poster-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px 20px; align-content: start; }
.v2 .poster-card {
  min-width: 0; border: 1px solid var(--line-strong); border-radius: 1px;
  background: var(--paper-3);
  box-shadow: 4px 4px 0 rgba(96, 85, 64, .13);
  cursor: pointer;
  transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
}
.v2 .poster-card:hover { transform: translate(-1px, -1px); box-shadow: 6px 6px 0 rgba(96,85,64,.17); border-color: #6d6657; }
.v2 .poster-card.is-selected { border-color: var(--red); box-shadow: 4px 4px 0 rgba(181,43,29,.24); }
.v2 .poster-image { position: relative; aspect-ratio: 16 / 8.2; overflow: hidden; background: #d9cfbb; border-bottom: 1px solid var(--line-strong); }
.v2 .poster-image::after {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(20,18,14,.02) 50%, rgba(20,18,14,.28));
  pointer-events: none;
}
.v2 .poster-image img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.8) sepia(.05) contrast(1.03); transition: transform .35s ease, filter .35s ease; }
.v2 .poster-card:hover .poster-image img { transform: scale(1.022); filter: saturate(.96) sepia(.02); }
.v2 .poster-index {
  position: absolute; z-index: 1; left: 9px; top: 9px;
  font-family: "Cascadia Mono", monospace; font-size: 9px; color: rgba(255,250,238,.86);
  text-shadow: 0 1px 3px rgba(0,0,0,.38);
}
.v2 .stamp {
  position: absolute; z-index: 1; right: 10px; top: 12px;
  padding: 3px 6px 2px;
  border: 1.5px solid var(--red); color: var(--red-deep);
  font-family: "Noto Serif SC", "SimSun", serif; font-size: 11px; font-weight: 900; letter-spacing: .1em;
  transform: rotate(-4deg);
  background: rgba(250,245,233,.7);
  box-shadow: inset 0 0 0 1px rgba(250,245,233,.6);
}
.v2 .poster-copy { padding: 12px 13px 11px; }
.v2 .poster-copy h3 {
  margin: 0; color: var(--ink);
  font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
  font-size: 16.5px; line-height: 1.35; font-weight: 700;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.v2 .poster-copy p { margin: 5px 0 0; color: #6d6b58; font-size: 9.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v2 .poster-copy p span { color: #b6ab96; margin: 0 3px; }
.v2 .poster-foot {
  display: flex; align-items: center; gap: 8px;
  margin-top: 9px; padding-top: 8px; border-top: 1px dashed var(--line);
}
.v2 .poster-state { display: inline-flex; align-items: center; gap: 5px; color: #6d6b58; font-size: 9px; }
.v2 .poster-state i { width: 5px; height: 5px; border: 1px solid #99937f; border-radius: 50%; }
.v2 .poster-state.on { color: var(--red-deep); font-weight: 700; }
.v2 .poster-state.on i { border-color: var(--red); background: var(--red); }
.v2 .poster-date { margin-left: auto; color: #8b8574; font-family: "Cascadia Mono", monospace; font-size: 8.5px; }
.v2 .switch {
  position: relative; width: 30px; height: 17px; flex: none;
  border: 1px solid #978e7a; border-radius: 10px; background: transparent;
  transition: background .16s ease, border-color .16s ease;
}
.v2 .switch .switch-knob {
  position: absolute; top: 2px; left: 2px; width: 11px; height: 11px;
  border: 1px solid #8e8572; border-radius: 50%; background: var(--paper-3);
  transition: transform .16s ease, background .16s ease, border-color .16s ease;
}
.v2 .switch.on { border-color: var(--red); background: var(--red); }
.v2 .switch.on .switch-knob { transform: translateX(13px); background: #fff5e6; border-color: #fff5e6; }
.v2 .bottom-note {
  flex: none; display: flex; align-items: center; gap: 7px;
  min-height: 31px; color: #78745f; font-size: 9px;
}
.v2 .bottom-note .i { width: 12px; height: 12px; color: #a7a08a; }
.v2 .bottom-note b { color: #6d6f58; font-weight: 500; }
.v2 .statusbar {
  height: 28px; flex: none; display: flex; align-items: center; gap: 14px;
  padding: 0 30px; border-top: 1px solid var(--line-strong);
  color: #92917c; font-family: "Cascadia Mono", monospace; font-size: 8px;
}
.v2 .statusbar .path { margin-left: auto; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; max-width: 45%; }
@media (max-width: 1220px) {
  .v2 .poster-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .v2 .page-head h1 { font-size: 32px; }
}
"""


def build_v2():
    cards = "\n".join(card_v2(m, selected=(m["title"] == MODS[2]["title"]), index=i + 1)
                      for i, m in enumerate(MODS))
    body = f"""
<div class="app">
  <aside class="sidebar">
    <div class="brand">
      <img src="assets/app-icon.png" alt="">
      <div class="brand-main">
        <div class="brand-serif">安全屋</div>
        <div class="brand-eng">SAFEHOUSE <b>/</b> MOD ARCHIVE</div>
      </div>
    </div>
    <label class="side-search">{icon('search')}<input data-search placeholder="搜索模组或别名…" aria-label="搜索模组"></label>
    <div class="side-nav" data-nav-group>
      <div class="section-label"><span>浏览 / LIBRARY</span><span>128</span></div>
      <button class="side-link" data-nav type="button">{icon('grid')}<span>全部模组</span><span class="n">128</span></button>
      <button class="side-link active" data-nav type="button">{icon('users')}<span>角色 / 幸存者</span><span class="n">42</span></button>
      <button class="side-link" data-nav type="button">{icon('alert')}<span>特感</span><span class="n">16</span></button>
      <button class="side-link" data-nav type="button">{icon('crosshair')}<span>武器</span><span class="n">36</span></button>
      <button class="side-link" data-nav type="button">{icon('crosshair')}<span>近战</span><span class="n">17</span></button>
      <button class="side-link" data-nav type="button">{icon('map')}<span>地图</span><span class="n">18</span></button>
      <button class="side-link" data-nav type="button">{icon('box')}<span>其他内容</span><span class="n">32</span></button>
    </div>
    <div class="nav-divider"></div>
    <div class="section-label"><span>收藏夹 / COLLECTIONS</span><span>6</span></div>
    <div class="collections">
      <button class="collection-row" type="button"><span class="collection-dot"></span><span>周末混战</span><span class="n">12</span></button>
      <button class="collection-row" type="button"><span class="collection-dot"></span><span>霓虹夜</span><span class="n">8</span></button>
      <button class="collection-row" type="button"><span class="collection-dot"></span><span>原版增强</span><span class="n">21</span></button>
    </div>
    <div class="side-spacer"></div>
    <div class="side-action">
      <div class="side-action-head">{icon('shield')}让库保持干净</div>
      <p>扫描 workshop 与 addons，把散落的模组收进同一个档案。</p>
      <button type="button" data-toast="开始扫描并纳管现有模组">扫描现有模组</button>
    </div>
    <div class="side-foot"><span class="online"><i></i>本地库在线</span><span>v1.2.1</span></div>
  </aside>
  <main class="content">
    <header class="topbar">
      <div class="crumb">全部模组 {icon('chevron-right')} 角色 {icon('chevron-right')} <strong>Ellis</strong></div>
      <div class="topbar-spacer"></div>
      <span class="scan-note">{icon('clock-rewind')}上次扫描 2 分钟前</span>
      <button class="icon-button" type="button" aria-label="刷新" data-toast="已重新扫描 addons">{icon('refresh')}</button>
      <button class="icon-button" type="button" aria-label="设置" data-toast="打开设置">{icon('settings')}</button>
      <button class="launch" type="button" data-toast="正在启动 Left 4 Dead 2">{icon('play')}启动游戏</button>
    </header>
    <div class="page-body">
      <div class="page-head">
        <div>
          <div class="eyebrow">COLLECTION / 角色外观</div>
          <h1>Ellis 的衣橱 <span>Ellis / 艾利斯</span></h1>
          <p><b>6</b> 个模组，<b>1</b> 个正在使用 · 同一物品只保留一个启用项</p>
        </div>
        <div class="head-actions">
          <button class="ghost-button" type="button" data-toast="整理规则已准备好">{icon('sliders')}整理规则</button>
          <button class="ghost-button" type="button" data-toast="打开导入面板">{icon('plus')}导入模组</button>
        </div>
      </div>
      <div class="filterbar">
        <button class="item-chip active" type="button" data-chip>Ellis <span class="n">6</span></button>
        <button class="item-chip" type="button" data-chip>Nick <span class="n">5</span></button>
        <button class="item-chip" type="button" data-chip>Coach <span class="n">4</span></button>
        <button class="item-chip" type="button" data-chip>Bill <span class="n">3</span></button>
        <button class="item-chip" type="button" data-chip>Zoey <span class="n">3</span></button>
        <div class="filterbar-spacer"></div>
        <button class="sort-button" type="button" data-toast="当前按最近添加排序">最近添加 {icon('chevron-down')}</button>
        <div class="view-toggle" aria-label="视图">
          <button class="active" type="button" aria-label="网格视图" data-toast="网格视图">{icon('grid')}</button>
          <button type="button" aria-label="列表视图" data-toast="列表视图">{icon('list')}</button>
        </div>
      </div>
      <div class="grid-wrap scroll-y">
        <div class="poster-grid">{cards}</div>
      </div>
      <div class="bottom-note">{icon('alert')}互斥规则已开启：启用新外观时，<b>同组旧模组会自动停用</b>，游戏内菜单同步更新。</div>
    </div>
    <footer class="statusbar">
      <span>128 MODS · 43 ENABLED</span><span>LIBRARY HEALTH: GOOD</span>
      <span class="path">E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2\\left4dead2\\addons</span>
    </footer>
  </main>
</div>
"""
    return page("02 SAFEHOUSE / 安全屋", "v2", V2_CSS, body)


def card_v3(m, selected=False):
    return f"""
<article class="workshop-card{' is-selected' if selected else ''}" data-select tabindex="0"
  data-title="{escape(m['title'])}" data-meta="{escape(m['cat'] + ' / ' + m['item'])}"
  data-size="{escape(m['size'])}" data-date="{escape(m['date'])}" data-file="{escape(m['file'])}"
  data-img="assets/mods/{m['img']}" aria-label="{escape(m['title'])}">
  <div class="workshop-art">
    <img src="assets/mods/{m['img']}" alt="{escape(m['title'])} 预览">
    <span class="workshop-live {'on' if m['on'] else ''}">{'ACTIVE' if m['on'] else 'READY'}</span>
  </div>
  <div class="workshop-copy">
    <h3>{escape(m['title'])}</h3>
    <div class="workshop-meta"><span>{escape(m['size'])}</span><span class="dot"></span><span>{escape(m['date'])}</span></div>
    <div class="workshop-foot">
      <span class="workshop-cat">{escape(m['cat'])} / {escape(m['item'])}</span>
      {switch(m['on'], label='切换 %s' % m['title'])}
    </div>
  </div>
</article>"""


# ---------------------------------------------------------------- V3 WORKSHOP
V3_CSS = r"""
:root {
  --night: #08121a;
  --deep: #0d1b25;
  --panel: #122430;
  --panel-2: #172b39;
  --panel-3: #1b3342;
  --line: #223845;
  --line-2: #305164;
  --text: #dbe9f0;
  --muted: #89a4b4;
  --dim: #5f7e90;
  --cyan: #6bc7f2;
  --cyan-2: #3e9ac6;
  --green: #a8d414;
  --ink: #061016;
  --danger: #f06a55;
  --focus: #6bc7f2;
  --selection: rgba(107, 199, 242, .25);
}
body.v3 {
  background: var(--night);
  color: var(--text);
  font-family: "Noto Sans SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
}
.v3 .app {
  height: 100vh; min-width: 1180px;
  display: flex; flex-direction: column;
  background:
    radial-gradient(900px 420px at 10% -12%, rgba(62,154,198,.12), transparent 68%),
    linear-gradient(180deg, #0c1922, #08121a 32%);
}
.v3 .topbar {
  height: 62px; flex: none;
  display: flex; align-items: center; gap: 24px;
  padding: 0 20px;
  border-bottom: 1px solid #1d3341;
  background: linear-gradient(180deg, #172b38, #10212c);
}
.v3 .brand { display: flex; align-items: center; gap: 10px; width: 212px; flex: none; }
.v3 .brand img { width: 29px; height: 29px; filter: saturate(.85) contrast(1.06); }
.v3 .brand-word {
  color: #e7f4fa; font-family: "Bahnschrift SemiBold", "Segoe UI", sans-serif;
  font-size: 16px; line-height: 1; letter-spacing: .12em;
}
.v3 .brand-sub { margin-top: 4px; color: #7997a8; font-family: "Cascadia Mono", monospace; font-size: 7.5px; letter-spacing: .18em; }
.v3 .tabs { display: flex; align-self: stretch; align-items: center; gap: 2px; }
.v3 .tab {
  height: 100%; padding: 0 14px;
  display: flex; align-items: center; gap: 7px;
  color: #88a3b2; font-size: 11px; letter-spacing: .04em;
  border-bottom: 2px solid transparent;
}
.v3 .tab:hover { color: #e0eef4; background: rgba(255,255,255,.025); }
.v3 .tab.active { color: #f0f8fb; border-bottom-color: var(--cyan); }
.v3 .tab .tab-badge {
  min-width: 15px; height: 15px; padding: 0 4px;
  display: grid; place-items: center;
  border-radius: 8px; background: #284557; color: #b9d2de;
  font-family: "Cascadia Mono", monospace; font-size: 8px;
}
.v3 .topbar-spacer { flex: 1; }
.v3 .top-search {
  width: 252px; height: 32px;
  display: flex; align-items: center; gap: 8px;
  padding: 0 9px;
  border: 1px solid #2b4657; border-radius: 3px;
  background: #0b1821;
  color: #7190a1;
}
.v3 .top-search input { flex: 1 1 auto; width: auto; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--text); font-size: 10.5px; }
.v3 .top-search input::placeholder { color: #607f90; }
.v3 .top-search .i { width: 14px; height: 14px; }
.v3 .steam-state {
  display: flex; align-items: center; gap: 6px;
  color: #8ba8b7; font-size: 9.5px; white-space: nowrap;
}
.v3 .steam-state i { width: 6px; height: 6px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 3px rgba(168,212,20,.1); }
.v3 .icon-button { width: 29px; height: 29px; display: grid; place-items: center; border-radius: 3px; color: #85a1b0; }
.v3 .icon-button:hover { background: #1a3040; color: #f1f8fb; }
.v3 .avatar {
  width: 28px; height: 28px; border-radius: 2px;
  display: grid; place-items: center;
  border: 1px solid #5a7f91;
  background: linear-gradient(145deg, #3f677b, #243d4c);
  color: #e6f3f7; font-family: "Bahnschrift", sans-serif; font-size: 11px;
}
.v3 .body { min-height: 0; flex: 1; display: flex; }
.v3 .content { min-width: 0; flex: 1; padding: 18px 22px 16px; display: flex; flex-direction: column; }
.v3 .hero {
  position: relative; flex: none; height: 208px;
  overflow: hidden; border: 1px solid #2b4b5c; border-radius: 3px;
  background: #12232e;
}
.v3 .hero-art { position: absolute; inset: 0; }
.v3 .hero-art img { width: 100%; height: 100%; object-fit: cover; object-position: center 28%; filter: saturate(.88) contrast(1.04); transform: scale(1.01); }
.v3 .hero::after {
  content: ""; position: absolute; inset: 0;
  background:
    linear-gradient(90deg, rgba(6,16,22,.96) 0%, rgba(8,20,28,.8) 42%, rgba(7,17,23,.14) 78%),
    linear-gradient(0deg, rgba(5,14,19,.74) 0%, transparent 55%);
}
.v3 .hero-copy { position: absolute; z-index: 1; left: 26px; bottom: 22px; max-width: 560px; }
.v3 .hero-eyebrow { display: flex; align-items: center; gap: 7px; color: #8ab3c6; font-family: "Cascadia Mono", monospace; font-size: 8.5px; letter-spacing: .14em; }
.v3 .hero-eyebrow i { width: 6px; height: 6px; border-radius: 50%; background: var(--cyan); }
.v3 .hero h1 {
  margin: 8px 0 0;
  color: #f0fafd;
  font-family: "Bahnschrift SemiBold", "Noto Sans SC", sans-serif;
  font-size: 31px; line-height: 1.15; font-weight: 600; letter-spacing: -.02em;
}
.v3 .hero h1 span { margin-left: 9px; color: #a8c7d5; font-family: "Noto Sans SC", sans-serif; font-size: 14px; font-weight: 300; letter-spacing: .02em; }
.v3 .hero p { margin: 7px 0 0; color: #a1bbc7; font-size: 10.5px; }
.v3 .hero p b { color: #dff7ff; font-weight: 500; }
.v3 .hero-chips { display: flex; gap: 6px; margin-top: 12px; }
.v3 .hero-chip {
  height: 21px; padding: 0 7px; display: inline-flex; align-items: center; gap: 5px;
  border: 1px solid rgba(145,194,214,.3); border-radius: 2px;
  background: rgba(7,19,26,.44); color: #b6d2dd;
  font-size: 8.5px;
}
.v3 .hero-chip .i { width: 11px; height: 11px; color: var(--green); }
.v3 .hero-actions { position: absolute; z-index: 1; right: 22px; bottom: 22px; display: flex; gap: 7px; }
.v3 .hero-button {
  height: 31px; padding: 0 11px; display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid rgba(175,222,239,.3); border-radius: 2px;
  background: rgba(7,19,26,.42); color: #d7ebf2; font-size: 10px;
  backdrop-filter: blur(4px);
}
.v3 .hero-button:hover { background: rgba(16,41,54,.8); border-color: #79c7e9; }
.v3 .hero-button.primary { border-color: var(--cyan); background: var(--cyan); color: #07131a; font-weight: 650; }
.v3 .hero-button.primary:hover { background: #9de0ff; border-color: #9de0ff; }
.v3 .hero-button .i { width: 13px; height: 13px; }
.v3 .toolbar { flex: none; min-height: 47px; display: flex; align-items: center; gap: 4px; }
.v3 .toolbar-tab {
  height: 27px; padding: 0 9px; display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid transparent; border-radius: 2px; color: #7796a7; font-size: 10px;
}
.v3 .toolbar-tab .n { color: #526f80; font-family: "Cascadia Mono", monospace; font-size: 8.5px; }
.v3 .toolbar-tab:hover { color: #d8eaf1; background: #132a37; }
.v3 .toolbar-tab.active { border-color: #375d71; background: #173241; color: #eef8fb; }
.v3 .toolbar-tab.active .n { color: #a9c9d7; }
.v3 .toolbar-spacer { flex: 1; }
.v3 .toolbar-button { display: inline-flex; align-items: center; gap: 5px; color: #7e9dac; font-size: 9.5px; }
.v3 .toolbar-button:hover { color: #d8eaf1; }
.v3 .toolbar-button .i { width: 12px; height: 12px; }
.v3 .view-toggle { display: inline-flex; padding: 2px; margin-left: 8px; border: 1px solid #274352; border-radius: 2px; background: #0b1a23; }
.v3 .view-toggle button { width: 23px; height: 21px; display: grid; place-items: center; border-radius: 1px; color: #62808f; }
.v3 .view-toggle button.active { color: var(--cyan); background: #1b3948; }
.v3 .view-toggle .i { width: 12px; height: 12px; }
.v3 .grid-wrap { min-height: 0; flex: 1; overflow-y: auto; padding: 0 1px 4px 0; }
.v3 .workshop-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; align-content: start; }
.v3 .workshop-card {
  min-width: 0; overflow: hidden;
  border: 1px solid #203a49; border-radius: 2px;
  background: #0d1d26;
  cursor: pointer;
  transition: border-color .16s ease, background .16s ease, transform .16s ease;
}
.v3 .workshop-card:hover { border-color: #3e6d84; background: #112631; transform: translateY(-1px); }
.v3 .workshop-card.is-selected { border-color: var(--cyan); box-shadow: 0 0 0 1px rgba(107,199,242,.13); }
.v3 .workshop-art { position: relative; aspect-ratio: 16 / 8.9; overflow: hidden; background: #0a151c; }
.v3 .workshop-art::after {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 56%, rgba(7,16,22,.55));
}
.v3 .workshop-art img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.79) contrast(1.03); transition: transform .35s ease, filter .35s ease; }
.v3 .workshop-card:hover .workshop-art img { transform: scale(1.035); filter: saturate(.95); }
.v3 .workshop-live {
  position: absolute; z-index: 1; left: 7px; bottom: 7px;
  height: 16px; padding: 0 5px;
  display: inline-flex; align-items: center;
  border: 1px solid rgba(176,212,224,.28); border-radius: 1px;
  background: rgba(7,16,22,.68);
  color: #a5c1cd; font-family: "Cascadia Mono", monospace; font-size: 7.5px; letter-spacing: .08em;
}
.v3 .workshop-live.on { background: var(--green); border-color: var(--green); color: #111700; font-weight: 700; }
.v3 .workshop-copy { padding: 9px 9px 8px; }
.v3 .workshop-copy h3 { margin: 0; color: #d9e8ee; font-size: 11px; line-height: 1.4; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v3 .workshop-meta { display: flex; align-items: center; gap: 5px; margin-top: 4px; color: #7191a1; font-family: "Cascadia Mono", monospace; font-size: 8px; }
.v3 .workshop-meta .dot { width: 2px; height: 2px; border-radius: 50%; background: #456676; }
.v3 .workshop-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 7px; padding-top: 7px; border-top: 1px solid #1b313d; }
.v3 .workshop-cat { color: #5f7f8f; font-size: 8.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v3 .switch {
  position: relative; width: 29px; height: 16px; flex: none;
  border: 1px solid #385767; border-radius: 9px; background: #1a303d;
}
.v3 .switch .switch-knob { position: absolute; top: 2px; left: 2px; width: 10px; height: 10px; border-radius: 50%; background: #7995a3; transition: transform .16s ease, background .16s ease; }
.v3 .switch.on { border-color: var(--green); background: var(--green); }
.v3 .switch.on .switch-knob { transform: translateX(13px); background: #111700; }
.v3 .add-card {
  min-height: 196px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 7px;
  border: 1px dashed #2f5264; border-radius: 2px;
  background: rgba(14,31,41,.5); color: #7292a1;
}
.v3 .add-card:hover { border-color: var(--cyan); color: #d5ecf5; background: rgba(22,51,66,.6); }
.v3 .add-icon { width: 32px; height: 32px; display: grid; place-items: center; border: 1px solid #355c6f; border-radius: 50%; color: var(--cyan); }
.v3 .add-icon .i { width: 15px; height: 15px; }
.v3 .add-card strong { color: #9db8c5; font-size: 10px; font-weight: 500; }
.v3 .add-card span { color: #5f7c8b; font-size: 8.5px; }
.v3 .side {
  width: 332px; flex: none;
  border-left: 1px solid #1f3744;
  background: #0b1921;
  padding: 17px 17px 14px;
  display: flex; flex-direction: column; gap: 13px;
  overflow-y: auto;
}
.v3 .side-head { display: flex; align-items: center; justify-content: space-between; }
.v3 .side-title { display: flex; align-items: center; gap: 8px; color: #d3e5ec; font-size: 12px; font-weight: 600; }
.v3 .side-title .i { width: 15px; height: 15px; color: var(--cyan); }
.v3 .live-tag { display: inline-flex; align-items: center; gap: 5px; color: #9dc96a; font-family: "Cascadia Mono", monospace; font-size: 7.5px; letter-spacing: .12em; }
.v3 .live-tag i { width: 5px; height: 5px; border-radius: 50%; background: var(--green); }
.v3 .sync-box { border: 1px solid #263e4b; border-radius: 2px; background: #0e202a; padding: 12px; }
.v3 .sync-main { display: flex; align-items: center; gap: 11px; }
.v3 .ring {
  width: 48px; height: 48px; border-radius: 50%; flex: none;
  background: conic-gradient(var(--cyan) 0 68%, #1d3542 68% 100%);
  display: grid; place-items: center; position: relative;
}
.v3 .ring::before { content: ""; position: absolute; inset: 4px; border-radius: 50%; background: #0e202a; }
.v3 .ring span { position: relative; z-index: 1; color: #cdeaf4; font-family: "Cascadia Mono", monospace; font-size: 10px; }
.v3 .sync-copy { min-width: 0; }
.v3 .sync-title { color: #cfe4ec; font-size: 10.5px; }
.v3 .sync-sub { margin-top: 3px; color: #6c8b9b; font-size: 8.5px; }
.v3 .progress-line { height: 3px; margin-top: 11px; border-radius: 3px; background: #1c3542; overflow: hidden; }
.v3 .progress-line i { display: block; width: 68%; height: 100%; background: var(--cyan); }
.v3 .sync-foot { display: flex; justify-content: space-between; margin-top: 6px; color: #5e7f8f; font-family: "Cascadia Mono", monospace; font-size: 8px; }
.v3 .queue-head { display: flex; align-items: center; justify-content: space-between; }
.v3 .queue-head span { color: #9eb6c1; font-size: 9.5px; }
.v3 .queue-head button { display: inline-flex; align-items: center; gap: 3px; color: #6e93a3; font-size: 8px; }
.v3 .queue-head button:hover { color: var(--cyan); }
.v3 .queue-list { display: flex; flex-direction: column; gap: 8px; margin-top: 7px; }
.v3 .queue-item { display: flex; align-items: center; gap: 8px; }
.v3 .queue-art { width: 46px; height: 29px; flex: none; overflow: hidden; border-radius: 1px; background: #132c39; }
.v3 .queue-art img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.6); }
.v3 .queue-copy { min-width: 0; flex: 1; }
.v3 .queue-name { color: #b5ccd5; font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v3 .queue-meta { display: flex; justify-content: space-between; margin-top: 4px; color: #5e7d8c; font-family: "Cascadia Mono", monospace; font-size: 7.5px; }
.v3 .queue-bar { height: 2px; margin-top: 4px; background: #1c3542; }
.v3 .queue-bar i { display: block; height: 100%; background: var(--cyan); }
.v3 .side-section { padding-top: 1px; }
.v3 .side-section-label { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px; color: #5f7f8f; font-family: "Cascadia Mono", monospace; font-size: 8px; letter-spacing: .12em; }
.v3 .side-section-label b { color: #8ba7b4; font-family: "Noto Sans SC", sans-serif; font-size: 8px; font-weight: 400; letter-spacing: 0; }
.v3 .storage-row { display: flex; align-items: baseline; justify-content: space-between; color: #adc3cd; font-size: 9px; }
.v3 .storage-row strong { color: #d8e7ed; font-family: "Cascadia Mono", monospace; font-size: 11px; font-weight: 400; }
.v3 .storage-row span { color: #607f8e; font-size: 8px; }
.v3 .storage-bar { height: 3px; margin: 7px 0 5px; border-radius: 3px; background: #1b3441; overflow: hidden; }
.v3 .storage-bar i { display: block; width: 18%; height: 100%; border-radius: inherit; background: #6d8791; }
.v3 .recent { display: flex; flex-direction: column; gap: 7px; }
.v3 .recent-row { display: flex; align-items: center; gap: 6px; color: #6b8998; font-size: 8.5px; }
.v3 .recent-row i { width: 4px; height: 4px; border-radius: 50%; background: #456a7b; }
.v3 .recent-row span:last-child { margin-left: auto; color: #4e7080; font-family: "Cascadia Mono", monospace; font-size: 7.5px; }
.v3 .quick-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 7px; }
.v3 .quick-button {
  height: 29px; display: flex; align-items: center; gap: 6px; padding: 0 8px;
  border: 1px solid #263e4b; border-radius: 2px;
  background: #0e202a; color: #7e9dac; font-size: 8.5px;
}
.v3 .quick-button:hover { border-color: #4d788d; color: #d6eaf2; }
.v3 .quick-button .i { width: 12px; height: 12px; }
.v3 .workshop-button {
  margin-top: auto; height: 32px; display: flex; align-items: center; justify-content: center; gap: 7px;
  border: 1px solid #356276; border-radius: 2px;
  background: #102a37; color: #b9dce9; font-size: 9.5px;
}
.v3 .workshop-button:hover { border-color: var(--cyan); background: #153644; color: #eefaff; }
.v3 .workshop-button .i { width: 13px; height: 13px; }
.v3 .statusbar {
  height: 28px; flex: none; display: flex; align-items: center; gap: 14px;
  padding: 0 16px;
  border-top: 1px solid #1d3341;
  background: #08131a; color: #557585; font-family: "Cascadia Mono", monospace; font-size: 8px;
}
.v3 .statusbar .ok { display: inline-flex; align-items: center; gap: 5px; color: #7d9a74; }
.v3 .statusbar .ok i { width: 5px; height: 5px; border-radius: 50%; background: var(--green); }
.v3 .statusbar .spacer { flex: 1; }
@media (max-width: 1280px) {
  .v3 .side { width: 300px; }
  .v3 .top-search { width: 210px; }
  .v3 .workshop-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
"""


def build_v3():
    cards = "\n".join(card_v3(m, selected=(m["title"] == MODS[2]["title"])) for m in MODS)
    body = f"""
<div class="app">
  <header class="topbar">
    <div class="brand">
      <img src="assets/app-icon.png" alt="">
      <div><div class="brand-word">L4D2 WORKSHOP</div><div class="brand-sub">LOCAL LIBRARY / STEAM LINKED</div></div>
    </div>
    <nav class="tabs" data-nav-group aria-label="主导航">
      <button class="tab active" data-nav type="button">库</button>
      <button class="tab" data-nav type="button">工坊</button>
      <button class="tab" data-nav type="button">下载 <span class="tab-badge">2</span></button>
      <button class="tab" data-nav type="button">合集</button>
    </nav>
    <div class="topbar-spacer"></div>
    <label class="top-search">{icon('search')}<input data-search placeholder="搜索你的模组库…" aria-label="搜索你的模组库"></label>
    <span class="steam-state"><i></i>STEAM 已连接</span>
    <button class="icon-button" type="button" aria-label="通知" data-toast="2 个下载任务正在进行">{icon('bell')}</button>
    <button class="icon-button" type="button" aria-label="设置" data-toast="打开设置">{icon('settings')}</button>
    <span class="avatar" aria-label="账户">P</span>
  </header>
  <div class="body">
    <main class="content">
      <section class="hero">
        <div class="hero-art"><img src="assets/mods/mod2.webp" alt="Ellis 当前外观精选"></div>
        <div class="hero-copy">
          <div class="hero-eyebrow"><i></i>FEATURED COLLECTION / 当前外观</div>
          <h1>Ellis 的夏日衣橱 <span>Ellis / 艾利斯</span></h1>
          <p><b>6</b> 个模组 · <b>1</b> 个已启用 · 同组自动互斥，游戏内即时同步</p>
          <div class="hero-chips">
            <span class="hero-chip">{icon('check')} VRC Plum 使用中</span>
            <span class="hero-chip">{icon('shield')} 本地库健康</span>
          </div>
        </div>
        <div class="hero-actions">
          <button class="hero-button" type="button" data-toast="打开 Ellis 外观合集">{icon('layers')}查看合集</button>
          <button class="hero-button primary" type="button" data-toast="正在启动 Left 4 Dead 2">{icon('play')}启动游戏</button>
        </div>
      </section>
      <div class="toolbar">
        <button class="toolbar-tab active" type="button" data-chip>全部 <span class="n">6</span></button>
        <button class="toolbar-tab" type="button" data-chip>已启用 <span class="n">1</span></button>
        <button class="toolbar-tab" type="button" data-chip>未启用 <span class="n">5</span></button>
        <div class="toolbar-spacer"></div>
        <button class="toolbar-button" type="button" data-toast="按最近添加排序">最近添加 {icon('chevron-down')}</button>
        <div class="view-toggle" aria-label="视图">
          <button class="active" type="button" aria-label="网格视图" data-toast="网格视图">{icon('grid')}</button>
          <button type="button" aria-label="列表视图" data-toast="列表视图">{icon('list')}</button>
        </div>
      </div>
      <div class="grid-wrap scroll-y">
        <div class="workshop-grid">
          {cards}
          <button class="add-card" type="button" data-toast="打开压缩包导入"><span class="add-icon">{icon('plus', 'i')}</span><strong>导入压缩包</strong><span>ZIP / 7z / RAR</span></button>
          <button class="add-card" type="button" data-toast="打开工坊链接解析"><span class="add-icon">{icon('download', 'i')}</span><strong>从工坊添加</strong><span>粘贴链接或物品 ID</span></button>
        </div>
      </div>
    </main>
    <aside class="side">
      <div class="side-head"><div class="side-title">{icon('download')}同步中心</div><span class="live-tag"><i></i>LIVE</span></div>
      <div class="sync-box">
        <div class="sync-main">
          <div class="ring"><span>68%</span></div>
          <div class="sync-copy"><div class="sync-title">正在检查工坊订阅</div><div class="sync-sub">2 个待处理 · 预计 01:24 完成</div></div>
        </div>
        <div class="progress-line"><i></i></div>
        <div class="sync-foot"><span>Verifying local files</span><span>68 / 100</span></div>
      </div>
      <div class="side-section">
        <div class="queue-head"><span>下载队列</span><button type="button" data-toast="打开下载管理器">全部任务 {icon('arrow-right')}</button></div>
        <div class="queue-list">
          <div class="queue-item">
            <div class="queue-art"><img src="assets/mods/mod4.webp" alt=""></div>
            <div class="queue-copy"><div class="queue-name">[Gakuen IDOLM@STER] Fujita</div><div class="queue-meta"><span>146.4 MB</span><span>72%</span></div><div class="queue-bar"><i style="width:72%"></i></div></div>
          </div>
          <div class="queue-item">
            <div class="queue-art"><img src="assets/mods/mod6.webp" alt=""></div>
            <div class="queue-copy"><div class="queue-name">雨衣替换 Ellis</div><div class="queue-meta"><span>246.6 MB</span><span>等待中</span></div><div class="queue-bar"><i style="width:4%;background:#4f7180"></i></div></div>
          </div>
        </div>
      </div>
      <div class="side-section">
        <div class="side-section-label"><span>LIBRARY / 本地概况</span><b>128 FILES</b></div>
        <div class="storage-row"><strong>4.8 GB</strong><span>可用 78.2 GB</span></div>
        <div class="storage-bar"><i></i></div>
        <div class="sync-foot"><span>Local addons</span><span>43 enabled</span></div>
      </div>
      <div class="side-section">
        <div class="side-section-label"><span>RECENT / 最近更新</span><b>THIS WEEK</b></div>
        <div class="recent">
          <div class="recent-row"><i></i><span>VRC Plum replace ellis</span><span>01:12</span></div>
          <div class="recent-row"><i></i><span>Koharu [Replace Ellis]</span><span>昨天</span></div>
          <div class="recent-row"><i></i><span>死亡中心 · 重制版</span><span>3 天前</span></div>
        </div>
      </div>
      <div class="side-section">
        <div class="side-section-label"><span>QUICK ACTIONS / 快捷入口</span><b>4 ITEMS</b></div>
        <div class="quick-actions">
          <button class="quick-button" type="button" data-toast="打开游戏 addons 目录">{icon('folder')}游戏目录</button>
          <button class="quick-button" type="button" data-toast="正在检查更新">{icon('refresh')}检查更新</button>
          <button class="quick-button" type="button" data-toast="打开压缩包导入">{icon('archive')}压缩包导入</button>
          <button class="quick-button" type="button" data-toast="正在清理缓存">{icon('trash')}清理缓存</button>
        </div>
      </div>
      <button class="workshop-button" type="button" data-toast="打开 Steam 创意工坊页面">{icon('external')}打开 Steam 创意工坊</button>
    </aside>
  </div>
  <footer class="statusbar">
    <span class="ok"><i></i>STEAM WORKSHOP LINKED</span>
    <span>128 MODS · 43 ENABLED</span>
    <span>GAME CLOSED</span>
    <span class="spacer"></span>
    <span>E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2\\left4dead2\\addons</span>
  </footer>
</div>
"""
    return page("03 WORKSHOP / 工坊中枢", "v3", V3_CSS, body)


def row_v4(m, selected=False):
    return f"""
<div class="lib-row{' is-selected' if selected else ''}" data-select tabindex="0"
  data-title="{escape(m['title'])}" data-meta="{escape(m['cat'] + ' / ' + m['item'])}"
  data-size="{escape(m['size'])}" data-file="{escape(m['file'])}" data-img="assets/mods/{m['img']}">
  <div class="lib-art"><img src="assets/mods/{m['img']}" alt=""></div>
  <div class="lib-copy"><div class="lib-name">{escape(m['title'])}</div><div class="lib-meta">{escape(m['cat'])} · {escape(m['item'])} · {escape(m['size'])}</div></div>
  <span class="lib-status {'on' if m['on'] else ''}">{'启用' if m['on'] else '停用'}</span>
  {switch(m['on'], label='切换 %s' % m['title'])}
</div>"""


# ---------------------------------------------------------------- V4 LOADOUT LAB
V4_CSS = r"""
:root {
  --void: #0a0d13;
  --panel: #11151d;
  --panel-2: #151a24;
  --panel-3: #1a202c;
  --line: #242b38;
  --line-2: #30394a;
  --text: #e8ecf4;
  --muted: #8d96a7;
  --dim: #5f697b;
  --mint: #79e5c1;
  --mint-2: #40b894;
  --amber: #f0b96a;
  --coral: #f17967;
  --indigo: #8d9eff;
  --focus: #79e5c1;
  --selection: rgba(121, 229, 193, .22);
}
body.v4 {
  background: var(--void);
  color: var(--text);
  font-family: "Noto Sans SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
}
.v4 .app {
  height: 100vh; min-width: 1180px;
  display: flex; flex-direction: column;
  background:
    radial-gradient(900px 480px at 74% -16%, rgba(99, 126, 255, .1), transparent 68%),
    radial-gradient(700px 360px at 16% 20%, rgba(121, 229, 193, .035), transparent 70%),
    var(--void);
}
.v4 .topbar {
  height: 60px; flex: none;
  display: flex; align-items: center; gap: 22px;
  padding: 0 18px;
  border-bottom: 1px solid #1e2430;
  background: rgba(10, 13, 19, .84);
}
.v4 .brand { display: flex; align-items: center; gap: 9px; width: 200px; flex: none; }
.v4 .brand img { width: 27px; height: 27px; filter: saturate(.7) contrast(1.08); }
.v4 .brand-name { color: #eff3f8; font-family: "Bahnschrift SemiBold", sans-serif; font-size: 14px; letter-spacing: .12em; line-height: 1; }
.v4 .brand-sub { margin-top: 4px; color: #687386; font-family: "Cascadia Mono", monospace; font-size: 7.5px; letter-spacing: .16em; }
.v4 .nav { display: flex; align-items: center; gap: 3px; }
.v4 .nav-item {
  height: 30px; padding: 0 11px;
  display: inline-flex; align-items: center; gap: 6px;
  border-radius: 6px; color: #7f8999; font-size: 10.5px;
}
.v4 .nav-item .i { width: 14px; height: 14px; }
.v4 .nav-item:hover { color: #dce3ec; background: #151a23; }
.v4 .nav-item.active { color: #071612; background: var(--mint); font-weight: 650; }
.v4 .top-spacer { flex: 1; }
.v4 .top-search {
  width: 220px; height: 31px;
  display: flex; align-items: center; gap: 7px;
  padding: 0 9px;
  border: 1px solid #2a3240; border-radius: 6px;
  background: #0d1118; color: #6e7a8c;
}
.v4 .top-search input { width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--text); font-size: 10px; }
.v4 .top-search input::placeholder { color: #5a6577; }
.v4 .top-search .i { width: 13px; height: 13px; }
.v4 .status-pill {
  display: inline-flex; align-items: center; gap: 5px;
  color: #8b96a8; font-size: 9px; white-space: nowrap;
}
.v4 .status-pill i { width: 5px; height: 5px; border-radius: 50%; background: #7c8799; }
.v4 .icon-button { width: 29px; height: 29px; display: grid; place-items: center; border-radius: 6px; color: #7d899a; }
.v4 .icon-button:hover { background: #171d27; color: #eef2f8; }
.v4 .launch {
  height: 32px; display: inline-flex; align-items: center; gap: 7px;
  padding: 0 13px; border-radius: 6px;
  background: var(--mint); color: #071410;
  font-size: 10.5px; font-weight: 700;
  box-shadow: 0 5px 22px rgba(121,229,193,.12);
}
.v4 .launch:hover { background: #9bf2d4; }
.v4 .launch .i { width: 13px; height: 13px; }
.v4 .body { min-height: 0; flex: 1; display: flex; }
.v4 .sidebar {
  width: 222px; flex: none;
  padding: 17px 11px 12px;
  border-right: 1px solid #1d2430;
  background: rgba(11, 14, 20, .66);
  display: flex; flex-direction: column;
}
.v4 .side-label { margin: 0 8px 7px; color: #596577; font-family: "Cascadia Mono", monospace; font-size: 8px; letter-spacing: .14em; }
.v4 .side-nav { display: flex; flex-direction: column; gap: 2px; }
.v4 .side-link {
  height: 35px; display: flex; align-items: center; gap: 9px;
  padding: 0 9px; border-radius: 6px;
  color: #7f8b9c; font-size: 10.5px; text-align: left;
}
.v4 .side-link .i { width: 15px; height: 15px; color: #657186; }
.v4 .side-link .badge {
  margin-left: auto; min-width: 18px; height: 16px; padding: 0 4px;
  display: grid; place-items: center; border-radius: 4px;
  background: #2c2319; color: var(--amber); font-family: "Cascadia Mono", monospace; font-size: 8px;
}
.v4 .side-link:hover { background: #141a23; color: #dce4ee; }
.v4 .side-link.active { background: #17251f; color: var(--mint); }
.v4 .side-link.active .i { color: var(--mint); }
.v4 .side-divider { height: 1px; margin: 14px 8px; background: #1d2430; }
.v4 .preset { display: flex; flex-direction: column; gap: 4px; }
.v4 .preset-item {
  padding: 8px 9px; border-radius: 6px;
  border: 1px solid transparent; text-align: left; color: #8c98a9;
}
.v4 .preset-item:hover { background: #141a23; }
.v4 .preset-item.active { border-color: #2d4b42; background: #121e1a; }
.v4 .preset-title { display: flex; align-items: center; justify-content: space-between; color: #bcc8d3; font-size: 10px; }
.v4 .preset-title span { color: var(--mint); font-family: "Cascadia Mono", monospace; font-size: 7px; }
.v4 .preset-sub { margin-top: 3px; color: #677384; font-size: 8px; }
.v4 .side-spacer { flex: 1; }
.v4 .side-storage { padding: 10px 9px 3px; border-top: 1px solid #1d2430; }
.v4 .side-storage-head { display: flex; justify-content: space-between; color: #687486; font-size: 8px; }
.v4 .side-storage-head b { color: #aebbc8; font-family: "Cascadia Mono", monospace; font-weight: 400; }
.v4 .side-meter { height: 3px; margin-top: 7px; border-radius: 3px; background: #202936; overflow: hidden; }
.v4 .side-meter i { display: block; width: 17%; height: 100%; background: #536373; border-radius: inherit; }
.v4 .main { min-width: 0; flex: 1; padding: 17px 22px 16px; display: flex; flex-direction: column; overflow-y: auto; }
.v4 .page-head { flex: none; display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; }
.v4 .crumb { display: flex; align-items: center; gap: 6px; color: #647083; font-size: 9.5px; }
.v4 .crumb .i { width: 10px; height: 10px; color: #4e5b6c; }
.v4 .crumb b { color: #a8b5c3; font-weight: 500; }
.v4 .page-head h1 { margin: 8px 0 0; font-size: 25px; line-height: 1.15; font-weight: 600; letter-spacing: -.02em; color: #edf1f5; }
.v4 .page-head h1 span { margin-left: 7px; color: #7c899a; font-size: 11px; font-weight: 400; letter-spacing: 0; }
.v4 .page-head p { margin: 5px 0 0; color: #778395; font-size: 10px; }
.v4 .page-head p b { color: var(--mint); font-weight: 500; }
.v4 .head-tools { display: flex; align-items: center; gap: 8px; padding-bottom: 2px; }
.v4 .small-button {
  height: 29px; display: inline-flex; align-items: center; gap: 6px;
  padding: 0 9px; border: 1px solid #2b3341; border-radius: 5px;
  color: #9aa6b6; background: #11161e; font-size: 9.5px;
}
.v4 .small-button:hover { border-color: #455268; color: #e3eaf2; }
.v4 .small-button .i { width: 13px; height: 13px; }
.v4 .loadout {
  flex: none; margin-top: 14px;
  border: 1px solid #263041; border-radius: 8px;
  background:
    linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px) 0 0 / 100% 26px,
    linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px) 0 0 / 26px 100%,
    linear-gradient(120deg, #141b25, #0e131b 66%);
  overflow: hidden;
}
.v4 .loadout-head { display: flex; align-items: center; justify-content: space-between; height: 40px; padding: 0 14px; border-bottom: 1px solid #23303a; }
.v4 .loadout-title { display: flex; align-items: center; gap: 8px; color: #dbe6ec; font-size: 10.5px; }
.v4 .loadout-title .i { width: 14px; height: 14px; color: var(--mint); }
.v4 .loadout-title b { color: #6f7f90; font-family: "Cascadia Mono", monospace; font-size: 8px; font-weight: 400; letter-spacing: .06em; }
.v4 .loadout-state { display: flex; align-items: center; gap: 7px; color: #798697; font-size: 8.5px; }
.v4 .loadout-state i { width: 5px; height: 5px; border-radius: 50%; background: #566475; }
.v4 .loadout-state .sync { color: #8fae9f; }
.v4 .slots { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); height: 143px; }
.v4 .slot { position: relative; min-width: 0; padding: 12px 12px 10px; border-right: 1px solid #222d39; }
.v4 .slot:last-child { border-right: 0; }
.v4 .slot-label { display: flex; align-items: center; justify-content: space-between; color: #657487; font-family: "Cascadia Mono", monospace; font-size: 7.5px; letter-spacing: .08em; }
.v4 .slot-label span { color: #4c5d6e; }
.v4 .slot-main { display: flex; align-items: center; gap: 9px; margin-top: 9px; }
.v4 .slot-art {
  width: 48px; height: 48px; flex: none; border-radius: 5px; overflow: hidden;
  border: 1px solid #34404f; background: #0c1218;
  display: grid; place-items: center; color: #678091;
}
.v4 .slot-art img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.72) contrast(1.03); }
.v4 .slot-art .i { width: 20px; height: 20px; }
.v4 .slot-art.map-art {
  background:
    radial-gradient(ellipse at 20% 40%, rgba(121,229,193,.2), transparent 40%),
    repeating-radial-gradient(ellipse at 50% 50%, transparent 0 5px, rgba(121,229,193,.07) 6px 7px),
    #0d1719;
  color: var(--mint);
}
.v4 .slot-art.weapon-art {
  background: radial-gradient(circle at 40% 35%, rgba(141,158,255,.26), transparent 55%), #11151e;
  color: var(--indigo);
}
.v4 .slot-art.melee-art {
  background: radial-gradient(circle at 40% 35%, rgba(240,185,106,.22), transparent 55%), #17150f;
  color: var(--amber);
}
.v4 .slot-copy { min-width: 0; }
.v4 .slot-copy b { display: block; color: #cbd8e1; font-size: 10.5px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v4 .slot-copy span { display: block; margin-top: 3px; color: #637487; font-family: "Cascadia Mono", monospace; font-size: 7.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v4 .slot-foot { position: absolute; left: 12px; right: 12px; bottom: 10px; display: flex; align-items: center; justify-content: space-between; }
.v4 .slot-state { display: inline-flex; align-items: center; gap: 5px; color: #668074; font-size: 8px; }
.v4 .slot-state i { width: 4px; height: 4px; border-radius: 50%; background: var(--mint); }
.v4 .slot-edit { color: #5f7182; font-size: 8px; }
.v4 .slot-edit:hover { color: #d7e5ed; }
.v4 .switch {
  position: relative; width: 28px; height: 16px; flex: none;
  border: 1px solid #384554; border-radius: 9px; background: #202a36;
}
.v4 .switch .switch-knob { position: absolute; top: 2px; left: 2px; width: 10px; height: 10px; border-radius: 50%; background: #7a8797; transition: transform .16s ease, background .16s ease; }
.v4 .switch.on { border-color: var(--mint); background: var(--mint); }
.v4 .switch.on .switch-knob { transform: translateX(12px); background: #091713; }
.v4 .lower { min-height: 0; flex: 1; display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(290px, 1fr); gap: 14px; margin-top: 14px; }
.v4 .panel { min-width: 0; border: 1px solid #232d3a; border-radius: 8px; background: #10151d; overflow: hidden; display: flex; flex-direction: column; }
.v4 .panel-head { flex: none; display: flex; align-items: center; justify-content: space-between; min-height: 42px; padding: 0 13px; border-bottom: 1px solid #202936; }
.v4 .panel-title { display: flex; align-items: center; gap: 7px; color: #c8d5df; font-size: 10.5px; }
.v4 .panel-title .i { width: 14px; height: 14px; color: #728497; }
.v4 .panel-title span { color: #5d6d7f; font-family: "Cascadia Mono", monospace; font-size: 7.5px; }
.v4 .panel-actions { display: flex; align-items: center; gap: 9px; }
.v4 .panel-actions button { display: inline-flex; align-items: center; gap: 4px; color: #687b8c; font-size: 8.5px; }
.v4 .panel-actions button:hover { color: #d6e2eb; }
.v4 .panel-actions .i { width: 11px; height: 11px; }
.v4 .lib-toolbar { flex: none; display: flex; align-items: center; gap: 3px; min-height: 35px; padding: 0 10px; border-bottom: 1px solid #1c2531; }
.v4 .lib-tab { height: 24px; padding: 0 7px; display: inline-flex; align-items: center; gap: 5px; border-radius: 4px; color: #6e7f91; font-size: 9px; }
.v4 .lib-tab:hover { color: #c8d6e2; background: #18212c; }
.v4 .lib-tab.active { background: #1a2b25; color: var(--mint); }
.v4 .lib-tab .n { color: #5d6e7e; font-family: "Cascadia Mono", monospace; font-size: 7.5px; }
.v4 .lib-tab.active .n { color: #8cbea8; }
.v4 .lib-toolbar-spacer { flex: 1; }
.v4 .libs { min-height: 0; flex: 1; overflow-y: auto; padding: 4px 5px 5px; }
.v4 .lib-row {
  display: flex; align-items: center; gap: 9px;
  min-height: 49px; padding: 5px 8px; border-radius: 5px;
  border: 1px solid transparent; cursor: pointer;
}
.v4 .lib-row:hover { background: #161e28; }
.v4 .lib-row.is-selected { border-color: #2a443b; background: #13211d; }
.v4 .lib-art { width: 44px; height: 28px; flex: none; overflow: hidden; border-radius: 3px; background: #0b1117; }
.v4 .lib-art img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.74); }
.v4 .lib-copy { min-width: 0; flex: 1; }
.v4 .lib-name { color: #c6d2dc; font-size: 9.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v4 .lib-meta { margin-top: 2px; color: #5d6f80; font-family: "Cascadia Mono", monospace; font-size: 7.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v4 .lib-status { font-family: "Cascadia Mono", monospace; font-size: 7.5px; color: #5d6e7e; }
.v4 .lib-status.on { color: #80c9ac; }
.v4 .lib-row .switch { margin-left: 3px; }
.v4 .lib-extra { flex: none; border-top: 1px solid #202936; padding: 9px 10px 10px; }
.v4 .lib-extra-head { display: flex; align-items: center; justify-content: space-between; color: #5f7182; font-family: "Cascadia Mono", monospace; font-size: 7.5px; letter-spacing: .1em; }
.v4 .lib-extra-head button { color: #687d8f; font-family: "Noto Sans SC", sans-serif; font-size: 8px; letter-spacing: 0; }
.v4 .lib-extra-head button:hover { color: #d2e0e9; }
.v4 .lib-extra-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-top: 7px; }
.v4 .extra-card { display: flex; align-items: center; gap: 8px; min-width: 0; height: 43px; padding: 0 8px; border: 1px solid #27313e; border-radius: 5px; background: #121821; text-align: left; }
.v4 .extra-card:hover { border-color: #3d4d60; background: #151e28; }
.v4 .extra-art { width: 38px; height: 27px; flex: none; border-radius: 3px; overflow: hidden; background: #0c1218; display: grid; place-items: center; color: #718699; }
.v4 .extra-art img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.68); }
.v4 .extra-art .i { width: 15px; height: 15px; }
.v4 .extra-copy { min-width: 0; }
.v4 .extra-copy b { display: block; color: #aab9c6; font-size: 8.5px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v4 .extra-copy span { display: block; margin-top: 2px; color: #5f7182; font-family: "Cascadia Mono", monospace; font-size: 7px; }
.v4 .check-panel { min-width: 0; border: 1px solid #232d3a; border-radius: 8px; background: #10151d; overflow: hidden; display: flex; flex-direction: column; }
.v4 .check-body { min-height: 0; flex: 1; padding: 12px; overflow-y: auto; }
.v4 .check-score { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; color: #aebdc8; font-size: 9.5px; }
.v4 .score-badge {
  width: 30px; height: 30px; display: grid; place-items: center; border-radius: 50%;
  border: 1px solid #3a4a46; color: var(--mint); background: #13211d;
  font-family: "Cascadia Mono", monospace; font-size: 9px;
}
.v4 .check-score span { color: #66798a; font-size: 8.5px; }
.v4 .alert-card {
  padding: 9px 9px 8px; margin-bottom: 8px;
  border: 1px solid #41372a; border-radius: 5px; background: #19150f;
}
.v4 .alert-card.info { border-color: #2a3748; background: #0e1720; }
.v4 .alert-head { display: flex; align-items: center; gap: 6px; color: var(--amber); font-size: 9px; }
.v4 .alert-card.info .alert-head { color: #8dafff; }
.v4 .alert-head .i { width: 12px; height: 12px; }
.v4 .alert-copy { margin-top: 5px; color: #766f5f; font-size: 8.5px; line-height: 1.5; }
.v4 .alert-card.info .alert-copy { color: #65788b; }
.v4 .alert-link { display: inline-flex; align-items: center; gap: 4px; margin-top: 6px; color: #bb9e6a; font-size: 8px; }
.v4 .alert-card.info .alert-link { color: #82a6f0; }
.v4 .presets { margin-top: 14px; padding-top: 12px; border-top: 1px solid #202936; }
.v4 .sub-label { display: flex; justify-content: space-between; color: #627386; font-family: "Cascadia Mono", monospace; font-size: 7.5px; letter-spacing: .12em; }
.v4 .sub-label b { color: #4f6071; font-family: "Noto Sans SC", sans-serif; font-size: 7.5px; font-weight: 400; letter-spacing: 0; }
.v4 .preset-pills { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; }
.v4 .preset-pill {
  display: flex; align-items: center; gap: 7px; height: 27px; padding: 0 7px;
  border: 1px solid #252f3b; border-radius: 4px; color: #7c8c9d; font-size: 8.5px;
}
.v4 .preset-pill:hover { border-color: #3c4b5d; background: #141b24; color: #d1dee7; }
.v4 .preset-pill.active { border-color: #2c4b40; background: #12211c; color: #9fd9c2; }
.v4 .preset-pill .i { width: 11px; height: 11px; }
.v4 .preset-pill span { margin-left: auto; color: #526475; font-family: "Cascadia Mono", monospace; font-size: 7px; }
.v4 .activity { margin-top: 14px; padding-top: 12px; border-top: 1px solid #202936; }
.v4 .activity-row { display: flex; align-items: center; gap: 6px; margin-top: 7px; color: #687a8b; font-size: 8px; }
.v4 .activity-row i { width: 4px; height: 4px; border-radius: 50%; background: #4f6577; }
.v4 .activity-row span:last-child { margin-left: auto; color: #4d6072; font-family: "Cascadia Mono", monospace; font-size: 7px; }
.v4 .footbar {
  height: 28px; flex: none; display: flex; align-items: center; gap: 14px;
  padding: 0 15px; border-top: 1px solid #1d2532;
  background: #0a0e14; color: #526173; font-family: "Cascadia Mono", monospace; font-size: 8px;
}
.v4 .footbar .spacer { flex: 1; }
.v4 .footbar .ready { display: inline-flex; align-items: center; gap: 5px; color: #7e9d8f; }
.v4 .footbar .ready i { width: 4px; height: 4px; border-radius: 50%; background: var(--mint); }
@media (max-width: 1280px) {
  .v4 .sidebar { width: 204px; }
  .v4 .lower { grid-template-columns: minmax(0, 1.45fr) minmax(275px, 1fr); }
  .v4 .slot-copy b { font-size: 9.5px; }
}
"""


def build_v4():
    rows = "\n".join(row_v4(m, selected=(m["title"] == MODS[2]["title"])) for m in MODS)
    body = f"""
<div class="app">
  <header class="topbar">
    <div class="brand"><img src="assets/app-icon.png" alt=""><div><div class="brand-name">LOADOUT LAB</div><div class="brand-sub">L4D2 / WORKBENCH 04</div></div></div>
    <nav class="nav" data-nav-group aria-label="主导航">
      <button class="nav-item active" data-nav type="button">{icon('sliders')}配装台</button>
      <button class="nav-item" data-nav type="button">{icon('grid')}模组库</button>
      <button class="nav-item" data-nav type="button">{icon('map')}地图</button>
      <button class="nav-item" data-nav type="button">{icon('download')}下载</button>
    </nav>
    <div class="top-spacer"></div>
    <label class="top-search">{icon('search')}<input data-search placeholder="搜索模组或预设…" aria-label="搜索模组或预设"></label>
    <span class="status-pill"><i></i>游戏未运行</span>
    <button class="icon-button" type="button" aria-label="通知" data-toast="有 1 个待处理冲突">{icon('bell')}</button>
    <button class="launch" type="button" data-toast="正在启动 Left 4 Dead 2">{icon('play')}启动游戏</button>
  </header>
  <div class="body">
    <aside class="sidebar">
      <div class="side-label">WORKBENCH / 工作台</div>
      <nav class="side-nav" data-nav-group>
        <button class="side-link active" data-nav type="button">{icon('sliders')}配装台</button>
        <button class="side-link" data-nav type="button">{icon('grid')}模组库</button>
        <button class="side-link" data-nav type="button">{icon('alert')}冲突中心<span class="badge">1</span></button>
        <button class="side-link" data-nav type="button">{icon('download')}下载队列<span class="badge">2</span></button>
        <button class="side-link" data-nav type="button">{icon('archive')}压缩包导入</button>
      </nav>
      <div class="side-divider"></div>
      <div class="side-label">PRESETS / 快捷方案</div>
      <div class="preset">
        <button class="preset-item active" type="button" data-toast="已切换到「周末混战」配装">
          <div class="preset-title">周末混战<span>ACTIVE</span></div><div class="preset-sub">Ellis · AK-47 · 死亡中心</div>
        </button>
        <button class="preset-item" type="button" data-toast="已载入「写实模式」配装">
          <div class="preset-title">写实模式</div><div class="preset-sub">原版外观 · 无 UI 模组</div>
        </button>
        <button class="preset-item" type="button" data-toast="已载入「原版外观」配装">
          <div class="preset-title">原版外观</div><div class="preset-sub">仅启用地图与音效</div>
        </button>
      </div>
      <div class="side-spacer"></div>
      <div class="side-storage">
        <div class="side-storage-head"><span>模组库占用</span><b>4.8 GB</b></div>
        <div class="side-meter"><i></i></div>
        <div class="side-storage-head" style="margin-top:6px"><span>128 FILES</span><span>43 ENABLED</span></div>
      </div>
    </aside>
    <main class="main">
      <div class="page-head">
        <div>
          <div class="crumb">工作台 {icon('chevron-right')} 配装 <b>周末混战</b></div>
          <h1>配装台 <span>今晚，直接开打。</span></h1>
          <p>一键切换正在使用的模组组合 · <b>1</b> 个组冲突待处理</p>
        </div>
        <div class="head-tools">
          <button class="small-button" type="button" data-toast="已重新检查所有互斥组">{icon('shield')}检查配装</button>
          <button class="small-button" type="button" data-toast="打开配装编辑">{icon('settings')}编辑方案</button>
        </div>
      </div>
      <section class="loadout">
        <div class="loadout-head">
          <div class="loadout-title">{icon('layers')}当前配装 <b>LOADOUT_01 / 本地</b></div>
          <div class="loadout-state"><span class="sync"><i></i>已与游戏同步</span><span>·</span><span>4 个槽位已填充</span></div>
        </div>
        <div class="slots">
          <div class="slot">
            <div class="slot-label">01 / 幸存者 <span>ELLIS</span></div>
            <div class="slot-main"><div class="slot-art"><img src="assets/mods/mod3.webp" alt=""></div><div class="slot-copy"><b>VRC Plum</b><span>replace ellis · 34.1 MB</span></div></div>
            <div class="slot-foot"><span class="slot-state"><i></i>已启用</span><button class="slot-edit" type="button" data-toast="打开幸存者槽位">更换 {icon('chevron-right')}</button></div>
          </div>
          <div class="slot">
            <div class="slot-label">02 / 主武器 <span>AK-47</span></div>
            <div class="slot-main"><div class="slot-art weapon-art">{icon('crosshair')}</div><div class="slot-copy"><b>霓虹风暴</b><span>AK-47 · 56.8 MB</span></div></div>
            <div class="slot-foot"><span class="slot-state"><i></i>已启用</span><button class="slot-edit" type="button" data-toast="打开主武器槽位">更换 {icon('chevron-right')}</button></div>
          </div>
          <div class="slot">
            <div class="slot-label">03 / 近战 <span>FIRE AXE</span></div>
            <div class="slot-main"><div class="slot-art melee-art">{icon('crosshair')}</div><div class="slot-copy"><b>消防斧 · 原版</b><span>使用游戏默认外观</span></div></div>
            <div class="slot-foot"><span class="slot-state"><i></i>已启用</span><button class="slot-edit" type="button" data-toast="打开近战槽位">更换 {icon('chevron-right')}</button></div>
          </div>
          <div class="slot">
            <div class="slot-label">04 / 地图 <span>DEAD CENTER</span></div>
            <div class="slot-main"><div class="slot-art map-art">{icon('map')}</div><div class="slot-copy"><b>死亡中心 · 重制版</b><span>1.2 GB · 3 个组件</span></div></div>
            <div class="slot-foot"><span class="slot-state"><i></i>已启用</span><button class="slot-edit" type="button" data-toast="打开地图槽位">更换 {icon('chevron-right')}</button></div>
          </div>
        </div>
      </section>
      <div class="lower">
        <section class="panel">
          <div class="panel-head">
            <div class="panel-title">{icon('grid')}模组库 <span>/ ELLIS</span></div>
            <div class="panel-actions"><button type="button" data-toast="打开完整模组库">查看全部 {icon('arrow-right')}</button><button type="button" data-toast="打开导入">{icon('plus')}导入</button></div>
          </div>
          <div class="lib-toolbar">
            <button class="lib-tab active" type="button" data-chip>Ellis <span class="n">6</span></button>
            <button class="lib-tab" type="button" data-chip>AK-47 <span class="n">2</span></button>
            <button class="lib-tab" type="button" data-chip>地图 <span class="n">2</span></button>
            <div class="lib-toolbar-spacer"></div>
            <button class="lib-tab" type="button" data-toast="按最近添加排序">最近添加 {icon('chevron-down')}</button>
          </div>
          <div class="libs scroll-y">{rows}</div>
          <div class="lib-extra">
            <div class="lib-extra-head"><span>OTHER ITEMS / 其他物品</span><button type="button" data-toast="浏览全部物品">全部 {icon('arrow-right')}</button></div>
            <div class="lib-extra-grid">
              <button class="extra-card" type="button" data-toast="切换到 AK-47"><span class="extra-art"><img src="assets/mods/mod2.webp" alt=""></span><span class="extra-copy"><b>AK-47</b><span>2 MODS · 1 ACTIVE</span></span></button>
              <button class="extra-card" type="button" data-toast="切换到地图"><span class="extra-art">{icon('map')}</span><span class="extra-copy"><b>地图合集</b><span>18 MAPS · 1 ACTIVE</span></span></button>
            </div>
          </div>
        </section>
        <aside class="check-panel">
          <div class="panel-head">
            <div class="panel-title">{icon('shield')}配装检查</div>
            <div class="panel-actions"><button type="button" data-toast="重新检查完成">重新检查 {icon('refresh')}</button></div>
          </div>
          <div class="check-body scroll-y">
            <div class="check-score"><div class="score-badge">A-</div><div>4 个槽位工作正常<br><span>1 个建议可清理</span></div></div>
            <div class="alert-card">
              <div class="alert-head">{icon('alert')}外观组有旧启用项</div>
              <div class="alert-copy">Ellis 组检测到 1 个旧外观仍处于启用状态。切换时会自动清理，不会影响当前配装。</div>
              <button class="alert-link" type="button" data-toast="打开冲突中心">查看冲突 {icon('arrow-up-right')}</button>
            </div>
            <div class="alert-card info">
              <div class="alert-head">{icon('map')}地图合集缺少组件</div>
              <div class="alert-copy">「死亡中心 · 重制版」还有 1 个组件未下载，进入地图时可能会回退到默认关卡。</div>
              <button class="alert-link" type="button" data-toast="打开下载队列">补齐组件 {icon('download')}</button>
            </div>
            <div class="presets">
              <div class="sub-label"><span>PRESETS / 快速切换</span><b>3 SAVED</b></div>
              <div class="preset-pills">
                <button class="preset-pill active" type="button" data-toast="已应用「周末混战」">{icon('check')}周末混战 <span>4 slots</span></button>
                <button class="preset-pill" type="button" data-toast="已应用「写实模式」">{icon('sliders')}写实模式 <span>2 slots</span></button>
                <button class="preset-pill" type="button" data-toast="已应用「原版外观」">{icon('shield')}原版外观 <span>0 mods</span></button>
              </div>
            </div>
            <div class="activity">
              <div class="sub-label"><span>ACTIVITY / 最近操作</span><b>TODAY</b></div>
              <div class="activity-row"><i></i><span>切换 Ellis 外观</span><span>12:40</span></div>
              <div class="activity-row"><i></i><span>启用死亡中心重制</span><span>昨天</span></div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  </div>
  <footer class="footbar">
    <span class="ready"><i></i>配装已就绪</span><span>4 SLOTS · 6 MODS</span><span>1 个组冲突</span><span class="spacer"></span><span>E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2\\left4dead2\\addons</span>
  </footer>
</div>
"""
    return page("04 LOADOUT LAB / 配装台", "v4", V4_CSS, body)


def row_v5(m, selected=False):
    status = "已启用" if m["on"] else "未启用"
    return f"""
<div class="table-row{' is-selected' if selected else ''}" data-select tabindex="0"
  data-title="{escape(m['title'])}" data-meta="{escape(m['cat'] + ' / ' + m['item'])}"
  data-size="{escape(m['size'])}" data-date="{escape(m['date'])}" data-file="{escape(m['file'])}"
  data-img="assets/mods/{m['img']}" aria-label="{escape(m['title'])}">
  <span class="row-check"><input type="checkbox" aria-label="选择 {escape(m['title'])}"></span>
  <div class="row-name">
    <span class="row-art"><img src="assets/mods/{m['img']}" alt=""></span>
    <span class="row-text"><b>{escape(m['title'])}</b><small>{escape(m['cat'])} · {escape(m['item'])}</small></span>
  </div>
  <span class="type-pill">{escape(m['cat'])}</span>
  <span class="row-size">{escape(m['size'])}</span>
  <span class="row-date">{escape(m['date'])}</span>
  <span class="row-state {'on' if m['on'] else ''}"><i></i>{status}</span>
  {switch(m['on'], label='切换 %s' % m['title'])}
</div>"""


# ---------------------------------------------------------------- V5 INDEX
V5_CSS = r"""
:root {
  --canvas: #f5f6f8;
  --surface: #ffffff;
  --surface-2: #fafbfc;
  --line: #e4e7ec;
  --line-strong: #d0d5dd;
  --ink: #14171c;
  --ink-2: #344054;
  --muted: #667085;
  --dim: #98a2b3;
  --faint: #c7ced8;
  --red: #d92d20;
  --red-deep: #b42318;
  --red-soft: #fef3f2;
  --green: #067647;
  --green-soft: #ecfdf3;
  --blue: #175cd3;
  --focus: #d92d20;
  --selection: rgba(217, 45, 32, .12);
}
body.v5 {
  background: var(--canvas);
  color: var(--ink);
  font-family: "Segoe UI Variable", "Segoe UI", "Noto Sans SC", "Microsoft YaHei UI", sans-serif;
  font-size: 12px;
}
.v5 .app { height: 100vh; min-width: 1180px; display: flex; flex-direction: column; }
.v5 .topbar {
  height: 58px; flex: none;
  display: flex; align-items: center; gap: 18px;
  padding: 0 18px;
  border-bottom: 1px solid var(--line);
  background: var(--surface);
}
.v5 .brand { width: 218px; flex: none; display: flex; align-items: center; gap: 9px; }
.v5 .brand img { width: 25px; height: 25px; filter: grayscale(.35) contrast(1.1); }
.v5 .brand-name { color: var(--ink); font-family: "Bahnschrift SemiBold", "Segoe UI", sans-serif; font-size: 14px; letter-spacing: .08em; line-height: 1; }
.v5 .brand-sub { margin-top: 4px; color: var(--dim); font-family: "Cascadia Mono", monospace; font-size: 7.5px; letter-spacing: .13em; }
.v5 .top-search {
  width: min(440px, 38vw); height: 33px;
  display: flex; align-items: center; gap: 8px;
  padding: 0 10px;
  border: 1px solid var(--line-strong); border-radius: 6px;
  background: var(--surface-2); color: var(--dim);
}
.v5 .top-search:focus-within { border-color: var(--ink-2); background: #fff; box-shadow: 0 0 0 3px rgba(20,23,28,.05); }
.v5 .top-search input { flex: 1 1 auto; width: auto; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--ink); font-size: 11px; }
.v5 .top-search input::placeholder { color: var(--dim); }
.v5 .top-search .i { width: 15px; height: 15px; }
.v5 .top-search .kbd { margin-left: auto; opacity: .45; }
.v5 .top-spacer { flex: 1; }
.v5 .top-status { display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: 9.5px; white-space: nowrap; }
.v5 .top-status i { width: 6px; height: 6px; border-radius: 50%; background: #12b76a; box-shadow: 0 0 0 3px rgba(18,183,106,.1); }
.v5 .top-divider { width: 1px; height: 20px; background: var(--line); }
.v5 .icon-button { width: 30px; height: 30px; display: grid; place-items: center; border: 1px solid transparent; border-radius: 5px; color: var(--muted); }
.v5 .icon-button:hover { border-color: var(--line); background: var(--surface-2); color: var(--ink); }
.v5 .top-button {
  height: 31px; display: inline-flex; align-items: center; gap: 6px;
  padding: 0 10px; border: 1px solid var(--line-strong); border-radius: 5px;
  background: #fff; color: var(--ink-2); font-size: 10px; white-space: nowrap;
}
.v5 .top-button:hover { border-color: #98a2b3; background: var(--surface-2); }
.v5 .top-button .i { width: 13px; height: 13px; }
.v5 .top-button.primary { border-color: var(--red); background: var(--red); color: #fff; font-weight: 650; }
.v5 .top-button.primary:hover { background: var(--red-deep); border-color: var(--red-deep); }
.v5 .body { min-height: 0; flex: 1; display: flex; }
.v5 .sidebar {
  width: 218px; flex: none;
  padding: 17px 11px 12px;
  border-right: 1px solid var(--line);
  background: var(--surface-2);
  display: flex; flex-direction: column;
}
.v5 .side-label { margin: 0 9px 7px; color: var(--dim); font-size: 8.5px; letter-spacing: .08em; font-weight: 600; text-transform: uppercase; }
.v5 .side-nav { display: flex; flex-direction: column; gap: 1px; }
.v5 .side-link {
  position: relative;
  height: 32px; display: flex; align-items: center; gap: 9px;
  padding: 0 9px; border-radius: 5px;
  color: var(--muted); font-size: 10.5px; text-align: left;
}
.v5 .side-link .i { width: 15px; height: 15px; color: var(--dim); }
.v5 .side-link .n { margin-left: auto; color: var(--dim); font-family: "Cascadia Mono", monospace; font-size: 8px; }
.v5 .side-link:hover { background: #f0f2f5; color: var(--ink); }
.v5 .side-link.active { background: #eef0f3; color: var(--ink); font-weight: 600; }
.v5 .side-link.active::before { content: ""; position: absolute; left: 0; top: 8px; bottom: 8px; width: 2px; border-radius: 2px; background: var(--red); }
.v5 .side-link.active .i { color: var(--red); }
.v5 .side-link.active .n { color: var(--ink-2); }
.v5 .side-gap { height: 16px; }
.v5 .side-divider { height: 1px; margin: 12px 9px; background: var(--line); }
.v5 .side-list { display: flex; flex-direction: column; gap: 1px; }
.v5 .side-list button {
  height: 28px; display: flex; align-items: center; gap: 8px;
  padding: 0 9px; border-radius: 5px; color: var(--muted); font-size: 9.5px; text-align: left;
}
.v5 .side-list button:hover { background: #f0f2f5; color: var(--ink); }
.v5 .side-list i { width: 5px; height: 5px; border-radius: 50%; background: var(--faint); }
.v5 .side-list button:nth-child(1) i { background: #12b76a; }
.v5 .side-list button:nth-child(2) i { background: #f79009; }
.v5 .side-list button:nth-child(3) i { background: #7a5af8; }
.v5 .side-list button:nth-child(4) i { background: var(--red); }
.v5 .side-list span:last-child { margin-left: auto; color: var(--dim); font-family: "Cascadia Mono", monospace; font-size: 8px; }
.v5 .side-spacer { flex: 1; }
.v5 .health-card { margin: 0 2px 12px; padding: 10px; border: 1px solid var(--line); border-radius: 6px; background: #fff; }
.v5 .health-head { display: flex; align-items: center; gap: 6px; color: var(--ink-2); font-size: 9px; font-weight: 600; }
.v5 .health-head .i { width: 13px; height: 13px; color: var(--green); }
.v5 .health-copy { margin-top: 5px; color: var(--muted); font-size: 8.5px; line-height: 1.5; }
.v5 .health-meter { height: 3px; margin-top: 8px; border-radius: 3px; background: #eaecf0; overflow: hidden; }
.v5 .health-meter i { display: block; width: 86%; height: 100%; background: #12b76a; border-radius: inherit; }
.v5 .side-foot { display: flex; align-items: center; justify-content: space-between; padding: 0 9px; color: var(--dim); font-family: "Cascadia Mono", monospace; font-size: 7.5px; }
.v5 .main { min-width: 0; flex: 1; padding: 20px 20px 0; display: flex; flex-direction: column; }
.v5 .page-head { flex: none; display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.v5 .crumb { display: flex; align-items: center; gap: 6px; color: var(--dim); font-size: 9px; }
.v5 .crumb .i { width: 10px; height: 10px; }
.v5 .crumb b { color: var(--ink-2); font-weight: 500; }
.v5 .page-head h1 { margin: 8px 0 0; color: var(--ink); font-size: 25px; line-height: 1.15; font-weight: 650; letter-spacing: -.035em; }
.v5 .page-head h1 span { margin-left: 7px; color: var(--dim); font-family: "Cascadia Mono", monospace; font-size: 10px; font-weight: 400; letter-spacing: 0; }
.v5 .page-head p { margin: 6px 0 0; color: var(--muted); font-size: 9.5px; }
.v5 .page-head p b { color: var(--ink-2); font-weight: 600; }
.v5 .page-actions { display: flex; align-items: center; gap: 7px; padding-bottom: 2px; }
.v5 .mini-button { height: 29px; display: inline-flex; align-items: center; gap: 6px; padding: 0 9px; border: 1px solid var(--line-strong); border-radius: 5px; background: #fff; color: var(--muted); font-size: 9.5px; }
.v5 .mini-button:hover { border-color: #98a2b3; color: var(--ink); }
.v5 .mini-button .i { width: 13px; height: 13px; }
.v5 .filterbar { flex: none; display: flex; align-items: center; gap: 5px; min-height: 45px; margin-top: 8px; border-bottom: 1px solid var(--line); }
.v5 .filter-chip { height: 26px; padding: 0 9px; display: inline-flex; align-items: center; gap: 5px; border: 1px solid transparent; border-radius: 4px; color: var(--muted); font-size: 9.5px; }
.v5 .filter-chip span { color: var(--dim); font-family: "Cascadia Mono", monospace; font-size: 8px; }
.v5 .filter-chip:hover { background: #eceff3; color: var(--ink); }
.v5 .filter-chip.active { border-color: var(--line-strong); background: #fff; color: var(--ink); box-shadow: 0 1px 2px rgba(16,24,40,.04); }
.v5 .filter-chip.active span { color: var(--ink-2); }
.v5 .filter-spacer { flex: 1; }
.v5 .filter-select { display: inline-flex; align-items: center; gap: 5px; color: var(--muted); font-size: 9.5px; }
.v5 .filter-select .i { width: 11px; height: 11px; }
.v5 .table-wrap { min-height: 0; flex: 1; display: flex; flex-direction: column; margin-top: 12px; border: 1px solid var(--line); border-radius: 7px; background: var(--surface); overflow: hidden; box-shadow: 0 1px 2px rgba(16,24,40,.03); }
.v5 .table-head {
  flex: none; display: grid; grid-template-columns: 22px minmax(220px, 1fr) 62px 64px 58px 76px 26px;
  align-items: center; gap: 8px; min-height: 31px; padding: 0 10px;
  border-bottom: 1px solid var(--line); background: var(--surface-2);
  color: var(--dim); font-size: 8px; letter-spacing: .03em;
}
.v5 .table-head .chk { width: 13px; height: 13px; border: 1px solid var(--line-strong); border-radius: 3px; background: #fff; }
.v5 .table-body { min-height: 0; flex: 1; overflow-y: auto; }
.v5 .table-row {
  display: grid; grid-template-columns: 22px minmax(220px, 1fr) 62px 64px 58px 76px 26px;
  align-items: center; gap: 8px; min-height: 49px; padding: 0 10px;
  border-bottom: 1px solid #edf0f3; cursor: pointer;
  transition: background .12s ease;
}
.v5 .table-row:last-child { border-bottom: 0; }
.v5 .table-row:hover { background: #f8f9fb; }
.v5 .table-row.is-selected { background: #fff7f6; box-shadow: inset 2px 0 0 var(--red); }
.v5 .row-check { display: grid; place-items: center; }
.v5 .row-check input { width: 13px; height: 13px; margin: 0; accent-color: var(--red); cursor: pointer; }
.v5 .row-name { min-width: 0; display: flex; align-items: center; gap: 10px; }
.v5 .row-art { width: 44px; height: 30px; flex: none; overflow: hidden; border: 1px solid var(--line); border-radius: 3px; background: #f2f4f7; }
.v5 .row-art img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.78); }
.v5 .row-text { min-width: 0; }
.v5 .row-text b { display: block; color: var(--ink-2); font-size: 11px; font-weight: 550; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v5 .row-text small { display: block; margin-top: 2px; color: var(--muted); font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v5 .type-pill { display: inline-flex; align-items: center; width: fit-content; padding: 2px 6px; border-radius: 3px; background: #f2f4f7; color: var(--muted); font-size: 8px; }
.v5 .row-size, .v5 .row-date { color: #5f6673; font-family: "Cascadia Mono", monospace; font-size: 8px; white-space: nowrap; }
.v5 .row-state { display: inline-flex; align-items: center; gap: 5px; color: var(--dim); font-size: 8px; white-space: nowrap; }
.v5 .row-state i { width: 5px; height: 5px; border-radius: 50%; background: #b9c0ca; }
.v5 .row-state.on { color: var(--green); }
.v5 .row-state.on i { background: #12b76a; box-shadow: 0 0 0 3px rgba(18,183,106,.09); }
.v5 .switch {
  position: relative; width: 27px; height: 15px; flex: none;
  border: 1px solid #cfd5de; border-radius: 8px; background: #eef1f4;
}
.v5 .switch .switch-knob { position: absolute; top: 2px; left: 2px; width: 9px; height: 9px; border-radius: 50%; background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.18); transition: transform .16s ease, background .16s ease; }
.v5 .switch.on { border-color: var(--green); background: var(--green); }
.v5 .switch.on .switch-knob { transform: translateX(12px); }
.v5 .table-foot { flex: none; min-height: 31px; display: flex; align-items: center; gap: 10px; padding: 0 11px; border-top: 1px solid var(--line); background: var(--surface-2); color: var(--dim); font-size: 8px; }
.v5 .table-foot .spacer { flex: 1; }
.v5 .table-foot b { color: var(--ink-2); font-weight: 600; }
.v5 .table-foot button { color: var(--red); font-size: 8px; }
.v5 .table-foot button:hover { color: var(--red-deep); }
.v5 .preview {
  width: 344px; flex: none;
  margin: 20px 20px 0 0;
  border: 1px solid var(--line); border-radius: 7px;
  background: var(--surface);
  box-shadow: 0 1px 2px rgba(16,24,40,.03);
  padding: 15px;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 13px;
}
.v5 .preview-head { display: flex; align-items: center; justify-content: space-between; }
.v5 .preview-head span { color: var(--dim); font-size: 8px; letter-spacing: .08em; font-weight: 600; }
.v5 .preview-head button { width: 22px; height: 22px; display: grid; place-items: center; border-radius: 4px; color: var(--dim); }
.v5 .preview-head button:hover { background: var(--surface-2); color: var(--ink); }
.v5 .preview-art { position: relative; aspect-ratio: 16 / 9.2; border: 1px solid var(--line); border-radius: 4px; overflow: hidden; background: #f2f4f7; }
.v5 .preview-art img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.84) contrast(1.02); }
.v5 .preview-art .preview-label { position: absolute; left: 8px; bottom: 7px; padding: 2px 5px; border-radius: 2px; background: rgba(20,23,28,.62); color: #fff; font-family: "Cascadia Mono", monospace; font-size: 7px; letter-spacing: .07em; }
.v5 .preview-title { margin: 0; color: var(--ink); font-size: 17px; line-height: 1.3; font-weight: 650; letter-spacing: -.02em; }
.v5 .preview-meta { margin: 5px 0 0; color: var(--muted); font-size: 9px; }
.v5 .preview-meta span { margin: 0 4px; color: var(--faint); }
.v5 .status-card { display: flex; align-items: center; justify-content: space-between; gap: 9px; padding: 9px 10px; border: 1px solid #abefc6; border-radius: 5px; background: var(--green-soft); }
.v5 .status-copy { display: flex; align-items: center; gap: 7px; color: var(--green); font-size: 9.5px; font-weight: 600; }
.v5 .status-copy i { width: 6px; height: 6px; border-radius: 50%; background: #12b76a; box-shadow: 0 0 0 3px rgba(18,183,106,.1); }
.v5 .status-sub { margin-top: 3px; color: #4e7a63; font-size: 8px; font-weight: 400; }
.v5 .details { border-top: 1px solid var(--line); }
.v5 .detail-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f0f2f5; }
.v5 .detail-row span { color: var(--muted); font-size: 8.5px; }
.v5 .detail-row b { color: var(--ink-2); font-family: "Cascadia Mono", monospace; font-size: 8.5px; font-weight: 400; text-align: right; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.v5 .alias { display: flex; align-items: center; gap: 6px; padding: 8px 9px; border: 1px dashed var(--line-strong); border-radius: 4px; color: var(--dim); font-size: 8.5px; }
.v5 .alias .i { width: 12px; height: 12px; }
.v5 .alias span { color: var(--ink-2); }
.v5 .alias button { margin-left: auto; color: var(--blue); font-size: 8px; }
.v5 .group-box { padding: 9px 10px; border: 1px solid var(--line); border-radius: 4px; }
.v5 .group-head { display: flex; align-items: center; justify-content: space-between; color: var(--muted); font-size: 8.5px; }
.v5 .group-head b { color: var(--ink-2); font-family: "Cascadia Mono", monospace; font-size: 8px; font-weight: 400; }
.v5 .group-row { display: flex; align-items: center; gap: 6px; margin-top: 7px; color: var(--muted); font-size: 8.5px; }
.v5 .group-row i { width: 4px; height: 4px; border-radius: 50%; background: var(--faint); }
.v5 .group-row.on { color: var(--green); }
.v5 .group-row.on i { background: #12b76a; }
.v5 .note-box { padding: 9px 10px; border: 1px solid var(--line); border-radius: 4px; background: var(--surface-2); }
.v5 .note-box b { display: block; color: var(--muted); font-size: 8px; font-weight: 600; letter-spacing: .04em; }
.v5 .note-box p { margin: 5px 0 0; color: var(--ink-2); font-size: 9px; line-height: 1.6; }
.v5 .preview-actions { margin-top: auto; display: grid; grid-template-columns: 1fr 1fr; gap: 7px; padding-top: 3px; }
.v5 .preview-action { height: 31px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid var(--line-strong); border-radius: 4px; background: #fff; color: var(--ink-2); font-size: 9px; }
.v5 .preview-action:hover { border-color: #98a2b3; background: var(--surface-2); }
.v5 .preview-action.danger { color: var(--red); border-color: #fecdca; background: var(--red-soft); }
.v5 .preview-action.danger:hover { border-color: #f97066; }
.v5 .preview-action .i { width: 12px; height: 12px; }
.v5 .statusbar {
  height: 30px; flex: none; display: flex; align-items: center; gap: 14px;
  padding: 0 18px; border-top: 1px solid var(--line); background: var(--surface);
  color: var(--dim); font-family: "Cascadia Mono", monospace; font-size: 8px;
}
.v5 .statusbar .ok { display: inline-flex; align-items: center; gap: 5px; color: var(--green); }
.v5 .statusbar .ok i { width: 5px; height: 5px; border-radius: 50%; background: #12b76a; }
.v5 .statusbar .spacer { flex: 1; }
@media (max-width: 1280px) {
  .v5 .preview { width: 310px; margin-right: 14px; }
  .v5 .main { padding-left: 14px; }
  .v5 .top-search { width: 300px; }
}
"""


def build_v5():
    rows = MODS + EXTRA_MODS
    table_rows = "\n".join(row_v5(m, selected=(m["title"] == MODS[2]["title"])) for m in rows)
    selected = MODS[2]
    body = f"""
<div class="app">
  <header class="topbar">
    <div class="brand"><img src="assets/app-icon.png" alt=""><div><div class="brand-name">L4D2 MOD MANAGER</div><div class="brand-sub">LOCAL LIBRARY / v1.2.1</div></div></div>
    <label class="top-search">{icon('search')}<input data-search placeholder="搜索名称、别名、标签、物品…" aria-label="搜索模组"><span class="kbd">Ctrl K</span></label>
    <div class="top-spacer"></div>
    <span class="top-status"><i></i>本地库已连接</span>
    <div class="top-divider"></div>
    <button class="icon-button" type="button" aria-label="刷新" data-toast="已重新扫描 addons">{icon('refresh')}</button>
    <button class="icon-button" type="button" aria-label="设置" data-toast="打开设置">{icon('settings')}</button>
    <button class="top-button" type="button" data-toast="打开压缩包导入">{icon('upload')}导入</button>
    <button class="top-button" type="button" data-toast="打开工坊链接解析">{icon('download')}工坊</button>
    <button class="top-button primary" type="button" data-toast="正在启动 Left 4 Dead 2">{icon('play')}启动游戏</button>
  </header>
  <div class="body">
    <aside class="sidebar">
      <nav data-nav-group>
        <div class="side-label">Library / 模组库</div>
        <div class="side-nav">
          <button class="side-link active" data-nav type="button">{icon('grid')}全部模组<span class="n">128</span></button>
          <button class="side-link" data-nav type="button">{icon('users')}角色<span class="n">42</span></button>
          <button class="side-link" data-nav type="button">{icon('crosshair')}武器<span class="n">36</span></button>
          <button class="side-link" data-nav type="button">{icon('map')}地图<span class="n">18</span></button>
          <button class="side-link" data-nav type="button">{icon('box')}其他<span class="n">32</span></button>
        </div>
        <div class="side-gap"></div>
        <div class="side-label">Smart lists / 智能列表</div>
        <div class="side-nav">
          <button class="side-link" data-nav type="button">{icon('check')}已启用<span class="n">43</span></button>
          <button class="side-link" data-nav type="button">{icon('x')}已停用<span class="n">85</span></button>
          <button class="side-link" data-nav type="button">{icon('clock')}最近添加<span class="n">12</span></button>
          <button class="side-link" data-nav type="button">{icon('alert')}需要处理<span class="n">1</span></button>
        </div>
        <div class="side-gap"></div>
        <div class="side-label">Collections / 合集</div>
        <div class="side-list">
          <button type="button"><i></i>周末混战<span>12</span></button>
          <button type="button"><i></i>霓虹夜<span>8</span></button>
          <button type="button"><i></i>原版增强<span>21</span></button>
          <button type="button"><i></i>未分类<span>32</span></button>
        </div>
      </nav>
      <div class="side-spacer"></div>
      <div class="health-card">
        <div class="health-head">{icon('shield')}库状态良好</div>
        <div class="health-copy">128 个模组已纳管，仅 1 组外观需要清理。</div>
        <div class="health-meter"><i></i></div>
      </div>
      <div class="side-foot"><span>128 FILES</span><span>4.8 GB</span></div>
    </aside>
    <main class="main">
      <div class="page-head">
        <div>
          <div class="crumb">模组库 {icon('chevron-right')} <b>全部模组</b></div>
          <h1>全部模组 <span>128 ITEMS</span></h1>
          <p>按最近更新显示 <b>12</b> 项 · 已启用 3 项 · 同组互斥已开启</p>
        </div>
        <div class="page-actions">
          <button class="mini-button" type="button" data-toast="扫描完成">{icon('refresh')}扫描</button>
          <button class="mini-button" type="button" data-toast="整理规则已准备好">{icon('sliders')}整理规则</button>
        </div>
      </div>
      <div class="filterbar">
        <button class="filter-chip active" type="button" data-chip>全部 <span>128</span></button>
        <button class="filter-chip" type="button" data-chip>已启用 <span>43</span></button>
        <button class="filter-chip" type="button" data-chip>未启用 <span>85</span></button>
        <button class="filter-chip" type="button" data-chip>有更新 <span>6</span></button>
        <div class="filter-spacer"></div>
        <button class="filter-select" type="button" data-toast="按最近更新排序">最近更新 {icon('chevron-down')}</button>
        <button class="filter-select" type="button" data-toast="筛选面板已打开">筛选 {icon('sliders')}</button>
      </div>
      <div class="table-wrap">
        <div class="table-head"><span class="chk"></span><span>模组</span><span>类别</span><span>大小</span><span>更新</span><span>状态</span><span></span></div>
        <div class="table-body scroll-y">
          {table_rows}
        </div>
        <div class="table-foot"><span>显示 <b>12</b> / 128</span><span>·</span><span>已选 0 项</span><span class="spacer"></span><button type="button" data-toast="加载更多模组">加载更多</button></div>
      </div>
    </main>
    <aside class="preview">
      <div class="preview-head"><span>DETAIL / 模组详情</span><button type="button" aria-label="关闭详情" data-toast="详情面板可收起">{icon('x')}</button></div>
      <div class="preview-art"><img data-detail-img src="assets/mods/{selected['img']}" alt="已选模组预览"><span class="preview-label">CATALOG PREVIEW</span></div>
      <div>
        <h2 class="preview-title" data-detail-title>{escape(selected['title'])}</h2>
        <p class="preview-meta"><span data-detail-meta>{selected['cat']} / {selected['item']}</span><span>·</span><span data-detail-size>{selected['size']}</span></p>
      </div>
      <div class="status-card">
        <div><div class="status-copy"><i></i>已启用</div><div class="status-sub">游戏内附加内容菜单已同步</div></div>
        {switch(True, label='切换 VRC Plum 启用状态')}
      </div>
      <div class="details">
        <div class="detail-row"><span>文件</span><b data-detail-file>{selected['file']}</b></div>
        <div class="detail-row"><span>加入日期</span><b>2026-11-07</b></div>
        <div class="detail-row"><span>来源</span><b>本地导入</b></div>
        <div class="detail-row"><span>冲突组</span><b>Ellis · 外观</b></div>
      </div>
      <div class="alias">{icon('tag')}别名 <span>夏日甜点屋</span><button type="button" data-toast="编辑别名">编辑</button></div>
      <div class="group-box">
        <div class="group-head"><span>同组模组</span><b>1 / 6 ACTIVE</b></div>
        <div class="group-row on"><i></i>VRC プラム Plum replace ellis</div>
        <div class="group-row"><i></i>Koharu [Replace Ellis]</div>
        <div class="group-row"><i></i>VRC lime 甜点屋 打歌服</div>
      </div>
      <div class="note-box"><b>备注 / NOTE</b><p>夏日甜点屋主题外观，建议与 VRC 系列角色模型搭配使用。文件已校验，无缺失依赖。</p></div>
      <div class="preview-actions">
        <button class="preview-action" type="button" data-toast="已在资源管理器中显示">{icon('folder')}打开文件夹</button>
        <button class="preview-action danger" type="button" data-toast="删除前会移动到回收站">{icon('trash')}移入回收站</button>
      </div>
    </aside>
  </div>
  <footer class="statusbar">
    <span class="ok"><i></i>LOCAL LIBRARY CONNECTED</span><span>128 MODS · 43 ENABLED</span><span>游戏未运行</span><span class="spacer"></span><span>E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2\\left4dead2\\addons</span>
  </footer>
</div>
"""
    return page("05 INDEX / 索引", "v5", V5_CSS, body)


DIRECTIONS = [
    dict(
        num="01", name="BLACKSITE", cn="战术档案", href="v1.html", img="screenshots/v1.png",
        lead="保留末世军械库的气质，把它做成一台真正的本地 mod 控制台。",
        desc="石墨黑与信号绿取代高饱和的末世绿；四区结构把“导航、筛选、内容、详情”分开。选中模组后，详情与同组互斥关系就地展开。",
        tags=["石墨黑", "信号绿", "发丝线", "常驻详情"],
        pros="品牌延续性最强；状态与冲突可见；高频操作有工作台感。",
        cons="四区布局，1100px 窗口下需要折叠详情；QSS 需要精细控制。",
        best="长期用户 / 高密度管理",
        rec=True,
    ),
    dict(
        num="02", name="SAFEHOUSE", cn="安全屋", href="v2.html", img="screenshots/v2.png",
        lead="像翻一本模组档案册，而不是打开一台机器。",
        desc="米纸色、油墨黑与安全红；大标题用衬线写，卡片有纸张与硬阴影。分类导航退到侧栏，物品 chips 让“同一个 Ellis”变成一次轻松的翻页。",
        tags=["米纸", "衬线", "安全红", "纸感"],
        pros="和普通工具差异最大；阅读性最好；截图传播性最好。",
        cons="浅色在夜间游戏场景可能刺眼；纸纹和硬阴影在 Qt 里最容易做“假”。",
        best="轻度收藏用户 / 想让产品更有人味",
        rec=False,
    ),
    dict(
        num="03", name="WORKSHOP", cn="工坊中枢", href="v3.html", img="screenshots/v3.png",
        lead="Steam 用户零学习成本的入口，下载和同步拥有天然的位置。",
        desc="深海军蓝与亮青；顶部全局导航，右侧常驻同步中心。Hero 展示当前外观合集，下载队列、订阅检查和本地概况彼此不抢戏。",
        tags=["海军蓝", "工坊", "同步中心", "大 Hero"],
        pros="熟悉、稳妥；工坊下载是主角；开发成本相对可控。",
        cons="品牌个性最弱，容易像 Steam 的皮肤；右侧栏占走 332px。",
        best="工坊重度用户 / 下载为主",
        rec=False,
    ),
    dict(
        num="04", name="LOADOUT LAB", cn="配装台", href="v4.html", img="screenshots/v4.png",
        lead="从“管理模组”升级为“管理今晚怎么玩”。",
        desc="顶部是四个配装槽位，下面是模组库和冲突中心。预设可以一键切换整套外观；互斥组不再藏在提示里，而是配装的一部分。",
        tags=["石墨蓝", "薄荷绿", "配装槽", "预设"],
        pros="把互斥与一键切换讲得最清楚；任务导向；天然支持场景预设。",
        cons="信息架构改动最大；需要新增配装/预设数据模型；小屏更紧。",
        best="高频切换玩法 / 愿意升级产品概念",
        rec=False,
    ),
    dict(
        num="05", name="INDEX", cn="索引", href="v5.html", img="screenshots/v5.png",
        lead="给 100+ 模组库的一张工作台。",
        desc="冷白、墨黑、品牌红；左侧分类，中间数据表，右侧详情。支持多选、排序、批量操作和键盘流，封面被压缩成一行缩略图，把空间还给比较。",
        tags=["冷白", "数据表", "多选", "键盘流"],
        pros="扫读与批量操作最强；浅色更耐看；最容易扩到 300+ 模组。",
        cons="游戏氛围弱；封面不再承担识别；长列表需要虚拟化。",
        best="收藏很多 / 重整理与清理",
        rec=False,
    ),
]

CRITERIA = [
    ("品牌辨识度", [5, 4, 3, 4, 2]),
    ("浏览效率", [4, 3, 4, 3, 5]),
    ("状态透明", [5, 3, 3, 5, 4]),
    ("工坊体验", [3, 3, 5, 3, 3]),
    ("扩展能力", [4, 3, 4, 3, 5]),
    ("实现成本（越高越轻）", [3, 2, 4, 1, 4]),
]

REVIEW_CSS = r"""
:root {
  --paper: #f4f1ea;
  --paper-2: #ece7dc;
  --surface: #fbf9f5;
  --ink: #17191c;
  --ink-2: #34372f;
  --muted: #696b61;
  --dim: #8f8d81;
  --line: #d9d1c2;
  --line-strong: #b9ae9a;
  --red: #c9362a;
  --red-deep: #9e2118;
  --olive: #49533b;
  --green: #5d6b3e;
  --dark: #141619;
  --sans: "Noto Sans SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
  --serif: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
  --mono: "Cascadia Mono", "Consolas", monospace;
}
body.review {
  background:
    radial-gradient(rgba(23,25,28,.036) .6px, transparent .7px) 0 0 / 4px 4px,
    var(--paper);
  color: var(--ink);
  font-family: var(--sans);
  overflow-y: auto;
  min-height: 100vh;
}
.review a { color: inherit; }
.review .top-strip {
  height: 40px; display: flex; align-items: center; gap: 18px;
  padding: 0 34px; background: var(--dark); color: #cdd2cb;
}
.review .top-brand { display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-size: 9px; letter-spacing: .12em; }
.review .top-brand img { width: 17px; height: 17px; filter: grayscale(1); opacity: .8; }
.review .top-brand b { color: #f2f5ee; font-weight: 400; }
.review .top-strip .nav { display: flex; gap: 16px; margin-left: 20px; }
.review .top-strip .nav a { color: #858d84; font-size: 9px; letter-spacing: .04em; }
.review .top-strip .nav a:hover { color: #f1f4ee; }
.review .top-strip .right { margin-left: auto; display: flex; align-items: center; gap: 14px; color: #747d75; font-family: var(--mono); font-size: 8px; letter-spacing: .08em; }
.review .top-strip .right b { color: #d8ded5; font-weight: 400; }
.review .wrap { width: min(1280px, calc(100% - 72px)); margin: 0 auto; }
.review .hero {
  display: grid; grid-template-columns: minmax(0, 1fr) 292px; gap: 50px;
  padding: 48px 0 44px; border-bottom: 1px solid var(--line);
}
.review .kicker { display: flex; align-items: center; gap: 9px; color: var(--red); font-family: var(--mono); font-size: 9px; letter-spacing: .16em; }
.review .kicker::before { content: ""; width: 24px; height: 1px; background: var(--red); }
.review .hero h1 {
  margin: 17px 0 0;
  font-family: var(--serif); font-size: clamp(48px, 5.8vw, 74px); line-height: 1.1; font-weight: 900; letter-spacing: -.03em;
}
.review .hero h1 em { color: var(--red); font-style: normal; }
.review .hero p { max-width: 560px; margin: 18px 0 0; color: var(--muted); font-size: 12px; line-height: 1.85; }
.review .hero-meta { align-self: end; padding-bottom: 8px; }
.review .meta-row { display: flex; align-items: baseline; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--line); }
.review .meta-row span { width: 56px; flex: none; color: var(--dim); font-family: var(--mono); font-size: 8px; letter-spacing: .08em; }
.review .meta-row b { color: var(--ink-2); font-size: 10px; font-weight: 500; line-height: 1.55; }
.review .meta-note { margin-top: 14px; color: var(--dim); font-size: 9px; line-height: 1.7; }
.review .section { padding: 38px 0 0; }
.review .section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; margin-bottom: 18px; }
.review .section-head .label { color: var(--red); font-family: var(--mono); font-size: 9px; letter-spacing: .13em; }
.review .section-head h2 { margin: 6px 0 0; font-family: var(--serif); font-size: 28px; font-weight: 900; letter-spacing: -.02em; }
.review .section-head p { max-width: 430px; margin: 0 0 2px; color: var(--muted); font-size: 10px; line-height: 1.7; text-align: right; }
.review .baseline {
  display: grid; grid-template-columns: 1.1fr .9fr; gap: 30px;
  align-items: stretch;
}
.review .baseline-figure { margin: 0; border: 1px solid var(--line-strong); background: #0b0d0f; box-shadow: 6px 6px 0 rgba(80,67,49,.1); }
.review .baseline-figure img { width: 100%; aspect-ratio: 16 / 10; object-fit: cover; object-position: top left; }
.review .baseline-figure figcaption { display: flex; align-items: center; justify-content: space-between; padding: 9px 12px; border-top: 1px solid #2c2d2c; color: #8d968b; font-family: var(--mono); font-size: 8px; }
.review .baseline-figure figcaption b { color: #cbd4c4; font-weight: 400; }
.review .findings { display: flex; flex-direction: column; justify-content: center; }
.review .finding { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 10px; padding: 13px 0; border-bottom: 1px solid var(--line); }
.review .finding:first-child { border-top: 1px solid var(--line); }
.review .finding .n { color: var(--red); font-family: var(--mono); font-size: 9px; padding-top: 2px; }
.review .finding b { color: var(--ink-2); font-size: 11px; font-weight: 600; }
.review .finding p { margin: 4px 0 0; color: var(--muted); font-size: 9.5px; line-height: 1.6; }
.review .note-strip {
  display: flex; align-items: center; gap: 8px; margin-top: 14px; padding: 9px 11px;
  border: 1px dashed var(--line-strong); color: var(--muted); font-size: 9px;
}
.review .note-strip b { color: var(--ink-2); font-weight: 600; }
.review .dir-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
.review .dir-card {
  grid-column: span 1;
  min-width: 0; display: flex; flex-direction: column;
  border: 1px solid var(--line); background: var(--surface); box-shadow: 4px 4px 0 rgba(80,67,49,.08);
}
.review .dir-card.wide { grid-column: span 2; display: grid; grid-template-columns: 1fr 1fr; }
.review .dir-card.wide .shot { border-right: 1px solid var(--line); border-bottom: 0; }
.review .dir-card.wide .shot img { width: 100%; height: 100%; aspect-ratio: auto; object-fit: cover; }
.review .dir-card.wide .dir-body { padding: 20px 22px 18px; }
.review .dir-card.wide .dir-name { font-size: 20px; }
.review .dir-card.wide .dir-lead { font-size: 14px; }
.review .shot { position: relative; display: block; overflow: hidden; border-bottom: 1px solid var(--line); background: #0d0f12; }
.review .shot img { width: 100%; aspect-ratio: 16 / 10; object-fit: cover; object-position: top left; transition: transform .3s ease, filter .3s ease; }
.review .shot:hover img { transform: scale(1.018); filter: saturate(1.03); }
.review .shot .open {
  position: absolute; right: 9px; bottom: 9px;
  padding: 5px 7px; border: 1px solid rgba(255,255,255,.32);
  background: rgba(10,12,14,.68); color: #f1f3eb;
  font-family: var(--mono); font-size: 7.5px; letter-spacing: .05em;
  opacity: 0; transform: translateY(3px); transition: opacity .18s ease, transform .18s ease;
  backdrop-filter: blur(4px);
}
.review .shot:hover .open { opacity: 1; transform: translateY(0); }
.review .dir-body { display: flex; flex-direction: column; flex: 1; padding: 14px 15px 12px; }
.review .dir-top { display: flex; align-items: center; gap: 7px; min-height: 18px; }
.review .dir-num { color: var(--red); font-family: var(--mono); font-size: 9px; }
.review .dir-rec { padding: 2px 6px; background: var(--red); color: #fff7ef; font-family: var(--mono); font-size: 7px; letter-spacing: .07em; }
.review .dir-name { margin: 8px 0 0; color: var(--ink); font-family: var(--sans); font-size: 16px; line-height: 1.2; font-weight: 700; letter-spacing: -.02em; }
.review .dir-name span { margin-left: 5px; color: var(--muted); font-family: var(--serif); font-size: 14px; font-weight: 600; letter-spacing: 0; }
.review .dir-lead { margin: 8px 0 0; color: var(--ink-2); font-family: var(--serif); font-size: 12.5px; font-weight: 600; line-height: 1.55; }
.review .dir-desc { margin: 6px 0 0; color: var(--muted); font-size: 9.5px; line-height: 1.62; }
.review .dir-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 10px; }
.review .dir-tags span { padding: 2px 5px; border: 1px solid var(--line); color: var(--muted); font-size: 8px; }
.review .dir-foot { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: auto; padding-top: 12px; }
.review .pros, .review .cons { padding-top: 7px; border-top: 1px solid var(--line); }
.review .pros b, .review .cons b { display: block; font-size: 8px; font-weight: 600; letter-spacing: .02em; }
.review .pros b { color: var(--green); }
.review .cons b { color: var(--red-deep); }
.review .pros p, .review .cons p { margin: 4px 0 0; color: var(--muted); font-size: 8.5px; line-height: 1.5; }
.review .best-for { margin-top: 8px; color: var(--dim); font-family: var(--mono); font-size: 7.5px; letter-spacing: .02em; }
.review .decision-card {
  display: grid; grid-template-columns: 1.12fr .88fr; gap: 28px;
  min-width: 0; margin-top: 24px;
  padding: 25px 28px; background: var(--dark); color: #eef1e9;
  border: 1px solid #272a27; box-shadow: 4px 4px 0 rgba(80,67,49,.1);
}
.review .decision-card .label { color: #d15a4e; font-family: var(--mono); font-size: 8px; letter-spacing: .15em; }
.review .decision-card h3 { margin: 9px 0 0; font-family: var(--serif); font-size: 27px; line-height: 1.18; font-weight: 900; letter-spacing: -.02em; }
.review .decision-card p { max-width: 510px; margin: 10px 0 0; color: #9da497; font-size: 9.5px; line-height: 1.7; }
.review .decision-card .decision-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 0; }
.review .decision-list div { padding-top: 9px; border-top: 1px solid #333732; }
.review .decision-list b { display: block; color: #cbd2c6; font-size: 9px; font-weight: 500; }
.review .decision-list span { display: block; margin-top: 3px; color: #727a70; font-size: 8px; line-height: 1.5; }
.review .decision-card a { margin-top: 18px; display: inline-flex; align-items: center; gap: 6px; width: fit-content; color: #f4c6bc; font-size: 9px; }
.review .decision-card a:hover { color: #fff; }
.review .compare-panel { border: 1px solid var(--line); background: var(--surface); box-shadow: 4px 4px 0 rgba(80,67,49,.07); overflow-x: auto; }
.review table { width: 100%; border-collapse: collapse; min-width: 760px; }
.review th, .review td { padding: 11px 13px; border-bottom: 1px solid #eae4d8; text-align: center; vertical-align: middle; }
.review thead th { background: var(--paper-2); color: var(--muted); font-family: var(--mono); font-size: 8px; letter-spacing: .06em; font-weight: 400; }
.review thead th:first-child { text-align: left; }
.review tbody tr:last-child td { border-bottom: 0; }
.review td:first-child, .review th:first-child { text-align: left; }
.review tbody td:first-child { color: var(--ink-2); font-size: 10px; font-weight: 500; }
.review tbody tr:hover { background: #faf7f0; }
.review .score { display: inline-flex; align-items: center; justify-content: center; gap: 4px; }
.review .bars { display: inline-flex; gap: 2px; }
.review .bars i { width: 8px; height: 5px; background: #e0d9cc; }
.review .bars i.on { background: var(--red); }
.review .score b { color: var(--muted); font-family: var(--mono); font-size: 8px; font-weight: 400; }
.review .table-note { padding: 8px 13px; border-top: 1px solid var(--line); color: var(--dim); font-size: 8px; }
.review .recommend {
  display: grid; grid-template-columns: 1.1fr .9fr; gap: 0; margin-top: 38px;
  border: 1px solid var(--line); background: var(--surface); box-shadow: 5px 5px 0 rgba(80,67,49,.08);
}
.review .recommend-main { padding: 28px 30px; }
.review .recommend-main .label { color: var(--red); font-family: var(--mono); font-size: 8px; letter-spacing: .13em; }
.review .recommend-main h2 { margin: 9px 0 0; font-family: var(--serif); font-size: 31px; font-weight: 900; letter-spacing: -.02em; }
.review .recommend-main h2 span { color: var(--red); }
.review .recommend-main p { margin: 11px 0 0; color: var(--muted); font-size: 10px; line-height: 1.8; }
.review .recommend-main .callout { margin-top: 15px; padding: 12px 14px; border-left: 2px solid var(--red); background: var(--paper-2); color: var(--ink-2); font-family: var(--serif); font-size: 12px; font-weight: 600; line-height: 1.6; }
.review .questions { border-left: 1px solid var(--line); background: var(--paper-2); padding: 28px 26px; }
.review .questions .label { color: var(--olive); font-family: var(--mono); font-size: 8px; letter-spacing: .13em; }
.review .questions h3 { margin: 9px 0 4px; font-family: var(--serif); font-size: 20px; font-weight: 800; }
.review .question { padding: 12px 0; border-bottom: 1px solid var(--line); }
.review .question:last-child { border-bottom: 0; }
.review .question b { display: block; color: var(--ink-2); font-size: 10px; font-weight: 600; }
.review .question p { margin: 4px 0 0; color: var(--muted); font-size: 9px; line-height: 1.6; }
.review .next { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-top: 38px; }
.review .next-step { padding-top: 12px; border-top: 1px solid var(--line-strong); }
.review .next-step .n { color: var(--red); font-family: var(--mono); font-size: 8px; }
.review .next-step b { display: block; margin-top: 7px; color: var(--ink-2); font-size: 10px; font-weight: 600; }
.review .next-step p { margin: 5px 0 0; color: var(--muted); font-size: 9px; line-height: 1.6; }
.review .footer { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-top: 50px; padding: 16px 0 52px; border-top: 1px solid var(--line); color: var(--dim); font-family: var(--mono); font-size: 8px; }
.review .footer a { color: var(--red-deep); }
.review .footer a:hover { color: var(--red); }
@media (max-width: 980px) {
  .review .wrap { width: min(100% - 36px, 860px); }
  .review .hero { grid-template-columns: 1fr; gap: 30px; }
  .review .hero-meta { max-width: 440px; }
  .review .baseline { grid-template-columns: 1fr; }
  .review .dir-grid { grid-template-columns: 1fr; }
  .review .dir-card, .review .dir-card.wide { grid-column: span 1; grid-template-columns: 1fr; }
  .review .dir-card.wide .shot { border-right: 0; border-bottom: 1px solid var(--line); }
  .review .decision-card { grid-template-columns: 1fr; }
  .review .recommend { grid-template-columns: 1fr; }
  .review .questions { border-left: 0; border-top: 1px solid var(--line); }
  .review .next { grid-template-columns: repeat(2, 1fr); }
}
"""


def review_cards():
    out = []
    for d in DIRECTIONS:
        rec = '<span class="dir-rec">我的建议</span>' if d["rec"] else ""
        tags = "".join(f"<span>{escape(t)}</span>" for t in d["tags"])
        wide = " wide" if d["num"] == "05" else ""
        out.append(f"""
<article class="dir-card{wide}">
  <a class="shot" href="{d['href']}" target="_blank" rel="noreferrer" aria-label="打开 {d['name']} 原型">
    <img src="{d['img']}" alt="{d['name']} 主界面样稿">
    <span class="open">OPEN PROTOTYPE ↗</span>
  </a>
  <div class="dir-body">
    <div class="dir-top"><span class="dir-num">{d['num']}</span>{rec}</div>
    <h3 class="dir-name">{d['name']} <span>{d['cn']}</span></h3>
    <p class="dir-lead">{escape(d['lead'])}</p>
    <p class="dir-desc">{escape(d['desc'])}</p>
    <div class="dir-tags">{tags}</div>
    <div class="dir-foot">
      <div class="pros"><b>强项</b><p>{escape(d['pros'])}</p></div>
      <div class="cons"><b>代价</b><p>{escape(d['cons'])}</p></div>
    </div>
    <div class="best-for">BEST FOR / {escape(d['best'])}</div>
  </div>
</article>""")
    return "\n".join(out)


def review_table():
    head = "".join(f"<th>{d['num']} {d['name']}</th>" for d in DIRECTIONS)
    rows = []
    for label, scores in CRITERIA:
        cells = []
        for score in scores:
            blocks = "".join('<i class="on"></i>' if i < score else "<i></i>" for i in range(5))
            cells.append(f'<td><span class="score"><span class="bars">{blocks}</span><b>{score}</b></span></td>')
        rows.append(f"<tr><td>{label}</td>{''.join(cells)}</tr>")
    return f"""
<div class="compare-panel">
  <table>
    <thead><tr><th>评估维度</th>{head}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <div class="table-note">1–5 为相对评估，用来帮助取舍，不是技术结论。实现成本一行的“越高”代表越容易落地。</div>
</div>"""


def build_review():
    cards = review_cards()
    table = review_table()
    body = f"""
<div class="top-strip">
  <div class="top-brand"><img src="assets/app-icon.png" alt=""><b>L4D2 MOD MANAGER</b> <span>/ VISUAL REVIEW</span></div>
  <nav class="nav"><a href="#baseline">现状</a><a href="#directions">五个方向</a><a href="#compare">对比</a><a href="#next">下一步</a></nav>
  <div class="right"><span>DESIGN REVIEW 01</span><b>2026.11.18</b></div>
</div>
<main class="wrap">
  <header class="hero">
    <div>
      <div class="kicker">VISUAL REFACTOR / 视觉重构</div>
      <h1>把军械库，<br><em>重新做一遍。</em></h1>
      <p>五个方向，同一份真实内容。先确定气质与信息架构，再讨论 Qt 重绘还是 WebView。所有样稿都只改界面，不动业务逻辑。</p>
    </div>
    <aside class="hero-meta">
      <div class="meta-row"><span>SCOPE</span><b>主界面 · 1440 × 900</b></div>
      <div class="meta-row"><span>BASELINE</span><b>v1.2.1 / PySide6</b></div>
      <div class="meta-row"><span>DELIVERY</span><b>5 个 HTML 原型 + 5 张截图</b></div>
      <div class="meta-row"><span>CHANGED</span><b>0 行业务代码</b></div>
      <div class="meta-note">原型支持卡片选择、开关、导航高亮与 Ctrl + K。数据为样稿内容，缩略图取自当前版本截图。</div>
    </aside>
  </header>

  <section class="section" id="baseline">
    <div class="section-head">
      <div><div class="label">00 / BASELINE</div><h2>先看清现在的问题</h2></div>
      <p>不是“换个黑色皮肤”。当前界面的主要阻力在层级、主次和状态反馈，而不是颜色本身。</p>
    </div>
    <div class="baseline">
      <figure class="baseline-figure">
        <img src="assets/current-ui.webp" alt="当前版本主界面">
        <figcaption><span>当前截图 / <b>v1.2.1</b></span><span>1276 × 936</span></figcaption>
      </figure>
      <div class="findings">
        <div class="finding"><span class="n">01</span><div><b>三级导航挤在左侧</b><p>级别、分类、物品三列并排，主卡片区被压到不足 900px，卡片只能做小。</p></div></div>
        <div class="finding"><span class="n">02</span><div><b>启用状态太轻</b><p>绿点和细勾选不足以支撑“一键切换”这个核心动作，用户需要二次确认。</p></div></div>
        <div class="finding"><span class="n">03</span><div><b>工具条所有动作同权</b><p>搜索、排序、刷新、导入、工坊、启动挤在一行，最常用的“启动”没有真正的视觉优先。</p></div></div>
        <div class="finding"><span class="n">04</span><div><b>冲突结果藏在提示里</b><p>同组互斥的结果主要靠状态栏和操作后提示，用户无法在操作前预见会影响哪些模组。</p></div></div>
      </div>
    </div>
    <div class="note-strip"><b>保留：</b>本地库优先、模组封面、同组互斥、一键管理、工坊下载、设置与回收站；<b>重做：</b>导航层级、卡片信息密度、详情/冲突呈现。</div>
  </section>

  <section class="section" id="directions">
    <div class="section-head">
      <div><div class="label">01–05 / DIRECTIONS</div><h2>五个方向，不是五套皮肤</h2></div>
      <p>每版都重新安排了信息优先级：谁先出现、详情放在哪、冲突如何被看见。点击截图可打开可交互原型。</p>
    </div>
    <div class="dir-grid">
      {cards}
    </div>
    <aside class="decision-card">
      <div>
        <div class="label">DECISION AHEAD / 不是第六个方案</div>
        <h3>你选气质，<br>我补实现。</h3>
        <p>这五版都能落地，但成本与终态不同。先确认视觉方向和信息架构，再谈 Qt 原生重绘、WebView 或 Tauri；现在换栈会把视觉评审变成技术赌注。</p>
      </div>
      <div>
        <div class="decision-list">
          <div><b>先定方向</b><span>选择 1 个主方案，指出想保留的局部。</span></div>
          <div><b>再补状态</b><span>补齐设置、下载、导入、空态与错误态。</span></div>
          <div><b>最后选型</b><span>用真实复杂度评估 Qt / Web 方案。</span></div>
        </div>
        <a href="#compare">看相对评估 {icon('arrow-right')}</a>
      </div>
    </aside>
  </section>

  <section class="section" id="compare">
    <div class="section-head">
      <div><div class="label">COMPARISON / 相对评估</div><h2>把取舍放在一张表上</h2></div>
      <p>没有全面胜出的方案。这里评估的是“作为当前产品的一次重构”，不是抽象的视觉排名。</p>
    </div>
    {table}
  </section>

  <section class="recommend">
    <div class="recommend-main">
      <div class="label">MY RECOMMENDATION / 我的一票</div>
      <h2>首选 <span>01 BLACKSITE</span>。</h2>
      <p>它最像这条产品线本来应该长成的样子：保留末世与军械库的气质，却把可读性、层级、详情和冲突都拉回到工作流里。对现有用户迁移成本最低，也最适合继续叠加工坊、下载和合集。</p>
      <div class="callout">如果“快速上手”和工坊下载比品牌气质更重要，选 03；如果模组量会很快到 300+，05 的索引能力值得优先。</div>
    </div>
    <div class="questions">
      <div class="label">NEED YOUR CALL / 需要你拍板</div>
      <h3>三个问题</h3>
      <div class="question"><b>01. 你更想要哪种气质？</b><p>末日军械库的控制台，还是更像日常软件的档案册/工具？</p></div>
      <div class="question"><b>02. 模组量会到 300+ 吗？</b><p>如果会，V5 的表格和批量操作应该成为主结构，而不是附属视图。</p></div>
      <div class="question"><b>03. 要不要把“配装/预设”提上路线？</b><p>如果愿意增加数据模型，V4 能把互斥规则变成真正的卖点。</p></div>
    </div>
  </section>

  <section class="section" id="next">
    <div class="section-head">
      <div><div class="label">NEXT / 下一步</div><h2>选定方向之后</h2></div>
      <p>本轮交付停在视觉与信息架构；下面的顺序可以避免在技术选型上过早下注。</p>
    </div>
    <div class="next">
      <div class="next-step"><div class="n">STEP 01</div><b>你选一个主方向</b><p>直接说编号，或指出“01 的骨架 + 05 的表格”这类组合；也可以只保留某个局部。</p></div>
      <div class="next-step"><div class="n">STEP 02</div><b>补齐状态覆盖</b><p>设置、详情、下载、压缩包导入、迁移、空态、错误态；统一间距、字号、控件状态与快捷键。</p></div>
      <div class="next-step"><div class="n">STEP 03</div><b>技术实现评估</b><p>在 PySide6 原生重绘、QWebEngine、Tauri 之间用真实复杂度比较；明确动画、字体、打包与体积成本。</p></div>
      <div class="next-step"><div class="n">STEP 04</div><b>增量落地</b><p>不动业务逻辑，先换壳和主界面；再拆组件，最后处理动效与响应式。</p></div>
    </div>
  </section>

  <footer class="footer">
    <span>L4D2 MOD MANAGER · VISUAL DIRECTIONS · 2026.11.18</span>
    <span><a href="assets/overview.png" target="_blank">五版总览图</a> · <a href="v1.html" target="_blank">01</a> · <a href="v2.html" target="_blank">02</a> · <a href="v3.html" target="_blank">03</a> · <a href="v4.html" target="_blank">04</a> · <a href="v5.html" target="_blank">05</a></span>
  </footer>
</main>
"""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>L4D2 Mod Manager · 视觉方案评审</title>
<link rel="stylesheet" href="assets/base.css">
<style>{REVIEW_CSS}</style>
</head>
<body class="review">
{body}
</body>
</html>
"""


def main():
    (ROOT / "v1.html").write_text(build_v1(), encoding="utf-8")
    (ROOT / "v2.html").write_text(build_v2(), encoding="utf-8")
    (ROOT / "v3.html").write_text(build_v3(), encoding="utf-8")
    (ROOT / "v4.html").write_text(build_v4(), encoding="utf-8")
    (ROOT / "v5.html").write_text(build_v5(), encoding="utf-8")
    (ROOT / "review.html").write_text(build_review(), encoding="utf-8")
    print("wrote v1.html, v2.html, v3.html, v4.html, v5.html, review.html")


if __name__ == "__main__":
    main()
