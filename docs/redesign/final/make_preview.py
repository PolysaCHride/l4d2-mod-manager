# -*- coding: utf-8 -*-
"""Build the BLACKSITE final preview.

Gates:
  01 TitleBar    brand + global search (x aligned to main) + workspace tabs + status + launch + controls
  02 Rail        全部 / 角色 / 特感 / 武器 / 地图 / 其他 + 一键整理 + 设置
  03 FilterPanel context filter; collapsible groups; status only here; no local search
  04 MainHeader  static breadcrumb + item title (no slogan line)
  05 ActionBar   count / view / sort / refresh
  06 ModGrid     library grid + in-window import and download
  07 Inspector   context-menu functions moved in (folder / workshop / more / delete)
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "v1.html"
OUT = ROOT / "preview.html"

EXTRA_SYMBOLS = """
  <symbol id="i-infected" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="6.9" r="2.5"/><circle cx="7.6" cy="15.3" r="2.5"/><circle cx="16.4" cy="15.3" r="2.5"/></symbol>
  <symbol id="i-link" viewBox="0 0 24 24"><path d="M10.5 13.5a4 4 0 0 0 5.7 0l2.6-2.6a4 4 0 0 0-5.7-5.7l-1.4 1.4"/><path d="M13.5 10.5a4 4 0 0 0-5.7 0l-2.6 2.6a4 4 0 0 0 5.7 5.7l1.4-1.4"/></symbol>
