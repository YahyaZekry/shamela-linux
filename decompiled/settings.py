# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: settings.py
import dbmanager
from across import Across
from theme import detectSystemThemeValue

def default_fonts():
    return {'font_pages':[
      'Traditional Naskh', 18, True, False], 
     'font_pages_spacing':0.9, 
     'font_matn':[
      'Traditional Naskh', 18, True, False], 
     'font_footnotes':[
      'Traditional Naskh', 14, True, False], 
     'font_footnotes_spacing':0.9, 
     'font_comments':[
      'Traditional Naskh', 18, True, False], 
     'font_comments_spacing':0.9, 
     'font_betaka':[
      'Traditional Naskh', 14, True, False], 
     'font_betaka_spacing':1, 
     'font_tree':Across.standard_font, 
     'font_search_tables':Across.standard_font, 
     'font_standard':Across.standard_font}


class Settings:
    _cache = None
    THEME_SYSTEM = 'system'
    THEME_DARK = 'dark'
    THEME_LIGHT = 'light'
    COLOR_KEYS = ('color_titles', 'color_matn', 'color_search', 'color_text', 'color_footnotes',
                  'color_comments', 'color_punctuate', 'color_men', 'color_text_back',
                  'color_text_back_unprinted', 'color_comments_back')

    @staticmethod
    def _loadDefaults():
        return {**(default_fonts()), **{'color_titles':[
          128, 0, 0], 
         'color_matn':[
          20, 38, 158], 
         'color_search':[
          210, 0, 0], 
         'color_text':[
          0, 0, 0], 
         'color_footnotes':[
          70, 70, 70], 
         'color_comments':[
          0, 0, 0], 
         'color_punctuate':[
          190, 0, 0], 
         'color_men':[
          0, 0, 250], 
         'color_text_back':[
          238, 234, 213], 
         'color_text_back_unprinted':[
          245, 245, 238], 
         'color_comments_back':[
          227, 225, 207], 
         'color_titles_dark':[
          111, 168, 220], 
         'color_matn_dark':[
          112, 197, 175], 
         'color_search_dark':[
          201, 116, 113], 
         'color_text_dark':[
          169, 168, 169], 
         'color_footnotes_dark':[
          139, 139, 139], 
         'color_comments_dark':[
          174, 174, 174], 
         'color_punctuate_dark':[
          212, 170, 92], 
         'color_men_dark':[
          100, 162, 97], 
         'color_text_back_dark':[
          18, 18, 18], 
         'color_text_back_unprinted_dark':[
          31, 32, 33], 
         'color_comments_back_dark':[
          48, 49, 50], 
         'theme_mode':Settings.THEME_SYSTEM, 
         'use_modern_icons':False, 
         'use_modern_design':False, 
         'session_records':True, 
         'search_records':True, 
         'search_words_records':True, 
         'downloaded_books_records':True, 
         'downloaded_pdf_records':True, 
         'open_book_records':True, 
         'search_boxes':5, 
         'show_searchbox_number':True, 
         'instant_display_result':True, 
         'search_completer':True, 
         'tab_title_words':5, 
         'sidebar_in_results':True, 
         'auto_download_books':False, 
         'auto_download_pdf':False, 
         'shortcut_desktop':True, 
         'shortcut_start':True, 
         'system_numbers':False, 
         'k_layout':True, 
         'restore_last_session':True, 
         'pdf_fit':1, 
         'majma_size':20, 
         'majma_spacing':1.1, 
         'amiri_size':17, 
         'amiri_spacing':1.2, 
         'emlaa_size':19, 
         'emlaa_spacing':1, 
         'attribute_size':14, 
         'attr_before':True, 
         'brackets_attr':True, 
         'angular_attr':False, 
         'helal_attr':True, 
         'undiacritize_copied':False, 
         'unsuperscript_copied':True, 
         'copy_formatted':False, 
         'brackets_nass':True, 
         'attr_newline':True, 
         'lastpage_history':True, 
         'lastpage_favorites':True, 
         'lastpage_others':False, 
         'pdf_folder':None, 
         'pdf_on':False, 
         'pdf_orientation':0, 
         'takreej_orientation':0, 
         'rijal_orientation':1, 
         'toroq_orientation':1}}

    LEGACY_UI_FONTS = ('Segoe UI', 'Segoe UI Widened', 'Vazirmatn UI')
    UI_FONT_KEYS = ('font_tree', 'font_search_tables', 'font_standard')

    @staticmethod
    def _migrateUiFontFamily():
        family = Across.ui_font_family
        if not family:
            return
        for key in Settings.UI_FONT_KEYS:
            value = Settings._cache.get(key)
            if isinstance(value, list) and value and value[0] in Settings.LEGACY_UI_FONTS:
                value[0] = family

    @staticmethod
    def _loadSettings():
        Settings._cache = dbmanager.UserDb().loadSettings()
        if not isinstance(Settings._cache, dict):
            Settings._cache = {}
        Settings._migrateUiFontFamily()

    @staticmethod
    def getDefault(key):
        defaults = Settings._loadDefaults()
        if key in defaults:
            return defaults[key]

    @staticmethod
    def _storedValue(key):
        if Settings._cache is None:
            Settings._loadSettings()
        if key in Settings._cache:
            return Settings._cache[key]
        return Settings.getDefault(key)

    @staticmethod
    def getValue(key):
        if key in Settings.COLOR_KEYS:
            key = Settings.themeColorKey(key)
        return Settings._storedValue(key)

    @staticmethod
    def pendingThemeMode():
        return Settings._storedValue('theme_mode')

    @staticmethod
    def pendingEffectiveThemeValue():
        return Settings.effectiveThemeValue(Settings.pendingThemeMode())

    @staticmethod
    def currentThemeValue():
        if Across.active_theme == 'dark':
            return Settings.THEME_DARK
        return Settings.THEME_LIGHT

    @staticmethod
    def effectiveThemeValue(value=None):
        if value is None:
            value = Settings.pendingThemeMode()
        if value in (Settings.THEME_DARK, Settings.THEME_LIGHT):
            return value
        return detectSystemThemeValue()

    @staticmethod
    def themeColorKey(key, theme_mode=None):
        if key not in Settings.COLOR_KEYS:
            return key
        theme = Settings.currentThemeValue() if theme_mode is None else Settings.effectiveThemeValue(theme_mode)
        if theme == Settings.THEME_DARK:
            return f"{key}_dark"
        return key

    @staticmethod
    def themePreviewValues(color_keys, currents):
        values = {}
        for theme, colors in currents.items():
            for key, color in zip(color_keys, colors):
                values[Settings.themeColorKey(key, theme)] = color

        return values

    @staticmethod
    def getColorValue(key, theme_mode=None):
        return Settings._storedValue(Settings.themeColorKey(key, theme_mode))

    @staticmethod
    def getDefaultColor(key, theme_mode=None):
        return Settings.getDefault(Settings.themeColorKey(key, theme_mode))

    @staticmethod
    def setColorValue(key, value, theme_mode=None, save=True):
        return Settings.setValue(Settings.themeColorKey(key, theme_mode), value, save)

    @staticmethod
    def setValue(key, value, save=True):
        from cache import CssCache, Numbers
        from customs import startMenuShortcut, desktopShortcut
        if key in Settings.COLOR_KEYS:
            key = Settings.themeColorKey(key)
        else:
            if Settings._cache is None:
                Settings._loadSettings()
            default = Settings.getDefault(key)
            if value == default:
                if key not in Settings._cache:
                    return
                else:
                    if Settings._storedValue(key) == value:
                        return
                    else:
                        CssCache.clear()
                        Numbers.clearCache()
                        if default == value:
                            if key in Settings._cache:
                                del Settings._cache[key]
                        else:
                            Settings._cache[key] = value
                    if save:
                        Settings.saveAll()
                if key == 'auto_download_books':
                    visible = None
                    if Across.main_window.update:
                        visible = Across.main_window.update.isVisible()
                        Across.main_window.update.scope_widget.stopDownload()
                        Across.main_window.update.kill()
                        Across.main_window.update = None
                    if value:
                        Across.main_window.startBook()
            else:
                Across.main_window.stopBook()
        if visible:
            Across.main_window.showUpdate(True)
        else:
            if key == 'auto_download_pdf':
                visible = None
                if Across.main_window.pdf:
                    visible = Across.main_window.pdf.isVisible()
                    Across.main_window.pdf.scope_widget.stopDownload()
                    Across.main_window.pdf.kill()
                    Across.main_window.pdf = None
                elif value:
                    Across.main_window.startPdf()
                else:
                    Across.main_window.stopPdf()
                if visible:
                    Across.main_window.showPdf(True)
            elif key == 'search_boxes' or key == 'search_completer':
                if Across.main_window.search_window:
                    visible = Across.main_window.search_window.isVisible()
                    if visible:
                        Across.refresh_set.discard(Across.main_window.search_window.select_widget)
                        Across.main_window.search_window.close()
                    Across.main_window.search_window = None
                    if visible:
                        Across.main_window.showSearch()
            elif key == 'shortcut_desktop':
                desktopShortcut()
            else:
                if key == 'shortcut_start':
                    startMenuShortcut()
                else:
                    if key == 'tab_title_words':
                        Across.main_window.dual.reText()
            return True

    @staticmethod
    def setValues(values_dict):
        any_change = False
        for key in values_dict:
            if Settings.setValue(key, values_dict[key]):
                any_change = True

        if any_change:
            Settings.saveAll()

    @staticmethod
    def saveAll():
        if Settings._cache is None:
            Settings._loadSettings()
        dbmanager.UserDb().saveSettings(Settings._cache)