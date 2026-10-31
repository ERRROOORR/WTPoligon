"""Конструктор подвески авиации (этап 3, ТЗ §6.4; docs/research/pylons_survey.md, круги 17–22 и 31).

Что проверено в игре и на чём стоит модуль:
  - новая схема (WeaponSlots): свой пресет = файл weaponPresets/<копия>_<имя>.blk со списком Weapon{slot, preset}
    + запись preset{name, blk} в "@override:weapon_presets" копии самолёта (17-й круг);
  - «любое оружие» на пилоне = новый вариант слота: копия варианта-образца (узлы ShowNodes, параметры Weapon) без
    reqModification и запретов, с другим файлом оружия (ФАБ-9000 на эмиттерах 500-фунтовок, 17-й круг);
  - старая схема (только weapon_presets): свой пресет = include стокового файла пресета + замена Weapon[n]/blk
    (A-20G, 19-й круг);
  - свой пресет работает только у копии под своим именем: имя, добавленное в userVehicles машины из ангара, игра
    ищет в стоковом файле (22-й круг) — поэтому изменённая подвеска всегда едет копией; штатный пресет без
    изменений — и у машины из ангара (настоящее имя);
  - пределы maxloadMass*, maxDisbalance и запреты BannedWeaponPreset миссия не проверяет, масса и перекос
    действуют в полёте (17-й круг) → программа их показывает и объясняет, но не запрещает;
  - невесомая подвеска = копия ЛМ с EmptyMass − Mп + "@override:fmFile" (подтверждено, круги 19–20 и 31); масса
    подвески Mп = боеприпас × bullets + Weapon/mass + mass верхнего уровня файла оружия (держатель).
Пары пилонов и стороны по именам вариантов — только подсказка (pylons_survey.md «Парные точки»).
"""
import collections
import csv
import io
import json
import os
import re
from dataclasses import dataclass, field

from .game import blk as B
from .mission import PREFIX

PKG = 'content/pkg_local/'
AMMO_BLOCKS = ('bomb', 'rocket', 'torpedo', 'bullet')
# оружие, которое не подвешивается (встроенное): слот только с ним — не пилон
FIXED_TRIGGERS = ('machine gun', 'cannon', 'countermeasures')
# триггер по виду оружия, если стоковая авиация его не использует (оружие наземки/флота, ТЗ §6.6) — 📄
FALLBACK_TRIGGER = {'bomb': 'bombs', 'rocket': 'rockets', 'torpedo': 'torpedoes', 'gun': 'additional gun',
                    'container': 'rockets', 'tank': 'fuel tanks', 'other': 'bombs'}
KIND_NAMES = {'bomb': 'бомба', 'rocket': 'ракета', 'torpedo': 'торпеда', 'gun': 'пушка/пулемёт',
              'container': 'контейнер', 'tank': 'подвесной бак', 'other': 'прочее'}
# папки gameData/Weapons, из которых каталог берёт подвесное оружие (остальное — по флажку «всё оружие игры»)
PYLON_FOLDERS = ('bombguns', 'rocketguns', 'torpedoes', 'containers', 'drop_tank', 'payloadguns', 'mines')
CATALOG_VERSION = 5
# папки машин, у которых собираем «носителей» оружия (поиск оружия по машине)
CARRIER_FOLDERS = ('gamedata/flightmodels/', 'gamedata/units/tankmodels/', 'gamedata/units/ships/')

_LEFT = re.compile(r'(^|_)(left|l|port)(_|$|\d)', re.I)
_RIGHT = re.compile(r'(^|_)(right|r|starboard)(_|$|\d)', re.I)


# ---------------------------------------------------------------- пилоны машины

@dataclass
class Variant:
    name: str
    block: B.Block                       # стоковый блок WeaponPreset (не менять: дерево из кэша источника)

    @property
    def weapons(self):
        return [w for w in self.block.blocks if w.name == 'Weapon']

    @property
    def req_mod(self):
        return self.block.get('reqModification')

    @property
    def icon(self):
        """Тип иконки игры (iconType): картинка gameuiskin/<icon>.png в atlases.vromfs.bin."""
        return self.block.get('iconType') or ''

    @property
    def banned(self):
        return [(b.get('slot'), b.get('preset')) for b in self.block.blocks if b.name == 'BannedWeaponPreset']


@dataclass
class Slot:
    index: int
    n: int                               # номер блока WeaponSlot по порядку (с 1) — для "@override:WeaponSlot[n]"
    variants: list
    tier: int = None
    no_disbalance: bool = False

    def variant(self, name):
        return next((v for v in self.variants if v.name == name), None)

    @property
    def fixed(self):
        """Встроенное вооружение (пулемёты, пушки, ловушки), а не пилон."""
        trig = {w.get('trigger') or '' for v in self.variants for w in v.weapons}
        return bool(trig) and all(t in FIXED_TRIGGERS or t.startswith('gunner') for t in trig)

    @property
    def side(self):
        """'L' / 'R' по именам вариантов (left/right, _l/_r, port/starboard) или None — только подсказка."""
        votes = collections.Counter()
        for v in self.variants:
            left, right = bool(_LEFT.search(v.name)), bool(_RIGHT.search(v.name))
            if left != right:
                votes['L' if left else 'R'] += 1
        if not votes or (votes['L'] and votes['R']):
            return None
        return 'L' if votes['L'] else 'R'


@dataclass
class Pylons:
    scheme: str                          # 'slots' — WeaponSlots; 'legacy' — только weapon_presets; '' — нет подвески
    slots: list = field(default_factory=list)
    limits: dict = field(default_factory=dict)   # maxloadMass, maxloadMassLeftConsoles, …, maxDisbalance
    presets: list = field(default_factory=list)  # [(имя, путь файла)] штатных пресетов
    fm_file: str = ''                    # 'fm/a-26b.blk' (относительно gameData/flightModels)

    def slot(self, index):
        return next((s for s in self.slots if s.index == index), None)

    @property
    def pylon_slots(self):
        return [s for s in self.slots if not s.fixed]

    def preset_file(self, name):
        return next((p for n, p in self.presets if n == name), None)


def read_pylons(unit):
    """Пилоны из дерева файла машины (flightModels/<имя>.blk)."""
    wp = unit.block('weapon_presets')
    presets = [(p.get('name'), p.get('blk')) for p in (wp.blocks if wp else []) if p.name == 'preset' and p.get('name')]
    ws = unit.block('WeaponSlots')
    slot_blocks = [s for s in (ws.blocks if ws else []) if s.name == 'WeaponSlot']
    if slot_blocks:
        slots = []
        for n, s in enumerate(slot_blocks, 1):
            variants = [Variant(p.get('name'), p) for p in s.blocks if p.name == 'WeaponPreset' and p.get('name')]
            slots.append(Slot(s.get('index'), n, variants, s.get('tier'), bool(s.get('notUseforDisbalanceCalculation'))))
        limits = {k: v for k, _t, v in ws.params if k.startswith('max')}
        return Pylons('slots', slots, limits, presets, unit.get('fmFile') or '')
    return Pylons('legacy' if presets else '', [], {}, presets, unit.get('fmFile') or '')


