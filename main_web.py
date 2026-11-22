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
    _arm_file_drop(window, api)
    _start_diagnostics(window)

    webview.start(debug=bool(os.environ.get("L4D2_DEBUG")))
    return 0


def _arm_file_drop(window, api):
    """把「拖文件进来」接到 Python 侧，这样才拿得到绝对路径。

    ⚠️ 必须由**这里**（Python）调 `Element.on('drop', ...)`：

      · pywebview 的 `_dnd_state['num_listeners']` 只有在
        `webview.dom.Element.on('drop', cb)` 时才会 +1；
      · 它 > 0 时，WebView2 才会走
        `postMessageWithAdditionalObjects('FilesDropped', files)`，
        传的是带 `.Path` 的 CoreWebView2File；
      · pywebview 再把绝对路径回填进事件里每个 file 的
        `pywebviewFullPath`。

    在 JS 里 `addEventListener('drop')` **不会**触发这条通道 ——
    `dataTransfer.files[i]` 只有 name/size/type，永远没有 path。
    这就是之前「拖拽看起来支持、实际拿不到路径」的根因。

    失败要静默：这条通道依赖 pywebview 内部实现，换版本可能失效。
    真挂了就退回原行为（前端弹文件选择框），不能让用户拖了没反应。
    """
    import threading

    def arm():
        try:
            from webview.dom import DOMEventHandler
        except Exception as exc:      # 老版本没有 DOM API
            print("[main] 拖拽路径注入不可用（%s），退回点击选择" % exc, flush=True)
            return

        # 等页面真加载完：DOM 是静态的，但 _getNodeId 需要元素已经存在。
        for _ in range(60):
            try:
                if window.evaluate_js("document.querySelector('#dropZone') !== null"):
                    break
            except Exception:
                pass
            time.sleep(0.25)

        for attempt in range(8):
            try:
                el = window.dom.get_element("#dropZone")
            except Exception as exc:
                print("[main] get_element 失败：%s" % exc, flush=True)
                return
            if el is not None:
                try:
                    # prevent_default=True 很关键：不阻止默认行为的话，
                    # WebView2 会试着把文件「当导航打开」，
                    # 在 file:// 页面上表现为白屏。
                    el.on("drop", DOMEventHandler(api.on_file_drop,
                                                  prevent_default=True))
                    print("[main] 拖拽路径注入已启用（第 %d 次尝试）" % (attempt + 1),
                          flush=True)
                    return
                except Exception as exc:
                    print("[main] 注册 drop 监听失败：%s" % exc, flush=True)
                    return
            time.sleep(0.4)
        print("[main] #dropZone 一直没出现，拖拽导入退回点击选择", flush=True)

    threading.Thread(target=arm, daemon=True).start()


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
