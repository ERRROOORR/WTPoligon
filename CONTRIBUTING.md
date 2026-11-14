> Русская версия: [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md)

# Contributing

To report a documentation error or a datamining finding, give the game version, the virtual BLK path and the full
field path, the original value and type, the proposed change and the expected behavior. Mark a finding
**Unverified (in files only)** until it is compared in the game.

For **Verified in game**, describe two cases that differ in one field: stock and changed. State how the mission or
the game was reloaded, the observed result and whether it was repeated. Check the game log for parser errors; a clean
log does not prove an effect in gameplay. For **No effect**, state the tested values and the observation, not a claim
that the game ignores the field.

Write in your own words and send only what is needed to reproduce the finding. Remove personal paths, account
details, raw logs, game files, extracted data and images. A BLK field name or path is enough. Documentation changes go
to both `docs/en/` and `docs/ru/` at matching paths, with the link to the other language at the top.
