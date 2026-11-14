"""Рецепт ядерного заряда, проверенный в миссиях 73, 77 и 78."""
import copy

from ..game import blk as B


def _set(block, key, typ, value):
    block.params = [(k, t, v) for k, t, v in block.params if k != key]
    block.params.append((key, typ, value))


def apply(tree, shell, yield_kt, rocket_sample=None):
    if not 0 < float(yield_kt) <= 100000:
        raise ValueError('мощность ядерного заряда должна быть от 0 до 100000 кт')
    root = copy.deepcopy(tree)
    named = root.block(shell)
    if named is None:
        raise ValueError('нет боеприпаса ' + shell)
    projectile = (named if named.name in ('bullet', 'rocket', 'bomb') else
                  named.block('bullet') or named.block('rocket') or named.block('bomb'))
    if projectile is None:
        raise ValueError('нет блока боеприпаса ' + shell)
    if projectile.name == 'bullet' and projectile.block('rocket') is None:
        sample = next((b.block('bullet') for b in root.blocks if b.block('bullet') and
                       b.block('bullet').block('rocket')), None)
        sample = sample or rocket_sample
        if sample:
            projectile = copy.deepcopy(sample)
            rocket = projectile.block('rocket')
            stock = named.block('bullet')
            if stock:
                for field in ('mass', 'caliber'):
                    if stock.get(field) is not None:
                        _set(rocket, field, 'r', float(stock.get(field)))
                if stock.get('speed') is not None:
                    _set(rocket, 'startSpeed', 'r', float(stock.get('speed')))
                    _set(rocket, 'endSpeed', 'r', float(stock.get('speed')))
            rocket.blocks = [b for b in rocket.blocks if b.name != 'guidance']
            rocket.params = [(k, t, v) for k, t, v in rocket.params if k not in
                             ('guidanceType', 'autoAimingMaxAngle', 'maxDeltaAngle', 'visRotationFreqX')]
        else:
            projectile = B.Block('bullet', blocks=[B.Block('rocket')])
            rocket = projectile.block('rocket')
        if named is projectile or named.name == 'bullet':
            root.blocks = [projectile if b is named else b for b in root.blocks]
        else:
            named.blocks = [projectile if b.name == 'bullet' else b for b in named.blocks]
        projectile = rocket
    elif projectile.name == 'bullet':
        projectile = projectile.block('rocket')
    _set(projectile, 'yield', 'r', float(yield_kt))
    _set(projectile, 'explosiveType', 't', 'tnt')
    _set(projectile, 'explosiveMass', 'r', 20000.0)
    if projectile.block('pressureDamage') is None:
        projectile.blocks.append(B.Block('pressureDamage', [('damageType', 't', 'pressure')]))
    return root
