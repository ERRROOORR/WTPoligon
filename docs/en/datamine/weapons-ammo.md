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
| `rocket/opticalSeeker/rangeMax` | Tested infrared seeker acquisition limit | m | Verified in game |

Mission selection has no in-mission shell picker in the tested setup. Gun copies, shell changes, rockets, bombs, and torpedoes worked in the examined missions; exact formulas and edge cases need separate evidence. A ground SAM's native `cannon` + `bullet{rocket}` format crashed when mounted on an aircraft. Converting a copy to `rocketGun` with a `rocket` block let tested missiles appear, launch, and guide. Radar-guided and naval SAMs remain unverified; compatibility must be tested per weapon family.

