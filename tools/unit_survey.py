"""Обзор всей техники игры для исследования запуска (docs/research/launch.md).

Источники: char.vromfs.bin (unittags, wpcost, shop), aces.vromfs.bin (файлы юнитов).
Выход: cache/units.json (по юниту) и сводка в stdout.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib import blk as B  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402

GAME = os.path.expandvars(r'%LOCALAPPDATA%\WarThunder')
FOLDERS = {'flightmodels': 'gamedata/flightmodels/', 'tankmodels': 'gamedata/units/tankmodels/',
           'ships': 'gamedata/units/ships/'}


def top_level_units(vf, prefix):
    out = {}
    for n in vf.files:
        if n.startswith(prefix) and n.endswith('.blk') and '/' not in n[len(prefix):]:
            out[n[len(prefix):-4]] = n
    return out


def shop_units(shop):
    names = set()

    def walk(b, depth):
        for x in b.blocks:
            # листья дерева магазина — блоки-юниты (внутри rank / группы)
            if depth >= 2 and x.name:
                names.add(x.name)
            walk(x, depth + 1)
    walk(shop, 0)
    return names


def main():
    ch = Vromfs(os.path.join(GAME, 'char.vromfs.bin'))
    rc = B.BinaryReader.for_vromfs(ch)
    tags = rc.parse(ch.files['config/unittags.blk'])
    wpcost = rc.parse(ch.files['config/wpcost.blk'])
    shop = rc.parse(ch.files['config/shop.blk'])
    in_cost = {b.name: b for b in wpcost.blocks}
    in_shop = shop_units(shop)

    aces = Vromfs(os.path.join(GAME, 'aces.vromfs.bin'))
    ra = B.BinaryReader.for_vromfs(aces)
    files = {k: top_level_units(aces, p) for k, p in FOLDERS.items()}

    units = {}
    for t in tags.blocks:
        u = {'type': t.get('type'), 'testFlight': t.get('testFlight'),
             'tags': [k for k, _, v in (t.block('tags').params if t.block('tags') else []) if v],
             'wpcost': t.name in in_cost, 'shop': t.name in in_shop,
             'country': in_cost[t.name].get('country') if t.name in in_cost else None,
             'folders': [k for k in FOLDERS if t.name.lower() in files[k]]}
        units[t.name] = u

    # файлы юнитов, которых нет в unittags (ИИ-модели, служебные)
    lower_units = {n.lower() for n in units}
    orphans = collections.Counter()
    for k, fs in files.items():
        for name in fs:
            if name not in lower_units:
                orphans[k] += 1

    # supportPlanes и allowSupportPlane у наземки и кораблей
    support = collections.Counter()
    support_units = {}
    for k in ('tankmodels', 'ships'):
        for name, path in files[k].items():
            try:
                b = ra.parse(aces.files[path])
            except Exception:  # noqa: BLE001
                continue
            sp = b.block('supportPlanes')
            if sp:
                cls = [x.get('class') for x in sp.blocks]
                support_units[name] = cls
                for c in cls:
                    support[(c or '').split('/')[0] if '/' in (c or '') else '(без папки)'] += 1
                for n in units:
                    if n.lower() == name:
                        units[n]['supportPlanes'] = cls

    out = os.path.join('cache', 'units.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(units, f, ensure_ascii=False, indent=0)

    by_type = collections.Counter(u['type'] for u in units.values())
    print('юнитов в unittags:', len(units), dict(by_type))
    print('в wpcost:', sum(u['wpcost'] for u in units.values()), ' в shop:', sum(u['shop'] for u in units.values()))
    print('без файла юнита в aces:', sum(1 for u in units.values() if not u['folders']))
    print('папки по типу:', dict(collections.Counter((u['type'], tuple(u['folders'])) for u in units.values())))
    print('файлы юнитов вне unittags:', dict(orphans))
    print('testFlight миссии (пример):', collections.Counter(u['testFlight'] for u in units.values()).most_common(8))
    print('без testFlight:', collections.Counter(u['type'] for u in units.values() if not u['testFlight']))
    print('supportPlanes:', len(support_units), 'машин, ссылки по папкам', dict(support))
    for n, c in sorted(support_units.items())[:40]:
        print('   ', n, c)
    print('unittags без wpcost:', [n for n, u in units.items() if not u['wpcost']][:40])
    print('wpcost без shop (первые 40):', [n for n, u in units.items() if u['wpcost'] and not u['shop']][:40])


if __name__ == '__main__':
    sys.exit(main())
