import os
import subprocess
import sqlite3
import datetime
import json
import shutil
from PySide6.QtCore import (
    QObject, Signal, Slot, Property, QTimer, QThread,
    QAbstractListModel, Qt,
)
from PySide6.QtWidgets import QFileDialog

from backend.cuda_checker import has_cuda, gpu_name, device_info
from backend.splitter import Splitter
from backend.audio_player import AudioEngine, StemPlayer
from backend.database import Database
from backend.cache_manager import CacheManager
from backend.waveform import compute_waveform


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


class BackendController(QObject):
    splitStarted = Signal(str)
    progressUpdated = Signal(int)
    statusUpdated = Signal(str)
    splitFinished = Signal(str, str)
    stemToggled = Signal(str, bool)
    stemMuteChanged = Signal(str, bool)
    stemSoloChanged = Signal(str, bool)
    waveformReady = Signal(str, object)
    gpuInfoChanged = Signal()

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
        self._history_model = HistoryListModel()
        self._soloed_stems = set()
        self._current_file = ""
        self._all_playing = False
        self._log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sonicsplit.log")

        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== SonicSplit {datetime.datetime.now().isoformat()} ===\n")

        self._splitter.progressChanged.connect(self.progressUpdated)
        self._splitter.statusChanged.connect(self._on_status_updated)
        self._splitter.finished.connect(self._on_split_finished)

        self._gpu_monitor = QTimer(self)
        self._gpu_monitor.setInterval(2000)
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

    @Slot()
    def startDemucsCheck(self):
        class DemucsCheck(QObject):
            done = Signal(bool)
            @Slot()
            def run(self):
                import subprocess, sys
                try:
                    r = subprocess.run([sys.executable, "-m", "demucs", "--help"],
                                       capture_output=True, timeout=10)
                    self.done.emit(r.returncode == 0)
                except Exception:
                    self.done.emit(False)

        self._demucs_check_thread = QThread()
        self._demucs_check_worker = DemucsCheck()
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
        try:
            import subprocess, sys
            r = subprocess.run(
                [sys.executable, "-m", "demucs", "--help"],
                capture_output=True, timeout=10
            )
            return r.returncode == 0
        except Exception:
            return False

    def _poll_gpu_stats(self):
        if not self._gpu_available:
            return
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if r.returncode == 0:
                parts = r.stdout.strip().split(", ")
                if len(parts) >= 3:
                    self._gpu_load = int(float(parts[0]))
                    self._vram_used = str(int(float(parts[1])))
                    self._vram_total = str(int(float(parts[2])))
                    self.gpuInfoChanged.emit()
        except Exception:
            pass

    def _get_gpu_load(self):
        return self._gpu_load

    def _get_vram_used(self):
        return self._vram_used

    def _get_vram_total(self):
        return self._vram_total

    gpuLoad = Property(int, _get_gpu_load, notify=gpuInfoChanged)
    vramUsed = Property(str, _get_vram_used, notify=gpuInfoChanged)
    vramTotal = Property(str, _get_vram_total, notify=gpuInfoChanged)

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
                import subprocess, sys
                try:
                    r = subprocess.run([sys.executable, "-m", "demucs", "--help"],
                                       capture_output=True, timeout=10)
                    self.done.emit(r.returncode == 0)
                except Exception:
                    self.done.emit(False)

        self._demucs_thread = QThread()
        self._demucs_worker = DemucsCheck()
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
        stems = []
        if os.path.isdir(dir_path):
            for f in sorted(os.listdir(dir_path)):
                if f.endswith((".wav", ".mp3", ".flac")):
                    full_path = os.path.join(dir_path, f)
                    stem_name = os.path.splitext(f)[0]
                    stems.append({"name": stem_name, "path": full_path})
        return stems

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
        for stem in stems:
            if stem["name"].lower() == "vocals":
                data = compute_waveform(stem["path"])
                self.waveformReady.emit(stem["name"], data)
                break
        else:
            data = compute_waveform(stems[0]["path"]) if stems else []
            if stems:
                self.waveformReady.emit(stems[0]["name"], data)

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
        dir_path = QFileDialog.getExistingDirectory(None, f"Export {name}")
        if not dir_path:
            return
        ext = os.path.splitext(src)[1] or ".wav"
        dst = os.path.join(dir_path, f"{name}{ext}")
        try:
            shutil.copy2(src, dst)
            self._log(f"Exported '{name}' -> {dst}")
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
    def cancelSplit(self):
        self._splitter.cancel()

    @Slot()
    def togglePlayAll(self):
        if self._all_playing:
            self._audio_engine.pauseAll()
            self._all_playing = False
        else:
            self._audio_engine.playAll()
            self._all_playing = True

    @Slot(list)
    def loadStems(self, stems):
        self._load_stems_into_engine(stems)
