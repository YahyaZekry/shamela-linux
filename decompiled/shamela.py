# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: shamela.py
import shutil, os, subprocess, sys, platform, ctypes, zipfile, zlib
from across import Across
from platformutils import arch_executable_path, arch_runtime_ready, launcher_path
from values import CURRENT_SOFTWARE_VERSION
STAGED_LAUNCHER_NAME = 'staged_launcher'

def realpath(path):
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def setup_qt_dpi():
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
    os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'PassThrough'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    os.environ['QT_USE_HIGH_DPI_PIXMAPS'] = '1'
    if Across.os == 'win':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass

    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import Qt
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass

    if hasattr(Qt, 'ApplicationAttribute'):
        if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except:
        pass


def is_32_bit_runtime():
    return Across.running_arch == '32' or sys.maxsize <= 4294967296


def jvm_xmx_mb():
    if not is_32_bit_runtime():
        return
    for xmx_mb in (768, 512, 384, 256):
        if _can_reserve_contiguous_mb(xmx_mb + 128):
            return xmx_mb


def _can_reserve_contiguous_mb(size_mb):
    if Across.os != 'win':
        return True
    MEM_RESERVE, MEM_RELEASE, PAGE_NOACCESS = (8192, 32768, 1)
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.VirtualAlloc.restype = ctypes.c_void_p
        kernel32.VirtualAlloc.argtypes = [
         ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
        kernel32.VirtualFree.argtypes = [
         ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong]
        address = kernel32.VirtualAlloc(None, size_mb * 1024 * 1024, MEM_RESERVE, PAGE_NOACCESS)
        if not address:
            return False
        kernel32.VirtualFree(address, 0, MEM_RELEASE)
        return True
    except Exception:
        return False


def jvm_has_vector_module():
    if is_32_bit_runtime():
        return False
    try:
        release_file = os.path.join(os.environ['JAVA_HOME'], 'release')
        with open(release_file, encoding='utf-8', errors='ignore') as (f):
            for line in f:
                if line.startswith('MODULES'):
                    return 'jdk.incubator.vector' in line

    except Exception:
        pass

    return False


def start_jvm(jpype, classpath):
    args = []
    xmx_mb = jvm_xmx_mb()
    if xmx_mb:
        args.append(f"-Xmx{xmx_mb}m")
    if Across.os == 'win':
        args.append('-XX:+PerfDisableSharedMem')
    if jvm_has_vector_module():
        args.append('--add-modules=jdk.incubator.vector')
    (jpype.startJVM)(*args, **{'classpath': classpath})


def normalize_arch(machine):
    machine = (machine or '').strip().lower()
    aliases = {
     'x86': "'32'", 
     'i386': "'32'", 
     'i486': "'32'", 
     'i586': "'32'", 
     'i686': "'32'", 
     'win32': "'32'", 
     'amd64': "'64'", 
     'x86_64': "'64'", 
     'x64': "'64'", 
     'arm64': "'arm64'", 
     'aarch64': "'arm64'"}
    return aliases.get(machine)


WINDOWS_IMAGE_MACHINE_ARCH = {332:'32', 
 34404:'64', 
 43620:'arm64'}
WINDOWS_PROCESSOR_ARCH = {0:'32', 
 9:'64', 
 12:'arm64'}

def detect_windows_arch_from_iswow64process2():
    """Use the Win10+ API when present, without importing it by name.

    Win7 does not export IsWow64Process2. Looking it up with GetProcAddress
    keeps Win7 on the fallback path while still allowing accurate ARM64
    detection on newer Windows.
    """
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        get_module_handle = kernel32.GetModuleHandleW
        get_module_handle.argtypes = [ctypes.c_wchar_p]
        get_module_handle.restype = ctypes.c_void_p
        get_proc_address = kernel32.GetProcAddress
        get_proc_address.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        get_proc_address.restype = ctypes.c_void_p
        kernel32_handle = get_module_handle('kernel32.dll')
        if not kernel32_handle:
            return
        proc_address = get_proc_address(kernel32_handle, b'IsWow64Process2')
        if not proc_address:
            return
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = ctypes.c_void_p
        is_wow64_process2 = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ushort), ctypes.POINTER(ctypes.c_ushort))(proc_address)
        process_machine = ctypes.c_ushort()
        native_machine = ctypes.c_ushort()
        if is_wow64_process2(get_current_process(), ctypes.byref(process_machine), ctypes.byref(native_machine)):
            return WINDOWS_IMAGE_MACHINE_ARCH.get(native_machine.value) or WINDOWS_IMAGE_MACHINE_ARCH.get(process_machine.value)
    except:
        pass


