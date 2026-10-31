"""Сборка (docs/architecture.md §3): машина + способ запуска -> набор файлов (путь от папки игры -> текст).
Чистая функция: на диск не пишет (это install). Проверка набора — verify_plan (модель правок = лог игры).

Этап 1 — стоковая миссия (ТЗ §6.1: пока правок нет, в игру идёт стоковая машина). Способ запуска (launch.md §8):
  - машина из ангара — под настоящим именем, файлов машины нет, только миссия (полноценна);
  - не из ангара — копия wtp5_<имя> = include стокового файла + перенос модификаций-блоков (дымы, тепловизор —
    8-й круг) + копии пусковых составного ЗРК (supportPlanes, 4-й круг); ездит и стреляет, но неполноценна.
"""
from dataclasses import dataclass, field

from . import install as I
from . import loadout as L
from . import edits as E
from . import targets as T
from .scenarios.model import Scenario as NewScenario
from .scenarios import build as SB, validate as SV
from .scenarios.catalog import CATEGORIES as SCENARIO_CATEGORIES
from .ammo import build as AB
from .game import blk as B
from .game import mods as M
from .mission import KINDS, PREFIX, SPAWNS, mission_text

HANGAR, COPY = 'hangar', 'copy'
PKG = 'content/pkg_local/gameData/'
# ссылка supportPlanes/plane/class -> папка файла (пусковые ЗРК — tankModels, launch.md §5.1)
SUPPORT_FOLDERS = {'tankModels': 'units/tankModels'}

NOTE_HANGAR = ('Машина из ангара — под настоящим именем, полноценная (launch.md §8). Если её на самом деле нет '
               'в ангаре, игра сразу выйдет в дебрифинг («Hero in userMission must be a unit owned by player»).')
NOTE_COPY = ('Машины нет в ангаре (или она не отмечена: в окне — галочка «Есть в моём ангаре», в командной строке — '
             'hangar add <имя>) — запускается копия '
             '%s под своим именем. Ездит/летает и стреляет, но неполноценна: в интерфейсе внутреннее имя, нет '
             'иконок снарядов; из модификаций работают только перенесённые блоки (дымы, тепловизор).')
NOTE_HELI = 'Вертолёт-копия получает самолётный интерфейс (HUD вертолёта — только у машины из ангара, 22-й круг).'
NOTE_LOADOUT = ('Подвеска изменена, поэтому в миссии будет копия этого самолёта (%s): свой набор оружия игра '
                'принимает только у копии (22-й круг). Летает и стреляет так же; в интерфейсе вместо названия — '
                'внутреннее имя, часть модификаций не работает. Штатный пресет без изменений едет на машине из '
                'ангара.')
NOTE_SAM = 'Пусковые ЗРК — тоже копии (%d шт.): кнопки вызова в интерфейсе нет, клавиша вызова работает (4-й круг).'
NOTE_STATS = 'Характеристики изменены: машина едет копией %s. Новые названия появятся после перезапуска игры.'


@dataclass
class Plan:
    vehicle: dict
    launch: str                       # HANGAR | COPY
    unit_class: str = ''              # имя машины в миссии
    mission: str = ''                 # mission{name} = имя файла миссии без .blk
    weapons: str = ''                 # пресет вооружения игрока
    scenario: T.Scenario = None       # место и мишени (этап 2)
    loadout: L.Loadout = None         # подвеска авиации (этап 3); None — штатный пресет по умолчанию
    ammo: object = None
    files: list = field(default_factory=list)      # [(путь от папки игры, текст)]
    notes: list = field(default_factory=list)      # что увидит пользователь (ограничения способа запуска)
    problems: list = field(default_factory=list)   # ошибки сборки: с ними не пишем

    @property
    def app_id(self):
        return self.vehicle['name'].lower()

    @property
    def mission_path(self):
        return '%s/%s.blk' % (I.MISSION_DIR, self.mission)


def copy_name(name):
    return PREFIX + name.lower()


def default_preset(unit, name, kind):
    """Пресет вооружения по умолчанию: <имя>_default, иначе первый с 'default' в имени, иначе первый.
    Корабль — пусто, как в проверенной миссии 4 (Fletcher, 27-й круг)."""
    if kind == 'ship':
        return ''
    wp = unit.block('weapon_presets')
    names = [p.get('name') for p in (wp.blocks if wp else []) if p.get('name')]
    exact = [n for n in names if n.lower() == name.lower() + '_default']
    return (exact or [n for n in names if 'default' in n.lower()] or names or [''])[0]


