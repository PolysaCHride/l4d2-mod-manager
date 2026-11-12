# -*- coding: utf-8 -*-
"""Steam 创意工坊公开接口：元数据 / 在线搜索 / 合集解析 / 预览图下载。

均不需要 API Key：
  - POST ISteamRemoteStorage/GetPublishedFileDetails/v1 （批量元数据，≤100/次）
  - GET  steamcommunity.com/workshop/browse/ （HTML 搜索页，正则解析，容忍改版）
"""
import re
import threading

L4D2_APPID = 550
DETAILS_URL = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
BROWSE_URL = "https://steamcommunity.com/workshop/browse/?appid=%d&searchtext=%s&numperpage=%d&pagenum=%d"

_lock = threading.Lock()
_last_call = 0.0
_PROXY = ""
_AUTO_PROXY = None   # 自动探测到的本地代理（clash 等），None=未探测


def set_proxy(p):
    """设置可选的 HTTP 代理（如 http://127.0.0.1:7890），空串=自动探测。"""
    global _PROXY
    _PROXY = (p or "").strip()


def _detect_local_proxy():
    """探测常见本地代理端口（clash 7890 / 7897、v2ray 10809、socks 常见 1080）。"""
    import socket
    for port in (7890, 7897, 10809, 1080):
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.4)
            s.close()
            return "http://127.0.0.1:%d" % port
        except OSError:
            continue
    return ""


def _pick_proxy():
    """返回可用代理地址；代理优先（被墙域名直连会长时间超时，拒绝连接则秒失败回退直连）。"""
    global _AUTO_PROXY
    if _PROXY:
        return _PROXY
    if _AUTO_PROXY:
        return _AUTO_PROXY
    _AUTO_PROXY = _detect_local_proxy() or ""
    return _AUTO_PROXY


def _request_with_fallback(do, url, timeout):
    """do(proxy|None, url, timeout)。代理失败回退直连，直连失败再探代理。"""
    global _AUTO_PROXY
    p = _pick_proxy()
    if p:
        try:
            return do(p, url, timeout)
        except Exception:
            _AUTO_PROXY = ""   # 代理失效，本轮回退直连
    try:
        return do(None, url, timeout)
    except Exception:
        p = _detect_local_proxy()
        if p:
            _AUTO_PROXY = p
            return do(p, url, timeout)
        raise


