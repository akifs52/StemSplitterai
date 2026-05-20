import os
import sys

from PySide6.QtCore import QObject, Signal, Slot, QThread, QProcess

from backend.progress_parser import ProgressParser
from backend.cuda_checker import has_cuda


class SplitWorker(QObject):
    progressChanged = Signal(int)
    statusChanged = Signal(str)
    finished = Signal(str, list)

    def __init__(self, file_path, output_dir):
        super().__init__()
        self.file_path = file_path
        self.output_dir = output_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @Slot()
    def run(self):
        try:
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            out_path = os.path.join(self.output_dir, "htdemucs", base_name)
            parser = ProgressParser()

            self.statusChanged.emit("Initializing Demucs...")
            self.progressChanged.emit(1)

            process = QProcess()
            process.setProcessChannelMode(QProcess.MergedChannels)

            program = sys.executable or "python"
            args = [
                "-m",
                "demucs",
                "--two-stems=vocals",
                "-o",
                self.output_dir,
            ]
            if has_cuda():
                args += ["--device", "cuda"]
            else:
                args += ["--device", "cpu"]
            args.append(self.file_path)

            process.start(program, args)

            if not process.waitForStarted(30000):
                err = process.errorString()
                self.finished.emit(f"Failed to start Demucs: {err}", [])
                return

            while not self._cancelled:
                if not process.waitForReadyRead(200):
                    if process.state() == QProcess.NotRunning:
                        break
                    continue

                data = process.readAll().data().decode("utf-8", errors="replace")
                for line in data.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    progress, status = parser.parse_line(line)
                    self.progressChanged.emit(min(progress, 99))
                    self.statusChanged.emit(status)

            process.waitForFinished(30000)
            exit_code = process.exitCode()

            if self._cancelled:
                self.finished.emit("Cancelled", [])
                return

            if exit_code != 0:
                stderr = process.readAllStandardError().data().decode("utf-8", errors="replace")
                self.finished.emit(f"Demucs failed (code {exit_code}): {stderr[:200]}", [])
                return

            stems = []
            if os.path.isdir(out_path):
                for f in sorted(os.listdir(out_path)):
                    if f.endswith((".wav", ".mp3", ".flac")):
                        full_path = os.path.join(out_path, f)
                        stem_name = os.path.splitext(f)[0]
                        stems.append({"name": stem_name, "path": full_path})

            self.progressChanged.emit(100)
            self.statusChanged.emit("Complete!")
            self.finished.emit("ok", stems)

        except Exception as e:
            self.finished.emit(f"Error: {str(e)}", [])


class Splitter(QObject):
    progressChanged = Signal(int)
    statusChanged = Signal(str)
    finished = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None

    @Slot(str)
    def split(self, file_path):
        if not os.path.isfile(file_path):
            self.finished.emit(f"File not found: {file_path}", [])
            return

        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "separated")
        os.makedirs(output_dir, exist_ok=True)

        self._thread = QThread()
        self._worker = SplitWorker(file_path, output_dir)
        self._worker.moveToThread(self._thread)

        self._worker.progressChanged.connect(self.progressChanged)
        self._worker.statusChanged.connect(self.statusChanged)
        self._worker.finished.connect(self._on_finished)
        self._thread.started.connect(self._worker.run)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self, status, stems):
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.quit()
            self._thread = None
        self.finished.emit(status, stems)

    @Slot()
    def cancel(self):
        if self._worker:
            self._worker.cancel()
