# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: searchwindow.py
from qtpy.QtCore import QTimer, QSize
from bookslist import Scope
from customs import hLine, customLayout, CustomDialog, vLine, customSplitter
from theme import Icon
from ignore import RichScope
from across import Across
from searchboxes import SearchWidget, SearchType
from selectwidget import SelectWidget

class SearchWindow(CustomDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent, geometry_name='search_complex', icon=':/icons/search.png')
        self.setWindowTitle(self.tr('Search'))
        self.search_type = SearchType()
        box = SearchWidget(self.triggerSearch)
        self.select_widget = SelectWidget(context=2, box=box, search_type=(self.search_type))
        self.scope_widget = Scope(self.select_widget)
        self.rich_scope = RichScope(self.scope_widget, self.select_widget)
        vertical = customLayout(True, [6, self.search_type, 6, hLine(), box, hLine(), self.rich_scope], margins=0)
        vertical = customLayout(False, [vLine(), vertical], margins=0)
        splitter = customSplitter(False, self.select_widget, vertical, 65)
        self.setLayout(customLayout(True, [splitter]))
        self.select_widget.go()
        QTimer.singleShot(0, box.setFocus)

    def triggerSearch(self, info):
        from engine import Query
        self.hide()
        self.search_type.save(info)
        info['scope'] = self.select_widget.getScope()
        query = Query(Across.global_index)
        query.load(info)
        Across.main_window.showSearchResults(query)

    def sizeHint(self):
        return QSize(1090, 700)