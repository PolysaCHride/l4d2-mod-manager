# -*- coding: utf-8 -*-
"""旧 PySide6 UI —— **ARCHIVED 2026-11-21：仅供查阅，不再维护、不再发版。**

新界面（`app/webui/` + `app/shell/`，入口 `main_web.py`）是唯一发布路径。
本包原地保留，原因有三：
  1. 它是 `app/shell/tasks.py` 的行为基准（重写时逐行对照过）
  2. 承载 6 个未移植功能的**领域知识**（搜索/预览下载/合集反查/订阅迁移/7zip安装/全量采纳）
  3. `tests/test_main_window_helpers.py` 仍依赖它

取回完整可发版的旧界面：`git checkout archive/legacy-ui-2026-11-21`
（`build_release.ps1 -Target legacy` 仍能构建，但会先打印警告，不保证可用。）

⚠️ 不要在新代码里 import 本包；不要删除、不要修改（除非是修归档注释本身）。
"""
