# -*- coding: utf-8 -*-
"""pywebview 打包验证：加载、渲染、通信、截图，然后退出。

用法：
    .venv/Scripts/python.exe proto_pywebview.py --check
"""
import json
import os
import sys
import threading
import time

import webview

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.normpath(os.path.join(HERE, "..", "final", "demo.html"))

FAKE_MODS = [
    {"id": "m1", "name": "Koharu [Replace Ellis]", "alias": "", "cat": "角色",
     "item": "Ellis", "size": 116.1, "enabled": False, "file": "3668116708.vpk",
     "img": "../assets/mods/mod1.webp", "added": "2 天前"},
    {"id": "m3", "name": "VRC プラム Plum replace ellis", "alias": "夏日甜点屋",
     "cat": "角色", "item": "Ellis", "size": 34.1, "enabled": True,
     "file": "3659210344.vpk", "img": "../assets/mods/mod3.webp", "added": "1 周前"},
]

RESULT = {}


class Api:
    def get_mods(self):
        print("[PY] get_mods", flush=True)
        return FAKE_MODS

    def toggle_mod(self, mod_id):
        for m in FAKE_MODS:
            if m["id"] == mod_id:
                m["enabled"] = not m["enabled"]
                print(f"[PY] toggle_mod {mod_id} -> {m['enabled']}", flush=True)
                return {"ok": True, "enabled": m["enabled"]}
        return {"ok": False}

    def ping(self):
        print("[PY] ping", flush=True)
        return "pong"

    def report(self, payload):
        """JS 把自检结果回传。"""
        RESULT["js"] = payload
        print("[PY] JS report:", payload, flush=True)
        return {"ok": True}


def run_check(window):
    """等页面就绪后跑一轮自检。"""
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            ready = window.evaluate_js(
                "typeof window.pywebview !== 'undefined' && "
                "typeof window.pywebview.api !== 'undefined'")
            if ready:
                break
        except Exception:
            pass
        time.sleep(0.4)

    js = """
    (async () => {
      const api = window.pywebview.api;
      const out = {};
      try { out.ping = await api.ping(); } catch (e) { out.pingError = String(e); }
      try {
        const mods = await api.get_mods();
        out.modCount = Array.isArray(mods) ? mods.length : -1;
        out.firstName = mods && mods[0] ? mods[0].name : null;
      } catch (e) { out.modsError = String(e); }
      try {
        const r = await api.toggle_mod('m1');
        out.toggled = r;
      } catch (e) { out.toggleError = String(e); }
      out.cards = document.querySelectorAll('.mod-card').length;
      out.brand = document.querySelector('.brand-name')?.textContent || null;
      out.accent = getComputedStyle(document.documentElement)
                    .getPropertyValue('--accent').trim();
      out.onCards = document.querySelectorAll('.mod-card.is-on').length;
      await api.report(JSON.stringify(out));
      return JSON.stringify(out);
    })()
    """
    try:
        val = window.evaluate_js(js)
        print("[PY] check result:", val, flush=True)
        RESULT["eval"] = val
    except Exception as e:
        print("[PY] eval error:", e, flush=True)
        RESULT["error"] = str(e)

    time.sleep(0.5)
    window.destroy()


def main():
    check = "--check" in sys.argv
    win = webview.create_window(
        "L4D2 Mod Manager · pywebview 原型",
        url="file:///" + DEMO.replace("\\", "/"),
        width=1440,
        height=900,
        js_api=Api(),
    )
    if check:
        threading.Thread(target=run_check, args=(win,), daemon=True).start()
    webview.start(debug=check)
    return 0


if __name__ == "__main__":
    sys.exit(main())
