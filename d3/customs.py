# decompyle3 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: customs.py
import json
from html.parser import HTMLParser
import os, shutil, subprocess
from pathlib import Path
import stat, sys, msgpack, regex as re
from across import Across
from scaling import scaled_font_size
if Across.os == 'win':
    import winshell, userpaths, win32api, ctypes
    from installwinfont import installWinFont, notify
else:
    winshell = userpaths = win32api = ctypes = None
    installWinFont = notify = None
from qtpy.QtCore import QByteArray, QItemSelectionModel, QAbstractListModel, QCoreApplication, QAbstractTableModel, QSettings, QModelIndex, QPointF, QTimer, QFile, QSize, Qt, QMimeData, Signal, QUrl, QLocale, QEvent
from qtpy.QtGui import QBrush, QIcon, QKeyEvent, QStandardItem, QStandardItemModel, QFontMetrics, QPainter, QPixmap, QColor, QFont, QTextCursor, QPalette, QKeySequence, QDesktopServices, QTextOption
from qtpy.QtWidgets import QApplication, QShortcut, QComboBox, QTableView, QDialog, QListWidgetItem, QLineEdit, QListWidget, QLabel, QFrame, QMessageBox, QSizePolicy, QPushButton, QToolButton, QHeaderView, QAbstractItemView, QSpacerItem, QWidget, QLayout, QVBoxLayout, QHBoxLayout, QSplitter, QTextBrowser, QTextEdit, QAction, QPlainTextEdit, QListView, QStackedWidget, QMenu
from cache import BookCache, HonorificCache
from dirs import pdfPath, extraPdfPath, userPath
from theme import Icon
from quraninfo import ayaFromPage, posFromAya, getSoraNames
from settings import Settings
from textmanager import val, arabize, latinize, treatSearch, iso, contains, noTashkeel, reverseNumbers, plain, reverseRows, isRich, clean_invisible, toAsciiDigits, displayDigits, legacyPunctuationToCss, legacySearchToCss
import zipfile
from platformutils import desktop_dir, menu_shortcut_supported, shortcut_target
SEP = '\n     '
WORD_XML_CLIPBOARD_FILE_MIME = 'application/x-shamela-word-xml-file'
CACHED_BRUSH_GRAY = QBrush(QColor(84, 84, 84))
CACHED_BRUSH_WHITE = QBrush(Qt.white)
CACHED_BRUSH_BLACK = QBrush(Qt.black)
CACHED_BRUSH_DARK_RED = QBrush(Qt.darkRed)
CACHED_BRUSH_DARK_GREEN = QBrush(Qt.darkGreen)
CACHED_BRUSH_LIGHT_RED = QBrush(QColor(242, 139, 130))
CACHED_BRUSH_LIGHT_GREEN = QBrush(QColor(129, 201, 149))
CACHED_BRUSH_BLUE = QBrush(Qt.blue)
CACHED_BRUSH_LIGHT_BLUE = QBrush(QColor(120, 170, 240))

def alert_brush():
    """Theme-aware red: light red in dark theme, dark red in light theme."""
    if Across.active_theme == 'dark':
        return CACHED_BRUSH_LIGHT_RED
    return CACHED_BRUSH_DARK_RED


CACHED_BRUSH_DARK_GRAY = QBrush(Qt.darkGray)
NSPasteboard = NSPasteboardItem = NSData = NSURL = None
_NATIVE_CLIPBOARD_IMPORT_ATTEMPTED = False

def checkStateValue(value):
    if isinstance(value, bool):
        return checkStateValue(Qt.Checked if value else Qt.Unchecked)
    try:
        return int(value)
    except:
        pass

    try:
        return int(value.value)
    except:
        pass

    return value


def toCheckState(value):
    if isinstance(value, bool):
        if value:
            return Qt.Checked
        return Qt.Unchecked
    value = checkStateValue(value)
    if value == checkStateValue(Qt.PartiallyChecked):
        return Qt.PartiallyChecked
    if value == checkStateValue(Qt.Checked):
        return Qt.Checked
    return Qt.Unchecked


def isCheckedState(value):
    if isinstance(value, bool):
        return value
    return checkStateValue(value) == checkStateValue(Qt.Checked)


_clipboard_routing = {
  'active': False,
  'xml_path': None,
  'rtf_bytes': None,
  'html': '',
  'text': '',
  'rtf_change_count': None,
  'word_change_count': None}
_clipboard_routing_timer = None
_clipboard_exit_hooked = False

def _ensureNativeClipboardApi():
    """Load PyObjC clipboard APIs on demand so macOS startup stays light."""
    global NSData
    global NSPasteboard
    global NSPasteboardItem
    global NSURL
    global _NATIVE_CLIPBOARD_IMPORT_ATTEMPTED
    if _NATIVE_CLIPBOARD_IMPORT_ATTEMPTED:
        return bool(NSPasteboard and NSPasteboardItem and NSData)
    _NATIVE_CLIPBOARD_IMPORT_ATTEMPTED = True
    if Across.os != 'mac':
        return False
    try:
        from AppKit import NSPasteboard as _NSPasteboard, NSPasteboardItem as _NSPasteboardItem
        from Foundation import NSData as _NSData, NSURL as _NSURL
    except ImportError:
        return False
    else:
        NSPasteboard = _NSPasteboard
        NSPasteboardItem = _NSPasteboardItem
        NSData = _NSData
        NSURL = _NSURL
        return True


def _startClipboardRoutingTimer():
    """Start (or restart) the 100 ms clipboard-routing poll timer."""
    global _clipboard_routing_timer
    if _clipboard_routing_timer is None:
        _clipboard_routing_timer = QTimer()
        _clipboard_routing_timer.timeout.connect(_clipboardRoutingTick)
    _clipboard_routing_timer.start(100)
    _ensureClipboardExitHook()


def _ensureClipboardExitHook():
    """Connect the aboutToQuit finalizer exactly once."""
    global _clipboard_exit_hooked
    if _clipboard_exit_hooked:
        return
    app = QApplication.instance()
    if app is None:
        return
    app.aboutToQuit.connect(_finalizeClipboardOnExit)
    _clipboard_exit_hooked = True


def _writeUniversalPasteboard(rtf_bytes, html, text):
    """Write a single static item carrying RTF + HTML + plain text (no file-url).

    This is the 'goodbye' clipboard left when the app quits mid-Majma-routing:
    every app can still paste after we're gone.  Word loses the Uthmanic glyph
    shaping (it would otherwise import the WordML file) but keeps correct text;
    all other apps paste fully formatted.
    """
    if not _ensureNativeClipboardApi():
        return
    pasteboard = NSPasteboard.generalPasteboard()
    if pasteboard is None:
        return
    item = NSPasteboardItem.alloc().init()
    if rtf_bytes:
        item.setData_forType_(NSData.dataWithBytes_length_(rtf_bytes, len(rtf_bytes)), 'public.rtf')
    if html:
        html_bytes = html.encode('utf-8')
        item.setData_forType_(NSData.dataWithBytes_length_(html_bytes, len(html_bytes)), 'public.html')
    if text:
        utf8 = text.encode('utf-8')
        item.setData_forType_(NSData.dataWithBytes_length_(utf8, len(utf8)), 'public.utf8-plain-text')
    pasteboard.clearContents()
    pasteboard.writeObjects_([item])


def _finalizeClipboardOnExit():
    """On quit, collapse any active Majma routing to a universal RTF/HTML/plain
    pasteboard so pasting still works after the app is gone."""
    state = _clipboard_routing
    if not state.get('active'):
        return
    state['active'] = False
    if _clipboard_routing_timer is not None:
        _clipboard_routing_timer.stop()
    if not _ensureNativeClipboardApi():
        return
    try:
        pasteboard = NSPasteboard.generalPasteboard()
        cc = pasteboard.changeCount()
        if cc == state.get('rtf_change_count') or cc == state.get('word_change_count'):
            _writeUniversalPasteboard(state.get('rtf_bytes'), state.get('html'), state.get('text'))
    except Exception:
        pass

    kill(state.get('xml_path'))


def _writeRtfPasteboard(rtf_bytes, text):
    """Write RTF + plain text as real pasteboard data.  Returns new changeCount."""
    if not _ensureNativeClipboardApi():
        return
    pasteboard = NSPasteboard.generalPasteboard()
    if pasteboard is None:
        return
    item = NSPasteboardItem.alloc().init()
    nsdata = NSData.dataWithBytes_length_(rtf_bytes, len(rtf_bytes))
    item.setData_forType_(nsdata, 'public.rtf')
    if text:
        utf8 = text.encode('utf-8')
        item.setData_forType_(NSData.dataWithBytes_length_(utf8, len(utf8)), 'public.utf8-plain-text')
    pasteboard.clearContents()
    if pasteboard.writeObjects_([item]):
        return pasteboard.changeCount()


def _writeFileurlPasteboard(xml_path):
    """Write a file-url-only pasteboard for MS Word.  Returns new changeCount."""
    if not (_ensureNativeClipboardApi() and NSURL):
        return
    pasteboard = NSPasteboard.generalPasteboard()
    if pasteboard is None:
        return
    url = NSURL.fileURLWithPath_(xml_path)
    pasteboard.clearContents()
    if pasteboard.writeObjects_([url]):
        return pasteboard.changeCount()


def _clipboardRoutingTick():
    """Called every 100 ms.  Swaps the pasteboard content based on active app."""
    state = _clipboard_routing
    if not state['active']:
        _clipboard_routing_timer.stop()
        return
    if not _ensureNativeClipboardApi():
        return
    try:
        pasteboard = NSPasteboard.generalPasteboard()
        cc = pasteboard.changeCount()
        if cc != state['rtf_change_count']:
            if cc != state['word_change_count']:
                state['active'] = False
                _clipboard_routing_timer.stop()
                return
        from AppKit import NSWorkspace
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        bundle = app.bundleIdentifier() if app else ''
        is_word = bundle == 'com.microsoft.Word'
        if is_word and cc == state['rtf_change_count']:
            new_cc = _writeFileurlPasteboard(state['xml_path'])
            if new_cc is not None:
                state['word_change_count'] = new_cc
                state['rtf_change_count'] = None
        else:
            if not is_word:
                if cc == state['word_change_count']:
                    new_cc = _writeRtfPasteboard(state['rtf_bytes'], state['text'])
                    if new_cc is not None:
                        state['rtf_change_count'] = new_cc
                        state['word_change_count'] = None
    except Exception:
        pass


def _stripQuotes(value):
    value = value.strip()
    if len(value) > 1:
        if value[0] == value[-1]:
            if value[0] in frozenset({"'", '"'}):
                return value[1:-1].strip()
    return value


def _parseFontFamily(value):
    family = _stripQuotes(value.split(',', 1)[0].strip())
    return family or None


def _parseFontSize(value):
    match = re.search('([\\d.]+)\\s*pt', value, re.I)
    if match:
        return round(float(match.group(1)) * 2)


def _parseInlineStyle(style_text):
    style = {}
    if not style_text:
        return style
    for chunk in style_text.split(';'):
        if ':' not in chunk:
            continue
        else:
            key, value = [part.strip() for part in chunk.split(':', 1)]
            key = key.lower()
            lowered = value.lower()
        if key == 'font-family':
            family = _parseFontFamily(value)
            if family:
                style['font'] = family
        else:
            if key == 'font-size':
                size = _parseFontSize(value)
                if size:
                    style['size'] = size
        if key == 'font-weight':
            style['bold'] = lowered in frozenset({'900', '800', '700', 'bold', '600'})
        else:
            if key == 'font-style':
                style['italic'] = lowered == 'italic'
        if key == 'font':
            size = _parseFontSize(value)
            if size:
                style['size'] = size
            family_match = re.search('pt\\s+(.+)$', value, re.I)
            if family_match:
                family = _parseFontFamily(family_match.group(1))
                if family:
                    style['font'] = family

    return style


class ClipboardHtmlParser(HTMLParser):
    __doc__ = "Parse Shamela's simple clipboard HTML into RTL paragraphs and styled runs."

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = []
        self.current_paragraph = None
        self.style_stack = [{}]
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs}
        pushed_style = False
        inherited = dict(self.style_stack[-1])
        inline_style = _parseInlineStyle(attr_map.get('style'))
        if tag == 'font':
            face = attr_map.get('face')
            if face:
                inherited['font'] = _parseFontFamily(face) or inherited.get('font')
            size = attr_map.get('size')
            if size:
                try:
                    inherited['size'] = int(size) * 2
                except ValueError:
                    pass

                inherited.update(inline_style)
                if tag in frozenset({'b', 'strong'}):
                    inherited['bold'] = True
                else:
                    if tag in frozenset({'em', 'i'}):
                        inherited['italic'] = True
                    else:
                        if tag in frozenset({'p', 'span', 'font', 'body'}):
                            pass
            if tag in frozenset({'p', 'span', 'i', 'font', 'body', 'b', 'em', 'strong'}):
                self.style_stack.append(inherited)
                pushed_style = True
        if tag == 'p':
            rtl = attr_map.get('dir', '').lower() == 'rtl'
            self.current_paragraph = {'rtl':rtl,  'runs':[]}
            self.paragraphs.append(self.current_paragraph)
        else:
            if tag == 'br':
                if self.current_paragraph:
                    self._appendText('\n')
        self.tag_stack.append((tag, pushed_style))

    def handle_endtag(self, tag):
        tag = tag.lower()
        while self.tag_stack:
            open_tag, pushed_style = self.tag_stack.pop()
            if pushed_style:
                if len(self.style_stack) > 1:
                    self.style_stack.pop()
            if open_tag == tag:
                break

        if tag == 'p':
            self.current_paragraph = None

    def handle_data(self, data):
        if not self.current_paragraph:
            return
        if not data:
            return
        if not data.strip():
            if '\xa0' not in data:
                return
        self._appendText(data.replace('\r', ''))

    def _appendText(self, text):
        if not text:
            return
        style = self.style_stack[-1]
        run = {'text':text, 
         'font':style.get('font'), 
         'size':style.get('size'), 
         'bold':bool(style.get('bold')), 
         'italic':bool(style.get('italic'))}
        runs = self.current_paragraph['runs']
        if runs and all((runs[-1][key] == run[key] for key in ('font', 'size', 'bold',
                                                               'italic'))):
            runs[-1]['text'] += text
        else:
            runs.append(run)


def _escapeRtfText(text):
    parts = []
    for char in text:
        code = ord(char)
        if char == '\\':
            parts.append('\\\\')
        else:
            if char == '{':
                parts.append('\\{')
            else:
                if char == '}':
                    parts.append('\\}')
                else:
                    if char == '\t':
                        parts.append('\\tab ')
                    else:
                        if char == '\n':
                            parts.append('\\line ')
                        else:
                            if 32<= code < 127:
                                parts.append(char)
                            else:
                                if code <= 65535:
                                    if code > 32767:
                                        code -= 65536
                                    else:
                                        parts.append(f"\\u{code}?")
                                else:
                                    utf16 = char.encode('utf-16-le')
                                    for index in range(0, len(utf16), 2):
                                        unit = int.from_bytes((utf16[index:index + 2]), 'little', signed=False)
                                        if unit > 32767:
                                            unit -= 65536
                                        else:
                                            parts.append(f"\\u{unit}?")

    return ''.join(parts)


