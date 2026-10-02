WalkingCensusRunner09-Publication01 -- additive source capsule; no commit/native

Frozen09 is unchanged. Its manifest is
f3ec68097357ea1ed4aeade07eadc7071f355a23c974298d4718533b00427327.
This capsule preserves reviewed author code, the include correction, native driver,
guarded Build/Census runners and actual offline regression tests. It introduces no
collision algorithm or production integration. Coordinator reports independent
09 PASS23/25; that report is not invented as an independently inspected receipt.

Publication boundary
manifest.json is the explicit publication allowlist, plus itself. Preserve raw
bytes with Git -text for these paths. Stage only those explicit paths. No assets,
DLL/lib/obj/PDB, engine/vendor source, raw runtime logs, Saved/DDC, runs, Python cache
or compiler outputs belong in publication. replay.py audits inventory/extensions,
reparse paths, file hashes and the original frozen-source correspondence.

closure.json maps all37 reviewed09 files: three byte-identical public Git blob
dependencies, one local alias for the duplicated strict ABI, and33 local files.
36 reconstructed files are byte-identical to09. strict-build-result.json alone is
sanitized: machine artifact/log locations were removed; inherited06 counts, flags,
source hashes and original receipt hash remain. It is NOT09 native build evidence.
The original local09 manifest and inputs.json retain local paths AS DECLARED
PREREQUISITES, never as offline replay reads. There is no silent active-tree import.

Public dependencies
Repository: https://github.com/ShmuelSokol/3rdbhmk.git
Commit:8d804acb4b2525f482c33e325916fe25623faa63
Each public reference records commit/path/Git blob ID AND SHA256. The three reused
author dependencies are OwnedChildJob.cs, MeasuredProfiles.h and SupportCoverage.h.
All112 required MikdashRuntime source inputs also resolve to public Git objects,
including published isolated source snapshots where the canonical project path
differs. Two need an EXPLICIT LF-to-CRLF reconstruction to reproduce the frozen
required bytes; both source and materialized hashes are recorded. They are checked
but not copied into this capsule. No unpublished/private source is assumed present.

Fresh offline replay
Use Python3.11+ (standard library), Git and PowerShell7. Supply a repository whose
object store already contains the declared commit and blobs. Fetching public Git
objects is preparation, not part of offline replay. Replay sets GIT_NO_LAZY_FETCH=1.

 python -B replay.py --repo <public-repo-or-bare-cache> --output <fresh-directory>
   --pwsh <PowerShell7-executable>

It materializes only the37-file reviewed source/test layout, executes the original
23 Python tests and25 PowerShell policy/parser checks, checks all112 public native
source pins, audits publication inventory and verifies tests preserved source bytes.
No frozen09 verify.py, runner native entrypoint, Add-Type, compiler, UE, IPC or
active project input is executed/read. Native wrappers remain author source to
review, not launch commands for this portable replay. Results/logs go only to the
fresh output, outside the capsule. Missing public blobs or tools fail explicitly.

Native prerequisites and limitation
native-prerequisites.json declares exact package/source/library pins. All34 assets,
installed UE/SDK, strict library and future compiled probe/module seals are omitted.
No native build/census is portable or admitted merely because offline replay passes.
The sanitized inherited receipt intentionally cannot satisfy the original native
staging path. A coordinator-reviewed local hydration must restore/verify required
native evidence and exact engine/assets, before the unchanged9GiB entry /4GiB owned
/2GiB reserve policy can admit any build. Present free commit is below9GiB.
Actual API/linkage, instance compatibility, dependency load completeness, writer
fence, solid containment and world readiness remain HOLD. No guards were lowered.

Actual Git-object replay is recorded in separate sanitized publication evidence.
New capsule files are exported through an isolated temporary Git tree (no commit);
public dependencies are fetched from the public remote into a fresh bare cache.
The publication working tree/index and frozen09 are not modified. This preserves
the reviewed capability for later integration; it does not claim native acceptance.
