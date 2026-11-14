> Русская версия: [../../ru/datamine/support.md](../../ru/datamine/support.md)

# Called-in vehicles (drones and support)

Ground vehicles can call a scout drone (`supportPlane`) or accompanying units like SAM launchers (`supportPlanes`).

| Claim | Evidence |
|---|---|
| Replacing `supportPlane/supportPlaneClass` with any aircraft spawns that aircraft as the called-in "drone"; it is player-controlled and fires its own weapons (stock or a custom loadout via a vehicle copy). A matching `planeStartSpeed` (km/h) is needed, otherwise the aircraft stalls. Spawn height cannot be changed (no field found). | Verified in game |
| A tank or SAM vehicle can be called the same way (`supportPlanes{ plane{ … isSlave:b=yes } }`). Several **ground** units need one entry each — `count` does not multiply. | Verified in game |
| One vehicle has one kind of call: with `supportPlanes` present, the drone call (`supportPlane`) disappears; aircraft and ground units cannot be mixed. Ships cannot be called (no call button). | Verified in game |
