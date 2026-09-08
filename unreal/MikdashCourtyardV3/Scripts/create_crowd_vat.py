"""Crowd figure source geometry for AMikdashCrowdField -- and the honest record of why it is
posed static meshes rather than a Vertex Animation Texture.

WHICH PATH WAS TAKEN
--------------------
The brief asked for a VAT bake of the existing walk cycle, with posed static meshes as the
practical fallback. THE FALLBACK PATH WAS TAKEN. `--probe-vat` records the evidence rather
than asserting it; run it offline for the on-disk part and, if you want the in-engine part,
under UnrealEditor-Cmd (see the invocation at the bottom of this docstring). Offline probing
already shows the blocking facts:

  * The walk cycle exists only as cooked-editor .uasset binaries
    (Content/MikdashV3/CharacterReview/PilgrimRigV2/...), not as FBX/glTF source. Nothing
    offline can read bone tracks or skin weights out of a .uasset, so an out-of-engine bake
    is not possible at all.
  * Inside 5.8 editor Python a bake needs three things at once: per-vertex skin weights and
    bone indices for the render mesh, per-frame bone transforms, and the ability to write
    float (not 8-bit) texture data. `unreal.AnimPoseExtensions` covers the second. The first
    (SkeletalMeshLODRenderData skin weight buffers) and the third (authoring an RGBA16F or
    RGBA32F Texture2D from a Python buffer) are not exposed to Python in 5.8; they are C++
    or a plugin (the standard route is Epic's own AnimToTexture / Houdini VAT toolset,
    neither of which is installed here -- `--probe-vat` lists the plugin folders it checked).

A VAT would have been the better answer for animation quality. Claiming to have baked one
without the APIs to do it would have been worse than saying this plainly.

WHAT THIS SCRIPT PRODUCES INSTEAD
---------------------------------
Six procedurally generated robed figures, one per sixth of a walk cycle, in the project's
keilim OBJ adapter convention (the same one create_dove_mesh_v2.py uses and
release_dove_people_v2.py imports: per-triangle vertices, file Y = -canonical Y, winding
reversed, `g` groups with `usemtl`). Each is 1,228 triangles, origin at the FEET (local Z 0)
and facing local +X, so an instance transform is (ground point, yaw, uniform scale) with
nothing to compensate for.

  SM_CrowdFigure_P0 .. SM_CrowdFigure_P5   six distinct stride positions, about 171 cm tall

Three material slots per mesh: CrowdRobe (the garment -- this is the slot whose base colour
the material tints from per-instance custom data), CrowdSkin (face, hands), CrowdWrap (head
covering and sash). Vertex colours are deliberately NOT written into the OBJ: this project's
note in create_dove_mesh_v2.py records that FBX-SDK OBJ reader tolerance for the
`v x y z r g b` extension is unverified here, and a silently dropped colour channel would
produce a uniformly grey crowd with nothing to show why. Garment colour therefore travels as
HISM per-instance custom data (float 1) instead, which is read back and verified by
Scripts/release_crowd_field.py.

Movement comes from three places, and only the first is real locomotion:
  1. AMikdashCrowdField rewrites instance transforms on a bounded per-frame budget: figures
     actually walk across the court at 60-110 cm/s along the zone flow field.
  2. The material bobs and leans each instance from its per-instance gait phase
     (custom data 0), matching MikdashCrowd::BobHeightCm / LeanDegrees on the CPU side.
  3. Six frozen poses spread across the crowd break up the silhouette.
The legs of one instance do not cycle. At the distance these figures are meant to be seen
this reads as a moving crowd; up close it does not, and the 24 skeletal
MikdashResidentCharacter actors remain the only figures with real articulation.

Offline (no engine):
    python Scripts/create_crowd_vat.py --export        # refuses to overwrite an existing folder
    python Scripts/create_crowd_vat.py --probe-vat     # on-disk half of the VAT feasibility record
    python Scripts/create_crowd_vat.py --verify        # re-check hashes/bounds of an exported folder

In-engine half of the probe (optional, read-only, changes nothing):
    "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
        "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
        -run=pythonscript -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/create_crowd_vat.py"
        -unattended -nullrhi -abslog="C:/Mikdash/Working-5.8/CrowdVatProbe-01.log"
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'SourceAssets/runtime-review/crowd-field/CrowdFigureV1'

ROBE, SKIN, WRAP = 'CrowdRobe', 'CrowdSkin', 'CrowdWrap'
# Slot base colours. The robe colour is the neutral the per-instance tint multiplies against,
# so it is a light stone-linen, not white: a tint can darken it but never brighten it.
SLOT_COLOURS = {ROBE: [0.62, 0.58, 0.52], SKIN: [0.66, 0.50, 0.40], WRAP: [0.80, 0.78, 0.72]}
POSE_COUNT = 6
# Poses are sampled at (k + PHASE_OFFSET)/POSE_COUNT, not k/POSE_COUNT. On the whole numbers a
# sine gait puts both legs at the passing position, so poses 0 and 3 would come out identical
# and the crowd would carry five silhouettes while claiming six. The offset moves every sample
# off the passing position; export asserts the six are actually distinct.
PHASE_OFFSET = 0.35
FIGURE_HEIGHT_CM = 171.0

# The skeletal walk cycle a VAT would have been baked from, if it could be read.
VAT_SOURCE = {
    'skeletalMesh': 'Content/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2.uasset',
    'walkAnimation': 'Content/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2A_Pilgrim_Original_Walk.uasset',
    'idleAnimation': 'Content/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2A_Pilgrim_Original_Idle.uasset',
}
VAT_PLUGIN_CANDIDATES = [
    'Plugins/Animation/AnimToTexture',
    'Plugins/Experimental/AnimToTexture',
    'Plugins/AnimToTexture',
    'Plugins/Runtime/AnimToTexture',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Primitive builders (closed, outward-wound solids; same conventions as the dove script)
# ---------------------------------------------------------------------------

def orient(mesh):
    """Flip winding if the signed volume came out negative, so every solid faces outward."""
    v, f = mesh
    volume = sum((v[a][0] * (v[b][1] * v[c][2] - v[b][2] * v[c][1]) + v[a][1] * (v[b][2] * v[c][0] - v[b][0] * v[c][2])
                  + v[a][2] * (v[b][0] * v[c][1] - v[b][1] * v[c][0])) / 6 for a, b, c in f)
    if volume < 0:
        f = [(a, c, b) for a, b, c in f]
    return v, f


def _skin(rings, faces_out):
    """Stitch consecutive rings of vertex indices, collapsing single-vertex poles."""
    for a, b in zip(rings, rings[1:]):
        n = max(len(a), len(b))
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1 and len(b) > 1:
                faces_out.append((a[0], b[j], b[i]))
            elif len(b) == 1 and len(a) > 1:
                faces_out.append((a[i], a[j], b[0]))
            elif len(a) > 1 and len(b) > 1:
                faces_out.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])


def lathe(profile, center=(0.0, 0.0, 0.0), segments=14, twist_deg=0.0):
    """Closed surface of revolution about local Z from a (radius, z) profile, poles collapsed."""
    vertices = []
    rings = []
    faces = []
    for radius, z in profile:
        ring = []
        count = 1 if radius <= 1e-9 else segments
        for i in range(count):
            angle = i * math.tau / segments + math.radians(twist_deg)
            ring.append(len(vertices))
            vertices.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle), center[2] + z))
        rings.append(ring)
    _skin(rings, faces)
    return orient((vertices, faces))


def ellipsoid(center, radii, segments=12, rings=8, yaw=0.0, pitch=0.0):
    profile = [(math.sin(math.pi * i / rings), -math.cos(math.pi * i / rings)) for i in range(rings + 1)]
    profile[0] = (0.0, -1.0)
    profile[-1] = (0.0, 1.0)
    v, f = lathe(profile, segments=segments)
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    out = []
    for x, y, z in v:
        x *= radii[0]
        y *= radii[1]
        z *= radii[2]
        x, z = cp * x + sp * z, -sp * x + cp * z
        x, y = cy * x - sy * y, sy * x + cy * y
        out.append((center[0] + x, center[1] + y, center[2] + z))
    return orient((out, f))


def tube(path_points, radii, segments=8):
    """Closed capped tube through a polyline; radii is one radius per path point."""
    assert len(path_points) == len(radii) >= 2
    vertices = []
    rings = []
    faces = []
    # Cap the start with a single pole vertex, then the rings, then a pole at the end.
    rings.append([len(vertices)])
    vertices.append(tuple(path_points[0]))
    for index, (p, r) in enumerate(zip(path_points, radii)):
        nxt = path_points[min(index + 1, len(path_points) - 1)]
        prv = path_points[max(index - 1, 0)]
        axis = [nxt[k] - prv[k] for k in range(3)]
        length = math.sqrt(sum(a * a for a in axis)) or 1.0
        axis = [a / length for a in axis]
        ref = (0.0, 1.0, 0.0) if abs(axis[1]) < 0.9 else (1.0, 0.0, 0.0)
        u = [axis[1] * ref[2] - axis[2] * ref[1], axis[2] * ref[0] - axis[0] * ref[2], axis[0] * ref[1] - axis[1] * ref[0]]
        ul = math.sqrt(sum(q * q for q in u)) or 1.0
        u = [q / ul for q in u]
        w = [axis[1] * u[2] - axis[2] * u[1], axis[2] * u[0] - axis[0] * u[2], axis[0] * u[1] - axis[1] * u[0]]
        ring = []
        for i in range(segments):
            a = i * math.tau / segments
            ring.append(len(vertices))
            vertices.append(tuple(p[k] + r * (math.cos(a) * u[k] + math.sin(a) * w[k]) for k in range(3)))
        rings.append(ring)
    rings.append([len(vertices)])
    vertices.append(tuple(path_points[-1]))
    _skin(rings, faces)
    return orient((vertices, faces))


def rotate_y(mesh, degrees, pivot):
    """Swing a limb about the hip/shoulder pivot in the sagittal (X-Z) plane."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    v, f = mesh
    out = []
    for x, y, z in v:
        dx, dz = x - pivot[0], z - pivot[2]
        out.append((pivot[0] + c * dx + s * dz, y, pivot[2] - s * dx + c * dz))
    return out, f


