import os
import sys
import time
import tempfile
import shutil

from PySide6.QtCore import QObject, Signal, Slot, QThread, QProcess

from backend.progress_parser import ProgressParser
from backend.cuda_checker import has_cuda


class SplitWorker(QObject):
    progressChanged = Signal(int)
    statusChanged = Signal(str)
    finished = Signal(str, list)

    def __init__(self, file_path, output_dir, original_stem=None, models=None):
        super().__init__()
        self.file_path = file_path
        self.output_dir = output_dir
        self.original_stem = original_stem
        self.models = models or ["htdemucs_6s", "htdemucs"]
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _run_model(self, model_name):
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        out_path = os.path.join(self.output_dir, model_name, base_name)
        parser = ProgressParser()

        self.statusChanged.emit(f"Initializing Demucs ({model_name})...")
        self.progressChanged.emit(1)

        process = QProcess()

        program = sys.executable or "python"
        args = ["-m", "demucs", "-n", model_name, "-o", self.output_dir]
        if has_cuda():
            args += ["--device", "cuda"]
        else:
            args += ["--device", "cpu"]
        args.append(self.file_path)

        process.start(program, args)

        if not process.waitForStarted(30000):
            return None, f"Failed to start Demucs: {process.errorString()}"

        last_emit = time.time()
        last_progress = -1
        while not self._cancelled:
            if not process.waitForReadyRead(200):
                if process.state() == QProcess.NotRunning:
                    break
                continue

            data = process.readAllStandardOutput().data().decode("utf-8", errors="replace")
            now = time.time()
            for line in data.split("\n"):
                line = line.strip()
                if not line:
                    continue
                progress, status = parser.parse_line(line)
                self.statusChanged.emit(status)
                if progress != last_progress and now - last_emit >= 0.15:
                    self.progressChanged.emit(min(progress, 99))
                    last_progress = progress
                    last_emit = now

        process.waitForFinished(30000)
        exit_code = process.exitCode()

        if self._cancelled:
            return None, "Cancelled"

        if exit_code != 0:
            stderr = process.readAllStandardError().data().decode("utf-8", errors="replace")
            remaining = process.readAllStandardOutput().data().decode("utf-8", errors="replace")
            detail = (stderr[:2000] + " | " + remaining[:500]).strip(" |")
            self.statusChanged.emit(f"Demucs error: {stderr[:300]}")
            return None, f"Demucs {model_name} failed (code {exit_code}): {detail}"

        if self.original_stem and base_name != self.original_stem:
            new_out = os.path.join(self.output_dir, model_name, self.original_stem)
            if os.path.isdir(out_path) and not os.path.isdir(new_out):
                try:
                    os.rename(out_path, new_out)
                    out_path = new_out
                except Exception:
                    pass

        stems = []
        if os.path.isdir(out_path):
            for f in sorted(os.listdir(out_path)):
                if f.endswith((".wav", ".mp3", ".flac")):
                    full_path = os.path.join(out_path, f)
                    stem_name = os.path.splitext(f)[0]
                    stems.append({"name": stem_name, "path": full_path})

        return stems, None

    @Slot()
    def run(self):
        try:
            errors = []
            for model in self.models:
                stems, error = self._run_model(model)
                if self._cancelled:
                    self.finished.emit("Cancelled", [])
                    return
                if stems is not None:
                    self.progressChanged.emit(100)
                    self.statusChanged.emit("Complete!")
                    self.finished.emit("ok", stems)
                    return
                errors.append(error)
                self.statusChanged.emit(f"{model} failed, trying next...")

            self.finished.emit("; ".join(errors), [])

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
        self._cleanup_path = None

    @Slot(str)
    def split(self, file_path):
        if self._thread and self._thread.isRunning():
            self._worker.cancel()
            self._thread.quit()
            if not self._thread.wait(5000):
                self._thread.terminate()
                self._thread.wait()

        if not os.path.isfile(file_path):
            self.finished.emit(f"File not found: {file_path}", [])
            return

        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "separated")
        os.makedirs(output_dir, exist_ok=True)

        # Demucs has issues with non-ASCII paths on Windows; copy to temp if needed
        original_stem = os.path.splitext(os.path.basename(file_path))[0]
        try:
            file_path.encode("ascii")
            safe_path = file_path
        except (UnicodeEncodeError, UnicodeDecodeError):
            ext = os.path.splitext(file_path)[1]
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            tmp.close()
            try:
                shutil.copy2(file_path, tmp.name)
            except Exception:
                os.unlink(tmp.name)
                self.finished.emit(f"Failed to copy file for processing: {file_path}", [])
                return
            safe_path = tmp.name
            self._cleanup_path = tmp.name
        else:
            self._cleanup_path = None

        self._thread = QThread()
        self._worker = SplitWorker(safe_path, output_dir, original_stem=original_stem,
                                    models=["htdemucs_6s", "htdemucs"])
        self._worker.moveToThread(self._thread)

        self._worker.progressChanged.connect(self.progressChanged)
        self._worker.statusChanged.connect(self.statusChanged)
        self._worker.finished.connect(self._on_finished)
        self._thread.started.connect(self._worker.run)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self, status, stems):
        worker = self._worker
        thread = self._thread
        self._worker = None
        self._thread = None
        if thread:
            thread.quit()
            thread.wait(3000)
        if worker:
            worker.deleteLater()
        if self._cleanup_path and os.path.isfile(self._cleanup_path):
            try:
                os.unlink(self._cleanup_path)
            except Exception:
                pass
            self._cleanup_path = None
        self.finished.emit(status, stems)

    @Slot()
    def cancel(self):
        if self._worker:
            self._worker.cancel()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        if self._cleanup_path and os.path.isfile(self._cleanup_path):
            try:
                os.unlink(self._cleanup_path)
            except Exception:
                pass
            self._cleanup_path = None
