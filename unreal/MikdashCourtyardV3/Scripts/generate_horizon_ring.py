"""Offline generator for the far-field horizon ring (HorizonRingV1). System Python, no Unreal.

WHY: every aerial frame shows a flat blue band on the horizon. It is the SkyAtmosphere's virtual
planet-ground shell, seen past the edge of the 6.4 km JerusalemContext terrain square. Height fog
cannot reach it (sky at infinite depth). Only geometry can hide it. See
Scripts/release_frame_defects.spec.json horizon.realFix and openWork[0].

WHAT: real elevation (Mapzen/AWS Terrarium tiles, the SAME source and projection the 256 tiles came
from: mikdash-walkthrough/scripts/fetch-jerusalem.py) out to +-204.8 km, in three graded zones:

    zone  from        to           cell     Terrarium zoom
    A     6.4 km sq   25.6 km sq   100 m    13 (bilinear; the tiles used 13 nearest)
    B     25.6        102.4        400 m    10
    C     102.4       409.6        1.6 km   8
    (half-extents in amot: 6400 / 25600 / 102400 / 409600; 1 amah = 0.5 m)

Each zone begins with a STITCH STRIP whose inner loop has the finer neighbour's spacing (A: the
tiles' own 25 m edge vertices; B: 100 m; C: 400 m), so there is no T-junction anywhere. At the DEM
edge the inner loop sits 0.3 m under the tile edge and carries a 10 m skirt facing outward, so a
camera outside the square can never see under the tiles.

Earth curvature is baked in (z -= d^2 / 2R about the world origin) because the SkyAtmosphere shell
is a sphere about that origin; a flat ring would rise above the real horizon line.

The SkyAtmosphere planet top is moved to REAL SEA LEVEL (-748 m) by release_horizon_ring.py. Then
every real land surface is above the shell, and the shell can only show where the ring edge is at
sea level (the Mediterranean, 55+ km west) AND the camera is high enough that the shell's tangent
point lies beyond the ring edge. coverage_analysis() computes that ceiling by casting the tangent
ray at every azimuth; it is not guessed.

Outputs SourceAssets/horizon-review/HorizonRingV1/{ring-buffers.bin, ring-manifest.json}.

    python Scripts/generate_horizon_ring.py            # download (cached), build, analyse
"""
import hashlib
import io
import json
import math
import struct
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets' / 'horizon-review' / 'HorizonRingV1'
CACHE = Path(r'C:\Mikdash\Working-5.8\TerrariumCache')
SOURCE_DEM = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\mikdash-walkthrough\public\context\jerusalem.json')

# --- the projection of fetch-jerusalem.py and the bake of terrain-manifest.json, verbatim -------
LAT0, LON0 = 31.77802, 35.2354
MX = 111320 * math.cos(math.radians(LAT0))
MZ = 111132.0
REF_ELEV_M = 748.0
TX, TZ = 17.509700315687695, 0.5513496449385334   # alignment.translationSourceAmos (x, z)
PLANET_RADIUS_M = 6360000.0                        # SkyAtmosphere bottom_radius default 6360 km
PLANET_TOP_ASL_M = -500.0                          # planet top after release_horizon_ring.py
SEA_LEVEL_REL_M = PLANET_TOP_ASL_M - REF_ELEV_M     # (name kept) coverage datum, relative to the plaza
# NOT sea level. cp21-P1 proved sea level wrong: the Jordan rift floor (-432 m) was then BELOW the
# shell, and UE shades geometry under the virtual ground with the shell's own colour through aerial
# perspective, so the whole eastern horizon still read as a sea. The shell must sit below the lowest
# ring elevation; -500 m ASL leaves 68 m under the Dead Sea clamp.

TILE_HALF = 6400        # amot; the 256-tile square
TILE_STEP = 50          # amot; 25 m tile vertex spacing
ZONES = [
    # name, inner half-extent, outer half-extent, cell (amot), terrarium zoom
    ('A', 6400, 25600, 200, 13),
    ('B', 25600, 102400, 800, 10),
    ('C', 102400, 409600, 3200, 8),
]
SEAM_DROP_M = 0.3
SKIRT_M = 10.0
DEAD_SEA_FLOOR_M = -432.0
MED_LON = 34.95         # west of this, negative Terrarium values are sea bathymetry -> sea level


