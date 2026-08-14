# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: rijal.py
from collections import defaultdict
from qtpy.QtCore import QCoreApplication, QItemSelectionModel, Qt, QAbstractItemModel, QAbstractTableModel, QModelIndex, Signal, QTimer
from qtpy.QtGui import QClipboard
from qtpy.QtWidgets import QTextBrowser, QLabel, QTreeView, QHeaderView, QAbstractItemView, QWidget, QStackedWidget, QToolBar, QButtonGroup, QListWidget, QListWidgetItem, QRadioButton
from across import Across
from scaling import scaled_font_size
from cache import DataCache, MenCache, EsnadCache, BookCache
from customs import customLayout, QtFont, customSplitter, Icon, alert_brush, customToolButton, hLine, Qtlabel, LineEdit, flexibleBrowser, TableView, TimedLineEdit, fitRow, blanchLabel
from dbmanager import BookDb, Services
from dbmanager import CoreDb
from displaybook import DisplayBook
from engine import getTaraf, getTorok
from settings import Settings
from textmanager import arabize, tip, linear, conditioned, treatSearch, iso

class SearchedBrowser(QWidget):

    def __init__(self):
        super().__init__()
        self.findonpageLineEdit = LineEdit(digit_policy='ascii', slot=(self.searchText), width=170)
        self.findonpageLineEdit.setPlaceholderText(QCoreApplication.translate('MainWindow', 'Find on Page'))
        self.findonpageLineEdit.textChanged.connect(self.searchText)
        self.browser = flexibleBrowser()
        lay = customLayout(False, [0, self.findonpageLineEdit])
        self.setLayout(customLayout(True, [hLine(), lay, self.browser]))
        self.source = None

    def setHtml(self, source):
        self.source = source
        self.browser.setHtml(self.source)

    def searchText(self):
        from engine import buildFilter, wholeSnippet
        will = False
        text = treatSearch(self.findonpageLineEdit.text())
        if text:
            search_info = buildFilter(text, True)
            source = wholeSnippet(self.source, search_info)
            if 'span id=go' in source:
                will = True
        elif will:
            self.browser.setUpdatesEnabled(False)
            self.browser.setHtml(source)
            self.browser.scrollToAnchor('go')
            self.browser.setUpdatesEnabled(True)
        else:
            pos = self.browser.verticalScrollBar().value()
            self.browser.setHtml(self.source)
            self.browser.verticalScrollBar().setValue(pos)


class BiTable(QWidget):
    rowClicked = Signal(int)
    rowDoubleClicked = Signal(int)
    emptyTable = Signal()

    def __init__(self, headers):
        super().__init__()
        self.view = View(self)
        self.model = Model(self)
        self.cache = DataCache(self.data)
        self.view.setModel(self.model)
        self.iso_text = {}
        self.arranged_source = []
        self.checks = (
         QRadioButton(headers[0]), QRadioButton(headers[1]))
        self.checks[1].setChecked(True)
        self.checks[0].toggled.connect(self.review)
        label = QLabel(self.tr('Order: '))
        lay = customLayout(False, [0, label, 0, self.checks[0], 0, self.checks[1], 0], margins=3)
        self.line = TimedLineEdit(search_slot=(self.review))
        self.line.setPlaceholderText(self.tr('Enter at least three letters to search'))
        self.source = []
        self.setLayout(customLayout(True, [lay, self.line, self.view]))
        self.model.setUi(self.view, QtFont(Settings.getValue('font_search_tables')), [(headers[0], 0), (headers[1], 0)], 0)
        self.view.horizontalHeader().resizeSection(1, 40)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def setCurrentChangedFunc(self, func):
        self.view.setCurrentChangedFunc(func)

    def isoText(self):
        if not self.iso_text:
            for _id, text, _ in self.source:
                self.iso_text[_id] = iso(text)

        return self.iso_text

    def setSource(self, source):
        if self.line.text():
            self.line.blockSignals(True)
            self.line.setText('')
            self.line.blockSignals(False)
        self.iso_text = {}
        self.arranged_source = None
        self.source = source
        self.review()

    def review(self):
        """Setting the proper source of the model"""
        if self.source:
            source = self.source if self.checks[0].isChecked() else self.arrangedSource()
            filter_text = iso(self.line.text())
            if len(filter_text) > 2:
                source = [(_id, text, num) for _id, text, num in source if filter_text in self.isoText()[_id]]
            self.model.setSource(source)
            source or self.emptyTable.emit()
        else:
            self.model.setSource([])
            self.emptyTable.emit()

    def arrangedSource(self):
        if not self.arranged_source:
            self.arranged_source = sorted((self.source), key=(lambda x: x[2]), reverse=True)
        return self.arranged_source

    def data(self, row_column_role):
        row, column, role = row_column_role
        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            if column == 0:
                return self.model.source[row][1]
            if column == 1:
                return arabize((f"{self.model.source[row][2]}"))


