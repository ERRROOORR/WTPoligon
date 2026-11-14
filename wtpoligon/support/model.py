"""Сохраняемая модель вызова."""
from dataclasses import dataclass, field, asdict


@dataclass
class Entry:
    vehicle: str
    kind: str                 # air | ground
    count: int = 1
    library_id: str = ''


@dataclass
class Support:
    entries: list[Entry] = field(default_factory=list)

    def to_dict(self):
        return {'schema_version': 1, 'entries': [asdict(e) for e in self.entries]}

    @classmethod
    def from_dict(cls, data):
        if data.get('schema_version') != 1:
            raise ValueError('неизвестная версия вызываемой техники')
        return cls([Entry(**e) for e in data.get('entries', [])])


def stock(unit):
    entries = []
    plane = unit.block('supportPlane') if unit else None
    if plane and plane.get('supportPlaneClass'):
        entries.append(Entry(plane.get('supportPlaneClass'), 'air'))
    planes = unit.block('supportPlanes') if unit else None
    for row in (planes.blocks if planes else []):
        if row.name == 'plane' and row.get('class'):
            cls = row.get('class')
            name = cls.split('/', 1)[-1]
            existing = next((e for e in entries if e.kind == 'ground' and e.vehicle == name), None)
            if existing:
                existing.count += 1
            else:
                entries.append(Entry(name, 'ground'))
    return Support(entries)
