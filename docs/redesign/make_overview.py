# -*- coding: utf-8 -*-
"""Compose a compact visual review board from the five screenshots."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "screenshots"
OUT = ROOT / "assets" / "overview.png"

W, H = 1680, 1000
M = 48
BG = (15, 16, 19)
PANEL = (23, 25, 29)
LINE = (46, 49, 56)
TEXT = (238, 240, 235)
MUTED = (145, 151, 160)
ACCENT = (201, 54, 42)
MINT = (208, 242, 108)


def load_font(size, bold=False):
    names = ["msyhbd.ttc", "msyh.ttc"] if bold else ["msyh.ttc", "msyhbd.ttc"]
    for name in names:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def rounded_image(src, size, radius=7):
    im = Image.open(src).convert("RGB")
    im.thumbnail(size, Image.LANCZOS)
    canvas = Image.new("RGBA", size, (18, 20, 23, 255))
    x = (size[0] - im.width) // 2
    y = (size[1] - im.height) // 2
    canvas.paste(im, (x, y))
    mask = Image.new("L", size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(canvas, (0, 0), mask)
    return out


def main():
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    f_eyebrow = load_font(13)
    f_title = load_font(38, bold=True)
    f_sub = load_font(15)
    f_num = load_font(13, bold=True)
    f_name = load_font(19, bold=True)
    f_label = load_font(11)
    f_footer = load_font(11)

    d.rectangle((0, 0, W, 7), fill=ACCENT)
    d.text((M, 37), "L4D2 MOD MANAGER  /  VISUAL DIRECTIONS", font=f_eyebrow, fill=MUTED)
    d.text((M, 62), "五个重构方向，同一套真实内容。", font=f_title, fill=TEXT)
    d.text((M, 116), "主界面样稿 · 1440 × 900 · 数据与缩略图来自当前版本", font=f_sub, fill=MUTED)
    d.text((W - M, 40), "DESIGN REVIEW 01", font=f_eyebrow, fill=ACCENT, anchor="ra")

    cards = [
        ("01", "BLACKSITE / 战术档案", "石墨黑 · 图表绿 · 常驻详情", "v1.png", "深色控制台，把冲突和详情放回工作流", TEXT),
        ("02", "SAFEHOUSE / 安全屋", "米纸色 · 油墨黑 · 安全红", "v2.png", "像档案册一样浏览，降低工具感", TEXT),
        ("03", "WORKSHOP / 工坊中枢", "海军蓝 · 亮青 · 同步优先", "v3.png", "Steam 用户零学习成本的入口", TEXT),
        ("04", "LOADOUT LAB / 配装台", "石墨蓝 · 薄荷绿 · 蓝图网格", "v4.png", "从管理模组，升级为管理今晚怎么玩", TEXT),
        ("05", "INDEX / 索引", "冷白 · 墨黑 · 品牌红", "v5.png", "给 100+ 模组库的一张工作台", TEXT),
        ("—", "CURRENT / 当前版本", "末世绿 · 三栏卡片", "../assets/current-ui.webp", "现有主界面，作为对照基线", MUTED),
    ]

    cols = 3
    gap = 24
    cw = (W - M * 2 - gap * (cols - 1)) // cols
    ch = 372
    top = 166
    for idx, (num, name, tags, file, desc, accent) in enumerate(cards):
        row, col = divmod(idx, cols)
        x = M + col * (cw + gap)
        y = top + row * (ch + gap)
        d.rounded_rectangle((x, y, x + cw, y + ch), radius=9, fill=PANEL, outline=LINE)

        shot = rounded_image(SHOTS / file, (cw - 24, 315), radius=5)
        canvas.paste(shot, (x + 12, y + 12), shot)

        color = ACCENT if num != "—" else MUTED
        d.text((x + 14, y + 336), num, font=f_num, fill=color)
        d.text((x + 46, y + 334), name, font=f_name, fill=TEXT)
        d.text((x + 14, y + 357), tags, font=f_label, fill=MUTED)
        # A tiny description at the right is intentionally omitted to keep the board calm.

    d.line((M, H - 38, W - M, H - 38), fill=LINE, width=1)
    d.text((M, H - 28), "PROTOTYPES  docs/redesign/v1.html — v5.html", font=f_footer, fill=MUTED)
    d.text((W - M, H - 28), "NEXT  /  pick a direction, then lock interaction + implementation", font=f_footer, fill=MUTED, anchor="ra")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, "PNG")
    print(OUT, canvas.size)


if __name__ == "__main__":
    main()
