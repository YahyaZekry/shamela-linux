# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: quran.py
import re
from qtpy.QtCore import Qt, Signal, QAbstractListModel, QTimer
from qtpy.QtWidgets import QComboBox, QGroupBox, QWidget, QLabel, QListView, QSplitter
from engine import Query, QueryType, collectQuranPage, buildFilter, is_shutdown_exception
from across import Across
from cache import CssCache
from customs import BookHolder, styledLabel, customToolButton, flexibleBrowser, hLine, NVDA, customLayout, LineEdit, customSplitter, NumCombo, ServiceBooks, TimedLineEdit, iconedPush, standardFont, shortcutLabel, directShortcutLabel
from dbmanager import UserDb
from quraninfo import posFromAya, ayat, fillPosition, marks, getSoraNames, parted
from search import Searcher
from searchboxes import SearchWidget
from textmanager import treatSearch, arabize, formatPage, tip, iso, contains, clean_invisible, centeredHr
PAGES = 604
HONORIFIC_BASMALA = '﷽'

class Sora:
    _names = []
    _iso_names = []

    @classmethod
    def _getNames(cls):
        if not cls._names:
            cls._names = getSoraNames()
        return cls._names

    @classmethod
    def _getIsoNames(cls):
        if not cls._iso_names:
            cls._iso_names = [iso(name) for name in cls._getNames()]
        return cls._iso_names

    @classmethod
    def name(cls, sora_number):
        return cls._getNames()[sora_number - 1]

    @classmethod
    def filter(cls, text=None):
        if text:
            i_text = iso(text)
            if i_text:
                pieces = iso(text).split(' ')
                return [i + 1 for i, name in enumerate(cls._getIsoNames()) if contains(name, pieces)]
        return list(range(1, 115))


class QuranWidget(QWidget):
    closed = Signal(QWidget)

    def __init__(self, saved_value=None):
        super().__init__()
        self.full_title = None
        self.go_widget = GoWidget()
        search_info = (saved_value['search'] if 'search' in saved_value else None) if saved_value else None
        rasm, aya_id = [saved_value['rasm'], saved_value['aya_id']] if saved_value else UserDb().load('quran_pos') or ['majma', 1]
        self.page_displayer = PageDisplayer(self.go_widget, rasm)
        self.moshaf = True
        self.books = ServiceBooks('tafseer')
        self.quranButton = iconedPush(':/icons/quran.png', (self.tr('The holy Quran')), slot=(self.displayQuran))
        self.book_widget = QWidget()
        self.book_widget.setLayout(customLayout(True, [self.quranButton, self.books]))
        self.container = BookHolder(off_features={'unlined', 'hide_bar'})
        both = QWidget()
        both.setLayout(customLayout(False, [self.page_displayer, self.container]))
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)
        splitter.addWidget(self.book_widget)
        splitter.addWidget(both)
        width = splitter.width()
        splitter.setSizes([122, width - 122])
        self.setLayout(customLayout(False, [self.go_widget, splitter], margins=[1, 0, 1, 1]))
        self.go_widget.selected.connect(self.goSelection)
        self.books.display.connect(self.goService)
        if search_info:
            self.container.setVisible(False)
            self.quranButton.setEnabled(False)
            self.page_displayer.searchPanel.boxes.load(search_info)
            if 'results_hash' in search_info:
                query = self.page_displayer.searchPanel.query
                query.load(search_info)
                search_info['results'] = query.results
                self.page_displayer.searchPanel.triggerBox(search_info)
        else:
            self.go_widget.go(aya_id=aya_id)

    def save(self, context_id):
        save_dict = {'aya_id':self.go_widget.position['aya_id'],  'rasm':self.page_displayer.rasm}
        search_data = self.page_displayer.searchInfo(context_id)
        if search_data:
            save_dict['search'] = search_data
        return [
         'QURAN', save_dict]

    def focusResults(self):
        if self.page_displayer.searchPanel.isVisible():
            self.page_displayer.searchPanel.view.setFocus()

    def focusSearch(self):
        self.page_displayer.focusSearch()

    def shortedPrevious(self):
        if self.moshaf:
            self.page_displayer.shortedPrevious()
        else:
            self.container.book.shortedPrevious()

    def shortedNext(self):
        if self.moshaf:
            self.page_displayer.shortedNext()
        else:
            self.container.book.shortedNext()

    def showSearch(self):
        if self.moshaf:
            self.page_displayer.line.setFocus()
        else:
            self.container.book.showSearch()

    def switchPdf(self):
        if not self.moshaf:
            self.container.book.switchPdf()

    def newDisplay(self):
        if not self.moshaf:
            self.container.book.newDisplay()

    def switchTakreej(self):
        if not self.moshaf:
            self.container.book.switchTakreej()

    def goText(self):
        if self.moshaf:
            self.page_displayer.goText()
        else:
            self.container.book.goText()

    def goTree(self):
        if self.moshaf:
            self.page_displayer.goTree()
        else:
            self.container.book.goTree()

    def showBetaka(self):
        if not self.moshaf:
            self.container.book.showBetaka()

    def shortBack(self):
        if not self.moshaf:
            self.container.book.shortBack()

    def shortForward(self):
        if not self.moshaf:
            self.container.book.shortForward()

    def focusBookResults(self):
        if not self.moshaf:
            self.container.book.sideBar.focusResult()

    def goService(self, service):
        self.container.showBook(service=service)
        self.page_displayer.setVisible(False)
        self.container.setVisible(True)
        self.quranButton.setEnabled(True)
        self.moshaf = None

    def displayQuran(self):
        if not self.moshaf:
            self.moshaf = True
            self.page_displayer.go()
            self.page_displayer.setVisible(True)
            self.container.setVisible(False)
            self.quranButton.setEnabled(False)

    def goSelection(self, selection_dict, search_signal):
        has_books = self.books.loadItems(selection_dict['aya_id'])
        if has_books:
            self.book_widget.setVisible(True)
        else:
            self.book_widget.setVisible(False)
            self.moshaf = True
        if self.moshaf:
            search_signal or self.page_displayer.go()
            self.page_displayer.setVisible(True)
            self.container.setVisible(False)
            self.quranButton.setEnabled(False)
        else:
            self.books.displayItem()
            self.quranButton.setEnabled(True)

    def closeTab(self):
        pass

    def closeEvent(self, event):
        self.closed.emit(self)
        event.accept()


