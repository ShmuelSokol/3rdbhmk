"""Guarded native placement of PrecinctApproachV1 - the way UP from the city to the plaza.

THE DEFECT THIS CLOSES
----------------------
SourceAssets/enclosure-review/PLAZA-DESIGN-20260909.md section 6, open item 2:

    "THE OUTSIDE APPROACHES ARE NOT BUILT. Where the deck stands above the ground outside
     the wall - 60.6 m at the south-west gate, 50.4 m at the south-east - a visitor arriving
     from the modern street has no way up."

The plaza deck is at Z 0 (748.0 m a.s.l.) across the whole 3,000-amah precinct and the
retaining ring reaches 137 m on the south face. Every gate opening is at or above the deck,
and outside three of the five gates the ground is below it, so the precinct today cannot be
entered on foot. This pass builds the missing approaches.

WHAT IS SOURCED, WHAT IS DERIVED, WHAT IS AUTHORED
--------------------------------------------------
SOURCED: the gate COUNT and side only - Mishkenei Elyon 196 m.2, two south, one each north,
    east and west - and the precinct extent, Yechezkel 42:15-20 with 40:5. Nothing in
    Yechezkel, the Mishnah or the book describes an approach to the precinct from outside.
DERIVED FROM MEASURED GEOMETRY (never authored, never assumed):
    * every gate POSITION is read from SourceAssets/enclosure-review/precinct-<Target>.json,
      not restated here, so the approaches land on the same axial gates the plaza's
      processional ways were set out from;
    * the deck datum and the paved extent are read from plaza-<Target>.json and re-read live
      off the placed AMikdashEnclosure actor (GetPlazaDeckTopZCm, GetOuterFacesCm);
    * the ground OUTSIDE the wall - the street this has to reach - is measured off the live
      terrain meshes in the level (the same *_PrecinctCut / *_FutureMountCut twins the level
      actually renders), triangle by triangle, and the whole plan is a pure function of that
      height field. The offline pass runs the identical planner over the frozen level grid
      (jerusalem-meshes.json 'Terrain 0') and both plans go in the receipt.
AUTHORED (this project's architecture, not a reconstruction):
    * that the approach is a raking monumental stair at all;
    * the 50-amah-square head landing outside every gate;
    * the direction rule - straight out where the ground rises to meet the stair, along the
      face where it does not;
    * the landing rhythm: a 10-amah landing every 20 risers and a 50-amah terrace every fifth
      landing;
    * the flanking retaining, kerbs, and that the wedge under the stair is left void.

THE RULE THAT DECIDES THE PLAN, and why a straight stair is wrong on the south
------------------------------------------------------------------------------
A stair on the project's frozen tread (PlazaStepRiserAmot 0.5, PlazaStepTreadAmot 2.0)
descends at 1:4. Outside the two south gates the GROUND falls away faster than that: at the
south-west gate the grade drops from 685 m at the wall to 592 m 384 m further south, while a
1:4 stair would only have reached 652 m. A stair driven straight out from the south gates
NEVER MEETS THE GROUND - it diverges from it for ever, and would end as a viaduct hanging
60 m over the Hinnom.

Along the same wall the grade RISES eastward from the south-west gate (684 m at the gate to
724 m at the middle of the south face). A stair that turns at the head landing and rakes
ALONG the face therefore converges with the ground at 1:4 plus the grade, and lands on it.
That is Robinson's Arch's answer to the same problem on the same hill, and it is the answer
this pass takes. The direction is not asserted: all three candidates (out, and both ways
along the face) are simulated against the measured height field and the one that reaches the
ground in the shortest run wins, with a preference for straight out where it converges at
all. Every candidate's run is recorded in the receipt.

REUSE, AND THE ONE RULE THAT MUST NOT BE BROKEN
-----------------------------------------------
No new mesh and no new material. The approaches are laid entirely from the seven approved
PrecinctPlazaV1 modules - SM_PlazaV1_Step, SM_PlazaV1_RetainingBand, SM_PlazaV1_WayTile and
SM_PlazaV1_Kerb - with the approved MI_PrecinctPlaza_Ashlar and MI_PrecinctPlaza_WaySlabs.

    THE RETAINING BANDS ARE NEVER SCALED IN Z. MI_HerodianV4_Ashlar maps u = world X|Y / 300
    and v = world Z / 300, so its course lines fall on fixed world-Z levels; a band stretched
    to fit a drop would carry courses of a different height from the band above it. Facing a
    drop is a COUNT of fixed 5-amah bands, and the lowest band over-runs into the ground.

Every instance in this pass carries the UNIFORM module scale ModuleScaleFor(cmPerAmah) - 0.96
on the 48 cm candidate, 1.0 on Main50 - and nothing else. There is no non-uniform scale
anywhere in this file, and the readback asserts it.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_precinct_approaches.py"
      -Candidate48 -ApproachApply
      -unattended -nullrhi -EnablePlugins=GeometryScripting
      -abslog="C:/Mikdash/Working-5.8/Release-PrecinctApproach-01.log"

ONE TARGET PER RUN, chosen with its flag; there is no default:
  -Candidate48   the configured default and the cook map. Run this one first.
  -Main50        the legacy 50 cm map.

ONE MODE PER RUN:
  -ApproachApply    measure the live ground, place, save, reopen, re-measure, read back.
  -ApproachVerify   reopen and re-measure the placed approaches. Saves nothing.
  -ApproachRevert   destroy the PrecinctApproachV1 actor, save, reopen, prove it is gone.

Run with no engine at all to get the offline plan as JSON:
  python Scripts/release_precinct_approaches.py -Candidate48
  python Scripts/release_precinct_approaches.py -Candidate48 --level-grid

WHY A NEW ACTOR, AND THE REGRESSION THAT COMES WITH IT
------------------------------------------------------
The plaza is seven HISM components ON the existing AMikdashEnclosure actor, which is why it
cost zero actors. It could be, because AMikdashEnclosure has UPROPERTYs for it. It has none
for the approaches, and adding them needs a plugin rebuild, which this pass is not permitted
to run. So the approaches are ONE new actor carrying FOUR HierarchicalInstancedStaticMesh
components - four draw calls, not one actor per step - placed by the editor subobject path
that Scripts/release_city_detail.py proved. That actor is NOT wired into the YECHEZKEL /
MODERN state toggle, for exactly the reason the terrain cut is not:
AMikdashEnclosure::GatherModernBuildings resolves an identity label only for meshes under
JerusalemContext/Buildings/ or OldCityFacadesV1/Meshes/, so no value in ExplicitHideLabels can
ever reach a PlazaV1 mesh. Until the plugin is rebuilt the approaches are visible in MODERN
too. That is named here, in the receipt, and in the design record, rather than buried.

SAFETY MODEL (identical in shape to Scripts/release_precinct_plaza.py)
----------------------------------------------------------------------
Refuse on a live or dirty editor, on the wrong project, on a loaded world that is not the
target. Hash the target map and every protected map before anything, checkpoint the target
map and its one-file-per-actor folders into ReviewCheckpoints, write the receipt at the start
and again in `finally`, and prove in the finally block that the protected maps came out
byte-identical.
"""
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
HEADER = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h'
PLAZA_SPEC_PATH = ROOT / 'Scripts/release_precinct_plaza.spec.json'
REVIEW = ROOT / 'SourceAssets/enclosure-review'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')

TARGET_FLAGS = {'-candidate48': 'Candidate48', '-main50': 'Main50'}
MODE_FLAGS = {'-approachapply': 'apply', '-approachverify': 'verify',
              '-approachrevert': 'revert'}

ACTOR_LABEL = 'RELEASE_PrecinctApproachV1'
ACTOR_TAG = 'PrecinctApproachV1'
ACTOR_FOLDER = 'MikdashV3/PrecinctApproachV1'

MESH_FOLDER = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes'
MATERIAL_FOLDER = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials'

# component name -> (approved mesh, approved material, cast shadow)
COMPONENTS = (
    ('ApproachStepInstances', 'SM_PlazaV1_Step', 'MI_PrecinctPlaza_Ashlar', True),
    ('ApproachPavingInstances', 'SM_PlazaV1_WayTile', 'MI_PrecinctPlaza_WaySlabs', False),
    ('ApproachRetainingInstances', 'SM_PlazaV1_RetainingBand', 'MI_PrecinctPlaza_Ashlar', True),
    ('ApproachKerbInstances', 'SM_PlazaV1_Kerb', 'MI_PrecinctPlaza_Ashlar', True),
)

SEA_LEVEL_AT_Z0_M = 748.0

# Outward normal of each side, in the enclosure's own side order (0 north, 1 east, 2 south,
# 3 west). Same table as EnclosureMath.h SideOutwardYawDegrees {270, 0, 90, 180}.
SIDE_OUTWARD = ((0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0))

# AUTHORED. How far a candidate direction is allowed to run before it is declared divergent.
# 1,200 amot is 576 m on the candidate: four times the tallest face on the site, so a
# direction that has not met the ground by then is not going to.
RUN_CAP_AMOT = 1200.0
# AUTHORED. Straight out through the gate is preferred wherever it converges at all, because
# a gate should be entered head-on; a turn is a concession to the ground, not a flourish.
PREFER_OUTWARD = True
# AUTHORED. How much lower another direction must land before the head-on entry is given up.
# 10 amot is 4.8 m on the candidate: one flight of twenty risers.
OUTWARD_PREFERENCE_AMOT = 10.0


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def metres_asl(z_cm):
    return SEA_LEVEL_AT_Z0_M + z_cm / 100.0


