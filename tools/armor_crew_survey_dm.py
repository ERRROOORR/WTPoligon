"""Обзор брони, живучести и экипажа War Thunder по публичному датамайну; только чтение.

Источник — локальный клон https://github.com/gszabi99/War-Thunder-Datamine (файлы `*.blkx` — BLK,
выгруженный в JSON). Достаточно частичного клона:
  git clone --filter=blob:none --sparse --no-checkout <url> wtdm && git -C wtdm checkout aa326f1
  git -C wtdm sparse-checkout set --no-cone /aces.vromfs.bin_u/gamedata/damage_model/ \
      '/aces.vromfs.bin_u/gamedata/flightmodels/*.blkx' '/aces.vromfs.bin_u/gamedata/units/tankmodels/*.blkx' \
      '/aces.vromfs.bin_u/gamedata/units/ships/*.blkx' /aces.vromfs.bin_u/config/fireparams.blkx \
      /aces.vromfs.bin_u/config/damagemodel.blkx /aces.vromfs.bin_u/config/damagemodelparts.blkx \
      /char.vromfs.bin_u/config/crew_skills.blkx /mis.vromfs.bin_u/gamedata/missions/
Запуск: PYTHONIOENCODING=utf-8 python tools/armor_crew_survey_dm.py <путь к клону>

Частота — число объектов указанного уровня (машин, групп, частей), где имя встретилось хотя бы раз.
Часть повреждений — ключ `*_dm` внутри группы `DamageParts/<группа>`; остальные ключи группы — её
значения по умолчанию для всех частей группы.
"""
from collections import Counter, defaultdict
import glob
import json
import os
import subprocess
import sys

TOP = 25      # сколько полей печатать в строке частот
EX = 4        # сколько примеров
TEST_UNITS = [('tank', 'ussr_t_80bvm'), ('tank', 'us_m1a1_abrams'), ('tank', 'germ_pzkpfw_vi_ausf_h1_tiger'),
              ('air', 'a-26b')]
ERA_KEYS = ('kineticProtectionEquivalent', 'cumulativeProtectionEquivalent')


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


def is_block(v):
    return bool(items(v))


def short(v, n=70):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n - 1] + '…'


def line(title, counter, total, limit=TOP):
    print(f'  {title} (из {total}): ' + ', '.join(f'{k} {n}' for k, n in counter.most_common(limit)))


def nums(vals):
    out = []
    for v in vals:
        if isinstance(v, list):
            out += nums(v)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append(v)
    return out


def numstat(vals):
    vals = sorted(nums(vals))
    if not vals:
        return '—'
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


def generic_path(path):
    """Обобщение имён: modifications/<мод>, DamageParts/<группа>/<часть>, ammoStowages/<укладка>."""
    out = []
    for i, p in enumerate(path):
        prev = path[i - 1] if i else ''
        if prev in ('modifications',):
            out.append('<мод>')
        elif prev in ('DamageParts', 'damagePartsOverride') and not p.endswith('_dm'):
            out.append('<группа>')
        elif p.endswith('_dm'):
            out.append('<часть>')
        elif prev == 'ammoStowages':
            out.append('<укладка>')
        elif prev == 'tank_crew':
            out.append('<член>')
        else:
            out.append(p)
    return '/'.join(out) or '<корень>'


# ---------------------------------------------------------------- загрузка машин

def load_units(gd):
    units = {}
    for cls, pat in (('tank', 'units/tankmodels/*.blkx'), ('ship', 'units/ships/*.blkx'),
                     ('air', 'flightmodels/*.blkx')):
        for f in sorted(glob.glob(os.path.join(gd, pat))):
            name = os.path.basename(f)[:-5]
            try:
                d = load(f)
            except Exception as e:      # noqa: BLE001
                print('ОШИБКА разбора', f, e)
                continue
            if not isinstance(d, dict):
                continue
            c = cls
            if cls == 'air':
                c = 'heli' if 'helicopter' in d else 'air'
            units[(c, name)] = d
    return units


CLS_RU = {'tank': 'наземная', 'air': 'самолёт', 'heli': 'вертолёт', 'ship': 'корабль'}


def by_class(units):
    out = defaultdict(list)
    for (c, n), d in units.items():
        out[c].append((n, d))
    return out


# ---------------------------------------------------------------- DamageParts

def dm_parts(d):
    """(группа, поля группы, {часть: поля}) для всех групп DamageParts."""
    for dp in items(d.get('DamageParts')):
        for g, gv in dp.items():
            for gx in items(gv):
                defaults = {k: v for k, v in gx.items() if not k.endswith('_dm')}
                parts = {k: (items(v)[0] if is_block(v) else {}) for k, v in gx.items() if k.endswith('_dm')}
                yield g, defaults, parts


