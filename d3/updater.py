# decompyle3 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: updater.py
import json, os, shutil, fitz
from queue import Queue, Empty
from functools import partial
from qtpy.QtCore import QThread, Signal, QTimer, Qt
from qtpy.QtWidgets import QApplication
import dirs
from across import Across
from customs import isZipValid, kill, readJson
from dbmanager import BookDb, CoreDb, UserDb, importMajor
from downloader import Downloader

def writeJson(file_path, data):
    folder = os.path.dirname(file_path)
    os.makedirs(folder, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as write_file:
        json.dump(data, write_file, separators=(', ', ': '), indent=4, ensure_ascii=False)


def setPdfVersion(file_path, version):
    if version > 1:
        folder, file = os.path.split(file_path)
        json_path = os.path.join(folder, 'versions.json')
        current_versions = readJson(json_path)
        current_versions[file.lower()] = version
        writeJson(json_path, current_versions)


def isPdfValid(file_path):
    if not os.path.isfile(file_path):
        return
    count = None
    try:
        doc = fitz.open(file_path)
        count = doc.page_count
    except:
        return
    else:
        if count:
            return True


class UpdateRequest:
    URL_BASE = 'https://dev.shamela.ws/api'
    API_KEY = '7b9524-8fc30c-e6241o-a0167e-a6d013'
    API_VER = 'v1'

    @staticmethod
    def bookRequest(book_id, major_ondisk, minor_ondisk):
        return f"{UpdateRequest.URL_BASE}/{UpdateRequest.API_VER}/patches/book-updates/{book_id}?api_key={UpdateRequest.API_KEY}&major_release={major_ondisk}&minor_release={minor_ondisk}"

    @staticmethod
    def masterRequest(disk_version):
        return f"{UpdateRequest.URL_BASE}/{UpdateRequest.API_VER}/patches/master?api_key={UpdateRequest.API_KEY}&version={disk_version}"

    @staticmethod
    def url(disk_version):
        return UpdateRequest.masterRequest(disk_version)


class MasterImporter(QThread):
    done = Signal(bool)
    progress = Signal(int, int)

    def __init__(self, extract_path, version, call_back, progression):
        super().__init__()
        self.extract_path = extract_path
        self.version = version
        self.done.connect(call_back, Qt.QueuedConnection)
        self.progress.connect(progression, Qt.QueuedConnection)

    def run(self):
        try:
            value = CoreDb().importMaster(self.extract_path, self.version, self.progress)
        except Exception:
            value = False

        self.done.emit(value)


class AutoMinors:
    __doc__ = 'Background minor updates, flood-proof by design: ONE serial worker\n    (download -> import -> version bump must fully finish before the next book)\n    and one attempt per book per session (the `tried` valve).'

    def __init__(self):
        self.is_running = self.allowed = None
        self.downloader = []
        self.tried = set()

    def reevaluate(self):
        self.allowed = CoreDb().minors()

    def go(self):
        self.is_running = True
        if not self.downloader:
            self.downloader.append(BookDownloader((self.picker), serial=True))
        for worker in self.downloader:
            worker.go()

    def picker(self):
        if not self.is_running:
            return
        self.reevaluate()
        for value in self.allowed:
            if value not in self.tried:
                self.tried.add(value)
                return value

    def stop(self):
        self.is_running = None


class Auto:

    def __init__(self, context):
        self.is_running = self.allowed = None
        self.context = context
        self.downloader = []
        self.tried = set()

    def reevaluate(self):
        self.allowed = CoreDb().allowedBooks(self.context)

    def go(self):
        self.is_running = True
        if not self.downloader:
            for i in range(6):
                self.downloader.append(BookDownloader(self.picker) if self.context == 4 else PdfDownloader(self.picker))

        for i in range(6):
            self.downloader[i].go()

    def picker(self):

        def subBook(book_id):
            if self.context == 5:
                return book_id
            sub_books = CoreDb().staleSubBooks(book_id)
            for book in sub_books:
                if book not in self.tried:
                    return book

            return book_id

        if not self.is_running:
            return
        self.reevaluate()
        for value in self.allowed:
            if value not in self.tried:
                new_value = subBook(value)
                if new_value:
                    self.tried.add(new_value)
                    return new_value

    def stop(self):
        self.is_running = None


class BookDownloader:
    RETRY_LIMIT = 3
    RETRY_BASE_DELAY = 5000

    def __init__(self, picker, serial=None):
        self.picker = picker
        self.serial = serial
        self.awaiting_import = None
        self.book_id = None
        self.major_ondisk = self.minor_ondisk = None
        self.minor_online = self.major_online = None
        self.major_path = self.minor_path = None
        self.minor_url = self.has_minor = None
        self.downloader = None
        self.is_running = None
        self.retries = 0
        self.epoch = 0
        importer().start()
        if serial:
            importer().progression.connect(self.importProgress, Qt.QueuedConnection)

    def go(self):
        if self.is_running:
            return
        self.epoch += 1
        self.is_running = True
        self.startBook()

    def stop(self):
        self.epoch += 1
        self.is_running = None

    def startBook(self):
        while 1:
            self.book_id = self.picker()
            if not self.book_id:
                self.is_running = None
                return
            if self.book_id not in Across.downloading_books:
                Across.downloading_books[self.book_id] = 0
                self.retries = 0
                self.requestBook()
                return

    def releaseBook(self):
        if self.book_id:
            Across.downloading_books.pop(self.book_id, None)
            window = Across.main_window.update
            if window:
                if window.isVisible():
                    window.refresh()

    def abandonBook(self):
        self.releaseBook()
        self.startBook()

    def scheduleRetry(self):
        self.retries += 1
        if self.retries > self.RETRY_LIMIT:
            self.abandonBook()
            return
        delay = min(self.RETRY_BASE_DELAY * 2 ** (self.retries - 1), 60000)
        epoch = self.epoch
        QTimer.singleShot(delay, lambda: self.retryBook(epoch)
)

    def retryBook(self, epoch):
        if epoch != self.epoch:
            return
        self.requestBook()

    def requestBook(self):
        self.info_path = None
        self.major_ondisk = self.minor_ondisk = None
        self.minor_online = self.major_online = None
        self.has_minor = None
        self.major_path = self.minor_path = None
        self.minor_url = None
        self.major_ondisk, self.minor_ondisk, major_online, minor_online = CoreDb().getBookVersions(self.book_id)
        if not self.major_ondisk or self.major_ondisk == -1:
            self.major_ondisk = 0
        if not self.minor_ondisk or self.minor_ondisk == -1:
            self.minor_ondisk = 0
        self.info_path = os.path.join(dirs.updateDir(), 'book', str(self.book_id), f"{self.book_id}.json")
        if os.path.isfile(self.info_path):
            try:
                with open(self.info_path, 'r') as f:
                    item = json.load(f)
            except (ValueError, OSError):
                item = None
                try:
                    os.remove(self.info_path)
                except OSError:
                    pass

            if item is not None:
                self.queueItem(item)
                return
        if major_online and major_online != self.major_ondisk:
            self.major_online = major_online
            self.minor_online = minor_online if minor_online is not None else 0
            self.downloadMajor()
        else:
            if major_online and minor_online and minor_online > self.minor_ondisk:
                self.askBook()
            else:
                self.abandonBook()

    def askBook(self):
        ask_url = UpdateRequest().bookRequest(self.book_id, self.major_ondisk, self.minor_ondisk)
        self.downloader = Downloader(ask_url, finished=(self.bookResponded))

    def bookResponded(self, data, status_code):
        if status_code == 204:
            self.abandonBook()
        else:
            if status_code == 200:
                try:
                    response = json.loads(str(data, encoding='utf-8'))
                    self.major_online = response['major_release']
                    self.minor_online = response['minor_release']
                except (ValueError, KeyError, TypeError):
                    self.scheduleRetry()
                    return

                if self.major_online == self.major_ondisk:
                    if self.minor_ondisk == self.minor_online:
                        self.abandonBook()
                    else:
                        if 'minor_release_url' in response:
                            minor = response['minor_release_url'].split('/api/')[1]
                            self.minor_url = f"https://dev.shamela.ws/api/{minor}"
                            self.has_minor = True
                            self.checkMinor()
                        else:
                            self.abandonBook()
                else:
                    self.downloadMajor()
            else:
                self.abandonBook()

    def downloadMajor(self):
        self.has_minor = None
        file_base = f"{self.book_id}-{self.major_online}-{self.minor_online}.zip"
        self.major_path = os.path.join('book', f"{self.book_id}", file_base)
        abs_major = os.path.join(dirs.updateDir(), self.major_path)
        if os.path.isfile(abs_major):
            self.putBook()
        else:
            major_url = f"https://ready.shamela.ws/ready/{file_base}"
            self.downloader = Downloader(major_url, abs_major, progressed=(self.progress), finished=(self.putMajor), error=(self.scheduleRetry))

    def progress(self, read, total):
        Across.main_window.bookDownloadProgress(self.book_id, read, total)

    def putMajor(self):
        self.progress(1, 0)
        self.putBook()

    def checkMinor(self):
        if self.has_minor:
            self.minor_path = os.path.join('book', f"{self.book_id}", f"{self.book_id}-{self.major_online}-{self.minor_ondisk}-{self.minor_online}.zip")
            abs_minor = os.path.join(dirs.updateDir(), self.minor_path)
            if os.path.isfile(abs_minor):
                self.putBook()
            else:
                self.downloader = Downloader((self.minor_url), abs_minor, finished=(self.putBook), error=(self.scheduleRetry))
        else:
            self.putBook()

    def putBook(self):
        item = [self.book_id, self.major_path, self.minor_path, self.major_online, self.minor_online]
        if self.book_id:
            writeJson(self.info_path, item)
            self.queueItem(item)

    def queueItem(self, item):
        Importer.put(item)
        importer().start()
        Across.downloading_books.pop(item[0], None)
        if self.serial:
            self.awaiting_import = item[0]
        else:
            self.startBook()

    def importProgress(self, book_id, read, total):
        if total == 0:
            if book_id == self.awaiting_import:
                self.awaiting_import = None
                self.startBook()


def importer():
    """a wrapper function to creat Importer thread Only when needed,
    to avoid overhead of creating a thread while we may not need it at all"""
    if not Across.importer_thread:
        Across.importer_thread = Importer()
    return Across.importer_thread


class Importer(QThread):
    progression = Signal(int, int, int)
    finished_signal = Signal()
    valve = set()
    queue = Queue()

    def __init__(self):
        super().__init__()
        self.stop_requested = False
        self.books_total = self.books_done = self.book_high = 0
        self.progression.connect(Across.main_window.bookProgress, Qt.QueuedConnection)
        self.progression.connect(self.prepareProgress, Qt.QueuedConnection)
        self.finished.connect(self.restartIfPending, Qt.QueuedConnection)

    def connectFinsihed(self, finished_slot):
        self.finished_signal.connect(finished_slot)

    def disconnectFinsihed(self):
        try:
            self.finished_signal.disconnect()
        except:
            pass

    @classmethod
    def put(cls, item):
        if item[0] not in cls.valve:
            cls.valve.add(item[0])
            cls.queue.put(item)

    @classmethod
    def get(cls):
        item = cls.queue.get()
        cls.valve.discard(item[0])
        return item

    @classmethod
    def drain(cls):
        """empty the pending import queue (an item already being imported is unaffected)"""
        while 1:
            try:
                cls.queue.get_nowait()
            except Empty:
                break

        cls.valve.clear()

    def run(self):
        self.stop_requested = False
        total = self.queue.qsize()
        current = 1
        self.books_total = total
        try:
            while not self.queue.empty():
                item = Importer.get()
                self.books_done = current - 1
                self.book_high = 0
                try:
                    imported = self.process(item)
                except Exception:
                    imported = None

                try:
                    self.clean(item, imported)
                    if Across.main_window.update_widget.button_state == 'prepare':
                        self.prepareBar(current * 100)
                        current += 1
                except Exception:
                    pass

                if self.stop_requested:
                    break

        finally:
            try:
                if Across.downloading_books:
                    self.progression.emit(next(iter(Across.downloading_books)), 0, 1)
                Across.main_window.progress.progress_signal.emit({'end': True})
            except Exception:
                pass

            self.finished_signal.emit()

    def prepareBar(self, value):
        Across.main_window.progress.progress_signal.emit({'start':self.books_total * 100, 
         'value':value,  'tip':self.tr('Importing downloaded books')})

    def prepareProgress(self, book_id, read, total):
        """spend each book's slot on that book's own progress.

        The first-run bar counts books, so a queue holding one big book is a bar
        that stands still for as long as that book takes. Each book now owns a
        hundredth of the bar and fills it as it is imported.

        A book is imported in steps that each count from 1 again, and a bar that
        went back on every new step would be worse than one that crawls: the
        high mark is what the bar follows, so the long step drives it and the
        quick ones that follow simply hold it until the book is done.
        """
        if read < 0 or not total or not self.books_total:
            return None
        if Across.main_window.update_widget.button_state != 'prepare':
            return None
        percent = min(99, max(1, int((read / total) * 100)))
        if percent <= self.book_high:
            return None
        self.book_high = percent
        self.prepareBar(self.books_done * 100 + percent)
        return None

    def restartIfPending(self):
        if self.stop_requested:
            return
        if not self.queue.empty():
            if not self.isRunning():
                self.start()

    def stop(self):
        self.stop_requested = True
        self.requestInterruption()

    def process(self, item):
        import dirs
        book_id, major_path, minor_path, major_version, minor_version = (
         item[0], item[1], item[2], item[3], item[4])
        if major_path:
            if os.path.isabs(major_path):
                major_path = os.sep.join(os.path.normpath(major_path).split(os.sep)[-3:])
            major_path = os.path.join(dirs.updateDir(), major_path)
        if minor_path:
            if os.path.isabs(minor_path):
                minor_path = os.sep.join(os.path.normpath(minor_path).split(os.sep)[-3:])
            minor_path = os.path.join(dirs.updateDir(), minor_path)
        self.progression.emit(book_id, -1, 100)
        for path in [major_path, minor_path]:
            if path:
                if not isZipValid(path):
                    return

        if major_path:
            importMajor(book_id, major_path, major_version, minor_version, self.progression)
        else:
            BookDb(book_id).importMinor(minor_path, major_version, minor_version)
        return True

    def clean(self, item, imported=True):
        book_id = item[0]
        if item[1]:
            if imported:
                UserDb().updateDownloadHistory('text', book_id)
        shutil.rmtree((os.path.join(dirs.updateDir(), 'book', f"{book_id}")), ignore_errors=True)
        self.progression.emit(book_id, 0, 0)


class PdfDownloader:
    RETRY_LIMIT = 3
    RETRY_BASE_DELAY = 5000
    MAX_INFLIGHT = 3

    def __init__(self, picker=None):
        self.picker = picker
        self.book_id = None
        self.downloader = []
        self.is_running = None
        self.single_progression = None
        self.epoch = 0
        self.pending = []
        self.pending_sizes = []
        self.pending_left = set()
        self.item_retries = {}
        self.next_index = 0
        self.inflight = 0
        self.files = []
        self.total_size = 0
        self.base_size = 0

    def singleBook(self, book_id, single_progression):
        self.single_progression = single_progression
        self.book_id = book_id
        Across.main_window.pdfProgress(self.book_id, 0)
        self.prepareBook()

    def go(self):
        if self.is_running:
            return
        self.is_running = True
        self.startBook()

    def stop(self):
        self.epoch += 1
        self.is_running = None

    def startBook(self):
        QApplication.processEvents()
        if self.book_id:
            if self.book_id in Across.downloading_pdfs:
                del Across.downloading_pdfs[self.book_id]
        if not self.picker:
            self.is_running = None
            return
        while 1:
            self.book_id = self.picker()
            if not self.book_id:
                self.is_running = None
                return
            if self.book_id not in Across.downloading_pdfs:
                Across.main_window.pdfProgress(self.book_id, 0)
                self.prepareBook()
                return

    def prepareBook(self):
        valve = set()
        self.epoch += 1
        self.pending = []
        self.pending_sizes = []
        self.downloader = []
        self.item_retries = {}
        self.next_index = 0
        self.inflight = 0
        self.files, self.total_size = CoreDb().sizedpdfs(self.book_id)
        self.base_size = 0
        self.current_item = None
        for pdf in self.files:
            if os.path.isfile(pdf['file']):
                self.base_size += os.path.getsize(pdf['file'])
                valve.add(pdf['url'])

        for pdf in self.files:
            if pdf['url'].startswith('/'):
                url = f"https://ready.shamela.ws/pdf{pdf['url']}"
            else:
                url = pdf['url'].replace('archive.org/download/', 'ready.shamela.ws/pdf/')
            if pdf['url'] not in valve:
                if not os.path.isfile(pdf['file']):
                    valve.add(pdf['url'])
                    self.pending.append({'url':f"{url}?{pdf['version']}", 
                     'version':pdf['version'],  'file':pdf['file']})
                    self.pending_sizes.append(0)

        self.pending_left = set(range(len(self.pending)))
        self.getItem()

    def getItem(self):
        while self.next_index < len(self.pending):
            if self.inflight < self.MAX_INFLIGHT:
                i = self.next_index
                self.next_index += 1
                self.launchItem(i)

        if not self.pending_left:
            if not self.inflight:
                self.yesFinished()

    def launchItem(self, i):
        item = self.pending[i]
        self.inflight += 1
        self.downloader.append(Downloader((item['url']), (item['file']), progressed=(partial(self.progress, self.epoch, i)),
          finished=(partial(self.itemFinished, self.epoch, i)),
          error=(partial(self.itemFailed, self.epoch, i))))

    def itemFinished(self, epoch, i):
        if epoch != self.epoch:
            return
        self.inflight -= 1
        setPdfVersion(self.pending[i]['file'], self.pending[i]['version'])
        self.pending_left.discard(i)
        if self.single_progression:
            self.single_progression()
        self.getItem()

    def itemFailed(self, epoch, i):
        if epoch != self.epoch:
            return
        self.inflight -= 1
        self.item_retries[i] = self.item_retries.get(i, 0) + 1
        stopped = self.picker and not self.is_running
        if self.item_retries[i] <= self.RETRY_LIMIT and not stopped:
            delay = min(self.RETRY_BASE_DELAY * 2 ** (self.item_retries[i] - 1), 60000)
            QTimer.singleShot(delay, partial(self.retryItem, epoch, i))
        else:
            self.pending_left.discard(i)
            self.getItem()

    def retryItem(self, epoch, i):
        if epoch != self.epoch:
            return
        self.launchItem(i)

    def yesFinished(self):
        valid = True
        Across.main_window.pdfProgress(self.book_id, Across.BUSY)
        for pdf in self.files:
            if not isPdfValid(pdf['file']):
                kill(pdf['file'])
                valid = False

        if valid:
            CoreDb().pdfDownloaded(self.book_id, self.files)
            Across.main_window.pdfProgress(self.book_id, 1000)
        else:
            Across.main_window.pdfProgress(self.book_id, 0)
        self.startBook()

    def progress(self, epoch, i, read, _):
        if epoch != self.epoch:
            return
        self.pending_sizes[i] = read
        current_size = self.base_size
        for pending_size in self.pending_sizes:
            current_size += pending_size

        if self.total_size:
            Across.main_window.pdfProgress(self.book_id, int(current_size / self.total_size * 100))