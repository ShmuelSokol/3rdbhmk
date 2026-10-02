# Process04 / Receiver04 source review

**Source only, not online delivery.** No Windows child, socket, native compiler,
engine or host service has been executed. Source02/03 are frozen and unchanged.

Start with [CONTRACT.md](CONTRACT.md) for exact deadlines, ownership, ACK semantics,
supported actions, missing integration and the reserved later OS fixture test.

New executable source entry points:

- `win32_child.py`: suspended exact-handle child, one-process Windows job, explicit
  inherited stdin/NUL list, cancellable bootstrap writer, confirmed cleanup.
- `host.py`: QPC core/stream/process wiring, isolated port/key allocation, bounded
  startup, authenticated readiness, route revocation and retained cleanup capacity.
- `consumption_channel.py`: v2 semantic outcome/time/generation validation before
  adapting an authenticated result to the frozen bridge API.
- `../../native/receiver04/Bootstrap.*` and `Receiver.*`: private bootstrap,
  owned controller/movement attachment and bounded authenticated loopback pump.
- `../../native/receiver04/Authority.*`, `SemanticMailbox.h`, `OnlineController.*`,
  `OnlineMovement.*`: consumed input outcomes, controller/pawn identity fences,
  synchronous walker and dove evaluation, cinematic suppression and late-ACK refusal.

Run only the listener-free checks now:

```text
python -B -m adapters.process04.validate
```

To create a fresh immutable receipt after those checks:

```text
python -B -m adapters.process04.validate --receipt receipt-02.json
```

`harmless_child.py` is staged for the later explicitly coordinated job/private-pipe
test. This validator NEVER executes it. Native automation tests are staged only.
The independent oracle folder belongs to Wegener and is read-only to this owner.

Before any real launch: coordinator integration must provide the approved inner
executable/class/module recipe, save/settings isolation, explicit E outcome API,
look scale, authenticated streamer attachment and bounded host admission/RPC.
Native compile-only validation belongs to the coordinator's reserved slot.

Receipt01 remains historical evidence. Receipt02 corrects UE would-block/EOF
handling, idle expiry, unconfirmed stdin close and post-settings object validity.
The validator includes actual C++ control-flow checks; native seam tests are
staged, not run. See the correction section in CONTRACT.md.
