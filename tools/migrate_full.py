#!/usr/bin/env python
"""Full migration: golden shamela library -> modern Linux shamela.

Phases (run in order):
  map      - build golden->modern book mapping + golden-cat->category mapping
             (writes tools/data/golden_map.json, gcat_map.json; no data touched)
  catalog  - insert catalog rows (author/category/book/author_book) for every
             golden book that has no modern match and has real content
  convert  - convert book content (per-book SQLite + Lucene page/title stores +
             master.db flags). Matched books write into their modern book_id;
             unmatched books use new ids allocated in the catalog phase.

Usage:
  migrate_full.py map [--force]
  migrate_full.py catalog [--limit N]
  migrate_full.py convert [--limit N] [--force-ondisk] [--commit-every N]
  migrate_full.py all [--limit N]

Resumable: state lives in tools/data/progress.db and golden_map.json.
"""
import os
import re
import sys
import json
import time
import types
import sqlite3
import argparse

APP_HOME = "/home/monst3r/Apps/shamela"
GOLD_ROOT = "/mnt/knowledge/إسلامي/Prog/golden shamela/Books"
GOLD_INDEX = "/mnt/knowledge/إسلامي/Prog/golden shamela/book_index.db"
SRC = "/mnt/airfryer/Projects/Linux/shamela-linux"
DATA = os.path.join(SRC, 'tools', 'data')
MAP_FILE = os.path.join(DATA, 'golden_map.json')
GCAT_FILE = os.path.join(DATA, 'gcat_map.json')
PROGRESS_DB = os.path.join(DATA, 'progress.db')
DB_DIR = os.path.join(APP_HOME, 'database')
MASTER_DB = os.path.join(DB_DIR, 'master.db')

sys.path.insert(0, os.path.join(SRC, 'decompiled'))
sys.path.insert(0, os.path.join(SRC, 'd3'))

from access_parser import AccessParser

DIA = re.compile(r'[\u064B-\u065F\u0670\u0640]')

# ---------------------------------------------------------------------------
# golden cat -> modern category overrides (data-driven vote + manual fixes)
# ---------------------------------------------------------------------------
GCAT_OVERRIDES = {
    9: 26,     # albani biographies -> التراجم والطبقات
    85: 23,    # رمضان/آداب -> الرقائق والآداب والأذكار
    243: 19,   # مسائل فقهية
    38: 40,    # علوم أخرى (catch-all for mixed topics)
}
GCAT_FALLBACK = 39   # كتب عامة


def norm(name):
    s = name or ''
    s = DIA.sub('', s)
    s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ٱ', 'ا')
    s = s.replace('ة', 'ه').replace('ى', 'ي')
    s = re.sub(r'\s+', ' ', s).strip()
    return (s, re.sub(r'^ال', '', s))


def golden_books():
    g = sqlite3.connect(GOLD_INDEX)
    g.row_factory = sqlite3.Row
    return [dict(r) for r in g.execute(
        "SELECT id, bookName, shamelaID, bookInfo, authorName, authorDeath, cat "
        "FROM books ORDER BY id")]


def modern_books():
    m = sqlite3.connect(MASTER_DB)
    m.row_factory = sqlite3.Row
    return [dict(r) for r in m.execute(
        "SELECT book_id, book_name, book_category, main_author FROM book")]


# ---------------------------------------------------------------------------
# phase: map
# ---------------------------------------------------------------------------

