"""Offline future-scenario platform and edge-skirt source; no Unreal imports.

Run with bundled Python3.12. Dependencies pinned in FutureMountV1/requirements.txt;
optional isolated .tools directory is LOCAL ONLY and must not be committed.
Uses GEOS constrained Delaunay, not a fan or centroid-filtered triangulation.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
OUTPUT = ROOT / "SourceAssets/FutureMountV1"
if (OUTPUT / ".tools").is_dir():
    sys.path.insert(0, str(OUTPUT / ".tools"))
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.geometry.polygon import orient

SOURCE_MESH = Path(r"C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\architecture-review\jerusalem-meshes.json")
DESIGN = ROOT / "SourceAssets/visual-review/mount-platform-design.json"
EXPECTED_MESH_SHA = "cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb"
TOP_Z = 0.0
WALL_INSET_CM = 110.0
GUARD_BUFFER_CM = 201.0
SKIRT_MAX_DEPTH_CM = 4000.0
SKIRT_SAMPLE_SPACING_CM = 250.0
AREA_TOLERANCE_CM2 = 0.01


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygon_parts(geometry):
    if isinstance(geometry, Polygon):
        return [geometry]
    assert isinstance(geometry, MultiPolygon), "Unexpected non-polygon output"
    return list(geometry.geoms)


def triangulate_verified(geometry):
    assert geometry.is_valid and not geometry.is_empty and geometry.area > 0
    result = shapely.constrained_delaunay_triangles(geometry)
    triangles = list(result.geoms)
    assert triangles and all(isinstance(t, Polygon) and len(t.exterior.coords) == 4
                             and t.area > 1e-8 for t in triangles)
    union = shapely.union_all(triangles)
    outside_area = union.difference(geometry).area
    gap_area = geometry.difference(union).area
    overlap_area = sum(t.area for t in triangles) - union.area
    assert outside_area < AREA_TOLERANCE_CM2, "Triangle escapes intended polygon"
    assert gap_area < AREA_TOLERANCE_CM2, "Triangulation leaves gaps"
    assert abs(overlap_area) < AREA_TOLERANCE_CM2, "Triangle interiors overlap"
    return triangles, {"outsideAreaCm2": outside_area, "uncoveredAreaCm2": gap_area,
                       "overlapAreaCm2": overlap_area, "triangleCount": len(triangles)}


def self_test():
    # Concavity and a genuine internal protected hole; a triangle fan cannot pass.
    outer = Polygon([(0, 0), (100, 0), (100, 30), (65, 30), (65, 100), (0, 100)],
                    holes=[[(10, 10), (30, 10), (30, 30), (10, 30)]])
    _, result = triangulate_verified(outer)
    assert result["triangleCount"] > 6
    split = MultiPolygon([outer, Polygon([(200, 0), (210, 0), (210, 10), (200, 10)])])
    triangulate_verified(split)


def terrain_sampler():
    assert sha(SOURCE_MESH) == EXPECTED_MESH_SHA, "Retained terrain source changed"
    document = json.loads(SOURCE_MESH.read_text(encoding="utf-8"))
    mesh = document["meshes"][0]
    assert mesh["name"] == "Terrain 0"
    positions = mesh["positions"]
    grid = {(positions[i], positions[i + 2]): positions[i + 1]
            for i in range(0, len(positions), 3)}
    assert len(grid) == 257 * 257

    def sample(x_cm, y_cm):
        x = x_cm / 50.0 - 17.509700315687695
        z = y_cm / 50.0 + 0.5513496449385334
        x0, z0 = math.floor(x / 50) * 50, math.floor(z / 50) * 50
        a, b = (x - x0) / 50, (z - z0) / 50
        h00, h10 = grid[x0, z0], grid[x0 + 50, z0]
        h01, h11 = grid[x0, z0 + 50], grid[x0 + 50, z0 + 50]
        height = (h00 + (h10 - h00) * a + (h01 - h00) * b if a + b <= 1
                  else h11 + (h01 - h11) * (1 - a) + (h10 - h11) * (1 - b))
        return height * 50.0
    return sample


def write_obj(path, vertices_cm, faces, material):
    # OBJ is conventional right-handed Blender metres: east,north,up.
    # JSON remains explicitly UE east,south,up centimetres for native adapters.
    lines = ["# FutureMountV1 user-directed scenario; Blender metres east/north/up",
             "# Do not apply the retained OSM anchor transform again.", "mtllib mount-platform.mtl",
             "o " + path.stem, "usemtl " + material]
    lines += ["v %.9f %.9f %.9f" % (x / 100, -y / 100, z / 100) for x, y, z in vertices_cm]
    # Coordinate reflection changes winding; reverse once to preserve intended normals.
    lines += ["f %d %d %d" % (a + 1, c + 1, b + 1) for a, b, c in faces]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def segment_fractions(a, b):
    """Split at every original DEM triangle boundary, plus bounded panel lengths."""
    count = max(1, int(math.ceil(math.dist(a, b) / SKIRT_SAMPLE_SPACING_CM)))
    fractions = {i / count for i in range(count + 1)}
    # Source grid50amot =2500cm. Its two triangles split on x+z=grid multiple.
    offset_x, offset_y = 17.509700315687695 * 50, -.5513496449385334 * 50
    for av, bv, offset in ((a[0], b[0], offset_x), (a[1], b[1], offset_y),
                           (a[0] + a[1], b[0] + b[1], offset_x + offset_y)):
        if abs(bv - av) < 1e-10:
            continue
        low, high = sorted(((av - offset) / 2500, (bv - offset) / 2500))
        for gridline in range(math.floor(low) + 1, math.ceil(high)):
            t = (offset + gridline * 2500 - av) / (bv - av)
            if 0 < t < 1:
                fractions.add(t)
    ordered = sorted(fractions)
    return [t for i, t in enumerate(ordered) if i == 0 or t - ordered[i - 1] > 1e-9]


def run():
    OUTPUT.mkdir(exist_ok=True)
    assert shapely.__version__ == "2.1.2", "Use pinned Shapely"
    assert shapely.geos_version >= (3, 10, 0)
    self_test()
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    enclosure = Polygon(design["boundary"]["nativeXYcm"])
    assert enclosure.is_valid and enclosure.exterior.is_simple
    protections = [Polygon(item["nativeXYcm"]) for item in design["protected"]]
    assert all(item.is_valid for item in protections)
    guards = shapely.union_all([shapely.buffer(item, GUARD_BUFFER_CM, quad_segs=16)
                               for item in protections])
    # Existing exported perimeter walls are nominally200cm wide;110cm inset leaves
    # a10cm assembly clearance behind their interior face. It never expands enclosure.
    inset = shapely.buffer(enclosure, -WALL_INSET_CM, join_style="mitre", mitre_limit=2)
    allowed = inset.difference(guards)
    assert allowed.is_valid and allowed.area > 0 and enclosure.covers(allowed)
    minimum_distances = [allowed.distance(item) for item in protections]
    assert all(value >= 200.0 for value in minimum_distances), "Protected guard eroded"
    triangles, checks = triangulate_verified(allowed)
    assert shapely.union_all(triangles).intersection(guards).area < AREA_TOLERANCE_CM2
    vertices, faces, indices = [], [], {}

    def vertex(point):
        key = tuple(float(value) for value in point)
        if key not in indices:
            indices[key] = len(vertices)
            vertices.append(list(key))
        return indices[key]

    for triangle in triangles:
        coordinates = list(orient(triangle, sign=1.0).exterior.coords)[:3]
        faces.append([vertex((x, y, TOP_Z)) for x, y in coordinates])
    # Verify that every retained polygon edge participates in the top mesh boundary.
    edge_count = {}
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((a, b)))
            edge_count[edge] = edge_count.get(edge, 0) + 1
    assert all(count in (1, 2) for count in edge_count.values())
    mesh_boundary = shapely.union_all([LineString([vertices[a][:2], vertices[b][:2]])
                                      for (a, b), count in edge_count.items() if count == 1])
    assert mesh_boundary.hausdorff_distance(allowed.boundary) < 0.001

    sample = terrain_sampler()
    skirt_vertices, skirt_faces, capped, skirt_projections = [], [], [], []
    rings = []
    for part in polygon_parts(allowed):
        oriented = orient(part, sign=1.0)
        for ring in [oriented.exterior] + list(oriented.interiors):
            points = list(ring.coords)
            rings.append(points)
            for a, b in zip(points, points[1:]):
                fractions = segment_fractions(a, b)
                for t0, t1 in zip(fractions, fractions[1:]):
                    start = [a[j] + (b[j] - a[j]) * t0 for j in range(2)]
                    end = [a[j] + (b[j] - a[j]) * t1 for j in range(2)]
                    bottoms = []
                    for point in (start, end):
                        desired = min(-20.0, sample(*point) - 20.0)
                        if desired < -SKIRT_MAX_DEPTH_CM:
                            capped.append({"xyCm": point, "desiredBottomZcm": desired})
                        bottoms.append(max(-SKIRT_MAX_DEPTH_CM, desired))
                    n = len(skirt_vertices)
                    skirt_vertices.extend([[*start, TOP_Z], [*end, TOP_Z],
                                           [*end, bottoms[1]], [*start, bottoms[0]]])
                    skirt_faces.extend([[n, n + 3, n + 2], [n, n + 2, n + 1]])
                    skirt_projections.append(LineString([start, end]))
    skirt_projection = shapely.union_all(skirt_projections)
    assert skirt_projection.hausdorff_distance(allowed.boundary) < 0.001
    assert skirt_projection.intersection(shapely.union_all(protections)).is_empty
    assert all(-SKIRT_MAX_DEPTH_CM <= point[2] <= TOP_Z for point in skirt_vertices)
    assert not capped, "Skirt safety bound would leave an edge gap; review terrain before extending"

    mesh_source = {
        "version": "FutureMountV1-platform-source-1", "units": "Unreal centimetres",
        "axes": ["east", "south", "up"], "anchorAlreadyApplied": True,
        "winding": "Mathematical CCW top+Z; Blender OBJ conversion reverses reflectedY exactly once",
        "surface": {"vertices": vertices, "triangles": faces},
        "skirt": {"vertices": skirt_vertices, "triangles": skirt_faces},
        "allowedBoundaryRingsXYcm": rings,
    }
    (OUTPUT / "mount-platform.mesh.json").write_text(json.dumps(mesh_source, separators=(",", ":")) + "\n")
    write_obj(OUTPUT / "mount-platform-surface.obj", vertices, faces, "PlatformReviewStone")
    write_obj(OUTPUT / "mount-platform-skirt.obj", skirt_vertices, skirt_faces, "PlatformReviewEdge")
    (OUTPUT / "mount-platform.mtl").write_text(
        "# Neutral inspection placeholders, not approved production stone\n"
        "newmtl PlatformReviewStone\nKd 0.63 0.59 0.51\nKs 0 0 0\nNs 1\n"
        "newmtl PlatformReviewEdge\nKd 0.48 0.44 0.37\nKs 0 0 0\nNs 1\n")
    (OUTPUT / "requirements.txt").write_text("shapely==2.1.2\nnumpy==2.5.3\n")
    (OUTPUT / ".gitignore").write_text(".tools/\n__pycache__/\n")
    files = ["mount-platform.mesh.json", "mount-platform-surface.obj", "mount-platform-skirt.obj",
             "mount-platform.mtl", "requirements.txt", ".gitignore"]
    report = {
        "status": "offline_mesh_generated_geometrically_verified_native_review_pending",
        "designSha256": sha(DESIGN), "generatorSha256": sha(Path(__file__)),
        "retainedTerrainSourceSha256": EXPECTED_MESH_SHA,
        "tools": {"python": sys.version, "shapely": shapely.__version__, "geos": shapely.geos_version_string,
                  "installation": "Isolated .tools directory; do not commit installed packages"},
        "apiReferences": ["https://shapely.readthedocs.io/en/stable/reference/shapely.constrained_delaunay_triangles.html",
                          "https://shapely.readthedocs.io/en/stable/reference/shapely.buffer.html"],
        "futureSceneRules": {
            "mountTrees": "User requires no trees on the Mount itself. Classification uses the full original enclosure ring, not just the inset platform polygon.",
            "treeClassification": "Classify each retained trunk ground-anchor in native XY against the closed enclosure polygon; inside or boundary anchors are scenario removal candidates. Remove matching crown instances by retained source-tree identity, never nearest-neighbor guesses.",
            "outsideVegetation": "Preserve every outside-tree identity, transform and color. Never hide/delete an entire shared trunk/crown ISM actor or spatial chunk. Outside vegetation upgrades require actual mapped/satellite evidence, not invented placements.",
            "execution": "This generator does not edit any tree instance or generate roads, bus stops, railway stations or other transit. Those are separate scoped integration tasks."
        },
        "enclosureAreaM2": enclosure.area / 10000, "platformAreaM2": allowed.area / 10000,
        "wallCentrelineInsetCm": WALL_INSET_CM, "guardBufferCm": GUARD_BUFFER_CM,
        "minimumDistanceToProtectedPolygonsCm": minimum_distances,
        "polygonComponents": len(polygon_parts(allowed)),
        "interiorHoleCount": sum(len(p.interiors) for p in polygon_parts(allowed)),
        "surfaceVertices": len(vertices), "surfaceTriangles": len(faces),
        "skirtVertices": len(skirt_vertices), "skirtTriangles": len(skirt_faces),
        "skirtMaxDepthCm": SKIRT_MAX_DEPTH_CM, "skirtDepthCappedSamples": capped,
        "checks": dict(checks, protectedOverlapAreaCm2=0, boundaryHausdorffErrorCm=mesh_boundary.hausdorff_distance(allowed.boundary),
                       concaveAndInternalHoleAndMultipolygonSelfTests="passed"),
        "files": {name: {"sha256": sha(OUTPUT / name), "bytes": (OUTPUT / name).stat().st_size} for name in files},
        "limits": [
            "Offline source mesh only: no Unreal import, map placement, collision, package or visual acceptance.",
            "Native editor overlay must review the inferred wall-chain boundary and protected offsets before adoption.",
            "Measured Temple geometry is untouched. Deck below elevated floors is intentional; no slab replaces gateway treads.",
            "Skirt splits at original terrain triangle boundaries and follows retained terrain with20cm overlap, safety-bounded40m. It is an edge surface, not engineered retaining-wall design.",
            "Existing interior terrain aboveZ0 and old road ribbons/instances remain unchanged; clipping/regrounding is a separate task. Do not adopt this overlay as a finished platform.",
            "Kotel approach stairs and gateway openings are NOT generated here. Protected2m engineering buffers remain empty.",
            "Neutral MTL is for mesh inspection only. PBR Jerusalem-stone material assignment and texel-scale visual review remain pending."
        ],
    }
    (OUTPUT / "mount-platform-generation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "areaM2": report["platformAreaM2"],
                      "surfaceTriangles": len(faces), "skirtTriangles": len(skirt_faces),
                      "skirtDepthCappedSamples": len(capped)}))


if __name__ == "__main__":
    run()
