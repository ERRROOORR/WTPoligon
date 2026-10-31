"""Шаг «Техника»: поиск с опечатками в любой раскладке (game/search.py), строки с картинкой машины из игры
(atlases.vromfs.bin units/<имя>.png), при наведении — карточка машины с крупной картинкой. Отметка «в ангаре»."""
import html
import os

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListView,
                               QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

from .. import hangar as H
from ..game import index as X
from . import texts as TX
from . import workers

ROW_H = 64
KIND_TITLES = {'tank': 'Наземная техника', 'air': 'Самолёты', 'heli': 'Вертолёты', 'ship': 'Флот'}


def _label(text='', name=None, wrap=True):
    w = QLabel(text)
    w.setWordWrap(wrap)
    if name:
        w.setObjectName(name)
    return w


def unit_info(v, with_name=False):
    """«самолёт · США · ранг VII · БР 12.0 · премиум» (+ внутреннее имя, если название не уникально)."""
    parts = [X.KIND_NAMES[v['kind']], TX.country_name(v['country'])]
    if v['rank']:
        parts.append('ранг ' + TX.rank_name(v['rank']))
    if v['br']:
        parts.append('БР %.1f' % v['br'])
    parts += v.get('marks') or []
    if with_name:
        parts.append(v['name'])
    return ' · '.join(parts)


def title(v):
    return v['ru'] or v['en'] or v['name']


class UnitImages:
    """Картинки техники из игры (как в дереве исследований): units/<имя>.png; нет — пусто."""

    def __init__(self, source, root=None):
        self.source, self.cache = source, {}
        self.pending = {}
        self.cache_dir = os.path.join(root or '', 'cache')
        self.signature = source.signature() if source.kind in ('game', 'datamine') else ''
        self.changed = None

    def get(self, name):
        """Картинка машины; нет своей (версии «_event», «_race» …) — основной машины без хвоста имени."""
        if name not in self.cache:
            pm = QPixmap()
            if self.source.kind in ('game', 'datamine'):
                self.pending[name] = workers.pool().submit(
                    workers.unit_image, self.source.kind, self.source.root,
                    self.signature, self.cache_dir, name)
                QTimer.singleShot(50, lambda: self._poll(name))
            else:
                try:
                    data = self.source.atlas_file('units/%s.png' % name)
                    if data:
                        pm.loadFromData(data)
                except NotImplementedError:
                    pass
            self.cache[name] = pm
        return self.cache[name]

    def _poll(self, name):
        future = self.pending.get(name)
        if future is None:
            return
        if not future.done():
            QTimer.singleShot(50, lambda: self._poll(name))
            return
        del self.pending[name]
        try:
            data = future.result()
            if data:
                self.cache[name].loadFromData(data)
        except Exception:
            pass
        if self.changed:
            self.changed(name)


class VehicleModel(QAbstractListModel):
    def __init__(self, marks, images):
        super().__init__()
        self.rows, self.marks, self.images = [], marks, images

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def is_duplicate(self, v):
        """Одинаковое название у нескольких машин (подарочная/событийная версии, другая нация) — покажем имя."""
        if not hasattr(self, '_dups'):
            from collections import Counter
            counts = Counter(title(x) for x in self.all_rows)
            self._dups = {t for t, n in counts.items() if n > 1}
        return title(v) in self._dups

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.DisplayRole):
        v = self.rows[index.row()]
        if role == Qt.DisplayRole:
            return title(v)
        if role == Qt.UserRole:
            return v
        return None


