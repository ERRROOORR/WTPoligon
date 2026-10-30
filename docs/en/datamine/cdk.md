> Русская версия: [../../ru/datamine/cdk.md](../../ru/datamine/cdk.md)

# CDK evidence

The [War Thunder CDK guide to custom units](https://wiki.warthunder.com/cdk/1212-custom-units-creation) describes adding a `weapon_presets/preset` entry through an override, using a separate preset BLK, and hiding unused pylon model nodes with `hideNodes`. It places helicopter definitions in the aircraft `flightModels` family. This is supporting documentation for the file structure, while the guide's custom model example does not prove that every stock vehicle accepts every invented combination.

| Path or field | Where | Meaning / type | Status | Observation |
|---|---|---|---|---|
| `weapon_presets/preset` | Aircraft BLK | Whole aircraft preset reference | Unverified (in files only) | Documented by the CDK guide and present in surveyed stock definitions. Specific custom copies were subsequently checked in game. |
| `flightModels/weaponPresets/*.blk` | Preset file | Weapon list / slot choices | Unverified (in files only) | CDK uses a separate file; preserve its actual stock form when adapting it. |
| Preset `hideNodes` | Preset BLK | Model node visibility | Unverified (in files only) | CDK shows hiding unused pylons. Exact node geometry still needs model or game inspection. |

See [Pylons](pylons.md) for the game tests and the separate old and new loadout schemes.
