# -*- coding: utf-8 -*-
"""桥接层共用的显示格式化。

目前只有一个函数，但它原来是两份逐字重复的实现（`api._fmt_size` /
`tasks._fmt_size`）。两份拷贝已经出现的风险是：改一处忘另一处，
列表里的体积和下载进度里的体积就会不一致。

**与旧界面 `app/ui/util.fmt_size` 的差异（有意为之）**：
  - 旧版 KB 段用整数（`%.0f`），这里用一位小数（`%.1f`）——
    300KB 的模组在旧界面显示 "293 KB"，这里显示 "292.8 KB"。
  - 旧版遇到非数字返回 "?"，这里返回 "0 B"。
`app/ui/` 是冻结基线，不再改；两条界面各自保持自己的历史输出即可，
不要为了「看起来一样」去改冻结代码。
"""


def fmt_size(n):
    """字节数 → 人类可读字符串。

    非数字/负数/None 一律 "0 B"（列表里 size 缺失的记录很常见，
    显示 "0 B" 比 "?" 更不容易被误解成「加载失败」）。
    """
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        n = 0.0
    if n <= 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (int(n), unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0
    return "%.1f GB" % n
