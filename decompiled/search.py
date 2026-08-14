# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: search.py
from collections import defaultdict
import threading, traceback
from qtpy.QtCore import QThread, Signal, Qt, QCoreApplication, QModelIndex, QPoint
from qtpy.QtGui import QFontMetrics, QPalette, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QApplication, QLabel, QHeaderView, QStyle, QStyledItemDelegate, QStyleOptionViewItem
import dbmanager, quraninfo
from across import Across
from cache import BookCache, AuthorCache, DataCache
from customs import unhideSelection, TableView, TableModel, QtFont, customMessage, specialSelectRow, fitRow
from theme import Icon
from settings import Settings
from textmanager import arabize, tip, tipH, tipHint, tipAuthor, conditioned, red
from engine import QueryType

class CachedTableModel(TableModel):

    def __init__(self, headers=None, parent=None):
        self.cache = DataCache(self.getData)
        super().__init__(headers, parent)

    def clearCache(self):
        self.cache.clear()

    def getData(self, row_column_role):
        pass

    def data(self, index, role):
        if index.isValid():
            row = index.row()
            column = index.column()
            return self.cache.get((row, column, role))

    def setSource(self, source, no_select=None):
        self.cache.clear()
        super().setSource(source, no_select)

    def removeRows(self, row, parent=QModelIndex()):
        self.cache.clear()
        super().removeRows(row, parent)


class HtmlDelegate(QStyledItemDelegate):

    def __init__(self, font, wide, parent=None):
        super().__init__(parent)
        self.label = QLabel()
        self.label.setContentsMargins(0, 0, 6, 0)
        self.label.setFont(font)
        self.label.setWordWrap(wide)
        self.colors_normal = (
         QApplication.palette().text().color().name(), False)

    def delegatedStyle(self, option, selected, active):
        palette = option.palette
        if Across.active_theme != 'native_light':
            return (
             palette.color(QPalette.Text).name(), bool(selected and active))
        else:
            return selected or self.colors_normal
        group = QPalette.Active if active else QPalette.Inactive
        text_color = palette.color(group, QPalette.HighlightedText).name()
        cobalt = palette.color(group, QPalette.Highlight).lightness() < 128
        return (text_color, cobalt)

    def paint(self, painter, option, index):
        self.label.setFixedSize(option.rect.size())
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        style = options.widget.style() if options.widget else QApplication.style()
        style.drawPrimitive(QStyle.PE_PanelItemViewItem, options, painter, options.widget)
        selected = option.state & QStyle.State_Selected
        active = option.state & QStyle.State_Active
        text_color, cobalt = self.delegatedStyle(options, selected, active)
        text = red(options.text, cobalt)
        self.label.setText(f"<body dir=rtl><font color={text_color}>{text}</font></body>")
        self.label.setStyleSheet('background-color: transparent')
        painter.save()
        painter.translate(option.rect.topLeft())
        self.label.render(painter, QPoint(0, 0))
        painter.restore()


