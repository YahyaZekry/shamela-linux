# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: sidebar.py
from qtpy.QtCore import QTimer, Qt
from qtpy.QtWidgets import QApplication, QWidget, QStackedWidget, QButtonGroup, QTreeWidgetItem, QTreeWidget, QAbstractItemView, QHeaderView, QStyle, QStyledItemDelegate, QStyleOptionViewItem
import dbmanager
from basebookview import Widget, Author
from customs import hLine, NVDA, styledLabel, QtFont, customLayout, LineEdit, customToolButton
from theme import Icon
from search import Searcher
from searchboxes import SearchWidget, SearchType
from settings import Settings
from textmanager import treatSearch
from engine import Query, QueryType, buildFilter
from across import Across

class CustomTree(QTreeWidget):

    def __init__(self, column_count):
        super().__init__()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        if Across.active_theme in frozenset({'modern_light', 'dark'}):
            self.setAllColumnsShowFocus(False)
        self.setIndentation(20)
        self.setHeaderHidden(True)
        self.headerItem().setText(0, '1')
        if Across.active_theme in frozenset({'modern_light', 'dark'}):
            self.setStyleSheet('QTreeView, QTreeWidget { show-decoration-selected: 0; }QTreeView::branch:selected,QTreeView::branch:selected:active,QTreeView::branch:selected:!active,QTreeView::branch:hover,QTreeView::branch:!selected:hover,QTreeWidget::branch:selected,QTreeWidget::branch:selected:active,QTreeWidget::branch:selected:!active,QTreeWidget::branch:hover,QTreeWidget::branch:!selected:hover { background: transparent; }')
        self.setColumnCount(column_count)
        self.header().setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(False)
        if Across.active_theme in frozenset({'modern_light', 'dark'}):
            self.setItemDelegate(_CompactTreeItemDelegate(self))

    def focusInEvent(self, event):
        NVDA.say('شجرة العناوين')
        super().focusInEvent(event)


class _CompactTreeItemDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        if not option.state & (QStyle.State_Selected | QStyle.State_MouseOver):
            return super().paint(painter, option, index)
        compact_option = QStyleOptionViewItem(option)
        self.initStyleOption(compact_option, index)
        compact_option.rect = self._compactRect(compact_option)
        style = compact_option.widget.style() if compact_option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, compact_option, painter, compact_option.widget)

    def _compactRect(self, option):
        rect = option.rect
        style = option.widget.style() if option.widget else QApplication.style()
        text_width = option.fontMetrics.horizontalAdvance(option.text)
        icon_width = 0
        if not option.icon.isNull():
            icon_width = option.decorationSize.width() or style.pixelMetric(QStyle.PM_SmallIconSize, option, option.widget)
        else:
            indicator_width = 0
            if option.features & QStyleOptionViewItem.HasCheckIndicator:
                indicator_width = style.pixelMetric(QStyle.PM_IndicatorWidth, option, option.widget)
            h_margin = style.pixelMetric(QStyle.PM_FocusFrameHMargin, option, option.widget) + 6
            compact_width = min(rect.width(), text_width + icon_width + indicator_width + h_margin * 2)
            compact_rect = rect.adjusted(0, 0, 0, 0)
            if option.direction == Qt.RightToLeft:
                compact_rect.setLeft(rect.right() - compact_width + 1)
            else:
                compact_rect.setWidth(compact_width)
        return compact_rect


