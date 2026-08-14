# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: mainwindow.py
import shutil, sys, json, os, socket
from functools import partial
from threading import Thread
from time import sleep, time
from qtpy.QtCore import QCoreApplication, QThread, QSize, Qt, QTranslator, QTimer, QSettings, Signal, QUrl, QObject, QEvent
from qtpy.QtGui import QIcon, QFont, QFontDatabase, QGuiApplication, QKeySequence, QImage, QPixmap, QFontMetrics, QDesktopServices, QKeyEvent, QPalette
from qtpy.QtWidgets import QWidgetAction, QSplitter, QTabWidget, QTabBar, QActionGroup, QAction, QMenu, QStackedWidget, QToolButton, QListWidget, QWidget, QProgressBar, QSizePolicy, QApplication, QLabel, QListWidgetItem
from values import *
from across import Across
from engine import Query
from customs import checkAllPdf, kill, isZipValid, flexibleBrowser, pextract, BusySpinner, customToolButton, QtFont, clickableLabel, LineEdit, unpack, customMessage, CustomDialog, registerFonts, shortcuts, customLayout, Qtlabel, image, hLine, singlePhrase, shortcut, directShortcut, styledLabel, minSize, shortcutLabel, directShortcutLabel, normalizeShortcutLabel, matchesShortcutEvent, trueLapse
from dbmanager import dbLuceneRectify, delayed_deletions, CoreDb, CoverDb, UserDb, updateService, switchUser, switchBoth
from dirs import getPaths, updateDir, isWritable, pdfPath, emptyLastSessionFlag, defaultPdfPath
from downloader import Downloader
from engine import Index
from engine import register_shutdown_handlers, replaceQuranIndex
from settings import Settings
from theme import Icon, applyApplicationTheme, TabCloseButton, installTabCloseButton
from textmanager import tip, arabize, conditioned, treatSearch, five, tooltipHtml
import resources.qrc_shamela
TARGET_SETUP_VERSION = 27
BUSY_ICON = 'busy'
CHECK_URL = f"https://dev.shamela.ws/versions/{Across.os}.php"
VERSION_DOWNLOAD_URL = f"https://dev.shamela.ws/updates/{Across.os}/"
lock = None

def mark_launcher_ready():
    path = os.environ.pop('SHAMELA_LAUNCH_READY_FILE', '')
    if not path:
        return
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as (ready_file):
            ready_file.write('ready\n')
    except Exception:
        pass


class PosixFileLock:

    def __init__(self, path):
        self.path = path
        self.fd = None

    def acquire(self, timeout=1):
        import fcntl
        deadline = time() + timeout
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 438)
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                if time() >= deadline:
                    os.close(self.fd)
                    self.fd = None
                    raise TimeoutError(self.path)
                sleep(0.05)

    def release(self):
        if self.fd is None:
            return
        import fcntl
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None


def updateFileLock(path):
    if Across.os == 'win':
        from filelock import FileLock
        return FileLock(path)
    return PosixFileLock(path)


def finish_startup_activation(app, form):
    if form.windowState() & Qt.WindowMinimized:
        form.setWindowState(Qt.WindowNoState)
    form.setFocus()
    form.raise_()
    form.activateWindow()
    app.setActiveWindow(form)


def inject(target, args, inter_signal, finished_slot):
    """Run target in a thread and emit its result back to the main thread."""

    def func():
        try:
            value = target(*args) if args else target()
        except Exception:
            value = None

        inter_signal.emit(value)

    try:
        inter_signal.disconnect()
    except:
        pass

    inter_signal.connect(finished_slot)
    Thread(target=func, daemon=True).start()


def cleanupTildeBinFolders():
    bin_directory = Across.bin_directory
    leftovers = []
    try:
        with os.scandir(bin_directory) as (entries):
            for entry in entries:
                if entry.name.startswith('~') and entry.is_dir(follow_symlinks=False):
                    leftovers.append(entry.path)

    except OSError:
        pass

    for path in leftovers:
        shutil.rmtree(path, ignore_errors=True)


def cleanupOldRuntimeFolders():
    runtime_roots = [
     os.path.realpath(os.path.join(Across.bin_directory, os.pardir, 'jre')),
     os.path.join(Across.home_directory, 'app', 'lucene')]
    for folder in runtime_roots:
        if not os.path.isdir(folder):
            continue
        versions = []
        valid_versions = []
        for name in os.listdir(folder):
            subfolder = os.path.join(folder, name)
            if not os.path.isdir(subfolder):
                continue
            if not name.isdigit():
                continue
            version = int(name)
            versions.append(version)
            if os.path.isfile(os.path.join(subfolder, 'done.manifest')):
                valid_versions.append(version)

        keep_version = max(valid_versions) if valid_versions else None
        for version in sorted(versions):
            if keep_version is not None:
                if version == keep_version:
                    continue
            shutil.rmtree(os.path.join(folder, f"{version}"))


_running_extractors = set()

class Extractor(QThread):
    done = Signal(bool)
    percent = Signal(float)

    def __init__(self, file, extract_path, finished=None, progress=None):
        super().__init__()
        self.file = file
        self.extract_path = extract_path
        if finished:
            self.done.connect(finished, Qt.QueuedConnection)
        if progress:
            self.percent.connect(progress, Qt.QueuedConnection)
        _running_extractors.add(self)
        self.finished.connect(lambda: _running_extractors.discard(self))
        self.finished.connect(self.deleteLater)

    def run(self):
        if pextract((self.file), (self.extract_path), signal=(self.percent)):
            self.done.emit(True)
        else:
            self.done.emit(False)


class ShiftedWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_shift = None

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            this_time = time()
            if self.last_shift:
                lapse = this_time - self.last_shift
                if trueLapse(lapse):
                    self.doubleShift()
                    return
            self.last_shift = this_time
        else:
            self.last_shift = None
        super().keyReleaseEvent(event)

    def doubleShift(self):
        pass


def is_connected():
    try:
        socket.create_connection(('1.1.1.1', 53), timeout=3).close()
        return True
    except OSError:
        return False


class Progress(QProgressBar):
    progress_signal = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(100)
        self.setFixedHeight(10)
        self.setVisible(False)
        self.setTextVisible(False)
        self.progress_signal.connect(self.adjust)
        self.db_tip = self.tr('Updating databases')

    def adjust(self, value):
        if 'start' in value:
            self.setMinimum(0)
            self.setMaximum(value['start'])
            self.setVisible(True)
        else:
            if 'value' in value:
                p_value = value['value']
                if p_value > self.maximum():
                    p_value = self.maximum()
                self.setValue(p_value)
                self.setVisible(True)
            if 'end' in value:
                self.setToolTip('')
                self.setVisible(False)
                for widget in Across.refresh_set:
                    widget.reinstall()

                if Across.main_window.update_widget.pdfButton.isVisible():
                    Across.main_window.checkPdfIcon()
        if 'tip' in value:
            self.setToolTip(self.db_tip if value['tip'] == 'db' else arabize(value['tip']))