class Searcher:
    _threads_lock = threading.RLock()
    _active_threads = set()

    def __init__(self, no_focus=None):
        self.view = SearchView(self, no_focus)
        self.query = None
        self.display_slot = self.completed_slot = self.filter_slot = self.boxes = None
        self.first_result_slot = None
        self._first_result_fired = False
        self.model = self.categories_model = self.centuries_model = None
        self.filter_enabled = False
        self.current_id = 0
        self.current_book = self.selected = self._thread = self.source = None

    def setQuery(self, query):
        self.query = query

    def searchCompleted(self):
        if self.filter_enabled:
            self.model.loadFilters()
        elif self.completed_slot:
            self.source = self.model.source[:]
            self.completed_slot(len(self.source))
        else:
            if self.boxes:
                self.source = self.model.source
                self.boxes.searchButton.setEnabled(True)
                count = len(self.model.source)
                label = QCoreApplication.translate('MainWindow', 'No resuts') if count == 0 else QCoreApplication.translate('MainWindow', 'Results Count: ') + arabize((f"{count}"))
                self.boxes.setResultsCount(label)
            if self.current_id != 0 and self.model.source:
                self.selected or self.model.firstRow.emit(0)

    def start(self):
        self.model.source_filter = defaultdict(set)
        self.model.clear()
        self.model.beginResetModel()
        self.model.endResetModel()
        if self.boxes:
            self.boxes.showProgress()
            self.boxes.searchButton.setEnabled(False)
        elif self.query.results:
            try:
                func = self.query.executeBiblio if self.query.type == QueryType.BIBLIO else self.query.execute
                for result in func():
                    self.insertResults(result)

                if self.filter_enabled:
                    self.model.loadFilters()
            except:
                traceback.print_exc()
                self.searchError()
                return
            else:
                self.searchCompleted()
        else:
            self._thread = SearcherThread(self)
            self._registerThread(self._thread)
            thread = self._thread
            self._thread.resultEmerged.connect(self.insertResults, Qt.QueuedConnection)
            self._thread.searchCompleted.connect(self.searchCompleted)
            self._thread.searchError.connect(self.searchError)
            self._thread.filteredBook.connect(self.filteredBook)
            self._thread.finished.connect(lambda thread=thread: self._unregisterThread(thread))
            self._thread.start()

    def abort(self):
        if self._thread:
            self._thread.abort()
            self._thread.requestInterruption()

    def stop(self, wait_ms=None):
        if not self._thread:
            return
        self.abort()
        if self._thread.isRunning():
            self._thread.wait(-1 if wait_ms is None else wait_ms)

    def isRunning(self):
        if self._thread:
            return self._thread.isRunning()
        return False

    def insertResults(self, result_list):
        if self.boxes:
            self.boxes.setResultsCount('')
        self.model.receiveResults(result_list)
        if not self._first_result_fired:
            if self.model.source:
                self._first_result_fired = True
                if self.first_result_slot:
                    self.first_result_slot()

    def constructViewer(self, side_view=False):
        if side_view:
            self.model = SearchBookModel(self)
        else:
            if self.query.type == QueryType.PAGES:
                self.model = PagesResultsModel(self)
            else:
                if self.query.type == QueryType.QURAN:
                    self.model = QuranResultsModel(self)
                else:
                    if self.query.type == QueryType.BIBLIO:
                        self.model = InfoResultsModel(self)
                    else:
                        if self.query.type == QueryType.TITLES:
                            self.model = TitleResultsModel(self)
        self.view.setModel(self.model)
        self.model.adjustView()
        return self.view

    def searchError(self):
        customMessage(QCoreApplication.translate('MainWindow', 'Error'), QCoreApplication.translate('MainWindow', 'Error Occured') + '\n' + QCoreApplication.translate('MainWindow', 'Try change the entries'))

    def filteredBook(self, book_id):
        if self.filter_slot:
            self.filter_slot(book_id)

    @classmethod
    def _registerThread(cls, thread):
        with cls._threads_lock:
            cls._active_threads.add(thread)

    @classmethod
    def _unregisterThread(cls, thread):
        with cls._threads_lock:
            cls._active_threads.discard(thread)

    @classmethod
    def stopAll(cls, wait_ms=None):
        with cls._threads_lock:
            threads = list(cls._active_threads)
        for thread in threads:
            try:
                thread.abort()
                thread.requestInterruption()
            except:
                pass

        for thread in threads:
            try:
                if thread.isRunning():
                    thread.wait(-1 if wait_ms is None else wait_ms)
            except:
                pass


class SearcherThread(QThread):
    resultEmerged = Signal(list)
    searchCompleted = Signal()
    searchError = Signal()
    filteredBook = Signal(int)

    def __init__(self, searcher):
        super().__init__()
        self.searcher = searcher
        self.abortRequest = False

    def run(self):
        from engine import Index, is_shutdown_exception
        any_result = False
        try:
            func = self.searcher.query.executeBiblio if self.searcher.query.type == QueryType.BIBLIO else self.searcher.query.execute
            for result in func():
                if self.abortRequest or self.isInterruptionRequested() or Index.is_shutting_down():
                    return
                if result:
                    any_result = True
                    self.resultEmerged.emit(result)
                    if self.searcher.filter_enabled and self.searcher.query.type in (QueryType.PAGES, QueryType.TITLES):
                        try:
                            self.filteredBook.emit(int((f"{result[0]}").split('-', 1)[0]))
                        except:
                            pass

                if self.abortRequest or self.isInterruptionRequested() or Index.is_shutting_down():
                    return

        except Exception as error:
            try:
                if is_shutdown_exception(error):
                    return
                traceback.print_exc()
                self.searchError.emit()
                return
            finally:
                error = None
                del error

        self.searchCompleted.emit()

    def abort(self):
        self.abortRequest = True


