"""Compile and test the actual standalone crowd header; no Unreal or map writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "SourceAssets/runtime-review/resident-crowd"
HEADER = ROOT / "Plugins/MikdashRuntime/Source/MikdashRuntime/Public/ResidentCrowdRuntime.h"
TEST = REVIEW / "ResidentCrowdRuntimeTest.cpp"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vcvars", type=Path, help="Explicit installed vcvars64.bat")
    args = parser.parse_args()
    candidates = [args.vcvars] if args.vcvars else []
    if not candidates:
        for base in ("ProgramFiles(x86)", "ProgramFiles"):
            root = Path(os.environ.get(base, "C:/Program Files")) / "Microsoft Visual Studio"
            candidates.extend(sorted(root.glob("*/BuildTools/VC/Auxiliary/Build/vcvars64.bat"), reverse=True))
    vcvars = next((p for p in candidates if p and p.is_file()), None)
    if not vcvars:
        raise SystemExit("No installed vcvars64.bat found; pass --vcvars. No toolchain download attempted.")
    environment = subprocess.run('cmd.exe /d /s /c ""{}" >nul && set"'.format(vcvars),
                                 capture_output=True, text=True, timeout=90, check=True)
    env = {k.upper(): v for k, v in os.environ.items()}
    env.update((k.upper(), v) for k, v in (line.split("=", 1) for line in environment.stdout.splitlines()
               if "=" in line and not line.startswith("=")))
    compiler = shutil.which("cl.exe", path=env.get("PATH", ""))
    if not compiler:
        raise SystemExit("Installed vcvars did not expose cl.exe")
    receipt = {"utc": datetime.now(timezone.utc).isoformat(), "status": "FAILED",
               "vcvars": str(vcvars), "scope": "Standalone actual C++14 module only; no Unreal/runtime/visual acceptance",
               "inputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (HEADER, TEST)},
               "runs": []}
    with tempfile.TemporaryDirectory(prefix="mikdash-crowd-") as temp:
        work = Path(temp)
        for name, flags in (("debug", ["/Od"]), ("release", ["/O2", "/DNDEBUG"])):
            exe = work / (name + ".exe")
            command = [compiler, "/nologo", "/std:c++14", "/EHsc", "/W4", "/WX", "/utf-8"] + flags + [
                "/I" + str(HEADER.parent), str(TEST), "/Fe:" + str(exe), "/Fo:" + str(work / (name + ".obj"))]
            build = subprocess.run(command, env=env, cwd=work, capture_output=True, text=True, timeout=120)
            row = {"configuration": name, "compiler_flags": flags + ["/std:c++14", "/W4", "/WX"],
                   "compile_exit": build.returncode, "compile_output": build.stdout + build.stderr}
            receipt["runs"].append(row)
            if build.returncode == 0:
                result = subprocess.run([str(exe), str(work / "snapshot.txt")], cwd=work,
                                        capture_output=True, text=True, timeout=30)
                row.update(test_exit=result.returncode, test_output=result.stdout + result.stderr)
            if row.get("test_exit", 1) != 0:
                break
    if len(receipt["runs"]) == 2 and all(r.get("test_exit") == 0 for r in receipt["runs"]):
        receipt["status"] = "PASS"
    REVIEW.mkdir(parents=True, exist_ok=True)
    output = REVIEW / "standalone-tests.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
