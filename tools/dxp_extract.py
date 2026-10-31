"""Extract the twelve Leopard 2A8 textures into an independent DxP2 pack.

The source layout is: 72-byte header, nul-terminated names, 64-bit name
offsets, 32-byte DDSx descriptors, 24-byte payload records, then payloads.
Header offsets and name offsets use byte 16 as their origin.
"""
import argparse
import struct
from pathlib import Path

SOURCE = Path('cache/dev/tanks/germ_gm_bq.dxp.bin')
OUTPUT = Path('cache/dev/tanks/wtp5t_dev_leopard_2a8.dxp.bin')
HEADER_SIZE = 72
COUNT_OFFSETS = (8, 20, 36, 52)
TABLE_OFFSETS = (16, 32, 48)


def align(value, boundary):
    return (value + boundary - 1) // boundary * boundary


def parse(raw):
    if raw[:4] != b'DxP2' or len(raw) < HEADER_SIZE:
        raise ValueError('not a DxP2 archive')
    count = struct.unpack_from('<I', raw, 8)[0]
    if count < 1 or any(struct.unpack_from('<I', raw, o)[0] != count for o in COUNT_OFFSETS):
        raise ValueError('inconsistent DxP2 entry counts')
    name_table, descriptors, records = (struct.unpack_from('<I', raw, o)[0] + 16 for o in TABLE_OFFSETS)
    if not (HEADER_SIZE <= name_table < descriptors < records < len(raw)):
        raise ValueError('invalid DxP2 table offsets')
    if name_table + 8 * count > descriptors or descriptors + 32 * count > records:
        raise ValueError('overlapping DxP2 tables')
    entries = []
    for i in range(count):
        name_at = struct.unpack_from('<Q', raw, name_table + 8 * i)[0] + 16
        if not HEADER_SIZE <= name_at < name_table:
            raise ValueError('name outside DxP2 name table')
        end = raw.find(b'\0', name_at, name_table)
        if end < 0:
            raise ValueError('unterminated DxP2 name')
        name = raw[name_at:end].decode('ascii')
        descriptor = raw[descriptors + 32 * i:descriptors + 32 * (i + 1)]
        record = raw[records + 24 * i:records + 24 * (i + 1)]
        payload_at, size = struct.unpack_from('<II', record, 12)
        if payload_at < records + 24 * count or payload_at + size > len(raw):
            raise ValueError('payload outside DxP2 archive: ' + name)
        entries.append((name, descriptor, record, raw[payload_at:payload_at + size]))
    if len({e[0] for e in entries}) != count:
        raise ValueError('duplicate DxP2 names')
    return entries


def build(source):
    entries = [e for e in parse(source) if e[0].startswith('leopard_2a8_')]
    if len(entries) != 12:
        raise ValueError(f'expected 12 Leopard textures, found {len(entries)}')
    out = bytearray(source[:HEADER_SIZE])
    for offset in COUNT_OFFSETS:
        struct.pack_into('<I', out, offset, len(entries))
    names = []
    for name, _, _, _ in entries:
        names.append(len(out) - 16)
        out.extend(name.encode('ascii') + b'\0')
    out.extend(b'\0' * (align(len(out), 8) - len(out)))
    struct.pack_into('<I', out, TABLE_OFFSETS[0], len(out) - 16)
    for offset in names:
        out.extend(struct.pack('<Q', offset))
    struct.pack_into('<I', out, TABLE_OFFSETS[1], len(out) - 16)
    for _, descriptor, _, _ in entries:
        out.extend(descriptor)
    struct.pack_into('<I', out, TABLE_OFFSETS[2], len(out) - 16)
    record_start = len(out)
    out.extend(b'\0' * (24 * len(entries)))
    struct.pack_into('<I', out, 12, len(out) - 16)
    out.extend(b'\0' * (align(len(out), 65536) - len(out)))
    for i, (_, _, record, payload) in enumerate(entries):
        new_record = bytearray(record)
        struct.pack_into('<II', new_record, 12, len(out), len(payload))
        out[record_start + 24 * i:record_start + 24 * (i + 1)] = new_record
        out.extend(payload)
    result = bytes(out)
    rebuilt = parse(result)
    if [(n, d, r[:12] + r[20:], p) for n, d, r, p in rebuilt] != [
            (n, d, r[:12] + r[20:], p) for n, d, r, p in entries]:
        raise ValueError('DxP2 self-check failed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    pack = build(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(pack)
    # Check the file on disk, not just the in-memory result.
    if args.output.read_bytes() != pack or len(parse(args.output.read_bytes())) != 12:
        raise ValueError('written DxP2 failed verification')
    print(f'DxP2 self-check OK: 12 textures, {len(pack)} bytes, {args.output}')


if __name__ == '__main__':
    main()
