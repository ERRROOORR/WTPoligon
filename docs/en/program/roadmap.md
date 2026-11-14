> Русская версия: [../../ru/program/roadmap.md](../../ru/program/roadmap.md)

# Roadmap after 2.0-beta

2.0-beta has a seven-step Russian interface, a catalog from the installed game, mission generation, loadout,
characteristics and ammunition editors, called-in vehicles, *My vehicles*, scenario controls, pre-write validation,
a program log and manifest-based rollback. The items below are plans or research, without release dates.

| Area | Planned work |
|---|---|
| Usability | English interface localization; a first-run tutorial and FAQ. |
| Vehicles | Dev-server vehicles in the regular client; each working path verified in game. |
| Distribution | A standalone `.exe`; the current beta is a ZIP with bundled Python and `run.bat`. |
| Weapons | Missile characteristics (range, speed, seeker, overload, warhead); ground-vehicle guns on aircraft; SAMs with radar seekers and naval SAMs on pylons. |
| Sensors | Radar guidance channels; EW modules. |
| Vehicle edits | Sight; turret and gun. |
| Scenarios | Long-range duel up to 200 km, air-defense penetration, a mission for SAM vehicles, naval targets. |
| Ammunition | Timer of the built-in ammunition restore; instant reload on the fire button. |
| Writes | History of applications and undo of a selected past application. The current screen lists installs and rolls back the current, selected or all installs. |

Each capability needs a traceable game-data source, valid generated files and an in-game test. Until then it is
labeled **not verified** or **📄**. See the [tester checklist](../../TESTING.md).
