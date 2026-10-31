"""Сверка модели @override (wtlib.blk.resolve_file) с тем, что игра написала в лог на реальных файлах.

Случай 1 — файл 4.7 userVehicles/ussr_t_80bvm.blk (бэкап 20261011_155631/files/f0). Игра 11.10 15:52:47:
  [E] cannot find param <shotFreq> (ordinal 1) for override in file …/userVehicles/ussr_t_80bvm.blk
  [F] FATAL ERROR: BLK invalid speedYaw (type real) value in line 11 … '360.0 "@override:speedPitch":r=100.0'
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib import blk as B  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402

GAME = os.path.expandvars(r'%LOCALAPPDATA%\WarThunder')
BACKUP = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon\backups\20261011_155631\files\f0')


def loader():
    aces = Vromfs(os.path.join(GAME, 'aces.vromfs.bin'))
    rd = B.BinaryReader.for_vromfs(aces)

    def load(path):
        p = path.replace('#/develop/gameBase/', '').lower()
        data = aces.get(p)
        if data is None:
            raise FileNotFoundError(path)
        return rd.parse(data)
    return load


def main():
    with open(BACKUP, encoding='utf-8') as f:
        text = f.read()
    log = []
    fatal = None
    try:
        B.resolve_file(text, loader(), log)
    except B.ApplyFatal as e:
        fatal = str(e)
    print('лог модели:')
    for s in log:
        print('   ', s)
    print('вылет модели:', fatal)
    ok = (any('cannot find param <shotFreq> (ordinal 1)' in s for s in log)
          and fatal is not None and fatal.startswith('BLK invalid speedYaw (type r) value in line 11'))
    print('СОВПАДАЕТ С ЛОГОМ ИГРЫ' if ok else 'НЕ СОВПАДАЕТ')

    # Случай 2 — наши тестовые копии wtp5t_* (make_test_missions.py): ошибок быть не должно,
    # ссылки на пусковые SAMP/T должны смениться.
    import make_test_missions as M
    problems = M.check_against_game(GAME, M.CASES)  # заодно собирает модификации и запекание (_bake)
    if problems:
        print('генератор не совпадает с игрой:', problems)
        return 1
    load = loader()
    bad = 0
    separate = [c for c in M.CASES if c['id'] in M.SEPARATE_IDS]
    for rel, text in M.plan(M.STANDARD_CASES) + M.plan(separate):
        if not rel.startswith('content/'):
            continue
        log2 = []
        res = B.resolve_file(text, load, log2)
        sp = res.block('supportPlanes')
        extra = ' пусковые: %s' % [p.get('class') for p in sp.blocks] if sp and 'fcs' in rel else ''
        if rel.endswith('/fm/wtp5t_a-26b_r23_takeoff.blk'):
            mass = res.block('Mass')
            takeoff = mass.get('Takeoff') if mass else None
            empty = mass.get('EmptyMass') if mass else None
            extra += ' Takeoff=%s EmptyMass=%s' % (takeoff, empty)
            bad += 0 if takeoff == 16324.0 and empty == 10332.0 else 1
        if '/fm/wtp5t_a-26b_r24_' in rel:
            field = 'Power' if 'main_power' in rel else 'Power0'
            section = 'Main' if field == 'Power' else 'Compressor'
            expected = 2998.5 if field == 'Power' else 3000.0
            values = [res.block('EngineType%d' % i).block(section).get(field) for i in (0, 1)]
            extra += ' %s=%s' % (field, values)
            bad += 0 if values == [expected, expected] else 1
        # 26-й круг: копия РЛС — у каждого режима range = сток × scale; копия самолёта ссылается на копию РЛС
        for c in M.CASES:
            if not c.get('_sensor'):
                continue
            cfg = M.SENSOR_COPIES[c['sensor_copy']]
            if rel.endswith('/' + M.copy_path(cfg['sensor']).split('/')[-1]):
                got = {t.name: t.get(cfg['field']) for t in res.block('transivers').blocks}
                want = {mode: new for mode, _old, new in c['_sensor'][2]}
                extra += ' %s: %s' % (cfg['field'], got)
                bad += 0 if all(got.get(k) == v for k, v in want.items()) else 1
            elif rel.endswith('/%s%s%s.blk' % (M.PREFIX, c['unit'].lower(), c.get('suffix', ''))):
                refs = [s.get('blk') for s in res.block('sensors').blocks if s.name == 'sensor']
                extra += ' РЛС: %s' % refs[0]
                bad += 0 if refs[0] == M.copy_path(cfg['sensor']) and len(refs) == len(set(refs)) else 1
        # 13-й круг: копия орудия — донор добавлен, правка дошла; копия машины ссылается на копию орудия
        for c in M.CASES:
            gc = c.get('gun_copy')
            if not gc or not c.get('_gun'):
                continue
            gname = M.gun_copy_name(c['_gun'])
            if rel.endswith('/' + gname):
                for sname, _src in gc.get('shells', []):
                    extra += ' %s: %s' % (sname, 'есть' if res.block(sname) else 'НЕТ')
                    bad += 0 if res.block(sname) else 1
                for path, value in gc.get('edits', []):
                    node = res
                    for part in path.split('/')[:-1]:
                        node = node.block(part) if node else None
                    got = node.get(path.split('/')[-1]) if node else None
                    extra += ' %s=%s' % (path.split('/')[-1], got)
                    bad += 0 if got == value else 1
            elif rel.endswith('/%s%s%s.blk' % (M.PREFIX, c['unit'].lower(), c.get('suffix', ''))):
                ref = res.block('commonWeapons').block('Weapon').get('blk')
                extra += ' орудие: %s' % ref
                bad += 0 if ref.endswith('/' + gname) else 1
        # 15-й круг: копия пресета — часть подвесов на копии файла оружия, остальные стоковые
        refs = [w.get('blk') or '' for w in res.blocks if w.name == 'Weapon']
        if '/weaponPresets/' + M.PREFIX in rel and any('/' + M.PREFIX in r for r in refs):
            # Пресеты с копией оружия из 15-го круга; новые контрольные пресеты оставляют стоковые ссылки.
            n = sum('/' + M.PREFIX in r for r in refs)
            extra += ' подвесов на копии: %d из %d' % (n, len(refs))
            bad += 0 if 0 < n < len(refs) else 1
        if rel.endswith('/flightModels/%sa-20g.blk' % M.PREFIX):
            extra += ' пресеты: %s' % [p.get('blk').split('/')[-1] for p in res.block('weapon_presets').blocks
                                         if M.PREFIX in (p.get('blk') or '')]
        if rel.endswith('/fm/wtp5t_a-26b_mass_2t.blk'):
            got = res.block('Mass').get('EmptyMass')
            extra += ' EmptyMass=%s' % got
            bad += 0 if got == 8332.0 else 1
        if rel.endswith('/fm/wtp5t_a-26b_r20_comp.blk'):
            got = res.block('Mass').get('EmptyMass')
            extra += ' EmptyMass=%s' % got
            bad += 0 if got == 925.0 else 1
        if rel.endswith('/BombGuns/wtp5t_r20_su_fab9000_light.blk'):
            got = res.block('bomb').get('mass')
            extra += ' bomb/mass=%s' % got
            bad += 0 if got == 5000.0 else 1
        if rel.endswith('/BombGuns/wtp5t_r21_su_fab9000_internal.blk'):
            good = (res.get('external') is False and res.block('bomb').get('mass') == 9407.0
                    and abs(res.block('bomb').get('dragCx') - 0.154) < 0.001)
            extra += ' external=no, масса и dragCx штатные: %s' % good
            bad += 0 if good else 1
        if rel.endswith('/flightModels/wtp5t_a-26b_r20_light.blk'):
            slot = [s for s in res.block('WeaponSlots').blocks
                    if s.name == 'WeaponSlot' and s.get('index') == 4][0]
            variant = [p for p in slot.blocks if p.name == 'WeaponPreset'
                       and p.get('name') == M.PREFIX + 'r20_fab_light_bay']
            refs20 = [w.get('blk') for p in variant for w in p.blocks if w.name == 'Weapon']
            good = (len(refs20) == 1 and refs20[0].endswith('/wtp5t_r20_su_fab9000_light.blk'))
            extra += ' лёгкая ФАБ в отсеке: %s' % good
            bad += 0 if good else 1
        if rel.endswith('/flightModels/wtp5t_a-26b_r21_internal.blk'):
            slot = [s for s in res.block('WeaponSlots').blocks
                    if s.name == 'WeaponSlot' and s.get('index') == 4][0]
            variant = [p for p in slot.blocks if p.name == 'WeaponPreset'
                       and p.get('name') == M.PREFIX + 'r21_fab_bay']
            refs21 = [w.get('blk') for p in variant for w in p.blocks if w.name == 'Weapon']
            good = (len(refs21) == 1 and refs21[0].endswith('/wtp5t_r21_su_fab9000_internal.blk'))
            extra += ' ФАБ external=no в отсеке: %s' % good
            bad += 0 if good else 1
        if rel.endswith('/weaponPresets/wtp5t_a-20g_a20_same.blk'):
            weapons = [w for w in res.blocks if w.name == 'Weapon']
            extra += ' Weapon=%d hideNodes=%s' % (len(weapons), bool(res.block('hideNodes')))
            bad += 0 if len(weapons) == 4 and res.block('hideNodes') else 1
        if rel.endswith('/weaponPresets/wtp5t_a-20g_a20_swap.blk'):
            weapons = [w for w in res.blocks if w.name == 'Weapon']
            refs = [(w.get('blk') or '').lower() for w in weapons]
            good = (len(refs) == 4 and refs[0].endswith('us_500lb_anm64a1.blk')
                    and all(r.endswith('us_250lb_anm57.blk') for r in refs[1:]))
            extra += ' первая 500 lb, остальные 250 lb: %s' % good
            bad += 0 if good else 1
        if rel.endswith('/flightModels/wtp5t_mi_28nm_r19.blk'):
            names = {p.get('name') for p in res.block('weapon_presets').blocks}
            good = {M.PREFIX + 'mi28_same', M.PREFIX + 'mi28_one'} <= names
            extra += ' свои пресеты Ми-28: %s' % good
            bad += 0 if good else 1
        # 17-й круг: свои варианты слотов и свои пресеты в итоговой копии самолёта
        for cfg in (M.AIR_LOADOUTS['A26'],):
            if rel.endswith('/flightModels/%sa-26b.blk' % M.PREFIX) or rel.endswith('/flightModels/%sa-26b_wl.blk' % M.PREFIX):
                ws = res.block('WeaponSlots')
                got = {s.get('index'): [p.get('name') for p in s.blocks if p.name == 'WeaponPreset']
                       for s in ws.blocks if s.name == 'WeaponSlot'}
                if rel.endswith('_wl.blk'):
                    extra += ' fmFile=%s' % res.get('fmFile')
                    bay = [p for p in got.get(4, []) if p == M.PREFIX + 'fab9000_bay']
                    sl = [s for s in ws.blocks if s.name == 'WeaponSlot' and s.get('index') == 4][0]
                    v = [p for p in sl.blocks if p.name == 'WeaponPreset' and p.get('name') == M.PREFIX + 'fab9000_bay']
                    extra += ' подвесов ФАБ в отсеке: %d' % len([w for w in v[0].blocks if w.name == 'Weapon']) if v else ''
                for index, _s, new, _b, *_k in cfg['variants']:
                    ok = new in got.get(index, [])
                    extra += ' слот %d: %s %s' % (index, new, 'есть' if ok else 'НЕТ')
                    bad += 0 if ok else 1
                have = [p.get('name') for p in res.block('weapon_presets').blocks]
                for pname in cfg['presets']:
                    extra += ' %s: %s' % (pname, 'есть' if pname in have else 'НЕТ')
                    bad += 0 if pname in have else 1
        # 31-й круг: копии A-26B с ФАБ ссылаются на общую копию ЛМ, в своём варианте слота 4 — один подвес ФАБ
        r31 = {'comp': (M.R31_FAB, None), 'bombcx': (M.R31_FAB_CX, None), 'wcx': (M.R31_FAB, 0.2)}
        name = rel.split('/')[-1]
        if '/fm/' not in rel and name.startswith(M.PREFIX + 'a-26b_r31_') and name[len(M.PREFIX + 'a-26b_r31_'):-4] in r31:
            blk, cx = r31[name[len(M.PREFIX + 'a-26b_r31_'):-4]]
            preset = {M.R31_FAB_CX: 'fab_cx', M.R31_FAB: 'fab_wcx' if cx else 'fab'}[blk]
            sl = [x for x in res.block('WeaponSlots').blocks if x.name == 'WeaponSlot' and x.get('index') == 4][0]
            v = [x for x in sl.blocks if x.get('name') == M.PREFIX + 'r31_%s_bay' % preset]
            ws = [w for w in v[0].blocks if w.name == 'Weapon'] if v else []
            good = (res.get('fmFile') == M.R31_FM[1][len('gameData/flightModels/'):] and len(ws) == 1
                    and ws[0].get('blk') == blk and ws[0].get('dragCx') == cx)
            extra += ' fmFile=%s подвес %s dragCx=%s %s' % (res.get('fmFile'), ws[0].get('blk') if ws else None,
                                                            ws[0].get('dragCx') if ws else None, 'ок' if good else 'НЕТ')
            bad += 0 if good else 1
        print('   %s: ошибок %d%s' % (rel.split('/')[-1], len(log2), extra))
        bad += len(log2)
    # 27–31-й круги: правки в файле копии машины, мишени или копии файла (29–30-й: СПО, ракета, орудие; 31-й: ЛМ, ФАБ) — итоговое
    # значение каждого поля = заданному, всё остальное дерево = сток (соседние ratio не задеты), контрольные копии
    # (стрелок 28-го круга, контроль 54) без @override
    print('27–31-й круги, итог правок:')
    bad += M.report_unit_edits(load, M.plan(separate), separate)
    return 0 if ok and not bad else 1


if __name__ == '__main__':
    sys.exit(main())
