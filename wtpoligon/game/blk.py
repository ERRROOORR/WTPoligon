"""BLK War Thunder: бинарный формат (из vromfs), текстовый формат (чтение и запись), общее дерево.

Дерево: Block(name, params=[(имя, тип, значение)], blocks=[Block]).
Типы и значения:
  t  str        i  int (32)     i64 int (64)    r  float (float32)    b  bool
  p2/p3/p4  tuple[float]        ip2/ip3/ip4  tuple[int]
  c  tuple(r, g, b, a) байты    m  tuple из 4 tuple[float]*3
Порядок параметров и блоков внутри блока сохраняется отдельно (в бинарном формате параметры всегда идут перед
блоками, в текстовом могут чередоваться — для сравнения деревьев это не важно).
"""
import decimal
import struct
import threading

import zstandard

TYPE_CODES = {1: 't', 2: 'i', 3: 'r', 4: 'p2', 5: 'p3', 6: 'p4', 7: 'ip2', 8: 'ip3',
              9: 'b', 10: 'c', 11: 'm', 12: 'i64', 13: 'ip4'}

BIN_FAT = 1        # свои имена внутри файла
BIN_FAT_ZSTD = 2
BIN_SLIM = 3       # имена в общей карте имён архива (?nm)
BIN_SLIM_ZSTD = 4
BIN_SLIM_ZSTD_DICT = 5  # zstd со словарём архива (*.dict)


class Block:
    __slots__ = ('name', 'params', 'blocks')

    def __init__(self, name=None, params=None, blocks=None):
        self.name = name
        self.params = params if params is not None else []
        self.blocks = blocks if blocks is not None else []

    def get(self, key, default=None):
        for k, _t, v in self.params:
            if k == key:
                return v
        return default

    def block(self, name):
        return next((b for b in self.blocks if b.name == name), None)

    def __repr__(self):
        return 'Block(%r, %d params, %d blocks)' % (self.name, len(self.params), len(self.blocks))


# ---------------------------------------------------------------- бинарный формат

def _uleb(b, p):
    r = s = 0
    while True:
        x = b[p]
        p += 1
        r |= (x & 0x7F) << s
        if x < 0x80:
            return r, p
        s += 7


def parse_name_table(b, p=0):
    cnt, p = _uleb(b, p)
    size, p = _uleb(b, p)
    names = b[p:p + size].split(b'\0')[:cnt]
    return [n.decode('utf-8', 'surrogateescape') for n in names], p + size


def parse_name_map_file(nm_file: bytes) -> list:
    """Файл '?nm' архива: 8 байт хэша имён + 32 байта хэша словаря + zstd-кадр с таблицей имён."""
    data = zstandard.ZstdDecompressor().decompressobj().decompress(nm_file[40:])
    return parse_name_table(data)[0]


def _parse_body(b, shared_names):
    # тело начинается с числа собственных имён: >0 — таблица имён внутри файла (FAT), 0 — общая карта (SLIM)
    own_cnt, p = _uleb(b, 0)
    if own_cnt > 0:
        names, p = parse_name_table(b, 0)
    elif shared_names is None:
        raise ValueError('файлу нужна карта имён архива')
    else:
        names = shared_names
    blocks_cnt, p = _uleb(b, p)
    params_cnt, p = _uleb(b, p)
    pdata_size, p = _uleb(b, p)
    pdata = b[p:p + pdata_size]
    p += pdata_size
    pinfo = []
    for _ in range(params_cnt):
        pinfo.append(b[p:p + 8])
        p += 8
    binfo = []
    for _ in range(blocks_cnt):
        nid, p = _uleb(b, p)
        pc, p = _uleb(b, p)
        bc, p = _uleb(b, p)
        first = 0
        if bc > 0:
            first, p = _uleb(b, p)
        binfo.append((nid, pc, bc, first))

    def cstr(off):
        return pdata[off:pdata.index(b'\0', off)].decode('utf-8', 'surrogateescape')

    def value(t, raw):
        v = struct.unpack('<I', raw)[0]
        if t == 1:
            return names[v & 0x7FFFFFFF] if v & 0x80000000 else cstr(v)
        if t == 2:
            return struct.unpack('<i', raw)[0]
        if t == 3:
            return struct.unpack('<f', raw)[0]
        if t == 4:
            return struct.unpack_from('<2f', pdata, v)
        if t == 5:
            return struct.unpack_from('<3f', pdata, v)
        if t == 6:
            return struct.unpack_from('<4f', pdata, v)
        if t == 7:
            return struct.unpack_from('<2i', pdata, v)
        if t == 8:
            return struct.unpack_from('<3i', pdata, v)
        if t == 9:
            return v != 0
        if t == 10:
            return (raw[2], raw[1], raw[0], raw[3])  # в файле BGRA
        if t == 11:
            f = struct.unpack_from('<12f', pdata, v)
            return (f[0:3], f[3:6], f[6:9], f[9:12])
        if t == 12:
            return struct.unpack_from('<q', pdata, v)[0]
        if t == 13:
            return struct.unpack_from('<4i', pdata, v)
        raise ValueError('неизвестный тип параметра %d' % t)

    objs = []
    pi = 0
    for nid, pc, bc, first in binfo:
        blk = Block(names[nid - 1] if nid > 0 else None)
        for _ in range(pc):
            raw = pinfo[pi]
            pi += 1
            nt = struct.unpack('<I', raw[:4])[0]
            t = nt >> 24
            blk.params.append((names[nt & 0xFFFFFF], TYPE_CODES[t], value(t, raw[4:])))
        objs.append((blk, bc, first))
    for blk, bc, first in objs:
        blk.blocks = [objs[first + i][0] for i in range(bc)]
    return objs[0][0] if objs else Block()


