"""shamela_patch - instrumentation + fixes injected into the frozen Shamela app.

Injected into the PYZ as module 'shamela_patch' and invoked from 'across'
via bytecode-level injection (`import shamela_patch; shamela_patch.install()`).

Interception strategy: the PyInstaller frozen importer sits at the TOP of
sys.meta_path and answers every frozen name, so a meta-path finder appended
(our earlier Hook2 approach) is never consulted for the 4 target modules.
Instead we pre-register shim objects in sys.modules: the import system
consults sys.modules BEFORE any finder, and `from X import Y` pulls Y via
__getattr__ on the shim, which then performs the real import behind the
scenes and applies the patches. This cannot be bypassed while still
preserving the frozen loader's per-import state.

Everything here must be defensive: any failure in this module may only log.
"""
import os
import sys
import time

_LOG_PATH = '/tmp/shamela_boot.log'
_T0 = time.time()
_FIXED = os.environ.get('SHAMELA_BASELINE') is None  # baseline = measure only


def log(msg):
    try:
        with open(_LOG_PATH, 'a') as f:
            f.write('%.3f %s\n' % (time.time() - _T0, msg))
    except Exception:
        pass


def install():
    try:
        log('=== boot start ===')
        log('argv=%r' % sys.argv)
        log('FIXED MODE' if _FIXED else 'BASELINE MODE: instrumentation only')
        _install_shims()
        log('shims installed for %s' % ', '.join(sorted(_TARGETS)))
    except Exception as e:
        log('install() failed: %r' % (e,))


# ---------------------------------------------------------------------------
# sys.modules shims
# ---------------------------------------------------------------------------

_TARGETS = ('mainwindow', 'searchbiblio', 'search_base', 'dbmanager', 'cache')
_INFLIGHT = set()


class _Shim(object):
    __path__ = []

    def __init__(self, name):
        self.__name__ = name
        self.__package__ = name.split('.')[0]
        self.__file__ = '<shim-%s>' % name

    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            raise AttributeError(attr)
        real = _ensure_real(self.__name__)
        return getattr(real, attr)


def _install_shims():
    import types
    for name in _TARGETS:
        if name in sys.modules:
            continue
        shim = _Shim(name)
        try:
            shim.__spec__ = types.SimpleNamespace(name=name, loader=None)
            import importlib.machinery
            shim.__spec__ = importlib.machinery.ModuleSpec(name, loader=None)
        except Exception:
            pass
        sys.modules[name] = shim


def _ensure_real(name):
    if name in _INFLIGHT:
        return sys.modules.get(name)
    _INFLIGHT.add(name)
    t = time.time()
    try:
        sys.modules.pop(name, None)
        try:
            __import__(name, globals(), locals())  # real frozen import
        except Exception as e:
            log('%s real import failed: %r' % (name, e))
            if name not in sys.modules:
                sys.modules[name] = _Shim(name)  # restore routing shim
            raise
        real = sys.modules.get(name)
        log('%s imported in %.3fs' % (name, time.time() - t))
        if real is not None and not isinstance(real, _Shim):
            _patch_module(name, real)
        return real
    finally:
        _INFLIGHT.discard(name)


# ---------------------------------------------------------------------------
# per-module patches: measurement always, fixes only in FIXED mode
# ---------------------------------------------------------------------------

def _patch_module(name, mod):
    try:
        if name == 'mainwindow':
            _patch_mainwindow(mod)
        elif name == 'searchbiblio':
            _patch_searchbiblio(mod)
        elif name == 'search_base':
            _patch_search_base(mod)
        elif name == 'dbmanager':
            _patch_dbmanager(mod)
        elif name == 'cache':
            _patch_cache(mod)
        log('%s patched' % name)
    except Exception as e:
        log('%s patch failed: %r' % (name, e))


