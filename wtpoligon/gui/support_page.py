"""Шаг «Вызываемая техника» по принятому макету A."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)

from .. import library
from ..support import catalog
from ..support.model import Entry, Support, stock


class SupportPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.model = Support()
        self.vehicle_name = ''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 8)
        heading = QHBoxLayout()
        title = QLabel('Вызываемая техника')
        title.setObjectName('title')
        heading.addWidget(title)
        heading.addStretch()
        back = QPushButton('← Техника')
        back.clicked.connect(lambda: self.win.go(0))
        heading.addWidget(back)
        layout.addLayout(heading)
        self.carrier = QLabel('')
        layout.addWidget(self.carrier)
        card = QFrame()
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 18)
        row = QHBoxLayout()
        row.addWidget(QLabel('Список вызываемых единиц'))
        row.addStretch()
        add = QPushButton('+ Добавить технику')
        add.setObjectName('primary')
        add.clicked.connect(lambda: self.pick())
        row.addWidget(add)
        card_layout.addLayout(row)
        self.list_layout = QVBoxLayout()
        card_layout.addLayout(self.list_layout)
        layout.addWidget(card)
        review = QPushButton('К проверке и записи →')
        review.clicked.connect(lambda: self.win.go(6))
        layout.addWidget(review, 0, Qt.AlignLeft)
        layout.addStretch()

    def set_vehicle(self, vehicle):
        if vehicle is None:
            self.vehicle_name = ''
            self.model = Support()
        elif vehicle['name'] != self.vehicle_name:
            self.vehicle_name = vehicle['name']
            self.model = stock(self.win.source.load(vehicle['file']))
        self.carrier.setText('Носитель: ' + (vehicle.get('ru') or vehicle.get('en') or vehicle['name']) if vehicle else '')
        self.render()

    def support(self):
        return self.model

    def render(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        names = {v['name']: v.get('ru') or v.get('en') or v['name'] for v in self.win.vehicles}
        mine = {x['id']: x['name'] for x in library.list_items(self.win.root)}
        if not self.model.entries:
            self.list_layout.addWidget(QLabel('У этой машины штатных вызываемых единиц нет. Добавьте технику кнопкой «+».'))
        for entry in list(self.model.entries):
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(12, 10, 12, 10)
            line.addWidget(QLabel(mine.get(entry.library_id) or names.get(entry.vehicle, entry.vehicle)), 1)
            if entry.kind == 'ground':
                line.addWidget(QLabel('Количество'))
                count = QSpinBox()
                count.setRange(1, 99)
                count.setValue(entry.count)
                count.valueChanged.connect(lambda value, e=entry: setattr(e, 'count', value))
                line.addWidget(count)
            else:
                line.addWidget(QLabel('Количество'))
                count = QSpinBox()
                count.setRange(1, 1)
                count.setValue(1)
                line.addWidget(count)
            replace = QPushButton('Заменить')
            replace.clicked.connect(lambda _=False, e=entry: self.pick(e))
            line.addWidget(replace)
            remove = QPushButton('Убрать')
            remove.clicked.connect(lambda _=False, e=entry: (self.model.entries.remove(e), self.render()))
            line.addWidget(remove)
            row.setObjectName('card')
            self.list_layout.addWidget(row)

    def pick(self, replace=None):
        dialog = QDialog(self)
        dialog.setWindowTitle('Выбрать вызываемую технику')
        dialog.resize(620, 500)
        lay = QVBoxLayout(dialog)
        find = QLineEdit()
        find.setPlaceholderText('Поиск по всей технике игры и своей сохранённой…')
        lay.addWidget(find)
        tabs = QHBoxLayout()
        category = QComboBox()
        for label, key in (('Все', 'all'), ('Самолёты и вертолёты', 'air'),
                           ('Наземная', 'ground'), ('Моя техника', 'mine')):
            category.addItem(label, key)
        tabs.addWidget(category)
        lay.addLayout(tabs)
        results = QListWidget()
        lay.addWidget(results)

        def refresh():
            rows = catalog.candidates(self.win.vehicles, self.model, library.list_items(self.win.root),
                                      find.text(), category.currentData())
            if replace is None and any(e.kind == 'air' for e in self.model.entries):
                rows = [r for r in rows if r[2] != 'air']
            results.clear()
            for vehicle, title, kind, saved in rows[:500]:
                from PySide6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(title)
                item.setData(Qt.UserRole, (vehicle, kind, saved))
                results.addItem(item)

        def choose(item):
            vehicle, kind, saved = item.data(Qt.UserRole)
            new = Entry(vehicle, kind, 1, saved)
            if replace in self.model.entries:
                self.model.entries[self.model.entries.index(replace)] = new
            else:
                self.model.entries.append(new)
            dialog.accept()
            self.render()

        find.textChanged.connect(refresh)
        category.currentIndexChanged.connect(refresh)
        results.itemClicked.connect(choose)
        refresh()
        dialog.exec()
