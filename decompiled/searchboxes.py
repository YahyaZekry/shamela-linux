# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: searchboxes.py
from functools import partial
import regex as re
from qtpy.QtCore import Signal, Qt, QSize, QTimer
from qtpy.QtGui import QColor, QPalette
from qtpy.QtWidgets import QGridLayout, QRadioButton, QWidgetAction, QMenu, QPushButton, QCheckBox, QCompleter, QWidget, QTabWidget, QScrollArea, QSizePolicy, QLabel, QGroupBox, QAction, QComboBox, QProgressBar, QApplication, QToolButton
from customs import hLine, Icon, CompleterModel, LineEdit, customLayout, customToolButton, NumCombo, customMessage, clickableLabel, flexibleBrowser, CustomDialog, minSize, QtFont, styledLabel
from dbmanager import UserDb
from settings import Settings
from textmanager import treatSearch, arabize, formatBetaka, latinize
from engine import QueryType
from across import Across
q_tbl = str.maketrans('?؟', '  ')

def removeQuestion(text):
    return text.translate(q_tbl)


def requiresMemoryIndex(info):
    """Whether this search would need the engine's precise in-memory second pass —
    i.e. it cannot be answered exactly by the normalized index alone. Mirrors
    engine.Query.secondPass()/adjustParameters at the raw-info level so the search
    box can decide before launching anything. (empty_base is never set, so moot.)
    """
    features = set(info.get('features', ()))
    if 'stemmed' in features:
        return False
    if 'hamza' in features or 'diacritics' in features:
        return True
    if 'numbers' in features:
        digit = nondigit = False
        for panel_group in info['phrases']:
            for panel in panel_group:
                for phrase in panel:
                    if re.search('\\d', phrase):
                        digit = True
                    if re.search('\\D', phrase):
                        nondigit = True

        return digit and nondigit
    return False


def searchAllowed(info):
    """False when the search would force building an in-memory index over the
    whole corpus. A NOT group is fine on its own when no second pass is needed
    (the user may legitimately ask for "everything not containing X" — a huge but
    cheap id list). But once a precise second pass is required, a NOT group that
    is either alone (no affirmative group to bound the candidate set) or OR-joined
    with the others (where the NOT branch is additive and matches ~everything) has
    no bounded candidate set to re-index — so it is refused. See audit F1/F2.
    """
    and_panels, or_panels, not_panels = info['phrases']
    if not not_panels:
        return True
    else:
        return requiresMemoryIndex(info) or True
    is_or = 'is_or' in set(info.get('features', ()))
    has_affirmative = bool(and_panels or or_panels)
    return bool(has_affirmative) and not is_or


class AffixByan(CustomDialog):

    def __init__(self):
        super().__init__(parent=(Across.main_window), icon=':/icons/search.png')
        self.setWindowTitle(self.tr('asterisk and question mark use'))
        minSize(self, 700, 450)
        font = QtFont(['Traditional Naskh', 14, True])
        label = styledLabel(height=40)
        label.setFont(font)
        label.setText(self.tr('Hints on the use of special cards in search words'))
        self.browser = flexibleBrowser()
        text = [
         "'• للبحث باللواصق، استخدم النجمة: وهي تعني احتمال وجود حرف أو أكثر في هذا الموضع.'", 
         "'• ويمكن وضعها في أي موضع من الكلمة: في أولها، أو وسطها، أو آخرها، أو كل ذلك.'", 
         "'• وذلك لأي كلمة من كلمات العبارة: فتعطي بذلك خيارات أوسع من مجرد وضع علامة على العبارة كاملة.'", 
         "'• فلو بحثت مثلا عن: *صيام* فإنك تجد نحو (الصيام) (صيامهم).'", 
         "'• ولو بحثت عن ص*م&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*عشر*: لوجدت نحو (صوم العشر) (صيام عشر) (صام عشرين).'", 
         "'• لكن لا تستخدم النجمة إلا عند الحاجة إليها: فهي تجعل البحث أبطأ قليلا، خصوصا إذا كانت في أول الكلمة.'", 
         "'• إذا كنت تحتاج أشكال متعددة لنفس الكلمة: فالبحث الصرفي أفضل، فبعض أشكال الكلمة تتغير بما لا يكفي معه استخدام اللواصق. مثل الحاجة، يحتاج، أحوج، احتياجاتهم.'", 
         "'• علامة الاستفهام: تفيد في أمر مختلف تماما، وهي تعني حرفا واحدا، لا أكثر ولا أقل؛ فهي تفيد باحثي المخطوطات.'", 
         "'• فمثلا: لو صادفت في المخطوط حرف (ذ) وبعده مقدار حرفين لا يظهران، وبعده (ج)، يمكنك أن تبحث عن ذ؟؟ج فتجد كلمات مثل ذؤوج ، ذريج'"]
        text = '\n'.join(text)
        self.browser.setHtml(formatBetaka(text, None, None, None, None))
        self.setLayout(customLayout(True, [3, label, 2, self.browser], margins=3, spacing=3))