def survey_damage_parts(units):
    print('\n=== DamageParts: броня и прочность частей')
    for c, lst in by_class(units).items():
        root_f, grp_f, part_f, cls_use, grp_names = Counter(), Counter(), Counter(), Counter(), Counter()
        thick, hp, var_thick, n_grp, n_part, with_dp = [], [], 0, 0, 0, 0
        fmt = Counter()
        era_units, era_ex, ex_thick = set(), [], []
        for n, d in lst:
            dps = items(d.get('DamageParts'))
            if not dps:
                continue
            with_dp += 1
            for dp in dps:
                root_f.update(k for k, v in dp.items() if not is_block(v))
                fmt[str(dp.get('formatVersion'))] += 1
            for g, defaults, parts in dm_parts(d):
                n_grp += 1
                grp_names[g] += 1
                grp_f.update(defaults.keys())
                if 'armorClass' in defaults:
                    cls_use[str(defaults['armorClass'])] += 1
                for p, pv in parts.items():
                    n_part += 1
                    part_f.update(pv.keys())
                    if 'armorClass' in pv:
                        cls_use[str(pv['armorClass'])] += 1
                    t = pv.get('armorThickness', defaults.get('armorThickness'))
                    thick.append(t)
                    hp.append(pv.get('hp', defaults.get('hp')))
                    if pv.get('variableThickness', defaults.get('variableThickness')):
                        var_thick += 1
                    if len(ex_thick) < EX and 'armorThickness' in pv:
                        ex_thick.append(f'{n}: DamageParts/{g}/{p}/armorThickness={pv["armorThickness"]:g}')
                era = any(k in defaults for k in ERA_KEYS) or any(k in pv for pv in parts.values()
                                                                   for k in ERA_KEYS)
                if era:
                    era_units.add(n)
                    if len(era_ex) < EX:
                        era_ex.append(f'{n}: {g} {short({k: defaults[k] for k in defaults if k in ERA_KEYS + ("armorClass",)})}')
        print(f'\n--- {CLS_RU[c]}: машин {len(lst)}, с DamageParts {with_dp}; групп {n_grp}, частей *_dm {n_part}')
        line('formatVersion', fmt, with_dp, 5)
        line('скаляры корня DamageParts', root_f, with_dp)
        line('поля группы (умолчания)', grp_f, n_grp)
        line('поля части', part_f, n_part)
        line('имена групп', grp_names, n_grp, 30)
        line('armorClass (группа+часть)', cls_use, sum(cls_use.values()), 30)
        print(f'  armorThickness части (с умолчанием группы): {numstat(thick)}; variableThickness: {var_thick}')
        print(f'  hp части: {numstat(hp)}')
        for e in ex_thick:
            print('   пример:', e)
        print(f'  ЭРА/навесная (поля {"/".join(ERA_KEYS)}): машин {len(era_units)}')
        for e in era_ex:
            print('   пример:', e)


def survey_armor_classes(gd, units):
    path = os.path.join(gd, 'damage_model', 'armor_classes.blkx')
    ac = load(path)
    print(f'\n=== damage_model/armor_classes.blkx: классов брони {len(ac)}')
    f = Counter()
    for v in ac.values():
        for x in items(v):
            f.update(x.keys())
    line('поля класса', f, len(ac), 40)
    used = Counter()
    for (c, n), d in units.items():
        for g, defaults, parts in dm_parts(d):
            for _, k, v in walk({'x': {'g': defaults, **parts}}):
                if k == 'armorClass':
                    used[str(v)] += 1
            if c in ('air', 'heli') and 'armorClass' not in defaults:
                used[g] += 1     # у авиации класс брони — имя группы
    known = {k for k in used if k in ac}
    unknown = Counter({k: n for k, n in used.items() if k not in ac and n})
    print(f'  имён, использованных машинами: {len([k for k in used if used[k]])}, из них есть в armor_classes: '
          f'{len([k for k in known if used[k]])}')
    line('нет в armor_classes (обычно авиа-группы без класса)', unknown, sum(unknown.values()), 15)
    for k in ('RHA_tank', 'RHA_tank_modern', 'CHA_tank', 'ERA_Relict', 'armor12_7', 'steel_tankman'):
        if k in ac:
            print(f'   {k}: {short(ac[k], 200)}')
    for fn in sorted(glob.glob(os.path.join(gd, 'damage_model', '*.blkx'))):
        d = load(fn)
        print(f'  {os.path.basename(fn)}: верхних ключей {len(d) if isinstance(d, dict) else "?"}: '
              + ', '.join(list(d)[:8] if isinstance(d, dict) else []))
    print(f'  projectile_types/: {len(glob.glob(os.path.join(gd, "damage_model", "projectile_types", "*.blkx")))} файлов')


