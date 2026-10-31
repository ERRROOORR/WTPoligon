> Русская версия: [../../ru/program/overview.md](../../ru/program/overview.md)

# WT Poligon Beta-1.0

WT Poligon builds single-player War Thunder test missions on Windows. It reads vehicles, weapons, names and images from an installed game, then writes a user mission and, when needed, small local BLK copies. It does not edit the game's archives. The Beta-1.0 interface is in Russian; [the user guide](user-guide.md) gives the button names.

The six steps are **Vehicle → Loadout → Characteristics → Ammunition → Scenario → Review and write**. Loadout applies to aircraft and helicopters. You can use a stock loadout, change pylon weapons, edit characteristics and ammunition, choose targets and conditions, then inspect the generated file list and validation errors before writing. A built-in list shows previous writes and offers rollback. See the [tester checklist](../../TESTING.md) for what still needs in-game evidence.

An owned vehicle can launch under its real identity. An unowned vehicle launches as a local copy, which may lack some modification-dependent equipment or interface elements. A custom aircraft loadout also requires a copy. The mission appears under **Single missions → Custom → “WTP5 — <vehicle>”**. New mission BLKs load without restarting the game; changed CSV names may need a restart. See [user missions](../datamine/user-missions.md) and [modifications](../datamine/modifications.md).

The program checks generated copies against the installed source before writing. This checks file structure and intended values, not whether every combination works in battle. **“Verified in game”** means there is gameplay evidence; **“Not verified”** and **📄** identify areas that need testing. Rollback uses a manifest and hashes, and leaves files changed after installation in place. Details for contributors: [developer guide](developer-guide.md).