def _escapeXmlText(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _escapeXmlAttr(text):
    return _escapeXmlText(text).replace('"', '&quot;').replace("'", '&apos;')


def _wordXmlTextNodes(text):
    lines = text.split('\n')
    parts = []
    for index, line in enumerate(lines):
        if line:
            parts.append(f"          <w:t>{_escapeXmlText(line)}</w:t>")
        if index < len(lines) - 1:
            parts.append('          <w:br/>')

    return '\n'.join(parts)


def wordXmlClipboardBytes(html):
    """Build Word 2003 XML bytes from Shamela clipboard HTML."""
    if not html:
        return
    parser = ClipboardHtmlParser()
    parser.feed(html)
    parser.close()
    paragraphs = [paragraph for paragraph in parser.paragraphs if paragraph['runs']]
    if not paragraphs:
        return
    default_font = 'Traditional Naskh'
    fonts = []
    for paragraph in paragraphs:
        for run in paragraph['runs']:
            font = run['font'] or default_font
            if font not in fonts:
                fonts.append(font)

    if default_font not in fonts:
        fonts.append(default_font)
    font_lines = '\n'.join((f'    <w:font w:name="{_escapeXmlAttr(font)}"/>' for font in fonts))
    paragraph_lines = []
    for paragraph in paragraphs:
        p_pr_xml = '          <w:bidi/>' if paragraph['rtl'] else ''
        run_lines = []
        for run in paragraph['runs']:
            text = run['text']
            if not text:
                continue
            else:
                font = _escapeXmlAttr(run['font'] or default_font)
                size = run['size'] or 24
                bold = '            <w:b/>\n' if run['bold'] else ''
                italic = '            <w:i/>\n' if run.get('italic') else ''
                rtl = '            <w:rtl/>\n' if paragraph['rtl'] else ''
                run_lines.append(f'        <w:r>\n          <w:rPr>\n            <w:rFonts w:ascii="{font}" w:h-ansi="{font}" w:cs="{font}"/>\n            <w:sz w:val="{size}"/>\n            <w:sz-cs w:val="{size}"/>\n{bold}{italic}{rtl}          </w:rPr>\n{_wordXmlTextNodes(text)}\n        </w:r>')

        runs_xml = '\n'.join(run_lines)
        if p_pr_xml:
            paragraph_lines.append(f"      <w:p>\n        <w:pPr>\n{p_pr_xml}\n        </w:pPr>\n{runs_xml}\n      </w:p>")
        else:
            paragraph_lines.append(f"      <w:p>\n{runs_xml}\n      </w:p>")

    default_font_xml = _escapeXmlAttr(default_font)
    paragraphs_xml = '\n'.join(paragraph_lines)
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<?mso-application progid="Word.Document"?>\n<w:wordDocument\n  xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"\n  xmlns:wx="http://schemas.microsoft.com/office/word/2003/auxHint"\n  xmlns:o="urn:schemas-microsoft-com:office:office"\n  xml:space="preserve">\n  <o:DocumentProperties>\n    <o:Title>Shamela clipboard</o:Title>\n  </o:DocumentProperties>\n  <w:fonts>\n{font_lines}\n  </w:fonts>\n  <w:styles>\n    <w:style w:type="paragraph" w:default="on" w:styleId="Normal">\n      <w:name w:val="Normal"/>\n      <w:rPr>\n        <w:rFonts w:ascii="{default_font_xml}" w:h-ansi="{default_font_xml}" w:cs="{default_font_xml}"/>\n        <w:sz w:val="24"/>\n        <w:sz-cs w:val="24"/>\n      </w:rPr>\n    </w:style>\n  </w:styles>\n  <w:body>\n    <wx:sect>\n{paragraphs_xml}\n      <w:sectPr>\n        <w:pgSz w:w="11906" w:h="16838"/>\n        <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>\n        <w:bidi/>\n      </w:sectPr>\n    </wx:sect>\n  </w:body>\n</w:wordDocument>\n'
    return document.encode('utf-8')


def _copyHelperDir():
    return Path(userPath())


def _nextCopyHelperPath(folder):
    for helper in folder.glob('copyhelper_*'):
        try:
            if helper.is_file() or helper.is_symlink():
                helper.unlink()
        except Exception:
            pass

    for index in range(1, 1000):
        path = folder / f"copyhelper_{index}.xml"
        if not path.exists():
            return path


def wordXmlClipboardFile(html):
    """Write generated WordML to an app-user helper file for the macOS file clipboard path."""
    xml = wordXmlClipboardBytes(html)
    if not xml:
        return
    folder = _copyHelperDir()
    if not folder:
        return
    path = _nextCopyHelperPath(folder)
    if not path:
        return
    try:
        path.write_bytes(xml)
        return str(path)
    except Exception:
        return


def _buildRtfFromParagraphs(paragraphs):
    paragraphs = [paragraph for paragraph in paragraphs if paragraph['runs']]
    if not paragraphs:
        return
    fonts = []
    for paragraph in paragraphs:
        for run in paragraph['runs']:
            font = run['font'] or 'Traditional Naskh'
            if font not in fonts:
                fonts.append(font)

    font_index = {font: index for index, font in enumerate(fonts)}
    font_table = ''.join((f"{{\\f{index}\\fnil\\fcharset0 {_escapeRtfText(font)};}}" for font, index in font_index.items()))
    parts = [
     '{\\rtf1\\ansi\\ansicpg1252\\deff0\\uc1\n',
     f"{{\\fonttbl{font_table}}}\n",
     '{\\colortbl;\\red0\\green0\\blue0;}\n']
    for para_index, paragraph in enumerate(paragraphs):
        parts.append('\\pard')
        parts.append('\\rtlpar\\qr\\sa0\\sb0\\rtlch' if paragraph['rtl'] else '\\ltrpar\\ql\\sa0\\sb0\\ltrch')
        parts.append('\\cf1 ')
        current_font = current_size = current_bold = current_italic = None
        for run in paragraph['runs']:
            font = run['font'] or fonts[0]
            size = run['size'] or 24
            bold = run['bold']
            italic = bool(run.get('italic'))
            if font != current_font:
                parts.append(f"\\f{font_index[font]} ")
                current_font = font
            else:
                if size != current_size:
                    parts.append(f"\\fs{size} ")
                    current_size = size
                if bold != current_bold:
                    parts.append('\\b ' if bold else '\\b0 ')
                    current_bold = bold
                if italic != current_italic:
                    parts.append('\\i ' if italic else '\\i0 ')
                    current_italic = italic
                parts.append(_escapeRtfText(run['text']))

        if para_index < len(paragraphs) - 1:
            parts.append('\\par\n')

    parts.append('}')
    return ''.join(parts).encode('utf-8')


def _attributionFont():
    """Aya-attribution font used on copy: the pages-text family (خط النص) at the
    user's attribution size. Attribution has no font family of its own."""
    fp = Settings.getValue('font_pages')
    return [
     fp[0], Settings.getValue('attribute_size'), fp[2], fp[3]]


def _quranHtmlDocument(text):
    """Wraps quran HTML in a full HTML document with StartFragment markers for clipboard."""
    font = _attributionFont()
    return f"<html><head><meta http-equiv=Content-Type content='text/html; charset=utf-8' /></head>\n        <body><p dir='rtl' style='{fontSettingCss(font)}'><!--StartFragment-->{text}<!--EndFragment--></p></body></html>"


def _escapeHtmlClipboardText(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')


def _buildHtmlFromParagraphs(paragraphs):
    body = []
    for paragraph in paragraphs:
        if not paragraph['runs']:
            continue
        else:
            direction = 'rtl' if paragraph['rtl'] else 'ltr'
            run_html = []
            for run in paragraph['runs']:
                style = [
                     f'font-family:"{run["font"]}"', f"font-size:{run['size'] / 2:g}pt"]
                if run['bold']:
                    style.append('font-weight:bold')
                else:
                    if run.get('italic'):
                        style.append('font-style:italic')
                    run_html.append(f"<span style='{'; '.join(style)}'>{_escapeHtmlClipboardText(run['text'])}</span>")

            body.append(f"<p dir='{direction}'>{''.join(run_html)}</p>")

    return f"<html><head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'/></head><body>{''.join(body)}</body></html>"


def _buildSingleFontRichPayload(text, font, rtl=True):
    paragraphs = []
    lines = text.split('\n') or ['']
    for line in lines:
        paragraphs.append({'rtl':rtl, 
         'runs':[
          {'text':line or ' ', 
           'font':font[0],  'size':font[1] * 2,  'bold':bool(font[2]), 
           'italic':bool(font[3])}]})

    return (
     _buildHtmlFromParagraphs(paragraphs), _buildRtfFromParagraphs(paragraphs))


def _buildManualRtf(html):
    parser = ClipboardHtmlParser()
    parser.feed(html)
    parser.close()
    return _buildRtfFromParagraphs(parser.paragraphs)


def htmlToRtfBytes(html):
    """Build deterministic RTF for Shamela's simple clipboard HTML."""
    if not html:
        return
    return _buildManualRtf(html)


def enrichMimeData(data):
    """Add RTF alongside HTML on macOS so TextEdit and other non-HTML apps can paste rich text."""
    if Across.os != 'mac':
        return data
    if not (data is None or data.hasHtml()):
        return data
    if not (data.data('text/rtf').isEmpty() and data.data('application/rtf').isEmpty()):
        return data
    rtf_bytes = htmlToRtfBytes(data.html())
    if rtf_bytes:
        data.setData('text/rtf', QByteArray(rtf_bytes))
        data.setData('application/rtf', QByteArray(rtf_bytes))
    return data


def setClipboardMimeData(data):
    """Write clipboard data, using native macOS types when available.

    Unified path for Majma Quran (macOS + Word installed):
      RTF + plain text are written as real data immediately (TextEdit and
      all non-Word apps paste this directly).  A 100 ms QTimer then polls
      the frontmost app:
        – When Word activates and clipboard is still ours → swap to file-url
          only, so Word imports the WordML XML with full formatting.
        – When a non-Word app regains focus and clipboard is the Word version
          → swap back to RTF.
    """
    data = enrichMimeData(data)
    if _ensureNativeClipboardApi():
        try:
            pasteboard = NSPasteboard.generalPasteboard()
            if pasteboard is not None:
                word_xml_file = bytes(data.data(WORD_XML_CLIPBOARD_FILE_MIME)).decode('utf-8')
                if word_xml_file:
                    if NSURL:
                        rtf_raw = data.data('text/rtf')
                        rtf_bytes = bytes(rtf_raw) if (not rtf_raw.isEmpty()) else None
                        if rtf_bytes:
                            text = data.text() if data.hasText() else ''
                            new_cc = _writeRtfPasteboard(rtf_bytes, text)
                            if new_cc is not None:
                                _clipboard_routing.update({'active':True, 
                                 'xml_path':word_xml_file, 
                                 'rtf_bytes':rtf_bytes, 
                                 'html':data.html() if data.hasHtml() else '', 
                                 'text':text, 
                                 'rtf_change_count':new_cc, 
                                 'word_change_count':None})
                                _startClipboardRoutingTimer()
                                return
                        else:
                            url = NSURL.fileURLWithPath_(word_xml_file)
                            pasteboard.clearContents()
                            if pasteboard.writeObjects_([url]):
                                return
                item = NSPasteboardItem.alloc().init()
                if data.hasText():
                    text = data.text()
                    utf8 = text.encode('utf-8')
                    utf16 = text.encode('utf-16')
                    item.setData_forType_(NSData.dataWithBytes_length_(utf8, len(utf8)), 'public.utf8-plain-text')
                    item.setData_forType_(NSData.dataWithBytes_length_(utf16, len(utf16)), 'public.utf16-external-plain-text')
                    item.setString_forType_(text, 'public.text')
                if data.hasHtml():
                    html = data.html().encode('utf-8')
                    item.setData_forType_(NSData.dataWithBytes_length_(html, len(html)), 'public.html')
                rtf_raw = data.data('text/rtf')
                if not rtf_raw.isEmpty():
                    rtf_bytes = bytes(rtf_raw)
                    item.setData_forType_(NSData.dataWithBytes_length_(rtf_bytes, len(rtf_bytes)), 'public.rtf')
                pasteboard.clearContents()
                if pasteboard.writeObjects_([item]):
                    return
        except Exception:
            pass

    QApplication.clipboard().setMimeData(data)


class BlockSize:
    _size = None

    @classmethod
    def getBlockSize(cls):
        if not cls._size:
            drive_name = os.path.splitdrive(Across.bin_directory)[0]
            if Across.os == 'win' and ctypes:
                try:
                    sectorsPerCluster = ctypes.c_ulonglong(0)
                    bytesPerSector = ctypes.c_ulonglong(0)
                    rootPathName = ctypes.c_wchar_p(drive_name)
                    ctypes.windll.kernel32.GetDiskFreeSpaceW(rootPathName, ctypes.pointer(sectorsPerCluster), ctypes.pointer(bytesPerSector), None, None)
                    cls._size = sectorsPerCluster.value * bytesPerSector.value
                except:
                    cls._size = 4096

            else:
                try:
                    path_to_check = drive_name if drive_name else Across.bin_directory
                    stat = os.statvfs(path_to_check)
                    cls._size = stat.f_frsize
                except (OSError, AttributeError):
                    cls._size = 4096

            return cls._size


def pextract(zip_path, target_path, call_back=None, signal=None, progress_signal=None):
    if not isZipValid(zip_path):
        kill(zip_path)
        return

    def zipName(info):
        name = info.filename
        if info.flag_bits & 2048:
            return name
        try:
            return name.encode('cp437').decode('utf-8')
        except UnicodeError:
            return name

    def isSymlink(info):
        return info.external_attr >> 16 & 61440 == 40960

    try:
        z = zipfile.ZipFile(zip_path)
        name_list = z.namelist()
        total_size = 0
        growing_size = 0
        for entry_name in name_list:
            total_size += z.getinfo(entry_name).file_size

        for entry_name in name_list:
            entry_info = z.getinfo(entry_name)
            extracted_name = zipName(entry_info)
            file_size = entry_info.file_size
            i = z.open(entry_name)
            if extracted_name[-1] != '/':
                dir_name = os.path.dirname(extracted_name)
                p = Path(f"{target_path}/{dir_name}")
                p.mkdir(parents=True, exist_ok=True)
                truncate = f"{target_path}/{extracted_name}"
                if isSymlink(entry_info) and hasattr(os, 'symlink'):
                    target = i.read().decode('utf-8')
                    growing_size += file_size
                    if os.path.lexists(truncate):
                        os.unlink(truncate)
                    os.symlink(target, truncate)
                    if file_size:
                        percent = growing_size / total_size * 100.0
                        if call_back:
                            call_back(percent)
                        if signal:
                            signal.emit(percent)
                        if progress_signal:
                            progress_signal.emit({'start':100, 
                             'value':percent,  'tip':QCoreApplication.translate('MainWindow', 'Extracting files')})
                else:
                    with open(truncate, 'w'):
                        pass
                    o = open(truncate, 'wb')
                    while True:
                        b = i.read(BlockSize.getBlockSize())
                        if file_size:
                            growing_size += len(b)
                            percent = growing_size / total_size * 100.0
                            if call_back:
                                call_back(percent)
                            if signal:
                                signal.emit(percent)
                            if progress_signal:
                                progress_signal.emit({'start':100, 
                                 'value':percent,  'tip':QCoreApplication.translate('MainWindow', 'Extracting files')})
                        if b == b'':
                            break
                        else:
                            o.write(b)

                    o.close()
                    if Across.os != 'win':
                        mode = entry_info.external_attr >> 16 & 511
                        if mode:
                            os.chmod(truncate, mode)
            i.close()

        z.close()
        kill(zip_path)
        if progress_signal:
            progress_signal.emit({'end': True})
        return True
    except:
        shutil.rmtree(target_path, ignore_errors=True)
        kill(zip_path)
        if progress_signal:
            progress_signal.emit({'end': True})


def ensureChecked(button):
    button.blockSignals(True)
    button.setChecked(True)
    button.blockSignals(False)


def unhideSelection(widget):
    palette = QApplication.palette()
    palette.setColor(QPalette.Inactive, QPalette.Highlight, palette.color(QPalette.Active, QPalette.Highlight))
    palette.setColor(QPalette.Inactive, QPalette.HighlightedText, palette.color(QPalette.Active, QPalette.HighlightedText))
    widget.setPalette(palette)


def flexibleBrowser():
    if NVDA.isRunning():
        return ReadersBrowser()
    return StandardBrowser()


def realResolutions_new():
    """Per-monitor DPI via shcore.GetDpiForMonitor (Windows 8.1+).

    Returns a list of [dpiX, dpiY], one entry per monitor, or None when the
    modern API is unavailable or fails — so the caller can fall back instead of
    mistaking a failure for a genuine 96 DPI reading. DPI awareness is already
    established once at startup (setup_qt_dpi), so we don't set it again here.
    """
    if Across.os != 'win' or not win32api or not ctypes:
        return None
    try:
        MDT_EFFECTIVE_DPI = 0
        shcore = ctypes.windll.shcore
        get_dpi = shcore.GetDpiForMonitor
        monitors = win32api.EnumDisplayMonitors()
        resolutions = []
        for monitor in monitors:
            dpiX = ctypes.c_uint()
            dpiY = ctypes.c_uint()
            hresult = get_dpi(monitor[0].handle, MDT_EFFECTIVE_DPI, ctypes.byref(dpiX), ctypes.byref(dpiY))
            if hresult != 0 or not dpiX.value or not dpiY.value:
                return None
            resolutions.append([dpiX.value, dpiY.value])
        return resolutions or None
    except Exception:
        return None


def realResolutions_old():
    """Legacy DPI via GetDeviceCaps on the desktop DC.

    Returns [dpiX, dpiY] for the primary device context, or None on failure.
    Under a per-monitor-aware process this reflects the primary monitor only,
    which is why it is a fallback rather than the preferred reader.
    """
    if not (Across.os != 'win' or ctypes):
        return
    try:
        LOGPIXELSX = 88
        LOGPIXELSY = 90
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        dc = user32.GetDC(None)
        if not dc:
            return
        try:
            x = gdi32.GetDeviceCaps(dc, LOGPIXELSX)
            y = gdi32.GetDeviceCaps(dc, LOGPIXELSY)
        finally:
            user32.ReleaseDC(None, dc)

        if not (x and y):
            return
        return [x, y]
    except Exception:
        return


def windowsDpiDots():
    """Best-effort [dpiX, dpiY] for the active screen on Windows.

    No sys.getwindowsversion() gating: GetVersionEx lies in frozen/manifested
    builds (can report Win 8 on Win 10/11), which would wrongly route us to the
    legacy reader and yield suboptimal DPI. Instead we simply attempt the modern
    per-monitor API, fall back to the legacy DC query, then to 96 — each guarded
    so a missing/failing API just advances to the next option.
    """
    per_monitor = realResolutions_new()
    if per_monitor:
        try:
            return per_monitor[QApplication.desktop().screenNumber()]
        except Exception:
            return per_monitor[0]

        legacy = realResolutions_old()
        if legacy:
            return legacy
        return [96, 96]


def scaling():
    """Get scaling factor based on platform"""
    if Across.os == 'win':
        dots = windowsDpiDots()
        return dots[1] / 96
    if Across.os == 'mac':
        try:
            screen = QApplication.primaryScreen()
            if screen:
                return screen.logicalDotsPerInchY() / 72
        except:
            pass

        return 1.0
    try:
        screen = QApplication.primaryScreen()
        if screen:
            return screen.logicalDotsPerInchY() / 96
    except:
        pass

    return 1.0


class Scale:
    current_scale = None

    @staticmethod
    def scale():
        if not Scale.current_scale:
            Scale.current_scale = scaling()
        return Scale.current_scale


def readJson(file_path):
    if not os.path.isfile(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as read_file:
        try:
            return json.load(read_file)
        except:
            return {}


def isCompleter(widget):
    comp = widget.completer()
    if comp:
        pop = comp.popup()
        if pop:
            if pop.isVisible():
                return True


STANDARD_WRAPPED_SHORTCUTS = {QKeySequence(sequence).toString(QKeySequence.PortableText) for sequence in ('Ctrl+A',
                                                                                                          'Ctrl+C',
                                                                                                          'Ctrl+F',
                                                                                                          'Ctrl+S',
                                                                                                          'Ctrl+V',
                                                                                                          'Ctrl+W',
                                                                                                          'Ctrl+X')}
SHORTCUT_MODIFIERS = Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier | Qt.KeypadModifier

def _qtEnumValue(value):
    try:
        return int(value)
    except TypeError:
        if hasattr(value, 'toCombined'):
            return value.toCombined()
        else:
            if hasattr(value, 'value'):
                return int(value.value)
            raise


SHORTCUT_MODIFIER_MASK = _qtEnumValue(SHORTCUT_MODIFIERS)

def _portableShortcut(sequence):
    if isinstance(sequence, QKeySequence):
        q_sequence = sequence
    else:
        q_sequence = QKeySequence(sequence)
    text = q_sequence.toString(QKeySequence.PortableText)
    return text or sequence


def _macLiteralControlShortcut(sequence):
    portable = _portableShortcut(sequence)
    if not Across.os != 'mac':
        if not 'Ctrl' not in portable or 'Control' not in portable:
            return portable
        return re.sub('(?:(?<=^)|(?<=\\+))(?:Ctrl|Control)(?=(?:\\+|$))', 'Meta', portable)


def _shortcutVariants(sequence, wrapped=True):
    portable = _portableShortcut(sequence)
    if not wrapped:
        return [_macLiteralControlShortcut(portable)]
    variants = [portable]
    literal = _macLiteralControlShortcut(portable)
    if Across.os == 'mac':
        if literal != portable:
            variants.append(literal)
    return variants


def _registerShortcut(parent, sequence, slot, context=None, wrapped=True):
    shortcuts = []
    for variant in _shortcutVariants(sequence, wrapped=wrapped):
        short = QShortcut(QKeySequence(variant), parent)
        if context:
            short.setContext(context)
        else:
            short.activated.connect(slot)
            shortcuts.append(short)

    if shortcuts:
        retained = getattr(parent, '_registered_shortcuts', None)
        if retained is None:
            retained = []
            setattr(parent, '_registered_shortcuts', retained)
        retained.extend(shortcuts)
    if shortcuts:
        return shortcuts[0]


def shortcut(parent, sequence, slot, context=None):
    return _registerShortcut(parent, sequence, slot, context=context, wrapped=True)


def directShortcut(parent, sequence, slot, context=None):
    return _registerShortcut(parent, sequence, slot, context=context, wrapped=False)


def shortcutText(sequence, wrapped=True):
    if not sequence:
        return ''
    display_sequence = _shortcutVariants(sequence, wrapped=wrapped)[0]
    q_sequence = QKeySequence(display_sequence)
    text = q_sequence.toString(QKeySequence.NativeText)
    if not text:
        text = q_sequence.toString(QKeySequence.PortableText)
    return text or sequence


def shortcutLabel(label, sequence, separator='  ', wrapped=True):
    if not sequence:
        return label
    text = shortcutText(sequence, wrapped=wrapped)
    if not text:
        return label
    return f"{label}{separator}{text}"


def directShortcutLabel(label, sequence, separator='  '):
    return shortcutLabel(label, sequence, separator=separator, wrapped=False)


def shouldWrapShortcut(sequence):
    return _portableShortcut(sequence) in STANDARD_WRAPPED_SHORTCUTS


def normalizeShortcutLabel(text, wrapped=None):
    if not text:
        return text
    text = text.replace('Ctr', 'Ctrl')
    pattern = re.compile('(?P<mods>(?:Ctrl|Control|Command|Cmd|Alt|Shift|Meta)(?:\\s*(?:\\+|-|\\s)\\s*(?:Ctrl|Control|Command|Cmd|Alt|Shift|Meta))*)\\s*(?:\\+|-|\\s)\\s*(?P<key>F\\d{1,2}|[A-Za-z0-9])', re.IGNORECASE)

    def native_shortcut(match):
        mods = []
        for part in re.split('\\s*(?:\\+|-|\\s)\\s*', match.group('mods').strip()):
            if not part:
                continue
            else:
                lower = part.lower()
            if lower in frozenset({'cmd', 'control', 'command'}):
                mods.append('Ctrl')
            else:
                if lower == 'ctrl':
                    mods.append('Ctrl')
                else:
                    if lower == 'alt':
                        mods.append('Alt')
                    else:
                        if lower == 'shift':
                            mods.append('Shift')
            if lower == 'meta':
                mods.append('Meta')

        key = match.group('key').upper()
        if key.startswith('F'):
            if key[1:].isdigit():
                key = 'F' + key[1:]
        if not mods:
            return match.group(0)
        sequence = '+'.join(mods + [key])
        use_wrapped = shouldWrapShortcut(sequence) if wrapped is None else wrapped
        return shortcutText(sequence, wrapped=use_wrapped)

    text = pattern.sub(native_shortcut, text)
    return text


def _shortcutInts(sequence, wrapped=True):
    return {_qtEnumValue(QKeySequence(variant)[0]) for variant in _shortcutVariants(sequence, wrapped=wrapped)}


def matchesShortcutEvent(event, sequence, wrapped=True):
    modifiers = _qtEnumValue(event.modifiers() & SHORTCUT_MODIFIERS)
    return modifiers | _qtEnumValue(event.key()) in _shortcutInts(sequence, wrapped=wrapped)


def matchesShortcutModifiers(modifiers, sequence, wrapped=True):
    current = _qtEnumValue(modifiers & SHORTCUT_MODIFIERS)
    variants = {shortcut_int & SHORTCUT_MODIFIER_MASK for shortcut_int in _shortcutInts(sequence, wrapped=wrapped)}
    return current in variants


class Splitter(QSplitter):

    def __init__(self, above_each, widgets_list, values=None):
        super().__init__()
        self.setHandleWidth(self.handleWidth() // 2)
        self.setOrientation(Qt.Vertical if above_each else Qt.Horizontal)
        for widget in widgets_list:
            self.addWidget(widget)

        if values:
            w = self.width()
            self.setSizes([value // w for value in values])


def customSplitter(above_each_other, first, second=None, first_percent=None, parent=None):
    splitter = QSplitter(parent)
    if above_each_other:
        splitter.setOrientation(Qt.Vertical)
    else:
        splitter.setOrientation(Qt.Horizontal)
    items = [first, second]
    for i in range(2):
        if isinstance(items[i], QLayout):
            widget = QWidget()
            widget.setLayout(items[i])
            items[i] = widget

    splitter.addWidget(items[0])
    if items[1]:
        if first_percent:
            splitter.addWidget(items[1])
            splitter.setStretchFactor(0, first_percent)
            splitter.setStretchFactor(1, 100 - first_percent)
            splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(int(splitter.handleWidth() / 2))
    return splitter


def customLayout(above_each_other, items=None, margins=None, spacing=None, parent=None):
    if margins is None:
        margins = [
         1, 1, 1, 1]
    if spacing is None:
        spacing = 1
    if isinstance(margins, int):
        margins = [
         margins, margins, margins, margins]
    layout = QVBoxLayout(parent) if above_each_other else QHBoxLayout(parent)
    layout.setContentsMargins(margins[0], margins[1], margins[2], margins[3])
    layout.setSpacing(spacing)
    if items:
        for item in items:
            if isinstance(item, QWidget):
                layout.addWidget(item)
            else:
                if isinstance(item, QSpacerItem):
                    layout.addSpacerItem(item)
                else:
                    if isinstance(item, QLayout):
                        layout.addLayout(item)
                    else:
                        if item == 0:
                            layout.addStretch()
            if isinstance(item, int):
                layout.addSpacing(item)

    return layout


def customToolButton(icon=None, tooltip=None, auto_raise=True, iconsize=16, slot=None, text=None, text_beside=None, text_below=None, checkable=None):
    toolButton = QToolButton()
    toolButton.setFont(QApplication.font())
    if text:
        toolButton.setText(text)
    if not text:
        text = tooltip
    if text_beside:
        toolButton.setText(text)
        toolButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if text_below:
        toolButton.setText(text)
        toolButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    if tooltip:
        toolButton.setToolTip(tooltip)
    if checkable:
        toolButton.setCheckable(True)
    toolButton.setAutoRaise(auto_raise)
    toolButton.setFocusPolicy(Qt.WheelFocus)
    if icon:
        toolButton.setIcon(Icon.icon(icon))
        toolButton._icon_path = icon
    if iconsize:
        toolButton.setIconSize(QSize(iconsize, iconsize))
    if slot:
        toolButton.clicked.connect(slot)
    return toolButton


def iconedPush(icon, text, tooltip=None, slot=None):
    push = QPushButton(Icon.icon(icon), '   ' + text)
    push._icon_path = icon
    if slot:
        push.clicked.connect(slot)
    push.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    push.setStyleSheet('text-align:center;')
    if tooltip:
        push.setToolTip(tooltip)
    return push


def customMessage(title, message, yes_no=False, nomain=None):
    main_visible = Across.main_window.isVisible() if Across.main_window else False
    if not main_visible:
        if not nomain:
            return
        box = QMessageBox()
        box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        box.setWindowTitle(title)
        box.setText(f" {message}\n")
        if yes_no:
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            button_yes = box.button(QMessageBox.Yes)
            button_yes.setText(QCoreApplication.translate('MainWindow', 'Yes'))
            button_no = box.button(QMessageBox.No)
            button_no.setText(QCoreApplication.translate('MainWindow', 'No'))
            return box.exec_() == QMessageBox.Yes
        box.setStandardButtons(QMessageBox.Ok)
        button = box.button(QMessageBox.Ok)
        button.setText(QCoreApplication.translate('MainWindow', 'OK'))
        return box.exec_()


def QtFont(l_font, scale=True):
    """Takes [font_name, base_size, bold?, italic?] and returns a QFont.

    Pass the *base* point-size as it should appear at 96 DPI / 100% scaling.
    scaling.scaled_font_size() is applied automatically when scale=True (default).
    Pass scale=False when displaying the font to the user (e.g. in options dialog)
    so the user sees and edits the real base size, not the DPI-adjusted size.
    """
    from scaling import scaled_font_size
    l = len(l_font)
    pt = scaled_font_size(l_font[1]) if scale else l_font[1]
    font = QFont(l_font[0], pt)
    style_name = fontSettingStyleName(l_font)
    if style_name:
        font.setStyleName(style_name)
    if l > 2:
        if l > 4 and not isinstance(l_font[4], str):
            font.setWeight(fontSettingWeight(l_font))
        else:
            font.setBold(l_font[2])
        if l > 3:
            font.setItalic(l_font[3])
    return font


def fontSettingStyleName(l_font):
    if len(l_font) > 5:
        if isinstance(l_font[5], str):
            return l_font[5].strip()
    if len(l_font) > 4:
        if isinstance(l_font[4], str):
            return l_font[4].strip()
    return ''


def fontSettingWeight(l_font):
    if len(l_font) > 4 and not isinstance(l_font[4], str):
        try:
            return int(l_font[4])
        except (TypeError, ValueError):
            pass

        if len(l_font) > 2:
            if l_font[2]:
                return int(QFont.Bold)
        return int(QFont.Normal)


def fontSettingCssWeight(l_font):
    weight = fontSettingWeight(l_font)
    if weight <= int(QFont.ExtraLight):
        return '200'
    if weight <= int(QFont.Light):
        return '300'
    if weight <= int(QFont.Normal):
        return '400'
    if weight <= int(QFont.Medium):
        return '500'
    if weight <= int(QFont.DemiBold):
        return '600'
    if weight <= int(QFont.Bold):
        return '700'
    if weight <= int(QFont.ExtraBold):
        return '800'
    return '900'


def fontSettingCss(l_font, include_size=True):
    style = [
     f'font-family:"{l_font[0]}"']
    if include_size:
        style.append(f"font-size:{l_font[1]}pt")
    style.append(f"font-weight:{fontSettingCssWeight(l_font)}")
    if len(l_font) > 3:
        if l_font[3]:
            style.append('font-style:italic')
    return ';'.join(style) + ';'


def hColor(l_color):
    return QColor(l_color[0], l_color[1], l_color[2]).name()


def hLine():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    line.setMinimumHeight(6)
    line.setStyleSheet('QFrame { background: transparent; border: none; border-top: 1px solid palette(dark); margin: 2px 0; }')
    return line


def vLine():
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setFrameShadow(QFrame.Plain)
    line.setStyleSheet('QFrame { background: transparent; border: none; border-right: 1px solid palette(dark); }')
    return line


def listFit(qlist, width=False, height=True):
    """makes size of QListWidget fits its content"""
    w = 0
    h = 0
    if width:
        w = qlist.sizeHintForColumn(0) + 12 * qlist.frameWidth()
        qlist.setMaximumWidth(w)
    if height:
        h = qlist.sizeHintForRow(0) * qlist.count() + 2 * qlist.frameWidth()
        qlist.setFixedHeight(h)
    return (w, h)


def image(image_path, size=None, old=None):
    label = QLabel()
    label.setScaledContents(True)
    label.setText('')
    label.setStyleSheet('')
    if old:
        label.setPixmap(QPixmap(image_path))
    else:
        ico = Icon.icon(image_path)
        px_size = size or 24
        pixmap = ico.pixmap(QSize(px_size, px_size))
        if pixmap.isNull():
            pixmap = QPixmap(image_path)
        label.setPixmap(pixmap)
    if size:
        label.setMaximumSize(QSize(size, size))
    return label


def styledLabel(width=None, height=None, no_center=None):
    """The app's card label, coloured off the active palette.

      dark  -> surface at the accent's own hue, hsl(hue, 50%, 20%), with the
               accent as text and border.  QPalette.Link is #8ab4f7 under the
               dark theme -- the very blue the card hardcoded -- and its hue
               (217) reproduces the old rgb(25,45,75) navy.
      light -> QPalette.Light surface (white under Fusion and modern light),
               QPalette.Text, and a QPalette.Mid border (#b8b8b8, a shade off
               the rgb(180,180,180) it hardcoded)."""
    palette = QApplication.palette()
    accent = palette.color(QPalette.Link)
    if palette.color(QPalette.Base).lightness() < 128:
        hue = accent.hue()
        bg = QColor.fromHsl(hue, 128, 51) if hue >= 0 else QColor(25, 45, 75)
        fg = accent
        border = accent
    else:
        bg = palette.color(QPalette.Light)
        fg = palette.color(QPalette.Text)
        border = palette.color(QPalette.Mid)
    label = QLabel()
    label.setAutoFillBackground(True)
    if not no_center:
        label.setAlignment(Qt.AlignCenter)
    if width:
        label.setFixedWidth(width)
    if height:
        label.setFixedHeight(height)
    label.setStyleSheet('QLabel {background-color: ' + bg.name() + '; color: ' + fg.name() + '; border: 1px solid ' + border.name() + '; border-radius: 4px;}')
    return label


def blanchLabel(text):
    """The 'nothing to show' card that replaces a whole page's content.

    Shared by the pdf viewer and the rijal sheokh/talameez/marweat tabs so every
    blanched page keeps one look: styledLabel's themed card (it follows the
    active theme's colours) in the app's Naskh display font, wrapped in a holder
    that insets it 1px, so the rounded border never sits flush against the panel
    edge. Toggle the returned holder's visibility, not the label's.
    Returns (holder, label)."""
    label = styledLabel()
    label.setFont(QtFont(['Traditional Naskh', 18, True]))
    label.setText(text)
    holder = QWidget()
    holder.setLayout(customLayout(True, [label], margins=[1, 1, 1, 0]))
    holder.setVisible(False)
    return (
     holder, label)


def isZipValid(file):
    if not os.path.isfile(file):
        return
    if not zipfile.is_zipfile(file):
        return
    return True


def findInList(data, item):
    if isinstance(item, tuple):
        return findInTuple(data, item)
    try:
        return data.index(item)
    except:
        return -1


def findInTuple(data, item):
    new_data = [member[0] for member in data]
    try:
        return new_data.index(item[0])
    except:
        return -1


def singlePhrase(panels):
    for panel in panels:
        for phrases_list in panel:
            for phrase in phrases_list:
                if phrase:
                    return phrase


def printQuery(info, name=None):
    words = ''
    for panels in info['phrases']:
        for panel in panels:
            words += f" [{' - '.join(panel)}] "

    words = re.sub(' +', ' ', words).strip()
    line = ''
    extra = []
    if 'excludes' in info:
        if 'type' in info:
            extra.append('عناوين')
        if 'body' in info['excludes']:
            extra.append('بدون المتن')
        if 'foot' in info['excludes']:
            extra.append('بدون الحواشي')
        if 'comment' in info['excludes']:
            extra.append('بدون التعليقات')
    if extra:
        line += ' (' + ' - '.join(extra) + ')'
    extra = []
    if 'features' in info:
        if 'stemmed' in info['features']:
            extra.append('صرفي')
        if 'hamza' in info['features']:
            extra.append('همزات')
        if 'diacritics' in info['features']:
            extra.append('تشكيل')
        if 'numbers' in info['features']:
            extra.append('أرقام')
    if extra:
        line += ' (' + ' - '.join(extra) + ')'
    if line:
        features = 'الخيارات:' + line
    else:
        features = 'الخيارات: الافتراضية'
    if 'scope' in info:
        scope = 'المجال: ' + printScope(info['scope'])
    else:
        scope = 'المجال: جميع الكتب'
    value = f"{words}{SEP}{features}{SEP}{scope}"
    if 'results_count' in info:
        value += SEP + 'عدد النتائج: ' + arabize(info['results_count'])
    if name:
        value = f"{name} {value}"
    return value


def printScope(value, name=None):
    category = 0
    author = 0
    period = 0
    favorite = 0
    book = 0
    for item in value:
        if isinstance(item, int):
            book += 1
        else:
            if 'category' in item:
                category += 1
            else:
                if 'author' in item:
                    author += 1
                else:
                    if 'period' in item:
                        period += 1
        if 'favorite' in item:
            favorite += 1

    majal = []
    if category:
        majal.append(f"أقسام ({arabize(category)})")
    if author:
        majal.append(f"مؤلفون ({arabize(author)})")
    if period:
        majal.append(f"فترات ({arabize(period)})")
    if favorite:
        majal.append(f"مفضلات ({arabize(favorite)})")
    if book:
        majal.append(f"كتب ({arabize(book)})")
    printed = ' - '.join(majal)
    if name:
        return f"{name}{SEP}{printed}"
    return printed


def registerFonts():
    """Register fonts for cross-platform support"""
    font_dir = fontDir()
    if not os.path.isdir(font_dir):
        os.makedirs(font_dir, exist_ok=True)
    for file_name in Across.fonts:
        installFont(font_dir, file_name)

    if Across.os == 'win' and notify:
        notify()
    else:
        if Across.os == 'linux':
            refreshLinuxFontCache(font_dir)


def staleFont(font_path, file_name):
    """True when the installed copy no longer matches the bundled resource.

    QFile.copy refuses to overwrite, so without this an updated bundled font
    never reaches anyone who already ran an older build -- they keep the old
    file, and Windows keeps it registered under the same family name.
    """
    if not os.path.isfile(font_path):
        return False
    resource = QFile(f":/fonts/{file_name}")
    if not resource.open(QFile.ReadOnly):
        return False
    try:
        bundled = bytes(resource.readAll())
    finally:
        resource.close()

    try:
        with open(font_path, 'rb') as installed:
            return installed.read() != bundled
    except OSError:
        return True


def installFont(font_dir, file_name):
    """Install font file to system font directory.

    There is no 'force' mode: the file is replaced only when its bytes differ
    from the bundled resource, because re-copying an identical file gains
    nothing. What the options 'fix fonts' button actually repairs is the
    registration -- a missing or wrong registry entry, or a font the user
    uninstalled -- and that runs unconditionally at the end of this function.
    """
    font_path = os.path.join(font_dir, file_name)
    if staleFont(font_path, file_name):
        try:
            os.chmod(font_path, stat.S_IWRITE)
        except OSError:
            pass

        kill(font_path)
    if not os.path.isfile(font_path):
        QFile.copy(f":/fonts/{file_name}", font_path)
    if Across.os == 'win':
        if installWinFont:
            if os.path.isfile(font_path):
                installWinFont(font_path)


def fontDir():
    """Get platform-specific font directory"""
    if Across.os == 'linux':
        return os.path.join(os.path.expanduser('~'), '.local', 'share', 'fonts')
    if Across.os == 'mac':
        return os.path.join(os.path.expanduser('~'), 'Library', 'Fonts')
    if Across.os == 'win':
        if userpaths:
            folder = os.path.join(userpaths.get_appdata(), 'shamela_4', 'fonts')
        else:
            folder = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'shamela_4', 'fonts')
        os.makedirs(folder, exist_ok=True)
        return folder
    folder = os.path.join(os.path.expanduser('~'), '.shamela_fonts')
    os.makedirs(folder, exist_ok=True)
    return folder


def refreshLinuxFontCache(font_dir):
    command = shutil.which('fc-cache')
    if not command:
        return
    try:
        subprocess.run([command, '-f', font_dir], stdout=(subprocess.DEVNULL), stderr=(subprocess.DEVNULL), check=False)
    except Exception:
        pass


def shortcuts():
    desktopShortcut()
    startMenuShortcut()


def desktopShortcut():
    value = Settings.getValue('shortcut_desktop')
    folder = winshell.desktop(False) if Across.os == 'win' else desktop_dir()
    fileShortcut(value, folder, location='desktop')


def startMenuShortcut():
    if not menu_shortcut_supported():
        return
    value = Settings.getValue('shortcut_start')
    if Across.os == 'win':
        folder = winshell.start_menu(False)
    else:
        if Across.os == 'linux':
            folder = os.path.join(os.path.expanduser('~'), '.local', 'share', 'applications')
    fileShortcut(value, folder, location='start_menu')


def linuxShortcutDataHome():
    return os.path.expanduser(os.environ.get('XDG_DATA_HOME') or '~/.local/share')


def linuxShortcutIconPath():
    return os.path.join(linuxShortcutDataHome(), 'shamela', 'icons', 'shamela.png')


def linuxShortcutIconBytes():
    icon_file = QFile(':/icons/shamela.png')
    if not icon_file.open(QFile.ReadOnly):
        return
    try:
        return bytes(icon_file.readAll())
    finally:
        icon_file.close()


def ensureLinuxShortcutIcon():
    icon_bytes = linuxShortcutIconBytes()
    if not icon_bytes:
        return
    target_path = linuxShortcutIconPath()
    try:
        os.makedirs((os.path.dirname(target_path)), exist_ok=True)
        needs_copy = True
        if os.path.isfile(target_path):
            try:
                with open(target_path, 'rb') as f:
                    needs_copy = f.read() != icon_bytes
            except:
                needs_copy = True

            if needs_copy:
                with open(target_path, 'wb') as f:
                    f.write(icon_bytes)
        return target_path
    except:
        return


def linuxDesktopFileName(location):
    app_name = 'المكتبة الشاملة'
    if location == 'start_menu':
        return 'shamela.desktop'
    return f"{app_name}.desktop"


def linuxDesktopEntry():
    app_name = 'المكتبة الشاملة'
    description = 'المكتبة الشاملة - الإصدار الرابع'
    target_path = shortcut_target()
    icon_path = ensureLinuxShortcutIcon()
    icon_line = f"Icon={icon_path}\n" if icon_path else ''
    path_root = os.path.dirname(target_path) if target_path else Across.home_directory
    path_line = f"Path={path_root}\n" if path_root else ''
    entry = f'[Desktop Entry]\nVersion=1.0\nName={app_name}\nComment={description}\nExec="{target_path}"\n{path_line}{icon_line}Terminal=false\nType=Application\nCategories=Education;\nStartupNotify=true\n'
    return entry


def writeLinuxDesktopFile(folder, location):
    if not folder:
        return
    shortcut_name = linuxDesktopFileName(location)
    shortcut_path = os.path.join(folder, shortcut_name)
    content = linuxDesktopEntry()
    try:
        os.makedirs(folder, exist_ok=True)
        previous = None
        if os.path.isfile(shortcut_path):
            try:
                with open(shortcut_path, 'r', encoding='utf-8') as f:
                    previous = f.read()
            except:
                pass

            if previous != content:
                with open(shortcut_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            os.chmod(shortcut_path, os.stat(shortcut_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            if location == 'start_menu':
                try:
                    subprocess.run([
                     'update-desktop-database', folder],
                      stdout=(subprocess.DEVNULL),
                      stderr=(subprocess.DEVNULL),
                      check=False)
                except Exception:
                    pass

        return shortcut_path
    except:
        return


def fileShortcut(value, folder, location):
    if not getattr(sys, 'frozen', False):
        return
    app_name = 'المكتبة الشاملة'
    description = 'المكتبة الشاملة - الإصدار الرابع'
    target_path = shortcut_target()
    if Across.os == 'win':
        shortcut_path = os.path.join(folder, f"{app_name}.lnk")
        if value and winshell:
            os.makedirs(folder, exist_ok=True)
            link = winshell.shortcut(shortcut_path)
            link.path = target_path
            link.description = description
            link.working_directory = os.path.dirname(target_path) or Across.bin_directory
            link.write()
        else:
            kill(shortcut_path)
    else:
        if Across.os == 'linux':
            shortcut_path = os.path.join(folder, linuxDesktopFileName(location))
            if value:
                writeLinuxDesktopFile(folder, location)
            else:
                kill(shortcut_path)
        else:
            if Across.os == 'mac':
                shortcut_path = os.path.join(folder, app_name)
                if value:
                    os.makedirs(folder, exist_ok=True)
                    if os.path.lexists(shortcut_path):
                        os.unlink(shortcut_path)
                    os.symlink(target_path, shortcut_path)
                else:
                    kill(shortcut_path)


def clickableLabel(text, slot, underline=None, italic=None, tooltip=None, normal_size=None, black=None):
    label = Qtlabel()
    if italic:
        text = f"<i>{text}</i>"
    if black:
        fg = QApplication.palette().color(QPalette.WindowText).name()
    else:
        if Across.active_theme != 'dark':
            fg = '#0000ff'
        else:
            fg = None
    if fg is not None:
        decoration = f' style="color: {fg};"' if underline else f' style="text-decoration:none; color: {fg};"'
    else:
        decoration = '' if underline else ' style="text-decoration:none;"'
    text = f'<a href="link"{decoration}>{text}</a>'
    label.setText(text if normal_size else f"<font size=3>{text}</font>")
    if tooltip:
        label.setToolTip(tooltip)
    label.setOpenExternalLinks(False)
    label.clicked.connect(slot)
    return label


def checkAllPdf(progress_signal):
    from dbmanager import CoreDb
    CoreDb().fixGroupFolder()
    CoreDb().fixPdfFolders()
    pdf_folder = pdfPath()
    if not os.path.isdir(pdf_folder):
        return
    file_bag = set()
    ver_dict = {}
    for root, dirs, files in os.walk(pdf_folder):
        for file in files:
            file_path = os.path.normcase(os.path.join(root, file))
            if file.lower().endswith('.json'):
                current_dict = readJson(file_path)
                for key in current_dict:
                    ver_dict[os.path.normcase(os.path.join(root, key))] = current_dict[key]

            else:
                file_bag.add(file_path)

    present_books = []
    defective_books = []
    pdf_files = CoreDb().onLinePdfFiles()
    progress_signal.emit({'start':len(pdf_files),  'tip':QCoreApplication.translate('MainWindow', 'Checking pdf files')})
    required = set()
    for i, book in enumerate(pdf_files, start=1):
        book_id = book[0]
        files = book[1]
        present = True
        for file, ver in files:
            required.add(file)
            if file in file_bag:
                if ver > 1:
                    if file in ver_dict:
                        if ver_dict[file] < ver:
                            present = False
                else:
                    pass
                present = False
            else:
                present = False

        if present:
            present_books.append(book_id)
        else:
            defective_books.append(book_id)
        progress_signal.emit({'value': i})

    CoreDb().updatePdfState(present_books, defective_books)
    extra_files = file_bag - required
    if extra_files:
        extra_path = extraPdfPath()
        os.makedirs(extra_path, exist_ok=True)
        with open(os.path.join(extra_path, 'رسالة من البرنامج.txt'), 'w') as f:
            f.write('هذه الملفات لا استخدام لها في البرنامج\nيمكنك حذفها أو نقلها لمكان آخر')
        for file in extra_files:
            os.renames(file, dstFile(file, extra_path, pdf_folder))

        QDesktopServices.openUrl(QUrl.fromLocalFile(extra_path))
    progress_signal.emit({'end': None})


def dstFile(file, extra_path, pdf_folder):
    file, extra_path, pdf_folder = os.path.normcase(file), os.path.normcase(extra_path), os.path.normcase(pdf_folder)
    dst_file = file.replace(pdf_folder, extra_path)
    if not os.path.isfile(dst_file):
        return dst_file
    f_base, extension = os.path.splitext(dst_file)
    c = 1
    while True:
        target = f"{f_base}_{c}{extension}"
        if not os.path.isfile(target):
            return target
        else:
            c += 1


def fitRow(view):
    font = view.font()
    row_height = QFontMetrics(font).height() + Across.row_space
    view.verticalHeader().setDefaultSectionSize(row_height)


def standardFont(view):
    from settings import Settings
    view._preview_font_key = 'font_standard'
    font = QtFont(Settings.getValue('font_standard'))
    view.setFont(font)
    try:
        fitRow(view)
    except:
        pass


def minSize(widget, width=None, height=None, measure_only=None):
    screen = None
    try:
        screen = QApplication.screenAt(widget.frameGeometry().center())
    except:
        pass

    if not screen:
        try:
            screen = widget.screen()
        except:
            pass

    if not screen:
        try:
            parent = widget.parentWidget()
            if parent:
                screen = parent.screen()
        except:
            pass

    if not screen:
        if Across.main_window:
            try:
                screen = Across.main_window.getScreen()
            except:
                pass

            if not screen:
                screen = QApplication.primaryScreen()
            rec = screen.availableGeometry()
            if width:
                width = width
                max_width = rec.width() - 50
                if width > max_width:
                    width = max_width
                if not measure_only:
                    try:
                        widget.setMinimumWidth(width)
                    except:
                        pass

                if height:
                    height = height
                    max_height = rec.height() - 50
                    if height > max_height:
                        height = max_height
                    if not measure_only:
                        try:
                            widget.setMinimumHeight(height)
                        except:
                            pass

        return (
         width, height)


def kill(file):
    try:
        os.unlink(file)
    except:
        pass


class BrowserMixin:
    __doc__ = "Shared copy/attribution pipeline for ReadersBrowser and StandardBrowser.\n\n    Every copy action follows a linear pipeline:\n      1. _getRawSelection()  — sub-class provides (plain_text, html_or_None)\n      2. createMimeDataFromSelection()  — dispatches by content type\n      3. _formatBook / _formatQuran / plain  — clean text, build fresh HTML, apply attribution\n\n    Key design decisions:\n      - We NEVER pass Qt's raw HTML to the clipboard directly.\n        Honorifics must be decomposed, Arabic-Indic digits replaced with ASCII,\n        page-number tags stripped, and HTML rebuilt from clean plain text using settings fonts.\n      - Book and Quran are mutually exclusive content types (elif, not if+if).\n      - ReadersBrowser (NVDA/plain-text) follows the same pipeline; it just\n        has no source HTML so the table-reversal step is skipped automatically.\n    "

    def setAttributeDict(self, attribute_dict):
        self.attribute_dict = attribute_dict

    def setPage(self, part, page):
        self.part = part
        self.page = page

    def _isBook(self):
        return 'prefix' in self.attribute_dict

    def _isQuran(self):
        return 'rasm' in self.attribute_dict

    def _makeMimeData(self, text, html=None, rtf=None, word_xml=False, force_formatted=False):
        """Create QMimeData from already-clean text and optional rich formats.

        When *word_xml* is True (Majma rasm) **and** on macOs, a WordML XML
        helper file is written to disk and its path stored under
        WORD_XML_CLIPBOARD_FILE_MIME.  setClipboardMimeData then writes RTF
        immediately and swaps to the file-url when Word activates.
        """
        rich_allowed = force_formatted or Settings.getValue('copy_formatted')
        if not rich_allowed:
            html = None
            rtf = None
            word_xml = False
        data = QMimeData()
        if word_xml:
            if html:
                if Across.os == 'mac':
                    path = wordXmlClipboardFile(html)
                    if path:
                        data.setData(WORD_XML_CLIPBOARD_FILE_MIME, QByteArray(path.encode('utf-8')))
                        data.setUrls([QUrl.fromLocalFile(path)])
        data.setText(text)
        if html:
            data.setHtml(html)
        if rtf:
            if Across.os == 'mac':
                data.setData('text/rtf', QByteArray(rtf))
                data.setData('application/rtf', QByteArray(rtf))
        return enrichMimeData(data)

    def _richRun(self, text, font, size, bold=False, italic=False):
        return {'text':text, 
         'font':font,  'size':size * 2,  'bold':bool(bold),  'italic':bool(italic)}

    def _richRunFromFontSetting(self, text, font_setting):
        return self._richRun(text, font_setting[0], font_setting[1], font_setting[2], font_setting[3])

    def _escapeHtmlText(self, text):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')

    def _renderRichParagraphs(self, paragraphs):
        body = []
        for paragraph in paragraphs:
            if not paragraph['runs']:
                continue
            else:
                direction = 'rtl' if paragraph['rtl'] else 'ltr'
                run_html = []
                for run in paragraph['runs']:
                    style = [
                 f'font-family:"{run["font"]}"', f"font-size:{run['size'] / 2:g}pt"]
                    if run['bold']:
                        style.append('font-weight:bold')
                    else:
                        if run.get('italic'):
                            style.append('font-style:italic')
                        run_html.append(f"<span style='{'; '.join(style)}'>{self._escapeHtmlText(run['text'])}</span>")

                body.append(f"<p dir='{direction}'>{''.join(run_html)}</p>")

        html = f"<html><head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'/></head><body>{''.join(body)}</body></html>"
        rtf = _buildRtfFromParagraphs(paragraphs) if Across.os == 'mac' else None
        return (
         html, rtf)

    def _getRawSelection(self):
        """Return (plain_text, html_or_None) for the current selection.
        Sub-classes must override this."""
        raise NotImplementedError

    def removePageTag(self, text):
        """Remove page-number tags (⦗...⦘) from plain text or HTML."""
        if not self.page_tag_pattern:
            self.page_tag_pattern = re.compile(' *⦗?ص?\\:? *\\d*\\⦘ *')
        return self.page_tag_pattern.sub(' ', text)

    def selectionLimits(self):
        """Return (start, end) character offsets of the current selection."""
        anchor = self.textCursor().anchor()
        position = self.textCursor().position()
        if anchor < position:
            return (anchor, position)
        return (position, anchor)

    def getAyat(self, selection):
        """Extract verse numbers from a quran selection."""
        start, end = self.selectionLimits()
        whole_text = self.toPlainText()
        for letter in selection:
            if letter in '()﴿١٢٣٤٥٦٧٨٩٠0123456789\u06dd ﴾':
                start += 1
            else:
                break

        for letter in selection[::-1]:
            if letter in '()﴿١٢٣٤٥٦٧٨٩٠0123456789\u06dd ﴾':
                end -= 1
            else:
                break

        for letter in whole_text[end:]:
            if letter not in '١٢٣٤٥٦٧٨٩٠0123456789':
                end += 1
            else:
                break

        for letter in whole_text[end:]:
            if letter in '١٢٣٤٥٦٧٨٩٠0123456789':
                end += 1
            else:
                break

        ayat_piece = whole_text[start:end]
        ayat = [latinize(aya) for aya in re.findall('\\d+', ayat_piece)]
        if ayat[0] == ayat[-1]:
            return f": {ayat[0]}"
        return f": {ayat[0]}-{ayat[-1]}"

    def getInlineSora(self):
        """Return sura name from inline text before the selection, if present."""
        _, end = self.selectionLimits()
        if end > 1:
            whole_text = self.toPlainText()
            previous_text = whole_text[:end]
            shift_position = previous_text.rfind('سورة')
            if shift_position != -1:
                return whole_text[shift_position:].splitlines()[0][5:-1]

    def getInlinePage(self, selection):
        """Return the nearest page number for the selection.
        Checks if the selection itself starts with a page tag first, then
        searches backwards through the full browser text."""
        if selection.startswith('⦗'):
            return val(selection)
        start, _ = self.selectionLimits()
        if start > 1:
            whole_text = self.toPlainText()
            previous_text = whole_text[0:start]
            shift_position = previous_text.rfind('⦗')
            if shift_position != -1:
                return val(whole_text[shift_position:])

    def selectWholeWords(self, forced=None):
        """Expand the current selection to whole-word boundaries."""
        cur = self.textCursor()
        text = self.toPlainText()
        start, end = cur.anchor(), cur.position()
        if end > start:
            cur.beginEditBlock()
            cur.setPosition(start)
            if text[start] != ' ':
                cur.movePosition(QTextCursor.StartOfWord, QTextCursor.MoveAnchor)
            cur.setPosition(end, QTextCursor.KeepAnchor)
            if not cur.atBlockStart():
                if text[end - 1] != ' ':
                    position = cur.position()
                    cur.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
                    if position != cur.position():
                        remove = 0
                        for letter in text[cur.position() - 1:position - 1:-1]:
                            if re.match('\\W', letter):
                                remove += 1
                            else:
                                break

                        if remove:
                            cur.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, remove)
            cur.endEditBlock()
            self.setTextCursor(cur)
        else:
            if start > end:
                if forced:
                    cur.beginEditBlock()
                    cur.setPosition(start)
                    if text[start - 1] != ' ':
                        cur.movePosition(QTextCursor.EndOfWord, QTextCursor.MoveAnchor)
                    cur.setPosition(end, QTextCursor.KeepAnchor)
                    if text[end] != ' ':
                        cur.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
                    cur.endEditBlock()
                    self.setTextCursor(cur)

    def clearSelection(self):
        """Clear text selection without losing cursor position."""
        cursor = QTextCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def _cleanBookText(self, raw_text, raw_html):
        """Return clean plain text from a book selection.

        If the selection HTML contains tables (which are stored reversed as an
        RTL display hack), reverse them back before extracting plain text.
        Then: strips diacritics (if setting), decomposes honorifics completely,
        removes page-number tags, replaces Arabic-Indic digits with ASCII,
        and strips invisible chars.
        """
        if raw_html and Settings.getValue('unsuperscript_copied'):
            raw_html = re.sub('vertical-align\\s*:\\s*super[^"]*">[^<>]*</span>', '', raw_html)
            text = plain(reverseRows(raw_html) if isRich(raw_html) else raw_html)
        else:
            if raw_html and isRich(raw_html):
                text = plain(reverseRows(raw_html))
            else:
                text = raw_text
        if Settings.getValue('undiacritize_copied'):
            text = noTashkeel(text)
        text = text.translate(HonorificCache.plainTable())
        text = self.removePageTag(text)
        text = clean_invisible(toAsciiDigits(text))
        return text

    def _buildBookRich(self, text, attribute=''):
        """Build plain text, HTML, and RTF for a book copy from shared runs."""
        font = Settings.getValue('font_pages')
        book_font = font[0]
        book_size = font[1]
        book_bold = font[2]
        content_text = text.strip()
        if attribute:
            if '«' not in content_text:
                if '»' not in content_text:
                    if Settings.getValue('brackets_nass'):
                        content_text = f"«{content_text}»"
            separator = '\n' if Settings.getValue('attr_newline') else ' ' if Settings.getValue('attr_before') else '. '
            if Settings.getValue('attr_before'):
                plain_text = f"{attribute}{separator}{content_text}"
                paragraph_runs = [
                 self._richRun(attribute, book_font, book_size, book_bold),
                 self._richRun(separator, book_font, book_size, book_bold),
                 self._richRun(content_text, book_font, book_size, book_bold)]
            else:
                plain_text = f"{content_text}{separator}{attribute}"
                paragraph_runs = [
                 self._richRun(content_text, book_font, book_size, book_bold),
                 self._richRun(separator, book_font, book_size, book_bold),
                 self._richRun(attribute, book_font, book_size, book_bold)]
        else:
            plain_text = content_text
            paragraph_runs = [self._richRun(content_text, book_font, book_size, book_bold)]
        html, rtf = self._renderRichParagraphs([{'rtl':True,  'runs':paragraph_runs}])
        return (
         plain_text, html, rtf)

    def _buildBookAttribution(self):
        """Build and return the attribution string for the current book page.
        Does not touch any QMimeData — returns a plain string."""
        page = self.getInlinePage('') or self.page
        part = self.part
        if part == 'الكتاب':
            part = None
        part_str = f"{part}/ " if part else 'ص'
        page_str = str(page) if page else ''
        if page_str:
            page_str = f"{part_str}{page_str}"
        suffix = self.attribute_dict['suffix']
        if self.attribute_dict['printed'] != 1:
            suffix = f"{suffix} بترقيم الشاملة آليا".strip()
        if suffix:
            page_str = f"{page_str} {suffix}".strip()
        prefix = self.attribute_dict['prefix']
        start_qoos = '' if '«' in prefix else '«'
        end_qoos = '' if '»' in prefix else '»'
        colon = ':' if Settings.getValue('attr_before') else ''
        if Settings.getValue('helal_attr'):
            page_str = f"({page_str})"
        attribute = f"{start_qoos}{prefix}{end_qoos} {page_str}{colon}"
        if not Settings.getValue('brackets_attr'):
            attribute = attribute.replace('«', '').replace('»', '')
        if Settings.getValue('angular_attr'):
            attribute = f"[{attribute}]"
        return attribute

    def _quranHtmlSpans(self, text, rasm, attr=None):
        """Builds inner HTML spans for a quran verse (no outer document wrapper)."""
        family = {'majma':'KFGQPC HAFS Uthmanic Script', 
         'amiri':'Amiri Quran'}
        if rasm == 'majma':
            pre, post, size, height = (
             'ﵟ', 'ﵞ', Settings.getValue('majma_size'), '')
        else:
            pre, post, size, height = (
             '﴿', '﴾', Settings.getValue('amiri_size'), '; line-height: .6')
        attr_font = _attributionFont()
        if 'سورة' not in text:
            text = f"{pre}{text}{post}"
        text = text.replace('\n', '<br>')
        if rasm == 'emlaa':
            fp = Settings.getValue('font_pages')
            verse_font = [fp[0], Settings.getValue('emlaa_size'), fp[2], fp[3]]
            html = f"<span style='{fontSettingCss(verse_font)}'>{text}</span>"
            if attr:
                html += f" {attr}"
        else:
            html = f"""<span style='font: {size}pt "{family[rasm]}"\'>{text}</span>"""
            if attr:
                attr_style = fontSettingCss(attr_font)
                if height:
                    attr_style += f" line-height:{height.lstrip('; ')};"
                html += f"&nbsp;<span style='{attr_style}'>{attr}</span>"
        return html

    def _buildQuranHtml(self, raw_text, rasm, attribution):
        """Build QMimeData for Quran copy on non-macOS."""
        text = latinize(raw_text.replace('\u200c', '').replace('&#8204;', '')).strip()
        if rasm == 'emlaa':
            text = text.replace('﴾', ')').replace('﴿', '(')
        else:
            if rasm == 'majma':
                text = reverseNumbers(text, ' ')
        attr = attribution if attribution else None
        quran_html = self._quranHtmlSpans(text, rasm, attr)
        html = _quranHtmlDocument(quran_html)
        if attribution:
            plain_text = f"﴿{text}﴾ {attribution}"
        else:
            plain_text = text
        data = QMimeData()
        data.setText(clean_invisible(plain_text))
        data.setHtml(html)
        return data

    def _buildQuranPlain(self, raw_text, attribution):
        """Build plain-text-only QMimeData for unformatted emlaa quran copy.

        No HTML/RTF is attached; the verse is wrapped in '{ }' instead of the
        ornate '﴿﴾' brackets used by the formatted styles.
        """
        text = latinize(raw_text.replace('\u200c', '').replace('&#8204;', '')).strip()
        text = text.replace('﴾', ')').replace('﴿', '(')
        if 'سورة' not in text:
            text = f"{{{text}}}"
        if attribution:
            text = f"{text} {attribution}"
        return self._makeMimeData(clean_invisible(text))

    def _buildRichHtmlForClipboard(self, raw_html, attribute):
        """Build clipboard HTML from the raw Qt selection HTML.

        Preserves tables (un-reversing the QTextBrowser RTL display workaround)
        and inline base64 images.  Applies the unsuperscript setting and strips
        page-number tags.  Returns (html_str, rtf_bytes_or_None).
        """
        if not raw_html:
            return (None, None)
        html_content = reverseRows(raw_html) if isRich(raw_html) else raw_html
        if Settings.getValue('unsuperscript_copied'):
            html_content = re.sub('vertical-align\\s*:\\s*super[^"]*">[^<>]*</span>', '', html_content)
        html_content = self.removePageTag(html_content)
        if attribute:
            font = Settings.getValue('font_pages')
            attr_html = f"<p dir='rtl' style='{fontSettingCss(font)}'>{self._escapeHtmlText(attribute)}</p>"
            body = attr_html + html_content if Settings.getValue('attr_before') else html_content + attr_html
        else:
            body = html_content
        full_html = f"<html><head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'/></head><body>{body}</body></html>"
        rtf = htmlToRtfBytes(full_html) if Across.os == 'mac' else None
        return (
         full_html, rtf)

    def _formatBook(self, raw_text, raw_html, with_attribute):
        """Full book copy pipeline: clean text → build HTML → apply attribution.

        Normally the HTML is rebuilt from scratch out of the cleaned plain text
        (honorifics decomposed, digits latinized, images dropped by construction).
        A table can't be represented that way, so only when the selection
        contains one (isRich) is formatted output forced with the raw Qt HTML
        as the basis instead (tables un-reversed; honorifics/images inside the
        table are left as-is since we can't safely rebuild a table from scratch).
        """
        text = self._cleanBookText(raw_text, raw_html)
        attribute = self._buildBookAttribution() if with_attribute else ''
        force_rich = isRich(raw_html)
        if force_rich:
            plain_text, _, _ = self._buildBookRich(text, attribute)
            html, rtf = self._buildRichHtmlForClipboard(raw_html, attribute)
        else:
            plain_text, html, rtf = self._buildBookRich(text, attribute)
        return self._makeMimeData(plain_text,
          html,
          (rtf if Across.os == 'mac' else None),
          force_formatted=force_rich)

    def _buildQuranAttribution(self):
        """Return the quran attribution string, e.g. '[سورة البقرة: 1-3]'.
        Returns empty string for sura-title selections."""
        text = self.textCursor().selectedText()
        if 'سورة' in text:
            return ''
        rasm = self.attribute_dict['rasm']
        sora = self.getInlineSora()
        if not sora:
            sora_num, _ = posFromAya(ayaFromPage(self.attribute_dict['page']))
            sora = getSoraNames()[sora_num - 1]
        ayat = self.getAyat(text)
        if rasm == 'majma':
            ayat = reverseNumbers(ayat, '-')
        return f"[{sora}{ayat}]"

    def _buildQuranRich(self, raw_text, rasm, attribution=''):
        """Build plain text, HTML, and RTF for quran copy from shared runs."""
        text = raw_text
        if rasm == 'majma':
            text = reverseNumbers(text, ' ')
            font = 'KFGQPC HAFS Uthmanic Script'
            size = Settings.getValue('majma_size')
        else:
            if rasm == 'amiri':
                font = 'Amiri Quran'
                size = Settings.getValue('amiri_size')
            else:
                font = Settings.getValue('font_pages')[0]
                size = Settings.getValue('emlaa_size')
        text = text.strip(' \n\r[]')
        pre, post = ('﴿', '﴾') if 'سورة' not in text else ('', '')
        plain_text = f"{pre}{text}{post}"
        fallback_font = 'Traditional Naskh'
        attribution_font = _attributionFont()
        runs = []
        if pre:
            runs.append(self._richRun(pre, fallback_font, size))
        if text:
            runs.append(self._richRun(text, font, size))
        if post:
            runs.append(self._richRun(post, fallback_font, size))
        if attribution:
            plain_text = f"{plain_text} {attribution}"
            runs.append(self._richRun(' ', fallback_font, size))
            runs.append(self._richRunFromFontSetting(attribution, attribution_font))
        html, rtf = self._renderRichParagraphs([{'rtl':True,  'runs':runs}])
        return (
         plain_text, html, rtf)

    def _formatQuran(self, raw_text, with_attribute):
        """Full quran copy pipeline: build HTML from plain text + optional attribution."""
        rasm = self.attribute_dict['rasm']
        raw_text = raw_text.translate(HonorificCache.plainTable())
        attribution = self._buildQuranAttribution() if with_attribute else ''
        if rasm not in ('majma', 'amiri'):
            raw_text = toAsciiDigits(raw_text)
            attribution = toAsciiDigits(attribution)
        if rasm == 'emlaa':
            if not Settings.getValue('copy_formatted'):
                return self._buildQuranPlain(raw_text, attribution)
            if Across.os != 'mac':
                return self._buildQuranHtml(raw_text, rasm, attribution)
            plain_text, html, rtf = self._buildQuranRich(raw_text, rasm, attribution)
            return self._makeMimeData((clean_invisible(plain_text)), (clean_invisible(html)), rtf, word_xml=(rasm == 'majma'),
              force_formatted=(rasm in ('majma', 'amiri')))

    def createMimeDataFromSelection(self, with_attribute=False):
        """Build clipboard data for the current selection.

        Dispatches to the book or quran pipeline when attribute_dict is set,
        or falls back to a plain clean copy.  Sub-classes provide the raw
        selection via _getRawSelection().
        """
        if self._isQuran():
            self.selectWholeWords(True)
        raw_text, raw_html = self._getRawSelection()
        if self._isBook():
            return self._formatBook(raw_text, raw_html, with_attribute)
        if self._isQuran():
            return self._formatQuran(raw_text, with_attribute)
        return self._makeMimeData(clean_invisible(toAsciiDigits(raw_text)))

    def copyContent(self):
        """Copy selected text (or all text if nothing is selected)."""
        empty = self.textCursor().selection().isEmpty()
        if empty:
            cursor = self.textCursor()
            self.selectAll()
        data = self.createMimeDataFromSelection()
        setClipboardMimeData(data)
        if empty:
            self.clearSelection()
            self.setTextCursor(cursor)

    def copyAttribute(self):
        """Copy selected text with attribution (or all text if nothing is selected)."""
        empty = self.textCursor().selection().isEmpty()
        if empty:
            cursor = self.textCursor()
            self.selectAll()
        data = self.createMimeDataFromSelection(with_attribute=True)
        setClipboardMimeData(data)
        if empty:
            self.clearSelection()
            self.setTextCursor(cursor)


class ReadersBrowser(QPlainTextEdit, BrowserMixin):
    link = Signal(str)

    def __init__(self):
        QPlainTextEdit.__init__(self)
        self.document().setDefaultTextOption(QTextOption(Qt.AlignRight))
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setTabChangesFocus(True)
        self.page_tag_pattern = self.part = self.page = None
        self.attribute_dict = {}
        self.rasm = None
        unhideSelection(self)

    def _applyDisplayFont(self, rasm=None):
        self.rasm = rasm
        if rasm == 'majma':
            self.setFont(QFont('KFGQPC HAFS Uthmanic Script', 20, False))
        else:
            if rasm == 'amiri':
                self.setFont(QFont('Amiri Quran', 17, False))
            else:
                font = Settings.getValue('font_pages')
                self.setFont(QtFont(font, scale=False))

    def setHtml(self, text, tashkeel=True, _=None, rasm=None):
        self._applyDisplayFont(rasm)
        if not tashkeel:
            text = noTashkeel(text)
        self.document().setPlainText(plain(text))
        self.moveCursor(QTextCursor.Start)
        self.find('\x01')
        self.ensureCursorVisible()

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()
        anchor = QTextCursor.KeepAnchor if modifiers & Qt.ShiftModifier else QTextCursor.MoveAnchor
        if matchesShortcutEvent(event, 'Ctrl+Up', wrapped=False):
            cur = self.textCursor()
            cur.beginEditBlock()
            cur.movePosition(QTextCursor.PreviousCharacter, anchor)
            cur.movePosition(QTextCursor.StartOfBlock, anchor)
            cur.endEditBlock()
            self.setTextCursor(cur)
            cur.select(QTextCursor.BlockUnderCursor)
            NVDA.silence()
            NVDA.say(cur.selectedText())
            return
        if matchesShortcutEvent(event, 'Ctrl+Down', wrapped=False):
            cur = self.textCursor()
            cur.beginEditBlock()
            cur.movePosition(QTextCursor.NextCharacter, anchor)
            cur.movePosition(QTextCursor.EndOfBlock, anchor)
            cur.movePosition(QTextCursor.NextCharacter, anchor)
            cur.endEditBlock()
            self.setTextCursor(cur)
            cur.select(QTextCursor.BlockUnderCursor)
            NVDA.silence()
            NVDA.say(cur.selectedText())
            return
        if key == Qt.Key_Up:
            cur = self.textCursor()
            cur.movePosition(QTextCursor.Up, anchor)
            self.setTextCursor(cur)
            cur.select(QTextCursor.LineUnderCursor)
            NVDA.silence()
            NVDA.say(cur.selectedText())
            return
        if key == Qt.Key_Down:
            cur = self.textCursor()
            cur.movePosition(QTextCursor.Down, anchor)
            self.setTextCursor(cur)
            cur.select(QTextCursor.LineUnderCursor)
            NVDA.silence()
            NVDA.say(cur.selectedText())
            return
        if matchesShortcutEvent(event, 'Ctrl+X') or matchesShortcutEvent(event, 'Ctrl+V'):
            super().keyPressEvent(event)
        elif modifiers & Qt.ControlModifier:
            super().keyPressEvent(event)
        elif Qt.Key_F1 <= key <= Qt.Key_F35 or key in {Qt.Key_Left, Qt.Key_Right, Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_End, Qt.Key_Copy, Qt.Key_End, Qt.Key_Home}:
            super().keyPressEvent(event)

    def putCursor(self, position):
        cur = self.textCursor()
        cur.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor, position)
        self.setTextCursor(cur)

    def dropEvent(self, event):
        pass

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.sayMe()

    def readPage(self):
        if self.hasFocus():
            self.sayMe()
        else:
            self.setFocus()

    def sayMe(self):
        NVDA.say(self.toPlainText())

    def scrollToAnchor(self, _=None, __=None):
        pass

    def _getRawSelection(self):
        """Return (plain_text, None) — ReadersBrowser has no HTML source."""
        return (
         self.textCursor().selection().toPlainText(), None)

    def createMimeDataFromSelection(self, with_attribute=False):
        return BrowserMixin.createMimeDataFromSelection(self, with_attribute)


class StandardBrowser(QTextBrowser, BrowserMixin):
    link = Signal(str)

    def __init__(self):
        QTextBrowser.__init__(self)
        self.raw_html = None
        self.current_scale = 0
        self.extra_selections = []
        palette = QApplication.palette()
        self.back = palette.highlight().color()
        self.line = palette.highlightedText().color()
        self.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard | Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        self.page_tag_pattern = self.part = self.page = None
        self.attribute_dict = {}
        unhideSelection(self)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self._handleAnchor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showActionsContextMenu)
        self.actions = []
        self.copyAttributeAction = None
        self.searchGoogleAction = None
        self.searchAppAction = None
        self.prepareCopyToMsWordAction = None
        self.prepareCopyToMsWordSeparatorAction = None
        self.searchSeparatorAction = None
        items = (
         (
          0, QCoreApplication.translate('MainWindow', 'Copy'), 'Ctrl+C', self.copyContent),
         (
          1, QCoreApplication.translate('MainWindow', 'Copy With Attribute'), 'Shift+Ctrl+C', self.copyAttribute),
         (
          2, QCoreApplication.translate('MainWindow', 'Select All'), 'Ctrl+A', self.selectAll),
         (
          3, QCoreApplication.translate('MainWindow', 'Search Google'), None, self.searchGoogle),
         (
          4, QCoreApplication.translate('MainWindow', 'Search Shamela'), None, self.searchApp))
        for index, label, sequence, slot in items:
            action = QAction(label, self)
            action.triggered.connect(slot)
            if sequence:
                action.setShortcut(QKeySequence(sequence))
                action.setShortcutContext(Qt.WidgetShortcut)
            if index in frozenset({3, 4}):
                self.copyAvailable.connect(action.setEnabled)
                action.setEnabled(False)
            if index == 1:
                action.setVisible(False)
                self.copyAttributeAction = action
            else:
                if index == 3:
                    self.searchGoogleAction = action
                else:
                    if index == 4:
                        self.searchAppAction = action
            self.addAction(action)
            self.actions.append(action)
            if index == 2:
                sep_action = QAction()
                sep_action.setSeparator(True)
                self.searchSeparatorAction = sep_action
                self.addAction(sep_action)
                self.actions.append(sep_action)

    def showActionsContextMenu(self, position):
        menu = QMenu()
        for action in self.actions:
            menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))

    def putCursor(self, _):
        pass

    def readPage(self):
        pass

    def setSource(self, url, resource_type=None):
        if resource_type is None:
            return super().setSource(url)
        try:
            return super().setSource(url, resource_type)
        except TypeError:
            return super().setSource(url)

    def setHtml(self, text, tashkeel=True, keep_position=None, rasm=None):
        """Set page HTML.  Stores the original for CSS zoom, applies tashkeel
        filtering, and optionally preserves the scroll position."""
        if not tashkeel:
            text = noTashkeel(text)
        self.raw_html = text
        self._setZoomedHtml(keep_position)
        self.clearHistory()

    def _setZoomedHtml(self, keep_position=None):
        if keep_position:
            pos = self.verticalScrollBar().value()
            super().setHtml(self.zoomedHtml())
            self.verticalScrollBar().setValue(pos)
        else:
            super().setHtml(self.zoomedHtml())

    def loadResource(self, type, url):
        s_url = url.toDisplayString()
        if s_url.startswith('inr://'):
            self.link.emit(s_url)
            return QByteArray()
        return super().loadResource(type, url)

    def _getRawSelection(self):
        if self.extra_selections:
            texts = {self.textCursor().anchor(): self.textCursor().selection().toPlainText()}
            for selection in self.extra_selections:
                texts[selection.cursor.anchor()] = selection.cursor.selection().toPlainText()

            ordered = [texts[k] for k in sorted(texts)]
            return (
             '\n'.join(ordered), None)
        raw = super().createMimeDataFromSelection()
        return (
         raw.text(), raw.html())

    def createMimeDataFromSelection(self, with_attribute=False):
        return BrowserMixin.createMimeDataFromSelection(self, with_attribute)

    def setAttributeDict(self, attribute_dict):
        self.attribute_dict = attribute_dict
        self.copyAttributeAction.setVisible(True)
        value = True
        if 'rasm' in self.attribute_dict:
            if self.attribute_dict['rasm'] != 'emlaa':
                value = False
        self.searchGoogleAction.setVisible(value)
        self.searchAppAction.setVisible(value)
        self.searchSeparatorAction.setVisible(value)

    def setPage(self, part, page):
        self.part = part
        self.page = page

    def searchSelection(self):
        text, _ = self._getRawSelection()
        return text

    def searchGoogle(self):
        search_phrase = toAsciiDigits(treatSearch((self.searchSelection()), clear_wild=True))
        if search_phrase:
            QDesktopServices.openUrl(QUrl(f"https://google.com/search?q={search_phrase}"))

    def searchApp(self):
        from engine import Query
        search_phrase = self.searchSelection()
        and_phrases = search_phrase.splitlines()
        if and_phrases:
            and_phrases = [treatSearch(phrase, clear_wild=True) for phrase in and_phrases]
            info = {'phrases': [[and_phrases], [], []]}
            for phrase in and_phrases:
                if re.match('\\d', phrase):
                    info['features'] = [
                     'numbers']
                    break

            query = Query(Across.global_index)
            query.load(info)
            Across.main_window.showSearchResults(query)

    def _handleAnchor(self, url):
        if url.scheme() == 'inr':
            self.link.emit(url.toString())
            return
        super().setSource(url)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            self.selectWholeWords()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.LeftButton:
            self.doubleClickedSelection()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cursor = self.textCursor()
            if event.modifiers() & Qt.ControlModifier:
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(self.back)
                selection.format.setForeground(self.line)
                selection.cursor = cursor
                self.extra_selections.append(selection)
                self.setExtraSelections(self.extra_selections)
            else:
                self.extra_selections = []
                self.setExtraSelections(self.extra_selections)
        super().mousePressEvent(event)

    def doubleClickedSelection(self):
        cur = self.textCursor()
        text = self.toPlainText()
        start, end = cur.anchor(), cur.position()
        if start > end:
            end, start = start, end
        if start >= len(text) or re.match('\\W', text[start]):
            return
        cur.beginEditBlock()
        cur.setPosition(start)
        position = cur.position()
        cur.setPosition(end, QTextCursor.KeepAnchor)
        cur.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
        if position != cur.position():
            remove = 0
            for letter in text[cur.position() - 1:position - 1:-1]:
                if re.match('\\W', letter):
                    remove += 1
                else:
                    break

            if remove:
                cur.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, remove)
        cur.endEditBlock()
        self.setTextCursor(cur)

    def selectWholeWords(self, forced=None):
        cur = self.textCursor()
        text = self.toPlainText()
        start, end = cur.anchor(), cur.position()
        if end > start:
            cur.beginEditBlock()
            cur.setPosition(start)
            if text[start] != ' ':
                cur.movePosition(QTextCursor.StartOfWord, QTextCursor.MoveAnchor)
            cur.setPosition(end, QTextCursor.KeepAnchor)
            if not cur.atBlockStart():
                if text[end - 1] != ' ':
                    position = cur.position()
                    cur.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
                    if position != cur.position():
                        remove = 0
                        for letter in text[cur.position() - 1:position - 1:-1]:
                            if re.match('\\W', letter):
                                remove += 1
                            else:
                                break

                        if remove:
                            cur.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, remove)
            cur.endEditBlock()
            self.setTextCursor(cur)
        else:
            if start > end:
                if forced:
                    cur = self.textCursor()
                    cur.beginEditBlock()
                    cur.setPosition(start)
                    if text[start - 1] != ' ':
                        cur.movePosition(QTextCursor.EndOfWord, QTextCursor.MoveAnchor)
                    cur.setPosition(end, QTextCursor.KeepAnchor)
                    if text[end] != ' ':
                        cur.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
                    cur.endEditBlock()
                    self.setTextCursor(cur)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()
        anchor = QTextCursor.KeepAnchor if modifiers & Qt.ShiftModifier else QTextCursor.MoveAnchor
        if matchesShortcutEvent(event, 'Ctrl+Up', wrapped=False):
            cur = self.textCursor()
            cur.beginEditBlock()
            cur.movePosition(QTextCursor.PreviousCharacter, anchor)
            cur.movePosition(QTextCursor.StartOfBlock, anchor)
            cur.endEditBlock()
            self.setTextCursor(cur)
            return
        if matchesShortcutEvent(event, 'Ctrl+Down', wrapped=False):
            cur = self.textCursor()
            cur.beginEditBlock()
            cur.movePosition(QTextCursor.NextCharacter, anchor)
            cur.movePosition(QTextCursor.EndOfBlock, anchor)
            cur.movePosition(QTextCursor.NextCharacter, anchor)
            cur.endEditBlock()
            self.setTextCursor(cur)
            return
        if matchesShortcutEvent(event, 'Ctrl++') or matchesShortcutEvent(event, 'Ctrl+='):
            self.changeCssZoom(1)
            return
        if matchesShortcutEvent(event, 'Ctrl+-') or matchesShortcutEvent(event, 'Ctrl+_'):
            self.changeCssZoom(-1)
            return
        if matchesShortcutEvent(event, 'Ctrl+0'):
            self.changeCssZoom(0)
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.readPage()

    def wheelEvent(self, event):
        if matchesShortcutModifiers(event.modifiers(), 'Ctrl+0'):
            try:
                delta = event.delta()
            except AttributeError:
                delta = event.angleDelta().y()

            if delta > 0:
                self.changeCssZoom(1)
            else:
                if delta < 0:
                    self.changeCssZoom(-1)
        else:
            super().wheelEvent(event)

    _ZOOM_FONT_PT_RE = re.compile('(?P<prop>\\bfont(?:-size)?)(?P<sep>\\s*:\\s*)(?P<num>\\d+(?:\\.\\d+)?)pt\\b', re.IGNORECASE)
    _ZOOM_TABLE_SPACING_RE = re.compile('(?P<prop>\\b(?:padding-bottom|margin-top))(?P<sep>\\s*:\\s*)(?P<num>\\d+(?:\\.\\d+)?)\\b', re.IGNORECASE)

    def zoomedHtml(self):
        if self.current_scale == 0:
            return self.raw_html
        scale = self.current_scale

        def bumpPt(match):
            return f"{match['prop']}{match['sep']}{float(match['num']) + scale:g}pt"

        def bumpSpacing(match):
            value = float(match['num']) + scale
            if match['prop'].lower() == 'padding-bottom':
                if value < 10:
                    value = 10
            return f"{match['prop']}{match['sep']}{value:g}"

        text = self._ZOOM_FONT_PT_RE.sub(bumpPt, self.raw_html)
        return self._ZOOM_TABLE_SPACING_RE.sub(bumpSpacing, text)

    def changeCssZoom(self, value):
        if value == 0:
            self.current_scale = 0
        else:
            self.current_scale += value
        pos = self.verticalScrollBar().value()
        super().setHtml(self.zoomedHtml())
        self.verticalScrollBar().setValue(pos)


class NVDA:
    if Across.os == 'win':
        dll_path = os.path.join(Across.bin_directory, f"nvdaControllerClient{Across.running_arch}.dll")
        if not os.path.isfile(dll_path):
            if Across.running_arch == 'arm64':
                dll_path = os.path.join(Across.bin_directory, 'nvdaControllerClient64.dll')
        try:
            clientLib = ctypes.windll.LoadLibrary(dll_path)
        except Exception:
            clientLib = None

    else:
        clientLib = None

    @staticmethod
    def isRunning():
        if NVDA.clientLib:
            return NVDA.clientLib.nvdaController_testIfRunning() == 0
        return False

    @staticmethod
    def silence():
        if NVDA.isRunning():
            NVDA.clientLib.nvdaController_cancelSpeech()

    @staticmethod
    def say(text):
        if NVDA.isRunning():
            NVDA.clientLib.nvdaController_speakText(text)


class BookHolder(QWidget):

    def __init__(self, off_features=None):
        super().__init__()
        from displaybook import DisplayBook
        self.placeholder = QTextBrowser()
        self.book = DisplayBook(off_features=off_features)
        self.book.hide()
        self.setLayout(customLayout(True, [self.placeholder, self.book]))

    def showBook(self, res=None, service=None):
        if res:
            self.book.setBookId(res[0])
            self.book.resultClicked(res)
        else:
            if service:
                self.book.goService(service)
        self.placeholder.hide()
        self.book.show()

    def clear(self):
        self.book.hide()
        self.placeholder.show()


class ServiceBooks(QWidget):
    display = Signal(list)

    def __init__(self, service_name):
        super().__init__()
        self.service_name = service_name
        self.editor_loaded = None
        self.lastbook = self.key_id = None
        self.iso_cache = {}
        self.search_pieces = []
        self.books = None
        self.categories = None
        self.positions_list = QListWidget()
        standardFont(self.positions_list)
        self.positions_list.setFixedWidth(22)
        self.positions_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.positions_list.itemSelectionChanged.connect(self.displaySubItem)
        self.positions_list.itemClicked.connect(self.displaySubItem)
        self.positions_list.itemActivated.connect(self.displaySubItem)
        self.positions_list.setVisible(False)
        self.book_list = QListWidget()
        standardFont(self.book_list)
        self.book_list.setStyleSheet('QListWidget::item { padding: 2px; }')
        self.book_list.setIconSize(QSize(16, 16))
        self.book_list.setWordWrap(False)
        self.book_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.book_filter = TimedLineEdit(search_slot=(self.updateLine))
        self.book_list.itemSelectionChanged.connect(self.displayItem)
        self.book_list.itemClicked.connect(self.displaySubItem)
        self.book_list.itemActivated.connect(self.displaySubItem)
        self.editListButton = QPushButton(self.tr('Edit List'))
        self.editListButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.editListButton.setStyleSheet('text-align:center;')
        self.editListButton.clicked.connect(lambda: self.showEdit(True)
)
        list_layout = customLayout(False, [self.book_list, self.positions_list])
        view_layout = customLayout(True, [1, self.book_filter, 1, list_layout, 1, self.editListButton])
        self.viewer = QWidget()
        self.viewer.setLayout(view_layout)
        self.edit_list = QListWidget()
        standardFont(self.edit_list)
        self.edit_list.setStyleSheet('QListWidget::item { padding: 2px; }')
        self.edit_list.setIconSize(QSize(16, 16))
        self.edit_list.setWordWrap(False)
        self.edit_list.setSelectionMode(QAbstractItemView.SingleSelection)
        label = styledLabel(height=30)
        label.setText(self.tr('Select books to display'))
        self.editDoneButton = QPushButton(self.tr('Ok'))
        self.editDoneButton.clicked.connect(lambda: self.showEdit(False)
)
        edit_layout = customLayout(True, [label, 3, self.edit_list, 1, self.editDoneButton])
        self.editor = QWidget()
        self.editor.setLayout(edit_layout)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.viewer)
        self.stack.addWidget(self.editor)
        self.setLayout(customLayout(False, [self.stack]))

    def showEvent(self, event):
        Across.refresh_set.add(self)
        super().showEvent(event)

    def hideEvent(self, event):
        Across.refresh_set.discard(self)
        super().hideEvent(event)

    def reinstall(self):
        self.editor_loaded = None
        if self.key_id:
            self.loadItems(self.key_id)

    def reHistory(self):
        pass

    def refavorites(self):
        pass

    def showEdit(self, value):
        if value:
            self.loadEditor()
            self.stack.setCurrentIndex(1)
        else:
            self.editor_loaded = None
            self.saveEditor()
            self.loadItems(self.key_id)
            self.stack.setCurrentIndex(0)

    def displayItem(self):
        if not self.book_list.selectedItems():
            self.book_list.blockSignals(True)
            self.book_list.item(1).setSelected(True)
            self.book_list.blockSignals(False)
        if not self.book_list.selectedItems():
            return
        item = self.book_list.selectedItems()[0]
        data = item.data(Qt.UserRole)
        self.lastbook = data[0]
        page_ids = data[1]
        if not page_ids:
            return
        self.display.emit([self.lastbook, page_ids[0], self.service_name, self.key_id])
        self.positions_list.blockSignals(True)
        self.positions_list.clear()
        pages_number = len(page_ids)
        if pages_number == 1:
            self.positions_list.setVisible(False)
        else:
            for num in range(1, pages_number + 1):
                item = QListWidgetItem(arabize((f"{num}")))
                item.setTextAlignment(Qt.AlignCenter)
                self.positions_list.addItem(item)

            self.positions_list.setCurrentRow(0)
            self.positions_list.setVisible(True)
        self.positions_list.blockSignals(False)

    def displaySubItem(self):
        if not self.book_list.selectedItems():
            return
        item = self.book_list.selectedItems()[0]
        data = item.data(Qt.UserRole)
        book_id = data[0]
        page_ids = data[1]
        id_index = self.positions_list.currentRow() if self.positions_list.count() else 0
        self.display.emit([book_id, page_ids[id_index], self.service_name, self.key_id])

    def iso(self, book_name):
        if book_name not in self.iso_cache:
            self.iso_cache[book_name] = iso(book_name)
        return self.iso_cache[book_name]

    def updateLine(self):
        current_filter = True if self.search_pieces else False
        text = treatSearch(self.book_filter.text())
        if len(text) < 3:
            self.search_pieces = None
            if current_filter:
                self.loadItems()
        else:
            self.search_pieces = iso(text).split(' ')
            self.loadItems()

    def getCategories(self):
        from dbmanager import CoreDb
        if not self.categories:
            self.categories = CoreDb().categoryDict()
        return self.categories

    def loadItems(self, key_id=None):
        self.book_list.blockSignals(True)
        value = self._loadItems(key_id)
        self.book_list.blockSignals(False)
        return value

    def _loadItems(self, key_id):
        from dbmanager import Services
        self.book_list.clear()
        if key_id:
            self.books = Services.getBooks(self.service_name, key_id)
        if self.books:
            category_dict = self.getCategories()
            last_category = None
            no_selection = True
            for book in self.books:
                if self.filtred(book[0]):
                    if book[1] != last_category:
                        last_category = book[1]
                        listItem = QListWidgetItem(category_dict[last_category])
                        listItem.setBackground(CACHED_BRUSH_GRAY)
                        listItem.setForeground(CACHED_BRUSH_WHITE)
                        listItem.setFlags(Qt.NoItemFlags)
                        self.book_list.addItem(listItem)
                    else:
                        text = BookCache.bookName(book[0])
                        listItem = QListWidgetItem(text)
                        listItem.setToolTip(text)
                        listItem.setIcon(BookCache.bookIcon(book[0]))
                        listItem.setData(Qt.UserRole, [book[0], book[2]])
                        if not book[2]:
                            listItem.setFlags(Qt.NoItemFlags)
                        self.book_list.addItem(listItem)
                    if no_selection:
                        if self.lastbook:
                            if self.lastbook == book[0]:
                                if book[2]:
                                    no_selection = None
                                    listItem.setSelected(True)

            if no_selection:
                self.lastbook = None
            self.key_id = key_id
            return True
        self.key_id = self.lastbook = None

    def loadEditor(self):
        from dbmanager import Services
        if self.editor_loaded:
            return
        books = Services.getAllBooks(self.service_name)
        if books:
            self.edit_list.clear()
            category_dict = self.getCategories()
            last_category = None
            for book in books:
                if self.filtred(book[0]):
                    if book[1] != last_category:
                        last_category = book[1]
                        listItem = QListWidgetItem(category_dict[last_category])
                        listItem.setBackground(CACHED_BRUSH_GRAY)
                        listItem.setForeground(CACHED_BRUSH_WHITE)
                        listItem.setFlags(Qt.NoItemFlags)
                        self.edit_list.addItem(listItem)
                    else:
                        listItem = QListWidgetItem(BookCache.bookName(book[0]))
                        listItem.setIcon(BookCache.bookIcon(book[0]))
                        listItem.setData(Qt.UserRole, book[0])
                        listItem.setFlags(listItem.flags() | Qt.ItemIsUserCheckable)
                        listItem.setCheckState(toCheckState(book[2] != 1))
                        self.edit_list.addItem(listItem)

        self.editor_loaded = True

    def saveEditor(self):
        from dbmanager import Services
        count = self.edit_list.count()
        any_checked = False
        first_book_item = None
        for i in range(count):
            item = self.edit_list.item(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                if first_book_item is None:
                    first_book_item = item
                if isCheckedState(item.checkState()):
                    any_checked = True
                    break

        if not any_checked:
            if first_book_item:
                first_book_item.setCheckState(toCheckState(Qt.Checked))
        selection_dict = {}
        for i in range(count):
            item = self.edit_list.item(i)
            book_id = item.data(Qt.UserRole)
            if book_id:
                if item.flags() & Qt.ItemIsUserCheckable:
                    selection_dict[book_id] = 0 if isCheckedState(item.checkState()) else 1

        Services.saveServiceSelection(self.service_name, selection_dict)

    def filtred(self, book_id):
        if not self.search_pieces:
            return True
        return contains(self.iso(BookCache.abstractName(book_id)), self.search_pieces)


class NumCombo(QComboBox):
    valueChanged = Signal(int)

    def __init__(self, max_num=None, num_list=None, read_only=None, force_ascii=None):
        super().__init__()
        self.read_only = read_only
        self.force_ascii = force_ascii
        self.num_list = list(num_list) if num_list is not None else None
        self.setEditable(False if read_only else True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self._applyDigitPolicy()
        e = QKeyEvent(QEvent.KeyPress, Qt.Key_Direction_R, Qt.NoModifier)
        QApplication.sendEvent(self, e)
        self.max_num = None
        if max_num or num_list:
            self.load(max_num, num_list)
        self.currentTextChanged.connect(self._valueChanged)

    def _applyDigitPolicy(self):
        if self.force_ascii:
            self.setLocale(QLocale(QLocale.English))
        else:
            if Settings.getValue('system_numbers'):
                self.setLocale(QLocale())
            else:
                self.setLocale(QLocale(QLocale.Arabic, QLocale.Egypt))

    def _digits(self, value):
        if self.force_ascii:
            return toAsciiDigits(value)
        return arabize((f"{value}"))

    def load(self, num, num_list):
        if num:
            self.max_num = num
            self.num_list = list(range(1, self.max_num + 1))
        else:
            if num_list is not None:
                self.num_list = list(num_list)
        num_list = self.num_list or []
        self.addItems([self._digits(i) for i in num_list])

    def setMaximum(self, num):
        self.blockSignals(True)
        self.clear()
        self.load(num, None)
        self.blockSignals(False)

    def _valueChanged(self, text):
        if text:
            num = int(latinize(text))
            if self.max_num:
                if num <= self.max_num:
                    self.valueChanged.emit(num)

    def value(self):
        text = self.currentText()
        if text:
            return int(latinize(text))

    def setValue(self, value):
        self.blockSignals(True)
        self.setCurrentText(self._digits(value))
        self.blockSignals(False)

    def refreshDigits(self):
        self._applyDigitPolicy()
        current_value = self.value()
        self.blockSignals(True)
        self.clear()
        self.load(self.max_num, self.num_list)
        if current_value:
            self.setCurrentText(self._digits(current_value))
        self.blockSignals(False)

    def focusInEvent(self, event):
        if not self.read_only:
            QTimer.singleShot(0, self.lineEdit().selectAll)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        self._applyDigitPolicy()
        key = event.key()
        if key == Qt.Key_Return:
            return
        redirection = False
        text = event.text()
        if text:
            if latinize(text).isdigit():
                e = QKeyEvent((QEvent.KeyPress), 0, (Qt.NoModifier), text=(self._digits(text)))
                super().keyPressEvent(e)
                redirection = True
        if not redirection:
            super().keyPressEvent(event)


class LineEdit(QLineEdit):

    def __init__(self, digit_policy=None, select=True, slot=None, width=None, focus_list=None, no_clear=None, modify_pasted=None):
        super().__init__()
        self.setFont(QApplication.font())
        self.digit_policy = digit_policy
        self.select = select
        if not no_clear:
            self.setClearButtonEnabled(True)
        self.slot = slot
        if modify_pasted:
            self.modify_pasted = modify_pasted
            self.textChanged.connect(self.testClip)
        self.focus_list = focus_list
        if width:
            self.setMaximumWidth(width)
        e = QKeyEvent(QEvent.KeyPress, Qt.Key_Direction_R, Qt.NoModifier)
        QApplication.sendEvent(self, e)

    def _syncPlaceholderPalette(self):
        if not hasattr(QPalette, 'PlaceholderText'):
            return
        app = QApplication.instance()
        if app is None:
            return
        app_palette = app.palette()
        palette = self.palette()
        changed = False
        for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            color = app_palette.color(group, QPalette.PlaceholderText)
            if palette.color(group, QPalette.PlaceholderText) != color:
                palette.setColor(group, QPalette.PlaceholderText, color)
                changed = True

        if changed:
            self.setPalette(palette)

    def testClip(self, text):
        clipboard_text = QApplication.clipboard().text()
        if text in {clipboard_text, self._normalizeInput(clipboard_text)}:
            self.setText(self.modify_pasted(clipboard_text))

    def setText(self, p_str):
        super().setText(self._normalizeInput(p_str))

    def paste(self):
        self.insert(self._normalizePastedInput(QApplication.clipboard().text()))

    def _normalizeInput(self, text):
        text = '' if text is None else str(text)
        text = clean_invisible(text)
        if self.digit_policy == 'ascii':
            return toAsciiDigits(text)
        if self.digit_policy == 'display':
            return displayDigits(text)
        return text

    def _normalizePastedInput(self, text):
        text = '' if text is None else str(text)
        text = clean_invisible(text)
        if self.digit_policy == 'ascii':
            return toAsciiDigits(text)
        return text

    def focusInEvent(self, QFocusEvent):
        if self.select:
            if not isCompleter(self):
                QTimer.singleShot(0, self.selectAll)
        super().focusInEvent(QFocusEvent)

    def showEvent(self, event):
        super().showEvent(event)
        self._syncPlaceholderPalette()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.StyleChange):
            self._syncPlaceholderPalette()

    def keyPressEvent(self, event):
        redirection = False
        text = event.text()
        if text:
            if latinize(text).isdigit():
                if self.digit_policy in ('ascii', 'display'):
                    e = QKeyEvent((QEvent.KeyPress), 0, (Qt.NoModifier), text=(self._normalizeInput(text)))
                    super().keyPressEvent(e)
                    redirection = True
        if not self.slot or event.key() in (Qt.Key_Enter, Qt.Key_Return):
            if not isCompleter(self):
                self.slot()
                redirection = True
            if not redirection:
                super().keyPressEvent(event)


class TimedLineEdit(LineEdit):

    def __init__(self, digit_policy='ascii', select=True, search_slot=None, width=None, focus_list=None, interval=None):
        super().__init__(digit_policy=digit_policy, select=select, width=width, focus_list=focus_list)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.CoarseTimer)
        self.timer.setInterval(interval or 500)
        self.timer.timeout.connect(self.dSlot)
        self.slot = search_slot
        self.textEdited.connect(self.timer.start)

    def dSlot(self):
        self.timer.stop()
        self.slot()

    def focusInEvent(self, event):
        QTimer.singleShot(0, self.selectAll)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            if self.focus_list:
                self.focus_list.setFocus()
                return
        else:
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                self.dSlot()
            else:
                super().keyPressEvent(event)