def phase_map(force=False):
    os.makedirs(DATA, exist_ok=True)
    if os.path.isfile(MAP_FILE) and not force:
        print("map exists; use --force to rebuild")
        return

    grows = golden_books()
    mrows = modern_books()
    mi = {}
    for r in mrows:
        bid, bname, bcat = r['book_id'], r['book_name'], r['book_category']
        for v in set(norm(bname)):
            mi.setdefault(v, []).append((bid, bcat))

    # title match
    hits = {}
    multi = {}
    for g in grows:
        gid, gname, sid = g['id'], g['bookName'], g['shamelaID']
        found = None
        for v in norm(gname):
            if v in mi:
                lst = mi[v]
                if len(lst) > 1:
                    multi[gid] = [b for b, _ in lst]
                found = lst[0][0]
                break
        if found:
            hits[sid] = {'target': found, 'gid': gid, 'name': gname}

    # golden cat -> modern cat majority vote
    vote = {}
    for g in grows:
        gid, gname, sid, gcat = (g['id'], g['bookName'],
                                 g['shamelaID'], g['cat'])
        if sid in hits:
            v = hits[sid]['target']
            for b, c in mi[norm(gname)[0]]:
                if b == v:
                    vote.setdefault(gcat, {})[c] = vote.get(gcat, {}).get(c, 0) + 1
                    break
    gcat_map = {}
    for gc, counts in vote.items():
        mcat, n = max(counts.items(), key=lambda kv: kv[1])
        total = sum(counts.values())
        conf = n / total if total else 0
        gcat_map[str(gc)] = {'mcat': mcat, 'conf': round(conf, 2), 'n': n,
                             'total': total,
                             'manual': gc in GCAT_OVERRIDES}
        if gc in GCAT_OVERRIDES:
            gcat_map[str(gc)]['mcat'] = GCAT_OVERRIDES[gc]
            gcat_map[str(gc)]['conf'] = 1.0

    json.dump(hits, open(MAP_FILE, 'w'), ensure_ascii=False, indent=0)
    json.dump(gcat_map, open(GCAT_FILE, 'w'), ensure_ascii=False, indent=0)

    matched = len(hits)
    modern_covered = len({v['target'] for v in hits.values()})
    print(f"golden matched: {matched}/{len(grows)} ({matched/len(grows)*100:.1f}%)")
    print(f"modern ids covered: {modern_covered}/{len(mrows)}")
    print(f"golden cats with evidence: {len(gcat_map)}")


def gcat_to_modern(gcat):
    if str(gcat) in GCAT_OVERRIDES:
        return GCAT_OVERRIDES[gcat]
    try:
        m = json.load(open(GCAT_FILE))
    except Exception:
        m = {}
    if str(gcat) in m:
        if m[str(gcat)]['conf'] >= 0.6:
            return m[str(gcat)]['mcat']
    return GCAT_FALLBACK


# ---------------------------------------------------------------------------
# phase: catalog  (insert rows for unmatched golden books with content)
# ---------------------------------------------------------------------------

def content_exists(sid):
    """Return (page_count, has_real_text) for a golden book."""
    path = os.path.join(GOLD_ROOT, str(sid % 10), f"{sid}.mdb")
    if not os.path.isfile(path):
        return 0, False
    try:
        from access_parser import AccessParser
        book = AccessParser(path).parse_table('book')
        n = len(book['id'])
        if n == 0:
            return 0, False
        text = ''.join(
            (v.decode('cp1256', errors='replace')
             if isinstance(v, bytes) else
             str(v).encode('latin1', errors='replace').decode('cp1256', errors='replace'))
            for v in book.get('nass', [])[:20])
        return n, bool(text.strip())
    except Exception as e:
        print(f"  [cat:{sid}] probe error: {e}")
        return 0, False


def insert_author(m_conn, name, death):
    death = death or 0
    d = death if death and death < 99999 else 99999
    cur = m_conn.execute(
        "INSERT INTO author (author_name, death_number, death_text, alpha) "
        "VALUES (?,?,?,1)", (name, d, str(d)))
    return cur.lastrowid


def load_hits():
    hits = json.load(open(MAP_FILE))
    return {int(k): v for k, v in hits.items()}


