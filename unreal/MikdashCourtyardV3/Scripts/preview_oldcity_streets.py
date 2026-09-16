"""Offline previews of OldCityStreetsV1: a plan sheet and eye-level perspective renders.

AUTHORED_OFFLINE_SOURCE. No engine, no map, no Content/. This exists so the paving is LOOKED
AT before an engine slot is spent on it: a z-buffered flat-shaded rasteriser over the emitted
paving OBJs, the exact game terrain and the city buildings, from a 170 cm eye.

    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" \
        -B Scripts/preview_oldcity_streets.py
"""
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))

import create_oldcity_facades as F      # noqa: E402
import oldcity_foundations_v2 as FO     # noqa: E402

OUT = ROOT / 'SourceAssets' / 'context-review' / 'OldCityStreetsV1'
OBJ_DIR = OUT / 'obj'
WIDTH, HEIGHT = 1280, 720
FOV_DEG = 75.0
FAR_CM = 9000.0
SUN = (-0.42, 0.30, 0.86)

# Eye-level cameras. S1 and S2 are the exact OldCityFoundationV2 acceptance cameras so the
# preview can be compared with oldcity01-before-S1/S2 frame for frame.
CAMERAS = [
    # S1 and S2 are the OldCityFoundationV2 acceptance cameras, kept so the comparison is frame
    # for frame. MEASURED against the emitted paving: S2 stands ON it (nearest vertex 0.4 cm,
    # 5,388 within 20 m) and K1 is 5.4 m from it, but S1's nearest paving is 24.8 m away with
    # NOTHING within 20 m - so S1 cannot show this pass's work and is kept only as evidence.
    dict(name='S1-jewish-quarter-lane', pos=(-22627.0, 20613.0), yaw=118.0, pitch=-5.0),
    dict(name='S2-jewish-quarter-lane', pos=(-29154.0, 30430.0), yaw=136.0, pitch=-5.0),
    # Candidates for a replacement walking view, taken from the densest Tier-A paving
    # neighbourhoods (individual stones, not plain strip) clear of S2 and K1. Positions are
    # measured; the headings are candidates to be chosen BY EYE from these renders rather than
    # guessed, because a camera aimed across a lane instead of along it shows nothing.
    dict(name='C1-west-lane-yaw135', pos=(-45000.0, 13000.0), yaw=135.0, pitch=-6.0),
    dict(name='C2-west-lane-yaw045', pos=(-45000.0, 13000.0), yaw=45.0, pitch=-6.0),
    dict(name='C3-west-lane-yaw315', pos=(-47000.0, 15000.0), yaw=315.0, pitch=-6.0),
    dict(name='C4-west-lane-yaw180', pos=(-41000.0, 29000.0), yaw=180.0, pitch=-6.0),
]


