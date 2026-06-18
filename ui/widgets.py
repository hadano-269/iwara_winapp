from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QRectF, Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtWidgets import QWidget
import requests


class HanimateThumbLoader(QThread):
    loaded = pyqtSignal(object)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        if not self.url:
            self.loaded.emit(None)
            return
        try:
            r = requests.get(self.url, stream=True, timeout=10)
            if r.status_code == 200:
                img = QImage()
                img.loadFromData(r.content)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img).scaled(
                        100, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    self.loaded.emit(pixmap)
                    return
        except Exception:
            pass
        self.loaded.emit(None)


class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(48, 48)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def _rotate(self):
        self._angle = (self._angle + 15) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor('#2d2d2d'), 3, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        rect = QRectF(4, 4, 40, 40)
        painter.drawArc(rect, self._angle * 16, 90 * 16)
        painter.setPen(QPen(QColor('#d0d0d0'), 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, (self._angle + 90) * 16, 270 * 16)
        painter.end()

    def start_spinner(self):
        self.show()
        self._timer.start(50)

    def stop_spinner(self):
        self._timer.stop()
        self.hide()
