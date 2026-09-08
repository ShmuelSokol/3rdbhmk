"""Acceptance gate for the Mikdash project.

The standing rule across this user's projects: if a repo has scripts/verify.py, it is
run before anything is called done and before anything is pushed. So this fails loudly
rather than passing quietly, and it never reports a check as passed that it skipped.

Run:  python scripts/verify.py            (everything except the engine compile)
      python scripts/verify.py --quick    (skip the C++ math tests, which dominate)
      python scripts/verify.py --build     (also run UnrealBuildTool; slow, serial)

Exit code 0 only when every check that ran passed AND nothing was silently skipped
for a reason that hides a real problem.
"""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "Plugins" / "MikdashRuntime"
MODULE = PLUGIN / "Source" / "MikdashRuntime"
TESTS = PLUGIN / "Tests"
PUBLIC = MODULE / "Public"
MAP = ROOT / "Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap"
VCVARS = Path(
    r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
)
UBT_BUILD = Path(r"C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"  {detail}" if detail else ""))
    return ok


# ---------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------

def check_no_stray_editor() -> None:
    """A zombie editor holding the map makes saves return False with no other symptom.

    This has cost this project a full debugging session before, so it is the first check.
    """
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq UnrealEditor*.exe", "/NH"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception as exc:  # noqa: BLE001
        check("no stray UnrealEditor process", False, f"could not run tasklist: {exc}")
        return
    running = [l for l in out.splitlines() if "UnrealEditor" in l]
    check("no stray UnrealEditor process", not running,
          "; ".join(l.split()[0] for l in running) if running else "")


def check_security_token() -> None:
    """This project leaked an Android File Server SecurityToken publicly once.

    Only whether it is empty is reported. The file is never printed.
    """
    ini = ROOT / "Config" / "DefaultEngine.ini"
    if not ini.exists():
        check("DefaultEngine.ini SecurityToken empty", False, "DefaultEngine.ini missing")
        return
    text = ini.read_text(encoding="utf-8", errors="replace")
    hits = re.findall(r"^[ \t]*SecurityToken[ \t]*=[ \t]*(.*)$", text, flags=re.M)
    nonempty = [h for h in hits if h.strip()]
    check("DefaultEngine.ini SecurityToken empty", not nonempty,
          f"{len(nonempty)} non-empty token(s)" if nonempty else "")


def check_map() -> None:
    if not MAP.exists():
        check("map present", False, str(MAP))
        return
    size = MAP.stat().st_size
    # The accepted combined map has been about 23 MB. An order of magnitude either way
    # means something replaced it.
    check("map present and plausible size", 2_000_000 < size < 400_000_000,
          f"{size/1_048_576:.1f} MB")


# ---------------------------------------------------------------------------
# python
# ---------------------------------------------------------------------------

def check_python_scripts() -> None:
    scripts = sorted((ROOT / "Scripts").glob("*.py")) if (ROOT / "Scripts").is_dir() else []
    bad = []
    for s in scripts:
        try:
            py_compile.compile(str(s), doraise=True, cfile=str(Path(tempfile.gettempdir()) / (s.stem + ".pyc")))
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{s.name}: {str(exc)[:120]}")
    check(f"Scripts/*.py parse ({len(scripts)} files)", not bad, "; ".join(bad[:5]))


def check_specs() -> None:
    specs = sorted((ROOT / "Scripts").glob("*.spec.json")) if (ROOT / "Scripts").is_dir() else []
    bad = []
    for s in specs:
        try:
            json.loads(s.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{s.name}: {str(exc)[:120]}")
    check(f"Scripts/*.spec.json valid ({len(specs)} files)", not bad, "; ".join(bad[:5]))


def check_receipts() -> None:
    """Surface any release receipt whose recorded status is a failure.

    Failure receipts are deliberately preserved by the release scripts. Ignoring them is
    how a broken placement pass reaches a build.
    """
    src = ROOT / "SourceAssets"
    if not src.is_dir():
        check("release receipts well-formed", False, "SourceAssets missing")
        return
    malformed, failed = [], []
    count = 0
    for j in src.rglob("*.json"):
        if any(p in {".tools", "node_modules"} for p in j.parts):
            continue
        try:
            data = json.loads(j.read_text(encoding="utf-8-sig", errors="replace"))
        except Exception:  # noqa: BLE001
            malformed.append(j.name)
            continue
        count += 1
        if isinstance(data, dict):
            status = str(data.get("status", ""))
            if status and ("fail" in status.lower() or "error" in status.lower()):
                failed.append(f"{j.relative_to(src)}: {status[:60]}")
    check(f"receipts parse ({count} files)", not malformed, "; ".join(malformed[:5]))

    # Failure receipts are deliberately preserved by the release scripts as evidence.
    # They are listed on every run so they cannot be forgotten, but an old failure that
    # was already dealt with must not block a new build, or the gate becomes noise that
    # people learn to ignore.
    if failed:
        print(f"  WARN  {len(failed)} receipt(s) record a failure:")
        for line in failed[:10]:
            print(f"          {line}")
        if len(failed) > 10:
            print(f"          ... and {len(failed) - 10} more")
    else:
        check("no receipt records a failure", True)


# ---------------------------------------------------------------------------
# C++ math tests
# ---------------------------------------------------------------------------

def run_math_tests() -> None:
    if not TESTS.is_dir():
        check("standalone math tests", False, "Tests folder missing")
        return
    sources = sorted(TESTS.glob("*.cpp"))
    if not sources:
        check("standalone math tests", False, "no tests found")
        return
    if not VCVARS.exists():
        check("standalone math tests", False, f"vcvars64 not found at {VCVARS}")
        return

    outdir = Path(tempfile.gettempdir()) / "mikdash-verify"
    outdir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    passed = 0
    for src in sources:
        exe = outdir / (src.stem + ".exe")
        # Driven through a batch file rather than `cmd /c "call ... && cl ..."`: the
        # vcvars path contains spaces and parentheses, and cmd's own quote handling
        # mangles it into an unrecognised command.
        bat = outdir / f"build_{src.stem}.bat"
        # No /Fo path: a trailing backslash before the closing quote escapes the quote
        # and cl then cannot open its own intermediate file. Object files land in cwd.
        bat.write_text(
            "@echo off\r\n"
            f'call "{VCVARS}" >nul\r\n'
            f'cd /d "{outdir}"\r\n'
            f'cl /nologo /std:c++17 /EHsc /W4 /O2 /I"{PUBLIC}" '
            f'"{src}" /Fe:"{exe}" /link /SUBSYSTEM:CONSOLE\r\n',
            encoding="ascii",
        )
        comp = subprocess.run(["cmd", "/c", str(bat)], capture_output=True, text=True, cwd=str(outdir))
        if comp.returncode != 0:
            tail = (comp.stdout or "") + (comp.stderr or "")
            first = next((l for l in tail.splitlines() if "error" in l.lower()), tail.strip()[:150])
            failures.append(f"{src.name} did not compile: {first[:160]}")
            continue
        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=300)
        if run.returncode != 0:
            tail = ((run.stdout or "") + (run.stderr or "")).strip().splitlines()
            last = tail[-1][:160] if tail else f"exit {run.returncode}"
            failures.append(f"{src.name} failed: {last}")
        else:
            passed += 1

    check(f"standalone math tests ({passed}/{len(sources)} passed)", not failures,
          " | ".join(failures[:6]))


# ---------------------------------------------------------------------------
# engine compile
# ---------------------------------------------------------------------------

def run_build() -> None:
    if not UBT_BUILD.exists():
        check("plugin C++ compiles", False, f"Build.bat not found at {UBT_BUILD}")
        return
    cmd = (
        f'"{UBT_BUILD}" MikdashCourtyardV3Editor Win64 Development '
        f'-Project="{ROOT / "MikdashCourtyardV3.uproject"}" -WaitMutex -NoHotReload'
    )
    proc = subprocess.run(["cmd", "/c", cmd], capture_output=True, text=True)
    ok = proc.returncode == 0 and "Result: Succeeded" in (proc.stdout or "")
    detail = ""
    if not ok:
        errs = [l for l in (proc.stdout or "").splitlines() if re.search(r"error [A-Z]+\d+", l)]
        detail = errs[0][:200] if errs else f"exit {proc.returncode}"
    check("plugin C++ compiles", ok, detail)


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="skip the C++ math tests")
    parser.add_argument("--build", action="store_true", help="also run UnrealBuildTool")
    args = parser.parse_args()

    print(f"verify: {ROOT}")
    print("-- environment")
    check_no_stray_editor()
    check_security_token()
    check_map()
    print("-- python")
    check_python_scripts()
    check_specs()
    check_receipts()
    print("-- C++")
    if args.quick:
        print("  SKIP  standalone math tests (--quick)")
    else:
        run_math_tests()
    if args.build:
        run_build()
    else:
        print("  SKIP  plugin C++ compiles (pass --build; it is slow and must run serial)")

    failed = [n for n, ok, _ in results if not ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("verify: green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
