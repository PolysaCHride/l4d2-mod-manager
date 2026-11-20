# -*- coding: utf-8 -*-
"""诊断：判断 pywebview 的报错是否影响实际功能。

只看两件事：
  1. 窗口里的界面是否渲染出来了
  2. api 调用是否通

用法：
    .venv/Scripts/python.exe -X utf8 docs/redesign/proto/probe_pywebview.py
"""
import os
import sys
import threading
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import webview  # noqa: E402

RESULT = {}


class Api(object):
    def ping(self):
        RESULT["ping"] = True
        print("[PY] ping", flush=True)
        return "pong"

    def get_mods(self):
        mods = [{"file": "a.vpk", "title": "测试模组", "enabled": True}]
        RESULT["get_mods"] = True
        print("[PY] get_mods", flush=True)
        return mods

    def report(self, payload):
        RESULT["js"] = payload
        print("[PY] JS report:", payload, flush=True)
        return {"ok": True}


def probe(window):
    deadline = time.time() + 25
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            ready = window.evaluate_js(
                "typeof window.pywebview !== 'undefined' && "
                "typeof window.pywebview.api !== 'undefined'")
        except Exception:
            continue
        if ready:
            break

    js = """
    (async () => {
      const api = window.pywebview.api;
      const out = {};
      try { out.ping = await api.ping(); } catch (e) { out.pingErr = String(e); }
      try {
        const ms = await api.get_mods();
        out.modCount = ms.length;
        out.first = ms[0].title;
      } catch (e) { out.modsErr = String(e); }
      out.rendered = document.querySelectorAll('.mod-card').length;
      out.brand = (document.querySelector('.brand-name') || {}).textContent || null;
      await api.report(JSON.stringify(out));
      return JSON.stringify(out);
    })()
    """
    try:
        print("[PY] eval:", window.evaluate_js(js), flush=True)
    except Exception as exc:
        print("[PY] eval error:", exc, flush=True)

    time.sleep(1)
    window.destroy()


def main():
    url = "file:///" + os.path.join(
        _ROOT, "app", "webui", "index.html").replace("\\", "/")
    print("[PY] url:", url, flush=True)
    win = webview.create_window(
        "probe", url=url, js_api=Api(),
        width=1440, height=900, background_color="#08090b")
    threading.Thread(target=probe, args=(win,), daemon=True).start()
    webview.start(debug=False)
    print("[PY] RESULT:", RESULT, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
