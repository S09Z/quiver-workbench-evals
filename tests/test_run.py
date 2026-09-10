import json
from types import SimpleNamespace

import pytest

import run


def test_import_works():
    assert hasattr(run, "cmd_run")
