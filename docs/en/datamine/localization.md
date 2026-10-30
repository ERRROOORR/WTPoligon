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

## Key construction and limits

| Path or key | Where | Meaning / type | Status | Observation |
|---|---|---|---|---|
| `missions/<mission>` | User mission CSV | Mission title, UTF-8 text | Verified in game | Localized after restarting the client. |
| `<vehicle>_1` | User mission CSV | Vehicle name in battle log and player list | Verified in game | A tested copied tank used this name; a copied aircraft without this key kept its internal ID. |
| `<vehicle>_shop`, `_0`, `_2`, `/date` | User mission CSV | Shop/card/class/date variants | Unverified (in files only) | A card was localized with several candidate keys present; their individual contribution was not isolated. |
| `weapons/<weapon>/short` | User mission CSV | Short copied missile name | Verified in game | Appeared on the loadout HUD and in the battle log after restart. |
| `bullet/bulletName` | Copied weapon BLK | Lookup key for copied shell text | Verified in game | A changed key with CSV entry named a tested shell in the battle log. |
| `locName`, `locDesc` | `mission_settings/mission` | Mission title/description or localization key | Unverified (in files only) | Literal mission text is supported; exact key lookup behavior was not isolated. |
| `uniqueName` | Mission unit props | Bot/crew name key | Unverified (in files only) | Stock examples suggest bot naming, not a replacement for vehicle identity. |

CSV uses semicolons and a header with language columns. A minimal new file can contain English and Russian columns; escape CSV quotes correctly. Keep mission stem, `mission_settings/mission/name`, and `usr_<mission>.csv` aligned. The mission CSV avoids replacing the global `lang` directory. A missing key may display as its identifier; ensure every named copy receives its `_1` entry.
