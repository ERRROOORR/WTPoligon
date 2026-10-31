"""Read-only survey of aircraft mass fields in War Thunder's aces.vromfs.bin.

Run: PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/fm_mass_survey.py
The report is printed to stdout; no game or project data is modified.
"""
from collections import Counter, defaultdict
from statistics import median
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib.blk import BinaryReader  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402

PREFIX = 'gamedata/flightmodels/fm/'
TARGETS = ('a-26b', 'a-20g', 'f-4c')


def walk(block, path=()):
    for child in block.blocks:
        here = path + (child.name,)
        yield here, child
        yield from walk(child, here)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def part_values(block):
    """Numeric entries under Parts; tank capacities are reported separately.

    In these BLKs a part's name is usually the *parameter name* (e.g. engine1_dm),
    not a nested Part/mass pair. Capacity is fuel storage, not dry part mass.
    """
    vals = []
    for _, node in (((), block), *walk(block)):
        vals.extend((k, v) for k, _, v in node.params if number(v))
    return vals


def describe(label, rows):
    nums = [v for _, v in rows if number(v)]
    examples = ', '.join(f'{p.rsplit("/", 1)[-1]}={v}' for p, v in rows[:4])
    typical = f'; median={median(nums):.3g}' if nums else ''
    print(f'{label}: {len(rows)} files{typical}; {examples}')


def main():
    game = os.path.join(os.environ['LOCALAPPDATA'], 'WarThunder', 'aces.vromfs.bin')
    vf = Vromfs(game)
    reader = BinaryReader.for_vromfs(vf)
    paths = sorted(p for p in vf.files if p.startswith(PREFIX)
                   and p.endswith('.blk') and '/' not in p[len(PREFIX):])
    fields = defaultdict(list)
    blocks = Counter()
    part_shapes = Counter()
    relations = defaultdict(list)
    targets = {}
    errors = []
    for path in paths:
        try:
            root = reader.parse(vf.files[path])
        except Exception as exc:
            errors.append((path, str(exc)))
            continue
        short = path[len(PREFIX):-4]
        if short in TARGETS:
            targets[short] = root
        nodes = [((), root), *walk(root)]
        seen = set()
        for chain, node in nodes:
            label = '/'.join(chain)
            if chain and (chain[0] == 'Mass' or any(x in node.name.lower() for x in ('mass', 'inertia', 'moment'))):
                blocks[label] += 1
            for key, _typ, value in node.params:
                if (chain and chain[0] == 'Mass') or any(x in key.lower() for x in ('mass', 'inertia', 'moment')):
                    full = f'{label}/{key}' if label else key
                    if full not in seen:
                        fields[full].append((path, value))
                        seen.add(full)
        mass = root.block('Mass')
        if mass:
            empty, takeoff = mass.get('EmptyMass'), mass.get('Takeoff')
            fuels = [v for k, _, v in mass.params if k.startswith('MaxFuelMass') and 'External' not in k and number(v)]
            oil = mass.get('OilMass', 0)
            advanced = mass.get('AdvancedMass')
            group = 'yes' if advanced is True else 'no' if advanced is False else 'missing'
            for kind in ('Parts', 'PartsWithSurface'):
                part = mass.block(kind)
                if part:
                    vals = part_values(part)
                    dry = [v for k, v in vals if 'capacity' not in k.lower()]
                    dm = [v for k, v in vals if k.endswith('_dm')]
                    part_shapes[(group, kind, 'files')] += 1
                    part_shapes[(group, kind, 'with numeric entries')] += bool(vals)
                    part_shapes[(group, kind, 'numeric entries')] += len(vals)
                    if number(empty) and vals:
                        relations[(group, kind, 'all numeric minus EmptyMass')].append((path, sum(v for _, v in vals) - empty))
                        relations[(group, kind, 'excluding capacity minus EmptyMass')].append((path, sum(dry) - empty))
                        relations[(group, kind, 'dm entries minus EmptyMass')].append((path, sum(dm) - empty))
            combined = [entry for kind in ('Parts', 'PartsWithSurface')
                        if (part := mass.block(kind)) for entry in part_values(part)]
            if number(empty) and combined:
                relations[(group, 'Parts+PartsWithSurface', 'all numeric minus EmptyMass')].append(
                    (path, sum(v for _, v in combined) - empty))
                relations[(group, 'Parts+PartsWithSurface', 'excluding capacity minus EmptyMass')].append(
                    (path, sum(v for k, v in combined if 'capacity' not in k.lower()) - empty))
                relations[(group, 'Parts+PartsWithSurface', 'dm entries minus EmptyMass')].append(
                    (path, sum(v for k, v in combined if k.endswith('_dm')) - empty))
            if all(number(x) for x in (empty, takeoff, oil)):
                relations[(group, 'Takeoff minus EmptyMass')].append((path, takeoff-empty))
                relations[(group, 'Takeoff minus EmptyMass-fuel-oil')].append(
                    (path, takeoff-empty-sum(fuels)-oil))
                relations[(group, 'fuel count')].append((path, len(fuels)))
    print(f'FM files: {len(paths)}; parsed: {len(paths)-len(errors)}; errors: {len(errors)}')
    for path, err in errors[:5]:
        print('ERROR', path, err)
    print('\nFIELDS (file frequency, median where numeric, examples):')
    for label, rows in sorted(fields.items()):
        describe(label, rows)
    print('\nMASS-RELATED BLOCKS (occurrences):')
    for label, count in sorted(blocks.items()):
        print(label, count)
    print('\nPART CONTAINERS:')
    for key, count in sorted(part_shapes.items()):
        print('/'.join(key), count)
    print('\nNUMERIC RELATIONS:')
    for key, rows in sorted(relations.items()):
        vals = [v for _, v in rows]
        close = sum(abs(v) <= 1 for v in vals) if 'minus' in key[-1] else None
        print('/'.join(key), 'n=', len(vals), 'median=', median(vals) if vals else None,
              'within 1 kg=', close, 'examples=', rows[:5])
    print('\nTARGETS:')
    for name in TARGETS:
        root = targets.get(name)
        if not root:
            print(name, 'MISSING')
            continue
        print('\n', name)
        for chain, node in [((), root), *walk(root)]:
            if (chain and chain[0] in ('Mass', 'Passport')) or not chain:
                relevant = [(k, v) for k, _, v in node.params
                            if (chain and chain[0] == 'Mass') or any(x in k.lower() for x in ('mass','inertia','moment'))]
                if relevant:
                    print('/'.join(chain) or '<root>', relevant[:60])
        for chain, node in walk(root):
            if chain[0].startswith(('EngineType', 'PropellerType')):
                relevant = [(k, v) for k, _, v in node.params if 'mass' in k.lower()]
                if relevant:
                    print('/'.join(chain), relevant)
        mass = root.block('Mass')
        if mass:
            for kind in ('Parts', 'PartsWithSurface'):
                part = mass.block(kind)
                if part:
                    print(kind, 'direct params=', part.params[:20], 'child count=', len(part.blocks),
                          'sample children=', [(b.name, b.params[:8]) for b in part.blocks[:5]],
                          'numeric sum=', sum(v for _, v in part_values(part)),
                          'excluding capacity=', sum(v for k, v in part_values(part) if 'capacity' not in k.lower()))


if __name__ == '__main__':
    main()
