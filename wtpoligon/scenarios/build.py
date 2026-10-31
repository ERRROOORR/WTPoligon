"""Преобразование сценария в части BLK миссии. Источники полей указаны рядом с опциями."""
import math

from ..game import blk as B
from ..mission import SPAWNS, _restore, _tm, _trigger
from .. import targets as T
from .catalog import CATEGORIES

# Источник: исходники/missions.py AIR_MAPS; level и точка старта читаются из миссии тест-драйва игры.
AIR_MAPS = {
    'tunisia': 'gamedata/missions/training/testflight/aircraft/test_flight_universal_tunisia.blk',
    'israel': 'gamedata/missions/training/testflight/aircraft/test_flight_universal_israel.blk',
    'denmark': 'gamedata/missions/training/testflight/aircraft/test_flight_universal_denmark.blk',
    'equatorial_island': 'gamedata/missions/training/testflight/aircraft/test_flight_universal_equatorial_island.blk',
    'afghan': 'gamedata/missions/training/testflight/aircraft/test_flight_universal_afghan.blk',
    'ladoga': 'gamedata/missions/training/testflight/aircraft/test_flight_universal_ladoga.blk',
}
TIMES = {'День': 'Day', 'Рассвет': 'Dawn', 'Закат': 'Dusk', 'Ночь': 'Night'}
WEATHER = {'Ясно': 'clear', 'Облачно': 'cloudy', 'Дождь': 'rain', 'Снег': 'blind'}
DIFFICULTIES = {'Как в миссии': '', 'Аркадный': 'arcade', 'Реалистичный': 'realistic',
                'Симуляторный': 'simulation'}
ALT_TIERS = {'low': (150, 300, 600, 1000), 'mid': (2000, 3500, 5000, 6500),
             'high': (8000, 10000, 12000, 15000)}


def spawn_settings(scenario, source):
    c = scenario.conditions
    if scenario.mode == 'ground':
        return {'spawn': 'firing_range', 'mtype': 'testFlight'}
    if scenario.mode == 'naval':
        return {'spawn': 'avn_fiji', 'mtype': 'testFlight'}
    spawn = 'denmark_heli_airfield' if scenario.mode == 'heli' and c.ground_start else 'air_denmark'
    result = {'spawn': spawn, 'mtype': 'singleMission'}
    # Источник: исходники/missions.py gen_air/gen_duel: level и spawn_area01 из test_flight_universal_*.blk.
    template = source.mission(AIR_MAPS.get(c.map, AIR_MAPS['denmark'])) if source else None
    if template:
        ms = template.block('mission_settings')
        mission = ms.block('mission') if ms else None
        areas = template.block('areas')
        key = 'heli_spawn_area' if scenario.mode == 'heli' and c.ground_start else (
            'spawn_area01_heli' if scenario.mode == 'heli' else 'spawn_area01')
        area = next((a for a in (areas.blocks if areas else []) if a.name == key), None)
        if mission and mission.get('level'):
            result['level'] = mission.get('level')
        if area and area.get('tm'):
            pos = list(area.get('tm')[3])
            if not c.ground_start:
                pos[1] = c.start_altitude
            result['player_pos'] = tuple(pos)
    else:
        pos = list(SPAWNS[spawn][1])
        if not c.ground_start:
            pos[1] = c.start_altitude
        result['player_pos'] = tuple(pos)
    result['player_speed'] = c.start_speed or (0 if c.ground_start else 150 if scenario.mode == 'heli' else 600)
    return result


def _ground_unit(name, cls, pos, ship, shoots, radar):
    kind = 'ships' if ship else 'tankModels'
    # Источник: исходники/missions.py ground_unit и M._setup: attack_type=hold_fire/fire_at_will.
    props = [('army', 'i', 2), ('count', 'i', 1),
             ('attack_type', 't', 'fire_at_will' if shoots else 'hold_fire')]
    if radar:
        # Источник: исходники/missions.py и текущий targets.air_parts: use_search_radar.
        props.append(('use_search_radar', 'b', True))
    return B.Block(kind, [('name', 't', name), ('tm', 'm', _tm(pos)), ('unit_class', 't', cls),
                          ('objLayer', 'i', 1), ('weapons', 't', '')],
                   [B.Block('props', props), B.Block('way')])


