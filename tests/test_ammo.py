"""Боекомплект и копии оружия на данных установленной игры."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from wtpoligon import build
from wtpoligon.ammo.catalog import Shell, shells_in, stock_setup
from wtpoligon.ammo.model import Ammo, Slot, AirGun
from wtpoligon.game.index import unit_file
from wtpoligon.game.source import open_source


GAME = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'WarThunder')


class TestAmmoModel(unittest.TestCase):
    def test_shell_search_by_name_gun_and_carrier(self):
        from wtpoligon.gui import workers
        from wtpoligon.game import blk

        shell = Shell('gameData/Weapons/test_gun.blk|ap', '3BM42 Mango', 'apds_fs_long_l30_tank',
                      'gameData/Weapons/test_gun.blk', 'ap')
        source = object()
        vehicles = [{'name': 'ussr_t_80bvm', 'ru': 'Т-80БВМ', 'en': 'T-80BVM'}]
        catalog = [{'path': shell.weapon, 'carriers': ['ussr_t_80bvm']}]
        block = blk.Block('ap', blocks=[blk.Block('bullet', params=[('caliber', 'r', 0.125)])])
        with patch.object(workers, 'source_at', return_value=source), \
             patch('wtpoligon.ammo.catalog.all_shells', return_value=(shell,)), \
             patch('wtpoligon.ammo.catalog._names', return_value={}), \
             patch('wtpoligon.ammo.catalog.shell_block', return_value=block), \
             patch('wtpoligon.loadout.load_catalog', return_value=catalog):
            for query in ('mango', 'test gun', 'т80бмв'):
                with self.subTest(query=query):
                    found = workers.ammo_search('game', 'unused', query, vehicles, 'cache')
                    self.assertEqual(found[0][0], shell)
                    self.assertEqual(found[0][4], 'Т-80БВМ')
                    self.assertEqual(found[0][5], 125)

    def test_round_trip_and_capacity(self):
        from wtpoligon.ammo.validate import check
        ammo = Ammo(capacity=20, slots=[Slot('gun|ap', 15), Slot('gun|he', 10), Slot(), Slot()])
        self.assertEqual(Ammo.from_dict(ammo.to_dict()), ammo)
        self.assertIn('заряжено больше вместимости', check(ammo))

    def test_offscreen_page(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from wtpoligon.gui.ammo_page import AmmoPage
        app = QApplication.instance() or QApplication([])
        win = SimpleNamespace(vehicle={'name': 'test_tank', 'kind': 'tank'}, source=None)
        page = AmmoPage(win)
        page.model.capacity = 20
        page.render()
        self.assertEqual(len(page.slot_combos), 4)
        self.assertIn('Заряжено 0 из 20', page.loaded.text())
        page.show()
        page.findChild(type(page.tree_toggle), 'ammoAddShell').click()
        self.assertTrue(page._shell_popup.isVisible())
        QTest.keyClick(page._shell_popup.find, Qt.Key_Escape)
        app.processEvents()
        self.assertIsNone(page._shell_popup)
        page.close()


@unittest.skipUnless(os.path.isfile(os.path.join(GAME, 'aces.vromfs.bin')), 'игра не установлена')
class TestAmmoGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = open_source(game_dir=GAME)

    def vehicle(self, name, kind):
        return {'name': name, 'kind': kind, 'file': unit_file(kind, name), 'ru': name, 'en': name}

    def test_ground_slots_and_donor(self):
        source = self.source
        vehicle = self.vehicle('ussr_t_80bvm', 'tank')
        guns, shells, capacity = stock_setup(source, vehicle)
        donor = shells_in(source, 'gameData/Weapons/groundModels_weapons/88mm_kwk36_user_cannon.blk')[2]
        ammo = Ammo(capacity=capacity, slots=[Slot(shells[3].key, 10), Slot(donor.key, 5), Slot(), Slot()],
                    added=[donor.key])
        plan = build.stock_plan(source, vehicle, False, ammo=ammo)
        self.assertEqual(build.verify_plan(source, plan), [])
        mission = dict(plan.files)[plan.mission_path]
        self.assertIn('125mm_ussr_3BM42_APDS_FS', mission)
        self.assertIn(donor.block, mission)
        self.assertTrue(any(donor.block in text for path, text in plan.files if path.startswith('content/pkg_local/gameData/Weapons/')))

    def test_air_preset_and_gun_copy(self):
        source = self.source
        vehicle = self.vehicle('f_15c_golden_eagle', 'air')
        unit = source.load(vehicle['file'])
        preset = build.default_preset(unit, vehicle['name'], 'air')
        guns, shells, _capacity = stock_setup(source, vehicle, preset)
        ammo = Ammo(air_guns=[AirGun(guns[0][1], shells[0].key, 500)])
        plan = build.stock_plan(source, vehicle, False, ammo=ammo)
        self.assertEqual(build.verify_plan(source, plan), [])
        self.assertTrue(any('weaponPresets' in path for path, _ in plan.files))
        self.assertTrue(any('Weapons/' in path for path, _ in plan.files))

    def test_donor_gun(self):
        source = self.source
        vehicle = self.vehicle('ussr_t_80bvm', 'tank')
        gun = 'gameData/Weapons/groundModels_weapons/88mm_kwk36_user_cannon.blk'
        shell = shells_in(source, gun)[2]
        ammo = Ammo(gun=gun, capacity=38, slots=[Slot(shell.key, 10), Slot(), Slot(), Slot()])
        plan = build.stock_plan(source, vehicle, False, ammo=ammo)
        self.assertEqual(build.verify_plan(source, plan), [])
        unit = dict(plan.files)['content/pkg_local/gameData/units/tankModels/' + plan.unit_class + '.blk']
        self.assertIn('@override:commonWeapons', unit)
