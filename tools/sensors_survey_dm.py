"""Обзор сенсоров War Thunder по публичному датамайну; только чтение.

Источник — локальный клон https://github.com/gszabi99/War-Thunder-Datamine (файлы `*.blkx` — BLK,
выгруженный в JSON). Достаточно частичного клона:
  git clone --depth 1 --filter=blob:none --sparse <url> wtdm
  git -C wtdm sparse-checkout set --no-cone /aces.vromfs.bin_u/gamedata/sensors/ \
      /aces.vromfs.bin_u/gamedata/countermeasures/ '/aces.vromfs.bin_u/gamedata/flightmodels/*.blkx' \
      '/aces.vromfs.bin_u/gamedata/units/tankmodels/*.blkx' '/aces.vromfs.bin_u/gamedata/units/ships/*.blkx' \
      /aces.vromfs.bin_u/gamedata/units/air_defence/ \
      '/aces.vromfs.bin_u/gamedata/weapons/rocketguns/*countermeasure*' \
      '/aces.vromfs.bin_u/gamedata/weapons/rocketguns/*chaff*' '/aces.vromfs.bin_u/gamedata/weapons/rocketguns/*flare*'
Запуск: PYTHONIOENCODING=utf-8 python tools/sensors_survey_dm.py <путь к клону>

Частота — число объектов указанного уровня (файлов, блоков), где имя встретилось хотя бы раз.
В JSON датамайна повторённый блок становится списком; списки скаляров (Point2/3, повтор параметра)
не различаются — поэтому такие значения считаются одним полем.
"""
from collections import Counter, defaultdict
import glob
import json
import os
import subprocess
import sys

TOP = 25      # сколько полей печатать в строке частот
EX = 4        # сколько примеров

KIND_RU = {
    'radar': 'РЛС (активная)', 'radar/infraRed': 'ИК-трекер / ИКСТ (IRST)',
    'radar/optic': 'оптический/ТВ-трекер', 'radar/radarIntercept': 'пассивная РТР (radarIntercept)',
    'rwr': 'СПО (RWR)', 'mlws': 'МАВС / УФ-предупреждение о ракетах (MLWS)',
    'lws': 'предупреждение о лазерном облучении (LWS)', 'lds': 'лазерный дальномер/целеуказатель (LDS)',
    'sonar': 'гидроакустика', 'fsm': 'служебный (только автомат состояний)',
}


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def items(v):
    """Блок может быть словарём или списком повторённых блоков."""
    if isinstance(v, dict):
        return [v]
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    return []


def kv(d, name):
    """Значение по имени без учёта регистра (в BLK встречается `Sensor` и `sensor`)."""
    if not isinstance(d, dict):
        return None
    for k, v in d.items():
        if k.lower() == name.lower():
            return v
    return None


def is_block(v):
    return bool(items(v))


def kind_of(d):
    t = d.get('type')
    if isinstance(t, list):          # дубль `type` (su_rp-1_*)
        t = t[0]
    if t is None:
        return 'fsm'
    if t != 'radar':
        return t
    vis = set()
    for tr in items(d.get('transivers')):
        for _, sub in tr.items():
            for x in items(sub):
                vis.add(x.get('visibilityType', 'radar'))
    vis.discard('radar')
    return 'radar/' + sorted(vis)[0] if vis else 'radar'


def short(v, n=60):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n - 1] + '…'


def line(title, counter, total, limit=TOP):
    print(f'  {title} (из {total}): ' + ', '.join(f'{k} {n}' for k, n in counter.most_common(limit)))


def numstat(vals):
    vals = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not vals:
        return '—'
    vals.sort()
    return f'n={len(vals)} мин {vals[0]:g} медиана {vals[len(vals) // 2]:g} макс {vals[-1]:g}'


def walk(o, path=()):
    """(путь из имён блоков, имя параметра, значение) для всех скалярных параметров."""
    if isinstance(o, dict):
        for k, v in o.items():
            if is_block(v):
                for x in items(v):
                    yield from walk(x, path + (k,))
            else:
                yield path, k, v


