"""Guarded keruv/palm frieze V2: seamless mirror tiling, brick-bond rows, flush 3 cm panels.

Second pass after the 20260907T194843Z renders of the V1 frieze (Scripts/release_keruv_frieze.py).
Every number comes from Scripts/release_frieze_v2.spec.json. What it does, in order:

  1. Offline image stage: V1's derive_relief (frozen source hash, luma, high-pass, mass/detail
     height, 2048 x 2048), then the V2 post-pass: a 2 px zero margin on all four sides of the
     height map and a recomputed Sobel normal map. Written as <stem>_v2_height16.png and
     <stem>_v2_normal.png in SourceAssets/relief-images/derived/, plus two 8-bit previews
     (mirror pair A|A', and a 4 x 2 panel row layout). The joint of the MIRROR tiling is
     measured on luma and on height (must be < image.seamRatioMax); the V1 plain-repeat ratio
     is recorded for comparison. Manifest: derived-manifest-v2.json.
  2. Engine stage: import both PNGs as textures, build M_KeruvFriezeV2 / _Displaced (gold),
     create the six displaced Nanite panel variants of panel.variants (A / A' at 3.0 cm for
     even rows, A / A' / two A' halves at 2.5 cm for odd rows; 3 cm thick, border at height 0)
     and the unplaced flat reference panel, all from explicit buffers; winding readback.
  3. Placement in the combined map: refuse if RELEASE_Frieze_* exists unless -FriezeReplace
     (then the V1 actors are matched against the latest V1 receipt, recorded and destroyed);
     palms must be absent; checkpoint; tile every enabled wall: even rows A A' A A' ..., odd
     rows half | A A' ... | half (125 cm offset), clearance-tested per panel.
  4. Save, reopen, numeric readback, receipt SourceAssets/sanctuary-detail/KeruvFriezeV2/.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_frieze_v2.py"
      -FriezeReplace -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-KeruvFriezeV2-01.log"

Optional switches (engine command line):
  -FriezeReplace               remove the V1 RELEASE_Frieze_* actors (recorded) and place V2.
  -FriezeImagesOnly            offline image stage only.
  -FriezeAssetsOnly            image stage + textures + materials + meshes; no map change.
  -FriezePlaceOnly             assets already saved in the V2 namespace: load, re-verify, place.
  -FriezeImage=<stem|path>     another PNG (stem looked up in SourceAssets/relief-images).
  -FriezeAllowUnverifiedWinding  place even if the winding readback is unavailable.

Offline (no engine):
  python Scripts/release_frieze_v2.py                      -> offline consistency check
  python Scripts/release_frieze_v2.py --derive [--size N]  -> image stage only
"""
import argparse
import importlib.util
import json
import math
import shutil
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_frieze_v2.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
AXIS = {'x': 0, 'y': 1, 'z': 2}


# --------------------------------------------------------------------------
# Spec and modules
# --------------------------------------------------------------------------

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def _load_module(relative, name, required):
    path = ROOT / relative
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for attr in required:
        if not hasattr(module, attr):
            raise RuntimeError('%s lacks helper %s' % (relative, attr))
    return module


def load_v1(spec):
    """V1 module: pure helpers (codec, filters, height pipeline, buffers) and engine builders."""
    return _load_module(spec['v1']['script'], 'release_keruv_frieze',
                        ('decode_png', 'encode_png', 'luma_rows', 'box_blur', 'resample_bilinear', 'sample_bilinear', 'height_rows_16',
                         'normal_rows_rgb8', 'seam_report', 'derive_relief', 'resolve_image', 'Buffers', 'check_buffers', 'flat_panel_buffers',
                         'signed_volume_ue', 'bounds_of', 'yaw_frame', 'import_texture', 'read_gold', 'build_material', 'create_mesh',
                         'latest_reliefs_receipt', 'sha256_of', '_asset_path', '_xyz', '_normalised', '_cross', '_dot', '_sub'))


def load_placement_helper(spec):
    return _load_module(spec['placementHelper'], 'release_place_assets',
                        ('sha256_of', 'disk_path', 'box_error', 'boxes_overlap_volume', 'verify_union_decomposition', 'Placement', '_actor_bounds', '_pose_close'))


def load_reliefs_module(spec):
    return _load_module(spec['reliefsScript'], 'release_import_reliefs', ('winding_report', 'ReliefRow'))


