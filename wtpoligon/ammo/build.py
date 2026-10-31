"""BLK копии орудия и патроны в миссии."""
from .. import edits as E
from ..game import blk as B
from ..loadout import weapon_key
from .catalog import gun_paths, shells_in, shell_block
from .validate import check


def copy_path(stock, unit_class):
    path = stock.replace('\\', '/').split('#/develop/gameBase/')[-1]
    folder, name = path.rsplit('/', 1)
    if folder.lower().startswith('gamedata/weapons/'):
        folder = 'gameData/Weapons/' + folder[len('gamedata/weapons/'):]
    elif folder.lower().startswith('gamedata/flightmodels/'):
        folder = 'gameData/FlightModels/' + folder[len('gamedata/flightmodels/'):]
    return '%s/%s__%s' % (folder, unit_class, name)


def build_files(source, unit, kind, preset, ammo, unit_class):
    """Возвращает (файлы, правка машины, ячейки миссии, ошибки)."""
    guns = gun_paths(unit, kind, source, preset)
    gun = ammo.gun or next((p for _, p, _ in guns if shells_in(source, p)), '')
    tree = source.load(gun) if gun else None
    if tree is None:
        return [], '', [], ['нет файла орудия %s' % gun]
    stock_shells = shells_in(source, gun)
    keys = {s.key for s in stock_shells}
    available = keys | set(ammo.added)
    problems = check(ammo, available)
    extra = []
    names = {s.key: s.block for s in stock_shells}
    for key in ammo.added:
        if key in keys:
            continue
        block = shell_block(source, key)
        if block is None:
            problems.append('нет снаряда %s' % key)
            continue
        if any(b.name == block.name for b in tree.blocks):
            problems.append('имя блока снаряда уже занято: %s' % block.name)
            continue
        extra.append(B.to_text(B.Block(None, blocks=[block])))
        names[key] = block.name
    edits = [e for e in ammo.edits if weapon_key(e.file) == weapon_key(gun)]
    if len(edits) != len(ammo.edits):
        problems.append('правка снаряда относится к другому файлу орудия')
    patch, bad = E.edits_text(tree, edits)
    problems += bad
    capacity_changed = bool(ammo.stock_capacity and ammo.capacity != ammo.stock_capacity)
    needs_copy = bool(ammo.gun or extra or edits or ammo.air_guns or capacity_changed)
    if not needs_copy and not any(s.shell or s.count for s in ammo.slots):
        return [], '', [], problems
    chosen = [(names.get(s.shell, ''), s.count) for s in ammo.slots]
    if kind in ('air', 'heli') and ammo.air_guns and not any(s.shell for s in ammo.slots):
        chosen = [(g.belt.rsplit('|', 1)[-1] if g.belt else '', g.rounds_per_barrel)
                  for g in ammo.air_guns[:4]]
    if not needs_copy:
        return [], '', chosen, problems
    copied = copy_path(gun, unit_class)
    text = 'include "#/develop/gameBase/%s"\n%s%s' % (gun, ''.join(extra), patch)
    files = [('content/pkg_local/' + copied, text)]
    if kind in ('air', 'heli'):
        wp = unit.block('weapon_presets')
        entry = next(((i, p) for i, p in enumerate(wp.blocks, 1) if p.get('name') == preset), None) if wp else None
        if not entry or not entry[1].get('blk'):
            return files, '', chosen, problems + ['нет пресета авиационного вооружения']
        base = entry[1].get('blk')
        preset_copy = copy_path(base, unit_class)
        weapon_lines = ''.join('"@override:Weapon[%d]"{"@override:blk":t=%s}\n' % (int(i.split(':')[1]), B.quote(copied))
                               for i, path, _ in guns if str(i).startswith('preset:') and weapon_key(path) == weapon_key(gun))
        files.append(('content/pkg_local/' + preset_copy,
                      'include "#/develop/gameBase/%s"\n%s' % (base, weapon_lines)))
        unit_patch = '"@override:weapon_presets"{"@override:preset[%d]"{"@override:blk":t=%s}}\n' % (
            entry[0], B.quote(preset_copy))
        nested_lines = ''.join(E.override_path(unit, i + '/blk', copied) for i, path, _ in guns
                               if str(i).startswith('WeaponSlots/') and weapon_key(path) == weapon_key(gun))
        for selection in ammo.air_guns:
            for location, path, _count in guns:
                if weapon_key(path) != weapon_key(selection.weapon) or not str(location).startswith('WeaponSlots/'):
                    continue
                if selection.rounds_per_barrel and E.stock_param(unit, location + '/bullets'):
                    nested_lines += E.override_path(unit, location + '/bullets', selection.rounds_per_barrel)
        unit_patch += nested_lines
        if not weapon_lines and not nested_lines:
            problems.append('орудия нет в пресете и слотах')
    else:
        index = next((i for i, p, _ in guns if weapon_key(p) == weapon_key(gun)), 1)
        unit_patch = '"@override:commonWeapons"{"@override:Weapon[%d]"{"@override:blk":t=%s}}\n' % (
            index, B.quote(copied))
        if capacity_changed:
            path = 'commonWeapons/Weapon[%d]/bullets' % index
            if E.stock_param(unit, path):
                unit_patch += E.override_path(unit, path, ammo.capacity)
            else:
                problems.append('у орудия нет поля вместимости bullets')
    return files, unit_patch, chosen, problems
