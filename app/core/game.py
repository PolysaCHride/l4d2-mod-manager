# -*- coding: utf-8 -*-
"""游戏进程检测与启动。"""
import os
import subprocess

APPID = "550"
GAME_EXE = "left4dead2.exe"


def is_l4d2_running():
    """字节级匹配进程名，避免控制台编码（GBK/UTF-8）差异问题。"""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq %s" % GAME_EXE, "/FO", "CSV", "/NH"],
            capture_output=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        data = (out.stdout or b"").lower()
        return GAME_EXE.lower().encode("ascii") in data
    except (OSError, subprocess.SubprocessError):
        return False


def launch_game(steam_exe=""):
    """经 Steam 启动游戏（保留用户的启动项）。"""
    os.startfile("steam://rungameid/" + APPID)  # noqa: S606


def launch_map(map_name, steam_exe=""):
    """一键进图：steam.exe -applaunch 550 +map <地图名>。"""
    if steam_exe and os.path.isfile(steam_exe):
        subprocess.Popen([steam_exe, "-applaunch", APPID, "+map", str(map_name)])
    else:
        os.startfile("steam://rungameid/" + APPID)  # noqa: S606


def open_workshop_page(item_id):
    os.startfile("steam://url/CommunityFilePage/" + str(item_id))  # noqa: S606


def open_folder(path):
    os.startfile(path)  # noqa: S606
