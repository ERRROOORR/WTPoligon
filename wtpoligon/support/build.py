"""Правка блока вызова в копии машины."""
from ..game import blk as B


def speed(vehicle):
    name = vehicle['name'].lower()
    tags = vehicle.get('tags') or []
    if 'uav' in name or 'drone' in name or any('ucav' in tag or 'uav' in tag for tag in tags):
        return 150
    if vehicle['kind'] == 'heli' or any(token in name for token in
                                       ('p_51', 'bf_109', 'spitfire', 'a6m', 'yak_', 'la_5', 'fw_190')):
        return 300
    return 450


def patch(support, vehicles, classes=None, stock_unit=None):
    known = {v['name']: v for v in vehicles}
    classes = classes or {}
    air = next((e for e in support.entries if e.kind == 'air'), None)
    lines = []
    if stock_unit is not None and stock_unit.block('supportPlane'):
        lines.append('"@delete:supportPlane"{}')
    if stock_unit is not None and stock_unit.block('supportPlanes'):
        lines.append('"@delete:supportPlanes"{}')
    if air:
        v = known[air.vehicle]
        lines += ['supportPlane{', '  supportPlaneClass:t=%s' % B.quote(classes.get(air.library_id, air.vehicle)),
                  '  planeStartSpeed:r=%s' % float(speed(v)), '}']
    ground = [e for e in support.entries if e.kind == 'ground']
    if ground:
        lines.append('supportPlanes{')
        for e in ground:
            cls = classes.get(e.library_id, e.vehicle)
            for _ in range(e.count):
                lines += ['  plane{', '    class:t=%s' % B.quote('tankModels/' + cls),
                          '    isSlave:b=true', '    count:i=1', '  }']
        lines.append('}')
    return '\n'.join(lines) + '\n'
