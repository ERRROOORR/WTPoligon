"""Сборка (docs/architecture.md §3): машина + способ запуска -> набор файлов (путь от папки игры -> текст).
Чистая функция: на диск не пишет (это install). Проверка набора — verify_plan (модель правок = лог игры).

Этап 1 — стоковая миссия (ТЗ §6.1: пока правок нет, в игру идёт стоковая машина). Способ запуска (launch.md §8):
  - машина из ангара — под настоящим именем, файлов машины нет, только миссия (полноценна);
  - не из ангара — копия wtp5_<имя> = include стокового файла + перенос модификаций-блоков (дымы, тепловизор ) + копии пусковых составного ЗРК; ездит и стреляет, но неполноценна.
"""
import re
from dataclasses import dataclass, field

from . import install as I
from . import loadout as L
from . import edits as E
from . import targets as T
from .scenarios.model import Scenario as NewScenario
from .scenarios import build as SB, validate as SV
from .scenarios.catalog import CATEGORIES as SCENARIO_CATEGORIES
from .ammo import build as AB
from .support import build as SUPB, validate as SUPV
from .support.model import stock as stock_support
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
NOTE_HELI = 'Вертолёт-копия получает самолётный интерфейс.'
NOTE_LOADOUT = ('Подвеска изменена, поэтому в миссии будет копия этого самолёта (%s): свой набор оружия игра '
                'принимает только у копии. Летает и стреляет так же; в интерфейсе вместо названия — '
                'внутреннее имя, часть модификаций не работает. Штатный пресет без изменений едет на машине из '
                'ангара.')
NOTE_SAM = 'Пусковые ЗРК — тоже копии (%d шт.): кнопки вызова в интерфейсе нет, клавиша вызова работает.'
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
    support: object = None
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


def mission_name(name):
    """Имя миссии: игра принимает только [a-z0-9_] — «invalid symbol in name: 'wtp5_fau-1'» (дефис у 510 машин)."""
    return PREFIX + re.sub(r'[^a-z0-9_]', '_', name.lower())


def default_preset(unit, name, kind):
    """Пресет вооружения по умолчанию: <имя>_default, иначе первый с 'default' в имени, иначе первый.
    Корабль — пусто, как в проверенной миссии 4."""
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


def fm_file(unit, name):
    """Лётная модель самолёта: fmFile, а если его нет — игра берёт fm/<имя машины>.blk (141 машина, V-1)."""
    return (unit.get('fmFile') if unit is not None else None) or 'fm/%s.blk' % name


BOMB_PLANE_FIELDS = ('bombPlaneName', 'haveBombPlaneSight', 'bombPlaneEjectionVel')
NOTE_BOMB_PLANE = 'Самолёт-бомба (как у Mistel): %s.'
NOTE_BOMB_NUKE = '📄 Ядерная боевая часть самолёта-бомбы: урон ядерный, взрыв выглядит обычным.'
_BOMB_DONORS = {}   # подпись игры -> {оружие-отцепка: штатный носитель} (поиск по всем самолётам — один раз)
BOMB_PLANE_COPY_FIELDS = ('cantBeBackModel', 'hookNode', 'bombPlane', 'changeToExplodedOnExplode',
                          'droppedYawPitchHoldRate', 'droppedYawPitchHoldIntegralRate', 'droppedRollHoldMult',
                          'bombPlaneDropAnimSpeed')


def _blk_refs(text):
    """Пути .blk из текста BLK (в т.ч. include "#/develop/gameBase/…")."""
    return {m.split('#/develop/gameBase/')[-1] for m in re.findall(r'"([^"]+\.blk)"', text)}


def _blk_value(name, value):
    if isinstance(value, bool):
        return '%s:b=%s\n' % (name, 'yes' if value else 'no')
    if isinstance(value, (tuple, list)):
        return '%s:p%d=%s\n' % (name, len(value), ', '.join(repr(float(x)) for x in value))
    if isinstance(value, float):
        return '%s:r=%r\n' % (name, value)
    if isinstance(value, int):
        return '%s:i=%d\n' % (name, value)
    return '%s:t=%s\n' % (name, B.quote(str(value)))