def _patch_mainwindow(mw):
    mwclass = mw.MainWindow
    qtlabel = getattr(mw, 'Qtlabel', None)

    orig_init = mwclass.__init__
    orig_show = mwclass.show
    orig_showbiblio = getattr(mwclass, 'showbiblio', None)
    orig_showbg = getattr(mwclass, 'showBackground', None)

    def init(self, *a, **k):
        t = time.time()
        try:
            return orig_init(self, *a, **k)
        finally:
            log('MainWindow.__init__ took %.3fs' % (time.time() - t))

    def show(self):
        t = time.time()
        try:
            return orig_show(self)
        finally:
            log('MainWindow.show returned after %.3fs (JVM up %ds)' %
                (time.time() - t, time.time() - _T0))

    def showbiblio(self, forced=None):
        t = time.time()
        try:
            return orig_showbiblio(self, forced=forced) if orig_showbiblio else None
        finally:
            log('showbiblio(%r) took %.3fs' % (forced, time.time() - t))

    mwclass.__init__ = init
    mwclass.show = show
    if orig_showbiblio is not None:
        mwclass.showbiblio = showbiblio

    if _FIXED and orig_showbg is not None:
        bg = _find_background()
        if bg:
            def patched_showBackground(self):
                try:
                    from qtpy.QtGui import QPixmap
                    from qtpy.QtWidgets import QSizePolicy
                    path = _find_background()
                    if path:
                        pix = QPixmap(path)
                        if not pix.isNull():
                            if not self.imageLabel:
                                label_cls = qtlabel or mw.Qtlabel
                                self.imageLabel = label_cls()
                                self.imageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
                                self.imageLabel.setScaledContents(True)
                                self.imageLabel.clicked.connect(self.showSelectBook)
                                self.imageLabel.rtClicked.connect(self.showSearch)
                                self.mainArea.addWidget(self.imageLabel)
                            self.imageLabel.setPixmap(pix)
                            self.mainArea.setCurrentWidget(self.imageLabel)
                            return
                except Exception as e:
                    log('background override failed: %r' % e)
                return orig_showbg(self)

            mwclass.showBackground = patched_showBackground
            log('showBackground patched -> %s' % bg)


def _find_background():
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        home = os.path.expanduser('~')
        for p in (os.environ.get('SHAMELA_BG'),
                  os.path.join(exe_dir, 'background.jpg'),
                  os.path.join(exe_dir, 'background.png'),
                  os.path.join(home, '.shamela', 'background.jpg'),
                  os.path.join(home, '.shamela', 'background.png')):
            if p and os.path.isfile(p):
                return p
    except Exception:
        pass
    return None


def _patch_searchbiblio(mod):
    BookList = mod.BookList
    orig_load = BookList._loadItems

    def load(self, key_id=None):
        t = time.time()
        try:
            return orig_load(self, key_id)
        finally:
            log('BookList._loadItems(%r) took %.3fs (%d books)' % (
                key_id, time.time() - t,
                len(self.books) if getattr(self, 'books', None) else -1))

    BookList._loadItems = load


class _IndexedList(list):
    def __init__(self, items=()):
        super().__init__(items)
        self._idx = {v: i for i, v in enumerate(items)}

    def index(self, value, *a, **k):
        try:
            return self._idx[value]
        except KeyError:
            raise ValueError('%r is not in list' % (value,))


def _patch_search_base(mod):
    import sys
    WidgetResults = mod.WidgetResults
    engine = sys.modules.get('engine')

    if engine is not None and _FIXED:
        Query = engine.Query
        orig_build_scope = Query.buildScope

        def buildScope(self):
            t = time.time()
            try:
                return orig_build_scope(self)
            finally:
                log('buildScope took %.3fs (%d ids)' % (
                    time.time() - t,
                    len(getattr(self, 'scope_list', None) or [])))
                sl = getattr(self, 'scope_list', None)
                if isinstance(sl, list) and not isinstance(sl, _IndexedList):
                    self.scope_list = _IndexedList(sl)

        Query.buildScope = buildScope
        log('Query.buildScope patched (indexed scope_list)')

    orig_sf = WidgetResults.searchFiltered

    def searchFiltered(self, book_id):
        t = time.time()
        try:
            return orig_sf(self, book_id)
        finally:
            dt = time.time() - t
            if dt > 0.001:
                log('searchFiltered(%d) took %.3fs' % (book_id, dt))

    WidgetResults.searchFiltered = searchFiltered
    log('WidgetResults.searchFiltered wrapped (timing)')


def _patch_dbmanager(mod):
    for qname in ('getBooks', 'getBooksSet', 'getCategories'):
        orig = getattr(mod.CoreDb, qname, None)
        if not orig:
            continue

        def wrapped(self, *a, _fn=orig, _qn=qname, **k):
            t = time.time()
            try:
                r = _fn(self, *a, **k)
            finally:
                log('%s took %.3fs (%d rows)' % (_qn, time.time() - t, len(r) if r else 0))
            return r

        setattr(mod.CoreDb, qname, wrapped)

    _patch_category_lookup(mod)


