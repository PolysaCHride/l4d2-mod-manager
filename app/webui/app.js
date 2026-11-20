/* BLACKSITE demo — 交互与数据。
   静态资源来自 ../assets/mods/，逻辑尽量贴近 app/ 的真实行为：
   - 同组互斥：启用一项会停用同物品其它项
   - 游戏运行时禁止写入
   - 导入 / 下载都是「解析 → 勾选 → 执行 → 结果」四段
   所有文案与按钮语义以 states.html 与 03/04 拆解文档为准。 */

(() => {
  'use strict';

  // 全局错误上报：打包后没有控制台，靠桥接层写文件
  window.addEventListener('error', (e) => {
    const msg = 'JS ERROR: ' + e.message + ' @ ' + (e.filename || '?') + ':' + e.lineno;
    if (window.bridge && window.bridge.log) window.bridge.log(msg);
    else console.error(msg);
  });
  window.addEventListener('unhandledrejection', (e) => {
    const msg = 'JS REJECT: ' + (e.reason && e.reason.message ? e.reason.message : e.reason);
    if (window.bridge && window.bridge.log) window.bridge.log(msg);
  });

  // ---------------------------------------------------------------- data
  const DEMO_MODS = [
    { id: 'm1', name: 'Koharu [Replace Ellis]', alias: '', cat: '角色', item: 'Ellis', size: 116.1, img: 'mod1.webp', enabled: false, added: 2, file: '3668116708.vpk', ws: '' },
    { id: 'm2', name: 'VRC lime 甜点屋 打歌服', alias: '', cat: '角色', item: 'Ellis', size: 93.0, img: 'mod2.webp', enabled: false, added: 4, file: '3664792140.vpk', ws: '3664792140' },
    { id: 'm3', name: 'VRC プラム Plum replace ellis', alias: '夏日甜点屋', cat: '角色', item: 'Ellis', size: 34.1, img: 'mod3.webp', enabled: true, added: 7, file: '3659210344.vpk', ws: '3659210344' },
    { id: 'm4', name: '[Gakuen IDOLM@STER] Fujita', alias: '', cat: '角色', item: 'Ellis', size: 146.4, img: 'mod4.webp', enabled: false, added: 9, file: '3671024551.vpk', ws: '3671024551' },
    { id: 'm5', name: '【原神】菲谢尔 极夜真梦', alias: '', cat: '角色', item: 'Ellis', size: 38.3, img: 'mod5.webp', enabled: false, added: 12, file: '3648830117.vpk', ws: '3648830117' },
    { id: 'm6', name: '雨衣替换 Ellis', alias: '', cat: '角色', item: 'Ellis', size: 246.6, img: 'mod6.webp', enabled: false, added: 18, file: '3639905428.vpk', ws: '3639905428' },

    { id: 'm7', name: 'Nick | 警长制服', alias: '', cat: '角色', item: 'Nick', size: 82.4, img: 'mod4.webp', enabled: true, added: 5, file: '3678823160.vpk', ws: '' },
    { id: 'm8', name: 'Coach | 军装', alias: '', cat: '角色', item: 'Coach', size: 64.2, img: 'mod1.webp', enabled: false, added: 15, file: '3674102118.vpk', ws: '' },

    { id: 'm9', name: 'Hunter | 血污皮肤', alias: '', cat: '特感', item: 'Hunter', size: 21.6, img: 'mod2.webp', enabled: true, added: 6, file: '3669120441.vpk', ws: '' },
    { id: 'm10', name: 'Tank | 熔岩体表', alias: '', cat: '特感', item: 'Tank', size: 44.9, img: 'mod5.webp', enabled: false, added: 21, file: '3650123788.vpk', ws: '' },

    { id: 'm11', name: 'AK-47 | 霓虹风暴', alias: '', cat: '枪械', item: 'AK-47', size: 56.8, img: 'mod2.webp', enabled: true, added: 1, file: '3680021947.vpk', ws: '' },
    { id: 'm12', name: 'AK-47 | 废土涂装', alias: '', cat: '枪械', item: 'AK-47', size: 48.3, img: 'mod4.webp', enabled: false, added: 11, file: '3671200336.vpk', ws: '' },
    { id: 'm13', name: 'M16A2 | 数码迷彩', alias: '', cat: '枪械', item: 'M16A2', size: 40.1, img: 'mod6.webp', enabled: true, added: 8, file: '3670120914.vpk', ws: '' },
    { id: 'm14', name: '消防斧 | 生锈', alias: '', cat: '近战', item: '消防斧', size: 18.7, img: 'mod1.webp', enabled: false, added: 13, file: '3664007712.vpk', ws: '' },
    { id: 'm15', name: '大剑 · 冷冽', alias: '', cat: '近战', item: '大剑', size: 27.4, img: 'mod3.webp', enabled: true, added: 16, file: '3658001120.vpk', ws: '' },
    { id: 'm16', name: '急救包 | 医疗箱', alias: '', cat: '医疗品', item: '急救包', size: 9.2, img: 'mod5.webp', enabled: false, added: 22, file: '3650110088.vpk', ws: '' },
    { id: 'm17', name: '燃烧瓶 | 荧光', alias: '', cat: '投掷', item: '燃烧瓶', size: 6.4, img: 'mod2.webp', enabled: true, added: 19, file: '3649002244.vpk', ws: '' },

    { id: 'm18', name: '死亡中心 · 重制版', alias: '', cat: '地图', item: '死亡中心', size: 1228.8, img: 'mod6.webp', enabled: true, added: 3, file: '3674110256.vpk', ws: '3674110256', collection: 'c1' },
    { id: 'm19', name: '寂静岭 · 雾中街区', alias: '', cat: '地图', item: '自定义', size: 3481.6, img: 'mod5.webp', enabled: false, added: 10, file: '3661004421.vpk', ws: '', collection: 'c2' },
    { id: 'm20', name: '黑色狂欢节', alias: '', cat: '地图', item: '黑色狂欢节', size: 812.0, img: 'mod4.webp', enabled: false, added: 24, file: '3643004412.vpk', ws: '' },

    { id: 'm21', name: 'HUD | 极简', alias: '', cat: 'UI', item: '', size: 12.1, img: 'mod1.webp', enabled: true, added: 14, file: '3662008811.vpk', ws: '' },
    { id: 'm22', name: '武器音效重制', alias: '', cat: '音效音乐', item: '', size: 96.4, img: 'mod3.webp', enabled: false, added: 17, file: '3657001133.vpk', ws: '' },
  ]

  // 真实数据由 bootstrap 填充；DEMO_MODS 只在浏览器 mock 时兜底。
  let MODS = [];

  // FilterPanel 结构与拆解文档一致：分组 → 物品
  // 一级分类 → 归属的二级分类。
  // 结构固定，但**具体物品从真实数据里读**，不再写死。
  const RAIL_DEFS = [
    { key: 'all',      title: '全部', cats: null },
    { key: 'survivor', title: '角色', cats: ['角色'] },
    { key: 'special',  title: '特感', cats: ['特感'] },
    { key: 'weapon',   title: '武器', cats: ['枪械', '近战', '医疗品', '投掷'],
      grouped: true },
    { key: 'map',      title: '地图', cats: ['地图'] },
    { key: 'other',    title: '其他',
      cats: ['UI', '音效音乐', '载具', '弹药', '材质特效', '动作', '杂物', '杂项', '其他', '未分类'],
      grouped: true },
  ];

  /** 一级分类是产品固定分组；二级物品才从数据推导。 */
  const RAILS = (() => {
    const out = {};
    RAIL_DEFS.forEach((def) => {
      out[def.key] = {
        title: def.title,
        cats: def.cats,
        grouped: !!def.grouped,
      };
    });
    return out;
  })();

  /** 取某个二级分类下的物品名（按数量降序，带「全部X」置顶）。 */
  function itemsOfCategory(catName, pool) {
    const names = [];
    pool.forEach((m) => {
      if (m.cat !== catName) return;
      const item = m.item || '';
      if (item && names.indexOf(item) < 0) names.push(item);
    });
    return ['全部' + catName].concat(names);
  }


  // 互斥类别：与 app/core/classify.py 的 CONFLICT_CATEGORIES 保持一致。
  // 只有这些类别下的同 item 模组才互斥，地图/脚本等不受限制。
  const MUTEX_CATEGORIES = new Set(['角色', '特感', '枪械', '近战', '医疗品', '投掷']);

  // ---------------------------------------------------------------- state
  const state = {
    view: 'library',
    rail: 'survivor',
    filterMode: 'all',        // all | on | off
    filterItem: null,         // 'Ellis' 等；null = 全部
    layout: 'grid',
    sort: 'added',
    query: '',
    selectedId: null,
    gameRunning: false,
    scanning: false,
    openGroups: new Set(),   // 树状分组展开状态，由用户点击决定
    toastTimer: null,
    settings: {},
    version: '1.2.1',
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const icon = (name, cls = 'i') => `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtSize = (mb) => (mb >= 1024 ? (mb / 1024).toFixed(1) + ' GB' : mb.toFixed(1) + ' MB');
  const fmtAgo = (days) => (days <= 1 ? '今天' : days < 7 ? days + ' 天前' : Math.floor(days / 7) + ' 周前');

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      $('#search').focus();
      $('#search').select();
    }
  });

  // ---------------------------------------------------------------- toast
  function toast(message) {
    const el = $('#toast');
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => el.classList.remove('show'), 2000);
  }

  // ---------------------------------------------------------------- modal
  function openModal(html, { onClose } = {}) {
    const root = $('#modal-root');
    $('#modal-host').innerHTML = html;
    root.classList.add('open');
    const first = $('#modal-host').querySelector('.dlg-foot button.primary, .dlg-foot button');
    if (first) first.focus();
    root.dataset.onClose = onClose ? '1' : '';
    root._onClose = onClose || null;
  }

  function closeModal(confirmed) {
    const root = $('#modal-root');
    if (!root.classList.contains('open')) return;
    root.classList.remove('open');
    $('#modal-host').innerHTML = '';
    const cb = root._onClose;
    root._onClose = null;
    if (cb) cb(confirmed);
  }

  function dialog({ title, tone = 'info', text = '', rows = [], check = '', buttons = [], progress = null, width = 520 }) {
    const rowsHtml = rows.length
      ? `<div class="dlg-rows">${rows.map((r) => `<div class="dlg-row"><span class="row-name">${esc(r.name)}</span><span class="row-tag ${r.tone || ''}">${esc(r.tag || '')}</span></div>`).join('')}</div>`
      : '';
    const checkHtml = check ? `<label class="dlg-check"><input type="checkbox" id="dlgCheck"><span>${esc(check)}</span></label>` : '';
    const progHtml = progress
      ? `<div class="dlg-progress"><i style="width:${progress.pct || 0}%"></i></div><div class="dlg-progress-meta">${esc(progress.meta || '')}</div>`
      : '';
    const btns = buttons.map((b, i) =>
      `<button class="btn ${b.kind || ''}" type="button" data-btn="${i}">${esc(b.label)}</button>`).join('');
    return `<div class="dlg ${tone}" style="max-width:${width}px">
      <div class="dlg-head"><span class="dot"></span><h4>${esc(title)}</h4>
        <button class="dlg-close" type="button" data-btn="close" aria-label="关闭">${icon('x')}</button></div>
      <div class="dlg-body">${text ? `<p class="dlg-text">${esc(text)}</p>` : ''}${rowsHtml}${checkHtml}${progHtml}</div>
      <div class="dlg-foot">${btns}</div>
    </div>`;
  }

  function confirmDialog({ title, tone, text, rows, check, confirm, cancel = '取消', danger, width }) {
    return new Promise((resolve) => {
      const buttons = [{ label: cancel, kind: 'ghost' }, { label: confirm, kind: danger ? 'danger' : 'primary' }];
      openModal(dialog({ title, tone, text, rows, check, buttons, width }), {
        onClose: (value) => resolve(!!value),
      });
      $$('#modal-host [data-btn]').forEach((b) => {
        b.addEventListener('click', () => closeModal(b.dataset.btn === '1'));
      });
    });
  }

  function infoDialog({ title, tone = 'info', text, rows, width }) {
    return new Promise((resolve) => {
      openModal(dialog({ title, tone, text, rows, buttons: [{ label: '知道了', kind: 'primary' }], width }), {
        onClose: () => resolve(true),
      });
      $$('#modal-host [data-btn]').forEach((b) => b.addEventListener('click', () => closeModal(true)));
    });
  }

  $('#modal-root').addEventListener('click', (e) => {
    // 点遮罩或弹窗外的留白都关闭
    const t = e.target;
    if (t.classList.contains('scrim') || t.classList.contains('modal-wrap')) {
      closeModal(false);
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && $('#modal-root').classList.contains('open')) closeModal(false);
  });

  // ---------------------------------------------------------------- selectors
  function modsInRail(rail) {
    if (rail === 'all') return MODS.slice();
    // 分类归属只在 RAIL_DEFS 定义一次，这里复用
    const def = RAILS[rail];
    const cats = (def && def.cats) || [];
    return MODS.filter((m) => cats.indexOf(m.cat) >= 0);
  }

  function visibleMods() {
    let list = modsInRail(state.rail);
    if (state.query) {
      const q = state.query.toLowerCase();
      list = list.filter((m) => (m.name + ' ' + m.alias + ' ' + m.file + ' ' + m.item).toLowerCase().includes(q));
    }
    if (state.filterItem) {
      const f = state.filterItem;
      if (f.startsWith('全部')) {
        const cat = f.slice(2);
        // 「全部X」：X 是二级分类名（枪械/近战…）或一级标题（角色/地图…）
        list = list.filter((m) => m.cat === cat);
      } else if (f === '未指定物品') {
        list = list.filter((m) => !m.item);
      } else {
        list = list.filter((m) => m.item === f);
      }
    }
    if (state.filterMode === 'on') list = list.filter((m) => m.enabled);
    if (state.filterMode === 'off') list = list.filter((m) => !m.enabled);
    const sorters = {
      added: (a, b) => b.added - a.added,   // 最新在前
      name: (a, b) => (a.alias || a.name).localeCompare(b.alias || b.name, 'zh'),
      size: (a, b) => b.size - a.size,
    };
    return list.slice().sort(sorters[state.sort] || sorters.added);
  }

  const selected = () => MODS.find((m) => m.id === state.selectedId) || null;
  const sameGroup = (m) => MODS.filter((x) => x.cat === m.cat && x.item === m.item && x.id !== m.id);

  // ---------------------------------------------------------------- render: rail
  function renderRail() {
    $$('[data-rail]').forEach((btn) => {
      const on = btn.dataset.rail === state.rail;
      btn.classList.toggle('active', on);
      if (on) btn.setAttribute('aria-current', 'page');
      else btn.removeAttribute('aria-current');
    });
  }

  // ---------------------------------------------------------------- render: filters
  function renderFilters() {
    const def = RAILS[state.rail];
    const all = modsInRail(state.rail);
    const on = all.filter((m) => m.enabled).length;

    const head = `<div class="filter-head"><h2>${def.title}</h2><span class="total">${all.length}</span></div>
      <div class="segmented" data-mode-group>
        <button data-mode="all" class="${state.filterMode === 'all' ? 'active' : ''}">全部</button>
        <button data-mode="on" class="${state.filterMode === 'on' ? 'active' : ''}">启用 <span>${on}</span></button>
        <button data-mode="off" class="${state.filterMode === 'off' ? 'active' : ''}">停用 <span>${all.length - on}</span></button>
      </div>`;

    // ---------------------------------------------------------- 分类树
    // 每个分组 = 一个二级分类（如「枪械」），组内是该分类下的具体物品。
    let groups = [];
    if (state.rail === 'all') {
      // 「全部」：每个二级分类各成一组，全部展开
      const seen = [];
      all.forEach((m) => { if (seen.indexOf(m.cat) < 0) seen.push(m.cat); });
      groups = seen.map((catName) => ({
        key: catName,
        items: itemsOfCategory(catName, all),
      }));
      groups.forEach((g) => state.openGroups.add(g.key));
    } else if (def.grouped) {
      // 武器 / 其他：按 cat 分组
      (def.cats || []).forEach((catName) => {
        const pool = all.filter((m) => m.cat === catName);
        if (pool.length) {
          groups.push({ key: catName, items: itemsOfCategory(catName, pool) });
        }
      });
    } else {
      // 角色 / 特感 / 地图：单层列表，物品直接摊平
      const items = ['全部' + def.title];
      all.forEach((m) => {
        const it = m.item || '';
        if (it && items.indexOf(it) < 0) items.push(it);
      });
      const unspecified = all.filter((m) => !m.item);
      if (unspecified.length) items.push('未指定物品');
      groups = [{ key: def.title, items, flat: true }];
    }

    let body = '';
    if (groups.length === 1 && groups[0].flat) {
      // 单层：不加树头
      body = '<div class="filter-list">' + renderItemRows(groups[0].items, all, false) + '</div>';
    } else {
      body = '<div class="filter-list is-tree">' + groups.map((g) => {
        const open = state.openGroups.has(g.key);
        const count = all.filter((m) => m.cat === g.key).length;
        return `<button class="tree-head ${open ? '' : 'is-collapsed'}" type="button"
                  data-group="${esc(g.key)}" aria-expanded="${open}">
            <svg class="fold-caret" aria-hidden="true"><use href="#i-caret"></use></svg>
            <span>${esc(g.key)}</span><span class="count">${count}</span></button>
          <div class="tree-items" ${open ? '' : 'hidden'}>${renderItemRows(g.items, all, true)}</div>`;
      }).join('') + '</div>';
    }

    // ---------------------------------------------------------- 冲突提示
    const conflictCount = countConflicts();
    const conflictLine = conflictCount
      ? `<div class="conflict-line">${icon('alert')}<span><b>${conflictCount}</b> 组待处理</span>
         <button type="button" data-conflict="1">查看</button></div>`
      : '';

    $('#filters').innerHTML = head + body + conflictLine;

    // ---------------------------------------------------------- 事件
    $$('[data-mode]').forEach((b) => b.addEventListener('click', () => {
      state.filterMode = b.dataset.mode;
      const pool = visibleMods();
      if (!pool.some((m) => m.id === state.selectedId) && pool.length) {
        state.selectedId = pool[0].id;
      }
      renderFilters(); renderGrid(); renderInspector();
    }));

    $$('[data-group]').forEach((b) => b.addEventListener('click', () => {
      const key = b.dataset.group;
      if (state.openGroups.has(key)) state.openGroups.delete(key);
      else state.openGroups.add(key);
      renderFilters();
    }));

    $$('[data-item]').forEach((b) => b.addEventListener('click', () => {
      state.filterItem = b.dataset.item;
      const pool = visibleMods();
      if (!pool.some((m) => m.id === state.selectedId) && pool.length) {
        state.selectedId = pool[0].id;
      }
      renderFilters(); renderHeader(); renderGrid(); renderInspector();
    }));

    const c = $('[data-conflict]');
    if (c) c.addEventListener('click', showConflictDialog);
  }

  /** 筛选列表排序：全部第一、未指定第二、其余按数量降序。 */
  function orderFilterItems(items, pool) {
    const rank = (name) => {
      if (name.startsWith('全部')) return 0;
      if (name.startsWith('未指定') || name === '未分类') return 1;
      return 2;
    };
    return items.slice().sort((a, b) => {
      const ra = rank(a), rb = rank(b);
      if (ra !== rb) return ra - rb;
      if (ra === 2) {
        const ca = pool.filter((m) => m.item === a).length;
        const cb = pool.filter((m) => m.item === b).length;
        if (ca !== cb) return cb - ca;
      }
      return a.localeCompare(b, 'zh');
    });
  }

  /** 渲染物品行。 */
  function renderItemRows(items, pool, nested) {
    return orderFilterItems(items, pool).map((name) => {
      const isAll = name.startsWith('全部');
      const isUnset = name === '未指定物品';
      const active = state.filterItem
        ? state.filterItem === name
        : isAll;
      let count;
      if (isAll) {
        // 「全部X」= 该分类下的全部；单层列表里 X 是一级标题，等于整个池
        const catName = name.slice(2);
        const matched = pool.filter((m) => m.cat === catName);
        count = matched.length || pool.length;
      } else if (isUnset) {
        count = pool.filter((m) => !m.item).length;
      } else {
        count = pool.filter((m) => m.item === name).length;
      }
      const hasOn = !isAll && pool.some((m) => m.item === name && m.enabled);
      return `<button class="filter-row ${nested ? 'is-nested' : ''} ${active ? 'active' : ''}"
                type="button" data-item="${esc(name)}">
          <span class="item-name">${esc(name)}</span>
          <span class="count">${count || ''}</span>
          ${hasOn ? '<span class="active-mark"></span>' : ''}</button>`;
    }).join('');
  }

  /** 数一数有几组真冲突（只算互斥类别）。 */
  function countConflicts() {
    const groups = {};
    MODS.forEach((m) => {
      if (!m.enabled || !MUTEX_CATEGORIES.has(m.cat) || !m.item) return;
      const k = m.cat + '/' + m.item;
      groups[k] = (groups[k] || 0) + 1;
    });
    return Object.values(groups).filter((n) => n > 1).length;
  }

  // ---------------------------------------------------------------- render: header
  function renderHeader() {
    const rail = RAILS[state.rail];
    const item = state.filterItem && !state.filterItem.startsWith('全部') ? state.filterItem : '';
    const title = item || rail.title;
    $('#crumb').innerHTML = `模组库 ${icon('chevron-right')} ${esc(rail.title)}${item ? ' ' + icon('chevron-right') + ' <strong>' + esc(item) + '</strong>' : ''}`;
    const alias = item ? (MODS.find((m) => m.item === item && m.alias) || {}).alias : '';
    const main = item || rail.title;
    $('#pageTitle').innerHTML = `${esc(main)}` + (alias ? ` <span>${esc(alias)}</span>` : '');
    const list = visibleMods();
    $('#countMeta').innerHTML = `<strong>${String(list.length).padStart(2, '0')}</strong> / ${modsInRail(state.rail).length} 项`;
  }

  // ---------------------------------------------------------------- render: grid
  function renderGrid() {
    const list = visibleMods();
    const grid = $('#grid');
    grid.className = 'grid' + (state.layout === 'list' ? ' list' : '');

    const totalAll = MODS.length;
    const onboard = $('#onboard');
    if (onboard) onboard.hidden = totalAll > 0;

    if (!list.length) {
      grid.innerHTML = totalAll === 0 ? '' : '<div class="empty">没有匹配的模组</div>';
      renderHeader();
      return;
    }

    grid.innerHTML = list.map((m) => {
      const shown = m.alias || m.name;
      return `<article class="mod-card ${m.id === state.selectedId ? 'selected' : ''} ${m.enabled ? 'is-on' : ''}" data-mod="${m.id}" tabindex="0" title="${m.enabled ? '双击停用' : '双击启用'}">
        <div class="mod-thumb">
          <img src="${esc(m.img)}" alt="${esc(shown)}" loading="lazy">
          ${m.enabled ? '<span class="badge-on">已启用</span>' : ''}
        </div>
        <div class="mod-copy">
          <div class="mod-name">${esc(shown)}</div>
          ${m.alias ? `<div class="mod-alias">${esc(m.name)}</div>` : ''}
          <div class="mod-foot"><span>${fmtSize(m.size)}</span><span>${fmtAgo(m.added)}</span></div>
        </div>
      </article>`;
    }).join('');

    $$('[data-mod]').forEach((card) => {
      // 选中只改类名，不重建 DOM —— 否则单击后节点被替换，双击永远收不到第二次点击
      card.addEventListener('click', () => selectCard(card.dataset.mod));
      card.addEventListener('dblclick', () => toggleMod(card.dataset.mod));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          selectCard(card.dataset.mod);
        } else if (e.key === ' ') {
          e.preventDefault();
          toggleMod(card.dataset.mod);
        }
      });
    });
    renderHeader();
  }

  /** 状态筛选下卡片会进出集合，必须重建；否则只改类名。 */
  function repaintAfterToggle() {
    if (state.filterMode !== 'all') {
      renderGrid();
    } else {
      paintCards();
    }
    renderInspector();
    renderFilters();
  }

  /** 只更新卡片外观，不重建节点。 */
  function paintCards() {
    $$('[data-mod]').forEach((card) => {
      const m = MODS.find((x) => x.id === card.dataset.mod);
      if (!m) return;
      card.classList.toggle('selected', m.id === state.selectedId);
      card.classList.toggle('is-on', !!m.enabled);
      card.title = m.enabled ? '双击停用' : '双击启用';
      let badge = card.querySelector('.badge-on');
      if (m.enabled && !badge) {
        badge = document.createElement('span');
        badge.className = 'badge-on';
        badge.textContent = '已启用';
        card.querySelector('.mod-thumb').appendChild(badge);
      } else if (!m.enabled && badge) {
        badge.remove();
      }
    });
  }

  function selectCard(id) {
    state.selectedId = id;
    paintCards();
    renderInspector();
  }

  // ---------------------------------------------------------------- render: inspector
  function renderInspector() {
    const m = selected();
    if (!m) {
      $('#inspector').innerHTML = '<div class="empty">选择左侧任意模组查看详情。</div>';
      return;
    }
    const group = sameGroup(m);
    const shown = m.alias || m.name;

    const specRows = [
      ['文件', m.file],
      ['分类', m.item ? `${m.cat} / ${m.item}` : m.cat],
      ['大小', fmtSize(m.size)],
      ['入库时间', m.addedDate || '—'],
      ...(m.ws ? [['工坊', m.ws]] : []),
    ];

    const groupRows = [
      `<div class="group-mini active"><img src="${esc(m.img)}" alt=""><span>${esc(shown)}</span>${icon('check')}</div>`,
      ...group.slice(0, 3).map((x) => `<div class="group-mini" data-pick="${x.id}"><img src="${esc(x.img)}" alt=""><span>${esc(x.alias || x.name)}</span></div>`),
    ].join('');

    $('#inspector').innerHTML = `
      <div class="inspector-head">
        <div class="title-block">
          <h2 class="detail-title">${esc(shown)}</h2>
          ${m.alias ? `<p class="detail-sub">${esc(m.name)}</p>` : ''}
        </div>
        <button class="close" type="button" id="insClose" aria-label="关闭详情">${icon('x')}</button>
      </div>

      <div class="preview"><img src="${esc(m.img)}" alt="${esc(shown)}" loading="lazy"></div>

      <div class="status-card ${m.enabled ? '' : 'off'}">
        <div class="status-left"><i class="dot"></i>${m.enabled ? '已启用' : '未启用'}</div>
        <button class="switch ${m.enabled ? 'on' : ''}" type="button" id="insSwitch" role="switch"
          aria-checked="${m.enabled}" aria-label="启用或停用">${'<span class="knob"></span>'}</button>
      </div>

      <div class="spec-list">
        ${specRows.map(([k, v]) => `<div class="spec-row"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`).join('')}
      </div>

      ${group.length ? `<div class="group-panel">
        <div class="group-head"><span>同组</span><span class="group-count">${group.filter((x) => x.enabled).length + (m.enabled ? 1 : 0)} / ${group.length + 1}</span></div>
        ${groupRows}
      </div>` : ''}

      <div class="inspector-actions">
        <button class="icon-action" type="button" id="insAlias" title="设置别名" aria-label="设置别名">${icon('tag')}</button>
        <button class="icon-action" type="button" id="insFolder" title="打开文件夹" aria-label="打开文件夹">${icon('folder')}</button>
        ${m.ws ? `<button class="icon-action" type="button" id="insWorkshop" title="打开工坊页" aria-label="打开工坊页">${icon('external')}</button>` : ''}
        <div class="more-wrap">
          <button class="icon-action" type="button" id="insMore" title="更多操作" aria-label="更多操作" aria-expanded="false">${icon('more')}</button>
          <div class="more-menu" id="insMoreMenu" hidden>
            <button type="button" data-more="category">修改分类</button>
            ${m.cat === '地图' ? '<button type="button" data-more="collection">归入合集</button>' : ''}
          </div>
        </div>
        <span class="actions-spacer"></span>
        <button class="icon-action danger" type="button" id="insDelete" title="移入回收站" aria-label="移入回收站">${icon('trash')}</button>
      </div>`;

    $('#insClose').addEventListener('click', () => { state.selectedId = null; renderGrid(); renderInspector(); });

    $('#insSwitch').addEventListener('click', () => toggleMod(m.id));

    $('#insAlias').addEventListener('click', async () => {
      const value = prompt('别名（留空恢复原名）', m.alias || '');
      if (value === null) return;
      const next = value.trim();
      const res = await window.bridge.set_alias(m.file, next);
      if (!res || !res.ok) {
        await infoDialog({ title: '无法保存别名', tone: 'danger',
                           text: (res && res.error) || '写入失败' });
        return;
      }
      m.alias = next;
      renderGrid(); renderInspector();
      toast(next ? '别名已保存' : '已恢复原名');
    });

    $('#insFolder').addEventListener('click', async () => {
      const res = await window.bridge.reveal_mod(m.file);
      if (!res || !res.ok) toast((res && res.error) || '无法打开文件夹');
    });
    const ws = $('#insWorkshop');
    if (ws) ws.addEventListener('click', () => infoDialog({
      title: '打开工坊页',
      text: '演示环境不会真的打开浏览器。实际实现会跳转到 Steam 创意工坊页面。',
    }));

    $('#insMore').addEventListener('click', (e) => {
      e.stopPropagation();
      const menu = $('#insMoreMenu');
      menu.hidden = !menu.hidden;
      $('#insMore').setAttribute('aria-expanded', String(!menu.hidden));
    });
    // 菜单开着时，点任何外部位置都收起
    if (!window.__moreMenuBound) {
      window.__moreMenuBound = true;
      const closeMore = () => {
        document.querySelectorAll('.more-menu').forEach((mm) => { mm.hidden = true; });
        document.querySelectorAll('[data-more]').forEach((b) => {
          const btn = b.closest('.more-wrap');
          if (btn) {
            const trigger = btn.querySelector('.icon-action');
            if (trigger) trigger.setAttribute('aria-expanded', 'false');
          }
        });
      };
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.more-wrap')) closeMore();
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMore();
      });
      // 侧栏滚动时也要收，否则菜单会飘在错误位置
      const insp = document.getElementById('inspector');
      if (insp && !insp.dataset.moreBound) {
        insp.dataset.moreBound = '1';
        insp.addEventListener('scroll', closeMore, { passive: true });
      }
    }
    $$('[data-more]').forEach((b) => b.addEventListener('click', async () => {
      $('#insMoreMenu').hidden = true;
      if (b.dataset.more === 'category') {
        await infoDialog({ title: '修改分类', text: '实际实现会打开分类选择对话框，演示页暂不展开。' });
      } else {
        await infoDialog({ title: '归入合集', text: '实际实现会解析合集链接或选择已有合集。' });
      }
    }));

    $$('[data-pick]').forEach((b) => b.addEventListener('click', async () => {
      const target = b.dataset.pick;
      const targetMod = MODS.find((x) => x.id === target);
      if (!targetMod) return;

      // 与 Mod Grid 双击行为一致：启用同组另一项时先确认互斥
      if (!targetMod.enabled && MUTEX_CATEGORIES.has(targetMod.cat)) {
        const siblings = sameGroup(targetMod).filter((x) => x.enabled);
        if (siblings.length) {
          const ok = await confirmDialog({
            title: '切换同组外观',
            tone: 'question',
            text: `启用后，同组的 ${siblings.length} 个模组会被自动停用。`,
            rows: siblings.map((x) => ({
              name: x.alias || x.name, tag: '将停用', tone: 'warn',
            })),
            confirm: '启用',
          });
          if (!ok) return;
          await window.bridge.toggle_mod(target, true);
        }
      }
      state.selectedId = target;
      renderGrid(); renderInspector(); renderFilters();
    }));

    $('#insDelete').addEventListener('click', async () => {
      const ok = await confirmDialog({
        title: '删除模组',
        tone: 'danger',
        text: `《${shown}》将从模组库移除，文件移入回收站。`,
        check: '今日不再提醒',
        confirm: '移到回收站',
        danger: true,
      });
      if (!ok) return;
      const res = await window.bridge.delete_mod(m.file);
      if (!res || !res.ok) {
        await infoDialog({ title: '删除失败', tone: 'danger',
                           text: (res && res.error) || '写入失败' });
        return;
      }
      const i = MODS.findIndex((x) => x.id === m.id);
      if (i >= 0) MODS.splice(i, 1);
      state.selectedId = null;
      renderFilters(); renderGrid(); renderInspector();
      toast('已移到回收站');
    });
  }


  // ---------------------------------------------------------------- 数据适配
  // 后端字段（title/category/thumb/size 字节）→ 界面字段（name/cat/img/size MB）
  function adapt(apiMod) {
    return {
      id: apiMod.file || '',
      name: apiMod.title || apiMod.file || '',
      alias: apiMod.alias || '',
      cat: apiMod.category || '未分类',
      item: apiMod.item || '',
      size: (apiMod.size || 0) / 1048576,
      img: apiMod.thumb || '',
      enabled: !!apiMod.enabled,
      // 后端 added 是秒级时间戳，统一成「几天前」
      added: apiMod.added
        ? Math.max(0, Math.round((Date.now() / 1000 - apiMod.added) / 86400))
        : 0,
      // 用本地时区，否则东八区 0-8 点入库会显示前一天
      addedDate: apiMod.added
        ? new Date(apiMod.added * 1000).toLocaleDateString('sv-SE')
        : '',
      file: apiMod.file || '',
      ws: apiMod.workshop_id || '',
      mutex: !!apiMod.mutex,
    };
  }

  async function loadFromBridge() {
    await window.bridge.whenReady();
    const res = await window.bridge.bootstrap();
    if (!res || !res.ok) {
      if (window.bridge.isMock()) MODS = DEMO_MODS.slice();
      return false;
    }
    MODS = (res.mods || []).map(adapt);
    state.settings = res.settings || state.settings;
    state.version = res.version || state.version;
    state.gameRunning = !!(res.game && res.game.running);
    applyGameStatus();
    if (res.paths && res.paths.addons) {
      const el = $('#statusPath');
      if (el) el.textContent = res.paths.addons;
    }
    if (MODS.length && !MODS.some((m) => m.id === state.selectedId)) {
      state.selectedId = MODS[0].id;
    }
    return true;
  }

  /** 把 state.gameRunning 同步到顶栏指示与启动按钮。 */
  function applyGameStatus() {
    const dot = $('#gameStatus');
    const btn = $('#launchBtn');
    if (dot) {
      dot.classList.toggle('running', state.gameRunning);
      dot.title = state.gameRunning ? '游戏运行中' : '游戏未运行';
    }
    if (btn) btn.disabled = state.gameRunning;
  }

  async function reloadMods() {
    const res = await window.bridge.bootstrap();
    if (res && res.ok) {
      MODS = (res.mods || []).map(adapt);
      return true;
    }
    return false;
  }

  /** 跑一个后端长任务，把事件桥接到 UI 回调。 */
  function runJob(jobId, onProgress, onDone, onError) {
    const offs = [];
    const cleanup = () => offs.forEach((off) => { try { off(); } catch (e) {} });
    offs.push(window.events.on('job.progress', (p) => {
      if (p && p.job_id === jobId && onProgress) onProgress(p);
    }));
    offs.push(window.events.on('job.done', (p) => {
      if (!p || p.job_id !== jobId) return;
      cleanup();
      if (onDone) onDone(p.result || {});
    }));
    offs.push(window.events.on('job.error', (p) => {
      if (!p || p.job_id !== jobId) return;
      cleanup();
      if (onError) onError(p.message || '任务失败');
    }));
  }

  // ---------------------------------------------------------------- actions
  async function toggleMod(id) {
    const m = MODS.find((x) => x.id === id);
    if (!m) return;
    state.selectedId = id;                 // 双击同时选中，Inspector 跟着变
    if (state.gameRunning) {
      paintCards(); renderInspector();
      await infoDialog({ title: '游戏运行中', tone: 'warning', text: '游戏运行时无法修改模组配置，请先退出游戏。' });
      return;
    }
    // ---- 停用 ----
    if (m.enabled) {
      const res = await window.bridge.toggle_mod(m.file, false);
      if (!res || !res.ok) {
        paintCards(); renderInspector();
        await infoDialog({ title: '无法停用', tone: 'danger',
                           text: (res && res.error) || '写入失败' });
        return;
      }
      m.enabled = false;
      repaintAfterToggle();
      toast('已停用');
      return;
    }

    // ---- 启用 ----
    const siblings = sameGroup(m).filter((x) => x.enabled);
    if (siblings.length) {
      const ok = await confirmDialog({
        title: '切换同组外观',
        tone: 'question',
        text: `启用后，同组的 ${siblings.length} 个模组会被自动停用。`,
        rows: siblings.map((x) => ({ name: x.alias || x.name, tag: '将停用', tone: 'warn' })),
        confirm: '启用',
      });
      if (!ok) { paintCards(); renderInspector(); return; }
    }

    const res = await window.bridge.toggle_mod(m.file, true);
    if (!res || !res.ok) {
      paintCards(); renderInspector();
      await infoDialog({ title: '无法启用', tone: 'danger',
                         text: (res && res.error) || '写入失败' });
      return;
    }
    m.enabled = true;
    // 后端会连带停用同组，用返回值校正本地状态
    (res.disabled_siblings || []).forEach((f) => {
      const sib = MODS.find((x) => x.file === f);
      if (sib) sib.enabled = false;
    });
    repaintAfterToggle();
    toast('已启用');
  }

  async function showConflictDialog() {
    const groups = {};
    MODS.forEach((m) => {
      if (!m.enabled) return;
      // 非互斥类别不参与冲突判定
      if (!MUTEX_CATEGORIES.has(m.cat)) return;
      if (!m.item) return;
      const k = m.cat + '/' + m.item;
      (groups[k] = groups[k] || []).push(m);
    });
    const conflicts = Object.entries(groups).filter(([, list]) => list.length > 1);
    if (!conflicts.length) {
      await infoDialog({ title: '没有待处理项', text: '当前每个外观组都只有一个启用项。' });
      return;
    }
    const ok = await confirmDialog({
      title: '处理同组冲突',
      tone: 'warning',
      text: '每组保留最新加入的一项，其余停用。',
      rows: conflicts.flatMap(([k, list]) => {
        const keep = list.slice().sort((a, b) => a.added - b.added)[0];
        return list.map((m) => ({
          name: `${k} · ${m.alias || m.name}`,
          tag: m === keep ? '保留' : '将停用',
          tone: m === keep ? 'ok' : 'warn',
        }));
      }),
      confirm: '自动处理',
    });
    if (!ok) return;
    // 保留最新启用的一项（added 是「几天前」，数值越小越新）
    const toDisable = [];
    conflicts.forEach(([, list]) => {
      const keep = list.slice().sort((a, b) => a.added - b.added)[0];
      list.filter((x) => x !== keep).forEach((x) => toDisable.push(x));
    });

    let done = 0;
    for (const mod of toDisable) {
      const res = await window.bridge.toggle_mod(mod.file, false);
      if (res && res.ok) { mod.enabled = false; done += 1; }
    }

    renderGrid(); renderInspector(); renderFilters();
    toast(`已处理 ${conflicts.length} 组` + (done < toDisable.length
      ? `（${toDisable.length - done} 个失败）` : ''));
  }

  // ---------------------------------------------------------------- status bar
  function setStatus(mode, { label = '', pct = 0, text = '', action = null } = {}) {
    $('#statusIdle').hidden = mode !== 'idle';
    $('#statusActivity').hidden = mode !== 'scanning';
    $('#statusError').hidden = mode !== 'error';
    if (mode === 'scanning') {
      $('#statusActivityLabel').textContent = label;
      $('#statusActivityBar').style.width = pct + '%';
    }
    if (mode === 'error') {
      $('#statusErrorText').textContent = text;
      const btn = $('#statusErrorAction');
      btn.hidden = !action;
      btn.onclick = action ? () => action() : null;
    }
  }

  async function runScan() {
    if (scanFlow.running) return;
    scanFlow.running = true;

    const res = await window.bridge.start_scan();
    if (!res || !res.ok) {
      scanFlow.running = false;
      await infoDialog({ title: '无法扫描', tone: 'danger',
                         text: (res && res.error) || '扫描失败' });
      return;
    }

    setStatus('scanning', { label: '扫描中', pct: 0 });

    runJob(res.job_id,
      (p) => setStatus('scanning', { label: p.label || '扫描中', pct: p.percent || 0 }),
      async (result) => {
        scanFlow.running = false;
        setStatus('idle');
        await reloadMods();
        renderFilters(); renderGrid(); renderInspector();
        const n = (result && result.count) || MODS.length;
        toast(`扫描完成 · ${n} 个模组`);
      },
      async (msg) => {
        scanFlow.running = false;
        setStatus('error', {
          text: msg || '扫描失败',
          action: () => runScan(),
        });
      });
  }

  // ---------------------------------------------------------------- import flow
  const scanFlow = { running: false };
  const importFlow = { candidates: [], running: false };

  function setImportProgress({ title, label, meta, pct }) {
    $('#importProgress').hidden = false;
    $('#importProgressTitle').textContent = title;
    $('#importProgressMeta').textContent = meta || '';
    $('#importProgressLabel').textContent = label || '';
    $('#importProgressBar').style.width = (pct || 0) + '%';
  }

  function renderImportCandidates() {
    const list = $('#importList');
    list.innerHTML = importFlow.candidates.map((c, i) => `
      <label class="task-row ${c.dup ? 'is-dup' : ''} ${c.selected ? 'is-checked' : ''}" data-cand="${i}">
        <input type="checkbox" ${c.selected ? 'checked' : ''} ${c.dup ? 'disabled' : ''}>
        <img src="${esc(c.img)}" alt="">
        <span class="task-copy"><b>${esc(c.name)}</b><small>${esc(c.meta)}</small></span>
        ${c.dup ? '<span class="task-tag">已在库</span>' : ''}
      </label>`).join('');

    const selectable = importFlow.candidates.filter((c) => !c.dup);
    const picked = selectable.filter((c) => c.selected).length;
    $('#importPanelTitle').textContent = `可加入的模组 · ${selectable.length}`;
    $('#importActions').hidden = !selectable.length;
    $('#importCommit').textContent = `加入模组库（${picked}）`;
    $('#importCommit').disabled = picked === 0;

    $$('[data-cand] input').forEach((box) => {
      box.addEventListener('change', () => {
        const row = box.closest('[data-cand]');
        const c = importFlow.candidates[Number(row.dataset.cand)];
        if (!c || c.dup) return;
        c.selected = box.checked;
        renderImportCandidates();
      });
    });
  }

  async function runImport() {
    if (importFlow.running) return;
    importFlow.running = true;      // 立刻占据，避免拖拽触发两次

    let paths = [];
    if (!window.bridge.isMock()) {
      const picked = await window.bridge.choose_archives();
      if (!picked || !picked.ok || !picked.paths || !picked.paths.length) return;
      paths = picked.paths;
    } else {
      paths = ['mock.7z'];
    }

    importFlow.candidates = [];
    importFlow.batchJob = null;

    $('#importPanel').hidden = true;
    $('#importActions').hidden = true;
    $('#dropZone').hidden = true;
    setImportProgress({ title: '正在解析', label: '准备中', meta: '', pct: 0 });

    const res = await window.bridge.analyze_archives(paths);
    if (!res || !res.ok) {
      importFlow.running = false;
      $('#importProgress').hidden = true;
      $('#dropZone').hidden = false;
      await infoDialog({ title: '无法导入', tone: 'warning',
                         text: (res && res.error) || '解析失败' });
      return;
    }

    importFlow.batchJob = res.job_id;
    runJob(res.job_id,
      (p) => setImportProgress({
        title: '正在解析', label: p.label || '读取压缩包',
        meta: (p.percent || 0) + '%', pct: p.percent || 0,
      }),
      (result) => {
        importFlow.candidates = (result.candidates || []).map((c) => ({
          stem: c.stem,
          name: c.title || c.stem,
          meta: [c.category, c.item].filter(Boolean).join(' / ')
                + (c.sizeText ? ' · ' + c.sizeText : ''),
          img: c.thumb || '',
          dup: !!c.duplicate,
          parseError: c.parseError || '',
          selected: !!c.selected,
        }));
        $('#importProgress').hidden = true;
        $('#dropZone').hidden = false;
        importFlow.running = false;
        $('#importPanel').hidden = false;
        renderImportCandidates();
      },
      async (msg) => {
        $('#importProgress').hidden = true;
        $('#dropZone').hidden = false;
        importFlow.running = false;
        await infoDialog({ title: '解析失败', tone: 'danger', text: msg });
      });
  }

  async function commitImport() {
    const picked = importFlow.candidates.filter(
      (c) => c.selected && !c.dup && !c.parseError);
    if (!picked.length) return;

    if (state.gameRunning) {
      await infoDialog({ title: '游戏运行中', tone: 'warning',
                         text: '游戏运行时无法写入模组库，请先退出游戏。' });
      return;
    }

    $('#importPanel').hidden = true;
    $('#importActions').hidden = true;
    $('#dropZone').hidden = true;
    setImportProgress({ title: `正在导入 ${picked.length} 个模组`,
                        label: picked[0].name, meta: '0 / ' + picked.length, pct: 0 });

    const stems = picked.map((c) => c.stem).filter(Boolean);
    const res = await window.bridge.commit_import(importFlow.batchJob, stems);
    if (!res || !res.ok) {
      $('#importProgress').hidden = true;
      $('#importPanel').hidden = false;
      $('#dropZone').hidden = false;
      await infoDialog({ title: '导入失败', tone: 'danger',
                         text: (res && res.error) || '写入失败' });
      return;
    }

    runJob(res.job_id,
      (p) => setImportProgress({
        title: `正在导入 ${picked.length} 个模组`,
        label: p.label || '', meta: (p.percent || 0) + '%', pct: p.percent || 0,
      }),
      async (result) => {
        $('#importProgress').hidden = true;
        $('#dropZone').hidden = false;
        await infoDialog({
          title: '导入完成',
          text: `已加入模组库 ${result.imported || picked.length} 个。`,
          rows: picked.map((c) => ({ name: c.name, tag: '已写入', tone: 'ok' })),
        });
        importFlow.candidates = [];
        await reloadMods();
        renderFilters(); renderGrid(); renderInspector();
      },
      async (msg) => {
        $('#importProgress').hidden = true;
        $('#importPanel').hidden = false;
        $('#dropZone').hidden = false;
        await infoDialog({ title: '导入失败', tone: 'danger', text: msg });
      });
  }

  // ---------------------------------------------------------------- download flow
  const dlFlow = { items: [], running: false, collection: null };

  function log(text) {
    const box = $('#dlLog');
    if (!box) return;
    const t = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    box.insertAdjacentHTML('beforeend', `<div>[${t}] ${esc(text)}</div>`);
    box.scrollTop = box.scrollHeight;
  }

  function renderDownloadItems() {
    const list = $('#downloadList');
    list.innerHTML = dlFlow.items.map((it, i) => `
      <label class="task-row ${it.dup ? 'is-dup' : ''}" data-dl="${i}">
        <input type="checkbox" ${it.selected ? 'checked' : ''} ${it.dup ? 'disabled' : ''}>
        <img src="${esc(it.img)}" alt="">
        <span class="task-copy"><b>${esc(it.name)}</b><small>${esc(it.meta)}</small></span>
        ${it.dup ? '<span class="task-tag">已在库</span>' : ''}
      </label>`).join('');
    const selectable = dlFlow.items.filter((i) => !i.dup);
    const picked = selectable.filter((i) => i.selected).length;
    $('#downloadPanelTitle').textContent = dlFlow.collection
      ? `已解析 · ${dlFlow.collection.name || '合集'}`
      : '已解析';
    $('#downloadPanelMeta').textContent = `${selectable.length} 个可下载`;
    $('#downloadActions').hidden = !selectable.length;
    $('#downloadStart').textContent = `开始下载（${picked}）`;
    $('#downloadStart').disabled = picked === 0;
    $$('[data-dl] input').forEach((box) => box.addEventListener('change', () => {
      const row = box.closest('[data-dl]');
      const it = dlFlow.items[Number(row.dataset.dl)];
      if (!it || it.dup) return;
      it.selected = box.checked;
      renderDownloadItems();
    }));
  }

  async function parseLink() {
    const raw = $('#linkInput').value.trim();
    if (!raw) {
      await infoDialog({ title: '无法解析', tone: 'warning',
                         text: '请先粘贴创意工坊链接或物品 ID。' });
      return;
    }

    $('#downloadPanel').hidden = true;
    $('#downloadActions').hidden = true;
    $('#downloadRunning').hidden = false;
    $('#dlRunTitle').textContent = '正在解析链接';
    $('#dlRunMeta').textContent = '';
    $('#dlLog').innerHTML = '';
    $('#dlRunBar').style.width = '0%';
    $('#dlRunLabel').textContent = '识别物品 ID';
    log('开始解析：' + raw);

    const res = await window.bridge.parse_links(raw);
    if (!res || !res.ok || !res.ids || !res.ids.length) {
      $('#downloadRunning').hidden = true;
      await infoDialog({ title: '链接无效', tone: 'warning',
                         text: (res && res.error) || '没有识别到有效的创意工坊物品 ID。' });
      return;
    }
    log('识别到 ' + res.ids.length + ' 个物品 ID');

    $('#dlRunLabel').textContent = '读取工坊详情';
    const details = await window.bridge.fetch_details(res.ids);
    if (!details || !details.ok) {
      $('#downloadRunning').hidden = true;
      await infoDialog({ title: '解析失败', tone: 'danger',
                         text: (details && details.error) || '读取工坊详情失败' });
      return;
    }

    dlFlow.collection = details.collection || null;
    dlFlow.items = (details.items || []).map((d) => ({
      id: d.id,
      name: d.title || d.id,
      meta: (d.sizeText ? d.sizeText : '') + (d.existing ? ' · 已在库' : ''),
      img: d.thumb || '',
      dup: !!d.existing,
      selected: !d.existing,
    }));
    log('读取完成：' + dlFlow.items.length + ' 个物品');

    $('#dlRunBar').style.width = '0%';
    $('#downloadRunning').hidden = true;
    $('#downloadPanel').hidden = false;
    renderDownloadItems();
  }

  async function startDownload() {
    const picked = dlFlow.items.filter((i) => i.selected && !i.dup);
    if (!picked.length) return;
    if (state.gameRunning) {
      await infoDialog({ title: '游戏运行中', tone: 'warning',
                         text: '请先关闭游戏，再下载导入模组。' });
      return;
    }

    $('#downloadPanel').hidden = true;
    $('#downloadActions').hidden = true;
    $('#downloadRunning').hidden = false;
    $('#dlRunTitle').textContent = `正在下载 ${picked.length} 个模组`;
    $('#dlRunMeta').textContent = '';
    $('#dlLog').innerHTML = '';
    $('#dlRunLabel').textContent = picked[0].name;
    log(`准备下载 ${picked.length} 个模组`);

    const res = await window.bridge.start_download(
      picked.map((i) => i.id), dlFlow.collection);
    if (!res || !res.ok) {
      $('#downloadRunning').hidden = true;
      $('#downloadPanel').hidden = false;
      $('#downloadActions').hidden = false;
      await infoDialog({ title: '无法下载', tone: 'danger',
                         text: (res && res.error) || '启动下载失败' });
      return;
    }

    runJob(res.job_id,
      (p) => {
        $('#dlRunBar').style.width = (p.percent || 0) + '%';
        if (p.current) {
          $('#dlRunLabel').textContent = p.current;
          if (p.label) log(p.label);
        }
        $('#dlRunMeta').textContent = `已完成 ${p.percent || 0}%`;
      },
      async (result) => {
        $('#downloadRunning').hidden = true;
        const recs = (result && result.records) || [];
        const fails = (result && result.failures) || [];
        const skipped = (result && result.skipped) || [];
        log(`完成：导入 ${recs.length}，失败 ${fails.length}，跳过 ${skipped.length}`);

        if (fails.length) {
          await infoDialog({
            title: '部分下载未完成',
            tone: 'warning',
            text: `已导入 ${recs.length} 个，失败 ${fails.length} 个。`,
            rows: fails.map((f) => ({ name: f.title || f.id,
                                      tag: (f.error || '').slice(0, 20) || '失败',
                                      tone: 'bad' })),
          });
        } else {
          await infoDialog({
            title: '下载完成',
            text: `已导入 ${recs.length} 个模组`
                  + (skipped.length ? `，跳过 ${skipped.length} 个已在库的条目` : '') + '。',
            rows: recs.map((r, i) => ({ name: picked[i] ? picked[i].name : String(i + 1),
                                        tag: '已启用', tone: 'ok' })),
          });
        }

        await reloadMods();
        renderFilters(); renderGrid(); renderInspector();
        renderDownloadItems();
        $('#downloadPanel').hidden = false;
        $('#downloadActions').hidden = false;
      },
      async (msg) => {
        $('#downloadRunning').hidden = true;
        $('#downloadPanel').hidden = false;
        $('#downloadActions').hidden = false;
        await infoDialog({ title: '下载失败', tone: 'danger', text: msg });
      });
  }

  // ---------------------------------------------------------------- settings
  function renderSettings() {
    $('#settings').innerHTML = `
      <div class="settings-group">
        <h3>游戏</h3>
        <div class="settings-row">
          <div class="settings-copy"><b>L4D2 目录</b><small class="path">${esc(state.settings.game_dir || "未设置")}</small></div>
          <button class="btn" type="button" data-setting="detect">自动检测</button>
          <button class="btn" type="button" data-setting="browse">更改目录</button>
        </div>
        <div class="settings-row">
          <div class="settings-copy"><b>游戏运行状态</b><small>用于演示「写入被锁」的拦截逻辑</small></div>
          <button class="switch ${state.gameRunning ? 'on' : ''}" type="button" data-setting="game" role="switch" aria-checked="${state.gameRunning}"><span class="knob"></span></button>
        </div>
      </div>

      <div class="settings-group">
        <h3>网络</h3>
        <div class="settings-row">
          <div class="settings-copy"><b>代理</b><small>留空时自动探测本地代理</small></div>
          <input class="btn" style="width:220px;text-align:left" value="" placeholder="http://127.0.0.1:7890">
          <button class="btn" type="button" data-setting="saveProxy">保存</button>
        </div>
      </div>

      <div class="settings-group">
        <h3>缓存与更新</h3>
        <div class="settings-row">
          <div class="settings-copy"><b>清理缓存</b><small>删除缩略图缓存与临时解压目录</small></div>
          <button class="btn" type="button" data-setting="clean">清理</button>
        </div>
        <div class="settings-row">
          <div class="settings-copy"><b>检查更新</b><small>当前版本 v${esc(state.version)}</small></div>
          <button class="btn" type="button" data-setting="update">检查更新</button>
        </div>
      </div>

      <div class="settings-group">
        <h3>关于</h3>
        <div class="settings-row">
          <div class="settings-copy"><b>L4D2 Mod Manager</b><small>v${esc(state.version)} · MIT License</small></div>
          <button class="btn" type="button" data-setting="repo">查看仓库</button>
        </div>
      </div>`;

    $$('[data-setting]').forEach((b) => b.addEventListener('click', async () => {
      const kind = b.dataset.setting;

      if (kind === 'game') {
        state.gameRunning = !state.gameRunning;
        applyGameStatus();
        renderSettings();
        toast(state.gameRunning ? '已标记为运行中' : '已标记为未运行');
        return;
      }

      if (kind === 'detect' || kind === 'browse') {
        const res = kind === 'detect'
          ? await window.bridge.detect_game_dir()
          : await window.bridge.choose_dir();
        const dir = res && res.ok ? (res.game_dir || res.path || '') : '';
        if (!dir) {
          await infoDialog({ title: '未找到', tone: 'warning',
                             text: (res && res.error) || '未能自动定位游戏目录，请手动选择。' });
          return;
        }
        await window.bridge.save_setting('game_dir', dir);
        state.settings.game_dir = dir;
        renderSettings();
        await loadFromBridge();
        renderFilters(); renderGrid(); renderInspector();
        toast('已更新游戏目录');
        return;
      }

      if (kind === 'clean') {
        const ok = await confirmDialog({
          title: '清理缓存', tone: 'question',
          text: '将删除缩略图缓存与临时解压目录，不影响模组文件。',
          confirm: '清理',
        });
        if (!ok) return;
        const res = await window.bridge.clean_cache();
        await infoDialog({
          title: '清理缓存',
          tone: (res && res.ok) ? 'info' : 'danger',
          text: (res && res.ok)
            ? (res.freed > 0
                ? `已释放 ${(res.freed / 1048576).toFixed(1)} MB。`
                : '没有可清理的文件。')
            : ((res && res.error) || '清理失败'),
        });
        return;
      }

      if (kind === 'update') {
        const res = await window.bridge.check_update();
        await infoDialog({
          title: '检查更新',
          text: (res && res.ok)
            ? (res.latest && res.latest !== state.version
                ? `发现新版本 ${res.latest}（当前 v${state.version}）。`
                : `当前已是最新版本 v${state.version}。`)
            : ((res && res.error) || '检查失败'),
        });
        return;
      }

      if (kind === 'saveProxy') {
        const input = $('#proxyInput');
        await window.bridge.save_setting('proxy', input ? input.value.trim() : '');
        toast('代理已保存');
        return;
      }

      if (kind === 'repo') {
        await window.bridge.open_path('https://github.com/PolysaCHride/l4d2-mod-manager');
        return;
      }
    }));
  }

  // ---------------------------------------------------------------- view switching
  function setView(view) {
    state.view = view;
    $('#toast').classList.remove('show');
    $$('.ws-tab').forEach((t) => {
      const on = t.dataset.view === view;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', String(on));
    });
    $$('[data-panel]').forEach((p) => { p.hidden = p.dataset.panel !== view; });

    // 任务视图没有「当前对象」：Inspector 与大标题都不出现，
    // 面包屑已经说明所在位置，重复一次标题没有信息量。
    const isLibrary = view === 'library';
    $('#inspector').hidden = !isLibrary;
    $('#pageTitle').hidden = !isLibrary;
    $('#app').classList.toggle('task-view', !isLibrary);

    $('#filters').hidden = !isLibrary;
    if (isLibrary) {
      renderHeader();
    } else {
      const labels = { import: '导入压缩包', download: '链接下载', settings: '设置' };
      $('#crumb').innerHTML = `模组库 ${icon('chevron-right')} ${labels[view] || ''}`;
    }
    if (view === 'settings') renderSettings();
  }

  // ---------------------------------------------------------------- wiring
  $$('.ws-tab').forEach((t) => t.addEventListener('click', () => setView(t.dataset.view)));
  $$('[data-view="settings"]').forEach((b) => b.addEventListener('click', () => setView('settings')));

  $$('[data-rail]').forEach((b) => b.addEventListener('click', () => {
    // 在导入 / 下载 / 设置里点分类，直接回到浏览，不用先手动切 tab
    if (state.view !== 'library') setView('library');
    state.rail = b.dataset.rail;
    state.filterItem = null;
    state.query = '';
    const pool = modsInRail(state.rail);
    if (!pool.some((m) => m.id === state.selectedId)) {
      state.selectedId = pool.length ? pool.slice().sort((a, b) => a.added - b.added)[0].id : null;
    }
    renderRail(); renderFilters(); renderGrid(); renderInspector();
  }));

  $$('[data-layout]').forEach((b) => b.addEventListener('click', () => {
    state.layout = b.dataset.layout;
    $$('[data-layout]').forEach((x) => x.classList.toggle('active', x === b));
    renderGrid();
  }));

  $('#sortBtn').addEventListener('click', async () => {
    const ok = await confirmDialog({
      title: '排序',
      tone: 'question',
      text: '选择排序方式（演示用对话框代替下拉菜单）。',
      confirm: '最近添加',
      cancel: '取消',
    });
    if (ok) { state.sort = 'added'; renderGrid(); }
  });

  $('#refreshBtn').addEventListener('click', () => runScan());
  $('#tidyBtn').addEventListener('click', () => runScan());

  $('#search').addEventListener('input', (e) => {
    state.query = e.target.value.trim();
    if (state.view !== 'library') setView('library');
    renderGrid();
  });

  $('#launchBtn').addEventListener('click', () => {
    if (state.gameRunning) { toast('游戏已在运行'); return; }
    infoDialog({ title: '启动游戏', text: '演示环境不会真的启动 L4D2。实际实现会调用 Steam 启动。' });
  });

  $$('[data-caption]').forEach((b) => b.addEventListener('click', async (e) => {
    e.stopPropagation();
    const kind = b.dataset.caption;

    if (kind === 'min') {
      await window.bridge.win_minimize();
      return;
    }

    if (kind === 'max') {
      const res = await window.bridge.win_toggle_maximize();
      document.body.classList.toggle(
        'is-maximized', !!(res && res.maximized));
      return;
    }

    if (kind === 'close') {
      await window.bridge.win_close();
      return;
    }
  }));

  $('#dropZone').addEventListener('click', () => runImport());

  $$('[data-import-all]').forEach((b) => b.addEventListener('click', () => {
    const on = b.dataset.importAll === '1';
    importFlow.candidates.forEach((c) => { if (!c.dup) c.selected = on; });
    renderImportCandidates();
  }));

  $('#importCommit').addEventListener('click', () => commitImport());
  $('#parseBtn').addEventListener('click', () => parseLink());
  $('#linkInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') parseLink(); });
  $('#downloadStart').addEventListener('click', () => startDownload());
  $('#statusPath').addEventListener('click', () => toast('已在资源管理器中打开 addons 目录'));

  // drag & drop on the import zone
  ['dragenter', 'dragover'].forEach((evt) => $('#dropZone').addEventListener(evt, (e) => {
    e.preventDefault();
    $('#dropZone').classList.add('drag');
  }));
  ['dragleave', 'drop'].forEach((evt) => $('#dropZone').addEventListener(evt, (e) => {
    e.preventDefault();
    $('#dropZone').classList.remove('drag');
  }));
  $('#dropZone').addEventListener('drop', (e) => {
    const name = (e.dataTransfer.files[0] || {}).name || '';
    if (name && !/\.(zip|7z|rar)$/i.test(name)) {
      infoDialog({ title: '无法导入', tone: 'warning', text: '只支持 ZIP、7z 和 RAR。' });
      return;
    }
    runImport();
  });
  // let the whole view accept drops
  const importView = $('[data-panel="import"]');
  importView.addEventListener('dragover', (e) => e.preventDefault());
  importView.addEventListener('drop', (e) => {
    e.preventDefault();
    const name = (e.dataTransfer.files[0] || {}).name || '';
    if (name && !/\.(zip|7z|rar)$/i.test(name)) {
      infoDialog({ title: '无法导入', tone: 'warning', text: '只支持 ZIP、7z 和 RAR。' });
      return;
    }
    runImport();
  });

  // ---------------------------------------------------------------- 状态栏事件
  if (window.events) {
    window.events.bindStatus({
      scanning(label, pct) { setStatus('scanning', { label: label, pct: pct }); },
      idle() { setStatus('idle'); },
    });
  }

  // ---------------------------------------------------------------- 首次引导
  const onboardBtn = $('#onboardStart');
  if (onboardBtn) {
    onboardBtn.addEventListener('click', async () => {
      onboardBtn.disabled = true;
      onboardBtn.textContent = '正在整理…';
      const res = await window.bridge.start_scan();
      if (!res || !res.ok) {
        onboardBtn.disabled = false;
        onboardBtn.textContent = '开始整理';
        await infoDialog({ title: '无法整理', tone: 'danger',
                           text: (res && res.error) || '扫描失败' });
        return;
      }
      runJob(res.job_id,
        null,
        async () => {
          onboardBtn.disabled = false;
          onboardBtn.textContent = '开始整理';
          await reloadMods();
          renderFilters(); renderGrid(); renderInspector();
        },
        async (msg) => {
          onboardBtn.disabled = false;
          onboardBtn.textContent = '开始整理';
          await infoDialog({ title: '整理失败', tone: 'danger', text: msg });
        });
    });
  }

  // ---------------------------------------------------------------- boot
  // 先取真实数据再渲染，避免闪一帧演示内容。
  (async () => {
    setView('library');
    setStatus('idle');

    const ok = await loadFromBridge();
    if (!ok) console.warn('[app] 后端不可用，使用演示数据');
    if (window.bridge && window.bridge.log) {
      window.bridge.log('boot mods=' + MODS.length + ' ok=' + ok);
    }

    // 验证用：URL hash 可指定初始分类（数据就绪后再应用）
    const hash = location.hash || '';
    const m = hash.match(/rail=([a-z]+)/);
    if (m && RAILS[m[1]]) state.rail = m[1];

    renderRail();
    renderFilters();
    renderGrid();
    renderInspector();

    if (window.bridge && window.bridge.log) {
      window.bridge.log('rendered cards='
        + document.querySelectorAll('.mod-card').length);
    }
  })();
})();
