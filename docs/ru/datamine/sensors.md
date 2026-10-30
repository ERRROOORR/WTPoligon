> English version: [../../en/datamine/sensors.md](../../en/datamine/sensors.md)

# Сенсоры, ГСН и противодействие

Машина подключает сенсор через `sensors/sensor/blk`; сенсоры могут также находиться в пресете или модификации. У РЛС, СПО, ИК-трекеров и других видов разные деревья. Копия сенсора со ссылкой из машины сработала для проверенных дальностей РЛС и СПО. Для проверки СПО нужен излучающий противник: молчащая цель не позволяет измерить дальность.

| Путь или поле | Смысл | Единицы | Статус |
|---|---|---|---|
| Машина `sensors/sensor/blk` | Ссылка на `gameData/sensors/*.blk` | путь | Verified in game |
| РЛС `transivers/<mode>/range` | Дальность обнаружения/захвата в проверенных режимах | м | Verified in game |
| РЛС `scopeRangeSets/<set>/rangeN` | Шкала индикатора, отдельно от дальности обнаружения | единицы исходника | Unverified (in files only) |
| РЛС `scanPatterns/<pattern>/azimuthLimits`, `elevationLimits`, `width` | Геометрия сканирования | градусы для углов | Unverified (in files only) |
| СПО, корень `range` | Дальность предупреждения для проверенного излучателя; мощность излучателя тоже влияет | м | Verified in game |
| СПО `bandN`, `receivers/*`, `groups/group/*` | Диапазоны, сектора, распознавание угроз | разные | Unverified (in files only) |
| Ракета `rocket/opticalSeeker/rangeMax` | Предел захвата ИК-ГСН | м | Verified in game |
| Машина `Weapon/bullets` при `trigger="countermeasures"` | Число ловушек/диполей в проверенной пусковой | штуки | Verified in game |
| Пусковая `bullet/rocket/signature`, машина `countermeasure/program` | Сигнатура и программа отстрела | разные | Unverified (in files only) |

Шкала индикатора РЛС не следовала автоматически за проверенным изменением дальности. Смысл остальных полей сенсоров следует из файлов и требует подтверждения в игре.
