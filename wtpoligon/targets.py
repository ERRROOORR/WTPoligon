"""Мишени сценария (этап 2): наземные танки-мишени и воздушная цель — юниты, действия и триггеры миссии.

Общие для программы и генератора тестов tools/make_test_missions.py (там — проверенные в игре варианты):
  - танки-мишени — как стоковый тест-драйв testflight_era_tft.blk на firing_range: tankModels армии 2, при старте
    attack_type "dont_aim" (не стреляют), уничтоженную через 5 с восстановить (12-й круг и далее, подтверждено);
  - воздушная цель — как flight_target* в test_flight_unit_template.blk: armada армии 2, cannotShoot, маршрут
    unitSetRoute к точке старта игрока (26-й круг); РЛС бота включается use_search_radar + useSearchRadar (30-й).
Сценарий программы (Scenario) — выбор пользователя: точка появления, набор/дистанция мишеней, воздушная цель.
"""
import math
from dataclasses import asdict, dataclass

from .game import blk as B
from .mission import SPAWNS, _restore, _tm, _trigger

# поворот мишеней стокового тест-драйва (лбом к линии стрельбы)
_TURN = ((-0.906308, 0.0, 0.422618), (0.0, 1.0, 0.0), (-0.422618, 0.0, -0.906308))
# точки мишеней стокового тест-драйва firing_range (640–770 м от точки появления наземки)
TARGET_POINTS = [(2046.37, 216.918, 2337.7), (2095.99, 216.918, 2341.14), (2145.95, 216.918, 2351.48),
                 (2207.38, 216.918, 2350.88), (2221.47, 217.254, 2368.38), (2354.39, 217.627, 2372.95)]
_STOCK_NAMES = ['target_tank01', 'target_tank02', 'target_tank03', 'target_tank04', 'target_tank05',
                'target_tank07']
# TARGET_POINTS — начальные tm юнитов стоковой миссии, но шаблон testflight_template.blk сразу переносит
# target_tankNN в зону tank_spawn_areaNN (unitRespawn в check_exist): в игре мишени стоят там, за речкой по курсу
# игрока (этап 2: по TARGET_POINTS — на нашем берегу слева). Зоны testflight_era_tft.blk (датамайн aa326f1):
# номер -> (ось X зоны — лбом к игроку, точка); TARGET_POINTS остаются у генератора тестов и над полигоном (самолёт)
_AREAS = {
    1: ((-0.993852, 0.0, 0.110723), (1949.84, 217.241, 1784.36)),
    2: ((-0.993852, 0.0, 0.110723), (2122.54, 218.172, 1804.45)),
    3: ((-0.993852, 0.0, 0.110723), (2318.7, 218.097, 1833.45)),
    4: ((-0.993852, 0.0, 0.110723), (2514.1, 218.565, 1868.75)),
    5: ((-0.993852, 0.0, 0.110723), (2905.36, 235.407, 1934.55)),
    6: ((-0.063539, 0.0, 0.997980), (2039.58, 219.45, 1341.87)),
    7: ((-0.355150, 0.0, 0.934810), (2021.45, 229.623, 1053.23)),
}
_AREA_OF = [1, 2, 3, 4, 5, 7]   # зоны _STOCK_NAMES (target_tank06 — ЗСУ, в наборах её нет)
# поворот игрока t1_player01 стокового тест-драйва: вперёд (ось X) — на мишени
PLAYER_TURN = ((0.939692, 0.0, 0.34202), (0.0, 1.0, 0.0), (-0.34202, 0.0, 0.939692))
_ROW_STEP = 40.0   # шаг мишеней в ряду поперёк линии стрельбы при выбранной дистанции, м

