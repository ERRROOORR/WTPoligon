"""Сохранённые конфигурации техники в папке данных приложения."""
import json
import os
import re
import logging
import uuid

LOG = logging.getLogger('wtpoligon.library')


def directory(root):
    return os.path.join(root, 'library')


def list_items(root):
    result = []
    path = directory(root)
    if not os.path.isdir(path):
        return result
    for name in os.listdir(path):
        if not re.fullmatch(r'[0-9a-f]{32}\.json', name):
            continue
        try:
            with open(os.path.join(path, name), encoding='utf-8') as stream:
                data = json.load(stream)
            if data.get('schema_version') == 1 and data.get('id') == name[:-5]:
                result.append(data)
            else:
                LOG.warning('Своя техника %s пропущена: schema_version=%r id=%r', name, data.get('schema_version'),
                            data.get('id'))
        except (OSError, ValueError) as exc:
            LOG.warning('Своя техника %s не читается: %s: %s', name, type(exc).__name__, exc)
            continue
    return sorted(result, key=lambda x: x['name'].casefold())


def get(root, item_id):
    if not re.fullmatch(r'[0-9a-f]{32}', item_id):
        raise ValueError('неверный идентификатор своей техники')
    with open(os.path.join(directory(root), item_id + '.json'), encoding='utf-8') as stream:
        data = json.load(stream)
    if data.get('schema_version') != 1 or data.get('id') != item_id:
        raise ValueError('неверный файл своей техники')
    return data


def save(root, name, vehicle, *, loadout=None, stats=None, ammo=None, scenario=None, support=None,
         item_id=None):
    name = name.strip()
    if not name or len(name) > 80:
        raise ValueError('имя должно содержать от 1 до 80 символов')
    item_id = item_id or uuid.uuid4().hex
    if not re.fullmatch(r'[0-9a-f]{32}', item_id):
        raise ValueError('неверный идентификатор своей техники')
    data = {'schema_version': 1, 'id': item_id, 'name': name, 'vehicle': vehicle['name'],
            'kind': vehicle['kind'], 'loadout': loadout, 'stats': stats, 'ammo': ammo,
            'scenario': scenario, 'support': support}
    path = directory(root)
    os.makedirs(path, exist_ok=True)
    target = os.path.join(path, item_id + '.json')
    with open(target + '.tmp', 'w', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
    os.replace(target + '.tmp', target)
    return data


def delete(root, item_id):
    get(root, item_id)
    os.remove(os.path.join(directory(root), item_id + '.json'))