def is_binary(data: bytes) -> bool:
    return bool(data) and data[0] in (BIN_FAT, BIN_FAT_ZSTD, BIN_SLIM, BIN_SLIM_ZSTD, BIN_SLIM_ZSTD_DICT)


class BinaryReader:
    """Разбор бинарных BLK одного архива (общая карта имён и словарь zstd).

    zstd-объекты не делим между потоками: распаковка под блокировкой.
    """

    def __init__(self, name_map=None, zstd_dict: bytes = None):
        self._names = name_map
        self._dict = zstd_dict
        self._lock = threading.Lock()
        self._plain = zstandard.ZstdDecompressor()
        self._dctx = zstandard.ZstdDecompressor(dict_data=zstandard.ZstdCompressionDict(zstd_dict)) \
            if zstd_dict else None

    @classmethod
    def for_vromfs(cls, vf):
        nm = vf.name_map_file()
        return cls(parse_name_map_file(nm) if nm else None, vf.dict_file())

    def parse(self, data: bytes) -> Block:
        t = data[0]
        with self._lock:
            if t == BIN_FAT:
                return _parse_body(data[1:], None)
            if t == BIN_FAT_ZSTD:
                # 3 байта длины сжатых данных, дальше zstd с полным FAT-телом (без байта типа)
                size = int.from_bytes(data[1:4], 'little')
                return _parse_body(self._plain.decompressobj().decompress(data[4:4 + size]), None)
            if t in (BIN_SLIM, BIN_SLIM_ZSTD, BIN_SLIM_ZSTD_DICT) and self._names is None:
                raise ValueError('SLIM-файлу нужна карта имён архива')
            if t == BIN_SLIM:
                return _parse_body(data[1:], self._names)
            if t == BIN_SLIM_ZSTD:
                return _parse_body(self._plain.decompressobj().decompress(data[1:]), self._names)
            if t == BIN_SLIM_ZSTD_DICT:
                if self._dctx is None:
                    raise ValueError('файлу нужен словарь zstd архива')
                return _parse_body(self._dctx.decompressobj().decompress(data[1:]), self._names)
        raise ValueError('не бинарный BLK (тип %d)' % t)


# ---------------------------------------------------------------- текстовый формат: запись

def fmt_real(x: float) -> str:
    """Кратчайшая запись float32, которая читается обратно в то же значение. Без экспоненты."""
    f32 = struct.unpack('<f', struct.pack('<f', x))[0]
    for prec in range(1, 10):
        s = '%.*g' % (prec, f32)
        if struct.unpack('<f', struct.pack('<f', float(s)))[0] == f32:
            break
    if 'e' in s or 'E' in s:
        s = format(decimal.Decimal(s), 'f')
    if '.' not in s and 'inf' not in s and 'nan' not in s:
        s += '.0'
    return s


