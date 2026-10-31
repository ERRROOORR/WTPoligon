"""Read-only inspection of aircraft payload mass and drag fields in aces.vromfs.bin.

Run with PYTHONIOENCODING=utf-8 and LOCALAPPDATA pointing at the real user profile.
"""
from collections import Counter
import os

from wtlib.blk import BinaryReader
from wtlib.vromfs import Vromfs


GAME = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'WarThunder')
UNITS = ('a-26b', 'a2d', 'f-4c', 'a_109_eoa2')


def children(root, name):
    return [b for b in root.blocks if b.name == name] if root else []


def fields(block, names):
    return {k: v for k, _typ, v in block.params if k in names} if block else {}


def main():
    aces = Vromfs(os.path.join(GAME, 'aces.vromfs.bin'))
    reader = BinaryReader.for_vromfs(aces)

    def load(path):
        data = aces.get(path.lower())
        return reader.parse(data) if data is not None else None

    print('SELECTED UNITS')
    for unit in UNITS:
        path = f'gamedata/flightmodels/{unit}.blk'
        root = load(path)
        if root is None:
            print(unit, 'MISSING')
            continue
        fm = load('gamedata/flightmodels/' + root.get('fmFile'))
        print(unit, 'fmFile=', root.get('fmFile'), 'FM Mass=',
              fields(fm.block('Mass') if fm else None, ('EmptyMass', 'Takeoff', 'AdvancedMass')))
        slots = children(root.block('WeaponSlots'), 'WeaponSlot')
        examples = []
        for slot in slots:
            for preset in children(slot, 'WeaponPreset'):
                for weapon in children(preset, 'Weapon'):
                    ref = weapon.get('blk')
                    if not ref:
                        continue
                    extra = fields(weapon, ('mass', 'dragCx', 'external'))
                    if extra and len(examples) < 4:
                        examples.append((slot.get('index'), preset.get('name'), ref, extra))
                    if unit == 'a-26b' and slot.get('index') == 4 and preset.get('name') == '1000lbs_int':
                        print('  bay sample:', fields(weapon, ('blk', 'bullets', 'mass', 'dragCx', 'external')))
        print('  slot Weapon mass/drag examples:', examples)

    print('BOMB FILES')
    for name in ('su_fab9000', 'us_1000lb_anm65a1'):
        path = f'gamedata/weapons/bombguns/{name}.blk'
        root = load(path)
        print(name, 'top=', fields(root, ('mass', 'dragCx', 'external', 'mesh')),
              'bomb=', fields(root.block('bomb') if root else None,
                              ('mass', 'dragCx', 'explosiveMass', 'caliber')))

    bomb_external = Counter()
    bomb_external_examples = {}
    for path in aces.files:
        p = path.lower()
        if not p.startswith('gamedata/weapons/bombguns/') or not p.endswith('.blk'):
            continue
        root = load(path)
        value = root.get('external') if root else None
        key = 'absent' if value is None else str(value).lower()
        bomb_external[key] += 1
        bomb_external_examples.setdefault(key, path)
    print('BOMBGUN top-level external:', dict(bomb_external), bomb_external_examples)

    counts = Counter()
    examples = {}
    drag_values = Counter()
    drag_examples = []
    for path in aces.files:
        p = path.lower()
        if not p.startswith('gamedata/flightmodels/') or not p.endswith('.blk'):
            continue
        if '/fm/' in p or '/weaponpresets/' in p:
            continue
        root = load(path)
        for slot in children(root.block('WeaponSlots') if root else None, 'WeaponSlot'):
            for preset in children(slot, 'WeaponPreset'):
                for weapon in children(preset, 'Weapon'):
                    ref = (weapon.get('blk') or '').lower()
                    if '/bombguns/' not in ref:
                        continue
                    for name in ('mass', 'dragCx', 'external'):
                        if weapon.get(name) is not None:
                            counts[name] += 1
                            examples.setdefault(name, (path, slot.get('index'), preset.get('name'),
                                                       ref, weapon.get(name)))
                    if weapon.get('dragCx') is not None:
                        drag_values[round(weapon.get('dragCx'), 4)] += 1
                        if len(drag_examples) < 8 and path not in {x[0] for x in drag_examples}:
                            drag_examples.append((path, slot.get('index'), preset.get('name'),
                                                  weapon.get('dragCx'), weapon.get('external'), ref))
    print('BOMB-SLOT WEAPON FIELDS:', dict(counts))
    for key, example in examples.items():
        print(' ', key, example)
    print('BOMB-SLOT dragCx values:', dict(drag_values))
    print('BOMB-SLOT dragCx examples:', drag_examples)


if __name__ == '__main__':
    main()