def unit_presets(unit):
    wp = unit.block('weapon_presets')
    return [p.get('name') for p in (wp.blocks if wp else [])]


def global_mods(source):
    root = source.config('modifications')
    if root is None:
        return B.Block('modifications')
    return root.block('modifications') or root


def copy_file_text(folder, base, name, extra=''):
    return ('// WT Poligon 5: копия %s (стоковая машина не из ангара, launch.md §8).\n'
            '// Убрать: python -m wtpoligon uninstall %s\n'
            'include "#/develop/gameBase/gameData/%s/%s.blk"\n%s') % (base, name, folder, base, extra)


def support_refs(unit):
    """[(номер plane с 1, class)] из supportPlanes."""
    sp = unit.block('supportPlanes')
    planes = [b for b in (sp.blocks if sp else []) if b.name == 'plane']
    return [(i, p.get('class')) for i, p in enumerate(planes, 1)]


def support_overrides(classes):
    """@override ссылок supportPlanes/plane[N]/class (номера с 1, ссылка всегда с папкой — launch.md §5.1).
    classes — {номер plane: новая ссылка}."""
    lines = ['"@override:supportPlanes"{']
    for i, cls in sorted(classes.items()):
        lines += ['  "@override:plane[%d]"{' % i, '    "@override:class":t=%s' % B.quote(cls), '  }']
    lines.append('}')
    return '\n'.join(lines) + '\n'


