# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: values.py
import platform
CURRENT_ARCH_VERSION = 1
CURRENT_SOFTWARE_VERSION_WIN = 102
CURRENT_SOFTWARE_VERSION_MAC = CURRENT_SOFTWARE_VERSION_WIN
CURRENT_SOFTWARE_VERSION_LINUX = CURRENT_SOFTWARE_VERSION_WIN
LUCENE_VERSION = 2
JRE_VERSION = 2
TRAJM = 'S1'
STEMS = 'S2'
VERSION_MONTH = 'محرم '
VERSION_YEAR = '1448'
CURRENT_SOFTWARE_VERSION_BY_OS = {'win':CURRENT_SOFTWARE_VERSION_WIN, 
 'mac':CURRENT_SOFTWARE_VERSION_MAC, 
 'linux':CURRENT_SOFTWARE_VERSION_LINUX}

def current_os():
    return {'Windows':'win', 
     'Darwin':'mac'}.get(platform.system(), 'linux')


def current_software_version(system_name=None):
    selected_os = system_name or current_os()
    return CURRENT_SOFTWARE_VERSION_BY_OS.get(selected_os, CURRENT_SOFTWARE_VERSION_LINUX)


CURRENT_SOFTWARE_VERSION = current_software_version()

def _os_detail():
    """A broad, human-readable OS label — 'Windows 11', 'macOS 14', 'Ubuntu 22.04'."""
    system = platform.system()
    try:
        if system == 'Windows':
            release, version = platform.win32_ver()[:2]
            try:
                if release == '10':
                    if int(version.split('.')[2]) >= 22000:
                        release = '11'
            except (IndexError, ValueError):
                pass

            return f"Windows {release}".strip()
            if system == 'Darwin':
                parts = platform.mac_ver()[0].split('.')
                major = '.'.join(parts[:2]) if (parts and parts[0] == '10') else (parts[0])
                return f"macOS {major}".strip()
        else:
            try:
                info = platform.freedesktop_os_release()
                name = info.get('NAME', '')
                version_id = info.get('VERSION_ID', '')
                label = f"{name} {version_id}".strip()
                if label:
                    return label
            except (AttributeError, OSError):
                pass

        return f"{system} {platform.release()}".strip()
    except Exception:
        return system or 'unknown'


def _user_agent():
    try:
        arch = platform.machine() or 'unknown'
        return f"desktop/{CURRENT_SOFTWARE_VERSION} ({current_os()}; {_os_detail()}; {arch})"
    except Exception:
        return f"desktop/{CURRENT_SOFTWARE_VERSION}"


USER_AGENT = _user_agent()