# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: dbmanager.py
import os, shutil, sqlite3, json, traceback, regex as re
from collections import defaultdict
from threading import Thread
from qtpy.QtGui import QStandardItem
from qtpy.QtCore import QCoreApplication
from across import Across
from dirs import updateDir, resultsFolder, bookPath, masterDbPath, userDbPath, coverDbPath, pdfPath, serviceDbPath, keptCommentsPath
from engine import Service, getElement, Importer, Book, deleteBooks, getSubtitles, wholeSnippet
from theme import Icon
from settings import Settings
from textmanager import conditioned, naturalsize, displayDate, val, arabize, formatBetaka, safeName, textAuthorFolder, formatAuthor, iso
API_VER = 1
ORDER = ' ORDER BY book_date, author.alpha, book.alpha, book.book_id'
GROUP_AUTHOR_ID = 208
UNKNOWN_AUTHOR_ID = 2610
_shared_core = _shared_user = None

def divideList(o_data, limit):
    data = o_data if isinstance(o_data, list) else list(o_data)
    return [data[i:i + limit] for i in range(0, len(data), limit)]


def getPdfVersion(folder):
    from customs import readJson
    json_path = os.path.join(folder, 'versions.json')
    return readJson(json_path)


def startTrackedThread(target, name=None, daemon=False, args=None, kwargs=None):
    args = args or ()
    kwargs = kwargs or {}
    thread = None

    def runner():
        try:
            target(*args, **kwargs)
        finally:
            Across.background_threads.discard(thread)

    thread = Thread(target=runner, name=name, daemon=daemon)
    Across.background_threads.add(thread)
    thread.start()
    return thread


def deObs(b_arry):
    if b_arry:
        return b_arry.decode('cp500').encode('latin_1').decode('cp1256')


def joinAuthors(authors):
    return ' - '.join(authors)


class RedundantAuthors:

    def __init__(self, core_db):
        self.core_db = core_db
        self.changed_authors = {}
        self.stored_authors = {}
        self.books = {}
        self.done_books = set()

    def addChanged(self, author_id, author_name):
        if author_id not in self.changed_authors:
            self.changed_authors[author_id] = author_name

    def addStored(self, author_id, author_name):
        if author_id not in self.stored_authors:
            self.stored_authors[author_id] = author_name

    def addBook(self, book_id, author_list):
        self.books[book_id] = author_list

    def authorName(self, author_id):
        if author_id in self.changed_authors:
            return self.changed_authors[author_id]
        if author_id not in self.stored_authors:
            self.stored_authors[author_id] = self.core_db.authorName(author_id)
        return self.stored_authors[author_id]

    def bookAuthors(self, book_id, authors_list=None):
        if book_id in self.books:
            authors = self.books[book_id]
        else:
            if authors_list:
                authors = [int(author.strip()) for author in authors_list.split(',')]
            else:
                authors = self.core_db.bookAuthors(book_id)
        return joinAuthors([self.authorName(author_id) for author_id in authors])

    def isAuthorNamesChanged(self, authors_list):
        for item in [int(author.strip()) for author in authors_list.split(',')]:
            if item in self.changed_authors:
                return True


class MenDb:

    def __init__(self):
        self.db, self.cur = connectPath(serviceDbPath('S1'))

    def arrange(self, ids):
        return listResults(self.cur.execute(f"SELECT i FROM b WHERE i IN {stringated(ids)} ORDER BY d"))

    def getNames(self, man_list):
        men_dict = {0:'راو مبهم', 
         1:'صحابي مبهم'}
        rows = self.cur.execute(f"SELECT i, s FROM b WHERE i In {stringated(man_list)}").fetchall()
        for row in rows:
            men_dict[row['i']] = deObs(row['s'])

        return men_dict

    def getBothNames(self, man_list):
        men_dict = {0:('راو مبهم', 'راو مبهم'), 
         1:('صحابي مبهم', 'صحابي مبهم')}
        rows = self.cur.execute(f"SELECT i, s, l FROM b WHERE i In {stringated(man_list)}").fetchall()
        for row in rows:
            men_dict[row['i']] = (
             deObs(row['s']), deObs(row['l']))

        return men_dict

    def hasGarh(self, man_id):
        row = self.cur.execute(f"SELECT 1 FROM b WHERE i={man_id} AND a is not null").fetchone()
        if row:
            return True
        return False

    def getShort(self, man_id):
        row = self.cur.execute(f"SELECT s FROM b WHERE i={man_id}").fetchone()
        if row['s']:
            return deObs(row['s'])
        return ''

    def getLong(self, man_id):
        row = self.cur.execute(f"SELECT l FROM b WHERE i={man_id}").fetchone()
        if row['l']:
            return deObs(row['l'])
        return ''

    def getSummary(self, man_id):
        row = self.cur.execute(f"SELECT b, l FROM b WHERE i={man_id}").fetchone()
        summary = json.loads(deObs(row['b'])) if row['b'] else {}
        long = deObs(row['l']) if row['l'] else ''
        return (summary, long)

    def getGarh(self, man_id):
        row = self.cur.execute(f"SELECT a FROM b WHERE i={man_id}").fetchone()
        if row['a']:
            return json.loads(deObs(row['a']))
        return {}

    def __del__(self):
        self.cur.close()
        self.db.close()


class Services:
    services = {'tafseer':1, 
     'hadeeth':1,  'trajim':1}
    show_all_services = {'tafseer'}

    @staticmethod
    def connect(service_name):
        return connectPath(serviceDbPath(service_name))

    @staticmethod
    def isOk():
        error = None
        for service in Services.services:
            if not Services._isOk(service):
                error = True

        if not error:
            return True

    @staticmethod
    def _isOk(service_name):
        db, cur = Services.connect(service_name)
        current_ver = getDbVersion(cur)
        if current_ver != Services.services[service_name]:
            try:
                cur.execute('begin')
                if current_ver < 1:
                    Services.buildServiceTables(cur)
                setDbVersion(cur, Services.services[service_name])
                cur.execute('commit')
                db.close()
            except:
                cur.execute('rollback')
                db.close()
                return

        return True

    @staticmethod
    def clearServices(book_id, pages_id):
        error = None
        for service in Services.services:
            db, cur = Services.connect(service)
            if not Services._clearServices(cur, book_id, pages_id):
                error = True
            commit(db)

        if not error:
            return True

    @staticmethod
    def _clearServices(cur, book_id, pages_id):
        try:
            id_str = str(pages_id).replace('[', '(').replace(']', ')')
            cur.execute(f"DELETE FROM service WHERE book_id={book_id} AND page_id IN {id_str}")
        except:
            return
            return True

    @staticmethod
    def clearBookServices(book_ids):
        error = None
        for service in Services.services:
            db, cur = Services.connect(service)
            if not Services._clearBookServices(cur, book_ids):
                error = True
            commit(db)

        if not error:
            return True

    @staticmethod
    def _clearBookServices(cur, book_ids):
        try:
            if not Service.deleteBooks(book_ids):
                return
            id_str = str(book_ids).replace('[', '(').replace(']', ')')
            cur.execute(f"DELETE FROM service WHERE book_id IN {id_str}")
            cur.execute(f"DELETE FROM inservice WHERE book IN {id_str}")
        except:
            return
            return True

    @staticmethod
    def injectServices(book_id, services, call_back=None):
        error = None
        pages = [page_id for page_id in services]
        if pages:
            if not Service.deletePages(book_id, pages):
                error = True
            else:
                if call_back:
                    call_back(20)
                if not Services.injectTafseer(book_id, services):
                    error = True
                if call_back:
                    call_back(40)
                error = Services.injectHadeeth(book_id,
                  services, call_back=((lambda percent: call_back(40 + percent * 0.5)) if call_back else None)) or True
        else:
            if call_back:
                call_back(100)
            return error or True

    @staticmethod
    def injectTafseer(book_id, services):
        if not any(('ayat' in services[page_id] for page_id in services)):
            return True
        db, cur = Services.connect('tafseer')
        try:
            deletions = []
            insertions = []
            cur.execute('begin')
            for page_id in services:
                deletions.append(page_id)
                if 'ayat' in services[page_id]:
                    for aya in services[page_id]['ayat']:
                        insertions.append([book_id, page_id, aya])

            if deletions:
                Services._clearServices(cur, book_id, deletions)
            if insertions:
                cur.executemany('INSERT INTO service (book_id, page_id, key_id) VALUES (?, ?, ?)', insertions)
            cur.execute('commit')
        except:
            cur.execute('rollback')

        Services.ensureBook(cur, book_id)
        db.close()

    @staticmethod
    def injectHadeeth(book_id, services, call_back=None):
        if not any(('hadeeth' in services[page_id] or 'esnad' in services[page_id] for page_id in services)):
            return True
        from cache import MenCache, EsnadCache
        db, cur = Services.connect('hadeeth')
        try:
            deletions = []
            insertions = []
            book = Book(book_id)
            cur.execute('begin')
            total = len(services) or 1
            for done, page_id in enumerate(services):
                deletions.append(page_id)
                if 'hadeeth' in services[page_id]:
                    for hadeeth in services[page_id]['hadeeth']:
                        insertions.append([book_id, page_id, hadeeth])

                if 'esnad' in services[page_id]:
                    book.addAsaneed(page_id, services[page_id]['esnad'])
                if call_back:
                    call_back(done / total * 100)

            book.commitBook()
            if deletions:
                Services._clearServices(cur, book_id, deletions)
            if insertions:
                cur.executemany('INSERT INTO service (book_id, page_id, key_id) VALUES (?, ?, ?)', insertions)
            cur.execute('commit')
        except:
            cur.execute('rollback')

        Services.ensureBook(cur, book_id)
        db.close()
        MenCache.clear()
        EsnadCache.clear()

    @staticmethod
    def getBooks(service_name, key_id):
        db, cur = Services.connect(service_name)
        result = Services.getServiceBooks(cur, key_id, service_name in Services.show_all_services)
        db.close()
        return result

    @staticmethod
    def getAllBooks(service_name):
        db, cur = Services.connect(service_name)
        result = Services.getAllServiceBooks(cur)
        db.close()
        return result

    @staticmethod
    def saveServiceSelection(service_name, selection_dict):
        db, cur = Services.connect(service_name)
        try:
            books = cur.execute('SELECT book, user_excluded FROM inservice').fetchall()
            for book in books:
                if book[0] in selection_dict and book[1] == selection_dict[book[0]]:
                    del selection_dict[book[0]]

            if selection_dict:
                cur.execute('begin')
                for book in selection_dict:
                    cur.execute('UPDATE inservice SET user_excluded = ? WHERE book = ?', (selection_dict[book], book))

                commit(db)
            else:
                db.close()
        except:
            db.close()

    @staticmethod
    def hasBooks(service_name):
        db, cur = Services.connect(service_name)
        rows = cur.execute('SELECT 1 FROM inservice LIMIT 1').fetchone()
        db.close()
        if rows:
            return True
        return False

    @staticmethod
    def isPageInService(book, page, service_name):
        db, cur = Services.connect(service_name)
        row = cur.execute(f"SELECT key_id FROM service WHERE book_id ={book} AND page_id={page} LIMIT 1").fetchone()
        if not row:
            db.close()
            return
        key_id = row['key_id']
        rows = cur.execute(f"SELECT 1 FROM service WHERE key_id ={key_id} LIMIT 2").fetchall()
        db.close()
        if rows:
            if len(rows) == 2:
                return key_id

    @staticmethod
    def getPositions(service_name, key_id):
        db, cur = Services.connect(service_name)
        rows = cur.execute(f"SELECT book_id, page_id FROM service WHERE key_id ={key_id}").fetchall()
        db.close()
        if rows:
            return [(row['book_id'], row['page_id']) for row in rows]
        return []

    @staticmethod
    def buildServiceTables(cur):
        cur.execute('CREATE TABLE service (key_id INTEGER, book_id INTEGER, page_id INTEGER)')
        cur.execute('CREATE INDEX key_id ON service (key_id)')
        cur.execute('CREATE INDEX book_id ON service (book_id)')
        cur.execute('CREATE INDEX page_id ON service (page_id)')
        cur.execute('CREATE TABLE inservice (book INTEGER, user_excluded INTEGER DEFAULT 0)')
        cur.execute('CREATE INDEX book ON inservice (book)')
        cur.execute('CREATE INDEX user_excluded ON inservice (user_excluded)')

    @staticmethod
    def getServiceBooks(cur, key_id, show_all=False):
        """
        :return:  a list of tuples (book_id, book_category, a list of positions)
        """
        positions = cur.execute(f"SELECT service.book_id, service.page_id\n        FROM service INNER JOIN inservice ON service.book_id = inservice.book\n        WHERE service.key_id = {key_id} AND inservice.user_excluded = 0\n        ORDER BY service.page_id\n        ").fetchall()
        if not positions:
            positions = cur.execute(f"SELECT service.book_id, service.page_id\n            FROM service INNER JOIN inservice ON service.book_id = inservice.book\n            WHERE service.key_id = {key_id} ORDER BY service.page_id\n            ").fetchall()
        book_dict = defaultdict(list)
        for position in positions:
            book_dict[position[0]].append(position[1])

        if show_all:
            for book_id, in cur.execute('SELECT book FROM inservice WHERE user_excluded = 0').fetchall():
                if book_id not in book_dict:
                    book_dict[book_id] = []

        if book_dict:
            books = CoreDb().categorizedBooks(list(book_dict.keys()))
            return [(book[0], book[1], book_dict[book[0]]) for book in books]

    @staticmethod
    def getAllServiceBooks(cur):
        """
        :return:  a list of tuples (book_id, book_category, user_excluded)
        """
        books = cur.execute('SELECT book, user_excluded FROM inservice').fetchall()
        if books:
            book_dict = {}
            for book in books:
                book_dict[book[0]] = book[1]

            books = CoreDb().categorizedBooks(list(book_dict.keys()))
            return [(book[0], book[1], book_dict[book[0]]) for book in books]

    @staticmethod
    def ensureBook(cur, book_id):
        rows = cur.execute(f"SELECT 1 FROM inservice where book = {book_id} LIMIT 1").fetchone()
        stored = True if rows else False
        rows = cur.execute(f"SELECT 1 FROM service where book_id = {book_id} LIMIT 1").fetchone()
        fresh = True if rows else False
        if stored != fresh:
            if fresh:
                cur.execute('INSERT INTO inservice (book, user_excluded) VALUES (?, ?)', (book_id, 0))
            else:
                cur.execute(f"DELETE FROM inservice WHERE book ={book_id}")


def commit(db):
    try:
        db.commit()
        db.close()
    except:
        pass


