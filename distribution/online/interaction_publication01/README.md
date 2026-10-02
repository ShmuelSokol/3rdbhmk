# Interaction01 portable publication allowlist

Copy only files explicitly listed in allowlist-01.json, plus that manifest, beneath
distribution/online. Three new directories are owned: runtime_interaction01,
runtime_interaction01_evidence01, interaction_publication01. No existing published
backend or project source is changed. The overlays are review artifacts only.

Eight baseline/context dependencies match committed publication bytes exactly;
two resident files match the Windows checkout and differ from Git blobs only
by CRLF/LF. Both exact hashes are recorded and accepted for context checks; logical
repository paths and hashes are in publication-context.json. Exact copies needed
for independent patch replay are included as snapshots. New artifacts are the
explicit outcome helper/adapter, reviewed patch overlay, tests, portable tooling
and sanitized evidence. There is no engine source, binary, raw log or absolute
private workstation path in this payload.

The included candidate-local .gitattributes preserves two exact CRLF resident
dependency snapshots against the parent publication's LF rules. It changes no
existing publication attributes. All other payload files are LF.

Run verify.py --expect-manifest <SHA256>. Optional --publication-root <repository>
checks all ten dependencies against an existing publication clone. Optional
--export <new-directory> makes a fresh standalone source-only copy, never merges
into or overwrites publication. Run the copy's runtime_interaction01/test_source_patch.py
with Python -I -B to reproduce the twelve source/patch checks without the authoring
workspace. Native tests are not run by either script.

Original frozen authoring source/evidence manifests are preserved unchanged outside
this derivative. Production/test C++ and patch bytes are preserved; path-bound
metadata, README and tools are explicitly adapted. Historical receipt hashes are
provenance, not substitutes for this new allowlist.

The actual pure headers passed 10 C++ cases / 28 checks under bounded MSVC owned
Jobs. This does not prove the uncompiled UE controller integration. No commit,
project patch application, UE launch, listener or media activation is included.
