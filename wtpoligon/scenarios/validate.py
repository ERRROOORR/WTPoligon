"""Проверка модели и пометки игровой проверки из §27."""
from .catalog import CATEGORIES, eligible, vehicle_map

VERIFIED = {'ground_distances': {0, 300, 1200, 2000}, 'bot_distances': {3000, 10000, 30000},
            'radar': True, 'hold_fire': True}


def check(scenario, vehicles):
    out = []
    if scenario.mode not in CATEGORIES:
        return ['неизвестный режим']
    known = vehicle_map(vehicles)
    if scenario.player and scenario.player not in known:
        out.append('нет машины игрока %s в игре' % scenario.player)
    for key, _, _ in CATEGORIES[scenario.mode]:
        cat = scenario.categories[key]
        if not 0 <= cat.count <= 20 or cat.total() != cat.count:
            out.append('%s: количество не совпадает со списком' % key)
        if cat.br_min > cat.br_max:
            out.append('%s: диапазон БР перевёрнут' % key)
        if not 0 <= cat.distance <= 200000:
            out.append('%s: дистанция вне пределов' % key)
        for target in cat.targets:
            v = known.get(target.vehicle)
            if v is None:
                out.append('%s: нет машины %s в игре' % (key, target.vehicle))
            elif not eligible(v, key, scenario.mode):
                out.append('%s: неверный класс %s' % (key, target.vehicle))
            if not 1 <= target.count <= 20:
                out.append('%s: неверная кратность' % key)
    if scenario.mode == 'duel' and scenario.duel.enemy not in known:
        out.append('не выбран противник')
    return out


def status(option, value=None):
    if option == 'distance_ground' and value in VERIFIED['ground_distances']:
        return 'проверено в игре'
    if option == 'distance_bot' and value in VERIFIED['bot_distances']:
        return 'проверено в игре'
    if option in ('radar', 'hold_fire'):
        return 'проверено в игре'
    return 'не проверено'
