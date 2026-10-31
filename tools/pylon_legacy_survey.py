"""Read-only survey of legacy aircraft presets, helicopters, and emitter symmetry.

Run with LOCALAPPDATA pointed at the real Windows profile when sandboxed.
"""
from collections import Counter, defaultdict
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib.blk import BinaryReader  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402

FM = 'gamedata/flightmodels/'
PRESETS = FM + 'weaponpresets/'


def children(block, name):
    return [child for child in block.blocks if child.name == name] if block else []


def norm_path(value):
    return re.sub(r'/+', '/', value.lower().replace('\\', '/')) if isinstance(value, str) else ''


def side_key(value):
    """Return a lexical left/right match; this says nothing about 3D placement."""
    if not isinstance(value, str):
        return None
    value = value.lower()
    for left, right in (('left', 'right'), ('port', 'starboard'), ('l', 'r')):
        for marker, side in ((left, 'L'), (right, 'R')):
            match = re.search(r'(?<![a-z])' + marker + r'(?![a-z])', value)
            if match:
                return value[:match.start()] + '{side}' + value[match.end():], side
    return None


def report(name, counter, limit=12):
    print(name, dict(counter.most_common(limit)))


def main():
    game = os.path.join(os.environ['LOCALAPPDATA'], 'WarThunder', 'aces.vromfs.bin')
    vf = Vromfs(game)
    reader = BinaryReader.for_vromfs(vf)
    machine_paths = sorted(path for path in vf.files if path.startswith(FM)
                           and path.endswith('.blk') and '/' not in path[len(FM):])
    preset_paths = sorted(path for path in vf.files if path.startswith(PRESETS)
                          and path.endswith('.blk'))
    presets = {path: reader.parse(vf.files[path]) for path in preset_paths}
    kinds = Counter()
    old_forms = Counter()
    legacy_emitters = Counter()
    legacy_pairs = Counter()
    new_pairs = Counter()
    helicopter = Counter()
    mass = Counter()
    examples = defaultdict(list)
    legacy_machine_count = 0
    legacy_with_emitter = 0
    legacy_with_pair = 0
    helicopter_names = []
    for path in machine_paths:
        root = reader.parse(vf.files[path])
        old = children(root.block('weapon_presets'), 'preset')
        slots = children(root.block('WeaponSlots'), 'WeaponSlot')
        old_only = bool(old) and not bool(slots)
        kind = 'old_only' if old_only else 'both' if old and slots else 'new_only' if slots else 'neither'
        kinds[kind] += 1
        name = path[len(FM):-4]
        tags = root.block('unittags')
        tag_values = [str(v).lower() for _, _, v in tags.params] if tags else []
        is_helicopter = (root.get('fightAiBehaviour') == 'helicopter'
                         or 'helicopter' in str(root.get('type', '')).lower()
                         or any('helicopter' in v for v in tag_values))
        if is_helicopter:
            helicopter_names.append(name)
            helicopter[kind] += 1
            helicopter['total'] += 1
        if old_only:
            legacy_machine_count += 1
        emitter_locations = defaultdict(set)
        all_emitters = set()
        combinations = set()
        for old_preset in old:
            ref = norm_path(old_preset.get('blk'))
            file = presets.get(ref)
            if not file:
                if old_only:
                    old_forms['unresolved'] += 1
                if old_only and len(examples['unresolved']) < 5:
                    examples['unresolved'].append((name, old_preset.get('name'), ref))
                continue
            weapons = children(file, 'Weapon')
            form = ('slot_choice' if any(w.get('slot') is not None for w in weapons)
                    else 'direct_weapon' if any(w.get('blk') is not None for w in weapons)
                    else 'empty_or_other')
            if old_only:
                old_forms[form] += 1
                if file.block('hideNodes'):
                    old_forms[form + '_hideNodes'] += 1
                if len(examples[form]) < 5:
                    examples[form].append((name, old_preset.get('name'), ref,
                                           len(weapons), bool(file.block('hideNodes'))))
            if old_only and form == 'direct_weapon':
                present = frozenset(str(w.get('emitter')) for w in weapons
                                    if w.get('emitter') is not None)
                combinations.add(present)
                all_emitters.update(present)
                for w in weapons:
                    emitter = w.get('emitter')
                    if emitter:
                        emitter_locations[emitter].add((w.get('trigger'), norm_path(w.get('blk'))))
        if old_only:
            legacy_emitters['machines'] += 1
            legacy_emitters['distinct_emitters'] += len(all_emitters)
            legacy_emitters['distinct_combinations'] += len(combinations)
            legacy_emitters['emitters_with_multiple_weapon_refs'] += sum(
                len(refs) > 1 for refs in emitter_locations.values())
            for emitter, refs in emitter_locations.items():
                if len(refs) > 1 and len(examples['emitter_variants']) < 8:
                    examples['emitter_variants'].append((name, emitter, sorted(refs)[:4]))
            if all_emitters:
                legacy_with_emitter += 1
            side_groups = defaultdict(set)
            for emitter in all_emitters:
                parsed = side_key(emitter)
                if parsed:
                    side_groups[parsed[0]].add(parsed[1])
            pair_count = sum(sides == {'L', 'R'} for sides in side_groups.values())
            legacy_pairs['paired_keys'] += pair_count
            legacy_pairs['one_sided_keys'] += sum(len(sides) == 1 for sides in side_groups.values())
            if pair_count:
                legacy_with_pair += 1
                if len(examples['legacy_pair']) < 8:
                    examples['legacy_pair'].append((name, pair_count, sorted(all_emitters)[:12]))
        if is_helicopter:
            if kind == 'old_only' and len(examples['helicopter_old_only']) < 14:
                examples['helicopter_old_only'].append((name, len(old)))
            helicopter['with_old_presets'] += bool(old)
            helicopter['with_slots'] += bool(slots)
            for slot in slots:
                for variant in children(slot, 'WeaponPreset'):
                    for weapon in children(variant, 'Weapon'):
                        ref = norm_path(weapon.get('blk'))
                        helicopter['slot_weapons'] += 1
                        if weapon.get('mass') is not None:
                            mass['helicopter_slot_weapon_mass'] += 1
                            if len(examples['helicopter_mass']) < 8:
                                examples['helicopter_mass'].append((name, slot.get('index'),
                                                                    variant.get('name'), weapon.get('mass'), ref))
                        if 'container' in ref or 'pod' in ref:
                            helicopter['container_or_pod_refs'] += 1
                            if len(examples['helicopter_container']) < 8:
                                examples['helicopter_container'].append((name, slot.get('index'),
                                                                         variant.get('name'), ref))
        if slots:
            sides = defaultdict(lambda: defaultdict(set))
            for slot in slots:
                idx = slot.get('index')
                for variant in children(slot, 'WeaponPreset'):
                    for weapon in children(variant, 'Weapon'):
                        parsed = side_key(weapon.get('emitter'))
                        if parsed:
                            sides[parsed[0]][parsed[1]].add(idx)
            paired = [(key, groups) for key, groups in sides.items() if groups['L'] and groups['R']]
            if paired:
                new_pairs['machines_with_paired_emitter_names'] += 1
                new_pairs['paired_keys'] += len(paired)
                new_pairs['same_slot_keys'] += sum(
                    groups['L'] == groups['R'] for _, groups in paired)
                new_pairs['different_slot_keys'] += sum(
                    groups['L'] != groups['R'] for _, groups in paired)
                new_pairs['ambiguous_slot_keys'] += sum(
                    len(groups['L']) != 1 or len(groups['R']) != 1
                    for _, groups in paired)
                if len(examples['new_pair']) < 8:
                    examples['new_pair'].append((name, [(key, sorted(groups['L']), sorted(groups['R']))
                                                        for key, groups in paired[:4]]))
    print('Machine files', len(machine_paths), 'Preset files', len(preset_paths))
    report('Machine schemes', kinds)
    print('Old-only machines', legacy_machine_count, 'with emitters', legacy_with_emitter,
          'with lexical L/R emitter pair', legacy_with_pair)
    report('Old-only referenced preset forms', old_forms)
    report('Old-only emitter totals', legacy_emitters)
    report('Old-only emitter side keys', legacy_pairs)
    report('New-scheme emitter side keys', new_pairs)
    report('Helicopters', helicopter)
    report('Mass fields', mass)
    print('Helicopter names', ', '.join(helicopter_names[:30]))
    for label, rows in examples.items():
        print(label + ':')
        for row in rows:
            print(' ', row)


if __name__ == '__main__':
    main()
