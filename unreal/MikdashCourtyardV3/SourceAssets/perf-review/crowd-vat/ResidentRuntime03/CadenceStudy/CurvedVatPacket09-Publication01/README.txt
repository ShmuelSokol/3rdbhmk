CurvedVatPacket09 portable author-source closure (native HOLD)

Publication boundary: every path in publication-manifest.json.files plus that
manifest itself. Export relative paths unchanged with .gitattributes (* -text).
Do not recursively export the adjacent study, logs, executables, assets or engine.
The original frozen 32 payloads/manifest remain untouched. closure.json accounts
for all32: two exact public Git prerequisites,22 local reconstructed inputs and
8 explicitly omitted historical/local-runner files. Sanitization is declared per
file; evidence/samples.csv is lossless text of the frozen compressed CSV.

Preload the public repository and commit in closure.json. Both prerequisite
paths,100644 modes, Git blob IDs and SHA256s must match. The replay disables lazy
fetch and needs only the existing commit, ancestor trees and two author blobs.
No UE installation, native assets or Epic implementation is part of this export.

Offline prerequisites: Python3.8+ standard library, Git, Windows MSVC C++17
compiler environment, and exact DXC binary hash in native-prerequisites.json.
The --vcvars and --dxc paths are explicit installed-tool inputs, not exported.
Use a fresh nonexistent OUTPUT outside this capsule; temporary logs/executables
stay there. Run from this folder (replace uppercase placeholders):

python -B replay.py --check-only
python -B test_publication.py
python -B git_object_replay.py --repo PUBLIC_GIT --output OUTPUT --vcvars VCVARS64_BAT --dxc DXC_EXE

This imports existing public objects into a new temporary Git object store,
detaches HEAD at the pinned public commit, writes an author capsule tree through
an isolated index and checks out exact bytes even with core.autocrlf=true.
It creates NO commit and writes NO active index/ref. This sparse reconstruction
is not a claim that the capsule has already been committed at public HEAD.
The exported entry then rebuilds the actual C++ test and emitted stock material
source, compares all208 sample rows byte-for-byte, replays the actual graph and
runs the offline HLSL syntax compiler. Receipts/logs are written only to OUTPUT.

Expected:1074 C++ checks,1501 graph checks,208 samples, DXC exit0; nine publication
fault tests. No HISM/native/GPU invocation occurs. The C++ shader-equivalent and
recording graph tests do not establish rendered material or motion-vector proof.

Independent frozen09 review passed the same scoped checks and preserved all32,
152 and78 source pins. The extra HISM dirty concern was resolved by installed
UE5.8 manager/flush behavior; it is not an established defect. Paired publication
and render-ACK host, full world/support/body gates and native integration remain
missing/HOLD. See native-prerequisites.json for excluded requirements. This
capsule backs up implementation; it does not adopt it into production.

Privacy correction: the original projectDir host path was replaced only in the
derivative spec; closure.json declares it. Decoded metadata host paths are now
checked independently of hashes, with the exact non-Users regression fixture.
URLs and Unreal package references remain intact. The preserved first and final
pre-fix receipts passed replay but their privatePathDataExported=0 claim was
incorrect; evidence/privacy-finding01.json records their publication HOLD.
