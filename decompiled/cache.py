# decompyle3 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: cache.py
import os, unicodedata
from collections import OrderedDict, defaultdict
from qtpy.QtCore import QLocale
from dbmanager import CoreDb, CoverDb, MenDb
from dirs import pdfPath, isWritable, hintsCachePath
from engine import getAsaneed, hintIds
from textmanager import val, buildCss, textAuthorFolder, safeName, formatManSummary, formatGarh
import regex as re

class Hints:
    _hints_books = []

    @classmethod
    def hintsBooks(cls):
        from customs import pack, unpack
        if cls._hints_books:
            return cls._hints_books
        hints_path = hintsCachePath()
        if os.path.isfile(hints_path):
            cls._hints_books = set(unpack(hints_path))
        else:
            hints_list = hintIds()
            pack(hints_list, hints_path)
            cls._hints_books = set(hints_list)
        return cls._hints_books

    @classmethod
    def reCache(cls):
        try:
            os.unlink(hintsCachePath())
        except:
            pass

        cls.hintsBooks()


class Numbers:
    arabic_table = latin_table = system_table = None

    @staticmethod
    def systemTable():
        if not Numbers.system_table:
            local_string = ''
            for i in range(10):
                local_string += QLocale().toString(i)

            Numbers.system_table = str.maketrans('0123456789', local_string)
        return Numbers.system_table

    @staticmethod
    def arabicTable():
        if not Numbers.arabic_table:
            Numbers.arabic_table = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
        return Numbers.arabic_table

    @staticmethod
    def latinTable():
        if not Numbers.latin_table:
            Numbers.latin_table = {codepoint: str(unicodedata.decimal(chr(codepoint))) for codepoint in range(1114112) if unicodedata.category(chr(codepoint)) == 'Nd'}
        return Numbers.latin_table

    @staticmethod
    def clearCache():
        Numbers.system_table = None


class FixSizeOrderedDict(OrderedDict):

    def __init__(self, *args, imax=0, **kwargs):
        self._max = imax
        (super().__init__)(*args, **kwargs)

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._max > 0:
            if len(self) > self._max:
                self.popitem(False)


class PdfSize:
    _cache = {}

    @staticmethod
    def getSize(book_id):
        if book_id not in PdfSize._cache:
            PdfSize._cache[book_id] = CoreDb().pdfSize(book_id)
        return PdfSize._cache[book_id]


class AuthorNames:
    _cache = {}

    @staticmethod
    def authorFolder(author_id):
        if author_id not in AuthorNames._cache:
            AuthorNames._cache[author_id] = CoreDb().authorFolder(author_id)
        return AuthorNames._cache[author_id]

    @staticmethod
    def setAuthorFolder(author_id, author_name, author_death):
        AuthorCache.clear(author_id)
        old_author_name = AuthorCache.authorName(author_id)
        old_author_death = AuthorCache.authorDeathN(author_id)
        if author_name == '#':
            author_name = old_author_name
        if author_death == '#':
            author_death = old_author_death
        old_folder = AuthorNames.authorFolder(author_id)
        if old_folder:
            new_folder = textAuthorFolder(author_name, author_death)
            if old_folder != new_folder:
                pdf_path = pdfPath()
                old_path = os.path.join(pdf_path, old_folder)
                if os.path.isdir(old_path):
                    new_path = os.path.join(pdf_path, new_folder)
                    try:
                        os.renames(old_path, new_path)
                    except:
                        pass

                    if os.path.isdir(old_path):
                        return
                    if not os.path.isdir(new_path):
                        return
        return AuthorNames.putAuthorFolder(author_id, author_name, author_death)

    @staticmethod
    def putAuthorFolder(author_id, author_name, author_death):
        AuthorNames._cache[author_id] = textAuthorFolder(author_name, author_death)
        return True

    @staticmethod
    def renameBook(book_id, author, name):
        old_author = CoreDb().authorId(book_id)
        old_name = CoreDb().bookName(book_id)
        if author == '#':
            author = old_author
        else:
            author = val(author)
        if name == '#':
            name = old_name
        old_folder = os.path.join(AuthorNames.authorFolder(old_author), safeName(old_name))
        new_folder = os.path.join(AuthorNames.authorFolder(author), safeName(name))
        return renamePdfFolder(old_folder, new_folder)


