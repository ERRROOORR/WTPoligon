"""Командная строка для проверки без окна (этап 1):

  python -m wtpoligon list [--kind tank|air|heli|ship] [--country ussr] [--find т-80] [--hangar] [--limit N]
  python -m wtpoligon                                                — окно программы (этап 2)
  python -m wtpoligon mission <машина> [--hangar|--copy] [сценарий] [--show] — что будет записано (без записи)
  python -m wtpoligon install <машина> [--hangar|--copy] [сценарий] [--dry-run] — записать миссию
  python -m wtpoligon scenarios                                      — места и мишени на выбор
     сценарий: --spawn <место> --targets <набор|none> --distance <м> --air-target <бот|none>
               --air-distance <км> --radar   (по умолчанию — как в targets.default_scenario)
  python -m wtpoligon pylons <машина>                                — пилоны, варианты и штатные пресеты (этап 3)
  python -m wtpoligon weapons [--find фаб|ф15с] [--kind bomb] [--all] — оружие по названию или носителю
     подвеска (mission/install): --preset <штатный> --slot N=<вариант|оружие[:точек]|none> (новая схема)
               --point N=<оружие> (старая схема) --weightless --saved <имя из библиотеки>
  python -m wtpoligon uninstall <машина>|--all [--dry-run]           — откат по манифесту
  python -m wtpoligon status                                         — что записано программой
  python -m wtpoligon check-all [--kind K] [--mode both|hangar|copy] [--report файл]
  python -m wtpoligon hangar add|remove|forget <машины…> | hangar list
  python -m wtpoligon set-game <папка игры>
  python -m wtpoligon crashlog [--lines 60]                         — лог игры после вылета (ошибки и конец)

Источник: установленная игра (автопоиск %LOCALAPPDATA%\\WarThunder, --game, set-game) или --datamine <клон>.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys
import time

from . import build as BL
from . import hangar as H
from . import install as I
from . import loadout as L
from . import paths as P
from . import targets as T
from .scenarios.model import Scenario as NewScenario
from .scenarios.catalog import CATEGORIES as SCENARIO_CATEGORIES
from .game import images as IMG
from .game import index as X
from .game import source as S


class CliError(Exception):
    pass


def _ctx(a):
    root = a.app_dir or P.app_root()
    if a.datamine:
        src = S.open_source(datamine=a.datamine)
    else:
        game = P.find_game_dir(a.game, root)
        if not game:
            raise CliError('Игра не найдена%s. Укажите --game <папка игры> или python -m wtpoligon set-game <папка>; '
                           'без игры — --datamine <клон датамайна>.' % (' в ' + a.game if a.game else ''))
        src = S.open_source(game_dir=game)
    vehicles, stats = X.load_index(src, os.path.join(root, 'cache'), a.refresh)
    return root, src, vehicles, stats


def _mark(marks, name):
    return {True: 'да', False: 'нет', None: '?'}[H.status(marks, name)]


def _pick(vehicles, query):
    v = X.find(vehicles, query)
    if v:
        return v
    scored = X.search_scored(vehicles, query)
    found = [v for v, _s in scored]
    if len(found) == 1 or (len(found) > 1 and scored[0][1] > scored[1][1] and scored[0][1] >= 98):
        return found[0]
    if not found:
        raise CliError('Машина «%s» не найдена (python -m wtpoligon list --find …).' % query)
    lines = ['Под «%s» подходит %d машин, укажите внутреннее имя:' % (query, len(found))]
    lines += ['  %-40s %s' % (v['name'], v['ru'] or v['en']) for v in found[:20]]
    if len(found) > 20:
        lines.append('  …')
    raise CliError('\n'.join(lines))


def _in_hangar(a, root, v):
    if a.hangar:
        return True
    if a.copy:
        return False
    return bool(H.status(H.load(root), v['name']))


def cmd_list(a):
    root, src, vehicles, stats = _ctx(a)
    marks = H.load(root)
    found = X.search(vehicles, a.find, a.kind, a.country)
    if a.hangar:
        found = [v for v in found if H.status(marks, v['name'])]
    shown = found if not a.limit else found[:a.limit]
    print('%-40s %-9s %-14s %4s %5s  %-6s %s' % ('машина', 'вид', 'страна', 'ранг', 'БР', 'ангар', 'название'))
    for v in shown:
        print('%-40s %-9s %-14s %4s %5s  %-6s %s' % (
            v['name'], X.KIND_NAMES[v['kind']], v['country'] or '-', v['rank'] or '-', v['br'] or '-',
            _mark(marks, v['name']), v['ru'] or v['en']))
    kinds = collections.Counter(v['kind'] for v in vehicles)
    print('Показано %d из %d найденных; всего в индексе %d (%s). Источник: %s' % (
        len(shown), len(found), len(vehicles), ', '.join('%s %d' % (X.KIND_NAMES[k], kinds[k]) for k in kinds),
        src.describe()))
    return 0


def scenario_from_args(a, kind):
    """Сценарий из опций командной строки поверх сценария по умолчанию для вида техники."""
    if getattr(a, 'scenario_json', None):
        with open(a.scenario_json, encoding='utf-8') as stream:
            return NewScenario.from_dict(json.load(stream))
    sc = T.default_scenario(kind)
    if a.spawn:
        sc.spawn = a.spawn
        if a.spawn in T.SPAWN_CHOICES:
            _t, _m, _k, ground_ok, air_ok = T.SPAWN_CHOICES[a.spawn]
            sc.ground = sc.ground if ground_ok else ''
            sc.air = sc.air if air_ok else ''
    if a.targets:
        sc.ground = '' if a.targets == 'none' else a.targets
    if a.distance is not None:
        sc.ground_distance = a.distance
    if a.air_target:
        sc.air = '' if a.air_target == 'none' else a.air_target
    if a.air_distance is not None:
        sc.air_distance = int(round(a.air_distance * 1000))
    if a.radar:
        sc.air_radar = True
    return sc


def _weapon(catalog, text):
    """Оружие каталога по пути или имени файла (без .blk), например su_fab9000."""
    key = L.weapon_key(text if text.endswith('.blk') else text + '.blk')
    found = [w for w in catalog if L.weapon_key(w['path']) == key or w['stem'] == key.rsplit('/', 1)[-1][:-4]]
    if len(found) != 1:
        raise CliError('Оружие «%s» %s (python -m wtpoligon weapons --find …).' % (
            text, 'не найдено' if not found else 'неоднозначно: ' + ', '.join(w['path'] for w in found[:5])))
    return found[0]['path']


def loadout_from_args(a, root, src, v):
    """Подвеска из опций (или None — штатный пресет по умолчанию) и каталог оружия."""
    if not (a.preset or a.slot or a.point or a.weightless or a.saved):
        return None, None
    if v['kind'] not in ('air', 'heli'):
        raise CliError('Подвеска — только у самолётов и вертолётов.')
    pylons = L.read_pylons(src.load(v['file']))
    catalog = L.load_catalog(src, os.path.join(root, 'cache'))
    if a.saved:
        lo = L.library_get(root, v['name'], a.saved)
        if lo is None:
            raise CliError('В библиотеке нет пресета «%s» для %s (есть: %s).' % (
                a.saved, v['name'], ', '.join(L.library_names(root, v['name'])) or 'ничего'))
    elif a.preset:
        try:
            lo = L.from_preset(src, pylons, a.preset)
        except ValueError as e:
            raise CliError(str(e))
    else:
        lo = L.Loadout()
    for item in a.slot or []:
        index, _, value = item.partition('=')
        if pylons.scheme != 'slots' or not index.isdigit() or pylons.slot(int(index)) is None:
            raise CliError('--slot %s: нет такого пилона (python -m wtpoligon pylons %s).' % (item, v['name']))
        s = pylons.slot(int(index))
        if value == 'none':
            lo.slots.pop(s.index, None)
        elif s.variant(value):
            lo.slots[s.index] = {'variant': value}
        else:
            weapon, _, count = value.partition(':')
            choice = {'weapon': _weapon(catalog, weapon), 'sample': s.variants[0].name}
            if count:
                choice['count'] = int(count)
            lo.slots[s.index] = choice
    for item in a.point or []:
        index, _, value = item.partition('=')
        if pylons.scheme != 'legacy' or not index.isdigit() or not lo.base:
            raise CliError('--point — для старой схемы вместе с --preset <штатный пресет-основа>.')
        lo.legacy[int(index)] = _weapon(catalog, value)
    lo.weightless = lo.weightless or a.weightless
    return lo, catalog


def _plan(a):
    root, src, vehicles, _ = _ctx(a)
    v = _pick(vehicles, a.unit)
    lo, catalog = loadout_from_args(a, root, src, v)
    plan = BL.stock_plan(src, v, _in_hangar(a, root, v), scenario=scenario_from_args(a, v['kind']), loadout=lo,
                         catalog=catalog, vehicles=vehicles)
    return root, src, plan, BL.verify_plan(src, plan)


def cmd_pylons(a):
    root, src, vehicles, _ = _ctx(a)
    v = _pick(vehicles, a.unit)
    py = L.read_pylons(src.load(v['file']))
    names = L._names(src)
    print('%s (%s): схема подвески — %s' % (v['name'], v['ru'] or v['en'], {
        'slots': 'пилоны (WeaponSlots)', 'legacy': 'старая (только целые пресеты)', '': 'нет'}[py.scheme]))
    if py.limits:
        print('Пределы (в ангаре; миссия их не проверяет): ' + ', '.join('%s %g' % kv for kv in py.limits.items()))
    pairs = L.mirror_pairs(py)
    for s in py.slots:
        print('Пилон %d%s%s%s:' % (s.index, ' — встроенное' if s.fixed else '',
                                   {'L': ', слева', 'R': ', справа'}.get(s.side, ''),
                                   ', пара — %d (предположение)' % pairs[s.index] if s.index in pairs else ''))
        for var in s.variants:
            ws = collections.Counter(L.weapon_title(src, w.get('blk'), names) for w in var.weapons)
            print('    %-34s %s' % (var.name, ', '.join('%s ×%d' % kv for kv in ws.items()) or '—'))
    print('Штатные пресеты (--preset):')
    for name, path in py.presets:
        print('  %-36s %s' % (name, path))
    return 0


def cmd_icons(a):
    """Диагностика картинок интерфейса (иконки вооружения и техники из atlases.vromfs.bin)."""
    _root, src, _vehicles, _ = _ctx(a)
    if src.kind == 'game':
        path = src.archive_path('atlases')
        print('Архив картинок: %s' % (path or 'НЕ НАЙДЕН в папке игры ' + src.root))
        vf = src._vromfs('atlases')
        if src.errors.get('atlases'):
            print('Ошибка чтения: ' + src.errors['atlases'])
        if vf is not None:
            names = list(vf.files)
            print('Файлов в архиве: %d' % len(names))
            for prefix in ('gameuiskin/', 'units/'):
                found = [n for n in names if prefix in n.lower()]
                print('  с «%s»: %d, например: %s' % (prefix, len(found), ', '.join(found[:3])))
            exts = collections.Counter(n.rsplit('.', 1)[-1].lower() for n in names if '.' in n)
            print('  расширения: ' + ', '.join('%s %d' % kv for kv in exts.most_common(6)))
        import importlib.util
        print('Распаковщик Oodle: %s' % ('pyooz' if importlib.util.find_spec('ooz') else
                                         IMG.oodle_dll(src.root) or 'НЕТ — pip install -r requirements.txt'))
    for name in a.names or ['gameuiskin/bombs_middle.png', 'gameuiskin/ptb.png', 'units/f_15c_golden_eagle.png']:
        src.errors.pop('atlas', None) if src.kind == 'game' else None
        data = src.atlas_file(name)
        kind = ('PNG' if data[:4] == b'\x89PNG' else 'SVG' if b'<svg' in data[:300] else 'другое: %r' % data[:8]
                ) if data else 'НЕ ПРОЧИТАНА'
        print('%-45s %s%s' % (name, kind, ', %d байт' % len(data) if data else ''))
        if not data and src.kind == 'game':
            print('    причина: %s' % (src.errors.get('atlas') or 'файла нет в архиве'))
            raw = src.atlas_raw(name.rsplit('.', 1)[0] + '.ddsx')
            if raw:
                print('    заголовок ddsx: %s; первые байты: %s' % (IMG.ddsx_header(raw), raw[:48].hex()))
                if a.dump:
                    print('    файл целиком (%d байт):' % len(raw))
                    print(raw.hex())
    return 0


# строки лога, важные для вылета: ошибки/предупреждения движка, падения и всё про миссию программы
CRASH_MARKS = (' [E] ', ' [W] ', 'CRITICAL', 'FATAL', 'assert', 'Exception', 'exception', 'crash', 'wtp5_')
CRASH_NOISE = ('killstreaks', 'center node', 'not fastest codepath', 'collision point not found')


MISSION_MARK = re.compile(r'wtp5t?_')     # миссии программы и тестовые миссии исследований


def cmd_crashlog(a):
    """Свежий лог игры с запуском миссии программы (wtp5_) или тестовой (wtp5t_): ошибки и последние строки — для разбора вылета."""
    from .game import clog
    root = a.app_dir or P.app_root()
    game = a.game or P.find_game_dir(None, root)
    logs = os.path.join(game or '', '.game_logs')
    files = sorted(glob.glob(os.path.join(logs, '*.clog')), key=os.path.getmtime, reverse=True)
    if not files:
        raise CliError('Нет логов игры в %s' % logs)
    key = clog.key_for_dir(logs)
    # лог с запуском миссии (AcesApp::doJob … wtp5_/wtp5t_); имя копии в ангаре после перезапуска игры — не запуск
    started = mentioned = None
    for path in files[:a.depth]:
        with open(path, 'rb') as f:
            text = clog.decrypt(f.read(), key).decode('utf-8', 'replace')
        if a.any or any('AcesApp::doJob' in ln and MISSION_MARK.search(ln) for ln in text.splitlines()):
            started = (path, text)
            break
        if mentioned is None and MISSION_MARK.search(text):
            mentioned = (path, text)
    if started is None and mentioned is None:
        raise CliError('В последних %d логах нет миссий программы (wtp5_/wtp5t_). Запустите миссию ещё раз или --any.'
                       % a.depth)
    path, text = started or mentioned
    out = os.path.join(root, 'cache', 'logs')
    os.makedirs(out, exist_ok=True)
    full = os.path.join(out, os.path.basename(path)[:-5] + '.log')
    with open(full, 'w', encoding='utf-8') as f:
        f.write(text)
    lines = text.splitlines()
    print('Лог: %s (%s), строк %d; целиком: %s' % (os.path.basename(path), time.strftime(
        '%d.%m %H:%M', time.localtime(os.path.getmtime(path))), len(lines), full))
    start = max((i for i, ln in enumerate(lines) if 'AcesApp::doJob' in ln and MISSION_MARK.search(ln)), default=0)
    hits, seen = [], set()
    for ln in lines[max(0, start - 200):]:                   # с загрузки последней миссии программы
        if any(m in ln for m in CRASH_MARKS) and not any(n in ln for n in CRASH_NOISE):
            msg = ln.split(' ', 1)[-1]                       # без времени — повторы в одну строку
            if msg not in seen:
                seen.add(msg)
                hits.append(ln)
    print('--- важное с загрузки миссии (%d, последние %d) ---' % (len(hits), min(len(hits), a.lines)))
    print('\n'.join(hits[-a.lines:]))
    print('--- конец лога ---')
    print('\n'.join(lines[-a.lines:]))
    return 0


def cmd_weapons(a):
    root, src, vehicles, _ = _ctx(a)
    catalog = L.load_catalog(src, os.path.join(root, 'cache'), a.refresh)
    found, carriers = L.search_weapons(catalog, vehicles, a.find, not a.all)
    found = [w for w in found if not a.kind or w['kind'] == a.kind]
    if carriers:
        print('Всё вооружение: %s' % ', '.join(c['ru'] or c['en'] or c['name'] for c in carriers))
    for w in found[:a.limit or None]:
        print('%-44s %-10s %8.1f кг  %s%s' % (w['stem'], L.KIND_NAMES[w['kind']], w['mass'], w['ru'] or w['en'],
                                             '' if w['air'] else '  📄 не с авиации'))
    print('Найдено %d из %d.' % (len(found), len(catalog)))
    return 0


def cmd_scenarios(a):
    print('Режимы и категории новой модели (файл --scenario-json для mission/install):')
    for mode, categories in SCENARIO_CATEGORIES.items():
        print('  %s: %s' % (mode, ', '.join(title for _, title, _ in categories) or 'противник'))
    print('Места появления (--spawn):')
    for k, (title, _m, kinds, ground_ok, air_ok) in T.SPAWN_CHOICES.items():
        print('  %-22s %s; техника: %s%s%s' % (k, title, ', '.join(X.KIND_NAMES[x] for x in kinds),
                                              '; наземные мишени' if ground_ok else '',
                                              '; воздушная цель' if air_ok else ''))
    print('Наземные мишени (--targets, none — без них):')
    for k, (title, _c, ok) in T.TARGET_SETS.items():
        print('  %-22s %s%s' % (k, title, '' if ok else '  📄 не проверено в игре'))
    print('  дистанция (--distance, м): %s; 0 — как в тест-драйве игры (полигон: 225–1190 м за речкой)' %
          ', '.join(map(str, T.GROUND_DISTANCES)))
    print('Воздушная цель (--air-target, none — без неё; --air-distance км; --radar — включить РЛС бота):')
    for k, (title, _c, _s, radar) in T.AIR_BOTS.items():
        print('  %-22s %s' % (k, title))
    print('По умолчанию: наземка — полигон с советскими танками; самолёт — Дания, МиГ-15 в 10 км; '
          'вертолёт и флот — без мишеней.')
    return 0


def _print_plan(plan, problems, show=False):
    v = plan.vehicle
    print('Машина: %s (%s, %s), файл %s' % (v['name'], v['ru'] or v['en'], X.KIND_NAMES[v['kind']], v['file']))
    print('Запуск: %s; в миссии — %s; пресет вооружения: %s' % (
        'из ангара под настоящим именем' if plan.launch == BL.HANGAR else 'копия не из ангара',
        plan.unit_class, plan.weapons or '(штатный)'))
    if plan.scenario and not plan.problems and (isinstance(plan.scenario, NewScenario) or
                                                plan.scenario.spawn in T.SPAWN_CHOICES):
        for line in (BL.SB.describe(plan.scenario) if isinstance(plan.scenario, NewScenario)
                     else T.describe(plan.scenario)):
            print('  ' + line)
    for n in plan.notes:
        print('  · ' + n)
    print('Файлы (%d):' % len(plan.files))
    for rel, text in plan.files:
        print('  %s (%d строк)' % (rel, text.count('\n')))
    if show:
        for rel, text in plan.files:
            print('=== %s\n%s' % (rel, text))
    if problems:
        print('ОШИБКИ сборки (%d) — записывать нельзя:' % len(problems))
        for p in problems:
            print('  ' + p)
    else:
        print('Проверка моделью правок: 0 ошибок.')


def cmd_mission(a):
    _root, _src, plan, problems = _plan(a)
    _print_plan(plan, problems, a.show)
    print('Только показ: ничего не записано (запись — install).')
    return 1 if problems else 0


def _target(a, src, meta=None):
    if a.target:
        return a.target
    if meta and meta.get('game_dir'):
        return meta['game_dir']
    if src is not None and src.kind == 'game':
        return src.root
    raise CliError('Куда писать? Источник — датамайн: укажите --target <папка игры>.')


def cmd_install(a):
    root, src, plan, problems = _plan(a)
    _print_plan(plan, problems)
    if problems:
        print('Ничего не записано.')
        return 1
    target = _target(a, src)
    meta = {'unit': plan.vehicle['name'], 'launch': plan.launch, 'mission': plan.mission,
            'game_dir': os.path.abspath(target), 'source': src.describe(), 'scenario': plan.scenario.to_dict(),
            'loadout': plan.loadout.to_dict() if plan.loadout else None}
    ok, report = I.install(target, root, plan.app_id, plan.files, meta, a.dry_run)
    for s in report:
        print(s)
    if not ok:
        print('Ничего не записано: путь занят чужим файлом или нарушает правила записи.')
        return 1
    if a.dry_run:
        print('Пробный прогон: ничего не записано.')
    else:
        print('Готово. В игре: Одиночные миссии → Пользовательские → «WTP5 — %s» (файл %s). '
              'Перезапуск игры не нужен.' % (plan.vehicle['ru'] or plan.vehicle['en'] or plan.vehicle['name'],
                                             plan.mission_path))
    return 0


def cmd_uninstall(a):
    root = a.app_dir or P.app_root()
    apps = I.installed(root)
    if a.all:
        ids = list(apps)
    elif a.unit:
        ids = [a.unit.lower()]
    else:
        raise CliError('Укажите машину или --all (список — python -m wtpoligon status).')
    if not ids:
        print('Программа ничего не записывала.')
        return 0
    for app_id in ids:
        meta = apps.get(app_id, {}).get('meta', {})
        target = _target(a, None, meta) if app_id in apps else (a.target or '')
        print('— %s (%s)' % (app_id, target or '?'))
        for s in I.uninstall(target, root, app_id, a.dry_run):
            print('  ' + s)
    return 0


def cmd_status(a):
    root = a.app_dir or P.app_root()
    rows = I.status(root)
    if not rows:
        print('Программа ничего не записывала (%s).' % os.path.join(root, I.INSTALLS))
        return 0
    for app_id, meta, state in rows:
        print('%-36s %-6s %s, %s; файлов %d (%s)' % (
            app_id, meta.get('launch', '?'), meta.get('mission', ''), meta.get('installed', ''),
            sum(state.values()), ', '.join('%s %d' % kv for kv in state.items())))
    return 0


def check_all(src, vehicles, modes=(BL.HANGAR, BL.COPY), progress=None):
    """Стоковая миссия для каждой машины в каждом способе запуска + проверка; дубли путей между машинами.
    -> (ошибки [(машина, способ, текст)], статистика {(вид, способ): число})."""
    gmods = BL.global_mods(src)
    errors, counts, owner = [], collections.Counter(), {}
    for n, v in enumerate(vehicles, 1):
        for mode in modes:
            try:
                plan = BL.stock_plan(src, v, mode == BL.HANGAR, gmods)
                problems = BL.verify_plan(src, plan)
            except Exception as e:  # noqa: BLE001 — сбой сборки одной машины не должен прятать остальные
                problems, plan = ['сбой: %s: %s' % (type(e).__name__, e)], None
            for p in problems:
                errors.append((v['name'], mode, p))
            if plan is not None:
                for rel, _ in plan.files:
                    key = rel.lower()
                    prev = owner.setdefault(key, (v['name'], mode))
                    if prev[0] != v['name']:
                        errors.append((v['name'], mode, 'тот же путь, что у %s: %s' % (prev[0], rel)))
            counts[v['kind'], mode] += 1
        if progress and n % 500 == 0:
            progress(n)
    return errors, counts


def cmd_check_all(a):
    _root, src, vehicles, stats = _ctx(a)
    chosen = [v for v in vehicles if not a.kind or v['kind'] == a.kind]
    if a.limit:
        chosen = chosen[:a.limit]
    modes = (BL.HANGAR, BL.COPY) if a.mode == 'both' else (a.mode,)
    print('Источник: %s; машин: %d; способы: %s' % (src.describe(), len(chosen), ', '.join(modes)))
    t0 = time.time()
    errors, counts = check_all(src, chosen, modes, lambda n: print('  … %d машин, %.0f с' % (n, time.time() - t0)))
    lines = ['Итог check-all (%s), %.0f с:' % (src.describe(), time.time() - t0)]
    for kind in X.KIND_NAMES:
        row = ['%s %d' % (m, counts[kind, m]) for m in modes if counts[kind, m]]
        if row:
            lines.append('  %-10s %s' % (X.KIND_NAMES[kind], ', '.join(row)))
    lines.append('  всего миссий собрано: %d; ошибок: %d' % (sum(counts.values()), len(errors)))
    if stats.get('no_file'):
        lines.append('  в реестре без файла машины (не в индексе): %d' % len(stats['no_file']))
    by_unit = collections.OrderedDict()
    for name, mode, p in errors:
        by_unit.setdefault((name, mode), []).append(p)
    lines += ['  %s [%s]: %s' % (name, mode, '; '.join(ps)) for (name, mode), ps in by_unit.items()]
    print('\n'.join(lines[:60] + (['  … полный список — в --report'] if len(lines) > 60 else [])))
    if a.report:
        with open(a.report, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print('Отчёт: ' + a.report)
    return 1 if errors else 0


def cmd_hangar(a):
    root = a.app_dir or P.app_root()
    if a.action == 'list':
        marks = H.load(root)
        for name, owned in sorted(marks.items()):
            print('%-40s %s' % (name, 'в ангаре' if owned else 'нет в ангаре'))
        print('Отмечено: %d. Без отметки машина считается не из ангара (копия wtp5_*).' % len(marks))
        return 0
    if not a.units:
        raise CliError('Укажите машины: python -m wtpoligon hangar add <имя> [<имя>…]')
    _root, _src, vehicles, _ = _ctx(a)
    names = [_pick(vehicles, u)['name'] for u in a.units]
    H.mark(root, names, {'add': True, 'remove': False, 'forget': None}[a.action])
    print('%s: %s' % ({'add': 'В ангаре', 'remove': 'Нет в ангаре', 'forget': 'Отметка снята'}[a.action],
                      ', '.join(names)))
    return 0


def cmd_set_game(a):
    root = a.app_dir or P.app_root()
    if not P.is_game_dir(a.path):
        raise CliError('В %s нет aces.vromfs.bin — это не папка War Thunder.' % a.path)
    settings = P.load_settings(root)
    settings['game_dir'] = os.path.abspath(a.path)
    P.save_settings(root, settings)
    print('Папка игры: ' + settings['game_dir'])
    return 0


def parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--game', default=argparse.SUPPRESS, help='папка игры (по умолчанию — автопоиск)')
    common.add_argument('--datamine', default=argparse.SUPPRESS, help='клон датамайна вместо игры (без записи)')
    common.add_argument('--app-dir', default=argparse.SUPPRESS, help='папка данных программы (для тестов)')
    common.add_argument('--refresh', action='store_true', default=argparse.SUPPRESS,
                        help='пересобрать индекс техники')
    ap = argparse.ArgumentParser(prog='python -m wtpoligon', parents=[common],
                                 description='WT Poligon 5: без команды — окно, с командой — проверка без окна.')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('list', parents=[common], help='техника игры')
    p.add_argument('--kind', choices=list(X.KIND_NAMES))
    p.add_argument('--country')
    p.add_argument('--find', default='')
    p.add_argument('--hangar', action='store_true', help='только отмеченные «в ангаре»')
    p.add_argument('--limit', type=int, default=50, help='сколько показать (0 — все)')
    p.set_defaults(func=cmd_list)

    for name, func, help_ in (('mission', cmd_mission, 'показать стоковую миссию (без записи)'),
                              ('install', cmd_install, 'записать стоковую миссию в игру')):
        p = sub.add_parser(name, parents=[common], help=help_)
        p.add_argument('unit')
        g = p.add_mutually_exclusive_group()
        g.add_argument('--hangar', action='store_true', help='машина в ангаре: настоящее имя')
        g.add_argument('--copy', action='store_true', help='не из ангара: копия wtp5_*')
        p.add_argument('--spawn', choices=list(T.SPAWN_CHOICES), help='место появления')
        p.add_argument('--scenario-json', help='сценарий новой модели из JSON')
        p.add_argument('--targets', choices=['none'] + list(T.TARGET_SETS), help='наземные мишени')
        p.add_argument('--distance', type=int, choices=T.GROUND_DISTANCES, help='дистанция наземных мишеней, м')
        p.add_argument('--air-target', choices=['none'] + list(T.AIR_BOTS), help='воздушная цель')
        p.add_argument('--air-distance', type=float, help='дистанция воздушной цели, км')
        p.add_argument('--radar', action='store_true', help='включить РЛС воздушной цели')
        p.add_argument('--preset', help='подвеска: как штатный пресет (основа)')
        p.add_argument('--slot', action='append', help='пилон: N=<вариант|оружие[:точек]|none> (можно несколько)')
        p.add_argument('--point', action='append', help='старая схема: N=<оружие> на N-й точке пресета-основы')
        p.add_argument('--weightless', action='store_true', help='невесомая подвеска')
        p.add_argument('--saved', help='подвеска из библиотеки по имени')
        if name == 'mission':
            p.add_argument('--show', action='store_true', help='напечатать тексты файлов')
        else:
            p.add_argument('--dry-run', action='store_true')
            p.add_argument('--target', help='папка игры для записи (по умолчанию — источник)')
        p.set_defaults(func=func)

    p = sub.add_parser('scenarios', parents=[common], help='места и мишени на выбор')
    p.set_defaults(func=cmd_scenarios)

    p = sub.add_parser('pylons', parents=[common], help='пилоны и пресеты самолёта/вертолёта')
    p.add_argument('unit')
    p.set_defaults(func=cmd_pylons)

    p = sub.add_parser('crashlog', parents=[common], help='лог игры после вылета: ошибки и конец лога')
    p.add_argument('--lines', type=int, default=60, help='сколько строк показывать')
    p.add_argument('--depth', type=int, default=6, help='сколько последних логов просматривать')
    p.add_argument('--any', action='store_true', help='самый свежий лог, даже без миссий программы')
    p.set_defaults(func=cmd_crashlog)

    p = sub.add_parser('icons', parents=[common], help='проверка картинок из игры (иконки оружия и техники)')
    p.add_argument('names', nargs='*', help='пути внутри архива, например gameuiskin/ptb.png')
    p.add_argument('--dump', action='store_true', help='напечатать непрочитанный .ddsx целиком (для разбора)')
    p.set_defaults(func=cmd_icons)

    p = sub.add_parser('weapons', parents=[common], help='каталог оружия для подвески')
    p.add_argument('--find', default='')
    p.add_argument('--kind', choices=list(L.KIND_NAMES))
    p.add_argument('--all', action='store_true', help='всё оружие игры, не только подвесное')
    p.add_argument('--limit', type=int, default=50)
    p.set_defaults(func=cmd_weapons)

    p = sub.add_parser('uninstall', parents=[common], help='откат записанного программой')
    p.add_argument('unit', nargs='?')
    p.add_argument('--all', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--target', help='папка игры (по умолчанию — из манифеста)')
    p.set_defaults(func=cmd_uninstall)

    p = sub.add_parser('status', parents=[common], help='что записано программой')
    p.set_defaults(func=cmd_status)

    p = sub.add_parser('check-all', parents=[common], help='миссия собирается для всей техники')
    p.add_argument('--kind', choices=list(X.KIND_NAMES))
    p.add_argument('--mode', choices=('both', BL.HANGAR, BL.COPY), default='both')
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--report')
    p.set_defaults(func=cmd_check_all)

    p = sub.add_parser('hangar', parents=[common], help='отметить машины «в ангаре»')
    p.add_argument('action', choices=('add', 'remove', 'forget', 'list'))
    p.add_argument('units', nargs='*')
    p.set_defaults(func=cmd_hangar)

    p = sub.add_parser('set-game', parents=[common], help='запомнить папку игры')
    p.add_argument('path')
    p.set_defaults(func=cmd_set_game)
    return ap


COMMANDS = {'list', 'mission', 'install', 'uninstall', 'status', 'check-all', 'hangar', 'set-game', 'scenarios',
            'pylons', 'weapons', 'icons', 'crashlog'}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass
    args = sys.argv[1:] if argv is None else list(argv)
    if not set(args) & (COMMANDS | {'-h', '--help'}):
        from .gui.app import main as gui_main   # без команды — окно (PySide6 нужен только ему)
        return gui_main(args)
    a = parser().parse_args(args)
    for k, default in (('game', None), ('datamine', None), ('app_dir', None), ('refresh', False)):
        if not hasattr(a, k):
            setattr(a, k, default)
    try:
        return a.func(a)
    except (CliError, FileNotFoundError) as e:
        print(e, file=sys.stderr)
        return 2