class Table(QWidget):
    rowClicked = Signal(int)
    rowDoubleClicked = Signal(int)

    def __init__(self):
        super().__init__()
        self.view = View(self)
        self.model = Model(self)
        self.cache = DataCache(self.data)
        self.view.setModel(self.model)
        self.source = []
        self.setLayout(customLayout(True, [self.view], margins=0))

    def setUi(self, font, header_text_width, total):
        self.model.setUi(self.view, font, header_text_width, total)

    def setCurrentChangedFunc(self, func):
        self.view.setCurrentChangedFunc(func)

    def setSource(self, source):
        self.source = source
        self.model.setSource(source)

    def data(self, info):
        pass


class View(TableView):

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.current_changed_func = None

    def setCurrentChangedFunc(self, func):
        self.current_changed_func = func

    def currentChanged(self, current, previous):
        if self.current_changed_func:
            self.current_changed_func(current, previous)
        super().currentChanged(current, previous)

    def enterPressed(self):
        if Settings.getValue('instant_display_result'):
            self.fullDisplay()
        else:
            self.displayCurrent()

    def fullDisplay(self):
        index = self.currentIndex()
        if index.isValid():
            self.widget.rowDoubleClicked.emit(index.row())

    def displayBookPressed(self):
        self.fullDisplay()

    def displayCurrent(self):
        index = self.currentIndex()
        if index.isValid():
            self.widget.rowClicked.emit(index.row())

    def displayRow(self, row=None, keep_position=None, forced=None):
        if row:
            self.widget.rowClicked.emit(row)
        else:
            self.displayCurrent()

    def firstRow(self):
        self.widget.rowClicked.emit(0)
        QTimer.singleShot(0, self.selectFirst)

    def selectFirst(self):
        self.setCurrentIndex(self.model().index(0, 0))
        self.scrollTo(self.model().index(0, 0))


class Model(QAbstractTableModel):

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.source = []
        self.headers = None
        self.column_count = 0

    def setUi(self, view, font, header_text_width, total=None):
        header_data, header_width = zip(*header_text_width)
        self.headers = header_data
        self.column_count = len(header_data)
        view.setFont(font)
        view.horizontalHeader().setFont(font)
        view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        fitRow(view)
        view.verticalHeader().hide()
        if total:
            view.setDimensions(total, list(header_width))

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.source)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if self.headers:
            if int_role == Qt.DisplayRole:
                if Qt_Orientation == Qt.Horizontal:
                    return self.headers[p_int]

    def setSource(self, source):
        self.widget.cache.clear()
        self.beginResetModel()
        if source:
            self.source = source
            self.widget.view.firstRow()
        else:
            self.source = []
        self.endResetModel()

    def data(self, index, role=None):
        if index.isValid():
            row = index.row()
            column = index.column()
            return self.widget.cache.get((row, column, role))


