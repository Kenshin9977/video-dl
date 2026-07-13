import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Several test modules replace utils.* and yt_dlp.* with MagicMocks in sys.modules
# and never put them back. Bind the real modules here, whatever the collection order.
sys.modules.setdefault("flet", MagicMock())
sys.modules.pop("utils.aria2_install", None)
sys.modules.pop("utils.sys_utils", None)

import deps  # noqa: E402
import version  # noqa: E402
from utils.aria2_install import _ARIA2C_BASE_URL  # noqa: E402
from utils.sys_utils import APP_VERSION  # noqa: E402

ROOT = Path(__file__).parent.parent
BUILD_WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"
MAKEFILE = ROOT / "Makefile"
RENOVATE = ROOT / ".github" / "renovate.json"

# The pins that must exist nowhere but deps.py. Anything that names a version, a
# tag or a commit: those are what drift when they are written down twice.
PINNED = ["FFMPEG_ANDROID_TAG", "ARIA2_TAG", "QUICKJS_COMMIT", "NDK_VERSION"]


class TestSingleSourceOfTruth:
    """A pin written down twice is a pin that will drift.

    It already had: aria2c was release-2.0.0 on the desktop and floated to 2.0.1 on
    Android, the NDK was 27.2 in CI and 28.2 in the Makefile, and the app version
    was 2.2.4 in pyproject.toml and 2.2.2 in the macOS bundle.
    """

    @pytest.mark.parametrize("pin", PINNED)
    def test_the_value_appears_nowhere_but_deps(self, pin):
        value = getattr(deps, pin)
        for path in (BUILD_WORKFLOW, MAKEFILE):
            assert value not in path.read_text(encoding="utf-8"), (
                f"{path.name} hardcodes {pin}={value}. Read it from deps.py instead."
            )

    def test_the_workflow_and_the_makefile_read_deps(self):
        assert "deps.py" in BUILD_WORKFLOW.read_text(encoding="utf-8")
        assert "deps.py" in MAKEFILE.read_text(encoding="utf-8")

    def test_the_desktop_installer_reads_the_same_aria2c_pin(self):
        assert deps.ARIA2_TAG in _ARIA2C_BASE_URL

    def test_the_app_version_lives_only_in_version_py(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'dynamic = ["version"]' in pyproject
        assert f'version = "{version.__version__}"' not in pyproject
        assert version.__version__ == APP_VERSION


class TestRenovateCoversEveryPin:
    """A pin nobody automates is a pin that rots. Renovate must know about each one."""

    @pytest.mark.parametrize("pin", PINNED)
    def test_every_pin_has_a_renovate_comment_or_manager(self, pin):
        source = Path(deps.__file__).read_text(encoding="utf-8")
        declaration = re.search(rf"^{pin} = ", source, re.MULTILINE)
        assert declaration, f"{pin} is not declared in deps.py"

        preceding = source[: declaration.start()]
        renovate_config = RENOVATE.read_text(encoding="utf-8")
        assert "# renovate:" in preceding.split("\n\n")[-1] or pin in renovate_config, (
            f"{pin} has no renovate hint, so nothing will ever bump it"
        )


class TestPinsAreImmutable:
    def test_nothing_floats_on_a_mutable_tag(self):
        """`latest` is replaced in place, so a build of the same tag is not reproducible."""
        assert deps.FFMPEG_ANDROID_TAG != "latest"
        assert deps.FFMPEG_ANDROID_TAG.startswith("autobuild-")
        assert re.fullmatch(r"[0-9a-f]{40}", deps.QUICKJS_COMMIT), "QuickJS must be pinned to a full commit sha"

    def test_the_workflow_never_downloads_a_latest_release(self):
        workflow = BUILD_WORKFLOW.read_text(encoding="utf-8")
        assert "gh release download latest" not in workflow

    def test_the_ffmpeg_asset_is_matched_by_pattern_not_by_name(self):
        """The name carries the build number, so pinning the tag and naming the file fetches nothing.

        The rolling `latest` release calls it ffmpeg-master-latest-androidarm64-*, and
        every dated autobuild calls it ffmpeg-N-<build>-g<commit>-androidarm64-*. Naming
        it would break the build the first time Renovate bumped the tag, which is the
        one moment nobody is watching.
        """
        pattern = deps.FFMPEG_ANDROID_ASSET_PATTERN
        assert pattern.startswith("*"), "the build number lives at the front, so the wildcard has to"
        assert "latest" not in pattern, "that name only exists on the rolling release, not on a pinned tag"
        assert not re.search(r"N-\d+", pattern), "a build number here breaks the next tag bump"