def _http():
    """优先 requests，缺失时退回 urllib。返回 (get_fn, post_form_fn, get_bytes_fn)。"""
    try:
        import requests
        sess = requests.Session()

        def get(url, timeout=20):
            def do(p, u, t):
                proxies = {"http": p, "https": p} if p else None
                return sess.get(u, timeout=t, proxies=proxies).text
            return _request_with_fallback(do, url, timeout)

        def post_form(url, data, timeout=20):
            def do(p, u, t):
                proxies = {"http": p, "https": p} if p else None
                return sess.post(u, data=data, timeout=t, proxies=proxies).json()
            return _request_with_fallback(do, url, timeout)

        def get_bytes(url, timeout=30):
            def do(p, u, t):
                proxies = {"http": p, "https": p} if p else None
                return sess.get(u, timeout=t, proxies=proxies).content
            return _request_with_fallback(do, url, timeout)

        return get, post_form, get_bytes
    except ImportError:
        import json as _json
        import urllib.parse
        import urllib.request

        def _do_urllib(p, url, timeout):
            handler = urllib.request.ProxyHandler(
                {"http": p, "https": p} if p else urllib.request.getproxies())
            opener = urllib.request.build_opener(handler)
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 L4D2ModManager/1.0"})
            resp = opener.open(req, timeout=timeout)
            return resp, req

        def get(url, timeout=20):
            def do(p, u, t):
                resp, _req = _do_urllib(p, u, t)
                with resp:
                    return resp.read().decode("utf-8", errors="replace")
            return _request_with_fallback(do, url, timeout)

        def post_form(url, data, timeout=20):
            def do(p, u, t):
                body = urllib.parse.urlencode(data).encode("utf-8")
                handler = urllib.request.ProxyHandler(
                    {"http": p, "https": p} if p else urllib.request.getproxies())
                opener = urllib.request.build_opener(handler)
                req = urllib.request.Request(u, data=body, headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Mozilla/5.0 L4D2ModManager/1.0"})
                with opener.open(req, timeout=t) as resp:
                    return _json.loads(resp.read().decode("utf-8", errors="replace"))
            return _request_with_fallback(do, url, timeout)

        def get_bytes(url, timeout=30):
            def do(p, u, t):
                resp, _req = _do_urllib(p, u, t)
                with resp:
                    return resp.read()
            return _request_with_fallback(do, url, timeout)

        return get, post_form, get_bytes


def get_details(item_ids, proxy=""):
    """批量查询工坊物品详情。返回 [detail dict]（result!=1 的为失败项）。"""
    import time
    global _last_call
    ids = [str(i) for i in item_ids if str(i).strip()][:100]
    if not ids:
        return []
    data = {"itemcount": str(len(ids))}
    for i, wid in enumerate(ids):
        data["publishedfileids[%d]" % i] = wid
    with _lock:
        wait = 1.0 - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _get, post_form, _b = _http()
        try:
            resp = post_form(DETAILS_URL, data)
        finally:
            _last_call = time.time()
    out = []
    for d in resp.get("response", {}).get("publishedfiledetails", []):
        # Steam Web API 使用 consumer_app_id。兼容早期/非标准响应里的
        # consumer_appid，避免把 AppID 730 等非 L4D2 物品误当成本游戏模组。
        appid = d.get("consumer_app_id")
        if appid in (None, ""):
            appid = d.get("consumer_appid")
        try:
            appid = int(appid) if appid not in (None, "") else None
        except (TypeError, ValueError):
            pass
        d["consumer_app_id"] = appid
        if appid not in (None, 0, L4D2_APPID):
            d["result"] = -100
            d["reject_reason"] = "wrong_app_id"
        out.append(d)
    return out


def collection_children_map(collection_ids):
    """批量查询合集子项，返回 {合集 ID: [子项 ID]}。

    GetPublishedFileDetails 对部分合集只返回封面资源，不带 children；
    GetCollectionDetails 才是合集成员的可靠来源。
    """
    ids = []
    for value in collection_ids:
        wid = str(value)
        if wid.isdigit() and wid not in ids:
            ids.append(wid)
    if not ids:
        return {}

    out = {}
    _g, post_form, _b = _http()
    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]
        data = {"collectioncount": str(len(batch))}
        for i, wid in enumerate(batch):
            data["publishedfileids[%d]" % i] = wid
        resp = post_form(
            "https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/",
            data,
            timeout=25,
        )
        for detail in (resp.get("response") or {}).get("collectiondetails", []):
            wid = str(detail.get("publishedfileid") or "")
            if detail.get("result") != 1 or not wid.isdigit():
                continue
            out[wid] = [
                str(child.get("publishedfileid"))
                for child in (detail.get("children") or [])
                if str(child.get("publishedfileid") or "").isdigit()
            ]
    return out


def resolve_collection_details(details, fetch_map=None):
    """给缺少 children 的合集详情补上 GetCollectionDetails 返回的子项。"""
    if not details:
        return details
    fetch_map = fetch_map or collection_children_map
    candidates = []
    for detail in details:
        if detail.get("result") != 1 or collection_children(detail):
            continue
        wid = str(detail.get("publishedfileid") or "")
        if wid.isdigit() and wid not in candidates:
            candidates.append(wid)
    if not candidates:
        return details

    found = fetch_map(candidates)
    for detail in details:
        wid = str(detail.get("publishedfileid") or "")
        children = found.get(wid) or []
        if children:
            detail["children"] = [
                {
                    "publishedfileid": str(child_id),
                    "sortorder": index + 1,
                    "filetype": 0,
                }
                for index, child_id in enumerate(children)
            ]
    return details


