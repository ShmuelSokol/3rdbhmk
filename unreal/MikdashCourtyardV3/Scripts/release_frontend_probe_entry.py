"""ExecCmds entry wrapper: shut down even if probe preflight fails before its tick loop."""
import json
import runpy
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
sanctuary = '-sanctuarywalkprobe' in unreal.SystemLibrary.get_command_line().lower().split()
platform = '-platformwalkprobe' in unreal.SystemLibrary.get_command_line().lower().split()
probe_name = 'release_sanctuary_walk_probe.py' if sanctuary else 'release_walk_probe.py' if platform else 'release_frontend_flight_probe.py'
try:
    if sanctuary and platform: raise RuntimeError('Choose one walking probe')
    runpy.run_path(str(ROOT / 'Scripts' / probe_name))
except Exception:
    receipt = ROOT / 'SourceAssets/runtime-review/frontend-flight' / (
        'native-probe-setup-failure-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    try:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(dict(status='failed_probe_setup', probe=probe_name, error=traceback.format_exc()), indent=2), encoding='utf-8')
    finally:
        unreal.SystemLibrary.quit_editor()
    raise