class UpdateWidget(QWidget):
    inter_signal = Signal(object)

    def __init__(self, free_progress, search_line):
        super().__init__()
        self.downloader = self.software_version = self.working = self.patch_path = None
        self.extractor = self.disk_version = self.web_version = self.master_importer = self.outer_file = None
        self.web_services = self.disk_services = self.next_bead = self.after_extraction = self.service_name = None
        self.local_file = self.local_folder = self.current_setup_ver = None
        self.jre_version = self.lucene_version = None
        self.runtime_name = self.runtime_file = self.runtime_folder = self.next_step = None
        self.app_next_step = None
        self.app_target_version = None
        self.restart_needed = None
        self.error_status = self.fix_error = None
        if Across.no_update:
            return
        self.button_state = 'prepare'
        directShortcut(self, 'Ctrl+U', self.goUpdate)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(100)
        self.progress.setFixedHeight(10)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.pdfButton = customToolButton(slot=(self.goPdf), iconsize=24)
        self.pdfButton.setToolTip(self.tr('Download Pdf'))
        self.pdfButton.setVisible(False)
        self.updateButton = customToolButton(slot=(self.goUpdate), iconsize=24)
        self.updateButton.setVisible(False)
        self.setLayout(customLayout(False, [
         0, search_line, 3, free_progress, 3, self.progress, self.pdfButton, self.updateButton, 1],
          margins=0))
        QTimer.singleShot(0, self.prepare)

    def prepare(self):
        core_db = CoreDb()
        self.current_setup_ver = core_db.getVersion('setup')
        pending_deletes = core_db.pendingDelets()
        if pending_deletes:
            Across.main_window.progress.progress_signal.emit({'start':0,  'tip':self.tr('Cleaning some files')})
            inject(delayed_deletions, None, self.inter_signal, self.importRemnants)
        else:
            self.importRemnants()

    def importRemnants(self):
        from updater import importer
        Across.main_window.progress.progress_signal.emit({'end': True})
        remnants_exist = None
        books_directory = os.path.join(updateDir(), 'book')
        subdirectories = [name for name in os.listdir(books_directory) if os.path.isdir(os.path.join(books_directory, name))]
        for directory in subdirectories:
            json_file = os.path.join(books_directory, directory, f"{directory}.json")
            if os.path.isfile(json_file):
                with open(json_file, 'r') as (f):
                    importer().put(json.load(f))
                remnants_exist = True

        if remnants_exist:
            importer().connectFinsihed(self.correctSetup)
            importer().start()
        else:
            self.correctSetup(skip_importer=True)

    def correctSetup(self, skip_importer=None):
        if not skip_importer:
            from updater import importer
            importer().disconnectFinsihed()
        elif self.current_setup_ver < TARGET_SETUP_VERSION:
            self.pdfCheckFix()
        else:
            self.checkSecret()

    def pdfCheckFix(self):
        if self.current_setup_ver < 24:
            inject(checkAllPdf, (Across.main_window.progress.progress_signal,), self.inter_signal, self.alphaFix)
        else:
            self.alphaFix()

    def alphaFix(self):

        def alpha():
            return CoreDb().alpha(catch_all=True)

        if self.current_setup_ver < 26:
            inject(alpha, None, self.inter_signal, self.rectify)
        else:
            self.finalizeCorrection()

    def rectify(self, value):

        def progressed(read, total):
            p_signal.emit({'start':total,  'value':read,  'tip':self.tr('Downloading files')})

        def json_fetched(data, _):
            nonlocal web_version
            try:
                p_signal.emit({'end': True})
                response = str(data, encoding='utf-8')
                response = json.loads(response)
                web_version = response['version']
                file_path = os.path.join(fix_path, f"{web_version}.zip")
                if os.path.isfile(file_path):
                    do()
                else:
                    self.downloader = Downloader((response['patch_url']), path=file_path, progressed=progressed, finished=do, error=do)
            except:
                self.fix_error = True
                do()

        def do():
            p_signal.emit({'end': True})
            if self.fix_error:
                self.finalizeCorrection()
            else:
                extract_path = os.path.join(fix_path, f"{web_version}")
                inject(dbLuceneRectify, (extract_path, p_signal), self.inter_signal, rect_result)

        def rect_result(r_value):
            if not r_value:
                self.fix_error = True
            self.finalizeCorrection()

        if value:
            web_version = 0
            p_signal = Across.main_window.progress.progress_signal
            fix_path = os.path.join(updateDir(), 'fix')
            from updater import UpdateRequest
            url = UpdateRequest.url(0)
            self.downloader = Downloader(url, finished=json_fetched, error=json_fetched)
        else:
            self.fix_error = True
            self.finalizeCorrection()

    def finalizeCorrection(self):
        if not self.fix_error:
            CoreDb().setVersion('setup', TARGET_SETUP_VERSION)
        self.checkSecret()

    def busy(self, tool_tip):
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setToolTip(tool_tip)
        self.showProgress()

    def progression(self, read, total):
        self.progress.setMinimum(0)
        self.progress.setMaximum(total)
        self.progress.setValue(read)
        self.showProgress()

    def showProgress(self):
        if not self.progress.isVisible():
            self.progress.setVisible(True)
        if self.pdfButton.isVisible():
            self.pdfButton.setVisible(False)
        if self.updateButton.isVisible():
            self.updateButton.setVisible(False)

    def iconize(self, icon_path, tool_tip=None):
        self.updateButton.setMaximumSize(16777215, 16777215)
        self.updateButton.setMinimumSize(0, 0)
        self.updateButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.updateButton.setStyleSheet('')
        self.updateButton.setText('')
        if icon_path == BUSY_ICON:
            BusySpinner.follow(self.updateButton)
        else:
            BusySpinner.unfollow(self.updateButton)
            self.updateButton.setIcon(Icon.icon(icon_path))
        if tool_tip:
            self.updateButton.setToolTip(directShortcutLabel(tool_tip, 'Ctrl+U'))
        if not self.updateButton.isVisible():
            self.updateButton.setVisible(True)

    def goUpdate(self):
        if not self.updateButton.isVisible():
            return
        elif self.button_state == 'initial':
            self.checkSecret()
        else:
            if self.button_state == 'ready':
                Across.main_window.showUpdate()
            else:
                if self.button_state == 'restart':
                    try:
                        import shamela as _sh
                        _sh.restart_via_launcher()
                    except Exception:
                        pass

                    Across.main_window.close()

    def goPdf(self):
        if not self.pdfButton.isVisible():
            return
        Across.main_window.showPdf()

    def runtimeFolder(self, runtime_name):
        if runtime_name == 'jre':
            return os.path.realpath(os.path.join(Across.bin_directory, os.pardir, 'jre'))
        return os.path.join(Across.home_directory, 'app', 'lucene')

    def runtimeDiskVersion(self, runtime_name):
        folder = self.runtimeFolder(runtime_name)
        if not os.path.isdir(folder):
            return 0
        versions = []
        for name in os.listdir(folder):
            subfolder = os.path.join(folder, name)
            if not os.path.isdir(subfolder):
                continue
            if not name.isdigit():
                continue
            if os.path.isfile(os.path.join(subfolder, 'done.manifest')):
                versions.append(int(name))

        if versions:
            return max(versions)
        return 0

    def runtimeUrl(self, runtime_name, version):
        if runtime_name == 'jre':
            return f"https://dev.shamela.ws/updates/{Across.os}/jre/{version}_{Across.running_arch}.zip"
        return f"https://dev.shamela.ws/updates/lucene/{version}.zip"

    def secretUrl(self):
        return f"https://dev.shamela.ws/versions/{Across.os}.php"

    def parseSecret(self, data):
        try:
            secret = str(data, encoding='utf-8')
        except:
            return
        else:
            parts = secret.split('|')
            if len(parts) != 6:
                return
            try:
                _, software_version, lucene_version, jre_version, web_version, web_services = parts
                return {'software_version':int(software_version), 
                 'lucene_version':int(lucene_version), 
                 'jre_version':int(jre_version), 
                 'web_version':int(web_version), 
                 'web_services':web_services}
            except:
                return

    def checkApp(self):
        if self.software_version > CURRENT_SOFTWARE_VERSION:
            self.appUpdate(self.checkJre)
        else:
            self.checkJre()

    def checkJre(self):
        self.checkRuntime('jre', self.jre_version, self.checkLucene)

    def checkLucene(self):
        self.checkRuntime('lucene', self.lucene_version, self.afterUpdateCheck)

    def checkRuntime(self, runtime_name, version, next_step):
        if version <= self.runtimeDiskVersion(runtime_name):
            next_step()
            return
        self.runtime_name = runtime_name
        runtime_root = self.runtimeFolder(runtime_name)
        os.makedirs(runtime_root, exist_ok=True)
        self.runtime_folder = os.path.join(runtime_root, f"{version}")
        self.runtime_file = f"{self.runtime_folder}.zip"
        self.next_step = next_step
        self.busy(self.tr('Downloading files'))
        if os.path.isfile(self.runtime_file):
            if isZipValid(self.runtime_file):
                self.runtimeDownloaded()
                return
            kill(self.runtime_file)
            if os.path.isfile(self.runtime_file):
                self.error()
                return
        self.downloader = Downloader((self.runtimeUrl(runtime_name, version)), (self.runtime_file), progressed=(self.progression),
          finished=(self.runtimeDownloaded),
          error=(self.downloadFailed))

    def runtimeDownloaded(self):
        shutil.rmtree((self.runtime_folder), ignore_errors=True)
        if os.path.isdir(self.runtime_folder):
            self.error()
            return
        self.busy(self.tr('Extracting files'))
        self.extractor = Extractor(self.runtime_file, self.runtime_folder, self.runtimeExtracted, self.extractProgress)
        self.extractor.start()

    def runtimeExtracted(self, value):
        if not value:
            self.error()
            return
        version = self.jre_version if self.runtime_name == 'jre' else self.lucene_version
        with open(os.path.join(self.runtime_folder, 'done.manifest'), 'w') as (f):
            f.write(f"{version}")
        self.restart_needed = True
        self.next_step()

    def afterUpdateCheck(self):
        if self.restart_needed:
            self.askRestart()
        else:
            self.checkServices()

    def checkServices(self):
        self.web_services = json.loads(self.web_services)
        self.disk_services = CoreDb().getServicesVersion()
        self.checkQuran()

    def askRestart(self):
        self.zero()
        self.progress.setVisible(False)
        self.pdfButton.setVisible(False)
        self.iconize(':/icons/upgrade.png', self.tr('Restart application to apply updates'))
        self.button_state = 'restart'

    def checkSecret(self):
        if not self.working:
            self.working = True
            self.progress.setVisible(False)
            self.pdfButton.setVisible(False)
            self.iconize(BUSY_ICON, self.tr('Checking Updates'))
            local_secret = os.path.join(Across.bin_directory, 'secrete.txt')
            if os.path.isfile(local_secret):
                try:
                    with open(local_secret, 'rb') as (f):
                        self.secretChecked(f.read().strip(), 200)
                except:
                    self.error()

            else:
                self.downloader = Downloader((self.secretUrl()), finished=(self.secretChecked))

    def checkPdfIcon(self):
        if not self.updateButton.isVisible():
            return
        elif self.button_state not in frozenset({'initial', 'ready'}):
            return
            if Across.no_update:
                return
            count, ignored, names_list = CoreDb().newBookCount(5)
            if ignored:
                count = arabize((f"{count}"), forced=True)
                caption = self.tr('All available Pdfs are downloaded Except Ignored Ones')
                self.pdfButton.setVisible(True)
                self.pdfButton.setIcon(Icon.icon(':/icons/pdf_grey.png'))
                self.pdfButton.setToolTip(tooltipHtml(f"{caption}: {count}", names_list))
        elif count:
            count = arabize((f"{count}"), forced=True)
            self.pdfButton.setVisible(True)
            self.pdfButton.setIcon(Icon.icon(':/icons/pdf_u.png'))
            caption = self.tr('Number of Pdfs')
            self.pdfButton.setToolTip(tooltipHtml(f"{caption}: {count}", names_list))
        else:
            self.pdfButton.setVisible(False)

    def zero(self):
        self.downloader = self.software_version = self.working = self.patch_path = self.extractor = self.disk_version = self.web_version = self.master_importer = None
        self.jre_version = self.lucene_version = None
        self.runtime_name = self.runtime_file = self.runtime_folder = self.next_step = None
        self.app_next_step = None
        self.app_target_version = None
        self.restart_needed = None
        self.button_state = 'initial'

    def ok(self):
        self.error_status = None
        self.zero()
        self.progress.setVisible(False)
        self.okGui()

    def okGui(self):
        self.updateCount()
        self.updateButton.setVisible(True)
        Across.main_window.startBook()
        Across.main_window.startPdf()
        Across.main_window.cover_downloader.download()
        Across.main_window.startMinors()
        if not Settings.getValue('auto_download_books'):
            if CoreDb().getOfflineBooksNumber() == 0:
                Across.main_window.showUpdate(forgive=True)

    def updateCount(self):
        if self.button_state == 'prepare':
            return
            if Across.no_update:
                return
            if self.error_status:
                return
            self.checkPdfIcon()
            count, ignored, names_list = CoreDb().newBookCount(4)
            if ignored:
                count = arabize((f"{count}"), forced=True)
                self.iconize(':/icons/grey_done.png')
                caption = self.tr('All available books are downloaded Except Ignored Ones')
                self.updateButton.setToolTip(tooltipHtml(f"{caption}: {count}", names_list))
                self.button_state = 'ready'
        elif count:
            count = arabize((f"{count}"), forced=True)
            qfont = QtFont(['Traditional Naskh', 18, True])
            width = QFontMetrics(qfont).boundingRect(count).width() + (15 if Across.os == 'mac' else 5)
            min_size = 22
            if width < min_size:
                width = min_size
            self.updateButton.setFixedWidth(width)
            self.updateButton.setFixedHeight(min_size)
            radius = min_size // 2
            bg = 'rgb(203,123,94)' if Across.active_theme == 'dark' else 'brown'
            fg = 'black' if Across.active_theme == 'dark' else '#fff'
            self.updateButton.setStyleSheet('QToolButton{font-family :"Traditional Naskh"; font-size: 18px; font-weight: 700; color: ' + fg + '; background-color: ' + bg + '; border: none; border-radius: ' + str(radius) + 'px;} QToolButton:hover {background-color: gray}')
            self.updateButton.setToolButtonStyle(Qt.ToolButtonTextOnly)
            self.updateButton.setText(count)
            self.updateButton.setIcon(Icon.icon())
            caption = self.tr('Number of Books')
            self.updateButton.setToolTip(tooltipHtml(f"{caption}: {count}", names_list))
            self.button_state = 'ready'
        else:
            self.iconize(':/icons/done.png', self.tr('All available books are downloaded'))
            self.button_state = 'initial'

    def downloadFailed(self):
        """The terminal handler for every download whose only answer to failure is
        to stop the chain and offer a retry.

        Downloader emits exactly one terminal signal, so a file download left with
        no error handler hangs the widget forever: the bar stays busy, the button
        stays hidden and `working` stays True, so not even Ctrl+U can restart it."""
        self.error(not is_connected())

    def error(self, no_net=None):
        self.error_status = True
        self.zero()
        self.working = False
        self.progress.setVisible(False)
        self.pdfButton.setVisible(False)
        if no_net:
            self.noNetGui()
        else:
            self.errorGui()

    def errorGui(self):
        self.iconize(':/icons/alert.png', self.tr('Error Updating. click to retry'))

    def noNetGui(self):
        self.iconize(':/icons/wifi.png', self.tr('Check Your internet connection and retry'))

    def secretChecked(self, data, _):
        """
        1|87|1|1|1261|{"Q":1,"S1":2,"S2":2}
        ignored|software|lucene|jre|master|services
        """
        if data == b'':
            self.error(not is_connected())
            return
        else:
            secret = self.parseSecret(data)
            secret or self.error()
            return
        self.software_version = secret['software_version']
        self.lucene_version = secret['lucene_version']
        self.jre_version = secret['jre_version']
        self.web_version = secret['web_version']
        self.web_services = secret['web_services']
        self.restart_needed = None
        self.checkApp()

    def checkService(self):
        if self.web_services[self.service_name] > self.disk_services[self.service_name]:
            self.working = True
            self.busy(self.tr('Updating Services'))
            file_base = f"{self.service_name}_{self.web_services[self.service_name]}.zip"
            local_file = os.path.join(Across.home_directory, 'database', 'service', file_base)
            if os.path.isfile(local_file):
                self.serviceDownloaded()
            else:
                url = f"https://dev.shamela.ws/services/{file_base}"
                self.downloader = Downloader(url, local_file, progressed=(self.progression), finished=(self.serviceDownloaded),
                  error=(self.downloadFailed))
        else:
            self.next_bead()

    def serviceDownloaded(self):
        self.busy(self.tr('Extracting files'))
        file_base = f"{self.service_name}_{self.web_services[self.service_name]}"
        extract_path = os.path.join(Across.home_directory, 'database', 'service')
        local_file = os.path.join(extract_path, f"{file_base}.zip")
        self.extractor = Extractor(local_file, extract_path, self.after_extraction)
        self.extractor.start()

    def checkQuran(self):
        self.service_name = 'Q'
        self.next_bead = self.checkTrajim
        self.after_extraction = self.quranExtracted
        self.checkService()

    def quranExtracted(self, value):
        if not value:
            self.error()
            return
        extracted_path = os.path.join(Across.home_directory, 'database', 'service', 'aya')
        try:
            if not replaceQuranIndex(extracted_path):
                self.error()
                return
            CoreDb().setVersion(self.service_name, self.web_services[self.service_name])
            self.next_bead()
        except:
            self.error()

    def checkTrajim(self):
        self.service_name = TRAJM
        self.next_bead = self.checkStems
        self.after_extraction = self.serviceExtracted
        self.checkService()

    def checkStems(self):
        self.service_name = STEMS
        self.next_bead = self.checkMaster
        self.after_extraction = self.serviceExtracted
        self.checkService()

    def serviceExtracted(self, value):
        if value:
            file_base = f"{self.service_name}_{self.web_services[self.service_name]}"
            extract_path = os.path.join(Across.home_directory, 'database', 'service')
            extracted_file = os.path.join(extract_path, f"{file_base}.db")
            if updateService(self.service_name, extracted_file):
                CoreDb().setVersion(self.service_name, self.web_services[self.service_name])
                self.next_bead()
            else:
                self.error()
            try:
                os.unlink(extracted_file)
            except:
                pass

        else:
            self.error()

    def checkMaster(self):
        self.disk_version = CoreDb().getVersion('master')
        if self.web_version <= self.disk_version:
            self.ok()
        else:
            self.requestMaster()

    def requestMaster(self):
        self.busy(self.tr('Checking information update'))
        from updater import UpdateRequest
        request_url = UpdateRequest.masterRequest(self.disk_version)
        self.downloader = Downloader(request_url, finished=(self.masterResponded))

    def masterResponded(self, data, status_code):
        if status_code == 204:
            self.ok()
            return
        try:
            response = str(data, encoding='utf-8')
            response = json.loads(response)
            self.web_version = response['version']
            self.patch_path = os.path.join(updateDir(), 'master', f"master-{self.disk_version}-{self.web_version}.zip")
            self.busy(self.tr('Updating Book Information'))
            if os.path.isfile(self.patch_path):
                self.masterDownloaded()
            else:
                self.downloader = Downloader((response['patch_url']), (self.patch_path), progressed=(self.progression), finished=(self.masterDownloaded),
                  error=(self.downloadFailed))
        except:
            self.error()
            return

    def masterDownloaded(self):
        self.busy(self.tr('Feeding the Software with Books Information'))
        extract_path = os.path.join(os.path.dirname(self.patch_path), os.path.splitext(os.path.basename(self.patch_path))[0])
        self.extractor = Extractor(self.patch_path, extract_path, self.masterExtracted)
        self.extractor.start()

    def masterExtracted(self, value):
        if value:
            extract_path = os.path.join(os.path.dirname(self.patch_path), os.path.splitext(os.path.basename(self.patch_path))[0])
            from updater import MasterImporter
            self.master_importer = MasterImporter(extract_path, self.web_version, self.masterImported, self.progression)
            self.master_importer.start()
        else:
            self.error()

    def masterImported(self, value):
        shutil.rmtree((os.path.join(updateDir(), 'master')), ignore_errors=True)
        if value:
            self.ok()
        else:
            self.error()

    def appUpdate(self, next_step=None):
        self.working = True
        self.busy(self.tr('Upgrading the Software'))
        self.app_next_step = next_step
        self.app_target_version = self.software_version
        arch_root = os.path.realpath(os.path.join(Across.bin_directory, os.pardir))
        os.makedirs(arch_root, exist_ok=True)
        self.local_folder = os.path.join(arch_root, 'update')
        self.local_file = f"{self.local_folder}_{self.app_target_version}.zip"
        if os.path.isfile(self.local_file):
            if isZipValid(self.local_file):
                self.appDownloaded()
                return
            kill(self.local_file)
            if os.path.isfile(self.local_file):
                self.error()
                return
        self.downloader = Downloader(f"https://dev.shamela.ws/updates/{Across.os}/{self.app_target_version}_{Across.running_arch}.zip", (self.local_file), progressed=(self.progression),
          finished=(self.appDownloaded),
          error=(self.downloadFailed))

    def appDownloaded(self):
        shutil.rmtree((self.local_folder), ignore_errors=True)
        if os.path.isdir(self.local_folder):
            self.error()
            return
        self.busy(self.tr('Installing Update'))
        self.extractor = Extractor(self.local_file, self.local_folder, self.appExtracted, self.extractProgress)
        self.extractor.start()

    def extractProgress(self, percent):
        self.progression(int(percent) or 1, 100)

    def appExtracted(self, value):
        if value:
            with open(os.path.join(self.local_folder, 'version.manifest'), 'w') as (f):
                f.write(f"{self.app_target_version}")
            self._applyLauncherAndShortcuts()
            self.restart_needed = True
            if self.app_next_step:
                app_next_step = self.app_next_step
                self.app_next_step = None
                app_next_step()
            elif self.restart_needed:
                self.askRestart()
            else:
                self.checkServices()
        else:
            self.error()

    def _applyLauncherAndShortcuts(self):
        """Install any staged Windows/Linux launcher bundled in the update and
        refresh desktop/menu shortcuts immediately after a successful app
        update, before the user is prompted to restart.
        """
        if Across.os != 'mac':
            try:
                import shamela as _sh
                staged = os.path.join(self.local_folder, _sh.STAGED_LAUNCHER_NAME)
                _sh.process_staged_launcher_container(staged)
            except Exception:
                pass

        try:
            shortcuts()
        except Exception:
            pass

    def afterAppDownload(self):
        self._applyLauncherAndShortcuts()
        self.askRestart()