def phase_catalog(limit=None):
    if not os.path.isfile(MAP_FILE):
        print("run 'map' first")
        return
    os.makedirs(DATA, exist_ok=True)
    hits = load_hits()
    grows = golden_books()
    m = sqlite3.connect(MASTER_DB)
    m.row_factory = sqlite3.Row

    state = sqlite3.connect(PROGRESS_DB)
    state.execute("CREATE TABLE IF NOT EXISTS catalog_done "
                  "(golden_id INTEGER PRIMARY KEY, book_id INTEGER)")
    state.execute("CREATE TABLE IF NOT EXISTS converted "
                  "(golden_id INTEGER PRIMARY KEY, book_id INTEGER, pages INTEGER)")

    existing = {r['book_id'] for r in m.execute("SELECT book_id FROM book")}
    # keep migration ids clearly above the online id space
    next_id = max(max(existing), 200000) + 1

    done = {r[0] for r in state.execute("SELECT golden_id FROM catalog_done")}
    # precompute author name index (norm -> author_id)
    author_index = {}
    for aid, aname in m.execute("SELECT author_id, author_name FROM author"):
        for v in norm(aname):
            author_index.setdefault(v, aid)
    added = 0
    for g in grows:
        gid = g['id']
        sid = g['shamelaID']
        if sid in hits or gid in done:
            continue
        pages, has_text = content_exists(sid)
        if not has_text:
            continue
        if limit and added >= limit:
            break
        # allocate id
        while next_id in existing:
            next_id += 1
        book_id = next_id
        next_id += 1

        # author
        aid = None
        if g['authorName'] and g['authorName'] not in ('-', 'مجموعة من المؤلفين'):
            aid = author_index.get(norm(g['authorName'])[0])
        if aid is None:
            aid = insert_author(m, g['authorName'] or 'مجهول',
                                g['authorDeath'] or 0)
            for v in norm(g['authorName'] or 'مجهول'):
                author_index.setdefault(v, aid)
        # category
        mcat = gcat_to_modern(g['cat'])
        # insert book
        death = g['authorDeath'] or 0
        book_date = death if 0 < death < 99999 else 99999
        name = g['bookName'] or ''
        authors_text = str(aid or 0)
        try:
            m.execute(
                "INSERT INTO book (book_id, book_name, book_category, book_type,"
                " book_date, authors, main_author, printed, group_id, hidden,"
                " major_online, minor_online, major_ondisk, minor_ondisk,"
                " pdf_ondisk, pdf_online, cover_ondisk, cover_online,"
                " meta_data, parent, alpha, group_order, book_up)"
                " VALUES (?,?,?,1,?,?,?,3,0,0,0,0,0,0,0,0,0,0,NULL,0,1,0,0)",
                (book_id, name, mcat, book_date, authors_text, aid))
            m.execute("INSERT INTO author_book (author_id, book_id) VALUES (?,?)",
                      (aid, book_id))
        except Exception as e:
            print(f"  [cat:{sid}] insert error: {e}")
            m.rollback()
            continue
        state.execute("INSERT INTO catalog_done VALUES (?,?)", (gid, book_id))
        existing.add(book_id)
        added += 1
        if added % 200 == 0:
            m.commit()
            state.commit()
        print(f"[cat] {sid} '{name[:40]}' -> new book {book_id} (gcat {g['cat']}->{mcat}, author {aid})", flush=True)

    m.commit()
    state.commit()
    print(f"catalog: added {added} new books")
    m.close()


# ---------------------------------------------------------------------------
# phase: convert
# ---------------------------------------------------------------------------

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


def extract(sid):
    path = os.path.join(GOLD_ROOT, str(sid % 10), f"{sid}.mdb")
    db = AccessParser(path)
    book = db.parse_table('book')
    title = db.parse_table('title') if 'title' in db.catalog else {}
    nass = book.get('nass', []) if book else []

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    ids = book.get('id', [])
    parts = book.get('part', [])
    pnums = book.get('page', [])
    pages = []
    for i in range(len(ids)):
        pages.append({'id': _int(ids[i]),
                      'part': _int(parts[i]) if i < len(parts) else 0,
                      'page': _int(pnums[i]) if i < len(pnums) else 0,
                      'nass': _decode(nass[i]) if i < len(nass) else ''})
    pages.sort(key=lambda p: p['id'])

    tids = title.get('id', [])
    tlvl = title.get('lvl', [])
    tsub = title.get('sub', [])
    tstr = title.get('tit', [])
    raw = [{'id': _int(tids[i]),
            'lvl': _int(tlvl[i]) if i < len(tlvl) else 0,
            'sub': _int(tsub[i]) if i < len(tsub) else 0,
            'tit': _decode(tstr[i]) if i < len(tstr) else ''}
           for i in range(len(tids))]
    raw.sort(key=lambda t: t['id'])
    return pages, raw


def renumber_titles(raw):
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


def write_book_db(book_id, pages, titled):
    folder = os.path.join(DB_DIR, 'book', str(book_id % 1000).zfill(3))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{book_id}.db")
    if os.path.isfile(path):
        os.unlink(path)
    # defensive: drop duplicate page ids (keep first), keep sequential order
    seen = set()
    uniq = []
    for p in pages:
        if p['id'] in seen:
            continue
        seen.add(p['id'])
        uniq.append(p)
    pages = uniq
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
        jpype.startJVM(classpath=[f"{lucene}/*"], heapsize="8g")
    import atexit as _atexit
    import gc as _gc

    def _shutdown():
        _gc.collect()
        if jpype.isJVMStarted():
            jpype.shutdownJVM()

    _atexit.register(_shutdown)
    import engine
    return engine


