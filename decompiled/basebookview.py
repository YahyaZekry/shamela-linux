# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: basebookview.py
from qtpy.QtCore import Qt, QAbstractTableModel, Signal, QSize
from qtpy.QtWidgets import QWidget, QListWidget, QHeaderView, QStackedWidget, QToolBar, QButtonGroup
from cache import BookCache
from across import Across
from customs import listFit, QtFont, customSplitter, standardFont, flexibleBrowser, customLayout, TimedLineEdit, customToolButton, BooksTable, ReadersBrowser, StandardBrowser, NVDA, CACHED_BRUSH_DARK_GRAY, CACHED_BRUSH_BLUE, CACHED_BRUSH_LIGHT_BLUE
from dbmanager import CoreDb
from engine import filterBooks
from theme import Icon
from settings import Settings
from textmanager import treatSearch, arabize, conditioned

def booklistColors():
    current = CACHED_BRUSH_LIGHT_BLUE if Across.active_theme == 'dark' else CACHED_BRUSH_BLUE
    return (None, CACHED_BRUSH_DARK_GRAY, current)


def flexibleBrowserClass():
    if NVDA.isRunning():
        return ReadersBrowser
    return StandardBrowser


class Widget(QWidget):

    def __init__(self, panel=None, is_author=None):
        super().__init__()
        self.author = is_author
        self.panel = panel
        self.betakaBrowser = EmbeddedInfo(author=(self.author))
        self.model = Model(self)
        self.view = View(self.model, panel, self.betakaBrowser)
        self.filter_text = TimedLineEdit(search_slot=(self.updateLine), focus_list=(self.view))
        self.filter_text.setPlaceholderText(self.tr('Enter at least three letters to search'))
        self.view.find_line = self.filter_text
        self.view.selectionModel().selectionChanged.connect(self.selectionChanged)
        self.betakaBrowser.setVisible(False)
        self.showBetakaButton = customToolButton(':/icons/betaka.png', self.tr('Book Information'))
        self.showBetakaButton.setCheckable(True)
        self.showBetakaButton.setChecked(False)
        self.showBetakaButton.clicked.connect(lambda: self.toggleBetaka(self.showBetakaButton.isChecked()))
        lay = customLayout(False, [self.filter_text, self.showBetakaButton])
        lay = customLayout(True, [lay, self.view], margins=0)
        lay = customSplitter(True, lay, self.betakaBrowser, 66)
        self.setLayout(customLayout(True, [lay]))

    def toggleBetaka(self, value):
        self.betakaBrowser.setVisible(value)
        if value:
            self.view.displayRow(forced=True)

    def selectionChanged(self):
        self.view.displayRow()

    def endResetModel(self):
        self.model.beginResetModel()
        self.model.endResetModel()

    def updateLine(self):
        search_text = treatSearch(self.filter_text.text())
        if len(search_text) < 3:
            search_text = ''
        self.model.filter_text = search_text
        self.model.updateFilter()

    def setSource(self, book_id, source, online_set):
        self.filter_text.blockSignals(True)
        self.filter_text.setText('')
        self.filter_text.blockSignals(False)
        self.model.filter_text = ''
        self.model.setSource(book_id, source, online_set)


class View(BooksTable):
    go = Signal(int)

    def __init__(self, model, panel, betakaBrowser):
        super().__init__(model)
        standardFont(self)
        self.betakaBrowser = betakaBrowser
        self.current_betaka = None
        self.setShowGrid(False)
        self.horizontalHeader().hide()
        if panel:
            self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.setColumnWidth(0, 40)
        else:
            self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def displayRow(self, row=None, keep_position=None, forced=None):
        if self.model().source:
            if row is None:
                row = self.currentIndex().row()
            if row == -1:
                self.clearBetaka()
                return
            if row is not None:
                book_id = self.model().source[row]
                if book_id != self.current_betaka:
                    self.go.emit(book_id)
                    if not self.betakaBrowser or self.betakaBrowser.isVisible() or forced:
                        self.betakaBrowser.setBook(book_id)
                        self.current_betaka = book_id
        else:
            self.clearBetaka()

    def clearBetaka(self):
        if self.betakaBrowser:
            self.betakaBrowser.setBook(None)
            self.current_betaka = None


class Model(QAbstractTableModel):
    firstRow = Signal(int)

    def __init__(self, books_widget, parent=None):
        super().__init__(parent)
        self.source = []
        self.book_id = None
        self.complete_source = []
        self.filter_text = ''
        self.books_widget = books_widget
        self.func = BookCache.abstractName if self.books_widget.author else BookCache.bookName
        self.name_column, self.number_column, self.column_count = (1, 0, 2) if self.books_widget.panel else (0,
                                                                                                             None,
                                                                                                             1)
        self.offline, self.online, self.current = booklistColors()

    def setSource(self, book_id, source, online_set):
        self.complete_source = source
        self.online_set = online_set
        self.book_id = book_id
        self.updateFilter()

    def updateFilter(self):
        if self.filter_text:
            self.source = filterBooks(self.filter_text, self.complete_source)
        else:
            self.source = self.complete_source
        self.beginResetModel()
        self.endResetModel()
        if self.source:
            self.books_widget.view.setCurrentIndex(self.index(0, 0))
            self.books_widget.view.displayRow(0)
        else:
            self.books_widget.view.clearBetaka()

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.source)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            book_id = self.source[row]
            if QModelIndex.column() == self.name_column:
                if int_role == Qt.DisplayRole:
                    return self.func(book_id)
                if int_role == Qt.ForegroundRole:
                    if book_id == self.book_id:
                        return self.current
                    if book_id in self.online_set:
                        return self.online
                    return self.offline
            else:
                if int_role == Qt.ToolTipRole:
                    return conditioned(CoreDb().bookBetaka(book_id, cover=True, truncated=True))
                if int_role == Qt.DecorationRole:
                    return BookCache.bookIcon(book_id)
                else:
                    if QModelIndex.column() == self.number_column:
                        if int_role == Qt.DisplayRole:
                            return arabize((f"{row + 1}"))


