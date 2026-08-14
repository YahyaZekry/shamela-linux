#!/usr/bin/env python
"""Proof-of-concept converter: golden shamela (.mdb) -> modern Linux shamela.

Reads legacy Shamela 3.x Access book files (Books/<id%10>/<id>.mdb) and writes
them into a modern Shamela 5.x data directory in the app's native format:

  * database/book/<id%1000:03d>/<id>.db   (per-book SQLite: page + title tables)
  * Lucene 'page' and 'title' stores       (full-text + stored text, via the
                                           app's own Book.updatePage/updateTitle)
  * master.db: book.major_ondisk = page count

Usage: convert_poc.py BOOK_ID [BOOK_ID ...]

Runs headless using the dev venv Python 3.7 + the app's bundled JRE and Lucene
jars. A minimal dbmanager stub satisfies engine.Book's CoreDb().sorter().
"""

import os
import sys
import types
import sqlite3

APP_HOME = "/home/monst3r/Apps/shamela"
GOLD_ROOT = "/mnt/knowledge/إسلامي/Prog/golden shamela/Books"
SRC = "/mnt/airfryer/Projects/Linux/shamela-linux"

sys.path.insert(0, os.path.join(SRC, 'decompiled'))
sys.path.insert(0, os.path.join(SRC, 'd3'))

from access_parser import AccessParser

DB_DIR = os.path.join(APP_HOME, 'database')

# ---------------------------------------------------------------------------
# minimal dbmanager stub (engine.Book._getDoc -> CoreDb().sorter())
# ---------------------------------------------------------------------------

stub = types.ModuleType('dbmanager')


class _CoreDb:
    def __init__(self):
        cur = sqlite3.connect(os.path.join(DB_DIR, 'master.db')).cursor()
        cur.row_factory = sqlite3.Row
        self.cur = cur

    def sorter(self, book_id):
        row = self.cur.execute(
            'SELECT book_date, main_author, book_up, group_id, group_order '
            'FROM book WHERE book_id = ?', (book_id,)).fetchone()
        if row:
            return {'date': row['book_date'], 'author': row['main_author'],
                    'book_up': row['book_up'], 'group': row['group_id'],
                    'group_order': row['group_order']}


stub.CoreDb = _CoreDb
sys.modules['dbmanager'] = stub


def _decode(value):
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode('cp1256', errors='replace')
    text = str(value)
    if text and all(ord(c) < 256 for c in text):
        return text.encode('latin1', errors='replace').decode('cp1256', errors='replace')
    return text


def _norm(text):
    return ' '.join(''.join(ch for ch in text if not ch in 'ًٌٍَُِّْ').split())


# ---------------------------------------------------------------------------
# boot the app's Lucene stack
# ---------------------------------------------------------------------------

def boot():
    from across import Across
    Across.home_directory = APP_HOME
    Across.bin_directory = os.path.join(APP_HOME, 'app', 'linux', '64', 'bin')
    Across.lucene_version = 2

    lucene = os.path.join(APP_HOME, 'app', 'lucene', '2')
    jre = os.path.join(APP_HOME, 'app', 'linux', '64', 'jre', '2')
    os.environ['JAVA_HOME'] = jre
    os.environ['PATH'] = (os.path.join(jre, 'bin') + os.pathsep +
                          os.path.join(jre, 'lib', 'server') + os.pathsep +
                          os.environ['PATH'])

    import jpype
    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=[f"{lucene}/*"])

    import atexit as _atexit
    import gc as _gc

    def _shutdown():
        _gc.collect()
        if jpype.isJVMStarted():
            jpype.shutdownJVM()

    _atexit.register(_shutdown)

    import engine
    return engine


# ---------------------------------------------------------------------------
# extraction (access_parser) and derivation
# ---------------------------------------------------------------------------

def extract(book_id):
    path = os.path.join(GOLD_ROOT, str(book_id % 10), f"{book_id}.mdb")
    db = AccessParser(path)
    book = db.parse_table('book')
    title = db.parse_table('title')

    pages = [{'id': int(book['id'][i]),
              'part': int(book['part'][i]),
              'page': int(book['page'][i]),
              'nass': _decode(book['nass'][i]) if 'nass' in book else ''}
             for i in range(len(book['id']))]
    pages.sort(key=lambda p: p['id'])

    raw = [{'id': int(title['id'][i]),
            'lvl': int(title['lvl'][i]),
            'sub': int(title['sub'][i]),
            'tit': _decode(title['tit'][i])}
           for i in range(len(title['id']))]
    raw.sort(key=lambda t: t['id'])
    return pages, raw