def quote(s: str) -> str:
    """Строка в кавычках. Экранирование Dagor BLK — символ '~' (~~, ~", ~n, ~t, ~r)."""
    s = s.replace('~', '~~').replace('"', '~"').replace('\n', '~n').replace('\t', '~t').replace('\r', '~r')
    return '"' + s + '"'


_IDENT_CHARS = frozenset('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.')


def _is_ident(k):
    # как dblk::is_ident_char в DagorEngine (без '~', чтобы не путать с экранированием); иначе имя в кавычках
    return bool(k) and all(c in _IDENT_CHARS for c in k)


def fmt_value(t, v) -> str:
    if t == 't':
        return quote(v)
    if t == 'b':
        return 'yes' if v else 'no'
    if t in ('i', 'i64'):
        return str(v)
    if t == 'r':
        return fmt_real(v)
    if t in ('p2', 'p3', 'p4'):
        return ', '.join(fmt_real(x) for x in v)
    if t in ('ip2', 'ip3', 'ip4', 'c'):
        return ', '.join(str(x) for x in v)
    if t == 'm':
        return '[' + ' '.join('[' + ', '.join(fmt_real(x) for x in r) + ']' for r in v) + ']'
    raise ValueError('тип %r' % t)


def to_text(blk: Block, indent: int = 0) -> str:
    """Один параметр на строку, отступ 2 пробела."""
    out = []
    _write(blk, indent, out)
    return '\n'.join(out) + '\n'


def _write(blk, ind, out):
    pad = '  ' * ind
    for k, t, v in blk.params:
        name = k if _is_ident(k) else quote(k)
        out.append('%s%s:%s=%s' % (pad, name, t, fmt_value(t, v)))
    for b in blk.blocks:
        name = b.name if _is_ident(b.name) else quote(b.name or '')
        if not b.params and not b.blocks:
            out.append('%s%s{}' % (pad, name))
            continue
        out.append('%s%s{' % (pad, name))
        _write(b, ind + 1, out)
        out.append('%s}' % pad)


# ---------------------------------------------------------------- текстовый формат: чтение

_TYPE_ALIASES = {'float': 'r', 'real': 'r', 'int': 'i', 'bool': 'b', 'text': 't', 'str': 't',
                 'float2': 'p2', 'float3': 'p3', 'float4': 'p4', 'int2': 'ip2', 'int3': 'ip3', 'int4': 'ip4',
                 'point2': 'p2', 'point3': 'p3', 'point4': 'p4', 'ipoint2': 'ip2', 'ipoint3': 'ip3',
                 'ipoint4': 'ip4', 'color': 'c', 'e3dcolor': 'c', 'tm': 'm', 'int64': 'i64'}


class TextError(ValueError):
    pass


class _Lexer:
    def __init__(self, s):
        self.s = s
        self.p = 0
        self.n = len(s)
        self.lenient = False

    def line(self):
        return self.s.count('\n', 0, self.p) + 1

    def err(self, msg):
        raise TextError('строка %d: %s' % (self.line(), msg))

    def skip_ws(self):
        s, n = self.s, self.n
        while self.p < n:
            c = s[self.p]
            if c in ' \t\r\n;':
                self.p += 1
            elif s.startswith('//', self.p):
                e = s.find('\n', self.p)
                self.p = n if e < 0 else e
            elif s.startswith('/*', self.p):
                e = s.find('*/', self.p + 2)
                if e < 0:
                    self.err('незакрытый комментарий')
                self.p = e + 2
            else:
                break

    def peek(self):
        self.skip_ws()
        return self.s[self.p] if self.p < self.n else ''

    def quoted(self):
        q = self.s[self.p]
        if self.s.startswith(q * 3, self.p):
            e = self.s.find(q * 3, self.p + 3)
            if e < 0:
                self.err('незакрытая строка')
            v = self.s[self.p + 3:e]
            self.p = e + 3
            return v
        out = []
        self.p += 1
        esc = {'n': '\n', 't': '\t', 'r': '\r'}
        while True:
            if self.p >= self.n:
                self.err('незакрытая строка')
            c = self.s[self.p]
            if c == '~' and self.p + 1 < self.n:
                d = self.s[self.p + 1]
                out.append(esc.get(d, d))
                self.p += 2
                continue
            if c == q:
                self.p += 1
                return ''.join(out)
            if c == '\n':
                self.err('перевод строки внутри строки')
            out.append(c)
            self.p += 1

    def name(self):
        self.skip_ws()
        if self.p < self.n and self.s[self.p] in '"\'':
            return self.quoted()
        st = self.p
        while self.p < self.n and self.s[self.p] not in ' \t\r\n:={}=;"\'':
            self.p += 1
        if st == self.p:
            self.err('ожидалось имя, найдено %r' % self.s[self.p:self.p + 10])
        return self.s[st:self.p]

    def raw_value(self):
        """Значение до конца строки (или до ; или }), без комментариев."""
        self.skip_inline_ws()
        st = self.p
        depth = 0
        while self.p < self.n:
            c = self.s[self.p]
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
            elif depth == 0 and (c in '\r\n;}' or self.s.startswith('//', self.p)):
                break
            self.p += 1
        return self.s[st:self.p].strip()

    def skip_inline_ws(self):
        while self.p < self.n and self.s[self.p] in ' \t':
            self.p += 1


