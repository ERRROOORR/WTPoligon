"""Сохраняемая модель сценария. В GUI не хранятся правила построения миссии."""
from dataclasses import asdict, dataclass, field

SCHEMA_VERSION = 1
DEFAULT_COUNTS = {'air': 10, 'fighters': 2, 'heli': 2, 'ground': 8, 'spaa': 3, 'ships': 3}
DEFAULT_RANGES = {'air': (-1.5, .5), 'fighters': (-1., .7), 'heli': (-4., 4.),
                  'ground': (-1., 1.), 'spaa': (-1., 1.), 'ships': (-3., 3.)}
DEFAULT_DISTANCES = {'air': 10000, 'fighters': 10000, 'heli': 3000,
                     'ground': 1200, 'spaa': 1200, 'ships': 30000}


@dataclass
class Target:
    vehicle: str
    count: int = 1


@dataclass
class Category:
    count: int = 0
    br_min: float = -1.0
    br_max: float = 1.0
    targets: list[Target] = field(default_factory=list)
    shoots: bool = False
    distance: int = 1200
    radar: bool = False

    def total(self):
        return sum(t.count for t in self.targets)


@dataclass
class Conditions:
    map: str = 'tunisia'
    time: str = 'Day'
    weather: str = 'good'
    difficulty: str = ''
    start_altitude: int = 2000
    start_speed: int = 0
    ground_start: bool = False
    air_altitude: str = 'mixed'


@dataclass
class Rules:
    markers: bool = True
    restore_targets: bool = True
    restore_ammo: bool = True
    infinite_fuel: bool = True
    player_respawn: bool = True
    moving_ships: bool = True
    rapid_reload: int = 0


@dataclass
class Duel:
    enemy: str = ''
    loadout: str = ''
    count: int = 1
    distance: int = 15000
    altitude: int = 0
    shoots: bool = True


def default_categories():
    return {key: Category(count=DEFAULT_COUNTS[key], br_min=DEFAULT_RANGES[key][0],
                          br_max=DEFAULT_RANGES[key][1], distance=DEFAULT_DISTANCES[key])
            for key in DEFAULT_COUNTS}


@dataclass
class Scenario:
    mode: str = 'air'
    player: str = ''
    player_br: float | None = None
    conditions: Conditions = field(default_factory=Conditions)
    categories: dict[str, Category] = field(default_factory=default_categories)
    duel: Duel = field(default_factory=Duel)
    rules: Rules = field(default_factory=Rules)

    def to_dict(self):
        return {'schema_version': SCHEMA_VERSION, **asdict(self)}

    @classmethod
    def from_dict(cls, data):
        if 'schema_version' not in data and 'spawn' in data:
            return cls.from_legacy(data)
        version = data.get('schema_version')
        if version != SCHEMA_VERSION:
            raise ValueError('неизвестная версия сценария: %r' % version)
        categories = default_categories()
        for key, raw in data.get('categories', {}).items():
            if key in categories:
                categories[key] = Category(**{**asdict(categories[key]), **raw,
                                              'targets': [Target(**t) for t in raw.get('targets', [])]})
        return cls(mode=data.get('mode', 'air'), player=data.get('player', ''),
                   player_br=data.get('player_br'), conditions=Conditions(**data.get('conditions', {})),
                   categories=categories, duel=Duel(**data.get('duel', {})), rules=Rules(**data.get('rules', {})))

    @classmethod
    def from_legacy(cls, data):
        """Старый targets.Scenario из install metadata/CLI."""
        from ..targets import AIR_BOTS, TARGET_SETS
        spawn = data.get('spawn', '')
        mode = {'firing_range': 'ground', 'avn_fiji': 'naval',
                'denmark_heli_airfield': 'heli'}.get(spawn, 'air')
        sc = cls(mode=mode)
        for category in sc.categories.values():
            category.count = 0
        if data.get('ground') in TARGET_SETS:
            cat = sc.categories['ground']
            cat.targets = [Target(v) for v in TARGET_SETS[data['ground']][1]]
            cat.count, cat.distance = len(cat.targets), data.get('ground_distance', 0)
        if data.get('air') in AIR_BOTS:
            cat = sc.categories['air']
            cat.targets = [Target(AIR_BOTS[data['air']][1])]
            cat.count, cat.distance, cat.radar = 1, data.get('air_distance', 10000), data.get('air_radar', False)
        return sc
