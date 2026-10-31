"""Индекс всей техники игры: наземка, авиация, вертолёты, флот (ТЗ §6.1, §6.6 — выбирается вся техника).

Реестр — char.vromfs config/unittags.blk (тип машины и теги; игра сама читает его, лог: updateAllUnits 3509),
страна/ранг/БР — config/wpcost.blk, названия — lang/units.csv (<имя>_shop, иначе <имя>_0). Файл машины —
aces.vromfs gameData/<папка>/<имя>.blk; машины без файла в индекс не входят (их не собрать), их число — в stats.
Кэш — JSON в <папка программы>/cache, ключ — signature() источника (версия и размеры архивов игры).
"""
import csv
import io
import json
import os
import unicodedata

from ..mission import KINDS

INDEX_VERSION = 4
# тип в unittags -> вид техники программы (KINDS); 'human' (пехота) — не техника
KIND_BY_TYPE = {'aircraft': 'air', 'helicopter': 'heli', 'tank': 'tank', 'ship': 'ship'}
KIND_NAMES = {'tank': 'наземная', 'air': 'самолёт', 'heli': 'вертолёт', 'ship': 'флот'}


def unit_file(kind, name):
    """Путь файла машины в игре (как в include копии): gameData/<папка>/<имя в нижнем регистре>.blk."""
    return 'gameData/%s/%s.blk' % (KINDS[kind][1], name.lower())


def battle_rating(economic_rank):
    """БР по economicRank* из wpcost: 1.0 + ранг / 3 (шаг 0.3/0.7)."""
    return round(1.0 + economic_rank / 3.0, 1) if isinstance(economic_rank, int) else None


def clean_name(text):
    """Название без значков шрифта игры (␙, ▄, ◄ … — знаки премиума, наборов и т.п. в units.csv)."""
    out = ''.join(ch for ch in (text or '') if unicodedata.category(ch)[0] in 'LNPZ' or ch in '×+')
    return ' '.join(out.split())


def vehicle_marks(name, cost):
    """Пометки для различения одноимённых машин (wpcost): «премиум», «подарок», «событие», «скрытая»."""
    out = []
    if cost is not None and cost.get('costGold'):
        out.append('премиум')
    if cost is not None and cost.get('gift'):
        out.append('подарок')
    if (cost is not None and cost.get('event')) or name.lower().endswith('_event'):
        out.append('событие')
    if cost is not None and cost.get('showOnlyWhenBought'):
        out.append('скрытая')
    return out


def read_names(csv_text):
    """{ключ: (английский, русский)} из units.csv."""
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
        if len(row) > max(en, ru):
            out[row[0]] = (clean_name(row[en]), clean_name(row[ru]))
    return out


def build_index(source):
    """(машины, статистика). Машина: name, kind, type, file, country, rank, br, en, ru, shop."""
    tags = source.config('unittags')
    if tags is None:
        raise FileNotFoundError('нет config/unittags.blk в ' + source.describe())
    cost = source.config('wpcost')
    costs = {b.name: b for b in cost.blocks} if cost is not None else {}
    names = read_names(source.lang_csv('units'))
    vehicles, stats, seen = [], {'skipped_type': 0, 'no_file': [], 'duplicate': []}, set()
    for b in tags.blocks:
        kind = KIND_BY_TYPE.get(b.get('type'))
        if kind is None:
            stats['skipped_type'] += 1
            continue
        path = unit_file(kind, b.name)
        if path.lower() in seen:
            stats['duplicate'].append(b.name)
            continue
        if not source.exists(path):
            stats['no_file'].append(b.name)
            continue
        seen.add(path.lower())
        w = costs.get(b.name)
        tag_block = b.block('tags')
        country = (w.get('country') if w is not None else None) or next(
            (k for k, _t, v in (tag_block.params if tag_block else []) if k.startswith('country_') and v), None)
        en, ru = names.get(b.name + '_shop') or names.get(b.name + '_0') or ('', '')
        vehicles.append({
            'name': b.name, 'kind': kind, 'type': b.get('type'), 'file': path,
            'tags': [k for k, _t, value in (tag_block.params if tag_block else []) if value],
            'country': (country or '').replace('country_', '') or None,
            'rank': w.get('rank') if w is not None else None,
            'br': battle_rating(w.get('economicRankHistorical')) if w is not None else None,
            'en': en, 'ru': ru, 'shop': w is not None, 'marks': vehicle_marks(b.name, w),
        })
    order = list(KINDS)
    vehicles.sort(key=lambda v: (order.index(v['kind']), v['country'] or '~', v['rank'] or 99, v['name'].lower()))
    stats['count'] = len(vehicles)
    return vehicles, stats


def load_index(source, cache_dir, refresh=False):
    """Индекс из кэша, если подпись источника та же; иначе собрать и сохранить. (машины, статистика)."""
    sig = source.signature()
    path = os.path.join(cache_dir, 'index_%s.json' % source.kind)
    if not refresh and os.path.isfile(path):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            if data.get('signature') == sig and data.get('version') == INDEX_VERSION:
                return data['vehicles'], data['stats']
        except (OSError, ValueError, KeyError):
            pass
    vehicles, stats = build_index(source)
    os.makedirs(cache_dir, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'version': INDEX_VERSION, 'signature': sig, 'vehicles': vehicles, 'stats': stats}, f,
                  ensure_ascii=False)
    os.replace(tmp, path)
    return vehicles, stats


def find(vehicles, query):
    """Машина по точному внутреннему имени (без учёта регистра) или None."""
    q = (query or '').lower()
    return next((v for v in vehicles if v['name'].lower() == q), None)


def search(vehicles, text='', kind=None, country=None):
    """Машины по виду и стране; с текстом — по убыванию совпадения, с опечатками и в любой раскладке
    (game/search.py: «т80бмв», «ф15с», «f15c»). Без текста — в исходном порядке."""
    return [v for v, _s in search_scored(vehicles, text, kind, country)]


def search_scored(vehicles, text='', kind=None, country=None):
    """[(машина, оценка 0–100)] — как search; без текста оценка 100."""
    from .search import searcher
    pool = searcher(vehicles).search(text) if norm_text(text) else [(v, 100) for v in vehicles]
    return [(v, s) for v, s in pool if (not kind or v['kind'] == kind)
            and (not country or (v['country'] or '') == country)]


def norm_text(text):
    from .search import norm
    return norm(text)