def _floats(s, n, lx):
    parts = [x.strip() for x in s.split(',')]
    if len(parts) != n:
        lx.err('ожидалось %d чисел: %r' % (n, s))
    return tuple(float(x) for x in parts)


def _ints(s, n, lx):
    parts = [x.strip() for x in s.split(',')]
    if len(parts) != n:
        lx.err('ожидалось %d целых: %r' % (n, s))
    return tuple(int(x) for x in parts)


def _convert(t, s, lx):
    try:
        if t == 'i' or t == 'i64':
            return int(s)
        if t == 'r':
            return float(s)
        if t == 'b':
            low = s.lower()
            if low in ('yes', 'true', 'on', '1'):
                return True
            if low in ('no', 'false', 'off', '0'):
                return False
            lx.err('не bool: %r' % s)
        if t in ('p2', 'p3', 'p4'):
            return _floats(s, int(t[1]), lx)
        if t in ('ip2', 'ip3', 'ip4'):
            return _ints(s, int(t[2]), lx)
        if t == 'c':
            return _ints(s, 4, lx)
        if t == 'm':
            rows = [r.strip(' ,') for r in s.strip()[1:-1].replace(']', '').split('[') if r.strip(' ,')]
            if len(rows) != 4:
                lx.err('матрица: нужно 4 строки: %r' % s)
            return tuple(_floats(r, 3, lx) for r in rows)
    except ValueError as e:
        if isinstance(e, TextError):
            raise
        lx.err('значение %r не подходит к типу %s' % (s, t))
    lx.err('неизвестный тип %r' % t)


class BadValue(str):
    """Значение, которое не разбирается в свой тип (мягкий режим parse_text). line — строка файла."""

    def __new__(cls, raw, line):
        o = super().__new__(cls, raw)
        o.line = line
        return o


def parse_text(s: str, lenient: bool = False) -> Block:
    """Текстовый BLK -> дерево. Директивы include возвращаются как параметры с типом 'include'.

    lenient=True — как игра: неразбираемое значение не ошибка разбора, а BadValue; ошибкой оно станет только
    если параметр реально запишется (apply_patch)."""
    if s.startswith('﻿'):
        s = s[1:]
    lx = _Lexer(s)
    lx.lenient = lenient
    root = Block()
    _parse_into(lx, root, top=True)
    return root


def _parse_into(lx, blk, top):
    while True:
        c = lx.peek()
        if c == '':
            if not top:
                lx.err('не закрыт блок %r' % blk.name)
            return
        if c == '}':
            if top:
                lx.err('лишняя }')
            lx.p += 1
            return
        name = lx.name()
        if name == 'include' and lx.peek() in '"\'':
            blk.params.append(('include', 'include', lx.quoted()))
            continue
        c = lx.peek()
        if c == '{':
            lx.p += 1
            sub = Block(name)
            _parse_into(lx, sub, top=False)
            blk.blocks.append(sub)
        elif c == ':':
            lx.p += 1
            st = lx.p
            while lx.p < lx.n and lx.s[lx.p] not in '= \t':
                lx.p += 1
            t = lx.s[st:lx.p]
            if lx.peek() == '{':
                # блок с ':' в имени (шаблоны ECS: "name:array"), так печатает wt_ext_cli без кавычек
                lx.p += 1
                sub = Block(name + ':' + t)
                _parse_into(lx, sub, top=False)
                blk.blocks.append(sub)
                continue
            t = _TYPE_ALIASES.get(t, t)
            if lx.peek() != '=':
                lx.err('ожидалось = после %s:%s' % (name, t))
            lx.p += 1
            lx.skip_inline_ws()
            if t == 't':
                if lx.p < lx.n and lx.s[lx.p] in '"\'':
                    v = lx.quoted()
                else:
                    v = lx.raw_value()
            else:
                raw = lx.raw_value()
                if lx.lenient:
                    # как в Dagor: значение превращается в число только при записи параметра (см. apply_patch)
                    try:
                        v = _convert(t, raw, lx)
                    except TextError:
                        v = BadValue(raw, lx.line())
                else:
                    v = _convert(t, raw, lx)
            blk.params.append((name, t, v))
        else:
            lx.err('после %r ожидалось : или {' % name)


