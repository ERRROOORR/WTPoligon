"""Разделы, пересчёт и границы характеристик без Qt."""
import os
import json
import tempfile
import unittest

from wtpoligon import stats as S
from wtpoligon import build as BL
from wtpoligon import loadout as L
from wtpoligon.game import blk as B


UNIT = 'gameData/flightModels/example.blk'
FM = 'gameData/flightModels/fm/example.blk'
RADAR = 'gameData/sensors/radar.blk'
RWR = 'gameData/sensors/rwr.blk'


class Source:
    def __init__(self, files):
        self.files = {k.lower(): B.parse_text(v) for k, v in files.items()}

    def load(self, path):
        return self.files.get(path.lower())

    def signature(self):
        return 'test'


class TestStats(unittest.TestCase):
    def setUp(self):
        self.source = Source({
            UNIT: '''fmFile:t="fm/example.blk"
                sensors{sensor{blk:t="gameData/sensors/radar.blk"}
                        sensor{blk:t="gameData/sensors/rwr.blk"}}
                WeaponSlots{WeaponSlot{WeaponPreset{Weapon{trigger:t="countermeasures"\n bullets:i=60}}}}''',
            FM: '''Mass{EmptyMass:r=1000\n Takeoff:r=2000\n}
                   EngineType0{Main{Power:r=100\n} Compressor{Power0:r=110\n}}
                   EngineType1{Main{Power:r=200\n} Compressor{Power0:r=220\n}}''',
            RADAR: '''type:t="radar"\n transivers{search{range:r=90000\n scanAngle:r=60\n
                       beamWidth:r=3\n angles:p2=10,20\n enabled:b=yes\n}}''',
            RWR: '''type:t="rwr"\n range:r=70000''',
        })
        self.vehicle = {'name': 'a-26b_example', 'file': UNIT, 'kind': 'air'}
        self.model = S.Stats(self.source, self.vehicle)

    def test_sections_only_from_existing_paths(self):
        self.assertEqual(self.model.sections(),
                         ['Двигатель', 'Масса', 'РЛС', 'СПО', 'Ловушки', 'Название'])
        radar = {p.path: p for p in self.model.params if p.section == 'РЛС'}
        self.assertEqual(radar['transivers/search/range'].status, 'проверено в игре')
        self.assertEqual(radar['transivers/search/range'].unit, 'км')
        self.assertEqual(self.model.display(radar['transivers/search/range']), 90)
        for path in ('transivers/search/scanAngle', 'transivers/search/beamWidth',
                     'transivers/search/angles', 'transivers/search/enabled'):
            self.assertEqual(radar[path].status, 'не проверено в игре')
        self.assertEqual([p.path for p in self.model.for_section('РЛС')],
                         ['transivers/search/range'])
        self.assertNotIn('Аэродинамика', self.model.sections())
        no_radar = Source({UNIT: 'fmFile:t="fm/example.blk"', FM: 'Mass{EmptyMass:r=1000}'})
        self.assertNotIn('РЛС', S.Stats(no_radar, self.vehicle).sections())

    def test_general_and_tree_share_values(self):
        self.assertEqual(self.model.general('Двигатель'), 300)
        self.model.set_general('Двигатель', 600)
        self.assertEqual([self.model.display(p) for p in self.model.for_section('Двигатель')
                          if p.path.endswith('/Main/Power')], [200, 400])
        self.model.set_leaf(FM, 'EngineType0/Main/Power', '150')
        self.assertEqual(self.model.general('Двигатель'), 550)
        self.model.reset('Двигатель')
        self.assertEqual(self.model.general('Двигатель'), 300)
        self.assertFalse(self.model.edits())

    def test_bounds_and_types(self):
        mass = next(p for p in self.model.for_section('Масса') if p.path.endswith('EmptyMass'))
        with self.assertRaises(ValueError):
            self.model.set(mass, 0)
        count = self.model.trap_rows()[0]
        with self.assertRaises(ValueError):
            self.model.set(count, -1)
        with self.assertRaises(ValueError):
            self.model.set(count, 1.5)
        self.model.set_leaf(RADAR, 'transivers/search/angles', '(15, 25)')
        self.model.set_leaf(RADAR, 'transivers/search/enabled', 'false')
        self.assertEqual(self.model.values[(RADAR, 'transivers/search/angles')], (15.0, 25.0))
        self.assertFalse(self.model.values[(RADAR, 'transivers/search/enabled')])

    def test_ranges_from_stock_and_cache(self):
        params = self.model.for_section('Двигатель')
        with tempfile.TemporaryDirectory() as cache:
            result = S.ranges(self.source, [self.vehicle], 'air', params, cache)
            self.assertEqual(result['EngineType0/Main/Power'], [100, 200])
            self.assertTrue(os.path.isfile(os.path.join(cache, 'stats_ranges.json')))

    def test_shared_jet_engine_type_counts_both_physical_engines(self):
        source = Source({
            UNIT: 'fmFile:t="fm/example.blk"',
            FM: '''EngineType0{Main{Type:t="Jet" Power:r=1200
                    Thrust:r=2200
                    ThrustMax{ThrustMax0:r=6225
                    ThrAftMaxCoeff_0_0:r=1.1}}}
                    Engine0{Type:i=0}
                    Engine1{Type:i=0}''',
        })
        model = S.Stats(source, self.vehicle)
        rows = [p for p in model.params if p.section == 'Двигатель']
        self.assertEqual(model.engine_mode, 'thrust')
        self.assertEqual(model.engine_instances, [(1, 'EngineType0', [1, 2]),
                                                  (2, 'EngineType0', [1, 2])])
        self.assertFalse(any(p.path.endswith('/Power') for p in rows))
        self.assertIn('Двигатель', model.sections())
        self.assertEqual([p.path for p in model.for_section('Двигатель')],
                         ['EngineType0/Main/ThrustMax/ThrustMax0'])
        self.assertEqual(model.general('Двигатель'), 12450)
        self.assertEqual(model.engine_total(True), None)
        model.set_general('Двигатель', 15000)
        self.assertEqual(model.general('Двигатель'), 15000)
        self.assertEqual(len(model.edits()), 1)
        model.reset('Двигатель')
        model.set_leaf(FM, 'EngineType0/Main/ThrustMax/ThrustMax0', '7500')
        self.assertEqual(len(model.edits()), 1)

    def test_countermeasures_follow_selected_variants_and_type(self):
        from wtpoligon.loadout import Loadout
        source = Source({
            UNIT: '''fmFile:t="fm/example.blk"
                WeaponSlots{
                  WeaponSlot{slot:i=0
                    WeaponPreset{name:t="common" Weapon{trigger:t="countermeasures"
                      blk:t="gameData/weapons/rocketguns/flare.blk" bullets:i=60}}}
                  WeaponSlot{slot:i=1
                    WeaponPreset{name:t="plain" Weapon{trigger:t="countermeasures"
                      blk:t="gameData/weapons/rocketguns/chaff.blk" bullets:i=20}}
                    WeaponPreset{name:t="bol" Weapon{trigger:t="countermeasures"
                      blk:t="gameData/weapons/rocketguns/chaff.blk" bullets:i=160}}}}''',
            FM: 'Mass{EmptyMass:r=1000}',
            'gameData/weapons/rocketguns/flare.blk': 'bullet{bulletType:t="flr"}',
            'gameData/weapons/rocketguns/chaff.blk': 'bullet{bulletType:t="chff"}',
        })
        model = S.Stats(source, self.vehicle, Loadout(slots={1: {'variant': 'plain'}}))
        rows = model.trap_rows()
        self.assertEqual([p.stock for p in rows], [60, 20])
        self.assertEqual(model.trap_totals(), {'Всего зарядов': 80, 'В подвесных контейнерах': 20})
        self.assertEqual(model.trap_split(), (60, 20))
        self.assertEqual(model.for_section('Ловушки'), [])
        model.set_general('Ловушки', 160)
        self.assertEqual([model.value(p) for p in rows], [120, 40])
        self.assertEqual(len(model.edits()), 2)

    def test_jet_afterburner_shared_type_edits_once(self):
        source = Source({UNIT: 'fmFile:t="fm/example.blk"',
                         FM: '''EngineType0{Main{Type:t="Jet" AfterburnerBoost:r=1.1
                           ThrustMax{ThrustMax0:r=6225
                           ThrustMaxCoeff_0_0:r=1
                           ThrAftMaxCoeff_0_0:r=1}}}
                           Engine0{Type:i=0} Engine1{Type:i=0}'''})
        model = S.Stats(source, self.vehicle)
        self.assertEqual(model.engine_total(), 12450)
        self.assertAlmostEqual(model.engine_total(True), 13695)
        model.set_engine('EngineType0', 7500, True)
        self.assertAlmostEqual(model.engine_total(True), 15000)
        self.assertEqual(len(model.edits()), 1)
        model.set_engine_total(18000, True)
        self.assertAlmostEqual(model.engine_total(True), 18000)
        self.assertEqual(len(model.edits()), 1)

    def test_split_launchers_and_pylon_container(self):
        source = Source({UNIT: '''fmFile:t="fm/example.blk"
            WeaponSlots{
              WeaponSlot{index:i=0
                WeaponPreset{name:t="common"
                  Weapon{trigger:t="countermeasures"
                    blk:t="gameData/weapons/rocketguns/countermeasure_split_launcher.blk"
                    bullets:i=60}
                  Weapon{trigger:t="countermeasures"
                    blk:t="gameData/weapons/rocketguns/countermeasure_split_launcher.blk"
                    bullets:i=60}
                  Weapon{trigger:t="countermeasures"
                    blk:t="gameData/weapons/rocketguns/countermeasure_split_launcher.blk"
                    bullets:i=30}
                  Weapon{trigger:t="countermeasures"
                    blk:t="gameData/weapons/rocketguns/countermeasure_split_launcher.blk"
                    bullets:i=30}}}
              WeaponSlot{index:i=1
                WeaponPreset{name:t="empty"}
                WeaponPreset{name:t="pod"
                  Weapon{trigger:t="countermeasures"
                    blk:t="gameData/weapons/rocketguns/chaff.blk"
                    bullets:i=40}}}}''',
                         FM: 'Mass{EmptyMass:r=1000}',
                         'gameData/weapons/rocketguns/countermeasure_split_launcher.blk': '',
                         'gameData/weapons/rocketguns/chaff.blk': 'bullet{bulletType:t="chff"}'})
        bare = S.Stats(source, self.vehicle, L.Loadout(slots={1: {'variant': 'empty'}}))
        self.assertEqual(bare.trap_totals()['Всего зарядов'], 180)
        self.assertEqual(bare.trap_split((1, 1)), (90, 90))
        self.assertEqual(bare.trap_split((2, 1)), (120, 60))
        with_pod = S.Stats(source, self.vehicle, L.Loadout(slots={1: {'variant': 'pod'}}))
        self.assertEqual(with_pod.trap_totals(), {'Всего зарядов': 220, 'В подвесных контейнерах': 40})
        self.assertEqual(with_pod.trap_split((1, 1)), (90, 130))
        with_pod.set_trap_total(440)
        self.assertEqual(with_pod.trap_totals()['Всего зарядов'], 440)

    def test_radar_general_scales_all_ranges_including_receiver(self):
        source = Source({UNIT: 'fmFile:t="fm/example.blk" sensors{sensor{blk:t="gameData/sensors/radar.blk"}}',
                         FM: 'Mass{EmptyMass:r=1000}',
                         RADAR: '''type:t="radar" transivers{
                           search{range:r=90000
                             receiver{range:r=45000}}
                           track{range:r=30000
                             receiver{range:r=15000}}}'''})
        model = S.Stats(source, self.vehicle)
        self.assertEqual(len(model.for_section('РЛС')), 1)
        self.assertEqual(model.general('РЛС'), 90)
        model.set_general('РЛС', 180)
        self.assertEqual(model.general('РЛС'), 180)
        self.assertEqual({p.path: model.value(p) for p in model.params if p.section == 'РЛС'},
                         {'transivers/search/range': 180000,
                          'transivers/search/receiver/range': 90000,
                          'transivers/track/range': 60000,
                          'transivers/track/receiver/range': 30000})
        self.assertEqual(len(model.edits()), 4)

    def test_radar_angles_and_split_antenna(self):
        source = Source({UNIT: 'fmFile:t="fm/example.blk" sensors{sensor{blk:t="gameData/sensors/radar.blk"}}',
                         FM: 'Mass{EmptyMass:r=1000}',
                         RADAR: '''type:t="radar" scanPatterns{
                           searchWide{azimuthLimits:p2=-60,60
                             elevationLimits:p2=-30,30
                             width:r=100
                             barHeight:r=20
                             barsCount:i=4}
                           searchNarrow{azimuthLimits:p2=-30,30
                             elevationLimits:p2=-15,15
                             width:r=50
                             barHeight:r=10
                             barsCount:i=2}
                           track{azimuthLimits:p2=-10,10
                             elevationLimits:p2=-8,8
                             width:r=10}}
                           transivers{mprf{antenna{azimuth{angleHalfSens:r=3.5}
                             elevation{angleHalfSens:r=4.8}}}
                             track{antenna{angleHalfSens:r=2}}}'''} )
        model = S.Stats(source, self.vehicle)
        self.assertEqual(model.radar_general('azimuth'), 60)
        self.assertEqual(model.radar_general('elevation'), 30)
        self.assertEqual(model.radar_general('beam'), 4.8)
        model.set_radar_general('azimuth', 20)
        model.set_radar_general('elevation', 10)
        model.set_radar_general('beam', 9.6)
        values = {p.path: model.value(p) for p in model.params if p.section == 'РЛС'}
        self.assertEqual(values['scanPatterns/searchWide/azimuthLimits'], (-20, 20))
        self.assertEqual(values['scanPatterns/searchNarrow/azimuthLimits'], (-10, 10))
        self.assertEqual(values['scanPatterns/track/azimuthLimits'], (-10, 10))
        self.assertEqual(values['scanPatterns/searchWide/width'], 40)
        self.assertEqual(values['scanPatterns/searchWide/elevationLimits'], (-10, 10))
        self.assertEqual(values['scanPatterns/searchWide/barHeight'], 5)
        self.assertAlmostEqual(values['transivers/mprf/antenna/azimuth/angleHalfSens'], 7)
        self.assertEqual(values['transivers/mprf/antenna/elevation/angleHalfSens'], 9.6)
        self.assertEqual(values['transivers/track/antenna/angleHalfSens'], 4)
        before = model.values.copy()
        for metric, bad in (('azimuth', 181), ('elevation', 91), ('beam', 0)):
            with self.assertRaises(ValueError):
                model.set_radar_general(metric, bad)
        self.assertEqual(model.values, before)
        with self.assertRaises(ValueError):
            model.set_leaf(RADAR, 'scanPatterns/searchWide/azimuthLimits', '(-200, 200)')
        model.reset('РЛС')
        self.assertEqual(model.radar_general('azimuth'), 60)
        self.assertFalse(model.edits())
        with tempfile.TemporaryDirectory() as cache:
            limits = S.radar_ranges(source, [self.vehicle], 'air', cache)
            self.assertEqual(limits['azimuth'], [30, 60])
            self.assertEqual(limits['elevation'], [15, 30])
            self.assertEqual(limits['beam'], [2, 4.8])


