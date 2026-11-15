# WT Poligon

Test-drive builder for War Thunder: any vehicle, any weapon on any pylon and your own characteristics in a
single-player mission.

## Features

- **Any Vehicle:** ground vehicles, aircraft, helicopters and ships, including vehicles you don't own
- **Any Weapon on Any Pylon:** including SAMs from ground vehicles and ships
- **Characteristics:** engine power and thrust, mass, radar, RWR, countermeasures, reload time
- **Ammunition:** any shell of the game in the ammo rack, with its own mass, explosive and velocity
- **Called-in Vehicles:** drones and escorts
- **Scenarios:** targets by battle rating or by hand, duels, map, weather, time of day, rules
- **Safe for the Game:** game files stay untouched, one button removes everything the program added

**Status:** closed beta 2.0-beta. What to test: [docs/TESTING.md](docs/TESTING.md).

## What's New in 2.0-beta

Called-in vehicles, saved vehicles, Mistel with any aircraft and radar setup in every mode.

- **Called-in Vehicles:** any aircraft as your drone, tanks and SAM launchers as escort, saved vehicles included
- **My Vehicles:** save a configured vehicle and open it later; saved vehicles show up in search
- **Mistel:** hang any aircraft under any carrier, with an explosive or nuclear warhead
- **Radar:** scan angles in every mode, up to 360° in close combat, and detection range
- **Ammunition Restore:** as in the game's test drive
- **Nuclear Charge:** for bombs, missiles and shells
- **Reload:** any reload time, down to instant
- **Missile Pods:** ×2 and ×4 on any pylon
- **No Map Borders**
- **Program Log:** included in the Logs archive
- **Game 2.61:** all vehicles launch again, Characteristics open instantly, search handles typos everywhere

Full list: [CHANGELOG.md](CHANGELOG.md).

## Download and Install

