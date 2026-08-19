#!/usr/bin/env python3
"""Parse and rebuild PyInstaller 5.x CArchive (exe) + embedded PYZ.

Verified against pyimod01_archive.pyc / pyimod02_importers.pyc from the
app's bootloader and PyInstaller v5.13.2 archive/writers.py.
"""
import marshal
import struct
import sys
import zlib

COOKIE_FORMAT = '!8sIIii64s'
COOKIE_LENGTH = struct.calcsize(COOKIE_FORMAT)
TOC_ENTRY_FORMAT = '!iIIIBB'
TOC_ENTRY_LENGTH = struct.calcsize(TOC_ENTRY_FORMAT)
CARCHIVE_MAGIC = b'MEI\014\013\012\013\016'

PYZ_MAGIC = b'PYZ\x00'
PYZ_HEADER = 17  # 4 magic + 4 pymagic + 4 toc_offset + 1 encrypt + 4 reserved
PYZ_ITEM_MODULE = 0
PYZ_ITEM_PKG = 1
PYZ_ITEM_DATA = 2
PYZ_ITEM_NSPKG = 3


class CArchive:
    def __init__(self, data):
        self.data = data
        self.cookie_pos = data.rfind(CARCHIVE_MAGIC)
        if self.cookie_pos < 0:
            raise ValueError('no CArchive cookie')
        (magic, archive_length, toc_offset, toc_length, pyvers, pylib) = struct.unpack_from(
            COOKIE_FORMAT, data, self.cookie_pos)
        self.cookie = dict(magic=magic, archive_length=archive_length,
                           toc_offset=toc_offset, toc_length=toc_length,
                           pyvers=pyvers, pylib=pylib)
        self.archive_start = self.cookie_pos - archive_length
        self.toc_pos = self.cookie_pos - toc_length
        self.entries = self._parse_toc()

    def _parse_toc(self):
        entries = []
        o = self.toc_pos
        toc_end = o + self.cookie['toc_length']
        while o < toc_end:
            entry_len, data_offset, comp_len, data_len, compress, typecode = \
                struct.unpack_from(TOC_ENTRY_FORMAT, self.data, o)
            name = self.data[o + TOC_ENTRY_LENGTH:o + entry_len].split(b'\x00', 1)[0].decode('utf-8')
            entries.append(dict(name=name, typecode=chr(typecode), compress=compress,
                                data_offset=data_offset, comp_len=comp_len,
                                data_len=data_len, entry_len=entry_len))
            o += entry_len
        return entries

    def entry_bytes(self, e):
        base = self.archive_start + 88  # data region base (fixed 88-byte blob header)
        return self.data[base + e['data_offset']:
                         base + e['data_offset'] + e['comp_len']]


class PYZ:
    def __init__(self, data):
        self.data = data
        assert data[:4] == PYZ_MAGIC
        self.pymagic = data[4:8]
        toc_offset = struct.unpack('!i', data[8:12])[0]
        self.encrypted = data[12]
        self.toc = dict(marshal.loads(data[toc_offset:]))
        self._load_all()

    def _load_all(self):
        self.blobs = {}
        for name, (typecode, offset, length) in self.toc.items():
            raw = self.data[offset:offset + length]
            plain = zlib.decompress(raw) if not self.encrypted else raw
            self.blobs[name] = (typecode, plain)

    def module(self, name):
        typecode, plain = self.blobs[name]
        return marshal.loads(plain)

    def add_module(self, name, code_object):
        self.blobs[name] = (PYZ_ITEM_MODULE, marshal.dumps(code_object))

    def replace_code(self, name, code_object):
        typecode, _ = self.blobs[name]
        self.blobs[name] = (typecode, marshal.dumps(code_object))

    def to_bytes(self):
        out = bytearray()
        out += b'\x00' * PYZ_HEADER
        toc = []
        for name, (typecode, plain) in self.blobs.items():
            obj = zlib.compress(plain, 6)
            toc.append((name, (typecode, len(out), len(obj))))
            out += obj
        toc_offset = len(out)
        out += marshal.dumps(toc)
        out[0:4] = PYZ_MAGIC
        out[4:8] = self.pymagic
        out[8:12] = struct.pack('!i', toc_offset)
        out[12] = 1 if self.encrypted else 0
        return bytes(out)


def rebuild_exe(exe_data, pyz_bytes=None):
    """Rebuild CArchive; replace PYZ entry blob with pyz_bytes if given.
    Other entries are copied byte-for-byte with their original flags.
    Returns the new exe bytes."""
    ca = CArchive(exe_data)
    prefix = exe_data[:ca.archive_start]
    blob = bytearray()
    toc = []
    for e in ca.entries:
        if e['name'] == 'PYZ-00.pyz' and pyz_bytes is not None:
            payload = pyz_bytes
            data_len = len(payload)
        else:
            payload = ca.entry_bytes(e)
            data_len = e['data_len']
        compress = e['compress']
        if compress:
            stored = zlib.compress(payload, 9)
        else:
            stored = payload
        toc.append((len(blob), len(stored), data_len, compress, e['typecode'], e['name']))
        blob += stored
    serialized = _serialize_toc(toc)
    toc_offset = len(blob)
    toc_length = len(serialized)
    archive_length = toc_offset + toc_length + COOKIE_LENGTH
    cookie = struct.pack(COOKIE_FORMAT, CARCHIVE_MAGIC, archive_length, toc_offset,
                         toc_length, ca.cookie['pyvers'], ca.cookie['pylib'])
    return bytes(prefix) + bytes(blob) + serialized + cookie


def _serialize_toc(toc):
    parts = []
    for data_offset, comp_len, data_len, compress, typecode, name in toc:
        nb = name.encode('utf-8')
        name_len = len(nb) + 1
        entry_len = TOC_ENTRY_LENGTH + name_len
        if entry_len % 16:
            name_len += 16 - (entry_len % 16)
        parts.append(struct.pack(TOC_ENTRY_FORMAT + '%ds' % name_len,
                                 TOC_ENTRY_LENGTH + name_len, data_offset, comp_len,
                                 data_len, compress, ord(typecode), nb))
    return b''.join(parts)


def main():
    exe = sys.argv[1]
    data = open(exe, 'rb').read()
    ca = CArchive(data)
    print('archive start %d cookie %d pyvers %d pylib %r' % (
        ca.archive_start, ca.cookie_pos, ca.cookie['pyvers'], ca.cookie['pylib']))
    for e in ca.entries:
        print('%-20s type=%s comp=%d off=%d clen=%d dlen=%d' % (
            e['name'], e['typecode'], e['compress'], e['data_offset'],
            e['comp_len'], e['data_len']))
    pyz_entry = next(e for e in ca.entries if e['name'] == 'PYZ-00.pyz')
    pyz = PYZ(ca.entry_bytes(pyz_entry))
    print('PYZ modules: %d' % len(pyz.toc))
    if len(sys.argv) > 2 and sys.argv[2] == 'list':
        for name in sorted(pyz.toc):
            print('  %s (type %d)' % (name, pyz.toc[name][0]))


if __name__ == '__main__':
    main()