# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: selectwidget.py
import ast, os
from collections import defaultdict
from threading import Thread
from time import time
from qtpy.QtCore import Qt, QSize, Signal
from qtpy.QtWidgets import QCheckBox, QProgressBar, QAbstractItemView, QRadioButton, QLabel, QWidget, QDialog, QButtonGroup, QToolBar, QStackedWidget, QListWidget, QPushButton, QSizePolicy, QMainWindow
from across import Across
from bookslist import PreviousSearches, SelectPeriod, SelectAuthors, SelectCategories, ShowSearchBooks, ShowHistory, ShowBothDownloads
from cache import BookCache
from customs import ensureChecked, image, customLayout, customMessage, customToolButton, hLine, shortcut, directShortcut, directShortcutLabel, normalizeShortcutLabel, trueLapse
from dbmanager import CoreDb, UserDb
from dirs import pdfPath
from exporter import exportBooks
from favoritetree import FavoriteWidget
from theme import Icon
from savebase import SavedScope
from settings import Settings

def expander(vertical=None):
    w = QWidget()
    if vertical:
        w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
    else:
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    return w


def centered(widget, vertical=None):
    w = QWidget()
    w.setLayout(customLayout((bool(vertical)), [0, widget, 0], margins=0))
    return w


def refreshModel(model):
    model.dataChanged.emit(model.index(0, 0), model.index(model.rowCount() - 1, model.columnCount() - 1))


