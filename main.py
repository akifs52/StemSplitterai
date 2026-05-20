import os
import sys
import signal

from PySide6.QtCore import (
    QObject, Signal, Slot, Property, QUrl, QAbstractListModel,
    Qt, QTimer,
)
from PySide6.QtGui import QGuiApplication, QFont, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from backend.cuda_checker import has_cuda, gpu_name
from backend.splitter import Splitter
from backend.backend_controller import BackendController


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    QQuickStyle.setStyle("Fusion")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("AI Stem Splitter")
    app.setOrganizationName("StemSplitter")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
    if os.path.isdir(fonts_dir):
        for f in sorted(os.listdir(fonts_dir)):
            if f.endswith(".ttf"):
                path = os.path.join(fonts_dir, f)
                id = QFontDatabase.addApplicationFont(path)
                if id >= 0:
                    families = QFontDatabase.applicationFontFamilies(id)
                    print(f"  Loaded font: {families}")

    engine = QQmlApplicationEngine()

    controller = BackendController()
    engine.rootContext().setContextProperty("backend", controller)

    qml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml", "Main.qml")
    engine.load(QUrl.fromLocalFile(qml_path))

    if not engine.rootObjects():
        sys.exit(-1)

    exit_code = app.exec()
    controller.cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
