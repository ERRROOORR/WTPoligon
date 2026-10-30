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
| Missile `rocket/guidance/opticalSeeker/rangeMax` | Infrared seeker acquisition limit | m | Verified in game |
| Vehicle `Weapon/bullets` for `trigger="countermeasures"` | Number of flares/chaff in a tested launcher | count | Verified in game |
| Launcher `bullet/rocket/signature`, vehicle `countermeasure/program` | Signature and dispensing program | mixed | Unverified (in files only) |

Radar display scale did not automatically follow the tested range change. Sensor field meanings beyond these checks are derived from file structure and need gameplay confirmation.

## Sensor families and references

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| Root `type=radar`, `visibilityType` in a transiver | `gameData/sensors/*.blk` | Radar; `infraRed`, `optic`, `radarIntercept` submodes | Unverified (in files only) | IR/optical trackers share radar style structures in surveyed files. |
| Root `type=rwr`, `mlws`, `lws`, `lds`, `sonar` | Sensor BLK | Warning, laser, sonar families | Unverified (in files only) | File survey classified these types; only selected RWR range was tested in game. |
| `sensors/sensor/{blk,dmPart,node,turretIndex,external}` | Vehicle BLK | Sensor link, damage part, mount and flags | Unverified (in files only) | Links occur at vehicle root, in a modification effect, and inside an aircraft weapon choice. Case sensitive `sensor`/`Sensor` appears in some choices. |
| `transivers/<mode>/{range,rangeMax,rcs,power,band}` | Radar/track sensor | Detection parameters, m where range | Unverified (in files only) | Only `range` in tested modes was changed in game; `rangeMax` and other inputs were not isolated. |
| `transivers/<mode>/antenna/{angleHalfSens,sideLobesSensitivity}` | Radar sensor | Beam properties | Unverified (in files only) | Some files instead split antenna by azimuth and elevation. |
| `scanPatterns/<name>/{azimuthLimits,elevationLimits,width,barsCount,period}` | Radar sensor | Scan geometry, degrees / count / time | Unverified (in files only) | Surveyed files contain narrow, wide and track patterns; effects not isolated. |
| `scanPatternSets/<name>/scanPatternN`, `scopeRangeSets/<name>/rangeN` | Radar sensor | Mode choices and display ranges | Unverified (in files only) | Display scale stayed separate from tested detection range. |
| `signals/<name>`, `fsms/<name>` | Radar sensor | Signal filters and state machine | Unverified (in files only) | Present in stock radar data; exact editing effects untested. |
| RWR `bandN`, `receivers/*`, `groups/group/{type,priority,detectLaunch}` | RWR sensor | Bands, sectors, threat library | Unverified (in files only) | An emitter was needed to measure the tested RWR range. |
| MLWS `automaticFlares`, `numFlares`, `flaresInterval` | Warning sensor | Automatic release settings | Unverified (in files only) | Found in some warning sensors; not tested as local edits. |
| `counterMeasures/counterMeasure/blk`, `countermeasure/program/*` | Vehicle BLK | Jammer attachment and release program | Unverified (in files only) | Separate from a launcher `Weapon`'s ammunition count. |
| Launcher `bullet/rocket/signature/{infraRed,radar}` | `gameData/Weapons/rocketGuns/*.blk` | Flare/chaff signature | Unverified (in files only) | Found in countermeasure payload files; effects not isolated. |

For a range edit, make a sensor copy and point the vehicle's matching `sensors/sensor/blk` to it. A copied radar changed detection/lock behavior; a copied RWR changed warning range against a radiating target. A silent opponent gave no RWR evidence. An infrared missile's copied `rocket/guidance/opticalSeeker/rangeMax` changed acquisition range, and changing `Weapon/bullets` changed the tested countermeasure count. Other fields in this table need separate in-game checks.

## Seeker and warning details

| Path or field | Where | Meaning / type or unit | Status | Observation |
|---|---|---|---|---|
| `rocket/guidance/opticalSeeker/rangeMax` | Missile weapon BLK | Overall acquisition limit, m | Verified in game | A reduced value shortened tested front and rear infrared lock distance. |
| `rocket/guidance/opticalSeeker/{rangeBand0..7,fov,lockAngleMax,angleMax}` | Missile weapon BLK | Band ranges, view and lock angles | Unverified (in files only) | Present in the tested missile's file; band meaning and local effects were not isolated. |
| `rocket/guidance/table0..2/{rangeMax,rangeMaxDogfight,timeMax}` | Missile weapon BLK | Launch envelope tables | Unverified (in files only) | Separate from seeker range; changes to `rangeMax` in the seeker do not prove these tables recalculate. |
| RWR `range` | Sensor root | Warning range, m | Verified in game | Reduction shortened warning against an aircraft radar. A powerful ground emitter was still heard farther than that number. |
| RWR `{targetRange,mandatoryRecognition,detectTracking,detectLaunch}` | Sensor root | Indication and classification settings | Unverified (in files only) | Found in source data; the range test did not isolate them. |
| `WeaponSlots/WeaponSlot/WeaponPreset/Weapon/bullets` with `trigger=countermeasures` | Aircraft BLK | Launcher quantity, integer | Verified in game | Increased count appeared on HUD and dispensed. |

The RWR result must be read with its emitter: the first attempt with a non-radiating opponent produced no useful range observation. Against an aircraft radar, reducing RWR root `range` moved the warning point inward. A ground radar still triggered farther away; transmitter power or other factors are plausible, but their formula remains unverified. The radar detection test changed `transivers/*/range`, while display `scopeRangeSets` stayed separate.
