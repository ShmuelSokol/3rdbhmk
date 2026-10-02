# Street-tree fork diagnostic 01

The accepted post-S5 Kotel close-up shows an exposed stump-like shoulder where
branches leave the trunk. This read-only diagnostic measures the current Olive
seed0 LOD0 source geometry; it changes no production mesh, map or material.

Run with Python and NumPy:

    python probe.py --output <fresh-directory>

The default project root comes from this file's repository location. A different
checkout may be passed with `--project-root`. Three exact source/OBJ hashes must
match before the generators are imported. No engine, network or asset export runs.
Existing output is refused, so reference evidence cannot be overwritten.

The generator emits40 independently capped tubes and13 forks,2936 bark triangles.
Every regenerated vertex matches the exported OBJ within5.1e-6cm; triangle
membership matches exactly after the documented Y-reflection adapter. At the
root fork2538/4096 deterministic area-uniform cap samples (61.96%) remain outside
every other closed bark shell at both0.001cm and0.01cm above the cap. Solid-angle
winding handles either orientation; an independent tetrahedron control checks
inside/outside/reversed winding. AABB tests only prune impossible intersections.

These are finite numerical samples, NOT a continuous area/visibility proof or
new rendered acceptance. They explain the exposed shelf in the existing frame;
they do not establish that a proposed replacement is manifold, properly shaded,
UV-correct or visually better. A continuous fork replacement must separately
preserve the root/crown/foliage, pass topology/envelope checks and be reviewed in
matched images before import. The accepted bark sampler repair remains intact.
