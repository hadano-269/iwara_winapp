from PyQt5.QtCore import QThread, pyqtSignal
from hanimate_scraper import CloudflareBlockedException


class HanimateFetchWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    cf_blocked = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, scraper, method, *args):
        super().__init__()
        self.scraper = scraper
        self.method = method
        self.args = args

    def run(self):
        try:
            if self.method == 'search_videos':
                self.status_update.emit('正在获取搜索页面...')
            elif self.method == 'get_download_links':
                self.status_update.emit('正在获取下载页面...')
            func = getattr(self.scraper, self.method)
            result = func(*self.args)
            self.status_update.emit('正在解析...')
            self.finished.emit(result)
        except CloudflareBlockedException as e:
            self.cf_blocked.emit(e.url)
        except Exception as e:
            self.error.emit(str(e))