class VehicleDelegate(QStyledItemDelegate):
    """Строка: картинка машины, название, «вид · страна · ранг · БР», отметка «в ангаре»."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def sizeHint(self, option, index):
        return QSize(200, ROW_H)

    def paint(self, p, option, index):
        v = index.data(Qt.UserRole)
        r = option.rect.adjusted(4, 2, -10, -2)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        selected = option.state & QStyle.State_Selected
        hover = option.state & QStyle.State_MouseOver
        if selected or hover:
            p.setPen(QColor('#f2913d') if selected else Qt.NoPen)
            p.setBrush(QColor('#1f1812') if selected else QColor('#1b1f27'))
            p.drawRoundedRect(r, 10, 10)
        pm = self.model.images.get(v['name'])
        img = QRect(r.left() + 10, r.top() + (r.height() - 44) // 2, 64, 44)
        if not pm.isNull():
            s = pm.scaled(img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(img.left() + (img.width() - s.width()) // 2, img.top() + (img.height() - s.height()) // 2, s)
        x = img.right() + 16
        f = QFont(option.font)
        f.setPointSizeF(11.5)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor('#e9ecf1'))
        p.drawText(QRect(x, r.top() + 10, r.width() - x - 120, 22), Qt.AlignLeft | Qt.AlignVCenter, title(v))
        f.setPointSizeF(9.5)
        f.setWeight(QFont.Normal)
        p.setFont(f)
        p.setPen(QColor('#8a93a3'))
        p.drawText(QRect(x, r.top() + 33, r.width() - x - 120, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   unit_info(v, self.model.is_duplicate(v)))
        if H.status(self.model.marks, v['name']):
            badge = QRect(r.right() - 96, r.top() + (r.height() - 24) // 2, 86, 24)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor('#173326'))
            p.drawRoundedRect(badge, 12, 12)
            p.setPen(QColor('#4cc38a'))
            p.drawText(badge, Qt.AlignCenter, 'в ангаре')
        p.restore()


class HoverCard(QFrame):
    """Карточка машины при наведении: крупная картинка, название, данные."""

    def __init__(self, images):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.images = images
        self.setObjectName('card')
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(300)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        self.pic = QLabel()
        self.pic.setAlignment(Qt.AlignCenter)
        self.pic.setFixedHeight(150)
        self.pic.setStyleSheet('background:#1b1f27; border-radius:10px;')
        lay.addWidget(self.pic)
        self.name = _label('', 'title')
        lay.addWidget(self.name)
        self.info = _label('', 'muted')
        lay.addWidget(self.info)
        self.extra = _label('', 'dim')
        lay.addWidget(self.extra)
        self.vehicle = None

    def show_for(self, v, marks, pos):
        if v is not self.vehicle:
            self.vehicle = v
            pm = self.images.get(v['name'])
            self.pic.setPixmap(pm.scaled(240, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                               if not pm.isNull() else QPixmap())
            self.pic.setText('' if not pm.isNull() else 'нет картинки')
            self.name.setText(html.escape(title(v)))
            self.info.setText(unit_info(v))
            own = H.status(marks, v['name'])
            self.extra.setText('Внутреннее имя: %s<br>%s' % (html.escape(v['name']).replace('_', '_\u200b'), {
                True: 'Отмечена: есть в ангаре', False: 'Отмечена: нет в ангаре',
                None: 'Наличие в ангаре не отмечено'}[own]))
            self.adjustSize()
        self.move(pos)
        self.show()


class VehiclePage(QWidget):
    LIMIT = 5000

    def __init__(self, win):
        super().__init__()
        self.setObjectName('page')
        self.win = win
        self.vehicles = win.vehicles
        self.selected = None
        self.images = UnitImages(win.source, win.root)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 8)
        lay.setSpacing(12)
        lay.addWidget(_label('Выберите машину', 'h1'))

        row = QHBoxLayout()
        self.find = QLineEdit()
        self.find.setPlaceholderText('Поиск: т80бвм, f15c, ф15с, абрамс — можно с опечатками и в любой раскладке')
        self.find.setClearButtonEnabled(True)
        self.find.setMinimumHeight(46)
        self.find.setStyleSheet('font-size:12pt;')
        row.addWidget(self.find, 1)
        lay.addLayout(row)

        frow = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItem('Вся техника', '')
        for k in X.KIND_NAMES:
            self.kind.addItem(KIND_TITLES[k], k)
        self.country = QComboBox()
        self.country.addItem('Все страны', '')
        for c in sorted({v['country'] for v in self.vehicles if v['country']}, key=TX.country_name):
            self.country.addItem(TX.country_name(c), c)
        self.rank = QComboBox()
        self.rank.addItem('Все ранги', 0)
        for r in sorted({v['rank'] for v in self.vehicles if isinstance(v['rank'], int)}):
            self.rank.addItem('Ранг ' + TX.rank_name(r), r)
        self.only_hangar = QCheckBox('Только из моего ангара')
        for w in (self.kind, self.country, self.rank):
            w.setMinimumWidth(180)
            frow.addWidget(w)
        frow.addWidget(self.only_hangar)
        frow.addStretch(1)
        self.count = _label('', 'muted', False)
        frow.addWidget(self.count)
        lay.addLayout(frow)

        body = QHBoxLayout()
        body.setSpacing(18)
        self.model = VehicleModel(win.marks, self.images)
        self.model.all_rows = self.vehicles
        self.table = QListView()
        self.table.setModel(self.model)
        self.table.setItemDelegate(VehicleDelegate(self.model))
        self.table.setUniformItemSizes(True)
        self.table.setMouseTracking(True)
        self.table.setStyleSheet('QListView { padding: 6px; } QListView::item { border: none; }')
        self.table.viewport().installEventFilter(self)
        body.addWidget(self.table, 1)

        side = QFrame()
        side.setObjectName('card')
        side.setFixedWidth(340)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(18, 16, 18, 16)
        sl.setSpacing(8)
        sl.addWidget(_label('Выбранная машина', 'muted', False))
        self.pic = QLabel()
        self.pic.setAlignment(Qt.AlignCenter)
        self.pic.setFixedHeight(150)
        self.pic.setStyleSheet('background:#1b1f27; border-radius:10px; color:#5c6473;')
        sl.addWidget(self.pic)
        self.info = _label('Пока ничего не выбрано.')
        self.info.setTextFormat(Qt.RichText)
        sl.addWidget(self.info)
        sl.addSpacing(6)
        self.hangar = QCheckBox('Есть в моём ангаре')
        self.hangar.setEnabled(False)
        sl.addWidget(self.hangar)
        sl.addWidget(_label(TX.HANGAR_HINT, 'dim'))
        sl.addStretch(1)
        body.addWidget(side)
        lay.addLayout(body, 1)

        self.card = HoverCard(self.images)
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(350)
        self._hover_timer.timeout.connect(self._show_card)
        self._hover = None

        self.find.textChanged.connect(self.refresh)
        for combo in (self.kind, self.country, self.rank):
            combo.currentIndexChanged.connect(self.refresh)
        self.only_hangar.toggled.connect(self.refresh)
        self.table.selectionModel().selectionChanged.connect(self._selected)
        self.table.doubleClicked.connect(lambda _i: self.win.go(self.win.neighbour(1)))
        self.hangar.clicked.connect(self._hangar_clicked)
        self.images.changed = self._image_ready
        self.refresh()

    def _image_ready(self, name):
        self.table.viewport().update()
        if self.selected is not None and self.selected['name'] == name:
            pm = self.images.cache[name]
            self.pic.setPixmap(pm.scaled(260, 140, Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation) if not pm.isNull() else QPixmap())

    # ---------------------------------------------------------------- карточка при наведении

    def eventFilter(self, obj, event):
        t = event.type()
        if t == event.Type.MouseMove:
            idx = self.table.indexAt(event.position().toPoint())
            v = idx.data(Qt.UserRole) if idx.isValid() else None
            if v is not self._hover:
                self._hover = v
                self.card.hide()
                if v is not None:
                    self._hover_timer.start()
            self._hover_pos = event.globalPosition().toPoint()
        elif t in (event.Type.Leave, event.Type.Wheel, event.Type.MouseButtonPress):
            self._hover = None
            self._hover_timer.stop()
            self.card.hide()
        return False

    def _show_card(self):
        if self._hover is not None:
            self.card.show_for(self._hover, self.win.marks, self._hover_pos + QPoint(24, 16))

    def hideEvent(self, event):
        try:
            self.card.hide()
        except RuntimeError:          # окно уже закрывается
            pass
        super().hideEvent(event)

    # ---------------------------------------------------------------- список

    def refresh(self):
        text = self.find.text().strip()
        found = X.search(self.vehicles, text, self.kind.currentData() or None, self.country.currentData() or None)
        if self.rank.currentData():
            found = [v for v in found if v['rank'] == self.rank.currentData()]
        if self.only_hangar.isChecked():
            found = [v for v in found if H.status(self.win.marks, v['name'])]
        if not X.norm_text(text):        # без поиска — по алфавиту; с поиском — по совпадению
            found.sort(key=lambda v: title(v).lower())
        self.model.set_rows(found[:self.LIMIT])
        self.count.setText('Найдено: %d из %d' % (len(found), len(self.vehicles)))
        if self.selected in self.model.rows:
            self.table.setCurrentIndex(self.model.index(self.model.rows.index(self.selected)))

    def select(self, name):
        """Выбрать машину по внутреннему имени (сбрасывает фильтры, если она скрыта)."""
        v = X.find(self.vehicles, name)
        if v is None:
            return False
        if v not in self.model.rows:
            self.find.clear()
            for combo in (self.kind, self.country, self.rank):
                combo.setCurrentIndex(0)
            self.only_hangar.setChecked(False)
        self.table.setCurrentIndex(self.model.index(self.model.rows.index(v)))
        return True

    def _selected(self, *_):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        v = self.model.rows[idx.row()]
        if v is self.selected:
            return
        self.selected = v
        self.hangar.setEnabled(True)
        pm = self.images.get(v['name'])
        self.pic.setPixmap(pm.scaled(260, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pm.isNull()
                           else QPixmap())
        self.pic.setText('' if not pm.isNull() else 'нет картинки')
        self.info.setText('<span style="font-size:15pt; font-weight:700">%s</span><br><span style="color:#8a93a3">'
                          '%s</span>' % (html.escape(title(v)), unit_info(v)))
        self.hangar.setChecked(bool(H.status(self.win.marks, v['name'])))
        self.win.vehicle_changed(v)

    def _hangar_clicked(self, checked):
        if self.selected is None:
            return
        self.win.marks = H.mark(self.win.root, [self.selected['name']], checked)
        self.model.marks = self.win.marks
        self.table.viewport().update()
        self.win.vehicle_changed(self.selected)
