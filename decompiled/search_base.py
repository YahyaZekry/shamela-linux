# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: search_base.py
from qtpy.QtCore import Signal, QTimer, QCoreApplication, QSize, Qt, QLocale
from qtpy.QtWidgets import QSizePolicy, QComboBox, QLabel, QAbstractItemView, QWidget, QProgressBar, QTableView, QHeaderView
from across import Across
from cache import BookCache
from customs import BookHolder, customLayout, customToolButton, LineEdit, Splitter, customMessage
from dbmanager import UserDb
from search import Searcher
from searchboxes import SearchWidget
from settings import Settings
from engine import Query

def viewSelections(view):
    return sorted([index.row() for index in view.selectionModel().selectedRows()], reverse=True)


class PercentLabel(QWidget):

    def __init__(self):
        super().__init__()
        from textmanager import arabize
        self.number = QLabel()
        self.mark = QLabel('٪')
        self.number.setFixedWidth(self.number.fontMetrics().horizontalAdvance(arabize('100')))
        self.number.setAlignment(Qt.AlignCenter)
        self.setLayout(customLayout(False, [self.number, 1, self.mark], margins=0, spacing=0))

    def setValue(self, value):
        from textmanager import arabize
        if value < 1:
            value = 1
        self.number.setText(arabize((f"{value}")))


