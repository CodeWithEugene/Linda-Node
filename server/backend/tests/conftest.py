"""Opt-in switch for the live upstream contract tests."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--contract", action="store_true", default=False, help="run tests that call the live ICPAC API")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--contract"):
        return
    skip = pytest.mark.skip(reason="live upstream test; pass --contract to run")
    for item in items:
        if "contract" in item.keywords:
            item.add_marker(skip)
