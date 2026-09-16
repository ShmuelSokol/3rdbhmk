"""StreetTreesV1 - real trees for modern Jerusalem, generated offline.

WHY THIS EXISTS. Checkpoint cp26 ships two families of vegetation. `JudeanFloraV1`
(Scripts/create_vegetation.py) is the good one: leaf-spray cards, LOD ladders, authored
materials, 225,780 instances on the hillsides. The other family is the one the reviewer
actually sees in the hero frames - 4,409 `SM_JerusalemInstance_Tree_trunks` and 13,227
`SM_JerusalemInstance_Tree_crowns`, illustrative OSM-derived placeholders imported with the
city. The trunk prototype is 20 triangles, the crown prototype is 80, and three crowns are
parented to each trunk. That is literally a cylinder with two or three low-poly spheres on
it, and it is what `cp26-A1-west-gate-approach-into-old-city.png` puts in the hero
foreground and what `cp26-07-north-gate-approach-plaza-stone-near.png` drives through the
north-gate stair. CP26-REVIEW.md D4.

THIS SCRIPT DOES NOT TOUCH `JudeanFloraV1`. It is a NEW namespace - AGENTS.md hard rule 4 -
producing `StreetTreesV1`: the trees that belong in the MODERN city around the Old City
walls, where the OSM placeholders currently stand.

WHAT IT BUILDS, and the standard it is trying to meet ("Warner Brothers style production",
and no repeating patterns):

  * A recursive branch grower. The trunk tapers, leans and FORKS, and each fork forks again,
    to a species-dependent order. Child radii follow the da Vinci / Murray rule
    (sum of child area = parent area) rather than a fixed fraction, so the taper is
    structurally right and a limb never grows thicker than what carries it. Apical dominance
    is a per-species number, which is the single parameter that separates a cypress (one
    strong leader, short branches hugging the axis) from an olive (no leader at all, a low
    fork into equals).
  * Leaf clusters anchored to BRANCH TIPS, not scattered through a crown envelope. This is
    the thing that makes a tree read as a tree instead of as a cloud on a stick: foliage in
    the real world hangs off the ends of the twigs that carry it.
  * Several independent SEEDS per species - four for the species that appear in groups - so
    no two neighbouring trees share a silhouette, plus per-instance yaw and scale applied at
    placement time.
  * A three-step LOD ladder and a billboard impostor that is an orthographic render of the
    species' own LOD1 mesh.

BUDGET. PERFORMANCE-BUDGET.md gives foliage a 3.5 M triangle per-frame ceiling on the RTX
2070, and `budget()` below re-derives the load with the same arithmetic
create_vegetation.py uses (`expected_triangles_per_frame`, VISIBLE_FRACTION, CLUMPING_SAFETY)
so the number is comparable rather than merely reassuring. For scale: the blob family being
replaced is 4,409*20 + 13,227*80 = 1,146,340 triangles with NO LOD ladder and NO cull, all
of it resident at every distance.

REUSE, DELIBERATELY. Everything that create_vegetation.py already paid for is imported from
it rather than rewritten: the Part/winding checks, `tapered_tube`, the back-to-back `card`,
the OBJ adapter and its readback, the leaf-mask rasteriser, the atlas and bark writers, and
the billboard renderer. The module's output paths are re-pointed at this family's own folder
at import time (see `_retarget`), which is what keeps a StreetTreesV1 run from writing a
single byte into JudeanFloraV1. Those are process-local rebindings; nothing on disk changes.

Runs on the 64-bit interpreter (`C:\\Users\\shmue\\anaconda3\\python.exe`, 3.8.8). The 32-bit
one on PATH runs out of memory on the plaza-scale work and is not supported here. No PIL, no
numpy, no network, no asset store: stdlib only, like every other create_* script here.

OFFLINE ONLY. This script never opens an engine, never touches a .umap and never writes into
Content/. Placement and import are release_street_trees.py's job.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FAMILY = 'StreetTreesV1'
OUT = ROOT / 'SourceAssets' / 'vegetation-review' / FAMILY
OBJ_DIR = OUT / 'obj'
TEX_DIR = OUT / 'textures'
PREVIEW_DIR = OUT / 'previews'
MANIFEST_PATH = OUT / 'street-trees-manifest.json'
MESH_PREFIX = 'SM_%s_' % FAMILY
DEST = '/Game/MikdashV3/Vegetation/%s' % FAMILY

SEED = 20260915


# =====================================================================================
# 1. THE GENERATOR THIS ONE STANDS ON
# =====================================================================================
def _load_create_vegetation():
    """Import Scripts/create_vegetation.py as a module without needing it on sys.path."""
    path = Path(__file__).resolve().parent / 'create_vegetation.py'
    spec = importlib.util.spec_from_file_location('mikdash_create_vegetation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cv = _load_create_vegetation()


def _retarget():
    """Point every create_vegetation writer at THIS family's folders.

    create_vegetation's texture and OBJ writers resolve `TEX_DIR` / `OBJ_DIR` as module
    globals at call time, so rebinding them here redirects the writes. Without this, the
    first `write_leaf_atlas` call would drop a PNG into JudeanFloraV1/textures and quietly
    corrupt a shipped family's manifest hashes. This is the whole reason the rebinding is a
    named function with a comment rather than three loose assignments.
    """
    cv.OUT = OUT
    cv.OBJ_DIR = OBJ_DIR
    cv.TEX_DIR = TEX_DIR
    cv.MANIFEST_PATH = MANIFEST_PATH
    cv.PLAN_PATH = OUT / 'placement-plan.json'


_retarget()

# Short aliases for the imported machinery, so the builders below read like geometry.
Part = cv.Part
tapered_tube = cv.tapered_tube
card = cv.card
norm = cv.norm
cross = cv.cross
dot = cv.dot
basis_from = cv.basis_from
clamp = cv.clamp
mid = cv.mid
hash_int = cv.hash_int
hash_unit = cv.hash_unit
hash_range = cv.hash_range
sha256_of = cv.sha256_of
MASK32 = cv.MASK32


# =====================================================================================
# 2. ONE LEAF SHAPE THE HILLSIDE FLORA NEVER NEEDED
# =====================================================================================
# Cercis siliquassium's leaf is cordate - a broad heart with a notched base - and it is the
# most recognisable thing about the tree out of blossom. create_vegetation.leaf_alpha has no
# such shape, so it is added here by wrapping rather than by editing that file: this family
# must not be able to change a silhouette in the shipped one.
_CV_LEAF_ALPHA = cv.leaf_alpha


def leaf_alpha(shape, u, v):
    if shape != 'cordate':
        return _CV_LEAF_ALPHA(shape, u, v)
    x = (u - 0.5) * 2.0
    y = (v - 0.5) * 2.0
    # A near-circular blade, widest low, with a notch cut out of the base at the petiole and
    # a drawn-out tip. y = -1 is the petiole end.
    if (x * x) / 0.80 ** 2 + ((y + 0.06) ** 2) / 0.86 ** 2 >= 1.0:
        return 0.0
    if y < -0.30 and abs(x) < 0.34 * (1.0 - (y + 1.0) / 0.70):
        return 0.0                                   # the basal sinus
    if y > 0.52 and abs(x) > 0.40 * (1.0 - (y - 0.52) / 0.48):
        return 0.0                                   # the acuminate tip
    return 1.0


cv.leaf_alpha = leaf_alpha
cv._SHAPE_FILL_CACHE = {}                            # the wrapper invalidates the old fills
cv.CELL_COVERAGE['cordate'] = 0.38


# =====================================================================================
# 3. SPECIES - what actually grows in this part of Jerusalem
# =====================================================================================
# Sources are the same two the hillside flora cites, plus the municipal planting that any
# photograph of the streets around the walls shows. `zones` is the placement weighting and is
# consumed by release_street_trees.py; it is recorded here so the botanical decision and the
# placement decision live in one reviewable table.
#
# WHAT IS DELIBERATELY ABSENT: nothing is planted on the Temple Mount itself. That is the
# user's standing instruction and it is also Devarim 16:21; the placement keep-out enforces
# it, and no species here is zoned for the precinct.
FP = 'Zohary, M., Plants of the Bible (Cambridge University Press, 1982), species entry'
FLP = 'Zohary & Feinbrun-Dothan, Flora Palaestina vols I-IV (Israel Academy of Sciences, 1966-1986)'
MUNI = ('Municipal and institutional street planting visible throughout the modern city '
        'around the Old City walls. Appearance reference only; see '
        'SourceAssets/context-review/OldCityReferenceV2/reference-notes.md. The private '
        'photographs behind that note are NOT used as textures and are not in this repository.')

SPECIES = [
    dict(
        key='Olive', label='olive', binomial='Olea europaea', form='tree',
        heightM=[4.5, 9.0], crownM=[4.0, 7.5], trunkDiameterM=[0.30, 0.85],
        sizeSource=FP + ' Olea europaea; street and garden specimens run 4.5-9 m',
        growsThere=('The signature tree of the hillsides and of every garden, courtyard and '
                    'roadside verge around the walls. Old specimens are transplanted into new '
                    'civic planting, which is why an olive by a modern kerb still reads as ancient.'),
        leafShape='lanceolate', leafLengthCm=6.0,
        leafColour=(96, 112, 74), leafBackColour=(152, 160, 134), barkColour=(128, 120, 102),
        evergreen=True, cardSpanCm=42.0, leafAreaIndex=2.3,
        # habit: no leader at all, a low fork into near-equals, heavy sinuous bole
        seeds=4, boleFraction=0.26, orders=3, forks=3, forkAngleDeg=44.0, forkJitterDeg=15.0,
        leaderBias=0.06, lengthRatio=0.70, curveUp=0.26, trunkLean=0.16, taper=0.40,
        flute=0.20, twist=0.16, trunkNodes=6, crownLift=0.10,
        # Mostly wood: an olive's outline IS its limbs, so the envelope only tidies the edge.
        envelopeBlend=0.28,
        scaleRange=[0.74, 1.26], tiltDegrees=6.0,
        zones=dict(old_city_lane=0.34, wall_perimeter=0.30, valley_floor=0.20,
                   hill_slope=0.22, plaza_approach=0.26, cemetery=0.06),
    ),
    dict(
        key='Cypress', label='Italian cypress', binomial='Cupressus sempervirens', form='tree',
        heightM=[10.0, 19.0], crownM=[1.8, 3.8], trunkDiameterM=[0.22, 0.50],
        sizeSource=FP + ' Cupressus sempervirens; the columnar form is 1.8-3.8 m across at 10-19 m',
        growsThere=('The dark vertical punctuation of every Jerusalem skyline - churches, '
                    'monastery walls, cemeteries and the Mount of Olives. A row of them against '
                    'limestone is the most recognisable planting in the city.'),
        leafShape='scale', leafLengthCm=3.0,
        leafColour=(52, 78, 58), leafBackColour=(70, 92, 72), barkColour=(120, 100, 84),
        evergreen=True, cardSpanCm=30.0, leafAreaIndex=3.4,
        # habit: one dominant leader, very short branches held close to the axis
        seeds=4, boleFraction=0.09, orders=3, forks=3, forkAngleDeg=17.0, forkJitterDeg=6.0,
        leaderBias=0.80, lengthRatio=0.52, curveUp=0.62, trunkLean=0.03, taper=0.62,
        flute=0.05, twist=0.03, trunkNodes=7, crownLift=0.02, columnar=True,
        # Almost pure envelope: a cypress's outline is the column, not any branch inside it.
        envelopeBlend=0.88,
        scaleRange=[0.80, 1.24], tiltDegrees=2.5,
        zones=dict(old_city_lane=0.10, wall_perimeter=0.30, valley_floor=0.10,
                   hill_slope=0.26, plaza_approach=0.30, cemetery=0.52),
    ),
    dict(
        key='AleppoPine', label='Aleppo pine', binomial='Pinus halepensis', form='tree',
        heightM=[9.0, 17.0], crownM=[9.0, 14.0], trunkDiameterM=[0.30, 0.65],
        sizeSource=FLP + ' Pinus halepensis; 9-17 m in the Judean hills',
        growsThere=('The conifer of a century of afforestation around the city, and what a '
                    'modern eye reads as "the hills of Jerusalem". Bare lower trunk, then a '
                    'broad flat parasol of a crown - the opposite silhouette to the cypress '
                    'it usually stands beside.'),
        leafShape='needle', leafLengthCm=9.0,
        leafColour=(74, 100, 68), leafBackColour=(98, 120, 88), barkColour=(124, 96, 76),
        evergreen=True, cardSpanCm=55.0, leafAreaIndex=2.6,
        # habit: weak leader high up, limbs sweep out and then FLATTEN into a parasol
        seeds=4, boleFraction=0.52, orders=3, forks=3, forkAngleDeg=56.0, forkJitterDeg=18.0,
        # curveUp POSITIVE: the limbs leave the trunk and turn back UP, then the plate rule
        # spreads their foliage flat. The old -0.30 bent every branch downward, which is a
        # weeping habit, not a pine, and it was half of why the crown came out round.
        leaderBias=0.14, lengthRatio=0.70, curveUp=0.34, trunkLean=0.09, taper=0.46,
        flute=0.08, twist=0.05, trunkNodes=6, crownLift=0.38, umbrella=True,
        # Mostly envelope: the parasol IS the shape of this tree, and nothing may hang low
        # enough to fill in the long bare bole underneath it.
        envelopeBlend=0.70,
        # The parasol as a layer of flattened plates high on the trunk. 0.22 was a lamina two
        # metres thick on a thirteen-metre tree and read as a cut disc; 0.46 keeps the plates
        # overlapping at slightly different heights, which is what a real crown does.
        plateFlatten=0.46, platePlaneFraction=0.76,
        scaleRange=[0.78, 1.28], tiltDegrees=4.0,
        zones=dict(old_city_lane=0.04, wall_perimeter=0.26, valley_floor=0.12,
                   hill_slope=0.44, plaza_approach=0.14, cemetery=0.16),
    ),
    dict(
        key='Carob', label='carob', binomial='Ceratonia siliqua', form='tree',
        heightM=[5.5, 10.0], crownM=[6.0, 10.0], trunkDiameterM=[0.32, 0.80],
        sizeSource=FP + ' Ceratonia siliqua; a dense evergreen of 5.5-10 m with a broad crown',
        growsThere=('Warm rocky slopes and the Kidron side, and a common shade tree on the '
                    'approaches. Very short thick bole, heavy low forks, and a dark rounded '
                    'mass much denser than an olive of the same size.'),
        leafShape='pinnate', leafLengthCm=14.0,
        leafColour=(64, 94, 54), leafBackColour=(100, 122, 84), barkColour=(114, 102, 88),
        evergreen=True, cardSpanCm=46.0, leafAreaIndex=3.6,
        seeds=4, boleFraction=0.20, orders=3, forks=3, forkAngleDeg=40.0, forkJitterDeg=13.0,
        leaderBias=0.12, lengthRatio=0.68, curveUp=0.20, trunkLean=0.10, taper=0.44,
        flute=0.14, twist=0.09, trunkNodes=5, crownLift=0.08,
        # A carob's crown is denser and rounder than an olive's, so it leans on the envelope.
        envelopeBlend=0.36,
        scaleRange=[0.76, 1.26], tiltDegrees=5.0,
        zones=dict(old_city_lane=0.12, wall_perimeter=0.20, valley_floor=0.30,
                   hill_slope=0.26, plaza_approach=0.16, cemetery=0.08),
    ),
    dict(
        key='JudasTree', label='Judas tree', binomial='Cercis siliquastrum', form='tree',
        heightM=[3.5, 7.5], crownM=[3.0, 6.5], trunkDiameterM=[0.12, 0.35],
        sizeSource=FLP + ' Cercis siliquastrum; a small tree of 3.5-7.5 m, often multi-stemmed',
        growsThere=('Wild on the rocky slopes and planted everywhere in the city; the pink '
                    'flush on the hillsides in spring. Small, vase-shaped, usually several '
                    'stems from the base, with a broad heart-shaped leaf.'),
        leafShape='cordate', leafLengthCm=10.0,
        leafColour=(104, 134, 84), leafBackColour=(140, 162, 118), barkColour=(96, 88, 84),
        evergreen=False, cardSpanCm=46.0, leafAreaIndex=2.1,
        # habit: multi-stemmed from the base, vase-shaped, wide divergence, no leader
        seeds=3, boleFraction=0.13, orders=3, forks=3, forkAngleDeg=48.0, forkJitterDeg=18.0,
        leaderBias=0.04, lengthRatio=0.72, curveUp=0.40, trunkLean=0.12, taper=0.38,
        flute=0.10, twist=0.08, trunkNodes=4, crownLift=0.06, multiStem=3,
        envelopeBlend=0.30,
        scaleRange=[0.74, 1.30], tiltDegrees=7.0,
        zones=dict(old_city_lane=0.30, wall_perimeter=0.24, valley_floor=0.14,
                   hill_slope=0.14, plaza_approach=0.22, cemetery=0.06),
    ),
    dict(
        key='DatePalm', label='date palm', binomial='Phoenix dactylifera', form='palm',
        heightM=[9.0, 16.0], crownM=[5.5, 8.5], trunkDiameterM=[0.35, 0.50],
        sizeSource=FP + ' Phoenix dactylifera; 9-16 m with a 5.5-8.5 m crown of pinnate fronds',
        growsThere=('Not a hilltop tree: it needs groundwater and heat, so naturally it belongs '
                    'on the valley floors. As ORNAMENTAL civic planting, however, it is exactly '
                    'what modern Jerusalem puts along a boulevard and around an open plaza, and '
                    'that is the only role it has here. It is never scattered on a ridge.'),
        leafShape='pinnate', leafLengthCm=300.0,
        leafColour=(108, 132, 72), leafBackColour=(138, 154, 104), barkColour=(134, 116, 90),
        evergreen=True, cardSpanCm=330.0, leafAreaIndex=1.7,
        seeds=3, scaleRange=[0.84, 1.18], tiltDegrees=3.5,
        zones=dict(old_city_lane=0.0, wall_perimeter=0.10, valley_floor=0.34,
                   hill_slope=0.0, plaza_approach=0.22, cemetery=0.0),
    ),
]
SPECIES_BY_KEY = dict((s['key'], s) for s in SPECIES)

# The zones the placement plan draws from. Weights above are per species WITHIN a zone and are
# normalised at placement time, so adding a species cannot silently rescale another's share.
ZONES = ['old_city_lane', 'wall_perimeter', 'valley_floor', 'hill_slope',
         'plaza_approach', 'cemetery']

# LOD ladder. Same shape and the same distances as the hillside flora, so the two families
# cross over at the same ranges and a street tree never pops against a hillside one.
LOD_DISTANCES = {'tree': [0.0, 4000.0, 12000.0, 30000.0],
                 'palm': [0.0, 4000.0, 12000.0, 30000.0]}
CULL_DISTANCE_CM = {'tree': 60000.0, 'palm': 60000.0}

# Per-LOD detail. `sides` is the tube cross-section, `orders` trims the recursion, and
# `cardMultiple` widens the leaf card so the SAME leaf area is carried by a quarter as many
# cards at each step - create_vegetation's rule, and the reason a tree does not thin into a
# diagram as it recedes.
TREE_LOD = [dict(sides=12, orders=0, cardMultiple=1, maxCards=1100),
            dict(sides=6, orders=-1, cardMultiple=2, maxCards=280),
            dict(sides=4, orders=-2, cardMultiple=4, maxCards=70)]


# =====================================================================================
# 4. THE BRANCH GROWER
# =====================================================================================
def rotate_toward(axis, azimuth, angle):
    """Tilt a unit axis by `angle` toward the perpendicular direction at `azimuth`."""
    u, v, _ = basis_from(axis)
    perp = norm(tuple(u[i] * math.cos(azimuth) + v[i] * math.sin(azimuth) for i in range(3)))
    return norm(tuple(axis[i] * math.cos(angle) + perp[i] * math.sin(angle) for i in range(3)))


def child_radius(parent_radius, count, leader_bias, is_leader):
    """Da Vinci / Murray: the cross-sections of the children sum to the parent's.

    r_parent^2 = sum r_child^2. With `count` equal children each is r/sqrt(count); apical
    dominance then moves area into the leader and takes it out of the siblings, which is what
    makes a cypress a single shaft with twigs and an olive a fork into equals. Solving keeps
    the sum exact, so a limb can never come out thicker than the wood that carries it - the
    structural error that makes procedural trees read as toys.
    """
    if count <= 1:
        return parent_radius * 0.92
    share = 1.0 / count
    if is_leader:
        share = share + leader_bias * (1.0 - share)
    else:
        share = share * (1.0 - leader_bias)
    return parent_radius * math.sqrt(max(1e-6, share))


def grow(bark, tips, base, axis, length, radius, order, species, sides, max_order, seed, lane,
         emit=True):
    """Grow one branch, then recurse into its forks. Appends (point, axis, radius) per tip.

    With `emit` False no geometry is written and only the tip list is produced. Every position
    in here is LINEAR in the starting `length` and no direction depends on it, so a dry run at
    length 1.0 measures the skeleton's reach per unit length exactly - which is what
    build_street_tree uses to make the tree come out at its species height. See the note there.

    The spine is CURVED, not straight: `curveUp` bends a branch toward the vertical as it
    extends (an olive limb reaching for light) or away from it when negative (an Aleppo pine
    limb flattening into its parasol). A straight segment between two forks is the single
    clearest tell of a procedural tree, so there is no straight segment anywhere in here.
    """
    nodes = species.get('trunkNodes', 5) if order == 0 else 3
    spine = [base]
    # ROOT FLARE. A bole swells where it meets the ground and the swell dies away within about
    # a diameter. Without it the trunk is a straight-sided cylinder that reads as a fence post
    # driven into the soil - and because the flute and twist are strongest on that same
    # straight section, the first Olive row rendered an identical dark hard-edged "boot" at the
    # foot of every tree, which is a repeating pattern in the one place the eye always lands.
    radii = [radius * (1.55 if order == 0 else 1.0)]
    point = base
    direction = axis
    curve = species.get('curveUp', 0.2)
    for i in range(1, nodes + 1):
        t = i / float(nodes)
        # bend toward (or away from) vertical, plus a small deterministic wander
        target = (0.0, 0.0, 1.0)
        bend = curve / float(nodes)
        wander = 0.16 / float(nodes)
        wa = hash_range(seed, lane * 97 + i, 11, -math.pi, math.pi)
        direction = norm((direction[0] + bend * (target[0] - direction[0]) + wander * math.cos(wa),
                          direction[1] + bend * (target[1] - direction[1]) + wander * math.sin(wa),
                          direction[2] + bend * (target[2] - direction[2])))
        step = length / float(nodes)
        point = (point[0] + direction[0] * step,
                 point[1] + direction[1] * step,
                 point[2] + direction[2] * step)
        spine.append(point)
        node_radius = radius * (1.0 - species.get('taper', 0.42) * t)
        if order == 0:
            node_radius *= 1.0 + 0.55 * (1.0 - t) ** 3.0
        radii.append(node_radius)
    if emit:
        # Flute and twist at HALF the species figure. At full strength the scalloped
        # cross-section shades as one flat dark facet down the whole bole instead of reading as
        # bark, and it is the bark texture's job to carry fissures at this range anyway.
        tapered_tube(bark, spine, radii, sides,
                     twist=(0.5 * species.get('twist', 0.05) if order == 0 else 0.0),
                     flute=(0.5 * species.get('flute', 0.08) if order == 0 else 0.0))

    # Foliage anchors ALONG the branch, not only at its tip. A cypress carries its foliage down
    # the whole length of a few long branches, so if tips are the only anchors a two-order
    # cypress has about six of them and renders as six dark balls threaded on a bare pole -
    # exactly what the first Cypress sheet showed. Sampling the spine also fills the bald
    # interior a purely tip-anchored broadleaf crown leaves behind.
    if order >= 1:
        for i in (1, 2):
            node = max(1, int((i / 3.0) * (len(spine) - 1)))
            tips.append((spine[node], direction, radii[node], order))

    if order >= max_order:
        tips.append((spine[-1], direction, radii[-1], order))
        return
    # A branch carries foliage at its own tip as well as at its children's, otherwise the
    # canopy is a hollow shell with a bald interior.
    if order >= 1:
        tips.append((spine[-1], direction, radii[-1], order))

    count = int(species.get('forks', 3))
    if order == 0 and species.get('multiStem'):
        count = int(species['multiStem'])
    leader_bias = float(species.get('leaderBias', 0.15))
    fork_angle = math.radians(float(species.get('forkAngleDeg', 40.0)))
    jitter = math.radians(float(species.get('forkJitterDeg', 12.0)))
    base_azimuth = hash_range(seed, lane, 21, 0.0, 2.0 * math.pi)
    for k in range(count):
        is_leader = (k == 0 and leader_bias > 0.02)
        azimuth = base_azimuth + 2.0 * math.pi * k / float(count) \
            + hash_range(seed, lane * 31 + k, 22, -0.45, 0.45)
        angle = fork_angle + hash_range(seed, lane * 31 + k, 23, -jitter, jitter)
        if is_leader:
            angle *= 0.28                     # the leader carries on nearly straight
        new_axis = rotate_toward(direction, azimuth, angle)
        new_radius = child_radius(radii[-1], count, leader_bias, is_leader)
        ratio = float(species.get('lengthRatio', 0.70))
        if is_leader:
            ratio = ratio + leader_bias * (1.0 - ratio)
        new_length = length * ratio * hash_range(seed, lane * 31 + k, 24, 0.86, 1.14)
        grow(bark, tips, spine[-1], new_axis, new_length, new_radius,
             order + 1, species, max(4, sides - 1), max_order, seed, lane * 31 + k + 1,
             emit=emit)


def spray(part, centre, span, seed, index, uv_rect, cards=3, tilt=0.35, flatten=1.0):
    """A leaf spray as several cards that are OFFSET and RESIZED, not stacked on one point.

    create_vegetation's `cross_cluster` puts every card of a cluster through one centre. That
    is right for a hillside read at 25 m and wrong for a street tree read at 4 m: a few hundred
    co-located crosses render as a heap of separate broccoli florets with sky between them,
    which is exactly what the first Olive sheet showed. Scattering each card inside a cell
    about the cluster centre, and varying its size, lets neighbouring clusters interpenetrate
    and close into one canopy.
    """
    for k in range(cards):
        lane = index * 7 + k
        angle = 2.0 * math.pi * hash_unit(seed, lane, 51) + math.pi * k / max(1, cards)
        size = span * hash_range(seed, lane, 52, 0.74, 1.22)
        drift = 0.46 * span
        # `flatten` < 1 turns a spherical spray into a PLATE: the vertical scatter is squashed
        # and the card itself is laid toward horizontal instead of standing upright. A pine's
        # foliage is carried in flat plates on the tops of its limbs, and a spray that drifts
        # equally in all three axes with upright cards can only ever make a ball - which is why
        # the Aleppo pine kept reading as a rounded broadleaf.
        point = (centre[0] + hash_range(seed, lane, 53, -drift, drift),
                 centre[1] + hash_range(seed, lane, 54, -drift, drift),
                 centre[2] + hash_range(seed, lane, 55, -drift, drift) * flatten)
        lean = tilt * (hash_unit(seed, lane, 56) - 0.5)
        axis_u = (math.cos(angle), math.sin(angle), 0.0)
        axis_v = norm((lean * math.cos(angle + 1.57), lean * math.sin(angle + 1.57),
                       max(0.12, flatten)))
        card(part, point, axis_u, axis_v, 0.5 * size, 0.5 * size, uv_rect)


def habit_for_seed(species, seed):
    """Per-seed habit jitter: the seeds must differ in PROPORTION, not only in detail.

    Four trees grown from one set of proportions read as one tree rotated four ways, however
    different their twigs are - which is the "repeating patterns all over" the brief refuses.
    Bole length, fork angle, how fast length falls away and how far the trunk leans are all
    drawn per seed, so the variants differ in the things the eye actually reads at a distance.
    """
    habit = dict(species)
    habit['boleFraction'] = float(species.get('boleFraction', 0.28)) \
        * hash_range(seed, 2, 61, 0.72, 1.32)
    habit['forkAngleDeg'] = float(species.get('forkAngleDeg', 40.0)) \
        * hash_range(seed, 3, 62, 0.82, 1.20)
    habit['lengthRatio'] = clamp(float(species.get('lengthRatio', 0.70))
                                 * hash_range(seed, 4, 63, 0.93, 1.09), 0.45, 0.88)
    habit['trunkLean'] = float(species.get('trunkLean', 0.10)) \
        * hash_range(seed, 5, 64, 0.50, 1.60)
    return habit


def build_street_tree(species, level, seed):
    """One tree: forked bark geometry, and leaf sprays hung on the branch tips."""
    setup = TREE_LOD[level]
    species = habit_for_seed(species, seed)
    height = mid(species['heightM']) * 100.0
    crown = mid(species['crownM']) * 100.0
    trunk_radius = mid(species['trunkDiameterM']) * 50.0
    bark = Part('%s_L%d_Bark' % (species['key'], level), 'solid', 'bark')
    leaf = Part('%s_L%d_Leaf' % (species['key'], level), 'card', 'leaf')

    max_order = max(0, int(species.get('orders', 3)) + setup['orders'])
    lean = math.radians(float(species.get('trunkLean', 0.10)) * 45.0)
    lean_azimuth = hash_range(seed, 1, 31, 0.0, 2.0 * math.pi)
    axis = rotate_toward((0.0, 0.0, 1.0), lean_azimuth, lean)
    span = species['cardSpanCm'] * setup['cardMultiple']

    # --- CALIBRATION, and it is the whole reason this tree has the proportions of a tree.
    #
    # A branch chain of n orders whose length falls by `lengthRatio` each time reaches only
    # L*(1 + q + q^2 + ...) - so setting the trunk to a fraction of the species height leaves
    # the finished tree far SHORTER than that height, while the trunk radius (which is set from
    # trunkDiameterM and does not depend on length) stays put. The first version did exactly
    # that: a 675 cm olive came out 432 cm tall on a 57 cm bole, a height-to-diameter of 7.5:1
    # where the species asks for 11.7:1, and it rendered as an elephant-foot baobab.
    #
    # Every position in `grow` is LINEAR in the starting length and no direction depends on it,
    # so ONE dry run at length 1.0 measures the skeleton's reach per unit exactly, and the
    # trunk length that lands the crown on the species height follows by division. No search,
    # no magic constant, and it stays correct when a species' habit numbers change.
    probe = []
    grow(None, probe, (0.0, 0.0, 0.0), axis, 1.0, trunk_radius, 0, species,
         setup['sides'], max_order, seed, 1, emit=False)
    reach_z = max([p[0][2] for p in probe] + [1e-6])
    reach_xy = max([math.hypot(p[0][0], p[0][1]) for p in probe] + [1e-6])
    bole = max(1.0, height - 0.55 * span) / reach_z
    top_estimate = max(1.0, bole * reach_z)
    half_crown = 0.5 * crown
    del reach_xy

    tips = []
    grow(bark, tips, (0.0, 0.0, 0.0), axis, bole, trunk_radius, 0, species,
         setup['sides'], max_order, seed, 1)
    if not tips:
        tips = [((0.0, 0.0, bole), (0.0, 0.0, 1.0), trunk_radius, 0)]

    # --- canopy. Cards are leaf-SPRAY sized (create_vegetation's rule) and the count comes
    # from the species' leaf area index, not from a fixed number. Every cluster is anchored to
    # a real branch tip, so the foliage sits where the wood put it.
    wanted = cv.cards_for_crown(species, crown, span, 'tree', min(level, 2))
    wanted = int(min(wanted, setup['maxCards']))
    per_cluster = 3 if level == 0 else (2 if level == 1 else 1)
    clusters = max(1, int(math.ceil(wanted / float(per_cluster))))

    # Outer tips carry more foliage than inner ones, but only MODERATELY so. Weighting the
    # draw hard toward the outermost order drives every spray to the ends of the longest
    # branches, which lifts the crown base to half the tree's height and flattens its top - an
    # olive read as a young plane tree in the first row shot. A gentler weight lets the inner,
    # lower forks carry foliage too, which is what brings an olive's crown down around its own
    # fork and rounds it.
    weights = []
    for _point, _dir, _radius, order in tips:
        weights.append(1.0 + 0.9 * order)
    total_weight = sum(weights)
    columnar = bool(species.get('columnar'))
    umbrella = bool(species.get('umbrella'))
    plate_flatten = clamp(float(species.get('plateFlatten', 1.0)), 0.08, 1.0)
    floor_z = height * float(species.get('crownLift', 0.08))
    # EVERY TERMINAL TWIG CARRIES FOLIAGE FIRST, and only then is the remainder drawn by
    # weight. Drawing every cluster by weight leaves some outermost branches bare, and because
    # the envelope blend pulls each spray inward, a bare twig then protrudes past the canopy as
    # a thin straight whisker - plainly visible on three of the four trees in the first Aleppo
    # pine sheet. Seeding one cluster per terminal tip removes them by construction rather than
    # by hiding them behind more foliage.
    terminal = [i for i, entry in enumerate(tips) if entry[3] >= max_order]
    for c in range(clusters):
        on_terminal = c < len(terminal)
        if on_terminal:
            index = terminal[c]
        else:
            pick = hash_unit(seed, c, 41) * total_weight
            index = 0
            for index in range(len(tips)):
                pick -= weights[index]
                if pick <= 0.0:
                    break
        point, direction, radius, _order = tips[index]
        # WHERE THE SPRAY HANGS: on its own branch, blended toward the species' crown ENVELOPE.
        #
        # Canopy width has to come from the species CROWN and never from the card span. `span`
        # is a LEAF-spray size - 30 cm on a cypress against a 280 cm crown - and using it as
        # the canopy radius collapses the entire crown onto the trunk axis. That was the
        # Cypress bug, and the olive only escaped it because its branch tips happened to be
        # spread wide already.
        #
        # `envelopeBlend` decides how much each species obeys its envelope rather than its
        # wood: a cypress is almost pure envelope, because its shape is the shape of the
        # column and not of any branch inside it; a broadleaf is mostly wood, because an
        # olive's outline IS its limbs.
        t = clamp(point[2] / top_estimate, 0.0, 1.0)
        if columnar:
            profile = (1.0 - t) ** 0.42
        elif umbrella:
            # A PARASOL, not a ball. An Aleppo pine carries its foliage as a wide flat disc in
            # the top third of the tree, over a long bare bole. A profile that peaks at
            # mid-height produces a rounded mass and the pine reads as a generic broadleaf,
            # which is exactly what the first Aleppo pine sheet showed. This one peaks high and
            # falls to nothing below about half height, so the open limb structure underneath
            # stays visible - which is the other half of why the tree is recognisable.
            profile = max(0.0, 1.0 - ((t - 0.82) / 0.34) ** 2)
        else:
            profile = math.sqrt(max(0.0, 1.0 - (2.0 * t - 1.0) ** 2))
        theta = hash_range(seed, c, 43, 0.0, 2.0 * math.pi)
        radial = half_crown * profile * math.sqrt(hash_unit(seed, c, 44))
        blend = clamp(float(species.get('envelopeBlend', 0.25)), 0.0, 1.0)
        if on_terminal:
            # A spray seeded onto a terminal twig has to STAY on that twig. Blending it toward
            # the envelope like any other cluster moves it off the twig end, and the bare twig
            # protrudes past the canopy as a whisker all over again - which is exactly why
            # seeding the terminal tips did not clear the whiskers from the Aleppo pine on its
            # own. The envelope shapes the crown; it does not get to strand the wood.
            blend *= 0.22
        centre = (point[0] * (1.0 - blend) + radial * math.cos(theta) * blend,
                  point[1] * (1.0 - blend) + radial * math.sin(theta) * blend,
                  point[2] + direction[2] * span * 0.35 * hash_unit(seed, c, 45))
        if umbrella and not on_terminal:
            # Draw the crown TOWARD a horizontal plane high in the tree: a parasol is a shallow
            # layer of overlapping plates, not a dome.
            #
            # Terminal sprays are EXEMPT, and that exemption is the whole difference between a
            # pine and a mushroom. Collapsing every spray onto one plane strands each outer
            # branch and leaves a thin flat lamina floating over bare whiskers - which is
            # exactly what the first plate attempt rendered. The plate sets where the MASS of
            # the crown sits; it does not get to lift foliage off the wood that carries it.
            plane = top_estimate * float(species.get('platePlaneFraction', 0.80))
            centre = (centre[0], centre[1], plane + (centre[2] - plane) * plate_flatten)
        if centre[2] < floor_z:
            continue                        # nothing hangs below the crown base
        spray(leaf, centre, span, seed, c, cv.card_uv(min(level, 2), c),
              cards=per_cluster, tilt=0.38, flatten=plate_flatten)
    return [bark], [leaf]


def build_plant(species, level, seed):
    if species['form'] == 'palm':
        # cv.build_palm varies the FROND LAYOUT by seed but reads height and crown straight off
        # the species table, so every palm comes out at exactly the same height carrying
        # exactly the same crown - two seeds that read as one tree rotated. The broadleaves get
        # their proportions jittered in habit_for_seed; a palm has no forks to jitter, so the
        # variation has to go into its height and crown directly.
        habit = dict(species)
        height = mid(species['heightM']) * hash_range(seed, 6, 65, 0.80, 1.22)
        crown = mid(species['crownM']) * hash_range(seed, 7, 66, 0.84, 1.18)
        habit['heightM'] = [height, height]
        habit['crownM'] = [crown, crown]
        return cv.build_palm(habit, level, seed)
    return build_street_tree(species, level, seed)


def species_seed(species, variant):
    """A stable, independent seed per (species, variant). Two variants must not correlate."""
    base = sum(ord(c) for c in species['key']) * 2246822519 + (variant + 1) * 40503
    return (SEED ^ hash_int(base)) & MASK32


def variant_name(species, variant):
    return '%s%s_S%d' % (MESH_PREFIX, species['key'], variant)


# =====================================================================================
# 5. OFFLINE PREVIEW - look at the trees before an engine ever runs
# =====================================================================================
# A frame is the only acceptance that counts, but a frame costs a cook and an engine slot. An
# orthographic render of the actual OBJ geometry costs nothing and catches the failures that
# are about SHAPE - a crown that is a drum, a bole with no taper, six trees that are the same
# tree. It is the same painter's-algorithm rasteriser create_vegetation uses for its billboard
# impostors, generalised to take a camera azimuth and to draw into a shared buffer so several
# trees can be composed into one picture.
def render_into(data, depth, width, height, tree, camera):
    bark_parts, leaf_parts, species, masks, mask_cell = tree['parts']
    yaw = math.radians(tree.get('yaw', 0.0))
    scale = tree.get('scale', 1.0)
    offset = tree.get('offset', (0.0, 0.0))
    ox, oz, ppcm, azimuth = camera
    ca, sa = math.cos(azimuth), math.sin(azimuth)
    cy, sy = math.cos(yaw), math.sin(yaw)
    light = norm((-0.38, -0.60, 0.70))
    for parts, colour, masked in ((bark_parts, species['barkColour'], False),
                                  (leaf_parts, species['leafColour'], True)):
        for part in parts:
            for a, b, c in part.faces:
                pa, pb, pc = part.vertices[a], part.vertices[b], part.vertices[c]
                ua, ub, uc = part.uvs[a], part.uvs[b], part.uvs[c]
                n = cross(tuple(pb[i] - pa[i] for i in range(3)),
                          tuple(pc[i] - pa[i] for i in range(3)))
                length = math.sqrt(dot(n, n))
                if length < 1e-9:
                    continue
                shade = 0.40 + 0.60 * max(0.0, dot(n, light) / length)
                pixel = bytes([min(255, max(0, int(colour[i] * shade))) for i in range(3)] + [255])
                projected = []
                for p in (pa, pb, pc):
                    x = (p[0] * cy - p[1] * sy) * scale + offset[0]
                    y = (p[0] * sy + p[1] * cy) * scale + offset[1]
                    z = p[2] * scale
                    wx = x * ca - y * sa
                    wy = x * sa + y * ca
                    projected.append((ox + wx * ppcm, oz - z * ppcm, -wy))
                (ax, ay, ad), (bx, by, bd), (cx, cy2, cd) = projected
                det = (by - cy2) * (ax - cx) + (cx - bx) * (ay - cy2)
                if abs(det) < 1e-9:
                    continue
                ymin = max(0, int(min(ay, by, cy2)))
                ymax = min(height - 1, int(max(ay, by, cy2)) + 1)
                xmin = max(0, int(min(ax, bx, cx)))
                xmax = min(width - 1, int(max(ax, bx, cx)) + 1)
                if ymin > ymax or xmin > xmax:
                    continue
                for py in range(ymin, ymax + 1):
                    for px in range(xmin, xmax + 1):
                        w0 = ((by - cy2) * (px + 0.5 - cx) + (cx - bx) * (py + 0.5 - cy2)) / det
                        if w0 < 0.0:
                            continue
                        w1 = ((cy2 - ay) * (px + 0.5 - cx) + (ax - cx) * (py + 0.5 - cy2)) / det
                        if w1 < 0.0 or w0 + w1 > 1.0:
                            continue
                        w2 = 1.0 - w0 - w1
                        if masked:
                            u = w0 * ua[0] + w1 * ub[0] + w2 * uc[0]
                            v = w0 * ua[1] + w1 * ub[1] + w2 * uc[1]
                            if not cv.sample_leaf_mask(masks, mask_cell, u, v):
                                continue
                        z = w0 * ad + w1 * bd + w2 * cd
                        index = py * width + px
                        if z > depth[index]:
                            depth[index] = z
                            data[index * 4:index * 4 + 4] = pixel


def new_canvas(width, height, sky=(232, 234, 228)):
    data = bytearray(width * height * 4)
    row = bytes(list(sky) + [255])
    for i in range(width * height):
        data[i * 4:i * 4 + 4] = row
    return data, [-1e18] * (width * height)


def draw_groundline(data, width, height, y, colour=(198, 190, 170)):
    if 0 <= y < height:
        for px in range(width):
            index = (y * width + px) * 4
            data[index:index + 4] = bytes(list(colour) + [255])


def silhouette_sheet(species, built, masks, mask_cell):
    """One sheet per species: every seed variant side by side, at a common scale.

    Read this for SHAPE. If two tiles have the same outline the seeds are not doing their job,
    and no amount of per-instance yaw will hide it in a group.
    """
    tile_w, tile_h = 300, 430
    variants = len(built)
    width, height = tile_w * variants, tile_h
    data, depth = new_canvas(width, height)
    tallest = 0.0
    for parts in built:
        for part in parts[0] + parts[1]:
            tallest = max(tallest, part.bounds()['max'][2])
    ppcm = (tile_h - 46) / max(1.0, tallest)
    ground = tile_h - 22
    draw_groundline(data, width, height, ground)
    for index, parts in enumerate(built):
        tree = {'parts': (parts[0], parts[1], species, masks, mask_cell), 'yaw': 0.0, 'scale': 1.0}
        render_into(data, depth, width, height, tree,
                    (tile_w * index + tile_w * 0.5, ground, ppcm, 0.0))
    path = PREVIEW_DIR / ('preview-%s-silhouettes.png' % species['key'])
    cv.png_rgba(path, data, width, height)
    return path


def group_shot(entries, name, width=1760, height=640):
    """A crowd of trees from one camera. This is the picture that catches clones.

    Per-instance yaw and scale are applied here exactly as the placement plan will apply them,
    so what this shows is what the level will show.
    """
    data, depth = new_canvas(width, height)
    tallest = 0.0
    for entry in entries:
        for part in entry['parts'][0] + entry['parts'][1]:
            tallest = max(tallest, part.bounds()['max'][2])
    ppcm = (height - 90) / max(1.0, tallest * 1.25)
    ground = height - 40
    draw_groundline(data, width, height, ground)
    ordered = sorted(entries, key=lambda e: -e['offset'][1])
    for entry in ordered:
        render_into(data, depth, width, height, entry, (width * 0.5, ground, ppcm, 0.0))
    path = PREVIEW_DIR / ('preview-%s.png' % name)
    cv.png_rgba(path, data, width, height)
    return path


# =====================================================================================
# 6. BUDGET
# =====================================================================================
def budget(triangle_counts, instances_per_species):
    """Re-derive the foliage load with create_vegetation's own arithmetic.

    Same ceiling (3.5 M), same VISIBLE_FRACTION, same 3x clumping safety, so this number and
    the hillside family's number are directly comparable and can simply be added.
    """
    report = {'triangleCeilingPerFrame': cv.FOLIAGE_TRIANGLE_CEILING,
              'visibleFractionOfCullDisc': cv.VISIBLE_FRACTION,
              'clumpingSafetyFactor': cv.CLUMPING_SAFETY,
              'basis': ('PERFORMANCE-BUDGET.md: RTX 2070, 8 GB, 1080p. Foliage is budgeted at '
                        '4 ms of a 16.6 ms frame and capped at 3.5 M triangles per frame for '
                        'ALL foliage, this family and JudeanFloraV1 together.'),
              'perSpecies': [], 'estimatedTrianglesPerFrame': 0.0}
    # Street trees line streets rather than covering the region, so the density that matters is
    # instances over the area they actually occupy. The area below is the modern-city footprint
    # the OSM trees span; release_street_trees.py replaces it with the measured one.
    area = float(instances_per_species.get('_areaCm2', 3.2e10))
    total = 0.0
    for species in SPECIES:
        count = int(instances_per_species.get(species['key'], 0))
        if not count:
            continue
        form = species['form']
        ladder = []
        for level, distance in enumerate(LOD_DISTANCES[form]):
            key = '%s_L%d' % (species['key'], level)
            triangles = triangle_counts.get(key)
            if triangles is None:
                triangles = triangle_counts.get('%s_Billboard' % species['key'], 2)
            ladder.append((distance, triangles))
        value = cv.expected_triangles_per_frame(count, area, CULL_DISTANCE_CM[form], ladder,
                                                cv.VISIBLE_FRACTION) * cv.CLUMPING_SAFETY
        total += value
        report['perSpecies'].append({'species': species['key'], 'instances': count,
                                     'lodLadder': [[d, t] for d, t in ladder],
                                     'trianglesPerFrame': round(value, 1)})
    report['estimatedTrianglesPerFrame'] = round(total, 1)
    report['triangleHeadroom'] = round(cv.FOLIAGE_TRIANGLE_CEILING / max(1.0, total), 2)
    report['withinTriangleCeiling'] = total <= cv.FOLIAGE_TRIANGLE_CEILING
    report['replacedBlobTriangles'] = 4409 * 20 + 13227 * 80
    report['replacedBlobNote'] = ('The OSM placeholder family this replaces carries '
                                  '1,146,340 triangles with no LOD ladder and no cull '
                                  'distance, resident at every range.')
    return report


# =====================================================================================
# 7. EXPORT
# =====================================================================================
def export(write_previews=True):
    OBJ_DIR.mkdir(parents=True, exist_ok=True)
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    meshes, readbacks, textures, previews = [], [], [], []
    triangle_counts = {}
    group_entries = []

    for species in SPECIES:
        form = species['form']
        levels = len(LOD_DISTANCES[form]) - 1          # last rung is the billboard
        mask_cell = 256
        masks = cv.build_leaf_masks(species, mask_cell)
        leaf_path = cv.write_leaf_atlas(species, masks)
        bark_path, normal_path = cv.write_bark_textures(species)

        lod0_variants = []
        lod1_reference = None
        per_level_triangles = {}
        for variant in range(int(species.get('seeds', 3))):
            seed = species_seed(species, variant)
            for level in range(levels):
                bark_parts, leaf_parts = build_plant(species, level, seed)
                if variant == 0 and level == 0:
                    lod1_reference = (bark_parts, leaf_parts)
                if level == 0:
                    lod0_variants.append((bark_parts, leaf_parts))
                if variant == 0 and level == 1:
                    lod1_reference = (bark_parts, leaf_parts)
                total = 0
                for parts, role in ((bark_parts, 'Bark'), (leaf_parts, 'Leaf')):
                    if not parts:
                        continue
                    name = '%s_L%d_%s' % (variant_name(species, variant), level, role)
                    record = cv.write_obj(OBJ_DIR / (name + '.obj'), name, parts, [
                        '%s (%s), StreetTreesV1 seed %d, LOD%d %s'
                        % (species['label'], species['binomial'], variant, level, role.lower()),
                        'height %.1f-%.1f m, crown %.1f-%.1f m; source: %s'
                        % (species['heightM'][0], species['heightM'][1], species['crownM'][0],
                           species['crownM'][1], species['sizeSource']),
                        'branching is recursive with da Vinci child radii; leaf sprays are '
                        'anchored to branch tips. Stylised habit, not a survey of any tree.',
                    ])
                    record['species'] = species['key']
                    record['variantSeed'] = variant
                    record['lod'] = level
                    record['materialRole'] = role.lower()
                    record['lodStartDistanceCm'] = LOD_DISTANCES[form][level]
                    meshes.append(record)
                    readbacks.append(cv.readback_obj(OBJ_DIR / (name + '.obj'), record))
                    total += record['triangles']
                key = '%s_L%d' % (species['key'], level)
                per_level_triangles.setdefault(key, []).append(total)

        for key, values in per_level_triangles.items():
            triangle_counts[key] = int(round(sum(values) / float(len(values))))

        # billboard: one per species, an ortho render of its own LOD1 mesh
        part = cv.build_billboard(species)
        name = '%s%s_Billboard' % (MESH_PREFIX, species['key'])
        record = cv.write_obj(OBJ_DIR / (name + '.obj'), name, [part], [
            '%s far impostor; ONE open single-sided quad drawn by a camera-facing material. '
            'Exempt from the closed-shell and signed-volume checks by construction.'
            % species['label']])
        record['species'] = species['key']
        record['lod'] = len(LOD_DISTANCES[form]) - 1
        record['materialRole'] = 'billboard'
        record['lodStartDistanceCm'] = LOD_DISTANCES[form][-1]
        meshes.append(record)
        readbacks.append(cv.readback_obj(OBJ_DIR / (name + '.obj'), record))
        triangle_counts['%s_Billboard' % species['key']] = record['triangles']

        entry = {'species': species['key'],
                 'leafAtlas': leaf_path.name, 'leafAtlasSha256': sha256_of(leaf_path),
                 'barkBaseColour': bark_path.name, 'barkBaseColourSha256': sha256_of(bark_path),
                 'barkNormal': normal_path.name, 'barkNormalSha256': sha256_of(normal_path),
                 'leafShape': species['leafShape'],
                 'leavesPerAtlasCell': cv.leaves_per_cell(species),
                 'cardSpanCm': species['cardSpanCm'],
                 'leafLengthCm': species['leafLengthCm'],
                 'leafFractionOfCell': round(cv.leaf_cell_scale(species), 4),
                 'alphaTest': True,
                 'note': ('Procedural, standard library only: no photograph, no scan, no '
                          'third-party asset, no licence question. The private Old City '
                          'reference photographs were NOT used to make any texture here.')}
        if lod1_reference is not None:
            billboard_path, coverage = cv.render_billboard_texture(
                species, lod1_reference[0], lod1_reference[1], masks, mask_cell)
            entry['billboardTexture'] = billboard_path.name
            entry['billboardTextureSha256'] = sha256_of(billboard_path)
            entry['billboardCoverage'] = round(coverage, 4)
        textures.append(entry)

        if write_previews:
            previews.append(str(silhouette_sheet(species, lod0_variants, masks,
                                                 mask_cell).relative_to(ROOT)))
        # collect a few instances of this species for the mixed group shot
        for variant, parts in enumerate(lod0_variants):
            group_entries.append({'parts': (parts[0], parts[1], species, masks, mask_cell),
                                  'species': species['key'], 'variant': variant})

    if write_previews:
        laid_out = []
        span = 2600.0
        for index, entry in enumerate(group_entries):
            species = SPECIES_BY_KEY[entry['species']]
            lo, hi = species['scaleRange']
            item = dict(entry)
            item['yaw'] = hash_range(SEED, index, 71, 0.0, 360.0)
            item['scale'] = hash_range(SEED, index, 72, lo, hi)
            item['offset'] = (hash_range(SEED, index, 73, -span, span),
                              hash_range(SEED, index, 74, -900.0, 900.0))
            laid_out.append(item)
        previews.append(str(group_shot(laid_out, 'group-mixed').relative_to(ROOT)))
        singles = [e for e in group_entries if e['species'] == 'Olive']
        laid_out = []
        for index, entry in enumerate(singles * 3):
            item = dict(entry)
            item['yaw'] = hash_range(SEED, index, 81, 0.0, 360.0)
            item['scale'] = hash_range(SEED, index, 82, 0.74, 1.26)
            item['offset'] = (-1500.0 + index * 260.0, hash_range(SEED, index, 83, -500.0, 500.0))
            laid_out.append(item)
        previews.append(str(group_shot(laid_out, 'group-olive-row', width=1500,
                                       height=560).relative_to(ROOT)))
    return meshes, readbacks, textures, triangle_counts, previews


def write_manifest(meshes, readbacks, textures, triangle_counts, previews, budget_report):
    manifest = {
        'status': 'offline_geometry_and_textures_generated_native_pending',
        'version': 1,
        'family': FAMILY,
        'generated': datetime.now(timezone.utc).isoformat(),
        'generator': 'Scripts/create_street_trees.py',
        'generatorSha256': sha256_of(Path(__file__)),
        'reusesGenerator': 'Scripts/create_vegetation.py',
        'reusesGeneratorSha256': sha256_of(Path(__file__).resolve().parent / 'create_vegetation.py'),
        'targetAssetFolder': DEST,
        'meshPrefix': MESH_PREFIX,
        'objConvention': cv.OBJ_HEADER_NOTE.replace('JudeanFloraV1', FAMILY),
        'replaces': {
            'meshes': ['SM_JerusalemInstance_Tree_trunks', 'SM_JerusalemInstance_Tree_crowns'],
            'trunkInstances': 4409, 'crownInstances': 13227,
            'prototypeTriangles': {'trunk': 20, 'crown': 80},
            'defect': ('CP26-REVIEW.md D4: low-poly two-sphere blob trees in cp26-A1 and '
                       'cp26-07, clipping the north-gate stair.'),
        },
        'meshCount': len(meshes),
        'triangles': sum(r['triangles'] for r in meshes),
        'trianglesPerLod': triangle_counts,
        'meshes': meshes,
        'readback': readbacks,
        'textures': textures,
        'previews': previews,
        'species': [dict((k, v) for k, v in s.items()) for s in SPECIES],
        'zones': ZONES,
        'lodLadderCm': LOD_DISTANCES,
        'cullDistanceCm': CULL_DISTANCE_CM,
        'budget': budget_report,
        'materials': {
            'bark': 'opaque, one-sided, base colour + normal',
            'leaf': 'MASKED alpha test at 0.5, TWO-SIDED, MSM_TWO_SIDED_FOLIAGE',
            'billboard': 'MASKED alpha test at 0.5, two-sided, DEFAULT_LIT',
            'usageFlagsRequired': ['used_with_instanced_static_meshes', 'used_with_static_mesh'],
            'usageFlagNote': ('UE 5.8 has NO bUsedWithFoliage: foliage is drawn through '
                              'instanced static mesh components, so bUsedWithInstancedStaticMeshes '
                              'IS the foliage flag. Verified against '
                              'Engine/Source/Runtime/Engine/Public/Materials/Material.h, which '
                              'declares bUsedWithInstancedStaticMeshes, bUsedWithStaticMesh and '
                              'bUsedWithNanite and no foliage flag at all. Setting a flag that '
                              'does not exist would raise in release_vegetation_materials.py\'s '
                              'own checker, which is how this was caught.'),
        },
        'limitations': [
            'Offline geometry and textures only. No visual, collision, cook or packaged '
            'acceptance is established by this script, and a -nullrhi run cannot establish one.',
            'Species habit is a stylised procedural approximation, not a scan or a survey.',
            'Textures are procedural. The private Old City reference photographs at '
            'C:/Mikdash/PrivateReferences/OldCity-20260915 were used as visual direction only '
            'and are never committed, imported, or turned into a game texture.',
            'Placement, keep-outs and the intersection proof are release_street_trees.py.',
            'Nothing here is halachic.',
        ],
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate StreetTreesV1 offline.')
    parser.add_argument('--no-preview', action='store_true', help='skip the preview PNGs')
    parser.add_argument('--species', help='comma-separated subset, for a fast iteration')
    args = parser.parse_args(argv)

    if args.species:
        wanted = set(s.strip() for s in args.species.split(',') if s.strip())
        unknown = wanted - set(SPECIES_BY_KEY)
        if unknown:
            raise SystemExit('unknown species: %s' % sorted(unknown))
        global SPECIES
        SPECIES = [s for s in SPECIES if s['key'] in wanted]

    print('generating %s: %d species' % (FAMILY, len(SPECIES)))
    meshes, readbacks, textures, triangle_counts, previews = export(
        write_previews=not args.no_preview)
    counts = {'_areaCm2': 3.2e10}
    for species in SPECIES:
        counts[species['key']] = 700           # provisional; the plan replaces it
    budget_report = budget(triangle_counts, counts)
    manifest = write_manifest(meshes, readbacks, textures, triangle_counts, previews,
                              budget_report)
    print('  %d meshes, %d triangles -> %s'
          % (manifest['meshCount'], manifest['triangles'],
             MANIFEST_PATH.relative_to(ROOT)))
    for key in sorted(triangle_counts):
        print('    %-24s %6d tri' % (key, triangle_counts[key]))
    print('  budget: %.0f tri/frame vs %.1f M ceiling (%.1fx headroom)'
          % (budget_report['estimatedTrianglesPerFrame'],
             budget_report['triangleCeilingPerFrame'] / 1e6,
             budget_report['triangleHeadroom']))
    for path in previews:
        print('    preview %s' % path)
    if not budget_report['withinTriangleCeiling']:
        print('  BUDGET EXCEEDED')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
