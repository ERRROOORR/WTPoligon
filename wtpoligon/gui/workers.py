"""CPU work isolated from Qt's event loop and the Python GIL."""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import hashlib
import os
import tempfile
import threading
from functools import lru_cache

_pool = None
_pool_lock = threading.Lock()
_sources = {}


def pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ProcessPoolExecutor(max_workers=2, mp_context=get_context('spawn'))
    return _pool


def source_at(kind, root):
    from ..game.source import open_source
    key = kind, root
    if key not in _sources:
        _sources[key] = open_source(game_dir=root) if kind == 'game' else open_source(datamine=root)
    return _sources[key]


def catalog(kind, root, cache_dir):
    from .. import loadout
    return loadout.load_catalog(source_at(kind, root), cache_dir)


def stats(kind, root, vehicle, loadout, vehicles, cache_dir):
    from .. import stats as S
    source = source_at(kind, root)
    model = S.Stats(source, vehicle, loadout)
    limits = {}
    for section in model.sections():
        rows = model.for_section(section)
        if rows and section != 'РЛС':
            limits[section] = S.ranges(source, vehicles, vehicle['kind'], rows, cache_dir)
    if 'РЛС' in model.sections():
        limits['РЛС'] = S.radar_ranges(source, vehicles, vehicle['kind'], cache_dir)
    model.source = None
    return model, limits


def scenario(data, vehicles, seed):
    from ..scenarios import autopick
    from ..scenarios.model import Scenario
    model = Scenario.from_dict(data)
    autopick.refill_all(model, vehicles, seed)
    return model.to_dict()


def atlas(kind, root, signature, cache_dir, path):
    """Return decoded image bytes, retaining a PNG copy across launches."""
    key = hashlib.sha256((signature + '\0' + path).encode('utf-8')).hexdigest()
    directory = os.path.join(cache_dir, 'atlas_png')
    filename = os.path.join(directory, key + '.png')
    try:
        with open(filename, 'rb') as stream:
            return stream.read()
    except OSError:
        pass
    data = source_at(kind, root).atlas_file(path)
    if data and data.startswith(b'\x89PNG'):
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
            os.replace(tmp, filename)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return data


def unit_image(kind, root, signature, cache_dir, name):
    parts = name.lower().split('_')
    for n in range(len(parts), 1, -1):
        data = atlas(kind, root, signature, cache_dir, 'units/%s.png' % '_'.join(parts[:n]))
        if data:
            return data
    return None


def loadout_setup(kind, root, vehicle):
    from .. import build as BL
    from .. import loadout as L
    source = source_at(kind, root)
    unit = source.load(vehicle['file'])
    pylons = L.read_pylons(unit) if unit is not None else None
    lo = None
    titles = []
    if pylons is not None and pylons.scheme:
        name = BL.default_preset(unit, vehicle['name'], vehicle['kind'])
        try:
            lo = L.from_preset(source, pylons, name) if name else L.Loadout()
        except ValueError:
            lo = L.Loadout(name if pylons.scheme == 'legacy' else '')
        titles = L.preset_titles(source, pylons)
    if pylons is None or not pylons.scheme:
        return pylons, lo, titles, None, [], [], None
    from .loadout_page import LoadoutPage
    from types import SimpleNamespace
    class Calc:
        has = LoadoutPage.has
        points = LoadoutPage.points
        _mass = LoadoutPage._mass
        _choice_icon = LoadoutPage._choice_icon
        _weapon_icon = LoadoutPage._weapon_icon
        _option_items = LoadoutPage._option_items
    calc = Calc()
    calc.win = SimpleNamespace(source=source, vehicles=[])
    calc.pylons, calc.lo, calc.catalog = pylons, lo, None
    calc._prepared_points = calc._prepared_options = None
    calc.mode, calc.group_filter = 'stock', ''
    calc.find = SimpleNamespace(text=lambda: '')
    points = calc.points()
    calc.selected = next((p[0] for p in points if p[3]), points[0][0] if points else None)
    options = calc._option_items()
    summary = L.summarize(source, pylons, lo, None)
    return pylons, lo, titles, calc.selected, points, options, summary


def review(kind, root, vehicle, in_hangar, scenario, loadout, catalog, stats, vehicles, ammo=None):
    from .. import build
    source = source_at(kind, root)
    if stats is not None:
        stats.source = source
    plan = build.stock_plan(source, vehicle, in_hangar, scenario=scenario, loadout=loadout,
                             catalog=catalog, stats=stats, vehicles=vehicles, ammo=ammo)
    return plan, build.verify_plan(source, plan)