def detect_windows_arch_from_system_info():

    class ProcessorInfo(ctypes.Structure):
        _fields_ = [('wProcessorArchitecture', ctypes.c_ushort),
         (
          'wReserved', ctypes.c_ushort)]

    class SystemInfoUnion(ctypes.Union):
        _fields_ = [
         (
          'dwOemId', ctypes.c_ulong),
         (
          'processorInfo', ProcessorInfo)]

    class SystemInfo(ctypes.Structure):
        _fields_ = [
         (
          'u', SystemInfoUnion),
         (
          'dwPageSize', ctypes.c_ulong),
         (
          'lpMinimumApplicationAddress', ctypes.c_void_p),
         (
          'lpMaximumApplicationAddress', ctypes.c_void_p),
         (
          'dwActiveProcessorMask', ctypes.c_size_t),
         (
          'dwNumberOfProcessors', ctypes.c_ulong),
         (
          'dwProcessorType', ctypes.c_ulong),
         (
          'dwAllocationGranularity', ctypes.c_ulong),
         (
          'wProcessorLevel', ctypes.c_ushort),
         (
          'wProcessorRevision', ctypes.c_ushort)]

    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        system_info = SystemInfo()
        try:
            get_native_system_info = kernel32.GetNativeSystemInfo
            get_native_system_info.argtypes = [ctypes.POINTER(SystemInfo)]
            get_native_system_info.restype = None
            get_native_system_info(ctypes.byref(system_info))
        except:
            get_system_info = kernel32.GetSystemInfo
            get_system_info.argtypes = [ctypes.POINTER(SystemInfo)]
            get_system_info.restype = None
            get_system_info(ctypes.byref(system_info))

        return WINDOWS_PROCESSOR_ARCH.get(system_info.u.processorInfo.wProcessorArchitecture)
    except:
        pass


def launched_arch():
    if not Across.bin_directory:
        return
    arch = os.path.basename(os.path.realpath(os.path.join(Across.bin_directory, os.pardir)))
    if arch:
        return arch


def detect_running_arch--- This code section failed: ---

 L. 337         0  LOAD_GLOBAL              normalize_arch
                2  LOAD_GLOBAL              launched_arch
                4  CALL_FUNCTION_0       0  '0 positional arguments'
                6  CALL_FUNCTION_1       1  '1 positional argument'
                8  JUMP_IF_TRUE_OR_POP    26  'to 26'
               10  LOAD_GLOBAL              sys
               12  LOAD_ATTR                maxsize
               14  LOAD_CONST               4294967296
               16  COMPARE_OP               <=
               18  POP_JUMP_IF_FALSE    24  'to 24'
               20  LOAD_STR                 '32'
               22  RETURN_VALUE     
             24_0  COME_FROM            18  '18'
               24  LOAD_STR                 '64'
             26_0  COME_FROM             8  '8'
               26  RETURN_VALUE     
               -1  RETURN_LAST      

