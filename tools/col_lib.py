# -*- coding: utf-8 -*-
"""Caves of Lore 汉化 · 资源读写核心库（打包版）。

与 workspace/tools/col_dialogue.py 同源（codec 部分逐字一致，改动需同步）：
- Unity 2022.3 序列化规则：逐字段 4 字节对齐；标量 bool 占 4 字节、数组元素 bool 1 字节；
  字符串 = int32 len + UTF-8 + 补零到 4；PPtr = int32 fileID + int64 pathID。
- 对象前缀：m_GameObject(12) + m_Enabled(1+3) + m_Script(12) + m_Name(string)。
- schema 来自 col_schemas.py（schema_gen.py 自动生成）。

本文件额外提供：对象解析/重序列化、字段路径 set、ID 方案（文件短名）。
"""
import struct

I32, F32, BOOL, STR, PPTR, VEC2, VEC3 = "i32", "f32", "bool", "str", "pptr", "vec2", "vec3"
VEC4, VEC6, I2, I3, U8 = "vec4", "vec6", "i2", "i3", "u8"
F64, C32 = "f64", "c32"
B8 = "b8"
ACURVE = "acurve"

FILES = ["resources.assets", "globalgamemanagers", "globalgamemanagers.assets"]
FILES += ["sharedassets%d.assets" % i for i in range(37)]
FILES += ["level%d" % i for i in range(37)]


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def i64(b, o):
    return int.from_bytes(b[o:o + 8], "little", signed=True)


def parse_string(buf, off):
    n = u32(buf, off)
    assert 0 <= n <= 1_000_000, "string len @%d: %d" % (off, n)
    s = buf[off + 4:off + 4 + n].decode("utf-8", "replace")
    end = off + 4 + n
    return s, end + (-end) % 4


def parse_monoscript(raw):
    try:
        s0, e0 = parse_string(raw, 0)
        s1, e1 = parse_string(raw, e0 + 20)
        s2, e2 = parse_string(raw, e1)
        s3, e3 = parse_string(raw, e2)
    except AssertionError:
        return None
    if e3 != len(raw):
        return None
    return s0, s2, s3, s1   # (name, ns, asm, cls)


def short_name(fn):
    if fn == "resources.assets":
        return "res"
    if fn == "globalgamemanagers.assets":
        return "gga"
    if fn == "globalgamemanagers":
        return "ggm"
    if fn.startswith("sharedassets"):
        return "sa" + fn[len("sharedassets"):-len(".assets")]
    if fn.startswith("level"):
        return "lv" + fn[len("level"):]
    return fn


class Str:
    __slots__ = ("v", "raw")

    def __init__(self, v, raw):
        self.v = v
        self.raw = raw


class R:
    __slots__ = ("b", "pos", "padlog")

    def __init__(self, buf, pos=0):
        self.b = buf
        self.pos = pos
        self.padlog = []

    def align4(self):
        n = (-self.pos) % 4
        if n:
            chunk = self.b[self.pos:self.pos + n]
            try:
                if chunk.strip(b"\x00"):
                    self.padlog.append((self.pos, bytes(chunk)))
            except Exception:
                pass
            self.pos += n

    def i32(self):
        self.align4()
        v = int.from_bytes(self.b[self.pos:self.pos + 4], "little", signed=True)
        self.pos += 4
        return v

    def f32(self):
        self.align4()
        v = struct.unpack_from("<f", self.b, self.pos)[0]
        self.pos += 4
        return v

    def byte(self):
        v = self.b[self.pos]
        self.pos += 1
        return v

    def pptr(self):
        fid = self.i32()
        pid = int.from_bytes(self.b[self.pos:self.pos + 8], "little", signed=True)
        self.pos += 8
        return (fid, pid)

    def string(self):
        self.align4()
        n = int.from_bytes(self.b[self.pos:self.pos + 4], "little")
        self.pos += 4
        raw = self.b[self.pos:self.pos + n]
        self.pos += n
        self.align4()
        try:
            v = raw.decode("utf-8")
        except UnicodeDecodeError:
            v = None
        return Str(v, raw)


def dec(t, r):
    if t == I32:
        return r.i32()
    if t == F32:
        return r.f32()
    if t == BOOL:
        r.align4()
        return r.byte()
    if t == B8:
        return r.byte()
    if t == STR:
        return r.string()
    if t == PPTR:
        return r.pptr()
    if t in (VEC2, VEC3, VEC4, VEC6):
        return [r.f32() for _ in range({VEC2: 2, VEC3: 3, VEC4: 4, VEC6: 6}[t])]
    if t in (I2, I3):
        return [r.i32() for _ in range(2 if t == I2 else 3)]
    if t == U8:
        r.align4()
        return r.byte()
    if t == F64:
        r.align4()
        v = struct.unpack_from("<d", r.b, r.pos)[0]
        r.pos += 8
        return v
    if t == C32:
        r.align4()
        v = int.from_bytes(r.b[r.pos:r.pos + 4], "little")
        r.pos += 4
        return v
    if t == ACURVE:
        r.align4()
        n = r.i32()
        assert 0 <= n <= 100000, "curve keys %d" % n
        keys = [[r.f32(), r.f32(), r.f32(), r.f32(), r.i32(), r.f32(), r.f32()]
                for _ in range(n)]
        pre = r.i32()
        post = r.i32()
        return [n, keys, pre, post]
    if isinstance(t, tuple):
        kind, sub = t
        if kind == "list":
            n = r.i32()
            assert 0 <= n <= 5_000_000, "list count @%d: %d" % (r.pos, n)
            return [dec(sub, r) for _ in range(n)]
        if kind == "struct":
            return {name: dec(ft, r) for name, ft in sub}
    raise ValueError("bad schema %r" % (t,))


