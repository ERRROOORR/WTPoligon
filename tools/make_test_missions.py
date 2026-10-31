"""Тестовые миссии для чек-листов в docs/research/.

Каждый пункт: миссия и, при необходимости, отдельная копия машины/оружия/ЛМ.
Безопасность (ТЗ §10):
  - пишем только в UserMissions/WTPoligonTest/ и content/pkg_local/gameData/, имена с префиксом wtp5t_
    (не пересекаются с файлами 4.7 `wtp_*` и чужих модов);
  - чужой файл (нет в нашем манифесте) или наш, но изменённый после записи, не перезаписываем — останавливаемся;
  - свой файл перед перезаписью копируем в бэкап;
  - откат (--remove) удаляет только свои файлы с неизменным содержимым.
Манифест и бэкапы: %LOCALAPPDATA%\\WTPoligon5\\test_missions\\.

Запуск:  .venv\\Scripts\\python tools\\make_test_missions.py [--round19|…|--round32] [--dry-run] [--remove] [--game <папка игры>]
Без игры (облако): make_test_missions.py --round26|…|--round32 --datamine <клон датамайна> — только показать файлы
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wtlib import blk as B  # noqa: E402
from wtlib import mods as M_mods  # noqa: E402
from wtlib.vromfs import Vromfs  # noqa: E402
from wtpoligon import mission as MI  # noqa: E402  (путь к пакету добавляет wtlib)
from wtpoligon import install as I  # noqa: E402
from wtpoligon import targets as T  # noqa: E402
from wtpoligon.edits import (_path_part, merge_overrides, override_path, path_value,  # noqa: E402,F401
                             set_path_value, unit_edits)
from wtpoligon.install import (adopt_exact, load_manifest, restore_original, save_manifest, sha,  # noqa: E402,F401
                               write)
from wtpoligon.mission import AIRFIELDS, KINDS, SPAWNS, _restore, _tm, _trigger  # noqa: E402,F401

PREFIX = 'wtp5t_'
MISSION_DIR = 'UserMissions/WTPoligonTest'
APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions')
ROUND19_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round19')
ROUND20_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round20')
ROUND21_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round21')
ROUND22_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round22')
ROUND23_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round23')
ROUND24_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round24')
ROUND25_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round25')
ROUND26_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round26')
ROUND27_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round27')
ROUND28_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round28')
ROUND29_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round29')
ROUND30_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round30')
ROUND31_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round31')
ROUND32_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round32')
ROUND33_APP_DIR = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon5\test_missions_round33')

# KINDS, SPAWNS, AIRFIELDS и каркас миссии — wtpoligon/mission.py (общие с программой)

# мишени для проверки пробития (12-й круг) — как в стоковом тест-драйве testflight_era_tft.blk (firing_range):
# tankModels армии 2 на тех же точках (640–770 м от игрока); шаблон testFlight_template.blk при старте ставит им
# attack_type "dont_aim" (не стреляют) и возрождает после уничтожения
TARGETS = T.TARGETS   # wtpoligon/targets.py (общие с программой)

CASES = [
    {'id': 't1_tank', 'title': '1. Т-80БВМ под своим именем + запечённые модификации', 'kind': 'tank', 'unit': 'ussr_t_80bvm', 'bake': True,
     # подкалиберный 3БМ42 «Манго» — снаряд из модификации, у копии модификации не работают (modifications.md)
     'bullets': [('125mm_ussr_3BM42_APDS_FS', 20)], 'targets': True,
     'spawn': 'firing_range', 'mtype': 'testFlight', 'weapons': 'ussr_t_80bvm_default'},
    {'id': 't2_air', 'title': '2. Самолёт: F-15C Golden Eagle', 'kind': 'air', 'unit': 'f_15c_golden_eagle',
     'spawn': 'air_denmark', 'mtype': 'singleMission', 'weapons': 'f_15c_golden_eagle_aim_9m'},
    {'id': 't3_heli', 'title': '3. Вертолёт: Ми-28НМ', 'kind': 'heli', 'unit': 'mi_28nm',
     'spawn': 'denmark_heli_airfield', 'mtype': 'testFlight', 'weapons': 'mi_28nm_rocket_9M39'},
    {'id': 't4_ship', 'title': '4. Корабль: эсминец Fletcher', 'kind': 'ship', 'unit': 'us_destroyer_fletcher',
     'spawn': 'avn_fiji', 'mtype': 'testFlight', 'weapons': ''},
    {'id': 't5_uav', 'title': '5. Танк с БПЛА: CM-34', 'kind': 'tank', 'unit': 'cn_cm_34',
     'spawn': 'firing_range', 'mtype': 'testFlight', 'weapons': 'cn_cm_34_default',
     'modifications': ['tank_support_ucav']},
    # SAMP/T, а не IRIS-T SLM: IRIS-T у пользователя есть (по логу 12.10 шёл под настоящим именем без отказа),
    # а проверить нужно ЗРК не из ангара
    {'id': 't6_sam', 'title': '6. Составной ЗРК: SAMP/T', 'kind': 'tank', 'unit': 'fr_samp_t_fcs',
     'spawn': 'firing_range', 'mtype': 'testFlight', 'weapons': '',
     'launcher': 'fr_samp_t_launcher'},
    # контрольный опыт (3-й круг: клавиши дымов/огнетушителя/дальномера/тепловизора у копий не работают):
    # одна и та же машина из ангара пользователя (M1A1 выбирался в ангаре по логам) под настоящим именем и под своим.
    # Работает в 7 и не работает в 8 → причина в имени (справочник интерфейса), а не в миссии
    {'id': 't7_ctrl_real', 'title': '7. Контроль: M1A1 под настоящим именем', 'kind': 'tank',
     'unit': 'us_m1a1_abrams', 'spawn': 'firing_range', 'mtype': 'testFlight', 'weapons': 'us_m1a1_abrams_default',
     'real_name': True},
    {'id': 't8_ctrl_copy', 'title': '8. M1A1 под своим именем + запечённые модификации', 'kind': 'tank', 'bake': True,
     'unit': 'us_m1a1_abrams', 'spawn': 'firing_range', 'mtype': 'testFlight', 'weapons': 'us_m1a1_abrams_default'},
    # 5-й круг: справочники через pkg_local/config игра не подхватила (3509 машин) → своё имя неполноценно.
    # Проверка «в ангаре» срезает userVehicles/ и смотрит настоящее имя (лог 11.10) — возможно, интерфейс тоже.
    # 'donor' — машина из ангара пользователя, под чьим именем запускаем; 'unit' — содержимое (include).
    {'id': 't9_uv_own', 'title': '9. M1A1 через userVehicles + запечённые модификации', 'kind': 'tank', 'bake': True,
     'unit': 'us_m1a1_abrams', 'donor': 'us_m1a1_abrams', 'spawn': 'firing_range', 'mtype': 'testFlight',
     'weapons': 'us_m1a1_abrams_default'},
    {'id': 't10_uv_donor', 'title': '10. Т-80БВМ под видом LVT(A)(1) + запечённые модификации', 'kind': 'tank', 'bake': True,
     'unit': 'ussr_t_80bvm', 'donor': 'us_lvt_a_1', 'spawn': 'firing_range', 'mtype': 'testFlight',
     'weapons': 'ussr_t_80bvm_default'},
    {'id': 't11_uv_heli', 'title': '11. Ми-28НМ через userVehicles + тепловизор из модификации', 'kind': 'heli', 'bake': True,
     'unit': 'mi_28nm', 'donor': 'mi_28nm', 'spawn': 'denmark_heli_airfield', 'mtype': 'testFlight',
     'weapons': 'mi_28nm_rocket_9M39'},
    # 13-й круг (ammo_survey.md): копия основного орудия = include стокового + правки. Миссия 1 — контроль
    # (настоящий 3БМ42 пробивает все мишени). Правка: 3БМ42 слабее — у БОПС пробитие по Ланцу–Одерматту от рабочей
    # длины (640 → 150 мм даёт ~140 мм вместо ~580, по формуле WTFTD). Замена: DTW-125 из китайского орудия — блок
    # снаряда донора целиком (ammo_survey.md «Последствия»: bulletType тянет набор полей)
    {'id': 't12_gun_copy', 'title': '12. Т-80БВМ: копия орудия — 3БМ42 ослаблен + снаряд DTW-125 от другого орудия',
     'kind': 'tank', 'unit': 'ussr_t_80bvm', 'suffix': '_gun', 'bake': True, 'targets': True,
     'spawn': 'firing_range', 'mtype': 'testFlight', 'weapons': 'ussr_t_80bvm_default',
     'bullets': [('125mm_ussr_3BM42_APDS_FS', 20), ('125mm_china_DTW_APDS_FS', 20)],
     'gun_copy': {
         # 16-й круг (caching.md): 150 → 900 при запущенной игре — перечитывает ли игра изменённую копию орудия
         # (у бомбы — да). 900 мм по формуле WTFTD — ~800 мм пробития
         'edits': [('125mm_ussr_3BM42_APDS_FS/bullet/damage/kinetic/lanzOdermattWorkingLength', 900.0)],
         'shells': [('125mm_china_DTW_APDS_FS', 'gameData/Weapons/groundModels_weapons/125mm_l54_cn_user_cannon.blk')]}},
    # 14-й круг (ammo_survey.md, вопросы 1, 3–5): «Тигр» H1 — единственная пушка игры (88-мм KwK 36), у которой есть
    # APCBC и APCR с Демарром, HEAT и HE. 13 — контроль (стоковые снаряды), 14 — по одной правке на снаряд:
    # APCBC mass ×2 (Демарр из файла: 154 → 269 мм у дула), APCR damageMass ×2 (растёт ли — значит, считается масса
    # сердечника), HEAT armorPower 110 → 300, HE explosiveMass ×10 (кинетика та же, F уже 0.75; растёт фугасное)
    {'id': 't13_tiger_ctrl', 'title': '13. «Тигр» H1: контроль — стоковые снаряды', 'kind': 'tank',
     'unit': 'germ_pzkpfw_vi_ausf_h1_tiger', 'bake': True, 'targets': True,
     'spawn': 'firing_range', 'mtype': 'testFlight', 'weapons': 'germ_pzkpfw_VI_ausf_h1_tiger_default',
     'bullets': [('88mm_ger_kwk36_Pzgr_APCBC', 20), ('88mm_ger_kwk36_APCR', 20), ('88mm_ger_kwk36_HEAT', 20),
                 ('88mm_ger_kwk36_default_HE', 20)]},
    {'id': 't14_tiger_mod', 'title': '14. «Тигр» H1: правки снарядов — Демарр, APCR, кумулятив, фугас', 'kind': 'tank',
     'unit': 'germ_pzkpfw_vi_ausf_h1_tiger', 'suffix': '_gun', 'bake': True, 'targets': True,
     'spawn': 'firing_range', 'mtype': 'testFlight', 'weapons': 'germ_pzkpfw_VI_ausf_h1_tiger_default',
     'bullets': [('88mm_ger_kwk36_Pzgr_APCBC', 20), ('88mm_ger_kwk36_APCR', 20), ('88mm_ger_kwk36_HEAT', 20),
                 ('88mm_ger_kwk36_default_HE', 20)],
     'gun_copy': {'edits': [('88mm_ger_kwk36_Pzgr_APCBC/bullet/mass', 19.0),
                            ('88mm_ger_kwk36_APCR/bullet/damageMass', 4.0),
                            ('88mm_ger_kwk36_HEAT/bullet/cumulativeDamage/armorPower', 300.0),
                            ('88mm_ger_kwk36_default_HE/bullet/explosiveMass', 9.0)]}},
    # 15-й круг (ammo_survey.md, вопрос 6): бомба, ракета, торпеда на одной копии A-20G (старая схема weapon_presets).
    # Копия пресета: каждый второй Weapon с этим файлом ссылается на копию файла оружия с правкой, остальные — стоковые
    # (контроль в той же миссии). Ракета: force ×3 и ограничитель maxSpeed ×3 (иначе скорость упрётся в 260 м/с)
    {'id': 't15_a20_bombs', 'title': '15. A-20G: 4 бомбы 250 lb — 2-я и 4-я с ВВ ×10 и взрывом 1000 кг', 'kind': 'air', 'unit': 'a-20g',
     'spawn': 'firing_range_air', 'mtype': 'singleMission', 'weapons': 'a20g_4x250lb', 'targets': True,
     'weapon_copy': 'A20'},
    {'id': 't16_a20_rockets', 'title': '16. A-20G: 12 ракет M8 — каждая 2-я с тягой ×3', 'kind': 'air', 'unit': 'a-20g',
     'spawn': 'firing_range_air', 'mtype': 'singleMission', 'weapons': 'a-20g_12xbazooka', 'targets': True,
     'weapon_copy': 'A20'},
    {'id': 't17_a20_torpedo', 'title': '17. A-20G: 2 торпеды — 2-я со скоростью ×4', 'kind': 'air', 'unit': 'a-20g',
     'spawn': 'avn_fiji_air', 'mtype': 'singleMission', 'weapons': 'a20g_torpedo', 'weapon_copy': 'A20'},
]

# 17-й круг (pylons_survey.md): своя подвеска самолёта новой схемы (WeaponSlots). variants — новые варианты слотов
# (копия варианта-образца: узлы ShowNodes и параметры Weapon, без reqModification и запретов, с другим файлом
# оружия); presets — свои пресеты: файл со списком Weapon{slot, preset} + запись preset{} в копии самолёта
AIR_LOADOUTS = {
    'A26': {
        # (слот, образец, имя, файл оружия[, сколько Weapon образца оставить])
        'variants': [(2, '500lbs_wing_left_out', PREFIX + 'fab9000_l', 'gameData/Weapons/BombGuns/su_fab9000.blk'),
                     (6, '500lbs_wing_right_out', PREFIX + 'fab9000_r', 'gameData/Weapons/BombGuns/su_fab9000.blk'),
                     (4, '1000lbs_int', PREFIX + 'fab9000_bay', 'gameData/Weapons/BombGuns/su_fab9000.blk', 1)],
        'presets': {
            # всё слева: HVAR-left запрещает (BannedWeaponPreset) левые бомбы 2/3; слева ~925 кг при maxDisbalance 400
            PREFIX + 'a26_mix': [(1, 'hvar_x7_left'), (2, '500lbs_wing_left_out'), (3, '500lbs_wing_left_in'),
                                 (4, '1000lbs_int')],
            # чужое оружие на пилонах: 2 × ФАБ-9000 (9 407 кг) при maxloadMass 2500
            PREFIX + 'a26_fab': [(2, PREFIX + 'fab9000_l'), (6, PREFIX + 'fab9000_r')],
            # одна ФАБ-9000 в бомбоотсеке — по центру, без перекоса (18-й круг: невесомая подвеска)
            PREFIX + 'a26_bay': [(4, PREFIX + 'fab9000_bay')]}},
    'MI28': {
        'variants': [],
        'presets': {
            PREFIX + 'mi28_same': [(1, 'c8ko'), (2, 'c8ko'), (3, 'c8ko'), (4, 'c8ko')],
            PREFIX + 'mi28_one': [(1, 'c8ko')],
        }},
    'A26_R20': {
        'variants': [(4, '1000lbs_int', PREFIX + 'r20_fab_bay',
                      'gameData/Weapons/BombGuns/su_fab9000.blk', 1),
                     (4, '1000lbs_int', PREFIX + 'r20_fab_light_bay',
                      'gameData/Weapons/BombGuns/' + PREFIX + 'r20_su_fab9000_light.blk', 1)],
        'presets': {
            PREFIX + 'r20_fab': [(4, PREFIX + 'r20_fab_bay')],
            PREFIX + 'r20_fab_light': [(4, PREFIX + 'r20_fab_light_bay')],
        },
        'weapon_edits': [('gameData/Weapons/BombGuns/su_fab9000.blk',
                          'gameData/Weapons/BombGuns/' + PREFIX + 'r20_su_fab9000_light.blk',
                          'bomb/mass', 5000.0)],
    },
    'A26_R21': {
        'variants': [(4, '1000lbs_int', PREFIX + 'r21_fab_bay',
                      'gameData/Weapons/BombGuns/' + PREFIX + 'r21_su_fab9000_internal.blk', 1)],
        'presets': {PREFIX + 'r21_fab_internal': [(4, PREFIX + 'r21_fab_bay')]},
        'weapon_edits': [('gameData/Weapons/BombGuns/su_fab9000.blk',
                          'gameData/Weapons/BombGuns/' + PREFIX + 'r21_su_fab9000_internal.blk',
                          'external', False)],
    },
}

# 18-й круг (ТЗ §6.4 «невесомая подвеска»): отдельного множителя массы подвески в ЛМ нет (Mass: EmptyMass…,
# doesPayloadAffectCOG), а bomb/mass — масса самого боеприпаса (баллистика, пробитие) → как в 4.7 (feature_matrix
# 2.9): копия ЛМ с EmptyMass минус масса подвески выбранного пресета. Последствие: после сброса самолёт легче пустого
CASES += [
    {'id': 't20_a26_bay', 'title': '20. A-26B: ФАБ-9000 в бомбоотсеке — обычная масса (контроль)',
     'kind': 'air', 'unit': 'a-26b', 'spawn': 'firing_range_air', 'mtype': 'singleMission', 'targets': True,
     'loadout': 'A26', 'weapons': PREFIX + 'a26_bay'},
    {'id': 't21_a26_bay_wl', 'title': '21. A-26B: ФАБ-9000 в бомбоотсеке — невесомая подвеска (EmptyMass минус 9,4 т)',
     'kind': 'air', 'unit': 'a-26b', 'suffix': '_wl', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'targets': True, 'loadout': 'A26', 'weapons': PREFIX + 'a26_bay', 'weightless': True},
]


def payload_mass(u, cfg, preset, load):
    """Масса подвески пресета из AIR_LOADOUTS: боеприпас (bomb/rocket/torpedo/bullet mass × bullets) + Weapon/mass
    + mass верхнего уровня файла оружия (держатель). Возвращает (кг, [(файл, кг)])."""
    slots = {s.get('index'): s for s in u.block('WeaponSlots').blocks if s.name == 'WeaponSlot'}
    variants = {(v[0], v[2]): v for v in cfg.get('variants', [])}
    total, parts = 0.0, []
    for slot, name in cfg['presets'][preset]:
        if (slot, name) in variants:
            v = variants[(slot, name)]
            sample = [p for p in slots[slot].blocks if p.name == 'WeaponPreset' and p.get('name') == v[1]][0]
            weapons = [w for w in sample.blocks if w.name == 'Weapon'][:v[4] if len(v) > 4 else None]
            refs = [(v[3], w) for w in weapons]
        else:
            p = [p for p in slots[slot].blocks if p.name == 'WeaponPreset' and p.get('name') == name][0]
            refs = [(w.get('blk'), w) for w in p.blocks if w.name == 'Weapon']
        for blk, w in refs:
            t = load(blk)
            ammo = next((t.block(k) for k in ('bomb', 'rocket', 'torpedo', 'bullet') if t and t.block(k)), None)
            m = (ammo.get('mass') or 0.0) * (w.get('bullets') or 1) if ammo else 0.0
            m += (w.get('mass') or 0.0) + ((t.get('mass') or 0.0) if t else 0.0)
            total += m
            parts.append((blk.split('/')[-1], m))
    return total, parts

CASES += [
    {'id': 't18_a26_mix', 'title': '18. A-26B: своя подвеска — HVAR слева + левые бомбы + 1000 lb, правое крыло пустое',
     'kind': 'air', 'unit': 'a-26b', 'spawn': 'firing_range_air', 'mtype': 'singleMission', 'targets': True,
     'loadout': 'A26', 'weapons': PREFIX + 'a26_mix'},
    {'id': 't19_a26_fab', 'title': '19. A-26B: на пилонах 2 и 6 — ФАБ-9000 (чужое оружие, 18,8 т)',
     'kind': 'air', 'unit': 'a-26b', 'spawn': 'firing_range_air', 'mtype': 'singleMission', 'targets': True,
     'loadout': 'A26', 'weapons': PREFIX + 'a26_fab'},
]

# 19-й круг: изолируем влияние EmptyMass без сопротивления ФАБ-9000; затем проверяем старый пресет A-20G
# и свой пресет Ми-28НМ на отдельной копии: существующий userVehicles без манифеста не перезаписывать.
CASES += [
    {'id': 't22_a26_mass_ctrl', 'title': '22. A-26B без подвески — стоковая масса', 'kind': 'air',
     'unit': 'a-26b', 'suffix': '_mass_ctrl', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'weapons': ''},
    {'id': 't23_a26_mass_2t', 'title': '23. A-26B без подвески — EmptyMass минус 2000 кг', 'kind': 'air',
     'unit': 'a-26b', 'suffix': '_mass_2t', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'weapons': '', 'fm_empty_delta': -2000.0},
    {'id': 't24_a20_stock', 'title': '24. A-20G: стоковые 4 × 250 lb', 'kind': 'air',
     'unit': 'a-20g', 'suffix': '_legacy', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'weapons': 'a20g_4x250lb', 'legacy_loadout': 'A20_CHECK', 'shared_title': 'A-20G: сток и свои пресеты'},
    {'id': 't25_a20_same', 'title': '25. A-20G: свой точный повтор 4 × 250 lb', 'kind': 'air',
     'unit': 'a-20g', 'suffix': '_legacy', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'weapons': PREFIX + 'a20_same', 'legacy_loadout': 'A20_CHECK', 'shared_title': 'A-20G: сток и свои пресеты'},
    {'id': 't26_a20_swap', 'title': '26. A-20G: свой пресет — первая бомба 500 lb, остальные 250 lb',
     'kind': 'air', 'unit': 'a-20g', 'suffix': '_legacy', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'weapons': PREFIX + 'a20_swap', 'legacy_loadout': 'A20_CHECK', 'shared_title': 'A-20G: сток и свои пресеты'},
    {'id': 't27_mi28_stock', 'title': '27. Ми-28НМ: стоковый пресет С-8КО', 'kind': 'heli',
     'unit': 'mi_28nm', 'suffix': '_r19', 'spawn': 'denmark_heli_airfield',
     'mtype': 'testFlight', 'weapons': 'mi_28nm_rocket_c_8_ko', 'loadout': 'MI28',
     'shared_title': 'Ми-28НМ: сток и свои пресеты'},
    {'id': 't28_mi28_same', 'title': '28. Ми-28НМ: свой точный повтор С-8КО', 'kind': 'heli',
     'unit': 'mi_28nm', 'suffix': '_r19', 'spawn': 'denmark_heli_airfield',
     'mtype': 'testFlight', 'weapons': PREFIX + 'mi28_same', 'loadout': 'MI28',
     'shared_title': 'Ми-28НМ: сток и свои пресеты'},
    {'id': 't29_mi28_one', 'title': '29. Ми-28НМ: С-8КО только на слоте 1', 'kind': 'heli',
     'unit': 'mi_28nm', 'suffix': '_r19', 'spawn': 'denmark_heli_airfield',
     'mtype': 'testFlight', 'weapons': PREFIX + 'mi28_one', 'loadout': 'MI28',
     'shared_title': 'Ми-28НМ: сток и свои пресеты'},
]
ROUND19_IDS = {'t22_a26_mass_ctrl', 't23_a26_mass_2t', 't24_a20_stock', 't25_a20_same',
               't26_a20_swap', 't27_mi28_stock', 't28_mi28_same', 't29_mi28_one'}

# 20-й круг: независимые копии A-26B с одинаковой точкой старта.
CASES += [
    {'id': 't30_a26_r20_empty', 'title': '30. A-26B: без бомбы, контроль', 'kind': 'air',
     'unit': 'a-26b', 'suffix': '_r20_empty', 'spawn': 'firing_range_air', 'mtype': 'singleMission', 'weapons': ''},
    {'id': 't31_a26_r20_fab', 'title': '31. A-26B: ФАБ-9000, масса 9407 кг', 'kind': 'air',
     'unit': 'a-26b', 'suffix': '_r20_fab', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'loadout': 'A26_R20', 'weapons': PREFIX + 'r20_fab'},
    {'id': 't32_a26_r20_comp', 'title': '32. A-26B: ФАБ-9000, EmptyMass минус 9407 кг', 'kind': 'air',
     'unit': 'a-26b', 'suffix': '_r20_comp', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'loadout': 'A26_R20', 'weapons': PREFIX + 'r20_fab', 'fm_empty_delta': -9407.0},
    {'id': 't33_a26_r20_light', 'title': '33. A-26B: копия ФАБ-9000, масса бомбы 5000 кг', 'kind': 'air',
     'unit': 'a-26b', 'suffix': '_r20_light', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'loadout': 'A26_R20', 'weapons': PREFIX + 'r20_fab_light'},
]
ROUND20_IDS = {c['id'] for c in CASES if c['id'].startswith(('t30_', 't31_', 't32_', 't33_'))}

# 21-й круг: одна новая миссия; контроль 31 уже измерен, его не перезаписываем и не повторяем.
CASES += [
    {'id': 't34_a26_r21_internal', 'title': '34. A-26B: ФАБ-9000, external=no', 'kind': 'air',
     'unit': 'a-26b', 'suffix': '_r21_internal', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
     'loadout': 'A26_R21', 'weapons': PREFIX + 'r21_fab_internal'},
]
ROUND21_IDS = {'t34_a26_r21_internal'}

# 22-й круг: настоящее имя вертолёта сохраняет HUD, но новый пресет под своим именем
# игра ищет в стоковом mi_28nm.blk и не видит из userVehicles. Контроль со штатным именем.
CASES += [
    {'id': 't35_mi28_r22_hud', 'title': '35. Ми-28НМ: штатный пресет С-8КО через userVehicles',
     'kind': 'heli', 'unit': 'mi_28nm', 'existing_user_vehicle': True,
     'spawn': 'denmark_heli_airfield', 'mtype': 'testFlight',
     'weapons': 'mi_28nm_rocket_c_8_ko'},
]
ROUND22_IDS = {'t35_mi28_r22_hud'}
ROUND22_ADOPT_PATH = 'content/pkg_local/gameData/flightModels/userVehicles/mi_28nm.blk'

# 23-й круг: изолированная проверка, участвует ли Mass/Takeoff в физике A-26B.
# EmptyMass, части, топливо и боеприпасы в обеих миссиях остаются стоковыми.
CASES += [
    {'id': 't36_a26_r23_control', 'title': '36. A-26B без подвески — контроль Takeoff',
     'kind': 'air', 'unit': 'a-26b', 'suffix': '_r23_control', 'spawn': 'firing_range_air',
     'mtype': 'singleMission', 'weapons': ''},
    {'id': 't37_a26_r23_takeoff', 'title': '37. A-26B без подвески — Takeoff минус 2000 кг',
     'kind': 'air', 'unit': 'a-26b', 'suffix': '_r23_takeoff', 'spawn': 'firing_range_air',
     'mtype': 'singleMission', 'weapons': '', 'fm_takeoff_delta': -2000.0},
]
ROUND23_IDS = {'t36_a26_r23_control', 't37_a26_r23_takeoff'}

# 24-й круг: два возможных регулятора мощности поршневого двигателя.
# Контроль без подвески — уже проверенная миссия 36 (375→475 км/ч за 30 с).
CASES += [
    {'id': 't38_a26_r24_main_power', 'title': '38. A-26B: Main/Power обоих двигателей ×1,5',
     'kind': 'air', 'unit': 'a-26b', 'suffix': '_r24_main_power', 'spawn': 'firing_range_air',
     'mtype': 'singleMission', 'weapons': '', 'fm_power_field': 'Main/Power'},
    {'id': 't39_a26_r24_comp_power', 'title': '39. A-26B: Compressor/Power0 обоих двигателей ×1,5',
     'kind': 'air', 'unit': 'a-26b', 'suffix': '_r24_comp_power', 'spawn': 'firing_range_air',
     'mtype': 'singleMission', 'weapons': '', 'fm_power_field': 'Compressor/Power0'},
]
ROUND24_IDS = {'t38_a26_r24_main_power', 't39_a26_r24_comp_power'}

# 25-й круг: локализация копии машины без правки WarThunder/lang или config.blk.
CASES += [
    {'id': 't40_a26_r25_loc', 'title': '40. A-26B: локализация из usr_*.csv',
     'kind': 'air', 'unit': 'a-26b', 'suffix': '_r25_loc', 'spawn': 'firing_range_air',
     'mtype': 'singleMission', 'weapons': '', 'mission_file_stem': 'wtp5t_t40_a26_r25_loc',
     'loc_name_key': 'wtp5t_r25_loc_probe'},
]
ROUND25_IDS = {'t40_a26_r25_loc'}

# 26-й круг (sensors_survey.md «Подготовка 26-го круга»): дальность обнаружения РЛС копией файла сенсора.
# Копия = include стока + "@override" поля field у каждого режима transivers/<режим> (тип — как в стоке);
# копия самолёта меняет только ссылку sensors/sensor[n]/blk. Общий стоковый файл сенсора не трогаем.
SENSOR_COPIES = {
    'APG63_R26': {'sensor': 'gameData/sensors/us_an_apg_63_v_3.blk', 'field': 'range', 'scale': 0.1},
}
# Самолёт-мишень для РЛС, как flight_target*_high в test_flight_unit_template.blk: армия 2, cannotShoot,
# маршрут unitSetRoute. Стоит на 30 км впереди игрока (игрок смотрит вдоль +X) на той же высоте и летит к точке
# старта игрока — сближение лоб в лоб. 30 км < шкалы 37 км (scopeRangeSets/common/range1, включается при старте)
AIR_TARGETS = {
    'r26_mig15': {'name': 'radar_target', 'unit_class': 'mig-15bis_ns23', 'distance': 30000.0, 'speed': 500.0},
}
CASES += [
    {'id': 't41_f15_r26_ctrl', 'title': '41. F-15C: РЛС AN/APG-63(V)3 стоковая — контроль, МиГ-15 в 30 км',
     'kind': 'air', 'unit': 'f_15c_golden_eagle', 'suffix': '_r26_ctrl', 'spawn': 'air_denmark',
     'mtype': 'singleMission', 'weapons': 'f_15c_golden_eagle_aim_9m', 'air_target': 'r26_mig15'},
    {'id': 't42_f15_r26_radar', 'title': '42. F-15C: копия РЛС, дальность обнаружения ×0,1 — МиГ-15 в 30 км',
     'kind': 'air', 'unit': 'f_15c_golden_eagle', 'suffix': '_r26_radar', 'spawn': 'air_denmark',
     'mtype': 'singleMission', 'weapons': 'f_15c_golden_eagle_aim_9m', 'air_target': 'r26_mig15',
     'sensor_copy': 'APG63_R26'},
]
ROUND26_IDS = {'t41_f15_r26_ctrl', 't42_f15_r26_radar'}

# 27-й круг (ground_naval_plan.md, Н1–Н4): одна правка физики в файле копии машины на миссию.
# unit_edits — [(путь, стоковое, новое)]: путь как в override_path (повторы — name[n]); стоковое сверяется по
# игре/датамайну перед записью (обновление игры → отказ, а не правка «не того»). Контроль — та же машина без правок,
# без запекания, тот же пресет и точка. Контроль Fletcher — уже установленная миссия 4 (t4_ship, та же копия без
# правок, та же точка avn_fiji): иначе кругу нужно 7 миссий при пределе 6
CASES += [
    {'id': 't43_t80_r27_ctrl', 'title': '43. Т-80БВМ: контроль физики — без правок',
     'kind': 'tank', 'unit': 'ussr_t_80bvm', 'suffix': '_r27_ctrl', 'spawn': 'firing_range',
     'mtype': 'testFlight', 'weapons': 'ussr_t_80bvm_default'},
    {'id': 't44_t80_r27_power', 'title': '44. Т-80БВМ: мощность ×2 (1250 → 2500 л. с.)',
     'kind': 'tank', 'unit': 'ussr_t_80bvm', 'suffix': '_r27_power', 'spawn': 'firing_range',
     'mtype': 'testFlight', 'weapons': 'ussr_t_80bvm_default',
     'unit_edits': [('VehiclePhys/engine/horsePowers', 1250.0, 2500.0)]},
    {'id': 't45_t80_r27_mass', 'title': '45. Т-80БВМ: масса ×2 (Empty 44,5 → 89 т)',
     'kind': 'tank', 'unit': 'ussr_t_80bvm', 'suffix': '_r27_mass', 'spawn': 'firing_range',
     'mtype': 'testFlight', 'weapons': 'ussr_t_80bvm_default',
     'unit_edits': [('VehiclePhys/Mass/Empty', 44500.0, 89000.0)]},
    {'id': 't46_tiger_r27_ctrl', 'title': '46. «Тигр» H1: контроль физики — без правок',
     'kind': 'tank', 'unit': 'germ_pzkpfw_vi_ausf_h1_tiger', 'suffix': '_r27_ctrl', 'spawn': 'firing_range',
     'mtype': 'testFlight', 'weapons': 'germ_pzkpfw_VI_ausf_h1_tiger_default'},
    {'id': 't47_tiger_r27_gear', 'title': '47. «Тигр» H1: 8-я передача ×0,5 (ratio 0.687 → 0.3435)',
     'kind': 'tank', 'unit': 'germ_pzkpfw_vi_ausf_h1_tiger', 'suffix': '_r27_gear', 'spawn': 'firing_range',
     'mtype': 'testFlight', 'weapons': 'germ_pzkpfw_VI_ausf_h1_tiger_default',
     'unit_edits': [('VehiclePhys/mechanics/gearRatios/ratio[13]', 0.687, 0.3435)]},
    {'id': 't48_fletcher_r27_speed', 'title': '48. Fletcher: maxSpeed ×2 (18 → 36)',
     'kind': 'ship', 'unit': 'us_destroyer_fletcher', 'suffix': '_r27_speed', 'spawn': 'avn_fiji',
     'mtype': 'testFlight', 'weapons': '',
     'unit_edits': [('ShipPhys/engines/maxSpeed', 18.0, 36.0)]},
]
ROUND27_IDS = {'t43_t80_r27_ctrl', 't44_t80_r27_power', 't45_t80_r27_mass', 't46_tiger_r27_ctrl',
               't47_tiger_r27_gear', 't48_fletcher_r27_speed'}
ROUND27_CONTROLS = {'t48_fletcher_r27_speed': 't4_ship'}  # опыт -> уже установленная миссия-контроль

# 28-й круг (armor_crew.md, вопросы 1, 3; живучесть экипажа): правки брони, экипажа и боеукладки в копии мишени.
# Стрелок — «Тигр» H1 (копия без правок, штатный PzGr 39 APCBC, как миссия 13); мишени — два «Тигра» лбом к игроку:
# ближняя (≈640 м) и дальняя (≈740 м). В каждой миссии дальняя отличается от ближней ОДНОЙ правкой (контроль —
# в той же миссии). 49 — контроль копии мишени: копия не из ангара у бота ведёт себя как сток (launch.md — гипотеза).
# 53: ближняя — копия из 52 (подрыв всегда), дальняя — та же + fatalExplosion=no: иначе редкий (15 %) подрыв
# не увидеть. Правки только в DamageParts/ammo/ammoStowages: геометрия брони — в модели, не в BLK (armor_crew.md §1)
R28_TIGER = 'germ_pzkpfw_vi_ausf_h1_tiger'
R28_PLAYER = {'kind': 'tank', 'unit': R28_TIGER, 'suffix': '_r28', 'spawn': 'firing_range', 'mtype': 'testFlight',
              'weapons': 'germ_pzkpfw_VI_ausf_h1_tiger_default', 'bullets': [('88mm_ger_kwk36_Pzgr_APCBC', 40)],
              'shared_title': '28-й круг: стрелок «Тигр» H1 без правок', 'target_unit': R28_TIGER}
# копии мишени: суффикс, подпись, unit_edits — [(путь, стоковое, новое)] как в 27-м круге
R28_TARGETS = {
    'ctrl': ('_r28_t_ctrl', 'мишень-контроль без правок', []),
    'armor': ('_r28_t_armor', 'мишень: верхний лобовой лист 100 → 300 мм',
              [('DamageParts/hull/superstructure_front_dm/armorThickness', 100.0, 300.0)]),
    'crew': ('_r28_t_crew', 'мишень: прочность экипажа ×100 (hp 40 → 4000)', [('DamageParts/crew/hp', 40.0, 4000.0)]),
    'det': ('_r28_t_det', 'мишень: подрыв БК всегда (detonateProb 0.15 → 1)', [('ammo/detonateProb', 0.15, 1.0)]),
    'nofatal': ('_r28_t_nofatal', 'мишень: подрыв БК всегда, но не смертелен (fatalExplosion → no)',
                [('ammo/detonateProb', 0.15, 1.0), ('ammoStowages/ammo1/fatalExplosion', True, False)]),
}
# точки мишеней 01 и 04 из TARGETS; поворот — лбом (ось X юнита) к точке появления игрока
R28_TARGET_POS = [TARGETS[0][2][3], TARGETS[3][2][3]]


def facing_tm(pos, to):
    """tm юнита в pos, ось X (вперёд) — по горизонтали на точку to; ось Z = X × Y, как у мишеней TARGETS."""
    dx, dz = to[0] - pos[0], to[2] - pos[2]
    n = (dx * dx + dz * dz) ** 0.5
    fx, fz = round(dx / n, 6), round(dz / n, 6)
    return ((fx, 0.0, fz), (0.0, 1.0, 0.0), (-fz, 0.0, fx), pos)


CASES += [dict(R28_PLAYER, id=i, title=t, target_pair=pair) for i, t, pair in (
    ('t49_tiger_r28_ctrl', '49. Броня: контроль — сток и копия «Тигра» без правок', (None, 'ctrl')),
    ('t50_tiger_r28_armor', '50. Броня: верхний лобовой лист «Тигра» 100 → 300 мм', (None, 'armor')),
    ('t51_tiger_r28_crew', '51. Экипаж: прочность экипажа «Тигра» ×100', (None, 'crew')),
    ('t52_tiger_r28_det', '52. Боеукладка: подрыв БК «Тигра» всегда', (None, 'det')),
    ('t53_tiger_r28_nofatal', '53. Боеукладка: подрыв БК не уничтожает «Тигр»', ('det', 'nofatal')),
)]
ROUND28_IDS = {'t49_tiger_r28_ctrl', 't50_tiger_r28_armor', 't51_tiger_r28_crew', 't52_tiger_r28_det',
               't53_tiger_r28_nofatal'}

# 29-й круг (sensors_survey.md и localization.md, «Подготовка 29-го круга»): СПО, ИК-головка ракеты, ловушки на
# F-15C (как миссии 2, 41) и имена копий оружия и снаряда. file_copies — [(стоковый файл, копия, правки)]: копия =
# include стока + @override; правки — (путь, стоковое, новое), стоковое сверяется, как в unit_edits. Ссылку на копию
# меняет unit_edits копии машины (стоковое значение — путь к стоковому файлу). Общие стоковые файлы не трогаем.
# Имена копий — wtp5t_r29_<стоковое имя>: копия орудия «Тигра» без r29_ уже есть у миссии 14 (другой манифест)
R29_F15 = {'kind': 'air', 'unit': 'f_15c_golden_eagle', 'spawn': 'air_denmark', 'mtype': 'singleMission',
           'weapons': 'f_15c_golden_eagle_aim_9m'}
# излучающий противник для СПО: МиГ-23М, РЛС «Сапфир-23» (band 9 — ALR-56C его слышит, имя есть в библиотеке угроз)
AIR_TARGETS['r29_mig23'] = {'name': 'radar_target', 'unit_class': 'mig_23m', 'distance': 30000.0, 'speed': 500.0}


def r29_copy(stock):
    return os.path.dirname(stock) + '/' + PREFIX + 'r29_' + os.path.basename(stock)


R29_RWR = 'gameData/sensors/us_an_alr_56c.blk'
R29_AIM9 = ('gameData/Weapons/rocketGuns/us_aim9m_sidewinder_default.blk',
            'gameData/Weapons/rocketGuns/us_aim9m_sidewinder.blk')
# варианты слотов 1, 3, 11, 13 пресета f_15c_golden_eagle_aim_9m (aim_9m_slotN_bol): Weapon[1] — пусковая BOL,
# Weapon[2] — ракета
R29_AIM9_REFS = [('WeaponSlots/WeaponSlot[%d]/WeaponPreset[8]/Weapon[2]/blk' % n, R29_AIM9[k])
                 for n, k in ((2, 0), (4, 1), (12, 1), (14, 0))]
R29_GUN = 'gameData/Weapons/groundModels_weapons/88mm_Kwk36_user_cannon.blk'
R29_SHELL = 'wtp5t_r29_88mm_pzgr'  # свой bulletName = ключ названия снаряда
# стрелок и мишени — как в 28-м круге (две стоковые мишени «Тигр» лбом), второй снаряд PzGr 40 — со стоковым именем
R29_TIGER = dict({k: v for k, v in R28_PLAYER.items() if k != 'shared_title'}, suffix='_r29_names',
                 bullets=[('88mm_ger_kwk36_Pzgr_APCBC', 20), ('88mm_ger_kwk36_APCR', 20)])


def r29_weapon_rows(stock, full, short):
    key = 'weapons/' + os.path.basename(r29_copy(stock))[:-4]
    return [(key, full[0], full[1]), (key + '/short', short[0], short[1])]


CASES += [
    dict(R29_F15, id='t54_f15_r29_rwr_ctrl', suffix='_r29_ctrl', air_target='r29_mig23',
         title='54. F-15C: СПО AN/ALR-56C стоковая — контроль, МиГ-23М с РЛС в 30 км'),
    dict(R29_F15, id='t55_f15_r29_rwr', suffix='_r29_rwr', air_target='r29_mig23',
         title='55. F-15C: копия СПО, дальность 70 → 7 км — МиГ-23М с РЛС в 30 км',
         file_copies=[(R29_RWR, r29_copy(R29_RWR), [('range', 70000.0, 7000.0)])],
         unit_edits=[('sensors/sensor[2]/blk', R29_RWR, r29_copy(R29_RWR))]),
    dict(R29_F15, id='t56_f15_r29_ir', suffix='_r29_ir', air_target='r26_mig15',
         mission_file_stem=PREFIX + 't56_f15_r29_ir',
         title='56. F-15C: копии AIM-9M, предел ГСН 11 → 1,1 км (+ имя копии ракеты) — МиГ-15 в 30 км',
         file_copies=[(f, r29_copy(f), [('rocket/guidance/opticalSeeker/rangeMax', 11000.0, 1100.0)])
                      for f in R29_AIM9],
         unit_edits=[(path, f, r29_copy(f)) for path, f in R29_AIM9_REFS],
         loc_csv=r29_weapon_rows(R29_AIM9[0], ('AIM-9M WTP-A missiles (full)', 'Ракеты AIM-9M WTP-A (полное)'),
                                 ('AIM-9M WTP-A (short)', 'AIM-9M WTP-A (кратко)'))
         + r29_weapon_rows(R29_AIM9[1], ('AIM-9M WTP-B missiles (full)', 'Ракеты AIM-9M WTP-B (полное)'),
                           ('AIM-9M WTP-B (short)', 'AIM-9M WTP-B (кратко)'))),
    dict(R29_F15, id='t57_f15_r29_flares', suffix='_r29_flares',
         title='57. F-15C: ловушки — одна пусковая 60 → 600',
         unit_edits=[('WeaponSlots/WeaponSlot[1]/WeaponPreset[1]/Weapon[4]/bullets', 60, 600)]),
    dict(R29_TIGER, id='t58_tiger_r29_names', target_pair=(None, None), mission_file_stem=PREFIX + 't58_tiger_r29_names',
         title='58. «Тигр» H1: копия орудия и снаряда PzGr 39 со своими именами (usr_*.csv)',
         file_copies=[(R29_GUN, r29_copy(R29_GUN),
                       [('88mm_ger_kwk36_Pzgr_APCBC/bullet/bulletName', '88mm_pzgr', R29_SHELL)])],
         unit_edits=[('commonWeapons/Weapon[1]/blk', R29_GUN, r29_copy(R29_GUN))],
         loc_csv=r29_weapon_rows(R29_GUN, ('88 mm KwK36 WTP copy (full)', '88-мм KwK36 копия WTP (полное)'),
                                 ('KwK36 WTP (short)', 'KwK36 WTP (кратко)'))
         + [(R29_SHELL, 'PzGr 39 WTP shell copy', 'PzGr 39 копия WTP'),
            (PREFIX + R28_TIGER + '_r29_names_1', 'Tiger H1 (WTP 29)', 'Тигр H1 (WTP 29)')]),
]
ROUND29_IDS = {'t54_f15_r29_rwr_ctrl', 't55_f15_r29_rwr', 't56_f15_r29_ir', 't57_f15_r29_flares',
               't58_tiger_r29_names'}

# 30-й круг (sensors_survey.md «Подготовка 30-го круга»): СПО F-15C с излучающим противником. В 54 (29-й круг) СПО
# молчало: МиГ-23М шёл с dont_aim + cannotShoot и без use_search_radar — стоковые миссии включают РЛС бота явно.
# Излучатели — как в стоке: самолёт — aircraft_countermeasures_chaff_sky.blk (бот F-15C: props use_search_radar,
# attack_type fire_at_will, unitSetProperties{cannotShoot, useSearchRadar}); ЗРК — test_flight_unit_template.blk
# (cn_tor_m1, hold_fire, use_search_radar, targetableByAi=no; триггер check_radar ставит useSearchRadar) в точке
# tank_spawn_idle_area11_01 test_flight_universal_denmark.blk — там стоковый тест-полёт ставит этот же «Тор».
# Контроль 59/61 — одна копия F-15C без правок, правка 60/62 — одна копия F-15C со ссылкой на одну копию СПО
AIR_TARGETS['r30_mig23_radar'] = {'name': 'radar_target', 'unit_class': 'mig_23m', 'distance': 30000.0,
                                  'speed': 500.0, 'radar': True}
GROUND_EMITTERS = {
    'r30_tor': {'name': 'radar_sam', 'unit_class': 'cn_tor_m1',
                'tm': ((-0.614472, 0.0, 0.788937), (0.0, 1.0, 0.0), (-0.788937, 0.0, -0.614472),
                       (19692.4, 32.604, -5734.2))},
}


def r30_copy(stock):
    return os.path.dirname(stock) + '/' + PREFIX + 'r30_' + os.path.basename(stock)


R30_RWR_EDIT = dict(file_copies=[(R29_RWR, r30_copy(R29_RWR), [('range', 70000.0, 7000.0)])],
                    unit_edits=[('sensors/sensor[2]/blk', R29_RWR, r30_copy(R29_RWR))],
                    copy_title='30-й круг: копия СПО AN/ALR-56C, дальность 70 → 7 км (миссии 60, 62)')
R30_CTRL = dict(R29_F15, suffix='_r30_ctrl', shared_title='30-й круг: F-15C без правок (контроль 59, 61)')
R30_RWR = dict(R29_F15, suffix='_r30_rwr', shared_title='30-й круг: F-15C с копией СПО (миссии 60, 62)', **R30_RWR_EDIT)
CASES += [
    dict(R30_CTRL, id='t59_f15_r30_air_ctrl', air_target='r30_mig23_radar',
         title='59. F-15C: СПО стоковая — контроль, МиГ-23М с включённой РЛС в 30 км'),
    dict(R30_RWR, id='t60_f15_r30_air_rwr', air_target='r30_mig23_radar',
         title='60. F-15C: копия СПО, дальность 70 → 7 км — МиГ-23М с включённой РЛС в 30 км'),
    dict(R30_CTRL, id='t61_f15_r30_sam_ctrl', ground_emitter='r30_tor',
         title='61. F-15C: СПО стоковая — контроль, ЗРК «Тор-М1» на земле в ~9 км'),
    dict(R30_RWR, id='t62_f15_r30_sam_rwr', ground_emitter='r30_tor',
         title='62. F-15C: копия СПО, дальность 70 → 7 км — ЗРК «Тор-М1» на земле в ~9 км'),
]
ROUND30_IDS = {'t59_f15_r30_air_ctrl', 't60_f15_r30_air_rwr', 't61_f15_r30_sam_ctrl', 't62_f15_r30_sam_rwr'}

# 31-й круг (pylons_survey.md «Невесомая подвеска: итог исследования»): масса ФАБ-9000 компенсирована копией ЛМ
# (EmptyMass 10332 → 925, как 32-я), остаётся ~11–14 % недобора энергии против пустого — гипотеза: сопротивление
# подвески. Какое поле его задаёт: bomb/dragCx самой бомбы (копия ×10) или Weapon/dragCx варианта слота (у внутреннего
# 1000lbs_int его нет; у 122 бомбовых Weapon других машин — 0.02; добавлено 0.2). Правки ×10 — сигнал выше разброса
# контролей (±5 %); ноль не берём: 1 кг бомбы в 20-м круге вешал игру. Одна копия ЛМ на 64–66, у каждой миссии своя
# копия A-26B (suffix); ФАБ и ЛМ из стока не меняются
R31_FM = ('gameData/flightModels/fm/a-26b.blk', 'gameData/flightModels/fm/%sa-26b_r31_comp.blk' % PREFIX,
          [('Mass/EmptyMass', 10332.0, 925.0)])
R31_FAB = 'gameData/Weapons/BombGuns/su_fab9000.blk'
R31_FAB_CX = ('gameData/Weapons/BombGuns/%sr31_su_fab9000_cx.blk' % PREFIX)
R31_BOMB = (R31_FAB, R31_FAB_CX, [('bomb/dragCx', 0.154, 1.54)])
R31_COPY_TITLE = '31-й круг: сопротивление ФАБ-9000 при компенсированной массе (round31_checklist.md)'
AIR_LOADOUTS['A26_R31'] = {
    'variants': [(4, '1000lbs_int', PREFIX + 'r31_fab_bay', R31_FAB, 1),
                 (4, '1000lbs_int', PREFIX + 'r31_fab_cx_bay', R31_FAB_CX, 1),
                 (4, '1000lbs_int', PREFIX + 'r31_fab_wcx_bay', R31_FAB, 1, [('dragCx', 'r', 0.2)])],
    'presets': {PREFIX + 'r31_fab': [(4, PREFIX + 'r31_fab_bay')],
                PREFIX + 'r31_fab_cx': [(4, PREFIX + 'r31_fab_cx_bay')],
                PREFIX + 'r31_fab_wcx': [(4, PREFIX + 'r31_fab_wcx_bay')]},
}
R31_COMP = {'kind': 'air', 'unit': 'a-26b', 'spawn': 'firing_range_air', 'mtype': 'singleMission',
            'loadout': 'A26_R31', 'fm_file': R31_FM[1], 'copy_title': R31_COPY_TITLE}
CASES += [
    {'id': 't63_a26_r31_ctrl', 'title': '63. A-26B без бомбы — контроль', 'kind': 'air', 'unit': 'a-26b',
     'suffix': '_r31_ctrl', 'spawn': 'firing_range_air', 'mtype': 'singleMission', 'weapons': ''},
    dict(R31_COMP, id='t64_a26_r31_comp', suffix='_r31_comp', weapons=PREFIX + 'r31_fab', file_copies=[R31_FM],
         title='64. A-26B: ФАБ-9000, EmptyMass минус 9407 кг (повтор 32-й)'),
    dict(R31_COMP, id='t65_a26_r31_bombcx', suffix='_r31_bombcx', weapons=PREFIX + 'r31_fab_cx',
         file_copies=[R31_FM, R31_BOMB], title='65. A-26B: как 64, копия ФАБ с bomb/dragCx ×10 (НЕ сбрасывать)'),
    dict(R31_COMP, id='t66_a26_r31_wcx', suffix='_r31_wcx', weapons=PREFIX + 'r31_fab_wcx', file_copies=[R31_FM],
         title='66. A-26B: как 64, у подвеса ФАБ добавлен Weapon/dragCx=0.2'),
]
ROUND31_IDS = {'t63_a26_r31_ctrl', 't64_a26_r31_comp', 't65_a26_r31_bombcx', 't66_a26_r31_wcx'}

# 32-й круг (round32_checklist.md): наземная ЗУР на пилоне самолёта. 26.10 программа (v0.94) повесила 95Я6М
# («Панцирь-СМ»: cannon:yes, bullet{rocket{guidanceType=saclos}}) на F-15C — игра упала сразу после старта миссии,
# лог без ошибки. Разделяем две причины: формат «орудия» и наведение saclos с земли. Пилон 1 F-15C, образец —
# штатный вариант aim_9l_default (одна AIM-9L, триггер aam). new_files — [(путь, функция(дерево, сток), сток)]:
# новый файл, а не копия с правками: ЗУР переделана в авиационную ракету — rocketGun + блок rocket из bullet ЗУР
R32_SAM_9X = 'gameData/Weapons/groundModels_weapons/127mm_aim_9x_user_cannon.blk'       # ЗУР AIM-9X, ИК-ГСН
R32_SAM_95 = 'gameData/Weapons/groundModels_weapons/170mm_57e6m_launcher_user_cannon.blk'  # 95Я6М, saclos


def r32_air(stock):
    return 'gameData/Weapons/rocketGuns/%sr32_%s_air.blk' % (PREFIX, os.path.basename(stock)[:-4].lower())


def r32_rocketgun(tree, stock):
    """Текст авиационной ракеты из ЗУР: rocketGun, 1 штука, mesh и блок rocket — из bullet ЗУР (как у
    rocketGuns/us_aim_120c_5.blk: rocketGun, bullets, shotFreq, mesh, rocket{}). None — в ЗУР нет bullet{rocket}."""
    bullet = tree.block('bullet')
    rocket = bullet.block('rocket') if bullet is not None else None
    if rocket is None:
        return None
    mesh = rocket.get('mesh') or tree.get('mesh') or ''
    head = ('// WT Poligon 5 test: %s переделана в авиационную ракету (rocketGun + rocket{} из bullet) — 32-й круг\n'
            % stock)
    params = 'rocketGun:b=yes\nbullets:i=1\nshotFreq:r=1.0\n' + ('mesh:t=%s\n' % B.quote(mesh) if mesh else '')
    return head + params + B.to_text(B.Block(None, blocks=[rocket]))


AIR_TARGETS['r32_mig15_5km'] = {'name': 'radar_target', 'unit_class': 'mig-15bis_ns23', 'distance': 5000.0,
                                'speed': 500.0}
# у каждой миссии — только свой вариант: игра может читать все варианты слотов при загрузке самолёта
for _key, _new, _wblk in (('F15_R32_RAW', 'r32_sam9x_raw', R32_SAM_9X), ('F15_R32_95', 'r32_95ya6m_air', r32_air(R32_SAM_95)),
                          ('F15_R32_9X', 'r32_sam9x_air', r32_air(R32_SAM_9X))):
    AIR_LOADOUTS[_key] = {'variants': [(1, 'aim_9l_default', PREFIX + _new, _wblk, 1)],
                          'presets': {PREFIX + _new: [(1, PREFIX + _new)]}}
R32_F15 = {'kind': 'air', 'unit': 'f_15c_golden_eagle', 'spawn': 'air_denmark', 'mtype': 'singleMission',
           'air_target': 'r32_mig15_5km',
           'copy_title': '32-й круг: наземная ЗУР на пилоне F-15C (round32_checklist.md)'}
CASES += [
    dict(R32_F15, id='t67_f15_r32_sam9x_raw', suffix='_r32_raw', weapons=PREFIX + 'r32_sam9x_raw', loadout='F15_R32_RAW',
         title='67. F-15C: «ЗУР AIM-9X» как есть (наземный формат, своя ИК-ГСН) на пилоне 1 — МОЖЕТ УРОНИТЬ ИГРУ'),
    dict(R32_F15, id='t68_f15_r32_95ya6m_air', suffix='_r32_95air', weapons=PREFIX + 'r32_95ya6m_air',
         loadout='F15_R32_95',
         new_files=[(r32_air(R32_SAM_95), 'r32_rocketgun', R32_SAM_95)],
         title='68. F-15C: 95Я6М, переделанная в авиационную ракету (rocketGun) — МОЖЕТ УРОНИТЬ ИГРУ'),
    dict(R32_F15, id='t69_f15_r32_sam9x_air', suffix='_r32_9xair', weapons=PREFIX + 'r32_sam9x_air',
         loadout='F15_R32_9X',
         new_files=[(r32_air(R32_SAM_9X), 'r32_rocketgun', R32_SAM_9X)],
         title='69. F-15C: «ЗУР AIM-9X», переделанная в авиационную ракету (rocketGun) — МОЖЕТ УРОНИТЬ ИГРУ'),
]
ROUND32_IDS = {'t67_f15_r32_sam9x_raw', 't68_f15_r32_95ya6m_air', 't69_f15_r32_sam9x_air'}
NEW_FILE_MAKERS = {'r32_rocketgun': r32_rocketgun}


def fm_link_problems(c, u, load):
    """31-й круг: копия ЛМ пункта (fm_file) — из file_copies, от стоковой ЛМ машины, и её EmptyMass = стоковая
    пустая масса минус масса подвески пресета (payload_mass), больше нуля."""
    if not c.get('fm_file'):
        return []
    copies = {copy: (stock, edits) for stock, copy, edits in c.get('file_copies', [])}
    if c['fm_file'] not in copies:
        return ['%s: копии ЛМ %s нет в file_copies' % (c['id'], c['fm_file'])]
    stock, edits = copies[c['fm_file']]
    if stock != 'gameData/flightModels/' + (u.get('fmFile') or ''):
        return ['%s: ЛМ машины %s, а копия сделана от %s' % (c['id'], u.get('fmFile'), stock)]
    if [e[0] for e in edits] != ['Mass/EmptyMass']:
        return ['%s: в копии ЛМ должна быть только правка Mass/EmptyMass' % c['id']]
    _path, empty, new = edits[0]
    # копия оружия из file_copies ещё не в игре: массу берём из её стока, если правки массу не трогают
    src = {copy: stock for stock, copy, e in c.get('file_copies', [])
           if not any(path.split('/')[-1] == 'mass' for path, _s, _n in e)}
    kg, _parts = payload_mass(u, AIR_LOADOUTS[c['loadout']], c['weapons'], lambda p: load(src.get(p, p)))
    if new <= 0 or abs(empty - kg - new) > 0.5:
        return ['%s: EmptyMass %s − подвеска %.1f кг ≠ %s' % (c['id'], empty, kg, new)]
    return []


def emitter_unit(c):
    """Стоковый файл излучателя пункта (самолёт-мишень с РЛС или ЗРК) или None."""
    if c.get('ground_emitter'):
        return 'gameData/units/tankModels/%s.blk' % GROUND_EMITTERS[c['ground_emitter']]['unit_class']
    at = AIR_TARGETS.get(c.get('air_target'), {})
    return 'gameData/flightModels/%s.blk' % at['unit_class'] if at.get('radar') else None


def radar_bands(unit, load, kind):
    """Диапазоны сенсоров машины вида kind: 'radar' — transivers/*/band РЛС (без ИК), 'rwr' — bandN=true СПО."""
    bands = set()
    for s in (unit.block('sensors').blocks if unit.block('sensors') else []):
        t = load(s.get('blk')) if s.get('blk') else None
        if t is None or t.get('type') != kind:
            continue
        if kind == 'rwr':
            bands |= {int(k[4:]) for k, _t, v in t.params if k.startswith('band') and k[4:].isdigit() and v is True}
        elif t.block('transivers'):
            bands |= {tr.get('band') for tr in t.block('transivers').blocks
                      if not tr.get('visibilityType') and isinstance(tr.get('band'), int) and tr.get('band') >= 0}
    return bands


def emitter_problems(c, u, load):
    """30-й круг: излучатель есть, у него РЛС, и СПО машины игрока слышит хотя бы один её диапазон."""
    path = emitter_unit(c)
    if not path:
        return []
    e = load(path)
    if e is None:
        return ['%s: нет излучателя %s' % (c['id'], path)]
    radar, rwr = radar_bands(e, load, 'radar'), radar_bands(u, load, 'rwr')
    if not radar:
        return ['%s: у излучателя %s нет РЛС' % (c['id'], path)]
    if not radar & rwr:
        return ['%s: СПО (диапазоны %s) не слышит РЛС излучателя (%s)' % (c['id'], sorted(rwr), sorted(radar))]
    return []


SEPARATE_IDS = (ROUND22_IDS | ROUND23_IDS | ROUND24_IDS | ROUND25_IDS | ROUND26_IDS | ROUND27_IDS | ROUND28_IDS
                | ROUND29_IDS | ROUND30_IDS | ROUND31_IDS | ROUND32_IDS)
STANDARD_CASES = [c for c in CASES if c['id'] not in SEPARATE_IDS]


def air_loadout(u, cfg, unit):
    """Своя подвеска по AIR_LOADOUTS: ([(путь в игре, текст пресета)], правки файла машины, проблемы)."""
    import copy
    problems = []
    ws = u.block('WeaponSlots')
    slots = [s for s in ws.blocks if s.name == 'WeaponSlot'] if ws else []
    names = {s.get('index'): [p.get('name') for p in s.blocks if p.name == 'WeaponPreset'] for s in slots}
    by_slot = {}
    for index, sample, new, wblk, *keep in cfg.get('variants', []):
        n = [i for i, s in enumerate(slots, 1) if s.get('index') == index]
        src = [p for p in (slots[n[0] - 1].blocks if n else []) if p.name == 'WeaponPreset' and p.get('name') == sample]
        if not src:
            problems.append('нет слота %s / варианта %s' % (index, sample))
            continue
        v = copy.deepcopy(src[0])
        v.params = [('name', 't', new) if k == 'name' else (k, t, x) for k, t, x in v.params if k != 'reqModification']
        v.blocks = [b for b in v.blocks if b.name not in ('BannedWeaponPreset', 'DependentWeaponPreset')]
        if keep:  # оставить первые keep[0] подвесов образца
            idx = [i for i, b in enumerate(v.blocks) if b.name == 'Weapon'][keep[0]:]
            v.blocks = [b for i, b in enumerate(v.blocks) if i not in idx]
        add = keep[1] if len(keep) > 1 else ()  # 31-й круг: новые параметры каждого Weapon, [(имя, тип, значение)]
        for w in v.blocks:
            if w.name == 'Weapon':
                w.params = [(k, t, wblk if k == 'blk' else x) for k, t, x in w.params]
                if any(w.get(k) is not None for k, _t, _x in add):
                    problems.append('вариант %s: параметр уже есть в образце %s' % (new, sample))
                w.params += list(add)
        by_slot.setdefault(n[0], []).append(B.to_text(B.Block(None, blocks=[v])))
        names[index].append(new)
    unit_text = ''
    if by_slot:
        unit_text += '"@override:WeaponSlots"{\n' + ''.join(
            '"@override:WeaponSlot[%d]"{\n%s}\n' % (n, ''.join(t)) for n, t in sorted(by_slot.items())) + '}\n'
    files, entries = [], []
    for pname, pairs in cfg.get('presets', {}).items():
        for slot, preset in pairs:
            if preset not in names.get(slot, []):
                problems.append('пресет %s: в слоте %s нет варианта %s' % (pname, slot, preset))
        path = 'gameData/FlightModels/weaponPresets/%s_%s.blk' % (PREFIX + unit.lower(), pname[len(PREFIX):])
        text = '// WT Poligon 5, тестовый пресет подвески %s (pylons_survey.md)\n' % pname + ''.join(
            'Weapon{\n  slot:i=%d\n  preset:t=%s\n}\n' % (slot, B.quote(preset)) for slot, preset in pairs)
        files.append(('content/pkg_local/' + path, text))
        entries.append('preset{\n  name:t=%s\n  blk:t=%s\n}\n' % (B.quote(pname), B.quote(path)))
    if entries:
        unit_text += '"@override:weapon_presets"{\n' + ''.join(entries) + '}\n'
    return files, unit_text, problems


LEGACY_LOADOUTS = {
    'A20_CHECK': {
        PREFIX + 'a20_same': ('a20g_4x250lb', None),
        PREFIX + 'a20_swap': ('a20g_4x250lb', 'gameData/Weapons/BombGuns/us_500lb_anm64a1.blk'),
    },
}


def legacy_loadout(u, load, cfg, unit):
    """Свои пресеты старой схемы: include стока и, при необходимости, замена Weapon[1]/blk."""
    old = [p for p in u.block('weapon_presets').blocks if p.name == 'preset']
    files, entries, problems = [], [], []
    for name, (source, replacement) in cfg.items():
        stock = next((p.get('blk') for p in old if p.get('name') == source), None)
        tree = load(stock) if stock else None
        if tree is None:
            problems.append('нет старого пресета %s' % source)
            continue
        weapon = next((w for w in tree.blocks if w.name == 'Weapon'), None)
        if weapon is None:
            problems.append('в %s нет Weapon' % source)
            continue
        patch = ''
        if replacement:
            if load(replacement) is None:
                problems.append('нет файла оружия %s' % replacement)
                continue
            patch = '"@override:Weapon[1]"{\n  "@override:blk":t=%s\n}\n' % B.quote(replacement)
        path = 'gameData/FlightModels/weaponPresets/%s_%s.blk' % (PREFIX + unit.lower(), name[len(PREFIX):])
        files.append(('content/pkg_local/' + path, gun_file_text(stock, name, patch)))
        entries.append('preset{\n  name:t=%s\n  blk:t=%s\n}\n' % (B.quote(name), B.quote(path)))
    return files, '"@override:weapon_presets"{\n' + ''.join(entries) + '}\n', problems


# копии файлов оружия в пресетах самолёта: имя -> {пресет: {стоковый файл оружия: [(путь, значение)]}}, every —
# каждый every-й Weapon с этим файлом (по порядку в пресете) получает копию. Общая для пунктов с одной машиной
WEAPON_COPIES = {
    'A20': {'every': 2, 'presets': {
        # вид взрыва — отдельное поле, не от explosiveMass (15-й круг: урон ×10, взрыв тот же); 585 кг ВВ — ступень
        # стоковых бомб «до 900 кг» → bomb_expl_1000kg
        'a20g_4x250lb': {'gameData/Weapons/BombGuns/us_250lb_anm57.blk': [('bomb/explosiveMass', 585.0),
                                                                          ('bomb/explosionFx', 'bomb_expl_1000kg')]},
        'a-20g_12xbazooka': {'gameData/Weapons/rocketGuns/us_m8bazooka.blk': [('rocket/force', 69000.0),
                                                                              ('rocket/maxSpeed', 780.0)]},
        'a20g_torpedo': {'gameData/Weapons/torpedoes/test_torpedo.blk': [('torpedo/maxSpeedInWater', 60.0)]}}},
}


# Эксперимент launch.md §7.9: интерфейс игры знает только машины из config/unittags.blk (§7.1), у копии под своим
# именем нет оборудования, кнопок, иконок (§7.8). Пишем в pkg_local/config/ полную копию справочника установленной
# игры + записи для копий (копия записи исходной машины под новым именем). Разные наборы — чтобы понять, не включит
# ли запись проверку «машина должна быть в ангаре»: Т-80 и M1A1 — оба справочника, CM-34 — только unittags,
# остальные копии не регистрируем (контроль).
REGISTRY = {
    'config/unittags.blk': ['ussr_t_80bvm', 'us_m1a1_abrams', 'cn_cm_34'],
    'config/wpcost.blk': ['ussr_t_80bvm', 'us_m1a1_abrams'],
}


def registry_files(game_dir):
    """[(путь от папки игры, текст)] — полные копии справочников + записи wtp5t_*."""
    ch = Vromfs(os.path.join(game_dir, 'char.vromfs.bin'))
    rd = B.BinaryReader.for_vromfs(ch)
    out = []
    for path, units in REGISTRY.items():
        root = rd.parse(ch.files[path])
        have = {b.name: b for b in root.blocks}
        for u in units:
            if u not in have:
                raise ValueError('%s: нет записи %s' % (path, u))
            copy = B._clone(have[u])
            copy.name = PREFIX + u.lower()
            root.blocks.append(copy)
        head = ('// WT Poligon 5, ЭКСПЕРИМЕНТ (launch.md §7.9): полная копия %s игры %s + записи %s.\n'
                '// Перед игрой онлайн и после обновления игры убрать: make_test_missions.py --no-registry\n'
                % (path, ch.header.version, ', '.join(PREFIX + u for u in units)))
        out.append(('content/pkg_local/' + path, head + B.to_text(root)))
    return out


# Перенос модификаций в копию — правила и код в wtlib/mods.py (docs/research/modifications.md).
# История: 7-й круг — параметры модификаций у копии не работают; 8-й — блоки (гранаты, тепловизор) работают.


# ------------------------------------------------------------------ файлы юнитов

def unit_file_text(folder, base, case_title, extra=''):
    what = 'Стоковая машина без правок' if not extra else 'Стоковая машина + правки ниже'
    return ('// WT Poligon 5, тестовая копия для чек-листа launch.md: %s\n'
            '// %s. Удаляется командой make_test_missions.py --remove\n'
            'include "#/develop/gameBase/gameData/%s/%s.blk"\n%s') % (case_title, what, folder, base, extra)


def target_copy_name(case, key):
    """Имя копии мишени 28-го круга (unit_class в миссии и имя файла)."""
    return PREFIX + case['target_unit'].lower() + R28_TARGETS[key][0]


def edited_copies(c):
    """Копии пункта для сверки итога правок: [(путь копии в игре, стоковый файл, правки)]. Копии без правок —
    только контроли 27–29-го кругов (в них не должно быть @override); копии других кругов (запекание, сенсоры…)
    проверяются своими правилами. Копии файлов (file_copies, 29-й круг) — как копии машины."""
    out = []
    if not (c.get('real_name') or c.get('donor') or c.get('existing_user_vehicle')):
        edits = c.get('unit_edits', [])
        if edits or c['id'] in ROUND27_IDS | ROUND28_IDS | ROUND29_IDS | ROUND30_IDS:
            folder = KINDS[c['kind']][1]
            out.append(('content/pkg_local/gameData/%s/%s%s%s.blk' % (folder, PREFIX, c['unit'].lower(), c.get('suffix', '')),
                        'gameData/%s/%s.blk' % (folder, c['unit']), edits))
    for key in c.get('target_pair', ()):
        if key:
            out.append(('content/pkg_local/gameData/units/tankModels/%s.blk' % target_copy_name(c, key),
                        'gameData/units/tankModels/%s.blk' % c['target_unit'], R28_TARGETS[key][2]))
    for stock, copy, edits in c.get('file_copies', []):
        out.append(('content/pkg_local/' + copy, stock, edits))
    return out


def prepare_file_copies(c, load):
    """Копии файлов пункта (file_copies): c['_files'] = [(путь в игре, текст)] — только если все стоковые значения
    совпали. Возвращает проблемы."""
    files, problems = [], []
    for stock, copy, edits in c.get('file_copies', []):
        tree = load(stock)
        if tree is None:
            problems.append('%s: нет файла %s' % (c['id'], stock))
            continue
        text, probs = unit_edits(tree, edits)
        problems += ['%s: %s: %s' % (c['id'], os.path.basename(stock), p) for p in probs]
        # copy_title — одна копия файла на несколько пунктов (30-й круг): текст не зависит от пункта
        files.append(('content/pkg_local/' + copy, gun_file_text(stock, c.get('copy_title', c['title']), text)))
    for dest, maker, stock in c.get('new_files', []):        # 32-й круг: новый файл из стокового (не копия)
        tree = load(stock)
        text = NEW_FILE_MAKERS[maker](tree, stock) if tree is not None else None
        if text is None:
            problems.append('%s: не собрать %s из %s' % (c['id'], dest, stock))
            continue
        files.append(('content/pkg_local/' + dest, text))
    if not problems:
        c['_files'] = files
    return problems


def check_unit_edits(load, items, cases):
    """После сборки: итоговое дерево каждой копии с unit_edits (resolve_file поверх стока) — лог пустой, значение
    каждого поля = заданному, остальные поля правок не трогали. Контрольная копия без правок не содержит @override.
    Общая копия (стрелок, мишень на несколько миссий) — один раз.
    Возвращает [(путь, проблема или '', [(поле, значение)])]."""
    files = dict(items)
    out, seen = [], set()
    for rel, stock, edits in [x for c in cases for x in edited_copies(c)]:
        if rel not in files or rel in seen:
            continue
        seen.add(rel)
        if not edits:
            out.append((rel, '' if '@override' not in files[rel] else 'в контроле есть @override', []))
            continue
        log = []
        res = B.resolve_file(files[rel], load, log)
        got = [(path, path_value(res, path)) for path, _s, _n in edits]
        bad = ['%s не равно заданному' % p for (p, v), (_p, _s, n) in zip(got, edits) if v != n]
        # всё, кроме правок, — как в стоке (соседние повторы, например другие передачи, не задеты)
        want = B._clone(load(stock))
        for path, _s, new in edits:
            set_path_value(want, path, type(path_value(want, path))(new))
        if not bad and B.to_text(res) != B.to_text(want):
            bad.append('кроме правок изменилось что-то ещё')
        out.append((rel, '; '.join(log + bad), got))
    return out


def gun_copy_name(stock_path):
    return PREFIX + os.path.basename(stock_path)


def gun_file_text(stock_path, case_title, extra):
    return ('// WT Poligon 5, тестовая копия файла: %s\n'
            '// Стоковый файл + правки ниже. Удаляется командой make_test_missions.py --remove\n'
            'include "#/develop/gameBase/%s"\n%s') % (case_title, stock_path, extra)


def copy_path(stock_path):
    return os.path.dirname(stock_path) + '/' + PREFIX + os.path.basename(stock_path)


def weapon_copies(u, load, cfg):
    """Копии пресетов и файлов оружия по WEAPON_COPIES: ([(путь в игре, текст)], правки файла машины, проблемы)."""
    files, unit_lines, problems = [], [], []
    presets = [p for p in u.block('weapon_presets').blocks if p.name == 'preset']
    done = set()
    for pname, weapons in cfg['presets'].items():
        k = [i for i, p in enumerate(presets) if p.get('name') == pname]
        if not k:
            problems.append('нет пресета %s' % pname)
            continue
        pblk = presets[k[0]].get('blk')
        ptree = load(pblk)
        lines = []
        for stock, edits in weapons.items():
            wtree = load(stock)
            if wtree is None:
                problems.append('нет файла %s' % stock)
                continue
            if stock not in done:
                try:
                    text = ''.join(override_path(wtree, path, v) for path, v in edits)
                except KeyError as e:
                    problems.append(str(e))
                    continue
                files.append(('content/pkg_local/' + copy_path(stock), gun_file_text(stock, pname, text)))
                done.add(stock)
            occ = 0
            for i, w in enumerate([b for b in ptree.blocks if b.name == 'Weapon'], 1):
                if (w.get('blk') or '').lower() == stock.lower():
                    occ += 1
                    if occ % cfg['every'] == 0:
                        lines.append('"@override:Weapon[%d]"{\n  "@override:blk":t=%s\n}\n' % (i, B.quote(copy_path(stock))))
            if not occ:
                problems.append('в пресете %s нет %s' % (pname, stock))
        files.append(('content/pkg_local/' + copy_path(pblk), gun_file_text(pblk, pname, ''.join(lines))))
        unit_lines.append('  "@override:preset[%d]"{\n    "@override:blk":t=%s\n  }\n' % (k[0] + 1, B.quote(copy_path(pblk))))
    unit = '"@override:weapon_presets"{\n' + ''.join(unit_lines) + '}\n' if unit_lines else ''
    return files, unit, problems


def sensor_entries(u, stock):
    """Записи sensors/sensor машины со ссылкой на файл stock (регистр пути не важен): [(место, номер с 1)].
    Место — 'root' или путь блока пресета/модификации (sensors_survey.md «Как машина подключает сенсор»)."""
    out = []

    def walk(node, where):
        for b in node.blocks:
            if b.name.lower() == 'sensors':
                refs = [s for s in b.blocks if s.name.lower() == 'sensor']
                for n, s in enumerate(refs, 1):
                    if (s.get('blk') or '').lower() == stock.lower():
                        out.append((where or 'root', n))
            else:
                walk(b, where + '/' + b.name if where else b.name)
    walk(u, '')
    return out


def sensor_copy(u, load, cfg, title):
    """Копия файла сенсора по SENSOR_COPIES: ([(путь в игре, текст)], правки файла машины, проблемы, [(режим, было,
    стало)]). Правится поле field у каждого transivers/<режим>, где оно есть; ссылка — только корневая запись."""
    stock, field, scale = cfg['sensor'], cfg['field'], cfg['scale']
    problems, changes = [], []
    tree = load(stock)
    if tree is None:
        return [], '', ['нет файла сенсора %s' % stock], []
    tr = tree.block('transivers')
    if tree.get('type') != 'radar' or not tr or any(t.get('visibilityType') for t in tr.blocks):
        problems.append('%s — не обычная РЛС (type/visibilityType)' % stock)
    edits = []
    for t in tr.blocks if tr else []:
        old = t.get(field)
        if old is None:
            continue
        new = round(old * scale, 1)
        edits.append(override_path(tree, 'transivers/%s/%s' % (t.name, field), new))
        changes.append((t.name, old, new))
    if not changes:
        problems.append('в %s нет transivers/*/%s' % (stock, field))
    places = sensor_entries(u, stock)
    root = [n for where, n in places if where == 'root']
    if len(root) != 1:
        problems.append('корневых ссылок на %s: %d (нужна одна)' % (stock, len(root)))
    other = [where for where, _n in places if where != 'root']
    if other:
        # пресет или модификация добавит стоковый сенсор ещё раз — проверка станет неоднозначной
        problems.append('ссылки на %s вне корня: %s' % (stock, other))
    copy = copy_path(stock)
    files = [('content/pkg_local/' + copy, gun_file_text(stock, title, ''.join(edits)))]
    count = len([s for s in u.block('sensors').blocks if s.name == 'sensor']) if u.block('sensors') else 0
    unit = ('"@override:sensors"{\n  "@override:sensor%s"{\n    "@override:blk":t=%s\n  }\n}\n'
            % ('[%d]' % root[0] if count > 1 else '', B.quote(copy))) if len(root) == 1 else ''
    return files, unit, problems, changes


