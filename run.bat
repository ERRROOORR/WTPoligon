@echo off
chcp 65001 >nul
rem WT Poligon 5 — запуск без сборки exe (ТЗ §8): run.bat без аргументов — окно; run.bat list / mission <машина> / install <машина> … — командная строка
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
".venv\Scripts\python.exe" -m wtpoligon %*
