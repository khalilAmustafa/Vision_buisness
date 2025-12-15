# ui/theme.py
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QPalette, QColor


# -----------------------------
# Settings (persistent)
# -----------------------------
_SETTINGS = QSettings("Vision", "VisionBusinessModel")


def load_theme_preference():
    mode = _SETTINGS.value("theme/mode", "dark")
    accent = _SETTINGS.value("theme/accent", "indigo")
    return str(mode), str(accent)


def save_theme_preference(mode: str, accent: str):
    _SETTINGS.setValue("theme/mode", mode)
    _SETTINGS.setValue("theme/accent", accent)


# -----------------------------
# Accent presets (demo-friendly)
# -----------------------------
ACCENTS = {
    "indigo": {"ACCENT": "#4F46E5", "ACCENT_HOVER": "#6366F1", "ACCENT_LIGHT_DARK": "#1F2A5A", "ACCENT_LIGHT_LIGHT": "#E0E7FF"},
    "cyan":   {"ACCENT": "#06B6D4", "ACCENT_HOVER": "#22D3EE", "ACCENT_LIGHT_DARK": "#0B2F3A", "ACCENT_LIGHT_LIGHT": "#CFFAFE"},
    "emerald":{"ACCENT": "#10B981", "ACCENT_HOVER": "#34D399", "ACCENT_LIGHT_DARK": "#0D2A1F", "ACCENT_LIGHT_LIGHT": "#D1FAE5"},
    "rose":   {"ACCENT": "#F43F5E", "ACCENT_HOVER": "#FB7185", "ACCENT_LIGHT_DARK": "#2B0F18", "ACCENT_LIGHT_LIGHT": "#FFE4E6"},
}


def _accent_tokens(mode: str, accent: str):
    a = ACCENTS.get(accent, ACCENTS["indigo"])
    if mode == "dark":
        return a["ACCENT"], a["ACCENT_HOVER"], a["ACCENT_LIGHT_DARK"]
    return a["ACCENT"], a["ACCENT_HOVER"], a["ACCENT_LIGHT_LIGHT"]


# -----------------------------
# Base color tokens (Light / Dark)
# -----------------------------
LIGHT_BASE = {
    "BACKGROUND": "#F6F8FF",
    "SURFACE": "#FFFFFF",
    "TEXT": "#0F172A",
    "MUTED": "#64748B",
    "BORDER": "#DDE3F1",
}

DARK_BASE = {
    "BACKGROUND": "#0B1220",
    "SURFACE": "#111827",
    "TEXT": "#E5E7EB",
    "MUTED": "#94A3B8",
    "BORDER": "#1F2937",
}


def _tokens(mode: str, accent: str):
    base = DARK_BASE if mode == "dark" else LIGHT_BASE
    accent_color, accent_hover, accent_light = _accent_tokens(mode, accent)

    t = dict(base)
    t["ACCENT"] = accent_color
    t["ACCENT_HOVER"] = accent_hover
    t["ACCENT_LIGHT"] = accent_light
    return t


def _build_palette(mode: str, accent: str) -> QPalette:
    t = _tokens(mode, accent)

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(t["BACKGROUND"]))
    pal.setColor(QPalette.Base, QColor(t["SURFACE"]))
    pal.setColor(QPalette.AlternateBase, QColor(t["SURFACE"]))
    pal.setColor(QPalette.WindowText, QColor(t["TEXT"]))
    pal.setColor(QPalette.Text, QColor(t["TEXT"]))
    pal.setColor(QPalette.Button, QColor(t["SURFACE"]))
    pal.setColor(QPalette.ButtonText, QColor(t["TEXT"]))
    pal.setColor(QPalette.Highlight, QColor(t["ACCENT"]))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    return pal


