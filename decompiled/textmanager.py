# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: textmanager.py
import html, base64, struct, regex as re
from qtpy.QtGui import QTextDocumentFragment, QFont, QFontInfo, QFontMetricsF
from across import Across
from scaling import scaled_font_size
from settings import Settings
from html.parser import HTMLParser as _HTMLParser
_VOID_TAGS = {
 "'br'", "'hr'", "'img'", "'input'", "'meta'", "'link'", "'area'", "'base'", 
 "'col'", 
 "'embed'", "'param'", "'source'", "'track'", "'wbr'"}

class _Node:
    __slots__ = ('tag', 'attrs', 'children')

    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def find(self, tag):
        tag = tag.lower()
        for c in self.children:
            if isinstance(c, _Node):
                if c.tag == tag:
                    return c
                r = c.find(tag)
                if r is not None:
                    return r

    def find_all(self, tag):
        tag = tag.lower()
        out = []
        for c in self.children:
            if isinstance(c, _Node):
                if c.tag == tag:
                    out.append(c)
                out.extend(c.find_all(tag))

        return out

    def to_html(self):
        attrs_str = ''.join((f" {k}" if v is None else f' {k}="{v}"' for k, v in self.attrs.items()))
        inner = ''.join((c.to_html() if isinstance(c, _Node) else c for c in self.children))
        if self.tag == '__root__':
            return inner
        if self.tag in _VOID_TAGS:
            return f"<{self.tag}{attrs_str}>"
        return f"<{self.tag}{attrs_str}>{inner}</{self.tag}>"


class _TreeBuilder(_HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = _Node('__root__')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag.lower(), attrs)
        self.stack[-1].children.append(node)
        if tag.lower() not in _VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def handle_entityref(self, name):
        self.stack[-1].children.append(f"&{name};")

    def handle_charref(self, name):
        self.stack[-1].children.append(f"&#{name};")

    def handle_comment(self, data):
        self.stack[-1].children.append(f"<!--{data}-->")


def _parse_html(s):
    builder = _TreeBuilder()
    builder.feed(s)
    return builder.root


def hFont(l_font):
    from customs import fontSettingCssWeight
    effective_size = scaled_font_size(l_font[1])
    style = [f'font-family:"{l_font[0]}"', f"font-size:{effective_size}pt", f"font-weight:{fontSettingCssWeight(l_font)}"]
    if l_font[3]:
        style.append('font-style:italic')
    return '; '.join(style) + ';'


def clean_invisible(text):
    if not text:
        return text
    return re.sub('(?!\\u06DD)[\\x01-\\x08\\x1e\\x1f\\p{Cf}]', '', text)


suffixes = {'arabic':('كيلو', 'ميجا', 'جيجا', 'تيرا', 'بيتا', 'إكسا', 'زيتا', 'يوتا'), 
 'english':('kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')}
months = [
 "'محرم'", "'صفر'", "'ربيع الأول'", "'ربيع الآخر'", "'جُمادَى الأولى'", "'جُمادَى الآخرة'", 
 "'رجب'", "'شعبان'", "'رمضان'", 
 "'شوّال'", "'ذو القعدة'", "'ذو الحجة'"]

class CoreReplaces:
    _replacements = _compiled = None

    @staticmethod
    def replacements():
        if not CoreReplaces._replacements:
            CoreReplaces._replacements = {'لاَ': "'لَا'", 
             'َّ': "'َّ'", 
             'ِّ': "'ِّ'", 
             'ُّ': "'ُّ'", 
             '¬': "''", 
             '…': '\'<span class="punct">…</span>\''}
        return CoreReplaces._replacements

    @staticmethod
    def compiledRegex():
        if not CoreReplaces._compiled:
            CoreReplaces._compiled = re.compile('(%s)' % '|'.join(map(re.escape, CoreReplaces.replacements().keys())))
        return CoreReplaces._compiled

    @staticmethod
    def adjust(text):
        if text:
            text = re.sub('(,)(?![^<]*>)', '،', html.unescape(text))
            text = re.sub('(^|[^.])\\.\\.\\.($|[^.])', '\\1…\\2', text)
            text = re.sub(' *(\\(¬\\d+\\))', '<span class="punct">\\1</span>', text)
            text = re.sub('(^|\\r|\\n)(\\d+ *[-\\._])', '\\1<span class="punct">\\2</span>', text)
            text = re.sub('(^|\\r|\\n)([\\[(]\\d+[])])', '\\1<span class="punct">\\2</span>', text)
            text = re.sub('⦗(\\d+)⦘', '<span class="punct">⦗ص: \\1⦘</span>', text)
            text = re.sub('(<span.+?>)', '&#8204;\\1&#8204;', text)
            text = CoreReplaces.compiledRegex().sub(lambda mo: CoreReplaces.replacements()[mo.string[mo.start():mo.end()]], text)
            return text


def safeStr(m_value):
    try:
        if m_value is None:
            return ''
        return str(m_value)
    except Exception:
        return ''


def safeInt(m_value):
    try:
        return int(toAsciiDigits(clean_invisible(m_value)))
    except Exception:
        return 0


def normalize(s):
    """safe to apply on any text"""
    s = re.sub('([ء-ٟ])ـ+([ء-ٟ])', '\\1\\2', s, flags=(re.U))
    s = re.sub('([ء-ؿف-ٟ])([a-zA-Z])', '\\1 \\2', s, flags=(re.U))
    s = re.sub('([a-zA-Z])([ء-ؿف-ٟ])', '\\1 \\2', s, flags=(re.U))
    return s