def preset_pairs(source, pylons, name):
    """{слот: вариант} штатного пресета новой схемы или None (файл не из пар slot/preset)."""
    path = pylons.preset_file(name)
    tree = source.load(path) if path else None
    if tree is None:
        return None
    pairs = {}
    for w in tree.blocks:
        if w.name != 'Weapon':
            continue
        if w.get('slot') is None or w.get('preset') is None:
            return None
        pairs[w.get('slot')] = w.get('preset')
    return pairs


def legacy_weapons(source, pylons, name):
    """[Weapon] файла штатного пресета (старая схема) или None."""
    path = pylons.preset_file(name)
    tree = source.load(path) if path else None
    if tree is None:
        return None
    return [w for w in tree.blocks if w.name == 'Weapon']


def mirror_pairs(pylons):
    """{слот: парный слот} — предположение по именам вариантов (left↔right), подтверждает пользователь."""
    out = {}
    for s in pylons.pylon_slots:
        if s.index in out:
            continue
        sided = {v.name for v in s.variants if _swap_side(v.name) != v.name}
        for t in pylons.pylon_slots:
            if t is s or t.index in out:
                continue
            if sided & {_swap_side(v.name) for v in t.variants}:
                out[s.index], out[t.index] = t.index, s.index
                break
    return out


_SIDE_WORDS = {'left': 'right', 'right': 'left', 'l': 'r', 'r': 'l', 'port': 'starboard', 'starboard': 'port'}


def _swap_side(name):
    """Имя с другой стороной: 'hvar_x7_left' -> 'hvar_x7_right', 'pod_1_l' -> 'pod_1_r' (по частям через '_')."""
    out = []
    for part in name.split('_'):
        m = re.fullmatch(r'([A-Za-z]+)(\d*)', part)
        word = m.group(1) if m else ''
        if word.lower() in _SIDE_WORDS:
            new = _SIDE_WORDS[word.lower()]
            part = (new.upper() if word.isupper() and len(word) > 1 or word in ('L', 'R') else new) + m.group(2)
        out.append(part)
    return '_'.join(out)


# ---------------------------------------------------------------- подвеска пользователя

@dataclass
class Loadout:
    """Подвеска. Новая схема: slots {слот: {'variant': имя} | {'weapon': путь, 'sample': вариант-образец[,
    'count': сколько точек образца занять — первые по порядку, как одна ФАБ в отсеке в 18-м круге]}};
    пустой слот — нет в slots. Старая схема: base — штатный пресет-основа, legacy {номер Weapon с 1: путь}."""
    base: str = ''
    slots: dict = field(default_factory=dict)
    legacy: dict = field(default_factory=dict)
    weightless: bool = False
    name: str = ''

    def to_dict(self):
        return {'base': self.base, 'slots': {str(k): v for k, v in sorted(self.slots.items())},
                'legacy': {str(k): v for k, v in sorted(self.legacy.items())}, 'weightless': self.weightless,
                'name': self.name}

    @classmethod
    def from_dict(cls, d):
        return cls(d.get('base', ''), {int(k): dict(v) for k, v in (d.get('slots') or {}).items()},
                   {int(k): v for k, v in (d.get('legacy') or {}).items()}, bool(d.get('weightless')),
                   d.get('name', ''))


def from_preset(source, pylons, name):
    """Подвеска «как штатный пресет name» (шаблон ТЗ §6.4)."""
    if pylons.scheme == 'slots':
        pairs = preset_pairs(source, pylons, name)
        if pairs is None:
            raise ValueError('пресет %s — не список слотов, шаблоном не годится' % name)
        return Loadout(name, {s: {'variant': v} for s, v in pairs.items()})
    return Loadout(name)


def stock_preset_of(source, pylons, lo):
    """Имя штатного пресета, если подвеска с ним совпадает и не невесомая (копия не нужна), иначе None."""
    if lo.weightless or not lo.base or pylons.preset_file(lo.base) is None:
        return None
    if pylons.scheme == 'legacy':
        return lo.base if not lo.legacy else None
    pairs = preset_pairs(source, pylons, lo.base)
    return lo.base if pairs is not None and lo.slots == {s: {'variant': v} for s, v in pairs.items()} else None


def fill_all(pylons, weapon_path, slots=None):
    """«Всё одним типом»: weapon_path на каждый пилон (образец — первый вариант слота)."""
    out = {}
    for s in pylons.pylon_slots:
        if slots is None or s.index in slots:
            out[s.index] = {'weapon': weapon_path, 'sample': s.variants[0].name}
    return out


def mirror(lo, pylons, src_slot, dst_slot):
    """Зеркалирование: на dst_slot — то же, что на src_slot (вариант — парный по имени, если он есть)."""
    choice = lo.slots.get(src_slot)
    dst = pylons.slot(dst_slot)
    if dst is None:
        raise KeyError('нет слота %s' % dst_slot)
    if choice is None:
        lo.slots.pop(dst_slot, None)
    elif 'variant' in choice:
        twin = _swap_side(choice['variant'])
        if dst.variant(twin):
            lo.slots[dst_slot] = {'variant': twin}
        elif dst.variant(choice['variant']):
            lo.slots[dst_slot] = {'variant': choice['variant']}
        else:   # варианта на парном нет — то же оружие на образце парного слота
            w = pylons.slot(src_slot).variant(choice['variant']).weapons
            lo.slots[dst_slot] = {'weapon': w[0].get('blk'), 'sample': dst.variants[0].name}
    else:
        sample = _swap_side(choice['sample'])
        lo.slots[dst_slot] = {'weapon': choice['weapon'],
                              'sample': sample if dst.variant(sample) else dst.variants[0].name}
    return lo


# ---------------------------------------------------------------- оружие: каталог, названия, масса

def weapon_key(path):
    """Ключ сравнения пути оружия: нижний регистр, без '#/develop/gameBase/' и повторных '/', с '.blk'."""
    p = _blk_path((path or '').replace('\\', '/').lower())
    p = p.split('#/develop/gamebase/')[-1]
    return re.sub('/+', '/', p)


def weapon_stem(path):
    return weapon_key(path).rsplit('/', 1)[-1][:-4]


def _blk_path(path):
    """Путь файла оружия как его ищет игра: ссылки бывают без '.blk' (e8n2 → jp_navy_type97mod6_60kg)."""
    return path if (path or '').lower().endswith('.blk') else (path or '') + '.blk'


def load_weapon(source, path):
    return source.load(_blk_path(path)) if path else None