class SearchWidget(QWidget):

    def __init__(self, slot, shrink=None):
        super().__init__()
        self.slot = slot
        self.info = self.test_request = None
        self.label = [self.tr('And'),
         self.tr('Or'),
         self.tr('Not')]
        self.explain = [
         self.tr('All group phrases must be present'),
         self.tr('Any group phrases must be present'),
         self.tr('All group phrases must be absent')]
        self.groupButton = QToolButton()
        self.groupButton.setStyleSheet('QToolButton::menu-indicator {image: none; width: 0px; padding: 0px;}')
        self.groupButton.setIcon(Icon.icon(':/icons/insert.png'))
        self.groupButton._icon_path = ':/icons/insert.png'
        self.groupButton.setAutoRaise(True)
        self.groupButton.setIconSize(QSize(16, 16))
        self.groupButton.setToolTip(self.tr('Add group'))
        self.groupButton.setMaximumWidth(24)
        self.groupButton.setMaximumHeight(24)
        self.groupButton.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.groupButton)
        menu.setStyleSheet('QMenu::icon {padding-left: 0px;}')
        m_label = QLabel(self.tr('Add new group'))
        m_label.setAlignment(Qt.AlignCenter)
        widget = QWidgetAction(menu)
        widget.setDefaultWidget(m_label)
        menu.addAction(widget)
        menu.addSeparator()
        items = (f"{self.label[0]}      : {self.explain[0]}", f"{self.label[1]}     : {self.explain[1]}", f"{self.label[2]} : {self.explain[2]}")
        self.actions = []
        for i, item in enumerate(items):
            action = QAction(item)
            menu.addAction(action)
            action.triggered.connect(partial(self.addNewPanelFromMenu, i))
            self.actions.append(action)

        menu.addSeparator()
        action = QAction(self.tr('Restore default'))
        menu.addAction(action)
        action.triggered.connect(self.restoreDefaultPanels)
        self.actions.append(action)
        self.groupButton.setMenu(menu)
        self.stemCheck = QCheckBox(self.tr('Stemmed search'))
        self.stemCheck.setToolTip(self.tr('Stemmed search by analyzing the word into its possible roots'))
        self.hamzaCheck = QCheckBox(self.tr('Consider Hamazat'))
        self.hamzaCheck.setToolTip(self.tr('Consider Difference between Hamazat and others in search'))
        self.diacCheck = QCheckBox(self.tr('Consider diacritics'))
        self.diacCheck.setToolTip(self.tr('Consider difference in diacritics'))
        self.numbersCheck = QCheckBox(self.tr('Consider Numbers'))
        self.numbersCheck.setToolTip(self.tr('Consider Numbers in search'))
        self.stemCheck.clicked.connect(self.stemmClicked)
        label = clickableLabel(text=(self.tr('Affix search')), tooltip=(self.tr('For affix search use asterisk')),
          normal_size=True,
          slot=(self.showAffixInfo),
          black=True)
        grid = QGridLayout()
        grid.addWidget(self.stemCheck, 0, 0)
        grid.addWidget(label, 0, 1)
        grid.addWidget(self.hamzaCheck, 1, 0)
        grid.addWidget(self.diacCheck, 1, 1)
        grid.addWidget(self.numbersCheck, 1, 2)
        self.byan = QLabel()
        self.byan.setAlignment(Qt.AlignCenter)
        self.andOption = QRadioButton(self.tr('Search all of the groups'))
        self.andOption.setToolTip(self.tr('All these groups must be present'))
        self.orOption = QRadioButton(self.tr('Search One or more of them'))
        self.orOption.setToolTip(self.tr('One or more of these groups is enough'))
        self.andOption.setChecked(True)
        self.updateByan()
        self.andOption.clicked.connect(self.updateByan)
        self.orOption.clicked.connect(self.updateByan)
        upper = customLayout(False, [self.andOption, 5, self.orOption, 0, self.groupButton], spacing=1)
        self.searchTabs = QTabWidget()
        self.searchTabs.setDocumentMode(True)
        self.searchTabs.currentChanged.connect(self.tabChanged)
        self.tabs_meta = []
        self._panel_tab_order_refresh_pending = False
        self._pending_focus_widget = None
        self._pending_focus_state = None
        if Settings.getValue('search_completer'):
            self.completer = QCompleter()
            self.completer.setModel(CompleterModel(UserDb()).MODEL)
        else:
            self.completer = None
        for i in range(3):
            self.addNewPanel(i)

        byan = QWidget()
        byan.setObjectName('searchTabCorner')
        byan.setLayout(customLayout(True, [self.byan, 3], spacing=0, margins=0))
        self.searchTabs.setCornerWidget(byan)
        self.count_label = QLabel()
        self.count_label.setAlignment(Qt.AlignCenter)
        self.clearButton = customToolButton(':/icons/file.png', (self.tr('clear search fields')), slot=(self.clearBoxes))
        self.addButton = customToolButton(':/icons/add.png', (self.tr('Adding search box')), slot=(self.addBoxes))
        self.searchButton = customToolButton(':/icons/search2.png', (self.tr('Search')), slot=(self.triggerSearch))
        self.progress = QProgressBar()
        self.progress.setFixedHeight(10)
        self.progress.setTextVisible(False)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setVisible(False)
        button_Layout = customLayout(False, [self.clearButton, self.addButton, self.progress, self.count_label, self.searchButton])
        self.setLayout(customLayout(True, [grid, 6, hLine(), upper, self.searchTabs, button_Layout], margins=[1, 2, 1, 1]))
        if shrink:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.testButton()
        self.declaration = None
        self.schedulePanelTabOrderRefresh()

    def showAffixInfo(self):
        if not self.declaration:
            self.declaration = AffixByan()
        self.declaration.show()

    def updateByan(self):
        byan = self.tr('All') if self.andOption.isChecked() else self.tr('Any')
        self.byan.setText(f"[{byan}]")

    def panelBoxes(self):
        if self.tabs_meta:
            return len(self.tabs_meta[0]['lines'])
        return Settings.getValue('search_boxes')

    def buildMeta(self, panel_type, phrases=None, and_options=None):
        lines = list(phrases or [])
        needed = max(self.panelBoxes(), len(lines))
        while len(lines) < needed:
            lines.append('')

        container = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)
        try:
            near, ordered = and_options or [0, False]
        except (TypeError, ValueError):
            near, ordered = (0, False)

        return {'type':panel_type,  'lines':lines, 
         'near':near if panel_type == 0 else 0, 
         'ordered':ordered if panel_type == 0 else False, 
         'has_text':any((line.strip() for line in lines)), 
         'container':container, 
         'panel':None}

    def builtPanel(self, index):
        if 0 <= index < len(self.tabs_meta):
            return self.tabs_meta[index]['panel']

    def ensurePanel(self, index):
        if index < 0 or index >= len(self.tabs_meta):
            return
        meta = self.tabs_meta[index]
        if meta['panel']:
            return
        panel = SearchPanel(meta['type'], self, index, self.completer, self.explain[meta['type']], meta)
        meta['panel'] = panel
        meta['container'].layout().addWidget(panel, 0, 0)
        self.schedulePanelTabOrderRefresh()

    def applyMetaToPanel(self, index):
        panel = self.builtPanel(index)
        if panel:
            panel.loadMeta(self.tabs_meta[index])
            self.schedulePanelTabOrderRefresh()

    def updatePanelIndexes(self):
        for i, meta in enumerate(self.tabs_meta):
            if meta['panel']:
                meta['panel'].index = i

    def tabChanged(self, index):
        self.ensurePanel(index)
        self.schedulePanelTabOrderRefresh()
        panel = self.builtPanel(index)
        if panel:
            if not any((line.hasFocus() for line in panel.searchLines)):
                self.schedulePanelLineFocus(index, 0)

    def syncPanelState(self, index):
        panel = self.builtPanel(index)
        if not panel:
            return
        panel_state = panel.rawState()
        meta = self.tabs_meta[index]
        meta['type'] = panel_state['type']
        meta['lines'] = panel_state['lines']
        meta['near'] = panel_state['near']
        meta['ordered'] = panel_state['ordered']
        self.changeColor(index, panel_state['has_text'])

    def panelData(self, index, sanitize=None):
        meta = self.tabs_meta[index]
        phrases = []
        changed = False
        for i, raw in enumerate(list(meta['lines'])):
            phrase = treatSearch(raw, keep_digits=True) if sanitize else raw
            if sanitize:
                if raw != phrase:
                    meta['lines'][i] = phrase
                    changed = True
            if phrase:
                phrases.append(phrase)

        meta['has_text'] = any((line.strip() for line in meta['lines']))
        if changed:
            self.applyMetaToPanel(index)
        panel_dict = {'type':meta['type'], 
         'phrases':phrases}
        if meta['type'] == 0:
            panel_dict['ordered'] = meta['ordered']
            panel_dict['near'] = meta['near']
        return panel_dict

    def restoreDefaultPanels(self):
        for i in range(len(self.tabs_meta) - 1, 2, -1):
            meta = self.tabs_meta.pop(i)
            self.searchTabs.removeTab(i)
            meta['container'].deleteLater()

        self.searchTabs.setCurrentIndex(0)
        self.updatePanelIndexes()
        self.testPresence()
        self.schedulePanelTabOrderRefresh()

    def addNewPanel(self, panel_type, phrases=None, and_options=None):
        meta = self.buildMeta(panel_type, phrases, and_options)
        current = len(self.tabs_meta)
        self.tabs_meta.append(meta)
        self.searchTabs.addTab(meta['container'], self.label[panel_type])
        self.changeColor(current, meta['has_text'])
        if current == self.searchTabs.currentIndex():
            self.ensurePanel(current)
        self.schedulePanelTabOrderRefresh()

    def addNewPanelFromMenu(self, panel_type):
        self.addNewPanel(panel_type)
        current = len(self.tabs_meta) - 1
        self.searchTabs.setCurrentIndex(current)
        self.schedulePanelLineFocus(current, 0)

    def chainTabOrder(self, widgets):
        widgets = [widget for widget in widgets if widget if not widget.isHidden() if widget.isEnabled() if widget.focusPolicy() != Qt.NoFocus]
        for first, second in zip(widgets, widgets[1:]):
            QWidget.setTabOrder(first, second)

    def ownsWidget(self, widget):
        while widget:
            if widget is self:
                return True
            widget = widget.parentWidget()

        return False

    def captureFocusState(self, widget):
        if not hasattr(widget, 'cursorPosition'):
            return
        state = {'cursor': widget.cursorPosition()}
        start = widget.selectionStart()
        if start >= 0:
            state['selection'] = (
             start, len(widget.selectedText()))
        return state

    def restoreFocusState(self, widget, state):
        if state:
            return hasattr(widget, 'setCursorPosition') or None
        else:
            widget.setCursorPosition(state['cursor'])
            if 'selection' in state:
                start, length = state['selection']
                widget.setSelection(start, length)
            else:
                if hasattr(widget, 'deselect'):
                    widget.deselect()

    def rememberCurrentFocus(self):
        widget = QApplication.focusWidget()
        if widget and self.ownsWidget(widget):
            self._pending_focus_widget = widget
            self._pending_focus_state = self.captureFocusState(widget)
        else:
            self._pending_focus_widget = None
            self._pending_focus_state = None

    def restoreRememberedFocus(self):
        widget = self._pending_focus_widget
        state = self._pending_focus_state
        self._pending_focus_widget = None
        self._pending_focus_state = None
        try:
            return widget and self.ownsWidget(widget) or None
            if not (widget.isHidden() or widget.isEnabled)() or widget.focusPolicy() == Qt.NoFocus:
                return
            widget.setFocus()
            self.restoreFocusState(widget, state)
        except RuntimeError:
            return

    def orderedTabWidgets(self):
        widgets = [
         self.stemCheck,
         self.hamzaCheck,
         self.diacCheck,
         self.numbersCheck,
         self.andOption,
         self.orOption,
         self.groupButton,
         self.searchTabs.tabBar()]
        panel = self.builtPanel(self.searchTabs.currentIndex())
        if panel:
            widgets.extend(panel.tabOrderWidgets())
        widgets.extend([
         self.clearButton,
         self.addButton,
         self.searchButton])
        return widgets

    def schedulePanelTabOrderRefresh(self):
        self.rememberCurrentFocus()
        if self._panel_tab_order_refresh_pending:
            return
        self._panel_tab_order_refresh_pending = True
        QTimer.singleShot(0, self.refreshPanelTabOrder)

    def refreshPanelTabOrder(self):
        self._panel_tab_order_refresh_pending = False
        self.chainTabOrder(self.orderedTabWidgets())
        self.restoreRememberedFocus()

    def stemmClicked(self):
        self.syncStemExclusion(clear=True)

    def syncStemExclusion(self, clear=False):
        others = [
         self.hamzaCheck, self.diacCheck, self.numbersCheck]
        if self.stemCheck.isChecked():
            if clear:
                for check in others:
                    check.setChecked(False)

            for check in others:
                check.setEnabled(False)

        else:
            for check in others:
                check.setEnabled(True)

    def changeColor(self, i, has_text):
        if has_text:
            color = QColor(242, 168, 101) if Across.active_theme == 'dark' else QColor(220, 50, 47)
        else:
            color = QApplication.palette().color(QPalette.WindowText)
        self.searchTabs.tabBar().setTabTextColor(i, color)
        self.tabs_meta[i]['has_text'] = has_text
        self.testButton()

    def setResultsCount(self, text):
        self.progress.setVisible(False)
        self.count_label.setText(text)
        self.count_label.setVisible(True)

    def showProgress(self):
        self.count_label.setVisible(False)
        self.progress.setVisible(True)

    def setFocus(self, Qt_FocusReason=None):
        current = self.searchTabs.currentIndex()
        self.ensurePanel(current)
        panel = self.builtPanel(current)
        if panel:
            panel.setFocus()

    def focusPanelLine(self, panel_index, line_index):
        if panel_index < 0 or panel_index >= len(self.tabs_meta):
            return
        self.ensurePanel(panel_index)
        panel = self.builtPanel(panel_index)
        if panel:
            panel.focusLine(line_index)

    def schedulePanelLineFocus(self, panel_index, line_index):
        QTimer.singleShot(0, partial(self.focusPanelLine, panel_index, line_index))

    def clearBoxes(self):
        current = self.searchTabs.currentIndex()
        for i, meta in enumerate(self.tabs_meta):
            meta['lines'] = [
             ''] * len(meta['lines'])
            self.changeColor(i, False)
            self.applyMetaToPanel(i)

        self.schedulePanelLineFocus(current, 0)

    def addBoxes(self):
        current = self.searchTabs.currentIndex()
        for i, meta in enumerate(self.tabs_meta):
            meta['lines'].append('')
            self.applyMetaToPanel(i)
            self.changeColor(i, meta['has_text'])

        self.schedulePanelLineFocus(current, len(self.tabs_meta[current]['lines']) - 1)
        self.schedulePanelTabOrderRefresh()

    def testButton(self):
        if not hasattr(self, 'searchButton'):
            return
        has_text = False
        for meta in self.tabs_meta:
            if meta['has_text']:
                has_text = True
                break

        self.searchButton.setEnabled(has_text)

    def triggerSearch(self):
        panels_list = []
        big_bag = set()
        for i in range(len(self.tabs_meta)):
            bag = set()
            panel_dict = self.panelData(i, sanitize=True)
            phrases_list = panel_dict['phrases']
            panels_list.append(panel_dict)
            for phrase in phrases_list:
                if phrase.isdigit():
                    if not self.stemCheck.isChecked():
                        self.numbersCheck.setChecked(True)
                        self.numbersCheck.repaint()
                if self.stemCheck.isChecked():
                    if '*' in phrase:
                        customMessage(self.tr('Search phrases'), self.tr('Astrick can not be used in stemmed search'))
                        return
                if not ' * ' in phrase:
                    if phrase.startswith('* ') or phrase.endswith(' *'):
                        self.searchTabs.setCurrentIndex(i)
                        customMessage(self.tr('Search phrases'), self.tr('Astrick should be a part of a word, not separate'))
                        return
                    if phrase in bag:
                        self.searchTabs.setCurrentIndex(i)
                        self.setFocus()
                        customMessage(self.tr('Search phrases'), self.tr('There are repeated phrases in search enteries'))
                        return
                    bag.add(phrase)
                    big_bag.add(phrase)

        if big_bag:
            UserDb().addSearchPhrases(list(big_bag))
            and_lists = []
            or_lists = []
            not_lists = []
            and_options = []
            for panel_dict in panels_list:
                if panel_dict['phrases']:
                    if panel_dict['type'] == 0:
                        and_lists.append(panel_dict['phrases'])
                        and_options.append([panel_dict['near'], panel_dict['ordered']])
                    elif panel_dict['type'] == 1:
                        or_lists.append(panel_dict['phrases'])
                    elif panel_dict['type'] == 2:
                        not_lists.append(panel_dict['phrases'])

            self.setFocus()
            self.info = {}
            self.info['phrases'] = [and_lists, or_lists, not_lists]
            features = []
            if and_options != [[0, False]]:
                self.info['and_options'] = and_options
            if self.stemCheck.isChecked():
                features.append('stemmed')
            if self.hamzaCheck.isChecked():
                features.append('hamza')
            if self.diacCheck.isChecked():
                features.append('diacritics')
            if self.numbersCheck.isChecked():
                features.append('numbers')
            if self.orOption.isChecked():
                features.append('is_or')
            if features:
                self.info['features'] = features
            if not searchAllowed(self.info):
                customMessage(self.tr('Search can not be performed'), self.tr('With your current options, You must add something to (AND) tab'))
                return
            self.slot(self.info)
        else:
            customMessage(self.tr('Search phrases'), self.tr('Enter some phrases to search for'))

    def load(self, info):
        stemmed, hamza, diacritics, numbers, is_or = (False, False, False, False, False)
        if info:
            if 'features' in info:
                if 'stemmed' in info['features']:
                    stemmed = True
                if 'hamza' in info['features']:
                    hamza = True
                if 'diacritics' in info['features']:
                    diacritics = True
                if 'numbers' in info['features']:
                    numbers = True
                if 'is_or' in info['features']:
                    is_or = True
            else:
                self.stemCheck.setChecked(stemmed)
                self.hamzaCheck.setChecked(hamza)
                self.diacCheck.setChecked(diacritics)
                self.numbersCheck.setChecked(numbers)
                self.syncStemExclusion(clear=True)
                if is_or:
                    self.orOption.setChecked(True)
                else:
                    self.andOption.setChecked(True)
            self.loadTabs(info)
            self.test_request = True

    def paintEvent(self, e):
        if self.test_request:
            self.test_request = None
            self.testPresence()
        super().paintEvent(e)

    def testPresence(self):
        for i, meta in enumerate(self.tabs_meta):
            self.changeColor(i, any((line.strip() for line in meta['lines'])))

    def loadTabs(self, info):
        and_lists, or_lists, not_lists = info['phrases']
        if not and_lists:
            and_lists = [[]]
        if not or_lists:
            or_lists = [[]]
        if not not_lists:
            not_lists = [[]]
        raw_options = info['and_options'] if 'and_options' in info else []

        def andOption(i):
            try:
                near, ordered = raw_options[i]
                return [near, ordered]
            except (IndexError, TypeError, ValueError):
                return [
                 0, False]

        needed = []
        for i, panel in enumerate(and_lists):
            needed.append((0, panel, andOption(i)))

        for panel in or_lists:
            needed.append((1, panel, None))

        for panel in not_lists:
            needed.append((2, panel, None))

        h = self.searchTabs.height()
        if h > 0:
            self.searchTabs.setFixedHeight(h)
        self.deleteTabs()
        for ptype, phrases, opts in needed:
            self.addNewPanel(ptype, phrases, opts)

        self.searchTabs.setCurrentIndex(0)
        self.ensurePanel(0)
        if h > 0:
            self.searchTabs.setMinimumHeight(0)
            self.searchTabs.setMaximumHeight(16777215)
        self.schedulePanelTabOrderRefresh()

    def deleteTabs(self):
        for i in range(len(self.tabs_meta) - 1, -1, -1):
            meta = self.tabs_meta.pop(i)
            self.searchTabs.removeTab(i)
            meta['container'].deleteLater()

        self.schedulePanelTabOrderRefresh()


