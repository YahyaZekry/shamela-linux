# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: searchbiblio.py
from qtpy.QtCore import Signal, Qt, QSize
from qtpy.QtWidgets import QWidget, QStackedWidget, QToolBar, QButtonGroup, QFrame, QRadioButton, QSplitter
from engine import Query, QueryType, getElement, wholeSnippet, buildFilter
from basebookview import Widget
from bookslist import SelectAuthors
from customs import specialSelectRow, customSplitter, styledLabel, customToolButton, flexibleBrowser, hLine, customLayout, LineEdit, ensureChecked
from dbmanager import CoreDb, UserDb
from cache import AuthorCache, BookCache, Hints
from search import Searcher
from searchboxes import SearchWidget
from textmanager import treatSearch, formatHint, arabize
from across import Across
from scaling import scaled_font_size

class Block:
    all_books = []
    online_set = set()
    button_list = []
    author_count = None


def selectRowByValue(view, value):
    source = view.model().source
    row = source.index(value)
    specialSelectRow(view, row)


class InfoSide(QWidget):

    def __init__(self, displayer, position=None, is_search=None):
        super().__init__()
        self.go_function = displayer.go
        displayer.setList(self)
        self.pages = QStackedWidget()
        self.biography_list = self.biblio_list = self.hint_list = None
        self.setMinimumWidth(300)
        toolbar = QToolBar(self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QSize(20, 20))
        self.group = QButtonGroup()
        texts = (
         self.tr('Authors'), self.tr('Books'), self.tr('Hint'))
        icons = ('authors', 'betaka', 'hint')
        slots = (self.showAuthors, self.showBibliography, self.showHint)
        for i in range(3):
            button = customToolButton(text=f" {texts[i]} ", icon=f":/icons/{icons[i]}.png", text_beside=True, slot=(slots[i]), checkable=True)
            button.setStyleSheet('QToolButton {font: bold ' + (f"{scaled_font_size(12)}") + 'pt "Traditional Naskh";}')
            toolbar.addWidget(button)
            Block.button_list.append(button)
            self.group.addButton(button)
            if i == 0:
                button.setChecked(True)

        if is_search:
            self.showAuthors(is_search=is_search)
        else:
            if position:
                self.gotoPosition(position)
            else:
                self.showAuthors()
        self.setLayout(customLayout(True, [customLayout(False, [0, toolbar, 0]), self.pages], margins=0))

    def currentPosition(self):
        return self.pages.currentWidget().currentPosition()

    def gotoPosition(self, position):
        index, value = position
        functions = (self.showAuthors, self.showBibliography, self.showHint)
        functions[index](value)

    def goTree(self):
        self.pages.currentWidget().goTree()

    def showAuthors(self, value=None, is_search=None):
        if not self.biography_list:
            self.biography_list = BiographyList(self.go_function)
            self.pages.addWidget(self.biography_list)
        self.pages.setCurrentWidget(self.biography_list)
        ensureChecked(self.group.buttons()[0])
        self.biography_list.last_value = value if (value and value is not True) else (self.biography_list.last_value or self.biography_list.widget.model.source[0][0])
        if not is_search:
            self.biography_list.goLast()

    def showBibliography(self, value=None):
        if not self.biblio_list:
            self.biblio_list = BookList(self.go_function, 'bibliography', value)
            self.pages.addWidget(self.biblio_list)
        self.pages.setCurrentWidget(self.biblio_list)
        ensureChecked(self.group.buttons()[1])
        self.biblio_list.last_value = value if (value and value is not True) else (self.biblio_list.last_value or self.biblio_list.widget.model.source[0])
        self.biblio_list.goLast()

    def showHint(self, value=None):
        if not self.hint_list:
            self.hint_list = BookList(self.go_function, 'hint')
            self.pages.addWidget(self.hint_list)
        self.pages.setCurrentWidget(self.hint_list)
        ensureChecked(self.group.buttons()[2])
        self.hint_list.last_value = value if (value and value is not True) else (self.hint_list.last_value or self.hint_list.widget.model.source[0])
        self.hint_list.goLast()


