> Русская версия: [../../ru/datamine/localization.md](../../ru/datamine/localization.md)

# Localization

Mission-local `usr_<mission>.csv` files can name a mission and custom units or weapons without replacing the game's global `lang` directory. Put the CSV beside the mission under `UserMissions/`; its stem must match the mission identity. CSV uses semicolons, a language header, and UTF-8. Existing game CSVs have more language columns; a small mission CSV may include only the needed columns. Test the actual client language.

| Path or key | Meaning | Unit | Status |
|---|---|---|---|
| `mission_settings/mission/name` | Identity paired with the mission CSV | — | Verified in game |
| `UserMissions/usr_<mission>.csv` | User localization; loaded when the game starts | — | Verified in game |
| `missions/<mission>` | Mission list title | text | Verified in game |
| `<copy>_1` | Custom vehicle name in battle messages | text | Verified in game |
| `<copy>_shop`, `<copy>_0`, `<copy>_2`, `<copy>/date` | Other vehicle card keys; exact contribution of each not isolated | text | Unverified (in files only) |
| `weapons/<weapon copy>/short` | Short copied missile/launcher name | text | Verified in game |
| Weapon `bullet/bulletName` → CSV key | Copied shell name | text | Verified in game |

Localization CSV is read at game startup: restart after adding or changing names. Mission and edited BLK files have a different reload schedule. A missing key may appear as an internal name. The tested mission title and vehicle card were localized; the exact vehicle card key among several simultaneously added candidates remains unknown.
