"""Поиск подходящих машин для вызова."""
from .model import Support
from ..game import search as S


def candidates(vehicles, support: Support, library=(), query='', category='all'):
    used = {(e.library_id or e.vehicle): e.kind for e in support.entries}
    q = query.strip()
    out = []
    for v in vehicles:
        if v['kind'] == 'ship':
            continue
        kind = 'air' if v['kind'] in ('air', 'heli') else 'ground'
        if category not in ('all', kind):
            continue
        if used.get(v['name'], kind) != kind:
            continue
        if S.matches(q, *(v.get(k) for k in ('ru', 'en', 'name'))):
            out.append((v['name'], v.get('ru') or v.get('en') or v['name'], kind, ''))
    for item in library:
        kind = 'air' if item['kind'] in ('air', 'heli') else 'ground'
        if category not in ('all', 'mine', kind) or used.get(item['id'], kind) != kind:
            continue
        if S.matches(q, item['name'], item['vehicle']):
            out.append((item['vehicle'], item['name'], kind, item['id']))
    return out