def ue_xy_cm(xs, zs):
    return (xs + TX) * 50.0, (zs - TZ) * 50.0


def latlon(xs, zs):
    return LAT0 - zs / 2.0 / MZ, LON0 + (xs + 124.0) / 2.0 / MX


# --------------------------------------------------------------------------- Terrarium ---------
class Terrarium:
    def __init__(self, zoom):
        self.z = zoom
        self.n = 2 ** zoom
        self.tiles = {}
        self.fetched = []

    def tile(self, ix, iy):
        key = (ix, iy)
        if key not in self.tiles:
            CACHE.mkdir(parents=True, exist_ok=True)
            p = CACHE / ('dem-%d-%d-%d.png' % (self.z, ix, iy))
            if not p.exists():
                url = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/%d/%d/%d.png' % (self.z, ix, iy)
                for attempt in range(4):
                    try:
                        with urllib.request.urlopen(url, timeout=40) as r:
                            p.write_bytes(r.read())
                        break
                    except Exception as e:  # noqa: BLE001
                        if attempt == 3:
                            raise
                        time.sleep(2 + attempt * 3)
            data = p.read_bytes()
            rgb = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'), dtype=np.float64)
            self.tiles[key] = rgb[:, :, 0] * 256.0 + rgb[:, :, 1] + rgb[:, :, 2] / 256.0 - 32768.0
            self.fetched.append({'zoom': self.z, 'x': ix, 'y': iy, 'file': p.name,
                                 'sha256': hashlib.sha256(data).hexdigest()})
        return self.tiles[key]

    def pixel(self, gx, gy):
        ix, iy = gx // 256, gy // 256
        return self.tile(int(ix), int(iy))[int(gy - iy * 256), int(gx - ix * 256)]

    def global_px(self, lat, lon):
        tx = (lon + 180.0) / 360.0 * self.n
        ty = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * self.n
        return tx * 256.0, ty * 256.0

    def nearest(self, lat, lon):
        # fetch-jerusalem.py sample(): int() of the in-tile pixel, no interpolation
        tx = (lon + 180.0) / 360.0 * self.n
        ty = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * self.n
        ix, iy = int(tx), int(ty)
        x = min(255, int((tx - ix) * 256)); y = min(255, int((ty - iy) * 256))
        return self.tile(ix, iy)[y, x]

    def bilinear(self, lat, lon):
        px, py = self.global_px(lat, lon)
        px -= 0.5; py -= 0.5
        x0, y0 = math.floor(px), math.floor(py)
        fx, fy = px - x0, py - y0
        a = self.pixel(x0, y0); b = self.pixel(x0 + 1, y0)
        c = self.pixel(x0, y0 + 1); d = self.pixel(x0 + 1, y0 + 1)
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


RIFT_BOX = (30.9, 33.0, 35.3, 35.75)   # lat min/max, lon min/max: Dead Sea, Jordan valley, Galilee
GALILEE_LAT = 32.6
GALILEE_SURFACE_M = -212.0


def clamp_elevation(e, lon, lat=None):
    """Terrarium carries bathymetry. Below-sea-level LAND exists only in the Jordan rift; every
    other negative value is sea and is drawn at its surface (0 m). Inside the rift the Dead Sea is
    clamped at its surface (-432 m) and the Sea of Galilee at its surface (-212 m).

    A first version keyed the sea on lon < 34.95 and left the coast north of Haifa (lon 35.0-35.4)
    at -432 m bathymetry; the coverage analysis caught it as a shell gap just west of north for
    doves at 1,500 m and above."""
    if lat is None:
        lat = LAT0
    in_rift = RIFT_BOX[0] <= lat <= RIFT_BOX[1] and RIFT_BOX[2] <= lon <= RIFT_BOX[3]
    if e < 0.0 and not in_rift:
        return 0.0
    if in_rift and lat >= GALILEE_LAT:
        return max(e, GALILEE_SURFACE_M)
    return max(e, DEAD_SEA_FLOOR_M)


