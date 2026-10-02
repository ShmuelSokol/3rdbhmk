"""Offline tests and immutable evidence only. NEVER executes a child or socket."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ORACLE = ROOT / 'native/receiver04/semantic-expiry-oracle'
OWNED = [
    'adapters/process04/' + n for n in (
        'win32_child.py','host.py','consumption_channel.py','harmless_child.py',
        'test_host.py','test_consumption_channel.py','test_native_order.py','test_stream_read.py','test_receiver_controlflow.py',
        'validate.py','CONTRACT.md','README.md')
] + [
    'native/receiver04/' + n for n in (
        'Authority.h','Authority.cpp','SemanticMailbox.h','SemanticMailboxTests.cpp',
        'OwnedConsumers.h','OnlineController.h','OnlineController.cpp',
        'OnlineMovement.h','OnlineMovement.cpp','Receiver.h','Receiver.cpp',
        'Bootstrap.h','Bootstrap.cpp','BootstrapGuards.h','LifecycleRegressionTests.cpp',
        'StreamRead.h','StreamReadTests.cpp')
]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen():
    result={}
    prior=ROOT/'adapters/process04/receipt-01.json'
    if digest(prior)!='9dc0c057b9a2bb1518ebe6b95ef8a8fbab955c2c57f3b03d4104340606cd9e38':
        raise RuntimeError('Historical Process04 receipt changed')
    result['process04PriorReceiptSha256']=digest(prior)
    for receipt in ('adapters/receipt-real-stream-source-02.json','native/receiver03/receipt-01.json'):
        data=json.loads((ROOT/receipt).read_text(encoding='utf-8'))
        for relative, expected in data['fileSha256'].items():
            path=(ROOT/relative).resolve()
            if ROOT not in path.parents or digest(path).lower()!=expected.lower():
                raise RuntimeError('Frozen source mismatch: '+relative)
        result[receipt]=dict(files=len(data['fileSha256']),sha256=digest(ROOT/receipt))
    original=json.loads((ORACLE/'model-results-01.json').read_text())
    for relative,expected in original['sourceSha256'].items():
        if digest(ORACLE/relative)!=expected:raise RuntimeError('Oracle mismatch')
    extension=json.loads((ORACLE/'suppression-results-01.json').read_text())
    if digest(ORACLE/'test_suppression.py')!=extension['sourceSha256']:raise RuntimeError('Oracle extension mismatch')
    result['oracle']=dict(originalReceiptSha256=digest(ORACLE/'model-results-01.json'),
                          suppressionReceiptSha256=digest(ORACLE/'suppression-results-01.json'),files=5)
    return result


def load_oracle(name, filename):
    spec=importlib.util.spec_from_file_location(name,ORACLE/filename)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--receipt')
    args=parser.parse_args()
    if args.receipt and not re.fullmatch(r'receipt-[0-9]{2}\.json',args.receipt):
        parser.error('Use a fresh receipt-NN.json basename')
    before=frozen()
    source={name:digest(ROOT/name) for name in OWNED}
    for name in OWNED:
        data=(ROOT/name).read_bytes()
        if b'\r' in data:raise RuntimeError('Source must use LF: '+name)
        if name.endswith('.py'):ast.parse(data,filename=name)
    groups={}
    for name in ('adapters.process04.test_host','adapters.process04.test_consumption_channel','adapters.process04.test_native_order',
                 'adapters.process04.test_stream_read','adapters.process04.test_receiver_controlflow'):
        result=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromName(name))
        groups[name]=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful())
        if not result.wasSuccessful():
            # Tests use only public synthetic fixtures; output fixed test IDs,
            # never adapter exception bodies or bootstrap contents.
            print(json.dumps({'failedTests':[str(test) for test,_ in result.failures+result.errors]}))
    sys.path.insert(0,str(ORACLE))
    try:
        for name,file in (('oracle_original','test_model.py'),('oracle_suppression','test_suppression.py')):
            result=unittest.TextTestRunner(stream=io.StringIO()).run(load_oracle(name,file))
            groups[name]=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful())
    finally:sys.path.pop(0)
    after=frozen()
    stable=before==after and source=={name:digest(ROOT/name) for name in OWNED}
    passed=stable and all(g['passed'] for g in groups.values())
    receipt=dict(schema=1,status='offline-source-review-candidate' if passed else 'failed',
        createdUtc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
        pythonChecks=sum(g['tests'] for g in groups.values()),groups=groups,
        fileSha256=source,sourceFileCount=len(source),sourceStable=stable,frozenEvidence=after,
        source02Preserved=True,receiver03Preserved=True,oraclePreserved=True,
        nativeAutomationTestsStaged=14,nativeAutomationTestsExecuted=0,nativeCompiled=False,
        windowsBackendExecuted=False,childProcessesExecuted=0,realThreadsStarted=0,
        socketsOpened=0,pipesOpened=0,projectConfigurationChanged=False,
        limitations=['Python/Win32 doubles and ordering models are not native execution',
                     'No UHT/UBT/native compile performed; coordinator reserved slot only',
                     'No installed controller/movement/bootstrap module or approved launch recipe',
                     'No authenticated streamer attachment, media start or browser admission/RPC transport',
                     'Settings/save application and explicit project interaction outcome API still required',
                     'Remote stock-camera control rotation does not claim same-tick pawn-facing acceptance',
                     'Unknown timeout may follow an effect; no automatic replay or rollback claim'])
    prior=json.loads((HERE/'receipt-01.json').read_text())['fileSha256']
    receipt['changedSinceReceipt01']=[name for name in OWNED if source[name]!=prior.get(name)]
    if args.receipt:
        if not passed:raise RuntimeError('Refusing a passing receipt for failed checks')
        path=HERE/args.receipt
        with path.open('x',encoding='utf-8',newline='\n') as out:
            json.dump(receipt,out,indent=2);out.write('\n')
        print(json.dumps(dict(receipt=str(path),sha256=digest(path),tests=receipt['pythonChecks'],files=len(source))))
    else:
        print(json.dumps(dict(status=receipt['status'],tests=receipt['pythonChecks'],groups=groups,
                              sourceFiles=len(source),frozen02=26,frozen03=15,sourceStable=stable)))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(main())