def get_collection_children(col_id):
    """合集子物品列表。优先用详情里的 children 字段，缺失时走
    ISteamRemoteStorage/GetCollectionDetails（部分合集只有这个接口返回子物品）。"""
    col_id = str(col_id)
    details = get_details([col_id])
    d = details[0] if details else {}
    children = collection_children(d)
    if children:
        return children
    return collection_children_map([col_id]).get(col_id, [])


def extract_ids(text):
    """从文本（链接/ID 列表）提取 publishedfileid。"""
    ids = []
    for m in re.finditer(r"(?:filedetails/\?id=|id=|^|\s)(\d{5,15})", text):
        wid = m.group(1)
        if wid not in ids:
            ids.append(wid)
    return ids


def search_workshop(query, page=1, num=30, sort="text"):
    """在线搜索。sort: text=相关度, mostsub=订阅最多, mostrecent=最新。返回 (items, total_text)。"""
    import urllib.parse
    q = urllib.parse.quote(query or "")
    url = BROWSE_URL % (L4D2_APPID, q, num, page)
    if sort == "mostsub":
        url += "&browsefilter=mostsub"
    elif sort == "mostrecent":
        url += "&browsefilter=mostrecent"
    elif sort == "trend":
        url += "&browsefilter=trend"
    _get, _p, _b = _http()
    html = _get(url, timeout=20)
    return _parse_browse_html(html)


def _parse_browse_html(html):
    """解析浏览页。兼容经典 DOM；改版时退化为「链接 id + 标题」配对。"""
    items = []
    total_m = re.search(r'(\d[\d,]*)\s*(?:entries|个?条目|entries matching)', html)
    total_text = total_m.group(1) if total_m else ""

    blocks = re.split(r'class="workshopItem(?:\s|")', html)
    if len(blocks) > 1:
        for b in blocks[1:]:
            idm = re.search(r'filedetails/\?id=(\d+)', b)
            if not idm:
                continue
            tm = re.search(r'class="workshopItemTitle[^"]*"[^>]*>([^<]+)<', b)
            am = re.search(r'class="workshopItemAuthor[^"]*"[^>]*>(?:.*?By\s*)?([^<]+)<', b, re.S)
            im = re.search(r'src="(https://[^"]+(?:images\.steamusercontent|akamaihd)[^"]*)"', b)
            sm = re.search(r'workshopItemSubscriptionCount[^>]*>\s*([\d,]+)', b)
            items.append({
                "id": idm.group(1),
                "title": _clean(tm.group(1) if tm else ""),
                "author": _clean(am.group(1)) if am else "",
                "preview": im.group(1) if im else "",
                "subs": sm.group(1) if sm else "",
            })
    if not items:
        # 退化解析：id 与标题按出现顺序配对
        ids = re.findall(r'filedetails/\?id=(\d+)"', html)
        titles = re.findall(r'<div class="workshopItemTitle[^"]*"[^>]*>([^<]+)<', html)
        imgs = re.findall(r'(https://[^\s"]+(?:images\.steamusercontent|akamaihd)\.net/ugc-workshop[^\s"]+)',
                          html)
        for i, wid in enumerate(ids):
            if wid in [it["id"] for it in items]:
                continue
            items.append({
                "id": wid,
                "title": _clean(titles[i]) if i < len(titles) else "",
                "author": "",
                "preview": imgs[i] if i < len(imgs) else "",
                "subs": "",
            })
    # 去重保序
    seen, uniq = set(), []
    for it in items:
        if it["id"] not in seen:
            seen.add(it["id"])
            uniq.append(it)
    return uniq, total_text


def _clean(s):
    return re.sub(r"\s+", " ", s).strip()


def collection_children(detail):
    """从合集 detail 中提取子物品 id 列表（按 sortorder）。"""
    children = detail.get("children") or []
    out = []
    for c in children:
        wid = str(c.get("publishedfileid") or "")
        if wid.isdigit():
            out.append(wid)
    return out


def fetch_preview_bytes(url):
    if not url:
        return b""
    _g, _p, get_bytes = _http()
    try:
        return get_bytes(url, timeout=30)
    except Exception:
        return b""