def toAsciiDigits(s):
    """Normalize any Unicode decimal digits to ASCII digits."""
    from cache import Numbers
    if s is not None:
        if s != '':
            return str(s).translate(Numbers.latinTable())
    return ''


def toArabicDigits(s):
    """Force any Unicode decimal digits to Arabic-Indic digits."""
    from cache import Numbers
    if s is not None:
        if s != '':
            return toAsciiDigits(s).translate(Numbers.arabicTable())
    return ''


def displayDigits(s, forced=None):
    """Render digits using the display policy: system digits when enabled, otherwise Arabic-Indic."""
    from cache import Numbers
    if s is not None:
        if s != '':
            s = toAsciiDigits(s)
            tbl = Numbers.systemTable() if Settings.getValue('system_numbers') and not forced else Numbers.arabicTable()
            return (f"{s}").translate(tbl)
    return ''


def arabize(s, forced=None):
    """Backward-compatible alias for displayDigits()."""
    return displayDigits(s, forced)


def latinize(s):
    """Backward-compatible alias for toAsciiDigits()."""
    return toAsciiDigits(s)


def treatSearch(s, clear_wild=None, keep_digits=None):
    from cache import HonorificCache
    if s:
        s = normalize(clean_invisible(s).translate(HonorificCache.vanishTable()))
        if clear_wild:
            s = re.sub('\\W+|[\\u0640_]+', ' ', s)
        else:
            s = re.sub('[^\\w?*؟]+|[\\u0640_]+', ' ', s)
            s = s.replace('؟', '?')
            s = re.sub('\\*+', '*', s)
            s = re.sub('^[ ?*]+$', '', s)
            s = specialWord(s)
        s = toArabicDigits(s)
        no_digits_ver = re.sub('\\d+', ' ', s).strip()
        if no_digits_ver:
            if not keep_digits:
                s = no_digits_ver
        return s.strip()
    return ''


def treatWord(text):
    return re.sub('^([\\*\\?]*)[آاإأ]بن([\\*\\?]*)$', '\\1بن\\2', text)


def specialWord(phrase):
    return ' '.join([treatWord(word) for word in phrase.strip().split(' ')])


def safeNorm(s):
    """safe to apply on any text
    remove khashida only if between arabic letters (ie tatweel), otherwise it is a word separator"""
    if s:
        s = re.sub('([ء-غف-ي])ـ+([ء-غف-ي])', '\\1\\2', s)
        s = re.sub('([ء-ؿف-ٟ])([a-zA-Z])', '\\1 \\2', s, flags=(re.U))
        s = re.sub('([a-zA-Z])([ء-ؿف-ٟ])', '\\1 \\2', s, flags=(re.U))
        return s
    return ''


def reverseTable(s):
    if s:
        if '<td>' not in s:
            return s
        root = _parse_html(s)
        for table in root.find_all('table'):
            table.attrs['align'] = 'center'
            table.attrs['class'] = 'qqtable'
            if table.attrs.get('dir', '').lower() == 'rtl':
                for table_row in table.find_all('tr'):
                    table_row.children = list(reversed(table_row.children))

        return root.to_html()


def safehtml(text):
    first_close = text.find('>')
    if first_close > -1:
        first_open = text.find('<')
        if first_close < first_open:
            text = text[first_close + 1:]
    last_open = text.rfind('<')
    if last_open > -1:
        last_close = text.rfind('>')
        if last_open > last_close:
            text = text[:last_open]
    return text


def five(s):
    LIMIT = Settings.getValue('tab_title_words')
    r = re.sub(' *\\- *', ' ', s).strip().split()
    if len(r) < LIMIT + 1:
        return s
    if LIMIT == 1:
        return f"{r[0]}…"
    return ' '.join(r[:LIMIT - 2 or 1]) + '…' + r[-1]


def conditioned(s):
    from customs import NVDA
    if NVDA.isRunning():
        return plain(s)
    return s


def tip(s):
    from customs import NVDA
    if NVDA.isRunning():
        return f"<table><tr><td>{s}</td></tr></table>"
    return s


def tipH(s):
    from cache import CssCache
    pieces = s.splitlines()
    new_text = '<p>'.join(pieces)
    return red(wrap(unifySymbols(f"{new_text}<br>"), CssCache.getCache('tip')))


def tipHint(s):
    from cache import CssCache
    pieces = s.splitlines()
    for i, piece in enumerate(pieces):
        clean = piece.replace('\x01', '').replace('\x02', '').strip()
        if clean.startswith('[') and clean.endswith(']'):
            pieces[i] = f"<span class='title'><div align=center>{piece}</div></span>"
            break

    new_text = '<p>'.join(pieces)
    return red(wrap(unifySymbols(f"{new_text}<br>"), CssCache.getCache('tip')))


def tipAuthor(s, name=None):
    from cache import CssCache
    pieces = s.splitlines()
    if name:
        if pieces:
            lead = noTashkeel(pieces[0].replace('\x01', '').replace('\x02', '').strip())
            if lead:
                if lead == (noTashkeel(name) or '').strip():
                    title = f"<span class='title'>{pieces[0]}</span>"
                    rest = '<p>'.join(pieces[1:])
                    new_text = title + coloredHr(breathing=False) + rest
                    return red(wrap(unifySymbols(f"{new_text}<br>"), CssCache.getCache('tip')))
    new_text = '<p>'.join(pieces)
    return red(wrap(unifySymbols(f"{new_text}<br>"), CssCache.getCache('tip')))


