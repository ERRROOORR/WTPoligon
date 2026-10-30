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

## Binary variants and text rules

| Form or type | Where | Meaning / unit | Status | Observation |
|---|---|---|---|---|
| Kind `1`, `3`, `4`, `5` | First binary BLK byte | FAT, SLIM, SLIM+zstd, SLIM+zstd with dictionary | Unverified (in files only) | All four appeared in examined archives. Kind `2` was implemented from format description but not found there. |
| Local names count / `?nm` | BLK body / VROMFS service entry | ULEB count; zero selects shared NameMap | Unverified (in files only) | The reader needs the containing archive to resolve SLIM names. |
| `t`, `i`, `i64`, `b`, `r` | Text parameters | String, 32/64 bit integer, boolean, float32 | Unverified (in files only) | Preserve the type on override; float32 values need round trip safe formatting. |
| `c`, `m`, `p2/p3/p4`, `ip2/ip3/ip4` | Text parameters | Color, matrix, float and integer vectors | Unverified (in files only) | Binary color stores B,G,R,A; `ip4` contains four integers. |
| Repeated block or parameter name | Any BLK tree | Ordered duplicate | Unverified (in files only) | Ordinal overrides count matching names from one. Converting a tree to a plain map loses information. |
| Quoted identifier / `~` escapes | Text BLK | Name and string syntax | Unverified (in files only) | Quote names with spaces, slashes, colons or `@`; escape string quotes with `~"`. |

Text values end at `;`, newline, `}`, or `//`. Place each parameter on its own line. Supported short type codes are `t i b c r m p2 p3 p4 ip2 ip3 ip4 i64`; boolean input also accepts `on/off`, `true/false`, and `1/0`, while generated text can consistently use `yes/no`. A backslash followed by a quote does not escape it. Some binary names contain non UTF-8 bytes and must be decoded without losing the byte sequence.

The examined binary reader round tripped 31,647 files. Comparison with another text renderer exposed differences in quoted unusual names, color channel order, and `ip4` punctuation. A text renderer's output is therefore a useful cross check, not a substitute for a typed tree.