# ---------------------------------------------------------------- экипаж

def survey_crew(units, root):
    print('\n=== Экипаж')
    for c, lst in by_class(units).items():
        top_f, mem_f, roles, sizes, subs = Counter(), Counter(), Counter(), Counter(), 0
        with_crew, ex, ship_crew = 0, [], []
        for n, d in lst:
            for tc in items(d.get('tank_crew')):
                with_crew += 1
                top_f.update(k for k, v in tc.items() if not is_block(v))
                mem = [(k, x) for k, v in tc.items() for x in items(v)]
                sizes[len(mem)] += 1
                total = 0
                for k, x in mem:
                    mem_f.update(x.keys())
                    r = x.get('role')
                    for rr in (r if isinstance(r, list) else [r]):
                        roles[str(rr)] += 1
                    subs += 'substitute' in x
                    total += x.get('crew', 1) if isinstance(x.get('crew', 1), (int, float)) else 1
                if c == 'ship':
                    ship_crew.append(total)
                if len(ex) < EX:
                    ex.append(f'{n}: ' + ', '.join(f'{k}({x.get("role")})' for k, x in mem[:6]))
        if not with_crew:
            continue
        print(f'\n--- {CLS_RU[c]}: tank_crew у {with_crew}/{len(lst)}')
        line('скаляры tank_crew', top_f, with_crew)
        line('поля члена экипажа', mem_f, sum(sizes[k] * k for k in sizes))
        line('роли', roles, sum(roles.values()), 30)
        line('членов (блоков) в tank_crew', Counter({str(k): v for k, v in sizes.items()}), with_crew, 15)
        if ship_crew:
            print(f'  корабли: сумма tank_crew/*/crew {numstat(ship_crew)}')
        print(f'  записей с substitute: {subs}')
        for e in ex:
            print('   пример:', e)
    # авиация: экипаж — части pilot*/gunner* в DamageParts
    for c in ('air', 'heli'):
        lst = by_class(units).get(c, [])
        cnt, gcnt, fph, grp = Counter(), Counter(), 0, Counter()
        for n, d in lst:
            k = 0
            for g, defaults, parts in dm_parts(d):
                for p, pv in parts.items():
                    if p.startswith(('pilot', 'gunner')):
                        k += 1
                        grp[g] += 1
                        fph += 'fireProtectionHp' in pv
            cnt[str(k)] += 1
            for a in items(d.get('Aircraft')):
                if 'gunnersCount' in a:
                    gcnt[str(a['gunnersCount'])] += 1
        print(f'\n--- {CLS_RU[c]}: частей pilot*/gunner* в DamageParts на машину')
        line('число', cnt, len(lst), 12)
        line('группа (класс брони) этих частей', grp, sum(grp.values()), 8)
        line('Aircraft/gunnersCount', gcnt, len(lst), 10)
        print(f'  из них с fireProtectionHp: {fph}')
    cs = os.path.join(root, 'char.vromfs.bin_u', 'config', 'crew_skills.blkx')
    if os.path.exists(cs):
        d = load(cs)
        sk = d.get('crew_skills', {})
        print(f'\n  char.vromfs crew_skills.blkx: специальностей {len(sk)}: '
              + ', '.join(f'{k}({len([x for x in v if is_block(v[x])])})' for k, v in sk.items()))


def survey_missions(root):
    md = os.path.join(root, 'mis.vromfs.bin_u', 'gamedata', 'missions')
    files = glob.glob(os.path.join(md, '**', '*.blkx'), recursive=True)
    if not files:
        print('\n=== Миссии: нет mis.vromfs.bin_u/gamedata/missions — пропуск')
        return
    vals, blocks, keys, ex = Counter(), Counter(), Counter(), []
    n_units = 0
    for f in files:
        try:
            d = load(f)
        except Exception:       # noqa: BLE001
            continue
        for u in items(d.get('units')):
            for b, v in u.items():
                for x in items(v):
                    if 'unit_class' not in x:
                        continue
                    n_units += 1
                    keys.update(k for k in x if 'crew' in k.lower() or 'skill' in k.lower())
                    if 'crewSkillK' in x:
                        vals[str(x['crewSkillK'])] += 1
                        blocks[b] += 1
                        if x['crewSkillK'] != 0 and len(ex) < EX:
                            ex.append(f'{os.path.relpath(f, md)}: {b} {x.get("unit_class")} crewSkillK={x["crewSkillK"]}')
    print(f'\n=== Миссии: файлов {len(files)}, юнитов с unit_class {n_units}')
    line('ключи юнита с crew/skill', keys, n_units)
    line('crewSkillK — значения', vals, sum(vals.values()))
    line('crewSkillK — в блоках', blocks, sum(blocks.values()), 12)
    for e in ex:
        print('   пример:', e)