LEVELS_DIR = 'content/pkg_local/levels/'
LEVEL_EDGE = 65536.0   # граница своей копии уровня (как у воздушных карт игры и Ask3lad)


def _set_param(block, key, typ, value):
    for i, (k, _t, _v) in enumerate(block.params):
        if k == key:
            block.params[i] = (k, typ, value)
            return True
    return False


import functools


@functools.lru_cache(maxsize=4)
def _relief(path, _mtime):
    """Рельеф уровня (10–45 МБ) — один раз на процесс (check-all собирает тысячи миссий на одной карте)."""
    with open(path, 'rb') as stream:
        return stream.read()


def level_copy(source, text):
    """Без зоны возврата: если граница уровня миссии уже ±LEVEL_EDGE — своя копия уровня с расширенными
    mapCoord/aiMapCoord (рельеф .bin — побайтно, BLK — писателем программы: имена со «*» в кавычках, иначе игра
    не читает уровень). -> (новый текст миссии, [(путь, содержимое)]) или (text, [])."""
    import copy as _copy
    import os
    m = re.search(r'level:t="levels/([^"/]+)\.bin"', text)
    if not m or m.group(1).startswith(PREFIX) or getattr(source, 'kind', '') != 'game':
        return text, []
    stem = m.group(1)
    tree = source.load('levels/%s.blk' % stem)
    relief = os.path.join(source.root, 'levels', stem + '.bin')
    c0, c1 = (tree.get('mapCoord0'), tree.get('mapCoord1')) if tree is not None else (None, None)
    if not c0 or not c1 or not os.path.isfile(relief):
        return text, []
    if min(c0) <= -LEVEL_EDGE and max(c1) >= LEVEL_EDGE:
        return text, []
    tree = _copy.deepcopy(tree)
    for key, value in (('mapCoord0', (-LEVEL_EDGE, -LEVEL_EDGE)), ('mapCoord1', (LEVEL_EDGE, LEVEL_EDGE)),
                       ('aiMapCoord0', (-LEVEL_EDGE, -LEVEL_EDGE)), ('aiMapCoord1', (LEVEL_EDGE, LEVEL_EDGE))):
        _set_param(tree, key, 'p2', value)
    name = PREFIX + stem
    data = _relief(relief, os.path.getmtime(relief))
    return (text.replace('levels/%s.bin' % stem, 'levels/%s.bin' % name),
            [(LEVELS_DIR + name + '.blk', '// WT Poligon 5: %s без зоны возврата\n%s' % (stem, B.to_text(tree))),
             (LEVELS_DIR + name + '.bin', data)])


def bomb_plane_copy(source, stock_name, bp, copy_name):
    """Копия самолёта-бомбы: другой самолёт снизу
    и/или своя боевая часть.
    -> (путь, текст) или None, если всё штатное."""
    vehicle = (bp or {}).get('vehicle') or ''
    mass = (bp or {}).get('explosive_mass')
    kt = (bp or {}).get('nuclear_kt')
    if not vehicle and mass is None and not kt:
        return None
    stock = source.load('gameData/flightModels/%s.blk' % stock_name)
    if stock is None or stock.block('warhead') is None:
        raise ValueError('нет штатного самолёта-бомбы ' + stock_name)
    import copy as _copy
    warhead = _copy.deepcopy(stock.block('warhead'))
    if kt:
        warhead.params = [(k, t, v) for k, t, v in warhead.params if k not in ('yield', 'explosiveType', 'explosiveMass')]
        warhead.params += [('yield', 'r', float(kt)), ('explosiveType', 't', 'tnt'), ('explosiveMass', 'r', 20000.0)]
        if warhead.block('pressureDamage') is None:
            warhead.blocks.append(B.Block('pressureDamage', [('damageType', 't', 'pressure')]))
    elif mass is not None:
        warhead.params = [(k, t, float(mass) if k == 'explosiveMass' else v) for k, t, v in warhead.params]
    base = vehicle or stock_name
    head = '// WT Poligon 5: самолёт-бомба из %s\n' % base
    if vehicle:
        unit = source.load('gameData/flightModels/%s.blk' % vehicle)
        if unit is None:
            raise ValueError('нет самолёта ' + vehicle)
        fuse = stock.get('warheadFusePart') or 'fuse_dm'
        if fuse not in B.to_text(unit):
            fuse = 'fuse_dm'
        text = (head + 'include "#/develop/gameBase/gameData/flightModels/%s.blk"\n' % vehicle
                + 'fmFile:t=%s\n' % B.quote(fm_file(unit, vehicle))
                + ''.join(_blk_value(f, stock.get(f)) for f in BOMB_PLANE_COPY_FIELDS if stock.get(f) is not None)
                + B.to_text(B.Block('root', blocks=[warhead])) + 'warheadFusePart:t=%s\n' % B.quote(fuse))
    else:
        tree = _copy.deepcopy(stock)
        tree.blocks = [warhead if b.name == 'warhead' else b for b in tree.blocks]
        if not tree.get('fmFile'):
            tree.params.insert(0, ('fmFile', 't', fm_file(stock, stock_name)))
        text = head + B.to_text(tree)
    return PKG + 'flightModels/%s.blk' % copy_name, text


