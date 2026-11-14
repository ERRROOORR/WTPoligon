> English version: [../../en/datamine/bomb-planes.md](../../en/datamine/bomb-planes.md)

# Составные самолёты («самолёты-бомбы», Mistel)

Mistel состоит из трёх частей: самолёт-носитель, «бомба», которая отцепляет нижний самолёт, и сам нижний самолёт.

| Часть | Поля |
|---|---|
| Носитель | `bombPlaneName:t="<самолёт>"`, `haveBombPlaneSight:b=yes`, `bombPlaneEjectionVel:p3=…` |
| «Бомба»-отцепка (`bombguns/de_ju_88g_1_mistel.blk`) | `releasesBombPlane:b=yes`; своей модели нет |
| Нижний самолёт (`ju_88g_1_mistel`) | обычный самолёт + `bombPlane:b=yes`, `hookNode`, `cantBeBackModel`, `changeToExplodedOnExplode`, автопилот `droppedYawPitchHoldRate` / `droppedYawPitchHoldIntegralRate` / `droppedRollHoldMult`, `bombPlaneDropAnimSpeed`, `warhead{}`, `warheadFusePart` |

| Утверждение | Доказательство |
|---|---|
| Носителем может быть любой самолёт: копия с тремя полями носителя и «бомба»-отцепка на пилоне. | Проверено в игре (F-15EX) |
| Нижним может быть любой самолёт: копия (`include` + поля выше + `warhead{}`), на которую указывает `bombPlaneName`. Висит вплотную к носителю (`hookNode` — от модели Mistel), после отцепки покачивается по тангажу (автопилот под Ju 88), но летит к точке прицеливания. | Проверено в игре (Су-27) |
| Урон — из `warhead{}` нижнего самолёта («бомба»-отцепка не влияет ни на урон, ни на вид). Ядерный рецепт там даёт ядерный урон, но обычный взрыв. | Проверено в игре |
| Управляемого камикадзе этими полями не сделать: `warhead{}` без `bombPlane` при таране не взрывается; `bombPlane:b=yes` отдаёт управление автопилоту; `humanDrone:b=yes` (от FPV-дронов) ломает камеру и пушки и не взрывается; усиленный `explosion_dmBlk` урона при таране не даёт. | Проверено в игре |
