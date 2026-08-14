# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: engine.py
import atexit, os, shutil, signal, threading, traceback, unicodedata
from collections import defaultdict
import jpype
from jpype.types import JArray, JClass, JString
from across import Across
from enum import Enum
import regex as re, sqlite3
from dirs import resultsFolder
LUCENE_ONE = Across.lucene_version == 1
LUCENE_TWO = Across.lucene_version == 2

class LazyJClass:

    def __init__(self, class_name, optional=False):
        self.class_name = class_name
        self.optional = optional
        self._class = None
        self._loaded = False
        self._lock = threading.Lock()

    def resolve(self):
        if not self._loaded:
            with self._lock:
                if not self._loaded:
                    try:
                        self._class = JClass(self.class_name)
                    except:
                        if not self.optional:
                            raise
                        self._class = None

                    self._loaded = True
        return self._class

    def __bool__(self):
        return self.resolve() is not None

    def __call__(self, *args, **kwargs):
        java_class = self.resolve()
        if java_class is None:
            raise RuntimeError(f"Java class is not available: {self.class_name}")
        return java_class(*args, **kwargs)

    def __getattr__(self, name):
        java_class = self.resolve()
        if java_class is None:
            raise AttributeError(name)
        return getattr(java_class, name)

    def __repr__(self):
        if self._loaded:
            return repr(self.resolve())
        return f"<lazy JClass {self.class_name}>"


class LazyLuceneCodec:

    def __init__(self):
        self._class = None
        self._loaded = False
        self._lock = threading.Lock()

    def resolve(self):
        if not self._loaded:
            with self._lock:
                if not self._loaded:
                    self._class = resolve_lucene_codec()
                    self._loaded = True
        return self._class

    def __call__(self, *args, **kwargs):
        return (self.resolve())(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.resolve(), name)


BooleanClause = LazyJClass('org.apache.lucene.search.BooleanClause')
BooleanQuery = LazyJClass('org.apache.lucene.search.BooleanQuery')
BytesRef = LazyJClass('org.apache.lucene.util.BytesRef')
CharTermAttribute = LazyJClass('org.apache.lucene.analysis.tokenattributes.CharTermAttribute')
CodecReader = LazyJClass('org.apache.lucene.index.CodecReader')
SlowCodecReaderWrapper = LazyJClass('org.apache.lucene.index.SlowCodecReaderWrapper')
ConstantScoreQuery = LazyJClass('org.apache.lucene.search.ConstantScoreQuery')
DirectoryReader = LazyJClass('org.apache.lucene.index.DirectoryReader')
ByteBuffersDirectory = LazyJClass('org.apache.lucene.store.ByteBuffersDirectory')
DocValuesType = LazyJClass('org.apache.lucene.index.DocValuesType')
FSDirectory = LazyJClass('org.apache.lucene.store.FSDirectory')
Highlighter = LazyJClass('org.apache.lucene.search.highlight.Highlighter')
IndexOptions = LazyJClass('org.apache.lucene.index.IndexOptions')
IndexSearcher = LazyJClass('org.apache.lucene.search.IndexSearcher')
IndexWriter = LazyJClass('org.apache.lucene.index.IndexWriter')
IntPoint = LazyJClass('org.apache.lucene.document.IntPoint')
IndexWriterConfig = LazyJClass('org.apache.lucene.index.IndexWriterConfig')
JInteger = LazyJClass('java.lang.Integer')
JList = LazyJClass('java.util.ArrayList')
JSet = LazyJClass('java.util.HashSet')
JMap = LazyJClass('java.util.HashMap')
JLSet = LazyJClass('java.util.LinkedHashSet')
LuceneDocument = LazyJClass('org.apache.lucene.document.Document')
LuceneFieldType = LazyJClass('org.apache.lucene.document.FieldType')
NullFragmenter = LazyJClass('org.apache.lucene.search.highlight.NullFragmenter')
NumericDocValuesField = LazyJClass('org.apache.lucene.document.NumericDocValuesField')
Paths = LazyJClass('java.nio.file.Paths')
PerFieldAnalyzerWrapper = LazyJClass('org.apache.lucene.analysis.miscellaneous.PerFieldAnalyzerWrapper')
PhraseQuery = LazyJClass('org.apache.lucene.search.PhraseQuery')
QueryParser = LazyJClass('org.apache.lucene.queryparser.classic.QueryParser')
QueryScorer = LazyJClass('org.apache.lucene.search.highlight.QueryScorer')
SimpleHTMLFormatter = LazyJClass('org.apache.lucene.search.highlight.SimpleHTMLFormatter')
SimpleSpanFragmenter = LazyJClass('org.apache.lucene.search.highlight.SimpleSpanFragmenter')
Sort = LazyJClass('org.apache.lucene.search.Sort')
SortField = LazyJClass('org.apache.lucene.search.SortField')
SpanMultiTermQueryWrapper = LazyJClass('org.apache.lucene.queries.spans.SpanMultiTermQueryWrapper')
SpanNearQuery = LazyJClass('org.apache.lucene.queries.spans.SpanNearQuery')
SpanTermQuery = LazyJClass('org.apache.lucene.queries.spans.SpanTermQuery')
MatchAllDocsQuery = LazyJClass('org.apache.lucene.search.MatchAllDocsQuery')
Term = LazyJClass('org.apache.lucene.index.Term')
TermInSetQuery = LazyJClass('org.apache.lucene.search.TermInSetQuery')
TermQuery = LazyJClass('org.apache.lucene.search.TermQuery')
WildcardQuery = LazyJClass('org.apache.lucene.search.WildcardQuery')
RegexpQuery = LazyJClass('org.apache.lucene.search.RegexpQuery')
WhitespaceAnalyzer = LazyJClass('org.apache.lucene.analysis.core.WhitespaceAnalyzer')
SoftDeletesDirectoryReaderWrapper = LazyJClass('org.apache.lucene.index.SoftDeletesDirectoryReaderWrapper')
TieredMergePolicy = LazyJClass('org.apache.lucene.index.TieredMergePolicy')
LuceneField = LazyJClass('ws.shamela.CustomField')
StemStore = LazyJClass('ws.shamela.StemStore')
MorphologyAnalyzer = LazyJClass('ws.shamela.MorphologyAnalyzer')
CustomAnalyzer = LazyJClass('ws.shamela.CustomAnalyzer')
Uid = LazyJClass('ws.shamela.Uid')
LuceneBulk = None if LUCENE_ONE else LazyJClass('ws.shamela.LuceneBulk', optional=True)
LuceneCodec = LazyLuceneCodec()
_basic_map = None
_sqlite_stem_store_class = None

def resolve_lucene_codec():
    if LUCENE_ONE:
        candidates = ('org.apache.lucene.codecs.lucene95.Lucene95Codec', 'org.apache.lucene.backward_codecs.lucene95.Lucene95Codec')
    else:
        candidates = ('org.apache.lucene.codecs.lucene104.Lucene104Codec', 'org.apache.lucene.codecs.lucene103.Lucene103Codec',
                      'org.apache.lucene.backward_codecs.lucene99.Lucene99Codec',
                      'org.apache.lucene.backward_codecs.lucene95.Lucene95Codec',
                      'org.apache.lucene.codecs.lucene95.Lucene95Codec')
    last_error = None
    for class_name in candidates:
        try:
            return JClass(class_name)
        except Exception as error:
            try:
                last_error = error
            finally:
                error = None
                del error

    if last_error:
        raise last_error
    raise RuntimeError('No compatible Lucene codec class was found')


def best_compression_codec():
    return LuceneCodec(LuceneCodec.Mode.BEST_COMPRESSION)


LUCENE_CLOSED_MARKERS = ('AlreadyClosedException', 'this IndexReader is closed', 'this IndexWriter is closed')

def is_closed_exception(error):
    text = f"{type(error).__name__}: {error}"
    return any((marker in text for marker in LUCENE_CLOSED_MARKERS))


def is_shutdown_exception(error):
    return Index.is_shutting_down() and is_closed_exception(error)


def configure_writer(analyzer):
    config = IndexWriterConfig(analyzer)
    config.setCodec(best_compression_codec())
    return config


def basicMap():
    global _basic_map
    if _basic_map is None:
        _basic_map = [
         JMap({'ـ': "''", 
          'ﷺ': "''", 'ﷻ': "''", '\ufd40': "''", '\ufd4f': "''", '\ufdff': "''", 
          '\ufd4a': "''", '\ufd44': "''", '\ufd43': "''", '\ufd45': "''", 
          '\ufd42': "''", 
          '\ufd41': "''", '\ufdfe': "''", '\ufd4e': "''", '\ufd47': "''", 
          '\ufd4d': "''", '\ufd48': "''", '\ufd49': "''", '\ufd4c': "''", 
          '﷽': "''", 
          '\ufd4b': "''", 
          '\ufdcf': "''", '\ufd46': "''", 
          'گ': "'ك'", 'پ': "'ب'", 'چ': "'ج'"})]
    return _basic_map


def charFilters(is_diacritics, is_hamza, is_numbers, is_quran=False):
    char_map = list(basicMap())
    if not is_diacritics:
        char_map += [JMap({'َ': "''", 'ً': "''", 'ُ': "''", 'ٌ': "''", 'ِ': "''", 'ٍ': "''", 'ْ': "''", 
          'ّ': "''"})]
    if not is_numbers:
        char_map += [
         JMap({chr(codepoint): ' ' for codepoint in range(1114112) if unicodedata.category(chr(codepoint)) == 'Nd'})]
    if not is_hamza:
        char_map += [JMap({'ٱ': "'ا'", 'آ': "'ا'", 'أ': "'ا'", 'إ': "'ا'", 'ى': "'ي'", 'ؤ': "'و'", 'ة': "'ه'"}),
         JMap({'ءا':'ء',  'يء':'ئ'})]
        if is_quran:
            char_map += [JMap({'ائ': 'اا'})]
        char_map += [
         JMap({'ئو': "'وو'", 'ءو': "'وو'", 'رحمان': "'رحمن'", 'سماوات': "'سموات'", 'مائه': "'مئه'", 
          'مائت': "'مئت'", 
          'سماعيل': "'سمعيل'", 'براهام': "'براهيم'", 'اسحاق': "'اسحق'", 
          'هاذا': "'هذا'", 'هاذين': "'هذين'", 'هاؤلاء': "'هؤلاء'", 'اولائك': "'اولئك'"}),
         JMap({'ئ':'ي',  'داوود':'داود',  'طاووس':'طاوس'}),
         JMap({'سفرايين': 'سفراين'})]
    return char_map


class Analyzer:
    _cache = {}
    stemStore = None

    @classmethod
    def stem(cls):
        if 'stem' not in cls._cache:
            cls._cache['stem'] = cls._stemAnalyzer(True)
        return cls._cache['stem']

    @classmethod
    def white(cls):
        if 'white' not in cls._cache:
            cls._cache['white'] = WhitespaceAnalyzer()
        return cls._cache['white']

    @classmethod
    def custom(cls, is_diacritics, is_hamza, is_numbers, is_quran=False):
        key = f"_{'q' if is_quran else ''}{'d' if is_diacritics else ''}{'h' if is_hamza else ''}{'n' if is_numbers else ''}"
        if key not in cls._cache:
            cls._cache[key] = cls._custom(is_diacritics, is_hamza, is_numbers, is_quran)
        return cls._cache[key]

    @classmethod
    def shamela(cls):
        return cls.custom(False, False, False)

    @classmethod
    def quran(cls):
        return cls.custom(False, False, False, True)

    @classmethod
    def _custom(cls, is_diacritics, is_hamza, is_numbers, is_quran=False):
        if not is_diacritics:
            tokenizer = is_hamza or is_numbers or 'letter'
            f_numbers = True
        else:
            tokenizer = 'standard'
            f_numbers = is_numbers
        synonym = JLSet() if is_hamza else JLSet([JMap({'ابن': 'بن'})])
        return CustomAnalyzer(tokenizer, JLSet(charFilters(is_diacritics, is_hamza, f_numbers, is_quran)), synonym)

    @classmethod
    def wrapper(cls, index_name=None):
        body_analyzer = cls.quran() if index_name == 'aya' else cls.shamela()
        return PerFieldAnalyzerWrapper(cls.white(), {'body':body_analyzer, 
         'foot':cls.shamela(),  'comment':cls.shamela(),  'hint':cls.shamela(),  'm_body':cls.stem(), 
         'm_foot':cls.stem(),  'm_comment':cls.stem(),  'm_hint':cls.stem(),  'n_body':cls.white(), 
         'n_foot':cls.white(),  'n_comment':cls.white(),  'n_hint':cls.white(),  'single':cls.shamela(), 
         'double':cls.shamela(),  'author':cls.shamela(),  'esnad':cls.white()})

    @classmethod
    def _stemAnalyzer(cls, remove_tashkeel):
        from dirs import serviceDbPath
        cls.stemStore = sqliteStemStoreClass()(serviceDbPath('S2'))
        return MorphologyAnalyzer(JLSet(basicMap()), cls.stemStore, remove_tashkeel)

    @classmethod
    def commitStems(cls):
        if cls.stemStore:
            cls.stemStore.commit()


def jset(f_token):
    j = JSet()
    j.add(f_token)
    return j