def weapon_exists(source, path):
    return bool(path) and source.exists(_blk_path(path))


_INFO = {}


def weapon_info(source, path, _depth=0):
    """Оружие по файлу: {kind, ammo, holder, per, title, unit_title}. Держатель-контейнер (container, blk, bullets:
    MER ×6, TER ×3, адаптер AIM-120 ×2) раскрывается: вид и название — того, что в нём, ammo — масса содержимого
    одного держателя. Масса подвеса с bullets штук: bullets × ammo + holder (как payload_mass генератора)."""
    key = (id(source), weapon_key(path))
    if key in _INFO:
        return _INFO[key]
    tree = load_weapon(source, path)
    names = _names(source)
    stem = weapon_stem(path)
    en, ru = names.get('weapons/%s/short' % stem) or names.get('weapons/%s' % stem) or ('', '')
    own = ru or en
    info = {'kind': 'other', 'ammo': 0.0, 'holder': 0.0, 'per': 1, 'title': own or stem, 'unit_title': own or stem}
    if tree is not None:
        info['holder'] = _num(tree.get('mass'))
        ammo = next(((k, tree.block(k)) for k in AMMO_BLOCKS + ('payload',) if tree.block(k) is not None), None)
        inner = tree.get('blk') if isinstance(tree.get('blk'), str) else None
        if ammo is not None:            # payload — подвесной бак: масса пустого бака, топливо — в лётной модели
            info['kind'] = {'bullet': 'gun', 'payload': 'tank'}.get(ammo[0], ammo[0])
            info['ammo'] = _num(ammo[1].get('mass'))
            # ракета в «снаряде» (ЗУР наземки/флота: bullet{rocket{guidance…}}) — это ракета, не пушка
            rocket = ammo[1] if ammo[0] == 'rocket' else ammo[1].block('rocket') if ammo[0] == 'bullet' else None
            if rocket is not None:
                info['kind'] = 'rocket'
                info['ammo'] = info['ammo'] or _num(rocket.get('mass'))
                info['guided'] = rocket.block('guidance') is not None or bool(rocket.get('guidanceType'))
                info['aam'] = bool(ammo[1].get('isAam') or rocket.get('isAam'))
        elif inner and _depth < 3:
            sub = weapon_info(source, inner, _depth + 1)
            n = int(_num(tree.get('bullets')) or 1)
            info['kind'] = sub['kind'] if sub['kind'] != 'other' else 'container'
            if sub['kind'] == 'gun':            # пушечный контейнер: bullets — патроны
                info.update(ammo=n * sub['ammo'] + sub['holder'], per=1, unit_title=sub['title'])
            else:
                info.update(ammo=n * (sub['ammo'] * sub['per'] + sub['holder']), per=n * sub['per'],
                            unit_title=sub['unit_title'])
            if not own:
                info['title'] = info['unit_title'] + (' ×%d' % info['per'] if info['per'] > 1 else '')
        elif any(b.name in ('weapon', 'Weapon') for b in tree.blocks):
            info['kind'] = 'container'
    _INFO[key] = info
    return info


def weapon_kind(source, path):
    return weapon_info(source, path)['kind']


def weapon_mass(source, path, bullets=1):
    """Масса подвеса: bullets × (боеприпас или содержимое держателя) + mass верхнего уровня файла."""
    i = weapon_info(source, path)
    return i['ammo'] * (bullets or 1) + i['holder']


# группы вооружения в списке выбора (по классам, как в игре): ключ -> название; порядок — порядок показа
GROUPS = [('aam', 'Ракеты «воздух — воздух»'), ('agm', 'Ракеты «воздух — поверхность»'),
          ('rockets', 'Неуправляемые ракеты'), ('guided', 'Управляемые бомбы'), ('glide', 'Планирующие бомбы'),
          ('bombs', 'Бомбы'), ('torpedoes', 'Торпеды'), ('tanks', 'Подвесные баки'),
          ('pods', 'Контейнеры и прицелы'), ('guns', 'Пушки и пулемёты'), ('other', 'Прочее')]
GROUP_NAMES = dict(GROUPS)


def weapon_group(trigger, icon='', kind=''):
    """Класс вооружения по триггеру, типу иконки игры и виду файла."""
    t, i = (trigger or '').lower(), (icon or '').lower()
    if t == 'fuel tanks' or kind == 'tank' or i.startswith('ptb') and 'missile' not in i and 'bomb' not in i:
        return 'tanks'
    if t == 'aam' or 'air_to_air' in i:
        return 'aam'
    if t in ('atgm', 'agm') or 'agm' in i or 'atgm' in i or 'anti_radiation' in i or 'anti_ship' in i:
        return 'agm'
    if t == 'guided bombs' or 'guided_bomb' in i:
        return 'glide' if 'glide' in i else 'guided'
    if t == 'bombs' or kind == 'bomb':
        return 'bombs'
    if t == 'rockets' or kind == 'rocket':
        return 'rockets'
    if t == 'torpedoes' or kind == 'torpedo':
        return 'torpedoes'
    if t in ('targetingpod', 'countermeasures') or 'container' in i or i.startswith('ltc'):
        return 'pods'
    if t in ('cannon', 'additional gun', 'machine gun') or kind == 'gun':
        return 'guns'
    return 'other'


def variant_group(v):
    """Класс варианта — по главному оружию (не баку): «КТБ + MK81 ×6» — бомбы."""
    ws = v.weapons
    w = next((x for x in ws if (x.get('trigger') or '') != 'fuel tanks'), ws[0] if ws else None)
    icon = v.icon if w is ws[0] or not ws else ''
    return weapon_group(w.get('trigger') if w is not None else '', icon)


def items_caption(source, items, sep=' + '):
    """Подпись набора [(путь, Weapon)]: «MK82 500 фн ×6», «КТБ + MK81 250 фн ×6»; пушки — без числа патронов."""
    counts = {}
    for path, w in items:
        info = weapon_info(source, path)
        n = 1 if info['kind'] == 'gun' else ((w.get('bullets') if w is not None else 1) or 1) * info['per']
        counts[info['unit_title']] = counts.get(info['unit_title'], 0) + n
    return sep.join('%s ×%d' % (t, n) if n > 1 else t for t, n in counts.items())


def preset_title(source, pylons, name):
    """Название штатного пресета, как в игре, — из содержимого: «AIM-120C-5 ×4 · AIM-9M ×4 · ПТБ ×3»
    (своих названий у пресетов в файлах локализации нет). Встроенное вооружение не пишется."""
    items = []
    pairs = preset_pairs(source, pylons, name) if pylons.scheme == 'slots' else None
    if pairs is not None:
        for index, variant in sorted(pairs.items()):
            s = pylons.slot(index)
            if s is not None and not s.fixed:
                items += slot_weapons(pylons, index, {'variant': variant})
    else:
        items = [(w.get('blk'), w) for w in (legacy_weapons(source, pylons, name) or []) if w.get('blk')]
        items = [(p, w) for p, w in items if weapon_kind(source, p) != 'gun' or w.get('trigger') not in
                 ('machine gun', 'cannon')]
    return items_caption(source, items, ' · ') or 'Без подвески'


