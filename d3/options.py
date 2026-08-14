# decompyle3 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: options.py
import os.path, subprocess, sys
from copy import deepcopy
from threading import Thread
import datetime
from qtpy.QtCore import QCoreApplication, QEvent, QLocale, QSize, QTimer, QUrl, Signal, Qt
from qtpy.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QIntValidator, QKeyEvent, QPainter, QPixmap
from qtpy.QtWidgets import QProgressBar, QScrollArea, QRadioButton, QGroupBox, QComboBox, QListWidgetItem, QLineEdit, QListWidget, QListView, QGridLayout, QLabel, QPushButton, QWidget, QApplication, QTextBrowser, QCheckBox, QStackedWidget, QFileDialog, QColorDialog, QDialogButtonBox, QFontDialog, QSpinBox
from across import Across
from customs import customLayout, QtFont, hLine, registerFonts, LineEdit, customMessage, listFit, image, CustomDialog, NumCombo, minSize, checkAllPdf, clickableLabel, pack, unpack
from dirs import isWritable
from theme import Icon
from settings import Settings
from textmanager import tip, noTashkeel, arabize, latinize, displayDigits
from engine import getComments, Book
from dbmanager import BookDb
from platformutils import desktop_dir, menu_shortcut_supported
OPTIONS_WIDTH = 700
OPTIONS_HEIGHT = 775
OPTIONS_LIST_WIDTH = 150
OPTIONS_BOX_HEIGHT = 70
_restart_effective_values = None

def _get_restart_baseline():
    """Return the settings that were in effect when the app started.

    This dict is populated lazily the first time the options dialog is used
    and never mutated afterwards, so the restart hint stays visible even after
    the user presses Apply/OK and re-opens the dialog.
    """
    global _restart_effective_values
    if _restart_effective_values is None:
        _restart_effective_values = {'theme_mode':Settings._storedValue('theme_mode'),  'use_modern_design':Settings._storedValue('use_modern_design'), 
         'use_modern_icons':Settings._storedValue('use_modern_icons'), 
         'system_numbers':Settings._storedValue('system_numbers')}
    return _restart_effective_values


def scroll(widget, stack):
    container = QScrollArea()
    container.setWidgetResizable(True)
    container.setWidget(widget)
    stack.addWidget(container)
    return container


def flat(label, layout):
    group = QGroupBox(f" {label}    ") if label else QGroupBox()
    group.setFlat(True)
    group.setLayout(layout)
    return group


def default_layout(func):
    return customLayout(False, [0, default_button(func)])


def default_button(func):
    button = QPushButton(QCoreApplication.translate('MainWindow', 'Default'))
    button.setToolTip(tip(QCoreApplication.translate('MainWindow', 'Return to the default Settings')))
    button.clicked.connect(func)
    return button


def customButtonBox():
    box = QDialogButtonBox()
    box.addButton(QCoreApplication.translate('MainWindow', 'OK'), QDialogButtonBox.AcceptRole)
    box.addButton(QCoreApplication.translate('MainWindow', 'Cancel'), QDialogButtonBox.RejectRole)
    return box


def page_default_layout(text, func):
    button = QPushButton(text)
    button.setToolTip(tip(QCoreApplication.translate('MainWindow', 'Return to the default Settings')))
    button.clicked.connect(func)
    return customLayout(False, [0, button], margins=0)


def _shouldStoreExactFontStyle(style_name, weight):
    if weight not in (int(QFont.Normal), int(QFont.Bold)):
        return True
    lowered = style_name.casefold()
    markers = ('black', 'heavy', 'semi', 'demi', 'extra', 'light', 'medium')
    return any((marker in lowered for marker in markers))


def lFont(qt_font):
    font = [
     qt_font.family(), qt_font.pointSize(), qt_font.bold(), qt_font.italic()]
    if hasattr(qt_font, 'styleName'):
        style_name = qt_font.styleName().strip() if qt_font.styleName() else ''
        if hasattr(qt_font, 'weight'):
            int(qt_font.weight())
        else:
            pass
        weight = int(QFont.Bold) if qt_font.bold() else int(QFont.Normal)
        if _shouldStoreExactFontStyle(style_name, weight):
            font.extend([weight, style_name])
        return font


def QtColor(l_color):
    return QColor(l_color[0], l_color[1], l_color[2])


def lColor(qt_color):
    tup = qt_color.getRgb()
    return [
     tup[0], tup[1], tup[2]]