# ---------------------------------------------------------------- пожары, укладка, эффекты

def survey_fire(gd, units):
    print('\n=== Пожары и огнестойкость')
    fp = os.path.join(os.path.dirname(gd), 'config', 'fireparams.blkx')
    presets = {}
    if os.path.exists(fp):
        presets = load(fp).get('presets', {})
        f = Counter()
        for v in presets.values():
            for x in items(v):
                f.update(x.keys())
        print(f'  config/fireparams.blkx: пресетов {len(presets)}')
        line('поля пресета', f, len(presets), 30)
    for c, lst in by_class(units).items():
        where, used, fph, top = Counter(), Counter(), [], Counter()
        for n, d in lst:
            seen = set()
            for path, k, v in walk(d):
                if k == 'fireParamsPreset':
                    seen.add(generic_path(path))
                    for x in (v if isinstance(v, list) else [v]):    # повтор параметра — список
                        used[str(x)] += 1
                elif k == 'fireProtectionHp':
                    fph.append(v)
            where.update(seen)
            for fpb in items(d.get('fireParams')):
                top.update(fpb.keys())
        print(f'\n--- {CLS_RU[c]} ({len(lst)})')
        line('где fireParamsPreset (машин)', where, len(lst), 10)
        line('какие пресеты', used, sum(used.values()), 12)
        miss = [k for k in used if presets and k not in presets]
        if miss:
            print('  нет в fireparams:', ', '.join(miss[:8]))
        print(f'  fireProtectionHp: {numstat(fph)}')
        if top:
            line('верхний fireParams', top, len(lst), 10)


def survey_stowage(units):
    print('\n=== Боеукладка ammoStowages и подрыв БК (ammo)')
    for c, lst in by_class(units).items():
        n_u, n_st, st_f, sh_f, cnt, flags, ammo_f = 0, 0, Counter(), Counter(), [], Counter(), Counter()
        n_ammo, ex = 0, []
        for n, d in lst:
            for a in items(d.get('ammo')):
                n_ammo += 1
                ammo_f.update(a.keys())
            sts = items(d.get('ammoStowages'))
            if not sts:
                continue
            n_u += 1
            total = 0
            for s in sts:
                for sn, sv in s.items():
                    for x in items(sv):
                        n_st += 1
                        st_f.update(k for k, v in x.items() if not is_block(v) or k in ('shells', 'charges'))
                        for k in ('fatalFire', 'fatalExplosion', 'removeLoadedAmmo'):
                            if k in x:
                                flags[f'{k}={x[k]}'] += 1
                        for kind in ('shells', 'charges'):
                            for sh in items(x.get(kind)):
                                sh_f.update(k for k in sh if not k.endswith('_dm'))
                                for k in ('fatalFire', 'fatalExplosion'):
                                    if k in sh:
                                        flags[f'{kind}/{k}={sh[k]}'] += 1
                                for p, pv in sh.items():
                                    if p.endswith('_dm'):
                                        for y in items(pv):
                                            total += y.get('count', 0) if isinstance(y.get('count'), (int, float)) else 0
            cnt.append(total)
            if len(ex) < EX:
                ex.append(f'{n}: укладок {len([1 for s in sts for _ in s])}, снарядов по count {total}')
        print(f'\n--- {CLS_RU[c]}: ammoStowages у {n_u}/{len(lst)}, укладок {n_st}; верхний ammo у {n_ammo}')
        if n_u:
            line('поля укладки', st_f, n_st)
            line('поля блока shells/charges', sh_f, sum(sh_f.values()) and n_st)
            line('флаги', flags, n_st, 12)
            print(f'  сумма count по частям: {numstat(cnt)}')
            for e in ex:
                print('   пример:', e)
        if n_ammo:
            line('поля ammo', ammo_f, n_ammo)