# ---------------------------------------------------------------- применение правок (@override и др.)
#
# Повторяет DataBlockParser::parse из DagorEngine (prog/engine/ioSys/dataBlock/blk_parser.cpp), см.
# docs/research/override_format.md. Нужен, чтобы до записи в игру посчитать итоговую машину и заранее увидеть
# каждую ошибку, которую игра напишет в лог.

class ApplyFatal(Exception):
    """Ошибка, на которой игра падает (FATAL ERROR BLK invalid …) — проверено логом 11.10 15:52."""


def _split_idx(name):
    """'Weapon[2]' -> ('Weapon', 1); без индекса -> 0; '[-1]' -> -2 (последний). Как get_array_idx: atoi(...) - 1."""
    p = name.find('[')
    if p < 0:
        return name, 0
    num = name[p + 1:].rstrip(']')
    try:
        n = int(num)
    except ValueError:
        n = 0
    return name[:p], n - 1


def _find(items, key, idx):
    """Индекс idx-го (с 0) элемента с именем key; idx < -1 — с конца (-2 = последний). Нет — None."""
    pos = [i for i, k in enumerate(items) if k == key]
    if idx >= 0:
        return pos[idx] if idx < len(pos) else None
    if idx < -1:
        return pos[idx + 1] if -(idx + 1) <= len(pos) else None
    return None  # [0] даёт idx = -1: игра такой элемент не найдёт


def _check_value(name, t, v):
    if isinstance(v, BadValue):
        raise ApplyFatal('BLK invalid %s (type %s) value in line %d: %r' % (name, t, v.line, str(v)))
    return v


def apply_patch(base: Block, patch: Block, log: list, path='') -> Block:
    """Применяет к base (меняя его) параметры и блоки patch по правилам Dagor. Ошибки игры — в log."""
    where = path or '/'
    for name, t, v in patch.params:
        if t == 'include':
            raise ValueError('include внутри правки не поддерживается: %s' % v)
        if not name.startswith('@'):
            base.params.append((name, t, _check_value(name, t, v)))
            continue
        op, _, target = name.partition(':')
        key, idx = _split_idx(target)
        keys = [p[0] for p in base.params]
        if op == '@override':
            i = _find(keys, key, idx)
            if i is None:
                log.append('cannot find param <%s> (ordinal %d) for override в %s' % (key, idx + 1, where))
            elif base.params[i][1] != t:
                log.append('different types (%s != %s) of param <%s> (ordinal %d) for override в %s'
                           % (t, base.params[i][1], key, idx + 1, where))
            else:
                base.params[i] = (key, t, _check_value(key, t, v))
        elif op == '@delete':
            i = _find(keys, key, idx)
            if i is None:
                log.append('cannot find param %s (ordinal %d) for deletion в %s' % (key, idx + 1, where))
            else:
                del base.params[i]
        elif op == '@delete-all':
            base.params = [p for p in base.params if p[0] != key]
        else:
            log.append('неизвестная директива параметра %s в %s (игра её пропустит)' % (name, where))
    for sub in patch.blocks:
        name = sub.name or ''
        if not name.startswith('@'):
            nb = Block(name)
            base.blocks.append(nb)
            apply_patch(nb, sub, log, path + '/' + name)
            continue
        op, _, target = name.partition(':')
        key, idx = _split_idx(target)
        keys = [b.name for b in base.blocks]
        if op == '@override':
            i = _find(keys, key, idx)
            if i is None:
                log.append('cannot find block <%s> (ordinal %d) for override в %s' % (key, idx + 1, where))
                apply_patch(Block(key), sub, [], '')  # игра разбирает содержимое во временный блок и выбрасывает
            else:
                apply_patch(base.blocks[i], sub, log, path + '/' + base.blocks[i].name)
        elif op == '@delete':
            i = _find(keys, key, idx)
            if i is None:
                log.append('cannot find block %s (ordinal %d) for deletion в %s' % (key, idx + 1, where))
            else:
                del base.blocks[i]
        elif op == '@delete-all':
            base.blocks = [b for b in base.blocks if b.name != key]
        elif op == '@clone-last':
            nb = _clone(base.blocks[-1]) if base.blocks else Block()
            nb.name = target
            base.blocks.append(nb)
            apply_patch(nb, sub, log, path + '/' + target)
        elif name == '@override-last':
            if base.blocks:
                apply_patch(base.blocks[-1], sub, log, path + '/' + str(base.blocks[-1].name))
            else:
                log.append('cannot find block for @override-last в %s' % where)
        elif name == '@delete-last':
            if base.blocks:
                base.blocks.pop()
            else:
                log.append('cannot find block for @delete-last в %s' % where)
        else:
            log.append('неизвестная директива блока %s в %s (игра её пропустит)' % (name, where))
    return base


