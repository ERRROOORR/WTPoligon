"""Главное окно: шаги «Техника → Подвеска → Сценарий → Проверка и запись» (ТЗ §6.1). Всё значение — через пакет
wtpoligon: индекс (game.index), отметка ангара (hangar), подвеска (loadout), сценарий (targets), сборка и проверка
(build), запись (install)."""
import html
import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QMainWindow, QMessageBox, QPushButton, QStackedWidget, QTextBrowser, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import build as BL
from .. import hangar as H
from .. import install as I
from .. import loadout as L
from .. import targets as T
from ..scenarios.model import Scenario as NewScenario
from ..scenarios import build as SBD
from ..game import index as X
from . import texts as TX
from .loadout_page import LoadoutPage
from .stats_page import StatsPage
from .scenario_page import ScenarioPage
from .ammo_page import AmmoPage
from .vehicle_page import VehiclePage
from . import workers

STEP_REVIEW = 5


def _label(text, name=None, wrap=True):
    w = QLabel(text)
    w.setWordWrap(wrap)
    if name:
        w.setObjectName(name)
    return w


class ReviewPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.plan, self.problems = None, []
        self._generation = 0
        self._future = None
        lay = QVBoxLayout(self)
        lay.addWidget(_label('Проверка и запись', 'title'))
        self.summary = QTextBrowser()
        self.summary.setOpenExternalLinks(False)
        lay.addWidget(self.summary, 3)
        row = QHBoxLayout()
        self.write_btn = QPushButton('Записать в игру')
        self.write_btn.setObjectName('primary')
        self.undo_btn = QPushButton('Откатить эту машину')
        self.target = _label('', 'hint')
        row.addWidget(self.write_btn)
        row.addWidget(self.undo_btn)
        row.addWidget(self.target, 1)
        lay.addLayout(row)
        self.result = _label('')
        lay.addWidget(self.result)

        lay.addWidget(_label('Что уже записано программой', 'title'))
        self.status = QTreeWidget()
        self.status.setHeaderLabels(['Машина', 'Способ', 'Миссия', 'Когда', 'Файлы'])
        self.status.setRootIsDecorated(False)
        self.status.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        lay.addWidget(self.status, 2)
        row = QHBoxLayout()
        self.undo_sel = QPushButton('Откатить выбранное')
        self.undo_all = QPushButton('Откатить всё')
        row.addWidget(self.undo_sel)
        row.addWidget(self.undo_all)
        row.addStretch(1)
        self.logs_btn = QPushButton('Логи')
        self.logs_btn.setToolTip('Собрать свежие логи игры и записи программы в архив (папка logs рядом с программой) '
                                 '— его можно отправить для разбора проблем.')
        self.logs_btn.clicked.connect(self.collect_logs)
        row.addWidget(self.logs_btn)
        lay.addLayout(row)

        self.write_btn.clicked.connect(self.write)
        self.undo_btn.clicked.connect(lambda: self.rollback([self.plan.app_id] if self.plan else []))
        self.undo_sel.clicked.connect(lambda: self.rollback([i.text(0) for i in self.status.selectedItems()]))
        self.undo_all.clicked.connect(lambda: self.rollback([r[0] for r in I.status(self.win.root)]))
        self.status.itemSelectionChanged.connect(self._buttons)

    def rebuild(self):
        """Собрать план под текущий выбор и проверить моделью правок."""
        self._generation += 1
        if len(self.win.vehicles) >= 100:
            self._future = None
            self.plan, self.problems = None, []
            self.summary.setPlainText('Загружаю проверку…')
            self.write_btn.setEnabled(False)
            self._rebuild_async(self._generation)
            return
        v, sc = self.win.vehicles_page.selected, self.win.scenario_page.scenario()
        self.result.setText('')
        if v is None or sc is None:
            self.plan, self.problems = None, ['машина не выбрана']
        else:
            in_hangar = bool(H.status(self.win.marks, v['name']))
            try:
                lp = self.win.loadout_page
                lo = lp.loadout() if self.win.has_loadout() else None   # подвеска только у авиации
                self.plan = BL.stock_plan(self.win.source, v, in_hangar, scenario=sc, loadout=lo,
                                          catalog=lp.ensure_catalog() if lo is not None else None,
                                          stats=self.win.stats_page.model, vehicles=self.win.vehicles,
                                          ammo=self.win.ammo_page.ammo())
                self.problems = BL.verify_plan(self.win.source, self.plan)
            except Exception as e:  # noqa: BLE001 — показать сбой, а не уронить окно
                self.plan, self.problems = None, ['сбой сборки: %s: %s' % (type(e).__name__, e)]
        self.summary.setHtml(self.summary_html())
        self.refresh_status()

    def _rebuild_async(self, generation):
        if generation != self._generation:
            return
        lp, sp = self.win.loadout_page, self.win.scenario_page
        pending = (lp._setup_future if lp._setup_future is not None and not lp._setup_future.done() else
                   sp._pending if sp._pending is not None and not sp._pending.done() else None)
        if pending is not None:
            QTimer.singleShot(30, lambda: self._rebuild_async(generation))
            return
        if lp._setup_future is not None and lp._setup_future.done():
            lp._poll_setup(lp._setup_generation)
        if sp._pending is not None and sp._pending.done():
            sp._poll_vehicle(sp._generation)
        if self._future is None:
            v, sc = self.win.vehicle, sp.scenario()
            lo = lp.loadout() if self.win.has_loadout() else None
            catalog = lp.catalog if lo is not None else None
            model = self.win.stats_page.model
            stats = None
            if model is not None and model.changed():
                import copy
                stats = copy.copy(model)
                stats.source = None
            self._future = workers.pool().submit(
                workers.review, self.win.source.kind, self.win.source.root, v,
                bool(H.status(self.win.marks, v['name'])), sc, lo, catalog, stats, self.win.vehicles,
                self.win.ammo_page.ammo())
            QTimer.singleShot(30, lambda: self._rebuild_async(generation))
            return
        if not self._future.done():
            QTimer.singleShot(30, lambda: self._rebuild_async(generation))
            return
        try:
            self.plan, self.problems = self._future.result()
        except Exception as exc:
            self.plan, self.problems = None, ['сбой сборки: %s: %s' % (type(exc).__name__, exc)]
        self._future = None
        self.summary.setHtml(self.summary_html())
        self.refresh_status()

    def collect_logs(self):
        """Логи игры и манифесты программы — в архив; сбор в фоне, затем открыть папку с архивом."""
        game = self.win.source.root if self.win.source.kind == 'game' else self.win.target_dir
        self.logs_btn.setEnabled(False)
        self.logs_btn.setText('Собираю…')
        future = workers.pool().submit(workers.collect_logs, game, self.win.root)

        def poll():
            if not future.done():
                QTimer.singleShot(100, poll)
                return
            self.logs_btn.setEnabled(True)
            self.logs_btn.setText('Логи')
            try:
                path = future.result()
            except Exception as e:  # noqa: BLE001 — показать, а не уронить окно
                self.result.setText('Не удалось собрать логи: %s' % e)
                return
            self.result.setText('Логи собраны: %s' % path)
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
        QTimer.singleShot(100, poll)

    def summary_html(self):
        e = html.escape
        if self.plan is None:
            return '<p style="color:#ff6b6b">%s</p>' % '<br>'.join(e(p) for p in self.problems)
        p, v = self.plan, self.plan.vehicle
        out = ['<h3>%s</h3>' % e(v['ru'] or v['en'] or v['name']),
               '<p>%s; в миссии — <code>%s</code>; вооружение: <code>%s</code></p>' % (
                   'Из ангара, под настоящим именем (полноценная)' if p.launch == BL.HANGAR else
                   'Не из ангара — копия под своим именем', e(p.unit_class), e(p.weapons or 'штатное'))]
        if self.problems:
            out.append('<p style="color:#ff6b6b"><b>Проверка нашла ошибки (%d) — записывать нельзя:</b><br>%s</p>'
                       % (len(self.problems), '<br>'.join(e(x) for x in self.problems)))
        else:
            out.append('<p style="color:#7bc96f"><b>Проверка моделью правок: 0 ошибок — можно записывать.</b></p>')
        if p.loadout is not None and not p.problems:
            lp = self.win.loadout_page
            sm = L.summarize(self.win.source, lp.pylons, p.loadout, lp.catalog)
            out.append('<p>Подвеска: %s; масса %.0f кг%s%s.</p>' % (
                'штатный пресет' if p.weapons == p.loadout.base and not p.weapons.startswith(BL.PREFIX)
                else 'изменена', sm.total, ', невесомая (пустая масса %.0f кг)' % sm.weightless_mass
                if sm.weightless_mass is not None else '',
                '; висит: ' + e(', '.join('%s ×%d' % kv for kv in sm.counts.items())) if sm.counts else ''))
        if self.win.stats_page.model and self.win.stats_page.model.changed():
            sm = self.win.stats_page.model
            out.append('<p>Характеристики: %d правок параметров%s.</p>' % (
                len(sm.values), '; название: ' + e(sm.title) if sm.title else ''))
        if p.ammo is not None and p.ammo.changed():
            out.append('<p>Боеприпасы: %d ячеек, %d добавленных снарядов, %d правок.</p>' % (
                sum(bool(s.shell) for s in p.ammo.slots), len(p.ammo.added), len(p.ammo.edits)))
        if p.scenario and not p.problems:
            out.append('<p>%s</p>' % '<br>'.join(e(s) for s in (SBD.describe(p.scenario) if isinstance(p.scenario, NewScenario) else T.describe(p.scenario))))
        if p.notes:
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % e(n) for n in p.notes))
        out.append('<p><b>Будет записано (%d):</b></p><ul>%s</ul>' % (
            len(p.files), ''.join('<li><code>%s</code> — %d строк</li>' % (e(r), t.count('\n')) for r, t in p.files)))
        return ''.join(out)

    def refresh_status(self):
        self.status.clear()
        for app_id, meta, state in I.status(self.win.root):
            QTreeWidgetItem(self.status, [
                app_id, 'из ангара' if meta.get('launch') == BL.HANGAR else 'копия',
                meta.get('mission', ''), meta.get('installed', '').replace('T', ' '),
                ', '.join('%s %d' % kv for kv in state.items())])
        self._buttons()

    def _buttons(self):
        target = self.win.target_dir
        self.target.setText('Папка игры: %s' % target if target else
                            'Запись недоступна: папка игры не задана (источник — датамайн).')
        ok = bool(self.plan) and not self.problems and bool(target)
        self.write_btn.setEnabled(ok)
        apps = {r[0] for r in I.status(self.win.root)}
        self.undo_btn.setEnabled(bool(self.plan) and self.plan.app_id in apps)
        self.undo_sel.setEnabled(bool(self.status.selectedItems()))
        self.undo_all.setEnabled(bool(apps))

    def write(self):
        p = self.plan
        if not p or self.problems or not self.win.target_dir:
            return False
        danger = [n for n in p.notes if n.startswith('⚠')]
        text = 'Записать %d файл(а) в %s?' % (len(p.files), self.win.target_dir)
        if danger:
            text = ('Внимание: в подвеске оружие, с которым игра может упасть при старте миссии:\n\n%s\n\n'
                    'Всё равно записать?' % '\n'.join(danger))
        if not self.win.confirm('Записать в игру', text):
            return False
        meta = {'unit': p.vehicle['name'], 'launch': p.launch, 'mission': p.mission,
                'game_dir': os.path.abspath(self.win.target_dir), 'source': self.win.source.describe(),
                'scenario': p.scenario.to_dict(), 'loadout': p.loadout.to_dict() if p.loadout else None,
                'ammo': p.ammo.to_dict() if p.ammo else None}
        ok, report = I.install(self.win.target_dir, self.win.root, p.app_id, p.files, meta)
        title = p.vehicle['ru'] or p.vehicle['en'] or p.vehicle['name']
        if ok:
            self.result.setText('<span style="color:#7bc96f">Готово. В игре: Одиночные миссии → Пользовательские → '
                                '«WTP5 — %s». Перезапуск игры не нужен.</span>' % html.escape(title))
        else:
            self.result.setText('<span style="color:#ff6b6b">Ничего не записано: %s</span>' %
                                html.escape('; '.join(report)))
        self.refresh_status()
        return ok

    def rollback(self, app_ids):
        apps = {r[0]: r[1] for r in I.status(self.win.root)}
        app_ids = [a for a in app_ids if a in apps]
        if not app_ids or not self.win.confirm('Откатить', 'Убрать из игры записанное программой для: %s?' %
                                               ', '.join(app_ids)):
            return False
        lines = []
        for app_id in app_ids:
            game = apps[app_id].get('game_dir') or self.win.target_dir or ''
            lines += I.uninstall(game, self.win.root, app_id)
        self.result.setText('Откат: %s' % html.escape('; '.join(lines) or 'готово'))
        self.refresh_status()
        return True


