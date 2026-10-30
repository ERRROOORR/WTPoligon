> Русская версия: [../../ru/datamine/override.md](../../ru/datamine/override.md)

# `include` and `@override`

A local text BLK can start with `include "#/develop/gameBase/gameData/.../original.blk"` and then apply edits to that stock tree. The include is inserted at its position; subsequent lines are processed in order. Normal declarations append, even if a name already exists. An `@override` changes an existing parameter or descends into an existing block. The original game archive is untouched.

| Path or directive | Meaning | Unit | Status |
|---|---|---|---|
| First line `include "#/develop/gameBase/gameData/..."` | Load a stock BLK into the local copy | — | Verified in game |
| `"@override:name":r=value` | Replace an existing parameter of the same type | source unit | Verified in game |
| `"@override:block"{...}` | Edit inside the first matching block | — | Verified in game |
| `"@override:name[n]"` | Select the nth duplicate, counting from 1 | index | Verified in game |
| `@delete`, `@delete-all`, `@clone-last` | Remove or clone entries; defined by BLK parser | — | Unverified (in files only) |

Check the exact source tree before writing: missing targets and type mismatches are logged and skipped. Adding a plain duplicate may leave the first value in use. Game updates can change duplicate indexes. Generate one parameter per line, preserve types, resolve each edit against the installed stock tree, and verify the resulting value before installing it.

Mission, vehicle, and tested weapon copies are re-read when a mission loads; changing them does not require a game restart. Newly created preset copies also load in the running game, while re-editing an already used preset was inferred from logs rather than isolated gameplay testing. Localization CSV is different: it is read at game startup.

## Minimal invented examples

These fragments use fictitious vehicle and field names to show syntax; they are not extracted game data or ready to install. A real edit must use an existing field and its actual stock type.

```blk
include "#/develop/gameBase/gameData/units/tankModels/example_vehicle.blk"
"@override:VehiclePhys"{
  "@override:Mass"{
    "@override:Empty":r=42000
  }
}
```

For a repeated value, use its one based ordinal in the same parent block:

```blk
include "#/develop/gameBase/gameData/units/tankModels/example_vehicle.blk"
"@override:VehiclePhys"{
  "@override:mechanics"{
    "@override:gearRatios"{
      "@override:ratio[2]":r=0.75
    }
  }
}
```

`@override` targets the first match without an ordinal. `@delete`, `@delete-all`, `@clone-last`, `@override-last`, and `@delete-last` are known parser directives but were not each isolated in game. `@override:name[0]` is invalid; `[1]` selects the first occurrence. A missing target or different type logs an error and skips that edit. Validate the resolved stock tree, all ordinal paths and types, and every intended final value before installing a copy.