class StemCache:
    _cache = {}
    _max_value = 100000
    _deflation = 30000
    _counter = 0
    _full_limit = 1000000
    _is_full = False

    @classmethod
    def find(cls, token):
        if token in cls._cache:
            if not cls._is_full:
                if cls._cache[token]['count'] < cls._full_limit:
                    cls._cache[token]['count'] += 1
            if cls._cache[token]['roots']:
                return cls._cache[token]['roots']
            return jset((f"{token}"))

    @classmethod
    def add(cls, token, roots):
        if not cls._is_full:
            cls._counter += 1
            cls._cache[token] = {'roots':roots,  'count':0}
            if cls._counter > cls._max_value:
                cls._deflate()

    @classmethod
    def _deflate(cls):
        arranged = sorted((cls._cache.items()), key=(lambda item: item[1]['count']))
        if arranged[0][1]['count'] >= cls._full_limit:
            cls._is_full = True
            return
        i = 1
        for item in arranged:
            if item[1]['count'] >= cls._full_limit:
                break
            del cls._cache[item[0]]
            i += 1
            if i > cls._deflation:
                break

        cls._counter -= i


def sqliteStemStoreClass():
    global _sqlite_stem_store_class
    if _sqlite_stem_store_class is not None:
        return _sqlite_stem_store_class

    @jpype.JImplements((StemStore.resolve()), deferred=True)
    class SqliteStemStore:
        ARABIC = set('ضصثقفغعهخحجةشسيىبلاآتنمكوؤرإزأدءذئطظ')

        def __init__(self, db_file, commit_rate=None):
            self.commit_counter = 0
            self.commit_rate = commit_rate or 1000
            self.db_file = db_file
            self.db = sqlite3.connect((self.db_file), check_same_thread=False)
            self.db.execute('PRAGMA journal_mode = WAL;')
            self.db.execute('PRAGMA synchronous = NORMAL;')
            self.db.execute('CREATE TABLE IF NOT EXISTS roots (token BLOB, root BLOB);')
            self.db.execute('CREATE INDEX IF NOT EXISTS token_idx ON roots(token);')

        def commit(self):
            try:
                self.db.execute('COMMIT;')
            except:
                pass

        @jpype.JOverride
        def findRoots(self, token):
            roots = StemCache.find(token)
            if roots:
                return roots
                f_token = f"{token}"
                if f_token[0] in self.ARABIC:
                    try:
                        stoken = f_token.encode('cp1256')
                    except:
                        return jset(f_token)
                    else:
                        result = self.db.execute('SELECT token, root FROM roots WHERE token = ?', (stoken,)).fetchone()
                    if result:
                        if result[1] is None:
                            StemCache.add(token, None)
                            return jset(f_token)
                        roots = JSet()
                        for root in result[1].decode('cp1256').split(','):
                            roots.add(root)

                        StemCache.add(token, roots)
                        return roots
                    else:
                        return
            else:
                return jset(f_token)

        @jpype.JOverride
        def saveRoots(self, token, roots):
            f_roots = ','.join([f"{root}" for root in roots])
            f_token = f"{token}"
            if f_roots and f_roots != f_token:
                self.db.execute('INSERT INTO roots (token, root) VALUES (?, ?);', ((f"{token}").encode('cp1256'), f_roots.encode('cp1256')))
                StemCache.add(token, roots)
            else:
                self.db.execute('INSERT INTO roots (token) VALUES (?);', ((f"{token}").encode('cp1256'),))
                StemCache.add(token, None)
            self.commit_counter += 1
            if self.commit_counter > self.commit_rate:
                try:
                    self.db.execute('COMMIT;')
                except:
                    pass

                self.commit_counter = 0

        def __del__(self):
            self.db.close()

    _sqlite_stem_store_class = SqliteStemStore
    return _sqlite_stem_store_class


class FieldType(Enum):
    ORD = 1
    ID = 2
    TEXT = 3
    ANALYSE = 4
    STORE = 5
    KEY = 6


class Field:
    _cache = {}

    def __init__(self, name, field_type, value):
        self.key = f"{name}|{field_type.value}"
        if self.key in Field._cache:
            if field_type == FieldType.ORD:
                Field._cache[self.key].setIntValue(value)
            else:
                Field._cache[self.key].setStringValue(value)
        else:
            lft = LuceneFieldType()
            lft.setStoreTermVectorOffsets(False)
            lft.setStoreTermVectorPayloads(False)
            lft.setStoreTermVectorPositions(False)
            lft.setStoreTermVectors(False)
            lft.setOmitNorms(True)
            lft.setStored(field_type in (FieldType.ID, FieldType.TEXT, FieldType.STORE))
            lft.setDocValuesType(DocValuesType.NUMERIC if field_type == FieldType.ORD else DocValuesType.NONE)
            if field_type in (FieldType.TEXT, FieldType.ANALYSE):
                lft.setTokenized(True)
                lft.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)
            else:
                lft.setTokenized(False)
                lft.setIndexOptions(IndexOptions.NONE if field_type in (FieldType.STORE, FieldType.ORD) else IndexOptions.DOCS)
            lft.freeze()
            Field._cache[self.key] = LuceneField(name, value, lft)

    def field(self):
        return Field._cache[self.key]


class Fake:

    def __init__(self):
        self.context = 2

    def evaluateAllowed(self):
        from dbmanager import CoreDb
        self.allowed_list = CoreDb().allowedBooks(self.context)
        self.allowed_set = set(self.allowed_list)


class QueryType(Enum):
    QURAN = 1
    PAGES = 2
    TITLES = 3
    BIBLIO = 4


class Query:

    def __init__(self, global_index):
        self.clear()
        self.global_index = global_index

    def clear(self):
        self.type = QueryType.PAGES
        self.bodyIncluded = True
        self.footIncluded = True
        self.commentIncluded = True
        self.stemmed = False
        self.hamza = False
        self.diacritics = False
        self.numbers = False
        self.is_or = False
        self.phrases = []
        self.and_options = []
        self.scope_json = None
        self.scope_list = None
        self.scope_size = None
        self.results = None
        self.pre_results = None
        self.results_hash = None
        self.results_row = None
        self._query = None
        self._final_query = None
        self._snippet_query = None
        self._final_analyzer = None
        self._snippet_phrases = []
        self._index = None
        self._fields = []
        self.empty_base = None
        self.not_only = None
        self.not_in_or = None

    def load(self, info):
        if 'type' in info:
            self.type = QueryType(info['type'])
        else:
            if 'excludes' in info:
                if 'body' in info['excludes']:
                    self.bodyIncluded = False
                if 'foot' in info['excludes']:
                    self.footIncluded = False
                if 'comment' in info['excludes']:
                    self.commentIncluded = False
            if 'features' in info:
                if 'stemmed' in info['features']:
                    self.stemmed = True
                if 'hamza' in info['features']:
                    self.hamza = True
                if 'diacritics' in info['features']:
                    self.diacritics = True
                if 'numbers' in info['features']:
                    self.numbers = True
                if 'is_or' in info['features']:
                    self.is_or = True
        self.and_options = info['and_options'] if 'and_options' in info else [[0, False]]
        if 'scope' in info:
            self.scope_json = info['scope']
        if 'results_hash' in info:
            self.results_hash = info['results_hash']
            self.results_row = info['results_row']
            self.results = {'source':unpickle(self.results_hash),  'row':self.results_row}
        self.phrases = info['phrases']

    def save(self, results=None, bypass_results=None, context_id=None):
        from dbmanager import UserDb
        info = {}
        if self.type != QueryType.PAGES:
            info['type'] = self.type.value
        info['phrases'] = self.phrases
        excludes = []
        if not self.bodyIncluded:
            excludes.append('body')
        if not self.footIncluded:
            excludes.append('foot')
        if not self.commentIncluded:
            excludes.append('comment')
        if excludes:
            info['excludes'] = excludes
        features = []
        if self.stemmed:
            features.append('stemmed')
        if self.hamza:
            features.append('hamza')
        if self.diacritics:
            features.append('diacritics')
        if self.numbers:
            features.append('numbers')
        if self.is_or:
            features.append('is_or')
        if features:
            info['features'] = features
        else:
            if self.and_options:
                if self.and_options != [[0, False]]:
                    info['and_options'] = self.and_options
            if self.scope_json:
                info['scope'] = self.scope_json
            if results:
                self.results = results
                if not bypass_results:
                    if not self.results_hash:
                        self.results_hash = pickle(results['source'])
                    info['results_hash'] = self.results_hash
                    info['results_row'] = results['row']
                    info['results_count'] = len(results['source'])
                    UserDb().addResultHash(context_id, self.results_hash)
        return info

    def buildScope(self):
        from selectwidget import ScopeSet
        from dbmanager import CoreDb
        if self.scope_json:
            scope_set = ScopeSet(Fake())
            scope_set.addScope(self.scope_json, True)
            self.scope_list = scope_set.flatScope()
        else:
            self.scope_list = CoreDb().allowedBooks(context=2)
        self.scope_size = len(self.scope_list)

    def _baseQuery(self):
        if not self._query:
            affirm_only = bool(self.secondPass()) and not self.is_or
            self._query = fieldsQuery(self._fields, self.info(), False, affirm_only)
        return self._query

    def info(self):
        return {'type':self.type.value, 
         'phrases':self.phrases,  'is_or':self.is_or,  'and_options':self.and_options,  'wild':self.wild,  'stemmed':self.stemmed, 
         'hamza':self.hamza,  'diacritics':self.diacritics,  'numbers':self.numbers,  'snippet_phrases':self._snippet_phrases}

    def numericPhrases(self):
        for phrases in self.phrases:
            for phrase in phrases:
                for s in phrase:
                    if re.search('\\D', s):
                        return

        return True

    def _finalQuery(self):
        if not self._final_query:
            if not self.secondPass():
                self._final_query = self._baseQuery()
            else:
                self._final_query = ConstantScoreQuery(fieldsQuery(self._fields, self.info(), True))
        return self._final_query

    def _snippetQuery(self):
        if not self._snippet_query:
            search_info = dict(self.info())
            search_info['phrases'] = self.info()['snippet_phrases']
            self._snippet_query = ConstantScoreQuery(fieldsQuery([''], search_info, True))
        return self._snippet_query

    def adjustParameters(self):

        def merge(panels):
            if len(panels) < 2:
                return panels
            merged = []
            for panel in panels:
                merged += [phrase for phrase in panel]

            return merged

        and_phrases, or_phrases, not_phrases = self.phrases
        if self.is_or:
            or_phrases = merge(or_phrases)
        else:
            not_phrases = merge(not_phrases)
        self.phrases = (
         and_phrases, or_phrases, not_phrases)
        if self.type == QueryType.PAGES:
            if self.bodyIncluded:
                self._fields.append('m_body' if self.stemmed else 'body')
            if self.footIncluded:
                self._fields.append('m_foot' if self.stemmed else 'foot')
            if self.commentIncluded:
                self._fields.append('m_comment' if self.stemmed else 'comment')
        else:
            self._fields = ['m_body'] if self.stemmed else ['body']
        self.wild = None
        if self.stemmed:
            self.hamza = False
            self.diacritics = False
            self.numbers = False
        if self.type == QueryType.QURAN:
            self.numbers = False
        if self.numbers:
            self.numbers = False
            for panel_group in self.phrases:
                if panel_group:
                    for panel in panel_group:
                        for phrase in panel:
                            if re.match('.*\\d.*', phrase):
                                self.numbers = True
                                break

        self._snippet_phrases = snippetPhrases(self.phrases)
        self.not_only = not (and_phrases or or_phrases)
        self.not_in_or = self.is_or and bool(not_phrases) and not self.not_only

    def _finalAnalyzer(self):
        if not self._final_analyzer:
            self._final_analyzer = getAnalyzer(self.info(), True)
        return self._final_analyzer

    def secondPass(self):
        if self.empty_base or self.hamza or self.diacritics:
            return True
        if self.numbers:
            if not self.numericPhrases():
                return True

    def preResulted(self, results):
        if self.pre_results:
            return [result for result in results if result in self.pre_results]
        return results

    def filterHits(self, searcher, hits, source_fields, item=None):
        if LuceneBulk:
            try:
                ids = [f"{value}" for value in LuceneBulk.secondPassIds(searcher, hits, javaStringArray(source_fields), javaStringArray(self._fields), self._finalAnalyzer(), self._finalQuery(), sortBy())]
                if item:
                    return [(item, _id) for _id in ids]
                return self.preResulted(ids)
            except:
                pass

        return self.filter(bulkHitRows(searcher, hits, source_fields), item)

    def execute(self):
        self.adjustParameters()
        if self.type == QueryType.PAGES:
            self._index = 'page'
        else:
            if self.type == QueryType.TITLES:
                self._index = 'title'
            else:
                if self.type == QueryType.QURAN:
                    self._index = 'aya'
                else:
                    if self.type == QueryType.PAGES or self.type == QueryType.TITLES:
                        self.buildScope()
                        query = BooleanQuery.Builder()
                        if not self.empty_base:
                            query.add(self._baseQuery(), BooleanClause.Occur.MUST)
                        query.add(scopeQuery(self.scope_list), BooleanClause.Occur.MUST)
                        query = ConstantScoreQuery(query.build())
                    else:
                        query = ConstantScoreQuery(self._baseQuery())
                    if self.results:
                        yield self.results['source']
                    else:
                        hits_limit = 1000
                    sorts = sortBy(sortsFromIndex(self._index))
                    second_pass = self.secondPass()
                    with self.global_index.lease(self._index) as (searcher):
                        batch_number = 0
                        hits = searcher.search(query, hits_limit, sorts, False).scoreDocs
                        while Index.is_shutting_down():
                            return
                            if hits:
                                batch_number += 1
                                if LUCENE_ONE:
                                    if second_pass:
                                        ids = self.filter([((f"{searcher.doc(hit.doc).get('id')}"), [f"{searcher.doc(hit.doc).get(field) or ''}" for field in self._fields]) for hit in hits])
                                    else:
                                        ids = self.preResulted([f"{searcher.doc(hit.doc).get('id')}" for hit in hits])
                                else:
                                    if second_pass:
                                        ids = self.filterHits(searcher, hits, self._fields)
                                    else:
                                        ids = self.preResulted(bulkHitIds(searcher, hits))
                                yield ids
                                if len(hits) < hits_limit:
                                    break
                                if Index.is_shutting_down():
                                    return
                                last_doc = hits[-1]
                                hits_limit = 9000 if hits_limit == 1000 else 10000
                                hits = searcher.searchAfter(last_doc, query, hits_limit, sorts, False).scoreDocs
                            else:
                                break

    def executeBiblio(self):
        self.adjustParameters()
        if self.results:
            yield self.results['source']
        else:
            field_map = {'hint':'hint', 
             'body':'body_store'}
            hits_limit = 1000
            second_pass = self.secondPass()
            for item in ('b', 'h', 'a'):
                index = 'author' if item == 'a' else 'book'
                sorts = sortBy(sortsFromIndex(self._index))
                self._fields = [('m_hint' if self.stemmed else 'hint') if item == 'h' else 'm_body' if self.stemmed else 'body']
                affirm_only = bool(self.secondPass()) and not self.is_or
                query = ConstantScoreQuery(fieldsQuery(self._fields, self.info(), False, affirm_only))
                with self.global_index.lease(index) as (searcher):
                    batch_number = 0
                    hits = searcher.search(query, hits_limit, sorts, False).scoreDocs
                    while Index.is_shutting_down():
                        return
                        if hits:
                            batch_number += 1
                            if LUCENE_ONE:
                                if second_pass:
                                    ids = self.filter([((f"{searcher.doc(hit.doc).get('id')}"),
                                     [f"{searcher.doc(hit.doc).get(field_map[field]) or ''}" for field in self._fields]) for hit in hits], item)
                                else:
                                    ids = self.preResulted([(item, (f"{searcher.doc(hit.doc).get('id')}")) for hit in hits])
                            else:
                                source_fields = [field_map[field] for field in self._fields]
                                if second_pass:
                                    ids = self.filterHits(searcher, hits, source_fields, item)
                                else:
                                    ids = self.preResulted([(item, _id) for _id in bulkHitIds(searcher, hits)])
                            yield ids
                            if len(hits) < hits_limit:
                                break
                            if Index.is_shutting_down():
                                return
                            last_doc = hits[-1]
                            hits_limit = 9000 if hits_limit == 1000 else 10000
                            hits = searcher.searchAfter(last_doc, query, hits_limit, sorts, False).scoreDocs
                        else:
                            break

    def filter(self, results, item=None):
        ram_dir = ByteBuffersDirectory()
        config = configure_writer(self._finalAnalyzer())
        writer = IndexWriter(ram_dir, config)
        reader = None
        try:
            w_doc = LuceneDocument()
            field_count = len(self._fields)
            for _id, fields in results:
                w_doc.clear()
                w_doc.add(Field('id', FieldType.ID, _id).field())
                for i in range(field_count):
                    value = fields[i]
                    if value:
                        w_doc.add(Field(self._fields[i], FieldType.ANALYSE, value).field())

                writer.addDocument(w_doc)

            writer.commit()
            hits_limit = 10000
            reader = DirectoryReader.open(ram_dir)
            searcher = IndexSearcher(reader)
            hits = searcher.search(self._finalQuery(), hits_limit, sortBy(), False).scoreDocs
            ids = bulkHitIds(searcher, hits)
            if item:
                return [(item, _id) for _id in ids]
            return self.preResulted(ids)
        finally:
            if reader:
                reader.close()
            writer.close()
            ram_dir.close()

    def snippet(self, doc_id, fragment_size=None, multiline=None):
        from textmanager import plain, linear, noTashkeel
        if fragment_size is None:
            fragment_size = 100
        if LUCENE_ONE:
            with self.global_index.lease(self._index) as (searcher):
                for field_name in self._fields:
                    if field_name.startswith('m_'):
                        field_name = field_name[2:]
                    text = getDoc(searcher, doc_id).get(field_name)
                    if text:
                        if self.not_only:
                            fragment = ' '.join((f"{text}").split(' ')[:int(fragment_size / 10)])
                        else:
                            fragment = highlight(text, self._snippetQuery(), self._finalAnalyzer(), fragment_size, '\x01', '\x02')
                            if not fragment:
                                if self.not_in_or:
                                    fragment = ' '.join((f"{text}").split(' ')[:int(fragment_size / 10)])
                        if fragment:
                            if multiline:
                                return noTashkeel((f"{fragment}"))
                            return plain(linear((f"{fragment}")))

            return ''
        with self.global_index.lease(self._index) as (searcher):
            fields = [field_name[2:] if field_name.startswith('m_') else field_name for field_name in self._fields]
            fragment = javaSnippet(searcher, doc_id, fields, self._snippetQuery(), self._finalAnalyzer(), fragment_size, '\x01', '\x02', self.not_only)
            if not fragment:
                if self.not_in_or:
                    fragment = javaSnippet(searcher, doc_id, fields, self._snippetQuery(), self._finalAnalyzer(), fragment_size, '\x01', '\x02', True)
        if fragment:
            if multiline:
                return noTashkeel((f"{fragment}"))
            return plain(linear((f"{fragment}")))
        return ''

    def biblioSnippet(self, prefix, doc_id, fragment_size=None, multiline=None):
        from cache import BookCache, AuthorCache
        from textmanager import plain, linear, noTashkeel
        if fragment_size is None:
            fragment_size = 100
        index = 'author' if prefix == 'a' else 'book'
        field = 'hint' if prefix == 'h' else 'body_store'
        if LUCENE_ONE:
            with self.global_index.lease(index) as (searcher):
                text = getDoc(searcher, doc_id).get(field) or ''
            doc_id = int(doc_id)
            if prefix == 'b':
                text = f"{BookCache.abstractName(doc_id)}\n{BookCache.authorAbstName(doc_id)}\n{text}"
            else:
                if prefix == 'a':
                    text = f"{AuthorCache.authorName(doc_id)}\n{text}"
                elif text:
                    fragment = highlight(text, self._snippetQuery(), self._finalAnalyzer(), fragment_size, '\x01', '\x02')
                    if fragment:
                        if multiline:
                            return noTashkeel((f"{fragment}"))
                        return plain(linear((f"{fragment}")))
                return ''
        with self.global_index.lease(index) as (searcher):
            text = javaBulkField(searcher, doc_id, field) or ''
        doc_id = int(doc_id)
        if prefix == 'b':
            text = f"{BookCache.abstractName(doc_id)}\n{BookCache.authorAbstName(doc_id)}\n{text}"
        else:
            if prefix == 'a':
                text = f"{AuthorCache.authorName(doc_id)}\n{text}"
            if text:
                fragment = javaHighlight(text, self._snippetQuery(), self._finalAnalyzer(), fragment_size, '\x01', '\x02')
                if fragment:
                    if multiline:
                        return noTashkeel((f"{fragment}"))
                    return plain(linear((f"{fragment}")))
            return ''


