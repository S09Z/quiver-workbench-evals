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


def test_resolve_models_rejects_old_list_shape(tmp_path):
    (tmp_path / "models.json").write_text(
        json.dumps(["anthropic/claude-opus-5"]), encoding="utf-8"
    )
    with pytest.raises(SystemExit):
        run.resolve_models(tmp_path, "openrouter", None)


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
        self.content = "สวัสดี"

    def create(self, **kwargs):
        self.kwargs = kwargs
        return _fake_resp(self.finish_reason, self.content)


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


def test_missing_tags_reports_only_absent():
    got = run.missing_tags(["qwen3:latest", "nope:1b"], ["qwen3:latest", "llama3:8b"])
    assert got == ["nope:1b"]


def test_missing_tags_empty_when_all_present():
    assert run.missing_tags(["qwen3:latest"], ["qwen3:latest", "llama3:8b"]) == []


def test_backend_from_dirname_new_format():
    assert run.backend_from_dirname("2026-09-09__catfood__ollama__qwen3-latest") == "ollama"


def test_backend_from_dirname_legacy_is_unknown():
    # โฟลเดอร์รูปแบบเก่าไม่มีช่อง backend — ต้องคืน '?' ไม่ใช่เดามั่ว
    assert run.backend_from_dirname("2026-09-09__catfood__anthropic__claude-opus-5") == "?"


def test_one_call_skips_without_calling_api_when_md_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient()
    case = {"id": "e99", "prompt": "hi"}
    run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    cl.completions.kwargs = None
    out = run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    assert out.startswith("skip")
    assert cl.completions.kwargs is None      # ไม่ได้ยิงซ้ำ


def test_one_call_force_reruns_and_calls_api(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient()
    case = {"id": "e99", "prompt": "hi"}
    run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    cl.completions.kwargs = None
    run.one_call(cl, "catfood", case, "qwen3:latest", 1, True, "ollama", 1234)
    assert cl.completions.kwargs is not None


def test_one_call_marks_truncation_in_the_md_file(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient("length")
    case = {"id": "e99", "prompt": "hi"}
    run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    md = (tmp_path / run.run_dir_name("catfood", "ollama", "qwen3:latest") / "e99__r1.md").read_text(
        encoding="utf-8"
    )
    assert "TRUNCATED" in md.splitlines()[0]


def test_one_call_md_has_no_marker_when_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient("stop")
    case = {"id": "e99", "prompt": "hi"}
    run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    md = (tmp_path / run.run_dir_name("catfood", "ollama", "qwen3:latest") / "e99__r1.md").read_text(
        encoding="utf-8"
    )
    assert "TRUNCATED" not in md


def test_one_call_reports_empty_answer_as_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient("length")
    cl.completions.content = ""
    case = {"id": "e99", "prompt": "hi"}
    out = run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 1234)
    assert out.startswith("EMPTY")


def test_one_call_records_max_tokens_in_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    cl = _FakeClient()
    case = {"id": "e99", "prompt": "hi"}
    run.one_call(cl, "catfood", case, "qwen3:latest", 1, False, "ollama", 4321)
    assert _meta_of(tmp_path)["max_tokens"] == 4321


def test_backends_carry_their_own_max_tokens():
    assert run.BACKENDS["ollama"]["max_tokens"] > run.BACKENDS["openrouter"]["max_tokens"]
