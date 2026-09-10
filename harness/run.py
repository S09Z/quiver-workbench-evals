#!/usr/bin/env python3
"""
quiver — สนามซ้อมส่วนตัวสำหรับทดสอบโมเดล

ยิง prompt ชุดเดียวกันไปหลายโมเดล เซฟคำตอบดิบไว้ให้ตรวจเอง
ไม่ผูกกับโดเมนไหน แต่ละโดเมนคือหนึ่ง suite ใต้ suites/

ติดตั้ง:
    pip install openai python-dotenv
    echo "OPENROUTER_API_KEY=sk-or-..." > .env

ใช้งาน:
    python run.py init <ชื่อ suite>            สร้าง suite ใหม่พร้อมเคสตัวอย่าง
    python run.py run <ชื่อ suite>             รันทุกเคสในชุดนั้น
    python run.py run <suite> --cases e03      รันเฉพาะบางเคส
    python run.py run <suite> --repeat 3       รันซ้ำ สำหรับวัด self-consistency
    python run.py report                       สรุปคะแนนทุกรัน

โครงไฟล์:
    suites/<ชื่อ>/SUITE.md          เอกสารอธิบายเคสและเกณฑ์ให้คะแนน
    suites/<ชื่อ>/cases/e01.json    โจทย์ + rubric
    suites/<ชื่อ>/fixtures/         ข้อมูลจริง อ้างจากเคสด้วย {{ชื่อไฟล์}}
    results/2026-09-08__<suite>__<model>/
        e01__r1.md                  คำตอบดิบ
        e01__r1.meta.json           token, เวลาที่ใช้
        scores.json                 คะแนนที่กรอกเอง
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).parent.parent      # run.py อยู่ใน harness/
SUITES_DIR = ROOT / "suites"
RESULTS_DIR = ROOT / "results"

# ---------------------------------------------------------------------------
# เช็ค model id ปัจจุบันที่ https://openrouter.ai/models ก่อนรันจริง
# ชื่อรุ่นเปลี่ยนบ่อยมาก อย่าเชื่อลิสต์นี้โดยไม่ตรวจ
# แต่ละ suite ทับลิสต์นี้ได้ด้วยไฟล์ suites/<ชื่อ>/models.json
# ---------------------------------------------------------------------------
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


def suite_path(name: str) -> Path:
    p = SUITES_DIR / name
    if not p.exists():
        available = [d.name for d in SUITES_DIR.glob("*/")] if SUITES_DIR.exists() else []
        hint = f" มีอยู่: {', '.join(available)}" if available else ""
        sys.exit(f"ไม่พบ suite '{name}'.{hint}")
    return p


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


def load_cases(suite: Path, only=None):
    cases_dir = suite / "cases"
    if not cases_dir.exists():
        sys.exit(f"ไม่มี {cases_dir}")
    cases = []
    for path in sorted(cases_dir.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        case.setdefault("id", path.stem)
        if only and case["id"] not in only:
            continue
        # เคสอ้างไฟล์ fixture ได้ แทนการแปะข้อมูลยาว ๆ ลงใน json
        for name in case.get("fixtures", []):
            text = (suite / "fixtures" / name).read_text(encoding="utf-8")
            case["prompt"] = case["prompt"].replace(f"{{{{{name}}}}}", text)
        cases.append(case)
    if not cases:
        sys.exit("ไม่เจอเคสที่ตรงกับที่ระบุ")
    return cases


def model_slug(model: str) -> str:
    """ชื่อโมเดล -> ชิ้นส่วนชื่อโฟลเดอร์

    '/' -> '__' ตามของเดิม และ ':' -> '-' เพราะ Finder บน macOS แสดง ':' เป็น '/'
    ทำให้ชื่อโฟลเดอร์ของ ollama อ่านสับสน
    """
    return model.replace("/", "__").replace(":", "-")


def run_dir_name(suite_name: str, backend: str, model: str, day: str | None = None) -> str:
    day = day or date.today().isoformat()
    return f"{day}__{suite_name}__{backend}__{model_slug(model)}"


def run_dir(suite_name: str, backend: str, model: str) -> Path:
    d = RESULTS_DIR / run_dir_name(suite_name, backend, model)
    d.mkdir(parents=True, exist_ok=True)
    return d


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


def make_score_stub(out_dir: Path, cases, repeat: int):
    """สร้างแบบฟอร์มให้กรอกคะแนนเอง ไม่ทับของเดิมที่กรอกไปแล้ว"""
    path = out_dir / "scores.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for case in cases:
        for rep in range(1, repeat + 1):
            key = f"{case['id']}__r{rep}"
            if key not in existing:
                existing[key] = {
                    "criteria": {c: None for c in case.get("rubric", [])},
                    "notes": "",
                }
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


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


def cmd_run(args):
    suite = suite_path(args.suite)
    cases = load_cases(suite, args.cases)
    models = resolve_models(suite, args.backend, args.models)

    cl = client(args.backend)

    if args.backend == "ollama":
        check_ollama(models)
    else:
        check_openrouter()

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


def backend_from_dirname(name: str) -> str:
    """รูปแบบใหม่คือ <วันที่>__<suite>__<backend>__<model>
    โฟลเดอร์เก่าที่ยังไม่มีช่อง backend คืน '?' ไปตรง ๆ ดีกว่าเดา"""
    parts = name.split("__")
    if len(parts) >= 4 and parts[2] in BACKENDS:
        return parts[2]
    return "?"


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


EXAMPLE_CASE = {
    "id": "e01",
    "title": "ตัวอย่าง — แทนที่ด้วยเคสจริงของคุณ",
    "temperature": 1.0,
    "fixtures": [],
    "prompt": "เขียนโจทย์จริงที่คุณเคยเจอว่าโมเดลทำพลาดตรงนี้",
    "rubric": [
        "เกณฑ์ข้อ 1 — เขียนให้ตรวจได้ ไม่ใช่ 'คำตอบดี'",
        "เกณฑ์ข้อ 2",
    ],
}

SUITE_README = """# {name}

