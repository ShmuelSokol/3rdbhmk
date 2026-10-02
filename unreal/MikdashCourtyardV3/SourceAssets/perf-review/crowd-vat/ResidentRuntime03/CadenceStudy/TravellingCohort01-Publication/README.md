# Frozen TravellingCohort01 evidence

Evidence publication only. The corrected study passes sustained every-member walking in 11/12 cases at120 seconds and10/12 at600 seconds. Both six-member/staggered starts still fail at600 seconds. No production adoption is authorized or claimed.

Publish **only** the exact relative paths in `manifest.json` → `publishFiles`. This directory is self-contained. Do not publish the parent study directory recursively: historic raw and compressed run logs remain local. Their paths and hashes are recorded under `omittedLocalLogs`; they are not replay dependencies. Original assessment and receipt bytes are copied unchanged under `receipts/` and may mention these omitted artifacts.

## Replay

Requires Windows, Python3.8+ standard library, and Visual Studio2022 C++ Build Tools with the x64 compiler. No Unreal, UBT, repository checkout, historical log, or Python package dependency is needed.

```
python reproduce.py --verify-only --case candidate600
python reproduce.py --case candidate600
python reproduce.py --case candidate120Verified
python reproduce.py --case baseline600Replay
```

Use `--vcvars "C:\path\to\vcvars64.bat"` if needed. Each actual replay extracts the pinned source bytes into a unique system temporary directory, compiles with `/std:c++17 /EHsc /W4 /O2`, runs the fixture and compares all six newly generated CSV files byte-for-byte against the included compressed CSVs. New logs and a replay receipt stay in that local temporary directory. It does not edit this publication directory or the frozen study.

Each case's complete source dependency set is explicit in `manifest.json` → `cases` → `inputs`: fixture.cpp; shared CrowdGroupMath.h, CrowdFieldMath.h, CrowdBoundaryCadenceStudy.h; RouteContinuityStudy.h and ExecutableRouteStudy.h; and, for candidate cases, TravellingCohortStudy.h. All compiled source is retained in gzip snapshots to preserve exact bytes across Git line-ending normalization. `reproduce.py.gz` preserves the exact publication replay helper; `reproduce.py` is its convenient text copy.

## Tests and receipts

- `baseline600Replay`:22,130,397 checks,0 failures; observational replay matches the prior twelve failed route-continuity cases.
- `candidate120Verified`:19,844,472 checks,0 failures;11/12 sustained-walking cases,24 unchanged controls,18 blocked/invalid cases.
- `candidate600`:22,676,315 checks,0 failures;10/12 sustained-walking cases. Coordinator reports independent verifier confirmation with exact six-CSV replay.
- `candidate120Replay`:19,838,298 checks,0 failures, but rejected corner-bookkeeping movement stall. Retained as failure evidence, not the accepted implementation.

Cases cover2/3/6 members, budgets48/17, prior seed13/identity47 and saved terminal starts. Added assertions cover swept formation bounds, rolling frontier progress, bounded route storage, mandatory per-member corners and independent corner advancement. Safety/math success does not erase movement failures. Per-member actual moving-frame fractions and pause-cause breakdowns are in the frozen receipts and `motion.csv.gz`.

The original `TravellingCohort01` directory, assessment and proofs have not been modified. `manifest.json` pins the eight protected repository source hashes and the frozen assessment hash. Historical scripts with wider repository dependencies are provenance, not required for this direct source replay.
