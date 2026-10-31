"""Тёмная тема (этап 3, макет A): минималистичная, крупный шрифт, карточки со скруглением, оранжевый акцент.
Стиль Fusion + палитра + QSS (docs/architecture.md §2). Цвета — COLORS, ими пользуются и страницы."""
from PySide6.QtGui import QColor, QFont, QPalette

COLORS = {
    'bg': '#0e1014', 's1': '#15181e', 's2': '#1b1f27', 's3': '#232833', 'line': '#2a303c', 'text': '#e9ecf1',
    'muted': '#8a93a3', 'dim': '#5c6473', 'accent': '#f2913d', 'accent_bg': '#2a1d12', 'ok': '#4cc38a',
    'warn': '#e8b64a', 'bad': '#ef5d5d', 'info': '#61a8f2',
    # совместимость со старыми страницами
    'window': '#0e1014', 'base': '#15181e', 'alt': '#1b1f27', 'button': '#1b1f27', 'link': '#61a8f2',
}

QSS = """
QWidget { color: #e9ecf1; font-size: 11pt; }
QMainWindow, QWidget#page { background: #0e1014; }
QToolTip { background: #232833; color: #e9ecf1; border: 1px solid #2a303c; padding: 6px; }
QPushButton, QToolButton { min-height: 34px; padding: 0 16px; border: 1px solid #2a303c; border-radius: 9px;
    background: #1b1f27; color: #e9ecf1; font-weight: 500; }
QPushButton:hover, QToolButton:hover { background: #232833; }
QPushButton:disabled, QToolButton:disabled { color: #5c6473; background: #15181e; }
QToolButton::menu-indicator { image: none; width: 0; }
QPushButton#primary { background: #f2913d; border-color: #f2913d; color: #15100a; font-weight: 600; }
QPushButton#primary:hover { background: #f5a35c; }
QPushButton#primary:disabled { background: #3a2a1c; border-color: #3a2a1c; color: #8a7a6a; }
QPushButton#step { border: none; border-radius: 17px; background: transparent; padding: 0 16px; color: #8a93a3;
    font-size: 11pt; }
QPushButton#step:checked { background: #1b1f27; color: #ffffff; }
QPushButton#step:disabled { color: #3d4450; }
QPushButton#help { min-width: 34px; max-width: 34px; padding: 0; border-radius: 9px; font-weight: 600; }
QPushButton#chip { min-height: 30px; padding: 0 14px; border-radius: 8px; border: 1px solid transparent;
    background: #1b1f27; color: #8a93a3; font-size: 10pt; }
QPushButton#chip:checked { background: #2a1d12; color: #f2913d; border-color: #6b4220; }
QPushButton#tab { border: none; border-radius: 0; background: transparent; padding: 0 2px 8px 2px; color: #8a93a3;
    font-weight: 600; min-height: 28px; }
QPushButton#tab:checked { color: #e9ecf1; border-bottom: 2px solid #f2913d; }
QFrame#card { background: #15181e; border: 1px solid #2a303c; border-radius: 14px; }
QFrame#pylon { background: #15181e; border: 1px solid #2a303c; border-radius: 12px; }
QFrame#pylon:hover { border-color: #3a4250; }
QFrame#pylon[selected="true"] { border: 2px solid #f2913d; background: #1c1712; }
QFrame#option { background: #1b1f27; border: 1px solid #2a303c; border-radius: 12px; }
QFrame#option:hover { border-color: #3a4250; background: #20252e; }
QFrame#option[selected="true"] { border: 2px solid #f2913d; background: #1f1812; }
QLabel { background: transparent; }
QLabel#hint, QLabel#muted { color: #8a93a3; }
QLabel#dim { color: #5c6473; font-size: 9.5pt; }
QLabel#warn { color: #e8b64a; }
QLabel#bad { color: #ef5d5d; }
QLabel#title { font-size: 15pt; font-weight: 700; }
QLabel#h1 { font-size: 18pt; font-weight: 700; }
QLabel#big { font-size: 24pt; font-weight: 700; }
QLabel#group { color: #8a93a3; font-size: 9.5pt; font-weight: 600; letter-spacing: 1px; }
QLabel#badge { background: #232833; color: #8a93a3; border-radius: 5px; padding: 0 5px; font-size: 8.5pt; }
QLineEdit, QComboBox, QSpinBox { min-height: 38px; padding: 0 12px; border: 1px solid #2a303c; border-radius: 10px;
    background: #1b1f27; selection-background-color: #f2913d; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #6b4220; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { background: #1b1f27; border: 1px solid #2a303c; selection-background-color: #2a1d12;
    selection-color: #f2913d; padding: 4px; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 20px; height: 20px; border-radius: 6px; border: 1px solid #3a4250; background: #1b1f27; }
QCheckBox::indicator:checked { background: #f2913d; border-color: #f2913d; }
QCheckBox#switch::indicator { width: 44px; height: 24px; border-radius: 12px; background: #3a4250; border: none; }
QCheckBox#switch::indicator:checked { background: #f2913d; }
QGroupBox { border: 1px solid #2a303c; border-radius: 14px; margin-top: 14px; padding: 12px 10px 10px 10px;
    background: #15181e; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #e9ecf1; font-weight: 600; }
QGroupBox::indicator { width: 18px; height: 18px; }
QTableView, QTreeWidget, QTextBrowser, QListWidget { border: 1px solid #2a303c; border-radius: 12px;
    background: #15181e; alternate-background-color: #181b22; gridline-color: #2a303c; }
QTableView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { background: #2a1d12;
    color: #f2913d; }
QHeaderView::section { background: #15181e; color: #8a93a3; padding: 8px; border: none;
    border-bottom: 1px solid #2a303c; font-size: 9.5pt; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar:horizontal { height: 10px; background: transparent; margin: 2px; }
QScrollBar::handle { background: #2f3542; border-radius: 4px; min-height: 30px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QProgressBar { border: none; border-radius: 4px; background: #232833; max-height: 8px; min-height: 8px; }
QProgressBar::chunk { border-radius: 4px; background: #4cc38a; }
QProgressBar[level="warn"]::chunk { background: #e8b64a; }
QProgressBar[level="bad"]::chunk { background: #ef5d5d; }
QProgressBar[level="info"]::chunk { background: #61a8f2; }
QMenu { background: #1b1f27; border: 1px solid #2a303c; padding: 6px; border-radius: 10px; }
QMenu::item { padding: 8px 18px; border-radius: 6px; }
QMenu::item:selected { background: #2a1d12; color: #f2913d; }
QMenu::separator { height: 1px; background: #2a303c; margin: 6px 4px; }
QSplitter::handle { background: transparent; }
"""


def apply_dark(app):
    app.setStyle('Fusion')
    f = QFont('Segoe UI')
    f.setPointSizeF(11)
    app.setFont(f)
    c = {k: QColor(v) for k, v in COLORS.items()}
    p = QPalette()
    for role, col in ((QPalette.Window, c['bg']), (QPalette.WindowText, c['text']), (QPalette.Base, c['s1']),
                      (QPalette.AlternateBase, c['s2']), (QPalette.ToolTipBase, c['s3']),
                      (QPalette.ToolTipText, c['text']), (QPalette.Text, c['text']), (QPalette.Button, c['s2']),
                      (QPalette.ButtonText, c['text']), (QPalette.BrightText, c['bad']), (QPalette.Link, c['info']),
                      (QPalette.Highlight, c['accent']), (QPalette.HighlightedText, QColor('#ffffff')),
                      (QPalette.PlaceholderText, c['dim'])):
        p.setColor(role, col)
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, c['dim'])
    app.setPalette(p)
    app.setStyleSheet(QSS)
