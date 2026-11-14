# Changelog / Журнал изменений

## 2.0-beta — 2026-11-15 (closed beta / закрытая бета)
- Radar: coverage in all modes incl. close combat and tracking (+ cue area); detection range = transmitters + displayed
  distance + scale; passive receivers untouched. / РЛС: обзор во всех режимах вкл. НСЦ и сопровождение; дальность —
  передатчики + зона отображения целей + шкала; пассивные приёмники не трогаются.
- Restore ammunition = "Limited ammunition: No" (`isLimitedAmmo=no`). / «Пополнять боезапас» = «Ограниченный боезапас: Нет».
- Missile containers keep all missiles on foreign pylons; empty slots not selectable; own loadout + gun copy;
  aircraft have no guns/belts block in Ammunition. / Контейнеры с ракетами; пустые пилоны; своя подвеска + копия пушки;
  у авиации нет блока «Пушки, ленты».
- Only "not verified" marks in the window. / В окне только пометки «не проверено».
- New step *Called-in vehicles* (any aircraft as a drone, tanks / SAM launchers as escorts, own saved vehicles). /
  Новый шаг «Вызываемая техника» (любой самолёт как дрон, танки / ЗРК в сопровождение, своя техника).
- *My vehicles*: save / open / rename / delete configured vehicles. / «Моя техника»: сохранить, открыть, переименовать, удалить.
- Bomb planes (Mistel): any carrier, any aircraft below, its warhead (explosive or nuclear — nuclear damage, ordinary
  visuals); only one per aircraft. / Самолёты-бомбы (Mistel): любой носитель, любой самолёт снизу, его боевая часть
  (взрывчатка или ядерная — урон ядерный, вид обычный); один на самолёт.
- Nuclear charge in *Ammunition*; *Reload* in *Characteristics*; *Restore ammunition* in *Scenario*; one gun copy per
  vehicle with all edits merged; *Reset ammo rack* button. / Ядерный заряд, «Перезарядка», «Пополнять боезапас»;
  одна копия орудия со всеми правками; кнопка «Сбросить боекомплект».
- No return-to-battle zone on narrow maps (own level copy with wide borders) — 📄 unverified. /
  Без зоны возврата на узких картах (своя копия уровня) — 📄 не проверено.
- Program log `logs\wtpoligon.log` (also in the *Logs* archive). / Журнал программы (и в архиве «Логи»).
- Game 2.61 fixes: lowercase weapon paths, mission names without hyphens, aircraft without `fmFile`, service entry
  `dummy_plane` hidden, *Characteristics* cache. / Исправления под игру 2.61.

## Beta-1.0 — 2026-10-31 (closed beta / закрытая бета)
First public release of the program code. / Первая публикация кода программы.
- Steps: Vehicle → Loadout (aircraft) → Characteristics → Ammunition → Scenario → Review and write.
  Шаги: Техника → Подвеска (авиация) → Характеристики → Боеприпасы → Сценарий → Проверка и запись.
- Any vehicle, any weapon on any pylon, weightless loadout, engine/mass/radar/RWR/countermeasure edits, ammo rack and
  shell edits, scenarios with BR-based target picking, rollback, “Logs” button.
- 📄 = not yet verified in game: afterburner thrust, radar angles, ammunition edits, most scenario options.
