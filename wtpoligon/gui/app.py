"""Запуск окна: python -m wtpoligon [--game <папка>] [--datamine <клон>] [--app-dir <папка>] [--target <папка>].

Источник — как у командной строки: установленная игра (автопоиск, сохранённый путь) или клон датамайна (без
записи, если не задан --target). Игра не найдена — окно попросит указать её папку и запомнит её.
"""
import argparse
import os
import sys

from .. import paths as P
from ..game import index as X
from ..game import source as S


def _args(argv):
    ap = argparse.ArgumentParser(prog='python -m wtpoligon', description='WT Poligon 5 — окно программы.')
    ap.add_argument('--game', help='папка игры (по умолчанию — автопоиск)')
    ap.add_argument('--datamine', help='клон датамайна вместо игры (запись — только с --target)')
    ap.add_argument('--app-dir', help='папка данных программы')
    ap.add_argument('--target', help='куда записывать (по умолчанию — папка игры)')
    ap.add_argument('--refresh', action='store_true', help='пересобрать индекс техники')
    return ap.parse_args(argv)


def open_context(a, ask_game=None):
    """(источник, машины, папка программы, куда писать) или исключение с понятным текстом.
    ask_game() -> папка игры от пользователя (или None), если игра не найдена."""
    root = a.app_dir or P.app_root()
    if a.datamine:
        src = S.open_source(datamine=a.datamine)
    else:
        game = P.find_game_dir(a.game, root)
        if not game and ask_game is not None:
            game = ask_game()
            if game and P.is_game_dir(game):
                settings = P.load_settings(root)
                settings['game_dir'] = os.path.abspath(game)
                P.save_settings(root, settings)
        if not game or not P.is_game_dir(game):
            raise FileNotFoundError('Игра не найдена. Укажите папку War Thunder (в ней лежит aces.vromfs.bin).')
        src = S.open_source(game_dir=game)
    vehicles, _stats = X.load_index(src, os.path.join(root, 'cache'), a.refresh)
    target = a.target or (src.root if src.kind == 'game' else None)
    return src, vehicles, root, target


def main(argv=None):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

    from .theme import apply_dark
    from .window import MainWindow

    a = _args(sys.argv[1:] if argv is None else argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    apply_dark(app)

    def ask_game():
        app.restoreOverrideCursor()
        QMessageBox.information(None, 'WT Poligon 5', 'Не нашёл War Thunder. Укажите папку игры — ту, где лежит '
                                'aces.vromfs.bin (обычно %LOCALAPPDATA%\\WarThunder или папка Steam).')
        path = QFileDialog.getExistingDirectory(None, 'Папка War Thunder') or None
        app.setOverrideCursor(Qt.WaitCursor)
        return path

    app.setOverrideCursor(Qt.WaitCursor)   # первая сборка индекса техники — до минуты, дальше из кэша
    try:
        src, vehicles, root, target = open_context(a, ask_game)
    except (FileNotFoundError, OSError, ValueError) as e:
        app.restoreOverrideCursor()
        QMessageBox.critical(None, 'WT Poligon 5', str(e))
        return 2
    app.restoreOverrideCursor()
    win = MainWindow(src, vehicles, root, target)
    win.show()
    return app.exec()
