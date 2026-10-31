"""Round 33 binary archive and manifest regression checks."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from dxp_extract import SOURCE, build, parse  # noqa: E402
from dynmodel_extract import DEV, MODELS, block_records, build as build_descriptor, encode, unpack  # noqa: E402
from make_test_missions import round33_write  # noqa: E402
from wtpoligon import install  # noqa: E402
from wtpoligon.game.blk import Block  # noqa: E402


def repr_tree(block):
    return block.name, block.params, [repr_tree(child) for child in block.blocks]


class Round33(unittest.TestCase):
    @unittest.skipUnless(DEV.is_file(), 'Dev descriptor fixture is local only')
    def test_descriptor_preserves_chroma_and_leopard_materials(self):
        source = encode(Block(None, blocks=[Block('chroma_dome_dynmodel')]))
        result = build_descriptor(source, DEV.read_bytes())
        original_data, _ = unpack(source)
        result_data, root = unpack(result)
        self.assertEqual([b.name for b in root.blocks], ['chroma_dome_dynmodel', *MODELS])
        self.assertEqual(block_records(original_data)[1], block_records(result_data)[1])
        _, dev = unpack(DEV.read_bytes())
        for name in MODELS:
            self.assertEqual(repr_tree(root.block(name)), repr_tree(dev.block(name)))

    def test_descriptor_adoption_restores_foreign_bytes_and_guards_changes(self):
        with tempfile.TemporaryDirectory() as root:
            game, app = Path(root, 'game'), Path(root, 'manifest')
            rel = 'content/pkg_local/res/dynModelDesc.bin'
            full = game / rel
            full.parent.mkdir(parents=True)
            original, replacement = b'foreign Chroma bytes', b'our descriptor bytes'
            full.write_bytes(original)
            ok, _ = round33_write(str(game), [(rel, replacement)], str(app), dry_run=True)
            self.assertTrue(ok)
            self.assertEqual(full.read_bytes(), original)
            self.assertFalse(app.exists())
            ok, report = round33_write(str(game), [(rel, replacement)], str(app))
            self.assertTrue(ok, report)
            self.assertEqual(full.read_bytes(), replacement)
            man = install.load_manifest(str(app))
            self.assertEqual(man['restores'][rel]['hash'], install.sha(original))
            self.assertEqual((app / man['restores'][rel]['backup']).read_bytes(), original)
            full.write_bytes(b'changed after installation')
            install.remove(str(game), str(app))
            self.assertEqual(full.read_bytes(), b'changed after installation')
            self.assertIn(rel, install.load_manifest(str(app))['files'])
            full.write_bytes(replacement)
            install.remove(str(game), str(app))
            self.assertEqual(full.read_bytes(), original)

    @unittest.skipUnless(SOURCE.is_file(), 'Dev DxP2 fixture is local only')
    def test_extracted_textures_keep_original_payloads(self):
        source = SOURCE.read_bytes()
        selected = {n: (d, p) for n, d, _, p in parse(source) if n.startswith('leopard_2a8_')}
        result = {n: (d, p) for n, d, _, p in parse(build(source))}
        self.assertEqual(len(result), 12)
        self.assertEqual(result, selected)

    def test_binary_manifest_and_hash_guarded_remove(self):
        with tempfile.TemporaryDirectory() as root:
            game, app = os.path.join(root, 'game'), os.path.join(root, 'manifest')
            rel, data = 'content/pkg_local/res/wtp5t_dev_test.dxp.bin', b'DxP2\0\xff'
            ok, report = install.write(game, [(rel, data)], app, dry_run=True)
            self.assertTrue(ok, report)
            self.assertFalse(os.path.exists(os.path.join(game, rel)))
            ok, report = install.write(game, [(rel, data)], app)
            self.assertTrue(ok, report)
            man = install.load_manifest(app)
            self.assertEqual(man['files'][rel], install.sha(data))
            self.assertEqual(man['sizes'][rel], len(data))
            with open(os.path.join(game, rel), 'ab') as f:
                f.write(b'changed')
            install.remove(game, app)
            self.assertTrue(os.path.exists(os.path.join(game, rel)))


if __name__ == '__main__':
    unittest.main()
