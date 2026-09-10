# Local LLM backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่ม flag `--backend {openrouter,ollama}` ให้ `harness/run.py` เพื่อรัน eval ผ่าน Ollama ที่ติดตั้งอยู่แล้วบนเครื่อง โดยไม่ต้องเติมเครดิต OpenRouter

**Architecture:** เปลี่ยนค่าคงที่ที่ฝังอยู่ใน `client()` เป็นตาราง `BACKENDS` (base_url / env ของ API key / จำนวน worker) แล้วให้ `--backend` เลือกทั้งรัน ติดชื่อ backend ลงในชื่อโฟลเดอร์ผลลัพธ์เพื่อให้ `report` แยก lane ได้ พร้อมเพิ่ม preflight check และเพดาน `max_tokens` แยกฟังก์ชันที่คำนวณล้วน ๆ (slug, การเลือกโมเดล, การเทียบ tag) ออกมาเพื่อให้เทสต์ได้โดยไม่ต้องต่อเน็ต

**Tech Stack:** Python 3.12, OpenAI SDK (ใช้ยิงได้ทั้ง OpenRouter และ Ollama), pytest, poetry

**Spec:** [`docs/superpowers/specs/2026-09-09-local-llm-backend-design.md`](../specs/2026-09-09-local-llm-backend-design.md)

---

## บริบทของ branch ที่ต้องรู้ก่อนเริ่ม

