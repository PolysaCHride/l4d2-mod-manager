# -*- coding: utf-8 -*-
"""WebUI 入口：pywebview + 桥接层。

与旧入口 main.py 并存：
  main.py        PySide6 原生界面（旧，仍在发布）
  main_web.py    本文件，pywebview + 系统 WebView2（新）

环境变量（都是给开发和排查用的，正式运行不需要）：
  L4D2_DEBUG=1        打开 DevTools
  L4D2_RAIL=weapon    启动后直接落到某个分类（角色/特感/武器/地图/其他）
  L4D2_SHOT=<路径>    等界面稳定后截图（BMP），然后退出
  L4D2_VERIFY=1       跑一轮 DOM 断言
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import webview  # noqa: E402

from app.core import app_paths  # noqa: E402
from app.shell.api import Api  # noqa: E402

WINDOW_TITLE = "L4D2 Mod Manager"


def webui_dir():
    """前端目录。打包后位于 _internal/webui。"""
    base = app_paths.resource_root()
    p = os.path.join(base, "webui")
    return p if os.path.isdir(p) else os.path.join(_ROOT, "app", "webui")


def build_url():
    from pathlib import Path as _Path
    index = _Path(webui_dir()) / "index.html"
    if not index.is_file():
        raise SystemExit("找不到前端文件：%s" % index)

    # file:// URL 必须百分号编码（路径含空格时 WebView2 会静默失败）
    url = index.as_uri()

    rail = os.environ.get("L4D2_RAIL")
    if rail:
        url += "#rail=" + rail
    return url


def main():
    t0 = time.time()
    api = Api()
    url = build_url()
    print("[main] webui:", url, flush=True)

    # 无边框窗口：标题栏由前端自绘（index.html 顶部 54px 那条）。
    # easy_drag 只对 .pywebview-drag-region 生效（pywebview 默认选择器），
    # 所以只有 <header class="topbar pywebview-drag-region"> 能拖窗口，
    # 卡片、输入框、按钮都不会误拖。
    window = webview.create_window(
        WINDOW_TITLE,
        url=url,
        js_api=api,
        width=1440,
        height=900,
        frameless=True,
        easy_drag=True,
        resizable=True,
        background_color="#08090b",
    )
    api.attach_window(window)

    print("[main] startup %.2fs" % (time.time() - t0), flush=True)
    _start_diagnostics(window)

    webview.start(debug=bool(os.environ.get("L4D2_DEBUG")))
    return 0


def _start_diagnostics(window):
    """按环境变量启动开发期诊断（不影响正常运行）。"""
    shot = os.environ.get("L4D2_SHOT")
    verify = os.environ.get("L4D2_VERIFY")
    if not (shot or verify):
        return

    import threading
    try:
        from app.shell import devtools
    except ImportError:
        print("[main] 找不到 app/shell/devtools.py，跳过诊断", flush=True)
        return

    def run():
        if verify:
            devtools.verify_ui(window)
        if shot:
            devtools.shot_window(window, shot, WINDOW_TITLE)

    threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    sys.exit(main())
