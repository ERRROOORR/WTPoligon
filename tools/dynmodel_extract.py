"""Build a small dynModelDesc.bin from the existing local descriptor and Dev models.

The descriptor is a Zstd wrapped FAT binary BLK. The decompressed payload has
one extra 0x01 prefix before the ordinary FAT BLK body.
"""
import argparse
import struct
import sys
from collections import deque
from pathlib import Path

import zstandard

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wtpoligon.game.blk import Block, _parse_body, _uleb, parse_name_table

DEV = Path('cache/dev/dynModelDesc.bin')
OUTPUT = Path('pkg_local/res/dynModelDesc.bin')
MODELS = ('leopard_2a8', 'leopard_2a8_dmg', 'leopard_2a8_xray')
TYPES = {'t': 1, 'i': 2, 'r': 3, 'p4': 6, 'b': 9}


def uleb(value):
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def unpack(raw):
    if len(raw) < 8 or raw[0] != 2 or int.from_bytes(raw[1:4], 'little') != len(raw) - 4:
        raise ValueError('invalid dynModelDesc wrapper')
    data = zstandard.ZstdDecompressor().decompress(raw[4:])
    if data[:1] != b'\x01':
        raise ValueError('unknown dynModelDesc payload version')
    return data, _parse_body(data[1:], None)


def block_records(data):
    """Return the encoded block records after the FAT name and parameter tables."""
    body = data[1:]
    _, pos = parse_name_table(body)
    count, pos = _uleb(body, pos)
    params, pos = _uleb(body, pos)
    pdata_size, pos = _uleb(body, pos)
    pos += pdata_size + params * 8
    records = []
    for _ in range(count):
        start = pos
        _, pos = _uleb(body, pos)
        _, pos = _uleb(body, pos)
        children, pos = _uleb(body, pos)
        if children:
            _, pos = _uleb(body, pos)
        records.append(body[start:pos])
    if pos != len(body):
        raise ValueError('trailing descriptor data')
    return records


def encode(root):
    blocks = []
    queue = deque([root])
    while queue:
        block = queue.popleft()
        # Children are appended after the entries already waiting in the BFS queue.
        blocks.append((block, len(blocks) + 1 + len(queue) if block.blocks else 0))
        queue.extend(block.blocks)
    names = ['chroma_dome_dynmodel']
    for block, _ in blocks:
        for name in ([block.name] if block.name else []) + [p[0] for p in block.params]:
            if name not in names:
                names.append(name)
    ids = {name: i for i, name in enumerate(names)}
    strings = b''.join(n.encode('utf-8') + b'\0' for n in names)
    pdata = bytearray()
    pinfo = bytearray()
    binfo = bytearray()
    for block, first in blocks:
        for name, typ, value in block.params:
            if typ == 't':
                offset = len(pdata)
                pdata.extend(value.encode('utf-8') + b'\0')
                raw = struct.pack('<I', offset)
            elif typ == 'i':
                raw = struct.pack('<i', value)
            elif typ == 'r':
                raw = struct.pack('<f', value)
            elif typ == 'b':
                raw = struct.pack('<I', int(value))
            elif typ == 'p4':
                offset = len(pdata)
                pdata.extend(struct.pack('<4f', *value))
                raw = struct.pack('<I', offset)
            else:
                raise ValueError('unsupported Leopard parameter type: ' + typ)
            pinfo.extend(struct.pack('<I', (TYPES[typ] << 24) | ids[name]) + raw)
        binfo.extend(uleb(ids[block.name] + 1 if block.name else 0))
        binfo.extend(uleb(len(block.params)))
        binfo.extend(uleb(len(block.blocks)))
        if block.blocks:
            binfo.extend(uleb(first))
    body = (uleb(len(names)) + uleb(len(strings)) + strings + uleb(len(blocks)) +
            uleb(len(pinfo) // 8) + uleb(len(pdata)) + pdata + pinfo + binfo)
    data = b'\x01' + body
    compressed = zstandard.ZstdCompressor().compress(data)
    return b'\x02' + len(compressed).to_bytes(3, 'little') + compressed


def build(chroma_raw, dev_raw):
    chroma_data, chroma = unpack(chroma_raw)
    if len(chroma.blocks) != 1 or chroma.blocks[0].name != 'chroma_dome_dynmodel' or chroma.blocks[0].params or chroma.blocks[0].blocks:
        raise ValueError('local descriptor is not the expected Chroma-only descriptor')
    # Its original leaf record is 01 00 00. Keep the Chroma name at index 0.
    if not chroma_data.endswith(b'\x01\x00\x00'):
        raise ValueError('unexpected Chroma record encoding')
    _, dev = unpack(dev_raw)
    entries = {b.name: b for b in dev.blocks if b.name in MODELS}
    if set(entries) != set(MODELS):
        raise ValueError('Dev descriptor lacks Leopard models')
    root = Block(None, blocks=[chroma.blocks[0]] + [entries[name] for name in MODELS])
    result = encode(root)
    data, checked = unpack(result)
    if [b.name for b in checked.blocks] != ['chroma_dome_dynmodel', *MODELS]:
        raise ValueError('descriptor entry self-check failed')
    if checked.blocks[0].params or checked.blocks[0].blocks:
        raise ValueError('Chroma self-check failed')
    if block_records(data)[1] != block_records(chroma_data)[1]:
        raise ValueError('Chroma record changed')
    # Compare all typed values, including texture and shader names, after rereading.
    def signature(block):
        return block.name, block.params, [signature(child) for child in block.blocks]
    for name in MODELS:
        if signature(checked.block(name)) != signature(entries[name]):
            raise ValueError('Leopard self-check failed: ' + name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chroma', type=Path, required=True)
    parser.add_argument('--dev', type=Path, default=DEV)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(args.chroma.read_bytes(), args.dev.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    unpack(args.output.read_bytes())
    print(f'dynModelDesc self-check OK: Chroma + {", ".join(MODELS)}, {len(result)} bytes, {args.output}')


if __name__ == '__main__':
    main()