class SearchView(TableView):

    def __init__(self, searcher, no_focus=None):
        super().__init__()
        self.searcher = searcher
        self.no_focus = no_focus

    def firstRow(self, row):
        super().firstRow(row)
        if not self.no_focus:
            self.setFocus()

    def displayRow(self, row, keep_position=None, forced=None):
        self.searcher.model.displayResult(row)

    def fullDisplay(self, model_index):
        try:
            self.searcher.model.fullDisplay(model_index)
        except:
            pass

    def enterPressed(self):
        if Settings.getValue('instant_display_result'):
            self.fullDisplay(self.currentIndex())
        else:
            self.displayRow(self.currentIndex().row())

    def displayBookPressed(self):
        self.fullDisplay(self.currentIndex())


class BaseSearchModel(CachedTableModel):

    def __init__(self, searcher):
        self.searcher = searcher
        self._scope_set = None
        super().__init__(headers=(self.setHeaders()))
        self.valve = defaultdict(int)
        self.firstRow.connect(self.searcher.view.firstRow)

    def setHeaderWidths(self, header_widths, total=None):
        if not total:
            total = 1905
        view = self.searcher.view
        unhideSelection(view)
        view.setDimensions(total, header_widths)

    def setHeaders(self):
        pass

    def fullDisplay(self, _):
        pass


class QuranResultsModel(BaseSearchModel):

    def __init__(self, searcher):
        super().__init__(searcher)

    def setHeaders(self):
        return [
         QCoreApplication.translate('MainWindow', 'No.'),
         QCoreApplication.translate('MainWindow', 'Text'),
         QCoreApplication.translate('MainWindow', 'Sora'),
         QCoreApplication.translate('MainWindow', 'Aya'),
         QCoreApplication.translate('MainWindow', 'Page')]

    def adjustView(self):
        view = self.searcher.view
        font = QtFont(Settings.getValue('font_search_tables'))
        view.setFont(font)
        view.horizontalHeader().setFont(font)
        view.setItemDelegateForColumn(1, HtmlDelegate(font, False))
        view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        fitRow(view)
        view.verticalHeader().hide()
        self.setHeaderWidths([40, 0, 80, 40, 40], 1280)

    def getData(self, row_column_role):
        row, column, role = row_column_role
        aya_id = int(self.source[row])
        if role == Qt.DisplayRole:
            sora, aya = quraninfo.posFromAya(aya_id)
            if column == 0:
                return arabize((f"{row + 1}"))
            if column == 1:
                return self.searcher.query.snippet(f"{aya_id}")
            if column == 2:
                return quraninfo.getSoraNames()[sora - 1]
            if column == 3:
                return arabize((f"{aya}"))
            if column == 4:
                return arabize((f"{quraninfo.pageFromAya(aya_id)}"))
        elif role == Qt.ToolTipRole:
            if column == 1:
                return tipH(self.searcher.query.snippet((f"{aya_id}"), fragment_size=500))

    def receiveResults(self, result_list):
        self.insertRows(result_list)

    def displayResult(self, row):
        self.searcher.display_slot(self.source[row])