class SideBar(QWidget):

    def __init__(self, owner, search_info=None):
        super().__init__()
        self.owner = owner
        self.search_info = search_info
        self.pages = QStackedWidget()
        self.titlesWidget = self.searchPanel = self.scripts = self.category = self.author = None
        self.group = QButtonGroup()
        icons = ('treeview', 'search_book', 'scripts', 'books', 'authors')
        texts = (self.tr('Titles'), self.tr('Search in this Book'), self.tr('Other Scripts for the Book'),
         self.tr('Books in the Same Category'), self.tr('Books of the author'))
        slots = (self.showTitles, self.showSearch, self.showScripts, self.showCategory, self.showAuthor)
        self.titleButton = self.searchButton = self.scriptButton = None
        buttons = []
        for i in range(5):
            button = customToolButton(tooltip=(texts[i]), icon=f":/icons/{icons[i]}.png", slot=(slots[i]), checkable=True, iconsize=20)
            button.setFixedSize(31, 31)
            buttons.append(button)
            self.group.addButton(button)
            if i == 0:
                button.setChecked(True)
                self.titleButton = button
            elif i == 1:
                self.searchButton = button
            elif i == 2:
                self.scriptButton = button

        lay = customLayout(False, buttons + [0])
        self.setLayout(customLayout(True, [lay, self.pages], margins=0))
        self.showTitles()
        self.pages.currentChanged.connect(self.viewChanged)

    def focusResult(self):
        self.showSearch(nofocus=True)
        self.searchPanel.result_view.setFocus()

    def viewChanged(self):
        book_id = self.owner.book_id
        if book_id:
            script = True if dbmanager.CoreDb().mainScript(book_id) else False
            self.scriptButton.setVisible(script)
            if not script:
                if self.pages.currentWidget() == self.scripts:
                    self.showTitles()
            self.pages.currentWidget().setBook(book_id)

    def showTitles(self):
        if not self.titlesWidget:
            self.titlesWidget = TitlesWidget(self.owner)
            self.pages.addWidget(self.titlesWidget)
        if not self.titleButton.isChecked():
            self.titleButton.setChecked(True)
        self.pages.setCurrentWidget(self.titlesWidget)

    def searchInfo(self, context_id):
        if self.searchPanel:
            return self.searchPanel.getInfo(context_id)

    def showSearch(self, nofocus=None, search_info=None):
        if not self.searchPanel:
            self.searchPanel = SearchBook(self.owner, search_info)
            self.pages.addWidget(self.searchPanel)
        else:
            self.pages.setCurrentWidget(self.searchPanel)
            if not self.searchButton.isChecked():
                self.searchButton.setChecked(True)
            nofocus or self.searchPanel.boxes.setFocus()

    def showScripts(self):
        if not self.scripts:
            self.scripts = Scripts()
            self.pages.addWidget(self.scripts)
        self.pages.setCurrentWidget(self.scripts)

    def showCategory(self):
        if not self.category:
            self.category = Category()
            self.pages.addWidget(self.category)
        self.pages.setCurrentWidget(self.category)

    def showAuthor(self):
        if not self.author:
            self.author = Author()
            self.pages.addWidget(self.author)
        self.pages.setCurrentWidget(self.author)

    def closeTab(self):
        if self.titlesWidget:
            self.titlesWidget.closeTab()
        if self.searchPanel:
            self.searchPanel.closeTab()


