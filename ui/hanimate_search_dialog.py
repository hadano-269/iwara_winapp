from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem, QApplication, QWidget,
                             QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap
from download_manager import DownloadManager
from hanimate_scraper import CloudflareBlockedException
from workers.cloudflare_solver import CloudflareSolverWorker, BrowserCloseWorker
from workers.hanimate_worker import HanimateFetchWorker
from ui.widgets import HanimateThumbLoader, LoadingSpinner
import requests


class CloudflareDialog(QDialog):

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.bridge = None
        self.setWindowTitle('Cloudflare 验证')
        self.setMinimumSize(420, 200)
        self._cancelled = False
        self.setup_ui()
        self._start_auto_solver()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel('正在通过 Cloudflare 验证')
        title.setStyleSheet('font-size: 18px; font-weight: 600; color: #1a1a1a; background: transparent;')
        layout.addWidget(title)

        self.status_label = QLabel('正在自动验证，请稍候...')
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet('font-size: 13px; color: #555555; background: transparent;')
        layout.addWidget(self.status_label)

        self.progress_label = QLabel('')
        self.progress_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        layout.addWidget(self.progress_label)

        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(cancel_btn)

    def _start_auto_solver(self):
        self.solver = CloudflareSolverWorker(self.url)
        self.solver.progress.connect(self._on_progress)
        self.solver.solved.connect(self._on_solved)
        self.solver.failed.connect(self._on_failed)
        self.solver.start()

    def _on_progress(self, msg):
        self.progress_label.setText(msg)

    def _on_solved(self, bridge):
        self.bridge = bridge
        self.status_label.setText('验证成功！')
        self.accept()

    def _on_failed(self, err):
        self.status_label.setText(f'自动验证失败: {err}')
        self.status_label.setStyleSheet('font-size: 13px; color: #cc3300; background: transparent;')

    def _on_cancel(self):
        self._cancelled = True
        if hasattr(self, 'solver') and self.solver.isRunning():
            self.solver.cancel()
            self._close_worker = BrowserCloseWorker(self.solver.bridge)
            self._close_worker.start()
        self.reject()

    def closeEvent(self, event):
        if self._cancelled:
            if hasattr(self, 'solver') and self.solver.isRunning():
                self.solver.cancel()
                self._close_worker = BrowserCloseWorker(self.solver.bridge)
                self._close_worker.start()
        event.accept()


