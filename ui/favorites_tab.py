from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QGridLayout, QLabel, QPushButton, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.video_card import VideoCard
from workers.api_worker import ApiWorker


class FavoritesTab(QWidget):
    video_clicked = pyqtSignal(dict)

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.current_page = 0
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['最新 (date)', '热门 (trending)', '播放量 (views)', '点赞数 (likes)', '人气 (popularity)'])
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        toolbar.addWidget(self.sort_combo)

        refresh_btn = QPushButton('刷新')
        refresh_btn.clicked.connect(self.load_subscriptions)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll)

        pagination = QHBoxLayout()
        pagination.setAlignment(Qt.AlignCenter)

        self.prev_btn = QPushButton('上一页')
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        pagination.addWidget(self.prev_btn)

        self.page_label = QLabel('第 1 页')
        pagination.addWidget(self.page_label)

        self.next_btn = QPushButton('下一页')
        self.next_btn.clicked.connect(self.next_page)
        pagination.addWidget(self.next_btn)

        layout.addLayout(pagination)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        layout.addWidget(self.status_label)

    def get_sort_value(self):
        return ['date', 'trending', 'views', 'likes', 'popularity'][self.sort_combo.currentIndex()]

    def on_sort_changed(self):
        self.current_page = 0
        self.load_subscriptions()

    def load_subscriptions(self):
        if not self.api_client.token:
            self.status_label.setText('请先登录以查看关注作者的作品')
            self.clear_grid()
            return
        self.status_label.setText('正在加载关注作者的作品...')
        self.clear_grid()
        if self.worker and self.worker.isRunning():
            self.worker.quit()
        sort = self.get_sort_value()
        self.worker = ApiWorker(self.api_client, 'get_videos', sort=sort, rating='all', page=self.current_page, limit=32, subscribed=True)
        self.worker.finished.connect(self.on_loaded)
        self.worker.error.connect(self.on_load_error)
        self.worker.start()

    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def on_loaded(self, result):
        self.status_label.setText('')
        try:
            data = result.json()
            results = data.get('results', []) if isinstance(data, dict) else []
            count = data.get('count', 0) if isinstance(data, dict) else len(results)
            self.render_videos(results)
            self.update_pagination(count)
            if not results:
                self.status_label.setText('暂无关注作者的作品')
        except Exception as e:
            self.status_label.setText(f'解析失败: {str(e)}')

    def on_load_error(self, err):
        self.status_label.setText(f'加载失败: {err}')

    def render_videos(self, videos):
        self.clear_grid()
        col = 0
        row = 0
        max_cols = 4
        for v in videos:
            card = VideoCard(v, self.api_client)
            card.clicked.connect(self.video_clicked.emit)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def update_pagination(self, total_count):
        page_size = 32
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        self.page_label.setText(f'第 {self.current_page + 1} / {total_pages} 页')
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_subscriptions()

    def next_page(self):
        self.current_page += 1
        self.load_subscriptions()