class W:
    __slots__ = ("out",)

    def __init__(self):
        self.out = bytearray()

    def align4(self):
        self.out += b"\x00" * ((-len(self.out)) % 4)

    def write(self, b):
        self.out += b


def enc(t, w, v):
    if t == I32:
        w.align4()
        w.write(int(v).to_bytes(4, "little", signed=True))
    elif t == F32:
        w.align4()
        w.write(struct.pack("<f", v))
    elif t == BOOL:
        w.align4()
        w.write(bytes((int(v) & 0xFF,)))
    elif t == B8:
        w.write(bytes((int(v) & 0xFF,)))
    elif t == STR:
        w.align4()
        b = v.raw if v.raw is not None else (v.v or "").encode("utf-8")
        w.write(len(b).to_bytes(4, "little"))
        w.write(b)
        w.align4()
    elif t == PPTR:
        w.align4()
        w.write(int(v[0]).to_bytes(4, "little", signed=True))
        w.write(int(v[1]).to_bytes(8, "little", signed=True))
    elif t in (VEC2, VEC3, VEC4, VEC6):
        for f in v:
            enc(F32, w, f)
    elif t in (I2, I3):
        for x in v:
            enc(I32, w, x)
    elif t == U8:
        w.align4()
        w.write(bytes((int(v) & 0xFF,)))
    elif t == F64:
        w.align4()
        w.write(struct.pack("<d", v))
    elif t == C32:
        w.align4()
        w.write(int(v).to_bytes(4, "little"))
    elif t == ACURVE:
        n, keys, pre, post = v
        enc(I32, w, n)
        for k in keys:
            enc(F32, w, k[0]); enc(F32, w, k[1]); enc(F32, w, k[2]); enc(F32, w, k[3])
            enc(I32, w, k[4]); enc(F32, w, k[5]); enc(F32, w, k[6])
        enc(I32, w, pre)
        enc(I32, w, post)
    elif isinstance(t, tuple):
        kind, sub = t
        if kind == "list":
            w.align4()
            w.write(len(v).to_bytes(4, "little"))
            for e in v:
                enc(sub, w, e)
        elif kind == "struct":
            for name, ft in sub:
                enc(ft, w, v[name])
        else:
            raise ValueError(t)
    else:
        raise ValueError("bad schema %r" % (t,))


def parse_obj(raw, schema):
    """返回 (prefix_dict, fields)；要求恰好耗尽（允许 ≤3 零尾）。"""
    r = R(raw, 0)
    prefix = {
        "m_GameObject": r.pptr(),
        "m_Enabled": r.byte(),
    }
    r.align4()
    prefix["m_Script"] = r.pptr()
    prefix["m_Name"] = r.string()
    fields = dec(schema, r)
    tail = raw[r.pos:]
    assert len(tail) <= 3 and not tail.strip(b"\x00"), \
        "consume %d != %d (tail %d)" % (r.pos, len(raw), len(tail))
    return prefix, fields


def encode_obj(prefix, fields, schema):
    w = W()
    enc(PPTR, w, prefix["m_GameObject"])
    enc(BOOL, w, prefix["m_Enabled"])
    enc(PPTR, w, prefix["m_Script"])
    enc(STR, w, prefix["m_Name"])
    enc(schema, w, fields)
    out = bytes(w.out)
    # 对象 raw 末尾必须补零到 4 字节对齐（Unity 写的对象尾零 0-3 字节；
    # parse_obj 会丢弃它们，若不补回则改动对象丢尾部 padding → 游戏读崩。
    # 2026-10-14 实机定位：仅"带尾零"的对象（如 11712/11303）会触发）。
    if len(out) % 4:
        out += b"\x00" * (4 - len(out) % 4)
    return out


SEG_RE = None


def _segs(path):
    global SEG_RE
    if SEG_RE is None:
        import re
        SEG_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")
    out = []
    for m in SEG_RE.finditer(path):
        if m.group(1) is not None:
            out.append(m.group(1))
        else:
            out.append(int(m.group(2)))
    return out


def get_field(fields, path):
    cur = fields
    for s in _segs(path):
        cur = cur[s] if not isinstance(cur, dict) else cur.get(s)
        if cur is None:
            return None
    return cur


def set_string(fields, path, value):
    """把字段路径末端的 Str 设为 value（raw=None → 重编码）。返回旧值。"""
    segs = _segs(path)
    cur = fields
    for s in segs[:-1]:
        cur = cur[s] if not isinstance(cur, dict) else cur[s]
    last = segs[-1]
    obj = cur[last] if not isinstance(cur, dict) else cur[last]
    if not isinstance(obj, Str):
        raise TypeError("目标不是字符串：%s (%r)" % (path, type(obj)))
    old = obj.v
    obj.v = value
    obj.raw = None
    return old
