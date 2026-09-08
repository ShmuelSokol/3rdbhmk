"""Compile and run every Plugins/MikdashRuntime/Tests/*.cpp standalone with installed MSVC.

No Unreal, no UnrealBuildTool, no download. Writes tests.json beside this script.
Usage: python run_standalone_tests.py [--vcvars <path to vcvars64.bat>] [--build-dir <dir>]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TESTS = ROOT / 'Plugins/MikdashRuntime/Tests'
PUBLIC = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public'
FLAGS = ['/nologo', '/std:c++17', '/EHsc', '/W4', '/WX', '/O2', '/DNDEBUG_UNUSED']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_vcvars(explicit):
    candidates = [explicit] if explicit else []
    for root in (Path(r'C:\Program Files (x86)\Microsoft Visual Studio'), Path(r'C:\Program Files\Microsoft Visual Studio')):
        if root.is_dir():
            candidates.extend(sorted(root.glob('*/BuildTools/VC/Auxiliary/Build/vcvars64.bat'), reverse=True))
            candidates.extend(sorted(root.glob('*/*/VC/Auxiliary/Build/vcvars64.bat'), reverse=True))
    found = next((Path(p) for p in candidates if p and Path(p).is_file()), None)
    if not found:
        raise SystemExit('No installed vcvars64.bat found; pass --vcvars. No toolchain download attempted.')
    return found


def toolchain_env(vcvars):
    out = subprocess.run('cmd.exe /d /s /c ""{}" >nul && set"'.format(vcvars), capture_output=True, text=True, check=True)
    env = dict(os.environ)
    for line in out.stdout.splitlines():
        if '=' in line:
            key, _, value = line.partition('=')
            env[key] = value
    compiler = shutil.which('cl.exe', path=env.get('PATH', ''))
    if not compiler:
        raise SystemExit('Installed vcvars did not expose cl.exe')
    return env, compiler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vcvars', type=Path)
    parser.add_argument('--build-dir', type=Path)
    args = parser.parse_args()
    vcvars = find_vcvars(args.vcvars)
    env, compiler = toolchain_env(vcvars)
    build = args.build_dir or Path(tempfile.mkdtemp(prefix='mikdash-tests-'))
    build.mkdir(parents=True, exist_ok=True)
    version = subprocess.run([compiler], capture_output=True, text=True, env=env)
    report = dict(stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
                  toolchain=(version.stderr or version.stdout).strip().splitlines()[0] if (version.stderr or version.stdout) else 'cl.exe',
                  flags=' '.join(f for f in FLAGS if f != '/DNDEBUG_UNUSED'),
                  note='Asserts stay enabled: NDEBUG is deliberately not defined so every assert is executed under /O2.',
                  sources=str(TESTS.relative_to(ROOT)) + '/*.cpp against ' + str(PUBLIC.relative_to(ROOT)),
                  headers={p.name: sha(p) for p in sorted(PUBLIC.glob('*.h'))},
                  results=[], allPassed=True)
    for source in sorted(TESTS.glob('*.cpp')):
        exe = build / (source.stem + '.exe')
        compile_cmd = [compiler] + [f for f in FLAGS if f != '/DNDEBUG_UNUSED'] + ['/I', str(PUBLIC), str(source), '/Fo' + str(build) + os.sep, '/Fe' + str(exe)]
        compiled = subprocess.run(compile_cmd, capture_output=True, text=True, env=env, cwd=str(build))
        row = dict(test=exe.name, source=source.name, sourceSha256=sha(source), compileExitCode=compiled.returncode)
        if compiled.returncode != 0:
            row.update(compileOutput=(compiled.stdout + compiled.stderr)[-4000:], exitCode=None, passed=False)
            report['allPassed'] = False
        else:
            run = subprocess.run([str(exe)], capture_output=True, text=True, cwd=str(build), timeout=120)
            row.update(exitCode=run.returncode, stdout=run.stdout.strip(), stderr=run.stderr.strip()[-2000:],
                       exeSha256=sha(exe), passed=run.returncode == 0)
            if run.returncode != 0:
                report['allPassed'] = False
        report['results'].append(row)
        print(('PASS ' if row['passed'] else 'FAIL ') + row['test'] + (': ' + row.get('stdout', row.get('compileOutput', ''))[:400]))
    (HERE / 'tests.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('allPassed=' + str(report['allPassed']) + ' -> ' + str(HERE / 'tests.json'))
    return 0 if report['allPassed'] else 1


if __name__ == '__main__':
    sys.exit(main())
