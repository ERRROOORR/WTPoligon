"""Генератор тестовых миссий: формат файлов и безопасность записи (на временной папке вместо игры)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import make_test_missions as M  # noqa: E402
from wtlib import blk as B  # noqa: E402


class Files(unittest.TestCase):
    def setUp(self):
        self.items = M.plan(M.STANDARD_CASES)

    def test_only_allowed_places_and_prefix(self):
        for rel, _ in self.items:
            self.assertTrue(rel.startswith('content/pkg_local/gameData/') or rel.startswith(M.MISSION_DIR + '/'), rel)
            if rel.startswith('content/'):
                donors = {c['donor'] for c in M.CASES if c.get('donor')}
                base = os.path.basename(rel)[:-4]
                if '/userVehicles/' in rel:
                    self.assertIn(base, donors, rel)  # слот машины из ангара — только для пунктов с donor
                else:
                    self.assertTrue(base.startswith(M.PREFIX), rel)

    def test_donor_slots_unique(self):
        donors = [(c['kind'], c['donor']) for c in M.STANDARD_CASES if c.get('donor')]
        self.assertEqual(len(donors), len(set(donors)))

    def test_round22_uses_existing_helicopter_and_stock_preset(self):
        case = [c for c in M.CASES if c['id'] in M.ROUND22_IDS][0]
        items = M.plan([case])
        self.assertEqual(len(items), 1)
        root = B.parse_text(items[0][1])
        player = root.block('units').blocks[0]
        self.assertEqual(player.get('unit_class'), 'userVehicles/mi_28nm')
        self.assertEqual(player.get('weapons'), 'mi_28nm_rocket_c_8_ko')

    def test_round23_isolates_takeoff_field(self):
        cases = [c for c in M.CASES if c['id'] in M.ROUND23_IDS]
        self.assertEqual(len(cases), 2)
        self.assertTrue(all(c['weapons'] == '' for c in cases))
        changed = [c for c in cases if c.get('fm_takeoff_delta') is not None]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]['fm_takeoff_delta'], -2000.0)
        self.assertFalse(any(c.get('fm_empty_delta') is not None or c.get('loadout') for c in cases))

    def test_round24_changes_one_engine_field_per_case(self):
        cases = [c for c in M.CASES if c['id'] in M.ROUND24_IDS]
        self.assertEqual({c['fm_power_field'] for c in cases},
                         {'Main/Power', 'Compressor/Power0'})
        self.assertTrue(all(c['weapons'] == '' and c['unit'] == 'a-26b' for c in cases))

    def test_round25_csv_matches_mission_name_and_copy(self):
        case = [c for c in M.CASES if c['id'] in M.ROUND25_IDS][0]
        items = dict(M.plan([case]))
        stem = case['mission_file_stem']
        root = B.parse_text(items[M.MISSION_DIR + '/' + stem + '.blk'])
        self.assertEqual(root.block('mission_settings').block('mission').get('name'), stem)
        self.assertEqual(root.block('mission_settings').block('mission').get('locName'),
                         case['loc_name_key'])
        csv = items[M.MISSION_DIR + '/usr_' + stem + '.csv']
        self.assertIn(case['loc_name_key'], csv)
        self.assertIn('wtp5t_a-26b_r25_loc_1', csv)
        self.assertIn('wtp5t_a-26b_r25_loc_shop', csv)
        self.assertIn('missions/' + stem + '/date', csv)

    def test_registry_targets_are_copies_in_plan(self):
        # регистрируем только машины, у которых есть копия wtp5t_* в наборе, и только в pkg_local/config/
        copies = {os.path.basename(r)[:-4] for r, _ in self.items if r.startswith('content/')}
        for path, units in M.REGISTRY.items():
            self.assertTrue(path.startswith('config/'), path)
            for u in units:
                self.assertIn(M.PREFIX + u.lower(), copies)

    def test_mission_points_to_unit_file_in_right_folder(self):
        units = {rel for rel, _ in self.items if rel.startswith('content/')}
        for rel, text in self.items:
            if not rel.startswith(M.MISSION_DIR):
                continue
            root = B.parse_text(text)
            player = root.block('units').blocks[0]
            case = [c for c in M.CASES if rel.endswith('/%s.blk' % c['id'])][0]
            if case.get('real_name'):
                # контроль: машина из ангара под настоящим именем, копии нет
                self.assertEqual(player.get('unit_class'), case['unit'])
                continue
            if case.get('donor'):
                self.assertEqual(player.get('unit_class'), 'userVehicles/' + case['donor'])
            folder = {'armada': 'flightModels', 'tankModels': 'units/tankModels', 'ships': 'units/ships'}[player.name]
            self.assertIn('content/pkg_local/gameData/%s/%s.blk' % (folder, player.get('unit_class')), units, rel)

    def test_unit_files_are_plain_include(self):
        for rel, text in self.items:
            if rel.startswith('content/'):
                inc = [p for p in B.parse_text(text).params if p[1] == 'include']
                self.assertEqual(len(inc), 1, rel)
                self.assertTrue(inc[0][2].startswith('#/develop/gameBase/gameData/'), rel)

    def test_sam_launchers_renamed_with_folder(self):
        fcs = [t for r, t in self.items if r.endswith(M.PREFIX + 'fr_samp_t_fcs.blk')][0]
        sp = B.parse_text(fcs).block('@override:supportPlanes')
        self.assertEqual([b.name for b in sp.blocks], ['@override:plane[1]', '@override:plane[2]'])
        for b in sp.blocks:
            self.assertEqual(b.get('@override:class'), 'tankModels/' + M.PREFIX + 'fr_samp_t_launcher')

    def test_mission_has_unique_name(self):
        names = []
        for rel, text in self.items:
            if rel.startswith(M.MISSION_DIR):
                names.append(B.parse_text(text).block('mission_settings').block('mission').get('name'))
        self.assertTrue(all(n and n.startswith(M.PREFIX) for n in names), names)
        self.assertEqual(len(names), len(set(names)))

    def test_all_mods_listed(self):
        case = dict(M.CASES[0], _all_mods=['a_mod', 'b_mod'])
        player = B.parse_text(M.mission(case, 'x')).block('units').blocks[0]
        self.assertEqual([v for k, _, v in player.params if k == 'modification'], ['a_mod', 'b_mod'])

    def test_heli_spawns_on_runway(self):
        heli = [c for c in M.CASES if c['kind'] == 'heli'][0]
        trig = B.parse_text(M.mission(heli, 'x')).block('triggers')
        for t in ('init', 'player_crashed'):
            self.assertEqual(trig.block(t).block('actions').block('spawnOnAirfield').get('objects'), 'player')
        # аэродром — объект миссии с тем же именем, что runwayName (иначе игра пишет «неизвестный аэродром»)
        root = B.parse_text(M.mission(heli, 'x'))
        runway = trig.block('init').block('actions').block('spawnOnAirfield').get('runwayName')
        objs = [u.get('name') for u in root.block('units').blocks if u.name == 'objectGroups']
        self.assertIn(runway, objs)
        acts = [b.name for b in root.block('triggers').block('init').block('actions').blocks]
        self.assertLess(acts.index('unitWakeUp'), acts.index('spawnOnAirfield'))

    def test_mission_ammo_choice(self):
        case = dict(M.CASES[0], bullets=[('125mm_x_APFSDS', 20)])
        player = B.parse_text(M.mission(case, 'x')).block('units').blocks[0]
        self.assertEqual(player.get('bullets0'), '125mm_x_APFSDS')
        self.assertEqual(player.get('bulletsCount0'), 20)
        self.assertEqual([player.get('bullets%d' % i) for i in (1, 2, 3)], ['', '', ''])
        self.assertEqual([player.get('bulletsCount%d' % i) for i in (1, 2, 3)], [0, 0, 0])

    def test_mission_targets(self):
        root = B.parse_text(M.mission(M.CASES[0], 'x'))
        targets = [u for u in root.block('units').blocks if u.get('name', '').startswith('target_')]
        self.assertEqual([u.get('unit_class') for u in targets], [t[1] for t in M.TARGETS])
        for u in targets:
            self.assertEqual(u.block('props').get('army'), 2)
            self.assertEqual(u.block('props').get('attack_type'), 'dont_aim')
        restore = root.block('triggers').block('targets_restore')
        self.assertIsNotNone(restore)
        self.assertEqual(len([b for b in restore.block('actions').blocks if b.name == 'unitRestore']), len(M.TARGETS))
        # без 'targets' мишеней нет
        other = B.parse_text(M.mission(M.CASES[1], 'x'))
        self.assertFalse([u for u in other.block('units').blocks if u.get('name', '').startswith('target_')])

    def test_override_path(self):
        stock = B.parse_text('s{ bullet{ damage{ kinetic{ len:r=640.0 } } } bullet{ x:i=1 } }')
        text = M.override_path(stock, 's/bullet/damage/kinetic/len', 150)
        self.assertIn('"@override:bullet[1]"{', text)  # одноимённых два — индекс обязателен
        self.assertIn('"@override:len":r=150.0', text)
        with self.assertRaises(KeyError):
            M.override_path(stock, 's/bullet/damage/kinetic/nope', 1.0)
        log = []
        res = B.apply_patch(stock, B.parse_text(text), log)
        self.assertEqual(log, [])
        self.assertEqual(res.block('s').block('bullet').block('damage').block('kinetic').get('len'), 150.0)

    def test_weapon_copies(self):
        trees = {
            'p/a.blk': B.parse_text('Weapon{ blk:t="w/x.blk" } Weapon{ blk:t="w/x.blk" } Weapon{ blk:t="w/y.blk" }'),
            'w/x.blk': B.parse_text('bomb{ explosiveMass:r=1.0 }'),
        }
        u = B.parse_text('weapon_presets{ preset{ name:t="other" blk:t="p/o.blk" } preset{ name:t="a" blk:t="p/a.blk" } }')
        cfg = {'every': 2, 'presets': {'a': {'w/x.blk': [('bomb/explosiveMass', 5.0)]}}}
        files, unit, problems = M.weapon_copies(u, trees.get, cfg)
        self.assertEqual(problems, [])
        got = dict(files)
        self.assertIn('"@override:explosiveMass":r=5.0', got['content/pkg_local/w/' + M.PREFIX + 'x.blk'])
        preset = got['content/pkg_local/p/' + M.PREFIX + 'a.blk']
        self.assertIn('"@override:Weapon[2]"', preset)  # второй из двух x.blk
        self.assertNotIn('"@override:Weapon[1]"', preset)
        self.assertIn('"@override:preset[2]"', unit)
        for _p, text in files:
            B.parse_text(text)
        B.parse_text(unit)

    def test_air_loadout(self):
        u = B.parse_text('\n'.join([
            'WeaponSlots{', 'WeaponSlot{', 'index:i=0', '}', 'WeaponSlot{', 'index:i=2', 'WeaponPreset{', 'name:t="b"',
            'reqModification:t="m"', 'ShowNodes{', 'node:t="n"', '}', 'BannedWeaponPreset{', 'slot:i=3', 'preset:t="x"', '}',
            'Weapon{', 'trigger:t="bombs"', 'blk:t="w/b.blk"', 'emitter:t="e"', '}', '}', '}', '}',
            'weapon_presets{', 'preset{', 'name:t="s"', '}', '}']))
        cfg = {'variants': [(2, 'b', 'wtp5t_big', 'w/big.blk')],
               'presets': {'wtp5t_p': [(2, 'wtp5t_big')], 'wtp5t_bad': [(2, 'nope')]}}
        files, unit, problems = M.air_loadout(u, cfg, 'plane')
        self.assertEqual(len(problems), 1)  # nope в слоте 2 нет
        res = B.apply_patch(u, B.parse_text(unit), [])
        slot = res.block('WeaponSlots').blocks[1]
        v = [p for p in slot.blocks if p.get('name') == 'wtp5t_big'][0]
        self.assertIsNone(v.get('reqModification'))
        self.assertIsNone(v.block('BannedWeaponPreset'))
        self.assertEqual(v.block('Weapon').get('blk'), 'w/big.blk')
        self.assertIsNotNone(v.block('ShowNodes'))
        self.assertIn('wtp5t_p', [p.get('name') for p in res.block('weapon_presets').blocks])
        text = dict(files)['content/pkg_local/gameData/FlightModels/weaponPresets/wtp5t_plane_p.blk']
        self.assertEqual(B.parse_text(text).block('Weapon').get('preset'), 'wtp5t_big')

    def test_one_param_per_line(self):
        for rel, text in self.items:
            for line in text.split('\n'):
                self.assertLessEqual(line.count(':t=') + line.count(':r=') + line.count(':i=') + line.count(':b='), 1,
                                     (rel, line))



# 26-й круг: копия РЛС и мишень — на маленьких деревьях вместо игры/датамайна
RADAR = B.parse_text('''
name:t="AN/TEST"
type:t="radar"
transivers{
  mprf{
    power:r=1000.0
    rcs:r=1.0
    range:r=70000.0
    rangeMax:r=150000.0
  }
  hprf{
    range:r=150000.0
    rangeMax:r=300000.0
  }
  common{ band:i=8 }
}
scopeRangeSets{ common{ range1:r=37000.0 } }
''')
PLANE = B.parse_text('''
sensors{
  sensor{ blk:t="gameData/sensors/rwr.blk" }
  sensor{
    blk:t="gameData/sensors/Test_Radar.blk"
    dmPart:t="radar_dm"
  }
}
weapon_presets{ preset{
  name:t="p1"
  blk:t="x.blk"
} }
''')
CFG = {'sensor': 'gameData/sensors/test_radar.blk', 'field': 'range', 'scale': 0.1}


class Round26(unittest.TestCase):
    def load(self, path):
        return {'gameData/sensors/test_radar.blk': RADAR}.get(path.replace('#/develop/gameBase/', ''))

    def test_sensor_copy_scales_every_mode_and_relinks_root_entry(self):
        files, unit, problems, changes = M.sensor_copy(PLANE, self.load, CFG, 'тест')
        self.assertEqual(problems, [])
        self.assertEqual(changes, [('mprf', 70000.0, 7000.0), ('hprf', 150000.0, 15000.0)])
        (rel, text), = files
        self.assertEqual(rel, 'content/pkg_local/gameData/sensors/' + M.PREFIX + 'test_radar.blk')
        self.assertTrue(text.split('\n')[2].startswith('include "#/develop/gameBase/gameData/sensors/test_radar.blk"'))
        log = []
        res = B.resolve_file(text, self.load, log)
        self.assertEqual(log, [])
        tr = res.block('transivers')
        self.assertEqual((tr.block('mprf').get('range'), tr.block('mprf').get('rangeMax')), (7000.0, 150000.0))
        self.assertEqual(tr.block('hprf').get('range'), 15000.0)
        self.assertEqual(res.block('scopeRangeSets').block('common').get('range1'), 37000.0)  # шкалы не трогаем
        self.assertIn('"@override:sensor[2]"', unit)  # регистр пути в ссылке не важен, сенсоров два → индекс
        got = B.apply_patch(PLANE, B.parse_text(unit), log)
        self.assertEqual(log, [])
        refs = [(s.get('blk'), s.get('dmPart')) for s in got.block('sensors').blocks]
        self.assertEqual(refs, [('gameData/sensors/rwr.blk', None),
                                ('gameData/sensors/' + M.PREFIX + 'test_radar.blk', 'radar_dm')])

    def test_sensor_copy_refuses_ambiguous_or_wrong_sensor(self):
        extra = B.parse_text(B.to_text(PLANE) + 'modifications{ m{ effects{ sensors{ sensor{ '
                             'blk:t="gameData/sensors/test_radar.blk" } } } } }')
        _f, _u, problems, _c = M.sensor_copy(extra, self.load, CFG, 'тест')
        self.assertTrue(any('вне корня' in p for p in problems), problems)
        ir = B.parse_text('type:t="radar"\ntransivers{ irst{\nvisibilityType:t="infraRed"\nrange:r=10.0\n} }')
        _f, _u, problems, _c = M.sensor_copy(PLANE, lambda p: ir, CFG, 'тест')
        self.assertTrue(any('не обычная РЛС' in p for p in problems), problems)
        _f, _u, problems, _c = M.sensor_copy(PLANE, lambda p: None, CFG, 'тест')
        self.assertEqual(len(problems), 1)
        _f, _u, problems, _c = M.sensor_copy(PLANE, self.load, dict(CFG, field='nope'), 'тест')
        self.assertTrue(any('нет transivers' in p for p in problems), problems)

    def test_round26_cases_and_plan(self):
        cases = [c for c in M.CASES if c['id'] in M.ROUND26_IDS]
        self.assertEqual(len(cases), 2)
        self.assertEqual(len({c['unit'] for c in cases} | {c['weapons'] for c in cases}), 2)  # та же машина и пресет
        self.assertEqual([bool(c.get('sensor_copy')) for c in cases], [False, True])
        self.assertTrue(all(c['id'] not in {x['id'] for x in M.STANDARD_CASES} for c in cases))
        with self.assertRaises(AssertionError):  # без подготовки копии РЛС не пишем «правку», равную контролю
            M.plan(cases)
        edited = dict(cases[1])
        files, unit, _p, _c = M.sensor_copy(PLANE, self.load, CFG, edited['title'])
        edited['_sensor'] = (files, unit, _c)
        items = dict(M.plan([cases[0], edited]))
        ctrl = items['content/pkg_local/gameData/flightModels/%s%s_r26_ctrl.blk' % (M.PREFIX, cases[0]['unit'])]
        self.assertNotIn('@override', ctrl)
        mod = items['content/pkg_local/gameData/flightModels/%s%s_r26_radar.blk' % (M.PREFIX, cases[1]['unit'])]
        self.assertIn(M.PREFIX + 'test_radar.blk', mod)
        self.assertIn('content/pkg_local/gameData/sensors/' + M.PREFIX + 'test_radar.blk', items)

    def test_mission_has_air_target_with_route(self):
        case = [c for c in M.CASES if c['id'] in M.ROUND26_IDS][0]
        at = M.AIR_TARGETS[case['air_target']]
        root = B.parse_text(M.mission(case, 'x'))
        units = root.block('units').blocks
        target = [u for u in units if u.get('name') == at['name']][0]
        self.assertEqual(target.name, 'armada')
        self.assertEqual(target.block('props').get('army'), 2)
        player_pos = units[0].get('tm')[3]
        start = target.get('tm')[3]
        self.assertAlmostEqual(start[0] - player_pos[0], at['distance'])
        self.assertEqual(start[1:], player_pos[1:])
        way = root.block('wayPoints').block(at['name'] + '_way').block('way').blocks
        self.assertEqual([w.get('tm')[3] for w in way], [start, player_pos])
        init = root.block('triggers').blocks[0].block('actions')
        self.assertTrue(init.block('unitSetProperties').get('cannotShoot'))
        self.assertEqual(init.block('unitSetRoute').get('route'), at['name'] + '_way')
        self.assertIn('26-й круг', root.block('mission_settings').block('mission').get('locDesc'))
        # у остальных миссий мишени-самолёта и маршрутов нет
        other = B.parse_text(M.mission(M.CASES[1], 'x'))
        self.assertEqual(other.block('wayPoints').blocks, [])

    def test_datamine_loader_and_check(self):
        import json
        with tempfile.TemporaryDirectory() as dm:
            def put(rel, obj):
                full = os.path.join(dm, 'aces.vromfs.bin_u', rel)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, 'w', encoding='utf-8') as f:
                    json.dump(obj, f)
            case = [c for c in M.CASES if c['id'] in M.ROUND26_IDS][1]
            stock = M.SENSOR_COPIES[case['sensor_copy']]['sensor']
            put('gamedata/flightmodels/%s.blkx' % case['unit'], {
                'sensors': {'sensor': [{'blk': stock, 'dmPart': 'radar_dm'}, {'blk': 'gameData/sensors/rwr.blk'}]},
                'weapon_presets': {'preset': [{'name': case['weapons'], 'blk': 'x.blk'}]}})
            put('gamedata/flightmodels/%s.blkx' % M.AIR_TARGETS[case['air_target']]['unit_class'], {'model': 'm'})
            put(stock.lower() + 'x', {'type': 'radar', 'transivers': {'mprf': {'range': 70000.0, 'band': 8}}})
            load = M.datamine_loader(dm)
            self.assertEqual(load(stock).block('transivers').block('mprf').params,
                             [('range', 'r', 70000.0), ('band', 'i', 8)])
            c = dict(case)
            self.assertEqual(M.check_against_datamine(load, [c]), [])
            self.assertEqual(c['_sensor'][2], [('mprf', 70000.0, 7000.0)])
            self.assertIn('"@override:sensor[1]"', c['_sensor'][1])
            # пункты с полями, которые по датамайну не проверить, — отказ, а не молчаливый пропуск
            self.assertTrue(M.check_against_datamine(load, [dict(case, bake=True)]))

    def test_datamine_flag_only_with_round26(self):
        import contextlib
        import io
        for argv in (['--datamine', 'x'], ['--round26', '--datamine', 'x', '--remove']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                M.main(argv)

def _round27_datamine(dm, tiger_top=0.687):
    """Датамайн-заглушка 27-го круга: файлы машин в виде *.blkx со стоковыми значениями ground_naval_plan.md §1."""
    import json

    def put(folder, unit, obj):
        full = os.path.join(dm, 'aces.vromfs.bin_u', 'gamedata', folder.lower(), unit + '.blkx')
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            json.dump(obj, f)
    presets = {c['unit']: c['weapons'] for c in M.CASES if c['id'] in M.ROUND27_IDS}
    put('units/tankModels', 'ussr_t_80bvm', {
        'maxFwdSpeed': 75.0, 'weapon_presets': {'preset': [{'name': presets['ussr_t_80bvm'], 'blk': 'x.blk'}]},
        'VehiclePhys': {'Mass': {'Empty': 44500.0, 'Fuel': 1500.0, 'TakeOff': 46000.0},
                        'engine': {'horsePowers': 1250.0, 'maxRPM': 3154.0}}})
    put('units/tankModels', 'germ_pzkpfw_vi_ausf_h1_tiger', {
        'maxFwdSpeed': 75.0, 'weapon_presets': {
            'preset': [{'name': presets['germ_pzkpfw_vi_ausf_h1_tiger'], 'blk': 'x.blk'}]},
        'VehiclePhys': {'mechanics': {'gearRatios': {'ratio': [
            -3.7, -5.2, -7.6, -11.5, 0.0, 11.0, 7.38, 5.05, 3.4, 2.22, 1.495, 1.025, tiger_top]}}}})
    put('units/ships', 'us_destroyer_fletcher', {
        'maxFwdSpeed': 80.0, 'ShipPhys': {'mass': {'Empty': 2160000.0}, 'engines': {
            'maxSpeed': 18.0, 'maxReverseSpeed': 7.0, 'speedToTime': {'row': [[5.0, 6.6], [10.0, 13.7], [18.0, 28.5]]}}}})
    return M.datamine_loader(dm)


class Round27(unittest.TestCase):
    def cases(self):
        # без служебных _полей: main() в другом тесте готовит пункты прямо в M.CASES
        return [{k: v for k, v in c.items() if not k.startswith('_')} for c in M.CASES if c['id'] in M.ROUND27_IDS]

    def test_override_path_index(self):
        stock = B.parse_text('g{ ratio:r=-3.7\nratio:r=0.0\nratio:r=0.687 }')
        text = M.override_path(stock, 'g/ratio[3]', 0.3435)
        self.assertIn('"@override:ratio[3]":r=0.3435', text)
        self.assertIn('"@override:g"{', text)  # блок один — без индекса
        self.assertEqual(M.path_value(stock, 'g/ratio[3]'), 0.687)
        self.assertEqual(M.path_value(stock, 'g/ratio'), -3.7)
        self.assertIsNone(M.path_value(stock, 'g/ratio[4]'))
        with self.assertRaises(KeyError):
            M.override_path(stock, 'g/ratio[4]', 1.0)
        log = []
        res = B.apply_patch(stock, B.parse_text(text), log)
        self.assertEqual(log, [])
        self.assertEqual([p[2] for p in res.block('g').params], [-3.7, 0.0, 0.3435])

    def test_round27_cases(self):
        cases = self.cases()
        self.assertLessEqual(len(cases), 6)
        nums = sorted(int(c['title'].split('.')[0]) for c in cases)
        self.assertEqual(nums, list(range(43, 43 + len(cases))))  # следующие после 42
        self.assertFalse({c['id'] for c in cases} & {c['id'] for c in M.STANDARD_CASES})
        edited = [c for c in cases if c.get('unit_edits')]
        self.assertEqual(len(edited), 4)  # Н1–Н4 плана
        self.assertTrue(all(len(c['unit_edits']) == 1 for c in edited))  # одна правка на миссию
        for c in cases:
            self.assertFalse(c.get('bake') or c.get('targets') or c.get('bullets') or c.get('donor'), c['id'])
            self.assertIn(c['spawn'], ('firing_range', 'avn_fiji'))
        # у каждой правки есть контроль: та же машина, пресет, точка; без правок
        allc = {c['id']: c for c in M.CASES}
        for c in edited:
            ctrl = [x for x in cases if not x.get('unit_edits') and x['unit'] == c['unit']]
            ctrl = ctrl or [allc[M.ROUND27_CONTROLS[c['id']]]]
            self.assertEqual(len(ctrl), 1, c['id'])
            for k in ('kind', 'unit', 'weapons', 'spawn', 'mtype'):
                self.assertEqual(ctrl[0][k], c[k], (c['id'], k))
            self.assertFalse(ctrl[0].get('bake') or ctrl[0].get('unit_edits') or ctrl[0].get('suffix', '').endswith('_gun'))

    def test_round27_datamine_plan_and_final_values(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round27_datamine(dm)
            cases = self.cases()
            self.assertEqual(M.check_against_datamine(load, cases), [])
            items = M.plan(cases)
            res = M.check_unit_edits(load, items, cases)
            self.assertEqual(len(res), 6)
            self.assertEqual([p for _r, p, _g in res], [''] * 6, res)
            got = {r.split('/')[-1]: g for r, _p, g in res}
            self.assertEqual(got['wtp5t_germ_pzkpfw_vi_ausf_h1_tiger_r27_gear.blk'],
                             [('VehiclePhys/mechanics/gearRatios/ratio[13]', 0.3435)])
            self.assertEqual(got['wtp5t_us_destroyer_fletcher_r27_speed.blk'], [('ShipPhys/engines/maxSpeed', 36.0)])
            files = dict(items)
            for c in cases:
                mission = B.parse_text(files['%s/%s.blk' % (M.MISSION_DIR, c['id'])])
                player = mission.block('units').blocks[0]
                self.assertEqual(player.get('unit_class'), M.PREFIX + c['unit'].lower() + c['suffix'])
                self.assertIn('27-й круг', mission.block('mission_settings').block('mission').get('locDesc'))
            # правка, задевшая соседнее поле или не дошедшая, — ошибка
            rel = 'content/pkg_local/gameData/units/tankModels/wtp5t_germ_pzkpfw_vi_ausf_h1_tiger_r27_gear.blk'
            for wrong in ('ratio[13]":r=0.3435', ):
                bad = dict(files)
                bad[rel] = files[rel].replace(wrong, 'ratio[12]":r=0.3435')
                self.assertTrue(M.check_unit_edits(load, list(bad.items()), cases)[4][1])
            bad = dict(files)
            ctrl = 'content/pkg_local/gameData/units/tankModels/wtp5t_ussr_t_80bvm_r27_ctrl.blk'
            bad[ctrl] = files[ctrl] + '"@override:maxFwdSpeed":r=30.0\n'
            self.assertTrue(M.check_unit_edits(load, list(bad.items()), cases)[0][1])

    def test_round27_refuses_changed_stock(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round27_datamine(dm, tiger_top=0.7)  # «обновление игры» поменяло стоковое значение
            problems = M.check_against_datamine(load, self.cases())
            self.assertTrue(any('ratio[13]' in p for p in problems), problems)
            with self.assertRaises(AssertionError):  # без подготовленной правки опыт не пишем
                M.plan([c for c in self.cases() if c['id'] == 't47_tiger_r27_gear'])

    def test_round27_datamine_flag(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as dm:
            _round27_datamine(dm)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(M.main(['--round27', '--datamine', dm]), 0)
            self.assertIn('ratio[13]=0.3435', out.getvalue())
            self.assertNotIn('ОШИБКА', out.getvalue())


def _round28_datamine(dm, front=100.0):
    """Датамайн-заглушка 28-го круга: «Тигр» H1 и его орудие со стоковыми значениями aa326f1 (armor_crew.md)."""
    import json

    def put(rel, obj):
        full = os.path.join(dm, 'aces.vromfs.bin_u', rel.lower() + 'x')
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            json.dump(obj, f)
    gun = 'gameData/Weapons/groundModels_weapons/88mm_Kwk36_user_cannon.blk'
    put('gameData/units/tankModels/%s.blk' % M.R28_TIGER, {
        'weapon_presets': {'preset': [{'name': M.R28_PLAYER['weapons'], 'blk': 'x.blk'}]},
        'commonWeapons': {'Weapon': [{'trigger': 'gunner0', 'blk': gun}]},
        'DamageParts': {'formatVersion': 2, 'armorClass': 'RHA_tank', 'hp': 10000.0,
                        'hull': {'body_front_dm': {'armorThickness': 100.0},
                                 'superstructure_front_dm': {'armorThickness': front}},
                        'crew': {'armorClass': 'steel_tankman', 'hp': 40.0, 'genericDamageMult': 3.0,
                                 'driver_dm': {}, 'gunner_dm': {}}},
        'tank_crew': {'changeTimeMult': 1.0, 'loader': {'dmPart': 'loader_dm', 'role': 'loader'}},
        'ammo': {'combustionTime': 10.0, 'detonateProb': 0.15},
        'ammoStowages': {'ammo1': {'removeLoadedAmmo': False, 'weaponTrigger': 'gunner0', 'fatalFire': True,
                                   'fatalExplosion': True}}})
    put(gun, {'bullet': {'mass': 10.0}, '88mm_ger_kwk36_Pzgr_APCBC': {'bullet': {'mass': 10.2}}})
    return M.datamine_loader(dm)


class Round28(unittest.TestCase):
    def cases(self):
        return [{k: v for k, v in c.items() if not k.startswith('_')} for c in M.CASES if c['id'] in M.ROUND28_IDS]

    def test_round28_cases(self):
        cases = self.cases()
        self.assertLessEqual(len(cases), 6)
        nums = sorted(int(c['title'].split('.')[0]) for c in cases)
        self.assertEqual(nums, list(range(49, 49 + len(cases))))  # после 48
        self.assertFalse({c['id'] for c in cases} & {c['id'] for c in M.STANDARD_CASES})
        for c in cases:
            self.assertFalse(c.get('bake') or c.get('targets') or c.get('donor') or c.get('unit_edits'), c['id'])
            for k in ('kind', 'unit', 'suffix', 'weapons', 'spawn', 'mtype', 'bullets', 'target_unit'):
                self.assertEqual(c[k], M.R28_PLAYER[k], (c['id'], k))  # один стрелок во всех миссиях
            near, far = c['target_pair']
            base = dict((p, n) for p, _s, n in (M.R28_TARGETS[near][2] if near else []))
            diff = [(p, n) for p, _s, n in M.R28_TARGETS[far][2] if base.get(p) != n]
            self.assertEqual(len(diff) + len(base), len(M.R28_TARGETS[far][2]), c['id'])  # ближняя ⊂ дальней
            self.assertEqual(len(diff), 0 if far == 'ctrl' else 1, c['id'])  # одна правка на миссию
        self.assertEqual(sum(c['target_pair'] == (None, 'ctrl') for c in cases), 1)  # контроль копии мишени

    def test_round28_datamine_plan_and_final_values(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round28_datamine(dm)
            cases = self.cases()
            self.assertEqual(M.check_against_datamine(load, cases), [])
            items = M.plan(cases)
            files = dict(items)
            res = M.check_unit_edits(load, items, cases)
            self.assertEqual(len(res), 6)  # стрелок + 5 копий мишени, общие — один раз
            self.assertEqual([p for _r, p, _g in res], [''] * 6, res)
            got = {r.split('/')[-1]: g for r, _p, g in res}
            name = 'wtp5t_%s_r28_t_%%s.blk' % M.R28_TIGER
            self.assertEqual(got[name % 'armor'], [('DamageParts/hull/superstructure_front_dm/armorThickness', 300.0)])
            self.assertEqual(got[name % 'crew'], [('DamageParts/crew/hp', 4000.0)])
            self.assertEqual(got[name % 'nofatal'], [('ammo/detonateProb', 1.0),
                                                     ('ammoStowages/ammo1/fatalExplosion', False)])
            self.assertEqual(got['wtp5t_%s_r28.blk' % M.R28_TIGER], [])
            for c in cases:
                mission = B.parse_text(files['%s/%s.blk' % (M.MISSION_DIR, c['id'])])
                units = mission.block('units').blocks
                self.assertEqual(len(units), 3)
                player, near, far = units
                self.assertEqual(player.get('unit_class'), M.PREFIX + M.R28_TIGER + '_r28')
                self.assertEqual(player.get('bullets0'), '88mm_ger_kwk36_Pzgr_APCBC')
                want = [M.PREFIX + M.R28_TIGER + M.R28_TARGETS[k][0] if k else M.R28_TIGER for k in c['target_pair']]
                self.assertEqual([near.get('unit_class'), far.get('unit_class')], want)
                for t in (near, far):
                    self.assertEqual(t.block('props').get('army'), 2)
                    self.assertEqual(t.block('props').get('attack_type'), 'dont_aim')
                    x = t.get('tm')[0]  # лбом к игроку
                    to = [player.get('tm')[3][i] - t.get('tm')[3][i] for i in (0, 2)]
                    n = (to[0] ** 2 + to[1] ** 2) ** 0.5
                    self.assertAlmostEqual(x[0] * to[0] / n + x[2] * to[1] / n, 1.0, places=5)
                self.assertIn('28-й круг', mission.block('mission_settings').block('mission').get('locDesc'))
            # правка не в той части или лишний @override в контроле — ошибка
            rel = 'content/pkg_local/gameData/units/tankModels/' + name % 'armor'
            bad = dict(files)
            bad[rel] = files[rel].replace('superstructure_front_dm', 'body_front_dm')
            self.assertTrue([p for r, p, _g in M.check_unit_edits(load, list(bad.items()), cases) if r == rel][0])
            ctrl = 'content/pkg_local/gameData/units/tankModels/' + name % 'ctrl'
            bad = dict(files)
            bad[ctrl] = files[ctrl] + '"@override:ammo"{\n"@override:detonateProb":r=1.0\n}\n'
            self.assertTrue([p for r, p, _g in M.check_unit_edits(load, list(bad.items()), cases) if r == ctrl][0])

    def test_round28_refuses_changed_stock(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round28_datamine(dm, front=102.0)
            problems = M.check_against_datamine(load, self.cases())
            self.assertTrue(any('superstructure_front_dm' in p for p in problems), problems)
            with self.assertRaises(AssertionError):
                M.plan([c for c in self.cases() if c['id'] == 't50_tiger_r28_armor'])

    def test_round28_unknown_shell(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round28_datamine(dm)
            case = dict(self.cases()[0], bullets=[('88mm_no_such_shell', 10)])
            self.assertTrue(any('88mm_no_such_shell' in p for p in M.check_against_datamine(load, [case])))

    def test_round28_datamine_flag(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as dm:
            _round28_datamine(dm)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(M.main(['--round28', '--datamine', dm]), 0)
            self.assertIn('armorThickness=300.0', out.getvalue())
            self.assertNotIn('ОШИБКА', out.getvalue())


def _round29_datamine(dm, rwr_range=70000.0):
    """Датамайн-заглушка 29-го круга: F-15C (сенсоры, слоты пресета AIM-9M, ловушки), СПО, AIM-9M, «Тигр» и его
    орудие, самолёты-мишени — со стоковыми значениями aa326f1 там, где их правит круг."""
    import json

    def put(rel, obj):
        full = os.path.join(dm, 'aces.vromfs.bin_u', rel.lower() + 'x')
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            json.dump(obj, f)
    slots = []
    for i in range(1, 15):
        presets = [{'name': 'other%d' % k, 'Weapon': {'blk': 'x.blk'}} for k in range(1, 8)]
        if i == 1:
            cm = 'gameData/Weapons/rocketGuns/countermeasure_split_launcher_jet.blk'
            presets[0] = {'name': 'm61a1_common', 'Weapon': [
                {'trigger': 'gunner0'}, {'trigger': 'gunner0'}, {'trigger': 'cannon', 'bullets': 940},
                {'trigger': 'countermeasures', 'blk': cm, 'bullets': 60},
                {'trigger': 'countermeasures', 'blk': cm, 'bullets': 60}]}
        ref = dict(M.R29_AIM9_REFS).get('WeaponSlots/WeaponSlot[%d]/WeaponPreset[8]/Weapon[2]/blk' % i)
        if ref:
            presets.append({'name': 'aim_9m_slot%d_bol' % i, 'Weapon': [
                {'trigger': 'countermeasures', 'bullets': 160}, {'trigger': 'aam', 'blk': ref, 'bullets': 1}]})
        slots.append({'index': i - 1, 'WeaponPreset': presets})
    put('gameData/flightModels/%s.blk' % M.R29_F15['unit'], {
        'sensors': {'sensor': [{'blk': 'gameData/sensors/us_an_apg_63_v_3.blk', 'dmPart': 'radar_dm'},
                               {'blk': M.R29_RWR}, {'blk': 'gameData/sensors/LaserDesignatorSensor.blk'}]},
        'weapon_presets': {'preset': [{'name': M.R29_F15['weapons'], 'blk': 'x.blk'}]},
        'commonWeapons': {'Weapon': {'slot': 0, 'preset': 'm61a1_common'}},
        'WeaponSlots': {'WeaponSlot': slots}})
    put(M.R29_RWR, {'type': 'rwr', 'name': 'AN/ALR-56C', 'range': rwr_range, 'band9': True})
    for f in M.R29_AIM9:
        put(f, {'bullets': 1, 'rocket': {'bulletName': 'us_aim9m_sidewinder', 'guidance': {'opticalSeeker': {
            'rangeBand0': 11000.0, 'rangeBand1': 3000.0, 'rangeMax': 11000.0, 'fov': 3.6}}}})
    for t in ('r29_mig23', 'r26_mig15'):
        put('gameData/flightModels/%s.blk' % M.AIR_TARGETS[t]['unit_class'], {'model': 'm'})
    put('gameData/units/tankModels/%s.blk' % M.R28_TIGER, {
        'weapon_presets': {'preset': [{'name': M.R28_PLAYER['weapons'], 'blk': 'x.blk'}]},
        'commonWeapons': {'Weapon': [{'trigger': 'gunner0', 'blk': M.R29_GUN},
                                     {'trigger': 'gunner1', 'blk': 'gameData/Weapons/mg.blk'}]}})
    put(M.R29_GUN, {'bullet': {'mass': 10.0},
                    '88mm_ger_kwk36_Pzgr_APCBC': {'bullet': {'mass': 10.2, 'bulletName': '88mm_pzgr'}},
                    '88mm_ger_kwk36_APCR': {'bullet': {'mass': 7.3, 'bulletName': '88mm_pzrg_40'}}})
    return M.datamine_loader(dm)


class Round29(unittest.TestCase):
    def cases(self):
        return [{k: v for k, v in c.items() if not k.startswith('_')} for c in M.CASES if c['id'] in M.ROUND29_IDS]

    def test_round29_cases(self):
        cases = self.cases()
        self.assertLessEqual(len(cases), 6)
        nums = sorted(int(c['title'].split('.')[0]) for c in cases)
        self.assertEqual(nums, list(range(54, 54 + len(cases))))  # после 53
        self.assertFalse({c['id'] for c in cases} & {c['id'] for c in M.STANDARD_CASES})
        for c in cases:
            self.assertFalse(c.get('bake') or c.get('targets') or c.get('donor') or c.get('gun_copy'), c['id'])
            # одна правка на копию файла (одно поле), ссылки — только на свои копии wtp5t_r29_*
            for stock, copy, edits in c.get('file_copies', []):
                self.assertEqual(len(edits), 1, c['id'])
                self.assertEqual(copy, M.r29_copy(stock))
                self.assertTrue(os.path.basename(copy).startswith(M.PREFIX + 'r29_'))
            copies = {copy for _s, copy, _e in c.get('file_copies', [])}
            relinks = [e for e in c.get('unit_edits', []) if e[1] != e[2] and isinstance(e[2], str)]
            self.assertTrue(all(new in copies for _p, _s, new in relinks), c['id'])
        ctrl = [c for c in cases if c['id'] == 't54_f15_r29_rwr_ctrl'][0]
        self.assertFalse(ctrl.get('unit_edits') or ctrl.get('file_copies'))
        rwr = [c for c in cases if c['id'] == 't55_f15_r29_rwr'][0]
        self.assertEqual(rwr['air_target'], ctrl['air_target'])  # контроль и правка — одна мишень с РЛС

    def test_round29_csv_keys_only_own(self):
        """CSV не переименовывает ничего стокового: все ключи — свои (wtp5t_*), имя файла = mission{name}."""
        for c in self.cases():
            for key, en, ru in c.get('loc_csv', []):
                self.assertIn(M.PREFIX, key, key)
                self.assertTrue(en and ru and '"' not in en + ru)
            if c.get('loc_csv'):
                self.assertEqual(c['mission_file_stem'], M.PREFIX + c['id'])

    def test_merge_overrides(self):
        tree = B.parse_text('a{ b{ x:r=1.0\n} b{ x:r=2.0\n} c:i=1\n}\nd:t="s"')
        text = M.merge_overrides([M.override_path(tree, p, v) for p, v in
                                  (('a/b[1]/x', 5.0), ('a/b[2]/x', 6.0), ('a/c', 7), ('d', 'q'))])
        self.assertEqual(text.count('"@override:a"{'), 1)
        log = []
        res = B.apply_patch(tree, B.parse_text(text), log)
        self.assertEqual(log, [])
        self.assertEqual([b.get('x') for b in res.block('a').blocks], [5.0, 6.0])
        self.assertEqual((res.block('a').get('c'), res.get('d')), (7, 'q'))

    def test_round29_datamine_plan_and_final_values(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round29_datamine(dm)
            cases = self.cases()
            self.assertEqual(M.check_against_datamine(load, cases), [])
            items = M.plan(cases)
            files = dict(items)
            res = M.check_unit_edits(load, items, cases)
            self.assertEqual([p for _r, p, _g in res], [''] * len(res), res)
            got = {r.split('/')[-1]: dict(g) for r, _p, g in res}
            self.assertEqual(got['wtp5t_r29_us_an_alr_56c.blk'], {'range': 7000.0})
            for f in M.R29_AIM9:
                self.assertEqual(got[os.path.basename(M.r29_copy(f))],
                                 {'rocket/guidance/opticalSeeker/rangeMax': 1100.0})
            self.assertEqual(got['wtp5t_f_15c_golden_eagle_r29_flares.blk'],
                             {'WeaponSlots/WeaponSlot[1]/WeaponPreset[1]/Weapon[4]/bullets': 600})
            self.assertEqual(got['wtp5t_r29_88mm_Kwk36_user_cannon.blk'],
                             {'88mm_ger_kwk36_Pzgr_APCBC/bullet/bulletName': M.R29_SHELL})
            self.assertEqual(got['wtp5t_f_15c_golden_eagle_r29_ctrl.blk'], {})
            ir = files['content/pkg_local/gameData/flightModels/wtp5t_f_15c_golden_eagle_r29_ir.blk']
            self.assertEqual(ir.count('"@override:WeaponSlots"{'), 1)  # четыре ссылки — одним блоком
            # СПО — копия только у второй записи, РЛС и остальные стоковые
            log = []
            rwr = B.resolve_file(files['content/pkg_local/gameData/flightModels/wtp5t_f_15c_golden_eagle_r29_rwr.blk'],
                                 load, log)
            self.assertEqual([s.get('blk') for s in rwr.block('sensors').blocks],
                             ['gameData/sensors/us_an_apg_63_v_3.blk', M.r29_copy(M.R29_RWR),
                              'gameData/sensors/LaserDesignatorSensor.blk'])
            for c in cases:
                stem = c.get('mission_file_stem', c['id'])
                mission = B.parse_text(files['%s/%s.blk' % (M.MISSION_DIR, stem)])
                ms = mission.block('mission_settings').block('mission')
                self.assertIn('29-й круг', ms.get('locDesc'))
                units = mission.block('units').blocks
                if c.get('air_target'):
                    self.assertEqual(units[1].get('unit_class'), M.AIR_TARGETS[c['air_target']]['unit_class'])
                if c.get('loc_csv'):
                    self.assertEqual(ms.get('name'), stem)
                    csv = files['%s/usr_%s.csv' % (M.MISSION_DIR, stem)].splitlines()
                    self.assertEqual(csv[0], '"<ID|readonly|noverify>";"<English>";"<Russian>"')
                    self.assertEqual([x.split(';')[0].strip('"') for x in csv[1:]], [k for k, _e, _r in c['loc_csv']])
            tiger = B.parse_text(files['%s/%s.blk' % (M.MISSION_DIR, M.PREFIX + 't58_tiger_r29_names')])
            player, near, far = tiger.block('units').blocks
            self.assertEqual((player.get('bullets0'), player.get('bullets1')),
                             ('88mm_ger_kwk36_Pzgr_APCBC', '88mm_ger_kwk36_APCR'))
            self.assertEqual([near.get('unit_class'), far.get('unit_class')], [M.R28_TIGER] * 2)
            self.assertIn('"weapons/wtp5t_r29_88mm_Kwk36_user_cannon"',
                          files['%s/usr_%s.csv' % (M.MISSION_DIR, M.PREFIX + 't58_tiger_r29_names')])
            # копия орудия 14-й миссии (другой манифест) не перезаписывается — у 29-го круга своё имя
            self.assertNotIn('content/pkg_local/gameData/Weapons/groundModels_weapons/wtp5t_88mm_Kwk36_user_cannon.blk',
                             files)

    def test_round29_refuses_changed_stock(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round29_datamine(dm, rwr_range=80000.0)
            problems = M.check_against_datamine(load, self.cases())
            self.assertTrue(any('us_an_alr_56c' in p and 'range' in p for p in problems), problems)
            with self.assertRaises(AssertionError):
                M.plan([c for c in self.cases() if c['id'] == 't55_f15_r29_rwr'])

    def test_round29_datamine_flag(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as dm:
            _round29_datamine(dm)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(M.main(['--round29', '--datamine', dm]), 0)
            self.assertIn('rangeMax=1100.0', out.getvalue())
            self.assertIn('usr_wtp5t_t58_tiger_r29_names.csv', out.getvalue())
            self.assertNotIn('ОШИБКА', out.getvalue())


def _round30_datamine(dm, rwr_range=70000.0, tor_band=6):
    """Датамайн-заглушка 30-го круга: F-15C (РЛС, СПО), СПО ALR-56C, МиГ-23М и «Тор-М1» с их РЛС — значения aa326f1."""
    import json

    def put(rel, obj):
        full = os.path.join(dm, 'aces.vromfs.bin_u', rel.lower() + 'x')
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            json.dump(obj, f)
    put('gameData/flightModels/%s.blk' % M.R29_F15['unit'], {
        'sensors': {'sensor': [{'blk': 'gameData/sensors/us_an_apg_63_v_3.blk', 'dmPart': 'radar_dm'},
                               {'blk': M.R29_RWR}, {'blk': 'gameData/sensors/LaserDesignatorSensor.blk'}]},
        'weapon_presets': {'preset': [{'name': M.R29_F15['weapons'], 'blk': 'x.blk'}]}})
    put(M.R29_RWR, {'type': 'rwr', 'name': 'AN/ALR-56C', 'range': rwr_range,
                    'band4': True, 'band5': True, 'band6': True, 'band7': True, 'band8': True, 'band9': True})
    put('gameData/sensors/us_an_apg_63_v_3.blk', {'type': 'radar', 'transivers': {'pulse': {'band': 8}}})
    put('gameData/flightModels/mig_23m.blk', {'sensors': {'sensor': [
        {'blk': 'gameData/sensors/su_sapphire_23.blk', 'dmPart': 'radar_dm'}, {'blk': 'gameData/sensors/su_spo-10.blk'}]}})
    put('gameData/sensors/su_sapphire_23.blk', {'type': 'radar', 'name': 'Sapphire-23', 'transivers': {
        'pulse': {'band': 9, 'range': 54000.0}, 'irst': {'band': 1, 'range': 12000.0, 'visibilityType': 'infraRed'}}})
    put('gameData/sensors/su_spo-10.blk', {'type': 'rwr', 'band3': True})
    put('gameData/units/tankModels/cn_tor_m1.blk', {'sensors': {'sensor': [
        {'blk': 'gameData/sensors/su_9k_330_search.blk', 'turretIndex': 0}]}})
    put('gameData/sensors/su_9k_330_search.blk', {'type': 'radar', 'name': '9K330 TA', 'transivers': {
        'search': {'band': tor_band, 'range': 27000.0}}})
    return M.datamine_loader(dm)


class Round30(unittest.TestCase):
    def cases(self):
        return [{k: v for k, v in c.items() if not k.startswith('_')} for c in M.CASES if c['id'] in M.ROUND30_IDS]

    def test_round30_cases(self):
        cases = self.cases()
        self.assertLessEqual(len(cases), 4)
        nums = sorted(int(c['title'].split('.')[0]) for c in cases)
        self.assertEqual(nums, list(range(59, 59 + len(cases))))  # после 58
        self.assertFalse({c['id'] for c in cases} & {c['id'] for c in M.STANDARD_CASES})
        by = {c['id']: c for c in cases}
        # у каждого опыта — излучатель с РЛС; правка отличается от своего контроля только копией СПО
        for ctrl, edit in (('t59_f15_r30_air_ctrl', 't60_f15_r30_air_rwr'), ('t61_f15_r30_sam_ctrl', 't62_f15_r30_sam_rwr')):
            self.assertTrue(M.emitter_unit(by[ctrl]))
            self.assertFalse(by[ctrl].get('unit_edits') or by[ctrl].get('file_copies'))
            self.assertEqual((by[ctrl].get('air_target'), by[ctrl].get('ground_emitter')),
                             (by[edit].get('air_target'), by[edit].get('ground_emitter')))
            self.assertEqual(by[edit]['file_copies'], [(M.R29_RWR, M.r30_copy(M.R29_RWR), [('range', 70000.0, 7000.0)])])
        self.assertTrue(M.AIR_TARGETS[by['t59_f15_r30_air_ctrl']['air_target']].get('radar'))
        # своя копия СПО 30-го круга: копия 29-го круга (другой манифест) не перезаписывается
        self.assertNotEqual(M.r30_copy(M.R29_RWR), M.r29_copy(M.R29_RWR))

    def test_round30_missions_turn_radar_on(self):
        for c in self.cases():
            mission = B.parse_text(M.mission(c, 'x'))
            ms = mission.block('mission_settings').block('mission')
            self.assertIn('30-й круг', ms.get('locDesc'))
            units = mission.block('units').blocks
            emitter = units[1]
            props = emitter.block('props')
            self.assertIs(props.get('use_search_radar'), True)
            self.assertEqual(props.get('army'), 2)
            init = [b for b in mission.block('triggers').blocks[0].block('actions').blocks
                    if b.name == 'unitSetProperties' and b.get('object') == emitter.get('name')]
            self.assertTrue(init and init[0].get('useSearchRadar') is True)
            if c.get('ground_emitter'):
                self.assertEqual((emitter.name, emitter.get('unit_class'), props.get('attack_type')),
                                 ('tankModels', 'cn_tor_m1', 'hold_fire'))
            else:
                # как бот chaff_sky: стрелять не даёт cannotShoot, а не dont_aim
                self.assertEqual((emitter.name, emitter.get('unit_class'), props.get('attack_type')),
                                 ('armada', 'mig_23m', 'fire_at_will'))
                self.assertIs(init[0].get('cannotShoot'), True)

    def test_earlier_air_targets_unchanged(self):
        """Миссии 41 и 54 уже установлены: у мишеней без radar — прежние dont_aim и нет use_search_radar."""
        for cid in ('t41_f15_r26_ctrl', 't54_f15_r29_rwr_ctrl'):
            c = [x for x in M.CASES if x['id'] == cid][0]
            text = M.mission(c, 'x')
            self.assertNotIn('use_search_radar', text)
            self.assertNotIn('useSearchRadar', text)
            self.assertIn('attack_type:t="dont_aim"', text)

    def test_round30_datamine_plan_and_final_values(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round30_datamine(dm)
            cases = self.cases()
            self.assertEqual(M.check_against_datamine(load, cases), [])
            items = M.plan(cases)
            files = dict(items)
            # одна копия СПО и две копии F-15C (контроль и правка) на четыре миссии
            self.assertEqual(sorted(r for r in files if r.startswith('content/')),
                             ['content/pkg_local/gameData/flightModels/wtp5t_f_15c_golden_eagle_r30_ctrl.blk',
                              'content/pkg_local/gameData/flightModels/wtp5t_f_15c_golden_eagle_r30_rwr.blk',
                              'content/pkg_local/' + M.r30_copy(M.R29_RWR)])
            self.assertFalse([r for r in files if r.endswith('.csv')])  # названий нет — перезапуск игры не нужен
            res = M.check_unit_edits(load, items, cases)
            self.assertEqual([p for _r, p, _g in res], [''] * len(res), res)
            got = {r.split('/')[-1]: dict(g) for r, _p, g in res}
            self.assertEqual(got['wtp5t_r30_us_an_alr_56c.blk'], {'range': 7000.0})
            self.assertEqual(got['wtp5t_f_15c_golden_eagle_r30_ctrl.blk'], {})
            log = []
            rwr = B.resolve_file(files['content/pkg_local/gameData/flightModels/wtp5t_f_15c_golden_eagle_r30_rwr.blk'],
                                 load, log)
            self.assertEqual(log, [])
            self.assertEqual([s.get('blk') for s in rwr.block('sensors').blocks],
                             ['gameData/sensors/us_an_apg_63_v_3.blk', M.r30_copy(M.R29_RWR),
                              'gameData/sensors/LaserDesignatorSensor.blk'])

    def test_round30_refuses_bad_stock(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round30_datamine(dm, rwr_range=80000.0)
            problems = M.check_against_datamine(load, self.cases())
            self.assertTrue(any('us_an_alr_56c' in p and 'range' in p for p in problems), problems)
        with tempfile.TemporaryDirectory() as dm:
            # РЛС «Тора» в диапазоне, которого СПО не слышит, — излучатель бесполезен, отказ
            load = _round30_datamine(dm, tor_band=2)
            problems = M.check_against_datamine(load, self.cases())
            self.assertTrue(any('t61_' in p and 'не слышит' in p for p in problems), problems)
            self.assertFalse(any('t59_' in p for p in problems), problems)

    def test_round30_datamine_flag(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as dm:
            _round30_datamine(dm)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(M.main(['--round30', '--datamine', dm]), 0)
            self.assertIn('range=7000.0', out.getvalue())
            self.assertNotIn('ОШИБКА', out.getvalue())


def _round31_datamine(dm, empty=10332.0, fab_cx=0.154, fab_mass=9407.0):
    """Датамайн-заглушка 31-го круга: A-26B (слот 4, вариант 1000lbs_int), его ЛМ и ФАБ-9000 — значения aa326f1."""
    import json

    def put(rel, obj):
        full = os.path.join(dm, 'aces.vromfs.bin_u', rel.lower() + 'x')
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            json.dump(obj, f)
    bomb = {'trigger': 'bombs', 'blk': 'gameData/Weapons/BombGuns/us_1000lb_anm65a1.blk', 'bullets': 1, 'machLimit': 1.01}
    put('gameData/flightModels/a-26b.blk', {
        'fmFile': 'fm/a-26b.blk',
        'WeaponSlots': {'maxloadMass': 2500.0, 'WeaponSlot': [
            {'index': 0}, {'index': 1}, {'index': 2}, {'index': 3},
            {'index': 4, 'WeaponPreset': [{'name': '1000lbs_int', 'reqModification': 'btd_mbc', 'Weapon': [
                dict(bomb, emitter='bomb1000lb%d' % i) for i in range(1, 5)]}]}]},
        'weapon_presets': {'preset': [{'name': 'a_26b_default', 'blk': 'x.blk'}]}})
    put('gameData/flightModels/fm/a-26b.blk', {'Mass': {'EmptyMass': empty, 'Takeoff': 18324.0, 'AdvancedMass': False},
                                               'MomentOfInertia': [96673.0, 68912.0, 60245.0]})
    put(M.R31_FAB, {'bombGun': True, 'external': True, 'bomb': {'mass': fab_mass, 'caliber': 1.2, 'dragCx': fab_cx}})
    put('gameData/Weapons/BombGuns/us_1000lb_anm65a1.blk', {'bomb': {'mass': 500.76, 'dragCx': 0.042}})
    return M.datamine_loader(dm)


class Round31(unittest.TestCase):
    def cases(self):
        return [{k: v for k, v in c.items() if not k.startswith('_')} for c in M.CASES if c['id'] in M.ROUND31_IDS]

    def test_round31_cases(self):
        cases = self.cases()
        self.assertLessEqual(len(cases), 4)
        nums = sorted(int(c['title'].split('.')[0]) for c in cases)
        self.assertEqual(nums, list(range(63, 63 + len(cases))))  # после 62
        self.assertFalse({c['id'] for c in cases} & {c['id'] for c in M.STANDARD_CASES})
        by = {c['id']: c for c in cases}
        ctrl = by['t63_a26_r31_ctrl']
        self.assertFalse(ctrl.get('loadout') or ctrl.get('file_copies') or ctrl.get('weapons'))
        # все опыты — одна точка старта и самолёт; 65 и 66 отличаются от 64 одной правкой
        self.assertEqual({(c['unit'], c['spawn']) for c in cases}, {('a-26b', 'firing_range_air')})
        self.assertEqual(len({c.get('suffix') for c in cases}), 4)
        comp = by['t64_a26_r31_comp']
        self.assertEqual(comp['file_copies'], [M.R31_FM])
        self.assertEqual(by['t65_a26_r31_bombcx']['file_copies'], [M.R31_FM, M.R31_BOMB])
        self.assertEqual(by['t66_a26_r31_wcx']['file_copies'], [M.R31_FM])
        variants = {v[2]: v for v in M.AIR_LOADOUTS['A26_R31']['variants']}
        self.assertEqual(variants['wtp5t_r31_fab_bay'][3:], (M.R31_FAB, 1))
        self.assertEqual(variants['wtp5t_r31_fab_cx_bay'][3:], (M.R31_FAB_CX, 1))
        self.assertEqual(variants['wtp5t_r31_fab_wcx_bay'][3:], (M.R31_FAB, 1, [('dragCx', 'r', 0.2)]))
        # правки ×10, не ноль; масса бомбы и ЛМ — как в 32-й
        self.assertEqual(M.R31_BOMB[2], [('bomb/dragCx', 0.154, 1.54)])
        self.assertEqual(M.R31_FM[2], [('Mass/EmptyMass', 10332.0, 925.0)])

    def test_round31_datamine_plan_and_final_values(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round31_datamine(dm)
            cases = self.cases()
            self.assertEqual(M.check_against_datamine(load, cases), [])
            items = M.plan(cases)
            files = dict(items)
            content = sorted(r for r in files if r.startswith('content/'))
            pre = 'content/pkg_local/gameData/'
            self.assertEqual(content, sorted(
                [pre + 'FlightModels/weaponPresets/wtp5t_a-26b_r31_%s.blk' % n for n in ('fab', 'fab_cx', 'fab_wcx')]
                + [pre + 'Weapons/BombGuns/wtp5t_r31_su_fab9000_cx.blk',
                   pre + 'flightModels/fm/wtp5t_a-26b_r31_comp.blk']
                + [pre + 'flightModels/wtp5t_a-26b_r31_%s.blk' % s for s in ('ctrl', 'comp', 'bombcx', 'wcx')]))
            self.assertNotIn('@override', files[pre + 'flightModels/wtp5t_a-26b_r31_ctrl.blk'])
            res = M.check_unit_edits(load, items, cases)
            self.assertEqual([p for _r, p, _g in res], [''] * len(res), res)
            got = {r.split('/')[-1]: dict(g) for r, _p, g in res}
            self.assertEqual(got, {'wtp5t_a-26b_r31_comp.blk': {'Mass/EmptyMass': 925.0},
                                   'wtp5t_r31_su_fab9000_cx.blk': {'bomb/dragCx': 1.54}})
            for suffix, preset, blk, cx in (('comp', 'wtp5t_r31_fab', M.R31_FAB, None),
                                            ('bombcx', 'wtp5t_r31_fab_cx', M.R31_FAB_CX, None),
                                            ('wcx', 'wtp5t_r31_fab_wcx', M.R31_FAB, 0.2)):
                log = []
                u = B.resolve_file(files[pre + 'flightModels/wtp5t_a-26b_r31_%s.blk' % suffix], load, log)
                self.assertEqual(log, [])
                self.assertEqual(u.get('fmFile'), 'fm/wtp5t_a-26b_r31_comp.blk')
                pfile = [p.get('blk') for p in u.block('weapon_presets').blocks if p.get('name') == preset][0]
                bay = B.parse_text(files['content/pkg_local/' + pfile]).block('Weapon').get('preset')
                slot = [s for s in u.block('WeaponSlots').blocks if s.name == 'WeaponSlot' and s.get('index') == 4][0]
                v = [p for p in slot.blocks if p.get('name') == bay][0]
                weapons = [w for w in v.blocks if w.name == 'Weapon']
                self.assertEqual(len(weapons), 1)  # одна ФАБ по центру
                self.assertEqual((weapons[0].get('blk'), weapons[0].get('dragCx')), (blk, cx))
                self.assertIsNone(v.get('reqModification'))
                mission = B.parse_text(M.mission([c for c in cases if c.get('weapons') == preset][0], 'x'))
                self.assertIn('31-й круг', mission.block('mission_settings').block('mission').get('locDesc'))
            # стоковые файлы ФАБ и ЛМ не меняются: копии — только wtp5t_
            self.assertFalse([r for r in content if not os.path.basename(r).startswith('wtp5t_')])

    def test_round31_refuses_changed_stock(self):
        for kw, needle in (({'fab_cx': 0.16}, 'dragCx'), ({'empty': 10400.0}, 'EmptyMass'),
                           ({'fab_mass': 9000.0}, 'подвеска')):
            with tempfile.TemporaryDirectory() as dm:
                load = _round31_datamine(dm, **kw)
                problems = M.check_against_datamine(load, self.cases())
                self.assertTrue(any(needle in p for p in problems), (kw, problems))
                self.assertFalse(any('t63_' in p for p in problems), problems)

    def test_air_loadout_refuses_existing_weapon_param(self):
        u = B.parse_text('WeaponSlots{\nWeaponSlot{\nindex:i=1\nWeaponPreset{\nname:t="b"\nWeapon{\n'
                         'blk:t="w.blk"\ndragCx:r=0.02\n}\n}\n}\n}\n')
        cfg = {'variants': [(1, 'b', 'wtp5t_x', 'w2.blk', 1, [('dragCx', 'r', 0.2)])], 'presets': {}}
        _files, _unit, problems = M.air_loadout(u, cfg, 'plane')
        self.assertTrue(problems)

    def test_round31_datamine_flag(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as dm:
            _round31_datamine(dm)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(M.main(['--round31', '--datamine', dm]), 0)
            self.assertIn('Mass/EmptyMass=925.0', out.getvalue())
            self.assertIn('bomb/dragCx=1.54', out.getvalue())
            self.assertNotIn('ОШИБКА', out.getvalue())


def _round32_datamine(dm, sample='aim_9l_default', rocket=True):
    """Датамайн-заглушка 32-го круга: F-15C (пилон 1, вариант aim_9l_default) и две ЗУР в наземном формате."""
    import json

    def put(rel, obj):
        full = os.path.join(dm, 'aces.vromfs.bin_u', rel.lower() + 'x')
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            json.dump(obj, f)
    put('gameData/flightModels/f_15c_golden_eagle.blk', {
        'fmFile': 'fm/f_15c_golden_eagle.blk',
        'WeaponSlots': {'WeaponSlot': [{'index': 0}, {'index': 1, 'WeaponPreset': [
            {'name': sample, 'iconType': 'missile_type_b_air_to_air',
             'Weapon': {'trigger': 'aam', 'external': True,
                        'blk': 'gameData/Weapons/rocketGuns/us_aim9l_sidewinder_default.blk',
                        'emitter': 'aim_9_001', 'bullets': 1}}]}]},
        'weapon_presets': {'preset': [{'name': 'f_15c_golden_eagle_default', 'blk': 'x.blk'}]}})
    put('gameData/flightModels/mig-15bis_ns23.blk', {'fmFile': 'fm/mig-15bis.blk'})
    for path, mesh, guidance in ((M.R32_SAM_9X, 'us_aim_9x_sidewinder', {'irSeeker': {'rangeMax': 11000.0}}),
                                 (M.R32_SAM_95, '57e6_rocket', {'guidanceType': 'saclos'})):
        bullet = {'bulletName': 'x', 'rocket': {'mesh': mesh, 'mass': 75.0, 'guidance': guidance}} if rocket else \
            {'bulletName': 'x', 'mass': 1.0}
        put(path, {'cannon': True, 'bullets': 4, 'mesh': mesh, 'bullet': bullet})
    return M.datamine_loader(dm)


class Round32(unittest.TestCase):
    def cases(self):
        return [{k: v for k, v in c.items() if not k.startswith('_')} for c in M.CASES if c['id'] in M.ROUND32_IDS]

    def test_round32_cases(self):
        cases = self.cases()
        nums = sorted(int(c['title'].split('.')[0]) for c in cases)
        self.assertEqual(nums, [67, 68, 69])  # после 66
        self.assertFalse({c['id'] for c in cases} & {c['id'] for c in M.STANDARD_CASES})
        self.assertEqual({(c['unit'], c['air_target']) for c in cases}, {('f_15c_golden_eagle', 'r32_mig15_5km')})
        self.assertEqual(len({c['suffix'] for c in cases}), 3)
        for c in cases:   # у каждой миссии — только свой вариант пилона 1
            variants = M.AIR_LOADOUTS[c['loadout']]['variants']
            self.assertEqual(len(variants), 1)
            self.assertEqual(variants[0][:3], (1, 'aim_9l_default', c['weapons']))

    def test_round32_datamine_plan(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round32_datamine(dm)
            cases = self.cases()
            self.assertEqual(M.check_against_datamine(load, cases), [])
            files = dict(M.plan(cases))
            pre = 'content/pkg_local/gameData/'
            self.assertFalse([r for r in files if r.startswith('content/')
                              and not os.path.basename(r).startswith('wtp5t_')])
            for stock, mesh in ((M.R32_SAM_95, '57e6_rocket'), (M.R32_SAM_9X, 'us_aim_9x_sidewinder')):
                air = B.parse_text(files['content/pkg_local/' + M.r32_air(stock)])
                self.assertTrue(air.get('rocketGun'))
                self.assertIsNone(air.get('cannon'))
                self.assertEqual((air.get('bullets'), air.get('mesh')), (1, mesh))
                self.assertEqual(air.block('rocket').get('mass'), 75.0)
                self.assertIsNotNone(air.block('rocket').block('guidance'))
            for c in cases:
                log = []
                u = B.resolve_file(files[pre + 'flightModels/wtp5t_f_15c_golden_eagle%s.blk' % c['suffix']], load, log)
                self.assertEqual(log, [])
                slot = [s for s in u.block('WeaponSlots').blocks if s.name == 'WeaponSlot' and s.get('index') == 1][0]
                v = [p for p in slot.blocks if p.get('name') == c['weapons']][0]
                weapons = [w for w in v.blocks if w.name == 'Weapon']
                self.assertEqual(len(weapons), 1)
                want = M.R32_SAM_9X if c['id'].endswith('_raw') else M.r32_air(
                    M.R32_SAM_95 if '95' in c['id'] else M.R32_SAM_9X)
                self.assertEqual(weapons[0].get('blk'), want)
                # в копии — только варианты, заданные этим пунктом
                ours = [p.get('name') for s in u.block('WeaponSlots').blocks if s.name == 'WeaponSlot'
                        for p in s.blocks if p.name == 'WeaponPreset' and str(p.get('name')).startswith('wtp5t_')]
                self.assertEqual(ours, [c['weapons']])

    def test_round32_refuses_sam_without_rocket(self):
        with tempfile.TemporaryDirectory() as dm:
            load = _round32_datamine(dm, rocket=False)
            problems = M.check_against_datamine(load, self.cases())
            self.assertTrue(any('t68_' in p for p in problems), problems)
            self.assertTrue(any('t69_' in p for p in problems), problems)

    def test_round32_datamine_flag(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as dm:
            _round32_datamine(dm)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(M.main(['--round32', '--datamine', dm]), 0)
            self.assertIn('wtp5t_r32_170mm_57e6m_launcher_user_cannon_air.blk', out.getvalue())
            self.assertNotIn('ОШИБКА', out.getvalue())


class Safety(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.game = os.path.join(self.tmp.name, 'game')
        self.app = os.path.join(self.tmp.name, 'app')
        self.items = M.plan(M.STANDARD_CASES)

    def tearDown(self):
        self.tmp.cleanup()

    def test_write_then_idempotent_then_remove(self):
        ok, rep = M.write(self.game, self.items, self.app)
        self.assertTrue(ok)
        self.assertTrue(all(s.startswith('создам') for s in rep))
        ok, rep = M.write(self.game, self.items, self.app)
        self.assertTrue(ok)
        self.assertTrue(all(s.startswith('без изменений') for s in rep))
        rep = M.remove(self.game, self.app)
        self.assertTrue(all(s.startswith('удалён') for s in rep))
        for rel, _ in self.items:
            self.assertFalse(os.path.exists(os.path.join(self.game, rel)))

    def test_foreign_file_blocks_everything(self):
        rel = self.items[0][0]
        full = os.path.join(self.game, rel)
        os.makedirs(os.path.dirname(full))
        with open(full, 'w') as f:
            f.write('чужое')
        ok, rep = M.write(self.game, self.items, self.app)
        self.assertFalse(ok)
        self.assertIn('чужой', rep[0])
        with open(full) as f:
            self.assertEqual(f.read(), 'чужое')
        self.assertEqual(sum(os.path.exists(os.path.join(self.game, r)) for r, _ in self.items), 1)

    def test_changed_own_file_is_kept(self):
        M.write(self.game, self.items, self.app)
        rel = self.items[0][0]
        with open(os.path.join(self.game, rel), 'a') as f:
            f.write('// правка руками\n')
        ok, _ = M.write(self.game, self.items, self.app)
        self.assertFalse(ok)
        rep = M.remove(self.game, self.app)
        self.assertTrue(any('оставляю' in s for s in rep))
        self.assertTrue(os.path.exists(os.path.join(self.game, rel)))

    def test_dropped_own_files_removed_with_backup(self):
        M.write(self.game, self.items, self.app)
        dropped, kept = self.items[0][0], self.items[1:]
        ok, rep = M.write(self.game, kept, self.app)
        self.assertTrue(ok)
        self.assertTrue(any(s.startswith('уберу') and s.endswith(dropped) for s in rep))
        self.assertFalse(os.path.exists(os.path.join(self.game, dropped)))
        self.assertNotIn(dropped, M.load_manifest(self.app)['files'])
        baks = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(self.app, 'backups')) for f in fs]
        self.assertEqual(len(baks), 1)

    def test_dropped_but_changed_file_is_kept(self):
        M.write(self.game, self.items, self.app)
        dropped = self.items[0][0]
        with open(os.path.join(self.game, dropped), 'a') as f:
            f.write('// правка руками\n')
        ok, rep = M.write(self.game, self.items[1:], self.app)
        self.assertTrue(ok)
        self.assertTrue(any('оставляю' in s for s in rep))
        self.assertTrue(os.path.exists(os.path.join(self.game, dropped)))

    def test_update_makes_backup(self):
        M.write(self.game, self.items, self.app)
        changed = [(r, t + '// v2\n') if i == 0 else (r, t) for i, (r, t) in enumerate(self.items)]
        ok, rep = M.write(self.game, changed, self.app)
        self.assertTrue(ok)
        self.assertTrue(rep[0].startswith('обновлю'))
        baks = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(self.app, 'backups')) for f in fs]
        self.assertEqual(len(baks), 1)

    def test_adopt_exact_file_and_restore_original(self):
        rel = M.ROUND22_ADOPT_PATH
        full = os.path.join(self.game, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        original = b'project generated original\n'
        with open(full, 'wb') as f:
            f.write(original)
        ok, _man, _report = M.adopt_exact(self.game, self.app, rel, original)
        self.assertTrue(ok)
        ok, _report = M.write(self.game, [(rel, 'new helicopter preset\n')], self.app)
        self.assertTrue(ok)
        with open(full, 'rb') as f:
            self.assertEqual(f.read(), b'new helicopter preset\n')
        report = M.remove(self.game, self.app)
        self.assertTrue(any('восстановлен исходный файл' in s for s in report))
        with open(full, 'rb') as f:
            self.assertEqual(f.read(), original)

    def test_adopt_refuses_different_or_changed_file(self):
        rel = M.ROUND22_ADOPT_PATH
        full = os.path.join(self.game, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'wb') as f:
            f.write(b'changed by someone\n')
        ok, _man, _report = M.adopt_exact(self.game, self.app, rel, b'original\n')
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(os.path.join(self.app, 'manifest.json')))

    def test_adopted_file_changed_after_install_is_not_restored(self):
        rel = M.ROUND22_ADOPT_PATH
        full = os.path.join(self.game, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'wb') as f:
            f.write(b'original\n')
        ok, _man, _report = M.adopt_exact(self.game, self.app, rel, b'original\n')
        self.assertTrue(ok)
        ok, _report = M.write(self.game, [(rel, 'generated update\n')], self.app)
        self.assertTrue(ok)
        with open(full, 'wb') as f:
            f.write(b'user edited\n')
        report = M.remove(self.game, self.app)
        self.assertTrue(any('изменён после записи, оставляю' in s for s in report))
        with open(full, 'rb') as f:
            self.assertEqual(f.read(), b'user edited\n')


if __name__ == '__main__':
    unittest.main()
