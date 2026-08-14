# decompyle3 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: displaybook.py
import json, os, regex as re
from qtpy.QtCore import QByteArray, QEvent, QMimeData, Qt, Signal, QTimer
from qtpy.QtGui import QFontMetrics, QKeyEvent, QPainter, QPixmap, QTextBlockFormat, QTextCursor
from qtpy.QtWidgets import QButtonGroup, QToolBar, QApplication, QComboBox, QSlider, QLabel, QWidget, QStackedWidget, QSplitter, QTextEdit
from across import Across
from scaling import scaled_font_size
from basebookview import Author
from cache import FixSizeOrderedDict, BookCache, CssCache
from customs import BusySpinner, CustomDialog, shortcut, Scale, customLayout, customToolButton, LineEdit, QtFont, flexibleBrowser, customMessage, Splitter, shortcutLabel, directShortcutLabel, _buildSingleFontRichPayload, setClipboardMimeData, vLine, htmlToRtfBytes
from dbmanager import BookDb, UserDb, CoreDb, Services
from dirs import pdfPath, isWritable
from theme import Icon
from settings import Settings
from sidebar import SideBar
from textmanager import treatSearch, safeStr, safeInt, arabize, latinize, formatPage, superscript, conditioned, safeNorm, clean_invisible, toAsciiDigits, displayDigits, isRich, reverseRows, lineHeight
from engine import QueryType, wholeSnippet, getTitle, buildFilter, Book
separator = f"\n<span class='h_separator'>{Across.separator}</span>\n"

class LatinTextEdit(QTextEdit):

    def __init__(self):
        super().__init__()

    def createMimeDataFromSelection(self):
        text = self.textCursor().selection().toPlainText().replace('\u2029', '\n').replace('\u2028', '\n')
        text = clean_invisible(toAsciiDigits(text))
        html_selection = self.textCursor().selection().toHtml()
        force_rich = isRich(html_selection)
        data = QMimeData()
        data.setText(text)
        if Settings.getValue('copy_formatted') or force_rich:
            if force_rich:
                fixed = reverseRows(html_selection)
                html = f"<html><head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'/></head><body>{fixed}</body></html>"
                rtf = htmlToRtfBytes(html) if Across.os == 'mac' else None
            else:
                html, rtf = _buildSingleFontRichPayload(text, Settings.getValue('font_comments'))
            data.setHtml(html)
            if rtf:
                data.setData('text/rtf', QByteArray(rtf))
                data.setData('application/rtf', QByteArray(rtf))
        return data

    def copy(self):
        if self.textCursor().selection().isEmpty():
            return
        setClipboardMimeData(self.createMimeDataFromSelection())


class TextEdit(LatinTextEdit):

    def __init__(self):
        super().__init__()
        doc = self.document()
        option = doc.defaultTextOption()
        option.setTextDirection(Qt.RightToLeft)
        doc.setDefaultTextOption(option)
        self.setDocument(doc)

    def keyPressEvent(self, event):
        redirection = False
        text = event.text()
        if text:
            if latinize(text).isdigit():
                e = QKeyEvent((QEvent.KeyPress), 0, (Qt.NoModifier), text=(displayDigits(text)))
                super().keyPressEvent(e)
                redirection = True
        if not redirection:
            super().keyPressEvent(event)


class ElidedLabel(QLabel):

    def __init__(self):
        super().__init__()

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self.text(), Qt.ElideMiddle, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)


PDF = 0
TAKREEJ = 3
RIJAL = 4
TOROQ = 5

class Displayer:

    def __init__(self, owner, container, display_type):
        self.first_id = self.second_id = self.search_info = self.service = self.shorts = self.page_text = None
        self.display_type = display_type
        self.activated = None if self.display_type == 't' else True
        self.container = container
        self.owner = owner

    def deactivate(self):
        self.activated = None

    def display(self, first_id, second_id, page_text, search_info, service=None, shorts=None):
        if not self.activated:
            self.activated = True
        if [
         self.first_id, self.second_id, self.search_info, self.service] != [first_id, second_id, search_info, service]:
            if self.first_id != first_id:
                self.shorts = shorts
            self.first_id, self.second_id, self.page_text, self.search_info, self.service = (
             first_id, second_id, page_text, search_info, service)
            return self._display()
        return (None, None)

    def _display(self, keep_position=None):
        text = None
        if self.display_type == 'c':
            text = self.page_text.comment()
            if self.search_info:
                fragment = wholeSnippet(text, self.search_info)
                if fragment:
                    text = fragment
                else:
                    keep_position = True
        else:
            if self.display_type == 'p':
                keep_position_text = False
                text = self.page_text.body()
                if self.search_info:
                    fragment = wholeSnippet(text, self.search_info)
                    if fragment:
                        text = fragment
                    else:
                        keep_position_text = True
                foot = self.page_text.foot()
                if self.search_info:
                    fragment = wholeSnippet(foot, self.search_info)
                    if fragment:
                        foot = fragment
                    else:
                        if keep_position_text:
                            keep_position = True
                if foot:
                    if text:
                        text = f"{superscript(text)}<div class='footnote'><div>{separator}{foot}</div></div>"
                    else:
                        if Across.splitter in foot:
                            text = foot.split(Across.splitter, 1)
                            text = f"{superscript(text[0])}<div class='footnote'>{separator}{text[1]}</div>"
                        else:
                            text = superscript(foot)
                else:
                    text = superscript(text)
            else:
                if self.display_type == 't':
                    text = getTitle(self.first_id, self.second_id)
                    if self.search_info:
                        fragment = wholeSnippet(text, self.search_info)
                        if fragment:
                            text = fragment
                        else:
                            keep_position = None
        cash = f"{self.display_type}_{self.owner.attribute_dict[self.first_id]['printed']}" if self.display_type == 'p' else self.display_type
        text, page_info = formatPage(text, (CssCache.getCache(cash)), service=(self.service), shorts=(self.shorts))
        if self.display_type == 'p':
            self.owner.page_info = self.owner.men = self.owner.takreej_id = None
            if text:
                self.owner.page_info = page_info
                self.owner.showButtons()
        if not keep_position:
            if self.search_info:
                self.container.setUpdatesEnabled(False)
        self.container.setHtml(text, self.tashkeelStatue(), keep_position)
        if not keep_position:
            if self.search_info:
                QApplication.processEvents()
                self.container.scrollToAnchor('go')
                self.container.setUpdatesEnabled(True)
        return (
         text, page_info)

    def tashkeelStatue(self):
        value = False
        if self.search_info:
            if self.search_info['diacritics']:
                value = True
        value = value or self.owner.tashkeel
        self.owner.diacriticToolButton.blockSignals(True)
        self.owner.diacriticToolButton.setChecked(value)
        self.owner.diacriticToolButton.blockSignals(False)
        return value

    def tashkeel(self):
        self._display(keep_position=True)

    def talween(self, search_info=None):
        if self.activated:
            if search_info != self.search_info:
                self.search_info = search_info
            self._display(keep_position=(search_info is None))


