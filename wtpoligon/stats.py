"""Характеристики машины: разделы из реально найденных параметров BLK и правки копий."""
from dataclasses import dataclass
import ast
import json
import math
import os
import re

from . import edits as E
from . import loadout as L
from .game import blk as B


SECTIONS = {
    'air': ('Двигатель', 'Масса', 'Аэродинамика', 'РЛС', 'СПО', 'Ловушки', 'Название'),
    'heli': ('Двигатель', 'Масса', 'Аэродинамика', 'РЛС', 'СПО', 'Ловушки', 'Название'),
    'tank': ('Двигатель', 'Масса', 'Трансмиссия', 'Броня', 'Название'),
    'ship': ('Ход', 'Название'),
}
EDITABLE_TYPES = ('r', 'i', 'i64', 't', 'b', 'p2', 'p3', 'p4', 'ip2', 'ip3', 'ip4')
RADAR_ANGLES = {'azimuth': ('azimuthLimits', 180), 'elevation': ('elevationLimits', 90)}

LABELS = {
    'Mass/EmptyMass': 'Масса пустого', 'Mass/Takeoff': 'Взлётная масса',
    'Mass/MaxFuelMass0': 'Топливо, макс.',
    'VehiclePhys/engine/horsePowers': 'Мощность',
    'VehiclePhys/engine/maxRPM': 'Макс. обороты',
    'VehiclePhys/Mass/Empty': 'Масса пустого',
    'ShipPhys/engines/maxSpeed': 'Макс. скорость',
}


def label_for(path):
    if path in LABELS:
        return LABELS[path]
    if path.startswith('Aerodynamics/'):
        return {'Areas': 'Площадь крыла', 'CxMin': 'Сопротивление при нуле подъёмной силы',
                'ClMax': 'Макс. коэф. подъёмной силы'}.get(path.rsplit('/', 1)[-1], path)
    return path


@dataclass
class Parameter:
    section: str
    label: str
    file: str
    path: str
    type: str
    stock: object
    unit: str = ''
    status: str = 'не проверено'
    scale: float = 1.0
    ref: str = ''                 # путь ссылки на отдельный файл в машине
    count: int = 1              # число физических двигателей с этим типом
    engine_class: str = ''
    tooltip: str = ''
    section_visible: bool = True

    @property
    def key(self):
        return self.file, self.path


def walk(tree, prefix=''):
    """Листья BLK с индексами повторяющихся блоков и параметров, как в edits.override_path."""
    counts, seen = {}, {}
    for name, _typ, _value in tree.params:
        counts[name] = counts.get(name, 0) + 1
    for name, typ, value in tree.params:
        seen[name] = seen.get(name, 0) + 1
        part = name + ('[%d]' % seen[name] if counts[name] > 1 else '')
        yield prefix + part, typ, value
    counts, seen = {}, {}
    for block in tree.blocks:
        counts[block.name] = counts.get(block.name, 0) + 1
    for block in tree.blocks:
        seen[block.name] = seen.get(block.name, 0) + 1
        part = block.name + ('[%d]' % seen[block.name] if counts[block.name] > 1 else '')
        yield from walk(block, prefix + part + '/')


def _file_ref(value, fm=False):
    if not isinstance(value, str) or not value.lower().endswith('.blk'):
        return ''
    value = value.replace('\\', '/')
    if value.lower().startswith('gamedata/'):
        return value
    return ('gameData/flightModels/' if fm else 'gameData/') + value.lstrip('/')