ทำงานบน branch `harness/local-llm-backend` (PR #4) ซึ่งแตกจาก `main` ที่มีแค่ initial commit ผลคือ:

- `pyproject.toml` บน branch นี้ยัง **ไม่มี** `openai` กับ `python-dotenv` ในรายการ dependencies (ของจริงอยู่ใน PR #3) — Task 1 เติมให้เพื่อให้ branch นี้รันได้ด้วยตัวเอง ตอน merge อาจชนกับ PR #3 แต่เป็นบรรทัดเดียวกันเป๊ะ แก้ conflict ง่าย
- `MANUAL.md` **ไม่มีบน branch นี้** (อยู่ใน PR #3) — Task 11 จึงแก้แค่ `CLAUDE.md` ส่วน `MANUAL.md` ทำหลัง PR #3 merge
- `.venv` ที่มีอยู่ตอนนี้ติดตั้ง `openai 3.10.0` และ `python-dotenv` ไว้แล้ว เทสต์จึงรันได้ทันที

## File Structure

| ไฟล์ | สถานะ | หน้าที่ |
|---|---|---|
| `harness/run.py` | แก้ | ตัว runner — เพิ่มตาราง backend, ฟังก์ชันคำนวณล้วน ๆ, preflight, max_tokens |
| `tests/conftest.py` | สร้าง | ให้ `import run` ได้จากในเทสต์ (harness/ ไม่ใช่ package) |
| `tests/test_run.py` | สร้าง | เทสต์ฟังก์ชันที่คำนวณล้วน ๆ ทั้งหมด ไม่ต่อเน็ต |
| `pyproject.toml` | แก้ | เติม `openai`, `python-dotenv`, และ dev group `pytest` |
| `CLAUDE.md` | แก้ | อัปเดตหัวข้อ "คำสั่ง" และ "สถานะ" |
| `docs/superpowers/specs/2026-09-09-local-llm-backend-design.md` | แก้ | แก้ endpoint เช็คเครดิตให้ถูก (Task 8) |

**สิ่งที่เทสต์ครอบคลุม:** `model_slug`, `run_dir_name`, `client`, `resolve_models`, `missing_tags`, `backend_from_dirname`, `one_call` (ผ่าน fake client)
**สิ่งที่ไม่ได้เทสต์อัตโนมัติ:** ฟังก์ชัน preflight ที่ยิง HTTP จริง (`check_ollama`, `check_openrouter`) — ตรวจด้วยมือใน Task 12 ตามเกณฑ์ตรวจรับของ spec §6

---

### Task 1: ตั้ง test infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/conftest.py`
- Create: `tests/test_run.py`

- [ ] **Step 1: เติม dependencies**

แก้ `pyproject.toml` ให้ส่วน `dependencies` เป็น:

```toml
dependencies = [
    "openai>=1.0.0",
    "python-dotenv>=1.0.0",
]

[tool.poetry]
package-mode = false

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
```

วางบล็อก `[tool.poetry]` และ `[tool.poetry.group.dev.dependencies]` ต่อท้ายไฟล์ ก่อน `[build-system]`

`package-mode = false` จำเป็น เพราะ repo นี้เป็นสคริปต์ ไม่ใช่ package — ถ้าไม่ใส่
`poetry install` จะพังด้วย `No file/folder found for package quiver-workbench-evals`

- [ ] **Step 2: ติดตั้ง**

Run: `poetry lock && poetry install`
Expected: ลงสำเร็จ เห็น `pytest` ในรายการที่ติดตั้ง

- [ ] **Step 3: สร้าง conftest ให้ import run.py ได้**

สร้าง `tests/conftest.py`:

```python
import sys
from pathlib import Path

# harness/ ไม่ใช่ package เลยต้องเติม path เองก่อน import run
sys.path.insert(0, str(Path(__file__).parent.parent / "harness"))
```

- [ ] **Step 4: สร้างไฟล์เทสต์พร้อม smoke test**

สร้าง `tests/test_run.py`:

```python
import json
from types import SimpleNamespace

import pytest

import run


def test_import_works():
    assert hasattr(run, "cmd_run")
```

- [ ] **Step 5: รันให้ผ่าน**

Run: `poetry run pytest tests/ -v`
Expected: PASS 1 test

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml poetry.lock tests/
git commit -m "test: ตั้ง pytest และ conftest สำหรับเทสต์ harness"
```

---

### Task 2: `model_slug()` — แปลงชื่อโมเดลเป็นชื่อโฟลเดอร์

**Files:**
- Modify: `harness/run.py` (เพิ่มฟังก์ชันใหม่ก่อน `run_dir` บรรทัด 110)
- Test: `tests/test_run.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เติมท้าย `tests/test_run.py`:

```python
def test_model_slug_openrouter_style():
    assert run.model_slug("anthropic/claude-opus-5") == "anthropic__claude-opus-5"


def test_model_slug_ollama_tag():
    assert run.model_slug("qwen3:latest") == "qwen3-latest"


def test_model_slug_cloud_tag():
    assert run.model_slug("glm-5.3:cloud") == "glm-5.3-cloud"
```

- [ ] **Step 2: รันให้เห็นว่าพัง**

Run: `poetry run pytest tests/test_run.py -k model_slug -v`
Expected: FAIL — `AttributeError: module 'run' has no attribute 'model_slug'`

- [ ] **Step 3: เขียน implementation**

เพิ่มใน `harness/run.py` เหนือ `def run_dir(...)`:

```python
def model_slug(model: str) -> str:
    """ชื่อโมเดล -> ชิ้นส่วนชื่อโฟลเดอร์

    '/' -> '__' ตามของเดิม และ ':' -> '-' เพราะ Finder บน macOS แสดง ':' เป็น '/'
    ทำให้ชื่อโฟลเดอร์ของ ollama อ่านสับสน
    """
    return model.replace("/", "__").replace(":", "-")
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `poetry run pytest tests/test_run.py -k model_slug -v`
Expected: PASS 3 tests

- [ ] **Step 5: Commit**

```bash
git add harness/run.py tests/test_run.py
git commit -m "feat: model_slug() แปลงชื่อโมเดลเป็นชื่อโฟลเดอร์ที่ปลอดภัย"
```

---

### Task 3: `run_dir_name()` — ใส่ backend ลงในชื่อโฟลเดอร์

**Files:**
- Modify: `harness/run.py:110-114`
- Test: `tests/test_run.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เติมท้าย `tests/test_run.py`:

```python
def test_run_dir_name_includes_backend():
    name = run.run_dir_name("catfood", "ollama", "qwen3:latest", day="2026-09-09")
    assert name == "2026-09-09__catfood__ollama__qwen3-latest"


def test_run_dir_name_openrouter():
    name = run.run_dir_name("catfood", "openrouter", "anthropic/claude-opus-5", day="2026-09-09")
    assert name == "2026-09-09__catfood__openrouter__anthropic__claude-opus-5"
```

- [ ] **Step 2: รันให้เห็นว่าพัง**

Run: `poetry run pytest tests/test_run.py -k run_dir_name -v`
Expected: FAIL — `AttributeError: module 'run' has no attribute 'run_dir_name'`

- [ ] **Step 3: เขียน implementation**

แทนที่ `def run_dir(...)` เดิมทั้งฟังก์ชัน (บรรทัด 110-114) ด้วย:

```python
def run_dir_name(suite_name: str, backend: str, model: str, day: str | None = None) -> str:
    day = day or date.today().isoformat()
    return f"{day}__{suite_name}__{backend}__{model_slug(model)}"


def run_dir(suite_name: str, backend: str, model: str) -> Path:
    d = RESULTS_DIR / run_dir_name(suite_name, backend, model)
    d.mkdir(parents=True, exist_ok=True)
    return d
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `poetry run pytest tests/test_run.py -k run_dir_name -v`
Expected: PASS 2 tests

- [ ] **Step 5: Commit**

```bash
git add harness/run.py tests/test_run.py
git commit -m "feat: run_dir_name() ติดชื่อ backend ลงในโฟลเดอร์ผลลัพธ์"
```

---

### Task 4: ตาราง `BACKENDS` และ `client(backend)`

**Files:**
- Modify: `harness/run.py:52-71`
- Test: `tests/test_run.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เติมท้าย `tests/test_run.py`:

```python
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
```

- [ ] **Step 2: รันให้เห็นว่าพัง**

Run: `poetry run pytest tests/test_run.py -k "backends or client" -v`
Expected: FAIL — `AttributeError: module 'run' has no attribute 'BACKENDS'`

- [ ] **Step 3: เขียน implementation**

แทนที่บล็อก `MAX_WORKERS = 4` (บรรทัด 59) ด้วยตาราง แล้วแก้ `client()`:

```python
REQUEST_TIMEOUT = 600     # โมเดล reasoning ใช้เวลานาน อย่าตั้งต่ำ
MAX_TOKENS = 4000         # ไม่ตั้ง = โมเดลขอเพดานตัวเอง (65536) แล้ว OpenRouter กันเครดิตไม่ไหว

# ---------------------------------------------------------------------------
# ollama ตั้ง workers=1 เพราะโมเดล 8B กินราว 5 GB ยิงขนานบน RAM 16 GB แล้ว swap
# อีกทั้ง ollama serialize request ต่อโมเดลอยู่แล้ว ขนานไปก็ไม่ได้ throughput เพิ่ม
# ---------------------------------------------------------------------------
BACKENDS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "workers": 4,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,
        "workers": 1,
    },
}
```

แล้วแทนที่ `def client()` ทั้งฟังก์ชัน:

```python
def client(backend: str) -> OpenAI:
    conf = BACKENDS[backend]
    env = conf["api_key_env"]
    if env:
        key = os.getenv(env)
        if not key:
            sys.exit(f"ไม่พบ {env} — ใส่ในไฟล์ .env ก่อน")
    else:
        key = "not-needed"      # ollama ไม่ตรวจคีย์ แต่ SDK บังคับให้ส่งค่าอะไรสักอย่าง
    return OpenAI(
        base_url=conf["base_url"],
        api_key=key,
        timeout=REQUEST_TIMEOUT,
    )
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `poetry run pytest tests/test_run.py -k "backends or client or worker" -v`
Expected: PASS 4 tests

- [ ] **Step 5: Commit**

```bash
git add harness/run.py tests/test_run.py
git commit -m "feat: ตาราง BACKENDS และ client(backend) แทน URL ที่ฝังไว้"
```

---

### Task 5: `DEFAULT_MODELS` เป็น dict และ `resolve_models()`

**Files:**
- Modify: `harness/run.py:52-57` (DEFAULT_MODELS), `harness/run.py:83-87` (load_models)
- Test: `tests/test_run.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เติมท้าย `tests/test_run.py`:

```python
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
```

- [ ] **Step 2: รันให้เห็นว่าพัง**

Run: `poetry run pytest tests/test_run.py -k "default_models or resolve_models" -v`
Expected: FAIL — `AttributeError: module 'run' has no attribute 'resolve_models'`

- [ ] **Step 3: เขียน implementation**

แทนที่ `DEFAULT_MODELS = [...]` (บรรทัด 52-57) ด้วย:

```python
DEFAULT_MODELS = {
    "openrouter": [
        "anthropic/claude-opus-5",
        "openai/gpt-5.6-sol",
        "google/gemini-3.8-flash",
        "qwen/qwen3.8-max",
    ],
    # tag ต้องตรงกับที่ `ollama list` มีจริง — 'qwen3:8b' ไม่มีอยู่จริง
    # โมเดล :cloud ไม่ใส่ไว้ตรงนี้เพราะมีวันหมดอายุ ให้ใส่ผ่าน models.json แทน
    "ollama": [
        "qwen3:latest",
        "llama3:8b",
        "deepseek-r1:latest",
    ],
}
```

แทนที่ `def load_models(suite)` ทั้งฟังก์ชัน (บรรทัด 83-87) ด้วย:

```python
def resolve_models(suite: Path, backend: str, override=None):
    """ลำดับความสำคัญ: --models > suites/<ชื่อ>/models.json > DEFAULT_MODELS"""
    if override:
        return override
    path = suite / "models.json"
    if path.exists():
        per_backend = json.loads(path.read_text(encoding="utf-8"))
        if backend not in per_backend:
            sys.exit(
                f"{path} ไม่มีคีย์ '{backend}' — ที่มีคือ: {', '.join(sorted(per_backend))}"
            )
        return per_backend[backend]
    return DEFAULT_MODELS[backend]
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `poetry run pytest tests/test_run.py -k "default_models or resolve_models" -v`
Expected: PASS 5 tests

- [ ] **Step 5: Commit**

```bash
git add harness/run.py tests/test_run.py
git commit -m "feat: ลิสต์โมเดลแยกตาม backend + resolve_models()"
```

---

### Task 6: `max_tokens` และ `finish_reason` ใน `one_call()`

**Files:**
- Modify: `harness/run.py:117-162`
- Test: `tests/test_run.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เติมท้าย `tests/test_run.py`:

```python
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
```

- [ ] **Step 2: รันให้เห็นว่าพัง**

Run: `poetry run pytest tests/test_run.py -k one_call -v`
Expected: FAIL — `TypeError: one_call() takes 6 positional arguments but 8 were given`

- [ ] **Step 3: เขียน implementation**

แทนที่ `def one_call(...)` ทั้งฟังก์ชัน (บรรทัด 117-162) ด้วย:

```python
def one_call(cl, suite_name, case, model, rep, force, backend, max_tokens):
    out_dir = run_dir(suite_name, backend, model)
    stem = f"{case['id']}__r{rep}"
    md_path = out_dir / f"{stem}.md"

    # resumable — รันซ้ำได้โดยไม่จ่ายเงินซ้ำ
    if md_path.exists() and not force:
        return f"skip  {model:34} {stem}"

    started = time.time()
    try:
        resp = cl.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": case["prompt"]}],
            temperature=case.get("temperature", 1.0),
            max_tokens=max_tokens,
        )
    except Exception as exc:
        (out_dir / f"{stem}.error.txt").write_text(repr(exc), encoding="utf-8")
        return f"FAIL  {model:34} {stem}  {type(exc).__name__}"

    elapsed = round(time.time() - started, 1)
    choice = resp.choices[0]
    text = choice.message.content or ""
    finish_reason = getattr(choice, "finish_reason", None)

    md_path.write_text(
        f"<!-- {model} | {suite_name}/{case['id']} | rep {rep} | {elapsed}s -->\n\n{text}",
        encoding="utf-8",
    )

    usage = getattr(resp, "usage", None)
    (out_dir / f"{stem}.meta.json").write_text(
        json.dumps(
            {
                "suite": suite_name,
                "backend": backend,
                "model": model,
                "case": case["id"],
                "repeat": rep,
                "seconds": elapsed,
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "finish_reason": finish_reason,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # คำตอบที่โดนตัดจะทำให้ให้คะแนนผิด (0 ในเกณฑ์ที่โมเดลยังไม่ทันเขียนถึง) ต้องเห็นชัด
    cut = "  ⚠️ ถูกตัดกลางคัน (max_tokens)" if finish_reason == "length" else ""
    return f"ok    {model:34} {stem}  {elapsed}s{cut}"
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `poetry run pytest tests/test_run.py -k one_call -v`
Expected: PASS 3 tests

- [ ] **Step 5: Commit**

```bash
git add harness/run.py tests/test_run.py
git commit -m "feat: ตั้งเพดาน max_tokens และบันทึก finish_reason กันคะแนนเพี้ยน"
```

---

### Task 7: preflight ของ ollama

**Files:**
- Modify: `harness/run.py` (เพิ่มฟังก์ชันใหม่ก่อน `cmd_run`)
- Test: `tests/test_run.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เติมท้าย `tests/test_run.py`:

```python
def test_missing_tags_reports_only_absent():
    got = run.missing_tags(["qwen3:latest", "nope:1b"], ["qwen3:latest", "llama3:8b"])
    assert got == ["nope:1b"]


def test_missing_tags_empty_when_all_present():
    assert run.missing_tags(["qwen3:latest"], ["qwen3:latest", "llama3:8b"]) == []
```

- [ ] **Step 2: รันให้เห็นว่าพัง**

Run: `poetry run pytest tests/test_run.py -k missing_tags -v`
Expected: FAIL — `AttributeError: module 'run' has no attribute 'missing_tags'`

- [ ] **Step 3: เขียน implementation**

เพิ่ม import ที่ต้นไฟล์ (ต่อจาก `import time` บรรทัด 33):

```python
import urllib.request
```

เพิ่มสองฟังก์ชันนี้เหนือ `def cmd_run(args):`:

```python
def missing_tags(requested, available) -> list:
    have = set(available)
    return sorted(t for t in requested if t not in have)


def check_ollama(models) -> None:
    """เช็คครั้งเดียวก่อนเข้าลูป ดีกว่าปล่อยให้พังทีละงานจนครบ"""
    url = BACKENDS["ollama"]["base_url"].replace("/v1", "") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            available = [m["name"] for m in json.load(r).get("models", [])]
    except Exception as exc:
        sys.exit(f"ต่อ ollama ไม่ได้ ({type(exc).__name__}) — ยังไม่ได้เปิดหรือเปล่า? ลอง `ollama serve`")

    missing = missing_tags(models, available)
    if missing:
        sys.exit(
            "ไม่พบ tag เหล่านี้ใน ollama: "
            + ", ".join(missing)
            + "\nที่มีอยู่: "
            + ", ".join(sorted(available))
            + "\nโหลดเพิ่มด้วย `ollama pull <tag>`"
        )
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `poetry run pytest tests/test_run.py -k missing_tags -v`
Expected: PASS 2 tests

- [ ] **Step 5: ตรวจกับ ollama จริง**

Run: `poetry run python -c "import sys; sys.path.insert(0,'harness'); import run; run.check_ollama(['qwen3:latest'])"`
Expected: ไม่มี output และ exit code 0 (เพราะ tag นี้มีจริง)

Run: `poetry run python -c "import sys; sys.path.insert(0,'harness'); import run; run.check_ollama(['ไม่มีจริง:9b'])"`
Expected: จบพร้อมข้อความบอกว่าไม่พบ tag และไล่ tag ที่มีให้ดู

- [ ] **Step 6: Commit**

```bash
git add harness/run.py tests/test_run.py
git commit -m "feat: preflight เช็ค ollama และ tag ที่ขอก่อนเริ่มรัน"
```

---

### Task 8: preflight ของ openrouter (เครดิต)

**Files:**
- Modify: `harness/run.py` (เพิ่มต่อจาก `check_ollama`)
- Modify: `docs/superpowers/specs/2026-09-09-local-llm-backend-design.md` (แก้ endpoint ให้ถูก)

- [ ] **Step 1: แก้ spec ให้ตรงความจริง**

ใน spec §5.5 บรรทัดที่ขึ้นต้นด้วย `- **openrouter:** \`GET /api/v1/key\`` ให้แก้ `/api/v1/key` เป็น `/api/v1/credits` และเติมหมายเหตุต่อท้ายย่อหน้าเดียวกัน:

```markdown
  (ตรวจจริงแล้ว: `/api/v1/key` คืน `limit_remaining: null` ใช้บอกยอดไม่ได้
  ตัวที่บอกได้คือ `/api/v1/credits` → `{"data":{"total_credits":X,"total_usage":Y}}`
  ยอดคงเหลือ = total_credits − total_usage)
```

- [ ] **Step 2: เขียน implementation**

เพิ่มต่อจาก `check_ollama`:

```python
def check_openrouter() -> None:
    """พิมพ์ยอดเครดิตให้เห็นก่อนเสมอ และหยุดถ้าเหลือ 0

    รันแรกพังทั้ง 48 งานด้วย 402 เพราะไม่มีใครรู้ว่าเครดิตหมดจนกว่าจะยิงจริง
    """
    key = os.getenv("OPENROUTER_API_KEY")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/credits",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)["data"]
    except Exception as exc:
        print(f"เช็คเครดิตไม่สำเร็จ ({type(exc).__name__}) — ไปต่อแบบไม่รู้ยอด", file=sys.stderr)
        return

    left = data.get("total_credits", 0) - data.get("total_usage", 0)
    print(f"เครดิต OpenRouter คงเหลือ: {left:.4f}")
    if left <= 0:
        sys.exit(
            "เครดิตหมด — เติมที่ https://openrouter.ai/settings/credits "
            "หรือรันด้วย --backend ollama แทน"
        )
```

- [ ] **Step 3: ตรวจกับของจริง**

Run: `poetry run python -c "import sys; sys.path.insert(0,'harness'); import run; run.check_openrouter()"`
Expected: พิมพ์ `เครดิต OpenRouter คงเหลือ: 0.0000` แล้วจบพร้อมข้อความให้ไปเติมเครดิตหรือใช้ ollama (เพราะบัญชีนี้เครดิตเป็น 0 จริง)

- [ ] **Step 4: Commit**

```bash
git add harness/run.py docs/superpowers/specs/2026-09-09-local-llm-backend-design.md
git commit -m "feat: preflight เช็คเครดิต OpenRouter ก่อนยิงงานจริง"
```

---

### Task 9: ต่อสาย `--backend` เข้า `cmd_run` และ argparse

**Files:**
- Modify: `harness/run.py:180-204` (cmd_run), `harness/run.py:294-300` (argparse)

- [ ] **Step 1: แก้ `cmd_run`**

แทนที่ `def cmd_run(args):` ทั้งฟังก์ชันด้วย:

```python
def cmd_run(args):
    suite = suite_path(args.suite)
    cases = load_cases(suite, args.cases)
    models = resolve_models(suite, args.backend, args.models)

    if args.backend == "ollama":
        check_ollama(models)
    else:
        check_openrouter()

    cl = client(args.backend)
    workers = BACKENDS[args.backend]["workers"]

    jobs = [
        (case, model, rep)
        for case in cases
        for model in models
        for rep in range(1, args.repeat + 1)
    ]
    print(
        f"{len(jobs)} งาน — {len(cases)} เคส × {len(models)} โมเดล × {args.repeat} รอบ "
        f"[{args.backend}, {workers} worker]\n"
    )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                one_call, cl, args.suite, case, model, rep,
                args.force, args.backend, args.max_tokens,
            )
            for case, model, rep in jobs
        ]
        for fut in as_completed(futures):
            print(fut.result(), flush=True)

    for model in models:
        make_score_stub(run_dir(args.suite, args.backend, model), cases, args.repeat)
    print("\nเสร็จ — ไปกรอกคะแนนใน results/*/scores.json")
```

- [ ] **Step 2: เพิ่ม flag ใน argparse**

เพิ่มสองบรรทัดนี้ต่อจาก `r.add_argument("--force", ...)`:

```python
    r.add_argument(
        "--backend", choices=sorted(BACKENDS), default="openrouter",
        help="openrouter (default) หรือ ollama สำหรับโมเดลในเครื่อง",
    )
    r.add_argument("--max-tokens", type=int, default=MAX_TOKENS, dest="max_tokens")
```

- [ ] **Step 3: ตรวจว่า flag ติดแล้ว**

Run: `poetry run python harness/run.py run --help`
Expected: เห็น `--backend {ollama,openrouter}` และ `--max-tokens MAX_TOKENS` ในรายการ

- [ ] **Step 4: ตรวจว่าเทสต์เดิมยังผ่านหมด**

Run: `poetry run pytest tests/ -v`
Expected: PASS ทุกตัว

- [ ] **Step 5: Commit**

```bash
git add harness/run.py
git commit -m "feat: flag --backend และ --max-tokens ใน cmd_run"
```

---

### Task 10: คอลัมน์ backend ใน `report`

**Files:**
- Modify: `harness/run.py:207-231` (cmd_report)
- Test: `tests/test_run.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เติมท้าย `tests/test_run.py`:

```python
def test_backend_from_dirname_new_format():
    assert run.backend_from_dirname("2026-09-09__catfood__ollama__qwen3-latest") == "ollama"


def test_backend_from_dirname_legacy_is_unknown():
    # โฟลเดอร์รูปแบบเก่าไม่มีช่อง backend — ต้องคืน '?' ไม่ใช่เดามั่ว
    assert run.backend_from_dirname("2026-09-09__catfood__anthropic__claude-opus-5") == "?"
```

- [ ] **Step 2: รันให้เห็นว่าพัง**

Run: `poetry run pytest tests/test_run.py -k backend_from_dirname -v`
Expected: FAIL — `AttributeError: module 'run' has no attribute 'backend_from_dirname'`

- [ ] **Step 3: เขียน implementation**

เพิ่มฟังก์ชันเหนือ `def cmd_report(args):`:

```python
def backend_from_dirname(name: str) -> str:
    """รูปแบบใหม่คือ <วันที่>__<suite>__<backend>__<model>
    โฟลเดอร์เก่าที่ยังไม่มีช่อง backend คืน '?' ไปตรง ๆ ดีกว่าเดา"""
    parts = name.split("__")
    if len(parts) >= 4 and parts[2] in BACKENDS:
        return parts[2]
    return "?"
```

แล้วแทนที่ `def cmd_report(args):` ทั้งฟังก์ชันด้วย:

```python
def cmd_report(args):
    rows = []
    for d in sorted(RESULTS_DIR.glob("*/")):
        path = d / "scores.json"
        if not path.exists():
            continue
        if args.suite and f"__{args.suite}__" not in d.name:
            continue
        scores = json.loads(path.read_text(encoding="utf-8"))
        vals = [
            v
            for entry in scores.values()
            for v in entry.get("criteria", {}).values()
            if isinstance(v, (int, float))
        ]
        slots = sum(len(e.get("criteria", {})) for e in scores.values())
        rows.append((d.name, backend_from_dirname(d.name), sum(vals), len(vals), slots))

    if not rows:
        sys.exit("ยังไม่มีคะแนน — กรอก scores.json ก่อน")

    print(f"{'run':58} {'backend':>10} {'คะแนน':>8} {'กรอกแล้ว':>12}")
    for name, backend, total, graded, slots in sorted(rows, key=lambda r: -r[2]):
        print(f"{name:58} {backend:>10} {total:>8} {f'{graded}/{slots}':>12}")
    print("\nอย่าเทียบข้ามรันที่กรอกไม่ครบเท่ากัน เดี๋ยวหลอกตัวเอง")
    print("และอย่าเทียบข้าม backend ตรง ๆ — local 8B กับ frontier คนละชั้น (MODEL_EVAL.md §13)")
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `poetry run pytest tests/test_run.py -k backend_from_dirname -v`
Expected: PASS 2 tests

- [ ] **Step 5: Commit**

```bash
git add harness/run.py tests/test_run.py
git commit -m "feat: report แสดงคอลัมน์ backend แยก lane"
```

---

### Task 11: อัปเดตเอกสาร

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: เพิ่มตัวอย่างคำสั่งใน CLAUDE.md**

ในหัวข้อ `## คำสั่ง` เพิ่มสองบรรทัดนี้ต่อท้ายบล็อก bash ที่มีอยู่:

```bash
python harness/run.py run <suite> --backend ollama    รันด้วยโมเดลในเครื่อง ไม่เสียเงิน
python harness/run.py run <suite> --max-tokens 2000   จำกัดความยาวคำตอบ
```

- [ ] **Step 2: อัปเดตหัวข้อสถานะ**

ในหัวข้อ `## สถานะ` เพิ่มบรรทัดต่อจาก `- [x] harness รองรับหลาย suite เทสต์แล้วว่ารันได้`:

```markdown
- [x] harness รองรับ backend `ollama` แล้ว (`--backend ollama`) รันได้โดยไม่ต้องมีเครดิต
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: บันทึก --backend ollama ใน CLAUDE.md"
```

**หมายเหตุ:** `MANUAL.md` ไม่มีบน branch นี้ (อยู่ใน PR #3) — หัวข้อ local backend ใน MANUAL.md ต้องทำหลัง PR #3 merge ตาม spec §7

---

### Task 12: ตรวจรับตามเกณฑ์ของ spec §6

**Files:** ไม่แก้ไฟล์ — เป็นการตรวจ end-to-end

- [ ] **Step 1: รันเคสสั้นที่สุดด้วย ollama จริง**

Run: `poetry run python harness/run.py run catfood --backend ollama --cases e08 --models qwen3:latest`
Expected: ขึ้น `1 งาน — 1 เคส × 1 โมเดล × 1 รอบ [ollama, 1 worker]` แล้วจบด้วย `ok qwen3:latest e08__r1 <วินาที>s`

**หมายเหตุ:** ถ้า branch นี้ยังไม่มี suite `catfood` (อยู่ใน PR #1) ให้ merge PR #1 เข้ามาก่อน หรือ cherry-pick commit `249162b` มาที่ branch นี้เพื่อทดสอบ แล้วค่อยเอาออก

- [ ] **Step 2: ตรวจชื่อโฟลเดอร์และ meta**

Run: `ls results/ | grep ollama && cat results/*ollama*/e08__r1.meta.json`
Expected: โฟลเดอร์ชื่อ `<วันที่>__catfood__ollama__qwen3-latest` และใน meta มีคีย์ `backend: "ollama"` กับ `finish_reason`

- [ ] **Step 3: ตรวจว่า resume ยังทำงาน**

Run: `poetry run python harness/run.py run catfood --backend ollama --cases e08 --models qwen3:latest`
Expected: ขึ้น `skip  qwen3:latest  e08__r1`

- [ ] **Step 4: ตรวจ preflight ตอน tag ผิด**

Run: `poetry run python harness/run.py run catfood --backend ollama --cases e08 --models qwen3:8b`
Expected: จบทันทีด้วยข้อความว่าไม่พบ tag `qwen3:8b` พร้อมไล่ tag ที่มีให้ดู — ไม่มีไฟล์ error รายงาน

- [ ] **Step 5: ตรวจว่า default ยังเป็น openrouter เหมือนเดิม**

Run: `poetry run python harness/run.py run catfood --cases e08`
Expected: พิมพ์ยอดเครดิต `0.0000` แล้วจบด้วยข้อความให้เติมเครดิตหรือใช้ `--backend ollama` (ไม่ยิงงานเลย)

- [ ] **Step 6: ตรวจ report**

Run: `poetry run python harness/run.py report --suite catfood`
Expected: ตารางมีคอลัมน์ `backend` และแถวของรัน ollama แสดงคำว่า `ollama`

- [ ] **Step 7: รันเทสต์ทั้งหมดอีกรอบ**

Run: `poetry run pytest tests/ -v`
Expected: PASS ทุกตัว

- [ ] **Step 8: Commit ผลการตรวจ (ถ้ามีไฟล์ผลลัพธ์ที่ควรเก็บ)**

```bash
git status --short
# ไฟล์ใน results/ ไม่ต้อง commit (.gitignore กันไว้แล้วสำหรับ *.md)
```

---

## Self-review

**ครอบคลุม spec ครบไหม:**

| spec | task |
|---|---|
| §5.1 ตาราง BACKENDS | Task 4 |
| §5.2 DEFAULT_MODELS ต่อ backend + models.json | Task 5 |
| §5.3 concurrency ต่อ backend + timeout เดิม | Task 4 (workers), Task 9 (เอาไปใช้) |
| §5.4 ชื่อโฟลเดอร์ + meta + คอลัมน์ใน report | Task 2, 3, 6, 10 |
| §5.5 preflight ทั้งสองฝั่ง | Task 7, 8 |
| §5.6 max_tokens + finish_reason + เตือนตอนถูกตัด | Task 6 |
| §6 เกณฑ์ตรวจรับ ทั้ง 6 ข้อ | Task 12 |
| §7 เอกสาร | Task 11 (CLAUDE.md; MANUAL.md รอ PR #3) |

**ชื่อฟังก์ชันที่ใช้ข้ามงานตรงกันหมด:** `model_slug`, `run_dir_name`, `run_dir(suite, backend, model)`, `client(backend)`, `resolve_models(suite, backend, override)`, `missing_tags`, `check_ollama`, `check_openrouter`, `backend_from_dirname`, `one_call(cl, suite, case, model, rep, force, backend, max_tokens)`
