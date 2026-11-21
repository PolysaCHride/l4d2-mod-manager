# -*- coding: utf-8 -*-
"""端到端检查：真实数据 + 真实桥接 + 真实界面。

用法：
    .venv/Scripts/python.exe -X utf8 docs/redesign/proto/e2e_check.py
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
window.__e2e = null;
(async () => {
  const out = { mode: window.bridge.isMock() ? 'mock' : 'live' };
  try {
    const b = await window.bridge.bootstrap();
    out.ok = !!b.ok;
    if (!b.ok) {
      out.error = b.error;
    } else {
      out.mods = b.mods.length;
      out.enabled = b.stats.enabled;
      out.version = b.version;
      out.valid = b.paths.valid;
      out.hasThumb = b.mods.filter((m) => m.thumb).length;
      out.categories = [...new Set(b.mods.map((m) => m.category))].length;
    }
  } catch (e) {
    out.ok = false;
    out.error = String(e);
  }
  // 等界面真的把卡片渲染出来再读 —— 首次渲染要把 200 张缩略图转成
  // data URI，比 bootstrap 慢一拍。原来这里是「读完就报」，偶尔会读到 0。
  for (let i = 0; i < 40; i += 1) {
    if (document.querySelectorAll('.mod-card').length) break;
    await new Promise((r) => setTimeout(r, 200));
  }
  out.cards = document.querySelectorAll('.mod-card').length;
  out.brand = (document.querySelector('.brand-name') || {}).textContent || null;
  window.__e2e = JSON.stringify(out);
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
        win.evaluate_js(PROBE_JS)
    except Exception as exc:
        print("[E2E] kick failed:", exc, flush=True)

    result = None
    for _ in range(60):
        time.sleep(0.4)
        try:
            result = win.evaluate_js("window.__e2e")
        except Exception:
            continue
        if result:
            break

    print("[E2E] result:", result, flush=True)
    time.sleep(0.8)
    win.destroy()


def main():
    api = Api()
    url = "file:///" + os.path.join(
        _ROOT, "app", "webui", "index.html").replace("\\", "/")
    win = webview.create_window("E2E", url=url, js_api=api,
                                width=1440, height=900,
                                background_color="#08090b")
    api.attach_window(win)
    threading.Thread(target=run, args=(win,), daemon=True).start()
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
