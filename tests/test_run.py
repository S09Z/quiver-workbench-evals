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


def test_backends_table_has_both_lanes():
    assert set(run.BACKENDS) == {"openrouter", "ollama"}


def test_client_ollama_points_at_localhost(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cl = run.client("ollama")
    assert str(cl.base_url).startswith("http://localhost:11434")


def test_client_openrouter_needs_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        run.client("openrouter")


def test_ollama_runs_one_worker():
    assert run.BACKENDS["ollama"]["workers"] == 1


def test_default_models_keyed_by_backend():
    assert set(run.DEFAULT_MODELS) == {"openrouter", "ollama"}
    assert "qwen3:latest" in run.DEFAULT_MODELS["ollama"]


def test_resolve_models_uses_backend_default(tmp_path):
    assert run.resolve_models(tmp_path, "ollama", None) == run.DEFAULT_MODELS["ollama"]


def test_resolve_models_cli_override_wins(tmp_path):
    assert run.resolve_models(tmp_path, "ollama", ["foo:bar"]) == ["foo:bar"]


def test_resolve_models_reads_suite_file(tmp_path):
    (tmp_path / "models.json").write_text(
        json.dumps({"ollama": ["custom:tag"]}), encoding="utf-8"
    )
    assert run.resolve_models(tmp_path, "ollama", None) == ["custom:tag"]


def test_resolve_models_missing_backend_key_exits(tmp_path):
    (tmp_path / "models.json").write_text(
        json.dumps({"openrouter": ["x/y"]}), encoding="utf-8"
    )
    with pytest.raises(SystemExit):
        run.resolve_models(tmp_path, "ollama", None)


def _fake_resp(finish_reason="stop", content="สวัสดี"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=22),
    )


class _FakeCompletions:
    def __init__(self, finish_reason):
        self.finish_reason = finish_reason
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return _fake_resp(self.finish_reason)


class _FakeClient:
    def __init__(self, finish_reason="stop"):
        self.completions = _FakeCompletions(finish_reason)
        self.chat = SimpleNamespace(completions=self.completions)


def _meta_of(tmp_path, backend="ollama", model="qwen3:latest"):
    name = run.run_dir_name("catfood", backend, model)
    return json.loads((tmp_path / name / "e99__r1.meta.json").read_text(encoding="utf-8"))


def test_one_call_sends_max_tokens(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient()
    case = {"id": "e99", "prompt": "hi"}
    run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    assert cl.completions.kwargs["max_tokens"] == 1234


def test_one_call_records_backend_and_finish_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient("length")
    case = {"id": "e99", "prompt": "hi"}
    out = run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    meta = _meta_of(tmp_path)
    assert meta["backend"] == "ollama"
    assert meta["finish_reason"] == "length"
    assert "ถูกตัด" in out


def test_one_call_no_warning_when_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient("stop")
    case = {"id": "e99", "prompt": "hi"}
    out = run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    assert "ถูกตัด" not in out
    assert _meta_of(tmp_path)["finish_reason"] == "stop"
