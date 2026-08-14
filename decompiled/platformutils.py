# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: platformutils.py
import os, sys
from qtpy.QtCore import QStandardPaths
from across import Across

def _standard_location(location):
    try:
        path = QStandardPaths.writableLocation(location)
        if path:
            return path
    except Exception:
        pass


def home_dir():
    return os.path.expanduser('~')


def desktop_dir():
    return _standard_location(QStandardPaths.DesktopLocation) or os.path.join(home_dir(), 'Desktop')


def executable_name():
    if Across.os == 'win':
        return 'shamela.exe'
    if Across.os == 'mac':
        return 'المكتبة الشاملة'
    return 'shamela'


def executable_path():
    return os.path.join(Across.bin_directory, executable_name())


def launcher_path():
    if Across.os == 'mac':
        return os.path.join('/Applications', 'المكتبة الشاملة.app')
    if Across.os == 'win':
        return os.path.join(Across.home_directory, 'shamela.exe')
    return os.path.join(Across.home_directory, 'shamela.AppImage')


def arch_bin_directory(arch):
    return os.path.join(Across.home_directory, 'app', Across.os, arch, 'bin')


def arch_executable_path(arch):
    return os.path.join(arch_bin_directory(arch), executable_name())


def arch_version_manifest_path(arch):
    return os.path.join(arch_bin_directory(arch), 'version.manifest')


def arch_runtime_ready(arch):
    executable = arch_executable_path(arch)
    if not os.path.isfile(executable):
        return False
    return os.path.isfile(arch_version_manifest_path(arch))


def menu_shortcut_supported():
    return Across.os != 'mac'


def shortcut_target():
    if Across.os == 'mac':
        if getattr(sys, 'frozen', False):
            return launcher_path()
    target_arch = None
    for arch in [Across.system_arch, Across.running_arch]:
        if not arch:
            continue
        try:
            if arch_runtime_ready(arch):
                target_arch = arch
                break
        except Exception:
            pass

    if target_arch:
        target_path = arch_executable_path(target_arch)
        if os.path.exists(target_path):
            return target_path
    return executable_path()