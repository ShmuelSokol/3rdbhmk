"""Offline replay and optional exclusive-create receipt; never starts processes."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
from pathlib import Path
import unittest
from model import Oracle, ZERO

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counterexamples():
    rows = []
    for policy, action in (("dispatch_only", "interact"),
                           ("controller_only", "move"), ("guarded", "move")):
        m = Oracle(policy=policy)
        m.submit(1, action, (1, 0, 0))
        if action == "move":
            m.advance(499)
            m.controller()
        m.advance(501)
        m.controller()
        vector = m.consume("move")
        rows.append(dict(policy=policy, action=action, inputDeadline=500,
                         vector=vector, effects=m.effects, ack=m.ack(), trace=m.trace))
    assert rows[0]["effects"] == [("interact", 501)]
    assert rows[1]["vector"] == (1, 0, 0)
    assert rows[2]["vector"] == ZERO
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, help="new result path; refuses overwrite")
    args = parser.parse_args()
    # Check historical sources against their existing receipt; never rewrite it.
    root = HERE.parents[2]
    historical = root / "native/receiver03/receipt-01.json"
    baseline = json.loads(historical.read_text(encoding="utf-8"))
    preservation = {name: digest(root / name) == expected
                    for name, expected in baseline["fileSha256"].items()}
    sources = ("model.py", "test_model.py", "run.py", "CONTRACT.txt")
    pins = {name: digest(HERE / name) for name in sources}
    tests = unittest.defaultTestLoader.discover(str(HERE), pattern="test_model.py")
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    examples = counterexamples()
    stable = all(digest(HERE / name) == value for name, value in pins.items())
    preserved_after = all(digest(root / name) == expected
                          for name, expected in baseline["fileSha256"].items())
    passed = result.wasSuccessful() and all(preservation.values()) and preserved_after and stable
    report = dict(schema=1, status="model_passed" if passed else "failed",
                  python=sys.version.split()[0], tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors),
                  skipped=len(result.skipped), boundarySchedules=252,
                  sourceSha256=pins, sourcesStable=stable,
                  receiver03ReceiptSha256=digest(historical),
                  receiver03FilesChecked=len(preservation),
                  receiver03Preserved=all(preservation.values()) and preserved_after,
                  counterexamples=examples, socketsOpened=0, pipesOpened=0,
                  nativeLaunches=0, limitations=[
                      "Independent Python oracle, not compiled receiver04 or UE execution",
                      "Pawn tags share semantic policy; do not establish actual walker/dove hook wiring",
                      "Integer injected clock models QPC-domain order, not live QPC calls",
                      "Consumer authorization is not physics completion or rendered acceptance",
                      "No OS watchdog, transport, scheduling or real cancellation exercised"])
    if args.receipt:
        with args.receipt.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
