> Русская версия: [../../ru/datamine/index.md](../../ru/datamine/index.md)

# Datamining reference

The reference describes findings from the examined game version and labels each claim by evidence: **Verified in game**, **Unverified (in files only)**, **No effect**, or **Crashes game**. A file path alone establishes structure, not gameplay behavior. “No effect” applies to the stated test. The repository contains descriptions and invented minimal examples, no extracted game content.

## Formats and validation

- [VROMFS archives](vromfs.md): headers, packing, dictionaries and virtual paths.
- [Binary and text BLK](blk.md): NameMap, types, syntax and round trips.
- [`include` and `@override`](override.md): ordered edits and validation.
- [Game logs](game-logs.md): decoding and what a log can prove.
- [Reloading and caches](caching.md): mission reload versus client restart.
- [Open tools](tools.md) and [CDK evidence](cdk.md).

## Game definitions

- [User missions and vehicles](user-missions.md): spawning, ownership and copy identities.
- [Aircraft flight models](aircraft.md) and [pylons and presets](pylons.md).
- [Weapons and ammunition](weapons-ammo.md).
- [Sensors, seekers and countermeasures](sensors.md).
- [Ground and naval physics](ground-naval.md) and [armor, damage and crew](armor-crew.md).
- [Modifications](modifications.md) and [localization](localization.md).
- [Failures and disproved approaches](failures.md).

The [program overview](../program/overview.md) explains how these findings are used when building a mission.
