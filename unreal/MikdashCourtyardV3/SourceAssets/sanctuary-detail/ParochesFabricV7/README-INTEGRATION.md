# V7 fabric integration

Use `release_paroches_fabric.run(apply=True)` in root's serial native slot. The new namespace is `/Game/MikdashV3/MaterialReview/ParochesFabricV7`; an existing namespace refuses. The only source is `third-temple-aron-wings-v7.png`, verified against this folder's frozen source receipt with READY_FOR_NATIVE_REVIEW required immediately before mutation.

V7 is the user's selected artistic synthesis: two keruvim with Aron-like wings, palms, and two faces sharing a head. Tiny requested flecks are baked into this image. There is no separate mask, ServiceAmount or extra tint, and no V1 asset is imported or overwritten. This is not asserted as exact Yechezkel imagery.

One sRGB/clamped texture connects directly to BaseColor. Whole-panel World→Local mapping remains `((X+180)/360,1-Z/306)`; roughness0.9, metallic0, two-sided and saved Nanite usage are retained. This avoids strip UV repetition and remains local under future actor scaling. Only the two exact ClothV1/HemV1 mesh components receive material overrides; geometry and source mesh materials stay unchanged.

Existing guards remain: current project/main, no PIE/dirty world, external actor/object refusal, exact two-target inventory, checkpoint/main SHA, source asset and three protected-map hashes, unrelated scene equality, cached actor identities, saved graph/link/texture/output readback and map reopen. Frozen sources and integration state are rechecked before mutation. Native material compilation and visual acceptance require root's run; no native job was run by the worker.