# ---------------------------------------------------------------------------
# Constants, read out of EnclosureMath.h rather than restated
# ---------------------------------------------------------------------------
def header_constants():
    text = HEADER.read_text(encoding='utf-8')
    found = {}
    for kind, pattern in (('double', r'constexpr\s+double\s+(\w+)\s*=\s*([^;]+);'),
                          ('int', r'constexpr\s+int\s+(\w+)\s*=\s*([^;]+);')):
        for name, value in re.findall(pattern, text):
            value = value.strip()
            if kind == 'double' and re.fullmatch(r'-?\d+(\.\d+)?', value):
                found[name] = float(value)
            elif kind == 'int' and re.fullmatch(r'-?\d+', value):
                found[name] = int(value)
    required = ('ProjectCmPerAmah', 'PlazaStepRiserAmot', 'PlazaStepTreadAmot',
                'PlazaStepWidthAmot', 'PlazaStepsPerFlight', 'PlazaLandingDepthAmot',
                'PlazaRetainingBandHeightAmot', 'PlazaRetainingBandThicknessAmot',
                'PlazaRetainingBatterEveryBands', 'PlazaRetainingBatterAmot',
                'PlazaCellAmot', 'PlazaKerbWidthAmot')
    missing = [name for name in required if name not in found]
    if missing:
        raise RuntimeError('EnclosureMath.h no longer declares %s' % missing)
    return found


K = header_constants()
HEADER_SHA256 = sha256_of(HEADER)

# AUTHORED. Every fifth landing is a terrace five times as deep: a place to stand and turn
# round on a 30 m climb, not just a break in the tread rhythm.
TERRACE_EVERY_LANDINGS = 5

# cp19 (11 Sep 2026). A rolled band laid on each exposed batter ledge (EnclosureMath.h PlazaBandIsLedge /
# PlazaLedgeWashOriginInsetUnrealCm, the same rule the precinct ring now uses). FRotator roll is POSITIVE
# clockwise looking along +X, i.e. it turns local +Y DOWN, so -45 tips the band's outer face up-and-out.
WASH_ROLL_DEGREES = -float(K.get('PlazaLedgeWashDegrees', 45.0))
WASH_INSET_FRACTION = 0.70710678118654752
TERRACE_DEPTH_AMOT = 50.0


def module_scale(cm_per_amah):
    """EnclosureMath.h ModuleScaleFor. UNIFORM, on all three axes, and the only scale this
    file ever applies: the modules are baked at ProjectCmPerAmah and a level baked at another
    amah scales them whole so a 25-amah module stays 25 amot."""
    return float(cm_per_amah) / float(K['ProjectCmPerAmah'])


def band_count(height_cm, band_cm):
    """EnclosureMath.h PlazaBandCount. A COUNT, never a Z scale."""
    if not (band_cm > 0.0) or not (height_cm > 0.0) or not math.isfinite(height_cm):
        return 0
    return int(math.ceil(height_cm / band_cm - 1e-9))


def band_batter_cm(band, cm_per_amah):
    """EnclosureMath.h PlazaBandBatterUnrealCm: one amah further out per five bands, never
    negative, so nothing overhangs."""
    if band <= 0 or K['PlazaRetainingBatterEveryBands'] <= 0:
        return 0.0
    steps = int(band) // int(K['PlazaRetainingBatterEveryBands'])
    return K['PlazaRetainingBatterAmot'] * steps * cm_per_amah


def compass_of(direction):
    """Level axes: +X east, +Y south, Z up (Scripts/create_enclosure.py, OBJ adapter note)."""
    x, y = float(direction[0]), float(direction[1])
    if abs(x) >= abs(y):
        return 'east' if x > 0 else 'west'
    return 'south' if y > 0 else 'north'


def side_outward_yaw(side):
    return (270.0, 0.0, 90.0, 180.0)[int(side) % 4]


def yaw_for_local_y(direction):
    """Yaw putting the module's local +Y along `direction`.

    A UE yaw t maps local +X to (cos t, sin t) and local +Y to (-sin t, cos t), so
    t = atan2(-Dx, Dy). Both modules this file orients are authored the same way: the STEP is
    50 amot along local X with its 2-amah tread along local Y ("local +Y in the direction of
    ascent", create_precinct_plaza.step_module), and the RETAINING BAND is 25 amot along
    local X with its body at local -Y and its outer FACE on the local Y = 0 plane, so local
    +Y is the face normal. One helper serves both.

    ---------------------------------------------------------------------------------------
    A NOTE ON THE RUNTIME'S OWN GATE STAIRS, WHICH DISAGREE WITH THIS AND ARE WRONG.
    MikdashEnclosure.cpp:1186 yaws the INSIDE gate flights by SideOutwardYawDegrees(Side)
    while advancing them along -Out. At the south side that is yaw 90 with travel along -Y,
    which puts the step's 50-amah WIDTH along the direction of travel and its 2-amah tread
    across it - 205 modules at the east gate and 10 at the west, each overlapping the next
    twenty-four times. The band placement four lines earlier uses SideOutwardYawDegrees - 90,
    which is the correct convention and the one this file follows. The inside flights are C++
    and cannot be corrected without a plugin rebuild, which this pass may not run; the defect
    is reported in the receipt under runtimeDefectsObserved and nothing here depends on it.
    ---------------------------------------------------------------------------------------
    """
    return math.degrees(math.atan2(-direction[0], direction[1])) % 360.0