def afterShow():
    arabicLayout()
    shortcuts()


def afterPrepare():
    """Deferred non-interactive work — runs once during closeEvent (after the
    window is hidden) so it never blocks the initial UI paint.  Cleanup may
    span multiple sessions if the user exits early; the next startup will
    retry anything that was skipped."""
    registerFonts()
    cleanupTildeBinFolders()
    cleanupOldRuntimeFolders()


def arabicLayout():
    if Across.os == 'win':
        if Settings.getValue('k_layout'):
            try:
                import ctypes, win32api
            except ImportError:
                return
            else:
                MAC_ARABIC_LAYOUT = '-0xf3ffbff'
                lang_dic = {'ar':'0x401',  'en':'0x409'}
                layout_list = win32api.GetKeyboardLayoutList()
                arabic = mac = None
                for layout in layout_list:
                    hex_layout = hex(layout)
                    if hex_layout == MAC_ARABIC_LAYOUT:
                        mac = layout
                        break
                    if arabic or hex_layout.startswith(lang_dic['ar']):
                        arabic = layout

                if mac:
                    arabic = mac
                if arabic:
                    ctypes.windll.user32.ActivateKeyboardLayout(arabic, 0)


class Container(QSplitter):
    tabCountChanged = Signal(int)

    def __init__(self):
        super().__init__()
        shortcut(self, 'Esc', (self.closeCurrent), context=(Qt.ShortcutContext.WindowShortcut))
        shortcut(self, 'Ctrl+W', (self.closeCurrent), context=(Qt.ShortcutContext.WindowShortcut))
        directShortcut(self, 'Ctrl+F4', (self.closeCurrent), context=(Qt.ShortcutContext.WindowShortcut))
        shortcut(self, 'Shift+Esc', (self.closeAll), context=(Qt.ShortcutContext.WindowShortcut))
        directShortcut(self, 'Shift+Ctrl+W', (self.closeAll), context=(Qt.ShortcutContext.WindowShortcut))
        shortcut(self, 'F5', (lambda: self.goActive('shortedNext')))
        shortcut(self, 'F6', (lambda: self.goActive('shortedPrevious')))
        shortcut(self, 'F4', (lambda: self.goActive('showSearch')))
        shortcut(self, 'F11', (lambda: self.goActive('switchPdf')))
        shortcut(self, 'Ctrl+F', (lambda: self.goActive('showSearch')))
        directShortcut(self, 'Ctrl+D', (lambda: self.goActive('newDisplay')))
        directShortcut(self, 'Ctrl+J', (lambda: self.goActive('switchTakreej')))
        directShortcut(self, 'Ctrl+T', (lambda: self.goActive('goText')))
        directShortcut(self, 'Ctrl+H', (lambda: self.goActive('goTree')))
        directShortcut(self, 'Ctrl+I', (lambda: self.goActive('showBetaka')))
        directShortcut(self, 'Ctrl+G', (lambda: self.goActive('go')))
        directShortcut(self, 'Ctrl+R', (lambda: self.goActive('focusResults')))
        shortcut(self, 'Backspace', (lambda: self.goActive('shortBack')))
        shortcut(self, 'Del', (lambda: self.goActive('shortDelete')))
        shortcut(self, 'Shift+Backspace', (lambda: self.goActive('shortForward')))
        directShortcut(self, 'Ctrl+Shift+R', (lambda: self.goActive('focusBookResults')))
        shortcut(self, 'Alt+T', self.show_tab_menu)
        self.first_widget = CustomTab(self)
        self.second_widget = CustomTab(self)
        self.addWidget(self.first_widget)
        self.addWidget(self.second_widget)
        self.setHandleWidth(3)
        self.setChildrenCollapsible(False)
        self.last_notified = -1
        self.first_widget.currentChanged.connect(self.tabsChanged)
        self.second_widget.currentChanged.connect(self.tabsChanged)
        self.first_widget.moveMe.connect(self.moveFromFirst)
        self.second_widget.moveMe.connect(self.moveFromSecond)
        self.first_widget.closeOthers.connect(self.closeOthersFirst)
        self.second_widget.closeOthers.connect(self.closeOthersSecond)
        self.first_widget.separateMe.connect(self.separateFromFirst)
        self.second_widget.separateMe.connect(self.separateFromSecond)
        self.first_widget.clicked.connect(self.firstClicked)
        self.second_widget.clicked.connect(self.secondClicked)
        self.active_pane = 1
        self.second_widget.hide()
        self.separated = []

    def show_tab_menu(self):
        self.activePane().show_tab_menu()

    def reText(self):
        self.first_widget.reText()
        self.second_widget.reText()

    def firstClicked(self):
        self.active_pane = 1
        self.first_widget.currentWidget().setFocus()

    def secondClicked(self):
        self.active_pane = 2
        self.second_widget.currentWidget().setFocus()

    def goActive(self, function_name):
        pane = self.activePane()
        if pane.count():
            widget = pane.currentWidget()
            if hasattr(widget, function_name):
                getattr(widget, function_name)()

    def separateFromFirst(self, index):
        self.separate(self.first_widget, index)
        Across.main_window.dual.notify(True)

    def separateFromSecond(self, index):
        self.separate(self.second_widget, index)

    def separate(self, pane=None, index=None):
        if not pane:
            pane = self.activePane()
        else:
            if pane.count() == 0:
                return
            index = index or pane.currentIndex()
        widget, icon, title, tool_tip = (
         pane.widget(index), pane.tabIcon(index), pane.widget(index).full_title, pane.tabToolTip(index))
        self.separated.append([widget, icon, title, tool_tip])
        pane.removeTab(index)
        widget.setWindowIcon(icon)
        widget.setWindowTitle(title)
        widget.setParent(None)
        widget.setWindowFlag(Qt.Window, True)
        widget.closed.connect(self.closeSeparated)
        factor = 0.6666666666666666
        widget.resize(int(Across.main_window.width() * factor), int(Across.main_window.height() * factor))
        widget.show()

    def join(self):
        if self.separated:
            pane = self.activePane()
            for widget, icon, title, tool_tip in self.separated:
                widget.hide()
                self.showInTab(widget, icon, title, tool_tip, pane)

            self.separated = []
            Across.main_window.mainArea.setCurrentWidget(self)

    def closeSeparated(self, widget):
        deleted = -1
        for i, item in enumerate(self.separated):
            if widget is item[0]:
                widget.deleteLater()
                deleted = i
                break

        if deleted != -1:
            del self.separated[deleted]
        self.notify()

    def tabsCount(self):
        return self.first_widget.count() + self.second_widget.count()

    def totalCount(self):
        return len(self.separated) + self.first_widget.count() + self.second_widget.count()

    def notify(self, forced=None):
        count = self.totalCount()
        if forced or count != self.last_notified:
            self.last_notified = count
            self.tabCountChanged.emit(count)

    def setTabText(self, widget, text):
        pane = self.activePane()
        index = pane.indexOf(widget)
        if widget is pane.currentWidget():
            index = pane.currentIndex()
        pane.setTabText(index, five(text))
        pane.setTabToolTip(index, text)

    def focusCheck(self, _, w):
        try:
            while 1:
                w = w.parent()
                if not w:
                    break
                if w is self.first_widget:
                    self.active_pane = 1
                    return
                if w is self.second_widget:
                    self.active_pane = 2
                    return

        except:
            pass

    def closeCurrent(self):
        for w in reversed(Across.dialog_stack):
            if w.isVisible():
                w.close()
                return

        self.activePane().closeCurrent()

    def tabsChanged(self):
        if self.second_widget.count() == 0:
            if self.first_widget.count() == 0:
                Across.main_window.showBackground()
            else:
                self.second_widget.hide()
        elif self.first_widget.count() == 0:
            self.oneSpace()
        self.notify()

    def activePane(self):
        if not self.second_widget.isVisible():
            return self.first_widget
        if self.active_pane == 2:
            return self.second_widget
        return self.first_widget

    def showInTab(self, frame, icon, title, tab_tip, pane):
        target_pane = pane or self.activePane()
        tab_index = target_pane.count()
        frame.full_title = title
        fived_title = five(title)
        frame.hide()
        frame.setWindowFlag(Qt.Window, False)
        frame.setParent(target_pane)
        target_pane.insertTab(tab_index, frame, icon, fived_title)
        if not tab_tip:
            tab_tip = tip(title)
        target_pane.setTabToolTip(tab_index, tab_tip)
        if not pane:
            target_pane.setCurrentIndex(tab_index)
            target_pane.show()

    def vertical(self):
        if self.first_widget.count() < 2:
            if not self.second_widget.isVisible():
                return
        if self.second_widget.count() == 0:
            self.movetab(self.first_widget, self.second_widget)
        self.setOrientation(Qt.Horizontal)
        self.second_widget.setVisible(True)

    def horizontal(self):
        if self.first_widget.count() < 2:
            if not self.second_widget.isVisible():
                return
        if self.second_widget.count() == 0:
            self.movetab(self.first_widget, self.second_widget)
        self.setOrientation(Qt.Vertical)
        self.second_widget.setVisible(True)

    def moveFromFirst(self, index):
        if self.first_widget.count() < 2:
            self.oneSpace()
        else:
            self.movetab(self.first_widget, self.second_widget, index)

    def moveFromSecond(self, index):
        self.movetab(self.second_widget, self.first_widget, index)

    def closeOthersFirst(self, tab):
        self.closeOthers(self.first_widget, self.second_widget, tab)

    def closeOthersSecond(self, tab):
        self.closeOthers(self.second_widget, self.first_widget, tab)

    def closeNonActive(self):
        one = self.activePane()
        tab = one.currentIndex()
        zero = self.second_widget if one is self.first_widget else self.first_widget
        self.closeOthers(one, zero, tab)

    def closeOthers(self, one, zero, tab):
        zero.blockSignals(True)
        for i in reversed(range(zero.count())):
            zero.closeTab(i)

        zero.hide()
        one.blockSignals(True)
        for i in reversed(range(tab)):
            one.closeTab(i)

        count = one.count()
        for i in reversed(range(1, count)):
            one.closeTab(i)

        zero.blockSignals(False)
        one.blockSignals(False)
        self.notify()

    def oneSpace(self):
        count = self.second_widget.count()
        if count != 0:
            self.first_widget.blockSignals(True)
            self.second_widget.blockSignals(True)
            for i in range(count):
                Container.abstractMove(self.second_widget, self.first_widget, 0)

            self.second_widget.setVisible(False)
            self.first_widget.setVisible(True)
            self.first_widget.blockSignals(False)
            self.second_widget.blockSignals(False)

    def movetab(self, from_widget, to_widget, index=None):
        if from_widget.count() < 2:
            if not to_widget.isVisible():
                return
        if index is None:
            index = from_widget.currentIndex()
        if index < 0:
            return
        self.block(True)
        Container.abstractMove(from_widget, to_widget, index)
        self.block(False)
        to_widget.setVisible(True)
        self.tabsChanged()

    @staticmethod
    def abstractMove(from_widget, to_widget, index):
        tab_tip = from_widget.tabToolTip(index)
        title = from_widget.tabText(index)
        icon = from_widget.tabIcon(index)
        frame = from_widget.widget(index)
        from_widget.removeTab(index)
        to_index = to_widget.currentIndex() + 1
        to_widget.insertTab(to_index, frame, icon, title)
        to_widget.setTabToolTip(to_index, tab_tip)

    def closeAll(self):
        Across.main_window.showBackground()
        QApplication.processEvents()
        switchUser(True)
        self.shut()
        switchUser(False)
        self.second_widget.hide()

    def shut(self):
        for widget in [self.first_widget, self.second_widget]:
            count = widget.count()
            widget.blockSignals(True)
            for i in reversed(range(count)):
                widget.closeTab(i)

            widget.blockSignals(False)

        for items in self.separated:
            items[0].closeTab()

        self.notify()

    def save(self, context_id):
        self.join()
        if self.first_widget.count() != 0:
            session = {'orientation':1 if self.orientation() == Qt.Vertical else 0, 
             'first':self.first_widget.save(context_id)}
            second_contents = self.second_widget.save(context_id)
            if second_contents:
                session['second'] = second_contents
            return session

    def block(self, value):
        self.first_widget.blockSignals(value)
        self.second_widget.blockSignals(value)
        self.first_widget.setUpdatesEnabled(not value)
        self.second_widget.setUpdatesEnabled(not value)

    def load(self, session):
        self.block(True)
        self.fill(session)
        self.block(False)
        self.tabsChanged()

    def unload(self):
        switchUser(True)
        self.shut()
        switchUser(False)
        Across.main_window.showBackground()

    def fill(self, session):
        loading_cache = CoreDb().loadingCache(session)
        try:
            if session['first']:
                self.setOrientation(Qt.Vertical if session['orientation'] == 1 else Qt.Horizontal)
                index, items = session['first']
                for item in items:
                    Across.main_window.load(item, self.first_widget, loading_cache)

                if 'float' in session:
                    for item in session['float']:
                        Across.main_window.load(item, self.first_widget, loading_cache)

                self.first_widget.setCurrentIndex(index)
                if 'second' in session:
                    if session['second']:
                        index, items = session['second']
                        for item in items:
                            Across.main_window.load(item, self.second_widget, loading_cache)

                        self.second_widget.setCurrentIndex(index)
                        self.second_widget.setVisible(True)
                Across.main_window.mainArea.setCurrentWidget(self)
            else:
                self.unload()
        except:
            self.unload()