class ShiftedMain(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_shift = None

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            this_time = time()
            if self.last_shift:
                lapse = this_time - self.last_shift
                if trueLapse(lapse):
                    self.doubleShift()
                    return
            self.last_shift = this_time
        else:
            self.last_shift = None
        super().keyReleaseEvent(event)

    def doubleShift(self):
        pass


class ScopeSet:

    def __init__(self, select_widget):
        self.select_widget = select_widget
        self.clear()
        self.evaluate()

    def clear(self):
        self.categories = set()
        self.authors = set()
        self.periods = set()
        self.favorites = set()
        self.books = set()
        self.green = set()

    def evaluate(self):
        self.select_widget.evaluateAllowed()
        if self.select_widget.context == 4:
            if Settings.getValue('auto_download_books'):
                self.books = self.select_widget.allowed_set
                return
        if self.select_widget.context == 5:
            if Settings.getValue('auto_download_pdf'):
                self.books = self.select_widget.allowed_set
                return
        for book_id in list(self.books):
            if book_id not in self.select_widget.allowed_set:
                self.books.discard(book_id)

    def addBooks(self, books, value):
        if value:
            for book in books:
                self.books.add(book)

        else:
            for book in books:
                self.books.discard(book)

        self.updateGreen()

    def addCategory(self, categories, value, view_type, printed):
        if value:
            for category in categories:
                self.categories.add(f"category|{category}|{view_type}|{printed}")

        else:
            for category in categories:
                self.categories.discard(f"category|{category}|{view_type}|{printed}")

        self.updateGreen()

    def isCategorySelected(self, category, view_type, printed):
        return f"category|{category}|{view_type}|{printed}" in self.categories

    def isAuthorSelected(self, author):
        return f"author|{author}" in self.authors

    def addFavorite(self, favorites, value):
        if value:
            for favorite in favorites:
                self.favorites.add(f"favorite|{favorite}")

        else:
            for favorite in favorites:
                self.favorites.discard(f"favorite|{favorite}")

        self.updateGreen()

    def addAuthor(self, authors, value):
        if value:
            for author in authors:
                self.authors.add(f"author|{author}")

        else:
            for author in authors:
                self.authors.discard(f"author|{author}")

        self.updateGreen()

    def addPeriod(self, period, value):
        if value:
            self.periods.add(f"period|{period}")
        else:
            self.periods.discard(f"period|{period}")
        self.updateGreen()

    def arrangeBooks(self):
        return [book for book in self.select_widget.allowed_list if book in self.books]

    def arrangecategory(self, db):
        elements = defaultdict(list)
        categories = []
        for category in self.categories:
            elements[int(category.split('|')[1])].append(category)

        for i in db.arrangedCategories():
            if i in elements:
                categories += elements[i]

        return categories

    def arrangeAuthors(self, db):
        abstracts = [int(element.split('|')[1]) for element in self.authors]
        return [f"author|{author_id}" for author_id in db.arrangedAuthors() if author_id in abstracts]

    def arrangePeriods(self):
        elements = {}
        for period in self.periods:
            elements[int(period.split('|')[3])] = period

        return [elements[i] for i in sorted(elements)]

    def arrangeFavorites(self):
        abstracts = [int(element.split('|')[1]) for element in self.favorites]
        return [f"favorite|{favorite_id}" for favorite_id in UserDb().arrangedFavorites() if favorite_id in abstracts]

    def modelScope(self):
        model_scope = []
        if self.categories or self.authors:
            db = CoreDb()
            if self.categories:
                model_scope += self.arrangecategory(db)
            if self.authors:
                model_scope += self.arrangeAuthors(db)
        if self.periods:
            model_scope += self.arrangePeriods()
        if self.favorites:
            model_scope += self.arrangeFavorites()
        if self.books:
            model_scope += self.arrangeBooks()
        return model_scope

    def discard(self, item):
        if isinstance(item, int):
            self.books.discard(item)
        else:
            s = item[0]
            if s == 'c':
                self.categories.discard(item)
            else:
                if s == 'a':
                    self.authors.discard(item)
                else:
                    if s == 'p':
                        self.periods.discard(item)
                    else:
                        if s == 'f':
                            self.favorites.discard(item)
        self.updateGreen()

    def flatScope(self):
        bag = CoreDb().extendSet(self.books.union(self.getBag()))
        return [book for book in self.select_widget.allowed_list if book in bag]

    def getBag(self):
        bag = set()
        db = CoreDb()
        if self.categories:
            for category in self.categories:
                pieces = category.split('|')
                category_id, view_type, printed = int(pieces[1]), ast.literal_eval(pieces[2]), ast.literal_eval(pieces[3])
                for book in db.getBooksSet(category_id, self.select_widget.context, view_type, printed):
                    bag.add(book)

        if self.authors:
            author_list = [int(author.split('|')[1]) for author in self.authors]
            for book in db.getAuthorBooksSet(author_list, self.select_widget.context):
                bag.add(book)

        if self.periods:
            for period in self.periods:
                pieces = period.split('|')
                for book in db.getPeriodBooks(pieces[3], pieces[4]):
                    bag.add(book)

        if self.favorites:
            favorite_list = [int(favorite.split('|')[1]) for favorite in self.favorites]
            for book in UserDb().listFavoriteBooks(favorite_list, self.select_widget.allowed_set):
                bag.add(book)

        return bag

    def updateGreen(self):
        self.green = self.getBag()

    def addScope(self, scope_content, value):
        if value:
            for item in scope_content:
                if isinstance(item, int):
                    self.books.add(item)
                else:
                    s = item[0]
                    if s == 'c':
                        self.categories.add(item)
                    elif s == 'a':
                        self.authors.add(item)
                    else:
                        if s == 'p':
                            self.periods.add(item)

        else:
            for item in scope_content:
                if isinstance(item, int):
                    self.books.discard(item)
                else:
                    s = item[0]
                    if s == 'c':
                        self.categories.discard(item)
                    elif s == 'a':
                        self.authors.discard(item)
                    else:
                        if s == 'p':
                            self.periods.discard(item)

        self.updateGreen()


class SelectionHelper(QWidget):

    def __init__(self, select_widget):
        super().__init__()
        self.select_widget = select_widget
        self.check_all = QCheckBox(self.tr('All'))
        self.check_new = QCheckBox(self.tr('New'))
        self.check_updated = QCheckBox(self.tr('Updated'))
        self.check_all.stateChanged.connect(self.allChanged)
        self.check_new.stateChanged.connect(self.newChanged)
        self.check_updated.stateChanged.connect(self.updatedChanged)
        self.setLayout(customLayout(True, [self.check_all, self.check_new, self.check_updated, 6], margins=5))

    def checkAll(self):
        self.check_all.setChecked(True)

    def allChanged(self):
        self.check_new.blockSignals(True)
        self.check_updated.blockSignals(True)
        state = self.check_all.isChecked()
        self.check_new.setChecked(state)
        self.check_updated.setChecked(state)
        self.check_new.blockSignals(False)
        self.check_updated.blockSignals(False)
        checkHelped(self.select_widget, 1, state)

    def newChanged(self):
        state = self.check_new.isChecked()
        self.updateAll(state)
        checkHelped(self.select_widget, 2, state)

    def updatedChanged(self):
        state = self.check_updated.isChecked()
        self.updateAll(state)
        checkHelped(self.select_widget, 3, state)

    def updateAll(self, value):
        if not value:
            self.check_all.blockSignals(True)
            self.check_all.setChecked(False)
            self.check_all.blockSignals(False)

    def clearSelection(self):
        self.check_new.blockSignals(True)
        self.check_updated.blockSignals(True)
        self.check_all.blockSignals(True)
        self.check_new.setChecked(False)
        self.check_updated.setChecked(False)
        self.check_all.setChecked(False)
        self.check_new.blockSignals(False)
        self.check_updated.blockSignals(False)
        self.check_all.blockSignals(False)


class SelectWidget(ShiftedMain):

    def __init__(self, context, box=None, search_type=None):
        super().__init__()
        Across.refresh_set.add(self)
        self.enabled_onselection = []
        self.group_enabled_onselection = []
        self.context = context
        self.new_set = set()
        self.pages = QStackedWidget()
        self.check_uncheck_groups = self.check_uncheck_books = None
        self.box = box
        self.search_type = search_type
        central = QWidget()
        central_list = [
         self.pages]
        if not (self.context == 2 or self.context) == 4 or Settings.getValue('auto_download_books'):
            if not (self.context == 5):
                self.check_uncheck_groups = CheckUncheckGroups(self)
                self.check_uncheck_books = CheckUncheckBooks(self)
                self.message_title = self.tr('Ignore Books')
                self.messages = {2:self.tr('Do You want to exclude the selected books from search, for the future'), 
                 4:self.tr('Do You want to exclude the selected books from download, for the future'), 
                 5:self.tr('Do You want to exclude the selected pdfs from download, for the future')}
                tooltips = {2:self.tr('Exclude the selected books from search, for the future'), 
                 4:self.tr('Exclude the selected books from download, for the future'), 
                 5:self.tr('Exclude the selected pdfs from download, for the future')}
                self.ignoreButton = customToolButton(':/icons/ignore.png', text=(self.tr('Ignore')), tooltip=(tooltips[self.context]),
                  text_beside=True)
                self.ignoreButton.clicked.connect(lambda: ignoreSelected(self))
                self.enabled_onselection.append(self.ignoreButton)
                self.expander = expander()
                self.lower_ribbon = QWidget()
                self.lower_ribbon.setLayout(customLayout(False, [
                 self.check_uncheck_groups, self.expander, self.check_uncheck_books, 3,
                 self.ignoreButton]))
                central_list.append(self.lower_ribbon)
        if context == 3:
            central_list.append(customLayout(False, [BooksAction(self)]))
        else:
            central.setLayout(customLayout(True, central_list))
            self.setCentralWidget(central)
            toolbar = QToolBar(self)
            toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
            toolbar.setMovable(False)
            self.evaluateAllowed()
            if context in frozenset({2, 4, 5}):
                self.scope = ScopeSet(self)
            else:
                self.scope = None
        self.scope_model = self.scope_widget = self.edit_favorites = self.helper = None
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.RightToolBarArea, toolbar)
        toolbar.setIconSize(QSize(55, 42) if Across.active_theme == 'native_light' else QSize(46, 36))
        self.group = QButtonGroup(self)
        texts = (self.tr('Books'), self.tr('Categories'), self.tr('Authors'), self.tr('Periods'), self.tr('Favorites'),
         self.tr('History'), self.tr('Downloads'), self.tr('Scopes'), self.tr('Records'))
        tooltips = (self.tr('Books'), directShortcutLabel((self.tr('Categories')), 'Ctrl+1', separator='     '),
         directShortcutLabel((self.tr('Authors')), 'Ctrl+2', separator='     '), self.tr('Time Periods'), self.tr('Favorites'),
         normalizeShortcutLabel(self.tr('History of open books    Ctr - 3')), self.tr('Downloads'),
         self.tr('Scopes'), self.tr('Record of previous searches'))
        slots = (self.showSearchBooks, self.showCategories, self.showAuthors, self.showPeriod, self.showFavorites, self.showHistory, self.showDownloads, self.showSaved, self.showPrevious)
        icons = ('search-books', 'categories', 'authors', 'calender', 'favorite', 'history',
                 'downloads', 'saved-scope', 'saved_search')
        if self.context > 3:
            buttons = [
             0, 1, 2]
        else:
            if self.context == 3:
                buttons = [
                 0, 1, 2]
            else:
                if self.context == 1:
                    buttons = [
                     0, 1, 2, 4, 5, 
                     6]
                else:
                    if self.context == 2:
                        buttons = list(range(9))
                    else:
                        current_action = 1 if self.context == 1 else 0
                        context_str = str(self.context)
                        if context_str in Across.dialog_state:
                            if Across.dialog_state[context_str] in buttons:
                                current_action = Across.dialog_state[context_str]
                        self.history_names = None
                        for i in buttons:
                            button = customToolButton(icon=f":/icons/{icons[i]}.png", text=(texts[i]), tooltip=(tooltips[i]), checkable=True,
                              text_below=True,
                              slot=(slots[i]))
                            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                            toolbar.addWidget(button)
                            self.group.addButton(button)
                            if i == current_action:
                                button.setChecked(True)
                            if icons[i] == 'search-books':
                                self.search_names = button
                            elif icons[i] == 'categories':
                                self.category_names = button
                            elif icons[i] == 'authors':
                                self.authors_names = button
                            elif icons[i] == 'history':
                                self.history_names = button

                        indicator_icon = ["''", "''", "'control_t'", "'update'", "'pdf_d'"]
                        indicator = image(f":/icons/{indicator_icon[context - 1]}.png", 60)
                        toolbar.addWidget(expander(True))
                        if self.context > 3:
                            self.helper = Settings.getValue('auto_download_books' if self.context == 4 else 'auto_download_pdf') or SelectionHelper(self)
                            toolbar.addWidget(self.helper)
                    toolbar.addWidget(centered(indicator))
                    toolbar.setMinimumHeight(toolbar.sizeHint().height())
                    self.categories = self.authors = self.history = self.favorites = self.search = self.saved = self.downloads = self.period = self.previous = None
                    self.slot = slots[current_action]
                    directShortcut(self, 'Ctrl+1', self.showCategories)
                    directShortcut(self, 'Ctrl+2', self.showAuthors)
                    directShortcut(self, 'Ctrl+3', self.showHistory)

    def loadSearch(self, info):
        self.box.load(info)
        self.search_type.load(info)
        self.scope.clear()
        if 'scope' in info:
            self.scope.addScope(info['scope'], True)
        self.scope_widget.bookChanged()

    def go(self):
        self.slot()

    def getScope(self):
        return self.scope.modelScope()

    def showSelectors(self, value):
        if value == 1:
            self.check_uncheck_groups.setVisible(True)
            self.expander.setVisible(True)
            self.check_uncheck_books.setVisible(False)
            self.ignoreButton.setVisible(False)
            self.lower_ribbon.setVisible(True)
        else:
            if value == 2:
                self.check_uncheck_groups.setVisible(False)
                self.expander.setVisible(False)
                self.check_uncheck_books.setVisible(True)
                self.ignoreButton.setVisible(True)
                self.lower_ribbon.setVisible(True)
            else:
                if value == 3:
                    self.check_uncheck_groups.setVisible(True)
                    self.expander.setVisible(True)
                    self.check_uncheck_books.setVisible(True)
                    self.ignoreButton.setVisible(True)
                    self.lower_ribbon.setVisible(True)
                else:
                    if value == 4:
                        self.lower_ribbon.setVisible(False)

    def killFavorites(self):
        if self.favorites:
            if self.pages.currentWidget() is not self.favorites:
                self.pages.removeWidget(self.favorites)
                del self.favorites
                self.favorites = None

    def evaluateAllowed(self):
        self.allowed_list, self.new_set = CoreDb().allowedExtended(self.context)
        self.allowed_set = set(self.allowed_list)

    def refavorites(self):
        if self.context in frozenset({3, 4}):
            return
        self.killFavorites()
        if self.favorites:
            self.favorites.reinstall()
        if self.context == 2:
            self.scope_widget.bookChanged(refresh_attached=False)

    def killHistory(self):
        if self.history:
            if self.pages.currentWidget() is not self.history:
                self.pages.removeWidget(self.history)
                del self.history
                self.history = None

    def reHistory(self):
        self.killHistory()
        if self.history:
            self.history.reinstall()

    def reinstall(self, hide_only=None):
        if hide_only:
            if self.context != 2:
                return
        elif self.scope:
            self.scope.evaluate()
        else:
            self.evaluateAllowed()
        self.killFavorites()
        count = self.pages.count()
        for i in range(count):
            self.pages.widget(i).reinstall()

        if self.edit_favorites:
            self.edit_favorites.reinstall()
        if self.scope_widget:
            self.scope_widget.bookChanged(refresh_attached=False)

    def showCategories(self):
        Across.dialog_state[self.context] = 1
        if not self.categories:
            self.categories = SelectCategories(self)
            self.pages.addWidget(self.categories)
        self.pages.setCurrentWidget(self.categories)
        self.testSelection()
        if self.check_uncheck_groups:
            self.check_uncheck_groups.changeText(self.tr('Check Selected Categories'), self.tr('Uncheck Selected Categories'))
            self.showSelectors(3)
        self.categories.view.setFocus()
        ensureChecked(self.category_names)

    def showAuthors(self):
        Across.dialog_state[self.context] = 2
        if not self.authors:
            self.authors = SelectAuthors(self)
            self.pages.addWidget(self.authors)
        self.pages.setCurrentWidget(self.authors)
        self.testSelection()
        if self.check_uncheck_groups:
            self.check_uncheck_groups.changeText(self.tr('Check Selected Authors'), self.tr('Uncheck Selected Authors'))
            self.showSelectors(3)
        self.authors.line.setFocus()
        ensureChecked(self.authors_names)

    def showPeriod(self):
        Across.dialog_state[self.context] = 3
        if not self.period:
            self.period = SelectPeriod(self)
            self.pages.addWidget(self.period)
        self.pages.setCurrentWidget(self.period)
        self.testSelection()
        if self.check_uncheck_groups:
            self.showSelectors(4)

    def showSaved(self):
        Across.dialog_state[self.context] = 7
        if not self.saved:
            self.saved = SavedScope(self)
            self.pages.addWidget(self.saved)
            self.scope_widget.scopeChanged.connect(self.saved.reinstall)
            self.saved.reinstall()
        self.pages.setCurrentWidget(self.saved)
        self.testSelection()
        if self.check_uncheck_groups:
            self.check_uncheck_groups.changeText(self.tr('Check Selected Scopes'), self.tr('Uncheck Selected Scopes'))
            self.showSelectors(1)

    def showPrevious(self):
        Across.dialog_state[self.context] = 8
        if not self.previous:
            self.previous = PreviousSearches(self)
            self.pages.addWidget(self.previous)
            self.previous.reinstall()
        self.pages.setCurrentWidget(self.previous)
        if self.check_uncheck_groups:
            self.showSelectors(4)

    def showHistory(self):
        if self.context > 2:
            return
        Across.dialog_state[self.context] = 5
        if not self.history:
            self.history = ShowHistory(self)
            self.pages.addWidget(self.history)
        self.pages.setCurrentWidget(self.history)
        self.testSelection()
        if self.check_uncheck_groups:
            self.showSelectors(2)
        self.history.books.filter_text.setFocus()
        ensureChecked(self.history_names)

    def showDownloads(self):
        Across.dialog_state[self.context] = 6
        if not self.downloads:
            self.downloads = ShowBothDownloads(self)
            self.pages.addWidget(self.downloads)
        self.pages.setCurrentWidget(self.downloads)
        self.testSelection()
        if self.check_uncheck_groups:
            self.showSelectors(2)

    def showSearchBooks(self):
        Across.dialog_state[self.context] = 0
        if not self.search:
            self.search = ShowSearchBooks(self)
            self.pages.addWidget(self.search)
            self.search.books.filter_text.setFocus()
        self.pages.setCurrentWidget(self.search)
        self.testSelection()
        if self.check_uncheck_groups:
            self.showSelectors(2)
        self.search.books.filter_text.setFocus()
        ensureChecked(self.search_names)

    def doubleShift(self):
        self.showSearchBooks()

    def showFavorites(self):
        Across.dialog_state[self.context] = 3
        if not self.favorites:
            self.favorites = FavoriteWidget(self)
            self.pages.addWidget(self.favorites)
        self.pages.setCurrentWidget(self.favorites)
        if self.check_uncheck_groups:
            self.check_uncheck_groups.changeText(self.tr('Check Selected Folders'), self.tr('Uncheck Selected Folders'))
            self.showSelectors(3)

    def attach(self, scope_widget):
        self.scope_widget = scope_widget

    def isSelection(self, value):
        for button in self.enabled_onselection:
            button.setEnabled(value)

    def isGroupSelection(self, value):
        for button in self.group_enabled_onselection:
            button.setEnabled(value)

    def selectedIds(self):
        return self.pages.currentWidget().books.selectedIds()

    def isPdfSelected(self):
        selected_ids = self.selectedIds()
        for book in selected_ids:
            if BookCache.hasPdf(book):
                return True

    def testSelection(self):
        if self.pages.currentWidget():
            if self.context == 3:
                selected_ids = self.selectedIds()
                self.isSelection(len(selected_ids) != 0)
            else:
                try:
                    self.isSelection(self.pages.currentWidget().books.hasSelection())
                    self.isGroupSelection(self.pages.currentWidget().isGroupSelected())
                except:
                    pass