# ---------------------------------------------------------------------------
# The planner. A PURE FUNCTION of the height field, so the offline pass and the
# native pass run the identical code over two independent measurements of the
# same ground and the receipt can compare them.
# ---------------------------------------------------------------------------
class Plan(object):
    """One target's approaches, and every instance transform they need.

    Instances are (x, y, z, yaw, kind) with a single uniform scale for the whole plan.
    """

    def __init__(self, config):
        self.config = config
        self.a = float(config['amahCm'])
        self.deck_z = float(config['deckZcm'])
        self.scale = module_scale(self.a)
        self.riser = K['PlazaStepRiserAmot'] * self.a
        self.tread = K['PlazaStepTreadAmot'] * self.a
        self.width = K['PlazaStepWidthAmot'] * self.a
        self.band_h = K['PlazaRetainingBandHeightAmot'] * self.a
        self.cell = K['PlazaCellAmot'] * self.a
        self.landing = K['PlazaLandingDepthAmot'] * self.a
        self.terrace = TERRACE_DEPTH_AMOT * self.a
        self.cap = RUN_CAP_AMOT * self.a
        self.steps = []
        self.paving = []
        self.bands = []
        self.kerbs = []
        self.approaches = []
        self._max_stack = 0
        self._parapet_max = 0.0
        self._washes = 0

    # -- geometry helpers ---------------------------------------------------
    def _lowest_under(self, height, centre, axis, half, samples=5):
        """Lowest measured ground across a module's footprint. The stack must reach the
        LOWEST ground under it or it stands on air at one end."""
        best = None
        for index in range(samples):
            t = -half + (2.0 * half) * index / float(samples - 1)
            z = height(centre[0] + axis[0] * t, centre[1] + axis[1] * t)
            if z is None:
                continue
            best = z if best is None else min(best, z)
        return best

    def _over(self, height, centre, half_x, half_y, pick, samples=5):
        best = None
        for i in range(samples):
            for j in range(samples):
                x = centre[0] - half_x + 2.0 * half_x * i / float(samples - 1)
                y = centre[1] - half_y + 2.0 * half_y * j / float(samples - 1)
                z = height(x, y)
                if z is None:
                    continue
                best = z if best is None else pick(best, z)
        return best

    def _highest_over(self, height, centre, half_x, half_y, samples=5):
        return self._over(height, centre, half_x, half_y, max, samples)

    def _lowest_over(self, height, centre, half_x, half_y, samples=5):
        return self._over(height, centre, half_x, half_y, min, samples)

    def _stack(self, top_z, ground_z, face_point, outward, yaw, world_grid=False):
        """One retaining stack of fixed 5-amah bands from `top_z` down past `ground_z`. Never Z-scaled.

        cp19 - ON THE WORLD BAND GRID. The stack used to start at its own tread (`top_z - band * h`)
        and batter by the band index counted from that tread, so along a raking flight every
        25-amah column put its band joints and its batter ledges one tread lower than the column
        before: the "staircase of ledges" on the south face at the S1 approach (cp17b P2 frame).
        A real retaining wall's face is continuous and only its footing follows the rock. Now band k
        always occupies [deck - (k+1)h, deck - k h] and batters by band_batter_cm(k) - exactly the
        precinct ring's own rule - so every column's joints and ledges sit on the same world-Z
        levels as the ring's, and the face is one plane per batter step. The top band is the one
        the tread falls in, so it stands up to one band ABOVE the tread as a stepped parapet on the
        open side of the stair. `face_point` must be the UN-ridden line (see _place_flight): at the
        tread's own band the world batter equals the ride, so the tread still sits on its ledge."""
        if not world_grid:
            # Pre-cp19 rule, byte-for-byte in effect: straight-out flights and head landings. Their flanks are short
            # and stand in the open, where a stepped top following the treads is right and a grid parapet is not.
            count = band_count(top_z - ground_z, self.band_h)
            for band in range(count):
                batter = band_batter_cm(band, self.a)
                self.bands.append((face_point[0] + outward[0] * batter,
                                   face_point[1] + outward[1] * batter,
                                   top_z - band * self.band_h, yaw, 'band'))
            self._max_stack = max(self._max_stack, count)
            return count
        k0 = int(math.floor((self.deck_z - top_z) / self.band_h + 1e-9))
        # first band whose bottom reaches the ground; NOT band_count, which clamps a negative height to 0 and
        # would run a stack that starts above the deck (cut-side gates, E) all the way down to the deck
        k_end = int(math.ceil((self.deck_z - ground_z) / self.band_h - 1e-9))
        if k_end <= k0:
            k_end = k0 + 1
        count = 0
        for k in range(k0, k_end):
            batter = band_batter_cm(k, self.a)
            z_top = self.deck_z - k * self.band_h
            self.bands.append((face_point[0] + outward[0] * batter,
                               face_point[1] + outward[1] * batter,
                               z_top, yaw, 'band'))
            count += 1
            if k > k0 and batter > band_batter_cm(k - 1, self.a):
                inset = self.band_h * WASH_INSET_FRACTION
                self.bands.append((face_point[0] + outward[0] * (batter - inset),
                                   face_point[1] + outward[1] * (batter - inset),
                                   z_top + inset, yaw, 'bandWash', WASH_ROLL_DEGREES))
                self._washes += 1
        self._max_stack = max(self._max_stack, count)
        self._parapet_max = max(self._parapet_max, (self.deck_z - k0 * self.band_h) - top_z)
        return count

    # -- one flight ---------------------------------------------------------
    def _simulate(self, height, start, direction, top_z, along_wall, outward, cap):
        """March a 1:4 flight until its tread comes down to the measured ground.

        Returns a dict describing the flight WITHOUT placing anything, so all three candidate
        directions can be simulated and compared before one is chosen.
        """
        z = top_z
        s = 0.0
        risers = 0
        landings = 0
        terraces = 0
        run_since_landing = 0
        max_unbroken = 0
        modules = []          # (along_s_centre, z, kind)
        buried = 0.0
        met = False
        foot = None
        while s < cap:
            z -= self.riser
            centre_s = s + self.tread * 0.5
            s += self.tread
            risers += 1
            run_since_landing += 1
            max_unbroken = max(max_unbroken, run_since_landing)
            modules.append((centre_s, z, 'tread'))
            point = self._point(start, direction, centre_s, z, top_z, along_wall, outward)
            ground = height(point[0], point[1])
            if ground is None:
                return dict(converged=False, reason='no terrain under the run at %.0f cm' % s,
                            runCm=s, risers=risers)
            buried = max(buried, ground - z)
            if z <= ground:
                met = True
                foot = dict(sCm=centre_s, zCm=z, groundZcm=ground, point=point)
                break
            if run_since_landing >= int(K['PlazaStepsPerFlight']):
                landings += 1
                depth = self.landing
                if landings % TERRACE_EVERY_LANDINGS == 0:
                    depth = self.terrace
                    terraces += 1
                units = int(round(depth / self.tread))
                for unit in range(units):
                    centre_l = s + (unit + 0.5) * self.tread
                    modules.append((centre_l, z, 'landing'))
                    # A landing runs level for 10 or 50 amot while the hillside keeps rising,
                    # so the ground can come up to meet it MID-LANDING. Checking only at the
                    # treads let the flight run on and cross half a metre low on the next
                    # riser; this catches it where it happens.
                    point_l = self._point(start, direction, centre_l, z, top_z,
                                          along_wall, outward)
                    ground_l = height(point_l[0], point_l[1])
                    if ground_l is not None:
                        buried = max(buried, ground_l - z)
                        if z <= ground_l:
                            met = True
                            foot = dict(sCm=centre_l, zCm=z, groundZcm=ground_l, point=point_l)
                            break
                if met:
                    s = foot['sCm'] + self.tread * 0.5
                    break
                s += units * self.tread
                run_since_landing = 0
        if not met:
            return dict(converged=False, reason='diverges: the ground falls away faster than '
                                                'a 1:4 stair descends', runCm=s, risers=risers)
        # THE FOOT. The crossing tread is at or below the ground; the tread before it is above.
        # Take whichever lands closer to the ground, so the last tread is never more than about
        # one riser from it in either direction, and truncate the flight there. Stopping short
        # is the failure mode this pass exists to avoid, so the residual is reported signed:
        # negative means the last tread runs INTO the slope, positive means it stands above it.
        if risers >= 2 and modules and modules[-1][2] == 'tread':
            previous_index = None
            for index in range(len(modules) - 2, -1, -1):
                if modules[index][2] == 'tread':
                    previous_index = index
                    break
            if previous_index is not None:
                prev_s, prev_z, _kind = modules[previous_index]
                prev_point = self._point(start, direction, prev_s, prev_z, top_z,
                                         along_wall, outward)
                prev_ground = height(prev_point[0], prev_point[1])
                if prev_ground is not None and \
                        abs(prev_z - prev_ground) < abs(foot['zCm'] - foot['groundZcm']):
                    modules = modules[:previous_index + 1]
                    risers -= 1
                    s = prev_s + self.tread * 0.5
                    foot = dict(sCm=prev_s, zCm=prev_z, groundZcm=prev_ground, point=prev_point)
                    buried = max(0.0, prev_ground - prev_z)
        return dict(converged=True, runCm=s, risers=risers, landings=landings,
                    terraces=terraces, maxUnbrokenRisers=max_unbroken,
                    maxUnbrokenRiseCm=max_unbroken * self.riser,
                    dropCm=top_z - foot['zCm'], modules=modules, foot=foot,
                    maxBuriedCm=max(0.0, buried))

    def _point(self, start, direction, along_s, z, top_z, along_wall, outward):
        """World XY of a module centre at `along_s` down the flight.

        A flight raking ALONG the face is pushed outward by the wall's OWN batter at that
        depth - PlazaBandBatterUnrealCm of the band the tread is in - so its inner edge rides
        the ledge line the retaining wall already steps out onto every 25 amot of height,
        rather than being buried in a wall that widens as it descends.
        """
        x = start[0] + direction[0] * along_s
        y = start[1] + direction[1] * along_s
        if along_wall:
            depth = max(0.0, top_z - z)
            batter = band_batter_cm(int(math.floor(depth / self.band_h)), self.a)
            x += outward[0] * batter
            y += outward[1] * batter
        return (x, y)

    # -- one gate -----------------------------------------------------------
    def build_gate(self, gate, height):
        side = int(gate['side'])
        outward = SIDE_OUTWARD[side]
        tangent = (-outward[1], outward[0])
        gx, gy = float(gate['positionCm'][0]), float(gate['positionCm'][1])
        half = self.width * 0.5

        # The head landing: 50 amot square, from the outer face outward, centred on the gate.
        head_centre = (gx + outward[0] * half, gy + outward[1] * half)
        face_ground = height(gx, gy)
        head_ground = self._highest_over(height, head_centre, half, half)
        head_low = self._lowest_over(height, head_centre, half, half)
        if face_ground is None or head_ground is None or head_low is None:
            return dict(id=gate['id'], side=side, built=False,
                        reason='no terrain measured at the gate')

        # THE THRESHOLD IS NOT RE-DERIVED HERE. It is the wall base the runtime actually built
        # this gate on - PlazaWallBaseZUnrealCm(GroundHigh over the gate's own cell span,
        # deck) - and it is read from plaza-<Target>.json, which is the receipt the placed
        # AMikdashEnclosure was verified against. Re-sampling the ground over a 50-amah head
        # landing instead gave a threshold 1.7 m ABOVE the built one at the east gate, which
        # would have put a step UP out of the gate onto the approach: the same "stops short"
        # failure this pass exists to prevent, upside down.
        top_z = float(gate['thresholdZcm'])
        drop = top_z - face_ground
        record = dict(id=gate['id'], side=side, sideName=('north', 'east', 'south', 'west')[side],
                      gateCm=[gx, gy],
                      groundAtFaceZcm=round(face_ground, 3),
                      groundAtFaceMetresAsl=round(metres_asl(face_ground), 2),
                      headGroundHighZcm=round(head_ground, 3),
                      headGroundLowZcm=round(head_low, 3),
                      thresholdZcm=round(top_z, 3),
                      thresholdMetresAsl=round(metres_asl(top_z), 2),
                      thresholdSource=gate.get('thresholdSource'),
                      measuredFaceHeightCm=round(top_z - face_ground, 2),
                      measuredFaceHeightMetres=round((top_z - face_ground) / 100.0, 2))
        if drop <= self.riser:
            record.update(built=False, reason='the ground outside stands within one riser '
                                              '(%.1f cm) of the threshold; a visitor already '
                                              'walks in at grade' % self.riser)
            return record

        # ---- candidate directions, all three simulated against the same measurement ----
        candidates = []
        for name, direction, along_wall, start in (
                ('outward', outward, False,
                 (gx + outward[0] * self.width, gy + outward[1] * self.width)),
                ('along+', tangent, True,
                 (gx + outward[0] * half + tangent[0] * half,
                  gy + outward[1] * half + tangent[1] * half)),
                ('along-', (-tangent[0], -tangent[1]), True,
                 (gx + outward[0] * half - tangent[0] * half,
                  gy + outward[1] * half - tangent[1] * half))):
            cap = self.cap
            if along_wall:
                # never run past the corner of its own side
                reach = self._distance_to_corner(gx, gy, side, direction)
                cap = max(0.0, min(cap, reach - self.width))
            result = self._simulate(height, start, direction, top_z, along_wall, outward, cap)
            result.update(name=name, compass=compass_of(direction),
                          direction=list(direction), startCm=list(start),
                          alongWall=along_wall, capCm=cap)
            candidates.append(result)
        record['candidates'] = [{k: v for k, v in c.items() if k != 'modules' and k != 'foot'}
                                for c in candidates]

        converged = [c for c in candidates if c['converged']]
        if not converged:
            record.update(built=False, reason='no direction converges with the ground within '
                                              '%g amot' % RUN_CAP_AMOT)
            return record
        # THE RULE. Take the direction whose foot lands LOWEST. An approach exists to reach
        # the ground people are actually on, and the SHORTEST stair is repeatedly the one that
        # stops highest on the hillside: at the south-west gate the short eastward rake lands
        # 35 m above the grade at the gate's own foot, on a 46 per cent slope, which has not
        # connected the precinct to the city. Straight out through the gate still wins wherever
        # it lands within OUTWARD_PREFERENCE_AMOT of the lowest, because a gate should be
        # entered head-on and a turn is a concession to the ground, not a flourish.
        lowest = min(converged, key=lambda c: c['foot']['zCm'])
        chosen = lowest
        outward_candidate = next((c for c in converged if c['name'] == 'outward'), None)
        if PREFER_OUTWARD and outward_candidate is not None and                 outward_candidate['foot']['zCm'] - lowest['foot']['zCm']                 <= OUTWARD_PREFERENCE_AMOT * self.a:
            chosen = outward_candidate
        record['chosen'] = chosen['name']
        record['chosenCompass'] = chosen['compass']
        record['chosenWhy'] = (
            'straight out through the gate converges and lands within %g amot of the lowest '
            'foot any direction reaches' % OUTWARD_PREFERENCE_AMOT
            if chosen['name'] == 'outward' else
            'straight out %s; the converging rake whose foot lands lowest is taken instead '
            '(%s, foot %.1f m a.s.l., against %.1f m for the shortest converging rake)'
            % (('diverges: ' + next(c['reason'] for c in candidates if c['name'] == 'outward'))
               if outward_candidate is None else 'lands too high',
               chosen['compass'], metres_asl(chosen['foot']['zCm']),
               metres_asl(min(converged, key=lambda c: c['runCm'])['foot']['zCm'])))

        # ---- place ----
        before = (len(self.steps), len(self.paving), len(self.bands), len(self.kerbs))
        self._max_stack = 0
        self._parapet_max = 0.0
        self._washes = 0
        head = self._place_head(head_centre, outward, tangent, top_z, height, half)
        self._place_flight(chosen, outward, top_z, height)
        # THE REST OF THE FALL, and whether it is a cliff or a hillside. Where the stair meets
        # the ground higher than the grade at the gate's own foot, the visitor walks the
        # remainder on natural ground; this measures that walk so the claim can be checked
        # rather than asserted.
        foot_point = chosen['foot']['point']
        gap_metres = (chosen['foot']['groundZcm'] - face_ground) / 100.0
        span_metres = math.hypot(foot_point[0] - gx, foot_point[1] - gy) / 100.0
        worst_grade = 0.0
        samples = 24
        previous = None
        for index in range(samples + 1):
            t = index / float(samples)
            px = gx + (foot_point[0] - gx) * t
            py = gy + (foot_point[1] - gy) * t
            z = height(px, py)
            if z is None:
                continue
            if previous is not None:
                run = math.hypot(px - previous[0], py - previous[1])
                if run > 1e-6:
                    worst_grade = max(worst_grade, abs(z - previous[2]) / run)
            previous = (px, py, z)
        record.update(
            built=True,
            headLanding=head,
            remainingFallBelowFootMetres=round(gap_metres, 2),
            remainingWalkOnNaturalGroundMetres=round(span_metres, 1),
            remainingWalkWorstGrade=round(worst_grade, 4),
            remainingWalkWorstGradeVersusStair=round(worst_grade / (self.riser / self.tread), 3),
            headLandingCentreCm=[round(v, 3) for v in head_centre],
            headLandingTopZcm=round(top_z, 3),
            headLandingSideCm=round(self.width, 2),
            runCm=round(chosen['runCm'], 2), runMetres=round(chosen['runCm'] / 100.0, 2),
            risers=chosen['risers'], landings=chosen['landings'], terraces=chosen['terraces'],
            maxUnbrokenRisers=chosen['maxUnbrokenRisers'],
            maxUnbrokenRiseCm=round(chosen['maxUnbrokenRiseCm'], 2),
            maxUnbrokenRiseMetres=round(chosen['maxUnbrokenRiseCm'] / 100.0, 2),
            totalClimbCm=round(chosen['dropCm'], 2),
            totalClimbMetres=round(chosen['dropCm'] / 100.0, 2),
            footZcm=round(chosen['foot']['zCm'], 3),
            footMetresAsl=round(metres_asl(chosen['foot']['zCm']), 2),
            footGroundZcm=round(chosen['foot']['groundZcm'], 3),
            footGroundMetresAsl=round(metres_asl(chosen['foot']['groundZcm']), 2),
            footPointCm=[round(v, 3) for v in chosen['foot']['point']],
            footResidualCm=round(chosen['foot']['zCm'] - chosen['foot']['groundZcm'], 3),
            maxBuriedCm=round(chosen['maxBuriedCm'], 2),
            tallestFlankBands=self._max_stack,
            tallestFlankMetres=round(self._max_stack * self.band_h / 100.0, 1),
            worldBandGrid=True, ledgeWashes=self._washes,
            parapetMaxAboveTreadCm=round(self._parapet_max, 3),
            instances=dict(steps=len(self.steps) - before[0], paving=len(self.paving) - before[1],
                           bands=len(self.bands) - before[2], kerbs=len(self.kerbs) - before[3]))
        return record

    def _distance_to_corner(self, gx, gy, side, direction):
        faces = self.config['outerFacesCm']
        if side in (0, 2):
            lo, hi = faces['xWest'], faces['xEast']
            here = gx
            return (hi - here) if direction[0] > 0 else (here - lo)
        lo, hi = faces['yNorth'], faces['ySouth']
        here = gy
        return (hi - here) if direction[1] > 0 else (here - lo)

    def _place_head(self, centre, outward, tangent, top_z, height, half):
        """A 50-amah square platform at the threshold, outside the gate: four 25-amah way
        tiles, a kerb on each exposed edge, and a retaining stack under every exposed edge
        module down to the measured ground."""
        cell = self.cell
        tiles = 0
        skipped = 0
        for i in (-0.5, 0.5):
            for j in (-0.5, 0.5):
                x = centre[0] + outward[0] * (i * cell) + tangent[0] * (j * cell)
                y = centre[1] + outward[1] * (i * cell) + tangent[1] * (j * cell)
                # A tile is laid only where the natural grade is BELOW the threshold. Where the
                # hillside stands higher - the cut sides - nothing is laid, because no terrain
                # is cut outside the precinct square by this pass and a tile there would be
                # buried in the slope.
                over = self._highest_over(height, (x, y), cell * 0.5, cell * 0.5)
                if over is not None and over > top_z:
                    skipped += 1
                    continue
                self.paving.append((x, y, top_z, 0.0, 'headTile'))
                tiles += 1
        # three exposed edges: +outward (the far edge) and both tangents. The fourth is the
        # precinct wall.
        edges = ((outward, tangent), (tangent, outward), ((-tangent[0], -tangent[1]), outward))
        for normal, run_axis in edges:
            face = (centre[0] + normal[0] * half, centre[1] + normal[1] * half)
            yaw = yaw_for_local_y(normal)
            kerb_yaw = yaw_for_local_y(normal)
            for k in (-0.5, 0.5):
                point = (face[0] + run_axis[0] * (k * cell), face[1] + run_axis[1] * (k * cell))
                ground = self._lowest_under(height, point, run_axis, cell * 0.5)
                if ground is None or ground >= top_z:
                    continue
                self._stack(top_z, ground, point, normal, yaw)
                # kerb sits on the platform, half a module in from the face
                self.kerbs.append((point[0] - normal[0] * (self.a * 0.5),
                                   point[1] - normal[1] * (self.a * 0.5),
                                   top_z, kerb_yaw, 'headKerb'))
        return dict(tilesLaid=tiles, tilesSkippedUnderHigherGround=skipped)

    def _place_flight(self, flight, outward, top_z, height):
        direction = tuple(flight['direction'])
        start = tuple(flight['startCm'])
        along_wall = flight['alongWall']
        # perpendicular to travel, in the plane: the flight's own width axis
        cross = (-direction[1], direction[0])
        step_yaw = yaw_for_local_y((-direction[0], -direction[1]))   # local +Y = ascent
        half = self.width * 0.5

        for centre_s, z, kind in flight['modules']:
            point = self._point(start, direction, centre_s, z, top_z, along_wall, outward)
            self.steps.append((point[0], point[1], z, step_yaw, kind))

        # Flanking retaining and kerb, one 25-amah module at a time down the run. For a rake
        # ALONG the face only the outer flank is exposed - the inner one is the precinct's own
        # retaining wall. For a flight driven straight OUT both flanks are.
        flanks = [cross] if along_wall else [cross, (-cross[0], -cross[1])]
        if along_wall:
            # the exposed flank is the one pointing AWAY from the wall
            flanks = [cross if (cross[0] * outward[0] + cross[1] * outward[1]) > 0
                      else (-cross[0], -cross[1])]
        run = flight['runCm']
        modules = max(1, int(math.ceil(run / self.cell)))
        for index in range(modules):
            s0 = index * self.cell
            s_mid = min(run, s0 + self.cell * 0.5)
            z = self._tread_z_at(flight, s_mid, top_z)
            for normal in flanks:
                # cp19: the UN-ridden line. _stack adds the batter by WORLD band index; at the tread's
                # own band that equals the ride _point gives the treads (threshold == deck on every
                # built approach), so the tread still sits on its ledge and the face is continuous.
                if along_wall:
                    base = (start[0] + direction[0] * s_mid, start[1] + direction[1] * s_mid)
                else:
                    base = self._point(start, direction, s_mid, z, top_z, along_wall, outward)
                point = (base[0] + normal[0] * half, base[1] + normal[1] * half)
                ground = self._lowest_under(height, point, direction, self.cell * 0.5)
                if ground is None or ground >= z:
                    continue
                self._stack(z, ground, point, normal, yaw_for_local_y(normal), world_grid=along_wall)
                self.kerbs.append((point[0] - normal[0] * (self.a * 0.5),
                                   point[1] - normal[1] * (self.a * 0.5),
                                   z, yaw_for_local_y(normal), 'flightKerb'))

    def _tread_z_at(self, flight, s, top_z):
        """The tread level at run distance s: the LAST module at or before s."""
        z = top_z
        for centre_s, module_z, _kind in flight['modules']:
            if centre_s <= s:
                z = module_z
            else:
                break
        return z

    # -- the whole target ---------------------------------------------------
    def build(self, height):
        for gate in self.config['gates']:
            self.approaches.append(self.build_gate(gate, height))
        return self

    def summary(self):
        built = [a for a in self.approaches if a.get('built')]
        return dict(
            amahCm=self.a, moduleScale=self.scale, deckZcm=self.deck_z,
            riserCm=self.riser, treadCm=self.tread, stepWidthCm=self.width,
            rakeRunOverRise=self.tread / self.riser,
            bandHeightCm=self.band_h,
            stepsPerFlight=int(K['PlazaStepsPerFlight']),
            landingDepthCm=self.landing, terraceDepthCm=self.terrace,
            terraceEveryLandings=TERRACE_EVERY_LANDINGS,
            approachesBuilt=len(built),
            approachesNotBuilt=[dict(id=a['id'], reason=a.get('reason'))
                                for a in self.approaches if not a.get('built')],
            maxUnbrokenRiseCm=round(max([a['maxUnbrokenRiseCm'] for a in built] or [0.0]), 2),
            maxUnbrokenRiseMetres=round(max([a['maxUnbrokenRiseCm'] for a in built] or [0.0])
                                        / 100.0, 2),
            worstFootResidualCm=round(max([abs(a['footResidualCm']) for a in built] or [0.0]), 3),
            worstBuriedCm=round(max([a['maxBuriedCm'] for a in built] or [0.0]), 2),
            counts=dict(steps=len(self.steps), paving=len(self.paving),
                        bands=len(self.bands), kerbs=len(self.kerbs),
                        total=len(self.steps) + len(self.paving) + len(self.bands)
                        + len(self.kerbs)),
            triangles=(len(self.steps) + len(self.paving) + len(self.bands)
                       + len(self.kerbs)) * 12)


