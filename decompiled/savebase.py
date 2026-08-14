# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: savebase.py
import subprocess, json
from qtpy.QtCore import Qt, QCoreApplication, QSize, QTimer
from qtpy.QtWidgets import QMenu, QButtonGroup, QWidget, QListWidget, QListWidgetItem, QAbstractItemView, QLabel, QToolBar, QStackedWidget
from engine import Query
from dbmanager import UserDb, switchBoth, switchUser
from across import Across
from cache import BookCache, MenCache
from customs import List, QtFont, findInList, customLayout, customMessage, LineEdit, customToolButton, CustomDialog, hLine, matchesShortcutEvent, SEP, singlePhrase, printQuery, printScope, toCheckState, isCheckedState
from theme import Icon
from platformutils import executable_path
from textmanager import arabize

def printSession(session, name=None):
    prefix = f"{name} " if name else ''
    first = session['first']
    second = session['second'] if 'second' in session else None
    if second:
        tab_number = f"[عدد التبويبات: {arabize(len(first[1]))} و {arabize(len(second[1]))}]"
        tabs = first[1] + second[1]
    else:
        tab_number = f"[عدد التبويبات: {arabize(len(first[1]))}]"
        tabs = session['first'][1]
    sessions = []
    for tab in tabs:
        key, value = tab[0], tab[1]
        if key == 'BOOK':
            text = 'كتاب: ' + BookCache.abstractName(value['book'])
        else:
            if key == 'SEARCH':
                text = 'بحث: ' + singlePhrase(value['phrases'])
            else:
                if key == 'INFO':
                    text = 'بحث في بيانات المؤلفين والكتب' if ('search' in value and value['search']) else 'بيانات المؤلفين والكتب'
                else:
                    if key == 'QURAN':
                        text = 'بحث في القرآن الكريم' if 'search' in value else 'القرآن الكريم'
                    else:
                        if key == 'MAN':
                            text = 'ترجمة: ' + MenCache.manShortName(value['id'])
                        else:
                            if key == 'TOROQ':
                                text = QCoreApplication.translate('MainWindow', 'Asaneed Tree')
                            else:
                                if key == 'TAKREEJ':
                                    text = QCoreApplication.translate('MainWindow', 'Takreej Hadeeth')
                                sessions.append(text)

    return f"{prefix}{tab_number}{SEP}{SEP.join(sessions)}"


class Saved(CustomDialog):

    def __init__(self, parent):
        super().__init__(parent=parent, geometry_name='saved', icon=':/icons/saved_search.png')
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        self.setWindowTitle(self.tr('Saved'))
        self.pages = QStackedWidget()
        self.past_session = self.saved_session = self.savedSearch = None
        toolbar = QToolBar(self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QSize(24, 24))
        self.group = QButtonGroup()
        texts = (
         self.tr('Past Sessions'), self.tr('Saved Sessions'), self.tr('Saved Search Results'))
        icons = (':/icons/history.png', ':/icons/save2.png', ':/icons/saved_search.png')
        slots = (self.showSessionHistory, self.showSavedSessions, self.showSavedSearches)
        actions = []
        for i in range(3):
            action = customToolButton(text=(texts[i]), icon=(icons[i]), text_beside=True, slot=(slots[i]), checkable=True)
            toolbar.addWidget(action)
            self.group.addButton(action)
            actions.append(action)

        self.last_page = UserDb().load('saved_page', 0)
        actions[self.last_page].setChecked(True)
        slots[self.last_page]()
        lay = customLayout(False, [0, toolbar, 0])
        self.setLayout(customLayout(True, [2, lay, 1, hLine(), self.pages], margins=0))

    def showSessionHistory(self):
        if not self.past_session:
            self.past_session = PastSession(self)
            self.pages.addWidget(self.past_session)
        self.pages.setCurrentWidget(self.past_session)
        self.last_page = 0

    def showSavedSessions(self):
        if not self.saved_session:
            self.saved_session = SavedSession(self)
            self.pages.addWidget(self.saved_session)
        self.pages.setCurrentWidget(self.saved_session)
        self.last_page = 1

    def showSavedSearches(self):
        if not self.savedSearch:
            self.savedSearch = SavedSearch(self)
            self.pages.addWidget(self.savedSearch)
            Across.results_loaded = True
        self.pages.setCurrentWidget(self.savedSearch)
        self.last_page = 2

    def reloadResults(self):
        self.savedSearch.load()

    def closeEvent(self, event):
        UserDb().save('saved_page', self.last_page)
        super().closeEvent(event)


