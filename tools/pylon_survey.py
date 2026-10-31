"""Обзор подвески авиации по BLK установленной игры; только чтение архивов.

Запуск: PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/pylon_survey.py
Частота означает число объектов данного уровня, где имя встретилось хотя бы раз.
"""
from collections import Counter, defaultdict
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib.blk import BinaryReader  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402

GAME = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'WarThunder')
FM = 'gamedata/flightmodels/'
PRESETS = FM + 'weaponpresets/'


def children(block, name):
    return [b for b in block.blocks if b.name == name]


def walk(block, chain=()):
    for child in block.blocks:
        path = chain + (child.name,)
        yield path, child
        yield from walk(child, path)


def count_shape(block, params, blocks):
    params.update({p[0] for p in block.params})
    blocks.update({b.name for b in block.blocks})


def show(title, counter, total, limit=30):
    print(f'{title} (объектов {total}):')
    print('  ' + ', '.join(f'{k} {n}' for k, n in counter.most_common(limit)))


def examples(title, rows, limit=5):
    print(title)
    for row in rows[:limit]:
        print('  ' + ' | '.join(map(str, row)))


def norm_path(value):
    return re.sub(r'/+', '/', value.lower().replace('\\', '/')) if isinstance(value, str) else ''


def side(name):
    """Осторожная эвристика для парных имен, без вывода о геометрии модели."""
    if not isinstance(name, str):
        return None
    s = name.lower()
    patterns = ((r'(^|[_-])left(?=$|[_-])', 'left', 'side'),
                (r'(^|[_-])right(?=$|[_-])', 'right', 'side'),
                (r'(^|[_-])l(?=$|[_-])', 'left', 'side'),
                (r'(^|[_-])r(?=$|[_-])', 'right', 'side'),
                (r'(^|[_-])port(?=$|[_-])', 'left', 'side'),
                (r'(^|[_-])starboard(?=$|[_-])', 'right', 'side'))
    for pattern, value, _ in patterns:
        if re.search(pattern, s):
            key = re.sub(pattern, r'\1{side}', s)
            return key, value
    return None


