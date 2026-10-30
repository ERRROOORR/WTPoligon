> Русская версия: [../../ru/datamine/modifications.md](../../ru/datamine/modifications.md)

# Vehicle modifications in a local copy

A separately named vehicle copy does not acquire the player's researched modifications automatically. Some effects are blocks in the vehicle definition and can be baked into that copy. Others depend on the game's modification system and remain unavailable. The same caution applies when a hangar vehicle is addressed through `userVehicles/`.

| Path or field | Where | Meaning / type | Status | Observation |
|---|---|---|---|---|
| `modifications/<name>/effects/commonWeapons` | Vehicle BLK | Replacement weapon block | Verified in game | Copied smoke grenade launchers worked and showed icons. |
| `modifications/<name>/effects/nightVision` | Vehicle BLK | Night vision block | Verified in game | Tank gunner thermal equipment worked; helicopter third person night vision needed the companion flag. |
| `enableNightVision:b=yes` | Modification definition / copied vehicle | Boolean companion flag | Verified in game | With the night vision block it enabled helicopter third person night vision. Sight thermal still did not work. |
| `modifications/<name>/effects/hideNodes` | Vehicle BLK | Hide or show model nodes | Verified in game | Additional armor appeared on a tested tank. |
| `modifications/<name>/effects/sensors` | Vehicle BLK | Sensor attachment block | Unverified (in files only) | A laser designator block was found, but it did not establish a working laser rangefinder. |
| `invertEnableLogic` | `config/modifications.blk` | Boolean: effect when upgrade absent | Unverified (in files only) | Stock penalties were identified in files; do not bake these into a fully equipped copy. |
| `group`, `reqModification` | Vehicle modification and common catalog | Text grouping / dependency | Unverified (in files only) | Alternative upgrades in one group must be selected rather than combined; prerequisites can form stages. |
| `extinguisherActivationCount`, `repairAvailable`, `rangefinderMounted` | Common modification catalog | Equipment flags/count | No effect | Baking standalone flags into tested copies did not restore extinguisher, repair, or rangefinder behavior. |
| `modifications/<name>/effects/ammoStowages`, `damagePartsOverride`, `tracks`, `counterMeasures` | Vehicle BLK | Replacement or additive blocks | Unverified (in files only) | Present across vehicle families; effect of each transfer was not isolated. |

When the stock vehicle already has a block, the modification's block commonly replaces it as a whole; when several modifications contribute distinct blocks, merging may be needed. Preserve order and resolve the final tree before writing. Do not blindly combine alternative gun or armor modifications.

**Known losses:** extinguisher, repair kit, engine smoke, laser rangefinder, first aid, modification granted shells, and a tested helicopter sight thermal mode. The shell can instead be selected through mission ammunition fields when its weapon supports it. A new vehicle identity can additionally lose stock names, some action bar icons, and the helicopter interface. The cause of every loss has not been isolated.