class InfoResultsModel(BaseSearchModel):

    def __init__(self, searcher):
        super().__init__(searcher)
        self.icons = {'a':Icon.icon(':/icons/authors.png'),  'h':Icon.icon(':/icons/hint.png'), 
         'b':Icon.icon(':/icons/betaka.png')}

    def setHeaders(self):
        return [
         QCoreApplication.translate('MainWindow', 'No.'),
         QCoreApplication.translate('MainWindow', 'Element'),
         QCoreApplication.translate('MainWindow', 'Text')]

    def adjustView(self):
        view = self.searcher.view
        font = QtFont(Settings.getValue('font_search_tables'))
        view.setFont(font)
        view.horizontalHeader().setFont(font)
        view.setItemDelegateForColumn(2, HtmlDelegate(font, False))
        view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        fitRow(view)
        view.verticalHeader().hide()
        self.setHeaderWidths([45, 300, 0], 900)

    def getData(self, row_column_role):
        row, column, role = row_column_role
        row_type, row_id = self.source[row][0], self.source[row][1]
        if role == Qt.DisplayRole:
            if column == 0:
                return arabize((f"{row + 1}"))
            if column == 1:
                if row_type == 'a':
                    return AuthorCache.authorName(row_id)
                    return BookCache.abstractName(row_id)
                elif column == 2:
                    return self.searcher.query.biblioSnippet(row_type, row_id, fragment_size=70)
            else:
                pass
        if role == Qt.ToolTipRole:
            if column == 1:
                if row_type == 'a':
                    return AuthorCache.authorName(row_id)
                return BookCache.abstractName(row_id)
            else:
                if column == 2:
                    if row_type == 'b':
                        return conditioned(dbmanager.CoreDb().bookBetaka(row_id, False, search_info=(self.searcher.query.info()), text_only=True))
                    snippet = self.searcher.query.biblioSnippet(row_type, row_id, fragment_size=500, multiline=True)
                    if row_type == 'a':
                        return tipAuthor(snippet, AuthorCache.authorName(row_id))
                    return tipHint(snippet)
        else:
            if role == Qt.DecorationRole:
                if column == 1:
                    return self.icons[row_type]

    def fullDisplay(self, model_index):
        row = model_index.row()
        if self.source[row][0] != 'a':
            Across.main_window.showBook(int(self.source[row][1]))

    def receiveResults(self, result_list):
        self.insertRows(result_list)

    def displayResult(self, row):
        self.searcher.display_slot(self.source[row])


