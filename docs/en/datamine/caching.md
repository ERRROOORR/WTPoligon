> Русская версия: [../../ru/datamine/caching.md](../../ru/datamine/caching.md)

# Reloading and caches

The observations below concern a running client and a fresh load of a user mission. They do not establish that every internal game cache is cleared. A log line saying that an `include` was read confirms parsing; the gun and bomb changes also had visible effects in game.

| File or path | Where | Type / unit | Status | Observation |
|---|---|---|---|---|
| `UserMissions/*.blk` | User mission directory | text BLK | Verified in game | An edited mission name was read on the next load in the same client session. |
| Vehicle copy | `content/pkg_local/gameData/{flightModels,units/tankModels,units/ships}/*.blk` | text BLK | Verified in game | New and edited copies loaded without restarting the client. |
| Gun copy | `gameData/Weapons/groundModels_weapons/*.blk` in `pkg_local` | text BLK | Verified in game | Editing a penetrator length in an already used copy changed penetration after reloading the mission. |
| Bomb copy | `gameData/Weapons/BombGuns/*.blk` in `pkg_local` | text BLK | Verified in game | An edited `explosionFx` was observed after reloading the mission. |
| New preset copy | `gameData/flightModels/weaponPresets/*.blk` in `pkg_local` | text BLK | Verified in game | Newly created presets loaded in the running client. |
| Edited, previously used preset copy | same | text BLK | Unverified (in files only) | Repeated `include` log lines suggest re-reading; no isolated visual comparison was recorded. |
| New rocket and torpedo copies | `gameData/Weapons/{rocketGuns,torpedoes}/*.blk` in `pkg_local` | text BLK | Verified in game | Both new copies loaded in the running client. Re-editing an existing copy was not isolated. |
| `UserMissions/usr_<mission>.csv` | Beside the mission | UTF-8, semicolon CSV | Verified in game | Added names appeared after a client restart; a mission reload alone did not update them. |

Keep stable managed copy names. For a gameplay BLK change, reload the mission. For a new or edited localization CSV, restart the client. Recheck these rules after game updates.