def renamePdfFolder(old_folder, new_folder):
    pdf_path = pdfPath()
    if not isWritable(pdf_path):
        return True
    if old_folder != new_folder:
        old_path = os.path.join(pdf_path, old_folder)
        if os.path.isdir(old_path):
            new_path = os.path.join(pdf_path, new_folder)
            try:
                os.renames(old_path, new_path)
            except:
                pass

            if not os.path.isdir(new_path):
                return
    return True


class CoverCache:
    _cache = FixSizeOrderedDict(max=20)

    @staticmethod
    def _getCache(book_id, pdf_links):
        if book_id not in CoverCache._cache:
            CoverCache._cache[book_id] = CoverDb().load(book_id, pdf_links)
        return CoverCache._cache[book_id]

    @staticmethod
    def bookCover(book_id, pdf_links):
        return CoverCache._getCache(book_id, pdf_links)


class BookCache:
    _cache = FixSizeOrderedDict(max=1000)

    @staticmethod
    def _getCache(book_id):
        if book_id not in BookCache._cache:
            BookCache._cache[book_id] = CoreDb().fillBookCache(book_id)
        return BookCache._cache[book_id]

    @staticmethod
    def clear(book_id=None):
        if book_id:
            if book_id in BookCache._cache:
                del BookCache._cache[book_id]
        else:
            BookCache._cache = FixSizeOrderedDict(max=1000)

    @staticmethod
    def bookName(book_id):
        return BookCache._getCache(book_id)[0]

    @staticmethod
    def bookIcon(book_id, context=None):
        from theme import Icon
        cache = BookCache._getCache(book_id)
        special_path = cache[6] if context in frozenset({5, 6}) else None
        path = special_path or cache[1]
        return Icon.icon(path)

    @staticmethod
    def printed(book_id):
        return BookCache._getCache(book_id)[8]

    @staticmethod
    def bookHidden(book_id):
        if BookCache._getCache(book_id)[2] in BookCache.viewSet(2, False):
            return True
        return False

    @staticmethod
    def abstractName(book_id):
        return BookCache._getCache(book_id)[3]

    @staticmethod
    def hasPdf(book_id):
        return BookCache._getCache(book_id)[4]

    @staticmethod
    def authorName(book_id):
        return BookCache._getCache(book_id)[5]

    @staticmethod
    def authorAbstName(book_id):
        return BookCache._getCache(book_id)[7]

    @staticmethod
    def viewSet(context, value):
        """
        :param context: 1 select    2 search   3 control    4 update   5 pdf    6 mak
        :param value: True show        False Hide
        :return:
        """
        if context == 2:
            if value:
                return {0,2,4,6,8,10,12,14}
            return {1,3,5,7,9,11,13,15}
        if context == 4:
            if value:
                return {0,1,4,5,8,9,12,13}
            return {2,3,6,7,10,11,14,15}
        if context == 5:
            if value:
                return {0,1,2,3,8,9,10,11}
            return {4,5,6,7,12,13,14,15}
        if context == 6:
            if value:
                return {0,1,2,3,4,5,6,7}
            return {8,9,10,11,12,13,14,15}


class AuthorCache:
    _cache = FixSizeOrderedDict(max=100)

    @staticmethod
    def _getCache(author_id):
        if author_id not in AuthorCache._cache:
            AuthorCache._cache[author_id] = CoreDb().fillAuthorCache(author_id)
        return AuthorCache._cache[author_id]

    @staticmethod
    def clear(author_id=None):
        if author_id:
            if author_id in AuthorCache._cache:
                del AuthorCache._cache[author_id]
        else:
            AuthorCache._cache = FixSizeOrderedDict(max=100)

    @staticmethod
    def authorName(author_id):
        return AuthorCache._getCache(author_id)[0]

    @staticmethod
    def authorDeath(author_id):
        return AuthorCache._getCache(author_id)[1]

    @staticmethod
    def authorDeathN(author_id):
        return AuthorCache._getCache(author_id)[2]