def norm_ref(s):
    """'gameData/sensors/X.blk' -> 'gamedata/sensors/x.blkx' (датамайн — нижний регистр)."""
    s = s.replace('\\', '/').lower()
    while '//' in s:
        s = s.replace('//', '/')
    return s[:-4] + '.blkx' if s.endswith('.blk') else s


def generic_path(path):
    """Путь блока с обобщением имени модификации/слота: modifications/<мод>/effects/... ."""
    out = []
    for i, p in enumerate(path):
        out.append('<мод>' if i and path[i - 1] == 'modifications' else p)
    return '/'.join(out)


# ---------------------------------------------------------------- сенсоры

def survey_sensors(gd):
    files = sorted(glob.glob(os.path.join(gd, 'sensors', '**', '*.blkx'), recursive=True))
    by_kind = defaultdict(list)
    data = {}
    for f in files:
        rel = os.path.relpath(f, gd).replace(os.sep, '/')
        try:
            d = load(f)
        except Exception as e:      # noqa: BLE001
            print('ОШИБКА разбора', rel, e)
            continue
        data[rel] = d
        by_kind[kind_of(d)].append(rel)

    print(f'\n=== Файлы сенсоров: {len(data)} (gamedata/sensors/**, из них naval/: '
          f'{sum(1 for r in data if "/naval/" in r)})')
    for k, rels in sorted(by_kind.items(), key=lambda x: -len(x[1])):
        print(f'  {k:22} {len(rels):4}  {KIND_RU.get(k, "?")}; примеры: '
              + ', '.join(r.split('/', 1)[1] for r in rels[:EX]))

    for k, rels in sorted(by_kind.items(), key=lambda x: -len(x[1])):
        print(f'\n--- {k} — {KIND_RU.get(k, "?")}: {len(rels)} файлов')
        top = Counter()
        for r in rels:
            top.update(data[r].keys())
        line('поля верхнего уровня', top, len(rels), 50)
        if k.startswith('radar'):
            radar_details(data, rels)
        elif k == 'rwr':
            rwr_details(data, rels)
        elif k in ('mlws', 'lws', 'lds', 'sonar'):
            simple_details(data, rels)
    return data, by_kind