class Stats:
    """Одна машина. Значения хранятся по (файл, путь), поэтому дерево и разделы всегда согласованы."""
    def __init__(self, source, vehicle, loadout=None):
        self.source, self.vehicle = source, vehicle
        self.loadout = loadout
        self.unit_file = vehicle['file']
        self.trees = {}
        self.refs = {}
        self.params = []
        self.values = {}
        self.title = ''
        self.mission_title = ''
        self.engine_mode = 'power'
        self.engine_instances = []
        self.trap_containers = set()
        self._load(self.unit_file)
        unit = self.trees.get(self.unit_file)
        if unit is None:
            return
        fm = _file_ref(unit.get('fmFile'), fm=True)
        if fm and source.load(fm) is not None:
            self.refs[fm] = 'fmFile'
            self._load(fm)
        self._sections(unit, fm if fm in self.trees else self.unit_file)

    def _load(self, file):
        tree = self.source.load(file)
        if tree is not None:
            self.trees[file] = tree

    def _add(self, section, label, file, path, unit='', status='не проверено', scale=1.0,
             ref='', count=1, engine_class='', tooltip='', section_visible=True):
        tree = self.trees.get(file)
        got = E.stock_param(tree, path) if tree is not None else None
        if got is None or any(p.file == file and p.path == path for p in self.params):
            return
        typ, stock = got
        if typ not in EDITABLE_TYPES:
            return
        self.params.append(Parameter(section, label, file, path, typ, stock, unit, status, scale,
                                     ref or self.refs.get(file, ''), count, engine_class, tooltip,
                                     section_visible))

    def _sections(self, unit, fm):
        kind = self.vehicle['kind']
        if kind in ('air', 'heli'):
            fm_tree = self.trees[fm]
            engine_types = sorted((b for b in fm_tree.blocks if re.fullmatch(r'EngineType\d+', b.name)),
                                  key=lambda b: int(b.name[10:]))
            physical = sorted((b for b in fm_tree.blocks if re.fullmatch(r'Engine\d+', b.name)),
                              key=lambda b: int(b.name[6:]))
            engines = [(i + 1, 'EngineType%d' % b.get('Type')) for i, b in enumerate(physical)
                       if isinstance(b.get('Type'), int)] if physical else []
            if not engines:
                engines = [(i + 1, b.name) for i, b in enumerate(engine_types)]
            self.engine_mode = ('thrust' if kind == 'air' and any(
                str(E.path_value(fm_tree, name + '/Main/Type')).lower() in ('jet', 'turbojet', 'turbofan')
                for _, name in engines) else 'power')
            grouped = {}
            for number, name in engines:
                grouped.setdefault(name, []).append(number)
            self.engine_instances = [(number, name, grouped[name]) for number, name in engines]
            for name, numbers in grouped.items():
                first, last = min(numbers), max(numbers)
                prefix = ('Двигатель %d' % first if len(numbers) == 1 else
                          'Двигатели %s' % ('–'.join(map(str, numbers)) if last - first + 1 == len(numbers)
                                         else ', '.join(map(str, numbers))))
                engine_class = str(E.path_value(fm_tree, name + '/Main/Type') or '').lower()
                if self.engine_mode == 'thrust':
                    candidates = ((name + '/Main/ThrustMax/ThrustMax0', 'тяга без форсажа у земли', 'кгс',
                                   'Базовая тяга из ЛМ при нулевой высоте и скорости; реальная тяга зависит от коэффициентов и режима двигателя.', True),
                                  (name + '/Main/Thrust', 'тяга (отдельное поле)', 'кгс',
                                   'Связь с тягой в игре не установлена.', False),
                                  (name + '/Main/AfterburnerBoost', 'множитель форсажа', '×',
                                   'Множитель базовой тяги для расчётного поля форсажа.', False))
                else:
                    candidates = ((name + '/Main/Power', 'мощность', 'л.с.', '', True),
                                  (name + '/Compressor/Power0', 'мощность нагнетателя', 'л.с.', '', False))
                for path, label, unit_name, tip, visible in candidates:
                    self._add('Двигатель', '%s · %s' % (prefix, label), fm, path,
                              unit_name, 'проверено в игре' if path.endswith('/Main/Power')
                              and self.engine_mode == 'power' and kind == 'air'
                              and self.vehicle['name'].startswith('a-26b')
                              else 'не проверено', count=len(numbers), engine_class=engine_class,
                              tooltip=tip, section_visible=visible)
            for name, label, status in (('EmptyMass', 'Масса пустого', 'проверено в игре'),
                                        ('Takeoff', 'Взлётная масса', 'в игре не влияет'),
                                        ('MaxFuelMass0', 'Топливо, макс.', 'не проверено')):
                self._add('Масса', label, fm, 'Mass/' + name, 'кг', status)
            for path, typ, _v in walk(fm_tree):
                if path.startswith('Aerodynamics/') and typ in ('r', 'i', 'i64'):
                    label = label_for(path)
                    self._add('Аэродинамика', label, fm, path,
                              'м²' if '/Areas/' in path else '', section_visible=label != path)
            sensors = unit.block('sensors')
            if sensors is not None:
                same = [b for b in sensors.blocks if b.name == 'sensor']
                for n, sensor in enumerate(same, 1):
                    ref = 'sensors/sensor[%d]/blk' % n
                    file = _file_ref(sensor.get('blk'))
                    if not file or self.source.load(file) is None:
                        continue
                    self.refs[file] = ref
                    self._load(file)
                    tree = self.trees[file]
                    if tree.get('type') == 'radar':
                        leaves = [(path, typ) for path, typ, _v in walk(tree)
                                  if path != 'type' and typ in EDITABLE_TYPES]
                        for path, typ in sorted(leaves, key=lambda row: not row[0].endswith('/range')):
                            measured = path.startswith('transivers/') and path.endswith('/range')
                            label = 'Дальность обнаружения' if measured else label_for(path)
                            self._add('РЛС', label, file, path,
                                      'км' if measured else '',
                                      'проверено в игре' if measured else 'не проверено в игре',
                                      1000 if measured else 1, ref,
                                      section_visible=measured and not any(p.section == 'РЛС' and p.section_visible
                                                                           for p in self.params))
                    elif E.stock_param(tree, 'range') is not None:
                        self._add('СПО', 'Дальность', file, 'range', 'км', 'проверено в игре', 1000, ref)
            self._countermeasures(unit)
        elif kind == 'tank':
            self._add('Двигатель', 'Мощность', self.unit_file, 'VehiclePhys/engine/horsePowers',
                      'л.с.', 'проверено в игре')
            self._add('Двигатель', 'Макс. обороты', self.unit_file, 'VehiclePhys/engine/maxRPM',
                      'об/мин')
            self._add('Масса', 'Масса пустого', self.unit_file, 'VehiclePhys/Mass/Empty',
                      'т', 'проверено в игре', 1000)
            for path, typ, _v in walk(unit):
                if path.startswith('VehiclePhys/mechanics/gearRatios/ratio'):
                    self._add('Трансмиссия', 'Передаточное число ' + path.rsplit('/', 1)[-1],
                              self.unit_file, path, '', 'проверено в игре')
                if path.startswith('DamageParts/') and path.endswith('/armorThickness'):
                    self._add('Броня', 'Толщина брони: ' + path.split('/')[-2],
                              self.unit_file, path, 'мм', 'проверено в игре')
        elif kind == 'ship':
            self._add('Ход', 'Макс. скорость', self.unit_file, 'ShipPhys/engines/maxSpeed',
                      'км/ч', 'проверено в игре', 1 / 3.6)

    def _countermeasures(self, unit):
        """Only launchers in the selected slot variants (and common weapons)."""
        selected = {}
        if self.loadout is not None:
            selected = {int(k): v
                        for k, v in self.loadout.slots.items()}
        slots = unit.block('WeaponSlots')
        if slots is None:
            return
        slot_blocks = [b for b in slots.blocks if b.name == 'WeaponSlot']
        for slot_index, slot in enumerate(slot_blocks, 1):
            variants = [b for b in slot.blocks if b.name == 'WeaponPreset']
            if not variants:
                continue
            slot_no = slot.get('index', slot_index - 1)
            choice = selected.get(slot_no)
            if choice is None:
                # The common weapons slot is independent of the selected pylon preset.
                if slot_no != 0:
                    continue
                variant_no, variant = 1, variants[0]
            else:
                name = choice.get('variant') or choice.get('sample')
                match = next(((i, v) for i, v in enumerate(variants, 1) if v.get('name') == name), None)
                if match is None:
                    continue
                variant_no, variant = match
            weapons = [b for b in variant.blocks if b.name == 'Weapon']
            for weapon_no, weapon in enumerate(weapons, 1):
                raw = str(choice.get('weapon') if choice and choice.get('weapon') else weapon.get('blk') or '')
                file = _file_ref(raw)
                types = set()
                if file:
                    launcher = self.source.load(file)
                    if launcher is not None:
                        types = {str(v).lower() for path, _typ, v in walk(launcher)
                                 if path.endswith('/bulletType') and str(v).lower() in ('flr', 'chff')}
                split = 'split' in os.path.basename(raw).lower() and 'launcher' in raw.lower()
                countermeasure = weapon.get('trigger') == 'countermeasures' or split or bool(types)
                if not countermeasure or weapon.get('bullets') is None:
                    continue
                kind = ('Смешанные ловушки' if split else
                        'ИК-ловушки' if types == {'flr'} else
                        'Дипольные отражатели' if types == {'chff'} else
                        'Смешанные ловушки' if types == {'flr', 'chff'} else
                        os.path.splitext(os.path.basename(raw))[0] or 'Ловушки')
                title = L.weapon_title(self.source, raw) if raw and hasattr(self.source, 'lang_csv') else ''
                title = title or os.path.splitext(os.path.basename(raw))[0]
                path = ('WeaponSlots/WeaponSlot[%d]/WeaponPreset[%d]/Weapon[%d]/bullets'
                        % (slot_index, variant_no, weapon_no))
                self._add('Ловушки', '%s · %s · пусковая %d' % (kind, title, weapon_no), self.unit_file,
                          path, 'шт.', 'проверено в игре', tooltip=raw, section_visible=False)
                if slot_no != 0:
                    self.trap_containers.add((self.unit_file, path))

    def trap_rows(self):
        return [p for p in self.params if p.section == 'Ловушки']

    def trap_totals(self):
        totals = {'Всего зарядов': sum(self.display(p) for p in self.trap_rows()),
                  'В подвесных контейнерах': sum(self.display(p) for p in self.trap_rows()
                                                  if p.key in self.trap_containers)}
        return totals

    def trap_split(self, ratio=(1, 1)):
        """Display estimate only: the game's selected flare/chaff ratio is not stored in the unit BLK."""
        fixed_ir = sum(self.display(p) for p in self.trap_rows() if p.label.startswith('ИК-ловушки ·'))
        fixed_chaff = sum(self.display(p) for p in self.trap_rows()
                          if p.label.startswith('Дипольные отражатели ·'))
        mixed = self.trap_totals()['Всего зарядов'] - fixed_ir - fixed_chaff
        a, b = ratio
        ir = fixed_ir + (round(mixed * a / (a + b)) if a + b else 0)
        return ir, self.trap_totals()['Всего зарядов'] - ir

    def set_trap_total(self, value):
        rows = self.trap_rows()
        old = sum(self.display(p) for p in rows)
        if not rows or old <= 0 or value < 0 or not float(value).is_integer():
            raise ValueError('недопустимый запас ловушек')
        previous = self.values.copy()
        try:
            allocated = 0
            for p in rows[:-1]:
                amount = round(value * self.display(p) / old)
                self.set(p, amount)
                allocated += amount
            self.set(rows[-1], value - allocated)
        except (ValueError, TypeError):
            self.values = previous
            raise

    def sections(self):
        names = {p.section for p in self.params if p.section_visible}
        if self.trap_rows():
            names.add('Ловушки')
        return [s for s in SECTIONS[self.vehicle['kind']] if s in names or s == 'Название']

    def for_section(self, section):
        return [p for p in self.params if p.section == section and p.section_visible]

    def value(self, p):
        return self.values.get(p.key, p.stock)

    def display(self, p):
        return self.value(p) / p.scale if isinstance(self.value(p), (int, float)) else self.value(p)

    def set(self, p, displayed):
        value = displayed * p.scale if p.type in ('r', 'i', 'i64') else displayed
        if isinstance(value, (int, float)) and not math.isfinite(value):
            raise ValueError('нужно конечное число')
        if p.type in ('i', 'i64') and (not isinstance(value, (int, float)) or not float(value).is_integer()):
            raise ValueError('нужно целое число')
        value = E.coerce(p.type, value)
        problem = self.invalid(p, value)
        if problem:
            raise ValueError(problem)
        if value == p.stock:
            self.values.pop(p.key, None)
        else:
            self.values[p.key] = value

    def invalid(self, p, value):
        angle = next((limit for field, limit in RADAR_ANGLES.values()
                      if p.path.startswith('scanPatterns/') and p.path.endswith('/' + field)), None)
        if angle is not None and (not isinstance(value, (tuple, list)) or len(value) != 2
                                  or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in value)
                                  or value[0] >= value[1] or value[0] < -angle or value[1] > angle):
            return 'угол обзора должен быть в пределах ±%d°' % angle
        if p.path.startswith('transivers/') and p.path.endswith('/angleHalfSens'):
            if not isinstance(value, (int, float)) or value <= 0 or value > 180:
                return 'ширина луча должна быть больше 0 и не больше 180°'
        if p.type in ('i', 'i64') and ('bullets' in p.path or 'count' in p.path.lower()) and value < 0:
            return 'количество не может быть отрицательным'
        if p.path.endswith(('EmptyMass', '/Empty', '/Takeoff', '/Power', '/Power0', '/horsePowers',
                            '/Thrust', '/ThrustMax0')) and value <= 0:
            return 'масса, мощность и тяга должны быть больше нуля'
        return ''

    def engine_parts(self, name):
        """One physical motor reads its shared type; afterburner is a BLK-derived estimate.

        At zero altitude/speed the reference coefficient is ThrustMaxCoeff_0_0 for
        dry thrust and ThrAftMaxCoeff_0_0 for afterburner. AfterburnerBoost is
        treated as a multiplier of ThrustMax0; the flight effect is unverified.
        Editing afterburner changes AfterburnerBoost, never the raw Thrust field.
        """
        rows = {p.path: p for p in self.params if p.section == 'Двигатель'}
        if self.engine_mode == 'power':
            p = rows.get(name + '/Main/Power')
            return (self.display(p) if p else None, None)
        base = rows.get(name + '/Main/ThrustMax/ThrustMax0')
        boost = rows.get(name + '/Main/AfterburnerBoost')
        if base is None:
            return None, None
        tree = self.trees[base.file]
        dry_coeff = E.path_value(tree, name + '/Main/ThrustMax/ThrustMaxCoeff_0_0')
        wet_coeff = E.path_value(tree, name + '/Main/ThrustMax/ThrAftMaxCoeff_0_0')
        dry = self.display(base) * (dry_coeff if isinstance(dry_coeff, (int, float)) else 1)
        wet = (self.display(base) * self.display(boost) *
               (wet_coeff if isinstance(wet_coeff, (int, float)) else 1)) if boost else None
        return dry, wet

    def engine_total(self, afterburner=False):
        index = 1 if afterburner else 0
        values = [self.engine_parts(name)[index] for _number, name, _shared in self.engine_instances]
        return sum(v for v in values if v is not None) if any(v is not None for v in values) else None

    def set_engine(self, name, value, afterburner=False):
        rows = {p.path: p for p in self.params if p.section == 'Двигатель'}
        if self.engine_mode == 'power':
            p = rows[name + '/Main/Power']
            self.set(p, value)
            return
        base = rows[name + '/Main/ThrustMax/ThrustMax0']
        tree = self.trees[base.file]
        coeff_name = 'ThrAftMaxCoeff_0_0' if afterburner else 'ThrustMaxCoeff_0_0'
        coeff = E.path_value(tree, name + '/Main/ThrustMax/' + coeff_name)
        coeff = coeff if isinstance(coeff, (int, float)) else 1
        if afterburner:
            boost = rows[name + '/Main/AfterburnerBoost']
            if value <= 0 or self.display(base) * coeff <= 0:
                raise ValueError('тяга должна быть больше нуля')
            self.set(boost, value / (self.display(base) * coeff))
        else:
            self.set(base, value / coeff)

    def set_engine_total(self, value, afterburner=False):
        old = self.engine_total(afterburner)
        if old is None or old <= 0 or value <= 0:
            raise ValueError('тяга или мощность должна быть больше нуля')
        previous = self.values.copy()
        try:
            for name in dict.fromkeys(name for _number, name, _shared in self.engine_instances):
                part = self.engine_parts(name)[1 if afterburner else 0]
                if part is not None:
                    self.set_engine(name, part * value / old, afterburner)
        except (ValueError, TypeError, KeyError):
            self.values = previous
            raise

    def general(self, section):
        if section == 'Двигатель' and self.vehicle['kind'] in ('air', 'heli'):
            return self.engine_total()
        if section == 'Ловушки':
            return self.trap_totals()['Всего зарядов']
        if section == 'РЛС':
            rows = [p for p in self.params if p.section == 'РЛС'
                      and p.path.startswith('transivers/') and p.path.endswith('/range')
                      and '/receiver/' not in p.path]
            search = [p for p in rows if any(token in p.path.lower()
                      for token in ('search', 'mprf', 'hprf', 'gtm'))]
            values = [self.display(p) for p in (search or rows)]
            return max(values) if values else None
        rows = self.for_section(section)
        if not rows:
            return None
        if self.is_sum(section):
            chosen = self._sum_rows(section, rows)
            chosen = chosen or rows[:1]
            return sum(self.display(p) * p.count for p in chosen)
        return self.display(rows[0])

    def radar_rows(self, metric):
        if metric in RADAR_ANGLES:
            field = RADAR_ANGLES[metric][0]
            return [p for p in self.params if p.section == 'РЛС' and p.type == 'p2'
                    and p.path.startswith('scanPatterns/') and p.path.endswith('/' + field)
                    and 'track' not in p.path.split('/')[1].lower()
                    and ('lock' not in p.path.split('/')[1].lower()
                         or 'search' in p.path.split('/')[1].lower())
                    and max(abs(v) for v in self.value(p)) > 0]
        if metric == 'beam':
            return [p for p in self.params if p.section == 'РЛС' and p.type in ('r', 'i')
                    and p.path.startswith('transivers/') and p.path.endswith('/angleHalfSens')
                    and '/antenna/' in p.path]
        return []

    def radar_general(self, metric):
        rows = self.radar_rows(metric)
        if metric in RADAR_ANGLES:
            values = [max(abs(v) for v in self.value(p)) for p in rows]
        else:
            values = [self.display(p) for p in rows]
        return max(values) if values else None

    def set_radar_general(self, metric, value):
        rows = self.radar_rows(metric)
        old = self.radar_general(metric)
        limit = RADAR_ANGLES[metric][1] if metric in RADAR_ANGLES else 180
        if not rows or old is None or old <= 0 or not math.isfinite(value) or not 0 < value <= limit:
            raise ValueError('значение должно быть больше 0 и не больше %d°' % limit)
        previous = self.values.copy()
        try:
            for p in rows:
                if metric in RADAR_ANGLES:
                    half = max(abs(v) for v in self.value(p)) * value / old
                    self.set(p, (-half, half))
                    prefix = p.path.rsplit('/', 1)[0]
                    companion = 'width' if metric == 'azimuth' else 'barHeight'
                    other = next((q for q in self.params if q.file == p.file and q.path == prefix + '/' + companion), None)
                    if other is not None:
                        count = 1
                        if metric == 'elevation':
                            count_p = next((q for q in self.params if q.file == p.file
                                            and q.path == prefix + '/barsCount'), None)
                            count = self.value(count_p) if count_p is not None else 1
                        maximum = 2 * half / count if count > 0 else 2 * half
                        if self.display(other) > maximum:
                            self.set(other, maximum)
                else:
                    self.set(p, self.display(p) * value / old)
        except (ValueError, TypeError):
            self.values = previous
            raise

    @staticmethod
    def _sum_rows(section, rows):
        if section == 'Двигатель':
            thrust = [p for p in rows if p.path.endswith('/ThrustMax/ThrustMax0')]
            return thrust or [p for p in rows if p.path.endswith(('/Main/Power', '/Main/Thrust'))]
        # Альтернативные подвесные контейнеры занимают тот же слот; их запасы не суммируются.
        return [p for p in rows if '/WeaponPreset[' not in p.path or '/WeaponPreset[1]/' in p.path]

    def set_general(self, section, value):
        if section == 'Двигатель' and self.vehicle['kind'] in ('air', 'heli'):
            self.set_engine_total(value)
            return
        if section == 'Ловушки':
            self.set_trap_total(value)
            return
        if section == 'РЛС':
            old = self.general(section)
            if not old or value <= 0:
                raise ValueError('дальность должна быть больше нуля')
            rows = [p for p in self.params if p.section == 'РЛС' and p.path.endswith('/range')]
            previous = self.values.copy()
            try:
                for p in rows:
                    self.set(p, self.display(p) * value / old)
            except (ValueError, TypeError):
                self.values = previous
                raise
            return
        rows = self.for_section(section)
        if not rows:
            return
        if self.is_sum(section):
            chosen = self._sum_rows(section, rows)
            chosen = chosen or rows[:1]
            old = sum(self.display(p) * p.count for p in chosen)
            if old <= 0:
                raise ValueError('сумма штатных значений равна нулю')
            new = [value * self.display(p) / old for p in chosen]
            old_values = self.values.copy()
            try:
                for p, v in dict((p.key, (p, v)) for p, v in zip(chosen, new)).values():
                    self.set(p, round(v) if p.type in ('i', 'i64') else v)
            except (ValueError, TypeError):
                self.values = old_values
                raise
        else:
            self.set(rows[0], value)

    def reset(self, section):
        for p in (self.params if section in ('РЛС', 'Ловушки', 'Двигатель') else self.for_section(section)):
            if p.section != section:
                continue
            self.values.pop(p.key, None)

    def edits(self):
        unique = {p.key: p for p in self.params if p.key in self.values}
        return [E.make_edit(self.trees[p.file], p.file, p.path, self.value(p), note=p.section + ': ' + p.label)
                for p in unique.values()]

    def is_sum(self, section):
        return section in ('Двигатель', 'Ловушки') and self.vehicle['kind'] in ('air', 'heli')

    def general_label(self, section):
        if section == 'РЛС':
            return 'Дальность обнаружения'
        if section == 'Двигатель' and self.vehicle['kind'] in ('air', 'heli'):
            return 'Тяга суммарно' if self.engine_mode == 'thrust' else 'Мощность суммарно'
        if section == 'Ловушки':
            return 'Ловушек всего'
        rows = self.for_section(section)
        return rows[0].label if rows else section

    def changed(self):
        return bool(self.values or self.title or self.mission_title)

    def all_leaves(self):
        return [(file, path, typ, value) for file, tree in self.trees.items()
                for path, typ, value in walk(tree)]

    def set_leaf(self, file, path, raw):
        got = E.stock_param(self.trees[file], path)
        if got is None:
            raise KeyError(path)
        typ, stock = got
        if typ not in EDITABLE_TYPES:
            raise ValueError('редактор этого типа пока недоступен')
        p = next((p for p in self.params if p.key == (file, path)), None)
        if p is None:
            p = Parameter('', path.rsplit('/', 1)[-1], file, path, typ, stock)
            self.params.append(p)
        self.set(p, self.parse(p, raw))

    @staticmethod
    def parse(p, raw):
        if p.type == 't':
            return raw
        if p.type == 'b':
            if raw.lower() not in ('true', 'false', 'yes', 'no', '1', '0'):
                raise ValueError('нужно true или false')
            return raw.lower() in ('true', 'yes', '1')
        if p.type in ('r', 'i', 'i64'):
            return float(raw.replace(',', '.'))
        try:
            return ast.literal_eval(raw)
        except (SyntaxError, ValueError) as exc:
            raise ValueError('нужен кортеж чисел') from exc


