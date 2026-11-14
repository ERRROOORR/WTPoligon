> Русская версия: [../../ru/datamine/map-borders.md](../../ru/datamine/map-borders.md)

# Map borders ("Return to the battlefield")

| Claim | Evidence |
|---|---|
| The return-to-battle zone comes from the **level**, not the mission: `mapCoord0/1` and `aiMapCoord0/1` in `levels/<map>.blk`. Mission battle areas and `missionBattleArea` options do not remove it. | Verified in game |
| A mission may reference its own level copy from `content/pkg_local/levels/<name>.blk` + `.bin` (the `.bin` terrain can be a byte copy of the stock one). | Verified in game (the copy loads) |
| The level BLK must be valid text BLK: block names containing `*` (e.g. `"microdetail_sand_c_tex_n*"{`) must be quoted. Otherwise the game logs `can't open level blk` and silently hides the mission from the list. | Verified in game |
| Map images: missions on third-party levels show the picture from `customLevelMap` / `customLevelTankMap` (a file path); a stock texture name shows an empty preview in the menu. | Verified in game (menu preview) |
| Air maps already use ±65 536 m; the ground firing range is about −6 000…10 000 m. Whether ±65 536 m on the firing range removes the warning entirely is | Unverified |