class EsnadCache:
    _cache = FixSizeOrderedDict(max=100)

    @staticmethod
    def _getCache(man_id):
        if man_id not in EsnadCache._cache:
            EsnadCache._cache[man_id] = {}
            asaneed = getAsaneed(man_id)
            if asaneed:
                sheokh_pos = defaultdict(lambda: defaultdict(set)
)
                talameez_pos = defaultdict(lambda: defaultdict(set)
)
                mawaten = defaultdict(set)
                sheokh_count = defaultdict(int)
                talameez_count = defaultdict(int)
                for esnad in asaneed:
                    book = esnad[0]
                    page = esnad[1]
                    mawaten[book].add(page)
                    true_esnad = [int(man) for man in esnad[2].split(' ')]
                    i = true_esnad.index(man_id)
                    if i != 0:
                        man = true_esnad[i - 1]
                        if man > 1:
                            if page not in sheokh_pos[man][book]:
                                sheokh_pos[man][book].add(page)
                                sheokh_count[man] += 1
                    if i != len(true_esnad) - 1:
                        man = true_esnad[i + 1]
                        if man > 1:
                            if page not in talameez_pos[man][book]:
                                talameez_pos[man][book].add(page)
                                talameez_count[man] += 1

                sheokh_set = set(sheokh_pos.keys())
                talameez_set = set(talameez_pos.keys())
                EsnadCache._cache[man_id]['names'] = MenCache.shortNames(sheokh_set.union(talameez_set))
                EsnadCache._cache[man_id]['books'] = CoreDb().arrangeBooks(set(mawaten.keys()))
                EsnadCache._cache[man_id]['sheokh'] = sheokh_set
                EsnadCache._cache[man_id]['talameez'] = talameez_set
                EsnadCache._cache[man_id]['mwaten'] = mawaten
                EsnadCache._cache[man_id]['sheokh_pos'] = (sheokh_count, sheokh_pos)
                EsnadCache._cache[man_id]['talameez_pos'] = (talameez_count, talameez_pos)
        return EsnadCache._cache[man_id]

    @staticmethod
    def menNames(man_id):
        return EsnadCache._getCache(man_id)['men_names']

    @staticmethod
    def names(man_id):
        return EsnadCache._getCache(man_id)['names']

    @staticmethod
    def books(man_id):
        return EsnadCache._getCache(man_id)['books']

    @staticmethod
    def sheokh(man_id):
        return EsnadCache._getCache(man_id)['sheokh']

    @staticmethod
    def talameez(man_id):
        return EsnadCache._getCache(man_id)['talameez']

    @staticmethod
    def mwaten(man_id):
        return EsnadCache._getCache(man_id)['mwaten']

    @staticmethod
    def sheokh_pos(man_id):
        return EsnadCache._getCache(man_id)['sheokh_pos']

    @staticmethod
    def talameez_pos(man_id):
        return EsnadCache._getCache(man_id)['talameez_pos']

    @staticmethod
    def clear():
        EsnadCache._cache = FixSizeOrderedDict(max=100)