def radar_details(data, rels):
    tr_fields, tr_names, rx_fields, ant_fields = Counter(), Counter(), Counter(), Counter()
    sp_types, sp_fields, sp_names, sig_fields = Counter(), Counter(), Counter(), Counter()
    ranges, range_max, power, band, rcs = [], [], [], [], []
    n_tr = n_sp = n_sig = 0
    fsm_ex = Counter()
    for r in rels:
        d = data[r]
        for tr in items(d.get('transivers')):
            for name, sub in tr.items():
                for x in items(sub):
                    n_tr += 1
                    tr_names[name] += 1
                    tr_fields.update(x.keys())
                    ranges.append(x.get('range'))
                    range_max.append(x.get('rangeMax'))
                    power.append(x.get('power'))
                    band.append(x.get('band'))
                    rcs.append(x.get('rcs'))
                    for rx in items(x.get('receiver')):
                        rx_fields.update(rx.keys())
                        ranges.append(rx.get('range'))
                        range_max.append(rx.get('rangeMax'))
                    for a in items(x.get('antenna')) + [a for rx in items(x.get('receiver'))
                                                        for a in items(rx.get('antenna'))]:
                        ant_fields.update(a.keys())
        for sp in items(d.get('scanPatterns')):
            for name, sub in sp.items():
                for x in items(sub):
                    n_sp += 1
                    sp_names[name] += 1
                    sp_types[str(x.get('type'))] += 1
                    sp_fields.update(x.keys())
        for sg in items(d.get('signals')):
            for _, sub in sg.items():
                for x in items(sub):
                    n_sig += 1
                    sig_fields.update(x.keys())
        for fs in items(d.get('fsms')):
            fsm_ex.update(fs.keys())
    line('transivers: имена трансиверов', tr_names, n_tr)
    line('transivers/<имя>: поля', tr_fields, n_tr, 40)
    line('transivers/<имя>/receiver: поля', rx_fields, n_tr)
    line('…/antenna: поля', ant_fields, n_tr)
    print(f'  дальность range: {numstat(ranges)}; rangeMax: {numstat(range_max)}')
    print(f'  power: {numstat(power)}; band: {Counter(short(b) for b in band if b is not None).most_common()}'
          f'; rcs: {numstat(rcs)}')
    line('scanPatterns: имена', sp_names, n_sp)
    line('scanPatterns/<имя>/type', sp_types, n_sp)
    line('scanPatterns/<имя>: поля', sp_fields, n_sp, 40)
    line('signals/<имя>: поля', sig_fields, n_sig, 40)
    line('fsms: имена автоматов', fsm_ex, len(rels))
    srs = Counter()
    for r in rels:
        for s in items(data[r].get('scopeRangeSets')):
            srs.update(s.keys())
    line('scopeRangeSets: имена наборов', srs, len(rels))
    # примеры дальностей по файлам
    ex = []
    for r in rels[:400]:
        for tr in items(data[r].get('transivers')):
            for name, sub in tr.items():
                for x in items(sub):
                    if 'range' in x:
                        ex.append((r.split('/', 1)[1], name, x.get('range'), x.get('rangeMax'), x.get('band')))
    for e in ex[:EX]:
        print('   пример:', ' | '.join(map(str, e)))
    for r in rels:
        if data[r].get('scopeRangeSets'):
            print('   пример scopeRangeSets/scanPatternSets:', r.split('/', 1)[1],
                  short(data[r]['scopeRangeSets'], 120), short(data[r].get('scanPatternSets'), 160))
            break


def rwr_details(data, rels):
    rec, grp, bands, ranges = Counter(), Counter(), Counter(), []
    n_rec = n_grp = 0
    for r in rels:
        d = data[r]
        ranges.append(d.get('range'))
        for k in d:
            if k.startswith('band') and k[4:].isdigit():
                bands[k] += 1
        for rc in items(d.get('receivers')):
            for _, sub in rc.items():
                for x in items(sub):
                    n_rec += 1
                    rec.update(x.keys())
        for g in items(d.get('groups')):
            for _, sub in g.items():
                for x in items(sub):
                    n_grp += 1
                    grp.update(x.keys())
    print(f'  range: {numstat(ranges)}')
    line('bandN (диапазоны, которые слышит СПО)', bands, len(rels))
    line('receivers/<имя>: поля', rec, n_rec)
    line('groups/<имя>: поля', grp, n_grp)
    for r in rels[:EX]:
        d = data[r]
        print('   пример:', r.split('/', 1)[1], 'range', d.get('range'),
              'bands', [k for k in d if k.startswith('band') and d[k] is True])


def simple_details(data, rels):
    rec = Counter()
    n = 0
    for r in rels:
        for rc in items(data[r].get('receivers')):
            for _, sub in rc.items():
                for x in items(sub):
                    n += 1
                    rec.update(x.keys())
    if n:
        line('receivers/<имя>: поля', rec, n)
    for r in rels[:EX]:
        d = data[r]
        print('   пример:', r.split('/', 1)[1], short({k: v for k, v in d.items() if not is_block(v)}, 200))


# ---------------------------------------------------------------- машины

CLASSES = (('самолёт', 'flightmodels'), ('вертолёт', 'flightmodels'),
           ('наземная', 'units/tankmodels'), ('корабль', 'units/ships'), ('ПВО-объект', 'units/air_defence'))


def vehicle_class(d, folder):
    if folder == 'flightmodels':
        return 'вертолёт' if 'helicopter' in d else 'самолёт'
    return dict((f, c) for c, f in CLASSES)[folder]


