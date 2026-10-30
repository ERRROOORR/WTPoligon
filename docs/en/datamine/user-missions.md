> Русская версия: [../../ru/datamine/user-missions.md](../../ru/datamine/user-missions.md)

# User missions and vehicles

A single player mission BLK lives under `UserMissions/`. Its unit block uses `armada` for aircraft or helicopters, `tankModels` for ground vehicles, and `ships` for naval vehicles. `unit_class` selects the vehicle; `mission_settings/mission/name` identifies the mission. The matching `usr_*.csv` can supply localized names (see [Localization](localization.md)).

| Path or field | Meaning | Unit | Status |
|---|---|---|---|
| `UserMissions/*.blk` | User mission definition | — | Verified in game |
| `armada`, `tankModels`, `ships` / `unit_class` | Unit category and selected vehicle | — | Verified in game |
| `mission_settings/mission/name` | Mission identifier used with localization | — | Verified in game |
| `pkg_local/gameData/flightModels/`, `units/tankModels/`, `units/ships/` | Local vehicle copy directories | — | Verified in game |
| `userVehicles/<owned vehicle>` | Launch using a vehicle owned in the hangar | — | Verified in game |
| `UserMissions/usr_<mission>.csv` | Mission and custom unit text, loaded at game startup | — | Verified in game |

Using an owned vehicle's real identity preserves the normal vehicle type and interface. An owned vehicle addressed through `userVehicles/` also retained the helicopter interface with a stock preset, but ground equipment tied to modifications did not fully transfer. A vehicle unavailable in the hangar needs a distinct local copy name; the copy can drive or fire but may lose vehicle specific interface, equipment, ammunition labels, or modification behavior. A helicopter copy under a new identity showed an aircraft interface. Adding a custom preset name only to `userVehicles/` failed because the stock preset catalog was consulted. These are observed limitations, so “any vehicle” does not promise identical stock behavior.
