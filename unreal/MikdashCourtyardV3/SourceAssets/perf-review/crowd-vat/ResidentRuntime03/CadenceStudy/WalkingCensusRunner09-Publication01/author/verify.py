"""Offline source/policy verification only. No compiler, editor or game."""
import json, subprocess, sys
from pathlib import Path
import runner
r=Path(__file__).resolve().parent
m,i=runner.verify()
for p in r.glob('*.py'):compile(p.read_text(encoding='utf-8'),str(p),'exec')
for n,h in runner.load(r/'strict-build-result.json')['sourcePins'].items():
    runner.require(runner.sha(r/n)==h,'inherited strict source changed: '+n)
runner.require((r/'StrictABI.h').read_bytes()==(r/'ABI/StrictABI.h').read_bytes(),'ABI mismatch')
subprocess.run([sys.executable,'-B',str(r/'test_runner.py')],check=True)
ps='C:/Users/shmue/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
policy=json.loads(subprocess.check_output([ps,'-NoProfile','-File',str(r/'test_policy.ps1')],text=True))
runner.require(policy['failures']==0 and policy['processesLaunched']==0,'policy result')
print(json.dumps({'status':'offline_source_checked_UE_uncompiled_review_required','manifest':runner.sha(r/'manifest.json'),
 'files':len(m['files']),'inputs':len(m['inputs']),'packages':len(i['packages']),'pluginFiles':len(i['pluginFiles']),
 'pythonTests':23,'policyChecks':policy['checks'],'UEExecuted':False,'worldReady':False}))
