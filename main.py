import sys
import time
from io import BytesIO
import matplotlib
import pyautogui
import pygetwindow as gw
import unicodeitplus
# MACOS CHANGE: Removed win32clipboard and win32con
from PIL import Image
# MACOS CHANGE: Replaced keyboard with pynput for robust, cross-platform hotkeys
from pynput import keyboard
import threading
import os

from PyQt5.QtCore import Qt, QObject, QTimer, QPoint, pyqtSignal
from PyQt5.QtGui import (QIcon, QFont, QPalette, QColor, QPixmap, QPainter, QBrush,
                         QPen, QImage)
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, QWidget,
                             QVBoxLayout, QLineEdit, QLabel, QSizePolicy)

matplotlib.use('Agg')
import matplotlib.pyplot as plt


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class LaTeXOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(450, 220)
        self.setWindowTitle("LaTeX to Unicode Inserter")
        self.last_active_window = None
        self.use_image_mode = False
        self.drag_position = None
        self.setup_ui()
        self.setup_dark_theme_styles()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor(43, 43, 43, 235))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)

    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Enter LaTeX (e.g., \\sqrt{x^2} or \\nu)")
        # MACOS CHANGE: Removed specific font for better cross-platform compatibility
        self.input_box.setFont(QFont("", 16))
        self.input_box.textChanged.connect(self.update_preview)
        self.input_box.returnPressed.connect(self.insert_and_hide)
        self.status_label = QLabel("Mode: Unicode (Press Tab to switch)")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("", 10))
        self.status_label.setObjectName("statusLabel")
        self.canvas_label = QLabel("Preview will appear here")
        self.canvas_label.setAlignment(Qt.AlignCenter)
        self.canvas_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas_label.setFont(QFont("", 24))
        self.layout.addWidget(self.input_box)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.canvas_label)

    def setup_dark_theme_styles(self):
        self.setStyleSheet("""
            QWidget {
                color: #dcdcdc;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 6px;
                color: #dcdcdc;
            }
            QLabel#statusLabel {
                color: #888;
            }
        """)

    def showEvent(self, event):
        self.input_box.clear()
        self.canvas_label.clear()
        self.input_box.setFocus()
        super().showEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_Tab:
            self.toggle_mode()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.input_box.geometry().contains(event.pos()):
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
            else:
                self.drag_position = None
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def toggle_mode(self):
        self.use_image_mode = not self.use_image_mode
        mode_text = "Image" if self.use_image_mode else "Unicode"
        self.status_label.setText(f"Mode: {mode_text} (Press Tab to switch)")
        self.update_preview()

    def update_preview(self):
        latex_code = self.input_box.text().strip()
        if not latex_code:
            self.canvas_label.setText("Preview will appear here")
            self.canvas_label.setPixmap(QPixmap())
            return
        if self.use_image_mode:
            self.render_image_preview(latex_code)
        else:
            self.render_unicode_preview(latex_code)

    def render_unicode_preview(self, latex_code):
        try:
            unicode_result = unicodeitplus.replace(latex_code)
            self.canvas_label.setText(unicode_result)
        except Exception as e:
            self.canvas_label.setText("Invalid Unicode")
            print(f"Unicode conversion error: {e}")

    def render_image_preview(self, latex_code):
        try:
            fig, ax = plt.subplots(figsize=(4, 1.5), dpi=150)
            ax.text(0.5, 0.5, fr"${latex_code}$", size=20, ha='center', va='center', color='#dcdcdc')
            ax.axis('off')
            fig.patch.set_alpha(0)
            qt_buf = BytesIO()
            fig.savefig(qt_buf, format='png', bbox_inches='tight', transparent=True)
            qt_buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(qt_buf.getvalue())
            self.canvas_label.setPixmap(pixmap)
            plt.close(fig)
        except Exception as e:
            self.canvas_label.setText("Render Error")
            print(f"Matplotlib render error: {str(e).strip()}")

    def insert_and_hide(self):
        latex_code = self.input_box.text().strip()
        if not latex_code:
            self.hide()
            return
        self.hide()
        # MACOS NOTE: This .activate() call can be unreliable on macOS.
        # Fortunately, the subsequent paste command will go to the active window anyway.
        if self.last_active_window:
            try:
                time.sleep(0.1)
                self.last_active_window.activate()
                time.sleep(0.1)
            except Exception as e:
                print(f"Could not activate previous window: {e}")

        # MACOS CHANGE: Use 'command' (Cmd) key instead of 'ctrl' for pasting
        paste_key = 'command' if sys.platform == 'darwin' else 'ctrl'

        if self.use_image_mode:
            self.paste_as_image(latex_code, paste_key)
        else:
            self.paste_as_unicode(latex_code, paste_key)

    def paste_as_unicode(self, latex_code, paste_key):
        try:
            result = unicodeitplus.replace(latex_code)
            QApplication.clipboard().setText(result)
            pyautogui.hotkey(paste_key, 'v')
        except Exception as e:
            print(f"Failed to insert Unicode for '{latex_code}': {e}")

    # MACOS CHANGE: Complete rewrite of paste_as_image to be cross-platform using PyQt
    def paste_as_image(self, latex_code, paste_key):
        try:
            # 1. Render the LaTeX to an in-memory PNG buffer
            fig, ax = plt.subplots(figsize=(4, 1.5), dpi=150)
            ax.text(0.5, 0.5, fr"${latex_code}$", size=20, ha='center', va='center', color='#dcdcdc')
            ax.axis('off')
            fig.patch.set_alpha(0)
            buf = BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
            buf.seek(0)
            plt.close(fig)

            # 2. Load this buffer into a QImage, which is what the clipboard needs
            qimage = QImage()
            qimage.loadFromData(buf.getvalue())

            # 3. Set the clipboard using PyQt's cross-platform method
            QApplication.clipboard().setImage(qimage)

            # 4. Simulate paste
            pyautogui.hotkey(paste_key, 'v')

        except Exception as e:
            print(f"Failed to paste image for '{latex_code}': {e}")


