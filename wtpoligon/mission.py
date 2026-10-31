"""Миссия: каркас пользовательской миссии, как у миссий 4.7, которые игра загружала (логи 10–24.10, launch.md §6).

Общий для программы и генератора тестов tools/make_test_missions.py: игрок, точка появления по типу техники,
возрождение после гибели, аэродром для вертолёта. Дополнительные юниты/действия/триггеры передаёт вызывающий.
"""
from .game import blk as B

PREFIX = 'wtp5_'

# блок миссии -> папка файла юнита (launch.md §2)
KINDS = {
    'air': ('armada', 'flightModels'),
    'heli': ('armada', 'flightModels'),
    'tank': ('tankModels', 'units/tankModels'),
    'ship': ('ships', 'units/ships'),
}

# точки появления, проверенные миссиями 4.7 (логи 10–12.10)
SPAWNS = {
    'firing_range': ('levels/firing_range.bin', (1724.72, 217.534, 1788.19), 0.0),
    'air_denmark': ('levels/air_denmark.bin', (24362.7, 2000.0, 1637.21), 700.0),
    'air_denmark_ground': ('levels/air_denmark.bin', (23389.1, 32.6033, 1602.4), 0.0),
    'avn_fiji': ('levels/avn_fiji.bin', (5524.64, 0.0, 3832.36), 0.0),
    # вертолёт — как универсальный тест-полёт игры test_flight_universal_denmark (mislist: test_flights_universal):
    # та же карта, что у самолёта; в миссии стоит объект «динамический аэродром» airfield_high, вертолёт ставится
    # на него spawnOnAirfield{runwayName:t="airfield_high"} (test_flight_template.blk: airfield_spawn = "airfield_" +
    # "high" для type_*_helicopter). История: без своего триггера игра возрождает вертолёт в воздухе (круг 1);
    # полоса Моздока из testflight_mozdok_heli — «неизвестный аэродром» без addAirfield (круг 2), у деревьев (круг 3)
    'denmark_heli_airfield': ('levels/air_denmark.bin', (23020.8, 31.574, 1600.45), 0.0),
    # 15-й круг: самолёт над мишенями firing_range (стоковый testflight_era_tft держит там самолёты-мишени на 400 м)
    # — 1,2 км до линии мишеней, ~700 м над землёй; и низко над водой avn_fiji (точка корабля) — для торпеды
    'firing_range_air': ('levels/firing_range.bin', (1000.0, 900.0, 2350.0), 350.0),
    'avn_fiji_air': ('levels/avn_fiji.bin', (5524.64, 60.0, 3832.36), 300.0),
}
# аэродромы-объекты: имя (оно же runwayName), класс objectGroups, tm — из test_flight_universal_denmark.blk
AIRFIELDS = {'denmark_heli_airfield': (
    'airfield_high', 'dynaf_pg_1line_3000_universal',
    ((0.998081, 0.0, 0.0619298), (0.0, 1.0, 0.0), (-0.0619298, 0.0, 0.998081), (23020.8, 31.574, 1600.45)))}


def _tm(pos, scale=1.0, turn=None):
    if turn:
        return tuple(tuple(v * scale for v in row) for row in turn) + (pos,)
    return ((scale, 0.0, 0.0), (0.0, scale, 0.0), (0.0, 0.0, scale), pos)


def _trigger(name, enabled, events, conditions, actions, after_complete):
    return B.Block(name, [('is_enabled', 'b', enabled), ('comments', 't', '')], [
        B.Block('props', [('actionsType', 't', 'PERFORM_ONE_BY_ONE'), ('conditionsType', 't', 'ALL'),
                          ('enableAfterComplete', 'b', after_complete)]),
        B.Block('events', blocks=events), B.Block('conditions', blocks=conditions),
        B.Block('actions', blocks=actions), B.Block('else_actions')])


def _restore(target, resurrect):
    return B.Block('unitRestore', [('target_marking', 'i', 0), ('ressurectIfDead', 'b', resurrect),
                                   ('fullRestore', 'b', True), ('target', 't', target), ('ammoRestore', 'b', True)])


