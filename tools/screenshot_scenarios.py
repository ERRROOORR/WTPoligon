"""Capture the five scenario modes with the real data source in offscreen Qt."""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtTest import QTest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase

from wtpoligon.gui.app import _args, open_context
from wtpoligon.gui.theme import apply_dark
from wtpoligon.gui.window import MainWindow


def main():
    app = QApplication([])
    # The offscreen Qt plugin does not discover Windows fonts on its own.
    for name in ('segoeui.ttf', 'segoeuib.ttf', 'segoeuii.ttf', 'seguisym.ttf'):
        QFontDatabase.addApplicationFont(str(Path('C:/Windows/Fonts') / name))
    apply_dark(app)
    source, vehicles, root, target = open_context(_args([]))
    window = MainWindow(source, vehicles, root, target)
    window.resize(int(os.environ.get("WTP_SHOT_W", 1280)), int(os.environ.get("WTP_SHOT_H", 900)))
    window.show()
    output = Path(__file__).resolve().parents[1] / 'docs' / 'screens'
    output.mkdir(parents=True, exist_ok=True)
    examples = {
        'ground': 'germ_leopard_2a7v',
        'air': 'f_15c_golden_eagle',
        'heli': 'mi_28nm',
        'naval': 'us_destroyer_fletcher',
        'duel': 'f_15c_golden_eagle',
    }
    for mode, vehicle in examples.items():
        window.vehicles_page.select(vehicle)
        window.go(3)
        for _ in range(200):
            app.processEvents()
            if window.scenario_page._pending is None:
                break
            QTest.qWait(20)
        window.scenario_page.set_mode(mode)
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()
        window.grab().save(str(output / f'scenarios_{mode}.png'))
        window.go(0)
    window.close()


if __name__ == '__main__':
    main()
