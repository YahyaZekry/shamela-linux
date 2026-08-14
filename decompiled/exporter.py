# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: exporter.py
import os
from qtpy.QtCore import QUrl
from qtpy.QtGui import QDesktopServices
from engine import Book
from cache import BookCache
from dbmanager import CoreDb, BookDb
from textmanager import safeName, adjustExport, toAsciiDigits
from platformutils import desktop_dir
PRE_PAGE = '\n<!DOCTYPE html><html lang=\'ar\' dir=\'rtl\'><head><meta content=\'text/html; charset=UTF-8\' http-equiv=\'Content-Type\'><style>@media all\n{\n\nbody\n{\ndirection: rtl;\nbackground-color: #D4D4D4;\nline-height: 2;\nfont: bold 18pt "Traditional Naskh";\ntext-align: center;\n}\n\nhr {clear:both; color: #221122;}\np {margin: 0px;}\n.title {color: #800000;}\n.footnote, .PageHead {font: bold 16pt "Traditional Naskh"; color: #464646;}\n.PageHead {font-style: italic}\n.PartName {float:right;}\n.PageNumber {float:left;}\n\n.Main {text-align:right; margin: 0 auto; max-width: 780px;}\n\n.PageText\n{\ntext-align: justify;\nbackground-color: #EFEBD6;\nmargin-top: 20px;\npadding: 90px 90px 90px 90px;\nborder: solid 1px gray;\nborder-right-width: 4px;\nborder-bottom-width: 4px;\n}\n\nTable\n{\nbackground-color: #800000;\nwidth: 90%;\n}\n\nTD {background-color: #fefbe7; padding: 0px 10px 0px 10px; vertical-align:middle;} \nTH {background-color: #e3e1cf; padding: 0px 10px 0px 10px; text-align:center; vertical-align:middle;}\n}\n\n@media print\n{\n.Main {width:650px;}\n.PageText\n\n{\npage-break-before:always;\nborder-width:0px;\nmargin:0px;\npadding:1px;\n}\n\n}\n</style><title>'
MID_PAGE = "</title></head><body><div class='Main'>"
POST_PAGE = '</div></body></html>'

def exportBooks(book_list, export_signal):
    book_quota = 1000 / len(book_list)
    base_folder = os.path.join(desktop_dir(), 'تصدير من الشاملة')
    for book_id in book_list:
        exportBook(book_id, base_folder, book_quota, export_signal)

    QDesktopServices.openUrl(QUrl.fromLocalFile(base_folder))
    export_signal.emit(0)


def exportBook(book_id, base_folder, book_quota, export_signal):
    file_names = {}
    book_db = BookDb(book_id)
    parts_list, parts_map = book_db.partsMap()
    book_name = BookCache.abstractName(book_id)
    betaka = CoreDb().bookBetaka(book_id, False, export=True)
    base_name = safeName(book_name, base_folder)
    if len(parts_list) == 1:
        file_names['0'] = file_names[parts_list[0]] = os.path.join(base_folder, f"{base_name}.htm")
    else:
        base_folder = os.path.join(base_folder, base_name)
        for part in parts_list:
            file_names[part] = os.path.join(base_folder, f"{prepare(part.zfill(3))}.htm")

    os.makedirs(base_folder, exist_ok=True)
    total = 0
    for part in parts_list:
        total += len(parts_map[part].pages_list)

    page_quota = book_quota / total
    book = Book(book_id)
    for part in parts_list:
        if part == '0':
            part_name = book_name
        else:
            if part.isdigit():
                part_name = f"{book_name} - جـ {part}"
            else:
                part_name = f"{book_name} - {part}"
        part_name = toAsciiDigits(part_name)
        pages_dict, footnotes_dict = book.getPart(parts_map[part].minId(), parts_map[part].maxId())
        part_text = [f"{PRE_PAGE}{part_name}{MID_PAGE}"]
        part_text.append(f"<div class='PageText'>{betaka}</div>")
        for page_id, page_num in parts_map[part].pages_list:
            page_text = pages_dict[page_id] if page_id in pages_dict else ''
            footnotes_text = footnotes_dict[page_id] if page_id in footnotes_dict else ''
            page_text = adjustExport(page_text, footnotes_text)
            page_head = f"<span class='PartName'>{part_name}</span>"
            if page_num:
                page_num = toAsciiDigits(f"(ص: {page_num})")
                page_num = f"<span class='PageNumber'>{page_num}</span>"
                page_head = f"{page_head}{page_num}"
            page_head = f"<div class='PageHead'>{page_head}<hr/></div>"
            page_text = f"<div class='PageText'>{page_head}{page_text}</div>"
            part_text.append(page_text)
            export_signal.emit(page_quota)

        part_text.append(POST_PAGE)
        with open((file_names[part]), mode='w', encoding='utf-8') as (f):
            f.write('\n'.join(part_text))


def prepare(file_name):
    s_file = file_name.replace('\\\\', '-').replace('/', '-')
    return s_file