"""Обзор полей блоков боеприпасов (bullet, rocket, bomb, torpedo) по клону датамайна War Thunder.

Только чтение. Источник — https://github.com/gszabi99/War-Thunder-Datamine (частичный клон), файлы
`aces.vromfs.bin_u/gamedata/weapons/**`: `.blkx` (JSON, вывод wt_ext_cli) или текстовые `.blk` (wtlib.blk).
Запуск:
  python tools/ammo_survey_dm.py <клон датамайна> [--kind bullet] [--type-top 8] [--min 0.02] [--grep РЕГВЫР] [--json out.json]
Частоты: «экз.» — число блоков боеприпаса (один снаряд повторяется в лентах и копиях оружия);
«уник.» — число разных блоков (по содержимому). Путь поля — относительно блока боеприпаса, «/» — вложенный блок,
«[]» — повторяющийся блок (несколько одноимённых блоков подряд).
"""
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

KINDS = ('bullet', 'rocket', 'bomb', 'torpedo')
SUBDIR = os.path.join('aces.vromfs.bin_u', 'gamedata', 'weapons')
# Поля, нужные редактору боеприпасов: показываются и ниже порога частоты (если встречаются хотя бы в 3 блоках).
FOCUS = re.compile(r'armorpower|armorPower|stucking|cumulative|kinetic|demarre|lanzOdermatt|nuclear|yield|'
                   r'fuse|Fuse|explos|hitpower|hitPower|damageMass|Caliber|guidance|seeker|sabot|'
                   r'penetration|subcaliber|shatter/|underwater|maxSpeed|speed|mass|warhead', re.I)
# Блоки-справочники (реакции на материалы, части модели снаряда): внутрь не спускаемся, считаем сам блок.
COLLAPSE = {'collisions', 'shatterCollisions', 'DamageParts', 'DamageEffects', 'explosionSmoke'}
# Хвосты bulletType, которые не меняют вид снаряда (носитель, длина сердечника и т.п.).
TYPE_SUFFIX = re.compile(r'(_(tank|naval|ship|boat|heli|air|ground|rocket|bomb|torpedo|long|l\d+|'
                         r'mp|vt|small|big|light|heavy|ussr|usa|ger|uk|jp|it|fr|cn|sw|il))+$')


# ---------------------------------------------------------------- чтение файлов в общий вид
# Узел — список пар (имя, значение); значение — скаляр/список (параметр) или узел (блок).

def from_json(value):
    """JSON wt_ext_cli: dict — блок; список словарей — повторяющийся блок; прочие списки — векторы."""
    items = []
    for key, v in value.items():
        if isinstance(v, dict):
            items.append((key, from_json(v)))
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            items.extend((key, from_json(x)) for x in v)
        else:
            items.append((key, v))
    return Node(items)


def from_blk(b):
    items = [(k, v) for k, t, v in b.params if t != 'include']
    items += [(c.name, from_blk(c)) for c in b.blocks]
    return Node(items)


class Node(list):
    def get(self, key):
        return next((v for k, v in self if k == key and not isinstance(v, Node)), None)


def load(path):
    with open(path, 'rb') as f:
        data = f.read()
    if path.endswith('.blkx'):
        return from_json(json.loads(data.decode('utf-8')))
    from wtlib import blk  # только для текстовых .blk; модуль требует zstandard
    return from_blk(blk.parse_text(data.decode('utf-8'), lenient=True))


# ---------------------------------------------------------------- обход

def projectiles(node, chain=()):
    """Блоки боеприпаса и путь к ним; внутрь найденного блока не спускаемся (суббоеприпасы — его поля)."""
    for key, v in node:
        if not isinstance(v, Node):
            continue
        if key in KINDS:
            yield chain + (key,), key, v
        else:
            yield from projectiles(v, chain + (key,))


def fields(node, prefix=''):
    """Пути полей и блоков внутри блока боеприпаса; повтор одноимённого блока помечается []."""
    seen = Counter(k for k, v in node if isinstance(v, Node))
    for key, v in node:
        if isinstance(v, Node):
            path = prefix + key + ('[]' if seen[key] > 1 else '')
            yield path + '/', None
            if key not in COLLAPSE:
                yield from fields(v, path + '/')
        else:
            yield prefix + key, v


def digest(node):
    return hashlib.md5(repr(node).encode('utf-8')).hexdigest()


def type_group(bt):
    if not isinstance(bt, str) or not bt:
        return '(нет bulletType)'
    return TYPE_SUFFIX.sub('', bt.lower()) or bt.lower()


# ---------------------------------------------------------------- сбор