# наборы мишеней: ключ -> (название, [unit_class по точкам], проверено в игре)
TARGET_SETS = {
    'soviet': ('Советские танки, как в тест-драйве игры (ИТ-1, Т-62, Т-55А, Т-10М, Т-64А, Т-90А)',
               ['ussr_it_1', 'ussr_t_62', 'ussr_t_55a', 'ussr_t_10m', 'ussr_t_64a_1971', 'ussr_t_90a'], True),
    'nato': ('Танки НАТО (M1 Abrams, Leopard 2A4, M60A3, AMX-30, Leopard 1A5, Centurion Mk 10)',
             ['us_m1_abrams', 'germ_leopard_2a4', 'us_m60a3_tts', 'fr_amx_30', 'germ_leopard_1a5',
              'uk_centurion_mk_10'], False),
    'ww2': ('Танки Второй мировой («Тигр», «Пантера», Pz.IV H, Т-34, КВ-1, «Шерман»)',
            ['germ_pzkpfw_vi_ausf_h1_tiger', 'germ_pzkpfw_v_ausf_d_panther', 'germ_pzkpfw_iv_ausf_h',
             'ussr_t_34_1942', 'ussr_kv_1_l_11', 'us_m4a1_1942_sherman'], False),
    'light': ('Лёгкая бронетехника (БМП-2, БТР-80А, M2A2 Bradley, Marder 1A3)',
              ['ussr_bmp_2', 'ussr_btr_80a', 'us_m2a2', 'germ_marder_1a3'], False),
}
# стоковый набор генератора (TARGETS): имя, класс, tm
TARGETS = [(n, cls, _TURN + (p,)) for n, cls, p in zip(_STOCK_NAMES, TARGET_SETS['soviet'][1], TARGET_POINTS)]

# дистанция до мишеней, м: 0 — как в тест-драйве игры (на полигоне зоны 225–1190 м, над полигоном ~720 м);
# остальные — ряд мишеней поперёк линии стрельбы (высота +2 м — мишень опустится на землю; в игре не проверено)
GROUND_DISTANCES = [0, 300, 1200, 2000]

# воздушные цели: ключ -> (название, unit_class, скорость км/ч, есть РЛС)
AIR_BOTS = {
    'mig15': ('МиГ-15бис — истребитель без РЛС', 'mig-15bis_ns23', 500.0, False),
    'mig23': ('МиГ-23М — истребитель с РЛС (для проверки СПО)', 'mig_23m', 500.0, True),
    'tu4': ('Ту-4 — большой медленный бомбардировщик', 'tu_4', 400.0, False),
}
AIR_DISTANCES = [3000, 10000, 30000]
AIR_MIN_ALT = 500.0   # вертолёт на аэродроме: цель не ниже 500 м, иначе бот врежется в землю

# точки появления по виду техники: ключ SPAWNS -> (название, тип миссии, виды, наземные мишени, воздушная цель)
SPAWN_CHOICES = {
    'firing_range': ('Полигон (firing_range), как тест-драйв наземки', 'testFlight', ('tank',), True, False),
    'air_denmark': ('Дания, в воздухе на 2 км', 'singleMission', ('air',), False, True),
    'firing_range_air': ('Над полигоном, 700 м, к линии танков-мишеней', 'singleMission', ('air',), True, True),
    'denmark_heli_airfield': ('Дания, вертолётная площадка', 'testFlight', ('heli',), False, True),
    'avn_fiji': ('Фиджи, море', 'testFlight', ('ship',), False, False),
}


@dataclass
class Scenario:
    spawn: str
    ground: str = ''              # ключ TARGET_SETS или '' — без наземных мишеней
    ground_distance: int = 0      # см. GROUND_DISTANCES
    air: str = ''                 # ключ AIR_BOTS или '' — без воздушной цели
    air_distance: int = 10000     # м
    air_radar: bool = False       # включить РЛС бота (только если у него есть РЛС)

    @property
    def mtype(self):
        return SPAWN_CHOICES[self.spawn][1]

    def to_dict(self):
        return asdict(self)


def spawns_for(kind):
    return [k for k, v in SPAWN_CHOICES.items() if kind in v[2]]


def default_scenario(kind):
    """По умолчанию: наземка — полигон с советскими танками-мишенями, самолёт — Дания с МиГ-15 в 10 км,
    вертолёт и флот — без мишеней (как проверенные миссии 1–4 этапа 1)."""
    if kind == 'tank':
        return Scenario('firing_range', ground='soviet')
    if kind == 'air':
        return Scenario('air_denmark', air='mig15')
    return Scenario(spawns_for(kind)[0])


