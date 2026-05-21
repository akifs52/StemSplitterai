import os

from PySide6.QtCore import QObject, Signal, Slot, QUrl, Property
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class StemPlayer(QObject):
    positionChanged = Signal(float)
    durationChanged = Signal(float)
    stateChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._muted = False
        self._solo = False
        self._gain = 1.0
        self._pan = 0.0
        self._name = ""

        self._player.positionChanged.connect(lambda pos: self.positionChanged.emit(pos / 1000.0))
        self._player.durationChanged.connect(lambda dur: self.durationChanged.emit(dur / 1000.0))
        self._player.mediaStatusChanged.connect(self._on_media_status)

    def _on_media_status(self, status):
        mapping = {
            QMediaPlayer.LoadedMedia: "loaded",
            QMediaPlayer.BufferingMedia: "buffering",
            QMediaPlayer.BufferedMedia: "buffered",
            QMediaPlayer.EndOfMedia: "ended",
        }
        self.stateChanged.emit(mapping.get(status, "unknown"))

    @Slot(str)
    def load(self, file_path):
        if os.path.isfile(file_path):
            self._player.setSource(QUrl.fromLocalFile(file_path))

    @Slot()
    def play(self):
        self._player.play()

    @Slot()
    def pause(self):
        self._player.pause()

    @Slot()
    def stop(self):
        self._player.stop()

    @Slot(float)
    def seek(self, position_sec):
        self._player.setPosition(int(position_sec * 1000))

    @Slot(float)
    def setVolume(self, vol):
        self._audio_output.setVolume(vol)

    @Slot(bool)
    def setMuted(self, muted):
        self._muted = muted
        self._audio_output.setMuted(muted)

    @Slot(float)
    def setGain(self, gain):
        self._gain = max(0.0, min(4.0, gain))
        self._audio_output.setVolume(self._gain)

    def setPan(self, pan):
        self._pan = max(-1.0, min(1.0, pan))

    def name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def deleteLater(self):
        self._player.stop()
        self._player.deleteLater()
        self._audio_output.deleteLater()
        super().deleteLater()


class AudioEngine(QObject):
    positionChanged = Signal(float)
    durationChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._players = {}
        self._master_volume = 1.0
        self._position = 0.0
        self._duration = 0.0

    def _get_position(self):
        return self._position

    def _get_duration(self):
        return self._duration

    position = Property(float, _get_position, notify=positionChanged)
    duration = Property(float, _get_duration, notify=durationChanged)

    def _sync_position(self, pos):
        self._position = pos
        self.positionChanged.emit(pos)

    def _sync_duration(self, dur):
        self._duration = dur
        self.durationChanged.emit(dur)

    @Slot(float)
    def seek(self, position_sec):
        self._position = position_sec
        for p in self._players.values():
            p.seek(position_sec)
        self.positionChanged.emit(position_sec)

    def create_stem_player(self, stem_name, file_path):
        if stem_name in self._players:
            self._players[stem_name].deleteLater()
        player = StemPlayer()
        player.set_name(stem_name)
        player.load(file_path)
        player.setVolume(self._master_volume)
        self._players[stem_name] = player
        player.positionChanged.connect(self._sync_position)
        player.durationChanged.connect(self._sync_duration)
        return player

    def get_stem_player(self, stem_name):
        return self._players.get(stem_name)

    @Slot(float)
    def setMasterVolume(self, vol):
        self._master_volume = max(0.0, min(1.0, vol))
        for p in self._players.values():
            p.setVolume(self._master_volume)

    @Slot()
    def previous(self):
        pass

    @Slot()
    def next(self):
        pass

    @Slot()
    def stopAll(self):
        for p in self._players.values():
            p.stop()

    @Slot()
    def playAll(self):
        first = next(iter(self._players.values()), None)
        if not first:
            return
        self._duration = first._player.duration() / 1000.0
        self.durationChanged.emit(self._duration)
        for p in self._players.values():
            p.seek(self._position)
            p.play()

    @Slot()
    def pauseAll(self):
        for p in self._players.values():
            p.pause()

    def clear(self):
        for p in list(self._players.values()):
            p.deleteLater()
        self._players.clear()

    def deleteLater(self):
        self.clear()
        super().deleteLater()
