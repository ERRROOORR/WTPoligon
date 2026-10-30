> Русская версия: [../../ru/datamine/ground-naval.md](../../ru/datamine/ground-naval.md)

# Ground and naval vehicles

Ground physics resides mainly in `gameData/units/tankModels/<vehicle>.blk` under `VehiclePhys`; ships use `gameData/units/ships/<vehicle>.blk` and `ShipPhys`. Keep repeated gear ratios in their original order. A listed top level speed is not necessarily the actual driving speed.

| Path or field | Meaning | Unit | Status |
|---|---|---|---|
| Tank `VehiclePhys/engine/horsePowers` | Engine power; increasing it improved acceleration | hp | Verified in game |
| Tank `VehiclePhys/Mass/Empty` | Empty mass; increasing it slowed acceleration | kg | Verified in game |
| Tank `VehiclePhys/mechanics/gearRatios/ratio[n]` | Ordered gear ratios; a changed upper gear engaged but was power limited | ratio | Verified in game |
| Tank `VehiclePhys/mechanics/maxBrakeForce` | Braking force by file name; effect not isolated | source unit | Unverified (in files only) |
| Ship `ShipPhys/engines/maxSpeed` | Ship speed setting; a tested increase raised speed substantially | m/s (inferred) | Verified in game |
| Ship `ShipPhys/engines/speedToTime` | Speed/acceleration table | mixed | Unverified (in files only) |
| `DamageParts/<part>/armorThickness` | Armor thickness of a specific part | mm | Verified in game |
| `DamageParts/crew/hp` | Crew durability candidate; isolated effect not established | source unit | No effect |
| `ammo/detonateProb`, `ammoStowages/*/fatalExplosion` | Ammunition survivability candidates; no clear protective effect in tested scenario | probability/boolean | No effect |

“No effect” here means no demonstrated effect in the reported test, not proof that the engine ignores the field in every context. Crew and ammunition behavior was obscured by ammunition explosions. Do not promise a crew durability control based on these fields.