def superscript(text):
    text = text.replace('¬ (¬', ' (¬')
    return re.sub('(?<!(^|\\r?\\n|\\r)) *([[(]¬[*\\d]+[])])', '<sup>\\2</sup>', text)


def _fix_title_ligation(s):
    """For single-word title spans mid-word, swap the ZWNJ guards (&#8204;) that
    CoreReplaces.adjust injected with ZWJ (&#8205;) so Qt re-ligates the word
    across the span boundary.  Multi-word titles (space in content) keep their
    ZWNJs — correct cross-boundary isolation and correct internal ligation."""
    AL = '[\u0600-ۿ]'

    def fix(m):
        before, span_open, content, span_close, after = m.groups()
        if ' ' in content:
            return m.group(0)
        return f"{before}&#8205;{span_open}&#8205;{content}&#8205;{span_close}&#8205;{after}"

    return re.sub(f"""({AL})&#8204;(<span(?=[^>]*data-type=["\\\']?title)[^>]*>)&#8204;(.*?)(</span>)({AL})""",
      fix,
      s, flags=(re.DOTALL))


def adjustPageContent(s, shorts):
    if s:
        s = CoreReplaces.adjust(s)
        s = _fix_title_ligation(s)
        s = re.sub('\\r+ـ+\\r+', '\\r<hr>', s)
        s = re.sub('\\r+\\={3,}\\r+', '\r<hr>', s)
        first = s.find('<hr>')
        if first != -1:
            second = s.find('<hr>', first + 4)
            s = re.sub('\\A(.+?)<hr>', "<div class='matn'>\\1</div><hr>", s, flags=(re.DOTALL))
            if second != -1:
                s = re.sub('(.+<hr>)(.*)', "\\1<div class='mobham'>\\2</div>", s, flags=(re.DOTALL))
                s = s.replace("<hr><div class='mobham'>", "<div class='mobham'><hr>")
            s = s.replace('<hr><s', '<hrs')
            s = re.sub('<hr>\\r*', '<hr>\\r', s)
            s = s.replace('<hrs', '<hr><s')
            s = re.sub('<hr><s(\\d+)>', centeredHr('<s\\1>'), s)
            s = s.replace('<hr>', coloredHr())
        if shorts:
            s = shorts.expand(s)
        s = paragraph('<p>'.join(s.splitlines()))
        s = reverseTable(s)
        return s + '<font size=1><br></font>'


def adjustExport(text, footnotes):
    from cache import HonorificCache
    if footnotes:
        html_separator = "<hr width='95' align='right'>"
        if text:
            text = f"{superscript(text)}{html_separator}<div class='footnote'>{footnotes}</div>"
        elif Across.splitter in footnotes:
            text = footnotes.split(Across.splitter, 1)
            text = f"{superscript(text[0])}{html_separator}<div class='footnote'>{text[1]}<p></div>"
        else:
            text = superscript(footnotes)
    elif '<hr>' in text:
        text = text.split('<hr>', 1)
        text = f"{superscript(text[0])}<hr>{text[1]}"
    else:
        text = superscript(text)
    if text:
        text = CoreReplaces.adjust(text)
        text = re.sub('<span data-type="title" id=toc-\\d+>', '<span class="title">', text)
        text = re.sub('<a href="inr://man-\\d+">([^<>]+)</a>', '\\1', text)
        text = re.sub('(<hadeeth-\\d+>)|(<hadeeth>)', '', text)
        text = '</p>'.join(text.splitlines())
        text = text.replace('</p></p>', '</p>&nbsp;</p>')
    return toAsciiDigits(text.translate(HonorificCache.plainTable()))


def formatPage(s, css=None, quran=None, service=None, shorts=None):
    from cache import CssCache, MenCache
    names_dict = {}
    page_info = {}

    def menTitles(match_object):
        key = int(match_object.group(1))
        return f'<a href="inr://man-{key}" title="{names_dict[key]}">'

    if s:
        if not quran:
            s = adjustPageContent(s, shorts)
        elif service:
            if service[2] == 'tafseer':
                service_text = f'<span id="aya-{service[3]}">'
                s = s.replace(service_text, f'<span data-type="title">&#10040;</span>{service_text}')
            else:
                if service[2] == 'man':
                    for man in service[3]:
                        piece = f'<a href="inr://man-{man}">'
                        s = re.sub(f"{piece}(.+?)</a>", f'{piece}<span id=go class="search">&#8204;\\1</span></a>', s)

        if 'inr://man' in s:
            text_men = re.findall('(?<=inr://man-)(\\d+)(?=">)', s)
            names_dict = MenCache.shortNames(text_men)
            page_info['text_men'] = text_men
            s = re.sub('<a href="inr://man-(\\d+?)">', menTitles, s)
            s = re.sub('<a href="inr://man-([01]+)"([\\s\\S]+?)</a>', '<span class="mobham"\\2</span>', s)
        s = re.sub('<img src=([^<>]+)>', "<br><table align='center'><tr><td><img style='float:left;' src=\\1></td></tr></table><br>", s)
        s = s.replace('<p> <br>', '<br>')
        return (wrap(unifySymbols(s), css), page_info)
    return (None, None)