class BusySpinner:
    __doc__ = 'A throbber that actually turns, for anything that has to say "working".\n\n    Two kinds of user: the download/import cells, which draw the frame for a book\n    with no percent to give (a still image there reads as a stalled download),\n    and buttons that stand for work in flight - follow() turns their icon until\n    unfollow(). The eight frames are drawn once per ink colour and cached, so a\n    turn costs nothing but the repaint, and the timer stops itself the moment\n    nothing is working.'
    SIZES = (16, 24, 32, 48, 64)
    STEPS = 8
    INTERVAL = 150
    _timer = None
    _index = 0
    _frames = {}
    _followers = set()

    @classmethod
    def icon(cls):
        """the ring at the current frame, in the current theme's ink"""
        colour = QApplication.palette().color(QPalette.Text)
        key = (colour.rgb(), cls._index % cls.STEPS)
        if key not in cls._frames:
            icon = QIcon()
            for size in cls.SIZES:
                icon.addPixmap(cls._ring(size, key[1], QColor(colour)))

            cls._frames[key] = icon
        return cls._frames[key]

    @classmethod
    def _ring(cls, size, frame, colour):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.translate(size / 2.0, size / 2.0)
        painter.rotate(frame * 360.0 / cls.STEPS)
        for step in range(cls.STEPS):
            colour.setAlphaF(1.0 - step / float(cls.STEPS) * 0.85)
            painter.setBrush(colour)
            painter.drawEllipse(QPointF(0, -size * 0.34), size * 0.105, size * 0.105)
            painter.rotate(360.0 / cls.STEPS)

        painter.end()
        return pixmap

    @classmethod
    def follow(cls, widget):
        """turn this widget's icon until unfollow(); for a button that means busy"""
        cls._followers.add(widget)
        widget.setIcon(cls.icon())
        cls.poke()

    @classmethod
    def unfollow(cls, widget):
        cls._followers.discard(widget)

    @classmethod
    def poke(cls):
        """(re)start turning; safe to call from any progress event"""
        if cls._timer is None:
            cls._timer = QTimer()
            cls._timer.setInterval(cls.INTERVAL)
            cls._timer.timeout.connect(cls._tick)
        if not cls._timer.isActive():
            cls._timer.start()

    @classmethod
    def _tick(cls):
        cls._index += 1
        alive = None
        for widget in list(cls._followers):
            try:
                widget.setIcon(cls.icon())
            except RuntimeError:
                cls._followers.discard(widget)
                continue

            alive = True

        main_window = Across.main_window
        if main_window:
            window = main_window.update
            if window:
                if window.isVisible():
                    if Across.downloading_books or Across.importing_books:
                        window.refresh()
                        alive = True
                    window = main_window.pdf
                    if window:
                        if window.isVisible():
                            if Across.downloading_pdfs:
                                window.refresh()
                                alive = True
        if not alive:
            cls._timer.stop()


