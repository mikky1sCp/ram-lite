from __future__ import annotations
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QListWidget,
    QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from utils import theme


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RAM Lite")
        self.setMinimumSize(800, 520)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self._drag_pos = None
        self._build()

    def _build(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_title_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_nav())
        self._page_stack = QStackedWidget()
        self._page_stack.addWidget(self._build_accounts_page())
        self._page_stack.addWidget(self._build_settings_page())
        self._page_stack.addWidget(self._build_console_page())
        body.addWidget(self._page_stack, 1)
        outer.addLayout(body, 1)

    def _build_title_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(32)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 0, 0)
        lay.setSpacing(0)
        title = QLabel("RAM Lite")
        title.setObjectName("titleText")
        lay.addWidget(title)
        lay.addStretch(1)
        min_btn = QPushButton("-")
        min_btn.setObjectName("titleButton")
        min_btn.clicked.connect(self.showMinimized)
        lay.addWidget(min_btn)
        close_btn = QPushButton("x")
        close_btn.setObjectName("titleButton")
        close_btn.clicked.connect(self.close)
        lay.addWidget(close_btn)
        return bar

    def _build_nav(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("navPanel")
        panel.setFixedWidth(130)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 12, 8, 12)
        lay.setSpacing(6)
        for i, name in enumerate(("Accounts", "Settings", "Console")):
            btn = QPushButton(name)
            btn.setObjectName("navTab")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setChecked(i == 0)
            btn.clicked.connect(
                lambda _=False, idx=i: self._page_stack.setCurrentIndex(idx)
            )
            lay.addWidget(btn)
        lay.addStretch(1)
        ver = QLabel("v0.1.0")
        ver.setStyleSheet(f"color: {theme.COLORS['MUTED']}; font-size: 9px;")
        lay.addWidget(ver)
        return panel

    def _build_accounts_page(self) -> QFrame:
        page = QFrame()
        page.setObjectName("centerPanel")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        title = QLabel("Accounts")
        title.setObjectName("sectionTitle")
        lay.addWidget(title)
        self._account_list = QListWidget()
        lay.addWidget(self._account_list, 1)
        row = QHBoxLayout()
        add_btn = QPushButton("Add Account")
        add_btn.clicked.connect(self._on_add_account)
        row.addWidget(add_btn)
        row.addStretch(1)
        lay.addLayout(row)
        return page

    def _build_settings_page(self) -> QFrame:
        page = QFrame()
        page.setObjectName("centerPanel")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        lay.addWidget(title)
        lay.addWidget(QLabel("Settings will appear here."))
        lay.addStretch(1)
        return page

    def _build_console_page(self) -> QFrame:
        page = QFrame()
        page.setObjectName("centerPanel")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Console")
        title.setObjectName("sectionTitle")
        lay.addWidget(title)
        self._console = QLabel("Console output will appear here.")
        self._console.setStyleSheet(f"color: {theme.COLORS['MUTED']};")
        lay.addWidget(self._console)
        lay.addStretch(1)
        return page

    def _on_add_account(self):
        self._account_list.addItem("test_account")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 32:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())
    window = MainWindow()
    window.show()
    return app.exec()