class CoverDb:
    CLEAN_VER = 2

    def __init__(self):
        self.db, self.cur = connectPath(coverDbPath())

    def isOk(self):
        DB_VER = 1
        current_ver = getDbVersion(self.cur)
        if current_ver < DB_VER:
            try:
                self.cur.execute('begin')
                if current_ver < 1:
                    self.cur.execute('CREATE TABLE IF NOT EXISTS cover (id INTEGER PRIMARY KEY, cover BLOB)')
                    CoreDb().evacuateCovers()
                setDbVersion(self.cur, DB_VER)
                self.cur.execute('commit')
            except:
                self.cur.execute('rollback')
                return

        return True

    def ensureClean(self):
        """The whole covers reset in one place, run right before the download list
        is built: version 2 means every stored cover entered validated and under
        its correct book id (the old chain could fork and cross-save covers, which
        is undetectable afterwards). Anything below 2 gets wiped - rows deleted,
        master unmarked so everything re-downloads - and only a store proven empty
        is ever stamped 2, all in one transaction."""
        if getDbVersion(self.cur) >= self.CLEAN_VER:
            return True
        try:
            self.cur.execute('begin')
            self.cur.execute('DELETE FROM cover')
            if self.cur.execute('SELECT COUNT(*) FROM cover').fetchone()[0]:
                self.cur.execute('rollback')
                return
            setDbVersion(self.cur, self.CLEAN_VER)
            CoreDb().evacuateCovers()
            self.cur.execute('commit')
            return True
        except:
            try:
                self.cur.execute('rollback')
            except:
                pass

            return

    def load(self, book_id, pdf_links):
        result = self.cur.execute(f"SELECT cover FROM cover WHERE id = {book_id}").fetchone()
        if result:
            return result[0]
        if pdf_links:
            if 'cover_alias' in pdf_links:
                cover_alias_id = json.loads(pdf_links)['cover_alias']
                return self.load(cover_alias_id, None)
            if 'alias' in pdf_links:
                alias_id = json.loads(pdf_links)['alias']
                return self.load(alias_id, None)

    def save(self, id_ver, data):
        try:
            self.cur.execute('INSERT OR REPLACE INTO cover (id, cover) VALUES(?, ?)', (id_ver[0], data))
            CoreDb().coverDone(id_ver)
            self.db.commit()
            return True
        except:
            return

    def delCover(self, book_id):
        self.cur.execute(f"DELETE FROM cover WHERE id = {book_id}")

    def commit(self):
        self.db.commit()

    def __del__(self):
        try:
            self.db.commit()
            self.cur.close()
            self.db.close()
        except Exception:
            pass


class _UserDb:

    def __init__(self):
        self.db, self.cur = connectPath(userDbPath())

    def isOk(self):
        DB_VER = 8
        current_ver = getDbVersion(self.cur)
        if current_ver < DB_VER:
            try:
                self.cur.execute('begin')
                if current_ver < 7:
                    self.cur.execute('CREATE TABLE last_viewed (book_id INTEGER PRIMARY KEY, page_id INTEGER, time INTEGER)')
                    self.cur.execute('CREATE INDEX view_time ON last_viewed(time)')
                    self.cur.execute('CREATE TABLE search_phrase (addition INTEGER PRIMARY KEY, phrase TEXT)')
                    self.cur.execute('CREATE UNIQUE INDEX phrase ON search_phrase(phrase)')
                    self.cur.execute('CREATE TABLE favorite_folder (folder_id INTEGER PRIMARY KEY, folder_order INTEGER, folder_parent INTEGER, folder_text TEXT)')
                    self.cur.execute('CREATE INDEX folder_order ON favorite_folder(folder_order)')
                    self.cur.execute('CREATE INDEX folder_parent ON favorite_folder(folder_parent)')
                    self.cur.execute('CREATE TABLE favorite_book (favorite_id INTEGER PRIMARY KEY, book_id INTEGER, folder_id INTEGER, favorite_name TEXT, favorite_order INTEGER)')
                    self.cur.execute('CREATE INDEX favorite_order ON favorite_book (favorite_order)')
                    self.cur.execute('CREATE TABLE scope (scope_id INTEGER PRIMARY KEY, scope_name TEXT, scope_json TEXT, scope_order INTEGER)')
                    self.cur.execute('CREATE INDEX scope_order ON scope (scope_order)')
                    self.cur.execute('CREATE TABLE search (search_id INTEGER PRIMARY KEY, search_name TEXT, search_json TEXT, search_order INTEGER)')
                    self.cur.execute('CREATE INDEX search_order ON search (search_order)')
                    self.cur.execute('CREATE TABLE session (session_id INTEGER PRIMARY KEY, session_name TEXT, session_json TEXT, session_order INTEGER)')
                    self.cur.execute('CREATE INDEX session_order ON session (session_order)')
                    self.cur.execute('CREATE TABLE store (key TEXT, value TEXT)')
                    self.cur.execute('CREATE UNIQUE INDEX key ON store (key)')
                    self.cur.execute('CREATE TABLE last_downloaded (book_id INTEGER INTEGER PRIMARY KEY, time INTEGER)')
                    self.cur.execute('CREATE TABLE last_downloaded_pdf (book_id INTEGER INTEGER PRIMARY KEY, time INTEGER)')
                    self.cur.execute('CREATE TABLE diacritic (book_id INTEGER PRIMARY KEY, diacritic BOOLEAN)')
                    self.cur.execute('CREATE TABLE result_hash (context_id TEXT, hash_value TEXT)')
                    self.cur.execute('CREATE INDEX context_id ON result_hash (context_id)')
                    self.cur.execute('CREATE INDEX hash_value ON result_hash (hash_value)')
                    self.cur.execute('CREATE TABLE search_history (search_id INTEGER PRIMARY KEY, search_json TEXT)')
                    self.cur.execute('CREATE INDEX search_json ON search_history (search_json)')
                    self.cur.execute('CREATE TABLE session_history (session_id INTEGER PRIMARY KEY, session_json TEXT)')
                    self.cur.execute('CREATE INDEX session_json ON session_history (session_json)')
                if current_ver < 8:
                    self.cur.execute('DROP INDEX IF EXISTS search_json')
                    self.cur.execute('CREATE INDEX IF NOT EXISTS search_json ON search_history (search_json)')
                setDbVersion(self.cur, DB_VER)
                self.cur.execute('commit')
            except:
                return

        return True

    def addResultHash(self, context_id, hash_value):
        self.cur.execute('INSERT INTO result_hash (context_id, hash_value) VALUES (?, ?)', (context_id, hash_value))

    def orphanHashes(self, results_folder, context_id):
        hashes = listResults(self.cur.execute('SELECT DISTINCT hash_value FROM result_hash WHERE context_id = ?', (context_id,)))
        self.cur.execute('DELETE FROM result_hash WHERE context_id = ?', (context_id,))
        for test_hash in hashes:
            result = self.cur.execute('SELECT 1 FROM result_hash WHERE hash_value = ?', (test_hash,)).fetchone()
            if not result:
                try:
                    os.unlink(os.path.join(results_folder, f"{test_hash}.o"))
                except:
                    pass

    def newSessionId(self):
        result = self.cur.execute('SELECT MAX(session_id) FROM session_history').fetchone()
        return (result[0] or 0) + 1

    def lastSession(self):
        result = self.cur.execute('SELECT MAX(session_id) FROM session_history').fetchone()
        if result[0]:
            session = self.cur.execute(f"SELECT session_json FROM session_history WHERE session_id={result[0]}").fetchone()[0]
            return json.loads(session)

    def loadSessionHistory(self):
        return {result['session_id']: json.loads(result['session_json']) for result in self.cur.execute('SELECT session_id, session_json FROM session_history ORDER BY session_id DESC')}

    def sessionById(self, session_id):
        value = self.cur.execute(f"SELECT session_json FROM session_history WHERE session_id = {session_id}").fetchone()[0]
        return json.loads(value)

    def addSessionHistory(self, session, new_id):
        if session:
            j = json.dumps(session, ensure_ascii=False)
            result = self.cur.execute('SELECT session_id from session_history WHERE session_json = ? LIMIT 1', (j,)).fetchone()
            if result:
                current_id = result[0]
                self.cur.execute('UPDATE session_history SET session_id = ? WHERE session_id =?', (new_id, current_id))
                self.cur.execute('UPDATE result_hash SET context_id = ? WHERE context_id =?', (f"session_history_{new_id}", f"session_history_{current_id}"))
            else:
                self.cur.execute('INSERT INTO session_history (session_id, session_json) VALUES (?, ?)', (new_id, j))
            values = keepTop((self.cur), 1000, 'session_history', 'session_id', record_deleted='session_id')
            if values:
                results_folder = resultsFolder()
                for value in values:
                    self.orphanHashes(results_folder, f"session_history_{value}")

    def addSearchHistory(self, search_json):
        if search_json:
            j = json.dumps(search_json, ensure_ascii=False)
            result = self.cur.execute('SELECT MAX(search_id) FROM search_history').fetchone()
            max_id = result[0] or 0
            new_id = max_id + 1
            result = self.cur.execute('SELECT search_id from search_history WHERE search_json = ? LIMIT 1', (j,)).fetchone()
            if result:
                current_id = result[0]
                if current_id != max_id:
                    self.cur.execute('UPDATE search_history SET search_id = ? WHERE search_id =?', (new_id, current_id))
            else:
                self.cur.execute('INSERT INTO search_history (search_id, search_json) VALUES (?, ?)', (new_id, j))
            keepTop(self.cur, 1000, 'search_history', 'search_id')

    def loadSearchHistory(self):
        return {result['search_id']: json.loads(result['search_json']) for result in self.cur.execute('SELECT search_id, search_json FROM search_history ORDER BY search_id DESC')}

    def deleteSearchHistory(self, ids):
        self.cur.execute(f"DELETE FROM search_history WHERE search_id IN {stringated(ids)}")

    def clearSearchHistory(self):
        self.cur.execute('DELETE FROM search_history')

    def deleteSessionHistory(self, ids):
        self.cur.execute(f"DELETE FROM session_history WHERE session_id IN {stringated(ids)}")

    def clearSessionHistory(self):
        self.cur.execute('DELETE FROM session_history')

    def addSearchPhrases(self, phrases_list):
        from customs import CompleterModel
        for phrase in phrases_list:
            result = self.cur.execute('SELECT MAX(addition) FROM search_phrase').fetchone()
            max_id = result[0] or 0
            new_id = max_id + 1
            result = self.cur.execute('SELECT addition FROM search_phrase WHERE phrase = ? LIMIT 1', (phrase,)).fetchone()
            if result:
                current_id = result[0]
                if current_id != max_id:
                    self.cur.execute('UPDATE search_phrase SET addition = ? WHERE addition =?', (new_id, current_id))
                self.cur.execute('UPDATE search_phrase SET addition = ? WHERE phrase = ?', (new_id, phrase))
            else:
                self.cur.execute('INSERT INTO search_phrase(phrase, addition) VALUES(?, ?)', (phrase, new_id))
                CompleterModel(self).addPhrase(phrase)

    def fillPhrasesModel(self, model):
        keepTop(self.cur, 7000, 'search_phrase', 'addition')
        for result in self.cur.execute('SELECT phrase FROM search_phrase'):
            model.appendRow(QStandardItem(result[0]))

    def subtract(self, key, book_list):
        current_set = set(self.load(key, []))
        if current_set:
            current_set = current_set - set(book_list)
            self.save(key, list(current_set))
            return current_set
        return set()

    def load(self, key, default=None):
        result = self.cur.execute('SELECT value FROM store WHERE key = ?', (key,)).fetchone()
        if result:
            if result[0]:
                try:
                    return json.loads(result[0])
                except:
                    pass

        return default

    def save(self, key, value):
        j = json.dumps(value, ensure_ascii=False)
        self.cur.execute('INSERT OR REPLACE INTO store (key, value) VALUES(?, ?)', (key, j))
        self.db.commit()

    def saveSettings(self, value):
        self.save(f"settings_{Across.os}", value)

    def loadSettings(self):
        return self.load(f"settings_{Across.os}", {})

    def getDownloadHistory(self, book_type, allowed_set):
        table = 'last_downloaded' if book_type == 'text' else 'last_downloaded_pdf'
        results = self.cur.execute(f"SELECT book_id FROM {table}  ORDER BY time DESC").fetchall()
        books = [result[0] for result in results if result[0] in allowed_set]
        return books

    def updateDownloadHistory(self, book_type, book_id):
        table = 'last_downloaded' if book_type == 'text' else 'last_downloaded_pdf'
        result = self.cur.execute(f"SELECT MAX(time) FROM {table}").fetchone()
        max_id = result[0] + 1 if result[0] else 1
        self.cur.execute(f"INSERT OR REPLACE INTO {table}(book_id, time) VALUES(?, ?)", (book_id, max_id))
        self.db.commit()
        for widget in Across.refresh_set:
            widget.reHistory()

    def updateHistory(self, book_id, page_id):
        result = self.cur.execute('SELECT MAX(time) FROM last_viewed').fetchone()
        max_id = result[0] + 1 if result[0] else 1
        self.cur.execute('INSERT OR REPLACE INTO last_viewed(book_id, page_id, time) VALUES(?, ?, ?)', (book_id, page_id, max_id))
        self.db.commit()
        for widget in Across.refresh_set:
            widget.reHistory()

    def getPageFromHistory(self, book_id):
        results = self.cur.execute(f"SELECT page_id FROM last_viewed WHERE book_id = {book_id}").fetchone()
        if results:
            return results[0]

    def getHistory(self, allowed_set):
        results = self.cur.execute('SELECT book_id FROM last_viewed ORDER BY time DESC').fetchall()
        return [result[0] for result in results if result[0] in allowed_set]

    def getFavoriteBooks(self, folder_id, allowed_set):
        books = self.cur.execute('SELECT favorite_id, favorite_name, book_id FROM favorite_book WHERE folder_id = ? ORDER BY favorite_order', (
         folder_id,)).fetchall()
        return [book for book in books if book[2] in allowed_set]

    def addFavoriteBooks(self, book_ids, folder_id):
        core_db = CoreDb()
        excluded_ids = set()
        excluded_orders = set()
        favorite_ids = []
        for book_id in book_ids:
            favorite_id = gapInColumn(self.cur, 'favorite_book', 'favorite_id', excluded_ids)
            excluded_ids.add(favorite_id)
            favorite_ids.append(favorite_id)
            favorite_order = nextInColumn(self.cur, 'favorite_book', 'favorite_order', excluded_orders)
            excluded_orders.add(favorite_order)
            favorite_name = core_db.bookName(book_id)
            self.cur.execute('INSERT INTO favorite_book (favorite_id, favorite_order, favorite_name, book_id, folder_id) VALUES (?,?,?,?,?)', (
             favorite_id, favorite_order, favorite_name, book_id, folder_id))

        return favorite_ids

    def newFavorite(self, folder_text, parent_id=0):
        new_order = 0
        rows = self.cur.execute('SELECT folder_id FROM favorite_folder WHERE folder_parent = ? ORDER BY folder_order', (
         parent_id,)).fetchall()
        host_ids = [row[0] for row in rows]
        for folder_id in host_ids:
            self.cur.execute('UPDATE favorite_folder SET folder_order = ? WHERE folder_id = ?', (new_order, folder_id))
            new_order += 1

        folder_id = gapInColumn(self.cur, 'favorite_folder', 'folder_id')
        self.cur.execute('INSERT INTO favorite_folder (folder_id, folder_order, folder_text, folder_parent) VALUES (?,?,?,?)', (
         folder_id, new_order, folder_text, parent_id))
        return folder_id

    def reparentFavorites(self, folder_ids, new_parent, position):
        new_order = 0
        rows = self.cur.execute('SELECT folder_id FROM favorite_folder WHERE folder_parent =? ORDER BY folder_order', (
         new_parent,)).fetchall()
        host_ids = [row[0] for row in rows]
        for folder_id in host_ids:
            if new_order == position:
                new_order += len(folder_ids)
            self.cur.execute('UPDATE favorite_folder SET folder_order = ? WHERE folder_id = ?', (new_order, folder_id))
            new_order += 1

        if position != -1:
            new_order = position
        for folder_id in folder_ids:
            self.cur.execute('UPDATE favorite_folder SET folder_parent = ?, folder_order = ? WHERE folder_id = ?', (
             new_parent, new_order, folder_id))
            new_order += 1

    def moveFavorites(self, old_list, new_list):
        order_list = [self.cur.execute('SELECT folder_order FROM favorite_folder WHERE folder_id = ? LIMIT 1', (favorite_id,)).fetchone()[0] for favorite_id in old_list]
        for i, favorite_id in enumerate(new_list):
            self.cur.execute('UPDATE favorite_folder SET folder_order = ? WHERE folder_id = ? ', (
             order_list[i], favorite_id))

    def renameFavorite(self, favorite_id, favorite_text):
        self.cur.execute('UPDATE favorite_folder SET folder_text = ? WHERE folder_id = ? ', (
         favorite_text, favorite_id))

    def renameFavoriteBook(self, favorite_id, favorite_text):
        self.cur.execute('UPDATE favorite_book SET favorite_name = ? WHERE favorite_id = ? ', (
         favorite_text, favorite_id))

    def listFavoriteBooks(self, id_list, allowed_set):
        id_list = getTree(self.cur, 'favorite_folder', 'folder_id', 'folder_parent', id_list)
        id_str = str(set(id_list)).replace('{', '(').replace('}', ')')
        results = self.cur.execute(f"SELECT book_id FROM favorite_book WHERE folder_id IN {id_str}").fetchall()
        return [result[0] for result in results if result[0] in allowed_set]

    def deleteFavorites(self, id_list):
        id_list = getTree(self.cur, 'favorite_folder', 'folder_id', 'folder_parent', id_list)
        id_str = str(set(id_list)).replace('{', '(').replace('}', ')')
        self.cur.execute(f"DELETE FROM favorite_folder WHERE folder_id IN {id_str}")
        self.cur.execute(f"DELETE FROM favorite_book WHERE folder_id IN {id_str}")

    def baseId(self, base):
        return gapInColumn(self.cur, base, f"{base}_id")

    def saveBaseValue(self, base, name, value, pre_id=None):
        _id = pre_id or self.baseId(base)
        _order = nextInColumn(self.cur, base, f"{base}_order")
        self.cur.execute(f"INSERT INTO {base} ({base}_id, {base}_order, {base}_name, {base}_json) VALUES (?,?,?,?)", (
         _id, _order, name, json.dumps(value, ensure_ascii=False)))
        return _id

    def updateBaseValue(self, base, value, _id):
        name = self.cur.execute(f"SELECT {base}_name FROM {base} WHERE {base}_id={_id}").fetchone()[0]
        self.cur.execute(f"UPDATE {base} SET {base}_json = ? WHERE {base}_id = ?", (json.dumps(value, ensure_ascii=False), _id))
        return name

    def saveBaseId(self, base):
        return gapInColumn(self.cur, base, f"{base}_id")

    def getElements(self, base):
        results = self.cur.execute(f"SELECT {base}_id, {base}_name, {base}_json FROM {base} ORDER BY {base}_order DESC").fetchall()
        _ids = []
        values = {}
        if results:
            for result in results:
                _id = result[f"{base}_id"]
                _ids.append(_id)
                values[_id] = {'name':result[f"{base}_name"],  'json':json.loads(result[f"{base}_json"])}

        return (
         _ids, values)

    def getElementsJson(self, base):
        return self.cur.execute(f"SELECT {base}_id, {base}_json FROM {base}").fetchall()

    def elementJson(self, base, element_id):
        return json.loads(self.cur.execute(f"SELECT {base}_json FROM {base} WHERE {base}_id = {element_id}").fetchone()[0])

    def deleteElements(self, base, id_list):
        id_str = str(set(id_list)).replace('{', '(').replace('}', ')')
        self.cur.execute(f"DELETE FROM {base} WHERE {base}_id IN {id_str}")
        results_folder = resultsFolder()
        for value in id_list:
            self.orphanHashes(results_folder, f"{base}_{value}")

    def renameElement(self, base, element_id, element_text):
        self.cur.execute(f"UPDATE {base} SET {base}_name = ? WHERE {base}_id = ?", (element_text, element_id))
        return self.cur.execute(f"SELECT {base}_name FROM {base} WHERE {base}_id = {element_id}").fetchone()[0]

    def swapElementOrder(self, base, first_id, second_id):
        swapValues(self.cur, base, f"{base}_id", f"{base}_order", first_id, second_id)

    def deleteBooks(self, complete_list):
        success = True
        for book_list in divideList(complete_list, 9000):
            id_str = str(book_list)[1:-1]
            script = f"DELETE FROM favorite_book WHERE book_id IN ({id_str});"
            script += f"DELETE FROM last_downloaded WHERE book_id IN ({id_str});"
            script += f"DELETE FROM last_downloaded_pdf WHERE book_id IN ({id_str});"
            try:
                self.cur.executescript(script)
            except:
                success = None

        return success

    def deletePdfs(self, id_str):
        self.cur.execute(f"DELETE FROM last_downloaded_pdf WHERE book_id IN {id_str}")

    def deleteFavoriteBooks(self, complete_list):
        for book_list in divideList(complete_list, 1000):
            id_str = str(book_list)[1:-1]
            try:
                self.cur.execute(f"DELETE FROM favorite_book WHERE favorite_id IN ({id_str})")
            except:
                pass

    def arrangedFavorites(self):
        return listResults(self.cur.execute('SELECT folder_id FROM favorite_folder ORDER BY folder_order'))

    def favoriteName(self, folder_id):
        return self.cur.execute(f"SELECT folder_text FROM favorite_folder WHERE folder_id = {folder_id}").fetchone()[0]

    def swapFavoriteOrder(self, first_id, second_id):
        swapValues(self.cur, 'favorite_folder', 'folder_id', 'folder_order', first_id, second_id)

    def swapFavoriteBookOrder(self, first_id, second_id):
        swapValues(self.cur, 'favorite_book', 'favorite_id', 'favorite_order', first_id, second_id)

    def getFavoritesHeads(self, default_favorite):
        rows = self.cur.execute('SELECT folder_text, folder_id FROM favorite_folder WHERE folder_parent = 0 ORDER BY folder_order').fetchall()
        return rows or [[default_favorite, self.newFavorite(default_favorite, 0)]]

    def getFavoriteNodes(self, top_id, default_text):
        folders = {}
        self.addFavoriteNodes(folders, top_id)
        if len(folders) == 0:
            new_id = self.newFavorite(default_text, top_id)
            folders[new_id] = [default_text, top_id]
        return folders

    def addFavoriteNodes(self, nodes, parent_id):
        rows = self.cur.execute('SELECT * FROM favorite_folder WHERE folder_parent = ? ORDER BY folder_order', (
         parent_id,)).fetchall()
        for row in rows:
            nodes[row['folder_id']] = [
             row['folder_text'], row['folder_parent']]
            self.addFavoriteNodes(nodes, row['folder_id'])

    def isDiacritized(self, book_id):
        row = self.cur.execute('SELECT diacritic FROM diacritic WHERE book_id = ?', (book_id,)).fetchone()
        if row:
            return row[0]

    def setDiacritized(self, book_id, value):
        self.cur.execute('INSERT OR REPLACE INTO diacritic(book_id, diacritic) VALUES(?, ?)', (book_id, int(value)))
        self.db.commit()

    def commit(self):
        self.db.commit()

    def __del__(self):
        self.db.commit()
        self.cur.close()
        self.db.close()


