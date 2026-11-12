# -*- coding: utf-8 -*-
"""VPK v1/v2 目录树解析（只读）。

只需要目录树做分类与提取 addoninfo.txt / missions/*.txt，不解包内容。
已知格式要点：
  - 头部 12 字节（v2 为 28 字节）：Signature=0x55AA1234, Version, TreeSize
  - 目录树三层：扩展名 -> 目录 -> 文件名，null 结尾；空串结束该层；单个空格 " " 占位表示该层为空
  - 条目 18 字节：CRC(u32) PreloadBytes(u16) ArchiveIndex(u16) Offset(u32) Length(u32) Terminator=0xFFFF(u16)
    Length==0 表示整个文件内容都在 preload 中；ArchiveIndex==0x7FFF 表示数据紧跟目录树之后
  - 多卷：xxx_dir.vpk 是索引，xxx_NNN.vpk 是数据分卷
  - 个别 VPK 使用「空串复用上一条目字符串」的优化，采用两次解析（严格/宽松）自校验
"""
import os
import struct

VPK_MAGIC = 0x55AA1234
ARCHIVE_INLINE = 0x7FFF

V1_HEADER = 12
V2_HEADER = 28


class VpkError(Exception):
    pass


class VpkEntry(object):
    __slots__ = ("path", "crc", "preload", "archive_index", "offset", "length")

    def __init__(self, path, crc, preload, archive_index, offset, length):
        self.path = path                # 归一化路径，含扩展名，'/' 分隔
        self.crc = crc
        self.preload = preload          # bytes（可能为空）
        self.archive_index = archive_index
        self.offset = offset
        self.length = length

    @property
    def size(self):
        return len(self.preload) + self.length


class VpkDir(object):
    """一个 _dir.vpk 的解析结果。"""

    def __init__(self, path):
        self.path = path                # _dir.vpk 绝对路径
        self.version = 1
        self.entries = {}               # lower_path -> VpkEntry
        self.tree_size = 0

    def paths(self):
        return list(self.entries.keys())

    def find(self, path):
        return self.entries.get(path.lower())

    # ---------- 文件内容读取（小文件用，如 txt） ----------
    def read_file(self, path):
        entry = self.find(path)
        if entry is None:
            return None
        if entry.length == 0:
            return entry.preload
        data = bytearray(entry.preload)
        base = os.path.splitext(self.path)[0]  # 去掉 _dir.vpk
        if entry.archive_index == ARCHIVE_INLINE:
            with open(self.path, "rb") as f:
                f.seek(V1_HEADER + self.tree_size + entry.offset)
                data += f.read(entry.length)
        else:
            part = "%s_%03d.vpk" % (base, entry.archive_index)
            if not os.path.isfile(part):
                raise VpkError("缺少分卷: " + os.path.basename(part))
            with open(part, "rb") as f:
                f.seek(entry.offset)
                data += f.read(entry.length)
        return bytes(data)


def _read_cstr(buf, pos):
    end = buf.index(b"\x00", pos)
    return buf[pos:end].decode("utf-8", errors="replace"), end + 1


def _parse_tree(tree, header_size, repeat_mode):
    """解析目录树。repeat_mode=False：空串结束该层；True：空串复用上一字符串（宽松模式）。
    返回 entries 列表 [(ext, dir, name, entry元组)]；解析异常抛出。"""
    entries = []
    pos = 0
    n = len(tree)
    last = ["", "", ""]
    while True:
        ext, pos = _read_cstr(tree, pos)
        if ext == "":
            if repeat_mode:
                ext = last[0]
            else:
                break
        if ext == " ":
            ext = ""
        last[0] = ext
        while True:
            dpath, pos = _read_cstr(tree, pos)
            if dpath == "":
                if repeat_mode:
                    dpath = last[1]
                else:
                    break
            if dpath == " ":
                dpath = ""
            last[1] = dpath
            while True:
                fname, pos = _read_cstr(tree, pos)
                if fname == "":
                    if repeat_mode:
                        fname = last[2]
                    else:
                        break
                if fname == " ":
                    fname = ""
                last[2] = fname
                if pos + 18 > n:
                    raise VpkError("条目越界")
                crc, preload, arc, off, ln, term = struct.unpack("<IHHIIH", tree[pos:pos + 18])
                if term != 0xFFFF:
                    raise VpkError("条目终止符错误")
                pos += 18
                if preload:
                    if pos + preload > n:
                        raise VpkError("preload 越界")
                    pre = bytes(tree[pos:pos + preload])
                    pos += preload
                else:
                    pre = b""
                entries.append((ext, dpath, fname, crc, pre, arc, off, ln))
                # 文件名循环继续
            # 目录循环继续
        # 扩展名循环继续
        if not repeat_mode:
            pass
    return entries, pos