class TitlesWidget(QWidget):

    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self.owner = owner
        self.still_searching = None
        self.titlesTree = CustomTree(1)
        self.searchButton = customToolButton(':/icons/search.png', (self.tr('Search In Titles')), slot=(self.updateSearch), iconsize=20)
        self.searcher = Searcher(no_focus=True)
        self.searcher.display_slot = self.owner.resultClicked
        self.searcher.completed_slot = self.searchCompleted
        self.titlesSearchView = self.searcher.constructViewer(side_view=True)
        self.titlesSearchView.setVisible(False)
        layout = customLayout(True, [self.titlesTree, self.titlesSearchView], margins=0, spacing=0)
        self.titlesSearchBox = LineEdit(digit_policy='ascii', slot=(self.updateSearch), focus_list=(self.titlesSearchView))
        self.titlesTree.setFont(QtFont(Settings.getValue('font_tree')))
        self.titlesSearchBox.textEdited.connect(self.evaluateSearchText)
        self.collapseTreeButton = customToolButton(':/icons/minus.png', (self.tr('Collapse Tree')), slot=(self.collapseTree), iconsize=20)
        self.collapseTreeButton.setEnabled(False)
        lower_layout = customLayout(False, [self.collapseTreeButton, self.titlesSearchBox, self.searchButton], spacing=3, margins=0)
        self.setLayout(customLayout(True, [layout, 2, lower_layout], spacing=0, margins=0))
        self.titlesTree.itemExpanded.connect(self.itemExpanded)
        self.titlesTree.itemCollapsed.connect(self.itemCollapsed)
        self.clicked_id = None
        self.titlesTree.itemSelectionChanged.connect(self.itemSelected)
        self.titlesTree.itemClicked.connect(self.itemSelected)
        self.titlesTree.itemActivated.connect(self.itemSelected)
        self.book_id = None
        self.page_id = None
        self.title_id = None
        self.expanded_items = 0
        self.dictionary = {}
        self.tree_loaded = False

    def searchCompleted(self, _):
        self.still_searching = None
        self.searchButton.setEnabled(True)

    def evaluateSearchText(self):
        text = treatSearch(self.titlesSearchBox.text())
        if not text:
            self.titlesSearchView.setVisible(False)
            self.titlesTree.setVisible(True)
            self.pageIdChanged(self.owner.page_id)
        return text

    def updateSearch(self):
        text = self.evaluateSearchText()
        if text:
            if self.still_searching:
                return
            self.still_searching = True
            self.searchButton.setEnabled(False)
            info = buildFilter(text, True)
            info['scope'] = {self.book_id}
            info['type'] = QueryType.TITLES.value
            query = Query(Across.global_index)
            query.load(info)
            self.searcher.current_id = self.owner.page_id
            self.searcher.current_book = self.owner.book_id
            self.searcher.setQuery(query)
            self.searcher.selected = None
            self.searcher.start()
            self.titlesSearchView.setVisible(True)
            self.titlesTree.setVisible(False)

    def setBook(self, book_id):
        if self.book_id != book_id:
            self.titlesTree.blockSignals(True)
            self.titlesTree.clear()
            self.titlesTree.blockSignals(False)
            self.titlesSearchView.model().setSource([])
            self.titlesSearchView.model().beginResetModel()
            self.titlesSearchView.model().endResetModel()
            self.expanded_items = 0
            self.book_id = book_id
            self.page_id = None
            self.title_id = None
            self.dictionary = {}
            self.tree_loaded = False
        if not self.titlesSearchView.isVisible():
            if self.page_id != self.owner.page_id:
                self.pageIdChanged(self.owner.page_id)

    def closeTab(self):
        self.searcher.stop(2000)

    def loadSubTitles(self, tree_item, title_id):
        results = dbmanager.BookDb(self.book_id).getTitles(title_id)
        nvda = NVDA.isRunning()
        for result in results:
            item = QTreeWidgetItem(tree_item)
            c_text = result[0]
            if result[2]:
                item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
                item.setData(0, Qt.DecorationRole, Icon.icon(':/icons/closed.png'))
                if nvda:
                    c_text = f"{c_text}[مطوي] "
            else:
                item.setData(0, Qt.DecorationRole, Icon.icon(':/icons/leaf.png'))
                self.dictionary.update({result[1]: item})
            item.setText(0, c_text)
            item.setToolTip(0, result[0])
            item.setText(1, str(result[1]))
            self.dictionary.update({result[1]: item})

    def itemExpanded(self, item):
        item.setData(0, Qt.DecorationRole, Icon.icon(':/icons/open.png'))
        if NVDA.isRunning():
            item.setText(0, f"{item.toolTip(0)}[موسع] ")
        if item.childCount() == 0:
            self.loadSubTitles(item, int(item.text(1)))
        if self.titlesTree.indexOfTopLevelItem(item) > -1:
            self.expanded_items += 1
            if self.expanded_items == 1:
                self.collapseTreeButton.setEnabled(True)

    def itemCollapsed(self, item):
        item.setData(0, Qt.DecorationRole, Icon.icon(':/icons/closed.png'))
        if NVDA.isRunning():
            item.setText(0, f"{item.toolTip(0)}[مطوي] ")
        if self.titlesTree.indexOfTopLevelItem(item) > -1:
            self.expanded_items -= 1
            if self.expanded_items == 0:
                self.collapseTreeButton.setEnabled(False)

    def collapseTree(self):
        self.collapseTreeButton.setEnabled(False)
        for i in range(self.titlesTree.topLevelItemCount()):
            self.titlesTree.topLevelItem(i).setExpanded(False)

        self.titlesSearchView.setVisible(False)
        self.titlesTree.setVisible(True)

    def itemSelected(self):
        clicked_id = int(self.titlesTree.selectedItems()[0].text(1))
        if self.clicked_id != clicked_id:
            self.clicked_id = clicked_id
            self.page_id = self.owner.goTitle(clicked_id)
            QTimer.singleShot(250, self.resetClickedId)

    def resetClickedId(self):
        self.clicked_id = None

    def pageIdChanged(self, page_id):
        if not self.tree_loaded:
            self.loadSubTitles(self.titlesTree, 0)
            self.tree_loaded = True
        elif page_id != self.page_id:
            parents = dbmanager.BookDb(self.book_id).getParentIds(page_id, self.title_id)
            if isinstance(parents, int):
                return
                if parents:
                    for parent in reversed(parents):
                        item = self.dictionary[parent]
                        if item.childIndicatorPolicy() == QTreeWidgetItem.ShowIndicator:
                            item.setExpanded(True)

                    self.titlesTree.blockSignals(True)
                    self.titlesTree.setCurrentItem(item)
                    self.page_id = page_id
                    self.title_id = item.text(1)
                    self.titlesTree.blockSignals(False)
            else:
                self.titlesTree.blockSignals(True)
                self.titlesTree.setCurrentItem(self.titlesTree.topLevelItem(0))
                self.titlesTree.blockSignals(False)


