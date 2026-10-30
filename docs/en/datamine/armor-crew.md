> Русская версия: [../../ru/datamine/armor-crew.md](../../ru/datamine/armor-crew.md)

# Armor, damage, fire and crew

Vehicle BLKs describe damageable groups and parts under `DamageParts`, responses under `DamageEffects`, and crew or ammunition layouts in separate trees. Changing a named armor part in a copied ground vehicle worked in game. Most other properties below are file findings, not proven user controls. See [Ground and naval physics](ground-naval.md) for mobility.

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `DamageParts/<group>/<part>/armorThickness` | Ground or naval vehicle BLK | Plate thickness, mm | Verified in game | Increasing one tested front plate stopped penetration while the adjacent lower plate remained penetrable. |
| `DamageParts/<group>/{armorClass,armorThickness}` | Vehicle BLK | Shared armor material and thickness | Unverified (in files only) | A group can supply fields to many parts; a part level edit may need a new field rather than changing the whole group. |
| `DamageParts/<group>/<part>/{hp,genericDamageMult,deadExplProb}` | Ground, naval or aircraft BLK | Part durability and damage multipliers | Unverified (in files only) | Surveyed across vehicle types; isolated gameplay effect not established. |
| `DamageParts/<era group>/{kineticProtectionEquivalent,cumulativeProtectionEquivalent}` | Ground vehicle BLK | Reactive armor resistance candidates | Unverified (in files only) | Found on reactive armor groups; local edit not tested. |
| `DamageParts/<group>/<part>/{fireProtectionHp,fireParamsPreset}` | Vehicle BLK | Fire protection and preset name | Unverified (in files only) | Present in armor/damage definitions; fire outcome not isolated. |
| `DamageEffects/part/{name,onHit,onKill}` | Vehicle BLK | Hit and destruction actions | Unverified (in files only) | Actions can include fire, explosion, cut, leak and smoke; no isolated local edit. |
| `config/fireparams.blk/presets/<name>` | Common data | Fire duration, damage and extinguishing parameters | Unverified (in files only) | Shared presets are not a per vehicle copy by themselves. |
| `fireParams/*` | Aircraft vehicle BLK | Aircraft specific fire parameters | Unverified (in files only) | Can coexist with a preset; precedence not established. |
| `ammoStowages/<name>/shells`, `charges`, `count`, `firstStage`, `autoLoad` | Ground or naval vehicle BLK | Ammunition distribution and loading | Unverified (in files only) | Structure indicates compartments and stages; exact depletion order not tested. |
| `ammoStowages/<name>/fatalExplosion=no` | Ground vehicle BLK | Attempt to avoid lethal ammunition explosion | No effect | Tested target still exploded and was destroyed. |
| `ammo/{detonateProb,detonatePortion,combustionTime}` | Ground or naval vehicle BLK | Detonation and fire candidates | Unverified (in files only) | Changing `detonateProb` gave no clear difference against a target that already exploded often. |
| `tank_crew/<member>/{dmPart,role,substitute}` | Ground vehicle BLK | Crew damage part, job, replacement order | Unverified (in files only) | Found in surveyed vehicles; removing or moving a role was not tested. |
| `tank_crew/sailorN/{dmPart,role,crew}`, `minCrewMemberAliveCount` | Naval vehicle BLK | Compartment crew and survival threshold | Unverified (in files only) | Present in ship definitions, not separately tested. |
| `DamageParts/crew/hp` | Ground vehicle BLK | Crew durability candidate | Unverified (in files only) | A large increase did not establish survival because tested targets died through ammunition explosions. |
| Mission unit `crewSkillK` | User mission BLK | Crew skill candidate | Unverified (in files only) | Appears in stock missions; isolated effect on the player was not established. |

Aircraft armor is often represented by a part's armor class group rather than an individual `armorThickness` number. Geometry and damageable part existence come from model resources, so a BLK value alone cannot create a new physical armor plate. General armor class, fire and projectile tables are shared data, not private attributes of one copied vehicle. A copy can modify its own references or fields, but the effect of such changes needs a game test.
