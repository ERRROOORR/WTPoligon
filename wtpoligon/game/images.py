"""Картинки интерфейса игры (ui/atlases.vromfs.bin) → PNG для окна.

В установленной игре (2.59) иконки вооружения gameuiskin/* — .avif и .svg, картинки техники units/* — .ddsx
(текстура движка Dagor); в датамайне они уже переведены в .png. Здесь — чтение всех трёх видов:
  - svg — отдаётся как есть (Qt читает SVG сам);
  - avif — Pillow (≥ 11.3, с поддержкой AVIF) → PNG;
  - ddsx — заголовок DDSxHeader (32 байта: 'DDSx', d3dFormat, flags, w, h, levels, …, memSz, packedSz); способ
    сжатия — код в трёх старших битах flags (маска 0xE0000000): 0x2… zstd, 0x4… LZMA (7zip), 0x6… Oodle,
    0x8… zlib (у пользователя 26.10: units/*.ddsx — 0x60008011, Oodle); после
    распаковки — мипы DDS без заголовка: дописываем заголовок DDS и читаем первый (самый большой) уровень Pillow.
Ошибки не роняют окно: decode возвращает (None, причина) — её показывает run.bat icons.
"""
import glob
import io
import lzma
import os
import struct
import zlib

COMPR_MASK = 0xE0000000
FLG_ZSTD, FLG_7ZIP, FLG_OODLE, FLG_ZLIB = 0x20000000, 0x40000000, 0x60000000, 0x80000000
FLG_REV_MIP_ORDER = 0x40000
D3DFMT_A8R8G8B8, D3DFMT_X8R8G8B8, D3DFMT_A8 = 21, 22, 28
EXTS = ('.png', '.avif', '.svg', '.ddsx')     # в каком порядке искать файл картинки в архиве


def ddsx_header(data):
    """dict полей заголовка .ddsx или None."""
    if len(data) < 32 or data[:4] != b'DDSx':
        return None
    fmt, flags, w, h, levels, hq, depth, bpp, _q, mem, packed = struct.unpack_from('<4sIHHBBHHHII', data, 4)
    return {'format': fmt, 'flags': flags, 'w': w, 'h': h, 'levels': levels, 'hq': hq, 'depth': depth,
            'bpp': bpp, 'mem': mem, 'packed': packed}


_OODLE = {}


def oodle_dll(game_dir):
    """Библиотека Oodle игры: oo2core*.dll в папке игры или на 2 уровня глубже; None — нет."""
    found = sorted(glob.glob(os.path.join(game_dir or '', 'oo2core*.dll')))
    if not found and game_dir:
        for depth in ('*', os.path.join('*', '*')):
            found = sorted(glob.glob(os.path.join(game_dir, depth, 'oo2core*.dll')))
            if found:
                break
    return found[-1] if found else None


def _ooz(ooz, src, size):
    """ooz отказывает, если после потока есть лишние байты, а packedSz в .ddsx бывает выровнен нулями: пробуем
    как есть, затем без хвостовых нулей (возвращая их по одному — поток мог сам кончаться нулями)."""
    try:
        return ooz.decompress(src, size)
    except RuntimeError as first:
        core = src.rstrip(b'\0')
        for extra in range(len(src) - len(core)):
            try:
                return ooz.decompress(core + b'\0' * extra, size)
            except RuntimeError:
                pass
        raise first


def _oodle(src, size, game_dir):
    """Распаковка Oodle: открытый распаковщик ooz (пакет pyooz, requirements.txt), иначе библиотека игры
    oo2core*.dll, если она есть (в WarThunder 2.59 её нет — распаковщик встроен в exe игры)."""
    try:
        import ooz
    except ImportError:
        ooz = None
    if ooz is not None:
        return _ooz(ooz, bytes(src), size)
    import ctypes
    if game_dir not in _OODLE:
        path = oodle_dll(game_dir)
        if not path:
            raise RuntimeError('нет распаковщика Oodle: установите pyooz (pip install -r requirements.txt)')
        lib = ctypes.WinDLL(path)
        f = lib.OodleLZ_Decompress
        f.restype = ctypes.c_int64
        f.argtypes = [ctypes.c_char_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_int64, ctypes.c_int, ctypes.c_int,
                      ctypes.c_int, ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p,
                      ctypes.c_void_p, ctypes.c_int64, ctypes.c_int]
        _OODLE[game_dir] = f
    out = ctypes.create_string_buffer(size)
    n = _OODLE[game_dir](bytes(src), len(src), out, size, 0, 0, 0, None, 0, None, None, None, 0, 3)
    if n != size:
        raise RuntimeError('Oodle вернул %d байт вместо %d' % (n, size))
    return out.raw