class MainWindow(QMainWindow):
    def __init__(self, source, vehicles, root, target_dir=None):
        super().__init__()
        self.source, self.vehicles, self.root, self.target_dir = source, vehicles, root, target_dir
        self.marks = H.load(root)
        self.setWindowTitle('WT Poligon 5 — тестовый выезд · автор ERRROOORR')
        self.resize(1100, 760)
        central = QWidget()
        central.setObjectName('page')
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        top.setContentsMargins(16, 6, 16, 6)
        brand = QLabel('WT Poligon <span style="color:#f2913d">5</span>')
        brand.setStyleSheet('font-weight:700; font-size:13pt; margin-right:24px;')
        top.addWidget(brand)
        self.step_buttons = []
        for i, name in enumerate(TX.STEPS):
            b = QPushButton('%d   %s' % (i + 1, name))
            b.setObjectName('step')
            b.setCheckable(True)
            b.clicked.connect(lambda _c=False, i=i: self.go(i))
            top.addWidget(b)
            self.step_buttons.append(b)
        top.addStretch(1)
        self.help_btn = QPushButton('?')
        self.help_btn.setObjectName('help')
        self.help_btn.setToolTip('Что делать на этом шаге')
        self.help_btn.clicked.connect(self.show_help)
        top.addWidget(self.help_btn)
        lay.addLayout(top)

        self.stack = QStackedWidget()
        self.vehicles_page = VehiclePage(self)
        self.loadout_page = LoadoutPage(self)
        self.stats_page = StatsPage(self)
        self.ammo_page = AmmoPage(self)
        self.scenario_page = ScenarioPage(self)
        self.review_page = ReviewPage(self)
        for page in (self.vehicles_page, self.loadout_page, self.stats_page, self.ammo_page,
                     self.scenario_page, self.review_page):
            self.stack.addWidget(page)
        lay.addWidget(self.stack, 1)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(24, 8, 24, 14)
        self.source_label = _label('Источник: %s' % source.describe(), 'hint')
        self.back_btn = QPushButton('← Назад')
        self.next_btn = QPushButton('Далее →')
        self.next_btn.setObjectName('primary')
        self.back_btn.clicked.connect(lambda: self.go(self.neighbour(-1)))
        self.next_btn.clicked.connect(lambda: self.go(self.neighbour(1)))
        bottom.addWidget(self.source_label, 1)
        bottom.addWidget(self.back_btn)
        bottom.addWidget(self.next_btn)
        lay.addLayout(bottom)
        self.setCentralWidget(central)
        self.step = 0
        self._dirty_pages = set()
        self.go(0)
        if len(self.vehicles) >= 100:
            QTimer.singleShot(300, self.loadout_page.start_catalog)

    @property
    def vehicle(self):
        return self.vehicles_page.selected

    STEP_LOADOUT = 1

    def has_loadout(self):
        """Шаг «Подвеска» — только у самолётов и вертолётов (у наземки и флота его нет совсем)."""
        return self.vehicle is not None and self.vehicle['kind'] in ('air', 'heli')

    def can_go(self, step):
        if step == self.STEP_LOADOUT and not self.has_loadout():
            return False
        return 0 <= step < len(TX.STEPS) and (step == 0 or self.vehicle is not None)

    def neighbour(self, delta):
        """Соседний доступный шаг (Далее/Назад перескакивают «Подвеску» у танков и кораблей)."""
        step = self.step + delta
        if step == self.STEP_LOADOUT and not self.has_loadout():
            step += delta
        return step

    def go(self, step):
        if not self.can_go(step):
            return False
        self.step = step
        if step in self._dirty_pages:
            page = {self.STEP_LOADOUT: self.loadout_page, 2: self.stats_page,
                    3: self.ammo_page, 4: self.scenario_page}.get(step)
            if page is not None:
                page.set_vehicle(self.vehicle)
            self._dirty_pages.discard(step)
        if step == STEP_REVIEW:
            if self.STEP_LOADOUT in self._dirty_pages and self.has_loadout():
                self.loadout_page.set_vehicle(self.vehicle)
                self._dirty_pages.discard(self.STEP_LOADOUT)
            self.review_page.rebuild()
        self.stack.setCurrentIndex(step)
        self._update_nav()
        return True

    def _update_nav(self):
        n = 0
        for i, b in enumerate(self.step_buttons):
            shown = i != self.STEP_LOADOUT or self.has_loadout() or self.vehicle is None
            b.setVisible(shown)
            if shown:
                n += 1
                b.setText('%d   %s' % (n, TX.STEPS[i]))
            b.setChecked(i == self.step)
            b.setEnabled(self.can_go(i))
        self.back_btn.setEnabled(self.step > 0)
        self.next_btn.setVisible(self.step < len(TX.STEPS) - 1)
        self.next_btn.setEnabled(self.can_go(self.neighbour(1)))

    def vehicle_changed(self, v):
        if len(self.vehicles) < 100:
            self.loadout_page.set_vehicle(v)
            self.stats_page.set_vehicle(v)
            self.ammo_page.set_vehicle(v)
            self.scenario_page.set_vehicle(v)
            self._update_nav()
            return
        self._dirty_pages.update((self.STEP_LOADOUT, 2, 3, 4))
        if self.step == self.STEP_LOADOUT:
            self.loadout_page.set_vehicle(v)
            self._dirty_pages.discard(self.STEP_LOADOUT)
        elif self.step == 2:
            self.stats_page.set_vehicle(v)
            self._dirty_pages.discard(2)
        if self.step == 3:
            self.ammo_page.set_vehicle(v)
            self._dirty_pages.discard(3)
        self.scenario_page.set_vehicle(v)
        self._dirty_pages.discard(4)
        if self.step == self.STEP_LOADOUT and not self.has_loadout():
            self.go(0)
        self._update_nav()

    def help_text(self, step=None):
        return TX.HELP[self.step if step is None else step]

    def show_help(self):
        title, text = self.help_text()
        QMessageBox.information(self, title, text)

    def closeEvent(self, event):
        self.loadout_page.stop_catalog()
        self.stats_page.stop_loader()
        super().closeEvent(event)

    def confirm(self, title, text):
        """Спросить пользователя (тесты подменяют)."""
        return QMessageBox.question(self, title, text) == QMessageBox.Yes