def ranges(source, vehicles, kind, params, cache_dir):
    """Разброс параметров по штатной технике; кэш меняется вместе с подписью игры."""
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, 'stats_ranges.json')
    try:
        with open(cache_path, encoding='utf-8') as stream:
            data = json.load(stream)
    except (OSError, ValueError):
        data = {}
    if data.get('signature') != source.signature():
        data = {'signature': source.signature(), 'ranges': {}}
    key = 'semantic-v3|' + kind + '|' + params[0].section
    def semantic(p):
        return re.sub(r'EngineType\d+', 'EngineType*', p.path) + '|' + p.engine_class
    if key not in data['ranges'] or any(semantic(p) not in data['ranges'][key]
                                        for p in params if p.type in ('r', 'i', 'i64')):
        found = {}
        groups = {}
        for p in params:
            if p.type in ('r', 'i', 'i64'):
                groups.setdefault(p.ref, []).append(p)
        extracted = {}
        for vehicle in vehicles:
            if vehicle['kind'] != kind:
                continue
            unit = source.load(vehicle['file'])
            if unit is None:
                continue
            fm = _file_ref(unit.get('fmFile'), fm=True)
            for ref, wanted in groups.items():
                if ref == 'fmFile':
                    file = fm
                elif ref:
                    file = _file_ref(E.path_value(unit, ref))
                else:
                    file = vehicle['file']
                if not file:
                    continue
                cache_key = (file.lower(), ref)
                if cache_key not in extracted:
                    tree = source.load(file)
                    values = {}
                    if tree is not None:
                        needed = {re.sub(r'EngineType\d+', 'EngineType*', p.path) for p in wanted}
                        classes = {}
                        for path, typ, value in walk(tree):
                            if typ not in ('r', 'i', 'i64'):
                                continue
                            canonical = re.sub(r'EngineType\d+', 'EngineType*', path)
                            if canonical not in needed:
                                continue
                            engine = re.match(r'(EngineType\d+)/', path)
                            engine_class = (classes.setdefault(engine[1], str(E.path_value(
                                tree, engine[1] + '/Main/Type') or '').lower()) if engine else '')
                            values.setdefault((canonical, engine_class), []).append(value)
                    extracted[cache_key] = values
                for p in wanted:
                    canonical = re.sub(r'EngineType\d+', 'EngineType*', p.path)
                    for value in extracted[cache_key].get((canonical, p.engine_class), []):
                        pair = found.setdefault(semantic(p), [value, value])
                        pair[0], pair[1] = min(pair[0], value), max(pair[1], value)
        data['ranges'][key] = found
        with open(cache_path, 'w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False)
    return {p.path: data['ranges'][key][semantic(p)] for p in params
            if semantic(p) in data['ranges'][key]}


def radar_ranges(source, vehicles, kind, cache_dir):
    """Разброс общих углов и луча по штатным РЛС этого вида техники."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, 'stats_radar_ranges.json')
    try:
        with open(path, encoding='utf-8') as stream:
            data = json.load(stream)
    except (OSError, ValueError):
        data = {}
    if data.get('signature') != source.signature():
        data = {'signature': source.signature(), 'ranges': {}}
    if kind not in data['ranges']:
        found, seen = {}, set()
        for vehicle in vehicles:
            if vehicle['kind'] != kind:
                continue
            unit = source.load(vehicle['file'])
            sensors = unit.block('sensors') if unit is not None else None
            if sensors is None:
                continue
            for sensor in sensors.blocks:
                file = _file_ref(sensor.get('blk'))
                if not file or file.lower() in seen:
                    continue
                seen.add(file.lower())
                tree = source.load(file)
                if tree is None or tree.get('type') != 'radar':
                    continue
                for leaf, typ, value in walk(tree):
                    metric = next((name for name, (field, _limit) in RADAR_ANGLES.items()
                                   if leaf.startswith('scanPatterns/') and leaf.endswith('/' + field)
                                   and 'track' not in leaf.split('/')[1].lower()
                                   and ('lock' not in leaf.split('/')[1].lower()
                                        or 'search' in leaf.split('/')[1].lower())), None)
                    if metric and typ == 'p2':
                        number = max(abs(v) for v in value)
                    elif leaf.startswith('transivers/') and '/antenna/' in leaf and leaf.endswith('/angleHalfSens') and typ in ('r', 'i'):
                        metric, number = 'beam', value
                    else:
                        continue
                    if number <= 0:
                        continue
                    pair = found.setdefault(metric, [number, number])
                    pair[0], pair[1] = min(pair[0], number), max(pair[1], number)
        data['ranges'][kind] = found
        with open(path, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False)
    return data['ranges'][kind]
