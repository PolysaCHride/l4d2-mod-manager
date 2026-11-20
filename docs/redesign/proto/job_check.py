# -*- coding: utf-8 -*-
"""验证长任务：扫描 + 进度事件。

只读操作，不改数据。
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

JS = r"""
window.__job = null;
(async () => {
  const out = {events: [], done: false};
  window.__dsh.on('job.progress', (p) => {
    if (out.events.length < 6) out.events.push({p: p.percent, l: p.label});
    out.lastPercent = p.percent;
  });
  window.__dsh.on('job.done', (p) => {
    out.done = true;
    out.totalEvents = out.events.length;
    window.__job = JSON.stringify(out);
  });
  window.__dsh.on('job.error', (p) => {
    out.error = p.message;
    window.__job = JSON.stringify(out);
  });
  const r = await window.bridge.start_scan();
  out.jobId = r.job_id;
  out.started = r.ok;
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

    win.evaluate_js(JS)
    result = None
    for _ in range(100):
        time.sleep(0.3)
        try:
            result = win.evaluate_js("window.__job")
        except Exception:
            continue
        if result:
            break

    print("[JOB] result:", result, flush=True)
    time.sleep(0.4)
    win.destroy()


def main():
    api = Api()
    url = "file:///" + os.path.join(
        _ROOT, "app", "webui", "index.html").replace("\\", "/")
    win = webview.create_window("job-test", url=url, js_api=api,
                                width=1200, height=800,
                                background_color="#08090b")
    api.attach_window(win)
    threading.Thread(target=run, args=(win,), daemon=True).start()
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