def colourizePunctuation(text):
    text = re.sub('([][)(}{﴿﴾«،•*»/\\\\\\-–=.:"ﷺ﷽ﷻ\ufd40\ufd4f\ufdff\ufd4a\ufd44\ufd4b\ufdcf\ufd43\ufd45\ufd42\ufd41\ufdfe\ufd4e\ufd47\ufd4d\ufd48\ufd49\ufd4c؛;!?؟]+)(?![^<]*>)', '<span class="punct">\\1</span>', html.unescape(text))
    return text


def legacyPunctuationToCss(text):
    punct = '[\\s\\d¬ص:\\[\\]\\(\\)\\{\\}﴿﴾⦗⦘«،•*»/\\\\\\-–=.:"ﷺ﷽ﷻ\ufd40\ufd4f\ufdff\ufd4a\ufd44\ufd4b\ufdcf\ufd43\ufd45\ufd42\ufd41\ufdfe\ufd4e\ufd47\ufd4d\ufd48\ufd49\ufd4c؛;!?؟]+'
    return re.sub(f"""<font color=["\\\']?#[0-9A-Fa-f]{{6}}["\\\']?>({punct})</font>""", '<span class="punct">\\1</span>', text)


def legacySearchToCss(text):
    return re.sub('<font id=go color=["\\\']?#[0-9A-Fa-f]{6}["\\\']?>([\\s\\S]*?)</font>', '<span id=go class="search">\\1</span>', text)


def unifySymbols(text):
    return re.sub('(?![^<]*>)([﷽ﷺﷻ\ufd40\ufd4f\ufdff\ufd4a\ufd44\ufd43\ufd45\ufd42\ufd41\ufdfe\ufd4e\ufd47\ufd4d\ufd48\ufd49\ufd4c﴿﴾ ])', '<span class="symbol">\\1</span>', text)


def renderQtHr(text):
    if Across.active_theme == 'dark':
        if text:
            if '<hr' in text.lower():
                from customs import hColor
                color = hColor(Settings.getValue('color_footnotes'))
                separator = f"<div style='background-color:{color}; margin-top:4px; margin-bottom:4px; line-height:1px; font-size:1px;'>&nbsp;</div>"

                def replace_hr(match_object):
                    tag = match_object.group(0)
                    if 'data-shamela-keep=' in tag.lower():
                        return tag
                    return separator

                return re.sub('<hr\\b[^>]*/*>', replace_hr, text, flags=(re.IGNORECASE))
    return text


def coloredHr(default_color=False, breathing=True):
    from customs import hColor
    key = 'color_footnotes'
    color = hColor(Settings.getDefaultColor(key) if default_color else Settings.getValue(key))
    padding = '10px' if breathing else '0'
    return f"<table width='100%' cellspacing='0' cellpadding='0' border='0' style='border-collapse:collapse'><tr><td style='border-bottom:1px solid {color}; font-size:1px; line-height:1px; padding:{padding} 0;'></td></tr></table>"


def tooltipHtml(head, names_list):
    body = f"{head}{coloredHr(breathing=False)}{'<br>'.join(names_list)}"
    return f"<table><tr><td>{body}</td></tr></table>"


def centeredHr(inner, default_color=False):
    side = f"<td valign='middle' style='padding:0; '>{coloredHr(default_color, breathing=False)}</td>"
    word = f"<td width='1%' valign='middle' style='white-space:nowrap; vertical-align:middle; padding-left:0.6em; padding-right:0.6em'><div>{inner}</div></td>"
    return f"<table style='border-collapse:collapse; margin-top:0.6em; margin-bottom:0.6em;' width=100%><tr>{side}{word}{side}</tr></table>"


def wrap(text=None, style=None, plain_text=None):
    if text:
        text = renderQtHr(text)
        style = f"<head><style>{style}</style></head>" if style else ''
        if not plain_text:
            text = colourizePunctuation(text)
        return f"<html dir=rtl>{style}<body>{text}</body></html>"


def quranTableColors(border, background, css_type):
    padding = '; padding-left:0.25em; padding-right:0.25em; padding-bottom:0.30em; padding-top:0.1em;}' if css_type == 'amiri' else '; padding: 0.5em}'
    return 'table {background-color: ' + border + ';} td {background-color: ' + background + padding


def formatManSummary(long, summary_list, free):
    from cache import CssCache
    from customs import hColor
    color = hColor(Settings.getValue('color_text'))
    pre = f"<span class='title'>الاسم: </span>{long}"
    final = []
    for title, text in summary_list:
        final.append(f"<p><span class='title'>{title}: </span>{text}")

    summary_html = f'<span style="color: {color}">' + arabize(commaFix(f"{pre}{''.join(final)}"), True) + '</span>'
    if free:
        ul, ull, li, lii = ('<ul>', '</ul>', '<li>', '</li>') if len(free) > 1 else ('',
                                                                                     '',
                                                                                     '',
                                                                                     '')
        free_text = []
        for line in free:
            free_line = f"{li}{line[0]}<br><span class='footnote'>[{line[1]}]</span>{lii}"
            free_text.append('<p>'.join(free_line.splitlines()))

        free_html = f'<span style="color: {color}">' + arabize(commaFix(f"{ul}{''.join(free_text)}{ull}"), True) + '</span>'
        return wrap(summary_html + coloredHr() + free_html, CssCache.getCache('man'))
    return wrap(summary_html, CssCache.getCache('man'))