class HonorificCache:
    _vanish = _plain = _honorific_repls = None

    @classmethod
    def vanishTable(cls):
        if not cls._vanish:
            cls._vanish = str.maketrans('', '', '\ufd46\ufdcf\ufd4b\ufd4c\ufd49\ufd48\ufd4d\ufd47\ufd4e\ufdfe\ufd41\ufd42\ufd45\ufd43\ufd44\ufd4a\ufdff\ufd4f\ufd40﷽ﷻﷺ')
        return cls._vanish

    @classmethod
    def plainTable(cls):
        if not cls._plain:
            honorifics = [('صلى الله عليه وسلم', 'ﷺ'),
             ('جل جلاله', 'ﷻ'),
             ('بسم الله الرحمن الرحيم', '﷽'),
             ('رحمه الله', '\ufd40'),
             ('رحمهم الله', '\ufd4f'),
             ('عز وجل', '\ufdff'),
             ('عليه الصلاة والسلام', '\ufd4a'),
             ('رضي الله عنهما', '\ufd44'),
             ('رضي الله عنهم', '\ufd43'),
             ('رضي الله عنهن', '\ufd45'),
             ('رضي الله عنها', '\ufd42'),
             ('رضي الله عنه', '\ufd41'),
             ('سبحانه وتعالى', '\ufdfe'),
             ('تبارك وتعالى', '\ufd4e'),
             ('عليه السلام', '\ufd47'),
             ('عليها السلام', '\ufd4d'),
             ('عليهم السلام', '\ufd48'),
             ('عليهما السلام', '\ufd49'),
             ('صلى الله عليه وآله وسلم', '\ufd4c'),
             ('}', '﴾'),
             ('{', '﴿')]
            honorific_dict = {}
            for equ, graph in honorifics:
                honorific_dict[graph] = equ

            cls._plain = str.maketrans(honorific_dict)
        return cls._plain

    @classmethod
    def honorificRepls(cls):
        if not cls._honorific_repls:
            prep_harakat = lambda s: re.sub('[يى]', '[يى]', re.sub('([ء-ي])', '\\1\\p{Mark}*', s))
            prep_honorific = lambda s: '(?<=[\\W|^])([(ـ-] ?)?%s( ?[-ـ)])?(?=[\\W|$])' % prep_harakat(s)
            honorifics = [
             ('صلى الله عليه وسلم', 'ﷺ'),
             ('جل جلاله', 'ﷻ'),
             ('رحمه الله(?! تعالى)', '\ufd40'),
             ('رحمهم الله(?! تعالى)', '\ufd4f'),
             ('عز وجل', '\ufdff'),
             ('عليه الصلاة والسلام', '\ufd4a'),
             ('رضي الله عنهما', '\ufd44'),
             ('رضي الله عنهم(?! ورضوا)', '\ufd43'),
             ('رضي الله عنهن', '\ufd45'),
             ('رضي الله عنها', '\ufd42'),
             ('رضي الله عنه', '\ufd41'),
             ('سبحانه وتعالى(?! عما)', '\ufdfe'),
             ('تبارك وتعالى', '\ufd4e'),
             ('عليه السلام', '\ufd47'),
             ('عليها السلام', '\ufd4d'),
             ('عليهم السلام', '\ufd48'),
             ('عليهما السلام', '\ufd49'),
             ('صلى الله عليه وآله وسلم', '\ufd4c')]
            cls._honorific_repls = [(1, prep_honorific(a), b) for a, b in honorifics]
            cls._honorific_repls.append((1, prep_harakat('\r\\(?بسم الله الرحمن الرحيم\\)? ?\\*?\r'), '\r﷽\r'))
        return cls._honorific_repls