class PastSession(QWidget):

    def __init__(self, close_me):
        super().__init__()
        self.close_me = close_me
        self.list_view = List(self.printRow)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_view.setAlternatingRowColors(True)
        self.list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_view.setFont(QtFont(['Traditional Naskh', 12, True, False]))
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.showContextMenu)
        self.loadList()
        self.list_view.rowDoubleClicked.connect(self.loadSession)
        self.delete_button = customToolButton(':/icons/delete_file.png', (self.tr('Delete selected sessions from the List')),
          text_beside=True,
          slot=(self.deleteSelected))
        self.clear_button = customToolButton(':/icons/clear.png', (self.tr('Clear the List')),
          text_beside=True,
          slot=(self.clear))
        lay = customLayout(False, [self.delete_button, self.clear_button, 0])
        self.setLayout(customLayout(True, [lay, self.list_view]))
        self.deleteButtonStatus()
        self.list_view.selectionModel().selectionChanged.connect(self.deleteButtonStatus)

    def loadList(self):
        self.data = UserDb().loadSessionHistory()
        self.list_view.setSource(list(self.data.keys()))

    def showContextMenu(self, pos):
        index = self.list_view.indexAt(pos)
        if index:
            menu = QMenu(self.list_view)
            open_action = menu.addAction(self.tr('Open session'))
            separate_action = menu.addAction(self.tr('Open session in a separate window'))
            menu.addSeparator()
            tabs_menu = QMenu(self.tr('Open one tab from the session'))
            tabs_menu.setStyleSheet('QMenu{menu-scrollable: 1;}')
            _id = self.list_view.source[index.row()]
            session = self.data[_id]
            first, second = session['first'], session['second'] if 'second' in session else None
            tabs = first[1] + second[1] if second else session['first'][1]
            lines = printSession(session).splitlines()[1:]
            count = len(lines)
            actions = [tabs_menu.addAction(line.strip()) for line in lines]
            menu.addMenu(tabs_menu)
            selected_action = menu.exec_(self.list_view.mapToGlobal(pos))
            if selected_action:
                if selected_action == open_action:
                    self.loadSession(None, _id)
                else:
                    if selected_action == separate_action:
                        separateSession(session)
                    else:
                        for i in range(count):
                            if selected_action == actions[i]:
                                self.close_me.close()
                                Across.main_window.load(tabs[i], None)
                                break

    def printRow(self, _id):
        return printSession(self.data[_id])

    def loadSession(self, _, _id):
        switchBoth(True)
        self.close_me.close()
        Across.main_window.dual.load(UserDb().sessionById(_id))
        switchBoth(False)

    def deleteButtonStatus(self):
        self.delete_button.setEnabled(True if self.list_view.selectedIndexes() else False)
        self.clear_button.setEnabled(self.list_view.rowCount() != 0)

    def deleteSelected(self):
        if customMessage(self.tr('Delete Sessions'), self.tr('Are You Sure That You Want to Delete Selected Sessions'), True):
            UserDb().deleteSessionHistory(self.list_view.deleteSelected())
            self.deleteButtonStatus()

    def clear(self):
        if customMessage(self.tr('Delete All Sessions'), self.tr('Are You Sure That You Want to Delete All Sessions'), True):
            self.list_view.clear()
            UserDb().clearSessionHistory()
            self.deleteButtonStatus()


def separateSession(session):
    subprocess.Popen(([executable_path()](json.dumps(session))), cwd=(Across.bin_directory))