def check_scenario(sc, kind):
    """Ошибки выбора (пусто — можно собирать)."""
    if sc.spawn not in SPAWN_CHOICES:
        return ['неизвестная точка появления %s' % sc.spawn]
    _t, _m, kinds, ground_ok, air_ok = SPAWN_CHOICES[sc.spawn]
    out = []
    if kind not in kinds:
        out.append('точка %s не для этого вида техники' % sc.spawn)
    if sc.ground:
        if sc.ground not in TARGET_SETS:
            out.append('неизвестный набор мишеней %s' % sc.ground)
        elif not ground_ok:
            out.append('на этой точке нет места для наземных мишеней')
        if sc.ground_distance not in GROUND_DISTANCES:
            out.append('дистанция мишеней %s м не из списка %s' % (sc.ground_distance, GROUND_DISTANCES))
    if sc.air:
        if sc.air not in AIR_BOTS:
            out.append('неизвестная воздушная цель %s' % sc.air)
        elif not air_ok:
            out.append('на этой точке воздушной цели нет')
        elif sc.air_radar and not AIR_BOTS[sc.air][3]:
            out.append('у %s нет РЛС' % AIR_BOTS[sc.air][0].split(' —')[0])
        if not 1000 <= sc.air_distance <= 60000:
            out.append('дистанция воздушной цели — от 1 до 60 км')
    return out


def unverified(sc):
    """Что в выбранном сценарии ещё не проверено в игре (пометка 📄 в окне и в сводке)."""
    out = []
    if sc.ground and not TARGET_SETS.get(sc.ground, ('', [], True))[2]:
        out.append('набор мишеней «%s»' % TARGET_SETS[sc.ground][0].split(' (')[0])
    if sc.ground and sc.ground_distance:
        out.append('мишени на дистанции %d м (проверена только дистанция тест-драйва)' % sc.ground_distance)
    if sc.ground and sc.spawn == 'firing_range_air' and sc.air:
        out.append('наземные мишени и воздушная цель вместе')
    if sc.air:
        if sc.air == 'tu4':
            out.append('воздушная цель Ту-4')
        out.append('возрождение воздушной цели после гибели')
        if sc.spawn != 'air_denmark':
            out.append('воздушная цель на этой точке появления')
    return out


def _turn_to(dx, dz):
    """Поворот юнита: ось X (вперёд) — по горизонтали (dx, dz), ось Z — как у стоковых tm."""
    d = math.hypot(dx, dz)
    a, b = round(dx / d, 6), round(dz / d, 6)
    return ((a, 0.0, b), (0.0, 1.0, 0.0), (-b, 0.0, a))


def ground_targets(set_key, distance=0, spawn='firing_range'):
    """[(имя, unit_class, tm)] набора. На полигоне — зоны tank_spawn_area стокового тест-драйва, при distance —
    ряд поперёк линии стрельбы игрока в distance м перед ним (высота — по зонам тест-драйва + 2 м). В других
    местах — TARGET_POINTS, при distance — сдвиг всей линии вдоль направления от точки появления к центру мишеней
    (центр оказывается в distance м по горизонтали)."""
    classes = TARGET_SETS[set_key][1]
    if spawn == 'firing_range':
        if not distance:
            return [(n, cls, _turn_to(_AREAS[a][0][0], _AREAS[a][0][2]) + (_AREAS[a][1],))
                    for n, cls, a in zip(_STOCK_NAMES, classes, _AREA_OF)]
        px, _py, pz = SPAWNS[spawn][1]
        fx, fz = PLAYER_TURN[0][0], PLAYER_TURN[0][2]
        # высота земли по зонам 01–05 (по курсу): ближайшая по глубине, дальше последней — как у последней
        depth = sorted(((_AREAS[a][1][0] - px) * fx + (_AREAS[a][1][2] - pz) * fz, _AREAS[a][1][1])
                       for a in range(1, 6))
        y = min(depth, key=lambda dy: abs(dy[0] - distance))[1] + 2.0
        out = []
        for i, (n, cls) in enumerate(zip(_STOCK_NAMES, classes)):
            side = (i - (len(classes) - 1) / 2.0) * _ROW_STEP
            pos = (round(px + fx * distance - fz * side, 2), y, round(pz + fz * distance + fx * side, 2))
            out.append((n, cls, _turn_to(-fx, -fz) + (pos,)))
        return out
    points = TARGET_POINTS[:len(classes)]
    if distance:
        player = SPAWNS[spawn][1]
        cx = sum(p[0] for p in points) / len(points)
        cz = sum(p[2] for p in points) / len(points)
        dx, dz = cx - player[0], cz - player[2]
        d = math.hypot(dx, dz)
        shift = distance - d
        points = [(round(p[0] + dx / d * shift, 2), p[1] + 2.0, round(p[2] + dz / d * shift, 2)) for p in points]
    return [(n, cls, _TURN + (p,)) for n, cls, p in zip(_STOCK_NAMES, classes, points)]