def getAnalyzer(search_info, is_final):
    if search_info['stemmed']:
        return Analyzer.stem()
    is_quran = search_info.get('type') == QueryType.QURAN.value
    numbers = search_info['numbers']
    if is_final:
        return Analyzer.custom(search_info['diacritics'], search_info['hamza'], numbers, is_quran)
    if numbers:
        return Analyzer.white()
    if is_quran:
        return Analyzer.quran()
    return Analyzer.shamela()


def snippetPhrases(phrases):
    """replace AND queries by OR queries to workaround 2 issues in coloring
    1 - spannear + near queries (if together) happen to colorize every term
    2 - When one phrase only is in the field (the other AND phrase is in another field
    """
    and_phrases, or_phrases, not_phrases = phrases
    or_set = set()
    for item in [and_phrases, or_phrases]:
        if item:
            for panel in item:
                if panel:
                    for phrase in panel:
                        or_set.add(phrase)

    return ([], [list(or_set)], not_phrases)


def wholeSnippet(text, info):
    from customs import NVDA
    search_info = dict(info)
    search_info['phrases'] = search_info['snippet_phrases']
    analyzer = getAnalyzer(search_info, True)
    query = ConstantScoreQuery(fieldsQuery([''], search_info, True))
    stream = analyzer.tokenStream(None, text)
    if NVDA.isRunning():
        pre, post = ('\x01', '')
    else:
        pre, post = ('<span id=go class="search">&#8204;', '</span>')
    highlighter = Highlighter(SimpleHTMLFormatter(pre, post), QueryScorer(query))
    highlighter.setMaxDocCharsToAnalyze(JInteger.MAX_VALUE)
    highlighter.setTextFragmenter(NullFragmenter())
    fragment = highlighter.getBestFragment(stream, text)
    if fragment:
        return (f"{fragment}")
    return text


def highlight(text, query, analyzer, fragment_size, pre, post):
    scorer = QueryScorer(query)
    fragmenter = SimpleSpanFragmenter(scorer, fragment_size)
    highlighter = Highlighter(SimpleHTMLFormatter(pre, post), scorer)
    highlighter.setMaxDocCharsToAnalyze(JInteger.MAX_VALUE)
    highlighter.setTextFragmenter(fragmenter)
    stream = analyzer.tokenStream(None, text)
    highlighted_text = highlighter.getBestFragment(stream, text)
    return highlighted_text or None


class _IndexLease:
    __doc__ = "Context manager that holds an active read lease on an IndexSearcher.\n\n    While a lease is held, Index.clear() and Index.squeeze() will *wait* before\n    closing the underlying reader, eliminating the AlreadyClosedException race\n    that corrupts the index when the user closes the app mid-search.\n\n    Usage::\n\n        with Index.lease('page') as searcher:\n            hits = searcher.search(query, ...)   # reader cannot be closed here\n    "
    __slots__ = ('_index_name', '_searcher')

    def __init__(self, index_name):
        self._index_name = index_name
        self._searcher = None

    def __enter__(self):
        with Index._lease_cond:
            if Index._shutdown:
                raise JClass('org.apache.lucene.store.AlreadyClosedException')('this IndexReader is closed')
            self._searcher = Index._get_or_open_searcher(self._index_name)
            Index._active_leases += 1
        return self._searcher

    def __exit__(self, *_):
        with Index._lease_cond:
            Index._active_leases -= 1
            if Index._active_leases == 0:
                Index._lease_cond.notify_all()
        return False


class Index:
    _directory_cache = {}
    _reader_cache = {}
    _writer_cache = {}
    _retired_readers = []
    _shutdown = False
    _lock = threading.RLock()
    _lease_cond = threading.Condition(_lock)
    _active_leases = 0

    @classmethod
    def lease(cls, index_name):
        """Return an _IndexLease context manager for *index_name*.

        Always use this (rather than calling searcher() directly) whenever a
        searcher is used across more than one statement or in a loop, so that
        Index.clear() cannot close the reader while it is still in use.
        """
        return _IndexLease(index_name)

    @classmethod
    def begin_shutdown(cls):
        cls._shutdown = True

    @classmethod
    def is_shutting_down(cls):
        return cls._shutdown

    @classmethod
    def _get_or_open_searcher(cls, index_name):
        """Open (or return cached) searcher.  Caller MUST hold _lock."""
        if index_name not in cls._reader_cache:
            index_reader = DirectoryReader.open(cls._path(index_name))
            cls._reader_cache[index_name] = IndexSearcher(index_reader)
        return cls._reader_cache[index_name]

    @classmethod
    def _close_searcher_nolock(cls, index_name):
        """Retire a cached searcher's reader.  Caller MUST hold _lock."""
        if index_name in cls._reader_cache:
            cls._retired_readers.append(cls._reader_cache[index_name].getIndexReader())
            del cls._reader_cache[index_name]

    @classmethod
    def directory_path(cls, index_path):
        index_path = os.path.realpath(index_path)
        with cls._lock:
            if index_path not in cls._directory_cache:
                cls._directory_cache[index_path] = FSDirectory.open(Paths.get(index_path))
            return cls._directory_cache[index_path]

    @classmethod
    def _path(cls, index_name):
        index_path = os.path.join(Across.home_directory, 'database', 'store', index_name)
        return cls.directory_path(index_path)

    @classmethod
    def reader(cls, index_name):
        return DirectoryReader.open(cls._path(index_name))

    @classmethod
    def searcher(cls, index_name):
        with cls._lock:
            return cls._get_or_open_searcher(index_name)

    @classmethod
    def writer(cls, index_name):
        with cls._lock:
            if index_name not in cls._writer_cache:
                config = configure_writer(Analyzer.wrapper(index_name))
                Index._writer_cache[index_name] = IndexWriter(cls._path(index_name), config)
            return Index._writer_cache[index_name]

    @classmethod
    def commit(cls, index_name):
        if index_name in cls._writer_cache:
            output = cls.writer(index_name).commit()
            if output != -1:
                if index_name in cls._reader_cache:
                    cls.refresh(index_name)

    @classmethod
    def refresh(cls, index_name):
        with cls._lock:
            if index_name not in cls._reader_cache:
                return
            reader = cls._reader_cache[index_name].getIndexReader()
            updated_reader = DirectoryReader.openIfChanged(reader)
            if updated_reader:
                cls._reader_cache[index_name] = IndexSearcher(updated_reader)
                cls._retired_readers.append(reader)

    @classmethod
    def close_searcher(cls, index_name):
        with cls._lock:
            cls._close_searcher_nolock(index_name)

    @classmethod
    def clear(cls):
        cls._shutdown = True
        with cls._lease_cond:
            cls._lease_cond.wait_for((lambda: cls._active_leases == 0), timeout=30)
            for key in list(cls._reader_cache):
                try:
                    cls._reader_cache[key].getIndexReader().close()
                except:
                    pass

            for key in list(cls._writer_cache):
                try:
                    cls._writer_cache[key].close()
                except:
                    pass

            if not LUCENE_ONE:
                for key in list(cls._directory_cache):
                    try:
                        cls._directory_cache[key].close()
                    except:
                        pass

            for reader in list(cls._retired_readers):
                try:
                    reader.close()
                except:
                    pass

            cls._reader_cache.clear()
            cls._writer_cache.clear()
            cls._retired_readers.clear()
            if not LUCENE_ONE:
                cls._directory_cache.clear()


