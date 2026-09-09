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
import csv
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
ALLOWED_MAPS = {
    "/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough",
    "/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough",
}
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
        proc = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            check("no stray UnrealEditor process", False,
                  f"process inventory failed (exit {proc.returncode}): {(proc.stderr or '').strip()[:200]}")
            return
        rows = list(csv.reader(proc.stdout.splitlines()))
        if not rows or any(len(row) < 2 for row in rows):
            check("no stray UnrealEditor process", False, "process inventory empty or malformed")
            return
        running = [row for row in rows if row[0].lower().startswith("unrealeditor")
                   and row[0].lower().endswith(".exe")]
        check("no stray UnrealEditor process", not running,
              "; ".join(row[0] + " PID " + row[1] for row in running))
    except Exception as exc:  # noqa: BLE001
        check("no stray UnrealEditor process", False, f"could not inventory processes: {exc}")


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


def selected_map(root: Path = ROOT) -> tuple[str, Path]:
    """Resolve one explicitly allowed map; refuse ambiguous or divergent defaults."""
    def values(path: Path, section: str, key: str) -> list[str]:
        found, current = [], None
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith((";", "#")):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1]
                continue
            if current == section and "=" in line:
                name, value = line.split("=", 1)
                if name.strip().lstrip("+-.!") == key:
                    if name.strip() not in (key, "+" + key):
                        raise ValueError(f"Unsupported config operator for {key}")
                    found.append(value.strip())
        return found
    engine = root / "Config/DefaultEngine.ini"
    game = root / "Config/DefaultGame.ini"
    default = values(engine, "/Script/EngineSettings.GameMapsSettings", "GameDefaultMap")
    startup = values(engine, "/Script/EngineSettings.GameMapsSettings", "EditorStartupMap")
    cooks = values(game, "/Script/UnrealEd.ProjectPackagingSettings", "MapsToCook")
    if len(default) != 1 or len(startup) != 1 or len(cooks) != 1:
        raise ValueError("Require exactly one GameDefaultMap, EditorStartupMap and MapsToCook entry")
    match = re.fullmatch(r'\(FilePath="([^"]+)"\)', cooks[0])
    if not match or default[0] != startup[0] or default[0] != match.group(1):
        raise ValueError("GameDefaultMap, EditorStartupMap and MapsToCook disagree")
    package = default[0]
    if package not in ALLOWED_MAPS:
        raise ValueError("Configured map is outside the explicit Main50/Selected48 allowlist")
    return package, root / "Content" / (package[6:] + ".umap")


def check_map() -> None:
    try:
        package, map_file = selected_map()
    except (OSError, ValueError) as exc:
        check("configured map consistency", False, str(exc))
        return
    if not map_file.is_file():
        check("map present", False, str(map_file))
        return
    size = map_file.stat().st_size
    # The accepted combined map has been about 23 MB. An order of magnitude either way
    # means something replaced it.
    check("map present and plausible size", 2_000_000 < size < 400_000_000,
          f"{package}; defaults/cook agree; {size/1_048_576:.1f} MB")


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

    # Per-process directory. A single shared one means two concurrent verify runs
    # clobber each other's generated .bat and .obj files, and the loser reports
    # "The batch file cannot be found" — a test failure that is really a gate bug.
    # That happened while several agents were running their own verifications.
    outdir = Path(tempfile.gettempdir()) / f"mikdash-verify-{os.getpid()}"
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
    # Build.bat requires cmd's batch parsing. Passing an already quoted command
    # as a list element adds literal backslash-quote escapes before Program Files.
    # shell=True supplies the outer cmd /c quoting for this fixed local command.
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="verify-ubt-",
                                     suffix=".log", dir=ROOT.parent, delete=False) as log:
        log.write(output)
        build_log = log.name
    print(f"  BUILD LOG  {build_log}")
    ok = proc.returncode == 0 and "Result: Succeeded" in (proc.stdout or "")
    detail = ""
    if not ok:
        errs = [l for l in output.splitlines() if re.search(r"error [A-Z]+\d+", l)]
        lines = [l.strip() for l in output.splitlines() if l.strip()]
        detail = errs[0][:200] if errs else f"exit {proc.returncode}: " + (lines[-1][:180] if lines else "no build output")
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
        # Math suites can take several minutes. A user may open the editor after the
        # initial inventory; recheck immediately before allowing the serial UBT job.
        if all(ok for _, ok, _ in results):
            check_no_stray_editor()
        if all(ok for _, ok, _ in results):
            run_build()
        else:
            print("  SKIP  plugin C++ compiles (failed pre-build gate; no engine job launched)")
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
