from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QMessageBox, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon


class LoginDialog(QDialog):
    login_success = pyqtSignal(str, str, object)

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setWindowTitle('登录 Iwara')
        self.setMinimumSize(440, 340)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel('登录 Iwara')
        title.setObjectName('titleLabel')
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet('font-size: 22px; font-weight: 600; color: #1a1a1a; background: transparent;')
        layout.addWidget(title)

        subtitle = QLabel('使用你的账号继续')
        subtitle.setStyleSheet('font-size: 13px; color: #999999; background: transparent;')
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('邮箱')
        self.email_input.setText(self.api_client.email or '')
        form.addRow('邮箱', self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('密码')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText(self.api_client.password or '')
        form.addRow('密码', self.password_input)

        layout.addLayout(form)

        layout.addSpacing(8)

        self.login_btn = QPushButton('登录')
        self.login_btn.setObjectName('downloadButton')
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.do_login)
        layout.addWidget(self.login_btn)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        layout.addWidget(self.status_label)

    def do_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        if not email or not password:
            self.status_label.setText('请填写邮箱和密码')
            self.status_label.setStyleSheet('color: #cc3300;')
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText('正在登录...')
        self.status_label.setText('正在连接服务器...')
        self.status_label.setStyleSheet('color: #999999;')

        try:
            r = self.api_client.login(email, password)
            if self.api_client.token:
                self.status_label.setText('登录成功')
                self.status_label.setStyleSheet('color: #2d2d2d;')
                user_data = r.json()
                self.login_success.emit(email, password, user_data)
                self.accept()
            else:
                msg = r.json().get('message', '登录失败，请检查邮箱和密码')
                self.status_label.setText(msg)
                self.status_label.setStyleSheet('color: #cc3300;')
        except Exception as e:
            self.status_label.setText(f'网络错误: {str(e)}')
            self.status_label.setStyleSheet('color: #cc3300;')

        self.login_btn.setEnabled(True)
        self.login_btn.setText('登录')