class CustomDialog(QDialog):

    def __init__(self, parent=None, fixed=None, geometry_name=None, icon=None):
        super().__init__(parent)
        if icon:
            super().setWindowIcon(QIcon(icon) if Across.active_theme == 'dark' else Icon.icon(icon))
        self.geometry_name = geometry_name
        self._restore_on_app_activate = False
        flags = Qt.Dialog | Qt.WindowCloseButtonHint
        if fixed:
            if Across.os == 'win':
                flags = flags | Qt.MSWindowsFixedSizeDialogHint
        if Across.os == 'mac':
            flags = flags | Qt.Tool
        self.setWindowFlags(flags)
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        Across.hidden_set.add(self)
        if self.geometry_name:
            self.settings = QSettings('shamela.ws_iv67', self.geometry_name)
            if self.settings.value('geometry'):
                self.restoreGeometry(self.settings.value('geometry', bytes('', 'utf-8')))
                self.noexceed()
            if parent:
                self.setWindowModality(Qt.NonModal)

    def noexceed(self):
        screen = QApplication.screenAt(self.frameGeometry().center())
        if not screen:
            screen = self.screen()
        if not screen:
            if self.parentWidget():
                screen = self.parentWidget().screen()
        if not screen:
            screen = QApplication.primaryScreen()
        rec = screen.availableGeometry()
        max_width = rec.width() - 50
        max_height = rec.height() - 50
        self.setMaximumWidth(max_width)
        self.setMaximumHeight(max_height)

    def centerOnParent(self):
        parent = self.parentWidget()
        self.adjustSize()
        screen = (parent.screen() if parent else None) or self.screen() or QApplication.primaryScreen()
        avail = screen.availableGeometry()
        if parent and parent.isVisible():
            center = parent.mapToGlobal(parent.rect().center())
        else:
            center = avail.center()
        geo = self.frameGeometry()
        geo.moveCenter(center)
        top_left = geo.topLeft()
        top_left.setX(max(avail.left(), min(top_left.x(), avail.right() - geo.width() + 1)))
        top_left.setY(max(avail.top(), min(top_left.y(), avail.bottom() - geo.height() + 1)))
        self.move(top_left)

    def show(self):
        self._restore_on_app_activate = False
        if self in Across.dialog_stack:
            Across.dialog_stack.remove(self)
        Across.dialog_stack.append(self)
        if not self.geometry_name:
            self.centerOnParent()
        super().show()
        self.raise_()
        self.activateWindow()

    def eventFilter(self, watched, event):
        if Across.os == 'mac':
            if watched is QApplication.instance():
                if event.type() == QEvent.ApplicationDeactivate:
                    self._restore_on_app_activate = self.isVisible()
                else:
                    if event.type() == QEvent.ApplicationActivate:
                        if self._restore_on_app_activate:
                            self._restore_on_app_activate = False
                            QTimer.singleShot(0, self.show)
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        self._restore_on_app_activate = False
        if self.geometry_name:
            self.settings.setValue('geometry', self.saveGeometry())
        if self in Across.dialog_stack:
            Across.dialog_stack.remove(self)
        self.hide()


