"""The version of the app, and the only place it is written down.

pyproject.toml reads it from here (`dynamic = ["version"]`), utils/sys_utils.py
imports it, and the macOS spec execs this file for CFBundleShortVersionString.

It used to live in all three, kept in sync by a sed in release.sh that only worked
on macOS. It was not in sync: pyproject said 2.2.4 and the macOS bundle said 2.2.2.

Keep this module free of imports: the PyInstaller spec runs it on its own.
"""

__version__ = "2.3.8"