def ground_parts(targets):
    """(юниты, действия init, триггеры) танков-мишеней [(имя, unit_class, tm)]."""
    names = [t[0] for t in targets]
    units = [B.Block('tankModels', [
        ('name', 't', n), ('tm', 'm', tm), ('unit_class', 't', cls), ('objLayer', 'i', 1),
        ('closed_waypoints', 'b', False), ('isShipSpline', 'b', False), ('shipTurnRadius', 'r', 100.0),
        ('weapons', 't', '')] + [('bullets%d' % i, 't', '') for i in range(4)]
        + [('bulletsCount%d' % i, 'i', 100 if i == 0 else 0) for i in range(4)]
        + [('crewSkillK', 'r', 0.0), ('applyAllMods', 'b', False)],
        [B.Block('props', [('army', 'i', 2), ('count', 'i', 1), ('formation_type', 't', 'rows'),
                           ('formation_div', 'i', 3), ('formation_step', 'p2', (2.5, 2.0)),
                           ('formation_noise', 'p2', (0.1, 0.1)), ('uniqueName', 't', ''),
                           ('attack_type', 't', 'dont_aim')]),
         B.Block('way')]) for n, cls, tm in targets]
    # как check_exist шаблона: не целиться, видны на карте; уничтоженную мишень через 5 с — восстановить
    no_aim = [B.Block('unitSetProperties', [('object', 't', n), ('forceVisibleOnMap', 'b', True),
                                            ('attack_type', 't', 'dont_aim')]) for n in names]
    killed = B.Block('unitWhenStatus', [
        ('object_type', 't', 'isKilled'), ('check_objects', 't', 'any'), ('object_marking', 'i', 0),
        ('object_var_name', 't', ''), ('object_var_comp_op', 't', 'equal'), ('object_var_value', 'i', 0),
        ('target_type', 't', 'isAlive'), ('check_period', 'r', 1.0)] + [('object', 't', n) for n in names])
    trigger = _trigger('targets_restore', True, [B.Block('periodicEvent', [('time', 'r', 1.0)])],
                       [killed], [B.Block('wait', [('time', 'r', 5.0)])]
                       + [_restore(n, True) for n in names] + no_aim, True)
    return units, list(no_aim), [trigger]


def air_parts(name, unit_class, start, end, speed, radar=False, respawn=False):
    """(юниты, действия init, триггеры, маршруты) воздушной цели: стоит в start носом к end (-X), летит к end.
    respawn — после гибели через 5 с восстановить и снова пустить по маршруту с начала (в игре не проверено)."""
    route = name + '_way'
    unit = B.Block('armada', [
        ('name', 't', name), ('tm', 'm', ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0), start)),
        ('unit_class', 't', unit_class), ('objLayer', 'i', 1), ('closed_waypoints', 'b', False),
        ('isShipSpline', 'b', False), ('shipTurnRadius', 'r', 100.0), ('weapons', 't', '')]
        + [('bullets%d' % i, 't', '') for i in range(4)] + [('bulletsCount%d' % i, 'i', 0) for i in range(4)]
        + [('crewSkillK', 'r', 0.0), ('applyAllMods', 'b', False)],
        [B.Block('props', [('army', 'i', 2), ('count', 'i', 1), ('free_distance', 'r', 70.0),
                           ('floating_distance', 'r', 50.0), ('minimum_distance_to_earth', 'r', 20.0),
                           ('altLimit', 'r', 16000.0),
                           # 30-й круг: РЛС включена, как бот F-15C в aircraft_countermeasures_chaff_sky.blk
                           ('attack_type', 't', 'fire_at_will' if radar else 'dont_aim'),
                           ('skill', 'i', 4)] + ([('use_search_radar', 'b', True)] if radar else [])
                 + [('speed', 'r', speed)],
                 [B.Block('plane', [('wing_formation', 't', 'Diamond'), ('row_distances', 'r', 3.0),
                                    ('col_distances', 'r', 3.0), ('super_formation', 't', 'Diamond'),
                                    ('super_row_distances', 'r', 1.5), ('super_col_distances', 'r', 1.5),
                                    ('ai_skill', 't', 'NORMAL'), ('task', 't', 'FLY_WAYPOINT')])]),
         B.Block('way')])
    wp = [B.Block('%s_wp_%02d' % (route, i), [('type', 't', 'normal'), ('tm', 'm', _tm(p))],
                  [B.Block('props', [('speed', 'r', speed), ('moveType', 't', 'MOVETO_STRAIGHT'),
                                     ('tas', 'b', False), ('canUsePathFinder', 'b', False)])])
          for i, p in enumerate((start, end), 1)]
    way = B.Block(route, [('closed_waypoints', 'b', False), ('isShipSpline', 'b', False),
                          ('shipTurnRadius', 'r', 100.0), ('dontOverrideHeight', 'b', True)],
                  [B.Block('way', blocks=wp)])

    def go(teleport):
        # как spawn_plane в test_flight_template.blk: не стреляет, летит по маршруту, отмечена на экране
        return [B.Block('unitSetProperties', [('object', 't', name), ('cannotShoot', 'b', True)]
                        + ([('useSearchRadar', 'b', True)] if radar else [])),
                B.Block('unitSetRoute', [('route', 't', route), ('object_var_name', 't', ''),
                                         ('object_var_comp_op', 't', 'equal'), ('teleportToStart', 'b', teleport),
                                         ('object', 't', name)]),
                B.Block('unitSetIndication', [('set', 'b', True), ('target', 't', name)])]
    triggers = []
    if respawn:
        killed = B.Block('unitWhenStatus', [
            ('object_type', 't', 'isKilled'), ('check_objects', 't', 'any'), ('object_marking', 'i', 0),
            ('object_var_name', 't', ''), ('object_var_comp_op', 't', 'equal'), ('object_var_value', 'i', 0),
            ('target_type', 't', 'isAlive'), ('check_period', 'r', 1.0), ('object', 't', name)])
        triggers.append(_trigger(name + '_restore', True, [B.Block('periodicEvent', [('time', 'r', 1.0)])],
                                 [killed], [B.Block('wait', [('time', 'r', 5.0)]), _restore(name, True)] + go(True),
                                 True))
    return [unit], go(False), triggers, [way]


