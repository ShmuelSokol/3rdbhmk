"""Compile and run the crowd-field standalone test with installed MSVC. Writes tests.json here.

No Unreal, no UnrealBuildTool, no download: CrowdFieldMath.h is engine-independent by design,
so the whole flow field, containment, budget and apportioning logic is testable without the
editor. Same shape as SourceAssets/runtime-review/dove-people-v2/run_standalone_tests.py.

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
SOURCES = ['CrowdFieldMathTest.cpp']
HEADERS = ['CrowdFieldMath.h', 'MikdashCrowdField.h']
# NDEBUG is deliberately NOT defined: every assert runs, under /O2, with warnings as errors.
FLAGS = ['/nologo', '/std:c++17', '/EHsc', '/W4', '/WX', '/O2']


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
    build = args.build_dir or Path(tempfile.mkdtemp(prefix='mikdash-crowd-tests-'))
    build.mkdir(parents=True, exist_ok=True)

    version = subprocess.run([compiler], capture_output=True, text=True, env=env)
    toolchain = (version.stderr or version.stdout).splitlines()[0].strip() if (version.stderr or version.stdout) else 'unknown'

    report = dict(
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        toolchain=toolchain,
        flags=' '.join(FLAGS),
        note='Asserts stay enabled: NDEBUG is deliberately not defined, so every assert is executed under /O2.',
        sources='Plugins/MikdashRuntime/Tests/CrowdFieldMathTest.cpp against Plugins/MikdashRuntime/Source/MikdashRuntime/Public',
        scope='Engine-independent crowd math only. This proves the flow field, zone containment, seeding, gait, round-robin budget, distance policy and apportioning; it proves nothing about rendering, instancing cost, frame time or how the crowd looks.',
        headers={name: sha(PUBLIC / name) for name in HEADERS if (PUBLIC / name).is_file()},
        results=[])

    all_passed = True
    for source_name in SOURCES:
        source = TESTS / source_name
        exe = build / (source.stem + '.exe')
        compile_result = subprocess.run([compiler] + FLAGS + ['/I' + str(PUBLIC), str(source), '/Fe:' + str(exe)],
                                        capture_output=True, text=True, cwd=str(build), env=env)
        entry = dict(test=exe.name, source=source_name, sourceSha256=sha(source),
                     compileExitCode=compile_result.returncode,
                     compileStdout=compile_result.stdout.strip(), compileStderr=compile_result.stderr.strip())
        if compile_result.returncode != 0 or not exe.is_file():
            entry['passed'] = False
            all_passed = False
            report['results'].append(entry)
            continue
        run_result = subprocess.run([str(exe)], capture_output=True, text=True, cwd=str(build), env=env)
        entry.update(exitCode=run_result.returncode, stdout=run_result.stdout.strip(), stderr=run_result.stderr.strip(),
                     exeSha256=sha(exe), passed=run_result.returncode == 0)
        all_passed = all_passed and entry['passed']
        report['results'].append(entry)

    report['allPassed'] = all_passed
    report['status'] = 'standalone_math_tests_passed' if all_passed else 'standalone_math_tests_failed'
    (HERE / 'tests.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('stamp', 'toolchain', 'allPassed', 'status')}, indent=2))
    for entry in report['results']:
        print(entry['test'], 'passed' if entry.get('passed') else 'FAILED')
        for line in (entry.get('stdout') or entry.get('compileStdout') or '').splitlines():
            print('   ', line)
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