def replaceQuranIndex(source_path):
    target_path = os.path.join(Across.home_directory, 'database', 'store', 'aya')
    target_realpath = os.path.realpath(target_path)
    with Index._lease_cond:
        if not Index._lease_cond.wait_for((lambda: Index._active_leases == 0), timeout=30):
            return False
            writer = Index._writer_cache.get('aya')
            if writer:
                try:
                    writer.close()
                    del Index._writer_cache['aya']
                except:
                    return False

            searcher = Index._reader_cache.get('aya')
            if searcher:
                try:
                    searcher.getIndexReader().close()
                    del Index._reader_cache['aya']
                except:
                    return False

        else:
            for reader in list(Index._retired_readers):
                try:
                    reader.close()
                except:
                    return False

            Index._retired_readers.clear()
            directory = Index._directory_cache.get(target_realpath)
            if directory:
                try:
                    directory.close()
                    del Index._directory_cache[target_realpath]
                except:
                    return False

            return os.path.isdir(source_path) or False
        shutil.rmtree(target_path, ignore_errors=True)
        if os.path.exists(target_path):
            return False
        os.rename(source_path, target_path)
        return True


def sortsFromIndex(index_name):
    if index_name == 'page' or index_name == 'title':
        return [
         "'date'", "'author'", "'book_up'", "'group'", "'group_order'", 
         "'book'", "'page'"]
    if index_name == 'book':
        return [
         "'date'", "'author'", "'book_up'", "'group'", "'group_order'", 
         "'book'"]
    if index_name == 'author':
        return [
         'date', 'author_id']
    if index_name == 'aya':
        return [
         'aya_id']
    return []


def scopeQuery(book_ids):
    if len(book_ids) == 1:
        return TermQuery(Term('book_key', (f"{book_ids[0]}")))
    return term_in_set_query('book_key', book_ids)


def javaStringArray(values):
    return JArray(JString)([f"{value}" for value in values])


def normalizeBulkRow(row):
    return (
     (f"{row[0]}"), [f"{row[i] or ''}" for i in range(1, len(row))])


def javaBulkField(searcher, _id, field):
    if LuceneBulk:
        try:
            value = LuceneBulk.fieldById(searcher, f"{_id}", field)
            if value is not None:
                return (f"{value}")
            return
        except:
            pass

    doc = getDoc(searcher, (f"{_id}"))
    if doc:
        if doc.get(field) is not None:
            return (f"{doc.get(field)}")


def javaBulkFields(searcher, _id, fields):
    if LuceneBulk:
        try:
            return [(f"{value}") if value is not None else None for value in LuceneBulk.fieldsById(searcher, f"{_id}", javaStringArray(fields))]
        except:
            pass

    doc = getDoc(searcher, (f"{_id}"))
    if doc:
        return [f"{doc.get(field) or ''}" for field in fields]
    return [
     None] * len(fields)


def javaBulkFirstField(searcher, _id, fields):
    if LuceneBulk:
        try:
            value = LuceneBulk.firstFieldById(searcher, f"{_id}", javaStringArray(fields))
            if value is not None:
                return (f"{value}")
            return
        except:
            pass

    else:
        doc = getDoc(searcher, (f"{_id}"))
        return doc or None
    for field in fields:
        value = doc.get(field)
        if value:
            return (f"{value}")

    return ''


def javaHighlight(text, query, analyzer, fragment_size, pre, post):
    if LuceneBulk:
        try:
            value = LuceneBulk.bestFragment(text, query, analyzer, fragment_size, pre, post)
            if value is not None:
                return (f"{value}")
            return
        except:
            pass

    return highlight(text, query, analyzer, fragment_size, pre, post)


def javaSnippet(searcher, _id, fields, query, analyzer, fragment_size, pre, post, not_only=False):
    if LuceneBulk:
        try:
            return (f"""{LuceneBulk.snippetById(searcher, f"{_id}", javaStringArray(fields), query, analyzer, fragment_size, pre, post, not_only) or ''}""")
        except:
            pass

    text = javaBulkFirstField(searcher, _id, fields)
    if text:
        if not_only:
            return ' '.join((f"{text}").split(' ')[:int(fragment_size / 10)])
        fragment = javaHighlight(text, query, analyzer, fragment_size, pre, post)
        if fragment:
            return fragment
    return ''


def bulkHitIds(searcher, hits):
    if LuceneBulk:
        try:
            return [f"{value}" for value in LuceneBulk.hitIds(searcher, hits)]
        except:
            pass

    return [f"{fetchDoc(searcher, hit.doc).get('id')}" for hit in hits]


def bulkHitRows(searcher, hits, fields):
    if LuceneBulk:
        try:
            return [normalizeBulkRow(row) for row in LuceneBulk.hitRows(searcher, hits, javaStringArray(fields))]
        except:
            pass

    results = []
    for hit in hits:
        doc = fetchDoc(searcher, hit.doc)
        results.append(((f"{doc.get('id')}"), [f"{doc.get(field) or ''}" for field in fields]))

    return results


def bulkQueryIds(searcher, query, hits_limit, sorts):
    if LuceneBulk:
        try:
            return [f"{value}" for value in LuceneBulk.queryIds(searcher, query, hits_limit, sorts)]
        except:
            pass

    results = []
    hits = searcher.search(query, hits_limit, sorts, False).scoreDocs
    while True:
        if hits:
            results += bulkHitIds(searcher, hits)
            if len(hits) < hits_limit:
                break
            last_doc = hits[-1]
            hits = searcher.searchAfter(last_doc, query, hits_limit, sorts, False).scoreDocs
        else:
            break

    return results


def bulkQueryRows(searcher, query, fields, hits_limit, sorts):
    if LuceneBulk:
        try:
            return [normalizeBulkRow(row) for row in LuceneBulk.queryRows(searcher, query, hits_limit, sorts, javaStringArray(fields))]
        except:
            pass

    results = []
    hits = searcher.search(query, hits_limit, sorts, False).scoreDocs
    while True:
        if hits:
            results += bulkHitRows(searcher, hits, fields)
            if len(hits) < hits_limit:
                break
            last_doc = hits[-1]
            hits = searcher.searchAfter(last_doc, query, hits_limit, sorts, False).scoreDocs
        else:
            break

    return results


def tokenize(text, analyzer):
    result = []
    stream = analyzer.tokenStream(None, text)
    stream.reset()
    while stream.incrementToken():
        result.append(str(stream.getAttribute(CharTermAttribute.class_).toString()))

    stream.close()
    return ' '.join(result)


def clean_phrase(text, analyzer):
    text = text.replace('؟', 'ˀ').replace('?', 'ˀ').replace('*', 'ˑ')
    text = tokenize(text, analyzer)
    return text.replace('ˀ', '?').replace('ˑ', '*')


def stemmed_query(text, field, _, __):
    return QueryParser(field, Analyzer.stem()).parse(f'"{text}"')


def phrase_query(text, field, analyzer, span_needed):
    text = clean_phrase(text, analyzer)
    if text == '':
        return
    has_space = lambda value: ' ' in value
    has_wildcard = lambda value: '*' in value or '?' in value
    if has_wildcard(text):
        if has_space(text):
            span_clauses = []
            for word in text.split(' '):
                if has_wildcard(word):
                    span_clauses.append(SpanMultiTermQueryWrapper(WildcardQuery(Term(field, word))))
                else:
                    span_clauses.append(SpanTermQuery(Term(field, word)))

            return SpanNearQuery(span_clauses, 0, True)
        if span_needed:
            return SpanMultiTermQueryWrapper(WildcardQuery(Term(field, text)))
        return WildcardQuery(Term(field, text))
    else:
        if has_space(text):
            if span_needed:
                span_clauses = []
                for word in text.split(' '):
                    span_clauses.append(SpanTermQuery(Term(field, word)))

                return SpanNearQuery(span_clauses, 0, True)
            return PhraseQuery(field, *text.split(' '))
        else:
            if span_needed:
                return SpanTermQuery(Term(field, text))
            return TermQuery(Term(field, text))


def tashkeel_query(text, field, analyzer, span_needed):

    def wordToregex(word):
        final = ''
        for i in word:
            final = f"{final}{i}╦"

        return final.replace('*', '.*').replace('?', '.').replace('╦', '[ًٌٍَُِّْ]*')

    text = clean_phrase(text, analyzer)
    if text == '':
        return
    has_space = lambda value: ' ' in value
    if has_space(text):
        span_clauses = []
        for word in text.split(' '):
            span_clauses.append(SpanMultiTermQueryWrapper(RegexpQuery(Term(field, wordToregex(word)))))

        return SpanNearQuery(span_clauses, 0, True)
    if span_needed:
        return SpanMultiTermQueryWrapper(RegexpQuery(Term(field, wordToregex(text))))
    return RegexpQuery(Term(field, wordToregex(text)))


def filterBooks(text, complete_source, full_scope=None, status=None):
    if not text:
        return full_scope or complete_source
    if not status:
        status = 0
    if status == 2:
        index_name = 'book'
        field = 'body'
    else:
        index_name = 's_book'
        field = 'single' if status == 0 else 'double'
    info = buildFilter(text, False)
    query = ConstantScoreQuery(fieldsQuery([field], info, False))
    with Index.lease(index_name) as (searcher):
        results = intCollectingSearch(searcher, query)
    return [book_id for book_id in complete_source if book_id in results]


def filterAuthors(text, authors_dict):
    if not text:
        return list(authors_dict.items())
    info = buildFilter(text, False)
    query = ConstantScoreQuery(fieldsQuery(['author'], info, False))
    with Index.lease('s_author') as (searcher):
        results = intCollectingSearch(searcher, query)
    return [[author_id, authors_dict[author_id]] for author_id in authors_dict if author_id in results]


def fieldsQuery(ofields, info, is_final, affirm_only=False):
    analyzer = getAnalyzer(info, is_final)
    and_panels, or_panels, not_panels = info['phrases']
    if info['stemmed']:
        func = stemmed_query
    else:
        func = tashkeel_query if (info['diacritics'] and is_final) else phrase_query
    numbers = info['numbers']
    fields = [f"n_{ofield}" if numbers and not is_final else ofield for ofield in ofields]
    or_split = numbers and not is_final
    if or_split:
        is_quran = info.get('type') == QueryType.QURAN.value
        text_analyzer = Analyzer.quran() if is_quran else Analyzer.shamela()
    else:
        affirm = None
        builder = BooleanQuery.Builder()
        if info['is_or']:
            joiner = BooleanClause.Occur.SHOULD
            builder.setMinimumNumberShouldMatch(1)
        else:
            joiner = BooleanClause.Occur.MUST
        and_options = info.get('and_options') or []
        for i, phrases in enumerate(and_panels):
            and_phrases = numberedPhrases(phrases, numbers, is_final)
            if and_phrases:
                affirm = True
                try:
                    near, ordered = and_options[i]
                except (IndexError, TypeError, ValueError):
                    near, ordered = (0, False)

                if (len(and_phrases) == 1 or near) == 0:
                    if not ordered:
                        builder.add(sAndQuery(and_phrases, fields, analyzer, func), joiner)
                builder.add(andQuery(and_phrases, fields, ordered, near, analyzer, func), joiner)

        for phrases in or_panels:
            if or_split:
                query = splitFieldQuery(phrases, ofields, fields, text_analyzer, analyzer, func)
                if query is not None:
                    affirm = True
                    builder.add(query, joiner)
                    continue
                or_phrases = numberedPhrases(phrases, numbers, is_final)
                if or_phrases:
                    affirm = True
                    builder.add(orQuery(or_phrases, fields, analyzer, func), joiner)

        if (affirm_only or info)['is_or']:
            for phrases in not_panels:
                not_phrases = numberedPhrases(phrases, numbers, is_final)
                if not_phrases:
                    builder.add(notQuery(not_phrases, fields, analyzer, func), joiner)

        else:
            for phrases in not_panels:
                not_phrases = numberedPhrases(phrases, numbers, is_final)
                if not_phrases:
                    dNotQuery(builder, not_phrases, fields, analyzer, func, affirm)

    return builder.build()