def curvature_drop_m(x_cm, y_cm):
    d = math.hypot(x_cm, y_cm) / 100.0
    return d * d / (2.0 * PLANET_RADIUS_M)


MESHES_JSON = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\architecture-review\jerusalem-meshes.json')


def tile_colours():
    """Median bare and green vertex colour of the source terrain mesh (mesh 0). Parses only that
    one list out of the 100 MB file so a 32-bit Python can do it."""
    text = MESHES_JSON.read_text(encoding='utf-8')
    k = text.index('"vertexColors":')
    start = text.index('[', k)
    depth = 0
    for end in range(start, len(text)):
        ch = text[end]
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                break
    cols = np.array(json.loads(text[start:end + 1]), dtype=np.float64).reshape(-1, 3)
    del text
    assert len(cols) == 66049, len(cols)
    lum = cols @ np.array([0.2126, 0.7152, 0.0722])
    bare = np.median(cols[lum > 0.45], axis=0)
    green = np.median(cols[lum < 0.42], axis=0)
    TILE_COLOUR_STATS.update({'bareMedian': bare.tolist(), 'greenMedian': green.tolist(),
                              'bareCount': int(np.sum(lum > 0.45)), 'greenCount': int(np.sum(lum < 0.42)),
                              'luminanceRange': [float(lum.min()), float(lum.max())]})
    return [float(v) for v in bare] + [1.0], [float(v) for v in green] + [1.0]


TILE_COLOUR_STATS = {}


# --------------------------------------------------------------------------- geometry ---------
class Builder:
    def __init__(self):
        self.pos = []       # UE cm
        self.col = []
        self.tri = []
        self.index = {}
        self.chunk_of_tri = []
        self.kind_of_tri = []

    def vertex(self, key, xyz, rgba):
        if key is not None and key in self.index:
            return self.index[key]
        self.pos.append(xyz); self.col.append(rgba)
        i = len(self.pos) - 1
        if key is not None:
            self.index[key] = i
        return i

    def triangle(self, a, b, c, chunk, kind):
        self.tri.append((a, b, c)); self.chunk_of_tri.append(chunk); self.kind_of_tri.append(kind)