def stock_plan(source, vehicle, in_hangar, gmods=None, scenario=None, loadout=None, catalog=None, stats=None,
               vehicles=None, ammo=None):
    """План миссии для машины индекса. in_hangar — запуск под настоящим именем; scenario — место и мишени
    (по умолчанию — targets.default_scenario вида техники); loadout — подвеска самолёта/вертолёта (loadout.py):
    штатный пресет без изменений — как есть, своя подвеска — копия машины (22-й круг); catalog — каталог оружия
    (триггер и количество чужого оружия)."""
    name, kind = vehicle['name'], vehicle['kind']
    sc = scenario or T.default_scenario(kind)
    plan = Plan(vehicle, HANGAR if in_hangar else COPY, mission=copy_name(name), scenario=sc, loadout=loadout,
                ammo=ammo)
    if isinstance(sc, NewScenario):
        if vehicles is not None:
            plan.problems += SV.check(sc, vehicles)
        if sc.mode == 'duel' and not sc.duel.enemy:
            plan.problems.append('не выбран противник')
        for key, cat in sc.categories.items():
            if key in {k for k, _, _ in SCENARIO_CATEGORIES[sc.mode]}:
                if cat.count != cat.total():
                    plan.problems.append('%s: количество не совпадает со списком' % key)
                if cat.br_min > cat.br_max:
                    plan.problems.append('%s: диапазон БР перевёрнут' % key)
        if sc.mode != {'tank': 'ground', 'ship': 'naval'}.get(kind, kind) and not (sc.mode == 'duel' and kind in ('air', 'heli')):
            plan.problems.append('режим сценария не подходит машине игрока')
    else:
        plan.problems += T.check_scenario(sc, kind)
    if loadout is not None and kind not in ('air', 'heli'):
        plan.problems.append('подвеска — только у самолётов и вертолётов')
    if plan.problems:
        return plan
    unit = source.load(vehicle['file'])
    if unit is None:
        plan.problems.append('нет файла машины ' + vehicle['file'])
        return plan
    plan.weapons = default_preset(unit, name, kind)
    custom = None
    if loadout is not None:
        pylons = L.read_pylons(unit)
        stock = L.stock_preset_of(source, pylons, loadout)
        if stock:
            plan.weapons = stock
        elif not pylons.scheme:
            plan.problems.append('у машины нет подвески (ни WeaponSlots, ни weapon_presets)')
            return plan
        else:
            custom = pylons
            if in_hangar:
                in_hangar = False
                plan.launch = COPY
                plan.notes.append(NOTE_LOADOUT % copy_name(name))
    if stats is not None and stats.changed() and in_hangar:
        in_hangar = False
        plan.launch = COPY
        plan.notes.append(NOTE_STATS % copy_name(name))
    if ammo is not None and (ammo.gun or ammo.added or ammo.edits or ammo.air_guns or
                             (ammo.stock_capacity and ammo.capacity != ammo.stock_capacity)) and in_hangar:
        in_hangar = False
        plan.launch = COPY
        plan.notes.append('Боеприпасы изменены: используется копия машины %s.' % copy_name(name))
    mods = [m.name for m in (unit.block('modifications').blocks if unit.block('modifications') else [])]
    folder = KINDS[kind][1]
    if in_hangar:
        plan.unit_class = name
        plan.notes.append(NOTE_HANGAR)
    else:
        base = name.lower()
        plan.unit_class = copy_name(name)
        if not plan.notes:          # вынужденная копия (своя подвеска) уже объяснена NOTE_LOADOUT
            plan.notes.append(NOTE_COPY % plan.unit_class)
        extra = ''
        refs = support_refs(unit)
        if refs:
            new = {}
            for i, cls in refs:
                where, _, target = (cls or '').partition('/')
                if where not in SUPPORT_FOLDERS or not target:
                    plan.problems.append('supportPlanes: неизвестная ссылка %r' % cls)
                    continue
                lname = '%s__%s' % (plan.unit_class, target.lower())
                new[i] = '%s/%s' % (where, lname)
                lfolder = SUPPORT_FOLDERS[where]
                text = copy_file_text(lfolder, target.lower(), name)
                path = '%s%s/%s.blk' % (PKG, lfolder, lname)
                if path not in dict(plan.files):
                    plan.files.append((path, text))
            extra += support_overrides(new)
            plan.notes.append(NOTE_SAM % len(dict(plan.files)))
        if kind == 'heli':
            plan.notes.append(NOTE_HELI)
        gm = gmods if gmods is not None else global_mods(source)
        extra += M.bake_text(unit, gm)
        if custom is not None:
            lfiles, ltext, plan.weapons, lprob = L.build_files(source, custom, loadout, plan.unit_class, catalog)
            plan.problems += lprob
            plan.files += lfiles
            extra += ltext
            sm = L.summarize(source, custom, loadout, catalog)
            plan.notes += ['⚠ ' + t for lvl, t in sm.warnings if lvl == 'danger']
            plan.notes += [t for lvl, t in sm.warnings if lvl in ('warn', 'info')]
            plan.notes += ['📄 ' + t for lvl, t in sm.warnings if lvl == 'untested']
        if stats is not None and stats.changed():
            extra, problems = stats_files(source, stats, plan, extra, loadout, custom, catalog)
            plan.problems += problems
            plan.notes += [e.note + ': %s → %s' % (e.stock, e.value) for e in stats.edits()]
        if ammo is not None and ammo.changed():
            afiles, atext, _bullets, aproblems = AB.build_files(source, unit, kind, plan.weapons, ammo,
                                                               plan.unit_class)
            plan.files += afiles
            extra += atext
            plan.problems += aproblems
        lost = M.lost_equipment(unit, gm)
        if lost:
            plan.notes.append('Не перенесутся в копию (только параметры, у копии не работают): ' + ', '.join(lost))
        plan.files.append(('%s%s/%s.blk' % (PKG, folder, plan.unit_class),
                           copy_file_text(folder, base, name, extra)))
    lacking = ([] if isinstance(sc, NewScenario) else T.unverified(sc))
    if lacking:
        plan.notes.append('📄 Не проверено в игре: %s.' % '; '.join(lacking))
    title = (stats.mission_title if stats and stats.mission_title else
             vehicle.get('ru') or vehicle.get('en') or name)
    parts = SB.mission_parts(sc, source) if isinstance(sc, NewScenario) else T.scenario_parts(sc)
    if ammo is not None and ammo.changed():
        if plan.launch == COPY:
            parts['bullets'] = _bullets
        else:
            _files, _text, parts['bullets'], aproblems = AB.build_files(source, unit, kind, plan.weapons, ammo,
                                                                        plan.unit_class)
            plan.problems += aproblems
    spawn = parts.pop('spawn', sc.spawn if not isinstance(sc, NewScenario) else None)
    mtype = parts.pop('mtype', sc.mtype if not isinstance(sc, NewScenario) else None)
    plan.files.append((plan.mission_path, mission_text(
        name=plan.mission, loc_name='WTP5 — ' + title,
        loc_desc=('WT Poligon 5: стоковая машина %s (%s).' %
                  (name, 'из ангара, настоящее имя' if in_hangar else 'копия ' + plan.unit_class)),
        kind=kind, spawn=spawn, mtype=mtype, unit_class=plan.unit_class, weapons=plan.weapons,
        modifications=mods, **parts,
        header='// WT Poligon 5: миссия программы. Убрать: python -m wtpoligon uninstall %s\n' % name)))
    if stats is not None and stats.title:
        import csv
        import io
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, delimiter=';', lineterminator='\n')
        writer.writerow(['<ID|readonly|noverify>', '<English>', '<Russian>'])
        for key in (plan.unit_class + '_1', plan.unit_class, plan.unit_class + '_shop',
                    plan.unit_class + '_0'):
            writer.writerow([key, stats.title, stats.title])
        plan.files.append((I.MISSION_DIR + '/usr_' + plan.mission + '.csv', stream.getvalue()))
    return plan


