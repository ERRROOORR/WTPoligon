"""Архив для тестеров: программа + переносной Python со всеми зависимостями, запуск — run.bat (без exe, ТЗ §8).

Использование: .venv\\Scripts\\python tools\\make_beta.py --name Beta-1.0
Результат: dist\\WTPoligon-<name>.zip (внутри папка WTPoligon-<name>: run.bat, python\\, wtpoligon\\, README).
"""
import argparse
import fnmatch
import os
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PYTHON = Path(sys.base_prefix)                  # переносной CPython, на котором собран .venv
SITE = ROOT / '.venv' / 'Lib' / 'site-packages'

# части PySide6, которые программа не использует (окно — только QtWidgets/QtGui/QtCore): без них архив втрое меньше
SKIP = ['__pycache__', '*.pyc', 'pip', 'pip-*', 'setuptools', 'setuptools-*', '_distutils_hack',
        'Qt6WebEngine*', 'QtWebEngine*', 'qtwebengine*', 'Qt6Quick*', 'QtQuick*', 'Qt6Qml*', 'QtQml*',
        'Qt63D*', 'Qt3D*', 'Qt6Pdf*', 'QtPdf*', 'Qt6Designer*', 'QtDesigner*', 'Qt6Multimedia*', 'QtMultimedia*',
        'Qt6Charts*', 'QtCharts*', 'Qt6DataVisualization*', 'QtDataVisualization*', 'Qt6Graphs*', 'QtGraphs*',
        'Qt6Location*', 'QtLocation*', 'Qt6Positioning*', 'QtPositioning*', 'Qt6Sensors*', 'QtSensors*',
        'Qt6SerialPort*', 'QtSerialPort*', 'Qt6Bluetooth*', 'QtBluetooth*', 'Qt6Nfc*', 'QtNfc*',
        'Qt6RemoteObjects*', 'QtRemoteObjects*', 'Qt6Scxml*', 'QtScxml*', 'Qt6SpatialAudio*', 'QtSpatialAudio*',
        'Qt6TextToSpeech*', 'QtTextToSpeech*', 'Qt6WebChannel*', 'QtWebChannel*', 'Qt6WebSockets*', 'QtWebSockets*',
        'Qt6WebView*', 'QtWebView*', 'Qt6HttpServer*', 'QtHttpServer*', 'Qt6VirtualKeyboard*',
        'designer.exe', 'assistant.exe', 'linguist.exe', 'lupdate.exe', 'lrelease.exe', 'qmlls.exe',
        'qtwebengine_locales', 'qml', 'translations']

RUN_BAT = r'''@echo off
chcp 65001 >nul
rem WT Poligon — запуск без установки: run.bat без аргументов — окно; run.bat <команда> — командная строка
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"python\python.exe" -m wtpoligon %*
'''

README = '''WT Poligon {name} — закрытый тест

Запуск: распакуйте папку куда угодно (путь лучше без кириллицы не обязателен) и дважды щёлкните run.bat.
Python ставить не нужно — он внутри (папка python).

Если что-то не работает: шаг «Проверка и запись» → кнопка «Логи» (справа внизу). Программа соберёт логи игры
и свои записи в архив в папке logs рядом с run.bat — пришлите этот архив вместе с описанием, что делали.

Откат всего, что записала программа: шаг «Проверка и запись» → «Откатить всё».
Чек-лист для тестеров — TESTING.md.

Автор — ERRROOORR, https://github.com/ERRROOORR/WTPoligon. Лицензия GPL v3 (LICENSE) с условием указывать
автора при распространении и публичном использовании (NOTICE.md).
'''


def skipped(name):
    return any(fnmatch.fnmatch(name, p) for p in SKIP)


def copy_tree(src, dst):
    def ignore(_dir, names):
        return [n for n in names if skipped(n)]
    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    a = ap.parse_args()
    folder = 'WTPoligon-' + a.name
    out = ROOT / 'dist' / folder
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    copy_tree(BASE_PYTHON, out / 'python')                       # интерпретатор + стандартная библиотека
    copy_tree(SITE, out / 'python' / 'Lib' / 'site-packages')    # зависимости из .venv
    copy_tree(ROOT / 'wtpoligon', out / 'wtpoligon')
    for f in ('VERSION', 'CHANGELOG.md', 'requirements.txt', 'LICENSE', 'NOTICE.md'):
        shutil.copy2(ROOT / f, out / f)
    if (ROOT / 'docs' / 'TESTING.md').exists():
        shutil.copy2(ROOT / 'docs' / 'TESTING.md', out / 'TESTING.md')
    (out / 'run.bat').write_text(RUN_BAT, encoding='utf-8')
    (out / 'README.txt').write_text(README.format(name=a.name), encoding='utf-8')
    archive = ROOT / 'dist' / (folder + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in out.rglob('*'):
            if path.is_file():
                z.write(path, Path(folder) / path.relative_to(out))
    print('%s — %.0f МБ' % (archive, archive.stat().st_size / 2 ** 20))


if __name__ == '__main__':
    main()
