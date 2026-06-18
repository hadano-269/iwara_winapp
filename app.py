import sys, os, ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QByteArray
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer


def get_resource_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), '_internal')
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_resource_dir()
SVG_PATH = os.path.join(APP_DIR, 'resources', 'logo.svg')


def create_icon():
    renderer = QSvgRenderer(SVG_PATH)
    icon = QIcon()
    for size in [16, 32, 48, 64, 128, 256]:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def main():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('iwara.client.app')

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    app = QApplication(sys.argv)
    icon = create_icon()
    app.setWindowIcon(icon)

    qss_path = os.path.join(APP_DIR, 'resources', 'dark.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    from ui.main_window import MainWindow
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