def preset_titles(source, pylons):
    """[(имя пресета, название)]; одинаковые названия различаются номером."""
    out, seen = [], {}
    for name, _p in pylons.presets:
        t = preset_title(source, pylons, name)
        seen[t] = seen.get(t, 0) + 1
        out.append((name, t if seen[t] == 1 else '%s (%d)' % (t, seen[t])))
    return out


def variant_caption(source, v):
    return items_caption(source, [(w.get('blk'), w) for w in v.weapons])


def variant_mass(source, v):
    return sum(_item_mass(source, w.get('blk'), w) for w in v.weapons)


def atlas_icon(source, icon):
    """PNG иконки вооружения из atlases.vromfs.bin: gameuiskin/<iconType>.png (как в меню подвески игры) или None."""
    return source.atlas_file('gameuiskin/%s.png' % icon) if icon else None


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else 0.0


def read_weapon_names(csv_text):
    """{ключ: (английский, русский)} из units_weaponry.csv (ключи 'weapons/<имя>' и 'weapons/<имя>/short')."""
    out = {}
    if not csv_text:
        return out
    rows = csv.reader(io.StringIO(csv_text), delimiter=';', quotechar='"')
    header = next(rows, [])
    try:
        en, ru = header.index('<English>'), header.index('<Russian>')
    except ValueError:
        return out
    for row in rows:
        if len(row) > max(en, ru) and row[0].startswith('weapons/'):
            out[row[0].lower()] = (row[en], row[ru])
    return out


def build_catalog(source, progress=None):
    """Каталог всего оружия игры: [{path, stem, folder, kind, en, ru, mass, trigger, bullets, air, pylon}].
    trigger/bullets — как чаще всего у стоковой авиации (air=True) или по виду оружия (air=False, 📄).
    progress(сделано, всего) — для полоски загрузки в окне (вызывается каждые ~100 файлов)."""
    unit_files = [(f, p) for f in CARRIER_FOLDERS for p in source.list_files(f)
                  if p.count('/') == f.count('/') and p.endswith('.blk')]
    weapon_files = [p for p in source.list_files('gamedata/weapons/') if p.endswith('.blk')]
    total, done = len(unit_files) + len(weapon_files), 0

    def tick():
        nonlocal done
        done += 1
        if progress and done % 100 == 0:
            progress(done, total)
    names = read_weapon_names(source.lang_csv('units_weaponry'))
    usage = collections.defaultdict(collections.Counter)
    counts = collections.defaultdict(collections.Counter)
    icons = collections.defaultdict(collections.Counter)
    carriers = collections.defaultdict(set)
    for _folder, path in unit_files:
        tick()
        unit = source.load(path)
        if unit is None:
            continue
        carrier = path.rsplit('/', 1)[-1][:-4]
        ws = unit.block('WeaponSlots')
        for s in (ws.blocks if ws else []):
            for p in s.blocks:
                for w in (p.blocks if p.name == 'WeaponPreset' else []):
                    if w.name == 'Weapon' and w.get('blk'):
                        usage[weapon_key(w.get('blk'))][w.get('trigger') or ''] += 1
                        counts[weapon_key(w.get('blk'))][w.get('bullets') or 1] += 1
                        if p.get('iconType'):
                            icons[weapon_key(w.get('blk'))][p.get('iconType')] += 1
        # носитель: всё оружие файла машины и её файлов пресетов (самолёт, вертолёт, танк, корабль)
        refs = _weapon_refs(unit)
        wp = unit.block('weapon_presets')
        for pr in (wp.blocks if wp else []):
            tree = source.load(pr.get('blk')) if pr.get('blk') else None
            refs |= _weapon_refs(tree) if tree is not None else set()
        for ref in refs:
            carriers[weapon_key(ref)].add(carrier)
    out = []
    for path in weapon_files:
        tick()
        rel = path[len('gamedata/weapons/'):]
        folder = rel.split('/')[0] if '/' in rel else ''
        info = weapon_info(source, path)
        kind = info['kind']
        if kind == 'other' and folder not in PYLON_FOLDERS:
            continue
        stem = rel.rsplit('/', 1)[-1][:-4]
        en, ru = names.get('weapons/%s/short' % stem) or names.get('weapons/%s' % stem) or ('', '')
        used = usage.get(path)
        bullets = counts[path].most_common(1)[0][0] if used else 1
        trigger = used.most_common(1)[0][0] if used else (
            'aam' if info.get('aam') else 'atgm' if info.get('guided') else FALLBACK_TRIGGER[kind])
        icon = icons[path].most_common(1)[0][0] if icons.get(path) else ''
        out.append({'path': 'gameData/Weapons/' + rel, 'stem': stem, 'folder': folder, 'kind': kind,
                    'en': en, 'ru': ru or ('' if en else info['title']), 'mass': round(weapon_mass(
                        source, path, bullets), 2), 'trigger': trigger, 'bullets': bullets, 'air': bool(used),
                    'pylon': folder in PYLON_FOLDERS, 'icon': icon, 'group': weapon_group(trigger, icon, kind),
                    'carriers': sorted(carriers.get(path, ()))})
    out.sort(key=lambda w: (not w['pylon'], w['folder'], w['stem']))
    return out


def _weapon_refs(tree):
    """Пути оружия в дереве: любые параметры blk со ссылкой на gameData/Weapons."""
    out, stack = set(), [tree]
    while stack:
        node = stack.pop()
        for k, _t, v in node.params:
            if k == 'blk' and isinstance(v, str) and 'weapons/' in v.lower():
                out.add(v)
        stack.extend(node.blocks)
    return out


