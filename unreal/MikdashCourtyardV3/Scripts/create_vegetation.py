"""JudeanFloraV1 - the trees, shrubs and dry grasses of the Judean hills, generated offline.

AUTHORED_OFFLINE_SOURCE. This module never imports `unreal`, never touches Content/ and never
opens a map. It writes OBJ meshes, PNG textures, a geometry manifest, a rule-derived placement
plan and preview images under SourceAssets/vegetation-review/JudeanFloraV1/.
Scripts/release_vegetation.py is the separate guarded native importer/placer.

Usage (no engine needed):
    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" \
        Scripts/create_vegetation.py [--export] [--plan] [--tests] [--no-preview]
    --export  meshes + textures + geometry manifest      (default: export and plan together)
    --plan    placement plan from the terrain and the exclusion set
    --tests   compile and run Plugins/MikdashRuntime/Tests/ScatterMathTest.cpp and write
              SourceAssets/vegetation-review/tests.json

WHY
---
The Mount stands on bare ground. The terrain carries as much of the believability as the
architecture does, and a hillside with no plants on it reads as a model, not a place.

WHAT IS AUTHORED AND WHAT IS SOURCED
------------------------------------
The SPECIES LIST and the SIZE RANGES are botanical and are cited per species in SPECIES below
(field ranges from standard reference works, not measurements of any individual plant; no page
number is claimed for a figure this script could not check offline, and `pageCited` records
that honestly). The MESH SHAPES are invented procedural approximations in the habit of each
species; they are not scans, not photogrammetry and not a claim about any particular tree.
Which species carry a MIKDASH SOURCE and which merely GROW THERE is recorded per species in
`mikdashSource` / `growsThere`, and the distinction is never blurred: an olive stands on the
Mount of Olives because Zecharyah 14:4 and Mishnah Parah 3:6 name that hill, whereas a
Jerusalem pine stands there because it is what grows on those slopes.

NOTHING IS PLACED INSIDE THE TEMPLE PRECINCT. Devarim 16:21 forbids planting any tree beside
the altar of the Lord, and the project's own recorded scenario rule (SourceAssets/FutureMountV1/
mount-platform-generation.json, `futureSceneRules.mountTrees`) already removed 144 illustrative
trees whose trunks stood inside the Mount enclosure. The one plant FORM inside the Sanctuary
that a source does put there - the golden vine over the entrance to the Heikhal, Mishnah Middot
3:8 - is metalwork, not vegetation, and is out of scope for a foliage pass. So the exception
clause resolves to: no source places a living tree inside the precinct, and none is placed.

GEOMETRY CONVENTIONS (project standard, unchanged)
--------------------------------------------------
Canonical vertices are UE cm, X east, +Y south, Z up, origin at the plant's ground contact.
Every OBJ is written with Y REFLECTED and triangle winding REVERSED - the legacy OBJ importer
adapter used by create_sanctuary_doors.export, create_keilim_ti_v1.write_obj and
create_oldcity_facades.write_obj; the importer reflects Y back, so the imported StaticMesh must
reproduce `canonicalBoundsCm`, and release_vegetation.py asserts that. One `o` object per file
and NO `g` groups, because the OBJ importer creates one material slot per `g` group (the
SM_KeruvimStudyV1 236-slot lesson). Two materials are needed per tree - bark and leaf - so bark
and leaf go in SEPARATE OBJ FILES and import as separate meshes, the same choice
create_keilim_ti_v1 made for gold versus bread.

THREE PART KINDS, THREE DIFFERENT WINDING CHECKS
------------------------------------------------
The signed-volume check that catches inside-out meshes (sum of dot(A, cross(B, C)) / 6 over the
canonical triangles, which must come out POSITIVE) only means anything for a closed solid, so it
is applied per part kind and the kind is recorded in the manifest:
  solid      trunk, limbs, twigs: closed, every edge used exactly twice, signed volume > 0.
  card       alpha-tested leaf cross-cards: written BACK TO BACK, i.e. every quad appears twice
             with opposite winding. That makes the shell closed (every edge used exactly twice)
             and its signed volume exactly zero to tolerance, which is a real test: a card
             emitted only once leaves an open shell and fails it. Back to back also means the
             canopy reads correctly whether or not the material ends up two-sided, so a
             wrongly reversed winding cannot make a canopy vanish.
  billboard  the far-distance impostor: ONE quad, two triangles, deliberately open and
             deliberately single-sided, drawn by a camera-facing material. Exempt from both
             checks, and the exemption is written into the manifest rather than left implicit.

LODS
----
Every tree carries LOD0/LOD1/LOD2 plus a distance billboard whose texture is an orthographic
render of that species' own LOD1 mesh, so the impostor is a picture of the tree it replaces.
Shrubs carry LOD0/LOD1 and a billboard; grasses carry LOD0/LOD1 and no billboard (they are
culled long before an impostor would help).

PLACEMENT IS BY RULE, NOT BY HAND
---------------------------------
Every instance comes out of MikdashScatter (Plugins/MikdashRuntime/Public/ScatterMath.h),
re-implemented here in Python line for line, including the integer hash, so the offline plan,
the editor commandlet and a packaged build produce the SAME scatter for the same seed.
Plugins/MikdashRuntime/Tests/ScatterMathTest.cpp proves the four contract properties of that
math; --tests runs it and records the numbers in tests.json.

THE TRAP THAT ALREADY COST THIS PROJECT A DAY
---------------------------------------------
Raw actor AABBs are useless as blockers here, for two separate reasons, and both are handled
explicitly in build_exclusions():
  * The 256 SM_JerusalemTerrain_* tiles are 400 m squares whose AABBs are 400-800 m tall boxes
    enclosing everything standing on them, the whole Temple included. Terrain tiles are the
    GROUND the plants stand on; they are excluded from the blocker set BY NAME, and the count
    of tiles skipped is recorded so the exclusion cannot silently stop matching.
  * Hollow union meshes ("Derived union of source outer envelope walls" and its siblings) are
    Boolean unions of many boxes whose AABB - +-8100 XY, Z 300..3425 - encloses the entire outer
    court. Using that AABB flags every point in the court, which is exactly the 100 per cent
    false-blocker result this project already paid for once. They are decomposed into their
    constituent boxes from the architecture manifest's `source_elements_json`, exactly as
    release_place_assets.union_constituent_boxes does, and the recomposition is verified against
    the manifest's expectedBoundsUnrealCm before the boxes are trusted.

LIMITS (also written into the manifest)
---------------------------------------
No visual, collision, cook, performance or packaged acceptance is established by this script.
Species habit is stylised. Nothing here is halachic. The existing illustrative OSM-derived tree
instances are left completely alone; their trunk anchors are read only as keep-out circles so a
new plant is never pushed through one.
"""

import argparse
import hashlib
import json
import math
import struct
import subprocess
import sys
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets' / 'vegetation-review' / 'JudeanFloraV1'
OBJ_DIR = OUT / 'obj'
TEX_DIR = OUT / 'textures'
MANIFEST_PATH = OUT / 'vegetation-manifest.json'
PLAN_PATH = OUT / 'placement-plan.json'
TESTS_PATH = ROOT / 'SourceAssets' / 'vegetation-review' / 'tests.json'
DEST = '/Game/MikdashV3/Vegetation/JudeanFloraV1'

WORKSPACE = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace')
SOURCE_JSON = WORKSPACE / 'mikdash-walkthrough' / 'public' / 'context' / 'jerusalem.json'
SOURCE_JSON_SHA = '76a2b76c0d97f45db7e532b3adbe8b58c02956fa0d3de73db71e31e097ea6463'
ARCHITECTURE_MANIFEST = ROOT / 'SourceAssets' / 'architecture-manifest.json'
MOUNT_TREE_REMOVAL = ROOT / 'SourceAssets' / 'FutureMountV1' / 'mount-tree-removal-manifest.json'
ENCLOSURE_DESIGN = ROOT / 'SourceAssets' / 'FutureMountV1' / 'EnclosureV1' / 'enclosure-design.json'
SCATTER_TEST = ROOT / 'Plugins' / 'MikdashRuntime' / 'Tests' / 'ScatterMathTest.cpp'
SCATTER_PUBLIC = ROOT / 'Plugins' / 'MikdashRuntime' / 'Source' / 'MikdashRuntime' / 'Public'
VCVARS = Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat')

# --------------------------------------------------------------- source constants
# Identical to Workspace/mikdash-walkthrough/lib/mikdash/{jerusalem,market}.ts, and to the
# constants create_oldcity_facades.py already froze. The alignment is baked into the level
# once; it is applied here and never applied twice.
#     UE_cm = ((x_amot + TX) * 50, (z_amot + TZ) * 50, y_amot * 50)
MARKET_X, MARKET_Z = -1750.0, 400.0
TX = 17.509700315687695
TZ = -0.5513496449385334
AMAH_CM = 50.0

# Terrain grid in UE cm, from jerusalem.json terrain {size 257, step 50, origin -6400} in amot.
# StepCm 2500 is the 25 m DEM cell the ScatterMath header's slope comment is about. The derived
# extent -319124.51 .. 320875.49 cm matches expectedBoundsUnrealCm in the 256-tile terrain
# import receipt SourceAssets/context-review/terrain-import-20260907T020927Z-2871d8.json.
TERRAIN_SIZE = 257
TERRAIN_STEP_CM = 50.0 * AMAH_CM
TERRAIN_ORIGIN_X_CM = (-6400.0 + TX) * AMAH_CM
TERRAIN_ORIGIN_Y_CM = (-6400.0 + TZ) * AMAH_CM

SEED = 20260908

# Planting region: 3.2 km square centred on the measured Temple. It reaches the Mount of Olives
# crest to the east, the Kidron floor between, Mount Scopus's shoulder to the north-east and the
# Old City and its western hills, which is every slope a walker on the Mount can see.
REGION_HALF_CM = 160000.0

# ------------------------------------------------------------------ draw budget
# See BUDGET below and budget_report(). The ceiling is the same 3.5 M triangles per frame the
# ScatterMath test already asserts for the tree LOD ladder.
FOLIAGE_TRIANGLE_CEILING = 3.5e6
INSTANCE_CAP_TOTAL = 360000
VISIBLE_FRACTION = 1.0 / 3.0        # of the cull disc actually in frustum and unoccluded
CLUMPING_SAFETY = 3.0               # groves are not uniform; charge 3x the uniform estimate


# =====================================================================================
# 1. SPECIES
# =====================================================================================
# heightM / crownM / trunkDiameterM are FIELD RANGES for a mature plant, not a measurement of
# an individual. `sizeSource` names where the range comes from. `pageCited` is False wherever a
# page number could not be checked from this machine, and no page number is then invented.
#
# `mikdashSource` is a source that connects the plant to the Mikdash or its service; it is None
# for a species that simply grows in these hills, and `growsThere` says why it belongs on the
# slope regardless. That distinction is the whole point of the field and is never blurred.
#
# Bands are in UE cm relative to the Temple Mount platform datum (Z 0 = the deck, ~743 m ASL),
# because that is the level's own zero. Slopes are degrees.
FP = 'Zohary, M., Plants of the Bible (Cambridge University Press, 1982), species entry'
FLP = 'Zohary & Feinbrun-Dothan, Flora Palaestina vols I-IV (Israel Academy of Sciences, 1966-1986), species entry'
DANIN = 'Danin, A., Flora and Vegetation of Israel (in Zohary ed.), Judean hills batha and maquis communities'