class MainWindow(ShiftedWidget):

    def __init__(self, app):
        super().__init__()
        Across.main_window = self
        Across.global_index = Index
        register_shutdown_handlers()
        screen = self.getScreen()
        from scaling import init_scaling, scaled_font_size
        init_scaling(screen)
        ui_font = QFont(Across.ui_font_family, scaled_font_size(10))
        ui_font.setHintingPreference(QFont.PreferFullHinting)
        app.setFont(ui_font)
        self.setWindowTitle(self.tr('Shamela Library'))
        if Across.os == 'mac':
            if hasattr(Qt, 'WA_MacAlwaysShowToolWindow'):
                self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
            else:
                switchBoth(True)
                settings = QSettings('shamela.ws', 'main_window')
                try:
                    self.restoreGeometry(settings.value('geometry', ''))
                except:
                    self.setWindowState(Qt.WindowMaximized)

            if not self.restoredGeometryScreen():
                screen_geometry = screen.availableGeometry()
                frame = self.frameGeometry()
                if frame.width() > screen_geometry.width() or frame.height() > screen_geometry.height():
                    self.setGeometry(screen_geometry)
                    self.setWindowState(self.windowState() | Qt.WindowMaximized)
        else:
            self.move(screen_geometry.center() - self.rect().center())
        directShortcut(self, 'Ctrl+1', self.goCategories)
        directShortcut(self, 'Ctrl+2', self.goAuthors)
        directShortcut(self, 'Ctrl+3', self.goHistory)
        self.search_window = self.email = self.saved = self.biblio = self.select_window = self.options_window = self.quran_window = self.control = self.update = self.pdf = self.option = self.release = self.book_downloader = self.pdf_downloader = self.imageLabel = None
        self.master = None
        self.cover_downloader = CoverDownloader()
        Across.dialog_state = UserDb().load('dialoge_state', {})
        self.mainArea = QStackedWidget()
        self.dual = Container()
        app.focusChanged.connect(self.dual.focusCheck)
        self.mainArea.addWidget(self.dual)
        self.dual.tabCountChanged.connect(self.tabStatus)
        quran_shortcut = 'Ctrl+Q'
        buttons = [
         (
          self.tr('Select a book'), ':/icons/open_book.png', self.showSelectBook, 'F10', True),
         (
          self.tr('Holy Quran'), ':/icons/quran.png', self.showQuran, quran_shortcut, False),
         (
          self.tr('Search'), ':/icons/search.png', self.showSearch, 'F3', True),
         (
          self.tr('Control Panel'), ':/icons/control_panel.png', self.controlPanel, 'F2', True),
         (
          self.tr('Biography and bibliography'), ':/icons/authors.png', self.showbiblio, None, True),
         (
          self.tr('Saved Sessions and Searches'), ':/icons/save2.png', self.showSaved, 'Ctrl+L', False),
         (
          self.tr('Windows'), ':/icons/win.png', None, None, True),
         (
          self.tr('Options'), ':/icons/options.png', self.showOptions, 'Ctrl+O', False),
         (
          self.tr('About the software'), ':/icons/email.png', self.aboutWindow, None, True),
         (
          self.tr('Donate'), ':/icons/donate.png', self.donate, None, True)]
        upper_widgets = []
        self.tab_actions = {}
        for button in buttons:
            text, icon, slot, shortkey, wrapped = button
            if shortkey:
                if wrapped:
                    shortcut(self, shortkey, slot)
                    text = shortcutLabel(text, shortkey)
                else:
                    directShortcut(self, shortkey, slot)
                    text = directShortcutLabel(text, shortkey)
            button = customToolButton(icon, text, slot=slot, iconsize=24)
            if not slot:
                self.windowsButton = button
                button.setStyleSheet(button.styleSheet() + '\n::menu-indicator{image: none;}')
                button.setPopupMode(QToolButton.InstantPopup)
                menu = QMenu(button)
                items = (self.tr('Arranged Vertically'), self.tr('Arranged Horizontally'), self.tr('one window'),
                 self.tr('Separate tab'), self.tr('join separated tabs'), self.tr('Close This Tab') + '\tEsc', self.tr('Close All Tabs') + '\tShift  Esc',
                 self.tr('Close Other Tabs'))
                names = ('vertical', 'horizontal', 'one', 'separate', 'join', 'this',
                         'all', 'others')
                actions = []
                group = QActionGroup(self)
                for i, item in enumerate(items):
                    action = QAction(item)
                    if i < 5:
                        action.setIcon(Icon.icon(f":/icons/{names[i]}.png"))
                    menu.addAction(action)
                    group.addAction(action)
                    self.tab_actions[names[i]] = action
                    action.triggered.connect(partial(self.changeWindowStatus, i))
                    actions.append(action)
                    if not i == 2:
                        if i == 4:
                            pass
                        menu.addSeparator()

                button.setMenu(menu)
            upper_widgets.append(button)

        self.progress = Progress()
        self.searchLine = LineEdit(digit_policy='ascii', slot=(self.globalSearch), width=200)
        self.searchLine.setObjectName('searchLine')
        self.searchLine.setPlaceholderText(self.tr('Search in All Books'))
        self.update_widget = UpdateWidget(self.progress, self.searchLine)
        upper_widgets += [self.update_widget, 2]
        self.auto_book = self.auto_pdf = self.auto_minors = None
        upper_layout = customLayout(False, upper_widgets, margins=0)
        self.setLayout(customLayout(True, [upper_layout, self.mainArea], margins=1))
        self.mainArea.setFocus()
        session = None
        if len(sys.argv) > 1:
            if sys.argv[1].startswith('{'):
                try:
                    session = json.loads(sys.argv[1])
                except:
                    pass

        else:
            if not Across.no_update:
                if Settings.getValue('restore_last_session'):
                    if not os.path.isfile(emptyLastSessionFlag()):
                        session = UserDb().lastSession()
            elif session:
                Across.main_window.dual.load(session)
            else:
                self.showBackground()
            self.dual.notify()
            self.show()
            switchBoth(False)
            release_file = os.path.join(Across.bin_directory, 'release_update.txt')
            if os.path.isfile(release_file):
                kill(release_file)
                QTimer.singleShot(0, self.showRelease)
            QTimer.singleShot(0, afterShow)

    def getScreen(self):
        screen = None
        try:
            screen = self.screen()
        except:
            pass

        if not screen:
            try:
                handle = self.windowHandle()
                if handle:
                    screen = handle.screen()
            except:
                pass

        if not screen:
            try:
                screen = QGuiApplication.screenAt(self.frameGeometry().center())
            except:
                pass

        if not screen:
            screen = QApplication.primaryScreen()
        return screen

    def restoredGeometryScreen(self):
        rect = self.frameGeometry()
        if rect.isNull():
            return
        try:
            screen = QGuiApplication.screenAt(rect.center())
            if screen:
                return screen
        except:
            pass

        try:
            for screen in QGuiApplication.screens():
                if screen.availableGeometry().intersects(rect):
                    return screen

        except:
            pass

    def globalSearch(self):
        text = treatSearch(self.searchLine.text())
        if text:
            query = Query(Across.global_index)
            query.load({'phrases': [[[text]], [], []]})
            self.showSearchResults(query, None)

    def tabStatus(self, total_count):
        separated_count = len(self.dual.separated)
        tab_count = total_count - separated_count
        self.windowsButton.setEnabled(total_count != 0)
        self.tab_actions['join'].setEnabled(separated_count != 0)
        if tab_count == 0:
            self.tab_actions['separate'].setEnabled(False)
            self.tab_actions['this'].setEnabled(False)
            self.tab_actions['all'].setEnabled(False)
            self.tab_actions['others'].setEnabled(False)
            self.tab_actions['one'].setEnabled(False)
            self.tab_actions['vertical'].setEnabled(False)
            self.tab_actions['horizontal'].setEnabled(False)
        else:
            self.tab_actions['separate'].setEnabled(True)
            self.tab_actions['this'].setEnabled(True)
            self.tab_actions['all'].setEnabled(True)
            if tab_count == 1:
                self.tab_actions['others'].setEnabled(False)
                self.tab_actions['one'].setEnabled(False)
                self.tab_actions['vertical'].setEnabled(False)
                self.tab_actions['horizontal'].setEnabled(False)
            else:
                self.tab_actions['others'].setEnabled(True)
                if self.dual.second_widget.count():
                    self.tab_actions['one'].setEnabled(True)
                    is_vertical = self.dual.orientation() == Qt.Vertical
                    self.tab_actions['vertical'].setEnabled(is_vertical)
                    self.tab_actions['horizontal'].setEnabled(not is_vertical)
                else:
                    self.tab_actions['one'].setEnabled(False)
                    self.tab_actions['vertical'].setEnabled(True)
                    self.tab_actions['horizontal'].setEnabled(True)

    def setTabText(self, widget, text):
        self.dual.setTabText(widget, text)

    def showInTab(self, frame, icon=Icon.icon(''), title='', tab_tip='', pane=None):
        self.dual.showInTab(frame, icon, title, tab_tip, pane)
        if not pane:
            self.mainArea.setCurrentWidget(self.dual)

    def showSearchResults(self, query, pane=None):
        title = singlePhrase(query.phrases)
        from search_base import WidgetResults

        def add_tab(frame):
            self.showInTab(frame, (Icon.icon(':/icons/search.png')), ('{}: {}'.format(self.tr('Search'), title)), pane=pane)

        WidgetResults(query, show_tab=add_tab)

    def showBook(self, book_id, page_id=None, full_display=None, search_res=None, afterfunction=None, search_info=None, pane=None, loading_cache=None):
        cached = loading_cache[book_id] if loading_cache else None
        if cached:
            return cached['is_ondisk'] or None
        else:
            if not CoreDb().isOnDisk(book_id):
                return
                if not full_display:
                    if not search_res:
                        if self.select_window:
                            self.select_window.hide()
            else:
                page_id = page_id or 1
            from cache import BookCache
            from displaybook import DisplayBook
            icon = cached['icon'] if cached else BookCache.bookIcon(book_id)
            title = cached['title'] if cached else BookCache.abstractName(book_id)
            betaka = cached['betaka_tip'] if cached else conditioned(CoreDb().bookBetaka(book_id, True, truncated=True))
            frame = DisplayBook(book_id, page_id, full_display=full_display, search_res=search_res, afterfunction=afterfunction, search_info=search_info)
            self.showInTab(frame, icon, title, betaka, pane)

    def showQuran(self):
        from quran import QuranWidget
        quran_window = QuranWidget()
        self.showInTab(quran_window, Icon.icon(':/icons/quran.png'), self.tr('Holy Quran'))

    def showbiblio(self, forced=None):
        from searchbiblio import BiblioWidget
        biblio = BiblioWidget()
        self.showInTab(biblio, Icon.icon(':/icons/authors.png'), self.tr('Biography and bibliography'))
        if forced == 'authors':
            biblio.listwidget.showAuthors()
        else:
            if forced == 'books':
                biblio.listwidget.showBibliography()

    def load(self, item, pane, loading_cache=None):
        key, value = item
        if key == 'BOOK':
            search_data = value['search'] if 'search' in value else None
            self.showBook((value['book']), (value['page']), search_info=search_data, pane=pane, loading_cache=loading_cache)
        else:
            if key == 'SEARCH':
                query = Query(Across.global_index)
                query.load(value)
                self.showSearchResults(query, pane)
            else:
                if key == 'INFO':
                    from searchbiblio import BiblioWidget
                    biblio = BiblioWidget(saved_value=value)
                    self.showInTab(biblio, (Icon.icon(':/icons/authors.png')), (self.tr('Biography and bibliography')), pane=pane)
                else:
                    if key == 'QURAN':
                        from quran import QuranWidget
                        quran = QuranWidget(saved_value=value)
                        self.showInTab(quran, (Icon.icon(':/icons/quran.png')), (self.tr('Holy Quran')), pane=pane)
                    else:
                        if key == 'MAN':
                            from rijal import separateMan
                            separateMan((value['id']), (value['list']), pane=pane)
                        else:
                            if key == 'TOROQ':
                                from rijal import separateTree
                                separateTree((value['hadeeth']), pane=pane)
                            else:
                                if key == 'TAKREEJ':
                                    from rijal import separateTakreej
                                    separateTakreej((value['hadeeth']), (value['single']), pane=pane)

    def changeWindowStatus(self, status):
        dual = self.dual
        functions = [dual.vertical, dual.horizontal, dual.oneSpace,
         dual.separate, dual.join,
         dual.closeCurrent, dual.closeAll, dual.closeNonActive]
        functions[status]()
        self.dual.notify(True)

    def startBook(self):
        if not Settings.getValue('auto_download_books'):
            return
        else:
            if not self.update_widget.button_state == 'ready':
                return
            else:
                return CoreDb().hasNewBooks() or None
            from updater import Auto
            self.auto_book = self.auto_book or Auto(4)
        self.auto_book.go()

    def startMinors(self):
        if CoreDb().hasMinors():
            from updater import AutoMinors
            if not self.auto_minors:
                self.auto_minors = AutoMinors()
            self.auto_minors.go()

    def startPdf(self):
        if not Settings.getValue('auto_download_pdf'):
            return
        else:
            if self.update_widget.button_state not in frozenset({'initial', 'ready'}):
                return
            else:
                if not isWritable(pdfPath()):
                    return
                return CoreDb().hasNewPdf() or None
            from updater import Auto
            self.auto_pdf = self.auto_pdf or Auto(5)
        self.auto_pdf.go()

    def stopBook(self):
        if self.auto_book:
            self.auto_book.stop()

    def stopPdf(self):
        if self.auto_pdf:
            self.auto_pdf.stop()

    def showauthors(self):
        self.showbiblio('authors')

    def showbooks(self):
        self.showbiblio('books')

    def donate(self):
        QDesktopServices.openUrl(QUrl('https://shamela.ws/page/contribute'))

    def showBackground(self):
        if not self.imageLabel:
            self.imageLabel = Qtlabel()
            self.imageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            self.imageLabel.setScaledContents(True)
            self.imageLabel.setPixmap(QPixmap.fromImage(QImage(':/images/background.jpg')))
            self.imageLabel.clicked.connect(self.showSelectBook)
            self.imageLabel.rtClicked.connect(self.showSearch)
            self.mainArea.addWidget(self.imageLabel)
        self.mainArea.setCurrentWidget(self.imageLabel)

    def showSearch(self):
        from searchwindow import SearchWindow
        if not self.search_window:
            self.search_window = SearchWindow(parent=self)
        self.search_window.show()

    def showSaved(self):
        from savebase import Saved
        if not self.saved:
            self.saved = Saved(self)
        self.saved.show()

    def aboutWindow(self):
        if not self.email:
            self.email = Email(parent=self)
        self.email.show()

    def showOptions(self, list_item=None, highlight=None):
        from options import OptionsWindow
        if not (self.option and self.option.isVisible()):
            self.option = OptionsWindow(self)
        self.option.show()
        if list_item or highlight:
            self.option.goPage(list_item, highlight)

    def showSelectBook(self):
        if not self.select_window:
            self.select_window = SelectBook(parent=self)
        self.select_window.show()

    def doubleShift(self):
        self.showSelectBook()
        self.select_window.select_widget.doubleShift()

    def goCategories(self):
        self.showSelectBook()
        self.select_window.select_widget.showCategories()

    def goAuthors(self):
        self.showSelectBook()
        self.select_window.select_widget.showAuthors()

    def goHistory(self):
        self.showSelectBook()
        self.select_window.select_widget.showHistory()

    def controlPanel(self):
        from controlwindow import ControlWindow
        if not self.control:
            self.control = ControlWindow(parent=self)
        self.control.show()

    def showUpdate(self, forgive=None):
        if not CoreDb().hasNewBooks():
            if not forgive:
                customMessage(self.tr('No New Books'), self.tr('No new Books to download'))
            return
        from updatewindow import UpdateWindow
        if not self.update:
            self.update = UpdateWindow(context=4, parent=self)
        self.update.show()
        self.startBook()

    def showPdf(self, forgive=None):
        if not CoreDb().hasNewPdf():
            if not forgive:
                customMessage(self.tr('No New Books'), self.tr('No new Books to download'))
        else:
            return
            pdf_folder = pdfPath()
            default_folder = defaultPdfPath()
            if not os.path.isdir(pdf_folder):
                if pdf_folder == default_folder:
                    os.makedirs(pdf_folder, exist_ok=True)
                    if os.path.isdir(pdf_folder):
                        pass
                    else:
                        if not forgive:
                            customMessage(self.tr('Pdf folder'), self.tr('Pdf folder is not existent'))
                        return
                else:
                    if not forgive:
                        customMessage(self.tr('Pdf folder'), self.tr('Pdf folder is not existent'))
                    return
            else:
                isWritable(pdf_folder) or forgive or customMessage(self.tr('Pdf folder'), self.tr('Pdf folder is not writable'))
            return
        if not self.pdf:
            from updatewindow import UpdateWindow
            self.pdf = UpdateWindow(context=5, parent=self)
        self.pdf.show()

    @staticmethod
    def stepPercent(read, total):
        """the percent of the step being reported, or BUSY where it has none.

        A server that sends no size gives total <= 0: that is a live download
        that simply cannot be counted, not a finished or an idle one."""
        if read < 0 or total <= 0:
            return Across.BUSY
        return min(99, max(1, int(read / total * 100)))

    def bookDownloadProgress(self, book_id, read, total):
        if read == 0:
            Across.downloading_books[book_id] = Across.QUEUED
        else:
            if total == 0:
                if book_id in Across.downloading_books:
                    Across.importing_books[book_id] = Across.QUEUED
                    del Across.downloading_books[book_id]
                else:
                    Across.downloading_books[book_id] = self.stepPercent(read, total)
            else:
                BusySpinner.poke()
                if self.update and self.update.isVisible():
                    self.update.refresh()

    def bookProgress(self, book_id, read, total):
        from cache import BookCache
        BookCache.clear(book_id)
        if total == 0:
            if book_id in Across.importing_books:
                del Across.importing_books[book_id]
                self.updateCount()
                self.startPdf()
                self.reinstallWindows()
        else:
            Across.importing_books[book_id] = self.stepPercent(read, total)
            BusySpinner.poke()
            if self.update:
                if self.update.isVisible():
                    self.update.refresh()

    def pdfProgress(self, book_id, percent):
        if percent == 1000:
            if book_id in Across.downloading_pdfs:
                del Across.downloading_pdfs[book_id]
                from cache import BookCache
                BookCache.clear(book_id)
                self.reinstallWindows()
                self.checkPdfIcon()
        else:
            if percent == 100:
                percent = 99
            Across.downloading_pdfs[book_id] = percent
            BusySpinner.poke()
            if self.pdf:
                if self.pdf.isVisible():
                    self.pdf.refresh()

    @staticmethod
    def reinstallWindows():
        for widget in Across.refresh_set:
            widget.reinstall()

    def updateCount(self):
        self.update_widget.updateCount()

    def checkPdfIcon(self):
        self.update_widget.checkPdfIcon()

    def showRelease(self):
        if not self.release:
            pk_path = os.path.join(Across.bin_directory, 'release.pk')
            if not os.path.isfile(pk_path):
                return
            try:
                names, contents = unpack(pk_path)
            except:
                return
                if not isinstance(names, list):
                    return
                return isinstance(contents, list) or None

            self.release = ReleaseNotes(self, names, contents)
        self.release.show()

    def sizeHint(self):
        handle = self.window().windowHandle()
        if handle:
            rec = handle.screen().availableGeometry()
            return QSize(int(rec.width() / 1.5), int(rec.height() / 1.5))
        return super().sizeHint()

    def preClose(self):
        settings = QSettings('shamela.ws', 'main_window')
        settings.setValue('geometry', self.saveGeometry())
        for w in Across.hidden_set:
            w.close()

        for item in self.dual.separated:
            item[0].setVisible(False)

        self.setVisible(False)

    def closeEvent(self, event):
        global lock
        for w in QApplication.topLevelWidgets():
            if w is not self and w.isVisible():
                w.hide()

        self.hide()
        QApplication.processEvents()
        afterPrepare()
        switchBoth(True)
        self.preClose()
        user_db = UserDb()
        user_db.save('dialoge_state', Across.dialog_state)
        new_id = user_db.newSessionId()
        context_id = f"session_history_{new_id}"
        flag_path = emptyLastSessionFlag()
        session = self.dual.save(context_id)
        if session:
            user_db.addSessionHistory(session, new_id)
            kill(flag_path)
        else:
            with open(flag_path, 'w') as (f):
                f.write('')
        for w in Across.hidden_set:
            w.deleteLater()

        self.dual.shut()
        Index.begin_shutdown()
        try:
            from search import Searcher
            Searcher.stopAll()
        except:
            pass

        importer_thread = Across.importer_thread
        if importer_thread:
            if importer_thread.isRunning():
                try:
                    importer_thread.stop()
                except:
                    pass

                importer_thread.wait()
        for thread in list(Across.background_threads):
            try:
                thread.join()
            except:
                pass

        Index.clear()
        try:
            lock.release()
        except:
            pass

        switchBoth(False)
        event.accept()


