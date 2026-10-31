"""Запись в игру (docs/architecture.md §7): единственный модуль, который пишет на диск игры.

Правила (ТЗ §10), проверены генератором тестов с 10.10:
  - чужой файл (нет в манифесте) или наш, но изменённый после записи, не перезаписываем — отказ до первой записи;
  - свой файл перед перезаписью копируем в бэкап; манифест (пути и SHA-256) — после каждого файла;
  - откат удаляет только свои файлы с неизменным содержимым.
Программа (install/uninstall ниже) дополнительно пишет только файлы wtp5_* в content/pkg_local/gameData и
в свою папку миссий; каждое применение (одна машина) — свой манифест installs/<id>/manifest.json.
"""
import datetime as dt
import hashlib
import json
import os
import re
import shutil

from .mission import PREFIX

MISSION_DIR = 'UserMissions/WTPoligon5'
PKG_DIR = 'content/pkg_local/gameData/'
INSTALLS = 'installs'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(app_dir):
    p = os.path.join(app_dir, 'manifest.json')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    return {'files': {}}


def save_manifest(app_dir, man):
    os.makedirs(app_dir, exist_ok=True)
    tmp = os.path.join(app_dir, 'manifest.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(app_dir, 'manifest.json'))


def adopt_exact(game_dir, app_dir, rel, expected: bytes, dry_run=False):
    """Take over a former project file only when it matches the generator byte for byte.

    Preserve the original as a separate restore target. A later --remove restores it,
    rather than deleting a file that existed before this test round.
    """
    man = load_manifest(app_dir)
    if rel in man['files']:
        if rel not in man.get('restores', {}):
            return False, man, ['учёт исходного файла отсутствует, не трогаю: ' + rel]
        return True, man, []
    full = os.path.join(game_dir, rel)
    if not os.path.isfile(full):
        return False, man, ['исходного файла нет, не создаю заново: ' + rel]
    with open(full, 'rb') as f:
        actual = f.read()
    if actual != expected:
        return False, man, ['исходный файл не совпадает побайтно с генератором миссии 11: ' + rel]
    backup_rel = os.path.join('originals', rel)
    backup = os.path.join(app_dir, backup_rel)
    if os.path.exists(backup):
        with open(backup, 'rb') as f:
            if f.read() != expected:
                return False, man, ['сохранённый оригинал отличается, не трогаю: ' + backup]
    elif not dry_run:
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.copy2(full, backup)
    man.setdefault('restores', {})[rel] = {'hash': sha(expected), 'backup': backup_rel}
    man['files'][rel] = sha(expected)
    if not dry_run:
        save_manifest(app_dir, man)
    return True, man, ['приму под учёт после точной сверки и сохраню оригинал: ' + rel]


def adopt_original(game_dir, app_dir, rel, dry_run=False):
    """Preserve an arbitrary existing third-party file for a reversible replacement."""
    man = load_manifest(app_dir)
    if rel in man['files']:
        if rel not in man.get('restores', {}):
            return False, man, ['учёт исходного файла отсутствует, не трогаю: ' + rel]
        return True, man, []
    full = os.path.join(game_dir, rel)
    if not os.path.isfile(full):
        return False, man, ['исходного файла нет, не трогаю: ' + rel]
    with open(full, 'rb') as f:
        original = f.read()
    backup_rel = os.path.join('originals', rel)
    backup = os.path.join(app_dir, backup_rel)
    if os.path.exists(backup):
        with open(backup, 'rb') as f:
            if f.read() != original:
                return False, man, ['сохранённый оригинал отличается, не трогаю: ' + backup]
    elif not dry_run:
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.copy2(full, backup)
    man.setdefault('restores', {})[rel] = {'hash': sha(original), 'backup': backup_rel}
    man['files'][rel] = sha(original)
    if not dry_run:
        save_manifest(app_dir, man)
    return True, man, ['сохраню исходный файл для отката: ' + rel]


def restore_original(app_dir, full, record):
    backup = os.path.join(app_dir, record['backup'])
    if not os.path.isfile(backup):
        return False, 'нет сохранённого оригинала: ' + backup
    with open(backup, 'rb') as f:
        original = f.read()
    if sha(original) != record['hash']:
        return False, 'сохранённый оригинал изменён: ' + backup
    tmp = full + '.wtp5_restore_tmp'
    if os.path.exists(tmp):
        return False, 'временный файл восстановления уже существует: ' + tmp
    with open(tmp, 'wb') as f:
        f.write(original)
    os.replace(tmp, full)
    return True, ''


def write(game_dir, items, app_dir, dry_run=False, manifest=None):
    """Записать набор [(путь от папки игры, текст)] по манифесту app_dir: чужой или изменённый после записи файл —
    отказ до первой записи; свой старый — в бэкап; свои файлы, выпавшие из набора, — убрать (через бэкап)."""
    man = manifest if manifest is not None else load_manifest(app_dir)
    # 1. проверка всех путей до первой записи
    blocked = []
    for rel, _text in items:
        full = os.path.join(game_dir, rel)
        if os.path.exists(full):
            rec = man['files'].get(rel)
            with open(full, 'rb') as f:
                cur = sha(f.read())
            if rec is None:
                blocked.append('чужой файл, не трогаю: ' + rel)
            elif rec != cur:
                blocked.append('наш файл изменён кем-то после записи, не трогаю: ' + rel)
    if blocked:
        return False, blocked
    report = []
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    for rel, text in items:
        full = os.path.join(game_dir, rel)
        data = text if isinstance(text, bytes) else text.encode('utf-8')
        if os.path.exists(full):
            with open(full, 'rb') as f:
                old = f.read()
            if old == data:
                report.append('без изменений: ' + rel)
                continue
            if not dry_run:
                bak = os.path.join(app_dir, 'backups', stamp, rel)
                os.makedirs(os.path.dirname(bak), exist_ok=True)
                shutil.copy2(full, bak)
            report.append('обновлю (старое — в бэкап): ' + rel)
        else:
            report.append('создам: ' + rel)
        if not dry_run:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'wb') as f:
                f.write(data)
            man['files'][rel] = sha(data)
            man.setdefault('sizes', {})[rel] = len(data)
            save_manifest(app_dir, man)
    # свои файлы, которых больше нет в наборе (например, заменили машину в пункте), — убрать через бэкап
    wanted = {rel for rel, _ in items}
    for rel, h in list(man['files'].items()):
        if rel in wanted:
            continue
        full = os.path.join(game_dir, rel)
        if os.path.exists(full):
            with open(full, 'rb') as f:
                cur = f.read()
            if sha(cur) != h:
                report.append('выпал из набора, но изменён после записи, оставляю: ' + rel)
                continue
            restore = man.get('restores', {}).get(rel)
            report.append(('восстановлю исходный файл: ' if restore else
                           'уберу (выпал из набора, копия — в бэкап): ') + rel)
            if dry_run:
                continue
            if restore:
                ok, reason = restore_original(app_dir, full, restore)
                if not ok:
                    report.append(reason)
                    continue
            else:
                bak = os.path.join(app_dir, 'backups', stamp, rel)
                os.makedirs(os.path.dirname(bak), exist_ok=True)
                shutil.copy2(full, bak)
                os.remove(full)
        if not dry_run:
            del man['files'][rel]
            man.get('sizes', {}).pop(rel, None)
            man.get('restores', {}).pop(rel, None)
            save_manifest(app_dir, man)
    return True, report