def gun_ref_override(copy_path):
    # основное орудие — первый Weapon в commonWeapons (как проверка снарядов в check_against_game)
    return ('"@override:commonWeapons"{\n  "@override:Weapon[1]"{\n    "@override:blk":t=%s\n  }\n}\n'
            % B.quote(copy_path))


def sam_overrides(launcher_name, count):
    # ссылки на пусковые всегда с папкой (launch.md §5.1); индекс блока с 1 (blk_parser.cpp, get_array_idx)
    lines = ['"@override:supportPlanes"{']
    for i in range(1, count + 1):
        lines += ['  "@override:plane[%d]"{' % i,
                  '    "@override:class":t=%s' % B.quote('tankModels/' + launcher_name), '  }']
    lines.append('}')
    return '\n'.join(lines) + '\n'


# ------------------------------------------------------------------ миссия

def mission_targets(case):
    """Мишени миссии [(имя, unit_class, tm)]: пара 28-го круга (сток или копия) или набор TARGETS."""
    if case.get('target_pair'):
        player = SPAWNS[case['spawn']][1]
        return [('target_%s' % side, target_copy_name(case, key) if key else case['target_unit'], facing_tm(pos, player))
                for side, key, pos in zip(('near', 'far'), case['target_pair'], R28_TARGET_POS)]
    return TARGETS if case.get('targets') else []


