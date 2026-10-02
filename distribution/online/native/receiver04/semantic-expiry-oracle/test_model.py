"""Run: python -B -m unittest discover -s <this directory> -v."""
import itertools
import unittest
from model import Oracle, ZERO

LOCAL = (2, -3, 4)
REMOTE = (1, 0, -1)
MERGED = (3, -3, 3)


class SemanticExpiryTests(unittest.TestCase):
    def test_dispatch_only_counterexample_late_button(self):
        m = Oracle(policy="dispatch_only")
        m.submit(1, "interact")
        m.advance(501)
        m.controller()
        self.assertEqual(m.effects, [("interact", 501)])
        self.assertEqual(m.ack()["status"], "unknown")

    def test_controller_only_counterexample_late_movement(self):
        for pawn in ("walker", "dove"):
            m = Oracle(pawn=pawn, policy="controller_only")
            m.submit(1, "move", REMOTE)
            m.advance(499)
            m.controller()
            m.advance(501)
            self.assertEqual(m.consume("move", LOCAL), MERGED)

    def test_stall_before_controller_rejects_all_semantics(self):
        for action in ("move", "look", "interact", "pause", "mute"):
            m = Oracle()
            m.submit(1, action, REMOTE)
            m.advance(500)
            m.controller()
            self.assertEqual(m.outcome, "expired")
            self.assertEqual(m.consume("move", LOCAL), LOCAL)
            self.assertEqual(m.effects, [])

    def test_stall_between_controller_and_consumer(self):
        for pawn, action in itertools.product(("walker", "dove"), ("move", "look")):
            m = Oracle(pawn=pawn)
            m.submit(1, action, REMOTE)
            m.controller()
            m.advance(500)
            self.assertEqual(m.consume(action, LOCAL), LOCAL)
            self.assertEqual(m.outcome, "expired")

    def test_boundary_sweep_oracle_at_actual_consumer(self):
        for pawn, action, dispatch, control, consume in itertools.product(
                ("walker", "dove"), ("move", "look"), (0, 9500, 9750),
                (0, 1, 249, 499, 500, 501), (0, 1, 249, 499, 500, 501)):
            if consume < control:
                continue
            m = Oracle(pawn=pawn)
            m.advance(dispatch)
            m.submit(1, action, REMOTE)
            m.advance(dispatch + control)
            m.controller()
            m.advance(dispatch + consume)
            expected = MERGED if dispatch + consume < min(dispatch + 500, 10000) else LOCAL
            with self.subTest(pawn=pawn, action=action, dispatch=dispatch,
                              control=control, consume=consume):
                self.assertEqual(m.consume(action, LOCAL), expected)

    def test_no_early_ack_for_axes(self):
        for action in ("move", "look"):
            m = Oracle()
            m.submit(1, action, REMOTE)
            self.assertEqual(m.ack(), "pending")
            m.controller()
            self.assertEqual(m.ack(), "pending")
            m.advance(10)
            m.consume(action)
            self.assertEqual(m.ack(), dict(sequence=1, status="consumed",
                                          consumed_at=10, observed_at=10))

    def test_paused_walker_and_dove_discard_axes_no_resume_replay(self):
        for pawn, action, pause_after_route in itertools.product(
                ("walker", "dove"), ("move", "look"), (False, True)):
            m = Oracle(pawn=pawn)
            m.submit(1, action, REMOTE)
            if pause_after_route:
                m.controller()
            m.set_paused(True)
            m.controller()
            self.assertEqual(m.consume(action, LOCAL), LOCAL)
            m.set_paused(False)
            self.assertEqual(m.consume(action, LOCAL), LOCAL)
            self.assertEqual(m.ack()["status"], "paused_rejected")

    def test_paused_buttons_and_expiry(self):
        for action in ("pause", "mute", "interact"):
            m = Oracle()
            m.set_paused(True)
            m.submit(1, action)
            m.controller()
            expected = "paused_rejected" if action == "interact" else "consumed"
            self.assertEqual(m.ack()["status"], expected)
            m.submit(2, "mute")
            m.advance(500)
            count = len(m.effects)
            m.controller()
            self.assertEqual(len(m.effects), count)

    def test_release_preserves_local_at_every_queued_phase(self):
        for action, routed in itertools.product(("move", "look", "interact"), (False, True)):
            if action == "interact" and routed:
                continue  # completed effects are not reversible
            m = Oracle()
            m.submit(1, action, REMOTE)
            if routed:
                m.controller()
            m.release()
            m.controller()
            self.assertEqual(m.consume("move", LOCAL), LOCAL)
            self.assertEqual(m.consume("look", LOCAL), LOCAL)
            self.assertEqual(m.effects, [])
            self.assertEqual(m.ack()["status"], "cancelled")

    def test_held_release_pause_and_pawn_change_preserve_local(self):
        for pawn, event in itertools.product(("walker", "dove"), ("release", "pause", "replace")):
            m = Oracle(pawn=pawn)
            m.submit(1, "move", REMOTE)
            m.controller()
            self.assertEqual(m.consume("move", LOCAL), MERGED)
            m.ack()
            if event == "release": m.release()
            elif event == "pause": m.set_paused(True)
            else: m.replace_pawn("dove" if pawn == "walker" else "walker")
            self.assertEqual(m.consume("move", LOCAL), LOCAL)
            m.set_paused(False)
            self.assertEqual(m.consume("move", LOCAL), LOCAL)

    def test_held_lease_never_extended_by_controller_delay(self):
        m = Oracle()
        m.submit(1, "move", REMOTE)
        m.advance(499)
        m.controller()
        m.consume("move")
        m.ack()
        m.advance(1999)
        self.assertEqual(m.consume("move", LOCAL), MERGED)
        m.advance(2000)
        self.assertEqual(m.consume("move", LOCAL), LOCAL)

    def test_session_caps_response_and_hold(self):
        m = Oracle(session_end=100)
        m.submit(1, "move", REMOTE)
        m.controller()
        m.consume("move")
        m.advance(100)
        self.assertEqual(m.consume("move", LOCAL), LOCAL)
        self.assertEqual(m.ack()["status"], "unknown")
        self.assertEqual(m.submit(2, "mute"), "closed")

    def test_handler_stall_unknown_with_effect_and_no_automatic_replay(self):
        m = Oracle()
        m.submit(1, "mute")
        m.advance(499)
        m.controller(handler_ticks=2)
        self.assertEqual(m.effects, [("mute", 499)])
        self.assertEqual(m.ack()["status"], "unknown")
        self.assertEqual(m.submit(1, "mute"), "replay_rejected")
        for now in (502, 1000, 2000):
            m.advance(now)
            m.controller()
            self.assertIsNone(m.ack())
        self.assertEqual(m.last_sequence, 1)  # no hidden fresh-sequence retry
        self.assertEqual(len(m.effects), 1)

    def test_timeout_without_effect_also_unknown(self):
        m = Oracle()
        m.submit(1, "interact")
        m.advance(500)
        self.assertEqual(m.ack()["status"], "unknown")
        m.controller()
        self.assertEqual(m.effects, [])

    def test_late_ack_not_success_even_when_consumed_in_time(self):
        m = Oracle()
        m.submit(1, "mute")
        m.controller()
        m.advance(500)
        self.assertEqual(m.ack()["status"], "unknown")

    def test_noop_handler_not_claimed_applied(self):
        m = Oracle()
        m.submit(1, "interact")
        m.controller(effective=False)
        self.assertEqual(m.ack()["status"], "no_effect")
        self.assertEqual(m.effects, [])

    def test_mailbox_bounded_busy_sequence_not_replayed(self):
        m = Oracle()
        self.assertEqual(m.submit(1, "mute"), "queued")
        self.assertEqual(m.submit(2, "pause"), "busy")
        self.assertEqual(m.pending.sequence, 1)
        m.controller()
        m.ack()
        self.assertEqual(m.submit(2, "pause"), "replay_rejected")

    def test_look_is_one_shot(self):
        m = Oracle()
        m.submit(1, "look", REMOTE)
        m.controller()
        self.assertEqual(m.consume("look", LOCAL), MERGED)
        self.assertEqual(m.consume("look", LOCAL), LOCAL)

    def test_clock_regression_cancels_remote(self):
        m = Oracle()
        m.submit(1, "move", REMOTE)
        m.controller()
        m.consume("move")
        m.advance(10)
        with self.assertRaises(ValueError): m.advance(9)
        self.assertEqual(m.consume("move", LOCAL), LOCAL)
        self.assertEqual(m.submit(2, "mute"), "closed")

    def test_identity_rechecked_without_relying_on_release_callback(self):
        for action, identity in itertools.product(("move", "look", "mute"), ("pawn", "generation")):
            m = Oracle()
            m.submit(1, action, REMOTE)
            if action != "mute": m.controller()
            if identity == "pawn": m.pawn = "dove"
            else: m.generation += 1
            m.controller()
            self.assertEqual(m.consume("move", LOCAL), LOCAL)
            self.assertEqual(m.consume("look", LOCAL), LOCAL)
            self.assertEqual(m.effects, [])

    def test_release_after_completed_button_cannot_undo_effect(self):
        m = Oracle()
        m.submit(1, "mute")
        m.controller()
        m.release()
        self.assertEqual(m.effects, [("mute", 0)])
        self.assertEqual(m.ack()["status"], "consumed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
