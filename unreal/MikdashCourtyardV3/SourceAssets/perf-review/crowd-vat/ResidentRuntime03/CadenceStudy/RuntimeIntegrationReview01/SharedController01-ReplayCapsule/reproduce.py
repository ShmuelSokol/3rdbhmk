"""Replay frozen standalone source; historic logs and the repository are not needed."""
import argparse,gzip,hashlib,json,re,subprocess,tempfile
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',default='exact600')
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--vcvars',default=r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
    args=parser.parse_args();base=Path(__file__).resolve().parent
    manifest=json.loads((base/'manifest.json').read_text())
    assert args.case in manifest['cases'],args.case
    case=manifest['cases'][args.case]
    source={}
    for item in case['inputs']:
        raw=(base/item['path']).read_bytes();assert sha(raw)==item['compressedSha256'],item['path']
        data=gzip.decompress(raw);assert sha(data)==item['sourceSha256'],item['path']
        source[item['extractAs']]=data
    expected={}
    for item in case['expectedCsv']:
        raw=(base/item['path']).read_bytes();assert sha(raw)==item['compressedSha256'],item['path']
        data=gzip.decompress(raw);assert sha(data)==item['csvSha256'],item['path']
        expected[item['outputName']]=item['csvSha256']
    if args.verify_only:
        print(json.dumps(dict(case=args.case,verifiedSourceFiles=len(source),verifiedCsvFiles=len(expected),historicLogsRequired=False)));return
    assert Path(args.vcvars).is_file(),args.vcvars
    work=Path(tempfile.mkdtemp(prefix='travelling-frozen-replay-'))
    for name,data in source.items():(work/name).write_bytes(data)
    # Single shell; no repository writes, deletion, Unreal, or UBT invocation.
    batch='@echo off\ncall "'+args.vcvars+'" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /EHsc /W4 /O2 /I. fixture.cpp /Fe:fixture.exe\nif errorlevel 1 exit /b 1\nfixture.exe\n'
    (work/'run.cmd').write_text(batch,encoding='ascii')
    result=subprocess.run(['cmd.exe','/c','run.cmd'],cwd=str(work),capture_output=True,timeout=120)
    log=result.stdout+result.stderr;(work/'replay.log').write_bytes(log)
    match=re.search(rb'CrowdBoundaryMath: (\d+) checks, (\d+) failures',log)
    checks=int(match.group(1)) if match else None;failures=int(match.group(2)) if match else None
    comparisons={}
    for name,h in expected.items():
        p=work/name;actual=sha(p.read_bytes()) if p.exists() else None
        comparisons[name]=dict(expected=h,actual=actual,matches=actual==h)
    passed=result.returncode==case['expectedExitCode'] and checks==case['checks'] and failures==case['expectedFailures'] and all(x['matches'] for x in comparisons.values())
    report=dict(case=args.case,reproducesExpectedOutcome=passed,acceptance=case['acceptance'],exitCode=result.returncode,checks=checks,failures=failures,
        csvComparisons=comparisons,localOutputDirectory=str(work),historicLogsRequired=False,
        productionAdoption=False,sourceInputs=case['inputs'])
    (work/'replay-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='sourceInputs'},indent=2))
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
