from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
src = ROOT / "preview.png"
out = ROOT / "blacksite-map.png"

shot = Image.open(src).convert("RGB")
W, SH = shot.size
HEAD = 82
LEG = 214
FOOT = 36
canvas = Image.new("RGB", (W, HEAD + SH + LEG + FOOT), (11, 13, 15))
canvas.paste(shot, (0, HEAD))
d = ImageDraw.Draw(canvas)

def font(size, bold=False):
    for name in ("msyhbd.ttc" if bold else "msyh.ttc", "msyh.ttc", "segoeui.ttf"):
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()

f_title = font(23, True)
f_body = font(10)
f_small = font(9)
f_badge = font(10, True)

ACCENT = (214, 244, 93)
TEXT = (232, 235, 229)
MUTED = (146, 154, 145)
DIM = (103, 112, 104)
LINE = (47, 55, 42)
PANEL = (17, 20, 18)

d.text((28, 18), "BLACKSITE / ZONE MAP", font=f_title, fill=TEXT)
d.text((28, 50), "TitleBar v0.2 · 搜索左边界与主区对齐 · 其余分区保持上一版。", font=f_body, fill=MUTED)
d.text((W - 28, 20), "L4D2 MOD MANAGER  /  FOUNDATION 01", font=f_small, fill=ACCENT, anchor="ra")
d.text((W - 28, 46), "不包含最终实现 · 2026.11.18", font=f_small, fill=DIM, anchor="ra")

zones = [
    ("01", "TITLEBAR", 0, 0, W, 56),
    ("02", "RAIL", 0, 56, 68, 814),
    ("03", "FILTER PANEL", 68, 56, 324, 814),
    ("04", "MAIN HEADER", 324, 56, 1114, 172),
    ("05", "ACTION BAR", 324, 172, 1114, 214),
    ("06", "MOD GRID", 324, 214, 1114, 814),
    ("07", "INSPECTOR", 1114, 56, 1440, 814),
    ("08", "STATUSBAR", 0, 870, 1440, 900),
]

for code, label, x1, y1, x2, y2 in zones:
    # subtle outline + corner marks
    d.rectangle((x1, y1 + HEAD, x2 - 1, y2 + HEAD - 1), outline=LINE, width=1)
    for (cx, cy, dx, dy) in ((x1 + 2, y1 + HEAD + 2, 1, 1), (x2 - 3, y1 + HEAD + 2, -1, 1), (x1 + 2, y2 + HEAD - 3, 1, -1), (x2 - 3, y2 + HEAD - 3, -1, -1)):
        d.line((cx, cy, cx + 10 * dx, cy), fill=ACCENT, width=1)
        d.line((cx, cy, cx, cy + 10 * dy), fill=ACCENT, width=1)

    # small number badge at the top-left of the zone, inside the screenshot
    bx, by = x1 + 7, y1 + HEAD + 7
    if code == "01":
        bx = x2 - 52
    if code == "08":
        bx, by = 8, y1 + HEAD + 7
    r = 10
    d.ellipse((bx, by, bx + r * 2, by + r * 2), fill=ACCENT)
    bb = d.textbbox((0, 0), code, font=f_badge)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    d.text((bx + r - tw / 2, by + r - th / 2 - 1), code, font=f_badge, fill=(9, 11, 13))

# Alignment marker: search and results share x = 324
ax = 324
ay1 = HEAD
ay2 = HEAD + SH
for yy in range(ay1, ay2, 8):
    d.line((ax, yy, ax, min(yy + 4, ay2)), fill=(214, 244, 93), width=1)
d.text((ax + 6, ay2 - 16), "324px  SEARCH ↔ RESULTS ALIGN", font=f_small, fill=ACCENT)

# Legend
ly = HEAD + SH + 14
d.text((28, ly), "ZONE INDEX / 分区索引", font=f_small, fill=ACCENT)
ly += 21
items = [
    ("01", "TITLEBAR", "品牌 / 全局搜索 / 游戏状态 / 启动 / 窗口按钮"),
    ("02", "RAIL", "一级导航 / 一键整理 / 设置"),
    ("03", "FILTER PANEL", "分类 / 物品 / 互斥提醒 / 容量"),
    ("04", "MAIN HEADER", "面包屑 / 标题 / 计数 / 页面操作"),
    ("05", "ACTION BAR", "搜索 / 排序 / 刷新 / 导入 / 工坊 / 启动"),
    ("06", "MOD GRID", "卡片 / 启用状态 / 库摘要"),
    ("07", "INSPECTOR", "预览 / 启用 / 文件 / 同组 / 操作"),
    ("08", "STATUSBAR", "连接 / 计数 / 游戏状态 / 路径 / 版本"),
]
col_w = (W - 56) // 4
for i, (code, name, desc) in enumerate(items):
    col, row = i % 4, i // 4
    x = 28 + col * col_w
    y = ly + row * 66
    d.rectangle((x, y, x + 24, y + 24), fill=PANEL, outline=LINE)
    d.text((x + 5, y + 5), code, font=f_badge, fill=ACCENT)
    d.text((x + 34, y + 2), name, font=f_small, fill=TEXT)
    d.text((x + 34, y + 18), desc, font=f_small, fill=MUTED)

# Footer
fy = HEAD + SH + LEG
d.rectangle((0, fy, W, fy + FOOT), fill=(11, 13, 15))
d.text((28, fy + 11), "GATE: 每个分区逐项对齐后才进入最终版；当前只确认边界、组件与文案。", font=f_small, fill=MUTED)
d.text((W - 28, fy + 11), "docs/redesign/final/BLACKSITE_DECOMPOSITION.md", font=f_small, fill=DIM, anchor="ra")

canvas.save(out)
print(out, canvas.size)