def mission(case, unit_name):
    """Структура как у миссий 4.7, которые игра загружала (логи 10–24.10); каркас — wtpoligon.mission."""
    level, pos, speed = SPAWNS[case['spawn']]
    extra_units, init_actions, extra_triggers, way_points = [], [], [], []
    targets = mission_targets(case)
    if targets:
        units, actions, triggers = T.ground_parts(targets)
        extra_units += units
        init_actions.extend(actions)
        extra_triggers += triggers

    if case.get('air_target'):
        at = AIR_TARGETS[case['air_target']]
        units, actions, _triggers, ways = T.air_parts(at['name'], at['unit_class'],
                                                      (pos[0] + at['distance'], pos[1], pos[2]), pos, at['speed'],
                                                      radar=bool(at.get('radar')))
        extra_units += units
        init_actions.extend(actions)
        way_points += ways

    if case.get('ground_emitter'):
        # 30-й круг: ЗРК-излучатель, как target_tank_idle_high11_01 в test_flight_unit_template.blk: не стреляет,
        # поисковая РЛС включена (props и триггер, как check_radar шаблона), отмечен на экране
        ge = GROUND_EMITTERS[case['ground_emitter']]
        extra_units.append(B.Block('tankModels', [
            ('name', 't', ge['name']), ('tm', 'm', ge['tm']), ('unit_class', 't', ge['unit_class']),
            ('objLayer', 'i', 1), ('closed_waypoints', 'b', False), ('isShipSpline', 'b', False),
            ('shipTurnRadius', 'r', 100.0), ('weapons', 't', '')]
            + [('bullets%d' % i, 't', '') for i in range(4)] + [('bulletsCount%d' % i, 'i', 0) for i in range(4)]
            + [('crewSkillK', 'r', 0.0), ('applyAllMods', 'b', False)],
            [B.Block('props', [('army', 'i', 2), ('count', 'i', 1), ('formation_type', 't', 'rows'),
                               ('formation_div', 'i', 3), ('formation_step', 'p2', (2.5, 2.0)),
                               ('formation_noise', 'p2', (0.1, 0.1)), ('uniqueName', 't', ''),
                               ('attack_type', 't', 'hold_fire'), ('use_search_radar', 'b', True),
                               ('targetableByAi', 'b', False)]),
             B.Block('way')]))
        init_actions.extend([
            B.Block('unitSetProperties', [('object', 't', ge['name']), ('useSearchRadar', 'b', True)]),
            B.Block('unitSetIndication', [('set', 'b', True), ('target', 't', ge['name'])])])

    title = 'WTP5 тест — ' + case['title']
    loc_desc = ('31-й круг: сопротивление подвески при компенсированной массе (см. round31_checklist.md).' if case['id'] in ROUND31_IDS
                else '30-й круг: СПО с излучающим противником (см. round30_checklist.md).' if case['id'] in ROUND30_IDS
                else '29-й круг: СПО, ИК-головка, ловушки, имена копий оружия (см. round29_checklist.md).' if case['id'] in ROUND29_IDS
                else '28-й круг: броня, экипаж, боеукладка (см. round28_checklist.md).' if case['id'] in ROUND28_IDS
                else '27-й круг: физика наземки и флота (см. round27_checklist.md).' if case['id'] in ROUND27_IDS
                else '26-й круг: дальность РЛС (см. round26_checklist.md).' if case['id'] in ROUND26_IDS
                else '25-й круг: локализация (см. round25_checklist.md).' if case['id'] in ROUND25_IDS
                else '24-й круг: мощность двигателя (см. round24_checklist.md).' if case['id'] in ROUND24_IDS
                else '23-й круг: Takeoff ЛМ (см. round23_checklist.md).' if case['id'] in ROUND23_IDS
                else '22-й круг: вертолётный HUD (см. round22_checklist.md).' if case['id'] in ROUND22_IDS
                else '21-й круг: external ФАБ (см. round21_checklist.md).' if case['id'] in ROUND21_IDS
                else '20-й круг: масса ФАБ (см. round20_checklist.md).' if case['id'] in ROUND20_IDS
                else '19-й круг: масса и подвеска (см. round19_checklist.md).' if case['id'] in ROUND19_IDS
                else 'Проверка запуска техники не из ангара (WT Poligon 5, launch.md §6).')
    return MI.mission_text(
        name=PREFIX + case['id'], loc_name=case.get('loc_name_key', title), loc_desc=loc_desc,
        kind=case['kind'], spawn=case['spawn'], mtype=case['mtype'], unit_class=unit_name,
        weapons=case.get('weapons', ''), bullets=case.get('bullets', []),
        modifications=case.get('_all_mods') or case.get('modifications', []),
        extra_units=extra_units, init_actions=init_actions, extra_triggers=extra_triggers,
        way_points=way_points)


