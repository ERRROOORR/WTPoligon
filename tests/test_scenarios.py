"""Новая модель, подбор и сборка по каждому режиму без запуска игры."""
import os
import json
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from wtpoligon import build as BL  # noqa: E402
from wtpoligon.game import blk as B  # noqa: E402
from wtpoligon.scenarios import autopick as A, catalog as C  # noqa: E402
from wtpoligon.scenarios.model import Scenario, Target  # noqa: E402
from wtpoligon.scenarios import build as SB  # noqa: E402
from test_wtpoligon import Base  # noqa: E402


class TestScenarioModel(unittest.TestCase):
    def test_round_trip_and_migration(self):
        scenario = Scenario(mode='air', player='mig_23m', player_br=10.0)
        scenario.categories['fighters'].targets = [Target('f_15c', 3)]
        scenario.categories['fighters'].count = 3
        self.assertEqual(Scenario.from_dict(scenario.to_dict()), scenario)
        old = Scenario.from_dict({'spawn': 'air_denmark', 'air': 'mig23',
                                  'air_distance': 30000, 'air_radar': True})
        self.assertEqual(old.mode, 'air')
        self.assertEqual(old.categories['air'].targets[0].vehicle, 'mig_23m')
        self.assertTrue(old.categories['air'].radar)

    def test_seed_range_refill_and_multiplicity(self):
        vehicles = [{'name': 'player', 'kind': 'air', 'type': 'type_fighter', 'br': 5.0}]
        vehicles += [{'name': 'f%d' % i, 'kind': 'air', 'type': 'type_fighter', 'br': 4.0 + i * .1}
                     for i in range(12)]
        scenario = Scenario(mode='air', player='player', player_br=5.0)
        cat = scenario.categories['fighters']
        cat.count = 5
        first = [t.vehicle for t in A.refill(scenario, vehicles, 'fighters', seed=8, reroll=True)]
        self.assertEqual(first, [t.vehicle for t in A.refill(scenario, vehicles, 'fighters', seed=8, reroll=True)])
        self.assertTrue(all(4.0 <= C.vehicle_map(vehicles)[name]['br'] <= 5.7 for name in first))
        cat.count = 3
        A.refill(scenario, vehicles, 'fighters', seed=8)
        self.assertEqual([t.vehicle for t in cat.targets], first[:3])
        cat.count = 6
        A.refill(scenario, vehicles, 'fighters', seed=8)
        self.assertEqual(cat.total(), 6)
        A.add(scenario, 'fighters', cat.targets[0].vehicle)
        self.assertEqual(cat.targets[0].count, 2)


class TestScenarioBuild(Base):
    def _empty(self, mode, player):
        scenario = Scenario(mode=mode, player=player)
        for category in scenario.categories.values():
            category.count = 0
        return scenario

    def test_parts_and_blk_all_modes(self):
        for mode, player in [('ground', 't1'), ('air', 'a1'), ('heli', 'H1'), ('naval', 's1')]:
            with self.subTest(mode=mode):
                scenario = self._empty(mode, player)
                plan = BL.stock_plan(self.src, self.v(player), False, scenario=scenario)
                self.assertEqual(plan.problems, [])
                self.assertEqual(B.parse_text(dict(plan.files)[plan.mission_path]).block('units').blocks[0].get('name'),
                                 'player')
                self.assertEqual(BL.verify_plan(self.src, plan), [])

    def test_duel_and_options(self):
        scenario = self._empty('duel', 'a1')
        scenario.duel.enemy = 'a1'
        scenario.duel.count = 2
        scenario.conditions.time = 'Night'
        scenario.rules.rapid_reload = 8
        scenario.rules.infinite_fuel = False
        plan = BL.stock_plan(self.src, self.v('a1'), False, scenario=scenario)
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        root = B.parse_text(dict(plan.files)[plan.mission_path])
        self.assertEqual(root.block('mission_settings').block('mission').get('environment'), 'Night')
        self.assertTrue(root.block('mission_settings').block('mission').get('isLimitedFuel'))
        self.assertIsNotNone(next((x for x in root.block('triggers').blocks if x.name == 'rapid_fire'), None))
        self.assertEqual(len([x for x in root.block('units').blocks if x.get('name', '').startswith('air_')]), 2)

    def test_target_rules_change_parts(self):
        scenario = self._empty('air', 'a1')
        scenario.categories['air'].targets = [Target('mig_23m')]
        scenario.categories['air'].count = 1
        scenario.categories['air'].radar = True
        scenario.categories['air'].shoots = True
        scenario.categories['ships'].targets = [Target('s1')]
        scenario.categories['ships'].count = 1
        scenario.rules.markers = False
        scenario.rules.restore_ammo = True
        parts = SB.mission_parts(scenario, self.src)
        air = next(u for u in parts['extra_units'] if u.name == 'armada')
        self.assertTrue(air.block('props').get('use_search_radar'))
        self.assertEqual(air.block('props').get('attack_type'), 'fire_at_will')
        self.assertFalse(any(a.name == 'unitSetIndication' for a in parts['init_actions']))
        self.assertTrue(any(w.name == 'ship_01_way' for w in parts['way_points']))
        self.assertTrue(any(a.name == 'unitRestore' and a.get('target') == 'player'
                            for t in parts['extra_triggers'] for a in t.block('actions').blocks))
        scenario.rules.moving_ships = False
        scenario.rules.restore_ammo = False
        parts = SB.mission_parts(scenario, self.src)
        self.assertFalse(any(w.name == 'ship_01_way' for w in parts['way_points']))

    def test_cli_scenario_json(self):
        scenario = self._empty('ground', 't1')
        scenario.categories['air'].targets = [Target('a1', 2)]
        scenario.categories['air'].count = 2
        path = os.path.join(self.tmp, 'scenario.json')
        with open(path, 'w', encoding='utf-8') as stream:
            json.dump(scenario.to_dict(), stream)
        code, output = self.run_cli('mission', 't1', '--scenario-json', path)
        self.assertEqual(code, 0, output)
        self.assertIn('a1 ×2', output)