Parse error at or near `None' instruction at offset -1


def detect_windows_native_arch():
    if Across.os != 'win':
        return
    return detect_windows_arch_from_iswow64process2() or normalize_arch(os.environ.get('PROCESSOR_ARCHITEW6432')) or detect_windows_arch_from_system_info() or normalize_arch(os.environ.get('PROCESSOR_ARCHITECTURE'))


def detect_system_arch():
    if Across.os == 'win':
        arch = detect_windows_native_arch()
        if arch:
            return arch
    arch = normalize_arch(platform.machine())
    if Across.os == 'mac':
        if arch == '64':
            try:
                arm64_capable = subprocess.check_output(['sysctl', '-in', 'hw.optional.arm64'], stderr=(subprocess.DEVNULL)).decode().strip()
                if arm64_capable == '1':
                    return 'arm64'
            except:
                pass

    return arch or detect_running_arch()


def settle_system_arch(system_arch):
    settled = system_arch or detect_running_arch()
    if settled == 'arm64':
        no_arm64_flag = os.path.join(getattr(Across, 'bin_directory', ''), 'no_arm64')
        if no_arm64_flag:
            if os.path.isfile(no_arm64_flag):
                settled = '64'
    return settled


def top_ver_info(folder):
    if not os.path.isdir(folder):
        return (None, None)
    else:
        valid_versions = []
        subfolders = [name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name))]
        for subfolder in subfolders:
            if subfolder.isdigit() and os.path.isfile(os.path.join(folder, subfolder, 'done.manifest')):
                valid_versions.append(int(subfolder))

        return valid_versions or (None, None)
    version = max(valid_versions)
    return (os.path.join(folder, f"{version}"), version)


def show_error_dialog(message):
    """Show an error dialog using native platform APIs only"""
    title = 'المكتبة الشاملة'
    if Across.os == 'mac':
        try:
            safe_message = message.replace('"', '\\"')
            subprocess.run([
             'osascript', '-e',
             f'display dialog "{safe_message}" with title "{title}" buttons {{"OK"}} default button "OK" with icon stop'],
              check=True)
            return
        except:
            pass

    else:
        if Across.os == 'linux':
            try:
                subprocess.run([
                 "'notify-send'", "'-u'", "'critical'", 
                 "'-i'", 
                 "'dialog-error'", 
                 'title', 
                 'message'],
                  check=True)
                return
            except:
                pass

            try:
                subprocess.run([
                 'wall'],
                  input=f"{title}: {message}",
                  text=True,
                  check=True)
                return
            except:
                pass

        else:
            if Across.os == 'win':
                if ctypes:
                    try:
                        MessageBox = ctypes.windll.user32.MessageBoxW
                        MessageBox(None, message, title, 16)
                        return
                    except:
                        pass

    print(f"ERROR - {title}: {message}")
    sys.stderr.write(f"ERROR - {title}: {message}\n")
    sys.stderr.flush()


def launcher_exists(path):
    if not path:
        pass
    if Across.os == 'mac':
        return os.path.isdir(path)
    return os.path.isfile(path)


def restart_via_launcher():
    """Schedule the launcher to be spawned after the JVM has fully shut down.

    atexit handlers fire in LIFO order.  A sentinel was registered in __main__
    *before* jpype was imported, so it sits below jpype's own cleanup hook in
    the stack and fires after the JVM tears down and releases all file handles.
    We store our callback there instead of registering a new atexit entry
    (which would be above jpype in LIFO and fire while the JVM is still up).

    Returns True when the callback was successfully registered.
    """
    launcher_exe = launcher_path()
    if not launcher_exists(launcher_exe):
        if Across.os == 'win':
            launcher_exe = legacy_launcher_path()
    else:
        return launcher_exists(launcher_exe) or False
    import sys as _sys
    main_module = _sys.modules.get('__main__')
    container = getattr(main_module, '_post_jvm_callback', None)

    def _launch():
        try:
            if Across.os == 'win':
                subprocess.Popen([
                 launcher_exe],
                  cwd=(os.path.dirname(launcher_exe) or None),
                  creationflags=(subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW),
                  close_fds=True)
            else:
                subprocess.Popen((['/usr/bin/open', '-n', launcher_exe] if Across.os == 'mac' else [launcher_exe]),
                  cwd=(None if Across.os == 'mac' else os.path.dirname(launcher_exe) or None),
                  start_new_session=True,
                  close_fds=True)
        except Exception:
            pass

    if container is not None:
        container[0] = _launch
    else:
        import atexit
        atexit.register(_launch)
    return True


def restart_direct():
    """Schedule the app to be re-spawned after the JVM shuts down.

    Uses the same _post_jvm_callback sentinel as restart_via_launcher() so the
    JVM fully tears down (releasing all file handles) before the new process is
    spawned.  No launcher involved — spawns the frozen executable directly, or
    re-runs the Python script when not frozen.
    """
    import sys as _sys
    exe = os.path.realpath(_sys.executable)
    if getattr(_sys, 'frozen', False):
        args = [exe] + _sys.argv[1:]
    else:
        args = [exe] + _sys.argv
    cwd = os.path.dirname(exe) or None
    main_module = _sys.modules.get('__main__')
    container = getattr(main_module, '_post_jvm_callback', None)

    def _launch():
        try:
            if Across.os == 'win':
                subprocess.Popen(args,
                  cwd=cwd,
                  creationflags=(subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW),
                  close_fds=True)
            else:
                subprocess.Popen(args,
                  cwd=cwd,
                  start_new_session=True,
                  close_fds=True)
        except Exception:
            pass

    if container is not None:
        container[0] = _launch
    else:
        import atexit
        atexit.register(_launch)


def remove_path(path):
    return path and os.path.lexists(path) or None
    try:
        if os.path.isdir(path):
            os.path.islink(path) or shutil.rmtree(path, ignore_errors=True)
        else:
            os.unlink(path)
    except:
        pass


def _file_crc32(path):
    """CRC-32 of a file on disk — matches the CRC stored in each ZIP entry."""
    crc = 0
    try:
        with open(path, 'rb') as (f):
            for chunk in iter((lambda: f.read(65536)), b''):
                crc = zlib.crc32(chunk, crc)

        return crc & 4294967295
    except:
        return


def _install_win_launcher_from_zip(zf):
    try:
        entry = zf.getinfo('shamela.exe')
    except KeyError:
        return False
    else:
        target_path = launcher_path()
        os.path.isfile(target_path) and _file_crc32(target_path) == entry.CRC or os.makedirs((os.path.dirname(target_path)), exist_ok=True)
        temp_path = f"{target_path}.__new"
        remove_path(temp_path)
        with zf.open(entry) as (src):
            with open(temp_path, 'wb') as (dst):
                shutil.copyfileobj(src, dst)
        os.replace(temp_path, target_path)
    return True


def legacy_launcher_path():
    return os.path.join(Across.home_directory, 'launcher.exe')


def _cleanup_legacy_launcher():
    if Across.os != 'win':
        return
    if os.path.isfile(launcher_path()):
        legacy_launcher = legacy_launcher_path()
        if os.path.isfile(legacy_launcher):
            try:
                os.remove(legacy_launcher)
            except Exception:
                pass


def _install_linux_launcher_from_zip(zf):
    try:
        entry = zf.getinfo('shamela.AppImage')
    except KeyError:
        return False
    else:
        target_path = launcher_path()
        if os.path.isfile(target_path):
            if _file_crc32(target_path) == entry.CRC:
                return True
        os.makedirs((os.path.dirname(target_path)), exist_ok=True)
        temp_path = f"{target_path}.__new"
        remove_path(temp_path)
        with zf.open(entry) as (src):
            with open(temp_path, 'wb') as (dst):
                shutil.copyfileobj(src, dst)
        try:
            os.chmod(temp_path, os.stat(temp_path).st_mode | 73)
        except:
            pass

        os.replace(temp_path, target_path)
        return True


def process_staged_launcher_container(container_path):
    if Across.os == 'mac':
        return False
    success = False
    try:
        if os.path.isfile(container_path):
            if zipfile.is_zipfile(container_path):
                with zipfile.ZipFile(container_path) as (zf):
                    if Across.os == 'win':
                        success = bool(_install_win_launcher_from_zip(zf))
                    else:
                        if Across.os == 'linux':
                            success = bool(_install_linux_launcher_from_zip(zf))
                if success:
                    if Across.os != 'win':
                        remove_path(container_path)
    except:
        success = False

    _cleanup_legacy_launcher()
    return success


def process_staged_launcher():
    if Across.os == 'mac':
        return False
    candidate = realpath(os.path.join(Across.bin_directory, STAGED_LAUNCHER_NAME))
    exists = os.path.isfile(candidate)
    process_staged_launcher_container(candidate)
    return exists


def handoff_to_system_arch():
    if not getattr(sys, 'frozen', False):
        return
        target_arch = getattr(Across, 'system_arch', None)
        if not target_arch or target_arch == Across.running_arch:
            return
        if not arch_runtime_ready(target_arch):
            return
        target_executable = arch_executable_path(target_arch)
        current_executable = os.path.realpath(sys.executable)
        if os.path.realpath(target_executable) == current_executable:
            return
        if Across.os == 'win':
            try:
                from customs import shortcuts
                shortcuts()
            except:
                pass

    else:
        try:
            subprocess.Popen(([target_executable] + sys.argv[1:]), cwd=(os.path.dirname(target_executable)))
            sys.exit()
        except:
            pass


if __name__ == '__main__':
    Across.os = {'Windows':'win', 
     'Darwin':'mac'}.get(platform.system(), 'linux')
    if getattr(sys, 'frozen', False):
        Across.bin_directory = realpath(os.path.dirname(sys.executable))
    else:
        Across.bin_directory = realpath(os.path.dirname(__file__))
    Across.home_directory = realpath(os.path.join(Across.bin_directory, os.pardir, os.pardir, os.pardir, os.pardir))
    if Across.os == 'win':
        if not Across.home_directory.isascii():
            show_error_dialog('فضلا، قم بنقل البرنامج إلى مسار بحروف إنجليزية، مثلا\nC:\\shamela')
            sys.exit()
    Across.running_arch = detect_running_arch()
    Across.system_arch = settle_system_arch(detect_system_arch())
    handoff_to_system_arch()
    REDOWNLOAD = 'بعض الملفات التشغيلية الضرورية ناقصة\nفضلا أعد تحميل البرنامج'
    update_dir = realpath(os.path.join(Across.bin_directory, os.pardir, 'update'))
    manifest_path = os.path.join(update_dir, 'version.manifest')
    if os.path.isfile(manifest_path):
        marker_path = os.path.join(update_dir, '.launcher_attempted')
        if os.path.isfile(marker_path):
            sys.exit()
        try:
            with open(marker_path, 'w'):
                pass
        except Exception:
            pass

        process_staged_launcher_container(os.path.join(update_dir, STAGED_LAUNCHER_NAME))
        launcher_exe = launcher_path()
        if launcher_exists(launcher_exe):
            subprocess.Popen((['/usr/bin/open', '-n', launcher_exe] if Across.os == 'mac' else [launcher_exe]),
              cwd=(None if Across.os == 'mac' else os.path.dirname(launcher_exe) or None))
        sys.exit()
    else:
        try:
            os.remove(os.path.join(Across.bin_directory, '.launcher_attempted'))
        except Exception:
            pass

        process_staged_launcher()
        jre_path, _ = top_ver_info(realpath(os.path.join(Across.bin_directory, os.pardir, 'jre')))
        lucene_path, Across.lucene_version = top_ver_info(os.path.join(Across.home_directory, 'app', 'lucene'))
        jre_path and lucene_path or show_error_dialog(REDOWNLOAD)
        sys.exit()
    jre = os.path.join(jre_path, 'bin')
    jre_server = os.path.join(jre_path, 'bin' if Across.os == 'win' else 'lib', 'server')
    os.environ['JAVA_HOME'] = jre_path
    new_paths = f"{jre}{os.pathsep}{jre_server}"
    os.environ['PATH'] = new_paths + os.pathsep + os.environ['PATH']
    import atexit as _atexit
    _post_jvm_callback = [
     None]

    def _post_jvm_sentinel():
        cb = _post_jvm_callback[0]
        if cb is not None:
            cb()


    _atexit.register(_post_jvm_sentinel)
    import jpype
    from jpype.types import JClass
    classpath = [
     f"{lucene_path}/*"]
    start_jvm(jpype, classpath)
    JClass('org.apache.lucene.search.IndexSearcher').setMaxClauseCount(JClass('java.lang.Integer').MAX_VALUE)
    setup_qt_dpi()
    from mainwindow import main
    main()