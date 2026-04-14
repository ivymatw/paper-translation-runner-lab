#!/Library/Developer/CommandLineTools/usr/bin/python3
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import fitz


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_warning_reasons(text: str) -> list[str]:
    return re.findall(r"Falling back to degraded translation output due to validation failure: ([^\n]+)", text or "")


def extract_error_reasons(text: str) -> list[str]:
    return re.findall(r"Invalid translation output after retries: ([^\n]+)", text or "")


def page_dir_for(root: Path, page: int) -> Path:
    return root / "pages" / f"page-{page:02d}"


def mono_path_for(page_dir: Path, stem: str) -> Path:
    return page_dir / f"{stem}-mono.pdf"


def dual_path_for(page_dir: Path, stem: str) -> Path:
    return page_dir / f"{stem}-dual.pdf"


def run_page(args, page: int, out_root: Path, stem: str, events_path: Path, manifest: dict) -> dict:
    page_dir = page_dir_for(out_root, page)
    mono_path = mono_path_for(page_dir, stem)
    dual_path = dual_path_for(page_dir, stem)
    logs_dir = out_root / "logs"
    ensure_dir(logs_dir)
    page_log_path = logs_dir / f"page-{page:02d}.log"

    existing = manifest["pages"].get(str(page))
    if mono_path.exists() and existing and existing.get("status") in {"pass", "degraded_pass", "failed_hard_source_passthrough"}:
        append_jsonl(events_path, {
            "ts": iso_now(),
            "event": "page_reused",
            "page": page,
            "status": existing.get("status"),
            "mono_path": str(mono_path),
        })
        return existing

    if page_dir.exists():
        for child in page_dir.glob("*"):
            if child.is_file():
                child.unlink()
            else:
                import shutil
                shutil.rmtree(child)
    ensure_dir(page_dir)

    cmd = [
        "/Library/Developer/CommandLineTools/usr/bin/python3",
        "-m",
        "pdf2zh.pdf2zh",
        str(args.src),
        "--service",
        args.service,
        "--lang-in",
        args.lang_in,
        "--lang-out",
        args.lang_out,
        "--pages",
        str(page),
        "--output",
        str(page_dir),
        "-t",
        str(args.thread),
    ]

    env = os.environ.copy()
    env["OPENAI_BASE_URL"] = args.openai_base_url
    env["OPENAI_API_KEY"] = args.openai_api_key
    env["OPENAI_MODEL"] = args.openai_model

    started = time.time()
    append_jsonl(events_path, {
        "ts": iso_now(),
        "event": "page_start",
        "page": page,
        "command": shlex.join(cmd),
    })
    proc = subprocess.run(cmd, cwd=str(args.workdir), env=env, capture_output=True, text=True)
    finished = time.time()
    combined = (proc.stdout or "") + (proc.stderr or "")
    page_log_path.write_text(combined, encoding="utf-8")

    warning_reasons = extract_warning_reasons(combined)
    error_reasons = extract_error_reasons(combined)

    if mono_path.exists():
        status = "degraded_pass" if warning_reasons else "pass"
    else:
        status = "failed_hard_source_passthrough"

    record = {
        "page": page,
        "status": status,
        "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(),
        "finished_at": datetime.fromtimestamp(finished, timezone.utc).isoformat(),
        "duration_seconds": round(finished - started, 3),
        "exit_code": proc.returncode,
        "mono_exists": mono_path.exists(),
        "dual_exists": dual_path.exists(),
        "mono_path": str(mono_path) if mono_path.exists() else None,
        "dual_path": str(dual_path) if dual_path.exists() else None,
        "log_path": str(page_log_path),
        "warning_reasons": warning_reasons,
        "error_reasons": error_reasons,
        "fallback_strategy": None,
    }

    if status == "failed_hard_source_passthrough":
        record["fallback_strategy"] = "original_page_passthrough"
    elif status == "degraded_pass":
        record["fallback_strategy"] = "translator_level_degraded_output"

    manifest["pages"][str(page)] = record
    append_jsonl(events_path, {
        "ts": iso_now(),
        "event": "page_done",
        **record,
    })
    return record


