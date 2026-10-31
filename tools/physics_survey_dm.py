"""Обзор физики техники по публичному датамайну War Thunder (gszabi99/War-Thunder-Datamine); только чтение.

Запуск: python tools/physics_survey_dm.py <путь к клону датамайна или к его папке gamedata>
Клон достаточно частичный (sparse): aces.vromfs.bin_u/gamedata/{flightmodels,units/tankmodels,units/ships}.

В датамайне файлы лежат как *.blkx в JSON (выгрузка wt_ext_cli): повторяющиеся параметры и блоки склеены в список,
типы BLK потеряны (вектор p3 и три одноимённых параметра выглядят одинаково). Текстовый BLK (*.blk) тоже читается —
через tools/wtlib/blk.py и приводится к тому же виду.
Частота означает число объектов данного уровня (файлов, блоков), где имя встретилось хотя бы раз.
"""
from collections import Counter, defaultdict
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

FM = 'flightmodels'
TANKS = 'units/tankmodels'
SHIPS = 'units/ships'


# ---------------------------------------------------------------- чтение

def block_to_dict(block):
    """wtlib.blk.Block -> dict как в JSON датамайна (повторы -> список)."""
    out = {}

    def put(k, v):
        if k in out:
            if not isinstance(out[k], list) or not getattr(out[k], 'dup', False):
                out[k] = _Dup([out[k]])
            out[k].append(v)
        else:
            out[k] = v
    for k, _t, v in block.params:
        put(k, list(v) if isinstance(v, tuple) else v)
    for b in block.blocks:
        put(b.name, block_to_dict(b))
    return out


class _Dup(list):
    dup = True


def load(path):
    with open(path, 'rb') as f:
        data = f.read()
    text = data.decode('utf-8-sig', errors='replace')
    if text.lstrip().startswith(('{', '[')):
        return json.loads(text)
    from wtlib.blk import parse_text  # нужен только для текстового BLK
    return block_to_dict(parse_text(text, lenient=True))


def find_gamedata(root):
    for cand in (root, os.path.join(root, 'gamedata'), os.path.join(root, 'aces.vromfs.bin_u', 'gamedata')):
        if os.path.isdir(os.path.join(cand, FM)) or os.path.isdir(os.path.join(cand, TANKS)):
            return cand
    sys.exit(f'Не найдена папка gamedata в {root}')


def read_dir(gamedata, sub):
    """{имя файла без расширения (нижний регистр): dict}; ошибки разбора считаются и выводятся."""
    folder = os.path.join(gamedata, sub)
    out, bad = {}, []
    if not os.path.isdir(folder):
        return out
    for fn in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in ('.blk', '.blkx') or not os.path.isfile(os.path.join(folder, fn)):
            continue
        try:
            d = load(os.path.join(folder, fn))
        except (ValueError, UnicodeError) as e:
            bad.append((fn, str(e)[:60]))
            continue
        if isinstance(d, dict):
            out[stem.lower()] = d
    if bad:
        print(f'  {sub}: не разобрано {len(bad)}: {bad[:3]}')
    return out


# ---------------------------------------------------------------- вывод

def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) and all(isinstance(x, dict) for x in v) else [v]


def dicts(v):
    return [x for x in as_list(v) if isinstance(x, dict)]


def get(d, path):
    for p in path.split('/'):
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def keys_freq(objs, skip=None):
    c = Counter()
    for o in objs:
        c.update(k for k in o if not (skip and skip.match(k)))
    return c


def show(title, counter, total, limit=40):
    print(f'{title} (объектов {total}):')
    if counter:
        print('  ' + ', '.join(f'{k} {n}' for k, n in counter.most_common(limit)))
        if len(counter) > limit:
            print(f'  … ещё имён: {len(counter) - limit}')


def short(v, n=60):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n - 1] + '…'


def examples(title, rows, limit=5):
    print(title)
    for row in rows[:limit]:
        print('  ' + ' | '.join(short(x) for x in row))


