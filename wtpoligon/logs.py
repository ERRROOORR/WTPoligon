"""Сбор логов для разбора проблем тестеров: свежие логи игры (расшифрованные), манифесты и настройки программы.

Архив кладётся в папку `logs` рядом с программой (где `run.bat`), чтобы тестер мог сразу его отправить.
"""
import glob
import json
import os
import platform
import sys
import time
import zipfile

from . import paths as P

PROGRAM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_LOGS = 5   # сколько последних запусков игры брать


def _version():
    try:
        with open(os.path.join(PROGRAM_DIR, 'VERSION'), encoding='utf-8') as f:
            return f.read().strip()
    except OSError:
        return '?'


def collect(game_dir, app_root=None, out_dir=None, count=GAME_LOGS):
    """Собрать архив; вернуть его путь. Логи игры расшифровываются (`.clog` → `.log`)."""
    from .game import clog
    app_root = app_root or P.app_root()
    out_dir = out_dir or os.path.join(PROGRAM_DIR, 'logs')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'wtpoligon_logs_%s.zip' % time.strftime('%Y%m%d_%H%M%S'))
    info = {'version': _version(), 'python': sys.version, 'os': platform.platform(), 'game_dir': game_dir,
            'collected': time.strftime('%Y-%m-%d %H:%M:%S'), 'game_logs': [], 'errors': []}
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        logs = os.path.join(game_dir or '', '.game_logs')
        files = sorted(glob.glob(os.path.join(logs, '*.clog')), key=os.path.getmtime, reverse=True)[:count]
        key = clog.key_for_dir(logs) if files else None
        for clog_path in files:
            name = os.path.basename(clog_path)[:-5] + '.log'
            try:
                with open(clog_path, 'rb') as f:
                    text = clog.decrypt(f.read(), key).decode('utf-8', 'replace')
                z.writestr('game_logs/' + name, text)
                info['game_logs'].append(name)
            except Exception as e:  # noqa: BLE001 — один битый лог не должен ломать весь сбор
                info['errors'].append('%s: %s' % (name, e))
        # что программа записала в игру (манифесты) и её настройки — без кэша и бэкапов
        for pattern in ('installs/*/*.json', '*.json'):
            for f in glob.glob(os.path.join(app_root, pattern)):
                z.write(f, 'program/' + os.path.relpath(f, app_root).replace('\\', '/'))
        missions = os.path.join(game_dir or '', 'UserMissions', 'WTPoligon5')
        if os.path.isdir(missions):
            info['missions'] = sorted(os.listdir(missions))
        z.writestr('info.json', json.dumps(info, ensure_ascii=False, indent=2))
    return path