# ---------------------------------------------------------------------------
# Target configuration, read from the receipts the plaza and the wall already wrote
# ---------------------------------------------------------------------------
def load_plaza_spec():
    spec = json.loads(PLAZA_SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('release_precinct_plaza.spec.json project directory differs')
    return spec


def target_config(target_name):
    spec = load_plaza_spec()
    if target_name not in spec['targets']:
        raise RuntimeError('Unknown target %r; the plaza spec declares %s'
                           % (target_name, list(spec['targets'])))
    entry = spec['targets'][target_name]
    precinct = json.loads((REVIEW / Path(entry['precinctReceipt']).name).read_text(
        encoding='utf-8-sig'))
    plaza = json.loads((REVIEW / Path(entry['plazaReceipt']).name).read_text(
        encoding='utf-8-sig'))
    if abs(float(precinct['cmPerAmah']) - float(entry['amahCm'])) > 1e-9:
        raise RuntimeError('%s: precinct receipt amah %g, spec %g'
                           % (target_name, precinct['cmPerAmah'], entry['amahCm']))
    if abs(float(plaza['cmPerAmah']) - float(entry['amahCm'])) > 1e-9:
        raise RuntimeError('%s: plaza receipt amah disagrees with the spec' % target_name)
    plaza_gates = {g['id']: g for g in plaza['gates']}
    gates = []
    for g in precinct['gates']:
        row = plaza_gates.get(g['id'])
        if row is None:
            raise RuntimeError('plaza-%s.json has no gate %r' % (target_name, g['id']))
        if [round(v, 3) for v in row['positionCm']] != [round(float(v), 3) for v in g['positionCm']]:
            raise RuntimeError('gate %s stands at %r in the precinct receipt and %r in the '
                               'plaza receipt' % (g['id'], g['positionCm'], row['positionCm']))
        gates.append(dict(
            id=g['id'], side=int(g['side']),
            positionCm=[float(g['positionCm'][0]), float(g['positionCm'][1])],
            openingCm=g['openingCm'], source=g['source'],
            thresholdZcm=(float(row['thresholdMetresAsl']) - SEA_LEVEL_AT_Z0_M) * 100.0,
            thresholdSource='plaza-%s.json gates[%s].thresholdMetresAsl = %g - the wall base '
                            'PlazaWallBaseZUnrealCm this gate was actually built on'
                            % (target_name, g['id'], row['thresholdMetresAsl'])))
    return dict(
        target=target_name, map=entry['map'], mapFile=entry['mapFile'],
        protectedMaps=entry['protectedMaps'],
        amahCm=float(entry['amahCm']),
        deckZcm=float(plaza['deck']['topZcm']),
        outerFacesCm={k: float(v) for k, v in precinct['square']['outerFacesCm'].items()},
        wallThicknessCm=6.0 * float(entry['amahCm']),
        gates=gates,
        precinctReceipt=entry['precinctReceipt'],
        precinctReceiptSha256=sha256_of(REVIEW / Path(entry['precinctReceipt']).name),
        plazaReceipt=entry['plazaReceipt'],
        plazaReceiptSha256=sha256_of(REVIEW / Path(entry['plazaReceipt']).name),
        plazaGates=plaza['gates'])


# ---------------------------------------------------------------------------
# Offline height field: the frozen grid the level's terrain tiles were built from
# ---------------------------------------------------------------------------
def offline_height(prefer_level_grid=False):
    """(callable, provenance). The DEM by default; the level grid with --level-grid.

    jerusalem-meshes.json is 98 MB and is the grid the 256 level tiles were built from, so it
    is the closer offline stand-in for the live meshes; jerusalem.json is the 257x257 OSM DEM
    the whole context descends from and loads in a second. Both are only ever a CROSS-CHECK:
    the plan that is placed is the one measured off the live level.
    """
    import sys
    sys.path.insert(0, str(ROOT / 'Scripts'))
    import importlib
    enclosure = importlib.import_module('create_enclosure')
    if prefer_level_grid and enclosure.LEVEL_TERRAIN_SOURCE.exists():
        raw = enclosure.LEVEL_TERRAIN_SOURCE.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw.decode('utf-8'))
        positions = data['meshes']['Terrain 0']['positions'] if 'meshes' in data else None
        if positions is None:
            for entry in data.get('objects', data.get('nodes', [])):
                if entry.get('name') == 'Terrain 0':
                    positions = entry['positions']
                    break
        if positions is None:
            raise RuntimeError('jerusalem-meshes.json has no "Terrain 0" positions')
        grid = enclosure.HeightGrid(positions[1::3], "jerusalem-meshes.json 'Terrain 0'", sha, 0.05)
        return grid.height_cm, dict(source=str(enclosure.LEVEL_TERRAIN_SOURCE), sha256=sha,
                                    kind='level grid (the source of the 256 terrain tiles)')
    dem = enclosure.JERUSALEM_SOURCE
    raw = dem.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    terrain = json.loads(raw.decode('utf-8'))['terrain']
    heights = terrain['heights']
    grid = enclosure.HeightGrid(heights, 'jerusalem.json terrain.heights', sha, 1.0)
    return grid.height_cm, dict(source=str(dem), sha256=sha,
                                kind='OSM DEM (jerusalem.json terrain.heights)')