class DisplayBook(QWidget):
    closed = Signal(QWidget)

    def __init__(self, book_id=None, page_id=None, full_display=None, search_res=None, afterfunction=None, search_info=None, off_features=None):
        super().__init__()
        self.full_title = None
        self.shown = None
        self.manual_pdf = None
        off_features = off_features or set()
        unshorts = 'unshorts' in off_features
        hide_bar = 'hide_bar' in off_features
        self.secondary = 'secondary' in off_features
        if 'minimal' in off_features:
            self.manual_pdf = True
            self.secondary = True
            hide_bar = True
            unshorts = True
        self.single = None
        self.services = self.page_info = self.men = self.takreej_id = None
        self.idSlider = QSlider()
        self.idSlider.setOrientation(Qt.Horizontal)
        self.idSlider.setMinimum(1)
        self.idSlider.valueChanged.connect(lambda page_id: self.goId(page_id)
)
        self.partComboBox = QComboBox()
        self.partComboBox.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.partComboBox.setMinimumWidth(15)
        self.partComboBox.currentIndexChanged.connect(self.goPart)
        self.pageLineEdit = LineEdit(digit_policy='display', width=40, slot=(self.goPage), no_clear=True)
        self.numLabel = QLabel(self.tr('Number'))
        self.numberLineEdit = LineEdit(digit_policy='display', width=50, slot=(self.goNumber), no_clear=True)
        self.commentToolButton = customToolButton(':/icons/hint.png', (self.tr('Comment')), checkable=True, iconsize=20)
        self.backToolButton = customToolButton(':/icons/back.png', tooltip=(self.tr('Back    Backspace')), iconsize=20)
        self.backToolButton.clicked.connect(lambda: self.goHistory(-1)
)
        self.forwardToolButton = customToolButton(':/icons/forward.png', tooltip=(self.tr('Forward    Shift-Backspace')), iconsize=20)
        self.forwardToolButton.clicked.connect(lambda: self.goHistory(1)
)
        self.firstToolButton = customToolButton(':/icons/first.png', self.tr('First Page'))
        self.firstToolButton.clicked.connect(lambda: self.goId(1)
)
        self.previoustToolButton = customToolButton(':/icons/previous.png', self.tr('Previous Page') + ('' if unshorts else '  F6'))
        self.previoustToolButton.clicked.connect(self.goPrevious)
        self.nextToolButton = customToolButton(':/icons/next.png', self.tr('Next Page') + ('' if unshorts else '  F5'))
        self.nextToolButton.clicked.connect(self.goNext)
        self.lastToolButton = customToolButton(':/icons/last.png', self.tr('Last Page'))
        self.lastToolButton.clicked.connect(lambda: self.goId(self.last_id)
)
        navigateLayout = customLayout(False, [self.firstToolButton, self.previoustToolButton, self.nextToolButton,
         self.lastToolButton],
          margins=0, spacing=8)
        new_display_label = self.tr('Display the Book in New Tab')
        if not unshorts:
            new_display_label = directShortcutLabel(new_display_label, 'Ctrl+D', separator='   ')
        self.newDisplayButton = customToolButton(':/icons/new.png', new_display_label, slot=(self.newDisplay))
        self.betakaButton = customToolButton(':/icons/betaka.png', tooltip=(self.tr('Display Book Betaka')), slot=(self.showBetaka))
        self.findonpageLineEdit = LineEdit(digit_policy='ascii', slot=(self.searchText), width=170)
        self.findonpageLineEdit.setPlaceholderText(self.tr('Find on Page'))
        self.findonpageLineEdit.textChanged.connect(self.searchText)
        self.textBrowser = flexibleBrowser()
        self.textBrowser.link.connect(self.goLink)
        copyToolButton = customToolButton(':/icons/copy.png', (directShortcutLabel(self.tr('Copy with attributes'), 'Ctrl+Shift+C')), slot=(self.textBrowser.copyAttribute))
        self.diacriticToolButton = customToolButton(':/icons/diacritic.png', self.tr('Diacritics'))
        self.diacriticToolButton.setCheckable(True)
        self.tashkeel = True
        self.diacriticToolButton.toggled.connect(self.userDiacritic)
        self.page_label = QLabel()
        self.book_name_label = ElidedLabel()
        self.book_name_label.setAlignment(Qt.AlignCenter)
        _color = f"color: {'#6FA8DC' if Across.active_theme == 'dark' else '#800000'}; "
        self.book_name_label.setStyleSheet(f'QLabel {{{_color}font: bold {scaled_font_size(14)}pt "Traditional Naskh";}}')
        self.book_name_label.setFixedHeight(32)
        self.book_name_label.setWordWrap(True)
        upper_ribbon = customLayout(False, [self.newDisplayButton, 30,
         navigateLayout,
         self.book_name_label,
         copyToolButton, 10,
         self.diacriticToolButton, 10,
         self.betakaButton, 10,
         self.findonpageLineEdit],
          margins=0)
        lower_ribbon = customLayout(False, [self.page_label,
         self.partComboBox, self.pageLineEdit,
         self.numLabel, self.numberLineEdit,
         self.idSlider,
         self.backToolButton, self.forwardToolButton, 3,
         self.commentToolButton],
          margins=[0, 0, 1, 0], spacing=6)
        self.titlesBox = flexibleBrowser()
        self.titlesBox.hide()
        self.commentWidget = Comment(self.commentToolButton)
        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)
        splitter.addWidget(self.titlesBox)
        splitter.addWidget(self.textBrowser)
        splitter.addWidget(self.commentWidget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 80)
        splitter.setStretchFactor(2, 25)
        splitter.setHandleWidth(int(splitter.handleWidth() / 2))
        main_layout = customLayout(True, [upper_ribbon, splitter, 1, lower_ribbon], margins=[1, 1, 3, 0])
        self.commentWidget.saveComment.connect(self.saveComment)
        self.commentWidget.setVisible(False)
        self.sideBar = SideBar(self)
        self.hContainer = Container()
        self.vContainer = Container()
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self._main_widget = main_widget
        self.hSplitter = Splitter(True, [main_widget, self.hContainer], [
         333564, 365332])
        self.hSplitter.setStyleSheet('QSplitter::handle { margin: 0; }')
        biview = Splitter(False, [self.hSplitter, self.vContainer], [
         679371, 787150])
        self.vSplitter = Splitter(False, [self.sideBar, biview], [
         411792, 1814272])
        self.rijal_switch = self.toroq_switch = self.takreej_switch = None
        self.pdf_switch = None if self.manual_pdf else Settings.getValue('pdf_on')
        self.groups = [
         set(), set()]
        containers = [self.vContainer, self.hContainer]
        value = Settings.getValue('pdf_orientation')
        self.pdfContainer = containers[value]
        self.groups[value].add(PDF)
        value = Settings.getValue('rijal_orientation')
        self.rijalContainer = containers[value]
        self.groups[value].add(RIJAL)
        value = Settings.getValue('toroq_orientation')
        self.toroqContainer = containers[value]
        self.groups[value].add(TOROQ)
        value = Settings.getValue('takreej_orientation')
        self.takreejContainer = containers[value]
        self.groups[value].add(TAKREEJ)
        sideToolButton = customToolButton(':/icons/tree.png', (self.tr('Side Bar')), iconsize=20)
        sideToolButton.setCheckable(True)
        self.pdfDownloadButton = customToolButton(':/icons/download.png', (self.tr('Download Pdf')), slot=(self.downloadPdf),
          iconsize=20)
        self.pdfDisplayButton = customToolButton(':/icons/pdf_r.png', (self.tr('Display Pdf') + ('' if unshorts else '  F11')),
          slot=(self.switchPdf),
          iconsize=20)
        self.pdfDisplayButton.setCheckable(True)
        self.rijalButton = customToolButton(':/icons/rijal.png', (self.tr('trajim')), slot=(self.switchTrajim), iconsize=20)
        if not self.secondary:
            self.rijalButton.setCheckable(True)
        self.toroqButton = customToolButton(':/icons/toroq.png', (self.tr('toroq')), slot=(self.switchToroq), iconsize=20)
        if not self.secondary:
            self.toroqButton.setCheckable(True)
        takreej_label = self.tr('takreej')
        if not unshorts:
            takreej_label = directShortcutLabel(takreej_label, 'Ctrl+J', separator='   ')
        self.takreejButton = customToolButton(':/icons/takreej.png', takreej_label, slot=(self.switchTakreej),
          iconsize=20)
        if not self.secondary:
            self.takreejButton.setCheckable(True)
        vbar = customLayout(True, [sideToolButton,
         self.pdfDisplayButton,
         self.pdfDownloadButton,
         self.takreejButton,
         self.rijalButton,
         self.toroqButton,
         0],
          spacing=3)
        self.setLayout(customLayout(False, [vbar, vLine(), self.vSplitter], margins=[2, 0, 2, 3]))
        self.page_displayer = Displayer(self, self.textBrowser, 'p')
        self.comment_displayer = Displayer(self, self.commentWidget, 'c')
        self.title_displayer = Displayer(self, self.titlesBox, 't')
        self.history = []
        self.history_index = self.book_id = self.page_id = self.last_id = self.has_parts = self.has_numbers = self.visible_side = self.pdf_dict = self.part = self.page = self.has_alias = self.betaka = None
        self.attribute_dict = FixSizeOrderedDict(max=10)
        if book_id:
            self.setBookId(book_id)
        side_bar = False if hide_bar else Settings.getValue('sidebar_in_results')
        self.sideBarVisible(side_bar)
        sideToolButton.setChecked(side_bar)
        self.record_history = not self.secondary
        sideToolButton.clicked.connect(lambda: self.sideBarVisible(sideToolButton.isChecked())
)
        self.commentToolButton.clicked.connect(lambda: self.commentWidget.toggle(self.commentToolButton.isChecked())
)
        if full_display:
            (self.display)(*full_display)
        else:
            if search_res:
                self.setBookId(search_res[0])
                self.resultClicked(search_res)
            else:
                if page_id:
                    if search_info:
                        self.showSearch(search_info)
                        if self.page_id != page_id:
                            self.goId(page_id)
                    else:
                        self.goId(page_id)
                        if afterfunction:
                            if afterfunction == 'takreej':
                                QTimer.singleShot(0, self.switchTakreej)
                            else:
                                if afterfunction == 'toroq':
                                    QTimer.singleShot(0, self.switchToroq)
        self.shown = True
        self.refreshSide()

    def focusBookResults(self):
        self.sideBar.focusResult()

    def save(self, context_id):
        save_dict = {'book':self.book_id, 
         'page':self.page_id}
        search_data = self.sideBar.searchInfo(context_id)
        if search_data:
            save_dict['search'] = search_data
        return ['BOOK', save_dict]

    def shortBack(self):
        if self.backToolButton.isEnabled():
            self.goHistory(-1)

    def shortForward(self):
        if self.forwardToolButton.isEnabled():
            self.goHistory(1)

    def go(self):
        if self.partComboBox.isVisible():
            self.partComboBox.setFocus()
        else:
            self.pageLineEdit.setFocus()

    def goText(self):
        self.textBrowser.setFocus()

    def goTree(self):
        if not self.visible_side:
            self.sideBarVisible(True)
        self.sideBar.showTitles()
        self.sideBar.titlesWidget.titlesTree.setFocus()

    def refreshSide(self):
        if self.visible_side:
            if self.shown:
                self.sideBar.viewChanged()

    def switchButtons(self, service_value, press):

        def checkButton(button, value):
            if not button:
                return
            button.blockSignals(True)
            button.setChecked(value)
            button.blockSignals(False)

        if service_value in self.groups[0]:
            group = 0
        else:
            if service_value in self.groups[1]:
                group = 1
            else:
                return
        buttons = {PDF: self.pdfDisplayButton, 
         RIJAL: self.rijalButton, 
         TOROQ: self.toroqButton, 
         TAKREEJ: self.takreejButton}
        for item in self.groups[group]:
            switch = item == service_value if press else False
            checkButton(buttons[item], switch)
            if press:
                if item == PDF:
                    self.pdf_switch = switch
                else:
                    if item == RIJAL:
                        self.rijal_switch = switch
                    else:
                        if item == TOROQ:
                            self.toroq_switch = switch
                if item == TAKREEJ:
                    self.takreej_switch = switch

    def showBetaka(self):
        if self.book_id:
            self.betaka = Info(parent=self, book_id=(self.book_id), separate=True)
            self.betaka.show()

    def newDisplay(self):
        Across.main_window.showBook((self.book_id), full_display=(self.last_display))

    def showSearch(self, search_info=None):
        self.sideBar.showSearch(search_info=search_info)
        if not self.visible_side:
            self.sideBarVisible(True)

    def shortedNext(self):
        self.goNext()
        self.textBrowser.readPage()

    def shortedPrevious(self):
        self.goPrevious()
        self.textBrowser.readPage()

    def goNext(self):
        if self.page_id != self.last_id:
            self.goId(self.page_id + 1)

    def goPrevious(self):
        if self.page_id != 1:
            self.goId(self.page_id - 1)

    def sideBarVisible(self, visible):
        self.sideBar.setVisible(visible)
        self.visible_side = visible
        self.refreshSide()

    def setBookId(self, book_id):
        if book_id != self.book_id:
            self.book_id = book_id
            self.page_id = None
            self.history = []
            self.history_index = -1
            info = BookDb(self.book_id)
            self.last_id = info.lastId()
            self.parts_list = info.partsList()
            self.has_numbers = info.hasNumbers()
            self.has_alias = info.hasAlias()
            self.meta_data, pdf_list, book_name, printed = info.getMeta()
            self.shorts = None
            if self.meta_data:
                if 'shorts' in self.meta_data:
                    self.shorts = Shorts(self.meta_data['shorts'])
            self.book_name_label.setText(book_name)
            self.book_name_label.setToolTip(book_name)
            self.refreshSide()
            self.last_display = None
            betaka = conditioned(CoreDb().bookBetaka((self.book_id), True, truncated=True))
            self.betakaButton.setToolTip(betaka)
            self.pdf_switch = None if self.manual_pdf else Settings.getValue('pdf_on')
            self.pdf_dict = {}
            if pdf_list:
                for pdf_dict in pdf_list:
                    self.pdf_dict[pdf_dict['part']] = {'file':pdf_dict['file'], 
                     'difference':pdf_dict['difference']}

            attribute_dict = {}
            attribute_dict['prefix'] = self.meta_data['prefix'] if 'prefix' in self.meta_data else book_name
            attribute_dict['suffix'] = self.meta_data['suffix'] if 'suffix' in self.meta_data else ''
            attribute_dict['printed'] = printed
            self.attribute_dict[self.book_id] = attribute_dict
            self.idSlider.blockSignals(True)
            self.idSlider.setMaximum(self.last_id)
            self.idSlider.blockSignals(False)
            if self.has_numbers:
                self.numLabel.show()
                self.numberLineEdit.show()
            else:
                self.numLabel.hide()
                self.numberLineEdit.hide()
            default_hidden_diacritic = 'hide_diacritic' in self.meta_data
            self.diacriticToolButton.setToolTip(self.tr('This Book is undiacritized in printed version') if default_hidden_diacritic else self.tr('Diacritics'))
            diacritic = UserDb().isDiacritized(book_id)
            if diacritic is None:
                diacritic = not default_hidden_diacritic
            if diacritic:
                self.diacriticToolButton.setChecked(True)
                self.diacritic(True)
            else:
                self.diacriticToolButton.setChecked(False)
                self.diacritic(False)
            if self.parts_list:
                self.partComboBox.blockSignals(True)
                self.partComboBox.clear()
                self.partComboBox.addItems(self.parts_list)
                self.partComboBox.show()
                self.partComboBox.blockSignals(False)
                self.page_label.setText(self.tr('Part/ Page'))
            else:
                self.partComboBox.hide()
                self.page_label.setText(self.tr('Page'))
            self.title_displayer.deactivate()

    @staticmethod
    def getAttribute(book_id):
        meta_data, pdf_list, book_name, printed = BookDb(book_id).getMeta()
        attribute_dict = {}
        attribute_dict['prefix'] = meta_data['prefix'] if 'prefix' in meta_data else book_name
        attribute_dict['suffix'] = meta_data['suffix'] if 'suffix' in meta_data else ''
        attribute_dict['printed'] = printed
        return attribute_dict

    def setPageId(self, page_id):
        if page_id != self.page_id:
            self.goId(page_id)

    def navButtonState(self):
        enabled = self.page_id != 1
        self.firstToolButton.setEnabled(enabled)
        self.previoustToolButton.setEnabled(enabled)
        enabled = self.page_id != self.last_id
        self.lastToolButton.setEnabled(enabled)
        self.nextToolButton.setEnabled(enabled)

    def showButtons(self):
        pdf_state = 0
        if self.pdf_dict:
            this_part = self.part
            if this_part not in self.pdf_dict:
                this_part = '0'
            if this_part in self.pdf_dict:
                if os.path.isfile(self.pdf_dict[this_part]['file']):
                    pdf_state = 1
                else:
                    pdf_state = 3 if self.book_id in Across.downloading_pdfs else 2
        self.pdfDisplayButton.setVisible(pdf_state == 1)
        self.pdfDownloadButton.setVisible(pdf_state > 1)
        self.pdfDownloadButton.setEnabled(pdf_state != 3)
        if pdf_state == 3:
            BusySpinner.follow(self.pdfDownloadButton)
        else:
            BusySpinner.unfollow(self.pdfDownloadButton)
            self.pdfDownloadButton.setIcon(Icon.icon(':/icons/download.png'))
        toroq = 'esnad' in self.services
        men = toroq or 'text_men' in self.page_info
        self.toroqButton.setVisible(toroq)
        self.rijalButton.setVisible(men)
        self.takreej_id = Services.isPageInService(self.book_id, self.page_id, 'hadeeth')
        if self.takreej_id:
            self.takreejButton.setVisible(True)
        else:
            self.takreejButton.setVisible(False)
        for group in (self.groups[0], self.groups[1]):
            for item in group:
                if item == PDF:
                    if self.pdf_switch:
                        if pdf_state == 1:
                            self.showPdf()
                        else:
                            self.hidePdf()
                    else:
                        self.hidePdf()
                if item == RIJAL:
                    if self.rijal_switch:
                        if men:
                            self.showMan()
                    else:
                        pass
                    self.hideMan()
                else:
                    if item == TOROQ:
                        if self.toroq_switch:
                            if toroq:
                                self.showToroq()
                        else:
                            pass
                        self.hideToroq()
                    else:
                        if item == TAKREEJ:
                            if self.takreej_switch:
                                if self.takreej_id:
                                    self.showTakreej()
                                else:
                                    self.hideTakreej()

    def downloadPdf(self):
        pdf_path = pdfPath()
        default_folder = None
        try:
            from dirs import defaultPdfPath
            default_folder = defaultPdfPath()
        except Exception:
            pass

        if not os.path.isdir(pdf_path):
            if default_folder and pdf_path == default_folder:
                os.makedirs(pdf_path, exist_ok=True)
                if os.path.isdir(pdf_path):
                    pass
                else:
                    customMessage(self.tr('Pdf Folder'), self.tr('Pdf folder not found'))
                    return
            else:
                customMessage(self.tr('Pdf Folder'), self.tr('Pdf folder not found'))
                return
        if not isWritable(pdf_path):
            customMessage(self.tr('Pdf Folder'), self.tr('Pdf folder is read only'))
            return
        self.pdf_switch = True
        BusySpinner.follow(self.pdfDownloadButton)
        self.pdfDownloadButton.setEnabled(False)
        QApplication.processEvents()
        if not self.single:
            from updater import PdfDownloader
            self.single = PdfDownloader()
        self.single.singleBook(self.book_id, self.showButtons)

    def goLink(self, link):
        pieces = link[6:].split('-')
        link_type = pieces[0]
        if link_type == 'man':
            man = int(pieces[1])
            if man > 1:
                self.showMan(man)
            else:
                self.hideMan()

    def showPdf(self):
        if not self.shown:
            self.vSplitter.setStretchFactor(0, 16)
            self.vSplitter.setStretchFactor(1, 45)
            self.vSplitter.setStretchFactor(2, 80)
        this_part = self.part
        if this_part not in self.pdf_dict:
            this_part = '0'
        file = self.pdf_dict[this_part]['file']
        if self.page.isdigit():
            self.pdfContainer.displayPage(int(self.page) + self.pdf_dict[this_part]['difference'], file)
        else:
            self.pdfContainer.blanch(True)
        self.switchButtons(PDF, True)

    def getMen(self):
        if not self.men:
            self.men = []
            men_valve = set()
            if 'text_men' in self.page_info:
                uniList(self.page_info['text_men'], self.men, men_valve)
            if 'esnad' in self.services:
                asaneed = self.services['esnad']
                for esnad in asaneed:
                    all_men = esnad.split(' ')[2:]
                    uniList(all_men, self.men, men_valve)

    def showMan(self, man_id=None):
        from rijal import separateMan
        self.getMen()
        if not man_id:
            man_id = self.men[0]
        if self.secondary:
            separateMan(man_id, self.men)
        else:
            self.rijalContainer.displayMan(self.men, man_id)
            self.switchButtons(RIJAL, True)

    def showToroq(self):
        if self.secondary:
            Across.main_window.showBook((self.book_id), (self.page_id), afterfunction='toroq')
        else:
            self.toroqContainer.displayToroq(self.services['hadeeth'][0])
            self.switchButtons(TOROQ, True)

    def showTakreej(self):
        if not self.takreej_id:
            return
        if self.secondary:
            Across.main_window.showBook((self.book_id), (self.page_id), afterfunction='takreej')
        else:
            self.takreejContainer.displayTakreej(self.takreej_id, self.book_id, self.page_id)
            self.switchButtons(TAKREEJ, True)

    def switchTrajim(self):
        if self.secondary:
            self.showMan()
        else:
            if self.rijalButton.isVisible():
                self.rijal_switch = not self.rijal_switch
                self.rijalState()

    def switchToroq(self):
        if self.secondary:
            self.showToroq()
        else:
            if self.toroqButton.isVisible():
                self.toroq_switch = not self.toroq_switch
                self.toroqState()

    def switchTakreej(self):
        if self.secondary:
            self.showTakreej()
        else:
            if self.takreejButton.isVisible():
                self.takreej_switch = not self.takreej_switch
                self.takreejState()

    def switchPdf(self):
        if self.pdfDisplayButton.isVisible():
            self.pdf_switch = not self.pdf_switch
            self.pdfState()

    def rijalState(self):
        if self.rijal_switch:
            self.showMan()
        else:
            self.hideMan()

    def pdfState(self):
        if self.pdf_switch:
            self.showPdf()
        else:
            self.hidePdf()

    def toroqState(self):
        if self.toroq_switch:
            self.showToroq()
        else:
            self.hideToroq()

    def takreejState(self):
        if self.takreej_switch:
            self.showTakreej()
        else:
            self.hideTakreej()

    def hidePdf(self):
        if not self.pdfContainer.shown:
            return
        self.pdfContainer.setVisible(False)
        self.switchButtons(PDF, False)

    def hideMan(self):
        if not self.rijalContainer.shown:
            return
        self.rijalContainer.setVisible(False)
        self.switchButtons(RIJAL, False)

    def hideToroq(self):
        if not self.toroqContainer.shown:
            return
        self.toroqContainer.setVisible(False)
        self.switchButtons(TOROQ, False)

    def hideTakreej(self):
        if not self.takreejContainer.shown:
            return
        self.takreejContainer.setVisible(False)
        self.switchButtons(TAKREEJ, False)

    def display(self, data, correlate_tree=True, history=True, search_info=None, service=None):
        from engine import PageText
        self.last_display = (
         data, False, history, search_info)
        services = None
        try:
            services = data['services']
        except:
            pass

        self.services = json.loads(services) if services else {}
        self.page = safeStr(data['page'])
        self.pageLineEdit.setText(self.page)
        if self.has_numbers:
            self.numberLineEdit.setText(safeStr(data['number']))
        title_id = None
        if search_info:
            if 'title_id' in search_info:
                title_id = search_info['title_id']
        if self.page_id != data['id']:
            self.page_id = data['id']
            self.navButtonState()
            self.idSlider.blockSignals(True)
            self.idSlider.setValue(self.page_id)
            self.idSlider.blockSignals(False)
            attribute_part = None
            if self.parts_list:
                self.part = data['part']
                self.partComboBox.blockSignals(True)
                attribute_part = self.part
                self.partComboBox.setCurrentIndex(self.partComboBox.findText(arabize(attribute_part)))
                self.partComboBox.blockSignals(False)
            else:
                self.part = '0'
            self.textBrowser.setPage(attribute_part, self.page)
            if correlate_tree:
                self.refreshSide()
            if history:
                if self.history:
                    self.history = self.history[:self.history_index + 1]
                if search_info:
                    self.history.append((self.page_id, search_info))
                else:
                    self.history.append(self.page_id)
                self.history_index += 1
            self.checkHistoryButtons()
        if title_id:
            self.title_displayer.display(self.book_id, title_id, None, search_info)
            self.titlesBox.show()
        else:
            self.titlesBox.hide()
        display_bookid, display_pageid = self.reAlias()
        page_text = PageText(display_bookid, display_pageid)
        self.page_displayer.display(display_bookid, display_pageid, page_text, search_info, service, self.shorts)
        self.comment_displayer.display(display_bookid, display_pageid, page_text, search_info)

    def reAlias(self):
        if self.has_alias:
            book_id, page_id = BookDb(self.book_id).getAlias(self.page_id)
        else:
            book_id, page_id = self.book_id, self.page_id
        if book_id not in self.attribute_dict:
            self.attribute_dict[book_id] = self.getAttribute(book_id)
        self.textBrowser.setAttributeDict(self.attribute_dict[book_id])
        return (
         book_id, page_id)

    def diacritic(self, value):
        self.tashkeel = value
        if self.page_id:
            self.page_displayer.tashkeel()
            self.title_displayer.tashkeel()

    def userDiacritic(self, value):
        UserDb().setDiacritized(self.book_id, value)
        self.diacritic(value)

    def searchText(self, text=None):
        if not text:
            text = self.findonpageLineEdit.text()
        text = treatSearch(text)
        if text:
            search_info = buildFilter(text, True)
            self.page_displayer.talween(search_info)
            self.comment_displayer.talween(search_info)
            self.title_displayer.talween(search_info)
        else:
            self.page_displayer.talween()
            self.comment_displayer.talween()
            self.title_displayer.talween()

    def checkHistoryButtons(self):
        self.backToolButton.setEnabled(self.history_index != 0)
        self.forwardToolButton.setEnabled(self.history_index != len(self.history) - 1)

    def goHistory(self, increment):
        self.history_index += increment
        if isinstance(self.history[self.history_index], int):
            self.display((BookDb(self.book_id).getById(self.history[self.history_index])), history=False)
        else:
            self.display((BookDb(self.book_id).getById(self.history[self.history_index][0])), history=False, search_info=(self.history[self.history_index][1]))

    def goId(self, page_id):
        self.display(BookDb(self.book_id).getById(page_id))

    def goTitle(self, title_id):
        result = BookDb(self.book_id).getByTitle(title_id)
        self.textBrowser.setUpdatesEnabled(False)
        self.display(result, correlate_tree=False)
        self.textBrowser.scrollToAnchor(f"toc-{title_id}")
        self.textBrowser.setUpdatesEnabled(True)
        return result['page']

    def goService(self, service):
        self.setBookId(service[0])
        page_id = service[1]
        service_type = {'tafseer':'aya',  'man':'man',  'hadeeth':'hadeeth'}[service[2]]
        service_id = service[3]
        self.textBrowser.setUpdatesEnabled(False)
        self.display((BookDb(self.book_id).getById(page_id)), service=service)
        self.textBrowser.scrollToAnchor(f"{service_type}-{service_id}")
        self.textBrowser.setUpdatesEnabled(True)

    def goPart(self):
        self.display(BookDb(self.book_id).getByPart(latinize(self.partComboBox.currentText())))

    def resultClicked(self, res):
        first_id, second_id, query = res
        search_info = query.info()
        if query.type == QueryType.TITLES:
            search_info['title_id'] = second_id
            self.display((BookDb(self.book_id).getByTitle(second_id)), search_info=search_info)
        else:
            db = BookDb(self.book_id)
            result_id = second_id if first_id == self.book_id else db.getOrigin(first_id, second_id)
            self.display((BookDb(self.book_id).getById(result_id)), search_info=search_info)

    def goPage(self):
        page = safeInt(self.pageLineEdit.text())
        bookDb = BookDb(self.book_id)
        if page != 0:
            if self.parts_list:
                self.display(bookDb.getByPartPage(latinize(self.partComboBox.currentText()), page))
            else:
                self.display(bookDb.getByPage(page))
        else:
            self.display(bookDb.getById(self.page_id))

    def goNumber(self):
        number = safeInt(self.numberLineEdit.text())
        bookDb = BookDb(self.book_id)
        if number != 0:
            self.display(bookDb.getByNumber(number))
        else:
            self.display(bookDb.getById(self.page_id))

    def saveComment(self, text):
        display_bookid, display_pageid = self.reAlias()
        book = Book(display_bookid)
        book.updatePage(display_pageid, {'comment': safeNorm(text)})
        book.commitBook()

    def closeTab(self):
        if self.sideBar:
            self.sideBar.closeTab()
        if self.betaka:
            self.betaka.close()
        UserDb().updateHistory(self.book_id, self.page_id)

    def closeEvent(self, event):
        self.closed.emit(self)
        event.accept()


