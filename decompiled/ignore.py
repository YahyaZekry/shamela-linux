# uncompyle6 version 3.9.0
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
        elif ignored_count == 0:
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
        self.filter_text.textEdited.connect(lambda: self.updateLine(self.filter_text.text()))
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

    def bookChanged--- This code section failed: ---

 L. 135         0  LOAD_CONST               None
                2  STORE_FAST               'value'

 L. 136         4  LOAD_FAST                'self'
                6  LOAD_ATTR                view
                8  LOAD_METHOD              currentIndex
               10  CALL_METHOD_0         0  '0 positional arguments'
               12  LOAD_METHOD              row
               14  CALL_METHOD_0         0  '0 positional arguments'
               16  STORE_FAST               'selected_row'

 L. 137        18  LOAD_FAST                'selected_row'
               20  LOAD_CONST               -1
               22  COMPARE_OP               >
               24  POP_JUMP_IF_FALSE    38  'to 38'

 L. 137        26  LOAD_FAST                'self'
               28  LOAD_ATTR                model
               30  LOAD_ATTR                source
               32  LOAD_FAST                'selected_row'
               34  BINARY_SUBSCR    
               36  STORE_FAST               'value'
             38_0  COME_FROM            24  '24'

 L. 139        38  LOAD_FAST                'self'
               40  LOAD_ATTR                text
               42  LOAD_METHOD              strip
               44  CALL_METHOD_0         0  '0 positional arguments'
               46  POP_JUMP_IF_FALSE    70  'to 70'

 L. 140        48  LOAD_GLOBAL              filterBooks
               50  LOAD_FAST                'self'
               52  LOAD_ATTR                text
               54  LOAD_FAST                'self'
               56  LOAD_ATTR                complete_source
               58  LOAD_CONST               None
               60  CALL_FUNCTION_3       3  '3 positional arguments'
               62  LOAD_FAST                'self'
               64  LOAD_ATTR                model
               66  STORE_ATTR               source
               68  JUMP_FORWARD         80  'to 80'
             70_0  COME_FROM            46  '46'

 L. 142        70  LOAD_FAST                'self'
               72  LOAD_ATTR                complete_source
               74  LOAD_FAST                'self'
               76  LOAD_ATTR                model
               78  STORE_ATTR               source
             80_0  COME_FROM            68  '68'

 L. 144        80  LOAD_FAST                'self'
               82  LOAD_ATTR                model
               84  LOAD_METHOD              beginResetModel
               86  CALL_METHOD_0         0  '0 positional arguments'
               88  POP_TOP          

 L. 145        90  LOAD_FAST                'self'
               92  LOAD_ATTR                model
               94  LOAD_METHOD              endResetModel
               96  CALL_METHOD_0         0  '0 positional arguments'
               98  POP_TOP          

 L. 146       100  LOAD_FAST                'self'
              102  LOAD_ATTR                model
              104  LOAD_ATTR                source
              106  POP_JUMP_IF_FALSE   212  'to 212'

 L. 147       108  LOAD_FAST                'value'
              110  POP_JUMP_IF_FALSE   170  'to 170'

 L. 148       112  LOAD_GLOBAL              findInList
              114  LOAD_FAST                'self'
              116  LOAD_ATTR                model
              118  LOAD_ATTR                source
              120  LOAD_FAST                'value'
              122  CALL_FUNCTION_2       2  '2 positional arguments'
              124  STORE_FAST               'found'

 L. 149       126  LOAD_FAST                'found'
              128  LOAD_CONST               -1
              130  COMPARE_OP               ==
              132  POP_JUMP_IF_FALSE   164  'to 164'

 L. 150       134  LOAD_GLOBAL              len
              136  LOAD_FAST                'self'
              138  LOAD_ATTR                model
              140  LOAD_ATTR                source
              142  CALL_FUNCTION_1       1  '1 positional argument'
              144  STORE_FAST               'l'

 L. 151       146  LOAD_FAST                'selected_row'
              148  LOAD_FAST                'l'
              150  COMPARE_OP               >=
              152  POP_JUMP_IF_FALSE   168  'to 168'

 L. 151       154  LOAD_FAST                'l'
              156  LOAD_CONST               1
              158  BINARY_SUBTRACT  
              160  STORE_FAST               'selected_row'
              162  JUMP_ABSOLUTE       174  'to 174'
            164_0  COME_FROM           132  '132'

 L. 153       164  LOAD_FAST                'found'
              166  STORE_FAST               'selected_row'
            168_0  COME_FROM           152  '152'
              168  JUMP_FORWARD        174  'to 174'
            170_0  COME_FROM           110  '110'

 L. 155       170  LOAD_CONST               0
              172  STORE_FAST               'selected_row'
            174_0  COME_FROM           168  '168'

 L. 156       174  LOAD_FAST                'self'
              176  LOAD_ATTR                model
              178  LOAD_METHOD              index
              180  LOAD_FAST                'selected_row'
              182  LOAD_CONST               0
              184  CALL_METHOD_2         2  '2 positional arguments'
              186  STORE_FAST               'm_index'

 L. 157       188  LOAD_FAST                'self'
              190  LOAD_ATTR                view
              192  LOAD_METHOD              setCurrentIndex
              194  LOAD_FAST                'm_index'
              196  CALL_METHOD_1         1  '1 positional argument'
              198  POP_TOP          

 L. 158       200  LOAD_FAST                'self'
              202  LOAD_ATTR                view
              204  LOAD_METHOD              scrollTo
              206  LOAD_FAST                'm_index'
              208  CALL_METHOD_1         1  '1 positional argument'
              210  POP_TOP          
            212_0  COME_FROM           106  '106'

 L. 159       212  LOAD_FAST                'self'
              214  LOAD_METHOD              buttonStatus
              216  CALL_METHOD_0         0  '0 positional arguments'
              218  POP_TOP          

Parse error at or near `LOAD_FAST' instruction at offset 212

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