# ------------------------------------------------------------------ проверка по данным игры

def check_against_game(game_dir, cases):
    """Исходная машина, пресет, модификация и пусковые должны существовать в установленной игре."""
    aces = Vromfs(os.path.join(game_dir, 'aces.vromfs.bin'))
    rd = B.BinaryReader.for_vromfs(aces)
    char = Vromfs(os.path.join(game_dir, 'char.vromfs.bin'))
    mods_blk = M_mods.global_mods(char)
    problems = []
    for c in cases:
        folder = KINDS[c['kind']][1].lower()
        data = aces.get('gamedata/%s/%s.blk' % (folder, c['unit'].lower()))
        if data is None:
            problems.append('%s: нет файла %s/%s.blk' % (c['id'], folder, c['unit']))
            continue
        u = rd.parse(data)
        presets = [p.get('name') for p in (u.block('weapon_presets').blocks if u.block('weapon_presets') else [])]
        if c.get('loadout'):
            cfg = AIR_LOADOUTS[c['loadout']]
            files, unit_text, probs = air_loadout(u, cfg, c['unit'])
            for source, destination, field, value in cfg.get('weapon_edits', []):
                data = aces.get(source.lower())
                if data is None:
                    problems.append('%s: нет файла оружия %s' % (c['id'], source))
                    continue
                try:
                    edit = override_path(rd.parse(data), field, value)
                except KeyError as e:
                    problems.append('%s: %s' % (c['id'], e))
                    continue
                files.append(('content/pkg_local/' + destination,
                              gun_file_text(source, '20-й круг: масса ФАБ для проверки до сброса', edit)))
            problems += ['%s: %s' % (c['id'], p) for p in probs]
            if c.get('weightless') and not probs:
                def load(p):
                    d = aces.get((p or '').lower())
                    return rd.parse(d) if d else None
                kg, parts = payload_mass(u, AIR_LOADOUTS[c['loadout']], c['weapons'], load)
                fm_rel = u.get('fmFile')
                fm_stock = 'gameData/flightModels/' + fm_rel
                fm = load(fm_stock)
                empty = fm.block('Mass').get('EmptyMass') if fm and fm.block('Mass') else None
                if not empty or empty - kg <= 0:
                    problems.append('%s: EmptyMass %s минус подвеска %.0f кг — не положительная' % (c['id'], empty, kg))
                else:
                    c['_payload'] = (kg, parts, empty)
                    fm_copy = 'fm/%s%s%s.blk' % (PREFIX, c['unit'].lower(), c.get('suffix', ''))
                    files = files + [('content/pkg_local/gameData/flightModels/' + fm_copy, gun_file_text(
                        fm_stock, c['title'] + ' — ЛМ: EmptyMass %.0f − подвеска %.0f кг' % (empty, kg),
                        override_path(fm, 'Mass/EmptyMass', round(empty - kg, 1))))]
                    unit_text += '"@override:fmFile":t=%s\n' % B.quote(fm_copy)
            c['_wcopy'] = (files, unit_text)
            presets += list(AIR_LOADOUTS[c['loadout']]['presets'])
        if c.get('legacy_loadout'):
            def load_legacy(p):
                d = aces.get((p or '').lower())
                return rd.parse(d) if d else None
            files, unit_text, probs = legacy_loadout(u, load_legacy,
                                                    LEGACY_LOADOUTS[c['legacy_loadout']], c['unit'])
            problems += ['%s: %s' % (c['id'], p) for p in probs]
            c['_legacy'] = (files, unit_text)
            presets += list(LEGACY_LOADOUTS[c['legacy_loadout']])
        if c.get('fm_empty_delta') is not None:
            fm_rel = u.get('fmFile')
            fm_stock = 'gameData/flightModels/' + fm_rel if fm_rel else ''
            fm_data = aces.get(fm_stock.lower()) if fm_stock else None
            fm = rd.parse(fm_data) if fm_data else None
            empty = fm.block('Mass').get('EmptyMass') if fm and fm.block('Mass') else None
            new_empty = empty + c['fm_empty_delta'] if empty is not None else None
            if new_empty is None or new_empty <= 0:
                problems.append('%s: недопустимый EmptyMass %s' % (c['id'], new_empty))
            else:
                path = 'fm/%s%s%s.blk' % (PREFIX, c['unit'].lower(), c.get('suffix', ''))
                c['_fm_copy'] = ('content/pkg_local/gameData/flightModels/' + path,
                                 gun_file_text(fm_stock, c['title'],
                                               override_path(fm, 'Mass/EmptyMass', new_empty)), path)
        if c.get('fm_takeoff_delta') is not None:
            fm_rel = u.get('fmFile')
            fm_stock = 'gameData/flightModels/' + fm_rel if fm_rel else ''
            fm_data = aces.get(fm_stock.lower()) if fm_stock else None
            fm = rd.parse(fm_data) if fm_data else None
            mass = fm.block('Mass') if fm else None
            takeoff = mass.get('Takeoff') if mass else None
            empty = mass.get('EmptyMass') if mass else None
            new_takeoff = takeoff + c['fm_takeoff_delta'] if takeoff is not None else None
            if new_takeoff is None or empty is None or new_takeoff <= empty:
                problems.append('%s: недопустимый Takeoff %s при EmptyMass %s' %
                                (c['id'], new_takeoff, empty))
            else:
                path = 'fm/%s%s%s.blk' % (PREFIX, c['unit'].lower(), c.get('suffix', ''))
                c['_fm_copy'] = ('content/pkg_local/gameData/flightModels/' + path,
                                 gun_file_text(fm_stock, c['title'],
                                               override_path(fm, 'Mass/Takeoff', new_takeoff)), path)
        if c.get('fm_power_field'):
            fm_rel = u.get('fmFile')
            fm_stock = 'gameData/flightModels/' + fm_rel if fm_rel else ''
            fm_data = aces.get(fm_stock.lower()) if fm_stock else None
            fm = rd.parse(fm_data) if fm_data else None
            edits = []
            for i in (0, 1):
                path = 'EngineType%d/%s' % (i, c['fm_power_field'])
                node = fm.block('EngineType%d' % i) if fm else None
                for part in c['fm_power_field'].split('/')[:-1]:
                    node = node.block(part) if node else None
                value = node.get(c['fm_power_field'].split('/')[-1]) if node else None
                if value is None or value <= 0:
                    problems.append('%s: нет положительной мощности %s' % (c['id'], path))
                else:
                    edits.append(override_path(fm, path, round(value * 1.5, 2)))
            if len(edits) == 2:
                path = 'fm/%s%s%s.blk' % (PREFIX, c['unit'].lower(), c.get('suffix', ''))
                c['_fm_copy'] = ('content/pkg_local/gameData/flightModels/' + path,
                                 gun_file_text(fm_stock, c['title'], ''.join(edits)), path)
        if c.get('weapons') and c['weapons'] not in presets:
            problems.append('%s: нет пресета %s (есть: %s)' % (c['id'], c['weapons'], presets[:5]))
        mods = [m.name for m in (u.block('modifications').blocks if u.block('modifications') else [])]
        for m in c.get('modifications', []):
            if m not in mods:
                problems.append('%s: нет модификации %s' % (c['id'], m))
        c['_all_mods'] = mods
        if c.get('bullets'):
            # снаряд должен быть блоком в файле основного орудия (commonWeapons, первый Weapon)
            w = u.block('commonWeapons').block('Weapon') if u.block('commonWeapons') else None
            wdata = aces.get((w.get('blk') or '').lower()) if w else None
            gun = rd.parse(wdata) if wdata else None
            names = [b.name for b in gun.blocks] if gun else []
            gc = c.get('gun_copy')
            if gc and gun:
                c['_gun'] = w.get('blk')
                extra = []
                for path, value in gc.get('edits', []):
                    try:
                        extra.append(override_path(gun, path, value))
                    except KeyError as e:
                        problems.append('%s: %s' % (c['id'], e))
                for sname, src in gc.get('shells', []):
                    sdata = aces.get(src.lower())
                    sblk = [b for b in rd.parse(sdata).blocks if b.name == sname] if sdata else []
                    if not sblk:
                        problems.append('%s: в %s нет снаряда %s' % (c['id'], src, sname))
                    elif sname in names:
                        problems.append('%s: снаряд %s уже есть в орудии' % (c['id'], sname))
                    else:
                        # блок донора целиком, обычным блоком (добавляется в конец, override_format.md п. 3)
                        extra.append('// снаряд из %s\n' % src + B.to_text(B.Block(None, blocks=[sblk[0]])))
                        names.append(sname)
                c['_gun_extra'] = ''.join(extra)
            for bname, _cnt in c['bullets']:
                if bname and bname not in names:
                    problems.append('%s: в файле орудия %s нет снаряда %s' % (c['id'], w.get('blk') if w else '?', bname))
        if c.get('unit_edits'):
            text, probs = unit_edits(u, c['unit_edits'])
            problems += ['%s: %s' % (c['id'], p) for p in probs]
            c['_unit_edits'] = text
        if c.get('target_pair'):
            tdata = aces.get('gamedata/units/tankmodels/%s.blk' % c['target_unit'].lower())
            problems += target_copies(c, rd.parse(tdata) if tdata else None)
        if c.get('file_copies') or c.get('new_files'):
            def load_copy(p):
                d = aces.get(p.lower())
                return rd.parse(d) if d else None
            problems += prepare_file_copies(c, load_copy)
            problems += fm_link_problems(c, u, load_copy)
        if c.get('weapon_copy'):
            def load(p):
                d = aces.get(p.lower())
                return rd.parse(d) if d else None
            files, unit_text, probs = weapon_copies(u, load, WEAPON_COPIES[c['weapon_copy']])
            problems += ['%s: %s' % (c['id'], p) for p in probs]
            c['_wcopy'] = (files, unit_text)
        if c.get('sensor_copy'):
            def load_sensor(p):
                d = aces.get(p.lower())
                return rd.parse(d) if d else None
            files, unit_text, probs, changes = sensor_copy(u, load_sensor, SENSOR_COPIES[c['sensor_copy']], c['title'])
            problems += ['%s: %s' % (c['id'], p) for p in probs]
            c['_sensor'] = (files, unit_text, changes)
        if c.get('air_target'):
            cls = AIR_TARGETS[c['air_target']]['unit_class']
            if aces.get('gamedata/flightmodels/%s.blk' % cls.lower()) is None:
                problems.append('%s: нет файла самолёта-мишени %s' % (c['id'], cls))
        if emitter_unit(c):
            def load_any(p):
                d = aces.get((p or '').lower())
                return rd.parse(d) if d else None
            problems += emitter_problems(c, u, load_any)
        for _n, cls, _tm in (TARGETS if c.get('targets') else []):
            if aces.get('gamedata/units/tankmodels/%s.blk' % cls.lower()) is None:
                problems.append('%s: нет файла мишени %s' % (c['id'], cls))
        if c.get('bake'):
            c['_bake'] =M_mods.bake_text(u, mods_blk, c.get('chosen', ()))
        if c.get('launcher'):
            sp = u.block('supportPlanes')
            refs = [p.get('class') for p in sp.blocks] if sp else []
            want = 'tankModels/' + c['launcher']
            if not refs or any(r != want for r in refs):
                problems.append('%s: supportPlanes не такие, как ожидалось: %s' % (c['id'], refs))
            c['_launcher_count'] = len(refs)
            if aces.get('gamedata/units/tankmodels/%s.blk' % c['launcher'].lower()) is None:
                problems.append('%s: нет файла пусковой %s' % (c['id'], c['launcher']))
    return problems


