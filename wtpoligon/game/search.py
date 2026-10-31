"""Поиск техники «как напечатал»: с опечатками, без дефисов и пробелов, русскими или латинскими буквами.

Примеры: «т80бмв» → Т-80БВМ (переставлены буквы), «ф15с» / «f15c» → F-15C, «абрамс» → M1 Abrams.
Каждая машина даёт несколько ключей (внутреннее имя с префиксом страны и без, английское и русское названия), все
приводятся к латинице без знаков: по звучанию (ф→f, в→v) и по похожему начертанию (с→c, в→b, р→p). Запрос
приводится так же; совпадение — начало ключа, подстрока или нечёткое (rapidfuzz partial_ratio, если установлен).
"""
import re

try:
    from rapidfuzz import fuzz, process
except ImportError:          # без rapidfuzz — только точные подстроки
    fuzz = process = None

PHONETIC = dict(zip('абвгдезийклмнопрстуфхцчшщъыьэюяё',
                    ['a', 'b', 'v', 'g', 'd', 'e', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't', 'u',
                     'f', 'h', 'ts', 'ch', 'sh', 'sch', '', 'y', '', 'e', 'yu', 'ya', 'e']))
PHONETIC['ж'] = 'zh'
# буквы, которые выглядят как латинские (набрал «с» вместо «c» на русской раскладке)
LOOKALIKE = dict(PHONETIC, **{'с': 'c', 'в': 'b', 'р': 'p', 'х': 'x', 'н': 'h', 'у': 'y', 'и': 'u', 'п': 'n',
                             'ц': 'c'})
COUNTRY_PREFIX = re.compile(r'^(ussr|germ|us|uk|jp|cn|it|fr|sw|il|ger|br|sweden|china|japan|italy|france|'
                            r'israel|britain|germany|usa)_')
MIN_FUZZY = 80          # порог нечёткого совпадения (0–100)


def norm(text):
    """Нижний регистр, ё→е, только буквы и цифры."""
    return re.sub(r'[\W_]+', '', (text or '').lower().replace('ё', 'е'))


def latin(text, table):
    return ''.join(table.get(ch, ch) for ch in text)


def forms(text):
    """Латинские формы строки: по звучанию и по начертанию (без повторов)."""
    n = norm(text)
    out = []
    for f in (latin(n, PHONETIC), latin(n, LOOKALIKE)):
        if f and f not in out:
            out.append(f)
    return out


def vehicle_keys(v):
    keys = []
    for text in (v['name'], COUNTRY_PREFIX.sub('', v['name'].lower()), v.get('en'), v.get('ru')):
        for f in forms(text):
            if f not in keys:
                keys.append(f)
    return keys


def weapon_keys(w):
    """Ключи оружия каталога (loadout.build_catalog): имя файла (и без префикса страны), русское и английское."""
    keys = []
    for text in (w['stem'], COUNTRY_PREFIX.sub('', w['stem']), w.get('ru'), w.get('en')):
        for f in forms(text):
            if f not in keys:
                keys.append(f)
    return keys


class Searcher:
    """Индекс ключей по списку (машины или оружие; строится один раз). keys_fn(элемент) -> [ключи]."""

    def __init__(self, items, keys_fn=None, label=None):
        self.vehicles = self.items = items
        self.label = label or (lambda x: x.get('ru') or x['name'])
        self.keys, self.owner = [], []
        for i, v in enumerate(items):
            for k in (keys_fn or vehicle_keys)(v):
                self.keys.append(k)
                self.owner.append(i)

    def scores(self, text):
        """{номер: оценка 0–100}: 100 — точное совпадение, 98 — ключ начинается с запроса, 95 — содержит
        его, до 94 — нечёткое."""
        best = {}
        for q in forms(text):
            for k, i in zip(self.keys, self.owner):
                s = 100 if k == q else 98 if k.startswith(q) else 95 if q in k else 0
                if s > best.get(i, 0):
                    best[i] = s
            if process is not None and len(q) >= 3:
                for k, s, j in process.extract(q, self.keys, scorer=fuzz.partial_ratio, score_cutoff=MIN_FUZZY,
                                               limit=None):
                    if len(k) < len(q):         # ключ короче запроса («т80» в «т80бмв») — сравнивать целиком
                        s = fuzz.ratio(q, k)
                        if s < MIN_FUZZY:
                            continue
                    i = self.owner[j]
                    s = min(s, 94)              # нечёткое — ниже точной подстроки
                    if s > best.get(i, 0):
                        best[i] = s
        return best

    def search(self, text):
        """[(элемент, оценка)] по убыванию оценки; при равной — короче название (точнее совпадение)."""
        sc = self.scores(text)
        order = sorted(sc, key=lambda i: (-sc[i], len(self.label(self.items[i]) or ''), str(self.label(
            self.items[i]))))
        return [(self.items[i], sc[i]) for i in order]


_CACHE = {}


def searcher(items, keys_fn=None, label=None):
    key = (id(items), keys_fn)
    if key not in _CACHE or _CACHE[key].items is not items:
        _CACHE[key] = Searcher(items, keys_fn, label)
    return _CACHE[key]