class MenCache:
    _summary_cache = FixSizeOrderedDict(max=100)
    _garh_cache = FixSizeOrderedDict(max=100)
    _short_cache = FixSizeOrderedDict(max=100)
    _long_cache = FixSizeOrderedDict(max=100)
    _hasgarh_cache = FixSizeOrderedDict(max=100)

    @staticmethod
    def _getSummaryCache(man_id):
        if man_id not in MenCache._summary_cache:
            MenCache._summary_cache[man_id], MenCache._long_cache[man_id] = MenDb().getSummary(man_id)
        return MenCache._summary_cache[man_id]

    @staticmethod
    def _getGarhCache(man_id):
        if man_id not in MenCache._garh_cache:
            MenCache._garh_cache[man_id] = MenDb().getGarh(man_id)
        return MenCache._garh_cache[man_id]

    @staticmethod
    def hasGarh(man_id):
        if man_id not in MenCache._hasgarh_cache:
            MenCache._hasgarh_cache[man_id] = MenDb().hasGarh(man_id)
        return MenCache._hasgarh_cache[man_id]

    @staticmethod
    def clear():
        MenCache._summary_cache = FixSizeOrderedDict(max=100)
        MenCache._garh_cache = FixSizeOrderedDict(max=100)
        MenCache._short_cache = FixSizeOrderedDict(max=500)
        MenCache._long_cache = FixSizeOrderedDict(max=100)
        MenCache._hasgarh_cache = FixSizeOrderedDict(max=100)

    @staticmethod
    def displaySummary(man_id):
        cache = MenCache._getSummaryCache(man_id)
        free = cache['free'] if 'free' in cache else None
        summary = cache['summary'] if 'summary' in cache else None
        return formatManSummary(MenCache.manLongName(man_id), summary, free)

    @staticmethod
    def manLongName(man_id):
        if man_id not in MenCache._long_cache:
            MenCache._long_cache[man_id] = MenDb().getLong(man_id)
        return MenCache._long_cache[man_id]

    @staticmethod
    def manShortName(man_id):
        if man_id not in MenCache._short_cache:
            MenCache._short_cache[man_id] = MenDb().getShort(man_id)
        return MenCache._short_cache[man_id]

    @staticmethod
    def shortNames(ids):
        result_dict = {}
        defective_set = set()
        for i in ids:
            if i in MenCache._short_cache:
                result_dict[i] = MenCache._short_cache[i]
            else:
                defective_set.add(i)

        if defective_set:
            names_dict = MenDb().getNames(defective_set)
            for key in names_dict:
                if key not in MenCache._short_cache:
                    MenCache._short_cache[key] = names_dict[key]
                if key not in result_dict:
                    result_dict[key] = names_dict[key]

        return result_dict

    @staticmethod
    def bothNames(ids):
        result_dict = {}
        defective_set = set()
        for i in ids:
            if i in MenCache._short_cache and i in MenCache._long_cache:
                result_dict[i] = (
                 MenCache._short_cache[i], MenCache._long_cache[i])
            else:
                defective_set.add(i)

        if defective_set:
            names_dict = MenDb().getBothNames(defective_set)
            for key in names_dict:
                if key not in MenCache._short_cache:
                    MenCache._short_cache[key] = names_dict[key][0]
                elif key not in MenCache._long_cache:
                    MenCache._long_cache[key] = names_dict[key][1]
                if key not in result_dict:
                    result_dict[key] = names_dict[key]

        return result_dict

    @staticmethod
    def manGarh(man_id):
        cache = MenCache._getGarhCache(man_id)
        if 'garh' in cache:
            return cache['garh']

    @staticmethod
    def manFawed(man_id):
        cache = MenCache._getGarhCache(man_id)
        if 'fwaed' in cache:
            return cache['fwaed']

    @staticmethod
    def displayGarh(man_id):
        return formatGarh(MenCache.manGarh(man_id), MenCache.manFawed(man_id))


class CssCache:
    _cache = {}

    @staticmethod
    def getCache(css_type):
        if css_type not in CssCache._cache:
            css = buildCss(css_type)
            if css_type not in ('s', 'h', 'punct'):
                css = f"/* shamela-css:{css_type} */ {css}"
            CssCache._cache[css_type] = css
        return CssCache._cache[css_type]

    @staticmethod
    def clear():
        CssCache._cache = {}


class DataCache:

    def __init__(self, getter_func):
        self.clear()
        self.getter_func = getter_func

    def get(self, row_column_role):
        if row_column_role not in self._cache:
            value = self.getter_func(row_column_role)
            if not value:
                return
            self._cache[row_column_role] = value
        return self._cache[row_column_role]

    def clear(self):
        self._cache = FixSizeOrderedDict(max=100)