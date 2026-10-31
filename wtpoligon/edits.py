"""Модель правок (docs/architecture.md §4), минимально для этапа 1: правка = путь, тип из стока, значение, источник.

Редактора ещё нет; на этот слой встаёт этап 3 (конструктор подвески). Текст правок — правила override_format.md,
проверенные в игре генератором tools/make_test_missions.py (override_path, merge_overrides, unit_edits).
Путь — 'блок/…/параметр', повтор одноимённых — '[n]' с 1 (без индекса — первый).
"""
from dataclasses import asdict, dataclass

from .game import blk as B

SOURCES = ('manual', 'derived', 'rule')


@dataclass
class Edit:
    file: str            # стоковый файл: 'gameData/units/tankModels/ussr_t_80bvm.blk'
    path: str            # 'VehiclePhys/mechanics/gearRatios/ratio[11]'
    type: str            # тип BLK из стока: r, i, i64, b, t, p2..p4, ip2..ip4, m, c
    stock: object        # стоковое значение; None — параметра в стоке нет
    value: object        # новое значение
    source: str = 'manual'   # manual | derived:<общий показатель> | rule:<правило>
    note: str = ''           # для сводки «что изменится»

    def __post_init__(self):
        if self.source.split(':', 1)[0] not in SOURCES:
            raise ValueError('неизвестный источник правки: %r' % self.source)
        self.value = coerce(self.type, self.value)

    def to_dict(self):
        d = asdict(self)
        for k in ('stock', 'value'):
            if isinstance(d[k], tuple):
                d[k] = [list(x) if isinstance(x, tuple) else x for x in d[k]]
        return d

    @classmethod
    def from_dict(cls, d):
        e = cls(**d)
        if e.stock is not None:
            e.stock = coerce(e.type, e.stock)
        return e


def coerce(t, v):
    """Значение к типу BLK (как его хранит Block): r — float, i/i64 — int, b — bool, t — str, p/ip — кортежи."""
    if t == 'r':
        if isinstance(v, (bool, str)):
            raise TypeError('ожидалось число, а не %r' % (v,))
        return float(v)
    if t in ('i', 'i64'):
        if isinstance(v, (bool, str)) or (isinstance(v, float) and not v.is_integer()):
            raise TypeError('ожидалось целое, а не %r' % (v,))
        return int(v)
    if t == 'b':
        if not isinstance(v, bool):
            raise TypeError('ожидалось да/нет, а не %r' % (v,))
        return v
    if t == 't':
        if not isinstance(v, str):
            raise TypeError('ожидалась строка, а не %r' % (v,))
        return v
    if t in ('p2', 'p3', 'p4', 'ip2', 'ip3', 'ip4'):
        n = int(t[-1])
        if len(v) != n:
            raise TypeError('ожидалось %d числа, а не %r' % (n, v))
        return tuple((int if t.startswith('i') else float)(x) for x in v)
    if t == 'm':
        return tuple(tuple(float(x) for x in row) for row in v)
    if t == 'c':
        return tuple(int(x) for x in v)
    raise TypeError('неизвестный тип BLK: %r' % t)


def stock_param(tree, path):
    """(тип, значение) параметра по пути или None."""
    *blocks, param = path.split('/')
    node = tree
    for part in blocks:
        name, n = _path_part(part)
        same = [b for b in node.blocks if b.name == name]
        if len(same) < (n or 1):
            return None
        node = same[(n or 1) - 1]
    name, n = _path_part(param)
    found = [p for p in node.params if p[0] == name]
    return tuple(found[(n or 1) - 1][1:]) if len(found) >= (n or 1) else None


def make_edit(tree, file, path, value, source='manual', note=''):
    """Правка существующего параметра: тип и сток — из дерева стокового файла. Нет параметра — KeyError."""
    got = stock_param(tree, path)
    if got is None:
        raise KeyError('нет параметра %s в %s' % (path, file))
    return Edit(file, path, got[0], got[1], value, source, note)


def edits_text(tree, edits):
    """Правки одного файла -> (текст @override, проблемы). Тип и сток сверяются с деревом (после обновления игры
    сток мог измениться — такую правку не пишем)."""
    texts, problems = [], []
    for e in edits:
        got = stock_param(tree, e.path)
        if got is None:
            problems.append('%s: нет параметра %s' % (e.file, e.path))
            continue
        typ, old = got
        if typ != e.type:
            problems.append('%s: %s — в стоке тип %s, в правке %s' % (e.file, e.path, typ, e.type))
            continue
        same = (abs(old - e.stock) <= 1e-6 * max(1.0, abs(e.stock))
                if isinstance(old, float) and isinstance(e.stock, (int, float)) else old == e.stock)
        if not same:
            problems.append('%s: %s — в стоке %r, в правке записано %r' % (e.file, e.path, old, e.stock))
            continue
        texts.append(override_path(tree, e.path, e.value))
    return merge_overrides(texts), problems


