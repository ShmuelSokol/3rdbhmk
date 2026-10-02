"""Independent regression specification, NOT UE or receiver04 implementation.

Run this file with Python -B. Optional --receipt NEW.json refuses overwrite.
Original oracle files/receipt are historical and remain unchanged.

Chosen modeled look contract: evaluate normal LOCAL camera modifiers once, then
authorize a callback-free remote delta/clamp at the final rotation commit. Remote
postprocessing is allowed only by an explicit supported-camera policy. Otherwise
reject remote and preserve the normal local result. Exactly one modeled modifier
evaluation and one final FaceRotation per update. This is NOT proof that arbitrary
custom modifiers/XR can be split into a local evaluation plus remote delta.

Cinematic suppression zeroes local look before modifiers as UE does; remote look
must independently check suppression again after callbacks and before commit.
Movement preserves its already accepted local vector; remote rejection must not
zero shared local input, existing velocity, or inertia. Re-enabling input does not
replay discarded remote commands. Integer fake time models ordering only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest


class Consumer:
    def __init__(self, pawn="walker", unsafe=False):
        self.pawn = pawn
        self.now = 0
        self.ignore_look = self.ignore_move = False
        self.paused = False
        self.supported_camera = True
        self.remote_look = 3
        self.remote_move = 3
        self.deadline = 500
        self.modifier_calls = self.face_calls = 0
        self.modifier_state = 0
        self.unsafe = unsafe
        self.outcome = None

    def modifier(self, local):
        self.modifier_calls += 1
        self.modifier_state += 1  # observable callback effect, cannot roll back
        return local + self.modifier_state

    def look(self, local, callback=lambda _: None, before_commit=lambda _: None):
        # Normal local path still runs once even when remote is expired/blocked.
        local_result = self.modifier(0 if self.ignore_look else local)
        callback(self)  # injected modifier stall/state change
        candidate = local_result
        if self.unsafe and self.remote_look is not None:
            candidate = self.modifier(candidate + self.remote_look)
        before_commit(self)
        fresh = self.now < self.deadline and not self.paused
        allowed = fresh and self.supported_camera and not self.ignore_look
        if self.unsafe:
            allowed = fresh  # historical bypass of ignore flags
        if self.remote_look is not None:
            self.outcome = "consumed" if allowed else "discarded"
            if allowed and not self.unsafe:
                candidate += self.remote_look  # pure delta; no second callback
            elif not allowed:
                candidate = local_result
        self.remote_look = None  # one-shot, including rejected and timed-out work
        self.face_calls += 1
        return candidate

    def movement(self, local, work=lambda _: None):
        # Work represents walker constrain/scale or dove collision sweep.
        # Candidate scale deliberately differs so stale derived state is visible.
        direction, scale = local + (self.remote_move or 0), .25
        work(self)
        allowed = self.now < self.deadline and not self.paused and not self.ignore_move
        if self.unsafe:
            allowed = self.now < self.deadline
        if self.remote_move is None or not allowed:
            self.remote_move = None
            return local, 1.0  # independent local result, not stale remote scale
        return direction, scale


class SuppressionTests(unittest.TestCase):
    def test_unsafe_cinematic_bypass_counterexample(self):
        c = Consumer(unsafe=True)
        c.ignore_move = c.ignore_look = True
        self.assertNotEqual(c.look(2), 1)  # normal suppressed local result is 1
        self.assertEqual(c.movement(2), (5, .25))

    def test_unsafe_expired_look_still_duplicates_modifier_effect(self):
        c = Consumer(unsafe=True)
        result = c.look(2, callback=lambda x: setattr(x, "now", 501))
        self.assertEqual(result, 3)  # output rollback cannot undo callback effects
        self.assertEqual(c.modifier_state, 2)
        self.assertEqual(c.modifier_calls, 2)

    def test_look_modifiers_and_face_exactly_once(self):
        for time in (0, 499, 500, 501):
            for suppressed in (False, True):
                c = Consumer()
                c.now, c.ignore_look = time, suppressed
                result = c.look(2)
                base = 1 if suppressed else 3
                self.assertEqual(result, base + (3 if time < 500 and not suppressed else 0))
                self.assertEqual((c.modifier_calls, c.face_calls, c.modifier_state), (1, 1, 1))

    def test_expiry_inside_modifier_preserves_local_result(self):
        c = Consumer()
        self.assertEqual(c.look(2, callback=lambda x: setattr(x, "now", 500)), 3)
        self.assertEqual((c.modifier_calls, c.face_calls), (1, 1))
        self.assertEqual(c.outcome, "discarded")

    def test_stall_after_modifier_before_commit(self):
        c = Consumer()
        self.assertEqual(c.look(2, before_commit=lambda x: setattr(x, "now", 501)), 3)
        self.assertEqual((c.modifier_calls, c.face_calls), (1, 1))

    def test_cinematic_or_pause_activated_by_modifier(self):
        for flag in ("ignore_look", "paused"):
            c = Consumer()
            self.assertEqual(c.look(2, callback=lambda x: setattr(x, flag, True)), 3)
            self.assertEqual(c.outcome, "discarded")
            self.assertEqual(c.modifier_calls, 1)

    def test_unsupported_camera_runs_local_once_and_rejects_remote(self):
        c = Consumer()
        c.supported_camera = False
        self.assertEqual(c.look(2), 3)
        self.assertEqual((c.modifier_calls, c.face_calls), (1, 1))
        self.assertEqual(c.outcome, "discarded")

    def test_reenabled_look_does_not_replay_discarded_command(self):
        c = Consumer()
        c.ignore_look = True
        self.assertEqual(c.look(2), 1)
        c.ignore_look = False
        self.assertEqual(c.look(2), 4)  # local2 + second modifier state2, no remote3
        self.assertEqual((c.modifier_calls, c.face_calls), (2, 2))

    def test_suppressed_walker_dove_preserve_local(self):
        for pawn in ("walker", "dove"):
            for flag in ("ignore_move", "paused"):
                c = Consumer(pawn)
                setattr(c, flag, True)
                self.assertEqual(c.movement(2), (2, 1.0))
                setattr(c, flag, False)
                self.assertEqual(c.movement(2), (2, 1.0))

    def test_suppression_during_scale_or_sweep_discards_all_remote_state(self):
        for pawn in ("walker", "dove"):
            c = Consumer(pawn)
            result = c.movement(2, work=lambda x: setattr(x, "ignore_move", True))
            self.assertEqual(result, (2, 1.0))
            c.ignore_move = False
            self.assertEqual(c.movement(2), (2, 1.0))

    def test_expiry_during_scale_or_sweep_preserves_local(self):
        for pawn in ("walker", "dove"):
            c = Consumer(pawn)
            self.assertEqual(c.movement(2, work=lambda x: setattr(x, "now", 500)), (2, 1.0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    historical = json.loads((here / "model-results-01.json").read_text())
    def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
    source_hash = digest(Path(__file__))
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SuppressionTests))
    preserved = all(digest(here / name) == pin for name, pin in historical["sourceSha256"].items())
    stable = digest(Path(__file__)) == source_hash
    report = dict(status="model_passed" if result.wasSuccessful() and preserved and stable else "failed",
                  tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  sourceSha256=source_hash, originalOraclePreserved=preserved, sourceStable=stable,
                  originalReceiptSha256=digest(here / "model-results-01.json"),
                  limitations="Independent fake-clock/callback model; not native adapter execution or arbitrary camera compatibility",
                  nativeLaunches=0, socketsOpened=0, pipesOpened=0)
    if args.receipt:
        with args.receipt.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["status"] == "model_passed" else 1)
