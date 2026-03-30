"""Centralised colour tokens and QSS stylesheet strings for eROSuite."""

# Palette colours
BG_MAIN        = "#1e1e1e"
BG_PANEL       = "#141414"
BG_INPUT       = "#2b2b2b"
BG_BTN         = "#3a3a3a"
BORDER         = "#555555"
BORDER_DIM     = "#444444"
BORDER_FOCUS   = "#4A9EFF"
SEPARATOR      = "#3a3a3a"
TEXT_PRIMARY   = "#dddddd"
TEXT_SECONDARY = "#aaaaaa"
TEXT_MUTED     = "#888888"
TEXT_INPUT     = "#eeeeee"
TEXT_BLUE      = "#4A9EFF"
STATE_RUNNING  = "#F0A500"
STATE_DONE     = "#4CAF50"
STATE_ERROR    = "#F44336"
STATE_ACTIVE   = "#4A9EFF"

SCROLLBAR = (
    "QScrollBar:vertical { width: 6px; background: #2b2b2b; }"
    "QScrollBar::handle:vertical { background: #555; border-radius: 3px; }"
    "QScrollBar:horizontal { height: 6px; background: #2b2b2b; }"
    "QScrollBar::handle:horizontal { background: #555; border-radius: 3px; }"
)

INPUT = (
    "QLineEdit { background: #2b2b2b; border: 1px solid #555; border-radius: 4px;"
    " padding: 4px 6px; color: #eeeeee; }"
    "QLineEdit:focus { border: 1px solid #4A9EFF; }"
)

BTN_SECONDARY = (
    "QPushButton { background: #3a3a3a; border: 1px solid #555; border-radius: 4px;"
    " padding: 4px 8px; color: #cccccc; }"
    "QPushButton:hover { background: #505050; }"
)

BTN_PRIMARY = (
    "QPushButton { background: #4A9EFF; color: white; border-radius: 5px;"
    " font-size: 13px; font-weight: bold; }"
    "QPushButton:hover { background: #6ab4ff; }"
    "QPushButton:pressed { background: #2277cc; }"
    "QPushButton:disabled { background: #444; color: #888; }"
)

BTN_RUN_ALL = (
    "QPushButton { background: #2a6e2a; color: white; border-radius: 5px;"
    " font-size: 12px; font-weight: bold; }"
    "QPushButton:hover { background: #3a8e3a; }"
    "QPushButton:pressed { background: #1a4e1a; }"
    "QPushButton:disabled { background: #444; color: #888; }"
)

BTN_STOP = (
    "QPushButton { background: #8b1a1a; color: white; border-radius: 4px;"
    " font-size: 11px; font-weight: bold; }"
    "QPushButton:hover { background: #b22222; }"
    "QPushButton:pressed { background: #6b1010; }"
)

BTN_SMALL = (
    "QPushButton { background: #3a3a3a; border: 1px solid #555; border-radius: 3px;"
    " color: #aaa; font-size: 10px; }"
    "QPushButton:hover { background: #505050; }"
)

SCROLL_AREA = (
    "QScrollArea { border: 1px solid #333; border-radius: 4px; background: #141414; }"
    + SCROLLBAR
)

TAB_WIDGET = (
    "QTabWidget::pane { border: none; background: #1e1e1e; }"
    "QTabBar::tab { background: #252525; color: #777777; padding: 6px 20px;"
    " border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }"
    "QTabBar::tab:selected { background: #1e1e1e; color: #ffffff;"
    " border-top: 2px solid #4A9EFF; }"
    "QTabBar::tab:hover:!selected { background: #333333; color: #cccccc; }"
)
