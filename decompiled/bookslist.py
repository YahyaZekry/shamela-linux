# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: bookslist.py
import ast, glob
from functools import partial
from qtpy.QtCore import Qt, QAbstractTableModel, QCoreApplication, QT_TRANSLATE_NOOP, Signal, QSize, QTimer
from qtpy.QtGui import QClipboard
from qtpy.QtWidgets import QStackedWidget, QGroupBox, QButtonGroup, QHeaderView, QAbstractItemView, QWidget, QToolBar, QCheckBox, QMenu, QAction, QPushButton, QActionGroup, QLabel, QWidgetAction, QListWidget, QToolButton
from hijridate import convert
from customs import CACHED_BRUSH_DARK_GREEN, CACHED_BRUSH_DARK_RED, CACHED_BRUSH_LIGHT_GREEN, CACHED_BRUSH_LIGHT_RED, alert_brush
from across import Across
from basebookview import EmbeddedInfo
from cache import AuthorCache, BookCache, PdfSize
from customs import NVDA, BusySpinner, findInList, flexibleBrowser, toCheckState, checkStateValue, isCheckedState, customLayout, customMessage, BooksTable, TableView, TableModel, customToolButton, standardFont, customSplitter, TimedLineEdit, hLine, LineEdit, QtFont, printQuery, List
from dbmanager import CoreDb, UserDb
from engine import filterBooks, filterAuthors
from theme import Icon
from settings import Settings
from textmanager import arabize, treatSearch, iso, contains, conditioned
WAITING_DOWNLOAD_STAGE = QT_TRANSLATE_NOOP('ScopeModel', 'Waiting to download')
WAITING_PREPARE_STAGE = QT_TRANSLATE_NOOP('ScopeModel', 'Downloaded, waiting to be prepared')
PREPARING_STAGE = QT_TRANSLATE_NOOP('ScopeModel', 'Preparing the book')

def stageText(value, holder):
    if value == Across.BUSY and holder is not Across.downloading_books:
        source = PREPARING_STAGE
    else:
        if holder is Across.importing_books:
            source = WAITING_PREPARE_STAGE
        else:
            source = WAITING_DOWNLOAD_STAGE
    return QCoreApplication.translate('ScopeModel', source)


def _alertBrush():
    return alert_brush()


def _safeBrush():
    if Across.active_theme == 'dark':
        return CACHED_BRUSH_LIGHT_GREEN
    return CACHED_BRUSH_DARK_GREEN


class SelectCategories(QWidget):

    def __init__(self, select_widget):
        super().__init__()
        self.context = select_widget.context
        self.current_category = None
        self.type_set = self.printed_set = None
        self.books = BooksWidget(select_widget, screen='category')
        self.books.setSay('قائمة كتب القسم')
        self.categories_list = []
        self.model = CategoriesModel([self.tr('Category'), self.tr('Count')], select_widget, self)
        self.view = CategoriesView(self)
        self.view.setSay('قائمة الأقسام')
        self.text = ''
        self.line = TimedLineEdit(search_slot=(self.updateLine), focus_list=(self.view))
        self.view.find_line = self.line
        list_layout = customLayout(True, [2, self.line, 2, self.view])
        list_layout = customSplitter(False, list_layout, self.books, 37)
        above_bar = TypeSelector(self.typeChanged)
        self.setLayout(customLayout(True, [above_bar, list_layout]))
        self.view.setCurrentIndex(self.model.index(0, 0))

    def typeChanged(self, type_set, printed_set):
        self.type_set = type_set
        self.printed_set = printed_set
        self.reinstall(True)

    def reinstall(self, keep_position=True):
        self.categories_list = CoreDb().getCategories(self.context, self.type_set, self.printed_set)
        self.refresh(keep_position)

    def refresh(self, keep_position):
        if self.text:
            source = filterCategories(self.text, self.categories_list)
        else:
            source = self.categories_list
        self.view.setModelSource(source, keep_position=keep_position)
        if not source:
            self.books.setSource([])

    def updateLine(self):
        self.text = treatSearch(self.line.text())
        self.refresh(False)

    def getMembers(self, category_id):
        return CoreDb().getBooks(category_id, self.context, self.type_set, self.printed_set)

    def isGroupSelected(self):
        if self.view.selectionModel().selectedRows():
            return True
        return False