def survey_vehicles(gd, sensors, kinds):
    kind_by_file = {r: k for k, rels in kinds.items() for r in rels}
    where = Counter()               # обобщённый путь -> вхождений
    where_ex = {}
    per_class = Counter()
    with_sensors = Counter()
    entry_fields = Counter()
    n_entries = 0
    missing = Counter()
    kinds_by_class = defaultdict(Counter)
    cm_where, cm_ex, cm_entry = Counter(), {}, Counter()
    cm_launch = Counter()           # Weapon с trigger=countermeasures: blk
    cm_bullets = defaultdict(list)
    cm_weapon_fields = Counter()
    threat = 0
    threat_ex = []
    avionics = Counter()
    for _, folder in CLASSES[1:]:
        for f in sorted(glob.glob(os.path.join(gd, folder, '*.blkx'))):
            try:
                d = load(f)
            except Exception as e:      # noqa: BLE001
                print('ОШИБКА разбора', f, e)
                continue
            if not isinstance(d, dict):
                continue
            name = os.path.basename(f)
            cls = vehicle_class(d, folder)
            per_class[cls] += 1
            has = False
            if 'countermeasure' in d and is_block(d['countermeasure']):
                threat += 1
                threat_ex.append(name)
            for m in items(d.get('damagePartsToAvionicsPartsMap')):
                for a in items(m.get('avionics')):
                    avionics[str(a.get('avionics'))] += 1
            for path, key, val in walk(d):
                if key.lower() == 'blk' and isinstance(val, str):
                    ref = norm_ref(val)
                    gp = generic_path(path)
                    if ref.startswith('gamedata/sensors/'):
                        has = True
                        where[(cls, gp)] += 1
                        where_ex.setdefault((cls, gp), f'{name}: {val}')
                        rel = ref[len('gamedata/'):]
                        if rel not in sensors:
                            missing[rel] += 1
                        kinds_by_class[cls][kind_of(sensors[rel]) if rel in sensors else '<нет файла>'] += 1
                    elif ref.startswith('gamedata/countermeasures/'):
                        cm_where[(cls, gp)] += 1
                        cm_ex.setdefault((cls, gp), f'{name}: {val}')
            # поля записи sensor и контрмер
            for path, blk in iter_blocks(d):
                low = [p.lower() for p in path]
                if len(low) >= 2 and low[-1] == 'sensor' and low[-2] == 'sensors':
                    n_entries += 1
                    entry_fields.update(blk.keys())
                if len(low) >= 2 and low[-1] == 'countermeasure' and low[-2] == 'countermeasures':
                    cm_entry.update(blk.keys())
                if low and low[-1] == 'weapon' and blk.get('trigger') == 'countermeasures':
                    b = norm_ref(str(blk.get('blk', ''))).rsplit('/', 1)[-1]
                    cm_launch[(cls, b)] += 1
                    cm_bullets[b].append(blk.get('bullets'))
                    cm_weapon_fields.update(blk.keys())
            if has:
                with_sensors[cls] += 1

    print('\n=== Как машина подключает сенсор')
    print('  машин по классам:', dict(per_class), '; с хотя бы одной ссылкой на sensors/:', dict(with_sensors))
    print('  путь блока со ссылкой blk на gamedata/sensors (класс | путь | вхождений | пример):')
    for (cls, gp), n in sorted(where.items(), key=lambda x: -x[1]):
        print(f'    {cls} | {gp} | {n} | {where_ex[(cls, gp)]}')
    line('поля записи sensors/sensor', entry_fields, n_entries)
    for cls, c in kinds_by_class.items():
        line(f'виды подключённых сенсоров — {cls}', c, sum(c.values()))
    print(f'  ссылок на отсутствующие файлы: {sum(missing.values())}', missing.most_common(EX))
    line('damagePartsToAvionicsPartsMap/avionics/avionics (повреждаемые узлы авионики)',
         avionics, sum(avionics.values()), 30)

    print('\n=== Помехи: файлы gamedata/countermeasures и ссылки на них')
    for (cls, gp), n in sorted(cm_where.items(), key=lambda x: -x[1]):
        print(f'    {cls} | {gp} | {n} | {cm_ex[(cls, gp)]}')
    line('поля записи counterMeasures/counterMeasure', cm_entry, sum(cm_where.values()))
    print(f'  верхний блок `countermeasure` (программа отстрела по угрозам): {threat} машин; '
          f'примеры {threat_ex[:EX]}')
    print('  Weapon с trigger="countermeasures" (класс | файл пусковой | вхождений | bullets):')
    for (cls, b), n in cm_launch.most_common(15):
        print(f'    {cls} | {b} | {n} | {numstat(cm_bullets[b])}')
    line('поля такого Weapon', cm_weapon_fields, sum(cm_launch.values()))


