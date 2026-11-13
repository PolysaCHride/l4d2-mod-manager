# -*- coding: utf-8 -*-
"""7-Zip / WinRAR discovery, extraction commands, and portable installation."""
import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from urllib.parse import quote, urljoin, urlparse

import requests

from . import app_paths

DOWNLOAD_PAGE = "https://www.7-zip.org/download.html"
PATH_EXECUTABLES = ("7z.exe", "7zz.exe", "WinRAR.exe", "rar.exe")


class ArchiverError(Exception):
    pass


class ArchiverNotFoundError(ArchiverError):
    pass


@dataclass(frozen=True)
class ArchiverInfo:
    path: str
    kind: str
    source: str = ""

    def extract_command(self, archive, dest_dir):
        if self.kind == "winrar":
            return [self.path, "x", "-ibck", "-y", "--",
                    archive, dest_dir + os.sep]
        if self.kind == "rar":
            return [self.path, "x", "-o+", "-y", "--",
                    archive, dest_dir + os.sep]
        return [self.path, "x", "-y", "-o" + dest_dir, "--", archive]


def _kind_for_path(path):
    name = os.path.basename(path).casefold()
    if name == "winrar.exe":
        return "winrar"
    if name == "rar.exe":
        return "rar"
    if name in ("7z.exe", "7zz.exe"):
        return "7z"
    return ""


def _valid(info):
    return bool(info and info.kind and os.path.isfile(info.path))


def from_path(path, source="manual"):
    """Validate an explicitly selected archiver executable."""
    if not path:
        return None
    info = ArchiverInfo(
        os.path.abspath(path),
        _kind_for_path(path),
        source,
    )
    return info if _valid(info) else None


def bundled_candidates(resource_root=None):
    root = resource_root or app_paths.resource_root()
    return (
        os.path.join(root, "7zip", "7z.exe"),
        os.path.join(root, "third_party", "7zip", "7z.exe"),
    )


def _registry_locations():
    locations = []
    try:
        import winreg
    except ImportError:
        return locations

    keys = (
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\7-Zip"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\7-Zip"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\7-Zip"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\7zFM.exe"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\7zFM.exe"),
    )
    for hive, key_name in keys:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                for value_name in ("InstallLocation", "", "Path"):
                    try:
                        value, _kind = winreg.QueryValueEx(key, value_name)
                    except OSError:
                        continue
                    if not isinstance(value, str) or not value.strip():
                        continue
                    value = os.path.expandvars(value.strip().strip('"'))
                    if os.path.isfile(value):
                        locations.append(value)
                        locations.append(
                            os.path.join(os.path.dirname(value), "7z.exe"))
                    else:
                        locations.append(os.path.join(value, "7z.exe"))
        except OSError:
            continue
    return locations


def installed_candidates():
    paths = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env_name)
        if not base:
            continue
        paths.extend((
            os.path.join(base, "7-Zip", "7z.exe"),
            os.path.join(base, "WinRAR", "WinRAR.exe"),
            os.path.join(base, "Programs", "7-Zip", "7z.exe"),
        ))
    paths.extend((
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        r"C:\Program Files\WinRAR\WinRAR.exe",
        r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
    ))
    paths.extend(_registry_locations())

    result = []
    seen = set()
    for path in paths:
        normalized = os.path.normpath(path)
        key = normalized.casefold()
        if key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def find_archiver(remembered_path="", resource_root=None, installed_paths=None,
                  path_lookup=None, require=False):
    """Find in bundled, remembered, installed, then PATH order."""
    groups = []
    groups.extend((path, "bundled") for path in bundled_candidates(resource_root))
    if remembered_path:
        groups.append((remembered_path, "remembered"))
    installed = installed_candidates() if installed_paths is None else installed_paths
    groups.extend((path, "installed") for path in installed)

    for path, source in groups:
        info = ArchiverInfo(os.path.abspath(path), _kind_for_path(path), source)
        if _valid(info):
            return info

    lookup = path_lookup or shutil.which
    for name in PATH_EXECUTABLES:
        path = lookup(name)
        if not path:
            continue
        info = ArchiverInfo(os.path.abspath(path), _kind_for_path(path), "path")
        if _valid(info):
            return info

    if require:
        raise ArchiverNotFoundError("未找到可用的 7-Zip 或 WinRAR 解压组件")
    return None