def survey_effects(units):
    print('\n=== DamageEffects (что происходит при попадании/уничтожении части)')
    for c, lst in by_class(units).items():
        shape, act, ev, keys, n = Counter(), Counter(), Counter(), Counter(), 0
        for _, d in lst:
            for de in items(d.get('DamageEffects')):
                n += 1
                shape['part[] (name, onHit/onKill)' if 'part' in de else 'по имени части/группы'] += 1
                for path, k, v in walk(de):
                    keys[k] += 1
                    if k == 'type' and path and path[-1] == 'action':
                        act[str(v)] += 1
                    if k == 'fxEventName':
                        ev[str(v)] += 1
        if not n:
            continue
        print(f'\n--- {CLS_RU[c]}: DamageEffects у {n}/{len(lst)}')
        line('форма', shape, n, 3)
        line('скалярные поля (вхождений)', keys, sum(keys.values()), 30)
        line('action/type', act, sum(act.values()), 12)
        line('fxEventName', ev, sum(ev.values()), 12)


def survey_mods_refs(units):
    print('\n=== Модификации и внешние файлы, касающиеся брони/живучести')
    for c, lst in by_class(units).items():
        eff, ex, refs = Counter(), defaultdict(list), Counter()
        for n, d in lst:
            seen = set()
            for path, k, v in walk(d.get('modifications', {}), ('modifications',)):
                gp = generic_path(path + (k,))
                if any(s in gp for s in ('DamageParts', 'damagePartsOverride', 'ammoStowages', 'tank_crew',
                                        'hideNodes', 'changeMass', 'armor', 'Armor', 'fire', 'Fire', 'crew')):
                    key = '/'.join(gp.split('/')[:5])
                    seen.add(key)
                    if len(ex[key]) < 2:
                        ex[key].append(f'{n}:{path[1] if len(path) > 1 else ""}')
            eff.update(seen)
            for k, v in d.items():
                if isinstance(v, str) and k.lower().endswith('blk') and ('damage' in k.lower() or 'dm' in k.lower()
                                                                         or 'meta' in k.lower()):
                    refs[k] += 1
        print(f'\n--- {CLS_RU[c]}')
        for k, m in eff.most_common(12):
            print(f'  {k}: машин {m}; пример {", ".join(ex[k])}')
        if refs:
            line('ссылки *Blk на общие файлы DM', refs, len(lst), 15)
        xr = sum(1 for _, d in lst if 'xray_viewer_data' in d)
        hd = Counter(str(d.get('hasDmg2')) for _, d in lst)
        print(f'  xray_viewer_data у {xr}; hasDmg2: {dict(hd)}')


def survey_test_units(units):
    print('\n=== Машины тестовых миссий проекта')
    for c, n in TEST_UNITS:
        d = units.get((c, n))
        if d is None:
            print(' нет', n)
            continue
        print(f'\n--- {n} ({CLS_RU[c]}), model={d.get("model")}')
        for g, defaults, parts in dm_parts(d):
            sample = list(parts.items())[:3]
            print(f'  DamageParts/{g}: {short(defaults, 120)}; частей {len(parts)}: '
                  + ', '.join(f'{p}{short(pv, 60)}' for p, pv in sample))
        for tc in items(d.get('tank_crew')):
            print('  tank_crew:', short(tc, 400))
        for s in items(d.get('ammoStowages')):
            for sn, sv in s.items():
                for x in items(sv):
                    shells = items(x.get('shells'))
                    parts = sum(1 for sh in shells for p in sh if p.endswith('_dm'))
                    print(f'  ammoStowages/{sn}: {short({k: v for k, v in x.items() if not is_block(v)}, 200)}; '
                          f'блоков shells {len(shells)}, частей {parts}')
        mods = [m for m, x in d.get('modifications', {}).items()
                if any(s in json.dumps(x) for s in ('hideNodes', 'DamageParts', 'changeMass'))]
        print('  модификации с hideNodes/DamageParts/changeMass:', ', '.join(mods) or '—')


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    root = sys.argv[1]
    gd = os.path.join(root, 'aces.vromfs.bin_u', 'gamedata')
    if not os.path.isdir(os.path.join(gd, 'damage_model')):
        sys.exit(f'нет {gd}/damage_model — укажите корень клона датамайна')
    try:
        rev = subprocess.run(['git', '-C', root, 'log', '-1', '--format=%h %cs'],
                             capture_output=True, text=True).stdout.strip()
    except OSError:
        rev = ''
    print(f'Датамайн: {root} (коммит {rev or "?"})')
    units = load_units(gd)
    print('Машин:', ', '.join(f'{CLS_RU[c]} {len(v)}' for c, v in by_class(units).items()))
    survey_damage_parts(units)
    survey_armor_classes(gd, units)
    survey_crew(units, root)
    survey_fire(gd, units)
    survey_stowage(units)
    survey_effects(units)
    survey_mods_refs(units)
    survey_test_units(units)
    survey_missions(root)


if __name__ == '__main__':
    main()
