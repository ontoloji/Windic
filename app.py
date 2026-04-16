import os
import sys
import json
from pathlib import Path
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMenu,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
)

from googletrans import Translator
import keyboard


def get_app_icon() -> QIcon:
    """Load app icon from assets if present, otherwise use an empty icon."""
    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent

    icon_path = base_path / "assets" / "windic.ico"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


def register_windows_startup() -> None:
    """Register app in HKCU Run so it starts when the user logs in."""
    if os.name != "nt":
        return

    try:
        import winreg

        app_name = "WindicMiniTranslate"
        run_key = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"

        if getattr(sys, "frozen", False):
            executable = Path(sys.executable)
            command = f'"{executable}" --background'
        else:
            script_path = Path(__file__).resolve()
            python_path = Path(sys.executable)
            pythonw_path = python_path.with_name("pythonw.exe")
            runner = pythonw_path if pythonw_path.exists() else python_path
            command = f'"{runner}" "{script_path}" --background'

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
    except Exception:
        # Startup registration should never block app startup.
        pass


class CompactTranslateWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.translator = Translator(
            service_urls=[
                "translate.googleapis.com",
                "translate.google.com",
            ]
        )
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(460, 250)
        self._dragging = False
        self._drag_position = QPoint()
        self.source_lang = "auto"
        self.target_lang = "tr"

        self.drag_handle = QWidget(self)
        self.drag_handle.setObjectName("dragHandle")
        self.drag_handle.setFixedHeight(6)
        self.drag_handle.setFixedWidth(250)

        self.input_box = QLineEdit(self)
        self.input_box.setPlaceholderText("Type a word...")

        self.output_box = QTextEdit(self)
        self.output_box.setReadOnly(True)
        self.output_box.setPlaceholderText("Translation appears here...")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)
        root_layout.addWidget(self.drag_handle, alignment=Qt.AlignHCenter)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        content_layout.addWidget(self.input_box)
        content_layout.addWidget(self.output_box)
        root_layout.addLayout(content_layout)

        self.setStyleSheet(
            """
            QWidget {
                background-color: rgba(248, 249, 251, 235);
                border-radius: 18px;
            }
            #dragHandle {
                background-color: #bfe8bf;
                border-radius: 3px;
            }
            QLineEdit, QTextEdit {
                background-color: #ffffff;
                border: 1px solid #d8dde5;
                border-radius: 14px;
                padding: 12px;
                font-family: 'Segoe UI';
                font-size: 16px;
                color: #20262e;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #8ea4c9;
            }
            """
        )

        self.translate_timer = QTimer(self)
        self.translate_timer.setSingleShot(True)
        self.translate_timer.setInterval(320)
        self.translate_timer.timeout.connect(self.translate_text)

        self.input_box.textChanged.connect(self.on_text_changed)

        self.toggle_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Space"), self)
        self.toggle_shortcut.activated.connect(self.toggle_visible)
        self.hide_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        self.hide_shortcut.activated.connect(self.hide)
        self.tr_to_en_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        self.tr_to_en_shortcut.activated.connect(self.set_direction_tr_to_en)
        self.en_to_tr_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        self.en_to_tr_shortcut.activated.connect(self.set_direction_en_to_tr)

    def _translate_via_public_endpoint(self, text: str) -> str:
        """Fallback for when googletrans fails due to token/service issues."""
        params = urllib_parse.urlencode(
            {
                "client": "gtx",
                "sl": self.source_lang,
                "tl": self.target_lang,
                "dt": "t",
                "q": text,
            }
        )
        url = f"https://translate.googleapis.com/translate_a/single?{params}"
        req = urllib_request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        with urllib_request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))

        parts = payload[0] if isinstance(payload, list) and payload else []
        translated = "".join(
            part[0] for part in parts if isinstance(part, list) and part and part[0]
        )
        if not translated:
            raise ValueError("Empty translation response")
        return translated

    def on_text_changed(self, _: str) -> None:
        self.translate_timer.start()

    def set_direction_tr_to_en(self) -> None:
        self.source_lang = "tr"
        self.target_lang = "en"
        self.output_box.setPlaceholderText("Translation appears here... (TR -> EN)")
        if self.input_box.text().strip():
            self.translate_timer.start()

    def set_direction_en_to_tr(self) -> None:
        self.source_lang = "en"
        self.target_lang = "tr"
        self.output_box.setPlaceholderText("Translation appears here... (EN -> TR)")
        if self.input_box.text().strip():
            self.translate_timer.start()

    def translate_text(self) -> None:
        source_text = self.input_box.text().strip()
        if not source_text:
            self.output_box.clear()
            return

        try:
            result = self.translator.translate(
                source_text,
                src=self.source_lang,
                dest=self.target_lang,
            )
            self.output_box.setPlainText(result.text)
            return
        except Exception as first_error:
            pass

        try:
            fallback_text = self._translate_via_public_endpoint(source_text)
            self.output_box.setPlainText(fallback_text)
        except (urllib_error.URLError, TimeoutError, OSError):
            self.output_box.setPlainText(
                "Google Translate is not reachable right now. Check your internet, VPN/proxy, or firewall."
            )
        except Exception:
            self.output_box.setPlainText(
                f"Translation failed: {first_error.__class__.__name__}."
            )

    def toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
            return

        if not self.pos().x() and not self.pos().y():
            self.move_to_default_position()

        self.show()
        self.activateWindow()
        self.raise_()
        self.input_box.setFocus()

    def move_to_default_position(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        screen_geometry = screen.availableGeometry()
        margin = 24
        x = screen_geometry.right() - self.width() - margin
        y = screen_geometry.bottom() - self.height() - margin
        self.move(x, y)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton and self.drag_handle.geometry().contains(event.pos()):
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)


def create_tray(app: QApplication, window: CompactTranslateWindow) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(get_app_icon(), app)

    menu = QMenu()
    show_action = QAction("Open Translator", menu)
    quit_action = QAction("Quit", menu)

    show_action.triggered.connect(window.toggle_visible)
    quit_action.triggered.connect(app.quit)

    menu.addAction(show_action)
    menu.addSeparator()
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.setToolTip("Windic Mini Translator")
    tray.activated.connect(
        lambda reason: window.toggle_visible()
        if reason == QSystemTrayIcon.Trigger
        else None
    )
    tray.show()
    
    if not tray.isVisible():
        raise RuntimeError("Failed to display system tray icon. Check Windows system tray settings.")
    
    return tray


def main() -> int:
    register_windows_startup()

    app = QApplication(sys.argv)
    app.setWindowIcon(get_app_icon())
    app.setQuitOnLastWindowClosed(False)

    window = CompactTranslateWindow()
    window.move_to_default_position()
    
    try:
        tray = create_tray(app, window)
    except Exception as e:
        sys.exit(f"Error: Failed to initialize system tray.\n{e}")

    hotkey = "ctrl+shift+space"
    hotkey_registered = False
    try:
        keyboard.add_hotkey(hotkey, lambda: QTimer.singleShot(0, window.toggle_visible))
        hotkey_registered = True
    except Exception:
        hotkey_registered = False

    if hotkey_registered:
        app.aboutToQuit.connect(keyboard.unhook_all_hotkeys)
    app.aboutToQuit.connect(tray.hide)

    if "--show" in sys.argv:
        window.toggle_visible()
    else:
        window.hide()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
