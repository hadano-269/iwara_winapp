from PyQt5.QtCore import QThread, pyqtSignal
import os

class ApiWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, api_client, method, *args, **kwargs):
        super().__init__()
        self.api_client = api_client
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            func = getattr(self.api_client, self.method)
            result = func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class HanimateSearchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, scraper, query):
        super().__init__()
        self.scraper = scraper
        self.query = query

    def run(self):
        try:
            results = self.scraper.search_videos(self.query)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class HanimateDownloadLinksWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, scraper, video_id):
        super().__init__()
        self.scraper = scraper
        self.video_id = video_id

    def run(self):
        try:
            links = self.scraper.get_download_links(self.video_id)
            self.finished.emit(links)
        except Exception as e:
            self.error.emit(str(e))


class ThumbnailWorker(QThread):
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str, str)

    def __init__(self, api_client, video_id, save_dir):
        super().__init__()
        self.api_client = api_client
        self.video_id = video_id
        self.save_dir = save_dir

    def run(self):
        try:
            path = self.api_client.download_video_thumbnail(self.video_id, self.save_dir)
            self.finished.emit(self.video_id, path)
        except Exception as e:
            self.error.emit(self.video_id, str(e))
