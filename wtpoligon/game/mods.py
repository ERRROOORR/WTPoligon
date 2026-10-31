"""Модификации машины: что можно перенести в копию под своим именем и как (docs/research/modifications.md).

Правила (данные игры 2.59.0.86 + проверки в игре 24.10, launch.md §7–9):
  - эффект-БЛОК в файле машины (modifications/<мод>/effects/<блок>) — переносим: блок модификации ложится в копию
    (подтверждено в игре: commonWeapons с дымовым гранатомётом, nightVision с gunnerThermal);
  - модификация с invertEnableLogic — её эффекты действуют, когда она НЕ установлена (штраф стоковой машины, «без
    навесной брони»); файл машины уже описывает установленное состояние → не переносим;
  - group — группировка в интерфейсе; альтернативы — только несколько модификаций одной группы на один и тот же
    блок (варианты вооружения A-26 и т.п.) → по выбору; цепочка reqModification — ступени, берётся верхняя;
  - эффект-ПАРАМЕТР (в файле машины или в общем config/modifications.blk) — у копии не работает даже вписанный
    в файл (7-й круг) → не переносим, показываем пользователю как потерю.
"""
from . import blk as B


def global_mods(char_vromfs):
    """Блок modifications из char.vromfs/config/modifications.blk."""
    root = B.BinaryReader.for_vromfs(char_vromfs).parse(char_vromfs.files['config/modifications.blk'])
    return root.block('modifications') or root


def classify(unit_blk, gmods):
    """[{name, invert, group, blocks, unit_params, global_params, kind}] по модификациям машины.

    kind: 'block' — переносим; 'alternative' — одна из нескольких модификаций группы на один блок (по выбору);
          'superseded' — нижняя ступень цепочки reqModification; 'stock_penalty' — инверсия;
          'lost' — только параметры (у копии не работают); 'none' — эффектов нет (снаряды и т.п.)."""
    out = []
    for m in (unit_blk.block('modifications').blocks if unit_blk.block('modifications') else []):
        g = gmods.block(m.name)
        eff = m.block('effects')
        geff = g.block('effects') if g else None
        out.append({
            'name': m.name,
            'invert': bool(g and g.get('invertEnableLogic')),
            'group': g.get('group') if g else None,
            'requires': [p[2] for p in (g.params if g else []) if p[0] == 'reqModification'],
            'blocks': [b.name for b in (eff.blocks if eff else [])],
            'unit_params': [p[0] for p in (eff.params if eff else [])],
            'global_params': [p[0] for p in (geff.params if geff else []) if p[0] not in ('rcostAddParam', 'rcostMul')],
        })
    # group — группировка в интерфейсе, а не «выбери одно»: у 979 из ~1000 случаев модификация в группе одна
    # (дымовые гранаты smoke_mod, тепловизор NVS). Альтернативы — только несколько модификаций одной группы,
    # меняющих один и тот же блок (30 машин: пушки A-26 и т.п.). Если одна требует другую (reqModification) —
    # это ступени: нижняя ступень вытесняется верхней.
    for rec in out:
        peers = [o for o in out if o is not rec and o['group'] and o['group'] == rec['group']
                 and set(o['blocks']) & set(rec['blocks'])]
        if rec['invert']:
            rec['kind'] = 'stock_penalty'
        elif rec['blocks'] and not peers:
            rec['kind'] = 'block'
        elif rec['blocks'] and any(rec['name'] in o['requires'] for o in peers):
            rec['kind'] = 'superseded'
        elif rec['blocks'] and peers and all(o['name'] in rec['requires'] or rec['name'] in o['requires']
                                             for o in peers):
            rec['kind'] = 'block'
        elif rec['blocks']:
            rec['kind'] = 'alternative'
        elif rec['unit_params'] or rec['global_params']:
            rec['kind'] = 'lost'
        else:
            rec['kind'] = 'none'
    return out


def bake_blocks(unit_blk, gmods, chosen=()):
    """[(имя блока, блок, [модификации])] для переноса в копию.

    chosen — модификации из групп, выбранные пользователем (по одной на группу).
    Блок есть в стоке → блок модификации заменяет его целиком (так устроены 596 из 622 танковых commonWeapons:
    блок модификации повторяет весь сток + своё); при нескольких модификациях — последняя.
    Блока в стоке нет → блоки нескольких модификаций объединяются (корабли: damagePartsOverride от разных
    модификаций — про разные отсеки)."""
    want = {r['name'] for r in classify(unit_blk, gmods)
            if r['kind'] == 'block' or (r['kind'] == 'alternative' and r['name'] in chosen)}
    result = {}
    for m in (unit_blk.block('modifications').blocks if unit_blk.block('modifications') else []):
        if m.name not in want:
            continue
        eff = m.block('effects')
        for b in (eff.blocks if eff else []):
            if unit_blk.block(b.name) is not None or b.name not in result:
                result[b.name] = (b.name, B._clone(b), [m.name])
            else:
                name, merged, srcs = result[b.name]
                merged.params += list(b.params)
                merged.blocks += [B._clone(x) for x in b.blocks]
                srcs.append(m.name)
    return list(result.values())


def companion_params(unit_blk, gmods, chosen=()):
    """Параметры из общего справочника у модификаций, чьи блоки переносим (состояние «установлена»).

    9-й круг: блок nightVision у Ми-28НМ перенесён, а ПНВ не работает — у авиации ночной режим, видимо,
    включается параметром enableNightVision той же модификации. Только параметры уже переносимых модификаций;
    параметры отдельно от блоков у копии не работают (7-й круг)."""
    src = {s for _, _, srcs in bake_blocks(unit_blk, gmods, chosen) for s in srcs}
    out, seen = [], set()
    for m in (unit_blk.block('modifications').blocks if unit_blk.block('modifications') else []):
        g = gmods.block(m.name)
        if m.name not in src or not g or not g.block('effects'):
            continue
        for k, t, v in g.block('effects').params:
            if k not in ('rcostAddParam', 'rcostMul') and k not in seen:
                seen.add(k)
                out.append((k, t, v, m.name))
    return out


def bake_text(unit_blk, gmods, chosen=()):
    """Строки правки: для каждого переносимого блока — @delete стокового (если есть) + блок модификации;
    затем параметры этих же модификаций из общего справочника (параметр есть → @override, нет → добавить)."""
    lines = []
    for name, block, srcs in bake_blocks(unit_blk, gmods, chosen):
        lines.append('// %s ← модификации: %s (modifications.md)' % (name, ', '.join(srcs)))
        if unit_blk.block(name) is not None:
            lines.append('"@delete:%s"{}' % name)
        lines.append(B.to_text(B.Block(None, blocks=[block])).rstrip('\n'))  # to_text пишет содержимое без имени
    stock = {k: t for k, t, _ in unit_blk.params}
    for k, t, v, mod in companion_params(unit_blk, gmods, chosen):
        if k in stock and stock[k] != t:
            continue  # другой тип в стоке — @override не применится (override_format.md §3)
        # комментарий — отдельной строкой: хвост «  // …» после значения без кавычек Dagor может прочитать
        # как часть значения (пробелы до //), а модель их срезает и ошибку не покажет
        lines.append('// %s ← модификация %s' % (k, mod))
        lines.append('%s:%s=%s' % ('"@override:%s"' % k if k in stock else k, t, B.fmt_value(t, v)))
    return '\n'.join(lines) + '\n' if lines else ''


def lost_equipment(unit_blk, gmods):
    """Модификации, которые у копии под своим именем не будут работать (для предупреждения в программе)."""
    return [r['name'] for r in classify(unit_blk, gmods) if r['kind'] == 'lost']
