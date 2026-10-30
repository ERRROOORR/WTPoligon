> Русская версия: [../../ru/datamine/sensors.md](../../ru/datamine/sensors.md)

# Sensors, seekers, and countermeasures

Vehicles attach sensor files through `sensors/sensor/blk`; a preset or modification may also carry sensors. Radar, RWR, infrared trackers, and other sensor types have different trees. Changing a copied sensor and pointing the vehicle to it worked for tested radar and RWR ranges. An RWR test needs an emitting target; a silent opponent cannot establish its range.

| Path or field | Meaning | Unit | Status |
|---|---|---|---|
| Vehicle `sensors/sensor/blk` | Reference to `gameData/sensors/*.blk` | path | Verified in game |
| Radar `transivers/<mode>/range` | Detection/lock range in tested modes | m | Verified in game |
| Radar `scopeRangeSets/<set>/rangeN` | Display scale, separate from detection range | source unit | Unverified (in files only) |
| Radar `scanPatterns/<pattern>/azimuthLimits`, `elevationLimits`, `width` | Scan geometry | degrees where angles | Unverified (in files only) |
| RWR root `range` | Warning range for a tested emitter; emitter power also mattered | m | Verified in game |
| RWR `bandN`, `receivers/*`, `groups/group/*` | Bands, sectors, threat classification | mixed | Unverified (in files only) |
| Missile `rocket/opticalSeeker/rangeMax` | Infrared seeker acquisition limit | m | Verified in game |
| Vehicle `Weapon/bullets` for `trigger="countermeasures"` | Number of flares/chaff in a tested launcher | count | Verified in game |
| Launcher `bullet/rocket/signature`, vehicle `countermeasure/program` | Signature and dispensing program | mixed | Unverified (in files only) |

Radar display scale did not automatically follow the tested range change. Sensor field meanings beyond these checks are derived from file structure and need gameplay confirmation.