def _clone(b: Block) -> Block:
    return Block(b.name, list(b.params), [_clone(x) for x in b.blocks])


def resolve_file(text: str, load_include, log: list) -> Block:
    """Файл правки (include стокового файла + директивы) -> итоговое дерево, как его увидит игра.

    load_include(path) -> Block стокового файла. include поддерживается только первой строкой (наш формат)."""
    patch = parse_text(text, lenient=True)
    base = Block()
    incs = [p for p in patch.params if p[1] == 'include']
    if incs:
        if patch.params[0][1] != 'include' or len(incs) > 1:
            raise ValueError('include поддерживается только один и первым')
        base = _clone(load_include(incs[0][2]))
        patch.params = patch.params[1:]
    return apply_patch(base, patch, log)


# ---------------------------------------------------------------- JSON датамайна (*.blkx)

def from_blkx(obj, name=None) -> Block:
    """Дерево из JSON публичного датамайна (gszabi99/War-Thunder-Datamine, `*.blkx`) — без игры.

    Выгрузка теряет часть BLK: повторённый параметр и Point2/3/4 оба выглядят списком чисел, тип восстанавливается
    по JSON (float -> r, int -> i, bool -> b, str -> t, 2–4 числа -> p2..p4/ip2..ip4, 4 списка по 3 числа -> m).
    Повторённый блок — список словарей. Годится для обзоров и dry-run; типы для записи сверять по бинарному файлу
    установленной игры (verify_override.py)."""
    blk = Block(name)
    for k, v in obj.items():
        if isinstance(v, dict):
            blk.blocks.append(from_blkx(v, k))
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            blk.blocks += [from_blkx(x, k) for x in v]
        elif isinstance(v, list) and any(isinstance(x, dict) for x in v):
            # параметр и блок с одним именем (bailout: seat:t="seat_01" … seat{part:t="seat_05"}) — одним списком
            for x in v:
                if isinstance(x, dict):
                    blk.blocks.append(from_blkx(x, k))
                else:
                    blk.params += [(k, t, y) for t, y in _blkx_params(x)]
        else:
            for t, x in _blkx_params(v):
                blk.params.append((k, t, x))
    return blk


def _blkx_scalar(v):
    if isinstance(v, bool):
        return 'b', v
    if isinstance(v, int):
        return 'i', v
    if isinstance(v, float):
        return 'r', v
    if isinstance(v, str):
        return 't', v
    raise ValueError('неизвестное значение в blkx: %r' % (v,))


def _blkx_params(v):
    if not isinstance(v, list):
        return [_blkx_scalar(v)]
    if (len(v) == 4 and all(isinstance(r, list) and len(r) == 3 for r in v)
            and all(isinstance(x, (int, float)) and not isinstance(x, bool) for r in v for x in r)):
        return [('m', tuple(tuple(float(x) for x in r) for r in v))]
    nums = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)
    if nums and 2 <= len(v) <= 4:
        if all(isinstance(x, int) for x in v):
            return [('ip%d' % len(v), tuple(v))]
        return [('p%d' % len(v), tuple(float(x) for x in v))]
    # иначе — повторённый параметр (в т. ч. список Point2)
    out = []
    for x in v:
        out += _blkx_params(x)
    return out
