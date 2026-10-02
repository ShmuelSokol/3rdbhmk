"""Receiver03 offline-only checks; frozen Source02 bytes are mandatory invariants."""
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

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def source_hashes():
    files=[ROOT/'adapters'/p for p in ('receiver03_bootstrap.py','test_receiver03_bootstrap.py','validate_receiver03.py')]
    files += [p for p in (ROOT/'native/receiver03').iterdir() if p.is_file() and not p.name.startswith('receipt')]
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',required=True)
    dest=Path(parser.parse_args().receipt).resolve()
    if dest.exists():parser.error('Choose a fresh receipt path')
    frozen_path=ROOT/'adapters/receipt-real-stream-source-02.json'
    frozen= json.loads(frozen_path.read_text())['fileSha256']
    frozen_receipt_hash=sha(frozen_path)
    def boundary():return all(sha(ROOT/p)==h for p,h in frozen.items()) and sha(frozen_path)==frozen_receipt_hash
    before=source_hashes();initial=boundary()
    suite=unittest.defaultTestLoader.loadTestsFromName('adapters.test_receiver03_bootstrap')
    result=unittest.TextTestRunner(stream=io.StringIO(),verbosity=0).run(suite)
    try:
        run=subprocess.run(['node','--test','--test-reporter=tap','native/receiver03/offered_rate.test.mjs'],
            cwd=str(ROOT),capture_output=True,encoding='utf-8',errors='replace',timeout=30)
        counts=re.search(r'^# tests (\d+)$',run.stdout,re.MULTILINE)
        passes=re.search(r'^# pass (\d+)$',run.stdout,re.MULTILINE)
        js_ok=run.returncode==0 and counts is not None and passes is not None and int(counts[1])==int(passes[1])==3
    except Exception:
        counts=None;js_ok=False
    after=source_hashes();preserved=initial and boundary()
    ok=preserved and before==after and result.wasSuccessful() and not result.skipped and js_ok
    receipt={'status':'receiver03-offline-checks-passed' if ok else 'receiver03-offline-checks-failed',
        'createdUtc':datetime.now(timezone.utc).isoformat(),
        'source02Preserved':preserved,'source02FileCount':len(frozen),'source02ReceiptSha256':frozen_receipt_hash,
        'newSourceStable':before==after,'fileSha256':after,'pythonChecks':result.testsRun,
        'pythonFailures':len(result.failures),'pythonErrors':len(result.errors),
        'javascriptOfferedLoadTests':int(counts[1]) if counts else 0,'javascriptPassed':bool(js_ok),
        'nativeAutomationTestsStaged':3,'nativeTestsExecuted':0,'nativeCompiled':False,
        'pipesOpenedInTests':0,'socketsOpenedInTests':0,'nativeLaunches':0,'listenersStarted':0,
        'configurationChanges':False,'publicationPerformed':False,'secretsStored':False,
        'limitations':['C++ is uncompiled source; staged native tests are not passing-runtime claims',
                       'Offered-load tests use real Source02 browser controls with simulated native scheduling',
                       'Bootstrap tests replace pipe I/O; no live IPC or browser/native flow verified',
                       'Only newly created QPC-clock cores supported; existing default-clock deadlines cannot migrate',
                       'Native module integration, owned-process watchdog/job, Node-Python RPC and browser admission still absent',
                       'Input-close ACK alone is not complete stream/process disposal evidence']}
    with dest.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print('{}: {} Python checks, {} JS tests; Source02 preserved={}'.format(receipt['status'],result.testsRun,
        receipt['javascriptOfferedLoadTests'],preserved))
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main())