class ManList(QWidget):
    closed = Signal(QWidget)

    def __init__(self, separated=None):
        super().__init__()
        self.separated = separated
        self.full_title = None
        self.adjusted = None
        self.man_list = None
        self.current_man = None
        self.items_dict = {}
        self.mList = QListWidget()
        self.mList.setFont(QtFont(['Traditional Naskh', 12, True, False]))
        self.mList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.man_widget = Man(self.separated)
        self.mList.currentRowChanged.connect(self.itemChanged)
        list_lay = customLayout(True, [self.mList], margins=[0, 0, 0, 2], spacing=0)
        splitter = customSplitter(False, list_lay, self.man_widget, 16)
        self.setLayout(customLayout(False, [6, splitter], margins=0, spacing=0))
        QTimer.singleShot(0, self.mList.setFocus)

    def displayMan(self, man_list, man_id):
        self.loadList(man_list, man_id)

    def loadList(self, man_list, man_id):

        def addItems(list_widget, names):
            for short, long in names:
                item = QListWidgetItem(list_widget)
                item.setText(short)
                item.setToolTip(long)

        if man_list != self.man_list:
            self.mList.blockSignals(True)
            self.mList.clear()
            self.man_list = man_list
            self.items_dict = MenCache.bothNames(self.man_list)
            men_names = [self.items_dict[man_id] for man_id in self.man_list]
            addItems(self.mList, men_names)
        else:
            if man_id:
                if man_id == self.current_man:
                    return
            elif man_id:
                current_index = self.man_list.index(man_id)
            else:
                current_index = 0
                man_id = self.man_list[0]
            self.mList.setCurrentRow(current_index)
            self.goMan(man_id)
            self.mList.blockSignals(False)

    def goMan(self, man_id):
        self.current_man = man_id
        self.man_widget.displayMan(self.man_list, self.current_man)
        self.full_title = MenCache.manShortName(man_id)
        if self.separated:
            Across.main_window.setTabText(self, self.full_title)

    def itemChanged(self, item_index):
        self.goMan(self.man_list[item_index])

    def save(self, _):
        return [
         'MAN', {'id':self.current_man,  'list':self.man_list}]

    def closeTab(self):
        pass

    def closeEvent(self, event):
        self.closed.emit(self)
        event.accept()


class Man(QWidget):

    def __init__(self, separated=None):

        def clickableMan():
            label = Qtlabel()
            color = '#64A261' if Across.active_theme == 'dark' else 'blue'
            label.setStyleSheet('QLabel {font: bold ' + (f"{scaled_font_size(14)}") + 'pt "Traditional Naskh"; color: ' + color + '}')
            label.setOpenExternalLinks(False)
            if not self.separated:
                label.clicked.connect(self.fullDisplay)
            return label

        super().__init__()
        self.separated = separated
        self.man_id = None
        self.pages = QStackedWidget()
        self.name = self.man_list = None
        self.button_list = []
        self.summary = self.tarjama = self.sheokh = self.talameez = self.marweat = None
        toolbar = QToolBar(self)
        self.group = QButtonGroup()
        self.group.setExclusive(True)
        texts = (self.tr('summary'), self.tr('garh_tadeel'), self.tr('Sheokh'), self.tr('Talameez'), self.tr('marweat'))
        slots = (self.showSummary, self.showTarjama, self.showSheokh, self.showTalameez, self.showMarweat)
        for i in range(len(texts)):
            button = customToolButton(text=(texts[i]), text_beside=True, slot=(slots[i]), checkable=True)
            toolbar.addWidget(button)
            self.group.addButton(button)
            self.button_list.append(button)

        self.label = clickableMan()
        if self.separated:
            tool = customLayout(False, [toolbar, 0, self.label, 0, 0], margins=0, spacing=0)
        else:
            fullTarjamaButton = customToolButton(':/icons/rijal.png', (self.tr('display Tarjama in a sepatrate tab')), slot=(self.fullDisplay))
            tool = customLayout(False, [toolbar, 0, self.label, 0, 0, fullTarjamaButton], margins=0, spacing=0)
        vertical = [hLine(), tool, self.pages] if self.separated else [tool, self.pages]
        self.setLayout(customLayout(True, vertical))

    def fullDisplay(self):
        separateMan(self.man_id, self.man_list)

    def viewChanged(self):
        self.pages.currentWidget().setMan(self.man_id)

    def setMan(self, man_id):
        if man_id != self.man_id:
            self.man_id = man_id
            if self.separated:
                self.label.setText(MenCache.manShortName(self.man_id))
            else:
                self.label.setText(f'<a href="link" style="text-decoration:none;">{MenCache.manShortName(self.man_id)}</a>')
            self.label.setToolTip(MenCache.manLongName(man_id))
            self.buttonState(self.man_id)
            if self.pages.currentIndex() == -1:
                self.showSummary()
            else:
                if self.pages.currentWidget().hasSomething(self.man_id):
                    self.pages.currentWidget().setMan(self.man_id)
                else:
                    self.showSummary()

    def displayMan(self, man_list, man_id):
        self.man_list = man_list
        self.setMan(man_id)

    def buttonState(self, man_id):
        self.button_list[1].setVisible(MenCache.hasGarh(man_id))

    def showSummary(self):
        if not self.summary:
            self.summary = Summary()
            self.pages.addWidget(self.summary)
        self.summary.setMan(self.man_id)
        self.pages.setCurrentWidget(self.summary)
        self.button_list[0].setChecked(True)

    def showTarjama(self):
        if not self.tarjama:
            self.tarjama = Tarjama()
            self.pages.addWidget(self.tarjama)
        self.tarjama.setMan(self.man_id)
        self.pages.setCurrentWidget(self.tarjama)
        self.button_list[1].setChecked(True)

    def showSheokh(self):
        if not self.sheokh:
            self.sheokh = People(True)
            self.pages.addWidget(self.sheokh)
        self.sheokh.setMan(self.man_id)
        self.pages.setCurrentWidget(self.sheokh)
        self.button_list[2].setChecked(True)

    def showTalameez(self):
        if not self.talameez:
            self.talameez = People(False)
            self.pages.addWidget(self.talameez)
        self.talameez.setMan(self.man_id)
        self.pages.setCurrentWidget(self.talameez)
        self.button_list[3].setChecked(True)

    def showMarweat(self):
        if not self.marweat:
            self.marweat = Marweat()
            self.pages.addWidget(self.marweat)
        self.marweat.setMan(self.man_id)
        self.pages.setCurrentWidget(self.marweat)
        self.button_list[4].setChecked(True)


