"""Шаг «Боеприпасы»: четыре карточки макета A; данные загружаются процессом."""
import ast
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIntValidator
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea, QSpinBox, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget, QInputDialog, QProgressBar, QSizePolicy, QFrame,
                               QListWidget, QListWidgetItem)

from ..ammo.model import Ammo, Slot, AirGun
from ..ammo import catalog as C
from ..ammo import ballistics
from ..game import blk as B
from .. import edits as E
from . import workers
from .scenario_page import FlowLayout


# поля, которые в файле в метрах, а в окне — в миллиметрах
DISPLAY_SCALE = {'caliber': 1000}

class AmmoPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.model = Ammo()
        self.guns = []
        self.shells = []
        self.selected = ''
        self._generation = 0
        self._future = None
        self._details = None
        self._search_generation = 0
        self._search_future = None
        self._shell_popup = None
        self.names = {}
        self._stock_slots = [Slot() for _ in range(4)]
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 12, 18, 12)
        outer.setSpacing(5)
        title = QLabel('Боеприпасы')
        title.setObjectName('title')
        outer.addWidget(title)
        self.caption = QLabel('Выберите технику')
        outer.addWidget(self.caption)
        area = QScrollArea()
        area.setWidgetResizable(True)
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(0, 4, 0, 0)
        self.body_layout.setSpacing(10)
        self._wide = None
        self.load_card = QGroupBox('')
        self.load_lay = QVBoxLayout(self.load_card)
        self.shell_card = QGroupBox('')
        self.shell_lay = QVBoxLayout(self.shell_card)
        self.edit_card = QGroupBox('')
        self.edit_lay = QVBoxLayout(self.edit_card)
        self.tree_card = QGroupBox('')
        for card in (self.load_card, self.shell_card, self.edit_card, self.tree_card):
            card.setStyleSheet('QGroupBox::title { font-weight: bold; }')
        self.tree_lay = QVBoxLayout(self.tree_card)
        self.tree_toggle = QPushButton('Все параметры · дерево  ▸')
        self.tree_toggle.setCheckable(True)
        self.tree_toggle.toggled.connect(self._toggle_tree)
        self.tree_lay.addWidget(self.tree_toggle)
        self.tree_search = QLineEdit()
        self.tree_search.setPlaceholderText('Найти поле: mass, speed, explosionFx…')
        self.tree_search.textChanged.connect(self.filter_tree)
        self.tree_lay.addWidget(self.tree_search)
        self.tree = QTreeWidget()
        self._tree_generation = 0
        self.tree.setHeaderLabels(['Поле', 'Значение'])
        self.tree.setColumnWidth(0, 260)
        self.tree.itemChanged.connect(self.tree_changed)
        self.tree_lay.addWidget(self.tree)
        self.tree_search.hide()
        self.tree.hide()
        self._place_columns()
        area.setWidget(body)
        outer.addWidget(area)
        self.setStyleSheet('''
            AmmoPage QGroupBox { background: #232326; border: 1px solid #424246;
                border-radius: 8px; margin-top: 2px; padding: 12px 10px 10px; }
            AmmoPage QGroupBox::title { subcontrol-origin: margin; left: 14px; top: 10px;
                padding: 0 4px; font-size: 12pt; font-weight: 700; }
            AmmoPage QComboBox, AmmoPage QLineEdit { min-height: 30px; max-height: 32px;
                border-radius: 6px; background: #232326; border-color: #424246; }
            AmmoPage QPushButton { min-height: 29px; border-radius: 6px;
                background: #2b2b2f; border-color: #424246; padding: 0 9px; }
            AmmoPage QLabel#ammoMuted { color: #a9a9b0; }
            AmmoPage QLabel#ammoHint { color: #85858d; font-size: 9pt; }
            AmmoPage QLabel#ammoStatus { color: #9bd36b; background: #1f3a1a;
                border-radius: 5px; padding: 2px 6px; font-size: 9pt; }
            AmmoPage QLabel#ammoLoaded { font-weight: 700; }
            AmmoPage QPushButton#ammoChip { text-align: left; min-height: 42px;
                padding: 2px 8px; background: #2b2b2f; }
            AmmoPage QPushButton#ammoChip:checked { color: #8cc0f5; background: #12355c; }
            AmmoPage QPushButton#ammoLink { border: none; color: #a9a9b0;
                background: transparent; text-align: left; }
            AmmoPage QProgressBar::chunk { background: #78ae57; }
        ''')
        self.render()

    def ammo(self):
        if self.model.slots == self._stock_slots and not (self.model.gun or self.model.added or
                self.model.edits or self.model.air_guns or self.model.capacity != self.model.stock_capacity):
            return None
        return self.model

    def _place_columns(self):
        if self._wide is not None:
            return
        self._wide = False
        for card in (self.load_card, self.shell_card, self.edit_card, self.tree_card):
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
            self.body_layout.addWidget(card)
        self.body_layout.addStretch()

    def _toggle_tree(self, checked):
        self.tree_search.setVisible(checked)
        self.tree.setVisible(checked)
        self.tree_toggle.setText('Все параметры · дерево  ▾' if checked else 'Все параметры · дерево  ▸')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_columns()
        for combo in getattr(self, 'slot_combos', []):
            combo.setFixedWidth(min(760, max(300, self.width() - 175)))

    def set_vehicle(self, vehicle):
        self._generation += 1
        self._search_generation += 1
        if self._shell_popup is not None:
            self._shell_popup.close()
        self.model = Ammo()
        self.guns = []
        self.shells = []
        self.selected = ''
        self.names = {}
        self._stock_slots = [Slot() for _ in range(4)]
        self.caption.setText((vehicle.get('ru') or vehicle.get('en') or vehicle['name']) if vehicle else 'Выберите технику')
        self.render()
        if vehicle is None:
            return
        preset = self.win.loadout_page.lo.base if self.win.loadout_page.lo else ''
        self._future = workers.pool().submit(workers.ammo_setup, self.win.source.kind,
                                             self.win.source.root, vehicle, preset)
        self._poll(self._generation)

    def _poll(self, generation):
        if generation != self._generation or self._future is None:
            return
        if not self._future.done():
            QTimer.singleShot(40, lambda: self._poll(generation))
            return
        try:
            self.guns, self.shells, self.model.capacity, self.names = self._future.result()
            self.model.stock_capacity = self.model.capacity
            if self.shells and self.win.vehicle['kind'] not in ('air', 'heli'):
                self._stock_slots = [Slot(self.shells[0].key, self.model.capacity)] + [Slot() for _ in range(3)]
                self.model.slots = [Slot(s.shell, s.count) for s in self._stock_slots]
            if self.shells:
                self.selected = self.shells[0].key
        except Exception as exc:
            self.caption.setText('Не удалось загрузить боеприпасы: %s' % exc)
        self._future = None
        self.render()
        self.show_details()

    @staticmethod
    def _clear(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                AmmoPage._clear(item.layout())

    @staticmethod
    def _count_input(value, maximum=99999):
        edit = QLineEdit(str(value))
        edit.setValidator(QIntValidator(0, maximum, edit))
        edit.setFixedWidth(82)
        return edit

    def render(self):
        if hasattr(self, 'gun_combo'):
            self.gun_combo.deleteLater()
        self._clear(self.load_lay)
        self._clear(self.shell_lay)
        self._clear(self.edit_lay)
        vehicle = self.win.vehicle
        if vehicle is None:
            return
        load_title = QLabel('Пушки, ленты и боезапас' if vehicle['kind'] in ('air', 'heli') else 'Боекомплект')
        load_title.setStyleSheet('font-size: 12pt; font-weight: 700')
        self.load_lay.addWidget(load_title)
        shell_title = QLabel('Снаряды')
        shell_title.setStyleSheet('font-size: 12pt; font-weight: 700')
        self.shell_lay.addWidget(shell_title)
        top = QHBoxLayout()
        self.gun_combo = QComboBox(self)
        self.gun_combo.hide()
        seen_guns = set()
        for _i, path, _n in self.guns:
            if path in seen_guns:
                continue
            seen_guns.add(path)
            self.gun_combo.addItem(C.display_name(self.names, path, True), path)
            self.gun_combo.setItemData(self.gun_combo.count() - 1, path, Qt.ToolTipRole)
        gun_name = C.display_name(self.names, self.model.gun or self.guns[0][1], True) if self.guns else 'Орудие не выбрано'
        status = QLabel('проверено в игре')
        status.setObjectName('ammoStatus')
        top.addStretch()
        top.addWidget(status)
        self.load_lay.addLayout(top)
        if self.model.gun:
            i = self.gun_combo.findData(self.model.gun)
            if i >= 0:
                self.gun_combo.setCurrentIndex(i)
        self.gun_combo.currentIndexChanged.connect(self.gun_changed)
        self.slot_combos = []
        self.slot_counts = []
        if vehicle['kind'] in ('air', 'heli'):
            self.load_lay.addWidget(self._label('Пушки, ленты и патронов на ствол', 'ammoMuted'))
            for n, (_i, path, count) in enumerate(self.guns):
                gun_title = C.display_name(self.names, path, True)
                if any(word in (gun_title + ' ' + path).lower() for word in ('лтц', 'до', 'countermeasure', 'chaff', 'flare')):
                    continue
                row = QHBoxLayout()
                label = QLabel(gun_title)
                label.setToolTip(path)
                row.addWidget(label)
                belt = QComboBox()
                stock = C.shells_in(self.win.source, path)
                for s in stock:
                    belt.addItem('%s · %s' % (self._belt_name(s.name), C.kind_name(self.names, s.kind)), s.key)
                selected_air = self.model.air_guns[n] if n < len(self.model.air_guns) else None
                if selected_air and selected_air.belt:
                    belt.setCurrentIndex(max(0, belt.findData(selected_air.belt)))
                row.addWidget(belt, 1)
                spin = self._count_input(selected_air.rounds_per_barrel if selected_air else count, 50000)
                spin.setToolTip('Патронов на ствол')
                row.addWidget(spin)
                belt.currentIndexChanged.connect(lambda _v, i=n, b=belt, s=spin, p=path: self.air_changed(i, p, b, s))
                spin.textChanged.connect(lambda _v, i=n, b=belt, s=spin, p=path: self.air_changed(i, p, b, s))
                self.load_lay.addLayout(row)
            self.load_lay.addWidget(self._label('Ловушки показаны отдельно в «Характеристиках».', 'ammoHint'))
        else:
            self.load_lay.addWidget(self._label('%s · 4 ячейки миссии' % gun_name, 'ammoMuted'))
            heading = QHBoxLayout()
            for title, stretch in (('#', 0), ('Снаряд', 1), ('Шт.', 0)):
                label = self._label(title, 'ammoHint')
                if title == '#':
                    label.setFixedWidth(24)
                if title == 'Шт.':
                    label.setFixedWidth(82)
                heading.addWidget(label, stretch)
            self.load_lay.addLayout(heading)
            for i, slot in enumerate(self.model.slots):
                row = QHBoxLayout()
                row.setSpacing(8)
                number = QLabel(str(i + 1))
                number.setFixedWidth(24)
                row.addWidget(number)
                combo = QComboBox()
                combo.setFixedWidth(min(760, max(300, self.width() - 175)))
                combo.addItem('Пусто', '')
                for s in self.shells:
                    combo.addItem('%s · %s' % (C.display_name(self.names, s.name), C.kind_name(self.names, s.kind)), s.key)
                    combo.setItemData(combo.count() - 1, s.name, Qt.ToolTipRole)
                j = combo.findData(slot.shell)
                combo.setCurrentIndex(max(0, j))
                spin = self._count_input(slot.count)
                combo.currentIndexChanged.connect(lambda _v, i=i, c=combo, s=spin: self.slot_changed(i, c, s))
                spin.textChanged.connect(lambda _v, i=i, c=combo, s=spin: self.slot_changed(i, c, s))
                row.addWidget(combo, 1, Qt.AlignLeft)
                row.addWidget(spin)
                self.load_lay.addLayout(row)
                line = QFrame()
                line.setFixedHeight(1)
                line.setStyleSheet('background: #424246')
                self.load_lay.addWidget(line)
                self.slot_combos.append(combo)
                self.slot_counts.append(spin)
            self.loaded = QLabel()
            self.loaded.setObjectName('ammoLoaded')
            self.load_lay.addWidget(self.loaded)
            self.meter = QProgressBar()
            self.meter.setTextVisible(False)
            self.meter.setFixedHeight(7)
            self.load_lay.addWidget(self.meter)
            cap = QHBoxLayout()
            cap.addWidget(QLabel('Вместимость, шт.'))
            self.capacity = self._count_input(self.model.capacity)
            self.capacity.textChanged.connect(self.capacity_changed)
            cap.addWidget(self.capacity)
            cap.addStretch()
            self.load_lay.addLayout(cap)
            self._loaded()
            self.load_lay.addWidget(self._label('В миссии: bullets0..3 / bulletsCount0..3', 'ammoHint'))
        reset = QPushButton('Сбросить боекомплект')
        reset.setObjectName('ammoLink')
        reset.clicked.connect(self.reset_loadout)
        self.load_lay.addWidget(reset, 0, Qt.AlignLeft)
        shell_head = QHBoxLayout()
        shell_head.addWidget(self._label(gun_name, 'ammoMuted'), 1)
        choose = QPushButton('Выбрать орудие…')
        choose.clicked.connect(self.choose_gun)
        shell_head.addWidget(choose)
        self.shell_lay.addLayout(shell_head)
        shell_row = FlowLayout(spacing=6)
        for index, shell in enumerate(self.shells):
            col = QWidget()
            col_lay = QHBoxLayout(col)
            col_lay.setContentsMargins(0, 0, 0, 0)
            col_lay.setSpacing(0)
            shell_name = (self._belt_name(shell.name) if vehicle['kind'] in ('air', 'heli')
                          else C.display_name(self.names, shell.name))
            button = QPushButton('%s\n%s' % (shell_name, C.kind_name(self.names, shell.kind)))
            button.setObjectName('ammoChip')
            button.setToolTip(shell.name)
            button.setMinimumWidth(button.sizeHint().width())   # длинные названия кораблей не обрезать
            button.setCheckable(True)
            button.setChecked(shell.key == self.selected)
            button.clicked.connect(lambda _v=False, key=shell.key: self.select(key))
            col_lay.addWidget(button)
            if shell.key in self.model.added:
                remove = QPushButton('×')
                remove.clicked.connect(lambda _v=False, key=shell.key: self.remove(key))
                col_lay.addWidget(remove)
            shell_row.addWidget(col)
        add = QPushButton('+')
        add.setObjectName('ammoAddShell')
        add.clicked.connect(self.add_shell)
        shell_row.addWidget(add)
        self.shell_lay.addLayout(shell_row)
        self.shell_lay.addWidget(self._label('Блок боеприпаса от другого орудия копируется целиком.', 'ammoHint'))
        self.edit_lay.addWidget(self._label('Выберите снаряд для просмотра и изменения параметров.', 'ammoHint'))

    @staticmethod
    def _label(value, name):
        label = QLabel(value)
        label.setObjectName(name)
        return label

    def _belt_name(self, name):
        key = name.lower().replace('_', ' ')
        translated = self.names.get(name.lower() + '/name') or self.names.get(name.lower())
        if translated:
            return translated
        for token, label in (('air targets', 'Воздушные цели'), ('armor targets', 'Бронецели'),
                             ('stealth', 'Скрытная'), ('universal', 'Универсальная')):
            if token in key:
                return label
        return 'Стандартная' if key == 'bullet' else name

    def _loaded(self):
        if hasattr(self, 'loaded'):
            n = sum(s.count for s in self.model.slots)
            self.loaded.setText('Заряжено %d из %d%s' % (n, self.model.capacity,
                                                         ' · превышена вместимость' if self.model.capacity and n > self.model.capacity else ''))
            self.meter.setRange(0, max(1, self.model.capacity))
            self.meter.setValue(min(n, max(1, self.model.capacity)))

    def reset_loadout(self):
        self.model.slots = [Slot(s.shell, s.count) for s in self._stock_slots]
        self.model.capacity = self.model.stock_capacity
        self.render()

    def slot_changed(self, i, combo, spin):
        self.model.slots[i] = Slot(combo.currentData() or '', int(spin.text() or 0) if combo.currentData() else 0)
        self._loaded()

    def capacity_changed(self, value):
        self.model.capacity = int(value or 0)
        self._loaded()

    def air_changed(self, i, path, belt, spin):
        while len(self.model.air_guns) < i:
            self.model.air_guns.append(AirGun())
        entry = AirGun(path, belt.currentData() or '', int(spin.text() or 0))
        if len(self.model.air_guns) == i:
            self.model.air_guns.append(entry)
        else:
            self.model.air_guns[i] = entry

    def gun_changed(self):
        path = self.gun_combo.currentData()
        if not path or not self.guns:
            return
        self.model.gun = path
        self.shells = C.shells_in(self.win.source, path)
        self.selected = self.shells[0].key if self.shells else ''
        self._stock_slots = [Slot(self.shells[0].key, self.model.capacity)] + [Slot() for _ in range(3)] if self.shells else [Slot() for _ in range(4)]
        self.model.slots = [Slot(s.shell, s.count) for s in self._stock_slots]
        self.render()
        self.show_details()

    def choose_gun(self):
        query, ok = QInputDialog.getText(self, 'Орудие из игры', 'Найти в имени файла орудия:')
        if not ok or not query:
            return
        future = workers.pool().submit(workers.ammo_guns, self.win.source.kind, self.win.source.root, query)
        self._poll_picker(future, 'gun')

    def add_shell(self):
        if self._shell_popup is not None:
            self._shell_popup.close()
        popup = QWidget(self, Qt.Popup)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setObjectName('ammoSearchPopup')
        popup.setStyleSheet('''
            QWidget#ammoSearchPopup { background: #232326; border: 1px solid #55555b;
                border-radius: 8px; }
            QLineEdit, QListWidget { background: #1c1c20; color: #ececf0;
                border: 1px solid #424246; border-radius: 5px; }
            QListWidget::item { padding: 7px; }
            QListWidget::item:selected { background: #12355c; }
        ''')
        layout = QVBoxLayout(popup)
        find = QLineEdit()
        find.setPlaceholderText('Снаряд, орудие или техника…')
        results = QListWidget()
        results.setMinimumHeight(220)
        status = QLabel('Введите название снаряда, орудия или техники')
        layout.addWidget(find)
        layout.addWidget(results)
        layout.addWidget(status)
        popup.find = find
        popup.results = results
        popup.status = status
        self._shell_popup = popup
        find.textChanged.connect(self._search_shells)
        find.returnPressed.connect(lambda: self._choose_shell_result(results.currentItem()))
        results.itemClicked.connect(self._choose_shell_result)
        popup.destroyed.connect(lambda: setattr(self, '_shell_popup', None) if self._shell_popup is popup else None)
        popup.resize(min(650, max(440, self.width() - 36)), 330)
        button = self.sender()
        pos = button.mapToGlobal(button.rect().bottomLeft())
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        if screen is not None:
            bounds = screen.availableGeometry()
            pos.setX(max(bounds.left(), min(pos.x(), bounds.right() - popup.width())))
            if pos.y() + popup.height() > bounds.bottom():
                pos.setY(button.mapToGlobal(button.rect().topLeft()).y() - popup.height())
        popup.move(pos)
        popup.show()
        find.setFocus()

    def _search_shells(self, query):
        self._search_generation += 1
        generation = self._search_generation
        popup = self._shell_popup
        popup.results.clear()
        if not query.strip():
            popup.status.setText('Введите название снаряда, орудия или техники')
            return
        popup.status.setText('Поиск…')
        # A short pause avoids queuing a full catalog search for every keystroke.
        QTimer.singleShot(180, lambda: self._start_shell_search(generation, query, popup))

    def _start_shell_search(self, generation, query, popup):
        if generation != self._search_generation or popup is not self._shell_popup or not popup.isVisible():
            return
        source = self.win.source
        future = workers.pool().submit(workers.ammo_search, source.kind, source.root, query,
                                       self.win.vehicles, os.path.join(self.win.root, 'cache'))
        self._search_future = future
        self._poll_shell_search(generation, popup, future)

    def _poll_shell_search(self, generation, popup, future):
        if generation != self._search_generation or popup is not self._shell_popup or not popup.isVisible():
            return
        if not future.done():
            QTimer.singleShot(40, lambda: self._poll_shell_search(generation, popup, future))
            return
        try:
            rows = future.result()
        except Exception as exc:
            popup.status.setText('Поиск не удался: %s' % exc)
            return
        for shell, name, kind, gun, carrier, caliber, vehicle_kind in rows:
            suffix = ' · %g мм' % caliber if caliber is not None else ''
            icon = {'tank': '▣', 'air': '✈', 'heli': '⚙', 'ship': '⚓'}.get(vehicle_kind, '')
            vehicle = (icon + ' ' if icon else '') + carrier
            item = QListWidgetItem('%s · %s · %s · %s%s' % (name, kind, gun, vehicle, suffix))
            item.setToolTip(item.text())
            item.setData(Qt.UserRole, shell)
            popup.results.addItem(item)
        popup.status.setText('Найдено: %d' % len(rows) if rows else 'Ничего не найдено')
        if rows:
            popup.results.setCurrentRow(0)

    def _choose_shell_result(self, item):
        if item is None:
            return
        row = item.data(Qt.UserRole)
        if self._shell_popup is not None:
            self._shell_popup.close()
        if row.key not in {s.key for s in self.shells}:
            self.shells.append(row)
            self.model.added.append(row.key)
        self.selected = row.key
        self.render()
        self.show_details()

    def _poll_picker(self, future, mode):
        if not future.done():
            QTimer.singleShot(50, lambda: self._poll_picker(future, mode))
            return
        rows = future.result()
        names = ([p.rsplit('/', 1)[-1] for p in rows] if mode == 'gun' else
                 ['%s · %s · %s' % (s.name, s.kind, s.weapon.rsplit('/', 1)[-1]) for s in rows])
        if not names:
            return
        choice, ok = QInputDialog.getItem(self, 'Выбор из игры', 'Найдено:', names, 0, False)
        if not ok:
            return
        row = rows[names.index(choice)]
        if mode == 'gun':
            self.guns.append((len(self.guns) + 1, row, 0))
            self.model.gun = row
            self.shells = C.shells_in(self.win.source, row)
            self._stock_slots = [Slot(self.shells[0].key, self.model.capacity)] + [Slot() for _ in range(3)] if self.shells else [Slot() for _ in range(4)]
            self.model.slots = [Slot(s.shell, s.count) for s in self._stock_slots]
        else:
            if row.key not in {s.key for s in self.shells}:
                self.shells.append(row)
                self.model.added.append(row.key)
            self.selected = row.key
        self.render()
        self.show_details()

    def remove(self, key):
        self.model.added.remove(key)
        self.shells = [s for s in self.shells if s.key != key]
        self.model.slots = [Slot() if s.shell == key else s for s in self.model.slots]
        if self.selected == key:
            self.selected = self.shells[0].key if self.shells else ''
        self.render()
        self.show_details()

    def select(self, key):
        self.selected = key
        self.render()
        self.show_details()

    def show_details(self):
        if not self.selected:
            return
        key = self.selected
        future = workers.pool().submit(workers.ammo_details, self.win.source.kind, self.win.source.root, key)
        def poll():
            if key != self.selected:
                return
            if not future.done():
                QTimer.singleShot(40, poll)
                return
            block_text, _tree_text, factors = future.result()
            parsed = B.parse_text(block_text)
            if parsed.blocks:
                self._show_block(parsed.blocks[0], key, factors)
        poll()

    def _show_block(self, block, key, factors=None):
        self._clear(self.edit_lay)
        self.tree.blockSignals(True)
        self.tree.clear()
        shell = next((s for s in self.shells if s.key == key), None)
        if not shell:
            self.tree.blockSignals(False)
            return
        shell_name = (self._belt_name(shell.name) if self.win.vehicle['kind'] in ('air', 'heli')
                      else C.display_name(self.names, shell.name))
        title = QLabel('%s · %s' % (shell_name, C.kind_name(self.names, shell.kind)))
        title.setStyleSheet('font-size: 12pt; font-weight: 600')
        title.setToolTip(shell.name)
        edit_head = QHBoxLayout()
        edit_head.addWidget(title, 1)
        edit_head.addWidget(self._label('проверено в игре', 'ammoStatus'))
        self.edit_lay.addLayout(edit_head)
        self.edit_lay.addWidget(self._label('Редактор выбранного боеприпаса · значения из игры', 'ammoHint'))
        reset_fields = QPushButton('Сбросить поля')
        reset_fields.clicked.connect(lambda: self.reset_fields(key))
        self.edit_lay.addWidget(reset_fields, 0, Qt.AlignLeft)
        form = QGridLayout()
        form.setColumnMinimumWidth(0, 220)
        form.setColumnMinimumWidth(1, 220)
        form.setColumnStretch(2, 1)
        ammo_block = block.block('bullet') or block.block('rocket') or block.block('bomb') or block.block('torpedo') or block
        fields = [('Масса, кг', 'mass'), ('ВВ, кг', 'explosiveMass'), ('Начальная скорость, м/с', 'speed'),
                  ('Калибр, мм', 'caliber'), ('Пробитие струёй, мм', 'cumulativeDamage/armorPower'),
                  ('Длина сердечника, мм', 'damage/kinetic/lanzOdermattWorkingLength'),
                  ('Диаметр сердечника, мм', 'damageCaliber'),
                  ('Коэффициент Демарра', 'damage/kinetic/demarrePenetrationK'),
                  ('Ядерная мощность, кт · не проверено', 'yield'),
                  ('Вид взрыва', 'explosionFx'), ('Дальность, м', 'distToLive'),
                  ('Дальность ГСН, м', 'guidance/table0/rangeMax'),
                  ('Тип ГСН', 'guidance/type'), ('Перегрузка, g', 'maxG')]
        file = key.split('|', 1)[0]
        prefix = block.name + '/' if block.name not in ('bullet', 'rocket', 'bomb', 'torpedo') else ''
        root = self.win.source.load(file)
        field_index = 0
        for label, field in fields:
            path = prefix + ammo_block.name + '/' + field
            stock = E.stock_param(root, path) if root else None
            if stock is None:
                continue
            value = next((e.value for e in self.model.edits if e.file == file and e.path == path), stock[1])
            scale = DISPLAY_SCALE.get(field, 1)   # в файле метры, в окне — миллиметры
            edit = QLineEdit('%g' % (value * scale) if isinstance(value, (int, float)) else str(value))
            edit.setMaximumWidth(190)
            edit.editingFinished.connect(lambda p=path, w=edit, r=root, f=file, k=scale:
                                         self.field_changed(r, f, p, w, k))
            row, col = divmod(field_index, 2)
            field_index += 1
            field_box = QVBoxLayout()
            field_box.addWidget(self._label(label, 'ammoMuted'))
            field_box.addWidget(edit)
            field_box.addWidget(self._label('сток: %s' % ('%g' % (stock[1] * scale) if isinstance(stock[1], (int, float)) else str(stock[1])), 'ammoHint'))
            form.addLayout(field_box, row, col)
        self.edit_lay.addLayout(form)
        if ammo_block.get('explosiveMass') is not None:
            self.edit_lay.addWidget(QLabel('Тротил-эквивалент: ≈ %.2f кг TNT' %
                                       ballistics.tnt_equivalent(ammo_block, factors)))
        pens = [ballistics.penetration(ammo_block, d) for d in (0, 500, 1000, 2000)]
        if pens[0] is not None:
            self.edit_lay.addWidget(QLabel('Пробитие · расчётная подсказка, мм'))
            pen_table = QGridLayout()
            pen_table.addWidget(self._label('Дистанция', 'ammoMuted'), 0, 0)
            for col, (distance, value) in enumerate(zip((0, 500, 1000, 2000), pens), 1):
                if value is None:
                    continue
                pen_table.addWidget(self._label('%d м' % distance, 'ammoMuted'), 0, col)
                pen_table.addWidget(QLabel('%.0f' % value), 1, col)
            pen_table.addWidget(QLabel('Расчёт'), 1, 0)
            self.edit_lay.addLayout(pen_table)
        hint = QLabel('Расчётная подсказка WTFTD; скорость на дистанции — только из файла игры.')
        hint.setWordWrap(True)
        self.edit_lay.addWidget(hint)
        def walk(node, parent, path):
            totals = {}   # сколько раз встречается имя — один проход, а не на каждое поле
            for name, _typ, _val in node.params:
                totals[name] = totals.get(name, 0) + 1
            counts = {}
            for name, typ, val in node.params:
                counts[name] = counts.get(name, 0) + 1
                part = name + ('[%d]' % counts[name] if totals[name] > 1 else '')
                leaf = QTreeWidgetItem(parent, [name, str(val)])
                leaf.setData(0, Qt.UserRole, (file, path + '/' + part, typ))
                leaf.setFlags(leaf.flags() | Qt.ItemIsEditable)
            totals = {}
            for child in node.blocks:
                totals[child.name] = totals.get(child.name, 0) + 1
            counts = {}
            for child in node.blocks:
                counts[child.name] = counts.get(child.name, 0) + 1
                part = child.name + ('[%d]' % counts[child.name] if totals[child.name] > 1 else '')
                item = QTreeWidgetItem(parent, [child.name, ''])
                walk(child, item, path + '/' + part)
        def fill(generation=self._tree_generation + 1):
            # дерево — отдельным шагом цикла событий: показ вкладки не ждёт сотни строк дерева
            if generation != self._tree_generation:
                return
            self.tree.blockSignals(True)
            top = QTreeWidgetItem(self.tree, [file, ''])
            item = QTreeWidgetItem(top, [block.name, ''])
            walk(block, item, block.name)
            self.tree.expandToDepth(1)
            self.tree.blockSignals(False)
            self.filter_tree(self.tree_search.text())
        self._tree_generation += 1
        self.tree.blockSignals(False)
        QTimer.singleShot(0, fill)

    def reset_fields(self, key):
        file, block = key.split('|', 1)
        self.model.edits = [e for e in self.model.edits if not (e.file == file and e.path.startswith(block + '/'))]
        self.show_details()

    def filter_tree(self, query):
        q = query.strip().lower()
        def visit(item):
            own = q in (item.text(0) + ' ' + item.text(1)).lower()
            children = [visit(item.child(i)) for i in range(item.childCount())]
            visible = not q or own or any(children)
            item.setHidden(not visible)
            if q and visible:
                item.setExpanded(True)
            return visible
        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))

    def tree_changed(self, item, column):
        if column != 1:
            return
        ref = item.data(0, Qt.UserRole)
        if not ref:
            return
        file, path, typ = ref
        try:
            raw = item.text(1)
            value = raw if typ == 't' else raw.lower() in ('true', 'yes', '1') if typ == 'b' else (
                ast.literal_eval(raw) if typ not in ('i', 'i64', 'r') else float(raw))
            edit = E.make_edit(self.win.source.load(file), file, path, value)
            self.model.edits = [e for e in self.model.edits if not (e.file == file and e.path == path)] + [edit]
            item.setForeground(1, Qt.GlobalColor.green)
        except (TypeError, ValueError, KeyError, SyntaxError):
            item.setForeground(1, Qt.GlobalColor.red)

    def field_changed(self, tree, file, path, widget, scale=1):
        try:
            typ, _stock = E.stock_param(tree, path)
            value = widget.text() if typ == 't' else float(widget.text().replace(',', '.')) / scale
            edit = E.make_edit(tree, file, path, value)
            self.model.edits = [e for e in self.model.edits if not (e.file == file and e.path == path)] + [edit]
            widget.setStyleSheet('')
        except (TypeError, ValueError, KeyError):
            widget.setStyleSheet('border: 1px solid #f08080')
