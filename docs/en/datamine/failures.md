> Русская версия: [../../ru/datamine/failures.md](../../ru/datamine/failures.md)

# Failures and disproved approaches

The status describes the reported configuration and observation, not every possible use of the field. Treat a crash as a reason to reject that generated combination before writing it.

| Path or field | Where | Intended use / type | Status | Observation |
|---|---|---|---|---|
| Custom preset named only under `userVehicles/<owned vehicle>` | Local vehicle file | Preset text key | No effect | The client still looked up the preset name in the stock aircraft catalog. A vehicle copy with the defined choice was required. |
| `bomb/mass` reduced to about 1 kg for a heavy bomb | Copied `BombGuns` BLK | Payload mass, kg | Crashes game | The tested mission hung and watchdog terminated the game. Changing payload mass also changes the weapon itself. |
| Ground SAM `cannon` with `bullet{rocket}` on an aircraft pylon | Ground weapon BLK used by aircraft preset | Weapon family | Crashes game | The tested native ground format crashed on mission load. A converted `rocketGun` with `rocket` block launched and guided in subsequent tests. |
| Several unseparated numeric parameters on one text BLK line | Local copy | BLK syntax | Crashes game | A malformed real value produced `BLK invalid` in the examined crash log. Put one parameter on each line. |
| Missing or wrong type `@override` target | Local text BLK | Edit target/type | No effect | The parser logged the failed override and skipped it. A plain duplicate may also leave the original first value in use. |
| `Mass/Takeoff` reduction | Copied aircraft flight model | Listed mass, kg | No effect | The measured flight comparison did not change beyond the control spread. |
| `Weapon/external=no` on a heavy bomb | Aircraft weapon choice | Boolean flag | No effect | Bomb remained visible and flight was not improved in the reported run. |
| `bomb/dragCx=0`, `Weapon/dragCx=0.2` | Bomb copy / slot weapon | Drag fields | No effect | Repeated 30 second comparison showed at most a small difference within the measured spread. |
| `Parts`, `PartsWithSurface` as a substitute for `EmptyMass` | Flight model | Distributed mass/damage parts | Unverified (in files only) | No tested basis for mass compensation through these parts, particularly with `AdvancedMass=yes`. |
| `DamageParts/crew/hp`, `ammo/detonateProb` | Ground vehicle copy | Crew and detonation candidates | Unverified (in files only) | No protective difference was demonstrated; ammunition explosions obscured the isolated crew test. |
| `ammoStowages/*/fatalExplosion=no` | Ground vehicle copy | Attempted ammunition protection | No effect | The tested target still exploded; the precise failure mode was not isolated. |
| Vehicle copy added to local `char` or a non-owned vehicle launched under stock identity | Local content / mission | Catalog identity | No effect | The client still used stock catalog identity and ownership checks. A distinct copy could run with reduced interface behavior. |

Other boundaries: a converted ground SAM's infrared guidance was observed, as was one later command guided conversion. Radar homing, satellite guided, and naval SAM families remain unverified. The general `rocketGun` conversion must retain appearance fields needed by the weapon. See [Weapons and ammunition](weapons-ammo.md).