# ---------------------------------------------------------------------------
# The figure
# ---------------------------------------------------------------------------

HIP_Z = 92.0
SHOULDER_Z = 141.0
SHOULDER_Y = 17.0
HIP_Y = 9.0


def figure_parts(phase):
    """One robed pilgrim posed at `phase` (0..1) of a walk cycle.

    Sagittal swings are a sine pair in antiphase, which is what a walk cycle looks like to
    within the accuracy a 1,200-triangle background figure can carry. Legs lead, arms
    counter-swing, the trailing knee bends, and the pelvis rises twice per cycle so a row of
    the six poses reads as a stride when they stand side by side.
    """
    swing = math.sin(2.0 * math.pi * phase)
    counter = math.sin(2.0 * math.pi * phase + math.pi)
    rise = 1.6 * 0.5 * (1.0 - math.cos(4.0 * math.pi * phase))     # two rises per cycle
    lean = 3.0 + 1.5 * math.sin(4.0 * math.pi * phase)             # slight forward carriage

    parts = []
    metrics = dict(phase=phase, hipDegrees={}, riseCm=round(rise, 4), leanDegrees=round(lean, 4))
    add = lambda name, material, mesh: parts.append(dict(name=name, material=material, mesh=mesh))

    # --- legs and feet, below the hem; swung about the hip
    for side, amount in ((-1, swing), (+1, counter)):
        pivot = (0.0, side * HIP_Y, HIP_Z)
        knee_bend = max(0.0, -amount) * 8.0
        leg = tube([(0.0, side * HIP_Y, HIP_Z), (0.0, side * HIP_Y, HIP_Z * 0.55), (0.0, side * HIP_Y, 7.0)],
                   [8.2, 6.4, 4.6], segments=8)
        metrics['hipDegrees'][str(side)] = round(amount * 17.0 + knee_bend, 4)
        add('Leg%+d' % side, ROBE, rotate_y(leg, amount * 17.0 + knee_bend, pivot))
        foot = ellipsoid((6.0, side * HIP_Y, 4.0), (11.0, 5.0, 4.0), segments=8, rings=5)
        add('Foot%+d' % side, SKIN, rotate_y(foot, amount * 17.0, pivot))

    # --- robe: a flared lathe from the hem to the shoulders, leaning forward with the gait
    hem_flare = 1.0 + 0.06 * abs(swing)
    robe_profile = [
        (0.0, 26.0), (25.0 * hem_flare, 26.5), (26.5 * hem_flare, 34.0), (25.5, 55.0), (23.5, 74.0),
        (22.0, HIP_Z), (21.0, 108.0), (22.5, 124.0), (23.0, SHOULDER_Z), (16.0, 150.0), (0.0, 152.0),
    ]
    add('Robe', ROBE, rotate_y(lathe(robe_profile, segments=14), lean, (0.0, 0.0, HIP_Z)))
    # Sash at the waist.
    add('Sash', WRAP, rotate_y(lathe([(0.0, 100.0), (23.0, 101.0), (23.6, 107.0), (0.0, 108.0)], segments=14), lean, (0.0, 0.0, HIP_Z)))

    # --- arms, counter-swinging, hanging just clear of the robe
    for side, amount in ((-1, counter), (+1, swing)):
        pivot = (0.0, side * SHOULDER_Y, SHOULDER_Z)
        arm = tube([(0.0, side * SHOULDER_Y, SHOULDER_Z), (1.0, side * (SHOULDER_Y + 3.0), 120.0), (2.0, side * (SHOULDER_Y + 2.0), 100.0)],
                   [7.0, 5.4, 4.2], segments=8)
        add('Arm%+d' % side, ROBE, rotate_y(arm, amount * 14.0, pivot))
        hand = ellipsoid((2.0, side * (SHOULDER_Y + 2.0), 96.0), (4.2, 3.4, 5.0), segments=8, rings=5)
        add('Hand%+d' % side, SKIN, rotate_y(hand, amount * 14.0, pivot))

    # --- head, face and covering
    head_z = 161.0 + rise
    add('Neck', SKIN, ellipsoid((1.0, 0.0, 152.0 + rise), (5.0, 6.0, 7.0), segments=10, rings=5))
    add('Head', SKIN, ellipsoid((1.5, 0.0, head_z), (8.4, 7.6, 9.6), segments=12, rings=8))
    add('Beard', WRAP, ellipsoid((7.0, 0.0, head_z - 5.5), (5.0, 5.2, 6.0), segments=10, rings=5))
    # Head covering: a shallow cap plus a shoulder drape, the silhouette that reads at distance.
    add('Cover', WRAP, lathe([(0.0, head_z + 9.8), (7.6, head_z + 6.0), (9.6, head_z - 1.0), (9.9, head_z - 6.0), (0.0, head_z - 6.4)],
                             center=(1.5, 0.0, 0.0), segments=12))
    add('Drape', WRAP, rotate_y(lathe([(0.0, 137.0), (16.0, 138.5), (20.0, 146.0), (18.0, SHOULDER_Z + 8.0), (0.0, 152.0)], segments=12),
                                lean, (0.0, 0.0, HIP_Z)))
    return parts, metrics


