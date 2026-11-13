# -*- coding: utf-8 -*-
"""定位 Steam / L4D2 / 相关工具。"""
import os
import re

GAME_DIR_NAME = "Left 4 Dead 2"
L4D2_APPID = "550"


def get_steam_path():
    """从注册表读取 Steam 安装目录。"""
    import winreg
    for hive, sub in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
    ):
        try:
            with winreg.OpenKey(hive, sub) as k:
                val, _ = winreg.QueryValueEx(k, "SteamPath")
                p = os.path.normpath(val)
                if os.path.isdir(p):
                    return p
        except OSError:
            continue
        # HKLM 的键名可能是 InstallPath
        try:
            with winreg.OpenKey(hive, sub) as k:
                val, _ = winreg.QueryValueEx(k, "InstallPath")
                p = os.path.normpath(val)
                if os.path.isdir(p):
                    return p
        except OSError:
            continue
    return ""


def iter_library_paths(steam_path):
    """Steam 主目录 + libraryfolders.vdf 中列出的所有库目录。"""
    libs = []
    if steam_path and os.path.isdir(steam_path):
        libs.append(steam_path)
        vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            for m in re.finditer(r'"path"\s*"([^"]+)"', text):
                p = m.group(1).replace("\\\\", "\\")
                p = os.path.normpath(p)
                if p not in libs:
                    libs.append(p)
        except OSError:
            pass
    return libs


def is_game_dir(path):
    if not path:
        return False
    left4dead2 = os.path.join(path, "left4dead2")
    return os.path.isdir(os.path.join(left4dead2, "addons"))


def find_game_dir(explicit=""):
    """优先用用户显式设置，否则扫描所有 Steam 库。返回游戏根目录（含 left4dead2/）或空串。"""
    if explicit and is_game_dir(explicit):
        return explicit
    for lib in iter_library_paths(get_steam_path()):
        candidate = os.path.join(lib, "steamapps", "common", GAME_DIR_NAME)
        if is_game_dir(candidate):
            return candidate
    return ""


def find_steam_exe():
    steam = get_steam_path()
    if steam:
        exe = os.path.join(steam, "steam.exe")
        if os.path.isfile(exe):
            return exe
    return ""


def find_archiver():
    """Backward-compatible tuple wrapper around the shared discovery logic."""
    from . import archiver as archiver_core
    info = archiver_core.find_archiver()
    return (info.path, info.kind) if info else ("", "")


class GamePaths(object):
    """游戏路径派生集合。game_dir 为 'Left 4 Dead 2' 根目录。"""

    def __init__(self, game_dir):
        self.game_dir = game_dir
        self.left4dead2 = os.path.join(game_dir, "left4dead2")
        self.addons_dir = os.path.join(self.left4dead2, "addons")
        self.workshop_addons_dir = os.path.join(self.addons_dir, "workshop")
        self.addonlist_file = os.path.join(self.left4dead2, "addonlist.txt")
        self.game_exe = os.path.join(game_dir, "left4dead2.exe")

    def valid(self):
        return is_game_dir(self.game_dir)
