# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: controlwindow.py
from qtpy.QtCore import QSize
from customs import customLayout, CustomDialog, customSplitter
from favoritetree import FavoriteWidget
from theme import Icon
from selectwidget import SelectWidget

class ControlWindow(CustomDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent, geometry_name='control_panel', icon=':/icons/control_panel.png')
        self.setWindowTitle(self.tr('Control Panel'))
        self.select_widget = SelectWidget(context=3)
        self.favorites = FavoriteWidget(self.select_widget)
        splitter = customSplitter(False, self.select_widget, self.favorites, 60)
        self.setLayout(customLayout(True, [splitter]))
        self.select_widget.go()

    def sizeHint(self):
        return QSize(1090, 700)