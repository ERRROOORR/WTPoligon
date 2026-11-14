> Русская версия: [../../ru/datamine/bomb-planes.md](../../ru/datamine/bomb-planes.md)

# Composite aircraft ("bomb planes", Mistel)

The Mistel is three parts: a carrier aircraft, a "bomb" that releases the lower aircraft, and the lower aircraft itself.

| Part | Fields |
|---|---|
| Carrier | `bombPlaneName:t="<aircraft>"`, `haveBombPlaneSight:b=yes`, `bombPlaneEjectionVel:p3=…` |
| Release "bomb" (`bombguns/de_ju_88g_1_mistel.blk`) | `releasesBombPlane:b=yes`; no model of its own |
| Lower aircraft (`ju_88g_1_mistel`) | a normal aircraft plus `bombPlane:b=yes`, `hookNode`, `cantBeBackModel`, `changeToExplodedOnExplode`, autopilot `droppedYawPitchHoldRate` / `droppedYawPitchHoldIntegralRate` / `droppedRollHoldMult`, `bombPlaneDropAnimSpeed`, `warhead{}`, `warheadFusePart` |

| Claim | Evidence |
|---|---|
| Any aircraft can be the carrier: copy it with the three carrier fields and hang the release "bomb" on a pylon. | Verified in game (F-15EX) |
| Any aircraft can be the lower aircraft: a copy (`include` + the fields above + `warhead{}`) referenced by `bombPlaneName`. It hangs close to the carrier (`hookNode` belongs to the Mistel model) and, after release, wobbles in pitch (autopilot tuned for the Ju 88), but flies to the aim point. | Verified in game (Su-27) |
| Damage comes from `warhead{}` of the lower aircraft (the release "bomb" affects neither damage nor visuals). A nuclear recipe there gives nuclear damage but an ordinary explosion. | Verified in game |
| A player-controlled kamikaze aircraft is not achievable with these fields: `warhead{}` without `bombPlane` does not detonate on impact; `bombPlane:b=yes` hands control to the autopilot; `humanDrone:b=yes` (from FPV drones) breaks the camera and guns and does not detonate; a bigger `explosion_dmBlk` adds no ramming damage. | Verified in game |