def bomb_plane_text(source, vehicles, unit, texts):
    """Mistel: Ju 88 — отдельный самолёт bombPlaneName у носителя, «бомба» с releasesBombPlane его только отцепляет.
    Если такое оружие висит на другом самолёте, перенести в копию поля связки от штатного носителя.
    -> (текст для копии, имя самолёта-«бомбы» или '')."""
    if unit.get('bombPlaneName'):
        return '', ''
    released = set()
    for path in set().union(*(_blk_refs(t) for t in texts)) if texts else ():
        tree = source.load(path)
        if tree is not None and tree.get('releasesBombPlane'):
            released.add(path.lower())
    if not released:
        return '', ''
    try:
        sig = source.signature()
    except Exception:  # noqa: BLE001 — источник без подписи: без кэша
        sig = None
    donors = _BOMB_DONORS.get(sig) if sig else None
    if donors is None:
        donors = {}
        for v in vehicles or ():
            if v['kind'] != 'air':
                continue
            unit_ = source.load(v['file'])
            if unit_ is None or not unit_.get('bombPlaneName'):
                continue
            presets = unit_.block('weapon_presets')
            for p in (presets.blocks if presets else []):
                tree = source.load(p.get('blk') or '')
                for r in (_blk_refs(B.to_text(tree)) if tree is not None else ()):
                    donors.setdefault(r.lower(), v['file'])
        if sig and vehicles:
            _BOMB_DONORS[sig] = donors
    for file in dict.fromkeys(donors[r] for r in released if r in donors):
        donor = source.load(file)
        if donor is not None:
            out = []
            for field in BOMB_PLANE_FIELDS:
                value = donor.get(field)
                if value is None:
                    continue
                if isinstance(value, bool):
                    out.append('%s:b=%s\n' % (field, 'yes' if value else 'no'))
                elif isinstance(value, (tuple, list)):
                    out.append('%s:p%d=%s\n' % (field, len(value), ', '.join(repr(float(x)) for x in value)))
                else:
                    out.append('%s:t=%s\n' % (field, B.quote(str(value))))
            return ''.join(out), donor.get('bombPlaneName')
    return '', ''