class TypeSelector(QWidget):

    def __init__(self, slot):
        super().__init__()
        self.slot = slot

        def toolBar():
            toolbar = QToolBar(self)
            toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
            toolbar.setStyleSheet('QToolBar{spacing:3px;}')
            return toolbar

        def group(text):
            group_box = QGroupBox(text)
            group_box.setAlignment(Qt.AlignCenter)
            group_box.setCheckable(True)
            group_box.setChecked(True)
            group_box.setStyleSheet('QGroupBox::title {subcontrol-origin:margin; subcontrol-position:top center; left:0; margin:0;}')
            return group_box

        self.viewTypes, self.printedTypes = [], []
        self.type_set, self.printed_set = {
         1, 2, 3, 4, 5, 6}, {1, 2, 3}
        texts = [
         [
          self.tr('Numbered same as printed'), self.tr('Numbered same as the printed script')],
         [
          self.tr('Numberd different than printed'), self.tr('Numberd different than the printed script')]]
        for text in texts:
            toggle = QCheckBox(text[0])
            toggle.setToolTip(text[1])
            toggle.setCheckable(True)
            toggle.setChecked(True)
            toggle.toggled.connect(self.updatePrinted)
            self.printedTypes.append(toggle)

        print_layout = customLayout(True, (self.printedTypes), margins=0)
        texts = (
         ' ' + self.tr('Books'), self.tr('Magazines'), self.tr('Manuscripts'), self.tr('Thesis'),
         self.tr('Electronic'), self.tr('Audio'))
        tips = (self.tr('Show/ Hide Books'), self.tr('Show/ Hide Magazines'), self.tr('Show/ Hide Manuscripts'),
         self.tr('Show/ Hide Thesis'), self.tr('Show/ Hide Electronic Publication'), self.tr('Show/ Hide Written Audio'))
        icons = ('book', 'bohoth', 'manuscript', 'thesis', 'electronic', 'sound')
        self.toolbar_printed = toolBar()
        self.toolbar_unprinted = toolBar()
        for i in range(6):
            toolbar = self.toolbar_printed if i < 2 else self.toolbar_unprinted
            button = customToolButton(icon=f":/icons/{icons[i]}.png", tooltip=(tips[i]), text=(texts[i]), checkable=True,
              slot=(self.updateView),
              text_beside=True)
            toolbar.addWidget(button)
            button.setChecked(True)
            self.viewTypes.append(button)

        self.group_printed = group(self.tr('printed'))
        self.group_unprinted = group(self.tr('unprinted'))
        self.group_printed.setLayout(customLayout(False, [self.toolbar_printed, 5, print_layout], margins=3))
        self.group_unprinted.setLayout(customLayout(True, [self.toolbar_unprinted], margins=3))
        self.group_printed.toggled.connect(self.updatePrintedGroup)
        self.group_unprinted.toggled.connect(self.updateUnprintedGroup)
        self.widgetsFromValues()
        self.review()
        self.setLayout(customLayout(False, [0, self.group_printed, 5, self.group_unprinted, 0], margins=0))
        self.setFixedHeight(70)
        QTimer.singleShot(0, self.ensuregroups)
        self.setMinimumWidth(self.group_printed.sizeHint().width() + self.group_unprinted.sizeHint().width() + 10)

    def widgetsFromValues(self):
        for i in range(2):
            self.printedTypes[i].blockSignals(True)
            self.printedTypes[i].setChecked(i + 1 in self.printed_set)
            self.printedTypes[i].blockSignals(False)

        for i in range(2):
            self.viewTypes[i].blockSignals(True)
            self.viewTypes[i].setChecked(i + 1 in self.type_set)
            self.viewTypes[i].blockSignals(False)

        for i in range(2, 6):
            self.viewTypes[i].blockSignals(True)
            self.viewTypes[i].setChecked(i + 1 in self.type_set)
            self.viewTypes[i].blockSignals(False)

    def updatePrintedGroup(self, value):
        self.printed_set = {1, 2} if value else set()
        for i in range(2):
            self.printedTypes[i].blockSignals(True)
            self.printedTypes[i].setChecked(value)
            self.printedTypes[i].blockSignals(False)

        for i in range(2):
            self.viewTypes[i].blockSignals(True)
            self.viewTypes[i].setChecked(value)
            self.viewTypes[i].blockSignals(False)

        self.updateView()

    def updateUnprintedGroup(self, value):
        self.type_set = set()
        for i in range(2, 6):
            self.viewTypes[i].blockSignals(True)
            self.viewTypes[i].setChecked(value)
            self.viewTypes[i].blockSignals(False)

        self.updateView()

    def ensuregroups(self):
        self.group_printed.blockSignals(True)
        self.group_unprinted.blockSignals(True)
        will = True
        if not self.printed_set & {1, 2}:
            will = False
        if not self.type_set & {1, 2}:
            will = False
        self.group_printed.setChecked(will)
        will = True
        if not self.type_set & {3, 4, 5, 6}:
            will = False
        self.group_unprinted.setChecked(will)
        self.toolbar_unprinted.setEnabled(True)
        self.toolbar_printed.setEnabled(True)
        for i in range(6):
            self.viewTypes[i].setEnabled(True)

        for i in range(2):
            self.printedTypes[i].setEnabled(True)

        self.group_printed.blockSignals(False)
        self.group_unprinted.blockSignals(False)

    def updatePrinted(self):
        self.printed_set = set()
        for i in range(2):
            if self.printedTypes[i].isChecked():
                self.printed_set.add(i + 1)

        self.review()

    def updateView(self):
        self.type_set = set()
        for i in range(6):
            if self.viewTypes[i].isChecked():
                self.type_set.add(i + 1)

        self.review()

    def review(self):
        self.slot(self.type_set, self.printed_set)
        self.ensuregroups()

    def minimumSizeHint(self):
        return QSize(650, 50)


class CategoriesView(TableView):

    def __init__(self, select_widget):
        super().__init__((select_widget.model), instant_display=True)
        standardFont(self)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.setColumnWidth(1, 50)
        self.setShowGrid(False)
        self.select_widget = select_widget
        if self.select_widget.context in frozenset({2, 4, 5}):
            self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        else:
            self.setSelectionMode(QAbstractItemView.SingleSelection)

    def enterPressed(self):
        self.select_widget.books.view.setFocus()

    def displayRow(self, row, keep_position=None, forced=None):
        source = self.model().source
        if source:
            self.select_widget.current_category = source[row][0]
            self.select_widget.books.setSource((self.select_widget.getMembers(self.select_widget.current_category)), keep_position=keep_position)

    def copyItems(self):
        source = self.model().source
        books = []
        rows = sorted(set([index.row() for index in self.selectedIndexes()]))
        for row in rows:
            books.append(source[row][1])

        QClipboard().setText('\n'.join(books))


class CategoriesModel(TableModel):

    def __init__(self, headers, select_widget, category_widget):
        super().__init__(headers)
        self.select_widget = select_widget
        self.category_widget = category_widget

    def data(self, QModelIndex, int_role=None):
        row = QModelIndex.row()
        column = QModelIndex.column()
        if int_role == Qt.DisplayRole:
            if column == 0:
                return self.source[row][1]
            if column == 1:
                return arabize((f"{self.source[row][2]}"))
        elif int_role == Qt.CheckStateRole:
            if column == 0:
                if self.select_widget.context == 2:
                    return checkStateValue(toCheckState(self.isSelected(row)))

    def setData(self, QModelIndex, QVariant, int_role=None):
        from selectwidget import selectAll
        if QModelIndex.isValid():
            if QModelIndex.column() == 0:
                if int_role == Qt.CheckStateRole:
                    if self.select_widget.scope is not None:
                        selectAll(self.select_widget, True if isCheckedState(QVariant) else False, QModelIndex.row())
            return True

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            if self.select_widget.context == 2:
                if QModelIndex.column() == 0:
                    if self.select_widget.scope:
                        return super().flags(QModelIndex) | Qt.ItemIsUserCheckable
            return super().flags(QModelIndex)

    def isSelected(self, row):
        category = self.source[row][0]
        type_set = self.category_widget.type_set
        printed_set = self.category_widget.printed_set
        return self.select_widget.scope.isCategorySelected(category, type_set, printed_set)


