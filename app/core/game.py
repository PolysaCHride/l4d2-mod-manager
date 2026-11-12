# -*- coding: utf-8 -*-
"""游戏进程检测与启动。"""
import base64
import json
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


def open_workshop_page(item_id):
    os.startfile("steam://url/CommunityFilePage/" + str(item_id))  # noqa: S606


def open_folder(path):
    os.startfile(path)  # noqa: S606


def reveal_files(paths):
    """在资源管理器中打开首个文件所在目录，并同时选中同目录下的目标文件。"""
    files = []
    seen = set()
    for path in paths:
        path = os.path.abspath(os.fspath(path))
        key = os.path.normcase(path)
        if key not in seen and os.path.isfile(path):
            files.append(path)
            seen.add(key)
    if not files:
        return False

    folder = os.path.dirname(files[0])
    files = [path for path in files
             if os.path.normcase(os.path.dirname(path)) == os.path.normcase(folder)]
    payload = base64.b64encode(json.dumps(
        {"folder": folder, "files": files}, ensure_ascii=False).encode("utf-8")).decode("ascii")
    script = r"""
$ErrorActionPreference = 'Stop'
$payload = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String('%s')) | ConvertFrom-Json
$folderPath = [IO.Path]::GetFullPath([string]$payload.folder)
$filePaths = @($payload.files | ForEach-Object {
    [IO.Path]::GetFullPath([string]$_)
})
$shell = New-Object -ComObject Shell.Application
$shell.Explore($folderPath)
$window = $null
for ($attempt = 0; $attempt -lt 40 -and -not $window; $attempt++) {
    Start-Sleep -Milliseconds 50
    foreach ($candidate in @($shell.Windows())) {
        try {
            $path = $candidate.Document.Folder.Self.Path
            if ([string]::Equals([IO.Path]::GetFullPath([string]$path),
                                 $folderPath,
                                 [StringComparison]::OrdinalIgnoreCase)) {
                $window = $candidate
                break
            }
        } catch {
        }
    }
}
if (-not $window) {
    Start-Process -FilePath explorer.exe -ArgumentList @(
        ('/select,"{0}"' -f $filePaths[0]))
    exit
}
$folder = $shell.Namespace($folderPath)
foreach ($path in $filePaths) {
    $item = $folder.ParseName([IO.Path]::GetFileName($path))
    if ($item) {
        $window.Document.SelectItem($item, 1)
    }
}
""" % payload
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    powershell = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"),
        r"System32\WindowsPowerShell\v1.0\powershell.exe")
    try:
        subprocess.Popen(
            [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except (OSError, subprocess.SubprocessError):
        try:
            subprocess.Popen(
                ["explorer.exe", "/select," + files[0]],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True
        except (OSError, subprocess.SubprocessError):
            return False