**[⬇ Download WT Poligon 2.0-beta](https://github.com/ERRROOORR/WTPoligon/releases/download/v2.0-beta/WTPoligon-2.0-beta.zip)**
(Windows, 83 MB) · [all releases](https://github.com/ERRROOORR/WTPoligon/releases)

1. Extract the archive to any folder (it does not run from inside the archive)
2. Run **`run.bat`**; Python is included. If Windows warns you, choose "More info" → "Run anyway"
3. The program finds War Thunder by itself; if not, select the game folder (the one with `aces.vromfs.bin`)
4. Pick a vehicle, go through the steps, press **Write to game**
5. In the game: **Single missions → Custom → "WTP5 — <vehicle>"**, no restart needed

- **Remove:** "Roll back all" on the last step removes everything the program added; to remove the program, delete its
  folder
- **Problems:** press **"Logs"** on the last step and send the archive from the `logs` folder
- **Language:** the interface is in Russian; English is planned

---

# WT Poligon (RU)

Конструктор тестовых выездов для War Thunder: любая техника, любое оружие на любом пилоне и свои характеристики
в одиночной миссии.

## Возможности

- **Любая техника:** наземка, самолёты, вертолёты и корабли, в том числе те, которых нет в ангаре
- **Любое оружие на любом пилоне:** в том числе ЗУР наземки и кораблей
- **Характеристики:** мощность и тяга двигателя, масса, РЛС, СПО, ловушки, время перезарядки
- **Боеприпасы:** любой снаряд игры в боекомплекте, со своей массой, ВВ и скоростью
- **Вызываемая техника:** дроны и сопровождение
- **Сценарии:** цели по БР или вручную, дуэли, карта, погода, время суток, правила
- **Безопасно для игры:** файлы игры не меняются, одна кнопка убирает всё, что добавила программа

**Состояние:** закрытая бета 2.0-beta. Что проверять — [docs/TESTING.md](docs/TESTING.md).

## Что нового в 2.0-beta

Вызываемая техника, сохранение техники, Mistel с любым самолётом и настройка РЛС во всех режимах.

- **Вызываемая техника:** любой самолёт как дрон, танки и пусковые ЗРК в сопровождение, в том числе своя техника
- **Моя техника:** сохранить настроенную машину и открыть позже; сохранённые машины есть в поиске
- **Mistel:** любой самолёт под любым носителем, с боевой частью из взрывчатки или ядерной
- **РЛС:** углы обзора во всех режимах, в ближнем бою до 360°, и дальность обнаружения
- **Пополнение боезапаса:** как в тест-драйве игры
- **Ядерный заряд:** для бомб, ракет и снарядов
- **Перезарядка:** любое время перезарядки, вплоть до мгновенной
- **Контейнеры с ракетами:** ×2 и ×4 на любом пилоне
- **Без границ карты**
- **Журнал программы:** входит в архив «Логи»
- **Игра 2.61:** снова запускается вся техника, «Характеристики» открываются мгновенно, поиск везде понимает опечатки

Полный список — [CHANGELOG.md](CHANGELOG.md).

## Скачать и установить

**[⬇ Скачать WT Poligon 2.0-beta](https://github.com/ERRROOORR/WTPoligon/releases/download/v2.0-beta/WTPoligon-2.0-beta.zip)**
(Windows, 83 МБ) · [все версии](https://github.com/ERRROOORR/WTPoligon/releases)

1. Распакуйте архив в любую папку (из архива программа не запускается)
2. Запустите **`run.bat`**, Python уже внутри. При предупреждении Windows — «Подробнее» → «Выполнить в любом случае»
3. Программа сама находит War Thunder; если нет — укажите папку игры (где лежит `aces.vromfs.bin`)
4. Выберите технику, пройдите шаги, нажмите **«Записать в игру»**
5. В игре: **Одиночные миссии → Пользовательские → «WTP5 — <машина>»**, перезапуск не нужен

- **Удаление:** «Откатить всё» на последнем шаге убирает всё, что добавила программа; программа удаляется вместе
  с папкой
- **Проблемы:** кнопка **«Логи»** на последнем шаге, пришлите архив из папки `logs`

---

## How It Works / Как это устроено

- **Reads your game / Читает вашу игру:** vehicles, weapons, names and icons come from the installed War Thunder and
  are re-read after game updates / техника, оружие, названия и иконки берутся из установленной игры и перечитываются
  после обновлений
- **Hangar vehicles / Машины из ангара:** a vehicle you own launches as itself, others as a copy that may miss some
  interface elements / своя машина выезжает как есть, остальные — копией, у которой может не быть части интерфейса
- **For modders / Для моддеров:** a user mission in `UserMissions` and small BLK copies in `content/pkg_local`
  (`include` + `@override`), see the [datamine reference](docs/en/datamine/index.md) / пользовательская миссия
  в `UserMissions` и небольшие копии BLK в `content/pkg_local`, см. [справочник](docs/ru/datamine/index.md)

---

## License / Лицензия

- **Program / Программа** — [GPL v3](LICENSE) with an author attribution requirement / с условием указывать автора
  ([NOTICE.md](NOTICE.md)): credit “WT Poligon by ERRROOORR” / «WT Poligon — автор ERRROOORR».
- **Documentation / Документация** — [CC BY 4.0](docs/LICENSE).

WT Poligon is an unofficial project. War Thunder is a trademark of Gaijin Entertainment. No game files are distributed.
WT Poligon — неофициальный проект. War Thunder — товарный знак Gaijin Entertainment. Файлы игры не распространяются.

## Documentation / Документация

- **Program / Программа:** [overview](docs/en/program/overview.md) · [roadmap](docs/en/program/roadmap.md) ·
  [user guide](docs/en/program/user-guide.md) · [developer guide](docs/en/program/developer-guide.md) ·
  [обзор](docs/ru/program/overview.md) · [план](docs/ru/program/roadmap.md) ·
  [руководство пользователя](docs/ru/program/user-guide.md) · [руководство разработчика](docs/ru/program/developer-guide.md) ·
  [testing / тестирование](docs/TESTING.md)
- **Datamine / Датамайн:** [index (EN)](docs/en/datamine/index.md) · [оглавление (RU)](docs/ru/datamine/index.md) —
  VROMFS, BLK, `@override`, game logs, missions, aircraft, pylons, weapons, sensors, ground and naval vehicles…
- **Contributing / Как помочь:** [CONTRIBUTING.md](CONTRIBUTING.md) · [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md)
- **Run from source / Запуск из исходников:** Python 3.12, `pip install -r requirements.txt`,
  `python -m wtpoligon` (window) · tests: `python -m unittest discover -s tests`
