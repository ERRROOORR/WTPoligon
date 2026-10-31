> Русская версия: [README.ru.md](README.ru.md)

# WT Poligon

WT Poligon is a builder for War Thunder single player custom test-drive missions. It aims to let you choose any vehicle, assemble an aircraft loadout, mount weapons on pylons, and change characteristics through local BLK copies using `include` and `@override`. Original game archives remain untouched; managed files are tracked for rollback. An unavailable or unowned vehicle may run as a custom copy with reduced interface or equipment behavior.

**Status: closed beta (Beta-1.0).** Download and install instructions are below, in English and Russian.

## Download and install (Beta-1.0)

**[⬇ Download WT Poligon Beta-1.0](https://github.com/ERRROOORR/WTPoligon/releases/download/v1.0-beta/WTPoligon-Beta-1.0-public.zip)** (83 MB, Windows) · [all releases](https://github.com/ERRROOORR/WTPoligon/releases)

1. Download `WTPoligon-Beta-1.0-public.zip` and extract it to any folder (do not run it from inside the archive).
2. Open the extracted folder and double-click **`run.bat`**. Python is bundled — nothing else to install.
   If Windows warns about the file, choose “More info” → “Run anyway”.
3. The program finds War Thunder by itself (`%LOCALAPPDATA%\WarThunder` or Steam); otherwise point it to the game
   folder (the one with `aces.vromfs.bin`). The first start takes up to a minute while it reads the game files.
4. Pick a vehicle → go through the steps → “Проверка и запись” (Review and write) → “Записать в игру” (Write to game).
5. In the game: **Single missions → Custom → “WTP5 — <vehicle>”**. No game restart needed.

Remove everything the program wrote: “Проверка и запись” → “Откатить всё”. Remove the program: delete its folder.
Something broken? “Проверка и запись” → **“Логи”** (bottom right) and send the archive from the `logs` folder.
The interface is in Russian for now. Vehicle pictures in the list are not shown in this public build.

### Скачать и установить — по-русски

**[⬇ Скачать WT Poligon Beta-1.0](https://github.com/ERRROOORR/WTPoligon/releases/download/v1.0-beta/WTPoligon-Beta-1.0-public.zip)** (83 МБ, Windows) · [все версии](https://github.com/ERRROOORR/WTPoligon/releases)

1. Скачайте `WTPoligon-Beta-1.0-public.zip` и распакуйте в любую папку (не запускайте прямо из архива).
2. Откройте распакованную папку и дважды щёлкните **`run.bat`**. Python внутри — ничего ставить не нужно.
   Если Windows предупредит о файле — «Подробнее» → «Выполнить в любом случае».
3. Программа сама найдёт War Thunder (`%LOCALAPPDATA%\WarThunder` или Steam); если нет — укажите папку игры
   (где лежит `aces.vromfs.bin`). Первый запуск — до минуты: программа читает файлы игры.
4. Выберите технику → пройдите шаги → «Проверка и запись» → **«Записать в игру»**.
5. В игре: **Одиночные миссии → Пользовательские → «WTP5 — <машина>»**. Перезапуск игры не нужен.

Удалить всё, что записала программа: «Проверка и запись» → «Откатить всё». Удалить программу — удалить её папку.
Что-то не работает — «Проверка и запись» → **«Логи»** (справа внизу) и пришлите архив из папки `logs`.
В этой публичной сборке нет картинок техники в списке.

| Capability | Status |
|---|---|
| Installed-game vehicle and weapon catalog, mission generator, basic desktop window | Implemented in development build |
| Aircraft loadout builder, custom pylons and tested air-compatible missile conversions | Implemented; core paths verified in game |
| Weightless loadout through a flight-model copy | Mechanism verified in game; GUI edge cases still being checked |
| General characteristics editor | In development |
| Ammunition, sensors, project library, sharing, packaged release | Planned; selected file edits researched in game |

The catalog is derived from the installed game. We label each technical claim **Verified in game**, **Unverified (in files only)**, or **No effect**. “No effect” means no observable effect in the stated test. Every new capability needs a file-level explanation and an in-game check before it is presented as working.

## Documentation

- [Datamining index](docs/en/datamine/index.md): [VROMFS](docs/en/datamine/vromfs.md), [BLK](docs/en/datamine/blk.md), [overrides](docs/en/datamine/override.md), [logs](docs/en/datamine/game-logs.md), [caching](docs/en/datamine/caching.md), [tools](docs/en/datamine/tools.md), [CDK](docs/en/datamine/cdk.md)
- [Missions](docs/en/datamine/user-missions.md), [aircraft](docs/en/datamine/aircraft.md), [pylons](docs/en/datamine/pylons.md), [weapons and ammunition](docs/en/datamine/weapons-ammo.md), [sensors](docs/en/datamine/sensors.md), [ground and naval vehicles](docs/en/datamine/ground-naval.md), [armor and crew](docs/en/datamine/armor-crew.md), [modifications](docs/en/datamine/modifications.md), [localization](docs/en/datamine/localization.md), [failures](docs/en/datamine/failures.md)
- [Program overview](docs/en/program/overview.md), [roadmap](docs/en/program/roadmap.md), [contributing](CONTRIBUTING.md)

## License and notice

The documentation is licensed under [CC BY 4.0](LICENSE). Program source code will be published later under a separate license. WT Poligon is an unofficial project. War Thunder is a trademark of Gaijin Entertainment. No game files, extracted game data, or game images are distributed here.