class OneSelector(QGroupBox):

    def __init__(self, selector_type, select_widget):
        super().__init__()
        self.selector_type = selector_type
        self.select_widget = select_widget
        self.setUi()
        self.loadLists()
        self.connectSlots()

    def connectSlots(self):
        self.fromList.currentTextChanged.connect(self.fromText.setText)
        self.toList.currentTextChanged.connect(self.toText.setText)
        self.addButton.clicked.connect(self.addItems)

    def setUi(self):
        label = QLabel(self.tr('Period by century') if self.selector_type == 0 else self.tr('Period by year'))
        label.setFont(QtFont(['Traditional Naskh', 12, True, False]))
        from_label = QLabel('(' + self.tr('From') + ')')
        from_label.setAlignment(Qt.AlignCenter)
        to_label = QLabel('(' + self.tr('To') + ')')
        to_label.setAlignment(Qt.AlignCenter)
        self.fromList = QListWidget()
        self.toList = QListWidget()
        self.fromText = LineEdit(digit_policy='display', slot=(self.addItems))
        self.toText = LineEdit(digit_policy='display', slot=(self.addItems))
        self.addButton = QPushButton(self.tr('Add to scope'))
        self.addButton.setIcon(Icon.icon(':/icons/check.png'))
        self.addButton._icon_path = ':/icons/check.png'
        indicator = QLabel('[' + (self.tr('Period by century') if self.selector_type == 0 else self.tr('Period by year')) + ']')
        from_lay = customLayout(True, [from_label, 6, self.fromList, 3, self.fromText])
        to_lay = customLayout(True, [to_label, 6, self.toList, 3, self.toText])
        list_lay = customLayout(False, [from_lay, 3, to_lay])
        add_lay = customLayout(False, [indicator, 0, self.addButton])
        self.setLayout(customLayout(True, [6, label, 6, hLine(), list_lay, add_lay]))
        self.setMaximumWidth(300)

    def loadLists(self):
        current_year = convert.Gregorian.today().to_hijri().year
        if self.selector_type == 0:
            current_century = current_year / 100
            int_century = int(current_century)
            if current_century != int_century:
                current_century = int_century + 1
            items = [arabize(century) + ' هـ' for century in range(1, current_century)]
            items.insert(0, self.tr('before first century H'))
            items.append(self.tr('Current century'))
        else:
            items = [arabize(year) + ' هـ' for year in range(1, current_year)]
            items.insert(0, self.tr('before first year H'))
            items.append(self.tr('Current year'))
        self.fromList.addItems(items)
        self.toList.addItems(items)

    def addItems(self):
        START = -99999
        END = 99999
        list_count = self.fromList.count()
        start_in_list = self.fromList.item(0).text()
        end_in_list = self.fromList.item(list_count - 1).text()
        end_num_in_list = val(self.fromList.item(list_count - 2).text())
        start_text = self.fromText.text()
        if start_text == start_in_list:
            i_start = START
        else:
            if start_text == end_in_list:
                i_start = END
            else:
                i_start = val(start_text) or START
        end_text = self.toText.text()
        if end_text == start_in_list:
            i_end = START
        else:
            if end_text == end_in_list:
                i_end = END
            else:
                i_end = val(end_text) or END
        if i_start < 1:
            i_start = START
        if i_end > end_num_in_list:
            i_end = END
        if i_end < i_start:
            customMessage(self.tr('Ensure Input'), self.tr('End date can not be before start date'))
            return
        if self.selector_type == 0:
            if i_start != START:
                i_start = (i_start - 1) * 100 + 1
            if i_end != END:
                i_end = i_end * 100
        t_start = self.tr('start') if i_start == START else arabize(i_start)
        t_end = self.tr('Current year') if i_end == END else arabize(i_end)
        period = f"{t_start}|{t_end}|{i_start}|{i_end}"
        self.select_widget.scope.addPeriod(period, True)
        self.select_widget.scope_widget.bookChanged()


def val(text):
    import regex as re
    try:
        return int(re.findall('\\d+|$', text)[0])
    except Exception:
        return 0


class SelectPeriod(QWidget):

    def __init__(self, select_widget):
        super().__init__()
        century_list = OneSelector(0, select_widget)
        years_list = OneSelector(1, select_widget)
        lay = customLayout(False, [century_list, 25, years_list])
        self.setLayout(customLayout(True, [6, lay]))


class SelectAuthors(QWidget):

    def __init__(self, select_widget, panel=None):
        super().__init__()
        self.context = select_widget.context
        self.panel = panel
        self.authors_dict = None
        headers = [self.tr('Number'), self.tr('Author'), self.tr('Death'), self.tr('Books')] if self.panel else [
         self.tr('Author'), self.tr('Death'), self.tr('Books')]
        self.model = AuthorModel(headers, panel, select_widget)
        self.view = AuthorView(self)
        self.view.setSay('قائمة المؤلفين')
        self.text = ''
        self.line = TimedLineEdit(search_slot=(self.updateLine), focus_list=(self.view))
        self.view.find_line = self.line
        if self.panel:
            self.setLayout(customLayout(True, [self.line, self.view]))
        else:
            self.authorBiblo = flexibleBrowser()
            self.authorBiblo.setVisible(False)
            self.showBiographyButton = customToolButton(':/icons/authors.png', self.tr('Author biography'))
            self.showBiographyButton.setCheckable(True)
            self.showBiographyButton.setChecked(False)
            self.showBiographyButton.toggled.connect(self.togglebiography)
            self.books = BooksWidget(select_widget, screen='author')
            self.books.setSay('قائمة كتب المؤلف')
            self.showBiographyButton.setFixedHeight(self.line.sizeHint().height())
            if Across.active_theme in ('dark', 'modern_light'):
                self.showBiographyButton.setStyleSheet('QToolButton {padding: 0px;}')
            lay = customLayout(False, [self.line, self.showBiographyButton], margins=0)
            lay = customLayout(True, [2, lay, 2, self.view], margins=[0, 1, 1, 1])
            lay = customSplitter(True, lay, self.authorBiblo, 65)
            lay = customSplitter(False, lay, self.books, 44)
            self.setLayout(customLayout(False, [lay]))
            self.reinstall(keep_position=None)

    def togglebiography(self, value):
        self.authorBiblo.setVisible(value)
        if value:
            self.view.displayRow(forced=True)

    def reinstall(self, keep_position=True):
        self.authors_dict = CoreDb().getAuthors(self.context)
        self.refresh(keep_position)

    def setSource(self):
        source = list(self.authors_dict.items())
        self.view.model().source = source
        self.view.model().beginResetModel()
        self.view.model().endResetModel()

    def refresh(self, keep_position):
        if self.text:
            source = filterAuthors(self.text, self.authors_dict)
        else:
            source = list(self.authors_dict.items())
        self.view.setModelSource(source, keep_position=keep_position)
        if not self.panel:
            if len(source) == 0:
                self.books.setSource([])
                self.authorBiblo.setHtml('')

    def getMembers(self, author_id):
        return CoreDb().getAuthorBooks(author_id, self.context)

    def updateLine(self):
        self.text = treatSearch(self.line.text())
        self.refresh(False)

    def isGroupSelected(self):
        if self.view.selectionModel().selectedRows():
            return True
        return False

    def selectionButtonsText(self):
        rows = set()
        for index in self.view.selectedIndexes():
            rows.add(index.row())

        return (
         self.tr('Check Selected Authors'), self.tr('Uncheck Selected Authors'))


class AuthorView(TableView):
    go = Signal(int)

    def __init__(self, author_widget):
        super().__init__((author_widget.model), instant_display=True)
        standardFont(self)
        if author_widget.panel:
            self.setColumnWidth(0, 40)
            self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.setColumnWidth(2, 65)
            self.setColumnWidth(3, 40)
        else:
            self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.setColumnWidth(1, 65)
            self.setColumnWidth(2, 40)
        self.setShowGrid(False)
        self.author_widget = author_widget
        if self.author_widget.context in frozenset({2, 4, 5}):
            self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        else:
            self.setSelectionMode(QAbstractItemView.SingleSelection)

    def copyItems(self):
        source = self.model().source
        books = []
        rows = sorted(set([index.row() for index in self.selectedIndexes()]))
        for row in rows:
            books.append(AuthorCache.authorName(source[row][0]))

        QClipboard().setText('\n'.join(books))

    def enterPressed(self):
        self.author_widget.books.view.setFocus()

    def displayRow(self, row=None, keep_position=None, forced=None):
        if self.model().source:
            if row is None:
                row = self.currentIndex().row()
            self.author_widget.current_author = self.model().source[row][0]
            if row > -1:
                if self.author_widget.panel:
                    self.go.emit(self.author_widget.current_author)
                else:
                    self.author_widget.books.setSource((self.author_widget.getMembers(self.author_widget.current_author)), keep_position=keep_position)
                    if not self.author_widget.authorBiblo.isVisible():
                        if not forced:
                            return
                    self.author_widget.authorBiblo.setHtml(CoreDb().authorBiography(self.author_widget.current_author))
        else:
            self.author_widget.authorBiblo.setHtml('')


