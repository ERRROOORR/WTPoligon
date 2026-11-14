"""Журнал программы: `%LOCALAPPDATA%\\WTPoligon5\\logs\\wtpoligon.log` (по 2 МБ, 3 старых копии).

Пишутся запуск, запись/откат, ошибки проверки и сборки, необработанные исключения (окно, потоки, Qt) и время
долгих шагов. Кнопка «Логи» кладёт журнал в архив (`logs.collect`).
"""
import logging
import logging.handlers
import os
import sys
import threading
import time
from contextlib import contextmanager

LOG = logging.getLogger('wtpoligon')
FILE_NAME = 'wtpoligon.log'
_path = None


def log_dir(root):
    return os.path.join(root, 'logs')


def setup(root, version='?'):
    """Включить журнал (один раз за процесс); вернуть путь к файлу или None, если папка недоступна."""
    global _path
    if _path is not None:
        return _path
    try:
        os.makedirs(log_dir(root), exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(os.path.join(log_dir(root), FILE_NAME), maxBytes=2_000_000,
                                                       backupCount=3, encoding='utf-8')
    except OSError:
        return None
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-7s %(name)s: %(message)s'))
    base = logging.getLogger()
    base.addHandler(handler)
    base.setLevel(logging.INFO)
    _path = handler.baseFilename

    def excepthook(kind, value, tb):
        LOG.critical('Необработанная ошибка', exc_info=(kind, value, tb))
        sys.__excepthook__(kind, value, tb)

    def thread_hook(args):
        LOG.critical('Необработанная ошибка в потоке %s', getattr(args.thread, 'name', '?'),
                     exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = excepthook
    threading.excepthook = thread_hook
    LOG.info('Запуск WT Poligon %s; Python %s; %s', version, sys.version.split()[0], sys.platform)
    return _path


def install_qt_handler():
    """Предупреждения и ошибки самого Qt — тоже в журнал."""
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    levels = {QtMsgType.QtWarningMsg: logging.WARNING, QtMsgType.QtCriticalMsg: logging.ERROR,
              QtMsgType.QtFatalMsg: logging.CRITICAL}

    def handler(kind, _context, message):
        level = levels.get(kind)
        if level is not None:
            logging.getLogger('wtpoligon.qt').log(level, message)
    qInstallMessageHandler(handler)


@contextmanager
def timed(what, slow=1.0):
    """Записать время шага, если он дольше `slow` секунд."""
    start = time.perf_counter()
    try:
        yield
    finally:
        spent = time.perf_counter() - start
        if spent >= slow:
            LOG.info('%s: %.1f с', what, spent)