class Fake:

    def __init__(self):
        self.context = 1
        self.scope = None

    def isSelection(self, _):
        pass


class BiblioWidget(QWidget):
    closed = Signal(QWidget)

    def __init__(self, saved_value=None):
        super().__init__()
        self.full_title = None
        splitter = QSplitter()
        position = search_info = is_search = None
        if saved_value:
            if 'position' in saved_value:
                position = saved_value['position']
            if 'search' in saved_value:
                search_info = saved_value['search']
                if search_info:
                    is_search = True
        self.info_displayer = InfoDisplayer(search_info)
        self.listwidget = InfoSide((self.info_displayer), position=position, is_search=is_search)
        splitter.setOrientation(Qt.Horizontal)
        splitter.addWidget(self.listwidget)
        splitter.addWidget(self.info_displayer)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setHandleWidth(int(splitter.handleWidth() / 2))
        self.setLayout(customLayout(True, [splitter], margins=[2, 0, 2, 2]))

    def goText(self):
        self.info_displayer.goText()

    def goTree(self):
        self.listwidget.goTree()

    def focusResults(self):
        if self.info_displayer.searchPanel.isVisible():
            self.info_displayer.searchPanel.view.setFocus()

    def save(self, context_id):
        save_dict = {'position': self.listwidget.currentPosition()}
        search_data = self.info_displayer.searchInfo(context_id)
        if search_data:
            save_dict['search'] = search_data
        return [
         'INFO', save_dict]

    def closeTab(self):
        pass

    def closeEvent(self, event):
        self.closed.emit(self)
        event.accept()


class BiographyList(QWidget):

    def __init__(self, go_function):
        super().__init__()
        self.count_label = styledLabel(height=30)
        self.go_function = go_function
        self.widget = SelectAuthors((Fake()), panel=True)
        self.widget.view.go.connect(self.go)
        self.last_value = None
        self.books = Widget(is_author=True)
        split = customSplitter(True, self.widget, self.books, 65)
        self.widget.authors_dict = CoreDb().getAuthors(1, True)
        Block.author_count = len(self.widget.authors_dict)
        self.count_label.setText(self.tr('Number of authors: ') + arabize((f"{Block.author_count}")))
        self.setLayout(customLayout(True, [self.count_label, split]))
        self.widget.setSource()

    def currentPosition(self):
        return (
         0, self.last_value)

    def select(self, value):
        source = self.widget.view.model().source
        source = [author for author, books in source]
        row = source.index(value)
        specialSelectRow(self.widget.view, row)

    def go(self, value):
        self.last_value = value
        self.go_function({'type':'biography',  'id':value})
        books, online_set = CoreDb().allAuthorBooks(value)
        self.books.setSource(0, books, online_set)

    def goLast(self):
        if self.last_value:
            self.go(self.last_value)
            self.select(self.last_value)

    def goTree(self):
        self.widget.view.setFocus()


class BookList(QWidget):

    def __init__(self, go_function, list_type, value=None):
        super().__init__()
        self.count_label = styledLabel(height=30)
        self.go_function = go_function
        self.list_type = list_type
        self.last_value = None
        self.widget = Widget(panel=True)
        self.widget.view.go.connect(self.go)
        self.setLayout(customLayout(True, [self.count_label, self.widget]))
        Block.all_books, Block.online_set = CoreDb().booksPanel()
        if list_type == 'hint':
            hint_set = Hints.hintsBooks()
            hint_books = [book for book in Block.all_books if book in hint_set]
            online_hint_set = Block.online_set.intersection(hint_set)
            self.count_label.setText(self.tr('Number of hits: ') + arabize((f"{len(hint_books)}")))
            self.widget.setSource(0, hint_books, online_hint_set)
        else:
            if list_type == 'bibliography':
                self.count_label.setText(self.tr('Number of books: ') + arabize((f"{len(Block.all_books)}")))
                self.widget.setSource(0, Block.all_books, Block.online_set)

    def currentPosition(self):
        return (
         {'bibliography':1, 
          'hint':2}[self.list_type], self.last_value)

    def select(self, value):
        selectRowByValue(self.widget.view, value)

    def go(self, value):
        self.last_value = value
        self.go_function({'type':self.list_type,  'id':value})

    def goLast(self):
        if self.last_value:
            self.go(self.last_value)
            self.select(self.last_value)

    def goTree(self):
        self.widget.view.setFocus()


