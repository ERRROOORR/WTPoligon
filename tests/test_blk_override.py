"""Правила @override/@delete/… — поведение DagorEngine blk_parser.cpp (docs/research/override_format.md)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from wtlib import blk as B  # noqa: E402

STOCK = '''
mass:r=100.0
name:t="stock"
Weapon{
  blk:t="gun_a.blk"
  bullets:i=40
}
Weapon{
  blk:t="gun_b.blk"
  bullets:i=10
}
Weapon{
  blk:t="gun_c.blk"
}
mod{
  effects{
    speed:r=1.0
  }
}
'''


def apply(patch_text):
    base = B.parse_text(STOCK)
    log = []
    B.apply_patch(base, B.parse_text(patch_text, lenient=True), log)
    return base, log


class Params(unittest.TestCase):
    def test_override_existing(self):
        b, log = apply('"@override:mass":r=5.0\n')
        self.assertEqual(b.get('mass'), 5.0)
        self.assertEqual(log, [])

    def test_override_missing_is_logged_and_skipped(self):
        b, log = apply('"@override:power":r=5.0\n')
        self.assertIsNone(b.get('power'))
        self.assertIn('cannot find param <power> (ordinal 1)', log[0])

    def test_override_wrong_type_is_logged_and_skipped(self):
        b, log = apply('"@override:mass":i=5\n')
        self.assertEqual(b.get('mass'), 100.0)
        self.assertIn('different types', log[0])

    def test_plain_param_is_appended_and_first_wins(self):
        # игра читает первый параметр с именем (DbUtils::find) — дубликат молча не действует
        b, log = apply('mass:r=5.0\n')
        self.assertEqual([v for k, _, v in b.params if k == 'mass'], [100.0, 5.0])
        self.assertEqual(b.get('mass'), 100.0)
        self.assertEqual(log, [])

    def test_plain_param_adds_missing(self):
        b, _ = apply('power:r=5.0\n')
        self.assertEqual(b.get('power'), 5.0)

    def test_delete_and_delete_all(self):
        b, log = apply('"@delete:name":t=""\n')
        self.assertIsNone(b.get('name'))
        b, log = apply('"@delete:nope":t=""\n')
        self.assertIn('for deletion', log[0])


class Blocks(unittest.TestCase):
    def test_index_is_one_based(self):
        b, log = apply('"@override:Weapon[2]"{\n"@override:bullets":i=99\n}\n')
        self.assertEqual([w.get('bullets') for w in b.blocks if w.name == 'Weapon'], [40, 99, None])
        self.assertEqual(log, [])

    def test_no_index_is_first(self):
        b, _ = apply('"@override:Weapon"{\n"@override:bullets":i=1\n}\n')
        self.assertEqual(b.blocks[0].get('bullets'), 1)

    def test_minus_one_is_last(self):
        b, log = apply('"@override:Weapon[-1]"{\nbullets:i=7\n}\n')
        self.assertEqual(b.blocks[2].get('bullets'), 7)
        self.assertEqual(log, [])

    def test_zero_index_never_found(self):
        _, log = apply('"@override:Weapon[0]"{\n"@override:bullets":i=1\n}\n')
        self.assertIn('cannot find block <Weapon> (ordinal 0)', log[0])

    def test_missing_block_is_logged_and_content_discarded(self):
        b, log = apply('"@override:Turret"{\nspeed:r=1.0\n}\n')
        self.assertIsNone(b.block('Turret'))
        self.assertIn('cannot find block <Turret>', log[0])

    def test_plain_block_appended(self):
        b, _ = apply('Weapon{\nblk:t="gun_d.blk"\n}\n')
        self.assertEqual([w.get('blk') for w in b.blocks if w.name == 'Weapon'][-1], 'gun_d.blk')

    def test_nested_override(self):
        b, log = apply('"@override:mod"{\n"@override:effects"{\n"@override:speed":r=3.0\n}\n}\n')
        self.assertEqual(b.block('mod').block('effects').get('speed'), 3.0)
        self.assertEqual(log, [])

    def test_delete_block_and_last(self):
        b, _ = apply('"@delete:Weapon[2]"{}\n')
        self.assertEqual([w.get('blk') for w in b.blocks if w.name == 'Weapon'], ['gun_a.blk', 'gun_c.blk'])
        b, _ = apply('"@delete-all:Weapon"{}\n')
        self.assertEqual([w.name for w in b.blocks], ['mod'])

    def test_clone_last(self):
        b, _ = apply('"@clone-last:mod2"{\n"@override:effects"{\n"@override:speed":r=9.0\n}\n}\n')
        self.assertEqual(b.block('mod').block('effects').get('speed'), 1.0)
        self.assertEqual(b.block('mod2').block('effects').get('speed'), 9.0)


class GameBehaviour(unittest.TestCase):
    """Случай из лога игры 11.10 15:52 (файл 4.7), см. tools/verify_override.py для сверки на настоящих файлах."""

    def test_bad_value_only_fatal_when_written(self):
        # несколько параметров в строке: если параметра нет — хвост молча выброшен, если есть — вылет игры
        _, log = apply('"@override:Weapon"{\n"@override:shotFreq":r=1.0 "@override:bullets":i=38\n}\n')
        self.assertIn('cannot find param <shotFreq>', log[0])
        with self.assertRaises(B.ApplyFatal):
            apply('"@override:Weapon"{\n"@override:bullets":i=38 "@override:blk":t="x"\n}\n')

    def test_resolve_file_with_include(self):
        stock = B.parse_text(STOCK)
        log = []
        res = B.resolve_file('include "#/develop/gameBase/gameData/x.blk"\n"@override:mass":r=1.0\n',
                             lambda p: stock, log)
        self.assertEqual(res.get('mass'), 1.0)
        self.assertEqual(stock.get('mass'), 100.0)  # сток не испорчен


if __name__ == '__main__':
    unittest.main()
