> Русская версия: [../../ru/program/developer-guide.md](../../ru/program/developer-guide.md)

# Developer guide (2.0-beta)

## Run and code map

Python 3.12 on Windows: `pip install -r requirements.txt`, then `python -m wtpoligon`.

- Without arguments the entry point goes through `wtpoligon/__main__.py` and `gui/app.py`, which finds the game (or
  takes `--game`), accepts a datamine source (`--datamine`) and an explicit write target (`--target`), loads the
  vehicle index and opens the Qt window.
- A datamine source without `--target` is read-only.
- With a command (`list`, `mission`, `install`, `uninstall`, `status`, `check-all` and others) `cli.py` does the same
  work without the window.

| Package or module | Responsibility |
|---|---|
| `game/` | Reading installed VROMFS and BLK through `source.py`, typed BLK values, vehicle index, name search, images, game logs, modifications. |
| `gui/` | Seven step pages and `window.py`; `texts.py` — Russian UI help; `workers.py` runs heavy jobs outside the Qt event loop. |
| `scenarios/`, `targets.py` | Scenario model, target catalog, BR-based picks, validation, mission fragments. |
| `support/` | Called-in vehicles: model, catalog, build, validation. |
| `ammo/` | Gun and shell catalog, ammunition model, ballistic helpers, validation, copies of changed ammunition. |
| `stats.py` | Characteristic fields per vehicle type, stock values, evidence status, bounds, edits. |
| `loadout.py` | Pylons, stock presets, weapon catalog, custom selections, bomb planes, mass summary, validation. |
| `library.py` | *My vehicles*: saved configurations in the application data folder. |
| `hangar.py` | The user's "in my hangar" marks (`hangar.json`). |
| `build.py`, `edits.py`, `mission.py` | Step models → plan of mission/BLK/CSV files, typed overrides, check of intended values against the source. |
| `install.py` | Output path restrictions, writing managed files, SHA-256 manifests, backups, rollback. |
| `applog.py` | Program log `%LOCALAPPDATA%\WTPoligon5\logs\wtpoligon.log` (2 MB, 3 old copies): start, writes and rollbacks, check and build errors, unhandled exceptions, long steps. |
| `logs.py` | Diagnostic ZIP: program manifests, program log, recent game logs. |

## Data flow

1. `game.source` opens the installed game archives.
2. `game.index` builds a cached vehicle index; loadout, ammo, called-in and scenario catalogs follow game references.
3. Qt pages hold the models of the selected vehicle.
4. `build.stock_plan()` creates the file plan: a user mission and the required local copies.
5. `build.verify_plan()` checks generated BLKs against the current stock tree.
6. `install.install()` writes allowed paths and records hashes in a per-application manifest.
7. `install.uninstall()` removes matching owned files or restores backed-up originals. A file modified since
   installation is left in place.

The game archives are never rewritten. See [BLK overrides](../datamine/override.md),
[user missions](../datamine/user-missions.md) and [caching](../datamine/caching.md).

Background work:

- `gui/workers.py` uses a two-process `ProcessPoolExecutor` with the `spawn` context.
- Workers cache source readers per process and build catalogs, stats, loadout, ammo search, scenario picks, review
  and logs.
- Pages poll futures with `QTimer` and drop stale results by generation number, so a vehicle change does not apply
  an old result.
- Qt widgets stay on the main thread.

## Verify and package

- Tests: `python -m unittest discover -s tests`.
- Whole game: `python -m wtpoligon check-all` builds the mission for every vehicle.
- `tools/ui_lag.py` measures window responsiveness during navigation and catalog work.
- In-game behavior: [docs/TESTING.md](../../TESTING.md), first of all the 📄 items.
- Beta ZIP from a prepared `.venv`: `.venv\Scripts\python tools\make_beta.py --name 2.0-beta`. It packs portable
  Python, dependencies, source, `run.bat` and notices into `dist/`; it does not build an `.exe`.

## Project rules

- Each capability: a source in game data → verified generated output → an in-game test → only then **verified in
  game**.
- Untested fields and combinations are marked **not verified** or **📄**; a passing parser check is not gameplay
  evidence.
- Extracted game files, icons and archives are not committed or distributed.
- The program is GPL v3 with the additional author attribution term in [NOTICE.md](../../../NOTICE.md): when
  redistributing or using it publicly, keep the notice and credit "WT Poligon by ERRROOORR" with a link to the
  project.
- Documentation is under a separate [CC BY 4.0 license](../../LICENSE).
