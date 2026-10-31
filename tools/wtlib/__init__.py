"""Совместимость для исследовательских скриптов tools/: код переехал в пакет wtpoligon.game (этап 1).

`from wtlib import blk`, `from wtlib.vromfs import Vromfs` и т.п. дают те же объекты модулей, что и
`wtpoligon.game.*` — без второй копии кода.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from wtpoligon.game import blk, clog, mods, vromfs  # noqa: E402

for _m in (blk, clog, mods, vromfs):
    sys.modules[__name__ + '.' + _m.__name__.rsplit('.', 1)[1]] = _m