def load_catalog(source, cache_dir, refresh=False, progress=None):
    """Каталог из кэша (ключ — подпись источника), иначе собрать и сохранить (progress — см. build_catalog)."""
    sig = source.signature()
    path = os.path.join(cache_dir, 'weapons_%s.json' % source.kind)
    if not refresh and os.path.isfile(path):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            if data.get('signature') == sig and data.get('version') == CATALOG_VERSION:
                return data['weapons']
        except (OSError, ValueError, KeyError):
            pass
    weapons = build_catalog(source, progress)
    os.makedirs(cache_dir, exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump({'version': CATALOG_VERSION, 'signature': sig, 'weapons': weapons}, f, ensure_ascii=False)
    os.replace(path + '.tmp', path)
    return weapons


def find_weapons(catalog, text='', kind=None, pylon_only=True, group=None):
    """Простой фильтр подстрокой (командная строка без индекса техники); окно — search_weapons."""
    t = (text or '').lower().strip()
    out = []
    for w in catalog:
        if pylon_only and not w['pylon']:
            continue
        if kind and w['kind'] != kind:
            continue
        if group and w['group'] != group:
            continue
        if t and t not in w['stem'] and t not in w['ru'].lower() and t not in w['en'].lower():
            continue
        out.append(w)
    return out


def _weapon_label(w):
    return w['ru'] or w['en'] or w['stem']


def search_weapons(catalog, vehicles, text, pylon_only=True, group=None, max_carriers=60):
    """Поиск оружия как поиск техники (с опечатками, в любой раскладке — game/search.py) по названию оружия и по
    носителю: «ф15с», «т-80бвм», «ми28» — всё вооружение этой машины (самолёты, вертолёты, танки, корабли).
    -> ([оружие каталога], [найденные носители — машины индекса]). Нашёлся носитель — его оружие (всё, и пушки) и
    точные совпадения по названию оружия («m/50» — и бомба m/50, и вооружение M50 Ontos); иначе — совпадения по
    названию (нечёткие не подвесные — только без фильтра «только подвесное»). Одноимённых носителей (версии
    «_killstreak», разные нации) берём всех."""
    from .game import search as S
    keep = (lambda w: not group or w['group'] == group)
    if not S.norm(text):
        return [w for w in catalog if keep(w) and (w['pylon'] or not pylon_only)], []
    # по названию ищем во всём оружии игры: точное совпадение (≥ 95) показываем всегда, даже не подвесное
    # («aim-9x» → «ЗУР AIM-9X» наземного комплекса), нечёткое не подвесное — только с галочкой
    by_name = [(w, sc) for w, sc in S.searcher(catalog, S.weapon_keys, _weapon_label).search(text)
               if keep(w) and (w['pylon'] or not pylon_only or sc >= 95)]
    top_weapon = by_name[0][1] if by_name else 0
    hits = S.searcher(vehicles).search(text) if vehicles else []
    carriers = []
    if hits and hits[0][1] >= max(85, top_weapon):
        top = hits[0][1]
        carriers = [v for v, sc in hits if sc >= top - 3][:max_carriers]
    if carriers:
        names = {v['name'].lower() for v in carriers}
        order = {g: n for n, (g, _t) in enumerate(GROUPS)}
        own = sorted((w for w in catalog if keep(w) and names & set(w.get('carriers') or ())),
                     key=lambda w: (order.get(w['group'], 99), _weapon_label(w)))
        seen = {w['path'] for w in own}
        return own + [w for w, sc in by_name if sc >= 95 and w['path'] not in seen], carriers
    return [w for w, _sc in by_name], []


def weapon_title(source, path, names=None):
    """Короткое русское название оружия (держатель — по содержимому: «MK82 500 фн ×6»; иначе имя файла)."""
    return weapon_info(source, path)['title']


_NAMES_CACHE = {}


def _names(source):
    key = id(source)
    if key not in _NAMES_CACHE:
        _NAMES_CACHE[key] = read_weapon_names(source.lang_csv('units_weaponry'))
    return _NAMES_CACHE[key]


# ---------------------------------------------------------------- итоги: масса, состав, предупреждения

def slot_weapons(pylons, index, choice):
    """[(путь оружия, Weapon-образец)] выбора на слоте."""
    s = pylons.slot(index)
    if s is None or not choice:
        return []
    if 'variant' in choice:
        v = s.variant(choice['variant'])
        return [(w.get('blk'), w) for w in v.weapons] if v else []
    v = s.variant(choice.get('sample')) or s.variants[0]
    return [(choice['weapon'], w) for w in v.weapons[:choice.get('count') or None]]


def _item_mass(source, path, w, catalog_entry=None):
    bullets = w.get('bullets') if w is not None else None
    if catalog_entry is not None and w is not None and weapon_key(w.get('blk')) != weapon_key(path):
        bullets = catalog_entry['bullets']        # чужое оружие на образце: количество — как у него на авиации
    wmass = w.get('mass') if w is not None and weapon_key(w.get('blk')) == weapon_key(path) else None
    return weapon_mass(source, path, bullets) + _num(wmass)


@dataclass
class Summary:
    total: float = 0.0
    by_slot: dict = field(default_factory=dict)       # {слот: кг}
    items: list = field(default_factory=list)         # [(слот или номер Weapon, путь оружия, кг)]
    counts: dict = field(default_factory=dict)        # {название: штук}
    left: float = 0.0
    right: float = 0.0
    unknown_side: float = 0.0
    req_mods: dict = field(default_factory=dict)      # {модификация ангара: [пилоны]}
    warnings: list = field(default_factory=list)      # [(уровень 'refuse'|'warn'|'untested'|'info', текст)]
    empty_mass: float = None
    weightless_mass: float = None                     # EmptyMass − Mп для копии ЛМ


def summarize(source, pylons, lo, catalog=None):
    """Живые итоги (ТЗ §6.4): масса против допустимой, сколько чего висит, предупреждения с объяснением."""
    by_path = {weapon_key(w['path']): w for w in (catalog or [])}
    sm = Summary()
    if pylons.scheme == 'slots':
        for index, choice in sorted(lo.slots.items()):
            s = pylons.slot(index)
            if s is None:
                sm.warnings.append(('refuse', 'нет пилона %s у этой машины' % index))
                continue
            if s.fixed and 'variant' in choice:
                continue        # встроенное вооружение (пулемёты, ловушки) — не подвеска, в массу не входит
            kg = 0.0
            for path, w in slot_weapons(pylons, index, choice):
                entry = by_path.get(weapon_key(path))
                m = _item_mass(source, path, w, entry if 'weapon' in choice else None)
                kg += m
                sm.items.append((index, path, m))
                count = (entry['bullets'] if 'weapon' in choice and entry else w.get('bullets') or 1)
                info = weapon_info(source, path)
                title = info['unit_title']
                gun = info['kind'] == 'gun'                 # у пушки bullets — патроны, а не штуки
                sm.counts[title] = sm.counts.get(title, 0) + (1 if gun else count * info['per'])
            sm.by_slot[index] = kg
            sm.total += kg
            side = None if s.no_disbalance else s.side
            if side == 'L':
                sm.left += kg
            elif side == 'R':
                sm.right += kg
            elif not s.no_disbalance:
                sm.unknown_side += kg
            _choice_warnings(source, pylons, s, choice, by_path, sm)
        _banned_warnings(pylons, lo, sm)
        _limit_warnings(pylons, sm)
        if sm.req_mods:
            sm.warnings.append(('info', 'В ангаре эти варианты требуют модификаций (%s) — в миссии копии это не '
                                        'проверяется, висеть будут.' % ', '.join(
                                            '%s: пилоны %s' % (m, ', '.join(map(str, i)))
                                            for m, i in sorted(sm.req_mods.items()))))
    elif pylons.scheme == 'legacy':
        weapons = legacy_weapons(source, pylons, lo.base) if lo.base else []
        if weapons is None:
            sm.warnings.append(('refuse', 'нет файла пресета %s' % lo.base))
            weapons = []
        for i, w in enumerate(weapons, 1):
            path = lo.legacy.get(i) or w.get('blk')
            if not path:
                continue
            m = _item_mass(source, path, w, by_path.get(weapon_key(path)) if i in lo.legacy else None)
            sm.items.append((i, path, m))
            sm.total += m
            info = weapon_info(source, path)
            sm.counts[info['unit_title']] = sm.counts.get(info['unit_title'], 0) + info['per']
        for i, path in sorted(lo.legacy.items()):
            if i > len(weapons):
                sm.warnings.append(('refuse', 'в пресете %s нет точки %d' % (lo.base, i)))
            elif not weapon_exists(source, path):
                sm.warnings.append(('refuse', 'нет файла оружия %s' % path))
            else:
                _kind_warning(source, path, weapons[i - 1].get('blk'), by_path, sm, 'точка %d' % i)
        if lo.legacy:
            sm.warnings.append(('info', 'Старая схема подвески: свой пресет — копия штатного «%s» с заменой оружия '
                                        'на точках (проверено в игре на A-20G, 19-й круг).' % lo.base))
    if lo.weightless:
        _weightless(source, pylons, sm)
    return sm


# наземное/морское оружие («орудия» ЗРК, танков, кораблей), которого нет у стоковой авиации. 32-й круг
# (round32_checklist.md): в наземном формате (cannon + bullet{rocket}) на пилоне F-15C игра падает при старте
# миссии (67, как 95Я6М 26.10); переделанная в авиационную ракету (rocketGun + блок rocket) ЗУР с ГСН пускается,
# захватывает и наводится (69). Поэтому ЗУР программа переделывает сама (air_rocket_text), остальное — «⚠»
RISKY_FOLDERS = ('groundmodels_weapons', 'navalmodels_weapons', 'human_weapons')
RISKY_TEXT = ('%s: наземное/морское оружие на пилоне — игра может упасть при старте миссии (32-й круг: '
              'ЗУР в наземном формате уронила игру).')
CONVERT_TEXT = ('%s: %s — ракета наземки/флота, переделана в авиационную (проверено в игре: ЗУР с ГСН и '
                'с наведением по командам пускаются, наводятся и видны на пилоне)')
# наведение, не проверенное с самолёта. saclos (по командам, как ПТУР) проверено 26.10 (v0.101): 95Я6М и 5В55
# (С-300) с F-15C пускаются, наводятся, видны на пилоне, у 5В55 после сброса раскрывается оперение
GROUND_GUIDANCE = {'sns': 'спутниковое'}
GUIDANCE_TEXT = '%s: наведение %s — на самолёте может не наводиться (не проверено в игре)'
AIR_COPY_DIR = 'gameData/Weapons/rocketGuns/'


def is_risky(entry):
    """Оружие каталога, которое на пилоне может уронить игру: наземное/морское, кроме ракет (их программа
    переделывает в авиационные, см. air_rocket_text)."""
    return (bool(entry) and entry.get('folder') in RISKY_FOLDERS and not entry.get('air')
            and entry.get('kind') != 'rocket')


def _ground_rocket(source, path):
    """Блок rocket ЗУР наземного формата (cannon + bullet{rocket}) или None."""
    tree = load_weapon(source, path)
    bullet = tree.block('bullet') if tree is not None and tree.block('rocket') is None else None
    return (tree, bullet.block('rocket')) if bullet is not None and bullet.block('rocket') is not None else None


def air_copy_path(path):
    """Путь авиационной ракеты, переделанной программой из ЗУР."""
    return '%s%s%s_air.blk' % (AIR_COPY_DIR, PREFIX, weapon_stem(path))


def air_rocket_text(source, path):
    """Текст авиационной ракеты из ЗУР наземного формата: rocketGun, 1 штука, mesh и блок rocket из bullet (как
    rocketGuns/us_aim_120c_5.blk; проверено в игре 32-м кругом, миссия 69). None — переделка не нужна."""
    if 'groundmodels_weapons/' not in weapon_key(path) and 'navalmodels_weapons/' not in weapon_key(path):
        return None
    found = _ground_rocket(source, path)
    if found is None:
        return None
    tree, rocket = found
    return ('// WT Poligon 5: %s переделана в авиационную ракету (rocketGun + rocket{} из bullet), 32-й круг\n'
            'rocketGun:b=yes\nbullets:i=1\nshotFreq:r=1.0\n%s%s' % (
                path, ''.join('%s:t=%s\n' % (k, B.quote(v)) for k, v in air_rocket_look(tree, rocket)),
                B.to_text(B.Block(None, blocks=[rocket]))))


def air_rocket_look(tree, rocket):
    """Вид ракеты для самолёта — поля верха файла, как у авиационных ракет. У наземной ЗУР они в блоке rocket
    или у пусковой: модель на пилоне (mesh; анимированная — animChar, как rocketGuns/us_127mm_tow.blk), модель
    в полёте (mesh_deployed, shellAnimChar — как su_kh_59m.blk). Без них 95Я6М на пилоне не видна, а летит
    моделью «ракета в контейнере» (пользователь, 32-й круг)."""
    out = [('mesh', rocket.get('mesh') or tree.get('mesh')),
           ('animChar', rocket.get('onPylonAnimChar') or rocket.get('animChar') or tree.get('animChar')),
           ('reloadAnimParam', tree.get('reloadAnimParam')),
           ('mesh_deployed', rocket.get('mesh_deployed') or tree.get('mesh_deployed')),
           ('shellAnimChar', rocket.get('shellAnimChar'))]
    return [(k, v) for k, v in out if isinstance(v, str) and v]


def pylon_weapon(source, path):
    """Путь оружия для подвеса: у ЗУР наземного формата — её авиационная переделка."""
    return air_copy_path(path) if air_rocket_text(source, path) is not None else path


def _kind_warning(source, path, sample_path, by_path, sm, where):
    new = weapon_kind(source, path)
    old = weapon_kind(source, sample_path) if sample_path else None
    entry = by_path.get(weapon_key(path))
    if is_risky(entry) or (entry is None and any('/%s/' % f in weapon_key(path) for f in RISKY_FOLDERS)
                           and new != 'rocket'):
        sm.warnings.append(('danger', RISKY_TEXT % where))
        return
    if air_rocket_text(source, path) is not None:
        sm.warnings.append(('info', CONVERT_TEXT % (where, weapon_title(source, path))))
        how = GROUND_GUIDANCE.get(_ground_rocket(source, path)[1].get('guidanceType'))
        if how:
            sm.warnings.append(('untested', GUIDANCE_TEXT % (where, how)))
    if old and new != old:
        sm.warnings.append(('untested', '%s: %s вместо «%s» — другой вид оружия на этой точке, триггер %s '
                                        '(не проверено в игре)' % (where, KIND_NAMES[new], KIND_NAMES[old],
                                                                    entry['trigger'] if entry else '?')))
    if entry is not None and not entry['air'] and air_rocket_text(source, path) is None:
        sm.warnings.append(('untested', '%s: %s не встречается на стоковой авиации (оружие наземки/флота) — '
                                        'триггер подобран по виду, не проверено в игре' % (
                                            where, weapon_title(source, path))))


def _choice_warnings(source, pylons, s, choice, by_path, sm):
    if 'variant' in choice:
        v = s.variant(choice['variant'])
        if v is None:
            sm.warnings.append(('refuse', 'пилон %d: нет варианта %s' % (s.index, choice['variant'])))
        elif v.req_mod:
            sm.req_mods.setdefault(v.req_mod, []).append(s.index)
        return
    if not weapon_exists(source, choice['weapon']):
        sm.warnings.append(('refuse', 'пилон %d: нет файла оружия %s' % (s.index, choice['weapon'])))
        return
    sample = s.variant(choice.get('sample')) or s.variants[0]
    if not sample.weapons:
        sm.warnings.append(('refuse', 'пилон %d: у варианта-образца %s нет точек подвеса' % (s.index, sample.name)))
        return
    _kind_warning(source, choice['weapon'], sample.weapons[0].get('blk'), by_path, sm, 'пилон %d' % s.index)


def _banned_warnings(pylons, lo, sm):
    chosen = {i: c.get('variant') for i, c in lo.slots.items() if 'variant' in c}
    for i, name in chosen.items():
        v = pylons.slot(i).variant(name) if pylons.slot(i) else None
        for slot, preset in (v.banned if v else []):
            if chosen.get(slot) == preset:
                sm.warnings.append(('info', 'пилоны %d и %d: в ангаре «%s» нельзя вместе с «%s» — в миссии игра это '
                                            'не проверяет, будет висеть оба (17-й круг)' % (i, slot, name, preset)))


def _limit_warnings(pylons, sm):
    lim = pylons.limits
    if lim.get('maxloadMass') and sm.total > lim['maxloadMass']:
        sm.warnings.append(('warn', 'Масса подвески %.0f кг больше допустимой %.0f кг. В миссии игра не запретит — '
                                    'самолёт будет тяжелее, хуже разгон и набор высоты (17-й круг); поможет '
                                    '«невесомая подвеска».' % (sm.total, lim['maxloadMass'])))
    for side, kg, key in (('левой', sm.left, 'maxloadMassLeftConsoles'), ('правой', sm.right,
                                                                           'maxloadMassRightConsoles')):
        if lim.get(key) and kg > lim[key]:
            sm.warnings.append(('warn', 'На %s консоли %.0f кг при допустимых %.0f кг (стороны — по именам '
                                        'вариантов, примерно).' % (side, kg, lim[key])))
    if lim.get('maxDisbalance') and abs(sm.left - sm.right) > lim['maxDisbalance']:
        sm.warnings.append(('warn', 'Перекос %.0f кг (слева %.0f, справа %.0f) больше допустимого %.0f кг: самолёт '
                                    'будет тянуть в тяжёлую сторону (17-й круг — «не сильно»).' % (
                                        abs(sm.left - sm.right), sm.left, sm.right, lim['maxDisbalance'])))
    if sm.unknown_side:
        sm.warnings.append(('info', '%.0f кг — на пилонах, сторона которых по файлам не ясна: перекос посчитан '
                                    'без них.' % sm.unknown_side))


def fm_tree(source, pylons):
    return source.load('gameData/flightModels/' + pylons.fm_file) if pylons.fm_file else None


def _weightless(source, pylons, sm):
    fm = fm_tree(source, pylons)
    mass = fm.block('Mass') if fm is not None else None
    empty = mass.get('EmptyMass') if mass is not None else None
    if not empty:
        sm.warnings.append(('refuse', 'Невесомая подвеска: в лётной модели нет Mass/EmptyMass — нечего '
                                      'компенсировать.'))
        return
    sm.empty_mass = empty
    rest = empty - sm.total
    if rest <= 0:
        sm.warnings.append(('refuse', 'Невесомая подвеска невозможна: подвеска (%.0f кг) тяжелее пустого самолёта '
                                      '(%.0f кг).' % (sm.total, empty)))
        return
    sm.weightless_mass = round(rest, 1)
    if rest < 0.09 * empty:
        sm.warnings.append(('untested', 'Невесомая подвеска: пустой планер станет %.0f кг — меньше 9 %% от '
                                        'штатного; так в игре не проверялось.' % rest))
    if mass.get('AdvancedMass'):
        sm.warnings.append(('untested', 'Невесомая подвеска: у этой лётной модели AdvancedMass=yes — не проверено '
                                        'в игре.'))
    sm.warnings.append(('info', 'Невесомая подвеска: летит примерно как пустой; после сброса/пуска всего — легче '
                                'пустого на %.0f кг; инерция и центровка от подвески не компенсируются; лёгкий планер '
                                'быстрее выходит на перегрузку (круг 31).' % sm.total))


WEIGHTLESS_HINT = ('Невесомая подвеска: программа вычтет массу подвески из пустой массы самолёта (копия лётной '
                   'модели). До сброса самолёт летит примерно как пустой; после сброса или пуска всего — легче '
                   'пустого на массу подвески, быстрее разгоняется и легче выходит на перегрузку. Баллистика и урон '
                   'боеприпасов не меняются. Проверено в игре (A-26B с ФАБ-9000, круги 19–20 и 31).')


# ---------------------------------------------------------------- сборка: файлы копии

def _safe(text):
    return re.sub(r'[^a-z0-9_]+', '_', (text or '').lower()).strip('_')[:40] or 'custom'


def variant_name(index, choice):
    """Имя своего варианта слота: wtp5_s<слот>_<оружие>[_x<точек>]."""
    return '%ss%d_%s%s' % (PREFIX, index, _safe(weapon_stem(choice['weapon'])),
                           '_x%d' % choice['count'] if choice.get('count') else '')


def preset_name(lo):
    """Имя своего пресета в копии (одна подвеска на копию; имя пользователя — только в библиотеке)."""
    return PREFIX + 'loadout'


def build_files(source, pylons, lo, unit_class, catalog=None):
    """Своя подвеска для копии unit_class: ([(путь от папки игры, текст)], текст правок файла копии,
    имя пресета для миссии, проблемы). Новые варианты слотов — копии образцов (17-й круг)."""
    by_path = {weapon_key(w['path']): w for w in (catalog or [])}
    problems = [t for lvl, t in summarize(source, pylons, lo, catalog).warnings if lvl == 'refuse']
    if problems:
        return [], '', '', problems
    pname = preset_name(lo)
    files, unit_text = [], ''
    ppath = 'gameData/FlightModels/weaponPresets/%s_%s.blk' % (unit_class, pname[len(PREFIX):])
    head = '// WT Poligon 5: своя подвеска %s (конструктор подвески, pylons_survey.md)\n' % pname
    if pylons.scheme == 'slots':
        by_n, pairs = {}, []
        for index, choice in sorted(lo.slots.items()):
            s = pylons.slot(index)
            if 'variant' in choice:
                pairs.append((index, choice['variant']))
                continue
            sample = s.variant(choice.get('sample')) or s.variants[0]
            new = variant_name(index, choice)
            entry = by_path.get(weapon_key(choice['weapon']))
            v = B._clone(sample.block)
            v.params = [('name', 't', new) if k == 'name' else (k, t, x) for k, t, x in v.params
                        if k != 'reqModification']
            v.blocks = [b for b in v.blocks if b.name not in ('BannedWeaponPreset', 'DependentWeaponPreset')]
            if choice.get('count'):     # оставить первые count точек образца
                drop = [i for i, b in enumerate(v.blocks) if b.name == 'Weapon'][choice['count']:]
                v.blocks = [b for i, b in enumerate(v.blocks) if i not in drop]
            same_kind = (weapon_kind(source, choice['weapon'])
                         == weapon_kind(source, sample.weapons[0].get('blk')))
            for w in v.blocks:
                if w.name != 'Weapon':
                    continue
                params = []
                for k, t, x in w.params:
                    if k == 'blk':
                        x = pylon_weapon(source, choice['weapon'])
                    elif k == 'mass':       # масса установки образца — не нашего оружия
                        continue
                    elif k == 'trigger' and entry is not None and not same_kind:
                        x = entry['trigger']
                    elif k == 'bullets' and entry is not None and not same_kind:
                        x = entry['bullets']
                    params.append((k, t, x))
                w.params = params
            by_n.setdefault(s.n, []).append(B.to_text(B.Block(None, blocks=[v])))
            pairs.append((index, new))
        if by_n:
            unit_text += '"@override:WeaponSlots"{\n' + ''.join(
                '"@override:WeaponSlot[%d]"{\n%s}\n' % (n, ''.join(t)) for n, t in sorted(by_n.items())) + '}\n'
        files.append((PKG + ppath, head + ''.join('Weapon{\n  slot:i=%d\n  preset:t=%s\n}\n' % (i, B.quote(p))
                                                  for i, p in pairs)))
    else:
        stock = pylons.preset_file(lo.base)
        patch = ''.join('"@override:Weapon[%d]"{\n  "@override:blk":t=%s\n}\n' % (
            i, B.quote(pylon_weapon(source, p))) for i, p in sorted(lo.legacy.items()))
        files.append((PKG + ppath, head + 'include "#/develop/gameBase/%s"\n%s' % (stock, patch)))
    chosen = [c['weapon'] for c in lo.slots.values() if 'weapon' in c] if pylons.scheme == 'slots' else \
        list(lo.legacy.values())
    for path in sorted(set(chosen), key=weapon_key):         # ЗУР наземного формата — авиационная переделка
        text = air_rocket_text(source, path)
        if text is not None:
            files.append((PKG + air_copy_path(path), text))
    unit_text += '"@override:weapon_presets"{\npreset{\n  name:t=%s\n  blk:t=%s\n}\n}\n' % (
        B.quote(pname), B.quote(ppath))
    if lo.weightless:
        sm = summarize(source, pylons, lo, catalog)
        fm_copy = 'fm/%s.blk' % unit_class
        fm_stock = 'gameData/flightModels/' + pylons.fm_file
        files.append(('%sgameData/flightModels/%s' % (PKG, fm_copy),
                      '// WT Poligon 5: невесомая подвеска — EmptyMass %.1f − подвеска %.1f кг\n'
                      'include "#/develop/gameBase/%s"\n"@override:Mass"{\n  "@override:EmptyMass":r=%r\n}\n' % (
                          sm.empty_mass, sm.total, fm_stock, sm.weightless_mass)))
        unit_text += '"@override:fmFile":t=%s\n' % B.quote(fm_copy)
    return files, unit_text, pname, []


def check_resolved(unit, pylons, lo, pname, unit_class):
    """Сверка итогового дерева копии (после модели правок): пресет есть, свои варианты — в своих слотах."""
    out = []
    wp = unit.block('weapon_presets')
    if not any(p.get('name') == pname for p in (wp.blocks if wp else [])):
        out.append('в копии нет пресета %s' % pname)
    if pylons.scheme == 'slots':
        ws = unit.block('WeaponSlots')
        slots = {s.get('index'): s for s in (ws.blocks if ws else []) if s.name == 'WeaponSlot'}
        for index, choice in lo.slots.items():
            if 'weapon' in choice:
                name = variant_name(index, choice)
                s = slots.get(index)
                v = next((p for p in (s.blocks if s else []) if p.get('name') == name), None)
                if v is None:
                    out.append('в слоте %d копии нет варианта %s' % (index, name))
                elif any(weapon_key(w.get('blk')) not in (weapon_key(choice['weapon']),
                                                          weapon_key(air_copy_path(choice['weapon'])))
                         for w in v.blocks if w.name == 'Weapon'):
                    out.append('вариант %s: оружие не %s' % (name, choice['weapon']))
    if lo.weightless and unit.get('fmFile') != 'fm/%s.blk' % unit_class:
        out.append('копия не ссылается на свою лётную модель')
    return out


# ---------------------------------------------------------------- библиотека своих пресетов (architecture.md §10.4)

LIBRARY = 'loadouts.json'


def library_load(app_root):
    try:
        with open(os.path.join(app_root, LIBRARY), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def library_names(app_root, unit):
    return sorted(library_load(app_root).get(unit.lower(), {}))


def library_get(app_root, unit, name):
    d = library_load(app_root).get(unit.lower(), {}).get(name)
    return Loadout.from_dict(d) if d else None


def library_save(app_root, unit, lo):
    if not lo.name.strip():
        raise ValueError('у пресета нет имени')
    lib = library_load(app_root)
    lib.setdefault(unit.lower(), {})[lo.name] = lo.to_dict()
    _library_write(app_root, lib)


def library_delete(app_root, unit, name):
    lib = library_load(app_root)
    if lib.get(unit.lower(), {}).pop(name, None) is not None:
        _library_write(app_root, lib)
        return True
    return False


def _library_write(app_root, lib):
    os.makedirs(app_root, exist_ok=True)
    path = os.path.join(app_root, LIBRARY)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(lib, f, ensure_ascii=False, indent=1)
    os.replace(path + '.tmp', path)