class CheckUncheckBooks(QWidget):

    def __init__(self, select_widget):
        super().__init__()
        self.selectButton = customToolButton(':/icons/check.png', (self.tr('Check Selected Books')), text_beside=True)
        self.deselectButton = customToolButton(':/icons/uncheck.png', (self.tr('UnCheck Selected Books')), text_beside=True)
        self.selectButton.clicked.connect(lambda: checkSelected(select_widget, True))
        self.deselectButton.clicked.connect(lambda: checkSelected(select_widget, False))
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(customLayout(False, [self.selectButton, self.deselectButton, 0]))
        select_widget.enabled_onselection += [self.selectButton, self.deselectButton]


class CheckUncheckGroups(QWidget):

    def __init__(self, select_widget):
        super().__init__()
        self.selectButton = customToolButton(':/icons/check.png', text_beside=True)
        self.deselectButton = customToolButton(':/icons/uncheck.png', text_beside=True)
        self.selectButton.clicked.connect(lambda: selectAll(select_widget, True))
        self.deselectButton.clicked.connect(lambda: selectAll(select_widget, False))
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(customLayout(False, [self.selectButton, self.deselectButton, 0]))
        select_widget.group_enabled_onselection += [self.selectButton, self.deselectButton]

    def changeText(self, check, uncheck):
        self.selectButton.setText(check)
        self.deselectButton.setText(uncheck)
        self.selectButton.setVisible(True)
        self.deselectButton.setVisible(True)