class BookDb:

    def __init__(self, book_id):
        self.book_id = book_id
        self.parts_list = self.has_numbers = self.meta = self.pdf = self._import_success = None
        self.db, self.cur = connectBook(self.book_id)

    def freshServices(self, call_back=None):
        try:
            rows = self.cur.execute('SELECT id, services FROM page WHERE services IS NOT NULL ORDER BY id')
            services = {}
            for row in rows:
                if row['services']:
                    services[row['id']] = json.loads(row['services'])

            if call_back:
                call_back(5)
            if services:
                Services.injectServices(self.book_id, services, call_back)
            if call_back:
                call_back(100)
            return True
        except:
            pass

    def hasAlias(self):
        return self.tableExists('alias')

    def getAlias(self, this_id):
        result = self.cur.execute(f"SELECT book_id, page_id FROM alias WHERE this_id = {this_id}").fetchone()
        if result:
            return (
             result[0], result[1])
        return (self.book_id, this_id)

    def getAliases(self, min_id, max_id):
        results = self.cur.execute(f"SELECT this_id, book_id, page_id FROM alias WHERE this_id >={min_id} and this_id <={max_id}").fetchall()
        if results:
            map_dict = {}
            for result in results:
                map_dict[f"{result['book_id']}-{result['page_id']}"] = f"{self.book_id}-{result['this_id']}"

            return map_dict
        return {}

    def getOrigin(self, book_id, page_id):
        return self.cur.execute(f"SELECT this_id FROM alias WHERE book_id = {book_id} AND page_id = {page_id}").fetchone()[0]

    def getMeta(self):
        if self.meta is None:
            self.meta = CoreDb().getMeta(self.book_id)
        return self.meta

    def partsMap(self):
        parts_list = []
        parts_set = set()
        parts_dict = defaultdict(BookPart)
        rows = self.cur.execute('SELECT id, part, page FROM page ORDER BY id')
        for row in rows:
            key = row['part']
            if not key:
                key = '0'
            if key not in parts_set:
                parts_set.add(key)
                parts_list.append(key)
            parts_dict[key].addPage(row['id'], row['page'])

        return (
         parts_list, parts_dict)

    def partsList(self):
        if self.parts_list is None:
            parts = self.cur.execute('SELECT DISTINCT part FROM page ORDER BY id').fetchall()
            if parts:
                if parts[0][0]:
                    self.parts_list = [arabize(part[0]) for part in parts]
                    return self.parts_list
            self.parts_list = []
        return self.parts_list

    def hasParts(self):
        if self.partsList():
            return True
        return False

    def hasChildren(self, title_id):
        self.cur.execute('SELECT id FROM title WHERE parent = ? LIMIT 1', (title_id,))
        return self.cur.fetchone() is not None

    def tableExists(self, table_name):
        return tableExists(self.cur, table_name)

    def indexExist(self, index_name):
        self.cur.execute('SELECT COUNT(*) FROM sqlite_master WHERE type = "index" AND name = ?', (index_name,))
        return self.cur.fetchone()[0] == 1

    def getTitle(self, page_id):
        import engine
        results = self.cur.execute('SELECT id FROM title WHERE page <= ? ORDER BY id DESC LIMIT 1', (page_id,)).fetchone()
        title_id = results[0] if results else 1
        return engine.getTitle(self.book_id, title_id)

    def tripleAttribute(self, page_id):
        result = self.cur.execute('SELECT part, page, number FROM page WHERE id = ?', (page_id,)).fetchone()
        if result:
            return {'part':result['part'], 
             'page':result['page'],  'number':result['number']}

    def getPageNumber(self, page_id, pre_page=None):
        if not pre_page:
            pre_page = ''
        result = self.cur.execute('SELECT part, page FROM page WHERE id = ?', (page_id,)).fetchone()
        value = ''
        if result:
            if result['part']:
                if result['part'] != 'الكتاب':
                    value += f"{result['part']}/ "
            if value != '':
                pre_page = ''
            if result['page']:
                value += f"{pre_page}{result['page']}"
        return value

    def getBestAttribute(self, page_id, detailed):
        value = None
        hadeeth, page = ('حديث ', 'صفحة ') if detailed else ('', 'ص ')
        try:
            result = self.cur.execute('SELECT number FROM page WHERE id = ?', (page_id,)).fetchone()
            value = result['number']
        except:
            pass

        if value:
            return f"{hadeeth}{value}"
        return (f"{self.getPageNumber(page_id, page)}")

    def getTitlePageNumber(self, title_id):
        page_id = self.cur.execute('SELECT page FROM title WHERE id = ?', (title_id,)).fetchone()[0]
        return self.getPageNumber(page_id)

    def getAllParents(self):
        parents = {}
        results = self.cur.execute('SELECT id, parent FROM title').fetchall()
        for result in results:
            parents[result['id']] = result['parent']

        return parents

    def getParentIds(self, page_id, title_id):
        results = self.cur.execute('SELECT id, parent FROM title WHERE page <= ? ORDER BY id DESC LIMIT 1', (
         page_id,)).fetchone()
        if results:
            if results[0] == title_id:
                return title_id
            parents = [
             results[0]]
            while results[1] != 0:
                self.cur.execute('SELECT id, parent FROM title WHERE id = ? ORDER BY id LIMIT 1', (
                 results[1],))
                results = self.cur.fetchone()
                parents.append(results[0])

            return parents

    def getTitles(self, parentId):
        titles_dict = getSubtitles(self.book_id, parentId)
        return [[titles_dict[title_id], title_id, self.hasChildren(title_id)] for title_id in sorted(titles_dict)]

    def getByTitle(self, title_id):
        page_id = self.cur.execute('SELECT page FROM title WHERE id = ?', (title_id,)).fetchone()[0]
        return self.cur.execute('SELECT * FROM page WHERE id = ?', (page_id,)).fetchone()

    def getById(self, page_id):
        return self.cur.execute('SELECT * FROM page WHERE id = ?', (page_id,)).fetchone()

    def getByPart(self, part):
        return self.cur.execute('SELECT * FROM page WHERE part = ? ORDER BY id LIMIT 1', (part,)).fetchone()

    def getByPage(self, page):
        result = self.cur.execute('SELECT * FROM page WHERE page = ? ORDER BY id LIMIT 1', (page,)).fetchone()
        if not result:
            result = self.cur.execute('SELECT * FROM page WHERE page < ? ORDER BY id DESC LIMIT 1', (page,)).fetchone()
            if not result:
                result = self.cur.execute('SELECT * FROM page WHERE id = 1').fetchone()
        return result

    def getByNumber(self, number):
        result = self.cur.execute('SELECT * FROM page WHERE number = ? ORDER BY id LIMIT 1', (number,)).fetchone()
        if not result:
            result = self.cur.execute('SELECT * FROM page WHERE number < ? ORDER BY id DESC LIMIT 1', (number,)).fetchone()
            if not result:
                result = self.cur.execute('SELECT * FROM page WHERE id = 1').fetchone()
        return result

    def getByPartPage(self, part, page):
        result = self.cur.execute('SELECT * FROM page WHERE part = ? AND page = ? ORDER BY id LIMIT 1', (part, page)).fetchone()
        if not result:
            result = self.cur.execute('SELECT * FROM page WHERE part = ? AND page < ? ORDER BY id DESC LIMIT 1', (part, page)).fetchone()
            if not result:
                result = self.cur.execute('SELECT * FROM page WHERE part = ? ORDER BY id LIMIT 1', (part,)).fetchone()
        return result

    def getId(self, page_id, part, page, number):
        if not self.hasParts():
            part = None
        else:
            if not self.hasNumbers():
                number = None
            else:
                sql = 'SELECT 1 FROM page WHERE id = ?'
                params = [page_id]
                if page:
                    sql += ' AND number = ?'
                    params.append(page)
                else:
                    sql += ' AND page IS NULL'
            if part:
                sql += ' AND part = ?'
                params.append(part)
            if number:
                sql += ' AND number = ?'
                params.append(number)
            result = self.cur.execute(sql + ' LIMIT 1', params).fetchone()
            if result:
                return page_id
            if number:
                if part:
                    result = self.cur.execute('SELECT id FROM page WHERE part = ? AND page = ? AND number = ? ORDER BY id LIMIT 1', (part, page, number)).fetchone()
                else:
                    result = self.cur.execute('SELECT id FROM page WHERE page = ? AND number = ? ORDER BY id LIMIT 1', (page, number)).fetchone()
                if not result:
                    result = self.cur.execute('SELECT id FROM page WHERE number = ? ORDER BY id LIMIT 1', (number,)).fetchone()
                    if not result:
                        result = self.cur.execute('SELECT id FROM page WHERE number < ? ORDER BY id DESC LIMIT 1', (number,)).fetchone()
                if result:
                    return result[0]
        if part:
            result = self.cur.execute('SELECT id FROM page WHERE part = ? AND page = ? ORDER BY id LIMIT 1', (part, page)).fetchone()
            result = result or self.cur.execute('SELECT id FROM page WHERE part = ? AND page < ? ORDER BY id DESC LIMIT 1', (part, page)).fetchone()
            result = result or self.cur.execute('SELECT * FROM page WHERE part = ? ORDER BY id LIMIT 1', (part,)).fetchone()
        else:
            result = self.cur.execute('SELECT id FROM page WHERE page = ? ORDER BY id LIMIT 1', (page,)).fetchone()
            if not result:
                result = self.cur.execute('SELECT id FROM page WHERE page < ? ORDER BY id DESC LIMIT 1', (page,)).fetchone()
            if result:
                return result[0]
            return 1

    def qualify(self, comments):
        insertions = []
        for page_id, comment in comments:
            attributes = self.tripleAttribute(page_id)
            if not attributes:
                continue
            insertions.append([(page_id, attributes['part'], attributes['page'], attributes['number']), comment])

        return insertions

    def mappedComments(self, comments=None):
        from customs import unpack
        if not comments:
            comments = unpack(keptCommentsPath(self.book_id))
        if comments:
            return [((self.getId)(*attribute), comment) for attribute, comment in comments]
        return []

    def commentsImported(self):
        file_path = keptCommentsPath(self.book_id)
        try:
            os.unlink(file_path)
        except:
            pass

        if not os.path.isfile(file_path):
            return True

    def lastId(self):
        return self.cur.execute('SELECT MAX(id) FROM page').fetchone()[0]

    def hasNumbers(self):
        if self.has_numbers is None:
            self.has_numbers = self._hasNumbers()
        return self.has_numbers

    def _hasNumbers(self):
        numbers = self.cur.execute('SELECT DISTINCT number FROM page LIMIT 2').fetchall()
        if numbers:
            if len(numbers) == 2:
                return True
        return False

    def importMinor(self, patch_path, major, minor):
        from customs import pextract
        extract_path = os.path.dirname(patch_path)
        base = os.path.splitext(os.path.basename(patch_path))[0]
        if not pextract(patch_path, extract_path):
            return
        else:
            file_path = os.path.join(extract_path, f"{base}.sqlite")
            return os.path.isfile(file_path) or None
        self._import_success = None
        self._importMinor(file_path)
        if self._import_success:
            return CoreDb().setBookVersion(self.book_id, major, minor)

    def addAlias(self, this_id, this_alias):
        if not tableExists(self.cur, 'alias'):
            self.cur.execute('CREATE TABLE alias (this_id INTEGER PRIMARY KEY, book_id INTEGER, page_id INTEGER)')
            self.cur.execute('CREATE INDEX book_id on alias (book_id)')
            self.cur.execute('CREATE INDEX alias_page on alias (page_id)')
        pieces = this_alias[1:].split('-')
        book_id = int(pieces[0].strip())
        insertRecord(self.cur, 'alias', {'this_id':this_id,  'book_id':book_id,  'page_id':int(pieces[1])})

    def _importMinor(self, file_path):
        book = Book(self.book_id)
        db, cur = connectPath(file_path)
        services = {}
        try:
            try:
                self.cur.execute('begin')
                if tableExists(cur, 'page'):
                    new, updated = segregate(cur, self.cur, 'page')
                    if new:
                        for this_id in new:
                            row = cur.execute(f"SELECT [part], [page], [number], [content], [services] FROM page WHERE id = {this_id}").fetchone()
                            new_record = {'id':this_id,  'part':row['part'],  'page':row['page'],  'number':row['number'],  'services':row['services']}
                            insertRecord(self.cur, 'page', new_record)
                            if row['services']:
                                services[this_id] = json.loads(row['services'])
                            if row['content']:
                                pages_dict = {'id': this_id}
                                if re.search('^ *~ *\\d+ *\\- *\\d+ *$', row['content']):
                                    self.addAlias(this_id, row['content'])
                                else:
                                    pages_dict['page'] = row['content']
                                book.updatePage(this_id, pages_dict)

                    if updated:
                        for this_id in updated:
                            row = cur.execute(f"SELECT [part], [page], [number], [content], [services] FROM page WHERE id = {this_id}").fetchone()
                            updated_string = ''
                            values = []
                            if row['part'] != '#':
                                updated_string += ', [part] = ?'
                                values.append(row['part'])
                            if row['page'] != '#':
                                updated_string += ', [page] = ?'
                                values.append(row['page'])
                            if row['number'] != '#':
                                updated_string += ', [number] = ?'
                                values.append(row['number'])
                            if row['services'] != '#':
                                updated_string += ', [services] = ?'
                                values.append(row['services'])
                                services[this_id] = json.loads(row['services']) if row['services'] else {}
                            if row['content'] != '#':
                                pages_dict = {'id': this_id}
                                if re.search('^ *~ *\\d+ *\\- *\\d+ *$', row['content']):
                                    self.addAlias(this_id, row['content'])
                                else:
                                    pages_dict['page'] = row['content']
                                book.updatePage(this_id, pages_dict)
                            if updated_string:
                                sql = f"update page set {updated_string[1:]} WHERE id = {this_id}"
                                self.cur.execute(sql, values)

                if tableExists(cur, 'title'):
                    new, updated = segregate(cur, self.cur, 'title')
                    if new:
                        for this_id in new:
                            row = cur.execute(f"SELECT [page], [parent], [content] FROM title WHERE id = {this_id}").fetchone()
                            new_record = {'id':this_id,  'page':row['page'],  'parent':row['parent']}
                            insertRecord(self.cur, 'title', new_record)
                            title_dict = {'id': this_id}
                            if row['content']:
                                title_dict['body'] = row['content']
                            title_dict['parent'] = int(row['parent'])
                            book.updateTitle(this_id, title_dict)

                    if updated:
                        for this_id in updated:
                            row = cur.execute(f"SELECT [page], [parent], [content] FROM title WHERE id = {this_id}").fetchone()
                            updated_string = ''
                            values = []
                            title_dict = None
                            if row['page'] != '#':
                                updated_string += ', [page] = ?'
                                values.append(row['page'])
                            if row['parent'] != '#':
                                updated_string += ', [parent] = ?'
                                values.append(row['parent'])
                                if row['content'] == '#':
                                    title_dict = {'id': this_id}
                                    title_dict['parent'] = int(row['parent'])
                                if row['content'] != '#':
                                    title_dict = {'id': this_id}
                                    title_dict['body'] = row['content']
                                    if row['parent'] == '#':
                                        title_dict['parent'] = self.cur.execute(f"SELECT parent FROM title WHERE id ={this_id}").fetchone()[0]
                                    else:
                                        title_dict['parent'] = int(row['parent'])
                                if title_dict:
                                    book.updateTitle(this_id, title_dict)
                                if updated_string:
                                    sql = f"update title set {updated_string[1:]} WHERE id = {this_id}"
                                    self.cur.execute(sql, values)

                if services:
                    Services.injectServices(self.book_id, services)
                book.commitBook()
                self.cur.execute('commit')
                self._import_success = True
            except Exception:
                try:
                    self.cur.execute('rollback')
                except:
                    pass

                traceback.print_exc()

        finally:
            cur.close()
            db.close()

    def __del__(self):
        self.cur.close()
        self.db.close()