def splitFieldQuery(phrases, text_fields, num_fields, text_analyzer, num_analyzer, func):
    """First-pass OR-panel candidate query for numbers mode.

    Words and numbers are indexed in different fields (text vs n_*), so the panel
    is built as two OR sub-queries — words against text_fields, numbers against
    num_fields — then OR-ed together, so a doc matching only the word or only the
    number is still collected. The in-memory second pass is the precise judge.
    Returns None when the panel yields neither a word nor a number part.
    """
    parts = []
    word_phrases = numberedPhrases(phrases, False, False)
    if word_phrases:
        parts.append(orQuery(word_phrases, text_fields, text_analyzer, func))
    else:
        num_phrases = numberedPhrases(phrases, True, False)
        if num_phrases:
            parts.append(orQuery(num_phrases, num_fields, num_analyzer, func))
        return parts or None
    if len(parts) == 1:
        return parts[0]
    builder = BooleanQuery.Builder()
    builder.setMinimumNumberShouldMatch(1)
    for part in parts:
        builder.add(part, BooleanClause.Occur.SHOULD)

    return builder.build()


def sAndQuery(phrases, fields, analyzer, func):
    """simplified [and] query while we can find result even if one phrase is in
    the body and the other is in foot. This can be done if no span is required
    """
    if len(phrases) == 1:
        if len(fields) == 1:
            return func(phrases[0], fields[0], analyzer, False)
        field_builder = BooleanQuery.Builder()
        field_builder.setMinimumNumberShouldMatch(1)
        for field in fields:
            field_builder.add(func(phrases[0], field, analyzer, False), BooleanClause.Occur.SHOULD)

        return field_builder.build()
    else:
        phrase_builder = BooleanQuery.Builder()
        for phrase in phrases:
            if len(fields) == 1:
                query = func(phrase, fields[0], analyzer, False)
            else:
                field_builder = BooleanQuery.Builder()
                field_builder.setMinimumNumberShouldMatch(1)
                for field in fields:
                    field_builder.add(func(phrase, field, analyzer, False), BooleanClause.Occur.SHOULD)

                query = field_builder.build()
            phrase_builder.add(query, BooleanClause.Occur.MUST)

        return phrase_builder.build()


def andQuery(phrases, fields, ordered, near, analyzer, func):
    if len(fields) == 1 and not near != 0:
        if ordered:
            span_clauses = []
            for phrase in phrases:
                if phrase:
                    span_clauses.append(func(phrase, fields[0], analyzer, True))

            return SpanNearQuery(span_clauses, near or JInteger.MAX_VALUE, ordered)
        builder = BooleanQuery.Builder()
        for phrase in phrases:
            if phrase:
                builder.add(func(phrase, fields[0], analyzer, False), BooleanClause.Occur.MUST)

        return builder.build()
    else:
        field_builder = BooleanQuery.Builder()
        field_builder.setMinimumNumberShouldMatch(1)
        for field in fields:
            if near != 0 or ordered:
                span_clauses = []
                for phrase in phrases:
                    if phrase:
                        span_clauses.append(func(phrase, field, analyzer, True))

                query = SpanNearQuery(span_clauses, near or JInteger.MAX_VALUE, ordered)
            else:
                builder = BooleanQuery.Builder()
                for phrase in phrases:
                    if phrase:
                        builder.add(func(phrase, field, analyzer, False), BooleanClause.Occur.MUST)

                query = builder.build()
            field_builder.add(query, BooleanClause.Occur.SHOULD)

        return field_builder.build()


def orQuery(phrases, fields, analyzer, func):
    builder = BooleanQuery.Builder()
    builder.setMinimumNumberShouldMatch(1)
    for phrase in phrases:
        if phrase:
            for field in fields:
                builder.add(func(phrase, field, analyzer, False), BooleanClause.Occur.SHOULD)

    return builder.build()


def notQuery(phrases, fields, analyzer, func):
    builder = BooleanQuery.Builder()
    builder.add(QueryParser('', Analyzer.white()).parse('*:*'), BooleanClause.Occur.MUST)
    for phrase in phrases:
        if phrase:
            for field in fields:
                builder.add(func(phrase, field, analyzer, False), BooleanClause.Occur.MUST_NOT)

    return builder.build()


def dNotQuery(builder, phrases, fields, analyzer, func, affirm):
    if not affirm:
        builder.add(QueryParser('', Analyzer.white()).parse('*:*'), BooleanClause.Occur.MUST)
    for phrase in phrases:
        if phrase:
            for field in fields:
                builder.add(func(phrase, field, analyzer, False), BooleanClause.Occur.MUST_NOT)


def numberedPhrases(phrases, is_numbers, is_final):

    def filterNumbers(phrase_list, regexp):
        new_list = []
        for phrase in phrase_list:
            new_phrase = re.sub(regexp, ' ', phrase).strip()
            new_phrase = f" {new_phrase} ".replace(' * ', ' ')
            new_phrase = re.sub(' +', ' ', new_phrase).strip()
            if new_phrase:
                new_list.append(new_phrase)

        return new_list

    if is_numbers:
        if is_final:
            return phrases
        return filterNumbers(phrases, '\\D+')
    return filterNumbers(phrases, '\\d+')


def sortBy(fields=None):
    if not fields:
        return Sort.INDEXORDER
    if len(fields) == 1:
        return Sort(SortField(fields[0], SortField.Type.INT))
    return Sort(*map((lambda field: SortField(field, SortField.Type.INT)), fields))


def term_in_set_query(field, values):
    refs = [BytesRef((f"{value}")) for value in values]
    if LUCENE_ONE:
        return TermInSetQuery(field, *refs)
    ref_list = JList()
    for ref in refs:
        ref_list.add(ref)

    return TermInSetQuery(field, ref_list)


def buildFilter(text, successive):

    def wild(s):
        s = re.sub('\\b[اآإأ]بن\\b', 'بن', s)
        return re.sub('\\*+', '*', f"*{s}*")

    if successive:
        phrases = [
         wild(text)]
    else:
        phrases = [wild(word) for word in text.split()]
    return {'is_or':False, 
     'stemmed':False,  'hamza':False,  'diacritics':False,  'numbers':False,  'phrases':[
      [
       phrases], [], []], 
     'snippet_phrases':[[phrases], [], []],  'and_options':[[0, False]]}


def getSubtitles(book_id, parent_id):
    from cache import HonorificCache
    hits_limit = 250000
    query = BooleanQuery.Builder()
    query.add(TermQuery(Term('book_key', (f"{book_id}"))), BooleanClause.Occur.MUST)
    query.add(TermQuery(Term('parent', (f"{parent_id}"))), BooleanClause.Occur.MUST)
    query = ConstantScoreQuery(query.build())
    result = {}
    with Index.lease('title') as (searcher):
        for _id, fields in bulkQueryRows(searcher, query, ['body'], hits_limit, Sort.INDEXORDER):
            title_id = int(_id.split('-')[1])
            result[title_id] = fields[0].translate(HonorificCache.plainTable())

    return result


def deleteBooks(book_ids):
    from dbmanager import keepComments
    query = ConstantScoreQuery(scopeQuery(book_ids))
    if not keepComments(getComments(query)):
        return
    Index.writer('page').deleteDocuments(query)
    Index.writer('title').deleteDocuments(query)
    Index.writer('esnad').deleteDocuments(query)
    Index.commit('page')
    Index.commit('title')
    Index.commit('esnad')
    return True


class PageText:

    def __init__(self, book_id, page_id):
        self._book_id = book_id
        self._page_id = page_id
        self._body = self._foot = self._comment = None
        self._scanned = False

    def _getContent(self):
        if not self._scanned:
            values = getFields('page', ['body', 'foot', 'comment'], f"{self._book_id}-{self._page_id}")
            self._body, self._foot, self._comment = [f"{value or ''}" for value in values]
            self._scanned = True

    def body(self):
        self._getContent()
        return self._body

    def foot(self):
        self._getContent()
        return self._foot

    def comment(self):
        self._getContent()
        return self._comment


def addPatchIndex(leaf, directory):
    """Fold a downloaded book's patch index into one of the shared indices.

    addIndexes(Directory) is a plain file copy, so a patch built by the Lucene 9
    bridge lands as a Lucene 9 segment and only becomes current if some later
    merge happens to rewrite it.  On a large library that wait can be
    indefinite: TieredMergePolicy stops considering segments once they approach
    maxMergedSegmentMB, so the biggest segments -- the ones carrying most of the
    text -- are the least likely to ever be picked up.

    The CodecReader overload re-encodes the patch with this writer's codec
    instead, so it arrives already current and the index never accumulates
    stale-format segments in the first place.  The cost is re-encoding one
    book's postings rather than copying them, which is not measurable beside
    extracting and importing the package around it.

    Under a Lucene 9 runtime there is nothing to re-encode into -- patch and
    index share one codec -- so the cheap copy is kept.
    """
    writer = Index.writer(leaf)
    if LUCENE_ONE:
        writer.addIndexes([directory])
        return
    reader = DirectoryReader.open(directory)
    try:
        leaves = list(reader.leaves())
        readers = JArray(CodecReader.resolve())(len(leaves))
        for position, context in enumerate(leaves):
            readers[position] = SlowCodecReaderWrapper.wrap(context.reader())

        writer.addIndexes(readers)
    finally:
        reader.close()


class Book:

    def __init__(self, book_id):
        self.book_id = book_id
        self._doc = None
        self._esnadDoc = None

    def _getEsnadDoc(self):
        if not self._esnadDoc:
            self._esnadDoc = LuceneDocument()
            self._esnadDoc.add(Field('id', FieldType.ID, '').field())
            self._esnadDoc.add(Field('book_key', FieldType.KEY, (f"{self.book_id}")).field())
            self._esnadDoc.add(Field('hadeeth', FieldType.ID, '').field())
            self._esnadDoc.add(Field('esnad', FieldType.TEXT, '').field())
        return self._esnadDoc

    def addAsaneed(self, page_id, asaneed):
        _id = f"{self.book_id}-{page_id}"
        Index.writer('esnad').deleteDocuments(Term('id', _id))
        for esnad in asaneed:
            doc = self._getEsnadDoc()
            pieces = esnad.split(' ')
            hadeeth = f"{int(pieces[0])}"
            esnad = ' '.join(pieces[2:])
            Field('id', FieldType.ID, _id).field()
            Field('hadeeth', FieldType.ID, hadeeth).field()
            Field('esnad', FieldType.TEXT, esnad).field()
            Index.writer('esnad').addDocument(doc)

    def _getDoc(self):
        from dbmanager import CoreDb
        if self._doc:
            for field in ('body', 'foot', 'comment', 'm_body', 'm_foot', 'm_comment',
                          'n_body', 'n_foot', 'n_comment', 'parent'):
                self._doc.removeField(field)

        else:
            self._doc = LuceneDocument()
            sorter = CoreDb().sorter(self.book_id)
            self._doc.add(Field('id', FieldType.ID, '').field())
            self._doc.add(Field('book_key', FieldType.KEY, (f"{self.book_id}")).field())
            self._doc.add(Field('date', FieldType.ORD, sorter['date']).field())
            self._doc.add(Field('author', FieldType.ORD, sorter['author']).field())
            if sorter['book_up']:
                self._doc.add(Field('book_up', FieldType.ORD, sorter['book_up']).field())
            if sorter['group']:
                self._doc.add(Field('group', FieldType.ORD, sorter['group']).field())
            if sorter['group_order']:
                self._doc.add(Field('group_order', FieldType.ORD, sorter['group_order']).field())
            self._doc.add(Field('book', FieldType.ORD, self.book_id).field())
            self._doc.add(Field('page', FieldType.ORD, 0).field())
        return self._doc

    def updatePage(self, page_id, content_dict):
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
        else:
            current_doc = None
            with Index.lease('page') as (_searcher):
                current_doc = getDoc(_searcher, f"{self.book_id}-{page_id}")
            if current_doc:
                for field in ('body', 'foot', 'comment'):
                    if field not in content_dict:
                        value = current_doc.get(field)
                        if value:
                            content_dict[field] = f"{value}"

            empty = True
            for field in ('body', 'foot', 'comment'):
                if field in content_dict and content_dict[field]:
                    empty = False
                    break

            writer = Index.writer('page')
            if empty:
                writer.deleteDocuments(Term('id', f"{self.book_id}-{page_id}"))
            else:
                doc = self._getDoc()
                Field('id', FieldType.ID, f"{self.book_id}-{page_id}").field()
                Field('page', FieldType.ORD, page_id).field()
                for field in ('body', 'foot', 'comment'):
                    if field in content_dict and content_dict[field]:
                        doc.add(Field(field, FieldType.TEXT, content_dict[field]).field())
                        doc.add(Field(f"m_{field}", FieldType.ANALYSE, content_dict[field]).field())
                        n_field = re.sub('\\D+', ' ', content_dict[field]).strip()
                        if n_field:
                            doc.add(Field(f"n_{field}", FieldType.ANALYSE, n_field).field())

                writer.updateDocument(Term('id', f"{self.book_id}-{page_id}"), doc)

    def updateTitle(self, page_id, title_dict):
        current_doc = None
        with Index.lease('title') as (_searcher):
            current_doc = getDoc(_searcher, f"{self.book_id}-{page_id}")
        if current_doc:
            if 'body' not in title_dict:
                value = current_doc.get('body')
                if value:
                    title_dict['body'] = f"{value}"
            title_dict['body'] = title_dict['body']
        writer = Index.writer('title')
        doc = self._getDoc()
        Field('id', FieldType.ID, f"{self.book_id}-{page_id}").field()
        Field('page', FieldType.ORD, page_id).field()
        if 'body' in title_dict:
            doc.add(Field('body', FieldType.TEXT, title_dict['body']).field())
            doc.add(Field('m_body', FieldType.ANALYSE, title_dict['body']).field())
            n_field = re.sub('\\D+', ' ', title_dict['body']).strip()
            if n_field:
                doc.add(Field('n_body', FieldType.ANALYSE, n_field).field())
        if 'parent' in title_dict:
            doc.add(Field('parent', FieldType.KEY, (f"{title_dict['parent']}")).field())
        writer.updateDocument(Term('id', f"{self.book_id}-{page_id}"), doc)

    def getPart(self, min_id, max_id):
        from dbmanager import BookDb
        pages_dict = {}
        footnotes_dict = {}
        locations = set()
        for page_id in list(range(min_id, max_id + 1)):
            locations.add(f"{self.book_id}-{page_id}")

        book_db = BookDb(self.book_id)
        map_dict = book_db.getAliases(min_id, max_id) if book_db.hasAlias() else {}
        for key in map_dict:
            locations.discard(map_dict[key])
            locations.add(key)

        query = term_in_set_query('id', locations)
        if LUCENE_ONE:
            hits_limit = 250000
            with Index.lease('page') as (searcher):
                hits = searcher.search(query, hits_limit, sortBy(), False).scoreDocs
                results = []
                while True:
                    if hits:
                        results += [[(f"{doc.get('id')}"), (f"{doc.get('body') or ''}"), (f"{doc.get('foot') or ''}")] for doc in [searcher.doc(hit.doc) for hit in hits]]
                        if len(hits) < hits_limit:
                            break
                        last_doc = hits[-1]
                        hits = searcher.searchAfter(last_doc, query, hits_limit, sortBy(), False).scoreDocs
                    else:
                        break

            for location, body, foot in results:
                page_id = int(map_dict[location].split('-')[1]) if location in map_dict else int(location.split('-')[1])
                if body:
                    pages_dict[page_id] = body
                if foot:
                    footnotes_dict[page_id] = foot

            return (
             pages_dict, footnotes_dict)
        with Index.lease('page') as (searcher):
            results = bulkQueryRows(searcher, query, ['body', 'foot'], 250000, sortBy())
        for location, fields in results:
            body, foot = fields
            page_id = int(map_dict[location].split('-')[1]) if location in map_dict else int(location.split('-')[1])
            if body:
                pages_dict[page_id] = body
            if foot:
                footnotes_dict[page_id] = foot

        return (
         pages_dict, footnotes_dict)

    def inject(self, patch_path):
        from dbmanager import BookDb
        try:
            for leaf in ('page', 'title'):
                directory = FSDirectory.open(Paths.get(os.path.join(patch_path, leaf)))
                try:
                    addPatchIndex(leaf, directory)
                    Index.commit(leaf)
                finally:
                    directory.close()

            book_db = BookDb(self.book_id)
            if not self.addComments(book_db.mappedComments()):
                return
            self.commitBook()
            return book_db.commentsImported()
        except Exception:
            traceback.print_exc()
            return

    def addComments(self, comments):
        try:
            for page_id, comment in comments:
                self.updatePage(page_id, {'comment': comment})

            return True
        except Exception:
            traceback.print_exc()
            return

    def commitBook(self):
        Index.commit('page')
        Index.commit('title')
        Index.commit('esnad')

    def __del__(self):
        self.commitBook()


