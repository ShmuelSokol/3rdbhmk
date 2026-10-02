Host11 author-source publication closure; source backup, NOT native acceptance.

Export every path in publication-manifest.json.files plus that manifest itself.
Keep .gitattributes (* -text). No recursive export of adjacent studies or scratch.
closure.json reconstructs exact Host11 (17 files including manifest) and rejected
Host10 (16 files including manifest), deduplicating identical author text.
No original files were sanitized or changed; all mappings have exact hashes.
The sole public dependency is the author CurvePacket09 header at commit
15e9f7dc7fa48726591cb4e83f810c006568db24. Exact path/blob/SHA are in closure.json.
It supplies both source trees; no active-tree or UE installation dependency.

Prerequisites: Python3.8+ stdlib, Git with pinned commit/path objects preloaded,
Windows MSVC C++17 environment supplied explicitly. No DXC/UE/UBT needed.
Run from this folder, replacing uppercase placeholders; OUTPUT must not exist
and must be outside the capsule. Compiler outputs and raw logs stay local there.

python -B replay.py --check-only
python -B test_publication.py
python -B git_object_replay.py --repo PUBLIC_GIT --output OUTPUT --vcvars VCVARS64_BAT

Detached reconstruction imports only the existing public commit, path trees and
one author blob into a new object store. It writes a private capsule index/tree,
checks out with core.autocrlf=true and exact-byte attributes, and runs exported
code. No new commit or active index/ref mutation. This is a sparse tree projection,
not a claim the capsule is already committed at prerequisite public HEAD.

The unchanged Host11 runner compiles ONLY ProtocolTest.cpp and executes the
protocol core shared with the candidate component. It then runs43 textual
structural checks. Expected1751 protocol checks,43 structural checks,0 failures,
byte-identical original offline receipt, plus8 publication privacy/fault tests.
Host10 is retained as rejected evidence, not silently described as a passing host.

Installed UE API path/line/hash references are historical source inspection
provenance ONLY. This portable run does NOT verify the installed engine, compile
the plugin or prove rendering. Those checks are expressly NOT EXECUTED and
separately declared in native-prerequisites.json. No licensed implementation,
engine asset, binary, raw log or private machine path is in the export.

Host11 remains an uncompiled raster/non-Nanite ISM alternative. It is not stock
HISM/Nanite shipping compatibility. Maximum64successful publications and64empty
session renewals, then HOLD; no automatic reservation/journal retirement.
Physical world/support leases and rendered/GPU acceptance remain required.
