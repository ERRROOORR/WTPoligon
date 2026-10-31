"""Сохраняемая модель выбора боеприпасов."""
from dataclasses import asdict, dataclass, field

from ..edits import Edit


@dataclass
class Slot:
    shell: str = ''
    count: int = 0


@dataclass
class AirGun:
    weapon: str = ''
    belt: str = ''
    rounds_per_barrel: int = 0


@dataclass
class Ammo:
    gun: str = ''
    capacity: int = 0
    stock_capacity: int = 0
    slots: list[Slot] = field(default_factory=lambda: [Slot() for _ in range(4)])
    added: list[str] = field(default_factory=list)
    edits: list[Edit] = field(default_factory=list)
    air_guns: list[AirGun] = field(default_factory=list)

    def to_dict(self):
        return {'schema_version': 1, 'gun': self.gun, 'capacity': self.capacity,
                'stock_capacity': self.stock_capacity,
                'slots': [asdict(s) for s in self.slots], 'added': list(self.added),
                'edits': [e.to_dict() for e in self.edits], 'air_guns': [asdict(g) for g in self.air_guns]}

    @classmethod
    def from_dict(cls, data):
        if data.get('schema_version') != 1:
            raise ValueError('неизвестная версия боекомплекта')
        return cls(data.get('gun', ''), data.get('capacity', 0), data.get('stock_capacity', 0),
                   [Slot(**s) for s in data.get('slots', [])], list(data.get('added', [])),
                   [Edit.from_dict(e) for e in data.get('edits', [])],
                   [AirGun(**g) for g in data.get('air_guns', [])])

    def changed(self):
        return bool(self.gun or self.added or self.edits or self.air_guns or
                    (self.stock_capacity and self.capacity != self.stock_capacity) or
                    any(s.shell or s.count for s in self.slots))