def game_loader(game_dir):
    """load(путь в игре) -> Block из aces.vromfs.bin установленной игры (для resolve_file)."""
    aces = Vromfs(os.path.join(game_dir, 'aces.vromfs.bin'))
    rd = B.BinaryReader.for_vromfs(aces)

    def load(path):
        data = aces.get((path or '').replace('#/develop/gameBase/', '').lower())
        if data is None:
            raise FileNotFoundError(path)
        return rd.parse(data)
    return load


def report_unit_edits(load, items, cases):
    """Печатает итог check_unit_edits; возвращает число ошибок."""
    bad = 0
    for rel, problem, got in check_unit_edits(load, items, cases):
        print('итог %s: %s%s' % (rel.split('/')[-1], 'ОШИБКА: ' + problem if problem else 'ок',
                                 ''.join(' %s=%r' % pv for pv in got)))
        bad += bool(problem)
    return bad


def datamine_loader(dm_dir):
    """load(путь в игре) -> Block по JSON датамайна: <dm>/aces.vromfs.bin_u/<путь в нижнем регистре>x."""
    def load(path):
        p = os.path.join(dm_dir, 'aces.vromfs.bin_u', (path or '').replace('#/develop/gameBase/', '').lower() + 'x')
        if not os.path.isfile(p):
            return None
        with open(p, encoding='utf-8') as f:
            return B.from_blkx(json.load(f))
    return load


