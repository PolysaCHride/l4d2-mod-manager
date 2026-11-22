#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Release preflight: verify a v1.3 candidate WITHOUT building or pushing.

Checks (read-only unless noted):
  1. git state          — branch, remote, divergence, uncommitted changes, tags
  2. version numbers    — every place a version literal lives, must agree
  3. tests              — Python unittest + Node contract suite (temp-dir workaround
                          for the DSH workspace sandbox: tempfile.mkdtemp creates
                          directories with mode 0700, whose DACL inherits no rights
                          inside the workspace, so writes into them are denied)
  4. assets/docs        — files the README/CHANGELOG will reference must exist
  5. packaging          — spec + build script + 7-Zip + version_info consistency

Usage:
  .venv/Scripts/python.exe scripts/release_preflight.py [--version 1.3.0]

Exit code 0 = all checks pass, 1 = at least one FAIL.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

def _find_root(start):
    """从脚本所在目录向上找仓库根（含 .git 或 CHANGELOG.md 的那层）。"""
    d = os.path.abspath(start)
    for _ in range(6):
        if os.path.exists(os.path.join(d, "CHANGELOG.md")) and os.path.isdir(os.path.join(d, "app")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT = _find_root(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
NODE = shutil.which("node") or "node"

FAILS = []
WARNS = []
NOTES = []


def ok(msg):
    print("  ok   %s" % msg)


def fail(msg):
    FAILS.append(msg)
    print("  FAIL %s" % msg)


def warn(msg):
    WARNS.append(msg)
    print("  warn %s" % msg)


def note(msg):
    NOTES.append(msg)
    print("  ·    %s" % msg)


def section(title):
    print("\n== %s ==" % title)


def run(cmd, **kw):
    kw.setdefault("cwd", ROOT)
    kw.setdefault("stdout", subprocess.PIPE)
    kw.setdefault("stderr", subprocess.STDOUT)
    p = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", **kw)
    return p.returncode, p.stdout or ""


def read(path):
    with io.open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as f:
        return f.read()


# --------------------------------------------------------------------------- 1
def check_git():
    section("git")
    rc, out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = out.strip()
    ok("branch = %s" % branch) if rc == 0 else fail("git rev-parse failed")
    if branch != "main":
        warn("当前不在 main（%s）；推公开仓库前应回到 main" % branch)

    rc, out = run(["git", "status", "--porcelain"])
    dirty = [l for l in out.splitlines() if l.strip()]
    if dirty:
        warn("工作区有 %d 个未提交改动：" % len(dirty))
        for l in dirty:
            print("         %s" % l)
    else:
        ok("工作区干净")

    rc, out = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if rc == 0:
        upstream = out.strip()
        rc2, out2 = run(["git", "rev-list", "--left-right", "--count", "%s...HEAD" % upstream])
        if rc2 == 0:
            behind, ahead = (out2.split() + ["?", "?"])[:2]
            note("上游 %s：落后 %s / 领先 %s 个提交" % (upstream, behind, ahead))
            if int(ahead or 0) > 0:
                warn("本地有 %s 个未推送提交 —— 推送即公开" % ahead)
    else:
        warn("当前分支没有上游追踪")

    rc, out = run(["git", "tag", "-l"])
    tags = sorted(t for t in out.split() if t)
    ok("现有 tag：%s" % (", ".join(tags) or "(无)"))
    for t in tags:
        if re.match(r"^v?\d+\.\d+(\.\d+)?$", t) and t.lstrip("v").startswith("1.3"):
            warn("tag %s 已存在，v1.3 发布会冲突" % t)

    rc, out = run(["git", "rev-list", "--count", "HEAD"])
    note("总提交数 %s" % out.strip())


# --------------------------------------------------------------------------- 2
VERSION_SITES = [
    ("app/shell/api.py", r'APP_VERSION\s*=\s*"([^"]+)"'),
    ("app/ui/main_window.py", r'APP_VERSION\s*=\s*"([^"]+)"'),
    ("packaging/version_info.txt", r'StringStruct\("FileVersion",\s*"([^"]+)"'),
    ("packaging/version_info.txt", r'StringStruct\("ProductVersion",\s*"([^"]+)"'),
]


def check_versions(expected):
    section("版本号一致性（期望 %s）" % (expected or "任意，但必须一致"))
    found = {}
    for path, pattern in VERSION_SITES:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            warn("缺少 %s" % path)
            continue
        m = re.search(pattern, read(path))
        if not m:
            warn("%s 里没找到版本号（pattern %s）" % (path, pattern))
            continue
        found.setdefault(m.group(1), []).append(path)
    for v, paths in sorted(found.items()):
        note("v%s ← %s" % (v, ", ".join(sorted(set(paths)))))
    if len(found) > 1:
        fail("版本号不一致：%s" % ", ".join(sorted(found)))
    if expected and found and expected not in found:
        fail("期望 %s，实际 %s" % (expected, ", ".join(sorted(found))))
    if expected and found and expected in found:
        ok("全部站点都是 %s" % expected)

    changelog = read("CHANGELOG.md")
    m = re.search(r"^##\s*(?:V|v)?(\d+\.\d+(?:\.\d+)?)", changelog, re.M)
    if m:
        top = m.group(1)
        note("CHANGELOG 最新条目 v%s" % top)
        if expected and top != expected:
            warn("CHANGELOG 顶部是 v%s，与期望 %s 不一致（发布前应补上本次条目）" % (top, expected))
    else:
        warn("CHANGELOG.md 里没找到版本标题")


# --------------------------------------------------------------------------- 3
TEMP_HOOK = r'''
import os, tempfile
def _mkdtemp(suffix=None, prefix=None, dir=None):
    suffix = suffix or ""
    prefix = prefix or tempfile.gettempprefix()
    dir = dir or tempfile.gettempdir()
    name = os.path.join(dir, prefix + next(tempfile._get_candidate_names()) + suffix)
    os.makedirs(name, exist_ok=True)
    return os.path.abspath(name)
tempfile.mkdtemp = _mkdtemp
'''


def ensure_temp_hook():
    """The DSH workspace sandbox denies writes into dirs created with mode 0700."""
    hook_dir = os.path.join(ROOT, ".tmp", "pyhook")
    os.makedirs(hook_dir, exist_ok=True)
    path = os.path.join(hook_dir, "sitecustomize.py")
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(TEMP_HOOK)
    return hook_dir


def check_tests():
    section("测试")
    hook = ensure_temp_hook()
    env = dict(os.environ)
    env["PYTHONPATH"] = hook
    env["PYTHONIOENCODING"] = "utf-8"

    py = PY if os.path.exists(PY) else sys.executable
    rc, out = run([py, "-m", "unittest", "discover", "-s", "tests"], env=env)
    m = re.search(r"^Ran (\d+) tests", out, re.M)
    ran = m.group(1) if m else "?"
    if rc == 0 and "OK" in out:
        ok("Python unittest：%s 个全过" % ran)
    else:
        fail("Python unittest 失败（Ran %s）" % ran)
        tail = "\n".join(out.splitlines()[-40:])
        print(tail)

    rc, out = run([NODE, os.path.join("tests", "adapt_contract.js")])
    passed = len(re.findall(r"^\s+ok\s", out, re.M))
    if rc == 0 and "全部通过" in out:
        ok("Node 契约测试：%d 项全过" % passed)
    else:
        fail("Node 契约测试失败（%d 项通过）" % passed)
        print("\n".join(out.splitlines()[-40:]))

    # JS syntax
    rc, out = run([NODE, "--check", os.path.join("app", "webui", "app.js")])
    (ok if rc == 0 else fail)("app/webui/app.js 语法")


# --------------------------------------------------------------------------- 4
REQUIRED_ASSETS = [
    "docs/images/addon-status.webp",
    "docs/images/appearance-switch.webp",
    "docs/images/copy-workshop-link.webp",
    "docs/images/workshop-download.webp",
    "docs/images/route-mode.webp",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
]


def check_docs():
    section("文档与资源")
    for p in REQUIRED_ASSETS:
        if os.path.exists(os.path.join(ROOT, p)):
            ok(p)
        else:
            fail("README/文档引用的资源不存在：%s" % p)

    # references inside README must resolve
    if os.path.exists(os.path.join(ROOT, "README.md")):
        text = read("README.md")
        for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
            target = m.group(1).split()[0]
            if target.startswith(("http://", "https://", "#")):
                continue
            if not os.path.exists(os.path.join(ROOT, target)):
                fail("README 图片引用失效：%s" % target)
        for m in re.finditer(r"\[[^\]]+\]\(([^)#]+)\)", text):
            target = m.group(1).strip()
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if not os.path.exists(os.path.join(ROOT, target)):
                warn("README 链接目标不存在：%s" % target)

    # files that must never be committed / shipped
    for p in ("data/library.json", "data/settings.json"):
        rc, out = run(["git", "ls-files", "--error-unmatch", p])
        if rc == 0:
            fail("个人数据被 Git 跟踪：%s" % p)
        else:
            ok("%s 未入库" % p)


# --------------------------------------------------------------------------- 5
def check_packaging():
    section("打包")
    for p in ("L4D2ModManagerWeb.spec", "main_web.py", "build_release.ps1",
              "packaging/version_info.txt", "requirements.txt"):
        (ok if os.path.exists(os.path.join(ROOT, p)) else fail)("存在 %s" % p)

    z = os.path.join(ROOT, "third_party", "7zip", "7z.exe")
    if os.path.exists(z):
        rc, out = run([z])
        ver = re.search(r"7-Zip\s+([\d.]+)", out)
        ok("内嵌 7-Zip：%s" % (ver.group(1) if ver else "版本未知"))
    else:
        fail("third_party/7zip/7z.exe 缺失（发行包必须内嵌）")

    spec = read("L4D2ModManagerWeb.spec") if os.path.exists(os.path.join(ROOT, "L4D2ModManagerWeb.spec")) else ""
    if "7zip" in spec:
        ok("Web spec 打包 7-Zip")
    else:
        fail("Web spec 未引用 7zip")

    rel = os.path.join(ROOT, "release")
    if os.path.isdir(rel):
        entries = [e for e in os.listdir(rel) if not e.startswith(".")]
        note("release/ 现有 %d 个条目（构建产物不入库）" % len(entries))
    else:
        note("release/ 不存在（尚未构建）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="", help="期望版本号，如 1.3.0")
    args = ap.parse_args()

    print("release preflight — %s" % ROOT)
    check_git()
    check_versions(args.version)
    check_tests()
    check_docs()
    check_packaging()

    section("结论")
    if FAILS:
        print("  %d 项失败：" % len(FAILS))
        for f in FAILS:
            print("   - %s" % f)
    if WARNS:
        print("  %d 项警告：" % len(WARNS))
        for w in WARNS:
            print("   - %s" % w)
    if not FAILS:
        print("  可发布（打包与推送仍需手动执行）")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
