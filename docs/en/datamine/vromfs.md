> Русская версия: [../../ru/datamine/vromfs.md](../../ru/datamine/vromfs.md)

# VROMFS containers

Game archives such as `aces.vromfs.bin`, `char.vromfs.bin`, and `mis.vromfs.bin` contain virtual file systems. Read them from the installed game; this repository distributes neither archives nor extracted contents. Archive paths are generally lowercase. The service entry `?nm` supplies a shared BLK name table; some archives also carry a zstd dictionary.

An extractor reads the `VRFs`/`VRFx` header, determines the packing mode, reverses the container obfuscation where present, decompresses the zstd payload, checks its MD5 when supplied, then walks the name and data tables. A binary BLK can require both `?nm` and the archive dictionary. Check offsets, lengths, hashes, and decompressed size before trusting a file. The examined archives used `VRFx` and packing mode `0x30`; other modes need separate validation.

| Path or field | Meaning | Unit | Status |
|---|---|---|---|
| `*.vromfs.bin` / `VRFx` | Archive and extended header with game version | bytes/version | Unverified (in files only) |
| Header `size`, `packed_size`, `pack_type` | Decompressed size, packed size, packing mode | bytes/code | Unverified (in files only) |
| Archive `?nm`, `*.dict` | Shared BLK names and optional zstd dictionary | — | Unverified (in files only) |
| Virtual `gamedata/.../*.blk` | Game definitions inside an archive | — | Unverified (in files only) |

The container reader was checked against independent raw extraction on the examined game version. This verifies parsing, not future archive layouts.