def iter_blocks(o, path=()):
    if isinstance(o, dict):
        for k, v in o.items():
            for x in items(v):
                yield path + (k,), x
                yield from iter_blocks(x, path + (k,))


def survey_countermeasures(gd):
    files = sorted(glob.glob(os.path.join(gd, 'countermeasures', '*.blkx')))
    print(f'\n=== gamedata/countermeasures: {len(files)} файлов (ИК/РЭ-подавители, не ловушки)')
    by = defaultdict(list)
    for f in files:
        d = load(f)
        by[str(d.get('type'))].append((os.path.basename(f), d))
    for t, lst in by.items():
        c = Counter()
        for _, d in lst:
            c.update(d.keys())
        print(f'  type={t}: {len(lst)} — ' + ', '.join(n for n, _ in lst[:6]))
        line('поля', c, len(lst), 30)

    files = sorted(glob.glob(os.path.join(gd, 'weapons', 'rocketguns', '*.blkx')))
    files = [f for f in files if any(s in os.path.basename(f) for s in ('countermeasure', 'chaff', 'flare'))]
    print(f'\n=== Пусковые ловушек/диполей (gamedata/weapons/rocketguns): {len(files)} файлов')
    top, bt, sig = Counter(), Counter(), Counter()
    rows = []
    for f in files:
        d = load(f)
        top.update(k for k, v in d.items() if not is_block(v))
        types = []
        for path, blk in iter_blocks(d):
            if path and path[-1] == 'bullet':
                types.append(str(blk.get('bulletType')))
                bt[str(blk.get('bulletType'))] += 1
                for rk in items(blk.get('rocket')):
                    for s in items(rk.get('signature')):
                        for p2, k2, _ in walk(s):
                            sig['/'.join(p2 + (k2,))] += 1
        rows.append((os.path.basename(f), d.get('bullets'), d.get('reloadTime'), d.get('shotFreq'), types))
    line('скалярные поля верхнего уровня', top, len(files), 30)
    line('bullet/bulletType', bt, sum(bt.values()))
    line('bullet/rocket/signature: поля (ИК/РЛ-сигнатура ловушки)', sig, sum(bt.values()), 30)
    for r in [r for r in rows if r[1] is not None][:8]:
        print('   пример: {} | bullets {} | reloadTime {} | shotFreq {} | типы {}'.format(*r))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    root = sys.argv[1]
    gd = os.path.join(root, 'aces.vromfs.bin_u', 'gamedata')
    if not os.path.isdir(gd):
        gd = root
    if not os.path.isdir(os.path.join(gd, 'sensors')):
        sys.exit(f'нет {gd}/sensors — укажите корень клона датамайна')
    try:
        rev = subprocess.run(['git', '-C', root, 'log', '-1', '--format=%h %cs'],
                             capture_output=True, text=True).stdout.strip()
    except OSError:
        rev = ''
    print(f'Датамайн: {root} (коммит {rev or "?"})')
    sensors, kinds = survey_sensors(gd)
    survey_vehicles(gd, sensors, kinds)
    survey_countermeasures(gd)


if __name__ == '__main__':
    main()