class AuthorModel(TableModel):

    def __init__(self, headers, panel, select_widget):
        super().__init__(headers)
        self.select_widget = select_widget
        self.col_num, self.col_name, self.col_death, self.col_books = (0, 1, 2, 3) if panel else (None,
                                                                                                  0,
                                                                                                  1,
                                                                                                  2)

    def data(self, QModelIndex, int_role=None):
        column = QModelIndex.column()
        row = QModelIndex.row()
        if int_role == Qt.DisplayRole:
            if column == self.col_num:
                return arabize((f"{row + 1}"))
            if column == self.col_name:
                return AuthorCache.authorName(self.source[row][0])
            if column == self.col_death:
                return arabize(AuthorCache.authorDeath(self.source[row][0]))
            if column == self.col_books:
                return arabize((f"{self.source[row][1]}"))
        else:
            if int_role == Qt.ToolTipRole:
                return conditioned(CoreDb().authorBiography((self.source[row][0]), truncated=True))
            if int_role == Qt.CheckStateRole:
                if column == 0:
                    if self.select_widget.context == 2:
                        return checkStateValue(toCheckState(self.isSelected(row)))

    def setData(self, QModelIndex, QVariant, int_role=None):
        from selectwidget import selectAll
        if QModelIndex.isValid():
            if QModelIndex.column() == 0:
                if int_role == Qt.CheckStateRole:
                    if self.select_widget.scope is not None:
                        selectAll(self.select_widget, True if isCheckedState(QVariant) else False, QModelIndex.row())
            return True

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            if self.select_widget.context == 2:
                if QModelIndex.column() == 0:
                    if self.select_widget.scope:
                        return super().flags(QModelIndex) | Qt.ItemIsUserCheckable
            return super().flags(QModelIndex)

    def isSelected(self, row):
        author = self.source[row][0]
        return self.select_widget.scope.isAuthorSelected(author)


class ShowBase(QWidget):

    def __init__(self, select_widget, screen):
        super().__init__()
        self.books = BooksWidget(select_widget, screen=screen)
        self.select_widget = select_widget
        self.setSource()
        self.setLayout(customLayout(True, [self.books], parent=self))

    def setSay(self, say_me):
        self.books.setSay(say_me)

    def setSource(self, keep_position=None):
        pass

    def reinstall(self):
        self.setSource(keep_position=True)


class ShowSearchBooks(ShowBase):

    def __init__(self, select_widget):
        super().__init__(select_widget, screen='search')

    def setSource(self, keep_position=None):
        self.books.setSource((self.select_widget.allowed_list), keep_position=keep_position)


class ShowHistory(ShowBase):

    def __init__(self, select_widget):
        super().__init__(select_widget, screen='history')

    def setSource(self, keep_position=None):
        book_list = [book for book in UserDb().getHistory(self.select_widget.allowed_set)]
        self.books.setSource(book_list, keep_position=keep_position)


class ShowBothDownloads(QWidget):

    def __init__(self, select_widget):
        super().__init__()
        self.select_widget = select_widget
        self.pages = QStackedWidget()
        self.pdf_page = self.books = None
        self.books_page = ShowDownloads(self.select_widget)
        self.books_page.setSay('قائمة الكتب المحملة')
        toolbar = QToolBar(self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QSize(20, 20))
        self.group = QButtonGroup(self)
        texts = (
         self.tr('Texts'), self.tr('Pdfs'))
        icons = (':/icons/book.png', ':/icons/pdf_d.png')
        slots = (self.showBooks, self.showPdfs)
        for i in range(2):
            button = customToolButton(icon=(icons[i]), tooltip=(texts[i]), text_beside=True, checkable=True, slot=(slots[i]))
            toolbar.addWidget(button)
            self.group.addButton(button)
            if i == 0:
                button.setChecked(True)

        self.pages.addWidget(self.books_page)
        self.showBooks()
        self.setLayout(customLayout(True, [toolbar, self.pages], margins=0))
        QTimer.singleShot(0, self.books_page.books.filter_text.setFocus)

    def showPdfs(self):
        if not self.pdf_page:
            self.pdf_page = ShowPdfDownloads(self.select_widget)
            self.pdf_page.setSay('قائمة المصورات المحملة')
            self.pages.addWidget(self.pdf_page)
            self.pdf_page.books.filter_text.setFocus()
        self.pages.setCurrentWidget(self.pdf_page)
        self.books = self.pdf_page.books

    def showBooks(self):
        self.pages.setCurrentWidget(self.books_page)
        self.books = self.books_page.books

    def reinstall(self):
        self.pages.currentWidget().reinstall()


class ShowDownloads(ShowBase):

    def __init__(self, select_widget):
        super().__init__(select_widget, screen='download')

    def setSource(self, keep_position=None):
        book_list = [book for book in UserDb().getDownloadHistory('text', self.select_widget.allowed_set)]
        self.books.setSource(book_list, keep_position=keep_position)


class ShowPdfDownloads(ShowBase):

    def __init__(self, select_widget):
        super().__init__(select_widget, screen='pdf')

    def setSource(self, keep_position=None):
        book_list = [book for book in UserDb().getDownloadHistory('pdf', self.select_widget.allowed_set)]
        self.books.setSource(book_list, keep_position=keep_position)