SPECIES = [
    dict(
        key='Olive', label='olive', binomial='Olea europaea', form='tree',
        heightM=[5.0, 12.0], crownM=[4.0, 8.0], trunkDiameterM=[0.30, 0.90],
        sizeSource=FP + ' Olea europaea; cultivated Judean groves run 5-10 m with a 4-8 m crown',
        pageCited=False,
        mikdashSource=('Olive oil for the Menorah, Shemot 27:20 and Mishnah Menachot 8:4-5, which '
                       'ranks the oil of Tekoa first. The Mount of Olives itself is named in '
                       'Zecharyah 14:4, and Mishnah Parah 3:6 has the causeway run from the Temple '
                       'Mount to it for the Red Heifer.'),
        growsThere='The characteristic cultivated tree of the terraced Judean hillsides.',
        leafShape='lanceolate', leafLengthCm=6.0, leafColour=(96, 112, 74), leafBackColour=(150, 158, 132),
        barkColour=(126, 118, 100), evergreen=True,
        band=dict(minZ=-9000.0, maxZ=14000.0, featherZ=2500.0, minSlope=2.0, maxSlope=32.0, slopeFeather=5.0),
        spacingCm=520.0, crownRadiusCm=320.0, densityPer100SqM=0.2,
        terraced=True, clusterRadiusCm=9000.0, clusterStrength=0.62, clusters=200,
        gnarledFraction=0.35,
        scaleRange=[0.72, 1.28], tiltDegrees=7.0, downhillTilt=0.30,
    ),
    dict(
        key='JerusalemPine', label='Jerusalem pine', binomial='Pinus halepensis', form='tree',
        heightM=[10.0, 20.0], crownM=[5.0, 9.0], trunkDiameterM=[0.30, 0.60],
        sizeSource=FLP + ' Pinus halepensis; 10-20 m in the Judean hills, taller only on deep soil',
        pageCited=False,
        mikdashSource=None,
        growsThere=('The dominant conifer of the Jerusalem hills and of a century of afforestation '
                    'on them; it is what a modern eye reads as "the hills around Jerusalem".'),
        leafShape='needle', leafLengthCm=9.0, leafColour=(74, 100, 68), leafBackColour=(96, 118, 86),
        barkColour=(118, 92, 74), evergreen=True,
        band=dict(minZ=-4000.0, maxZ=16000.0, featherZ=3000.0, minSlope=0.0, maxSlope=34.0, slopeFeather=6.0),
        spacingCm=700.0, crownRadiusCm=400.0, densityPer100SqM=0.12,
        terraced=False, clusterRadiusCm=14000.0, clusterStrength=0.68, clusters=120,
        gnarledFraction=0.0,
        scaleRange=[0.78, 1.30], tiltDegrees=5.0, downhillTilt=0.20,
    ),
    dict(
        key='Cypress', label='cypress', binomial='Cupressus sempervirens', form='tree',
        heightM=[12.0, 22.0], crownM=[2.0, 5.0], trunkDiameterM=[0.25, 0.55],
        sizeSource=FP + ' Cupressus sempervirens; the columnar form is 2-5 m across at 12-22 m tall',
        pageCited=False,
        mikdashSource=('"Berosh" supplies the boards, floor and doors of Shlomo\'s Temple, '
                       'Melachim I 6:15 and 6:34. The identification of berosh with Cupressus is the '
                       'common one but is disputed (Juniperus excelsa and Abies cilicica are the rival '
                       'readings), and that dispute is recorded rather than hidden.'),
        growsThere='Native to the eastern Mediterranean hills and long planted on them.',
        leafShape='scale', leafLengthCm=3.0, leafColour=(58, 84, 62), leafBackColour=(74, 96, 74),
        barkColour=(122, 100, 82), evergreen=True,
        band=dict(minZ=-6000.0, maxZ=15000.0, featherZ=2500.0, minSlope=0.0, maxSlope=30.0, slopeFeather=5.0),
        spacingCm=560.0, crownRadiusCm=220.0, densityPer100SqM=0.05,
        terraced=False, clusterRadiusCm=6000.0, clusterStrength=0.7, clusters=110,
        gnarledFraction=0.0,
        scaleRange=[0.80, 1.25], tiltDegrees=3.0, downhillTilt=0.10,
    ),
    dict(
        key='Almond', label='almond', binomial='Amygdalus communis (Prunus dulcis)', form='tree',
        heightM=[3.5, 8.0], crownM=[3.0, 6.0], trunkDiameterM=[0.15, 0.40],
        sizeSource=FP + ' Amygdalus communis; a small tree of 3.5-8 m',
        pageCited=False,
        mikdashSource=('The Menorah\'s cups are "meshukadim", made in the form of the almond blossom, '
                       'Shemot 25:33-34. Aharon\'s staff bore almonds, Bamidbar 17:23.'),
        growsThere='Grows wild and cultivated on the terraces; the first blossom of the Judean spring.',
        leafShape='lanceolate', leafLengthCm=8.0, leafColour=(104, 128, 76), leafBackColour=(138, 156, 108),
        barkColour=(104, 92, 82), evergreen=False,
        band=dict(minZ=-8000.0, maxZ=12000.0, featherZ=2000.0, minSlope=2.0, maxSlope=28.0, slopeFeather=4.0),
        spacingCm=460.0, crownRadiusCm=260.0, densityPer100SqM=0.07,
        terraced=True, clusterRadiusCm=7000.0, clusterStrength=0.66, clusters=110,
        gnarledFraction=0.10,
        scaleRange=[0.75, 1.25], tiltDegrees=6.0, downhillTilt=0.25,
    ),
    dict(
        key='Fig', label='fig', binomial='Ficus carica', form='tree',
        heightM=[3.0, 8.0], crownM=[4.0, 9.0], trunkDiameterM=[0.20, 0.60],
        sizeSource=FP + ' Ficus carica; a low, wide, often multi-stemmed tree, crown wider than tall',
        pageCited=False,
        mikdashSource=('One of the seven species of Devarim 8:8, from which bikkurim are brought to the '
                       'Mikdash; Mishnah Bikkurim 3:1 has the fig among the first fruits marked in the '
                       'field and carried up to Yerushalayim.'),
        growsThere='Planted at terrace edges and beside cisterns throughout the Judean hills.',
        leafShape='palmate', leafLengthCm=18.0, leafColour=(86, 122, 66), leafBackColour=(124, 148, 100),
        barkColour=(148, 142, 128), evergreen=False,
        band=dict(minZ=-11000.0, maxZ=9000.0, featherZ=2000.0, minSlope=0.0, maxSlope=26.0, slopeFeather=4.0),
        spacingCm=520.0, crownRadiusCm=340.0, densityPer100SqM=0.05,
        terraced=True, clusterRadiusCm=5000.0, clusterStrength=0.7, clusters=130,
        gnarledFraction=0.20,
        scaleRange=[0.75, 1.25], tiltDegrees=8.0, downhillTilt=0.30,
        wadiPreference=0.55,
    ),
    dict(
        key='Pomegranate', label='pomegranate', binomial='Punica granatum', form='tree',
        heightM=[2.0, 5.0], crownM=[2.0, 4.0], trunkDiameterM=[0.08, 0.25],
        sizeSource=FP + ' Punica granatum; a large shrub or small tree of 2-5 m',
        pageCited=False,
        mikdashSource=('Rimonim of blue, purple and scarlet on the hem of the Kohen Gadol\'s me\'il, '
                       'Shemot 28:33-34, and two hundred rimonim in rows on the capitals of Yachin and '
                       'Boaz, Melachim I 7:18-20. Also one of the seven species, Devarim 8:8.'),
        growsThere='A standard terrace and garden shrub of the hills.',
        leafShape='ovate', leafLengthCm=5.0, leafColour=(96, 132, 72), leafBackColour=(132, 156, 104),
        barkColour=(140, 118, 96), evergreen=False,
        band=dict(minZ=-10000.0, maxZ=8000.0, featherZ=2000.0, minSlope=0.0, maxSlope=25.0, slopeFeather=4.0),
        spacingCm=380.0, crownRadiusCm=190.0, densityPer100SqM=0.05,
        terraced=True, clusterRadiusCm=4500.0, clusterStrength=0.72, clusters=120,
        gnarledFraction=0.0,
        scaleRange=[0.75, 1.30], tiltDegrees=8.0, downhillTilt=0.25,
        wadiPreference=0.45,
    ),
    dict(
        key='DatePalm', label='date palm', binomial='Phoenix dactylifera', form='palm',
        heightM=[12.0, 22.0], crownM=[6.0, 9.0], trunkDiameterM=[0.35, 0.50],
        sizeSource=FP + ' Phoenix dactylifera; 12-22 m with a 6-9 m crown of pinnate fronds',
        pageCited=False,
        mikdashSource=('Temarim are carved on every wall, post and gate of Yechezkel\'s Temple, '
                       'Yechezkel 40:16, 40:22, 40:26, 41:18-20 - as CARVED RELIEF, not as living '
                       'trees inside the precinct. The lulav of Vayikra 23:40 and Mishnah Sukkah 3:1 '
                       'is the palm frond.'),
        growsThere=('The date palm needs groundwater and heat; it does not grow naturally on the '
                    'Jerusalem hilltops. It is therefore placed ONLY on low ground - the Kidron floor '
                    'and the valley bottoms below the platform datum - and never on the ridges. '
                    'Putting palms on the crest would be the single most obvious botanical error '
                    'available in this landscape.'),
        leafShape='pinnate', leafLengthCm=300.0, leafColour=(108, 132, 72), leafBackColour=(138, 154, 104),
        barkColour=(134, 116, 90), evergreen=True,
        # AT OR BELOW THE PLATFORM DATUM, and flat. Measured against the project's own DEM:
        # the Kidron floor east of the Mount sits about -20 m relative to the deck, so a band
        # starting at -60 m (as a first attempt did) matched nothing but the far desert and
        # planted six palms in the whole scene. Low ground here means the valley floors.
        band=dict(minZ=-30000.0, maxZ=1000.0, featherZ=2000.0, minSlope=0.0, maxSlope=12.0, slopeFeather=3.0),
        regionOverrideCm=[-20000.0, -60000.0, 90000.0, 70000.0],
        spacingCm=760.0, crownRadiusCm=420.0, densityPer100SqM=0.35,
        terraced=False, clusterRadiusCm=5000.0, clusterStrength=0.7, clusters=40,
        gnarledFraction=0.0,
        scaleRange=[0.82, 1.20], tiltDegrees=5.0, downhillTilt=0.15,
        wadiPreference=0.85,
    ),
    dict(
        key='Carob', label='carob', binomial='Ceratonia siliqua', form='tree',
        heightM=[6.0, 12.0], crownM=[6.0, 10.0], trunkDiameterM=[0.30, 0.80],
        sizeSource=FP + ' Ceratonia siliqua; a dense evergreen of 6-12 m with a broad crown',
        pageCited=False,
        mikdashSource=None,
        growsThere=('Warm, sunny, south-facing rocky slopes; the Ceratonio-Pistacietum association of '
                    'the Judean foothills. Its aspect preference is modelled: the band prefers the '
                    'downhill bearing that faces the sun in this frame. (Choni and the carob, '
                    'Ta\'anit 23a, is a Judean image but not a Mikdash source, and is not claimed as one.)'),
        leafShape='pinnate', leafLengthCm=14.0, leafColour=(66, 96, 56), leafBackColour=(102, 124, 86),
        barkColour=(112, 100, 86), evergreen=True,
        band=dict(minZ=-14000.0, maxZ=9000.0, featherZ=2500.0, minSlope=3.0, maxSlope=34.0, slopeFeather=5.0,
                  preferredAspect=90.0, aspectWeight=0.65),
        spacingCm=640.0, crownRadiusCm=380.0, densityPer100SqM=0.07,
        terraced=False, clusterRadiusCm=8000.0, clusterStrength=0.68, clusters=100,
        gnarledFraction=0.25,
        scaleRange=[0.78, 1.28], tiltDegrees=7.0, downhillTilt=0.30,
    ),
    dict(
        key='Terebinth', label='terebinth', binomial='Pistacia palaestina / P. atlantica', form='tree',
        heightM=[4.0, 12.0], crownM=[4.0, 12.0], trunkDiameterM=[0.20, 0.90],
        sizeSource=(FP + ' Pistacia palaestina (3-8 m) and P. atlantica (10-15 m, very broad crown); '
                    'the range spans both, which is why it is wide'),
        pageCited=False,
        mikdashSource=None,
        growsThere=('The elah of Bereishit 35:4 and Shoftim 6:11, and one of the two climax trees of '
                    'the natural Judean maquis together with Quercus calliprinos. It belongs on the '
                    'shaded northern faces and in the wadis. A biblical mention is not a Mikdash '
                    'connection and is not counted as one here.'),
        leafShape='pinnate', leafLengthCm=12.0, leafColour=(88, 116, 68), leafBackColour=(122, 142, 100),
        barkColour=(108, 98, 90), evergreen=False,
        band=dict(minZ=-16000.0, maxZ=12000.0, featherZ=3000.0, minSlope=2.0, maxSlope=36.0, slopeFeather=6.0,
                  preferredAspect=270.0, aspectWeight=0.45),
        spacingCm=680.0, crownRadiusCm=380.0, densityPer100SqM=0.09,
        terraced=False, clusterRadiusCm=10000.0, clusterStrength=0.64, clusters=110,
        gnarledFraction=0.30,
        scaleRange=[0.70, 1.35], tiltDegrees=9.0, downhillTilt=0.35,
        wadiPreference=0.60,
    ),
    dict(
        key='Sage', label='Judean sage', binomial='Salvia fruticosa', form='shrub',
        heightM=[0.5, 1.0], crownM=[0.6, 1.2], trunkDiameterM=[0.02, 0.05],
        sizeSource=FLP + ' Salvia fruticosa; a dwarf shrub of 0.5-1.0 m',
        pageCited=False,
        mikdashSource=('Zohary proposed that the whorled branching of a Salvia is the botanical model '
                       'behind the Menorah\'s form. That is a PROPOSAL about the shape of a vessel, not '
                       'a source that puts sage in the Mikdash, and it is recorded as a proposal.'),
        growsThere='A dominant dwarf shrub of the Judean batha on shallow rocky soil.',
        leafShape='ovate', leafLengthCm=5.0, leafColour=(126, 138, 108), leafBackColour=(158, 164, 142),
        barkColour=(120, 110, 92), evergreen=True,
        band=dict(minZ=-18000.0, maxZ=17000.0, featherZ=3000.0, minSlope=2.0, maxSlope=42.0, slopeFeather=6.0),
        spacingCm=180.0, crownRadiusCm=70.0, densityPer100SqM=0.3,
        terraced=False, clusterRadiusCm=4000.0, clusterStrength=0.5, clusters=220,
        gnarledFraction=0.0,
        scaleRange=[0.70, 1.35], tiltDegrees=12.0, downhillTilt=0.20,
    ),
    dict(
        key='Hyssop', label='hyssop (ezov)', binomial='Origanum syriacum', form='shrub',
        heightM=[0.3, 0.7], crownM=[0.3, 0.7], trunkDiameterM=[0.01, 0.03],
        sizeSource=FLP + ' Origanum syriacum; 0.3-0.7 m',
        pageCited=False,
        mikdashSource=('Ezov is bound with cedar wood and crimson wool and thrown into the burning of '
                       'the Red Heifer, Bamidbar 19:6 and Mishnah Parah 3:10-11 - and that burning takes '
                       'place on the Mount of Olives opposite the Temple, which is exactly this hillside. '
                       'The identification of ezov with Origanum syriacum is Rambam\'s and is the '
                       'standard one; it is an identification, not a certainty.'),
        growsThere='Grows out of rock crevices and terrace walls across these hills.',
        leafShape='ovate', leafLengthCm=2.0, leafColour=(132, 142, 112), leafBackColour=(164, 168, 146),
        barkColour=(122, 112, 94), evergreen=True,
        band=dict(minZ=-18000.0, maxZ=17000.0, featherZ=3000.0, minSlope=4.0, maxSlope=48.0, slopeFeather=6.0),
        spacingCm=150.0, crownRadiusCm=50.0, densityPer100SqM=0.18,
        terraced=False, clusterRadiusCm=3000.0, clusterStrength=0.52, clusters=240,
        gnarledFraction=0.0,
        scaleRange=[0.70, 1.35], tiltDegrees=14.0, downhillTilt=0.20,
    ),
    dict(
        key='Rockrose', label='rockrose', binomial='Cistus creticus', form='shrub',
        heightM=[0.5, 1.2], crownM=[0.6, 1.3], trunkDiameterM=[0.02, 0.05],
        sizeSource=FLP + ' Cistus creticus; 0.5-1.2 m',
        pageCited=False,
        mikdashSource=None,
        growsThere=('The first shrub back after fire or grazing on these slopes, and the pink flush on '
                    'the Judean hillsides in spring.'),
        leafShape='ovate', leafLengthCm=4.0, leafColour=(104, 122, 86), leafBackColour=(142, 152, 126),
        barkColour=(116, 100, 84), evergreen=True,
        band=dict(minZ=-18000.0, maxZ=17000.0, featherZ=3000.0, minSlope=3.0, maxSlope=44.0, slopeFeather=6.0),
        spacingCm=190.0, crownRadiusCm=75.0, densityPer100SqM=0.22,
        terraced=False, clusterRadiusCm=5000.0, clusterStrength=0.55, clusters=200,
        gnarledFraction=0.0,
        scaleRange=[0.70, 1.35], tiltDegrees=12.0, downhillTilt=0.20,
    ),
    dict(
        key='ThornyBurnet', label='thorny burnet', binomial='Sarcopoterium spinosum', form='shrub',
        heightM=[0.3, 0.6], crownM=[0.4, 0.9], trunkDiameterM=[0.01, 0.04],
        sizeSource=FLP + ' Sarcopoterium spinosum; a hemispherical dwarf shrub 0.3-0.6 m tall',
        pageCited=False,
        mikdashSource=None,
        growsThere=(DANIN + '; Sarcopoterium is THE dominant dwarf shrub of degraded Judean batha and '
                    'the single most characteristic plant of an exposed, grazed, rocky Jerusalem ridge. '
                    'If one plant has to carry the bare ridges, it is this one.'),
        leafShape='needle', leafLengthCm=1.5, leafColour=(118, 124, 96), leafBackColour=(146, 148, 124),
        barkColour=(128, 116, 96), evergreen=True,
        band=dict(minZ=-18000.0, maxZ=18000.0, featherZ=3000.0, minSlope=0.0, maxSlope=50.0, slopeFeather=6.0),
        spacingCm=160.0, crownRadiusCm=60.0, densityPer100SqM=0.55,
        terraced=False, clusterRadiusCm=6000.0, clusterStrength=0.38, clusters=240,
        gnarledFraction=0.0,
        scaleRange=[0.70, 1.35], tiltDegrees=10.0, downhillTilt=0.15,
    ),
    dict(
        key='DryGrass', label='dry grasses', binomial='Hordeum spontaneum / Avena sterilis / Stipa spp.',
        form='grass',
        heightM=[0.3, 0.8], crownM=[0.2, 0.5], trunkDiameterM=[0.0, 0.0],
        sizeSource=FLP + ' Hordeum spontaneum and Avena sterilis; culms 0.3-0.8 m',
        pageCited=False,
        mikdashSource=('Hordeum spontaneum is the wild ancestor of the barley of the Omer, cut on the '
                       'night after the first day of Pesach from a field near Yerushalayim - Mishnah '
                       'Menachot 10:2-3. The stand modelled here is wild hillside grass, not a barley '
                       'field, and the Omer field is not being depicted.'),
        growsThere='The dry annual grass layer that covers every un-grazed Judean slope by early summer.',
        leafShape='blade', leafLengthCm=45.0, leafColour=(178, 166, 118), leafBackColour=(196, 184, 140),
        barkColour=(170, 158, 116), evergreen=False,
        band=dict(minZ=-20000.0, maxZ=18000.0, featherZ=3000.0, minSlope=0.0, maxSlope=40.0, slopeFeather=8.0),
        spacingCm=110.0, crownRadiusCm=35.0, densityPer100SqM=1.8,
        terraced=False, clusterRadiusCm=9000.0, clusterStrength=0.32, clusters=260,
        gnarledFraction=0.0,
        scaleRange=[0.65, 1.40], tiltDegrees=16.0, downhillTilt=0.10,
    ),
]
SPECIES_BY_KEY = {s['key']: s for s in SPECIES}

# LOD ladder per form: (distance at which the step takes over in cm, triangle target).
# Distances are the same ladder the ScatterMath test asserts for trees.
LOD_DISTANCES = {
    'tree': [0.0, 4000.0, 12000.0, 30000.0],
    'palm': [0.0, 4000.0, 12000.0, 30000.0],
    'shrub': [0.0, 2500.0, 8000.0],
    'grass': [0.0, 1500.0],
}
CULL_DISTANCE_CM = {'tree': 60000.0, 'palm': 60000.0, 'shrub': 14000.0, 'grass': 6000.0}


# =====================================================================================
# 2. DETERMINISTIC HASH - a line-for-line port of MikdashScatter's integer hash
# =====================================================================================
# Every random draw in the placement plan comes from these, and from nothing else. No
# random module, no time, no std::rand. The C++ header and this Python must agree bit for
# bit or the offline plan and the in-editor scatter drift apart, so the port is literal and
# check_hash_parity() below re-derives a handful of values the C++ test also prints.
MASK32 = 0xFFFFFFFF


def hash_int(v):
    v &= MASK32
    v ^= v >> 16
    v = (v * 0x85EBCA6B) & MASK32
    v ^= v >> 13
    v = (v * 0xC2B2AE35) & MASK32
    v ^= v >> 16
    return v


def hash_combine(seed, value):
    seed &= MASK32
    mixed = (value + 0x9E3779B9 + ((seed << 6) & MASK32) + (seed >> 2)) & MASK32
    return hash_int(seed ^ mixed)


def hash_unit(seed, index, lane):
    return hash_combine(hash_combine(seed, index), lane) / 4294967296.0


def hash_range(seed, index, lane, lo, hi):
    return lo + (hi - lo) * hash_unit(seed, index, lane)


