# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: across.py


class Across:
    global_index = None
    running_arch = None
    system_arch = None
    lucene_version = None
    diac_table = str.maketrans('', '', '¬ًٌٍَُِّْ')
    iso_table = str.maketrans('ؤىئإأٱآة', 'وييااااه')
    iso_table.update(diac_table)
    stringated_table = str.maketrans('{}[]', '()()')
    row_space = 8
    fonts = [
     "'Traditional Naskh Bold.ttf'", "'Traditional Naskh.ttf'", 
     "'Kitab-Regular.ttf'", 
     "'UthmanicHafs_V22.ttf'", "'amiri-quran.ttf'", 
     "'VazirmatnUI-Decurled.ttf'"]
    ui_font_family = 'Vazirmatn UI Decurled'
    home_directory = bin_directory = None
    results_loaded = None
    splitter = '\r_________\r'
    separator = '_________'
    importer_thread = None
    main_window = None
    refresh_set = set()
    hidden_set = set()
    dialog_stack = []
    standard_font = None
    writable = None
    stop_pdf = stop_books = obligatory = None
    QUEUED = 0
    BUSY = -1
    downloading_books = {}
    importing_books = {}
    downloading_pdfs = {}
    background_threads = set()
    dialog_state = {}
    no_update = None
    os = None
    icon_style = 'old'
    active_theme = 'native_light'