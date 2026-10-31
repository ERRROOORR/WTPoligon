"""Запись/чтение текстового BLK. Правила взяты из DagorEngine (blk_parser.cpp, blk_serialize.cpp)."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from wtlib import blk as B  # noqa: E402


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class Quote(unittest.TestCase):
    def test_escape_is_tilde_not_backslash(self):
        self.assertEqual(B.quote('a"b'), '"a~"b"')
        self.assertEqual(B.quote('a~b'), '"a~~b"')
        self.assertEqual(B.quote('a\nb\tc'), '"a~nb~tc"')
        # обратный слэш — обычный символ (пути Windows)
        self.assertEqual(B.quote('C:\\x'), '"C:\\x"')

    def test_roundtrip_strings(self):
        for s in ['', 'простой', 'a"b\'c', '~~"', 'line1\nline2', 'tab\there', 'back\\slash\\"']:
            blk = B.Block(params=[('s', 't', s)])
            self.assertEqual(B.parse_text(B.to_text(blk)).get('s'), s)


class Reals(unittest.TestCase):
    def test_float32_exact_and_no_exponent(self):
        for x in [0.0, 1.0, -2.5, 0.1, 27320.177734375, 1e-20, -2.7755598776686065e-17, 3.4e38, 1.17549435e-38]:
            s = B.fmt_real(x)
            self.assertNotIn('e', s.lower(), s)
            self.assertIn('.', s)
            self.assertEqual(f32(float(s)), f32(x), s)


class Layout(unittest.TestCase):
    def test_one_param_per_line(self):
        blk = B.Block(params=[('a', 'r', 1.0), ('b', 'i', 2), ('c', 'b', True)],
                      blocks=[B.Block('sub', params=[('d', 'p3', (1.0, 2.0, 3.0))])])
        lines = B.to_text(blk).strip().split('\n')
        self.assertEqual(lines, ['a:r=1.0', 'b:i=2', 'c:b=yes', 'sub{', '  d:p3=1.0, 2.0, 3.0', '}'])

    def test_names_needing_quotes(self):
        blk = B.Block(params=[('@override:mass', 'r', 5.0)], blocks=[B.Block('x:array')])
        text = B.to_text(blk)
        self.assertIn('"@override:mass":r=5.0', text)
        self.assertIn('"x:array"{}', text)
        back = B.parse_text(text)
        self.assertEqual(back.params[0][0], '@override:mass')
        self.assertEqual(back.blocks[0].name, 'x:array')

    def test_all_types_roundtrip(self):
        blk = B.Block(params=[
            ('t', 't', 'x'), ('i', 'i', -7), ('i64', 'i64', 1 << 40), ('r', 'r', 0.5), ('b', 'b', False),
            ('p2', 'p2', (1.0, 2.0)), ('p4', 'p4', (1.0, 2.0, 3.0, 4.0)), ('ip3', 'ip3', (1, -2, 3)),
            ('ip4', 'ip4', (1, 2, 3, 4)), ('c', 'c', (255, 0, 10, 128)),
            ('m', 'm', ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (5.0, 6.0, 7.0)))])
        back = B.parse_text(B.to_text(blk))
        self.assertEqual(back.params, blk.params)


class Parse(unittest.TestCase):
    def test_semicolon_separates_params(self):
        b = B.parse_text('a:r=1; b:i=2\n')
        self.assertEqual(b.params, [('a', 'r', 1.0), ('b', 'i', 2)])

    def test_space_separated_params_on_one_line_is_error(self):
        # Dagor: значение без кавычек тянется до ; или конца строки -> "1 b:r=2" не число
        with self.assertRaises(B.TextError):
            B.parse_text('a:r=1 b:r=2\n')

    def test_backslash_quote_breaks_string(self):
        # так писала 4.7: \" не экранирует, строка закрывается раньше и дальше мусор
        with self.assertRaises(B.TextError):
            B.parse_text('a:t="x\\"y"\n')

    def test_writer_never_puts_comment_after_value(self):
        # значение без кавычек Dagor читает до // — пробелы перед комментарием могут попасть в значение
        import make_test_missions as M
        for rel, text in M.plan(M.STANDARD_CASES):
            for line in text.split('\n'):
                if '=' in line and '//' in line.split('=', 1)[1]:
                    val = line.split('=', 1)[1]
                    self.assertTrue(val.lstrip().startswith('"'), (rel, line))

    def test_include_and_comments(self):
        b = B.parse_text('include "#/develop/gameBase/x.blk"\n// c\n/* d */ "@override:m":r=2\n')
        self.assertEqual(b.params[0], ('include', 'include', '#/develop/gameBase/x.blk'))
        self.assertEqual(b.params[1], ('@override:m', 'r', 2.0))


if __name__ == '__main__':
    unittest.main()


class Blkx(unittest.TestCase):
    """JSON публичного датамайна (*.blkx) -> дерево (облачные проверки без игры)."""

    def test_types_blocks_and_repeats(self):
        root = B.from_blkx({
            'type': 'radar', 'rcs': 1.0, 'band': 8, 'active': True,
            'pos': [1.0, 2.0], 'ipos': [1, 2, 3],
            'tm': [[1, 0, 0], [0, 1, 0], [0, 0, 1], [5, 6, 7]],
            'band_list': [2, 3, 4, 5, 6],
            'transivers': {'mprf': {'range': 70000.0}},
            'sensor': [{'blk': 'a.blk'}, {'blk': 'b.blk'}],
        })
        self.assertEqual(root.params[:4], [('type', 't', 'radar'), ('rcs', 'r', 1.0), ('band', 'i', 8),
                                           ('active', 'b', True)])
        self.assertEqual(root.params[4], ('pos', 'p2', (1.0, 2.0)))
        self.assertEqual(root.params[5], ('ipos', 'ip3', (1, 2, 3)))
        self.assertEqual(root.params[6][1], 'm')
        self.assertEqual([p for p in root.params if p[0] == 'band_list'],
                         [('band_list', 'i', x) for x in (2, 3, 4, 5, 6)])
        self.assertEqual(root.block('transivers').block('mprf').get('range'), 70000.0)
        self.assertEqual([b.get('blk') for b in root.blocks if b.name == 'sensor'], ['a.blk', 'b.blk'])
        B.parse_text(B.to_text(root))  # то, что собрали, пишется и читается обратно
