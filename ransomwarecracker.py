import sys
import random
import string
import time
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import win32gui
import win32con
import win32api

class Worker(QObject):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, hwnd_edit, length, delay):
        super().__init__()
        self.hwnd_edit = hwnd_edit
        self.length = length
        self.delay = delay
        self._running = True

    def stop(self):
        self._running = False

    def send_text(self, hwnd, text):
        # Send text char-by-char to the edit control
        for ch in text:
            if not self._running:
                break
            win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(ch), 0)
            time.sleep(0.01)
        # Send Enter key
        if self._running:
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

    def run(self):
        chars = string.ascii_letters + string.digits + string.punctuation
        while self._running:
            text = ''.join(random.choice(chars) for _ in range(self.length))
            self.update_signal.emit(text)
            self.send_text(self.hwnd_edit, text)
            time.sleep(self.delay)
        self.finished_signal.emit()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Direct Target Keyboard Spammer")
        self.setFixedSize(350, 220)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            background-color: #121212;
            color: #eee;
            font-family: Consolas, monospace;
        """)

        self.worker_thread = None
        self.worker = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        label = QLabel("Enter ransomware window title (exact):")
        self.window_title_input = QLineEdit()
        layout.addWidget(label)
        layout.addWidget(self.window_title_input)

        length_layout = QHBoxLayout()
        length_label = QLabel("String length:")
        self.length_input = QLineEdit("8")
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_input)
        layout.addLayout(length_layout)

        delay_layout = QHBoxLayout()
        delay_label = QLabel("Delay (seconds):")
        self.delay_input = QLineEdit("1")
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(self.delay_input)
        layout.addLayout(delay_layout)

        self.status_label = QLabel("Status: Waiting")
        layout.addWidget(self.status_label)

        self.start_btn = QPushButton("▶ Start Spamming")
        self.start_btn.clicked.connect(self.start_spamming)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_spamming)
        layout.addWidget(self.stop_btn)

        self.exit_btn = QPushButton("❌ Exit")
        self.exit_btn.clicked.connect(self.close)
        layout.addWidget(self.exit_btn)

        self.setLayout(layout)

    def find_edit_control(self, parent_hwnd):
        # Recursive search for edit control (textbox)
        edit_hwnds = []

        def enum_child(hwnd, param):
            class_name = win32gui.GetClassName(hwnd)
            if class_name == "Edit":
                edit_hwnds.append(hwnd)
            return True

        win32gui.EnumChildWindows(parent_hwnd, enum_child, None)
        if edit_hwnds:
            return edit_hwnds[0]  # Return first edit control found
        return None

    def start_spamming(self):
        title = self.window_title_input.text()
        if not title:
            QMessageBox.warning(self, "Error", "Please enter the ransomware window title.")
            return

        try:
            length = int(self.length_input.text())
            delay = float(self.delay_input.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter valid length and delay.")
            return

        hwnd = win32gui.FindWindow(None, title)
        if hwnd == 0:
            QMessageBox.warning(self, "Error", f"Window titled '{title}' not found.")
            return

        hwnd_edit = self.find_edit_control(hwnd)
        if hwnd_edit is None:
            QMessageBox.warning(self, "Error", "Could not find the input box (Edit control) in the window.")
            return

        self.status_label.setText(f"Status: Found input box, starting spam...")

        # Setup worker thread
        self.worker = Worker(hwnd_edit, length, delay)
        self.worker_thread = threading.Thread(target=self.worker.run)
        self.worker.update_signal.connect(self.update_status)
        self.worker.finished_signal.connect(self.spam_finished)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.worker_thread.start()

    def stop_spamming(self):
        if self.worker:
            self.worker.stop()
        if self.worker_thread:
            self.worker_thread.join()
        self.status_label.setText("Status: Stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_status(self, text):
        self.status_label.setText(f"Typing: {text}")

    def spam_finished(self):
        self.status_label.setText("Status: Finished")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        self.stop_spamming()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
