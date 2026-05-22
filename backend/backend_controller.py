import os
import sqlite3
import datetime
import json
import shutil
import sys
from PySide6.QtCore import (
    QObject, Signal, Slot, Property, QTimer, QThread,
    QAbstractListModel, Qt, QProcess,
)
from PySide6.QtWidgets import QFileDialog

from backend.cuda_checker import has_cuda, gpu_name, device_info
from backend.splitter import Splitter
from backend.audio_player import AudioEngine, StemPlayer
from backend.database import Database
from backend.cache_manager import CacheManager
from backend.waveform import compute_waveform
from backend.process_utils import ffmpeg_program, run_hidden
from backend.update_checker import UpdateChecker
from version import APP_VERSION, LATEST_JSON_URL


class HistoryListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def roleNames(self):
        return {
            0: b"file_name",
            1: b"file_path",
            2: b"file_size",
            3: b"status",
            4: b"stems",
            5: b"created_at",
        }

    def rowCount(self, parent=None):
        return len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        keys = ["file_name", "file_path", "file_size", "status", "stems", "created_at"]
        return item.get(keys[role], "")

    def setItems(self, items):
        self.beginResetModel()
        self._items = items
        self.endResetModel()


class WaveformWorker(QThread):
    finished = Signal(str, list)

    def __init__(self, file_path, name="original", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.name = name

    def run(self):
        try:
            data = compute_waveform(self.file_path)
            self.finished.emit(self.name, data)
        except Exception:
            self.finished.emit(self.name, [])


class StemsWaveformWorker(QThread):
    stemReady = Signal(str, list)
    finished = Signal()

    def __init__(self, stems, parent=None):
        super().__init__(parent)
        self.stems = stems

    def run(self):
        try:
            for stem in self.stems:
                data = compute_waveform(stem["path"], max_points=80)
                if data:
                    self.stemReady.emit(stem["name"], data)
        except Exception:
            pass
        self.finished.emit()


class BackendController(QObject):
    splitStarted = Signal(str)
    progressUpdated = Signal(int)
    statusUpdated = Signal(str)
    splitFinished = Signal(str, str)
    stemToggled = Signal(str, bool)
    stemMuteChanged = Signal(str, bool)
    stemSoloChanged = Signal(str, bool)
    waveformReady = Signal(str, list)
    stemWaveformReady = Signal(str, list)
    gpuInfoChanged = Signal()
    positionChanged = Signal(float)
    durationChanged = Signal(float)
    allPlayingChanged = Signal()

    # --- Update signals ---
    updateAvailableChanged = Signal()
    updateDownloadProgressChanged = Signal()
    updateStatusChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._splitter = Splitter()
        self._audio_engine = AudioEngine()
        self._database = Database()
        self._cache_manager = CacheManager()
        self._gpu_info = "Checking..."
        self._gpu_available = False
        self._gpu_load = 0
        self._vram_used = "0"
        self._vram_total = "0"
        self._gpu_process = None
        self._history_model = HistoryListModel()
        self._soloed_stems = set()
        self._current_file = ""
        self._all_playing = False
        self._log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sonicsplit.log")

        # --- Update state ---
        self._update_checker = UpdateChecker(LATEST_JSON_URL, APP_VERSION, self)
        self._update_available = False
        self._update_version = ""
        self._update_notes = ""
        self._update_url = ""
        self._update_sha256 = ""
        self._update_download_progress = 0
        self._update_downloaded_path = ""

        self._update_checker.updateAvailable.connect(self._on_update_available)
        self._update_checker.updateNotAvailable.connect(self._on_update_not_available)
        self._update_checker.updateCheckError.connect(self._on_update_check_error)
        self._update_checker.downloadProgress.connect(self._on_download_progress)
        self._update_checker.downloadFinished.connect(self._on_download_finished_update)
        self._update_checker.downloadError.connect(self._on_download_error)

        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== SonicSplit {datetime.datetime.now().isoformat()} ===\n")

        self._splitter.progressChanged.connect(self.progressUpdated)
        self._splitter.statusChanged.connect(self._on_status_updated)
        self._splitter.finished.connect(self._on_split_finished)

        self._position = 0.0
        self._duration = 0.0
        self._audio_engine.positionChanged.connect(self._on_position_changed)
        self._audio_engine.durationChanged.connect(self._on_duration_changed)

        self._gpu_monitor = QTimer(self)
        self._gpu_monitor.setInterval(5000)
        self._gpu_monitor.timeout.connect(self._poll_gpu_stats)
        self._gpu_monitor.start()

        self._load_history()

    def _log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _on_status_updated(self, msg):
        self._log(msg)
        self.statusUpdated.emit(msg)

    def _gpu(self):
        return self._gpu_info

    gpuInfo = Property(str, _gpu, notify=gpuInfoChanged)

    def _get_gpu_available(self):
        return self._gpu_available

    gpuAvailable = Property(bool, _get_gpu_available, notify=gpuInfoChanged)

    def _history_model_getter(self):
        return self._history_model

    historyModel = Property(QObject, _history_model_getter, constant=True)

    @Slot()
    def checkGpu(self):
        if has_cuda():
            info = device_info()
            self._gpu_info = f"{info['name']} ({info['memory']}GB VRAM)"
            self._gpu_available = True
        else:
            self._gpu_info = "CPU Mode"
            self._gpu_available = False
        self.gpuInfoChanged.emit()

    def _demucs_installed(self):
        if hasattr(sys, 'frozen'):
            try:
                import importlib
                importlib.import_module('demucs')
                return True
            except Exception:
                return False
        try:
            r = run_hidden(
                [sys.executable, "-m", "demucs", "--help"],
                capture_output=True, timeout=10
            )
            return r.returncode == 0
        except Exception:
            return False

    @Slot()
    def startDemucsCheck(self):
        class DemucsCheck(QObject):
            done = Signal(bool)
            @Slot()
            def run(self):
                ok = self._parent._demucs_installed()
                self.done.emit(ok)
            def __init__(self, parent):
                super().__init__()
                self._parent = parent

        self._demucs_check_thread = QThread()
        self._demucs_check_worker = DemucsCheck(self)
        self._demucs_check_worker.moveToThread(self._demucs_check_thread)
        self._demucs_check_thread.started.connect(self._demucs_check_worker.run)
        self._demucs_check_worker.done.connect(lambda ok: self._on_startup_demucs_checked(ok))
        self._demucs_check_worker.done.connect(self._demucs_check_thread.quit)
        self._demucs_check_thread.finished.connect(self._demucs_check_thread.deleteLater)
        self._demucs_check_thread.start()

    def _on_startup_demucs_checked(self, ok):
        if not ok:
            self._log("Demucs not found on startup")
            self._on_status_updated("Demucs not found. Install: pip install demucs")

    @Slot(result=bool)
    def checkDemucs(self):
        return self._demucs_installed()

    def _poll_gpu_stats(self):
        if not self._gpu_available or self._gpu_process is not None:
            return

        process = QProcess(self)
        process.setProgram("nvidia-smi")
        process.setArguments([
            "--query-gpu=utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ])
        process.finished.connect(lambda code, _status: self._on_gpu_stats_finished(process, code))
        process.errorOccurred.connect(lambda _error: self._on_gpu_stats_error(process))
        self._gpu_process = process
        process.start()

    def _on_gpu_stats_finished(self, process, code):
        if self._gpu_process is process:
            self._gpu_process = None
        try:
            if code == 0:
                out = process.readAllStandardOutput().data().decode("utf-8", errors="replace")
                parts = out.strip().split(", ")
                if len(parts) >= 3:
                    self._gpu_load = int(float(parts[0]))
                    self._vram_used = str(int(float(parts[1])))
                    self._vram_total = str(int(float(parts[2])))
                    self.gpuInfoChanged.emit()
        except Exception:
            pass
        process.deleteLater()

    def _on_gpu_stats_error(self, process):
        if self._gpu_process is process:
            self._gpu_process = None
        process.deleteLater()

    def _get_gpu_load(self):
        return self._gpu_load

    def _get_vram_used(self):
        return self._vram_used

    def _get_vram_total(self):
        return self._vram_total

    gpuLoad = Property(int, _get_gpu_load, notify=gpuInfoChanged)
    vramUsed = Property(str, _get_vram_used, notify=gpuInfoChanged)
    vramTotal = Property(str, _get_vram_total, notify=gpuInfoChanged)

    def _get_selected_model(self):
        return self._splitter.selectedModel

    def _set_selected_model(self, val):
        self._splitter.selectedModel = val
        self._log(f"Model set to: {val}")

    def _get_segment_size(self):
        return self._splitter.segmentSize

    def _set_segment_size(self, val):
        self._splitter.segmentSize = val

    def _get_overlap(self):
        return self._splitter.overlap

    def _set_overlap(self, val):
        self._splitter.overlap = val

    def _get_shifts(self):
        return self._splitter.shifts

    def _set_shifts(self, val):
        self._splitter.shifts = val

    selectedModel = Property(str, _get_selected_model, _set_selected_model)
    segmentSize = Property(int, _get_segment_size, _set_segment_size)
    overlap = Property(float, _get_overlap, _set_overlap)
    shifts = Property(int, _get_shifts, _set_shifts)

    @Slot(str)
    def startSplit(self, file_path):
        self._log(f"startSplit called: {file_path}")
        if not os.path.isfile(file_path):
            self._log(f"File NOT FOUND: {file_path}")
            self.splitFinished.emit(f"File not found: {file_path}", "[]")
            return

        self._current_file = file_path
        self.splitStarted.emit(file_path)
        self._on_status_updated("Preparing...")

        # Compute waveform for the original file asynchronously in background thread
        self._compute_original_waveform(file_path)

        cache_path = self._cache_manager.has_cached(file_path)
        if cache_path:
            stems = self._stems_from_dir(cache_path, file_path)
            if stems:
                self._log(f"Using cached stems: {len(stems)} files")
                QTimer.singleShot(100, lambda: self._emit_cached(stems, file_path))
                return

        self._log("Checking Demucs installation...")
        self._on_status_updated("Checking Demucs...")

        class DemucsCheck(QObject):
            done = Signal(bool)
            @Slot()
            def run(self):
                ok = self._parent._demucs_installed()
                self.done.emit(ok)
            def __init__(self, parent):
                super().__init__()
                self._parent = parent

        self._demucs_thread = QThread()
        self._demucs_worker = DemucsCheck(self)
        self._demucs_worker.moveToThread(self._demucs_thread)
        self._demucs_thread.started.connect(self._demucs_worker.run)
        self._demucs_worker.done.connect(lambda ok: self._on_demucs_checked(ok))
        self._demucs_worker.done.connect(self._demucs_thread.quit)
        self._demucs_thread.finished.connect(self._demucs_thread.deleteLater)
        self._demucs_thread.start()

    def _on_demucs_checked(self, ok):
        self._log(f"Demucs installed: {ok}")
        if not ok:
            self._on_status_updated("Demucs not found. Install: pip install demucs")
            self.splitFinished.emit("Demucs is not installed. Run: pip install demucs", "[]")
            return
        self._on_status_updated("Starting split...")
        self._splitter.split(self._current_file)

    def _emit_cached(self, stems, file_path):
        self.splitFinished.emit("ok", json.dumps(stems))
        self._log_to_db(file_path, stems, "cached")

    def _stems_from_dir(self, dir_path, original_path=None):
        stems_by_name = {}
        preferred_ext = os.path.splitext(original_path or "")[1].lower()
        if os.path.isdir(dir_path):
            if preferred_ext and preferred_ext != ".wav":
                self._on_status_updated(f"Converting cached stems to {preferred_ext[1:].upper()}...")
                for f in sorted(os.listdir(dir_path)):
                    if f.lower().endswith(".wav"):
                        self._convert_stem_to_format(os.path.join(dir_path, f), preferred_ext)

            for f in sorted(os.listdir(dir_path)):
                if not f.lower().endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac")):
                    continue
                full_path = os.path.join(dir_path, f)
                stem_name, ext = os.path.splitext(f)
                existing = stems_by_name.get(stem_name)
                if existing is None or ext.lower() == preferred_ext:
                    stems_by_name[stem_name] = full_path
        return [{"name": name, "path": path} for name, path in sorted(stems_by_name.items())]

    def _convert_stem_to_format(self, wav_path, target_ext):
        target_path = os.path.splitext(wav_path)[0] + target_ext
        if os.path.isfile(target_path) and os.path.getmtime(target_path) >= os.path.getmtime(wav_path):
            return target_path

        args = [ffmpeg_program(), "-y", "-hide_banner", "-loglevel", "error", "-i", wav_path, "-vn"]
        if target_ext == ".mp3":
            args += ["-codec:a", "libmp3lame", "-q:a", "2"]
        elif target_ext == ".flac":
            args += ["-codec:a", "flac"]
        elif target_ext == ".ogg":
            args += ["-codec:a", "libvorbis", "-q:a", "6"]
        elif target_ext in (".m4a", ".aac"):
            args += ["-codec:a", "aac", "-b:a", "256k"]
        args.append(target_path)

        try:
            run_hidden(args, capture_output=True, text=True, check=True, timeout=600)
            return target_path
        except Exception as e:
            self._log(f"Stem format conversion failed: {e}")
            return wav_path

    def _on_split_finished(self, status, stems):
        self._log(f"Split finished: status={status}, stems={len(stems)}")
        if status == "ok" and stems:
            self._cache_manager.set_cached(self._current_file_path(), self._stems_dir(stems))
            self._load_stems_into_engine(stems)
            self._log_to_db(self._current_file_path(), stems, "ok")
        else:
            self._on_status_updated(status if isinstance(status, str) else "Unknown error")

        self._load_history()
        self.splitFinished.emit(status, json.dumps(stems))

    def _current_file_path(self):
        return self._current_file

    def _stems_dir(self, stems):
        if stems:
            return os.path.dirname(stems[0]["path"])
        return ""

    def _load_stems_into_engine(self, stems):
        for stem in stems:
            player = self._audio_engine.create_stem_player(stem["name"], stem["path"])
            if player:
                player.positionChanged.connect(lambda pos, n=stem["name"]: None)
        self._compute_waveform_from_stems(stems)

    def _compute_waveform_from_stems(self, stems):
        self._log("Starting background stems waveform worker")
        self._stems_waveform_thread = StemsWaveformWorker(stems, self)
        self._stems_waveform_thread.stemReady.connect(self.stemWaveformReady.emit)
        self._stems_waveform_thread.finished.connect(self._stems_waveform_thread.deleteLater)
        self._stems_waveform_thread.start()

    def _compute_original_waveform(self, file_path):
        self._log(f"Computing original waveform for: {file_path}")
        self._waveform_thread = WaveformWorker(file_path, "original", self)
        self._waveform_thread.finished.connect(self._on_original_waveform_ready)
        self._waveform_thread.finished.connect(self._waveform_thread.deleteLater)
        self._waveform_thread.start()

    def _on_original_waveform_ready(self, name, data):
        self._log(f"Original waveform ready: {len(data)} points")
        self.waveformReady.emit(name, data)

    def _log_to_db(self, file_path, stems, status):
        try:
            name = os.path.basename(file_path)
            size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
            self._database.add_history(name, file_path, size, 0, status, stems)
        except Exception:
            pass

    def _load_history(self):
        try:
            items = self._database.get_history(20)
            self._history_model.setItems(items)
        except Exception:
            pass

    @Slot(str)
    def toggleStem(self, name):
        player = self._audio_engine.get_stem_player(name)
        if not player:
            return
        if player.name() == name:
            is_playing = False
            self.stemToggled.emit(name, is_playing)

    @Slot(str)
    def toggleMute(self, name):
        player = self._audio_engine.get_stem_player(name)
        if player:
            muted = not player._muted
            player.setMuted(muted)
            self.stemMuteChanged.emit(name, muted)

    @Slot(str)
    def toggleSolo(self, name):
        player = self._audio_engine.get_stem_player(name)
        if not player:
            return
        if name in self._soloed_stems:
            self._soloed_stems.discard(name)
            player.setMuted(False)
        else:
            for s in list(self._soloed_stems):
                p = self._audio_engine.get_stem_player(s)
                if p:
                    p.setMuted(False)
            self._soloed_stems.clear()
            self._soloed_stems.add(name)

            for n, p in self._audio_engine._players.items():
                if n != name:
                    p.setMuted(True)

        is_soloed = name in self._soloed_stems
        self.stemSoloChanged.emit(name, is_soloed)

    @Slot(str, float)
    def setStemGain(self, name, gain):
        player = self._audio_engine.get_stem_player(name)
        if player:
            player.setGain(gain)

    @Slot(str)
    def playStem(self, name):
        player = self._audio_engine.get_stem_player(name)
        if player:
            player.play()
            self.stemToggled.emit(name, True)

    @Slot(str)
    def stopStem(self, name):
        player = self._audio_engine.get_stem_player(name)
        if player:
            player.stop()
            self.stemToggled.emit(name, False)

    @Slot(str)
    def exportStem(self, name):
        player = self._audio_engine.get_stem_player(name)
        if not player:
            self._log(f"Export failed: stem '{name}' not loaded")
            self._on_status_updated(f"Export failed: stem '{name}' not found")
            return
        src = player._player.source().toLocalFile()
        if not src or not os.path.isfile(src):
            self._log(f"Export failed: no source file for '{name}'")
            return
        ext = os.path.splitext(src)[1] or ".wav"
        filter_str = f"Audio Files (*{ext});;All Files (*)"
        dst_path, _ = QFileDialog.getSaveFileName(
            None,
            f"Save {name.capitalize()} Stem",
            f"{name}{ext}",
            filter_str
        )
        if not dst_path:
            return
        try:
            shutil.copy2(src, dst_path)
            self._log(f"Exported '{name}' -> {dst_path}")
            self._on_status_updated(f"Exported '{name}'")
        except Exception as e:
            self._log(f"Export error: {e}")

    @Slot()
    def exportAllStems(self):
        players = list(self._audio_engine._players.items())
        if not players:
            self._log("Export All: no stems loaded")
            return
        dir_path = QFileDialog.getExistingDirectory(None, "Export All Stems")
        if not dir_path:
            return
        for name, player in players:
            src = player._player.source().toLocalFile()
            if src and os.path.isfile(src):
                ext = os.path.splitext(src)[1] or ".wav"
                dst = os.path.join(dir_path, f"{name}{ext}")
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    self._log(f"Export '{name}' error: {e}")
        self._log(f"Exported {len(players)} stems to {dir_path}")
        self._on_status_updated(f"Exported {len(players)} stems")

    @Slot()
    def cleanup(self):
        self._audio_engine.clear()

    @Slot()
    def clearAll(self):
        self._audio_engine.clear()
        self._soloed_stems.clear()

    @Slot()
    def clearHistory(self):
        try:
            conn = sqlite3.connect(self._database.db_path)
            conn.execute("DELETE FROM history")
            conn.commit()
            conn.close()
            self._load_history()
            self._log("History cleared")
            self._on_status_updated("History cleared")
        except Exception:
            pass

    @Slot()
    def clearSolo(self):
        for n, p in self._audio_engine._players.items():
            p.setMuted(False)
        self._soloed_stems.clear()

    @Slot(str)
    def setSolo(self, name):
        self.clearSolo()
        self._soloed_stems.add(name)
        for n, p in self._audio_engine._players.items():
            if n != name:
                p.setMuted(True)

    @Slot()
    def cancelSplit(self):
        self._splitter.cancel()

    # ===== UPDATE SYSTEM =====

    def _get_app_version(self):
        return APP_VERSION

    appVersion = Property(str, _get_app_version, constant=True)

    def _get_update_available(self):
        return self._update_available

    updateAvailable = Property(bool, _get_update_available, notify=updateAvailableChanged)

    def _get_update_version(self):
        return self._update_version

    updateVersion = Property(str, _get_update_version, notify=updateAvailableChanged)

    def _get_update_notes(self):
        return self._update_notes

    updateNotes = Property(str, _get_update_notes, notify=updateAvailableChanged)

    def _get_update_download_progress(self):
        return self._update_download_progress

    updateDownloadProgress = Property(int, _get_update_download_progress, notify=updateDownloadProgressChanged)

    @Slot()
    def checkForUpdates(self):
        self._log("Checking for updates...")
        self._update_download_progress = 0
        self._update_downloaded_path = ""
        self.updateDownloadProgressChanged.emit()
        self.updateStatusChanged.emit("checking")
        self._update_checker.check()

    @Slot()
    def downloadUpdate(self):
        if not self._update_url:
            return
        self._log(f"Downloading update v{self._update_version}...")
        self.updateStatusChanged.emit("downloading")
        self._update_checker.download(self._update_url, self._update_sha256)

    @Slot()
    def installUpdate(self):
        self._log("Installing update and restarting...")
        self._update_checker.installAndRestart()

    def _on_update_available(self, version, notes, url, sha256):
        self._log(f"Update available: v{version}")
        self._update_available = True
        self._update_version = version
        self._update_notes = notes
        self._update_url = url
        self._update_sha256 = sha256
        self.updateAvailableChanged.emit()
        self.updateStatusChanged.emit("available")

    def _on_update_not_available(self):
        self._log("No update available — app is up to date")
        self._update_available = False
        self._update_version = ""
        self._update_notes = ""
        self.updateAvailableChanged.emit()
        self.updateStatusChanged.emit("uptodate")

    def _on_update_check_error(self, msg):
        self._log(f"Update check error: {msg}")
        self.updateStatusChanged.emit("error")

    def _on_download_progress(self, percent):
        self._update_download_progress = percent
        self.updateDownloadProgressChanged.emit()

    def _on_download_finished_update(self, path):
        self._log(f"Update downloaded: {path}")
        self._update_downloaded_path = path
        self.updateStatusChanged.emit("ready")

    def _on_download_error(self, msg):
        self._log(f"Update download error: {msg}")
        self._update_download_progress = 0
        self.updateDownloadProgressChanged.emit()
        self.updateStatusChanged.emit("error")

    def _get_all_playing(self):
        return self._all_playing

    allPlaying = Property(bool, _get_all_playing, notify=allPlayingChanged)

    @Slot(float)
    def setMasterVolume(self, vol):
        self._audio_engine.setMasterVolume(vol)

    def _on_position_changed(self, pos):
        self._position = pos
        self.positionChanged.emit(pos)

    def _on_duration_changed(self, dur):
        self._duration = dur
        self.durationChanged.emit(dur)

    def _get_position(self):
        return self._position

    def _get_duration(self):
        return self._duration

    position = Property(float, _get_position, notify=positionChanged)
    duration = Property(float, _get_duration, notify=durationChanged)

    @Slot(float)
    def seek(self, position_sec):
        self._audio_engine.seek(position_sec)

    @Slot()
    def togglePlayAll(self):
        if self._all_playing:
            self._audio_engine.pauseAll()
            self._all_playing = False
        else:
            self._audio_engine.playAll()
            self._all_playing = True
        self.allPlayingChanged.emit()

    @Slot(list)
    def loadStems(self, stems):
        self._load_stems_into_engine(stems)

    @Slot(str, str)
    def loadHistoryItem(self, file_path, stems_json):
        self._log(f"loadHistoryItem called: {file_path}")
        
        # Verify if the stem files exist
        try:
            stems = json.loads(stems_json)
        except Exception as e:
            self._log(f"Error parsing stems JSON: {e}")
            self._on_status_updated("Error loading history: invalid data")
            self.splitFinished.emit("error", "[]")
            return
            
        missing_files = []
        for stem in stems:
            path = stem.get("path")
            if not path or not os.path.exists(path):
                missing_files.append(stem.get("name", "unknown"))
                
        if missing_files:
            self._log(f"Cannot load history: missing files {missing_files}")
            self._on_status_updated(f"Cannot load history: files for {', '.join(missing_files)} are missing")
            self.splitFinished.emit("error", "[]")
            return
            
        self.clearAll()
        self._current_file = file_path

        # Compute waveform for the original file asynchronously in background thread
        self._compute_original_waveform(file_path)

        self.splitFinished.emit("ok", stems_json)