class SelectBook(CustomDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent, geometry_name='select_complex', icon=':/icons/open_book.png')
        self.setWindowTitle(self.tr('Select book'))
        from selectwidget import SelectWidget
        self.select_widget = SelectWidget(context=1)
        customLayout(True, [self.select_widget], parent=self)
        self.select_widget.go()


class Email(CustomDialog):

    def __init__(self, parent=None):
        super().__init__(fixed=True, parent=parent, icon=':/icons/email.png')
        FONT = 'Traditional Naskh'
        is_dark = Across.active_theme == 'dark'
        sz_title = 7
        sz_about = sz_version = 5
        sz_mail = sz_url = 3
        palette = QApplication.palette()
        link_color = '#0000ff' if not is_dark else palette.color(QPalette.Active, QPalette.Link).name()
        title_color = link_color if is_dark else 'brown'
        version_color = link_color
        link_style = 'text-decoration:none; color:' + link_color + ';'
        self.setWindowTitle('راسل المكتبة الشاملة')
        title_label = QLabel(f'<b><font face="{FONT}" size={sz_title}>المكتبة الشاملة</font></b>')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet('QLabel {color: ' + title_color + ';}')
        about_text = 'برنامج مجاني يهدف لجمع ما يحتاجه طالب العلم من كتب وبحوث<br>في العلوم الشرعية وما يتعلق بها من علوم الآلة<br>في صيغة نصية قابلة للبحث والنسخ'
        about_label = QLabel(f'<font face="{FONT}" size={sz_about}>{about_text}</font>')
        img = image(':/icons/shamela.png', 48, old=True)
        img = customLayout(True, [0, img, 0])
        vertical = customLayout(True, [about_label])
        horizontal = customLayout(False, [vertical, img])
        mail_label = styledLabel(height=33)
        mail_label.setText(f"<font size={sz_mail}>" + self.tr('For contact and sending books ') + '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' + f'<a href="mailto:mail@shamela.ws" style="{link_style}">mail@shamela.ws</a></font>')
        mail_label.setOpenExternalLinks(True)
        version_label = QLabel(f'<font face="{FONT}" size={sz_version}><b>{VERSION_MONTH}{arabize(VERSION_YEAR, forced=True)}</b></font>')
        version_label.setStyleSheet('QLabel {color: ' + version_color + ';}')
        url_label = QLabel(f'<font size={sz_url}><a href="https://shamela.ws" style="{link_style}">https://shamela.ws</a></font>')
        url_label.setOpenExternalLinks(True)
        books, authors = CoreDb().booksAuthorsCount()
        books = clickableLabel((self.tr('Books Count: ') + arabize((str(books)), forced=True)), tooltip=(self.tr('Open Books Info Screen')), slot=(Across.main_window.showbooks))
        authors = clickableLabel((self.tr('Authors Count: ') + arabize((str(authors)), forced=True)), tooltip=(self.tr('Open Authors Info Screen')), slot=(Across.main_window.showauthors))
        count = customLayout(False, [books, 0, authors])
        push = clickableLabel(text=(self.tr('Release Notes')), slot=(self.showRelease))
        side_width = max(version_label.sizeHint().width(), url_label.sizeHint().width())
        version_label.setFixedWidth(side_width)
        version_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        url_label.setFixedWidth(side_width)
        url_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lower = customLayout(False, ['version_label', 0, 'push', 0, 'url_label'])
        self.setLayout(customLayout(True, [title_label, 7, horizontal, 3, mail_label, 7, hLine(), 7, count, 10, hLine(), 10, lower, 7], margins=[10, 1, 10, 1]))

    def showRelease(self):
        Across.main_window.showRelease()


