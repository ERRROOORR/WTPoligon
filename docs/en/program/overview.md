> Русская версия: [../../ru/program/overview.md](../../ru/program/overview.md)

# Program overview

WT Poligon is a Windows desktop application under development. Its current flow starts with a vehicle search and selection, then an aircraft loadout step where applicable, a mission setup, and a review/write step. The vehicle and weapon catalog is built from the installed game. The aircraft loadout editor and basic window have been exercised in game; the general characteristics editor is still being built.

| Component or path | Purpose | Unit | Status |
|---|---|---|---|
| Installed `*.vromfs.bin` and BLK | Source for vehicle, weapon, and preset catalog | — | Unverified (in files only) |
| `UserMissions/*.blk` | Generated mission | — | Verified in game |
| `content/pkg_local/gameData/.../*.blk` | Vehicle, flight model, preset, sensor, and weapon copies | — | Verified in game |
| Local manifest and backups | Track writes and support rollback | — | Unverified (in files only) |
| `include` + `@override` | Apply selected edits to copies | source unit | Verified in game |

The intended write pipeline builds all files in memory, resolves every override against the current installed stock tree, checks type and final value, then writes only managed mission and local content files. A manifest records paths and hashes for rollback; files outside its ownership must not be overwritten automatically. The framework, catalog, basic window, aircraft loadout editor, and manifest handling exist in the private development project. Some GUI paths, loadout mirroring, old preset handling, library reuse, and rollback still need direct user confirmation. No executable release is available.