def renumber_titles(raw):
    """Golden files can repeat title ids.  Renumber uniquely in order and
    remap every sub (parent) reference to its new id, preserving the tree."""
    old2new = {}
    titles = []
    for idx, t in enumerate(raw, start=1):
        old2new[t['id']] = idx
        titles.append({'id': idx, 'sub': t['sub'], 'tit': t['tit']})
    for t in titles:
        parent = t['sub']
        t['parent'] = old2new.get(parent, 0) if parent else 0
        del t['sub']
    return titles


def derive_title_pages(titles, pages):
    """Assign each title a page.id: first page whose text starts with the
    heading text; fall back to the previous title's page (or the first page)."""
    cache = {}
    prev_page = pages[0]['id'] if pages else 1
    norm_pages = [(_norm(p['nass']), p['id']) for p in pages]
    result = []
    for t in titles:
        key = _norm(t['tit'])
        if key:
            page = cache.get(key)
            if page is None:
                page = 0
                for nass, pid in norm_pages:
                    if nass.startswith(key):
                        page = pid
                        break
                cache[key] = page
            if page:
                prev_page = page
        result.append({'id': t['id'], 'page': prev_page, 'parent': t['parent'],
                       'body': t['tit']})
    return result


# ---------------------------------------------------------------------------
# write modern per-book sqlite
# ---------------------------------------------------------------------------

def write_book_db(book_id, pages, titled):
    folder = os.path.join(DB_DIR, 'book', str(book_id % 1000).zfill(3))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{book_id}.db")

    if os.path.isfile(path):
        os.unlink(path)

    db = sqlite3.connect(path)
    cur = db.cursor()
    cur.execute('CREATE TABLE page (id INTEGER PRIMARY KEY, part TEXT, page INTEGER, number INTEGER, services TEXT)')
    cur.execute('CREATE INDEX part on page (part)')
    cur.execute('CREATE INDEX page_id on page (page)')
    cur.execute('CREATE INDEX number on page (number)')
    cur.execute('CREATE TABLE title (id INTEGER PRIMARY KEY, page INTEGER, parent INTEGER)')
    cur.execute('CREATE INDEX parent on title (parent)')
    cur.execute('CREATE INDEX correspond on title (page)')

    single_part = len({p['part'] for p in pages}) <= 1
    cur.executemany('INSERT INTO page VALUES (?,?,?,?,?)',
                    [(p['id'], '' if single_part else str(p['part']),
                      p['page'], None, None) for p in pages])
    cur.executemany('INSERT INTO title VALUES (?,?,?)',
                    [(t['id'], t['page'], t['parent']) for t in titled])
    db.commit()
    db.close()
    return path


# ---------------------------------------------------------------------------
# write Lucene stores (the app's own writer classes)
# ---------------------------------------------------------------------------

def write_lucene(engine, book_id, pages, titled):
    book = engine.Book(book_id)
    for p in pages:
        book.updatePage(p['id'], {'page': p['nass']})
    for t in titled:
        book.updateTitle(t['id'], {'body': t['body'], 'parent': t['parent']})
    engine.Index.commit('page')
    engine.Index.commit('title')


def mark_ondisk(book_id, count):
    db = sqlite3.connect(os.path.join(DB_DIR, 'master.db'))
    db.execute('UPDATE book SET major_ondisk = ? WHERE book_id = ?',
               (count, book_id))
    db.commit()
    db.close()


def convert(engine, book_id, target_id=None):
    target_id = target_id or book_id
    print(f"[{book_id}] extracting ...", flush=True)
    pages, titles = extract(book_id)
    print(f"[{book_id}] {len(pages)} pages, {len(titles)} titles -> target {target_id}", flush=True)
    titles = renumber_titles(titles)
    titled = derive_title_pages(titles, pages)
    path = write_book_db(target_id, pages, titled)
    print(f"[{book_id}] wrote {path}", flush=True)
    write_lucene(engine, target_id, pages, titled)
    print(f"[{book_id}] wrote Lucene page/title stores", flush=True)
    mark_ondisk(target_id, len(pages))
    print(f"[{book_id}] master.db major_ondisk[{target_id}] = {len(pages)}", flush=True)
    return len(pages)


def main():
    ids = [a for a in sys.argv[1:]]
    if not ids:
        print(__doc__)
        sys.exit(1)
    engine = boot()
    for spec in ids:
        if ':' in spec:
            gold_id, target_id = (int(x) for x in spec.split(':'))
        else:
            gold_id = target_id = int(spec)
        try:
            convert(engine, gold_id, target_id)
        except Exception as exc:
            print(f"[{gold_id}] FAILED: {exc}", flush=True)
            raise


if __name__ == '__main__':
    main()