"""

TOP_BAR = r'''
<header class="topbar">
  <div class="title-left">
    <img src="assets/app-icon.png" alt="">
    <span class="brand-name">L4D2 // ARMORY</span>
  </div>
  <label class="top-search">
    <svg class="i" aria-hidden="true"><use href="#i-search"></use></svg>
    <input data-search placeholder="搜索模组、别名、标签、文件" aria-label="搜索模组">
    <span class="kbd">Ctrl K</span>
  </label>
  <div class="ws-tabs" role="tablist" aria-label="工作区">
    <button class="ws-tab active" type="button" role="tab" aria-selected="true" data-ws="library">
      <svg class="i" aria-hidden="true"><use href="#i-grid"></use></svg><span>浏览</span>
    </button>
    <button class="ws-tab" type="button" role="tab" aria-selected="false" data-ws="import">
      <svg class="i" aria-hidden="true"><use href="#i-archive"></use></svg><span>导入压缩包</span>
    </button>
    <button class="ws-tab" type="button" role="tab" aria-selected="false" data-ws="download">
      <svg class="i" aria-hidden="true"><use href="#i-download"></use></svg><span>链接下载</span>
    </button>
  </div>
  <span class="game-status" title="游戏未运行"><i class="dot"></i></span>
  <button class="launch-button" type="button" data-toast="正在启动 Left 4 Dead 2">
    <svg class="i" aria-hidden="true"><use href="#i-play"></use></svg>启动
  </button>
  <div class="window-controls" aria-label="窗口控制">
    <button class="caption-button" type="button" title="最小化" aria-label="最小化" data-toast="窗口最小化">
      <svg class="caption-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16"></path></svg>
    </button>
    <button class="caption-button" type="button" title="最大化" aria-label="最大化" data-toast="窗口最大化">
      <svg class="caption-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="4.5" y="4.5" width="15" height="15" rx="0.8"></rect></svg>
    </button>
    <button class="caption-button close" type="button" title="关闭" aria-label="关闭" data-toast="关闭窗口">
      <svg class="caption-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5l14 14M19 5 5 19"></path></svg>
    </button>
  </div>
</header>
'''

RAIL = r'''
<nav class="rail" aria-label="主导航">
  <div class="rail-nav">
    <button class="rail-button" data-nav data-rail="all" type="button"><svg class="i" aria-hidden="true"><use href="#i-grid"></use></svg><span>全部</span></button>
    <button class="rail-button active" data-nav data-rail="survivor" aria-current="page" type="button"><svg class="i" aria-hidden="true"><use href="#i-users"></use></svg><span>角色</span></button>
    <button class="rail-button" data-nav data-rail="special" type="button"><svg class="i" aria-hidden="true"><use href="#i-infected"></use></svg><span>特感</span></button>
    <button class="rail-button" data-nav data-rail="weapon" type="button"><svg class="i" aria-hidden="true"><use href="#i-crosshair"></use></svg><span>武器</span></button>
    <button class="rail-button" data-nav data-rail="map" type="button"><svg class="i" aria-hidden="true"><use href="#i-map"></use></svg><span>地图</span></button>
    <button class="rail-button" data-nav data-rail="other" type="button"><svg class="i" aria-hidden="true"><use href="#i-box"></use></svg><span>其他</span></button>
  </div>
  <div class="rail-spacer"></div>
  <button class="rail-utility" type="button"><svg class="i" aria-hidden="true"><use href="#i-shield"></use></svg><span>整理</span></button>
  <button class="rail-button rail-settings" type="button" data-toast="打开设置"><svg class="i" aria-hidden="true"><use href="#i-settings"></use></svg><span>设置</span></button>
</nav>
'''

MAIN_HEAD = r'''
      <div class="main-head">
        <div class="crumb is-static">模组库 <svg class="i" aria-hidden="true"><use href="#i-chevron-right"></use></svg> <strong>角色</strong></div>
        <h1 class="page-title">ELLIS <span>艾利斯</span></h1>
      </div>
'''

INSPECTOR = r'''
    <aside class="inspector" aria-label="模组详情">
      <div class="inspector-head">
        <div class="title-block">
          <h2 class="detail-title" data-detail-title>夏日甜点屋</h2>
          <p class="detail-subtitle" data-detail-subtitle>VRC プラム Plum replace ellis</p>
        </div>
        <button class="close" type="button" aria-label="关闭详情" data-toast="收起详情"><svg class="i" aria-hidden="true"><use href="#i-x"></use></svg></button>
      </div>

      <div class="preview">
        <img data-detail-img src="assets/mods/mod3.webp" alt="已选模组预览">
      </div>

      <div class="status-card">
        <div class="status-left">
          <i class="dot"></i>
          <span data-detail-state>已启用</span>
        </div>
        <button type="button" class="switch on" role="switch" aria-checked="true" aria-label="启用或停用当前模组" data-switch data-toast-on="已启用" data-toast-off="已停用"><span class="switch-knob"></span></button>
      </div>

      <div class="spec-list">
        <div class="spec-row"><span class="k">文件</span><span class="v" data-detail-file>3659210344.vpk</span></div>
        <div class="spec-row"><span class="k">分类</span><span class="v" data-detail-meta>角色 / Ellis</span></div>
        <div class="spec-row"><span class="k">大小</span><span class="v" data-detail-size>34.1 MB</span></div>
        <div class="spec-row"><span class="k">入库时间</span><span class="v">2026-11-07</span></div>
        <div class="spec-row"><span class="k">来源</span><span class="v">本地导入</span></div>
        <div class="spec-row"><span class="k">工坊</span><span class="v">3659210344</span></div>
      </div>

      <div class="group-panel">
        <div class="group-head"><span>同组</span><span class="group-count">1 / 6</span></div>
        <div class="group-mini active"><img src="assets/mods/mod3.webp" alt=""><span>VRC Plum</span><svg class="i" aria-hidden="true"><use href="#i-check"></use></svg></div>
        <div class="group-mini"><img src="assets/mods/mod1.webp" alt=""><span>Koharu</span></div>
        <div class="group-mini"><img src="assets/mods/mod2.webp" alt=""><span>VRC lime</span></div>
      </div>

      <div class="inspector-actions">
        <button class="icon-action" type="button" title="设置别名" aria-label="设置别名" data-alias data-toast="别名已保存"><svg class="i" aria-hidden="true"><use href="#i-tag"></use></svg></button>
        <button class="icon-action" type="button" title="打开文件夹" aria-label="打开文件夹" data-toast="已在资源管理器中显示"><svg class="i" aria-hidden="true"><use href="#i-folder"></use></svg></button>
        <button class="icon-action" type="button" title="打开工坊页" aria-label="打开工坊页" data-toast="打开 Steam 创意工坊页面"><svg class="i" aria-hidden="true"><use href="#i-external"></use></svg></button>
        <div class="more-wrap">
          <button class="icon-action" type="button" title="更多操作" aria-label="更多操作" aria-expanded="false" data-more><svg class="i" aria-hidden="true"><use href="#i-more"></use></svg></button>
          <div class="more-menu" hidden>
            <button type="button" data-toast="修改分类">修改分类</button>
            <button type="button" data-toast="归入合集" data-map-only>归入合集</button>
          </div>
        </div>
        <span class="actions-spacer"></span>
        <button class="icon-action danger" type="button" title="移入回收站" aria-label="移入回收站" data-toast="删除前会移动到回收站"><svg class="i" aria-hidden="true"><use href="#i-trash"></use></svg></button>
      </div>
    </aside>
'''

IMPORT_VIEW = r'''
      <section class="view view-task" data-view="import" hidden>
        <div class="view-body scroll-y">
          <button class="drop-zone" type="button" data-toast="选择 ZIP / 7z / RAR 压缩包">
            <span class="drop-icon"><svg class="i" aria-hidden="true"><use href="#i-plus"></use></svg></span>
            <span class="drop-title">选择压缩包</span>
            <span class="drop-hint">ZIP / 7z / RAR</span>
          </button>

          <div class="task-panel">
            <div class="task-head">
              <span>可加入的模组</span>
              <span class="task-actions-inline">
                <button type="button" data-toast="已全选">全选</button>
                <button type="button" data-toast="已清空">清空</button>
              </span>
            </div>
            <div class="task-list">
              <label class="task-row is-checked">
                <input type="checkbox" checked>
                <img src="assets/mods/mod2.webp" alt="">
                <span class="task-copy"><b>VRC lime 甜点屋 打歌服</b><small>角色 / Ellis · 93.0 MB</small></span>
              </label>
              <label class="task-row is-checked">
                <input type="checkbox" checked>
                <img src="assets/mods/mod5.webp" alt="">
                <span class="task-copy"><b>【原神】菲谢尔 极夜真梦</b><small>角色 / Ellis · 38.3 MB</small></span>
              </label>
              <label class="task-row is-dup">
                <input type="checkbox" disabled>
                <img src="assets/mods/mod3.webp" alt="">
                <span class="task-copy"><b>VRC プラム Plum replace ellis</b><small>角色 / Ellis · 34.1 MB</small></span>
                <span class="task-tag">已在库</span>
              </label>
            </div>
          </div>

          <div class="task-actions">
            <button class="button primary" type="button" data-toast="加入模组库">加入模组库（2）</button>
          </div>
        </div>
      </section>
'''

DOWNLOAD_VIEW = r'''
      <section class="view view-task" data-view="download" hidden>
        <div class="view-body scroll-y">
          <div class="link-row">
            <svg class="i" aria-hidden="true"><use href="#i-link"></use></svg>
            <input placeholder="创意工坊链接或物品 ID" aria-label="创意工坊链接">
            <button class="button" type="button" data-toast="正在解析链接">解析</button>
          </div>

          <div class="task-panel">
            <div class="task-head"><span>已解析</span></div>
            <div class="task-list">
              <label class="task-row is-checked">
                <input type="checkbox" checked>
                <img src="assets/mods/mod4.webp" alt="">
                <span class="task-copy"><b>[Gakuen IDOLM@STER] Fujita</b><small>角色 / Ellis · 146.4 MB</small></span>
              </label>
              <label class="task-row is-checked">
                <input type="checkbox" checked>
                <img src="assets/mods/mod6.webp" alt="">
                <span class="task-copy"><b>雨衣替换 Ellis</b><small>角色 / Ellis · 246.6 MB</small></span>
              </label>
            </div>
          </div>

          <div class="task-actions">
            <button class="button primary" type="button" data-toast="开始下载">开始下载（2）</button>
          </div>

          <div class="progress-panel">
            <div class="progress-head">
              <span>正在下载 · Fujita</span>
              <span>72%</span>
            </div>
            <div class="progress-bar"><i style="width:72%"></i></div>
          </div>
        </div>
      </section>
'''

VIEW_JS = r'''
<script>
(() => {
  const tabs = Array.from(document.querySelectorAll('[data-ws]'));
  const views = Array.from(document.querySelectorAll('[data-view]'));
  const crumb = document.querySelector('.crumb');
  const h1 = document.querySelector('.page-title');
  const SEP = '<svg class="i" aria-hidden="true"><use href="#i-chevron-right"></use></svg>';
  const PANE_TITLE = { all: '全部', survivor: '角色', special: '特感', weapon: '武器', map: '地图', other: '其他' };

  const railOf = () => document.querySelector('[data-rail].active');
  const railName = () => (PANE_TITLE[railOf() && railOf().dataset.rail] || '全部');
  const itemRow = () => document.querySelector('.filter-pane:not([hidden]) .filter-row.active');
  const itemName = () => (itemRow() ? itemRow().querySelector('.item-name').textContent.trim() : '');
  const mode = () => (tabs.find((t) => t.classList.contains('active') || {}).dataset || {}).ws || 'library';

  function setTitle(text) {
    const m = String(text).match(/^([^（(]+)[（(](.+)[）)]$/);
    h1.innerHTML = m ? m[1].trim() + ' <span>' + m[2].trim() + '</span>' : text;
  }

  // Aggregate rows ("全部角色") describe the category, not a specific item.
  function selection() {
    const item = itemName();
    if (!item || item.startsWith('全部')) return { title: railName(), item: '' };
    return { title: item, item: item };
  }

  function renderCrumb(view) {
    if (view === 'import') { crumb.innerHTML = '模组库 ' + SEP + ' 导入压缩包'; return; }
    if (view === 'download') { crumb.innerHTML = '模组库 ' + SEP + ' 链接下载'; return; }
    const sel = selection();
    crumb.innerHTML = '模组库 ' + SEP + ' ' + railName() +
      (sel.item ? ' ' + SEP + ' <strong>' + sel.item + '</strong>' : '');
  }

  function setView(view) {
    tabs.forEach((t) => {
      const on = t.dataset.ws === view;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', String(on));
    });
    views.forEach((v) => { v.hidden = v.dataset.view !== view; });
    renderCrumb(view);

    const isTask = view === 'import' || view === 'download';
    h1.hidden = isTask;
    if (!isTask) setTitle(selection().title);
  }

  tabs.forEach((t) => t.addEventListener('click', () => setView(t.dataset.ws)));

  document.addEventListener('click', (event) => {
    const row = event.target.closest('.filter-row');
    if (row && mode() === 'library') {
      Array.from(row.parentElement.querySelectorAll('.filter-row')).forEach((r) => {
        r.classList.toggle('active', r === row);
        if (r === row) r.setAttribute('aria-current', 'page');
        else r.removeAttribute('aria-current');
      });
      setTitle(selection().title);
      renderCrumb('library');
    }

    const aliasBtn = event.target.closest('[data-alias]');
    if (aliasBtn) {
      const title = document.querySelector('[data-detail-title]');
      const sub = document.querySelector('[data-detail-subtitle]');
      const next = window.prompt('别名（留空恢复原名）', title.dataset.custom ? title.textContent : '');
      if (next !== null) {
        const original = sub.textContent;
        const value = next.trim();
        if (value) {
          title.textContent = value;
          title.dataset.custom = '1';
          sub.textContent = original;
          sub.hidden = false;
        } else {
          title.textContent = original;
          delete title.dataset.custom;
          sub.hidden = true;
        }
      }
      return;
    }

    const moreBtn = event.target.closest('[data-more]');
    if (moreBtn) {
      const menu = moreBtn.parentElement.querySelector('.more-menu');
      const open = menu.hidden;
      menu.hidden = !open;
      moreBtn.setAttribute('aria-expanded', String(open));
      return;
    }
    document.querySelectorAll('.more-menu').forEach((m) => {
      if (!m.contains(event.target)) m.hidden = true;
    });
    document.querySelectorAll('[data-more]').forEach((b) => b.setAttribute('aria-expanded', 'false'));
  });

  // "归入合集" only applies to map mods.
  function syncMapOnly() {
    const isMap = (document.querySelector('[data-detail-meta]') || {}).textContent?.trim().startsWith('地图');
    document.querySelectorAll('[data-map-only]').forEach((el) => { el.hidden = !isMap; });
  }
  syncMapOnly();

  // StatusBar demo: the rail "整理" button shows the scanning state for a few seconds.
  const idle = document.querySelector('.status-idle');
  const activity = document.querySelector('[data-activity]');
  const activityBar = document.querySelector('.activity-bar i');
  const activityLabel = document.querySelector('.activity-label');

  document.querySelectorAll('.rail-utility').forEach((btn) => btn.addEventListener('click', () => {
    if (activity.hidden) {
      idle.hidden = true;
      activity.hidden = false;
      let pct = 6;
      activityBar.style.width = pct + '%';
      activityLabel.textContent = '扫描中 0/128';
      const timer = setInterval(() => {
        pct = Math.min(100, pct + 7);
        activityBar.style.width = pct + '%';
        activityLabel.textContent = '扫描中 ' + Math.round(pct * 1.28) + '/128';
        if (pct >= 100) {
          clearInterval(timer);
          setTimeout(() => {
            activity.hidden = true;
            idle.hidden = false;
          }, 700);
        }
      }, 220);
    }
  }));

  document.querySelectorAll('[data-rail]').forEach((btn) => btn.addEventListener('click', () => {
    if (mode() !== 'library') setView('library');
    setTitle(selection().title);
    renderCrumb('library');
  }));
})();
</script>
'''


def item_row(name, count, active=False, has_enabled=False, indent=False):
    cls = "filter-row item-row"
    if indent:
        cls += " is-nested"
    if active:
        cls += " active"
    dot = '<span class="active-mark"></span>' if has_enabled else ""
    return (f'<button class="{cls}" type="button">'
            f'<span class="item-name">{name}</span>'
            f'<span class="count">{count}</span>{dot}</button>')


def group_row(key, name, count, expanded=True):
    cls = "tree-head" + ("" if expanded else " is-collapsed")
    return (f'<button class="{cls}" type="button" data-fold="{key}" '
            f'aria-expanded="{"true" if expanded else "false"}">'
            f'<svg class="fold-caret" aria-hidden="true"><use href="#i-chevron-down"></use></svg>'
            f'<span>{name}</span><span class="count">{count}</span></button>')


def pane(key, title, total, enabled, disabled, body, hidden=False):
    attrs = " hidden" if hidden else ""
    return f'''
<div class="filter-pane" data-pane="{key}"{attrs}>
  <div class="filter-head"><h2>{title}</h2><span class="total">{total}</span></div>
  <div class="segmented" data-nav-group>
    <button class="active" type="button" data-nav>全部</button>
    <button type="button" data-nav>启用 <span>{enabled}</span></button>
    <button type="button" data-nav>停用 <span>{disabled}</span></button>
  </div>
  {body}
</div>'''


def build_filters():
    # 全部: no category repetition — a cross-category item list is the honest next layer.
    all_items = [
        ("全部物品", 128, True, False),
        ("Ellis（艾利斯）", 6, False, True),
        ("AK-47（AK）", 6, False, True),
        ("Nick（尼克）", 5, False, False),
        ("消防斧", 4, False, True),
        ("死亡中心 · 重制版", 3, False, True),
        ("Coach（教练）", 4, False, False),
        ("📁 寂静岭 · 雾中街区", 4, False, False),
    ]
    all_body = (
        '<div class="filter-list" data-nav-group>'
        + "".join(item_row(n, c, a, e) for n, c, a, e in all_items)
        + "</div>"
        + '''
  <div class="conflict-line">
    <svg class="i" aria-hidden="true"><use href="#i-alert"></use></svg>
    <span><b>1</b> 组待处理</span>
    <button type="button" data-toast="查看冲突组">查看</button>
  </div>'''
    )

    survivors = [
        ("全部角色", 42, False, False),
        ("Ellis（艾利斯）", 6, True, True),
        ("Nick（尼克）", 5, False, False),
        ("Coach（教练）", 4, False, False),
        ("Bill（比尔）", 3, False, False),
        ("Zoey（佐伊）", 3, False, False),
        ("Louis（路易斯）", 3, False, False),
        ("Francis（弗朗西斯）", 3, False, False),
        ("Rochelle（罗谢尔）", 2, False, False),
        ("未指定物品", 13, False, False),
    ]
    survivor_body = (
        '<div class="filter-list" data-nav-group>'
        + "".join(item_row(n, c, a, e) for n, c, a, e in survivors)
        + "</div>"
        + '''
  <div class="conflict-line">
    <svg class="i" aria-hidden="true"><use href="#i-alert"></use></svg>
    <span><b>1</b> 组待处理</span>
    <button type="button" data-toast="查看冲突组">查看</button>
  </div>'''
    )

    specials = [
        ("全部特感", 16, False, False),
        ("Hunter", 2, False, False),
        ("Smoker", 2, False, False),
        ("Boomer", 2, False, False),
        ("Charger", 2, False, False),
        ("Spitter", 2, False, False),
        ("Jockey", 2, False, False),
        ("Tank", 2, False, False),
        ("Witch", 1, False, False),
        ("普通感染者", 1, False, False),
    ]
    special_body = ('<div class="filter-list" data-nav-group>'
                    + "".join(item_row(n, c, a, e) for n, c, a, e in specials) + "</div>")

    weapon_groups = [
        ("firearms", "枪械", 36, True, [
            ("全部枪械", 36, False, False),
            ("AK-47（AK）", 6, True, True),
            ("M16A2（M4）", 5, False, True),
            ("AWP（大狙）", 4, False, False),
            ("SPAS-12（二代连喷）", 3, False, False),
            ("M60（机枪）", 2, False, False),
            ("其他枪械", 16, False, False),
        ]),
        ("melee", "近战", 17, False, [
            ("全部近战", 17, False, False),
            ("消防斧", 4, False, True),
            ("武士刀", 3, False, False),
            ("平底锅", 2, False, False),
            ("其他近战", 8, False, False),
        ]),
        ("med", "医疗品", 8, False, [
            ("全部医疗品", 8, False, False),
            ("急救包", 4, False, True),
            ("除颤器", 2, False, False),
            ("其他医疗品", 2, False, False),
        ]),
        ("throw", "投掷", 6, False, [
            ("全部投掷", 6, False, False),
            ("燃烧瓶", 3, False, True),
            ("土制炸弹", 2, False, False),
            ("胆汁罐", 1, False, False),
        ]),
    ]
    weapon_parts = []
    for key, name, count, expanded, items in weapon_groups:
        weapon_parts.append(group_row(key, name, count, expanded))
        rows = "".join(item_row(n, c, a, e, indent=True) for n, c, a, e in items)
        weapon_parts.append(f'<div class="tree-items"{"" if expanded else " hidden"} data-items="{key}">{rows}</div>')
    weapon_body = ('<div class="filter-list is-tree" data-nav-group>'
                   + "".join(weapon_parts) + "</div>")

    maps = [
        ("全部地图", 18, False, False),
        ("📁 死亡中心 · 重制版", 3, True, True),
        ("📁 寂静岭 · 雾中街区", 4, False, False),
        ("黑色狂欢节", 1, False, False),
        ("沼泽激战", 1, False, False),
        ("暴风骤雨", 1, False, False),
        ("短暂时刻", 1, False, False),
        ("教区", 1, False, False),
        ("自定义战役", 5, False, False),
    ]
    map_body = ('<div class="filter-list" data-nav-group>'
                + "".join(item_row(n, c, a, e) for n, c, a, e in maps) + "</div>")

    other_groups = [
        ("ui", "UI", 5), ("audio", "音效音乐", 6), ("vehicle", "载具", 4),
        ("ammo", "弹药", 3), ("material", "材质特效", 5), ("action", "动作", 4),
        ("misc", "杂项", 3), ("unknown", "未分类", 2),
    ]
    other_parts = []
    for key, name, count in other_groups:
        other_parts.append(group_row(key, name, count, False))
        rows = item_row(f"全部{name}", count, False, False, indent=True)
        other_parts.append(f'<div class="tree-items" data-items="{key}" hidden>{rows}</div>')
    other_body = ('<div class="filter-list is-tree" data-nav-group>'
                  + "".join(other_parts) + "</div>")

    # 「全部」= 每个分类各成一组，默认全部展开
    all_tree = []
    for key, name, items in [
        ("s", "角色", survivors[1:]), ("sp", "特感", specials[1:]),
        ("w", "枪械", weapon_groups[0][4]), ("me", "近战", weapon_groups[1][4]),
        ("md", "医疗品", weapon_groups[2][4]), ("th", "投掷", weapon_groups[3][4]),
        ("mp", "地图", maps[1:]),
    ]:
        all_tree.append(group_row(key, name, sum(c for _n, c, _a, _e in items), True))
        rows = "".join(item_row(n, c, a, e, indent=True) for n, c, a, e in items)
        all_tree.append(f'<div class="tree-items" data-items="{key}">{rows}</div>')
    all_body = ('<div class="filter-list is-tree" data-nav-group>'
                + "".join(all_tree) + "</div>")

    panes = "".join([
        pane("all", "全部", "128", 43, 85, all_body, hidden=True),
        pane("survivor", "角色", "42", 18, 24, survivor_body),
        pane("special", "特感", "16", 5, 11, special_body, hidden=True),
        pane("weapon", "武器", "67", 21, 46, weapon_body, hidden=True),
        pane("map", "地图", "18", 6, 12, map_body, hidden=True),
        pane("other", "其他", "32", 8, 24, other_body, hidden=True),
    ])
    return f'<aside class="filters" aria-label="筛选">{panes}</aside>'


FILTER_JS = r'''
<script>
(() => {
  const railButtons = Array.from(document.querySelectorAll('[data-rail]'));
  const panes = Array.from(document.querySelectorAll('[data-pane]'));

  railButtons.forEach((btn) => btn.addEventListener('click', () => {
    const key = btn.dataset.rail;
    railButtons.forEach((b) => {
      const on = b === btn;
      b.classList.toggle('active', on);
      if (on) b.setAttribute('aria-current', 'page');
      else b.removeAttribute('aria-current');
    });
    panes.forEach((p) => { p.hidden = p.dataset.pane !== key; });
  }));

  document.addEventListener('click', (event) => {
    const head = event.target.closest('[data-fold]');
    if (!head) return;
    const items = document.querySelector('.tree-items[data-items="' + head.dataset.fold + '"]');
    if (!items) return;
    const open = !items.hidden;
    items.hidden = open;
    head.setAttribute('aria-expanded', String(!open));
    head.classList.toggle('is-collapsed', open);
  });
})();
</script>
'''


def main():
    html = SOURCE.read_text(encoding="utf-8")
    html = html.replace("<head>", '<head>\n<base href="../">', 1)
    html = html.replace('body class="v1"', 'body class="v1 final-preview"', 1)
    html = html.replace("</style>", '</style>\n<link rel="stylesheet" href="final/tokens.css">\n<link rel="stylesheet" href="final/preview.css">', 1)
    html = html.replace('</svg>\n\n\n<div class="app">', EXTRA_SYMBOLS + '</svg>\n\n\n<div class="app">', 1)

    for pattern, repl, label in [
        (r'<header class="topbar">.*?</header>', TOP_BAR, "topbar"),
        (r'<nav class="rail"[^>]*>.*?</nav>', RAIL, "rail"),
        (r'<aside class="filters"[^>]*>.*?</aside>', build_filters(), "filters"),
        (r'<aside class="inspector"[^>]*>.*?</aside>', INSPECTOR, "inspector"),
    ]:
        html, count = re.subn(pattern, repl.replace('\\', '\\\\'), html, count=1, flags=re.S)
        if count != 1:
            raise SystemExit(f"{label} replacement failed")

    # status chips are gone from the action bar (gate 03)
    html, count = re.subn(r'\s*<button class="chip[^"]*" type="button" data-chip>.*?</button>', "", html)
    if count < 3:
        raise SystemExit("action bar chip removal failed")

    # rebuild main column: header + library view + task views
    m = re.search(r'<main class="main">(.*)</main>', html, flags=re.S)
    if not m:
        raise SystemExit("main region not found")
    inner = m.group(1)
    library = inner[inner.index('<div class="toolbar">'):]
    new_inner = (MAIN_HEAD
                 + '\n      <section class="view" data-view="library">\n'
                 + library
                 + '\n      </section>\n'
                 + IMPORT_VIEW
                 + DOWNLOAD_VIEW
                 + '\n    ')
    html = html[:m.start()] + '<main class="main">' + new_inner + '</main>' + html[m.end():]

    html = re.sub(r'\s*<div class="mod-sub">[^<]*<span>/</span>[^<]*</div>', "", html)
    # Only the enabled state earns a badge; absence means "not enabled".
    html = re.sub(r'\s*<span class="mod-state ">未启用</span>', "", html)
    # 启用态：只给含「已启用」角标的卡片加 is-on 类（绿卡白字）
    def mark_enabled(match):
        block = match.group(0)
        if 'mod-state on' in block:
            block = block.replace('<article class="mod-card', '<article class="mod-card is-on', 1)
        return block
    html = re.sub(r'<article class="mod-card[^>]*>.*?</article>', mark_enabled, html, flags=re.S)
    html = re.sub(r'\s*<div class="library-summary">.*?</div>\s*</div>\s*<div class="grid-hint">',
                  '\n        <div class="grid-hint">', html, count=1, flags=re.S)
    html = re.sub(r'\s*<div class="grid-hint">.*?</div>', "", html, count=1, flags=re.S)

    path_text = "&bsol;".join(["E:", "SteamLibrary", "steamapps", "common", "Left 4 Dead 2", "left4dead2", "addons"])
    statusbar = (
        '<footer class="statusbar">\n'
        '    <span class="status-idle"><span class="dot"></span>就绪</span>\n'
        '    <span class="status-activity" data-activity hidden>\n'
        '      <span class="dot"></span>\n'
        '      <span class="activity-label">扫描中 3/128</span>\n'
        '      <span class="activity-bar"><i style="width:38%"></i></span>\n'
        '    </span>\n'
        '    <span class="spacer"></span>\n'
        '    <button class="status-path" type="button" title="打开 addons 目录" data-toast="已在资源管理器中打开">'
        + path_text + '</button>\n'
        '    <span class="status-version">v1.2.1</span>\n'
        '  </footer>'
    )
    html, count = re.subn(r'<footer class="statusbar">.*?</footer>', lambda _m: statusbar, html, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("statusbar replacement failed")
    html = html.replace("&bsol;", chr(92))

    html = html.replace("</body>", FILTER_JS + VIEW_JS + "\n</body>", 1)

    OUT.write_text(html, encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
