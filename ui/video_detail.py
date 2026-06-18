from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWebEngineWidgets import QWebEngineView
from workers.api_worker import ApiWorker
from ui.hanimate_search_dialog import HanimateSearchDialog
from download_manager import DownloadManager
import requests, os, json


class VideoDetailDialog(QDialog):
    favorite_changed = pyqtSignal()

    def __init__(self, api_client, hanimate_scraper, video_data, save_dir, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.hanimate_scraper = hanimate_scraper
        self.video_data = video_data
        self.video_id = video_data.get('id', '')
        self.save_dir = save_dir
        self.full_video_data = None
        self.setWindowTitle('视频详情')
        self.setMinimumSize(800, 600)
        self.worker = None
        self.is_favorite = False
        self.setup_ui()
        self.load_video_detail()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(350)
        layout.addWidget(self.web_view)

        title = self.video_data.get('title', '未知标题')
        self.title_label = QLabel(title)
        self.title_label.setObjectName('titleLabel')
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet('font-size: 22px; font-weight: 600; color: #1a1a1a; background: transparent; border: none; padding: 0;')
        layout.addWidget(self.title_label)

        author_layout = QHBoxLayout()
        author_layout.setSpacing(12)
        user = self.video_data.get('user', {})
        author_name = user.get('name', '未知作者') if isinstance(user, dict) else '未知作者'
        self.author_label = QLabel(author_name)
        self.author_label.setStyleSheet('font-size: 13px; color: #2d2d2d; font-weight: 500; background: transparent;')
        author_layout.addWidget(self.author_label)

        hanimate_btn = QPushButton('在 Hanimate 上查找')
        hanimate_btn.setObjectName('hanimateButton')
        hanimate_btn.setCursor(Qt.PointingHandCursor)
        hanimate_btn.clicked.connect(self.search_hanimate)
        author_layout.addWidget(hanimate_btn)
        author_layout.addStretch()
        layout.addLayout(author_layout)

        stats_layout = QHBoxLayout()
        views = self.video_data.get('numViews', 0)
        likes = self.video_data.get('numLikes', 0)
        stats_label = QLabel(f'{views} 播放  ·  {likes} 赞')
        stats_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        stats_layout.addWidget(stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        body = self.video_data.get('body', '')
        if body:
            desc_label = QLabel(body[:200])
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet('font-size: 12px; color: #777777; background: transparent; border: none; padding: 0;')
            layout.addWidget(desc_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.download_btn = QPushButton('下载视频')
        self.download_btn.setObjectName('downloadButton')
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(self.download_video)
        btn_layout.addWidget(self.download_btn)

        self.favorite_btn = QPushButton('收藏')
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        btn_layout.addWidget(self.favorite_btn)

        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        layout.addWidget(self.status_label)

    def load_video_detail(self):
        if self.video_id:
            url = f'https://iwara.tv/video/{self.video_id}'
            self.web_view.load(QUrl(url))

    def download_video(self):
        if not self.video_id:
            return
        self.status_label.setText('正在获取下载信息...')
        self.worker = ApiWorker(self.api_client, 'get_video_download_info', self.video_id)
        self.worker.finished.connect(self.on_download_info_ready)
        self.worker.error.connect(self.on_download_info_error)
        self.worker.start()

    def on_download_info_ready(self, result):
        self.status_label.setText('')
        if not result or not result.get('resources'):
            QMessageBox.warning(self, '提示', '未找到下载资源')
            return
        resources = result['resources']
        video_title = self.video_data.get('title', self.video_id)
        if len(resources) == 1:
            resource = resources[0]
            url = resource['download_url']
            filename = self.video_id + '.' + resource['file_type']
            DownloadManager.get_instance().start_download(url, filename, self.save_dir, video_title)
            self.status_label.setText('已开始后台下载')
        else:
            self._show_quality_select(resources, video_title)

    def _show_quality_select(self, resources, video_title):
        dialog = QDialog(self)
        dialog.setWindowTitle('选择清晰度')
        dialog.setFixedSize(400, 250)
        dialog.setStyleSheet('background-color: #ffffff; color: #1a1a1a;')

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel('选择清晰度')
        title.setObjectName('titleLabel')
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet('font-size: 18px; font-weight: 600; color: #1a1a1a; background: transparent;')
        layout.addWidget(title)

        for res in resources:
            btn = QPushButton(f'{res["name"]} ({res["file_type"]})')
            btn.setObjectName('downloadButton')
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, r=res, vt=video_title: self._start_iwara_download(r, vt, dialog))
            layout.addWidget(btn)

        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(dialog.close)
        layout.addWidget(cancel_btn)
        dialog.exec_()

    def _start_iwara_download(self, resource, video_title, select_dialog):
        select_dialog.close()
        url = resource['download_url']
        filename = self.video_id + '.' + resource['file_type']
        DownloadManager.get_instance().start_download(url, filename, self.save_dir, video_title)
        self.status_label.setText('已开始后台下载')

    def on_download_info_error(self, err):
        self.status_label.setText(f'获取下载信息失败: {err}')
        QMessageBox.warning(self, '错误', f'获取下载信息失败: {err}')

    def search_hanimate(self):
        user = self.video_data.get('user', {})
        author_name = user.get('name', '') if isinstance(user, dict) else ''
        if not author_name:
            QMessageBox.warning(self, '提示', '无法获取作者名')
            return
        dialog = HanimateSearchDialog(self.hanimate_scraper, author_name, self.save_dir, self)
        dialog.exec_()

    def toggle_favorite(self):
        if not self.api_client.token:
            QMessageBox.warning(self, '提示', '请先登录后再收藏')
            return
        if self.is_favorite:
            self.worker = ApiWorker(self.api_client, 'remove_favorite', self.video_id)
            self.favorite_btn.setText('收藏')
            self.is_favorite = False
        else:
            self.worker = ApiWorker(self.api_client, 'add_favorite', self.video_id)
            self.favorite_btn.setText('取消收藏')
            self.is_favorite = True
        self.worker.finished.connect(lambda r: self.favorite_changed.emit())
        self.worker.error.connect(lambda e: QMessageBox.warning(self, '错误', e))
        self.worker.start()
