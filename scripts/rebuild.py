"""Rebuild and verify AccelScope from source on Ubuntu/WSL."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DESIGNS = (
    ("sequential", "accelscope_seq", "seq", "test_seq.cpp"),
    ("parallel", "accelscope_parallel", "parallel", "test_parallel.cpp"),
)


def run(label: str, command: list[str], *, log_name: str | None = None) -> None:
    print(f"\n{label}", flush=True)
    env = os.environ.copy()
    src = str(ROOT / "src")
    old_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src + (os.pathsep + old_path if old_path else "")
    if log_name is None:
        subprocess.run(command, cwd=ROOT, env=env, check=True)
        return
    log = ROOT / "build" / "logs" / log_name
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            command, cwd=ROOT, env=env, stdout=stream,
            stderr=subprocess.STDOUT, check=False,
        )
    if result.returncode:
        print(log.read_text(encoding="utf-8", errors="replace")[-12000:])
        raise RuntimeError(f"{label} failed. Full log: {log}")
    print(f"Passed. Log: {log.relative_to(ROOT)}", flush=True)


def main() -> int:
    missing = [name for name in ("verilator", "yosys", "g++", "make")
               if shutil.which(name) is None]
    if missing:
        raise RuntimeError("Missing tools: " + ", ".join(missing)
                           + ". Install the Ubuntu prerequisites in README.md.")
    required = ["scripts/generate_vectors.py", "scripts/compare_architectures.py",
                "src/accelscope/reference.py", "src/accelscope/selector.py",
                "tests/test_reference.py", "tests/test_selector.py"]
    for _, top, _, bench in DESIGNS:
        required.extend((f"rtl/{top}.v", f"sim/{bench}"))
    absent = [name for name in required if not (ROOT / name).is_file()]
    if absent:
        raise RuntimeError("Missing project files: " + ", ".join(absent))

    print("AccelScope: rebuild and verify", flush=True)
    run("Verilator version", ["verilator", "--version"])
    run("Yosys version", ["yosys", "-V"])
    run("Python tests", [sys.executable, "-m", "unittest", "discover",
                         "-s", "tests", "-v"])
    run("Generate deterministic reference vectors",
        [sys.executable, "scripts/generate_vectors.py"])
    for name, top, folder, bench in DESIGNS:
        rtl = f"rtl/{top}.v"
        run(f"Lint {name}", ["verilator", "--lint-only", "--Wall",
                              "--top-module", top, rtl])
        obj = ROOT / "build" / folder / "obj"
        # Only disposable simulator outputs are removed; source files stay intact.
        if obj.exists():
            shutil.rmtree(obj)
        obj.parent.mkdir(parents=True, exist_ok=True)
        run(f"Build {name}", ["verilator", "--cc", "--exe", "--build",
            "--Wall", "--top-module", top, "--Mdir", str(obj),
            "-CFLAGS", "-std=c++17", rtl, str(ROOT / "sim" / bench)],
            log_name=f"build-{name}.log")
    run("Verify both designs and regenerate synthesis evidence",
        [sys.executable, "scripts/compare_architectures.py"])
    print("\nRebuild passed. Report: reports/architecture-comparison.json")
    print("Launch: python -m streamlit run app/main.py --server.address 127.0.0.1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nRebuild failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