class BooksAction(QWidget):
    export_progress_signal = Signal(float)

    def __init__(self, select_widget):
        super().__init__()
        self.delete_button = customToolButton(':/icons/delete_red.png', tooltip=(self.tr('Delete Selected Books - DEL')), text=(self.tr('Delete Selected Books')), slot=(self.deleteBooks), text_beside=True)
        self.export_progress_current = 0
        directShortcut(self, 'Ctrl+E', self.shortExport)
        shortcut(self, 'Del', self.shortDelete)
        shortcut(self, 'Backspace', self.shortDelete)
        self.checkDoneLabel = QLabel(self.tr('Checked'))
        self.checkDoneLabel.setVisible(False)
        self.exportButton = customToolButton(':/icons/export.png', tooltip=directShortcutLabel((self.tr('Export Selected Books')), 'Ctrl+E', separator=' - '),
          text=(self.tr('Export Selected Books')),
          slot=(self.export),
          text_beside=True)
        self.export_progress = QProgressBar()
        self.export_progress.setMaximumHeight(10)
        self.export_progress.setMaximum(1000)
        self.export_progress.setFixedWidth(110)
        self.export_progress.setVisible(False)
        self.setLayout(customLayout(False, [
         self.delete_button, 0, self.export_progress,
         10, self.exportButton]))
        self.select_widget = select_widget
        self.delete_button.setEnabled(False)
        self.export_progress_signal.connect(self.exportProgress)
        self.is_pdf_selected = None
        select_widget.enabled_onselection += [self.delete_button, self.exportButton]

    def shortExport(self):
        if self.exportButton.isEnabled():
            self.export()

    def shortDelete(self):
        if self.delete_button.isEnabled():
            self.deleteBooks()

    def export(self):
        book_list = self.select_widget.selectedIds()
        self.exportButton.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.export_progress_current = 0
        self.export_progress.setValue(0)
        self.export_progress.setVisible(True)
        Thread(target=exportBooks, args=(book_list, self.export_progress_signal)).start()

    def exportProgress(self, increment):
        if increment == 0:
            self.export_progress.setVisible(False)
            self.exportButton.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.export_progress_current += increment
            self.export_progress.setValue(int(self.export_progress_current))

    def deletePdf(self, book_list):
        if not os.path.isdir(pdfPath()):
            customMessage(self.tr('Pdf Folder'), self.tr('Pdf folder not found'))
            return
        for book_id in book_list:
            BookCache.clear(book_id)

        CoreDb().deletePdf(book_list)
        for widget in Across.refresh_set:
            widget.reinstall()

        Across.main_window.checkPdfIcon()
        Across.main_window.startPdf()

    def deleteBooks(self):
        book_list = self.select_widget.selectedIds()
        for book_id in book_list:
            BookCache.clear(book_id)

        parents, children = CoreDb().siblings(book_list)
        value = DeleteBooks(book_list, (self.select_widget.isPdfSelected()), parent=(self.select_widget)).getValue()
        if value == 4:
            return
            if value == 2:
                self.deletePdf(book_list)
                for widget in Across.refresh_set:
                    widget.reinstall()

                return
            if value == 3:
                self.deletePdf(book_list)
            if parents == children == []:
                CoreDb().deleteBooks(book_list)
                for widget in Across.refresh_set:
                    widget.reinstall()

        else:
            sibling = Sibling(book_list, parents, children, parent=(self.select_widget))
            sibling.show()
        Across.main_window.checkPdfIcon()
        Across.main_window.startBook()