class GoWidget(QWidget):
    selected = Signal(dict, bool)

    def __init__(self):
        super().__init__()
        self.position = {}
        self.soras_table = self._SoraList(self.go)
        self.quarters = self._QuarterSelector(self.go)
        self.pages = self._PagesSelector(self.go)
        self.setLayout(customLayout(True, [self.soras_table, self.quarters, self.pages], spacing=6))
        self.setMaximumWidth(self.soras_table.view.sizeHintForColumn(0) + 50)
        self.ignore_one = False

    def go(self, aya_id=None, sora=None, aya=None, page=None, quarter=None, search_signal=None):
        self.position = {}
        if aya_id:
            self.position['aya_id'] = aya_id
        if sora:
            self.position['sora'] = sora
        if aya:
            self.position['aya'] = aya
        if page:
            self.position['page'] = page
        if quarter:
            self.position['quarter'] = quarter
        self.adjustPosition()
        self.selected.emit(self.position, search_signal)

    def goNext(self):
        if self.position['page'] != PAGES:
            self.go(page=(self.position['page'] + 1))

    def goPrevious(self):
        if self.position['page'] != 1:
            self.go(page=(self.position['page'] - 1))

    def goFirst(self):
        if self.position['page'] != 1:
            self.go(page=1)

    def goLast(self):
        if self.position['page'] != PAGES:
            self.go(page=PAGES)

    def adjustPosition(self):
        fillPosition(self.position)
        if not NVDA.isRunning():
            self.soras_table.injectPosition(self.position)
            self.quarters.injectPosition(self.position)
            self.pages.injectPosition(self.position)

    class _SoraList(QGroupBox):

        def __init__(self, slot):
            QGroupBox.__init__(self)
            self.slot = slot
            self.setTitle(self.tr('Soras'))
            self.a_label = QLabel(self.tr('Aya: '))
            self.aya_combo = NumCombo()
            self.model = self._SoraModel()
            self.view = self._SoraView()
            self.view.setModel(self.model)
            standardFont(self.view)
            self.view.loadAll()
            self.soraFilterLineEdit = TimedLineEdit(search_slot=(self.searchSoraName), focus_list=(self.view))
            self.soraFilterLineEdit.setPlaceholderText(self.tr('Search'))
            self.setLayout(customLayout(True, [3, self.soraFilterLineEdit, self.view, 2, self.a_label, self.aya_combo], spacing=6, margins=6))
            self.view.soraSelected.connect(self.soraSelected)
            self.aya_combo.valueChanged.connect(self.ayaSelected)

        def soraSelected(self, sora_number):
            self.preSoraSelect(sora_number)
            self.slot(sora=sora_number)

        def preSoraSelect(self, sora_number):
            max_aya = ayat(sora_number)
            self.a_label.setText(arabize('{} [1 - {}]'.format(self.tr('Aya: '), max_aya)))
            self.aya_combo.setMaximum(max_aya)

        def ayaSelected(self, aya):
            sora = 0
            try:
                sora = self.view.currentSora()
            except:
                pass

            if sora != 0:
                self.slot(sora=sora, aya=aya)

        def injectPosition(self, position):
            if self.view.currentSora() != position['sora']:
                self.view.blockSignals(True)
                self.view.setCurrentSora(position['sora'])
                self.view.blockSignals(False)
                self.preSoraSelect(position['sora'])
            if self.aya_combo.value() != position['aya']:
                self.aya_combo.blockSignals(True)
                self.aya_combo.setValue(position['aya'])
                self.aya_combo.blockSignals(False)

        def searchSoraName(self):
            text = self.soraFilterLineEdit.text()
            if text:
                text = treatSearch(text)
                if text:
                    soras = Sora.filter(text)
                    if soras:
                        self.model.setSource(soras)
                        self.view.selectFirst()
                        return
            self.view.loadAll()

        class _SoraView(QListView):
            soraSelected = Signal(int)

            def __init__(self):
                QListView.__init__(self)

            def currentSora(self):
                index = self.currentIndex()
                if index.isValid():
                    return self.model().source[index.row()]

            def _spesifySora(self, sora_number):
                i = 0
                for m_number in self.model().source:
                    if sora_number == m_number:
                        return i
                    i += 1

                return -1

            def setCurrentSora(self, sora_number):
                i = self._spesifySora(sora_number)
                if i == -1:
                    self.loadAll()
                    i = self._spesifySora(sora_number)
                index = self.model().index(i, 0)
                self.setCurrentIndex(index)

            def loadAll(self):
                self.soras = Sora.filter()
                self.model().setSource(self.soras)
                self.selectFirst()

            def selectFirst(self):
                self.setCurrentIndex(self.model().index(0, 0))

            def selectionChanged(self, QItemSelection, QItemSelection_1):
                sora = self.currentSora()
                if sora:
                    self.soraSelected.emit(sora)

        class _SoraModel(QAbstractListModel):

            def __init__(self):
                QAbstractListModel.__init__(self)
                self.source = []

            def rowCount(self, parent):
                return len(self.source)

            def setSource(self, num_list):
                self.source = num_list
                self.beginResetModel()
                self.endResetModel()

            def data(self, index, role=None):
                if index.isValid():
                    if role == Qt.DisplayRole:
                        row = index.row()
                        return arabize('[{}]   {}'.format(self.source[row], Sora.name(self.source[row])))

    class _PagesSelector(QGroupBox):

        def __init__(self, slot):
            QGroupBox.__init__(self)
            self.slot = slot
            self.setTitle('{} {}    '.format(self.tr('Pages'), arabize(f"[1 - {PAGES}]")))
            self.pages = NumCombo()
            self.pages.setMaximum(PAGES)
            self.setLayout(customLayout(True, [3, self.pages], spacing=6, margins=6))
            self.pages.valueChanged.connect(self.goPage)

        def goPage(self, page):
            self.slot(page=page)

        def injectPosition(self, position):
            if position['page'] != self.pages.value():
                self.pages.setValue(position['page'])

    class _QuarterSelector(QGroupBox):

        def __init__(self, slot):
            QGroupBox.__init__(self)
            self.slot = slot
            self.setTitle(self.tr('Parts and quarters'))
            self.parts = QComboBox()
            self.ahzaab = QComboBox()
            self.quarters = QComboBox()
            part = self.tr('Part:')
            self.parts.addItems([f'{part}    {arabize(("{i}"))}' for i in range(1, 31)])
            self.ahzaab.addItems([self.tr('First Hezb'), self.tr('Second Hezb')])
            self.quarters.addItems([self.tr('First Quarter'), self.tr('Second Quarter'),
             self.tr('Third Quarter'), self.tr('Fourth Quarter')])
            self.setLayout(customLayout(True, [3, self.parts, self.ahzaab, self.quarters], spacing=6, margins=6))
            self.parts.activated.connect(self.partSelected)
            self.ahzaab.activated.connect(self.hizbSelected)
            self.quarters.activated.connect(self.quarterSelected)

        def partSelected(self):
            self.ahzaab.setCurrentIndex(0)
            self.quarters.setCurrentIndex(0)
            self.quarterSelected()

        def hizbSelected(self):
            self.quarters.setCurrentIndex(0)
            self.quarterSelected()

        def quarterSelected(self):
            p = self.parts.currentIndex()
            h = self.ahzaab.currentIndex()
            q = self.quarters.currentIndex()
            quarter = p * 8 + h * 4 + q + 1
            self.slot(quarter=quarter)

        def setIndex(self, combo, value):
            index = value - 1
            if index != combo.currentIndex():
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)

        def injectPosition(self, position):
            part, hezb, quarter = parted(position['quarter'])
            self.setIndex(self.parts, part)
            self.setIndex(self.ahzaab, hezb)
            self.setIndex(self.quarters, quarter)


