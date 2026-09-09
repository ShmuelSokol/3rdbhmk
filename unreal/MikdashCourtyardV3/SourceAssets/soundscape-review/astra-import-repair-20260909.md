# Soundscape importer repair — 9 September 2026 UTC

No native job, asset change, map change, build, audition or source rewrite was performed by this worker.

The retained helper filename is release_soundscape_v2.py and its spec is release_soundscape_v2.spec.json. The prepared output namespace is now /Game/MikdashV3/Runtime/Audio/SoundscapeV3. The old SoundscapeV2 support assets remain untouched. Existing namespace presence (registry OR disk) refuses; automatic deletion of failed-run leftovers is removed. The command entry refuses revert and map adoption. There is no fresh namespace overwrite or reuse.

Only -SoundscapeImportOnly is eligible for native creation. -SoundscapeDryRun performs guards/discovery and writes a receipt, but cannot change the pilot, probe SoundCues, checkpoint or save. The runtime-only branch refuses the old ambient fallback. Every other on-disk map and existing audio file outside the fresh namespace is hashed. Snapshots use the shared persistent comparator, excluding transients and rebuilt instance bounds. Process inventory uses checked tasklist CSV and rejects any other editor PID.

All runtime SoundWaves are nonlooping; C++ owns take timing and crossfades. This avoids its 30-second fallback for indefinitely looping waves. Runtime import omits obsolete SoundCue construction/fallback. Every created package must exist on disk, load by the exact object path and keep its SHA256 stable; every wave reads looping=false. The receipt explicitly marks this same-process proof: fresh-process persistence and actual listening remain pending.

Offline AST/import and manifest consistency pass: 29 unchanged source recordings, zero problems. Frozen source hashes/provenance were not rewritten. No source is declared auditioned.

Before map adoption: audition wind, cloth, city and murmur takes for hiss, sharp impacts, music/intelligible speech and inappropriate room character. Map flock SpeciesName to corresponding call banks: current C++ ignores species. Wire the court crowd count (currently defaults zero), and review event overlap. Service and wingburst banks remain intentionally empty; Soundscape footstep/service calls are not wired into runtime owners. These C++ issues are outside this importer repair.

Coordinator should run independent focused review, then serial import-only with a unique log, inspect exact saved hashes, and verify from a fresh process. Do not adopt the actor or claim an improved audible experience until listening evidence exists.