def by_file(edits):
    """{файл: [правки]} в порядке первого появления."""
    out = {}
    for e in edits:
        out.setdefault(e.file, []).append(e)
    return out


# ---------------------------------------------------------------- текст правок (перенесено из генератора)

def _path_part(part):
    """'ratio[13]' -> ('ratio', 13); без индекса -> (имя, None)."""
    if part.endswith(']') and '[' in part:
        name, n = part[:-1].split('[')
        return name, int(n)
    return part, None


def override_path(tree, path, value):
    """Правка существующего параметра по пути 'блок/…/параметр' (override_format.md п. 2): тип — как в стоке,
    [n] — когда одноимённых больше одного (без индекса в пути — первый). Индекс в пути ('ratio[13]', с 1) выбирает
    n-й из одноимённых и пишется всегда. Возвращает текст или бросает KeyError."""
    *blocks, param = path.split('/')
    lines, node = [], tree
    for depth, part in enumerate(blocks):
        name, n = _path_part(part)
        same = [b for b in node.blocks if b.name == name]
        if not same or (n or 1) > len(same):
            raise KeyError('нет блока %s в %s' % (part, path))
        lines.append('  ' * depth + '"@override:%s%s"{' % (name, '[%d]' % (n or 1) if n or len(same) > 1 else ''))
        node = same[(n or 1) - 1]
    param, n = _path_part(param)
    found = [p for p in node.params if p[0] == param]
    if not found or (n or 1) > len(found):
        raise KeyError('нет параметра %s' % path)
    typ, old = found[(n or 1) - 1][1:]
    # составные типы (p2…, m, c) — fmt_value; скаляры — как в проверенных кругах (repr числа того же типа)
    val = (B.quote(value) if typ == 't' else ('yes' if value else 'no') if typ == 'b'
           else B.fmt_value(typ, value) if isinstance(old, tuple) else repr(type(old)(value)))
    lines.append('  ' * len(blocks) + '"@override:%s%s":%s=%s' % (
        param, '[%d]' % (n or 1) if n or len(found) > 1 else '', typ, val))
    lines += ['  ' * d + '}' for d in reversed(range(len(blocks)))]
    return '\n'.join(lines) + '\n'


def merge_overrides(texts):
    """Тексты override_path одним деревом: правки с общим началом пути — в одном блоке "@override:…"{} (порядок
    первого появления сохраняется), а не отдельными блоками подряд, как четыре ссылки на ракеты в 29-м круге."""
    root = {}
    for text in texts:
        lines = [x.strip() for x in text.splitlines()]
        heads = [x for x in lines if x.endswith('{')]
        node = root
        for h in heads:
            node = node.setdefault(h, {})
        node[lines[len(heads)]] = None

    def dump(node, depth):
        out = []
        for line, sub in node.items():
            out.append('  ' * depth + line)
            if sub is not None:
                out += dump(sub, depth + 1) + ['  ' * depth + '}']
        return out
    return ''.join(x + '\n' for x in dump(root, 0))


def path_value(tree, path):
    """Значение по пути override_path ('блок/…/параметр[n]') или None."""
    *blocks, param = path.split('/')
    node = tree
    for part in blocks:
        name, n = _path_part(part)
        same = [b for b in node.blocks if b.name == name] if node else []
        node = same[(n or 1) - 1] if len(same) >= (n or 1) else None
    if node is None:
        return None
    name, n = _path_part(param)
    found = [p[2] for p in node.params if p[0] == name]
    return found[(n or 1) - 1] if len(found) >= (n or 1) else None


def set_path_value(tree, path, value):
    """Записать значение по пути path_value в дерево (для эталона сверки)."""
    *blocks, param = path.split('/')
    node = tree
    for part in blocks:
        name, n = _path_part(part)
        node = [b for b in node.blocks if b.name == name][(n or 1) - 1]
    name, n = _path_part(param)
    i = [k for k, p in enumerate(node.params) if p[0] == name][(n or 1) - 1]
    node.params[i] = (name, node.params[i][1], value)


def unit_edits(u, edits):
    """Правки файла машины по unit_edits: (текст правок, проблемы). Стоковое значение должно совпасть с ожидаемым."""
    texts, problems = [], []
    for path, stock, new in edits:
        got = path_value(u, path)
        # бинарный BLK хранит float32 (0.687 → 0.68699997…), датамайн — округлённый текст: сравнивать с допуском
        same = (abs(got - stock) <= 1e-6 * max(1.0, abs(stock))
                if isinstance(got, float) and isinstance(stock, (int, float)) else got == stock)
        if not same:
            problems.append('%s: в стоке %r, ожидалось %r' % (path, got, stock))
            continue
        try:
            texts.append(override_path(u, path, new))
        except KeyError as e:
            problems.append(str(e))
    return merge_overrides(texts), problems