class PageDisplayer(QWidget):

    def __init__(self, go_widget, rasm, search_info=None):
        super().__init__()
        self.search_info = {}
        self.go_widget = go_widget
        self.quran_browser = flexibleBrowser()
        self.history = []
        self.rasm = rasm
        self.rasmCombo = QComboBox()
        self.rasmCombo.addItems([self.tr('majma'), self.tr('amiri'), self.tr('emlaa')])
        self.rasmCombo.setCurrentIndex({'majma':0,  'amiri':1,  'emlaa':2}[self.rasm])
        self.rasmCombo.activated.connect(self.rasmChanged)
        copyToolButton = customToolButton(':/icons/copy.png', (directShortcutLabel(self.tr('Copy with attributes'), 'Ctrl+Shift+C')),
          slot=(self.quran_browser.copyAttribute))
        copyToolButton.setEnabled(False)
        self.quran_browser.copyAvailable.connect(copyToolButton.setEnabled)
        self.findonpageLineEdit = LineEdit(digit_policy='ascii', slot=(self.searchText), width=170)
        self.findonpageLineEdit.setPlaceholderText(self.tr('Find on Page'))
        self.findonpageLineEdit.textChanged.connect(self.searchText)
        self.search_aya_id = None
        self.part_label = styledLabel(100)
        self.sora_label = styledLabel(100)
        self.page_lable = styledLabel(30)
        self.firstToolButton = customToolButton(':/icons/first.png', (self.tr('First Page')), slot=(self.goFirst))
        self.previoustToolButton = customToolButton(':/icons/previous.png', (self.tr('Previous Page') + '  F5'), slot=(self.goPrevious))
        self.nextToolButton = customToolButton(':/icons/next.png', (self.tr('Next Page') + '  F6'), slot=(self.goNext))
        self.lastToolButton = customToolButton(':/icons/last.png', (self.tr('Last Page')), slot=(self.goLast))
        navigate_layout = customLayout(False, [self.part_label, 3, self.firstToolButton, self.previoustToolButton,
         self.page_lable, self.nextToolButton, self.lastToolButton, 3,
         self.sora_label])
        self.searchPanel = SearchPanel(self.go)
        self.showSearchButton = customToolButton(':/icons/search2.png', ' ' + self.tr('Search in Holy Quran'))
        self.showSearchButton.setCheckable(True)
        if search_info or UserDb().load('quran_search_visible', True):
            self.showSearchButton.setChecked(True)
        else:
            self.searchPanel.setVisible(False)
        self.line = TimedLineEdit(search_slot=(self.quickSearch), focus_list=(self.searchPanel.view), interval=951)
        self.line.setPlaceholderText(shortcutLabel(self.tr('Search in Ayat'), 'Ctrl+F'))
        copyOptionButton = customToolButton(':/icons/font.png', (tip(self.tr('Holy Quran Font'))), slot=(self.copyOptions))
        copyToolButton = customToolButton(':/icons/copy.png', (directShortcutLabel(self.tr('Copy with attributes'), 'Ctrl+Shift+C')),
          slot=(self.quran_browser.copyAttribute))
        _strip_h = self.line.sizeHint().height()
        for widget in (self.showSearchButton, self.rasmCombo, self.line, self.part_label,
         self.sora_label, self.page_lable, self.firstToolButton, self.previoustToolButton,
         self.nextToolButton, self.lastToolButton, copyToolButton, copyOptionButton,
         self.findonpageLineEdit):
            widget.setFixedHeight(_strip_h)

        upper_layout = customLayout(False, [
         self.showSearchButton, 6, self.rasmCombo, 6, self.line, 0, navigate_layout, 0,
         copyToolButton, 1, copyOptionButton, 10, self.findonpageLineEdit],
          margins=0)
        splitter = customSplitter(True, customLayout(True, [upper_layout, self.quran_browser], margins=0), self.searchPanel, 75)
        self.setLayout(customLayout(True, [splitter], margins=0))
        self.showSearchButton.clicked.connect(lambda: self.searchPanel.toggle(self.showSearchButton.isChecked()))
        QTimer.singleShot(0, self.line.setFocus)

    def searchInfo(self, context_id):
        if self.searchPanel:
            return self.searchPanel.getInfo(context_id)

    def goText(self):
        self.quran_browser.setFocus()

    def goTree(self):
        self.go_widget.soras_table.soraFilterLineEdit.setFocus()

    def shortedNext(self):
        self.go_widget.goNext()
        self.quran_browser.readPage()

    def shortedPrevious(self):
        self.go_widget.goPrevious()
        self.quran_browser.readPage()

    def goFirst(self):
        self.go_widget.goFirst()

    def goPrevious(self):
        self.go_widget.goPrevious()

    def goNext(self):
        self.go_widget.goNext()

    def goLast(self):
        self.go_widget.goLast()

    def quickSearch(self):
        text = f"{treatSearch(self.line.text())}"
        if len(text) < 3:
            return
        if self.searchPanel.still_searching:
            return
        if not self.searchPanel.isVisible():
            self.searchPanel.setVisible(True)
        self.searchPanel.triggerSearch(text)

    def focusSearch(self):
        if not self.showSearchButton.isChecked():
            self.showSearchButton.click()
        self.searchPanel.boxes.setFocus()

    def copyOptions(self):
        Across.main_window.showOptions(list_item='quran')

    def assemblePage(self):
        page = []
        ayas = collectQuranPage(self.go_widget.position['page'], self.rasm, self.search_info, self.search_aya_id)
        open_section = False
        for aya_id, aya_text in ayas:
            sora, aya = posFromAya(aya_id)
            if aya == 1:
                heading = centeredHr(f"<span class='title'>[سورة {Sora.name(sora)}]</span>", default_color=True)
                if open_section:
                    page.append('</div>')
                page.append(heading)
                page.append("<div align='center' style='margin:0'>")
                open_section = True
                if sora not in (1, 9):
                    page.append(f"{HONORIFIC_BASMALA}<br>")
            page.append(formateAya(marks(aya_id, aya, aya_text), aya, self.rasm))

        if open_section:
            page.append('</div>')
        return f"<p><table width=95% align='center' cellpadding='12'><tr><td align='center'>{''.join(page)}</td></tr></table><p>"

    def go(self, query=None, aya_id=None):
        if query and query.phrases:
            self.search_info = query.info()
            self.search_aya_id = aya_id
            self.go_widget.go(aya_id=aya_id, search_signal=True)
        else:
            self.search_info = {}
            self.search_aya_id = None
        self.display()

    def rasmChanged(self):
        rasm = [
         'majma', 'amiri', 'emlaa'][self.rasmCombo.currentIndex()]
        if self.rasm == rasm:
            return
        self.rasm = rasm
        self.display()

    def searchText(self, text=None):
        if not text:
            text = self.findonpageLineEdit.text()
        else:
            text = treatSearch(text)
            if text:
                self.search_info = buildFilter(text, True)
                self.search_info['type'] = QueryType.QURAN.value
                self.search_aya_id = None
            else:
                self.search_info = {}
        self.display()

    def display(self):
        UserDb().save('quran_pos', [self.rasm, self.go_widget.position['aya_id']])
        self.quran_browser.setAttributeDict({'rasm':self.rasm,  'page':self.go_widget.position['page']})
        try:
            html, _ = formatPage((self.assemblePage()), (CssCache.getCache(self.rasm)), quran=True)
        except:
            return
        else:
            if self.search_info:
                self.quran_browser.setUpdatesEnabled(False)
            self.quran_browser.setHtml(html, rasm=(self.rasm))
            if self.search_info:
                self.quran_browser.scrollToAnchor('go')
                self.quran_browser.setUpdatesEnabled(True)
            self.navButtonState()

    def navButtonState(self):
        enabled = self.go_widget.position['page'] != 1
        self.firstToolButton.setEnabled(enabled)
        self.previoustToolButton.setEnabled(enabled)
        enabled = self.go_widget.position['page'] != PAGES
        self.lastToolButton.setEnabled(enabled)
        self.nextToolButton.setEnabled(enabled)
        part, _, _ = parted(self.go_widget.position['quarter'])
        self.part_label.setText(self.tr('Part:') + ' ' + arabize((f"{part}")))
        self.sora_label.setText(self.tr('Sora:') + ' ' + Sora.name(self.go_widget.position['sora']))
        self.page_lable.setText(arabize((f"{self.go_widget.position['page']}")))