class SaveBase(QWidget):

    def __init__(self, base, print_function):
        super().__init__()
        self.base = base
        self.printFunction = print_function
        self.has_items_to_save = self.base == 'scope' or self.base == 'session'
        self.list_widget = KeyedListWidget(enter_func=(self.enterPressed))
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setFont(QtFont(['Traditional Naskh', 12, True, False]))
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.showContextMenu)
        self.list_widget.itemDoubleClicked.connect(self.doubleClicked)
        self.nameEdit = LineEdit(slot=(self.editSlot))
        self.deleteButton = customToolButton(':/icons/delete.png', (QCoreApplication.translate('MainWindow', 'Delete')), slot=(self.deleteScope))
        self.renameButton = customToolButton(':/icons/rename2.png', (QCoreApplication.translate('MainWindow', 'Rename')), slot=(self.renameItem))
        self.upButton = customToolButton(':/icons/up.png', (QCoreApplication.translate('MainWindow', 'Move Up')), slot=(self.upElement))
        self.downButton = customToolButton(':/icons/down.png', (QCoreApplication.translate('MainWindow', 'Move Down')), slot=(self.downElement))
        bar = [
         self.deleteButton, self.upButton, self.downButton, self.nameEdit]
        if self.base == 'scope' or self.base == 'session':
            self.saveButton = customToolButton(':icons/save.png', (QCoreApplication.translate('MainWindow', 'Save')), slot=(self.save))
            self.saveButton.setEnabled(False)
            bar.append(self.saveButton)
            label = QCoreApplication.translate('MainWindow', 'Save The open session by the name:') if self.base == 'session' else QCoreApplication.translate('MainWindow', 'Save The current Scope by Name:')
            label = QLabel(label)
        bar.append(self.renameButton)
        bar = customLayout(False, bar)
        vertical = [label, 3, bar, self.list_widget] if (self.base == 'scope' or self.base == 'session') else ([bar, self.list_widget])
        if self.base == 'scope':
            self.list_widget.itemChanged.connect(self.itemChecked)
        self.setLayout(customLayout(True, vertical, margins=[1, 5, 1, 1]))
        self._ids = []
        self.row = self.value = None
        self.load()
        self.list_widget.itemSelectionChanged.connect(self.buttonState)
        self.nameEdit.textChanged.connect(self.buttonState)

    def showContextMenu(self, _):
        pass

    def enterPressed(self):
        pass

    def doubleClicked(self):
        pass

    def selectedIndices(self):
        return sorted([self.list_widget.row(item) for item in self.list_widget.selectedItems()])

    def hasSelection(self):
        if self.list_widget.selectedItems():
            return True
        return False

    def buttonState(self):
        selected_indices = self.selectedIndices()
        if selected_indices:
            self.deleteButton.setEnabled(True)
            self.upButton.setEnabled(selected_indices[0] != 0)
            self.downButton.setEnabled(selected_indices[-1] != self.list_widget.count() - 1)
            self.renameButton.setEnabled(len(selected_indices) == 1)
        else:
            self.upButton.setEnabled(False)
            self.downButton.setEnabled(False)
            self.deleteButton.setEnabled(False)
            self.renameButton.setEnabled(False)
        text = self.nameEdit.text().strip()
        if not text:
            self.renameButton.setEnabled(False)

    def savePosition(self):
        self.row = self.value = None
        if self.list_widget.currentItem():
            self.row = self.list_widget.currentRow()
            self.value = self._ids[self.row]

    def restorePosition(self):
        count = self.list_widget.count()
        if count:
            if self.value:
                found = findInList(self._ids, self.value)
                if found > -1:
                    self.list_widget.setCurrentRow(found)
                else:
                    last_row = count - 1
                    if self.row > last_row:
                        self.row = last_row
                    self.list_widget.setCurrentRow(self.row)
            else:
                self.list_widget.setCurrentRow(0)
        self.row = self.value = None

    def load(self):
        switchBoth(True)
        self.list_widget.blockSignals(True)
        self.savePosition()
        self.list_widget.clear()
        self._ids, values = UserDb().getElements(self.base)
        for _id in self._ids:
            value = values[_id]['json']
            name = f"{values[_id]['name']}"
            self.list_widget.addItem(self.printFunction(value, name))

        self.restorePosition()
        self.list_widget.blockSignals(False)
        self.buttonState()
        switchBoth(False)

    def selectedIds(self):
        return [self._ids[self.list_widget.row(item)] for item in self.list_widget.selectedItems()]

    def deleteScope(self):
        if customMessage(QCoreApplication.translate('MainWindow', 'Delete Scopes'), QCoreApplication.translate('MainWindow', 'Are You Sure That You Want to Delete'), True):
            UserDb().deleteElements(self.base, self.selectedIds())
            self.load()

    def upElement(self):
        self.moveElement(-1)

    def downElement(self):
        self.moveElement(1)

    def moveElement(self, param):
        selected_indices = reversed(self.selectedIndices()) if param > 0 else self.selectedIndices()
        for element_ix in selected_indices:
            UserDb().swapElementOrder(self.base, self._ids[element_ix], self._ids[element_ix + param])
            self.swapElements(element_ix, element_ix + param)

    def swapElements(self, first_id, second_id):
        tmp_value = self._ids[first_id]
        self._ids[first_id] = self._ids[second_id]
        self._ids[second_id] = tmp_value
        tmp_value = self.list_widget.item(first_id).text()
        self.list_widget.item(first_id).setText(self.list_widget.item(second_id).text())
        self.list_widget.item(second_id).setText(tmp_value)
        tmp_value = self.list_widget.item(first_id).isSelected()
        self.list_widget.item(first_id).setSelected(self.list_widget.item(second_id).isSelected())
        self.list_widget.item(second_id).setSelected(tmp_value)

    def currentId(self):
        return self._ids[self.list_widget.currentRow()]

    def renameItem(self):
        current_id = self.currentId()
        user_db = UserDb()
        value = user_db.elementJson(self.base, current_id)
        new_name = user_db.renameElement(self.base, current_id, self.nameEdit.text())
        self.list_widget.item(self.list_widget.currentRow()).setText(self.printFunction(value, new_name))

    def addScope(self, scope_id, value):
        pass

    def editSlot(self):
        try:
            if self.saveButton.isEnabled():
                self.save()
        except:
            if self.renameButton.isEnabled():
                self.renameItem()

    def save(self):
        pass

    def itemChecked(self, item):
        pass


