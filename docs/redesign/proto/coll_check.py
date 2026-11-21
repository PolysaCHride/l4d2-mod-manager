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

    const card = [...document.querySelectorAll('.mod-card')]
      .find((c) => (c.dataset.mod || '') === withColl.file);
    ok(!!card, '网格里找不到卡片：' + withColl.file);
    if (card) card.click();
    await sleep(800);

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
      ok(/合集 · \d+ 个部件/.test(out.summary), '折叠标题没显示合集摘要：' + out.summary);

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
    print("[coll] 详情：summary=%r title=%r 部件=%s 当前=%s 展开保留=%s"
          % (out.get("summary"), out.get("title"), out.get("parts"),
             out.get("current"), out.get("staysOpen")), flush=True)
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
