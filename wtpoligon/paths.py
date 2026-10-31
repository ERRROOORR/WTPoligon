"""Папки программы: данные (%LOCALAPPDATA%\\WTPoligon5), настройки, путь к игре."""
import json
import os

APP_NAME = 'WTPoligon5'


def app_root():
    """Папка данных программы: WTP_APP_DIR (тесты) или %LOCALAPPDATA%\\WTPoligon5 (вне Windows — ~/.local/share)."""
    if os.environ.get('WTP_APP_DIR'):
        return os.environ['WTP_APP_DIR']
    base = os.environ.get('LOCALAPPDATA') or os.path.join(os.path.expanduser('~'), '.local', 'share')
    return os.path.join(base, APP_NAME)


def load_settings(root):
    p = os.path.join(root, 'settings.json')
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(root, settings):
    os.makedirs(root, exist_ok=True)
    tmp = os.path.join(root, 'settings.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(root, 'settings.json'))


def is_game_dir(path):
    return bool(path) and os.path.isfile(os.path.join(path, 'aces.vromfs.bin'))


def game_candidates(root=None):
    """Где искать игру по порядку: WTP_GAME, сохранённый путь, %LOCALAPPDATA%\\WarThunder, Steam."""
    out = []
    if os.environ.get('WTP_GAME'):
        out.append(os.environ['WTP_GAME'])
    if root:
        saved = load_settings(root).get('game_dir')
        if saved:
            out.append(saved)
    if os.environ.get('LOCALAPPDATA'):
        out.append(os.path.join(os.environ['LOCALAPPDATA'], 'WarThunder'))
    for pf in (os.environ.get('ProgramFiles(x86)'), os.environ.get('ProgramFiles')):
        if pf:
            out.append(os.path.join(pf, 'Steam', 'steamapps', 'common', 'War Thunder'))
    return out


def find_game_dir(explicit=None, root=None):
    """Папка игры: явный путь (если это игра) или первый найденный кандидат; None — не найдена."""
    if explicit:
        return explicit if is_game_dir(explicit) else None
    return next((p for p in game_candidates(root) if is_game_dir(p)), None)
