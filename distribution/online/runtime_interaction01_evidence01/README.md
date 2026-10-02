# Portable additive execution evidence

The exact unchanged interaction helper, project ResidentDialogState, frozen
SemanticMailbox and SessionBridge passed **10 actual MSVC cases / 28 checks**.
Compile and test exited zero with exact owned-Job cleanup confirmed. Both used
512 MiB Job/process caps, with cleanup reserved inside the 60/15-second budgets.

receipt-01.json is a sanitized derivative of the frozen evidence01 receipt. It keeps
the tested-source hashes, compiler hashes/versions, command flags, exit/cleanup
results, warning, timing, memory peaks and original receipt hashes. Absolute private
paths, raw logs, binaries and local verifier dependencies are excluded. The original
source/evidence manifests identify prior immutable snapshots, not the new portable
publication manifest.

Applied / NoOp / Rejected / Unknown, expired last-branch rejection, late ACK
suppression, same-sequence replay refusal and pre-consumption timestamp behavior
are covered. The first /WX compile failed on existing mailbox C4100; cleanup was
confirmed. The /W4 retry passed with that warning retained and no source mutation.

This proves pure-header semantics, not UE actor/possession/window integration or
online delivery. The UE adapter is still uncompiled/unexecuted. No engine code or
executables are included. The publication verifier checks these hashes against the
portable source files without needing the original workstation.
