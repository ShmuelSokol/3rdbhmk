"""Independent semantic-expiry specification; no UE, IPC, wall clock or I/O.

Integer ticks represent monotonic QPC time in milliseconds for exact boundaries.
Unsafe policies exist ONLY to execute the historical scheduling counterexamples.
"""
from dataclasses import dataclass

ZERO = (0, 0, 0)


@dataclass(frozen=True)
class Command:
    sequence: int
    action: str
    value: tuple
    generation: int
    pawn: str
    end: int
    hold_end: int


class Oracle:
    def __init__(self, pawn="walker", session_end=10000, policy="guarded"):
        if pawn not in ("walker", "dove") or policy not in (
                "guarded", "dispatch_only", "controller_only"):
            raise ValueError("Unsupported model configuration")
        self.pawn, self.session_end, self.policy = pawn, session_end, policy
        self.now = 0
        self.generation = 1
        self.last_sequence = 0
        self.pending = None
        self.phase = None
        self.outcome = None
        self.consumed_at = None
        self.held = None
        self.paused = False
        self.effects = []
        self.trace = []
        self.closed = False

    def advance(self, now):
        if type(now) is not int or now < self.now:
            self.closed = True
            self.release()
            raise ValueError("Nonmonotonic/noninteger clock")
        self.now = now

    def submit(self, sequence, action, value=ZERO):
        if self.closed or self.now >= self.session_end:
            return "closed"
        if type(sequence) is not int or sequence <= self.last_sequence:
            return "replay_rejected"
        # Reserve sequence even for overload: never replay this attempt later.
        self.last_sequence = sequence
        if self.pending is not None:
            return "busy"
        if action not in ("move", "look", "interact", "pause", "mute"):
            return "invalid"
        self.pending = Command(sequence, action, value, self.generation,
                               self.pawn, min(self.now + 500, self.session_end),
                               min(self.now + 2000, self.session_end))
        self.phase, self.outcome, self.consumed_at = "dispatch", None, None
        self.trace.append(("queued", sequence, self.now))
        return "queued"  # explicitly NOT a success ACK

    def fresh(self, command, end):
        return (not self.closed and command.generation == self.generation
                and command.pawn == self.pawn and self.now < end
                and self.now < self.session_end)

    def complete(self, outcome):
        self.outcome = outcome
        self.phase = "complete"
        self.trace.append((outcome, self.pending.sequence, self.now))

    def controller(self, handler_ticks=0, effective=True):
        """PostProcessInput/button branch; movement/look only route to consumer.

        handler_ticks models a stall AFTER fresh authorization, before return.
        effective=False represents the project's void/no-op handler branches.
        """
        if type(handler_ticks) is not int or handler_ticks < 0:
            raise ValueError("Invalid simulated handler time")
        c = self.pending
        if c is None or self.phase != "dispatch":
            return
        if self.policy != "dispatch_only" and not self.fresh(c, c.end):
            self.complete("expired")
            return
        if self.paused and c.action not in ("pause", "mute"):
            self.complete("paused_rejected")
            return
        if c.action in ("move", "look"):
            self.phase = "consumer"
            return
        self.consumed_at = self.now
        if effective:
            self.effects.append((c.action, self.now))
            if c.action == "pause":
                self.set_paused(not self.paused)
        self.advance(self.now + handler_ticks)
        self.complete("consumed" if effective else "no_effect")

    def consume(self, action, local=ZERO):
        """Actual ConsumeInputVector / UpdateRotation boundary, not physics.

        Returns unclamped local + remote contributions to expose provenance.
        Actual engine scaling, clamping, inertia and collision are not modeled.
        """
        remote = ZERO
        c = self.pending
        if c and self.phase == "consumer" and c.action == action:
            if self.policy == "guarded" and not self.fresh(c, c.end):
                self.complete("expired")
            elif self.paused:
                self.complete("paused_rejected")
            else:
                remote = c.value
                self.consumed_at = self.now
                if action == "move":
                    self.held = c
                self.complete("consumed")
        elif action == "move" and self.held:
            if self.paused or not self.fresh(self.held, self.held.hold_end):
                self.held = None
            else:
                remote = self.held.value
        self.trace.append(("consumer", action, self.now, local, remote))
        return tuple(a + b for a, b in zip(local, remote))

    def set_paused(self, paused):
        self.paused = paused
        if paused:
            self.held = None
            if self.pending and self.pending.action in ("move", "look"):
                self.complete("paused_rejected")

    def release(self):
        """Out-of-band cancellation clears ONLY modeled remote ownership."""
        self.generation += 1
        self.held = None
        if self.pending and self.phase != "complete":
            self.complete("cancelled")

    def replace_pawn(self, pawn):
        if pawn not in ("walker", "dove"):
            raise ValueError("Unsupported pawn")
        self.release()
        self.pawn = pawn

    def ack(self):
        """Client-visible terminal result, with a fixed response deadline.

        Timeout is unknown to the caller even if the model knows no effect ran.
        Completed held movement survives a lost ACK only until its input lease.
        No retry or fresh-sequence resubmission is performed by this oracle.
        """
        c = self.pending
        if c is None:
            return None
        if self.now >= c.end:
            status = "unknown"
        elif self.phase != "complete":
            return "pending"
        else:
            status = self.outcome
        result = dict(sequence=c.sequence, status=status,
                      consumed_at=self.consumed_at, observed_at=self.now)
        self.pending, self.phase, self.outcome = None, None, None
        return result
