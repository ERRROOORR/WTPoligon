"""Запуск как раньше (`python tools/wtlib/clog.py [логи] [куда]`); код — wtpoligon/game/clog.py."""
import os
import runpy
import sys

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    runpy.run_module('wtpoligon.game.clog', run_name='__main__')
