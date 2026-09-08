"""Driver for the PilgrimRigV3 native import, one batch per editor launch.

The review helper exposes run(import_assets=..., variants=..., batch=...) for use from the
editor's Python. This wrapper lets the coordinator launch it as a single serial job:

    UnrealEditor.exe <uproject> /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough
        -ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/run_pilgrim_v3_batch.py"
        -unattended -nullrhi -abslog=<unique>

Batch selection by environment variable, so the same file serves all three launches:
    MIKDASH_PILGRIM_BATCH = first | second | third | gate      (default: gate = offline check only)

-ExecutePythonScript is correct here: the helper is synchronous and the editor may exit
when it returns. (The PIE probes need -ExecCmds instead; this is not one of those.)
"""
import json
import os
import runpy
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
HELPER = ROOT / "Scripts" / "release_pilgrim_v3_review.py"
OUT = ROOT / "SourceAssets" / "characters-review" / "PilgrimRigV3"

BATCHES = {
    "gate": dict(),
    "first": dict(import_assets=True, variants=["V3_Pilgrim_Man_Standard"]),
    "second": dict(import_assets=True, batch=4),
    "third": dict(import_assets=True, batch=4),
}

which = os.environ.get("MIKDASH_PILGRIM_BATCH", "gate").strip().lower()
if which not in BATCHES:
    raise SystemExit("MIKDASH_PILGRIM_BATCH must be one of %s" % sorted(BATCHES))

sys.path.insert(0, str(ROOT / "Scripts"))   # sibling imports inside the helper
module = runpy.run_path(str(HELPER))
result = module["run"](**BATCHES[which])

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
summary = {
    "batch": which,
    "stamp": stamp,
    "status": result.get("status") if isinstance(result, dict) else str(result),
    "result": result if isinstance(result, (dict, list)) else str(result),
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / f"batch-driver-{which}-{stamp}.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
print("MIKDASH_PILGRIM_BATCH", json.dumps({"batch": which, "status": summary["status"]}))