def mission_text(*, name, loc_name, loc_desc, kind, spawn, mtype, unit_class, weapons='', bullets=(),
                 modifications=(), extra_units=(), init_actions=(), extra_triggers=(), way_points=(),
                 player_turn=None, header='// WT Poligon 5: тестовая миссия (launch.md §6)\n',
                 level=None, player_pos=None, player_speed=None, environment='Day', weather='good',
                 difficulty='', infinite_fuel=True, player_respawn=True, rapid_reload=0):
    """Текст миссии. name — mission{name} (= имя файла без .blk); bullets — [(блок снаряда, количество)] до 4;
    modifications — модификации игрока; init_actions — действия в конце триггера init; extra_triggers — после
    стандартных; extra_units — после игрока (и аэродрома); player_turn — поворот игрока и зоны возрождения
    (3 строки tm, без него — без поворота, как у миссий 4.7)."""
    block, _ = KINDS[kind]
    stock_level, pos, speed = SPAWNS[spawn]
    level = level or stock_level
    pos = player_pos or pos
    speed = player_speed if player_speed is not None else speed
    airfield = AIRFIELDS.get(spawn)
    units = []
    if airfield:
        # как test_flight_template.blk: разбудить аэродром и поставить на него; после гибели через 3 с — снова
        af_name, af_class, af_tm = airfield
        units = [B.Block('objectGroups', [('name', 't', af_name), ('tm', 'm', af_tm), ('unit_class', 't', af_class),
                                          ('objLayer', 'i', 2)],
                         [B.Block('props', [('army', 'i', 1), ('active', 'b', True)])])]
        on_air = B.Block('spawnOnAirfield', [('runwayName', 't', af_name), ('objects', 't', 'player')])
        wake = B.Block('unitWakeUp', [('target', 't', af_name)])
        triggers = B.Block('triggers', [('isCategory', 'b', True), ('is_enabled', 'b', True)], [
            _trigger('init', True, [B.Block('initMission')], [], [wake, on_air], False),
            _trigger('player_crashed', True, [B.Block('periodicEvent', [('time', 'r', 1.0)])],
                     [B.Block('playersWhenStatus', [('players', 't', 'isKilled'), ('check_players', 't', 'any')])],
                     [B.Block('wait', [('time', 'r', 3.0)]), on_air], True)])
    else:
        triggers = B.Block('triggers', [('isCategory', 'b', True), ('is_enabled', 'b', True)], [
            _trigger('init', True, [B.Block('initMission')], [],
                     [B.Block('triggerEnable', [('target', 't', 'player_crashed')])], False),
            _trigger('player_crashed', False, [B.Block('periodicEvent', [('time', 'r', 1.0)])],
                     [B.Block('unitWhenStatus', [
                         ('object_type', 't', 'isKilled'), ('check_objects', 't', 'any'), ('object_marking', 'i', 0),
                         ('object_var_name', 't', ''), ('object_var_comp_op', 't', 'equal'),
                         ('object_var_value', 'i', 0), ('target_type', 't', 'isAlive'), ('check_period', 'r', 1.0),
                         ('object', 't', 'player')])],
                     [B.Block('wait', [('time', 'r', 3.0)]),
                      B.Block('unitRespawn', [('delay', 'r', 0.0), ('offset', 'p3', (0.0, 0.0, 0.0)),
                                              ('object', 't', 'player'), ('target', 't', 'player_spawn')]),
                      _restore('player', True)], True)])
    triggers.blocks[0].block('actions').blocks.extend(init_actions)
    triggers.blocks.extend(extra_triggers)
    # Источник: исходники/missions.py M.build: rapid_fire = periodicEvent + unitRestore.
    if rapid_reload:
        triggers.blocks.append(_trigger('rapid_fire', True,
            [B.Block('periodicEvent', [('time', 'r', float(max(1, rapid_reload)))])], [],
            [_restore('player', False)], True))
    # Источник: исходники/missions.py M.build: опциональное возрождение игрока.
    if not player_respawn:
        triggers.blocks = [t for t in triggers.blocks if t.name != 'player_crashed']
        actions = triggers.blocks[0].block('actions')
        actions.blocks = [a for a in actions.blocks if a.name != 'triggerEnable']

    params = [('name', 't', 'player'), ('tm', 'm', _tm(pos, turn=player_turn)), ('unit_class', 't', unit_class),
              ('objLayer', 'i', 1), ('closed_waypoints', 'b', False), ('isShipSpline', 'b', False),
              ('shipTurnRadius', 'r', 100.0), ('weapons', 't', weapons)]
    # 11-й круг: снаряд выбирает миссия — bulletsN = имя блока снаряда в файле орудия (как в 246 стоковых миссиях,
    # weapons_survey.md), bulletsCountN — количество. Без bullets — пусто (штатный снаряд)
    chosen = list(bullets) + [('', 0)] * 4
    for i in range(4):
        params.append(('bullets%d' % i, 't', chosen[i][0]))
    # стоковые testFlight-миссии наземки/флота ставят ненулевое число (10/100/1000), миссии авиа 4.7 — 0
    first = 0 if block == 'armada' else 100
    for i in range(4):
        params.append(('bulletsCount%d' % i, 'i', chosen[i][1] if bullets else first if i == 0 else 0))
    # проверка 24.10: у копии под своим именем работают только перечисленные модификации, applyAllMods не помогает
    # (дрон из списка был, огнетушителя/дымов/тепловизора — нет) → перечисляем все модификации из файла машины
    for m in modifications:
        params.append(('modification', 't', m))
    params += [('crewSkillK', 'r', 1.0), ('applyAllMods', 'b', True)]

    props = [('army', 'i', 1), ('count', 'i', 1)]
    sub = []
    if block == 'armada':
        props += [('free_distance', 'r', 70.0), ('floating_distance', 'r', 50.0),
                  ('minimum_distance_to_earth', 'r', 20.0), ('altLimit', 'r', 16000.0),
                  ('attack_type', 't', 'fire_at_will'), ('skill', 'i', 4), ('fuel', 'r', 100.0),
                  ('speed', 'r', speed)]
        sub = [B.Block('plane', [('wing_formation', 't', 'Diamond'), ('row_distances', 'r', 3.0),
                                 ('col_distances', 'r', 3.0), ('super_formation', 't', 'Diamond'),
                                 ('super_row_distances', 'r', 1.5), ('super_col_distances', 'r', 1.5),
                                 ('ai_skill', 't', 'NORMAL'), ('task', 't', 'FLY_WAYPOINT')])]
    else:
        props += [('formation_type', 't', 'rows'), ('formation_div', 'i', 3), ('formation_step', 'p2', (2.5, 2.0)),
                  ('formation_noise', 'p2', (0.1, 0.1)), ('uniqueName', 't', ''), ('attack_type', 't', 'fire_at_will')]
    player = B.Block(block, params, [B.Block('props', props, sub), B.Block('way')])

    root = B.Block(None, [('selected_tag', 't', ''), ('bin_dump_file', 't', '')], [
        B.Block('mission_settings', blocks=[
            B.Block('player', [('army', 'i', 1), ('wing', 't', 'player')]),
            B.Block('player_teamB', [('army', 'i', 2)]),
            # имя миссии: с пустым именем «Перезапуск» грузит первую по алфавиту миссию с тем же пустым именем
            # (24.10 — Chroma_Poligon_Air_C_krymsk, 11.10 — Ask3lad); mission{name} подтверждено в игре (launch.md)
            B.Block('mission', [('name', 't', name),
                                ('type', 't', mtype), ('level', 't', level), ('environment', 't', environment),
                                ('weather', 't', weather), ('locName', 't', loc_name), ('locDesc', 't', loc_desc),
                                ('isLimitedFuel', 'b', not infinite_fuel), ('isLimitedAmmo', 'b', True),
                                ('restoreType', 't', 'manual'), ('optionalTakeOff', 'b', False)]
                    + ([('difficulty', 't', difficulty)] if difficulty else []))]),
        B.Block('imports'), triggers,
        B.Block('mission_objectives', [('isCategory', 'b', True), ('is_enabled', 'b', True)]),
        B.Block('variables'), B.Block('dialogs'), B.Block('airfields'), B.Block('effects'),
        B.Block('units', blocks=[player] + units + list(extra_units)),
        B.Block('areas', blocks=[B.Block('player_spawn', [('type', 't', 'Sphere'), ('tm', 'm', _tm(pos, 10.0, player_turn)),
                                                          ('objLayer', 'i', 0)], [B.Block('props')])]),
        B.Block('objLayers', blocks=[B.Block('layer', [('enabled', 'b', True)]) for _ in range(4)]),
        B.Block('wayPoints', blocks=list(way_points))])
    return header + B.to_text(root)
