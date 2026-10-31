"""Шаг «Подвеска» (этап 3, ТЗ §6.4; макет A, 26.10 — выбран пользователем): сверху ряд карточек пилонов с
иконками вооружения из игры (atlases.vromfs.bin, как в меню подвески War Thunder), ниже — выбор для выбранного
пилона: штатное этого пилона одним списком, сгруппированным по классам (бомбы, управляемые бомбы, ракеты…), или любое
оружие игры с поиском; справа — сводка (масса, перекос, что висит, невесомая подвеска). Всё значение — в loadout.py;
страница только показывает и меняет Loadout."""
import os

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
                               QLabel, QLayout, QLineEdit, QMenu, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
                               QSpinBox, QToolButton, QVBoxLayout, QWidget)

from .. import build as BL
from .. import loadout as L
from ..game.source import open_source
from . import workers

# короткие названия классов для фильтров (полные — в подсказке и заголовках групп)
GROUP_SHORT = {'aam': 'Ракеты В-В', 'agm': 'Ракеты В-П', 'rockets': 'НАР', 'guided': 'Управляемые бомбы',
               'glide': 'Планирующие бомбы', 'bombs': 'Бомбы', 'torpedoes': 'Торпеды', 'tanks': 'Баки',
               'pods': 'Контейнеры', 'guns': 'Пушки', 'other': 'Прочее'}
ANY_LIMIT = 160          # сколько карточек «любого оружия» показывать за раз (дальше — уточнить поиск)
COLUMNS = 4            # колонок плиток на широком окне; на узком — меньше (OPTION_W на плитку)
OPTION_W = 250
# иконка по классу, если у оружия своей нет (оружие наземки/флота на пилоне — ТЗ §6.6)
GROUP_ICONS = {'aam': 'missile_type_b_air_to_air', 'agm': 'agm_missile', 'rockets': 'nar_small_group_3',
               'guided': 'guided_bomb_middle_laser', 'glide': 'glide_guided_bomb_middle_jdam', 'bombs': 'bombs_middle',
               'torpedoes': 'air_torpedo', 'tanks': 'ptb', 'pods': 'flir_container', 'guns': '', 'other': ''}


def _label(text='', name=None, wrap=True):
    w = QLabel(text)
    w.setWordWrap(wrap)
    if name:
        w.setObjectName(name)
    return w


def _restyle(w, **props):
    for k, v in props.items():
        w.setProperty(k, v)
    w.style().unpolish(w)
    w.style().polish(w)


class FlowLayout(QLayout):
    """Раскладка «как текст»: элементы слева направо, не влезло — на следующую строку."""

    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self.items, self.gap = [], spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, i):
        return self.items[i] if 0 <= i < len(self.items) else None

    def takeAt(self, i):
        return self.items.pop(i) if 0 <= i < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._place(QRect(0, 0, width, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._place(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for it in self.items:
            size = size.expandedTo(it.minimumSize())
        return size

    def _place(self, rect, apply):
        x, y, line = rect.x(), rect.y(), 0
        for it in self.items:
            hint = it.sizeHint()
            if x + hint.width() > rect.right() + 1 and line:
                x, y, line = rect.x(), y + line + self.gap, 0
            if apply:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self.gap
            line = max(line, hint.height())
        return y + line - rect.y()


def _clear(layout):
    """Убрать всё из раскладки сразу (deleteLater оставляет старые виджеты видимыми до конца события)."""
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.setParent(None)
            w.deleteLater()


def _kg(x):
    return ('%s кг' % format(round(x), ',').replace(',', ' ')) if x else ''


class CatalogLoader(QThread):
    """Сборка каталога оружия в отдельном потоке и со своим источником (файлы игры читаются независимо от окна)."""
    progress = Signal(int, int)

    def __init__(self, source, cache_dir):
        super().__init__()
        self.kind, self.root, self.cache_dir = source.kind, source.root, cache_dir
        self.catalog, self.error = None, ''

    def run(self):
        try:
            self.catalog = workers.pool().submit(workers.catalog, self.kind, self.root, self.cache_dir).result()
        except InterruptedError:
            self.error = 'прервано'
        except Exception as e:  # noqa: BLE001 — показать в окне, а не уронить поток
            self.error = '%s: %s' % (type(e).__name__, e)

    def _progress(self, done, total):
        if self.isInterruptionRequested():         # окно закрывают — бросаем сборку (кэш не пишется)
            raise InterruptedError
        self.progress.emit(done, total)


class Icons:
    """Картинки вооружения из игры по типу иконки (iconType); нет картинки — пунктирный кружок."""

    def __init__(self, source, root=None):
        self.source, self.cache = source, {}
        self.pending = {}
        self.changed = None
        self.cache_dir = os.path.join(root or '', 'cache')
        self.signature = source.signature() if source.kind in ('game', 'datamine') else ''

    def get(self, icon, size):
        key = (icon, size)
        if key not in self.cache:
            pm = QPixmap()
            if icon and self.source.kind in ('game', 'datamine'):
                if icon not in self.pending:
                    self.pending[icon] = workers.pool().submit(
                        workers.atlas, self.source.kind, self.source.root, self.signature,
                        self.cache_dir, 'gameuiskin/%s.png' % icon)
                    QTimer.singleShot(50, lambda: self._poll(icon))
                data = None
            else:
                data = L.atlas_icon(self.source, icon) if icon else None
            if not data or not pm.loadFromData(data):
                pm = QPixmap(size, size)
                pm.fill(Qt.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.Antialiasing)
                p.setPen(QPen(QColor('#3a4250'), 2, Qt.DashLine))
                p.drawEllipse(size * 0.18, size * 0.18, size * 0.64, size * 0.64)
                p.end()
            self.cache[key] = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return self.cache[key]

    def _poll(self, icon):
        future = self.pending.get(icon)
        if future is None:
            return
        if not future.done():
            QTimer.singleShot(50, lambda: self._poll(icon))
            return
        del self.pending[icon]
        try:
            data = future.result()
            if data:
                for key in [key for key in self.cache if key[0] == icon]:
                    pm = QPixmap()
                    if pm.loadFromData(data):
                        size = key[1]
                        self.cache[key] = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            pass
        if self.changed:
            self.changed()


class Clickable(QFrame):
    clicked = Signal(object)

    def __init__(self, name, payload):
        super().__init__()
        self.setObjectName(name)
        self.payload = payload
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty('selected', False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.payload)
        event.accept()


class PylonCard(Clickable):
    def __init__(self, key, number, side, title, mass, pixmap, filled):
        super().__init__('pylon', key)
        self.setFixedHeight(170)
        self.setMinimumWidth(74)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 8, 6, 10)
        lay.setSpacing(4)
        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(_label(str(number), 'dim', False))
        top.addStretch(1)
        lay.addLayout(top)
        icon = QLabel()
        icon.setPixmap(pixmap)
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)
        name = _label(title or 'пусто', None if filled else 'dim')
        name.setAlignment(Qt.AlignCenter)
        if filled:
            name.setStyleSheet('font-weight:600; font-size:10pt;')
        lay.addWidget(name, 1)
        m = _label(_kg(mass), 'dim', False)
        m.setAlignment(Qt.AlignCenter)
        lay.addWidget(m)
        self.title = title
        for w in self.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)


