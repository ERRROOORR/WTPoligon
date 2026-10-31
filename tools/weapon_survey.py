"""Обзор оружия, боеприпасов и выбора лент в архивных BLK War Thunder.

Только чтение aces.vromfs.bin, char.vromfs.bin и mis.vromfs.bin.
Запуск: PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/weapon_survey.py
Частоты параметров и блоков означают число файлов, где имя встречается хотя бы раз.
"""
from collections import Counter, defaultdict
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib.blk import BinaryReader  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402

GAME = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'WarThunder')
PREFIX = 'gamedata/weapons/'
GROUPS = {
    '.': 'пушки/пулемёты и прочее в корне',
    'rocketguns': 'ракетные пусковые',
    'bombguns': 'бомбовые держатели',
    'torpedoes': 'торпедные аппараты',
    'groundmodels_weapons': 'наземное оружие',
    'navalmodels_weapons': 'морское оружие',
}
PROJECTILES = {'bullet', 'rocket', 'bomb', 'torpedo'}
KEYS = ('shotFreq', 'reloadTime', 'bullets', 'mass', 'speed', 'caliber',
        'explosiveMass', 'explosiveType', 'bulletType', 'armorpower',
        'fuse', 'proximityFuse')


def walk(block, chain=()):
    for child in block.blocks:
        current = chain + (child.name,)
        yield current, child
        yield from walk(child, current)


def show(counter, total, limit=18):
    ordered = counter.most_common(limit)
    return ', '.join(f'{key}={n}/{total}' for key, n in ordered) or '—'