class BooksWidget(QWidget):

    def __init__(self, select_widget, screen):
        super().__init__()
        self.screen = screen
        self.select_widget = select_widget
        self.initial_betaka_displayed = None
        self.betakaBrowser = EmbeddedInfo(author=(screen == 'author'))
        self.betakaBrowser.setVisible(False)
        betkaSearchButton = QToolButton()
        betkaSearchButton.setStyleSheet('QToolButton::menu-indicator {image: none; width: 0px; padding: 0px;}')
        betkaSearchButton.setIcon(Icon.icon(':/icons/settings.png'))
        betkaSearchButton._icon_path = ':/icons/settings.png'
        betkaSearchButton.setToolTip(self.tr('Search Settings'))
        betkaSearchButton.setMaximumWidth(32)
        betkaSearchButton.setAutoRaise(True)
        betkaSearchButton.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(betkaSearchButton)
        label = QLabel(self.tr('Search In:'))
        label.setAlignment(Qt.AlignCenter)
        widget = QWidgetAction(menu)
        widget.setDefaultWidget(label)
        menu.addAction(widget)
        menu.addSeparator()
        items = (
         self.tr('Book'), self.tr('Book and Author'), self.tr('Book and Author and Betaka'))
        self.actions = []
        group = QActionGroup(self)
        for i, item in enumerate(items):
            action = QAction(item)
            action.setCheckable(True)
            menu.addAction(action)
            group.addAction(action)
            if i == 1:
                action.setChecked(True)
            action.triggered.connect(partial(self.changeFilterStatus, i))
            self.actions.append(action)

        betkaSearchButton.setMenu(menu)
        self.model = BooksModel(self, select_widget, screen)
        self.view = BooksView(self.model, select_widget.context, self.betakaBrowser, screen)
        self.filter_text = TimedLineEdit(search_slot=(self.updateLine), focus_list=(self.view))
        if screen != 'author':
            self.filter_text.setPlaceholderText(self.tr('You can search by a part of book name, author name, or both'))
        self.view.find_line = self.filter_text
        self.showBetakaButton = customToolButton(':/icons/betaka.png', self.tr('Book Information'))
        self.showBetakaButton.setCheckable(True)
        self.showBetakaButton.toggled.connect(self.toggleBetaka)
        _filter_h = self.filter_text.sizeHint().height()
        betkaSearchButton.setFixedHeight(_filter_h)
        self.showBetakaButton.setFixedHeight(_filter_h)
        if Across.active_theme in ('dark', 'modern_light'):
            betkaSearchButton.setStyleSheet(betkaSearchButton.styleSheet() + 'QToolButton {padding: 0px;}')
            self.showBetakaButton.setStyleSheet('QToolButton {padding: 0px;}')
        lay = customLayout(False, [self.filter_text, betkaSearchButton, self.showBetakaButton], margins=0)
        lay = customLayout(True, [2, lay, 2, self.view], margins=0)
        lay = customSplitter(True, lay, self.betakaBrowser, 65 if screen == 'author' else 55)
        self.setLayout(customLayout(True, [lay]))
        self.rows = []
        self.view.selectionModel().selectionChanged.connect(self.selectionChanged)
        self.model.modelReset.connect(self.selectionChanged)

    def setSay(self, say_me):
        self.view.say_me = say_me

    def changeFilterStatus(self, status):
        self.model.filter_status = status
        if status > 1:
            if not self.showBetakaButton.isChecked():
                self.showBetakaButton.setChecked(True)
        self.updateLine()

    def initialBetaka(self):
        if not self.initial_betaka_displayed:
            self.initial_betaka_displayed = True
            checked = UserDb().load(f"betaka_view_{self.screen}", False)
            self.showBetakaButton.blockSignals(True)
            self.showBetakaButton.setChecked(checked)
            self.showBetakaButton.blockSignals(False)
            self.betakaBrowser.setVisible(checked)
            if checked:
                self.view.displayRow(forced=True)

    def toggleBetaka(self, value):
        self.betakaBrowser.setVisible(value)
        if value:
            self.view.displayRow(forced=True)
        UserDb().save(f"betaka_view_{self.screen}", value)

    def hasSelection(self):
        return len(self.view.selectedIndexes()) != 0

    def selectionChanged(self):
        self.select_widget.testSelection()
        self.view.displayRow()

    def endResetModel(self):
        self.model.beginResetModel()
        self.model.endResetModel()

    def updateLine(self):
        self.model.filter_text = treatSearch(self.filter_text.text())
        self.model.updateFilter()
        self.view.setCurrentIndex(self.model.index(0, 0))

    def setSource(self, source, names_dict=None, page_dict=None, keep_position=None):
        """Call this Function to keep selection after setting source if possible"""
        if not source:
            self.model.setSource(source, names_dict, page_dict)
            self.view.clearBetaka()
            return
            will = False
            will = keep_position or True
        else:
            if not self.model.rowCount():
                will = True
            else:
                row = self.view.currentIndex().row()
                if row == -1:
                    will = True
                elif will:
                    self.model.setSource(source, names_dict, page_dict)
                    if not NVDA.isRunning():
                        self.view.setCurrentIndex(self.model.index(0, 0))
                    self.view.displayRow(0)
                    self.initialBetaka()
                    return
                    old_value = self.model.source[row]
                    old_count = len(self.model.source)
                    self.model.setSource(source, names_dict, page_dict)
                    new_count = self.model.rowCount()
                    if new_count == old_count:
                        self.model.dataChanged.emit(self.model.index(0, 0), self.model.index(new_count - 1, self.model.columnCount() - 1))
                else:
                    self.model.beginResetModel()
                    self.model.endResetModel()
                i = findInList(self.model.source, old_value)
                if i != -1:
                    index = self.model.index(i, 0)
                    self.view.setCurrentIndex(index)
                    self.view.scrollTo(index)
                    self.view.displayRow(i, keep_position=keep_position)
                    return
                if new_count != old_count:
                    keep_position = None
                new_row = row if row < new_count else new_count - 1
                self.view.setCurrentIndex(self.model.index(new_row, 0))
                self.view.displayRow(new_row, keep_position=keep_position)

    def dataChanged(self):
        self.model.dataChanged.emit(self.model.index(0, 0), self.model.index(self.model.rowCount() - 1, self.model.columnCount() - 1))

    def selectedIds(self):
        return [self.model.source[row] for row in sorted([index.row() for index in self.view.selectionModel().selectedRows()])]


class BooksView(BooksTable):

    def __init__(self, model, context, betakaBrowser, screen=None):
        super().__init__(model)
        standardFont(self)
        self.context = context
        self.betakaBrowser = betakaBrowser
        self.screen = screen
        if context != 1:
            self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        if not model.headers:
            self.horizontalHeader().hide()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setShowGrid(False)
        self.total_width = sum(model.widths)
        self.widths = model.widths

    def displayRow(self, row=None, keep_position=None, forced=None):
        if self.model().source:
            if not self.betakaBrowser.isVisible():
                if not forced:
                    return
            if row is None:
                row = self.currentIndex().row()
            if row == -1:
                row = 0
            self.betakaBrowser.setBook(self.model().source[row])
        else:
            self.clearBetaka()

    def clearBetaka(self):
        self.betakaBrowser.setBook(None)