def blanchLayout(widget, items):
    """Lay items out inside widget behind the 'no results' card, PdfGui.blanch style:
    when the page's table holds no row at all, the whole content is hidden and the
    card takes its place. Returns (content, blanch) for the page's blanch()."""
    content = QWidget()
    content.setLayout(customLayout(True, items, margins=[1, 1, 1, 0]))
    blanch, _ = blanchLabel(QCoreApplication.translate('MainWindow', 'No results, according to the books included in the service'))
    widget.setLayout(customLayout(True, [content, blanch], margins=0))
    return (content, blanch)


class Marweat(QWidget):

    def __init__(self):
        super().__init__()
        self.man_id = self.book = None
        self.position = PositionWidget(hasbooks=False)
        self.table = BiTable([self.tr('Book'), self.tr('Num')])
        self.table.rowClicked.connect(self.displayItem)
        self.table.emptyTable.connect(self.position.clear)
        splitter = customSplitter(False, self.table, self.position, 30)
        self.content, self.blanch_card = blanchLayout(self, [hLine(), splitter])

    def hasSomething(self, _):
        return True

    def blanch(self, value):
        self.blanch_card.setVisible(value)
        self.content.setVisible(not value)

    def setMan(self, man_id):
        if man_id != self.man_id:
            self.man_id = man_id
            self.book = None
            self.man_list = None
            self.mwaten = EsnadCache.mwaten(self.man_id)
            orderd_books = EsnadCache.books(self.man_id)
            book_set = set(self.mwaten.keys())
            source = [(book, BookCache.abstractName(book), len(self.mwaten[book])) for book in orderd_books if book in book_set]
            self.table.setSource(source)
            self.blanch(not source)

    def displayItem(self, row):
        self.book = self.table.model.source[row][0]
        source = [(self.book, position) for position in sorted(self.mwaten[self.book])]
        self.position.setSource(source, 'man', [self.man_id])


class Summary(SearchedBrowser):

    def __init__(self):
        super().__init__()
        self.man_id = None

    def hasSomething(self, _):
        return True

    def setMan(self, man_id):
        if man_id != self.man_id:
            self.setHtml(MenCache.displaySummary(man_id))


class Tarjama(SearchedBrowser):

    def __init__(self):
        super().__init__()
        self.man_id = None

    def hasSomething(self, man_id):
        return MenCache.hasGarh(man_id)

    def setMan(self, man_id):
        if man_id != self.man_id:
            self.setHtml(MenCache.displayGarh(man_id))


