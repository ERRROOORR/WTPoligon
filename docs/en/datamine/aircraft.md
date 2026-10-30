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

“Weightless loadout” uses a copy of the flight model and sets `EmptyMass` to its stock value minus payload mass, then points the vehicle copy to it through `fmFile`. This compensated a tested heavy bomb in flight. Reject a nonpositive result; advanced mass models and helicopters remain unverified. The unchanged copy implies a lower empty mass after release, although that consequence was not isolated in flight. Tested changes to `bomb/dragCx` and `Weapon/dragCx` had no visible effect in the measured scenario.

## Flight model field map

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `fmFile` | Aircraft root BLK | Flight model path, text | Verified in game | A vehicle copy pointed at a copied FM and used its changed mass. Many aircraft share an FM, so filenames cannot be guessed. |
| `Mass/EmptyMass` | `flightModels/fm/*.blk` | Empty mass, kg | Verified in game | A copied FM changed measured flight and compensated a tested payload. |
| `Mass/Takeoff` | FM | Listed takeoff mass, kg | No effect | Its tested reduction did not change measured flight beyond control variation. |
| `Mass/{MaxFuelMass0,OilMass,AdvancedMass}` | FM | Fuel/oil mass in kg and boolean mass mode | Unverified (in files only) | Present in stock data; local effects were not isolated. |
| `Mass/{Parts,PartsWithSurface}` | FM | Distributed parts with mass/damage associations | Unverified (in files only) | Their sums need not equal `EmptyMass`; advanced mass mode remains untested for compensation. |
| `Mass/{CenterOfGravity,MaxFuelMassExternal0}` | FM | Point / kg | Unverified (in files only) | Present in stock FM; effects of a local edit were not isolated. |
| `MomentOfInertia` | FM root, outside `Mass` | Three component inertia | Unverified (in files only) | A payload compensation edit leaves it unchanged. |
| `EngineN/Type` → `EngineTypeN` | FM | Shared engine type reference | Unverified (in files only) | A shared type affects every engine that refers to it. Some FMs instead embed engine values in `EngineN`. |
| `EngineTypeN/Main/Power` | FM | Piston engine power, source unit | Verified in game | A tested increase changed acceleration. |
| `EngineTypeN/Main/{Type,Thrust,ThrustMax,RPMMax}` | FM | Engine kind and output fields, source units | Unverified (in files only) | Present in stock data; do not assume `Thrust` is the active piston power control. |
| `EngineTypeN/Compressor/{Power0,Altitude0,Ceiling0}` | FM | Altitude power curve | Verified in game | A tested `Power0` change altered flight; other curve points were not isolated. |
| `EngineTypeN/Main/ModeN`, `ThrustMax/*`, `Afterburner/*` | FM | Throttle, thrust table and boost | Unverified (in files only) | Present in many jet/turboprop FMs; the exact consequences of local edits were not isolated. |
| `PropellerN`, `PropellerTypeN`, `TransmissionN`, `NozzleN` | FM | Propeller, drive and nozzle structures | Unverified (in files only) | Some engines use these references; never assume a single engine layout. |

In a measured 30 second comparison, reducing `EmptyMass` by the tested payload mass restored flight approximately to the empty aircraft; the same aircraft with payload and no compensation flew substantially heavier. `Takeoff` changed neither acceleration nor height beyond control variation. The exact handling of payload drag, center of gravity and advanced mass models remains open. See [Pylons](pylons.md).