def offline_plan(target_name, prefer_level_grid=False):
    config = target_config(target_name)
    height, provenance = offline_height(prefer_level_grid)
    plan = Plan(config).build(height)
    return dict(status='OFFLINE_PLAN', target=target_name, map=config['map'],
                scriptSha256=sha256_of(Path(__file__)),
                enclosureMathSha256=HEADER_SHA256,
                heightFieldProvenance=provenance,
                precinctReceipt=config['precinctReceipt'],
                precinctReceiptSha256=config['precinctReceiptSha256'],
                plazaReceipt=config['plazaReceipt'],
                plazaReceiptSha256=config['plazaReceiptSha256'],
                summary=plan.summary(),
                approaches=plan.approaches)


# ---------------------------------------------------------------------------
# Native
# ---------------------------------------------------------------------------
class LiveHeightField(object):
    """Upper-envelope height lookup over the terrain triangles the LEVEL ACTUALLY RENDERS.

    Same bucketed triangle soup as release_precinct_terrain_cut.HeightField, filled from the
    VISIBLE terrain actors only, with each actor's own transform applied, so what it reports
    is the ground a visitor would stand on - including the *_PrecinctCut and *_FutureMountCut
    twins that replaced four and eleven of the originals.
    """

    CELL_CM = 2000.0

    def __init__(self):
        self.buckets = {}
        self.triangles = 0

    def add(self, faces):
        for face in faces:
            self.triangles += 1
            xs = [p[0] for p in face]
            ys = [p[1] for p in face]
            i0 = int(math.floor(min(xs) / self.CELL_CM))
            i1 = int(math.floor(max(xs) / self.CELL_CM))
            j0 = int(math.floor(min(ys) / self.CELL_CM))
            j1 = int(math.floor(max(ys) / self.CELL_CM))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.buckets.setdefault((i, j), []).append(face)

    def height(self, x, y):
        key = (int(math.floor(x / self.CELL_CM)), int(math.floor(y / self.CELL_CM)))
        best = None
        for a, b, c in self.buckets.get(key, ()):
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if den == 0.0:
                continue
            w0 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / den
            w1 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / den
            w2 = 1.0 - w0 - w1
            if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                continue
            z = w0 * a[2] + w1 * b[2] + w2 * c[2]
            if best is None or z > best:
                best = z
        return best


def _asset_path(obj):
    return None if obj is None else obj.get_path_name().split('.')[0]