def CoreDb():
    global _shared_core
    if _shared_core:
        return _shared_core
    return _CoreDb()


def UserDb():
    global _shared_user
    if _shared_user:
        return _shared_user
    return _UserDb()


def switchUser(value):
    global _shared_user
    _shared_user = _UserDb() if value else None


def switchBoth(value):
    global _shared_core
    global _shared_user
    _shared_core, _shared_user = (_CoreDb(), _UserDb()) if value else (None, None)


def dbLuceneRectify(extract_path, progress_signal):
    from customs import pextract
    shutil.rmtree(extract_path, ignore_errors=True)
    pextract(f"{extract_path}.zip", extract_path, progress_signal=progress_signal)
    author_path = f"{extract_path}/author.sqlite"
    if not os.path.isfile(author_path):
        return
    else:
        book_path = f"{extract_path}/book.sqlite"
        return os.path.isfile(book_path) or None
    db, cur = connectPath(author_path, existent_only=True)
    count = cur.execute('SELECT COUNT(*) FROM author').fetchone()[0]
    progress_signal.emit({'start':count, 
     'tip':QCoreApplication.translate('MainWindow', 'Updating information')})
    i = 0
    author_names = {}
    for result in cur.execute('SELECT id, name, biography, death_number FROM author'):
        author_names[result['id']] = result['name']
        author_dict = {'id':int(result['id']),  'name':result['name'], 
         'date':int(result['death_number']), 
         'biography':result['biography']}
        author_names[author_dict['id']] = author_dict['name']
        Importer.addAuthor(author_dict)
        i += 1
        progress_signal.emit({'value': i})

    progress_signal.emit({'end': True})
    Importer.commitAuthors()
    db, cur = connectPath(book_path, existent_only=True)
    count = cur.execute('SELECT COUNT(*) FROM book').fetchone()[0]
    progress_signal.emit({'start':count, 
     'tip':QCoreApplication.translate('MainWindow', 'Updating information')})
    i = 0
    for result in cur.execute('SELECT id, name, bibliography, hint, date, author, metadata FROM book'):
        book_dict = {'id':int(result['id']), 
         'name':result['name'],  'bibliography':result['bibliography'],  'hint':result['hint'], 
         'date':int(result['date'])}
        author_ids = [int(author_id.strip()) for author_id in result['author'].split(',')]
        book_dict['author'] = author_ids[0]
        book_dict['author_names'] = ' - '.join([author_names[author_id] for author_id in author_ids])
        meta = json.loads(result['metadata']) if result['metadata'] else {}
        book_dict['book_up'] = meta['book_up'] if 'book_up' in meta else None
        book_dict['group'] = meta['group'] if 'group' in meta else None
        book_dict['group_order'] = meta['group_order'] if 'group_order' in meta else None
        Importer.addBook(book_dict, info_only=True)
        i += 1
        progress_signal.emit({'value': i})

    progress_signal.emit({'end': True})
    Importer.commitBookMeta()
    db.close()
    shutil.rmtree((os.path.join(updateDir(), 'fix')), ignore_errors=True)
    return True


