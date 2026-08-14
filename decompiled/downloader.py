# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: downloader.py
import os
from qtpy.QtCore import QObject, QUrl, QFile, QIODevice, Signal, QTimer
from qtpy.QtNetwork import QNetworkAccessManager, QNetworkRequest
from values import USER_AGENT

class Downloader(QObject):
    __doc__ = 'One HTTP transfer that can never leave its caller waiting forever.\n\n    Contract: every construction ends with exactly one terminal signal, on\n    every path (existing file, duplicate url, open failure, network error,\n    stall, success) — file mode emits finished/error, memory mode emits data\n    with the http status code (0 when the request never produced a response).\n    A connection that stops sending bytes is aborted by an inactivity\n    watchdog and reported through the error path with its partial file kept\n    for a Range resume.'
    qnam = QNetworkAccessManager()
    finished = Signal()
    error = Signal()
    progressed = Signal(int, int)
    data = Signal(bytearray, int)
    valve = set()
    active = {}
    FILE_IDLE_LIMIT = 45000
    MEMORY_IDLE_LIMIT = 30000

    def __init__(self, url, path=None, progressed=None, finished=None, error=None):
        super().__init__()
        self.url = url
        self.is_file_mode = bool(path)
        self.httpRequestAborted = None
        self._done = None
        self._owns_valve = None
        self._timed_out = None
        self._headers_checked = None
        self._reply = None
        self.outFile = None
        self.watchdog = None
        self.baze = 0
        self._received = 0
        self._expected_total = 0
        if progressed:
            self.progressed.connect(progressed)
        else:
            if error:
                self.error.connect(error)
            elif finished:
                if path:
                    self.finished.connect(finished)
                else:
                    self.data.connect(finished)
            if self.url in self.valve:
                self._finishLater(False)
                return
                self.valve.add(self.url)
                self._owns_valve = True
                self.active[self.url] = self
                if path:
                    self.final = path
                    if os.path.isfile(self.final):
                        self._finishLater(True)
                        return
                    os.makedirs((os.path.dirname(self.final)), exist_ok=True)
                    self.partial = f"{self.final}.___"
                    self.outFile = QFile(self.partial)
                    if not self.outFile.open(QIODevice.Append):
                        self.outFile = None
                        self._finishLater(False)
                        return
                request = QNetworkRequest(QUrl(self.url))
                request.setRawHeader(b'User-Agent', USER_AGENT.encode())
                request.setRawHeader(b'Connection', b'Keep-Alive')
                if hasattr(QNetworkRequest, 'HttpPipeliningAllowedAttribute'):
                    request.setAttribute(QNetworkRequest.HttpPipeliningAllowedAttribute, True)
                if hasattr(QNetworkRequest, 'FollowRedirectsAttribute'):
                    request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
            else:
                self.qnam.setRedirectPolicy(QNetworkRequest.NoLessSafeRedirectPolicy)
        request.setAttribute(QNetworkRequest.CacheLoadControlAttribute, QNetworkRequest.AlwaysNetwork)
        if path:
            self.baze = self.outFile.size()
            if self.baze:
                request.setRawHeader(b'Range', f"bytes={self.baze}-".encode())
        self._reply = self.qnam.get(request)
        self._reply.ignoreSslErrors()
        if path:
            self._reply.finished.connect(self.httpFinished)
            self._reply.readyRead.connect(self.httpReadyRead)
            self._reply.downloadProgress.connect(self.downloadProgress)
            self._reply.metaDataChanged.connect(self.headersArrived)
            idle_limit = self.FILE_IDLE_LIMIT
        else:
            self._reply.finished.connect(self.memory)
            self._reply.downloadProgress.connect(self.kick)
            idle_limit = self.MEMORY_IDLE_LIMIT
        self.watchdog = QTimer(self)
        self.watchdog.setSingleShot(True)
        self.watchdog.setInterval(idle_limit)
        self.watchdog.timeout.connect(self.watchdogExpired)
        self.watchdog.start()

    def _finish(self, ok, payload=None, status_code=0):
        """The single terminal gate: release all shared state, then emit exactly once."""
        if self._done:
            return
        else:
            self._done = True
            if self.watchdog:
                self.watchdog.stop()
            if self.outFile:
                self.outFile.close()
                self.outFile = None
            if self._reply:
                self._reply.deleteLater()
            if self._owns_valve:
                Downloader.valve.discard(self.url)
                Downloader.active.pop(self.url, None)
            if self.is_file_mode:
                if ok:
                    self.finished.emit()
                else:
                    self.error.emit()
            else:
                self.data.emit(payload if payload is not None else bytearray(b''), status_code)

    def _finishLater(self, ok):
        QTimer.singleShot(0, lambda: self._finish(ok))

    def kick(self, *args):
        if self.watchdog:
            self.watchdog.start()

    def watchdogExpired(self):
        self._timed_out = True
        self.abort()

    def memory(self):
        if self._done:
            return
        payload = self._reply.readAll()
        status_code = 0
        try:
            status_code = self._reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
        except:
            pass

        self._finish(True, payload, status_code)

    def downloadProgress(self, read_bytes, total_bytes):
        self.kick()
        if total_bytes > 0:
            self._expected_total = total_bytes + self.baze
        self.progressed.emit(read_bytes + self.baze, total_bytes + self.baze)

    def headersArrived(self):
        self.kick()
        self.checkResumeHonored()

    def checkResumeHonored(self):
        if self._headers_checked or self._done:
            return
        status_code = self._reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if (status_code == 206 or status_code) == 200:
            self._headers_checked = self.baze or True
        else:
            if status_code == 200:
                self._headers_checked = True
                self.outFile.close()
                if self.outFile.open(QIODevice.WriteOnly | QIODevice.Truncate):
                    self.baze = 0
                    self._received = 0
                else:
                    self.abort()

    def httpReadyRead(self):
        self.kick()
        self.checkResumeHonored()
        if self._done:
            return
        else:
            chunk = self._reply.readAll()
            return self._headers_checked or None
        self._received += chunk.size()
        if self.outFile.write(chunk) != chunk.size():
            self.abort()
            return
        self.outFile.flush()

    def httpFinished(self):
        if self._done:
            return
        self.outFile.close()
        status_code = self._reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
        aborted = self.httpRequestAborted or self._timed_out
        net_error = bool(self._reply.error())
        byte_complete = self._expected_total > 0 and self._received + self.baze == self._expected_total
        has_data = os.path.isfile(self.partial) and os.path.getsize(self.partial) > 0
        ok = not aborted and has_data and status_code in (200, 206) and (not net_error or byte_complete)
        if ok:
            try:
                os.replace(self.partial, self.final)
            except OSError:
                pass

            ok = os.path.isfile(self.final)
        else:
            if status_code == 416:
                try:
                    os.remove(self.partial)
                except OSError:
                    pass

            self._finish(ok)

    def abort(self):
        if self._done:
            return
        elif self._reply:
            self.httpRequestAborted = True
            self._reply.abort()
        else:
            self._finish(False)

    @classmethod
    def abortAll(cls):
        """Abort every in-flight transfer. Each one closes its file, releases its
        valve entry and emits its terminal signal, so afterwards no .___ file is
        held open (Windows cannot delete open files)."""
        for downloader in list(cls.active.values()):
            downloader.abort()