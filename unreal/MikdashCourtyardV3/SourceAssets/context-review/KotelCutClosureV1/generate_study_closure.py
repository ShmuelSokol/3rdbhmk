"""Pure offline exterior-cut closure for an unsaved Entry-scene A/B only.

No Unreal dependency, no asset export/import, no edits outside this folder.
Writes closure-study.json; --check reproduces it without writes. Internal step
boundaries are counted but deliberately excluded from this exterior-seam study.
"""
import argparse
import json
import math
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE / "measure_boundary.py"))


def exterior_segments(rects):
    """Exact rectilinear arrangement; overlapping rectangles take lowest target."""
    xs = sorted({v for r, z in rects for v in (r[0], r[2])})
    ys = sorted({v for r, z in rects for v in (r[1], r[3])})
    xi, yi = {v: i for i, v in enumerate(xs)}, {v: i for i, v in enumerate(ys)}
    floors = {}
    for (a, b, c, d), top in rects:
        for i in range(xi[a], xi[c]):
            for j in range(yi[b], yi[d]):
                floors[i, j] = min(floors.get((i, j), float("inf")), top - 50.0)
    out, internal = [], 0
    for (i, j), floor in sorted(floors.items()):
        for di, dj, a, b, normal in (
            (-1, 0, (xs[i], ys[j]), (xs[i], ys[j + 1]), (1, 0, 0)),
            (1, 0, (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (-1, 0, 0)),
            (0, -1, (xs[i], ys[j]), (xs[i + 1], ys[j]), (0, 1, 0)),
            (0, 1, (xs[i], ys[j + 1]), (xs[i + 1], ys[j + 1]), (0, -1, 0)),
        ):
            neighbor = floors.get((i + di, j + dj))
            if neighbor is None:
                out.append((a, b, floor, normal))
            elif neighbor != floor and (di, dj) in ((1, 0), (0, 1)):
                internal += 1
    return out, internal, len(floors)


def bary(tri, p):
    a, b, c = tri
    det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    assert abs(det) > 1e-8
    u = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / det
    v = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / det
    return u, v, 1.0 - u - v


def clip_segment(tri, a, b):
    """Clip parameter interval against all three barycentric halfplanes."""
    wa, wb = bary(tri, a), bary(tri, b)
    lo, hi = 0.0, 1.0
    for av, bv in zip(wa, wb):
        change = bv - av
        if abs(change) < 1e-12:
            if av < -1e-10:
                return None
        elif change > 0:
            lo = max(lo, -av / change)
        else:
            hi = min(hi, -av / change)
    return (lo, hi) if hi - lo > 1e-10 else None


def lerp(a, b, t):
    return [x + (y - x) * t for x, y in zip(a, b)]


def cross(a, b, c):
    u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
    return [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]


def build(source, rects):
    edges, internal, cells = exterior_segments(rects)
    source_triangles = [[source["vertices"][i] for i in face] for face in source["triangles"]]
    vertices, normals, uv, faces, pieces = [], [], [], [], []
    source_missing_length = 0.0
    for edge_index, (a, b, floor, normal) in enumerate(edges):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        hits = []
        for ti, tri in enumerate(source_triangles):
            interval = clip_segment(tri, a, b)
            if interval:
                hits.append((interval[0], interval[1], ti))
        # Split all overlaps first. A segment lying on a source-triangle edge
        # must produce one curtain, not two coincident copies.
        knots = sorted({0.0, 1.0} | {v for lo, hi, ti in hits for v in (lo, hi)})
        for lo, hi in zip(knots, knots[1:]):
            if (hi - lo) * length < 1e-6:
                continue
            mid = (lo + hi) * 0.5
            covering = [ti for start, end, ti in hits if start - 1e-10 <= mid <= end + 1e-10]
            if not covering:
                # A pre-existing platform hole has no source terrain. Do not
                # invent a face across it or infer a height from nearest ground.
                source_missing_length += (hi - lo) * length
                continue
            za = []
            zb = []
            for ti in covering:
                tri = source_triangles[ti]
                za.append(sum(w * p[2] for w, p in zip(bary(tri, lerp(a, b, lo)), tri)))
                zb.append(sum(w * p[2] for w, p in zip(bary(tri, lerp(a, b, hi)), tri)))
            assert max(za) - min(za) < 0.01 and max(zb) - min(zb) < 0.01
            z0, z1 = za[0], zb[0]
            if max(z0, z1) <= floor + 1e-7:
                continue
            if min(z0, z1) < floor:
                t = (floor - z0) / (z1 - z0)
                root = lo + (hi - lo) * t
                if z0 < floor:
                    lo, z0 = root, floor
                else:
                    hi, z1 = root, floor
            p, q = lerp(a, b, lo), lerp(a, b, hi)
            quad = [p + [floor], q + [floor], q + [z1], p + [z0]]
            first = len(faces)
            for order in ((0, 1, 2), (0, 2, 3)):
                triangle = [quad[k] for k in order]
                n = cross(*triangle)
                if math.sqrt(sum(v*v for v in n)) < 1e-7:
                    continue
                if sum(n[k] * normal[k] for k in range(3)) < 0:
                    triangle.reverse()
                n = cross(*triangle)
                assert sum(n[k] * normal[k] for k in range(3)) > 0
                indices = []
                for v in triangle:
                    indices.append(len(vertices))
                    vertices.append(v)
                    normals.append(list(normal))
                    uv.append([math.hypot(v[0]-a[0], v[1]-a[1])/100.0, (v[2]-floor)/100.0])
                faces.append(indices)
            pieces.append({"edgeIndex": edge_index, "sourceTriangles": covering,
                           "xyEndpointsCm": [p, q], "bottomZcm": floor, "topZcm": [z0, z1],
                           "cavityNormal": list(normal), "triangleStart": first,
                           "triangleCount": len(faces) - first})
    return {"vertices": vertices, "normals": normals, "uv0": uv, "triangles": faces,
            "pieces": pieces, "arrangementCells": cells, "exteriorAtomicEdges": len(edges),
            "internalLevelEdgesExcluded": internal,
            "exteriorLengthWithoutSourceTerrainCm": source_missing_length}


def self_check():
    edges, internal, cells = exterior_segments([([0,0,1,1],0), ([1,0,2,1],0)])
    assert len(edges) == 6 and internal == 0 and cells == 2
    edges, internal, cells = exterior_segments([([0,0,2,2],0), ([1,1,2,2],-100)])
    assert internal == 2 and cells == 4
    s = {"vertices": [[0,0,10],[2,0,10],[2,2,10],[0,2,10]], "triangles": [[0,1,2],[0,2,3]]}
    result = build(s, [([0.5,0.5,1.5,1.5],50)])
    area = sum(math.sqrt(sum(v*v for v in cross(*[result["vertices"][i] for i in f]))) * 0.5
               for f in result["triangles"])
    assert abs(area - 40.0) < 1e-8, "Shared triangle diagonals must not double the curtain"
    assert result["exteriorLengthWithoutSourceTerrainCm"] == 0


def generate():
    self_check()
    baseline = M["measure"]()  # all original pinned-input and deck-module checks
    source = json.loads(M["SOURCE"].read_text(encoding="utf-8-sig"))
    plan = json.loads(M["PLAN"].read_text(encoding="utf-8-sig"))
    result = build(source, M["rectangles"](plan, True))
    # Each measured west-edge gap must have exactly one closure piece at its XY.
    for sample in baseline["samples"]:
        x, y = sample["boundaryXYcm"]
        matching = []
        for piece in result["pieces"]:
            a, b = piece["xyEndpointsCm"]
            d2 = sum((b[i]-a[i])**2 for i in range(2))
            t = ((x-a[0])*(b[0]-a[0])+(y-a[1])*(b[1]-a[1])) / d2
            point = lerp(a, b, t)
            if -1e-7 <= t <= 1+1e-7 and math.hypot(point[0]-x, point[1]-y) < 0.001:
                z = piece["topZcm"][0] + t*(piece["topZcm"][1]-piece["topZcm"][0])
                matching.append((piece["bottomZcm"], z))
        assert matching
        assert all(abs(lo-sample["insideCutTargetZcm"]) < 0.001 and
                   abs(hi-sample["sourceGroundZcm"]) < 0.001 for lo, hi in matching)
    result.update({"status": "offline_study_geometry_only_native_AB_pending", "units": "world centimeters",
                   "sourceHashesSha256": baseline["sourceHashesSha256"],
                   "generatorSha256": M["sha"](Path(__file__).resolve()),
                   "camera": baseline["camera"], "westSamplesCovered": len(baseline["samples"]),
                   "scope": "Exterior boundary of snapped cut union only. Not a watertight terrain solid; existing platform holes and internal level edges are not closed.",
                   "normalsAndWinding": "Mathematical cross products agree with cavity-facing normals; native one-sided front-face check still required."})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = generate()
    path = HERE / "closure-study.json"
    if args.check:
        assert json.loads(path.read_text(encoding="utf-8")) == result
        print("PASS: union, overlap and seam tests; seven west samples; existing geometry reproduced")
    else:
        path.write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
        print("Study only: %d triangles, %d exterior edges, %d internal edges excluded, %.6f cm lacks source terrain" %
              (len(result["triangles"]), result["exteriorAtomicEdges"], result["internalLevelEdgesExcluded"], result["exteriorLengthWithoutSourceTerrainCm"]))