class ReleaseNotes(CustomDialog):

    def __init__(self, parent, names, contents):
        super().__init__(parent=parent, icon=':/icons/period.png')
        self.setWindowTitle(self.tr('Release Notes'))
        minSize(self, 650, 450)
        font_pt = 14
        font = QtFont(['Traditional Naskh', font_pt, True])
        label = styledLabel(height=40)
        label.setFont(font)
        label.setText(self.tr('You can reach this from from (release notes button) on about software screen'))
        self.contents = contents
        self.text_browser = flexibleBrowser()
        self.list_items = QListWidget()
        for name in names:
            self.list_items.addItem(QListWidgetItem(Icon.icon(':/icons/period.png'), name))

        self.list_items.setFont(font)
        self.list_items.setFixedWidth(190)
        self.list_items.currentRowChanged.connect(self.displayItem)
        self.list_items.setCurrentRow(0)
        lay = customLayout(False, [self.list_items, self.text_browser], margins=0, spacing=3)
        lay = customLayout(True, [3, label, 3, lay], margins=3, spacing=3)
        self.setLayout(lay)

    def displayItem(self, index):
        from textmanager import formatBetaka
        text = f"<span class='title'>{self.list_items.currentItem().text()}</span>\n<hr>\n{self.contents[index]}"
        self.text_browser.setHtml(self.healItem(formatBetaka(text, None, None, None, None)))

    def healItem(self, text):
        text = text.replace('Ctr ١', 'Ctr 1').replace('Ctr ٢', 'Ctr 2').replace('Ctr ٣', 'Ctr 3')
        text = text.replace('F٢', 'F2').replace('F٣', 'F3').replace('F٤', 'F4').replace('F٥', 'F5').replace('F٦', 'F6').replace('F١٠', 'F10').replace('F١١', 'F11')
        return normalizeShortcutLabel(text)