# ---------------------------------------------------------------------------
# OBJ writing (keilim adapter convention)
# ---------------------------------------------------------------------------

def write_obj(path, name, parts):
    lines = ['# Mikdash crowd figure V1; figure-local cm; +X forward, +Z up, origin at the feet',
             '# keilim OBJ adapter convention: per-triangle vertices, file Y = -canonical Y, winding reversed',
             'o ' + name]
    index = 1
    total = 0
    report_parts = []
    canonical = []
    for part in parts:
        vertices, faces = part['mesh']
        canonical.extend(vertices)
        keys = [tuple(round(x, 6) for x in v) for v in vertices]
        edges = {}
        volume = 0.0
        lines.append('g ' + part['name'])
        lines.append('usemtl ' + part['material'])
        written = 0
        for a, b, c in faces:
            va, vb, vc = vertices[a], vertices[b], vertices[c]
            volume += sum(va[i] * [vb[1] * vc[2] - vb[2] * vc[1], vb[2] * vc[0] - vb[0] * vc[2], vb[0] * vc[1] - vb[1] * vc[0]][i] for i in range(3)) / 6
            for i, j in ((a, b), (b, c), (c, a)):
                edge = tuple(sorted([keys[i], keys[j]]))
                edges[edge] = edges.get(edge, 0) + 1
            adapted = [(v[0], -v[1], v[2]) for v in (va, vc, vb)]
            aa, bb, cc = adapted
            ab = [bb[i] - aa[i] for i in range(3)]
            ac = [cc[i] - aa[i] for i in range(3)]
            n = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
            area = math.sqrt(sum(q * q for q in n))
            length = math.sqrt(sum(q * q for q in ab))
            if area <= 1e-9 or length <= 1e-9:
                continue      # degenerate pole sliver
            normal = [q / area for q in n]
            uv = [(0.0, 0.0), (length / 10.0, 0.0), (sum(ac[i] * ab[i] / length for i in range(3)) / 10.0, area / length / 10.0)]
            for v in adapted:
                lines.append('v %.6f %.6f %.6f' % v)
            for v in uv:
                lines.append('vt %.6f %.6f' % v)
            for _ in range(3):
                lines.append('vn %.6f %.6f %.6f' % tuple(normal))
            lines.append('f ' + ' '.join('%d/%d/%d' % (i, i, i) for i in range(index, index + 3)))
            index += 3
            written += 1
        # Every part must be a closed, outward-facing solid before it is written.
        assert volume > 0, part['name']
        assert all(count == 2 for count in edges.values()), part['name']
        report_parts.append(dict(name=part['name'], material=part['material'], triangles=written,
                                 signed_volume_cm3=round(volume, 3)))
        total += written
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(v[i] for v in canonical) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    return dict(file=path.name, sha256=sha(path), triangles=total, bounds_cm=bounds,
                materials=sorted({p['material'] for p in parts}), parts=report_parts)