def _restore_trigger(name):
    killed = B.Block('unitWhenStatus', [('object_type', 't', 'isKilled'), ('check_objects', 't', 'any'),
                                        ('object_marking', 'i', 0), ('object_var_name', 't', ''),
                                        ('object_var_comp_op', 't', 'equal'), ('object_var_value', 'i', 0),
                                        ('target_type', 't', 'isAlive'), ('check_period', 'r', 1.0),
                                        ('object', 't', name)])
    return _trigger(name + '_restore', True, [B.Block('periodicEvent', [('time', 'r', 1.0)])],
                    [killed], [B.Block('wait', [('time', 'r', 5.0)]), _restore(name, True)], True)


def _ammo_restore():
    # Источник: исходники/missions.py M.build: restore_on_kill → unitRestore(player, full=False, ammo=True).
    return B.Block('unitRestore', [('target_marking', 'i', 0), ('ressurectIfDead', 'b', False),
                                    ('fullRestore', 'b', False), ('target', 't', 'player'),
                                    ('ammoRestore', 'b', True)])


def _route(name, points, speed, closed=False):
    way = [B.Block('%s_wp_%02d' % (name, i), [('type', 't', 'normal'), ('tm', 'm', _tm(p))],
                   [B.Block('props', [('speed', 'r', speed), ('moveType', 't', 'MOVETO_STRAIGHT'),
                                      ('tas', 'b', False), ('canUsePathFinder', 'b', False)])])
           for i, p in enumerate(points, 1)]
    return B.Block(name, [('closed_waypoints', 'b', closed), ('isShipSpline', 'b', False),
                          ('shipTurnRadius', 'r', 100.0), ('dontOverrideHeight', 'b', True)],
                   [B.Block('way', blocks=way)])


def _duel_weapons(source, cls, choice):
    # Источник: исходники/ui.html §duel и missions.py gen_duel: weapons = имя weapon_presets противника.
    if not source or choice in ('', 'none'):
        return ''
    from ..game.index import unit_file
    unit = source.load(unit_file('air', cls)) or source.load(unit_file('heli', cls))
    presets = unit.block('weapon_presets') if unit else None
    names = [p.get('name') for p in (presets.blocks if presets else []) if p.get('name')]
    if choice in names:
        return choice
    needles = ('air', 'aam', 'fighter', 'missile') if choice == 'air' else ('bomb', 'rocket', 'strike', 'ground')
    return next((name for name in names if any(x in name.lower() for x in needles)), '')