# minimal dbmanager stub (engine.Book._getDoc -> CoreDb().sorter())
def install_dbmanager_stub():
    stub = types.ModuleType('dbmanager')

    class _CoreDb:
        def __init__(self):
            cur = sqlite3.connect(MASTER_DB).cursor()
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
            return {'date': 99999, 'author': 0, 'book_up': 0,
                    'group': 0, 'group_order': 0}

    stub.CoreDb = _CoreDb
    sys.modules['dbmanager'] = stub


class InsertBook:
    """Insert-only fast path (no per-doc searcher lease): safe for a fresh
    book whose Lucene docs were just deleted. Mirrors engine.Book logic."""

    def __init__(self, engine, book_id):
        self.engine = engine
        self.Book = engine.Book
        self.book_id = book_id
        self._book = engine.Book(book_id)

    def updatePage(self, page_id, content_dict):
        import re as _re
        content_dict = dict(content_dict)
        if 'page' in content_dict:
            if content_dict['page']:
                full_page = content_dict['page']
                splitter = '\r_________\r'
                if full_page.startswith('舄'):
                    content_dict['foot'] = full_page[1:]
                else:
                    if splitter in full_page:
                        text = full_page.split(splitter, 1)
                        content_dict['body'] = text[0]
                        content_dict['foot'] = text[1]
                    else:
                        content_dict['body'] = full_page
            del content_dict['page']
        empty = True
        for field in ('body', 'foot', 'comment'):
            if content_dict.get(field):
                empty = False
                break
        writer = self.engine.Index.writer('page')
        if not empty:
            doc = self._book._getDoc()
            self.engine.Field('id', self.engine.FieldType.ID,
                              f"{self.book_id}-{page_id}").field()
            self.engine.Field('page', self.engine.FieldType.ORD, page_id).field()
            for field in ('body', 'foot', 'comment'):
                if content_dict.get(field):
                    doc.add(self.engine.Field(field, self.engine.FieldType.TEXT,
                                              content_dict[field]).field())
                    doc.add(self.engine.Field(f"m_{field}",
                                              self.engine.FieldType.ANALYSE,
                                              content_dict[field]).field())
                    n_field = _re.sub('\\D+', ' ', content_dict[field]).strip()
                    if n_field:
                        doc.add(self.engine.Field(f"n_{field}",
                                                  self.engine.FieldType.ANALYSE,
                                                  n_field).field())
            writer.addDocument(doc)

    def updateTitle(self, page_id, title_dict):
        import re as _re
        title_dict = dict(title_dict)
        writer = self.engine.Index.writer('title')
        doc = self._book._getDoc()
        self.engine.Field('id', self.engine.FieldType.ID,
                          f"{self.book_id}-{page_id}").field()
        self.engine.Field('page', self.engine.FieldType.ORD, page_id).field()
        if 'body' in title_dict:
            doc.add(self.engine.Field('body', self.engine.FieldType.TEXT,
                                      title_dict['body']).field())
            doc.add(self.engine.Field('m_body', self.engine.FieldType.ANALYSE,
                                      title_dict['body']).field())
            n_field = _re.sub('\\D+', ' ', title_dict['body']).strip()
            if n_field:
                doc.add(self.engine.Field('n_body', self.engine.FieldType.ANALYSE,
                                          n_field).field())
        if 'parent' in title_dict:
            doc.add(self.engine.Field('parent', self.engine.FieldType.KEY,
                                      (f"{title_dict['parent']}")).field())
        writer.addDocument(doc)

    def finish(self):
        pass


def delete_book_content(engine, book_id):
    """Remove all Lucene page/title/esnad docs for a book (re-run safety)."""
    try:
        engine.Importer.deleteBooks([book_id])
    except Exception:
        pass


def mark_ondisk(book_id, count):
    db = sqlite3.connect(MASTER_DB)
    db.execute('UPDATE book SET major_ondisk = ?, minor_ondisk = 0 '
               'WHERE book_id = ?', (count, book_id))
    db.commit()
    db.close()


