"""Детерминированный подбор с сохранением уже выбранных машин при изменении количества."""
import random

from .catalog import CATEGORIES, candidates, eligible
from .model import Target


def refill(scenario, vehicles, category, seed=0, reroll=False):
    cat = scenario.categories[category]
    rng = random.Random('%s:%s:%s:%s' % (seed, scenario.mode, category, scenario.player))
    items = [] if reroll else [Target(t.vehicle, t.count) for t in cat.targets if t.count > 0]
    while sum(t.count for t in items) > cat.count:
        items[-1].count -= 1
        if not items[-1].count:
            items.pop()
    br = scenario.player_br or next((v.get('br') for v in vehicles if v['name'] == scenario.player), None) or 5.0
    pool = candidates(vehicles, category, scenario.mode, br, (cat.br_min, cat.br_max), scenario.player)
    if not pool:
        pool = sorted((v for v in vehicles if v.get('br') is not None and eligible(v, category, scenario.mode)
                       and v['name'] != scenario.player), key=lambda v: (abs(v['br'] - br), v['name']))[:max(10, cat.count * 3)]
    pool = sorted((v for v in pool if v['name'] not in {t.vehicle for t in items}), key=lambda v: v['name'])
    rng.shuffle(pool)
    while sum(t.count for t in items) < cat.count and pool:
        items.append(Target(pool.pop()['name']))
    if items and sum(t.count for t in items) < cat.count:
        items[-1].count += cat.count - sum(t.count for t in items)
    cat.targets = items
    return items


def refill_all(scenario, vehicles, seed=0, reroll=True):
    for key, _, _ in CATEGORIES[scenario.mode]:
        refill(scenario, vehicles, key, seed, reroll)
    return scenario


def add(scenario, category, vehicle):
    cat = scenario.categories[category]
    match = next((t for t in cat.targets if t.vehicle == vehicle), None)
    if match:
        match.count += 1
    else:
        cat.targets.append(Target(vehicle))
    cat.count = cat.total()


def remove(scenario, category, index):
    cat = scenario.categories[category]
    cat.targets.pop(index)
    cat.count = cat.total()