class Near(QWidget):

    def __init__(self, current_value):
        super().__init__()
        self.check = QCheckBox(self.tr('Near phrases'))
        self.check.clicked.connect(self.checkClicked)
        self.combo = NumCombo(max_num=700)
        tip = self.tr('How many words between phrases as maximum')
        self.combo.setToolTip(tip)
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        _sp = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        _sp.setRetainSizeWhenHidden(True)
        self.combo.setSizePolicy(_sp)
        self.check.setToolTip(tip)
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        self.combo.lineEdit().editingFinished.connect(self.normalizeCurrentText)
        self.setValue(current_value)
        if current_value:
            self.combo.setVisible(True)
        else:
            self.combo.setVisible(False)
        self.setLayout(customLayout(False, [self.check, 0, self.combo], margins=0))

    def checkClicked(self, value):
        self.combo.setVisible(value)
        if value:
            self.normalizeCurrentText()

    def setValue(self, current_value):
        shown_value = current_value + 1 if current_value else 10
        self.combo.setValue(shown_value)

    def normalizeCurrentText(self):
        try:
            value = int(latinize(self.combo.currentText()))
        except Exception:
            value = 10

        value = min(700, max(1, value))
        self.combo.setValue(value)

    def getValue(self):
        if self.check.isChecked():
            self.normalizeCurrentText()
            return self.combo.value() - 1
        return 0