def main():
    aces = Vromfs(os.path.join(GAME, 'aces.vromfs.bin'))
    char = Vromfs(os.path.join(GAME, 'char.vromfs.bin'))
    mis = Vromfs(os.path.join(GAME, 'mis.vromfs.bin'))
    ar, cr, mr = (BinaryReader.for_vromfs(v) for v in (aces, char, mis))
    mods_root = cr.parse(char.get('config/modifications.blk'))
    mods = mods_root.block('modifications') or mods_root
    additive = defaultdict(list)
    for mod in mods.blocks:
        effects = mod.block('effects')
        if effects:
            for key, _typ, value in effects.params:
                if key == 'additiveBulletMod' and isinstance(value, str):
                    additive[value.lower()].append(mod.name)

    folders = Counter()
    stats = defaultdict(lambda: {'n': 0, 'top': Counter(), 'blocks': Counter(),
                                  'projectiles': defaultdict(Counter),
                                  'projectile_n': Counter(), 'nested': defaultdict(Counter),
                                  'examples': {}})
    matches = []
    named_blocks = []
    errors = []
    paths = sorted(p for p in aces.files if p.startswith(PREFIX) and p.endswith('.blk'))
    for path in paths:
        rel = path[len(PREFIX):]
        folder = rel.split('/')[0] if '/' in rel else '.'
        folders[folder] += 1
        try:
            root = ar.parse(aces.files[path])
        except Exception as exc:  # keep the denominator and report failures
            errors.append((path, str(exc)))
            continue
        if folder not in GROUPS:
            continue
        s = stats[folder]
        s['n'] += 1
        s['top'].update({p[0] for p in root.params})
        s['blocks'].update({b.name for b in root.blocks})
        for kind in PROJECTILES:
            found = [b for b in root.blocks if b.name == kind]
            if found:
                s['projectile_n'][kind] += 1
                s['projectiles'][kind].update({p[0] for b in found for p in b.params})
                s['nested'][kind].update({c.name for b in found for c in b.blocks})
                s['examples'].setdefault(kind, path)
        for chain, b in walk(root):
            if b.name and b.name.lower() in additive:
                named_blocks.append((path, '/'.join(chain), b.name, additive[b.name.lower()][:3]))
            if b.name in PROJECTILES:
                for key, _typ, value in b.params:
                    if key in ('bulletName', 'bulletType') and isinstance(value, str) and value.lower() in additive:
                        matches.append((path, '/'.join(chain), key, value, additive[value.lower()][:3]))

    print(f'АРХИВ aces: {len(paths)} *.blk под {PREFIX}; ошибок разбора: {len(errors)}')
    print('ПАПКИ (все *.blk):')
    for folder, n in sorted(folders.items(), key=lambda x: (-x[1], x[0])):
        print(f'  {folder}: {n}')
    print(f'МОДИФИКАЦИИ: {sum(map(len, additive.values()))} записей additiveBulletMod, {len(additive)} уникальных значений')
    for folder in GROUPS:
        s = stats[folder]
        n = s['n']
        print(f'\nКАТЕГОРИЯ {folder} ({GROUPS[folder]}): {n} разобрано')
        print('  верхние параметры, топ: ' + show(s['top'], n))
        print('  верхние параметры, ключевые: ' + show(Counter({k: s['top'][k] for k in KEYS if s['top'][k]}), n, 30))
        print('  верхние блоки: ' + show(s['blocks'], n, 25))
        for kind in sorted(s['projectile_n']):
            count = s['projectile_n'][kind]
            params = s['projectiles'][kind]
            print(f'  {kind}: {count}/{n} файлов; пример {s["examples"][kind]}')
            print('    параметры, топ: ' + show(params, count, 25))
            print('    параметры, ключевые: ' + show(Counter({k: params[k] for k in KEYS if params[k]}), count, 30))
            print('    вложенные блоки: ' + show(s['nested'][kind], count, 18))
            special = {k: v for k, v in params.items() if any(x in k.lower() for x in ('armor', 'damage', 'fuse', 'prox'))}
            print('    броня/урон/взрыватели: ' + show(Counter(special), count, 30))
    print(f'\nСВЯЗИ С additiveBulletMod: совпадений имени блока={len(named_blocks)}, bulletName/bulletType={len(matches)}')
    selected = []
    for row in named_blocks:
        if row[2] == '120mm_M829A_APDS_FS':
            selected.append(row)
            break
    for row in named_blocks:
        if row[0] not in {x[0] for x in selected}:
            selected.append(row)
        if len(selected) >= 3:
            break
    for row in selected:
        print('  блок:', *row, sep=' | ')
    for row in matches[:12]:
        print('  поле:', *row, sep=' | ')
    print('  примеры значений из справочника:')
    for name, linked in list(additive.items())[:5]:
        print(f'    {name}: {linked[:3]}')

    mission_count = 0
    with_ammo = 0
    mission_examples = []
    ammo_values = Counter()
    for path, data in sorted(mis.files.items()):
        if not path.startswith('gamedata/missions/') or not path.endswith('.blk'):
            continue
        mission_count += 1
        try:
            root = mr.parse(data)
        except Exception as exc:
            errors.append((path, str(exc)))
            continue
        found = []
        for chain, block in walk(root):
            fields = {k: v for k, _t, v in block.params if k in {f'bullets{i}' for i in range(4)} | {f'bulletsCount{i}' for i in range(4)}}
            active = [(k, v) for k, v in fields.items() if k.startswith('bullets') and not k.startswith('bulletsCount') and v not in ('', None)]
            if active:
                found.append(('/'.join(chain), fields))
                ammo_values.update(str(v) for _k, v in active)
        if found:
            with_ammo += 1
            if len(mission_examples) < 8 and any(
                    any(v > 0 for k, v in fields.items() if k.startswith('bulletsCount'))
                    for _chain, fields in found):
                mission_examples.append((path, found[:2]))
    print(f'\nМИССИИ: {mission_count} *.blk, с непустыми bullets0..3: {with_ammo}')
    print('  частые значения:', ammo_values.most_common(15))
    weapon_names = {row[2].lower() for row in named_blocks}
    print('  значения bullets*: уникальных=%d, совпадают с additiveBulletMod=%d, '
          'с именованным блоком оружия=%d' %
          (len(ammo_values), sum(v.lower() in additive for v in ammo_values),
           sum(v.lower() in weapon_names for v in ammo_values)))
    for path, items in mission_examples:
        for chain, fields in items:
            print(f'  {path} | {chain} | {fields}')
    if errors:
        print(f'ОШИБКИ РАЗБОРА ({len(errors)}), первые 10:')
        for path, reason in errors[:10]:
            print(f'  {path}: {reason}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
