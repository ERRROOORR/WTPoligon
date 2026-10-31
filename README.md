# WT Poligon

**WT Poligon** is a free, open-source test-drive builder for **War Thunder**. Pick any vehicle in the game, change
almost anything about it and get a ready single-player test mission in one click.

The in-game test drive only lets you try a vehicle as it is. WT Poligon lets you:

- launch **any vehicle of the game** — ground, aircraft, helicopters, ships;
- hang **any weapon of the game on any pylon** — including SAMs from tanks and ships on a jet;
- change **characteristics** — engine power and thrust, mass, radar range and scan angles, RWR, countermeasures;
- set up **ammunition** — any shell of the game in the ammo rack, its mass, explosive, velocity;
- build a **scenario** — targets picked automatically by battle rating or by hand, duels, weather, time, rules;
- **roll everything back** — game files are never modified, everything the program writes can be removed.

**Status: closed beta (Beta-1.0).** What to test — [docs/TESTING.md](docs/TESTING.md).

## Download and install

**[⬇ Download WT Poligon Beta-1.0](https://github.com/ERRROOORR/WTPoligon/releases/download/v1.0-beta/WTPoligon-Beta-1.0.zip)**
(Windows, 83 MB) · [all releases](https://github.com/ERRROOORR/WTPoligon/releases)

1. Download the archive and extract it to any folder (do not run it from inside the archive).
2. Double-click **`run.bat`**. Python is bundled — nothing else to install.
   If Windows warns about the file, choose “More info” → “Run anyway”.
3. The program finds War Thunder by itself; otherwise point it to the game folder (the one with `aces.vromfs.bin`).
   The first start takes up to a minute while it reads the game files.
4. Pick a vehicle → go through the steps → **Write to game**.
5. In the game: **Single missions → Custom → “WTP5 — <vehicle>”**. No game restart needed.

To remove everything the program wrote — “Roll back all” on the last step; to remove the program — delete its folder.
Something broken — press **“Logs”** on the last step and send the archive from the `logs` folder.
The interface is in Russian for now; English is planned.

---

**WT Poligon** — бесплатный конструктор тестовых выездов для **War Thunder** с открытым кодом. Выберите любую технику
игры, поменяйте в ней почти всё и получите готовую одиночную миссию в один клик.

Тестовый выезд в игре даёт попробовать машину только как есть. WT Poligon позволяет:

- запустить **любую технику игры** — наземку, самолёты, вертолёты, корабли;
- повесить **любое оружие игры на любой пилон** — вплоть до ЗУР танков и кораблей на истребитель;
- менять **характеристики** — мощность и тягу двигателя, массу, дальность и углы обзора РЛС, СПО, ловушки;
- настроить **боеприпасы** — любой снаряд игры в боекомплект, его массу, ВВ, скорость;
- собрать **сценарий** — цели с автоподбором по БР или вручную, дуэли, погоду, время, правила;
- **всё откатить** — файлы игры не меняются, всё, что записала программа, удаляется.

**Состояние: закрытая бета (Beta-1.0).** Что проверять — [docs/TESTING.md](docs/TESTING.md).

## Скачать и установить

**[⬇ Скачать WT Poligon Beta-1.0](https://github.com/ERRROOORR/WTPoligon/releases/download/v1.0-beta/WTPoligon-Beta-1.0.zip)**
(Windows, 83 МБ) · [все версии](https://github.com/ERRROOORR/WTPoligon/releases)

1. Скачайте архив и распакуйте в любую папку (не запускайте прямо из архива).
2. Дважды щёлкните **`run.bat`**. Python внутри — ничего ставить не нужно.
   Если Windows предупредит о файле — «Подробнее» → «Выполнить в любом случае».
3. Программа сама найдёт War Thunder; если нет — укажите папку игры (где лежит `aces.vromfs.bin`).
   Первый запуск — до минуты: программа читает файлы игры.
4. Выберите технику → пройдите шаги → **«Записать в игру»**.
5. В игре: **Одиночные миссии → Пользовательские → «WTP5 — <машина>»**. Перезапуск игры не нужен.

Удалить всё, что записала программа, — «Откатить всё» на последнем шаге; удалить программу — удалить её папку.
Что-то не работает — кнопка **«Логи»** на последнем шаге, пришлите архив из папки `logs`.

---

## How it works

- **Reads your installed game.** The vehicle list, weapons, names and icons come straight from the game archives
  (VROMFS, BLK files) and are cached; after a game update the program rebuilds the cache by itself.
- **Writes a custom mission and copies.** The test drive is a user mission in `UserMissions`. Changed vehicles,
  weapons, radars and shells are written as small copies in `content/pkg_local` that include the original file and
  override only the changed fields (`include` + `@override`). The game's own archives are never touched.
- **Vehicles you own run as themselves**; others run as a copy (some interface parts may be missing for copies).
- **Everything is tracked.** Each write is recorded in a manifest with file hashes, so a rollback removes exactly what
  the program wrote and restores anything it replaced.
- **Science, not guessing.** Every feature is checked in the game first. Fields that exist in the game files but were
  not yet verified in the game are marked 📄 — these are the most useful to test.
- **Built for the community:** Python + Qt (PySide6), runs from source; the UI never freezes — heavy work runs in
  background processes.

## Как это устроено

- **Читает вашу установленную игру.** Список техники, оружие, названия и иконки берутся прямо из архивов игры
  (VROMFS, файлы BLK) и кэшируются; после обновления игры программа сама пересобирает кэш.
- **Пишет пользовательскую миссию и копии.** Тестовый выезд — пользовательская миссия в `UserMissions`. Изменённые
  машины, оружие, РЛС и снаряды записываются маленькими копиями в `content/pkg_local`: копия подключает исходный
  файл и меняет только нужные поля (`include` + `@override`). Архивы самой игры не трогаются.
- **Машина из вашего ангара запускается как есть**, остальные — копией (у копии может не быть части интерфейса).
- **Всё учитывается.** Каждая запись попадает в манифест с контрольными суммами, поэтому откат удаляет ровно то, что
  записала программа, и возвращает то, что она заменила.
- **Научно, а не наугад.** Каждая возможность сначала проверяется в игре. Поля, которые есть в файлах игры, но в игре
  ещё не проверены, помечены 📄 — их проверять полезнее всего.
- **Для сообщества:** Python + Qt (PySide6), запуск из исходников; окно не зависает — тяжёлая работа идёт в фоне.

---

## License / Лицензия

- **Program / Программа** — [GPL v3](LICENSE) with an author attribution requirement / с условием указывать автора
  ([NOTICE.md](NOTICE.md)): credit “WT Poligon by ERRROOORR” / «WT Poligon — автор ERRROOORR».
- **Documentation / Документация** — [CC BY 4.0](docs/LICENSE).

WT Poligon is an unofficial project. War Thunder is a trademark of Gaijin Entertainment. No game files are distributed.
WT Poligon — неофициальный проект. War Thunder — товарный знак Gaijin Entertainment. Файлы игры не распространяются.

## Documentation / Документация

- **Program / Программа:** [overview](docs/en/program/overview.md) · [roadmap](docs/en/program/roadmap.md) ·
  [обзор](docs/ru/program/overview.md) · [план](docs/ru/program/roadmap.md) · [testing / тестирование](docs/TESTING.md)
- **Datamine / Датамайн:** [index (EN)](docs/en/datamine/index.md) · [оглавление (RU)](docs/ru/datamine/index.md) —
  VROMFS, BLK, `@override`, game logs, missions, aircraft, pylons, weapons, sensors, ground and naval vehicles…
- **Contributing / Как помочь:** [CONTRIBUTING.md](CONTRIBUTING.md) · [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md)
- **Run from source / Запуск из исходников:** Python 3.12, `pip install -r requirements.txt`,
  `python -m wtpoligon` (window) · tests: `python -m unittest discover -s tests`
