"""Ограничения перед сборкой боекомплекта."""
import math


def check(ammo, available=()):
    problems = []
    if len(ammo.slots) != 4:
        problems.append('у боекомплекта должно быть четыре ячейки')
    if ammo.capacity < 0:
        problems.append('вместимость не может быть отрицательной')
    if sum(s.count for s in ammo.slots) > ammo.capacity and ammo.capacity:
        problems.append('заряжено больше вместимости')
    for i, slot in enumerate(ammo.slots, 1):
        if slot.count < 0 or (slot.count and not slot.shell):
            problems.append('ячейка %d: снаряд и количество не согласованы' % i)
        if slot.shell and available and slot.shell not in available:
            problems.append('ячейка %d: снаряд отсутствует в орудии' % i)
    for edit in ammo.edits:
        if isinstance(edit.value, (int, float)) and not math.isfinite(edit.value):
            problems.append('%s: число не конечно' % edit.path)
        if edit.path.split('/')[-1] in ('mass', 'explosiveMass', 'speed', 'caliber') and edit.value < 0:
            problems.append('%s: значение меньше нуля' % edit.path)
    return problems
