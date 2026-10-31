> Русская версия: [../../ru/program/user-guide.md](../../ru/program/user-guide.md)

# User guide (Beta-1.0)

The current window is in Russian. This guide names its controls in Russian alongside English step names.

## Start

On Windows, extract the beta ZIP and run `run.bat`, or run `python -m wtpoligon` from source. The program finds an installed War Thunder or asks for its folder, which contains `aces.vromfs.bin`. Building the first catalog can take up to a minute. Choose a vehicle, use **Далее →** (Next) or the step buttons, and finish with **Записать в игру** (Write to game).

**«Проверено в игре»** (verified in game) marks behavior with an in-game test. **«Не проверено»** (not verified) and **📄** mean that the option is derived from game files but its gameplay behavior still needs testing. A successful pre-write check only validates generated files. See the [tester checklist](../../TESTING.md).

## 1. Vehicle / «Техника»

Search by Russian or English name or internal ID; search tolerates typos and keyboard-layout mistakes. Filter by vehicle type, nation and rank. Pick an aircraft, helicopter, ground vehicle or ship. Mark **«Есть в моём ангаре»** only if you own it. An owned vehicle can launch under its real identity with its normal interface; an unowned one launches as a copy and may lose some modifications or icons. You can filter to **«Только из моего ангара»** (only in my hangar). A false ownership mark can make the game exit the mission immediately.

## 2. Loadout / «Подвеска»

This step applies to aircraft and helicopters; it is skipped for tanks and ships. Start from a stock preset, then select a numbered pylon. **«Штатное для пилона»** lists its normal options; **«Любое оружие игры»** searches the wider weapon catalog. The extra checkbox includes tank, ship and SAM weapons; these unusual combinations are marked 📄 where untested. Set the number of attachment points, clear a pylon with **«Снять»**, or copy to a suggested partner with **«Зеркально»**; check the partner number. Save and load your own named presets from **«Мои пресеты»**. The summary shows total mass, limits, balance and counts. **«Невесомая подвеска»** compensates payload mass. A custom loadout uses a vehicle copy even when you own the original; a stock preset can keep the real vehicle.

## 3. Characteristics / «Характеристики»

Pick a section and edit its overall value or individual parameters. The overall value changes linked fields proportionally; changing a field updates the overall figure. Available sections depend on the vehicle and can include engines, mass, radar, warning receivers, countermeasures and names. Rows show the stock value, BLK path, unit and evidence status; **«Все параметры (дерево)»** offers a searchable field tree. **«Сброс»** resets a section. Red invalid values block writing; amber values are outside the observed stock range. Changing names in the mission CSV may require restarting the game before they appear.

## 4. Ammunition / «Боеприпасы»

For ground and naval vehicles, choose a gun and fill up to four mission ammunition slots with a shell and count. Watch **«Заряжено»** against capacity. **«Выбрать орудие…»** searches gun file names; **«+»** searches a shell, gun or carrier and adds a shell from the installed game. Select a shell to inspect and edit its fields; **«Все параметры · дерево»** exposes the typed field tree. Aircraft and helicopters instead show gun belts and rounds per barrel. **«Сбросить боекомплект»** restores the stock slot choices. The ammunition workflow is a priority 📄 area in the [tester checklist](../../TESTING.md); verify the result in battle.

## 5. Scenario / «Сценарий»

The selected vehicle sets the available mode: ground, aircraft, helicopter or naval; aircraft and helicopters can also choose a duel. Set the player BR for automatic target selection. **«Подобрать по БР»** fills target categories; adjust category counts, distances and whether targets shoot or use radar. Add or remove a specific target, or **«Перебрать категорию»** to reroll it. Choose map where offered, time, weather and game mode. Aircraft controls include start altitude and speed; helicopters can start on the ground. A duel lets you choose the opponent, its loadout, count, starting distance, altitude and whether it shoots. Rules include markers, restoring targets and ammo, infinite fuel, fast reload and mode-specific options. Read each **«проверено в игре» / «не проверено»** badge; many scenario combinations still need gameplay testing.

## 6. Review and write / «Проверка и запись»

Inspect launch mode, edits, scenario, warnings and the exact file list. Errors disable **«Записать в игру»**. If writing is available, confirm the target game folder and write. The mission appears at **Single missions → Custom → “WTP5 — <vehicle>”** without a restart. The lower table lists the program's recorded installs and file states. **«Откатить эту машину»**, **«Откатить выбранное»** and **«Откатить всё»** roll back the current, selected or all recorded installs. Rollback removes only program-owned files whose hash still matches and restores originals it backed up; files changed afterward are left in place. Review the rollback report.

**«Логи»** collects recent game logs and the program's records into a ZIP in the `logs` folder next to the program and opens that folder. Send the ZIP with the vehicle, steps taken and what happened when reporting a problem.

## Common problems

| Symptom | What to check |
|---|---|
| Game not found | Select the installed game folder containing `aces.vromfs.bin`. |
| Mission exits at once | Clear **«Есть в моём ангаре»** if the vehicle is not owned; write again. |
| Custom loadout lacks an interface item or modification | It launches as a copy. Try a stock preset or an owned vehicle under its real identity. |
| **Write to game** is disabled | Select a vehicle, wait for loading and read validation errors. A datamine source also needs an explicit target game folder. |
| New name does not appear | Restart the game after a CSV name change. |
| Mission or weapon fails in game | Note any 📄 status, roll back the install and collect **«Логи»**. |
