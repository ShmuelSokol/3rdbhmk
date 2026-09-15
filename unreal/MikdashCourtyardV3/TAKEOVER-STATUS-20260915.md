# Astra takeover checkpoint — 15 September 2026

Full filesystem access works. The active project is
`C:\Mikdash\Working-5.8\MikdashCourtyardV3`. The publication clone is
`C:\Mikdash\GitHub\3rdbhmk`. Claude's recent session entries are weekly-limit notices.
No editor, game, commandlet or cook remains running at this checkpoint.

Latest completed material work: horizontal coursing correction is applied to
M_Context_Building, M_Context_CityWall, and M_CityFacadeV1. Native before/after cube
renders were visually inspected, all three original masters saved, and a separate
fresh Unreal process verified the corrected code. All20 project maps remain unchanged.
See SourceAssets/context-review/ContextCoursingV2/review.md for evidence, backup,
rejected captures and limits. This change fits memory without a full map load.
It is not in the old packaged cp24/download; no new cook has been made.

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
again. Do not repeat identical crashing runs. The current shell lacks the privilege
needed for live page-file changes. See the live-memory recovery update below before
assuming that a paging change was applied.

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

## Live-memory recovery helper, 15 September

Stopped only the verified idle, weekly-limited Claude CLI process (PID 22832), freeing
about 0.9 GB of system commit. AnyDesk remained running. Page file still measured
49,152 MB, system commit limit 63.86 GiB, usage about 51.3 GiB before elevation.

`Scripts/Expand-PagefileLive.ps1` prepares a live-only increase of the existing C:
page file to 65,536 MB. It requires normal Windows administrator elevation; it does
not bypass UAC, change services or registry settings, or restart. It retains at least
30 GiB of disk space. `-CheckOnly` compiles the interop without making a change.
Automatic management remains in effect, so the size after a future boot is not pinned.

An ordinary RunAs request was launched, waited at Windows administrator consent,
then returned "The operation was canceled by the user." The helper never launched;
fresh readback still showed 49,152 MB. **The increase was not applied.** Do not infer
whether the user dismissed it or Windows timed it out from that error alone.
Read `C:\Mikdash\Working-5.8\MemoryRecovery\pagefile-*.json` and fresh Windows counters
for the outcome. Require both the allocated page-file size and live commit limit to
increase. A failed verification can follow an actual change if counters lag; inspect
the current state before any retry. Do not approve Windows security prompts by automation.

Verification: helper CheckOnly passed; project gate 7/7 and standalone math suites
32/32 passed. Log: LegacyRoofZonesV1/verify-pagefile-helper-20260915T134150Z.log.
