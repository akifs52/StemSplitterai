from PySide6.QtCore import QObject, Signal, Slot, QThread


class Task(QObject):
    progressChanged = Signal(int)
    statusChanged = Signal(str)
    finished = Signal(str, object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @Slot()
    def run(self):
        try:
            if self._cancelled:
                self.finished.emit("cancelled", None)
                return
            self.statusChanged.emit("Starting...")
            result = self.fn(*self.args, **self.kwargs)
            if self._cancelled:
                self.finished.emit("cancelled", None)
            else:
                self.finished.emit("ok", result)
        except Exception as e:
            self.finished.emit(str(e), None)


class WorkerPool(QObject):
    def __init__(self, parent=None, max_threads=4):
        super().__init__(parent)
        self.max_threads = max_threads
        self._queue = []
        self._active = {}

    def submit(self, task):
        thread = QThread()
        task.moveToThread(thread)
        thread.started.connect(task.run)
        task.finished.connect(lambda: self._cleanup(thread, task))
        thread.start()
        self._active[thread] = task

    def _cleanup(self, thread, task):
        task.deleteLater()
        thread.quit()
        thread.wait()
        thread.deleteLater()
        self._active.pop(thread, None)
