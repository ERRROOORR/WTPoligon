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

## Header and payload layout

| Field or entry | Where | Meaning / type | Status | Observation |
|---|---|---|---|---|
| `VRFs` / `VRFx` | Bytes 0–3 | Base / extended signature | Unverified (in files only) | All examined archives had `VRFx`; a reader should accept either signature. |
| `platform` | Header bytes 4–7 | Four byte platform marker | Unverified (in files only) | Read before unpacking; no gameplay effect assigned. |
| `size` | Header bytes 8–11 | Unpacked size, little endian `u32` | Unverified (in files only) | Bounds the decompression result. |
| `packed_size`, `pack_type` | Header bytes 12–15 | Low 26 bits: byte count; upper 6 bits: packing code | Unverified (in files only) | The examined archives used `0x30`. |
| Extended size, flags, version | `VRFx` extension | Two `u16` and one `u32` version | Unverified (in files only) | Version bytes identify the examined game build; extension size moves payload offset. |
| `0x10`, `0x20`, `0x30` | Packing code | Obfuscated zstd without check, plain, obfuscated zstd with MD5 | Unverified (in files only) | Only `0x30` is established by the full archive comparison here. |
| Leading/trailing 16 payload bytes | Packed payload | XOR obfuscation before zstd | Unverified (in files only) | Undo before decompressing for examined packed mode. |
| 16 bytes after packed payload | `0x30` container | MD5 of unpacked image | Unverified (in files only) | Hashes matched the examined images. |
| Name and data table offsets/counts | Unpacked image | Little endian offsets and counts | Unverified (in files only) | Counts must agree; a name points to a NUL terminated path, a data entry to offset and size. |
| `\xff?nm` | Virtual service entry | Shared BLK NameMap, non UTF-8 leading byte | Unverified (in files only) | Needed for SLIM BLK names. |
| `<hash>.dict` | Virtual service entry where present | zstd dictionary | Unverified (in files only) | Found in examined `aces` and `mis` archives; needed by some BLKs. |

The image and UI resource families need separate decoders. Some `units/*.ddsx` image payloads use Oodle, while other DDSx payloads may use zstd, LZMA or zlib; these are inner image formats, not VROMFS packing modes. Never infer a payload codec from the archive path alone. On the examined build, an independent extractor returned 35,568 identical raw entries across eight archives.
