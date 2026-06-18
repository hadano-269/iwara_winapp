from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QMessageBox, QApplication, QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.home_tab import HomeTab
from ui.favorites_tab import FavoritesTab
from ui.downloads_tab import DownloadsTab
from ui.profile_tab import ProfileTab
from ui.video_detail import VideoDetailDialog
from ui.login_dialog import LoginDialog
from api_client import ApiClient
from hanimate_scraper import HanimateScraper
from download_manager import DownloadManager
import os, json


SETTINGS_FILE = os.path.join(os.path.expanduser('~'), '.iwara_client_settings.json')


class AutoLoginWorker(QThread):
    login_done = pyqtSignal(bool, object)

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    def run(self):
        if not self.api_client.email or not self.api_client.password:
            self.login_done.emit(False, None)
            return
        try:
            r = self.api_client.login()
            if self.api_client.token:
                user_data = None
                try:
                    user_r = self.api_client.get_user()
                    if user_r.status_code == 200:
                        user_data = user_r.json()
                except Exception:
                    pass
                self.login_done.emit(True, user_data)
            else:
                self.login_done.emit(False, None)
        except Exception:
            self.login_done.emit(False, None)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Iwara 客户端')
        self.setMinimumSize(1220, 800)

        email, password, save_dir = self.load_settings()
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

        self.api_client = ApiClient(email, password)
        self.hanimate_scraper = HanimateScraper()

        self.setup_ui()
        self.check_auto_login()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.South)

        self.home_tab = HomeTab(self.api_client)
        self.home_tab.video_clicked.connect(self.open_video_detail)
        self.tab_widget.addTab(self.home_tab, '首页')

        self.favorites_tab = FavoritesTab(self.api_client)
        self.favorites_tab.video_clicked.connect(self.open_video_detail)
        self.tab_widget.addTab(self.favorites_tab, '关注')

        self.downloads_tab = DownloadsTab()
        self.tab_widget.addTab(self.downloads_tab, '下载')

        self.profile_tab = ProfileTab(self.api_client, self.save_dir)
        self.profile_tab.login_requested.connect(self.on_login_requested)
        self.profile_tab.logout_requested.connect(self.on_logout)
        self.profile_tab.save_dir_changed.connect(self.on_save_dir_changed)
        self.tab_widget.addTab(self.profile_tab, '我')

        layout.addWidget(self.tab_widget)

        self.statusBar().showMessage('欢迎使用 Iwara 客户端')

    def check_auto_login(self):
        if self.api_client.email and self.api_client.password:
            self.statusBar().showMessage('正在自动登录...')
            self.auto_login_worker = AutoLoginWorker(self.api_client)
            self.auto_login_worker.login_done.connect(self.on_auto_login_done)
            self.auto_login_worker.start()
        else:
            self.statusBar().showMessage('请登录后使用')
            self.home_tab.load_videos()

    def on_auto_login_done(self, success, user_data):
        if success:
            self.statusBar().showMessage('已自动登录')
            if user_data:
                self.profile_tab.set_user_data(user_data)
            else:
                self.profile_tab.update_profile_display()
            self.home_tab.load_videos()
            self.favorites_tab.load_subscriptions()
        else:
            self.statusBar().showMessage('自动登录失败，请手动登录')
            self.profile_tab.update_profile_display()

    def on_login_requested(self):
        if self.api_client.token:
            self.save_settings(self.api_client.email, self.api_client.password)
            try:
                r = self.api_client.get_user()
                if r.status_code == 200:
                    self.profile_tab.set_user_data(r.json())
            except Exception:
                pass
        self.home_tab.load_videos()
        self.favorites_tab.load_subscriptions()

    def on_logout(self):
        self.clear_settings()
        self.home_tab.load_videos()
        self.favorites_tab.load_subscriptions()
        self.statusBar().showMessage('已退出登录')

    def on_save_dir_changed(self, new_dir):
        self.save_dir = new_dir
        self.save_field('save_dir', new_dir)
        self.statusBar().showMessage(f'下载位置已更改为: {new_dir}')

    def open_video_detail(self, video_data):
        dialog = VideoDetailDialog(self.api_client, self.hanimate_scraper, video_data, self.save_dir, self)
        dialog.favorite_changed.connect(self.favorites_tab.load_subscriptions)
        dialog.exec_()

    def load_settings(self):
        default_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'iwara')
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('email', ''), data.get('password', ''), data.get('save_dir', default_dir)
        except Exception:
            pass
        return '', '', default_dir

    def save_settings(self, email, password):
        self._save_all(email, password, self.save_dir)

    def _save_all(self, email, password, save_dir):
        try:
            data = {'email': email, 'password': password, 'save_dir': save_dir}
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def save_field(self, key, value):
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            data[key] = value
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def clear_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                os.remove(SETTINGS_FILE)
        except Exception:
            pass
