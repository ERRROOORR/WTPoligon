"""Сверка своего парсера бинарных BLK с wt_ext_cli (BlkText) по всем BLK всех архивов игры.

Для каждого бинарного BLK:
  1) моё дерево == дерево из эталонного текста (числа сравниваются как float32);
  2) круговая проверка: to_text(моё) -> parse_text -> то же дерево (запись без потерь).
Подготовка эталона:
  tools\\ext\\wt_ext_cli.exe unpack_vromf -i <игра>\\<имя>.vromfs.bin -o cache\\ext_BlkText --format BlkText
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib import blk as B  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402

GAME = os.path.expandvars(r'%LOCALAPPDATA%\WarThunder')
ARCHIVES = 'aces char game gui lang mis webUi wwdata'.split()


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def norm(t, v):
    if t == 'r':
        return f32(v)
    if t in ('p2', 'p3', 'p4'):
        return tuple(f32(x) for x in v)
    if t == 'm':
        return tuple(tuple(f32(x) for x in r) for r in v)
    return v


def diff(a, b, path=''):
    """Первое отличие двух деревьев или None."""
    if len(a.params) != len(b.params):
        return '%s: параметров %d / %d' % (path, len(a.params), len(b.params))
    for (ka, ta, va), (kb, tb, vb) in zip(a.params, b.params):
        if ka != kb or ta != tb:
            return '%s: параметр %s:%s / %s:%s' % (path, ka, ta, kb, tb)
        if norm(ta, va) != norm(tb, vb):
            return '%s/%s:%s: %r / %r' % (path, ka, ta, va, vb)
    if len(a.blocks) != len(b.blocks):
        return '%s: блоков %d / %d' % (path, len(a.blocks), len(b.blocks))
    for x, y in zip(a.blocks, b.blocks):
        if x.name != y.name:
            return '%s: блок %r / %r' % (path, x.name, y.name)
        d = diff(x, y, path + '/' + str(x.name))
        if d:
            return d
    return None


def fix_ref_ip4(text):
    # wt_ext_cli 0.6.6 печатает ip4 без последней запятой: "4, 4, 4 4"
    out = []
    for line in text.split('\n'):
        if ':ip4 = ' in line:
            head, val = line.split(' = ', 1)
            parts = val.replace(',', ' ').split()
            line = head + ' = ' + ', '.join(parts)
        out.append(line)
    return '\n'.join(out)


def swap_ref_colors(b):
    # wt_ext_cli 0.6.6 печатает байты цвета в порядке хранения (B, G, R, A) как r, g, b, a.
    # В DagorEngine E3DCOLOR = {b, g, r, a} (dag_e3dColor.h), значит верно (raw2, raw1, raw0, raw3).
    b.params = [(k, t, (v[2], v[1], v[0], v[3]) if t == 'c' else v) for k, t, v in b.params]
    for x in b.blocks:
        swap_ref_colors(x)


def main():
    stats = collections.Counter()
    problems = collections.defaultdict(list)
    # аргументы: [архивы через запятую] [каждый N-й файл]
    archives = sys.argv[1].split(',') if len(sys.argv) > 1 else ARCHIVES
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    for v in archives:
        vf = Vromfs(os.path.join(GAME, v + '.vromfs.bin'))
        rd = B.BinaryReader.for_vromfs(vf)
        root = os.path.join('cache', 'ext_BlkText', v + '.vromfs.bin_u')
        for name, data in list(vf.files.items())[::step]:
            if not name.endswith('.blk'):
                continue
            if not B.is_binary(data):
                stats['текстовые в архиве'] += 1
                continue
            stats['бинарных'] += 1
            stats['тип %d' % data[0]] += 1
            try:
                mine = rd.parse(data)
            except Exception as e:  # noqa: BLE001
                problems['наш разбор упал'].append('%s/%s: %s' % (v, name, e))
                continue
            # круговая проверка
            try:
                back = B.parse_text(B.to_text(mine))
                d = diff(mine, back)
                if d:
                    problems['круговая проверка'].append('%s/%s: %s' % (v, name, d))
                else:
                    stats['круговая ок'] += 1
            except Exception as e:  # noqa: BLE001
                problems['круговая: разбор упал'].append('%s/%s: %s' % (v, name, e))
            # эталон
            ref_path = os.path.join(root, name.lstrip('/'))
            if not os.path.exists(ref_path):
                problems['нет эталона'].append('%s/%s' % (v, name))
                continue
            with open(ref_path, encoding='utf-8', errors='surrogateescape') as f:
                ref_text = fix_ref_ip4(f.read())
            try:
                ref = B.parse_text(ref_text)
            except Exception as e:  # noqa: BLE001
                problems['эталонный текст не разобрался'].append('%s/%s: %s' % (v, name, e))
                continue
            swap_ref_colors(ref)
            d = diff(mine, ref)
            if d:
                problems['отличие от эталона'].append('%s/%s: %s' % (v, name, d))
            else:
                stats['совпало с эталоном'] += 1
        print(v, dict(stats), flush=True)
    print('\nИТОГ:', dict(stats))
    for k, lst in problems.items():
        print('\n== %s: %d' % (k, len(lst)))
        for s in lst[:15]:
            print('   ', s)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
