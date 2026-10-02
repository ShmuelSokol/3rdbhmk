"""Portable Windows MSVC standalone decision test. Python standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    for name, pin in manifest['files'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or digest(path) != pin:
            raise RuntimeError('Payload hash/path mismatch: ' + name)
    return digest(ROOT / 'manifest.json')


def atomic(path, value):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def execute(command, output, log, timeout):
    started = time.monotonic()
    with (output / log).open('wb') as stream:
        child = subprocess.Popen(command, cwd=output, stdout=stream,
                                 stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        timed_out = False
        cleanup = None
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            cleanup = subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                                     capture_output=True, timeout=5,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            code = child.wait(timeout=5)
    return dict(command=command, exitCode=code, timedOut=timed_out,
                deadlineSeconds=timeout, elapsedSeconds=time.monotonic()-started,
                output=log, outputSHA256=digest(output/log),
                cleanupExit=None if cleanup is None else cleanup.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path,
                        help='Explicit fresh nonexistent directory outside source closure')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise SystemExit('Output must be outside source closure')
    if os.name != 'nt':
        raise SystemExit('Windows/MSVC required; no emulation or engine substitute')
    before = verify()
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(status='FAIL', manifestBefore=before, fullAdapterCompiled=False,
                   UEExecuted=False, UHTRun=False, UBTRun=False)
    try:
        candidates = [Path(os.environ.get(k, '')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
                      for k in ('ProgramFiles(x86)', 'ProgramFiles') if os.environ.get(k)]
        vswhere = next((p for p in candidates if p.is_file()), None)
        if vswhere is None:
            raise RuntimeError('vswhere missing: install Visual Studio C++ Build Tools')
        query = [str(vswhere), '-latest', '-products', '*', '-requires',
                 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath']
        discovered = subprocess.run(query, capture_output=True, text=True,
                                    timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        receipt['discovery'] = dict(command=query, exitCode=discovered.returncode,
                                    stdout=discovered.stdout, stderr=discovered.stderr)
        if discovered.returncode != 0 or not discovered.stdout.strip():
            raise RuntimeError('MSVC x64 discovery failed')
        vcvars = Path(discovered.stdout.strip()) / 'VC/Auxiliary/Build/vcvars64.bat'
        if not vcvars.is_file():
            raise RuntimeError('Discovered toolchain lacks vcvars64.bat')
        # These paths enter a generated batch file. Reject shell expansion/control
        # characters rather than interpret untrusted path text as cmd syntax.
        for path in (ROOT, output, vcvars):
            if any(c in str(path) for c in '%!\r\n"&|<>^'):
                raise RuntimeError('Path unsupported by bounded batch invocation')
        source = ROOT / 'tests/decision_test.cpp'
        command = ('cl.exe /std:c++17 /EHsc /W4 /Bv /showIncludes "' + str(source)
                   + '" /Fodecision_test.obj /Fedecision_test.exe')
        batch = ('@echo off\r\ncall "' + str(vcvars) + '"\r\n'
                 'if errorlevel 1 exit /b %errorlevel%\r\n'
                 'where cl.exe\r\n' + command + '\r\nexit /b %errorlevel%\r\n')
        (output/'compile.cmd').write_bytes(batch.encode('utf-8'))
        receipt['compilerCommand'] = command
        receipt['sourceSHA256'] = digest(source)
        receipt['compilation'] = execute([os.environ['COMSPEC'], '/d', '/c', str(output/'compile.cmd')],
                                         output, 'compiler-output.txt', 60)
        if receipt['compilation']['exitCode'] != 0 or receipt['compilation']['timedOut']:
            raise RuntimeError('Standalone compilation failed/timed out')
        receipt['execution'] = execute([str(output/'decision_test.exe')], output, 'test-output.txt', 10)
        expected = 'focused=18 exhaustive=16384 quality=4 readyAssignments=1 failures=0'
        if receipt['execution']['exitCode'] != 0 or receipt['execution']['timedOut'] or (output/'test-output.txt').read_text().strip() != expected:
            raise RuntimeError('Compiled decision checks failed')
        receipt.update(status='PASS_COMPILED_DECISION_ONLY', focusedCases=18,
                       exhaustiveAssignments=16384, qualityCases=4)
    except Exception as exc:
        receipt['error'] = str(exc)
    finally:
        try:
            receipt['manifestAfter'] = verify()
            if receipt['manifestAfter'] != before:
                raise RuntimeError('Manifest changed during test')
        except Exception as exc:
            receipt.update(status='FAIL', preservationError=str(exc))
        atomic(output/'receipt.json', receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['status'] == 'PASS_COMPILED_DECISION_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