def numbered(prefix, d):
    """Блоки prefix0, prefix1… (EngineN, PropellerN) в порядке номеров."""
    rx = re.compile(re.escape(prefix) + r'(\d+)$')
    found = [(int(m.group(1)), k) for k in d if (m := rx.match(k))]
    return [(n, k) for n, k in sorted(found)]


def header(s):
    print()
    print('=' * 8, s, '=' * 8)


# ---------------------------------------------------------------- авиация

def survey_air(gd):
    header('АВИАЦИЯ: flightmodels/*.blk и flightmodels/fm/*.blk')
    units = read_dir(gd, FM)
    fms = read_dir(gd, FM + '/fm')
    print(f'файлов машин {len(units)}, файлов ЛМ (fm/) {len(fms)}')

    # связь машины с ЛМ
    links, missing, implicit, heli_fm = Counter(), [], [], set()
    users = defaultdict(list)
    for name, d in units.items():
        fm_file = d.get('fmFile')
        if isinstance(fm_file, str):
            target = os.path.splitext(os.path.basename(fm_file.replace('\\', '/')))[0].lower()
            links['fmFile есть'] += 1
            links['fmFile = своё имя' if target == name else 'fmFile = чужое имя'] += 1
        else:
            target = name
            links['fmFile нет'] += 1
            implicit.append(name)
        if target in fms:
            users[target].append(name)
        else:
            missing.append((name, fm_file))
        if d.get('fightAiBehaviour') == 'helicopter':
            heli_fm.add(target)
    links['fmFile нет, но есть fm/<своё имя>'] = sum(n in fms for n in implicit)
    print('связь с ЛМ:', dict(links))
    print(f'ЛМ не найдена в датамайне: {len(missing)} {missing[:5]}')
    shared = sorted(((t, u) for t, u in users.items() if len(u) > 1), key=lambda x: -len(x[1]))
    print(f'файлов ЛМ, общих для 2+ машин: {len(shared)}; больше всех: '
          + '; '.join(f'{t} ← {len(u)} ({", ".join(u[:3])}…)' for t, u in shared[:4]))
    orphans = sorted(set(fms) - set(users))
    print(f'файлов ЛМ, на которые не ссылается ни одна машина: {len(orphans)} {orphans[:8]}')
    print(f'вертолётов (fightAiBehaviour=helicopter): {len(heli_fm)} файлов ЛМ')
    rows = [(n, d.get('fmFile')) for n, d in units.items() if d.get('fmFile')
            and os.path.splitext(os.path.basename(d['fmFile']))[0].lower() != n]
    examples('примеры fmFile на чужое имя:', rows)

    # масса и инерция
    masses = [d['Mass'] for d in fms.values() if isinstance(d.get('Mass'), dict)]
    show('\nfm: блоки верхнего уровня', keys_freq(fms.values(), re.compile(r'.*\d$')), len(fms), 60)
    show('fm: Mass{}', keys_freq(masses), len(masses), 60)
    show('fm: Mass/Parts{} (имена частей)', keys_freq(x for m in masses for x in dicts(m.get('Parts'))),
         len(masses), 15)
    show('fm: Mass/PartsWithSurface{}', keys_freq(x for m in masses for x in dicts(m.get('PartsWithSurface'))),
         len(masses), 20)
    examples('примеры (ЛМ | EmptyMass | MaxFuelMass0 | Takeoff | OilMass | MomentOfInertia | CenterOfGravity):',
             [(n, get(d, 'Mass/EmptyMass'), get(d, 'Mass/MaxFuelMass0'), get(d, 'Mass/Takeoff'),
               get(d, 'Mass/OilMass'), d.get('MomentOfInertia'), get(d, 'Mass/CenterOfGravity'))
              for n, d in fms.items() if n in ('mig-15_ns23', 'spitfire_mk9c_4cannons', 'f_117', 'ah_1g', 'ki_84_otsu',
                                               'b_66b', 'p-61c_1')], 7)
    moi = Counter('MomentOfInertia' in d for d in fms.values())
    print(f'MomentOfInertia на верхнем уровне fm: {moi[True]} из {len(fms)}')

    # двигатели
    scheme, per_fm, by_type, sub_by_type, ex_by_type = Counter(), defaultdict(set), defaultdict(Counter), \
        defaultdict(Counter), defaultdict(list)
    thrust_keys, engine_keys, et_keys, comp_by_type = Counter(), Counter(), Counter(), defaultdict(Counter)
    thrust_n = 0
    for name, d in fms.items():
        for _n, ek in numbered('Engine', d):
            for eng in dicts(d[ek]):
                engine_keys.update(eng.keys())
                if isinstance(eng.get('Type'), int):
                    tk = f'EngineType{eng["Type"]}'
                    src = d.get(tk)
                    scheme['EngineN{Type:i} → EngineTypeN{Main}'] += 1
                    if not isinstance(src, dict):
                        scheme['ссылка на EngineTypeN не найдена'] += 1
                        continue
                else:
                    src = eng
                    scheme['EngineN{Main} внутри'] += 1
                main = src.get('Main')
                if not isinstance(main, dict):
                    scheme['нет Main'] += 1
                    continue
                t = str(main.get('Type'))
                if name in heli_fm:
                    t += ' (вертолёт)'
                by_type[t].update(main.keys())
                sub_by_type[t].update(k for k, v in src.items() if isinstance(v, dict))
                per_fm[t].add(name)
                ex_by_type[t].append((name, ek, main.get('Power'), main.get('Thrust'), main.get('Mass'),
                                      main.get('RPMMax'), get(main, 'ThrustMax/ThrustMax0')))
                for comp in dicts(src.get('Compressor')):
                    comp_by_type[t].update(re.sub(r'\d+$', 'N', k) for k in comp)
                if isinstance(main.get('ThrustMax'), dict):
                    thrust_n += 1
                    thrust_keys.update(re.sub(r'\d+', 'N', k) for k in main['ThrustMax'])
        for _n, tk in numbered('EngineType', d):
            et_keys.update(k for x in dicts(d[tk]) for k in x)
    print('\nсхема двигателей (блоков EngineN):', dict(scheme))
    show('EngineN{} (поля и блоки)', engine_keys, sum(len(numbered('Engine', d)) for d in fms.values()), 30)
    show('EngineTypeN{}', et_keys, sum(len(numbered('EngineType', d)) for d in fms.values()), 30)
    print('виды двигателей по Main/Type (блоков | файлов ЛМ):',
          ', '.join(f'{t} {sum(c.get("Type", 0) for c in [by_type[t]])}|{len(per_fm[t])}' for t in
                    sorted(by_type, key=lambda t: -len(per_fm[t]))))
    for t in sorted(by_type, key=lambda t: -len(per_fm[t])):
        print()
        show(f'Main{{}} — {t}', by_type[t], by_type[t].get('Type', 0), 45)
        show(f'  блоки рядом с Main — {t}', sub_by_type[t], by_type[t].get('Type', 0), 15)
        show(f'  Compressor{{}} — {t} (номера в конце → N)', comp_by_type[t], by_type[t].get('Type', 0), 25)
        examples(f'  примеры (ЛМ | блок | Power | Thrust | Mass | RPMMax | ThrustMax/ThrustMax0):', ex_by_type[t], 4)
    show('\nMain/ThrustMax{} (номера → N)', thrust_keys, thrust_n, 20)

    props = [x for d in fms.values() for _n, k in numbered('Propeller', d) for x in dicts(d[k])]
    show('\nPropellerN{}', keys_freq(props), len(props), 20)
    show('PropellerN/Geometry{}', keys_freq(x for p in props for x in dicts(p.get('Geometry'))), len(props), 30)
    ptypes = [x for d in fms.values() for _n, k in numbered('PropellerType', d) for x in dicts(d[k])]
    show('PropellerTypeN{} (на него ссылается PropellerN{Type:i})', keys_freq(ptypes), len(ptypes), 20)
    show('PropellerTypeN/Geometry{}', keys_freq(x for p in ptypes for x in dicts(p.get('Geometry'))), len(ptypes), 20)
    inline = [x for d in fms.values() for _n, k in numbered('Engine', d) for e in dicts(d[k])
              for x in dicts(e.get('Propellor'))]
    show('EngineN/Propellor{} (винт внутри двигателя, старая схема)', keys_freq(inline), len(inline), 20)
    trans = [x for d in fms.values() for _n, k in numbered('Transmission', d) for x in dicts(d[k])]
    show('TransmissionN{}', keys_freq(trans, re.compile(r'.*\d$')), len(trans), 20)
    heli = [fms[n] for n in heli_fm if n in fms]
    show('ЛМ вертолётов: блоки верхнего уровня', keys_freq(heli), len(heli), 80)