def _patch_category_lookup(mod):
    CoreDb = mod.CoreDb
    bc = getattr(CoreDb, 'bookCategory', None)
    bn = getattr(CoreDb, 'bookCentury', None)
    if not bc or not bn:
        return

    def _century(year):
        if year < 1:
            return 1
        c = year / 100
        if c != int(c):
            c = int(c) + 1
        return int(c)

    def _cat_cache(self):
        cache = getattr(self, '_shamela_cat_cache', None)
        if cache is None:
            t = time.time()
            rows = self.cur.execute(
                'SELECT book_id, book_category, book_date FROM book').fetchall()
            cache = {}
            for book_id, category, date in rows:
                try:
                    cache[book_id] = (category, _century(date))
                except Exception:
                    cache[book_id] = (category, 1)
            self._shamela_cat_cache = cache
            log('category/century cache built (%d books) in %.3fs' % (
                len(cache), time.time() - t))
        return cache

    def bookCategory(self, book_id):
        try:
            return _cat_cache(self)[book_id][0]
        except Exception:
            return bc(self, book_id)

    def bookCentury(self, book_id):
        try:
            return _cat_cache(self)[book_id][1]
        except Exception:
            return bn(self, book_id)

    CoreDb.bookCategory = bookCategory
    CoreDb.bookCentury = bookCentury
    log('bookCategory/bookCentury batched')


def _patch_cache(mod):
    BookCache = mod.BookCache
    log('BookCache: dict max=%s, current=%d' % (
        getattr(getattr(BookCache, '_cache', None), 'max', 'n/a'),
        len(BookCache._cache) if hasattr(BookCache, '_cache') else -1))
    if not _FIXED:
        return
    raw = BookCache._getCache
    if hasattr(raw, '__func__'):
        raw = raw.__func__
    BookCache._origGetCache = staticmethod(raw)  # fallback if prefill fails

    def get_cache(book_id):
        c = BookCache._cache
        if book_id in c:
            return c[book_id]
        try:
            if not _PREFILL_LOCK[0] or len(c) < 1000:
                _prefill_book_cache()
            if book_id in BookCache._cache:
                return BookCache._cache[book_id]
        except Exception as e:
            log('prefill failed, using original per-book load: %r' % e)
        return BookCache._origGetCache(book_id)

    BookCache._getCache = staticmethod(get_cache)
    log('BookCache._getCache patched (batch prefill)')


_PREFILL_LOCK = [False]


def _prefill_book_cache():
    if _PREFILL_LOCK[0]:
        return False
    _PREFILL_LOCK[0] = True
    from cache import BookCache  # noqa
    from dbmanager import CoreDb  # noqa
    from textmanager import arabize  # noqa
    from dbmanager import joinAuthors  # noqa
    db = CoreDb()
    t = time.time()
    book_rows = db.cur.execute(
        'SELECT book_id, book_name, book_type, printed, hidden, authors, pdf_ondisk '
        'FROM book').fetchall()
    author_rows = {r[0]: (r[1], r[2]) for r in db.cur.execute(
        'SELECT author_id, death_text, author_name FROM author').fetchall()}
    cache = {}
    for row in book_rows:
        book_id, book_name, book_type, printed, hidden, authors_str, pdf = row
        abstract_name = arabize(book_name)
        author_ids = [int(a.strip()) for a in (authors_str or '').split(',') if a.strip()]
        main_death = None
        author_names = []
        author_abst_names = []
        for author_id in author_ids:
            info = author_rows.get(author_id)
            if info is None:
                continue
            author_death, author_name = info
            author_death = " (ت %s)" % arabize(author_death) if author_death else ''
            if main_death is None:
                main_death = author_death
            author_names.append('%s%s' % (author_name, author_death))
            author_abst_names.append(author_name)
        name = '%s%s' % (abstract_name, main_death or '')
        author_disp = joinAuthors(author_names)
        author_abst = "(%s)" % ' - '.join(author_abst_names)
        special_icon_path = None
        if book_type == 1:
            if printed == 1:
                icon_path = ':/icons/printed.png'
                special_icon_path = ':/icons/pdf_r.png'
            else:
                icon_path = ':/icons/unprinted.png'
        elif book_type == 2:
            icon_path = ':/icons/mag-printed.png' if printed == 1 else ':/icons/mag-unprinted.png'
        else:
            if book_type == 3:
                special_icon_path = ':/icons/manuscript.png'
            icons = ['manuscript', 'thesis', 'electronic', 'sound']
            icon_path = ':/icons/%s.png' % icons[book_type - 3]
        cache[book_id] = (name, icon_path, hidden, abstract_name, bool(pdf),
                          author_disp, special_icon_path, author_abst, printed)
    BookCache._cache = cache
    log('BookCache prefilled %d books in %.3fs' % (len(cache), time.time() - t))
    return True