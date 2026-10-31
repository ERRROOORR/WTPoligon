> Русская версия: [../../ru/program/developer-guide.md](../../ru/program/developer-guide.md)

# Developer guide (Beta-1.0)

## Run and code map

Use Python 3.12 on Windows: `pip install -r requirements.txt`, then `python -m wtpoligon`. The entry point goes through `wtpoligon/__main__.py` and `gui/app.py`. The latter finds the game (or accepts `--game`), supports a datamine source (`--datamine`) and an explicit write target (`--target`), loads the vehicle index and opens the Qt window. A datamine source without `--target` is read-only.

| Package or module | Responsibility |
|---|---|
| `game/` | Read installed VROMFS and BLK data through `source.py`, preserve typed BLK values, index vehicles, search names, resolve images, logs and modifications. |
| `gui/` | Six step pages and `window.py`; `texts.py` holds Russian UI help; `workers.py` runs expensive jobs outside the Qt event loop. |
| `scenarios/` | Scenario model, target catalog and BR-based automatic picks, validation and mission fragments. |
| `ammo/` | Gun and shell catalog, ammunition model, ballistic helpers, validation and copies for changed ammunition. |
| `stats.py` | Vehicle-specific characteristic fields, stock values, evidence status, bounds and edits. |
| `loadout.py` | Pylons, stock presets, weapon catalog, custom selections, mass summary and validation. |
| `build.py`, `edits.py`, `mission.py` | Turn step models into a plan of mission/BLK/CSV files, render typed overrides and verify intended values against the source. |
| `install.py` | Restrict output paths, install managed files, keep SHA-256 manifests/backups and roll back. |
| `logs.py` | Collect program manifests and recent game logs into a diagnostic ZIP. |

## Data flow

`game.source` opens the installed game archives → `game.index` builds a cached vehicle index; loadout, ammo and scenario catalogs follow game references → Qt pages hold models for the selected vehicle → `build.stock_plan()` creates a file plan, including a user mission and any required local copies → `build.verify_plan()` checks generated BLKs against the current stock tree → `install.install()` writes allowed paths and records hashes in a per-application manifest → `install.uninstall()` removes matching owned files or restores backed-up originals. A file modified since installation is left in place. The game archives are never rewritten. See [BLK overrides](../datamine/override.md), [user missions](../datamine/user-missions.md) and [caching](../datamine/caching.md).

The GUI uses `gui/workers.py` with a two-process `ProcessPoolExecutor` and the `spawn` context. Workers cache source readers per process and handle catalog building, stats, loadout setup, ammo search, scenario selection, review and log collection. Pages poll futures with `QTimer` and discard stale results by generation number so changing a vehicle does not apply an old result. Keep Qt widgets on the main thread.

## Verify and package

Run `python -m unittest discover -s tests` for the code suite. Use `tools/ui_lag.py` to measure window responsiveness during navigation and catalog work. Test behavior in the installed game using [docs/TESTING.md](../../TESTING.md), especially any 📄 path. To build the beta ZIP from a prepared `.venv`, run `.venv\Scripts\python tools\make_beta.py --name Beta-1.0`. It packages portable Python, dependencies, source, `run.bat` and notices under `dist/`; it does not make an `.exe`.

## Project rules

Trace each proposed capability to game data, verify generated output, then test it in game before marking it **verified in game**. Mark untested fields and combinations **not verified** or **📄**; a passing parser check is not gameplay evidence. Do not commit or distribute extracted game files, icons or archives. The program is GPL v3 with the additional author attribution term in [NOTICE.md](../../../NOTICE.md): keep that notice and credit “WT Poligon by ERRROOORR” with a link to the project when redistributing or publicly using it. Documentation has its separate [CC BY 4.0 license](../../LICENSE).
