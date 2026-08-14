# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: pdfviewer.py
import os
from pathlib import Path
import fitz
from qtpy.QtCore import Qt, QUrl
from qtpy.QtGui import QImage, QPixmap, QDesktopServices
from qtpy.QtWidgets import QLabel, QFrame, QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from customs import customToolButton, customLayout, LineEdit, shortcut, blanchLabel, Scale, checkAllPdf, matchesShortcutEvent, matchesShortcutModifiers
from settings import Settings
from textmanager import arabize, safeInt
from across import Across

class PdfGui(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('pdfPanel')
        shortcut(self, 'PgUp', (self.previous), context=(Qt.WidgetWithChildrenShortcut))
        shortcut(self, 'PgDown', (self.next), context=(Qt.WidgetWithChildrenShortcut))
        self.viewer = PdfViewer(self)
        self.firstToolButton = customToolButton(':/icons/p-first.png', (self.tr('First Page')), iconsize=20)
        self.previoustToolButton = customToolButton(':/icons/p-previous.png', (self.tr('Previous Page') + '  PgUp'), iconsize=20)
        self.nextToolButton = customToolButton(':/icons/p-next.png', (self.tr('Next Page') + '  PgDn'), iconsize=20)
        self.lastToolButton = customToolButton(':/icons/p-last.png', (self.tr('Last Page')), iconsize=20)
        self.firstToolButton.clicked.connect(lambda: self.displayPage(1))
        self.previoustToolButton.clicked.connect(lambda: self.displayPage(self.viewer.pageNumber() - 1))
        self.nextToolButton.clicked.connect(lambda: self.displayPage(self.viewer.pageNumber() + 1))
        self.lastToolButton.clicked.connect(lambda: self.displayPage(self.viewer.page_count))
        self.totalPagesLabel = QLabel()
        self.totalPagesLabel.setMaximumWidth(35)
        self.totalPagesLabel.setAlignment(Qt.AlignCenter)
        self.gotoPageEdit = LineEdit(digit_policy='display', width=35, slot=(self.goNumber), no_clear=True)
        self.gotoPageEdit.setAlignment(Qt.AlignCenter)
        self.fitWidthButton = customToolButton(':/icons/fit-width.png', (self.tr('Fit Width')), iconsize=20)
        self.fitHeightButton = customToolButton(':/icons/fit-height.png', (self.tr('Fit Height')), iconsize=20)
        self.fitWidthButton.clicked.connect(self.viewer.fitWidth)
        self.fitHeightButton.clicked.connect(self.viewer.fitHeight)
        self.fitWidthButton.setEnabled(False)
        self.zoomOutButton = customToolButton(':/icons/p-minus.png', (self.tr('Zoom Out')), iconsize=20)
        self.zoomInButton = customToolButton(':/icons/p-plus.png', (self.tr('Zoom In')), iconsize=20)
        self.zoomOutButton.clicked.connect(self.viewer.zoomOut)
        self.zoomInButton.clicked.connect(self.viewer.zoomIn)
        openFileButton = customToolButton(':/icons/file.png', (self.tr('Open Pdf File')), iconsize=20)
        openFolderButton = customToolButton(':/icons/folder.png', (self.tr('Open Pdf Folder')), iconsize=20)
        openFileButton.clicked.connect(self.viewer.openFile)
        openFolderButton.clicked.connect(self.viewer.openFolder)
        rightrotBotton = customToolButton(':/icons/rot-rt.png', (self.tr('Rotate Right')), iconsize=20)
        leftrotBotton = customToolButton(':/icons/rot-lt.png', (self.tr('Rotate Left')), iconsize=20)
        rightrotBotton.clicked.connect(self.viewer.rotateRight)
        leftrotBotton.clicked.connect(self.viewer.rotateLeft)
        layout = customLayout(False, [
         openFileButton, openFolderButton, 7,
         rightrotBotton, leftrotBotton, 0,
         self.firstToolButton, self.previoustToolButton,
         self.gotoPageEdit, 7, self.totalPagesLabel,
         self.nextToolButton, self.lastToolButton, 0,
         self.zoomInButton, self.zoomOutButton, 7,
         self.fitHeightButton, self.fitWidthButton],
          margins=0)
        self.pdf = QWidget()
        self.pdf.setLayout(customLayout(True, [self.viewer, layout]))
        self.blanch_card, self.blanch_label = blanchLabel(self.tr('No page in pdf corresponding that page'))
        self.setLayout(customLayout(True, [self.pdf, self.blanch_card], margins=0))

    def blanch(self, value):
        self.blanch_card.setVisible(value)
        self.pdf.setVisible(not value)

    def refreshDigits(self):
        page = self.viewer.pageNumber()
        if page:
            self.gotoPageEdit.setText(str(page))
        else:
            count = self.viewer.page_count
            if count:
                self.totalPagesLabel.setText(arabize((f"{count}")))
            else:
                self.totalPagesLabel.clear()

    def next(self):
        if self.pdf.isVisible():
            if self.nextToolButton.isEnabled():
                self.displayPage(self.viewer.pageNumber() + 1)

    def previous(self):
        if self.pdf.isVisible():
            if self.nextToolButton.isEnabled():
                self.displayPage(self.viewer.pageNumber() - 1)

    def displayPage(self, page_no=1, filename=None):
        self.viewer.displayPage(page_no, filename)
        page = self.viewer.pageNumber()
        if not page:
            self.blanch(True)
            return
        self.blanch(False)
        strpage = str(page)
        if strpage != self.gotoPageEdit.text():
            self.gotoPageEdit.setText(strpage)
        count = self.viewer.page_count
        strcount = f"{count}"
        if strcount != self.totalPagesLabel.text():
            self.totalPagesLabel.setText(arabize(strcount))
        enabled = page != 1
        self.firstToolButton.setEnabled(enabled)
        self.previoustToolButton.setEnabled(enabled)
        enabled = page != count
        self.lastToolButton.setEnabled(enabled)
        self.nextToolButton.setEnabled(enabled)

    def goNumber(self):
        page = safeInt(self.gotoPageEdit.text())
        count = self.viewer.page_count
        if 0 < page < count + 1:
            self.displayPage(page)
            return
        self.gotoPageEdit.setText(str(self.viewer.pageNumber()))


class PdfViewer(QGraphicsView):

    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.filepath = None
        self.page_count = None
        self.page_number = None
        self.current_scale = None
        self.matrix = None
        self.doc = None
        self.current_rotation = 0
        self.current_fit = Settings.getValue('pdf_fit')
        if self.current_fit not in frozenset({1, 2}):
            self.current_fit = 1
        self.zoom_out_enabled = True
        self.zoom_in_enabled = True
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setAlignment(Qt.AlignCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._pixmapItem = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmapItem)

    def rotateLeft(self):
        if self.current_rotation == -270:
            self.current_rotation = 0
        else:
            self.current_rotation -= 90
        self.displayPixmap()

    def rotateRight(self):
        if self.current_rotation == 270:
            self.current_rotation = 0
        else:
            self.current_rotation += 90
        self.displayPixmap()

    def rotationMatrix(self):
        if self.current_rotation == 0:
            return fitz.Matrix(0)
        return fitz.Matrix(0).prerotate(self.current_rotation)

    def openAndTest(self):
        try:
            doc = fitz.open(self.filepath)
            if not self.page_count:
                self.page_count = doc.page_count
        except:
            try:
                os.unlink(self.filepath)
            except:
                pass

            checkAllPdf(Across.main_window.progress.progress_signal)
            return
            return doc

    def displayPixmap(self, fit=None, reposition=False):
        if fit:
            self.current_fit = fit
        try:
            doc = self.openAndTest()
            if not doc:
                return
            if self.page_number > self.page_count:
                return
            page = doc[self.page_number - 1]
            self.adjustMatrix(page)
            pix = page.get_pixmap(matrix=(self.matrix), alpha=False)
            doc.close()
            samples = bytes(pix.samples)
            w, h, stride = pix.width, pix.height, pix.stride
            pix = None
            fitz.TOOLS.store_shrink(100)
            img = QPixmap.fromImage(QImage(samples, w, h, stride, QImage.Format_RGB888))
            scale = Scale.scale()
            img.setDevicePixelRatio(scale)
            self._pixmapItem.setPixmap(img)
            self._pixmapItem.setOffset(0, 0)
            self.setSceneRect(0, 0, img.width() / scale, img.height() / scale)
        except:
            return
            if reposition:
                sbar = self.verticalScrollBar()
                sbar.setValue(sbar.minimum())
            elif self.current_fit in frozenset({1, 2}):
                Settings.setValue('pdf_fit', self.current_fit, True)
                self.ui.fitHeightButton.setEnabled(self.current_fit == 1)
                self.ui.fitWidthButton.setEnabled(self.current_fit == 2)
                self.ui.zoomInButton.setEnabled(True)
                self.ui.zoomOutButton.setEnabled(True)
            else:
                self.zoom_in_enabled = self.current_scale < 8
                self.zoom_out_enabled = self.current_scale > 0.18
                self.ui.zoomInButton.setEnabled(self.zoom_in_enabled)
                self.ui.zoomOutButton.setEnabled(self.zoom_out_enabled)
                self.ui.fitHeightButton.setEnabled(True)
                self.ui.fitWidthButton.setEnabled(True)
            return True

    def pageNumber(self):
        if self.page_count:
            return self.page_number

    def openFile(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.filepath)))

    def openFolder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(str(self.filepath))))

    def displayPage(self, page_no=1, filename=None):
        if page_no < 1:
            return
            if filename:
                f_path = Path(filename)
            else:
                f_path = self.filepath
            if not f_path:
                return
            if f_path != self.filepath:
                self.page_count = None
                self.filepath = f_path
        else:
            if self.page_number == page_no:
                if self.page_count:
                    return
            self.page_number = page_no
            self.page_number = self.displayPixmap(reposition=True) or None

    def adjustMatrix(self, page):
        if self.current_fit == 1:
            if self.current_rotation in (90, 270, -90, -270):
                w = page.bound().y1
            else:
                w = page.bound().x1
            self.current_scale = self.viewport().rect().width() / w * Scale.scale()
        else:
            if self.current_fit == 2:
                if self.current_rotation in (90, 270, -90, -270):
                    h = page.bound().x1
                else:
                    h = page.bound().y1
                self.current_scale = self.viewport().rect().height() / h * Scale.scale()
        self.matrix = self.rotationMatrix().prescale(self.current_scale, self.current_scale)

    def fitWidth(self):
        self.fit(1)

    def fitHeight(self):
        self.fit(2)

    def fit(self, fit_type):
        self.displayPixmap(fit_type)

    def zoomOut(self):
        self.zoom(0.8)

    def zoomIn(self):
        self.zoom(1.25)

    def zoom(self, factor):
        if factor > 1:
            if not self.zoom_in_enabled:
                return
        if factor < 1:
            if not self.zoom_out_enabled:
                return
        self.current_scale *= factor
        self.matrix = self.rotationMatrix().prescale(self.current_scale, self.current_scale)
        self.displayPixmap(3)

    def resizeEvent(self, event):
        if self.current_fit in (1, 2):
            if self.page_number is not None:
                self.displayPixmap()
        super().resizeEvent(event)

    def keyPressEvent(self, event):
        if matchesShortcutEvent(event, 'Ctrl+-') or matchesShortcutEvent(event, 'Ctrl+_'):
            self.zoomOut()
        else:
            if matchesShortcutEvent(event, 'Ctrl++') or matchesShortcutEvent(event, 'Ctrl+='):
                self.zoomIn()
            else:
                super().keyPressEvent(event)

    def wheelEvent(self, event):
        if matchesShortcutModifiers(event.modifiers(), 'Ctrl+0'):
            self.handleWheelNotches(event.angleDelta().y() / 240.0)
            event.accept()
        else:
            super().wheelEvent(event)

    def handleWheelNotches(self, notches):
        self.zoom(1.25 ** notches)