def ammo_setup(kind, root, vehicle, preset):
    from ..ammo.catalog import stock_setup, _names
    from .. import build
    source = source_at(kind, root)
    if not preset:
        unit = source.load(vehicle['file'])
        preset = build.default_preset(unit, vehicle['name'], vehicle['kind']) if unit else ''
    return (*stock_setup(source, vehicle, preset), _names(source))


@lru_cache(maxsize=2)
def _ammo_search_index(kind, root, cache_dir):
    from ..ammo import catalog as C
    from ..game import search as S
    from .. import loadout as L
    source = source_at(kind, root)
    shells = C.all_shells(source)
    names = C._names(source)
    catalog = L.load_catalog(source, cache_dir) if cache_dir else []
    carrier_by_gun = {L.weapon_key(w['path']): w.get('carriers', []) for w in catalog}
    gun_name = lambda shell: C.display_name(names, shell.weapon, True)
    def keys(shell):
        values = (shell.name, C.display_name(names, shell.name), shell.kind,
                  C.kind_name(names, shell.kind), shell.weapon, gun_name(shell))
        return list(dict.fromkeys(form for value in values for form in S.forms(value)))

    searcher = S.Searcher(shells, keys, lambda s: C.display_name(names, s.name))
    return source, shells, names, carrier_by_gun, searcher


def ammo_search(kind, root, query, vehicles=(), cache_dir=None):
    """Search shells, their guns and carrier vehicles in a worker process."""
    from ..ammo import catalog as C
    from ..game import search as S
    from .. import loadout as L

    if not S.norm(query):
        return []
    source, shells, names, carrier_by_gun, searcher = _ammo_search_index(kind, root, cache_dir)
    vehicle_by_name = {v['name'].lower(): v for v in vehicles}
    by_name = searcher.search(query)
    vehicle_hits = S.searcher(vehicles).search(query) if vehicles else []
    matched_carriers = {v['name'].lower() for v, score in vehicle_hits if score >= 85}
    by_carrier = [s for s in shells if matched_carriers.intersection(
        carrier_by_gun.get(L.weapon_key(s.weapon), ()))]
    ordered = list(dict.fromkeys(by_carrier + [s for s, _score in by_name]))[:120]
    result = []
    for shell in ordered:
        carriers = carrier_by_gun.get(L.weapon_key(shell.weapon), ())
        carrier = next((vehicle_by_name[n.lower()] for n in carriers if n.lower() in matched_carriers
                        and n.lower() in vehicle_by_name), None)
        if carrier is None:
            carrier = next((vehicle_by_name[n.lower()] for n in carriers if n.lower() in vehicle_by_name), None)
        label = (carrier.get('ru') or carrier.get('en') or carrier['name']) if carrier else '—'
        block = C.shell_block(source, shell.key)
        ammo = next((b for b in block.blocks if b.name in ('bullet', 'rocket', 'bomb', 'torpedo')), block) if block else None
        caliber = ammo.get('caliber') if ammo else None
        result.append((shell, C.display_name(names, shell.name), C.kind_name(names, shell.kind),
                       C.display_name(names, shell.weapon, True), label,
                       round(caliber * 1000, 1) if isinstance(caliber, (int, float)) else None,
                       carrier.get('kind') if carrier else None))
    return result


def ammo_details(kind, root, key):
    from ..ammo.catalog import shell_block
    from ..game import blk as B
    path, _block = key.split('|', 1)
    source = source_at(kind, root)
    tree = source.load(path)
    block = shell_block(source, key)
    explosive = source.load('gameData/damage_model/explosive.blk')
    types = explosive.block('explosiveTypes') if explosive else None
    factors = {b.name: b.get('strengthEquivalent') for b in (types.blocks if types else [])
               if b.get('strengthEquivalent') is not None}
    return (B.to_text(B.Block(None, blocks=[block])) if block else '',
            B.to_text(tree) if tree else '', factors)


def ammo_guns(kind, root, query):
    from ..ammo.catalog import shells_in
    source = source_at(kind, root)
    q = query.lower()
    return [p for p in source.list_files('gameData/Weapons/') if p.endswith('.blk') and q in p.lower()
            and shells_in(source, p)][:300]


def collect_logs(game_dir, app_root):
    from .. import logs
    return logs.collect(game_dir, app_root)
