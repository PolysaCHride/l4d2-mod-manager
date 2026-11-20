# -*- coding: utf-8 -*-
"""重写 renderFilters：从真实数据构建分类树。

============================================================
!!  历史脚本：只能用一次，重复执行会重复插入代码  !!
============================================================
renderFilters 已经在 app.js 里了，此脚本完成了它的历史任务。
它用字符串切片定位并替换，第二次跑会在文件里再插一遍 NEW_RENDER。
保留仅供追溯，不要执行。


旧版把 RAILS 的分组和物品名写死成演示数据，
连上真实库后「枪械」只显示 AK-47/M16A2 两个假物品，
真实 23 个枪械模组全被藏起来了。

新版：
- 一级分类固定（角色/特感/武器/地图/其他）
- 二级物品从 MODS 里实时推导
- 「全部X」置顶，「未指定」排第二，其余按数量降序
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "app" / "webui" / "app.js"

NEW_RENDER = r'''  function renderFilters() {
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
        const count = g.items[0].startsWith('全部')
          ? all.filter((m) => m.cat === g.key).length
          : all.filter((m) => m.cat === g.key).length;
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
        const catName = name.slice(2);
        count = pool.filter((m) => m.cat === catName || m.cat === name.slice(0, -0)
          || true).length;
        // 「全部X」= 该分类下的全部
        count = pool.filter((m) => m.cat === catName).length || pool.length;
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
'''


def main():
    s = TARGET.read_text(encoding="utf-8")

    # 找到 renderFilters 的完整范围
    start = s.index("  function renderFilters() {")
    # 用下一节的注释作为结束锚点
    anchor = "  // ---------------------------------------------------------------- render: header"
    if anchor not in s:
        print("FAILED: 找不到 header 锚点")
        sys.exit(1)
    end = s.index(anchor)

    s = s[:start] + NEW_RENDER + "\n" + s[end:]

    # visibleMods 也要支持「未指定物品」
    s = s.replace('''    if (state.filterItem) {
      if (state.filterItem.startsWith('全部')) {
        const cat = state.filterItem.slice(2);
        list = list.filter((m) => m.cat === cat);
      } else {
        list = list.filter((m) => m.item === state.filterItem || m.cat === state.filterItem);
      }
    }''',
'''    if (state.filterItem) {
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
    }''')

    TARGET.write_text(s, encoding="utf-8")
    print("renderFilters 已重写；文件 %d 行" % len(s.splitlines()))


if __name__ == "__main__":
    main()
