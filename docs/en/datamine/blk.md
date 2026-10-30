> Русская версия: [../../ru/datamine/blk.md](../../ru/datamine/blk.md)

# BLK: binary and text

BLK is a tree of named blocks and typed parameters. Binary files in VROMFS may store names locally (FAT) or refer to the archive `?nm` table (SLIM); variants can use zstd and an archive dictionary. Text BLK is used for local copies and missions. Preserve duplicate names and their order: an override can target a particular occurrence.

| Path or field | Meaning | Unit | Status |
|---|---|---|---|
| Binary BLK kind `1`, `3`, `4`, `5` | FAT, SLIM, and compressed SLIM variants observed in archives | code | Unverified (in files only) |
| `?nm` / BLK own names | Shared or local name table | — | Unverified (in files only) |
| `name:t="text"` | Text | — | Unverified (in files only) |
| `name:i`, `name:i64`, `name:b` | 32/64 bit integer, boolean (`yes`/`no`) | value | Unverified (in files only) |
| `name:r`, `name:c`, `name:m` | Float, color, matrix | value | Unverified (in files only) |
| `name:p2/p3/p4`, `name:ip2/ip3/ip4` | Float or integer vectors | value | Unverified (in files only) |

In text BLK, quote names containing special characters, put one parameter per line, and escape strings with `~` (`~"`, `~~`, `~n`). A backslash is not the string escape character. Keep the original parameter type when overriding. Binary parsing and text round trips were checked on the examined files; that alone does not prove a field affects gameplay.