def _build_stylesheet(mode: str, accent: str) -> str:
    t = _tokens(mode, accent)

    if mode == "dark":
        hero_bg = "#0B1B3A"
        table_header_bg = "#121C33"
        table_header_fg = t["TEXT"]
        metric_total_bg = "#141B2E"
        metric_emp_bg = "#0F2A2A"
        metric_mgr_bg = "#2A220F"
        metric_total_border = "#2B3A7A"
        metric_emp_border = "#1A4F4B"
        metric_mgr_border = "#5A4A1A"
    else:
        hero_bg = "#0B1B3A"
        table_header_bg = t["ACCENT_LIGHT"]
        table_header_fg = "#0F172A"
        metric_total_bg = "#EEF2FF"
        metric_emp_bg = "#F0FDFA"
        metric_mgr_bg = "#FFFBEB"
        metric_total_border = "#C7D2FE"
        metric_emp_border = "#99F6E4"
        metric_mgr_border = "#FDE68A"

    return f"""
/* ---------- GLOBAL ---------- */
QWidget {{
    background: {t["BACKGROUND"]};
    color: {t["TEXT"]};
    font-family: Segoe UI, Arial;
    font-size: 13px;
}}

/* IMPORTANT: no label rectangles */
QLabel {{
    background: transparent;
}}

/* ---------- CARDS ---------- */
QFrame#Card {{
    background: {t["SURFACE"]};
    border: 1px solid {t["BORDER"]};
    border-radius: 16px;
}}

/* ---------- HERO PANEL ---------- */
QFrame#HeroPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {hero_bg}, stop:1 {t["BACKGROUND"]});
    border-radius: 20px;
}}

QLabel#HeroTitle {{
    color: #F8FAFF;
    font-size: 30px;
    font-weight: 800;
}}

QLabel#HeroBody {{
    color: #C7D2FE;
    font-size: 13px;
}}

QLabel#TitleLabel {{
    font-size: 22px;
    font-weight: 700;
}}

QLabel#MutedLabel {{
    color: {t["MUTED"]};
}}

QLabel#MetricValue {{
    font-size: 20px;
    font-weight: 700;
}}


QTimeEdit {{
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 10px 12px;
    min-height: 36px;
}}
QTimeEdit:focus {{
    border-color: #4F46E5;
}}
QTimeEdit::up-button, QTimeEdit::down-button {{
    width: 18px;
    border: none;
    background: transparent;
}}


QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: #1F2A5A;
    border-radius: 6px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #3343A5;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #1F2A5A;
    border-radius: 6px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #3343A5;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: transparent;
}}


/* ---------- BUTTONS ---------- */
QPushButton {{
    background-color: {t["ACCENT"]};
    color: white;
    border: none;
    border-radius: 12px;
    padding: 10px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {t["ACCENT_HOVER"]};
}}

QPushButton#SecondaryButton {{
    background: transparent;
    color: {t["ACCENT"]};
    border: 1px solid {t["BORDER"]};
}}
QPushButton#SecondaryButton:hover {{
    border-color: {t["ACCENT"]};
}}

/* ---------- INPUTS ---------- */
QLineEdit, QComboBox {{
    background: {t["SURFACE"]};
    border: 1px solid {t["BORDER"]};
    border-radius: 12px;
    padding: 10px 12px;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {t["ACCENT"]};
}}

/* ---------- TABS ---------- */
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    padding: 10px 16px;
    margin-right: 10px;
    color: {t["MUTED"]};
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {t["TEXT"]};
    border-bottom: 3px solid {t["ACCENT"]};
}}

/* ---------- TABLE ---------- */
QTableWidget {{
    background: {t["SURFACE"]};
    border: 1px solid {t["BORDER"]};
    border-radius: 14px;
    gridline-color: {t["BORDER"]};
}}
QHeaderView::section {{
    background-color: {table_header_bg};
    color: {table_header_fg};
    border: none;
    padding: 10px;
    font-weight: 700;
}}
QTableWidget::item:selected {{
    background: {t["ACCENT_LIGHT"]};
}}

/* ---------- METRIC CARDS ---------- */
QFrame#MetricCardTotal {{
    background: {metric_total_bg};
    border: 1px solid {metric_total_border};
    border-radius: 14px;
}}
QFrame#MetricCardEmployees {{
    background: {metric_emp_bg};
    border: 1px solid {metric_emp_border};
    border-radius: 14px;
}}
QFrame#MetricCardManagers {{
    background: {metric_mgr_bg};
    border: 1px solid {metric_mgr_border};
    border-radius: 14px;
}}
"""


def apply_theme(app, mode: str = "dark", accent: str = "indigo"):
    app.setPalette(_build_palette(mode, accent))
    app.setStyleSheet(_build_stylesheet(mode, accent))
