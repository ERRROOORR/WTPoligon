"""Окно (этап 2) без экрана: QT_QPA_PLATFORM=offscreen. Источник — поддельный датамайн из test_wtpoligon,
запись — во временную папку «игры». Без PySide6 тесты пропускаются (локально: pip install -r requirements.txt)."""
import os
import sys
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.*=false')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from test_wtpoligon import Base  # noqa: E402
from wtpoligon import hangar as H  # noqa: E402
from wtpoligon import install as I  # noqa: E402
from wtpoligon.targets import Scenario  # noqa: E402
from test_stats import Source  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # нет PySide6 или системных библиотек Qt
    QApplication = None

if QApplication is not None:
    from wtpoligon.gui import texts as TX
    from wtpoligon.gui.app import _args, open_context
    from wtpoligon.gui.theme import apply_dark
    from wtpoligon.gui.window import MainWindow


@unittest.skipIf(QApplication is None, 'нет PySide6')
class TestWindow(Base):
    @classmethod
    def setUpClass(cls):
        cls.qapp = QApplication.instance() or QApplication([])
        apply_dark(cls.qapp)

    def window(self, target=True):
        src, vehicles, root, tgt = open_context(_args(['--datamine', self.dm, '--app-dir', self.app] +
                                                      (['--target', self.game] if target else [])))
        w = MainWindow(src, vehicles, root, tgt)
        w.confirm = lambda *_a: True
        w.show()
        self.addCleanup(w.close)
        return w

    def test_steps_need_vehicle(self):
        w = self.window()
        self.assertEqual(w.step, 0)
        self.assertFalse(w.next_btn.isEnabled())
        self.assertFalse(w.go(5))
        self.assertEqual(w.vehicles_page.model.rowCount(), 5)
        w.vehicles_page.find.setText('т-1')
        self.assertEqual([v['name'] for v in w.vehicles_page.model.rows], ['t1', 't1_launcher'])
        self.assertTrue(w.vehicles_page.select('t1'))
        self.assertTrue(w.next_btn.isEnabled())
        # у танка шага «Подвеска» нет: кнопка скрыта, «Далее» ведёт к характеристикам
        self.assertFalse(w.step_buttons[1].isVisible())
        self.assertFalse(w.go(1))
        w.next_btn.click()
        self.assertEqual(w.step, 2)
        self.assertEqual(w.step_buttons[2].text().split()[0], '2')
        w.back_btn.click()
        self.assertEqual(w.step, 0)
        self.assertTrue(w.go(5))
        self.assertFalse(w.next_btn.isVisible())
        w.vehicles_page.select('a1')                       # самолёт — шаг есть
        self.assertTrue(w.step_buttons[1].isVisible())
        self.assertTrue(w.go(1))
        w.go(0)
        self.assertEqual(w.stack.currentIndex(), 0)

    def test_filters(self):
        w = self.window()
        page = w.vehicles_page
        page.kind.setCurrentIndex(page.kind.findData('air'))
        self.assertEqual([v['name'] for v in page.model.rows], ['a1'])
        page.kind.setCurrentIndex(0)
        page.country.setCurrentIndex(page.country.findData('ussr'))
        self.assertEqual(sorted(v['name'] for v in page.model.rows), ['t1', 't1_launcher'])
        page.rank.setCurrentIndex(page.rank.findData(3))
        self.assertEqual([v['name'] for v in page.model.rows], ['t1'])
        self.assertTrue(page.select('a1'))                     # скрытая фильтром машина — фильтры сброшены
        self.assertEqual(page.selected['name'], 'a1')

    def test_help_on_every_step(self):
        w = self.window()
        for i in range(len(TX.STEPS)):
            title, text = w.help_text(i)
            self.assertIn('Шаг %d' % (i + 1), title)
            self.assertGreater(len(text), 100)

    def test_characteristics_page_offscreen(self):
        w = self.window()
        w.vehicles_page.select('a1')
        unit = 'gameData/flightModels/a1.blk'
        fm = 'gameData/flightModels/fm/a1.blk'
        original_source = w.source
        w.source = Source({unit: 'fmFile:t="fm/a1.blk"', fm: 'Mass{EmptyMass:r=1000\n}'})
        w.stats_page.vehicle_name = ''
        w.stats_page.set_vehicle(w.vehicle)
        from PySide6.QtTest import QTest
        for _ in range(100):
            if w.stats_page.model is not None:
                break
            QTest.qWait(10)
        self.assertEqual([w.stats_page.menu.item(i).text() for i in range(w.stats_page.menu.count())],
                         ['Масса', 'Название', 'Все параметры (дерево)'])
        self.assertTrue(w.go(2))
        self.assertEqual(w.stack.currentWidget(), w.stats_page)
        w.stats_page.general_edit.setText('1500')
        w.stats_page.general_edit.editingFinished.emit()
        self.assertEqual(w.stats_page.model.general('Масса'), 1500)
        w.stats_page.menu.setCurrentRow(2)
        from PySide6.QtWidgets import QTreeWidget
        tree = w.stats_page.findChild(QTreeWidget)
        self.assertIsNotNone(tree)
        self.assertTrue(any(path == 'Mass/EmptyMass' for _, path, _, _ in w.stats_page.model.all_leaves()))
        w.source = original_source

    def test_hangar_mark(self):
        w = self.window()
        w.vehicles_page.select('t1')
        w.vehicles_page.hangar.click()
        self.assertEqual(H.load(self.app), {'t1': True})
        w.go(5)
        self.assertEqual(w.review_page.plan.launch, 'hangar')
        w.go(0)
        w.vehicles_page.hangar.click()
        self.assertEqual(H.load(self.app), {'t1': False})

    def test_scenario_by_kind(self):
        w = self.window()
        sp = w.scenario_page
        w.vehicles_page.select('a1')
        self.assertEqual(sp.scenario().mode, 'air')
        sp.set_mode('ground')   # машина задаёт режим: смена на наземку не меняет технику
        self.assertEqual(sp.scenario().mode, 'air')
        self.assertEqual(sp.scenario().player, 'a1')
        self.assertFalse(sp.mode_buttons['ground'].isVisibleTo(sp))
        sp.set_mode('duel')
        self.assertEqual(sp.scenario().mode, 'duel')
        w.vehicles_page.select('t1')
        self.assertEqual(sp.scenario().mode, 'ground')
        self.assertEqual(sp.scenario().player, 't1')
        sp._set_count('air', 10)
        self.assertEqual(sp.scenario().categories['air'].total(), 10)
        sp._remove('air', 0)
        self.assertEqual(sp.scenario().categories['air'].total(), 0)
        sp._pick_vehicle = lambda pool, title: next(v for v in pool if v['name'] == 'a1')
        sp._add('air')
        self.assertEqual(sp.scenario().categories['air'].total(), 1)
        w.vehicles_page.select('s1')
        self.assertEqual(sp.scenario().mode, 'naval')

    def test_write_status_rollback(self):
        w = self.window()
        w.vehicles_page.select('t1')
        sp = w.scenario_page
        self.assertEqual(sp.scenario().categories['air'].total(), 10)
        w.go(5)
        rp = w.review_page
        self.assertEqual(rp.problems, [])
        self.assertIn('0 ошибок', rp.summary.toPlainText())
        self.assertTrue(rp.write_btn.isEnabled())
        self.assertFalse(rp.undo_btn.isEnabled())
        rp.write_btn.click()
        mission = os.path.join(self.game, 'UserMissions', 'WTPoligon5', 'wtp5_t1.blk')
        with open(mission, encoding='utf-8') as f:
            self.assertIn('a1', f.read())
        self.assertIn('Готово', rp.result.text())
        self.assertEqual(rp.status.topLevelItemCount(), 1)
        self.assertIn('на месте', rp.status.topLevelItem(0).text(4))
        self.assertTrue(rp.undo_btn.isEnabled())
        rp.undo_btn.click()
        self.assertFalse(os.path.exists(mission))
        self.assertEqual(I.installed(self.app), {})
        self.assertEqual(rp.status.topLevelItemCount(), 0)

    def test_rollback_all_and_cancel(self):
        w = self.window()
        for name in ('t1', 'a1'):
            w.vehicles_page.select(name)
            w.go(5)
            self.assertTrue(w.review_page.write())
        self.assertEqual(len(I.installed(self.app)), 2)
        w.confirm = lambda *_a: False
        w.review_page.undo_all.click()
        self.assertEqual(len(I.installed(self.app)), 2)        # «Нет» — ничего не тронуто
        w.confirm = lambda *_a: True
        w.review_page.undo_all.click()
        self.assertEqual(I.installed(self.app), {})

    def test_no_target_no_write(self):
        w = self.window(target=False)
        w.vehicles_page.select('t1')
        w.go(5)
        self.assertEqual(w.review_page.problems, [])
        self.assertFalse(w.review_page.write_btn.isEnabled())
        self.assertIn('недоступна', w.review_page.target.text())
        self.assertFalse(w.review_page.write())


if __name__ == '__main__':
    unittest.main()