DATAMINE_KEYS = {'id', 'title', 'kind', 'unit', 'suffix', 'spawn', 'mtype', 'weapons', 'air_target', 'sensor_copy',
                 'unit_edits', 'bullets', 'shared_title', 'target_unit', 'target_pair', 'file_copies', 'loc_csv',
                 'mission_file_stem', 'ground_emitter', 'copy_title', 'loadout', 'fm_file', 'new_files'}


def target_copies(c, stock):
    """Правки копий мишени пункта (target_pair) по стоковому файлу мишени: c['_targets'] = {ключ: текст правок}.
    Возвращает проблемы."""
    if stock is None:
        return ['%s: нет мишени %s' % (c['id'], c['target_unit'])]
    problems, c['_targets'] = [], {}
    for key in c['target_pair']:
        if key:
            text, probs = unit_edits(stock, R28_TARGETS[key][2])
            problems += ['%s: мишень %s: %s' % (c['id'], key, p) for p in probs]
            c['_targets'][key] = text
    return problems


def check_against_datamine(load, cases):
    """Облачная проверка без игры (только пункты из DATAMINE_KEYS, например 26–28-й круги): машина, пресет, мишень,
    копия сенсора, снаряды основного орудия и правки файлов машины и мишеней по датамайну. Перед установкой всё равно нужен check_against_game по установленной игре."""
    problems = []
    for c in cases:
        extra = set(c) - DATAMINE_KEYS - {k for k in c if k.startswith('_')}
        if extra:
            problems.append('%s: по датамайну не проверяю поля %s' % (c['id'], sorted(extra)))
            continue
        u = load('gameData/%s/%s.blk' % (KINDS[c['kind']][1], c['unit']))
        if u is None:
            problems.append('%s: нет машины %s' % (c['id'], c['unit']))
            continue
        presets = [p.get('name') for p in (u.block('weapon_presets').blocks if u.block('weapon_presets') else [])]
        if c.get('loadout'):
            # своя подвеска (31-й круг) — как в check_against_game; правки файлов оружия — только через file_copies
            cfg = AIR_LOADOUTS[c['loadout']]
            if cfg.get('weapon_edits'):
                problems.append('%s: weapon_edits по датамайну не проверяю' % c['id'])
                continue
            files, unit_text, probs = air_loadout(u, cfg, c['unit'])
            problems += ['%s: %s' % (c['id'], p) for p in probs]
            c['_wcopy'] = (files, unit_text)
            presets += list(cfg['presets'])
            problems += fm_link_problems(c, u, load)
        if c.get('weapons') and c['weapons'] not in presets:
            problems.append('%s: нет пресета %s' % (c['id'], c['weapons']))
        if c.get('air_target') and load('gameData/flightModels/%s.blk' % AIR_TARGETS[c['air_target']]['unit_class']) is None:
            problems.append('%s: нет самолёта-мишени' % c['id'])
        problems += emitter_problems(c, u, load)
        if c.get('sensor_copy'):
            files, unit_text, probs, changes = sensor_copy(u, load, SENSOR_COPIES[c['sensor_copy']], c['title'])
            problems += ['%s: %s' % (c['id'], p) for p in probs]
            c['_sensor'] = (files, unit_text, changes)
        if c.get('unit_edits'):
            text, probs = unit_edits(u, c['unit_edits'])
            problems += ['%s: %s' % (c['id'], p) for p in probs]
            c['_unit_edits'] = text
        if c.get('bullets'):
            # как в check_against_game: снаряд — блок файла основного орудия (commonWeapons, первый Weapon)
            w = u.block('commonWeapons').block('Weapon') if u.block('commonWeapons') else None
            gun = load(w.get('blk')) if w and w.get('blk') else None
            names = [b.name for b in gun.blocks] if gun else []
            for bname, _cnt in c['bullets']:
                if bname and bname not in names:
                    problems.append('%s: в файле орудия %s нет снаряда %s' % (c['id'], w.get('blk') if w else '?', bname))
        if c.get('target_pair'):
            problems += target_copies(c, load('gameData/units/tankModels/%s.blk' % c['target_unit']))
        problems += prepare_file_copies(c, load)
    return problems


