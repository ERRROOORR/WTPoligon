> Русская версия: [../../ru/datamine/aircraft.md](../../ru/datamine/aircraft.md)

# Aircraft flight models and pylons

An aircraft definition is under `gameData/flightModels/<vehicle>.blk`; `fmFile` can point to a shared flight model under `flightModels/fm/`. Do not assume the file has the vehicle's name. Engine layouts vary: `EngineN` may contain parameters or refer through `Type` to `EngineTypeN`. A type shared by two engines affects both.

| Path or field | Meaning | Unit | Status |
|---|---|---|---|
| Vehicle `fmFile` | Flight model reference | path | Unverified (in files only) |
| FM `Mass/EmptyMass` | Empty mass; changing it affected flight and compensated payload mass | kg | Verified in game |
| FM `Mass/Takeoff` | Listed takeoff mass; a tested reduction had no visible flight effect | kg | No effect |
| FM `Mass/AdvancedMass`, `Parts`, `PartsWithSurface` | Distributed mass representation | mixed | Unverified (in files only) |
| FM `EngineTypeN/Main/Power`, `Compressor/Power0` | Engine power fields; both changed acceleration in a piston aircraft | source power unit | Verified in game |
| Vehicle `WeaponSlots/WeaponSlot/index`, `WeaponPreset/Weapon/blk`, `emitter` | New slot, option, weapon and attachment point | index/path | Verified in game |
| Vehicle `weapon_presets/preset/blk` → `flightModels/weaponPresets/*.blk` | Older whole aircraft preset; may list `Weapon` directly | path | Verified in game |
| `WeaponSlots/maxloadMass*`, `maxDisbalance`, `BannedWeaponPreset` | Stated load and combination limits | kg where mass; otherwise source unit | Unverified (in files only) |

Custom `(slot, preset)` combinations and the older direct `Weapon` list have worked in game. The mission allowed combinations beyond the listed load and balance limits; those limits should be shown as warnings. Slot numbers do not universally identify left and right, and helicopter behavior deserves separate checks.

“Weightless loadout” uses a copy of the flight model and sets `EmptyMass` to its stock value minus payload mass, then points the vehicle copy to it through `fmFile`. This compensated a tested heavy bomb in flight. Reject a nonpositive result; advanced mass models and helicopters remain unverified. After dropping the load, the aircraft remains lighter than its stock empty mass. Tested changes to `bomb/dragCx` and `Weapon/dragCx` had no visible effect in the measured scenario.