def mission_parts(scenario, source=None):
    """Ключи mission_text: юниты, действия, триггеры, маршруты и настройки."""
    config = spawn_settings(scenario, source)
    pos = config.get('player_pos', SPAWNS[config['spawn']][1])
    units, init, triggers, ways = [], [], [], []
    air_i = ground_i = ship_i = 0
    if scenario.mode == 'ground':
        config['player_turn'] = T.PLAYER_TURN
    if scenario.mode == 'duel':
        entries = [('duel', scenario.duel.enemy, scenario.duel.count)] if scenario.duel.enemy else []
    else:
        entries = [(key, t.vehicle, t.count) for key, _, _ in CATEGORIES[scenario.mode]
                   for t in scenario.categories[key].targets]
    for key, cls, count in entries:
        cat = scenario.categories.get(key)
        shoots = scenario.duel.shoots if key == 'duel' else cat.shoots
        radar = cat.radar if cat else False
        distance = scenario.duel.distance if key == 'duel' else cat.distance
        for _ in range(count):
            if key in ('ground', 'spaa', 'ships'):
                if key == 'ships':
                    ship_i += 1
                    i, name = ship_i, 'ship_%02d' % ship_i
                    p = (pos[0] + distance + (i - 1) * 130, 0., pos[2] + (i % 3) * 170)
                else:
                    ground_i += 1
                    i, name = ground_i, 'gnd_%02d' % ground_i
                    if scenario.mode == 'ground':
                        if not distance and i <= len(T._AREAS):
                            # Источник: targets.py _AREAS из testflight_era_tft.blk, дистанция 0.
                            p = T._AREAS[i][1]
                        else:
                            fx, fz = T.PLAYER_TURN[0][0], T.PLAYER_TURN[0][2]
                            side = (i - 1) * 40
                            p = (pos[0] + fx * (distance or 650) - fz * side,
                                 pos[1] + 2, pos[2] + fz * (distance or 650) + fx * side)
                    else:
                        p = (pos[0] + (distance or 650) + (i - 1) * 35, pos[1], pos[2] + (i % 4) * 40)
                units.append(_ground_unit(name, cls, p, key == 'ships', shoots, radar))
                if key == 'ships' and scenario.rules.moving_ships and scenario.mode in ('air', 'heli'):
                    # Источник: исходники/missions.py gen_air: route корабля по замкнутому кругу.
                    route = name + '_way'
                    points = [(p[0] + 600 * (math.cos(j * math.pi / 3) - 1), 0.,
                               p[2] + 600 * math.sin(j * math.pi / 3)) for j in range(6)]
                    ways.append(_route(route, points, 30., True))
                    init.append(B.Block('unitSetRoute', [('route', 't', route), ('object', 't', name),
                                                         ('teleportToStart', 'b', False)]))
                if scenario.rules.markers:
                    # Источник: исходники/missions.py M._setup: unitSetIndication.
                    init.append(B.Block('unitSetIndication', [('set', 'b', True), ('target', 't', name)]))
                if scenario.rules.restore_targets:
                    trigger = _restore_trigger(name)
                    if scenario.rules.restore_ammo:
                        trigger.block('actions').blocks.append(_ammo_restore())
                    triggers.append(trigger)
            else:
                air_i += 1
                i, name = air_i, 'air_%02d' % air_i
                tier = scenario.conditions.air_altitude
                height = (ALT_TIERS[tier][(i - 1) % 4] if tier in ALT_TIERS else
                          (150, 2000, 8000)[(i - 1) % 3])
                if key == 'duel':
                    height = scenario.duel.altitude or pos[1]
                p = (pos[0] + distance, max(500, height), pos[2] + (i - 1) * 300)
                end = (pos[0], p[1], pos[2])
                speed = 180. if key == 'heli' else 500.
                # Источник: targets.air_parts — маршрут, use_search_radar и возрождение;
                # исходники/missions.py air_slot — эшелоны низкий/средний/высокий.
                u, a, t, w = T.air_parts(name, cls, p, end, speed, radar=radar,
                                         respawn=scenario.rules.restore_targets)
                props = u[0].block('props')
                props.params = [(k, typ, val) for k, typ, val in props.params if k != 'attack_type'] + [
                    ('attack_type', 't', 'fire_at_will' if shoots else 'hold_fire')]
                if shoots:
                    for action in a + [action for trig in t for action in trig.block('actions').blocks]:
                        if action.name == 'unitSetProperties':
                            action.params = [(k, typ, val) for k, typ, val in action.params if k != 'cannotShoot']
                if not scenario.rules.markers:
                    a = [action for action in a if action.name != 'unitSetIndication']
                    for trig in t:
                        actions = trig.block('actions')
                        actions.blocks = [action for action in actions.blocks if action.name != 'unitSetIndication']
                if key in ('air', 'heli'):
                    # Источник: исходники/missions.py gen_air: восемь точек на круге, смена эшелона air_slot.
                    radius = max(3000, distance)
                    points = [(pos[0] + radius * math.cos(j * math.pi / 4), p[1],
                               pos[2] + radius * math.sin(j * math.pi / 4)) for j in range(8)]
                    w = [_route(name + '_way', points, speed, True)]
                if key == 'duel':
                    weapons = _duel_weapons(source, cls, scenario.duel.loadout)
                    u[0].params = [(k, typ, weapons if k == 'weapons' else val) for k, typ, val in u[0].params]
                if scenario.rules.restore_ammo:
                    for trig in t:
                        trig.block('actions').blocks.append(_ammo_restore())
                units += u
                init += a
                triggers += t
                ways += w
    c, r = scenario.conditions, scenario.rules
    # Источник: исходники/missions.py M.build: environment/weather/difficulty/isLimitedFuel.
    config.update(extra_units=units, init_actions=init, extra_triggers=triggers, way_points=ways,
                  environment=TIMES.get(c.time, c.time), weather=WEATHER.get(c.weather, c.weather),
                  difficulty=DIFFICULTIES.get(c.difficulty, c.difficulty), infinite_fuel=r.infinite_fuel,
                  player_respawn=r.player_respawn, rapid_reload=r.rapid_reload)
    return config


def describe(scenario):
    lines = ['Режим: ' + scenario.mode, 'Карта: ' + scenario.conditions.map]
    if scenario.mode == 'duel':
        lines.append('Противник: %s ×%d' % (scenario.duel.enemy, scenario.duel.count))
    else:
        for key, _, _ in CATEGORIES[scenario.mode]:
            cat = scenario.categories[key]
            if cat.targets:
                lines.append('%s: %s' % (key, ', '.join('%s ×%d' % (t.vehicle, t.count)
                                                         for t in cat.targets)))
    return lines