class BooksModel(QAbstractTableModel):
    firstRow = Signal(int)

    def __init__(self, books_widget, select_widget, screen=None, parent=None):
        super().__init__(parent)
        self.source = []
        self.complete_source = []
        self.filter_text = ''
        self.select_widget = select_widget
        self.screen = screen
        self.books_widget = books_widget
        self.names_dict = self.page_dict = None
        self.filter_status = 1
        self.pdf_column = self.size_column = self.author_column = None
        self.widths = [
         280]
        self.headers = []
        author = self.screen != 'author'
        self.name_func = BookCache.abstractName if author else BookCache.bookName
        if author:
            last_column, self.author_column = (1, 1)
            self.widths.append(163 if screen in frozenset({'favorite', 'category'}) else 235)
            self.headers += [self.tr('Book'), self.tr('Author')]
        else:
            last_column, self.author_column = (0, None)
        if self.select_widget.context == 5:
            self.size_column = last_column + 1
            self.widths.append(55)
            if author:
                self.headers.append(self.tr('Size'))
        elif self.select_widget.context == 3:
            self.pdf_column = last_column + 1
            self.widths.append(32)
            if author:
                self.headers.append('')
        self.column_count = len(self.widths)

    def setSource(self, source, names_dict, page_dict):
        self.complete_source = source
        self.names_dict = names_dict
        self.page_dict = page_dict
        self.updateFilter()

    def updateFilter(self):
        if len(self.filter_text) > 2:
            self.source = filterBooks((self.filter_text), (self.complete_source), status=(self.filter_status))
        else:
            self.source = self.complete_source
        self.beginResetModel()
        self.endResetModel()
        if self.source:
            self.books_widget.view.displayRow(0)
        else:
            self.books_widget.view.clearBetaka()

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.source)

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            if QModelIndex.column() == 0:
                if self.select_widget.scope:
                    return super().flags(QModelIndex) | Qt.ItemIsUserCheckable
            return super().flags(QModelIndex)

    def _statusBrush(self, book_id):
        if self.select_widget.context == 2:
            if self.select_widget.scope and book_id in self.select_widget.scope.green:
                return _safeBrush()
        elif self.select_widget.context > 3:
            if book_id in self.select_widget.new_set:
                return _alertBrush()

    def getName(self, book_id):

        def finalize(book_id, text):
            if book_id in self.select_widget.new_set:
                return f"☆ {text}"
            return text

        if self.names_dict:
            if self.filter_text:
                if self.name_func(book_id) != self.names_dict[book_id]:
                    return finalize(book_id, f"{self.names_dict[book_id]} [{self.name_func(book_id)}]")
            return finalize(book_id, self.names_dict[book_id])
        return finalize(book_id, self.name_func(book_id))

    def data(self, QModelIndex, int_role=None):
        if self.source:
            if QModelIndex.isValid():
                row = QModelIndex.row()
                column = QModelIndex.column()
                book_id = self.source[row]
                if column == 0:
                    if int_role == Qt.DisplayRole:
                        return self.getName(book_id)
                    if int_role == Qt.ForegroundRole:
                        return self._statusBrush(book_id)
                    if int_role == Qt.ToolTipRole:
                        return conditioned(CoreDb().bookBetaka(book_id, True, truncated=True))
                    if int_role == Qt.DecorationRole:
                        if self.screen == 'pdf':
                            return BookCache.bookIcon(book_id, context=5)
                        return BookCache.bookIcon(book_id, context=(self.select_widget.context))
                    if int_role == Qt.CheckStateRole:
                        will = True
                        if self.select_widget.context == 4:
                            if Settings.getValue('auto_download_books'):
                                will = False
                        if self.select_widget.context == 5:
                            if Settings.getValue('auto_download_pdf'):
                                will = False
                        if self.select_widget.scope is None:
                            will = False
                        if will:
                            return checkStateValue(toCheckState(book_id in self.select_widget.scope.books))
                if self.author_column:
                    if column == self.author_column:
                        if int_role == Qt.DisplayRole:
                            return BookCache.authorName(book_id)
                        if int_role == Qt.ForegroundRole:
                            return self._statusBrush(book_id)
                        if int_role == Qt.ToolTipRole:
                            if '-' in BookCache.authorName(book_id):
                                return BookCache.authorName(book_id)
                            return conditioned(CoreDb().authorBiographyFromBook(book_id, truncated=True))
                if self.pdf_column:
                    if column == self.pdf_column:
                        if BookCache.hasPdf(book_id):
                            if int_role == Qt.DecorationRole:
                                return Icon.icon(':/icons/pdf_r.png')
                            if int_role == Qt.ToolTipRole:
                                return self.tr('The book has a pdf version')
                if self.size_column and column == self.size_column:
                    if int_role == Qt.DisplayRole:
                        return PdfSize.getSize(book_id)

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if self.headers:
            if int_role == Qt.DisplayRole:
                if Qt_Orientation == Qt.Horizontal:
                    return self.headers[p_int]

    def setData(self, QModelIndex, QVariant, int_role=None):
        if QModelIndex.isValid():
            if QModelIndex.column() == 0:
                if int_role == Qt.CheckStateRole:
                    if self.select_widget.scope is not None:
                        row = QModelIndex.row()
                        book_id = self.source[row]
                        if isCheckedState(QVariant):
                            self.select_widget.scope.books.add(book_id)
                            self.select_widget.scope_widget.bookChanged(False)
                        else:
                            self.select_widget.scope.discard(book_id)
                            self.select_widget.scope_widget.bookChanged(False)
            return True