def intCollectingSearch(searcher, query, sort_fields=None):
    if LUCENE_ONE:
        hits_limit = 250000
        results = []
        sorts = sortBy(sort_fields)
        hits = searcher.search(query, hits_limit, sorts, False).scoreDocs
        while True:
            if hits:
                batch = [int((f"{searcher.doc(hit.doc).get('id')}")) for hit in hits]
                results += batch
                if len(batch) < hits_limit:
                    break
                last_doc = hits[-1]
                hits = searcher.searchAfter(last_doc, query, hits_limit, sorts, False).scoreDocs
            else:
                break

        return results
    return [int(_id) for _id in bulkQueryIds(searcher, query, 250000, sortBy(sort_fields))]


def getElement(key, _id):
    if key == 'bibliography':
        return getField('book', 'body_store', _id)
    if key == 'biography':
        return getField('author', 'body_store', _id)
    if key == 'hint':
        return getField('book', 'hint', _id)
    if key == 'amiri':
        return getField('aya', 'amiri', _id)
    if key == 'majma':
        return getField('aya', 'majma', _id)
    if key == 'emlaa':
        return getField('aya', 'body', _id)


def getTitle(book_id, title_id):
    from cache import HonorificCache
    value = getField('title', 'body', f"{book_id}-{title_id}")
    if value:
        return value.translate(HonorificCache.plainTable())
    return ''


def getField(index_name, field, _id):
    try:
        with Index.lease(index_name) as (searcher):
            if LUCENE_ONE:
                doc = getDoc(searcher, (f"{_id}"))
                if doc:
                    return (f"{doc.get(field) or ''}")
                return
            value = javaBulkField(searcher, _id, field)
            if value is not None:
                return (f"{value or ''}")
            return
    except Exception:
        return


def getFields(index_name, field_list, _id):
    try:
        with Index.lease(index_name) as (searcher):
            if LUCENE_ONE:
                doc = getDoc(searcher, (f"{_id}"))
                if doc:
                    return [f"{doc.get(field) or ''}" for field in field_list]
                return [
                 None] * len(field_list)
            return javaBulkFields(searcher, _id, field_list)
    except Exception:
        return [
         None] * len(field_list)


def fetchDoc(searcher, doc_id):
    if LUCENE_ONE:
        return searcher.doc(doc_id)
    return searcher.getIndexReader().storedFields().document(doc_id)


def firstScoreDoc(top_docs):
    score_docs = getattr(top_docs, 'scoreDocs', None)
    if score_docs is None:
        return
    if len(score_docs):
        return score_docs[0]


def getDoc(searcher, _id):
    if LUCENE_ONE:
        hits = searcher.search(ConstantScoreQuery(TermQuery(Term('id', _id))), 1)
        if hits.scoreDocs.length:
            return searcher.doc(hits.scoreDocs[0].doc)
        return
    hits = searcher.search(ConstantScoreQuery(TermQuery(Term('id', _id))), 1)
    score_doc = firstScoreDoc(hits)
    if score_doc is not None:
        return fetchDoc(searcher, score_doc.doc)


def hintIds():
    query = ConstantScoreQuery(WildcardQuery(Term('hint', '*')))
    with Index.lease('book') as (searcher):
        return intCollectingSearch(searcher, query)


def getAsaneed(man_id):
    query = ConstantScoreQuery(TermQuery(Term('esnad', (f"{man_id}"))))
    return esnadQuery(query)


def getTorok(hadeeth_id):
    query = ConstantScoreQuery(TermQuery(Term('hadeeth', (f"{hadeeth_id}"))))
    return esnadQuery(query)


def esnadQuery(query):
    with Index.lease('esnad') as (searcher):
        if LUCENE_ONE:
            hits_limit = 250000
            results = []
            hits = searcher.search(query, hits_limit, Sort.INDEXORDER, False).scoreDocs
            while True:
                if hits:
                    for hit in hits:
                        doc = searcher.doc(hit.doc)
                        pieces = (f"{doc.get('id')}").split('-')
                        results.append([int(pieces[0]), int(pieces[1]), (f"{doc.get('esnad')}")])

                    if len(hits) < hits_limit:
                        break
                    last_doc = hits[-1]
                    hits = searcher.searchAfter(last_doc, query, hits_limit, Sort.INDEXORDER, False).scoreDocs
                else:
                    break

            return results
        results = []
        for _id, fields in bulkQueryRows(searcher, query, ['esnad'], 250000, Sort.INDEXORDER):
            pieces = _id.split('-')
            results.append([int(pieces[0]), int(pieces[1]), fields[0]])

        return results


def getTaraf(book_id, page_id):
    from textmanager import plain, linear
    text = PageText(book_id, page_id)
    if '<hadeeth>' in text.body():
        target = text.body()
    else:
        if '<hadeeth>' in text.foot():
            target = text.foot()
        else:
            if text.body():
                target = text.body()
            else:
                if text.foot():
                    target = text.foot()
                else:
                    return ''
    match = re.findall('(?<=<hadeeth-\\d+>)([\\s\\S]+?)(?=<hadeeth>)', target)
    taraf = match[0].replace('«', '').replace('»', '').strip() or target if match else target
    return plain(linear(taraf))


class Basmala:
    _basmala = {}

    def inRasm(rasm):
        if rasm not in Basmala._basmala:
            Basmala._basmala[rasm] = getElement(rasm, 1)
        return Basmala._basmala[rasm]


def collectQuranPage(page_number, rasm, search_info, aya_id):
    from quraninfo import ayat_fromPage
    AYAT_MAX = 6236
    PRE = '<span id=go class="search">&#8204;'
    POST = '</span>'

    def highightAya(text, rasm=None):

        def reformateAya(emlaee, osthmani):
            osthmani = osthmani.split()
            emlaee = emlaee.split()
            for i, emlaee in enumerate(emlaee):
                if emlaee.startswith('|'):
                    osthmani[i] = f"{PRE}{osthmani[i]}"
                if emlaee.endswith('|'):
                    osthmani[i] = f"{osthmani[i]}{POST}"

            return ' '.join(osthmani)

        info = dict(search_info)
        info['phrases'] = info['snippet_phrases']
        analyzer = getAnalyzer(info, True)
        query = ConstantScoreQuery(fieldsQuery([''], info, True))
        stream = analyzer.tokenStream(None, text)
        pre, post = ('|', '|') if rasm else (PRE, POST)
        highlighter = Highlighter(SimpleHTMLFormatter(pre, post), QueryScorer(query))
        highlighter.setMaxDocCharsToAnalyze(JInteger.MAX_VALUE)
        highlighter.setTextFragmenter(NullFragmenter())
        fragment = highlighter.getBestFragment(stream, text)
        if fragment:
            if rasm:
                return reformateAya((f"{fragment}"), rasm)
            return (f"{fragment}")
        else:
            return rasm or text

    def collectAyat(searcher, query, field, body_required):
        if LUCENE_ONE:
            hits_limit = AYAT_MAX
            ayat = {}
            body = {}
            hits = searcher.search(query, hits_limit, Sort.INDEXORDER, False).scoreDocs
            for hit in hits:
                doc = searcher.doc(hit.doc)
                aya_id = int((f"{doc.get('id')}"))
                ayat[aya_id] = f"{doc.get(field)}"
                if body_required:
                    body[aya_id] = f"{doc.get('body')}"

            return (
             ayat, body)
        ayat = {}
        body = {}
        fields = [field, 'body'] if body_required else [field]
        for _id, values in bulkQueryRows(searcher, query, fields, AYAT_MAX, Sort.INDEXORDER):
            aya_id = int(_id)
            ayat[aya_id] = values[0]
            if body_required:
                body[aya_id] = values[1]

        return (
         ayat, body)

    field = 'body' if rasm == 'emlaa' else rasm
    paga_ayat = ayat_fromPage(page_number)
    range_query = term_in_set_query('id', paga_ayat)
    body_required = search_info and search_info['phrases'] and rasm != 'emlaa'
    with Index.lease('aya') as (_aya_searcher):
        ayat, body = collectAyat(_aya_searcher, range_query, field, body_required)
    if search_info:
        if search_info['phrases']:
            if rasm == 'emlaa':
                body = ayat
            for _id in ayat:
                if not aya_id or _id == aya_id:
                    ayat[_id] = highightAya(body[_id], ayat[_id] if rasm != 'emlaa' else None)

    return sorted(ayat.items())


