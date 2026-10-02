import argparse,json,subprocess,shutil,hashlib,sys
from pathlib import Path
p=Path(__file__).resolve().parent
a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--vcvars',required=True);x=a.parse_args()
o=Path(x.output).absolute();assert not o.exists();o.mkdir(parents=True)
tool=Path(x.vcvars).absolute();assert tool.is_file() and not any(t in str(tool) for t in ['"','%','\n','\r'])
shutil.copyfile(p/'ProtocolTest.cpp',o/'ProtocolTest.cpp');d=o/'Source/PairedRenderHost/Public';d.mkdir(parents=True);shutil.copyfile(p/'Source/PairedRenderHost/Public/PairProtocol.h',d/'PairProtocol.h')
(o/'build.cmd').write_text('@echo off\ncall "'+str(tool)+'" >nul\ncl /nologo /std:c++17 /EHsc /O2 /fp:strict ProtocolTest.cpp /Fe:test.exe\n')
r=subprocess.run(['cmd.exe','/d','/c','build.cmd'],cwd=o,capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
r=subprocess.run([str(o/'test.exe')],cwd=o,capture_output=True,timeout=30);(o/'protocol.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
result={'protocol':r.stdout.decode().strip(),'nativeCompiled':False,'renderProved':False}
r=subprocess.run([sys.executable,'-B',str(p/'source_tests.py')],capture_output=True,timeout=30);assert r.returncode==0,r.stderr;result.update(json.loads(r.stdout))
result['sourceHashes']={str(f.relative_to(p)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob('*')) if f.is_file() and f.suffix in ['.h','.cpp','.py','.cs']}
(o/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
