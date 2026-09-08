"""ExecCmds entry wrapper: shut down even if probe preflight fails before its tick loop."""
import json
import runpy
import traceback
from datetime import datetime, timezone
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[1]
try:
    runpy.run_path(str(ROOT / 'Scripts/release_frontend_flight_probe.py'))
except Exception:
    receipt = ROOT / 'SourceAssets/runtime-review/frontend-flight' / (
        'native-probe-setup-failure-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(dict(status='failed_probe_setup', error=traceback.format_exc()), indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
    raise
