from __future__ import annotations
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from classes.account_manager import AccountManager
from classes.operation_result import OperationResult
from utils import theme
from utils.workers import BackgroundTask


class _ImportCookieDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.cookie_value = ""
        self.setWindowTitle("Import Cookie")
        self.setFixedSize(500, 220)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        lay.addWidget(QLabel("Paste a .ROBLOSECURITY cookie:"))
        self._text = QTextEdit()
        self._text.setPlaceholderText("_|WARNING:-DO-NOT-SHARE-THIS...")
        lay.addWidget(self._text, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        ok_btn = QPushButton("Import")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        lay.addLayout(row)

    def _accept(self):
        self.cookie_value = self._text.toPlainText().strip()
        if self.cookie_value:
            self.accept()


class MainWindow(QMainWindow):
    def __init__(self, manager: AccountManager):
        super().__init__()
        self._manager = manager
        self._import_task: BackgroundTask | None = None
        self.setWindowTitle("RAM Lite")
        self.setMinimumSize(800, 520)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self._drag_pos = None
        self._build()
        self._refresh_accounts()

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
        ver = QLabel("v0.2.0")
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
        self._add_btn = QPushButton("Add Account")
        self._add_btn.clicked.connect(self._on_add_account)
        row.addWidget(self._add_btn)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_accounts)
        row.addWidget(refresh_btn)
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

    def _refresh_accounts(self) -> None:
        self._account_list.clear()
        for username, data in self._manager.accounts.items():
            note = data.get("note", "")
            label = username if not note else f"{username}    |    {note}"
            self._account_list.addItem(label)

    def _on_add_account(self) -> None:
        dlg = _ImportCookieDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.cookie_value:
            return
        self._import_cookie(dlg.cookie_value)

    def _import_cookie(self, cookie: str) -> None:
        if self._import_task is not None:
            return
        self._add_btn.setEnabled(False)
        self._add_btn.setText("Importing...")
        task = BackgroundTask(
            lambda: self._manager.import_cookie_account_result(cookie), self,
        )
        task.completed.connect(self._on_import_done)
        task.failed.connect(self._on_import_failed)
        self._import_task = task
        task.start()

    def _on_import_done(self, result: OperationResult) -> None:
        self._import_task = None
        self._add_btn.setEnabled(True)
        self._add_btn.setText("Add Account")
        if result:
            self._refresh_accounts()
            QMessageBox.information(self, "Account Added", result.message)
        else:
            QMessageBox.critical(
                self, result.title or "Import Failed",
                f"{result.message}\n\nError code: {result.code}",
            )

    def _on_import_failed(self, exc: BaseException) -> None:
        self._import_task = None
        self._add_btn.setEnabled(True)
        self._add_btn.setText("Add Account")
        QMessageBox.critical(self, "Import Failed", str(exc))

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
    manager = AccountManager()
    window = MainWindow(manager)
    window.show()
    return app.exec()