class SavedSession(SaveBase):

    def __init__(self, close_me):
        self.close_me = close_me
        self.total_count = Across.main_window.dual.totalCount()
        super().__init__(base='session', print_function=printSession)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        Across.main_window.dual.tabCountChanged.connect(self.tabsChanged)
        QTimer.singleShot(0, self.nameEdit.setFocus)

    def showContextMenu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item:
            menu = QMenu(self.list_widget)
            save_over = None
            if self.total_count:
                save_over = menu.addAction(self.tr('Save the Open session over this session'))
                menu.addSeparator()
            open_action = menu.addAction(self.tr('Open session'))
            separate_action = menu.addAction(self.tr('Open session in a separate window'))
            menu.addSeparator()
            tabs_menu = QMenu(self.tr('Open one tab from the session'))
            tabs_menu.setStyleSheet('QMenu{menu-scrollable: 1;}')
            _id = self._ids[self.list_widget.row(item)]
            session = UserDb().elementJson('session', _id)
            first, second = session['first'], session['second'] if 'second' in session else None
            tabs = first[1] + second[1] if second else session['first'][1]
            lines = item.text().splitlines()[1:]
            count = len(lines)
            actions = [tabs_menu.addAction(line.strip()) for line in lines]
            menu.addMenu(tabs_menu)
            selected_action = menu.exec_(self.list_widget.mapToGlobal(pos))
            if selected_action:
                if selected_action == open_action:
                    self.loadSession()
                else:
                    if selected_action == separate_action:
                        separateSession(session)
                    else:
                        if selected_action == save_over:
                            self.saveOver(_id)
                        else:
                            for i in range(count):
                                if selected_action == actions[i]:
                                    self.close_me.close()
                                    Across.main_window.load(tabs[i], None)
                                    break

    def saveOver(self, _id):
        switchBoth(True)
        session = Across.main_window.dual.save(f"session_{_id}")
        name = UserDb().updateBaseValue('session', session, _id)
        self.list_widget.blockSignals(True)
        self.list_widget.currentItem().setText(printSession(session, name))
        self.list_widget.blockSignals(False)
        switchBoth(False)

    def save(self):
        switchBoth(True)
        name = self.nameEdit.text().strip()
        new_id = UserDb().baseId('session')
        session = Across.main_window.dual.save(f"session_{new_id}")
        UserDb().saveBaseValue('session', name, session, new_id)
        self.list_widget.blockSignals(True)
        self.list_widget.insertItem(0, printSession(session, name))
        self.list_widget.blockSignals(False)
        self._ids.insert(0, new_id)
        switchBoth(False)

    def tabsChanged(self, total_number):
        self.total_count = total_number
        self.buttonState()

    def buttonState(self):
        text = self.nameEdit.text().strip()
        self.saveButton.setEnabled(True if (text and self.total_count) else False)
        super().buttonState()

    def loadSession(self):
        switchBoth(True)
        self.close_me.close()
        session = UserDb().elementJson('session', self.currentId())
        Across.main_window.dual.load(session)
        switchBoth(False)

    def enterPressed(self):
        self.loadSession()

    def doubleClicked(self):
        self.loadSession()