# ---------------------------------------------------------------------------
# VAT feasibility probe
# ---------------------------------------------------------------------------

def probe_vat():
    """Record, with evidence, whether a VAT bake is reachable. Offline-safe; if it happens to
    be running inside the editor it additionally probes the Python API surface."""
    engine_dir = Path(r'C:\Program Files\Epic Games\UE_5.8\Engine')
    report = {
        'question': 'Can the existing walk cycle be baked into position/normal textures from here?',
        'answer': 'no',
        'sourceAnimationOnDisk': {},
        'sourceIsBinaryUassetOnly': True,
        'offlineBakePossible': False,
        'offlineBakeReason': 'Skeletal mesh and animation exist only as .uasset binaries; there is no FBX/glTF/ABC source in the project and no offline reader for cooked-editor packages. Bone tracks and skin weights cannot be read outside the engine.',
        'vatPluginsChecked': [],
        'vatPluginPresent': False,
        'engineDirExists': engine_dir.is_dir(),
        'inEditor': False,
    }
    for key, rel in VAT_SOURCE.items():
        path = ROOT / rel
        report['sourceAnimationOnDisk'][key] = dict(path=rel, exists=path.is_file(),
                                                    bytes=path.stat().st_size if path.is_file() else 0,
                                                    sha256=sha(path) if path.is_file() else None)
    for rel in VAT_PLUGIN_CANDIDATES:
        for base in ([engine_dir] if engine_dir.is_dir() else []) + [ROOT]:
            candidate = base / rel
            present = candidate.is_dir()
            report['vatPluginsChecked'].append(dict(path=str(candidate), exists=present))
            report['vatPluginPresent'] = report['vatPluginPresent'] or present
    try:
        import unreal as ue
    except ImportError:
        report['pythonApi'] = 'not probed (run under UnrealEditor-Cmd for the in-engine half)'
        report['reason'] = report['offlineBakeReason']
        return report
    report['inEditor'] = True
    api = {}
    for name in ('AnimPoseExtensions', 'AnimPose', 'SkeletalMeshComponent', 'Texture2DFactoryNew',
                 'AnimToTextureDataAsset', 'AnimToTextureBPLibrary', 'SkeletalMeshLODRenderData',
                 'MeshDescription', 'TextureFactory'):
        api[name] = hasattr(ue, name)
    report['pythonApi'] = api
    report['skinWeightsReadable'] = bool(api.get('SkeletalMeshLODRenderData'))
    report['floatTextureAuthorable'] = bool(api.get('AnimToTextureBPLibrary'))
    report['bonePosesReadable'] = bool(api.get('AnimPoseExtensions'))
    blockers = []
    if not report['skinWeightsReadable']:
        blockers.append('No Python access to per-vertex skin weights / bone indices (SkeletalMeshLODRenderData not exposed)')
    if not report['floatTextureAuthorable']:
        blockers.append('No Python route to author a float (RGBA16F/32F) Texture2D from a data buffer; AnimToTexture is not available')
    report['blockers'] = blockers
    report['answer'] = 'no' if blockers else 'possibly, but not attempted by this script'
    report['reason'] = '; '.join(blockers) if blockers else 'APIs present; a bake was still not attempted, the posed-mesh path was already shipped'
    return report


