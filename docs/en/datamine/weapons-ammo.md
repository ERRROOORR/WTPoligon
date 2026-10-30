> Русская версия: [../../ru/datamine/weapons-ammo.md](../../ru/datamine/weapons-ammo.md)

# Weapons and ammunition

The vehicle or aircraft preset points to a weapon BLK. Its top level describes a gun or launcher; `bullet`, `rocket`, `bomb`, and `torpedo` blocks describe payloads. Named alternative shell blocks may coexist with the default `bullet`. To edit ammunition, copy the weapon file using `include` and `@override`, then point the vehicle or preset at the copy. Copying only a shell block from another gun requires its complete compatible block structure.

| Path or field | Meaning | Unit | Status |
|---|---|---|---|
| `gameData/weapons/{groundModels_weapons,rocketGuns,bombGuns,torpedoes}/*.blk` | Weapon files by family | — | Unverified (in files only) |
| Weapon `shotFreq`, `bullets`, `reloadTime` | Firing and capacity fields | source unit | Unverified (in files only) |
| `bullet/mass`, `speed`, `caliber`, `explosiveMass` | Projectile properties | kg, m/s, source unit, kg where applicable | Verified in game |
| `rocket/mass`, `bomb/mass`, `torpedo/mass`, `explosiveMass` | Payload and explosive mass | kg | Verified in game |
| `bullet/damage/kinetic/lanzOdermattWorkingLength` | Long rod penetration input | mm | Verified in game |
| `bullet/cumulativeDamage/armorPower` | Shaped charge penetration input | mm | Verified in game |
| `bomb/yield` | Nuclear yield appears in files; editing it is untested | kt | Unverified (in files only) |
| Mission `bullets0..3`, `bulletsCount0..3` | Named shell selection and count | name/count | Verified in game |
| `rocket/guidance/opticalSeeker/rangeMax` | Tested infrared seeker acquisition limit | m | Verified in game |

Mission selection has no in-mission shell picker in the tested setup. Gun copies, shell changes, rockets, bombs, and torpedoes worked in the examined missions; exact formulas and edge cases need separate evidence. A ground SAM's native `cannon` + `bullet{rocket}` format crashed when mounted on an aircraft. Converting a copy to `rocketGun` with a `rocket` block let tested missiles appear, launch, and guide. Radar-guided and naval SAMs remain unverified; compatibility must be tested per weapon family.

## Projectile field map

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `bullet/damage/kinetic/{demarrePenetrationK,demarreSpeedPow,demarreMassPow,demarreCaliberPow}` | Shell in gun BLK | DeMarre formula inputs | Unverified (in files only) | Community calculations agreed with sampled penetration; exact game formula and rare shell types remain open. |
| `bullet/damage/kinetic/lanzOdermattWorkingLength` | Long rod shell | Working length, mm | Verified in game | A copied shell with changed length had changed penetration. |
| `bullet/armorpower/ArmorPower*m` | Shell | Penetration by distance | Unverified (in files only) | Found in several shell families; precedence and interpolation not isolated. |
| `bullet/cumulativeDamage/armorPower` | Shaped charge shell | Jet penetration, mm | Verified in game | A tested edit changed penetration. |
| `bullet/{fuseDelay,fuseDelayDist,explodeTreshold}`, `proximityFuse/*` | Shell | Fuze timing and thresholds | Unverified (in files only) | Found in files; effects of local edits not isolated. |
| `rocket/{force,timeFire,massEnd,startSpeed,maxSpeed,dragCx}` | Rocket weapon BLK | Thrust, burn time, spent mass, speed and drag | Unverified (in files only) | A copied rocket worked, but these individual dynamics were not isolated. |
| `bomb/explosionFx` | Bomb weapon BLK | Visual effect key | Verified in game | A copied bomb changed the observed explosion. |
| `bomb/yield` | Nuclear bomb BLK | Yield, kt | Unverified (in files only) | Exists in files; never edited in the recorded tests. |
| `torpedo/{maxSpeedInWater,distToLive,armDistance}` | Torpedo weapon BLK | Speed in m/s and distances in m | Unverified (in files only) | A copied torpedo loaded; individual travel fields were not isolated. |
| `damage_model/explosive.blk`, `projectile_types/*.blk` | Common game definitions | Blast tables and projectile defaults | Unverified (in files only) | Structure surveyed; local replacement or exact formula use not established. |

Penetration is described through DeMarre coefficients, Lanz–Odermatt long rod inputs, an `armorpower` table, or `cumulativeDamage/armorPower`. Select by fields present, not `bulletType` alone. High explosive behavior also refers to common explosive tables. Copy a complete compatible donor shell block; changing only `bulletType` can leave inconsistent related fields. APCR `damageMass` remained uncertain.

## Other surveyed controls

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `shotFreq`, `reloadTime`, `bullets`, `recoilMultiplier`, `overheat` | Gun or launcher BLK | Rate, reload, capacity, recoil and heating | Unverified (in files only) | File survey found them; the examined game tests did not isolate each control. |
| `commonWeapons/Weapon[n]/blk` | Ground vehicle BLK | Weapon file reference | Verified in game | Redirecting after transferred modification blocks selected a copied gun. |
| Preset `Weapon[n]/blk` | Aircraft preset BLK | Weapon file reference | Verified in game | A copied preset selected a copied aircraft weapon. |
| `bullet/{mass,speed,caliber,damageCaliber,damageMass,explosiveMass,explosiveType}` | Shell block | Projectile dimensions, mass and charge | Unverified (in files only) | Individual mass and charge edits worked; APCR `damageMass` interpretation remains uncertain. |
| `rocket/{mass,massEnd,force,timeFire,force1,timeFire1}`, `guidance/tableN` | Rocket block | Fuel mass, thrust stages and guidance range tables | Unverified (in files only) | Fields are linked in source data; changing one does not prove the others automatically recalculate. |
| `bomb/{nearArmorPower,midArmorPower,farArmorPower,explodeArmorPower}` | Bomb block | Impact and explosive penetration candidates | Unverified (in files only) | Found in surveyed bomb families; calculation not isolated. |
| `torpedo/{pressureDamage,detonationRadius,detonationDepth,diveDepth}` | Torpedo block | Shock and depth behavior | Unverified (in files only) | Present in files; local effects not isolated. |

