# -*- coding: utf-8 -*-
"""旧 PySide6 UI —— 保留作行为基准与功能参考，新架构不依赖此包。

⚠️ 不要在新代码里 import 本包。
⚠️ 未移植功能清单见 docs/LEGACY_UI.md。
⚠️ tests/test_main_window_helpers.py 仍依赖本包。

新 UI 在 app/webui/ + app/shell/，入口是 main_web.py。
本包是 5887 行的 QThread 版实现，用途：
  1. 作为 app/shell/tasks.py 的行为基准（重写时的对照物）
  2. 承载 6 个尚未移植的功能（搜索/预览下载/合集反查/订阅迁移/7zip安装/全量采纳）
"""