from test_loadout import LBase  # noqa: E402 — общий датамайн с настоящей схемой подвески


class TestStatsBuild(LBase):
    def test_mass_edit_and_weightless_share_fm_copy(self):
        model = S.Stats(self.src, self.v('b1'))
        mass = next(p for p in model.for_section('Масса') if p.path == 'Mass/EmptyMass')
        model.set(mass, 3500)
        lo = L.Loadout(slots={2: {'weapon': 'gameData/Weapons/bombguns/b1_bomb.blk',
                                  'sample': 'bomb_left'}}, weightless=True)
        plan = BL.stock_plan(self.src, self.v('b1'), True, loadout=lo, catalog=self.cat, stats=model)
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        fm_files = [(p, t) for p, t in plan.files if p.endswith('/fm/wtp5_b1.blk')]
        self.assertEqual(len(fm_files), 1, [p for p, _ in fm_files])
        self.assertIn('EmptyMass', fm_files[0][1])
        self.assertEqual(plan.launch, BL.COPY)

    def test_sensor_edit_creates_own_copy(self):
        sensor = 'gameData/sensors/test_radar.blk'
        path = os.path.join(self.dm, 'aces.vromfs.bin_u', 'gamedata', 'sensors', 'test_radar.blkx')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as out:
            json.dump({'type': 'radar', 'transivers': {'search': {'range': 90000.0,
                                                                 'scanAngle': 60.0}}}, out)
        unit = self.src.load(self.v('b1')['file'])
        unit.blocks.extend(B.parse_text('sensors{sensor{blk:t="%s"\n}}' % sensor).blocks)
        model = S.Stats(self.src, self.v('b1'))
        self.assertFalse(any(p.path.endswith('scanAngle') for p in model.for_section('РЛС')))
        model.set_leaf(sensor, 'transivers/search/scanAngle', '90')
        plan = BL.stock_plan(self.src, self.v('b1'), False, stats=model)
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        self.assertTrue(any(p.endswith('/sensors/wtp5_b1__test_radar.blk') for p, _ in plan.files))


if __name__ == '__main__':
    unittest.main()
