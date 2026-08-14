# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: favoritetree.py
from qtpy.QtCore import Qt, QPersistentModelIndex, QModelIndex
from qtpy.QtGui import QClipboard
from qtpy.QtWidgets import QTableWidgetItem, QWidget, QTreeWidgetItemIterator, QHeaderView, QAbstractItemView, QComboBox, QTreeWidget, QListWidgetItem, QTreeWidgetItem, QListWidget, QTableWidget
from across import Across
from bookslist import BooksWidget
from cache import BookCache
from customs import Icon, customSplitter, hLine, vLine, customLayout, customToolButton, LineEdit, customMessage, fitRow
from dbmanager import UserDb
from textmanager import tip

def ListTable():
    list_table = QTableWidget()
    list_table.setColumnCount(1)
    list_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    list_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    list_table.verticalHeader().hide()
    list_table.setWordWrap(False)
    list_table.horizontalHeader().setHighlightSections(False)
    list_table.setShowGrid(False)
    list_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    list_table.horizontalHeader().hide()
    fitRow(list_table)
    return list_table


class customList(QListWidget):

    def __init__(self, del_key_slot=None, drag_drop_slot=None):
        super().__init__()
        self.del_key_slot = del_key_slot
        self.drag_drop_slot = drag_drop_slot
        if drag_drop_slot:
            self.setAcceptDrops(True)
            self.setDragEnabled(True)
            self.setDragDropMode(QAbstractItemView.InternalMove)
        self.drag_rows = None

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if self.del_key_slot:
            if event.key() == Qt.Key_Delete:
                if self.selectedItems():
                    self.del_key_slot()

    def startDrag(self, supportedActions):
        if self.drag_drop_slot:
            self.drag_rows = sorted([self.indexFromItem(item).row() for item in self.selectedItems()])
        super().startDrag(supportedActions)

    def dropEvent(self, event):
        super().dropEvent(event)
        if self.drag_drop_slot:
            if self.drag_rows:
                dropped_row = self.currentRow()
                max_dropped = dropped_row + len(self.drag_rows) - 1
                old_list = self.drag_rows + [dropped_row, max_dropped]
                old_list = list(range(min(old_list), max(old_list) + 1))
                insertion_point = old_list.index(dropped_row)
                new_list = [i for i in old_list if i not in self.drag_rows]
                new_list[insertion_point:insertion_point] = self.drag_rows
                self.drag_drop_slot(old_list, new_list)
                self.drag_rows = None


