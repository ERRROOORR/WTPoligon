"""Категории как TCATS в исходники/ui.html 4.7; типы — config/unittags.blk через game.index."""
from .model import DEFAULT_RANGES

CATEGORIES = {
    'air': [('air', 'Самолёты на кругах', 'Летают по кругам на разных высотах и скоростях'),
            ('fighters', 'Истребители', 'Летят к вам и крутят бой'), ('heli', 'Вертолёты', ''),
            ('ground', 'Наземные цели', ''), ('spaa', 'ЗСУ / ЗРК', ''), ('ships', 'Корабли', '')],
    'ground': [('ground', 'Танки и техника', ''), ('spaa', 'ЗСУ / ЗРК', ''),
               ('air', 'Самолёты', ''), ('heli', 'Вертолёты', '')],
    'naval': [('ships', 'Корабли и катера', 'Ближе — катера, дальше — крупные корабли'),
              ('air', 'Самолёты', '')],
    'duel': [],
}
CATEGORIES['heli'] = CATEGORIES['air']
FIGHTER_TYPES = {'type_fighter', 'type_interceptor', 'type_light_fighter'}
TANK_TYPES = {'type_medium_tank', 'type_heavy_tank', 'type_light_tank', 'type_tank_destroyer'}
SHIP_TYPES = {'type_destroyer', 'type_light_cruiser', 'type_frigate'}


def eligible(vehicle, category, mode='air'):
    kind, vtype = vehicle.get('kind'), vehicle.get('type')
    tags = set(vehicle.get('tags') or ())
    return {'air': lambda: kind == 'air',
            'fighters': lambda: kind == 'air' and bool(tags & FIGHTER_TYPES or vtype in FIGHTER_TYPES),
            'heli': lambda: kind == 'heli',
            'ground': lambda: kind == 'tank' and bool(tags & TANK_TYPES or vtype in TANK_TYPES),
            'spaa': lambda: kind == 'tank' and ('type_spaa' in tags or vtype == 'type_spaa'),
            'ships': lambda: kind == 'ship' and (mode == 'naval' or bool(tags & SHIP_TYPES or vtype in SHIP_TYPES))}[category]()


def candidates(vehicles, category, mode, player_br, spread=None, player=''):
    lo, hi = spread if spread is not None else DEFAULT_RANGES[category]
    base = min(player_br, 11.0) if category in ('ground', 'spaa') and mode != 'ground' else player_br
    return [v for v in vehicles if v.get('name') != player and v.get('br') is not None
            and eligible(v, category, mode) and base + lo <= v['br'] <= base + hi]


def vehicle_map(vehicles):
    return {v['name']: v for v in vehicles}
