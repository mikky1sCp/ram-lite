from __future__ import annotations
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMessageBox, QPushButton, QStackedWidget, QTextEdit, QVBoxLayout,
    QWidget,
)

from classes.account_manager import AccountManager
from classes.operation_result import OperationResult
from features import avatars, launcher
from utils import theme
from utils.workers import BackgroundTask

_AVATAR_SIZE = 22


def _circular_pixmap(data: bytes, size: int = _AVATAR_SIZE) -> QPixmap:
    src = QPixmap()
    src.loadFromData(data)
    if src.isNull():
        return QPixmap()
    src = src.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, src)
    painter.end()
    return result


def _placeholder_pixmap(size: int = _AVATAR_SIZE) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(Qt.GlobalColor.darkGray)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return pix


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
        self._avatar_tasks: list[BackgroundTask] = []
        self._avatar_labels: dict[str, QLabel] = {}
        self._search_query = ""
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
        ver = QLabel("v0.4.0 beta")
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

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search accounts...")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search_changed)
        lay.addWidget(self._search_edit)

        self._account_list = QListWidget()
        self._account_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._account_list.customContextMenuRequested.connect(
            self._on_context_menu
        )
        self._account_list.itemDoubleClicked.connect(self._on_double_click)
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

    def _on_search_changed(self, text: str) -> None:
        self._search_query = text.strip().lower()
        self._refresh_accounts()

    def _matches(self, username: str, note: str) -> bool:
        if not self._search_query:
            return True
        haystack = f"{username} {note}".lower()
        return self._search_query in haystack

    def _refresh_accounts(self) -> None:
        self._account_list.clear()
        self._avatar_labels.clear()
        self._avatar_tasks.clear()

        visible = [
            (username, data)
            for username, data in self._manager.accounts.items()
            if self._matches(username, data.get("note", ""))
        ]

        if not visible:
            item = QListWidgetItem(
                "No accounts match your search." if self._search_query
                else "No accounts. Use 'Add Account' to add one."
            )
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._account_list.addItem(item)
            return

        for username, data in visible:
            note = data.get("note", "")
            item = QListWidgetItem("")
            item.setSizeHint(_avatar_size_hint())
            item.setData(Qt.ItemDataRole.UserRole, username)

            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(4, 0, 6, 0)
            row_lay.setSpacing(6)

            av_label = QLabel()
            av_label.setFixedSize(_AVATAR_SIZE, _AVATAR_SIZE)
            av_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cached = avatars.get_cached(str(data.get("user_id", "")))
            if cached:
                pix = _circular_pixmap(cached)
                av_label.setPixmap(pix if not pix.isNull() else _placeholder_pixmap())
            else:
                av_label.setPixmap(_placeholder_pixmap())
                user_id = str(data.get("user_id", ""))
                if user_id and user_id != "0":
                    self._load_avatar_async(user_id, av_label)
            row_lay.addWidget(av_label)

            name_label = QLabel(username)
            row_lay.addWidget(name_label)

            if note:
                sep = QLabel("|")
                sep.setStyleSheet(f"color: {theme.COLORS['MUTED']};")
                row_lay.addWidget(sep)
                note_label = QLabel(note)
                note_label.setStyleSheet(f"color: {theme.COLORS['NOTE']}; font-weight: 600;")
                row_lay.addWidget(note_label)

            row_lay.addStretch(1)
            self._account_list.addItem(item)
            self._account_list.setItemWidget(item, row)

    def _load_avatar_async(self, user_id: str, label: QLabel) -> None:
        task = BackgroundTask(lambda: avatars.download_avatar(user_id), self)
        task.completed.connect(
            lambda data, lbl=label: self._on_avatar_ready(data, lbl)
        )
        self._avatar_tasks.append(task)
        task.start()

    def _on_avatar_ready(self, data, label: QLabel) -> None:
        if not data:
            return
        pix = _circular_pixmap(bytes(data))
        if pix.isNull():
            return
        try:
            label.setPixmap(pix)
        except RuntimeError:
            pass

    def _selected_username(self) -> str | None:
        item = self._account_list.currentItem()
        if item is None:
            return None
        username = item.data(Qt.ItemDataRole.UserRole)
        return username if username in self._manager.accounts else None

    def _on_context_menu(self, pos) -> None:
        username = self._selected_username()
        if not username:
            return
        menu = QMenu(self)
        home_action = menu.addAction("Launch Roblox Home")
        place_action = menu.addAction("Launch Place ID...")
        menu.addSeparator()
        edit_action = menu.addAction("Edit Note")
        delete_action = menu.addAction("Delete")
        chosen = menu.exec(self._account_list.mapToGlobal(pos))
        if chosen is home_action:
            self._launch_home(username)
        elif chosen is place_action:
            self._launch_place(username)
        elif chosen is edit_action:
            self._edit_note(username)
        elif chosen is delete_action:
            self._delete_account(username)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        username = item.data(Qt.ItemDataRole.UserRole)
        if username in self._manager.accounts:
            self._edit_note(username)

    def _edit_note(self, username: str) -> None:
        current = self._manager.get_note(username)
        note, ok = QInputDialog.getText(
            self, f"Edit Note - {username}", "Note:", text=current,
        )
        if not ok:
            return
        self._manager.set_note(username, note)
        self._refresh_accounts()

    def _launch_home(self, username: str) -> None:
        data = dict(self._manager.accounts.get(username, {}))
        if not data:
            return
        self._run_launch(username, lambda: launcher.launch_home(data))

    def _launch_place(self, username: str) -> None:
        data = dict(self._manager.accounts.get(username, {}))
        if not data:
            return
        place_id, ok = QInputDialog.getText(
            self, f"Launch {username} in Place ID", "Place ID:",
        )
        if not ok or not place_id.strip():
            return
        self._run_launch(
            username,
            lambda: launcher.launch_place(data, place_id.strip()),
        )

    def _run_launch(self, username: str, work) -> None:
        task = BackgroundTask(work, self)
        task.completed.connect(
            lambda result, u=username: self._on_launch_done(u, result)
        )
        task.failed.connect(
            lambda exc, u=username: self._on_launch_failed(u, exc)
        )
        task.start()

    def _on_launch_done(self, username: str, result: OperationResult) -> None:
        if result:
            return
        QMessageBox.critical(
            self, result.title or "Launch Failed",
            f"{result.message}\n\nError code: {result.code}",
        )

    def _on_launch_failed(self, username: str, exc: BaseException) -> None:
        QMessageBox.critical(
            self, "Launch Failed", f"{username}: {exc}",
        )

    def _delete_account(self, username: str) -> None:
        reply = QMessageBox.question(
            self, "Delete Account",
            f"Remove '{username}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._manager.delete_account(username):
            self._refresh_accounts()

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


def _avatar_size_hint():
    from PySide6.QtCore import QSize
    return QSize(0, _AVATAR_SIZE + 6)


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())
    manager = AccountManager()
    window = MainWindow(manager)
    window.show()
    return app.exec()