# MACOS CHANGE: New Hotkey Listener class using pynput
class HotkeyListener(QObject):
    hotkey_activated = pyqtSignal() # A signal to safely communicate with the GUI thread

    def __init__(self):
        super().__init__()
        # Define the hotkey combination. Use `Key.cmd` for macOS Command key.
        self.hotkey = keyboard.HotKey(
            keyboard.HotKey.parse('<cmd>+<alt>+m')
        )
        self.listener_thread = None

    def run(self):
        # This will run in a separate thread
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()

    def on_press(self, key):
        if self.hotkey.check(key):
            self.hotkey_activated.emit()

    def start(self):
        if not self.listener_thread:
            self.listener_thread = threading.Thread(target=self.run, daemon=True)
            self.listener_thread.start()


class AppManager(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.overlay_window = None

    # MACOS CHANGE: No more polling timer. This is now a slot connected to the hotkey signal.
    def toggle_overlay_visibility(self):
        if self.overlay_window is None:
            self.overlay_window = LaTeXOverlay()
        if self.overlay_window.isVisible():
            self.overlay_window.hide()
        else:
            try:
                # This might fail on some macOS setups or without permissions
                self.overlay_window.last_active_window = gw.getActiveWindow()
            except Exception:
                self.overlay_window.last_active_window = None
            win = self.overlay_window
            pos = pyautogui.position()
            # Find the screen where the mouse is
            screen = self.app.screenAt(QPoint(pos.x, pos.y))
            if not screen:
                screen = self.app.primaryScreen()
            screen_rect = screen.availableGeometry()

            # Center the window under the cursor, but keep it on screen
            ideal_x = pos.x - win.width() // 2
            ideal_y = pos.y - 20
            final_x = max(screen_rect.left(), min(ideal_x, screen_rect.right() - win.width()))
            final_y = max(screen_rect.top(), min(ideal_y, screen_rect.bottom() - win.height()))

            win.move(final_x, final_y)
            win.show()
            win.activateWindow()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # MACOS CHANGE: Use a .png for the icon, which PyInstaller can convert to .icns
    # or specify a .icns file directly in the build script.
    ICON_FILENAME = "icon.png"

    # MACOS CHANGE: Removed the administrator check. It's not relevant on macOS.
    # Instead, the user must grant "Accessibility" permissions in System Settings for the hotkey.
    print("Starting AppManager and Hotkey listener...")

    manager = AppManager(app)

    # Setup and start the hotkey listener
    hotkey_listener = HotkeyListener()
    hotkey_listener.hotkey_activated.connect(manager.toggle_overlay_visibility)
    hotkey_listener.start()

    tray_icon = QSystemTrayIcon()
    try:
        icon_path = resource_path(ICON_FILENAME)
        tray_icon.setIcon(QIcon(icon_path))
    except Exception as e:
        print(f"Could not load icon from path '{icon_path}': {e}")

    tray_icon.setVisible(True)
    menu = QMenu()
    # MACOS CHANGE: Update hotkey text for the user
    show_action = QAction("Show/Hide Overlay (Cmd+Alt+M)")
    show_action.triggered.connect(manager.toggle_overlay_visibility)
    menu.addAction(show_action)
    quit_action = QAction("Quit")
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)
    tray_icon.setContextMenu(menu)
    tray_icon.setToolTip("LaTeX Inserter")
    print("LaTeX Inserter is running. Press Cmd+Alt+M to open the overlay.")
    print("IMPORTANT: On macOS, you must grant this app 'Accessibility' permissions")
    print("in 'System Settings > Privacy & Security' for the hotkey to work.")
    sys.exit(app.exec_())