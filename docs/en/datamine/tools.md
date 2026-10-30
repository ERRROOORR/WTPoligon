> Русская версия: [../../ru/datamine/tools.md](../../ru/datamine/tools.md)

# Open tools and research references

These are external references for studying formats and comparing parser output. They are not bundled with this repository. Check each project's own license and current behavior before using it.

| Project | Use | Evidence in this research |
|---|---|---|
| [WTOSF `wt_ext_cli`](https://github.com/Warthunder-Open-Source-Foundation/wt_ext_cli) | VROMFS extraction and BLK text reference | Raw extraction matched all examined archive entries byte for byte; most parsed BLK trees agreed. Its text renderer had a small set of quoting, color channel, and `ip4` formatting issues in the examined version. |
| [WTOSF `wt_blk`](https://github.com/Warthunder-Open-Source-Foundation/wt_blk) | Independent BLK format implementation | Useful for checking typed values and binary variants. |
| [DagorEngine](https://github.com/GaijinEntertainment/DagorEngine) | Text BLK parser and directives | `blk_parser.cpp`, `blk_core.cpp`, and serialization code explain `include`, override ordinals, types, and `~` string escapes. |
| [War Thunder Datamine](https://github.com/gszabi99/War-Thunder-Datamine) | Public history of extracted definitions | Useful for following changes across game versions; this repository does not redistribute those files. |
| [WTFTD](https://github.com/StonewarP/WTFTD-War_Thunder_Full_Test_Drive) | Community penetration calculations | Its formula implementation was compared with in-game penetration observations; exact edge cases still need validation. |

The examined client archives used `VRFx`, packing mode `0x30`; 35,568 extracted files matched the independent raw extraction. The binary BLK reader round tripped 31,647 examined files. Parsing agreement proves a format interpretation for that game version, not an effect of any gameplay field. See [VROMFS](vromfs.md), [BLK](blk.md), and [Logs](game-logs.md).