class FavoriteWidget(QWidget):

    def __init__(self, select_widget, parent=None):
        super().__init__(parent)
        self.context = select_widget.context
        self.select_widget = select_widget
        select_widget.edit_favorites = self
        self.editable = self.context == 3
        self.tree = TreeWidget(self)
        self.parent_ids = []
        self.favorite_ids = []
        if self.editable:
            self.top_list = customList(self.deleteFavorite, self.dragDrop)
            self.top_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.top_list.itemSelectionChanged.connect(self.parentsState)
            self.top_list.currentRowChanged.connect(self.parentChanged)
            self.top_list.itemDelegate().commitData.connect(self.favoritEdited)
            self.tree.itemDelegate().commitData.connect(self.folderEdited)
            self.books_list = ListTable()
            self.books_list.itemDelegate().commitData.connect(self.bookEdited)
            self.books_list.itemSelectionChanged.connect(self.booksState)
            self.top_list.setMaximumHeight(100)
            self.deleteFavoriteToolButton = customToolButton(':/icons/delete.png', (self.tr('Delete Favorite')), slot=(self.deleteFavorite))
            self.upFavoriteToolButton = customToolButton(':/icons/up.png', (self.tr('Move Up')), slot=(self.upFavorite))
            self.downFavoriteToolButton = customToolButton(':/icons/down.png', (self.tr('Move Down')), slot=(self.downFavorite))
            self.renameFavoriteToolButton = customToolButton(':/icons/rename.png', (self.tr('Rename')), slot=(self.renameFavorite))
            newFavoriteToolButton = customToolButton(':/icons/new_favorite.png', (self.tr('Add Favorite')), slot=(self.newFavorite))
            self.renameFavoriteLineEdit = LineEdit()
            self.parentsState()
            heads_panel = customLayout(False, [self.deleteFavoriteToolButton, self.upFavoriteToolButton,
             self.downFavoriteToolButton,
             0,
             newFavoriteToolButton, self.renameFavoriteLineEdit,
             self.renameFavoriteToolButton])
            self.deleteFolderToolButton = customToolButton(':/icons/delete_folder.png', (self.tr('Delete Folder')), slot=(self.deleteFolders))
            self.upFolderToolButton = customToolButton(':/icons/up.png', (self.tr('Move Up')), slot=(self.tree.moveFoldersUp))
            self.downFolderToolButton = customToolButton(':/icons/down.png', (self.tr('Move Down')), slot=(self.tree.moveFoldersDown))
            self.renameFolderToolButton = customToolButton(':/icons/rename.png', (self.tr('Rename')), slot=(self.renameFolder))
            newFolderToolButton = customToolButton(':/icons/new_folder.png', (self.tr('Add Folder')), slot=(self.newFolder))
            self.newSubfolderToolButton = customToolButton(':/icons/new_subfolder.png', (self.tr('Add Subfolder')), slot=(self.newSubfolder))
            self.renameFolderLineEdit = LineEdit()
            folders_panel = customLayout(False, [self.deleteFolderToolButton, self.upFolderToolButton,
             self.downFolderToolButton,
             0,
             newFolderToolButton, self.newSubfolderToolButton,
             self.renameFolderLineEdit,
             self.renameFolderToolButton])
            transbutton = customToolButton(':/icons/add_f.png', (self.tr('Add')), iconsize=35, slot=(self.addBooks))
            transbutton.setStyleSheet('QToolButton{border:none;background:transparent;padding:2px;}QToolButton:hover{border:none;background:transparent;padding:3px 3px 1px 1px;}QToolButton:pressed{border:none;background:transparent;padding:4px 4px 0px 0px;}')
            transbutton.setEnabled(False)
            select_widget.enabled_onselection.append(transbutton)
            self.deleteBookToolButton = customToolButton(':/icons/delete_file.png', (self.tr('Remove Book From Favorites')),
              slot=(self.deleteBooks))
            self.upBookToolButton = customToolButton(':/icons/up.png', (self.tr('Move Up')), slot=(self.upBook))
            self.downBookToolButton = customToolButton(':/icons/down.png', (self.tr('Move Down')), slot=(self.downBook))
            self.renameBookToolButton = customToolButton(':/icons/rename.png', (self.tr('Rename')), slot=(self.renameBook))
            self.renameBookLineEdit = LineEdit()
            books_panel = customLayout(False, [self.deleteBookToolButton, self.upBookToolButton,
             self.downBookToolButton,
             0,
             self.renameBookLineEdit, self.renameBookToolButton])
            v_layout = customLayout(True, [
             self.top_list, heads_panel, 3, hLine(), 6, self.tree, folders_panel, hLine(), 6,
             self.books_list, 1, books_panel, 1])
            button_layout = customLayout(True, [0, 0, 0, 0, 'transbutton', 0])
            self.setLayout(customLayout(False, [vLine(), button_layout, 1, vLine(), 3, v_layout]))
        else:
            self.fav_combo = QComboBox()
            self.fav_combo.currentIndexChanged.connect(self.parentChanged)
            layout = customLayout(True, [2, self.fav_combo, 2, self.tree])
            self.books = BooksWidget(select_widget, screen='favorite')
            self.tree.itemSelectionChanged.connect(self.setModelSource)
            splitter = customSplitter(False, layout, self.books, 37)
            self.setLayout(customLayout(True, [splitter]))
        self.loadParents()
        if self.editable:
            self.tree.itemSelectionChanged.connect(self.foldersState)
        self.select_widget.testSelection()

    def reinstall(self):
        self.loadParents()

    def setModelSource(self):
        if self.tree.currentItem():
            folder_id = int(self.tree.currentItem().text(1))
            book_list = []
            names_dict = {}
            source = UserDb().getFavoriteBooks(folder_id, self.select_widget.allowed_set)
            for favorite in source:
                book_id = favorite[2]
                if book_id in self.select_widget.allowed_set:
                    book_list.append(book_id)
                    names_dict[book_id] = favorite[1]

            self.books.setSource(book_list, names_dict)

    def addBooks(self):
        book_ids = self.select_widget.selectedIds()
        folder_id = int(self.tree.currentItem().text(1))
        favorite_ids = UserDb().addFavoriteBooks(book_ids, folder_id)
        row = self.books_list.rowCount()
        self.books_list.setRowCount(row + len(book_ids))
        for book_id, favorite_id in zip(book_ids, favorite_ids):
            item = QTableWidgetItem(BookCache.bookIcon(book_id), BookCache.bookName(book_id))
            item.setToolTip(tip(item.text()))
            self.books_list.setItem(row, 0, item)
            self.favorite_ids.append(favorite_id)
            row += 1

        refavorites()

    def loadBooks(self):
        from cache import BookCache
        folder_id = int(self.tree.currentItem().text(1))
        self.books_list.clear()
        self.books_list.setRowCount(0)
        self.favorite_ids = []
        favorite_books = UserDb().getFavoriteBooks(folder_id, self.select_widget.allowed_set)
        if favorite_books:
            count = len(favorite_books)
            self.books_list.setRowCount(count)
            for i, favorite_book in enumerate(favorite_books):
                item = QTableWidgetItem(BookCache.bookIcon(favorite_book[2]), favorite_book[1])
                item.setToolTip(tip(item.text()))
                self.books_list.setItem(i, 0, item)
                self.favorite_ids.append(favorite_book[0])

            self.books_list.item(0, 0).setSelected(True)
        if self.editable:
            self.booksState()

    def foldersState(self):
        if self.tree.currentItem():
            self.loadBooks()
        elif self.editable:
            l = len(self.tree.selectedItems())
            enabled = l == 1
            self.renameFolderToolButton.setEnabled(enabled)
            self.newSubfolderToolButton.setEnabled(enabled)
            if l == 0:
                self.deleteFolderToolButton.setEnabled(False)
                self.upFolderToolButton.setEnabled(False)
                self.downFolderToolButton.setEnabled(False)
            else:
                self.deleteFolderToolButton.setEnabled(True)
                parent = self.tree.currentItem().parent()
                enabled = True
                rows = []
                for item in self.tree.selectedItems():
                    if item.parent() is parent:
                        rows.append(self.tree.indexFromItem(item).row())
                    else:
                        enabled = False
                        break

                if enabled:
                    self.upFolderToolButton.setEnabled(min(rows) != 0)
                    if parent is None:
                        row_count = self.tree.topLevelItemCount()
                    else:
                        row_count = parent.childCount()
                    self.downFolderToolButton.setEnabled(max(rows) != row_count - 1)
                else:
                    self.upFolderToolButton.setEnabled(False)
                    self.downFolderToolButton.setEnabled(False)

    def parentChanged(self, row):
        self.tree.loadFolders(self.parent_ids[row])
        if self.editable:
            self.foldersState()

    def dragDrop(self, old_list, new_list):
        old_ids = [self.parent_ids[i] for i in old_list]
        new_ids = [self.parent_ids[i] for i in new_list]
        UserDb().moveFavorites(old_ids, new_ids)
        self.parent_ids[old_list[0]:old_list[-1] + 1] = new_ids
        self.parentsState()
        refavorites()

    def favoritEdited(self):
        row = self.top_list.currentRow()
        text = self.top_list.currentItem().text()
        UserDb().renameFavorite(self.parent_ids[row], text)
        refavorites()

    def folderEdited(self):
        folder_id = int(self.tree.currentItem().text(1))
        text = self.tree.currentItem().text(0)
        UserDb().renameFavorite(folder_id, text)
        refavorites()

    def bookEdited(self):
        favorite_id = self.favorite_ids[self.books_list.currentItem().row()]
        text = self.books_list.currentItem().text()
        UserDb().renameFavoriteBook(favorite_id, text)
        refavorites()

    def booksState(self):
        rows = sorted([item.row() for item in self.books_list.selectedItems()])
        if rows:
            self.deleteBookToolButton.setEnabled(True)
            self.upBookToolButton.setEnabled(rows[0] != 0)
            self.downBookToolButton.setEnabled(rows[-1] != self.books_list.rowCount() - 1)
            self.renameBookToolButton.setEnabled(len(rows) == 1)
        else:
            self.upBookToolButton.setEnabled(False)
            self.downBookToolButton.setEnabled(False)
            self.deleteBookToolButton.setEnabled(False)
            self.renameBookToolButton.setEnabled(False)

    def parentsState(self):
        selected_indices = self.selectedIndices()
        if selected_indices:
            self.deleteFavoriteToolButton.setEnabled(True)
            self.upFavoriteToolButton.setEnabled(selected_indices[0] != 0)
            self.downFavoriteToolButton.setEnabled(selected_indices[-1] != self.top_list.count() - 1)
            self.renameFavoriteToolButton.setEnabled(len(selected_indices) == 1)
        else:
            self.upFavoriteToolButton.setEnabled(False)
            self.downFavoriteToolButton.setEnabled(False)
            self.deleteFavoriteToolButton.setEnabled(False)
            self.renameFavoriteToolButton.setEnabled(False)

    def loadParents(self):
        self.parent_ids = []
        if self.editable:
            self.top_list.blockSignals(True)
            self.tree.blockSignals(True)
            self.books_list.blockSignals(True)
            self.top_list.clear()
            self.tree.clear()
            self.books_list.clear()
            for favorite_text, favorite_id in UserDb().getFavoritesHeads(self.tr('Favorite')):
                self.addFavorite(favorite_text, favorite_id)

            self.top_list.blockSignals(False)
            self.tree.blockSignals(False)
            self.books_list.blockSignals(False)
            self.top_list.setCurrentRow(0)
        else:
            self.fav_combo.blockSignals(True)
            self.fav_combo.clear()
            for text, favorite_id in UserDb().getFavoritesHeads(self.tr('Favorite')):
                self.fav_combo.addItem(text)
                self.parent_ids.append(favorite_id)

            self.tree.loadFolders(self.parent_ids[0])
            self.fav_combo.blockSignals(False)

    def addFavorite(self, favorite_text, favorite_id=None):
        item = QListWidgetItem(favorite_text)
        self.top_list.addItem(item)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        if not favorite_id:
            favorite_id = UserDb().newFavorite(favorite_text, 0)
        self.parent_ids.append(favorite_id)
        refavorites()
        return item

    def selectedIndices(self):
        return sorted([self.top_list.row(item) for item in self.top_list.selectedItems()])

    def deleteFavorite(self):
        if customMessage(self.tr('Delete Favorites'), self.tr('Are You sure That You Want to Delete'), True):
            selected_indices = self.selectedIndices()
            for ix in reversed(selected_indices):
                self.top_list.takeItem(ix)

            UserDb().deleteFavorites([self.parent_ids[i] for i in selected_indices])
            if self.top_list.count() == 0:
                self.addFavorite(self.tr('Favorite'))
                self.top_list.setCurrentRow(0)
            else:
                self.top_list.setCurrentRow(selected_indices[0] - 1 if selected_indices[0] > 0 else 0)
        refavorites()

    def deleteFolders(self):
        if customMessage(self.tr('Delete Folders'), self.tr('Are You sure That You Want to Delete'), True):
            self.tree.deleteSelected()
            refavorites()

    def deleteBooks(self):
        if customMessage(self.tr('Remove Books'), self.tr('Are You sure That You Want to Remove'), True):
            rows = self.selectedFavoriteRows()
            UserDb().deleteFavoriteBooks([self.favorite_ids[row] for row in rows])
            for row in reversed(rows):
                self.books_list.removeRow(row)
                del self.favorite_ids[row]

            refavorites()

    def copyItems(self):
        books = []
        rows = self.selectedFavoriteRows()
        for row in rows:
            books.append(self.books_list.item(row, 0).text())

        QClipboard().setText('\n'.join(books))

    def upFavorite(self):
        self.moveFavorite(-1)

    def downFavorite(self):
        self.moveFavorite(1)

    def moveFavorite(self, param):
        selected_indices = reversed(self.selectedIndices()) if param > 0 else self.selectedIndices()
        for favorite_ix in selected_indices:
            UserDb().swapFavoriteOrder(self.parent_ids[favorite_ix], self.parent_ids[favorite_ix + param])
            self.swapFavorites(favorite_ix, favorite_ix + param)

        refavorites()

    def selectedFavoriteRows(self):
        return sorted([item.row() for item in self.books_list.selectedItems()])

    def upBook(self):
        self.moveBook(-1)

    def downBook(self):
        self.moveBook(1)

    def moveBook(self, param):
        selected_indices = reversed(self.selectedFavoriteRows()) if param > 0 else self.selectedFavoriteRows()
        for favorite_ix in selected_indices:
            UserDb().swapFavoriteBookOrder(self.favorite_ids[favorite_ix], self.favorite_ids[favorite_ix + param])
            self.swapFavoriteBooks(favorite_ix, favorite_ix + param)

        refavorites()

    def swapFavorites(self, first_id, second_id):
        tmp_value = self.parent_ids[first_id]
        self.parent_ids[first_id] = self.parent_ids[second_id]
        self.parent_ids[second_id] = tmp_value
        tmp_value = self.top_list.item(first_id).text()
        self.top_list.item(first_id).setText(self.top_list.item(second_id).text())
        self.top_list.item(second_id).setText(tmp_value)
        tmp_value = self.top_list.item(first_id).isSelected()
        self.top_list.item(first_id).setSelected(self.top_list.item(second_id).isSelected())
        self.top_list.item(second_id).setSelected(tmp_value)

    def swapFavoriteBooks(self, first_id, second_id):
        tmp_value = self.favorite_ids[first_id]
        self.favorite_ids[first_id] = self.favorite_ids[second_id]
        self.favorite_ids[second_id] = tmp_value
        tmp_value = self.books_list.item(first_id, 0).text()
        self.books_list.item(first_id, 0).setText(self.books_list.item(second_id, 0).text())
        self.books_list.item(second_id, 0).setText(tmp_value)
        tmp_value = self.books_list.item(first_id, 0).icon()
        self.books_list.item(first_id, 0).setIcon(self.books_list.item(second_id, 0).icon())
        self.books_list.item(second_id, 0).setIcon(tmp_value)
        tmp_value = self.books_list.item(first_id, 0).isSelected()
        self.books_list.item(first_id, 0).setSelected(self.books_list.item(second_id, 0).isSelected())
        self.books_list.item(second_id, 0).setSelected(tmp_value)

    def renameFavorite(self):
        current_id = self.parent_ids[self.top_list.currentRow()]
        current_text = self.renameFavoriteLineEdit.text().strip()
        self.top_list.currentItem().setText(current_text)
        UserDb().renameFavorite(current_id, current_text)
        refavorites()

    def renameFolder(self):
        current_id = int(self.tree.currentItem().text(1))
        current_text = self.renameFolderLineEdit.text().strip()
        self.tree.currentItem().setText(0, current_text)
        UserDb().renameFavorite(current_id, current_text)
        refavorites()

    def renameBook(self):
        current_id = self.favorite_ids[self.books_list.currentItem().row()]
        current_text = self.renameBookLineEdit.text().strip()
        self.books_list.currentItem().setText(current_text)
        UserDb().renameFavoriteBook(current_id, current_text)
        refavorites()

    def newFavorite(self):
        for item in self.top_list.selectedItems():
            item.setSelected(False)

        current_text = self.renameFavoriteLineEdit.text().strip()
        if current_text:
            item = self.addFavorite(current_text)
            self.top_list.setCurrentItem(item)
        else:
            current_text = self.tr('New Favorite')
            item = self.addFavorite(current_text)
            self.top_list.setCurrentItem(item)
            self.top_list.editItem(item)
        refavorites()

    def newFolder(self):
        self.newTreeItem(self.tree, self.tree.top_id)
        refavorites()

    def newSubfolder(self):
        item = self.tree.currentItem()
        self.newTreeItem(item, int(item.text(1)))
        refavorites()

    def newTreeItem(self, parent, parent_id):
        for item in self.tree.selectedItems():
            item.setSelected(False)

        current_text = self.renameFolderLineEdit.text().strip()
        if current_text:
            self.addFolder(current_text, parent, parent_id)
        else:
            current_text = self.tr('New Folder')
            item = self.addFolder(current_text, parent, parent_id)
            self.tree.editItem(item)
        refavorites()

    def addFolder(self, folder_text, parent, parent_id):
        folder_id = UserDb().newFavorite(folder_text, parent_id)
        item = QTreeWidgetItem(parent, [folder_text, str(folder_id)])
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setData(0, Qt.DecorationRole, Icon.icon(':/icons/closed.png'))
        self.tree.setCurrentItem(item)
        refavorites()
        return item


