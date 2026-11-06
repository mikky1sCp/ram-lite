from __future__ import annotations
import os
import sys
import threading

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

from classes.account_manager import (
    AccountManager,
    AccountManagerError,
    AccountPasswordError,
    PasswordRequiredError,
)
from classes.encryption import EncryptionConfig
from classes.operation_result import OperationResult
from features import avatars, launcher, multi_roblox
from features import settings_store
from features.cookie_validator import validate_all_cookies
from features.instance_guard import InstanceGuard  # STEP 8
from utils import theme
from utils.app_paths import get_data_dir
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


class _CookieCheckWorker(QObject):
    checked = Signal(str, bool)
    finished = Signal(int, int)

    def __init__(self, manager, delay: float, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._delay = delay
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="cookie-check",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            validate_all_cookies(
                self._manager,
                on_progress=self._on_progress,
                on_done=self._on_done,
                delay=self._delay,
                stop_event=self._stop,
            )
        except Exception:
            try:
                self.finished.emit(0, 0)
            except Exception:
                pass

    def _on_progress(self, username: str, is_valid: bool) -> None:
        self.checked.emit(username, is_valid)

    def _on_done(self, valid: int, invalid: int) -> None:
        self.finished.emit(valid, invalid)


class MainWindow(QMainWindow):
    def __init__(self, manager: AccountManager):
        super().__init__()
        self._manager = manager
        self._import_task: BackgroundTask | None = None
        self._avatar_tasks: list[BackgroundTask] = []
        self._avatar_labels: dict[str, QLabel] = {}
        self._search_query = ""
        # STEP 7
        self._cookie_worker: _CookieCheckWorker | None = None
        self._cookie_badges: dict[str, QLabel] = {}
        self._cookie_total = 0
        self._cookie_done = 0
        # STEP 8
        self._instance_guard: InstanceGuard | None = None

        self.setWindowTitle("RAM Lite")
        self.setMinimumSize(800, 520)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self._drag_pos = None
        self._list_selection_mode_changed()
        self._build()
        self._refresh_accounts()
        QTimer.singleShot(1500, self._start_cookie_check)
        # STEP 8: auto-start guard when the setting is enabled
        if settings_store.get("instance_guard_enabled", False):
            self._on_guard_toggled(True)

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
        ver = QLabel("v0.7.0 beta")
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

        self._cookie_status = QLabel("")
        self._cookie_status.setStyleSheet(
            f"color: {theme.COLORS['MUTED']}; font-size: 10px;"
        )
        self._cookie_status.hide()
        lay.addWidget(self._cookie_status)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search accounts...")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search_changed)
        lay.addWidget(self._search_edit)

        self._account_list = QListWidget()
        self._account_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
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

    def _list_selection_mode_changed(self) -> None:
        if hasattr(self, "_account_list"):
            self._account_list.setSelectionMode(
                QListWidget.SelectionMode.ExtendedSelection
            )

    def _build_settings_page(self) -> QFrame:
        page = QFrame()
        page.setObjectName("centerPanel")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        lay.addWidget(title)

        launcher_lbl = QLabel("Roblox launcher:")
        launcher_lbl.setStyleSheet(f"color: {theme.COLORS['MUTED']};")
        lay.addWidget(launcher_lbl)
        self._launcher_combo = QComboBox()
        self._launcher_combo.addItem("Default (Windows handler)", "default")
        self._launcher_combo.addItem("Bloxstrap", "bloxstrap")
        self._launcher_combo.addItem("Roblox Client (direct .exe)", "client")
        current = settings_store.get("roblox_launcher", "default")
        idx = self._launcher_combo.findData(current)
        if idx >= 0:
            self._launcher_combo.setCurrentIndex(idx)
        self._launcher_combo.currentIndexChanged.connect(
            self._on_launcher_changed
        )
        lay.addWidget(self._launcher_combo)

        self._multi_chk = QCheckBox(
            "Enable Multi Roblox (run several clients at once)"
        )
        self._multi_chk.setChecked(multi_roblox.is_enabled())
        self._multi_chk.toggled.connect(self._on_multi_toggled)
        lay.addWidget(self._multi_chk)

        hint = QLabel(
            "Multi Roblox must be enabled before launching a second client. "
            "Close all Roblox windows before toggling it on."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.COLORS['MUTED']}; font-size: 10px;")
        lay.addWidget(hint)

        # STEP 8: Instance Guard section
        guard_title = QLabel("Instance Guard (experimental)")
        guard_title.setStyleSheet(
            f"color: {theme.COLORS['MUTED']}; margin-top: 12px;"
        )
        lay.addWidget(guard_title)

        self._guard_chk = QCheckBox("Keep instances alive")
        self._guard_chk.setToolTip(
            "Continuously closes Roblox singleton handles to prevent "
            "clients from closing when new ones launch.\n"
            "Uses native handle manipulation — use at your own risk.\n"
            "Run RAM Lite as administrator for this to work."
        )
        self._guard_chk.setChecked(
            bool(settings_store.get("instance_guard_enabled", False))
        )
        self._guard_chk.toggled.connect(self._on_guard_toggled)
        lay.addWidget(self._guard_chk)

        guard_hint = QLabel(
            "Requires administrator rights. Manipulates Windows handles "
            "of Roblox processes. Anti-cheat systems may treat this "
            "as suspicious activity."
        )
        guard_hint.setWordWrap(True)
        guard_hint.setStyleSheet(
            f"color: {theme.COLORS['NOTE']}; font-size: 10px;"
        )
        lay.addWidget(guard_hint)

        # Encryption section
        enc_title = QLabel("Encryption")
        enc_title.setStyleSheet(
            f"color: {theme.COLORS['MUTED']}; margin-top: 12px;"
        )
        lay.addWidget(enc_title)

        self._enc_status = QLabel()
        self._enc_status.setWordWrap(True)
        self._enc_btn = QPushButton("Enable Encryption...")
        self._refresh_encryption_widgets()
        lay.addWidget(self._enc_status)
        lay.addWidget(self._enc_btn)
        self._enc_btn.clicked.connect(self._on_enable_encryption)

        enc_hint = QLabel(
            "AES-GCM with a password. Only the salt is stored on disk — "
            "the password itself is never saved. If you forget it, "
            "the saved cookies cannot be recovered."
        )
        enc_hint.setWordWrap(True)
        enc_hint.setStyleSheet(
            f"color: {theme.COLORS['MUTED']}; font-size: 10px;"
        )
        lay.addWidget(enc_hint)

        # Cookie validation section
        cookie_title = QLabel("Cookie validation")
        cookie_title.setStyleSheet(
            f"color: {theme.COLORS['MUTED']}; margin-top: 12px;"
        )
        lay.addWidget(cookie_title)

        self._cookie_check_chk = QCheckBox("Check cookies on startup")
        self._cookie_check_chk.setChecked(
            bool(settings_store.get("check_cookies_on_startup", True))
        )
        self._cookie_check_chk.toggled.connect(
            lambda v: settings_store.save("check_cookies_on_startup", v)
        )
        lay.addWidget(self._cookie_check_chk)

        delay_row = QHBoxLayout()
        delay_lbl = QLabel("Delay between checks (seconds):")
        delay_lbl.setStyleSheet(f"color: {theme.COLORS['MUTED']};")
        delay_row.addWidget(delay_lbl)
        delay_row.addStretch(1)
        self._cookie_delay_spin = QDoubleSpinBox()
        self._cookie_delay_spin.setRange(0.5, 30.0)
        self._cookie_delay_spin.setSingleStep(0.5)
        self._cookie_delay_spin.setDecimals(1)
        self._cookie_delay_spin.setValue(
            float(settings_store.get("cookie_check_delay_seconds", 1.5))
        )
        self._cookie_delay_spin.valueChanged.connect(
            lambda v: settings_store.save(
                "cookie_check_delay_seconds", float(v),
            )
        )
        delay_row.addWidget(self._cookie_delay_spin)
        lay.addLayout(delay_row)

        lay.addStretch(1)
        return page

    # STEP 8: InstanceGuard lifecycle
    def _on_guard_toggled(self, enabled: bool) -> None:
        settings_store.save("instance_guard_enabled", enabled)
        if enabled:
            if self._instance_guard is None:
                self._instance_guard = InstanceGuard(interval=3.0)
            self._instance_guard.start()
            self._console.setText(
                "Instance Guard started. It will keep closing singleton "
                "handles in Roblox processes every 3 seconds."
            )
            self._console.setStyleSheet(
                f"color: {theme.COLORS['ACCENT_TEXT']};"
            )
        else:
            if self._instance_guard is not None:
                self._instance_guard.stop()
                self._instance_guard = None
            self._console.setText("Instance Guard stopped.")
            self._console.setStyleSheet(f"color: {theme.COLORS['MUTED']};")

    def _refresh_encryption_widgets(self) -> None:
        enabled = self._manager.is_encryption_enabled()
        if enabled:
            self._enc_status.setText("Encryption: enabled (AES-GCM)")
            self._enc_status.setStyleSheet(
                f"color: {theme.COLORS['ACCENT_TEXT']};"
            )
        else:
            self._enc_status.setText(
                "Encryption: disabled — cookies are stored in plain text."
            )
            self._enc_status.setStyleSheet(f"color: {theme.COLORS['NOTE']};")
        self._enc_btn.setEnabled(not enabled)

    def _on_enable_encryption(self) -> None:
        pw1, ok = QInputDialog.getText(
            self, "Enable Encryption",
            "Choose a password (min. 8 characters).\n"
            "There is no recovery if you lose it:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not pw1:
            return
        if len(pw1) < 8:
            QMessageBox.warning(
                self, "Password Too Short",
                "Use a password with at least 8 characters.",
            )
            return
        pw2, ok = QInputDialog.getText(
            self, "Enable Encryption", "Confirm password:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return
        if pw1 != pw2:
            QMessageBox.warning(
                self, "Passwords Do Not Match", "Try again.",
            )
            return
        result = self._manager.enable_encryption(pw1)
        if not result:
            QMessageBox.critical(
                self, result.title or "Encryption Failed",
                f"{result.message}\n\nError code: {result.code}",
            )
            return
        QMessageBox.information(self, "Encryption Enabled", result.message)
        self._refresh_encryption_widgets()

    def _on_launcher_changed(self, _index: int) -> None:
        settings_store.save(
            "roblox_launcher", self._launcher_combo.currentData(),
        )

    def _on_multi_toggled(self, checked: bool) -> None:
        if checked:
            result = multi_roblox.enable()
            if not result:
                self._multi_chk.blockSignals(True)
                self._multi_chk.setChecked(False)
                self._multi_chk.blockSignals(False)
                QMessageBox.critical(
                    self, result.title or "Multi Roblox",
                    f"{result.message}\n\nError code: {result.code}",
                )
        else:
            multi_roblox.disable()

    def _start_cookie_check(self) -> None:
        if self._cookie_worker is not None:
            return
        if not settings_store.get("check_cookies_on_startup", True):
            return
        if not self._manager.accounts:
            return
        delay = float(settings_store.get("cookie_check_delay_seconds", 1.5))
        self._cookie_total = len(self._manager.accounts)
        self._cookie_done = 0
        worker = _CookieCheckWorker(self._manager, delay, self)
        worker.checked.connect(self._on_cookie_checked)
        worker.finished.connect(self._on_cookie_check_finished)
        self._cookie_worker = worker
        self._cookie_status.setText(
            f"Checking cookies... 0/{self._cookie_total}"
        )
        self._cookie_status.show()
        worker.start()

    def _on_cookie_checked(self, username: str, is_valid: bool) -> None:
        self._cookie_done += 1
        if self._cookie_total > 0:
            self._cookie_status.setText(
                f"Checking cookies... "
                f"{self._cookie_done}/{self._cookie_total}"
            )
        badge = self._cookie_badges.get(username)
        if badge is not None:
            try:
                badge.setVisible(not is_valid)
            except RuntimeError:
                pass

    def _on_cookie_check_finished(self, valid: int, invalid: int) -> None:
        self._cookie_worker = None
        self._cookie_status.hide()
        if invalid > 0:
            self._console.setText(
                f"Cookie check: {valid} valid, {invalid} expired. "
                "Re-import expired cookies via 'Add Account'."
            )
            self._console.setStyleSheet(f"color: {theme.COLORS['NOTE']};")
        elif valid > 0:
            self._console.setText(
                f"Cookie check: {valid} valid."
            )
            self._console.setStyleSheet(f"color: {theme.COLORS['MUTED']};")

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
        self._console.setWordWrap(True)
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
        self._cookie_badges.clear()

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

            av_container = QWidget()
            av_container.setFixedSize(_AVATAR_SIZE, _AVATAR_SIZE)
            av_inner = QHBoxLayout(av_container)
            av_inner.setContentsMargins(0, 0, 0, 0)
            av_inner.setSpacing(0)
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
            av_inner.addWidget(av_label)

            badge = QLabel(av_container)
            badge.setFixedSize(8, 8)
            badge.setStyleSheet(
                "background: #E5534B; border-radius: 4px; "
                "border: 1px solid #0E0E0E;"
            )
            badge.setToolTip(
                "Cookie expired — re-import it via 'Add Account'."
            )
            badge.move(_AVATAR_SIZE - 8, _AVATAR_SIZE - 8)
            cookie_valid = data.get("cookie_valid")
            badge.setVisible(cookie_valid is False)
            self._cookie_badges[username] = badge

            row_lay.addWidget(av_container)

            name_label = QLabel(username)
            row_lay.addWidget(name_label)

            if note:
                sep = QLabel("|")
                sep.setStyleSheet(f"color: {theme.COLORS['MUTED']};")
                row_lay.addWidget(sep)
                note_label = QLabel(note)
                note_label.setStyleSheet(
                    f"color: {theme.COLORS['NOTE']}; font-weight: 600;"
                )
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

    def _selected_usernames(self) -> list[str]:
        usernames = []
        for item in self._account_list.selectedItems():
            username = item.data(Qt.ItemDataRole.UserRole)
            if username and username in self._manager.accounts:
                usernames.append(username)
        return usernames

    def _launch_home_batch(self, usernames: list[str]) -> None:
        if not multi_roblox.is_enabled():
            reply = QMessageBox.question(
                self, "Multi Roblox Required",
                "Multi Roblox is not enabled. Enable it now? "
                "All running Roblox windows must be closed first.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            result = multi_roblox.enable()
            if not result:
                QMessageBox.critical(
                    self, result.title or "Multi Roblox",
                    f"{result.message}\n\nError code: {result.code}",
                )
                return
            self._multi_chk.blockSignals(True)
            self._multi_chk.setChecked(True)
            self._multi_chk.blockSignals(False)

        accounts = [
            (u, dict(self._manager.accounts[u])) for u in usernames
        ]
        task = BackgroundTask(
            lambda: launcher.launch_home_batch(accounts, delay=1.5), self,
        )
        task.completed.connect(self._on_batch_launch_done)
        task.failed.connect(
            lambda exc: QMessageBox.critical(
                self, "Batch Launch Failed", str(exc),
            )
        )
        task.start()

    def _on_batch_launch_done(self, result: OperationResult) -> None:
        if result:
            QMessageBox.information(self, "Launch Complete", result.message)
        else:
            detail = result.detail or ""
            QMessageBox.warning(
                self, result.title or "Partial Launch",
                f"{result.message}\n\n{detail}",
            )

    def _selected_username(self) -> str | None:
        item = self._account_list.currentItem()
        if item is None:
            return None
        username = item.data(Qt.ItemDataRole.UserRole)
        return username if username in self._manager.accounts else None

    def _on_context_menu(self, pos) -> None:
        selected = self._selected_usernames()
        if not selected:
            return
        menu = QMenu(self)
        if len(selected) == 1:
            home_action = menu.addAction("Launch Roblox Home")
            place_action = menu.addAction("Launch Place ID...")
        else:
            home_action = None
            place_action = None
            batch_action = menu.addAction(
                f"Launch {len(selected)} Accounts (Home)"
            )
        menu.addSeparator()
        edit_action = menu.addAction("Edit Note")
        delete_action = menu.addAction("Delete")
        chosen = menu.exec(self._account_list.mapToGlobal(pos))
        if not chosen:
            return
        if len(selected) == 1 and chosen is home_action:
            self._launch_home(selected[0])
        elif len(selected) == 1 and chosen is place_action:
            self._launch_place(selected[0])
        elif len(selected) > 1 and chosen is batch_action:
            self._launch_home_batch(selected)
        elif chosen is edit_action:
            self._edit_note(selected[0])
        elif chosen is delete_action:
            self._delete_account(selected[0])

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

    def closeEvent(self, event):
        if self._cookie_worker is not None:
            self._cookie_worker.stop()
            self._cookie_worker = None
        # STEP 8: stop InstanceGuard cleanly
        if self._instance_guard is not None:
            self._instance_guard.stop()
            self._instance_guard = None
        super().closeEvent(event)


def _avatar_size_hint():
    from PySide6.QtCore import QSize
    return QSize(0, _AVATAR_SIZE + 6)


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    data_dir = os.environ.get("RAM_DATA_DIR", "").strip() or get_data_dir()
    cfg = EncryptionConfig(os.path.join(data_dir, "encryption_config.json"))

    password = None
    if cfg.is_enabled():
        password, ok = QInputDialog.getText(
            None, "Password Required",
            "Enter your accounts password:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return 1

    try:
        manager = AccountManager(password=password)
    except PasswordRequiredError:
        QMessageBox.critical(
            None, "Password Required",
            "The accounts file is encrypted. Restart and enter a password.",
        )
        return 1
    except AccountPasswordError:
        QMessageBox.critical(
            None, "Wrong Password",
            "The password could not unlock the accounts file.",
        )
        return 1
    except AccountManagerError as exc:
        QMessageBox.critical(None, "Cannot Open Accounts", str(exc))
        return 1

    window = MainWindow(manager)
    window.show()
    return app.exec()