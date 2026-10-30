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