def formatGarh(garh, fwaed):
    from cache import CssCache
    from customs import hColor
    color = hColor(Settings.getValue('color_text'))

    def addToList(m_list, j_list):
        for item in j_list:
            m_list.append(f"<p><span class='title'>{item[0]}: </span><ul>")
            for qawl in item[1]:
                m_list.append(f"<li>{qawl[0]} <span class='footnote'>[{qawl[1]}]</span></li>")

            m_list.append('</ul><p>')

    def make_span(items):
        return f'<span style="color: {color}">' + arabize(commaFix(''.join(items)), True) + '</span>'

    garh_items, fwaed_items = [], []
    if garh:
        addToList(garh_items, garh)
    if fwaed:
        addToList(fwaed_items, fwaed)
    html_parts = []
    if garh_items:
        html_parts.append(make_span(garh_items))
    if garh:
        if fwaed:
            html_parts.append(centeredHr("<span class='title'>[تنبيهات وفوائد]</span>"))
    if fwaed_items:
        html_parts.append(make_span(fwaed_items))
    return wrap(''.join(html_parts), CssCache.getCache('man'))


def formatStandaloneSeparators(text):
    if text:
        if Across.separator in text:
            separator = f"<span class='h_separator'>{Across.separator}</span>"
            pieces = text.splitlines()
            final = []
            in_footnote = False
            for piece in pieces:
                if piece.strip() == Across.separator:
                    final.append(f"<div class='footnote'>{separator}" if not in_footnote else separator)
                    in_footnote = True
                else:
                    final.append(piece)

            text = '\n'.join(final)
            if in_footnote:
                text += '\n</div>'
    return text


def formatBetaka(text, cover, value, wide, export, printed=None):
    from customs import hColor
    css = f"standard_{printed or 1}"
    from cache import CssCache
    text = text.replace('<hr>', coloredHr(breathing=False))
    if '╦' in text:
        parts = text.split('╦', 1)
        pre, text = f"{parts[0]}<p>", parts[1]
    else:
        pre = ''
    text = formatStandaloneSeparators(text)
    pieces = text.splitlines()
    final = []
    for piece in pieces:
        piece = piece.strip()
        if piece:
            final.append(re.sub('^(?!<)(.{1,100})\\:', "<span class='title'>\\1:</span>", piece))

    new_text = f"""<span style="color: {hColor(Settings.getValue('color_text'))}">""" + paragraph(f"{pre}{colourizePunctuation('<p>'.join(final))}") + '</span>'
    if export:
        return toAsciiDigits(new_text)
        if cover:
            if value:
                width = '100%' if wide else '700'
                value = str(base64.b64encode(value), 'utf-8')
                new_text = f"<table align = 'right' width={width}><tr><td><table><tr><td><img src='data:image;base64,{value}'></td></tr></table><td align='right'><table><tr><td>&nbsp;&nbsp;&nbsp;&nbsp;</td><td align='right'>{new_text}</td></tr></table></td></tr></table></body>"
                return wrap(new_text, (CssCache.getCache(css)), plain_text=True)
    elif value:
        return wrap(f'<table width=100%"><tr><td>{new_text}{coloredHr(breathing=False)}{formatHint(value)}</td></tr></table>', (CssCache.getCache(css)), plain_text=True)
    return wrap(f'<table">{new_text}</table>', (CssCache.getCache(css)), plain_text=True)


def formatHint(text, full=False):
    from cache import CssCache
    from customs import hColor
    if text:
        text = formatStandaloneSeparators(text)
        pieces = text.splitlines()
        pieces[0] = f"<span class='title'><div align = center>{pieces[0]}</div></span>"
        content = f"""<span style="color: {hColor(Settings.getValue('color_text'))}">""" + commaFix('<p>'.join(pieces)) + '</span>'
        if full:
            return wrap(content, CssCache.getCache('standard'))
        return colourizePunctuation(content)
    return ''


def formatAuthor(text):
    from cache import CssCache
    from customs import hColor
    if text:
        text = formatStandaloneSeparators(text)
        color = hColor(Settings.getValue('color_text'))
        if '<hr>' in text:
            head, rest = text.split('<hr>', 1)
            html = f"""<span style="color: {color}">{'<p>'.join(head.splitlines())}</span>""" + coloredHr(breathing=False) + f"""<span style="color: {color}">{'<p>'.join(rest.splitlines())}</span>"""
        else:
            html = f"""<span style="color: {color}">{'<p>'.join(text.splitlines())}</span>"""
        return commaFix(wrap(html, CssCache.getCache('standard')))
    return ''


def paragraph(s):
    if s:
        return s.replace('<p><p>', '<p>&nbsp;<p>')


def commaFix(text):
    return paragraph(text.replace(',', '،'))


_METRIC_PROBE_PX = 512
_USE_TYPO_METRICS = 128
_MIN_LINE_FACTOR = 0.5
_MAX_LINE_FACTOR = 1.5
_line_factors = {}
AMIRI_FAMILY = 'Amiri Quran'
MAJMA_FAMILY = 'KFGQPC HAFS Uthmanic Script'
SEPARATOR_FAMILY = 'Vazirmatn UI Decurled'

def _fontTable(raw, tag):
    """A raw font table as plain bytes. PySide2 and PySide6 differ on whether
    fontTable() hands back a QByteArray or bytes, so normalise here."""
    table = raw.fontTable(tag)
    if table is None:
        return b''
    return bytes(table.data() if hasattr(table, 'data') else table)