def ddsx_payload(data, game_dir=None):
    """(заголовок, распакованные данные мипов)."""
    h = ddsx_header(data)
    if h is None:
        raise ValueError('не DDSx')
    body = data[32:32 + h['packed']] if h['packed'] else data[32:32 + h['mem']]
    c = h['flags'] & COMPR_MASK
    if not h['packed'] or not c:
        raw = body
    elif c == FLG_ZSTD:
        import zstandard
        raw = zstandard.ZstdDecompressor().decompress(body, max_output_size=h['mem'])
    elif c == FLG_ZLIB:
        raw = zlib.decompress(body)
    elif c == FLG_7ZIP:
        raw = _lzma(body)
    elif c == FLG_OODLE:
        raw = _oodle(body, h['mem'], game_dir)
    else:
        raise ValueError('неизвестное сжатие, флаги 0x%08x' % h['flags'])
    return h, raw


def _lzma(body):
    """7zip в Dagor — LZMA «alone»: 5 байт свойств + сама запись (без 8 байт размера) или формат .lzma."""
    try:
        return lzma.decompress(body, format=lzma.FORMAT_ALONE)
    except lzma.LZMAError:
        props = body[:5]
        filt = lzma._decode_filter_properties(lzma.FILTER_LZMA1, props)
        return lzma.decompress(body[5:], format=lzma.FORMAT_RAW, filters=[filt])


def _dds_header(fmt, w, h, linear):
    """Заголовок DDS (128 байт) для первого мипа: FourCC (DXT1/3/5, ATI1/2) или 32-битный ARGB."""
    caps, flags = 0x1000, 0x1 | 0x2 | 0x4 | 0x1000
    if fmt in (b'DXT1', b'DXT3', b'DXT5', b'ATI1', b'ATI2', b'BC4U', b'BC5U'):
        pf = struct.pack('<II4sIIIII', 32, 0x4, fmt, 0, 0, 0, 0, 0)
        flags |= 0x80000
    else:
        code = struct.unpack('<I', fmt)[0]
        if code not in (D3DFMT_A8R8G8B8, D3DFMT_X8R8G8B8):
            raise ValueError('формат текстуры %r не поддержан' % fmt)
        alpha = 0xFF000000 if code == D3DFMT_A8R8G8B8 else 0
        pf = struct.pack('<II4sIIIII', 32, 0x40 | (0x1 if alpha else 0), b'\0\0\0\0', 32, 0xFF0000, 0xFF00, 0xFF,
                         alpha)
        flags |= 0x8
    head = struct.pack('<IIIIIII', 124, flags, h, w, linear, 0, 1) + b'\0' * 44 + pf + struct.pack('<IIIII', caps,
                                                                                                  0, 0, 0, 0)
    return b'DDS ' + head


def _level0_size(fmt, w, h):
    if fmt in (b'DXT1', b'ATI1', b'BC4U'):
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 8
    if fmt in (b'DXT3', b'DXT5', b'ATI2', b'BC5U'):
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 16
    return w * h * 4


def ddsx_to_png(data, game_dir=None):
    from PIL import Image
    h, raw = ddsx_payload(data, game_dir)
    size = _level0_size(h['format'], h['w'], h['h'])
    if len(raw) < size:
        raise ValueError('мало данных: %d < %d' % (len(raw), size))
    level0 = raw[-size:] if h['flags'] & FLG_REV_MIP_ORDER else raw[:size]
    linear = size if h['format'][:3] in (b'DXT', b'ATI', b'BC4', b'BC5') else h['w'] * 4
    img = Image.open(io.BytesIO(_dds_header(h['format'], h['w'], h['h'], linear) + level0))
    out = io.BytesIO()
    img.convert('RGBA').save(out, 'PNG')
    return out.getvalue()


def avif_to_png(data):
    from PIL import Image
    out = io.BytesIO()
    Image.open(io.BytesIO(data)).convert('RGBA').save(out, 'PNG')
    return out.getvalue()


def decode(data, ext, game_dir=None):
    """(байты PNG или SVG, '') или (None, причина)."""
    try:
        if ext == '.png' or ext == '.svg':
            return data, ''
        if ext == '.avif':
            return avif_to_png(data), ''
        if ext == '.ddsx':
            return ddsx_to_png(data, game_dir), ''
    except Exception as e:  # noqa: BLE001 — картинка необязательна, причину покажет run.bat icons
        return None, '%s: %s' % (type(e).__name__, e)
    return None, 'неизвестный формат ' + ext
