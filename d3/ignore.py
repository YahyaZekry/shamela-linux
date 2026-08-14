# decompyle3 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: ignore.py
from qtpy.QtCore import Qt, QSize, QAbstractTableModel, Signal
from qtpy.QtWidgets import QWidget, QStackedWidget, QToolBar, QButtonGroup, QAbstractItemView
from across import Across
from cache import BookCache
from customs import ensureChecked, findInList, TimedLineEdit, customToolButton, customLayout, BooksTable, standardFont
from dbmanager import CoreDb
from engine import filterBooks
from textmanager import treatSearch, arabize, conditioned

class RichScope(QWidget):

    def __init__(self, plain_scope, select_widget):
        super().__init__()
        self.select_widget = select_widget
        self.pages = QStackedWidget()
        self.scope = plain_scope
        self.scope.ignoreChanged.connect(self.ignoreChanged)
        self.scope.scopeChanged.connect(self.scopeChanged)
        self.ignore = None
        self.toolbar = QToolBar(self)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.setIconSize(QSize(16, 16))
        self.group = QButtonGroup()
        if select_widget.context == 2:
            texts = (
             self.tr('Search Scope'), self.tr('Ignore List'))
            icons = (':/icons/search.png', ':/icons/ignore.png')
        else:
            texts = (
             self.tr('Download List'), self.tr('Ignore List'))
            icons = (':/icons/download.png', ':/icons/ignore.png')
        slots = (
         self.showPlain, self.showIgnore)
        for i in range(2):
            button = customToolButton(text=(texts[i]), icon=(icons[i]), slot=(slots[i]), checkable=True, text_beside=True)
            self.toolbar.addWidget(button)
            self.group.addButton(button)
            if i == 0:
                self.plainButton = button
            else:
                self.ignoreButton = button

        self.pages.addWidget(self.scope)
        self.ignoreChanged(True)
        self.setLayout(customLayout(True, [self.toolbar, self.pages], margins=0))

    def scopeChanged(self, book_set):
        text = self.tr('Search Scope') if self.select_widget.context == 2 else self.tr('Download List')
        if book_set:
            self.plainButton.setText(text + ' (' + arabize((f"{len(book_set)}")) + ')')
        else:
            self.plainButton.setText(text)

    def ignoreChanged(self, first_run=None):
        count, ignored_count = CoreDb().newCount(self.select_widget.context)
        if first_run:
            if count == ignored_count:
                self.showIgnore()
                self.ignoreButton.setChecked(True)
            else:
                self.showPlain()
                self.plainButton.setChecked(True)
        if ignored_count == 0:
            self.ignoreButton.setText(self.tr('Ignore List'))
            self.showPlain()
            self.toolbar.setVisible(False)
        else:
            self.ignoreButton.setText(self.tr('Ignore List') + ' (' + arabize((f"{ignored_count}")) + ')')
            self.toolbar.setVisible(True)
        if not Across.no_update:
            Across.main_window.update_widget.updateCount()

    def showIgnore(self):
        if not self.ignore:
            self.ignore = IgnoreWidget(self.select_widget, self.scope.ignoreChanged, self.ignoreChanged)
            self.pages.addWidget(self.ignore)
        self.pages.setCurrentWidget(self.ignore)
        ensureChecked(self.ignoreButton)

    def showPlain(self):
        self.pages.setCurrentWidget(self.scope)
        ensureChecked(self.plainButton)


class IgnoreWidget(QWidget):

    def __init__(self, select_widget, connected_signal, tab_slot):
        super().__init__()
        self.select_widget = select_widget
        self.context = select_widget.context
        self.model = IgnoreModel(self.context)
        self.view = IgnoreView(self.model)
        connected_signal.connect(self.sourceChanged)
        self.tab_slot = tab_slot
        self.delete_button = customToolButton(':/icons/delete_file.png', (self.tr('Exclude Books From the Ignore List')), text_beside=True,
          slot=(self.deleteSelected))
        self.clear_button = customToolButton(':/icons/clear.png', (self.tr('Clear the List')), slot=(self.emptyList))
        layout = customLayout(False, [self.delete_button, 0, self.clear_button], margins=[0, 2, 0, 2])
        self.text = ''
        self.filter_text = TimedLineEdit(focus_list=(self.view))
        self.filter_text.textEdited.connect(lambda: self.updateLine(self.filter_text.text())
)
        self.view.find_line = self.filter_text
        self.complete_source = CoreDb().ignoreList(self.context)
        self.bookChanged()
        self.setLayout(customLayout(True, [self.filter_text, self.view, 2, layout]))

    def updateLine(self, text):
        self.text = treatSearch(text)
        self.bookChanged()

    def deleteSelected(self):
        selected_set = set()
        for index in self.view.selectedIndexes():
            selected_set.add(self.model.source[index.row()])

        CoreDb().addToIgnore(self.context, selected_set, False)
        self.sourceChanged()

    def emptyList(self):
        CoreDb().addToIgnore(self.context, set(self.model.source), False)
        self.sourceChanged()

    def sourceChanged(self):
        self.complete_source = CoreDb().ignoreList(self.context)
        self.bookChanged()
        self.select_widget.reinstall()
        self.tab_slot()

    def bookChanged(self):
        value = None
        selected_row = self.view.currentIndex().row()
        if selected_row > -1:
            value = self.model.source[selected_row]
        if self.text.strip():
            self.model.source = filterBooks(self.text, self.complete_source, None)
        else:
            self.model.source = self.complete_source
        self.model.beginResetModel()
        self.model.endResetModel()
        if self.model.source:
            if value:
                found = findInList(self.model.source, value)
                if found == -1:
                    l = len(self.model.source)
                    if selected_row >= l:
                        selected_row = l - 1
                else:
                    selected_row = found
            else:
                selected_row = 0
            m_index = self.model.index(selected_row, 0)
            self.view.setCurrentIndex(m_index)
            self.view.scrollTo(m_index)
        self.buttonStatus()

    def buttonStatus(self):
        books_number = len(self.model.source)
        enabled = books_number != 0
        self.delete_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)


class IgnoreView(BooksTable):

    def __init__(self, model):
        super().__init__(model)
        standardFont(self)
        self.simulateList()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)


class IgnoreModel(QAbstractTableModel):
    firstRow = Signal(int)

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.source = []
        self.context = context

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 1

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.source)

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if int_role == Qt.DisplayRole:
            if Qt_Orientation == Qt.Horizontal:
                return ''

    def data(self, QModelIndex, int_role=None):
        if self.source:
            if QModelIndex.isValid():
                book_id = self.source[QModelIndex.row()]
                if int_role == Qt.DisplayRole:
                    return BookCache.bookName(book_id)
                if int_role == Qt.ToolTipRole:
                    return conditioned(CoreDb().bookBetaka(book_id, True, truncated=True))
                if int_role == Qt.DecorationRole:
                    return BookCache.bookIcon(book_id, context=(self.context))