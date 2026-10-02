"""Executable ownership-contract tests; adapters are test doubles, not a walkthrough."""
from dataclasses import replace
import math
import threading
import unittest

from session_core import Connection, InputEvent, Limits, MAX_TIME_SECONDS, SessionCore, SessionError, State


class Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class Processes:
    def __init__(self):
        self.live = {}
        self.started = []
        self.stopped = []
        self.fail_start = False
        self.fail_stop = False
        self.on_start = None

    def start(self, owner):
        assert owner.process_key not in self.live
        self.live[owner.process_key] = owner
        self.started.append(owner)
        if self.on_start:
            self.on_start()
        if self.fail_start:
            raise RuntimeError("private adapter diagnostic MUST NOT reach receipt")

    def stop(self, owner):
        if self.fail_stop:
            raise RuntimeError("stop unavailable")
        previous = self.live.get(owner.process_key)
        assert previous is None or previous == owner
        self.live.pop(owner.process_key, None)
        self.stopped.append(owner)


class Streams:
    def __init__(self):
        self.live = {}
        self.inputs = []
        self.releases = []
        self.closed = []
        self.fail_open = False
        self.fail_close = False
        self.fail_release = False
        self.fail_input = False
        self.on_input = None

    def open(self, owner):
        assert owner.stream_id not in self.live
        self.live[owner.stream_id] = owner
        if self.fail_open:
            raise RuntimeError("partial stream acquisition")

    def close(self, owner):
        if self.fail_close:
            raise RuntimeError("close unavailable")
        previous = self.live.get(owner.stream_id)
        assert previous is None or previous == owner
        self.live.pop(owner.stream_id, None)
        self.closed.append(owner)

    def release_inputs(self, owner, connection_id):
        if self.fail_release:
            raise RuntimeError("release unavailable")
        self.releases.append((owner, connection_id))

    def send_input(self, owner, connection_id, event):
        assert self.live.get(owner.stream_id) == owner
        if self.on_input:
            self.on_input()
        if self.fail_input:
            raise RuntimeError("input unavailable")
        self.inputs.append((owner, connection_id, event))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.processes = Processes()
        self.streams = Streams()
        self.core = SessionCore(self.processes, self.streams,
                                Limits(capacity=2, max_queue=2, queue_seconds=10,
                                       reconnect_seconds=5, lifetime_seconds=30, event_limit=16),
                                self.clock)

    def connect(self):
        ticket = self.core.request()
        return self.core.connect(ticket.session_id, ticket.credential)

    def race(self, *functions):
        barrier = threading.Barrier(len(functions))
        outcomes = []
        result_lock = threading.Lock()

        def run(function):
            barrier.wait(timeout=3)
            try:
                result = function()
            except Exception as error:
                result = error
            with result_lock:
                outcomes.append(result)

        threads = [threading.Thread(target=run, args=(fn,), daemon=True) for fn in functions]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive(), "Lifecycle race deadlocked")
        self.assertEqual(len(outcomes), len(functions))
        return outcomes

    def test_distinct_identities_and_correct_input_routing(self):
        a, b = self.connect(), self.connect()
        owners = self.processes.started
        values = [getattr(o, k) for o in owners for k in
                  ("session_id", "process_key", "stream_id", "save_prefix", "settings_slot")]
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(owners[0].expires_at, 130)
        self.core.submit(a, InputEvent("move", 1, 0))
        self.core.submit(b, InputEvent("look", 0, -1))
        self.assertEqual([row[0] for row in self.streams.inputs], owners)

    def test_cross_session_and_forged_connection_refused(self):
        a, b = self.connect(), self.connect()
        for forged in (replace(a, session_id=b.session_id),
                       replace(a, connection_id=b.connection_id),
                       replace(a, credential=b.credential)):
            with self.assertRaises(SessionError):
                self.core.submit(forged, InputEvent("move", 1, 0))
        self.assertEqual(self.streams.inputs, [])

    def test_fifo_and_queue_limit(self):
        a, b = self.connect(), self.connect()
        c, d = self.core.request(), self.core.request()
        self.assertEqual(self.core.status(d.session_id, d.credential).queue_position, 2)
        with self.assertRaisesRegex(SessionError, "Queue full"):
            self.core.request()
        self.core.cancel(a.session_id, a.credential)
        self.assertEqual(self.processes.started[-1].session_id, c.session_id)
        self.assertEqual(self.core.status(d.session_id, d.credential).queue_position, 1)
        self.assertEqual(len(self.processes.live), 2)

    def test_zero_queue_capacity(self):
        self.core = SessionCore(self.processes, self.streams, Limits(capacity=1, max_queue=0), self.clock)
        self.connect()
        with self.assertRaisesRegex(SessionError, "Queue full"):
            self.core.request()

    def test_queue_expiry_exact_boundary_and_no_allocation(self):
        self.connect(), self.connect()
        ticket = self.core.request()
        self.clock.advance(10)
        with self.assertRaises(SessionError):
            self.core.connect(ticket.session_id, ticket.credential)
        self.assertEqual(len(self.processes.started), 2)
        self.assertIn("queue_expired", [e.kind for e in self.core.events()])

    def test_queued_cancel_never_touches_resources(self):
        self.connect(), self.connect()
        ticket = self.core.request()
        self.core.cancel(ticket.session_id, ticket.credential)
        self.assertEqual(self.streams.closed, [])
        self.assertEqual(self.processes.stopped, [])

    def test_unattached_session_expires(self):
        ticket = self.core.request()
        self.clock.advance(5)
        self.core.tick()
        self.assertEqual(self.processes.live, {})
        with self.assertRaises(SessionError):
            self.core.connect(ticket.session_id, ticket.credential)

    def test_disconnect_releases_and_reconnect_rotates(self):
        connection = self.connect()
        self.core.submit(connection, InputEvent("move", 1, 0))
        self.core.disconnect(connection)
        self.assertEqual(self.streams.releases[-1][1], connection.connection_id)
        with self.assertRaises(SessionError):
            self.core.submit(connection, InputEvent("move", 1, 0))
        with self.assertRaises(SessionError):
            self.core.submit(replace(connection, connection_id=None), InputEvent("move", 1, 0))
        new = self.core.connect(connection.session_id, connection.credential)
        self.assertNotEqual(new.credential, connection.credential)
        self.assertNotEqual(new.connection_id, connection.connection_id)
        with self.assertRaises(SessionError):
            self.core.disconnect(connection)
        self.core.submit(new, InputEvent("look", .5, -.5))
        self.assertEqual(len(self.processes.started), 1)

    def test_concurrent_reconnect_only_one_wins(self):
        old = self.connect()
        self.core.disconnect(old)
        results = self.race(*(lambda: self.core.connect(old.session_id, old.credential) for _ in range(2)))
        self.assertEqual(sum(type(r) is Connection for r in results), 1)
        self.assertEqual(sum(isinstance(r, SessionError) for r in results), 1)

    def test_duplicate_initial_attachment_refused(self):
        ticket = self.core.request()
        self.core.connect(ticket.session_id, ticket.credential)
        with self.assertRaises(SessionError):
            self.core.connect(ticket.session_id, ticket.credential)

    def test_reconnect_exact_expiry_refused(self):
        connection = self.connect()
        self.core.disconnect(connection)
        self.clock.advance(5)
        with self.assertRaises(SessionError):
            self.core.connect(connection.session_id, connection.credential)
        self.assertEqual(self.processes.live, {})

    def test_reconnect_never_extends_absolute_lifetime(self):
        connection = self.connect()
        self.clock.advance(28)
        self.core.disconnect(connection)
        self.clock.advance(1)
        connection = self.core.connect(connection.session_id, connection.credential)
        self.clock.advance(1)
        with self.assertRaises(SessionError):
            self.core.submit(connection, InputEvent("interact"))
        self.assertEqual(self.processes.live, {})

    def test_expiry_vs_input_race_no_dispatch(self):
        connection = self.connect()
        self.clock.advance(30)
        results = self.race(self.core.tick, lambda: self.core.submit(connection, InputEvent("move", 1)))
        self.assertEqual(sum(isinstance(r, SessionError) for r in results), 1)
        self.assertEqual(self.streams.inputs, [])
        self.assertEqual(len(self.processes.stopped), 1)

    def test_disconnect_vs_input_serializes_release_after_any_dispatch(self):
        connection = self.connect()
        history = []
        original_release = self.streams.release_inputs

        def release(owner, binding):
            history.append("release")
            original_release(owner, binding)

        self.streams.release_inputs = release
        self.streams.on_input = lambda: history.append("input")
        results = self.race(lambda: self.core.disconnect(connection),
                            lambda: self.core.submit(connection, InputEvent("move", 1)))
        self.assertTrue(all(r is None or isinstance(r, SessionError) for r in results))
        self.assertIn(history, (["release"], ["input", "release"]))

    def test_wrong_owner_and_stale_crash_cannot_stop_replacement(self):
        a, b = self.connect(), self.connect()
        owner = self.processes.started[0]
        queued = self.core.request()
        with self.assertRaisesRegex(SessionError, "Ownership mismatch"):
            self.core.report_crash(replace(owner, process_key=self.processes.started[1].process_key))
        self.assertTrue(self.core.report_crash(owner))
        self.assertFalse(self.core.report_crash(owner))
        self.assertEqual(len(self.processes.stopped), 1)
        self.assertEqual({o.session_id for o in self.processes.live.values()}, {b.session_id, queued.session_id})

    def test_concurrent_crash_and_cancel_cleanup_once(self):
        connection = self.connect()
        owner = self.processes.started[0]
        results = self.race(lambda: self.core.report_crash(owner),
                            lambda: self.core.cancel(connection.session_id, connection.credential))
        self.assertTrue(all(r in (None, True, False) or isinstance(r, SessionError) for r in results))
        self.core.tick()
        self.assertEqual(len(self.processes.stopped), 1)
        self.assertEqual(len(self.streams.closed), 1)

    def test_partial_process_start_failure_disposed(self):
        self.processes.fail_start = True
        with self.assertRaisesRegex(SessionError, "Provision failed"):
            self.core.request()
        self.assertEqual(self.processes.live, {})
        self.assertEqual(len(self.streams.closed), 1)
        self.assertNotIn("private", repr(self.core.events()))

    def test_partial_stream_start_failure_disposed(self):
        self.streams.fail_open = True
        with self.assertRaises(SessionError):
            self.core.request()
        self.assertEqual(self.processes.live, {})
        self.assertEqual(self.streams.live, {})

    def test_cleanup_failure_quarantines_capacity_and_retries_only_unfinished(self):
        self.core = SessionCore(self.processes, self.streams,
                                Limits(capacity=1, max_queue=1), self.clock)
        connection = self.connect()
        queued = self.core.request()
        self.processes.fail_stop = True
        self.core.cancel(connection.session_id, connection.credential)
        self.assertEqual(self.core.cleanup_pending(), 1)
        self.assertEqual(len(self.processes.started), 1)
        self.core.tick()
        self.assertEqual(len(self.streams.closed), 1)
        with self.assertRaises(SessionError):
            self.core.submit(connection, InputEvent("move", 1))
        self.processes.fail_stop = False
        self.core.tick()
        self.assertEqual(self.core.cleanup_pending(), 0)
        self.assertEqual(self.processes.started[-1].session_id, queued.session_id)
        self.assertEqual(len(self.streams.closed), 1)

    def test_stream_cleanup_failure_also_holds_capacity(self):
        connection = self.connect()
        self.streams.fail_close = True
        self.core.cancel(connection.session_id, connection.credential)
        self.assertEqual(self.core.cleanup_pending(), 1)
        self.core.tick()
        self.assertEqual(len(self.processes.stopped), 1)
        self.streams.fail_close = False
        self.core.tick()
        self.assertEqual(self.core.cleanup_pending(), 0)

    def test_input_release_failure_fails_closed(self):
        connection = self.connect()
        self.streams.fail_release = True
        with self.assertRaises(SessionError):
            self.core.disconnect(connection)
        with self.assertRaises(SessionError):
            self.core.connect(connection.session_id, connection.credential)
        self.assertEqual(self.processes.live, {})
        self.assertEqual(self.streams.live, {})

    def test_dispatch_failure_revokes_session(self):
        connection = self.connect()
        self.streams.fail_input = True
        with self.assertRaisesRegex(SessionError, "Input adapter failed"):
            self.core.submit(connection, InputEvent("move", 1))
        self.assertEqual(self.processes.live, {})

    def test_invalid_inputs_never_reach_adapter(self):
        connection = self.connect()
        for event in (InputEvent("execute"), InputEvent("move", math.nan),
                      InputEvent("look", math.inf), InputEvent("move", 2),
                      InputEvent("pause", 1), InputEvent("move", True), {"action": "move"}):
            with self.assertRaises(SessionError):
                self.core.submit(connection, event)
        self.assertEqual(self.streams.inputs, [])

    def test_invalid_credentials_are_safe(self):
        ticket = self.core.request()
        for value in (None, "", "x" * 129, "\u2603" * 40):
            with self.assertRaisesRegex(SessionError, "Invalid session credential"):
                self.core.connect(ticket.session_id, value)
        with self.assertRaises(SessionError):
            self.core.connect([], ticket.credential)

    def test_hostile_session_ids_rejected_by_every_authenticated_api(self):
        ticket = self.core.request()
        for bad in ([], {}, None, 123, b"session", "", "s" * 129):
            for method in (self.core.connect, self.core.status, self.core.cancel):
                with self.subTest(kind=type(bad).__name__, method=method.__name__):
                    with self.assertRaises(SessionError):
                        method(bad, ticket.credential)
        self.assertEqual(len(self.processes.live), 1)

    def test_malformed_connection_fields_rejected_without_type_errors(self):
        connection = self.connect()
        for field in ("session_id", "connection_id", "credential"):
            for bad in ([], {}, None, 123, b"binding", "", "x" * 129):
                forged = replace(connection, **{field: bad})
                with self.subTest(field=field, kind=type(bad).__name__):
                    with self.assertRaises(SessionError):
                        self.core.submit(forged, InputEvent("move", 1))
                    with self.assertRaises(SessionError):
                        self.core.disconnect(forged)
        self.assertEqual(self.streams.inputs, [])
        self.assertEqual(self.streams.releases, [])

    def test_hostile_crash_ownership_fields_rejected(self):
        self.connect()
        owner = self.processes.started[0]
        for field in ("session_id", "process_key", "stream_id", "save_prefix", "settings_slot"):
            for bad in ([], {}, None, "", "x" * 129):
                with self.assertRaises(SessionError):
                    self.core.report_crash(replace(owner, **{field: bad}))
        for bad in (None, "later", math.nan, math.inf, True):
            with self.assertRaises(SessionError):
                self.core.report_crash(replace(owner, expires_at=bad))
        self.assertEqual(self.processes.stopped, [])

    def test_adapter_exception_credentials_never_escape(self):
        connection = self.connect()

        def fail_with_secret(*args):
            raise RuntimeError("upstream URL credential=" + connection.credential)

        self.streams.send_input = fail_with_secret
        self.streams.close = fail_with_secret
        self.processes.stop = fail_with_secret
        with self.assertRaises(SessionError) as failure:
            self.core.submit(connection, InputEvent("move", 1))
        self.assertEqual(str(failure.exception), "Input adapter failed")
        self.assertIsNone(failure.exception.__context__)
        self.assertIsNone(failure.exception.__cause__)
        self.assertNotIn(connection.credential, repr(self.core.events()))
        self.assertEqual(self.core.cleanup_pending(), 1)
        self.connect()  # Remaining capacity only; failed slot is still occupied.
        first, second = self.core.request(), self.core.request()
        self.assertEqual(len(self.processes.started), 2)
        self.assertEqual(self.core.status(second.session_id, second.credential).queue_position, 2)
        with self.assertRaisesRegex(SessionError, "Queue full"):
            self.core.request()

    def test_reentry_fails_closed_without_deadlock(self):
        self.processes.on_start = self.core.tick
        with self.assertRaises(SessionError):
            self.core.request()
        self.assertEqual(self.processes.live, {})

    def test_clock_rejects_backwards_and_nonfinite(self):
        self.core.tick()
        for value in (99, math.nan, math.inf, "now"):
            self.clock.value = value
            with self.assertRaisesRegex(SessionError, "Invalid monotonic clock"):
                self.core.tick()

    def test_limits_are_finite_and_bounded(self):
        for kwargs in ({"capacity": 0}, {"capacity": True}, {"max_queue": -1},
                       {"max_queue": 10001}, {"event_limit": 0}, {"queue_seconds": math.inf},
                       {"lifetime_seconds": 86401}, {"reconnect_seconds": 0}):
            with self.assertRaises(ValueError):
                Limits(**kwargs)

    def test_bounded_retention_and_secret_free_events(self):
        credentials = []
        for _ in range(30):
            connection = self.connect()
            credentials.append(connection.credential)
            self.core.cancel(connection.session_id, connection.credential)
        self.assertEqual(len(self.core._sessions), 0)
        self.assertEqual(len(self.core.events()), 16)
        for credential in credentials:
            self.assertNotIn(credential, repr(self.core.events()))
        self.assertNotIn(connection.credential, repr(connection))

    def test_shutdown_idempotent_and_never_admits_queue(self):
        self.connect(), self.connect()
        self.core.request()
        self.core.shutdown()
        self.core.shutdown()
        self.assertEqual(len(self.processes.started), 2)
        self.assertEqual(len(self.processes.stopped), 2)
        self.assertEqual(self.core._sessions, {})
        with self.assertRaisesRegex(SessionError, "shut down"):
            self.core.request()

    def test_concurrent_admission_never_exceeds_bounds(self):
        results = self.race(*(self.core.request for _ in range(10)))
        self.assertEqual(sum(isinstance(r, SessionError) for r in results), 6)
        self.assertEqual(len(self.core._sessions), 4)
        self.assertEqual(len(self.processes.live), 2)

    def test_crash_waits_for_inflight_dispatch_then_disposes_exact_owner(self):
        connection = self.connect()
        owner = self.processes.started[0]
        entered, finish = threading.Event(), threading.Event()
        history = []
        errors = []

        def held_dispatch():
            entered.set()
            if not finish.wait(timeout=3):
                raise RuntimeError("test dispatch timed out")
            history.append("input")

        self.streams.on_input = held_dispatch
        original_stop = self.processes.stop

        def stop(identity):
            history.append("stop")
            original_stop(identity)

        self.processes.stop = stop

        def dispatch():
            try:
                self.core.submit(connection, InputEvent("move", 1))
            except Exception as error:
                errors.append(error)

        sender = threading.Thread(target=dispatch, daemon=True)
        sender.start()
        self.assertTrue(entered.wait(timeout=3))
        crash = threading.Thread(target=lambda: self.core.report_crash(owner), daemon=True)
        crash.start()
        finish.set()
        sender.join(timeout=3)
        crash.join(timeout=3)
        self.assertFalse(sender.is_alive() or crash.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(history, ["input", "stop"])
        with self.assertRaises(SessionError):
            self.core.submit(connection, InputEvent("move", 1))

    def test_duplicate_disconnect_does_not_renew_grace(self):
        connection = self.connect()
        self.core.disconnect(connection)
        self.clock.advance(4)
        with self.assertRaises(SessionError):
            self.core.disconnect(connection)
        self.clock.advance(1)
        with self.assertRaises(SessionError):
            self.core.connect(connection.session_id, connection.credential)

    def test_queued_time_counts_toward_absolute_lifetime(self):
        self.core = SessionCore(self.processes, self.streams,
                                Limits(capacity=1, queue_seconds=60, lifetime_seconds=10), self.clock)
        self.connect()
        queued = self.core.request()
        self.clock.advance(10)
        self.core.tick()
        self.assertEqual(len(self.processes.started), 1)
        with self.assertRaises(SessionError):
            self.core.connect(queued.session_id, queued.credential)

    def test_shutdown_retries_failed_cleanup_without_reopening(self):
        self.connect()
        self.processes.fail_stop = True
        self.core.shutdown()
        self.assertEqual(self.core.cleanup_pending(), 1)
        self.processes.fail_stop = False
        self.core.shutdown()
        self.assertEqual(self.core.cleanup_pending(), 0)
        self.assertEqual(len(self.streams.closed), 1)
        self.assertEqual(len(self.processes.started), 1)

    def delayed_other_cleanup(self, attached=True, lifetime=10, delay=11, reconnect=20):
        """A different owner's pending cleanup consumes the target's lease."""
        self.core = SessionCore(self.processes, self.streams,
                                Limits(capacity=2, max_queue=2, queue_seconds=5,
                                       reconnect_seconds=reconnect, lifetime_seconds=lifetime), self.clock)
        other = self.connect()
        other_owner = self.processes.started[0]
        ticket = self.core.request()
        target = self.core.connect(ticket.session_id, ticket.credential) if attached else ticket
        self.processes.fail_stop = True
        self.core.cancel(other.session_id, other.credential)
        self.processes.fail_stop = False
        original_stop = self.processes.stop

        def delayed_stop(owner):
            if owner == other_owner:
                self.clock.advance(delay)
            original_stop(owner)

        self.processes.stop = delayed_stop
        return target

    def test_submit_rechecks_lifetime_after_other_cleanup_advances_clock(self):
        target = self.delayed_other_cleanup()
        with self.assertRaises(SessionError):
            self.core.submit(target, InputEvent("move", 1))
        self.assertEqual(self.clock.value, 111)
        self.assertEqual(self.streams.inputs, [])
        self.assertEqual(self.core.cleanup_pending(), 1)
        self.core.tick()
        self.assertEqual(self.processes.live, {})

    def test_connect_rechecks_lifetime_after_other_cleanup(self):
        target = self.delayed_other_cleanup(attached=False)
        with self.assertRaises(SessionError):
            self.core.connect(target.session_id, target.credential)
        self.assertFalse(any(e.session_id == target.session_id and e.kind == "connected"
                             for e in self.core.events()))

    def test_connect_rechecks_attachment_grace_after_other_cleanup(self):
        target = self.delayed_other_cleanup(attached=False, lifetime=30, reconnect=5, delay=6)
        with self.assertRaises(SessionError):
            self.core.connect(target.session_id, target.credential)
        self.assertIn("reconnect_expired", [e.kind for e in self.core.events()])

    def test_status_rechecks_lifetime_after_other_cleanup(self):
        target = self.delayed_other_cleanup()
        with self.assertRaises(SessionError):
            self.core.status(target.session_id, target.credential)

    def test_disconnect_rechecks_lifetime_after_other_cleanup(self):
        target = self.delayed_other_cleanup()
        with self.assertRaises(SessionError):
            self.core.disconnect(target)
        self.assertFalse(any(binding == target.connection_id for _, binding in self.streams.releases))

    def test_request_deadline_starts_after_maintenance_callbacks(self):
        self.delayed_other_cleanup()
        ticket = self.core.request()
        snapshot = self.core.status(ticket.session_id, ticket.credential)
        self.assertEqual(self.clock.value, 111)
        self.assertEqual(snapshot.expires_at, 121)
        self.assertEqual(self.processes.started[-1].expires_at, 121)

    def test_queue_expiring_during_cleanup_is_not_provisioned(self):
        self.delayed_other_cleanup(lifetime=30, delay=0)
        # Retry cannot free the old slot yet, allowing another request to queue.
        self.processes.fail_stop = True
        ticket = self.core.request()
        original_stop = self.processes.stop
        self.processes.fail_stop = False

        def delayed_stop(owner):
            self.clock.advance(6)
            original_stop(owner)

        self.processes.stop = delayed_stop
        self.core.tick()
        self.assertFalse(any(o.session_id == ticket.session_id for o in self.processes.started))
        with self.assertRaises(SessionError):
            self.core.status(ticket.session_id, ticket.credential)

    def test_expiry_during_process_start_prevents_stream_acquisition(self):
        self.core = SessionCore(self.processes, self.streams, Limits(lifetime_seconds=10), self.clock)
        self.processes.on_start = lambda: self.clock.advance(11)
        opened = []
        self.streams.open = lambda owner: opened.append(owner)
        with self.assertRaisesRegex(SessionError, "Provision failed"):
            self.core.request()
        self.assertEqual(opened, [])
        self.assertEqual(self.processes.live, {})
        self.assertNotIn("ready", [e.kind for e in self.core.events()])

    def test_expiry_during_stream_open_prevents_ready_ticket(self):
        self.core = SessionCore(self.processes, self.streams, Limits(lifetime_seconds=10), self.clock)
        original_open = self.streams.open

        def delayed_open(owner):
            original_open(owner)
            self.clock.advance(11)

        self.streams.open = delayed_open
        with self.assertRaisesRegex(SessionError, "Provision failed"):
            self.core.request()
        self.assertEqual(self.processes.live, {})
        self.assertEqual(self.streams.live, {})
        self.assertNotIn("ready", [e.kind for e in self.core.events()])

    def test_initial_attachment_grace_starts_at_actual_readiness(self):
        self.processes.on_start = lambda: self.clock.advance(3)
        ticket = self.core.request()
        self.assertEqual(self.clock.value, 103)
        self.clock.advance(4)
        connection = self.core.connect(ticket.session_id, ticket.credential)
        self.assertEqual(self.core.status(connection.session_id, connection.credential).expires_at, 130)

    def test_disconnect_deadline_uses_fresh_time_but_release_does_not_renew_it(self):
        target = self.delayed_other_cleanup(lifetime=30, delay=3, reconnect=5)
        original_release = self.streams.release_inputs

        def delayed_release(owner, binding):
            original_release(owner, binding)
            self.clock.advance(2)

        self.streams.release_inputs = delayed_release
        self.core.disconnect(target)
        self.assertEqual(self.clock.value, 105)
        self.clock.advance(3)
        with self.assertRaises(SessionError):
            self.core.connect(target.session_id, target.credential)

    def test_expiry_during_disconnect_release_revokes_without_retry_loop(self):
        connection = self.connect()
        original_release = self.streams.release_inputs

        def delayed_release(owner, binding):
            original_release(owner, binding)
            self.clock.advance(6)

        self.streams.release_inputs = delayed_release
        with self.assertRaises(SessionError):
            self.core.disconnect(connection)
        self.assertEqual(len(self.streams.releases), 1)
        self.assertEqual(self.core.cleanup_pending(), 1)
        with self.assertRaises(SessionError):
            self.core.connect(connection.session_id, connection.credential)

    def test_later_provisioning_consumes_earlier_queue_deadline(self):
        self.core = SessionCore(self.processes, self.streams,
                                Limits(capacity=2, queue_seconds=5, lifetime_seconds=30), self.clock)
        a, b = self.connect(), self.connect()
        first, second = self.core.request(), self.core.request()
        # Keep occupied sessions disconnected while the queue is still live.
        self.core.disconnect(a)
        self.core.disconnect(b)
        # Trusted crash releases one slot; provision first takes six seconds.
        self.processes.on_start = lambda: self.clock.advance(6)
        self.core.report_crash(self.processes.started[0])
        self.assertTrue(any(o.session_id == first.session_id for o in self.processes.started))
        self.assertFalse(any(o.session_id == second.session_id for o in self.processes.started))
        with self.assertRaises(SessionError):
            self.core.status(second.session_id, second.credential)

    def test_huge_int_axes_raise_sessionerror_not_overflow(self):
        connection = self.connect()
        for value in (10 ** 400, -(10 ** 400)):
            for event in (InputEvent("move", value), InputEvent("look", 0, value)):
                with self.assertRaises(SessionError):
                    self.core.submit(connection, event)
        self.assertEqual(self.streams.inputs, [])

    def test_huge_int_limits_raise_valueerror_not_overflow(self):
        for name in ("capacity", "max_queue", "event_limit", "queue_seconds",
                     "reconnect_seconds", "lifetime_seconds"):
            for value in (10 ** 400, -(10 ** 400)):
                with self.assertRaises(ValueError):
                    Limits(**{name: value})

    def test_huge_int_clock_and_ownership_raise_sessionerror_not_overflow(self):
        self.connect()
        owner = self.processes.started[0]
        for value in (10 ** 400, -(10 ** 400), MAX_TIME_SECONDS + 1):
            with self.assertRaises(SessionError):
                self.core.report_crash(replace(owner, expires_at=value))
            self.clock.value = value
            with self.assertRaises(SessionError):
                self.core.tick()
            self.clock.value = 100
        self.assertEqual(self.processes.stopped, [])

    def test_invalid_clock_after_acquisition_disposes_partial_owner(self):
        def corrupt_clock():
            self.clock.value = 10 ** 400

        self.processes.on_start = corrupt_clock
        with self.assertRaises(SessionError):
            self.core.request()
        self.assertEqual(self.processes.live, {})
        self.assertEqual(self.streams.live, {})


if __name__ == "__main__":
    unittest.main()