class Native(object):
    def __init__(self, ue, config, mode, stamp):
        self.ue = ue
        self.config = config
        self.mode = mode
        self.stamp = stamp
        for name in ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries'):
            if not hasattr(ue, name):
                raise RuntimeError('Launch with -EnablePlugins=GeometryScripting: ' + name)
        self.query = ue.GeometryScript_MeshQueries
        self.asset_utils = ue.GeometryScript_AssetUtils
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.receipt = {}
        self.receipt_path = None
        self.transform_path = None

    def write_receipt(self):
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1, ensure_ascii=False) + '\n',
                                     encoding='utf-8')

    # -- the ground --------------------------------------------------------
    def terrain_rows(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            if actor is None:
                continue
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            if component is None:
                continue
            mesh = component.get_editor_property('static_mesh')
            if mesh is None or not mesh.get_name().startswith('SM_JerusalemTerrain_'):
                continue
            rows.append(dict(actor=actor.get_name(), label=actor.get_actor_label(),
                             mesh=mesh.get_name(),
                             hidden=bool(actor.get_editor_property('hidden')),
                             actor_object=actor, component=component, mesh_object=mesh))
        return rows

    def build_height_field(self, regions):
        """The live ground, from the visible terrain tiles that overlap the corridors this
        pass could possibly build into. Only those tiles are extracted: reading all 256 would
        be minutes of Python for ground no approach can reach."""
        ue = self.ue
        field = LiveHeightField()
        used = []
        for row in self.terrain_rows():
            if row['hidden']:
                continue
            origin, extent = row['actor_object'].get_actor_bounds(False)
            box = (origin.x - extent.x, origin.y - extent.y,
                   origin.x + extent.x, origin.y + extent.y)
            if not any(box[0] <= r[2] and r[0] <= box[2] and box[1] <= r[3] and r[1] <= box[3]
                       for r in regions):
                continue
            transform = row['component'].get_world_transform()
            dynamic = ue.DynamicMesh()
            options = ue.GeometryScriptCopyMeshFromAssetOptions()
            options.set_editor_property('apply_build_settings', False)
            options.set_editor_property('request_tangents', False)
            options.set_editor_property('use_build_scale', False)
            lod = ue.GeometryScriptMeshReadLOD()
            lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
            lod.set_editor_property('lod_index', 0)
            result = self.asset_utils.copy_mesh_from_static_mesh_v2(
                row['mesh_object'], dynamic, options, lod)
            if ue.GeometryScriptOutcomePins.SUCCESS not in result:
                raise RuntimeError('Terrain extraction failed for ' + row['mesh'])
            faces = []
            for tid in range(dynamic.get_triangle_count()):
                points = [v for v in self.query.get_triangle_positions(dynamic, tid)
                          if isinstance(v, ue.Vector)]
                if len(points) != 3:
                    raise RuntimeError('Incomplete triangle on ' + row['mesh'])
                world = [transform.transform_location(p) for p in points]
                faces.append([[w.x, w.y, w.z] for w in world])
            field.add(faces)
            used.append(dict(actor=row['label'], mesh=row['mesh'], triangles=len(faces),
                             boundsCm=[round(v, 2) for v in box]))
        return field, used

    def regions_of_interest(self):
        """One box per gate, reaching RUN_CAP_AMOT outward and along the face."""
        config = self.config
        reach = RUN_CAP_AMOT * config['amahCm']
        boxes = []
        for gate in config['gates']:
            gx, gy = gate['positionCm']
            boxes.append((gx - reach, gy - reach, gx + reach, gy + reach))
        return boxes

    # -- the actor ---------------------------------------------------------
    def find_actor(self):
        found = [a for a in self.actors.get_all_level_actors()
                 if a is not None and a.get_actor_label() == ACTOR_LABEL]
        if len(found) > 1:
            raise RuntimeError('%d actors labelled %s; refusing to guess'
                               % (len(found), ACTOR_LABEL))
        return found[0] if found else None

    def find_precinct(self):
        label = load_plaza_spec()['enclosureActorLabel']
        found = [a for a in self.actors.get_all_level_actors()
                 if a is not None and a.get_actor_label() == label]
        if len(found) != 1:
            raise RuntimeError('Expected exactly one %s, found %d' % (label, len(found)))
        return found[0]

    def new_hism(self, actor):
        """Instance-owned HISM on a plain editor actor, by the editor subobject path.

        AActor.add_component_by_class is not exposed to Python in UE 5.8 and merely
        constructing the component with outer=actor produces one the level never owns; this is
        Scripts/release_city_detail.py's proven path, with ownership verified three ways.
        """
        ue = self.ue
        subsystem = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
        library = ue.SubobjectDataBlueprintFunctionLibrary
        handles = subsystem.k2_gather_subobject_data_for_instance(actor)
        parent = next((h for h in handles
                       if library.get_associated_object(library.get_data(h)) == actor), None)
        if parent is None:
            raise RuntimeError('Editor actor subobject handle missing')
        params = ue.AddNewSubobjectParams(
            parent_handle=parent, new_class=ue.HierarchicalInstancedStaticMeshComponent,
            blueprint_context=None, conform_transform_to_parent=True)
        handle, reason = subsystem.add_new_subobject(params)
        if not library.is_handle_valid(handle):
            raise RuntimeError('Persistent HISM creation failed: ' + str(reason))
        data = library.get_data(handle)
        component = library.get_associated_object(data)
        if not isinstance(component, ue.HierarchicalInstancedStaticMeshComponent):
            raise RuntimeError('Subobject is a %s, not a HISM' % type(component).__name__)
        if component.get_owner() != actor or not library.is_instanced_component(data):
            raise RuntimeError('HISM ownership/instance creation not verified')
        if component not in actor.get_components_by_class(
                ue.HierarchicalInstancedStaticMeshComponent):
            raise RuntimeError('HISM absent from the actor component readback')
        return component

    def transform(self, row, scale):
        """By KEYWORD, never positionally.

        unreal.Transform's positional order is (rotation, translation, scale). Passing a
        location first silently produces a rotation and an instance at the origin, and an
        instance-count check would never see it. The first construction of a run is read back
        numerically before any other is built.
        """
        ue = self.ue
        x, y, z, yaw = float(row[0]), float(row[1]), float(row[2]), float(row[3])
        roll = float(row[5]) if len(row) > 5 else 0.0
        location = ue.Vector(x, y, z)
        rotation = ue.Rotator(pitch=0.0, yaw=yaw, roll=roll)
        if roll != 0.0:
            # a wash must face UP-and-out: the rolled local +Y must climb (checked, never assumed)
            right = rotation.get_right_vector()
            if not right.z > 0.69:
                raise RuntimeError('wash roll %g gives local +Y %s; it must tilt up' % (roll, right))
        scale3d = ue.Vector(scale, scale, scale)
        if self.transform_path is None:
            self.transform_path = 'keyword'
            try:
                probe = ue.Transform(rotation=rotation, translation=location, scale=scale3d)
                got = probe.get_editor_property('translation')
                if max(abs(got.x - x), abs(got.y - y), abs(got.z - z)) > 1e-3:
                    self.transform_path = 'set_editor_property'
            except Exception:                                          # noqa: BLE001
                self.transform_path = 'set_editor_property'
        if self.transform_path == 'keyword':
            return ue.Transform(rotation=rotation, translation=location, scale=scale3d)
        built = ue.Transform()
        built.set_editor_property('translation', location)
        built.set_editor_property('rotation', rotation.quaternion())
        built.set_editor_property('scale3d', scale3d)
        return built

    def place(self, plan):
        ue = self.ue
        actor = self.actors.spawn_actor_from_class(ue.Actor, ue.Vector(0.0, 0.0, 0.0),
                                                   ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0))
        if actor is None:
            raise RuntimeError('spawn_actor_from_class returned None')
        actor.set_actor_label(ACTOR_LABEL)
        actor.set_folder_path(ACTOR_FOLDER)
        # The spawned actor's DefaultSceneRoot is MOVABLE, and a STATIC component cannot be
        # attached to a movable parent - UE logs "AttachTo ... Aborting" and the component is
        # left unattached. Make the root static FIRST, so all four components attach.
        root = actor.get_editor_property('root_component')
        if root is not None:
            root.set_mobility(ue.ComponentMobility.STATIC)
        actor.set_editor_property('tags', [ue.Name(ACTOR_TAG)])
        rows_for = {'ApproachStepInstances': plan.steps,
                    'ApproachPavingInstances': plan.paving,
                    'ApproachRetainingInstances': plan.bands,
                    'ApproachKerbInstances': plan.kerbs}
        placed = {}
        try:
            for name, mesh_name, material_name, cast_shadow in COMPONENTS:
                mesh = ue.load_asset(MESH_FOLDER + '/' + mesh_name)
                material = ue.load_asset(MATERIAL_FOLDER + '/' + material_name)
                if mesh is None or material is None:
                    raise RuntimeError('Approved asset missing: %s / %s'
                                       % (mesh_name, material_name))
                component = self.new_hism(actor)
                component.set_editor_property('static_mesh', mesh)
                component.set_material(0, material)
                component.set_mobility(ue.ComponentMobility.STATIC)
                component.set_editor_property('cast_shadow', cast_shadow)
                rows = rows_for[name]
                transforms = [self.transform(row, plan.scale) for row in rows]
                if transforms:
                    try:
                        component.add_instances(transforms, False, True, False)
                    except TypeError:
                        component.add_instances(transforms, False)
                count = int(component.get_instance_count())
                if count != len(rows):
                    raise RuntimeError('%s: asked for %d instances, component reports %d'
                                       % (name, len(rows), count))
                placed[name] = dict(component=component.get_name(), mesh=_asset_path(mesh),
                                    material=_asset_path(material), castShadow=cast_shadow,
                                    instances=count)
        except Exception:
            self.actors.destroy_actor(actor)
            raise
        return actor, placed

    def read_components(self, actor):
        ue = self.ue
        found = {}
        for component in actor.get_components_by_class(
                ue.HierarchicalInstancedStaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            found[mesh.get_name() if mesh is not None else '?'] = component
        return found


def numeric_readback(ue, native, actor, plan, height, config):
    """THE ACCEPTANCE. Every number measured off the reopened level, never off the plan.

    * every component's instance count, and that no instance carries a non-uniform scale;
    * the head landing's top against the LIVE deck - the actor's own GetPlazaDeckTopZCm and
      the nearest placed deck-tile instance - so "meets the deck above" is proved against
      geometry rather than against the number this script wrote;
    * the foot tread against the LIVE terrain height field rebuilt after the reopen;
    * the longest unbroken rise between landings, from the placed instance Z values.
    """
    result = dict()
    by_mesh = native.read_components(actor)
    expected = {'SM_PlazaV1_Step': len(plan.steps), 'SM_PlazaV1_WayTile': len(plan.paving),
                'SM_PlazaV1_RetainingBand': len(plan.bands), 'SM_PlazaV1_Kerb': len(plan.kerbs)}
    counts = {}
    worst_scale = 0.0
    for mesh_name, want in expected.items():
        component = by_mesh.get(mesh_name)
        if component is None:
            raise RuntimeError('No HISM for %s on the reopened actor' % mesh_name)
        got = int(component.get_instance_count())
        counts[mesh_name] = dict(instances=got, expected=want,
                                 component=component.get_name())
        if got != want:
            raise RuntimeError('%s read back %d instances, the plan says %d'
                               % (mesh_name, got, want))
        # EVERY instance, not a sample: a single band stretched in Z would carry courses of
        # the wrong height on a face the whole design is about, and a sample of five would
        # miss it.
        for index in range(got):
            transform = component.get_instance_transform(index, True)
            scale3d = transform.get_editor_property('scale3d')
            worst_scale = max(worst_scale,
                              abs(scale3d.x - plan.scale), abs(scale3d.y - plan.scale),
                              abs(scale3d.z - plan.scale))
    result['components'] = counts
    result['worstScaleDeviationFromUniform'] = round(worst_scale, 9)
    if worst_scale > 1e-6:
        raise RuntimeError('An approach instance carries a non-uniform or wrong scale '
                           '(deviation %g); the ashlar course mapping v = world Z / 300 '
                           'forbids it' % worst_scale)

    # -- the deck above, from the precinct actor and from its own placed tiles --
    precinct = native.find_precinct()
    precinct.measure_without_hiding()
    deck_z = float(precinct.get_plaza_deck_top_z_cm())
    faces = precinct.get_outer_faces_cm()
    result['liveDeck'] = dict(
        plazaDeckTopZcm=round(deck_z, 6),
        plazaStatus=str(precinct.get_plaza_status()),
        outerFacesCm=[round(float(getattr(faces, axis)), 3) for axis in ('x', 'y', 'z', 'w')])
    deck_component = None
    for component in precinct.get_components_by_class(
            ue.HierarchicalInstancedStaticMeshComponent):
        mesh = component.get_editor_property('static_mesh')
        if mesh is not None and mesh.get_name() == 'SM_PlazaV1_DeckTile':
            deck_component = component
            break
    result['liveDeckTileComponent'] = (deck_component.get_name() if deck_component else None)

    approaches = []
    for record in plan.approaches:
        if not record.get('built'):
            approaches.append(dict(id=record['id'], built=False, reason=record.get('reason')))
            continue
        gx, gy = record['gateCm']
        row = dict(id=record['id'], side=record['side'], chosen=record['chosen'])

        # the deck, measured: the nearest placed deck tile to this gate
        nearest = None
        if deck_component is not None:
            best = None
            total = int(deck_component.get_instance_count())
            stride = max(1, total // 4000)
            for index in range(0, total, stride):
                transform = deck_component.get_instance_transform(index, True)
                location = transform.get_editor_property('translation')
                distance = (location.x - gx) ** 2 + (location.y - gy) ** 2
                if best is None or distance < best[0]:
                    best = (distance, index, location.x, location.y, location.z)
            if best is not None:
                nearest = dict(index=best[1], locationCm=[round(best[2], 3), round(best[3], 3),
                                                          round(best[4], 3)],
                               distanceCm=round(math.sqrt(best[0]), 2))
        row['nearestLiveDeckTile'] = nearest
        row['headLandingTopZcm'] = record['headLandingTopZcm']
        row['headLandingMinusLiveDeckCm'] = round(record['headLandingTopZcm'] - deck_z, 4)
        if nearest is not None:
            row['headLandingMinusNearestDeckTileCm'] = round(
                record['headLandingTopZcm'] - nearest['locationCm'][2], 4)

        # the street below, measured after the reopen
        fx, fy = record['footPointCm']
        ground = height(fx, fy)
        row['footZcm'] = record['footZcm']
        row['footGroundZcmAfterReopen'] = None if ground is None else round(ground, 3)
        row['footResidualCmAfterReopen'] = (None if ground is None
                                            else round(record['footZcm'] - ground, 3))
        cross = []
        for offset in (-0.5, -0.25, 0.0, 0.25, 0.5):
            direction = SIDE_OUTWARD[record['side']]
            tangent = (-direction[1], direction[0])
            axis = tangent if record['chosen'] == 'outward' else direction
            span = plan.width * offset
            z = height(fx + axis[0] * span, fy + axis[1] * span)
            cross.append(None if z is None else round(record['footZcm'] - z, 2))
        row['footResidualAcrossWidthCm'] = cross
        row['measuredFaceHeightMetres'] = record['measuredFaceHeightMetres']
        row['totalClimbMetres'] = record['totalClimbMetres']
        row['climbVersusFaceHeightMetres'] = round(
            record['totalClimbMetres'] - record['measuredFaceHeightMetres'], 2)
        row['maxUnbrokenRiseMetres'] = record['maxUnbrokenRiseMetres']
        row['runMetres'] = record['runMetres']
        row['risers'] = record['risers']
        row['landings'] = record['landings']
        row['terraces'] = record['terraces']
        row['maxBuriedCm'] = record['maxBuriedCm']
        approaches.append(row)
    result['approaches'] = approaches

    # THE LONGEST UNBROKEN RISE, recomputed from the PLACED step instances rather than from
    # the plan. The steps of every approach are appended in descent order, so the Z sequence
    # falls by one riser per tread and REPEATS on a landing (5 modules, or 25 on a terrace).
    # A run therefore ends at the first repeated level, and a level that goes UP is the start
    # of the next approach.
    step_component = by_mesh.get('SM_PlazaV1_Step')
    levels = []
    total = int(step_component.get_instance_count())
    for index in range(total):
        transform = step_component.get_instance_transform(index, True)
        levels.append(round(float(transform.get_editor_property('translation').z), 3))
    # Per APPROACH, using the instance ranges each one contributed, because the components are
    # shared: the first tread of one approach is often lower than the last tread of the one
    # before it, and a single pass over the whole component would run the two together. (It
    # did, on the first run of this pass: 29 risers reported across the boundary between the
    # east gate's foot and the south-west gate's head.)
    runs = []
    cursor = 0
    per_approach = {}
    for record in plan.approaches:
        if not record.get('built'):
            continue
        count = int(record['instances']['steps'])
        segment = levels[cursor:cursor + count]
        cursor += count
        best = 0
        run = 0
        previous = None
        for z in segment:
            if previous is None:
                run = 1
            elif abs(z - previous) <= 1e-6:
                run = 0                  # a landing: the unbroken rise is broken here
            elif z < previous - 1e-6:
                run += 1
            else:
                raise RuntimeError('%s: the placed step levels rise from %g to %g inside one '
                                   'approach; a descending flight cannot go up'
                                   % (record['id'], previous, z))
            best = max(best, run)
            previous = z
        per_approach[record['id']] = dict(steps=count, maxUnbrokenRisers=best,
                                          maxUnbrokenRiseCm=round(best * plan.riser, 2),
                                          maxUnbrokenRiseMetres=round(best * plan.riser / 100.0, 2))
        runs.append(best)
    if cursor != len(levels):
        raise RuntimeError('The step component holds %d instances; the approaches account for '
                           '%d' % (len(levels), cursor))
    result['maxUnbrokenRisePerApproach'] = per_approach
    longest = max(runs) if runs else 0
    result['maxUnbrokenRisersFromPlacedInstances'] = longest
    result['maxUnbrokenRiseCmFromPlacedInstances'] = round(longest * plan.riser, 2)
    result['maxUnbrokenRiseMetresFromPlacedInstances'] = round(longest * plan.riser / 100.0, 2)
    result['placedStepZRangeCm'] = [min(levels), max(levels)] if levels else None
    if longest > int(K['PlazaStepsPerFlight']):
        raise RuntimeError('The placed flights carry an unbroken run of %d risers; '
                           'PlazaStepsPerFlight is %d and a monumental stair with a longer '
                           'unbroken rise is neither buildable nor walkable'
                           % (longest, int(K['PlazaStepsPerFlight'])))
    worst_residual = max([abs(r['footResidualCmAfterReopen'])
                          for r in result['approaches']
                          if r.get('footResidualCmAfterReopen') is not None] or [0.0])
    result['worstFootResidualCmAfterReopen'] = round(worst_residual, 3)
    if worst_residual > 2.0 * plan.riser:
        raise RuntimeError('An approach foot stands %.1f cm from the live ground, more than '
                           'two risers (%.1f cm). A stair that stops short of the street is '
                           'the failure this pass exists to prevent.'
                           % (worst_residual, 2.0 * plan.riser))
    return result


def run(target_name, mode):
    import unreal as ue
    config = target_config(target_name)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    native = Native(ue, config, mode, '')
    if native.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
       ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed work')

    target_map = config['map']
    map_file = ROOT / config['mapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in config['protectedMaps']
                 if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    native.stamp = stamp
    native.receipt_path = REVIEW / ('native-approach-%s-%s-%s.json' % (mode, target_name, stamp))
    if native.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(native.receipt_path))

    checkpoint = None
    external_copied = []
    if mode in ('apply', 'revert'):
        checkpoint = CHECKPOINT_ROOT / ('PrecinctApproach-%s-%s' % (target_name, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / target_map[6:]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / target_map[6:])
                external_copied.append(str(external))

    native.receipt = {
        'status': 'started_' + mode,
        'mode': mode, 'stamp': stamp, 'target': target_name, 'map': target_map,
        'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint) if checkpoint else None,
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'scriptSha256': sha256_of(Path(__file__)),
        'enclosureMathSha256': HEADER_SHA256,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'actorLabel': ACTOR_LABEL, 'actorTag': ACTOR_TAG,
        'targetConfig': {k: v for k, v in config.items() if k != 'plazaGates'},
        'sourcedVersusAuthored': {
            'sourced': 'The gate count and side only (Mishkenei Elyon 196 m.2: two south, one '
                       'each north, east and west) and the precinct extent (Yechezkel 42:15-20 '
                       'with 40:5). NOTHING in Yechezkel, the Mishnah or the book describes an '
                       'approach to the precinct from outside.',
            'derivedFromMeasuredGeometry':
                'Every gate position, read from precinct-<Target>.json. The deck datum and '
                'paved extent, read from plaza-<Target>.json and re-read live off the placed '
                'AMikdashEnclosure actor. The ground outside the wall, measured triangle by '
                'triangle off the VISIBLE terrain meshes in this level, which is what decides '
                'each approach\'s direction, length, step count and where it stops.',
            'authored':
                'That the approach is a raking monumental stair at all; the 50-amah square '
                'head landing outside each gate; the rule that a flight goes straight out '
                'where the ground rises to meet it and rakes along the face where it does '
                'not; the landing rhythm (a 10-amah landing every 20 risers, a 50-amah '
                'terrace every fifth landing); the flanking retaining and kerbs; and that the '
                'wedge under the stair is left void, as the wedge under the deck already is.'},
        'limitations': [
            'GEOMETRY ONLY. NOBODY HAS SEEN ANY OF THIS IN A FRAME. Nothing here establishes '
            'visual, walking, collision, navigation or packaged acceptance.',
            'THE APPROACHES ARE NOT WIRED INTO THE STATE TOGGLE. They are a new actor, not '
            'components on AMikdashEnclosure, because that class has no UPROPERTY for them '
            'and this pass may not rebuild the plugin. GatherModernBuildings resolves an '
            'identity label only for meshes under JerusalemContext/Buildings/ or '
            'OldCityFacadesV1/Meshes/ (MikdashEnclosure.cpp:22-42), so no value in '
            'ExplicitHideLabels can reach a PlazaV1 mesh either. Until the plugin is rebuilt '
            'the approaches stand in MODERN and OVERLAY too - the SAME pending two lines the '
            'terrain cut already needs.',
            'THE WEDGE UNDER EACH STAIR IS VOID, closed by its flanking retaining. No vaults, '
            'no substructure, exactly as under the deck.',
            'THE APPROACHES CROSS GROUND THAT STILL CARRIES VISIBLE MODERN BUILDINGS. Nothing '
            'outside the precinct ring is hidden by this pass and no building is ever '
            'deleted. Which building actors stand under each approach is measured and listed '
            'in buildingsUnderApproach, not resolved.',
            'NO COLLISION OR NAVMESH PASS. The HISM components take the meshes\' own collision '
            'settings; nothing here has been walked.'],
        'runtimeDefectsObserved': [
            'MikdashEnclosure.cpp:1186 yaws the INSIDE gate flights by '
            'SideOutwardYawDegrees(Side) while advancing them along -Out. The step module is '
            '50 amot along local X and 2 amot along local Y, so that yaw lays the 50-amah '
            'WIDTH along the direction of travel: at the south side, yaw 90 with travel along '
            '-Y. The retaining bands four lines earlier use SideOutwardYawDegrees - 90, which '
            'is the correct convention. On Candidate48 that affects the 205 step modules of '
            'the east gate flight and the 10 of the west. FOUND BY READING, NOT SEEN IN A '
            'FRAME (the design record notes nobody has looked at the plaza yet). It is C++ '
            'and cannot be fixed without a plugin rebuild, which this pass may not run. '
            'Nothing in this file depends on it: the approaches are placed from Python with '
            'the band convention.'],
        'omissions': [], 'errors': [], 'mapSaved': False,
    }
    native.write_receipt()

    saved = False
    try:
        if not native.levels.load_level(target_map):
            raise RuntimeError('load_level failed for ' + target_map)
        loaded = native.editor.get_editor_world().get_outermost().get_name()
        if loaded != target_map:
            raise RuntimeError('Loaded world %s is not the target map %s' % (loaded, target_map))

        if mode == 'revert':
            actor = native.find_actor()
            native.receipt['actorFoundBeforeRevert'] = actor is not None
            if actor is not None:
                native.actors.destroy_actor(actor)
                if not native.levels.save_current_level():
                    raise RuntimeError('save_current_level returned False')
                saved = True
                native.receipt['mapSaved'] = True
                if not native.levels.load_level(target_map):
                    raise RuntimeError('Reopen failed')
                native.receipt['actorFoundAfterRevert'] = native.find_actor() is not None
                if native.receipt['actorFoundAfterRevert']:
                    raise RuntimeError('The approach actor survived the revert')
            native.receipt['status'] = 'approaches_reverted_saved_reopened'
            return native.receipt

        existing = native.find_actor()
        if existing is not None:
            if mode == 'apply':
                raise RuntimeError('%s is already in %s. Run -ApproachRevert first; this '
                                   'script never places a second one.'
                                   % (ACTOR_LABEL, target_map))
        elif mode == 'verify':
            raise RuntimeError('%s is not in %s; nothing to verify' % (ACTOR_LABEL, target_map))

        field, tiles = native.build_height_field(native.regions_of_interest())
        native.receipt['terrainTilesRead'] = tiles
        native.receipt['terrainTrianglesRead'] = field.triangles
        native.write_receipt()

        plan = Plan(config).build(field.height)
        native.receipt['plan'] = dict(summary=plan.summary(), approaches=[
            {k: v for k, v in a.items()} for a in plan.approaches])
        native.write_receipt()

        if mode == 'apply':
            actor, placed = native.place(plan)
            native.receipt['placed'] = placed
            native.write_receipt()
            if not native.levels.save_current_level():
                raise RuntimeError('save_current_level returned False')
            saved = True
            native.receipt['mapSaved'] = True
            native.receipt['mapSha256AfterSave'] = sha256_of(map_file)
            native.write_receipt()
            if not native.levels.load_level(target_map):
                raise RuntimeError('Reopen failed')

        reopened = native.find_actor()
        if reopened is None:
            raise RuntimeError('The approach actor is not in the reopened level')
        after_field, after_tiles = native.build_height_field(native.regions_of_interest())
        native.receipt['terrainTilesReadAfterReopen'] = len(after_tiles)
        native.receipt['readback'] = numeric_readback(ue, native, reopened, plan,
                                                      after_field.height, config)
        native.receipt['buildingsUnderApproach'] = buildings_under(ue, native, plan)
        native.receipt['status'] = (
            'approaches_placed_saved_reopened_measured_visual_acceptance_pending'
            if mode == 'apply' else 'approaches_measured_map_unchanged')
    except Exception as error:
        native.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        native.receipt['status'] = ('FAILED_AFTER_SAVE_CHECKPOINT_AVAILABLE' if saved
                                    else 'FAILED_BEFORE_SAVE_MAP_UNCHANGED')
        raise
    finally:
        native.receipt['mapSha256After'] = sha256_of(map_file)
        native.receipt['mapBytesChanged'] = native.receipt['mapSha256After'] != map_sha_before
        native.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        if mode == 'verify' and native.receipt['mapBytesChanged']:
            native.receipt['errors'].append(
                {'stage': 'finally', 'error': '-ApproachVerify must not change the map, and it did.'})
        native.write_receipt()
    return native.receipt


def buildings_under(ue, native, plan):
    """Which VISIBLE modern building actors stand under an approach footprint.

    Reported, never resolved: nothing outside the precinct ring is hidden by this pass. The
    footprint is the axis-aligned box of the approach's placed step and paving instances,
    which is a slight over-count on a rake that is not axis-aligned - and every rake in this
    plan is axis-aligned, because every side of the precinct is.
    """
    boxes = []
    labelled = []
    for record in plan.approaches:
        if not record.get('built'):
            continue
        points = [record['gateCm'], record['headLandingCentreCm'], record['footPointCm']]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        box = (min(xs) - plan.width, min(ys) - plan.width,
               max(xs) + plan.width, max(ys) + plan.width)
        boxes.append(box)
        labelled.append(dict(id=record['id'], boxCm=[round(v, 1) for v in box]))
    rows = []
    for actor in native.actors.get_all_level_actors():
        if actor is None:
            continue
        component = actor.get_component_by_class(ue.StaticMeshComponent)
        if component is None:
            continue
        mesh = component.get_editor_property('static_mesh')
        if mesh is None:
            continue
        name = mesh.get_name()
        if 'Building' not in name and 'Facade' not in name:
            continue
        if bool(actor.get_editor_property('hidden')):
            continue
        origin, extent = actor.get_actor_bounds(False)
        box = (origin.x - extent.x, origin.y - extent.y, origin.x + extent.x, origin.y + extent.y)
        if any(box[0] <= b[2] and b[0] <= box[2] and box[1] <= b[3] and b[1] <= box[3]
               for b in boxes):
            rows.append(actor.get_actor_label())
    return dict(footprintBoxesCm=labelled,
                visibleBuildingActorsOverlapping=len(rows), labels=sorted(rows)[:40],
                note='Reported, not hidden. Nothing outside the precinct ring is hidden by '
                     'this pass and no actor is ever deleted.')


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def flag_from(command_line, table, what):
    lowered = ' %s ' % command_line.lower()
    chosen = [name for flag, name in table.items()
              if (' %s ' % flag) in lowered or ('%s=' % flag) in lowered]
    if len(chosen) > 1:
        raise RuntimeError('Choose exactly one %s: %s' % (what, list(table)))
    return chosen[0] if chosen else None


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    target_name = flag_from(command_line, TARGET_FLAGS, 'target')
    mode = flag_from(command_line, MODE_FLAGS, 'mode')
    if not target_name:
        raise RuntimeError('Choose the target map with one of %s (Candidate48 first: it is '
                           'the configured default and the cook map)' % list(TARGET_FLAGS))
    if not mode:
        raise RuntimeError('Choose exactly one mode: %s' % list(MODE_FLAGS))
    try:
        receipt = run(target_name, mode)
        ue.log('release_precinct_approaches[%s/%s]: %s'
               % (target_name, mode, receipt['status']))
    except Exception as error:
        ue.log_error('release_precinct_approaches failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and \
           '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_precinct_approaches.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        import sys
        argv = ' '.join(sys.argv[1:])
        name = flag_from(argv, TARGET_FLAGS, 'target')
        if not name:
            raise SystemExit('Choose the target map with one of %s' % list(TARGET_FLAGS))
        print(json.dumps(offline_plan(name, '--level-grid' in sys.argv), indent=1))
elif _invoked_as_native_script():
    _main()
