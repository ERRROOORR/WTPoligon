# WT Poligon

**WT Poligon** is a free open-source test-drive builder for **War Thunder**. You pick a vehicle, change its
parameters, and the program writes a single-player test mission into the game.

The game's test drive runs a vehicle only with stock parameters. WT Poligon can:

- launch **any vehicle of the game**: ground vehicles, aircraft, helicopters, ships;
- put **any weapon of the game on any pylon**, including SAMs of ground vehicles and ships;
- change **characteristics**: engine power and thrust, mass, radar range and scan angles, RWR, countermeasures;
- change **ammunition**: any shell of the game in the ammo rack, its mass, explosive and velocity;
- build a **scenario**: targets by battle rating or by hand, duels, weather, time, rules;
- **roll back**: game files are not modified, everything the program wrote can be removed.

**Status: closed beta (2.0-beta).** What to test: [docs/TESTING.md](docs/TESTING.md).

## What's new in 2.0-beta

- **Called-in vehicles** — new step. Any aircraft as a drone of your vehicle, tanks and SAM launchers as escort,
  vehicles from *My vehicles*.
- **My vehicles** — a configured vehicle can be saved and opened later. Saved vehicles appear in the vehicle search.
- **Bomb planes (Mistel)** — on any aircraft, with **any aircraft** below. The aircraft below gets a warhead:
  explosive mass or nuclear. A nuclear warhead deals nuclear damage, the explosion looks ordinary.
- **Radar** (verified in game) — coverage changes in all modes, including close combat (up to 360°). Detection range
  changes the target display area, the scale and the transmitters.
- **Restore ammunition** — works as "Limited ammunition: No" in the game's test drive: ammunition is restored after
  everything is fired.
- **Nuclear charge** for bombs, missiles and shells in *Ammunition*. **Reload** section in *Characteristics*,
  down to instant reload.
- Missile containers (×2, ×4) carry all their missiles on any pylon. Pylons without weapons can't be selected.
- **No "Return to the battlefield" on the firing range** — for narrow maps the program writes a level copy with wide
  borders (📄 not verified in game).
- **Program log** — `%LOCALAPPDATA%\WTPoligon5\logs\wtpoligon.log`. The *Logs* button adds it to the archive.
- Fixes for game version 2.61: writing to the game works; vehicles with a hyphen in the name and aircraft without an
  explicit flight model launch; *Characteristics* reopen instantly; search tolerates typos everywhere. The window
  shows only "not verified" marks.

Full list: [CHANGELOG.md](CHANGELOG.md).

## Download and install

