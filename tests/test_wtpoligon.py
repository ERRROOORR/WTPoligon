"""Каркас программы (этап 1): индекс, модель правок, сборка стоковой миссии, запись/откат, CLI — без игры.

Источник — маленький поддельный клон датамайна во временной папке. Прогон по настоящему датамайну
(вся техника игры) — при WTP_DATAMINE=<клон>: python -m wtpoligon --datamine <клон> check-all.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from wtpoligon import build as BL  # noqa: E402
from wtpoligon import cli  # noqa: E402
from wtpoligon import edits as E  # noqa: E402
from wtpoligon import hangar as H  # noqa: E402
from wtpoligon import install as I  # noqa: E402
from wtpoligon import targets as T  # noqa: E402
from wtpoligon.game import blk as B  # noqa: E402
from wtpoligon.game import index as X  # noqa: E402
from wtpoligon.game import source as S  # noqa: E402

GUN = 'gameData/Weapons/groundModels_weapons/t1_gun.blk'
UNITS = {
    'units/tankmodels/t1': {
        'weapon_presets': {'preset': [{'name': 't1_default', 'blk': 'gameData/Weapons/t1_default.blk'}]},
        'commonWeapons': {'Weapon': {'blk': GUN, 'trigger': 'gunner0'}},
        'VehiclePhys': {'mechanics': {'gearRatios': {'ratio': [-2.5, 3.0, 2.5, 2.0, 1.5]}, 'maxBrakeForce': 1000.0}},
        'supportPlanes': {'plane': [{'class': 'tankModels/t1_launcher'}, {'class': 'tankModels/t1_launcher'}]},
        'modifications': {
            'smoke_mod': {'effects': {'commonWeapons': {'Weapon': [
                {'blk': GUN, 'trigger': 'gunner0'}, {'blk': 'gameData/Weapons/smoke.blk', 'trigger': 'gunner4'}]}}},
            'tool_kit': {}}},
    'units/tankmodels/t1_launcher': {'weapon_presets': {'preset': {'name': 't1_launcher_default'}}},
    'flightmodels/a1': {'fmFile': 'fm/a1.blk', 'weapon_presets': {'preset': [
        {'name': 'a1_bombs'}, {'name': 'a1_default'}]}},
    'flightmodels/h1': {'weapon_presets': {'preset': [{'name': 'h1_rockets'}]},
                        'bailout': {'seat': ['seat_01', {'part': 'seat_02'}]}},
    'units/ships/s1': {'weapon_presets': {'preset': {'name': 's1_default'}}},
}
UNITTAGS = {'t1': {'type': 'tank', 'tags': {'country_ussr': True, 'tank': True}},
            't1_launcher': {'type': 'tank', 'tags': {'country_ussr': True}},
            'a1': {'type': 'aircraft'}, 'H1': {'type': 'helicopter'}, 's1': {'type': 'ship'},
            'inf': {'type': 'human'}, 'ghost': {'type': 'tank'}}
WPCOST = {'t1': {'country': 'country_ussr', 'rank': 3, 'economicRankHistorical': 6},
          'a1': {'country': 'country_usa', 'rank': 1, 'economicRankHistorical': 0}}
GMODS = {'modifications': {'smoke_mod': {'effects': {}}, 'tool_kit': {'effects': {'repairSpeed': 1.5}}}}
CSV = ('"<ID|readonly|noverify>";"<English>";"<Russian>";"<Comments>"\n'
       '"t1_shop";"T-1";"Т-1";\n"a1_0";"A-1";"А-1";\n')


def make_datamine(root):
    def put(rel, obj):
        p = os.path.join(root, *rel.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(obj, f) if not isinstance(obj, str) else f.write(obj)
    for rel, obj in UNITS.items():
        put('aces.vromfs.bin_u/gamedata/%s.blkx' % rel, obj)
    put('aces.vromfs.bin_u/gamedata/weapons/groundmodels_weapons/t1_gun.blkx', {'shell': {'mass': 1.0}})
    # мишени сценария — стоковая техника игры (в реестр не входят, только файлы)
    for _set, classes, _ok in T.TARGET_SETS.values():
        for cls in classes:
            put('aces.vromfs.bin_u/gamedata/units/tankmodels/%s.blkx' % cls, {'weapon_presets': {}})
    for _t, cls, _s, _r in T.AIR_BOTS.values():
        put('aces.vromfs.bin_u/gamedata/flightmodels/%s.blkx' % cls, {'weapon_presets': {}})
    put('char.vromfs.bin_u/config/unittags.blkx', UNITTAGS)
    put('char.vromfs.bin_u/config/wpcost.blkx', WPCOST)
    put('char.vromfs.bin_u/config/modifications.blkx', GMODS)
    put('lang.vromfs.bin_u/lang/units.csv', CSV)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='wtp_test_')
        self.dm = os.path.join(self.tmp, 'dm')
        self.app = os.path.join(self.tmp, 'app')
        self.game = os.path.join(self.tmp, 'game')
        os.makedirs(self.game)
        make_datamine(self.dm)
        self.src = S.open_source(datamine=self.dm)
        self.vehicles, self.stats = X.load_index(self.src, os.path.join(self.app, 'cache'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def v(self, name):
        return X.find(self.vehicles, name)

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = cli.main(['--datamine', self.dm, '--app-dir', self.app] + list(args))
        return code, out.getvalue()


class TestPackage(Base):
    def test_wtlib_is_package_module(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
        from wtlib import blk as old_blk
        from wtlib.vromfs import Vromfs
        from wtpoligon.game import vromfs
        self.assertIs(old_blk, B)
        self.assertIs(Vromfs, vromfs.Vromfs)


class TestIndex(Base):
    def test_kinds_names_and_skips(self):
        names = {v['name']: v for v in self.vehicles}
        self.assertEqual(sorted(names), ['H1', 'a1', 's1', 't1', 't1_launcher'])
        self.assertEqual([names[n]['kind'] for n in ('t1', 'a1', 'H1', 's1')], ['tank', 'air', 'heli', 'ship'])
        self.assertEqual(names['H1']['file'], 'gameData/flightModels/h1.blk')
        self.assertEqual((names['t1']['country'], names['t1']['rank'], names['t1']['br']), ('ussr', 3, 3.0))
        self.assertEqual((names['t1']['en'], names['t1']['ru']), ('T-1', 'Т-1'))
        self.assertEqual(names['a1']['ru'], 'А-1')
        self.assertEqual(names['t1_launcher']['country'], 'ussr')   # страна из тегов, если нет в wpcost
        self.assertFalse(names['s1']['shop'])
        self.assertEqual(self.stats['no_file'], ['ghost'])
        self.assertEqual(self.stats['skipped_type'], 1)

    def test_cache_and_refresh(self):
        cache = os.path.join(self.app, 'cache')
        path = os.path.join(cache, 'index_datamine.json')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        data['vehicles'] = data['vehicles'][:1]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        self.assertEqual(len(X.load_index(self.src, cache)[0]), 1)           # та же подпись — из кэша
        self.assertEqual(len(X.load_index(self.src, cache, refresh=True)[0]), 5)
        data['signature'] = 'другая версия игры'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(dict(data, vehicles=[]), f)
        self.assertEqual(len(X.load_index(self.src, cache)[0]), 5)           # игра обновилась — пересбор

    def test_search(self):
        self.assertEqual([v['name'] for v in X.search(self.vehicles, 'т-1')], ['t1', 't1_launcher'])  # точное первым
        self.assertEqual([v['name'] for v in X.search(self.vehicles, 'т1 лаунчер')][:1], ['t1_launcher'])
        self.assertEqual([v['name'] for v in X.search(self.vehicles, 'а1')], ['a1'])      # русская «а» = латинская
        self.assertEqual(X.find(self.vehicles, 'h1')['name'], 'H1')
        self.assertEqual([v['name'] for v in X.search(self.vehicles, kind='ship')], ['s1'])

    def test_no_duplicates_in_index(self):
        files = [v['file'].lower() for v in self.vehicles]
        self.assertEqual(len(files), len(set(files)))


class TestEdits(Base):
    def test_make_edit_and_text(self):
        u = self.src.load('gameData/units/tankModels/t1.blk')
        e = E.make_edit(u, 'gameData/units/tankModels/t1.blk', 'VehiclePhys/mechanics/gearRatios/ratio[5]', 0.75)
        self.assertEqual((e.type, e.stock, e.value, e.source), ('r', 1.5, 0.75, 'manual'))
        e2 = E.make_edit(u, e.file, 'VehiclePhys/mechanics/maxBrakeForce', 2000, source='derived:tank_brake')
        self.assertEqual(e2.value, 2000.0)
        text, problems = E.edits_text(u, [e, e2])
        self.assertEqual(problems, [])
        log = []
        res = B.resolve_file('include "#/develop/gameBase/%s"\n%s' % (e.file, text), self.src.loader(), log)
        self.assertEqual(log, [])
        mech = res.block('VehiclePhys').block('mechanics')
        self.assertEqual([p[2] for p in mech.block('gearRatios').params], [-2.5, 3.0, 2.5, 2.0, 0.75])
        self.assertEqual(mech.get('maxBrakeForce'), 2000.0)
        self.assertEqual(E.Edit.from_dict(e.to_dict()), e)

    def test_type_checks_and_stock_drift(self):
        u = self.src.load('gameData/units/tankModels/t1.blk')
        with self.assertRaises(KeyError):
            E.make_edit(u, 'f', 'VehiclePhys/nope', 1.0)
        with self.assertRaises(TypeError):
            E.make_edit(u, 'f', 'VehiclePhys/mechanics/maxBrakeForce', 'много')
        with self.assertRaises(ValueError):
            E.Edit('f', 'p', 'r', 1.0, 2.0, source='magic')
        drift = E.Edit('f', 'VehiclePhys/mechanics/maxBrakeForce', 'r', 999.0, 5.0)
        wrong_type = E.Edit('f', 'VehiclePhys/mechanics/maxBrakeForce', 'i', 1000, 5)
        text, problems = E.edits_text(u, [drift, wrong_type])
        self.assertEqual(text, '')
        self.assertEqual(len(problems), 2)

    def test_point_types_written_as_blk(self):
        tree = B.parse_text('a{ pos:p3=1, 2, 3 }\n')
        text = E.override_path(tree, 'a/pos', (4.0, 5.5, 6.0))
        self.assertIn('"@override:pos":p3=4.0, 5.5, 6.0', text)
        log = []
        B.apply_patch(tree, B.parse_text(text), log)
        self.assertEqual((log, tree.block('a').get('pos')), ([], (4.0, 5.5, 6.0)))


class TestBuild(Base):
    def test_default_preset(self):
        self.assertEqual(BL.default_preset(self.src.load('gameData/flightModels/a1.blk'), 'a1', 'air'), 'a1_default')
        self.assertEqual(BL.default_preset(self.src.load('gameData/flightModels/h1.blk'), 'H1', 'heli'), 'h1_rockets')
        self.assertEqual(BL.default_preset(self.src.load('gameData/units/ships/s1.blk'), 's1', 'ship'), '')

    def test_hangar_plan_only_mission(self):
        plan = BL.stock_plan(self.src, self.v('t1'), True)
        self.assertEqual([r for r, _ in plan.files], ['UserMissions/WTPoligon5/wtp5_t1.blk'])
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        m = B.parse_text(plan.files[0][1])
        self.assertEqual(m.block('mission_settings').block('mission').get('name'), 'wtp5_t1')
        player = m.block('units').block('tankModels')
        self.assertEqual((player.get('unit_class'), player.get('weapons')), ('t1', 't1_default'))
        self.assertEqual([p[2] for p in player.params if p[0] == 'modification'], ['smoke_mod', 'tool_kit'])

    def test_copy_plan(self):
        plan = BL.stock_plan(self.src, self.v('t1'), False)
        files = dict(plan.files)
        copy = 'content/pkg_local/gameData/units/tankModels/wtp5_t1.blk'
        launcher = 'content/pkg_local/gameData/units/tankModels/wtp5_t1__t1_launcher.blk'
        self.assertEqual(sorted(files), sorted([launcher, copy, 'UserMissions/WTPoligon5/wtp5_t1.blk']))
        body = [x for x in files[copy].splitlines() if not x.startswith('//')]
        self.assertEqual(body[0], 'include "#/develop/gameBase/gameData/units/tankModels/t1.blk"')
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        res = B.resolve_file(files[copy], self.src.loader(), [])
        guns = [w.get('blk') for w in res.block('commonWeapons').blocks]
        self.assertEqual(guns, [GUN, 'gameData/Weapons/smoke.blk'])       # дымы перенесены (8-й круг)
        self.assertEqual([p.get('class') for p in res.block('supportPlanes').blocks],
                         ['tankModels/wtp5_t1__t1_launcher'] * 2)
        self.assertTrue(any('tool_kit' in n for n in plan.notes))         # потеря — показана
        unit = B.parse_text(files['UserMissions/WTPoligon5/wtp5_t1.blk']).block('units').block('tankModels')
        self.assertEqual(unit.get('unit_class'), 'wtp5_t1')

    def test_kinds_spawn(self):
        for name, block, level in (('a1', 'armada', 'levels/air_denmark.bin'), ('H1', 'armada', 'levels/air_denmark.bin'),
                                   ('s1', 'ships', 'levels/avn_fiji.bin')):
            for hangar in (True, False):
                plan = BL.stock_plan(self.src, self.v(name), hangar)
                self.assertEqual(BL.verify_plan(self.src, plan), [], name)
                m = B.parse_text(dict(plan.files)[plan.mission_path])
                self.assertEqual(m.block('mission_settings').block('mission').get('level'), level)
                self.assertIsNotNone(m.block('units').block(block))
        heli = B.parse_text(dict(BL.stock_plan(self.src, self.v('H1'), False).files)[
            'UserMissions/WTPoligon5/wtp5_h1.blk'])
        self.assertEqual(heli.block('units').block('objectGroups').get('name'), 'airfield_high')

    def test_mission_text_roundtrip(self):
        """Корректность текстового BLK: разбор и запись обратно дают тот же текст."""
        for name in ('t1', 'a1', 'H1', 's1'):
            for hangar in (True, False):
                for rel, text in BL.stock_plan(self.src, self.v(name), hangar).files:
                    if rel.startswith('UserMissions'):
                        body = text.split('\n', 1)[1]
                        self.assertEqual(B.to_text(B.parse_text(body)), body, rel)

    def test_verify_catches_errors(self):
        plan = BL.stock_plan(self.src, self.v('t1'), False)
        plan.weapons = 'no_such_preset'
        self.assertTrue(any('пресета' in p for p in BL.verify_plan(self.src, plan)))
        plan = BL.stock_plan(self.src, self.v('t1'), False)
        rel, text = plan.files[1]
        plan.files[1] = (rel, text + '"@override:noSuchParam":r=1\n')
        self.assertTrue(any('cannot find param' in p for p in BL.verify_plan(self.src, plan)))
        plan = BL.stock_plan(self.src, self.v('t1'), False)
        plan.files[1] = (rel, text.replace('/t1.blk', '/t9.blk'))
        self.assertTrue(any('include' in p for p in BL.verify_plan(self.src, plan)))
        plan = BL.stock_plan(self.src, self.v('t1'), False)
        plan.files[0] = ('content/pkg_local/gameData/units/tankModels/userVehicles/us_m2a4.blk', plan.files[0][1])
        self.assertTrue(any('wtp5_' in p for p in BL.verify_plan(self.src, plan)))

    def test_check_all(self):
        errors, counts = cli.check_all(self.src, self.vehicles)
        self.assertEqual(errors, [])
        self.assertEqual(sum(counts.values()), 10)


class TestInstall(Base):
    def files(self, hangar=False, name='t1'):
        return BL.stock_plan(self.src, self.v(name), hangar).files

    def test_check_paths(self):
        ok = [('content/pkg_local/gameData/units/tankModels/wtp5_x.blk', ''),
              ('UserMissions/WTPoligon5/wtp5_x.blk', ''), ('UserMissions/WTPoligon5/usr_wtp5_x.csv', '')]
        self.assertEqual(I.check_paths(ok), [])
        for rel in ('content/pkg_local/gameData/units/tankModels/us_m2a4.blk',
                    'content/pkg_local/gameData/units/tankModels/userVehicles/us_m2a4.blk',
                    'content/pkg_local/levels/wtp5_x.blk', 'UserMissions/Ask3lad/wtp5_x.blk',
                    'UserMissions/WTPoligon5/other.blk', 'UserMissions/WTPoligon5/sub/wtp5_x.blk',
                    'content/pkg_local/gameData/../config.blk', '/etc/wtp5_x.blk', 'C:/wtp5_x.blk', 'config.blk',
                    'content\\pkg_local\\gameData\\wtp5_x.blk'):
            self.assertTrue(I.check_paths([(rel, '')]), rel)
        self.assertTrue(I.check_paths(ok + ok[:1]))

    def test_install_reinstall_uninstall(self):
        foreign = os.path.join(self.game, 'content/pkg_local/gameData/units/tankModels/userVehicles/us_m2a4.blk')
        os.makedirs(os.path.dirname(foreign))
        with open(foreign, 'w', encoding='utf-8') as f:
            f.write('чужой мод\n')
        ok, _ = I.install(self.game, self.app, 't1', self.files(), {'unit': 't1'})
        self.assertTrue(ok)
        for rel, text in self.files():
            with open(os.path.join(self.game, rel), encoding='utf-8') as f:
                self.assertEqual(f.read(), text)
        self.assertEqual(I.installed(self.app)['t1']['meta']['unit'], 't1')
        # переустановка «из ангара»: копии машины и пусковых убираются, миссия обновляется (старая — в бэкап)
        ok, report = I.install(self.game, self.app, 't1', self.files(hangar=True))
        self.assertTrue(ok, report)
        self.assertFalse(os.path.exists(os.path.join(self.game, self.files()[1][0])))
        self.assertTrue(os.path.isdir(os.path.join(self.app, 'installs', 't1', 'backups')))
        I.uninstall(self.game, self.app, 't1')
        self.assertFalse(os.path.exists(os.path.join(self.game, 'UserMissions', 'WTPoligon5')))
        self.assertEqual(I.installed(self.app), {})
        with open(foreign, encoding='utf-8') as f:
            self.assertEqual(f.read(), 'чужой мод\n')                     # чужой мод не тронут

    def test_foreign_or_changed_file_blocks_everything(self):
        rel = self.files()[1][0]
        full = os.path.join(self.game, rel)
        os.makedirs(os.path.dirname(full))
        with open(full, 'w', encoding='utf-8') as f:
            f.write('не наш\n')
        ok, report = I.install(self.game, self.app, 't1', self.files())
        self.assertFalse(ok)
        self.assertTrue(any('чужой' in s for s in report))
        self.assertFalse(os.path.exists(os.path.join(self.game, 'UserMissions')))   # отказ до первой записи
        os.remove(full)
        self.assertTrue(I.install(self.game, self.app, 't1', self.files())[0])
        with open(full, 'a', encoding='utf-8') as f:
            f.write('// правка руками\n')
        ok, report = I.install(self.game, self.app, 't1', self.files(hangar=True))
        self.assertTrue(ok)                                                # выпал из набора, но изменён — оставлен
        self.assertTrue(any('изменён' in s for s in report))
        self.assertFalse(I.install(self.game, self.app, 't1', self.files())[0])   # перезаписать изменённый — нет
        report = I.uninstall(self.game, self.app, 't1')
        self.assertTrue(os.path.exists(full))                             # изменённый после записи — оставлен
        self.assertTrue(any('изменён' in s for s in report))

    def test_other_application_file_refused(self):
        self.assertTrue(I.install(self.game, self.app, 't1', self.files())[0])
        ok, report = I.install(self.game, self.app, 'other', self.files()[:1])
        self.assertFalse(ok)
        self.assertTrue(any('применением t1' in s for s in report))

    def test_dry_run_writes_nothing(self):
        ok, _ = I.install(self.game, self.app, 't1', self.files(), dry_run=True)
        self.assertTrue(ok)
        self.assertEqual(os.listdir(self.game), [])
        self.assertEqual(I.installed(self.app), {})

    def test_bad_app_id(self):
        with self.assertRaises(ValueError):
            I.install(self.game, self.app, '../x', self.files())


class TestCli(Base):
    def test_list_mission_install_status_uninstall(self):
        code, out = self.run_cli('list', '--kind', 'tank')
        self.assertEqual(code, 0)
        self.assertIn('Т-1', out)
        code, out = self.run_cli('mission', 't1', '--show')
        self.assertEqual(code, 0, out)
        self.assertIn('копия не из ангара', out)
        self.assertIn('0 ошибок', out)
        code, out = self.run_cli('install', 't1')
        self.assertEqual(code, 2)                                          # датамайн: куда писать — не задано
        code, out = self.run_cli('hangar', 'add', 'Т-1')
        self.assertEqual((code, H.load(self.app)), (0, {'t1': True}))
        code, out = self.run_cli('install', 't1', '--target', self.game)
        self.assertEqual(code, 0, out)
        self.assertIn('из ангара', out)
        self.assertTrue(os.path.isfile(os.path.join(self.game, 'UserMissions/WTPoligon5/wtp5_t1.blk')))
        code, out = self.run_cli('status')
        self.assertIn('на месте 1', out)
        code, out = self.run_cli('uninstall', '--all')
        self.assertEqual(code, 0)
        self.assertEqual(os.listdir(self.game), ['UserMissions'])
        self.assertEqual(I.installed(self.app), {})

    def test_check_all_and_ambiguous(self):
        code, out = self.run_cli('check-all')
        self.assertEqual(code, 0, out)
        self.assertIn('ошибок: 0', out)
        code, out = self.run_cli('mission', 't1_')
        self.assertEqual(code, 0)                                          # единственное совпадение
        code, out = self.run_cli('mission', 't')
        self.assertEqual(code, 2)
        self.assertIn('подходит', out)

    def test_no_game(self):
        out = io.StringIO()
        env = {k: os.environ.pop(k) for k in ('WTP_GAME', 'LOCALAPPDATA') if k in os.environ}
        try:
            with contextlib.redirect_stderr(out), contextlib.redirect_stdout(out):
                code = cli.main(['--app-dir', self.app, '--game', self.game, 'list'])
        finally:
            os.environ.update(env)
        self.assertEqual(code, 2)
        self.assertIn('Игра не найдена', out.getvalue())


class TestTargets(Base):
    def mission(self, name, sc=None, hangar=True):
        plan = BL.stock_plan(self.src, self.v(name), hangar, scenario=sc)
        return plan, B.parse_text(dict(plan.files)[plan.mission_path]) if plan.files else None

    def test_defaults_by_kind(self):
        self.assertEqual(T.default_scenario('tank'), T.Scenario('firing_range', ground='soviet'))
        self.assertEqual(T.default_scenario('air'), T.Scenario('air_denmark', air='mig15'))
        self.assertEqual(T.default_scenario('heli'), T.Scenario('denmark_heli_airfield'))
        self.assertEqual(T.default_scenario('ship'), T.Scenario('avn_fiji'))
        for kind in X.KIND_NAMES:
            self.assertEqual(T.check_scenario(T.default_scenario(kind), kind), [], kind)

    def test_generator_uses_same_targets(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
        import make_test_missions as G
        self.assertIs(G.TARGETS, T.TARGETS)
        # над полигоном — проверенные точки генератора; на земле — зоны тест-драйва, куда шаблон переносит мишени
        self.assertEqual(T.ground_targets('soviet', spawn='firing_range_air'), T.TARGETS)
        self.assertNotEqual(T.ground_targets('soviet'), T.TARGETS)

    def test_firing_range_targets_ahead(self):
        """Баг этапа 2: мишени были на нашем берегу слева. Теперь — зоны tank_spawn_area тест-драйва, игрок лицом
        к ним (поворот t1_player01), каждая мишень лбом к игроку."""
        px, pz = (1724.72, 1788.19)
        fx, fz = T.PLAYER_TURN[0][0], T.PLAYER_TURN[0][2]
        for dist in T.GROUND_DISTANCES:
            for set_key in T.TARGET_SETS:
                for i, (_n, _c, tm) in enumerate(T.ground_targets(set_key, dist)):
                    dx, dz = tm[3][0] - px, tm[3][2] - pz
                    d = (dx * dx + dz * dz) ** 0.5
                    # впереди в ±60°; шестая на тест-драйве — зона 07 справа (как в стоке), только не позади
                    self.assertGreater((dx * fx + dz * fz) / d, 0.0 if i == 5 and not dist else 0.5, (set_key, dist))
                    self.assertGreater(-(tm[0][0] * dx + tm[0][2] * dz) / d, 0.9)       # лбом к игроку
        self.assertEqual(T.ground_targets('soviet')[0][2][3], (1949.84, 217.241, 1784.36))   # tank_spawn_area01
        self.assertEqual(T.ground_targets('soviet')[5][2][3], (2021.45, 229.623, 1053.23))   # 07 для target_tank07
        _plan, m = self.mission('t1')
        player = [u for u in m.block('units').blocks if u.get('name') == 'player'][0]
        self.assertEqual(tuple(player.get('tm')[:3]), T.PLAYER_TURN)
        self.assertEqual(tuple(m.block('areas').block('player_spawn').get('tm')[0]), (9.39692, 0.0, 3.4202))

    def test_ground_targets_in_mission(self):
        plan, m = self.mission('t1')
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        tanks = [u for u in m.block('units').blocks if u.name == 'tankModels' and u.get('name') != 'player']
        self.assertEqual([u.get('unit_class') for u in tanks], T.TARGET_SETS['soviet'][1])
        for u in tanks:
            self.assertEqual((u.block('props').get('army'), u.block('props').get('attack_type')), (2, 'dont_aim'))
        trig = m.block('triggers').block('targets_restore')
        self.assertEqual(trig.block('actions').blocks[0].get('time'), 5.0)
        self.assertEqual(sum(a.name == 'unitRestore' for a in trig.block('actions').blocks), len(tanks))
        self.assertFalse(any('Не проверено' in n for n in plan.notes))

    def test_ground_distance_and_set(self):
        sc = T.Scenario('firing_range', ground='nato', ground_distance=1200)
        pts = [tm[3] for _n, _c, tm in T.ground_targets('nato', 1200)]
        player = (1724.72, 217.534, 1788.19)
        cx, cz = sum(p[0] for p in pts) / len(pts), sum(p[2] for p in pts) / len(pts)
        self.assertAlmostEqual(((cx - player[0]) ** 2 + (cz - player[2]) ** 2) ** 0.5, 1200, delta=1)
        plan, m = self.mission('t1', sc)
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        self.assertTrue(any('📄' in n and '1200' in n for n in plan.notes))
        self.assertIn('us_m1_abrams', [u.get('unit_class') for u in m.block('units').blocks])

    def test_air_target_radar_and_respawn(self):
        sc = T.Scenario('air_denmark', air='mig23', air_distance=30000, air_radar=True)
        plan, m = self.mission('a1', sc)
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        bot = [u for u in m.block('units').blocks if u.get('name') == 'air_target'][0]
        self.assertEqual((bot.get('unit_class'), bot.block('props').get('use_search_radar')), ('mig_23m', True))
        self.assertAlmostEqual(bot.get('tm')[3][0] - 24362.7, 30000, places=1)
        init = m.block('triggers').block('init').block('actions')
        props = [a for a in init.blocks if a.name == 'unitSetProperties' and a.get('object') == 'air_target'][0]
        self.assertEqual((props.get('cannotShoot'), props.get('useSearchRadar')), (True, True))
        self.assertIsNotNone(m.block('triggers').block('air_target_restore'))
        self.assertIsNotNone(m.block('wayPoints').block('air_target_way'))

    def test_heli_air_target_not_in_ground(self):
        plan, m = self.mission('H1', T.Scenario('denmark_heli_airfield', air='tu4'))
        self.assertEqual(BL.verify_plan(self.src, plan), [])
        bot = [u for u in m.block('units').blocks if u.get('name') == 'air_target'][0]
        self.assertGreaterEqual(bot.get('tm')[3][1], T.AIR_MIN_ALT)

    def test_bad_choices_refused(self):
        for kind, sc, word in (('tank', T.Scenario('air_denmark'), 'вида'),
                               ('tank', T.Scenario('firing_range', air='mig15'), 'воздушной'),
                               ('air', T.Scenario('air_denmark', ground='soviet'), 'наземных'),
                               ('air', T.Scenario('air_denmark', air='mig15', air_radar=True), 'РЛС'),
                               ('tank', T.Scenario('firing_range', ground='soviet', ground_distance=5), 'дистанция')):
            self.assertTrue(any(word in p for p in T.check_scenario(sc, kind)), (sc, word))
        plan = BL.stock_plan(self.src, self.v('t1'), True, scenario=T.Scenario('air_denmark'))
        self.assertEqual(plan.files, [])
        self.assertTrue(BL.verify_plan(self.src, plan))

    def test_verify_catches_shooting_or_missing_target(self):
        plan = BL.stock_plan(self.src, self.v('t1'), True)
        rel, text = plan.files[0]
        plan.files[0] = (rel, text.replace('attack_type:t="dont_aim"', 'attack_type:t="fire_at_will"'))
        self.assertTrue(any('стрелять' in p for p in BL.verify_plan(self.src, plan)))
        plan.files[0] = (rel, text.replace('"ussr_t_62"', '"no_such_tank"'))
        self.assertTrue(any('no_such_tank' in p for p in BL.verify_plan(self.src, plan)))

    def test_cli_scenario_options(self):
        code, out = self.run_cli('scenarios')
        self.assertEqual(code, 0)
        self.assertIn('mig23', out)
        code, out = self.run_cli('mission', 'a1', '--air-target', 'mig23', '--radar', '--air-distance', '30')
        self.assertEqual(code, 0, out)
        self.assertIn('РЛС включена', out)
        code, out = self.run_cli('mission', 'a1', '--spawn', 'firing_range_air', '--targets', 'ww2',
                                 '--air-target', 'none', '--show')
        self.assertEqual(code, 0, out)
        self.assertIn('germ_pzkpfw_vi_ausf_h1_tiger', out)
        self.assertNotIn('air_target', out)
        code, out = self.run_cli('mission', 't1', '--targets', 'none', '--show')
        self.assertEqual(code, 0, out)
        self.assertNotIn('target_tank', out)
        code, out = self.run_cli('mission', 't1', '--air-target', 'mig15')
        self.assertEqual(code, 1)
        code, out = self.run_cli('install', 't1', '--target', self.game, '--targets', 'light')
        self.assertEqual(code, 0, out)
        self.assertEqual(I.installed(self.app)['t1']['meta']['scenario']['ground'], 'light')


@unittest.skipUnless(os.environ.get('WTP_DATAMINE'), 'WTP_DATAMINE=<клон датамайна> — прогон по всей технике')
class TestWholeDatamine(unittest.TestCase):
    def test_check_all_whole_game(self):
        src = S.open_source(datamine=os.environ['WTP_DATAMINE'])
        vehicles, _ = X.build_index(src)
        errors, counts = cli.check_all(src, vehicles)
        self.assertEqual(errors[:20], [])
        self.assertGreater(sum(counts.values()), 6000)


if __name__ == '__main__':
    unittest.main()