class _CoreDb:

    def __init__(self):
        self.db, self.cur = connectPath((masterDbPath()), existent_only=True)
        self._importsuccess = None
        self._alpha_authors = set()
        self._alpha_books = set()
        self._execution_list = []

    def startExecution(self):
        self._execution_list = []

    def addToExecution(self, sql_values_list):
        self._execution_list.append(sql_values_list)

    def execute(self):
        if self._execution_list:
            self.cur.execute('begin')
            try:
                try:
                    for sql, values in self._execution_list:
                        if values:
                            self.cur.execute(sql, values)
                        else:
                            self.cur.execute(sql)

                    self.cur.execute('commit')
                except:
                    self.cur.execute('rollback')

            finally:
                self._execution_list = []

    def __del__(self):
        if self.cur:
            self.cur.close()
            self.db.close()

    def isOk(self):
        current_ver = getDbVersion(self.cur)
        MIN_VER = 5
        DB_VER = 6
        if current_ver < MIN_VER:
            return
        if current_ver < DB_VER:
            try:
                self.cur.execute('begin')
                self.cur.execute('ALTER TABLE author ADD COLUMN alpha INTEGER')
                self.cur.execute('CREATE INDEX alpha_author ON author(alpha)')
                self.cur.execute('ALTER TABLE book ADD COLUMN alpha INTEGER')
                self.cur.execute('ALTER TABLE book ADD COLUMN group_order INTEGER')
                self.cur.execute('ALTER TABLE book ADD COLUMN book_up INTEGER')
                self.cur.execute('CREATE INDEX alpha_book ON book(alpha)')
                self.cur.execute('CREATE INDEX group_order ON book(group_order)')
                self.cur.execute('CREATE INDEX book_up ON book(book_up)')
                self.cur.execute('DROP INDEX IF EXISTS book_order')
                setDbVersion(self.cur, DB_VER)
                self.cur.execute('commit')
            except:
                self.cur.execute('rollback')
                return

        return True

    def loadingCache(self, session):
        cached_values = {}
        book_ids = []
        try:
            if session:
                if session['first']:
                    _, items = session['first']
                    for item in items:
                        key, value = item
                        if key == 'BOOK':
                            book_ids.append(value['book'])

                if 'second' in session:
                    if session['second']:
                        _, items = session['second']
                        for item in items:
                            key, value = item
                            if key == 'BOOK':
                                book_ids.append(value['book'])

        except:
            pass

        if not book_ids:
            return {}
        for row in self.cur.execute(f"SELECT book_id, book_name, book_type, printed, major_ondisk FROM book WHERE book_id in {stringated(book_ids)}"):
            book_id = row['book_id']
            book_dict = {'title': arabize(row['book_name'])}
            book_dict['is_ondisk'] = row['major_ondisk'] > 0
            book_type, printed = row['book_type'], row['printed']
            if book_type == 1:
                if printed == 1:
                    icon_path = ':/icons/printed.png'
                else:
                    icon_path = ':/icons/unprinted.png'
            else:
                if book_type == 2:
                    icon_path = ':/icons/mag-printed.png' if printed == 1 else ':/icons/mag-unprinted.png'
                else:
                    icons = [
                     'manuscript', 'thesis', 'electronic', 'sound']
                    icon_path = f":/icons/{icons[book_type - 3]}.png"
            book_dict['icon'] = Icon.icon(icon_path)
            cached_values[book_id] = book_dict

        for book_id in cached_values:
            cached_values[book_id]['betaka_tip'] = conditioned(self.bookBetaka(book_id, True, truncated=True))

        return cached_values

    @classmethod
    def isAffected(cls, affected_set, ids_list):
        if affected_set:
            for _id in ids_list:
                if _id in affected_set:
                    return True

        else:
            return True

    def alpha(self, catch_all=None):
        error = None
        self.execute()
        if not self.alphaAuthors(catch_all):
            error = True
        else:
            if not self.alphaBooks(catch_all):
                error = True
            if error:
                self.startExecution()
            else:
                self.execute()
                return True

    def alphaAuthors(self, catch_all=None):
        if not catch_all:
            if not self._alpha_authors:
                return True
        from cache import AuthorCache
        AuthorCache.clear()
        progress_signal = Across.main_window.progress.progress_signal
        try:
            rows = self.cur.execute("SELECT death_number, COUNT(*), GROUP_CONCAT(author_id, ',') AS ids\n                         FROM author\n                         GROUP BY death_number\n                         HAVING COUNT(*) > 1").fetchall()
            if catch_all:
                progress_signal.emit({'start':len(rows),  'tip':QCoreApplication.translate('MainWindow', 'Sorting author names')})
            for n, row in enumerate(rows, 1):
                if catch_all:
                    progress_signal.emit({'value': n})
                ids_list = [int(item.strip()) for item in row['ids'].split(',')]
                if catch_all or self.isAffected(self._alpha_authors, ids_list):
                    ids_list = sorted(ids_list, key=(AuthorCache.authorName))
                    for i, _id in enumerate(ids_list, 1):
                        self.addToExecution(['update author set alpha = ? WHERE author_id = ?', (i, _id)])

            progress_signal.emit({'end': True})
            return True
        except:
            pass

    def alphaBooks(self, catch_all=None):
        if not catch_all:
            if not self._alpha_books:
                return True
        from cache import BookCache
        BookCache.clear()
        progress_signal = Across.main_window.progress.progress_signal
        try:
            rows = self.cur.execute("SELECT main_author, COUNT(*), GROUP_CONCAT(book_id, ',') AS ids\n                         FROM book\n                         GROUP BY main_author\n                         HAVING COUNT(*) > 1").fetchall()
            if catch_all:
                progress_signal.emit({'start':len(rows),  'tip':QCoreApplication.translate('MainWindow', 'Sorting book names')})
            for n, row in enumerate(rows, 1):
                if catch_all:
                    progress_signal.emit({'value': n})
                ids_list = [int(item.strip()) for item in row['ids'].split(',')]
                if catch_all or self.isAffected(self._alpha_books, ids_list):
                    ids_list = sorted(ids_list, key=(BookCache.bookName))
                    for i, _id in enumerate(ids_list, 1):
                        self.addToExecution(['update book set alpha = ? WHERE book_id = ?', (i, _id)])

            progress_signal.emit({'end': True})
            return True
        except:
            pass

    def arrangeBooks(self, books):
        if not books:
            return []
        return listResults(self.cur.execute(f"SELECT book_id FROM book INNER JOIN author ON book.main_author = author.author_id WHERE book_id IN {stringated(books)}{ORDER}"))

    def addToIgnore(self, context, books, value):
        from cache import BookCache
        hidden_map = {2:0, 
         4:1,  5:2}
        current = {}
        results = self.cur.execute(f"SELECT book_id, hidden FROM book where book_id in {stringated(books)}")
        for result in results:
            hidden = numberToHidden(result['hidden'])
            hidden[hidden_map[context]] = 1 if value else 0
            current[result['book_id']] = hiddenToNumber(*hidden)

        try:
            self.cur.execute('begin')
            for key in current:
                self.cur.execute('UPDATE book SET hidden = ? WHERE book_id = ?', (current[key], key))

            self.db.commit()
        except:
            self.cur.execute('rollback')
            return
            for book_id in books:
                BookCache.clear(book_id)

            return True

    def ignoreList(self, context):
        from cache import BookCache
        return listResults(self.cur.execute(f"SELECT book_id FROM book INNER JOIN author ON book.main_author = author.author_id WHERE hidden in {stringated(BookCache.viewSet(context, False))}{ORDER}"))

    def fixhalf(self):
        """To fix a previous logical error"""
        try:
            self.cur.execute('UPDATE book SET major_ondisk = 0 WHERE major_ondisk = 0.5')
        except:
            return
            self.db.commit()
            return True

    def categorizedBooks(self, book_list):
        id_str = str(book_list)[1:-1]
        results = self.cur.execute(f"SELECT book.book_id, book.book_category FROM book\n        INNER JOIN category ON book.book_category = category.category_id \n        INNER JOIN author ON book.main_author = author.author_id \n        WHERE book.book_id IN ({id_str}) AND{getOnline(1)}\n        ORDER BY category.category_order, book.book_date, author.alpha, book.alpha, book.group_order\n        ").fetchall()
        return results

    def minors(self):
        return listResults(self.cur.execute('SELECT book_id FROM book WHERE major_online = major_ondisk AND minor_online > minor_ondisk'))

    def hasMinors(self):
        rows = self.cur.execute('SELECT 1 FROM book WHERE major_online = major_ondisk AND minor_online > minor_ondisk LIMIT 1').fetchone()
        if rows:
            return True

    def fillAuthorCache(self, author_id):
        result = self.cur.execute(f"SELECT author_name, death_text, death_number From author WHERE author_id ={author_id}").fetchone()
        return (result[0], result[1], result[2])

    def pdfSize(self, book_id, raw=None):
        row = self.cur.execute('SELECT pdf_links FROM book WHERE book_id = ?', (book_id,)).fetchone()
        if row['pdf_links']:
            info = json.loads(row['pdf_links'])
            if 'size' in info:
                if raw:
                    return info['size']
                return arabize(naturalsize(info['size']))
            if 'alias' in info:
                return self.pdfSize(info['alias'], raw)
        if raw:
            return 0
        return ''

    def sizedpdfs(self, book_id):
        files = self.pdfFiles(book_id)
        self.ensurePdfVersion(files, book_id)
        return (files, self.pdfSize(book_id, True))

    def ensurePdfVersion(self, pdfs, book_id):
        if Across.no_update:
            return
            from dirs import pdfPath, isWritable
            if not isWritable(pdfPath()):
                return True

            def fileVersion(folder_dict, filename):
                filename = filename.lower()
                if filename in folder_dict:
                    return folder_dict[filename]
                return 1

            pdf_online, pdf_ondisk = self.cur.execute(f"SELECT pdf_online, pdf_ondisk FROM book WHERE book_id = {book_id}").fetchone()
            no_defect = True
            if pdfs:
                folder = os.path.dirname(pdfs[0]['file'])
                folder_version = getPdfVersion(folder)
                for pdf in pdfs:
                    if os.path.isfile(pdf['file']):
                        if pdf['version'] > 1:
                            file = os.path.basename(pdf['file'])
                            version = fileVersion(folder_version, file)
                            if version < pdf['version']:
                                no_defect = None
                                try:
                                    os.unlink(pdf['file'])
                                except:
                                    pass

                    else:
                        no_defect = None

            if no_defect:
                if pdf_ondisk != pdf_online:
                    self.cur.execute(f"UPDATE book SET pdf_ondisk = pdf_online WHERE book_id = {book_id}")
                    Across.main_window.checkPdfIcon()
        elif pdf_ondisk == pdf_online:
            self.cur.execute(f"UPDATE book SET pdf_ondisk = NULL WHERE book_id = {book_id}")
            Across.main_window.checkPdfIcon()
            Across.main_window.startBook()
        return no_defect

    def getMeta(self, book_id):
        meta = {}
        row = self.cur.execute('SELECT meta_data, book_name, printed FROM book WHERE book_id = ?', (
         book_id,)).fetchone()
        if row['meta_data']:
            meta = json.loads(row['meta_data'])
        files, _ = self.sizedpdfs(book_id)
        return (meta, files, arabize(row['book_name']), row['printed'])

    def isOnDisk(self, book_id):
        if self.cur.execute('SELECT major_ondisk FROM book WHERE book_id = ?', (book_id,)).fetchone()[0] > 0:
            return True

    def pdfDownloaded(self, book_id, files):
        if self.ensurePdfVersion(files, book_id):
            try:
                self.addToIgnore(5, {book_id}, False)
                UserDb().updateDownloadHistory('pdf', book_id)
                for widget in Across.refresh_set:
                    widget.reinstall()

            except:
                return
                return True

    def pdfVersion(self, book_id):
        return self.cur.execute('SELECT pdf_ondisk FROM book WHERE book_id = ?', (book_id,)).fetchone()[0] or 1

    def pdfLinks(self, book_id):
        return self.cur.execute('SELECT pdf_links FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]

    def pdfFiles(self, book_id, row=None):
        if not row:
            row = self.cur.execute('SELECT pdf_links, book_name, main_author FROM book WHERE book_id = ?', (
             book_id,)).fetchone()
        else:
            pdf_links = row['pdf_links']
            if not pdf_links:
                return []
                pdf_links = json.loads(pdf_links)
                if 'alias' in pdf_links:
                    p_root = p_files = None
                    row = self.cur.execute('SELECT pdf_links, book_name, main_author FROM book WHERE book_id = ?', (
                     pdf_links['alias'],)).fetchone()
                    if 'files' in pdf_links:
                        p_files = pdf_links['files']
                    if 'root' in pdf_links:
                        p_root = pdf_links['root']
                    pdf_links = json.loads(row['pdf_links'])
                    if p_files:
                        pdf_links['files'] = p_files
                    if p_root:
                        pdf_links['root'] = p_root
                if 'files' not in pdf_links:
                    return []
                files = pdf_links['files']
                root = pdf_links['root'] if 'root' in pdf_links else ''
                if 'folder' in pdf_links:
                    base_folder = os.path.join(self.authorFolder(pdf_links['folder'][0]), safeName(pdf_links['folder'][1]))
            else:
                base_folder = os.path.join(self.authorFolder(row['main_author']), safeName(row['book_name']))
        c = 'c' in pdf_links
        pdf = []
        for file in files:
            base = file[file.rfind('/') + 1:] if '/' in file else file
            pdf_dict = {'version':1,  'difference':0,  'c':c}
            part = str(val(base))
            pdf_dict['part'] = '@@' if part == '0' else part
            pieces = base.split('|')
            folder = None
            if len(pieces) > 1:
                base = pieces[0]
                file = file[:file.find('|')]
                for piece in pieces[1:]:
                    if len(piece) == 0:
                        pdf_dict['part'] = '@@'
                    else:
                        start = piece[0]
                        if start == '#':
                            pdf_dict['version'] = int(piece[1:])
                        elif start == '@':
                            pdf_dict['difference'] = int(piece[1:])
                        elif start == 'f':
                            folder_alias = int(piece[1:])
                            row = self.cur.execute('SELECT pdf_links, book_name, main_author FROM book WHERE book_id = ?', (
                             folder_alias,)).fetchone()
                            pdf_links = row['pdf_links']
                            if pdf_links:
                                if 'folder' in pdf_links:
                                    folder = os.path.join(self.authorFolder(pdf_links['folder'][0]), safeName(pdf_links['folder'][1]))
                                else:
                                    folder = os.path.join(self.authorFolder(row['main_author']), safeName(row['book_name']))
                        else:
                            pdf_dict['part'] = piece

            pdf_dict['url'] = file if '://' in file else f"{root}{file}"
            pdf_dict['file'] = os.path.normcase(os.path.join(pdfPath(), folder or base_folder, base))
            pdf.append(pdf_dict)

        if len(files) == 1:
            pdf[0]['part'] = '0'
        return pdf

    def fixGroupFolder(self):
        from cache import renamePdfFolder
        row = self.cur.execute(f"SELECT death_number, author_name from author WHERE author_id={GROUP_AUTHOR_ID}").fetchone()
        old_folder = textAuthorFolder(row['author_name'], row['death_number'])
        new_folder = textAuthorFolder(row['author_name'], 0)
        return renamePdfFolder(old_folder, new_folder)

    def fixPdfFolders(self):
        if not os.path.isdir(pdfPath()):
            return True
        from cache import renamePdfFolder
        error = None
        if not renamePdfFolder('00000 مجموعة من المؤلفين', '0000 المجاميع'):
            error = True
        rows = self.cur.execute('SELECT author_name from author WHERE death_number=99999').fetchall()
        for row in rows:
            old_folder = safeName(row['author_name'])
            new_folder = textAuthorFolder(row['author_name'], 99999)
            if not renamePdfFolder(old_folder, new_folder):
                error = True

        if error:
            return False
        return True

    def authorFolder(self, author_id):
        row = self.cur.execute(f"SELECT death_number, author_name from author WHERE author_id={author_id}").fetchone()
        if author_id == GROUP_AUTHOR_ID:
            return textAuthorFolder(row['author_name'], 0)
        if author_id == UNKNOWN_AUTHOR_ID:
            return textAuthorFolder(row['author_name'], 99998)
        return textAuthorFolder(row['author_name'], row['death_number'])

    def preMajor(self, book_id):
        """ensure NO sqlite db or search engine remnants for the book,
        but not complete delete of book, we need it in favorites and history of opened books, etc
        So, I can not simply use the coming deleteBooks, and should use this function"""
        if not deleteBooks([book_id]):
            return
        if deleteSqlite([book_id]) != [book_id]:
            return
        return Services.clearBookServices([book_id])

    def deleteBooks(self, book_list):
        marked = []
        for book_list in divideList(book_list, 1000):
            id_str = str(book_list)[1:-1]
            try:
                self.cur.execute(f"UPDATE book SET major_ondisk = -1, minor_ondisk = 0 WHERE book_id IN ({id_str})")
            except:
                pass

            self.db.commit()
            marked_subset = listResults(self.cur.execute(f"SELECT book_id FROM book WHERE major_ondisk = -1 AND book_id IN ({id_str})"))
            marked += marked_subset

        if marked:
            Across.main_window.updateCount()
            startTrackedThread(delayed_deletions, name='delayed-deletions')

    def sorter(self, book_id):
        """returns a dictionary of sorting fields"""
        row = self.cur.execute('SELECT book_date, main_author, book_up, group_id, group_order FROM book WHERE book_id = ?', (book_id,)).fetchone()
        if row:
            return {'date':row['book_date'], 
             'author':row['main_author'],  'book_up':row['book_up'],  'group':row['group_id'],  'group_order':row['group_order']}

    def fillBookCache(self, book_id):
        abstract_name, book_type, printed, hidden, authors, pdf = self.cur.execute('SELECT book_name, book_type, printed, hidden, authors, pdf_ondisk FROM book WHERE book_id = ?', (
         book_id,)).fetchone()
        abstract_name = arabize(abstract_name)
        authors = [int(author.strip()) for author in authors.split(',')]
        main_death = None
        author_names = []
        author_abst_names = []
        for author in authors:
            author_death, author_name = self.cur.execute(f"SELECT death_text, author_name FROM author WHERE author_id={author}").fetchone()
            author_death = f" (ت {arabize(author_death)})" if author_death else ''
            if main_death is None:
                main_death = f"{author_death}"
            author_names.append(f"{author_name}{author_death}")
            author_abst_names.append(author_name)

        book_name = f"{abstract_name}{main_death}"
        author_name = joinAuthors(author_names)
        author_abst_names = f"({' - '.join(author_abst_names)})"
        special_icon_path = None
        if book_type == 1:
            if printed == 1:
                icon_path = ':/icons/printed.png'
                special_icon_path = ':/icons/pdf_r.png'
            else:
                icon_path = ':/icons/unprinted.png'
        else:
            if book_type == 2:
                icon_path = ':/icons/mag-printed.png' if printed == 1 else ':/icons/mag-unprinted.png'
            else:
                if book_type == 3:
                    special_icon_path = ':/icons/manuscript.png'
                icons = [
                 'manuscript', 'thesis', 'electronic', 'sound']
                icon_path = f":/icons/{icons[book_type - 3]}.png"
        return (
         book_name, icon_path, hidden, abstract_name, True if pdf else False, author_name, special_icon_path, author_abst_names, printed)

    def bookName(self, book_id):
        return self.cur.execute('SELECT book_name FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]

    def bookAuthors(self, book_id):
        author_list = self.cur.execute('SELECT authors FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]
        return [int(author.strip()) for author in author_list.split(',')]

    def bookDate(self, book_id):
        return self.cur.execute('SELECT book_date FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]

    def bookBetaka(self, book_id, cover, content=None, export=None, report_cover=None, truncated=None, search_info=None, text_only=None):
        from cache import BookCache, CoverCache
        results = self.cur.execute('SELECT book_category, pdf_links FROM book WHERE book_id = ?', (book_id,)).fetchone()
        category, pdf_links = results[0], results[1]
        category = self.cur.execute(f"SELECT category_name FROM category WHERE category_id ={category}").fetchone()[0]
        betaka = content or getElement('bibliography', book_id)
        printed = BookCache.printed(book_id)
        if truncated:
            l = len(betaka)
            if l > 700:
                pos = betaka.rfind('\r', 0, 600)
                betaka = betaka[:pos] + ' . . . '
        else:
            name = BookCache.abstractName(book_id)
            authors = BookCache.authorAbstName(book_id)
            betaka = f"{name}╔{authors}╓{betaka}"
            book_date = self.betakaDate(book_id)
            if book_date:
                betaka = f"{betaka}\nتاريخ النشر بالشاملة: {book_date}"
            else:
                if search_info:
                    betaka = wholeSnippet(betaka, search_info)
                betaka = "<span class='title'>" + betaka.replace('╔', "&nbsp;&nbsp;&nbsp;</span><span class='footnote'>").replace('╓', f"</span><p><span class='title'>القسم:</span> {category}<hr>╦")
                if text_only:
                    value = None
                else:
                    if cover:
                        value = CoverCache.bookCover(book_id, pdf_links)
                    else:
                        value = self.mainScript(book_id) or book_id
                value = getElement('hint', value)
        if report_cover:
            return (
             formatBetaka(betaka, None, value, False, export, printed=printed), CoverCache.bookCover(book_id, pdf_links))
        return formatBetaka(betaka, (False if text_only else cover), value, (False if truncated else True), export, printed=printed)

    def authorBiographyFromBook(self, book_id, truncated=None):
        return self.authorBiography((self.authorId(book_id)), truncated=truncated)

    def authorBiography(self, author_id, truncated=None):
        content = getElement('biography', author_id)
        row = self.cur.execute(f"SELECT author_name, death_text FROM author WHERE author_id ={author_id}").fetchone()
        name = row['author_name']
        if row['death_text']:
            name = f"{name} ({arabize(row['death_text'], True)})"
        biography = f"<span class='title'>{name}</span>"
        if content:
            biography = f"{biography}<hr>\r{content}"
        if truncated:
            l = len(biography)
            if l > 700:
                pos = biography.rfind('\r', 0, 600)
                biography = biography[:pos] + ' . . . \r'
        return formatAuthor(biography)

    def bookCategory(self, book_id):
        return self.cur.execute('SELECT book_category FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]

    def bookCentury(self, book_id):
        year = self.cur.execute('SELECT book_date FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]
        if year < 1:
            return 1
        century = year / 100
        if century != int(century):
            century = int(century) + 1
        return int(century)

    def arrangeCategories(self, categories):
        categories = str(categories)[1:-1]
        return self.cur.execute(f"SELECT category_id, category_name FROM category WHERE category_id in ({categories}) order by category_order").fetchall()

    def inCategory(self, book_id):
        category_id = self.cur.execute('SELECT book_category FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]
        category_name = self.cur.execute('SELECT category_name FROM category WHERE category_id = ?', (category_id,)).fetchone()[0]
        book_list = []
        online_set = set()
        results = self.cur.execute(f"SELECT book_id, major_ondisk FROM book INNER JOIN author ON book.main_author = author.author_id WHERE book_category = {category_id}{ORDER}").fetchall()
        if results:
            for result in results:
                book_list.append(result[0])
                if not result[1]:
                    online_set.add(result[0])

        return (
         category_name, book_list, online_set)

    def mainScript(self, book_id):
        return self.cur.execute('SELECT group_id FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]

    def inScript(self, book_id):
        script_id = self.mainScript(book_id)
        book_list = []
        online_set = set()
        results = self.cur.execute(f"SELECT book_id, major_ondisk FROM book INNER JOIN author ON book.main_author = author.author_id WHERE group_id = {script_id}{ORDER}").fetchall()
        if results:
            for result in results:
                book_list.append(result[0])
                if not result[1]:
                    online_set.add(result[0])

        return (
         book_list, online_set)

    def allAuthorBooks(self, author_id):
        phrase = f"SELECT book.book_id, book.major_ondisk FROM author_book\n                    INNER JOIN book ON author_book.book_id = book.book_id\n                    WHERE author_book.author_id = {author_id}\n                    ORDER BY book.book_date, book.main_author, book.alpha, book.group_order"
        results = self.cur.execute(phrase).fetchall()
        if results:
            book_list = []
            online_set = set()
            for result in results:
                book_id = result[0]
                book_list.append(book_id)
                if result[1] == 0:
                    online_set.add(book_id)

            return (
             book_list, online_set)
        return ([], set())

    def inAuthor(self, book_id):
        result = self.cur.execute('SELECT main_author, authors FROM book WHERE book_id = ?', (book_id,)).fetchone()
        if result:
            author_id = result['main_author']
            authors = result['authors']
            author_dict = {}
            if authors:
                author_list = [int(author.strip()) for author in authors.split(',')]
                results = self.cur.execute(f"SELECT author_id, author_name FROM author WHERE author_id IN ({authors})").fetchall()
                if results:
                    for result in results:
                        author_dict[result['author_id']] = result['author_name']

            else:
                author_dict[author_id] = self.cur.execute(f"SELECT author_name FROM author WHERE author_id = {author_id}").fetchone()[0]
                author_list = [author_id]
            books, online_set = self.allAuthorBooks(author_id)
            return (author_list, author_dict, books, online_set)

    def categoryName(self, category_id):
        return self.cur.execute(f"SELECT category_name FROM category WHERE category_id={category_id}").fetchone()[0]

    def authorId(self, book_id):
        return self.cur.execute('SELECT main_author FROM book WHERE book_id = ?', (book_id,)).fetchone()[0]

    def authorName(self, author_id):
        return self.cur.execute(f"SELECT author_name FROM author WHERE author_id={author_id}").fetchone()[0]

    def updateRedundant(self, progression_signal=None):
        changed = self.redundant_authors.changed_authors
        current_list = list(changed.keys())
        books = set(self.getAuthorsBooks(current_list)) - self.redundant_authors.done_books
        if books:
            condition = f"WHERE book_id IN {stringated(books)}"
            rows = self.cur.execute(f"SELECT book_name, book_id, book_date, main_author, authors FROM book {condition}").fetchall()
            total = len(rows)
            done = 0
            if progression_signal:
                progression_signal.emit({'start': total})
            for row in rows:
                book_id = row['book_id']
                book_dict = {'id':book_id,  'date':row['book_date'],  'name':row['book_name'],  'author':row['main_author']}
                book_dict['author_names'] = self.redundant_authors.bookAuthors(book_id, row['authors'])
                Importer.addBook(book_dict)
                done += 1
                if progression_signal:
                    progression_signal.emit({'value': done})

            Importer.commitBooks()

    def getCategories(self, context, view_items, printed_items):
        phrase = f"SELECT category.category_id, category.category_name, COUNT(*) FROM book\n                    INNER JOIN category ON category.category_id = book.book_category WHERE\n                    {getOnline(context)}{viewType(view_items)}{getHidden(context)}{printedString(printed_items)}\n                    GROUP BY book_category ORDER BY category.category_order"
        results = self.cur.execute(phrase).fetchall()
        if results:
            return [(result[0], result[1], result[2], iso(result[1])) for result in results]
        return []

    def categoryDict(self):
        category_dict = {}
        categories = self.cur.execute('SELECT category_id, category_name FROM category').fetchall()
        for category in categories:
            category_dict[category[0]] = category[1]

        return category_dict

    def getAuthors(self, context, panel=None):
        extra = '' if panel else f" WHERE {getOnline(context)}{getHidden(context)}"
        phrase = f"SELECT author.author_id, COUNT(*) FROM book\n                    INNER JOIN author_book ON author_book.book_id = book.book_id\n                    INNER JOIN author ON author.author_id = author_book.author_id {extra}\n                    GROUP BY author.author_id ORDER BY author.death_number, author.alpha\n                    "
        return {row[0]: row[1] for row in self.cur.execute(phrase)}

    def arrangedCategories(self):
        return listResults(self.cur.execute('SELECT category_id FROM category ORDER BY category_order'))

    def arrangedAuthors(self):
        phrase = 'SELECT author.author_id FROM book\n                    INNER JOIN author_book ON author_book.book_id = book.book_id\n                    INNER JOIN author ON author.author_id = author_book.author_id \n                    GROUP BY author.author_id ORDER BY author.death_number, author.alpha'
        return listResults(self.cur.execute(phrase))

    def getAuthorBooks(self, author_id, context):
        phrase = f"SELECT book.book_id FROM author_book\n                    INNER JOIN book ON author_book.book_id = book.book_id\n                    WHERE author_book.author_id = {author_id} AND {getOnline(context)}{getHidden(context)}\n                    ORDER BY book.book_date, book.main_author, book.alpha, book.group_order"
        return listResults(self.cur.execute(phrase))

    def getAuthorsBooks(self, author_list):
        """No need to filter or order. It will pass through a limited ordered set after that"""
        phrase = f"SELECT book.book_id FROM author_book\n                    INNER JOIN book ON author_book.book_id = book.book_id\n                    WHERE author_book.author_id IN {stringated(author_list)}"
        return listResults(self.cur.execute(phrase))

    def getAuthorBooksSet(self, author_list, context):
        id_str = str(author_list)[1:-1]
        phrase = f"SELECT book.book_id FROM author_book\n                    INNER JOIN book ON author_book.book_id = book.book_id\n                    WHERE author_book.author_id In ({id_str}) AND {getOnline(context)}{getHidden(context)}"
        book_set = set(listResults(self.cur.execute(phrase)))
        if context == 2:
            phrase = f"SELECT book.book_id FROM coauthor_book\n                        INNER JOIN book ON coauthor_book.book_id = book.book_id\n                        WHERE coauthor_book.author_id In ({id_str}) AND {getOnline(context)}{getHidden(context)}"
            co_book_set = set(listResults(self.cur.execute(phrase)))
            book_set = book_set.union(co_book_set)
        return book_set

    def getBooks(self, category_id, context, view_type, printed_items):
        phrase = f"SELECT book_id FROM book \n                     INNER JOIN author ON book.main_author = author.author_id\n                     WHERE book_category = {category_id} AND\n                  {getOnline(context)}{viewType(view_type)}{getHidden(context)}{printedString(printed_items)}\n                   {ORDER}"
        return listResults(self.cur.execute(phrase))

    def getBooksSet(self, category_id, context, view_type, printed_items):
        phrase = f"SELECT book_id FROM book WHERE book_category = {category_id} AND\n                  {getOnline(context)}{viewType(view_type)}{getHidden(context)}{printedString(printed_items)}"
        return listResults(self.cur.execute(phrase))

    def getPeriodBooks(self, llimit, ulimit):
        date_set = set(listResults(self.cur.execute(f"SELECT book_id from book WHERE book_date BETWEEN {llimit} AND {ulimit}")))
        authors_set = self.getAuthorBooksSet((listResults(self.cur.execute(f"SELECT author_id from author WHERE death_number BETWEEN {llimit} AND {ulimit}"))), context=2)
        return date_set.union(authors_set)

    def allowedBooks(self, context):
        phrase = f"SELECT book_id FROM book\n        INNER JOIN author ON book.main_author = author.author_id  \n        WHERE {getOnline(context)}{getHidden(context)}{ORDER}"
        return listResults(self.cur.execute(phrase))

    def allowedExtended(self, context):
        return (
         self.allowedBooks(context), self.newSet(context))

    def allBooks(self):
        return listResults(self.cur.execute(f"SELECT book_id FROM book INNER JOIN author ON book.main_author = author.author_id{ORDER}"))

    def offlineBooks(self):
        return listResults(self.cur.execute(f"SELECT book_id FROM book INNER JOIN author ON book.main_author = author.author_id WHERE book.major_ondisk > 0{ORDER}"))

    def bookSet(self):
        return set(listResults(self.cur.execute('SELECT book_id FROM book')))

    def booksPanel(self):
        return (
         self.allBooks(), set(self.allowedBooks(context=4)))

    def getOfflineBooksNumber(self):
        return self.cur.execute('SELECT COUNT(*) FROM book WHERE major_ondisk <> 0').fetchone()[0]

    def booksAuthorsCount(self):
        books = self.cur.execute('SELECT COUNT(*) FROM book').fetchone()[0]
        authors = self.cur.execute('SELECT COUNT(DISTINCT author_id) FROM author_book').fetchone()[0]
        return (books, authors)

    def getVersion(self, key):
        result = self.cur.execute('SELECT value FROM version WHERE key = ?', (key,)).fetchone()
        if result:
            if result[0]:
                return result[0]
            return 0
        return 0

    def getServicesVersion(self):
        services = {}
        for key in ('Q', 'S1', 'S2'):
            services[key] = self.getVersion(key)

        return services

    def setVersion(self, key, value):
        try:
            self.cur.execute('INSERT OR REPLACE INTO version (key, value) VALUES(?, ?)', (key, value))
            self.db.commit()
            self._alpha_authors = set()
            self._alpha_books = set()
        except:
            return
            return True

    def setBookVersion(self, book_id, major, minor):
        try:
            self.cur.execute('UPDATE book SET major_ondisk = ?, minor_ondisk = ? WHERE book_id = ?', (
             major, minor, book_id))
            if major > 0:
                self.addToIgnore(4, {book_id}, False)
            self.db.commit()
        except:
            return
            return True

    def getBookVersion(self, book_id):
        result = self.cur.execute('SELECT major_ondisk, minor_ondisk FROM book WHERE book_id = ?', (
         book_id,)).fetchone()
        if result:
            return (
             result['major_ondisk'], result['minor_ondisk'])

    def getBookVersions(self, book_id):
        """ondisk + online versions in one row; master.db already knows what is
        current online, so a major (full book) download needs no api call"""
        result = self.cur.execute('SELECT major_ondisk, minor_ondisk, major_online, minor_online FROM book WHERE book_id = ?', (
         book_id,)).fetchone()
        if result:
            return (
             result['major_ondisk'], result['minor_ondisk'], result['major_online'], result['minor_online'])
        return (None, None, None, None)

    def getServiceVersion(self):
        return self.cur.execute('SELECT service FROM version LIMIT 1').fetchone()[0]

    def subBooks(self, book_id):
        meta = self.cur.execute(f"SELECT meta_data FROM book WHERE book_id = {book_id}").fetchone()[0]
        if meta:
            meta = json.loads(meta)
            if 'sub_books' in meta:
                return meta['sub_books']
        return []

    def betakaDate(self, book_id):
        meta = self.cur.execute(f"SELECT meta_data FROM book WHERE book_id = {book_id}").fetchone()[0]
        if meta:
            meta = json.loads(meta)
            if 'date' in meta:
                return displayDate(meta['date'])

    def staleSubBooks(self, book_id):
        sub_books = self.subBooks(book_id)
        if sub_books:
            sub_str = str(sub_books)[1:-1]
            results = listResults(self.cur.execute(f"SELECT book_id FROM book WHERE book_id IN ({sub_str})\n             AND (major_online > major_ondisk OR minor_online > minor_ondisk)"))
            if results:
                return results
        return [
         book_id]

    def extendSet(self, book_set):
        meta = set(listResults(self.cur.execute('SELECT book_id FROM book WHERE meta_data IS NOT NULL')))
        if meta:
            target = book_set.intersection(meta)
            for book_id in target:
                for sub_book in self.subBooks(book_id):
                    book_set.add(sub_book)

        return book_set

    def siblings(self, book_list):
        children_dict = {}
        parents_dict = defaultdict(set)
        book_set = set(book_list)
        results = self.cur.execute('SELECT book_id, parent FROM book WHERE parent IS NOT NULL').fetchall()
        for result in results:
            children_dict[result['book_id']] = result['parent']
            parents_dict[result['parent']].add(result['book_id'])

        parents = []
        children = []
        for book_id in book_list:
            if book_id in children_dict:
                if children_dict[book_id] not in book_set:
                    children.append(book_id)
            if book_id in parents_dict:
                children_included = True
                for child in parents_dict[book_id]:
                    if child not in book_set:
                        children_included = False
                        break

                children_included or parents.append(book_id)

        return (
         parents, children)

    def newSet(self, context):
        if context == 4:
            return set(listResults(self.cur.execute('SELECT book_id FROM book WHERE major_ondisk = 0')))
        if context == 5:
            return set(listResults(self.cur.execute('SELECT book_id FROM book WHERE pdf_ondisk = 0 OR pdf_ondisk IS NULL')))
        return set()

    def hasNewPdf(self):
        rows = self.cur.execute(f"SELECT 1 FROM book WHERE {getOnline(5)} LIMIT 1").fetchone()
        if rows:
            return True
        return False

    def hasNewBooks(self):
        rows = self.cur.execute(f"SELECT 1 FROM book WHERE {getOnline(4)} LIMIT 1").fetchone()
        if rows:
            return True

    def newCount(self, context):
        from cache import BookCache
        count = self.cur.execute(f"SELECT COUNT(*) FROM book WHERE {getOnline(context)}").fetchone()[0]
        if count:
            ignored_count = self.cur.execute(f"SELECT COUNT(*) FROM book WHERE {getOnline(context)} AND hidden in {stringated(BookCache.viewSet(context, False))}").fetchone()[0]
            return (count, ignored_count)
        return (0, 0)

    def newBookCount(self, context):
        from cache import BookCache

        def bookslist(results, new_book_set, book_count):
            for book in results:
                if book['book_id'] in new_book_set:
                    list_results.append(f"☆ {book['book_name']}")
                else:
                    list_results.append(book['book_name'])

            if book_count > 10:
                list_results.append('...')
            return list_results

        list_results = []
        count, ignored_count = self.newCount(context)
        if count:
            new_set = self.newSet(context)
            if count == ignored_count:
                results = self.cur.execute(f"SELECT book_id, book_name FROM book INNER JOIN author ON book.main_author = author.author_id WHERE {getOnline(context)} AND hidden in {stringated(BookCache.viewSet(context, False))}{ORDER} LIMIT 10").fetchall()
                return (ignored_count, True, bookslist(results, new_set, ignored_count))
            count -= ignored_count
            results = self.cur.execute(f"SELECT book_id, book_name FROM book INNER JOIN author ON book.main_author = author.author_id WHERE {getOnline(context)} AND hidden in {stringated(BookCache.viewSet(context, True))}{ORDER} LIMIT 10").fetchall()
            return (count, False, bookslist(results, new_set, count))
        return (
         0, False, [])

    def pendingDelets(self):
        if self.cur.execute('SELECT 1 FROM book WHERE major_ondisk = -1 LIMIT 1').fetchone():
            return True

    def autoBooks(self, context):
        new = []
        value = Settings.getValue('auto_download_books') if context == 4 else Settings.getValue('auto_download_pdf')
        if value:
            new = self.allowedBooks(context=context)
        return new

    def pdfList(self):
        return listResults(self.cur.execute(f"SELECT book_id FROM book INNER JOIN author ON book.main_author = author.author_id WHERE major_ondisk > 0 AND\n             pdf_ondisk IS NOT NULL AND pdf_online > pdf_ondisk{ORDER}"))

    def onLinePdf(self):
        results = self.cur.execute(f"SELECT book_id, pdf_ondisk FROM book INNER JOIN author ON book.main_author = author.author_id WHERE pdf_online IS NOT NULL{ORDER}").fetchall()
        return [(result[0], result[1]) for result in results]

    def onLinePdfFiles(self):
        files = []
        rows = self.cur.execute('SELECT book_id, pdf_links, book_name, main_author, pdf_ondisk FROM book WHERE pdf_online IS NOT NULL').fetchall()
        for row in rows:
            book_id = row['book_id']
            pdf_files = self.pdfFiles(book_id, row)
            book_files = [(item['file'], item['version']) for item in pdf_files]
            files.append([book_id, book_files])

        return files

    def updatePdfState(self, present_books, defective_books):
        if present_books:
            self.cur.execute(f"UPDATE book SET pdf_ondisk = pdf_online WHERE book_id IN {stringated(present_books)}")
        if defective_books:
            self.cur.execute(f"UPDATE book SET pdf_ondisk = NULL WHERE book_id IN {stringated(defective_books)}")

    def deletePdf(self, book_list):
        id_str = str(book_list)[1:-1]
        id_list = listResults(self.cur.execute(f"SELECT book_id FROM book WHERE book_id IN ({id_str}) AND pdf_ondisk IS NOT NULL"))
        if id_list:
            for book_id in id_list:
                pdf_files = self.pdfFiles(book_id)
                for pdf in pdf_files:
                    try:
                        os.unlink(pdf['file'])
                    except:
                        pass

                try:
                    book_folder = os.path.dirname(pdf['file'])
                    author_folder = os.path.dirname(book_folder)
                    os.rmdir(book_folder)
                    os.rmdir(author_folder)
                except:
                    pass

            del_set = set(id_list)
            for book_id in id_list:
                book_kept = True
                pdf_files = self.pdfFiles(book_id)
                for pdf in pdf_files:
                    if not os.path.isfile(pdf['file']):
                        book_kept = False
                        break

                if book_kept:
                    del_set.discard(book_id)

            if del_set:
                id_str = stringated(del_set)
                self.cur.execute(f"UPDATE book SET pdf_ondisk = NULL WHERE book_id IN {id_str}")
                UserDb().deletePdfs(id_str)

    def coverList(self):
        cover_list = []
        covers = self.cur.execute('SELECT book_id, cover_online FROM book WHERE cover_online > cover_ondisk\n              Or (cover_online is NOT NULL AND cover_ondisk IS NULL)').fetchall()
        if covers:
            cover_list = [(cover['book_id'], cover['cover_online']) for cover in covers if cover['cover_online'] != 0]
        return cover_list

    def coverDone(self, id_ver):
        self.cur.execute('UPDATE book SET cover_ondisk = ? WHERE book_id = ?', (id_ver[1], id_ver[0]))

    def evacuateCovers(self):
        self.cur.execute('UPDATE book SET cover_ondisk = NULL')

    def importMaster(self, extract_path, version, progression_signal):
        full_path = {}
        for file in os.listdir(extract_path):
            full_path[file] = os.path.join(extract_path, file)

        self._importsuccess = True
        self.redundant_authors = RedundantAuthors(self)
        self.startExecution()
        if 'category.sqlite' in full_path:
            self._importcategory(full_path['category.sqlite'], progression_signal)
        if self._importsuccess:
            if 'author.sqlite' in full_path:
                self._importauthor(full_path['author.sqlite'], progression_signal)
            if self._importsuccess:
                if 'book.sqlite' in full_path:
                    self._importbook(full_path['book.sqlite'], progression_signal)
                if self._alpha_authors or self._alpha_books:
                    if not self.alpha():
                        self._importsuccess = False
                if self._importsuccess:
                    self.execute()
                    self.updateRedundant()
                    return self.setVersion('master', version)

    def _importcategory(self, file_path, progression_signal):
        db, cur = connectPath(file_path)
        try:
            try:
                progression_signal.emit(0, 0)
                new, updated = segregate(cur, self.cur, 'category')
                total = len(new) + len(updated)
                read = 0
                if new:
                    for this_id in new:
                        row = cur.execute(f"SELECT [order], [name] FROM category WHERE id = {this_id}").fetchone()
                        new_record = {'category_id':this_id,  'category_name':row['name'],  'category_order':row['order']}
                        self.addToExecution(script_record('category', new_record))
                        read += 1
                        progression_signal.emit(read, total)

                if updated:
                    for this_id in updated:
                        row = cur.execute(f"SELECT [order], [name] FROM category WHERE id = {this_id}").fetchone()
                        updated_string = ''
                        values = []
                        if row['order'] != '#':
                            updated_string += ', category_order = ?'
                            values.append(row['order'])
                        if row['name'] != '#':
                            updated_string += ', category_name = ?'
                            values.append(row['name'])
                        if updated_string:
                            values.append(this_id)
                            self.addToExecution([
                             f"UPDATE category SET {updated_string[2:]} WHERE category_id = ?", values])
                        read += 1
                        progression_signal.emit(read, total)

            except:
                self._importsuccess = False

        finally:
            cur.close()
            db.close()

    def _importauthor(self, file_path, progression_signal):
        from cache import AuthorCache, AuthorNames
        self._alpha_authors = set()
        db, cur = connectPath(file_path)
        try:
            try:
                progression_signal.emit(0, 0)
                new, updated = segregate(cur, self.cur, 'author')
                total = len(new) + len(updated)
                read = 0
                if new:
                    for this_id in new:
                        self._alpha_authors.add(this_id)
                        AuthorCache.clear(this_id)
                        row = cur.execute(f"SELECT [name], [biography], [death_text], [death_number] FROM author WHERE id = {this_id}").fetchone()
                        AuthorNames.putAuthorFolder(this_id, row['name'], row['death_number'])
                        new_record = {'author_id':this_id,  'author_name':row['name'],  'death_text':row['death_text'],  'death_number':row['death_number']}
                        self.addToExecution(script_record('author', new_record))
                        author_dict = {'id':this_id, 
                         'date':int(row['death_number']),  'name':row['name']}
                        if row['biography']:
                            author_dict['biography'] = row['biography']
                        Importer.addAuthor(author_dict)
                        read += 1
                        self.redundant_authors.addStored(this_id, row['name'])
                        progression_signal.emit(read, total)

                if updated:
                    for this_id in updated:
                        AuthorCache.clear(this_id)
                        row = cur.execute(f"SELECT [name], [biography], [death_text], [death_number] FROM author WHERE id = {this_id}").fetchone()
                        updated_string = ''
                        values = []
                        author_dict = {}
                        rename_author = None
                        if row['death_text'] != '#':
                            updated_string += ', [death_text] = ?'
                            values.append(row['death_text'])
                        if row['biography'] != '#':
                            author_dict['biography'] = row['biography']
                        if row['name'] != '#':
                            self._alpha_authors.add(this_id)
                            updated_string += ', [author_name] = ?'
                            values.append(row['name'])
                            author_dict['name'] = row['name']
                            rename_author = True
                            self.redundant_authors.addChanged(this_id, row['name'])
                        if row['death_number'] != '#':
                            self._alpha_authors.add(this_id)
                            updated_string += ', [death_number] = ?'
                            death = int(row['death_number'])
                            values.append(death)
                            author_dict['date'] = death
                            rename_author = True
                        if rename_author:
                            AuthorNames.setAuthorFolder(this_id, row['name'], row['death_number'])
                        if author_dict:
                            if 'date' not in author_dict or 'name' not in author_dict:
                                res = self.cur.execute(f"SELECT [author_name], [death_number] FROM author WHERE author_id = {this_id}").fetchone()
                                if 'author' not in author_dict:
                                    author_dict['db_name'] = res['author_name']
                                if 'date' not in author_dict:
                                    author_dict['db_date'] = res['death_number']
                            author_dict['id'] = this_id
                        if updated_string:
                            sql = f"update author set {updated_string[1:]} WHERE author_id = {this_id}"
                            self.addToExecution([sql, values])
                        if author_dict:
                            Importer.addAuthor(author_dict)
                        read += 1
                        progression_signal.emit(read, total)

                Importer.commitAuthors()
            except:
                self._importsuccess = False

        finally:
            cur.close()
            db.close()

    def setBookAuthors(self, book_id, comma_separated_list):
        if comma_separated_list:
            authors = [int(author.strip()) for author in comma_separated_list.split(',')]
            self.redundant_authors.addBook(book_id, authors)
            return self.setBaseAuthors(book_id, 'author_book', authors)

    def setBaseAuthors(self, book_id, table, author_list):
        if author_list:
            new_authors = set(author_list)
            old_authors = set()
            results = self.cur.execute(f"SELECT author_id FROM {table} WHERE book_id = {book_id}").fetchall()
            if results:
                old_authors = set([result[0] for result in results])
            removed_authors = old_authors - new_authors
            added_authors = new_authors - old_authors
            if removed_authors:
                id_str = str(removed_authors).replace('{', '(').replace('}', ')')
                self.cur.execute(f"DELETE FROM {table} WHERE book_id = {book_id} AND author_id IN {id_str}")
            if added_authors:
                for author_id in added_authors:
                    self.cur.execute(f"INSERT INTO {table} (author_id, book_id) VALUES (?,?)", (author_id, book_id))

            self.db.commit()
            return author_list[0]

    def setMetaData(self, book_id, meta_data_field):
        meta = {}
        if meta_data_field:
            try:
                meta = json.loads(meta_data_field)
            except:
                pass

        if not meta:
            meta = {}
        if 'sub_books' in meta:
            sub_set = str(meta['sub_books'])[1:-1]
            self.cur.execute(f"UPDATE book set parent = {book_id} WHERE book_id IN ({sub_set})")
        group_id = meta['group'] if 'group' in meta else None
        group_order = meta['group_order'] if 'group_order' in meta else None
        book_up = meta['book_up'] if 'book_up' in meta else None
        min_ver = meta['min_ver'] if 'min_ver' in meta else None
        if 'coauthor' in meta:
            self.setBaseAuthors(book_id, 'coauthor_book', meta['coauthor'])
        return (
         book_up, group_id, group_order, min_ver)

    def _importbook(self, file_path, progression_signal):
        from cache import BookCache, AuthorNames, Hints
        self._alpha_books = set()
        db, cur = connectPath(file_path)
        try:
            try:
                deletions = []
                progression_signal.emit(0, 0)
                new, updated = segregate(cur, self.cur, 'book')
                total = len(new) + len(updated)
                read = 0
                any_hint = False
                if new:
                    for this_id in new:
                        self._alpha_books.add(this_id)
                        BookCache.clear(this_id)
                        row = cur.execute(f"SELECT [name], [category], [type], [date], [author], [hint], [printed], [major_release], [minor_release], [bibliography], [pdf_links], [metadata] FROM book WHERE id = {this_id}").fetchone()
                        new_record = {'book_id':this_id,  'book_name':row['name'],  'book_category':row['category']}
                        book_dict = {'id':this_id,  'date':int(row['date']),  'name':row['name']}
                        new_record['book_type'] = row['type']
                        new_record['meta_data'] = row['metadata']
                        new_record['pdf_links'] = row['pdf_links']
                        new_record['book_date'] = row['date']
                        new_record['printed'] = row['printed']
                        new_record['major_online'] = row['major_release']
                        new_record['minor_online'] = row['minor_release']
                        new_record['major_ondisk'] = 0
                        new_record['minor_ondisk'] = 0
                        new_record['hidden'] = 0
                        author = row['author']
                        new_record['authors'] = author
                        new_record['main_author'] = self.setBookAuthors(this_id, author)
                        book_up, group, group_order, _ = self.setMetaData(this_id, row['metadata'])
                        if book_up:
                            new_record['book_up'] = book_up
                            book_dict['book_up'] = book_up
                        if group:
                            new_record['group_id'] = group
                            book_dict['group'] = group
                        if group_order:
                            new_record['group_order'] = group_order
                            book_dict['group_order'] = group_order
                        if row['pdf_links']:
                            new_record['pdf_online'], new_record['cover_online'] = setPdf(row['pdf_links'])
                        self.addToExecution(script_record('book', new_record))
                        book_dict['author_names'] = self.redundant_authors.bookAuthors(this_id)
                        book_dict['author'] = new_record['main_author']
                        if row['bibliography']:
                            book_dict['bibliography'] = row['bibliography']
                        if row['hint']:
                            book_dict['hint'] = row['hint']
                            any_hint = True
                        Importer.addBook(book_dict)
                        self.redundant_authors.done_books.add(this_id)
                        read += 1
                        progression_signal.emit(read, total)

                if updated:
                    for this_id in updated:
                        BookCache.clear(this_id)
                        row = cur.execute(f"SELECT [name], [category], [type], [date], [author], [printed], [major_release], [minor_release], [bibliography], [hint], [pdf_links], [metadata] FROM book WHERE id = {this_id}").fetchone()
                        updated_string = ''
                        values = []
                        book_dict = {}
                        rename_book = None
                        if row['category'] != '#':
                            updated_string += ', [book_category] = ?'
                            values.append(row['category'])
                        if row['type'] != '#':
                            updated_string += ', [book_type] = ?'
                            values.append(row['type'])
                        if row['printed'] != '#':
                            updated_string += ', [printed] = ?'
                            values.append(row['printed'])
                        if row['major_release'] != '#':
                            updated_string += ', [major_online] = ?'
                            values.append(row['major_release'])
                        if row['minor_release'] != '#':
                            updated_string += ', [minor_online] = ?'
                            values.append(row['minor_release'])
                        if row['name'] != '#':
                            self._alpha_books.add(this_id)
                            updated_string += ', [book_name] = ?'
                            values.append(row['name'])
                            book_dict['name'] = row['name']
                            rename_book = True
                        if row['bibliography'] != '#':
                            book_dict['bibliography'] = row['bibliography']
                        if row['hint'] != '#':
                            book_dict['hint'] = row['hint']
                            any_hint = True
                        if row['pdf_links'] != '#':
                            updated_string += ', [pdf_links] = ?, [pdf_online] = ?, [cover_online] = ?'
                            online_pdf, online_cover = setPdf(row['pdf_links'], this_id)
                            values += [row['pdf_links'], online_pdf, online_cover]
                        if row['date'] != '#':
                            self._alpha_books.add(this_id)
                            updated_string += ', [book_date] = ?'
                            values.append(row['date'])
                            i_date = int(row['date'])
                            book_dict['date'] = i_date
                        if row['author'] != '#':
                            self._alpha_books.add(this_id)
                            main_author = self.setBookAuthors(this_id, row['author'])
                            updated_string += ', [main_author] = ?, [authors] = ?'
                            values += [main_author, row['author']]
                            book_dict['author'] = main_author
                            book_dict['author_names'] = self.redundant_authors.bookAuthors(this_id)
                            rename_book = True
                        if rename_book:
                            AuthorNames.renameBook(this_id, row['author'], row['name'])
                        if row['metadata'] != '#':
                            meta = row['metadata']
                            updated_string += ', [meta_data] = ?'
                            values.append(meta)
                            sorter = self.sorter(this_id)
                            book_up, group, group_order, min_ver = self.setMetaData(this_id, meta)
                            if book_up != sorter['book_up']:
                                updated_string += ', [book_up] = ?'
                                values.append(book_up)
                                book_dict['book_up'] = book_up
                            if group != sorter['group']:
                                updated_string += ', [group_id] = ?'
                                values.append(group)
                                book_dict['group'] = group
                            if group_order != sorter['group_order']:
                                updated_string += ', [group_order] = ?'
                                values.append(group_order)
                                book_dict['group_order'] = group_order
                            if min_ver:
                                current_version, _ = self.getBookVersion(this_id)
                                if current_version < min_ver:
                                    deletions.append(this_id)
                        if book_dict:
                            book_dict['id'] = this_id
                            result = self.cur.execute(f"SELECT [book_name], [book_date], [main_author], [book_up], [group_id], [group_order], [authors] FROM book WHERE book_id = {this_id}").fetchone()
                            if 'name' not in book_dict:
                                book_dict['db_name'] = result['book_name']
                            if 'date' not in book_dict:
                                book_dict['db_date'] = result['book_date']
                            if 'author' not in book_dict:
                                book_dict['db_author'] = result['main_author']
                            if 'book_up' not in book_dict:
                                book_dict['db_book_up'] = result['book_up']
                            if 'group' not in book_dict:
                                book_dict['db_group'] = result['group_id']
                            if 'group_order' not in book_dict:
                                book_dict['db_group_order'] = result['group_order']
                            if self.redundant_authors.isAuthorNamesChanged(result['authors']):
                                book_dict['author_names'] = self.redundant_authors.bookAuthors(this_id)
                            if 'author_names' not in book_dict:
                                book_dict['db_author_names'] = self.redundant_authors.bookAuthors(this_id)
                        if updated_string:
                            sql = f"update book set {updated_string[1:]} WHERE book_id = {this_id}"
                            self.addToExecution([sql, values])
                        if book_dict:
                            Importer.addBook(book_dict)
                            self.redundant_authors.done_books.add(this_id)
                        read += 1
                        progression_signal.emit(read, total)

                if deletions:
                    self.deleteBooks(deletions)
                Importer.commitBooks()
                if any_hint:
                    Hints.reCache()
            except Exception:
                self._importsuccess = False

        finally:
            cur.close()
            db.close()


def _setBooksMissing(book_ids):
    book_ids = sorted(set([int(book_id) for book_id in book_ids if book_id]))
    if not book_ids:
        return True
    core_db = CoreDb()
    try:
        core_db.cur.execute(f"UPDATE book SET major_ondisk = 0, minor_ondisk = 0 WHERE book_id IN {stringated(book_ids)}")
        core_db.db.commit()
    except Exception:
        traceback.print_exc()
        return
    else:
        try:
            Across.main_window.updateCount()
        except:
            pass

        return True


def finalizeBookDeletion(book_ids, clear_user=False):
    book_ids = sorted(set([int(book_id) for book_id in book_ids if book_id]))
    if not book_ids:
        return True
    if clear_user:
        if not UserDb().deleteBooks(book_ids):
            return
    else:
        if not deleteBooks(book_ids):
            return
        deleted = deleteSqlite(book_ids)
        if deleted != book_ids:
            return
        return Services.clearBookServices(book_ids) or None
    return _setBooksMissing(book_ids)


def delayed_deletions():
    """Files in CoreDb and services are marked deleted already"""
    core_db = CoreDb()
    marked = listResults(core_db.cur.execute('SELECT book_id FROM book WHERE major_ondisk = -1'))
    if not marked:
        return True
    else:
        finalizeBookDeletion(marked, clear_user=True)
        marked = listResults(core_db.cur.execute('SELECT book_id FROM book WHERE major_ondisk = -1'))
        return marked or True


def segregate(patch_cursor, local_cursor, table):
    local = set()
    patch = set()
    id_field = 'id' if table in frozenset({'page', 'title'}) else f"{table}_id"
    results = local_cursor.execute(f"SELECT {id_field} FROM {table}").fetchall()
    if results:
        local = set([result[0] for result in results])
    results = patch_cursor.execute(f"SELECT id FROM {table}").fetchall()
    if results:
        patch = set([result[0] for result in results])
    new = patch - local
    updated = local.intersection(patch)
    return (new, updated)


def insertRecord(cursor, table_name, dict_data):
    attrib_names = ', '.join(dict_data.keys())
    attrib_values = ', '.join('?' * len(dict_data.keys()))
    sql = f"INSERT OR IGNORE INTO {table_name} ({attrib_names}) VALUES ({attrib_values})"
    cursor.execute(sql, list(dict_data.values()))


def script_record(table_name, dict_data):
    attrib_names = ', '.join(dict_data.keys())
    attrib_values = ', '.join('?' * len(dict_data.keys()))
    sql = f"INSERT OR IGNORE INTO {table_name} ({attrib_names}) VALUES ({attrib_values})"
    return [sql, list(dict_data.values())]


def connectPath(file_path, existent_only=None):
    if existent_only:
        if not os.path.isfile(file_path):
            return (None, None)
    os.makedirs((os.path.dirname(file_path)), exist_ok=True)
    db = sqlite3.connect(file_path, isolation_level=None, check_same_thread=False)
    db.execute('PRAGMA journal_mode = MEMORY;')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    return (db, cursor)


def connectBook(book_id):
    book_path = bookPath(book_id)
    db, cur = connectPath(book_path, existent_only=True)
    if not cur:
        return (None, None)
    if not tableExists(cur, 'page'):
        cur.execute('CREATE TABLE page (id INTEGER PRIMARY KEY, part TEXT, page INTEGER, number INTEGER, services TEXT)')
        cur.execute('CREATE INDEX part on page (part)')
        cur.execute('CREATE INDEX page_id on page (page)')
        cur.execute('CREATE INDEX number on page (number)')
    if not tableExists(cur, 'title'):
        cur.execute('CREATE TABLE title (id INTEGER PRIMARY KEY, page INTEGER, parent INTEGER)')
        cur.execute('CREATE INDEX parent on title (parent)')
        cur.execute('CREATE INDEX correspond on title (page)')
    return (db, cur)


def updateService(service_name, file_path):
    try:
        db, cur = connectPath(file_path, True)
        if not cur:
            return
        db.close()
        service_path = serviceDbPath(service_name)
        if os.path.isfile(service_path):
            try:
                os.unlink(service_path)
            except:
                pass

            if os.path.isfile(service_path):
                return
        try:
            os.renames(file_path, service_path)
        except:
            return
        else:
            if os.path.isfile(service_path):
                return True
    except:
        return


def tableExists(cur, table_name):
    cur.execute('SELECT COUNT(*) FROM sqlite_master WHERE type = "table" AND name = ?', (table_name,))
    return cur.fetchone()[0] == 1


def gapInColumn(cur, table_name, column_name, excluded=None):
    if not excluded:
        excluded = set()
    else:
        rows = cur.execute(f"SELECT {column_name} from {table_name} ORDER BY {column_name}").fetchall()
        return rows or 1
    a = 1
    for row in rows:
        if row[0] != a:
            if a not in excluded:
                return a
        a += 1

    while a in excluded:
        a += 1

    return a


def nextInColumn(cur, table_name, column_name, excluded=None):
    if not excluded:
        excluded = set()
    else:
        row = cur.execute(f"SELECT MAX({column_name}) FROM {table_name}").fetchone()
        if row[0]:
            a = row[0] + 1
        else:
            a = 1
    while a in excluded:
        a += 1

    return a


def swapValues(cur, table_name, id_column, swapped_column, first_id, second_id):
    first_value = cur.execute(f"SELECT {swapped_column} FROM {table_name} WHERE {id_column} = {first_id}").fetchone()[0]
    second_value = cur.execute(f"SELECT {swapped_column} FROM {table_name} WHERE {id_column} = {second_id}").fetchone()[0]
    cur.execute(f"UPDATE {table_name} SET {swapped_column} = ? WHERE {id_column} = ?", (first_value, second_id))
    cur.execute(f"UPDATE {table_name} SET {swapped_column} = ? WHERE {id_column} = ?", (second_value, first_id))


def getTree(cur, table_name, id_column, parent_column, id_list):
    full = id_list
    for field_id in id_list:
        rows = cur.execute(f"SELECT {id_column} FROM {table_name} WHERE {parent_column} = {field_id}").fetchall()
        if rows:
            full += getTree(cur, table_name, id_column, parent_column, [row[0] for row in rows])

    return full


def getHidden(context):
    from cache import BookCache
    if context in frozenset({1, 3}):
        return ''
    return f" AND hidden in {stringated(BookCache.viewSet(context, True))}"


def stringated(iter):
    return str(iter).translate(Across.stringated_table)


def hiddenToNumber(search_exclude, update_exclude, pdf_exclude, mak_exclude):
    collision = 0
    if search_exclude:
        collision += 1
    if update_exclude:
        collision += 2
    if pdf_exclude:
        collision += 4
    if mak_exclude:
        collision += 8
    return collision


def numberToHidden(number):
    search_exclude = 0
    update_exclude = 0
    pdf_exclude = 0
    mak_exclude = 0
    if number >= 8:
        number -= 8
        mak_exclude = 1
    if number >= 4:
        number -= 4
        pdf_exclude = 1
    if number >= 2:
        number -= 2
        update_exclude = 1
    if number >= 1:
        search_exclude = 1
    return [search_exclude, update_exclude, pdf_exclude, mak_exclude]


def getOnline(context):
    if context == 5:
        return ' (major_ondisk > 0 AND ((pdf_ondisk IS NULL AND pdf_online IS NOT NULL) OR (pdf_ondisk IS NOT NULL AND pdf_online > pdf_ondisk)))'
    if context == 4:
        return ' major_online > major_ondisk'
    return ' major_ondisk > 0'


def printedString(printed_items):
    printed_items.add(3)
    return ' AND printed IN (' + ', '.join([f"{i}" for i in printed_items]) + ')'


def viewType(view_items):
    return ' AND book_type IN (' + ', '.join([f"{i}" for i in view_items]) + ')'


def listResults(results):
    if results:
        return [result[0] for result in results]
    return []


def deleteSqlite(books):
    return [book_id for book_id in books if isDeleted(book_id)]


def isDeleted(book_id):
    book_path = bookPath(book_id)
    if not os.path.isfile(book_path):
        return True
    else:
        try:
            os.unlink(book_path)
        except:
            pass

        return os.path.isfile(book_path) or True


def getDbVersion(cur):
    try:
        return cur.execute('SELECT value FROM db_ver').fetchone()[0]
    except:
        return 0


def setDbVersion(cur, value):
    if tableExists(cur, 'db_ver'):
        cur.execute('DELETE FROM db_ver')
    else:
        cur.execute('CREATE TABLE db_ver (value INTEGER)')
    cur.execute('INSERT INTO db_ver (value) VALUES(?)', (value,))


class BookPart:

    def __init__(self):
        self.initial = True
        self.pages_list = []

    def addPage(self, page_id, page_number):
        self.pages_list.append((page_id, page_number))

    def minId(self):
        if self.pages_list:
            return self.pages_list[0][0]

    def maxId(self):
        if self.pages_list:
            return self.pages_list[-1][0]


def setPdf(pdf_link, current_id=None):
    online_pdf = online_cover = None
    if pdf_link:
        try:
            field = json.loads(pdf_link)
        except:
            field = {}

        if 'alias' in field:
            online_pdf = 1
        else:
            if 'files' in field:
                online_pdf = 1
                for file in field['files']:
                    if '#' in file:
                        version = val(file[file.find('#') + 1:])
                        if version > online_pdf:
                            online_pdf = version

            elif 'cover' in field:
                online_cover = field['cover']
            else:
                if current_id:
                    CoverDb().delCover(current_id)
    return (
     online_pdf, online_cover)


def importMajor(book_id, patch_path, major, minor, progression_signal):
    """Import one downloaded book, each step reporting its own 1..100.

    Extraction used to be the only step that reported anything, so a big book
    showed a percent, reached 100, and then sat silent through the rest. Every
    step now speaks for itself: the ones that can count (unpacking, the
    services) run their own percent from 1 to 100, and the ones that cannot
    (clearing the previous copy, folding the ready-made lucene pieces in) say
    only that they are busy. Nothing here guesses how long a step will take
    relative to the others - a step that is quick passes in a blink, and a step
    that is slow is the one holding the number, which is exactly what the
    reader needs to know."""
    from customs import pextract
    last_reported = [
     None]

    def report(percent):
        value = max(1, min(99, int(percent)))
        if value == last_reported[0]:
            return
        last_reported[0] = value
        progression_signal.emit(book_id, value, 100)

    def busy():
        last_reported[0] = None
        progression_signal.emit(book_id, -1, 100)

    busy()
    CoreDb().setBookVersion(book_id, -1, 0)
    if not CoreDb().preMajor(book_id):
        return
    else:
        extract_path = os.path.dirname(patch_path)
        base = os.path.splitext(os.path.basename(patch_path))[0]
        return pextract(patch_path, extract_path, call_back=report) or None
    busy()
    file_path = os.path.join(extract_path, f"{base}.sqlite")
    if not os.path.isfile(file_path):
        return
    else:
        book_path = bookPath(book_id)
        try:
            os.renames(file_path, book_path)
        except:
            pass

        if not os.path.isfile(book_path):
            return
        if not Book(book_id).inject(extract_path):
            return
        return BookDb(book_id).freshServices(call_back=report) or None
    busy()
    return CoreDb().setBookVersion(book_id, major, minor)


def keepTop(cur, limit, table, column, record_deleted=None):
    results = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    if results:
        if results[0] > limit:
            stem = f"FROM {table} WHERE {column} NOT IN (SELECT {column} FROM {table} ORDER BY {column} DESC LIMIT {limit})"
            deletion = f"DELETE {stem}"
            if record_deleted:
                values = listResults(cur.execute(f"SELECT {record_deleted} {stem}"))
                cur.execute(deletion)
                return values
            cur.execute(deletion)


def keepComments(comments):
    from customs import pack
    if comments:
        for book_id in comments:
            if not pack(comments[book_id], keptCommentsPath(book_id)):
                return

    return True