class People(QWidget):

    def __init__(self, is_sheokh):
        super().__init__()
        self.is_sheokh = is_sheokh
        self.man_id = None
        self.method = EsnadCache.sheokh_pos if self.is_sheokh else EsnadCache.talameez_pos
        self.position = PositionWidget(hasbooks=True)
        self.table = BiTable([self.tr('Rawee'), self.tr('Num')])
        self.table.rowClicked.connect(self.displayItem)
        self.table.rowDoubleClicked.connect(self.fullTarjama)
        self.table.emptyTable.connect(self.position.clear)
        splitter = customSplitter(False, self.table, self.position, 30)
        self.content, self.blanch_card = blanchLayout(self, [hLine(), splitter])

    def hasSomething(self, _):
        return True

    def blanch(self, value):
        self.blanch_card.setVisible(value)
        self.content.setVisible(not value)

    def setMan(self, man_id):
        if man_id != self.man_id:
            self.man_id = man_id
            self.man_list = None
            people = EsnadCache.sheokh(self.man_id) if self.is_sheokh else EsnadCache.talameez(self.man_id)
            source = []
            if people:
                names = {}
                for man in people:
                    names[man] = EsnadCache.names(self.man_id)[man]

                names = dict(sorted((names.items()), key=(lambda item: item[1])))
                source = [(key_id, names[key_id], self.method(self.man_id)[0][key_id]) for key_id in names]
            self.table.setSource(source)
            self.blanch(not source)

    def displayItem(self, row):
        man = self.table.model.source[row][0]
        positions = self.method(self.man_id)[1][man]
        self.position.setSource(arrangPosition(positions, False), 'man', [self.man_id, man])

    def fullTarjama(self):
        row = self.table.view.currentIndex().row()
        current_man = self.table.model.source[row][0]
        separateMan(current_man, [item[0] for item in self.table.source])


class Node:

    def __init__(self, node_id, parent=None):
        self.id = node_id
        self.children = []
        self.parent = parent
        if parent:
            parent.add_child(self)

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def child(self, row):
        return self.children[row]

    def childCount(self):
        return len(self.children)

    def row(self):
        if self.parent is not None:
            return self.parent.children.index(self)

    def finalLeaves(self):
        leaves = set()
        Node._addLeaves(self, leaves)
        return leaves

    def log(self, names, level=None):
        output = ''
        if level:
            output += '\t' * level
        else:
            level = 0
        level += 1
        output += Node.displayName(self.id, names) + '\n'
        for child in self.children:
            output += child.log(names, level)

        return output

    @staticmethod
    def _addLeaves(node, leaves):
        if node.childCount() == 0:
            leaves.add(node.id)
        else:
            for child in node.children:
                Node._addLeaves(child, leaves)

    @staticmethod
    def displayName(node_id, names):
        if '-' in node_id:
            book, page = [int(value) for value in node_id.split('-')]
            name = BookCache.abstractName(book)
            if '-' in name:
                name = name.split('-')[0].strip()
            attr = arabize(BookDb(book).getBestAttribute(page, False))
            if Settings.getValue('helal_attr'):
                attr = f"({attr})"
            return f"{name} {attr}"
        return names[int(node_id)]


class MenTreeModel(QAbstractItemModel):
    pathChanged = Signal(list, set)

    def __init__(self, view):
        super().__init__()
        self._rootNode = self.names = None
        self.ancestor_set = set()
        self.view = view

    def setRoot(self, root, names):
        self.names = names
        self.beginResetModel()
        self._rootNode = root
        self.endResetModel()
        self.view.blockSignals(True)
        self.expandIfOne()
        self.view.blockSignals(False)

    def expandIfOne(self, index=QModelIndex()):
        node = self.getNode(index)
        self.view.setExpanded(index, True)
        if node.childCount() == 1:
            self.expandIfOne(self.index(0, 0, index))
        else:
            self.view.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)
            self.currentChanged(index)

    def continueExpansion(self, index):
        node = self.getNode(index)
        self.view.setExpanded(index, True)
        if node.childCount() == 1:
            self.expandIfOne(self.index(0, 0, index))

    def rowCount(self, parent):
        if self._rootNode:
            if not parent.isValid():
                parentNode = self._rootNode
            else:
                parentNode = parent.internalPointer()
            return parentNode.childCount()
        return 0

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if index.isValid():
            if index.column() == 0:
                node = index.internalPointer()
                if role == Qt.DisplayRole or role == Qt.ToolTipRole:
                    return Node.displayName(node.id, self.names)
                if role == Qt.DecorationRole:
                    if '-' in node.id:
                        return BookCache.bookIcon(int(node.id.split('-')[0]))
                    return Icon.icon(':/icons/rijal.png')
                else:
                    if role == Qt.ForegroundRole:
                        if index in self.ancestor_set:
                            return alert_brush()

    def currentChanged(self, index):
        node = self.getNode(index)
        if node:
            up_list = []
            leaves = node.finalLeaves()
            old_ancestors = self.ancestor_set
            self.ancestor_set = set()
            while index.isValid():
                self.ancestor_set.add(index)
                up_list.append(self.getNode(index).id)
                index = index.parent()

            for idx in old_ancestors | self.ancestor_set:
                if idx.isValid():
                    self.dataChanged.emit(idx, idx)

            self.pathChanged.emit(up_list, leaves)

    def parent(self, index):
        node = self.getNode(index)
        parentNode = node.parent
        if parentNode is None or parentNode == self._rootNode:
            return QModelIndex()
        row = parentNode.row()
        if row is None:
            return QModelIndex()
        return self.createIndex(row, 0, parentNode)

    def index(self, row, column, parent):
        parentNode = self.getNode(parent)
        childItem = parentNode.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        return QModelIndex()

    def getNode(self, index):
        if index.isValid():
            node = index.internalPointer()
            if node:
                return node
        return self._rootNode