def select_windows_installer(page_html):
    """Read the official download page and return its current x64 MSI URL."""
    match = re.search(
        r'href=["\']([^"\']*?7z[0-9.]+-x64\.msi)["\']',
        page_html,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ArchiverError("无法从 7-Zip 官方下载页找到 x64 安装包")
    url = urljoin(DOWNLOAD_PAGE, html.unescape(match.group(1)))
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    official_host = host in ("7-zip.org", "www.7-zip.org", "sourceforge.net")
    official_github = (
        host == "github.com"
        and parsed.path.startswith("/ip7z/7zip/releases/download/")
    )
    if not official_host and not official_github:
        raise ArchiverError("7-Zip 下载地址不是官方域名")
    return url


def _report(progress, percent, text):
    if progress:
        progress(int(percent), str(text))


def _download_file(url, destination, progress=None):
    _report(progress, 5, "正在连接 7-Zip 官方下载站…")
    with requests.get(
            url, stream=True, timeout=(15, 60),
            headers={"User-Agent": "L4D2-Mod-Manager"}) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        with open(destination, "wb") as target:
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                target.write(chunk)
                received += len(chunk)
                if total:
                    percent = 8 + min(55, received * 55 // total)
                else:
                    percent = min(63, 8 + received // (256 * 1024))
                _report(progress, percent, "正在下载 7-Zip 组件…")
    if not os.path.isfile(destination) or os.path.getsize(destination) < 1024:
        raise ArchiverError("下载的 7-Zip 安装包不完整")


def release_digest_from_html(page_html, filename):
    """Extract the digest GitHub displays next to a release asset."""
    pattern = (
        r'href=["\'][^"\']*/%s["\'][\s\S]{0,5000}?'
        r'sha256:([0-9a-f]{64})'
    ) % re.escape(filename)
    match = re.search(pattern, page_html, flags=re.IGNORECASE)
    return match.group(1).casefold() if match else ""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path, expected):
    actual = sha256_file(path)
    if not expected or actual.casefold() != expected.casefold():
        raise ArchiverError("7-Zip 安装包 SHA-256 校验失败")


def _github_release_asset(url):
    parsed = urlparse(url)
    match = re.fullmatch(
        r"/ip7z/7zip/releases/download/([^/]+)/([^/]+)",
        parsed.path,
        flags=re.IGNORECASE,
    )
    if (parsed.hostname or "").casefold() != "github.com" or not match:
        return None
    return match.group(1), match.group(2)


def _fetch_release_digest(installer_url):
    asset = _github_release_asset(installer_url)
    if not asset:
        return ""
    tag, filename = asset
    page_url = (
        "https://github.com/ip7z/7zip/releases/expanded_assets/"
        + quote(tag, safe="")
    )
    try:
        response = requests.get(
            page_url, timeout=(15, 30),
            headers={"User-Agent": "L4D2-Mod-Manager"})
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ArchiverError("无法读取 7-Zip 官方发布校验值: %s" % exc) from exc
    digest = release_digest_from_html(response.text, filename)
    if not digest:
        raise ArchiverError("7-Zip 官方发布页未提供安装包 SHA-256")
    return digest


def _verify_authenticode(path):
    script = (
        "$sig = Get-AuthenticodeSignature -LiteralPath '%s'; "
        "[pscustomobject]@{"
        "Status=$sig.Status.ToString(); "
        "Subject=if ($sig.SignerCertificate) "
        "{$sig.SignerCertificate.Subject} else {''}"
        "} | ConvertTo-Json -Compress"
    ) % path.replace("'", "''")
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-EncodedCommand", encoded],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ArchiverError("无法校验 7-Zip 安装包签名: %s" % exc) from exc
    try:
        result = json.loads((proc.stdout or "").strip())
    except (TypeError, ValueError) as exc:
        raise ArchiverError("无法读取 7-Zip 安装包签名信息") from exc
    if proc.returncode != 0 or result.get("Status") != "Valid":
        raise ArchiverError("7-Zip 安装包数字签名校验失败")
    return result.get("Subject") or ""


def _verify_download(installer_url, path):
    expected = _fetch_release_digest(installer_url)
    if expected:
        verify_sha256(path, expected)
        return "sha256"
    _verify_authenticode(path)
    return "authenticode"


def _extract_msi(msi_path, destination):
    os.makedirs(destination, exist_ok=True)
    if '"' in msi_path or '"' in destination:
        raise ArchiverError("7-Zip 安装路径包含无效字符")
    command = (
        'msiexec.exe /a "%s" /qn TARGETDIR="%s"'
        % (msi_path, destination)
    )
    try:
        proc = subprocess.run(
            command,
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ArchiverError("无法执行 7-Zip 安装包: %s" % exc) from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[-200:]
        raise ArchiverError("7-Zip 安装包解包失败：%s" % (detail or proc.returncode))


def install_portable_7zip(dest_dir, progress=None):
    """Download the verified official MSI and extract a portable full component."""
    _report(progress, 2, "正在获取 7-Zip 最新版本信息…")
    try:
        response = requests.get(
            DOWNLOAD_PAGE, timeout=(15, 30),
            headers={"User-Agent": "L4D2-Mod-Manager"})
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ArchiverError("无法访问 7-Zip 官方下载页: %s" % exc) from exc
    installer_url = select_windows_installer(response.text)

    parent = os.path.dirname(os.path.abspath(dest_dir))
    os.makedirs(parent, exist_ok=True)
    work = tempfile.mkdtemp(prefix=".7zip_", dir=parent)
    try:
        msi_path = os.path.join(work, "7zip-x64.msi")
        _download_file(installer_url, msi_path, progress)
        _report(progress, 66, "正在校验 7-Zip 官方 SHA-256…")
        _verify_download(installer_url, msi_path)
        _report(progress, 72, "正在安全解包 7-Zip 组件…")
        extracted = os.path.join(work, "extracted")
        _extract_msi(msi_path, extracted)

        source_dir = ""
        for root, _dirs, files in os.walk(extracted):
            if any(name.casefold() == "7z.exe" for name in files):
                source_dir = root
                break
        if not source_dir:
            raise ArchiverError("7-Zip 安装包内未找到 7z.exe")
        if not os.path.isfile(os.path.join(source_dir, "7z.dll")):
            raise ArchiverError("7-Zip 安装包缺少完整的 7z.dll")

        _report(progress, 84, "正在安装内置 7-Zip 组件…")
        os.makedirs(dest_dir, exist_ok=True)
        for root, _dirs, files in os.walk(source_dir):
            relative = os.path.relpath(root, source_dir)
            target_root = dest_dir if relative == "." else os.path.join(dest_dir, relative)
            os.makedirs(target_root, exist_ok=True)
            for name in files:
                shutil.copy2(os.path.join(root, name),
                             os.path.join(target_root, name))

        exe = os.path.join(dest_dir, "7z.exe")
        info = ArchiverInfo(exe, "7z", "downloaded")
        if not _valid(info):
            raise ArchiverError("7-Zip 组件安装完成后无法使用")
        _report(progress, 100, "7-Zip 组件已安装")
        return info
    finally:
        shutil.rmtree(work, ignore_errors=True)
