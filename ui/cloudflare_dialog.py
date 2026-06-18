from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QWidget, QApplication,
                             QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from workers.cloudflare_solver import CloudflareSolverWorker
import webbrowser


class CloudflareDialog(QDialog):
    cookies_ready = pyqtSignal(dict, str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.cookies = {}
        self.user_agent = ''
        self.solver_worker = None
        self.setWindowTitle('Cloudflare 验证')
        self.setMinimumSize(480, 320)
        self.setup_ui()
        self._start_auto_solver()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel('Cloudflare 验证')
        title.setStyleSheet('font-size: 18px; font-weight: 600; color: #1a1a1a; background: transparent;')
        layout.addWidget(title)

        self.status_label = QLabel('正在自动验证，请稍候...')
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet('font-size: 13px; color: #555555; background: transparent;')
        layout.addWidget(self.status_label)

        self.progress_label = QLabel('')
        self.progress_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        layout.addWidget(self.progress_label)

        divider = QLabel('— 自动验证失败？手动输入 —')
        divider.setAlignment(Qt.AlignCenter)
        divider.setStyleSheet('font-size: 12px; color: #cccccc; background: transparent; padding: 8px;')
        layout.addWidget(divider)

        manual_group = QGroupBox('手动输入 Cookie 和 User-Agent')
        manual_layout = QFormLayout()
        manual_layout.setSpacing(10)

        self.cookie_input = QLineEdit()
        self.cookie_input.setPlaceholderText('cf_clearance 的值')
        self.cookie_input.setStyleSheet('font-size: 13px;')
        manual_layout.addRow('Cookie:', self.cookie_input)

        self.ua_input = QLineEdit()
        self.ua_input.setPlaceholderText('navigator.userAgent 的值')
        self.ua_input.setStyleSheet('font-size: 13px;')
        manual_layout.addRow('UA:', self.ua_input)

        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        submit_btn = QPushButton('使用手动输入')
        submit_btn.clicked.connect(self._on_manual_submit)
        btn_layout.addWidget(submit_btn)

        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _start_auto_solver(self):
        self.solver_worker = CloudflareSolverWorker(self.url)
        self.solver_worker.progress.connect(self._on_solver_progress)
        self.solver_worker.solved.connect(self._on_solver_solved)
        self.solver_worker.failed.connect(self._on_solver_failed)
        self.solver_worker.start()

    def _on_solver_progress(self, msg):
        self.progress_label.setText(msg)

    def _on_solver_solved(self, cookies, ua):
        self.cookies = cookies
        self.user_agent = ua
        self.status_label.setText('验证成功！')
        self.status_label.setStyleSheet('font-size: 13px; color: #2d2d2d; background: transparent;')
        self.cookies_ready.emit(cookies, ua)
        self.accept()

    def _on_solver_failed(self, err):
        self.status_label.setText(f'自动验证失败: {err}')
        self.status_label.setStyleSheet('font-size: 13px; color: #cc3300; background: transparent;')
        self.progress_label.setText('请在下方手动输入 Cookie 和 User-Agent')

    def _on_manual_submit(self):
        cookie_text = self.cookie_input.text().strip()
        ua_text = self.ua_input.text().strip()
        if not cookie_text or not ua_text:
            return
        if '=' in cookie_text:
            for pair in cookie_text.split(';'):
                pair = pair.strip()
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    self.cookies[k.strip()] = v.strip()
        else:
            self.cookies['cf_clearance'] = cookie_text
        self.user_agent = ua_text
        if self.cookies and self.user_agent:
            self.cookies_ready.emit(self.cookies, self.user_agent)
            self.accept()

    def _on_cancel(self):
        if self.solver_worker and self.solver_worker.isRunning():
            self.solver_worker.cancel()
            self.solver_worker.quit()
        self.reject()
