# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: updatewindow.py
from qtpy.QtCore import QSize
from across import Across
from bookslist import Scope
from customs import BusySpinner, Icon, customLayout, CustomDialog, vLine, customSplitter
from ignore import RichScope
from selectwidget import SelectWidget

class UpdateWindow(CustomDialog):

    def __init__(self, context, parent):
        if context == 4:
            super().__init__(parent=parent, geometry_name='update_book', icon=':/icons/update.png')
            self.setWindowTitle(self.tr('Update'))
        else:
            if context == 5:
                super().__init__(parent=parent, geometry_name='update_pdf', icon=':/icons/pdf.png')
                self.setWindowTitle(self.tr('Pdf Download'))
        self.select_widget = SelectWidget(context=context)
        self.scope_widget = Scope(self.select_widget)
        self.rich_scope = RichScope(self.scope_widget, self.select_widget)
        separated = customLayout(False, [vLine(), self.rich_scope], margins=0)
        splitter = customSplitter(False, self.select_widget, separated, 60)
        self.setLayout(customLayout(True, [splitter], margins=0))
        self.select_widget.go()

    def sizeHint(self):
        return QSize(1090, 700)

    def show(self):
        super().show()
        BusySpinner.poke()

    def refresh(self):
        model = self.scope_widget.model
        model.dataChanged.emit(model.index(0, 0), model.index(model.rowCount() - 1, model.columnCount() - 1))

    def kill(self):
        self.hide()
        Across.refresh_set.discard(self.select_widget)
        Across.hidden_set.discard(self)
        self.deleteLater()