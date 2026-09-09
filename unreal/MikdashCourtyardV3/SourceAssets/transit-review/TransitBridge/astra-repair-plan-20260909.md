# Transit bridge guarded placement repair — 9 September 2026 UTC

Prepared for serial coordinator execution. No Unreal, map, asset, build or publication was run by this worker.

The prepared placement helper had Python bool names with the C++ b_ prefix, a coordinator guard that continued after unreadable activation state, exact-class matching that missed derived actors, and a raw actor-count delta vulnerable to transient world actors. These are now repaired. An absent editor world returns an empty map identity and is handled by the existing explicit target-load rule.

The six bool properties use Unreal Python names; required actors and duplicate/coordinator detection use reflected MathLibrary.class_is_child_of (UE Python has no Object.is_a). An unloaded coordinator class or failed activation read refuses placement. Guards execute inside the receipt/error path, before mutation; all spec/job execution is inside editor-cleanup try/finally. Map snapshots use the shared release_place_assets persistent comparator, including ordinary mesh bounds but excluding transient actors and regenerated instance bounds. Exactly one new bridge class (including subclasses) must reopen. Unrelated persistent actors must compare equal. Every other map on disk is protected, in addition to the authored protected list. The original settings, main-map target and checkpoint rule remain.

Offline consistency passed: 25 invariants, 16 authored route stops. This is not the current native placed-stop count and not runtime evidence. AST/import checks passed. A focused independent review is requested before native execution. The coordinator must inspect process ownership, run guarded placement serially, and then a separate real-RHI PIE probe; save/reopen alone proves neither rendering nor boarding.

The bridge animates its own static figures using transit exchange events and crowd-field assets. It does not implement real CrowdPartyHost population handover, and no claim is made that the separate 24 skeletal residents transfer into vehicles. Visual quality, stop-ground alignment and bounded live event behavior remain pending native evidence.
