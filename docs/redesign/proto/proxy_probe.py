# -*- coding: utf-8 -*-
"""验证 pywebview api Proxy 的方法访问方式。"""
import logging
import os
import sys
import threading
import time

_ROOT = r"D:\项目\L4D2 Mod Manager"
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import webview  # noqa: E402


class Q(logging.Filter):
    def filter(self, r):
        try:
            m = r.getMessage()
        except Exception:
            return True
        return not any(k in m for k in (
            "AccessibilityObject", "AllowExternalDrop", "CanGoBack",
            "CanGoForward", "recursion depth", "E_NOINTERFACE",
            "CoreWebView2"))


logging.getLogger("pywebview").addFilter(Q())


class Api(object):
    _serializable = False

    def ping(self):
        return "pong"

    def add(self, a, b):
        return a + b


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>probe</title></head>
<body><pre id="o">waiting</pre>
<script>
window.out = [];
(async () => {
  const lines = [];
  const api = window.pywebview.api;
  lines.push('typeof api: ' + typeof api);
  lines.push('keys: ' + JSON.stringify(Object.keys(api)));
  lines.push("'ping' in api: " + ('ping' in api));
  lines.push('typeof api.ping: ' + typeof api.ping);

  try {
    const r = await api.ping();
    lines.push('api.ping() -> ' + JSON.stringify(r));
  } catch (e) { lines.push('api.ping() ERR: ' + e); }

  try {
    const r2 = await api.add(1, 2);
    lines.push('api.add(1,2) -> ' + JSON.stringify(r2));
  } catch (e) { lines.push('api.add ERR: ' + e); }

  document.getElementById('o').textContent = lines.join('\\n');
  window.done = lines.join(' | ');
})();
</script></body></html>"""


def run(win):
    for _ in range(60):
        time.sleep(0.4)
        try:
            if win.evaluate_js("window.done || null"):
                break
        except Exception:
            pass
    try:
        print("[P]", win.evaluate_js("window.done"), flush=True)
        print("[P] pre:", win.evaluate_js(
            "document.getElementById('o').textContent"), flush=True)
    except Exception as exc:
        print("[P] err:", exc, flush=True)
    win.destroy()


def main():
    api = Api()
    win = webview.create_window("probe", html=PAGE, js_api=api,
                                width=800, height=600)
    threading.Thread(target=run, args=(win,), daemon=True).start()
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
