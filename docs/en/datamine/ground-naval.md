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
| `DamageParts/crew/hp` | Crew durability candidate; isolated effect not established | source unit | Unverified (in files only) |
| `ammo/detonateProb` | Ammunition detonation candidate; no clear difference in tested scenario | probability | Unverified (in files only) |
| `ammoStowages/*/fatalExplosion=no` | Attempted ammunition protection | boolean | No effect |

“No effect” here means no demonstrated effect in the reported test, not proof that the engine ignores the field in every context. Crew and ammunition behavior was obscured by ammunition explosions. Do not promise a crew durability control based on these fields.

## Physics and damage field map

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `maxFwdSpeed`, `maxRevSpeed` | Root of tank or ship BLK | Top level speed values | Unverified (in files only) | Similar values occur on vehicles with different real speeds; a changed ship `ShipPhys/engines/maxSpeed` exceeded its unchanged root value. |
| `VehiclePhys/Mass/{Empty,TakeOff,Fuel}` | Tank BLK | Masses, kg | Unverified (in files only) | `Empty` affected acceleration in the tested tank; `TakeOff` and `Fuel` were not isolated. |
| `VehiclePhys/engine/{horsePowers,maxRPM,minRPM}` | Tank BLK | Power, hp; RPM values | Unverified (in files only) | `horsePowers` changed acceleration; RPM fields were not isolated. |
| `VehiclePhys/mechanics/{mainGearRatio,sideGearRatio,driveGearRadius}` | Tank BLK | Drive ratios / radius | Unverified (in files only) | Present in stock transmission; only an individual `gearRatios/ratio` change was tested. |
| `VehiclePhys/suspension/{defaultDampeningForce,suspensionOffsets}`, `VehiclePhys/tracks/*`, `floats/*` | Tank BLK | Suspension, track and buoyancy parameters | Unverified (in files only) | File survey found these families; gameplay changes were not isolated. |
| `ShipPhys/mass/{Empty,momentOfInertia,CenterOfGravity}` | Ship BLK | Mass and inertia | Unverified (in files only) | Present in stock ships, not separately changed in game. |
| `ShipPhys/engines/{maxReverseSpeed,speedToTime,reverseSpeedToTime}` | Ship BLK | Reverse speed and speed/time curves | Unverified (in files only) | `maxSpeed` alone doubled the observed speed of a tested ship; acceleration tables were not isolated. |
| `ShipPhys/hydrodynamics/{bodyArea,mulReaction,rudder,hydrofoils}` | Ship BLK | Hull, steering, foil properties | Unverified (in files only) | Excessive tested speed caused strong heel on turning; the individual hydrodynamic fields were not changed. |
| `DamageParts/<group>/<part>/{armorThickness,hp,armorClass}` | Vehicle BLK | Thickness in mm, durability, class | Unverified (in files only) | `armorThickness` of one tested plate blocked a shot while an adjacent plate remained penetrable; other fields not isolated. |
| `DamageEffects/part`, `fireParamsPreset`, `fireProtectionHp` | Vehicle BLK / common fire presets | Hit, fire and protection behavior | Unverified (in files only) | Present in surveyed armor/damage trees; local effects not isolated. |
| `ammoStowages/<stowage>/{shells,charges,fatalFire,fatalExplosion}`, `ammo/*` | Tank or ship BLK | Distribution and detonation rules | Unverified (in files only) | The attempted `fatalExplosion=no` did not protect the tested target; other fields need isolated tests. |
| `tank_crew/<member>/{dmPart,role,substitute}`, `minCrewMemberAliveCount` | Tank/ship BLK | Crew part and role links | Unverified (in files only) | Structure is present; a high `DamageParts/crew/hp` did not establish crew survival because ammunition exploded. |

The validated ground edits are engine `horsePowers`, `Mass/Empty`, and a selected repeated `gearRatios/ratio`. A longer upper gear engaged but the tank lacked power to accelerate further. Ship `maxSpeed` doubled the observed HUD speed in a comparison; the unchanged top level `maxFwdSpeed` did not cap it. A tested armor plate changed from penetration to nonpenetration when its `armorThickness` increased, without changing the neighboring lower plate. Crew and ammunition durability controls remain unresolved.

## Additional mobility fields found in files

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `VehiclePhys/Mass/{momentOfInertia,CenterOfGravity,AdvancedMass,trackMass,engineInertialMass}` | Tank BLK | Inertia, center and masses | Unverified (in files only) | Surveyed on stock ground vehicles; the apparent inertia units were not established. |
| `VehiclePhys/engine/{type,model,manufacturer,rpmTau}` | Tank BLK | Engine family and response metadata | Unverified (in files only) | Present on some vehicles; no isolated local edit. |
| `VehiclePhys/mechanics/{steerType,neutralGearRatio,gearType,tracked}` | Tank BLK | Steering/transmission modes | Unverified (in files only) | May differ for wheeled and tracked vehicles; gameplay effects not isolated. |
| `VehiclePhys/suspension/{dampeningRelaxationRatio,dampeningCompressionRatio,defaultGearRadius}` | Tank BLK | Suspension damping and wheel geometry | Unverified (in files only) | Present in stock files; local effects not measured. |
| `VehiclePhys/movableSuspension/{speed,maxSpeedForMove,clearance,pitch,roll}` | Some tank BLKs | Adjustable suspension | Unverified (in files only) | Found on hydro-pneumatic vehicles; no direct test of these paths. |
| `ShipPhys/engines/engine/{pos,propeller,engineDmPart,shaftDmPart,boilerPressure}` | Ship BLK | Repeated shaft/engine component | Unverified (in files only) | Ships can have several `engine` blocks; preserve ordinal order. |
| `ShipPhys/hydrodynamics/rudder/{pos,area,deflection,dmPart}` | Ship BLK | Repeated rudder definition | Unverified (in files only) | Found in stock ships; steering response to a local edit not isolated. |
| `ShipPhys/hydrodynamics/hydrofoils` | Ship BLK | Foil blocks | Unverified (in files only) | Only some ships have this structure. |

Do not turn the root `maxFwdSpeed` into an advertised vehicle top speed: most surveyed tanks shared a similar value despite different real performance. The tested tank's longer gear illustrates that gearing and engine power must be considered together. The ship speed edit also increased heel during a hard turn; a UI should warn about that observed consequence.
