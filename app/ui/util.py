# -*- coding: utf-8 -*-
"""UI 小工具：格式化 / 预览图加载。"""
import os
import re
import time

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImageReader, QPainter, QPainterPath, QPixmap

from ..core import app_paths
from . import theme

WIKI_DIR = app_paths.asset_path("wiki")

# 占位图缓存（含 wiki 占位），避免反复解码
_PIX_CACHE = {}


def _safe_name(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name or "").strip()


def wiki_image_path(item, category):
    """按 物品 → 类别 顺序找 assets/wiki 下的占位图。"""
    for name in (item, category):
        if not name:
            continue
        p = os.path.join(WIKI_DIR, _safe_name(name) + ".png")
        if os.path.isfile(p):
            return p
    return ""


def fmt_size(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    if n >= 1024 ** 3:
        return "%.1f GB" % (n / 1024 ** 3)
    if n >= 1024 ** 2:
        return "%.1f MB" % (n / 1024 ** 2)
    if n >= 1024:
        return "%.0f KB" % (n / 1024)
    return "%d B" % n


def fmt_time(ts):
    try:
        return time.strftime("%Y-%m-%d", time.localtime(int(ts)))
    except (TypeError, ValueError):
        return "-"


def elide(text, width_px, font_metrics):
    if not text:
        return ""
    return font_metrics.elidedText(text, Qt.ElideRight, width_px)


def _cache_put(key, pm):
    if len(_PIX_CACHE) > 900:
        _PIX_CACHE.clear()
    _PIX_CACHE[key] = pm


def rounded_pixmap(pixmap, radius):
    """裁出圆角预览图，避免卡片图片的直角破坏整体轮廓。"""
    if pixmap.isNull() or radius <= 0:
        return pixmap
    result = QPixmap(pixmap.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(result.rect()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return result


def load_thumb(path, width, height, category, item="", radius=0):
    """预览图优先级：mod 自带/已下载预览 → wiki 物品图 → wiki 类别图 → 渐变占位。

    全部走缓存（key 含文件 mtime，预览图更新后自动失效），避免大库反复解码卡顿。
    """
    wp = wiki_image_path(item, category)
    key_src = ""
    if path and os.path.isfile(path):
        key_src = path
    elif wp:
        key_src = wp
    if not key_src:
        key = ("gen", category, width, height, radius)
        pm = _PIX_CACHE.get(key)
        if pm is None:
            pm = rounded_pixmap(theme.thumb_pixmap(width, height, category), radius)
            _cache_put(key, pm)
        return pm
    try:
        mtime = os.stat(key_src).st_mtime
    except OSError:
        mtime = 0
    key = (key_src, mtime, width, height, radius)
    pm = _PIX_CACHE.get(key)
    if pm is not None:
        return pm
    img = _decode_scaled(key_src, width, height)
    pm = img if img is not None else theme.thumb_pixmap(width, height, category)
    pm = rounded_pixmap(pm, radius)
    _cache_put(key, pm)
    return pm


def _decode_scaled(path, width, height):
    """按目标宽度解码图片并垂直居中裁剪；失败返回 None。"""
    try:
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid() and size.width() > 0:
            tw = max(1, width)
            th = max(1, int(size.height() * tw / size.width()))
            reader.setScaledSize(QSize(tw, th))
        img = reader.read()
        if not img.isNull():
            scaled = QPixmap.fromImage(img)
            if scaled.height() < height:
                reader2 = QImageReader(path)
                reader2.setAutoTransform(True)
                hh = max(1, height)
                ww = max(1, int(size.width() * hh / max(1, size.height()))) \
                    if size.isValid() and size.height() > 0 else width * 2
                reader2.setScaledSize(QSize(ww, hh))
                img2 = reader2.read()
                if not img2.isNull():
                    scaled = QPixmap.fromImage(img2)
            x = max(0, (scaled.width() - width) // 2)
            y = max(0, (scaled.height() - height) // 2)
            return scaled.copy(x, y, min(width, scaled.width()), min(height, scaled.height()))
    except Exception:
        pass
    return None