def stats_files(source, stats, plan, extra, loadout, pylons, catalog):
    """Копии ЛМ/сенсоров и правки машины. Каждая ссылка ведёт только на свою копию файла."""
    problems = []
    unit = stats.trees[stats.unit_file]
    by_file = E.by_file(stats.edits())
    unit_edits = by_file.pop(stats.unit_file, [])
    for file, edits in by_file.items():
        ref = stats.refs.get(file)
        if not ref:
            problems.append('нет ссылки машины на файл %s' % file)
            continue
        if ref == 'fmFile':
            copy = 'gameData/flightModels/fm/%s.blk' % plan.unit_class
            link = 'fm/%s.blk' % plan.unit_class
            if loadout is not None and loadout.weightless and pylons is not None:
                sm = L.summarize(source, pylons, loadout, catalog)
                for edit in edits:
                    if edit.path == 'Mass/EmptyMass':
                        edit.value = round(edit.value - sm.total, 1)
                        if edit.value <= 0:
                            problems.append('EmptyMass − масса подвески должна быть больше нуля')
                if not any(e.path == 'Mass/EmptyMass' for e in edits):
                    edits.append(E.make_edit(stats.trees[file], file, 'Mass/EmptyMass', sm.weightless_mass,
                                             source='rule:weightless'))
                plan.files = [(p, t) for p, t in plan.files if p != PKG + copy[len('gameData/'):]]
                extra = extra.replace('"@override:fmFile":t=%s\n' % B.quote(link), '')
        else:
            copy = file.rsplit('/', 1)[0] + '/' + plan.unit_class + '__' + file.rsplit('/', 1)[1]
            link = copy
        text, bad = E.edits_text(stats.trees[file], edits)
        problems += bad
        plan.files.append((PKG + copy[len('gameData/'):],
                           'include "#/develop/gameBase/%s"\n%s' % (file, text)))
        unit_edits.append(E.make_edit(unit, stats.unit_file, ref, link, source='rule:copy'))
    # Невесомая подвеска без ручной правки массы уже подготовлена конструктором подвески.
    text, bad = E.edits_text(unit, unit_edits)
    problems += bad
    extra += text
    return extra, problems


# блок юнита миссии -> папка файла (мишени — стоковая техника игры)
UNIT_FOLDERS = {'tankModels': 'units/tankModels', 'armada': 'flightModels', 'ships': 'units/ships'}


def target_problems(source, mission, allow_shoot=False):
    """Мишени миссии: файл машины есть в игре, мишень армии 2 и не стреляет (dont_aim / hold_fire / cannotShoot)."""
    units = mission.block('units')
    no_shoot = set()
    for trig in mission.block('triggers').blocks:
        for act in (trig.block('actions').blocks if trig.block('actions') else []):
            if act.name == 'unitSetProperties' and act.get('cannotShoot'):
                no_shoot.add(act.get('object'))
    out = []
    for u in units.blocks:
        if u.get('name') == 'player' or u.name not in UNIT_FOLDERS:
            continue
        cls, name = u.get('unit_class'), u.get('name')
        if not source.exists('gameData/%s/%s.blk' % (UNIT_FOLDERS[u.name], (cls or '').lower())):
            out.append('мишень %s: нет машины %s в игре' % (name, cls))
        props = u.block('props')
        if props is None or props.get('army') != 2:
            out.append('мишень %s не армии 2' % name)
        elif not allow_shoot and props.get('attack_type') not in ('dont_aim', 'hold_fire') and name not in no_shoot:
            out.append('мишень %s может стрелять' % name)
    return out