class SearchPanel(QWidget):
    hasText = Signal(bool)

    def configuredScrollAreaHeight(self, visible_rows):
        visible_rows = max(0, min(visible_rows, self.scrollLayout.count()))
        margins = self.scrollLayout.contentsMargins()
        height = margins.top() + margins.bottom() + self.scrollArea.frameWidth() * 2
        if visible_rows > 1:
            height += (visible_rows - 1) * self.scrollLayout.spacing()
        for i in range(visible_rows):
            item = self.scrollLayout.itemAt(i)
            widget = item.widget() if item else None
            if widget:
                height += widget.sizeHint().height()

        return height

    def __init__(self, panel_type, box, index, completer, explain, meta):
        super().__init__()
        self.is_mac = Across.os == 'mac'
        boxes_number = Settings.getValue('search_boxes')
        self.enumerate = Settings.getValue('show_searchbox_number')
        self.box = box
        self.index = index
        self.loading = False
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setStyleSheet('QScrollArea { border: none; }')
        scrollWidget = QWidget(self)
        self.scrollLayout = customLayout(True)
        self.searchLines = []
        self.panel_type = panel_type
        self.completer = completer
        self.box_number = 0
        self.visible_rows = boxes_number
        scrollWidget.setLayout(self.scrollLayout)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(scrollWidget)
        label = QLabel(explain)
        contents = [label, 5]
        if self.panel_type == 0:
            self.chekOrdered = QCheckBox(self.tr('Ordered'))
            self.near = Near(0)
            self.chekOrdered.toggled.connect(self.syncState)
            self.near.check.toggled.connect(self.syncState)
            self.near.check.toggled.connect(self.box.schedulePanelTabOrderRefresh)
            self.near.combo.currentTextChanged.connect(self.syncState)
            contents += [self.chekOrdered, self.near]
        contents = customLayout(False, contents, margins=0, spacing=0)
        w = QWidget()
        w.setLayout(contents)
        w.setFixedHeight(20)
        self.setLayout(customLayout(True, [w, self.scrollArea], spacing=4, margins=[3, 6, 3, 1]))
        for _ in range(len(meta['lines'])):
            self.addBox(notify=False)

        self.loadMeta(meta)
        self.applyConfiguredScrollAreaHeight()

    def setFocus(self, Qt_FocusReason=None):
        for line in self.searchLines:
            if line.hasFocus():
                return

        self.focusLine(0)

    def focusLine(self, index):
        if not self.searchLines:
            return
        index = max(0, min(index, len(self.searchLines) - 1))
        line = self.searchLines[index]
        line.setFocus()
        self.scrollArea.ensureWidgetVisible(line)

    def addBox(self, phrase=None, notify=True):
        LABEL_WIDTH = 15
        STAR_SIZE = 28 if self.is_mac else 20
        self.box_number += 1
        line = LineEdit(digit_policy='ascii', slot=(self.box.triggerSearch), modify_pasted=removeQuestion)
        if self.completer:
            line.setCompleter(self.completer)
        else:
            line.textChanged.connect(self.syncState)
            line.setMinimumHeight(STAR_SIZE)
            self.searchLines.append(line)
            if self.enumerate:
                label = QLabel(arabize((f"{self.box_number}")))
                label.setAlignment(Qt.AlignCenter)
                label.setMinimumWidth(LABEL_WIDTH)
                w = QWidget()
                w.setLayout(customLayout(False, [label, line]))
                self.scrollLayout.addWidget(w)
            else:
                self.scrollLayout.addWidget(line)
        if phrase is not None:
            line.setText(phrase)
        if notify:
            self.syncState()
        self.box.schedulePanelTabOrderRefresh()

    def loadMeta(self, meta):
        self.loading = True
        while len(self.searchLines) < len(meta['lines']):
            self.addBox(notify=False)

        for i, line in enumerate(self.searchLines):
            line.setText(meta['lines'][i] if i < len(meta['lines']) else '')

        if self.panel_type == 0:
            self.near.setValue(meta['near'])
            if meta['near']:
                self.near.check.setChecked(True)
                self.near.combo.setVisible(True)
            else:
                self.near.check.setChecked(False)
                self.near.combo.setVisible(False)
            self.chekOrdered.setChecked(meta['ordered'])
        self.loading = False
        self.box.schedulePanelTabOrderRefresh()

    def applyConfiguredScrollAreaHeight(self):
        fixed_h = self.configuredScrollAreaHeight(self.visible_rows)
        self.scrollArea.setFixedHeight(fixed_h)
        self.scrollArea.setMinimumHeight(0)
        self.scrollArea.setMaximumHeight(fixed_h)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.applyConfiguredScrollAreaHeight)

    def syncState(self):
        if self.loading:
            return
        self.box.syncPanelState(self.index)

    def rawState(self):
        lines = [line.text() for line in self.searchLines]
        return {'type':self.panel_type, 
         'lines':lines, 
         'near':self.near.getValue() if self.panel_type == 0 else 0, 
         'ordered':self.chekOrdered.isChecked() if self.panel_type == 0 else False, 
         'has_text':any((line.strip() for line in lines))}

    def tabOrderWidgets(self):
        widgets = []
        if self.panel_type == 0:
            widgets.extend([self.chekOrdered, self.near.check, self.near.combo])
        widgets.extend(self.searchLines)
        return widgets


