"""
Preserve real modules that may get mocked by some test files.

Some test files (e.g. test_gui_fields.py) mock entire modules at import time.
This conftest ensures that tests which need real modules can always access them.
"""

import contextlib
import importlib
import sys

import pytest

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


@pytest.fixture(autouse=True)
def _config_in_tmp(tmp_path, monkeypatch):
    """Keep every test away from the real config file.

    Building VideodlApp loads and rewrites videodl-config.toml, and test_gui_builds
    builds it against a MagicMock page: every `pytest` run was rewriting, and once
    emptying, the settings of whoever ran it. Point the config dir at tmp_path,
    and drop the cached path so it is recomputed there. Several test files re-import
    gui.*, so reset it on every copy of the module still reachable.
    """
    for var in ("HOME", "XDG_CONFIG_HOME", "LOCALAPPDATA"):
        monkeypatch.setenv(var, str(tmp_path))
    namespaces = [vars(m) for m in list(sys.modules.values()) if hasattr(m, "_get_config_filename")]
    namespaces += [
        m.VideodlConfig.__init__.__globals__
        for m in list(sys.modules.values())
        if isinstance(getattr(m, "VideodlConfig", None), type)
    ]
    for namespace in namespaces:
        if "_config_filename" in namespace:
            monkeypatch.setitem(namespace, "_config_filename", None)