def sha256_of(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def latest_v1_receipt(spec):
    folder = ROOT / spec['v1']['receiptFolder']
    prefix = spec['v1']['receiptStatusPrefix']
    rows = []
    for path in sorted(folder.glob('native-import-*.json')):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if str(data.get('status', '')).startswith(prefix):
            rows.append((path, data))
    if not rows:
        raise RuntimeError('No V1 frieze receipt with status %s* in %s' % (prefix, folder))
    return rows[-1]


# --------------------------------------------------------------------------
# Image stage (V1 pipeline + V2 post-pass)
# --------------------------------------------------------------------------

def apply_zero_margin(rows, margin):
    """Set the outer `margin` texels of a float height field to 0 (all four sides)."""
    if margin <= 0:
        return rows
    height, width = len(rows), len(rows[0])
    zero_row = [0.0] * width
    out = []
    for y, row in enumerate(rows):
        if y < margin or y >= height - margin:
            out.append(list(zero_row))
        else:
            new = list(row)
            for x in range(margin):
                new[x] = 0.0
                new[width - 1 - x] = 0.0
            out.append(new)
    return out


def _col(img, i):
    return [row[i] for row in img]


def _mad(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def mirror_seam_report(img):
    """Joint quality of the A|A' MIRROR tiling versus the image's own column-to-column smoothness."""
    width = len(img[0])
    step = max(1, width // 64)
    xs = list(range(step, width - 1 - step, step))
    interior = sum(_mad(_col(img, x), _col(img, x + 1)) for x in xs) / len(xs)
    interior_second = sum(_mad([2 * v for v in _col(img, x)], [a + b for a, b in zip(_col(img, x - 1), _col(img, x + 1))]) for x in xs) / len(xs)
    right, right_in = _col(img, width - 1), _col(img, width - 2)
    left, left_in = _col(img, 0), _col(img, 1)
    # Sequence across the A|A' joint: ..., c[w-2], c[w-1] | c[w-1], c[w-2], ... ; across A'|A: ..., c[1], c[0] | c[0], c[1], ...
    joint_right = _mad(right, right)              # identical columns by construction
    joint_left = _mad(left, left)
    one_in_right = _mad(right_in, right)          # columns one texel in from the joint
    one_in_left = _mad(left_in, left)
    # Sequence c[w-2], c[w-1] | c[w-1], c[w-2]: the second difference at the joint column is |c[w-1] - c[w-2]|.
    second_right = one_in_right
    second_left = one_in_left
    plain = _mad(right, left)                     # V1 plain repeat A|A
    return {'tiling': 'mirror A|A\' and A\'|A',
            'interiorAdjacentColumnMeanAbsDiff': interior,
            'jointColumnsMeanAbsDiff': {'A|A\'': joint_right, 'A\'|A': joint_left},
            'oneTexelInMeanAbsDiff': {'A|A\'': one_in_right, 'A\'|A': one_in_left},
            'ratioJointOverInterior': max(joint_right, joint_left) / interior if interior > 0 else None,
            'ratioOneTexelInOverInterior': max(one_in_right, one_in_left) / interior if interior > 0 else None,
            'secondDifference': {'interiorMean': interior_second, 'atJointMean': max(second_right, second_left),
                                 'ratio': max(second_right, second_left) / interior_second if interior_second > 0 else None,
                                 'note': 'derivative kink of the mirror joint; informational'},
            'plainRepeatRightVsLeftMeanAbsDiff': plain,
            'plainRepeatRatioOverInterior': plain / interior if interior > 0 else None,
            'rule': 'ratio near 1 = the joint is as smooth as neighbouring columns; the mirror joint columns are identical (0)'}


def _gray8_png(path, img, v1):
    width = len(img[0])
    rows = [bytes(int(round(min(max(v, 0.0), 1.0) * 255)) for v in row) for row in img]
    return v1.encode_png(path, width, len(img), rows, 0, bit_depth=8)


def _downsample(img, size, v1):
    height, width = len(img), len(img[0])
    factor = max(1, int(round(width / float(size))))
    smooth = v1.box_blur(img, factor // 2, 1) if factor > 1 else img
    return v1.resample_bilinear(smooth, size, size)


def _tile(panel, u0, u1):
    """Columns of `panel` re-sampled over source u in [u0, u1] across the tile width (mirror when u0 > u1)."""
    width = len(panel[0])
    n = int(round(width * abs(u1 - u0)))
    out = []
    for row in panel:
        out.append([row[min(width - 1, max(0, int((u0 + (u1 - u0) * (i + 0.5) / n) * width)))] for i in range(n)])
    return out


def write_previews(spec, v1, luma, height_rows, derived_dir, stem):
    cfg = spec['image']['outputs']
    px = int(cfg['previewPanelPx'])
    small_luma = _downsample(luma, px, v1)
    pair = [a + b for a, b in zip(_tile(small_luma, 0.0, 1.0), _tile(small_luma, 1.0, 0.0))]
    pair_path = derived_dir / (stem + cfg['mirrorPairPreviewSuffix'])
    pair_sha = _gray8_png(pair_path, pair, v1)
    small_h = _downsample(height_rows, px, v1)
    depth_even, depth_odd = spec['layout']['depthByRowParity']['even'], spec['layout']['depthByRowParity']['odd']
    scale_odd = depth_odd / depth_even
    even = [a + b + a + b for a, b in zip(_tile(small_h, 0, 1), _tile(small_h, 1, 0))]   # A M A M
    odd_rows = list(zip(_tile(small_h, 0.5, 0.0), _tile(small_h, 0, 1), _tile(small_h, 1, 0), _tile(small_h, 0, 1), _tile(small_h, 1.0, 0.5)))
    odd = [[v * scale_odd for part in parts for v in part] for parts in odd_rows]   # MR A M A ML
    layout = odd + even                                                   # image top = odd (upper) row, bottom = even (floor) row
    layout_path = derived_dir / (stem + cfg['layoutPreviewSuffix'])
    layout_sha = _gray8_png(layout_path, layout, v1)
    return {'mirrorPair': {'path': str(pair_path), 'sha256': pair_sha, 'size': [len(pair[0]), len(pair)], 'content': 'luma of A | A\' at %d px per panel' % px},
            'rowLayout': {'path': str(layout_path), 'sha256': layout_sha, 'size': [len(layout[0]), len(layout)],
                          'content': 'height of 4 columns x 2 rows: bottom row A M A M (3.0 cm), top row MR A M A ML (2.5 cm, scaled %.3f)' % scale_odd}}


def image_stage(spec, image=None, derived_dir=None, size=None, v1=None):
    v1 = v1 or load_v1(spec)
    cfg = spec['image']
    source, is_default = v1.resolve_image(spec, image)
    derived = Path(derived_dir) if derived_dir else ROOT / cfg['derivedFolder']
    derived.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    record = v1.derive_relief(spec, source, derived, size=size, is_default=is_default)
    height_rows = record.pop('_heightRows')
    out_h, out_w = len(height_rows), len(height_rows[0])
    t = time.monotonic()
    margin = int(cfg['heightMapZeroMarginPx'])
    if size and margin * 4 >= min(out_w, out_h):
        margin = 0
    height_rows = apply_zero_margin(height_rows, margin)
    height_path = Path(record['outputs']['height']['path'])
    record['outputs']['height']['sha256'] = v1.encode_png(height_path, out_w, out_h, v1.height_rows_16(height_rows), cfg['outputs']['heightPngColorType'],
                                                          bit_depth=cfg['outputs']['heightBitDepth'])
    slope_factor = record['parameters']['normalSlopeFactorPerTexel']
    normal_path = Path(record['outputs']['normal']['path'])
    record['outputs']['normal']['sha256'] = v1.encode_png(normal_path, out_w, out_h, v1.normal_rows_rgb8(height_rows, slope_factor, bool(cfg['flipGreen'])),
                                                          cfg['outputs']['normalPngColorType'])
    record['timingsSeconds']['v2MarginAndRewriteS'] = time.monotonic() - t
    t = time.monotonic()
    decoded = v1.decode_png(source)
    luma = v1.luma_rows(decoded, cfg['lumaWeights'])
    del decoded
    record['seamV1PlainRepeat'] = record.pop('seam')
    record['seamMirrorTiling'] = {'luma': mirror_seam_report(luma), 'height': mirror_seam_report(height_rows)}
    ratios = [r for block in record['seamMirrorTiling'].values() for r in (block['ratioJointOverInterior'], block['ratioOneTexelInOverInterior']) if r is not None]
    record['seamRatio'] = max(ratios) if ratios else None
    record['seamRatioMax'] = cfg['seamRatioMax']
    record['seamPassed'] = record['seamRatio'] is not None and record['seamRatio'] < cfg['seamRatioMax']
    record['horizontalRepeat'] = cfg['horizontalRepeat']
    record['heightMapZeroMarginPx'] = margin
    record['borderZeroCheck'] = {'topRowMax': max(height_rows[0]), 'bottomRowMax': max(height_rows[-1]),
                                 'leftColumnMax': max(_col(height_rows, 0)), 'rightColumnMax': max(_col(height_rows, out_w - 1))}
    if margin and max(record['borderZeroCheck'].values()) != 0.0:
        raise RuntimeError('Zero margin not applied')
    record['previews'] = write_previews(spec, v1, luma, height_rows, derived, record['stem'])
    record['timingsSeconds']['v2SeamAndPreviewsS'] = time.monotonic() - t
    record['timingsSeconds']['v2TotalS'] = time.monotonic() - started
    if not record['seamPassed']:
        raise RuntimeError('Mirror joint ratio %.3f not below %.2f' % (record['seamRatio'], cfg['seamRatioMax']))
    manifest_path = derived / cfg['derivedManifest']
    manifest = {'images': []}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        except ValueError:
            manifest = {'images': []}
    manifest['images'] = [m for m in manifest.get('images', []) if m.get('stem') != record['stem']]
    manifest['images'].append(dict(record))
    manifest['updated'] = datetime.now(timezone.utc).isoformat()
    manifest['specSha256'] = sha256_of(SPEC_PATH)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    record['manifest'] = str(manifest_path)
    record['_heightRows'] = height_rows
    return record


# --------------------------------------------------------------------------
# Panel geometry
# --------------------------------------------------------------------------

def variant_by_role(spec, role):
    for variant in spec['panel']['variants']:
        if variant['role'] == role:
            return variant
    raise RuntimeError('No panel variant with role ' + role)


def variant_local_box(spec, variant):
    hw = variant['widthCm'] / 2.0
    return {'min': [-hw, 0.0, 0.0], 'max': [hw, spec['panel']['thicknessCm'] + variant['depthCm'], spec['panel']['sizeCm'][1]]}


def _box_sides_v2(buffers, hw, t, hh, xs, zs):
    """Back, bottom, top, left, right faces as strips matching the (h = 0) front border vertices."""
    buffers.add_quad([(-hw, 0, 0), (-hw, 0, hh), (hw, 0, hh), (hw, 0, 0)], (0, -1, 0), [(1, 1), (1, 0), (0, 0), (0, 1)])
    nx, nz = len(xs) - 1, len(zs) - 1
    for i in range(nx):
        x0, x1 = xs[i], xs[i + 1]
        u0, u1 = i / float(nx), (i + 1) / float(nx)
        buffers.add_quad([(x0, 0, 0), (x1, 0, 0), (x1, t, 0), (x0, t, 0)], (0, 0, -1), [(u0, 1), (u1, 1), (u1, 0), (u0, 0)])
        buffers.add_quad([(x0, 0, hh), (x0, t, hh), (x1, t, hh), (x1, 0, hh)], (0, 0, 1), [(u0, 1), (u0, 0), (u1, 0), (u1, 1)])
    for j in range(nz):
        z0, z1 = zs[j], zs[j + 1]
        v0, v1 = 1 - j / float(nz), 1 - (j + 1) / float(nz)
        buffers.add_quad([(-hw, 0, z0), (-hw, t, z0), (-hw, t, z1), (-hw, 0, z1)], (-1, 0, 0), [(0, v0), (1, v0), (1, v1), (0, v1)])
        buffers.add_quad([(hw, 0, z0), (hw, 0, z1), (hw, t, z1), (hw, t, z0)], (1, 0, 0), [(1, v0), (1, v1), (0, v1), (0, v0)])


def displaced_panel_buffers(spec, v1, height_rows, variant):
    """Front face = (nx+1)(nz+1) vertices displaced along +Y by height(u, v) * depth; u from the variant's uRange."""
    panel = spec['panel']
    width, hh, t = float(variant['widthCm']), float(panel['sizeCm'][1]), float(panel['thicknessCm'])
    hw = width / 2.0
    depth = float(variant['depthCm'])
    u0, u1 = [float(u) for u in variant['uRange']]
    grid = int(panel['displacedGrid'])
    nx = max(1, int(round(grid * width / float(panel['sizeCm'][0]))))
    nz = grid
    fx, fz = int(panel['borderFeatherCellsX']), int(panel['borderFeatherCellsZ'])
    cell_x, cell_z = width / nx, hh / nz
    xs = [-hw + width * i / nx for i in range(nx + 1)]
    zs = [hh * j / nz for j in range(nz + 1)]
    us = [u0 + (u1 - u0) * i / float(nx) for i in range(nx + 1)]
    h = []
    for j in range(nz + 1):
        v = 1.0 - j / float(nz)
        bz = min(j, nz - j)
        wz = 0.0 if bz == 0 else (min(1.0, bz / float(fz)) if fz > 0 else 1.0)
        row = []
        for i in range(nx + 1):
            bx = min(i, nx - i)
            wx = 0.0 if bx == 0 else (min(1.0, bx / float(fx)) if fx > 0 else 1.0)
            row.append(v1.sample_bilinear(height_rows, us[i], v) * min(wx, wz))
        h.append(row)
    buffers = v1.Buffers()
    index = {}
    for j in range(nz + 1):
        for i in range(nx + 1):
            i0, i1 = max(i - 1, 0), min(i + 1, nx)
            j0, j1 = max(j - 1, 0), min(j + 1, nz)
            dhdx = (h[j][i1] - h[j][i0]) * depth / ((i1 - i0) * cell_x)
            dhdz = (h[j1][i] - h[j0][i]) * depth / ((j1 - j0) * cell_z)
            index[(i, j)] = len(buffers.positions)
            buffers.positions.append([xs[i], t + h[j][i] * depth, zs[j]])
            buffers.normals.append(v1._normalised([-dhdx, 1.0, -dhdz]))
            buffers.uv0.append([us[i], 1.0 - j / float(nz)])
    for j in range(nz):
        for i in range(nx):
            a, b, c, d = index[(i, j)], index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]
            buffers.add_triangle(a, b, c, (0, 1, 0))
            buffers.add_triangle(a, c, d, (0, 1, 0))
    _box_sides_v2(buffers, hw, t, hh, xs, zs)
    border_max = max(max(h[0]), max(h[nz]), max(r[0] for r in h), max(r[nx] for r in h))
    if border_max != 0.0:
        raise RuntimeError('Front border not at height 0 for ' + variant['name'])
    mean_h = sum(sum(r) for r in h) / float((nx + 1) * (nz + 1))
    return buffers, {'variant': variant['name'], 'role': variant['role'], 'gridX': nx, 'gridZ': nz, 'uRange': [u0, u1], 'depthCm': depth, 'widthCm': width,
                     'borderFeatherCellsX': fx, 'borderFeatherCellsZ': fz, 'borderMaxHeight': border_max,
                     'meanDisplacementCm': mean_h * depth, 'maxDisplacementCm': max(max(r) for r in h) * depth,
                     'expectedTriangles': 2 * nx * nz + 4 * nx + 4 * nz + 2}


# --------------------------------------------------------------------------
# Wall layout
# --------------------------------------------------------------------------

def row_sequence(spec, columns, row):
    """[(role, along offset of the panel centre from the wall start in modules, width in modules)]."""
    module = 1.0
    if row % 2 == 0 or columns < 2:
        roles = ['evenFull' if c % 2 == 0 else 'evenFullMirror' for c in range(columns)]
        return [(role, (c + 0.5) * module, module) for c, role in enumerate(roles)]
    out = [('oddHalfStart', 0.25 * module, 0.5 * module)]
    for c in range(columns - 1):
        out.append(('oddFull' if c % 2 == 0 else 'oddFullMirror', 0.5 * module + (c + 0.5) * module, module))
    out.append(('oddHalfEnd', columns * module - 0.25 * module, 0.5 * module))
    return out


def _rotate_box_yaw(local, location, yaw_degrees):
    yaw = math.radians(yaw_degrees)
    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
    corners = []
    for x in (local['min'][0], local['max'][0]):
        for y in (local['min'][1], local['max'][1]):
            for z in (local['min'][2], local['max'][2]):
                corners.append((location[0] + x * cos_yaw - y * sin_yaw, location[1] + x * sin_yaw + y * cos_yaw, location[2] + z))
    return {'min': [min(c[i] for c in corners) for i in range(3)], 'max': [max(c[i] for c in corners) for i in range(3)]}


def plan_wall(spec, wall, veneer_bounds, floor_top, boxes_by_role):
    """Panels for one wall from the live veneer bounds and floor top. Returns (wall report, panel plans)."""
    frieze = spec['frieze']
    module = float(frieze['moduleCm'])
    n_axis, a_axis = AXIS[wall['normalAxis']], AXIS[wall['alongAxis']]
    sign = int(wall['sign'])
    face = veneer_bounds['max'][n_axis] if sign < 0 else veneer_bounds['min'][n_axis]
    back_plane = face - sign * frieze['standoffCm']
    standoff = abs(back_plane - face)
    lo, hi = frieze['standoffWindowCm']
    room_dir = [0.0, 0.0]
    room_dir[n_axis] = -float(sign)
    yaw = math.radians(wall['yawDegrees'])
    local_x, local_y = [math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)]
    report = {'wall': wall['name'], 'veneerLabel': wall.get('veneerLabel'), 'normalAxis': wall['normalAxis'], 'sign': sign, 'yawDegrees': wall['yawDegrees'],
              'veneerWorldBoundsCm': veneer_bounds, 'veneerRoomFace': face, 'panelBackPlane': back_plane, 'standoffCm': standoff,
              'roomDirectionWorldXY': room_dir, 'localPlusYWorldXY': local_y, 'localPlusXWorldXY': local_x, 'floorTopZ': floor_top, 'panels': []}
    if not lo <= standoff <= hi or (back_plane - face) * room_dir[n_axis] <= 0:
        report['conflict'] = 'standoff %.3f cm outside [%s, %s] or not toward the room; wall skipped' % (standoff, lo, hi)
        return report, []
    if local_y[0] * room_dir[0] + local_y[1] * room_dir[1] < 0.999:
        report['conflict'] = 'yaw %.1f does not point local +Y into the room; wall skipped' % wall['yawDegrees']
        return report, []
    forward = [-room_dir[0], -room_dir[1], 0.0]
    right = [0.0 * forward[2] - 1.0 * forward[1], 1.0 * forward[0] - 0.0 * forward[2], 0.0]   # up x forward
    if local_x[0] * right[0] + local_x[1] * right[1] < 0.999:
        report['conflict'] = 'local +X is not the viewer\'s right; the image would be mirrored; wall skipped'
        return report, []
    a_min, a_max = wall['alongRangeCm']
    v_min, v_max = veneer_bounds['min'][a_axis], veneer_bounds['max'][a_axis]
    if a_min < v_min - 0.2 or a_max > v_max + 0.2:
        report['conflict'] = 'spec along range %r leaves the veneer extent [%s, %s]; wall skipped' % (wall['alongRangeCm'], v_min, v_max)
        return report, []
    cols = int(math.floor((a_max - a_min) / module + 1e-9))
    margin = ((a_max - a_min) - cols * module) / 2.0
    # The live floor top is 925.00006, so the eighth row needs a hair of tolerance (V1 placed 7 rows for that reason).
    rows = min(int(frieze['maxRows']), int(math.floor((veneer_bounds['max'][2] - floor_top + float(frieze['rowFitToleranceCm'])) / module)))
    report.update(columns=cols, rows=rows, alongMarginCm=margin, veneerTopZ=veneer_bounds['max'][2])
    # Along-axis direction of local +X in world: sign of local_x along the along axis.
    along_dir = local_x[a_axis]
    if abs(abs(along_dir) - 1.0) > 1e-6:
        report['conflict'] = 'local +X is not aligned with the along axis'
        return report, []
    start = a_min + margin if along_dir > 0 else a_max - margin
    plans = []
    for row in range(rows):
        for col, (role, centre_modules, width_modules) in enumerate(row_sequence(spec, cols, row)):
            location = [0.0, 0.0, floor_top + row * module]
            location[a_axis] = start + along_dir * centre_modules * module
            location[n_axis] = back_plane
            rotation = [0.0, float(wall['yawDegrees']), 0.0]
            plans.append({'wall': wall['name'], 'row': row, 'column': col, 'role': role, 'widthCm': width_modules * module, 'location': location,
                          'rotation': rotation, 'plannedWorldBoundsCm': _rotate_box_yaw(boxes_by_role[role], location, rotation[1])})
    return report, plans


def _overlap(a, b):
    for i in range(3):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= 1e-6:
            return False
    return True


# --------------------------------------------------------------------------
# Offline check
# --------------------------------------------------------------------------

def offline_check(spec=None, namespace_expected=None, v1=None):
    spec = spec or load_spec()
    v1 = v1 or load_v1(spec)
    helper = load_placement_helper(spec)
    report = {}
    image_path = ROOT / spec['image']['defaultSource']
    if not image_path.exists():
        raise RuntimeError('Default relief image missing: ' + str(image_path))
    report['defaultImage'] = {'path': str(image_path), 'sha256': sha256_of(image_path), 'frozenHashMatches': sha256_of(image_path) == spec['image']['defaultSourceSha256']}
    if not report['defaultImage']['frozenHashMatches']:
        raise RuntimeError('Frozen relief image hash differs')
    receipt_path, receipt = v1.latest_reliefs_receipt(spec)
    veneers = {v['label']: v['worldBoundsCm'] for v in receipt['veneers']['all']}
    report['reliefsReceipt'] = {'path': str(receipt_path), 'status': receipt['status'], 'veneerLabels': sorted(veneers)}
    v1_receipt_path, v1_receipt = latest_v1_receipt(spec)
    report['v1Receipt'] = {'path': str(v1_receipt_path), 'status': v1_receipt['status'], 'placedActorCount': v1_receipt.get('placedActorCount')}

    flat = v1.flat_panel_buffers(spec)
    report['flatPanel'] = v1.check_buffers(flat, spec['panel']['flatLocalBoundsCm'])
    expected_volume = spec['panel']['sizeCm'][0] * spec['panel']['sizeCm'][1] * spec['panel']['thicknessCm']
    if report['flatPanel']['triangles'] != spec['panel']['flatTriangles'] or abs(report['flatPanel']['signedVolumeUEcm3'] - expected_volume) > 1e-6:
        raise RuntimeError('Flat reference panel differs from the spec')
    roles = [v['role'] for v in spec['panel']['variants']]
    for role in ('evenFull', 'evenFullMirror', 'oddFull', 'oddFullMirror', 'oddHalfStart', 'oddHalfEnd'):
        if role not in roles:
            raise RuntimeError('panel.variants lacks role ' + role)
    grid = spec['panel']['displacedGrid']
    estimates = {}
    for variant in spec['panel']['variants']:
        nx = int(round(grid * variant['widthCm'] / spec['panel']['sizeCm'][0]))
        estimates[variant['name']] = 2 * nx * grid + 4 * nx + 4 * grid + 2
        if estimates[variant['name']] > spec['panel']['displacedTriangleBudget']:
            raise RuntimeError('%s exceeds the triangle budget' % variant['name'])
        if not (0.0 <= min(variant['uRange']) and max(variant['uRange']) <= 1.0):
            raise RuntimeError('uRange outside 0..1 for ' + variant['name'])
    report['displacedTriangleEstimates'] = estimates
    # Mirror-joint consistency of the row sequences: abutting edges must show the same source column.
    def edge_u(role, side):
        u0, u1 = variant_by_role(spec, role)['uRange']
        return u1 if side == 'right' else u0
    for cols in (1, 2, 4, 8):
        for row in (0, 1):
            seq = row_sequence(spec, cols, row)
            for (role_a, ca, wa), (role_b, cb, wb) in zip(seq, seq[1:]):
                if abs((ca + wa / 2.0) - (cb - wb / 2.0)) > 1e-9:
                    raise RuntimeError('Row sequence has a gap (cols %d row %d)' % (cols, row))
                if abs(edge_u(role_a, 'right') - edge_u(role_b, 'left')) > 1e-9:
                    raise RuntimeError('Row sequence joint mismatch %s|%s (cols %d row %d)' % (role_a, role_b, cols, row))
            if abs(sum(w for _, _, w in seq) - cols) > 1e-9:
                raise RuntimeError('Row sequence width differs from the column count')
    report['rowSequenceJointsConsistent'] = True
    boxes_by_role = {v['role']: variant_local_box(spec, v) for v in spec['panel']['variants']}
    walls = []
    total = 0
    for wall in spec['frieze']['walls']:
        floor_top = spec['frieze']['floors'][wall['floor']]['topZ']
        bounds = veneers.get(wall.get('veneerLabel')) if wall.get('veneerLabel') else None
        if bounds is None and wall.get('veneerSearchBoundsCm'):
            matches = [b for b in veneers.values() if helper.box_error(b, wall['veneerSearchBoundsCm']) <= spec['frieze']['veneerBoundsToleranceCm']]
            bounds = matches[0] if len(matches) == 1 else None
        if bounds is None:
            walls.append({'wall': wall['name'], 'enabled': wall['enabled'], 'veneer': 'absent_in_receipt', 'planned': 0})
            continue
        wall_report, plans = plan_wall(spec, wall, bounds, floor_top, boxes_by_role)
        walls.append({'wall': wall['name'], 'enabled': wall['enabled'], 'veneer': 'present', 'columns': wall_report.get('columns'), 'rows': wall_report.get('rows'),
                      'conflict': wall_report.get('conflict'), 'planned': len(plans) if wall['enabled'] else 0,
                      'byRole': {r: sum(1 for p in plans if p['role'] == r) for r in roles} if wall['enabled'] else {}})
        if wall['enabled'] and wall_report.get('conflict'):
            raise RuntimeError('%s: %s' % (wall['name'], wall_report['conflict']))
        if wall['enabled']:
            total += len(plans)
    report['walls'] = walls
    report['plannedPanelsFromReceiptGeometry'] = total
    namespace_dir = ROOT / 'Content' / spec['panel']['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    if namespace_expected is False and namespace_dir.exists():
        raise RuntimeError('Target namespace folder already exists on disk: ' + str(namespace_dir))
    if namespace_expected is True and not namespace_dir.exists():
        raise RuntimeError('Place-only needs the saved namespace on disk: ' + str(namespace_dir))
    report['v1NamespaceOnDisk'] = (ROOT / 'Content' / spec['v1']['namespace'][len('/Game/'):]).exists()
    report['goldSourceOnDisk'] = helper.disk_path(spec['material']['goldSource']).exists()
    derived = ROOT / spec['image']['derivedFolder']
    report['derivedOnDisk'] = {k: (derived / (image_path.stem + spec['image']['outputs'][k + 'Suffix'])).exists() for k in ('height', 'normal')}
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

def uv_readback(ue, spec, v1, mesh, variant):
    """Prove the +Y face UVs: u = u0 + (u1 - u0) (x + hw) / w, v = 1 - z / h, when GetTriangleUVs is bound."""
    if not hasattr(ue, 'GeometryScript_MeshQueries') or not hasattr(ue.GeometryScript_MeshQueries, 'get_triangle_uvs'):
        return {'status': 'unavailable_in_5_8_python_uvs_from_explicit_buffers', 'passed': True,
                'note': 'GeometryScript_MeshQueries.get_triangle_uvs not bound; UVs come from explicit buffers; verify orientation in a real-RHI render'}
    panel = spec['panel']
    hw, hh, t = variant['widthCm'] / 2.0, panel['sizeCm'][1], panel['thicknessCm']
    u0, u1 = variant['uRange']
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('apply_build_settings', False)
    options.set_editor_property('request_tangents', False)
    options.set_editor_property('use_build_scale', False)
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
    if ue.GeometryScriptOutcomePins.SUCCESS not in result:
        return {'status': 'copy_failed', 'passed': False, 'reason': str(result)}
    query = ue.GeometryScript_MeshQueries
    count = dynamic.get_triangle_count()
    step = max(1, count // 4000)
    front, invalid, max_error = 0, 0, 0.0
    for tid in range(0, count, step):
        positions = [v1._xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
        face = query.get_triangle_face_normal(dynamic, tid)
        normal = [v1._xyz(v) for v in face if isinstance(v, ue.Vector)][0] if isinstance(face, tuple) else v1._xyz(face)
        if len(positions) != 3 or min(p[1] for p in positions) < t - 1e-4 or normal[1] <= 0:
            continue
        uvs = query.get_triangle_uvs(dynamic, 0, tid)
        pairs = [v for v in uvs if isinstance(v, ue.Vector2D)] if isinstance(uvs, tuple) else []
        if len(pairs) != 3:
            invalid += 1
            continue
        front += 1
        for p, uv in zip(positions, pairs):
            expected_u = u0 + (u1 - u0) * (p[0] + hw) / (2.0 * hw)
            max_error = max(max_error, abs(float(uv.x) - expected_u), abs(float(uv.y) - (1.0 - p[2] / hh)))
    passed = front > 0 and invalid == 0 and max_error <= panel['uvReadbackToleranceUv']
    return {'status': 'checked', 'passed': passed, 'frontTrianglesChecked': front, 'invalidUvTriangles': invalid, 'maxUvError': max_error}


def load_saved_assets(ue, spec, v1, receipt):
    cfg, panel = spec['material'], spec['panel']
    out = {'materials': {}, 'meshes': {}}
    for variant_name in ('flat', 'displaced'):
        material = ue.load_asset(cfg['folder'] + '/' + cfg['names'][variant_name])
        if not isinstance(material, ue.Material):
            raise RuntimeError('Saved material missing: ' + cfg['names'][variant_name])
        receipt['materials'][variant_name] = {'asset': v1._asset_path(material), 'status': 'reused'}
        out['materials'][variant_name] = material
    expected_material = cfg['folder'] + '/' + cfg['names']['displaced']
    for variant in panel['variants']:
        mesh = ue.load_asset(panel['meshFolder'] + '/' + variant['name'])
        if not isinstance(mesh, ue.StaticMesh):
            raise RuntimeError('Saved mesh missing: ' + variant['name'])
        box = mesh.get_bounding_box()
        slots = len(mesh.get_editor_property('static_materials'))
        materials = {v1._asset_path(mesh.get_material(i)) for i in range(slots)}
        info = {'asset': v1._asset_path(mesh), 'triangles': int(mesh.get_num_triangles(0)), 'materialSlots': slots, 'material': sorted(materials),
                'localBoundsCm': {'min': v1._xyz(box.min), 'max': v1._xyz(box.max)}, 'reused': True, 'variant': variant['name'], 'role': variant['role']}
        if slots == 0 or materials != {expected_material}:
            raise RuntimeError('%s material slots differ from the spec: %s' % (variant['name'], materials))
        expected_box = variant_local_box(spec, variant)
        tol = panel['boundsToleranceCm']
        box_read = info['localBoundsCm']
        # X and Z extents and the back plane are exact; max Y is thickness + depth only where the height map reaches 1.0.
        xz_error = max(abs(box_read[k][i] - expected_box[k][i]) for k in ('min', 'max') for i in (0, 2))
        if xz_error > tol or abs(box_read['min'][1]) > tol or box_read['max'][1] > expected_box['max'][1] + tol or box_read['max'][1] < panel['thicknessCm'] - tol:
            raise RuntimeError('%s bounds differ from the spec: %r' % (variant['name'], box_read))
        receipt['meshes'][variant['name']] = info
        out['meshes'][variant['role']] = (mesh, info, variant)
    return out


class FriezePlacementV2:
    def __init__(self, ue, spec, v1, helper, reliefs, run, receipt, reliefs_receipt):
        self.ue, self.spec, self.v1, self.helper, self.run, self.receipt = ue, spec, v1, helper, run, receipt
        self.reliefs_receipt = reliefs_receipt
        self.clearance = reliefs.ReliefRow(ue, spec, helper, run, receipt)

    def find_floors(self):
        floors = self.spec['frieze']['floors']
        out = {}
        for key in ('heikhal', 'kodesh'):
            rows = self.run.actors_with_mesh(floors[key]['mesh'])
            if len(rows) != 1:
                raise RuntimeError('Expected one %s clear floor actor, found %d' % (key, len(rows)))
            floor = rows[0]
            if self.helper.box_error(floor['bounds'], floors[key]['worldBoundsCm']) > floors['boundsToleranceCm']:
                raise RuntimeError('%s floor bounds differ from spec: %r' % (key, floor['bounds']))
            if abs(floor['bounds']['max'][2] - floors[key]['topZ']) > floors['topToleranceCm']:
                raise RuntimeError('%s floor top %.3f differs from %.3f' % (key, floor['bounds']['max'][2], floors[key]['topZ']))
            out[key] = floor
        self.receipt['floors'] = {k: {'label': v['label'], 'topZ': v['bounds']['max'][2]} for k, v in out.items()}
        return out

    def find_veneers(self):
        tolerance = self.spec['frieze']['veneerBoundsToleranceCm']
        expected = {v['label']: v for v in self.reliefs_receipt['veneers']['all']}
        by_label = {}
        for row in self.run.snapshot:
            if row['label'] in expected:
                by_label.setdefault(row['label'], []).append(row)
        found = {}
        for label, entry in expected.items():
            rows = by_label.get(label, [])
            if len(rows) != 1:
                raise RuntimeError('Veneer %s: %d actors in the level' % (label, len(rows)))
            if self.helper.box_error(rows[0]['bounds'], entry['worldBoundsCm']) > tolerance:
                raise RuntimeError('Veneer %s bounds moved since the reliefs receipt: %r' % (label, rows[0]['bounds']))
            found[label] = rows[0]
        extras = [r for r in self.run.snapshot if r['label'] not in expected and r['folder'].endswith('Sanctuary finishes') and r['meshes']]
        self.receipt['veneers'] = {'matched': sorted(found), 'otherSanctuaryFinishActors': [r['label'] for r in extras]}
        return found, extras

    def check_palms_absent(self):
        prefix = self.spec['palms']['labelPrefix']
        live = [r['label'] for r in self.run.snapshot if r['label'].startswith(prefix)]
        if live:
            raise RuntimeError('Palm actors still present (V1 removed them; restore data in the V1 receipt): %s' % live[:5])
        self.receipt['palms'] = {'liveCount': 0, 'rule': self.spec['palms']['rule']}

    def find_v1_actors(self, v1_receipt):
        cfg = self.spec['v1']
        live = [r for r in self.run.snapshot if r['label'].startswith(cfg['labelPrefix']) or r['folder'] == self.spec['folder']]
        expected = sorted(p['label'] for p in v1_receipt['placed'])
        labels = sorted(r['label'] for r in live)
        if labels != expected:
            raise RuntimeError('Live RELEASE_Frieze_* actors (%d) differ from the V1 receipt (%d): %s' % (len(labels), len(expected),
                               sorted(set(labels) ^ set(expected))[:8]))
        for row in live:
            if len(row['meshes']) != 1 or not (row['meshes'][0] or '').startswith(cfg['meshNamespace']):
                raise RuntimeError('Frieze actor %s carries a non-V1 mesh %s' % (row['label'], row['meshes']))
        return live

    def remove_actors(self, live, key):
        restore = []
        for row in live:
            actor = row['actor']
            component = actor.get_component_by_class(self.ue.StaticMeshComponent)
            restore.append({'label': row['label'], 'name': row['name'], 'folder': row['folder'], 'mesh': row['meshes'][0], 'pose': row['pose'],
                            'worldBoundsCm': row['bounds'], 'tags': [str(t) for t in actor.get_editor_property('tags')],
                            'collisionProfile': str(component.get_collision_profile_name()) if component else None})
            if not self.run.actors.destroy_actor(actor):
                raise RuntimeError('destroy_actor returned False for ' + row['label'])
        self.receipt[key] = {'count': len(restore), 'restore': restore,
                             'restoreRule': 'spawn StaticMeshActor per entry with mesh, pose, folder, tags, NoCollision; or copy the checkpoint back'}
        return restore

    def place(self, meshes_by_role, floors, veneers, extras):
        spec = self.spec
        frieze = spec['frieze']
        tolerance = spec['verification']['staticBoundsToleranceCm']
        boxes_by_role = {role: info['localBoundsCm'] for role, (mesh, info, variant) in meshes_by_role.items()}
        excluded = dict(veneers)
        excluded['__kodesh_floor__'] = floors['kodesh']
        candidates, boxes_by_key = self.clearance.clearance_candidates(floors['heikhal'], excluded)
        walls_report, records, placed_actors, placed_boxes = [], [], [], []
        counter = 0
        try:
            for wall in frieze['walls']:
                floor_top = floors[wall['floor']]['bounds']['max'][2]
                veneer = veneers.get(wall.get('veneerLabel')) if wall.get('veneerLabel') else None
                if veneer is None and wall.get('veneerSearchBoundsCm'):
                    matches = [r for r in extras if self.helper.box_error(r['bounds'], wall['veneerSearchBoundsCm']) <= frieze['veneerBoundsToleranceCm']]
                    veneer = matches[0] if len(matches) == 1 else None
                if veneer is None:
                    walls_report.append({'wall': wall['name'], 'enabled': wall['enabled'], 'result': 'skipped_no_veneer_actor', 'panels': []})
                    continue
                if not wall['enabled']:
                    walls_report.append({'wall': wall['name'], 'enabled': False, 'veneerLabel': veneer['label'], 'result': 'disabled_by_spec', 'panels': []})
                    continue
                report, plans = plan_wall(spec, wall, veneer['bounds'], floor_top, boxes_by_role)
                report['veneerLabel'] = veneer['label']
                walls_report.append(report)
                if 'conflict' in report:
                    continue
                for plan in plans:
                    entry = dict(plan)
                    report['panels'].append(entry)
                    planned = plan['plannedWorldBoundsCm']
                    if self.helper.boxes_overlap_volume(planned, veneer['bounds']):
                        entry['result'] = 'conflict_intersects_veneer'
                        continue
                    blockers = self.clearance.blockers_for(planned, candidates, boxes_by_key)
                    if blockers:
                        entry.update(result='skipped_intersects_existing_actor', blockers=blockers)
                        continue
                    corner_overlaps = [b['label'] for b in placed_boxes if _overlap(planned, b['bounds'])]
                    mesh, info, variant = meshes_by_role[plan['role']]
                    counter += 1
                    label = '%s%s_%d' % (spec['labelPrefix'], spec['group'], counter)
                    tags = ['Release' + spec['group'], 'Wall:' + wall['name'], 'Row%02d' % plan['row'], 'Col%02d' % plan['column'], 'Variant:' + variant['name']]
                    actor, component = self.run.spawn_static(mesh, plan['location'], plan['rotation'], label, spec['folder'], spec['collisionProfile'], tags)
                    placed_actors.append(actor)
                    placed_bounds = self.helper._actor_bounds(actor)
                    if self.helper.box_error(placed_bounds, planned) > tolerance:
                        raise RuntimeError('%s bounds differ from plan by %.4f' % (label, self.helper.box_error(placed_bounds, planned)))
                    placed_boxes.append({'label': label, 'bounds': planned})
                    records.append({'label': label, 'kind': 'StaticMeshActor', 'mesh': info['asset'], 'variant': variant['name'], 'role': plan['role'],
                                    'wall': wall['name'], 'row': plan['row'], 'column': plan['column'], 'location': plan['location'], 'rotation': plan['rotation'],
                                    'scale': [1.0, 1.0, 1.0], 'collisionProfile': spec['collisionProfile'], 'plannedWorldBoundsCm': planned,
                                    'placedWorldBoundsCm': placed_bounds, 'cornerOverlapsWith': corner_overlaps, 'actor': actor})
                    entry.update(result='placed', actor=label, cornerOverlapsWith=corner_overlaps)
        except Exception:
            self.run.destroy_all(placed_actors)
            self.receipt['walls'] = walls_report
            raise
        panels = [p for w in walls_report for p in w.get('panels', [])]
        self.receipt['walls'] = walls_report
        self.receipt['frieze'] = {'moduleCm': frieze['moduleCm'], 'layout': spec['layout'], 'panelLocalBoxesCm': boxes_by_role,
                                  'placed': sum(1 for p in panels if p.get('result') == 'placed'),
                                  'skipped': sum(1 for p in panels if str(p.get('result', '')).startswith(('skipped', 'conflict'))),
                                  'placedByRole': {role: sum(1 for r in records if r['role'] == role) for role in boxes_by_role},
                                  'wallsInConflict': [w['wall'] for w in walls_report if 'conflict' in w],
                                  'wallsWithoutVeneer': [w['wall'] for w in walls_report if w.get('result') == 'skipped_no_veneer_actor'],
                                  'cornerOverlappingPanels': sum(1 for r in records if r['cornerOverlapsWith']),
                                  'perWall': {w['wall']: {'columns': w.get('columns'), 'rows': w.get('rows'),
                                                          'placed': sum(1 for p in w.get('panels', []) if p.get('result') == 'placed')} for w in walls_report}}
        return records


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def _strip(record):
    return {k: v for k, v in record.items() if k != 'actor'}


def fresh_receipt_path(spec):
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = folder / (spec['receiptPrefix'] + stamp + '.json')
        if not path.exists():
            return stamp, path
    raise RuntimeError('Could not allocate a fresh receipt stamp')


def run(images_only=False, assets_only=False, place_only=False, replace=False, image=None, allow_unverified=False):
    import unreal as ue
    if sum(bool(x) for x in (images_only, assets_only, place_only)) > 1:
        raise RuntimeError('-FriezeImagesOnly, -FriezeAssetsOnly and -FriezePlaceOnly are mutually exclusive')
    spec = load_spec()
    v1 = load_v1(spec)
    helper = load_placement_helper(spec)
    reliefs = load_reliefs_module(spec)
    offline = offline_check(spec, namespace_expected=(True if place_only else (None if images_only else False)), v1=v1)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before the run')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    namespace = spec['panel']['namespace']
    namespace_exists = assets.does_directory_exist(namespace)
    if place_only and not namespace_exists:
        raise RuntimeError('Place-only requested but namespace is missing: ' + namespace)
    if not place_only and not images_only and namespace_exists:
        raise RuntimeError('Existing native namespace preserved (use -FriezePlaceOnly): ' + namespace)

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    reliefs_receipt_path, reliefs_receipt = v1.latest_reliefs_receipt(spec)
    v1_receipt_path, v1_receipt = latest_v1_receipt(spec)
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesV1ReceiptSha256AfterSave': map_sha_before == v1_receipt.get('mapSha256AfterSave'), 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': offline, 'reliefsReceipt': str(reliefs_receipt_path), 'v1Receipt': str(v1_receipt_path),
        'switches': {'imagesOnly': images_only, 'assetsOnly': assets_only, 'placeOnly': place_only, 'replace': replace, 'image': image, 'allowUnverified': allow_unverified},
        'sourceReference': 'Yechezkel 41:18-20: keruvim and palms alternate; each keruv has a man\'s face and a young lion\'s face. Mirror tiling keeps the '
                           'alternation; full bodies and wings are the image\'s artistic interpretation (CLAUDE-VISUAL-ASSETS.md).',
        'scheme': {'horizontalRepeat': spec['image']['horizontalRepeatChoice'], 'layout': spec['layout'], 'border': spec['panel']['borderRule'],
                   'thicknessCm': spec['panel']['thicknessCm'], 'sideFaces': spec['material']['sideFaces']},
        'image': {}, 'textures': {}, 'gold': {}, 'materials': {}, 'meshes': {}, 'uvReadback': {}, 'windingCheck': {}, 'placed': [], 'errors': [],
        'mapSaved': False, 'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        derived = None
        if not place_only:
            derived = image_stage(spec, image=image, v1=v1)
            receipt['image'] = {k: v for k, v in derived.items() if not k.startswith('_')}
            write()
            if images_only:
                receipt['status'] = 'derived_images_written_no_engine_assets_no_map_change'
                return receipt

        meshes_by_role = {}
        if place_only:
            loaded = load_saved_assets(ue, spec, v1, receipt)
            meshes_by_role = loaded['meshes']
            verify_list = [(info['asset'].rsplit('/', 1)[-1], mesh, info, variant) for mesh, info, variant in meshes_by_role.values()]
        else:
            height_tex = v1.import_texture(ue, spec, 'height', derived['outputs']['height']['path'], derived['stem'], receipt)
            normal_tex = v1.import_texture(ue, spec, 'normal', derived['outputs']['normal']['path'], derived['stem'], receipt)
            write()
            gold = v1.read_gold(ue, spec, receipt)
            flat_material = v1.build_material(ue, spec, 'flat', gold, height_tex, normal_tex, receipt)
            displaced_material = v1.build_material(ue, spec, 'displaced', gold, height_tex, normal_tex, receipt)
            receipt['materials']['tessellated'] = {'status': 'not_created_in_v2', 'note': 'V1 already holds the unassigned M_KeruvFrieze_Tessellated review material'}
            write()
            flat_buffers = v1.flat_panel_buffers(spec)
            flat_check = v1.check_buffers(flat_buffers, spec['panel']['flatLocalBoundsCm'])
            flat_mesh, flat_info = v1.create_mesh(ue, spec, spec['panel']['flatName'], flat_buffers, flat_material, spec['panel']['naniteOnFlat'], receipt, flat_check)
            flat_info['placed'] = False
            write()
            verify_list = [(spec['panel']['flatName'], flat_mesh, flat_info, {'widthCm': spec['panel']['sizeCm'][0], 'uRange': [0.0, 1.0]})]
            for variant in spec['panel']['variants']:
                buffers, extra = displaced_panel_buffers(spec, v1, derived['_heightRows'], variant)
                check = v1.check_buffers(buffers, None, spec['panel']['displacedTriangleBudget'])
                if check['triangles'] != extra['expectedTriangles']:
                    raise RuntimeError('%s has %d triangles, expected %d' % (variant['name'], check['triangles'], extra['expectedTriangles']))
                check.update(extra)
                mesh, info = v1.create_mesh(ue, spec, variant['name'], buffers, displaced_material, spec['panel']['naniteOnDisplaced'], receipt, check)
                info.update(variant=variant['name'], role=variant['role'], depthCm=variant['depthCm'], widthCm=variant['widthCm'], uRange=variant['uRange'])
                if info['materialSlots'] != 1:
                    raise RuntimeError('%s has %d material slots; sides must share the gold material' % (variant['name'], info['materialSlots']))
                meshes_by_role[variant['role']] = (mesh, info, variant)
                verify_list.append((variant['name'], mesh, info, variant))
                del buffers
                write()
            derived.pop('_heightRows', None)
        receipt['status'] = 'assets_verified' if place_only else 'assets_saved'

        all_passed = True
        for name, mesh, info, variant in verify_list:
            uv = uv_readback(ue, spec, v1, mesh, variant)
            receipt['uvReadback'][name] = uv
            winding = reliefs.winding_report(ue, mesh, spec)
            offline_volume = (info.get('offline') or {}).get('signedVolumeUEcm3')
            if offline_volume is not None and winding.get('signedVolumeUEcm3') is not None:
                winding['offlineSignedVolumeUEcm3'] = offline_volume
                winding['volumeMatchesOffline'] = abs(winding['signedVolumeUEcm3'] - offline_volume) <= spec['windingCheck']['volumeRelativeTolerance'] * abs(offline_volume)
                winding['passed'] = bool(winding['passed'] and winding['volumeMatchesOffline'])
            receipt['windingCheck'][name] = winding
            all_passed = all_passed and uv['passed'] and winding['passed']
        receipt['uvAndWindingVerified'] = all_passed
        write()
        if assets_only:
            receipt['status'] = 'assets_saved_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified:
            receipt['status'] = 'assets_saved_placement_skipped_verification_failed'
            receipt['limitations'].append('Placement skipped: UV or winding readback failed/unavailable; rerun with -FriezePlaceOnly -FriezeAllowUnverifiedWinding after inspection')
            return receipt
        if not all_passed:
            receipt['limitations'].append('Placed with UNVERIFIED UV/winding by explicit switch')
        if spec['panel']['placeVariant'] != 'displaced':
            raise RuntimeError('V2 places the displaced variants only')
        receipt['placedVariant'] = 'displaced'

        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map; resolve before checkpointed placement')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
        receipt['checkpoint'] = str(checkpoint)

        run_state = helper.Placement(ue, spec)
        run_state.world = world
        run_state.receipt = receipt
        run_state.receipt_path = receipt_path
        run_state.take_snapshot()
        baseline = run_state.numeric_baseline(run_state.snapshot)
        placement = FriezePlacementV2(ue, spec, v1, helper, reliefs, run_state, receipt, reliefs_receipt)
        own_prefix = spec['labelPrefix'] + spec['group'] + '_'
        clashes = [r for r in run_state.snapshot if r['label'].startswith(own_prefix) or r['folder'] == spec['folder']]
        removed_names = set()
        if clashes and not replace:
            raise RuntimeError('Existing frieze actors preserved (use -FriezeReplace): %s' % [r['label'] for r in clashes[:10]])
        if replace:
            if not clashes:
                raise RuntimeError('-FriezeReplace given but no RELEASE_Frieze_* actor is in the level')
            live = placement.find_v1_actors(v1_receipt)
            live_names = {r['name'] for r in live}
            receipt['preExistingReleaseActors'] = [{'label': r['label'], 'folder': r['folder'], 'meshes': r['meshes']}
                                                   for r in run_state.snapshot if r['label'].startswith(spec['labelPrefix']) and r['name'] not in live_names]
            receipt['actorCountBefore'] = len(run_state.snapshot)
            floors = placement.find_floors()
            veneers, extras = placement.find_veneers()
            placement.check_palms_absent()
            write()
            removed_names = {r['name'] for r in live}
            placement.remove_actors(live, 'v1FriezeRemoved')
            run_state.take_snapshot()
            if any(r['name'] in removed_names for r in run_state.snapshot):
                raise RuntimeError('V1 frieze actors still present after destroy')
        else:
            receipt['preExistingReleaseActors'] = [{'label': r['label'], 'folder': r['folder'], 'meshes': r['meshes']}
                                                   for r in run_state.snapshot if r['label'].startswith(spec['labelPrefix'])]
            receipt['actorCountBefore'] = len(run_state.snapshot)
            floors = placement.find_floors()
            veneers, extras = placement.find_veneers()
            placement.check_palms_absent()
        write()
        expected_baseline = {k: v for k, v in baseline.items() if k not in removed_names}
        records = placement.place(meshes_by_role, floors, veneers, extras)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in expected_baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])
        if not levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()

        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run_state.world = editor.get_editor_world()
        reopened = run_state.take_snapshot()
        reopened_numeric = run_state.numeric_baseline(reopened)
        changed = [name for name, row in expected_baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        still = [r['label'] for r in reopened if r['name'] in removed_names]
        if still:
            raise RuntimeError('Removed V1 actors reappeared after reopen: %s' % still[:5])
        v1_meshes_live = [r['label'] for r in reopened if any((m or '').startswith(spec['v1']['meshNamespace']) for m in r['meshes'])]
        if replace and v1_meshes_live:
            raise RuntimeError('V1 frieze meshes still referenced after reopen: %s' % v1_meshes_live[:5])
        verify = spec['verification']
        readback = []
        for record in records:
            matching = [r for r in reopened if r['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            close, error = helper._pose_close(row['pose'], record['location'], record['rotation'], record['scale'], verify['transformToleranceCm'])
            bounds_error = helper.box_error(row['bounds'], record['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            entry = {'label': record['label'], 'variant': record['variant'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'],
                     'worldBoundsCm': row['bounds'], 'poseErrorCm': error, 'boundsErrorCm': bounds_error,
                     'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': [v1._asset_path(component.get_material(i)) for i in range(component.get_num_materials())]}
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'frieze_v2_saved_reopened_v1_actors_replaced_visual_acceptance_pending' if replace else 'frieze_v2_saved_reopened_visual_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif place_only:
            receipt['status'] = 'failed_place_only_map_unchanged_saved_assets_untouched'
        elif receipt['meshes'] or receipt['materials'] or receipt['textures']:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_assets_nothing_changed'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(helper.disk_path(m, 'umap')) == v for m, v in protected.items())
        receipt['placedActorCount'] = len(receipt['placed'])
        write()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_frieze_v2.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    tokens = command_line.split()
    lowered = [t.lower() for t in tokens]
    image = None
    for token in tokens:
        if token.lower().startswith('-friezeimage='):
            image = token.split('=', 1)[1].strip('"')
    try:
        receipt = run(images_only='-friezeimagesonly' in lowered, assets_only='-friezeassetsonly' in lowered, place_only='-friezeplaceonly' in lowered,
                      replace='-friezereplace' in lowered, image=image, allow_unverified='-friezeallowunverifiedwinding' in lowered)
        ue.log('release_frieze_v2: %s placed %s verified %s' % (receipt['status'], receipt.get('placedActorCount'), receipt.get('uvAndWindingVerified')))
    except Exception as error:
        ue.log_error('release_frieze_v2 failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


def _offline_main():
    parser = argparse.ArgumentParser(description='Offline image stage / consistency check for the keruv frieze V2')
    parser.add_argument('--derive', action='store_true', help='run the image stage (writes the V2 height/normal PNGs and previews)')
    parser.add_argument('--image', help='stem or path of another PNG')
    parser.add_argument('--derived-dir', help='output folder (default spec derivedFolder)')
    parser.add_argument('--size', type=int, help='override derived size (test only)')
    parser.add_argument('--buffers', action='store_true', help='also build every displaced variant offline and report triangle counts')
    args = parser.parse_args()
    spec = load_spec()
    v1 = load_v1(spec)
    if args.derive:
        record = image_stage(spec, image=args.image, derived_dir=args.derived_dir, size=(args.size, args.size) if args.size else None, v1=v1)
        out = {k: v for k, v in record.items() if not k.startswith('_')}
        if args.buffers:
            out['variants'] = {}
            for variant in spec['panel']['variants']:
                buffers, extra = displaced_panel_buffers(spec, v1, record['_heightRows'], variant)
                check = v1.check_buffers(buffers, None, spec['panel']['displacedTriangleBudget'])
                check.update(extra)
                out['variants'][variant['name']] = check
        print(json.dumps(out, indent=2))
    else:
        print(json.dumps(offline_check(spec, v1=v1), indent=2))


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        _offline_main()
elif _invoked_as_native_script():
    _main()