def phase_convert(limit=None, force_ondisk=False, commit_every=1):
    if not os.path.isfile(MAP_FILE):
        print("run 'map' first")
        return
    hits = load_hits()
    grows = golden_books()

    install_dbmanager_stub()
    engine = boot()

    m = sqlite3.connect(MASTER_DB)
    m.row_factory = sqlite3.Row

    state = sqlite3.connect(PROGRESS_DB)
    state.execute("CREATE TABLE IF NOT EXISTS converted "
                  "(golden_id INTEGER PRIMARY KEY, book_id INTEGER, pages INTEGER)")
    state.execute("CREATE TABLE IF NOT EXISTS catalog_done "
                  "(golden_id INTEGER PRIMARY KEY, book_id INTEGER)")

    # which golden books are matched to modern ids already on disk?
    ondisk = {r['book_id'] for r in m.execute(
        "SELECT book_id FROM book WHERE major_ondisk > 0")}
    # map golden sid -> target book_id
    golden_sid = {g['id']: g['shamelaID'] for g in grows}
    target = {}
    for sid, v in hits.items():
        target[sid] = v['target']
    for r in state.execute("SELECT golden_id, book_id FROM catalog_done"):
        gid = r[0]
        sid = golden_sid.get(gid)
        if sid:
            target[sid] = r[1]

    done = {r[0] for r in state.execute("SELECT golden_id FROM converted")}
    todo = [g for g in grows
            if g['shamelaID'] in target and g['id'] not in done]
    t0 = time.time()
    n = 0
    pages_done = 0
    pending = []
    fails = 0

    def flush_batch(final=False):
        nonlocal pending
        if not pending:
            return
        engine.Index.commit('page')
        engine.Index.commit('title')
        for gid, book_id, count in pending:
            if count:
                mark_ondisk(book_id, count)
            state.execute("INSERT OR REPLACE INTO converted VALUES (?,?,?)",
                          (gid, book_id, count))
        state.commit()
        pending = []

    for g in todo:
        gid = g['id']
        sid = g['shamelaID']
        if limit and n >= limit:
            break
        book_id = target[sid]
        if book_id in ondisk and not force_ondisk:
            print(f"[skip] {sid} -> {book_id} already on disk", flush=True)
            pending.append((gid, book_id, 0))
            n += 1
            if len(pending) >= commit_every:
                flush_batch()
            continue
        try:
            pages, raw = extract(sid)
            if not pages:
                print(f"[skip] {sid} -> no pages", flush=True)
                pending.append((gid, book_id, 0))
                n += 1
                if len(pending) >= commit_every:
                    flush_batch()
                continue
            titles = renumber_titles(raw)
            titled = derive_title_pages(titles, pages)
            delete_book_content(engine, book_id)
            path = write_book_db(book_id, pages, titled)
            book = InsertBook(engine, book_id)
            for p in pages:
                book.updatePage(p['id'], {'page': p['nass']})
            for t in titled:
                book.updateTitle(t['id'], {'body': t['body'],
                                           'parent': t['parent']})
            pending.append((gid, book_id, len(pages)))
            n += 1
            pages_done += len(pages)
            rate = (time.time() - t0) / n
            print(f"[ok] {sid} -> {book_id} {len(pages)}p/{len(titled)}t "
                  f"({rate:.1f}s/book, {n}/{len(todo)} done, "
                  f"ETA {(len(todo) - n) * rate / 60:.0f}min)",
                  flush=True)
            if len(pending) >= commit_every or len(pages) >= 50000:
                flush_batch()
        except Exception as e:
            fails += 1
            print(f"[FAIL] {sid} -> {book_id}: {e!r}", flush=True)
            continue

    flush_batch()
    print(f"convert: {n} books, {pages_done} pages, {fails} failed, "
          f"{time.time() - t0:.0f}s elapsed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['map', 'catalog', 'convert', 'all'])
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--force-ondisk', action='store_true')
    ap.add_argument('--commit-every', type=int, default=1)
    args = ap.parse_args()

    if args.phase in ('map', 'all'):
        phase_map(force=args.force)
    if args.phase in ('catalog', 'all'):
        phase_catalog(limit=args.limit)
    if args.phase in ('convert', 'all'):
        phase_convert(limit=args.limit, force_ondisk=args.force_ondisk,
                      commit_every=args.commit_every)


if __name__ == '__main__':
    main()