class ScopeResultsModel(BaseSearchModel):

    def __init__(self, searcher):
        super().__init__(searcher)

    def _adjustView(self, delegate_index, header_width_list):
        view = self.searcher.view
        font = QtFont(Settings.getValue('font_search_tables'))
        view.setFont(font)
        view.horizontalHeader().setFont(font)
        view.setItemDelegateForColumn(delegate_index, HtmlDelegate(font, False))
        view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        fitRow(view)
        view.verticalHeader().hide()
        self.setHeaderWidths(header_width_list)

    def deleteResults(self, results):
        for book_id, page_id in results:
            self.valve[book_id] -= 1

        self.searcher.source = [item for item in self.searcher.source if item not in results]
        self.loadFilters(new_count=(len(self.searcher.source)))

    def loadFilters(self, new_count=None):
        from collections import defaultdict
        from dbmanager import CoreDb
        core_db = CoreDb()
        valve_items = list(self.valve.items())
        categories_result_count = defaultdict(int)
        centuries_result_count = defaultdict(int)
        _categories = defaultdict(set)
        _centuries = defaultdict(set)
        self.categories = []
        self.centuries = []
        for book_id, result_count in valve_items:
            category = core_db.bookCategory(book_id)
            century = core_db.bookCentury(book_id)
            _categories[category].add(book_id)
            _centuries[century].add(book_id)
            categories_result_count[category] += result_count
            centuries_result_count[century] += result_count

        count = arabize((f"{new_count or len(self.source)}"))
        categories = core_db.arrangeCategories(list(_categories.keys()))
        if not new_count:
            count_categories = len(categories_result_count)
            self.searcher.categories_model = QStandardItemModel(count_categories + 1, 2)
            text = QStandardItem(QCoreApplication.translate('MainWindow', 'All Categories'))
            self.searcher.categories_model.setItem(0, 0, text)
            count_centuries = len(centuries_result_count)
            text = QStandardItem(QCoreApplication.translate('MainWindow', 'All Centuries'))
            self.searcher.centuries_model = QStandardItemModel(count_centuries + 1, 2)
            self.searcher.centuries_model.setItem(0, 0, text)
        number = QStandardItem(count)
        number.setSelectable(False)
        number.setTextAlignment(Qt.AlignCenter)
        self.searcher.categories_model.setItem(0, 1, number)
        number = QStandardItem(count)
        number.setSelectable(False)
        number.setTextAlignment(Qt.AlignCenter)
        self.searcher.centuries_model.setItem(0, 1, number)
        c = 0
        for category_id, category_name in categories:
            c += 1
            if not new_count:
                text = QStandardItem(category_name)
                self.searcher.categories_model.setItem(c, 0, text)
            number = QStandardItem(arabize((f"{categories_result_count[category_id]}")))
            number.setSelectable(False)
            number.setTextAlignment(Qt.AlignCenter)
            self.searcher.categories_model.setItem(c, 1, number)
            self.categories.append(_categories[category_id])

        c = 0
        for century in sorted(centuries_result_count):
            c += 1
            if not new_count:
                text = QStandardItem('{} {}'.format(QCoreApplication.translate('MainWindow', 'Century:'), formalize(century)))
                self.searcher.centuries_model.setItem(c, 0, text)
            number = QStandardItem(arabize((f"{centuries_result_count[century]}")))
            number.setSelectable(False)
            number.setTextAlignment(Qt.AlignCenter)
            self.searcher.centuries_model.setItem(c, 1, number)
            self.centuries.append(_centuries[century])

    def groupSelected(self, row):
        if row == 0:
            self.unFilter()
        else:
            self.setFilter(self.categories[row - 1])

    def centurySelected(self, row):
        if row == 0:
            self.unFilter()
        else:
            self.setFilter(self.centuries[row - 1])

    def setFilter(self, filter):
        new_source = [row for row in self.searcher.source if row[0] in filter]
        if new_source:
            current = self.source[self.searcher.view.currentIndex().row()]
            if current in new_source:
                self.setSource(new_source, no_select=True)
                row = new_source.index(current)
                specialSelectRow(self.searcher.view, row)
            else:
                self.setSource(new_source)

    def unFilter(self):
        if self.searcher.source:
            current = self.source[self.searcher.view.currentIndex().row()]
            self.setSource((self.searcher.source), no_select=True)
            row = self.source.index(current)
            specialSelectRow(self.searcher.view, row)

    def receiveResults(self, pulse):
        source = []
        for line in pulse:
            pieces = line.split('-')
            first, second = int(pieces[0]), int(pieces[1])
            self.valve[first] += 1
            source.append((first, second))

        if source:
            self.insertRows(source)

    def fullDisplay(self, model_index):
        row = model_index.row()
        res = (self.source[row][0], self.source[row][1], self.searcher.query)
        Across.main_window.showBook((self.source[row][0]), search_res=res)

    def displayResult(self, row):
        self.searcher.display_slot((self.source[row][0], self.source[row][1], self.searcher.query))


class TitleResultsModel(ScopeResultsModel):

    def __init__(self, searcher):
        super().__init__(searcher)

    def setHeaders(self):
        return [
         QCoreApplication.translate('MainWindow', 'No.'),
         QCoreApplication.translate('MainWindow', 'Book'),
         QCoreApplication.translate('MainWindow', 'Text'),
         QCoreApplication.translate('MainWindow', 'Page')]

    def adjustView(self):
        self._adjustView(2, [48, 240, 0, 80])

    def getData(self, row_column_role):
        row, column, role = row_column_role
        book_id = self.source[row][0]
        title_id = self.source[row][1]
        if role == Qt.DisplayRole:
            if column == 0:
                return arabize((f"{row + 1}"))
                if column == 1:
                    return BookCache.abstractName(book_id)
                if column == 2:
                    return self.searcher.query.snippet(f"{book_id}-{title_id}")
                if column == 3:
                    return arabize(dbmanager.BookDb(book_id).getTitlePageNumber(title_id))
            else:
                pass
        if role == Qt.ToolTipRole:
            if column == 1:
                return conditioned(dbmanager.CoreDb().bookBetaka(book_id, True, truncated=True))
            if column == 2:
                return tipH(self.searcher.query.snippet(f"{book_id}-{title_id}", fragment_size=500))
            if column == 3:
                return tip(arabize(dbmanager.BookDb(book_id).getTitlePageNumber(title_id)))
        elif role == Qt.DecorationRole:
            if column == 1:
                return BookCache.bookIcon(book_id)


