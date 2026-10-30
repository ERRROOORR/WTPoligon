> Русская версия: [../../ru/datamine/pylons.md](../../ru/datamine/pylons.md)

# Aircraft pylons and presets

The surveyed aircraft BLKs have two overlapping schemes. In the examined archive, 827 aircraft used only the older `weapon_presets` list, 821 had both it and `WeaponSlots`, none had only slots, and four did not fit either classification. A stock preset file can select `(slot,preset)` pairs, list `Weapon` entries directly, or contain no top level `Weapon`. Preserve its original shape and order.

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `WeaponSlots/WeaponSlot/index` | Aircraft BLK | Slot ID, integer | Verified in game | Custom `(slot,preset)` combinations loaded. Index arithmetic does not determine left and right. |
| `WeaponSlot/WeaponPreset/name` | Aircraft BLK | Choice name, text | Verified in game | A mission can select a defined choice; a new name has to be defined in the vehicle copy. |
| `WeaponPreset/Weapon/{trigger,blk,emitter,bullets}` | Aircraft BLK | Control group, weapon path, attachment, count | Verified in game | Custom weapons mounted and fired using these records. A choice can contain several `Weapon` blocks. |
| `WeaponPreset/{ShowNodes,HideNodes}` | Aircraft BLK | Model node visibility | Unverified (in files only) | Many stock choices toggle nodes; geometry must be checked on the actual model. |
| `WeaponPreset/{DependentWeaponPreset,BannedWeaponPreset,reqModification}` | Aircraft BLK | Dependencies, exclusions, upgrade key | Unverified (in files only) | Present in stock data; the mission accepted combinations that exceeded listed restrictions. |
| `WeaponSlots/{maxloadMass,maxloadMassLeftConsoles,maxloadMassRightConsoles,maxDisbalance}` | Aircraft BLK | Listed mass/balance limits, kg where applicable | Unverified (in files only) | Mission loading did not enforce them. Payload mass and imbalance still matter in flight. |
| `WeaponSlot/{tier,order,notUseforDisbalanceCalculation}` | Aircraft BLK | Ordering and balance flag | Unverified (in files only) | Some slots lack `tier` or `order`; exact game rules were not isolated. |
| `Weapon/{external,separate,machLimit,mass,dragCx}` | Choice or preset | Mixed flags/limits/mass | Unverified (in files only) | Values occur at weapon level; do not equate `Weapon/mass` with payload mass. Tested `Weapon/dragCx` had no visible flight effect. |
| `weapon_presets/preset/{name,blk}` | Aircraft BLK | Whole aircraft preset and file reference | Verified in game | Old style direct weapon lists worked in the tested aircraft. |
| Preset `Weapon/{slot,preset}` | `flightModels/weaponPresets/*.blk` | Slot selection | Verified in game | Custom combinations loaded when the vehicle copy defined their names. |
| Preset `Weapon/{trigger,blk,emitter,bullets}`, `hideNodes` | same | Direct old style list and node visibility | Verified in game | Direct lists worked; preserve empty lists and node settings. |

The same `emitter` can appear with different weapons in separate stock presets. This establishes examples, not universal physical compatibility. For older aircraft, mixing entries from separate presets was not fully validated. Helicopters use the same family of files: some have slots, others only whole aircraft presets. Container records can contain several weapons, and `Weapon/mass` may describe installation mass. A separately named helicopter copy showed an aircraft HUD; an owned helicopter addressed through `userVehicles/` retained its helicopter HUD with a stock preset.

The mission did not enforce listed overall mass, per wing mass, imbalance, or `BannedWeaponPreset` limits in the tested combinations. Treat these as warnings, while recognizing that mass and imbalance affect flight. Slot mirroring requires evidence from names, node visibility, the model, or an in-game view; `index + 1` is not a general rule.

For the tested aircraft, a copied flight model with `Mass/EmptyMass` reduced by payload mass made a very heavy bomb fly approximately like the empty aircraft. Require a positive resulting empty mass. `AdvancedMass=yes`, center of gravity behavior, and helicopters need separate checks. The unchanged copied FM implies a lower empty mass after release; this consequence was not isolated in flight. Changing `Mass/Takeoff`, `bomb/dragCx`, or `Weapon/dragCx` did not provide the sought effect in the tested scenarios. See [Failures](failures.md).

## Survey details and assembly rules

The archive survey examined 1,652 root aircraft definitions and 9,815 preset files. Of the latter, 7,525 used only `(slot,preset)` records, 1,691 contained direct `Weapon/blk` entries, and 599 had no top level `Weapon`. The two forms are data shapes, not separate eras: 821 aircraft contained both the old catalog and slot definitions. Two older preset references in the surveyed archive were unresolved, so a resolver must report missing files rather than invent them.

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `WeaponSlots/HideNodes` | Aircraft BLK | Initially hidden nodes | Unverified (in files only) | Stock slot variants may reveal pylons through `ShowNodes`; the case of the name must be preserved. |
| `WeaponPreset/{iconType,showInWeaponMenu}` | Slot variant | Menu metadata | Unverified (in files only) | Present for many but not all stock variants; it does not by itself prove a weapon is usable. |
| `WeaponPreset/Weapon/{external,separate,machLimit,mass}` | Slot variant | Mount flags, Mach limit, optional mass | Unverified (in files only) | Optional `mass` at this level may be installation mass, particularly on helicopters. |
| Preset `weaponConfig`, `tags` | Aircraft `weapon_presets/preset` | Whole preset metadata | Unverified (in files only) | Present on some older catalog entries; retain when cloning a known entry. |
| Preset `hideNodes`, `hideDmParts` | Preset file | Geometry and damage part visibility | Unverified (in files only) | A zero weapon preset can still carry important node settings. |
| `reqModification` | Slot choice, weapon, or old preset | Unlock dependency | Unverified (in files only) | The same key can be found in vehicle modifications and shared cost data; the exact unlock rule in a user mission was not isolated. |
| `Weapon/emitter` | Slot choice or direct preset | Model attachment/emission point | Unverified (in files only) | The same point can appear with different weapons in separate stock presets. Name alone does not establish geometry. |

For an old style copy, retain a direct `Weapon` list including `trigger`, `blk`, `emitter`, `bullets`, its order, and `hideNodes`. An empty list can mean an unarmed external preset while fixed guns remain in the vehicle. For a slot based copy, define each new `WeaponPreset/name` in the copied aircraft and make the separate preset file refer to those exact names. A custom name placed only under `userVehicles/` failed because the stock preset catalog still supplied the lookup. A tested old preset could replace one bomb link while retaining the other three.

Mirroring cannot use a universal slot number formula. Left/right names, `ShowNodes`, and `emitter` provide clues; on many older aircraft emitters are numbered without sides. Helicopter variants can contain a container plus several weapon records; their `trigger`, order and optional installation mass must be retained. The demonstrated helicopter custom slot combination worked under a new copy identity but showed an aircraft HUD.