# ------------------------------------------------------------------ план записи

def plan(cases):
    """[(относительный путь от папки игры, текст)]"""
    out = []
    for c in cases:
        block, folder = KINDS[c['kind']]
        if c.get('real_name'):
            # машина из ангара под настоящим именем: файла копии нет, только миссия
            out.append(('%s/%s.blk' % (MISSION_DIR, c['id']), mission(c, c['unit'])))
            continue
        if c.get('existing_user_vehicle'):
            out.append(('%s/%s.blk' % (MISSION_DIR, c['id']),
                        mission(c, 'userVehicles/' + c['unit'])))
            continue
        if c.get('donor'):
            # слот машины из ангара: userVehicles/<donor>.blk с содержимым c['unit']
            extra = c.get('_bake', '')
            if c.get('_wcopy'):
                out += c['_wcopy'][0]
                extra = c['_wcopy'][1] + extra
            out.append(('content/pkg_local/gameData/%s/userVehicles/%s.blk' % (folder, c['donor']),
                        unit_file_text(folder, c['unit'], c.get('shared_title', c['title']), extra)))
            out.append(('%s/%s.blk' % (MISSION_DIR, c['id']), mission(c, 'userVehicles/' + c['donor'])))
            continue
        # suffix — вторая копия той же машины с другими правками (иначе файлы пунктов совпадут)
        name = PREFIX + c['unit'].lower() + c.get('suffix', '')
        extra = ''
        if c.get('launcher'):
            lname = PREFIX + c['launcher'].lower()
            extra = sam_overrides(lname, c.get('_launcher_count', 2))
            out.append(('content/pkg_local/gameData/%s/%s.blk' % (folder, lname),
                        unit_file_text(folder, c['launcher'], c['title'] + ' (пусковая)')))
        if c.get('gun_copy') and c.get('_gun'):
            gpath = os.path.dirname(c['_gun']) + '/' + gun_copy_name(c['_gun'])
            out.append(('content/pkg_local/' + gpath, gun_file_text(c['_gun'], c['title'], c.get('_gun_extra', ''))))
            # после запекания: модификация (дымы) пишет commonWeapons заново (@delete + блок) — правка до неё теряется
            after = gun_ref_override(gpath)
        else:
            after = ''
        if c.get('_wcopy'):
            out += c['_wcopy'][0]
            extra += c['_wcopy'][1]
        if c.get('_legacy'):
            out += c['_legacy'][0]
            extra += c['_legacy'][1]
        assert not c.get('sensor_copy') or c.get('_sensor'), 'копия сенсора не подготовлена: ' + c['id']
        if c.get('_sensor'):
            out += c['_sensor'][0]
            extra += c['_sensor'][1]
        assert not c.get('unit_edits') or c.get('_unit_edits'), 'правки машины не подготовлены: ' + c['id']
        assert not (c.get('file_copies') or c.get('new_files')) or c.get('_files'), \
            'копии файлов не подготовлены: ' + c['id']
        out += c.get('_files', [])
        extra += c.get('_unit_edits', '')
        for key in c.get('target_pair', ()):
            if key:
                # копия мишени: include стока + правки; один файл на все миссии, где она стоит
                assert key in c.get('_targets', {}), 'правки мишени не подготовлены: %s %s' % (c['id'], key)
                out.append(('content/pkg_local/gameData/units/tankModels/%s.blk' % target_copy_name(c, key),
                            unit_file_text('units/tankModels', c['target_unit'], '28-й круг, ' + R28_TARGETS[key][1],
                                           c['_targets'][key])))
        if c.get('_fm_copy'):
            out.append(c['_fm_copy'][:2])
            extra += '"@override:fmFile":t=%s\n' % B.quote(c['_fm_copy'][2])
        if c.get('fm_file'):
            assert c['fm_file'] in [x[1] for x in c.get('file_copies', [])], 'копии ЛМ нет в file_copies: ' + c['id']
            # копия ЛМ — из file_copies (уже в out); ссылка — относительно gameData/flightModels, как fmFile в стоке
            extra += '"@override:fmFile":t=%s\n' % B.quote(c['fm_file'][len('gameData/flightModels/'):])
        shared = c.get('weapon_copy') or c.get('loadout') or c.get('legacy_loadout')
        title = c.get('shared_title') or (c['title'] if not shared else 'копия для пунктов %s' % shared)
        out.append(('content/pkg_local/gameData/%s/%s.blk' % (folder, name),
                    unit_file_text(folder, c['unit'], title, extra + c.get('_bake', '') + after)))
        stem = c.get('mission_file_stem', c['id'])
        out.append(('%s/%s.blk' % (MISSION_DIR, stem), mission(c, name)))
        if c['id'] in ROUND25_IDS:
            key = c['loc_name_key']
            unit_key = name + '_1'
            csv = ('"<ID|readonly|noverify>";"<English>";"<Russian>"\n'
                   '"%s";"WTP localization probe";"WTP ЛОКАЛИЗАЦИЯ РАБОТАЕТ"\n'
                   '"%s";"A-26B localized test";"А-26Б локализованная копия"\n'
                   '"%s";"A-26B localized test";"А-26Б локализованная копия"\n'
                   '"%s_shop";"A-26B localized test";"А-26Б локализованная копия"\n'
                   '"%s_0";"A-26B localized test";"А-26Б локализованная копия"\n'
                   '"%s_2";"Aircraft";"Самолёт"\n'
                   '"missions/%s/date";"25 October 2026";"25 октября 2026"\n' %
                   (key, unit_key, name, name, name, name, stem))
            out.append(('%s/usr_%s.csv' % (MISSION_DIR, stem), csv))
        if c.get('loc_csv'):
            # 29-й круг: ключи имён копий оружия и снаряда рядом с миссией (как 25-й круг; имя файла = mission{name})
            assert stem == PREFIX + c['id'], 'CSV не совпадёт с mission{name}: ' + c['id']
            out.append(('%s/usr_%s.csv' % (MISSION_DIR, stem), '"<ID|readonly|noverify>";"<English>";"<Russian>"\n'
                        + ''.join('"%s";"%s";"%s"\n' % row for row in c['loc_csv'])))
    # общие файлы (одна копия машины на несколько пунктов) — один раз; разный текст по одному пути — ошибка
    seen, uniq = {}, []
    for path, text in out:
        if path in seen:
            assert seen[path] == text, 'разные файлы по одному пути: ' + path
            continue
        seen[path] = text
        uniq.append((path, text))
        if path.endswith('.blk'):
            B.parse_text(text)  # не пишем того, что сами не можем разобрать
    return uniq