def scenario_parts(sc):
    """Части миссии по сценарию: dict(extra_units, init_actions, extra_triggers, way_points, player_turn)."""
    units, init, triggers, ways = [], [], [], []
    if sc.ground:
        u, a, t = ground_parts(ground_targets(sc.ground, sc.ground_distance, sc.spawn))
        units += u
        init += a
        triggers += t
    if sc.air:
        _title, cls, speed, has_radar = AIR_BOTS[sc.air]
        pos = SPAWNS[sc.spawn][1]
        alt = max(pos[1], AIR_MIN_ALT)
        u, a, t, w = air_parts('air_target', cls, (pos[0] + sc.air_distance, alt, pos[2]), (pos[0], alt, pos[2]),
                               speed, radar=sc.air_radar and has_radar, respawn=True)
        units += u
        init += a
        triggers += t
        ways += w
    # на полигоне игрок — лицом к мишеням, как t1_player01 тест-драйва
    turn = PLAYER_TURN if sc.spawn == 'firing_range' else None
    return dict(extra_units=units, init_actions=init, extra_triggers=triggers, way_points=ways, player_turn=turn)


def target_classes(sc):
    """[(блок миссии, unit_class)] мишеней сценария — для проверки, что файлы есть в игре."""
    out = [('tankModels', c) for c in (TARGET_SETS[sc.ground][1] if sc.ground in TARGET_SETS else [])]
    if sc.air in AIR_BOTS:
        out.append(('armada', AIR_BOTS[sc.air][1]))
    return out


def describe(sc):
    """Строки сводки простым языком."""
    lines = ['Место: ' + SPAWN_CHOICES[sc.spawn][0]]
    if sc.ground:
        lines.append('Наземные мишени: %s; %s. Не стреляют, через 5 с после уничтожения возрождаются.' % (
            TARGET_SETS[sc.ground][0],
            ('дистанция как в тест-драйве (225–1190 м, за речкой по курсу)' if sc.spawn == 'firing_range' else
             'дистанция как в тест-драйве (~720 м)') if not sc.ground_distance else
            'дистанция ~%d м' % sc.ground_distance))
    if sc.air:
        lines.append('Воздушная цель: %s, в %g км навстречу%s. Не стреляет, после гибели через 5 с появляется '
                     'снова.' % (AIR_BOTS[sc.air][0].split(' —')[0], sc.air_distance / 1000.0,
                                 ', РЛС включена' if sc.air_radar else ''))
    if not sc.ground and not sc.air:
        lines.append('Мишеней нет.')
    return lines