class InfoDisplayer(QWidget):

    def __init__(self, search_info=None):
        super().__init__()
        self.pos_dict = self.query = self.search_info = self.form_shown = self.initial_display = None
        self.type_label = styledLabel()
        self.name_label = styledLabel()
        self.sync_button = customToolButton(':/icons/tree.png', (self.tr('Go to the element in list')), slot=(self.goList))
        self.open_button = customToolButton(':/icons/open_book.png', (self.tr('Open the book')), slot=(self.openItem))
        self.open_button.setVisible(False)
        self.info_browser = flexibleBrowser()
        self.searchPanel = SearchPanel(self.go, search_info)
        showSearchButton = customToolButton(':/icons/search2.png', ' ' + self.tr('Search in Data'))
        showSearchButton.setCheckable(True)
        showSearchButton.clicked.connect(lambda: self.searchPanel.toggle(showSearchButton.isChecked()))
        if search_info or UserDb().load('info_search_visible', True):
            showSearchButton.setChecked(True)
        else:
            self.searchPanel.setVisible(False)
        findonpageLineEdit = LineEdit(digit_policy='ascii', slot=(self.searchText), width=180)
        findonpageLineEdit.setPlaceholderText(self.tr('Find on Page'))
        findonpageLineEdit.textChanged.connect(self.searchText)
        upper_layout = customLayout(False, [
         showSearchButton, 0, self.sync_button, 6, self.type_label, 3, self.name_label, 6, self.open_button, 0, findonpageLineEdit])
        info_lay = customLayout(True, [upper_layout, 1, self.info_browser])
        splitter = customSplitter(True, info_lay, self.searchPanel, 75)
        self.setLayout(customLayout(True, [splitter], margins=0))

    def setList(self, list_widget):
        self.list_widget = list_widget

    def goList(self):
        if self.pos_dict:
            if self.pos_dict['type'] == 'bibliography':
                self.list_widget.showBibliography(self.pos_dict['id'])
            else:
                if self.pos_dict['type'] == 'biography':
                    self.list_widget.showAuthors(self.pos_dict['id'])
                else:
                    if self.pos_dict['type'] == 'hint':
                        self.list_widget.showHint(self.pos_dict['id'])

    def openItem(self):
        if self.pos_dict:
            Across.main_window.showBook(self.pos_dict['id'])

    def searchInfo(self, context_id):
        return self.searchPanel.getInfo(context_id)

    def goText(self):
        self.info_browser.setFocus()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.form_shown:
            self.form_shown = True
            if self.pos_dict:
                self.display()

    def go(self, pos_dict=None, search_info=None):
        if not pos_dict:
            if not self.pos_dict:
                return
        if not (self.form_shown or self.initial_display):
            if (
             self.pos_dict, self.search_info) == (pos_dict, search_info):
                return
            self.pos_dict = pos_dict
            self.search_info = search_info
            self.display()
            self.initial_display = True

    def searchText(self, text):
        text = treatSearch(text)
        if text:
            self.search_info = buildFilter(text, True)
        else:
            self.search_info = {}
        self.display()

    def display(self):
        if self.pos_dict['type'] == 'biography':
            self.open_button.setVisible(False)
            author_id = self.pos_dict['id']
            label = self.tr('Authors Biography')
            element = AuthorCache.authorName(author_id)
            author_biblo = CoreDb().authorBiography(author_id=author_id)
            if author_biblo:
                if self.search_info:
                    author_biblo = wholeSnippet(author_biblo, self.search_info)
                self.info_browser.setHtml(author_biblo)
            else:
                self.info_browser.setText('')
        else:
            if self.pos_dict['type'] == 'bibliography':
                book_id = self.pos_dict['id']
                if self.form_shown:
                    self.open_button.setVisible(bool(CoreDb().isOnDisk(book_id)))
                label = self.tr('Books Bibliography')
                element = BookCache.bookName(book_id)
                betaka = CoreDb().bookBetaka(book_id, True, search_info=(self.search_info))
                self.info_browser.setHtml(betaka)
            else:
                if self.pos_dict['type'] == 'hint':
                    book_id = self.pos_dict['id']
                    if self.form_shown:
                        self.open_button.setVisible(bool(CoreDb().isOnDisk(book_id)))
                    label = self.tr('Books Hints')
                    element = BookCache.bookName(book_id)
                    content = getElement('hint', book_id)
                    if self.search_info:
                        content = wholeSnippet(content, self.search_info)
                    if self.search_info:
                        self.info_browser.setUpdatesEnabled(False)
                    self.info_browser.setHtml(formatHint(content, True))
                else:
                    self.type_label.setText(f" {label} ")
                    self.name_label.setText(f" {element} ")
                    if self.search_info:
                        self.info_browser.scrollToAnchor('go')
                        self.info_browser.setUpdatesEnabled(True)
                        if self.form_shown:
                            self.sync_button.setVisible(True)
                    else:
                        self.sync_button.setVisible(False)


