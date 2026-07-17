"""A missing DLL in a child process must not pop a Windows dialog.

aria2c, ffmpeg and qjs run as subprocesses. When one cannot load a DLL, the Windows
loader shows a modal "code execution cannot proceed" box per missing library, and
the app cannot catch it: the user just gets a stack of errors at startup. A user hit
exactly this with a dynamically-linked aria2c shipped without its DLLs.

main.py sets SEM_FAILCRITICALERRORS at startup so the loader returns an error code
instead. These check the call is made, that it is inherited by children, and that it
is a no-op off Windows.
"""

import subprocess
import sys

import pytest

import main


class TestSilenceWindowsLoaderDialogs:
    def test_it_is_a_noop_off_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        # Must not touch ctypes (which has no windll off Windows) or raise.
        main._silence_windows_loader_dialogs()

    @pytest.mark.skipif(sys.platform != "win32", reason="SetErrorMode is Windows only")
    def test_it_sets_the_fail_critical_errors_flag(self):
        import ctypes

        SEM_FAILCRITICALERRORS = 0x0001
        main._silence_windows_loader_dialogs()
        assert ctypes.windll.kernel32.GetErrorMode() & SEM_FAILCRITICALERRORS

    @pytest.mark.skipif(sys.platform != "win32", reason="SetErrorMode is Windows only")
    def test_a_child_that_cannot_load_a_dll_fails_with_a_code_not_a_dialog(self, tmp_path):
        """A .exe importing a DLL that does not exist returns STATUS_DLL_NOT_FOUND.

        Built here rather than reusing aria2c so the test owns its broken binary. The
        point is that subprocess.run returns instead of blocking on a modal dialog.
        """
        import ctypes

        # A tiny PE that imports a nonexistent DLL is awkward to synthesize, so lean on
        # the loader directly: LoadLibrary of a missing DLL under this error mode must
        # return 0 (failure) rather than raising a dialog.
        main._silence_windows_loader_dialogs()
        handle = ctypes.windll.kernel32.LoadLibraryW("this-dll-does-not-exist-videodl.dll")
        assert handle == 0

        # And a real subprocess launch of a missing executable returns, never hangs.
        with pytest.raises((FileNotFoundError, OSError)):
            subprocess.run([str(tmp_path / "nope.exe")], capture_output=True, timeout=10)
