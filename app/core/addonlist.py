# -*- coding: utf-8 -*-
"""left4dead2/addonlist.txt 的读写。

格式为 KeyValues：根键 "AddonList"，条目形如 "文件名.vpk" "1"/"0"，
条目顺序即加载优先级（越靠前越高）。工坊条目可能带 "workshop\\xxx.vpk" 前缀。
外部程序需在游戏关闭时写入。
"""
import collections
import os
import shutil

ROOT_KEY = "AddonList"


class AddonList(object):
    """有序条目容器。entries: OrderedDict[key(str) -> value(str，通常 "1"/"0")]"""

    def __init__(self):
        self.entries = collections.OrderedDict()

    # ---------- 解析 ----------
    @classmethod
    def load(cls, path):
        al = cls()
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError:
            return al
        text = raw.decode("utf-8", errors="replace")
        al.entries = _parse_keyvalues(text)
        return al

    # ---------- 查询 / 修改 ----------
    def get(self, key, default="0"):
        return self.entries.get(key, default)

    def is_enabled(self, key):
        return self.entries.get(key, "0").strip() == "1"

    def set(self, key, value):
        """设置条目值；已存在时保持原顺序，不存在时追加到末尾。"""
        if key in self.entries:
            self.entries[key] = value
        else:
            self.entries[key] = value

    def remove(self, key):
        self.entries.pop(key, None)

    def rename_key(self, old, new):
        """重命名键并尽量保持原位置（迁移 workshop\\x.vpk -> x.vpk 时用）。"""
        if old not in self.entries:
            return
        val = self.entries.pop(old)
        rebuilt = collections.OrderedDict()
        inserted = False
        for k, v in self.entries.items():
            if not inserted and k == new:
                rebuilt[new] = val
                rebuilt[k] = v
                inserted = True
            else:
                rebuilt[k] = v
        if not inserted:
            rebuilt[new] = val
        self.entries = rebuilt

    # ---------- 序列化 / 保存 ----------
    def serialize(self):
        lines = ['"%s"' % ROOT_KEY, "{"]
        for k, v in self.entries.items():
            lines.append('\t"%s"\t\t"%s"' % (k, v))
        lines.append("}")
        return "\n".join(lines) + "\n"

    def save(self, path):
        """原子保存：先写临时文件再替换，原文件备份为 .bak。"""
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.serialize())
        if os.path.exists(path):
            try:
                shutil.copy2(path, path + ".bak")
            except OSError:
                pass
        os.replace(tmp, path)


def _tokenize(text):
    """KeyValues 词法：返回 token 列表（带引号字符串去引号，花括号为独立 token）。"""
    tokens = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif c == '"':
            i += 1
            buf = []
            while i < n:
                ch = text[i]
                if ch == "\\" and i + 1 < n and text[i + 1] in ('"', "\\"):
                    buf.append(text[i + 1])
                    i += 2
                elif ch == '"':
                    i += 1
                    break
                else:
                    buf.append(ch)
                    i += 1
            tokens.append(("str", "".join(buf)))
        elif c == "{" or c == "}":
            tokens.append((c, c))
            i += 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n{}":
                j += 1
            tokens.append(("str", text[i:j]))
            i = j
    return tokens


def _parse_keyvalues(text):
    """只解析 AddonList 根节点内的平铺键值对，保持顺序，容忍多余/未知内容。"""
    tokens = _tokenize(text)
    entries = collections.OrderedDict()
    i, n = 0, len(tokens)
    # 找到根键
    while i < n and not (tokens[i][0] == "str" and tokens[i][1] == ROOT_KEY):
        i += 1
    while i < n and tokens[i][0] != "{":
        i += 1
    if i >= n:
        return entries
    i += 1
    while i < n and tokens[i][0] != "}":
        if tokens[i][0] == "str" and i + 1 < n and tokens[i + 1][0] == "str":
            entries[tokens[i][1]] = tokens[i + 1][1]
            i += 2
        else:
            i += 1
    return entries
