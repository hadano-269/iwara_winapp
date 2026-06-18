from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QFileDialog, QMessageBox,
                             QApplication)
from PyQt5.QtCore import Qt, pyqtSignal
from workers.download_worker import DownloadWorker


class DownloadDialog(QDialog):
    download_complete = pyqtSignal(str)

    def __init__(self, url, filename, save_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle('下载')
        self.setFixedSize(420, 160)
        self.worker = None
        self.url = url
        self.filename = filename
        self.save_dir = save_dir
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        self.filename_label = QLabel(self.filename)
        self.filename_label.setStyleSheet('font-size: 14px; font-weight: 500; color: #1a1a1a; background: transparent;')
        layout.addWidget(self.filename_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel('准备下载')
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.clicked.connect(self.cancel_download)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.start_download()

    def start_download(self):
        self.worker = DownloadWorker(self.url, self.save_dir, self.filename)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, downloaded, total):
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_bar.setValue(percent)
            mb_down = downloaded / 1024 / 1024
            mb_total = total / 1024 / 1024
            self.status_label.setText(f'{mb_down:.1f} / {mb_total:.1f} MB ({percent}%)')

    def on_finished(self, filepath):
        self.progress_bar.setValue(100)
        self.status_label.setText('下载完成')
        self.status_label.setStyleSheet('font-size: 12px; color: #2d2d2d; background: transparent;')
        self.cancel_btn.setText('关闭')
        self.download_complete.emit(filepath)

    def on_error(self, err):
        self.status_label.setText(f'下载失败: {err}')
        self.status_label.setStyleSheet('font-size: 12px; color: #cc3300; background: transparent;')
        self.cancel_btn.setText('关闭')

    def cancel_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText('正在取消...')
        else:
            self.close()
