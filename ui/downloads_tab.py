from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame, QProgressBar,
                             QTabWidget)
from PyQt5.QtCore import Qt
from download_manager import DownloadManager
import os


class DownloadItemWidget(QFrame):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setObjectName('videoCard')
        self.setFixedHeight(70)
        self.setup_ui()
        self.update_status()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 10, 12, 10)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.name_label = QLabel(self.task.display_name or self.task.filename)
        self.name_label.setStyleSheet('font-size: 13px; font-weight: 500; color: #1a1a1a; background: transparent;')
        self.name_label.setMaximumWidth(600)
        info_layout.addWidget(self.name_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        info_layout.addWidget(self.progress_bar)

        self.detail_label = QLabel('')
        self.detail_label.setStyleSheet('font-size: 11px; color: #999999; background: transparent;')
        info_layout.addWidget(self.detail_label)

        layout.addLayout(info_layout, 1)

        self.action_btn = QPushButton('')
        self.action_btn.setFixedWidth(70)
        self.action_btn.clicked.connect(self.on_action)
        layout.addWidget(self.action_btn)

    def update_status(self):
        self.detail_label.setStyleSheet('font-size: 11px; color: #999999; background: transparent;')
        status = self.task.status
        if status == 'downloading':
            self.progress_bar.setValue(self.task.progress)
            mb_down = self.task.downloaded / 1024 / 1024
            mb_total = self.task.total / 1024 / 1024 if self.task.total > 0 else 0
            if mb_total > 0:
                self.detail_label.setText(f'{mb_down:.1f} / {mb_total:.1f} MB  ·  {self.task.progress}%')
            else:
                self.detail_label.setText(f'{mb_down:.1f} MB')
            self.action_btn.setText('取消')
            self.action_btn.setEnabled(True)
        elif status == 'completed':
            self.progress_bar.setValue(100)
            size_mb = os.path.getsize(self.task.final_path) / 1024 / 1024 if self.task.final_path and os.path.exists(self.task.final_path) else 0
            self.detail_label.setText(f'已完成  ·  {size_mb:.1f} MB')
            self.action_btn.setText('打开')
            self.action_btn.setEnabled(True)
        elif status == 'failed':
            self.progress_bar.setValue(0)
            self.detail_label.setText(f'失败: {self.task.error_msg[:50]}')
            self.detail_label.setStyleSheet('font-size: 11px; color: #cc3300; background: transparent;')
            self.action_btn.setText('重试')
            self.action_btn.setEnabled(True)
        elif status == 'cancelled':
            self.progress_bar.setValue(0)
            self.detail_label.setText('已取消')
            self.action_btn.setText('重试')
            self.action_btn.setEnabled(True)
        else:
            self.progress_bar.setValue(0)
            self.detail_label.setText('等待中...')
            self.action_btn.setText('取消')
            self.action_btn.setEnabled(True)

    def on_action(self):
        status = self.task.status
        if status in ('downloading', 'pending'):
            DownloadManager.get_instance().cancel(self.task)
        elif status in ('failed', 'cancelled'):
            DownloadManager.get_instance().retry(self.task)
        elif status == 'completed':
            if self.task.final_path and os.path.exists(self.task.final_path):
                os.startfile(self.task.final_path)
            elif self.task.final_path:
                os.startfile(os.path.dirname(self.task.final_path))


class ActiveTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet('QScrollArea { background-color: transparent; border: none; }')

        self.container = QWidget()
        self.container.setStyleSheet('background: transparent;')
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setSpacing(8)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.empty_label = QLabel('暂无下载任务')
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet('font-size: 13px; color: #cccccc; background: transparent; padding: 40px;')
        layout.addWidget(self.empty_label)

    def get_list_layout(self):
        return self.list_layout

    def get_empty_label(self):
        return self.empty_label

    def clear_items(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()


class CompletedTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        self.clear_btn = QPushButton('清除记录')
        self.clear_btn.clicked.connect(self.on_clear)
        toolbar.addWidget(self.clear_btn)
        layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet('QScrollArea { background-color: transparent; border: none; }')

        self.container = QWidget()
        self.container.setStyleSheet('background: transparent;')
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setSpacing(8)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.empty_label = QLabel('暂无已完成的下载')
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet('font-size: 13px; color: #cccccc; background: transparent; padding: 40px;')
        layout.addWidget(self.empty_label)

    def on_clear(self):
        DownloadManager.get_instance().clear_completed()

    def get_list_layout(self):
        return self.list_layout

    def get_empty_label(self):
        return self.empty_label

    def clear_items(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()


class DownloadsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = DownloadManager.get_instance()
        self.active_widgets = {}
        self.completed_widgets = {}
        self.setup_ui()
        self.connect_signals()
        self.refresh_all()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel('下载管理')
        title.setStyleSheet('font-size: 18px; font-weight: 600; color: #1a1a1a; background: transparent; padding: 16px 20px 0 20px;')
        layout.addWidget(title)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.setTabPosition(QTabWidget.North)

        self.active_tab = ActiveTab()
        self.sub_tabs.addTab(self.active_tab, '进行中')

        self.completed_tab = CompletedTab()
        self.sub_tabs.addTab(self.completed_tab, '已完成')

        layout.addWidget(self.sub_tabs)

    def connect_signals(self):
        self.manager.task_added.connect(self.on_task_added)
        self.manager.task_progress.connect(self.on_task_progress)
        self.manager.task_completed.connect(self.on_task_completed)
        self.manager.task_failed.connect(self.on_task_failed)
        self.manager.tasks_cleared.connect(self.on_tasks_cleared)

    def refresh_all(self):
        self.active_tab.clear_items()
        self.completed_tab.clear_items()
        self.active_widgets = {}
        self.completed_widgets = {}
        for task in self.manager.tasks:
            self._add_item(task)
        self._update_empty_states()

    def _add_item(self, task):
        widget = DownloadItemWidget(task)
        if task.status in ('downloading', 'pending', 'failed', 'cancelled'):
            self.active_tab.get_list_layout().addWidget(widget)
            self.active_widgets[id(task)] = widget
        else:
            self.completed_tab.get_list_layout().insertWidget(0, widget)
            self.completed_widgets[id(task)] = widget

    def _move_to_completed(self, task):
        widget = self.active_widgets.pop(id(task), None)
        if widget:
            self.active_tab.get_list_layout().removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        self._add_item(task)

    def _update_empty_states(self):
        active_count = len(self.active_widgets)
        completed_count = len(self.completed_widgets)
        self.active_tab.get_empty_label().setVisible(active_count == 0)
        self.completed_tab.get_empty_label().setVisible(completed_count == 0)

    def on_task_added(self, task):
        self._add_item(task)
        self._update_empty_states()

    def on_task_progress(self, task):
        widget = self.active_widgets.get(id(task))
        if widget:
            widget.update_status()

    def on_task_completed(self, task):
        self._move_to_completed(task)
        self._update_empty_states()

    def on_task_failed(self, task):
        widget = self.active_widgets.get(id(task))
        if widget:
            widget.update_status()
        else:
            widget = self.completed_widgets.get(id(task))
            if widget:
                widget.update_status()
        self._update_empty_states()

    def on_tasks_cleared(self):
        self.completed_tab.clear_items()
        self.completed_widgets = {}
        self._update_empty_states()