class SearchPanel(QWidget):

    def __init__(self, go_function, search_info):
        QWidget.__init__(self)
        self.info = None
        self.query = Query(Across.global_index)
        self.query.type = QueryType.BIBLIO
        self.go_function = go_function
        self.boxes = SearchWidget(self.triggerSearch, True)
        self.searcher = Searcher()
        self.searcher.display_slot = self.showResult
        self.searcher.boxes = self.boxes
        self.searcher.setQuery(self.query)
        self.view = self.searcher.constructViewer()
        v_layout = customLayout(False, [self.boxes, 2, self.view])
        self.setLayout(customLayout(True, [hLine(), v_layout]))
        if search_info:
            self.boxes.load(search_info)
            if 'results_hash' in search_info:
                self.query.load(search_info)
                search_info['results'] = self.query.results
                self.triggerSearch(search_info)

    def getInfo(self, context_id):
        if self.searcher.source:
            row = self.view.currentIndex().row()
            return self.query.save({'source':self.searcher.source,  'row':row}, context_id=context_id)

    def toggle(self, value):
        self.setVisible(value)
        if value:
            self.boxes.setFocus()
        UserDb().save('info_search_visible', value)

    def triggerSearch(self, info):
        self.info = info
        self.info['type'] = QueryType.BIBLIO.value
        self.query.clear()
        self.query.load(info)
        if self.query.results:
            self.view.bypassFirst(info['results']['row'])
        self.searcher.start()

    def showResult(self, row):
        translate = {'a':'biography', 
         'b':'bibliography',  'h':'hint'}
        pos_dict = {'type':translate[row[0]],  'id':int(row[1])}
        search_info = self.query.info()
        self.go_function(pos_dict=pos_dict, search_info=search_info)


class Group(QFrame):

    def __init__(self, option_list):
        super().__init__()
        self.radios = []
        for option in option_list:
            radio = QRadioButton(option)
            if not self.radios:
                radio.setChecked(True)
            self.radios.append(radio)

        self.setLayout(customLayout(True, (self.radios), spacing=3, margins=6))