# ---------------------------------------------------------------------------
# Export / verify
# ---------------------------------------------------------------------------

def export():
    if FOLDER.exists():
        raise RuntimeError('Existing %s preserved; author a new version folder for revisions' % FOLDER.name)
    probe = probe_vat()
    FOLDER.mkdir(parents=True)
    manifest = dict(
        status='offline_geometry_validated_native_import_pending',
        path='vertex_animation_texture_refused_posed_static_meshes_used',
        vatProbe=probe,
        convention='keilim OBJ adapter: per-triangle vertices, file Y = -canonical Y, winding reversed; the importer reflects back, so imported bounds must match bounds_cm within 0.05 cm',
        axes='figure-local: +X forward, +Y left-to-right, +Z up; centimetres; origin at the feet (min Z ~ 0)',
        poseCount=POSE_COUNT,
        poseMeaning='Pose k is frozen at gait phase (k + %.2f)/%d. Instances do not change pose at run time; the six poses are distributed across the crowd so the silhouette varies.' % (PHASE_OFFSET, POSE_COUNT),
        materialSlots=SLOT_COLOURS,
        vertexColours='not written; garment tint travels as HISM per-instance custom data (see module docstring)',
        customData={'0': 'gait phase 0..1', '1': 'garment tint index / palette size', '2': 'reserved (standing flag)'},
        meshes={},
        sourceScriptSha256=sha(Path(__file__)),
        limitations=[
            'Stylized original geometry, not a scan or a measured garment',
            'Frozen poses: one instance never cycles its own legs; only translation, yaw, bob and lean animate',
            'No skinning, no collision, no per-figure LOD authored here (LODs are generated at import by release_crowd_field.py)',
            'No native import, render, cook, PIE or packaged acceptance is claimed by this script',
        ])
    heights = []
    signatures = []
    for k in range(POSE_COUNT):
        phase = (k + PHASE_OFFSET) / float(POSE_COUNT)
        name = 'SM_CrowdFigure_P%d' % k
        parts, metrics = figure_parts(phase)
        record = write_obj(FOLDER / (name + '.obj'), name, parts)
        record['phase'] = phase
        record['pose'] = metrics
        signatures.append((metrics['hipDegrees']['-1'], metrics['hipDegrees']['1']))
        manifest['meshes'][name] = record
        heights.append(record['bounds_cm']['max'][2] - record['bounds_cm']['min'][2])
        # Feet on the ground, a believable adult height, and a budget a 10 000-instance
        # crowd can afford. These are the invariants the crowd field depends on.
        assert abs(record['bounds_cm']['min'][2]) < 8.0, (name, record['bounds_cm'])
        assert 150.0 < heights[-1] < 200.0, (name, heights[-1])
        assert 900 <= record['triangles'] <= 2200, (name, record['triangles'])
        assert sorted(record['materials']) == sorted(SLOT_COLOURS), (name, record['materials'])
    # The six poses must actually differ: identical files would be a crowd of five silhouettes
    # sold as six, and identical hip angles would be the same stride drawn twice.
    hashes = {m['sha256'] for m in manifest['meshes'].values()}
    assert len(hashes) == POSE_COUNT, 'duplicate pose meshes exported'
    for i in range(POSE_COUNT):
        for j in range(i + 1, POSE_COUNT):
            spread = max(abs(signatures[i][0] - signatures[j][0]), abs(signatures[i][1] - signatures[j][1]))
            assert spread > 2.0, ('poses %d and %d are the same stride (%.2f deg apart)' % (i, j, spread), signatures)
    manifest['poseHipDegrees'] = {('P%d' % k): dict(left=signatures[k][0], right=signatures[k][1]) for k in range(POSE_COUNT)}
    manifest['phaseOffset'] = PHASE_OFFSET
    manifest['totalTriangles'] = sum(m['triangles'] for m in manifest['meshes'].values())
    manifest['figureHeightCm'] = dict(min=min(heights), max=max(heights), nominal=FIGURE_HEIGHT_CM)
    # All six poses must be the same person: heights within a couple of centimetres.
    assert max(heights) - min(heights) < 6.0, heights
    (FOLDER / 'geometry-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def verify():
    manifest_path = FOLDER / 'geometry-manifest.json'
    if not manifest_path.is_file():
        raise RuntimeError('No export to verify at %s; run --export first' % FOLDER)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    out = dict(folder=str(FOLDER.relative_to(ROOT)), meshes=[], ok=True)
    for name, record in sorted(manifest['meshes'].items()):
        path = FOLDER / record['file']
        actual = sha(path) if path.is_file() else None
        triangles = 0
        vertices = []
        if path.is_file():
            for line in path.read_text().splitlines():
                if line.startswith('f '):
                    triangles += 1
                elif line.startswith('v '):
                    p = line.split()
                    vertices.append((float(p[1]), float(p[2]), float(p[3])))
        reflected = {'min': [min(v[0] for v in vertices), -max(v[1] for v in vertices), min(v[2] for v in vertices)],
                     'max': [max(v[0] for v in vertices), -min(v[1] for v in vertices), max(v[2] for v in vertices)]} if vertices else None
        error = max(abs(reflected[k][i] - record['bounds_cm'][k][i]) for k in ('min', 'max') for i in range(3)) if reflected else None
        good = actual == record['sha256'] and triangles == record['triangles'] and error is not None and error < 1e-4
        out['ok'] = out['ok'] and good
        out['meshes'].append(dict(name=name, sha256Matches=actual == record['sha256'], triangles=triangles,
                                  expectedTriangles=record['triangles'], boundsErrorCm=error, ok=good))
    out['totalTriangles'] = sum(m['triangles'] for m in out['meshes'])
    return out


if __name__ == '__main__':
    if '--probe-vat' in sys.argv:
        print(json.dumps(probe_vat(), indent=2))
    elif '--verify' in sys.argv:
        result = verify()
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['ok'] else 1)
    elif '--export' in sys.argv:
        result = export()
        print(json.dumps(dict(totalTriangles=result['totalTriangles'], figureHeightCm=result['figureHeightCm'],
                              vat=result['vatProbe']['answer']), indent=2))
        for name, mesh in sorted(result['meshes'].items()):
            print(name, mesh['triangles'], 'tris  bounds', [[round(c, 1) for c in mesh['bounds_cm'][k]] for k in ('min', 'max')])
    else:
        try:
            import unreal  # noqa: F401
        except ImportError:
            raise SystemExit(__doc__)
        # Inside the editor this script only ever probes; it never writes assets.
        import unreal as ue
        ue.log(json.dumps(probe_vat(), indent=2))