class Comment(QWidget):
    saveComment = Signal(str)

    def __init__(self, button, parent=None):
        super().__init__(parent)
        shortcut(self, 'Ctrl+S', (self.save), context=(Qt.WidgetWithChildrenShortcut))
        self.button = button
        self.textEdit = TextEdit()
        self.textEdit.setAcceptRichText(False)
        self.pinButton = customToolButton(':/icons/pin.png', self.tr('Pin Comment Panel'))
        self.undoButton = customToolButton(':/icons/undo.png', self.tr('Undo'))
        self.redoButton = customToolButton(':/icons/redo.png', self.tr('Redo'))
        self.saveButton = customToolButton(':/icons/save.png', shortcutLabel((self.tr('Save Comment')), 'Ctrl+S', separator='     '))
        self.pinButton.setCheckable(True)
        self.undoButton.setEnabled(False)
        self.redoButton.setEnabled(False)
        self.textEdit.setStyleSheet(CssCache.getCache('c'))
        commentLayout = customLayout(True, [self.pinButton, 0, self.undoButton, self.redoButton,
         self.saveButton],
          spacing=3)
        customLayout(False, [self.textEdit, commentLayout], parent=self)
        self.saveButton.clicked.connect(self.save)
        self.undoButton.clicked.connect(self.textEdit.undo)
        self.redoButton.clicked.connect(self.textEdit.redo)
        self.textEdit.undoAvailable.connect(lambda value: self.undoButton.setEnabled(value)
)
        self.textEdit.redoAvailable.connect(lambda value: self.redoButton.setEnabled(value)
)
        self.textEdit.textChanged.connect(lambda: self.saveButton.setEnabled(True)
)

    def applyTextFormat(self):
        self.textEdit.setStyleSheet(CssCache.getCache('c'))
        blockFmt = QTextBlockFormat()
        spacing = lineHeight('font_comments_spacing', Settings.getValue('font_comments'))
        blockFmt.setLineHeight(spacing * 100, 1)
        theCursor = self.textEdit.textCursor()
        selected = theCursor.hasSelection()
        selection_start = theCursor.selectionStart()
        selection_end = theCursor.selectionEnd()
        formatCursor = QTextCursor(self.textEdit.document())
        formatCursor.select(QTextCursor.Document)
        formatCursor.mergeBlockFormat(blockFmt)
        if selected:
            theCursor.setPosition(selection_start)
            theCursor.setPosition(selection_end, QTextCursor.KeepAnchor)
        self.textEdit.setTextCursor(theCursor)

    def toggle(self, value):
        self.setVisible(value)
        if value:
            self.textEdit.setFocus()

    def save(self):
        self.textEdit.setFocus()
        self.saveButton.setEnabled(False)
        self.saveButton.repaint()
        text = self.textEdit.toPlainText()
        self.saveComment.emit(text)

    def setHtml(self, text, _, keep_position=None):
        if text:
            if keep_position:
                pos = self.textEdit.verticalScrollBar().value()
                self.textEdit.setHtml(text)
                self.textEdit.verticalScrollBar().setValue(pos)
            else:
                self.textEdit.setHtml(text)
            self.ensureVisible(True)
        else:
            self.textEdit.clear()
            self.ensureVisible(self.pinButton.isChecked())
        self.applyTextFormat()
        self.textEdit.document().clearUndoRedoStacks()
        self.saveButton.setEnabled(False)

    def scrollToAnchor(self, anchor):
        self.textEdit.scrollToAnchor(anchor)

    def ensureVisible(self, value):
        if self.isVisible() != value:
            self.setVisible(value)
        if self.button.isChecked() != value:
            self.button.setChecked(value)


