> Русская версия: [../../ru/datamine/nuclear.md](../../ru/datamine/nuclear.md)

# Nuclear warheads

How the game decides that an explosion is nuclear, and how to give that behaviour to other munitions.

| Claim | Evidence |
|---|---|
| Stock nuclear bombs carry `yield` (kilotons) inside `bomb{}`; the full nuclear explosion (flash, mushroom) is drawn from `yield` alone — `nuclearExplosionFx` is optional (some 5 kt variants set `explosion_massive` and `createVolumetricCloud:b=no`). | Verified in game |
| Any **bomb** or **rocket/ATGM/SAM** becomes nuclear (damage and visuals) with: `yield:r=<kt>`, `explosiveType:t="tnt"`, `explosiveMass:r=20000`, `pressureDamage{ damageType:t="pressure" }` inside its `bomb{}` / `rocket{}` block. | Verified in game |
| A **gun shell** (`bullet{}`) with the same fields gets nuclear damage but an ordinary explosion; adding only `yield`+`pressureDamage` gives a normal HE burst. | Verified in game |
| A gun shell becomes a full nuclear round when it is an **unguided `bullet{ rocket{…} }`** with the recipe above. | Verified in game |
| An aircraft used as a bomb (composite aircraft, see [bomb planes](bomb-planes.md)): the recipe in its `warhead{}` gives nuclear **damage** only — no mushroom, with or without an explicit `nuclearExplosionFx`. | Verified in game |

Edits are made in a copy of the weapon file (`include` of the stock file plus the changed block); the stock file is never touched.
