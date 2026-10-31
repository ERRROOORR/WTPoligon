"""Шаг «Характеристики»: разделы и дерево параметров стоковых файлов машины."""
import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QPushButton,
                               QSlider, QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget, QFrame, QAbstractItemView, QStyledItemDelegate)

from .. import stats as S
from . import workers


class StatsLoader(QThread):
    loaded = Signal(object, object, str)
    limits_ready = Signal(object)

    def __init__(self, source, vehicle, loadout, vehicles, cache_dir):
        super().__init__()
        self.source, self.vehicle, self.loadout = source, vehicle, loadout
        self.vehicles, self.cache_dir = vehicles, cache_dir

    def run(self):
        try:
            if getattr(self.source, 'kind', '') in ('game', 'datamine'):
                model, limits = workers.pool().submit(
                    workers.stats, self.source.kind, self.source.root, self.vehicle,
                    self.loadout, self.vehicles, self.cache_dir).result()
                model.source = self.source
            else:  # in-memory sources used by integrations and tests
                model = S.Stats(self.source, self.vehicle, self.loadout)
                limits = {}
            self.loaded.emit(model, {}, '')
            self.limits_ready.emit(limits)
        except Exception as exc:
            self.loaded.emit(None, {}, str(exc))


def number(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return ('%g' % value) if isinstance(value, (int, float)) else str(value)


class MenuDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.data(Qt.UserRole) == 'tree':
            painter.save()
            painter.setPen(QPen(QColor('#45454b')))
            painter.drawLine(option.rect.left() + 5, option.rect.top(),
                             option.rect.right() - 5, option.rect.top())
            painter.restore()


class StatsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.model = None
        self.vehicle_name = ''
        self._busy = False
        self.loader = None
        self._old_loaders = []
        self._limits_by_section = {}
        self._prior_model = None
        self.setStyleSheet('''
            QListWidget#statsMenu { background:#2b2b2f; border:1px solid #45454b; border-radius:6px;
                padding:5px; font-size:13px; }
            QListWidget#statsMenu::item { padding:6px 8px; border-radius:6px; }
            QListWidget#statsMenu::item:selected { background:#12355c; color:#8cc0f5; }
            QFrame#statsCard { background:#2b2b2f; border:1px solid #45454b; border-radius:6px; }
            QTableWidget#statsTable { background:transparent; border:0; gridline-color:#45454b; font-size:13px; }
            QTableWidget#statsTable::item { padding:3px; }
            QHeaderView::section { background:#2b2b2f; color:#a9a9b0; padding:5px; }
            QLineEdit#statsValue { min-height:28px; max-height:28px; padding:0 6px; border-radius:6px; }
            QPushButton#statsReset { min-height:28px; max-height:28px; padding:0 10px; border-radius:6px; }
        ''')
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        title = QLabel('Характеристики')
        title.setObjectName('title')
        lay.addWidget(title)
        self.caption = QLabel('Выберите машину')
        self.caption.setObjectName('hint')
        lay.addWidget(self.caption)
        self.loading = QLabel('')
        lay.addWidget(self.loading)
        split = QSplitter()
        left = QFrame()
        left.setObjectName('statsCard')
        ll = QVBoxLayout(left)
        ll.setContentsMargins(5, 5, 5, 5)
        ll.setSpacing(2)
        self.menu = QListWidget()
        self.menu.setObjectName('statsMenu')
        self.menu.setFrameShape(QFrame.NoFrame)
        self.menu.setItemDelegate(MenuDelegate(self.menu))
        ll.addWidget(self.menu)
        later = QLabel('другие разделы — позже')
        later.setStyleSheet('font-size:11px;color:#7d7d85;padding:4px 8px')
        ll.addWidget(later)
        right = QFrame()
        right.setObjectName('statsCard')
        self.editor = QVBoxLayout(right)
        self.editor.setContentsMargins(12, 10, 12, 10)
        self.editor.setSpacing(6)
        split.addWidget(left)
        split.addWidget(right)
        left.setMinimumWidth(175)
        left.setMaximumWidth(195)
        split.setSizes([180, 750])
        lay.addWidget(split, 1)
        self.menu.currentRowChanged.connect(self.show_section)

    def set_vehicle(self, vehicle, force=False):
        if vehicle is None:
            return
        if vehicle['name'] == self.vehicle_name and not force:
            return
        self._prior_model = self.model if force else None
        self.vehicle_name = vehicle['name']
        self.model = None
        self.menu.clear()
        self.loading.setText('Загружаю характеристики и диапазоны…')
        self.caption.setText('%s · параметры из файлов игры' % (vehicle['ru'] or vehicle['en'] or vehicle['name']))
        if self.loader is not None:
            self.loader.loaded.disconnect(self._loaded)
            self.loader.limits_ready.disconnect(self._limits_ready)
            self.loader.requestInterruption()
            self._old_loaders.append(self.loader)
        loadout = self.win.loadout_page.lo
        self.loader = StatsLoader(self.win.source, vehicle, loadout, self.win.vehicles,
                                  os.path.join(self.win.root, 'cache'))
        self.loader.loaded.connect(self._loaded)
        self.loader.limits_ready.connect(self._limits_ready)
        self.loader.start()

    def _loaded(self, model, limits, error):
        self._old_loaders = [loader for loader in self._old_loaders if loader.isRunning()]
        if error:
            self.loading.setText('Не удалось загрузить характеристики: ' + error)
            return
        if self._prior_model is not None:
            model.values = {key: value for key, value in self._prior_model.values.items()
                            if key[0] in model.trees}
            model.title = self._prior_model.title
            model.mission_title = self._prior_model.mission_title
            self._prior_model = None
        self.model = model
        self._limits_by_section = limits
        self.loading.setText('')
        self.menu.clear()
        self.menu.addItems(model.sections() + ['Все параметры (дерево)'])
        tree_item = self.menu.item(self.menu.count() - 1)
        tree_item.setData(Qt.UserRole, 'tree')
        self.menu.setCurrentRow(0)

    def _limits_ready(self, limits):
        self._limits_by_section = limits
        if self.menu.currentItem() is not None:
            self.show_section()

    def refresh_loadout(self):
        if self.win.vehicle is not None:
            self.set_vehicle(self.win.vehicle, force=True)

    def stop_loader(self):
        for loader in [self.loader, *self._old_loaders]:
            if loader is not None and loader.isRunning():
                loader.wait()

    def _clear(self):
        def remove(layout):
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
                elif item.layout():
                    remove(item.layout())
        remove(self.editor)

    def show_section(self, *_):
        if self.model is None or self.menu.currentItem() is None:
            return
        self._clear()
        section = self.menu.currentItem().text()
        if section == 'Все параметры (дерево)':
            self._tree()
        elif section == 'Название':
            self._names()
        else:
            self._parameters(section)

    def _names(self):
        title = QLabel('Название · проверено в игре')
        title.setObjectName('title')
        self.editor.addWidget(title)
        for label, attr in (('Машина в игре', 'title'), ('Миссия в списке', 'mission_title')):
            self.editor.addWidget(QLabel(label + ' · usr_*.csv'))
            edit = QLineEdit(getattr(self.model, attr))
            edit.setPlaceholderText(self.caption.text().split(' · ')[0])
            edit.textChanged.connect(lambda text, a=attr: setattr(self.model, a, text.strip()))
            self.editor.addWidget(edit)
        note = QLabel('Новые названия видны после перезапуска игры.')
        note.setObjectName('warn')
        self.editor.addWidget(note)
        self.editor.addStretch(1)

    def _parameters(self, section):
        if section == 'Двигатель' and self.model.vehicle['kind'] in ('air', 'heli'):
            self._engines()
            return
        if section == 'Ловушки':
            self._traps()
            return
        if section == 'РЛС':
            self._radar()
            return
        rows = self.model.for_section(section)
        limits = self._limits_by_section.get(section, {})
        heading = QHBoxLayout()
        title = QLabel(section)
        title.setStyleSheet('font-size:16px;font-weight:600')
        heading.addWidget(title)
        heading.addStretch()
        status = ('проверено в игре' if all(p.status == 'проверено в игре' for p in rows)
                  else 'не проверено' if any(p.status == 'не проверено' for p in rows)
                  else 'в игре не влияет')
        heading.addWidget(self._badge(status))
        self.editor.addLayout(heading)
        general = QHBoxLayout()
        general.setSpacing(8)
        name = QLabel(self.model.general_label(section))
        name.setStyleSheet('font-size:13px;color:#a9a9b0')
        general.addWidget(name, 1)
        self.general_edit = QLineEdit(number(self.model.general(section)))
        self.general_edit.setObjectName('statsValue')
        self.general_edit.setFixedWidth(120)
        self.general_edit.editingFinished.connect(lambda s=section: self._set_general(s))
        general.addWidget(self.general_edit)
        unit = QLabel(rows[0].unit if rows else '')
        unit.setFixedWidth(42)
        general.addWidget(unit)
        chosen = self.model._sum_rows(section, rows) if self.model.is_sum(section) else rows[:1]
        stock = sum(p.stock / p.scale * p.count for p in chosen) if chosen else 0
        stock_label = QLabel('сток ' + number(stock))
        stock_label.setStyleSheet('font-size:11px;color:#7d7d85')
        general.addWidget(stock_label)
        reset = QPushButton('Сброс')
        reset.setObjectName('statsReset')
        reset.clicked.connect(lambda _=False, s=section: self._reset(s))
        general.addWidget(reset)
        if section != 'Ловушки':
            self.editor.addLayout(general)
        if self.model.is_sum(section):
            hint = QLabel('Общий показатель меняет частные пропорционально; частные пересчитывают общий.')
            hint.setStyleSheet('font-size:11px;color:#7d7d85')
            self.editor.addWidget(hint)
        if any(p.count > 1 for p in rows):
            hint = QLabel('Один тип на несколько двигателей — правка меняет все.')
            hint.setStyleSheet('font-size:11px;color:#7d7d85')
            self.editor.addWidget(hint)
        self.table = QTableWidget(len(rows), 5)
        self.table.setObjectName('statsTable')
        self.table.setHorizontalHeaderLabels(['Параметр', 'Сток', 'Значение', '', 'Статус'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col, width in ((1, 72), (2, 120), (3, 46), (4, 120)):
            self.table.setColumnWidth(col, width)
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._limits = limits
        blocked = False
        for i, p in enumerate(rows):
            label_cell = QWidget()
            label_layout = QVBoxLayout(label_cell)
            label_layout.setContentsMargins(4, 2, 2, 2)
            label_layout.setSpacing(1)
            label = QLabel(p.label)
            label.setStyleSheet('font-size:13px')
            if p.tooltip:
                label.setToolTip(p.tooltip)
            path_label = QLabel(p.path)
            path_label.setStyleSheet('font-family:Consolas;font-size:11px;color:#7d7d85')
            path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            label_layout.addWidget(label)
            label_layout.addWidget(path_label)
            self.table.setCellWidget(i, 0, label_cell)
            self.table.setItem(i, 1, QTableWidgetItem(number(p.stock / p.scale if isinstance(p.stock, (int, float))
                                                                   else p.stock)))
            edit = QLineEdit(number(self.model.display(p)))
            edit.setObjectName('statsValue')
            edit.editingFinished.connect(lambda p=p, edit=edit: self._set_value(p, edit))
            cell = QWidget()
            cell_lay = QVBoxLayout(cell)
            cell_lay.setContentsMargins(0, 0, 0, 0)
            cell_lay.setSpacing(0)
            cell_lay.addWidget(edit)
            bounds = limits.get(p.path)
            if bounds:
                label = QLabel('%s–%s %s' % (number(bounds[0] / p.scale), number(bounds[1] / p.scale), p.unit))
                label.setStyleSheet('font-size:11px;color:#7d7d85')
                cell_lay.addWidget(label)
                if not bounds[0] <= self.model.value(p) <= bounds[1]:
                    edit.setToolTip('⚠ Таких значений в штатной технике игры нет')
                    edit.setStyleSheet('border: 1px solid #e8b64a')
                    label.setStyleSheet('font-size:11px;color:#e8b64a')
            problem = self.model.invalid(p, self.model.value(p))
            if problem:
                blocked = True
                edit.setStyleSheet('border:1px solid #ef5d5d')
            self.table.setCellWidget(i, 2, cell)
            self.table.setItem(i, 3, QTableWidgetItem(p.unit))
            self.table.setCellWidget(i, 4, self._badge(p.status))
            self.table.setRowHeight(i, 57)
        self.table.setFixedHeight(min(520, self.table.horizontalHeader().height()
                                      + sum(self.table.rowHeight(i) for i in range(len(rows))) + 4))
        self.editor.addWidget(self.table)
        self.blocked_note = QLabel('⛔ Значение вне допустимого диапазона — запись заблокирована' if blocked else '')
        self.blocked_note.setObjectName('bad')
        self.editor.addWidget(self.blocked_note)
        self.warning = QLabel('')
        self.warning.setObjectName('warn')
        self.editor.addWidget(self.warning)
        self._warning(section)
        self.editor.addStretch(1)

    def _metric_line(self, label, value, unit, callback, stock=None, tip=''):
        line = QHBoxLayout()
        title = QLabel(label)
        title.setStyleSheet('font-size:13px')
        if tip:
            title.setToolTip(tip)
        line.addWidget(title, 1)
        edit = QLineEdit(number(value))
        edit.setObjectName('statsValue')
        edit.setFixedWidth(120)
        edit.editingFinished.connect(lambda: self._metric_changed(edit, callback))
        line.addWidget(edit)
        line.addWidget(QLabel(unit))
        if stock is not None:
            hint = QLabel('сток ' + number(stock))
            hint.setStyleSheet('font-size:11px;color:#7d7d85')
            line.addWidget(hint)
        self.editor.addLayout(line)
        return edit

    def _metric_changed(self, edit, callback):
        try:
            callback(float(edit.text().replace(',', '.')))
        except (ValueError, TypeError, KeyError) as exc:
            edit.setToolTip(str(exc))
            edit.setStyleSheet('border:1px solid #ef5d5d')
            return
        self.show_section()

    def _radar(self):
        model = self.model
        limits = self._limits_by_section.get('РЛС', {})
        title = QHBoxLayout()
        title.addWidget(QLabel('РЛС'))
        title.addStretch(1)
        self.editor.addLayout(title)
        for label, metric, unit, status in (
                ('Дальность обнаружения', None, 'км', 'проверено в игре'),
                ('Обзор по азимуту, ±°', 'azimuth', '°', 'не проверено в игре'),
                ('Обзор по углу места, ±°', 'elevation', '°', 'не проверено в игре'),
                ('Ширина луча, °', 'beam', '°', 'не проверено в игре')):
            value = model.general('РЛС') if metric is None else model.radar_general(metric)
            if value is None:
                continue
            line = QHBoxLayout()
            line.addWidget(QLabel(label), 1)
            edit = QLineEdit(number(value))
            edit.setObjectName('statsValue')
            edit.setFixedWidth(120)
            callback = (lambda v: model.set_general('РЛС', v)) if metric is None else (
                lambda v, m=metric: model.set_radar_general(m, v))
            edit.editingFinished.connect(lambda e=edit, cb=callback: self._metric_changed(e, cb))
            line.addWidget(edit)
            line.addWidget(QLabel(unit))
            range_rows = [p for p in model.params if p.section == 'РЛС'
                          and p.path.startswith('transivers/') and p.path.endswith('/range')
                          and '/receiver/' not in p.path]
            search_rows = [p for p in range_rows if any(token in p.path.lower()
                           for token in ('search', 'mprf', 'hprf', 'gtm'))]
            stock = max((p.stock / p.scale for p in (search_rows or range_rows)), default=None) if metric is None else None
            bounds = limits.get(metric) if metric else None
            if bounds:
                hint = QLabel('штатно %s–%s' % tuple(map(number, bounds)))
                hint.setStyleSheet('font-size:11px;color:#7d7d85')
                if not bounds[0] <= value <= bounds[1]:
                    edit.setStyleSheet('border:1px solid #e8b64a')
                    edit.setToolTip('⚠ Таких значений в штатной технике игры нет')
                    hint.setStyleSheet('font-size:11px;color:#e8b64a')
                line.addWidget(hint)
            elif stock is not None:
                line.addWidget(QLabel('сток ' + number(stock)))
            line.addWidget(self._badge(status))
            self.editor.addLayout(line)
        note = QLabel('Общие поля меняют шаблоны поиска и передатчики пропорционально. '
                      'Шаблоны сопровождения (track, boresightLock, hmdLock) меняются только в дереве.')
        note.setWordWrap(True)
        self.editor.addWidget(note)
        reset = QPushButton('Сброс')
        reset.setObjectName('statsReset')
        reset.clicked.connect(lambda: self._reset('РЛС'))
        self.editor.addWidget(reset)
        self.editor.addStretch(1)

    def _engines(self):
        model = self.model
        wet = model.engine_mode == 'thrust'
        head = QHBoxLayout()
        head.addWidget(QLabel('Двигатель'))
        head.addStretch()
        head.addWidget(self._badge('не проверено' if wet else
                                   'проверено в игре' if model.vehicle['name'].startswith('a-26b')
                                   else 'не проверено'))
        self.editor.addLayout(head)
        unit = 'кгс' if wet else 'л.с.'
        self._metric_line('Тяга суммарно · без форсажа' if wet else 'Мощность суммарно',
                          model.engine_total(), unit,
                          lambda v: model.set_engine_total(v))
        if wet and model.engine_total(True) is not None:
            self._metric_line('Тяга суммарно · на форсаже', model.engine_total(True), unit,
                              lambda v: model.set_engine_total(v, True),
                              tip='Расчёт по ThrustMax0, AfterburnerBoost и коэффициенту форсажа у земли.')
        reset = QPushButton('Сброс')
        reset.setObjectName('statsReset')
        reset.clicked.connect(lambda: self._reset('Двигатель'))
        reset_line = QHBoxLayout()
        reset_line.addWidget(reset)
        reset_line.addStretch(1)
        self.editor.addLayout(reset_line)
        for number_, name, shared in model.engine_instances:
            title = QLabel('Двигатель %d' % number_)
            title.setStyleSheet('font-size:13px;font-weight:600')
            self.editor.addWidget(title)
            if len(shared) > 1:
                others = ', '.join(str(n) for n in shared if n != number_)
                note = QLabel('Общий тип с двигателем %s — правка меняет оба.' % others)
                note.setStyleSheet('font-size:11px;color:#7d7d85')
                self.editor.addWidget(note)
            dry, after = model.engine_parts(name)
            if dry is not None:
                self._metric_line('Без форсажа' if wet else 'Мощность', dry, unit,
                                  lambda v, name=name: model.set_engine(name, v))
            if wet and after is not None:
                self._metric_line('На форсаже', after, unit,
                                  lambda v, name=name: model.set_engine(name, v, True),
                                  tip='Расчётное значение; статус: не проверено.')
        self.editor.addStretch(1)

    def _traps(self):
        model = self.model
        head = QHBoxLayout()
        head.addWidget(QLabel('Ловушки'))
        head.addStretch()
        head.addWidget(self._badge('проверено в игре'))
        self.editor.addLayout(head)
        self._metric_line('Всего зарядов', model.general('Ловушки'), 'шт.', model.set_trap_total)
        # one slider for the flare share of every split launcher; display only, the game keeps the ratio itself
        ratio = QSlider(Qt.Horizontal)
        ratio.setRange(0, 100)
        ratio.setSingleStep(5)
        ratio.setPageStep(10)
        ratio.setValue(50)
        self.editor.addWidget(ratio)
        share = QLabel()
        share.setStyleSheet('font-size:13px;color:#a9a9b0')
        self.editor.addWidget(share)
        def update_share():
            ir_share = ratio.value()
            ir, chaff = model.trap_split((ir_share, 100 - ir_share))
            share.setText('ИК %d %% ≈ %s / дипольные %d %% ≈ %s'
                          % (ir_share, number(ir), 100 - ir_share, number(chaff)))
        ratio.valueChanged.connect(update_share)
        update_share()
        containers = model.trap_totals()['В подвесных контейнерах']
        note = QLabel('из них в подвесных контейнерах: %s' % number(containers)
                      if containers else 'контейнеров нет')
        note.setStyleSheet('font-size:12px;color:#a9a9b0')
        self.editor.addWidget(note)
        reset = QPushButton('Сброс')
        reset.setObjectName('statsReset')
        reset.clicked.connect(lambda: self._reset('Ловушки'))
        reset_line = QHBoxLayout()
        reset_line.addWidget(reset)
        reset_line.addStretch(1)
        self.editor.addLayout(reset_line)
        self.editor.addStretch(1)

    @staticmethod
    def _badge(status):
        label = QLabel('проверено' if status == 'проверено в игре' else status)
        good = status == 'проверено в игре'
        label.setFixedHeight(21)
        label.setSizePolicy(label.sizePolicy().horizontalPolicy(), label.sizePolicy().verticalPolicy())
        label.setStyleSheet('font-size:11px;border-radius:5px;padding:2px 6px;'
                            + ('background:#1f3a1a;color:#9bd36b' if good else
                               'background:#4a3509;color:#f2c25a'))
        cell = QWidget()
        cell.setFixedWidth(label.sizeHint().width() + 2)
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        layout.addStretch(1)
        return cell

    def _set_general(self, section):
        try:
            self.model.set_general(section, float(self.general_edit.text().replace(',', '.')))
        except (ValueError, TypeError) as e:
            self.warning.setText('⛔ ' + str(e))
            self.blocked_note.setText('⛔ Запись заблокирована')
            return
        self.show_section()

    def _set_trap_total(self, kind, edit):
        try:
            self.model.set_trap_total(kind, float(edit.text().replace(',', '.')))
        except (ValueError, TypeError) as exc:
            self.warning.setText('⛔ ' + str(exc))
            self.blocked_note.setText('⛔ Запись заблокирована')
            return
        self.show_section()

    def _set_value(self, p, edit):
        try:
            value = self.model.parse(p, edit.text())
            self.model.set(p, value)
        except (ValueError, TypeError) as e:
            self.warning.setText('⛔ ' + str(e))
            self.blocked_note.setText('⛔ Запись заблокирована')
            edit.setStyleSheet('border: 1px solid #ef5d5d')
            return
        self.show_section()

    def _reset(self, section):
        self.model.reset(section)
        self.show_section()

    def _warning(self, section):
        rows = self.model.for_section(section)
        notes = []
        if section == 'Масса' and self.model.vehicle['kind'] in ('air', 'heli'):
            p = next((p for p in rows if p.path == 'Mass/EmptyMass'), None)
            if p and self.model.value(p) < p.stock * .09:
                notes.append('Меньше 9 % от стока — поведение в игре не проверено.')
        if section == 'Двигатель' and self.model.vehicle['kind'] == 'air' and self.model.engine_mode == 'power':
            if any(p.path.endswith('/Main/Power') and self.model.display(p) > 2000 for p in rows):
                notes.append('Винт рассчитан на 2 000 л.с. на мотор — часть мощности может не дойти до тяги.')
        if section == 'Броня':
            notes.append('Меняется толщина; геометрия брони остаётся прежней.')
        if section == 'Двигатель' and self.model.vehicle['kind'] == 'tank':
            if any(isinstance(self.model.value(p), (int, float)) and self.model.value(p) > p.stock * 1.5
                   for p in rows if p.path.endswith('/horsePowers')):
                notes.append('КПП может упереться в обороты — проверьте трансмиссию.')
        if section == 'Ход' and self.model.vehicle['kind'] == 'ship':
            if any(p.path.endswith('/maxSpeed') and self.model.display(p) > 100 for p in rows):
                notes.append('На руле при такой скорости корабль может почти перевернуться.')
        if section == 'СПО':
            notes.append('Фактическая дальность зависит от мощности излучателя.')
        if section == 'Аэродинамика':
            notes.append('Эффект этих полей в игре ещё не подтверждён.')
        self.warning.setText(' '.join(notes) if notes else '')

    def _tree(self):
        self.editor.addWidget(QLabel('Все параметры файла · редактирование листьев'))
        search = QLineEdit()
        search.setPlaceholderText('Найти параметр или путь…')
        self.editor.addWidget(search)
        tree = QTreeWidget()
        tree.setHeaderLabels(['Параметр', 'Значение', 'Тип'])
        tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.editor.addWidget(tree, 1)

        def children(parent, node, prefix, file):
            if parent.data(0, Qt.UserRole + 1):
                return
            parent.setData(0, Qt.UserRole + 1, True)
            counts = {}
            for name, _typ, _value in node.params:
                counts[name] = counts.get(name, 0) + 1
            seen = {}
            for name, typ, stock in node.params:
                seen[name] = seen.get(name, 0) + 1
                part = name + ('[%d]' % seen[name] if counts[name] > 1 else '')
                path = prefix + part
                value = self.model.values.get((file, path), stock)
                item = QTreeWidgetItem(parent, [part, number(value), typ])
                item.setData(0, Qt.UserRole, (file, path))
                if typ in S.EDITABLE_TYPES:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
            counts = {}
            for block in node.blocks:
                counts[block.name] = counts.get(block.name, 0) + 1
            seen = {}
            for block in node.blocks:
                seen[block.name] = seen.get(block.name, 0) + 1
                part = block.name + ('[%d]' % seen[block.name] if counts[block.name] > 1 else '')
                child = QTreeWidgetItem(parent, [part])
                child.setData(0, Qt.UserRole + 2, (block, prefix + part + '/', file))
                child.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

        def expanded(item):
            data = item.data(0, Qt.UserRole + 2)
            if data:
                children(item, *data)

        def populate(query=''):
            tree.clear()
            if query:
                shown = 0
                for file, path, typ, stock in self.model.all_leaves():
                    if query.lower() not in (file + '/' + path).lower():
                        continue
                    value = self.model.values.get((file, path), stock)
                    item = QTreeWidgetItem(tree, [file + '/' + path, number(value), typ])
                    item.setData(0, Qt.UserRole, (file, path))
                    if typ in S.EDITABLE_TYPES:
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                    shown += 1
                    if shown >= 200:
                        break
                return
            for file, node in self.model.trees.items():
                root = QTreeWidgetItem(tree, [file])
                root.setData(0, Qt.UserRole + 2, (node, '', file))
                root.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

        def changed(item, column):
            if column != 1 or self._busy:
                return
            key = item.data(0, Qt.UserRole)
            if not key:
                return
            try:
                self.model.set_leaf(*key, item.text(1))
            except (ValueError, TypeError, KeyError) as e:
                self._busy = True
                item.setText(1, number(self.model.values.get(key, S.E.stock_param(self.model.trees[key[0]], key[1])[1])))
                self._busy = False
                item.setToolTip(1, str(e))

        tree.itemChanged.connect(changed)
        tree.itemExpanded.connect(expanded)
        search.textChanged.connect(populate)
        populate()