class Info(CustomDialog):

    def __init__(self, parent, book_id, separate=None):
        super().__init__(parent, icon=':/icons/betaka.png')
        self.setWindowTitle(self.tr('Book Information'))
        self.pages = QStackedWidget()
        self.author = None
        self.book_id = book_id
        toolbar = QToolBar(self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.group = QButtonGroup()
        self.textBrowser = flexibleBrowser()
        betaka, cover = CoreDb().bookBetaka((self.book_id), None, report_cover=True)
        self.textBrowser.setHtml(betaka)
        self.pages.addWidget(self.textBrowser)
        if separate:
            self.pages.setMinimumWidth(500)
        core = customLayout(True, [toolbar, self.pages], margins=0)
        texts = (
         self.tr('Book'), self.tr('Author'))
        icons = (BookCache.bookIcon(self.book_id), ':/icons/authors.png')
        slots = (self.showBetaka, self.showAuthor)
        for i in range(2):
            button = customToolButton(text=(texts[i]), icon=(icons[i]), slot=(slots[i]), text_beside=True, checkable=True)
            toolbar.addWidget(button)
            self.group.addButton(button)
            if i == 0:
                button.setChecked(True)

        safe_height = 500
        height = None
        if cover:
            try:
                pix = QPixmap()
                pix.loadFromData(cover)
                scale = Scale.scale()
                if scale != 1:
                    pix.setDevicePixelRatio(scale)
                height = pix.height()
                width = pix.width()
            except:
                pass

        if height:
            label = QLabel()
            label.setScaledContents(True)
            label.setPixmap(pix)
            label.setFixedHeight(height)
            label.setFixedWidth(width)
            self.setLayout(customLayout(False, [label, 3, core]))
        else:
            self.pages.setMinimumHeight(safe_height)
            self.setLayout(customLayout(True, [core]))
        self.showBetaka()

    def showBetaka(self):
        self.pages.setCurrentWidget(self.textBrowser)
        self.setFocus()

    def showAuthor(self):
        if not self.author:
            self.author = Author('font_betaka')
            self.author.setBook(self.book_id)
            self.pages.addWidget(self.author)
        self.pages.setCurrentWidget(self.author)
        self.setFocus()


class Shorts:

    def __init__(self, rep):
        self.rep = {}
        for k in rep:
            self.rep[f"<s{k}>"] = f"<span data-type='title'>{rep[k]}</span>"

        self.rep = dict(((re.escape(k), v) for k, v in self.rep.items()))
        self.pattern = re.compile('|'.join(self.rep.keys()))

    def expand(self, text):
        return self.pattern.sub(lambda m: self.rep[re.escape(m.group(0))]
, text)


class Container(QStackedWidget):

    def __init__(self):
        super().__init__()
        self.pdf_displayer = self.men_displayer = self.toroq_displayer = self.takreej_displayer = self.shown = None
        self.setVisible(False)

    def displayTakreej(self, hadeeth_id, book, page):
        from rijal import Takreej
        if not self.takreej_displayer:
            self.takreej_displayer = Takreej()
            self.addWidget(self.takreej_displayer)
        self.takreej_displayer.setHadeeth(hadeeth_id, (book, page))
        self.setCurrentWidget(self.takreej_displayer)
        self.ensureShown()

    def showPdf(self):
        self.setCurrentWidget(self.pdf_displayer)
        self.ensureShown()

    def displayPage(self, page_no=None, filename=None):
        if not self.pdf_displayer:
            from pdfviewer import PdfGui
            self.pdf_displayer = PdfGui()
            self.displayPdfPage(page_no or 1, filename)
            self.addWidget(self.pdf_displayer)
        else:
            self.displayPdfPage(page_no, filename)
        self.showPdf()

    def displayPdfPage(self, page_no, filename):
        self.retained_file = filename
        self.retained_page = page_no
        QTimer.singleShot(0, self.delayedPdf)

    def delayedPdf(self):
        self.pdf_displayer.displayPage(self.retained_page, self.retained_file)

    def blanch(self, value):
        if not self.pdf_displayer:
            from pdfviewer import PdfGui
            self.pdf_displayer = PdfGui()
            self.pdf_displayer.blanch(value)
            self.addWidget(self.pdf_displayer)
        else:
            self.pdf_displayer.blanch(value)
        self.showPdf()

    def ensureShown(self):
        self.setVisible(True)
        if not self.shown:
            self.shown = True
            if self.parent():
                self.setMinimumWidth(int(self.parent().width() * 0.43))
                self.setMinimumHeight(int(self.parent().height() * 0.43))

    def displayMan(self, man_list, man_id):
        from rijal import Man
        if not self.men_displayer:
            self.men_displayer = Man()
            self.addWidget(self.men_displayer)
        self.men_displayer.displayMan(man_list, man_id)
        self.setCurrentWidget(self.men_displayer)
        self.ensureShown()

    def displayToroq(self, hadeeth_id):
        from rijal import TorqList
        if not self.toroq_displayer:
            self.toroq_displayer = TorqList()
            self.addWidget(self.toroq_displayer)
        self.toroq_displayer.setHadeeth(hadeeth_id)
        self.setCurrentWidget(self.toroq_displayer)
        self.ensureShown()


def uniList(str_list, int_list, m_valve):
    for item in str_list:
        item = int(item)
        if item > 1:
            if item not in m_valve:
                m_valve.add(item)
                int_list.append(item)