class Scope(QWidget):
    scopeChanged = Signal(set)
    ignoreChanged = Signal()

    def __init__(self, select_widget, parent=None):
        super().__init__(parent)
        self.select_widget = select_widget
        self.select_widget.attach(self)
        self.model = ScopeModel(self.select_widget)
        self.view = ScopeView(self.model)
        self.model.modelReset.connect(self.buttonStatus)
        self.view.selectionModel().selectionChanged.connect(self.deleteButtonStatus)
        self.tried = None
        self.is_downloading = None
        self.downloader = []
        self.text = ''
        self.full_label = QLabel(self.tr('Current scope: all books'))
        self.full_label.setAlignment(Qt.AlignCenter)
        self.full_label.setFont(QtFont(['Traditional Naskh', 12, True, False]))
        self.full_label.setVisible(False)
        self.filter_text = TimedLineEdit(focus_list=(self.view))
        self.filter_text.textEdited.connect(lambda: self.updateLine(self.filter_text.text()))
        self.view.find_line = self.filter_text
        self.numLabel = QLabel()
        self.numLabel.setAlignment(Qt.AlignCenter)
        self.numLabel.setMinimumWidth(30)
        layout = None
        if not (select_widget.context == 2 or select_widget.context) == 4 or Settings.getValue('auto_download_books'):
            if not (select_widget.context == 5):
                self.delete_button = customToolButton(':/icons/delete_file.png', (self.tr('Delete Selected Items From the List')),
                  text_beside=True, slot=(self.deleteSelected))
                self.clear_button = customToolButton(':/icons/clear.png', (self.tr('Clear the List')), slot=(self.emptyList))
                self.lower_ribbon = QWidget()
                self.lower_ribbon.setLayout(customLayout(False, [self.delete_button, 0, self.clear_button], margins=[0, 2, 0, 2]))
                self.full_label.setFixedHeight(self.lower_ribbon.sizeHint().height())
                layout = customLayout(False, [self.full_label, self.lower_ribbon])
            if select_widget.context == 2:
                self.filled_list = QWidget()
                self.filled_list.setLayout(customLayout(True, [self.filter_text, self.view, layout]))
                self.setLayout(customLayout(True, [self.filled_list], margins=0))
            else:
                if Settings.getValue('auto_download_books' if select_widget.context == 4 else 'auto_download_pdf'):
                    widget = 1
                    self.bookChanged()
                    self.setLayout(customLayout(True, [widget, 10, self.filter_text, self.view, 2, layout], margins=[5, 12, 5, 1]))
                else:
                    self.fix_button = customToolButton(':/icons/fix.png', (self.tr('Fix Suspended Downloads')), iconsize=20, slot=(self.fixtDownload))
                    self.start_button = customToolButton(':/icons/start.png', (self.tr('Start Download')), iconsize=16, slot=(self.startDownload))
                    self.stop_button = customToolButton(':/icons/stop.png', (self.tr('Stop Download after the Current')), iconsize=16,
                      slot=(self.stopDownload))
                    self.startall_button = customToolButton(':/icons/downall.png', text=(self.tr('Add and start all')), iconsize=16, slot=(self.startAll), text_beside=True)
                    widget = QWidget()
                    widget.setMaximumHeight(30)
                    widget.setLayout(customLayout(False, [self.startall_button, 0, self.numLabel, 0, self.stop_button, 10, self.start_button, 20, self.fix_button]))
                    self.setLayout(customLayout(True, [widget, 2, self.filter_text, self.view, layout]))
        self.buttonStatus(True)
        self.deleteButtonStatus()

    def buttonStatus(self, nohide=None):
        filled = self.model.rowCount() != 0
        if self.select_widget.context == 2:
            self.lower_ribbon.setVisible(filled)
            self.full_label.setVisible(not filled)
        else:
            if hasattr(self, 'clear_button'):
                self.clear_button.setEnabled(filled)
            if hasattr(self, 'start_button'):
                self.start_button.setEnabled(filled)
                self.stop_button.setEnabled(filled)
                if self.is_downloading:
                    self.start_button.setEnabled(False)
                    self.startall_button.setEnabled(False)
                else:
                    self.startall_button.setEnabled(True)
                    self.stop_button.setEnabled(False)
        self.deleteButtonStatus()
        self.model.dataChanged.emit(self.model.index(0, 1), self.model.index(self.model.rowCount() - 1, 1))
        if (self.select_widget.allowed_list or self.select_widget.scope.books or nohide or self.select_widget.context) == 4:
            Across.main_window.update.hide()
        else:
            if self.select_widget.context == 5:
                Across.main_window.pdf.hide()

    def deleteButtonStatus(self):
        if hasattr(self, 'delete_button'):
            if self.view.selectedIndexes():
                self.delete_button.setEnabled(True)
            else:
                self.delete_button.setEnabled(False)

    def fixtDownload(self):
        import shutil, dirs, os
        from qtpy.QtWidgets import QApplication
        from downloader import Downloader
        from updater import Importer
        self.stopDownload()
        for worker in self.downloader:
            worker.stop()

        Downloader.abortAll()
        QApplication.processEvents()
        Downloader.valve.clear()
        Downloader.active.clear()
        self.tried = set()
        if self.select_widget.context == 4:
            Across.downloading_books.clear()
            Importer.drain()
            update_dir = dirs.updateDir()
            shutil.rmtree(update_dir, ignore_errors=True)
            os.makedirs(update_dir, exist_ok=True)
        else:
            if self.select_widget.context == 5:
                Across.downloading_pdfs.clear()
                pdf_dir = dirs.pdfPath().replace(os.sep, '/')
                file_list = glob.glob(f"{pdf_dir}/**/*.___", recursive=True)
                for file in file_list:
                    try:
                        os.unlink(file)
                    except OSError:
                        pass

            self.buttonStatus()

    def picker(self):

        def subBook(book_id):
            if self.select_widget.context == 5:
                return book_id
            sub_books = CoreDb().staleSubBooks(book_id)
            for book in sub_books:
                if book not in self.tried:
                    return book

            return book_id

        if not self.is_downloading:
            self.buttonStatus()
            return
        for value in self.select_widget.allowed_list:
            if value in self.select_widget.scope.books and value not in self.tried:
                new_value = subBook(value)
                if new_value:
                    self.tried.add(new_value)
                    return new_value

        if not (self.select_widget.allowed_list and self.select_widget.scope.books):
            self.is_downloading = None

    def ignoreBooks(self, books):
        CoreDb().addToIgnore(self.select_widget.context, books, True)
        self.ignoreChanged.emit()

    def startAll(self):
        self.select_widget.helper.checkAll()
        self.startDownload()

    def startDownload(self):
        self.tried = set()
        self.is_downloading = True
        self.buttonStatus()
        if not self.downloader:
            from updater import BookDownloader, PdfDownloader
            for i in range(6):
                self.downloader.append(BookDownloader(self.picker) if self.select_widget.context == 4 else PdfDownloader(self.picker))

        for i in range(6):
            self.downloader[i].go()

    def stopDownload(self):
        self.is_downloading = None
        self.buttonStatus()

    def updateLine(self, text):
        self.text = treatSearch(text)
        self.bookChanged()

    def deleteSelected(self):
        for index in self.view.selectedIndexes():
            self.select_widget.scope.discard(self.model.source[index.row()])

        self.bookChanged()

    def emptyList(self):
        self.select_widget.scope.clear()
        self.bookChanged()

    def bookChanged(self, refresh_attached=True):
        value = None
        selected_row = self.view.currentIndex().row()
        if selected_row > -1:
            value = self.model.source[selected_row]
        else:
            full_scope = self.select_widget.scope.modelScope()
            if self.text.strip():
                self.model.source = filterBooks(self.text, self.select_widget.scope.books, full_scope)
            else:
                self.model.source = full_scope
                self.scopeChanged.emit(set(self.model.source))
            rows = len(self.model.source)
            if rows:
                self.numLabel.setText(arabize((f"{rows}")))
            else:
                self.numLabel.setText('')
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
                if not NVDA.isRunning():
                    m_index = self.model.index(selected_row, 0)
                    self.view.setCurrentIndex(m_index)
                    self.view.scrollTo(m_index)
                else:
                    NVDA.silence()
            else:
                if self.select_widget.helper:
                    self.select_widget.helper.clearSelection()
            self.is_downloading = None
        self.buttonStatus()
        if refresh_attached:
            if self.select_widget.pages.currentWidget():
                try:
                    self.select_widget.pages.currentWidget().books.dataChanged()
                except:
                    pass


class ScopeView(BooksTable):

    def __init__(self, model):
        super().__init__(model)
        standardFont(self)
        if model.select_widget.context >= 4:
            self.setShowGrid(False)
            self.horizontalHeader().hide()
            self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            if not (model.select_widget.context == 4 and Settings.getValue('auto_download_books')):
                if not model.select_widget.context == 5 or Settings.getValue('auto_download_pdf'):
                    self.setSelectionMode(QAbstractItemView.NoSelection)
                else:
                    self.setSelectionMode(QAbstractItemView.ExtendedSelection)
            else:
                self.simulateList()
                self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        elif model.select_widget.context == 4:
            self.setColumnWidth(1, self.percentWidth())
        else:
            if model.select_widget.context == 5:
                self.setColumnWidth(1, 55)
                self.setColumnWidth(2, self.percentWidth())

    def percentWidth(self):
        """room for the widest cell, "99 %", and then some: this column must
        never elide, and the delegate spends ~6px of it on margins.

        The size is fixed at 10pt but scaling.scaled_font_size lifts it with the
        display scaling (13pt at 125%), so the width this needs is not."""
        return self.fontMetrics().horizontalAdvance(f"{arabize('99')} %") + 20


