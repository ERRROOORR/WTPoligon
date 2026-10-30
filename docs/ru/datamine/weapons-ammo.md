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
| `rocket/opticalSeeker/rangeMax` | Проверенный предел захвата ИК-ГСН | м | Verified in game |

В проверенном сценарии у миссии не было меню выбора снаряда. Копии орудий, правки снарядов, ракеты, бомбы и торпеды работали; точные формулы и крайние случаи требуют отдельных подтверждений. Наземный формат ЗУР `cannon` + `bullet{rocket}` при подвеске на самолёт вызывал сбой. Копия, переделанная в `rocketGun` с блоком `rocket`, позволила проверенным ракетам появиться, запуститься и навестись. ЗУР с радиолокационной ГСН и морские ЗУР не проверены; совместимость надо проверять по семействам оружия.

