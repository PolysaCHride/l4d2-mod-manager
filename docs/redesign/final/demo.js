/* BLACKSITE demo — 交互与数据。
   静态资源来自 ../assets/mods/，逻辑尽量贴近 app/ 的真实行为：
   - 同组互斥：启用一项会停用同物品其它项
   - 游戏运行时禁止写入
   - 导入 / 下载都是「解析 → 勾选 → 执行 → 结果」四段
   所有文案与按钮语义以 states.html 与 03/04 拆解文档为准。 */

(() => {
  'use strict';

  // ---------------------------------------------------------------- data
  const MODS = [
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
  ];

  const COLLECTIONS = {
    c1: { name: '死亡中心 · 重制版', files: ['m18'] },
    c2: { name: '寂静岭 · 雾中街区', files: ['m19'] },
  };

  // FilterPanel 结构与拆解文档一致：分组 → 物品
  const RAILS = {
    all: {
      title: '全部', groups: null, items: null, expandAll: true,
    },
    survivor: {
      title: '角色',
      groups: null,
      items: ['全部角色', 'Ellis', 'Nick', 'Coach'],
    },
    special: {
      title: '特感',
      groups: null,
      items: ['全部特感', 'Hunter', 'Tank'],
    },
    weapon: {
      title: '武器',
      groups: [
        { key: '枪械', items: ['全部枪械', 'AK-47', 'M16A2'] },
        { key: '近战', items: ['全部近战', '消防斧', '大剑'] },
        { key: '医疗品', items: ['全部医疗品', '急救包'] },
        { key: '投掷', items: ['全部投掷', '燃烧瓶'] },
      ],
    },
    map: {
      title: '地图',
      groups: null,
      items: ['全部地图', '死亡中心', '自定义', '黑色狂欢节'],
    },
    other: {
      title: '其他',
      groups: [
        { key: 'UI', items: ['全部 UI'] },
        { key: '音效音乐', items: ['全部音效音乐'] },
        { key: '载具', items: ['全部载具'] },
        { key: '弹药', items: ['全部弹药'] },
        { key: '材质特效', items: ['全部材质特效'] },
        { key: '动作', items: ['全部动作'] },
        { key: '杂项', items: ['全部杂项'] },
        { key: '未分类', items: ['全部未分类'] },
      ],
    },
  };

  // ---------------------------------------------------------------- state
  const state = {
    view: 'library',
    rail: 'survivor',
    filterMode: 'all',        // all | on | off
    filterItem: null,         // 'Ellis' 等；null = 全部
    layout: 'grid',
    sort: 'added',
    query: '',
    selectedId: 'm3',
    gameRunning: false,
    scanning: false,
    dirMissing: false,
    openGroups: new Set(['枪械', '近战', '医疗品', '投掷']),
    toastTimer: null,
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
    if (e.target.classList.contains('scrim')) closeModal(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && $('#modal-root').classList.contains('open')) closeModal(false);
  });

  // ---------------------------------------------------------------- selectors
  function modsInRail(rail) {
    const map = { survivor: ['角色'], special: ['特感'], weapon: ['枪械', '近战', '医疗品', '投掷'], map: ['地图'], other: ['UI', '音效音乐', '载具', '弹药', '材质特效', '动作', '杂项', '未分类'] };
    if (rail === 'all') return MODS.slice();
    const cats = map[rail] || [];
    return MODS.filter((m) => cats.includes(m.cat));
  }

  function visibleMods() {
    let list = modsInRail(state.rail);
    if (state.query) {
      const q = state.query.toLowerCase();
      list = list.filter((m) => (m.name + ' ' + m.alias + ' ' + m.file + ' ' + m.item).toLowerCase().includes(q));
    }
    if (state.filterItem) {
      if (state.filterItem.startsWith('全部')) {
        const cat = state.filterItem.slice(2);
        list = list.filter((m) => m.cat === cat);
      } else {
        list = list.filter((m) => m.item === state.filterItem || m.cat === state.filterItem);
      }
    }
    if (state.filterMode === 'on') list = list.filter((m) => m.enabled);
    if (state.filterMode === 'off') list = list.filter((m) => !m.enabled);
    const sorters = {
      added: (a, b) => a.added - b.added,
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
    const rail = RAILS[state.rail];
    // 「全部」= 每个分类各成一组，全部展开
    if (rail.expandAll) {
      const groups = {};
      modsInRail('all').forEach((m) => {
        (groups[m.cat] = groups[m.cat] || []).push(m);
      });
      rail.groups = Object.keys(groups).map((cat) => ({
        key: cat,
        items: [`全部${cat}`, ...groups[cat].map((m) => m.item).filter((v, i, a) => v && a.indexOf(v) === i)],
      }));
      // 进入「全部」时把所有分组都展开一次
      rail.groups.forEach((g) => state.openGroups.add(g.key));
    }
    const all = modsInRail(state.rail);
    const on = all.filter((m) => m.enabled).length;
    const head = `<div class="filter-head"><h2>${rail.title}</h2><span class="total">${all.length}</span></div>
      <div class="segmented" data-mode-group>
        <button data-mode="all" class="${state.filterMode === 'all' ? 'active' : ''}">全部</button>
        <button data-mode="on" class="${state.filterMode === 'on' ? 'active' : ''}">启用 <span>${on}</span></button>
        <button data-mode="off" class="${state.filterMode === 'off' ? 'active' : ''}">停用 <span>${all.length - on}</span></button>
      </div>`;

    let body = '';
    if (rail.groups) {
      body = '<div class="filter-list">' + rail.groups.map((g) => {
        const open = state.openGroups.has(g.key);
        const count = all.filter((m) => m.item === g.items[1] || m.cat === g.key).length || g.items.length - 1;
        const rows = g.items.map((name) => {
          const active = state.filterItem === name;
          const n = name.startsWith('全部') ? count : all.filter((m) => m.item === name).length;
          return `<button class="filter-row is-nested ${active ? 'active' : ''}" type="button" data-item="${esc(name)}">
            <span class="item-name">${esc(name)}</span><span class="count">${n || ''}</span></button>`;
        }).join('');
        return `<button class="tree-head ${open ? '' : 'is-collapsed'}" type="button" data-group="${esc(g.key)}">
            <svg class="fold-caret" aria-hidden="true"><use href="#i-chevron-down"></use></svg>
            <span>${esc(g.key)}</span><span class="count">${count}</span></button>
          <div class="tree-items" ${open ? '' : 'hidden'}>${rows}</div>`;
      }).join('') + '</div>';
    } else if (rail.items) {
      body = '<div class="filter-list">' + rail.items.map((name) => {
        const active = state.filterItem === name || (!state.filterItem && name.startsWith('全部'));
        const count = name.startsWith('全部')
          ? all.length
          : all.filter((m) => m.item === name).length;
        const hasOn = !name.startsWith('全部') && all.some((m) => m.item === name && m.enabled);
        return `<button class="filter-row ${active ? 'active' : ''}" type="button" data-item="${esc(name)}">
          <span class="item-name">${esc(name)}</span><span class="count">${count || ''}</span>
          ${hasOn ? '<span class="active-mark"></span>' : ''}</button>`;
      }).join('') + '</div>';
    }

    const conflict = MODS.some((m) => m.enabled && sameGroup(m).some((x) => x.enabled));
    const conflictLine = conflict
      ? `<div class="conflict-line">${icon('alert')}<span><b>1</b> 组待处理</span>
         <button type="button" data-conflict="1">查看</button></div>`
      : '';

    $('#filters').innerHTML = head + body + conflictLine;

    $$('[data-mode]').forEach((b) => b.addEventListener('click', () => {
      state.filterMode = b.dataset.mode;
      const pool = visibleMods();
      if (!pool.some((m) => m.id === state.selectedId) && pool.length) state.selectedId = pool[0].id;
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
      if (!pool.some((m) => m.id === state.selectedId) && pool.length) state.selectedId = pool[0].id;
      renderFilters(); renderHeader(); renderGrid(); renderInspector();
    }));
    const c = $('[data-conflict]');
    if (c) c.addEventListener('click', showConflictDialog);
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

    if (!list.length) {
      grid.innerHTML = `<div class="empty"><strong>这里还没有模组</strong>切换到别的分类，或导入一个新模组。</div>`;
      renderHeader();
      return;
    }

    grid.innerHTML = list.map((m) => {
      const shown = m.alias || m.name;
      return `<article class="mod-card ${m.id === state.selectedId ? 'selected' : ''} ${m.enabled ? 'is-on' : ''}" data-mod="${m.id}" tabindex="0" title="${m.enabled ? '双击停用' : '双击启用'}">
        <div class="mod-thumb">
          <img src="../assets/mods/${m.img}" alt="${esc(shown)}">
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
      ['入库时间', `2026-11-${String(Math.max(1, 19 - m.added)).padStart(2, '0')}`],
      ...(m.ws ? [['工坊', m.ws]] : []),
    ];

    const groupRows = [
      `<div class="group-mini active"><img src="../assets/mods/${m.img}" alt=""><span>${esc(shown)}</span>${icon('check')}</div>`,
      ...group.slice(0, 3).map((x) => `<div class="group-mini" data-pick="${x.id}"><img src="../assets/mods/${x.img}" alt=""><span>${esc(x.alias || x.name)}</span></div>`),
    ].join('');

    $('#inspector').innerHTML = `
      <div class="inspector-head">
        <div class="title-block">
          <h2 class="detail-title">${esc(shown)}</h2>
          ${m.alias ? `<p class="detail-sub">${esc(m.name)}</p>` : ''}
        </div>
        <button class="close" type="button" id="insClose" aria-label="关闭详情">${icon('x')}</button>
      </div>

      <div class="preview"><img src="../assets/mods/${m.img}" alt="${esc(shown)}"></div>

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
      m.alias = value.trim();
      renderGrid(); renderInspector();
      toast(m.alias ? '别名已保存' : '已恢复原名');
    });

    $('#insFolder').addEventListener('click', () => toast('已在资源管理器中显示'));
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
    $$('[data-more]').forEach((b) => b.addEventListener('click', async () => {
      $('#insMoreMenu').hidden = true;
      if (b.dataset.more === 'category') {
        await infoDialog({ title: '修改分类', text: '实际实现会打开分类选择对话框，演示页暂不展开。' });
      } else {
        await infoDialog({ title: '归入合集', text: '实际实现会解析合集链接或选择已有合集。' });
      }
    }));

    $$('[data-pick]').forEach((b) => b.addEventListener('click', () => {
      state.selectedId = b.dataset.pick;
      renderGrid(); renderInspector();
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
      const i = MODS.findIndex((x) => x.id === m.id);
      if (i >= 0) MODS.splice(i, 1);
      state.selectedId = null;
      renderFilters(); renderGrid(); renderInspector();
      toast('已移到回收站');
    });
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
    if (m.enabled) {
      m.enabled = false;
      repaintAfterToggle();
      toast('已停用');
      return;
    }

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
      siblings.forEach((x) => { x.enabled = false; });
    }
    m.enabled = true;
    repaintAfterToggle();
    toast('已启用');
  }

  async function showConflictDialog() {
    const groups = {};
    MODS.forEach((m) => {
      if (!m.enabled) return;
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
      text: '每组只保留最新启用的一项，其余自动停用。',
      rows: conflicts.flatMap(([k, list]) => list.map((m, i) => ({
        name: `${k} · ${m.alias || m.name}`, tag: i === 0 ? '保留' : '将停用', tone: i === 0 ? 'ok' : 'warn',
      }))),
      confirm: '自动处理',
    });
    if (!ok) return;
    conflicts.forEach(([, list]) => list.slice(1).forEach((m) => { m.enabled = false; }));
    renderGrid(); renderInspector(); renderFilters();
    toast('已处理 1 组');
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
    if (state.scanning) return;
    state.scanning = true;
    $('#tidyBtn').disabled = true;
    const ok = await confirmDialog({
      title: '整理现有模组',
      tone: 'question',
      text: '将扫描 addons 与 workshop：登记未入库模组、把 workshop 内容移入顶层、同组外观只保留一个启用项。',
      rows: [
        { name: '登记未入库', tag: '预计 12 个' },
        { name: 'workshop 迁移', tag: '预计 8 个' },
        { name: '外观互斥', tag: '预计停用 5 个', tone: 'warn' },
      ],
      confirm: '开始整理',
    });
    if (!ok) {
      state.scanning = false;
      $('#tidyBtn').disabled = false;
      return;
    }

    setStatus('scanning', { label: '扫描中 0/22', pct: 2 });
    let done = 0;
    await new Promise((resolve) => {
      const timer = setInterval(() => {
        done += 1;
        const pct = Math.round((done / 22) * 100);
        setStatus('scanning', { label: `扫描中 ${done}/22`, pct });
        if (done >= 22) { clearInterval(timer); resolve(); }
      }, 90);
    });
    setStatus('idle');
    state.scanning = false;
    $('#tidyBtn').disabled = false;
    await infoDialog({
      title: '整理完成',
      text: '补记顶层 2 个 · 子目录移入 1 个 · workshop 迁移 3 个 · 自动停用 2 个。',
    });
  }

  // ---------------------------------------------------------------- import flow
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
        <img src="../assets/mods/${c.img}" alt="">
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

    // pick a fake archive
    const candidates = [
      { name: 'VRC lime 甜点屋 打歌服', meta: '角色 / Ellis · 93.0 MB', img: 'mod2.webp', dup: false, selected: true },
      { name: '【原神】菲谢尔 极夜真梦', meta: '角色 / Ellis · 38.3 MB', img: 'mod5.webp', dup: false, selected: true },
      { name: 'VRC プラム Plum replace ellis', meta: '角色 / Ellis · 34.1 MB', img: 'mod3.webp', dup: true, selected: false },
    ];
    importFlow.running = true;
    importFlow.candidates = [];

    $('#importPanel').hidden = true;
    $('#importActions').hidden = true;
    $('#dropZone').hidden = true;
    setImportProgress({ title: '正在解析', label: '正在解压 VRC_bundle.7z', meta: '0%', pct: 0 });

    await new Promise((resolve) => {
      let pct = 0;
      const timer = setInterval(() => {
        pct = Math.min(100, pct + 9);
        setImportProgress({
          title: '正在解析',
          label: pct < 60 ? '正在解压 VRC_bundle.7z' : '正在读取 VPK',
          meta: pct + '%',
          pct,
        });
        if (pct >= 100) { clearInterval(timer); resolve(); }
      }, 80);
    });

    $('#importProgress').hidden = true;
    $('#dropZone').hidden = false;
    importFlow.candidates = candidates;
    importFlow.running = false;
    $('#importPanel').hidden = false;
    renderImportCandidates();
  }

  async function commitImport() {
    const picked = importFlow.candidates.filter((c) => c.selected && !c.dup);
    if (!picked.length) return;

    if (state.gameRunning) {
      await infoDialog({ title: '游戏运行中', tone: 'warning', text: '游戏运行时无法写入模组库，请先退出游戏。' });
      return;
    }

    $('#importPanel').hidden = true;
    $('#importActions').hidden = true;
    $('#dropZone').hidden = true;
    setImportProgress({ title: `正在导入 ${picked.length} 个模组`, label: picked[0].name, meta: `0 / ${picked.length}`, pct: 0 });

    for (let i = 0; i < picked.length; i++) {
      await new Promise((r) => setTimeout(r, 260));
      setImportProgress({
        title: `正在导入 ${picked.length} 个模组`,
        label: picked[i].name,
        meta: `${i + 1} / ${picked.length}`,
        pct: Math.round(((i + 1) / picked.length) * 100),
      });
    }

    $('#importProgress').hidden = true;
    $('#dropZone').hidden = false;
    await infoDialog({
      title: '导入完成',
      text: `已加入模组库 ${picked.length} 个${importFlow.candidates.some((c) => c.dup) ? '，另有 1 个重复项已跳过' : ''}。`,
      rows: picked.map((c) => ({ name: c.name, tag: '已写入', tone: 'ok' })),
    });

    picked.forEach((c) => {
      if (!MODS.some((m) => m.name === c.name)) {
        MODS.push({
          id: 'n' + Date.now() + Math.random().toString(16).slice(2, 6),
          name: c.name, alias: '', cat: '角色', item: 'Ellis',
          size: parseFloat(c.meta.split('·')[1]) || 50, img: c.img,
          enabled: true, added: 0, file: 'new_' + Math.random().toString(16).slice(2, 8) + '.vpk', ws: '',
        });
      }
    });
    importFlow.candidates = [];
    $('#importPanel').hidden = true;
    renderFilters(); renderGrid(); renderInspector();
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
        <img src="../assets/mods/${it.img}" alt="">
        <span class="task-copy"><b>${esc(it.name)}</b><small>${esc(it.meta)}</small></span>
        ${it.dup ? '<span class="task-tag">已在库</span>' : ''}
      </label>`).join('');
    const selectable = dlFlow.items.filter((i) => !i.dup);
    const picked = selectable.filter((i) => i.selected).length;
    $('#downloadPanelTitle').textContent = dlFlow.collection ? `已解析 · ${dlFlow.collection}` : '已解析';
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
      await infoDialog({ title: '无法解析', tone: 'warning', text: '请先粘贴创意工坊链接或物品 ID。' });
      return;
    }
    if (!/^\d{6,}$/.test(raw) && !/steamcommunity\.com/.test(raw)) {
      await infoDialog({ title: '链接无效', tone: 'warning', text: '没有识别到有效的创意工坊物品 ID。' });
      return;
    }

    $('#downloadPanel').hidden = true;
    $('#downloadActions').hidden = true;
    $('#downloadRunning').hidden = false;
    $('#dlRunTitle').textContent = '正在解析链接';
    $('#dlRunMeta').textContent = '';
    $('#dlLog').innerHTML = '';
    $('#dlRunBar').style.width = '0%';
    $('#dlRunLabel').textContent = '读取工坊物品详情';
    log('开始解析：' + raw);

    await new Promise((resolve) => {
      let pct = 0;
      const timer = setInterval(() => {
        pct = Math.min(100, pct + 12);
        $('#dlRunBar').style.width = pct + '%';
        if (pct === 24) log('读取工坊物品详情…');
        if (pct === 60) log('识别到合集结构，正在展开部件');
        if (pct >= 100) { clearInterval(timer); resolve(); }
      }, 90);
    });

    $('#dlRunBar').style.width = '0%';
    $('#downloadRunning').hidden = true;
    $('#downloadPanel').hidden = false;

    const isCollection = raw.includes('collection') || raw.endsWith('3671');
    dlFlow.collection = isCollection ? '《Ellis 夏日合集》' : null;
    dlFlow.items = [
      { name: 'VRC lime 甜点屋 打歌服', meta: '角色 / Ellis · 93.0 MB', img: 'mod2.webp', size: 93, dup: false, selected: true },
      { name: '[Gakuen IDOLM@STER] Fujita', meta: '角色 / Ellis · 146.4 MB', img: 'mod4.webp', size: 146.4, dup: false, selected: true },
      { name: 'VRC プラム Plum replace ellis', meta: '角色 / Ellis · 34.1 MB', img: 'mod3.webp', size: 34.1, dup: true, selected: false },
    ];
    renderDownloadItems();
  }

  async function startDownload() {
    const picked = dlFlow.items.filter((i) => i.selected && !i.dup);
    if (!picked.length) return;
    if (state.gameRunning) {
      await infoDialog({ title: '游戏运行中', tone: 'warning', text: '请先关闭游戏，再下载导入模组。' });
      return;
    }

    $('#downloadPanel').hidden = true;
    $('#downloadActions').hidden = true;
    $('#downloadRunning').hidden = false;
    $('#dlRunTitle').textContent = `正在下载 ${picked.length} 个模组`;
    $('#dlRunMeta').textContent = '';
    $('#dlLog').innerHTML = '';
    $('#dlRunLabel').textContent = picked[0].name;

    const failed = [];
    for (let i = 0; i < picked.length; i++) {
      const it = picked[i];
      $('#dlRunLabel').textContent = it.name;
      $('#dlRunMeta').textContent = `第 ${i + 1} / ${picked.length} 项`;
      log(`开始处理 ${i + 1}/${picked.length}：${it.name}`);

      await new Promise((resolve) => {
        let pct = 0;
        const timer = setInterval(() => {
          pct += 20;
          $('#dlRunBar').style.width = pct + '%';
          if (pct === 20) log('正在获取下载地址');
          if (pct === 60) log('file_url 直连可用，开始写入 addons');
          if (pct >= 100) { clearInterval(timer); resolve(); }
        }, 120);
      });
      log(`完成 ${it.name}`);
      $('#dlRunBar').style.width = '0%';
    }

    $('#downloadRunning').hidden = true;
    await infoDialog({
      title: '下载完成',
      text: `已导入 ${picked.length} 个模组${dlFlow.items.some((i) => i.dup) ? '，跳过 1 个已在库的条目' : ''}。`,
      rows: picked.map((i) => ({ name: i.name, tag: '已启用', tone: 'ok' })),
    });
    renderDownloadItems();
    $('#downloadPanel').hidden = false;
    $('#downloadActions').hidden = false;
  }

  // ---------------------------------------------------------------- settings
  function renderSettings() {
    $('#settings').innerHTML = `
      <div class="settings-group">
        <h3>游戏</h3>
        <div class="settings-row">
          <div class="settings-copy"><b>L4D2 目录</b><small class="path">E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2</small></div>
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
          <div class="settings-copy"><b>检查更新</b><small>当前版本 v1.2.1</small></div>
          <button class="btn" type="button" data-setting="update">检查更新</button>
        </div>
      </div>

      <div class="settings-group">
        <h3>关于</h3>
        <div class="settings-row">
          <div class="settings-copy"><b>L4D2 Mod Manager</b><small>v1.2.1 · MIT License</small></div>
          <button class="btn" type="button" data-setting="repo">查看仓库</button>
        </div>
      </div>`;

    $$('[data-setting]').forEach((b) => b.addEventListener('click', async () => {
      const kind = b.dataset.setting;
      if (kind === 'game') {
        state.gameRunning = !state.gameRunning;
        $('#gameStatus').classList.toggle('running', state.gameRunning);
        $('#gameStatus').title = state.gameRunning ? '游戏运行中' : '游戏未运行';
        $('#launchBtn').disabled = state.gameRunning;
        renderSettings();
        toast(state.gameRunning ? '已模拟游戏运行中' : '已模拟游戏未运行');
        return;
      }
      if (kind === 'clean') {
        const ok = await confirmDialog({
          title: '清理缓存',
          tone: 'question',
          text: '将删除缩略图缓存与临时解压目录，不影响模组文件。',
          confirm: '清理',
        });
        if (ok) toast('已释放 42.6 MB');
        return;
      }
      const messages = {
        detect: ['自动检测', '未能自动定位游戏目录，请手动选择。'],
        browse: ['更改目录', '实际实现会打开文件夹选择对话框。'],
        saveProxy: ['网络', '代理设置已保存。'],
        update: ['检查更新', '当前已是最新版本 v1.2.1。'],
        repo: ['关于', '实际实现会打开项目仓库页面。'],
      };
      const [title, text] = messages[kind] || ['提示', ''];
      await infoDialog({ title, text });
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
      buttons: undefined,
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

  $$('[data-caption]').forEach((b) => b.addEventListener('click', async () => {
    const kind = b.dataset.caption;
    if (kind === 'close') {
      const ok = await confirmDialog({ title: '关闭窗口', tone: 'question', text: '确定要退出模组管理器吗？', confirm: '退出' });
      if (ok) toast('演示环境不会真的退出');
      return;
    }
    toast(kind === 'min' ? '演示环境不支持最小化' : '演示环境不支持最大化');
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

  // ---------------------------------------------------------------- boot
  $('#statusPath').textContent = 'E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2\\left4dead2\\addons';
  renderRail();
  renderFilters();
  renderGrid();
  renderInspector();
  setView('library');
  setStatus('idle');
})();
