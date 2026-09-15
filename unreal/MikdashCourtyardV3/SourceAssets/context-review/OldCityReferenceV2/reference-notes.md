# Old City visual direction — user photographs, 15 September 2026

Shmuel supplied two phone photo grids and said: "This is what the old city looks like, by the way."
Private originals are preserved outside the repository at
`C:\Mikdash\PrivateReferences\OldCity-20260915\old-city-photo-grid-{1,2}.jpg`.
Keep the family photographs out of Git, game textures and public distributions.
These collages establish appearance, not surveyed dimensions or a complete street map.

## What the photographs actually show

- Connected, narrow stone lanes; walls close to the pedestrian. Alternating open sky,
  transverse arches and vaulted passages. Long sun/shade boundaries and sky light
  bouncing into shade, rather than uniform amber illumination.
- Cream, pale beige, grey and honey limestone. Individual wall blocks have varied
  course heights, chipped edges, rough faces, deep irregular joints and localized
  wear. Wall stones and walking surfaces have visibly different finishes.
- Rectangular limestone paving in rows. Some surfaces are pecked/chisel textured;
  walked areas and step noses look smoother and worn. Pavers vary in size, value and
  weathering. Avoid the current vertical-looking texture on city wall faces.
- Shallow stepped lanes with broad landings and narrow central ramps; handrails
  follow the slope. Ramps/steps are physical geometry and must be walk-tested.
- Circular utility covers, square frames and paving cut around them; occasional
  linear drainage. These are modern Old City details, not a claim about Temple floors.
- Recessed arched doors, shutters, metal gates, iron grilles, modest wall lamps,
  surface pipes/cables and air-conditioning units. Openings need real depth close up.
- Small groups moving through lanes, with space to pass; some individuals. The
  reference is for spacing, scale and activity, not recreating identifiable people.
- Sparse greenery around buildings and beyond the Mount. These photos do not change
  the user's separate instruction to keep trees off the Temple Mount itself.

## Implementation and acceptance order

1. Fix missing/incorrect ground and unsupported buildings before surface decoration.
   cp24 K2 has an apparent opening/mirrored band beneath the Jewish Quarter; its
   physical cause remains unverified. Do not hide it with a material-only patch.
2. Select one actual source street segment and build a cohesive walking view with
   connected facades, arches, landings, steps and ramp. Preserve source road alignment;
   author missing detail explicitly, without claiming measurements from the collage.
3. Apply different wall and floor treatments: correct world scale/course orientation,
   varied blocks, wear and roughness. A procedural window drawn onto a floating box
   is not sufficient acceptance.
4. Add a restrained set of utility details and street lighting, followed by grouped
   pedestrians. Keep collision clear at ramps, thresholds and handrails.
5. Compare a walking-height packaged screenshot against this brief in daylight and
   arch shade. Confirm ground continuity and all three precinct visibility states.

Status: reference captured and direction recorded. No new geometry, materials or
map application from these photographs is claimed by this note.

## Source finding while native saves are memory-blocked

`Scripts/release_context_materials.py` maps X-facing walls with `uvX = p.zy`,
while Y-facing walls use `uvY = p.xz`. The X projection therefore puts world height
in texture U; the Y projection puts height in V. This is a concrete candidate for
the inconsistent/vertical stone coursing visible in cp24. The same X projection
is used by its normal-map sampling and reorientation. CityFacade imports these
HLSL blocks; the older facade shells use the context material directly.

Before changing saved assets, inspect the source diffuse texture's course direction,
then test X- and Y-facing wall samples at the same scale. Any correction must update
albedo, roughness, normal sampling AND the normal's world-space reorientation together.
Roof/floor XY mapping should retain its existing orientation. This is a source
diagnosis, not a rendered fix or permission to bypass checkpoint/readback checks.
