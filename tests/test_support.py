"""Вызов техники, библиотека и ядерный рецепт."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from test_wtpoligon import Base

from wtpoligon import build, library
from wtpoligon.ammo import nuclear
from wtpoligon.game import blk as B
from wtpoligon.support import catalog, validate
from wtpoligon.support.model import Entry, Support, stock

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    QApplication = None


class TestSupport(Base):
    def test_ground_count_and_filter(self):
        support = Support([Entry('t1', 'ground', 3)])
        rows = catalog.candidates(self.vehicles, support)
        self.assertNotIn(('s1', 's1', 'ground', ''), rows)
        self.assertEqual(validate.check(support, self.vehicles), [])
        plan = build.stock_plan(self.src, self.v('t1'), False, vehicles=self.vehicles, support=support)
        self.assertEqual(build.verify_plan(self.src, plan), [])
        unit = next(t for p, t in plan.files if p.endswith('/wtp5_t1.blk'))
        self.assertEqual(unit.count('count:i=1'), 3)
        self.assertEqual(unit.count('class:t="tankModels/t1"'), 3)

    def test_air_and_exclusive_kind(self):
        support = Support([Entry('a1', 'air')])
        plan = build.stock_plan(self.src, self.v('t1'), True, vehicles=self.vehicles, support=support)
        self.assertEqual(plan.launch, build.COPY)
        self.assertEqual(build.verify_plan(self.src, plan), [])
        unit = next(t for p, t in plan.files if p.endswith('/wtp5_t1.blk'))
        self.assertIn('supportPlaneClass:t="a1"', unit)
        self.assertIn('planeStartSpeed:r=450.0', unit)
        wrong = Support([Entry('a1', 'air'), Entry('a1', 'ground')])
        self.assertTrue(validate.check(wrong, self.vehicles))
        self.assertEqual(stock(self.src.load(self.v('t1')['file'])).entries[0].vehicle, 't1_launcher')

    def test_library_roundtrip(self):
        item = library.save(self.app, 'Мой танк', self.v('t1'), stats={'values': []},
                            support=Support([Entry('a1', 'air')]).to_dict())
        self.assertEqual(library.get(self.app, item['id']), item)
        self.assertEqual(library.list_items(self.app)[0]['name'], 'Мой танк')
        self.assertEqual(catalog.candidates(self.vehicles, Support(), library.list_items(self.app),
                                            'Мой танк', 'mine')[0][3], item['id'])
        plan = build.stock_plan(self.src, self.v('t1'), False, vehicles=self.vehicles,
                                support=Support([Entry('t1', 'ground', 1, item['id'])]),
                                support_library=library.list_items(self.app))
        self.assertEqual(build.verify_plan(self.src, plan), [])
        self.assertTrue(any(p.endswith('/wtp5_%s.blk' % item['id']) for p, _ in plan.files))

    def test_nuclear_shell_rocket_bomb(self):
        root = B.Block(None, blocks=[
            B.Block('HE', blocks=[B.Block('bullet', [('mass', 'r', 10.)])]),
            B.Block('ATGM', blocks=[B.Block('bullet', blocks=[B.Block('rocket', blocks=[B.Block('guidance')])])]),
            B.Block('BOMB', blocks=[B.Block('bomb')])])
        shell = nuclear.apply(root, 'HE', 30)
        rocket = shell.block('HE').block('bullet').block('rocket')
        self.assertEqual(rocket.get('yield'), 30)
        self.assertEqual(rocket.get('explosiveMass'), 20000)
        self.assertIsNone(rocket.block('guidance'))
        self.assertIsNotNone(rocket.block('pressureDamage'))
        self.assertEqual(nuclear.apply(root, 'ATGM', 5).block('ATGM').block('bullet').block('rocket').get('yield'), 5)
        self.assertEqual(nuclear.apply(root, 'BOMB', 1200).block('BOMB').block('bomb').get('yield'), 1200)


@unittest.skipIf(QApplication is None, 'нет PySide6')
class TestLibraryWindow(Base):
    @classmethod
    def setUpClass(cls):
        cls.app_qt = QApplication.instance() or QApplication([])

    def test_saved_vehicle_in_search_and_restore(self):
        from PySide6.QtTest import QTest
        from wtpoligon.gui.window import MainWindow
        item = library.save(self.app, 'Мой танк', self.v('t1'),
                            support=Support([Entry('a1', 'air')]).to_dict())
        window = MainWindow(self.src, self.vehicles, self.app, self.game)
        self.addCleanup(window.close)
        window.show()
        window.vehicles_page.find.setText('Мой танк')
        self.assertEqual(window.vehicles_page.model.rows[0]['_library_id'], item['id'])
        self.assertTrue(window.open_library(item['id']))
        for _ in range(50):
            self.app_qt.processEvents()
            QTest.qWait(10)
        self.assertEqual(window.support_page.model.entries[0].vehicle, 'a1')
