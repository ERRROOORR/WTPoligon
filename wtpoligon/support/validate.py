"""Проверка выбора вызываемой техники."""


def check(support, vehicles, library=()):
    known = {v['name']: v for v in vehicles}
    saved = {x['id']: x for x in library}
    errors, kinds = [], {}
    air = 0
    for entry in support.entries:
        v = known.get(entry.vehicle)
        if not v:
            errors.append('нет вызываемой машины %s' % entry.vehicle)
            continue
        actual = 'air' if v['kind'] in ('air', 'heli') else 'ground'
        if actual != entry.kind or v['kind'] == 'ship':
            errors.append('неверный вид вызова %s' % entry.vehicle)
        key = entry.library_id or entry.vehicle
        if key in kinds and kinds[key] != entry.kind:
            errors.append('машина вызвана двумя способами: %s' % entry.vehicle)
        kinds[key] = entry.kind
        if entry.library_id and entry.library_id not in saved:
            errors.append('нет своей техники %s' % entry.library_id)
        if not isinstance(entry.count, int) or not 1 <= entry.count <= 99:
            errors.append('количество должно быть от 1 до 99')
        if entry.kind == 'air':
            air += 1
            if entry.count != 1:
                errors.append('авиация вызывается по одной машине')
    if air > 1:
        errors.append('можно выбрать только один авиационный вызов')
    return errors
