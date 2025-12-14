from PyQt5.QtGui import QPalette, QColor


PRIMARY = "#0F172A"
ACCENT = "#2563EB"
ACCENT_LIGHT = "#DBEAFE"
BACKGROUND = "#F4F6FB"
SURFACE = "#FFFFFF"
TEXT = "#111827"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
ERROR = "#EF4444"


GLOBAL_STYLE = f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: 'Segoe UI', 'Helvetica Neue', Arial;
    font-size: 13px;
}}
QMainWindow {{
    background-color: {BACKGROUND};
}}
QFrame#Card {{
    background-color: {SURFACE};
    border-radius: 14px;
    border: 1px solid {BORDER};
    padding: 16px;
}}
QFrame#HeroPanel {{
    background-color: #0C1F42;
    color: #E3ECFF;
    border: none;
}}
QFrame#HeroPanel QLabel {{
    color: #E3ECFF;
    background: transparent;
}}
QLabel#TitleLabel {{
    font-size: 22px;
    font-weight: 600;
    color: {PRIMARY};
}}
QLabel#HeroTitle {{
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 6px;
    color: #F8FAFF;
}}
QLabel#HeroBody {{
    color: #D6E3FF;
}}
QLabel#MutedLabel {{
    color: {MUTED};
}}
QLabel#MetricValue {{
    font-size: 20px;
    font-weight: 600;
    color: {PRIMARY};
}}
QPushButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: #1D4ED8;
}}
QPushButton#SecondaryButton {{
    background-color: transparent;
    border: 1px solid {BORDER};
    color: {PRIMARY};
}}
QLineEdit, QComboBox, QTimeEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 10px;
}}
QTableWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    gridline-color: {BORDER};
    selection-background-color: {ACCENT};
    selection-color: white;
    alternate-background-color: #FAFBFF;
}}
QHeaderView::section {{
    background-color: #EEF2FF;
    color: {PRIMARY};
    border: none;
    padding: 6px;
    font-weight: 600;
}}
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background-color: transparent;
    border: none;
    padding: 8px 18px;
    font-weight: 600;
    color: {MUTED};
}}
QTabBar::tab:selected {{
    color: {PRIMARY};
    border-bottom: 3px solid {ACCENT};
}}
QChartView {{
    background: {SURFACE};
    border-radius: 14px;
    border: 1px solid {BORDER};
}}
"""


def apply_theme(app):
    app.setStyleSheet(GLOBAL_STYLE)
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(BACKGROUND))
    palette.setColor(QPalette.Base, QColor(SURFACE))
    palette.setColor(QPalette.AlternateBase, QColor("#FAFBFF"))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Text, QColor(TEXT))
    app.setPalette(palette)
