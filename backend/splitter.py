import os
import sys
import time
import tempfile
import shutil

from PySide6.QtCore import QObject, Signal, Slot, QThread, QProcess

from backend.progress_parser import ProgressParser
from backend.cuda_checker import has_cuda
from backend.process_utils import ffmpeg_program, run_hidden


class SplitWorker(QObject):
    progressChanged = Signal(int)
    statusChanged = Signal(str)
    finished = Signal(str, list)

    def __init__(self, file_path, output_dir, original_stem=None, original_ext=".wav", models=None,
                 segment_size=5, overlap=0.25, shifts=1):
        super().__init__()
        self.file_path = file_path
        self.output_dir = output_dir
        self.original_stem = original_stem
        self.original_ext = original_ext.lower()
        self.models = models or ["htdemucs_6s", "htdemucs"]
        self.segment_size = segment_size
        self.overlap = overlap
        self.shifts = shifts
        self._cancelled = False
        self._process = None

    def _conversion_args(self, src_path, dst_path):
        ext = os.path.splitext(dst_path)[1].lower()
        args = [ffmpeg_program(), "-y", "-hide_banner", "-loglevel", "error", "-i", src_path, "-vn"]
        if ext == ".mp3":
            args += ["-codec:a", "libmp3lame", "-q:a", "2"]
        elif ext == ".flac":
            args += ["-codec:a", "flac"]
        elif ext == ".ogg":
            args += ["-codec:a", "libvorbis", "-q:a", "6"]
        elif ext in (".m4a", ".aac"):
            args += ["-codec:a", "aac", "-b:a", "256k"]
        args.append(dst_path)
        return args

    def _convert_stem_if_needed(self, wav_path):
        if self.original_ext in ("", ".wav"):
            return wav_path

        dst_path = os.path.splitext(wav_path)[0] + self.original_ext
        if os.path.isfile(dst_path) and os.path.getmtime(dst_path) >= os.path.getmtime(wav_path):
            return dst_path

        run_hidden(
            self._conversion_args(wav_path, dst_path),
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )
        return dst_path

    def _collect_stems(self, out_path):
        stems_by_name = {}
        if not os.path.isdir(out_path):
            return []

        for f in sorted(os.listdir(out_path)):
            if not f.lower().endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac")):
                continue
            full_path = os.path.join(out_path, f)
            stem_name, ext = os.path.splitext(f)
            existing = stems_by_name.get(stem_name)
            if existing is None or ext.lower() == self.original_ext:
                stems_by_name[stem_name] = full_path

        return [{"name": name, "path": path} for name, path in sorted(stems_by_name.items())]

    def cancel(self):
        self._cancelled = True
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.kill()
            self._process.waitForFinished(3000)

    def _run_model(self, model_name):
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        out_path = os.path.join(self.output_dir, model_name, base_name)
        parser = ProgressParser()

        self.statusChanged.emit(f"Initializing Demucs ({model_name})...")
        self.progressChanged.emit(1)

        process = QProcess()
        self._process = process

        demucs_args = ["-n", model_name, "-o", self.output_dir,
                       "--segment", str(self.segment_size),
                       "--overlap", str(self.overlap),
                       "--shifts", str(self.shifts)]
        if has_cuda():
            demucs_args += ["--device", "cuda"]
        else:
            demucs_args += ["--device", "cpu"]
        demucs_args.append(self.file_path)

        program = sys.executable or shutil.which("python") or "python"
        if getattr(sys, "frozen", False):
            args = ["--stemsplit-demucs", *demucs_args]
        else:
            args = ["-m", "demucs", *demucs_args]

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

        if self._cancelled and process.state() != QProcess.NotRunning:
            process.kill()
        process.waitForFinished(30000)
        exit_code = process.exitCode()
        self._process = None

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

        if self.original_ext != ".wav":
            self.statusChanged.emit(f"Converting stems to {self.original_ext[1:].upper()}...")
            for f in sorted(os.listdir(out_path)) if os.path.isdir(out_path) else []:
                if f.lower().endswith(".wav"):
                    self._convert_stem_if_needed(os.path.join(out_path, f))

        stems = self._collect_stems(out_path)

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
        self.selectedModel = "htdemucs_6s"
        self.segmentSize = 5
        self.overlap = 0.25
        self.shifts = 1

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
        original_ext = os.path.splitext(file_path)[1].lower() or ".wav"
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
                                    original_ext=original_ext,
                                    models=[self.selectedModel],
                                    segment_size=self.segmentSize,
                                    overlap=self.overlap,
                                    shifts=self.shifts)
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
