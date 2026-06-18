from PyQt5.QtCore import QThread, pyqtSignal
import os, requests, cloudscraper

class DownloadWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, save_path, filename=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.filename = filename
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if not self.filename:
                self.filename = self.url.split('/')[-1].split('?')[0]
            full_path = os.path.join(self.save_path, self.filename)
            if os.path.exists(full_path):
                self.finished.emit(full_path)
                return
            scraper = cloudscraper.create_scraper()
            r = scraper.get(self.url, stream=True)
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(full_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if self._is_cancelled:
                        os.remove(full_path)
                        self.error.emit('Download cancelled')
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(downloaded, total)
            self.finished.emit(full_path)
        except Exception as e:
            self.error.emit(str(e))
