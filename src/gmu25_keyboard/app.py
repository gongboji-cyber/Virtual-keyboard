from __future__ import annotations
from pathlib import Path
from PyQt5.QtGui import QIcon

import sys
import time

from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __version__
from .input_engine import TypingConfig, type_text

def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS) / relative_path)
    return str(Path(__file__).resolve().parents[2] / relative_path)

class TypingWorker(QThread):
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int, int)
    finished_ok = pyqtSignal(float)
    failed = pyqtSignal(str)

    def __init__(self, text: str, config: TypingConfig):
        super().__init__()
        self.text = text
        self.config = config
        self.stop_event = Event()
        self.pause_event = Event()

    def run(self) -> None:
        start = time.perf_counter()
        try:
            type_text(
                text=self.text,
                config=self.config,
                stop_event=self.stop_event,
                pause_event=self.pause_event,
                progress_callback=lambda current, total: self.progress_changed.emit(current, total),
                status_callback=lambda message: self.status_changed.emit(message),
            )
            elapsed = time.perf_counter() - start
            self.finished_ok.emit(elapsed)
        except Exception as exc:
            self.failed.emit(str(exc))

    def stop(self) -> None:
        self.stop_event.set()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self.pause_event.set()
        else:
            self.pause_event.clear()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: TypingWorker | None = None
        self.is_paused = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle(__app_name__)
        self.setWindowIcon(QIcon(resource_path("assets/app.ico")))
        self.resize(780, 560)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("在这里输入需要模拟录入的文本。点击开始后，请在倒计时内切换到目标输入框。")

        self.speed_box = QComboBox()
        self.speed_box.addItem("10 字符/秒 - 稳定", 10)
        self.speed_box.addItem("20 字符/秒 - 推荐", 20)
        self.speed_box.addItem("40 字符/秒 - 较快", 40)
        self.speed_box.addItem("80 字符/秒 - 激进", 80)
        self.speed_box.setCurrentIndex(1)

        self.delay_box = QSpinBox()
        self.delay_box.setRange(1, 30)
        self.delay_box.setValue(3)
        self.delay_box.setSuffix(" 秒")

        self.topmost_check = QCheckBox("窗口置顶")
        self.topmost_check.stateChanged.connect(self._toggle_topmost)

        self.status_label = QLabel("就绪。")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.start_button = QPushButton("开始录入")
        self.pause_button = QPushButton("暂停")
        self.stop_button = QPushButton("停止")
        self.clear_button = QPushButton("清空文本")

        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.start_button.clicked.connect(self.start_typing)
        self.pause_button.clicked.connect(self.pause_or_resume)
        self.stop_button.clicked.connect(self.stop_typing)
        self.clear_button.clicked.connect(self.text_edit.clear)

        settings_group = QGroupBox("录入设置")
        grid = QGridLayout()
        grid.addWidget(QLabel("速度："), 0, 0)
        grid.addWidget(self.speed_box, 0, 1)
        grid.addWidget(QLabel("开始倒计时："), 1, 0)
        grid.addWidget(self.delay_box, 1, 1)
        grid.addWidget(self.topmost_check, 2, 1)
        settings_group.setLayout(grid)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_button)

        root = QVBoxLayout()
        root.addWidget(QLabel(f"{__app_name__} v{__version__}"))
        root.addWidget(self.text_edit, stretch=1)
        root.addWidget(settings_group)
        root.addLayout(button_layout)
        root.addWidget(self.progress_bar)
        root.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

    def _toggle_topmost(self) -> None:
        flags = self.windowFlags()
        if self.topmost_check.isChecked():
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def start_typing(self) -> None:
        text = self.text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "文本为空", "请先输入需要录入的文本。")
            return

        config = TypingConfig(
            chars_per_second=float(self.speed_box.currentData()),
            start_delay=int(self.delay_box.value()),
        )

        self.worker = TypingWorker(text=text, config=config)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.progress_changed.connect(self._update_progress)
        self.worker.finished_ok.connect(self._typing_finished)
        self.worker.failed.connect(self._typing_failed)

        self.progress_bar.setValue(0)
        self.is_paused = False
        self.pause_button.setText("暂停")
        self._set_running_state(True)
        self.worker.start()

    def pause_or_resume(self) -> None:
        if not self.worker:
            return
        self.is_paused = not self.is_paused
        self.worker.set_paused(self.is_paused)
        self.pause_button.setText("继续" if self.is_paused else "暂停")
        self.status_label.setText("已暂停。" if self.is_paused else "继续录入……")

    def stop_typing(self) -> None:
        if self.worker:
            self.worker.stop()
        self.status_label.setText("正在停止……")

    def _update_progress(self, current: int, total: int) -> None:
        if total <= 0:
            self.progress_bar.setValue(0)
            return
        self.progress_bar.setValue(round(current / total * 100))

    def _typing_finished(self, elapsed: float) -> None:
        self.status_label.setText(f"完成，用时 {elapsed:.2f} 秒。")
        self._set_running_state(False)
        self.worker = None

    def _typing_failed(self, message: str) -> None:
        self._set_running_state(False)
        self.worker = None
        self.status_label.setText("录入失败。")
        QMessageBox.critical(
            self,
            "录入失败",
            f"错误信息：\n{message}\n\n如果目标程序以管理员身份运行，请尝试右键以管理员身份运行本工具。",
        )

    def _set_running_state(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.pause_button.setEnabled(running)
        self.stop_button.setEnabled(running)
        self.speed_box.setEnabled(not running)
        self.delay_box.setEnabled(not running)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt method name
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1500)
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