class MenTreeView(QTreeView):

    def __init__(self):
        super().__init__()
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setIndentation(20)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.setHeaderHidden(True)
        self.expanded.connect(self.continueExpansion)

    def currentChanged(self, current, previous):
        model = self.model()
        if model:
            model.currentChanged(current)
        super().currentChanged(current, previous)

    def continueExpansion(self, index):
        self.model().continueExpansion(index)


class PositionWidget(QWidget):

    def __init__(self, hasbooks):
        super().__init__()
        self.service_name = self.service_list = self.s_row = None
        self.position_table = PositionTable(hasbooks)
        self.position_table.setCurrentChangedFunc(self.hi)
        self.display = DisplayBook(off_features={'minimal'})
        self.holder = QTextBrowser()
        self.content = customSplitter(True, self.display, self.position_table, 40)
        self.setLayout(customLayout(True, [self.content, self.holder]))
        self.position_table.rowClicked.connect(self.displayRow)
        self.position_table.rowDoubleClicked.connect(self.fullDisplay)

    def clear(self):
        self.service_name = self.service_list = self.s_row = None
        self.position_table.setSource([])
        self.holder.setVisible(True)
        self.content.setVisible(False)

    def displayRow(self, row):
        self.holder.setVisible(False)
        self.content.setVisible(True)
        values = self.position_table.source[row]
        self.display.goService([values[0], values[1], self.service_name, self.service_list])

    def fullDisplay(self, _):
        self.display.newDisplay()

    def hi(self, index, _):
        row = index.row()
        if row == self.s_row:
            self.position_table.view.setStyleSheet('QTableView::item:selected{background-color: #D3D3D3; color: #8B0000;};");')
        else:
            self.position_table.view.setStyleSheet('')

    def setSource(self, positions, service_name, service_list, single=None):
        self.service_name = service_name
        self.service_list = service_list
        self.s_row = None
        if single:
            value = list(single)
            if value in positions:
                self.s_row = positions.index(value)
        self.position_table.setSource(positions, single)


class Bread(QLabel):

    def __init__(self, owner_widget):
        super().__init__()
        self.owner_widget = owner_widget
        self.setAutoFillBackground(True)
        self.setFixedHeight(40)
        self.setStyleSheet('QLabel {background-color: rgb(247,247,247); border-width: 1px; border-style: solid; border-radius: 4px;}')
        self.setMargin(4)
        self.setOpenExternalLinks(False)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.setWordWrap(True)
        self.linkActivated.connect(self.go_link)

    def go_link(self, link):
        man_id = int(link.split('-')[1])
        men = [int(man) for man in self.owner_widget.men if '-' not in man]
        separateMan(man_id, men)