class ComboTable(QTableView):

    def __init__(self, model):
        super().__init__()
        self.setModel(model)
        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.setColumnWidth(1, 60)
        self.setMinimumWidth(230)
        self.setAlternatingRowColors(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setWordWrap(False)
        self.setTabKeyNavigation(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setHighlightSections(False)
        self.setShowGrid(False)


class WidgetResults(QWidget):
    closed = Signal(QWidget)

    def __init__(self, query, show_tab=None, parent=None):
        super().__init__(parent)
        self.full_title = None
        self.search_done = None
        self.show_tab = show_tab
        self._tab_shown = False
        self.container = BookHolder(off_features={'secondary'})
        self.searcher = Searcher()
        self.searcher.setQuery(query)
        self.searcher.filter_enabled = True
        self.searcher.display_slot = self.container.showBook
        self.searcher.completed_slot = self.searchCompleted
        self.searcher.filter_slot = self.searchFiltered
        self.searcher.first_result_slot = self.showTab
        self.view = self.searcher.constructViewer(side_view=False)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setFixedWidth(100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet('QProgressBar { border: 1px solid palette(mid); border-radius: 5px; background: palette(base); }QProgressBar::chunk { background: palette(highlight); border-radius: 4px; margin: 1px; }')
        if not Settings.getValue('system_numbers'):
            self.progress_bar.setLocale(QLocale(QLocale.Arabic, QLocale.Egypt))
        self.percent_label = PercentLabel()
        self.count_label = QLabel(self.tr('Preparing ...'))
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setFixedWidth(110)
        self.progress_label = QLabel()
        self.book_icon = QLabel()
        self.progress_label = QLabel()
        self.saveLineEdit = LineEdit(slot=(self.saveResults))
        self.saveLineEdit.setPlaceholderText(self.tr('Name for Saving this result'))
        self.saveLineEdit.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.saveButton = customToolButton(':/icons/save.png', (self.tr('Save these Results')), slot=(self.saveResults))
        self.groupsCombo = FilterCombo()
        self.groupsCombo.activated.connect(self.searcher.model.groupSelected)
        self.groupsCombo.activated.connect(lambda: self.centuriesCombo.setCurrentIndex(0))
        self.centuriesCombo = FilterCombo()
        self.centuriesCombo.activated.connect(self.searcher.model.centurySelected)
        self.centuriesCombo.activated.connect(lambda: self.groupsCombo.setCurrentIndex(0))
        self.deleteResultButton = customToolButton(':/icons/delete_red.png', (self.tr('Delete these Results') + '  DEL'), slot=(self.deleteResults))
        self.searchBox = SearchWidget(self.searchResults, True)
        self.searchBox.setVisible(False)
        self.showSearchButton = customToolButton(':/icons/search2.png', self.tr('Search Current Results'))
        self.showSearchButton.setCheckable(True)
        self.showSearchButton.clicked.connect(self.switchSearch)
        view = customLayout(False, [customLayout(True, [self.searchBox, 0], spacing=0, margins=0), self.view])
        ribbon = customLayout(False, [self.showSearchButton, self.count_label, 2, self.deleteResultButton,
         self.progress_bar, 2, self.percent_label, 10, self.book_icon, 2,
         self.progress_label,
         10, self.groupsCombo, 6, self.centuriesCombo, 0,
         self.saveLineEdit, self.saveButton],
          margins=0)
        wd = QWidget()
        wd.setLayout(customLayout(True, [view, 3, ribbon]))
        sp = Splitter(True, [self.container, wd], [435175, 278850])
        self.setLayout(customLayout(True, [sp]))
        self.saveLineEdit.textChanged.connect(self.buttonState)
        self.saveButton.setEnabled(False)
        if query.results:
            self.view.bypassFirst(query.results['row'])
        self.finalShow(False)
        self.searcher.start()

    def shortedPrevious(self):
        self.container.book.shortedPrevious()

    def shortedNext(self):
        self.container.book.shortedNext()

    def showSearch(self):
        self.container.book.showSearch()

    def switchPdf(self):
        self.container.book.switchPdf()

    def newDisplay(self):
        self.container.book.newDisplay()

    def switchTakreej(self):
        self.container.book.switchTakreej()

    def goText(self):
        self.container.book.goText()

    def goTree(self):
        self.container.book.goTree()

    def showBetaka(self):
        self.container.book.showBetaka()

    def shortBack(self):
        self.container.book.shortBack()

    def shortForward(self):
        self.container.book.shortForward()

    def focusBookResults(self):
        self.container.book.sideBar.focusResult()

    def focusResults(self):
        self.view.setFocus()

    def finalShow(self, value):
        self.search_done = value
        self.saveLineEdit.setVisible(value)
        self.saveButton.setVisible(value)
        self.deleteResultButton.setVisible(value)
        self.showSearchButton.setVisible(value)
        self.progress_bar.setVisible(not value)
        self.percent_label.setVisible(not value)

    def shortDelete(self):
        if self.deleteResultButton.isVisible():
            self.deleteResults()

    def switchSearch(self):
        if self.showSearchButton.isChecked():
            self.searchBox.setVisible(True)
            QTimer.singleShot(0, self.searchBox.setFocus)
        else:
            self.searchBox.setVisible(False)

    def deleteResults(self):
        if customMessage(self.tr('Delete Results'), self.tr('Do you want to delete the results'), True):
            position = self.view.currentIndex().row()
            rows = viewSelections(self.view)
            model = self.view.model()
            source = model.source
            model.deleteResults(set([source[row] for row in rows]))
            model.clearCache()
            for row in rows:
                del source[row]
                index = model.index(row, 0)
                model.beginRemoveRows(index.parent(), index.row(), index.row())

            model.beginResetModel()
            model.endResetModel()
            final_row = len(source) - 1
            if position > final_row:
                position = final_row
            self.view.setCurrentIndex(self.view.model().index(position, 0))
            self.view.displayRow(position)
            self.setCount()
            self.searcher.query.results_hash = None

    def searchResults(self, info):
        query = Query(Across.global_index)
        query.load(info)
        query.type = self.searcher.query.type
        query.pre_results = set([f"{pieces[0]}-{pieces[1]}" for pieces in self.searcher.source])
        query.scope_json = self.searcher.query.scope_json
        Across.main_window.showSearchResults(query)

    def saveResults(self):
        text = self.saveLineEdit.text().strip()
        if text:
            self.saveButton.setEnabled(False)
            user_db = UserDb()
            new_id = user_db.saveBaseId('search')
            context_id = f"search_{new_id}"
            value = self._save(context_id)
            UserDb().saveBaseValue('search', text, value, new_id)
            if Across.results_loaded:
                Across.main_window.saved.reloadResults()
            self.saveButton.setEnabled(True)
            customMessage(self.tr('Saved'), self.tr('Results Saved'))

    def save(self, context_id):
        value = self._save(context_id)
        if value:
            return [
             'SEARCH', value]

    def _save(self, context_id):
        source = self.view.model().source
        full_source = self.searcher.source or source
        if full_source:
            if source:
                row = self.view.currentIndex().row()
                if source[row] != full_source[row]:
                    row = full_source.index(source[row])
            else:
                row = 0
            results = {'source':[f"{pieces[0]}-{pieces[1]}" for pieces in full_source], 
             'row':row}
            return self.searcher.query.save(results, context_id=context_id)

    def buttonState(self):
        text = self.saveLineEdit.text().strip()
        self.saveButton.setEnabled(True if text else False)

    def setCount(self):
        from textmanager import arabize
        self.count_label.setText(self.tr('Results') + ': ' + arabize((f"{len(self.searcher.source)}")))

    def showTab(self):
        if not self._tab_shown:
            self._tab_shown = True
            if self.show_tab:
                self.show_tab(self)

    def searchCompleted(self, count):
        if count == 0:
            self.closeTab()
            self.close()
            QTimer.singleShot(0, zeroMessage)
            return
        self.book_icon.clear()
        self.book_icon.hide()
        self.progress_label.clear()
        self.progress_label.hide()
        self.setCount()
        self.finalShow(True)
        view = ComboTable(self.searcher.categories_model)
        self.groupsCombo.setModel(self.searcher.categories_model)
        self.groupsCombo.setView(view)
        self.groupsCombo.show()
        view = ComboTable(self.searcher.centuries_model)
        self.centuriesCombo.setModel(self.searcher.centuries_model)
        self.centuriesCombo.setView(view)
        self.centuriesCombo.show()

    def searchFiltered(self, book_id):
        from textmanager import arabize
        if self.count_label:
            if not self.search_done:
                query = self.searcher.query
                UserDb().addSearchHistory(query.save(bypass_results=True))
                if Across.main_window.search_window:
                    if Across.main_window.search_window.select_widget.previous:
                        Across.main_window.search_window.select_widget.previous.loadList()
                self.book_icon.setPixmap(BookCache.bookIcon(book_id).pixmap(QSize(16, 16)))
                self.progress_label.setText(f"{BookCache.bookName(book_id)}")
                self.count_label.setText(self.tr('Results') + ': ' + arabize((f"{len(self.searcher.model.source)}")))
                index = query.scope_list.index(book_id)
                if index != -1:
                    try:
                        self.progress_bar.setValue(index)
                        self.progress_bar.setMaximum(query.scope_size)
                        if query.scope_size:
                            self.percent_label.setValue(int(index / query.scope_size * 100))
                    except:
                        pass

                self.progress_label.show()
                self.book_icon.show()

    def closeTab(self):
        self.hide()
        self.search_done = True
        self.book_icon.clear()
        self.book_icon.hide()
        self.progress_label.clear()
        self.progress_label.hide()
        self.searcher.stop(2000)

    def closeEvent(self, event):
        self.closed.emit(self)
        self.deleteLater()
        event.accept()


class FilterCombo(QComboBox):

    def __init__(self):
        super().__init__()
        self.hide()


def zeroMessage():
    customMessage(QCoreApplication.translate('MainWindow', 'No results'), QCoreApplication.translate('MainWindow', 'No results are there'))