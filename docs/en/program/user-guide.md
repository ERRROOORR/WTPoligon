> Русская версия: [../../ru/program/user-guide.md](../../ru/program/user-guide.md)

# User guide (2.0-beta)

The window is in Russian. This guide gives Russian control names next to English step names.

## Start

1. On Windows, extract the beta ZIP and run `run.bat`; from source, run `python -m wtpoligon`.
2. The program finds the installed War Thunder or asks for its folder (the one with `aces.vromfs.bin`). The first
   catalog build takes up to a minute.
3. Choose a vehicle, move with **Далее →** (Next) or the step buttons at the top, finish with **Записать в игру**
   (Write to game).

## 1. Vehicle / «Техника»

- Search by Russian or English name or internal ID; typos and wrong keyboard layout are tolerated.
- Filters: type, nation, rank.
- **«Есть в моём ангаре»** (in my hangar) — only for a vehicle you own. It launches under its real identity with the
  normal interface. An unowned vehicle launches as a copy and may lose some modifications or icons.
- A false ownership mark makes the game exit the mission immediately.
- Filter **«Только из моего ангара»** (only in my hangar).
- Saved vehicles (*My vehicles*) appear in the search together with game vehicles.

## 2. Loadout / «Подвеска»

Aircraft and helicopters only; skipped for tanks and ships.

- Start from a stock preset and select a pylon by number.
- **«Штатное для пилона»** — the pylon's stock options; **«Любое оружие игры»** — the full weapon catalog with
  search. A separate checkbox adds tank, ship and SAM weapons.
- Number of attachment points; **«Снять»** clears a pylon; **«Зеркально»** copies to the paired pylon (check the
  pair number).
- Pylons without available weapons can't be selected. Missile containers (×2, ×4) go on any pylon.
- **«Мои пресеты»** — save and load your own presets.
- The summary shows mass, limits, balance and counts. **«Невесомая подвеска»** (weightless loadout) compensates
  payload mass.
- Bomb plane (Mistel): when a pylon holds a weapon that releases a bomb plane, the **«Самолёт под подвеской»**
  (aircraft below) block appears — any aircraft of the game, **«Взрывчатка, кг»** (explosive, kg) or **«Ядерная»**
  (nuclear). A bomb plane goes on one pylon only. A nuclear warhead deals nuclear damage; the blast looks ordinary.
- A custom loadout uses a vehicle copy even when you own the original; a stock preset can keep the real vehicle.

## 3. Characteristics / «Характеристики»

- Pick a section; edit the overall value or individual fields. The overall value scales linked fields; editing a
  field updates the overall value.
- Sections depend on the vehicle: engines, mass, radar, RWR, countermeasures, reload, names.
- Radar: scan angles in every mode, close combat included, and detection range.
- **«Перезарядка»** (reload) — reload time in seconds, down to instant.
- Each row shows the stock value, BLK path, unit and evidence status. **«Все параметры (дерево)»** — searchable
  field tree. **«Сброс»** resets the section.
- Red values are invalid and block writing; amber values are outside the stock range.
- A new CSV name appears only after a game restart.

## 4. Ammunition / «Боеприпасы»

- Ground and naval vehicles: choose a gun and fill up to four slots with a shell and a count. Watch **«Заряжено»**
  (loaded) against capacity.
- **«Выбрать орудие…»** searches gun file names; **«+»** searches a shell, gun or vehicle and adds a shell from the
  game.
- A selected shell can be edited; **«Все параметры · дерево»** shows all typed fields.
- **«Ядерный заряд»** (nuclear charge) — for bombs, missiles and shells.
- Aircraft and helicopters: belts and rounds per barrel; they have no ground-gun block.
- **«Сбросить боекомплект»** restores the stock slots.

## 5. Called-in vehicles / «Вызываемая техника»

- The list shows the vehicle's stock called-in units.
- An aircraft can be set as the vehicle's drone; tanks and SAM launchers as escort. Ground units have a count.
- **«Заменить»** (replace) and **«Убрать»** (remove) act on a list row.
- **«+ Добавить технику»** (add) searches game vehicles and your saved vehicles (called in with their loadout).

## 6. Scenario / «Сценарий»

- The vehicle sets the mode: ground, aircraft, helicopter or naval; aircraft also have a duel.
- Player BR drives automatic picks. **«Подобрать по БР»** fills target categories; then set counts, distances,
  whether targets shoot, bot radar.
- Add or remove a specific target; **«Перебрать категорию»** rerolls a category.
- Map (where offered), time, weather, game mode.
- Aircraft: start altitude and speed; helicopters can start on the ground.
- Duel: opponent, its loadout, count, distance, altitude, whether it shoots.
- Rules: markers, target restore, infinite fuel, mode options.
- **«Пополнять боезапас»** (restore ammunition) — as in the game's test drive.
- Map borders are removed.

## 7. Review and write / «Проверка и запись»

- Shows the launch mode, edits, scenario, warnings and the exact file list.
- Errors disable **«Записать в игру»**. If writing is available, confirm the game folder and write.
- The mission appears at **Single missions → Custom → "WTP5 — <vehicle>"** without a restart.
- **«Сохранить как свою технику»** / **«Открыть свою технику»** — *My vehicles*. A saved vehicle can be opened,
  renamed and deleted.
- The lower table lists the program's installs and file states. **«Откатить эту машину»**, **«Откатить выбранное»**,
  **«Откатить всё»** roll back the current, selected or all installs.
- Rollback removes only what the program added; files you changed yourself stay.
- **«Логи»** (Logs) packs recent game logs, the program log (`%LOCALAPPDATA%\WTPoligon5\logs\wtpoligon.log`) and the
  program's records into a ZIP in the `logs` folder next to the program and opens the folder. Send the ZIP with the
  vehicle and the steps taken when reporting a problem.

## Common problems

| Symptom | What to check |
|---|---|
| Game not found | Select the installed game folder with `aces.vromfs.bin`. |
| Mission exits at once | Clear **«Есть в моём ангаре»** if the vehicle is not owned; write again. |
| Custom loadout lacks an interface item or modification | It launches as a copy. Try a stock preset or an owned vehicle. |
| **Write to game** is disabled | Select a vehicle, wait for loading, read the validation errors. A datamine source needs an explicit game folder. |
| New name does not appear | Restart the game after a CSV name change. |
| Mission or weapon fails in game | Roll back the install, collect **«Логи»**. |
