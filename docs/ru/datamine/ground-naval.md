> English version: [../../en/datamine/ground-naval.md](../../en/datamine/ground-naval.md)

# Наземная техника и флот

Физика наземной машины находится главным образом в `gameData/units/tankModels/<машина>.blk`, в блоке `VehiclePhys`; корабли используют `gameData/units/ships/<машина>.blk` и `ShipPhys`. Повторяющиеся передаточные числа сохраняйте в исходном порядке. Указанная в корне максимальная скорость не обязательно равна фактической скорости движения.

| Путь или поле | Смысл | Единицы | Статус |
|---|---|---|---|
| Танк `VehiclePhys/engine/horsePowers` | Мощность; увеличение улучшило разгон | л. с. | Verified in game |
| Танк `VehiclePhys/Mass/Empty` | Пустая масса; увеличение замедлило разгон | кг | Verified in game |
| Танк `VehiclePhys/mechanics/gearRatios/ratio[n]` | Упорядоченные передачи; изменённая высшая включалась, но упиралась в мощность | отношение | Verified in game |
| Танк `VehiclePhys/mechanics/maxBrakeForce` | Тормозное усилие по имени поля; отдельный эффект не измерен | единицы исходника | Unverified (in files only) |
| Корабль `ShipPhys/engines/maxSpeed` | Настройка скорости; проверенное увеличение значительно подняло скорость | м/с (вывод) | Verified in game |
| Корабль `ShipPhys/engines/speedToTime` | Таблица скорости и разгона | разные | Unverified (in files only) |
| `DamageParts/<часть>/armorThickness` | Толщина брони конкретной части | мм | Verified in game |
| `DamageParts/crew/hp` | Возможная живучесть экипажа; отдельный эффект не установлен | единицы исходника | No effect |
| `ammo/detonateProb`, `ammoStowages/*/fatalExplosion` | Возможные параметры живучести БК; ясного защитного эффекта в тесте не было | вероятность/логическое | No effect |

Здесь No effect означает отсутствие показанного эффекта в описанной проверке, а не доказательство, что движок всегда игнорирует поле. Поведение экипажа и БК было скрыто взрывами боекомплекта. Не обещайте редактор живучести экипажа на основе этих полей.