# ---------------------------------------------------------------- наземка

WHEEL = re.compile(r'wheel_|.*_wheel')


def survey_ground(gd):
    header('НАЗЕМКА: units/tankmodels/*.blk')
    tanks = read_dir(gd, TANKS)
    vp = {n: d['VehiclePhys'] for n, d in tanks.items() if isinstance(d.get('VehiclePhys'), dict)}
    print(f'файлов {len(tanks)}, с VehiclePhys {len(vp)}; без: {[n for n in tanks if n not in vp][:5]}')
    top = Counter(k for d in tanks.values() for k in d if k in (
        'maxFwdSpeed', 'maxRevSpeed', 'maxAngSpeed', 'maxAccel', 'maxDecel', 'maxAngAccel', 'maxAngAccel0',
        'maxAngAccel1', 'groundNormSmoothViscosity', 'minDistBetween', 'moveType', 'expClass'))
    show('верхний уровень файла: скоростные поля', top, len(tanks))
    print('значения maxFwdSpeed:', Counter(short(d.get('maxFwdSpeed')) for d in tanks.values()).most_common(6))
    show('VehiclePhys{}', keys_freq(vp.values()), len(vp), 30)
    for b in ('Mass', 'engine', 'mechanics', 'tracks', 'movableSuspension'):
        objs = [x for v in vp.values() for x in dicts(v.get(b))]
        show(f'VehiclePhys/{b}{{}}', keys_freq(objs), len(objs), 40)
    susp = [x for v in vp.values() for x in dicts(v.get('suspension'))]
    show('VehiclePhys/suspension{} (без имён колёс wheel_*)', keys_freq(susp, WHEEL), len(susp), 40)
    wheel_named = sum(any(WHEEL.match(k) for k in s) for s in susp)
    print(f'  suspension с параметрами по именам колёс (wheel_*): {wheel_named}')
    print('engine/type:', dict(Counter(str(get(v, 'engine/type')) for v in vp.values())))
    print('mechanics/steerType:', dict(Counter(str(get(v, 'mechanics/steerType')) for v in vp.values())))
    print('mechanics/type:', dict(Counter(str(get(v, 'mechanics/type')) for v in vp.values())))
    print('mechanics/tracked:', dict(Counter(str(get(v, 'mechanics/tracked')) for v in vp.values())))
    ratios = Counter()
    for v in vp.values():
        r = get(v, 'mechanics/gearRatios/ratio')
        ratios[len(r) if isinstance(r, list) else ('1 (одно значение)' if r is not None else 'нет')] += 1
    print('число ratio в gearRatios (передачи вкл. нейтраль и задние):',
          dict(sorted(ratios.items(), key=lambda x: str(x[0]))))
    pick = ('ussr_t_80u', 'germ_pzkpfw_vi_ausf_e_tiger', 'us_m1_abrams', 'sw_strv_103c', 'jp_type_74_f', 'it_centauro_2',
            'ussr_bmp_3', 'us_m1128_mgs')
    examples('примеры (машина | maxFwdSpeed | maxRevSpeed | Mass/Empty | Mass/TakeOff | horsePowers | maxRPM | '
             'maxBrakeForce | gearRatios/ratio):',
             [(n, tanks[n].get('maxFwdSpeed'), tanks[n].get('maxRevSpeed'), get(vp[n], 'Mass/Empty'),
               get(vp[n], 'Mass/TakeOff'), get(vp[n], 'engine/horsePowers'), get(vp[n], 'engine/maxRPM'),
               get(vp[n], 'mechanics/maxBrakeForce'), get(vp[n], 'mechanics/gearRatios/ratio'))
              for n in pick if n in vp], 8)
    ms = [(n, list(v['movableSuspension'])) for n, v in vp.items() if isinstance(v.get('movableSuspension'), dict)]
    print(f'movableSuspension (управляемая/гидропневматическая подвеска): {len(ms)} машин')
    examples('  примеры (машина | блоки и поля):', [m for m in ms if not m[0].startswith(('railway', 'us_railway',
                                                                                          'ussr_freight'))], 8)


