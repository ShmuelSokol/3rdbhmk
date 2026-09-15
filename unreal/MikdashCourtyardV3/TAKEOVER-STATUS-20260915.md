# Astra takeover checkpoint — 15 September 2026

Full filesystem access works. The active project is
`C:\Mikdash\Working-5.8\MikdashCourtyardV3`. The publication clone is
`C:\Mikdash\GitHub\3rdbhmk`. Claude's recent session entries are weekly-limit notices.
No editor, game, commandlet or cook remains running at this checkpoint.

## Verified and preserved

- Full gate: 11/11, including 32/32 standalone C++ math suites. Editor and Game UBT
  succeeded incrementally with zero compile actions; this was not a clean rebuild.
- Eight offline ownership/visibility guards pass. Exact frozen-geometry ownership:
  6,007 rooftop tank/panel pairs, 1,263 in hidden-building groups and 4,744 retained.
- Native read-only preflight verified all 12,014 original transforms. The persistent
  component trial created all four groups and passed counts, transform and render
  property checks BEFORE SAVE. It did not save the map.
- Candidate48 remains SHA256
  `3f986fb62e889db59b01d956d4ab63718f58366874e7e64b7ec4fd0fa62e3df1`.
  Backups and failed attempt receipts are in `..\ReviewCheckpoints\LegacyRoofZones-*`.
- User's new Old City photographs are private references outside the repository.
  See `SourceAssets/context-review/OldCityReferenceV2/reference-notes.md` for the
  street, paving, stonework, arches, ramps and lighting direction.

## Actual blocker, not a permissions issue

Windows reported 57.4 GB committed against a 68.6 GB limit before Unreal. Repeated
native attempts exhausted commit and reported that the paging file was too small.
All attempts left the saved map unchanged. No new cook or packaged build was made.
The user is connected from a phone through AnyDesk: DO NOT restart Windows, sign
out, or stop AnyDesk, networking or security services to recover memory. Clear
memory only through actions that preserve the active remote connection, then measure
again. Do not repeat identical crashing runs. No system paging or security settings
were changed. The current shell lacks the privilege needed for live page-file changes.

`EditorActorSubsystem.duplicate_actor` crashed under the commandlet before save.
Full editor retries exceeded memory, even with an empty startup map and serialized
asset preparation. The CURRENT repair instead uses the original importer's persistent
ISM component creation, copies render settings, and verifies every transform.
Use the current code, not the older duplicate-actor recipe recorded in historical notes.

## Resume after memory is available

1. Read AGENTS.md, verify no competing native jobs, run `Scripts/verify.py --build`.
2. Run a fresh read-only native preflight with UnrealEditor-Cmd and
   `-run=pythonscript -script=<project>\Scripts\release_legacy_roof_zones.py`
   `-LegacyRoofPlan=<project>\SourceAssets\context-review\LegacyRoofZonesV1\legacy-roof-zones.json`
   `-unattended -nullrhi` and a unique absolute log path. Quote paths containing spaces.
3. If preflight passes, repeat with `-LegacyRoofApply`. It checkpoints before mutation.
   Require a successful save/reopen receipt and unchanged protected maps, not just
   process exit or pre-save groups. Preserve any failure evidence.
4. Run a SEPARATE fresh process with `-LegacyRoofVerify`. Compare its groups/settings
   to the successful apply receipt: this fresh process cannot infer original settings.
5. Run `Checkpoint-Build.ps1 -Label roofzones01`, including smoke test. Then run
   `Scripts/capture_city_facade.ps1 -Archive <new archive> -Label roofzones01 -Only A1 -IncludeRoofStateViews`.
   Inspect Yechezkel, Modern and Overlay frames for removal AND restoration.
6. Verify and explicitly publish the changed map plus its unpublished dependencies,
   without sweeping unrelated clone files or raw movie-frame folders.

The current city still needs major visual correction. cp24's six frames completed;
they were not interrupted. A1 has floating legacy fixtures, K2 has an apparent
ground opening/mirrored band, and a thin camera-relative object appears in several
views. Their causes/acceptance must be tested, not assumed fixed by this repair.

Publication at this checkpoint covers the tested repair scripts, plan, tests and notes.
Claude's prior unpublished assets/maps remain intact locally. The generic publish
helper would select roughly 64 GB including raw capture frames, so it was not run.
Two unrelated codex-entries.json edits and ParochesFabricV1 in the clone stay untouched.
