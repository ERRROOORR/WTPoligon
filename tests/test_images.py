"""Картинки игры (wtpoligon/game/images.py): .ddsx (zstd / zlib / LZMA / без сжатия, DXT1/DXT5/ARGB, обратный
порядок мипов), .avif → PNG. Файлы собираются здесь же: настоящих .ddsx в датамайне нет (там уже .png)."""
import io
import lzma
import os
import struct
import sys
import unittest
import zlib

import zstandard

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from wtpoligon.game import images as IMG  # noqa: E402

try:
    from PIL import Image, features
except ImportError:
    Image = None


def sample(w=16, h=8):
    img = Image.new('RGBA', (w, h), (255, 0, 0, 255))
    for x in range(w // 2, w):
        for y in range(h):
            img.putpixel((x, y), (0, 0, 255, 255))
    return img


def dds_level0(img, fmt):
    """Данные первого мипа DDS (без заголовка) через Pillow."""
    out = io.BytesIO()
    img.save(out, 'DDS', pixel_format=fmt)
    return out.getvalue()[128:]


def ddsx(fmt, w, h, payload, flags=0, compress=None):
    mem = len(payload)
    body = compress(payload) if compress else payload
    packed = len(body) if compress else 0
    head = b'DDSx' + struct.pack('<4sIHHBBHHHII', fmt, flags, w, h, 1, 0, 1, 0, 0, mem, packed)
    return head + body


@unittest.skipIf(Image is None, 'нет Pillow')
class TestImages(unittest.TestCase):
    def check_png(self, data):
        img = Image.open(io.BytesIO(data)).convert('RGBA')
        self.assertEqual(img.size, (16, 8))
        left, right = img.getpixel((1, 1)), img.getpixel((14, 1))
        self.assertGreater(left[0], 200)
        self.assertGreater(right[2], 200)

    def test_ddsx_compressions(self):
        dxt5 = dds_level0(sample(), 'DXT5')
        for flags, comp in ((0, None), (IMG.FLG_ZSTD, zstandard.ZstdCompressor().compress),
                            (IMG.FLG_ZLIB, zlib.compress),
                            (IMG.FLG_7ZIP, lambda b: lzma.compress(b, format=lzma.FORMAT_ALONE))):
            data = ddsx(b'DXT5', 16, 8, dxt5, flags, comp)
            png, err = IMG.decode(data, '.ddsx')
            self.assertEqual(err, '', hex(flags))
            self.check_png(png)

    def test_ddsx_dxt1_argb_and_mip_order(self):
        png, err = IMG.decode(ddsx(b'DXT1', 16, 8, dds_level0(sample(), 'DXT1'), IMG.FLG_ZSTD,
                                   zstandard.ZstdCompressor().compress), '.ddsx')
        self.assertEqual(err, '')
        self.check_png(png)
        bgra = sample().tobytes('raw', 'BGRA')
        png, err = IMG.decode(ddsx(struct.pack('<I', IMG.D3DFMT_A8R8G8B8), 16, 8, bgra), '.ddsx')
        self.assertEqual(err, '')
        self.check_png(png)
        small = b'\0' * 32                                       # меньший мип впереди, обратный порядок
        png, err = IMG.decode(ddsx(b'DXT5', 16, 8, small + dds_level0(sample(), 'DXT5'), IMG.FLG_REV_MIP_ORDER),
                              '.ddsx')
        self.assertEqual(err, '')
        self.check_png(png)

    def test_oodle_flag_as_in_game(self):
        """Заголовок units/f_15c_golden_eagle.ddsx у пользователя: DXT5 80×68, флаги 0x60008011 → Oodle."""
        dxt5 = dds_level0(sample(), 'DXT5')
        calls = []

        def fake(src, size, game_dir):
            calls.append((src, size, game_dir))
            return dxt5
        old, IMG._oodle = IMG._oodle, fake
        try:
            png, err = IMG.decode(ddsx(b'DXT5', 16, 8, dxt5, 0x60008011, lambda b: b'packed'), '.ddsx', 'C:/WT')
        finally:
            IMG._oodle = old
        self.assertEqual(err, '')
        self.check_png(png)
        self.assertEqual(calls, [(b'packed', len(dxt5), 'C:/WT')])

    def test_oodle_real_decoder(self):
        """Настоящий ooz (pyooz): несжатый блок Oodle (байт 0x4C — «без сжатия») внутри .ddsx с флагом Oodle."""
        import importlib.util
        if importlib.util.find_spec('ooz') is None:
            self.skipTest('нет pyooz')
        dxt5 = dds_level0(sample(), 'DXT5')
        png, err = IMG.decode(ddsx(b'DXT5', 16, 8, dxt5, 0x60008011, lambda b: bytes([0x4C, 0x0C]) + b), '.ddsx')
        self.assertEqual(err, '')
        self.check_png(png)
        # packedSz выровнен нулями после потока (как, видимо, в игре) — тоже читается
        png, err = IMG.decode(ddsx(b'DXT5', 16, 8, dxt5, 0x60008011,
                                   lambda b: bytes([0x4C, 0x0C]) + b + b'\0' * 11), '.ddsx')
        self.assertEqual(err, '')
        self.check_png(png)

    def test_bad_input_does_not_raise(self):
        png, err = IMG.decode(b'garbage', '.ddsx')
        self.assertIsNone(png)
        self.assertIn('DDSx', err)

    @unittest.skipUnless(Image is not None and features.check('avif'), 'Pillow без AVIF')
    def test_avif(self):
        out = io.BytesIO()
        sample().save(out, 'AVIF', quality=100)
        png, err = IMG.decode(out.getvalue(), '.avif')
        self.assertEqual(err, '')
        self.check_png(png)


if __name__ == '__main__':
    unittest.main()