def preset_problems(source, unit, resolved, weapons):
    """Свой пресет копии: файл в наборе; пара slot/preset — вариант этого слота в итоговой копии; файл оружия
    (старая схема) есть в игре."""
    entry = next((p for p in unit.block('weapon_presets').blocks if p.get('name') == weapons), None)
    path = PKG[:-len('gameData/')] + entry.get('blk') if entry is not None and entry.get('blk') else None
    tree = resolved.get(path)
    if tree is None:
        return ['нет файла своего пресета %s в наборе' % weapons]
    ws = unit.block('WeaponSlots')
    slots = {s.get('index'): {p.get('name') for p in s.blocks if p.name == 'WeaponPreset'}
             for s in (ws.blocks if ws else []) if s.name == 'WeaponSlot'}
    out = []
    for w in tree.blocks:
        if w.name == 'Weapon' and w.get('slot') is not None and w.get('preset') not in slots.get(w.get('slot'), ()):
            out.append('пресет %s: в слоте %s нет варианта %s' % (weapons, w.get('slot'), w.get('preset')))
        elif (w.name == 'Weapon' and w.get('blk') and not L.weapon_exists(source, w.get('blk'))
              and PKG[:-len('gameData/')] + L._blk_path(w.get('blk')) not in resolved):
            out.append('пресет %s: нет файла оружия %s' % (weapons, w.get('blk')))
    return out


def verify_plan(source, plan):
    """Проверка набора до записи: пути, разбор каждого BLK, итог копий по модели правок (лог должен быть пуст),
    пресет вооружения, ссылки на пусковые, миссия. Возвращает список ошибок (пусто — можно писать)."""
    if plan.problems and not plan.files:
        return list(plan.problems)
    problems = list(plan.problems) + I.check_paths(plan.files)
    files = dict(plan.files)
    resolved = {}
    for rel, text in plan.files:
        if not rel.endswith('.blk'):
            continue
        try:
            B.parse_text(text)
        except B.TextError as e:
            problems.append('%s: не разбирается: %s' % (rel, e))
            continue
        if rel.startswith(PKG):
            log = []
            try:
                resolved[rel] = B.resolve_file(text, source.loader(), log)
            except FileNotFoundError as e:
                problems.append('%s: нет файла для include: %s' % (rel, e))
                continue
            except (B.ApplyFatal, ValueError) as e:
                problems.append('%s: игра упадёт: %s' % (rel, e))
                continue
            problems += ['%s: %s' % (rel, line) for line in log]
    kind = plan.vehicle['kind']
    folder = KINDS[kind][1]
    if plan.launch == COPY:
        unit = resolved.get('%s%s/%s.blk' % (PKG, folder, plan.unit_class))
        if unit is None and not problems:
            problems.append('нет копии машины в наборе')
    else:
        unit = source.load(plan.vehicle['file'])
    if unit is not None:
        if plan.weapons and plan.weapons not in unit_presets(unit):
            problems.append('нет пресета вооружения %s' % plan.weapons)
        if plan.launch == COPY and plan.weapons.startswith(PREFIX) and plan.loadout is not None:
            pylons = L.read_pylons(source.load(plan.vehicle['file']))
            problems += L.check_resolved(unit, pylons, plan.loadout, plan.weapons, plan.unit_class)
            problems += preset_problems(source, unit, resolved, plan.weapons)
        if plan.launch == COPY:
            for i, cls in support_refs(unit):
                where, _, target = (cls or '').partition('/')
                if not target.startswith(PREFIX) or '%s%s/%s.blk' % (PKG, SUPPORT_FOLDERS.get(where, '?'),
                                                                      target) not in files:
                    problems.append('supportPlanes/plane[%d]: ссылка не на свою копию: %s' % (i, cls))
    text = files.get(plan.mission_path)
    if text is None:
        problems.append('нет миссии ' + plan.mission_path)
    else:
        try:
            m = B.parse_text(text)
        except B.TextError as e:
            problems.append('миссия не разбирается: %s' % e)
        else:
            ms = m.block('mission_settings').block('mission')
            if ms.get('name') != plan.mission:
                problems.append('mission{name} %r не совпадает с файлом %s' % (ms.get('name'), plan.mission))
            if ms.get('level') not in {s[0] for s in SPAWNS.values()} and not (
                    isinstance(plan.scenario, NewScenario) and ms.get('level')):
                problems.append('неизвестная карта %s' % ms.get('level'))
            player = m.block('units').block(KINDS[kind][0])
            if player is None or player.get('name') != 'player' or player.get('unit_class') != plan.unit_class:
                problems.append('в миссии игрок не %s' % plan.unit_class)
            problems += target_problems(source, m, isinstance(plan.scenario, NewScenario))
    return problems
