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
| `DamageParts/crew/hp` | Возможная живучесть экипажа; отдельный эффект не установлен | единицы исходника | Unverified (in files only) |
| `ammo/detonateProb` | Возможный параметр детонации; явной разницы в опыте нет | вероятность | Unverified (in files only) |
| `ammoStowages/*/fatalExplosion=no` | Попытка защитить БК | логическое | No effect |

Здесь No effect означает отсутствие показанного эффекта в описанной проверке, а не доказательство, что движок всегда игнорирует поле. Поведение экипажа и БК было скрыто взрывами боекомплекта. Не обещайте редактор живучести экипажа на основе этих полей.
## Карта полей физики и повреждений

| Путь или поле | Где находится | Смысл / тип или единицы | Статус | Наблюдение |
|---|---|---|---|---|
| `maxFwdSpeed`, `maxRevSpeed` | Корень BLK танка или корабля | Верхние значения скорости | Unverified (in files only) | Похожие числа встречаются у машин с разной реальной скоростью; правка `ShipPhys/engines/maxSpeed` дала скорость выше неизменённого верхнего значения. |
| `VehiclePhys/Mass/{Empty,TakeOff,Fuel}` | BLK танка | Массы, кг | Unverified (in files only) | `Empty` изменило разгон проверенного танка; `TakeOff` и `Fuel` отдельно не проверены. |
| `VehiclePhys/engine/{horsePowers,maxRPM,minRPM}` | BLK танка | Мощность, л.с.; обороты | Unverified (in files only) | `horsePowers` изменило разгон; поля оборотов не проверены отдельно. |
| `VehiclePhys/mechanics/{mainGearRatio,sideGearRatio,driveGearRadius}` | BLK танка | Передачи / радиус привода | Unverified (in files only) | Есть в стоковой трансмиссии; в игре проверена только отдельная `gearRatios/ratio`. |
| `VehiclePhys/suspension/{defaultDampeningForce,suspensionOffsets}`, `VehiclePhys/tracks/*`, `floats/*` | BLK танка | Подвеска, гусеницы и плавучесть | Unverified (in files only) | Семейства найдены в файлах; игровые правки не изолированы. |
| `ShipPhys/mass/{Empty,momentOfInertia,CenterOfGravity}` | BLK корабля | Масса и инерция | Unverified (in files only) | Есть у стоковых кораблей, отдельно в игре не менялись. |
| `ShipPhys/engines/{maxReverseSpeed,speedToTime,reverseSpeedToTime}` | BLK корабля | Задний ход и таблицы скорости/времени | Unverified (in files only) | Одно `maxSpeed` удвоило наблюдаемую скорость проверенного корабля; таблицы разгона не изолированы. |
| `ShipPhys/hydrodynamics/{bodyArea,mulReaction,rudder,hydrofoils}` | BLK корабля | Корпус, руление, подводные крылья | Unverified (in files only) | Завышенная проверенная скорость вызвала сильный крен на повороте; отдельные поля гидродинамики не менялись. |
| `DamageParts/<группа>/<часть>/{armorThickness,hp,armorClass}` | BLK машины | Толщина в мм, прочность, класс | Unverified (in files only) | `armorThickness` одной проверенной плиты остановила снаряд, соседняя плита осталась пробиваемой; другие поля не изолированы. |
| `DamageEffects/part`, `fireParamsPreset`, `fireProtectionHp` | BLK машины / общие пресеты пожара | Попадания, пожар и защита | Unverified (in files only) | Найдены в деревьях повреждений; действие локальных правок не изолировано. |
| `ammoStowages/<укладка>/{shells,charges,fatalFire,fatalExplosion}`, `ammo/*` | BLK танка или корабля | Размещение БК и детонация | Unverified (in files only) | Проверка `fatalExplosion=no` не защитила мишень; прочие поля требуют отдельных опытов. |
| `tank_crew/<член>/{dmPart,role,substitute}`, `minCrewMemberAliveCount` | BLK танка/корабля | Связь частей и ролей экипажа | Unverified (in files only) | Структура есть; высокое `DamageParts/crew/hp` не доказало живучесть экипажа из-за взрыва БК. |

Для наземной машины подтверждены правки `horsePowers`, `Mass/Empty` и выбранного повторяющегося `gearRatios/ratio`. Более длинная верхняя передача включалась, но мощности для дальнейшего разгона не хватало. `maxSpeed` корабля удвоило скорость на HUD; неизменённое верхнее `maxFwdSpeed` не ограничило её. Увеличение `armorThickness` одной плиты сделало её непробиваемой, соседняя нижняя плита осталась пробиваемой. Регуляторы живучести экипажа и БК не установлены.

## Дополнительные поля подвижности в файлах

| Путь или поле | Где находится | Смысл / тип или единицы | Статус | Наблюдение |
|---|---|---|---|---|
| `VehiclePhys/Mass/{momentOfInertia,CenterOfGravity,AdvancedMass,trackMass,engineInertialMass}` | BLK танка | Инерция, центр и массы | Unverified (in files only) | Найдены у стоковой техники; единицы кажущейся инерции не установлены. |
| `VehiclePhys/engine/{type,model,manufacturer,rpmTau}` | BLK танка | Вид двигателя и данные реакции | Unverified (in files only) | Есть у части машин; локальной отдельной проверки нет. |
| `VehiclePhys/mechanics/{steerType,neutralGearRatio,gearType,tracked}` | BLK танка | Руление и режимы трансмиссии | Unverified (in files only) | Различаются у колёсной и гусеничной техники; эффект не изолирован. |
| `VehiclePhys/suspension/{dampeningRelaxationRatio,dampeningCompressionRatio,defaultGearRadius}` | BLK танка | Демпфирование и геометрия колёс | Unverified (in files only) | Есть в стоковых файлах; локальный эффект не измерялся. |
| `VehiclePhys/movableSuspension/{speed,maxSpeedForMove,clearance,pitch,roll}` | Некоторые BLK танков | Регулируемая подвеска | Unverified (in files only) | Найдена у гидропневматической техники; прямой проверки путей нет. |
| `ShipPhys/engines/engine/{pos,propeller,engineDmPart,shaftDmPart,boilerPressure}` | BLK корабля | Повторяющийся вал и двигатель | Unverified (in files only) | У корабля бывает несколько блоков `engine`; порядок повторов нужно сохранять. |
| `ShipPhys/hydrodynamics/rudder/{pos,area,deflection,dmPart}` | BLK корабля | Повторяющееся определение руля | Unverified (in files only) | Найдено в стоке; влияние локальной правки руления не изолировано. |
| `ShipPhys/hydrodynamics/hydrofoils` | BLK корабля | Блоки подводных крыльев | Unverified (in files only) | Структура есть лишь у части кораблей. |

Верхнее `maxFwdSpeed` нельзя выдавать за паспортную максимальную скорость: многие изученные танки имели похожее значение при разной реальной скорости. Опыт с длинной передачей показывает, что её нужно оценивать вместе с мощностью двигателя. Правка скорости корабля также усилила крен на резком повороте; интерфейс должен предупреждать об этом наблюдении.
