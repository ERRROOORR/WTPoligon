"""Чтение контейнеров *.vromfs.bin War Thunder.

Сверено с wt_ext_cli v0.6.6 (режим Raw) побайтно на всех 8 архивах игры, см. docs/research/tools.md.
"""
import hashlib
import struct

import zstandard

# Обфускация первых и последних 16 байт сжатых данных (типы упаковки 0x10 и 0x30).
_PATT = (0xAA55AA55, 0xF00FF00F, 0xAA55AA55, 0x12481248)
_PATT_REV = (0x12481248, 0xAA55AA55, 0xF00FF00F, 0xAA55AA55)

PACK_ZSTD_OBFS_NOCHECK = 0x10
PACK_PLAIN = 0x20
PACK_ZSTD_OBFS = 0x30


def _xor16(buf, off, patt):
    for i in range(4):
        v = struct.unpack_from('<I', buf, off + i * 4)[0] ^ patt[i]
        struct.pack_into('<I', buf, off + i * 4, v)


def _deobfuscate(buf):
    n = len(buf)
    if n >= 16:
        _xor16(buf, 0, _PATT)
    if n >= 32:
        _xor16(buf, (n & 0x03FFFFFC) - 16, _PATT_REV)


class Header:
    __slots__ = ('magic', 'platform', 'size', 'packed_size', 'pack_type', 'version', 'data_offset')


def read_header(raw: bytes) -> Header:
    h = Header()
    h.magic = raw[:4]
    if h.magic not in (b'VRFs', b'VRFx'):
        raise ValueError('не vromfs: сигнатура %r' % h.magic)
    h.platform = raw[4:8]
    h.size, info = struct.unpack_from('<II', raw, 8)
    h.packed_size = info & 0x03FFFFFF
    h.pack_type = info >> 26
    h.version = None
    h.data_offset = 16
    if h.magic == b'VRFx':
        ext_size, _flags, ver = struct.unpack_from('<HHI', raw, 16)
        h.version = '%d.%d.%d.%d' % (ver >> 24, (ver >> 16) & 0xFF, (ver >> 8) & 0xFF, ver & 0xFF)
        h.data_offset += ext_size
    return h


def unpack_container(raw: bytes, check: bool = True) -> bytes:
    """Возвращает внутренний образ файловой системы."""
    h = read_header(raw)
    off = h.data_offset
    if h.pack_type == PACK_PLAIN or h.packed_size == 0:
        return raw[off:off + h.size]
    buf = bytearray(raw[off:off + h.packed_size])
    if h.pack_type in (PACK_ZSTD_OBFS, PACK_ZSTD_OBFS_NOCHECK):
        _deobfuscate(buf)
    elif h.pack_type != 0:
        raise ValueError('неизвестный тип упаковки 0x%x' % h.pack_type)
    data = zstandard.ZstdDecompressor().decompress(bytes(buf), max_output_size=h.size)
    if check and h.pack_type == PACK_ZSTD_OBFS:
        digest = raw[off + h.packed_size:off + h.packed_size + 16]
        if len(digest) == 16 and hashlib.md5(data).digest() != digest:
            raise ValueError('MD5 содержимого vromfs не совпал')
    return data


def list_files(fs: bytes) -> dict:
    """Внутренний образ -> {путь: байты}, порядок как в архиве."""
    names_off, names_cnt = struct.unpack_from('<II', fs, 0)
    data_off, data_cnt = struct.unpack_from('<II', fs, 16)
    if names_cnt != data_cnt:
        raise ValueError('vromfs: имён %d, а файлов %d' % (names_cnt, data_cnt))
    files = {}
    for i in range(names_cnt):
        p = struct.unpack_from('<Q', fs, names_off + i * 8)[0]
        raw_name = fs[p:fs.index(b'\0', p)]
        # служебный файл карты имён называется b'\xff?nm' — это не UTF-8
        name = raw_name.decode('latin-1') if raw_name[:1] == b'\xff' else raw_name.decode('utf-8')
        o, s = struct.unpack_from('<II', fs, data_off + i * 16)
        files[name] = fs[o:o + s]
    return files


class Vromfs:
    """Открытый архив: files — {путь как в архиве: байты}."""

    def __init__(self, path: str, check: bool = True):
        with open(path, 'rb') as f:
            raw = f.read()
        self.path = path
        self.header = read_header(raw)
        self.files = list_files(unpack_container(raw, check))
        self._lower = None

    def get(self, name: str):
        """Файл по пути без учёта регистра (в архиве пути в нижнем регистре)."""
        b = self.files.get(name)
        if b is None:
            if self._lower is None:
                self._lower = {k.lower(): k for k in self.files}
            k = self._lower.get(name.lower())
            b = self.files.get(k) if k else None
        return b

    def name_map_file(self):
        return next((b for n, b in self.files.items() if n.endswith('?nm')), None)

    def dict_file(self):
        return next((b for n, b in self.files.items() if n.endswith('.dict')), None)