class TorqList(QWidget):
    closed = Signal(QWidget)

    def __init__(self, full=None):
        super().__init__()
        self.full_title = None
        self.hadeeth_id = self.names = self.men = self.up_list = None
        self.label = Bread(self)
        self.iso_men = []
        collapseTreeButton = customToolButton(':/icons/collapse.png', (self.tr('Collapse Tree')), slot=(self.collapseTree))
        expandTreeButton = customToolButton(':/icons/expand.png', (self.tr('Expand Tree')), slot=(self.expandTree))
        self.fullTarjamaButton = customToolButton(':/icons/rijal.png', (self.tr('display Tarjama in a sepatrate tab')), slot=(self.fullDisplayTarjama))
        self.treeView = MenTreeView()
        self.model = MenTreeModel(self.treeView)
        self.treeView.setModel(self.model)
        self.model.pathChanged.connect(self.currentChanged)
        self.position_widget = PositionWidget(hasbooks=True)
        self.copyButton = customToolButton(':/icons/copy.png', (self.tr('Copy The Selected and Offsprings')), slot=(self.log))
        self.copyButton.setVisible(False)
        self.display = DisplayBook(off_features={'minimal'})
        if full:
            lower_ribbon = customLayout(False, [collapseTreeButton, expandTreeButton, 0, self.copyButton, 3,
             self.fullTarjamaButton])
        else:
            fullDisplayButton = customToolButton(':/icons/toroq.png', (self.tr('display Tree in a sepatrate tab')), slot=(self.fullDisplay))
            lower_ribbon = customLayout(False, [collapseTreeButton, expandTreeButton, 0, self.copyButton, 3,
             self.fullTarjamaButton, 3, fullDisplayButton])
        lay = customLayout(True, [self.treeView, 1, lower_ribbon])
        label = customLayout(False, [1, self.label], margins=0)
        splitter = customSplitter(False, lay, self.position_widget, 35)
        self.setLayout(customLayout(True, [label, 1, splitter]))

    def save(self, _):
        return ['TOROQ', {'hadeeth': self.hadeeth_id}]

    def fullDisplay(self):
        separateTree(self.hadeeth_id)

    def expandTree(self):
        self.treeView.expandAll()

    def fullDisplayTarjama(self):
        man_id = self.model.getNode(self.treeView.currentIndex()).id
        if not man_id.isdigit():
            man_id = self.model.getNode(self.treeView.selectedIndexes()[0]).id
        if '-' not in man_id:
            man_id = int(man_id)
            men = [int(man) for man in self.men if '-' not in man]
            separateMan(man_id, men)

    def log(self):
        node = self.model.getNode(self.treeView.currentIndex())
        q = QClipboard()
        q.clear()
        q.setText(node.log(self.names))

    def collapseTree(self):
        self.treeView.collapseAll()
        self.model.expandIfOne()

    def currentChanged(self, up_list, leavs_set):
        self.up_list = up_list
        self.updateLabel(up_list)
        positions = arrangPosition([[int(piece) for piece in leaf.split('-')] for leaf in leavs_set], True)
        self.position_widget.setSource(positions, 'man', self.up_list)
        value = '-' not in up_list[0] if up_list else False
        self.fullTarjamaButton.setVisible(value)
        self.copyButton.setVisible(True)

    def setHadeeth(self, hadeeth_id):
        if self.hadeeth_id != hadeeth_id:
            self.hadeeth_id = hadeeth_id
            asaneed = [esnad[2].split(' ') + [f"{esnad[0]}-{esnad[1]}"] for esnad in getTorok(self.hadeeth_id)]
            nodes = {'': Node('Tree')}
            self.men = set()
            for esnad in asaneed:
                parent_key = ''
                for man in esnad:
                    if '-' not in man:
                        self.men.add(man)
                    key = f"{parent_key} {man}".strip()
                    if key not in nodes:
                        nodes[key] = Node(man, nodes[parent_key])
                    parent_key = key

            self.names = MenCache.shortNames(self.men)
            self.model.setRoot(nodes[''], self.names)

    def updateLabel(self, up_list):
        display = []
        for node_id in up_list:
            name = Node.displayName(node_id, self.names)
            if '-' in node_id:
                display.append(name)
            else:
                display.append(f'<a href="inr://man-{node_id}" style="text-decoration:none;">{name}</a>')

        label = " <font color='brown' size=4><b>»</b></font> ".join(display)
        self.label.setText(label)

    def closeTab(self):
        pass

    def closeEvent(self, event):
        self.closed.emit(self)
        event.accept()