def parse_vpk_dir(path):
    """解析 _dir.vpk。返回 VpkDir；格式不符抛 VpkError。"""
    with open(path, "rb") as f:
        head = f.read(V2_HEADER)
        if len(head) < V1_HEADER:
            raise VpkError("文件过小")
        sig, version, tree_size = struct.unpack("<III", head[:12])
        if sig != VPK_MAGIC:
            raise VpkError("魔数不符")
        if version not in (1, 2):
            raise VpkError("不支持的版本 %d" % version)
        header_size = V1_HEADER if version == 1 else V2_HEADER
        f.seek(header_size)
        tree = f.read(tree_size)
        if len(tree) < tree_size:
            raise VpkError("目录树不完整")

    vpk = VpkDir(path)
    vpk.version = version
    vpk.tree_size = tree_size

    last_err = None
    for repeat_mode in (False, True):
        try:
            raw_entries, consumed = _parse_tree(tree, header_size, repeat_mode)
            if consumed != tree_size:
                raise VpkError("目录树长度不匹配 (consumed %d / %d)" % (consumed, tree_size))
        except (VpkError, ValueError, struct.error) as e:
            last_err = e
            continue
        for ext, dpath, fname, crc, pre, arc, off, ln in raw_entries:
            full = ((dpath + "/") if dpath else "") + fname + (("." + ext) if ext else "")
            entry = VpkEntry(full, crc, pre, arc, off, ln)
            vpk.entries[full.lower()] = entry
        return vpk
    raise VpkError(str(last_err))


def vpk_parts(path):
    """给定集合内任一 vpk 文件路径，返回整组文件（_dir + 全部数据分卷）。"""
    base, name = os.path.split(path)
    if not name.lower().endswith(".vpk"):
        return [path]
    stem = name[:-4]
    low = stem.lower()
    if low.endswith("_dir"):
        dir_path = path
        stem = stem[:-4]
    else:
        idx = stem.rfind("_")
        if idx > 0 and len(stem) - idx - 1 == 3 and stem[idx + 1:].isdigit():
            cand = os.path.join(base, stem[:idx] + "_dir.vpk")
            if os.path.isfile(cand):
                dir_path = cand
                stem = stem[:idx]
            else:
                return [path]  # 孤儿分卷，按单文件处理
        else:
            dir_path = os.path.join(base, stem + "_dir.vpk")
            if not os.path.isfile(dir_path):
                return [path]  # 单文件 vpk
    parts = [dir_path]
    i = 0
    while True:
        part = os.path.join(base, "%s_%03d.vpk" % (stem, i))
        if os.path.isfile(part):
            parts.append(part)
            i += 1
        else:
            break
    return parts


def parse_keyvalues(text):
    """解析 addoninfo.txt / mission txt 为嵌套 dict（值均为字符串，重复键保留第一个）。"""
    tokens = _tokenize(text)
    pos = [0]

    def parse_block():
        obj = {}
        while pos[0] < len(tokens):
            kind, val = tokens[pos[0]]
            if kind == "}":
                pos[0] += 1
                return obj
            if kind == "str":
                if pos[0] + 1 < len(tokens):
                    nkind, nval = tokens[pos[0] + 1]
                    if nkind == "{":
                        pos[0] += 2
                        obj[val] = parse_block()
                        continue
                    if nkind == "str":
                        if val not in obj:
                            obj[val] = nval
                        pos[0] += 2
                        continue
                pos[0] += 1
            else:
                pos[0] += 1
        return obj

    return parse_block()


def _tokenize(text):
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
            if j > i:
                tokens.append(("str", text[i:j]))
            i = j if j > i else i + 1
    return tokens


def extract_addoninfo(vpk):
    """读取 addoninfo.txt，返回 dict 或 None。"""
    try:
        data = vpk.read_file("addoninfo.txt")
    except (VpkError, OSError):
        return None
    if not data:
        return None
    text = data.decode("utf-8", errors="replace")
    kv = parse_keyvalues(text)
    info = kv.get("AddonInfo")
    return info if isinstance(info, dict) else (kv if kv else None)


def extract_mission(vpk):
    """在 missions/*.txt 中找战役 mission 文件。
    返回 (mission_dict, mission_path) 或 (None, None)。"""
    mission_path = None
    for lower, entry in vpk.entries.items():
        if lower.startswith("missions/") and lower.endswith(".txt"):
            mission_path = entry.path
            break
    if mission_path is None:
        return None, None
    try:
        data = vpk.read_file(mission_path)
    except (VpkError, OSError):
        return None, None
    if not data:
        return None, None
    kv = parse_keyvalues(data.decode("utf-8", errors="replace"))
    mission = kv.get("mission")
    if not isinstance(mission, dict):
        mission = kv if kv else None
    return mission, mission_path
