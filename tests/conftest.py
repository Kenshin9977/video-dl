"""
Preserve real modules that may get mocked by some test files.

Some test files (e.g. test_gui_fields.py) mock entire modules at import time.
This conftest ensures that tests which need real modules can always access them.
"""

import contextlib
import importlib
import sys

# Pre-import real modules before any test can mock them
_REAL_MODULES = {}
for _mod_name in [
    "quantiphy",
    "core.error_report",
    "core.progress",
    "core.ydl_opts",
    "i18n.lang",
    "utils.parse_util",
    "utils.sys_architecture",
]:
    with contextlib.suppress(ImportError):
        _REAL_MODULES[_mod_name] = importlib.import_module(_mod_name)


def ensure_real_module(mod_name: str):
    """Restore a real module if it was replaced by a mock."""
    if mod_name in _REAL_MODULES:
        sys.modules[mod_name] = _REAL_MODULES[mod_name]