class HanimateSearchDialog(QDialog):

    def __init__(self, scraper, author_name, save_dir, parent=None):
        super().__init__(parent)
        self.scraper = scraper
        self.author_name = author_name
        self.save_dir = save_dir
        self.setWindowTitle(f'Hanimate 搜索 - {author_name}')
        self.setMinimumSize(750, 550)
        self.current_video_title = ''
        self.current_video_id = ''
        self.fetch_worker = None
        self.cf_dialog = None
        self._close_worker = None
        self._thumb_loaders = []
        self.setup_ui()
        QTimer.singleShot(100, self.start_search)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        self.title_label = QLabel(f'搜索: {self.author_name}')
        self.title_label.setObjectName('titleLabel')
        self.title_label.setStyleSheet('font-size: 18px; font-weight: 600; color: #1a1a1a; background: transparent;')
        layout.addWidget(self.title_label)

        self.results_list = QListWidget()
        self.results_list.setStyleSheet('QListWidget::item { height: 80px; padding: 10px; }')
        self.results_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.results_list)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        layout.addWidget(self.status_label)

        self.spinner = LoadingSpinner(self)
        self.spinner.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.spinner.isVisible():
            self._center_spinner()

    def _center_spinner(self):
        lx = self.results_list.x()
        ly = self.results_list.y()
        lw = self.results_list.width()
        lh = self.results_list.height()
        self.spinner.move(lx + (lw - self.spinner.width()) // 2,
                           ly + (lh - self.spinner.height()) // 2)

    def _show_spinner(self):
        self.results_list.clear()
        self._center_spinner()
        self.spinner.start_spinner()

    def _hide_spinner(self):
        self.spinner.stop_spinner()

    def start_search(self):
        if not self.scraper.has_bridge():
            self._show_spinner()
            self._handle_cf_block('', 'search')
            return
        self._show_spinner()
        self.status_label.setText('正在搜索 Hanimate...')
        self.fetch_worker = HanimateFetchWorker(
            self.scraper, 'search_videos', self.author_name)
        self.fetch_worker.status_update.connect(self._on_status_update)
        self.fetch_worker.finished.connect(self.on_search_done)
        self.fetch_worker.error.connect(self.on_search_error)
        self.fetch_worker.cf_blocked.connect(lambda url: self._handle_cf_block(url, 'search'))
        self.fetch_worker.start()

    def _on_status_update(self, msg):
        self.status_label.setText(msg)
        QApplication.processEvents()

    def _handle_cf_block(self, url, action_type):
        self._hide_spinner()
        if not url:
            url = self.scraper.BASE_URL + '/search?query=' + \
                  self.author_name.replace(' ', '%20')
        self.status_label.setText('被 Cloudflare 拦截，正在自动验证...')
        QApplication.processEvents()
        self.cf_dialog = CloudflareDialog(url, self)
        if self.cf_dialog.exec_() == QDialog.Accepted and self.cf_dialog.bridge:
            self.scraper.set_bridge(self.cf_dialog.bridge)
            self.status_label.setText('验证成功，正在继续...')
            self._show_spinner()
            if action_type == 'search':
                QTimer.singleShot(200, self.start_search)
            elif action_type == 'download':
                self._start_download_fetch()
        else:
            self.status_label.setText('验证取消')
            self.status_label.setStyleSheet('font-size: 12px; color: #cc3300; background: transparent;')
            if self.cf_dialog and self.cf_dialog.bridge:
                self._close_worker = BrowserCloseWorker(self.cf_dialog.bridge)
                self._close_worker.start()

    def on_search_done(self, results):
        self._async_close_bridge()
        self._hide_spinner()
        self.title_label.setText(f'搜索结果  ·  {self.author_name}  ·  {len(results)} 个视频')
        self.status_label.setStyleSheet('font-size: 12px; color: #999999; background: transparent;')
        if not results:
            self.status_label.setText('未找到相关视频')
            return
        self.status_label.setText('正在加载缩略图...')
        QApplication.processEvents()
        for item_data in results:
            self._add_result_item(item_data)
        self.status_label.setText('')

    def _add_result_item(self, item_data):
        item_widget = QWidget()
        item_widget.setStyleSheet('background: transparent;')
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 8, 8, 8)
        item_layout.setSpacing(12)

        thumb_label = QLabel()
        thumb_label.setFixedSize(100, 60)
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setStyleSheet('background-color: #f0f0f0; border-radius: 6px;')
        thumb_label.setText('...')
        self._load_thumb(item_data.get('thumbnail', ''), thumb_label)
        item_layout.addWidget(thumb_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        title = QLabel(item_data.get('title', '未知'))
        title.setStyleSheet('font-size: 13px; font-weight: 500; color: #1a1a1a; background: transparent;')
        title.setWordWrap(True)
        info_layout.addWidget(title)

        stats = QLabel(f'{item_data.get("duration", "")}  ·  {item_data.get("views", "")}  ·  {item_data.get("likes", "")}')
        stats.setStyleSheet('font-size: 11px; color: #999999; background: transparent;')
        info_layout.addWidget(stats)

        item_layout.addLayout(info_layout, 1)
        item_layout.addStretch()

        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())
        list_item.setData(Qt.UserRole, item_data)
        self.results_list.addItem(list_item)
        self.results_list.setItemWidget(list_item, item_widget)

    def _load_thumb(self, url, label):
        loader = HanimateThumbLoader(url)
        loader.loaded.connect(lambda pm, lbl=label: self._on_thumb_loaded(pm, lbl))
        self._thumb_loaders.append(loader)
        loader.start()

    def _on_thumb_loaded(self, pixmap, label):
        try:
            if pixmap:
                label.setPixmap(pixmap)
            else:
                label.setText('N/A')
        except RuntimeError:
            pass

    def on_search_error(self, err):
        self._async_close_bridge()
        self._hide_spinner()
        self.status_label.setText(f'搜索失败: {err}')
        self.status_label.setStyleSheet('font-size: 12px; color: #cc3300; background: transparent;')

    def on_item_clicked(self, list_item):
        item_data = list_item.data(Qt.UserRole)
        self.current_video_id = item_data.get('id', '')
        self.current_video_title = item_data.get('title', '')
        if not self.current_video_id:
            return
        self._start_download_fetch()

    def _start_download_fetch(self):
        if not self.current_video_id:
            return
        self._show_spinner()
        self.status_label.setText('正在获取下载链接...')
        self.fetch_worker = HanimateFetchWorker(
            self.scraper, 'get_download_links', self.current_video_id)
        self.fetch_worker.status_update.connect(self._on_status_update)
        self.fetch_worker.finished.connect(self.on_links_ready)
        self.fetch_worker.error.connect(self.on_links_error)
        self.fetch_worker.cf_blocked.connect(
            lambda url: self._handle_cf_block(url, 'download'))
        self.fetch_worker.start()

    def on_links_ready(self, links):
        self._async_close_bridge()
        self._hide_spinner()
        self.status_label.setText('')
        if not links:
            return
        self.show_quality_select(links)

    def on_links_error(self, err):
        self._async_close_bridge()
        self._hide_spinner()
        self.status_label.setText(f'获取下载链接失败: {err}')
        self.status_label.setStyleSheet('font-size: 12px; color: #cc3300; background: transparent;')

    def show_quality_select(self, links):
        dialog = QDialog(self)
        dialog.setWindowTitle('选择清晰度')
        dialog.setFixedSize(400, 300)
        dialog.setStyleSheet('background-color: #ffffff; color: #1a1a1a;')

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel('选择清晰度')
        title.setObjectName('titleLabel')
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet('font-size: 18px; font-weight: 600; color: #1a1a1a; background: transparent;')
        layout.addWidget(title)

        video_title = self.current_video_title
        for link_data in links:
            btn = QPushButton(f'{link_data["quality"]}  ·  {link_data["file_type"]}  ·  {link_data["file_size"]}')
            btn.setObjectName('downloadButton')
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, d=link_data, vt=video_title: self.start_hanimate_download(d, vt, dialog))
            layout.addWidget(btn)

        layout.addSpacing(8)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(dialog.close)
        layout.addWidget(cancel_btn)

        dialog.exec_()

    def start_hanimate_download(self, link_data, video_title, select_dialog):
        select_dialog.close()
        url = link_data['download_url']
        filename = link_data['download_url'].split('/')[-1].split('?')[0]
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        DownloadManager.get_instance().start_download(url, filename, self.save_dir, video_title)
        self.status_label.setText('已开始后台下载')

    def _async_close_bridge(self):
        if self.scraper.has_bridge():
            bridge = self.scraper._bridge
            self.scraper._bridge = None
            self._close_worker = BrowserCloseWorker(bridge)
            self._close_worker.start()

    def closeEvent(self, event):
        self._hide_spinner()
        self._async_close_bridge()
        event.accept()