class DeleteBooks(QDialog):

    def __init__(self, book_list, is_pdf_selected, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.tr('Delete Books'))
        self.setMinimumWidth(450)
        self.book_list = book_list
        label = self.tr('Determine what do you want to delete') if is_pdf_selected else self.tr('Are You sure You want to delete books')
        label = QLabel(label)
        text_button = QPushButton(self.tr('Delete Books' if is_pdf_selected else self.tr('Ok')))
        text_button.clicked.connect(self.deleteBooks)
        lay = [0, text_button]
        self.value_selected = 4
        if is_pdf_selected:
            pdf_button = QPushButton(self.tr('Delete pdfs'))
            pdf_button.clicked.connect(self.deletePdfs)
            both_button = QPushButton(self.tr('Delete Books and pdfs'))
            both_button.clicked.connect(self.deleteBoth)
            lay += [20, pdf_button, 20, both_button]
        cancel_button = QPushButton(self.tr('cancel'))
        cancel_button.clicked.connect(self.cancelDeletion)
        lay += [20, cancel_button, 0]
        lay = customLayout(False, lay)
        self.setLayout(customLayout(True, [label, lay], margins=6, spacing=6))

    def deleteBooks(self):
        self.value_selected = 1
        self.accept()

    def deletePdfs(self):
        self.value_selected = 2
        self.accept()

    def deleteBoth(self):
        self.value_selected = 3
        self.accept()

    def cancelDeletion(self):
        self.value_selected = 4
        self.accept()

    def getValue(self):
        self.exec_()
        return self.value_selected