def merge_output(args, out_root: Path, stem: str, manifest: dict, events_path: Path) -> Path:
    merged = fitz.open()
    src_doc = fitz.open(str(args.src))
    for page in range(1, manifest["page_count"] + 1):
        rec = manifest["pages"].get(str(page))
        if rec and rec.get("mono_exists") and rec.get("mono_path"):
            page_doc = fitz.open(rec["mono_path"])
            merged.insert_pdf(page_doc, from_page=page - 1, to_page=page - 1)
            source = "translated_page"
        else:
            merged.insert_pdf(src_doc, from_page=page - 1, to_page=page - 1)
            source = "original_page_passthrough"
        append_jsonl(events_path, {
            "ts": iso_now(),
            "event": "merge_page",
            "page": page,
            "source": source,
        })
    merged_path = out_root / f"{stem}-mono.pdf"
    merged.save(str(merged_path))
    return merged_path


def summarize(manifest: dict) -> dict:
    counts = {"pass": 0, "degraded_pass": 0, "failed_hard_source_passthrough": 0}
    total_duration = 0.0
    for rec in manifest["pages"].values():
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        total_duration += rec.get("duration_seconds", 0.0)
    return {
        "page_status_counts": counts,
        "total_page_runtime_seconds": round(total_duration, 3),
    }


def main():
    default_workdir = Path("/Users/ivyma/obsidian/Max-Docs/llm-ccp-propaganda")
    default_src = default_workdir / "papers/2602.06371_Bilingual_Bias_in_LLMs_Taiwan_Sovereignty.pdf"
    default_out = default_workdir / "pdf2zh-minimax-full1-by-page"

    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=default_src)
    ap.add_argument("--out", type=Path, default=default_out)
    ap.add_argument("--workdir", type=Path, default=default_workdir)
    ap.add_argument("--service", default="openai")
    ap.add_argument("--lang-in", default="en")
    ap.add_argument("--lang-out", default="zh-TW")
    ap.add_argument("--thread", type=int, default=1)
    ap.add_argument("--openai-base-url", default="http://127.0.0.1:8091/v1")
    ap.add_argument("--openai-api-key", default="dummy")
    ap.add_argument("--openai-model", default="MiniMax-M2.7-UD-Q5_K_M-00001-of-00005.gguf")
    ap.add_argument("--start-page", type=int, default=1)
    ap.add_argument("--end-page", type=int, default=None)
    args = ap.parse_args()

    args.src = args.src.expanduser().resolve()
    args.out = args.out.expanduser().resolve()
    args.workdir = args.workdir.expanduser().resolve()
    ensure_dir(args.out)
    ensure_dir(args.out / "pages")
    ensure_dir(args.out / "logs")

    stem = args.src.stem
    page_count = fitz.open(str(args.src)).page_count
    end_page = args.end_page or page_count

    manifest_path = args.out / "run-manifest.json"
    events_path = args.out / "run-events.jsonl"
    errors_path = args.out / "error-log.jsonl"

    manifest = read_json(manifest_path, {
        "runner": "run_pdf2zh_by_page.py",
        "version": 1,
        "started_at": iso_now(),
        "source_pdf": str(args.src),
        "output_root": str(args.out),
        "page_count": page_count,
        "config": {
            "service": args.service,
            "lang_in": args.lang_in,
            "lang_out": args.lang_out,
            "thread": args.thread,
            "openai_base_url": args.openai_base_url,
            "openai_model": args.openai_model,
        },
        "pages": {},
    })
    manifest["page_count"] = page_count
    write_json(manifest_path, manifest)

    for page in range(args.start_page, end_page + 1):
        rec = run_page(args, page, args.out, stem, events_path, manifest)
        if rec["status"] != "pass":
            append_jsonl(errors_path, {
                "ts": iso_now(),
                "page": page,
                "status": rec["status"],
                "warning_reasons": rec.get("warning_reasons", []),
                "error_reasons": rec.get("error_reasons", []),
                "fallback_strategy": rec.get("fallback_strategy"),
                "log_path": rec.get("log_path"),
            })
        write_json(manifest_path, manifest)

    merged_path = merge_output(args, args.out, stem, manifest, events_path)
    manifest["merged_mono_pdf"] = str(merged_path)
    manifest["completed_at"] = iso_now()
    manifest["summary"] = summarize(manifest)
    write_json(manifest_path, manifest)
    print(str(merged_path))


if __name__ == "__main__":
    main()