## ขอบเขต
(ชุดนี้ทดสอบอะไร ทำไมถึงสำคัญกับงานคุณ)

## Failure mode ที่ตั้งใจจับ
1.
2.

## เคส
| id | ทดสอบอะไร | วิธีตรวจ |
|---|---|---|
| e01 | | |

สเกลคะแนนต่อเกณฑ์: 0 = ไม่มี/ผิด, 1 = ตื้นหรือคลุมเครือ, 2 = ถูกและใช้ได้จริง
"""


def cmd_init(args):
    suite = SUITES_DIR / args.suite
    (suite / "cases").mkdir(parents=True, exist_ok=True)
    (suite / "fixtures").mkdir(exist_ok=True)

    readme = suite / "SUITE.md"
    if not readme.exists():
        readme.write_text(SUITE_README.format(name=args.suite), encoding="utf-8")
        print(f"สร้าง  {readme}")

    case_path = suite / "cases" / "e01.json"
    if case_path.exists():
        print(f"มีอยู่แล้ว ข้าม  {case_path}")
    else:
        case_path.write_text(
            json.dumps(EXAMPLE_CASE, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"สร้าง  {case_path}")

    print(f"\nแก้เคสให้ตรงกับงานจริง แล้วรัน `python harness/run.py run {args.suite}`")


def main():
    p = argparse.ArgumentParser(description="quiver — สนามซ้อมทดสอบโมเดล")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="สร้าง suite ใหม่")
    i.add_argument("suite")
    i.set_defaults(func=cmd_init)

    r = sub.add_parser("run", help="รันเคสในชุดหนึ่ง")
    r.add_argument("suite")
    r.add_argument("--cases", nargs="*", help="เช่น e03 e06 (ไม่ใส่ = ทุกเคส)")
    r.add_argument("--models", nargs="*", help="ทับลิสต์โมเดลชั่วคราว")
    r.add_argument("--repeat", type=int, default=1)
    r.add_argument("--force", action="store_true", help="รันทับของเดิม")
    r.add_argument(
        "--backend", choices=sorted(BACKENDS), default="openrouter",
        help="openrouter (default) หรือ ollama สำหรับโมเดลในเครื่อง",
    )
    r.add_argument("--max-tokens", type=int, default=MAX_TOKENS, dest="max_tokens")
    r.set_defaults(func=cmd_run)

    rep = sub.add_parser("report", help="สรุปคะแนน")
    rep.add_argument("--suite", help="กรองเฉพาะชุดเดียว")
    rep.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