class SavedSearch(SaveBase):

    def __init__(self, close_me):
        super().__init__(base='search', print_function=printQuery)
        self.close_me = close_me
        self.setLayout(customLayout(True, [6, self]))

    def displaySearch(self):
        self.close_me.close()
        search_info = UserDb().elementJson('search', self.currentId())
        query = Query(Across.global_index)
        query.load(search_info)
        Across.main_window.showSearchResults(query)

    def doubleClicked(self):
        self.displaySearch()

    def enterPressed(self):
        self.displaySearch()


class Fake:

    def __init__(self, base):
        self.base = base

    def dataChanged(self):
        pass

    def selectedIds(self):
        return self.base.selectedIds()

    def hasSelection(self):
        return self.base.hasSelection()


class SavedScope(SaveBase):

    def __init__(self, select_widget):
        self.select_widget = select_widget
        self.books = Fake(self)
        self.blocked = None
        self.has_books = False
        super().__init__(base='scope', print_function=printScope)

    def save(self):
        switchUser(True)
        name = self.nameEdit.text().strip()
        current_scope = self.select_widget.scope.modelScope()
        new_id = UserDb().saveBaseValue('scope', name, current_scope)
        self.list_widget.blockSignals(True)
        item = QListWidgetItem(printScope(current_scope, name))
        self.list_widget.insertItem(0, item)
        item.setCheckState(toCheckState(Qt.Checked))
        self._ids.insert(0, new_id)
        self.list_widget.blockSignals(False)
        switchUser(False)

    def buttonState(self):
        super().buttonState()
        text = self.nameEdit.text().strip()
        self.saveButton.setEnabled(True if (text and self.has_books) else False)
        selected = True if self.selectedIndices() else False
        self.select_widget.isSelection(selected)

    def reinstall(self):
        if self.blocked:
            return
            self.list_widget.blockSignals(True)
            scope_set = set(self.select_widget.scope_widget.model.source)
            self.has_books = scope_set or False
            for i in range(self.list_widget.count()):
                self.list_widget.item(i).setCheckState(toCheckState(Qt.Unchecked))

        else:
            self.has_books = True
            values = {}
            for _id, scope in UserDb().getElementsJson('scope'):
                values[_id] = self.evaluateScope(json.loads(scope), scope_set)

            for i in range(self.list_widget.count()):
                self.list_widget.item(i).setCheckState(toCheckState(values[self._ids[i]]))

        self.list_widget.blockSignals(False)
        self.buttonState()

    def evaluateScope(self, scope, scope_set):
        found = unfound = False
        for element in scope:
            if element in scope_set:
                found = True
            else:
                unfound = True
            if found == unfound == True:
                return toCheckState(Qt.PartiallyChecked)

        if found:
            return toCheckState(Qt.Checked)
        return toCheckState(Qt.Unchecked)

    def itemChecked(self, item):
        self.addScope(self._ids[self.list_widget.row(item)], True if isCheckedState(item.checkState()) else False)

    def addScope(self, scope_id, value):
        scope_content = UserDb().elementJson('scope', scope_id)
        self.select_widget.scope.addScope(scope_content, value)
        self.select_widget.scope_widget.bookChanged()

    def checkSelected(self, value):
        selected_ids = self.selectedIds()
        for scope_id in selected_ids:
            scope_content = UserDb().elementJson('scope', scope_id)
            self.select_widget.scope.addScope(scope_content, value)

        self.select_widget.scope_widget.bookChanged()


class KeyedListWidget(QListWidget):

    def __init__(self, enter_func=None, copy_func=None, find_func=None):
        super().__init__()
        self.enter_func = enter_func
        self.copy_func = copy_func
        self.find_func = find_func

    def keyPressEvent(self, event):
        key = event.key()
        if matchesShortcutEvent(event, 'Ctrl+C'):
            if self.copy_func:
                self.copy_func()
        elif matchesShortcutEvent(event, 'Ctrl+F'):
            if self.find_func:
                self.find_func()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            if self.enter_func:
                self.enter_func()
        super().keyPressEvent(event)