class SearchType(QGroupBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(self.tr('Search in: '))
        self.setFlat(True)
        self.fields = ['body', 'foot', 'comment', 'title']
        texts = [self.tr('Text'), self.tr('Footnotes'), self.tr('Comments'), self.tr('Titles')]
        tips = [self.tr('Search in the Main text'), self.tr('Search in Footnotes'), self.tr('Search in User Comments'),
         self.tr('Search in Titles')]
        self.options = []
        for i in range(4):
            check = QCheckBox(texts[i])
            check.setToolTip(tips[i])
            check.setChecked(i != 3)
            check.toggled.connect(partial(self.ensureOne, i))
            self.options.append(check)

        checked_color = 'rgb(242,168,101)' if Across.active_theme == 'dark' else 'rgb(128, 0, 0)'
        self.options[3].setStyleSheet(f"QCheckBox:unchecked {{color: palette(window-text);}} QCheckBox:checked {{color: {checked_color};}}")
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setLayout(customLayout(False, (self.options), margins=[1, 5, 1, 1]))

    def ensureOne--- This code section failed: ---

 L. 863         0  SETUP_LOOP           26  'to 26'
                2  LOAD_FAST                'self'
                4  LOAD_ATTR                options
                6  GET_ITER         
                8  FOR_ITER             24  'to 24'
               10  STORE_FAST               'option'

 L. 863        12  LOAD_FAST                'option'
               14  LOAD_METHOD              blockSignals
               16  LOAD_CONST               True
               18  CALL_METHOD_1         1  '1 positional argument'
               20  POP_TOP          
               22  JUMP_BACK             8  'to 8'
               24  POP_BLOCK        
             26_0  COME_FROM_LOOP        0  '0'

 L. 864        26  LOAD_FAST                'checked'
               28  POP_JUMP_IF_FALSE    92  'to 92'

 L. 865        30  LOAD_FAST                'i'
               32  LOAD_CONST               3
               34  COMPARE_OP               ==
               36  POP_JUMP_IF_FALSE    74  'to 74'

 L. 866        38  SETUP_LOOP           90  'to 90'
               40  LOAD_GLOBAL              range
               42  LOAD_CONST               3
               44  CALL_FUNCTION_1       1  '1 positional argument'
               46  GET_ITER         
               48  FOR_ITER             70  'to 70'
               50  STORE_FAST               'i'

 L. 866        52  LOAD_FAST                'self'
               54  LOAD_ATTR                options
               56  LOAD_FAST                'i'
               58  BINARY_SUBSCR    
               60  LOAD_METHOD              setChecked
               62  LOAD_CONST               False
               64  CALL_METHOD_1         1  '1 positional argument'
               66  POP_TOP          
               68  JUMP_BACK            48  'to 48'
               70  POP_BLOCK        
               72  JUMP_ABSOLUTE       154  'to 154'
             74_0  COME_FROM            36  '36'

 L. 868        74  LOAD_FAST                'self'
               76  LOAD_ATTR                options
               78  LOAD_CONST               3
               80  BINARY_SUBSCR    
               82  LOAD_METHOD              setChecked
               84  LOAD_CONST               False
               86  CALL_METHOD_1         1  '1 positional argument'
               88  POP_TOP          
             90_0  COME_FROM_LOOP       38  '38'
               90  JUMP_FORWARD        154  'to 154'
             92_0  COME_FROM            28  '28'

 L. 870        92  LOAD_CONST               False
               94  STORE_FAST               'anyone'

 L. 871        96  SETUP_LOOP          134  'to 134'
               98  LOAD_GLOBAL              range
              100  LOAD_CONST               4
              102  CALL_FUNCTION_1       1  '1 positional argument'
              104  GET_ITER         
            106_0  COME_FROM           122  '122'
              106  FOR_ITER            132  'to 132'
              108  STORE_FAST               'i'

 L. 872       110  LOAD_FAST                'self'
              112  LOAD_ATTR                options
              114  LOAD_FAST                'i'
              116  BINARY_SUBSCR    
              118  LOAD_METHOD              isChecked
              120  CALL_METHOD_0         0  '0 positional arguments'
              122  POP_JUMP_IF_FALSE   106  'to 106'

 L. 873       124  LOAD_CONST               True
              126  STORE_FAST               'anyone'

 L. 874       128  BREAK_LOOP       
              130  JUMP_BACK           106  'to 106'
              132  POP_BLOCK        
            134_0  COME_FROM_LOOP       96  '96'

 L. 875       134  LOAD_FAST                'anyone'
              136  POP_JUMP_IF_TRUE    154  'to 154'

 L. 875       138  LOAD_FAST                'self'
              140  LOAD_ATTR                options
              142  LOAD_CONST               0
              144  BINARY_SUBSCR    
              146  LOAD_METHOD              setChecked
              148  LOAD_CONST               True
              150  CALL_METHOD_1         1  '1 positional argument'
              152  POP_TOP          
            154_0  COME_FROM           136  '136'
            154_1  COME_FROM            90  '90'

 L. 876       154  SETUP_LOOP          180  'to 180'
              156  LOAD_FAST                'self'
              158  LOAD_ATTR                options
              160  GET_ITER         
              162  FOR_ITER            178  'to 178'
              164  STORE_FAST               'option'

 L. 876       166  LOAD_FAST                'option'
              168  LOAD_METHOD              blockSignals
              170  LOAD_CONST               False
              172  CALL_METHOD_1         1  '1 positional argument'
              174  POP_TOP          
              176  JUMP_BACK           162  'to 162'
              178  POP_BLOCK        
            180_0  COME_FROM_LOOP      154  '154'

Parse error at or near `COME_FROM_LOOP' instruction at offset 90_0

    def save(self, info):
        if self.options[3].isChecked():
            info['type'] = QueryType.TITLES.value
        else:
            if 'type' in info:
                del info['type']
            else:
                excludes = []
                if not self.options[0].isChecked():
                    excludes.append('body')
                if not self.options[1].isChecked():
                    excludes.append('foot')
                if not self.options[2].isChecked():
                    excludes.append('comment')
                if excludes:
                    info['excludes'] = excludes
                else:
                    if 'excludes' in info:
                        del info['excludes']

    def load(self, info):
        if 'type' in info:
            body, foot, comment, titles = (False, False, False, True)
        else:
            body, foot, comment, titles = (True, True, True, False)
            if 'excludes' in info:
                if 'body' in info['excludes']:
                    body = False
                if 'foot' in info['excludes']:
                    foot = False
                if 'comment' in info['excludes']:
                    comment = False
        self.options[0].setChecked(body)
        self.options[1].setChecked(foot)
        self.options[2].setChecked(comment)
        self.options[3].setChecked(titles)