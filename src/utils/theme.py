from __future__ import annotations

COLORS = {
    "BG": "#0E0E0E",
    "PANEL": "#151515",
    "INPUT": "#1A1A1A",
    "TEXT": "#EDEDED",
    "MUTED": "#AAAAAA",
    "LINE": "#242424",
    "SELECT": "#2A2A2A",
    "ACCENT": "#0078D7",
    "ACCENT_TEXT": "#5DBBFF",
    "NOTE": "#D6BB7D",
}


def stylesheet() -> str:
    c = COLORS
    return f"""
    QMainWindow {{ background: {c['BG']}; }}
    QWidget {{ color: {c['TEXT']}; font-family: 'Segoe UI'; font-size: 11px; }}
    QFrame#navPanel {{ background: {c['PANEL']}; border: 0; }}
    QFrame#centerPanel {{ background: {c['BG']}; border: 0; }}
    QFrame#titleBar {{ background: {c['PANEL']}; border-bottom: 1px solid {c['LINE']}; }}
    QLabel#titleText {{ font-size: 12px; font-weight: 700; }}
    QLabel#sectionTitle {{ font-size: 13px; font-weight: 700; }}
    QPushButton#navTab {{
        background: transparent; border: 1px solid transparent;
        text-align: left; min-height: 28px; padding: 2px 8px; color: {c['MUTED']};
    }}
    QPushButton#navTab:checked {{
        background: {c['SELECT']}; border: 1px solid {c['LINE']};
        color: {c['TEXT']}; font-weight: 700;
    }}
    QPushButton#titleButton {{
        background: transparent; border: 0;
        min-height: 24px; min-width: 30px; color: {c['MUTED']};
    }}
    QPushButton#titleButton:hover {{ background: {c['SELECT']}; color: {c['TEXT']}; }}
    QPushButton {{
        background: {c['INPUT']}; border: 1px solid {c['LINE']};
        min-height: 26px; padding: 2px 8px; color: {c['TEXT']};
    }}
    QPushButton:hover {{ background: {c['SELECT']}; }}
    QListWidget {{
        background: {c['INPUT']}; border: 1px solid {c['LINE']}; outline: none;
    }}
    QListWidget::item {{ height: 24px; padding-left: 6px; }}
    QListWidget::item:selected {{ background: {c['SELECT']}; color: {c['TEXT']}; }}
    QLineEdit {{
        background: {c['INPUT']}; border: 1px solid {c['LINE']};
        padding: 4px 6px; min-height: 24px; color: {c['TEXT']};
    }}
        QCheckBox {{ color: {c['TEXT']}; font-size: 11px; spacing: 6px; }}
    QCheckBox::indicator {{
        width: 13px; height: 13px;
        border: 1px solid {c['LINE']}; background: {c['INPUT']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['ACCENT']}; border: 1px solid {c['ACCENT']};
    }}
    QComboBox {{
        background: {c['INPUT']}; border: 1px solid {c['LINE']};
        color: {c['TEXT']}; padding: 3px 6px; min-height: 24px;
    }}
    QComboBox QAbstractItemView {{
        background: {c['PANEL']}; color: {c['TEXT']};
        selection-background-color: {c['SELECT']};
    }}
    """