class Sibling(QDialog):

    def __init__(self, book_list, parents, children, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.tr('Delete Books'))
        self.setMinimumWidth(450)
        self.book_list = book_list
        self.radio_only = self.radio_all = None
        layout = [
         6]
        if children:
            self.book_list = list(set(book_list) - set(children))
            child_label = QLabel(self.tr('These books will NOT be deleted, as they are parts from other books. Delete Them First'))
            child_list = Sibling.listWidget(children)
            layout += [child_label, 3, child_list]
        if parents:
            if children:
                layout += [15, hLine()]
            parent_label = QLabel(self.tr('These books have extracted content represented as separate books'))
            parent_list = Sibling.listWidget(parents)
            self.radio_only = QRadioButton(self.tr('Delete The selected book only and keep the extracted books'))
            self.radio_all = QRadioButton(self.tr('Delete The selected book and the extracted books'))
            self.radio_only.setChecked(True)
            layout += [parent_label, 3, parent_list, 3, self.radio_only, self.radio_all]
        del_button = QPushButton(self.tr('Delete'))
        del_button.clicked.connect(self.deleteBooks)
        cancel_button = QPushButton(self.tr('Cancel'))
        cancel_button.clicked.connect(self.close)
        h_lay = customLayout(False, [0, del_button, cancel_button])
        layout += [15, hLine(), h_lay]
        self.setLayout(customLayout(True, layout, margins=6))

    def deleteBooks(self):
        if self.radio_all:
            if self.radio_all.isChecked():
                self.book_list = list(CoreDb().extendSet(set(self.book_list)))
        CoreDb().deleteBooks(self.book_list)
        for widget in Across.refresh_set:
            widget.reinstall()

        self.close()

    @staticmethod
    def listWidget(items):
        list_widget = QListWidget()
        for book_id in items:
            list_widget.addItem(BookCache.bookName(book_id))

        list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        list_widget.setFocusPolicy(Qt.NoFocus)
        return list_widget


