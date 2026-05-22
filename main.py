import os
import sys
import signal


DEMUCS_CLI_ARG = "--stemsplit-demucs"


def _run_demucs_cli(argv):
    from backend.cuda_checker import _ensure_cuda_dll_path

    _ensure_cuda_dll_path()
    sys.argv = ["demucs", *argv]

    from demucs.separate import main as demucs_main

    demucs_main()


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == DEMUCS_CLI_ARG:
    _run_demucs_cli(sys.argv[2:])
    sys.exit(0)


from PySide6.QtCore import (
    QUrl,
)
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication


def _load_splash(app, base_dir):
    engine = QQmlApplicationEngine()
    engine.load(QUrl.fromLocalFile(os.path.join(base_dir, "qml", "Splash.qml")))
    if not engine.rootObjects():
        return None, engine
    splash = engine.rootObjects()[0]
    splash.show()
    app.processEvents()
    return splash, engine


def _set_splash_status(splash, app, status, progress=None):
    if splash is not None:
        splash.setProperty("statusText", status)
        if progress is not None:
            splash.setProperty("progressValue", progress)
    app.processEvents()


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("AI Stem Splitter")
    app.setOrganizationName("Akifs52")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    splash, splash_engine = _load_splash(app, base_dir)
    _set_splash_status(splash, app, "Initializing AI Engine...", 0.16)

    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Akifs52.AIStemSplitter.App"
        )

    icon_path = os.path.join(base_dir, "assets", "icons", "icon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    _set_splash_status(splash, app, "Loading fonts...", 0.30)
    fonts_dir = os.path.join(base_dir, "assets", "fonts")
    if os.path.isdir(fonts_dir):
        for f in sorted(os.listdir(fonts_dir)):
            if f.endswith(".ttf"):
                path = os.path.join(fonts_dir, f)
                id = QFontDatabase.addApplicationFont(path)
                if id >= 0:
                    families = QFontDatabase.applicationFontFamilies(id)
                    print(f"  Loaded font: {families}")

    _set_splash_status(splash, app, "Loading Qt interface...", 0.52)
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Fusion")
    engine = QQmlApplicationEngine()

    _set_splash_status(splash, app, "Preparing backend...", 0.72)
    from backend.backend_controller import BackendController

    controller = BackendController()
    engine.rootContext().setContextProperty("backend", controller)
    engine.rootContext().setContextProperty("audioEngine", controller)

    _set_splash_status(splash, app, "Opening workspace...", 0.92)
    qml_path = os.path.join(base_dir, "qml", "Main.qml")
    engine.load(QUrl.fromLocalFile(qml_path))

    if not engine.rootObjects():
        if splash is not None:
            splash.close()
        sys.exit(-1)

    window = engine.rootObjects()[0]
    if isinstance(window, QQuickWindow) and os.path.isfile(icon_path):
        window.setIcon(QIcon(icon_path))

    _set_splash_status(splash, app, "Ready", 1.0)
    if splash is not None:
        splash.close()
    splash_engine.deleteLater()
    exit_code = app.exec()
    controller.cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