class Importer:

    @staticmethod
    def commitAuthors():
        Index.commit('s_author')
        Index.commit('author')

    @staticmethod
    def commitBookMeta():
        Index.commit('s_book')
        Index.commit('book')

    @staticmethod
    def commitBooks():
        for index in ('author', 's_author', 'book', 's_book', 'page', 'title'):
            Index.commit(index)

    @staticmethod
    def commitPages():
        Index.commit('page')
        Index.commit('title')

    @classmethod
    def addAuthor(cls, author_dict):
        index_name = 'author'
        writer = Index.writer(index_name)
        short_writer = Index.writer(f"s_{index_name}")
        short_doc = LuceneDocument()
        doc = LuceneDocument()
        author_id = author_dict['id']
        s_author_id = f"{author_id}"
        if 'name' in author_dict:
            short_doc.add(Field('id', FieldType.ID, s_author_id).field())
            short_doc.add(Field('author', FieldType.ANALYSE, author_dict['name']).field())
            short_writer.updateDocument(Term('id', s_author_id), short_doc)
        if 'name' in author_dict or 'biography' in author_dict:
            author_name = author_dict['name'] if 'name' in author_dict else author_dict['db_name']
            author_death = author_dict['date'] if 'date' in author_dict else author_dict['db_date']
            biography = author_dict['biography'] if 'biography' in author_dict else getField('author', 'body_store', s_author_id)
            analyzed_biography = f"{author_name} {biography}" if biography else author_name
            doc.add(Field('id', FieldType.ID, s_author_id).field())
            doc.add(Field('date', FieldType.ORD, author_death).field())
            doc.add(Field('author_id', FieldType.ORD, author_id).field())
            doc.add(Field('body', FieldType.ANALYSE, analyzed_biography).field())
            doc.add(Field('m_body', FieldType.ANALYSE, analyzed_biography).field())
            if biography:
                doc.add(Field('body_store', FieldType.STORE, biography).field())
                n_field = re.sub('\\D+', ' ', biography).strip()
                if n_field:
                    doc.add(Field('n_body', FieldType.ANALYSE, n_field).field())
                writer.updateDocument(Term('id', s_author_id), doc)
            else:
                pass
        if 'date' in author_dict:
            writer.updateNumericDocValue(Term('id', s_author_id), 'date', author_dict['date'])

    @classmethod
    def addBook--- This code section failed: ---

 L.2225         0  LOAD_CLOSURE             'book_dict'
                2  BUILD_TUPLE_1         1 
                4  LOAD_CODE                <code_object fetch>
                6  LOAD_STR                 'Importer.addBook.<locals>.fetch'
                8  MAKE_FUNCTION_8          'closure'
               10  STORE_FAST               'fetch'

 L.2228        12  LOAD_STR                 'book'
               14  STORE_FAST               'index_name'

 L.2229        16  LOAD_GLOBAL              Index
               18  LOAD_METHOD              writer
               20  LOAD_FAST                'index_name'
               22  CALL_METHOD_1         1  '1 positional argument'
               24  STORE_FAST               'writer'

 L.2230        26  LOAD_GLOBAL              Index
               28  LOAD_METHOD              writer
               30  LOAD_STR                 's_'
               32  LOAD_FAST                'index_name'
               34  FORMAT_VALUE          0  ''
               36  BUILD_STRING_2        2 
               38  CALL_METHOD_1         1  '1 positional argument'
               40  STORE_FAST               'short_writer'

 L.2231        42  LOAD_GLOBAL              LuceneDocument
               44  CALL_FUNCTION_0       0  '0 positional arguments'
               46  STORE_FAST               'short_doc'

 L.2232        48  LOAD_GLOBAL              LuceneDocument
               50  CALL_FUNCTION_0       0  '0 positional arguments'
               52  STORE_FAST               'doc'

 L.2234        54  LOAD_DEREF               'book_dict'
               56  LOAD_STR                 'id'
               58  BINARY_SUBSCR    
               60  STORE_FAST               'book_id'

 L.2235        62  LOAD_FAST                'book_id'
               64  FORMAT_VALUE          0  ''
               66  STORE_FAST               's_book_id'

 L.2237        68  LOAD_FAST                'fetch'
               70  LOAD_STR                 'name'
               72  CALL_FUNCTION_1       1  '1 positional argument'
               74  LOAD_FAST                'fetch'
               76  LOAD_STR                 'author_names'
               78  CALL_FUNCTION_1       1  '1 positional argument'
               80  ROT_TWO          
               82  STORE_FAST               'name'
               84  STORE_FAST               'author_names'

 L.2238        86  LOAD_FAST                'fetch'
               88  LOAD_STR                 'book_up'
               90  CALL_FUNCTION_1       1  '1 positional argument'
               92  LOAD_FAST                'fetch'
               94  LOAD_STR                 'group'
               96  CALL_FUNCTION_1       1  '1 positional argument'
               98  LOAD_FAST                'fetch'
              100  LOAD_STR                 'group_order'
              102  CALL_FUNCTION_1       1  '1 positional argument'
              104  ROT_THREE        
              106  ROT_TWO          
              108  STORE_FAST               'book_up'
              110  STORE_FAST               'group'
              112  STORE_FAST               'group_order'

 L.2240       114  LOAD_STR                 'name'
              116  LOAD_DEREF               'book_dict'
              118  COMPARE_OP               in
              120  POP_JUMP_IF_TRUE    130  'to 130'
              122  LOAD_STR                 'author_names'
              124  LOAD_DEREF               'book_dict'
              126  COMPARE_OP               in
              128  POP_JUMP_IF_FALSE   230  'to 230'
            130_0  COME_FROM           120  '120'

 L.2241       130  LOAD_FAST                'short_doc'
              132  LOAD_METHOD              add
              134  LOAD_GLOBAL              Field
              136  LOAD_STR                 'id'
              138  LOAD_GLOBAL              FieldType
              140  LOAD_ATTR                ID
              142  LOAD_FAST                's_book_id'
              144  CALL_FUNCTION_3       3  '3 positional arguments'
              146  LOAD_METHOD              field
              148  CALL_METHOD_0         0  '0 positional arguments'
              150  CALL_METHOD_1         1  '1 positional argument'
              152  POP_TOP          

 L.2242       154  LOAD_FAST                'short_doc'
              156  LOAD_METHOD              add
              158  LOAD_GLOBAL              Field
              160  LOAD_STR                 'single'
              162  LOAD_GLOBAL              FieldType
              164  LOAD_ATTR                ANALYSE
              166  LOAD_FAST                'name'
              168  CALL_FUNCTION_3       3  '3 positional arguments'
              170  LOAD_METHOD              field
              172  CALL_METHOD_0         0  '0 positional arguments'
              174  CALL_METHOD_1         1  '1 positional argument'
              176  POP_TOP          

 L.2243       178  LOAD_FAST                'short_doc'
              180  LOAD_METHOD              add
              182  LOAD_GLOBAL              Field
              184  LOAD_STR                 'double'
              186  LOAD_GLOBAL              FieldType
              188  LOAD_ATTR                ANALYSE
              190  LOAD_FAST                'name'
              192  FORMAT_VALUE          0  ''
              194  LOAD_STR                 ' '
              196  LOAD_FAST                'author_names'
              198  FORMAT_VALUE          0  ''
              200  BUILD_STRING_3        3 
              202  CALL_FUNCTION_3       3  '3 positional arguments'
              204  LOAD_METHOD              field
              206  CALL_METHOD_0         0  '0 positional arguments'
              208  CALL_METHOD_1         1  '1 positional argument'
              210  POP_TOP          

 L.2244       212  LOAD_FAST                'short_writer'
              214  LOAD_METHOD              updateDocument
              216  LOAD_GLOBAL              Term
              218  LOAD_STR                 'id'
              220  LOAD_FAST                's_book_id'
              222  CALL_FUNCTION_2       2  '2 positional arguments'
              224  LOAD_FAST                'short_doc'
              226  CALL_METHOD_2         2  '2 positional arguments'
              228  POP_TOP          
            230_0  COME_FROM           128  '128'

 L.2246       230  LOAD_STR                 'name'
              232  LOAD_DEREF               'book_dict'
              234  COMPARE_OP               in
          236_238  POP_JUMP_IF_TRUE    270  'to 270'
              240  LOAD_STR                 'author_names'
              242  LOAD_DEREF               'book_dict'
              244  COMPARE_OP               in
          246_248  POP_JUMP_IF_TRUE    270  'to 270'
              250  LOAD_STR                 'bibliography'
              252  LOAD_DEREF               'book_dict'
              254  COMPARE_OP               in
          256_258  POP_JUMP_IF_TRUE    270  'to 270'
              260  LOAD_STR                 'hint'
              262  LOAD_DEREF               'book_dict'
              264  COMPARE_OP               in
          266_268  POP_JUMP_IF_FALSE   786  'to 786'
            270_0  COME_FROM           256  '256'
            270_1  COME_FROM           246  '246'
            270_2  COME_FROM           236  '236'

 L.2247       270  LOAD_STR                 'bibliography'
              272  LOAD_DEREF               'book_dict'
              274  COMPARE_OP               in
          276_278  POP_JUMP_IF_FALSE   288  'to 288'
              280  LOAD_DEREF               'book_dict'
              282  LOAD_STR                 'bibliography'
              284  BINARY_SUBSCR    
              286  JUMP_FORWARD        298  'to 298'
            288_0  COME_FROM           276  '276'
              288  LOAD_GLOBAL              getField
              290  LOAD_STR                 'book'
              292  LOAD_STR                 'body_store'
              294  LOAD_FAST                's_book_id'
              296  CALL_FUNCTION_3       3  '3 positional arguments'
            298_0  COME_FROM           286  '286'
              298  STORE_FAST               'biblio'

 L.2248       300  LOAD_STR                 'hint'
              302  LOAD_DEREF               'book_dict'
              304  COMPARE_OP               in
          306_308  POP_JUMP_IF_FALSE   318  'to 318'
              310  LOAD_DEREF               'book_dict'
              312  LOAD_STR                 'hint'
              314  BINARY_SUBSCR    
              316  JUMP_FORWARD        328  'to 328'
            318_0  COME_FROM           306  '306'
              318  LOAD_GLOBAL              getField
              320  LOAD_STR                 'book'
              322  LOAD_STR                 'hint'
              324  LOAD_FAST                's_book_id'
              326  CALL_FUNCTION_3       3  '3 positional arguments'
            328_0  COME_FROM           316  '316'
              328  STORE_FAST               'hint'

 L.2249       330  LOAD_FAST                'name'
              332  FORMAT_VALUE          0  ''
              334  LOAD_STR                 ' '
              336  LOAD_FAST                'author_names'
              338  FORMAT_VALUE          0  ''
              340  LOAD_STR                 ' '
              342  LOAD_FAST                'biblio'
              344  FORMAT_VALUE          0  ''
              346  BUILD_STRING_5        5 
              348  STORE_FAST               'analyzed_biblio'

 L.2251       350  LOAD_FAST                'doc'
              352  LOAD_METHOD              add
              354  LOAD_GLOBAL              Field
              356  LOAD_STR                 'id'
              358  LOAD_GLOBAL              FieldType
              360  LOAD_ATTR                ID
              362  LOAD_FAST                's_book_id'
              364  CALL_FUNCTION_3       3  '3 positional arguments'
              366  LOAD_METHOD              field
              368  CALL_METHOD_0         0  '0 positional arguments'
              370  CALL_METHOD_1         1  '1 positional argument'
              372  POP_TOP          

 L.2252       374  LOAD_FAST                'doc'
              376  LOAD_METHOD              add
              378  LOAD_GLOBAL              Field
              380  LOAD_STR                 'date'
              382  LOAD_GLOBAL              FieldType
              384  LOAD_ATTR                ORD
              386  LOAD_FAST                'fetch'
              388  LOAD_STR                 'date'
              390  CALL_FUNCTION_1       1  '1 positional argument'
              392  CALL_FUNCTION_3       3  '3 positional arguments'
              394  LOAD_METHOD              field
              396  CALL_METHOD_0         0  '0 positional arguments'
              398  CALL_METHOD_1         1  '1 positional argument'
              400  POP_TOP          

 L.2253       402  LOAD_FAST                'doc'
              404  LOAD_METHOD              add
              406  LOAD_GLOBAL              Field
              408  LOAD_STR                 'author'
              410  LOAD_GLOBAL              FieldType
              412  LOAD_ATTR                ORD
              414  LOAD_FAST                'fetch'
              416  LOAD_STR                 'author'
              418  CALL_FUNCTION_1       1  '1 positional argument'
              420  CALL_FUNCTION_3       3  '3 positional arguments'
              422  LOAD_METHOD              field
              424  CALL_METHOD_0         0  '0 positional arguments'
              426  CALL_METHOD_1         1  '1 positional argument'
              428  POP_TOP          

 L.2255       430  LOAD_FAST                'book_up'
          432_434  POP_JUMP_IF_FALSE   460  'to 460'

 L.2255       436  LOAD_FAST                'doc'
              438  LOAD_METHOD              add
              440  LOAD_GLOBAL              Field
              442  LOAD_STR                 'book_up'
              444  LOAD_GLOBAL              FieldType
              446  LOAD_ATTR                ORD
              448  LOAD_FAST                'book_up'
              450  CALL_FUNCTION_3       3  '3 positional arguments'
              452  LOAD_METHOD              field
              454  CALL_METHOD_0         0  '0 positional arguments'
              456  CALL_METHOD_1         1  '1 positional argument'
              458  POP_TOP          
            460_0  COME_FROM           432  '432'

 L.2256       460  LOAD_FAST                'group'
          462_464  POP_JUMP_IF_FALSE   490  'to 490'

 L.2256       466  LOAD_FAST                'doc'
              468  LOAD_METHOD              add
              470  LOAD_GLOBAL              Field
              472  LOAD_STR                 'group'
              474  LOAD_GLOBAL              FieldType
              476  LOAD_ATTR                ORD
              478  LOAD_FAST                'group'
              480  CALL_FUNCTION_3       3  '3 positional arguments'
              482  LOAD_METHOD              field
              484  CALL_METHOD_0         0  '0 positional arguments'
              486  CALL_METHOD_1         1  '1 positional argument'
              488  POP_TOP          
            490_0  COME_FROM           462  '462'

 L.2257       490  LOAD_FAST                'group_order'
          492_494  POP_JUMP_IF_FALSE   520  'to 520'

 L.2257       496  LOAD_FAST                'doc'
              498  LOAD_METHOD              add
              500  LOAD_GLOBAL              Field
              502  LOAD_STR                 'group_order'
              504  LOAD_GLOBAL              FieldType
              506  LOAD_ATTR                ORD
              508  LOAD_FAST                'group_order'
              510  CALL_FUNCTION_3       3  '3 positional arguments'
              512  LOAD_METHOD              field
              514  CALL_METHOD_0         0  '0 positional arguments'
              516  CALL_METHOD_1         1  '1 positional argument'
              518  POP_TOP          
            520_0  COME_FROM           492  '492'

 L.2259       520  LOAD_FAST                'doc'
              522  LOAD_METHOD              add
              524  LOAD_GLOBAL              Field
              526  LOAD_STR                 'book'
              528  LOAD_GLOBAL              FieldType
              530  LOAD_ATTR                ORD
              532  LOAD_FAST                'book_id'
              534  CALL_FUNCTION_3       3  '3 positional arguments'
              536  LOAD_METHOD              field
              538  CALL_METHOD_0         0  '0 positional arguments'
              540  CALL_METHOD_1         1  '1 positional argument'
              542  POP_TOP          

 L.2260       544  LOAD_FAST                'doc'
              546  LOAD_METHOD              add
              548  LOAD_GLOBAL              Field
              550  LOAD_STR                 'body'
              552  LOAD_GLOBAL              FieldType
              554  LOAD_ATTR                ANALYSE
              556  LOAD_FAST                'analyzed_biblio'
              558  CALL_FUNCTION_3       3  '3 positional arguments'
              560  LOAD_METHOD              field
              562  CALL_METHOD_0         0  '0 positional arguments'
              564  CALL_METHOD_1         1  '1 positional argument'
              566  POP_TOP          

 L.2261       568  LOAD_FAST                'doc'
              570  LOAD_METHOD              add
              572  LOAD_GLOBAL              Field
              574  LOAD_STR                 'm_body'
              576  LOAD_GLOBAL              FieldType
              578  LOAD_ATTR                ANALYSE
              580  LOAD_FAST                'analyzed_biblio'
              582  CALL_FUNCTION_3       3  '3 positional arguments'
              584  LOAD_METHOD              field
              586  CALL_METHOD_0         0  '0 positional arguments'
              588  CALL_METHOD_1         1  '1 positional argument'
              590  POP_TOP          

 L.2262       592  LOAD_FAST                'doc'
              594  LOAD_METHOD              add
              596  LOAD_GLOBAL              Field
              598  LOAD_STR                 'body_store'
              600  LOAD_GLOBAL              FieldType
              602  LOAD_ATTR                STORE
              604  LOAD_FAST                'biblio'
              606  CALL_FUNCTION_3       3  '3 positional arguments'
              608  LOAD_METHOD              field
              610  CALL_METHOD_0         0  '0 positional arguments'
              612  CALL_METHOD_1         1  '1 positional argument'
              614  POP_TOP          

 L.2263       616  LOAD_GLOBAL              re
              618  LOAD_METHOD              sub
              620  LOAD_STR                 '\\D+'
              622  LOAD_STR                 ' '
              624  LOAD_FAST                'biblio'
              626  CALL_METHOD_3         3  '3 positional arguments'
              628  LOAD_METHOD              strip
              630  CALL_METHOD_0         0  '0 positional arguments'
              632  STORE_FAST               'n_field'

 L.2264       634  LOAD_FAST                'n_field'
          636_638  POP_JUMP_IF_FALSE   664  'to 664'

 L.2264       640  LOAD_FAST                'doc'
              642  LOAD_METHOD              add
              644  LOAD_GLOBAL              Field
              646  LOAD_STR                 'n_body'
              648  LOAD_GLOBAL              FieldType
              650  LOAD_ATTR                ANALYSE
              652  LOAD_FAST                'biblio'
              654  CALL_FUNCTION_3       3  '3 positional arguments'
              656  LOAD_METHOD              field
              658  CALL_METHOD_0         0  '0 positional arguments'
              660  CALL_METHOD_1         1  '1 positional argument'
              662  POP_TOP          
            664_0  COME_FROM           636  '636'

 L.2265       664  LOAD_FAST                'hint'
          666_668  POP_JUMP_IF_FALSE   766  'to 766'

 L.2266       670  LOAD_FAST                'doc'
              672  LOAD_METHOD              add
              674  LOAD_GLOBAL              Field
              676  LOAD_STR                 'hint'
              678  LOAD_GLOBAL              FieldType
              680  LOAD_ATTR                TEXT
              682  LOAD_FAST                'hint'
              684  CALL_FUNCTION_3       3  '3 positional arguments'
              686  LOAD_METHOD              field
              688  CALL_METHOD_0         0  '0 positional arguments'
              690  CALL_METHOD_1         1  '1 positional argument'
              692  POP_TOP          

 L.2267       694  LOAD_FAST                'doc'
              696  LOAD_METHOD              add
              698  LOAD_GLOBAL              Field
              700  LOAD_STR                 'm_hint'
              702  LOAD_GLOBAL              FieldType
              704  LOAD_ATTR                ANALYSE
              706  LOAD_FAST                'hint'
              708  CALL_FUNCTION_3       3  '3 positional arguments'
              710  LOAD_METHOD              field
              712  CALL_METHOD_0         0  '0 positional arguments'
              714  CALL_METHOD_1         1  '1 positional argument'
              716  POP_TOP          

 L.2268       718  LOAD_GLOBAL              re
              720  LOAD_METHOD              sub
              722  LOAD_STR                 '\\D+'
              724  LOAD_STR                 ' '
              726  LOAD_FAST                'hint'
              728  CALL_METHOD_3         3  '3 positional arguments'
              730  LOAD_METHOD              strip
              732  CALL_METHOD_0         0  '0 positional arguments'
              734  STORE_FAST               'n_field'

 L.2269       736  LOAD_FAST                'n_field'
          738_740  POP_JUMP_IF_FALSE   766  'to 766'

 L.2269       742  LOAD_FAST                'doc'
              744  LOAD_METHOD              add
              746  LOAD_GLOBAL              Field
              748  LOAD_STR                 'n_hint'
              750  LOAD_GLOBAL              FieldType
              752  LOAD_ATTR                ANALYSE
              754  LOAD_FAST                'n_field'
              756  CALL_FUNCTION_3       3  '3 positional arguments'
              758  LOAD_METHOD              field
              760  CALL_METHOD_0         0  '0 positional arguments'
              762  CALL_METHOD_1         1  '1 positional argument'
              764  POP_TOP          
            766_0  COME_FROM           738  '738'
            766_1  COME_FROM           666  '666'

 L.2270       766  LOAD_FAST                'writer'
              768  LOAD_METHOD              updateDocument
              770  LOAD_GLOBAL              Term
              772  LOAD_STR                 'id'
              774  LOAD_FAST                's_book_id'
              776  CALL_FUNCTION_2       2  '2 positional arguments'
              778  LOAD_FAST                'doc'
              780  CALL_METHOD_2         2  '2 positional arguments'
              782  POP_TOP          
              784  JUMP_FORWARD        858  'to 858'
            786_0  COME_FROM           266  '266'

 L.2273       786  LOAD_GLOBAL              Term
              788  LOAD_STR                 'id'
              790  LOAD_FAST                's_book_id'
              792  CALL_FUNCTION_2       2  '2 positional arguments'
              794  STORE_FAST               'term'

 L.2274       796  SETUP_LOOP          858  'to 858'
              798  LOAD_CONST               ('date', 'author', 'book_up', 'group', 'group_order')
              800  GET_ITER         
            802_0  COME_FROM           812  '812'
              802  FOR_ITER            856  'to 856'
              804  STORE_FAST               'item'

 L.2275       806  LOAD_FAST                'item'
              808  LOAD_DEREF               'book_dict'
              810  COMPARE_OP               in
          812_814  POP_JUMP_IF_FALSE   802  'to 802'

 L.2276       816  SETUP_EXCEPT        840  'to 840'

 L.2276       818  LOAD_FAST                'writer'
              820  LOAD_METHOD              updateNumericDocValue
              822  LOAD_FAST                'term'
              824  LOAD_FAST                'item'
              826  LOAD_DEREF               'book_dict'
              828  LOAD_FAST                'item'
              830  BINARY_SUBSCR    
              832  CALL_METHOD_3         3  '3 positional arguments'
              834  POP_TOP          
              836  POP_BLOCK        
              838  JUMP_BACK           802  'to 802'
            840_0  COME_FROM_EXCEPT    816  '816'

 L.2277       840  POP_TOP          
              842  POP_TOP          
              844  POP_TOP          

 L.2277       846  POP_EXCEPT       
              848  JUMP_BACK           802  'to 802'
              850  END_FINALLY      
          852_854  JUMP_BACK           802  'to 802'
              856  POP_BLOCK        
            858_0  COME_FROM_LOOP      796  '796'
            858_1  COME_FROM           784  '784'

 L.2280       858  LOAD_FAST                'info_only'
          860_862  POP_JUMP_IF_TRUE    968  'to 968'

 L.2281       864  LOAD_GLOBAL              Term
              866  LOAD_STR                 'book_key'
              868  LOAD_FAST                's_book_id'
              870  CALL_FUNCTION_2       2  '2 positional arguments'
              872  STORE_FAST               'term'

 L.2282       874  SETUP_LOOP          968  'to 968'
              876  LOAD_CONST               ('date', 'author', 'book_up', 'group', 'group_order')
              878  GET_ITER         
            880_0  COME_FROM           890  '890'
              880  FOR_ITER            966  'to 966'
              882  STORE_FAST               'item'

 L.2283       884  LOAD_FAST                'item'
              886  LOAD_DEREF               'book_dict'
              888  COMPARE_OP               in
          890_892  POP_JUMP_IF_FALSE   880  'to 880'

 L.2284       894  SETUP_LOOP          962  'to 962'
              896  LOAD_GLOBAL              Index
              898  LOAD_METHOD              writer
              900  LOAD_STR                 'page'
              902  CALL_METHOD_1         1  '1 positional argument'
              904  LOAD_GLOBAL              Index
              906  LOAD_METHOD              writer
              908  LOAD_STR                 'title'
              910  CALL_METHOD_1         1  '1 positional argument'
              912  BUILD_LIST_2          2 
              914  GET_ITER         
              916  FOR_ITER            960  'to 960'
              918  STORE_FAST               'writer'

 L.2285       920  SETUP_EXCEPT        944  'to 944'

 L.2285       922  LOAD_FAST                'writer'
              924  LOAD_METHOD              updateNumericDocValue
              926  LOAD_FAST                'term'
              928  LOAD_FAST                'item'
              930  LOAD_DEREF               'book_dict'
              932  LOAD_FAST                'item'
              934  BINARY_SUBSCR    
              936  CALL_METHOD_3         3  '3 positional arguments'
              938  POP_TOP          
              940  POP_BLOCK        
              942  JUMP_BACK           916  'to 916'
            944_0  COME_FROM_EXCEPT    920  '920'

 L.2286       944  POP_TOP          
              946  POP_TOP          
              948  POP_TOP          

 L.2286       950  POP_EXCEPT       
              952  JUMP_BACK           916  'to 916'
              954  END_FINALLY      
          956_958  JUMP_BACK           916  'to 916'
              960  POP_BLOCK        
            962_0  COME_FROM_LOOP      894  '894'
          962_964  JUMP_BACK           880  'to 880'
              966  POP_BLOCK        
            968_0  COME_FROM_LOOP      874  '874'
            968_1  COME_FROM           860  '860'

