import json
from types import SimpleNamespace

import pytest

import run


def test_import_works():
    assert hasattr(run, "cmd_run")


def test_model_slug_openrouter_style():
    assert run.model_slug("anthropic/claude-opus-5") == "anthropic__claude-opus-5"


def test_model_slug_ollama_tag():
    assert run.model_slug("qwen3:latest") == "qwen3-latest"


def test_model_slug_cloud_tag():
    assert run.model_slug("glm-5.3:cloud") == "glm-5.3-cloud"


def test_run_dir_name_includes_backend():
    name = run.run_dir_name("catfood", "ollama", "qwen3:latest", day="2026-09-09")
    assert name == "2026-09-09__catfood__ollama__qwen3-latest"


def test_run_dir_name_openrouter():
    name = run.run_dir_name("catfood", "openrouter", "anthropic/claude-opus-5", day="2026-09-09")
    assert name == "2026-09-09__catfood__openrouter__anthropic__claude-opus-5"