class PositionTable(Table):

    def __init__(self, hasbooknames):
        super().__init__()
        self.hasbooknames = hasbooknames
        font = QtFont(Settings.getValue('font_search_tables'))
        if self.hasbooknames:
            headers, total = [
             (
              self.tr('No.'), 45),
             (
              self.tr('Book'), 200),
             (
              self.tr('Taraf'), 0),
             (
              self.tr('Title'), 210),
             (
              self.tr('Attribute'), 80)], 1181
            self.book_coulmn, self.taraf_column, self.title_column, self.attribute_column = (1,
                                                                                             2,
                                                                                             3,
                                                                                             4)
        else:
            headers, total = [
             (
              self.tr('No.'), 45),
             (
              self.tr('Taraf'), 0),
             (
              self.tr('Title'), 210),
             (
              self.tr('Attribute'), 80)], 1181
            self.book_coulmn, self.taraf_column, self.title_column, self.attribute_column = (None,
                                                                                             1,
                                                                                             2,
                                                                                             3)
        self.s_row = None
        self.setUi(font, headers, total)

    def setSource(self, source, single=None):
        self.s_row = None
        if single:
            value = list(single)
            if value in source:
                self.s_row = source.index(value)
        super().setSource(source)

    def data(self, row_column_role):
        row, column, role = row_column_role
        book = self.source[row][0]
        page = self.source[row][1]
        if role == Qt.DisplayRole:
            if column == 0:
                return arabize((f"{row + 1}"))
                if column == self.book_coulmn:
                    return BookCache.abstractName(book)
                if column == self.taraf_column:
                    return linear(getTaraf(book, page))
                if column == self.title_column:
                    return BookDb(book).getTitle(page)
                if column == self.attribute_column:
                    return arabize(BookDb(book).getBestAttribute(page, False))
            else:
                pass
        if role == Qt.ForegroundRole:
            if row == self.s_row:
                return alert_brush()
        else:
            if role == Qt.ToolTipRole:
                if column == self.book_coulmn:
                    return conditioned(CoreDb().bookBetaka(book, True, truncated=True))
                if column == self.taraf_column:
                    return linear(getTaraf(book, page))
                if column == self.title_column:
                    return tip(BookDb(book).getTitle(page))
                if column == self.attribute_column:
                    return tip(arabize(BookDb(book).getBestAttribute(page, True)))
            elif role == Qt.DecorationRole:
                if column == self.book_coulmn:
                    return BookCache.bookIcon(book)


def arrangPosition(positions, is_tuples):
    if is_tuples:
        pos = defaultdict(list)
        for book, page in positions:
            pos[book].append(page)

        arranged = CoreDb().arrangeBooks(set(pos.keys()))
    else:
        pos = positions
        arranged = CoreDb().arrangeBooks(set(positions.keys()))
    final = []
    for book in arranged:
        pages = sorted(pos[book])
        final += [[book, page] for page in pages]

    return final


class Takreej(QWidget):
    closed = Signal(QWidget)

    def __init__(self, full=None):
        super().__init__()
        self.full_title = None
        self.position_widget = PositionWidget(hasbooks=True)
        self.hadeeth_id = self.single = None
        if full:
            self.setLayout(customLayout(True, [self.position_widget]))
        else:
            newDisplayButton = customToolButton(':/icons/takreej.png', (self.tr('display Takreej in a sepatrate tab')), text_beside=True,
              slot=(self.fullDisplay))
            lay = customLayout(False, [newDisplayButton, 0])
            self.setLayout(customLayout(True, [self.position_widget, lay]))

    def save(self, _):
        return [
         'TAKREEJ', {'hadeeth':self.hadeeth_id,  'single':self.single}]

    def fullDisplay(self):
        separateTakreej(self.hadeeth_id, self.single)

    def setHadeeth(self, hadeeth_id, single=None):
        self.hadeeth_id = hadeeth_id
        self.single = single
        position_tuples = Services.getPositions('hadeeth', key_id=hadeeth_id)
        position_tuples = arrangPosition(position_tuples, True)
        self.position_widget.setSource(position_tuples, 'hadeeth', [hadeeth_id], single)

    def closeTab(self):
        pass

    def closeEvent(self, event):
        self.closed.emit(self)
        event.accept()


def separateTakreej(hadeeth_id, single, pane=None):
    frame = Takreej(True)
    frame.setHadeeth(hadeeth_id, single)
    title = QCoreApplication.translate('MainWindow', 'Takreej Hadeeth')
    Across.main_window.showInTab(frame, icon=(Icon.icon(':/icons/takreej.png')), title=title, tab_tip=title, pane=pane)


def separateMan(man_id, man_list=None, pane=None):
    frame = ManList(separated=True)
    if not man_list:
        man_list = [
         man_id]
    frame.displayMan(man_list, man_id)
    title = MenCache.manShortName(man_id)
    Across.main_window.showInTab(frame, icon=(Icon.icon(':/icons/rijal.png')), title=title, tab_tip=title, pane=pane)


def separateTree(hadeeth_id, pane=None):
    frame = TorqList(True)
    frame.setHadeeth(hadeeth_id)
    title = QCoreApplication.translate('MainWindow', 'Asaneed Tree')
    Across.main_window.showInTab(frame, icon=(Icon.icon(':/icons/toroq.png')), title=title, tab_tip=title, pane=pane)