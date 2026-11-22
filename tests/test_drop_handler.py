# -*- coding: utf-8 -*-
"""Api.on_file_drop 的行为契约（不需要窗口）。

拖拽导入的路径由 Python 侧的 pywebview DOM 监听给出（见 main_web._arm_file_drop）：
WebView2 走 `postMessageWithAdditionalObjects('FilesDropped')`，传的是带 `.Path` 的
CoreWebView2File，pywebview 把它回填成事件里的 `pywebviewFullPath`。
这里只测**拿到路径之后**的分类与容错，窗口部分靠实机验证。
"""
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.shell.api import Api  # noqa: E402


class DropHandlerTests(unittest.TestCase):
    def setUp(self):
        self.api = Api()
        self.events = []
        self.api._emit = lambda t, p: self.events.append((t, p))
        self.tmp = tempfile.mkdtemp()

    def _file(self, name):
        p = os.path.join(self.tmp, name)
        with open(p, "wb") as f:
            f.write(b"x")
        return p

    def _event(self, *files):
        return {"dataTransfer": {"files": list(files)}}

    def test_collects_supported_paths(self):
        zip_path = self._file("a.zip")
        seven = self._file("b.7z")
        rar = self._file("c.rar")
        r = self.api.on_file_drop(self._event(
            {"name": "a.zip", "pywebviewFullPath": zip_path},
            {"name": "b.7z", "pywebviewFullPath": seven},
            {"name": "c.rar", "pywebviewFullPath": rar},
        ))
        self.assertTrue(r["ok"])
        self.assertEqual(r["paths"], [zip_path, seven, rar])
        self.assertEqual(r["rejected"], [])
        self.assertEqual(self.events[0][0], "files.dropped")
        self.assertEqual(self.events[0][1]["paths"], [zip_path, seven, rar])

    def test_rejects_unsupported_extensions(self):
        txt = self._file("readme.txt")
        r = self.api.on_file_drop(self._event(
            {"name": "readme.txt", "pywebviewFullPath": txt}))
        self.assertEqual(r["paths"], [])
        self.assertEqual(r["rejected"], ["readme.txt"])

    def test_missing_path_goes_to_rejected(self):
        """拿不到 pywebviewFullPath 的条目不能被静默丢掉。"""
        r = self.api.on_file_drop(self._event({"name": "ghost.zip"}))
        self.assertEqual(r["paths"], [])
        self.assertEqual(r["rejected"], ["ghost.zip"])

    def test_nonexistent_path_rejected(self):
        r = self.api.on_file_drop(self._event(
            {"name": "gone.zip",
             "pywebviewFullPath": os.path.join(self.tmp, "nope.zip")}))
        self.assertEqual(r["paths"], [])
        self.assertEqual(r["rejected"], ["gone.zip"])

    def test_empty_event_is_harmless(self):
        for ev in (None, {}, {"dataTransfer": None}, {"dataTransfer": {"files": None}}):
            r = self.api.on_file_drop(ev)
            self.assertTrue(r["ok"], ev)
            self.assertEqual(r["paths"], [])

    def test_extension_match_is_case_insensitive(self):
        upper = self._file("UPPER.ZIP")
        r = self.api.on_file_drop(self._event(
            {"name": "UPPER.ZIP", "pywebviewFullPath": upper}))
        self.assertEqual(r["paths"], [upper])


if __name__ == "__main__":
    unittest.main()