def _requestedLineHeight(probe):
    """The line box *probe*'s font file asks for, in em, or None if unreadable.

    Reads OS/2 directly rather than trusting the engine — that is the whole
    point. Any binding or table surprise falls through to None, i.e. to the
    uncorrected setting, so this can never be worse than not correcting."""
    try:
        from qtpy.QtGui import QRawFont
        raw = QRawFont.fromFont(probe)
        if not raw.isValid():
            return
        os2, head = _fontTable(raw, 'OS/2'), _fontTable(raw, 'head')
        if len(os2) < 78 or len(head) < 20:
            return
        units = struct.unpack('>H', head[18:20])[0]
        if not units:
            return
        fs_selection = struct.unpack('>H', os2[62:64])[0]
        if fs_selection & _USE_TYPO_METRICS:
            ascent, descent, gap = struct.unpack('>hhh', os2[68:74])
            return (ascent - descent + gap) / units
        ascent, descent = struct.unpack('>HH', os2[74:78])
        return (ascent + descent) / units
    except Exception:
        return


def _lineFactor(l_font):
    """How much to stretch a line-height setting for *l_font* so that it means the
    pitch the font asks for on this machine's engine. 1.0 when they already agree,
    and whenever the font cannot be measured.

    Family-agnostic: whatever the user picks in the font dialog is measured the
    same way, no per-font table. Of the 194 families on a stock macOS only four
    fall outside the clamp below, and none of them are Arabic text faces."""
    listed = isinstance(l_font, (list, tuple))
    family = l_font[0] if listed else l_font
    bold = bool(l_font[2]) if (listed and len(l_font) > 2) else False
    if (family, bold) in _line_factors:
        return _line_factors[(family, bold)]
    else:
        probe = QFont(family)
        probe.setBold(bold)
        probe.setPixelSize(_METRIC_PROBE_PX)
        if QFontInfo(probe).family() != family:
            return 1.0
        natural = QFontMetricsF(probe).height() / _METRIC_PROBE_PX
        requested = _requestedLineHeight(probe)
        return natural and requested or 1.0
    factor = min(max(requested / natural, _MIN_LINE_FACTOR), _MAX_LINE_FACTOR)
    _line_factors[(family, bold)] = factor
    return factor


def lineHeight(spacing_key, l_font):
    """The line-height CSS value for *spacing_key* as rendered in *l_font* — the
    user's setting, corrected for the font engine (see the note above). Pass the
    font setting list (or a bare family) the rule's text is actually drawn in;
    passing the wrong family only mis-sizes the correction, never the font."""
    return round(Settings.getValue(spacing_key) * _lineFactor(l_font), 3)


