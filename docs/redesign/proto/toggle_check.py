# -*- coding: utf-8 -*-
"""交互验证：双击启停是否真的写入了 addonlist.txt。

用最安全的方式验证——先记下原状态，toggle 两次回到原状。
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

TEST_JS = r"""
window.__t = null;
(async () => {
  const out = {steps: []};
  try {
    // 找一个当前未启用的角色模组
    const all = await window.bridge.bootstrap();
    const poolNonConflict = all.mods.filter(m =>
      m.category === '角色' && !m.enabled && !m.item);   // item 为空 = 不参与互斥
    const pool = poolNonConflict.length ? poolNonConflict
      : all.mods.filter(m => m.category === '角色' && !m.enabled);
    if (!pool.length) { out.error = '没有可用的未启用角色模组'; window.__t = JSON.stringify(out); return; }
    const target = pool[0];
    out.file = target.file;
    out.title = target.title;
    out.nonConflict = !target.item;

    // 先读「开互斥」的开关状态，验证时把它关掉 —— 否则启用 A 会顺带停用同组 B，
    // 再停用 A 也**不会**把 B 放回来，两轮 toggle 就不是「回到原状」了。
    // （2026-11-22 互斥回归后新增的坑：这个探针原来假设「toggle 两次等于没动」。）
    const before = await window.bridge.get_mutex();
    const wasMutex = !!(before && before.mutex);
    if (wasMutex) await window.bridge.set_mutex(false);

    let r1 = null, r2 = null;
    try {
      // 第一次：启用
      r1 = await window.bridge.toggle_mod(target.file, true);
      out.steps.push({step: 'enable', ok: r1.ok, enabled: r1.enabled,
                      siblings: (r1.disabled_siblings || []).length});

      const b2 = await window.bridge.bootstrap();
      const m2 = b2.mods.find(m => m.file === target.file);
      out.enabledAfter = m2 ? m2.enabled : null;

      // 第二次：停用，恢复原状
      r2 = await window.bridge.toggle_mod(target.file, false);
      out.steps.push({step: 'disable', ok: r2.ok, enabled: r2.enabled});
    } finally {
      // 无论成败都把开关恢复原值 —— 探针绝不能改用户的设置
      if (wasMutex) await window.bridge.set_mutex(true);
    }

    const b3 = await window.bridge.bootstrap();
    const m3 = b3.mods.find(m => m.file === target.file);
    out.restored = m3 ? !m3.enabled : null;
    out.mutexRestored = !!(await window.bridge.get_mutex()).mutex === wasMutex;

    out.pass = out.enabledAfter === true && out.restored === true && out.mutexRestored;
  } catch (e) {
    out.error = String(e);
  }
  window.__t = JSON.stringify(out);
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

    try:
        win.evaluate_js(TEST_JS)
    except Exception as exc:
        print("[T] kick failed:", exc, flush=True)

    result = None
    for _ in range(80):
        time.sleep(0.4)
        try:
            result = win.evaluate_js("window.__t")
        except Exception:
            continue
        if result:
            break

    print("[T] result:", result, flush=True)
    time.sleep(0.5)
    win.destroy()


def main():
    api = Api()
    url = "file:///" + os.path.join(
        _ROOT, "app", "webui", "index.html").replace("\\", "/")
    win = webview.create_window("toggle-test", url=url, js_api=api,
                                width=1440, height=900,
                                background_color="#08090b")
    api.attach_window(win)
    threading.Thread(target=run, args=(win,), daemon=True).start()
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
