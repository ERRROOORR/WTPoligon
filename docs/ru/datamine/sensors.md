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
| Ракета `rocket/guidance/opticalSeeker/rangeMax` | Предел захвата ИК-ГСН | м | Verified in game |
| Машина `Weapon/bullets` при `trigger="countermeasures"` | Число ловушек/диполей в проверенной пусковой | штуки | Verified in game |
| Пусковая `bullet/rocket/signature`, машина `countermeasure/program` | Сигнатура и программа отстрела | разные | Unverified (in files only) |

Шкала индикатора РЛС не следовала автоматически за проверенным изменением дальности. Смысл остальных полей сенсоров следует из файлов и требует подтверждения в игре.
## Виды сенсоров и ссылки

| Путь или поле | Где находится | Смысл / тип или единицы | Статус | Наблюдение |
|---|---|---|---|---|
| Корневой `type=radar`, `visibilityType` в трансивере | `gameData/sensors/*.blk` | РЛС; подвиды `infraRed`, `optic`, `radarIntercept` | Unverified (in files only) | ИК и оптические трекеры используют структуры типа РЛС в изученных файлах. |
| Корневой `type=rwr`, `mlws`, `lws`, `lds`, `sonar` | BLK сенсора | СПО, предупреждение, лазер, гидроакустика | Unverified (in files only) | Типы классифицированы по файлам; в игре проверена только дальность выбранного СПО. |
| `sensors/sensor/{blk,dmPart,node,turretIndex,external}` | BLK машины | Ссылка, часть повреждения, крепление и флаги | Unverified (in files only) | Ссылки есть в корне машины, эффекте модификации и варианте авиационного оружия. В некоторых вариантах встречается `Sensor` с заглавной буквы. |
| `transivers/<режим>/{range,rangeMax,rcs,power,band}` | РЛС или трекер | Параметры обнаружения, дальность в м | Unverified (in files only) | В игре меняли только `range` проверенных режимов; `rangeMax` и прочие входы не изолированы. |
| `transivers/<режим>/antenna/{angleHalfSens,sideLobesSensitivity}` | BLK РЛС | Параметры луча | Unverified (in files only) | Некоторые файлы вместо этого разделяют антенну по азимуту и углу места. |
| `scanPatterns/<имя>/{azimuthLimits,elevationLimits,width,barsCount,period}` | BLK РЛС | Геометрия обзора, градусы / число / время | Unverified (in files only) | Найдены узкие, широкие и сопровождающие шаблоны; эффект правок не изолирован. |
| `scanPatternSets/<имя>/scanPatternN`, `scopeRangeSets/<имя>/rangeN` | BLK РЛС | Режимы и шкалы индикатора | Unverified (in files only) | Шкала индикатора не следовала автоматически за проверенной дальностью. |
| `signals/<имя>`, `fsms/<имя>` | BLK РЛС | Фильтры сигналов и автомат состояний | Unverified (in files only) | Есть в стоковых данных; эффект правки не проверен. |
| СПО `bandN`, `receivers/*`, `groups/group/{type,priority,detectLaunch}` | BLK СПО | Диапазоны, секторы, библиотека угроз | Unverified (in files only) | Для измерения дальности проверенного СПО потребовалась излучающая цель. |
| МАВС `automaticFlares`, `numFlares`, `flaresInterval` | BLK предупреждения | Настройки автоматического отстрела | Unverified (in files only) | Есть у части сенсоров; локальные правки не проверены. |
| `counterMeasures/counterMeasure/blk`, `countermeasure/program/*` | BLK машины | Подключение подавителя и программа отстрела | Unverified (in files only) | Отделены от количества в `Weapon` пусковой. |
| Пусковая `bullet/rocket/signature/{infraRed,radar}` | `gameData/Weapons/rocketGuns/*.blk` | Сигнатура ловушки или диполей | Unverified (in files only) | Есть в файлах противодействия; действие не изолировано. |

Для правки дальности нужна копия сенсора и ссылка на неё в соответствующем `sensors/sensor/blk` машины. Копия РЛС изменила обнаружение и захват; копия СПО изменила дальность предупреждения по излучающей цели. Молчавший противник ничего не доказал о СПО. Правка `rocket/guidance/opticalSeeker/rangeMax` в копии ракеты изменила дальность захвата, а `Weapon/bullets` — число ловушек в проверенной пусковой. Остальные поля таблицы требуют отдельных опытов.

## Детали ГСН и предупреждения

| Путь или поле | Где находится | Смысл / тип или единицы | Статус | Наблюдение |
|---|---|---|---|---|
| `rocket/guidance/opticalSeeker/rangeMax` | BLK ракеты | Общий предел захвата, м | Verified in game | Уменьшение сократило проверенную дальность ИК-захвата спереди и сзади. |
| `rocket/guidance/opticalSeeker/{rangeBand0..7,fov,lockAngleMax,angleMax}` | BLK ракеты | Дальности по диапазонам, обзор и углы | Unverified (in files only) | Есть у проверенной ракеты; смысл диапазонов и локальные эффекты не изолированы. |
| `rocket/guidance/table0..2/{rangeMax,rangeMaxDogfight,timeMax}` | BLK ракеты | Таблицы зоны пуска | Unverified (in files only) | Отделены от дальности ГСН; её правка не доказывает пересчёт таблиц. |
| СПО `range` | Корень сенсора | Дальность предупреждения, м | Verified in game | Уменьшение сократило дальность по авиационной РЛС. Мощный наземный излучатель был слышен дальше этого числа. |
| СПО `{targetRange,mandatoryRecognition,detectTracking,detectLaunch}` | Корень сенсора | Индикация и классификация | Unverified (in files only) | Найдены в файле; проверка дальности их не изолировала. |
| `WeaponSlots/WeaponSlot/WeaponPreset/Weapon/bullets` при `trigger=countermeasures` | BLK самолёта | Количество в пусковой, целое | Verified in game | Увеличенный счётчик появился на HUD, ловушки отстреливались. |

Результат СПО нужно читать с учётом излучателя: первый опыт с молчавшим противником не дал сведений о дальности. По авиационной РЛС уменьшение корневого `range` сдвинуло точку предупреждения ближе. Наземная РЛС всё равно обнаруживалась дальше; мощность передатчика или другие факторы правдоподобны, но формула не проверена. В опыте с РЛС меняли `transivers/*/range`, а шкала `scopeRangeSets` осталась отдельной.