def remove(game_dir, app_dir, dry_run=False, mission_dir=None):
    """Откат по манифесту: удалить свои неизменённые файлы, вернуть принятые под учёт оригиналы.
    mission_dir — папка своих миссий (относительно игры): если опустела, убрать и её."""
    man = load_manifest(app_dir)
    report = []
    for rel, h in list(man['files'].items()):
        full = os.path.join(game_dir, rel)
        if not os.path.exists(full):
            report.append('уже нет: ' + rel)
        else:
            with open(full, 'rb') as f:
                cur = sha(f.read())
            if cur != h:
                report.append('изменён после записи, оставляю: ' + rel)
                continue
            restore = man.get('restores', {}).get(rel)
            if restore:
                if not dry_run:
                    ok, reason = restore_original(app_dir, full, restore)
                    if not ok:
                        report.append(reason)
                        continue
                report.append(('восстановлю исходный файл: ' if dry_run else
                               'восстановлен исходный файл: ') + rel)
            else:
                if not dry_run:
                    os.remove(full)
                report.append('удалю: ' + rel if dry_run else 'удалён: ' + rel)
        if not dry_run:
            del man['files'][rel]
            man.get('sizes', {}).pop(rel, None)
            man.get('restores', {}).pop(rel, None)
            save_manifest(app_dir, man)
    if not dry_run and mission_dir:
        d = os.path.join(game_dir, mission_dir)
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    return report