def octant(xs, zs):
    ang = math.degrees(math.atan2(-zs, xs))   # 0 = east, 90 = north (zs is south)
    return int(((ang + 22.5) % 360) // 45)    # 0 E, 1 NE, 2 N, 3 NW, 4 W, 5 SW, 6 S, 7 SE


OCTANT_NAMES = ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']


def hash01(i, j, seed):
    h = (i * 374761393 + j * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def value_noise(x, y, scale, seed):
    u, v = x / scale, y / scale
    i, j = math.floor(u), math.floor(v)
    fu, fv = u - i, v - j
    fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    a, b = hash01(i, j, seed), hash01(i + 1, j, seed)
    c, d = hash01(i, j + 1, seed), hash01(i + 1, j + 1, seed)
    return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    src = json.loads(SOURCE_DEM.read_text(encoding='utf-8'))['terrain']
    assert src['size'] == 257 and src['step'] == TILE_STEP and src['origin'] == -TILE_HALF
    grid = np.array(src['heights'], dtype=np.float64).reshape(257, 257)   # [j=z][i=x], amot
    # jerusalem.ts: h * smoothstep(max(|x|,|z|), 260, 360) - 0.05; the factor is 1 on the edge.
    tile_edge_amot = lambda xs, zs: grid[(zs + TILE_HALF) // TILE_STEP, (xs + TILE_HALF) // TILE_STEP] - 0.05

    samplers = {z: Terrarium(z) for z in (8, 10, 13)}
    # Proof the source is the same: the tiles' own z13-nearest at the DEM corners reproduces them.
    t13 = samplers[13]
    proof = []
    for xs, zs in [(-6400, -6400), (6400, -6400), (-6400, 6400), (6400, 6400), (0, -6400), (-6400, 0)]:
        lat, lon = latlon(xs, zs)
        rebuilt = round((t13.nearest(lat, lon) - REF_ELEV_M) * 2, 2)
        stored = grid[(zs + TILE_HALF) // TILE_STEP, (xs + TILE_HALF) // TILE_STEP]
        proof.append({'xs': xs, 'zs': zs, 'storedAmot': stored, 'rebuiltAmot': rebuilt})
    assert all(abs(p['storedAmot'] - p['rebuiltAmot']) < 0.011 for p in proof), proof

    # Representative vertex colours, taken from the tiles' OWN vertexColors (mesh 0 of
    # jerusalem-meshes.json, which is what the FBX carried). The material only uses their
    # luminance as a bare/scrub mask (MaskLumLow 0.4, MaskLumHigh 0.5), so matching the tiles'
    # values, not re-deriving them from the HSL rule, is what keeps the seam invisible.
    bare_rgba, green_rgba = tile_colours()

    def hsl(kind, jitter):
        base = green_rgba if kind == 'green' else bare_rgba
        return [max(0.0, base[0] + jitter), max(0.0, base[1] + jitter), max(0.0, base[2] + jitter), 1.0]

    def colour(xs, zs, e_asl, lon):
        # West of the watershed: planted pine and scrub on the Judean hills; the coastal plain is
        # farmland; east of the watershed (the Judean desert and the rift) is bare. The material
        # decides bare vs scrub from luminance, and forces bare on slopes regardless.
        n = value_noise(xs, zs, 2400.0, 7) * 0.65 + value_noise(xs, zs, 700.0, 11) * 0.35
        if lon < 35.18 and 250.0 < e_asl < 900.0:
            green = n > 0.58
        elif lon < 34.95 and 0.5 < e_asl < 250.0:
            green = n > 0.5
        elif lon > 35.3 and e_asl > 700.0:      # Moab / Gilead plateau farmland
            green = n > 0.62
        else:
            green = False
        jitter = (hash01(int(xs) // 50, int(zs) // 50, 3) - 0.5) * 0.04
        return hsl('green' if green else 'bare', jitter * 0.5)

    height_cache = {}

    def height_cm(xs, zs, zoom):
        key = (xs, zs, zoom)
        if key not in height_cache:
            lat, lon = latlon(xs, zs)
            e = clamp_elevation(samplers[zoom].bilinear(lat, lon), lon, lat)
            x, y = ue_xy_cm(xs, zs)
            height_cache[key] = ((e - REF_ELEV_M - curvature_drop_m(x, y)) * 100.0, e, lon)
        return height_cache[key]

    B = Builder()
    zone_stats = []

    def add_vertex(xs, zs, zoom, zone):
        z_cm, e, lon = height_cm(xs, zs, zoom)
        x, y = ue_xy_cm(xs, zs)
        return B.vertex(('v', xs, zs), (x, y, z_cm), colour(xs, zs, e, lon))

    def add_seam_vertex(xs, zs):
        # On the tile edge: 0.3 m under the tile's own vertex, so the tile always wins.
        x, y = ue_xy_cm(xs, zs)
        z = tile_edge_amot(xs, zs) * 50.0 - SEAM_DROP_M * 100.0
        lat, lon = latlon(xs, zs)
        return B.vertex(('v', xs, zs), (x, y, z), colour(xs, zs, z / 100.0 + REF_ELEV_M, lon))

    def loop_points(half, step):
        """Square loop at half-extent `half`, CCW in (xs, zs) starting at (-half, -half)."""
        pts = []
        for s in range(-half, half, step): pts.append((s, -half))
        for s in range(-half, half, step): pts.append((half, s))
        for s in range(half, -half, -step): pts.append((s, half))
        for s in range(half, -half, -step): pts.append((-half, s))
        return pts

    for zi, (name, inner, outer, cell, zoom) in enumerate(ZONES):
        tri_before = len(B.tri)
        fine = cell // 4
        # inner loop vertices (shared with the finer neighbour / the tiles)
        def inner_vertex(xs, zs):
            if zi == 0:
                return add_seam_vertex(xs, zs)
            return add_vertex(xs, zs, ZONES[zi - 1][4], name)  # the finer zone's own sampler
        # --- stitch strip between the inner loop (spacing cell/4) and the loop at inner+cell ----
        a, b = inner, inner + cell
        # walk each side: coarse segment on the outer loop, 4 fine segments on the inner loop
        sides = [  # (fixed axis, fixed sign, running direction) described by point generators
            lambda s, h: (s, -h), lambda s, h: (h, s), lambda s, h: (-s, h), lambda s, h: (-h, -s)]
        for side in sides:
            # coarse outer segments whose projection covers [-a, a] on the inner loop
            for s0 in range(-a, a, cell):
                ins = [inner_vertex(*side(s0 + k * fine, a)) for k in range(5)]
                o0 = add_vertex(*side(s0, b), zoom, name)
                o1 = add_vertex(*side(s0 + cell, b), zoom, name)
                mx_ = side(s0 + cell / 2, a)
                ch = octant(*mx_)
                tri = [(ins[0], ins[1], o0), (ins[1], ins[2], o0), (ins[2], o1, o0),
                       (ins[2], ins[3], o1), (ins[3], ins[4], o1)]
                for t in tri:
                    B.triangle(*t, chunk=(name, ch), kind='stitch')
            # corner square [a, b] x [a, b] at the end of this side
            ic = inner_vertex(*side(a, a))
            oc = add_vertex(*side(b, b), zoom, name)
            oa = add_vertex(*side(a, b), zoom, name)
            # the corner is bounded by inner corner ic, outer loop points side(a,b) (end of this
            # side's outer run), side(b,b) (outer corner) and the NEXT side's first outer point.
            ch = octant(*side(a + cell / 2, a + cell / 2))
            nxt = sides[(sides.index(side) + 1) % 4]
            on = add_vertex(*nxt(-a, b), zoom, name)
            B.triangle(ic, oc, oa, chunk=(name, ch), kind='stitch')
            B.triangle(ic, on, oc, chunk=(name, ch), kind='stitch')
        # --- regular grid from inner+cell to outer --------------------------------------------
        lo = -outer
        n_cells = (2 * outer) // cell
        hole = inner + cell
        for j in range(n_cells):
            z0 = lo + j * cell
            for i in range(n_cells):
                x0 = lo + i * cell
                if -hole <= x0 and x0 + cell <= hole and -hole <= z0 and z0 + cell <= hole:
                    continue
                v00 = add_vertex(x0, z0, zoom, name); v10 = add_vertex(x0 + cell, z0, zoom, name)
                v01 = add_vertex(x0, z0 + cell, zoom, name); v11 = add_vertex(x0 + cell, z0 + cell, zoom, name)
                ch = octant(x0 + cell / 2, z0 + cell / 2)
                # split along the diagonal that best follows the terrain
                h00, h11 = B.pos[v00][2], B.pos[v11][2]
                h10, h01 = B.pos[v10][2], B.pos[v01][2]
                if abs(h00 - h11) <= abs(h10 - h01):
                    B.triangle(v00, v10, v11, chunk=(name, ch), kind='grid')
                    B.triangle(v00, v11, v01, chunk=(name, ch), kind='grid')
                else:
                    B.triangle(v00, v10, v01, chunk=(name, ch), kind='grid')
                    B.triangle(v10, v11, v01, chunk=(name, ch), kind='grid')
        zone_stats.append({'zone': name, 'innerHalfAmot': inner, 'outerHalfAmot': outer,
                           'cellAmot': cell, 'cellMetres': cell / 2, 'terrariumZoom': zoom,
                           'triangles': len(B.tri) - tri_before})
        print('zone', name, 'triangles', len(B.tri) - tri_before, 'vertices', len(B.pos),
              '%.0fs' % (time.time() - t0), flush=True)

    # --- the seam skirt: from each tile edge vertex straight down, facing OUTWARD --------------
    skirt_tris = 0
    pts = loop_points(TILE_HALF, TILE_STEP)
    for k in range(len(pts)):
        p, q = pts[k], pts[(k + 1) % len(pts)]
        tops = []
        for (xs, zs) in (p, q):
            x, y = ue_xy_cm(xs, zs)
            z = tile_edge_amot(xs, zs) * 50.0
            lat, lon = latlon(xs, zs)
            c = colour(xs, zs, z / 100.0 + REF_ELEV_M, lon)
            top = B.vertex(None, (x, y, z), c)
            bot = B.vertex(None, (x, y, z - (SEAM_DROP_M + SKIRT_M) * 100.0), c)
            tops.append((top, bot))
        (pt, pb), (qt, qb) = tops
        ch = octant((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        B.triangle(pt, qt, qb, chunk=('A', ch), kind='skirt')
        B.triangle(pt, qb, pb, chunk=('A', ch), kind='skirt')
        skirt_tris += 2

    pos = np.array(B.pos, dtype=np.float64)
    tri = np.array(B.tri, dtype=np.int64)
    kinds = np.array(B.kind_of_tri)

    # --- winding: terrain faces +Z, skirt faces away from the origin (right-handed cross) ------
    e1 = pos[tri[:, 1]] - pos[tri[:, 0]]
    e2 = pos[tri[:, 2]] - pos[tri[:, 0]]
    nrm = np.cross(e1, e2)
    flip = np.zeros(len(tri), dtype=bool)
    terr = kinds != 'skirt'
    flip[terr] = nrm[terr, 2] < 0
    centre = (pos[tri[:, 0]] + pos[tri[:, 1]] + pos[tri[:, 2]]) / 3.0
    sk = ~terr
    outward = centre[sk, :2]
    flip[sk] = (nrm[sk, 0] * outward[:, 0] + nrm[sk, 1] * outward[:, 1]) < 0
    tri[flip] = tri[flip][:, [0, 2, 1]]
    degenerate = int(np.sum(np.linalg.norm(nrm, axis=1) < 1e-3))
    assert degenerate == 0, 'degenerate triangles: %d' % degenerate

    # --- smooth vertex normals from the terrain triangles only (skirts get horizontal normals) ---
    e1 = pos[tri[:, 1]] - pos[tri[:, 0]]
    e2 = pos[tri[:, 2]] - pos[tri[:, 0]]
    fn = np.cross(e1, e2)
    vn = np.zeros_like(pos)
    for k in range(3):
        np.add.at(vn, tri[terr, k], fn[terr])
    sk_idx = np.unique(tri[sk].ravel())
    vn[sk_idx] = 0.0
    for k in range(3):
        np.add.at(vn, tri[sk, k], fn[sk])
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-9)
    assert np.all(vn[np.unique(tri[terr].ravel()), 2] > 0.05), 'a terrain normal points down'

    # --- chunks: zone x octant, each re-indexed ------------------------------------------------
    blob = io.BytesIO()
    chunks = []
    col = np.array(B.col, dtype=np.float32)
    keys = sorted(set(B.chunk_of_tri), key=lambda k: (k[0], k[1]))
    chunk_arr = np.array(['%s_%d' % k for k in B.chunk_of_tri])
    for key in keys:
        sel = np.nonzero(chunk_arr == '%s_%d' % key)[0]
        t = tri[sel]
        used, inv = np.unique(t.ravel(), return_inverse=True)
        t_local = inv.reshape(-1, 3).astype(np.uint32)
        p = pos[used].astype(np.float32); n = vn[used].astype(np.float32); c = col[used]
        entry = {'name': 'SM_HorizonRingV1_%s_%s' % (key[0], OCTANT_NAMES[key[1]]),
                 'zone': key[0], 'octant': OCTANT_NAMES[key[1]],
                 'vertices': int(len(used)), 'triangles': int(len(t_local)),
                 'boundsCm': [float(v) for v in p.min(axis=0)] + [float(v) for v in p.max(axis=0)],
                 'kinds': {k: int(np.sum(kinds[sel] == k)) for k in ('grid', 'stitch', 'skirt')}}
        for label, arr in (('positions', p), ('normals', n), ('colors', c), ('indices', t_local)):
            entry[label + 'Offset'] = blob.tell()
            blob.write(arr.tobytes(order='C'))
            entry[label + 'Bytes'] = int(arr.nbytes)
        chunks.append(entry)
    data = blob.getvalue()
    bin_path = OUT / 'ring-buffers.bin'
    bin_path.write_bytes(data)

    coverage = coverage_analysis(B, pos, samplers, grid)

    fetched = sum((s.fetched for s in samplers.values()), [])
    manifest = {
        'version': 'HorizonRingV1',
        'generatedUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'generator': 'Scripts/generate_horizon_ring.py',
        'generatorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'buffers': bin_path.name, 'buffersSha256': hashlib.sha256(data).hexdigest(),
        'bufferLayout': 'per chunk: float32 xyz positions (UE cm), float32 xyz normals, float32 rgba '
                        'linear vertex colours, uint32 triangle indices; offsets/bytes per chunk',
        'projection': {'lat0': LAT0, 'lon0': LON0, 'mxMetresPerDegLon': MX, 'mzMetresPerDegLat': MZ,
                       'source': 'mikdash-walkthrough/scripts/fetch-jerusalem.py lines 20-22 and 46',
                       'bake': 'terrain-manifest.json coordinateConvention; UE X=(xs+%.10f)*50, '
                               'Y=(zs-%.10f)*50, Z=(elev-748)*100' % (TX, TZ)},
        'referenceElevationMetres': REF_ELEV_M,
        'planetRadiusMetres': PLANET_RADIUS_M,
        'curvature': 'z -= d^2/(2R), d = horizontal distance from the world origin, R = the '
                     'SkyAtmosphere bottom radius, so the ring and the shell share one sphere',
        'elevationSource': 'Mapzen / AWS Open Data Terrarium tiles, https://registry.opendata.aws/terrain-tiles/',
        'elevationClamp': clamp_elevation.__doc__.strip() + ' Rift box lat %s-%s lon %s-%s.' % RIFT_BOX,
        'sourceProof': {'note': 'fetch-jerusalem.py z13 nearest sampling, re-run here, reproduces the '
                                'stored DEM to 0.01 amot at the corners and edge midpoints: the ring and '
                                'the tiles come from one elevation source.', 'samples': proof},
        'tileColours': TILE_COLOUR_STATS,
        'seam': {'innerLoop': 'the 1,024 tile edge vertices themselves (25 m spacing), %.1f m under the '
                              'tile surface' % SEAM_DROP_M,
                 'skirt': '%.0f m, outward-facing, top exactly on the tile edge' % SKIRT_M},
        'zones': zone_stats,
        'skirtTriangles': skirt_tris,
        'totals': {'vertices': int(len(pos)), 'triangles': int(len(tri)), 'chunks': len(chunks),
                   'outerHalfExtentKm': ZONES[-1][2] / 2000.0},
        'windingRule': 'terrain triangles have cross(b-a, c-a).z > 0 in UE cm (right-handed cross); '
                       'release_horizon_ring.py checks this against a live terrain tile and flips '
                       'every triangle if the tile disagrees',
        'terrariumTiles': fetched,
        'chunks': chunks,
        'coverage': coverage,
    }
    (OUT / 'ring-manifest.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    print(json.dumps({k: manifest[k] for k in ('totals', 'zones')}, indent=1))
    print(json.dumps(coverage['summary'], indent=1))
    print('done %.0fs' % (time.time() - t0))


# --------------------------------------------------------------------------- coverage ---------
def coverage_analysis(B, pos, samplers, grid):
    """For each camera, every azimuth (0.5 deg), find the ray that grazes the SkyAtmosphere shell
    (planet top at sea level, radius R, centred under the world origin) and march it across the
    ring + tiles. The shell is visible in that azimuth iff the grazing ray reaches the ring edge
    without passing under terrain. Steeper rays are lower at every distance, so a blocked grazing
    ray means no shell pixel at all in that azimuth."""
    R = PLANET_RADIUS_M
    top = SEA_LEVEL_REL_M
    centre = np.array([0.0, 0.0, top - R])
    outer_m = ZONES[-1][2] / 2.0

    def terrain_m(x_m, y_m):
        # heights from the same samplers the ring uses, tiles inside the square
        xs = x_m * 2.0 - TX; zs = y_m * 2.0 + TZ
        if abs(xs) <= TILE_HALF and abs(zs) <= TILE_HALF:
            i = (xs + TILE_HALF) / TILE_STEP; j = (zs + TILE_HALF) / TILE_STEP
            i0, j0 = int(min(255, max(0, math.floor(i)))), int(min(255, max(0, math.floor(j))))
            fi, fj = i - i0, j - j0
            h = (grid[j0, i0] * (1 - fi) + grid[j0, i0 + 1] * fi) * (1 - fj) + \
                (grid[j0 + 1, i0] * (1 - fi) + grid[j0 + 1, i0 + 1] * fi) * fj
            return h / 2.0
        m = max(abs(xs), abs(zs))
        zoom = 13 if m <= 25600 else (10 if m <= 102400 else 8)
        lat, lon = latlon(xs, zs)
        e = clamp_elevation(samplers[zoom].bilinear(lat, lon), lon, lat)
        return e - REF_ELEV_M - (x_m * x_m + y_m * y_m) / (2 * R)

    def grazing_ray(cam, az):
        d_h = np.array([math.cos(math.radians(az)), -math.sin(math.radians(az)), 0.0])  # UE: Y south
        lo, hi = 0.0, math.radians(15.0)
        for _ in range(60):
            mid = (lo + hi) / 2
            d = d_h * math.cos(mid) + np.array([0, 0, -math.sin(mid)])
            oc = cam - centre
            b = np.dot(oc, d); c = np.dot(oc, oc) - R * R
            if b * b - c >= 0 and b < 0:
                hi = mid
            else:
                lo = mid
        return hi, d_h

    cameras = [
        ('temple-mount-ground', (0.0, 0.0, 2.0)),
        ('cp17b-P1-aerial', (-950.0, 1750.0, 300.0)),
        ('dove-500m', (0.0, 0.0, 500.0)),
        ('dove-1000m', (0.0, 0.0, 1000.0)),
        ('dove-1500m', (0.0, 0.0, 1500.0)),
        ('dove-2000m', (0.0, 0.0, 2000.0)),
        ('dove-2000m-at-DEM-corner', (-3000.0, 3000.0, 2000.0)),
        ('dove-2400m', (0.0, 0.0, 2400.0)),
        ('dove-3000m', (0.0, 0.0, 3000.0)),
    ]
    results = []
    for label, cam in cameras:
        cam = np.array(cam)
        open_az = []
        min_margin = None
        for k in range(720):
            az = k * 0.5
            theta, d_h = grazing_ray(cam, az)
            blocked = False
            best = -1e9
            s = 50.0
            while True:
                p = cam[:2] + d_h[:2] * s
                if max(abs(p[0]), abs(p[1])) > outer_m:
                    break
                ray_z = cam[2] - s * math.tan(theta)
                t = terrain_m(p[0], p[1])
                best = max(best, t - ray_z)
                if t >= ray_z:
                    blocked = True
                    break
                s *= 1.02 if s > 2000 else 1.0
                s += 50.0 if s < 20000 else 400.0
            if not blocked:
                open_az.append(az)
            margin = best
            min_margin = margin if min_margin is None else min(min_margin, margin)
        results.append({'camera': label, 'positionMetres': [float(v) for v in cam],
                        'azimuthsTested': 720, 'azimuthsWhereShellVisible': len(open_az),
                        'openAzimuthsDeg': open_az[:40],
                        'worstMarginMetres': round(float(min_margin), 1)})
        print('coverage', label, 'open', len(open_az), 'worst margin', round(float(min_margin), 1), flush=True)
    ceiling = None
    for r in results:
        if r['camera'].startswith('dove-') and 'corner' not in r['camera'] and r['azimuthsWhereShellVisible'] == 0:
            ceiling = r['positionMetres'][2]
    return {'method': coverage_analysis.__doc__.strip(), 'cameras': results,
            'summary': {'highestTestedDoveHeightWithNoShellMetres': ceiling,
                        'analyticCeilingMetres': round((ZONES[-1][2] / 2.0) ** 2 / (2 * R) + SEA_LEVEL_REL_M, 0),
                        'analyticNote': 'with the ring edge at sea level, the shell stays hidden while '
                                        'the grazing point sqrt(2HR) (H = height above sea level) lies '
                                        'inside the ring: H <= D_out^2/2R'}}


if __name__ == '__main__':
    main()
