#!/usr/bin/env python3
"""Inject a patch into the Shamela exe by replacing the embedded PYZ in place.

Run under the venv Python 3.7.12 (bytecode-compatible with the frozen app).

The embedded PYZ occupies a fixed byte region inside the exe:
  base = archive_start + 88
  pyz_region = exe[base + pyz_entry.data_offset : base + pyz_entry.data_offset + comp_len]

The rebuilt PYZ (same logical module set, plus 'shamela_patch', with the
'across' module surgically altered) is padded to the exact same length and
spliced over that region. Everything else in the file stays byte-identical,
so the bootloader's cookie/TOC/pydata resolution is untouched.
"""
import marshal
import struct
import sys
import types
import zlib

sys.path.insert(0, '/tmp/opencode')
from pyz_tool import CArchive, PYZ  # noqa: E402
from pyz_tool import PYZ_MAGIC  # noqa: E402

EXE_IN = '/home/monst3r/Apps/shamela/app/linux/64/bin/shamela'
EXE_OUT = '/home/monst3r/Apps/shamela/app/linux/64/bin/shamela.new'
PATCH_SRC = '/tmp/opencode/shamela_patch.py'

LOAD_CONST = 100
POP_TOP = 1
CALL_FUNCTION = 131
IMPORT_NAME = 108
LOAD_ATTR = 106


def find_append(tup, pred, val):
    tup = tuple(tup)
    for i, x in enumerate(tup):
        if pred(x):
            return i, tup
    return len(tup), tup + (val,)


def shift_lnotab(lnotab, shift):
    out = bytearray()
    carry = shift
    i = 0
    while i + 1 < len(lnotab):
        delta = lnotab[i]
        line = lnotab[i + 1]
        if carry:
            delta += carry
            if delta > 255:
                carry = delta - 255
                delta = 255
            else:
                carry = 0
        out += bytes((delta, line))
        i += 2
    if i < len(lnotab):
        out += lnotab[i:i + 1]
    if carry:
        out += bytes((carry, 0))
    return bytes(out)


def prepend_import_call(code):
    consts = tuple(code.co_consts)
    names = tuple(code.co_names)
    none_i, consts = find_append(consts, lambda x: x is None, None)
    zero_i, consts = find_append(consts, lambda x: isinstance(x, int) and x == 0, 0)
    patch_i, names = find_append(names, lambda x: x == 'shamela_patch', 'shamela_patch')
    install_i, names = find_append(names, lambda x: x == 'install', 'install')

    ops = ((LOAD_CONST, zero_i), (LOAD_CONST, none_i), (IMPORT_NAME, patch_i),
           (LOAD_ATTR, install_i), (CALL_FUNCTION, 0), (POP_TOP, 0))
    prefix = bytes(v for pair in ops for v in pair)

    new_code = prefix + code.co_code
    new_lnotab = shift_lnotab(code.co_lnotab, len(prefix))

    return types.CodeType(
        code.co_argcount, code.co_kwonlyargcount, code.co_nlocals,
        max(code.co_stacksize, 2) + 2, code.co_flags, new_code, consts, names,
        code.co_varnames, code.co_filename, code.co_name, code.co_firstlineno,
        new_lnotab, code.co_freevars, code.co_cellvars)


def main():
    exe_data = open(EXE_IN, 'rb').read()
    ca = CArchive(exe_data)
    pyz_entry = next(e for e in ca.entries if e['name'] == 'PYZ-00.pyz')
    pyz = PYZ(ca.entry_bytes(pyz_entry))
    orig_len = pyz_entry['comp_len']
    print('PYZ region: +88 base %d, entry data_offset %d, length %d' % (
        ca.archive_start, pyz_entry['data_offset'], orig_len))

    across = pyz.module('across')
    print('across: names=%d consts=%d code=%dB (0x%x len)' % (
        len(across.co_names), len(across.co_consts), len(across.co_code),
        across.co_firstlineno))
    new_across = prepend_import_call(across)
    pyz.replace_code('across', new_across)
    print('across patched: code %d -> %d bytes' % (
        len(across.co_code), len(new_across.co_code)))

    src = open(PATCH_SRC, 'r', encoding='utf-8').read()
    patch_code = compile(src, 'shamela_patch.py', 'exec')
    pyz.add_module('shamela_patch', patch_code)
    print('shamela_patch module added (%d compile consts)' % len(patch_code.co_consts))

    new_pyz = _rebuild_compact(pyz)
    delta = len(new_pyz) - orig_len
    print('new PYZ %d bytes (delta %+d)' % (len(new_pyz), delta))
    if delta > 0:
        raise SystemExit('PYZ too big; patch source must shrink by %d bytes' % delta)
    new_pyz = new_pyz + b'\x00' * (-delta)

    base = ca.archive_start + 88
    start = base + pyz_entry['data_offset']
    patched = bytearray(exe_data)
    patched[start:start + orig_len] = new_pyz
    open(EXE_OUT, 'wb').write(bytes(patched))
    print('spliced in-place; wrote %s (%d bytes)' % (EXE_OUT, len(patched)))


def _rebuild_compact(pyz):
    out = bytearray(b'\x00' * 17)
    toc = []
    for name, (typecode, plain) in pyz.blobs.items():
        obj = zlib.compress(plain, 9)
        toc.append((name, (typecode, len(out), len(obj))))
        out += obj
    toc_offset = len(out)
    out += marshal.dumps(toc)
    out[0:4] = PYZ_MAGIC
    out[4:8] = pyz.pymagic
    out[8:12] = struct.pack('!i', toc_offset)
    out[12] = 1 if pyz.encrypted else 0
    return bytes(out)


if __name__ == '__main__':
    main()