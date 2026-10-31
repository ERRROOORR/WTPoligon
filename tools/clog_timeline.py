"""Хронология: применения WT Poligon 4.7 (манифесты бэкапов) + события игры из расшифрованных логов.

Вход: cache/logs/*.log (см. wtlib/clog.py), %LOCALAPPDATA%/WTPoligon/backups/*/manifest.json.
Выход: cache/timeline.txt — по времени (местное), строки логов игры отфильтрованы по нашим файлам и ошибкам.
"""
import datetime as dt
import glob
import json
import os
import re
import sys

LOGS = os.path.join('cache', 'logs')
BACKUPS = os.path.expandvars(r'%LOCALAPPDATA%\WTPoligon\backups')

# что считаем относящимся к делу
RELEVANT = re.compile(
    r'wtp_|WTPoligon|userVehicles|pkg_local/gameData|Ask3lad|f_15c_aim9x|Fuji_suspension|'
    r'cannot find param|different types|syntax error|BLK (?:invalid|error)|failed to load|including binary file|create_unit_entity\(\) failed|'
    r'owned by|testFlight|Hero in|hero.*mission|crash|exception|ASSERT|fatal', re.I)
NOISE = re.compile(r'unit delayed status changed|hud_mp_ui_message|killed by:|Death report|died\. Last damaged|'
                   r'sending unit respawn|UnitRespawn received|statsd_on_login|collRes|skip duplicate apex|'
                   r'fx: loading: land_crash|Failed to load user skin|crashpad|TextKillReport|\[RMBL\]|\[SNDSYS\]|'
                   r'on_controlled_hero_changed|unit ecs init')
STAMP = re.compile(r'^\s*(\d+(?:\.\d+)?|\d+:\d\d(?::\d\d)?\.\d+)\s')
START = re.compile(r'started at \w+ (\w+ +\d+ \d+:\d+:\d+ \d+) UTC')


def rel_seconds(s):
    parts = s.split(':')
    v = 0.0
    for p in parts:
        v = v * 60 + float(p)
    return v


def utc_offset():
    now = dt.datetime.now(dt.timezone.utc)
    return now.astimezone().replace(tzinfo=None) - now.replace(tzinfo=None)


def game_events():
    off = utc_offset()
    for path in sorted(glob.glob(os.path.join(LOGS, '*.log'))):
        with open(path, encoding='utf-8', errors='replace') as f:
            text = f.read()
        if 'UserMissions/WTPoligon' not in text and 'pkg_local/gameData' not in text:
            continue
        m = START.search(text)
        if not m:
            continue
        t0 = dt.datetime.strptime(' '.join(m.group(1).split()), '%b %d %H:%M:%S %Y') + off
        seen = {}
        for line in text.split('\n'):
            if not RELEVANT.search(line) or NOISE.search(line):
                continue
            sm = STAMP.match(line)
            if not sm:
                continue
            body = re.sub(r'^(\[[A-Z]\]\s+)?\$[0-9A-F]+\s+', lambda m: m.group(1) or '', line[sm.end():].strip())
            key = re.sub(r'0x[0-9A-Fa-f]+|\d+', 'N', body)[:200]
            if key in seen:
                seen[key][1] += 1
                continue
            seen[key] = [t0 + dt.timedelta(seconds=rel_seconds(sm.group(1))), 1, body]
        name = os.path.basename(path)
        yield t0, 'ИГРА', 'старт сессии ' + name
        for t, n, body in seen.values():
            yield t, 'ИГРА', ('[x%d] ' % n if n > 1 else '') + body[:300]


def applies():
    for mf in glob.glob(os.path.join(BACKUPS, '*', 'manifest.json')):
        with open(mf, encoding='utf-8') as f:
            m = json.load(f)
        files = ', '.join(('' if x.get('existed') else '+') + x['path'] for x in m.get('files', []))
        yield dt.datetime.fromtimestamp(m['time']), '4.7 ', '%s | %s' % (m.get('label', ''), files)


def main():
    ev = sorted(list(game_events()) + list(applies()), key=lambda e: e[0])
    out = os.path.join('cache', 'timeline.txt')
    with open(out, 'w', encoding='utf-8') as f:
        for t, who, s in ev:
            f.write('%s %s %s\n' % (t.strftime('%m-%d %H:%M:%S'), who, s))
    print(out, len(ev))


if __name__ == '__main__':
    sys.exit(main())