def formateAya(aya_text, aya_number, rasm):
    if rasm == 'majma':
        if NVDA.isRunning():
            return f"""{aya_text} <span class=\'title\'><font face="Traditional Naskh">({aya_number}) </font></span>"""
        aya_str = str(aya_number)
        if Across.os != 'mac':
            aya_str = aya_str[::-1]
        return f"{aya_text} <span class='title'>{arabize(aya_str, True)}</span></span> "
    else:
        if rasm == 'amiri':
            return f"""{aya_text} <span class='title'>\u06dd{arabize(("{aya_number}"), True)}</span> """
        if rasm == 'emlaa':
            return f"""{aya_text.replace('۞', '✷')} <span class='title'>({arabize(("{aya_number}"), True)})</span> """


class SearchPanel(QWidget):

    def __init__(self, go_function):
        QWidget.__init__(self)
        self.still_searching = None
        self.query = Query(Across.global_index)
        self.query.type = QueryType.QURAN
        self.go_function = go_function
        self.boxes = SearchWidget(self.triggerBox, True)
        self.searcher = Searcher(no_focus=True)
        self.searcher.setQuery(self.query)
        self.searcher.display_slot = self.showResult
        self.searcher.completed_slot = self.searchCompleted
        self.searcher.boxes = self.boxes
        self.info = {}
        self.view = self.searcher.constructViewer()
        v_layout = customLayout(False, [self.boxes, 2, self.view])
        self.setLayout(customLayout(True, [hLine(), v_layout]))

    def getInfo(self, context_id):
        if self.searcher.source:
            row = self.view.currentIndex().row()
            return self.query.save({'source':self.searcher.source,  'row':row}, context_id=context_id)

    def toggle(self, value):
        self.setVisible(value)
        if value:
            self.boxes.setFocus()
        UserDb().save('quran_search_visible', value)

    def triggerBox(self, info):
        info['phrases'] = self.qTreatPhrases(info['phrases'])
        self.info = info
        self.info['type'] = QueryType.QURAN.value
        self.query.clear()
        self.query.load(self.info)
        if self.query.results:
            self.view.bypassFirst(info['results']['row'])
        self.still_searching = True
        self.searcher.start()

    def searchCompleted(self, _):
        self.still_searching = None

    def triggerSearch(self, text):
        info = {'phrases': buildFilter(text, True)['phrases']}
        self.triggerBox(info)

    def showResult(self, aya_id):
        self.go_function(query=(self.searcher.query), aya_id=(int(aya_id)))

    def qTreatPhrases(self, p_list):
        return [[[self.qTreatPhrase(phrase) for phrase in panel] for panel in panels] for panels in p_list]

    @staticmethod
    def qTreatPhrase(phrase):
        phrase = clean_invisible(phrase)
        phrase = f" {phrase} "
        phrase = re.sub('\\bيا\\b +', 'يا', phrase)
        phrase = re.sub('\\bويا\\b +', 'ويا', phrase)
        phrase = re.sub('\\bها(\\**) ([اآأإ])نتم\\b', 'ها\\1\\2نتم', phrase)
        phrase = phrase.replace('بعدما', 'بعد ما')
        phrase = phrase.replace('حيي ال', 'حي ال')
        phrase = phrase.replace('حيى ال', 'حي ال')
        phrase = phrase.strip()
        return phrase