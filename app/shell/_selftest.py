# -*- coding: utf-8 -*-
"""桥接层自测：不需要窗口，用假 window 就能验证。

运行：
    .venv/Scripts/python.exe -X utf8 -m app.shell._selftest
"""
import json
import sys


class FakeWindow(object):
    """只实现 evaluate_js，把调用打印出来。"""

    def __init__(self):
        self.events = []

    def evaluate_js(self, js):
        self.events.append(js)
        print("  [emit] %s" % js[:140], flush=True)


def show(title, payload):
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) > 320:
        text = text[:320] + "…"
    print("%-42s %s" % (title, text), flush=True)


def main():
    from app.shell.api import Api

    win = FakeWindow()
    api = Api()
    api.attach_window(win)

    print("=" * 70)
    print("桥接层自测")
    print("=" * 70)

    boot = api.bootstrap()
    if not boot.get("ok"):
        print("bootstrap 失败：", boot.get("error"))
        return 1

    mods = boot["mods"]
    print("bootstrap: ok")
    print("  mods   :", len(mods))
    print("  enabled:", boot["stats"]["enabled"])
    print("  version:", boot["version"])
    print("  paths  :", boot["paths"]["addons"][:60])
    print("  valid  :", boot["paths"]["valid"])
    print("  game   :", boot["game"]["running"])
    if mods:
        m = mods[0]
        print("  首条   :", m["title"][:40])
        print("    category=%s item=%r size=%s" % (m["category"], m["item"], m["sizeText"]))
        print("    thumb=%s" % (m["thumb"][:70] if m["thumb"] else "(无)"))

    print()
    print("--- 读接口 ---")
    show("get_stats()", api.get_stats())
    show("get_mods() 条数", {"count": len(api.get_mods().get("mods", []))})

    print()
    print("--- 分类分布 ---")
    from collections import Counter
    dist = Counter(m["category"] for m in mods)
    for cat, n in dist.most_common():
        print("  %-8s %d" % (cat, n))

    print()
    print("--- 写接口（安全性检查，不实际改动）---")
    # 只验证参数校验路径，不真的改数据
    show("toggle_mod(不存在)", api.toggle_mod("__not_exist__.vpk", True))
    show("set_alias(不存在)", api.set_alias("__not_exist__.vpk", "x"))
    show("delete_mod(不存在)", api.delete_mod("__not_exist__.vpk"))

    print()
    print("--- 设置 ---")
    show("set_palette(非法)", api.set_palette("nope"))
    show("set_palette(safehouse)", api.set_palette("safehouse"))
    show("set_palette(还原 blacksite)", api.set_palette("blacksite"))

    print()
    print("--- 事件推送 ---")
    print("  已推送事件数：", len(win.events))
    if win.events:
        print("  最后一条：", win.events[-1][:100])

    print()
    print("=" * 70)
    print("自测完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