def buildCss(css_type):
    from customs import hColor
    title_color = hColor(Settings.getValue('color_titles'))
    matn_color = hColor(Settings.getValue('color_matn'))
    footnotes_color = hColor(Settings.getValue('color_footnotes'))
    general_style = '.punct {color: ' + hColor(Settings.getValue('color_punctuate')) + ';} '
    general_style += '.search {color: ' + hColor(Settings.getValue('color_search')) + ';} '
    general_style += 'hr {background-color: ' + hColor(Settings.getValue('color_footnotes')) + ';} '
    printed = '1'
    if '_' in css_type:
        pieces = css_type.split('_')
        printed = pieces[1]
        css_type = pieces[0]
    elif printed == '1':
        background_color = hColor(Settings.getValue('color_text_back'))
    else:
        background_color = hColor(Settings.getValue('color_text_back_unprinted'))
    if css_type == 'p':
        pages_pt = Settings.getValue('font_pages')[1]
        footnotes_pt = Settings.getValue('font_footnotes')[1]
        css = 'a, u {text-decoration: none; color: ' + hColor(Settings.getValue('color_men')) + ';} body {margin-left: 3; margin-right: 3; background-color: ' + background_color + '; '
        css += 'color: ' + hColor(Settings.getValue('color_text')) + '; '
        css += hFont(Settings.getValue('font_pages')) + f" line-height: {lineHeight('font_pages_spacing', Settings.getValue('font_pages'))};" + '} '
        css += 'p {margin: 0px;} '
        bottom_pad = pages_pt
        if bottom_pad < 15:
            bottom_pad = 15
        css += '.qqtable {margin-top:' + (f"{bottom_pad}") + '; background-color: ' + title_color + '} .qqtable TD {background-color: ' + background_color + '; padding-left:10; padding-right:10; padding-top:5; padding-bottom:' + (f"{bottom_pad}") + '; vertical-align:middle;} .qqtable TH {background-color: ' + hColor(Settings.getValue('color_comments_back')) + '; padding-left:23; padding-right:23; padding-top:5; padding-bottom:' + (f"{bottom_pad}") + '; vertical-align:middle; text-align:center}'
        css += 'span[data-type=title] {color: ' + title_color + ';} '
        css += '.title {color: ' + title_color + ';} '
        css += '.matn {color: ' + matn_color + '; '
        css += hFont(Settings.getValue('font_matn')) + '} '
        css += '.symbol {font-family: Kitab; font-weight: normal} '
        css += '.mobham {color: ' + footnotes_color + ';} '
        css += '.footnote {' + hFont(Settings.getValue('font_footnotes')) + f" line-height: {lineHeight('font_footnotes_spacing', Settings.getValue('font_footnotes'))};" + ' color: ' + footnotes_color + ';} '
        css += '.h_separator {font: ' + (f"{scaled_font_size(14)}") + f'pt "{SEPARATOR_FAMILY}";' + f" line-height: {lineHeight('font_footnotes_spacing', SEPARATOR_FAMILY)};" + ' color: ' + footnotes_color + '; } '
        return css + general_style
        if css_type == 'c':
            css = 'QTextEdit {background-color: ' + hColor(Settings.getValue('color_comments_back')) + '; '
            css += 'color: ' + hColor(Settings.getValue('color_comments')) + '; '
            css += hFont(Settings.getValue('font_comments')) + '} '
            return css + general_style
        if css_type == 't':
            css = 'body {background-color: ' + hColor(Settings.getValue('color_comments_back')) + '; '
            css += 'color: ' + hColor(Settings.getValue('color_comments')) + '; '
            css += hFont(Settings.getValue('font_pages')) + f" line-height: {lineHeight('font_pages_spacing', Settings.getValue('font_pages'))};" + '} '
            css += '.symbol {font-family: Kitab; font-weight: normal} '
            css += 'p {margin: 0px;}'
            return css + general_style
        if css_type == 's':
            return hColor(Settings.getValue('color_search'))
        if css_type == 'h':
            return title_color
        if css_type == 'punct':
            return hColor(Settings.getValue('color_punctuate'))
        if css_type in ('amiri', 'majma', 'emlaa'):

            def quranColor(key):
                return hColor(Settings.getDefaultColor(key))

            title_color = quranColor('color_titles')
            punctuate_color = quranColor('color_punctuate')
            footnotes_color = quranColor('color_footnotes')
            text_color = quranColor('color_text')
            background = quranColor('color_text_back')
            outer_color = quranColor('color_comments_back')
            css = quranTableColors(title_color, background, css_type)
            css += 'span.title {color: ' + title_color + ';} '
            css += 'span.punct {color: ' + title_color + ';} '
            css += '.symbol {font-family: Kitab; font-weight: normal;} '
            css += '.symbol .punct {color: ' + punctuate_color + ';} '
            css += '.search {color: ' + quranColor('color_search') + ';} '
            css += 'hr {background-color: ' + footnotes_color + ';} '
            css += 'body {margin-top: 6; margin-bottom: 6; background-color: ' + outer_color + ';'
            if css_type == 'amiri':
                return css + 'font: ' + (f"{scaled_font_size(Settings.getValue('amiri_size'))}") + 'pt "Amiri Quran";' + f" line-height: {lineHeight('amiri_spacing', AMIRI_FAMILY)};" + ' color: ' + text_color + ';} '
            if css_type == 'majma':
                return css + 'font: ' + (f"{scaled_font_size(Settings.getValue('majma_size'))}") + 'pt "KFGQPC HAFS Uthmanic Script";' + f" line-height: {lineHeight('majma_spacing', MAJMA_FAMILY)};" + ' color: ' + text_color + ';} '
            if css_type == 'emlaa':
                fp = Settings.getValue('font_pages')
                emlaa_font = [fp[0], Settings.getValue('emlaa_size'), fp[2], fp[3]]
                return css + hFont(emlaa_font) + f" line-height: {lineHeight('emlaa_spacing', emlaa_font)};" + ' color: ' + text_color + ';} '
    else:
        if css_type == 'man':
            css = 'body {margin-left: 3; margin-right: 3; background-color: ' + hColor(Settings.getValue('color_text_back')) + '; padding: 5px;'
            css += hFont(Settings.getValue('font_betaka')) + f" line-height: {lineHeight('font_betaka_spacing', Settings.getValue('font_betaka'))};" + '} '
            css += '.title {color: ' + hColor(Settings.getValue('color_titles')) + '; } '
            css += 'p {margin: 0px;}'
            css += '.footnote {' + hFont(Settings.getValue('font_betaka')) + f" line-height: {lineHeight('font_betaka_spacing', Settings.getValue('font_betaka'))};" + ' color: ' + hColor(Settings.getValue('color_footnotes')) + ';} '
            css += 'span.h_separator {font: ' + (f"{scaled_font_size(14)}") + f'pt "{SEPARATOR_FAMILY}";' + f" line-height: {lineHeight('font_betaka_spacing', SEPARATOR_FAMILY)};" + ' color: ' + footnotes_color + '; } '
            return css + general_style
        if css_type == 'standard':
            css = 'body {margin-left: 3; margin-right: 3; background-color: ' + background_color + '; padding: 5px;'
            css += hFont(Settings.getValue('font_betaka')) + f" line-height: {lineHeight('font_betaka_spacing', Settings.getValue('font_betaka'))};" + '} '
            css += '.title {color: ' + hColor(Settings.getValue('color_titles')) + '; } '
            css += 'p {margin: 0px;}'
            css += '.footnote {' + hFont(Settings.getValue('font_betaka')) + f" line-height: {lineHeight('font_betaka_spacing', Settings.getValue('font_betaka'))};" + ' color: ' + hColor(Settings.getValue('color_footnotes')) + ';} '
            css += 'div.footnote {' + hFont(Settings.getValue('font_betaka')) + f" line-height: {lineHeight('font_betaka_spacing', Settings.getValue('font_betaka'))};" + ' color: ' + hColor(Settings.getValue('color_footnotes')) + ';} '
            css += 'span.h_separator {font: ' + (f"{scaled_font_size(14)}") + f'pt "{SEPARATOR_FAMILY}";' + f" line-height: {lineHeight('font_betaka_spacing', SEPARATOR_FAMILY)};" + ' color: ' + footnotes_color + '; } '
            return css + general_style
    if css_type == 'tip':
        css = 'body {margin-left: 3; margin-right: 3; background-color: ' + hColor(Settings.getValue('color_text_back')) + '; padding: 5px;'
        css += hFont(Settings.getValue('font_betaka')) + f" line-height: {lineHeight('font_pages_spacing', Settings.getValue('font_betaka'))};" + '} '
        css += '.title {color: ' + hColor(Settings.getValue('color_titles')) + '; } '
        css += '.symbol {font-family: Kitab; font-weight: normal} '
        css += 'p {margin: 0px;}'
        css += '.footnote {' + hFont(Settings.getValue('font_betaka')) + f" line-height: {lineHeight('font_pages_spacing', Settings.getValue('font_betaka'))};" + ' color: ' + hColor(Settings.getValue('color_footnotes')) + ';} '
        css += 'div.footnote {' + hFont(Settings.getValue('font_betaka')) + f" line-height: {lineHeight('font_pages_spacing', Settings.getValue('font_betaka'))};" + ' color: ' + hColor(Settings.getValue('color_footnotes')) + ';} '
        css += 'span.h_separator {font: ' + (f"{scaled_font_size(14)}") + f'pt "{SEPARATOR_FAMILY}";' + f" line-height: {lineHeight('font_pages_spacing', SEPARATOR_FAMILY)};" + ' color: ' + footnotes_color + '; } '
        return css + general_style


