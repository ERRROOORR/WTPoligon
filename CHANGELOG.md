# Changelog / Журнал изменений

## 2.0-beta — 2026-11-15, closed beta

- New step *Called-in vehicles*: any aircraft as a drone, tanks and SAM launchers as escort, own saved vehicles.
- *My vehicles*: save, open, rename and delete configured vehicles.
- Bomb planes (Mistel): any carrier, any aircraft below, its warhead (explosive or nuclear: nuclear damage, ordinary
  visuals). One per aircraft.
- Radar: coverage in all modes including close combat and tracking, plus the cue area. Detection range changes the
  transmitters, the displayed range and the scale. Passive receivers are not changed.
- *Restore ammunition* = "Limited ammunition: No" (`isLimitedAmmo=no`).
- Nuclear charge in *Ammunition*; *Reload* in *Characteristics*; *Restore ammunition* in *Scenario*. One gun copy per
  vehicle with all edits merged. *Reset ammo rack* button.
- Missile containers keep all missiles on other aircraft's pylons. Empty pylons can't be selected. Custom loadout
  together with a gun copy. No guns/belts block in *Ammunition* for aircraft.
- No return-to-battle zone on narrow maps (level copy with wide borders) — 📄 not verified.
- Program log `logs\wtpoligon.log`, also in the *Logs* archive.
- Fixes for game 2.61: lowercase weapon paths, mission names without hyphens, aircraft without `fmFile`, service entry
  `dummy_plane` hidden, *Characteristics* cache.
- Only "not verified" marks in the window.

## Beta-1.0 — 2026-10-31, closed beta

First public release of the program code.

- Steps: Vehicle → Loadout (aircraft) → Characteristics → Ammunition → Scenario → Review and write.
- Any vehicle, any weapon on any pylon, weightless loadout; engine, mass, radar, RWR and countermeasure edits; ammo
  rack and shell edits; scenarios with targets by battle rating; rollback; "Logs" button.
- 📄 = not verified in game: afterburner thrust, radar angles, ammunition edits, most scenario options.

---

## 2.0-beta — 15.11.2026, закрытая бета

- Новый шаг «Вызываемая техника»: любой самолёт как дрон, танки и пусковые ЗРК в сопровождение, своя сохранённая
  техника.
- «Моя техника»: сохранение, открытие, переименование и удаление настроенных машин.
- Самолёты-бомбы (Mistel): любой носитель, любой самолёт снизу, его боевая часть (взрывчатка или ядерная: урон
  ядерный, вид обычный). Один на самолёт.
- РЛС: обзор во всех режимах, в том числе НСЦ и сопровождение, и область наведения. Дальность обнаружения меняет
  передатчики, зону отображения целей и шкалу. Пассивные приёмники не меняются.
- «Пополнять боезапас» = «Ограниченный боезапас: Нет» (`isLimitedAmmo=no`).
- Ядерный заряд в «Боеприпасах»; «Перезарядка» в «Характеристиках»; «Пополнять боезапас» в «Сценарии». Одна копия
  орудия со всеми правками. Кнопка «Сбросить боекомплект».
- Контейнеры с ракетами на чужом пилоне — со всеми ракетами. Пустые пилоны не выбираются. Своя подвеска вместе
  с копией пушки. У авиации в «Боеприпасах» нет блока «Пушки, ленты».
- Без зоны возврата на узких картах (копия уровня с широкой границей) — 📄 не проверено.
- Журнал программы `logs\wtpoligon.log`, он же в архиве «Логи».
- Исправления под игру 2.61: пути к оружию строчными, имена миссий без дефиса, самолёты без `fmFile`, скрыта служебная
  запись `dummy_plane`, кэш «Характеристик».
- В окне только пометки «не проверено».

## Beta-1.0 — 31.10.2026, закрытая бета

Первая публикация кода программы.

- Шаги: Техника → Подвеска (авиация) → Характеристики → Боеприпасы → Сценарий → Проверка и запись.
- Любая техника, любое оружие на любой пилон, невесомая подвеска; правка двигателя, массы, РЛС, СПО и ловушек;
  правка боекомплекта и снарядов; сценарии с подбором целей по БР; откат; кнопка «Логи».
- 📄 — в игре не проверено: тяга на форсаже, углы РЛС, правки боеприпасов, большинство настроек сценария.