**[⬇ Download WT Poligon 2.0-beta](https://github.com/ERRROOORR/WTPoligon/releases/download/v2.0-beta/WTPoligon-2.0-beta.zip)**
(Windows, 83 MB) · [all releases](https://github.com/ERRROOORR/WTPoligon/releases)

1. Download the archive and extract it to any folder. The program does not run from inside the archive.
2. Run **`run.bat`**. Python is included.
   If Windows shows a warning, choose "More info" → "Run anyway".
3. The program finds War Thunder automatically. If not, select the game folder (the one with `aces.vromfs.bin`).
   The first start takes up to a minute: the program reads the game files.
4. Select a vehicle → go through the steps → **Write to game**.
5. In the game: **Single missions → Custom → "WTP5 — <vehicle>"**. The game does not need a restart.

Removing everything the program wrote: "Roll back all" on the last step. Removing the program: delete its folder.
Problems: press **"Logs"** on the last step and send the archive from the `logs` folder.
The interface is in Russian; English is planned.

---

**WT Poligon** — бесплатный конструктор тестовых выездов для **War Thunder** с открытым кодом. Вы выбираете
технику, меняете её параметры, программа записывает в игру одиночную тестовую миссию.

Тестовый выезд в игре запускает машину только со стоковыми параметрами. WT Poligon умеет:

- запускать **любую технику игры**: наземку, самолёты, вертолёты, корабли;
- вешать **любое оружие игры на любой пилон**, в том числе ЗУР наземки и кораблей;
- менять **характеристики**: мощность и тягу двигателя, массу, дальность и углы обзора РЛС, СПО, ловушки;
- менять **боеприпасы**: любой снаряд игры в боекомплекте, его массу, ВВ, скорость;
- собирать **сценарий**: цели по БР или вручную, дуэли, погода, время, правила;
- **откатывать** записанное: файлы игры не меняются, всё записанное программой удаляется.

**Состояние: закрытая бета (2.0-beta).** Что проверять — [docs/TESTING.md](docs/TESTING.md).

## Что нового в 2.0-beta

- **Вызываемая техника** — новый шаг. Любой самолёт как дрон вашей машины, танки и пусковые ЗРК в сопровождение,
  техника из «Моей техники».
- **Моя техника** — настроенную машину можно сохранить и открыть позже. Сохранённые машины есть в поиске техники.
- **Самолёты-бомбы (Mistel)** — на любом самолёте, снизу — **любой самолёт**. У нижнего самолёта боевая часть:
  масса взрывчатки или ядерная. Ядерная наносит ядерный урон, взрыв выглядит обычным.
- **РЛС** (проверено в игре) — обзор меняется во всех режимах, в том числе в ближнем бою (до 360°). Дальность
  обнаружения меняет зону отображения целей, шкалу и передатчики.
- **«Пополнять боезапас»** — работает как «Ограниченный боезапас: Нет» в тест-драйве игры: боезапас пополняется,
  когда всё выпущено.
- **Ядерный заряд** для бомб, ракет и снарядов в «Боеприпасах». Раздел **«Перезарядка»** в «Характеристиках»,
  вплоть до мгновенной.
- Контейнеры с ракетами (×2, ×4) на любом пилоне несут все ракеты. Пилоны без оружия не выбираются.
- **Без «Вернитесь на поле боя» на полигоне** — для узких карт программа пишет копию уровня с широкой границей
  (📄 в игре не проверено).
- **Журнал программы** — `%LOCALAPPDATA%\WTPoligon5\logs\wtpoligon.log`. Кнопка «Логи» кладёт его в архив.
- Исправления под версию игры 2.61: работает запись в игру; запускаются машины с дефисом в имени и самолёты без явной
  лётной модели; «Характеристики» открываются повторно мгновенно; поиск везде учитывает опечатки. В окне только
  пометки «не проверено».

Полный список — [CHANGELOG.md](CHANGELOG.md).

## Скачать и установить

**[⬇ Скачать WT Poligon 2.0-beta](https://github.com/ERRROOORR/WTPoligon/releases/download/v2.0-beta/WTPoligon-2.0-beta.zip)**
(Windows, 83 МБ) · [все версии](https://github.com/ERRROOORR/WTPoligon/releases)

1. Скачайте архив и распакуйте в любую папку. Из архива программа не запускается.
2. Запустите **`run.bat`**. Python входит в архив.
   При предупреждении Windows — «Подробнее» → «Выполнить в любом случае».
3. Программа находит War Thunder сама. Если не нашла — укажите папку игры (где лежит `aces.vromfs.bin`).
   Первый запуск — до минуты: программа читает файлы игры.
4. Выберите технику → пройдите шаги → **«Записать в игру»**.
5. В игре: **Одиночные миссии → Пользовательские → «WTP5 — <машина>»**. Перезапуск игры не нужен.

Удалить всё записанное программой — «Откатить всё» на последнем шаге. Удалить программу — удалить её папку.
При ошибках — кнопка **«Логи»** на последнем шаге, пришлите архив из папки `logs`.

---

## How it works

- **Reads the installed game.** Vehicle list, weapons, names and icons come from the game archives (VROMFS, BLK
  files) and are cached. After a game update the cache is rebuilt automatically.
- **Writes a user mission and copies.** The test drive is a user mission in `UserMissions`. Changed vehicles,
  weapons, radars and shells are written to `content/pkg_local` as copies: a copy includes the original file and
  overrides only the changed fields (`include` + `@override`). The game archives are not modified.
- **Hangar vehicles launch as themselves**, other vehicles as a copy (a copy may lack some interface elements).
- **Every write is recorded** in a manifest with file hashes. Rollback removes exactly what the program wrote and
  restores replaced files.
- **Features are verified in the game first.** Fields found in the game files but not yet verified in the game are
  marked 📄; they need testing most.
- **Python + Qt (PySide6)**, runs from source. Heavy tasks run in background processes, the window does not freeze.

## Как это устроено

- **Читает установленную игру.** Список техники, оружие, названия и иконки берутся из архивов игры (VROMFS, файлы
  BLK) и кэшируются. После обновления игры кэш пересобирается сам.
- **Пишет пользовательскую миссию и копии.** Тестовый выезд — пользовательская миссия в `UserMissions`. Изменённые
  машины, оружие, РЛС и снаряды записываются в `content/pkg_local` копиями: копия подключает исходный файл и меняет
  только изменённые поля (`include` + `@override`). Архивы игры не меняются.
- **Машина из ангара запускается как есть**, остальные — копией (у копии может не быть части интерфейса).
- **Каждая запись учитывается** в манифесте с контрольными суммами. Откат удаляет ровно записанное программой
  и возвращает заменённые файлы.
- **Каждая возможность сначала проверяется в игре.** Поля, которые есть в файлах игры, но в игре не проверены,
  помечены 📄; их проверка нужнее всего.
- **Python + Qt (PySide6)**, запуск из исходников. Тяжёлые задачи идут в фоновых процессах, окно не зависает.

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
