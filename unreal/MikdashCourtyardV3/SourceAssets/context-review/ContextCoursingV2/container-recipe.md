# Offline container-input builder — 15 September 2026

`Scripts/prepare_context_iostore_patch.py` writes response files and a JSON recipe.
It has no subprocess or engine invocation and does not open/edit a packaged
archive. Native container construction, mounting and rendered acceptance remain
coordinator-owned tests.

The initial successful single-material cook is:
`C:/Mikdash/Working-5.8/ContextPatchStudies/M_Context_CityWall-20260915T174959787Z-5363d21c/receipt.json`.
It contains four cooked packages: the CityWall master and three texture hard
dependencies. The initial patch recipe selects **only the master**, relying on
the retained base for its textures. This is not coverage of the building or
CityFacade families or their descendants.

```powershell
python Scripts/prepare_context_iostore_patch.py --self-test
python Scripts/prepare_context_iostore_patch.py --receipt C:/Mikdash/Working-5.8/ContextPatchStudies/M_Context_CityWall-20260915T174959787Z-5363d21c/receipt.json --allow-package /Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall
```

Each run creates a unique `ContainerRecipeV1-<UTC>-<id>` directory within the
isolated study. The CLI requires an explicit allowlist; repeated
`--allow-package` arguments are accepted only for the three supported masters
that the same cook explicitly requested. Being a hard dependency does not make
a package eligible. A failed/incomplete receipt, absent outputs, map activity,
changed protected source evidence, changed output hashes/file set, missing or
ambiguous metadata, escaped path, or unreviewed package segment causes refusal.

The builder verifies the SHA256 and size of **every output in the receipt**
against the current isolated files and requires the actual cooked file set to
match. It requires exactly one nonempty `packagestore.manifest` and
`scriptobjects.bin` from that cook. These are construction inputs, never entries
in a deployed container response.

Generated files:

- `IoStoreResponse.txt`: only selected `.uasset`, `.ubulk`, `.uptnl`, or
  `.m.ubulk` segments. Mounts preserve
  `../../../MikdashCourtyardV3/Content/<package-relative-path>`.
- The `.uexp` companion is required, hash-checked and listed under
  `implicitUexpInputs` in the recipe, but omitted from both response files.
- `IoStoreCommands.txt`: one `ContextCoursingV2_1_P` container, writing
  `Containers/ContextCoursingV2_1_P.utoc` and its associated data file(s).
- `PakResponse.txt`: only the authored `ContextCoursingV2-patch-marker.json` at
  `../../../MikdashCourtyardV3/ContextCoursingV2-patch-marker.json`. This gives
  the same-stem companion pak a deliberate non-package entry.
- `recipe.json`: exact argument arrays for the future UnrealPak IoStore command
  and companion-pak command, hashes, included/implicit/excluded input census,
  and explicit limitations. **No command is executed by this builder.**

The future IoStore command uses the isolated Windows cooked directory, its fresh
manifest and script descriptor, and the generated commands file. Its required
global-container output goes in `BuildOnly/global.utoc`, separate from the
candidate bundle. **Never deploy BuildOnly/global.*, AssetRegistry files, shader
libraries, or arbitrary cooked dependencies.** The candidate unit is the full
same-stem `.pak`, `.utoc`, `.ucas` bundle, including any additional data partitions
reported by native construction. This script does not certify signing/encryption
compatibility, base dependency identity, package schema compatibility, mount
priority or rendered shader correctness.

Installed source checked for this recipe (paths relative to UE Engine/Source):

- `Programs/AutomationTool/Scripts/CopyBuildToStagingDirectory.Automation.cs`
  around 4641 routes package headers and bulk/optional files to IoStore and
  omits `.uexp`; ordinary non-package files go to pak. The generic UAT route can
  also include shared shader libraries, which this narrow experiment excludes.
- The same file around 418–447 constructs Output/ContainerName/ResponseFile,
  and around 5328–5353 supplies fresh manifest, cooked directory, commands and
  script-object descriptor for filesystem cooks.
- `Developer/IoStoreUtilities/Private/IoStoreUtilities.cpp:1959–1973` resolves
  a package header to its sibling `.uexp`; a missing companion rejects that
  input. This is why the export segment is verified but not separately listed.

Verification: 12 synthetic offline tests passed for segment routing, marker-only
pak, failed/empty cook refusal, map receipt and unlisted map refusal, changed
implicit bytes, missing metadata, unrequested master/dependency rejection, path
escape, changed source-preservation evidence and response-token injection.
The actual successful cook's 19 output files were also verified and the initial
master-only recipe emitted at:
`ContainerRecipeV1-20260915T175454880991Z-e04e496b/recipe.json` within that study.
Its IoStore response has one `.uasset` row; the `.uexp` is an implicit verified
input. No containers have been produced by these offline checks.

## Audited descendants opt-in

The preparer now also accepts an explicit allowlist drawn from the exact 13
packages in the pinned dependency audit: three masters and ten discovered
instances. A descendant or any all-family cook requires `--dependency-audit`
pointing at `dependency-audit-20260915T174543Z-34988.json`. The shared validator
pins the receipt and audit-script hashes, checks passing state, both native
discovery methods, exact roots/descendants and all 13 current source hashes.
The cook must record the same audit identity and before/after preservation of
all 13 sources, and must have explicitly requested every allowed package.
No instance is automatically added to the response; repeat `--allow-package`
for each reviewed package. Unknown-parent instances elsewhere remain excluded.
The existing master-only recipe without an audit remains valid.

`--validate-audit <path>` prints validated audit identity/package/hash JSON and
writes nothing. The PowerShell cook wrapper uses this offline command as its
shared validator. Twenty synthetic builder/audit tests passed, including
current-source changes, audit-script changes, wrong roots/descendants and absent
explicit descendant audit. The real pinned audit and all 13 source hashes also
passed. Family container creation and rendering remain separate native tests.