class CoverDownloader:

    def __init__(self):
        self.download_list = self.downloader = self.runonce = None
        self.working = None
        self.retried = set()

    def download(self):
        if self.working:
            return
        self.runonce = self.runonce or True
        try:
            if not CoverDb().ensureClean():
                return
            self.download_list = CoreDb().coverList()
        except Exception:
            return

        if self.download_list:
            self.working = True
            current = self.download_list.pop(0)
            self.downloader = Downloader(f"https://dev.shamela.ws/covers/{current[0]}.jpg?{current[1]}", finished=(partial(self.done, current)))

    def done(self, current, data, _):
        self.working = None
        if not QImage.fromData(data).isNull():
            CoverDb().save(current, data)
        else:
            if current[0] not in self.retried:
                self.retried.add(current[0])
                self.download_list.append(current)
        self.download()


class QtMenu(QMenu):
    __doc__ = '\n    supports a different action on right click\n    '

    def __init__(self, parent):
        super().__init__(parent)
        self.tab_widget = parent
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightClicked)

    def rightClicked(self, pos):
        action = self.actionAt(pos)
        if action:
            menu_index = self.actions().index(action)
            current_index = menu_index - 2
            self.tab_widget.closeTab(current_index)
            self.tab_widget.countTabs()
            self.removeAction(action)
            action = self.actions()
            max_index = len(action) - 1
            if max_index < 2:
                self.hide()
            else:
                if menu_index > max_index:
                    menu_index -= 1
                self.setActiveAction(action[menu_index])

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.RightButton:
            super().mouseReleaseEvent(event)