def survey(root):
    base = os.path.join(root, SUBDIR)
    if not os.path.isdir(base):
        sys.exit(f'нет папки {base}: нужен клон War-Thunder-Datamine с aces.vromfs.bin_u/gamedata/weapons')
    st = {k: {'n': 0, 'uniq': set(), 'files': set(), 'types': Counter(), 'raw_types': Counter(),
              'fields': Counter(), 'by_type': defaultdict(Counter), 'values': defaultdict(Counter),
              'examples': {}} for k in KINDS}
    files = errors = 0
    for dirpath, _dirs, names in os.walk(base):
        for name in sorted(names):
            if not name.endswith(('.blk', '.blkx')):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, base).replace(os.sep, '/')
            files += 1
            try:
                tree = load(path)
            except Exception as e:  # noqa: BLE001 — обзор, не валидация
                errors += 1
                print(f'! {rel}: {e}', file=sys.stderr)
                continue
            for chain, kind, node in projectiles(tree):
                s = st[kind]
                h = digest(node)
                s['n'] += 1
                s['files'].add(rel)
                bt = node.get('bulletType')
                grp = type_group(bt)
                s['types'][grp] += 1
                s['raw_types'][bt if isinstance(bt, str) else '(нет)'] += 1
                if h in s['uniq']:
                    continue
                s['uniq'].add(h)
                s.setdefault('uniq_types', Counter())[grp] += 1
                paths = set()
                for p, v in fields(node):
                    paths.add(p)
                    if v is not None and not isinstance(v, list) and len(s['values'][p]) < 400:
                        s['values'][p][v if not isinstance(v, float) else round(v, 4)] += 1
                for p in paths:
                    s['fields'][p] += 1
                    s['by_type'][grp][p] += 1
                    s['examples'].setdefault(p, rel + ':' + '/'.join(chain))
    return files, errors, st


# ---------------------------------------------------------------- вывод

def is_focus(path):
    return bool(FOCUS.search(path))


def report(files, errors, st, type_top, min_share, only, grep=None):
    out = [f'Файлов BLK: {files}, ошибок разбора: {errors}', '']
    for kind in KINDS:
        if only and kind != only:
            continue
        s = st[kind]
        u = len(s['uniq'])
        if not s['n']:
            continue
        ut = s['uniq_types']
        out.append(f'## {kind}: экз. {s["n"]}, уник. {u}, файлов {len(s["files"])}')
        out.append('Виды (группа bulletType, уник.): ' + ', '.join(f'{t}={n}' for t, n in ut.most_common(40)))
        out.append('Сырые bulletType (экз.): ' + ', '.join(f'{t}={n}' for t, n in s['raw_types'].most_common(25)))
        top = [t for t, _ in ut.most_common(type_top)]
        out.append('')
        out.append('| поле | уник. | ' + ' | '.join(top) + ' | значения (частые) |')
        out.append('|---|---:|' + '---:|' * len(top) + '---|')
        for p, n in sorted(s['fields'].items(), key=lambda x: (-x[1], x[0])):
            if grep and not re.search(grep, p):
                continue
            if n / u < min_share and not (is_focus(p) and n >= 3):
                continue
            cells = []
            for t in top:
                tn = ut[t]
                c = s['by_type'][t][p]
                cells.append(f'{100 * c // tn}%' if c else '·')
            vals = s['values'].get(p)
            vs = ', '.join(f'{v}×{c}' for v, c in vals.most_common(4)) if vals else ''
            out.append(f'| `{p}` | {n} | ' + ' | '.join(cells) + f' | {vs[:90]} |')
        out.append('')
        out.append(f'Столбцы видов — доля уникальных блоков вида с этим полем; размеры видов: '
                   + ', '.join(f'{t}={ut[t]}' for t in top))
        out.append('')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', help='корень клона War-Thunder-Datamine')
    ap.add_argument('--kind', choices=KINDS, help='только один вид боеприпаса')
    ap.add_argument('--type-top', type=int, default=8, help='сколько видов bulletType показывать столбцами')
    ap.add_argument('--min', type=float, default=0.02, help='порог доли уникальных блоков для показа поля')
    ap.add_argument('--grep', help='показывать только поля, путь которых подходит под регулярное выражение')
    ap.add_argument('--json', help='полный результат в JSON (все поля, частоты по видам, примеры файлов)')
    a = ap.parse_args()
    files, errors, st = survey(a.root)
    print(report(files, errors, st, a.type_top, a.min, a.kind, a.grep))
    if a.json:
        dump = {k: {'instances': s['n'], 'unique': len(s['uniq']), 'files': len(s['files']),
                    'types': dict(s['uniq_types'] if 'uniq_types' in s else {}),
                    'raw_types': dict(s['raw_types']), 'fields': dict(s['fields']),
                    'by_type': {t: dict(c) for t, c in s['by_type'].items()},
                    'examples': s['examples'],
                    'values': {p: [[str(v), c] for v, c in vc.most_common(10)] for p, vc in s['values'].items()}}
                for k, s in st.items()}
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(dump, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