class TreeWidget(QTreeWidget):

    def __init__(self, owner, parent=None):
        QTreeWidget.__init__(self, parent)
        self.header().setHidden(True)
        editable = owner.editable
        self.owner = owner
        if editable:
            self.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.setDragDropMode(QAbstractItemView.InternalMove)
            self.setDragEnabled(True)
            self.setDropIndicatorShown(True)
        else:
            self.setSelectionMode(QAbstractItemView.SingleSelection)
            self.setDragEnabled(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setIndentation(20)
        self.setColumnCount(1)
        self.header().setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.itemExpanded.connect(self.expandIcon)
        self.itemCollapsed.connect(self.collapseIcon)

    def expandIcon(self, item):
        item.setData(0, Qt.DecorationRole, Icon.icon(':/icons/open.png'))

    def collapseIcon(self, item):
        item.setData(0, Qt.DecorationRole, Icon.icon(':/icons/closed.png'))

    def loadFolders(self, top_id):
        self.top_id = top_id
        self.clear()
        items_dict = {}
        folders = UserDb().getFavoriteNodes(top_id, self.tr('Folder'))
        for key in folders:
            parent_id = folders[key][1]
            if parent_id == top_id:
                item = QTreeWidgetItem(self, [folders[key][0], str(key)])
                items_dict[key] = item
            else:
                item = QTreeWidgetItem(items_dict[parent_id], [folders[key][0], str(key)])
                items_dict[key] = item
                items_dict[parent_id].setExpanded(True)
            if self.owner.editable:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(0, Qt.DecorationRole, Icon.icon(':/icons/closed.png'))

        if items_dict:
            self.setCurrentItem(self.topLevelItem(0))
            self.currentItem().setSelected(True)

    def correctIcons(self):
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            item.setData(0, Qt.DecorationRole, item.isExpanded() or Icon.icon(':/icons/closed.png') if not item.childCount() == 0 else Icon.icon(':/icons/open.png'))
            iterator += 1

    def dropEvent(self, event):
        if event.source() == self:
            QAbstractItemView.dropEvent(self, event)

    def dropMimeData(self, parent, row, data, action):
        if action == Qt.MoveAction:
            return self.moveSelection(parent, row)
        return False

    def moveSelection(self, parent, position):
        selection = [QPersistentModelIndex(i) for i in self.selectedIndexes()]
        parent_index = self.indexFromItem(parent)
        if parent_index in selection:
            return False
        target = self.model().index(position, 0, parent_index).row()
        if target < 0:
            target = position
        taken = []
        for index in reversed(selection):
            item = self.itemFromIndex(QModelIndex(index))
            if item is None or item.parent() is None:
                taken.append(self.takeTopLevelItem(index.row()))
            else:
                taken.append(item.parent().takeChild(index.row()))

        parent_id = int(parent.text(1)) if parent_index.isValid() else self.top_id
        ids = [int(taken_item.text(1)) for taken_item in reversed(taken)]
        UserDb().reparentFavorites(ids, parent_id, position)
        while taken:
            if position == -1:
                if parent_index.isValid():
                    parent.insertChild(parent.childCount(), taken.pop(0))
                else:
                    self.insertTopLevelItem(self.topLevelItemCount(), taken.pop(0))
            elif parent_index.isValid():
                parent.insertChild(min(target, parent.childCount()), taken.pop(0))
            else:
                self.insertTopLevelItem(min(target, self.topLevelItemCount()), taken.pop(0))

        self.correctIcons()
        refavorites()
        return True

    def moveFoldersUp(self):
        self.moveChildern(-1)

    def moveFoldersDown(self):
        self.moveChildern(1)

    def moveChildern(self, param):

        def selectedRows():
            return sorted([index.row() for index in self.selectedIndexes()])

        self.blockSignals(True)
        parent = self.currentItem().parent() or self.invisibleRootItem()
        rows = reversed(selectedRows()) if param > 0 else selectedRows()
        for row in rows:
            first_item = parent.child(row)
            second_item = parent.child(row + param)
            first_selected = first_item.isSelected()
            second_selected = second_item.isSelected()
            UserDb().swapFavoriteOrder(int(first_item.text(1)), int(second_item.text(1)))
            item = parent.takeChild(row)
            parent.insertChild(row + param, item)
            parent.child(row).setSelected(second_selected)
            parent.child(row + param).setSelected(first_selected)

        self.correctIcons()
        self.blockSignals(False)
        refavorites()

    def selectedFolders(self):
        return [int(item.text(1)) for item in self.selectedItems()]

    def deleteSelected(self):
        folder_ids = []
        for item in self.selectedItems():
            folder_ids.append(int(item.text(1)))
            parent = item.parent() or self.invisibleRootItem()
            o = parent.takeChild(parent.indexOfChild(item))
            del o

        UserDb().deleteFavorites(folder_ids)
        if self.topLevelItemCount() == 0:
            self.loadFolders(self.top_id)
        refavorites()


def refavorites():
    for widget in Across.refresh_set:
        widget.refavorites()