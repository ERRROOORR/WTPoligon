"""Вкладка сценария по docs/mockups/scenarios_47.html; состояние и расчёты — wtpoligon.scenarios."""
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import QLayout, QSizePolicy
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QListWidget, QPushButton, QScrollArea, QSpinBox,
                               QVBoxLayout, QWidget)

from ..scenarios import autopick as A, catalog as C, validate as V
from ..scenarios.model import Scenario
from . import workers

MODES = [('ground', 'Наземка'), ('air', 'Самолёт'), ('heli', 'Вертолёт'), ('naval', 'Флот'), ('duel', 'Дуэль')]
MAPS = [('Тунис', 'tunisia'), ('Израиль', 'israel'), ('Дания', 'denmark'),
        ('Экваториальный остров', 'equatorial_island'), ('Афганистан', 'afghan'), ('Ладога', 'ladoga')]


class FlowLayout(QLayout):
    """A compact wrapping row for target chips."""

    def __init__(self, parent=None, spacing=5):
        super().__init__(parent)
        self._items = []
        self.setSpacing(spacing)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size + QSize(0, 2 * self.contentsMargins().top())

    def _arrange(self, rect, measure):
        margins = self.contentsMargins()
        left = rect.x() + margins.left()
        right = rect.right() - margins.right()
        x, y, row_height = left, rect.y() + margins.top(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x > left and x + hint.width() - 1 > right:
                x, y, row_height = left, y + row_height + self.spacing(), 0
            if not measure:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self.spacing()
            row_height = max(row_height, hint.height())
        return y + row_height + margins.bottom() - rect.y()


def choice(items, value):
    w = QComboBox()
    for title, key in items:
        w.addItem(title, key)
    w.setCurrentIndex(max(0, w.findData(value)))
    return w


class NumberEdit(QLineEdit):
    valueChanged = Signal(object)

    def __init__(self, value=0, lo=0, hi=100, decimals=0):
        super().__init__()
        self.lo, self.hi, self.decimals = lo, hi, decimals
        self.setValue(value)
        self.editingFinished.connect(self._commit)

    def setRange(self, lo, hi):
        self.lo, self.hi = lo, hi
        self.setValue(self.value())

    def setSingleStep(self, _step):
        pass

    def value(self):
        try:
            return float(self.text().replace(',', '.')) if self.decimals else int(self.text())
        except ValueError:
            return self.lo

    def setValue(self, value):
        value = min(self.hi, max(self.lo, float(value)))
        value = round(value, self.decimals) if self.decimals else int(value)
        self.setText(str(value).replace('.', ','))

    def _commit(self):
        old = self.text()
        changed = self.isModified()
        value = self.value()
        self.setValue(value)
        if self.text() != old or changed:
            self.valueChanged.emit(value)
        self.setModified(False)


def spin(value, lo, hi):
    return NumberEdit(value, lo, hi)


def badge(verified=False):
    w = QLabel('проверено в игре' if verified else 'не проверено')
    w.setObjectName('badge')
    w.setProperty('verified', verified)
    w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return w


def field(label, widget, width=None):
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(3)
    caption = QLabel(label)
    caption.setObjectName('scenarioCaption')
    lay.addWidget(caption)
    if width:
        widget.setFixedWidth(width)
    lay.addWidget(widget)
    return box


def line():
    rule = QFrame()
    rule.setObjectName('scenarioLine')
    rule.setFixedHeight(1)
    return rule


class ScenarioPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.model = Scenario()
        self._vehicle = None
        self._seed = 0
        self._generation = 0
        self._pending = None
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        column = QWidget()
        column.setMaximumWidth(1600)   # на широком окне — две колонки (render), не пустая половина экрана
        outer.addWidget(column, 1)
        content = QVBoxLayout(column)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(10)
        top = QHBoxLayout()
        heading = QLabel('Сценарии')
        heading.setObjectName('h1')
        top.addWidget(heading, 1)
        self.player_button = QLabel('Ваша техника')   # машина выбирается на шаге «Техника», здесь только показ
        self.player_button.setObjectName('scenarioPlayer')
        top.addWidget(self.player_button)
        top.addWidget(QLabel('БР'))
        self.player_br = NumberEdit(1, 1, 14, 1)
        self.player_br.setFixedWidth(72)
        self.player_br.setRange(1, 14)
        self.player_br.setSingleStep(.1)
        self.player_br.valueChanged.connect(lambda v: setattr(self.model, 'player_br', v))
        top.addWidget(self.player_br)
        content.addLayout(top)
        modes = QHBoxLayout()
        self.mode_buttons = {}
        for key, title in MODES:
            button = QPushButton(title)
            button.setObjectName('scenarioMode')
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, k=key: self.set_mode(k))
            modes.addWidget(button)
            self.mode_buttons[key] = button
        content.addLayout(modes)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.body = QWidget()
        self.body_layout = QGridLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setHorizontalSpacing(12)
        self.columns = [QVBoxLayout(), QVBoxLayout()]
        for column_layout in self.columns:
            column_layout.setSpacing(10)
        self._column = self.columns[0]
        self._wide = None
        scroll.setWidget(self.body)
        content.addWidget(scroll, 1)
        self.setStyleSheet('''
            ScenarioPage QFrame#scenarioSection { border: none; background: transparent; }
            ScenarioPage QFrame#scenarioLine { border: none; background: #3a3a40; }
            ScenarioPage QLabel#scenarioCaption { color: #a9a9b0; font-size: 9pt; }
            ScenarioPage QLabel#scenarioMuted { color: #a9a9b0; font-size: 9pt; }
            ScenarioPage QLabel#scenarioCategory { font-weight: 600; }
            ScenarioPage QFrame#scenarioChip { background: #1e2530; border: 1px solid #3b526b;
                border-radius: 6px; }
            ScenarioPage QPushButton#scenarioMini { min-height: 27px; padding: 0 8px; border-radius: 6px;
                font-size: 9pt; }
            ScenarioPage QPushButton#scenarioAuto { min-height: 28px; padding: 0 9px;
                color: #8cc0f5; background: #12355c; border: 1px solid #527ba4;
                border-radius: 6px; font-size: 9pt; }
            ScenarioPage QPushButton#scenarioMode:checked { color: #8cc0f5;
                background: #12355c; border-color: #527ba4; }
            ScenarioPage QPushButton#scenarioRemove { min-width: 18px; max-width: 18px;
                min-height: 22px; padding: 0; background: transparent; border: none; }
            ScenarioPage QSpinBox, ScenarioPage QDoubleSpinBox { color: #ececec;
                background: #2b2b2f; padding: 0 3px; }
            ScenarioPage QFrame#card { border-radius: 8px; }
            ScenarioPage QLabel#badge[verified="true"] { background: #1f3a1a; color: #9bd36b; }
        ''')
        self.render()

    def set_vehicle(self, vehicle):
        if vehicle is None:
            return
        self._vehicle = vehicle
        new_mode = {'tank': 'ground', 'ship': 'naval'}.get(vehicle['kind'], vehicle['kind'])
        self.model.mode = new_mode
        self.model.player = vehicle['name']
        self.model.player_br = vehicle.get('br') or 5.0
        self.player_br.blockSignals(True)
        self.player_br.setValue(self.model.player_br)
        self.player_br.blockSignals(False)
        self._generation += 1
        generation = self._generation
        if len(self.win.vehicles) < 100:
            A.refill_all(self.model, self.win.vehicles, self._seed)
            self._finish_vehicle()
        else:
            self._pending = workers.pool().submit(workers.scenario, self.model.to_dict(),
                                                  self.win.vehicles, self._seed)
            self.body.hide()
            QTimer.singleShot(30, lambda: self._poll_vehicle(generation))

    def _poll_vehicle(self, generation):
        if generation != self._generation or self._pending is None:
            return
        if not self._pending.done():
            QTimer.singleShot(30, lambda: self._poll_vehicle(generation))
            return
        try:
            self.model = Scenario.from_dict(self._pending.result())
        except Exception:
            self._pending = None
            self.body.show()
            return
        self._pending = None
        self._finish_vehicle()

    def _finish_vehicle(self):
        for key, _, _ in C.CATEGORIES[self.model.mode]:
            cat = self.model.categories[key]
            if not cat.targets:
                cat.count = 0
        self.render()
        self.body.show()

    def load(self, scenario):
        self.model = Scenario.from_dict(scenario.to_dict()) if hasattr(scenario, 'to_dict') else Scenario.from_dict(scenario)
        self.render()

    def scenario(self):
        return self.model

    def own_mode(self):
        """Режим выезда задаёт машина, выбранная на шаге «Техника»; авиации доступна ещё дуэль."""
        kind = (self._vehicle or {}).get('kind')
        return {'tank': 'ground', 'ship': 'naval'}.get(kind, kind) if kind else self.model.mode

    def allowed_modes(self):
        own = self.own_mode()
        return [own, 'duel'] if own in ('air', 'heli') else [own]

    def set_mode(self, mode):
        if mode not in self.allowed_modes():
            return   # машину здесь не меняем — она выбрана на шаге «Техника»
        self.model.mode = mode
        self.render()

    def _clear(self):
        for column_layout in self.columns:
            while column_layout.count():
                item = column_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def _place_columns(self):
        """Шире 1200 px — цели слева, условия и правила справа; уже — одна колонка, как в макете."""
        wide = self.width() >= 1200
        if wide == self._wide:
            return
        self._wide = wide
        for column_layout in self.columns:
            self.body_layout.removeItem(column_layout)
        if wide:
            self.body_layout.addLayout(self.columns[0], 0, 0)
            self.body_layout.addLayout(self.columns[1], 0, 1)
            self.body_layout.setColumnStretch(0, 3)
            self.body_layout.setColumnStretch(1, 2)
        else:
            self.body_layout.addLayout(self.columns[1], 0, 0)
            self.body_layout.addLayout(self.columns[0], 1, 0)
            self.body_layout.setColumnStretch(0, 1)
            self.body_layout.setColumnStretch(1, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_columns()

    def _card(self, title):
        card = QFrame()
        card.setObjectName('card')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setObjectName('title')
        header = QHBoxLayout()
        header.addWidget(heading)
        header.addStretch(1)
        layout.addLayout(header)
        self._column.addWidget(card)
        return layout, header

    def render(self):
        self._clear()
        self.player_button.setText((self._vehicle or {}).get('ru') or (self._vehicle or {}).get('en') or
                                   self.model.player or 'Ваша техника')
        allowed = self.allowed_modes()
        for key, button in self.mode_buttons.items():
            button.setVisible(key in allowed and len(allowed) > 1)   # один режим — кнопка не нужна
            button.setChecked(key == self.model.mode)
        self._place_columns()
        self._column = self.columns[1]
        self._conditions()
        self._rules()
        self._column = self.columns[0]
        if self.model.mode == 'duel':
            self._duel()
        else:
            self._targets()
        for column_layout in self.columns:
            column_layout.addStretch(1)

    def _conditions(self):
        c = self.model.conditions
        card, _ = self._card('Карта и условия')
        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        card.addLayout(form)
        row_number = 0

        def add(label, widget):
            nonlocal row_number
            wrapper = field(label, widget)
            wrapper.layout().itemAt(0).widget().setWordWrap(True)
            form.addWidget(wrapper, row_number // 2, row_number % 2)
            row_number += 1
        if self.model.mode in ('air', 'heli', 'duel'):
            w = choice(MAPS, c.map)
            w.currentIndexChanged.connect(lambda: setattr(c, 'map', w.currentData()))
            add('Карта (как в пробном вылете)', w)
        else:
            add('Карта', QLabel('Полигон тест-драйва танков' if self.model.mode == 'ground'
                               else 'Морской полигон тест-драйва кораблей'))
        for label, values, attr in [('Время суток', [('День', 'Day'), ('Рассвет', 'Dawn'),
                                                ('Закат', 'Dusk'), ('Ночь', 'Night')], 'time'),
                                    ('Погода', [('Ясно', 'good'), ('Облачно', 'cloudy'),
                                                ('Дождь', 'rain'), ('Снег', 'blind')], 'weather'),
                                    ('Режим игры', [('Как в миссии', ''), ('Аркадный', 'arcade'),
                                                    ('Реалистичный', 'realistic'), ('Симуляторный', 'simulator')],
                                     'difficulty')]:
            w = choice(values, getattr(c, attr))
            w.currentIndexChanged.connect(lambda _i, x=w, a=attr: setattr(c, a, x.currentData()))
            add(label, w)
        if self.model.mode in ('air', 'heli', 'duel'):
            alt = spin(c.start_altitude, 128, 100000)
            alt.valueChanged.connect(lambda v: setattr(c, 'start_altitude', v))
            add('Высота старта, м (128–100 000)', alt)
            speed = spin(c.start_speed, 0, 3000)
            speed.valueChanged.connect(lambda v: setattr(c, 'start_speed', v))
            add('Скорость старта, км/ч (0 — авто)', speed)
        if self.model.mode == 'heli':
            ground = QCheckBox('Старт с земли')
            ground.setChecked(c.ground_start)
            ground.toggled.connect(lambda v: setattr(c, 'ground_start', v))
            card.addWidget(ground)
            card.addWidget(badge())

    def _targets(self):
        card, header = self._card('Цели')
        auto = QPushButton('Подобрать по БР')
        auto.setObjectName('scenarioAuto')
        auto.clicked.connect(self._auto_all)
        header.addWidget(auto)
        if self.model.mode in ('air', 'heli'):
            row = QHBoxLayout()
            row.addWidget(QLabel('Высота воздушных целей:'))
            alt = choice([('Все высоты', 'mixed'), ('Низкие (до 1 км)', 'low'),
                          ('Средние (2–6,5 км)', 'mid'), ('Высокие (8–15 км)', 'high')],
                         self.model.conditions.air_altitude)
            alt.currentIndexChanged.connect(lambda: setattr(self.model.conditions, 'air_altitude', alt.currentData()))
            row.addWidget(alt)
            row.addWidget(badge())
            card.addLayout(row)
        vehicle_map = C.vehicle_map(self.win.vehicles)
        for index, (key, title, description) in enumerate(C.CATEGORIES[self.model.mode]):
            cat = self.model.categories[key]
            if index:
                card.addWidget(line())
            section = QFrame()
            section.setObjectName('scenarioSection')
            # как в макете: заголовок и «сколько» справа, ниже галочки, поля и цели на всю ширину
            lay = QVBoxLayout(section)
            lay.setContentsMargins(0, 3, 0, 3)
            lay.setSpacing(6)
            head = QHBoxLayout()
            names = QVBoxLayout()
            names.setSpacing(2)
            title_label = QLabel(title)
            title_label.setObjectName('scenarioCategory')
            names.addWidget(title_label)
            if description:
                desc = QLabel(description)
                desc.setObjectName('scenarioMuted')
                desc.setWordWrap(True)
                names.addWidget(desc)
            head.addLayout(names, 1)
            count = spin(cat.count, 0, 20)
            count.setObjectName('count_' + key)
            count.valueChanged.connect(lambda n, k=key: self._set_count(k, n))
            head.addWidget(field('сколько', count, 70), 0, Qt.AlignTop)
            lay.addLayout(head)
            flags = QHBoxLayout()
            flags.setSpacing(6)
            shoot = QCheckBox('стреляют по вам')
            shoot.setChecked(cat.shoots)
            shoot.toggled.connect(lambda v, x=cat: setattr(x, 'shoots', v))
            flags.addWidget(shoot)
            flags.addWidget(badge(True))
            if key in ('air', 'fighters', 'spaa'):
                flags.addSpacing(14)
                radar = QCheckBox('РЛС бота')
                radar.setChecked(cat.radar)
                radar.toggled.connect(lambda v, x=cat: setattr(x, 'radar', v))
                flags.addWidget(radar)
                flags.addWidget(badge(True))
            flags.addStretch(1)
            lay.addLayout(flags)
            main = QWidget()
            main_lay = QVBoxLayout(main)
            main_lay.setContentsMargins(0, 0, 0, 0)
            main_lay.setSpacing(7)
            tuning = QHBoxLayout()
            tuning.setSpacing(6)
            for text, attr in [('БР от', 'br_min'), ('до', 'br_max')]:
                value = NumberEdit(0, -14, 14, 1)
                value.setRange(-14, 14)
                value.setSingleStep(.1)
                value.setValue(getattr(cat, attr))
                value.valueChanged.connect(lambda n, a=attr, x=cat: setattr(x, a, n))
                tuning.addWidget(field(text, value, 65))
            reference = QLabel('от БР %s' % str(self.model.player_br).replace('.', ','))
            reference.setObjectName('scenarioMuted')
            tuning.addWidget(reference, 0, Qt.AlignBottom)
            dist = choice(([(str(x) + ' м', x) for x in (0, 300, 1200, 2000)] if key in ('ground', 'spaa')
                           else [(str(x // 1000) + ' км', x) for x in (3000, 10000, 30000)])
                          + [('Своя…', -1)], cat.distance)
            if dist.findData(cat.distance) < 0:
                dist.insertItem(dist.count() - 1, str(cat.distance) + ' м', cat.distance)
                dist.setCurrentIndex(dist.findData(cat.distance))
            dist.currentIndexChanged.connect(lambda _i, k=key, w=dist: self._distance(k, w))
            tuning.addWidget(field('Дистанция', dist, 105))
            tuning.addWidget(badge(V.status('distance_ground' if key in ('ground', 'spaa')
                                            else 'distance_bot', cat.distance) == 'проверено в игре'),
                             0, Qt.AlignBottom)
            tuning.addStretch(1)
            main_lay.addLayout(tuning)
            chips = FlowLayout()
            for i, target in enumerate(cat.targets):
                vehicle = vehicle_map.get(target.vehicle, {})
                chip = QFrame()
                chip.setObjectName('scenarioChip')
                chip_lay = QHBoxLayout(chip)
                chip_lay.setContentsMargins(5, 2, 4, 2)
                chip_lay.setSpacing(4)
                icon = {'tank': '▣', 'air': '✈', 'heli': '⚙', 'ship': '⚓'}.get(vehicle.get('kind'), '◆')
                chip_lay.addWidget(QLabel(icon))
                name = vehicle.get('ru') or vehicle.get('en') or target.vehicle
                name_label = QLabel(name)
                name_label.setMaximumWidth(170)
                name_label.setToolTip(name)
                chip_lay.addWidget(name_label)
                br_label = QLabel('БР %s' % str(vehicle.get('br') or '—').replace('.', ','))
                br_label.setObjectName('scenarioMuted')
                chip_lay.addWidget(br_label)
                chip_lay.addWidget(QLabel('×'))
                mult = spin(target.count, 1, 20)
                mult.setFixedWidth(40)
                mult.valueChanged.connect(lambda v, k=key, j=i: self._mult(k, j, v))
                chip_lay.addWidget(mult)
                remove = QPushButton('×')
                remove.setObjectName('scenarioRemove')
                remove.clicked.connect(lambda _=False, k=key, j=i: self._remove(k, j))
                chip_lay.addWidget(remove)
                chips.addWidget(chip)
            add = QPushButton('+ добавить')
            add.setObjectName('scenarioMini')
            add.clicked.connect(lambda _=False, k=key: self._add(k))
            chips.addWidget(add)
            main_lay.addLayout(chips)
            actions = QHBoxLayout()
            reroll = QPushButton('Перебрать категорию')
            reroll.setObjectName('scenarioMini')
            reroll.clicked.connect(lambda _=False, k=key: self._reroll(k))
            actions.addWidget(reroll)
            total = QLabel('%d из %d' % (cat.total(), cat.count))
            total.setObjectName('scenarioMuted')
            actions.addWidget(total)
            actions.addStretch(1)
            main_lay.addLayout(actions)
            lay.addWidget(main)
            card.addWidget(section)

    def _duel(self):
        d = self.model.duel
        card, _ = self._card('Противник')
        pick = QPushButton(d.enemy or 'Выбрать…')
        pick.clicked.connect(self._pick_duel)
        card.addWidget(pick)
        form = QFormLayout()
        card.addLayout(form)
        presets = []
        if d.enemy:
            enemy = C.vehicle_map(self.win.vehicles).get(d.enemy)
            unit = self.win.source.load(enemy['file']) if enemy else None
            block = unit.block('weapon_presets') if unit else None
            presets = [(p.get('name'), p.get('name')) for p in (block.blocks if block else []) if p.get('name')]
        loadout = choice([('Как в игре', ''), ('Без подвески', 'none')] + presets, d.loadout)
        loadout.currentIndexChanged.connect(lambda: setattr(d, 'loadout', loadout.currentData()))
        form.addRow('Подвеска противника', loadout)
        for label, attr, lo, hi in [('Сколько противников', 'count', 1, 8),
                                     ('Дистанция на старте, м', 'distance', 1000, 200000),
                                     ('Высота противника, м (0 — как у вас)', 'altitude', 0, 100000)]:
            w = spin(getattr(d, attr), lo, hi)
            w.valueChanged.connect(lambda v, a=attr: setattr(d, a, v))
            form.addRow(label, w)
        shoot = QCheckBox('Противник стреляет')
        shoot.setChecked(d.shoots)
        shoot.toggled.connect(lambda v: setattr(d, 'shoots', v))
        card.addWidget(shoot)
        card.addWidget(badge(True))

    def _rules(self):
        r = self.model.rules
        card, _ = self._card('Правила')
        choices = [('markers', 'Маркеры над целями'), ('restore_targets', 'Цели возвращаются'),
                   ('restore_ammo', 'Пополнять боезапас'), ('infinite_fuel', 'Бесконечное топливо')]
        if self.model.mode in ('air', 'heli', 'duel'):
            choices.append(('player_respawn', 'Возрождение после крушения'))
        if self.model.mode in ('air', 'heli'):
            choices.append(('moving_ships', 'Корабли-цели плывут'))
        for key, title in choices:
            row = QHBoxLayout()
            w = QCheckBox(title)
            w.setChecked(getattr(r, key))
            w.toggled.connect(lambda v, k=key: setattr(r, k, v))
            row.addWidget(w, 1)
            row.addWidget(badge())
            card.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel('Быстрая перезарядка и ремонт'))
        rapid = spin(r.rapid_reload, 0, 3600)
        rapid.valueChanged.connect(lambda v: setattr(r, 'rapid_reload', v))
        row.addWidget(rapid)
        row.addWidget(QLabel('сек (0 — выключено)'))
        row.addWidget(badge())
        card.addLayout(row)

    def _auto_all(self):
        A.refill_all(self.model, self.win.vehicles, self._seed)
        for key, _, _ in C.CATEGORIES[self.model.mode]:
            cat = self.model.categories[key]
            if not cat.targets:
                cat.count = 0
        self.render()

    def _set_count(self, key, count):
        self.model.categories[key].count = count
        A.refill(self.model, self.win.vehicles, key, self._seed)
        self.render()

    def _reroll(self, key):
        self._seed += 1
        A.refill(self.model, self.win.vehicles, key, self._seed, True)
        self.render()

    def _remove(self, key, index):
        A.remove(self.model, key, index)
        self.render()

    def _mult(self, key, index, count):
        cat = self.model.categories[key]
        cat.targets[index].count = count
        cat.count = cat.total()
        self.render()

    def _distance(self, key, widget):
        value = widget.currentData()
        if value == -1:
            value, ok = QInputDialog.getInt(self, 'Дистанция', 'Метры:', self.model.categories[key].distance,
                                            0, 200000)
            if not ok:
                return
        self.model.categories[key].distance = value
        self.render()

    def _pick_vehicle(self, candidates, title):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(580, 620)
        layout = QVBoxLayout(dialog)
        search = QLineEdit()
        search.setPlaceholderText('Поиск по всей технике…')
        layout.addWidget(search)
        results = QListWidget()
        layout.addWidget(results)
        shown = []

        def refresh(text=''):
            shown.clear()
            results.clear()
            query = text.casefold().strip()
            for vehicle in candidates:
                name = vehicle.get('ru') or vehicle.get('en') or vehicle['name']
                if query and query not in (name + ' ' + vehicle['name']).casefold():
                    continue
                shown.append(vehicle)
                results.addItem('%s · %s · БР %s' % (name, vehicle['name'], vehicle.get('br') or '—'))
                if len(shown) >= 200:
                    break

        search.textChanged.connect(refresh)
        results.itemDoubleClicked.connect(lambda _item: dialog.accept())
        refresh()
        search.setFocus()
        if dialog.exec() == QDialog.Accepted and results.currentRow() >= 0:
            return shown[results.currentRow()]
        return None

    def _add(self, key):
        pool = [v for v in self.win.vehicles if C.eligible(v, key, self.model.mode)]
        vehicle = self._pick_vehicle(pool, 'Добавить цель')
        if vehicle:
            A.add(self.model, key, vehicle['name'])
            self.render()

    def _pick_duel(self):
        vehicle = self._pick_vehicle([v for v in self.win.vehicles if v['kind'] in ('air', 'heli')], 'Противник')
        if vehicle:
            self.model.duel.enemy = vehicle['name']
            self.model.duel.loadout = ''
            self.render()