class ScopeModel(QAbstractTableModel):
    firstRow = Signal(int)

    def __init__(self, select_widget, parent=None):
        super().__init__(parent)
        self.select_widget = select_widget
        self.source = []
        self.size_column = self.percent_column = None
        if self.select_widget.context == 5:
            self.size_column, self.percent_column, self.column_count = (1, 2, 3)
        else:
            if self.select_widget.context == 4:
                self.percent_column, self.column_count = (1, 2)
            else:
                self.column_count = 1

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

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
                if isinstance(book_id, int):
                    if QModelIndex.column() == 0:
                        if int_role == Qt.DisplayRole:
                            if book_id in self.select_widget.new_set:
                                return f"☆ {BookCache.bookName(book_id)}"
                            return BookCache.bookName(book_id)
                    elif int_role == Qt.ToolTipRole:
                        return conditioned(CoreDb().bookBetaka(book_id, True, truncated=True))
                        if int_role == Qt.DecorationRole:
                            return BookCache.bookIcon(book_id, self.select_widget.context)
                        if int_role == Qt.ForegroundRole:
                            if self.select_widget.context > 3:
                                if book_id in self.select_widget.new_set:
                                    return _alertBrush()
                    elif QModelIndex.column() == self.size_column:
                        if int_role == Qt.DisplayRole:
                            return PdfSize.getSize(book_id)
            elif QModelIndex.column() == self.percent_column:
                holder = None
                if self.select_widget.context == 5:
                    if book_id in Across.downloading_pdfs:
                        holder = Across.downloading_pdfs
            elif self.select_widget.context == 4:
                if book_id in Across.importing_books:
                    holder = Across.importing_books
            else:
                if Across.downloading_books.get(book_id, Across.QUEUED) != Across.QUEUED:
                    holder = Across.downloading_books
                if holder:
                    value = holder[book_id]
                    if int_role == Qt.DisplayRole:
                        if value > 0:
                            return f'{arabize(("{value}"))} %'
                elif int_role == Qt.DecorationRole:
                    if value <= 0:
                        return BusySpinner.icon()
                elif int_role == Qt.ToolTipRole and value <= 0:
                    return stageText(value, holder)
        else:
            if QModelIndex.column() == 0:
                if int_role == Qt.DecorationRole:
                    return self.scopeIcon(book_id)
                if int_role in {Qt.DisplayRole, Qt.ToolTipRole}:
                    return self.scopeDiscription(book_id)

    def scopeIcon(self, params):
        ico = params.split('|')[0]
        if ico == 'category':
            ico = 'book'
        return Icon.icon(f":/icons/{ico}.png")

    def scopeDiscription(self, params):
        pieces = params.split('|')
        item_type = pieces[0]
        if item_type == 'category':
            category = self.tr('Category: ') + CoreDb().categoryName(pieces[1])
            view_type = set(ast.literal_eval(pieces[2]))
            view_count = len(view_type)
            printed = set(ast.literal_eval(pieces[3]))
            print_count = len(printed)
            if not print_count or print_count != 3 or view_count != 6:
                if 1 in view_type or 2 in view_type:
                    if 1 in view_type:
                        category += self.tr(' [Books]')
                    if 2 in view_type:
                        category += self.tr(' [Magazines]')
                    if (1 in printed) ^ (2 in printed):
                        if 1 in printed:
                            category += self.tr(' (Like Printed)')
                        if 2 in printed:
                            category += self.tr(' (Unlike Printed)')
            else:
                if 3 in view_type:
                    category += self.tr(' [Manuscripts]')
                if 4 in view_type:
                    category += self.tr(' [Thesis]')
                if 5 in view_type:
                    category += self.tr(' [electronic]')
                if 6 in view_type:
                    category += self.tr(' [sound]')
            return category
        if item_type == 'author':
            return self.tr('Author: ') + CoreDb().authorName(pieces[1])
        if item_type == 'period':
            return self.tr('Period: ') + arabize(f"{pieces[1]} - {pieces[2]}")
        if item_type == 'favorite':
            return self.tr('favorite: ') + UserDb().favoriteName(pieces[1])


class PreviousSearches(QWidget):

    def __init__(self, select_widget):
        super().__init__()
        self.select_widget = select_widget
        self.list_view = List(self.rowText)
        self.list_view.setAlternatingRowColors(True)
        self.list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_view.setFont(QtFont(['Traditional Naskh', 12, True, False]))
        self.loadList()
        self.list_view.rowClicked.connect(self.loadSearch)
        self.list_view.rowDoubleClicked.connect(self.doSearch)
        self.delete_button = customToolButton(':/icons/delete_file.png', (self.tr('Delete Selected Searches From the List')),
          text_beside=True,
          slot=(self.deleteSelected))
        self.clear_button = customToolButton(':/icons/clear.png', (self.tr('Clear the List')),
          text_beside=True,
          slot=(self.clear))
        lay = customLayout(False, [self.delete_button, self.clear_button, 0])
        self.setLayout(customLayout(True, [self.list_view, 2, lay]))
        self.deleteButtonStatus()
        self.list_view.selectionModel().selectionChanged.connect(self.deleteButtonStatus)

    def loadList(self):
        self.data = UserDb().loadSearchHistory()
        self.list_view.setSource(list(self.data.keys()))

    def rowText(self, source_id):
        return printQuery(self.data[source_id])

    def reinstall(self):
        pass

    def loadSearch(self, _, source_id):
        self.select_widget.loadSearch(self.data[source_id])
        QTimer.singleShot(0, self.list_view.setFocus)

    def doSearch(self, _, source_id):
        self.select_widget.loadSearch(self.data[source_id])
        self.select_widget.box.triggerSearch()

    def deleteButtonStatus(self):
        self.delete_button.setEnabled(True if self.list_view.selectedIndexes() else False)
        self.clear_button.setEnabled(self.list_view.rowCount() != 0)

    def deleteSelected(self):
        if customMessage(self.tr('Delete Searches'), self.tr('Are You Sure That You Want to Delete Selected Searches'), True):
            UserDb().deleteSearchHistory(self.list_view.deleteSelected())
            self.deleteButtonStatus()

    def clear(self):
        if customMessage(self.tr('Delete All Searches'), self.tr('Are You Sure That You Want to Delete All Searches'), True):
            self.list_view.clear()
            UserDb().clearSearchHistory()
            self.deleteButtonStatus()


def filterCategories(text, categories_list):
    if not text:
        return categories_list
    pieces = iso(text).split(' ')
    return [category for category in categories_list if contains(category[3], pieces)]