# Packaged acceptance protocol — unfinished draft

Stopped at user-directed wrap-up. Validator authored and syntax checked only; fixture tests and complete schema example were NOT created. Do not use this draft as an accepted release gate until those tests and review are completed. Previous control-audit delivery remains untouched.

For ONE fresh release archive, record its id, SHA256 and byte size, exact map package/hash, fresh cook/package exit codes and hashed provenance logs. Every session, check and evidence record must identify this same archive. Historical packages and synthetic input are ineligible.

Use two physical operator sessions, each at most 180 seconds, with native captures/logs and timestamped observations. Session one: welcome must not capture; explicitly Start, test P and Escape pause/resume, sustained WASD/arrows on a clear route, mouse look and pointer movement outside paused viewport, bounded reviewed stair roundtrip, stopped motion while paused, focus loss/regain remaining paused, audible mute. Save muted preference and close cleanly. Session two: fresh process, observe persisted mute before any toggle; verify actual sound output and close cleanly. Stop immediately on unsafe pointer/focus/route behavior. Record process identity and operator; do not substitute method calls for physical actions.

Draft entrypoint: python validate_receipt.py receipt.json
It requires complete local archive and evidence files and checks hashes. Success means only receipt structure/integrity is complete and still requires human evidence review; it does not authenticate physical actions or prove observed behavior. No native execution occurred here.
