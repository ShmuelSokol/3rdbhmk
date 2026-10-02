"""Offline source/build verification; no native process or network service."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    paths = [ROOT/name for name in ('session_core.py','test_session_core.py','README.md','validate.py','upstream-lock.json')]
    for directory in ('signalling','browser','native','adapters'):
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file()
                     and p.suffix in ('.mjs','.py','.h','.cpp','.md','.html','.json') and not p.name.startswith('receipt'))
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(paths)}


def command(args):
    try:
        p = subprocess.run(args,cwd=str(ROOT),capture_output=True,encoding='utf-8',errors='replace',timeout=60)
        return p.returncode, p.stdout
    except Exception:
        return -1, ''  # never store process exception text or captured stderr


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',required=True)
    parser.add_argument('--receipt',required=True)
    args=parser.parse_args()
    dest=Path(args.receipt).resolve()
    if dest.exists():parser.error('Choose a fresh receipt path')
    before=hashes()
    core_receipt=json.loads((ROOT/'receipt-time-validation-v2.json').read_text())
    core_unchanged=all(digest(ROOT/p)==h for p,h in core_receipt['fileSha256'].items())
    groups={}
    for module in ('test_session_core','adapters.test_bridge','adapters.test_loopback_channel','native.test_source_contract'):
        suite=unittest.defaultTestLoader.loadTestsFromName(module)
        result=unittest.TextTestRunner(stream=io.StringIO(),verbosity=0).run(suite)
        groups[module]={'tests':result.testsRun,'passed':result.wasSuccessful() and not result.skipped,
                        'failures':len(result.failures),'errors':len(result.errors)}
    rc, output=command(['node','--test','--test-reporter=tap','signalling/gateway.test.mjs','browser/controls.test.mjs'])
    count=re.search(r'^# tests (\d+)$',output,re.MULTILINE)
    passed=re.search(r'^# pass (\d+)$',output,re.MULTILINE)
    js_ok=rc==0 and count is not None and passed is not None and int(count[1])==int(passed[1])>0
    build_rc,_=command(['node','adapters/build.mjs',str(Path(args.cache).resolve())])
    after=hashes()
    ok=core_unchanged and before==after and js_ok and build_rc==0 and all(g['passed'] for g in groups.values())
    receipt={'status':'offline-source-slice-passed' if ok else 'offline-source-slice-failed',
        'createdUtc':datetime.now(timezone.utc).isoformat(), 'coreUnchanged':core_unchanged,
        'pythonGroups':groups,'javascriptTests':int(count[1]) if count else 0,'javascriptPassed':bool(js_ok),
        'browserBundleBuilt':build_rc==0,'sourceStable':before==after,'fileSha256':after,
        'upstreamCommit':'6b8cfb460bda09703e85178f1f77aa6faec9e890',
        'nativeCompiled':False,'nativeExecuted':False,'socketsOpenedForTests':0,
        'listenersStarted':0,'productionConfigChanged':False,'publicationPerformed':False,
        'endToEndWalkthroughAccepted':False,'secretsStored':False,
        'limits':['Native checks are source assertions, not compiled/runtime tests',
                  'Loopback client tests replace socket creation; receiver is unimplemented',
                  'Native process/bootstrap/clock handshake and Node-Python host wiring absent',
                  'Authenticated browser admission/upgrade endpoints absent',
                  'No first-frame, independent-native-session, desktop/mobile usability or online acceptance']}
    if build_rc==0:
        receipt['bundle']=json.loads((Path(args.cache)/'out/build-result.json').read_text())
    engine=Path('C:/Program Files/Epic Games/UE_5.8/Engine')
    evidence=['Build/Build.version',
        'Plugins/Media/PixelStreaming2/Source/PixelStreaming2Input/Public/IPixelStreaming2InputHandler.h',
        'Plugins/Media/PixelStreaming2/Source/PixelStreaming2Input/Private/PixelStreaming2DefaultDataProtocol.cpp',
        'Plugins/Media/PixelStreaming2/Source/PixelStreaming2RTC/Private/EpicRtcStreamer.cpp',
        'Plugins/Media/PixelStreaming2/Source/PixelStreaming2RTC/Private/RTCInputHandler.cpp',
        'Source/Runtime/Engine/Private/PlayerController.cpp',
        'Source/Runtime/Engine/Private/UserInterface/PlayerInput.cpp']
    receipt['installedEngineEvidenceSha256']={p:digest(engine/p) for p in evidence}
    with dest.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print('{}; Python checks={}; JS checks={}; core unchanged={}'.format(receipt['status'],
        sum(g['tests'] for g in groups.values()),receipt['javascriptTests'],core_unchanged))
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main())
