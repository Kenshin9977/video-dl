from unittest.mock import patch

import pytest
from utils.sys_architecture import get_system_architecture


class TestGetSystemArchitecture:
    @pytest.mark.parametrize(
        ("machine_value", "expected"),
        [
            ("arm64", "arm64"),
            ("aarch64", "arm64"),
            ("ARM64", "arm64"),
            ("armv7l", "arm"),
            ("armv6l", "arm"),
            ("i686", "x86"),
            ("i386", "x86"),
            ("x86_64", "x86_64"),
            ("AMD64", "x86_64"),
            ("riscv64", "unknown"),
            ("mips", "unknown"),
        ],
    )
    def test_architectures(self, machine_value, expected):
        with patch("utils.sys_architecture.machine", return_value=machine_value):
            assert get_system_architecture() == expected
