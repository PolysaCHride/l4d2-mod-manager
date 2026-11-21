# -*- coding: utf-8 -*-
"""开发期诊断工具：从入口文件里搬出来的临时脚手架。

包含三件东西：
  shot_window()  —— 抓窗口截图（不依赖 Pillow，手写 BMP）
  verify_ui()    —— 在页面里跑一轮 DOM 断言
  selftest()     —— bootstrap + 卡片数量检查（窗口关闭后退出）

入口 main_web.py 只在对应环境变量存在时才调用它们，
这样正式运行时这些代码完全不参与，入口也能保持可读。
"""
import os
import sys
import time


# ------------------------------------------------------------------ 截图

def shot_window(window, path, title, wait=6.0):
    """等界面稳定后抓窗口并保存。不依赖 Pillow（手写 BMP）。"""
    import ctypes
    from ctypes import wintypes

    time.sleep(wait)
    user32 = gdi32 = None
    hwnd = hdc = mdc = bmp = None
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            print("[shot] window not found", flush=True)
            return False

        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top
        print("[shot] size", w, h, flush=True)

        hdc = user32.GetWindowDC(hwnd)
        mdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        gdi32.SelectObject(mdc, bmp)
        user32.PrintWindow(hwnd, mdc, 2)

        class BMIH(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD),
                        ("biWidth", wintypes.LONG),
                        ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD),
                        ("biBitCount", wintypes.WORD),
                        ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD),
                        ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG),
                        ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD)]

        bi = BMIH()
        bi.biSize = ctypes.sizeof(BMIH)
        bi.biWidth = w
        bi.biHeight = -h          # 负数 = GetDIBits 按「自上而下」给像素
        bi.biPlanes = 1
        bi.biBitCount = 32
        bi.biCompression = 0

        buf = ctypes.create_string_buffer(w * h * 4)
        if not gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0):
            print("[shot] GetDIBits failed", flush=True)
            return False

        import struct
        hdr = b"BM" + struct.pack("<IHHI", 54 + len(buf), 0, 0, 54)
        # ⚠️ 文件头里 biHeight 也必须写 -h，与上面 GetDIBits 的行序保持一致。
        # 早先这里写的是正数（声明 bottom-up）而数据其实是 top-down，
        # 结果每张截图在 Viewers 里都是上下颠倒的。
        info = struct.pack("<IiiHHIIiiII", 40, w, -h, 1, 32, 0,
                           w * h * 4, 0, 0, 0, 0)
        with open(path, "wb") as f:
            f.write(hdr + info + buf.raw)
        print("[shot] saved", path, flush=True)
        return True
    except Exception as exc:
        print("[shot] failed:", exc, flush=True)
        return False
    finally:
        # GDI 句柄每次都要释放。早先成功分支直接 return，
        # bmp / mdc / hdc 一直没释放（重复截图会一路累积）。
        try:
            if gdi32 and bmp:
                gdi32.DeleteObject(bmp)
            if gdi32 and mdc:
                gdi32.DeleteDC(mdc)
            if user32 and hdc:
                user32.ReleaseDC(hwnd, hdc)
        except Exception:
            pass


# ------------------------------------------------------------- UI 断言

VERIFY_JS = r"""
(async () => {
  const out = {};
  const w = document.querySelector('[data-rail="weapon"]');
  if (w) { w.click(); await new Promise(r => setTimeout(r, 400)); }

  const caret = document.querySelector('.fold-caret use');
  out.caret = caret ? caret.getAttribute('href') : null;

  const rows = [...document.querySelectorAll('#filters .tree-items:not([hidden]) .filter-row')];
  out.firstItem = rows[0] ? rows[0].querySelector('.item-name').textContent.trim() : null;
  out.rowCount = rows.length;
  out.treeHeads = document.querySelectorAll('#filters .tree-head').length;
  out.conflictLine = !!document.querySelector('.conflict-line');

  const more = document.getElementById('insMore');
  if (more) {
    more.click(); await new Promise(r => setTimeout(r, 100));
    out.menuOpen = !document.getElementById('insMoreMenu').hidden;
    document.body.click(); await new Promise(r => setTimeout(r, 100));
    out.menuAutoClose = document.getElementById('insMoreMenu').hidden;
  }
  out.groupMini = document.querySelectorAll('[data-pick]').length;
  out.cards = document.querySelectorAll('.mod-card').length;
  window.__verify = JSON.stringify(out);
})();
"""


def verify_ui(window, wait=3.0):
    """跑一轮 DOM 断言，结果打到 stdout。用于打包后的冒烟检查。"""
    # 等卡片真的渲染出来再断言，否则会拿到空结果
    for _ in range(60):
        time.sleep(0.5)
        try:
            n = window.evaluate_js("document.querySelectorAll('.mod-card').length")
            if n:
                break
        except Exception:
            pass

    try:
        window.evaluate_js(VERIFY_JS)
        for _ in range(40):
            time.sleep(0.3)
            r = window.evaluate_js("window.__verify || null")
            if r:
                print("[verify]", r, flush=True)
                return r
    except Exception as exc:
        print("[verify] failed:", exc, flush=True)
    return None


# --------------------------------------------------------------- 自检

SELFTEST_JS = r"""
window.__st = null;
(async () => {
  const out = { mode: window.bridge.isMock() ? 'mock' : 'live' };
  try {
    const b = await window.bridge.bootstrap();
    out.ok = !!b.ok;
    out.mods = b.ok ? b.mods.length : 0;
    out.enabled = b.ok ? b.stats.enabled : 0;
    out.version = b.ok ? b.version : null;
  } catch (e) { out.error = String(e); }
  await new Promise((r) => setTimeout(r, 300));
  out.cards = document.querySelectorAll('.mod-card').length;
  out.onboardVisible = !document.getElementById('onboard').hidden;
  window.__st = JSON.stringify(out);
})();
"""


def selftest(window, wait=1.2):
    """bootstrap + 渲染检查。检查完关闭窗口。"""
    time.sleep(wait)
    try:
        window.evaluate_js(SELFTEST_JS)
    except Exception:
        pass
    for _ in range(60):
        time.sleep(0.3)
        try:
            r = window.evaluate_js("window.__st")
        except Exception:
            continue
        if r:
            print("[selftest]", r, flush=True)
            break
    window.destroy()
