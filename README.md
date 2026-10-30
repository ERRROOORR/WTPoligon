> Русская версия: [README.ru.md](README.ru.md)

# WT Poligon

WT Poligon is a builder for War Thunder single player custom test-drive missions. It aims to let you choose any vehicle, assemble an aircraft loadout, mount weapons on pylons, and change characteristics through local BLK copies using `include` and `@override`. Original game archives remain untouched; managed files are tracked for rollback. An unavailable or unowned vehicle may run as a custom copy with reduced interface or equipment behavior.

**Status: in development, no release yet.** There is no executable to install. Running from source: coming soon, when the program code is published.

| Capability | Status |
|---|---|
| Installed-game vehicle and weapon catalog, mission generator, basic desktop window | Implemented in development build |
| Aircraft loadout builder, custom pylons and tested air-compatible missile conversions | Implemented; core paths verified in game |
| Weightless loadout through a flight-model copy | Mechanism verified in game; GUI edge cases still being checked |
| General characteristics editor | In development |
| Ammunition, sensors, project library, sharing, packaged release | Planned; selected file edits researched in game |

The catalog is derived from the installed game. We label each technical claim **Verified in game**, **Unverified (in files only)**, or **No effect**. “No effect” means no observable effect in the stated test. Every new capability needs a file-level explanation and an in-game check before it is presented as working.

## Documentation

- [Datamining: VROMFS](docs/en/datamine/vromfs.md), [BLK](docs/en/datamine/blk.md), [overrides](docs/en/datamine/override.md), [logs](docs/en/datamine/game-logs.md)
- [Missions](docs/en/datamine/user-missions.md), [aircraft](docs/en/datamine/aircraft.md), [weapons and ammunition](docs/en/datamine/weapons-ammo.md), [sensors](docs/en/datamine/sensors.md), [ground and naval vehicles](docs/en/datamine/ground-naval.md), [localization](docs/en/datamine/localization.md)
- [Program overview](docs/en/program/overview.md), [roadmap](docs/en/program/roadmap.md), [contributing](CONTRIBUTING.md)

## License and notice

The documentation is licensed under [CC BY 4.0](LICENSE). Program source code will be published later under a separate license. WT Poligon is an unofficial project. War Thunder is a trademark of Gaijin Entertainment. No game files, extracted game data, or game images are distributed here.
