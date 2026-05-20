import os
from PySide6.QtCore import (
    QObject, Signal, Slot, Property, QTimer,
    QAbstractListModel, Qt,
)

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
    splitFinished = Signal(str, object)
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
        self._history_model = HistoryListModel()
        self._soloed_stems = set()
        self._current_file = ""
        self._all_playing = False

        self._splitter.progressChanged.connect(self.progressUpdated)
        self._splitter.statusChanged.connect(self.statusUpdated)
        self._splitter.finished.connect(self._on_split_finished)

        self._load_history()

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

    @Slot(str)
    def startSplit(self, file_path):
        if not os.path.isfile(file_path):
            self.splitFinished.emit(f"File not found: {file_path}", [])
            return

        self._current_file = file_path
        self.splitStarted.emit(file_path)
        self.statusUpdated.emit("Preparing...")

        cache_path = self._cache_manager.has_cached(file_path)
        if cache_path:
            stems = self._stems_from_dir(cache_path, file_path)
            if stems:
                QTimer.singleShot(100, lambda: self._emit_cached(stems, file_path))
                return

        if not self.checkDemucs():
            self.statusUpdated.emit("Demucs not found. Install it: pip install demucs")
            self.splitFinished.emit("Demucs is not installed. Run: pip install demucs", [])
            return

        self._splitter.split(file_path)

    def _emit_cached(self, stems, file_path):
        self.splitFinished.emit("ok", stems)
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
        if status == "ok" and stems:
            self._cache_manager.set_cached(self._current_file_path(), self._stems_dir(stems))
            self._load_stems_into_engine(stems)
            self._log_to_db(self._current_file_path(), stems, "ok")
        else:
            self.statusUpdated.emit(status if isinstance(status, str) else "Unknown error")

        self._load_history()
        self.splitFinished.emit(status, stems)

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

    @Slot()
    def cleanup(self):
        self._audio_engine.clear()

    @Slot()
    def clearAll(self):
        self._audio_engine.clear()
        self._soloed_stems.clear()

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