# ------------------------------------------------------------------ запись / откат (wtpoligon/install.py)

def remove(game_dir, app_dir, dry_run=False):
    return I.remove(game_dir, app_dir, dry_run, mission_dir=MISSION_DIR)


def round33_items(game_dir):
    """Dev 2A8 and only BLK dependencies absent from the normal client."""
    from dxp_extract import build, parse
    from dynmodel_extract import DEV, build as build_descriptor

    dev = Vromfs('cache/dev/aces.vromfs.bin')
    normal = Vromfs(os.path.join(game_dir, 'aces.vromfs.bin'))
    reader = B.BinaryReader.for_vromfs(dev)
    root = 'gamedata/units/tankmodels/germ_leopard_2a8.blk'
    queue, missing, visited = [root], {}, set()
    while queue:
        path = queue.pop(0).lower()
        if path in visited:
            continue
        visited.add(path)
        raw = dev.get(path)
        if raw is None:
            raise ValueError('Dev aces lacks referenced BLK: ' + path)
        block = reader.parse(raw)
        if normal.get(path) is None or path == root:
            missing[path] = block

        def references(node):
            for key, _type, value in node.params:
                if isinstance(value, str) and value.lower().endswith('.blk'):
                    ref = value.lower().replace('#/develop/gamebase/', '')
                    if ref.startswith('gamedata/'):
                        queue.append(ref)
            for child in node.blocks:
                references(child)
        references(block)

    def copy_path(source):
        parent, name = source.rsplit('/', 1)
        if source == root:
            return parent + '/wtp5t_dev_leopard_2a8.blk'
        return parent + '/wtp5t_dev_' + name

    copied = {source: copy_path(source) for source in missing}
    items = []
    for source, block in sorted(missing.items()):
        body = B.to_text(block)
        for original, dest in copied.items():
            # The text serializer preserves the reference spelling from the BLK.
            import re
            body = re.sub(re.escape(original), dest, body, flags=re.IGNORECASE)
        rel = 'content/pkg_local/' + copied[source]
        B.parse_text(body)
        items.append((rel, body))
    model = Path('cache/dev/tanks/germ_leopard_2a8.grp').read_bytes()
    if model[:4] != b'GRP2':
        raise ValueError('Dev model is not GRP2')
    source_dxp = Path('cache/dev/tanks/germ_gm_bq.dxp.bin').read_bytes()
    pack = build(source_dxp)
    if len(parse(pack)) != 12:
        raise ValueError('incomplete Leopard texture pack')
    items.extend([
        ('content/pkg_local/res/wtp5t_dev_leopard_2a8.grp', model),
        ('content/pkg_local/res/wtp5t_dev_leopard_2a8.dxp.bin', pack),
    ])
    descriptor_rel = 'content/pkg_local/res/dynModelDesc.bin'
    restore = load_manifest(ROUND33_APP_DIR).get('restores', {}).get(descriptor_rel)
    chroma_path = Path(ROUND33_APP_DIR, restore['backup']) if restore else Path(game_dir, descriptor_rel)
    chroma = chroma_path.read_bytes()
    items.append((descriptor_rel, build_descriptor(chroma, DEV.read_bytes())))
    case = {'id': 'wtp5t_r33_leopard_2a8', 'title': '33. Leopard 2A8 Dev на полигоне',
            'kind': 'tank', 'unit': 'germ_leopard_2a8', 'spawn': 'firing_range',
            'mtype': 'testFlight', 'weapons': 'tank_weapon_preset_default',
            'bullets': [('120mm_DM_APDS_FS', 20)], 'targets': True}
    items.append((MISSION_DIR + '/' + case['id'] + '.blk', mission(case, 'wtp5t_dev_leopard_2a8')))
    return items, sorted(missing)


def round33_write(game_dir, items, app_dir, dry_run=False):
    """Preflight all files, then preserve the foreign descriptor before replacement."""
    rel = 'content/pkg_local/res/dynModelDesc.bin'
    ok, man, adoption = I.adopt_original(game_dir, app_dir, rel, dry_run=True)
    if not ok:
        return False, adoption
    ok, preview = write(game_dir, items, app_dir, dry_run=True, manifest=man)
    if not ok or dry_run:
        return ok, adoption + preview
    ok, man, adoption = I.adopt_original(game_dir, app_dir, rel)
    if not ok:
        return False, adoption
    ok, report = write(game_dir, items, app_dir, manifest=man)
    return ok, adoption + report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=os.path.expandvars(r'%LOCALAPPDATA%\WarThunder'))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--remove', action='store_true', help='убрать все свои файлы')
    ap.add_argument('--round19', action='store_true', help='только новые миссии 22–29, отдельный манифест')
    ap.add_argument('--round20', action='store_true', help='только новые миссии 30–33, отдельный манифест')
    ap.add_argument('--round21', action='store_true', help='только новая миссия 34, отдельный манифест')
    ap.add_argument('--round22', action='store_true', help='миссия 35: свой пресет вертолёта через подтверждённый userVehicles')
    ap.add_argument('--round23', action='store_true', help='миссии 36–37: поле Takeoff ЛМ без подвески')
    ap.add_argument('--round24', action='store_true', help='миссии 38–39: мощность двух двигателей A-26B')
    ap.add_argument('--round25', action='store_true', help='миссия 40: локализация копии A-26B через usr_*.csv')
    ap.add_argument('--round26', action='store_true', help='миссии 41–42: дальность РЛС F-15C копией файла сенсора')
    ap.add_argument('--round27', action='store_true',
                    help='миссии 43–48: физика Т-80БВМ, «Тигра» H1, Fletcher (контроль Fletcher — миссия 4)')
    ap.add_argument('--round28', action='store_true',
                    help='миссии 49–53: броня, экипаж, боеукладка копии мишени «Тигр» H1')
    ap.add_argument('--round29', action='store_true',
                    help='миссии 54–58: СПО, ИК-головка AIM-9M, ловушки F-15C, имена копий орудия и снаряда «Тигра»')
    ap.add_argument('--round30', action='store_true',
                    help='миссии 59–62: СПО F-15C с излучателем — МиГ-23М с включённой РЛС и ЗРК «Тор-М1»')
    ap.add_argument('--round31', action='store_true',
                    help='миссии 63–66: сопротивление ФАБ-9000 на A-26B при компенсированной массе (EmptyMass)')
    ap.add_argument('--round32', action='store_true',
                    help='миссии 67–69: наземная ЗУР на пилоне F-15C — что роняет игру (формат или наведение)')
    ap.add_argument('--round33', action='store_true', help='Leopard 2A8 Dev, отдельный манифест')
    ap.add_argument('--datamine', help='без игры: проверить по клону датамайна и показать файлы (--round26–32)')
    # 5-й круг 24.10: справочники из pkg_local/config игра не читает (updateAllUnits: 3509) — по умолчанию выключено
    ap.add_argument('--registry', action='store_true',
                    help='эксперимент §7.9: записать pkg_local/config/{unittags,wpcost}.blk (игра их не читает)')
    a = ap.parse_args(argv)
    if sum((a.round19, a.round20, a.round21, a.round22, a.round23, a.round24, a.round25, a.round26, a.round27,
            a.round28, a.round29, a.round30, a.round31, a.round32, a.round33)) > 1:
        ap.error('флаги отдельных кругов несовместимы')
    if a.datamine and (not (a.round26 or a.round27 or a.round28 or a.round29 or a.round30 or a.round31
                            or a.round32) or a.remove):
        ap.error('--datamine только вместе с --round26…--round32 и без --remove')
    if a.round33:
        if a.registry or a.datamine:
            ap.error('--round33 несовместим с --registry/--datamine')
        if a.remove:
            for line in remove(a.game, ROUND33_APP_DIR, a.dry_run):
                print(line)
            return 0
        try:
            items, absent = round33_items(a.game)
        except (OSError, ValueError) as exc:
            print('План 33-го круга не готов:', exc)
            return 1
        print('Недостающие BLK:', ', '.join(absent))
        for rel, content in items:
            data = content if isinstance(content, bytes) else content.encode('utf-8')
            print('план: %s — %d байт, SHA-256 %s' % (rel, len(data), sha(data)))
        ok, report = round33_write(a.game, items, ROUND33_APP_DIR, a.dry_run)
        for line in report:
            print(line)
        if a.dry_run:
            print('Только --dry-run: в игру ничего не записано; манифест не создан.')
        return 0 if ok else 1
    app_dir = (ROUND32_APP_DIR if a.round32 else ROUND31_APP_DIR if a.round31 else ROUND30_APP_DIR if a.round30 else ROUND29_APP_DIR if a.round29 else ROUND28_APP_DIR if a.round28 else ROUND27_APP_DIR if a.round27 else ROUND26_APP_DIR if a.round26 else ROUND25_APP_DIR if a.round25 else ROUND24_APP_DIR if a.round24 else ROUND23_APP_DIR if a.round23 else ROUND22_APP_DIR if a.round22 else ROUND21_APP_DIR if a.round21 else ROUND20_APP_DIR if a.round20 else
               ROUND19_APP_DIR if a.round19 else APP_DIR)
    cases = ([c for c in CASES if c['id'] in ROUND32_IDS] if a.round32 else
             [c for c in CASES if c['id'] in ROUND31_IDS] if a.round31 else
             [c for c in CASES if c['id'] in ROUND30_IDS] if a.round30 else
             [c for c in CASES if c['id'] in ROUND29_IDS] if a.round29 else
             [c for c in CASES if c['id'] in ROUND28_IDS] if a.round28 else
             [c for c in CASES if c['id'] in ROUND27_IDS] if a.round27 else
             [c for c in CASES if c['id'] in ROUND26_IDS] if a.round26 else
             [c for c in CASES if c['id'] in ROUND25_IDS] if a.round25 else
             [c for c in CASES if c['id'] in ROUND24_IDS] if a.round24 else
             [c for c in CASES if c['id'] in ROUND23_IDS] if a.round23 else
             [c for c in CASES if c['id'] in ROUND22_IDS] if a.round22 else
             [c for c in CASES if c['id'] in ROUND21_IDS] if a.round21 else
             [c for c in CASES if c['id'] in ROUND20_IDS] if a.round20 else
             [c for c in CASES if c['id'] in ROUND19_IDS] if a.round19 else STANDARD_CASES)
    if a.remove:
        for s in remove(a.game, app_dir, a.dry_run):
            print(s)
        return 0
    if a.datamine:
        problems = check_against_datamine(datamine_loader(a.datamine), cases)
        if problems:
            print('Не совпадает с датамайном:')
            for s in problems:
                print('  ', s)
            return 1
        items = plan(cases)
        for rel, text in items:
            print('=== %s\n%s' % (rel, text if not (rel.startswith(MISSION_DIR) and rel.endswith('.blk')) else '(миссия, %d строк)' % text.count('\n')))
        bad = report_unit_edits(datamine_loader(a.datamine), items, cases)
        print('Только показ: в игру ничего не записано. Установка — локально, без --datamine.')
        return 1 if bad else 0
    problems = check_against_game(a.game, cases)
    if problems:
        print('Не совпадает с установленной игрой, ничего не пишу:')
        for s in problems:
            print('  ', s)
        return 1
    items = plan(cases)
    if report_unit_edits(game_loader(a.game), items, cases):
        print('Итог правок не совпал с заданным, ничего не пишу')
        return 1
    if a.round27:
        # контроль Fletcher — уже установленная миссия 4: только сверить (без записи), что она та же, что у генератора
        controls = [c for c in CASES if c['id'] in set(ROUND27_CONTROLS.values())]
        if not check_against_game(a.game, controls):
            for rel, text in plan(controls):
                full = os.path.join(a.game, rel)
                same = False
                if os.path.isfile(full):
                    with open(full, 'rb') as f:
                        same = f.read() == text.encode('utf-8')
                print('контроль (не трогаю): %s — %s' % (rel, 'совпадает с генератором' if same else
                                                        'НЕ совпадает или нет — сравнение с ней ненадёжно'))
    if a.round22:
        original = next(c for c in CASES if c['id'] == 't11_uv_heli')
        old_problems = check_against_game(a.game, [original])
        if old_problems:
            print('Не могу сверить исходный файл миссии 11:', old_problems)
            return 1
        expected = dict(plan([original]))[ROUND22_ADOPT_PATH].encode('utf-8')
        full = os.path.join(a.game, ROUND22_ADOPT_PATH)
        actual = None
        if os.path.isfile(full):
            with open(full, 'rb') as f:
                actual = f.read()
        if actual != expected:
            print('Исходный userVehicles/mi_28nm.blk изменился; миссию 35 не устанавливаю')
            return 1
    if a.registry:
        items += registry_files(a.game)
    ok, report = write(a.game, items, app_dir, a.dry_run)
    for s in report:
        print(s)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
