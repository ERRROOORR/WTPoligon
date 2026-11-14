> Русская версия: [../../ru/datamine/reload-restore.md](../../ru/datamine/reload-restore.md)

# Reload and ammunition restore

| Claim | Evidence |
|---|---|
| Reload time of a gun = `1 / shotFreq` in a copy of the gun file (tank guns: 1 s, 0.05 s; manual loading 0.5 s is not overridden by the crew). Aircraft cannon rate of fire scales the same way. | Verified in game |
| Mission action `unitRestore` refills ammunition: every N seconds, fully, or after a target is destroyed; with 1 s / 0.5 s intervals the gun effectively fires non-stop. Triggering it on the fire button gives an instant reload. | Verified in game |
| There is no mission condition on remaining ammunition, so "refill when empty" cannot be expressed directly. | In files only (no such condition among mission conditions) |
