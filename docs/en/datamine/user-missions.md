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

## Mission and launch field map

| Path or field | Where | Meaning / type | Status | Observation |
|---|---|---|---|---|
| `mission_settings/mission/{name,locName,locDesc}` | Mission BLK | Identity and visible title/description | Verified in game | `name` ties the mission to localization; literal title was shown. |
| `units/armada`, `units/tankModels`, `units/ships` | Mission BLK | Unit family blocks | Verified in game | Tested aircraft, tank and ship missions loaded under their respective families. |
| Unit `unit_class` | Mission unit block | Vehicle ID, text | Verified in game | Stock identity works for owned units; an unavailable stock identity is still subject to ownership/catalog behavior. |
| Unit `weapons`, `bullets0..3`, `bulletsCount0..3` | Mission unit block | Preset and ammunition keys/counts | Verified in game | Tested missions selected a preset and shell counts without a separate in-mission picker. |
| `userVehicles/<owned vehicle>` | `content/pkg_local` | Slot bound to hangar identity | Verified in game | Retained tested helicopter HUD with a stock preset; modification equipment did not fully transfer. |
| Separate local copy under `gameData/flightModels`, `units/tankModels` or `units/ships` | `content/pkg_local` | New vehicle identity | Verified in game | Can start an unavailable vehicle, with the interface and equipment limitations above. |
| `char.vromfs.bin` catalog lookups | Stock archive | Identity, unlock and preset references | Verified in game | A local copy did not replace stock catalog membership or make a new preset visible solely through `userVehicles`. |
| Unit `crewSkillK`, `props/uniqueName` | Mission unit | Skill multiplier candidate and bot name key | Unverified (in files only) | Present in stock missions; isolated player effects were not established. |

The generated scenario may add ground or airborne targets, routes, check conditions and restore triggers. Those are mission BLK constructs; their presence alone does not prove each proposed scenario combination is supported. See the [program overview](../program/overview.md).
