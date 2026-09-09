"""Run several release scripts inside ONE editor session.

Why this exists: loading this map costs several GB and a minute or more, because it pulls
in 11,437 city buildings, 256 terrain tiles and the whole Temple. Launching one editor per
release script pays that cost once per script, and on a 16 GB machine each launch is a
chance for the memory guard to kill the editor mid-job. One editor, many scripts, pays it
once.

Each script runs in its own namespace with its own try/except, so one refusal does not stop
the rest — every script in this project already guards itself and writes its own receipt.
A per-script summary lands in SourceAssets/build-review/batch-<stamp>.json.

    set MIKDASH_BATCH=release_soundscape_v2.py,release_sky_tod.py
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -unattended -nullrhi
        -script=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/run_batch.py
        -abslog=<unique>

Names are resolved inside Scripts/ only, and anything outside it is refused: this runs
whatever it is handed, so it must never be handed a path.
"""
import json
import os
import runpy
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
SCRIPTS = ROOT / "Scripts"
OUT = ROOT / "SourceAssets" / "build-review"

import unreal as ue

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
requested = [n.strip() for n in os.environ.get("MIKDASH_BATCH", "").split(",") if n.strip()]
report = {"status": "started", "stamp": stamp, "requested": requested, "results": []}

sys.path.insert(0, str(SCRIPTS))  # sibling imports (release_place_assets and friends)

try:
    if not requested:
        raise RuntimeError("MIKDASH_BATCH is empty; give a comma-separated list of script names")

    for name in requested:
        entry = {"script": name}
        started = time.time()
        try:
            if "/" in name or "\\" in name or not name.endswith(".py"):
                raise RuntimeError("names only, no paths: %r" % name)
            path = (SCRIPTS / name).resolve()
            if path.parent != SCRIPTS.resolve() or not path.exists():
                raise RuntimeError("not a script in Scripts/: %r" % name)

            ue.log("MIKDASH_BATCH_BEGIN " + name)
            runpy.run_path(str(path), run_name="__main__")
            entry["outcome"] = "ran"
        except SystemExit as exc:                    # a script choosing to stop is not a crash
            entry["outcome"] = "system_exit"
            entry["code"] = getattr(exc, "code", None)
        except Exception as exc:                     # noqa: BLE001 - one refusal must not stop the rest
            entry["outcome"] = "raised"
            entry["error"] = str(exc) or repr(exc)
            entry["traceback"] = traceback.format_exc()[-1500:]
        entry["seconds"] = round(time.time() - started, 1)
        report["results"].append(entry)
        ue.log("MIKDASH_BATCH_END " + json.dumps({k: entry.get(k) for k in ("script", "outcome", "seconds", "error")}))

    ran = sum(1 for r in report["results"] if r["outcome"] == "ran")
    report["status"] = "batch_complete_%d_of_%d_ran_without_raising" % (ran, len(report["results"]))
except Exception as exc:  # noqa: BLE001
    report.update(status="batch_failed", error=str(exc) or repr(exc))
finally:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"batch-{stamp}.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    ue.log("MIKDASH_BATCH " + json.dumps({"status": report["status"],
                                          "results": [{k: r.get(k) for k in ("script", "outcome")} for r in report["results"]]}))
