from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QRect, QRectF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPainterPath
import requests


_thumb_cache = {}

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.iwara.tv/',
}


class ThumbnailLoader(QThread):
    loaded = pyqtSignal(str, bytes)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        if self.url in _thumb_cache:
            cached = _thumb_cache[self.url]
            if cached is not None:
                self.loaded.emit(self.url, cached)
            return
        try:
            r = requests.get(self.url, headers=BROWSER_HEADERS, timeout=15)
            if r.status_code == 200 and len(r.content) > 100:
                _thumb_cache[self.url] = r.content
                self.loaded.emit(self.url, r.content)
            else:
                _thumb_cache[self.url] = None
        except Exception:
            _thumb_cache[self.url] = None


class VideoCard(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, video_data, api_client, parent=None):
        super().__init__(parent)
        self.video_data = video_data
        self.api_client = api_client
        self.setObjectName('videoCard')
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(280, 210)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.thumb_url = None
        self.thumb_thread = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(262, 120)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet('background-color: #f0f0f0; border-radius: 8px;')
        thumb_container = QHBoxLayout()
        thumb_container.setContentsMargins(0, 0, 0, 0)
        thumb_container.addStretch()
        thumb_container.addWidget(self.thumb_label)
        thumb_container.addStretch()
        layout.addLayout(thumb_container)

        thumb_url = self._build_thumb_url()
        if thumb_url:
            self.thumb_url = thumb_url
            if thumb_url in _thumb_cache:
                cached = _thumb_cache[thumb_url]
                if cached is not None:
                    self._apply_thumb(cached)
                else:
                    self.thumb_label.setText('加载失败')
            else:
                self.thumb_label.setText('')
                self.thumb_thread = ThumbnailLoader(thumb_url)
                self.thumb_thread.loaded.connect(self._on_thumb_loaded)
                self.thumb_thread.start()
        else:
            self.thumb_label.setText('无缩略图')

        title = self.video_data.get('title', '未知标题')
        title_label = QLabel(title[:40] + '...' if len(title) > 40 else title)
        title_label.setWordWrap(True)
        title_label.setMaximumHeight(40)
        title_label.setStyleSheet('font-size: 13px; font-weight: 500; color: #1a1a1a; background: transparent;')
        layout.addWidget(title_label)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        user = self.video_data.get('user', {})
        author_name = user.get('name', '未知作者') if isinstance(user, dict) else '未知作者'
        author_label = QLabel(author_name)
        author_label.setStyleSheet('font-size: 11px; color: #999999; background: transparent;')
        meta_layout.addWidget(author_label)

        meta_layout.addStretch()

        views = self.video_data.get('numViews', 0)
        views_label = QLabel(f'{views} 播放')
        views_label.setStyleSheet('font-size: 11px; color: #cccccc; background: transparent;')
        meta_layout.addWidget(views_label)

        likes = self.video_data.get('numLikes', 0)
        likes_label = QLabel(f'{likes} 赞')
        likes_label.setStyleSheet('font-size: 11px; color: #cccccc; background: transparent;')
        meta_layout.addWidget(likes_label)

        layout.addLayout(meta_layout)

    def _build_thumb_url(self):
        file_info = self.video_data.get('file')
        thumb_idx = self.video_data.get('thumbnail')
        if isinstance(file_info, dict) and file_info.get('id') and thumb_idx is not None:
            file_id = file_info['id']
            thumb_str = f'{thumb_idx:02d}'
            return f'https://i.iwara.tv/image/original/{file_id}/thumbnail-{thumb_str}.jpg'
        return None

    def _on_thumb_loaded(self, url, data):
        if url == self.thumb_url and data:
            self._apply_thumb(data)

    def _apply_thumb(self, data):
        try:
            qimage = QImage()
            qimage.loadFromData(data)
            if not qimage.isNull():
                pixmap = QPixmap.fromImage(qimage)
                target_w, target_h = 262, 120
                scaled = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                x = (scaled.width() - target_w) // 2
                y = (scaled.height() - target_h) // 2
                cropped = scaled.copy(x, y, target_w, target_h)

                rounded = QPixmap(cropped.size())
                rounded.fill(Qt.transparent)
                painter = QPainter(rounded)
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, target_w, target_h), 8, 8)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, cropped)
                painter.end()
                self.thumb_label.setPixmap(rounded)
            else:
                self.thumb_label.setText('加载失败')
        except RuntimeError:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.video_data)
        super().mousePressEvent(event)