class SearchBook(QWidget):

    def __init__(self, owner, search_info):
        super().__init__()
        self.book_id = self.info = None
        self.owner = owner
        self.boxes = SearchWidget(self.triggerSearch)
        self.search_type = SearchType()
        self.searcher = Searcher()
        self.searcher.display_slot = owner.resultClicked
        self.searcher.boxes = self.boxes
        self.query = Query(Across.global_index)
        self.result_view = self.searcher.constructViewer(True)
        self.setLayout(customLayout(True, [self.search_type, 6, hLine(), self.boxes, 6, self.result_view], margins=[1, 1, 1, 0]))
        if search_info:
            self.setBook(owner.book_id)
            self.search_type.load(search_info)
            self.boxes.load(search_info)
            if 'results_hash' in search_info:
                self.query.load(search_info)
                search_info['results'] = self.query.results
                self.triggerSearch(search_info)
        QTimer.singleShot(0, self.boxes.setFocus)

    def setBook(self, book_id):
        if book_id != self.book_id:
            self.book_id = book_id
            self.boxes.setResultsCount('')
            self.query.clear()
            self.info = None
            self.result_view.model().setSource([])
            self.result_view.model().beginResetModel()
            self.result_view.model().endResetModel()

    def getInfo(self, context_id):
        if self.searcher.source:
            row = self.result_view.currentIndex().row()
            return self.query.save({'source':[f"{pieces[0]}-{pieces[1]}" for pieces in self.searcher.source],  'row':row}, context_id=context_id)

    def triggerSearch(self, info):
        self.info = info
        self.search_type.save(info)
        self.info['scope'] = [self.book_id]
        self.query.clear()
        self.query.load(info)
        if self.query.results:
            self.result_view.bypassFirst(info['results']['row'])
        self.searcher.current_id = self.owner.page_id
        self.searcher.current_book = self.owner.book_id
        self.searcher.setQuery(self.query)
        self.searcher.selected = None
        self.boxes.showProgress()
        self.searcher.start()

    def closeTab(self):
        self.searcher.stop(2000)


class Scripts(QWidget):

    def __init__(self):
        super().__init__()
        self.books = Widget()
        self.setLayout(customLayout(True, [self.books], margins=0))

    def setBook(self, book_id):
        book_list, online_set = dbmanager.CoreDb().inScript(book_id)
        self.books.setSource(book_id, book_list, online_set)


class Category(QWidget):

    def __init__(self):
        super().__init__()
        self.label = styledLabel(height=30)
        self.books = Widget()
        self.setLayout(customLayout(True, [self.label, self.books], margins=[1, 1, 1, 0]))

    def setBook(self, book_id):
        category_name, book_list, online_set = dbmanager.CoreDb().inCategory(book_id)
        self.label.setText(category_name)
        self.books.setSource(book_id, book_list, online_set)