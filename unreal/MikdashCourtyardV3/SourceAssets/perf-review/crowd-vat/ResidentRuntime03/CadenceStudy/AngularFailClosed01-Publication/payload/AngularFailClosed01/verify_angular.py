from pathlib import Path
import tempfile,subprocess,json,hashlib
b=Path(__file__).resolve().parent
w=Path(tempfile.mkdtemp(prefix='angular-integration-'))
for p in b.iterdir():
 if p.suffix in ['.cpp','.h']:(w/p.name).write_bytes(p.read_bytes())
(w/'run.cmd').write_text('@echo off\ncall "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\ncl /nologo /std:c++17 /EHsc /W4 /O2 AngularIntegrationTest.cpp /Fe:budget.exe\nif errorlevel 1 exit /b 1\nbudget.exe\n')
r=subprocess.run(['cmd.exe','/c','run.cmd'],cwd=str(w),capture_output=True,timeout=60)
(w/'run.log').write_bytes(r.stdout+r.stderr)
print((r.stdout+r.stderr).decode(errors='replace'))
(b/'angular-test.json').write_text(json.dumps(dict(exitCode=r.returncode,output=r.stdout.decode(errors='replace'),localLog=str(w/'run.log'),sourceHashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in b.iterdir() if p.suffix in ['.h','.cpp']}),indent=2)+'\n')
raise SystemExit(r.returncode)
