from PyQt5.QtCore import QObject, pyqtSignal
from workers.download_worker import DownloadWorker
import os


def sanitize_filename(name):
    invalid = '<>:"/\\|?*'
    for ch in invalid:
        name = name.replace(ch, '_')
    return name.strip().rstrip('.')


class DownloadTask:
    def __init__(self, url, filename, save_dir, display_name):
        self.url = url
        self.filename = filename
        self.save_dir = save_dir
        self.display_name = display_name
        self.worker = None
        self.status = 'pending'
        self.progress = 0
        self.downloaded = 0
        self.total = 0
        self.error_msg = ''
        self.final_path = ''


class DownloadManager(QObject):
    task_added = pyqtSignal(object)
    task_progress = pyqtSignal(object)
    task_completed = pyqtSignal(object)
    task_failed = pyqtSignal(object)
    tasks_cleared = pyqtSignal()

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.tasks = []

    def start_download(self, url, filename, save_dir, display_name):
        task = DownloadTask(url, filename, save_dir, display_name)
        self.tasks.append(task)
        self._start_worker(task)
        self.task_added.emit(task)
        return task

    def _start_worker(self, task):
        task.status = 'downloading'
        task.progress = 0
        task.error_msg = ''
        task.worker = DownloadWorker(task.url, task.save_dir, task.filename)
        task.worker.progress.connect(lambda d, t, tk=task: self._on_progress(tk, d, t))
        task.worker.finished.connect(lambda path, tk=task: self._on_finished(tk, path))
        task.worker.error.connect(lambda err, tk=task: self._on_error(tk, err))
        task.worker.start()

    def _on_progress(self, task, downloaded, total):
        if task.status == 'cancelled':
            return
        task.downloaded = downloaded
        task.total = total
        if total > 0:
            task.progress = int(downloaded * 100 / total)
        self.task_progress.emit(task)

    def _on_finished(self, task, filepath):
        if task.status == 'cancelled':
            return
        if task.display_name:
            ext = os.path.splitext(filepath)[1]
            new_name = sanitize_filename(task.display_name) + ext
            new_path = os.path.join(os.path.dirname(filepath), new_name)
            if new_path != filepath:
                if os.path.exists(new_path):
                    os.remove(new_path)
                try:
                    os.rename(filepath, new_path)
                    filepath = new_path
                except Exception:
                    pass
        task.final_path = filepath
        task.status = 'completed'
        task.progress = 100
        self.task_completed.emit(task)

    def _on_error(self, task, err):
        if task.status == 'cancelled':
            return
        if 'cancelled' in err.lower():
            task.status = 'cancelled'
        else:
            task.status = 'failed'
            task.error_msg = err
        self.task_failed.emit(task)

    def retry(self, task):
        old_path = os.path.join(task.save_dir, task.filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
        self._start_worker(task)
        self.task_progress.emit(task)

    def cancel(self, task):
        if task.status in ('downloading', 'pending'):
            task.status = 'cancelled'
            if task.worker and task.worker.isRunning():
                task.worker.cancel()
            self.task_failed.emit(task)

    def clear_completed(self):
        self.tasks = [t for t in self.tasks if t.status != 'completed']
        self.tasks_cleared.emit()