class PagesResultsModel(ScopeResultsModel):

    def __init__(self, searcher):
        super().__init__(searcher)

    def setHeaders(self):
        return [
         QCoreApplication.translate('MainWindow', 'No.'),
         QCoreApplication.translate('MainWindow', 'Book'),
         QCoreApplication.translate('MainWindow', 'Text'),
         QCoreApplication.translate('MainWindow', 'Chapter'),
         QCoreApplication.translate('MainWindow', 'Page')]

    def adjustView(self):
        self._adjustView(2, [48, 250, 0, 260, 80])

    def getData(self, row_column_role):
        row, column, role = row_column_role
        book_id, page_id = self.source[row]
        if role == Qt.DisplayRole:
            if column == 0:
                return arabize((f"{row + 1}"))
                if column == 1:
                    return BookCache.abstractName(book_id)
                if column == 2:
                    return self.searcher.query.snippet(f"{book_id}-{page_id}")
                if column == 3:
                    return dbmanager.BookDb(book_id).getTitle(page_id)
                if column == 4:
                    return arabize(dbmanager.BookDb(book_id).getPageNumber(page_id))
            else:
                pass
        if role == Qt.ToolTipRole:
            if column == 1:
                return conditioned(dbmanager.CoreDb().bookBetaka(book_id, True, truncated=True))
            if column == 2:
                return tipH(self.searcher.query.snippet(f"{book_id}-{page_id}", fragment_size=500, multiline=True))
            if column == 3:
                return tip(dbmanager.BookDb(book_id).getTitle(page_id))
            if column == 4:
                return tip(arabize(dbmanager.BookDb(book_id).getPageNumber(page_id)))
        elif role == Qt.DecorationRole:
            if column == 1:
                return BookCache.bookIcon(book_id)


class SearchBookModel(BaseSearchModel):

    def __init__(self, searcher):
        super().__init__(searcher)

    def setHeaders(self):
        return [
         '']

    def adjustView(self):
        view = self.searcher.view
        font = QtFont(Settings.getValue('font_search_tables'))
        view.setFont(font)
        view.horizontalHeader().setFont(font)
        view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        view.horizontalHeader().hide()
        row_height = QFontMetrics(font).height() * 3 + Across.row_space
        view.setItemDelegateForColumn(0, HtmlDelegate(font, True))
        view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        view.verticalHeader().setDefaultSectionSize(row_height)
        view.verticalHeader().hide()
        self.setHeaderWidths([0])

    def receiveResults(self, pulse):
        source = []
        for line in pulse:
            pieces = line.split('-')
            first = int(pieces[0])
            second = int(pieces[1])
            self.valve[first] += 1
            source.append((first, second))

        if source:
            self.insertRows(source)

    def insertRows(self, value, parent=QModelIndex()):
        position = self.rowCount()
        added_count = len(value)
        self.beginInsertRows(parent, position, position + added_count - 1)
        self.source += value
        self.endInsertRows()
        if self.searcher.current_id:
            if not self.searcher.selected:
                for item in value:
                    if item[0] == self.searcher.current_book:
                        if item[1] > self.searcher.current_id:
                            self.searcher.selected = True
                            self.firstRow.emit(position)
                            return
                        position += 1

    def getData(self, row_column_role):
        row, column, role = row_column_role
        book_id, page_id = self.source[row]
        if role == Qt.DisplayRole:
            if column == 0:
                return f"\x01{arabize(row + 1)} -\x02 " + self.searcher.query.snippet(f"{book_id}-{page_id}")
        elif role == Qt.ToolTipRole:
            if column == 0:
                return tipH(self.searcher.query.snippet(f"{book_id}-{page_id}", fragment_size=500, multiline=True))

    def displayResult(self, row):
        self.searcher.display_slot((self.source[row][0], self.source[row][1], self.searcher.query))


def formalize(century):
    if century > 999:
        return QCoreApplication.translate('MainWindow', 'Contemporary')
    return arabize((f"{century}"))