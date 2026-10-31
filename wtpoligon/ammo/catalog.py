"""Индекс орудий и снарядов; поиск всех файлов оружия выполняет worker."""
from dataclasses import dataclass
from functools import lru_cache
import csv
import io

from .. import loadout as L


@dataclass(frozen=True)
class Shell:
    key: str                 # путь файла|имя блока верхнего уровня
    name: str
    kind: str
    weapon: str
    block: str


@lru_cache(maxsize=2)
def _names(source):
    rows = csv.reader(io.StringIO(source.lang_csv('units_weaponry') or ''), delimiter=';')
    header = next(rows, [])
    try:
        ru = header.index('<Russian>')
    except ValueError:
        return {}
    return {row[0].lower(): row[ru] for row in rows if len(row) > ru and row[ru]}


def display_name(source, name, weapon=False):
    key = name.rsplit('/', 1)[-1].removesuffix('.blk').lower()
    names = source if isinstance(source, dict) else _names(source)
    if weapon:
        return names.get('weapons/' + key + '/short') or names.get('weapons/' + key) or key.replace('_', ' ')
    return names.get(key + '/name/short') or names.get(key) or key.replace('_', ' ')


def kind_name(source, kind):
    aliases = {'apds_fs_long_l30_tank': 'БОПС', 'heat_fs_tank': 'КС'}
    names = source if isinstance(source, dict) else _names(source)
    return aliases.get(kind) or names.get(kind.lower() + '/name/short') or {
        'bullet': 'Снаряд', 'rocket': 'Ракета', 'bomb': 'Бомба', 'torpedo': 'Торпеда'
    }.get(kind, kind.replace('_', ' '))


def gun_paths(unit, kind, source=None, preset=''):
    if kind in ('air', 'heli'):
        wp = unit.block('weapon_presets')
        entry = next((p for p in (wp.blocks if wp else []) if p.get('name') == preset), None)
        tree = source.load(entry.get('blk')) if source and entry and entry.get('blk') else None
        direct = [(f'preset:{i}', w.get('blk'), w.get('bullets') or 0) for i, w in enumerate(
            (b for b in (tree.blocks if tree else []) if b.name == 'Weapon'), 1) if w.get('blk')]
        slots = unit.block('WeaponSlots')
        refs = {(w.get('slot'), w.get('preset')) for w in (unit.block('commonWeapons').blocks
                if unit.block('commonWeapons') else []) if w.name == 'Weapon'}
        refs |= {(w.get('slot'), w.get('preset')) for w in (tree.blocks if tree else []) if w.name == 'Weapon'}
        nested = []
        for si, slot in enumerate((b for b in (slots.blocks if slots else []) if b.name == 'WeaponSlot'), 1):
            if slot.get('index') is None:
                continue
            for pi, choice in enumerate((b for b in slot.blocks if b.name == 'WeaponPreset'), 1):
                if (slot.get('index'), choice.get('name')) not in refs:
                    continue
                for wi, weapon in enumerate((b for b in choice.blocks if b.name == 'Weapon'), 1):
                    if weapon.get('blk'):
                        nested.append((f'WeaponSlots/WeaponSlot[{si}]/WeaponPreset[{pi}]/Weapon[{wi}]',
                                       weapon.get('blk'), weapon.get('bullets') or 0))
        return direct + nested
    cw = unit.block('commonWeapons')
    return [(i, w.get('blk'), w.get('bullets') or 0) for i, w in enumerate(
        (b for b in (cw.blocks if cw else []) if b.name == 'Weapon'), 1) if w.get('blk')]


def shells_in(source, weapon):
    return list(_shells_in(source, L.weapon_key(weapon)))


@lru_cache(maxsize=8192)
def _shells_in(source, weapon):
    tree = source.load(weapon)
    if tree is None:
        return ()
    out = []
    seen = set()
    for b in tree.blocks:
        ammo = b if b.name in ('bullet', 'rocket', 'bomb', 'torpedo') else next(
            (x for x in b.blocks if x.name in ('bullet', 'rocket', 'bomb', 'torpedo')), None)
        if ammo is None:
            continue
        name = ammo.get('bulletName') or b.name
        if name in seen:
            continue
        seen.add(name)
        key = '%s|%s' % (L.weapon_key(weapon), b.name)
        out.append(Shell(key, name, ammo.get('bulletType') or ammo.name, L.weapon_key(weapon), b.name))
    return tuple(out)


@lru_cache(maxsize=2)
def all_shells(source):
    out = []
    for path in source.list_files('gameData/Weapons/'):
        if path.endswith('.blk'):
            out.extend(shells_in(source, path))
    return tuple(out)


def shell_block(source, key):
    weapon, block = key.split('|', 1)
    tree = source.load(weapon)
    return next((b for b in (tree.blocks if tree else []) if b.name == block), None)


def stock_setup(source, vehicle, preset=''):
    unit = source.load(vehicle['file'])
    if unit is None:
        return [], [], 0
    guns = gun_paths(unit, vehicle['kind'], source, preset)
    choices = [(i, p, n) for i, p, n in guns if shells_in(source, p)]
    shells = shells_in(source, choices[0][1]) if choices else []
    return choices, shells, choices[0][2] if choices else 0
