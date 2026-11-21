# -*- coding: utf-8 -*-
"""合集展示（A-1）的端到端检查：真实库 + 真实桥接 + 真实界面。

用法：
    .venv/Scripts/python.exe -X utf8 docs/redesign/proto/coll_check.py

验的是「详情 → 更多 → 合集」这一块，因为它的数据来源有两处容易出错：
  1. 归属要从 collections 表反查（记录上的 collection 字段会被重扫抹掉）
  2. 没有合集的模组不该渲染这个块（200 条里只有 6 条有归属）

断言失败会打印原因并返回退出码 1。
"""
import logging
import os
import sys
import threading
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import webview  # noqa: E402

from app.shell.api import Api  # noqa: E402


class _Quiet(logging.Filter):
    NOISE = ("AccessibilityObject", "AllowExternalDrop", "CanGoBack",
             "CanGoForward", "recursion depth", "E_NOINTERFACE",
             "CoreWebView2")

    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        return not any(n in msg for n in self.NOISE)


logging.getLogger("pywebview").addFilter(_Quiet())

PROBE_JS = r"""
window.__coll = null;
(async () => {
  const out = { errors: [] };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const ok = (cond, msg) => { if (!cond) out.errors.push(msg); };
  try {
    const b = await window.bridge.bootstrap();
    ok(!!b.ok, 'bootstrap 失败');
    out.mode = window.bridge.isMock() ? 'mock' : 'live';

    const cols = b.collections || {};
    out.collections = Object.keys(cols);
    out.modsWithColl = b.mods.filter((m) => m.collection).length;
    ok(out.modsWithColl > 0,
       '没有任何模组带 collection —— 归属反查没生效（见 api._collection_index）');

    // 每个合集里至少有一个成员能在 mods 里找到
    for (const cid of Object.keys(cols)) {
      const files = cols[cid].files || [];
      const hit = b.mods.filter((m) => files.indexOf(m.file) >= 0);
      ok(hit.length > 0, '合集 ' + cid + ' 的成员在模组列表里一个都找不到');
      hit.forEach((m) => ok(m.collection === cid,
        m.file + ' 属于 ' + cid + '，但前端拿到 ' + JSON.stringify(m.collection)));
    }

    // 挑**部件最多**的合集来测（真实库里 The Bloody Moors 有 5 个部件，
    // 且标题完全相同 —— 只有这组才能验到「用体积区分部件」）
    const groups = {};
    b.mods.forEach((m) => {
      if (!m.collection) return;
      (groups[m.collection] = groups[m.collection] || []).push(m);
    });
    const bestId = Object.keys(groups).sort((x, y) => groups[y].length - groups[x].length)[0];
    const withColl = bestId ? groups[bestId][0] : null;
    out.bestCollection = bestId;
    if (!withColl) { out.errors.push('没有可测的合集模组'); window.__coll = JSON.stringify(out); return; }

    const rail = document.querySelector('[data-rail="' + (withColl.category === '地图' ? 'map' : 'all') + '"]');
    if (rail) rail.click();
    await sleep(700);

    // 卡片上的合集标签：成员带 (x/N)，非成员不带
    const tagOf = (c) => (c.querySelector('.mod-coll') || {}).textContent || '';
    const cards = [...document.querySelectorAll('.mod-card')];
    out.cards = cards.length;
    const memberFiles = [];
    Object.keys(cols).forEach((cid) => (cols[cid].files || []).forEach((f) => memberFiles.push(f)));
    let tagged = 0, untagged = 0;
    cards.forEach((c) => {
      const f = c.dataset.mod || '';
      const t = tagOf(c);
      if (memberFiles.indexOf(f) >= 0) {
        tagged += 1;
        ok(t.length > 0, '合集成员卡片没有标签：' + f);
        const expect = (() => {
          for (const cid of Object.keys(cols)) {
            const i = (cols[cid].files || []).indexOf(f);
            if (i >= 0) return cols[cid].name + ' (' + (i + 1) + '/' + cols[cid].files.length + ')';
          }
          return null;
        })();
        ok(t === expect, '标签不对：' + f + ' 期望 ' + JSON.stringify(expect) + ' 实际 ' + JSON.stringify(t));
      } else {
        untagged += 1;
        ok(t === '', '非合集成员不该有标签：' + f + ' → ' + JSON.stringify(t));
      }
    });
    out.tagged = tagged;
    out.untagged = untagged;
    ok(tagged > 0, '一张带标签的卡片都没有');

    // 点标签本身也要能选中卡片（新元素不能吞点击）
    const oneTag = [...document.querySelectorAll('.mod-card')]
      .map((c) => c.querySelector('.mod-coll')).find(Boolean);
    if (oneTag) {
      oneTag.click();
      await sleep(500);
      out.tagClickSelects = !!document.querySelector('.mod-card.selected');
      ok(out.tagClickSelects, '点合集标签没有选中卡片（吞了点击）');
    }


    const card = [...document.querySelectorAll('.mod-card')]
      .find((c) => (c.dataset.mod || '') === withColl.file);
    ok(!!card, '网格里找不到卡片：' + withColl.file);
    if (card) card.click();
    await sleep(800);

    // 「⋯ 更多操作」已隐藏（留给将来的功能入口，DOM 保留）
    const moreWrap = document.querySelector('[data-reserved-entry="insMore"]');
    out.moreHidden = !moreWrap || moreWrap.hidden
      || getComputedStyle(moreWrap).display === 'none';
    ok(out.moreHidden, '详情栏的三点「更多操作」没有隐藏');

    const det = document.querySelector('.ins-more');
    ok(!!det, '有合集归属，但详情里没有「更多」块');
    if (det) {
      out.summary = (det.querySelector('summary') || {}).textContent || '';
      out.title = (det.querySelector('.coll-title') || {}).textContent || '';
      out.parts = [...det.querySelectorAll('.coll-part')].length;
      out.current = det.querySelectorAll('.coll-part.cur').length;
      const expect = (cols[withColl.collection] || {}).files || [];
      ok(out.parts === expect.length,
         '部件数 ' + out.parts + ' ≠ collections 里的 ' + expect.length);
      ok(out.current === 1, '当前项高亮数应为 1，实际 ' + out.current);

      // 同图部件标题一模一样，体积是唯一区分字段 —— 每行都得有
      const sizes = [...det.querySelectorAll('.coll-part')]
        .map((p) => ((p.querySelector('.coll-part-size') || {}).textContent || '').trim());
      const inLib = [...det.querySelectorAll('.coll-part')]
        .filter((p) => p.dataset.part).length;
      ok(sizes.filter(Boolean).length === inLib,
         '有 ' + inLib + ' 个部件在库里，但只有 ' + sizes.filter(Boolean).length + ' 行显示了体积');
      out.sizes = sizes;
      // 折叠标题只剩「更多」——摘要文字被砍掉了（信息在展开后的「合集 N 个部件」行）
      ok(out.summary.trim() === '更多', '折叠标题应只有「更多」：' + out.summary);

      // 展开状态要能跨重渲染保留。
      // ⚠️ 这里**不能**去点启用开关：那会真写 addonlist.txt。
      // 改用「选别的卡片再选回来」触发 renderInspector。
      det.open = true;
      await sleep(250);
      const others = [...document.querySelectorAll('.mod-card')]
        .filter((c) => (c.dataset.mod || '') !== withColl.file);
      if (others.length) {
        others[0].click();
        await sleep(600);
        card.click();
        await sleep(600);
      }
      out.staysOpen = !!document.querySelector('.ins-more[open]');
      ok(out.staysOpen, '重渲染后「更多」被收起来了');
    }

    // ── 子分类（合集统一为子分类，§5）──
    // 会真的写几次 library.json（改子分类 → 新建 → 归回 → 清空），最后还原。
    const collName = (cols[withColl.collection] || {}).name;
    const subBtn = document.querySelector('#insSub');
    out.hasSubRow = !!subBtn;
    ok(!!subBtn, '「更多」里没有子分类行');
    if (subBtn) {
      ok(subBtn.textContent.trim() === collName,
         '子分类应显示合集名，实际 ' + JSON.stringify(subBtn.textContent.trim()));

      const openPicker = async () => {
        document.querySelector('#insSub').click();
        await sleep(500);
        const catInput = [...document.querySelectorAll('#modal-host input[name="dlgChoice"]')]
          .find((i) => i.value === withColl.category);
        ok(!!catInput, '分类对话框里没有当前分类选项：' + withColl.category);
        if (catInput) catInput.click();
        const next1 = [...document.querySelectorAll('#modal-host [data-btn]')]
          .find((b) => b.dataset.btn === '1');
        next1.click();
        await sleep(500);
        return document.querySelector('#subList');
      };
      const savePicker = async () => {
        const btn = [...document.querySelectorAll('#modal-host [data-btn]')]
          .find((b) => b.dataset.btn === '1');
        btn.click();
        await sleep(1000);
      };

      const list = await openPicker();
      ok(!!list, '选择器里没有子分类列表');

      // 「新建」是列表里的一行，点开才出现输入框
      ok(!document.querySelector('#dlgInput'), '输入框不该一开始就出现（点「新建」才出现）');
      const create = list.querySelector('#subCreate');
      ok(!!create, '列表里没有「新建子分类」行');
      ok(!create.classList.contains('is-muted') && create.classList.contains('is-create'),
         '「新建」行没有和其它行区分开');
      ok(list.firstElementChild === create,
         '「新建」必须是第一行（否则要滚动才找得到）');

      // 列表行 = 现有子分类（+ 当前有值时的「不细分」），按名称排序
      const rows = [...list.querySelectorAll('.sub-item[data-sub]')];
      out.subOptions = rows.length;
      ok(rows.length > 0, '列表是空的（该分类下明明有子分类）');
      const names = rows.map((r) => r.dataset.sub).filter(Boolean);
      out.subSorted = JSON.stringify(names)
        === JSON.stringify(names.slice().sort((a, b) => a.localeCompare(b, 'zh')));
      ok(out.subSorted, '子分类没有按名称排序');
      out.hasClearRow = !!list.querySelector('.sub-item.is-muted');
      ok(out.hasClearRow, '当前有子分类时应该有一条「不细分」');

      // 可滚动
      const cs = getComputedStyle(list);
      out.subScrollable = (cs.overflowY === 'auto' || cs.overflowY === 'scroll');
      ok(out.subScrollable, '列表不是可滚动的：overflowY=' + cs.overflowY);
      ok(list.scrollHeight > list.clientHeight,
         '列表内容没超过高度，滚动验证不了（' + list.scrollHeight + ' vs ' + list.clientHeight + '）');

      // 点「新建」→ 输入框出现在列表里同一位置
      create.click();
      await sleep(250);
      const input = document.querySelector('#dlgInput');
      ok(!!input, '点「新建」后没有出现输入框');
      ok(input.parentElement === list, '输入框没有放进列表里（应该和已有子分类放一起）');
      ok(!document.querySelector('#subCreate'), '换出输入框后「新建」行应该消失');
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, '沼泽测试');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      await sleep(1200);

      // 卡片标签变成用户值、且不带 (x/x)；「更多」里的子分类同步
      out.tagAfterEdit = (document.querySelector('.mod-card.selected .mod-coll') || {}).textContent || '';
      ok(out.tagAfterEdit === '沼泽测试',
         '新建子分类后卡片标签不是用户值：' + JSON.stringify(out.tagAfterEdit));
      out.subAfterEdit = (document.querySelector('#insSub') || {}).textContent || '';
      ok(out.subAfterEdit === '沼泽测试',
         '「更多」里的子分类没同步：' + JSON.stringify(out.subAfterEdit));

      // 归回：重开选择器 → 点合集名那一行 → 保存
      await openPicker();
      const back = [...document.querySelectorAll('#subList .sub-item[data-sub]')]
        .find((r) => r.dataset.sub === collName);
      ok(!!back, '列表里找不到合集名那一行：' + collName);
      if (back) back.click();
      await sleep(150);
      ok(back.classList.contains('active'), '选中行没有高亮');
      await savePicker();
      const b4 = await window.bridge.bootstrap();
      const m4 = b4.mods.find((x) => x.file === withColl.file);
      out.itemAfterRevert = m4 ? m4.item : null;
      ok(out.itemAfterRevert === collName,
         '归回后 item 不是合集名：' + JSON.stringify(out.itemAfterRevert));
      const tagBack = (document.querySelector('.mod-card.selected .mod-coll') || {}).textContent || '';
      out.tagAfterRevert = tagBack;
      ok(/\(\d+\/\d+\)$/.test(tagBack), '归回后卡片标签没有恢复 (x/x)：' + JSON.stringify(tagBack));

      // 「不细分」= 清空子分类
      await openPicker();
      const clearRow = document.querySelector('#subList .sub-item.is-muted');
      ok(!!clearRow, '找不到「不细分」行');
      if (clearRow) clearRow.click();
      await sleep(150);
      await savePicker();
      const b6 = await window.bridge.bootstrap();
      const m6 = b6.mods.find((x) => x.file === withColl.file);
      out.itemAfterClear = m6 ? m6.item : null;
      ok(out.itemAfterClear === '', '「不细分」没有把 item 清空：' + JSON.stringify(out.itemAfterClear));
      // item 清空了，但这个模组属于合集 → 显示层按合集名回落（§5.3）。
      out.subAfterClear = (document.querySelector('#insSub') || {}).textContent || '';
      ok(out.subAfterClear === collName,
         '清空后显示应回落到合集名：' + JSON.stringify(out.subAfterClear));

      // 「用户新建的子分类」在最后一个模组被移走后必须自动消失，
      // 而管理器自带的（The Bloody Moors 这些）不受影响。
      await sleep(400);
      const treeNames = [...document.querySelectorAll('.filter-row .item-name')]
        .map((e) => e.textContent);
      out.autoCleared = treeNames.indexOf('沼泽测试') < 0;
      ok(out.autoCleared, '新建的子分类在没模组之后仍然留在树上：沼泽测试');
      out.builtinKept = ['Divine Cybermancy', 'The Bloody Moors']
        .every((n) => treeNames.indexOf(n) >= 0);
      ok(out.builtinKept, '管理器自带的子分类被误删了');

      // 树的子分类按名称排序（「全部X」在第一、「未指定」紧随其后）
      const plain = treeNames.filter((n) => !n.startsWith('全部') && n !== '未指定');
      out.treeSorted = JSON.stringify(plain)
        === JSON.stringify(plain.slice().sort((a, b) => a.localeCompare(b, 'zh')));
      ok(out.treeSorted, '树的子分类没有按名称排序');

      // 收尾：清掉 pinned / auto_*，把记录还原成采样前状态
      await window.bridge.restore_auto_category(withColl.file);
      const b5 = await window.bridge.bootstrap();
      const m5 = b5.mods.find((x) => x.file === withColl.file);
      out.pinnedAfterCleanup = m5 ? !!m5.pinned : null;
      ok(!out.pinnedAfterCleanup, '收尾没把 pinned 清掉');
    }

    // ── 特感：没有模组的子分类也要列出来（catalog 补全）──
    // 真实库里特感只有 Tank / 普通感染者 两个有模组，但 9 个都要在树上。
    const railSpecial = document.querySelector('[data-rail="special"]');
    if (railSpecial) {
      railSpecial.click();
      await sleep(900);
      const rows = [...document.querySelectorAll('.filter-row')].map((r) => ({
        name: (r.querySelector('.item-name') || {}).textContent || '',
        count: ((r.querySelector('.count') || {}).textContent || '').trim(),
      }));
      out.specialRows = rows.map((r) => r.name);
      const want = ['Boomer', 'Charger', 'Hunter', 'Jockey', 'Smoker', 'Spitter',
                    'Tank', 'Witch', '普通感染者'];
      const missing = want.filter((n) => out.specialRows.indexOf(n) < 0);
      ok(missing.length === 0, '特感少了子分类：' + missing.join(','));
      ok(out.specialRows.indexOf('全部特感') === 0, '第一行应该是「全部特感」');
      ok(out.specialRows.indexOf('未指定') === 1,
         '第二行应该是「未指定」：' + out.specialRows.join(' / '));

      const empty = rows.find((r) => r.name === 'Hunter');
      out.emptyCount = empty ? empty.count : null;
      ok(empty && empty.count === '', '没模组的子分类不该显示数量，实际 ' + out.emptyCount);

      // 点一个空子分类：应该能选中、网格为空，但不能报错
      const hunter = [...document.querySelectorAll('.filter-row')]
        .find((r) => ((r.querySelector('.item-name') || {}).textContent || '') === 'Hunter');
      if (hunter) hunter.click();
      await sleep(700);
      out.emptyCards = document.querySelectorAll('.mod-card').length;
      ok(out.emptyCards === 0, '空子分类里不该有卡片：' + out.emptyCards);
      ok(!!(document.querySelector('.grid .empty') || document.querySelector('.empty')),
         '空子分类没有空状态提示');
      const allBtn = document.querySelector('.filter-row[data-item="全部特感"]');
      if (allBtn) allBtn.click();
      await sleep(600);
      out.specialCards = document.querySelectorAll('.mod-card').length;
      ok(out.specialCards > 0, '回到「全部特感」后没有卡片');
    }

    // ── 「未指定」在每个一级分类下都有，并且只筛本分类 ──
    // 以前只有单层列表临时追加这一行，分组里根本没有；而且点哪个分类的
    // 「未指定」都会把整个 rail 的空 item 模组混在一起。
    const railOther = document.querySelector('[data-rail="other"]');
    if (railOther) {
      railOther.click();
      await sleep(900);
      // 展开全部分组（有的默认收起）
      [...document.querySelectorAll('[data-group][aria-expanded="false"]')]
        .forEach((h) => h.click());
      await sleep(600);
      const unsetRows = [...document.querySelectorAll('.filter-row')]
        .filter((r) => r.querySelector('.item-name')
          && r.querySelector('.item-name').textContent === '未指定');
      out.unsetCats = [...new Set(unsetRows.map((r) => r.dataset.cat))];
      ok(out.unsetCats.length >= 3,
         '「其他」里多个分类都该有「未指定」，实际 ' + out.unsetCats.join(','));

      // 点「音效音乐 → 未指定」，只应筛出音效音乐里没有子分类的那些
      const target = unsetRows.find((r) => r.dataset.cat === '音效音乐');
      ok(!!target, '音效音乐没有「未指定」行');
      const bb = await window.bridge.bootstrap();
      const expect = bb.mods.filter((m) => m.category === '音效音乐'
        && !m.item && !m.collection).length;
      out.unsetExpect = expect;
      if (target) {
        target.click();
        await sleep(800);
        out.unsetCards = document.querySelectorAll('.mod-card').length;
        ok(out.unsetCards === expect,
           '「未指定」筛出的数量不对：' + out.unsetCards + ' vs ' + expect);
        out.unsetCrumb = (document.querySelector('#crumb') || {}).textContent || '';
        ok(out.unsetCrumb.indexOf('音效音乐') >= 0,
           '面包屑没带分类：' + out.unsetCrumb);
      }
    }

    // 没有合集的模组**也要**有「更多」块，正文写「不属于任何合集」
    const noColl = b.mods.find((m) => !m.collection);
    if (noColl) {
      const rail2 = document.querySelector('[data-rail="all"]');
      if (rail2) rail2.click();
      await sleep(700);
      const c2 = [...document.querySelectorAll('.mod-card')]
        .find((c) => (c.dataset.mod || '') === noColl.file);
      if (c2) {
        c2.click();
        await sleep(700);
        const d2 = document.querySelector('.ins-more');
        out.noCollHasMore = !!d2;
        ok(!!d2, '没有合集的模组没有渲染「更多」块（应该始终渲染）');
        if (d2) {
          out.noCollText = (d2.querySelector('.more-body') || {}).textContent || '';
          ok(out.noCollText.indexOf('不属于任何合集') >= 0,
             '无合集时正文没有「不属于任何合集」：' + out.noCollText.slice(0, 40));
          ok(!d2.querySelector('.more-hint'),
             '无合集时折叠条不该显示「合集 · N 个部件」摘要');
          ok(!d2.querySelector('.coll-parts'), '无合集时不该渲染部件列表');
        }
      }
    }
  } catch (e) {
    out.errors.push('异常：' + String(e && e.stack ? e.stack : e));
  }
  window.__coll = JSON.stringify(out);
})();
"""