class MacCtrlShortcutFilter(QObject):
    duplicate_sequences = ('Ctrl+A', 'Ctrl+C', 'Ctrl+F', 'Ctrl+S', 'Ctrl+V', 'Ctrl+W',
                           'Ctrl+X')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.forwarding = False
        self._pending_backward = 0

    def _forwardAsWrapped(self, watched, event):
        target = watched if hasattr(watched, 'event') else QApplication.focusWidget()
        if not target:
            return False
        modifiers = Qt.ControlModifier
        if event.modifiers() & Qt.ShiftModifier:
            modifiers |= Qt.ShiftModifier
        clone = QKeyEvent(event.type(), event.key(), modifiers, event.text(), event.isAutoRepeat(), event.count())
        self.forwarding = True
        try:
            QApplication.sendEvent(target, clone)
        finally:
            self.forwarding = False

        return True

    def _cycleTab(self, forward: bool) -> bool:
        """Cycle tabs in the active pane (Meta+Tab / Meta+Shift+Tab on Mac)."""
        try:
            dual = Across.main_window.dual
        except AttributeError:
            return False
        else:
            pane = dual.activePane()
            count = pane.count()
            if count < 2:
                return False
            current = pane.currentIndex()
            next_index = (current + 1) % count if forward else (current - 1) % count
            pane.setCurrentIndex(next_index)
            return True

    def eventFilter(self, watched, event):
        if not Across.os != 'mac':
            if self.forwarding:
                return False
            evt_type = event.type()
            if evt_type in {QEvent.KeyPress, QEvent.KeyRelease}:
                key = event.key()
                mods = event.modifiers()
                if key == Qt.Key_Meta:
                    if evt_type == QEvent.KeyPress:
                        self._pending_backward += 1
                    elif key in {Qt.Key_Tab, Qt.Key_Backtab}:
                        if evt_type == QEvent.KeyPress:
                            if not mods & Qt.MetaModifier:
                                self._pending_backward = 0
                elif mods & Qt.MetaModifier:
                    self._pending_backward = max(0, self._pending_backward - 1)
                    if self._cycleTab(forward=True):
                        return True
                elif self._pending_backward > 0:
                    self._pending_backward -= 1
                    if self._cycleTab(forward=False):
                        return True
        else:
            modifier_only = {
             Qt.Key_Shift, Qt.Key_Alt, Qt.Key_AltGr,
             Qt.Key_Control, Qt.Key_Meta}
            if evt_type == QEvent.KeyPress:
                if key not in modifier_only:
                    self._pending_backward = 0
            if evt_type not in {QEvent.ShortcutOverride, QEvent.KeyPress}:
                return False
            for sequence in self.duplicate_sequences:
                if matchesShortcutEvent(event, sequence, wrapped=False):
                    return self._forwardAsWrapped(watched, event)

            return False


class ThemedCornerWidget(QWidget):
    __doc__ = 'Wrapper for the tab corner button with an explicit theme-background fill.\n\n    On macOS, Fusion style paints the corner-widget area using\n    QPalette::Window via CE_TabBarBase / PE_FrameTabWidget, completely\n    bypassing the Qt stylesheet.  This widget overrides paintEvent so\n    that its own background always matches the application theme colour,\n    regardless of what the platform style draws behind it.\n    '

    def paintEvent(self, event):
        from qtpy.QtGui import QPainter, QPalette as _Pal
        p = QPainter(self)
        p.fillRect(self.rect(), QApplication.palette().color(_Pal.Window))
        p.end()


class CustomTab(QTabWidget):
    moveMe = Signal(int)
    separateMe = Signal(int)
    closeOthers = Signal(int)
    clicked = Signal()

    def __init__(self, owner):
        super().__init__(parent=owner)
        self.owner = owner
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self.closeTab)
        self.currentChanged.connect(self._refreshCloseButtonIcons)
        self.setElideMode(Qt.ElideNone)
        self.count_label = None
        bar = self.tabBar()
        bar.setExpanding(False)
        bar.setUsesScrollButtons(True)
        bar.setContextMenuPolicy(Qt.CustomContextMenu)
        bar.customContextMenuRequested.connect(self.showContextMenu)
        self.tabBarClicked.connect(self.clicked)
        self.tab_menu_button = customToolButton(text='▼', tooltip=(self.tr('Open Tabs') + '            Alt   T'), slot=(self.show_tab_menu))
        self.tab_menu = QtMenu(self)
        self.tab_menu.setStyleSheet('QMenu{menu-scrollable: 1;}')
        from qtpy.QtWidgets import QHBoxLayout
        self._corner_container = ThemedCornerWidget(self)
        _cl = QHBoxLayout(self._corner_container)
        _cl.setContentsMargins(0, 0, 0, 0)
        _cl.setSpacing(0)
        _cl.addWidget(self.tab_menu_button)
        self.setCornerWidget(self._corner_container, Qt.Corner.TopRightCorner)

    def tabInserted(self, index):
        super().tabInserted(index)
        installTabCloseButton(self, index)
        self._refreshCloseButtonIcons()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._refreshCloseButtonIcons()

    def _refreshCloseButtonIcons(self, *_):
        bar = self.tabBar()
        current_index = self.currentIndex()
        for index in range(self.count()):
            button = bar.tabButton(index, QTabBar.RightSide)
            if isinstance(button, TabCloseButton):
                button.setBaseState('normal' if index == current_index else 'unfocused')

    def countTabs(self):
        if self.count_label:
            self.count_label.setText(self.tr('Open Tabs') + f": {arabize(self.count())}")

    def show_tab_menu(self):
        self.tab_menu.clear()
        self.count_label = QLabel()
        self.count_label.setAlignment(Qt.AlignCenter)
        self.countTabs()
        widget = QWidgetAction(self.tab_menu)
        widget.setDefaultWidget(self.count_label)
        self.tab_menu.addAction(widget)
        self.tab_menu.addSeparator()
        first_action = None
        count = self.count()
        for i in range(count):
            tab_text = self.widget(i).full_title
            action = self.tab_menu.addAction(tab_text)
            action.setIcon(self.tabIcon(i))
            action.triggered.connect(partial(self.setCurrentWidget, self.widget(i)))
            if not first_action:
                first_action = action

        self.tab_menu.popup(self.tab_menu_button.mapToGlobal(self.tab_menu_button.pos()))
        self.tab_menu.setActiveAction(first_action)

    def reText(self):
        count = self.count()
        for i in range(count):
            self.setTabText(i, five(self.widget(i).full_title))

    def showContextMenu(self, point):
        if point is None:
            return
        bar = self.tabBar()
        tab = bar.tabAt(point)
        items = (
         (
          0, self.tr('Close'), 'Esc', self.closeThis),
         (
          1, self.tr('Close Other Tabs'), None, self.closeOthersSlot),
         (
          2, self.tr('Close All Tabs'), 'Shift+Esc', self.closeAll),
         (
          3, self.tr('Move to the other compartment'), None, self.moveMeSlot),
         (
          4, self.tr('Separate tab'), None, self.separateMeSlot),
         (
          5, self.tr('Change number of words in tab head'), None, self.tabHeadOption))
        menu = QMenu(bar)
        actions = []
        for index, label, sequence, slot in items:
            action = QAction(label)
            action.triggered.connect(partial(slot, tab))
            if index == 1:
                action.setEnabled(Across.main_window.dual.tabsCount() != 1)
            if sequence:
                action.setShortcut(QKeySequence(sequence))
            actions.append(action)
            menu.addAction(actions[-1])
            if index == 2 or index == 4:
                menu.addSeparator()

        menu.exec_(bar.mapToGlobal(point))

    def tabHeadOption(self, _):
        Across.main_window.showOptions('setting', 'tab_title_words')

    def moveMeSlot(self, tab):
        self.moveMe.emit(tab)

    def separateMeSlot(self, tab):
        self.separateMe.emit(tab)

    def closeOthersSlot(self, tab):
        self.closeOthers.emit(tab)

    def closeCurrent(self):
        if self.count() != 0:
            self.closeTab(self.currentIndex())

    def closeThis(self, tab):
        self.closeTab(tab)

    def closeAll(self, _):
        self.owner.closeAll()

    def closeTab(self, current_index):
        current_widget = self.widget(current_index)
        current_widget.closeTab()
        current_widget.close()
        self.removeTab(current_index)

    def save(self, context_id):
        if self.count() != 0:
            return (
             self.currentIndex(), [self.widget(i).save(context_id) for i in range(self.count())])


def main():
    global lock
    value = getPaths()
    translator = QTranslator()
    translator.load(':/lang/ar')
    app_title = 'المكتبة الشاملة'
    QCoreApplication.setApplicationName(app_title)
    if hasattr(QGuiApplication, 'setApplicationDisplayName'):
        QGuiApplication.setApplicationDisplayName(app_title)
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontShowShortcutsInContextMenus, False)
    style_hints = app.styleHints()
    if hasattr(style_hints, 'setShowShortcutsInContextMenus'):
        style_hints.setShowShortcutsInContextMenus(True)
    if Across.os == 'mac':
        app.ctrl_shortcut_filter = MacCtrlShortcutFilter(app)
        app.installEventFilter(app.ctrl_shortcut_filter)
    applyApplicationTheme(app)
    app.installTranslator(translator)
    app.setOrganizationName('Shamela Software')
    app.setOrganizationDomain('shamela.ws')
    app.setApplicationName(app_title)
    if hasattr(app, 'setApplicationDisplayName'):
        app.setApplicationDisplayName(app_title)
    app.setWindowIcon(QIcon(':/icons/shamela.png'))
    if value == 3:
        customMessage((QCoreApplication.translate('MainWindow', 'Program Folders')), (QCoreApplication.translate('MainWindow', 'This is the old shamela folder, and can not be upgraded to this version. Download the new version')),
          nomain=True)
        sys.exit()
    if value == 4:
        customMessage((QCoreApplication.translate('MainWindow', 'Databases')), (QCoreApplication.translate('MainWindow', 'Can not start main databases')),
          nomain=True)
        sys.exit()
    if value == 1:
        customMessage((QCoreApplication.translate('MainWindow', 'Program Folders')), (QCoreApplication.translate('MainWindow', 'Can not prepare the Application Folder')),
          nomain=True)
        sys.exit()
    if not Across.writable:
        customMessage((QCoreApplication.translate('MainWindow', 'Read Only Folder')), (QCoreApplication.translate('MainWindow', 'The Folder of the Application should be writable')),
          nomain=True)
        sys.exit()
    lock_path = os.path.join(Across.home_directory, 'database', 'update', 'updates.lock')
    lock = updateFileLock(lock_path)
    try:
        lock.acquire(timeout=1)
    except:
        Across.no_update = True

    app.setLayoutDirection(Qt.RightToLeft)
    Across.standard_font = [Across.ui_font_family, 10, False, False]
    for font in Across.fonts:
        QFontDatabase.addApplicationFont(f":/fonts/{font}")

    form = MainWindow(app)
    form.show()
    QTimer.singleShot(0, mark_launcher_ready)
    QTimer.singleShot(0, lambda: finish_startup_activation(app, form))
    if Across.os == 'mac':
        QTimer.singleShot(250, lambda: finish_startup_activation(app, form))
    sys.exit(app.exec_())