"""Подсказки пробития по опубликованным формулам WTFTD (ammo_survey.md)."""
import math


_FILLER = ((.65, 1.), (1.6, .93), (2., .90), (3., .85), (4., .75))


def filler_factor(mass, explosive):
    pct = 100 * explosive / mass if mass > 0 else 0
    if pct <= _FILLER[0][0]:
        return 1.
    for (a, fa), (b, fb) in zip(_FILLER, _FILLER[1:]):
        if pct <= b:
            return fa + (fb - fa) * (pct - a) / (b - a)
    return .75


def penetration(shell, distance=0):
    """Миллиметры или None. Скорость на дистанции берётся лишь из явной таблицы игры."""
    damage = shell.block('damage')
    kinetic = damage.block('kinetic') if damage else None
    cumulative = shell.block('cumulativeDamage')
    if cumulative and cumulative.get('armorPower') is not None:
        return float(cumulative.get('armorPower'))
    armor = shell.block('armorpower')
    if armor:
        points = sorted((v[1], v[0]) for k, _, v in armor.params if k.startswith('ArmorPower') and isinstance(v, tuple))
        if points:
            if distance <= points[0][0]:
                return points[0][1]
            for (d0, p0), (d1, p1) in zip(points, points[1:]):
                if distance <= d1:
                    return p0 + (p1 - p0) * (distance - d0) / (d1 - d0)
            return points[-1][1]
    if distance and not shell.block('speedByDistance'):
        return None
    speed = shell.get('speed') or 0
    mass = shell.get('damageMass') or shell.get('mass') or 0
    caliber = shell.get('caliber') or 0
    if kinetic and kinetic.get('lanzOdermattWorkingLength'):
        length = kinetic.get('lanzOdermattWorkingLength')
        diameter = shell.get('damageCaliber') or 0
        density = kinetic.get('lanzOdermattDensity') or 0
        material = str(kinetic.get('lanzOdermattMaterial') or '').lower()
        a, c0, c1 = (.825, 90., -.0849) if 'uran' in material else (.994, 134.5, -.148)
        if min(length, diameter, density, speed) <= 0:
            return None
        return length * a / math.tanh(.283 + .0656 * length / diameter) * math.sqrt(density / 7850) * math.exp(
            -(c0 + c1 * 260) * 260 / (density * (speed / 1000) ** 2))
    if kinetic and kinetic.get('demarrePenetrationK') and min(speed, mass, caliber) > 0:
        return ((speed / 1900) ** (kinetic.get('demarreSpeedPow') or 1.43) *
                mass ** (kinetic.get('demarreMassPow') or .71) /
                (10 * caliber) ** (kinetic.get('demarreCaliberPow') or 1.07) * 100 *
                kinetic.get('demarrePenetrationK') * filler_factor(shell.get('mass') or mass,
                                                                 shell.get('explosiveMass') or 0))
    return None


def tnt_equivalent(shell, explosive_factors=None):
    mass = shell.get('explosiveMass') or 0
    kind = shell.get('explosiveType') or 'TNT'
    return mass * (explosive_factors or {}).get(kind, 1.)
