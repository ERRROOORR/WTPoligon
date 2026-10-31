"""Конструктор подвески (этап 3): пилоны, своя подвеска, итоги, невесомая, библиотека, CLI, окно — без игры.

Источник — поддельный датамайн test_wtpoligon + самолёт b1 (новая схема, по образцу A-26B) и c1 (старая схема,
по образцу A-20G). Прогон по настоящему датамайну — при WTP_DATAMINE=<клон> (A-26B: невесомая ФАБ-9000 в отсеке
даёт EmptyMass 925 кг, как в проверенных кругах 18/31; все штатные пресеты всех самолётов узнаются как штатные).
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.*=false')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from test_wtpoligon import UNITTAGS, Base, make_datamine  # noqa: E402
from wtpoligon import build as BL  # noqa: E402
from wtpoligon import install as I  # noqa: E402
from wtpoligon import loadout as L  # noqa: E402
from wtpoligon.game import blk as B  # noqa: E402
from wtpoligon.game import index as X  # noqa: E402
from wtpoligon.game import source as S  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    QApplication = None

BOMB = 'gameData/Weapons/bombguns/b1_bomb.blk'
BIG = 'gameData/Weapons/bombguns/big_bomb.blk'
ROCKET = 'gameData/Weapons/rocketguns/b1_rocket.blk'
SAM = 'gameData/Weapons/groundmodels_weapons/sam_missile.blk'
SAM9X = 'gameData/Weapons/groundmodels_weapons/sam_aim9x.blk'
SACLOS = 'gameData/Weapons/groundmodels_weapons/sam_saclos.blk'
TANKGUN = 'gameData/Weapons/groundmodels_weapons/tank_gun.blk'
GUN = 'gameData/Weapons/gun_b1.blk'
MID = 'gameData/Weapons/bombguns/mid_bomb.blk'
MER = 'gameData/Weapons/containers/mer_b1_x6.blk'
WP = 'gameData/FlightModels/weaponPresets/'


def _w(trigger, blk, emitter, bullets=1, **kw):
    return dict(trigger=trigger, blk=blk, emitter=emitter, bullets=bullets, **kw)


EXTRA = {
    'aces.vromfs.bin_u/gamedata/flightmodels/b1': {
        'fmFile': 'fm/b1.blk',
        'WeaponSlots': {
            'maxloadMass': 1000.0, 'maxloadMassLeftConsoles': 300.0, 'maxloadMassRightConsoles': 300.0,
            'maxDisbalance': 100.0,
            'WeaponSlot': [
                {'index': 0, 'WeaponPreset': {'name': 'default_guns', 'Weapon': _w('machine gun', GUN, 'g1', 300)}},
                {'index': 1, 'tier': 1, 'WeaponPreset': {
                    'name': 'rockets_left', 'reqModification': 'rails',
                    'Weapon': [_w('rockets', ROCKET, 'r1'), _w('rockets', ROCKET, 'r2')],
                    'BannedWeaponPreset': {'slot': 2, 'preset': 'bomb_left'}}},
                {'index': 2, 'tier': 1, 'WeaponPreset': {'name': 'bomb_left',
                                                         'Weapon': _w('bombs', BOMB, 'b1', external=True)}},
                {'index': 3, 'tier': 1, 'WeaponPreset': {'name': 'bay_bombs', 'Weapon': [
                    _w('bombs', BOMB, 'bay%d' % i) for i in range(1, 5)]}},
                {'index': 4, 'tier': 1, 'WeaponPreset': {'name': 'bomb_right',
                                                         'Weapon': _w('bombs', BOMB, 'b2', external=True)}},
                {'index': 5, 'tier': 1, 'WeaponPreset': {
                    'name': 'rockets_right', 'Weapon': [_w('rockets', ROCKET, 'r3'), _w('rockets', ROCKET, 'r4')]}},
            ]},
        'weapon_presets': {'preset': [{'name': 'b1_default', 'blk': WP + 'b1_default.blk'},
                                      {'name': 'b1_bombs', 'blk': WP + 'b1_bombs.blk'}]}},
    'aces.vromfs.bin_u/gamedata/flightmodels/weaponpresets/b1_default': {'Weapon': {'slot': 0,
                                                                                     'preset': 'default_guns'}},
    'aces.vromfs.bin_u/gamedata/flightmodels/weaponpresets/b1_bombs': {'Weapon': [
        {'slot': 0, 'preset': 'default_guns'}, {'slot': 2, 'preset': 'bomb_left'},
        {'slot': 3, 'preset': 'bay_bombs'}, {'slot': 4, 'preset': 'bomb_right'}]},
    'aces.vromfs.bin_u/gamedata/flightmodels/fm/b1': {'Mass': {'EmptyMass': 3000.0, 'Takeoff': 5000.0}},
    'aces.vromfs.bin_u/gamedata/flightmodels/c1': {
        'fmFile': 'fm/c1.blk',
        'weapon_presets': {'preset': [{'name': 'c1_default', 'blk': WP + 'c1_default.blk'},
                                      {'name': 'c1_bombs', 'blk': WP + 'c1_bombs.blk'}]}},
    'aces.vromfs.bin_u/gamedata/flightmodels/weaponpresets/c1_default': {'hideNodes': {'node': 'pylon1'}},
    'aces.vromfs.bin_u/gamedata/flightmodels/weaponpresets/c1_bombs': {'Weapon': [
        _w('bombs', BOMB, 'bomb1'), _w('bombs', BOMB, 'bomb2')]},
    'aces.vromfs.bin_u/gamedata/flightmodels/fm/c1': {'Mass': {'EmptyMass': 2000.0}},
    'aces.vromfs.bin_u/gamedata/weapons/bombguns/b1_bomb': {'bomb': {'mass': 100.0}},
    'aces.vromfs.bin_u/gamedata/weapons/bombguns/big_bomb': {'mass': 50.0, 'bomb': {'mass': 950.0}},
    'aces.vromfs.bin_u/gamedata/weapons/bombguns/mid_bomb': {'bomb': {'mass': 350.0}},
    'aces.vromfs.bin_u/gamedata/weapons/containers/mer_b1_x6': {'container': True, 'blk': BOMB, 'bullets': 6,
                                                                 'mass': 40.0},
    'aces.vromfs.bin_u/gamedata/weapons/rocketguns/b1_rocket': {'rocket': {'mass': 20.0}},
    'aces.vromfs.bin_u/gamedata/weapons/groundmodels_weapons/sam_missile': {'rocket': {'mass': 50.0}},
    'aces.vromfs.bin_u/gamedata/weapons/gun_b1': {'bullet': {'mass': 0.05}},
    'aces.vromfs.bin_u/gamedata/weapons/groundmodels_weapons/tank_gun': {'cannon': True, 'bullet': {'mass': 10.0}},
    'aces.vromfs.bin_u/gamedata/weapons/groundmodels_weapons/sam_saclos': {
        'cannon': True, 'mesh': 'tpk', 'animChar': 'tpk_char', 'reloadAnimParam': 'rocket_action', 'bullet': {
            'mass': 70.0, 'rocket': {'mass': 70.0, 'guidanceType': 'saclos', 'shellAnimChar': 'tpk_deployed_char',
                                     'guidance': {'controlRangeMax': 20000.0}}}},
    'aces.vromfs.bin_u/gamedata/weapons/groundmodels_weapons/sam_aim9x': {'cannon': True, 'bullet': {
        'mass': 85.0, 'isAam': True, 'rocket': {'mass': 85.0, 'guidanceType': 'ir', 'guidance': {}}}},
}
WEAPONRY = ('"<ID|readonly|noverify>";"<English>";"<Russian>";"<Comments>"\n'
            '"weapons/b1_bomb/short";"B-100";"Б-100";\n"weapons/big_bomb";"Big bomb";"Большая бомба";\n'
            '"weapons/b1_rocket/short";"R-20";"Р-20";\n"weapons/sam_aim9x";"AIM-9X SAM";"ЗУР AIM-9X";\n')


def make_loadout_datamine(root):
    make_datamine(root)
    for rel, obj in EXTRA.items():
        p = os.path.join(root, *rel.split('/')) + '.blkx'
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(obj, f)
    tags = dict(UNITTAGS, b1={'type': 'aircraft'}, c1={'type': 'aircraft'})
    with open(os.path.join(root, 'char.vromfs.bin_u', 'config', 'unittags.blkx'), 'w', encoding='utf-8') as f:
        json.dump(tags, f)
    with open(os.path.join(root, 'lang.vromfs.bin_u', 'lang', 'units_weaponry.csv'), 'w', encoding='utf-8') as f:
        f.write(WEAPONRY)


class LBase(Base):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='wtp_lo_')
        self.dm = os.path.join(self.tmp, 'dm')
        self.app = os.path.join(self.tmp, 'app')
        self.game = os.path.join(self.tmp, 'game')
        os.makedirs(self.game)
        make_loadout_datamine(self.dm)
        self.src = S.open_source(datamine=self.dm)
        self.vehicles, self.stats = X.load_index(self.src, os.path.join(self.app, 'cache'))
        self.cat = L.load_catalog(self.src, os.path.join(self.app, 'cache'))
        self.b1 = L.read_pylons(self.src.load('gameData/flightModels/b1.blk'))
        self.c1 = L.read_pylons(self.src.load('gameData/flightModels/c1.blk'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plan(self, name, lo, hangar=False):
        plan = BL.stock_plan(self.src, self.v(name), hangar, loadout=lo, catalog=self.cat)
        return plan, BL.verify_plan(self.src, plan)


class TestPylons(LBase):
    def test_read_slots(self):
        p = self.b1
        self.assertEqual(p.scheme, 'slots')
        self.assertEqual(p.limits['maxloadMass'], 1000.0)
        self.assertEqual([s.index for s in p.pylon_slots], [1, 2, 3, 4, 5])
        self.assertTrue(p.slot(0).fixed)
        self.assertEqual([p.slot(i).side for i in range(1, 6)], ['L', 'L', None, 'R', 'R'])
        self.assertEqual(L.mirror_pairs(p), {1: 5, 5: 1, 2: 4, 4: 2})
        self.assertEqual(p.slot(1).variant('rockets_left').banned, [(2, 'bomb_left')])
        self.assertEqual(self.c1.scheme, 'legacy')

    def test_container(self):
        info = L.weapon_info(self.src, MER)
        self.assertEqual((info['kind'], info['title'], info['per'], info['unit_title']), ('bomb', 'Б-100 ×6', 6, 'Б-100'))
        self.assertEqual(L.weapon_mass(self.src, MER), 640.0)              # 6 × 100 + держатель 40
        lo = L.Loadout(slots={2: {'weapon': MER, 'sample': 'bomb_left'}})
        sm = L.summarize(self.src, self.b1, lo, self.cat)
        self.assertEqual((sm.total, sm.counts), (640.0, {'Б-100': 6}))
        self.assertEqual(L.weapon_group('bombs', 'bombs_middle_group_x6'), 'bombs')
        self.assertEqual(L.weapon_group('guided bombs', 'glide_guided_bomb_middle_jdam'), 'glide')
        self.assertEqual(L.weapon_group('fuel tanks', 'ptb'), 'tanks')
        self.assertEqual(L.weapon_group('aam', ''), 'aam')

    def test_search_by_name_and_carrier(self):
        by = {w['stem']: w for w in self.cat}
        self.assertEqual(by['b1_bomb']['carriers'], ['b1', 'c1'])          # слоты b1 и пресет c1
        self.assertEqual(by['big_bomb']['carriers'], [])
        found, carriers = L.search_weapons(self.cat, self.vehicles, 'б1')    # носитель, русская «б»
        self.assertEqual([c['name'] for c in carriers][:1], ['b1'])
        self.assertTrue({'b1_bomb', 'b1_rocket', 'gun_b1'} <= {w['stem'] for w in found})   # и пушка носителя
        found, carriers = L.search_weapons(self.cat, self.vehicles, 'большя бомба')         # опечатка
        self.assertEqual((carriers, found[0]['stem']), ([], 'big_bomb'))
        found, _c = L.search_weapons(self.cat, self.vehicles, 'mer b1')
        self.assertEqual(found[0]['stem'], 'mer_b1_x6')

    def test_sam_in_bullet_is_missile(self):
        """ЗУР наземки: bullet{rocket{guidance}} — ракета «воздух-воздух», а не пушка; точное имя находится и без
        галочки «+ оружие танков…»."""
        by = {w['stem']: w for w in self.cat}
        self.assertEqual((by['sam_aim9x']['kind'], by['sam_aim9x']['group']), ('rocket', 'aam'))
        self.assertEqual(by['sam_aim9x']['mass'], 85.0)
        found, _c = L.search_weapons(self.cat, self.vehicles, 'aim-9x')
        self.assertEqual(found[0]['stem'], 'sam_aim9x')

    def test_swap_side(self):
        self.assertEqual(L._swap_side('hvar_x7_left'), 'hvar_x7_right')
        self.assertEqual(L._swap_side('500lbs_wing_left_out'), '500lbs_wing_right_out')
        self.assertEqual(L._swap_side('hf_14_pod_1_l'), 'hf_14_pod_1_r')
        self.assertEqual(L._swap_side('bay_bombs'), 'bay_bombs')

    def test_catalog(self):
        by = {w['stem']: w for w in self.cat}
        self.assertEqual((by['b1_bomb']['kind'], by['b1_bomb']['ru'], by['b1_bomb']['air']), ('bomb', 'Б-100', True))
        self.assertEqual(by['big_bomb']['mass'], 1000.0)                    # боеприпас + держатель
        self.assertEqual((by['sam_missile']['air'], by['sam_missile']['trigger'], by['sam_missile']['pylon']),
                         (False, 'rockets', False))
        self.assertEqual(by['b1_rocket']['trigger'], 'rockets')
        self.assertEqual([w['stem'] for w in L.find_weapons(self.cat, 'большая')], ['big_bomb'])
        self.assertNotIn('sam_missile', [w['stem'] for w in L.find_weapons(self.cat)])
        self.assertIn('sam_missile', [w['stem'] for w in L.find_weapons(self.cat, pylon_only=False)])


class TestLoadout(LBase):
    def test_stock_preset_keeps_hangar(self):
        lo = L.from_preset(self.src, self.b1, 'b1_bombs')
        self.assertEqual(lo.slots, {0: {'variant': 'default_guns'}, 2: {'variant': 'bomb_left'},
                                    3: {'variant': 'bay_bombs'}, 4: {'variant': 'bomb_right'}})
        self.assertEqual(L.stock_preset_of(self.src, self.b1, lo), 'b1_bombs')
        plan, problems = self.plan('b1', lo, hangar=True)
        self.assertEqual((plan.launch, plan.weapons, problems), (BL.HANGAR, 'b1_bombs', []))
        self.assertEqual([f for f, _ in plan.files], ['UserMissions/WTPoligon5/wtp5_b1.blk'])
        sm = L.summarize(self.src, self.b1, lo, self.cat)
        self.assertEqual((sm.total, sm.left, sm.right), (600.0, 100.0, 100.0))
        self.assertEqual(sm.counts['Б-100'], 6)

    def test_custom_forces_copy_and_builds(self):
        lo = L.from_preset(self.src, self.b1, 'b1_bombs')
        lo.slots[3] = {'weapon': BIG, 'sample': 'bay_bombs', 'count': 1}
        lo.slots[1] = {'variant': 'rockets_left'}
        plan, problems = self.plan('b1', lo, hangar=True)
        self.assertEqual(problems, [])
        self.assertEqual((plan.launch, plan.unit_class, plan.weapons), (BL.COPY, 'wtp5_b1', 'wtp5_loadout'))
        self.assertTrue(plan.notes[0].startswith('Подвеска изменена, поэтому в миссии будет копия'))
        files = dict(plan.files)
        preset = files['content/pkg_local/' + WP + 'wtp5_b1_loadout.blk']
        self.assertIn('preset:t="wtp5_s3_big_bomb_x1"', preset)
        unit = B.resolve_file(files['content/pkg_local/gameData/flightModels/wtp5_b1.blk'], self.src.loader(), [])
        slot3 = [s for s in unit.block('WeaponSlots').blocks if s.get('index') == 3][0]
        new = [p for p in slot3.blocks if p.get('name') == 'wtp5_s3_big_bomb_x1'][0]
        self.assertEqual([w.get('emitter') for w in new.blocks if w.name == 'Weapon'], ['bay1'])
        self.assertEqual([w.get('blk') for w in new.blocks if w.name == 'Weapon'], [BIG])
        sm = L.summarize(self.src, self.b1, lo, self.cat)
        self.assertEqual(sm.total, 1240.0)
        kinds = {lvl for lvl, _t in sm.warnings}
        self.assertIn('warn', kinds)                                       # больше maxloadMass
        self.assertTrue(any('нельзя вместе' in t for _l, t in sm.warnings))  # запрет ангара — только сведения
        self.assertTrue(any('rails' in t for _l, t in sm.warnings))

    def test_foreign_kind_trigger(self):
        lo = L.Loadout(slots={2: {'weapon': ROCKET, 'sample': 'bomb_left'},
                              4: {'weapon': TANKGUN, 'sample': 'bomb_right'}})
        plan, problems = self.plan('b1', lo)
        self.assertEqual(problems, [])
        unit = B.resolve_file(dict(plan.files)['content/pkg_local/gameData/flightModels/wtp5_b1.blk'],
                              self.src.loader(), [])
        slot2 = [s for s in unit.block('WeaponSlots').blocks if s.get('index') == 2][0]
        w = [p for p in slot2.blocks if p.get('name') == 'wtp5_s2_b1_rocket'][0].block('Weapon')
        self.assertEqual((w.get('trigger'), w.get('external')), ('rockets', True))
        sm = L.summarize(self.src, self.b1, lo, self.cat)
        untested = [t for lvl, t in sm.warnings if lvl == 'untested']
        self.assertEqual(len(untested), 1)      # ракета вместо бомбы
        danger = [t for lvl, t in sm.warnings if lvl == 'danger']
        self.assertEqual(len(danger), 1)        # наземное оружие (не ракета) на пилоне — может уронить игру
        self.assertTrue(any('📄' in n for n in plan.notes))
        self.assertTrue(any(n.startswith('⚠') for n in plan.notes))

    def test_ground_sam_becomes_air_rocket(self):
        """32-й круг: ЗУР наземного формата (cannon + bullet{rocket}) на пилоне роняет игру, переделанная в
        rocketGun — работает. Программа сама пишет переделку и вешает её (saclos тоже проверено)."""
        lo = L.Loadout(slots={2: {'weapon': SAM9X, 'sample': 'bomb_left'}, 4: {'weapon': SACLOS, 'sample': 'bomb_right'}})
        plan, problems = self.plan('b1', lo)
        self.assertEqual(problems, [])
        files = dict(plan.files)
        air = {p: B.parse_text(t) for p, t in files.items() if '/rocketGuns/' in p}
        self.assertEqual(sorted(air), ['content/pkg_local/gameData/Weapons/rocketGuns/wtp5_sam_aim9x_air.blk',
                                       'content/pkg_local/gameData/Weapons/rocketGuns/wtp5_sam_saclos_air.blk'])
        sac = air['content/pkg_local/gameData/Weapons/rocketGuns/wtp5_sam_saclos_air.blk']
        self.assertEqual((sac.get('rocketGun'), sac.get('cannon'), sac.get('bullets'), sac.get('mesh')),
                         (True, None, 1, 'tpk'))
        # анимированная модель: на пилоне — animChar пусковой, в полёте — shellAnimChar ракеты (верх файла)
        self.assertEqual((sac.get('animChar'), sac.get('reloadAnimParam'), sac.get('shellAnimChar')),
                         ('tpk_char', 'rocket_action', 'tpk_deployed_char'))
        self.assertEqual(sac.block('rocket').get('guidanceType'), 'saclos')
        unit = B.resolve_file(files['content/pkg_local/gameData/flightModels/wtp5_b1.blk'], self.src.loader(), [])
        blks = {s.get('index'): [w.get('blk') for p in s.blocks if str(p.get('name')).startswith('wtp5_')
                                 for w in p.blocks if w.name == 'Weapon']
                for s in unit.block('WeaponSlots').blocks if s.get('index') in (2, 4)}
        self.assertEqual(blks, {2: [L.air_copy_path(SAM9X)], 4: [L.air_copy_path(SACLOS)]})
        sm = L.summarize(self.src, self.b1, lo, self.cat)
        levels = [lvl for lvl, _t in sm.warnings]
        self.assertNotIn('danger', levels)
        self.assertEqual(sum('переделана в авиационную' in t for _l, t in sm.warnings), 2)
        self.assertFalse([t for lvl, t in sm.warnings if 'может не наводиться' in t])   # saclos проверено (v0.101)
        self.assertFalse(L.is_risky({w['stem']: w for w in self.cat}['sam_saclos']))
        self.assertTrue(L.is_risky({w['stem']: w for w in self.cat}['tank_gun']))

    def test_weightless(self):
        lo = L.Loadout(slots={3: {'weapon': BIG, 'sample': 'bay_bombs', 'count': 1}}, weightless=True)
        plan, problems = self.plan('b1', lo)
        self.assertEqual(problems, [])
        files = dict(plan.files)
        fm = files['content/pkg_local/gameData/flightModels/fm/wtp5_b1.blk']
        self.assertIn('"@override:EmptyMass":r=2000.0', fm)
        tree = B.resolve_file(fm, self.src.loader(), [])
        self.assertEqual(tree.block('Mass').get('EmptyMass'), 2000.0)
        self.assertEqual(tree.block('Mass').get('Takeoff'), 5000.0)
        self.assertIn('"@override:fmFile":t="fm/wtp5_b1.blk"', files['content/pkg_local/gameData/flightModels/'
                                                                     'wtp5_b1.blk'])
        lo.slots = L.fill_all(self.b1, BIG)          # 5 пилонов: 2+1+4+1+2 точек по 1000 кг — тяжелее планера
        sm = L.summarize(self.src, self.b1, lo, self.cat)
        self.assertEqual(sm.total, 10000.0)
        self.assertTrue(any(lvl == 'refuse' and 'тяжелее' in t for lvl, t in sm.warnings))
        plan, problems = self.plan('b1', lo)
        self.assertTrue(problems)
        lo.slots = {3: {'weapon': BIG, 'sample': 'bay_bombs', 'count': 2}, 2: {'variant': 'bomb_left'},
                    4: {'variant': 'bomb_right'}, 1: {'variant': 'rockets_left'}, 5: {'variant': 'rockets_right'}}
        sm = L.summarize(self.src, self.b1, lo, self.cat)    # 2000 + 100 + 100 + 40 + 40 = 2280 → 720 кг
        self.assertAlmostEqual(sm.weightless_mass, 720.0)

    def test_weightless_untested_below_9_percent(self):
        lo = L.Loadout(slots={3: {'weapon': BIG, 'sample': 'bay_bombs', 'count': 2},
                              2: {'weapon': MID, 'sample': 'bomb_left'}, 4: {'weapon': MID, 'sample': 'bomb_right'}},
                       weightless=True)
        sm = L.summarize(self.src, self.b1, lo, self.cat)          # 2000 + 350 + 350 → 300 кг (10 %)
        self.assertAlmostEqual(sm.weightless_mass, 300.0)
        self.assertFalse([t for lvl, t in sm.warnings if lvl == 'untested' and '9 %' in t])
        lo.slots[1] = {'variant': 'rockets_left'}
        lo.slots[5] = {'variant': 'rockets_right'}
        sm = L.summarize(self.src, self.b1, lo, self.cat)          # + 40 + 40 → 220 кг (7 %)
        self.assertAlmostEqual(sm.weightless_mass, 220.0)
        self.assertTrue([t for lvl, t in sm.warnings if lvl == 'untested' and '9 %' in t])

    def test_mirror(self):
        lo = L.Loadout(slots={1: {'variant': 'rockets_left'}, 2: {'weapon': BIG, 'sample': 'bomb_left'}})
        L.mirror(lo, self.b1, 1, 5)
        L.mirror(lo, self.b1, 2, 4)
        self.assertEqual(lo.slots[5], {'variant': 'rockets_right'})
        self.assertEqual(lo.slots[4], {'weapon': BIG, 'sample': 'bomb_right'})
        L.mirror(lo, self.b1, 3, 5)                                 # пустой пилон — снять и на паре
        self.assertNotIn(5, lo.slots)
        L.mirror(lo, self.b1, 1, 3)                                 # варианта нет — то же оружие на образце
        self.assertEqual(lo.slots[3], {'weapon': ROCKET, 'sample': 'bay_bombs'})

    def test_legacy(self):
        lo = L.from_preset(self.src, self.c1, 'c1_bombs')
        self.assertEqual(L.stock_preset_of(self.src, self.c1, lo), 'c1_bombs')
        lo.legacy[2] = BIG
        plan, problems = self.plan('c1', lo)
        self.assertEqual(problems, [])
        text = dict(plan.files)['content/pkg_local/' + WP + 'wtp5_c1_loadout.blk']
        self.assertIn('include "#/develop/gameBase/%sc1_bombs.blk"' % WP, text)
        self.assertIn('"@override:Weapon[2]"{\n  "@override:blk":t="%s"' % BIG, text)
        tree = B.resolve_file(text, self.src.loader(), [])
        self.assertEqual([w.get('blk') for w in tree.blocks if w.name == 'Weapon'], [BOMB, BIG])
        self.assertEqual(L.summarize(self.src, self.c1, lo, self.cat).total, 1100.0)
        lo.legacy[3] = BIG
        self.assertTrue(self.plan('c1', lo)[1])                     # точки 3 в пресете нет

    def test_library(self):
        lo = L.Loadout(slots={2: {'variant': 'bomb_left'}}, weightless=True, name='Моя бомба')
        L.library_save(self.app, 'b1', lo)
        self.assertEqual(L.library_names(self.app, 'B1'), ['Моя бомба'])
        self.assertEqual(L.library_get(self.app, 'b1', 'Моя бомба'), lo)
        self.assertTrue(L.library_delete(self.app, 'b1', 'Моя бомба'))
        self.assertEqual(L.library_names(self.app, 'b1'), [])
        with self.assertRaises(ValueError):
            L.library_save(self.app, 'b1', L.Loadout())

    def test_not_for_tanks(self):
        plan, problems = self.plan('t1', L.Loadout())
        self.assertIn('подвеска — только у самолётов и вертолётов', problems)


class TestCrashlog(LBase):
    def test_crashlog_finds_program_mission(self):
        import random
        logs = os.path.join(self.game, '.game_logs')
        os.makedirs(logs)
        key = bytes(random.Random(1).randrange(256) for _ in range(768))
        from wtpoligon.game import clog

        def put(name, text):
            data = text.encode()
            with open(os.path.join(logs, name), 'wb') as f:
                f.write(clog.decrypt(data, key))      # XOR симметричен: шифрование = расшифровка
        filler = ''.join('line %d of the game log with words and spaces here\n' % i for i in range(4000))
        put('2026_10_26_10_00_00.clog', filler + 'loading mission UserMissions/WTPoligon5/wtp5_f_15c.blk\n'
            + 'CRITICAL ERROR: something broke in wtp5_f_15c\n' + filler[:2000])
        os.utime(os.path.join(logs, '2026_10_26_10_00_00.clog'), (1, 1))
        put('2026_10_26_11_00_00.clog', filler)                              # новее, но без миссии программы
        code, out = self.run_cli('--game', self.game, 'crashlog', '--lines', '5')
        self.assertEqual(code, 0, out)
        self.assertIn('2026_10_26_10_00_00.clog', out)
        self.assertIn('CRITICAL ERROR: something broke', out)
        # после вылета игру перезапустили: в новом логе копия только в ангаре — нужен лог с запуском тестовой миссии
        put('2026_10_26_12_00_00.clog', filler + 'AcesApp::doJob mission UserMissions/WTPoligonTest/t67_wtp5t_x.blk\n'
            + 'last line before crash\n')
        os.utime(os.path.join(logs, '2026_10_26_12_00_00.clog'), (2, 2))
        put('2026_10_26_13_00_00.clog', filler + 'SQRL aircraft = wtp5_ucav_orion\n')
        code, out = self.run_cli('--game', self.game, 'crashlog', '--lines', '5')
        self.assertIn('2026_10_26_12_00_00.clog', out)
        self.assertIn('last line before crash', out)


class TestLoadoutCli(LBase):
    def test_pylons_weapons_mission(self):
        code, out = self.run_cli('pylons', 'b1')
        self.assertEqual(code, 0)
        self.assertIn('Пилон 1, слева, пара — 5', out)
        self.assertIn('bay_bombs', out)
        code, out = self.run_cli('weapons', '--find', 'big')
        self.assertIn('Большая бомба', out)
        code, out = self.run_cli('mission', 'b1', '--hangar', '--preset', 'b1_bombs')
        self.assertEqual(code, 0)
        self.assertIn('пресет вооружения: b1_bombs', out)
        code, out = self.run_cli('mission', 'b1', '--hangar', '--preset', 'b1_bombs', '--slot', '3=big_bomb:1',
                                 '--slot', '2=none', '--weightless', '--show')
        self.assertEqual(code, 0, out)
        self.assertIn('копия не из ангара', out)
        self.assertIn('wtp5_s3_big_bomb_x1', out)
        self.assertIn('"@override:EmptyMass":r=1900.0', out)       # 3000 − (1000 + 100)
        code, out = self.run_cli('mission', 'c1', '--preset', 'c1_bombs', '--point', '1=big_bomb')
        self.assertEqual(code, 0, out)
        code, out = self.run_cli('mission', 'b1', '--slot', '9=big_bomb')
        self.assertEqual(code, 2)


@unittest.skipIf(QApplication is None, 'нет PySide6')
class TestLoadoutWindow(LBase):
    @classmethod
    def setUpClass(cls):
        cls.qapp = QApplication.instance() or QApplication([])

    def window(self):
        from wtpoligon.gui.window import MainWindow
        w = MainWindow(self.src, self.vehicles, self.app, self.game)
        w.confirm = lambda *_a: True
        w.show()
        self.addCleanup(w.close)
        return w

    def test_untouched_is_stock(self):
        w = self.window()
        w.vehicles_page.select('b1')
        lp = w.loadout_page
        self.assertIsNone(lp.loadout())
        self.assertEqual([p[0] for p in lp.points()], [1, 2, 3, 4, 5])
        self.assertEqual(len(lp.cards), 5)
        w.go(5)
        self.assertEqual(w.review_page.plan.weapons, 'b1_default')

    def test_options_grouped_by_class(self):
        w = self.window()
        w.vehicles_page.select('b1')
        lp = w.loadout_page
        lp.select_pylon(1)
        self.assertEqual([c.payload for c in lp.options], [('variant', 'rockets_left')])
        lp.ensure_catalog()
        lp.set_mode('any')
        lp.find.setText('b1_')                         # «b1» — ещё и носитель: всё его вооружение, с пушкой
        groups = [g for g, *_r in lp._option_items()]
        self.assertEqual(sorted(set(groups)), ['bombs', 'guns', 'rockets'])
        self.assertEqual([c['name'] for c in lp._carriers][:1], ['b1'])
        lp.find.setText('mer')
        self.assertEqual([c.title for c in lp.options], ['Б-100 ×6'])   # держатель — по содержимому

    def test_build_custom_and_write(self):
        w = self.window()
        w.vehicles_page.select('b1')
        lp = w.loadout_page
        w.go(1)
        self.assertTrue(lp.apply_template('b1_bombs'))
        self.assertEqual(lp.loadout().slots[2], {'variant': 'bomb_left'})
        lp.select_pylon(3)
        lp.ensure_catalog()
        lp.set_mode('any')
        lp.find.setText('big')
        self.assertEqual(len(lp.options), 1)
        self.assertTrue(lp.choose(lp.options[0].payload))
        self.assertTrue(lp.count.isVisibleTo(lp))
        self.assertEqual(lp.count.maximum(), 4)
        lp.count.setValue(1)
        self.assertEqual(lp.lo.slots[3], {'weapon': BIG, 'sample': 'bay_bombs', 'count': 1})
        lp.select_pylon(2)
        self.assertIn('(парный)', lp.mirror_menu.actions()[0].text())      # пара по именам — первой
        self.assertTrue(lp.mirror_to(4))
        self.assertIn('1 200 кг', lp.summary_text())
        lp.weightless.setChecked(True)
        self.assertIn('1 800 кг', lp.summary_text())                     # 3000 − 1200
        self.assertTrue(lp.save_as('Тест'))
        w.go(5)
        rp = w.review_page
        self.assertEqual(rp.problems, [])
        self.assertEqual((rp.plan.launch, rp.plan.weapons), (BL.COPY, 'wtp5_loadout'))
        self.assertIn('Подвеска: изменена', rp.summary.toPlainText())
        self.assertTrue(rp.write())
        self.assertTrue(os.path.isfile(os.path.join(self.game, 'content', 'pkg_local', 'gameData', 'flightModels',
                                                    'fm', 'wtp5_b1.blk')))
        meta = I.installed(self.app)['b1']['meta']
        self.assertTrue(meta['loadout']['weightless'])
        w.go(1)
        lp.reset()
        self.assertIsNone(lp.loadout())
        self.assertTrue(lp.load_saved('Тест'))
        self.assertTrue(lp.loadout().weightless)
        self.assertTrue(lp.delete_saved('Тест'))

    def test_legacy_in_window(self):
        w = self.window()
        w.vehicles_page.select('c1')
        lp = w.loadout_page
        self.assertEqual(lp.points(), [])                           # c1_default — пустой пресет
        self.assertTrue(lp.apply_template('c1_bombs'))
        self.assertEqual([p[0] for p in lp.points()], [1, 2])
        lp.select_pylon(2)
        lp.ensure_catalog()
        lp.set_mode('any')
        lp.find.setText('big')
        self.assertTrue(lp.choose(lp.options[0].payload))
        self.assertEqual(lp.lo.legacy, {2: BIG})
        w.go(5)
        self.assertEqual(w.review_page.problems, [])

    def test_catalog_loads_in_background(self):
        """Замечание пользователя 26.10: «Любое оружие игры» вешало окно. Каталог собирается в фоне, пока — полоска."""
        import shutil as sh
        sh.rmtree(os.path.join(self.app, 'cache'), ignore_errors=True)        # без кэша — настоящая сборка
        w = self.window()
        w.vehicles_page.select('b1')
        lp = w.loadout_page
        lp.catalog, lp.loader = None, None
        lp.set_mode('any')
        if lp.catalog is None:
            self.assertTrue(lp.loading.isVisibleTo(lp))
            self.assertFalse(lp.options_area.isVisibleTo(lp))
        lp.loader.wait()
        for _ in range(20):
            self.qapp.processEvents()
        self.assertIsNotNone(lp.catalog)
        self.assertFalse(lp.loading.isVisibleTo(lp))
        lp.find.setText('big')
        self.assertEqual([c.title for c in lp.options], ['Большая бомба'])

    def test_group_filter_resets_on_new_query(self):
        """Выбран класс «бомбы», новый запрос без бомб — показать найденное, а не «Ничего не найдено»."""
        w = self.window()
        w.vehicles_page.select('b1')
        lp = w.loadout_page
        lp.ensure_catalog()
        lp.select_pylon(2)
        lp.set_mode('any')
        lp.all_weapons.setChecked(True)
        lp.find.setText('big')
        lp._set_group('bomb')
        self.assertEqual([c.title for c in lp.options], ['Большая бомба'])
        lp.find.setText('aim-9x')
        self.assertIn('ЗУР AIM-9X', [c.title for c in lp.options])
        self.assertEqual(lp.group_filter, '')

    def test_risky_weapon_asks_before_write(self):
        w = self.window()
        w.vehicles_page.select('b1')
        lp = w.loadout_page
        lp.ensure_catalog()
        lp.select_pylon(2)
        lp.set_mode('any')
        lp.all_weapons.setChecked(True)
        lp.find.setText('tank_gun')
        card = [c for c in lp.options if c.payload == ('weapon', TANKGUN)][0]
        self.assertIn('⚠', card.title + card.toolTip())
        lp.choose(card.payload)
        self.assertIn('упасть', lp.alerts.text())
        w.go(5)
        asked = []
        w.confirm = lambda title, text: asked.append(text) or False
        self.assertFalse(w.review_page.write())
        self.assertIn('может упасть', asked[0])

    def test_tank_has_no_loadout(self):
        w = self.window()
        w.vehicles_page.select('t1')
        self.assertIn('подвески нет', w.loadout_page.none_label.text())


@unittest.skipUnless(os.environ.get('WTP_DATAMINE'), 'нужен WTP_DATAMINE=<клон датамайна>')
class TestLoadoutDatamine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='wtp_lo_dm_')
        cls.src = S.open_source(datamine=os.environ['WTP_DATAMINE'])
        cls.vehicles, _ = X.load_index(cls.src, os.path.join(cls.tmp, 'cache'))
        cls.cat = L.load_catalog(cls.src, os.path.join(cls.tmp, 'cache'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_vehicle_and_weapon_searchable(self):
        """Сплошная проверка поиска (замечание пользователя 26.10: «nasam», «aim-9x»): каждая машина с оружием
        находится как носитель по русскому, английскому и внутреннему имени и отдаёт всё своё оружие; каждое оружие
        находится по своим названиям; каждая машина находится поиском техники."""
        import collections
        own = collections.defaultdict(set)
        for w in self.cat:
            for c in w['carriers']:
                own[c].add(w['path'])
        bad = []
        for v in self.vehicles:
            for field in ('ru', 'en', 'name'):
                if not v[field]:
                    continue
                if v not in X.search(self.vehicles, v[field]):
                    bad.append(('техника', field, v['name']))
                mine = own.get(v['name'].lower())
                if mine:
                    ws, cs = L.search_weapons(self.cat, self.vehicles, v[field])
                    if v['name'] not in [c['name'] for c in cs] or not mine <= {w['path'] for w in ws}:
                        bad.append(('носитель', field, v['name']))
        for w in self.cat:
            for field in ('ru', 'en', 'stem'):
                if w[field] and w['path'] not in {x['path'] for x in L.search_weapons(
                        self.cat, self.vehicles, w[field], pylon_only=False)[0]}:
                    bad.append(('оружие', field, w['stem']))
        self.assertEqual(bad, [])

    def test_a26b_weightless_fab_as_rounds_18_31(self):
        v = X.find(self.vehicles, 'a-26b')
        lo = L.Loadout(slots={4: {'weapon': 'gameData/Weapons/BombGuns/su_fab9000.blk', 'sample': '1000lbs_int',
                                  'count': 1}}, weightless=True)
        plan = BL.stock_plan(self.src, v, False, loadout=lo, catalog=self.cat)
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        fm = dict(plan.files)['content/pkg_local/gameData/flightModels/fm/wtp5_a-26b.blk']
        self.assertIn('"@override:EmptyMass":r=925.0', fm)          # 10 332 − 9 407, проверено в игре

    def test_every_stock_preset_is_stock(self):
        bad = []
        for v in self.vehicles:
            if v['kind'] not in ('air', 'heli'):
                continue
            py = L.read_pylons(self.src.load(v['file']))
            for name, _path in py.presets:
                try:
                    lo = L.from_preset(self.src, py, name)
                except ValueError:
                    continue                     # файл пресета не из пар slot/preset (готовый список Weapon)
                if L.stock_preset_of(self.src, py, lo) != name:
                    bad.append((v['name'], name))
        self.assertEqual(bad, [])

    def test_custom_builds_for_all_slot_aircraft(self):
        """Каждый самолёт/вертолёт новой схемы: на первом пилоне — первое оружие его же первого варианта как
        «чужое» (новый вариант слота) + невесомая, если можно. Сборка и модель правок — 0 ошибок."""
        errors, n = [], 0
        for v in self.vehicles:
            if v['kind'] not in ('air', 'heli'):
                continue
            py = L.read_pylons(self.src.load(v['file']))
            slots = [s for s in py.pylon_slots if s.variants and s.variants[0].weapons]
            if py.scheme != 'slots' or not slots:
                continue
            s = slots[0]
            lo = L.Loadout(slots={s.index: {'weapon': s.variants[0].weapons[0].get('blk'),
                                            'sample': s.variants[0].name}})
            lo.weightless = not any(lvl == 'refuse' for lvl, _t in L.summarize(
                self.src, py, L.Loadout(lo.base, dict(lo.slots), weightless=True), self.cat).warnings)
            plan = BL.stock_plan(self.src, v, False, loadout=lo, catalog=self.cat)
            problems = BL.verify_plan(self.src, plan)
            n += 1
            if problems:
                errors.append((v['name'], problems[:3]))
        self.assertGreater(n, 800)
        self.assertEqual(errors, [])

    def test_custom_builds_for_all_legacy_aircraft(self):
        """Каждая машина старой схемы: первый пресет со списком Weapon, на точке 1 — то же оружие (замена blk,
        как A-20G в 19-м круге). Сборка и модель правок — 0 ошибок."""
        errors, n = [], 0
        for v in self.vehicles:
            if v['kind'] not in ('air', 'heli'):
                continue
            py = L.read_pylons(self.src.load(v['file']))
            if py.scheme != 'legacy':
                continue
            base = next((name for name, _p in py.presets
                         if (L.legacy_weapons(self.src, py, name) or [None])[0] is not None
                         and L.legacy_weapons(self.src, py, name)[0].get('blk')), None)
            if base is None:
                continue
            lo = L.Loadout(base, legacy={1: L.legacy_weapons(self.src, py, base)[0].get('blk')})
            plan = BL.stock_plan(self.src, v, False, loadout=lo, catalog=self.cat)
            problems = BL.verify_plan(self.src, plan)
            n += 1
            if problems:
                errors.append((v['name'], problems[:3]))
        self.assertGreater(n, 400)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()