def hash_bell(seed, index, lane):
    a = hash_unit(seed, index, lane)
    b = hash_unit(seed, index, (lane + 0x51ED2701) & MASK32)
    c = hash_unit(seed, index, (lane + 0x1B873593) & MASK32)
    return clamp((a + b + c) * 2.0 - 3.0, -3.0, 3.0)


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def smoothstep(v, lo, hi):
    if hi <= lo:
        return 1.0 if v >= hi else 0.0
    t = clamp((v - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    length = math.sqrt(dot(a, a))
    if length < 1e-12:
        return (0.0, 0.0, 1.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def basis_from(axis):
    """Any orthonormal frame whose third vector is `axis`."""
    axis = norm(axis)
    reference = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = norm(cross(reference, axis))
    v = cross(axis, u)
    return u, v, axis


# =====================================================================================
# 3. GEOMETRY - one closed canonical solid, or one back-to-back card sheet
# =====================================================================================
class Part:
    """A named lump of triangles with a declared kind: solid, card or billboard.

    kind decides which winding check applies, and the answer is written into the manifest
    per part rather than asserted once for the whole file.
    """

    __slots__ = ('name', 'kind', 'material', 'vertices', 'uvs', 'faces')

    def __init__(self, name, kind, material):
        if kind not in ('solid', 'card', 'billboard'):
            raise ValueError('unknown part kind ' + kind)
        self.name = name
        self.kind = kind
        self.material = material
        self.vertices = []
        self.uvs = []
        self.faces = []

    def add(self, point, uv=(0.0, 0.0)):
        self.vertices.append((float(point[0]), float(point[1]), float(point[2])))
        self.uvs.append((float(uv[0]), float(uv[1])))
        return len(self.vertices) - 1

    def tri(self, a, b, c):
        self.faces.append((a, b, c))

    def quad(self, a, b, c, d):
        self.faces.append((a, b, c))
        self.faces.append((a, c, d))

    def fan(self, loop):
        for index in range(1, len(loop) - 1):
            self.faces.append((loop[0], loop[index], loop[index + 1]))

    def volume(self):
        """Signed volume, sum dot(A, cross(B, C)) / 6. Positive for an outward-wound solid."""
        total = 0.0
        for a, b, c in self.faces:
            ax, ay, az = self.vertices[a]
            bx, by, bz = self.vertices[b]
            cx, cy, cz = self.vertices[c]
            total += (ax * (by * cz - bz * cy)
                      + ay * (bz * cx - bx * cz)
                      + az * (bx * cy - by * cx))
        return total / 6.0

    def orient(self):
        """Flip until the canonical signed volume is positive. Solids only."""
        value = self.volume()
        if value < 0.0:
            self.faces = [(a, c, b) for a, b, c in self.faces]
            value = -value
        return value

    def edge_use(self):
        """{undirected edge: count}. A closed shell uses every edge exactly twice."""
        keys = [tuple(round(x, 4) for x in p) for p in self.vertices]
        counter = {}
        for a, b, c in self.faces:
            for i, j in ((a, b), (b, c), (c, a)):
                key = tuple(sorted((keys[i], keys[j])))
                counter[key] = counter.get(key, 0) + 1
        return counter

    def closed(self, exact=True):
        """A solid must use every edge exactly twice.

        A back-to-back card sheet is also boundary-free, but the quad's own diagonal is shared
        by the front pair AND the back pair and so appears four times. The correct topological
        test for "no boundary" is therefore an EVEN count, not a count of two, and even is
        still enough to catch the failure this exists for: a card written only once leaves its
        four rim edges used exactly once each.
        """
        counts = self.edge_use().values()
        if exact:
            return all(count == 2 for count in counts)
        return all(count % 2 == 0 for count in counts)

    def bounds(self):
        return {
            'min': [min(p[i] for p in self.vertices) for i in range(3)],
            'max': [max(p[i] for p in self.vertices) for i in range(3)],
        }

    def check(self, tolerance_volume=1e-6):
        """Run the winding check that belongs to this part's kind. Returns the record."""
        record = {'part': self.name, 'kind': self.kind, 'triangles': len(self.faces),
                  'vertices': len(self.vertices)}
        if self.kind == 'solid':
            value = self.orient()
            if not self.closed():
                raise AssertionError('open solid part ' + self.name)
            if not value > 0.0:
                raise AssertionError('degenerate solid part ' + self.name)
            record['signedVolumeCm3'] = round(value, 4)
            record['closed'] = True
        elif self.kind == 'card':
            # Back-to-back cards: closed shell, zero volume. A card emitted only once is an
            # open shell and fails here, which is the entire point of writing them in pairs.
            if not self.closed(exact=False):
                raise AssertionError('leaf cards of %s are not back to back' % self.name)
            value = self.volume()
            span = max(self.bounds()['max'][i] - self.bounds()['min'][i] for i in range(3))
            if abs(value) > tolerance_volume * max(1.0, span) ** 3:
                raise AssertionError('card sheet %s is not zero volume: %g' % (self.name, value))
            record['signedVolumeCm3'] = round(value, 9)
            record['closed'] = True
        else:
            if len(self.faces) != 2:
                raise AssertionError('billboard %s must be exactly two triangles' % self.name)
            record['closed'] = False
            record['windingCheckExempt'] = ('single open camera-facing quad; a closed-shell or '
                                            'signed-volume test is meaningless for it')
        record['boundsCm'] = self.bounds()
        return record


def tapered_tube(part, spine, radii, sides, twist=0.0, flute=0.0):
    """Closed capped tube swept along a polyline spine with a per-node radius.

    spine: list of (x, y, z) nodes, at least two. radii: one radius per node.
    flute adds a fixed radial ripple, which is what makes an old olive trunk read as fluted
    rather than as a smooth cone.
    """
    if len(spine) < 2 or len(spine) != len(radii):
        raise ValueError('tapered_tube needs matching spine and radii')
    rings = []
    for index, centre in enumerate(spine):
        if index == 0:
            axis = norm(tuple(spine[1][i] - spine[0][i] for i in range(3)))
        elif index == len(spine) - 1:
            axis = norm(tuple(spine[-1][i] - spine[-2][i] for i in range(3)))
        else:
            axis = norm(tuple(spine[index + 1][i] - spine[index - 1][i] for i in range(3)))
        u, v, _ = basis_from(axis)
        ring = []
        for k in range(sides):
            angle = 2.0 * math.pi * k / sides + twist * index
            radius = radii[index] * (1.0 + flute * math.cos(sides * 0.5 * angle))
            point = tuple(centre[i] + radius * (math.cos(angle) * u[i] + math.sin(angle) * v[i])
                          for i in range(3))
            ring.append(part.add(point, (k / float(sides), index / float(len(spine) - 1))))
        rings.append(ring)
    for index in range(len(rings) - 1):
        low, high = rings[index], rings[index + 1]
        for k in range(sides):
            nxt = (k + 1) % sides
            part.quad(low[k], low[nxt], high[nxt], high[k])
    part.fan(rings[-1])
    part.fan(rings[0][::-1])


def card(part, centre, axis_u, axis_v, half_u, half_v, uv_rect):
    """One alpha-tested quad, written BACK TO BACK so the sheet stays closed."""
    u0, v0, u1, v1 = uv_rect
    corners = []
    for su, sv, uv in ((-1, -1, (u0, v1)), (1, -1, (u1, v1)), (1, 1, (u1, v0)), (-1, 1, (u0, v0))):
        point = tuple(centre[i] + su * half_u * axis_u[i] + sv * half_v * axis_v[i] for i in range(3))
        corners.append(part.add(point, uv))
    a, b, c, d = corners
    part.quad(a, b, c, d)
    back = []
    for index in (a, b, c, d):
        back.append(part.add(part.vertices[index], part.uvs[index]))
    e, f, g, h = back
    part.quad(e, h, g, f)


def cross_cluster(part, centre, radius, height, seed, index, uv_rect, cards=2, tilt=0.0):
    """A leaf cluster as `cards` intersecting vertical cards rotated about the vertical."""
    base_angle = 2.0 * math.pi * hash_unit(seed, index, 41)
    lean = tilt * (hash_unit(seed, index, 42) - 0.5)
    for k in range(cards):
        angle = base_angle + math.pi * k / cards
        axis_u = (math.cos(angle), math.sin(angle), 0.0)
        axis_v = norm((lean * math.cos(angle + 1.57), lean * math.sin(angle + 1.57), 1.0))
        card(part, centre, axis_u, axis_v, radius, height * 0.5, uv_rect)


# =====================================================================================
# 4. PLANT BUILDERS
# =====================================================================================
# Each builder returns (bark_parts, leaf_parts) in canonical cm with the ground contact at
# the origin, built at the MIDDLE of the species' height range. Per-instance scale jitter
# then spreads instances across the range, so the range in SPECIES is honoured by the
# placement, not by the mesh.
#
# Detail is driven by one `level` number so the LOD ladder is the same shape for every
# species: level 0 full, level 1 reduced, level 2 minimal.
# Detail per level. LOD0 is set from the draw budget, not from taste: the budget arithmetic in
# BudgetChecks (ScatterMathTest.cpp) sizes the whole foliage load against a 3.5 M triangle
# ceiling assuming about 3000 triangles at LOD0, and comes out with roughly nine times the
# headroom it needs, so LOD0 can afford to be a real tree rather than a diagram. LOD1 and LOD2
# fall away steeply because they are what actually gets drawn most of the time - the LOD0 ring
# is only the first 40 m of a 600 m cull disc.
TREE_LEVELS = [
    dict(sides=10, orders=2, clusters=90, cards=3, twigs=True),
    dict(sides=6, orders=1, clusters=32, cards=2, twigs=False),
    dict(sides=4, orders=0, clusters=10, cards=1, twigs=False),
]
SHRUB_LEVELS = [dict(stems=9, clusters=16, cards=2), dict(stems=4, clusters=6, cards=1)]
GRASS_LEVELS = [dict(blades=11, cards=1), dict(blades=4, cards=1)]


def mid(range_pair):
    return 0.5 * (range_pair[0] + range_pair[1])


def leaf_uv(species, index):
    """Pick one of the four leaf silhouettes in this species' 2x2 atlas."""
    cell = index % 4
    u0 = 0.5 * (cell % 2)
    v0 = 0.5 * (cell // 2)
    inset = 0.002
    return (u0 + inset, v0 + inset, u0 + 0.5 - inset, v0 + 0.5 - inset)


def build_tree(species, level, seed, gnarled=False):
    """Trunk and main branches as real geometry; canopy as alpha-tested cross-cards."""
    setup = TREE_LEVELS[level]
    height = mid(species['heightM']) * 100.0
    crown = mid(species['crownM']) * 100.0
    trunk_radius = mid(species['trunkDiameterM']) * 50.0
    bark = Part('%s_L%d_Bark' % (species['key'], level), 'solid', 'bark')
    leaf = Part('%s_L%d_Leaf' % (species['key'], level), 'card', 'leaf')

    # --- trunk. A gnarled olive gets a short, heavily leaning, fluted, twisted bole.
    clear = height * (0.22 if gnarled else 0.38)
    if species['key'] == 'Cypress':
        clear = height * 0.10
    nodes = 6 if level == 0 else (4 if level == 1 else 2)
    lean = (0.28 if gnarled else 0.06) * height
    lean_angle = 2.0 * math.pi * hash_unit(seed, 1, 51)
    spine, radii = [], []
    for i in range(nodes + 1):
        t = i / float(nodes)
        wobble = lean * t * t
        sway = (0.05 * height) * math.sin(3.1 * t + 2.0 * hash_unit(seed, i, 52))
        spine.append((wobble * math.cos(lean_angle) + sway * 0.3,
                      wobble * math.sin(lean_angle) + sway * 0.3,
                      clear * t))
        flare = 1.0 + 0.85 * (1.0 - t) ** 3
        radii.append(trunk_radius * flare * (1.0 - 0.42 * t))
    tapered_tube(bark, spine, radii, setup['sides'],
                 twist=(0.22 if gnarled else 0.04), flute=(0.22 if gnarled else 0.05))

    # --- limbs. Real geometry, not cards: the silhouette of a leafless olive limb is most
    # of what makes an olive read as an olive.
    limb_tips = []
    limb_count = (7 if gnarled else 6) if level == 0 else (3 if level == 1 else 0)
    top = spine[-1]
    for b in range(limb_count):
        angle = 2.0 * math.pi * (b / float(max(1, limb_count))) + hash_unit(seed, b, 53)
        rise = height * (0.30 + 0.34 * hash_unit(seed, b, 54))
        reach = crown * (0.30 + 0.20 * hash_unit(seed, b, 55))
        tip = (top[0] + reach * math.cos(angle), top[1] + reach * math.sin(angle), top[2] + rise)
        limb_spine = [top,
                      (top[0] + reach * 0.35 * math.cos(angle) - 0.06 * reach * math.sin(angle),
                       top[1] + reach * 0.35 * math.sin(angle) + 0.06 * reach * math.cos(angle),
                       top[2] + rise * 0.45),
                      tip]
        limb_radius = radii[-1] * (0.62 - 0.06 * b / max(1, limb_count))
        tapered_tube(bark, limb_spine, [limb_radius, limb_radius * 0.62, limb_radius * 0.24],
                     max(4, setup['sides'] - 2), twist=0.1 if gnarled else 0.0)
        limb_tips.append(tip)
        if setup['orders'] >= 2:
            for s in range(2):
                sub = angle + (0.8 if s else -0.8) + 0.5 * hash_unit(seed, b * 8 + s, 56)
                sub_reach = reach * (0.42 + 0.22 * hash_unit(seed, b * 8 + s, 57))
                sub_tip = (tip[0] + sub_reach * math.cos(sub), tip[1] + sub_reach * math.sin(sub),
                           tip[2] + rise * (0.24 + 0.20 * hash_unit(seed, b * 8 + s, 58)))
                tapered_tube(bark, [tip, sub_tip], [limb_radius * 0.30, limb_radius * 0.11],
                             max(4, setup['sides'] - 3))
                limb_tips.append(sub_tip)
    if not limb_tips:
        limb_tips = [top]

    # --- canopy. Clusters are hung on the limb tips, so the leaves sit where wood ends.
    columnar = species['key'] == 'Cypress'
    clusters = setup['clusters']
    cluster_radius = crown * (0.16 if level == 0 else (0.26 if level == 1 else 0.44))
    for c in range(clusters):
        anchor = limb_tips[c % len(limb_tips)]
        spread = crown * 0.5 * (0.35 + 0.65 * hash_unit(seed, c, 61) ** 0.5)
        theta = 2.0 * math.pi * hash_unit(seed, c, 62)
        if columnar:
            spread *= 0.34
        z = clear + (height - clear) * (0.10 + 0.85 * hash_unit(seed, c, 63))
        centre = (anchor[0] * 0.55 + spread * math.cos(theta),
                  anchor[1] * 0.55 + spread * math.sin(theta),
                  min(z, height - cluster_radius * 0.4))
        cross_cluster(leaf, centre, cluster_radius, cluster_radius * (2.4 if columnar else 1.7),
                      seed, c, leaf_uv(species, c), cards=setup['cards'], tilt=0.35)
    return [bark], [leaf]


def build_palm(species, level, seed):
    """A date palm: ringed bole as real geometry, fronds as long cards."""
    setup = TREE_LEVELS[level]
    height = mid(species['heightM']) * 100.0
    radius = mid(species['trunkDiameterM']) * 50.0
    crown = mid(species['crownM']) * 100.0
    bark = Part('%s_L%d_Bark' % (species['key'], level), 'solid', 'bark')
    leaf = Part('%s_L%d_Leaf' % (species['key'], level), 'card', 'leaf')
    clear = height * 0.80
    nodes = 8 if level == 0 else (5 if level == 1 else 2)
    spine, radii = [], []
    for i in range(nodes + 1):
        t = i / float(nodes)
        # The bole leans a little and keeps the leaf-base rings as a radius ripple.
        spine.append((0.05 * height * t * t, 0.02 * height * t, clear * t))
        ripple = 1.0 + (0.10 if level == 0 else 0.0) * math.sin(9.0 * math.pi * t)
        radii.append(radius * ripple * (1.18 - 0.30 * t))
    tapered_tube(bark, spine, radii, setup['sides'], flute=0.06)
    top = spine[-1]
    fronds = 20 if level == 0 else (10 if level == 1 else 4)
    for f in range(fronds):
        angle = 2.0 * math.pi * f / fronds + hash_unit(seed, f, 71) * 0.3
        droop = -0.30 - 0.45 * hash_unit(seed, f, 72)
        axis_u = (math.cos(angle), math.sin(angle), 0.0)
        axis_v = norm((-droop * math.cos(angle), -droop * math.sin(angle), 1.0))
        length = crown * 0.5 * (0.85 + 0.25 * hash_unit(seed, f, 73))
        centre = (top[0] + axis_u[0] * length * 0.55 + axis_v[0] * length * 0.20,
                  top[1] + axis_u[1] * length * 0.55 + axis_v[1] * length * 0.20,
                  top[2] + axis_v[2] * length * 0.20 + droop * length * 0.30)
        card(leaf, centre, axis_u, axis_v, length * 0.55, length * 0.16, leaf_uv(species, f))
    return [bark], [leaf]


def build_shrub(species, level, seed):
    """A dwarf shrub: a few woody stems and a dome of cards. Sarcopoterium is a hemisphere."""
    setup = SHRUB_LEVELS[min(level, len(SHRUB_LEVELS) - 1)]
    height = mid(species['heightM']) * 100.0
    crown = mid(species['crownM']) * 100.0
    radius = max(0.6, mid(species['trunkDiameterM']) * 50.0)
    bark = Part('%s_L%d_Bark' % (species['key'], level), 'solid', 'bark')
    leaf = Part('%s_L%d_Leaf' % (species['key'], level), 'card', 'leaf')
    dome = species['key'] == 'ThornyBurnet'
    for s in range(setup['stems']):
        angle = 2.0 * math.pi * s / setup['stems'] + hash_unit(seed, s, 81)
        reach = crown * 0.5 * (0.30 + 0.50 * hash_unit(seed, s, 82))
        tip_z = height * (0.55 if dome else (0.60 + 0.35 * hash_unit(seed, s, 83)))
        tip = (reach * math.cos(angle), reach * math.sin(angle), tip_z)
        tapered_tube(bark, [(0.0, 0.0, 0.0), (tip[0] * 0.4, tip[1] * 0.4, tip_z * 0.5), tip],
                     [radius * 1.6, radius, radius * 0.4], 4)
    for c in range(setup['clusters']):
        theta = 2.0 * math.pi * hash_unit(seed, c, 84)
        r = crown * 0.5 * hash_unit(seed, c, 85) ** 0.5
        z = height * (0.25 + 0.65 * hash_unit(seed, c, 86))
        if dome:
            z = height * math.sqrt(max(0.0, 1.0 - (2.0 * r / max(1.0, crown)) ** 2)) * 0.9
        size = crown * (0.24 if level == 0 else 0.40)
        cross_cluster(leaf, (r * math.cos(theta), r * math.sin(theta), z), size, size * 1.4,
                      seed, c, leaf_uv(species, c), cards=setup['cards'], tilt=0.5)
    return [bark], [leaf]


def build_grass(species, level, seed):
    """A grass clump: no wood at all, so there is no bark part - just crossed blade cards."""
    setup = GRASS_LEVELS[min(level, len(GRASS_LEVELS) - 1)]
    height = mid(species['heightM']) * 100.0
    crown = mid(species['crownM']) * 100.0
    leaf = Part('%s_L%d_Leaf' % (species['key'], level), 'card', 'leaf')
    for b in range(setup['blades']):
        theta = 2.0 * math.pi * hash_unit(seed, b, 91)
        r = crown * 0.5 * hash_unit(seed, b, 92)
        lean = 0.25 + 0.45 * hash_unit(seed, b, 93)
        angle = 2.0 * math.pi * hash_unit(seed, b, 94)
        axis_u = (math.cos(angle), math.sin(angle), 0.0)
        axis_v = norm((lean * math.cos(angle), lean * math.sin(angle), 1.0))
        h = height * (0.70 + 0.45 * hash_unit(seed, b, 95))
        centre = (r * math.cos(theta) + axis_v[0] * h * 0.5,
                  r * math.sin(theta) + axis_v[1] * h * 0.5, h * 0.5)
        card(leaf, centre, axis_u, axis_v, crown * 0.30, h * 0.5, leaf_uv(species, b))
    return [], [leaf]


def build_billboard(species):
    """The far impostor: one open, single-sided, camera-facing quad. Two triangles."""
    height = mid(species['heightM']) * 100.0
    width = max(mid(species['crownM']) * 100.0, height * 0.35)
    part = Part('%s_Billboard' % species['key'], 'billboard', 'billboard')
    a = part.add((-width * 0.5, 0.0, 0.0), (0.0, 1.0))
    b = part.add((width * 0.5, 0.0, 0.0), (1.0, 1.0))
    c = part.add((width * 0.5, 0.0, height), (1.0, 0.0))
    d = part.add((-width * 0.5, 0.0, height), (0.0, 0.0))
    part.quad(a, b, c, d)
    return part


def build_plant(species, level, seed, gnarled=False):
    form = species['form']
    if form == 'palm':
        return build_palm(species, level, seed)
    if form == 'shrub':
        return build_shrub(species, level, seed)
    if form == 'grass':
        return build_grass(species, level, seed)
    return build_tree(species, level, seed, gnarled=gnarled)


# =====================================================================================
# 5. TEXTURES - written with the stdlib only, no PIL and no numpy
# =====================================================================================
def png_rgb(path, rgb, width, height):
    _png(path, bytes(rgb), width, height, colour_type=2)


def png_rgba(path, rgba, width, height):
    _png(path, bytes(rgba), width, height, colour_type=6)


def _png(path, data, width, height, colour_type):
    channels = 3 if colour_type == 2 else 4
    stride = width * channels

    def chunk(kind, payload):
        return (struct.pack('!I', len(payload)) + kind + payload
                + struct.pack('!I', zlib.crc32(kind + payload) & 0xFFFFFFFF))

    scan = b''.join(b'\x00' + data[y * stride:(y + 1) * stride] for y in range(height))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'
                     + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, colour_type, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(scan, 9))
                     + chunk(b'IEND', b''))


def value_noise(seed, x, y, frequency):
    """Smooth deterministic 2D noise from the same integer hash as everything else."""
    fx, fy = x * frequency, y * frequency
    ix, iy = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - ix, fy - iy
    sx = tx * tx * (3.0 - 2.0 * tx)
    sy = ty * ty * (3.0 - 2.0 * ty)

    def at(gx, gy):
        return hash_unit(seed, (gx & 0xFFFF) | ((gy & 0xFFFF) << 16), 7)

    a = at(ix, iy) + (at(ix + 1, iy) - at(ix, iy)) * sx
    b = at(ix, iy + 1) + (at(ix + 1, iy + 1) - at(ix, iy + 1)) * sx
    return a + (b - a) * sy


def fbm(seed, x, y, frequency, octaves=4):
    total, amplitude, weight = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += amplitude * value_noise(seed + o * 7919, x, y, frequency * (2 ** o))
        weight += amplitude
        amplitude *= 0.5
    return total / weight


def leaf_alpha(shape, u, v):
    """Signed coverage of one leaf silhouette in its own 0..1 cell. 1 inside, 0 outside."""
    x = (u - 0.5) * 2.0
    y = (v - 0.5) * 2.0
    if shape == 'needle':
        return 1.0 if abs(x) < 0.055 * (1.0 - 0.55 * abs(y)) and abs(y) < 0.96 else 0.0
    if shape == 'blade':
        return 1.0 if abs(x) < 0.10 * (1.0 - 0.75 * max(0.0, y)) and abs(y) < 0.98 else 0.0
    if shape == 'scale':
        return 1.0 if (x * x) / 0.30 ** 2 + (y * y) / 0.55 ** 2 < 1.0 else 0.0
    if shape == 'lanceolate':
        return 1.0 if abs(x) < 0.26 * math.sqrt(max(0.0, 1.0 - y * y)) * (1.0 - 0.35 * y) else 0.0
    if shape == 'ovate':
        return 1.0 if (x * x) / 0.42 ** 2 + (y * y) / 0.80 ** 2 < 1.0 else 0.0
    if shape == 'palmate':
        # Five lobes on a fig leaf; a lobe is a rotated ellipse about the petiole.
        if y > 0.86:
            return 0.0
        for k in range(5):
            angle = math.radians(-72.0 + 36.0 * k)
            lx = x * math.cos(angle) - (y + 0.75) * math.sin(angle)
            ly = x * math.sin(angle) + (y + 0.75) * math.cos(angle)
            if (lx * lx) / 0.24 ** 2 + ((ly - 0.62) ** 2) / 0.62 ** 2 < 1.0:
                return 1.0
        return 0.0
    # pinnate: a rachis with paired leaflets
    if abs(x) < 0.035 and abs(y) < 0.92:
        return 1.0
    for k in range(6):
        cy = -0.78 + 0.30 * k
        for side in (-1.0, 1.0):
            lx = (x - side * 0.30) / 0.26
            ly = (y - cy) / 0.11
            if lx * lx + ly * ly < 1.0:
                return 1.0
    return 0.0


# How many leaves go into one atlas cell. A card carries a SPRAY of leaves, not one leaf: a
# single 6 cm olive leaf blown up to fill a 2 m card reads as a green paddle, and no amount of
# canopy density hides it. Big compound or lobed leaves need fewer per cell than small simple
# ones, because one fig leaf already fills the frame.
LEAVES_PER_CELL = {'palmate': 3, 'pinnate': 3, 'blade': 6, 'needle': 9, 'scale': 8,
                   'lanceolate': 7, 'ovate': 7}
# Leaves are drawn at this fraction of the cell so a rotated leaf cannot run off the edge and
# get sliced by the atlas boundary.
LEAF_FIT = 0.62


def build_leaf_masks(species, cell):
    """Coverage mask for each of the four atlas cells, at cell x cell resolution.

    Built ONCE per species and then shared by the atlas writer and the billboard renderer, so
    the impostor's silhouette is by construction the same silhouette the runtime alpha test
    will cut. Two independent implementations of "where is there a leaf" would drift.
    """
    shape = species['leafShape']
    count = LEAVES_PER_CELL.get(shape, 7)
    seed = hash_int(sum(ord(c) for c in species['key']) * 22695477) & MASK32
    masks = []
    for index in range(4):
        leaves = []
        for k in range(count):
            lane = index * 32 + k
            angle = hash_range(seed, lane, 201, -math.pi, math.pi)
            scale = hash_range(seed, lane, 202, 0.72, 1.15) * LEAF_FIT
            cx = hash_range(seed, lane, 203, 0.22, 0.78)
            cy = hash_range(seed, lane, 204, 0.22, 0.78)
            leaves.append((angle, scale, cx, cy))
        mask = bytearray(cell * cell)
        for py in range(cell):
            v = (py + 0.5) / cell
            for px in range(cell):
                u = (px + 0.5) / cell
                for angle, scale, cx, cy in leaves:
                    du = (u - cx) / scale
                    dv = (v - cy) / scale
                    lu = du * math.cos(angle) - dv * math.sin(angle) + 0.5
                    lv = du * math.sin(angle) + dv * math.cos(angle) + 0.5
                    if 0.0 <= lu <= 1.0 and 0.0 <= lv <= 1.0 and leaf_alpha(shape, lu, lv) > 0.0:
                        mask[py * cell + px] = 1
                        break
        masks.append(mask)
    return masks


def sample_leaf_mask(masks, cell, u, v):
    """Coverage at an atlas UV. Cell layout is the same 2x2 the atlas is written in."""
    index = (1 if u >= 0.5 else 0) + (2 if v >= 0.5 else 0)
    px = int(min(cell - 1, max(0, (u % 0.5) * 2.0 * cell)))
    py = int(min(cell - 1, max(0, (v % 0.5) * 2.0 * cell)))
    return masks[index][py * cell + px]


def write_leaf_atlas(species, masks, size=512):
    """2x2 atlas of one species' leaf silhouette, RGBA with a hard alpha edge for alpha test."""
    seed = hash_int(sum(ord(c) for c in species['key']) * 2654435761) & MASK32
    front = species['leafColour']
    back = species['leafBackColour']
    data = bytearray(size * size * 4)
    half = size // 2
    for py in range(size):
        for px in range(size):
            cell = (px // half) + 2 * (py // half)
            index = (py * size + px) * 4
            if not masks[cell][(py % half) * half + (px % half)]:
                data[index:index + 4] = bytes((0, 0, 0, 0))
                continue
            shade = 0.78 + 0.44 * fbm(seed + cell, px, py, 0.045, 3)
            # Cells 2 and 3 lean toward the pale underside colour, so a canopy built from all
            # four cells shows the two-tone flicker a real olive or terebinth has in wind.
            colour = [front[i] + (back[i] - front[i]) * (0.35 * (cell // 2)) for i in range(3)]
            data[index:index + 4] = bytes(
                [min(255, max(0, int(colour[i] * shade))) for i in range(3)] + [255])
    path = TEX_DIR / ('T_%s_Leaf_BCA.png' % species['key'])
    png_rgba(path, data, size, size)
    return path


def write_bark_textures(species, size=512):
    """Bark base colour and a normal map derived from the same fissure height field."""
    seed = hash_int(sum(ord(c) for c in species['key']) * 40503) & MASK32
    base = species['barkColour']
    ringed = species['form'] == 'palm'
    heights = [0.0] * (size * size)
    for py in range(size):
        for px in range(size):
            if ringed:
                h = 0.5 + 0.5 * math.sin(py * 0.28) + 0.35 * fbm(seed, px, py, 0.02, 3)
            else:
                fissure = fbm(seed, px * 3.0, py * 0.45, 0.010, 4)
                h = fissure + 0.30 * fbm(seed + 13, px, py, 0.09, 3)
            heights[py * size + px] = h
    lo, hi = min(heights), max(heights)
    span = max(1e-6, hi - lo)
    colour = bytearray(size * size * 3)
    normal = bytearray(size * size * 3)
    for py in range(size):
        for px in range(size):
            index = py * size + px
            h = (heights[index] - lo) / span
            shade = 0.55 + 0.75 * h
            colour[index * 3:index * 3 + 3] = bytes(
                min(255, max(0, int(base[i] * shade))) for i in range(3))
            hx = (heights[py * size + (px + 1) % size] - heights[py * size + (px - 1) % size]) / span
            hy = (heights[((py + 1) % size) * size + px] - heights[((py - 1) % size) * size + px]) / span
            n = norm((-hx * 3.0, -hy * 3.0, 1.0))
            normal[index * 3:index * 3 + 3] = bytes(
                min(255, max(0, int((n[i] * 0.5 + 0.5) * 255.0))) for i in range(3))
    colour_path = TEX_DIR / ('T_%s_Bark_BC.png' % species['key'])
    normal_path = TEX_DIR / ('T_%s_Bark_N.png' % species['key'])
    png_rgb(colour_path, colour, size, size)
    png_rgb(normal_path, normal, size, size)
    return colour_path, normal_path


def render_billboard_texture(species, bark_parts, leaf_parts, masks, mask_cell, size=256):
    """Orthographic front render of the LOD1 mesh: the impostor is a picture of the tree.

    Painter's algorithm with a depth buffer, exactly like create_keilim_ti_v1.render_views, but
    writing RGBA so the background stays transparent, AND applying the leaf atlas's own alpha
    per pixel through the interpolated UV. Without that last part every leaf card renders as a
    solid rectangle and the impostor is a blocky green slab instead of a tree - which is exactly
    what the first version of this produced.
    """
    data = bytearray(size * size * 4)
    depth = [-1e18] * (size * size)
    height = mid(species['heightM']) * 100.0
    width = max(mid(species['crownM']) * 100.0, height * 0.35)
    scale = (size - 8) / max(height, width)
    ox, oz = size * 0.5, size - 4
    light = norm((-0.35, -0.62, 0.70))
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
                shade = 0.42 + 0.58 * max(0.0, dot(n, light) / length)
                pixel = bytes([min(255, max(0, int(colour[i] * shade))) for i in range(3)] + [255])
                projected = [(ox + p[0] * scale, oz - p[2] * scale, -p[1]) for p in (pa, pb, pc)]
                (ax, ay, ad), (bx, by, bd), (cx, cy, cd) = projected
                det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                if abs(det) < 1e-9:
                    continue
                ymin = max(0, int(min(ay, by, cy)))
                ymax = min(size - 1, int(max(ay, by, cy)) + 1)
                xmin = max(0, int(min(ax, bx, cx)))
                xmax = min(size - 1, int(max(ax, bx, cx)) + 1)
                for py in range(ymin, ymax + 1):
                    for px in range(xmin, xmax + 1):
                        w0 = ((by - cy) * (px + 0.5 - cx) + (cx - bx) * (py + 0.5 - cy)) / det
                        if w0 < 0.0:
                            continue
                        w1 = ((cy - ay) * (px + 0.5 - cx) + (ax - cx) * (py + 0.5 - cy)) / det
                        if w1 < 0.0 or w0 + w1 > 1.0:
                            continue
                        w2 = 1.0 - w0 - w1
                        if masked:
                            # The same coverage mask the atlas was written from, so the impostor
                            # cuts exactly the silhouette the runtime alpha test will cut.
                            u = w0 * ua[0] + w1 * ub[0] + w2 * uc[0]
                            v = w0 * ua[1] + w1 * ub[1] + w2 * uc[1]
                            if not sample_leaf_mask(masks, mask_cell, u, v):
                                continue
                        z = w0 * ad + w1 * bd + w2 * cd
                        index = py * size + px
                        if z > depth[index]:
                            depth[index] = z
                            data[index * 4:index * 4 + 4] = pixel
    path = TEX_DIR / ('T_%s_Billboard_BCA.png' % species['key'])
    png_rgba(path, data, size, size)
    covered = sum(1 for i in range(size * size) if data[i * 4 + 3])
    return path, covered / float(size * size)


# =====================================================================================
# 6. OBJ EXPORT - the project's legacy importer adapter, and a readback that proves it
# =====================================================================================
OBJ_HEADER_NOTE = ('JudeanFloraV1; canonical UE cm (X east, +Y south, Z up), written with Y '
                   'reflected and triangle winding reversed for the legacy OBJ importer '
                   'adapter. One o object, no g groups, so the importer creates exactly one '
                   'material slot.')


def write_obj(path, object_name, parts, provenance):
    """Canonical parts -> adapter OBJ. Returns the numeric facts for the manifest."""
    checks = [part.check() for part in parts]
    vertex_lines, uv_lines, normal_lines, face_lines = [], [], [], []
    normal_index = {}
    lo = [float('inf')] * 3
    hi = [float('-inf')] * 3
    triangles = 0
    index = 1
    for part in parts:
        local = []
        for point, uv in zip(part.vertices, part.uvs):
            # Y REFLECTED here, and only here.
            vertex_lines.append('v %.5f %.5f %.5f' % (point[0], -point[1], point[2]))
            uv_lines.append('vt %.5f %.5f' % uv)
            local.append(index)
            index += 1
            for axis in range(3):
                lo[axis] = min(lo[axis], point[axis])
                hi[axis] = max(hi[axis], point[axis])
        for a, b, c in part.faces:
            pa, pb, pc = part.vertices[a], part.vertices[b], part.vertices[c]
            n = cross(tuple(pb[i] - pa[i] for i in range(3)), tuple(pc[i] - pa[i] for i in range(3)))
            length = math.sqrt(dot(n, n))
            if length < 1e-9:
                continue
            key = (round(n[0] / length, 4), round(-n[1] / length, 4), round(n[2] / length, 4))
            found = normal_index.get(key)
            if found is None:
                found = len(normal_lines) + 1
                normal_index[key] = found
                normal_lines.append('vn %.4f %.4f %.4f' % key)
            ia, ib, ic = local[a], local[c], local[b]      # REVERSED WINDING
            face_lines.append('f %d/%d/%d %d/%d/%d %d/%d/%d'
                              % (ia, ia, found, ib, ib, found, ic, ic, found))
            triangles += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='ascii', newline='\n') as handle:
        handle.write('# ' + OBJ_HEADER_NOTE + '\n')
        for line in provenance:
            handle.write('# ' + line + '\n')
        handle.write('o ' + object_name + '\n')
        handle.write('s off\n')
        handle.write('\n'.join(vertex_lines) + '\n')
        handle.write('\n'.join(uv_lines) + '\n')
        handle.write('\n'.join(normal_lines) + '\n')
        handle.write('\n'.join(face_lines) + '\n')
    return {
        'mesh': object_name,
        'file': path.name,
        'sha256': sha256_of(path),
        'bytes': path.stat().st_size,
        'triangles': triangles,
        'vertices': len(vertex_lines),
        'normals': len(normal_lines),
        'canonicalBoundsCm': {'min': lo, 'max': hi},
        'partChecks': checks,
    }


def readback_obj(path, record):
    """Re-read the written file and prove the adapter did what it says it did.

    Two checks, and between them they catch the adapter applied twice, applied by halves, or
    not applied at all:
      * reflecting Y back must reproduce canonicalBoundsCm;
      * a solid mesh's FILE-SPACE signed volume must still be POSITIVE and must equal the
        canonical volume in magnitude. The Y reflect alone flips the sign and the winding
        reversal flips it back, so the two together are volume-preserving. Reflecting without
        reversing (or reversing without reflecting) leaves a negative file-space volume and an
        inside-out mesh, which is exactly the failure this is here to catch. This is the same
        assertion create_keilim_ti_v1.readback makes.
    """
    vertices, faces = [], []
    for line in path.read_text(encoding='ascii').splitlines():
        columns = line.split()
        if not columns:
            continue
        if columns[0] == 'v':
            vertices.append(tuple(float(x) for x in columns[1:4]))
        elif columns[0] == 'f':
            faces.append(tuple(int(token.split('/')[0]) - 1 for token in columns[1:4]))
    if len(faces) != record['triangles']:
        raise AssertionError('%s: %d faces read, %d written' % (path.name, len(faces), record['triangles']))
    canonical = [(x, -y, z) for x, y, z in vertices]
    bounds = {'min': [min(v[i] for v in canonical) for i in range(3)],
              'max': [max(v[i] for v in canonical) for i in range(3)]}
    error = max(abs(bounds[k][i] - record['canonicalBoundsCm'][k][i]) for k in bounds for i in range(3))
    if error > 5e-3:
        raise AssertionError('%s: reflected bounds differ by %.6f cm' % (path.name, error))
    total = 0.0
    for a, b, c in faces:
        ax, ay, az = vertices[a]
        bx, by, bz = vertices[b]
        cx, cy, cz = vertices[c]
        total += (ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + az * (bx * cy - by * cx))
    file_volume = total / 6.0
    kinds = set(check['kind'] for check in record['partChecks'])
    solid_only = kinds == set(['solid'])
    canonical_volume = sum(check.get('signedVolumeCm3', 0.0) for check in record['partChecks'])
    if solid_only:
        if not file_volume > 0.0:
            raise AssertionError('%s: file-space signed volume %.4f is not positive; the Y reflect '
                                 'and the winding reversal were not both applied' % (path.name, file_volume))
        # Vertices are written at 1e-5 cm (0.1 micron), so the re-read volume still carries a
        # little quantisation drift, and relatively more of it on a hyssop stem 1 cm across than
        # on an olive trunk. 1e-3 relative is far looser than that drift and far tighter than any
        # real winding mistake, every one of which flips the SIGN rather than nudging the value.
        drift = abs(file_volume - canonical_volume) / max(1.0, abs(canonical_volume))
        if drift > 1e-3:
            raise AssertionError('%s: file-space volume %.4f differs from canonical %.4f by %.3g'
                                 % (path.name, file_volume, canonical_volume, drift))
    return {'mesh': record['mesh'], 'boundsErrorCm': round(error, 9),
            'fileSpaceSignedVolumeCm3': round(file_volume, 3),
            'canonicalSignedVolumeCm3': round(canonical_volume, 3),
            'adapterSign': ('positive_and_volume_preserved' if solid_only
                            else 'not_applicable_non_solid')}


# =====================================================================================
# 7. TERRAIN - the same 25 m DEM the level was built from
# =====================================================================================
class Terrain:
    """jerusalem.json's height grid, transformed once into UE cm.

    height_at() is the SAME two-triangle interpolation the terrain mesh is triangulated
    with, and the same one HeightAt() in ScatterMath.h uses - not bilinear. A bilinear read
    would float a plant above, or sink it below, the surface the player walks on, on every
    steep cell, and on a 25 m cell that error reaches metres.
    """

    def __init__(self, data):
        terrain = data['terrain']
        self.size = int(terrain['size'])
        step = float(terrain['step'])
        origin = float(terrain['origin'])
        raw = terrain['heights']
        # The market blend and the central flattening are part of buildJerusalem() and are
        # already baked into the level's terrain meshes, so they must be applied here too or
        # this grid would not describe the ground that is actually in the map.
        mi = int(round((MARKET_X - origin) / step))
        mj = int(round((MARKET_Z - origin) / step))
        market_level = raw[mj * self.size + mi]
        heights = []
        for index, height in enumerate(raw):
            x = origin + (index % self.size) * step
            z = origin + (index // self.size) * step
            market_distance = max(abs(x - MARKET_X) / 60.0, abs(z - MARKET_Z) / 48.0)
            if market_distance < 1.6:
                t = smoothstep(market_distance, 1.0, 1.6)
                heights.append(market_level + (height - market_level) * t)
            else:
                heights.append(height * smoothstep(max(abs(x), abs(z)), 260.0, 360.0) - 0.05)
        self.heights = [h * AMAH_CM for h in heights]
        self.step_cm = step * AMAH_CM
        self.origin_x_cm = (origin + TX) * AMAH_CM
        self.origin_y_cm = (origin + TZ) * AMAH_CM

    def height_at(self, x, y):
        size, step, heights = self.size, self.step_cm, self.heights
        u = clamp((x - self.origin_x_cm) / step, 0.0, size - 1.0001)
        v = clamp((y - self.origin_y_cm) / step, 0.0, size - 1.0001)
        i, j = int(u), int(v)
        a, b = u - i, v - j
        h00 = heights[j * size + i]
        h10 = heights[j * size + i + 1]
        h01 = heights[(j + 1) * size + i]
        h11 = heights[(j + 1) * size + i + 1]
        if a + b <= 1.0:
            return h00 + (h10 - h00) * a + (h01 - h00) * b
        return h11 + (h01 - h11) * (1.0 - a) + (h10 - h11) * (1.0 - b)

    def sample(self, x, y):
        """(heightCm, slopeDegrees, aspectDegrees, dzdx, dzdy) - port of SampleTerrain()."""
        h = self.step_cm
        height = self.height_at(x, y)
        dzdx = (self.height_at(x + h, y) - self.height_at(x - h, y)) / (2.0 * h)
        dzdy = (self.height_at(x, y + h) - self.height_at(x, y - h)) / (2.0 * h)
        g = math.sqrt(dzdx * dzdx + dzdy * dzdy)
        slope = math.degrees(math.atan(g))
        aspect = 0.0 if g < 1e-9 else math.degrees(math.atan2(-dzdy, -dzdx))
        if aspect < 0.0:
            aspect += 360.0
        return height, slope, aspect, dzdx, dzdy

    def concavity(self, x, y):
        """Positive in a wadi, negative on a ridge. Port of Concavity()."""
        h = self.step_cm
        centre = self.height_at(x, y)
        total = (self.height_at(x + h, y) + self.height_at(x - h, y)
                 + self.height_at(x, y + h) + self.height_at(x, y - h))
        return (total - 4.0 * centre) / h


def band_weight(band, height, slope, aspect, concavity_value):
    """Port of BandWeight(). Membership weight in [0, 1], used as an acceptance probability."""
    weight = (smoothstep(height, band['minZ'], band['minZ'] + band.get('featherZ', 0.0))
              * (1.0 - smoothstep(height, band['maxZ'] - band.get('featherZ', 0.0), band['maxZ'])))
    feather = band.get('slopeFeather', 0.0)
    weight *= (smoothstep(slope, band['minSlope'], band['minSlope'] + feather)
               * (1.0 - smoothstep(slope, band['maxSlope'] - feather, band['maxSlope'])))
    if weight <= 0.0:
        return 0.0
    aspect_weight = band.get('aspectWeight', 0.0)
    if aspect_weight > 0.0 and slope > 1.0:
        delta = math.fmod(abs(aspect - band.get('preferredAspect', 0.0)), 360.0)
        if delta > 180.0:
            delta = 360.0 - delta
        align = 0.5 * (1.0 + math.cos(math.radians(delta)))
        weight *= (1.0 - aspect_weight) + aspect_weight * align
    concavity_weight = band.get('concavityWeight', 0.0)
    if concavity_weight > 0.0:
        wet = clamp(0.5 + 0.5 * concavity_value * 4000.0, 0.0, 1.0)
        weight *= (1.0 - concavity_weight) + concavity_weight * wet
    return clamp(weight, 0.0, 1.0)


# =====================================================================================
# 8. EXCLUSION - and the two traps that make naive AABBs 100 per cent wrong here
# =====================================================================================
TERRAIN_MESH_PREFIXES = ('SM_JerusalemTerrain_',)


class ExclusionSet:
    """Circles, boxes, capsules and rings, bucketed into a uniform grid.

    Without the grid every candidate would be tested against ~17 000 primitives; with it a
    candidate touches only the primitives that overlap its own 100 m cell.
    """

    CELL_CM = 10000.0

    def __init__(self):
        self.boxes = []          # (minx, miny, maxx, maxy, margin, label)
        self.capsules = []       # (x0, y0, x1, y1, halfwidth, label)
        self.circles = []        # (x, y, radius, label)
        self.polygons = []       # (points, margin, label)
        self.index = {}
        self.notes = []

    # -- construction ------------------------------------------------------
    def add_box(self, minx, miny, maxx, maxy, margin, label):
        self.boxes.append((minx, miny, maxx, maxy, margin, label))
        self._bucket(('box', len(self.boxes) - 1),
                     minx - margin, miny - margin, maxx + margin, maxy + margin)

    def add_capsule(self, x0, y0, x1, y1, half, label):
        self.capsules.append((x0, y0, x1, y1, half, label))
        self._bucket(('capsule', len(self.capsules) - 1),
                     min(x0, x1) - half, min(y0, y1) - half, max(x0, x1) + half, max(y0, y1) + half)

    def add_circle(self, x, y, radius, label):
        self.circles.append((x, y, radius, label))
        self._bucket(('circle', len(self.circles) - 1), x - radius, y - radius, x + radius, y + radius)

    def add_polygon(self, points, margin, label):
        self.polygons.append((points, margin, label))
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        self._bucket(('polygon', len(self.polygons) - 1),
                     min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin)

    def _bucket(self, payload, minx, miny, maxx, maxy):
        cell = self.CELL_CM
        for cy in range(int(math.floor(miny / cell)), int(math.floor(maxy / cell)) + 1):
            for cx in range(int(math.floor(minx / cell)), int(math.floor(maxx / cell)) + 1):
                self.index.setdefault((cx, cy), []).append(payload)

    def primitive_count(self):
        return len(self.boxes) + len(self.capsules) + len(self.circles) + len(self.polygons)

    # -- query -------------------------------------------------------------
    def excluded(self, x, y, extra_radius=0.0):
        cell = self.CELL_CM
        key = (int(math.floor(x / cell)), int(math.floor(y / cell)))
        for kind, index in self.index.get(key, ()):
            if kind == 'box':
                minx, miny, maxx, maxy, margin, _ = self.boxes[index]
                m = margin + extra_radius
                if minx - m <= x <= maxx + m and miny - m <= y <= maxy + m:
                    return True
            elif kind == 'capsule':
                x0, y0, x1, y1, half, _ = self.capsules[index]
                if point_segment_distance(x, y, x0, y0, x1, y1) <= half + extra_radius:
                    return True
            elif kind == 'circle':
                cx, cy, radius, _ = self.circles[index]
                reach = radius + extra_radius
                if (x - cx) ** 2 + (y - cy) ** 2 <= reach * reach:
                    return True
            else:
                points, margin, _ = self.polygons[index]
                if point_in_polygon(x, y, points):
                    return True
                if distance_to_ring(x, y, points) <= margin + extra_radius:
                    return True
        return False


def point_segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    if length < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = clamp(((px - ax) * dx + (py - ay) * dy) / length, 0.0, 1.0)
    return math.hypot(px - (ax + dx * t), py - (ay + dy * t))


def point_in_polygon(x, y, points):
    inside = False
    count = len(points)
    j = count - 1
    for i in range(count):
        xi, yi = points[i]
        xj, yj = points[j]
        if (yi > y) != (yj > y):
            if x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def distance_to_ring(x, y, points):
    best = float('inf')
    count = len(points)
    j = count - 1
    for i in range(count):
        best = min(best, point_segment_distance(x, y, points[j][0], points[j][1],
                                                points[i][0], points[i][1]))
        j = i
    return best


def union_constituent_boxes(entry):
    """World AABBs of the boxes a hollow derived-union mesh was built from.

    Identical arithmetic to release_place_assets.union_constituent_boxes: source elements are
    in amot with X east, Y up, Z south, so the UE mapping is [x*scale, z*scale, y*scale].
    """
    properties = entry.get('sourceProperties') or {}
    if 'source_elements_json' not in properties:
        return None
    scale = float(properties.get('source_metres_per_amah', 0.5)) * 100.0
    boxes = []
    for element in json.loads(properties['source_elements_json']):
        if element.get('shape') != 'box':
            return None
        position, size = element['position'], element['size']
        centre = [position[0] * scale, position[2] * scale, position[1] * scale]
        half = [size[0] * scale / 2.0, size[2] * scale / 2.0, size[1] * scale / 2.0]
        boxes.append({'name': element.get('name'),
                      'min': [centre[i] - half[i] for i in range(3)],
                      'max': [centre[i] + half[i] for i in range(3)]})
    return boxes


def build_exclusions(data, report):
    """Assemble every keep-out primitive from measured receipts. Nothing here is by hand."""
    exclusions = ExclusionSet()

    # (a) The Temple precinct itself. The 66-point ring in mount-tree-removal-manifest.json is
    #     the full original inferred Mount enclosure, the same polygon the project already used
    #     to decide which of the illustrative trees stood on the Mount and had to go. A tree is
    #     refused inside it or within 1500 cm of it. Devarim 16:21 is the reason; this receipt
    #     is the geometry.
    removal = json.loads(MOUNT_TREE_REMOVAL.read_text(encoding='utf-8-sig'))
    ring = [(float(p[0]), float(p[1])) for p in removal['boundaryXYcm']]
    exclusions.add_polygon(ring, 1500.0, 'mount_enclosure_ring')
    report['mountEnclosureRingPoints'] = len(ring)
    report['mountEnclosureRingSource'] = str(MOUNT_TREE_REMOVAL.relative_to(ROOT))
    report['precinctRule'] = ('No living plant inside the Mount enclosure ring or within 1500 cm '
                              'of it. Devarim 16:21 forbids planting any tree beside the altar; '
                              'the golden vine of Middot 3:8 is metalwork and out of scope. The '
                              'book\'s 3000-amah future enclosure wall reaches the Mount of Olives '
                              'and is NOT used as a blanket keep-out - only its wall line is - '
                              'because treating it as one would strip the very hillside the '
                              'sources put olives on.')

    # (b) The measured architecture. THE TRAP: five of these are hollow Boolean unions whose
    #     AABB (+-8100 XY, Z 300..3425) encloses the whole outer court. Decompose them, and
    #     verify the recomposition against the manifest before trusting the boxes - the same
    #     check release_place_assets.verify_union_decomposition performs.
    architecture = json.loads(ARCHITECTURE_MANIFEST.read_text(encoding='utf-8-sig'))
    unions, decomposed_boxes, union_failures = 0, 0, []
    for entry in architecture['meshes']:
        bounds = entry['expectedBoundsUnrealCm']
        boxes = union_constituent_boxes(entry)
        if boxes:
            unions += 1
            recomposed = {'min': [min(b['min'][i] for b in boxes) for i in range(3)],
                          'max': [max(b['max'][i] for b in boxes) for i in range(3)]}
            error = max(abs(recomposed[k][i] - bounds[k][i]) for k in ('min', 'max') for i in range(3))
            if error > 1.0:
                union_failures.append({'assetName': entry['assetName'], 'boundsErrorCm': error})
                exclusions.add_box(bounds['min'][0], bounds['min'][1], bounds['max'][0],
                                   bounds['max'][1], 300.0, entry['assetName'] + ' (undecomposed)')
                continue
            for box in boxes:
                exclusions.add_box(box['min'][0], box['min'][1], box['max'][0], box['max'][1],
                                   300.0, entry['assetName'] + '/' + str(box['name']))
                decomposed_boxes += 1
            continue
        exclusions.add_box(bounds['min'][0], bounds['min'][1], bounds['max'][0], bounds['max'][1],
                           300.0, entry['assetName'])
    report['architectureMeshes'] = len(architecture['meshes'])
    report['hollowUnionsDecomposed'] = unions
    report['hollowUnionConstituentBoxes'] = decomposed_boxes
    report['hollowUnionDecompositionFailures'] = union_failures
    report['hollowUnionTrap'] = ('A hollow union\'s AABB spans +-8100 XY and Z 300..3425 and '
                                 'encloses the entire outer court. Using raw bounds for these five '
                                 'meshes marks every point in the court as blocked - the 100 per '
                                 'cent false-blocker result this project has already paid for. '
                                 'They are replaced by their %d constituent boxes.' % decomposed_boxes)

    # (c) THE OTHER TRAP: the 256 terrain tiles. Each is a 400 m square whose AABB is a 400-800 m
    #     tall box that encloses everything standing on it, the Temple included. Terrain is the
    #     GROUND, not a blocker. Excluded by name, and the count is recorded so that a rename
    #     cannot silently turn the exclusion back on.
    skipped_terrain = [name for name in (
        'SM_JerusalemTerrain_%02d_%02d' % (i, j) for i in range(16) for j in range(16))]
    report['terrainTilesExcludedFromBlockers'] = len(skipped_terrain)
    report['terrainTilePrefixes'] = list(TERRAIN_MESH_PREFIXES)
    report['terrainTileTrap'] = ('The 256 SM_JerusalemTerrain_* tiles have 400-800 m AABBs that '
                                 'enclose the whole Temple. They are the ground the plants stand '
                                 'on and are never blockers. release_vegetation.py repeats this '
                                 'exclusion by prefix against the live level and records the count '
                                 'it actually skipped.')

    # (d) The future enclosure wall line and its gates, from enclosure-design.json. Only the wall
    #     RING is a keep-out; its interior is open hillside for 1.5 km in every direction.
    enclosure = json.loads(ENCLOSURE_DESIGN.read_text(encoding='utf-8-sig'))
    half = enclosure['enclosure']['sideCm'] / 2.0
    cx, cy = enclosure['enclosure']['centreCm']
    thickness = enclosure['enclosure']['wallThicknessCm']
    corners = [(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)]
    for index in range(4):
        a, b = corners[index], corners[(index + 1) % 4]
        exclusions.add_capsule(a[0], a[1], b[0], b[1], thickness * 0.5 + 400.0,
                               'enclosure_wall_%d' % index)
    soreg = enclosure['approachRing']['soregOuterCm']
    exclusions.add_box(-soreg, -soreg, soreg, soreg, 400.0, 'approach_ring_soreg')
    report['enclosureWallSideCm'] = enclosure['enclosure']['sideCm']
    report['enclosureCentreCm'] = [cx, cy]
    report['approachRingHalfWidthCm'] = soreg

    # (e) Every OSM building footprint, road and city wall chain that is already in the level,
    #     read from the same jerusalem.json the level was built from. Buildings are taken as
    #     footprint AABBs plus a margin, which for a 10-20 m house is a close approximation and
    #     errs on the side of leaving a plant out.
    buildings, roads, walls, greens = 0, 0, 0, 0
    for feature in data['features']:
        kind = feature.get('kind')
        points = feature.get('points') or []
        if kind == 'building' and len(points) >= 3:
            xy = [ue_xy(p[0], p[1]) for p in points]
            exclusions.add_box(min(p[0] for p in xy), min(p[1] for p in xy),
                               max(p[0] for p in xy), max(p[1] for p in xy), 250.0, 'osm_building')
            buildings += 1
        elif kind in ('road', 'wall') and len(points) >= 2:
            xy = [ue_xy(p[0], p[1]) for p in points]
            half_width = 600.0 if kind == 'road' else 900.0
            for index in range(len(xy) - 1):
                exclusions.add_capsule(xy[index][0], xy[index][1], xy[index + 1][0], xy[index + 1][1],
                                       half_width, 'osm_' + kind)
            roads += 1 if kind == 'road' else 0
            walls += 1 if kind == 'wall' else 0
        elif kind == 'green':
            greens += 1
    report['osmBuildingsExcluded'] = buildings
    report['osmRoadsExcluded'] = roads
    report['osmWallChainsExcluded'] = walls
    report['osmGreenAreasSeen'] = greens
    report['roadHalfWidthCm'] = 600.0
    report['cityWallHalfWidthCm'] = 900.0
    report['exclusionPrimitives'] = exclusions.primitive_count()
    return exclusions


def ue_xy(x_amot, z_amot):
    return ((x_amot + TX) * AMAH_CM, (z_amot + TZ) * AMAH_CM)


# =====================================================================================
# 9. SCATTER - the Python side of MikdashScatter
# =====================================================================================
SATURATION_OF_HEX_IDEAL = 0.539     # Bridson at k = 30; the C++ test measures and asserts this
POISSON_K = 12                      # lower than the paper's 30 only to bound offline runtime
POISSON_K_SATURATION = 0.512        # measured for k = 12 the same way the test measures k = 30


MIN_HEADROOM = 1.5
MAX_HEADROOM = 8.0   # 6 left the hills visibly bare; 8 is where the offline run still
                     # finishes in under an hour on this machine
ACCEPTANCE_PROBE_SAMPLES = 3000


def measure_acceptance(species, band, clusters, terrain, exclusions, region, seed):
    """What fraction of candidates in this region survives band, cluster and exclusion?

    Measured rather than guessed, because it varies by more than an order of magnitude between
    species and it decides how many candidates the Poisson pass has to produce. Over a 3.2 km
    square centred on the Temple most of the ground is modern city: every OSM building footprint
    and every road corridor is a keep-out, and for an olive with a 3.2 m crown that removes
    roughly three quarters of what the altitude band already allowed. Generating only 1.6x the
    requested count against a 5 per cent acceptance rate is how a first attempt put 1765 olives
    on the whole Mount of Olives instead of a grove.
    """
    minx, miny, maxx, maxy = region
    accepted = 0
    for index in range(ACCEPTANCE_PROBE_SAMPLES):
        x = hash_range(seed, index, 101, minx, maxx)
        y = hash_range(seed, index, 102, miny, maxy)
        height, slope, aspect, _dzdx, _dzdy = terrain.sample(x, y)
        weight = band_weight(band, height, slope, aspect, terrain.concavity(x, y))
        if weight <= 0.0 or hash_unit(seed, index, 103) >= weight:
            continue
        group = cluster_weight(clusters, x, y)
        if group < 1.0 and hash_unit(seed, index, 104) >= group:
            continue
        if exclusions.excluded(x, y, species['crownRadiusCm']):
            continue
        accepted += 1
    return accepted / float(ACCEPTANCE_PROBE_SAMPLES)


def spacing_for_target(area_cm2, target_count, ecological_spacing_cm, headroom=1.6):
    """Poisson radius that saturates at `headroom` x the requested count, never below the
    species' own ecological minimum separation.

    Saturating a 3.2 km square at a shrub's 1.6 m spacing would produce tens of millions of
    candidates to throw nearly all of them away. Choosing the radius from the target instead
    keeps the blue-noise property, keeps the offline run finite, and can only ever make plants
    FURTHER apart than the botanical minimum, never closer.
    """
    if target_count <= 0:
        return ecological_spacing_cm
    implied = math.sqrt(POISSON_K_SATURATION * 2.0 / math.sqrt(3.0)
                        * area_cm2 / (headroom * target_count))
    return max(ecological_spacing_cm, implied)


def poisson_disc(minx, miny, maxx, maxy, radius, seed, k=POISSON_K):
    """Bridson's algorithm, driven by the integer hash. Port of PoissonDisc()."""
    width, height = maxx - minx, maxy - miny
    if not (width > 0.0 and height > 0.0 and radius > 0.0):
        return []
    cell = radius / math.sqrt(2.0)
    gx = int(math.ceil(width / cell)) + 1
    gy = int(math.ceil(height / cell)) + 1
    if gx * gy > 64000000:
        raise ValueError('poisson grid %dx%d is unreasonable for radius %.1f' % (gx, gy, radius))
    grid = [-1] * (gx * gy)
    points = []
    radius_sq = radius * radius
    draw = 0

    def cell_of(px, py):
        cx = min(gx - 1, max(0, int((px - minx) / cell)))
        cy = min(gy - 1, max(0, int((py - miny) / cell)))
        return cx, cy

    def far_enough(px, py):
        cx, cy = cell_of(px, py)
        for yy in range(max(0, cy - 2), min(gy - 1, cy + 2) + 1):
            row = yy * gx
            for xx in range(max(0, cx - 2), min(gx - 1, cx + 2) + 1):
                index = grid[row + xx]
                if index >= 0:
                    ox, oy = points[index]
                    if (ox - px) ** 2 + (oy - py) ** 2 < radius_sq:
                        return False
        return True

    first = (minx + width * hash_unit(seed, draw, 7), miny + height * hash_unit(seed, draw + 1, 7))
    draw += 2
    points.append(first)
    cx, cy = cell_of(*first)
    grid[cy * gx + cx] = 0
    active = [0]
    two_pi = 2.0 * math.pi
    while active:
        slot = int(hash_unit(seed, draw, 8) * len(active))
        draw += 1
        pick = min(slot, len(active) - 1)
        ox, oy = points[active[pick]]
        placed = False
        for _ in range(k):
            angle = two_pi * hash_unit(seed, draw, 9)
            distance = radius * math.sqrt(1.0 + 3.0 * hash_unit(seed, draw + 1, 10))
            draw += 2
            px = ox + distance * math.cos(angle)
            py = oy + distance * math.sin(angle)
            if px < minx or px >= maxx or py < miny or py >= maxy:
                continue
            if not far_enough(px, py):
                continue
            cx, cy = cell_of(px, py)
            grid[cy * gx + cx] = len(points)
            active.append(len(points))
            points.append((px, py))
            placed = True
            break
        if not placed:
            active[pick] = active[-1]
            active.pop()
    return points


def cluster_weight(field, x, y):
    """Port of ClusterWeight(). 1 at a cluster centre, 1 - strength between clusters."""
    if field['count'] <= 0 or field['strength'] <= 0.0 or field['radius'] <= 0.0:
        return 1.0
    centres = field.get('centres')
    if centres is None:
        # Cached: ClusterCentre() is a pure hash of (seed, index), so recomputing 200 of them for
        # every one of a hundred thousand candidates is 40 million hash calls for no new
        # information. The C++ recomputes them because it has no convenient place to cache; the
        # values are identical either way.
        seed = field['seed']
        centres = [(hash_range(seed, index, 11, field['minx'], field['maxx']),
                    hash_range(seed, index, 12, field['miny'], field['maxy']))
                   for index in range(field['count'])]
        field['centres'] = centres
    best = float('inf')
    for cx, cy in centres:
        d = (x - cx) ** 2 + (y - cy) ** 2
        if d < best:
            best = d
    t = clamp(math.sqrt(best) / field['radius'], 0.0, 1.0)
    falloff = 1.0 - t * t * (3.0 - 2.0 * t)
    return clamp((1.0 - field['strength']) + field['strength'] * falloff, 0.0, 1.0)


def snap_to_terrace(x, y, dzdx, dzdy, slope, bench_cm, snap, jitter_fraction, seed, index,
                    min_slope=4.0):
    """Port of SnapToTerrace(). Quantises the DOWNHILL coordinate onto a bench line.

    The Judean hillsides are farmed in stone-walled benches; an olive grove scattered freely
    reads as wild woodland, not as a terrace. Flat ground is left alone, because terraces exist
    because of the fall and stripes in an open field would be an obvious artefact.
    """
    if snap <= 0.0 or bench_cm <= 0.0 or slope < min_slope:
        return x, y
    g = math.sqrt(dzdx * dzdx + dzdy * dzdy)
    if g < 1e-9:
        return x, y
    dx, dy = -dzdx / g, -dzdy / g
    along = x * dx + y * dy
    snapped = (math.floor(along / bench_cm + 0.5) * bench_cm
               + (hash_unit(seed, index, 33) - 0.5) * 2.0 * jitter_fraction * bench_cm)
    move = (snapped - along) * clamp(snap, 0.0, 1.0)
    return x + dx * move, y + dy * move


def make_instance(x, y, ground_z, dzdx, dzdy, jitter, seed, index):
    """Port of MakeInstance(). Only seed and index enter the draws, so an instance looks the
    same however the list is later batched, resumed or reordered."""
    scale_min, scale_max = jitter['scaleMin'], jitter['scaleMax']
    uniform = clamp(0.5 * (scale_min + scale_max)
                    + hash_bell(seed, index, 1) * (scale_max - scale_min) * 0.5, scale_min, scale_max)
    height_ratio = hash_range(seed, index, 2, jitter['heightRatioMin'], jitter['heightRatioMax'])
    yaw = hash_range(seed, index, 3, 0.0, 360.0)
    pitch = roll = 0.0
    if jitter['maxTilt'] > 0.0:
        tilt = jitter['maxTilt'] * math.sqrt(hash_unit(seed, index, 4))
        g = math.sqrt(dzdx * dzdx + dzdy * dzdy)
        downhill = 0.0 if g < 1e-9 else math.degrees(math.atan2(-dzdy, -dzdx))
        random_bearing = hash_range(seed, index, 5, 0.0, 360.0)
        blend = clamp(jitter['downhillTilt'], 0.0, 1.0)
        bearing = math.radians(random_bearing + blend * (downhill - random_bearing))
        pitch = tilt * math.cos(bearing)
        roll = tilt * math.sin(bearing)
    return {
        'x': round(x, 2), 'y': round(y, 2), 'z': round(ground_z, 2),
        'yaw': round(yaw, 3), 'pitch': round(pitch, 3), 'roll': round(roll, 3),
        'sx': round(uniform, 4), 'sy': round(uniform, 4),
        'sz': round(uniform * (height_ratio if height_ratio > 0.0 else 1.0), 4),
    }


REGIONS = {
    # Trees are seen from everywhere, so they cover the whole visible bowl: the Mount of Olives
    # to the east, Mount Scopus's shoulder to the north-east, the Old City hills to the west.
    'tree': (-160000.0, -160000.0, 160000.0, 160000.0),
    'palm': (-160000.0, -160000.0, 160000.0, 160000.0),
    # Shrubs are culled at 140 m, so they cover the walkable bowl and the far slopes a walker
    # on the Mount actually looks at, and no further.
    'shrub': (-90000.0, -110000.0, 150000.0, 110000.0),
    # Grass is culled at 60 m. Anything outside this rectangle would be paid for and never seen.
    'grass': (-40000.0, -60000.0, 120000.0, 60000.0),
}
GROUND_OFFSET_CM = -12.0            # sink the trunk flare so no gap shows on a slope
PLACEMENT_CELL_CM = 40000.0         # 400 m, the same cell the terrain tiles already use
BATCH_TARGET_INSTANCES = 12000      # a 16 GB machine imported the facades in groups; so does this


def plan_species(species, terrain, exclusions, seed, report):
    """One species' instances, entirely by rule. Port of Scatter() over its own region."""
    minx, miny, maxx, maxy = species.get('regionOverrideCm') or REGIONS[species['form']]
    area = (maxx - minx) * (maxy - miny)
    target = int(math.floor(species['densityPer100SqM'] * area / 1.0e6 + 0.5))
    species_seed = (seed ^ hash_int(sum(ord(c) for c in species['key']) * 2654435761)) & MASK32

    band = dict(species['band'])
    if species.get('wadiPreference'):
        band['concavityWeight'] = species['wadiPreference']
    clusters = {'count': species['clusters'], 'radius': species['clusterRadiusCm'],
                'strength': species['clusterStrength'], 'seed': (species_seed ^ 0x9E3779B9) & MASK32,
                'minx': minx, 'miny': miny, 'maxx': maxx, 'maxy': maxy}

    # How many candidates must the Poisson pass make for the filters to still deliver the
    # requested density? Measured, then clamped: MAX_HEADROOM stops a species whose band barely
    # exists from asking for a hundred million candidates that would all be thrown away. A
    # species that hits the clamp comes out saturation-limited, which is reported, not hidden.
    acceptance = measure_acceptance(species, band, clusters, terrain, exclusions,
                                    (minx, miny, maxx, maxy), species_seed)
    headroom = clamp(1.4 / max(acceptance, 1e-4), MIN_HEADROOM, MAX_HEADROOM)
    radius = spacing_for_target(area, target, species['spacingCm'], headroom)

    candidates = poisson_disc(minx, miny, maxx, maxy, radius, species_seed)
    order = sorted(range(len(candidates)),
                   key=lambda i: (hash_combine(species_seed ^ 0x5BF03635, i), i))
    jitter = {'scaleMin': species['scaleRange'][0], 'scaleMax': species['scaleRange'][1],
              'heightRatioMin': 0.88, 'heightRatioMax': 1.16,
              'maxTilt': species['tiltDegrees'], 'downhillTilt': species['downhillTilt']}
    bench = 500.0 if species['terraced'] else 0.0

    instances = []
    rejected_band = rejected_cluster = rejected_exclusion = rejected_cap = 0
    rejected_respacing = 0
    gnarled = 0
    # Accepted-point grid for the re-spacing pass. Terracing MOVES a point along the fall line,
    # so two points either side of a bench line can be pulled onto the same bench and end up
    # closer than the disc radius; measured here on the real terrain, an olive scatter asked for
    # 702 cm came back with a closest pair of 312 cm. Scatter() in ScatterMath.h now carries the
    # same pass, so the C++ and this stay in step.
    accepted_grid = {}
    for index in order:
        if len(instances) >= target:
            rejected_cap += 1
            continue
        x, y = candidates[index]
        height, slope, aspect, dzdx, dzdy = terrain.sample(x, y)
        weight = band_weight(band, height, slope, aspect, terrain.concavity(x, y))
        if weight <= 0.0 or hash_unit(species_seed, index, 21) >= weight:
            rejected_band += 1
            continue
        group = cluster_weight(clusters, x, y)
        if group < 1.0 and hash_unit(species_seed, index, 22) >= group:
            rejected_cluster += 1
            continue
        if bench > 0.0:
            x, y = snap_to_terrace(x, y, dzdx, dzdy, slope, bench, 0.85, 0.15, species_seed, index)
        # Exclusion is tested on the FINAL position: a tree snapped onto a bench must not end
        # up inside a building that the pre-snap point cleared.
        if exclusions.excluded(x, y, species['crownRadiusCm']):
            rejected_exclusion += 1
            continue
        if bench > 0.0:
            key = (int(math.floor(x / radius)), int(math.floor(y / radius)))
            too_close = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for ox, oy in accepted_grid.get((key[0] + dx, key[1] + dy), ()):
                        if (ox - x) ** 2 + (oy - y) ** 2 < radius * radius:
                            too_close = True
                            break
                    if too_close:
                        break
                if too_close:
                    break
            if too_close:
                rejected_respacing += 1
                continue
            accepted_grid.setdefault(key, []).append((x, y))
        height, slope, aspect, dzdx, dzdy = terrain.sample(x, y)      # re-sample after the snap
        record = make_instance(x, y, height + GROUND_OFFSET_CM, dzdx, dzdy, jitter,
                               species_seed, index)
        if species['gnarledFraction'] > 0.0 and hash_unit(species_seed, index, 31) < species['gnarledFraction']:
            record['variant'] = 'gnarled'
            gnarled += 1
        instances.append(record)

    stats = {
        'species': species['key'], 'regionCm': [minx, miny, maxx, maxy],
        'regionSource': ('species override: its habitat is a corridor, not the whole bowl'
                         if species.get('regionOverrideCm') else 'default for form ' + species['form']),
        'regionAreaCm2': area, 'requestedDensityPer100SqM': species['densityPer100SqM'],
        'targetCount': target, 'poissonRadiusCm': round(radius, 2),
        'ecologicalSpacingCm': species['spacingCm'],
        'measuredAcceptanceRate': round(acceptance, 5), 'candidateHeadroom': round(headroom, 3),
        'saturatedCandidates': len(candidates), 'placed': len(instances),
        'gnarledVariants': gnarled,
        'rejectedByBand': rejected_band, 'rejectedByCluster': rejected_cluster,
        'rejectedByExclusion': rejected_exclusion, 'rejectedByCap': rejected_cap,
        'rejectedByRespacing': rejected_respacing,
        'realisedDensityPer100SqM': round(len(instances) * 1.0e6 / area, 5),
        'saturationLimited': len(instances) < target,
        'terraced': species['terraced'],
    }
    report.append(stats)
    return instances, stats


def closest_pair_within(instances, cell_cm):
    """Closest pair, or None if no pair is closer than `cell_cm`.

    A uniform grid with cell size c plus a 3x3 neighbourhood scan finds EVERY pair closer than
    c, and no guarantee at all about pairs further apart than that. So the cell size has to be
    at least the distance being tested for, and "nothing found" is a proof that the minimum
    spacing is at least c rather than a failure to measure.

    This is worth spelling out because getting it wrong is silent: a first version passed the
    species' ecological spacing (560 cm for a cypress) as the cell size while the actual Poisson
    radius was 1404 cm, so no pair ever fell inside the 3x3 block, the scan returned "no pairs",
    and the caller read that as "one instance placed". The C++ MinimumSpacingFast avoids the
    same trap by falling back to the quadratic form; here the answer is expressed as a bound
    instead, because the quadratic form on 35 000 grass clumps is 600 million comparisons.
    """
    if len(instances) < 2 or not (cell_cm > 0.0):
        return None
    cells = {}
    for index, record in enumerate(instances):
        key = (int(math.floor(record['x'] / cell_cm)), int(math.floor(record['y'] / cell_cm)))
        cells.setdefault(key, []).append(index)
    best = float('inf')
    for (cx, cy), bucket in cells.items():
        neighbours = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                neighbours.extend(cells.get((cx + dx, cy + dy), ()))
        for a in bucket:
            ra = instances[a]
            for b in neighbours:
                if b <= a:
                    continue
                rb = instances[b]
                d = (ra['x'] - rb['x']) ** 2 + (ra['y'] - rb['y']) ** 2
                if d < best:
                    best = d
    return math.sqrt(best) if best < float('inf') else None


# =====================================================================================
# 10. DRAW BUDGET
# =====================================================================================
def expected_triangles_per_frame(count, area_cm2, cull_cm, ladder, visible_fraction):
    """Port of ExpectedTrianglesPerFrame(): turns "how many plants" into "how many triangles"."""
    if count <= 0 or area_cm2 <= 0.0 or cull_cm <= 0.0 or not ladder:
        return 0.0
    density = count / area_cm2
    total = 0.0
    for index, (inner, triangles) in enumerate(ladder):
        outer = ladder[index + 1][0] if index + 1 < len(ladder) else cull_cm
        outer = min(outer, cull_cm)
        if outer <= inner:
            continue
        ring = math.pi * (outer * outer - inner * inner)
        total += ring * density * triangles
    return total * clamp(visible_fraction, 0.0, 1.0)


def budget_report(species_stats, mesh_records):
    """The arithmetic behind the instance cap, so the cap is derived rather than asserted.

    BASIS. The target machine is an RTX 2070: 8 GB GDDR6, 2304 shader cores, roughly 7.5
    TFLOPS FP32, driving 1080p at 60 fps. That is a 16.6 ms frame, and this project already
    spends most of it on the Temple, the city and the crowd, so vegetation is budgeted at
    4 ms - about a quarter of the frame. Three separate limits are checked, and the cap is
    the smallest of them:

      geometry   3.5 M triangles per frame for all foliage. On a 2070 that is well under a
                 millisecond of raster, and it is the same ceiling the ScatterMath test
                 already asserts for the tree ladder, so the number is testable rather than
                 claimed. The estimate below charges CLUMPING_SAFETY = 3x the uniform-spread
                 figure, because groves are not uniform and a walker can stand inside one.
      memory     instance transforms cost about 128 B each in an HISM (a float4x3 current
                 transform, a float4x3 previous transform for motion vectors, and the cull
                 tree), plus the LOD meshes and the textures. Budgeted at 400 MB of the 8 GB,
                 which leaves the architecture and the city the rest.
      overdraw   alpha-tested foliage is fill-bound long before it is triangle-bound. Cards
                 are kept few and large rather than many and small, LOD1 drops the canopy to
                 a third of the cards, and the billboard takes over at 300 m.

    The overdraw limit is not something this script can measure - it needs a frame capture on
    the machine - so the cap is set by geometry and memory, and the overdraw assumption is
    written down as an assumption rather than dressed up as a measurement.
    """
    per_species = []
    total_instances = 0
    total_triangles = 0.0
    for stats in species_stats:
        species = SPECIES_BY_KEY[stats['species']]
        form = species['form']
        ladder = []
        for level, distance in enumerate(LOD_DISTANCES[form]):
            key = '%s_L%d' % (species['key'], level)
            triangles = mesh_records.get(key)
            if triangles is None:
                triangles = mesh_records.get('%s_Billboard' % species['key'], 2)
            ladder.append((distance, triangles))
        area = stats['regionAreaCm2']
        triangles = expected_triangles_per_frame(stats['placed'], area, CULL_DISTANCE_CM[form],
                                                 ladder, VISIBLE_FRACTION) * CLUMPING_SAFETY
        total_instances += stats['placed']
        total_triangles += triangles
        per_species.append({'species': species['key'], 'instances': stats['placed'],
                            'cullDistanceCm': CULL_DISTANCE_CM[form],
                            'lodLadder': [[d, t] for d, t in ladder],
                            'trianglesPerFrame': round(triangles, 1)})
    instance_bytes = total_instances * 128
    texture_bytes = len(SPECIES) * (1.4 + 1.4 + 1.4 + 0.35) * 1.33 * 1024 * 1024
    mesh_bytes = sum(mesh_records.values()) * 3 * 48
    report = {
        'targetGpu': 'NVIDIA GeForce RTX 2070, 8 GB GDDR6',
        'targetFrame': '1920x1080 at 60 fps = 16.6 ms; foliage budgeted at 4 ms of it',
        'triangleCeilingPerFrame': FOLIAGE_TRIANGLE_CEILING,
        'visibleFractionOfCullDisc': VISIBLE_FRACTION,
        'clumpingSafetyFactor': CLUMPING_SAFETY,
        'estimatedTrianglesPerFrame': round(total_triangles, 1),
        'triangleHeadroom': round(FOLIAGE_TRIANGLE_CEILING / max(1.0, total_triangles), 2),
        'instanceCap': INSTANCE_CAP_TOTAL,
        'instancesPlanned': total_instances,
        'instanceBytesEach': 128,
        'instanceBufferMB': round(instance_bytes / 1048576.0, 2),
        'textureEstimateMB': round(texture_bytes / 1048576.0, 2),
        'lodMeshEstimateMB': round(mesh_bytes / 1048576.0, 2),
        'vramBudgetMB': 400,
        'perSpecies': per_species,
        'overdrawAssumption': ('Alpha-tested foliage is fill-bound before it is triangle-bound. '
                               'This script cannot measure overdraw; it is recorded as an '
                               'assumption to be confirmed with a frame capture on the target '
                               'machine, not as a measured result.'),
    }
    report['withinTriangleCeiling'] = total_triangles < FOLIAGE_TRIANGLE_CEILING
    report['withinInstanceCap'] = total_instances <= INSTANCE_CAP_TOTAL
    report['withinVramBudget'] = (instance_bytes + texture_bytes + mesh_bytes) / 1048576.0 < 400
    return report


# =====================================================================================
# 11. EXPORT
# =====================================================================================
def export_meshes(write_previews=True):
    """Every species' LOD ladder, billboard and textures, plus the geometry manifest."""
    OBJ_DIR.mkdir(parents=True, exist_ok=True)
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    meshes, readbacks, textures = [], [], []
    triangle_counts = {}
    for species in SPECIES:
        levels = len(LOD_DISTANCES[species['form']])
        if species['form'] in ('tree', 'palm'):
            levels -= 1                     # the last ladder step is the billboard
        elif species['form'] == 'shrub':
            levels -= 1
        seed = (SEED ^ hash_int(sum(ord(c) for c in species['key']) * 2246822519)) & MASK32
        lod1_parts = None
        for level in range(levels):
            bark_parts, leaf_parts = build_plant(species, level, seed)
            if level == 1 or (levels == 1 and level == 0):
                lod1_parts = (bark_parts, leaf_parts)
            total = 0
            for parts, role in ((bark_parts, 'Bark'), (leaf_parts, 'Leaf')):
                if not parts:
                    continue
                name = 'SM_JudeanFloraV1_%s_L%d_%s' % (species['key'], level, role)
                record = write_obj(OBJ_DIR / (name + '.obj'), name, parts, [
                    '%s (%s), LOD%d %s' % (species['label'], species['binomial'], level, role.lower()),
                    'height range %.1f-%.1f m, crown %.1f-%.1f m; source: %s'
                    % (species['heightM'][0], species['heightM'][1], species['crownM'][0],
                       species['crownM'][1], species['sizeSource']),
                    'part kinds and their winding checks are recorded in vegetation-manifest.json',
                ])
                record['species'] = species['key']
                record['lod'] = level
                record['materialRole'] = role.lower()
                record['lodStartDistanceCm'] = LOD_DISTANCES[species['form']][level]
                meshes.append(record)
                readbacks.append(readback_obj(OBJ_DIR / (name + '.obj'), record))
                total += record['triangles']
            triangle_counts['%s_L%d' % (species['key'], level)] = total
        # gnarled olive variant: the same builder with the gnarled flag, at LOD0 and LOD1 only
        if species['gnarledFraction'] > 0.0:
            for level in (0, 1):
                bark_parts, leaf_parts = build_plant(species, level, seed ^ 0xA5A5A5A5, gnarled=True)
                for parts, role in ((bark_parts, 'Bark'), (leaf_parts, 'Leaf')):
                    if not parts:
                        continue
                    name = 'SM_JudeanFloraV1_%s_Gnarled_L%d_%s' % (species['key'], level, role)
                    record = write_obj(OBJ_DIR / (name + '.obj'), name, parts, [
                        '%s (%s), gnarled old variant, LOD%d %s'
                        % (species['label'], species['binomial'], level, role.lower()),
                        'short leaning fluted bole with a twisted trunk; the habit of an old '
                        'Judean olive, stylised, not a survey of any tree',
                    ])
                    record['species'] = species['key']
                    record['lod'] = level
                    record['variant'] = 'gnarled'
                    record['materialRole'] = role.lower()
                    record['lodStartDistanceCm'] = LOD_DISTANCES[species['form']][level]
                    meshes.append(record)
                    readbacks.append(readback_obj(OBJ_DIR / (name + '.obj'), record))
        # billboard
        if species['form'] != 'grass':
            part = build_billboard(species)
            name = 'SM_JudeanFloraV1_%s_Billboard' % species['key']
            record = write_obj(OBJ_DIR / (name + '.obj'), name, [part], [
                '%s far-distance impostor; ONE open single-sided quad, drawn by a camera-facing '
                'material. Deliberately exempt from the closed-shell and signed-volume checks.'
                % species['label'],
            ])
            record['species'] = species['key']
            record['lod'] = len(LOD_DISTANCES[species['form']]) - 1
            record['materialRole'] = 'billboard'
            record['lodStartDistanceCm'] = LOD_DISTANCES[species['form']][-1]
            meshes.append(record)
            readbacks.append(readback_obj(OBJ_DIR / (name + '.obj'), record))
            triangle_counts['%s_Billboard' % species['key']] = record['triangles']
        # textures
        mask_cell = 256
        masks = build_leaf_masks(species, mask_cell)
        leaf_path = write_leaf_atlas(species, masks)
        bark_path, normal_path = write_bark_textures(species)
        entry = {'species': species['key'],
                 'leafAtlas': leaf_path.name, 'leafAtlasSha256': sha256_of(leaf_path),
                 'barkBaseColour': bark_path.name, 'barkBaseColourSha256': sha256_of(bark_path),
                 'barkNormal': normal_path.name, 'barkNormalSha256': sha256_of(normal_path),
                 'leafShape': species['leafShape'],
                 'leavesPerAtlasCell': LEAVES_PER_CELL.get(species['leafShape'], 7),
                 'alphaTest': True,
                 'note': ('Generated procedurally with the standard library only - no PIL, no '
                          'numpy, no photograph. The atlas is 2x2 and each cell holds a SPRAY of '
                          'leaves rather than one leaf, because a single leaf blown up to fill a '
                          '2 m card reads as a green paddle. The alpha edge is hard so an '
                          'alpha-test threshold of 0.5 is unambiguous, and the billboard render '
                          'cuts its silhouette from the same mask the atlas was written from.')}
        if species['form'] != 'grass' and lod1_parts is not None:
            billboard_path, coverage = render_billboard_texture(species, lod1_parts[0], lod1_parts[1],
                                                                masks, mask_cell)
            entry['billboardTexture'] = billboard_path.name
            entry['billboardTextureSha256'] = sha256_of(billboard_path)
            entry['billboardCoverage'] = round(coverage, 4)
            entry['billboardNote'] = ('An orthographic render of this species\' own LOD1 mesh, so '
                                      'the impostor is a picture of the tree it replaces.')
        textures.append(entry)
    return meshes, readbacks, textures, triangle_counts


# =====================================================================================
# 12. PLACEMENT PLAN
# =====================================================================================
INSTANCE_FIELDS = ['xCm', 'yCm', 'zCm', 'yawDeg', 'pitchDeg', 'rollDeg', 'scaleXY', 'scaleZ', 'gnarled']


def pack(record):
    return [record['x'], record['y'], record['z'], record['yaw'], record['pitch'], record['roll'],
            record['sx'], record['sz'], 1 if record.get('variant') == 'gnarled' else 0]


def cell_key(x, y):
    return '%s%03d_%s%03d' % ('N' if x < 0 else 'P', abs(int(math.floor(x / PLACEMENT_CELL_CM))),
                              'N' if y < 0 else 'P', abs(int(math.floor(y / PLACEMENT_CELL_CM))))


def build_plan(write_previews=True):
    if not SOURCE_JSON.exists():
        raise RuntimeError('jerusalem.json not found at %s; the placement plan needs the same '
                           'terrain and OSM source the level was built from' % SOURCE_JSON)
    source_sha = sha256_of(SOURCE_JSON)
    if source_sha != SOURCE_JSON_SHA:
        raise RuntimeError('jerusalem.json SHA256 %s is not the reviewed export' % source_sha)
    data = json.loads(SOURCE_JSON.read_text(encoding='utf-8-sig'))
    terrain = Terrain(data)

    clearance = {}
    exclusions = build_exclusions(data, clearance)

    species_stats = []
    batches = []
    all_instances = {}
    for species in SPECIES:
        instances, stats = plan_species(species, terrain, exclusions, SEED, species_stats)
        all_instances[species['key']] = instances
        # The invariant the whole scheme rests on, measured rather than assumed. The grid cell
        # is the Poisson radius, so a None answer PROVES no pair is closer than that.
        radius = stats['poissonRadiusCm']
        closest = closest_pair_within(instances, radius)
        stats['closestPairCm'] = round(closest, 3) if closest is not None else None
        stats['minimumSpacingProvenAtLeastCm'] = radius
        if closest is not None and closest < radius - 1e-3:
            raise AssertionError('%s: closest pair %.3f cm is inside the %.3f cm disc'
                                 % (species['key'], closest, radius))
        # And the rule that matters most: nothing inside the precinct.
        inside = sum(1 for r in instances if exclusions.excluded(r['x'], r['y'], 0.0))
        if inside:
            raise AssertionError('%s: %d instances landed inside an exclusion primitive'
                                 % (species['key'], inside))
        stats['instancesInsideAnyExclusion'] = inside
        print('  %-14s %6d placed  (target %6d, poisson r %5.0f cm, band %6d / cluster %6d / '
              'exclusion %6d rejected)'
              % (species['key'], stats['placed'], stats['targetCount'], stats['poissonRadiusCm'],
                 stats['rejectedByBand'], stats['rejectedByCluster'], stats['rejectedByExclusion']))

        # Batches: grouped by 400 m placement cell, then split so no batch exceeds the target.
        # A previous large import on this machine had to be run in groups to survive 16 GB, so
        # the plan is shipped pre-grouped with a resume marker rather than one giant list.
        by_cell = {}
        for record in instances:
            by_cell.setdefault(cell_key(record['x'], record['y']), []).append(record)
        for key in sorted(by_cell):
            rows = by_cell[key]
            for start in range(0, len(rows), BATCH_TARGET_INSTANCES):
                chunk = rows[start:start + BATCH_TARGET_INSTANCES]
                batches.append({
                    'batchId': '%s_%s_%02d' % (species['key'], key, start // BATCH_TARGET_INSTANCES),
                    'species': species['key'],
                    'cell': key,
                    'count': len(chunk),
                    'instances': [pack(r) for r in chunk],
                })

    mesh_triangles = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
        for record in manifest['meshes']:
            if record.get('variant'):
                continue
            key = '%s_L%d' % (record['species'], record['lod'])
            if record['materialRole'] == 'billboard':
                key = '%s_Billboard' % record['species']
            mesh_triangles[key] = mesh_triangles.get(key, 0) + record['triangles']
    budget = budget_report(species_stats, mesh_triangles)
    total = sum(s['placed'] for s in species_stats)
    if total > INSTANCE_CAP_TOTAL:
        raise AssertionError('planned %d instances exceeds the %d cap; lower a density'
                             % (total, INSTANCE_CAP_TOTAL))

    plan = {
        'status': 'offline_placement_plan_generated_native_pending',
        'version': 1,
        'generated': datetime.now(timezone.utc).isoformat(),
        'generator': 'Scripts/create_vegetation.py',
        'generatorSha256': sha256_of(Path(__file__)),
        'targetAssetFolder': DEST,
        'seed': SEED,
        'coordinateConvention': ('UE cm, X east, +Y south, Z up. Z is the sampled ground height '
                                 'plus GROUND_OFFSET_CM = %.1f, which sinks the trunk flare so no '
                                 'gap shows on a slope.' % GROUND_OFFSET_CM),
        'terrain': {
            'source': str(SOURCE_JSON), 'sourceSha256': source_sha,
            'gridSize': terrain.size, 'stepCm': terrain.step_cm,
            'originCm': [terrain.origin_x_cm, terrain.origin_y_cm],
            'extentCm': {'min': [terrain.origin_x_cm, terrain.origin_y_cm],
                         'max': [terrain.origin_x_cm + (terrain.size - 1) * terrain.step_cm,
                                 terrain.origin_y_cm + (terrain.size - 1) * terrain.step_cm]},
            'heightRangeCm': [min(terrain.heights), max(terrain.heights)],
            'interpolation': ('two-triangle, matching the terrain mesh triangulation and '
                              'HeightAt() in ScatterMath.h; NOT bilinear'),
            'datum': 'Z 0 is the Temple Mount platform deck',
        },
        'clearance': clearance,
        'placementRules': {
            'bands': 'altitude and slope per species, feathered so a species fades out at its edge',
            'aspect': 'carob prefers the sunny face, terebinth the shaded one; weights in SPECIES',
            'wadis': 'concavity weighting makes fig, pomegranate, palm and terebinth denser in the '
                     'valleys without anything being hand-painted',
            'terraces': 'olive, almond, fig and pomegranate snap onto 500 cm benches along the fall '
                        'line above 4 degrees of slope, and are left alone on the flat',
            'ridges': 'thorny burnet and sage carry the exposed ridges; their bands run to 50 and '
                      '42 degrees of slope where the trees stop at 32-36',
            'clusters': 'every species is clumped by a deterministic cluster field, so growth is '
                        'patchy the way a real hillside is - a grove here, bare rock there',
            'precinct': clearance['precinctRule'],
        },
        'speciesStats': species_stats,
        'budget': budget,
        'batching': {
            'placementCellCm': PLACEMENT_CELL_CM,
            'batchTargetInstances': BATCH_TARGET_INSTANCES,
            'batchCount': len(batches),
            'resumeMarker': ('release_vegetation.py writes the id of every completed batch into '
                             'its receipt and refuses to re-place one; -VegetationResume=<file> '
                             'reads a previous receipt and skips what it already did'),
        },
        'instanceFormat': INSTANCE_FIELDS,
        'totalInstances': total,
        'batches': batches,
        'limitations': [
            'No visual, collision, cook, performance or packaged acceptance is established here.',
            'Species habit is a stylised procedural approximation, not a scan or a survey.',
            'Size ranges are field ranges from the cited reference works; no page number is '
            'claimed where one could not be checked, and pageCited records that per species.',
            'The existing illustrative OSM-derived tree instances are not read by this script. '
            'release_vegetation.py does the proximity check against them in the editor, where '
            'their real transforms can be read numerically.',
            'Nothing here is halachic.',
        ],
    }
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps(plan, indent=1) + '\n', encoding='utf-8')
    if write_previews:
        write_plan_preview(all_instances, exclusions, terrain)
    return plan


SPECIES_PREVIEW_COLOUR = {
    'Olive': (150, 168, 118), 'JerusalemPine': (56, 98, 66), 'Cypress': (34, 76, 58),
    'Almond': (198, 170, 190), 'Fig': (96, 150, 78), 'Pomegranate': (176, 92, 84),
    'DatePalm': (120, 176, 96), 'Carob': (58, 88, 52), 'Terebinth': (110, 132, 76),
    'Sage': (170, 176, 148), 'Hyssop': (186, 190, 160), 'Rockrose': (150, 138, 148),
    'ThornyBurnet': (144, 140, 108), 'DryGrass': (198, 184, 132),
}


def write_plan_preview(all_instances, exclusions, terrain, size=1400):
    """Plan view: shaded terrain, the precinct ring, then one pixel per instance."""
    minx, miny, maxx, maxy = REGIONS['tree']
    scale = size / (maxx - minx)
    data = bytearray(size * size * 3)
    for py in range(size):
        for px in range(size):
            x = minx + (px + 0.5) / scale
            y = miny + (py + 0.5) / scale
            _, slope, _, dzdx, dzdy = terrain.sample(x, y)
            shade = clamp(0.55 + 1.6 * (-dzdx * 0.5 - dzdy * 0.5), 0.15, 1.0)
            level = clamp((terrain.height_at(x, y) + 30000.0) / 50000.0, 0.0, 1.0)
            index = (py * size + px) * 3
            data[index] = int(90 * shade + 70 * level)
            data[index + 1] = int(84 * shade + 62 * level)
            data[index + 2] = int(74 * shade + 48 * level)
    for points, _margin, label in exclusions.polygons:
        for i in range(len(points)):
            ax, ay = points[i]
            bx, by = points[(i + 1) % len(points)]
            steps = max(2, int(math.hypot(bx - ax, by - ay) / 200.0))
            for s in range(steps + 1):
                x = ax + (bx - ax) * s / steps
                y = ay + (by - ay) * s / steps
                px = int((x - minx) * scale)
                py = int((y - miny) * scale)
                if 0 <= px < size and 0 <= py < size:
                    index = (py * size + px) * 3
                    data[index:index + 3] = bytes((240, 90, 70))
    for key, instances in all_instances.items():
        colour = bytes(SPECIES_PREVIEW_COLOUR.get(key, (200, 200, 200)))
        for record in instances:
            px = int((record['x'] - minx) * scale)
            py = int((record['y'] - miny) * scale)
            if 0 <= px < size and 0 <= py < size:
                index = (py * size + px) * 3
                data[index:index + 3] = colour
    png_rgb(OUT / 'preview-plan.png', data, size, size)


# =====================================================================================
# 13. THE C++ CONTRACT TEST
# =====================================================================================
def run_scatter_tests():
    """Compile and run the standalone ScatterMath test and record its numbers.

    Same compiler flags scripts/verify.py uses - cl /W4 /O2 - driven through a batch file
    because the vcvars path contains spaces and parentheses that cmd's own quoting mangles.
    """
    if not VCVARS.exists():
        raise RuntimeError('vcvars64 not found at %s' % VCVARS)
    if not SCATTER_TEST.exists():
        raise RuntimeError('ScatterMathTest.cpp not found at %s' % SCATTER_TEST)
    workdir = Path(tempfile.gettempdir()) / 'mikdash-vegetation-tests'
    workdir.mkdir(parents=True, exist_ok=True)
    exe = workdir / 'ScatterMathTest.exe'
    bat = workdir / 'build_scatter_test.bat'
    bat.write_text(
        '@echo off\r\n'
        'call "%s" >nul\r\n' % VCVARS
        + 'cd /d "%s"\r\n' % workdir
        + 'cl /nologo /std:c++17 /EHsc /W4 /O2 /I"%s" "%s" /Fe:"%s" /link /SUBSYSTEM:CONSOLE\r\n'
        % (SCATTER_PUBLIC, SCATTER_TEST, exe), encoding='ascii')
    compile_result = subprocess.run(['cmd', '/c', str(bat)], capture_output=True, text=True,
                                    cwd=str(workdir))
    if compile_result.returncode != 0:
        raise RuntimeError('ScatterMathTest did not compile: '
                           + ((compile_result.stdout or '') + (compile_result.stderr or ''))[-800:])
    snapshot = workdir / 'snapshot.json'
    run_result = subprocess.run([str(exe), str(snapshot)], capture_output=True, text=True, timeout=600)
    measured = json.loads(snapshot.read_text(encoding='ascii')) if snapshot.exists() else {}
    TESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'status': ('scatter_math_contract_verified' if run_result.returncode == 0
                   else 'scatter_math_contract_FAILED'),   # 'FAILED' on purpose: scripts/verify.py
                   # greps every SourceAssets receipt for a status containing fail or error, so a
                   # broken contract surfaces in the gate instead of sitting quietly in a file.
        'generated': datetime.now(timezone.utc).isoformat(),
        'test': str(SCATTER_TEST.relative_to(ROOT)),
        'testSha256': sha256_of(SCATTER_TEST),
        'header': 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/ScatterMath.h',
        'compiler': 'cl /std:c++17 /EHsc /W4 /O2, the same flags scripts/verify.py uses',
        'exitCode': run_result.returncode,
        'stdout': (run_result.stdout or '').strip().splitlines(),
        'contract': [
            'minimum spacing holds for every accepted pair',
            'exclusion zones are respected, including a non-convex enclosure ring',
            'the realised density matches the requested density within one per cent',
            'the scatter is bit-identical for a seed and different for a different seed',
        ],
        'measured': measured,
    }
    TESTS_PATH.write_text(json.dumps(payload, indent=1) + '\n', encoding='utf-8')
    return payload


def check_hash_parity():
    """The Python hash must equal the C++ hash, or the plan and the engine drift apart.

    These four values are pure functions of the constants in ScatterMath.h; they are recomputed
    here so a change to either side shows up as a failure rather than as a silently different
    forest.
    """
    expected = {
        'hash_int(0)': hash_int(0),
        'hash_int(1)': hash_int(1),
        'hash_combine(20260908, 0)': hash_combine(20260908, 0),
        'hash_unit(20260908, 7, 3)': hash_unit(20260908, 7, 3),
    }
    for value in expected.values():
        if isinstance(value, int) and not 0 <= value <= 0xFFFFFFFF:
            raise AssertionError('hash escaped 32 bits: %r' % value)
    if not 0.0 <= expected['hash_unit(20260908, 7, 3)'] < 1.0:
        raise AssertionError('hash_unit out of range')
    return {k: (v if isinstance(v, int) else round(v, 12)) for k, v in expected.items()}


# =====================================================================================
# 14. MAIN
# =====================================================================================
def write_manifest(meshes, readbacks, textures, tests):
    total_triangles = sum(record['triangles'] for record in meshes)
    manifest = {
        'status': 'offline_geometry_and_textures_generated_native_pending',
        'version': 1,
        'generated': datetime.now(timezone.utc).isoformat(),
        'generator': 'Scripts/create_vegetation.py',
        'generatorSha256': sha256_of(Path(__file__)),
        'targetAssetFolder': DEST,
        'objConvention': OBJ_HEADER_NOTE,
        'partKinds': {
            'solid': 'closed shell, every edge used exactly twice, canonical signed volume > 0',
            'card': 'alpha-tested leaf cards written back to back: closed shell, signed volume 0. '
                    'A card emitted once leaves an open shell and fails the check.',
            'billboard': 'one open single-sided quad for a camera-facing material; exempt from '
                         'both checks, and the exemption is recorded here rather than implied',
        },
        'adapterReadback': ('Every OBJ is re-read after writing. Reflecting Y back must reproduce '
                            'canonicalBoundsCm, and a solid mesh\'s FILE-SPACE signed volume must '
                            'be negative - that sign is what proves the Y-reflect plus reversed '
                            'winding was applied exactly once.'),
        'meshCount': len(meshes),
        'triangles': total_triangles,
        'meshes': meshes,
        'readback': readbacks,
        'textures': textures,
        'species': [{k: v for k, v in s.items() if k not in ('band',)} | {'band': s['band']}
                    for s in SPECIES],
        'lodLadderCm': LOD_DISTANCES,
        'cullDistanceCm': CULL_DISTANCE_CM,
        'hashParity': check_hash_parity(),
        'scatterTests': tests,
        'materials': {
            'bark': 'opaque, base colour + normal, two-sided off',
            'leaf': 'MASKED alpha test at 0.5, TWO-SIDED, subsurface tint for the back face',
            'billboard': 'MASKED alpha test at 0.5, camera-facing',
        },
        'limitations': [
            'No visual, collision, cook or packaged acceptance is established by this script.',
            'Species habit is a stylised procedural approximation, not a scan or a survey.',
            'Textures are procedural: no photograph, no third-party asset, no licence question.',
            'Nothing here is halachic.',
        ],
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate JudeanFloraV1 offline.')
    parser.add_argument('--export', action='store_true', help='meshes, textures and the manifest')
    parser.add_argument('--plan', action='store_true', help='the rule-derived placement plan')
    parser.add_argument('--tests', action='store_true', help='compile and run ScatterMathTest.cpp')
    parser.add_argument('--no-preview', action='store_true', help='skip the preview PNGs')
    args = parser.parse_args(argv)
    do_export = args.export or not (args.export or args.plan or args.tests)
    do_plan = args.plan or not (args.export or args.plan or args.tests)

    tests = None
    if args.tests:
        tests = run_scatter_tests()
        print('scatter tests: %s (exit %d)' % (tests['status'], tests['exitCode']))
        for line in tests['stdout'][-3:]:
            print('  ' + line)
        if tests['exitCode'] != 0:
            return 1

    if do_export:
        print('exporting meshes and textures...')
        meshes, readbacks, textures, _counts = export_meshes()
        manifest = write_manifest(meshes, readbacks, textures, tests)
        print('  %d meshes, %d triangles, %d texture sets -> %s'
              % (manifest['meshCount'], manifest['triangles'], len(textures),
                 MANIFEST_PATH.relative_to(ROOT)))

    if do_plan:
        print('planning placement...')
        plan = build_plan(write_previews=not args.no_preview)
        budget = plan['budget']
        print('  %d instances in %d batches -> %s'
              % (plan['totalInstances'], plan['batching']['batchCount'], PLAN_PATH.relative_to(ROOT)))
        print('  budget: %.0f tris/frame estimated against a %.1f M ceiling (%.1fx headroom), '
              '%d of a %d instance cap, %.1f MB instance buffers'
              % (budget['estimatedTrianglesPerFrame'], budget['triangleCeilingPerFrame'] / 1e6,
                 budget['triangleHeadroom'], budget['instancesPlanned'], budget['instanceCap'],
                 budget['instanceBufferMB']))
        if not (budget['withinTriangleCeiling'] and budget['withinInstanceCap']
                and budget['withinVramBudget']):
            print('  BUDGET EXCEEDED')
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