class EmbeddedInfo(QWidget):

    def __init__(self, parent=None, author=None):
        super().__init__(parent)
        self.pages = QStackedWidget()
        self.author = self.betaka = self.book_id = self.bookAction = None
        if author:
            self.setLayout(customLayout(True, [self.pages], margins=0))
        else:
            toolbar = QToolBar(self)
            toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            toolbar.setIconSize(QSize(16, 16))
            self.group = QButtonGroup()
            texts = (
             self.tr('Book'), self.tr('Author'))
            icons = (':/icons/book.png', ':/icons/authors.png')
            slots = (self.showBetaka, self.showAuthor)
            for i in range(2):
                action = customToolButton(text=(texts[i]), icon=(icons[i]), text_beside=True, slot=(slots[i]), checkable=True)
                toolbar.addWidget(action)
                self.group.addButton(action)
                if i == 0:
                    action.setChecked(True)
                    self.bookAction = action

            self.setLayout(customLayout(True, [toolbar, self.pages], margins=0))
            self.pages.currentChanged.connect(self.viewChanged)
        self.showBetaka()

    def setBook(self, book_id):
        self.book_id = book_id
        if self.bookAction:
            if self.book_id:
                self.bookAction.setIcon(BookCache.bookIcon(self.book_id))
            else:
                self.bookAction.setIcon(Icon.icon(':/icons/book.png'))
        self.viewChanged()

    def viewChanged(self):
        self.pages.currentWidget().setBook(self.book_id)

    def showBetaka(self):
        if not self.betaka:
            self.betaka = Betaka()
            self.pages.addWidget(self.betaka)
        self.pages.setCurrentWidget(self.betaka)
        self.setFocus()

    def showAuthor(self):
        if not self.author:
            self.author = Author('font_betaka')
            self.pages.addWidget(self.author)
        self.pages.setCurrentWidget(self.author)
        self.setFocus()


class Betaka(flexibleBrowserClass()):

    def __init__(self):
        super().__init__()
        self.book_id = None

    def setBook(self, book_id):
        if book_id == self.book_id:
            return
        else:
            self.book_id = book_id
            if self.book_id is None:
                self.setHtml('')
            else:
                self.setHtml(CoreDb().bookBetaka(self.book_id, False))


class Author(QWidget):

    def __init__(self, font=None):
        super().__init__()
        self.authorListWidget = QListWidget()
        self.authorListWidget.setFont(QtFont(Settings.getValue('font_standard')))
        self.display_font = font
        self.authorListWidget.currentItemChanged.connect(self.displayListItem)
        self.book_id = None
        self.authorBiblo = flexibleBrowser()
        self.books = Widget(is_author=True)
        self.author_list = []
        lay = customSplitter(True, self.authorBiblo, self.books, 65)
        self.setLayout(customLayout(True, [self.authorListWidget, lay], margins=0))

    def displayListItem(self):
        self.showAuthor(self.author_list[self.authorListWidget.currentRow()])

    def setBook(self, book_id):
        if book_id == self.book_id:
            return
            self.book_id = book_id
            if self.book_id is None:
                self.authorListWidget.setVisible(False)
                self.authorBiblo.setHtml('')
                self.books.setSource(0, [], set())
                return
            self.author_list, author_dict, books, online_set = CoreDb().inAuthor(book_id)
            if len(self.author_list) == 1:
                self.authorListWidget.setVisible(False)
                self.showAuthor(self.author_list[0], books, online_set)
        else:
            self.authorListWidget.blockSignals(True)
            self.authorListWidget.clear()
            self.authorListWidget.addItems([author_dict[author] for author in self.author_list])
            listFit(self.authorListWidget)
            self.authorListWidget.blockSignals(False)
            self.authorListWidget.setCurrentRow(0)
            self.authorListWidget.setVisible(True)

    def showAuthor(self, author_id, books=None, online_set=None):
        if not books:
            books, online_set = CoreDb().allAuthorBooks(author_id)
        else:
            author_biblo = CoreDb().authorBiography(author_id)
            if author_biblo:
                self.authorBiblo.setHtml(author_biblo)
                self.authorBiblo.setVisible(True)
            else:
                self.authorBiblo.setVisible(False)
                self.authorBiblo.setHtml(author_biblo)
        self.books.setSource(self.book_id, books, online_set)