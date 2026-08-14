# decompyle3 version 3.9.0
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
                        else:
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
         JMap({ 'ـ': '',
           'ﷺ': '', 'ﷻ': '', '\ufd40': '', '\ufd4f': '', '\ufdff': '', '\ufd4a': '', '\ufd44': '', '\ufd43': '', '\ufd45': '', '\ufd42': '',
           '\ufd41': '', '\ufdfe': '', '\ufd4e': '', '\ufd47': '', '\ufd4d': '', '\ufd48': '', '\ufd49': '', '\ufd4c': '', '﷽': '',
           '\ufd4b': '',
           '\ufdcf': '', '\ufd46': '',
           'گ': 'ك', 'پ': 'ب', 'چ': 'ج'})]
    return _basic_map


def charFilters(is_diacritics, is_hamza, is_numbers, is_quran=False):
    char_map = list(basicMap())
    if not is_diacritics:
        char_map += [JMap({ 'َ': '', 'ً': '', 'ُ': '', 'ٌ': '', 'ِ': '', 'ٍ': '', 'ْ': '', 'ّ': ''})]
    if not is_numbers:
        char_map += [
         JMap({chr(codepoint): ' ' for codepoint in range(1114112) if unicodedata.category(chr(codepoint)) == 'Nd'})]
    if not is_hamza:
        char_map += [JMap({ 'ٱ': 'ا', 'آ': 'ا', 'أ': 'ا', 'إ': 'ا', 'ى': 'ي', 'ؤ': 'و', 'ة': 'ه'}),
         JMap({'ءا':'ء',  'يء':'ئ'})]
        if is_quran:
            char_map += [JMap({'ائ': 'اا'})]
        char_map += [
         JMap({ 'ئو': 'وو', 'ءو': 'وو', 'رحمان': 'رحمن', 'سماوات': 'سموات', 'مائه': 'مئه', 'مائت': 'مئت',
           'سماعيل': 'سمعيل', 'براهام': 'براهيم', 'اسحاق': 'اسحق',
           'هاذا': 'هذا', 'هاذين': 'هذين', 'هاؤلاء': 'هؤلاء', 'اولائك': 'اولئك'}),
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
        if not (is_diacritics or is_hamza or is_numbers):
            tokenizer = 'letter'
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
        arranged = sorted((cls._cache.items()), key=(lambda item: item[1]['count']
))
        if arranged[0][1]['count'] >= cls._full_limit:
            cls._is_full = True
            return
        i = 1
        for item in arranged:
            if item[1]['count'] >= cls._full_limit:
                break
            else:
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
            f_token = (f"{token}")
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
            f_token = (f"{token}")
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
            with self.global_index.lease(self._index) as searcher:
                batch_number = 0
                hits = searcher.search(query, hits_limit, sorts, False).scoreDocs
                while True:
                    if Index.is_shutting_down():
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
                        else:
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
                self._fields = ('m_hint' if self.stemmed else 'hint') if item == 'h' else ['m_body' if self.stemmed else 'body']
                affirm_only = bool(self.secondPass()) and not self.is_or
                query = ConstantScoreQuery(fieldsQuery(self._fields, self.info(), False, affirm_only))
                with self.global_index.lease(index) as searcher:
                    batch_number = 0
                    hits = searcher.search(query, hits_limit, sorts, False).scoreDocs
                    while True:
                        if Index.is_shutting_down():
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
                            else:
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
            with self.global_index.lease(self._index) as searcher:
                for field_name in self._fields:
                    if field_name.startswith('m_'):
                        field_name = field_name[2:]
                    else:
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
                            else:
                                return plain(linear((f"{fragment}")))

            return ''
        with self.global_index.lease(self._index) as searcher:
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
            with self.global_index.lease(index) as searcher:
                text = getDoc(searcher, doc_id).get(field) or ''
            doc_id = int(doc_id)
            if prefix == 'b':
                text = f"{BookCache.abstractName(doc_id)}\n{BookCache.authorAbstName(doc_id)}\n{text}"
            else:
                if prefix == 'a':
                    text = f"{AuthorCache.authorName(doc_id)}\n{text}"
            if text:
                fragment = highlight(text, self._snippetQuery(), self._finalAnalyzer(), fragment_size, '\x01', '\x02')
                if fragment:
                    if multiline:
                        return noTashkeel((f"{fragment}"))
                    return plain(linear((f"{fragment}")))
            return ''
        with self.global_index.lease(index) as searcher:
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
            cls._lease_cond.wait_for((lambda: cls._active_leases == 0
), timeout=30)
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
        if not Index._lease_cond.wait_for((lambda: Index._active_leases == 0
), timeout=30):
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

            if not os.path.isdir(source_path):
                return False
            shutil.rmtree(target_path, ignore_errors=True)
            if os.path.exists(target_path):
                return False
            os.rename(source_path, target_path)
            return True


def sortsFromIndex(index_name):
    if index_name == 'page' or index_name == 'title':
        return [
         'date','author','book_up','group','group_order','book','page']
    if index_name == 'book':
        return [
         'date','author','book_up','group','group_order','book']
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
        return [None] * len(fields)


def javaBulkFirstField(searcher, _id, fields):
    if LuceneBulk:
        try:
            value = LuceneBulk.firstFieldById(searcher, f"{_id}", javaStringArray(fields))
            if value is not None:
                return (f"{value}")
            return
        except:
            pass

        doc = getDoc(searcher, (f"{_id}"))
        if not doc:
            return
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
                else:
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
                else:
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
    with Index.lease(index_name) as searcher:
        results = intCollectingSearch(searcher, query)
    return [book_id for book_id in complete_source if book_id in results]


def filterAuthors(text, authors_dict):
    if not text:
        return list(authors_dict.items())
    info = buildFilter(text, False)
    query = ConstantScoreQuery(fieldsQuery(['author'], info, False))
    with Index.lease('s_author') as searcher:
        results = intCollectingSearch(searcher, query)
    return [[author_id, authors_dict[author_id]] for author_id in authors_dict if author_id in results]


def fieldsQuery(ofields, info, is_final, affirm_only=False):
    analyzer = getAnalyzer(info, is_final)
    and_panels, or_panels, not_panels = info['phrases']
    if info['stemmed']:
        func = stemmed_query
    else:
        func = tashkeel_query if (info['diacritics']) and is_final else phrase_query
    numbers = info['numbers']
    fields = [f"n_{ofield}" if (not is_final) else ofield for ofield in ofields if numbers]
    or_split = numbers and not is_final
    if or_split:
        is_quran = info.get('type') == QueryType.QURAN.value
        text_analyzer = Analyzer.quran() if is_quran else Analyzer.shamela()
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

            if not ((len(and_phrases) == 1 or near) == 0 and ordered):
                builder.add(sAndQuery(and_phrases, fields, analyzer, func), joiner)
            else:
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

    if not affirm_only:
        if info['is_or']:
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
    num_phrases = numberedPhrases(phrases, True, False)
    if num_phrases:
        parts.append(orQuery(num_phrases, num_fields, num_analyzer, func))
    if not parts:
        return
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
    if len(fields) == 1:
        if near != 0 or ordered:
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
    return Sort(*map(lambda field: SortField(field, SortField.Type.INT)
, fields))


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
    return {'is_or':False,  'stemmed':False,  'hamza':False,  'diacritics':False,  'numbers':False,  'phrases':[
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
    with Index.lease('title') as searcher:
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
            hadeeth = (f"{int(pieces[0])}")
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
        current_doc = None
        with Index.lease('page') as _searcher:
            current_doc = getDoc(_searcher, f"{self.book_id}-{page_id}")
        if current_doc:
            for field in ('body', 'foot', 'comment'):
                if field not in content_dict:
                    value = current_doc.get(field)
                    if value:
                        content_dict[field] = (f"{value}")

        empty = True
        for field in ('body', 'foot', 'comment'):
            if field in content_dict:
                if content_dict[field]:
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
                if field in content_dict:
                    if content_dict[field]:
                        doc.add(Field(field, FieldType.TEXT, content_dict[field]).field())
                        doc.add(Field(f"m_{field}", FieldType.ANALYSE, content_dict[field]).field())
                        n_field = re.sub('\\D+', ' ', content_dict[field]).strip()
                        if n_field:
                            doc.add(Field(f"n_{field}", FieldType.ANALYSE, n_field).field())

            writer.updateDocument(Term('id', f"{self.book_id}-{page_id}"), doc)

    def updateTitle(self, page_id, title_dict):
        current_doc = None
        with Index.lease('title') as _searcher:
            current_doc = getDoc(_searcher, f"{self.book_id}-{page_id}")
        if current_doc:
            if 'body' not in title_dict:
                value = current_doc.get('body')
                if value:
                    title_dict['body'] = (f"{value}")
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
            with Index.lease('page') as searcher:
                hits = searcher.search(query, hits_limit, sortBy(), False).scoreDocs
                results = []
                while True:
                    if hits:
                        results += [[(f"{doc.get('id')}"), (f"{doc.get('body') or ''}"), (f"{doc.get('foot') or ''}")] for doc in [searcher.doc(hit.doc) for hit in hits]]
                        if len(hits) < hits_limit:
                            break
                        else:
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
        with Index.lease('page') as searcher:
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
                else:
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
        with Index.lease(index_name) as searcher:
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
        with Index.lease(index_name) as searcher:
            if LUCENE_ONE:
                doc = getDoc(searcher, (f"{_id}"))
                if doc:
                    return [f"{doc.get(field) or ''}" for field in field_list]
                return [None] * len(field_list)
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
    with Index.lease('book') as searcher:
        return intCollectingSearch(searcher, query)


def getAsaneed(man_id):
    query = ConstantScoreQuery(TermQuery(Term('esnad', (f"{man_id}"))))
    return esnadQuery(query)


def getTorok(hadeeth_id):
    query = ConstantScoreQuery(TermQuery(Term('hadeeth', (f"{hadeeth_id}"))))
    return esnadQuery(query)


def esnadQuery(query):
    with Index.lease('esnad') as searcher:
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
                    else:
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
                ayat[aya_id] = (f"{doc.get(field)}")
                if body_required:
                    body[aya_id] = (f"{doc.get('body')}")

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
    with Index.lease('aya') as _aya_searcher:
        ayat, body = collectAyat(_aya_searcher, range_query, field, body_required)
    if search_info:
        if search_info['phrases']:
            if rasm == 'emlaa':
                body = ayat
            for _id in ayat:
                if aya_id:
                    if _id == aya_id:
                        pass
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
        s_author_id = (f"{author_id}")
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
            if 'date' in author_dict:
                writer.updateNumericDocValue(Term('id', s_author_id), 'date', author_dict['date'])

    @classmethod
    def addBook(cls, book_dict, info_only=None):

        def fetch(key):
            if key in book_dict:
                return book_dict[key]
            if f"db_{key}" in book_dict:
                return book_dict[f"db_{key}"]

        index_name = 'book'
        writer = Index.writer(index_name)
        short_writer = Index.writer(f"s_{index_name}")
        short_doc = LuceneDocument()
        doc = LuceneDocument()
        book_id = book_dict['id']
        s_book_id = (f"{book_id}")
        name, author_names = fetch('name'), fetch('author_names')
        book_up, group, group_order = fetch('book_up'), fetch('group'), fetch('group_order')
        if 'name' in book_dict or 'author_names' in book_dict:
            short_doc.add(Field('id', FieldType.ID, s_book_id).field())
            short_doc.add(Field('single', FieldType.ANALYSE, name).field())
            short_doc.add(Field('double', FieldType.ANALYSE, f"{name} {author_names}").field())
            short_writer.updateDocument(Term('id', s_book_id), short_doc)
        if 'name' in book_dict or 'author_names' in book_dict or 'bibliography' in book_dict or 'hint' in book_dict:
            biblio = book_dict['bibliography'] if 'bibliography' in book_dict else getField('book', 'body_store', s_book_id)
            hint = book_dict['hint'] if 'hint' in book_dict else getField('book', 'hint', s_book_id)
            analyzed_biblio = f"{name} {author_names} {biblio}"
            doc.add(Field('id', FieldType.ID, s_book_id).field())
            doc.add(Field('date', FieldType.ORD, fetch('date')).field())
            doc.add(Field('author', FieldType.ORD, fetch('author')).field())
            if book_up:
                doc.add(Field('book_up', FieldType.ORD, book_up).field())
            if group:
                doc.add(Field('group', FieldType.ORD, group).field())
            if group_order:
                doc.add(Field('group_order', FieldType.ORD, group_order).field())
            doc.add(Field('book', FieldType.ORD, book_id).field())
            doc.add(Field('body', FieldType.ANALYSE, analyzed_biblio).field())
            doc.add(Field('m_body', FieldType.ANALYSE, analyzed_biblio).field())
            doc.add(Field('body_store', FieldType.STORE, biblio).field())
            n_field = re.sub('\\D+', ' ', biblio).strip()
            if n_field:
                doc.add(Field('n_body', FieldType.ANALYSE, biblio).field())
            if hint:
                doc.add(Field('hint', FieldType.TEXT, hint).field())
                doc.add(Field('m_hint', FieldType.ANALYSE, hint).field())
                n_field = re.sub('\\D+', ' ', hint).strip()
                if n_field:
                    doc.add(Field('n_hint', FieldType.ANALYSE, n_field).field())
            writer.updateDocument(Term('id', s_book_id), doc)
        else:
            term = Term('id', s_book_id)
            for item in ('date', 'author', 'book_up', 'group', 'group_order'):
                if item in book_dict:
                    try:
                        writer.updateNumericDocValue(term, item, book_dict[item])
                    except:
                        pass

        if not info_only:
            term = Term('book_key', s_book_id)
            for item in ('date', 'author', 'book_up', 'group', 'group_order'):
                if item in book_dict:
                    for writer in [Index.writer('page'), Index.writer('title')]:
                        try:
                            writer.updateNumericDocValue(term, item, book_dict[item])
                        except:
                            pass


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
        with Index.lease('page') as searcher:
            for _id, fields in bulkQueryRows(searcher, query, ['comment'], 250000, sortBy()):
                text = fields[0]
                if not text:
                    continue
                else:
                    pieces = _id.split('-')
                    comments[pieces[0]].append([int(pieces[1]), text])

        if comments:
            book_order = [f"{b}" for b in offline_order] if offline_order else list(comments)
            ordered = {}
            for s_book_id in book_order:
                if s_book_id not in comments:
                    continue
                else:
                    book_comments = sorted((comments[s_book_id]), key=(lambda entry: entry[0]
))
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