def copy_file_text(folder, base, name, extra='', source=None):
    """Копия машины. У самолёта без fmFile копия искала бы fm/<имя копии>.blk — пишем ЛМ оригинала явно."""
    if folder.lower() == 'flightmodels' and source is not None:
        unit = source.load('gameData/flightModels/%s.blk' % base)
        if unit is not None and not unit.get('fmFile'):
            extra = 'fmFile:t=%s\n' % B.quote(fm_file(unit, base)) + extra
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
               vehicles=None, ammo=None, support=None, support_library=(), copy_class=None,
               support_air_default=False):
    """План миссии для машины индекса. in_hangar — запуск под настоящим именем; scenario — место и мишени
    (по умолчанию — targets.default_scenario вида техники); loadout — подвеска самолёта/вертолёта (loadout.py):
    штатный пресет без изменений — как есть, своя подвеска — копия машины; catalog — каталог оружия
    (триггер и количество чужого оружия)."""
    name, kind = vehicle['name'], vehicle['kind']
    sc = scenario or T.default_scenario(kind)
    plan = Plan(vehicle, HANGAR if in_hangar else COPY, mission=mission_name(name), scenario=sc, loadout=loadout,
                ammo=ammo, support=support)
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
    if support is not None:
        plan.problems += SUPV.check(support, vehicles or (), support_library)
        if plan.problems:
            return plan
    support_changed = support is not None and support != stock_support(unit)
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
                             ammo.nuclear or (ammo.stock_capacity and ammo.capacity != ammo.stock_capacity)) and in_hangar:
        in_hangar = False
        plan.launch = COPY
        plan.notes.append('Боеприпасы изменены: используется копия машины %s.' % copy_name(name))
    if support_changed and in_hangar:
        in_hangar = False
        plan.launch = COPY
    mods = [m.name for m in (unit.block('modifications').blocks if unit.block('modifications') else [])]
    folder = KINDS[kind][1]
    if in_hangar:
        plan.unit_class = name
        plan.notes.append(NOTE_HANGAR)
    else:
        base = name.lower()
        plan.unit_class = copy_class or copy_name(name)
        if not plan.notes:          # вынужденная копия (своя подвеска) уже объяснена NOTE_LOADOUT
            plan.notes.append(NOTE_COPY % plan.unit_class)
        extra = ''
        refs = support_refs(unit)
        if refs and not support_changed:
            new = {}
            for i, cls in refs:
                where, _, target = (cls or '').partition('/')
                if where not in SUPPORT_FOLDERS or not target:
                    plan.problems.append('supportPlanes: неизвестная ссылка %r' % cls)
                    continue
                lname = '%s__%s' % (plan.unit_class, target.lower())
                new[i] = '%s/%s' % (where, lname)
                lfolder = SUPPORT_FOLDERS[where]
                text = copy_file_text(lfolder, target.lower(), name, source=source)
                path = '%s%s/%s.blk' % (PKG, lfolder, lname)
                if path not in dict(plan.files):
                    plan.files.append((path, text))
            extra += support_overrides(new)
            plan.notes.append(NOTE_SAM % len(dict(plan.files)))
        if support_changed:
            classes = {}
            saved = {x['id']: x for x in support_library}
            by_name = {v['name']: v for v in (vehicles or ())}
            for entry in support.entries:
                if not entry.library_id or entry.library_id in classes:
                    continue
                item = saved[entry.library_id]
                target = by_name.get(item['vehicle'])
                if target is None:
                    plan.problems.append('нет исходной машины своей техники ' + item['name'])
                    continue
                from .ammo.model import Ammo
                from .stats import Stats
                own_lo = L.Loadout.from_dict(item['loadout']) if item.get('loadout') else None
                own_ammo = Ammo.from_dict(item['ammo']) if item.get('ammo') else None
                own_stats = None
                if item.get('stats'):
                    own_stats = Stats(source, target, own_lo)
                    own_stats.values = {(f, p): value for f, p, value in item['stats'].get('values', [])}
                    own_stats.title = item['stats'].get('title', '')
                cls = PREFIX + entry.library_id
                nested = stock_plan(source, target, False, gmods=gmods, loadout=own_lo, catalog=catalog,
                                    stats=own_stats, vehicles=vehicles, ammo=own_ammo, copy_class=cls,
                                    support_air_default=entry.kind == 'air')
                plan.problems += nested.problems
                plan.files += [(p, t) for p, t in nested.files if p.startswith('content/pkg_local/')]
                classes[entry.library_id] = cls
            if not plan.problems:
                extra += SUPB.patch(support, vehicles or (), classes, unit)
        if kind == 'heli':
            plan.notes.append(NOTE_HELI)
        gm = gmods if gmods is not None else global_mods(source)
        extra += M.bake_text(unit, gm)
        if custom is not None:
            lfiles, ltext, plan.weapons, lprob = L.build_files(source, custom, loadout, plan.unit_class, catalog)
            plan.problems += lprob
            plan.files += lfiles
            extra += ltext
            bp_text, bp_name = bomb_plane_text(source, vehicles, unit, [t for _, t in lfiles] + [ltext])
            if bp_text:
                own = None
                try:
                    own = bomb_plane_copy(source, bp_name, loadout.bomb_plane, plan.unit_class + '_bombplane')
                except ValueError as exc:
                    plan.problems.append(str(exc))
                if own:
                    plan.files.append(own)
                    bp_text = re.sub(r'bombPlaneName:t=[^\n]*', lambda _m: 'bombPlaneName:t=%s' % B.quote(
                        plan.unit_class + '_bombplane'), bp_text)
                extra += bp_text
                shown = (loadout.bomb_plane or {}).get('vehicle') or bp_name
                tv = next((x for x in (vehicles or ()) if x['name'] == shown), None)
                plan.notes.append(NOTE_BOMB_PLANE % ((tv.get('ru') or tv.get('en') or shown) if tv else shown))
                if (loadout.bomb_plane or {}).get('nuclear_kt'):
                    plan.notes.append(NOTE_BOMB_NUKE)
            if support_air_default:
                presets = unit.block('weapon_presets')
                rows = [p for p in (presets.blocks if presets else []) if p.name == 'preset']
                default = default_preset(unit, name, kind)
                index = next((i for i, p in enumerate(rows, 1) if p.get('name') == default), None)
                own_preset = next((p[len('content/pkg_local/'):] for p, _ in lfiles
                                   if p.endswith('_loadout.blk') and 'weaponPresets/' in p), None)
                if index is None or own_preset is None:
                    plan.problems.append('не найден штатный или свой пресет вызываемого самолёта')
                else:
                    extra += ('"@override:weapon_presets"{\n'
                              '  "@override:preset[%d]"{\n    "@override:blk":t=%s\n  }\n}\n'
                              % (index, B.quote(own_preset)))
                if not loadout.weightless:
                    fm = fm_file(unit, name)
                    if not fm:
                        plan.problems.append('у вызываемого самолёта нет fmFile')
                    else:
                        fm_copy = 'fm/%s.blk' % plan.unit_class
                        plan.files.append((PKG + 'flightModels/' + fm_copy,
                                           '// WT Poligon 5: ЛМ вызываемого самолёта со своей подвеской\n'
                                           'include "#/develop/gameBase/gameData/flightModels/%s"\n' % fm))
                        extra += '"@override:fmFile":t=%s\n' % B.quote(fm_copy)
            sm = L.summarize(source, custom, loadout, catalog)
            plan.notes += ['⚠ ' + t for lvl, t in sm.warnings if lvl == 'danger']
            plan.notes += [t for lvl, t in sm.warnings if lvl in ('warn', 'info')]
            plan.notes += ['📄 ' + t for lvl, t in sm.warnings if lvl == 'untested']
        shared_gun = ''
        shared_edits = []
        if stats is not None and stats.changed():
            if ammo is not None and (ammo.gun or ammo.added or ammo.edits or ammo.air_guns or ammo.nuclear or
                                     (ammo.stock_capacity and ammo.capacity != ammo.stock_capacity)):
                from .ammo.catalog import gun_paths, shells_in
                guns = gun_paths(unit, kind, source, plan.weapons)
                shared_gun = ammo.gun or next((p for _, p, _ in guns if shells_in(source, p)), '')
                shared_edits = [e for e in stats.edits() if L.weapon_key(e.file) == L.weapon_key(shared_gun)]
            extra, problems = stats_files(source, stats, plan, extra, loadout, custom, catalog,
                                          exclude_files={e.file for e in shared_edits})
            plan.problems += problems
            plan.notes += [e.note + ': %s → %s' % (e.stock, e.value) for e in stats.edits()]
        if ammo is not None and ammo.changed():
            own_presets = ([(p, t) for p, t in plan.files if 'weaponpresets/' in p.lower()]
                           if custom is not None else None)
            afiles, atext, _bullets, aproblems = AB.build_files(source, unit, kind, plan.weapons, ammo,
                                                               plan.unit_class, shared_edits,
                                                               custom_presets=own_presets)
            replaced = dict(afiles)
            plan.files = [(p, replaced.pop(p)) if p in replaced else (p, t) for p, t in plan.files]
            afiles = list(replaced.items())
            plan.files += afiles
            extra += atext
            plan.problems += aproblems
        lost = M.lost_equipment(unit, gm)
        if lost:
            plan.notes.append('Не перенесутся в копию (только параметры, у копии не работают): ' + ', '.join(lost))
        plan.files.append(('%s%s/%s.blk' % (PKG, folder, plan.unit_class),
                           copy_file_text(folder, base, name, extra, source=source)))
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
    path, text = plan.files[-1]
    text, level_files = level_copy(source, text)
    plan.files[-1] = (path, text)
    plan.files += level_files
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


