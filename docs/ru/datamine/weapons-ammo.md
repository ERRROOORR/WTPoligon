> English version: [../../en/datamine/weapons-ammo.md](../../en/datamine/weapons-ammo.md)

# Оружие и боеприпасы

Машина или авиационный пресет ссылается на BLK оружия. Верхний уровень описывает орудие или пусковую; блоки `bullet`, `rocket`, `bomb`, `torpedo` — боеприпасы. Именованные альтернативные блоки снарядов могут соседствовать с обычным `bullet`. Для правки боеприпаса сделайте копию файла оружия через `include` и `@override`, затем направьте на неё машину или пресет. Снаряд из другого орудия требует полного совместимого блока.

| Путь или поле | Смысл | Единицы | Статус |
|---|---|---|---|
| `gameData/weapons/{groundModels_weapons,rocketGuns,bombGuns,torpedoes}/*.blk` | Семейства файлов оружия | — | Unverified (in files only) |
| Оружие `shotFreq`, `bullets`, `reloadTime` | Поля стрельбы и ёмкости | единицы исходника | Unverified (in files only) |
| `bullet/mass`, `speed`, `caliber`, `explosiveMass` | Свойства снаряда | кг, м/с, единицы исходника, кг соответственно | Verified in game |
| `rocket/mass`, `bomb/mass`, `torpedo/mass`, `explosiveMass` | Масса боеприпаса и ВВ | кг | Verified in game |
| `bullet/damage/kinetic/lanzOdermattWorkingLength` | Входная длина сердечника для расчёта пробития | мм | Verified in game |
| `bullet/cumulativeDamage/armorPower` | Пробитие кумулятивной струи | мм | Verified in game |
| `bomb/yield` | Ядерная мощность есть в файлах; правка не проверена | кт | Unverified (in files only) |
| Миссия `bullets0..3`, `bulletsCount0..3` | Выбор именованного снаряда и количество | имя/штуки | Verified in game |
| `rocket/guidance/opticalSeeker/rangeMax` | Проверенный предел захвата ИК-ГСН | м | Verified in game |

В проверенном сценарии у миссии не было меню выбора снаряда. Копии орудий, правки снарядов, ракеты, бомбы и торпеды работали; точные формулы и крайние случаи требуют отдельных подтверждений. Наземный формат ЗУР `cannon` + `bullet{rocket}` при подвеске на самолёт вызывал сбой. Копия, переделанная в `rocketGun` с блоком `rocket`, позволила проверенным ракетам появиться, запуститься и навестись. ЗУР с радиолокационной ГСН и морские ЗУР не проверены; совместимость надо проверять по семействам оружия.

## Карта полей боеприпаса

| Путь или поле | Где находится | Смысл / тип или единицы | Статус | Наблюдение |
|---|---|---|---|---|
| `bullet/damage/kinetic/{demarrePenetrationK,demarreSpeedPow,demarreMassPow,demarreCaliberPow}` | Снаряд в BLK орудия | Входы формулы Демарра | Unverified (in files only) | Расчёты сообщества совпали с отдельными наблюдениями; точная формула игры и редкие виды открыты. |
| `bullet/damage/kinetic/lanzOdermattWorkingLength` | Длинный сердечник | Рабочая длина, мм | Verified in game | Копия с изменённой длиной имела другое пробитие. |
| `bullet/armorpower/ArmorPower*m` | Снаряд | Пробитие по дистанции | Unverified (in files only) | Найдено у нескольких семейств; приоритет и интерполяция не изолированы. |
| `bullet/cumulativeDamage/armorPower` | Кумулятивный снаряд | Пробитие струи, мм | Verified in game | Проверенная правка изменила пробитие. |
| `bullet/{fuseDelay,fuseDelayDist,explodeTreshold}`, `proximityFuse/*` | Снаряд | Время и пороги взрывателя | Unverified (in files only) | Найдены в файлах; локальные правки не проверены. |
| `rocket/{force,timeFire,massEnd,startSpeed,maxSpeed,dragCx}` | BLK ракеты | Тяга, горение, остаточная масса, скорость, сопротивление | Unverified (in files only) | Копия ракеты работала, но отдельные поля динамики не проверены. |
| `bomb/explosionFx` | BLK бомбы | Ключ визуального эффекта | Verified in game | Копия изменила наблюдаемый взрыв. |
| `bomb/yield` | BLK ядерной бомбы | Мощность, кт | Unverified (in files only) | Есть в файлах; в описанных опытах не менялся. |
| `torpedo/{maxSpeedInWater,distToLive,armDistance}` | BLK торпеды | Скорость в м/с и дистанции в м | Unverified (in files only) | Копия торпеды загрузилась; поля хода отдельно не проверены. |
| `damage_model/explosive.blk`, `projectile_types/*.blk` | Общие определения игры | Таблицы взрыва и исходные поля снарядов | Unverified (in files only) | Структура изучена; локальная замена и точные формулы не установлены. |

Пробитие описывается коэффициентами Демарра, параметрами длинного сердечника Ланца–Одерматта, таблицей `armorpower` или `cumulativeDamage/armorPower`. Выбирать способ нужно по наличию полей, а не по одному `bulletType`. Фугасное действие также связано с общими таблицами взрыва. Переносите весь совместимый блок снаряда донора: смена одного `bulletType` может оставить противоречивые поля. Роль `damageMass` у APCR осталась сомнительной.

## Другие исследованные поля

| Путь или поле | Где находится | Смысл / тип или единицы | Статус | Наблюдение |
|---|---|---|---|---|
| `shotFreq`, `reloadTime`, `bullets`, `recoilMultiplier`, `overheat` | BLK орудия или пусковой | Темп, перезарядка, ёмкость, отдача и нагрев | Unverified (in files only) | Найдены в файлах; каждое поле в описанных опытах не изолировано. |
| `commonWeapons/Weapon[n]/blk` | BLK наземной машины | Ссылка на файл орудия | Verified in game | Перенаправление после переноса блоков модификаций выбрало копию орудия. |
| Пресет `Weapon[n]/blk` | BLK авиационного пресета | Ссылка на файл оружия | Verified in game | Копия пресета выбрала копию авиационного оружия. |
| `bullet/{mass,speed,caliber,damageCaliber,damageMass,explosiveMass,explosiveType}` | Блок снаряда | Размеры, масса и заряд | Unverified (in files only) | Отдельные правки массы и заряда работали; смысл APCR `damageMass` остаётся спорным. |
| `rocket/{mass,massEnd,force,timeFire,force1,timeFire1}`, `guidance/tableN` | Блок ракеты | Топливо, ступени тяги и таблицы наведения | Unverified (in files only) | Поля связаны в исходных данных; изменение одного не доказывает автоматический пересчёт других. |
| `bomb/{nearArmorPower,midArmorPower,farArmorPower,explodeArmorPower}` | Блок бомбы | Параметры пробития удара и взрыва | Unverified (in files only) | Найдены в семействах бомб; расчёт не изолирован. |
| `torpedo/{pressureDamage,detonationRadius,detonationDepth,diveDepth}` | Блок торпеды | Ударная волна и глубина | Unverified (in files only) | Есть в файлах; действие локальных правок не изолировано. |