def write_png(path, width, height, pixels):
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        rows.extend(pixels[y * width * 3:(y + 1) * width * 3])
    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload
                + struct.pack('>I', zlib.crc32(tag + payload) & 0xFFFFFFFF))
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(rows), 6))
           + chunk(b'IEND', b''))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def load_obj_triangles(path, centre, radius):
    """Canonical triangles (reflect Y back, restore winding) near the camera."""
    verts = []
    tris = []
    with path.open() as handle:
        for line in handle:
            if line.startswith('v '):
                parts = line.split()
                verts.append((float(parts[1]), -float(parts[2]), float(parts[3])))
            elif line.startswith('f '):
                parts = line.split()
                ids = [int(parts[k].split('/')[0]) - 1 for k in (1, 3, 2)]
                tri = (verts[ids[0]], verts[ids[1]], verts[ids[2]])
                cx = (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0
                cy = (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0
                if abs(cx - centre[0]) < radius and abs(cy - centre[1]) < radius:
                    tris.append(tri)
    return tris


class Raster:
    def __init__(self, width, height, eye, yaw_deg, pitch_deg):
        self.w, self.h = width, height
        self.eye = eye
        yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
        self.fwd = (math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))
        self.right = (-math.sin(yaw), math.cos(yaw), 0.0)
        self.up = tuple(self.fwd[(i + 1) % 3] * self.right[(i + 2) % 3]
                        - self.fwd[(i + 2) % 3] * self.right[(i + 1) % 3] for i in range(3))
        self.focal = (width / 2.0) / math.tan(math.radians(FOV_DEG) / 2.0)
        self.depth = [1e30] * (width * height)
        self.pixels = bytearray(width * height * 3)
        for i in range(width * height):
            y = i // width
            t = y / float(height)
            self.pixels[i * 3 + 0] = int(150 + 70 * (1 - t))
            self.pixels[i * 3 + 1] = int(170 + 60 * (1 - t))
            self.pixels[i * 3 + 2] = int(200 + 45 * (1 - t))

    def project(self, p):
        d = (p[0] - self.eye[0], p[1] - self.eye[1], p[2] - self.eye[2])
        z = sum(d[i] * self.fwd[i] for i in range(3))
        if z < 1.0:
            return None
        x = sum(d[i] * self.right[i] for i in range(3))
        y = sum(d[i] * self.up[i] for i in range(3))
        return (self.w / 2.0 + x * self.focal / z, self.h / 2.0 - y * self.focal / z, z)

    def triangle(self, tri, colour):
        pts = [self.project(p) for p in tri]
        if any(p is None for p in pts):
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1 = max(0, int(min(xs))), min(self.w - 1, int(math.ceil(max(xs))))
        y0, y1 = max(0, int(min(ys))), min(self.h - 1, int(math.ceil(max(ys))))
        if x1 < x0 or y1 < y0:
            return
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts
        area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if abs(area) < 1e-9:
            return
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                sx, sy = px + 0.5, py + 0.5
                w0 = ((bx - ax) * (sy - ay) - (by - ay) * (sx - ax)) / area
                w1 = ((sx - ax) * (cy - ay) - (sy - ay) * (cx - ax)) / area
                if w0 < 0 or w1 < 0 or w0 + w1 > 1:
                    continue
                z = az + (cz - az) * w0 + (bz - az) * w1
                index = py * self.w + px
                if z >= self.depth[index] or z > FAR_CM:
                    continue
                self.depth[index] = z
                haze = min(1.0, z / FAR_CM) ** 1.3
                for c in range(3):
                    base = colour[c]
                    sky = (190, 205, 225)[c]
                    self.pixels[index * 3 + c] = int(base + (sky - base) * haze * 0.75)


def shade(tri, base):
    u = [tri[1][i] - tri[0][i] for i in range(3)]
    v = [tri[2][i] - tri[0][i] for i in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    length = math.sqrt(sum(c * c for c in n)) or 1.0
    n = tuple(c / length for c in n)
    lambert = max(0.0, sum(n[i] * SUN[i] for i in range(3)))
    ambient = 0.34 + 0.16 * max(0.0, n[2])
    gain = ambient + 0.78 * lambert
    return tuple(int(max(0, min(255, base[i] * gain))) for i in range(3))


def main():
    raw = FO.read(FO.RAW)['meshes']
    terrain = FO.Terrain(raw[0])
    source = F.CitySource(FO.read(F.SOURCE_JSON))
    buildings, _skipped = source.buildings()
    del raw
    obj_files = sorted(OBJ_DIR.glob('*.obj'))
    if not obj_files:
        raise SystemExit('no paving OBJs in %s - run create_oldcity_streets.py build first' % OBJ_DIR)

    for camera in CAMERAS:
        cx, cy = camera['pos']
        eye = (cx, cy, terrain.at(cx, cy) + 170.0)
        raster = Raster(WIDTH, HEIGHT, eye, camera['yaw'], camera['pitch'])
        radius = FAR_CM

        # terrain, 2 m grid around the camera
        step = 200.0
        n = int(radius / step)
        for i in range(-n, n):
            for j in range(-n, n):
                x0, y0 = cx + i * step, cy + j * step
                x1, y1 = x0 + step, y0 + step
                quad = [(x0, y0, terrain.at(x0, y0)), (x1, y0, terrain.at(x1, y0)),
                        (x1, y1, terrain.at(x1, y1)), (x0, y1, terrain.at(x0, y1))]
                for tri in ((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])):
                    raster.triangle(tri, shade(tri, (196, 178, 148)))

        # buildings near the camera, extruded from their OSM footprints
        for record in buildings:
            bx, by = F.ue_xy(record['centre'][0], record['centre'][1])
            if abs(bx - cx) > radius or abs(by - cy) > radius:
                continue
            ring = [F.ue_xy(p[0], p[1]) for p in record['points']]
            base = F.ue_z(record['base'])
            top = base + F.ue_z(record['height'])
            for k in range(len(ring)):
                a, b = ring[k], ring[(k + 1) % len(ring)]
                wall = [(a[0], a[1], base), (b[0], b[1], base), (b[0], b[1], top), (a[0], a[1], top)]
                for tri in ((wall[0], wall[1], wall[2]), (wall[0], wall[2], wall[3])):
                    raster.triangle(tri, shade(tri, (214, 201, 172)))
            for k in range(1, len(ring) - 1):
                tri = ((ring[0][0], ring[0][1], top), (ring[k][0], ring[k][1], top),
                       (ring[k + 1][0], ring[k + 1][1], top))
                raster.triangle(tri, shade(tri, (188, 176, 154)))

        # the paving itself
        count = 0
        for path in obj_files:
            for tri in load_obj_triangles(path, (cx, cy), radius):
                raster.triangle(tri, shade(tri, (176, 170, 156)))
                count += 1
        out = OUT / ('preview-%s.png' % camera['name'])
        write_png(out, WIDTH, HEIGHT, raster.pixels)
        print('%s  %d paving triangles in view' % (out, count), flush=True)


if __name__ == '__main__':
    main()
