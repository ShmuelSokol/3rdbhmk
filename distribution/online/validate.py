"""Run bounded local contract tests and write a secret-free, byte-pinned receipt."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parent
FILES = ("session_core.py", "test_session_core.py", "README.md", "validate.py")


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


class SafeResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.completed = []

    def addSuccess(self, test):
        self.completed.append(test.id())
        super().addSuccess(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    destination = Path(args.receipt).resolve()
    if destination.exists():
        parser.error("Receipt destination already exists; choose a fresh path")
    before = hashes()
    suite = unittest.defaultTestLoader.discover(str(ROOT), pattern="test_session_core.py")
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0,
                                    resultclass=SafeResult).run(suite)
    elapsed = time.monotonic() - started
    after = hashes()
    stable = before == after
    passed = result.wasSuccessful() and stable and result.testsRun > 0 and not result.skipped
    receipt = {
        "status": "offline-core-tests-passed" if passed else "offline-core-tests-failed",
        "createdUtc": datetime.now(timezone.utc).isoformat(),
        "scope": "Reusable lifecycle core tested with adapters; no native/signaling/browser delivery",
        "python": platform.python_version(),
        "testsRun": result.testsRun,
        "passed": len(result.completed),
        "failures": [test.id() for test, _ in result.failures],
        "errors": [test.id() for test, _ in result.errors],
        "skippedCount": len(result.skipped),
        "passedTests": result.completed,
        "elapsedSeconds": round(elapsed, 6),
        "sourceStableDuringTests": stable,
        "fileSha256": after,
        "secretsStored": False,
        "nativeLaunches": 0,
        "networkServicesStarted": 0,
        "productionConfigChanges": False,
        "publicationPerformed": False,
        "remaining": ["Native/process adapter", "Signaling/stream adapter", "Browser desktop/mobile controls",
                      "Measured host capacity", "Real independent-session and online acceptance"],
    }
    with destination.open("x", encoding="utf-8") as output:
        json.dump(receipt, output, indent=2)
        output.write("\n")
    print("{}: {}/{} tests passed; source stable={}".format(
        receipt["status"], len(result.completed), result.testsRun, stable))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
