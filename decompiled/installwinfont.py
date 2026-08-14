# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: installwinfont.py
import ctypes, os
from ctypes import wintypes
try:
    import winreg
except ImportError:
    import _winreg as winreg

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
FONTS_REG_PATH = 'Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts'
HWND_BROADCAST = 65535
SMTO_ABORTIFHUNG = 2
WM_FONTCHANGE = 29
GFRI_DESCRIPTION = 1
GFRI_ISTRUETYPE = 3
if not hasattr(wintypes, 'LPDWORD'):
    wintypes.LPDWORD = ctypes.POINTER(wintypes.DWORD)
user32.SendMessageTimeoutW.restype = wintypes.LPVOID
user32.SendMessageTimeoutW.argtypes = (
 wintypes.HWND,
 wintypes.UINT,
 wintypes.LPVOID,
 wintypes.LPVOID,
 wintypes.UINT,
 wintypes.UINT,
 wintypes.LPVOID)
gdi32.AddFontResourceW.argtypes = (
 wintypes.LPCWSTR,)
gdi32.GetFontResourceInfoW.argtypes = (
 wintypes.LPCWSTR,
 wintypes.LPDWORD,
 wintypes.LPVOID,
 wintypes.DWORD)

def notify():
    user32.SendMessageTimeoutW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0, SMTO_ABORTIFHUNG, 1000, None)


def installWinFont(dst_path):
    try:
        if not gdi32.AddFontResourceW(dst_path):
            return
        filename = os.path.basename(dst_path)
        fontname = os.path.splitext(filename)[0]
        cb = wintypes.DWORD()
        if gdi32.GetFontResourceInfoW(filename, ctypes.byref(cb), None, GFRI_DESCRIPTION):
            buf = (ctypes.c_wchar * cb.value)()
            if gdi32.GetFontResourceInfoW(filename, ctypes.byref(cb), buf, GFRI_DESCRIPTION):
                fontname = buf.value
        is_truetype = wintypes.BOOL()
        cb.value = ctypes.sizeof(is_truetype)
        gdi32.GetFontResourceInfoW(filename, ctypes.byref(cb), ctypes.byref(is_truetype), GFRI_ISTRUETYPE)
        if is_truetype:
            fontname += ' (TrueType)'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, FONTS_REG_PATH, 0, winreg.KEY_SET_VALUE) as (key):
            winreg.SetValueEx(key, fontname, 0, winreg.REG_SZ, dst_path)
    except:
        return