Parse error at or near `COME_FROM_LOOP' instruction at offset 968_0


class Service:

    @staticmethod
    def deleteBooks(book_ids):
        query = term_in_set_query('book_key', book_ids)
        Index.writer('esnad').deleteDocuments(query)
        Index.commit('esnad')
        return True

    @staticmethod
    def deletePages(book_id, pages):
        for page in pages:
            Index.writer('esnad').deleteDocuments(Term('id', f"{book_id}-{page}"))

        Index.commit('esnad')
        return True


def getComments(scope_query=None):
    from dbmanager import BookDb, CoreDb
    comments = defaultdict(list)
    try:
        comments_query = BooleanQuery.Builder()
        comments_query.add(WildcardQuery(Term('comment', '*')), BooleanClause.Occur.SHOULD)
        comments_query.add(WildcardQuery(Term('n_comment', '*')), BooleanClause.Occur.SHOULD)
        builder = BooleanQuery.Builder()
        builder.add(comments_query.build(), BooleanClause.Occur.MUST)
        offline_order = None
        if scope_query:
            builder.add(scope_query, BooleanClause.Occur.MUST)
        else:
            offline_order = CoreDb().offlineBooks()
            if not offline_order:
                return comments
            builder.add(scopeQuery(offline_order), BooleanClause.Occur.MUST)
        query = ConstantScoreQuery(builder.build())
        with Index.lease('page') as (searcher):
            for _id, fields in bulkQueryRows(searcher, query, ['comment'], 250000, sortBy()):
                text = fields[0]
                if not text:
                    continue
                pieces = _id.split('-')
                comments[pieces[0]].append([int(pieces[1]), text])

        if comments:
            book_order = [f"{b}" for b in offline_order] if offline_order else list(comments)
            ordered = {}
            for s_book_id in book_order:
                if s_book_id not in comments:
                    continue
                book_comments = sorted((comments[s_book_id]), key=(lambda entry: entry[0]))
                try:
                    qualified = BookDb(int(s_book_id)).qualify(book_comments)
                except Exception:
                    traceback.print_exc()
                    continue

                if qualified:
                    ordered[s_book_id] = qualified

            return ordered
        return comments
    except Exception:
        traceback.print_exc()


def pickle(result):
    from customs import pack
    import hashlib
    b = bytes(str(result), 'utf-8')
    hash_value = hashlib.md5(b).hexdigest()
    file_path = os.path.join(resultsFolder(), f"{hash_value}.o")
    if not os.path.isfile(file_path):
        pack(result, file_path)
    return hash_value


def unpickle(hash_value):
    from customs import unpack
    return unpack(os.path.join(resultsFolder(), f"{hash_value}.o"))


def register_shutdown_handlers():
    """Register atexit and OS-signal handlers so that Index.begin_shutdown()
    is called even when the user force-quits the app (Cmd+Q / Task Manager
    kill / SIGTERM). This lets in-flight app work notice shutdown and unwind
    before Index.clear() closes shared readers and writers.

    Must be called from the *main* thread.
    """

    def _emergency_shutdown(signum=None, frame=None):
        try:
            Index.begin_shutdown()
        except Exception:
            pass

    atexit.register(_emergency_shutdown)
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _emergency_shutdown)
        except (OSError, ValueError):
            pass