> Русская версия: [../../ru/program/overview.md](../../ru/program/overview.md)

# Program overview

WT Poligon is a Windows desktop builder for single player test missions. It reads the installed game's archives for its catalog and writes managed local copies and user missions. Stock archives remain untouched. A basic window and aircraft loadout builder exist in the development build; the general characteristics editor is in progress.

## Window flow

| Step | User choice | Result and current scope |
|---|---|---|
| **Vehicle** | Search the installed catalog, choose aircraft, helicopter, ground vehicle or ship, inspect hangar ownership | The launch mode and losses of a copy are disclosed. Search uses localized names, identifiers and typo tolerant matching. |
| **Loadout** | Inspect slots, variants and older whole aircraft presets; choose pylon weapons and confirmed mirror pairs | Retains `trigger`, `emitter`, counts and node settings. Shows mass, balance and compatibility warnings. |
| **Characteristics** | Change a verified aggregate or an individual typed BLK field | In development. The editor should show source path, stock value, unit, evidence status and consequences. |
| **Scenario** | Choose spawn, ground target set and distance, and a supported air target | Becomes mission units, routes, triggers and target restoration. Invalid combinations are rejected. |
| **Review and write** | Inspect copy paths, mission, warnings and validation | Files are built in memory, checked against stock, then installed with ownership and rollback records. |

## From selection to mission

VROMFS supplies binary BLK definitions, localization, weapons, presets and image resources from the installed game. The readers preserve typed values and duplicate names. The vehicle index and weapon catalog follow links across files. Search matches names with spelling errors. Icons come from game atlases and vehicle assets; no extracted images are published here. UI `.ddsx` images may use Oodle and need a separate decoder from zstd BLK.

The generator writes a text BLK in `UserMissions/`. It selects `armada` for aircraft and helicopters, `tankModels` for ground vehicles and `ships` for naval vehicles. `unit_class` identifies the player unit. Mission fields `bullets0..3` and `bulletsCount0..3` can select ammunition. Scenario targets add units, paths and triggers for restoration after destruction. A paired `usr_<mission>.csv` supplies names; the client loads CSV localization at startup.

An owned hangar machine can run under its real identity or through `userVehicles/<owned vehicle>`, retaining more stock interface. Another vehicle needs a separately named local copy with `include` and typed overrides. Copies may lose modification controlled equipment, names, action bar entries or a vehicle specific HUD. See [User missions](../datamine/user-missions.md) and [Modifications](../datamine/modifications.md).

## Edit and write pipeline

An edit records source file, path with one based duplicate ordinal, stock type/value, requested value and provenance. `coerce`, `stock_param`, `make_edit`, `override_path` and `edits_text` form the edit model and text output. Each copied BLK begins with a stock `include`; `@override` changes that tree. A weapon or sensor edit also needs its own copy and a changed reference in the vehicle or preset. A compensated payload needs a flight model copy and `fmFile` reference.

Before writing, the builder resolves every generated copy against the current installed stock tree. It checks target paths, types, parser errors and final values, with float32 comparison for real values. The loadout checker computes mass and flags limits, banned combinations and uncertain weapon families. Known crashing combinations must block writing. The installer tracks owned paths and previous contents for rollback; unrelated local files are not silently replaced. The derived archive/catalog cache can be rebuilt after a game update. Gameplay BLKs are re-read on mission load in tested cases; CSV names require a client restart. See [Caching](../datamine/caching.md).

The mission and core loadout mechanisms have been tested in game. The characteristics window, broad weapon compatibility, some mirror mappings, older preset variations and project sharing remain development or research areas. Every field should carry a status from the [datamining reference](../datamine/index.md). No executable release is published yet.
