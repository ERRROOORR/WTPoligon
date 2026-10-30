> Русская версия: [../../ru/datamine/game-logs.md](../../ru/datamine/game-logs.md)

# Reading `.clog` game logs

The client writes `.clog` under `%LOCALAPPDATA%/WarThunder/.game_logs/`. These files are obfuscated text, not plain text. In the examined format, a 768 byte XOR key repeats across the entire file. It can be estimated from a sufficiently large log by assuming the most common plaintext byte at each key position is a space; validate the decoded result rather than assuming the format never changes. Do not publish raw logs: they may contain local paths and account or machine details.

| Path or field | Meaning | Unit | Status |
|---|---|---|---|
| `.game_logs/*.clog` | Client log files | bytes | Unverified (in files only) |
| XOR offset `position % 768` | Repeating key position in examined logs | byte index | Unverified (in files only) |
| `including binary file` | An `include` was resolved; by itself it does not prove the edit affected gameplay | — | Unverified (in files only) |
| `cannot find ... for override`, `different types` | An edit was rejected by the BLK parser | — | Unverified (in files only) |

Decode into a private local directory, inspect only lines relevant to a mission load or BLK error, and compare them with an in-game observation. A clean log is necessary evidence for parsing, not sufficient evidence for gameplay behavior.

## Interpreting evidence

| Log text or condition | Where | Meaning / type | Status | Observation |
|---|---|---|---|---|
| `BUILD TIMESTAMP`, base game version | Decoded `.clog` start | Build metadata | Unverified (in files only) | Useful for matching observations to a client version. |
| `including binary file` | BLK parser messages | Stock `include` was resolved | Unverified (in files only) | Repeated on later mission loads; it does not prove the field had an effect. |
| `cannot find param/block ... for override` | BLK parser messages | Missing target and ordinal | No effect | The tested edit was skipped; check the exact owning file and duplicate index. |
| `different types ... for override` | BLK parser messages | Type mismatch | No effect | The replacement is not applied; keep the stock type. |
| `BLK invalid ... (type real)` | Parser/crash context | Malformed numeric text | Crashes game | Observed with multiple unseparated parameters on one line. |
| `load bomb properties from 'mod:...'` | Mission load | Local bomb file loaded | Unverified (in files only) | In the tested case a subsequent visual change established the gameplay effect. |

The examined logs used a 768 byte repeating XOR key. Derive a candidate key from enough log data, validate by decoded structure and low control byte rate, and avoid assuming the same key for future client builds. Logs have finite retention, so record the game version and the relevant observation separately.