def selectAll(select_widget, value, current=None):
    widget = select_widget.pages.currentWidget()

    def members(is_authors):
        if current:
            rows = [
             current]
        else:
            rows = set()
            for index in widget.view.selectedIndexes():
                rows.add(index.row())

        groups = [widget.model.source[row][0] for row in rows]
        if is_authors:
            rows = sorted(rows)
            return (rows, groups)
        return groups

    if select_widget.context == 2:
        if isinstance(widget, SelectCategories):
            select_widget.scope.addCategory(members(False), value, widget.type_set, widget.printed_set)
        else:
            if isinstance(widget, SavedScope):
                widget.checkSelected(value)
            else:
                if isinstance(widget, FavoriteWidget):
                    select_widget.scope.addFavorite(widget.tree.selectedFolders(), value)
                else:
                    if isinstance(widget, SelectAuthors):
                        _, groups = members(True)
                        select_widget.scope.addAuthor(groups, value)
                    else:
                        checkSelected(select_widget, value)
    else:
        if select_widget.context >= 4:
            if hasattr(widget, 'view'):
                books = []
                ids = set()
                for index in widget.view.selectedIndexes():
                    ids.add(widget.model.source[index.row()][0])

                for item_id in ids:
                    for book in widget.getMembers(item_id):
                        books.append(book)

            else:
                books = widget.books.selectedIds()
            select_widget.scope.addBooks(books, value)
        select_widget.scope_widget.bookChanged()
        try:
            refreshModel(widget.model)
        except:
            pass


def checkSelected(select_widget, value):
    widget = select_widget.pages.currentWidget()
    books = widget.books.selectedIds()
    select_widget.scope.addBooks(books, value)
    select_widget.scope_widget.bookChanged()


def ignoreSelected(select_widget):
    value = customMessage(select_widget.message_title, select_widget.messages[select_widget.context], True)
    if value:
        widget = select_widget.pages.currentWidget()
        books = widget.books.selectedIds()
        select_widget.scope_widget.ignoreBooks(books)
        for widget in Across.refresh_set:
            widget.reinstall()


def checkHelped(select_widget, selection_type, value):
    if selection_type == 1:
        if value:
            select_widget.scope.books = set(select_widget.allowed_set)
        else:
            select_widget.scope.books = set()
    else:
        if selection_type == 2:
            current_set = select_widget.new_set
        else:
            current_set = select_widget.allowed_set - select_widget.new_set
        select_widget.scope.addBooks(current_set, value)
    select_widget.scope_widget.bookChanged()