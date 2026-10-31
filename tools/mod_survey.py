"""Обзор модификаций, которые меняют блоки в файле машины (docs/research/modifications.md).

Для каждого блока из effects модификаций в файлах машин:
  - флаг invertEnableLogic модификации (общий справочник char.vromfs/config/modifications.blk);
  - есть ли такой блок в стоковой машине и содержит ли блок модификации всё стоковое (признак «замены целиком»);
  - сколько машин, где один и тот же блок меняют несколько модификаций (и есть ли у них group).
Выход — сводка в stdout.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib import blk as B  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402

GAME = os.path.expandvars(r'%LOCALAPPDATA%\WarThunder')
FOLDERS = {'танки': 'gamedata/units/tankmodels/', 'корабли': 'gamedata/units/ships/',
           'авиация': 'gamedata/flightmodels/'}


def sig(b):
    """Отпечаток блока для сравнения: параметры и вложенные блоки целиком (как текст)."""
    return B.to_text(b)


def children(b):
    return [sig(x) for x in b.blocks] + ['%s:%s=%r' % p for p in b.params]


def main():
    char = Vromfs(os.path.join(GAME, 'char.vromfs.bin'))
    root = B.BinaryReader.for_vromfs(char).parse(char.files['config/modifications.blk'])
    gmods = root.block('modifications') or root
    aces = Vromfs(os.path.join(GAME, 'aces.vromfs.bin'))
    rd = B.BinaryReader.for_vromfs(aces)
    for kind, pref in FOLDERS.items():
        stat = collections.defaultdict(collections.Counter)
        multi = collections.Counter()
        multi_ex = {}
        for path, data in aces.files.items():
            if not (path.startswith(pref) and path.endswith('.blk') and '/' not in path[len(pref):]):
                continue
            try:
                u = rd.parse(data)
            except Exception:  # noqa: BLE001
                continue
            mods = u.block('modifications')
            if not mods:
                continue
            per_block = collections.defaultdict(list)
            for m in mods.blocks:
                eff = m.block('effects')
                g = gmods.block(m.name)
                inv = bool(g and g.get('invertEnableLogic'))
                grp = g.get('group') if g else None
                for x in (eff.blocks if eff else []):
                    s = stat[x.name]
                    s['всего'] += 1
                    s['инверсия' if inv else 'обычная'] += 1
                    base = u.block(x.name)
                    if base is None:
                        s['в стоке нет'] += 1
                    else:
                        bc, mc = children(base), set(children(x))
                        s['содержит весь сток' if all(c in mc for c in bc) else 'НЕ содержит весь сток'] += 1
                    per_block[x.name].append((m.name, grp, inv))
            for name, lst in per_block.items():
                if len(lst) > 1:
                    multi[name] += 1
                    multi_ex.setdefault(name, (path.split('/')[-1], lst[:4]))
        print('==', kind)
        for name, s in sorted(stat.items(), key=lambda kv: -kv[1]['всего']):
            print('  %-20s %s' % (name, dict(s)))
        print('  один блок меняют несколько модификаций:', dict(multi))
        for name, ex in multi_ex.items():
            print('     ', name, ex)


if __name__ == '__main__':
    sys.exit(main())