# ---------------------------------------------------------------- флот

def survey_ships(gd):
    header('ФЛОТ: units/ships/*.blk')
    ships = read_dir(gd, SHIPS)
    sp = {n: d['ShipPhys'] for n, d in ships.items() if isinstance(d.get('ShipPhys'), dict)}
    other_phys = Counter(k for d in ships.values() for k in d if k.endswith('Phys') and k != 'ShipPhys')
    print(f'файлов {len(ships)}, с ShipPhys {len(sp)}; другие *Phys: {dict(other_phys)}')
    no = [n for n in ships if n not in sp]
    top = Counter(k for n in no for k in ships[n] if k.startswith('max') or k == 'moveType')
    show('без ShipPhys: поля max*/moveType верхнего уровня', top, len(no), 20)
    examples('  примеры без ShipPhys (файл | moveType | maxFwdSpeed | maxRevSpeed | maxAngSpeed):',
             [(n, ships[n].get('moveType'), ships[n].get('maxFwdSpeed'), ships[n].get('maxRevSpeed'),
               ships[n].get('maxAngSpeed')) for n in no], 5)
    top2 = Counter(k for n in sp for k in ships[n] if k.startswith('max') or k == 'moveType')
    show('с ShipPhys: поля max*/moveType верхнего уровня', top2, len(sp), 20)
    print('значения maxFwdSpeed (с ShipPhys):', Counter(short(ships[n].get('maxFwdSpeed')) for n in sp).most_common(6))
    show('ShipPhys{}', keys_freq(sp.values()), len(sp), 30)
    for b in ('mass', 'engines', 'hydrodynamics'):
        objs = [x for v in sp.values() for x in dicts(v.get(b))]
        show(f'ShipPhys/{b}{{}}', keys_freq(objs), len(objs), 30)
    engs = [e for v in sp.values() for e in dicts(get(v, 'engines/engine'))]
    show('ShipPhys/engines/engine{} (каждый вал/двигатель)', keys_freq(engs), len(engs), 20)
    rud = [r for v in sp.values() for r in dicts(get(v, 'hydrodynamics/rudder'))]
    show('ShipPhys/hydrodynamics/rudder{}', keys_freq(rud), len(rud), 20)
    cnt = Counter(len(dicts(get(v, 'engines/engine'))) for v in sp.values())
    print('engine{} на корабль:', dict(sorted(cnt.items())))
    pick = ('us_aircraftcarrier_enterprise', 'us_destroyer_fletcher', 'ussr_destroyer_7y_stroyny', 'uk_fairmile_a_ml100',
            'germ_s38_s100', 'it_p420_sparviero', 'us_elco_80ft_pt_boat_thunderbolt', 'uss_dd_sims_test')
    examples('примеры (корабль | mass/Empty | maxSpeed | maxReverseSpeed | speedToTime/row | engine{} | rudder{}):',
             [(n, get(sp[n], 'mass/Empty'), get(sp[n], 'engines/maxSpeed'), get(sp[n], 'engines/maxReverseSpeed'),
               get(sp[n], 'engines/speedToTime/row'), len(dicts(get(sp[n], 'engines/engine'))),
               len(dicts(get(sp[n], 'hydrodynamics/rudder')))) for n in pick if n in sp], 8)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    gd = find_gamedata(sys.argv[1])
    print('gamedata:', gd)
    survey_air(gd)
    survey_ground(gd)
    survey_ships(gd)


if __name__ == '__main__':
    main()