def stats_files(source, stats, plan, extra, loadout, pylons, catalog, exclude_files=()):
    """Копии ЛМ/сенсоров и правки машины. Каждая ссылка ведёт только на свою копию файла."""
    problems = []
    unit = stats.trees[stats.unit_file]
    by_file = E.by_file(stats.edits())
    unit_edits = by_file.pop(stats.unit_file, [])
    for file, edits in by_file.items():
        weapon_links = stats.weapon_refs.get(file, [])
        ref = stats.refs.get(file) or (weapon_links[0] + '/blk' if weapon_links else '')
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
        if file not in exclude_files:
            text, bad = E.edits_text(stats.trees[file], edits)
            problems += bad
            plan.files.append((PKG + copy[len('gameData/'):],
                               'include "#/develop/gameBase/%s"\n%s' % (file, text)))
            for reference in ([prefix + '/blk' for prefix in weapon_links] if weapon_links else [ref]):
                unit_edits.append(E.make_edit(unit, stats.unit_file, reference, link, source='rule:copy'))
        for prefix in weapon_links:
            shot = prefix + '/shotFreq'
            frequency = next((e.value for e in edits if e.path == 'shotFreq'), None)
            if frequency is not None and E.stock_param(unit, shot) is not None:
                unit_edits.append(E.make_edit(unit, stats.unit_file, shot, frequency,
                                              source='rule:reload'))
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
            problems += L.check_resolved(unit, pylons, plan.loadout, plan.weapons, plan.unit_class, source)
            problems += preset_problems(source, unit, resolved, plan.weapons)
        if plan.launch == COPY:
            for i, cls in support_refs(unit):
                where, _, target = (cls or '').partition('/')
                if plan.support is not None and plan.support != stock_support(source.load(plan.vehicle['file'])):
                    if where != 'tankModels' or not (source.load('gameData/units/tankModels/%s.blk' % target)
                                                     or '%sunits/tankModels/%s.blk' % (PKG, target) in files):
                        problems.append('supportPlanes/plane[%d]: нет машины %s' % (i, cls))
                elif not target.startswith(PREFIX) or '%s%s/%s.blk' % (PKG, SUPPORT_FOLDERS.get(where, '?'),
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
            if not re.fullmatch(r'[A-Za-z0-9_]+', ms.get('name') or ''):
                problems.append('недопустимое для игры имя миссии %r (только латиница, цифры, _)' % ms.get('name'))
            own_level = (ms.get('level') or '').startswith('levels/' + PREFIX)
            if own_level and LEVELS_DIR + ms.get('level')[len('levels/'):] not in dict(plan.files):
                problems.append('нет своей копии уровня %s' % ms.get('level'))
            if not own_level and ms.get('level') not in {s[0] for s in SPAWNS.values()} and not (
                    isinstance(plan.scenario, NewScenario) and ms.get('level')):
                problems.append('неизвестная карта %s' % ms.get('level'))
            player = m.block('units').block(KINDS[kind][0])
            if player is None or player.get('name') != 'player' or player.get('unit_class') != plan.unit_class:
                problems.append('в миссии игрок не %s' % plan.unit_class)
            problems += target_problems(source, m, isinstance(plan.scenario, NewScenario))
    return problems