class TableView(QTableView):

    def __init__(self, model=None, instant_display=None):
        super().__init__()
        self.total_width = self.widths = self.find_line = self.say_me = None
        self.instant_display = instant_display
        self.painted = False
        self.setTextElideMode(Qt.ElideMiddle)
        if model:
            self.setModel(model)
            model.firstRow.connect(self.firstRow)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().hide()
        self.setWordWrap(False)
        self.setTabKeyNavigation(False)
        self.horizontalHeader().setHighlightSections(False)
        self.clicked.connect(self.displayCurrent)
        self.doubleClicked.connect(self.displayBookPressed)
        self.bypass_first = None

    def bypassFirst(self, row):
        self.bypass_first = row

    def setDimensions(self, total, widths):
        self.total_width = total
        self.widths = widths

    def setSay(self, say_me):
        self.say_me = say_me

    def copyItems(self):
        pass

    def enterPressed(self):
        pass

    def displayBookPressed(self):
        pass

    def findPressed(self):
        if self.find_line:
            self.find_line.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        if matchesShortcutEvent(event, 'Ctrl+C'):
            self.copyItems()
            return
        if matchesShortcutEvent(event, 'Ctrl+D', wrapped=False):
            self.displayBookPressed()
            return
        if matchesShortcutEvent(event, 'Ctrl+F'):
            self.findPressed()
            return
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.enterPressed()
            return
        old_row = self.currentIndex().row()
        super().keyPressEvent(event)
        if self.instant_display or Settings.getValue('instant_display_result'):
            new_row = self.currentIndex().row()
            if old_row != new_row:
                self.displayRow(new_row)
            return

    def setModelSource(self, source, keep_position=None):
        """Call this Function to keep selection after setting source if possible"""
        will = False
        if not keep_position:
            will = True
        else:
            if not source:
                will = True
            else:
                if not self.model().rowCount():
                    will = True
                else:
                    row = self.currentIndex().row()
                    if row == -1:
                        will = True
        if will:
            self.model().setSource(source)
            return
        old_value = self.model().source[row]
        old_count = self.model().rowCount()
        self.model().source = source
        new_count = len(source)
        if new_count == old_count:
            self.model().dataChanged.emit(self.model().index(0, 0), self.model().index(new_count - 1, self.model().column_count - 1))
        else:
            self.model().beginResetModel()
            self.model().endResetModel()
        i = findInList(source, old_value)
        if i != -1:
            self.setCurrentIndex(self.model().index(i, 0))
            specialSelectRow(self, i)
            self.displayRow(i, keep_position=keep_position)
            return
        if new_count != old_count:
            keep_position = False
        new_row = row if row < new_count else new_count - 1
        self.setCurrentIndex(self.model().index(new_row, 0))
        self.displayRow(new_row, keep_position=keep_position)

    def simulateList(self):
        self.setShowGrid(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().hide()

    def displayRow(self, row):
        pass

    def firstRow(self, row):
        if self.bypass_first:
            self.displayRow(self.bypass_first)
            specialSelectRow(self, self.bypass_first)
            self.bypass_first = None
            return
        self.setCurrentIndex(self.model().index(row, 0))
        self.displayRow(row)
        self.scrollTo(self.model().index(row, 0))

    def displayCurrent(self):
        index = self.currentIndex()
        if index.isValid():
            row = index.row()
            self.displayRow(row)

    def focusInEvent(self, event):
        if self.say_me:
            NVDA.say(self.say_me)
        super().focusInEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.total_width and not self.horizontalScrollBar().isVisible():
            column_count = len(self.widths)
            widget_width = self.size().width()
            if column_count == 1:
                self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        else:
            EXTENSIBLE = 0
            CORRECTION = 24
            EXCEPTION = 32
            MARGIN = 8
            if EXTENSIBLE not in self.widths:
                self.widths[self.widths.index(max(self.widths))] = EXTENSIBLE
            unit = widget_width / self.total_width
            final_widths = []
            font_metrics = QFontMetrics(self.horizontalHeader().font())
            for i, width in enumerate(self.widths):
                if width != EXTENSIBLE:
                    if width != EXCEPTION:
                        width = int(width * unit)
                        if self.model().headers:
                            min_width = font_metrics.boundingRect(self.model().headers[i]).width() + MARGIN
                            if width < min_width:
                                width = min_width
                final_widths.append(width)

            remaining = widget_width - sum(final_widths) - CORRECTION
            final_widths = [width or remaining for width in final_widths]
            for i, width in enumerate(final_widths):
                self.horizontalHeader().resizeSection(i, width)


class BooksTable(TableView):

    def __init__(self, model=None):
        self.screen = None
        super().__init__(model=model, instant_display=True)

    def displayBook(self):
        from dbmanager import UserDb
        index = self.currentIndex()
        if index.isValid():
            row = index.row()
            book_id = self.model().source[row]
            if self.screen == 'history':
                will = Settings.getValue('lastpage_history')
            else:
                if self.screen == 'favorite':
                    will = Settings.getValue('lastpage_favorites')
                else:
                    will = Settings.getValue('lastpage_others')
            if will:
                page_id = UserDb().getPageFromHistory(book_id)
                if page_id:
                    Across.main_window.showBook(book_id, page_id)
                else:
                    Across.main_window.showBook(book_id)
            else:
                Across.main_window.showBook(book_id)

    def copyItems(self):
        source = self.model().source
        books = []
        rows = sorted(set([index.row() for index in self.selectedIndexes()]))
        for row in rows:
            books.append(BookCache.abstractName(source[row]))

        QApplication.clipboard().setText('\n'.join(books))

    def displayBookPressed(self):
        self.displayBook()

    def enterPressed(self):
        self.displayBook()


class TableModel(QAbstractTableModel):
    firstRow = Signal(int)

    def __init__(self, headers=None, parent=None):
        super().__init__(parent)
        self.headers = headers
        self.column_count = len(self.headers) if self.headers else 1
        self.source = []

    def clear(self):
        self.setSource([])

    def setSource(self, source, no_select=None):
        if source:
            old_count = len(self.source)
            self.source = source
            if old_count == len(self.source):
                self.dataChanged.emit(self.index(0, 0), self.index(old_count - 1, self.column_count - 1))
            else:
                self.beginResetModel()
                self.endResetModel()
                if not no_select:
                    self.firstRow.emit(0)
        else:
            self.source = []
            self.beginResetModel()
            self.endResetModel()

    def insertRows(self, value, parent=QModelIndex()):
        position = self.rowCount()
        added_count = len(value)
        self.beginInsertRows(parent, position, position + added_count - 1)
        self.source += value
        self.endInsertRows()
        if not position:
            self.firstRow.emit(0)

    def removeRows(self, row, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        del self.source[row]
        self.endRemoveRows()

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.source)

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if self.headers:
            if int_role == Qt.DisplayRole:
                if Qt_Orientation == Qt.Horizontal:
                    return self.headers[p_int]


def trueLapse(lapse):
    return 0.01 < lapse < 0.6


class Qtlabel(QLabel):
    clicked = Signal()
    rtClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rtClicked.emit()
        else:
            self.clicked.emit()


class CompleterModel:
    MODEL = None

    @classmethod
    def __init__(cls, user_db):
        if cls.MODEL is None:
            cls.MODEL = QStandardItemModel()
            user_db.fillPhrasesModel(cls.MODEL)

    @classmethod
    def addPhrase(cls, phrase):
        cls.MODEL.appendRow(QStandardItem(phrase))

    @classmethod
    def clear(cls):
        cls.MODEL.removeRows(0, cls.MODEL.rowCount())


class List(QListView):
    __doc__ = '\n    Text only listview and model depending on int key eg: search_id\n    '
    rowClicked = Signal(int, int)
    rowDoubleClicked = Signal(int, int)

    def __init__(self, row_text_func):
        super().__init__()
        self.source = []
        self.setModel(ListModel(self))
        self.clicked.connect(self._clicked)
        self.doubleClicked.connect(self._dclicked)
        self.row_text_func = row_text_func

    def currentChanged(self, current, previous):
        if not QApplication.mouseButtons():
            self._clicked()

    def _clicked(self):
        if self.source:
            row = self.currentIndex().row()
            source_id = self.source[row]
            self.rowClicked.emit(row, source_id)

    def _dclicked(self):
        if self.source:
            row = self.currentIndex().row()
            source_id = self.source[row]
            self.rowDoubleClicked.emit(row, source_id)

    def setSource(self, source):
        self.source = source
        self.model().beginResetModel()
        self.model().endResetModel()

    def clear(self):
        self.setSource([])

    def deleteSelected(self):
        selected_ids = []
        rows = sorted([index.row() for index in self.selectedIndexes()], reverse=True)
        first_row = rows[-1]
        for row in rows:
            selected_ids.append(self.source.pop(row))

        self.model().beginResetModel()
        self.model().endResetModel()
        index = self.model().index(first_row, 0)
        self.setCurrentIndex(index)
        self.selectionModel().select(index, QItemSelectionModel.Select)
        return selected_ids

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self._dclicked()
        else:
            super().keyPressEvent(event)

    def rowCount(self):
        return self.model().rowCount()


class ListModel(QAbstractListModel):

    def __init__(self, attached_view):
        super().__init__()
        self.attached_view = attached_view

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            if index.isValid():
                if self.attached_view.source:
                    row = index.row()
                    source_id = self.attached_view.source[row]
                    return self.attached_view.row_text_func(source_id)

    def rowCount(self, QModelIndex_parent=None):
        return len(self.attached_view.source)


def specialSelectRow(view, row):

    def doIt():
        view.setCurrentIndex(view.model().index(row, 0))
        start_row = view.rowAt(0)
        end_row = view.rowAt(view.height())
        visible_rows = end_row - start_row + 1
        if row < visible_rows - 1:
            scroll_row = 0
        else:
            shift = int(visible_rows / 2)
            scroll_row = row + shift - 2
            count = view.model().rowCount()
            final_row = count - 1
            if scroll_row > final_row:
                scroll_row = final_row
        view.scrollTo(view.model().index(scroll_row, 0))

    QTimer.singleShot(0, doIt)


def lined(lay):
    return customLayout(True, [hLine(), lay], spacing=0, margins=0)


def pack(value, file_path):
    try:
        if os.path.isfile(file_path):
            try:
                os.unlink(file_path)
            except:
                pass

            if os.path.isfile(file_path):
                return
        with open(file_path, 'wb') as f:
            msgpack.pack(value, f)
        return True
    except:
        return


def unpack(file_path):
    try:
        if os.path.isfile(file_path):
            with open(file_path, 'rb') as f:
                return msgpack.unpack(f, strict_map_key=False)
    except:
        pass