# WT Poligon

WT Poligon is a builder for War Thunder single player custom test-drive missions. It aims to let you choose any vehicle, assemble an aircraft loadout, mount weapons on pylons, and change characteristics through local BLK copies using `include` and `@override`. Original game archives remain untouched; managed files are tracked for rollback. An unavailable or unowned vehicle may run as a custom copy with reduced interface or equipment behavior.

**Status: closed beta (Beta-1.0).** Download and install instructions are below.

## Download and install (Beta-1.0)

**[⬇ Download WT Poligon Beta-1.0](https://github.com/ERRROOORR/WTPoligon/releases/download/v1.0-beta/WTPoligon-Beta-1.0.zip)** (83 MB, Windows) · [all releases](https://github.com/ERRROOORR/WTPoligon/releases)

1. Download `WTPoligon-Beta-1.0.zip` and extract it to any folder (do not run it from inside the archive).
2. Open the extracted folder and double-click **`run.bat`**. Python is bundled — nothing else to install.
   If Windows warns about the file, choose “More info” → “Run anyway”.
3. The program finds War Thunder by itself (`%LOCALAPPDATA%\WarThunder` or Steam); otherwise point it to the game
   folder (the one with `aces.vromfs.bin`). The first start takes up to a minute while it reads the game files.
4. Pick a vehicle → go through the steps → “Проверка и запись” (Review and write) → “Записать в игру” (Write to game).
5. In the game: **Single missions → Custom → “WTP5 — <vehicle>”**. No game restart needed.

Remove everything the program wrote: “Проверка и запись” → “Откатить всё”. Remove the program: delete its folder.
Something broken? “Проверка и запись” → **“Логи”** (bottom right) and send the archive from the `logs` folder.

## Documentation

- [Datamining index](docs/en/datamine/index.md): [VROMFS](docs/en/datamine/vromfs.md), [BLK](docs/en/datamine/blk.md), [overrides](docs/en/datamine/override.md), [logs](docs/en/datamine/game-logs.md), [caching](docs/en/datamine/caching.md), [tools](docs/en/datamine/tools.md), [CDK](docs/en/datamine/cdk.md)
- [Missions](docs/en/datamine/user-missions.md), [aircraft](docs/en/datamine/aircraft.md), [pylons](docs/en/datamine/pylons.md), [weapons and ammunition](docs/en/datamine/weapons-ammo.md), [sensors](docs/en/datamine/sensors.md), [ground and naval vehicles](docs/en/datamine/ground-naval.md), [armor and crew](docs/en/datamine/armor-crew.md), [modifications](docs/en/datamine/modifications.md), [localization](docs/en/datamine/localization.md), [failures](docs/en/datamine/failures.md)
- [Program overview](docs/en/program/overview.md), [roadmap](docs/en/program/roadmap.md), [contributing](CONTRIBUTING.md)

## License and notice

The documentation is licensed under [CC BY 4.0](LICENSE). The program is licensed under GPL v3 with an author attribution requirement (`LICENSE` and `NOTICE.md` inside the download): keep the notice and credit “WT Poligon by ERRROOORR” when sharing or showing it. WT Poligon is an unofficial project. War Thunder is a trademark of Gaijin Entertainment. No game files, extracted game data, or game images are distributed here.

---

WT Poligon — конструктор одиночных пользовательских миссий-тестдрайвов War Thunder. Цель — выбирать любую технику, собирать авиационную подвеску, ставить оружие на пилоны и менять характеристики через локальные копии BLK с `include` и `@override`. Оригинальные архивы игры не трогаются; записанные программой файлы учитываются для отката. Недоступная или отсутствующая в ангаре машина может запускаться как копия с ограничениями интерфейса и оборудования.

**Статус: закрытая бета (Beta-1.0).** Как скачать и установить — ниже.

## Скачать и установить (Beta-1.0)

**[⬇ Скачать WT Poligon Beta-1.0](https://github.com/ERRROOORR/WTPoligon/releases/download/v1.0-beta/WTPoligon-Beta-1.0.zip)** (83 МБ, Windows) · [все версии](https://github.com/ERRROOORR/WTPoligon/releases)

1. Скачайте `WTPoligon-Beta-1.0.zip` и распакуйте в любую папку (не запускайте прямо из архива).
2. Откройте распакованную папку и дважды щёлкните **`run.bat`**. Python внутри — ничего ставить не нужно.
   Если Windows предупредит о файле — «Подробнее» → «Выполнить в любом случае».
3. Программа сама найдёт War Thunder (`%LOCALAPPDATA%\WarThunder` или Steam); если нет — укажите папку игры
   (где лежит `aces.vromfs.bin`). Первый запуск — до минуты: программа читает файлы игры.
4. Выберите технику → пройдите шаги → «Проверка и запись» → **«Записать в игру»**.
5. В игре: **Одиночные миссии → Пользовательские → «WTP5 — <машина>»**. Перезапуск игры не нужен.

Удалить всё, что записала программа: «Проверка и запись» → «Откатить всё». Удалить программу — удалить её папку.
Что-то не работает — «Проверка и запись» → **«Логи»** (справа внизу) и пришлите архив из папки `logs`.

| Возможность | Статус |
|---|---|
| Каталог техники и оружия из установленной игры, создание миссии, базовое окно | Сделано в разрабатываемой версии |
| Конструктор авиационной подвески, свои пилоны и проверенная переделка ракет для самолёта | Сделано; основные сценарии проверены в игре |
| Невесомая подвеска через копию ЛМ | Способ проверен в игре; крайние случаи интерфейса ещё проверяются |
| Общий редактор характеристик | В разработке |
| Боеприпасы, сенсоры, библиотека проектов, обмен, собранная версия | В планах; отдельные правки файлов исследованы в игре |

Каталог строится из установленной игры. Каждое техническое утверждение помечается **Verified in game**, **Unverified (in files only)** или **No effect**. «No effect» означает отсутствие видимого эффекта в описанной проверке. Для новой возможности нужны объяснение на уровне файлов и проверка в игре.

## Документация

- [Оглавление датамайна](docs/ru/datamine/index.md): [VROMFS](docs/ru/datamine/vromfs.md), [BLK](docs/ru/datamine/blk.md), [правки](docs/ru/datamine/override.md), [логи](docs/ru/datamine/game-logs.md), [кэш](docs/ru/datamine/caching.md), [инструменты](docs/ru/datamine/tools.md), [CDK](docs/ru/datamine/cdk.md)
- [Миссии](docs/ru/datamine/user-missions.md), [авиация](docs/ru/datamine/aircraft.md), [пилоны](docs/ru/datamine/pylons.md), [оружие и боеприпасы](docs/ru/datamine/weapons-ammo.md), [сенсоры](docs/ru/datamine/sensors.md), [наземная техника и флот](docs/ru/datamine/ground-naval.md), [броня и экипаж](docs/ru/datamine/armor-crew.md), [модификации](docs/ru/datamine/modifications.md), [локализация](docs/ru/datamine/localization.md), [неудачные подходы](docs/ru/datamine/failures.md)
- [Как устроена программа](docs/ru/program/overview.md), [план развития](docs/ru/program/roadmap.md), [как помочь](CONTRIBUTING.ru.md)

## Лицензия и уведомление

Документация распространяется по [CC BY 4.0](LICENSE). Программа — по лицензии GPL v3 с условием указывать автора (`LICENSE` и `NOTICE.md` в архиве): при распространении и показе сохраняйте уведомление и указывайте «WT Poligon — автор ERRROOORR». WT Poligon — неофициальный проект. War Thunder — товарный знак Gaijin Entertainment. Файлы игры, извлечённые данные и изображения игры здесь не распространяются.
