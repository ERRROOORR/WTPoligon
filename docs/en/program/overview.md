> Русская версия: [../../ru/program/overview.md](../../ru/program/overview.md)

# WT Poligon 2.0-beta

WT Poligon builds single-player War Thunder test missions on Windows. It reads vehicles, weapons, names and images
from the installed game and writes a user mission and, where edits need it, small local BLK copies. The game archives
are not modified. The interface is in Russian; [the user guide](user-guide.md) gives the button names.

## Steps

1. **Vehicle** — any vehicle of the game; save and open your own configurations (*My vehicles*).
2. **Loadout** — aircraft and helicopters only: stock or custom pylons, any weapon, Mistel bomb planes.
3. **Characteristics** — engine, mass, radar, RWR, countermeasures, reload, names.
4. **Ammunition** — ammo rack, shells and their fields, nuclear charge.
5. **Called-in vehicles** — drones and escorts.
6. **Scenario** — targets, map, conditions, rules.
7. **Review and write** — file list, validation errors, writing, rollback of previous writes.

What still needs in-game evidence: the [tester checklist](../../TESTING.md).

## How a vehicle launches

- An owned vehicle can launch under its real identity.
- An unowned vehicle launches as a local copy. The copy may lack some modification-dependent equipment or interface
  elements.
- A custom aircraft loadout also requires a copy.
- The mission appears under **Single missions → Custom → "WTP5 — <vehicle>"**. New mission BLKs load without a game
  restart; changed CSV names may need one.

See [user missions](../datamine/user-missions.md) and [modifications](../datamine/modifications.md).

## Checks and rollback

- Before writing, the program checks generated copies against the installed source. This checks file structure and
  intended values, not whether every combination works in battle.
- Rollback uses a manifest and hashes. Files changed after installation are left in place.

Details for contributors: [developer guide](developer-guide.md).