# ---------------------------------------------------------------- применения программы

def check_paths(items):
    """Пути набора, которые программе писать нельзя (ТЗ §10): только wtp5_* в pkg_local/gameData и свои миссии
    (wtp5_*.blk, usr_wtp5_*.csv) в MISSION_DIR; без '..', абсолютных путей и повторов."""
    bad, seen = [], set()
    for rel, _text in items:
        norm = rel.replace('\\', '/')
        parts = norm.split('/')
        name = parts[-1]
        if norm != rel or os.path.isabs(rel) or '..' in parts or '' in parts or ':' in norm:
            bad.append('недопустимый путь: ' + rel)
        elif norm.lower() in seen:
            bad.append('путь повторяется: ' + rel)
        elif norm.startswith(PKG_DIR):
            if not (name.startswith(PREFIX) and name.endswith('.blk')):
                bad.append('в pkg_local пишу только свои копии %s*.blk: %s' % (PREFIX, rel))
        elif norm.startswith(MISSION_DIR + '/') and len(parts) == len(MISSION_DIR.split('/')) + 1:
            if not ((name.startswith(PREFIX) and name.endswith('.blk'))
                    or (name.startswith('usr_' + PREFIX) and name.endswith('.csv'))):
                bad.append('в папке миссий пишу только свои миссии %s*: %s' % (PREFIX, rel))
        else:
            bad.append('вне pkg_local/gameData и %s: %s' % (MISSION_DIR, rel))
        seen.add(norm.lower())
    return bad


def app_id_ok(app_id):
    return bool(re.fullmatch(r'[a-z0-9][a-z0-9_.-]*', app_id or ''))


def _app_dir(app_root, app_id):
    if not app_id_ok(app_id):
        raise ValueError('недопустимое имя применения: %r' % app_id)
    return os.path.join(app_root, INSTALLS, app_id)


def installed(app_root):
    """{id применения: манифест} всех применений программы."""
    d = os.path.join(app_root, INSTALLS)
    out = {}
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if os.path.isfile(os.path.join(d, name, 'manifest.json')):
            out[name] = load_manifest(os.path.join(d, name))
    return out


def status(app_root):
    """Что записано программой: [(id применения, meta, {состояние: число файлов})], состояние — «на месте»,
    «нет файла», «изменён после записи» (сверка SHA-256 с манифестом)."""
    out = []
    for app_id, man in installed(app_root).items():
        meta = man.get('meta', {})
        state = {}
        for rel, h in man['files'].items():
            full = os.path.join(meta.get('game_dir', ''), rel)
            if not os.path.isfile(full):
                key = 'нет файла'
            else:
                with open(full, 'rb') as f:
                    key = 'на месте' if sha(f.read()) == h else 'изменён после записи'
            state[key] = state.get(key, 0) + 1
        out.append((app_id, meta, state))
    return out


def install(game_dir, app_root, app_id, items, meta=None, dry_run=False):
    """Записать набор файлов одного применения. (ok, отчёт). Повторная установка того же id обновляет набор
    (файлы, выпавшие из набора, убираются). Файл другого применения — отказ."""
    bad = check_paths(items)
    app_dir = _app_dir(app_root, app_id)
    for other, man in installed(app_root).items():
        if other != app_id:
            bad += ['файл уже записан применением %s: %s' % (other, rel) for rel, _ in items if rel in man['files']]
    if bad:
        return False, bad
    ok, report = write(game_dir, items, app_dir, dry_run)
    if ok and not dry_run:
        man = load_manifest(app_dir)
        man['meta'] = dict(meta or {}, installed=dt.datetime.now().isoformat(timespec='seconds'))
        save_manifest(app_dir, man)
    return ok, report


def uninstall(game_dir, app_root, app_id, dry_run=False):
    """Откат одного применения; пустой манифест удаляется вместе с папкой применения."""
    app_dir = _app_dir(app_root, app_id)
    if not os.path.isfile(os.path.join(app_dir, 'manifest.json')):
        return ['нет такого применения: ' + app_id]
    report = remove(game_dir, app_dir, dry_run, mission_dir=MISSION_DIR)
    if not dry_run and not load_manifest(app_dir)['files']:
        os.remove(os.path.join(app_dir, 'manifest.json'))
        if os.path.isdir(os.path.join(app_dir, 'backups')):
            report.append('бэкапы оставлены: ' + os.path.join(app_dir, 'backups'))
        else:
            os.rmdir(app_dir)
    return report
