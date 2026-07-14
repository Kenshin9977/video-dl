"""Every translated widget must follow the language the user picked.

Not a mocked GUI test: it reads gui/app.py and checks an invariant that is easy to
break and invisible until someone screenshots the app in another language.

The Chrome cookies panel broke exactly this way. Its four labels were built with
gt() in __init__ and then never reassigned in _refresh_labels, so they kept whatever
the *system* locale was, while the rest of the window followed the config. An English
user on a French machine got half a window in French.
"""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).parent.parent / "gui" / "app.py"
TREE = ast.parse(APP.read_text(encoding="utf-8"))

APP_CLASS = next(node for node in ast.walk(TREE) if isinstance(node, ast.ClassDef) and node.name == "VideodlApp")
METHODS = {node.name: node for node in APP_CLASS.body if isinstance(node, ast.FunctionDef)}


def _calls_gt(node: ast.AST) -> bool:
    return any(
        isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "gt"
        for inner in ast.walk(node)
    )


def _translated_widgets() -> set[str]:
    """`self.x = Text(gt(...))` in __init__: a widget whose text comes from the language."""
    widgets = set()
    for node in ast.walk(METHODS["__init__"]):
        if not isinstance(node, ast.Assign) or not _calls_gt(node.value):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                widgets.add(target.attr)
    return widgets


def _refreshed_widgets() -> set[str]:
    """Widgets reassigned by _refresh_labels, or by a helper it calls."""
    bodies = [METHODS["_refresh_labels"]]
    for node in ast.walk(METHODS["_refresh_labels"]):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
            and node.func.attr in METHODS
        ):
            bodies.append(METHODS[node.func.attr])

    refreshed = set()
    for body in bodies:
        for node in ast.walk(body):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                # self.<widget>.<property> = ...
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Attribute)
                    and isinstance(target.value.value, ast.Name)
                    and target.value.value.id == "self"
                ):
                    refreshed.add(target.value.attr)
    return refreshed


class TestEveryTranslatedWidgetFollowsTheLanguage:
    def test_the_app_declares_translated_widgets(self):
        """Guard the guard: if the parsing stops finding anything, the test below is vacuous."""
        assert len(_translated_widgets()) > 10

    @pytest.mark.parametrize("widget", sorted(_translated_widgets()))
    def test_it_is_refreshed_when_the_language_changes(self, widget):
        assert widget in _refreshed_widgets(), (
            f"self.{widget} is built with gt() but _refresh_labels never reassigns it, "
            "so it will keep the language it was born with"
        )
