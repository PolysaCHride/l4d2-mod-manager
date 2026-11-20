# -*- coding: utf-8 -*-
"""把 Node 侧的契约测试挂进 unittest，使「一条命令跑全部契约」成立。

背景：
`tests/test_webui_contract.py` 只能验证 Python 侧（_to_mod 的输出字段集）。
`adapt()` 在前端 JS 里，Python 读不到它的行为 —— 那半边此前完全没有保护。

`tests/adapt_contract.js` 补上了 Node 侧。这个文件负责：

1. 调用 node 跑它，把失败如实传给 unittest；
2. **没有 node 时跳过而不是失败** —— 契约的 Python 那一半仍然有效，
   不该因为开发机没装 node 就让整套测试红掉。

运行：
    .venv/Scripts/python.exe -m unittest tests.test_adapt_contract_js -v
"""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tests" / "adapt_contract.js"


class TestAdaptContractJs(unittest.TestCase):
    """前端 adapt() 的字段契约（Node 侧执行）。"""

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if cls.node is None:
            raise unittest.SkipTest(
                "未找到 node，跳过前端契约测试（adapt_contract.js）")

    def test_script_exists(self):
        self.assertTrue(SCRIPT.is_file(), "缺少 tests/adapt_contract.js")

    def test_adapt_contract_passes(self):
        """adapt() 的字段集、单位换算、枚举一致性必须全部成立。

        失败时把 node 的 stdout/stderr 原样带出来 —— 这些断言的消息
        已经写清「期望什么 / 实际什么」，不要在 Python 侧再翻译一遍。
        """
        proc = subprocess.run(
            [self.node, str(SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(
            proc.returncode, 0,
            "adapt() 契约测试失败：\n" + output)

    def test_app_js_is_valid_syntax(self):
        """app.js / bridge.js 至少必须是合法 JS。

        语法错误在打包版里只表现为「界面白屏」，没有任何提示。
        """
        for name in ("app.js", "bridge.js", "events.js"):
            path = ROOT / "app" / "webui" / name
            proc = subprocess.run(
                [self.node, "--check", str(path)],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60)
            self.assertEqual(
                proc.returncode, 0,
                "%s 语法错误：\n%s" % (name, (proc.stdout or "") + (proc.stderr or "")))


if __name__ == "__main__":
    unittest.main()
