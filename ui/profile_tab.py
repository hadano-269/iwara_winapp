from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QMessageBox, QFormLayout,
                             QGroupBox, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.login_dialog import LoginDialog
import os


class ProfileTab(QWidget):
    login_requested = pyqtSignal()
    logout_requested = pyqtSignal()
    save_dir_changed = pyqtSignal(str)

    def __init__(self, api_client, save_dir, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.save_dir = save_dir
        self.setup_ui()
        self.update_profile_display()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(24, 24, 24, 24)

        self.profile_group = QGroupBox('账号信息')
        self.profile_group.setStyleSheet('QGroupBox { color: #1a1a1a; font-weight: 600; font-size: 14px; border: 1px solid #ececec; border-radius: 10px; margin-top: 12px; padding-top: 20px; } QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0px 6px; background-color: #ffffff; }')
        profile_layout = QFormLayout()
        profile_layout.setSpacing(14)
        profile_layout.setContentsMargins(16, 10, 16, 16)

        self.username_label = QLabel('未登录')
        self.username_label.setObjectName('titleLabel')
        self.username_label.setStyleSheet('font-size: 18px; font-weight: 600; color: #1a1a1a; background: transparent;')
        profile_layout.addRow('用户名', self.username_label)

        self.email_label = QLabel('-')
        self.email_label.setStyleSheet('font-size: 13px; color: #2d2d2d; background: transparent;')
        profile_layout.addRow('邮箱', self.email_label)

        self.role_label = QLabel('-')
        self.role_label.setStyleSheet('font-size: 13px; color: #2d2d2d; background: transparent;')
        profile_layout.addRow('角色', self.role_label)

        self.created_label = QLabel('-')
        self.created_label.setStyleSheet('font-size: 13px; color: #2d2d2d; background: transparent;')
        profile_layout.addRow('注册时间', self.created_label)

        self.profile_group.setLayout(profile_layout)
        layout.addWidget(self.profile_group)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.login_btn = QPushButton('登录')
        self.login_btn.setObjectName('downloadButton')
        self.login_btn.clicked.connect(self.do_login)
        btn_layout.addWidget(self.login_btn)

        self.logout_btn = QPushButton('退出登录')
        self.logout_btn.clicked.connect(self.do_logout)
        self.logout_btn.setEnabled(False)
        btn_layout.addWidget(self.logout_btn)

        refresh_btn = QPushButton('刷新信息')
        refresh_btn.clicked.connect(self.refresh_profile)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.download_group = QGroupBox('下载设置')
        self.download_group.setStyleSheet('QGroupBox { color: #1a1a1a; font-weight: 600; font-size: 14px; border: 1px solid #ececec; border-radius: 10px; margin-top: 12px; padding-top: 20px; } QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0px 6px; background-color: #ffffff; }')
        download_layout = QVBoxLayout()
        download_layout.setSpacing(12)
        download_layout.setContentsMargins(16, 10, 16, 16)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        self.download_path_label = QLabel(self.save_dir)
        self.download_path_label.setWordWrap(True)
        self.download_path_label.setStyleSheet('font-size: 13px; color: #555555; padding: 10px 12px; background-color: #f0f0f0; border-radius: 8px;')
        path_row.addWidget(self.download_path_label, 1)

        change_btn = QPushButton('更改位置')
        change_btn.clicked.connect(self.change_download_dir)
        path_row.addWidget(change_btn)
        download_layout.addLayout(path_row)

        open_btn = QPushButton('打开下载目录')
        open_btn.clicked.connect(self.open_download_dir)
        download_layout.addWidget(open_btn)

        self.download_group.setLayout(download_layout)
        layout.addWidget(self.download_group)

        layout.addStretch()

    def update_profile_display(self):
        if self.api_client.token:
            self.login_btn.setEnabled(False)
            self.logout_btn.setEnabled(True)
            if self.api_client.email:
                self.email_label.setText(self.api_client.email)
        else:
            self.username_label.setText('未登录')
            self.email_label.setText('-')
            self.role_label.setText('-')
            self.created_label.setText('-')
            self.login_btn.setEnabled(True)
            self.logout_btn.setEnabled(False)

    def set_user_data(self, user_data):
        if user_data:
            user = user_data.get('user', user_data)
            username = user.get('name', user.get('username', '未知'))
            self.username_label.setText(username)
            email = user.get('email', self.api_client.email or '-')
            self.email_label.setText(email)
            role = user.get('role', '-')
            self.role_label.setText(role)
            created = user.get('createdAt', '-')
            self.created_label.setText(created)
        self.update_profile_display()

    def do_login(self):
        dialog = LoginDialog(self.api_client, self)
        if dialog.exec_() == LoginDialog.Accepted:
            self.login_requested.emit()

    def do_logout(self):
        self.api_client.token = None
        self.api_client.email = None
        self.api_client.password = None
        self.username_label.setText('未登录')
        self.email_label.setText('-')
        self.role_label.setText('-')
        self.created_label.setText('-')
        self.update_profile_display()
        self.logout_requested.emit()

    def refresh_profile(self):
        if not self.api_client.token:
            QMessageBox.information(self, '提示', '请先登录')
            return
        self.login_requested.emit()

    def change_download_dir(self):
        new_dir = QFileDialog.getExistingDirectory(self, '选择下载目录', self.save_dir)
        if new_dir:
            self.save_dir = new_dir
            self.download_path_label.setText(new_dir)
            self.save_dir_changed.emit(new_dir)

    def open_download_dir(self):
        path = self.save_dir
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        os.startfile(path)

