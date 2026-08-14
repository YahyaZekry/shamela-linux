# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: dirs.py
import os
from across import Across

def get_directory(path):
    if os.path.isdir(path):
        return True
    try:
        try:
            os.makedirs(path)
        except:
            pass

    finally:
        return

    return os.path.isdir(path)


def pdfPath():
    from settings import Settings
    return Settings.getValue('pdf_folder') or defaultPdfPath()


def extraPdfPath():
    return pdfPath() + '_extra'


def keptCommentsPath(book_id):
    return os.path.join(userPath(), 'kept', f"{book_id}.pk")


def userPath():
    return os.path.join(Across.home_directory, 'database', 'user')


def resultsFolder():
    return os.path.join(userPath(), 'results')


def defaultPdfPath():
    return os.path.join(Across.home_directory, 'pdf')


def coverDbPath():
    return os.path.join(Across.home_directory, 'database', 'cover.db')


def serviceDbPath(service_name):
    return os.path.join(Across.home_directory, 'database', 'service', f"{service_name}.db")


def bookPath(book_id):
    return os.path.join(Across.home_directory, 'database', 'book', str(book_id % 1000).zfill(3), f"{book_id}.db")


def masterDbPath():
    return os.path.join(Across.home_directory, 'database', 'master.db')


def userDbPath():
    return os.path.join(userPath(), 'data.db')


def emptyLastSessionFlag():
    return os.path.join(userPath(), 'last_session.db')


def hintsCachePath():
    return os.path.join(userPath(), 'hints.pk')


def updateDir():
    return os.path.join(Across.home_directory, 'database', 'update')


def isWritable(path):
    absent = not os.path.isdir(path)
    if absent:
        try:
            os.makedirs(path)
        except:
            pass

        if not os.path.isdir(path):
            return
    try:
        tmpFile = 'write_tester'
        count = 0
        filename = os.path.join(path, tmpFile)
        while os.path.exists(filename):
            filename = f"{os.path.join(path, tmpFile)}.{count}"
            count += 1

        f = open(filename, 'w')
        f.close()
        os.remove(filename)
        if absent:
            os.rmdir(path)
        return True
    except:
        pass

    if absent:
        os.rmdir(path)


def getPaths():
    """
    :return:
    0    ok
    1    can not prepare directories
    2    incomplete folders   # obsolete now
    3    shamela 3 folder
    """
    from dbmanager import CoreDb, UserDb, CoverDb, Services
    Across.writable = isWritable(os.path.join(Across.home_directory, 'database'))
    if not get_directory(os.path.join(Across.home_directory, 'database', 'service')):
        return 1
    else:
        if not get_directory(userPath()):
            return 1
        else:
            if not get_directory(os.path.join(Across.home_directory, 'database', 'user', 'results')):
                return 1
            else:
                if not get_directory(os.path.join(Across.home_directory, 'database', 'user', 'kept')):
                    return 1
                else:
                    if not get_directory(os.path.join(Across.home_directory, 'database', 'book')):
                        return 1
                    else:
                        if not get_directory(os.path.join(Across.home_directory, 'database', 'update')):
                            return 1
                        return get_directory(os.path.join(Across.home_directory, 'database', 'update', 'book')) or 1
                    if os.path.isdir(os.path.join(Across.home_directory, 'Files')):
                        return 3
                    return CoverDb().isOk() or 4
                return UserDb().isOk() or 4
            return CoreDb().isOk() or 4
        return Services.isOk() or 4
    return 0