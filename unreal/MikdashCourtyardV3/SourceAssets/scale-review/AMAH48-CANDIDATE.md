# Architecture-only 48 cm candidate

The selected book amah is author-approved 48 cm. This script makes a **partial review candidate**, never a default-map migration. All dependent systems remain explicitly unconverted; promotion is unavailable.

`Scripts/release_amah48_candidate.py` reads current GameDefaultMap from config at invocation. Its exact package allowlist is the 2,633 architecture manifest assets under `/Game/MikdashV3/Architecture/architecture_<assetName>`, each hashed. It scales only matching simple, unattached, identity-placed StaticMeshActors by .96 about fixed Temple origin [0,0,0]. World coordinates were baked in these source meshes. Shared mesh geometry/material/collision assets stay byte-identical; actor scale also transforms their existing collision, whose walking behavior still requires testing. Bounds must transform by .96 within0.1cm.

Fitted finishes, doors and friezes are deliberately excluded: the prior migration inventory names candidate families but does not supply a reviewed exact current asset/placement allowlist. The script will not classify them by label substring or proximity. Their incomplete alignment is a conspicuous dependency, not an accepted 48cm scene. Modern city, Kotel, people and all other actors retain snapshot equality.

Main map and all original architecture asset hashes are captured at runtime, checkpointed as evidence and rechecked before duplication and in finally. Only main map is physically copied because no original asset is mutated. Fresh timestamped candidate package refuses overwrite; external-actor packages currently refuse pending expanded checkpoint support. Full numeric/component snapshots use the existing resident release helper, recording its hash; nonselected scene must remain identical and candidate must read back after save/reopen. Failure leaves its receipt and candidate for inspection; no source restoration is needed because source writes are prohibited.

Unconverted dependencies are serialized in every receipt: fitted additions; vessels; physical-offset placements; residents/crowd/transit; service/access triggers; water; tours; acoustic regions and FX/lights; enclosure/context joins; world-space material masks; save versions; walking/collision/visual/cook acceptance. No configuration or runtime constants change. Do not launch this candidate as a finished walkthrough.

Offline command from project root: engine Python `Scripts/release_amah48_candidate.py`.

Native invocation, root's serial slot only, main already loaded with no dirty packages/PIE:

```python
import sys
sys.path.insert(0, r'C:\Mikdash\Working-5.8\MikdashCourtyardV3\Scripts')
import release_amah48_candidate
report = release_amah48_candidate.run(apply=True)
```

Root native execution passed on2026-09-08: amah48-candidate-20260908T144034771385Z.json records all2633 actors scaled, bounds verified, candidate saved/reopened, untouched scene and main/source assets/three protected maps unchanged. Commandlet exit0,0warnings/errors. Walking and all unconverted dependencies remain unverified; this partial map cannot be promoted.

Review strengthening: all three protected maps (original Courtyard, FutureMountV1 and CourtyardGold) are hashed in preflight/finally. Exactly 2,633 unique architecture assets/actors are required; absent/duplicate details are persisted before refusal. Each actor calls `modify(True)` before transformation to dirty its candidate package (installed UE5.8 `PyWrapperObject.cpp:1130` exposes this exact API). A compact timestamped receipt is also persisted beside this document, containing changes and snapshot/hash digests; the full scene snapshot stays in the external checkpoint. Offline AST, 2,633 asset hashes and three protected-map hashes passed after these changes. Native execution remains pending.
