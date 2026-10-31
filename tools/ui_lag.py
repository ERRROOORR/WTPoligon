r"""Замер подвисаний окна: выбор машин и переход по шагам на настоящей игре (offscreen).

Пульс окна каждые 20 мс; пауза пульса > порога = подвисание. Для каждого действия печатает время вызова
в потоке окна и самые долгие паузы, в конце — где стоял поток окна (выборка стека).
Запуск: set QT_QPA_PLATFORM=offscreen & .venv\Scripts\python tools\ui_lag.py [--limit 0.2]
Код выхода 1, если какое-либо действие или пауза дольше порога.
"""
import argparse
import os
import multiprocessing
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

VEHICLES = ('f_15c_golden_eagle', 'a_26b_10', 'germ_leopard_2a7v', 'mi_28nm', 'us_destroyer_fletcher')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=float, default=0.2)
    a = ap.parse_args()
    app = QApplication([])
    from wtpoligon.gui.app import _args, open_context
    from wtpoligon.gui.window import MainWindow
    src, vehicles, root, target = open_context(_args([]))
    win = MainWindow(src, vehicles, root, target)
    win.show()
    main_id = threading.get_ident()
    last, label, stalls, samples, slow = [time.perf_counter()], ['запуск'], [], {}, []

    def beat():
        now = time.perf_counter()
        if now - last[0] > a.limit:
            stalls.append((label[0], round(now - last[0], 2)))
        last[0] = now

    hb = QTimer()
    hb.timeout.connect(beat)
    hb.start(20)

    def sampler():
        while True:
            time.sleep(0.05)
            if time.perf_counter() - last[0] > a.limit * 0.75:
                frame = sys._current_frames().get(main_id)
                if frame:
                    st = [f for f in traceback.extract_stack(frame) if 'wtpoligon' in f.filename][-4:]
                    key = ' <- '.join('%s:%d %s' % (os.path.basename(f.filename), f.lineno, f.name) for f in reversed(st))
                    samples[key] = samples.get(key, 0) + 1

    threading.Thread(target=sampler, daemon=True).start()
    steps = [('простой после запуска', lambda: None, 4000)]
    for name in VEHICLES:
        steps.append(('выбор ' + name, lambda n=name: win.vehicles_page.select(n), 2500))
        for s in range(1, 5):
            steps.append(('%s → шаг %d' % (name, s), lambda s=s: win.go(s), 1500))
        steps.append(('%s → шаг 0' % name, lambda: win.go(0), 1000))

    def run(i=0):
        if i >= len(steps):
            print('\nПаузы окна > %.2f с: %d' % (a.limit, len(stalls)))
            for s in stalls:
                print('  %-40s %.2f с' % s)
            print('\nГде стоял поток окна (выборки):')
            for k, c in sorted(samples.items(), key=lambda x: -x[1])[:15]:
                print('  %3d  %s' % (c, k))
            app.exit(1 if stalls or slow else 0)
            return
        name, fn, wait = steps[i]
        label[0] = name
        t = time.perf_counter()
        fn()
        d = time.perf_counter() - t
        print('%-40s %.2f с%s' % (name, d, '  ← ДОЛГО' if d > a.limit else ''))
        if d > a.limit:
            slow.append(name)
        last[0] = time.perf_counter()
        QTimer.singleShot(wait, lambda: run(i + 1))

    QTimer.singleShot(100, run)
    sys.exit(app.exec())


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
