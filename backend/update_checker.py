"""
Auto-update checker for StemSplitAI.

Checks GitHub for latest.json, compares versions, downloads setup with
SHA256 verification, and launches the installer.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, QThread, Signal, Slot


def _parse_version(version_str: str) -> tuple:
    """Parse a version string like '1.2.3' into a comparable tuple (1, 2, 3)."""
    try:
        return tuple(int(x) for x in version_str.strip().lstrip("v").split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _is_newer(remote: str, local: str) -> bool:
    """Return True if remote version is strictly newer than local."""
    return _parse_version(remote) > _parse_version(local)


class _CheckWorker(QThread):
    """Background thread that fetches latest.json from GitHub."""

    updateAvailable = Signal(str, str, str, str)   # version, notes, url, sha256
    updateNotAvailable = Signal()
    checkError = Signal(str)

    def __init__(self, url: str, current_version: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._current = current_version

    def run(self):
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "StemSplitAI-Updater/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            remote_version = data.get("version", "")
            if _is_newer(remote_version, self._current):
                self.updateAvailable.emit(
                    remote_version,
                    data.get("notes", ""),
                    data.get("url", ""),
                    data.get("sha256", ""),
                )
            else:
                self.updateNotAvailable.emit()
        except Exception as exc:
            self.checkError.emit(str(exc))


class _DownloadWorker(QThread):
    """Background thread that downloads the setup exe with progress."""

    progress = Signal(int)          # 0-100
    finished = Signal(str)          # local file path
    error = Signal(str)

    def __init__(self, url: str, expected_sha256: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._sha256 = expected_sha256.lower().strip() if expected_sha256 else ""

    def run(self):
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "StemSplitAI-Updater/1.0"},
            )
            resp = urllib.request.urlopen(req, timeout=300)
            total = int(resp.headers.get("Content-Length", 0))

            # Determine download path
            filename = self._url.rsplit("/", 1)[-1] or "StemSplitAI-Setup.exe"
            download_dir = os.path.join(tempfile.gettempdir(), "StemSplitAI_updates")
            os.makedirs(download_dir, exist_ok=True)
            dest = os.path.join(download_dir, filename)

            sha = hashlib.sha256()
            downloaded = 0
            chunk_size = 64 * 1024  # 64 KB

            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    sha.update(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        self.progress.emit(int(downloaded * 100 / total))

            resp.close()

            # SHA256 verification
            if self._sha256 and sha.hexdigest() != self._sha256:
                os.remove(dest)
                self.error.emit(
                    f"SHA256 mismatch: expected {self._sha256[:16]}…, "
                    f"got {sha.hexdigest()[:16]}…"
                )
                return

            self.progress.emit(100)
            self.finished.emit(dest)
        except Exception as exc:
            self.error.emit(str(exc))


class UpdateChecker(QObject):
    """
    High-level update manager exposed to BackendController.

    Signals (forwarded to QML):
        updateAvailable(version, notes, url, sha256)
        updateNotAvailable()
        updateCheckError(message)
        downloadProgress(percent)
        downloadFinished(filePath)
        downloadError(message)
    """

    updateAvailable = Signal(str, str, str, str)
    updateNotAvailable = Signal()
    updateCheckError = Signal(str)
    downloadProgress = Signal(int)
    downloadFinished = Signal(str)
    downloadError = Signal(str)

    def __init__(self, latest_json_url: str, current_version: str, parent=None):
        super().__init__(parent)
        self._url = latest_json_url
        self._current = current_version
        self._check_worker = None
        self._download_worker = None
        self._downloaded_path = ""

    # --- Check ---------------------------------------------------------

    @Slot()
    def check(self):
        """Start checking for updates in a background thread."""
        if self._check_worker is not None and self._check_worker.isRunning():
            return

        self._check_worker = _CheckWorker(self._url, self._current, self)
        self._check_worker.updateAvailable.connect(self._on_update_available)
        self._check_worker.updateNotAvailable.connect(self.updateNotAvailable.emit)
        self._check_worker.checkError.connect(self.updateCheckError.emit)
        self._check_worker.finished.connect(self._check_worker.deleteLater)
        self._check_worker.start()

    def _on_update_available(self, version, notes, url, sha256):
        self.updateAvailable.emit(version, notes, url, sha256)

    # --- Download ------------------------------------------------------

    @Slot(str, str)
    def download(self, url: str, sha256: str):
        """Download the setup executable in background."""
        if self._download_worker is not None and self._download_worker.isRunning():
            return

        self._download_worker = _DownloadWorker(url, sha256, self)
        self._download_worker.progress.connect(self.downloadProgress.emit)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self.downloadError.emit)
        self._download_worker.finished.connect(self._download_worker.deleteLater)
        self._download_worker.start()

    def _on_download_finished(self, path: str):
        self._downloaded_path = path
        self.downloadFinished.emit(path)

    # --- Install -------------------------------------------------------

    @Slot()
    def installAndRestart(self):
        """Launch the downloaded installer and exit the app."""
        if not self._downloaded_path or not os.path.isfile(self._downloaded_path):
            self.downloadError.emit("Setup file not found.")
            return

        try:
            # Start the installer detached from the current process
            if sys.platform == "win32":
                os.startfile(self._downloaded_path)
            else:
                subprocess.Popen([self._downloaded_path], start_new_session=True)
        except Exception as exc:
            self.downloadError.emit(f"Could not launch installer: {exc}")
            return

        # Exit the running application
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.quit()