def iso(s):
    s = s.translate(Across.iso_table)
    s = re.sub('[\\W\\sـ]+', ' ', s).strip()
    return s


def searchHighlightColor(cobalt=False):
    if cobalt:
        if Across.active_theme == 'modern_light':
            return '#9F2F24'
        return '#FFA277'
    if Across.active_theme != 'native_light':
        if Across.active_theme == 'dark':
            return '#F28B82'
        return '#C43E2F'
    return '#D20000'


def red(text, cobalt=False):
    mapping_dict = {}
    mapping_dict['\x01'] = f"<font color={searchHighlightColor(cobalt)}>"
    mapping_dict['\x02'] = '</font>'
    tbl = str.maketrans(mapping_dict)
    return '<style>a, u {text-decoration: none}</style>' + safehtml(text.translate(tbl))


def linear(s):
    from cache import HonorificCache
    if s:
        s = re.sub('\\s+', ' ', noTashkeel(s)).strip()
        return s.translate(HonorificCache.plainTable())


def noTashkeel(s):
    if s:
        return s.translate(Across.diac_table)


def textAuthorFolder(author_name, author_death):
    death = int(author_death)
    if death == 0:
        return '0000 المجاميع'
    if death == 99998:
        return '0000 المجهولون'
    if death < 0:
        return f"0000 العصر الجاهلي/{str(death + 621).zfill(4)} {safeName(author_name)}"
    if death == 99999:
        return f"0000 المعاصرون/{safeName(author_name)}"
    return safeName(f"{str(death).zfill(4)} {author_name}")


def safeName(filename, folder=None, max_len=None):
    tbl = str.maketrans('<|\\>:?/*"', '         ')
    filename = linear(filename.translate(tbl).strip())
    filename = filename.replace(' و ', ' و')
    filename = filename.replace('ـ', '')
    filename = re.sub('\\s+', ' ', filename)
    if max_len:
        l = max_len
    else:
        if folder:
            l = 200 - len(folder)
        else:
            l = 150
    if len(filename) > l:
        filename = filename[:l]
        pos = filename.rfind(' ')
        if pos != -1:
            filename = filename[:pos]
    return filename


def val(text):
    try:
        return int(re.findall('\\d+|$', text)[0])
    except Exception:
        return 0


def displayDate(date_string):
    day = arabize((f"{int(date_string[:2])}"), True)
    month = months[int(date_string[2:4]) - 1]
    year = arabize(date_string[4:], True)
    return f"{day} {month} {year}"


def reverseNumbers(s, separator):
    from qtpy import API
    if API != 'pyside2':
        return s
    if s:
        pieces = s.split(separator)
        numerical = None
        for i, piece in enumerate(pieces):
            if piece.startswith(': '):
                pieces[i] = pieces[i][:2] + pieces[i][-1:1:-1]
                numerical = True

        if numerical:
            return separator.join(pieces)
        return s


def naturalsize(value, arabic=True, format='%.0f'):
    """Format a number of bytes like a human readable filesize (eg. 10 kB).

    By default, arabic suffixes are used. use arabic=False For English
    By default, No fractions. use format='%.1f' or format='%.2f'
    """
    if arabic:
        suffix = suffixes['arabic']
    else:
        suffix = suffixes['english']
    base = 1024
    bytes = float(value)
    abs_bytes = abs(bytes)
    if abs_bytes < base:
        if arabic:
            return '%d بايت' % bytes
        return '%d Bytes' % bytes
    for i, s in enumerate(suffix):
        unit = base ** (i + 2)
        if abs_bytes < unit:
            return (format + ' %s') % (base * bytes / unit, s)

    return (format + ' %s') % (base * bytes / unit, s)


def contains(iso_text, pieces):
    for piece in pieces:
        if piece not in iso_text:
            return

    return True


def plain(html_txt):
    return QTextDocumentFragment.fromHtml(html_txt).toPlainText().strip()


def reverseRows(s):
    if s:
        root = _parse_html(s)
        for row in root.find_all('tr'):
            row.children = list(reversed(row.children))

        for table in root.find_all('table'):
            table.attrs['dir'] = 'rtl'

        return root.to_html()


def isRich(s):
    if s:
        if '<td' not in s:
            if '<TD' not in s:
                return
        return True