def availablePath(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    count = 1
    while True:
        candidate = f"{base}_{count}{ext}"
        if not os.path.exists(candidate):
            return candidate
        else:
            count += 1


class FontWidget(QFontDialog):

    def __init__(self, lang=None):
        super().__init__()
        self.setSizeGripEnabled(False)
        self.setOptions(QFontDialog.NoButtons | QFontDialog.ProportionalFonts | QFontDialog.DontUseNativeDialog)
        self.setLayoutDirection(Qt.LeftToRight)
        self.findChildren(QGroupBox)[0].hide()
        box = self.findChildren(QGroupBox)[1]
        box.setMinimumHeight(110)
        box.setAlignment(Qt.AlignRight)
        box.setTitle('نموذج')
        texts = ('الخط', 'نمط الخط', 'الحجم', 'شكل الخط')
        for i in range(4):
            label = self.findChildren(QLabel)[i]
            label.setText(texts[i])

        if lang:
            combo = self.findChildren(QComboBox)[0]
            index = combo.findText(lang)
            if index >= 0:
                combo.setCurrentIndex(index)
                combo.activated.emit(index)
        self.findChildren(QLineEdit)[3].setText(QCoreApplication.translate('MainWindow', 'He is Allah One'))

    def setCurrentFont(self, font):
        super().setCurrentFont(font)
        self._syncStyleControls(font)

    def _syncStyleControls(self, font):
        style_text = self._resolvedStyleText(font)
        if not style_text:
            return
        line_edits = self.findChildren(QLineEdit)
        if len(line_edits) > 1:
            if line_edits[1].isReadOnly():
                line_edits[1].setText(style_text)
        list_views = self.findChildren(QListView)
        if len(list_views) > 1:
            style_view = list_views[1]
            model = style_view.model()
            if model:
                for row in range(model.rowCount()):
                    index = model.index(row, 0)
                    if str(index.data()).strip().casefold() == style_text.casefold():
                        style_view.setCurrentIndex(index)
                        break

    def _resolvedStyleText(self, font):
        styles = [style for style in QFontDatabase().styles(font.family()) if style]
        if not styles:
            if font.bold():
                return 'Bold'
            return 'Regular'
        preferred = []
        if font.bold() and font.italic():
            preferred = ('bold italic', 'bold oblique', 'demi bold italic', 'demi bold oblique')
        else:
            if font.bold():
                preferred = ('bold', 'demi bold', 'black', 'heavy')
            else:
                if font.italic():
                    preferred = ('italic', 'oblique')
                else:
                    preferred = ('regular', 'normal', 'roman', 'book', 'plain', 'medium')
        lowered = [(style, style.casefold()) for style in styles]
        for wanted in preferred:
            for style, lowered_style in lowered:
                if wanted in lowered_style:
                    return style

        if not font.bold():
            if not font.italic():
                for style, lowered_style in lowered:
                    if 'bold' not in lowered_style:
                        if 'italic' not in lowered_style:
                            if 'oblique' not in lowered_style:
                                return style

            return QFontDatabase().styleString(font) or styles[0]


def colorWidget():
    color = QColorDialog()
    color.setOptions(QColorDialog.NoButtons | QColorDialog.DontUseNativeDialog)
    color.setSizeGripEnabled(False)
    color.setLayoutDirection(Qt.LeftToRight)
    texts = ('الألوان الأساسية', '', 'الألوان المخصصة', 'التدرج', 'الإشباع', 'الإضاءة',
             'أحمر', 'أخضر', 'أزرق', '', 'نص فائق')
    labels = color.findChildren(QLabel)
    for i in range(len(texts)):
        if i < len(labels):
            label = labels[i]
            label.setAlignment(Qt.AlignLeft)
            label.setText(texts[i])

    buttons = color.findChildren(QPushButton)
    if len(buttons) > 1:
        buttons[1].setText('إضافة للألوان المخصصة')
    if buttons:
        buttons[0].hide()
    return color


def colorBox(l_color, size=20):
    """Returns a Icon.icon from the given color and size"""
    color = QtColor(l_color)
    pixmap = QPixmap(size, size)
    pixmap.fill(color)
    p = QPainter(pixmap)
    p.drawRect(0, 0, size - 1, size - 1)
    p.end()
    icon = QIcon(pixmap)
    icon.addPixmap(pixmap, QIcon.Selected)
    return icon


def stableIcon(path):
    return Icon.icon(path)


class SpinBox(QSpinBox):

    def __init__(self):
        super().__init__()
        self._applyDigitPolicy()
        e = QKeyEvent(QEvent.KeyPress, Qt.Key_Direction_R, Qt.NoModifier)
        QApplication.sendEvent(self, e)

    def _applyDigitPolicy(self):
        if Settings.getValue('system_numbers'):
            self.setLocale(QLocale())
        else:
            self.setLocale(QLocale(QLocale.Arabic, QLocale.Egypt))

    def focusInEvent(self, event):
        self._applyDigitPolicy()
        QTimer.singleShot(0, self.selectAll)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        self._applyDigitPolicy()
        redirection = False
        text = event.text()
        if text:
            if latinize(text).isdigit():
                e = QKeyEvent((QEvent.KeyPress), 0, (Qt.NoModifier), text=(displayDigits(text)))
                super().keyPressEvent(e)
                redirection = True
        if not redirection:
            super().keyPressEvent(event)


class AttributeOptions(QWidget):

    def __init__(self):
        super().__init__()
        self.keys = []
        self.options = []
        self.sample_dict = {'page':'5/ 93', 
         'book':'الكمال في أسماء الرجال'}
        self.sample_dict['text'] = '[2767] سالم بن سَرْج -بالسين المهملة، والجيم- أبو النُّعْمان، ويقال: سالم بن النعمان، ويقال: ابن خَرَّبُوذ المدني، مولي أُم صُبيَّة (1).\nقال الحاكم: من قال ابن سُرْج؛ عَرَّبَهُ، ومن قال: ابن خَرَّبُوذ؛ أراد به الإكاف بالفارسيَّة'
        self.keys.append('brackets_attr')
        self.options.append(SettingCheck(self.tr('Surrounding Attributes by quotation'), self.keys[-1]))
        self.keys.append('helal_attr')
        self.options.append(SettingCheck(self.tr('Surrounding Attribute Numbers by brackets'), self.keys[-1]))
        self.keys.append('angular_attr')
        self.options.append(SettingCheck(self.tr('Surrounding the Whole Attribute by brackets'), self.keys[-1]))
        self.keys.append('attr_before')
        self.options.append(SettingCheck(self.tr('Placing Attributes before Nass'), self.keys[-1]))
        self.keys.append('attr_newline')
        self.options.append(SettingCheck(self.tr('Attributes in new line'), self.keys[-1]))
        self.keys.append('brackets_nass')
        self.options.append(SettingCheck(self.tr('Surrounding Nass by quotation'), self.keys[-1]))
        self.keys.append('undiacritize_copied')
        self.options.append(SettingCheck(self.tr('Remove diacritics from copied nass'), self.keys[-1]))
        self.keys.append('unsuperscript_copied')
        self.options.append(SettingCheck(self.tr('Remove Footnotes Numbers from copied nass'), self.keys[-1]))
        self.keys.append('copy_formatted')
        self.options.append(SettingCheck(self.tr('Copy text with formatting'), self.keys[-1]))
        for option in self.options:
            option.stateChanged.connect(self.reSample)

        self.sample = QTextBrowser()
        self.sample.setFont(QtFont(['Traditional Naskh', 16, True, False]))
        group_attr = QGroupBox(self.tr('Attribute'))
        group_attr.setLayout(customLayout(True, ([2] + self.options[:3]), margins=6, spacing=2))
        group_attr_pos = QGroupBox(self.tr('Attribute Position'))
        group_attr_pos.setLayout(customLayout(True, ([2] + self.options[3:5]), margins=6, spacing=2))
        group_text = QGroupBox(self.tr('Copied Text'))
        group_text.setLayout(customLayout(True, ([2] + self.options[5:]), margins=6, spacing=2))
        group_sample = QGroupBox(self.tr('Sample'))
        group_sample.setLayout(customLayout(True, [3, self.sample], margins=6, spacing=2))
        self.reSample()
        layout_list = [
         default_layout(self.restoreDefault), 2, hLine(), 10, group_attr, 10, group_attr_pos, 10,
         group_text, 10, group_sample, 0]
        self.setLayout(customLayout(True, layout_list, margins=6, spacing=5))

    def reSample(self):
        brackets = ('[', ']') if self.options[2].isChecked() else ('', '')
        colon = ':' if self.options[3].isChecked() else ''
        separator = '\n' if self.options[4].isChecked() else ' ' if self.options[3].isChecked() else '. '
        book = f"«{self.sample_dict['book']}»" if self.options[0].isChecked() else self.sample_dict['book']
        page = f"({self.sample_dict['page']})" if self.options[1].isChecked() else self.sample_dict['page']
        text = self.sample_dict['text']
        if self.options[6].isChecked():
            text = noTashkeel(text)
        if self.options[7].isChecked():
            text = text.replace(' (1)', '')
        if self.options[5].isChecked():
            text = f"«{text}»"
        text = f"{brackets[0]}{book} {page}{brackets[1]}{colon}{separator}{text}" if self.options[3].isChecked() else f"{text}{separator}{brackets[0]}{book} {page}{colon}{brackets[1]}"
        self.sample.setText(arabize(text, forced=True))

    def restoreDefault(self):
        for option in self.options:
            option.restoreDefault()

    def ok(self):
        for option in self.options:
            option.ok()


class PdfOptions(QWidget):

    def __init__(self):
        from dirs import defaultPdfPath
        super().__init__()
        message = '• ' + self.tr('Changing the Folder does not Move or copy any files')
        message += '\n\n• ' + self.tr('You should move any files yourself to the new folder')
        label = optionLabel(message)
        self.keys = ['pdf_folder']
        labels = (
         self.tr('Pdf Folder'), self.tr('Pdf Check'), self.tr('Check Pdf files to detect any defects'), self.tr('Pdf Checking Done'))
        self.select_folder = SelectFolder((self.keys[-1]), (defaultPdfPath()), labels, check_function=checkAllPdf)
        self.options = [self.select_folder]
        layout_list = [
         default_layout(self.restoreDefault), 1, hLine(), 10, label, 10, hLine(), 10, self.options[0], 0]
        self.setLayout(customLayout(True, layout_list, margins=6, spacing=6))

    def restoreDefault(self):
        for option in self.options:
            option.restoreDefault()

    def ok(self):
        for option in self.options:
            option.ok()


class DownloadMessage(CustomDialog):

    def __init__(self, books, parent):
        from cache import BookCache
        super().__init__(parent=parent, geometry_name='download_message')
        self.setWindowTitle(self.tr('Add Comments'))
        minSize(self, 300, 200)
        message = '• ' + self.tr('No comments are added because some of them are on undownloaded books')
        message += '\n• ' + self.tr('You can download these books, then add comments')
        message += '\n• ' + self.tr('These are the books that need to be downloaded')
        label = QLabel(message)
        label.setFont(QtFont(['Traditional Naskh', 12, True, False]))
        list_items = QListWidget()
        list_items.addItems([BookCache.abstractName(book_id) for book_id in books])
        button = QPushButton(self.tr('Ok'))
        button.clicked.connect(self.close)
        button = customLayout(False, [0, button, 0])
        self.setLayout(customLayout(True, [3,label,3,list_items,button], margins=3, spacing=3))


def optionLabel(message):
    label = QLabel(message)
    label.setFont(QtFont(['Traditional Naskh', 14, True]))
    return label


class CommentsExchange(QWidget):
    progress_signal = Signal(dict)

    def __init__(self):
        super().__init__()
        caption = optionLabel(self.tr('Exchange comments'))
        caption = customLayout(False, [0, caption, 0, image(':/icons/hint.png', 30)])
        message = '• ' + self.tr('You can save all your comments to a file')
        message += '\n\n• ' + self.tr('Then You can this file or add to another copy of the software')
        label = optionLabel(message)
        self.exportButon = QPushButton(self.tr('Save Comments'))
        self.exportButon.setToolTip(self.tr('Save Comments to a file'))
        self.exportButon.clicked.connect(self.saveComments)
        self.importButon = QPushButton(self.tr('Add Comments'))
        self.importButon.setToolTip(self.tr('Add Comments to a file'))
        self.importButon.clicked.connect(self.loadComments)
        self.progressBar = QProgressBar()
        self.progressBar.setMaximumHeight(10)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.progressBar.setVisible(False)
        self.progress_signal.connect(self.progress)
        button_lay = customLayout(False, [0, self.exportButon, 6, self.importButon])
        layout_list = [6, caption, 3, hLine(), 10, label, 10, hLine(), 3, button_lay, 3, self.progressBar, 0]
        self.setLayout(customLayout(True, layout_list, margins=6, spacing=6))

    def switchBusy(self, value):
        self.exportButon.setEnabled(not value)
        self.importButon.setEnabled(not value)
        self.progressBar.setVisible(value)

    def saveComments(self):
        self.switchBusy(True)
        comments = getComments()
        if comments:
            folder_path = os.path.join(desktop_dir(), 'تعليقات الشاملة')
            os.makedirs(folder_path, exist_ok=True)
            file_path = availablePath(os.path.join(folder_path, f"{datetime.date.today()}.pk"))
            pack(comments, file_path)
            self.switchBusy(False)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        else:
            self.switchBusy(False)
            customMessage(self.tr('comments'), self.tr('No comments are there'))

    def loadComments(self):
        desktop_path = desktop_dir()
        folder_path = os.path.join(desktop_path, 'تعليقات الشاملة')
        current_path = folder_path if os.path.isdir(folder_path) else desktop_path
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(self, (self.tr('Open File')), current_path, 'pk Files (*.pk)', options=options)
        if file_path:
            self.importFile(file_path)

    def importThread(self, comments):
        error = None
        count = len(comments)
        self.progress_signal.emit({'start': count})
        for i, s_book_id in enumerate(comments, 1):
            self.progress_signal.emit({'value': i})
            book_id = int(s_book_id)
            mapped_comments = BookDb(book_id).mappedComments(comments[s_book_id])
            book = Book(book_id)
            if not book.addComments(mapped_comments):
                error = True
                continue
            else:
                book.commitBook()

        self.progress_signal.emit({'end': 'لم يمكن إضافة التعليقات. لعل الملف المحدد تالف' if error else 'تم إضافة التعليقات للمكتبة'})

    def importFile(self, file_path):
        from dbmanager import CoreDb
        try:
            comments = unpack(file_path)
            if comments:
                core_db = CoreDb()
                online_books = [book for book in comments.keys() if not core_db.isOnDisk(book)]
                if online_books:
                    all_books = core_db.allBooks()
                    online_books = [book for book in all_books if book in online_books]
                    DownloadMessage(online_books, self).show()
                    return
                Thread(target=(self.importThread), args=(comments,)).start()
        except:
            return

    def progress(self, value):
        if 'start' in value:
            self.progressBar.setMinimum(0)
            self.progressBar.setMaximum(value['start'])
            self.switchBusy(True)
        if 'value' in value:
            self.progressBar.setValue(value['value'])
        if 'end' in value:
            self.switchBusy(False)
            customMessage('إضافة التعليقات', value['end'])


class QuranFontOptions(QWidget):
    previewChanged = Signal()
    _SIZE_KEYS = (('majma_size', 'majma_spacing'), ('amiri_size', 'amiri_spacing'),
                  ('emlaa_size', 'emlaa_spacing'))

    def __init__(self):
        super().__init__()
        self.num_list = [
         6,7,8,9,10,11,12,14,16,18,20,22,24,26,28,36,48,72]
        self.line_values = [i / 10 for i in range(5, 31)]
        self._groups = []
        self.comboMajma, self.lineMajma, group_majma = self._fontGroup(self.tr('Majma Font size'), 'majma_size', 'majma_spacing')
        self.comboAmiri, self.lineAmiri, group_amiri = self._fontGroup(self.tr('Amiri Font size'), 'amiri_size', 'amiri_spacing')
        self.comboEmlaa, self.lineEmlaa, group_emlaa = self._fontGroup(self.tr('Emlaa Font size'), 'emlaa_size', 'emlaa_spacing')
        self.comboAttr = NumCombo(num_list=(self.num_list), force_ascii=True)
        self.comboAttr.setValidator(QIntValidator(1, 100))
        self.comboAttr.setValue(Settings.getValue('attribute_size'))
        group_attr = flat(self.tr('Aya Attribution Font size'), customLayout(False, [0, self.comboAttr]))
        self.setLayout(customLayout(True, [default_layout(self.restoreDefault), 2, hLine(), 10,
         group_majma, 20,
         group_amiri, 20,
         group_emlaa, 20,
         group_attr, 0],
          margins=6))

    def _fontGroup(self, title, size_key, spacing_key):
        size_combo = NumCombo(num_list=(self.num_list), force_ascii=True)
        size_combo.setValidator(QIntValidator(1, 100))
        size_combo.setValue(Settings.getValue(size_key))
        line_combo = self._lineCombo()
        self._setLine(line_combo, Settings.getValue(spacing_key))
        group = flat(title, customLayout(False, [
         0, size_combo, 16, QLabel(self.tr('Line spacing')), 6, line_combo]))
        size_combo.currentTextChanged.connect(lambda _: self.previewChanged.emit()
)
        line_combo.currentIndexChanged.connect(lambda _: self.previewChanged.emit()
)
        self._groups.append((size_combo, line_combo, size_key, spacing_key))
        return (
         size_combo, line_combo, group)

    def _lineCombo(self):
        combo = QComboBox()
        combo.setEditable(False)
        combo.setMinimumWidth(70)
        combo.addItems([str(v) for v in self.line_values])
        return combo

    def _setLine(self, combo, value):
        value = round(float(value), 1)
        if value in self.line_values:
            combo.setCurrentIndex(self.line_values.index(value))
        else:
            combo.setCurrentText(str(value))

    def _lineValue(self, combo):
        return float(combo.currentText())

    def restoreDefault(self):
        for size_combo, line_combo, size_key, spacing_key in self._groups:
            size_combo.setValue(Settings.getDefault(size_key))
            self._setLine(line_combo, Settings.getDefault(spacing_key))

        self.comboAttr.setValue(Settings.getDefault('attribute_size'))
        self.previewChanged.emit()

    def previewValues(self):
        values = {}
        for size_combo, line_combo, size_key, spacing_key in self._groups:
            values[size_key] = size_combo.value()
            values[spacing_key] = self._lineValue(line_combo)

        return values

    def preview(self):
        window = self.window()
        if hasattr(window, 'previewSettings'):
            window.previewSettings(self.previewValues())

    def ok(self):
        for size_combo, line_combo, size_key, spacing_key in self._groups:
            Settings.setValue(size_key, size_combo.value(), False)
            Settings.setValue(spacing_key, self._lineValue(line_combo), False)

        Settings.setValue('attribute_size', self.comboAttr.value(), False)


class OptionsWindow(CustomDialog):
    _THEME_MISSING = object()

    def __init__(self, parent=None):
        super().__init__(parent=parent, geometry_name='options', icon=':/icons/options.png')
        self._accepted = False
        self._preview_dirty = False
        self._preview_snapshot = self._settingsSnapshot()
        self.setWindowTitle(self.tr('Options'))
        self.fonts = self.colors = self.misc = self.shut = self.aya_copy = self.attribute_options = self.pdf_folder = self.display = self.comments_exchange = self.theme = None
        self._page_slots = [self.showTheme, self.showColors, self.showFonts, self.showAyaCopy,
         self.showAttributeOptions, self.showDisplay, self.showMisc,
         self.showPdfFolder, self.showCommentsExchange]
        items = [self.tr('Theme'), self.tr('Colors'), self.tr('Fonts'), self.tr('Holy Quran Font'),
         self.tr('Nass Attribution'), self.tr('Book Display'), self.tr('Other settings'),
         self.tr('Pdf Folder'), self.tr('Comments')]
        self.icons = ('theme', 'color', 'font', 'quran', 'copy', 'open_book', 'setting',
                      'pdf', 'hint')
        self.optionslist = QListWidget()
        self.optionslist.setFont(QtFont(['Traditional Naskh', 14, True]))
        self.optionslist.setFixedWidth(OPTIONS_LIST_WIDTH)
        self.optionslist.setIconSize(QSize(20, 20))
        for icon, item in zip(self.icons, items):
            self.optionslist.addItem(QListWidgetItem(stableIcon(':/icons/' + icon), ' ' + item))

        self.stack = QStackedWidget()
        self._preview_button = QPushButton(QCoreApplication.translate('MainWindow', 'Preview'))
        self._preview_button.hide()
        ok_btn = QPushButton(QCoreApplication.translate('MainWindow', 'OK'))
        self._apply_button = QPushButton(QCoreApplication.translate('MainWindow', 'Apply'))
        cancel_btn = QPushButton(QCoreApplication.translate('MainWindow', 'Cancel'))
        self._restart_hint = QLabel(QCoreApplication.translate('MainWindow', 'Some changes require a restart to take effect'))
        self._restart_hint.hide()
        self._restart_now_btn = QPushButton(QCoreApplication.translate('MainWindow', 'Now'))
        self._restart_now_btn.setToolTip(tip(QCoreApplication.translate('MainWindow', 'Apply All changes and Restart the Application now')))
        self._restart_now_btn.hide()
        self._restart_now_btn.clicked.connect(self._restartNow)
        box_lay = customLayout(False, [
         4, self._restart_hint, 2, self._restart_now_btn, 0, self._preview_button, 8, self._apply_button, 8, ok_btn, 8, cancel_btn, 4])
        layout = customLayout(False, [self.optionslist, 1, self.stack], [3, 5, 3, 3])
        self.setLayout(customLayout(True, [layout, box_lay]))
        width, height = minSize(self, OPTIONS_WIDTH, OPTIONS_HEIGHT, True)
        self.stack.setMinimumWidth(width - OPTIONS_LIST_WIDTH)
        self.stack.setMinimumHeight(height - OPTIONS_BOX_HEIGHT)
        self.optionslist.currentRowChanged.connect(self._showPageForRow)
        ok_btn.clicked.connect(self.ok)
        cancel_btn.clicked.connect(self.close)
        self._preview_button.clicked.connect(self._previewCurrentPage)
        self._apply_button.clicked.connect(self._onApply)

    def _previewKeys(self):
        keys = [
         'font_pages',
         'font_pages_spacing',
         'font_matn',
         'font_footnotes',
         'font_footnotes_spacing',
         'font_comments',
         'font_comments_spacing',
         'font_betaka',
         'font_betaka_spacing',
         'font_tree',
         'font_search_tables',
         'font_standard',
         'majma_size',
         'majma_spacing',
         'amiri_size',
         'amiri_spacing',
         'emlaa_size',
         'emlaa_spacing',
         'attribute_size']
        for key in Settings.COLOR_KEYS:
            keys.append(key)
            keys.append(f"{key}_dark")

        return keys

    def _settingsSnapshot(self):
        Settings.getValue('theme_mode')
        return {key: deepcopy(Settings._cache[key]) if key in Settings._cache else self._THEME_MISSING for key in self._previewKeys()}

    def _changedPreviewKeys(self, before_snapshot, after_snapshot):
        return {key for key in self._previewKeys() if before_snapshot.get(key, self._THEME_MISSING) != after_snapshot.get(key, self._THEME_MISSING)}

    def _restorePreviewSnapshot(self):
        current_snapshot = self._settingsSnapshot()
        changed_keys = self._changedPreviewKeys(current_snapshot, self._preview_snapshot)
        Settings.getValue('theme_mode')
        for key, value in self._preview_snapshot.items():
            if value is self._THEME_MISSING:
                Settings._cache.pop(key, None)
            else:
                Settings._cache[key] = deepcopy(value)

        self._preview_dirty = False
        if changed_keys:
            self._refreshPreview(changed_keys)

    def previewSettings(self, values):
        Settings.getValue('theme_mode')
        for key, value in values.items():
            Settings._cache[key] = deepcopy(value)

        self._preview_dirty = True
        self._refreshPreview(set(values))

    def _refreshPreview(self, changed_keys=None):
        from theme import refreshPreviewWidgets
        refreshPreviewWidgets(changed_keys=changed_keys)

    def _defaultPageIcon(self):
        if self.icons:
            return self.icons[0]

    def _rowForPage(self, page=None):
        from dbmanager import UserDb
        if not page:
            page = UserDb().load('last_options_page', self._defaultPageIcon())
        if not page:
            return -1
        try:
            return self.icons.index(page)
        except ValueError:
            if self.optionslist.count():
                return 0
            return -1

    def _showPageForRow(self, row):
        if row < 0 or row >= len(self._page_slots):
            return
        self._page_slots[row]()
        self._updatePreviewButton()

    def _currentPageWidget(self):
        container = self.stack.currentWidget()
        if isinstance(container, QScrollArea):
            return container.widget()
        return container

    def _updatePreviewButton(self):
        page = self._currentPageWidget()
        getter = getattr(page, 'previewValues', None)
        values = getter() if callable(getter) else None
        self._preview_button.setVisible(callable(getter))
        self._preview_button.setEnabled(bool(values) and self._previewWouldChange(values))

    def _previewWouldChange(self, values):
        return any((Settings._storedValue(key) != value for key, value in values.items()))

    def _previewCurrentPage(self):
        page = self._currentPageWidget()
        preview = getattr(page, 'preview', None)
        if callable(preview):
            preview()
        self._updatePreviewButton()

    def _ensureCurrentPage(self):
        row = self.optionslist.currentRow()
        if row < 0 or row >= len(self._page_slots):
            row = self._rowForPage()
            if row >= 0:
                self.optionslist.setCurrentRow(row)
                if self.optionslist.currentRow() == row:
                    if not self.stack.currentWidget():
                        self._showPageForRow(row)
            return
        if not self.stack.currentWidget():
            self._showPageForRow(row)

    def show(self):
        self._ensureCurrentPage()
        super().show()
        self._updateRestartHint()

    def goPage(self, page, highlight=None):
        row = self._rowForPage(page)
        if row >= 0:
            self.optionslist.setCurrentRow(row)
            if self.optionslist.currentRow() == row:
                if not self.stack.currentWidget():
                    self._showPageForRow(row)
                if highlight:
                    if self.misc:
                        self.misc.highlightKey(highlight)

    def showCommentsExchange(self):
        if not self.comments_exchange:
            self.comments_exchange = CommentsExchange()
            self.comments_container = scroll(self.comments_exchange, self.stack)
        self.stack.setCurrentWidget(self.comments_container)

    def showTheme(self):
        if not self.theme:
            self.theme = ThemeWidget()
            self.theme_container = scroll(self.theme, self.stack)
        self.stack.setCurrentWidget(self.theme_container)

    def showFonts(self):
        if not self.fonts:
            self.fonts = FontsWidget()
            self.fonts.previewChanged.connect(self._updatePreviewButton)
            self.font_container = scroll(self.fonts, self.stack)
        self.stack.setCurrentWidget(self.font_container)

    def showColors(self):
        if not self.colors:
            self.colors = ColorsWidget()
            self.colors.previewChanged.connect(self._updatePreviewButton)
            self.color_container = scroll(self.colors, self.stack)
        self.stack.setCurrentWidget(self.color_container)

    def showAyaCopy(self):
        if not self.aya_copy:
            self.aya_copy = QuranFontOptions()
            self.aya_copy.previewChanged.connect(self._updatePreviewButton)
            self.aya_copy_container = scroll(self.aya_copy, self.stack)
        self.stack.setCurrentWidget(self.aya_copy_container)

    def showDisplay(self):
        if not self.display:
            self.display = DisplayOptions()
            self.display_container = scroll(self.display, self.stack)
        self.stack.setCurrentWidget(self.display_container)

    def showPdfFolder(self):
        if not self.pdf_folder:
            self.pdf_folder = PdfOptions()
            self.pdf_folder_container = scroll(self.pdf_folder, self.stack)
        self.stack.setCurrentWidget(self.pdf_folder_container)

    def showAttributeOptions(self):
        if not self.attribute_options:
            self.attribute_options = AttributeOptions()
            self.attribute_options_container = scroll(self.attribute_options, self.stack)
        self.stack.setCurrentWidget(self.attribute_options_container)

    def showMisc(self):
        if not self.misc:
            self.misc = SettingWidget()
            self.misc_container = scroll(self.misc, self.stack)
        self.stack.setCurrentWidget(self.misc_container)

    def closeEvent(self, event):
        if not self._accepted:
            if self._preview_dirty:
                self._restorePreviewSnapshot()
        super().closeEvent(event)
        from dbmanager import UserDb
        row = self.optionslist.currentRow()
        if row < 0 or row >= len(self.icons):
            row = 0
        if row >= 0:
            UserDb().save('last_options_page', self.icons[row])

    def _updateRestartHint(self):
        baseline = _get_restart_baseline()
        if self.theme:
            theme_needs = self.theme.needsRestart()
        else:
            stored = ThemeWidget._appearanceState(Settings._storedValue('theme_mode'), Settings._storedValue('use_modern_design'), Settings._storedValue('use_modern_icons'))
            base = ThemeWidget._appearanceState(baseline['theme_mode'], baseline['use_modern_design'], baseline['use_modern_icons'])
            theme_needs = stored != base
        if self.misc:
            misc_needs = self.misc.needsRestart()
        else:
            misc_needs = Settings._storedValue('system_numbers') != baseline['system_numbers']
        visible = bool(theme_needs or misc_needs)
        self._restart_hint.setVisible(visible)
        self._restart_now_btn.setVisible(visible)

    def _saveAll(self, refresh_preview=True):
        preview_before_apply = self._settingsSnapshot()
        if self.theme:
            self.theme.ok()
        if self.fonts:
            self.fonts.ok()
        if self.colors:
            self.colors.ok()
        if self.aya_copy:
            self.aya_copy.ok()
        if self.misc:
            self.misc.ok()
        if self.attribute_options:
            self.attribute_options.ok()
        if self.pdf_folder:
            self.pdf_folder.ok()
        if self.display:
            self.display.ok()
        Settings.saveAll()
        current_snapshot = self._settingsSnapshot()
        if refresh_preview:
            changed_keys = self._changedPreviewKeys(preview_before_apply, current_snapshot)
            if changed_keys:
                self._refreshPreview(changed_keys)
        self._preview_snapshot = current_snapshot
        self._preview_dirty = False
        self._updateRestartHint()
        self._updatePreviewButton()

    def _onApply(self):
        self._saveAll(refresh_preview=True)

    def _applyAndRestart(self):
        self._saveAll(refresh_preview=False)
        QApplication.processEvents()
        try:
            import shamela as _sh
            _sh.restart_direct()
        except Exception:
            pass

        Across.main_window.close()

    def _restartNow(self):
        self._applyAndRestart()

    def ok(self):
        self._accepted = True
        self.hide()
        QApplication.processEvents()
        self._saveAll(refresh_preview=True)
        self.close()


class FontsWidget(QWidget):
    previewChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        titles = (
         self.tr('Font of pages text'),
         self.tr('Font of Matn'),
         self.tr('Font of footnotes'),
         self.tr('Font of comments'),
         self.tr('Font of bibliography'),
         self.tr('Font of titles tree'),
         self.tr('Font of search results table'),
         self.tr('Font of book lists and such'))
        self.keys = ('font_pages', 'font_matn', 'font_footnotes', 'font_comments',
                     'font_betaka', 'font_tree', 'font_search_tables', 'font_standard')
        self.line_keys = ('font_pages_spacing', 'font_footnotes_spacing', 'font_comments_spacing',
                          'font_betaka_spacing')
        self.fontlist = QListWidget()
        self.fontlist.addItems(titles)
        listFit(self.fontlist)
        fixButton = QPushButton(self.tr('Register Fonts'))
        fixButton.setToolTip(self.tr('Register required fonts to the system'))
        fixButton.clicked.connect(self.fixFonts)
        self._restore_default_btn = default_button(self.restoreDefault)
        i = image(':/images/font.png', 70)
        i = customLayout(False, [i], margins=0)
        img_col = customLayout(True,
          [
         0, i, 0, self._restore_default_btn],
          margins=0)
        restore_all_btn = QPushButton(self.tr('Default for all fonts'))
        restore_all_btn.setToolTip(tip(QCoreApplication.translate('MainWindow', 'Return to the default Settings')))
        restore_all_btn.clicked.connect(self.restoreAllDefaults)
        top_row = customLayout(False, [fixButton, 0, restore_all_btn], margins=0)
        listlayout = customLayout(False, [self.fontlist, 5, img_col])
        label = QLabel(self.tr('Line spacing'))
        self.line_combo = QComboBox()
        self.line_combo.setEditable(False)
        self.line_combo.setMinimumWidth(70)
        self.line_values = [i / 10 for i in range(5, 31)]
        self.line_combo.addItems([str(i) for i in self.line_values])
        self.line = QWidget()
        sp = self.line.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.line.setSizePolicy(sp)
        self.line.setLayout(customLayout(False, [10, label, 10, self.line_combo, 0]))
        self.fontbox = FontWidget('Arabic')
        self.setLayout(customLayout(True, [
         top_row,
         hLine(), 0, listlayout, 0, hLine(),
         2, self.line, 2, self.fontbox, 10]))
        self.currents = [Settings.getValue(key) for key in self.keys]
        self.line_currents = [Settings.getValue(key) for key in self.line_keys]
        self.fontlist.setCurrentRow(0)
        self.swichFontPage(0)
        self.line_combo.currentIndexChanged.connect(self.currentLineChanged)
        self.fontlist.currentRowChanged.connect(lambda index: self.swichFontPage(index)
)
        self.fontbox.currentFontChanged.connect(lambda font: self.currentFontChanged(font, self.fontlist.currentRow())
)

    def fixFonts(self):
        registerFonts()
        customMessage(self.tr('Register Fonts'), self.tr('Necessary fonts have been registered to the system'))

    def restoreDefault(self):
        index = self.fontlist.currentRow()
        self.fontbox.setCurrentFont(QtFont((Settings.getDefault(self.keys[index])), scale=False))
        line_index = self.lineKeyIndex(index)
        if line_index is not None:
            self.line_combo.setCurrentIndex(self.line_values.index(Settings.getDefault(self.line_keys[line_index])))

    def restoreAllDefaults(self):
        self.currents = [Settings.getDefault(key) for key in self.keys]
        self.line_currents = [Settings.getDefault(key) for key in self.line_keys]
        self.swichFontPage(self.fontlist.currentRow())

    def lineKeyIndex(self, index):
        if index == 0:
            return 0
        if 2<= index <= 4:
            return index - 1

    def swichFontPage(self, index):
        font = QtFont((self.currents[index]), scale=False)
        self.fontbox.blockSignals(True)
        self.fontbox.setCurrentFont(font)
        self.fontbox.blockSignals(False)
        combo_index = self.lineKeyIndex(index)
        if combo_index is not None:
            self.line.setVisible(True)
            self.line_combo.blockSignals(True)
            self.line_combo.setCurrentIndex(self.line_values.index(self.line_currents[combo_index]))
            self.line_combo.blockSignals(False)
        else:
            self.line.setVisible(False)

    def currentFontChanged(self, font, index):
        self.currents[index] = lFont(font)
        self.previewChanged.emit()

    def currentLineChanged(self, combo_index):
        line_index = self.lineKeyIndex(self.fontlist.currentRow())
        if line_index is not None:
            self.line_currents[line_index] = self.line_values[combo_index]
            self.previewChanged.emit()

    def previewValues(self):
        values = {key: current for key, current in zip(self.keys, self.currents)}
        values.update({key: current for key, current in zip(self.line_keys, self.line_currents)})
        return values

    def previewFonts(self):
        window = self.window()
        if hasattr(window, 'previewSettings'):
            window.previewSettings(self.previewValues())

    def preview(self):
        self.previewFonts()

    def ok(self):
        for key, current in zip(self.keys, self.currents):
            Settings.setValue(key, current, False)

        for key, current in zip(self.line_keys, self.line_currents):
            Settings.setValue(key, current, False)


class ColorsWidget(QWidget):
    previewChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        titles = (
         self.tr('Color of titles'),
         self.tr('Color of search words'),
         self.tr('Color of text'),
         self.tr('Color of Matn'),
         self.tr('Color of footnotes'),
         self.tr('Color of comments'),
         self.tr('Color of punctuation'),
         self.tr('Color of men in asaneed'),
         self.tr('Color of pages background, like printed'),
         self.tr('Color of pages background, electronic'),
         self.tr('Color of comments background'))
        self.keys = ('color_titles', 'color_search', 'color_text', 'color_matn', 'color_footnotes',
                     'color_comments', 'color_punctuate', 'color_men', 'color_text_back',
                     'color_text_back_unprinted', 'color_comments_back')
        self.colortlist = QListWidget()
        for title, key in zip(titles, self.keys):
            self.colortlist.addItem(QListWidgetItem(colorBox(Settings.getValue(key)), title))

        listFit(self.colortlist)
        i = image(':/images/color.png', 70)
        i = customLayout(False, [i], margins=0)
        self.colorbox = colorWidget()
        self._current_theme = Settings.currentThemeValue()
        theme_label_text = self.tr('Colors of current theme: Dark') if self._current_theme == Settings.THEME_DARK else self.tr('Colors of current theme: Light')
        self.theme_label = QLabel(theme_label_text)
        self.theme_label.setContentsMargins(2, 4, 2, 4)
        self._restore_default_btn = default_button(self.restoreDefault)
        self._restore_all_btn = QPushButton(self.tr('Default for all colors'))
        self._restore_all_btn.setToolTip(tip(QCoreApplication.translate('MainWindow', 'Return to the default Settings')))
        self._restore_all_btn.clicked.connect(self.restoreAllDefaults)
        img_col = customLayout(True,
          [
         0, i, 0, self._restore_default_btn],
          margins=0)
        listlayout = customLayout(False, [self.colortlist, 5, img_col])
        header_row = customLayout(False, [self.theme_label, 0, self._restore_all_btn], margins=0)
        self.setLayout(customLayout(True, [
         header_row,
         hLine(), 0, listlayout, 0, hLine(),
         self.colorbox]))
        self.currents = {self._current_theme: [Settings.getColorValue(key, self._current_theme) for key in self.keys]}
        self.colortlist.setCurrentRow(0)
        self.swichColorPage(0)
        self.colortlist.currentRowChanged.connect(lambda index: self.swichColorPage(index)
)
        self.colorbox.currentColorChanged.connect(lambda color: self.currentColorChanged(color, self.colortlist.currentRow())
)

    def currentTheme(self):
        return self._current_theme

    def currentColors(self):
        return self.currents[self._current_theme]

    def restoreDefault(self):
        index = self.colortlist.currentRow()
        if index < 0:
            return
        self.colorbox.setCurrentColor(QtColor(Settings.getDefaultColor(self.keys[index], self.currentTheme())))

    def restoreAllDefaults(self):
        theme = self.currentTheme()
        self.currents[theme] = [Settings.getDefaultColor(key, theme) for key in self.keys]
        for index, current in enumerate(self.currents[theme]):
            self.colortlist.item(index).setIcon(colorBox(current))

        self.swichColorPage(self.colortlist.currentRow())
        self.previewChanged.emit()

    def swichColorPage(self, index):
        if index < 0:
            return
        self.colorbox.blockSignals(True)
        self.colorbox.setCurrentColor(QtColor(self.currentColors()[index]))
        self.colorbox.blockSignals(False)
        QTimer.singleShot(0, self.colortlist.setFocus)

    def currentColorChanged(self, color, index):
        if index < 0:
            return
        l_color = lColor(color)
        self.currentColors()[index] = l_color
        self.colortlist.item(index).setIcon(colorBox(l_color))
        self.previewChanged.emit()

    def previewValues(self):
        return Settings.themePreviewValues(self.keys, self.currents)

    def previewTheme(self):
        window = self.window()
        if hasattr(window, 'previewSettings'):
            window.previewSettings(self.previewValues())

    def preview(self):
        self.previewTheme()

    def ok(self):
        for key, current in zip(self.keys, self.currents[self._current_theme]):
            Settings.setColorValue(key, current, self._current_theme, False)


class ThemeWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_mode = SettingThemeMode(self.tr('System theme'), self.tr('Dark theme'), self.tr('Light theme'))
        self.use_modern_design = QCheckBox(self.tr('Use modern design'))
        self.use_modern_icons = QCheckBox(self.tr('Use modern icons'))
        self.use_modern_design.setChecked(Settings._storedValue('use_modern_design'))
        self.use_modern_icons.setChecked(Settings._storedValue('use_modern_icons'))
        _baseline = _get_restart_baseline()
        self._stored_state = ThemeWidget._appearanceState(_baseline['theme_mode'], _baseline['use_modern_design'], _baseline['use_modern_icons'])
        group_theme = flat('', customLayout(False, [self.theme_mode, 0], margins=4))
        group_appearance = flat(self.tr('In light theme'), customLayout(True, [8, self.use_modern_design, 4, self.use_modern_icons], margins=4))
        self.light_theme_options = QWidget()
        self.light_theme_options.setLayout(customLayout(True, [14, group_appearance], margins=0))
        self.setLayout(customLayout(True, [
         page_default_layout(self.tr('Default Theme'), self.restoreDefault),
         10, group_theme, 10, self.light_theme_options, 0],
          margins=6))
        for button in (self.theme_mode.system, self.theme_mode.dark, self.theme_mode.light):
            button.toggled.connect(self.updateThemeControls)

        self.use_modern_design.toggled.connect(self.updateThemeControls)
        self.use_modern_icons.toggled.connect(self.updateThemeControls)
        self.updateThemeControls()

    @staticmethod
    def _appearanceState(theme_mode, use_modern_design, use_modern_icons):
        effective_theme = Settings.effectiveThemeValue(theme_mode)
        if effective_theme == Settings.THEME_DARK:
            return (effective_theme, None, 'dark')
        return (effective_theme, bool(use_modern_design), 'light' if use_modern_icons else 'old')

    def currentAppearanceState(self):
        return self._appearanceState(self.theme_mode.value(), self.use_modern_design.isChecked(), self.use_modern_icons.isChecked())

    def updateThemeControls(self):
        effective_theme = Settings.effectiveThemeValue(self.theme_mode.value())
        self.light_theme_options.setVisible(effective_theme == Settings.THEME_LIGHT)
        window = self.window()
        if hasattr(window, '_updateRestartHint'):
            window._updateRestartHint()

    def needsRestart(self):
        return self.currentAppearanceState() != self._stored_state

    def scheduleRestart(self):
        import atexit
        if getattr(sys, 'frozen', False):
            command = [
             
              sys.executable, *sys.argv[1:]]
        else:
            command = [
             
              sys.executable, os.path.realpath(sys.argv[0]), *sys.argv[1:]]

        def _restart():
            try:
                if Across.os == 'win':
                    subprocess.Popen(command,
                      creationflags=(subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW),
                      close_fds=True)
                else:
                    subprocess.Popen(command, start_new_session=True, close_fds=True)
            except Exception:
                pass

        main_module = sys.modules.get('__main__')
        container = getattr(main_module, '_post_jvm_callback', None)
        if container is not None:
            container[0] = _restart
        else:
            atexit.register(_restart)

    def applyAndRestart(self):
        window = self.window()
        if not hasattr(window, '_applyAndRestart'):
            return
        self.scheduleRestart()
        window._applyAndRestart()

    def restoreDefault(self):
        self.theme_mode._setValue(Settings.getDefault('theme_mode'))
        self.use_modern_design.setChecked(Settings.getDefault('use_modern_design'))
        self.use_modern_icons.setChecked(Settings.getDefault('use_modern_icons'))
        self.updateThemeControls()

    def ok(self):
        self.theme_mode.ok()
        Settings.setValue('use_modern_icons', self.use_modern_icons.isChecked(), False)
        Settings.setValue('use_modern_design', self.use_modern_design.isChecked(), False)


class SettingWidget(QWidget):

    def __init__(self):
        super().__init__()
        SPACING = 5
        SPACING_SECTIONS = SPACING * 2
        self.keys = []
        self.options = []
        self.highlight = {}
        label = optionLabel(self.tr('Other settings'))
        label = customLayout(False, [
         image(':/images/option.png', 40), 0, label, 0, default_button(self.restoreDefault)])
        layout_list = [6, label]
        group = QGroupBox(' ' + self.tr('Search options') + '    ')
        group.setFlat(True)
        self.keys.append('search_boxes')
        self.options.append(SettingSpin(self.tr('Number of search boxes'), self.keys[-1], 3, 10))
        self.keys.append('show_searchbox_number')
        self.options.append(SettingCheck(self.tr('Enumerate search boxes'), self.keys[-1]))
        self.keys.append('sidebar_in_results')
        self.options.append(SettingCheck(self.tr('Display Titles side bar in search results as default'), self.keys[-1]))
        self.keys.append('instant_display_result')
        self.options.append(SettingCheck(self.tr('Display search result just on switching to it without clicking'), self.keys[-1]))
        self.keys.append('search_completer')
        self.options.append(SettingCheck(self.tr('Show autocomplete in search boxes'), self.keys[-1]))
        options = [
         SPACING_SECTIONS] + list(reversed(self.options))
        group.setLayout(customLayout(True, options, [0, 3, 0, 5], spacing=SPACING))
        layout_list.append(group)
        if not Across.no_update:
            group = QGroupBox(' ' + self.tr('Download options:') + ' ')
            group.setFlat(True)
            self.keys.append('auto_download_books')
            self.options.append(SettingCheck(self.tr('Auto Download books'), self.keys[-1]))
            self.keys.append('auto_download_pdf')
            self.options.append(SettingCheck(self.tr('Download pdf follows text automatically'), self.keys[-1]))
            group.setLayout(customLayout(False, [self.options[-2], 20, self.options[-1], 0], margins=[
             0, SPACING_SECTIONS, 0, 0],
              spacing=5))
            layout_list.append(group)
        group = QGroupBox(' ' + self.tr('Miscellaneous') + '  ')
        group.setFlat(True)
        lay = []
        grid = QGridLayout()
        self.keys.append('lastpage_history')
        self.options.append(SettingCheck(self.tr('History screen'), self.keys[-1]))
        self.keys.append('lastpage_favorites')
        self.options.append(SettingCheck(self.tr('Favorites screen'), self.keys[-1]))
        self.keys.append('lastpage_others')
        self.options.append(SettingCheck(self.tr('Other screens'), self.keys[-1]))
        grid.addWidget(QLabel(self.tr('Remeber Last page When Reach Books from:')), 0, 0)
        grid.addWidget(self.options[-3], 0, 1)
        grid.addWidget(self.options[-2], 0, 2)
        grid.addWidget(self.options[-1], 0, 3)
        shortcut_widgets = []
        self.keys.append('shortcut_desktop')
        self.options.append(SettingCheck(self.tr('On desktop'), self.keys[-1]))
        shortcut_widgets.append(self.options[-1])
        if menu_shortcut_supported():
            self.keys.append('shortcut_start')
            self.options.append(SettingCheck(self.tr('On Start Menu'), self.keys[-1]))
            shortcut_widgets.append(self.options[-1])
        if shortcut_widgets:
            grid.addWidget(QLabel(self.tr('Create Shortcut for Shamela:')), 1, 0)
            for column, widget in enumerate(shortcut_widgets, 1):
                grid.addWidget(widget, 1, column)

        lay.append(grid)
        self.keys.append('restore_last_session')
        self.options.append(SettingCheck(self.tr('Restore open tabs from last time'), self.keys[-1]))
        lay.append(self.shiftlay(1, self.options[-1]))
        if Across.os == 'win':
            self.keys.append('k_layout')
            self.options.append(SettingCheck(self.tr('At Startup of the Software Change Keyboard to Arabic'), self.keys[-1]))
            lay.append(self.shiftlay(1, self.options[-1]))
        self.keys.append('system_numbers')
        self.options.append(SettingCheck((self.tr('Always use ١ ٢ ٣ digit shapes in text fields regardless of system settings')),
          (self.keys[-1]),
          invert=True))
        self._system_numbers_opt = self.options[-1]
        self._system_numbers_opt.stateChanged.connect(self._notifyRestartHint)
        self.options[-1].setToolTip(self.tr('This option affects newly created text fields, not ones already shown. It does not apply to text inside books.'))
        lay.append(self.shiftlay(1, self.options[-1]))
        self.keys.append('tab_title_words')
        spin = SettingSpin(self.tr('Maximum number of words in tab head'), self.keys[-1], 1, 10)
        self.highlight['tab_title_words'] = spin.label
        self.options.append(spin)
        lay.append(self.shiftlay(1, self.options[-1]))
        group.setLayout(customLayout(True, lay, margins=[
         0, SPACING_SECTIONS, 0, 0],
          spacing=SPACING))
        layout_list.append(group)
        layout_list.append(0)
        self.setLayout(customLayout(True, layout_list, [6, 0, 6, 6], int(SPACING_SECTIONS * 2)))

    def _notifyRestartHint(self):
        window = self.window()
        if hasattr(window, '_updateRestartHint'):
            window._updateRestartHint()

    def needsRestart(self):
        opt = self._system_numbers_opt
        return opt._toStored(opt.isChecked()) != _get_restart_baseline()['system_numbers']

    def highlightKey(self, key):
        create_border((self.highlight[key]), color='red', width=1, style='solid')

    @staticmethod
    def shiftlay(shift, widget):
        return customLayout(False, [shift, widget], margins=0, spacing=0)

    def restoreDefault(self):
        for option in self.options:
            option.restoreDefault()

        self.refreshScreens()
        self._notifyRestartHint()

    def ok(self):
        for option in self.options:
            option.ok()

        self.refreshScreens()

    def refreshScreens(self):
        for widget in Across.refresh_set:
            widget.reinstall()


class checkEdit(QWidget):

    def __init__(self, text, key):
        super().__init__(None)
        self.key = key
        self.checked = None
        self.line = LineEdit(digit_policy='display')
        validator = QIntValidator()
        validator.setBottom(0)
        self.checkBox = QCheckBox(text)
        self.checkBox.stateChanged.connect(self.checkValue)
        self.line.setMaximumWidth(50)
        self.setFixedHeight(17)
        self.setLayout(customLayout(False, [self.checkBox, 20, 0, self.line], margins=0))
        self.setValue(Settings.getValue(key))

    def checkValue(self):
        self.line.setVisible(self.checkBox.isChecked())

    def setValue(self, value):
        if isinstance(value, int):
            value = [
             True, value]
        self.checkBox.blockSignals(True)
        self.checkBox.setChecked(value[0])
        self.line.setText(str(value[1]))
        self.line.setVisible(value[0])
        self.checkBox.blockSignals(False)

    def getValue(self):
        return [
         self.checkBox.isChecked(), int(latinize(self.line.text()))]

    def ok(self):
        Settings.setValue(self.key, self.getValue(), False)

    def restoreDefault(self):
        self.setValue(Settings.getDefault(self.key))


class SelectFolder(QGroupBox):
    progress_signal = Signal(dict)

    def __init__(self, key, default_folder, labels, check_function):
        super().__init__(labels[0])
        self.key = key
        self.default_folder = default_folder
        self.default_text = self.tr('The current path is the default one')
        self.check_function = check_function
        self.currentLine = QLineEdit()
        self.currentLine.setReadOnly(True)
        self.setText(Settings.getValue(self.key))
        openPush = QPushButton(self.tr('Open'))
        openPush.clicked.connect(self.openFolder)
        changePush = QPushButton(self.tr('Change'))
        changePush.clicked.connect(self.changeFolder)
        layout = customLayout(False, [self.currentLine, openPush, changePush], margins=6)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(10)
        self.progress_bar.setVisible(False)
        self.progress_signal.connect(self.progress)
        self.done_text = labels[3]
        self.label = clickableLabel(text=(labels[1]), tooltip=(labels[2]), normal_size=True, slot=(self.check))
        check_layout = customLayout(False, [0, self.progress_bar, self.label, 9])
        self.setLayout(customLayout(True, [3, layout, check_layout, 3]))

    def check(self):
        self.label.setVisible(False)
        if self.confirm():
            Thread(target=checkAllPdf, args=(self.progress_signal,)).start()
        else:
            self.label.setVisible(True)
            customMessage(self.tr('Read Only Folder'), self.tr('The Folder should be writable'))

    def isDefault(self, current):
        if current is None:
            return True
        return os.path.normcase(current) == os.path.normcase(self.default_folder)

    def setText(self, path):
        self.currentLine.setText(self.default_text if self.isDefault(path) else path)

    def getPath(self):
        if self.currentLine.text() == self.default_text:
            return self.default_folder
        return self.currentLine.text()

    def changeFolder(self):
        folder = QFileDialog.getExistingDirectory(None, (self.tr('Select folder:')), dir=(self.getPath()), options=(QFileDialog.ShowDirsOnly))
        if folder:
            self.setText(folder)
            self.ok()

    def openFolder(self):
        folder = self.getPath()
        if folder:
            if os.path.isdir(folder):
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            else:
                customMessage(self.tr('Folder'), self.tr('Folder not found'))
                return

    def restoreDefault(self):
        self.setText(None)

    def value(self):
        folder = self.getPath()
        if folder == self.default_folder:
            return
        return folder

    def progress(self, value):
        if 'start' in value:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(value['start'])
            self.progress_bar.setVisible(True)
            self.label.setVisible(False)
        if 'tip' in value:
            self.progress_bar.setToolTip(value['tip'])
        if 'value' in value:
            self.progress_bar.setValue(value['value'])
            self.progress_bar.setVisible(True)
        if 'end' in value:
            for widget in Across.refresh_set:
                widget.reinstall()

            Across.main_window.checkPdfIcon()
            Across.main_window.startPdf()
            self.progress_bar.setToolTip('')
            self.progress_bar.setVisible(False)
            self.label.setText(self.done_text)
            self.label.setVisible(True)

    def confirm(self, ok=None):
        old_value = Settings.getValue(self.key)
        new_value = self.value()
        if old_value != new_value:
            Settings.setValue(self.key, new_value, False)
        is_writable = isWritable(new_value or self.default_folder)
        if ok:
            if not is_writable or self.check_function:
                Thread(target=(self.check_function), args=(Across.main_window.progress.progress_signal,)).start()
        else:
            if is_writable:
                return True

    def ok(self):
        self.confirm(True)


class SettingSpin(QWidget):

    def __init__(self, text, key, i_min, i_max):
        super().__init__()
        self.key = key
        self.spin = SpinBox()
        self.spin.setMinimum(i_min)
        self.spin.setMaximum(i_max)
        self.spin.setValue(Settings.getValue(key))
        self.spin.setMaximumWidth(60)
        self.label = QLabel(text + '     ')
        customLayout(False, [self.label, 60, self.spin, 0], parent=self)

    def ok(self):
        Settings.setValue(self.key, self.spin.value(), False)

    def restoreDefault(self):
        self.spin.setValue(Settings.getDefault(self.key))


class SettingCheck(QCheckBox):

    def __init__(self, text, key, parent=None, invert=False):
        super().__init__(parent)
        self.key = key
        self.invert = invert
        self.setText(text)
        self.setChecked(self._fromStored(Settings.getValue(self.key)))

    def _fromStored(self, value):
        if self.invert:
            return not value
        return value

    def _toStored(self, value):
        if self.invert:
            return not value
        return value

    def ok(self):
        Settings.setValue(self.key, self._toStored(self.isChecked()), False)

    def restoreDefault(self):
        self.setChecked(self._fromStored(Settings.getDefault(self.key)))


class SettingThemeMode(QWidget):
    key = 'theme_mode'
    system_value = Settings.THEME_SYSTEM
    dark_value = Settings.THEME_DARK
    light_value = Settings.THEME_LIGHT
    default_value = system_value

    def __init__(self, system_text, dark_text, light_text, parent=None):
        super().__init__(parent)
        self.system = QRadioButton(system_text)
        self.dark = QRadioButton(dark_text)
        self.light = QRadioButton(light_text)
        self.setLayout(customLayout(False, [self.system, 20, self.dark, 20, self.light, 0], margins=0))
        self._setValue(Settings.getValue(self.key))

    def _setValue(self, value):
        if value not in (self.system_value, self.dark_value, self.light_value):
            value = self.default_value
        self.system.setChecked(value == self.system_value)
        self.dark.setChecked(value == self.dark_value)
        self.light.setChecked(value == self.light_value)

    def value(self):
        if self.system.isChecked():
            return self.system_value
        if self.dark.isChecked():
            return self.dark_value
        if self.light.isChecked():
            return self.light_value
        return self.default_value

    def ok(self):
        Settings.setValue(self.key, self.value(), False)


class SettingRadio(QWidget):

    def __init__(self, text, options, key, columns, parent=None):
        super().__init__(parent)
        self.key = key
        self.buttons = []
        for option in options:
            button = QRadioButton(option)
            self.buttons.append(button)

        self.setLayout(customLayout(False, [QLabel(text), 20] + self.buttons + [0]))
        self.buttons[Settings.getValue(self.key)].setChecked(True)

    def checkedId(self):
        for i, button in enumerate(self.buttons):
            if button.isChecked():
                return i

    def ok(self):
        Settings.setValue(self.key, self.checkedId(), False)

    def restoreDefault(self):
        self.buttons[Settings.getDefault(self.key)].setChecked(True)


class OrientationSetting(QWidget):

    def __init__(self, key, text):
        super().__init__()
        self.key = key
        label = QLabel(f"• {text}")
        label.setFixedWidth(100)
        self.combo = QComboBox()
        self.combo.addItems([self.tr('Vertical'), self.tr('Horizontal')])
        self.combo.setCurrentIndex(Settings.getValue(self.key))
        self.setLayout(customLayout(False, [10, label, self.combo, 0]))

    def ok(self):
        Settings.setValue(self.key, self.combo.currentIndex(), False)

    def restoreDefault(self):
        value = Settings.getDefault(self.key)
        if self.combo.currentIndex() != value:
            self.combo.setCurrentIndex(value)


class DisplayOptions(QWidget):

    def __init__(self):
        super().__init__()
        self.keys = []
        self.options = []
        layout = []
        label = QLabel(self.tr('This Will Apply Only on New Tabs'))
        label = customLayout(False, [10, label])
        self.keys.append('pdf_on')
        self.options.append(SettingCheck(self.tr('Initially display Pdf if available'), self.keys[-1]))
        layout += [default_layout(self.restoreDefaults), 6, hLine(), 10, self.options[0], 20]
        group = QGroupBox(' ' + self.tr('Display Services') + '    ')
        group.setFlat(True)
        keys = ('pdf_orientation', 'takreej_orientation', 'rijal_orientation', 'toroq_orientation')
        texts = (self.tr('pdfs'), self.tr('Takreej'), self.tr('Trajim'), self.tr('Asaneed Tree'))
        for key, text in zip(keys, texts):
            self.options.append(OrientationSetting(key, text))

        group.setLayout(customLayout(True, [10, label, 10, self.options[-4], self.options[-3], self.options[-2], self.options[-1]], [
         0, 3, 0, 5],
          spacing=5))
        layout += [group, hLine(), 0]
        self.setLayout(customLayout(True, layout, margins=6))

    def ok(self):
        for option in self.options:
            option.ok()

    def restoreDefaults(self):
        for option in self.options:
            option.restoreDefault()


def create_border(label, color='black', width=1, style='solid'):
    """Creates a border around a QLabel.

    Args:
        label: The QLabel to add the border to.
        color: The border color.
        width: The border width in pixels.
        style: The border style (solid, dashed, dotted).
    """
    style_sheet = f"border: {width}px {style} {color};"
    label.setStyleSheet(style_sheet)