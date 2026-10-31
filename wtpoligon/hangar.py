"""Есть ли машина в ангаре пользователя.

По файлам игры это не определить: владение — данные аккаунта на сервере (launch.md §5: «решение — всегда своё
имя, иначе спрашивать пользователя»). Поэтому отметку ставит пользователь: hangar.json в папке программы,
{"owned": [...], "not_owned": [...]}. Без отметки машина считается не из ангара — запускается копия wtp5_*
(настоящее имя машины не из ангара игра не пускает: «Hero in userMission must be a unit owned by player»).
"""
import json
import os

FILE = 'hangar.json'


def load(root):
    """{имя в нижнем регистре: True (в ангаре) | False (нет)}."""
    try:
        with open(os.path.join(root, FILE), encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {n.lower(): False for n in data.get('not_owned', [])}
    out.update({n.lower(): True for n in data.get('owned', [])})
    return out


def status(marks, name):
    """True / False / None (не отмечено)."""
    return marks.get(name.lower())


def mark(root, names, owned):
    """Отметить машины: owned=True — в ангаре, False — нет, None — снять отметку."""
    marks = load(root)
    for n in names:
        if owned is None:
            marks.pop(n.lower(), None)
        else:
            marks[n.lower()] = owned
    os.makedirs(root, exist_ok=True)
    tmp = os.path.join(root, FILE + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'owned': sorted(k for k, v in marks.items() if v),
                   'not_owned': sorted(k for k, v in marks.items() if not v)}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(root, FILE))
    return marks