def run(win):
    for _ in range(50):
        time.sleep(0.4)
        try:
            if win.evaluate_js("typeof window.bridge !== 'undefined'"):
                break
        except Exception:
            pass
    time.sleep(1.2)
    try:
        win.evaluate_js(PROBE_JS)
    except Exception as exc:
        print("[coll] kick failed:", exc, flush=True)

    raw = None
    for _ in range(80):
        time.sleep(0.4)
        try:
            raw = win.evaluate_js("window.__coll")
        except Exception:
            continue
        if raw:
            break

    if not raw:
        print("[coll] FAIL: 探针没有返回结果", flush=True)
        win.destroy()
        return

    import json
    out = json.loads(raw)
    print("[coll] mode=%s collections=%s 有归属的模组=%d"
          % (out.get("mode"), out.get("collections"), out.get("modsWithColl", 0)),
          flush=True)
    print("[coll] 卡片：共 %s 张，带合集标签 %s 张，不带 %s 张，点标签能选中卡片=%s"
          % (out.get("cards"), out.get("tagged"), out.get("untagged"),
             out.get("tagClickSelects")), flush=True)
    print("[coll] 详情：summary=%r title=%r 部件=%s 当前=%s 展开保留=%s"
          % (out.get("summary"), out.get("title"), out.get("parts"),
             out.get("current"), out.get("staysOpen")), flush=True)
    print("[coll] 子分类：行=%s 新建后=%r 归回后=%r 清空后 item=%r/显示=%r 清 pinned=%s"
          % (out.get("hasSubRow"), out.get("subAfterEdit"), out.get("itemAfterRevert"),
             out.get("itemAfterClear"), out.get("subAfterClear"),
             not out.get("pinnedAfterCleanup")), flush=True)
    print("[coll] 特感（目录补全）：%d 个子分类 %s；空项 Hunter 数量=%r 卡片=%s"
          % (len(out.get("specialRows") or []),
             "、".join(out.get("specialRows") or []),
             out.get("emptyCount"), out.get("emptyCards")), flush=True)
    print("[coll] 未指定：分类=%s 音效音乐应有 %s 筛出 %s 面包屑=%r"
          % (",".join(out.get("unsetCats") or []), out.get("unsetExpect"),
             out.get("unsetCards"), out.get("unsetCrumb")), flush=True)
    print("[coll] 选择器：现有 %s 项 可滚动=%s 已排序=%s 不细分行=%s；树上按名排序=%s；"
          "新建项自动清除=%s；自带项保留=%s；⋯ 已隐藏=%s"
          % (out.get("subOptions"), out.get("subScrollable"), out.get("subSorted"),
             out.get("hasClearRow"), out.get("treeSorted"), out.get("autoCleared"),
             out.get("builtinKept"), out.get("moreHidden")), flush=True)
    errors = out.get("errors") or []
    if errors:
        for e in errors:
            print("[coll] FAIL:", e, flush=True)
        print("[coll] 共 %d 项失败" % len(errors), flush=True)
    else:
        print("[coll] 全部通过", flush=True)
    win.destroy()


def main():
    api = Api()
    url = "file:///" + os.path.join(
        _ROOT, "app", "webui", "index.html").replace("\\", "/")
    win = webview.create_window("coll_check", url=url, js_api=api,
                                width=1440, height=900,
                                background_color="#08090b")
    api.attach_window(win)
    threading.Thread(target=run, args=(win,), daemon=True).start()
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
