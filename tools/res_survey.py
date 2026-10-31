"""Read-only byte survey of WT GRP2, DxP2, descriptor and grp_hdr files.

Usage: .venv/Scripts/python tools/res_survey.py [--game GAME_ROOT]
"""
import argparse
import re
import struct
import sys
from pathlib import Path

import zstandard

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wtpoligon.game.vromfs import Vromfs

ASCII = re.compile(rb"[a-zA-Z0-9_./*?+-]{4,}\x00")


def strings(raw, limit=None):
    return [(m.start(), m.group()[:-1].decode("ascii")) for m in ASCII.finditer(raw[:limit])]


def words(raw, count=16):
    return [f"{v:08x}" for v in struct.unpack_from("<" + "I" * count, raw)]


def descriptor(path):
    raw = path.read_bytes()
    size = int.from_bytes(raw[1:4], "little")
    assert size == len(raw) - 4, (path, size, len(raw))
    data = zstandard.ZstdDecompressor().decompress(raw[4:])
    print(f"{path.name}: wrapper={raw[0]:02x}, declared={size}, decompressed={len(data)}")
    print("  words:", " ".join(words(data, min(len(data) // 4, 12))))
    print("  strings:", strings(data))
    print("  hex:", data[:256].hex(" "))


def grp(path):
    raw = path.read_bytes()
    assert raw[:4] == b"GRP2", path
    head = strings(raw, min(len(raw), 4096))
    textures = sorted({m.group().decode("ascii") for m in re.finditer(rb"[a-z][a-z0-9_]{3,}\*", raw)})
    print(f"{path.name}: {len(raw)} bytes, words={' '.join(words(raw))}")
    print("  first names:", head[:35])
    print("  texture-like byte sequences (unverified):", textures[:100])
    return textures


def dxp_names(raw):
    assert raw[:4] == b"DxP2"
    # The header points to the end of the texture-name table; payload follows.
    names_end = struct.unpack_from("<I", raw, 12)[0]
    return {s for _, s in strings(raw, names_end) if "*" in s and "?" in s}


def dxp_names_file(path):
    """Read only the DxP2 name table, without loading texture payloads."""
    with open(path, 'rb') as stream:
        header = stream.read(16)
        if header[:4] != b'DxP2':
            raise ValueError('not DxP2: ' + str(path))
        names_end = struct.unpack_from('<I', header, 12)[0]
        stream.seek(0)
        return dxp_names(stream.read(names_end))


def descriptor_models(path, names=('leopard_2a8', 'leopard_2a8_dmg', 'leopard_2a8_xray')):
    """Summarize the FAT BLK hierarchy and its texture/material references."""
    from dynmodel_extract import unpack
    _, root = unpack(path.read_bytes())
    print(f'{path}: {len(root.blocks)} model entries')
    for name in names:
        model = root.block(name)
        if model is None:
            continue
        tex = model.block('tex')
        mat_r = model.block('matR')
        mat_s = model.block('matS')
        classes = sorted({child.get('cls') for group in (mat_r, mat_s) if group
                          for child in group.blocks if child.get('cls')})
        print(f'  {name}: tex={len(tex.params) if tex else 0}, '
              f'matR={len(mat_r.blocks) if mat_r else 0}, '
              f'matS={len(mat_s.blocks) if mat_s else 0}, classes={classes}')


def dxp(path, wanted=()):
    raw = path.read_bytes()
    names = dxp_names(raw)
    print(f"{path.name}: {len(raw)} bytes, words={' '.join(words(raw))}")
    print(f"  texture names: {len(names)}, first={sorted(names)[:12]}")
    if wanted:
        found = sorted(s for s in names if s.split("*")[0] + "*" in wanted)
        print(f"  Leopard stems found: {len(found)} {found}")
    return names


def header(path):
    vf = Vromfs(str(path))
    print(f"{path.name}: {len(vf.files)} files, vromfs {vf.header.version}")
    for name, data in vf.files.items():
        if any(x in name.lower() for x in ("germ_leopard_2a8", "germ_gm_bq", "dynmodel", "ridesc")):
            print("  match:", name, len(data), data[:40].hex(" "))
    print("  first files:", [(n, len(d)) for n, d in list(vf.files.items())[:12]])
    hits = [(n, sorted(s for s in dxp_names(d) if "leopard_2a8" in s))
            for n, d in vf.files.items() if n.endswith(".dxp.bincache.bin")]
    print("  Leopard 2A8 texture packs:", [(n, names) for n, names in hits if names])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game", type=Path, default=Path.home() / "AppData/Local/WarThunder")
    a = p.parse_args()
    local = a.game / "content/pkg_local/res"
    base = a.game / "content/base/res"
    for name in ("dynModelDesc.bin", "riDesc.bin"):
        descriptor(local / name)
    descriptor_models(Path('cache/dev/dynModelDesc.bin'))
    grp(local / "sample_m60a1.grp")
    dxp(local / "sample_m60a1.dxp.bin")
    model = Path("cache/dev/tanks/germ_leopard_2a8.grp")
    wanted = grp(model)
    dev_dxp = dxp(Path("cache/dev/tanks/germ_gm_bq.dxp.bin"), wanted)
    live_dxp = dxp(base / "tanks/germ_gm_bq.dxp.bin", wanted)
    print("  Dev-only German tank textures:", sorted(dev_dxp - live_dxp))
    print("  normal-only German tank textures:", sorted(live_dxp - dev_dxp))
    raw_grp = model.read_bytes()
    print("  Dev-only names directly in GRP:", [n for n in sorted(dev_dxp - live_dxp) if n.split("*")[0].encode() in raw_grp])
    header(Path("cache/dev/grp_hdr.vromfs.bin"))
    header(base / "grp_hdr.vromfs.bin")


if __name__ == "__main__":
    main()