class OptionCard(Clickable):
    def __init__(self, payload, title, sub, pixmap, untested=False):
        super().__init__('option', payload)
        self.setFixedHeight(84)
        self.title = title
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 12, 8)
        lay.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(pixmap)
        icon.setFixedSize(60, 60)
        lay.addWidget(icon)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = _label(title + {'risky': '  ⚠', 'untested': '  📄'}.get(untested, '  📄' if untested is True else ''))
        if untested == 'risky':
            self.setStyleSheet('QFrame#option { border-color: #6b2a2a; }')
        t.setStyleSheet('font-weight:600;')
        m = _label(sub, 'muted')
        for w in (t, m):             # длинное название переносится, а не раздвигает сетку
            w.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addStretch(1)
        col.addWidget(t)
        col.addWidget(m)
        col.addStretch(1)
        lay.addLayout(col, 1)
        if untested == 'risky':
            self.setToolTip('⚠ Наземное/морское оружие: на самолёте игра может упасть при старте миссии '
                            '(так было с 95Я6М на F-15C). Идёт проверка в игре.')
        elif untested:
            self.setToolTip('📄 Так в игре ещё не проверяли: по файлам игры должно работать.')
        for w in self.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)


def _card():
    f = QFrame()
    f.setObjectName('card')
    return f


class LoadoutPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.setObjectName('page')
        self.win = win
        self.icons = Icons(win.source, win.root)
        self._icon_refresh = QTimer(self)
        self._icon_refresh.setSingleShot(True)
        self._icon_refresh.setInterval(120)
        self._icon_refresh.timeout.connect(self.refresh)
        self.icons.changed = lambda: self._icon_refresh.start() if self.isVisible() and self.has else None
        self.vehicle, self.pylons, self.lo, self.catalog = None, None, None, None
        self.loader = None
        self._setup_generation = 0
        self._setup_future = None
        self._preset_titles = None
        self._prepared_points = None
        self._prepared_options = None
        self._prepared_summary = None
        self.touched = False
        self.selected = None
        self.mode = 'stock'                # 'stock' — штатное для пилона, 'any' — любое оружие игры
        self.group_filter = ''
        self.cards, self.options = {}, []
        self.summary = None
        self._busy = False

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 8)
        root.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(12)
        root.addLayout(left, 1)

        head = QHBoxLayout()
        self.name_label = _label('', 'h1', False)
        head.addWidget(self.name_label)
        head.addStretch(1)
        self.template = QComboBox()
        self.template.setMinimumWidth(320)
        self.template.setToolTip('Начать со штатного пресета игры')
        head.addWidget(self.template)
        self.presets_btn = QToolButton()
        self.presets_btn.setText('Мои пресеты  ▾')
        self.presets_btn.setPopupMode(QToolButton.InstantPopup)
        self.presets_menu = QMenu(self)
        self.presets_btn.setMenu(self.presets_menu)
        head.addWidget(self.presets_btn)
        left.addLayout(head)
        self.none_label = _label('', 'muted')
        left.addWidget(self.none_label)

        self.strip_area = QScrollArea()
        self.strip_area.setWidgetResizable(True)
        self.strip_area.setFixedHeight(196)
        self.strip_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.strip = QWidget()
        self.strip_lay = QHBoxLayout(self.strip)
        self.strip_lay.setContentsMargins(0, 0, 0, 0)
        self.strip_lay.setSpacing(8)
        self.strip_area.setWidget(self.strip)
        left.addWidget(self.strip_area)

        self.picker = _card()
        pl = QVBoxLayout(self.picker)
        pl.setContentsMargins(20, 16, 20, 16)
        pl.setSpacing(10)
        row = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        self.pylon_title = _label('', 'title', False)
        self.pylon_sub = _label('', 'muted', False)
        col.addWidget(self.pylon_title)
        col.addWidget(self.pylon_sub)
        row.addLayout(col, 1)
        self.count = QSpinBox()
        self.count.setMinimum(1)
        self.count.setPrefix('точек: ')
        self.count.setToolTip('Сколько точек этого пилона занять выбранным оружием')
        self.count.valueChanged.connect(self._count_changed)
        row.addWidget(self.count)
        self.mirror_btn = QToolButton()
        self.mirror_btn.setText('⇋  Зеркально')
        self.mirror_btn.setPopupMode(QToolButton.InstantPopup)
        self.mirror_menu = QMenu(self)
        self.mirror_btn.setMenu(self.mirror_menu)
        row.addWidget(self.mirror_btn)
        self.clear_btn = QPushButton('Снять')
        row.addWidget(self.clear_btn)
        pl.addLayout(row)

        tabs = QHBoxLayout()
        tabs.setSpacing(24)
        self.tab_stock = QPushButton('Штатное для пилона')
        self.tab_any = QPushButton('Любое оружие игры')
        for b in (self.tab_stock, self.tab_any):
            b.setObjectName('tab')
            b.setCheckable(True)
            tabs.addWidget(b)
        tabs.addStretch(1)
        pl.addLayout(tabs)

        frow = QHBoxLayout()
        self.find = QLineEdit()
        self.find.setPlaceholderText('Оружие или носитель: «фаб 9000», «аим9», «ф15с», «ми28» — можно с ошибками')
        self.find.setClearButtonEnabled(True)
        frow.addWidget(self.find, 1)
        self.all_weapons = QCheckBox('+ оружие танков, кораблей и ЗРК')
        self.all_weapons.setToolTip('Без галочки — только то, что вешается на пилоны (бомбы, ракеты, торпеды, '
                                    'контейнеры, баки).\nС галочкой — всё оружие игры: пушки танков и кораблей, '
                                    'ракеты зенитных комплексов, авиапушки.\n📄 На самолёте такое в игре не проверялось.')
        frow.addWidget(self.all_weapons)
        pl.addLayout(frow)
        chips = QWidget()
        self.chips_row = FlowLayout(chips, 6)      # не влезают в строку — переносятся, а не сжимаются
        pl.addWidget(chips)

        self.loading = QWidget()             # полоска загрузки каталога оружия (фоновая сборка)
        ll = QVBoxLayout(self.loading)
        ll.setContentsMargins(0, 24, 0, 24)
        self.load_label = _label('Собираю список всего оружия игры… Это один раз — потом список берётся из кэша.',
                                 'muted')
        self.load_bar = QProgressBar()
        self.load_bar.setTextVisible(False)
        self.load_bar.setRange(0, 0)
        ll.addWidget(self.load_label)
        ll.addWidget(self.load_bar)
        ll.addStretch(1)
        self.loading.hide()
        pl.addWidget(self.loading, 1)
        self.options_area = QScrollArea()
        self.options_area.setWidgetResizable(True)
        self.options_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.options_box = QWidget()
        self.options_lay = QVBoxLayout(self.options_box)
        self.options_lay.setContentsMargins(0, 0, 4, 0)
        self.options_lay.setSpacing(8)
        self.options_area.setWidget(self.options_box)
        pl.addWidget(self.options_area, 1)
        left.addWidget(self.picker, 1)

        # сводка справа
        self.side = _card()
        self.side.setFixedWidth(330)
        sl = QVBoxLayout(self.side)
        sl.setContentsMargins(20, 18, 20, 18)
        sl.setSpacing(10)
        sl.addWidget(_label('Масса подвески', 'muted', False))
        self.mass_label = _label('', 'big', False)
        sl.addWidget(self.mass_label)
        self.mass_bar = QProgressBar()
        self.mass_bar.setTextVisible(False)
        sl.addWidget(self.mass_bar)
        self.mass_limit = _label('', 'dim', False)
        sl.addWidget(self.mass_limit)
        sl.addSpacing(6)
        self.balance_label = _label('', 'muted', False)
        sl.addWidget(self.balance_label)
        self.balance = QWidget()            # перекос — только если стороны всех занятых пилонов известны
        bal = QHBoxLayout(self.balance)
        bal.setContentsMargins(0, 0, 0, 0)
        bal.setSpacing(4)
        self.bar_left, self.bar_right = QProgressBar(), QProgressBar()
        for b in (self.bar_left, self.bar_right):
            b.setTextVisible(False)
            _restyle(b, level='info')
            bal.addWidget(b)
        self.bar_left.setInvertedAppearance(True)
        sl.addWidget(self.balance)
        self.balance_sides = _label('', 'dim', False)
        sl.addWidget(self.balance_sides)
        sl.addSpacing(6)
        sl.addWidget(_label('Что висит', 'muted', False))
        self.hang_list = QVBoxLayout()
        self.hang_list.setSpacing(4)
        sl.addLayout(self.hang_list)
        sl.addStretch(1)
        wl = QHBoxLayout()
        wcol = QVBoxLayout()
        wcol.setSpacing(0)
        t = _label('Невесомая подвеска', None, False)
        t.setStyleSheet('font-weight:600;')
        wcol.addWidget(t)
        wcol.addWidget(_label('самолёт летит как пустой', 'muted', False))
        wl.addLayout(wcol, 1)
        self.weightless = QCheckBox()
        self.weightless.setObjectName('switch')
        self.weightless.setToolTip(L.WEIGHTLESS_HINT)
        wl.addWidget(self.weightless)
        sl.addLayout(wl)
        self.weightless_info = _label('', 'muted')
        sl.addWidget(self.weightless_info)
        self.alerts = _label('')
        self.alerts.setTextFormat(Qt.RichText)
        sl.addWidget(self.alerts)
        root.addWidget(self.side)

        self.template.activated.connect(self._template_chosen)
        self.weightless.toggled.connect(self._weightless)
        self.clear_btn.clicked.connect(self.clear_pylon)
        self.tab_stock.clicked.connect(lambda: self.set_mode('stock'))
        self.tab_any.clicked.connect(lambda: self.set_mode('any'))
        self.find.textChanged.connect(lambda _t: self.refresh_options())
        self.all_weapons.toggled.connect(lambda _c: self.refresh_options())

    # ---------------------------------------------------------------- состояние

    def set_vehicle(self, v):
        if v is self.vehicle:
            return
        self._setup_generation += 1
        self.vehicle, self.pylons, self.lo, self.selected, self.touched = v, None, None, None, False
        self._preset_titles = None
        self._invalidate_prepared()
        if v is not None and v['kind'] in ('air', 'heli') and len(self.win.vehicles) >= 100:
            self.none_label.setText('Загружаю подвеску…')
            self._setup_future = workers.pool().submit(
                workers.loadout_setup, self.win.source.kind, self.win.source.root, v)
            generation = self._setup_generation
            QTimer.singleShot(30, lambda: self._poll_setup(generation))
            return
        self._setup_future = None
        unit = None
        if v is not None and v['kind'] in ('air', 'heli'):
            unit = self.win.source.load(v['file'])
            self.pylons = L.read_pylons(unit) if unit is not None else None
        if self.pylons is not None and self.pylons.scheme:
            self.lo = self._default_loadout(unit, v)
            pts = self.points()
            self.selected = next((p[0] for p in pts if p[3]), pts[0][0] if pts else None)
        self._fill_template()
        self._fill_presets()
        self.mode, self.group_filter = 'stock', ''
        self.refresh()

    def _poll_setup(self, generation):
        if generation != self._setup_generation or self._setup_future is None:
            return
        if not self._setup_future.done():
            QTimer.singleShot(30, lambda: self._poll_setup(generation))
            return
        try:
            (self.pylons, self.lo, self._preset_titles, self.selected,
             self._prepared_points, self._prepared_options,
             self._prepared_summary) = self._setup_future.result()
        except Exception as exc:
            self._setup_future = None
            self.none_label.setText('Не удалось загрузить подвеску: %s' % exc)
            return
        self._setup_future = None
        self._fill_template()
        self._fill_presets()
        self.mode, self.group_filter = 'stock', ''
        self.refresh()

    def _default_loadout(self, unit, v):
        name = BL.default_preset(unit, v['name'], v['kind'])
        try:
            return L.from_preset(self.win.source, self.pylons, name) if name else L.Loadout()
        except ValueError:
            return L.Loadout(name if self.pylons.scheme == 'legacy' else '')

    def start_catalog(self):
        """Собрать каталог оружия в фоне (первый раз — до минуты, потом из кэша): окно не зависает."""
        if self.catalog is not None or self.loader is not None:
            return
        self.loader = CatalogLoader(self.win.source, os.path.join(self.win.root, 'cache'))
        self.loader.progress.connect(self._catalog_progress)
        self.loader.finished.connect(self._catalog_done)
        self.loader.start()

    def stop_catalog(self):
        if self.loader is not None and self.loader.isRunning():
            self.loader.requestInterruption()
            self.loader.wait(10000)

    def _catalog_progress(self, done, total):
        self.load_bar.setRange(0, total)
        self.load_bar.setValue(done)
        self.load_label.setText('Собираю список всего оружия игры: %d из %d файлов. Это один раз — потом '
                                'список берётся из кэша.' % (done, total))

    def _catalog_done(self):
        loader = self.loader
        if loader is None or loader.catalog is None and not loader.error:
            return
        self.catalog = loader.catalog
        if loader.error:
            self.load_label.setText('Не удалось собрать список оружия: %s' % loader.error)
            return
        self.loading.hide()
        if self.has:
            self.refresh()

    def ensure_catalog(self):
        """Каталог сейчас (ждёт фоновую сборку — нужен для записи/тестов)."""
        if self.catalog is None:
            self.start_catalog()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.loader.wait()
            finally:
                QApplication.restoreOverrideCursor()
            self.catalog = self.loader.catalog or []
        return self.catalog

    def loadout(self):
        """Подвеска для сборки или None — пользователь её не трогал (штатный пресет по умолчанию)."""
        return self.lo if self.touched and self.lo is not None else None

    def _changed(self):
        self._invalidate_prepared()
        self.touched = True
        self.refresh()
        if hasattr(self.win, 'stats_page'):
            self.win.stats_page.refresh_loadout()

    def reset(self):
        if self.vehicle is not None:
            v = self.vehicle
            self.vehicle = None
            self.set_vehicle(v)

    def _invalidate_prepared(self):
        self._prepared_points = self._prepared_options = self._prepared_summary = None

    @property
    def has(self):
        return self.pylons is not None and bool(self.pylons.scheme)

    # ---------------------------------------------------------------- данные для показа

    def points(self):
        """[(ключ, номер, подпись, есть ли что-то, сторона, иконка, масса)] карточек пилонов."""
        if self._prepared_points is not None:
            return self._prepared_points
        out, src = [], self.win.source
        if not self.has:
            return out
        if self.pylons.scheme == 'slots':
            for s in self.pylons.pylon_slots:
                choice = self.lo.slots.get(s.index)
                items = L.slot_weapons(self.pylons, s.index, choice)
                out.append((s.index, s.index, L.items_caption(src, items), bool(items), s.side,
                            self._choice_icon(s, choice), self._mass(items)))
        else:
            weapons = L.legacy_weapons(src, self.pylons, self.lo.base) if self.lo.base else []
            for i, w in enumerate(weapons or [], 1):
                path = self.lo.legacy.get(i) or w.get('blk')
                if path:
                    out.append((i, i, L.items_caption(src, [(path, w)]), True, None, self._weapon_icon(path),
                                self._mass([(path, w)])))
        return out

    def _mass(self, items):
        by_path = {L.weapon_key(w['path']): w for w in (self.catalog or [])}
        return sum(L._item_mass(self.win.source, p, w, by_path.get(L.weapon_key(p))) for p, w in items)

    def _choice_icon(self, s, choice):
        if not choice:
            return ''
        if 'variant' in choice:
            v = s.variant(choice['variant'])
            return v.icon if v else ''
        return self._weapon_icon(choice['weapon'])

    def _weapon_icon(self, path):
        """Иконка оружия: как у стоковой авиации (каталог) или по классу."""
        entry = next((w for w in (self.catalog or []) if L.weapon_key(w['path']) == L.weapon_key(path)), None)
        if entry is not None:
            return entry['icon'] or GROUP_ICONS.get(entry['group'], '')
        for s in (self.pylons.slots if self.pylons else []):
            for v in s.variants:
                if any(L.weapon_key(w.get('blk')) == L.weapon_key(path) for w in v.weapons) and v.icon:
                    return v.icon
        kind = L.weapon_kind(self.win.source, path)
        return GROUP_ICONS.get(L.weapon_group('', '', kind), '')

    # ---------------------------------------------------------------- показ

    def _fill_template(self):
        self.template.clear()
        self.template.addItem('Штатная подвеска по умолчанию', None)
        if self.pylons is not None and self.pylons.scheme:
            for name, title in (self._preset_titles if self._preset_titles is not None else
                                L.preset_titles(self.win.source, self.pylons)):
                self.template.addItem(title, name)
                self.template.setItemData(self.template.count() - 1, 'Пресет игры: ' + name, Qt.ToolTipRole)
        if self.pylons is not None and self.pylons.scheme == 'slots':
            self.template.addItem('Снять всё', '')

    def _fill_presets(self):
        m = self.presets_menu
        m.clear()
        m.addAction('Сохранить как…', self._save_dialog)
        names = L.library_names(self.win.root, self.vehicle['name']) if self.vehicle else []
        if names:
            m.addSeparator()
            for n in names:
                m.addAction(n, lambda n=n: self.load_saved(n))
            m.addSeparator()
            dm = m.addMenu('Удалить')
            for n in names:
                dm.addAction(n, lambda n=n: self.delete_saved(n))

    def refresh(self):
        has = self.has
        for w in (self.template, self.presets_btn, self.strip_area, self.picker, self.side):
            w.setVisible(has)
        if self.vehicle is None:
            self.name_label.setText('Подвеска')
            self.none_label.setText('Сначала выберите машину.')
        else:
            self.name_label.setText(self._title())
            self.none_label.setText('' if has else 'У этой техники подвески нет — переходите к сценарию.')
        if not has:
            return
        self._busy = True
        self.weightless.setChecked(self.lo.weightless)
        self._busy = False
        self._draw_strip()
        self._pylon_header()
        self.refresh_options()
        self._totals()

    def _title(self):
        v = self.vehicle
        return v['ru'] or v['en'] or v['name']

    def _draw_strip(self):
        _clear(self.strip_lay)
        self.cards = {}
        for key, number, caption, filled, side, icon, mass in self.points():
            card = PylonCard(key, number, side, caption, mass, self.icons.get(icon, 64) if filled else
                             self.icons.get('', 64), filled)
            _restyle(card, selected=key == self.selected)
            card.clicked.connect(self.select_pylon)
            self.strip_lay.addWidget(card, 1)
            self.cards[key] = card

    def _pylon_header(self):
        key = self.selected
        slots = self.pylons.scheme == 'slots'
        self.tab_stock.setText('Штатное для пилона' if slots else 'Штатное этой машины')
        self.tab_stock.setChecked(self.mode == 'stock')
        self.tab_any.setChecked(self.mode == 'any')
        self.mirror_menu.clear()
        self.count.hide()
        if key is None:
            self.pylon_title.setText('Выберите пилон')
            self.pylon_sub.setText('Щёлкните по карточке пилона сверху.')
            return
        pt = next((p for p in self.points() if p[0] == key), None)
        if slots:
            s = self.pylons.slot(key)
            self.pylon_title.setText('Пилон %d' % key)
            choice = self.lo.slots.get(key)
            if choice and 'weapon' in choice:
                sample = s.variant(choice.get('sample')) or s.variants[0]
                if len(sample.weapons) > 1:
                    self._busy = True
                    self.count.setMaximum(len(sample.weapons))
                    self.count.setValue(choice.get('count') or len(sample.weapons))
                    self._busy = False
                    self.count.show()
            pairs = L.mirror_pairs(self.pylons)
            others = sorted((t.index for t in self.pylons.pylon_slots if t.index != key),
                            key=lambda i: (i != pairs.get(key), i))
            for i in others:
                self.mirror_menu.addAction('На пилон %d%s' % (i, '  (парный)' if pairs.get(key) == i else ''),
                                           lambda i=i: self.mirror_to(i))
        else:
            self.pylon_title.setText('Точка %d' % key)
        self.pylon_sub.setText('Сейчас: %s%s' % (pt[2] or 'пусто', ', ' + _kg(pt[6]) if pt and pt[6] else '')
                               if pt else 'Сейчас: пусто')
        self.mirror_btn.setVisible(slots)
        self.clear_btn.setVisible(slots)

    def set_mode(self, mode):
        self._prepared_options = None
        self.mode = mode
        self.group_filter = ''
        if mode == 'any':
            self.start_catalog()
        self._pylon_header()
        self.refresh_options()

    def _option_items(self):
        """[(группа, payload, название, подпись, иконка, 📄, выбрано)] для выбранного пилона и режима."""
        if self._prepared_options is not None and not self.find.text().strip():
            return self._prepared_options
        key, src = self.selected, self.win.source
        if key is None:
            return []
        text = self.find.text().strip().lower()
        out = []
        if self.mode == 'stock':
            if self.pylons.scheme == 'slots':
                s = self.pylons.slot(key)
                cur = (self.lo.slots.get(key) or {}).get('variant')
                for v in s.variants:
                    cap = L.variant_caption(src, v)
                    if text and not _matches(text, cap, v.name):
                        continue
                    g = L.variant_group(v)
                    out.append((g, ('variant', v.name), cap or v.name, _kg(L.variant_mass(src, v)) or '—', v.icon,
                                False, cur == v.name))
            else:
                weapons = L.legacy_weapons(src, self.pylons, self.lo.base) or []
                stock = weapons[key - 1].get('blk') if 0 < key <= len(weapons) else None
                cur = self.lo.legacy.get(key) or stock
                seen = []
                for _n, path in self.pylons.presets:      # всё, что встречается в штатных пресетах машины
                    for w in (L.legacy_weapons(src, self.pylons, _n) or []):
                        b = w.get('blk')
                        if b and L.weapon_key(b) not in [L.weapon_key(x) for x in seen]:
                            seen.append(b)
                for b in seen:
                    info = L.weapon_info(src, b)
                    if text and not _matches(text, info['title'], b):
                        continue
                    g = L.weapon_group('', '', info['kind'])
                    out.append((g, ('weapon', b), info['title'], _kg(L.weapon_mass(src, b)) or '—',
                                self._weapon_icon(b), False, L.weapon_key(cur or '') == L.weapon_key(b)))
        else:
            cur = None
            if self.pylons.scheme == 'slots':
                cur = (self.lo.slots.get(key) or {}).get('weapon')
            else:
                cur = self.lo.legacy.get(key)
            if self.catalog is None:             # ещё собирается в фоне — показываем полоску загрузки
                return []
            found, carriers = L.search_weapons(self.catalog, self.win.vehicles, self.find.text(), not
                                               self.all_weapons.isChecked())
            self._carriers = carriers
            self._groups = {w['group'] for w in found}
            if self.group_filter not in self._groups:  # класса нет среди найденного (новый запрос) — показать все
                self.group_filter = ''
            if self.group_filter:
                found = [w for w in found if w['group'] == self.group_filter]
            labels = [w['ru'] or w['en'] or w['stem'] for w in found[:ANY_LIMIT]]
            for w, label in zip(found[:ANY_LIMIT], labels):
                sub = _kg(w['mass']) or '—'
                if labels.count(label) > 1:           # одинаковые названия — разные файлы: покажем имя файла
                    sub += ' · ' + w['stem']
                out.append((w['group'], ('weapon', w['path']), label, sub,
                            w['icon'] or GROUP_ICONS.get(w['group'], ''),
                            'risky' if L.is_risky(w) else 'untested' if not w['air'] else '',
                            L.weapon_key(cur or '') == L.weapon_key(w['path'])))
            self._more = max(0, len(found) - ANY_LIMIT)
        return out

    def refresh_options(self):
        if not self.has:
            return
        self._more, self._groups, self._carriers = 0, set(), []
        waiting = self.mode == 'any' and self.catalog is None
        self.loading.setVisible(waiting)
        self.options_area.setVisible(not waiting)
        items = self._option_items()
        groups = [g for g, _n in L.GROUPS if any(i[0] == g for i in items)]
        if self.mode == 'stock' and self.group_filter not in groups:
            self.group_filter = ''
        # фильтр по классу (чипы): в «штатном» фильтруем показанное, в «любом» — каталог
        _clear(self.chips_row)
        chip_groups = groups if self.mode == 'stock' else [g for g, _n in L.GROUPS if g in self._groups]
        for g in [''] + chip_groups:
            b = QPushButton('Все' if not g else GROUP_SHORT[g])
            b.setToolTip(L.GROUP_NAMES[g] if g else 'Все классы')
            b.setObjectName('chip')
            b.setCheckable(True)
            b.setChecked(self.group_filter == g)
            b.clicked.connect(lambda _c=False, g=g: self._set_group(g))
            self.chips_row.addWidget(b)
        self.all_weapons.setVisible(self.mode == 'any')
        if self.mode == 'stock' and self.group_filter:
            items = [i for i in items if i[0] == self.group_filter]
        _clear(self.options_lay)
        self.options = []
        if self.mode == 'any' and self._carriers:
            names = ', '.join(c['ru'] or c['en'] or c['name'] for c in self._carriers)
            self.options_lay.addWidget(_label('Всё вооружение: %s' % names, 'muted'))
        if not items:
            self.options_lay.addWidget(_label('Ничего не найдено.' if self.selected is not None else '', 'muted'))
        cols = self._columns()
        self._cols = cols
        box = QWidget()
        grid = QGridLayout(box)            # одна сетка на все группы: одинаковые колонки
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        row = 0
        for g in [g for g, _n in L.GROUPS]:
            part = [i for i in items if i[0] == g]
            if not part:
                continue
            head = _label(L.GROUP_NAMES[g].upper(), 'group', False)
            head.setContentsMargins(0, 8 if row else 0, 0, 0)
            grid.addWidget(head, row, 0, 1, cols)
            row += 1
            for n, (_g, payload, title, sub, icon, untested, sel) in enumerate(part):
                card = OptionCard(payload, title, sub, self.icons.get(icon, 60), untested)
                if payload[0] == 'weapon':
                    card.setToolTip((card.toolTip() + '\n' if card.toolTip() else '') + payload[1])
                _restyle(card, selected=sel)
                card.clicked.connect(self.choose)
                grid.addWidget(card, row + n // cols, n % cols)
                self.options.append(card)
            row += (len(part) + cols - 1) // cols
        for c in range(cols):
            grid.setColumnStretch(c, 1)
        self.options_lay.addWidget(box)
        if self._more:
            self.options_lay.addWidget(_label('… и ещё %d — уточните поиск.' % self._more, 'muted'))
        self.options_lay.addStretch(1)
        self.options_lay.activate()
        self.options_box.adjustSize()

    def _columns(self):
        return max(2, min(COLUMNS, self.options_area.viewport().width() // OPTION_W))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.has and getattr(self, '_cols', None) not in (None, self._columns()):
            self.refresh_options()

    def _set_group(self, g):
        self.group_filter = g
        self.refresh_options()

    def _totals(self):
        sm = self._prepared_summary if self._prepared_summary is not None else L.summarize(
            self.win.source, self.pylons, self.lo, self.catalog)
        self.summary = sm
        lim = self.pylons.limits.get('maxloadMass')
        self.mass_label.setText(_kg(sm.total) or '0 кг')
        ratio = sm.total / lim if lim else 0
        self.mass_bar.setRange(0, 1000)
        self.mass_bar.setValue(int(min(1.0, ratio) * 1000))
        _restyle(self.mass_bar, level='bad' if ratio > 1 else 'warn' if ratio > 0.9 else '')
        self.mass_limit.setText('допустимо %s' % _kg(lim) if lim else 'предел массы в файлах не указан')
        dis = self.pylons.limits.get('maxDisbalance')
        diff = abs(sm.left - sm.right)
        self.balance_label.setText('Перекос: %s%s' % (_kg(diff) or '0 кг', ' · допустимо %s' % _kg(dis) if dis else ''))
        top = max(sm.left, sm.right, 1.0)
        for bar, kg in ((self.bar_left, sm.left), (self.bar_right, sm.right)):
            bar.setRange(0, 1000)
            bar.setValue(int(kg / top * 1000))
            _restyle(bar, level='bad' if dis and diff > dis else 'info')
        self.balance_sides.setText('слева %s  ·  справа %s' % (_kg(sm.left) or '0', _kg(sm.right) or '0'))
        # стороны пилонов игра в файлах не задаёт, программа узнаёт их только по именам вариантов
        known = self.pylons.scheme == 'slots' and not sm.unknown_side
        for w in (self.balance_label, self.balance, self.balance_sides):
            w.setVisible(known)
        _clear(self.hang_list)
        for title, n in (sm.counts or {'ничего': 0}).items():
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            rl.addWidget(_label(title, None if n else 'muted', False), 1)
            if n:
                rl.addWidget(_label('×%d' % n, 'muted', False))
            self.hang_list.addWidget(row)
        self.weightless_info.setText('Пустая масса %s → %s' % (_kg(sm.empty_mass), _kg(sm.weightless_mass))
                                     if sm.weightless_mass is not None else '')
        self.weightless_info.setVisible(sm.weightless_mass is not None)
        # только то, что мешает или заметно в полёте: отказ и перегруз/перекос (сведения ангара — не здесь)
        alerts = [(lvl, t) for lvl, t in sm.warnings if lvl in ('refuse', 'danger', 'warn')
                  and (known or not t.startswith(('Перекос', 'На левой', 'На правой')))]
        self.alerts.setText('<br>'.join('<span style="color:%s">%s</span>' % (
            '#ef5d5d' if lvl in ('refuse', 'danger') else '#e8b64a', ('⚠ ' if lvl == 'danger' else '') +
            _short_warning(t)) for lvl, t in alerts))
        self.alerts.setVisible(bool(alerts))

    def summary_text(self):
        """Сводка простым текстом (для тестов)."""
        parts = [self.mass_label.text(), self.mass_limit.text(), self.balance_label.text(),
                 self.weightless_info.text(), self.alerts.text()]
        for i in range(self.hang_list.count()):
            w = self.hang_list.itemAt(i).widget()
            parts += [x.text() for x in w.findChildren(QLabel)] if w else []
        return '\n'.join(parts)

    # ---------------------------------------------------------------- действия

    def select_pylon(self, key):
        self._prepared_options = None
        self.selected = key
        for k, card in self.cards.items():
            _restyle(card, selected=k == key)
        self._pylon_header()
        self.refresh_options()

    def _template_chosen(self, index):
        name = self.template.itemData(index)
        if name is None:
            self.reset()
            return
        self.apply_template(name)

    def apply_template(self, name):
        if self.lo is None:
            return False
        weightless = self.lo.weightless
        try:
            self.lo = L.from_preset(self.win.source, self.pylons, name) if name else L.Loadout()
        except ValueError as e:
            self.none_label.setText(str(e))
            return False
        self.lo.weightless = weightless
        self._invalidate_prepared()
        pts = self.points()
        if self.selected not in [p[0] for p in pts]:
            self.selected = pts[0][0] if pts else None
        self._changed()
        return True

    def choose(self, payload):
        """Повесить выбранное на пилон: ('variant', имя) — штатный вариант; ('weapon', путь) — оружие."""
        key = self.selected
        if key is None:
            return False
        what, value = payload
        if self.pylons.scheme == 'slots':
            if what == 'variant':
                self.lo.slots[key] = {'variant': value}
            else:
                s = self.pylons.slot(key)
                old = self.lo.slots.get(key) or {}
                sample = s.variant(old.get('sample') or old.get('variant')) or s.variants[0]
                self.lo.slots[key] = {'weapon': value, 'sample': sample.name}
        else:
            weapons = L.legacy_weapons(self.win.source, self.pylons, self.lo.base) or []
            stock = weapons[key - 1].get('blk') if 0 < key <= len(weapons) else None
            if stock and L.weapon_key(stock) == L.weapon_key(value):
                self.lo.legacy.pop(key, None)
            else:
                self.lo.legacy[key] = value
        self._changed()
        return True

    def _count_changed(self, value):
        if self._busy or self.selected is None or self.pylons.scheme != 'slots':
            return
        choice = self.lo.slots.get(self.selected)
        if choice and 'weapon' in choice:
            s = self.pylons.slot(self.selected)
            sample = s.variant(choice.get('sample')) or s.variants[0]
            if value >= len(sample.weapons):
                choice.pop('count', None)
            else:
                choice['count'] = value
            self._changed()

    def clear_pylon(self):
        if self.selected is not None and self.pylons.scheme == 'slots':
            self.lo.slots.pop(self.selected, None)
            self._changed()

    def mirror_to(self, dst):
        if self.selected is None or self.pylons.scheme != 'slots':
            return False
        L.mirror(self.lo, self.pylons, self.selected, dst)
        self._changed()
        return True

    def _weightless(self, checked):
        if self._busy or self.lo is None:
            return
        self.lo.weightless = checked
        self._changed()

    def _save_dialog(self):
        name, ok = QInputDialog.getText(self, 'Сохранить пресет', 'Имя пресета:', text=self.lo.name if self.lo else '')
        if ok:
            self.save_as(name)

    def save_as(self, name):
        name = (name or '').strip()
        if not name or self.lo is None:
            return False
        self.lo.name = name
        L.library_save(self.win.root, self.vehicle['name'], self.lo)
        self._fill_presets()
        return True

    def load_saved(self, name):
        lo = L.library_get(self.win.root, self.vehicle['name'], name) if self.vehicle else None
        if lo is None:
            return False
        self.lo = lo
        self._invalidate_prepared()
        pts = self.points()
        if self.selected not in [p[0] for p in pts]:
            self.selected = pts[0][0] if pts else None
        self._changed()
        return True

    def delete_saved(self, name):
        if self.vehicle and self.win.confirm('Удалить', 'Удалить «%s» из моих пресетов?' % name):
            L.library_delete(self.win.root, self.vehicle['name'], name)
            self._fill_presets()
            return True
        return False


def _matches(text, *names):
    """Запрос в названии без учёта раскладки, дефисов и пробелов: «аим 9» найдёт «AIM-9M»."""
    from ..game import search as S
    keys = [f for n in names for f in S.forms(n)]
    return any(q in k for q in S.forms(text) for k in keys)


def _short_warning(text):
    """Предупреждение сводки — первой фразой, без ссылок на круги проверки."""
    first = text.split('. ')[0].rstrip('.')
    return first + '.'