def main():
    aces = Vromfs(os.path.join(GAME, 'aces.vromfs.bin'))
    ar = BinaryReader.for_vromfs(aces)
    char = Vromfs(os.path.join(GAME, 'char.vromfs.bin'))
    cr = BinaryReader.for_vromfs(char)
    mods_root = cr.parse(char.get('config/modifications.blk'))
    global_mods = {b.name.lower(): b for b in (mods_root.block('modifications') or mods_root).blocks}
    cost = cr.parse(char.get('config/wpcost.blk'))
    costs = {b.name.lower(): b for b in cost.blocks}

    paths = sorted(p for p in aces.files if p.startswith(FM) and p.endswith('.blk')
                   and '/' not in p[len(FM):])
    preset_paths = sorted(p for p in aces.files if p.startswith(PRESETS) and p.endswith('.blk'))
    parsed_presets = {}
    errors = []
    for path in preset_paths:
        try:
            parsed_presets[path] = ar.parse(aces.files[path])
        except Exception as exc:
            errors.append((path, str(exc)))

    kinds = Counter()
    machine_examples = defaultdict(list)
    slot_params, slot_blocks = Counter(), Counter()
    preset_params, preset_blocks = Counter(), Counter()
    weapon_params, weapon_blocks = Counter(), Counter()
    legacy_params, legacy_blocks = Counter(), Counter()
    legacy_preset_params, legacy_preset_blocks = Counter(), Counter()
    slots_params, slots_blocks = Counter(), Counter()
    file_params, file_blocks = Counter(), Counter()
    file_weapon_params, file_weapon_blocks = Counter(), Counter()
    slots_n = presets_n = weapons_n = legacy_n = 0
    slot_indices, slot_tiers = Counter(), Counter()
    preset_kinds = Counter()
    file_weapons = 0
    refs = Counter()
    ref_examples = defaultdict(list)
    mass_fields = Counter()
    mass_examples = defaultdict(list)
    node_fields = Counter()
    node_examples = defaultdict(list)
    mod_refs = Counter()
    mod_locations = Counter()
    mod_examples = defaultdict(list)
    link_stats = Counter()
    link_examples = defaultdict(list)
    pair_stats = Counter()
    pair_examples = defaultdict(list)
    index_pairs = Counter()
    weapon_links = Counter()
    weapon_link_examples = defaultdict(list)
    preset_ref_missing = []

    for path in paths:
        try:
            root = ar.parse(aces.files[path])
        except Exception as exc:
            errors.append((path, str(exc)))
            continue
        slots_root = root.block('WeaponSlots')
        legacy_root = root.block('weapon_presets')
        has_new = bool(slots_root and children(slots_root, 'WeaponSlot'))
        has_old = bool(legacy_root and children(legacy_root, 'preset'))
        kind = 'оба' if has_new and has_old else 'новый' if has_new else 'старый' if has_old else 'без обоих'
        kinds[kind] += 1
        if len(machine_examples[kind]) < 5:
            machine_examples[kind].append((path,))
        unit = path[len(FM):-4].lower()
        unit_mods = root.block('modifications')
        local_mods = {b.name.lower() for b in unit_mods.blocks} if unit_mods else set()
        cost_unit = costs.get(unit)
        cost_mods = cost_unit.block('modifications') if cost_unit else None
        cost_mod_names = {b.name.lower() for b in cost_mods.blocks} if cost_mods else set()
        if cost_unit:
            link_stats['машина в wpcost'] += 1
            if cost_unit.get('hasWeaponSlots') is True:
                link_stats['hasWeaponSlots=yes'] += 1
        for chain, b in walk(root):
            for key, _typ, val in b.params:
                low = key.lower()
                if any(x in low for x in ('mass', 'load', 'disbalance')):
                    label = '/'.join(chain) + ':' + key
                    mass_fields[label] += 1
                    if len(mass_examples[label]) < 3:
                        mass_examples[label].append((path, val))
                if key in ('reqModification', 'reqModifications'):
                    mod_refs['все'] += 1
                    mod_locations['/'.join(chain) + ':' + key] += 1
                    mod_refs['глобальная запись' if str(val).lower() in global_mods else 'нет глобальной записи'] += 1
                    mod_refs['в машине' if str(val).lower() in local_mods else 'нет в машине'] += 1
                    mod_refs['в wpcost' if str(val).lower() in cost_mod_names else 'нет в wpcost'] += 1
                    if len(mod_examples['reqModification']) < 8:
                        mod_examples['reqModification'].append((path, '/'.join(chain), val,
                           str(val).lower() in global_mods, str(val).lower() in local_mods,
                           str(val).lower() in cost_mod_names))
        if slots_root:
            count_shape(slots_root, slots_params, slots_blocks)
            for snode in children(slots_root, 'HideNodes') + children(slots_root, 'ShowNodes'):
                node_fields['WeaponSlots/' + snode.name] += 1
                if len(node_examples[snode.name]) < 5:
                    node_examples[snode.name].append((path, [v for k, _, v in snode.params if k == 'node'][:6]))
        if legacy_root:
            count_shape(legacy_root, legacy_params, legacy_blocks)
            for legacy in children(legacy_root, 'preset'):
                legacy_n += 1
                count_shape(legacy, legacy_preset_params, legacy_preset_blocks)
                ref = norm_path(legacy.get('blk'))
                exists = aces.get(ref) is not None
                refs['ссылка есть'] += bool(ref)
                refs['ссылка разрешена'] += exists
                refs['ссылка не разрешена'] += bool(ref) and not exists
                if ref and not exists:
                    preset_ref_missing.append((path, legacy.get('name'), legacy.get('blk')))
                if len(ref_examples['legacy']) < 6:
                    ref_examples['legacy'].append((path, legacy.get('name'), legacy.get('blk'), exists))
                if exists:
                    pr = parsed_presets.get(ref)
                    if pr:
                        refs['ссылается на Weapon(slot,preset)'] += bool(any(
                            w.get('slot') is not None and w.get('preset') is not None
                            for w in children(pr, 'Weapon')))
                        refs['ссылается на Weapon(blk,emitter)'] += bool(any(
                            w.get('blk') is not None for w in children(pr, 'Weapon')))
        if not slots_root:
            continue
        slot_sides = defaultdict(lambda: defaultdict(list))
        for slot in children(slots_root, 'WeaponSlot'):
            slots_n += 1
            count_shape(slot, slot_params, slot_blocks)
            idx = slot.get('index')
            slot_indices[idx] += 1
            slot_tiers[slot.get('tier')] += 1
            for preset in children(slot, 'WeaponPreset'):
                presets_n += 1
                count_shape(preset, preset_params, preset_blocks)
                preset_kinds['со встроенным Weapon'] += bool(children(preset, 'Weapon'))
                preset_kinds['со ссылкой blk'] += preset.get('blk') is not None
                for node in children(preset, 'ShowNodes') + children(preset, 'HideNodes'):
                    node_fields['WeaponPreset/' + node.name] += 1
                    if len(node_examples[node.name]) < 5 and not any(
                            row[0] == path for row in node_examples[node.name]):
                        node_examples[node.name].append((path, idx, preset.get('name'),
                            [v for k, _, v in node.params if k == 'node'][:6]))
                name_side = side(preset.get('name'))
                if name_side:
                    slot_sides[name_side[0]][name_side[1]].append((idx, preset.get('name')))
                for weapon in children(preset, 'Weapon'):
                    weapons_n += 1
                    count_shape(weapon, weapon_params, weapon_blocks)
                    wref = norm_path(weapon.get('blk'))
                    if wref:
                        weapon_links['ссылка blk'] += 1
                        good = aces.get(wref) is not None
                        weapon_links['разрешена'] += good
                        if not good and len(weapon_link_examples['нет']) < 5:
                            weapon_link_examples['нет'].append((path, idx, wref))
        for key, sides in slot_sides.items():
            if sides['left'] and sides['right']:
                pair_stats['парные имена в машине'] += 1
                for left in sides['left']:
                    for right in sides['right']:
                        if left[0] == right[0]:
                            pair_stats['один index'] += 1
                        else:
                            pair_stats['разные index'] += 1
                            index_pairs[(left[0], right[0])] += 1
                        if len(pair_examples['имена']) < 12 and not any(
                                row[0] == path for row in pair_examples['имена']):
                            pair_examples['имена'].append((path, key, left, right))

    for path, root in parsed_presets.items():
        file_weapons += len(children(root, 'Weapon'))
        count_shape(root, file_params, file_blocks)
        for weapon in children(root, 'Weapon'):
            count_shape(weapon, file_weapon_params, file_weapon_blocks)
        for chain, block in walk(root):
            for key, _typ, val in block.params:
                if any(x in key.lower() for x in ('mass', 'load', 'disbalance')):
                    label = 'файл пресета/' + '/'.join(chain) + ':' + key
                    mass_fields[label] += 1
                    if len(mass_examples[label]) < 3:
                        mass_examples[label].append((path, val))
        weapons = children(root, 'Weapon')
        if weapons and all(w.get('slot') is not None and w.get('preset') is not None for w in weapons):
            preset_kinds['файл-комбинация слотов'] += 1
            if len(ref_examples['combination']) < 5:
                ref_examples['combination'].append((path, [(w.get('slot'), w.get('preset')) for w in weapons[:5]]))
        elif weapons and any(w.get('blk') is not None for w in weapons):
            preset_kinds['файл с оружием'] += 1
            if len(ref_examples['weapons']) < 5:
                ref_examples['weapons'].append((path, [(w.get('trigger'), w.get('blk'), w.get('emitter'), w.get('bullets')) for w in weapons[:2]]))
        else:
            preset_kinds['файл без Weapon'] += 1
            if len(ref_examples['other']) < 5:
                ref_examples['other'].append((path, [b.name for b in root.blocks[:5]]))

    print('ИСТОЧНИКИ:', len(paths), 'корневых BLK машин;', len(preset_paths),
          'BLK файлов weaponpresets; ошибок:', len(errors))
    print('ФОРМАТЫ МАШИН:', dict(kinds))
    for kind, rows in machine_examples.items():
        examples('  ' + kind, rows)
    print('ОБЪЕКТЫ: WeaponSlot', slots_n, 'WeaponPreset внутри слота', presets_n,
          'Weapon внутри них', weapons_n, 'старых preset', legacy_n,
          'Weapon в файлах пресетов', file_weapons)
    show('WeaponSlots: параметры', slots_params, kinds['оба'] + kinds['новый'], 20)
    show('WeaponSlots: блоки', slots_blocks, kinds['оба'] + kinds['новый'], 20)
    show('WeaponSlot: параметры', slot_params, slots_n, 35)
    show('WeaponSlot: блоки', slot_blocks, slots_n, 25)
    show('WeaponPreset: параметры', preset_params, presets_n, 45)
    show('WeaponPreset: блоки', preset_blocks, presets_n, 35)
    show('Weapon: параметры', weapon_params, weapons_n, 45)
    show('Weapon: блоки', weapon_blocks, weapons_n, 20)
    show('weapon_presets: параметры', legacy_params, len(paths), 20)
    show('weapon_presets: блоки', legacy_blocks, len(paths), 20)
    show('weapon_presets/preset: параметры', legacy_preset_params, legacy_n, 25)
    show('weapon_presets/preset: блоки', legacy_preset_blocks, legacy_n, 20)
    show('Файл weaponpresets: параметры', file_params, len(parsed_presets), 25)
    show('Файл weaponpresets: блоки', file_blocks, len(parsed_presets), 25)
    show('Файл weaponpresets/Weapon: параметры', file_weapon_params, file_weapons, 30)
    show('Файл weaponpresets/Weapon: блоки', file_weapon_blocks, file_weapons, 20)
    print('SLOT INDEX (топ):', slot_indices.most_common(20))
    print('SLOT TIER (топ):', slot_tiers.most_common(20))
    print('ТИПЫ ПРЕСЕТОВ:', dict(preset_kinds))
    print('ССЫЛКИ:', dict(refs), 'оружие:', dict(weapon_links))
    examples('НЕРАЗРЕШЕННЫЕ ССЫЛКИ ПРЕСЕТОВ', preset_ref_missing)
    for kind in ('legacy', 'combination', 'weapons', 'other'):
        examples('ПРИМЕРЫ ' + kind, ref_examples[kind])
    examples('НЕРАЗРЕШЕННЫЕ ССЫЛКИ ОРУЖИЯ', weapon_link_examples['нет'])
    show('МАССА И ОГРАНИЧЕНИЯ: путь:поле', mass_fields, len(paths), 50)
    for key, _ in mass_fields.most_common(15):
        examples('  ' + key, mass_examples[key], 2)
    print('УЗЛЫ:', dict(node_fields))
    for kind, rows in node_examples.items():
        examples('  ' + kind, rows)
    print('МОДИФИКАЦИИ:', dict(mod_refs), 'wpcost:', dict(link_stats))
    show('  места reqModification', mod_locations, mod_refs['все'], 8)
    examples('  reqModification: машина | путь | имя | global | local | wpcost', mod_examples['reqModification'], 8)
    print('СИММЕТРИЯ ПО ИМЕНАМ:', dict(pair_stats), 'частые пары индексов:', index_pairs.most_common(20))
    examples('  пары', pair_examples['имена'], 12)
    if errors:
        examples('ОШИБКИ', errors, 10)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
