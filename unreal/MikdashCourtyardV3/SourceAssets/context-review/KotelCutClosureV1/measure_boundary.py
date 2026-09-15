"""Read frozen geometry and measure K2's open excavation boundary; no Unreal imports.

Run with Python 3.8+: python -B <this file> [--check]
Default writes only boundary-samples.json beside this script. --check is read-only.
This is a diagnosis, not a geometry generator or a native visibility test.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "SourceAssets/FutureMountV1/terrain-generated/SM_JerusalemTerrain_07_08_FutureMountCut.mesh.json"
PLAN = ROOT / "SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json"
TWIN = ROOT / "Content/MikdashV3/KotelPlazaCutV3/SM_JerusalemTerrain_07_08_FutureMountCut_KotelPlazaCut.uasset"
NATIVE = ROOT / "SourceAssets/enclosure-review/native-terrain-cut-assets-Candidate48-20260911T121133563106Z.json"
IMAGE = ROOT / "SourceAssets/visual-review/city-facade/cfafter-cp24-K2-kotel-upper-deck-facing-jewish-quarter.png"
MODULES = ROOT / "SourceAssets/enclosure-review/plaza-manifest.json"
CUT_RECIPE = ROOT / "Scripts/release_precinct_terrain_cut.py"
PLAZA_RECIPE = ROOT / "Scripts/create_kotel_plaza.py"
EXPECTED = {
    SOURCE: "abc6152db1d10b80476870ac843bfde232b30ccac90733994e3ecf743579095a",
    PLAN: "f3483bff589169159bc99200761d90230e4726ec248226c948f0ead6dedca69c",
    TWIN: "ed26cb8d2710b4a425985fed31c095fe59c13cc1f0068454bc7d53092aa78211",
}
CAMERA = (-20732.0, 19230.0, -814.0)
PITCH = 6.0
YAWS = (150, 160, 170, 175, 180, 190, 200)
DECK_HALF_SIZE_CM = 625.0
THICKNESS_CM = 50.0
EDGE_SNAP_CM = 0.01


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def rectangles(plan, snapped):
    result = []
    for row in plan["deck"]:
        assert row["rot"] == [0.0, 0.0, 0.0] and row["scale"][2] == 1.0
        x, y, z = row["loc"]
        hx, hy = [DECK_HALF_SIZE_CM * v for v in row["scale"][:2]]
        edges = [x - hx, y - hy, x + hx, y + hy]
        if snapped:
            # Exactly release_precinct_terrain_cut.kotel_job's V3 lattice.
            edges = [round(round(v / EDGE_SNAP_CM) * EDGE_SNAP_CM, 6) for v in edges]
        result.append((edges, z))
    return result


def ray_exit(rects, origin, direction):
    """First exit from the union connected to t=0, using analytic slab intervals."""
    intervals = []
    for (xmin, ymin, xmax, ymax), unused_z in rects:
        lo, hi = 0.0, float("inf")
        for p, d, vmin, vmax in zip(origin, direction, (xmin, ymin), (xmax, ymax)):
            if abs(d) < 1e-12:
                if p < vmin or p > vmax:
                    hi = -1.0
                    break
            else:
                a, b = (vmin - p) / d, (vmax - p) / d
                lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
        if hi >= lo:
            intervals.append((lo, hi))
    intervals.sort()
    assert intervals and intervals[0][0] <= 1e-7, "Camera XY must be on deck"
    end = intervals[0][1]
    for lo, hi in intervals[1:]:
        # Original deck cells have sub-millimetre numerical cracks. These are not
        # the metre-high outside excavation edge. V3 cut edges are snapped.
        if lo > end + 0.01:
            break
        end = max(end, hi)
    return end


def heights_at(rects, x, y):
    return [z for (a, b, c, d), z in rects if a <= x <= c and b <= y <= d]


def ground_at(source, x, y):
    """Interpolate actual source triangles, never the bilinear DEM approximation."""
    hits = []
    for index, face in enumerate(source["triangles"]):
        a, b, c = [source["vertices"][i] for i in face]
        det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(det) < 1e-8:
            continue
        u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / det
        v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / det
        w = 1.0 - u - v
        if min(u, v, w) >= -1e-8:
            hits.append((u * a[2] + v * b[2] + w * c[2], index))
    assert hits, "Boundary must remain on the source terrain, outside its platform hole"
    assert max(z for z, unused in hits) - min(z for z, unused in hits) < 0.01
    return hits[0][0], [index for unused, index in hits]


def measure():
    hashes = {relative(p): sha(p) for p in (
        SOURCE, PLAN, TWIN, NATIVE, IMAGE, MODULES, CUT_RECIPE, PLAZA_RECIPE, Path(__file__).resolve())}
    for path, expected in EXPECTED.items():
        assert hashes[relative(path)] == expected, "Frozen input changed: " + str(path)
    source = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    plan = json.loads(PLAN.read_text(encoding="utf-8-sig"))
    native = json.loads(NATIVE.read_text(encoding="utf-8-sig"))
    modules = json.loads(MODULES.read_text(encoding="utf-8-sig"))
    bounds = next(m["canonicalBoundsCm"] for m in modules["meshes"] if m["name"] == "SM_PlazaV1_DeckTile")
    assert bounds["min"] == [-625.0, -625.0, -50.0] and bounds["max"] == [625.0, 625.0, 0.0]
    assert source["units"] == "centimeters" and source["axes"] == "east,south,up"
    assert source["anchorAlreadyApplied"] is True
    assert len(source["triangles"]) == 566
    assert len(plan["deck"]) == 959
    cut = rectangles(plan, True)
    deck = rectangles(plan, False)
    x, y, z = CAMERA
    camera_decks = heights_at(deck, x, y)
    assert len(camera_decks) == 1
    samples = []
    for yaw in YAWS:
        direction = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
        distance = ray_exit(cut, CAMERA[:2], direction)
        bx, by = x + distance * direction[0], y + distance * direction[1]
        top, triangles = ground_at(source, bx, by)
        # One hundredth of a centimetre inside the cut resolves edge ownership.
        inside = heights_at(cut, bx - direction[0] * 0.01, by - direction[1] * 0.01)
        outside = heights_at(cut, bx + direction[0] * 0.01, by + direction[1] * 0.01)
        assert inside and not outside
        deck_top = max(inside)
        cut_bottom = min(inside) - THICKNESS_CM
        ray_z = z + distance * math.tan(math.radians(PITCH))
        assert top > deck_top
        samples.append({
            "yawDegrees": yaw,
            "cutBoundaryDistanceCm": distance,
            "deckBoundaryDistanceCm": ray_exit(deck, CAMERA[:2], direction),
            "boundaryXYcm": [bx, by],
            "sourceTriangleIndices": triangles,
            "sourceGroundZcm": top,
            "insideDeckTopZcm": deck_top,
            "insideCutTargetZcm": cut_bottom,
            "missingVerticalSurfaceHeightCm": top - cut_bottom,
            "uncoveredAboveDeckHeightCm": top - deck_top,
            "cameraPitchRayZcm": ray_z,
            "rayBelowSourceGroundCm": top - ray_z,
            "openAboveDeckAngularIntervalDegrees": [
                math.degrees(math.atan2(deck_top - z, distance)),
                math.degrees(math.atan2(top - z, distance)),
            ],
        })
    native_twin = next(t for t in native["twins"] if t.get("kind") == "kotel")
    assert native_twin["uassetSha256"] == EXPECTED[TWIN]
    return {
        "status": "offline_open_boundary_measured_native_pixel_attribution_pending",
        "scope": "K2 west-facing cut edge samples only; not an exhaustive perimeter coverage audit",
        "sourceHashesSha256": hashes,
        "camera": {"locationCm": list(CAMERA), "pitchDegrees": PITCH, "yawDegrees": 175.0,
                   "rollDegrees": 0.0, "basis": "capture_city_facade.ps1 K2 BugItGo request; not fresh native camera readback",
                   "deckTopZcm": camera_decks[0], "eyeAboveDeckCm": z - camera_decks[0],
                   "sourceTerrainZcm": ground_at(source, x, y)[0]},
        "sourceTriangleCount": len(source["triangles"]),
        "deckCellCount": len(plan["deck"]),
        "existingPerimeterBandCount": len(plan["band"]),
        "cutEdgeSnapCm": EDGE_SNAP_CM,
        "intervalMergeToleranceCm": 0.01,
        "method": "Analytic ray versus union of axis-aligned V3 snapped deck rectangles; barycentric height on frozen 566-triangle mesh. Angular intervals are geometric elevations, not pixel projections or occlusion tests.",
        "nativeAssetReceiptEvidence": {k: native_twin[k] for k in (
            "sourceTriangles", "twinTriangles", "windingAgrees", "windingTriangles", "readback")},
        "samples": samples,
        "limitations": [
            "No Unreal process, native render, collision trace, or asset edit performed.",
            "Absence of closure faces is established by build_twin's code path, not by reading cooked GPU buffers.",
            "The native receipt confirms saved source-model parity, not complete scene occlusion.",
            "Existing road ribbons, buildings, reflected objects, and other scene actors are not included in these ray calculations.",
            "The image's distant-city-looking band is consistent with the open seam; exclusive pixel causation remains unproven.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare existing receipt without writing")
    args = parser.parse_args()
    result = measure()
    target = HERE / "boundary-samples.json"
    if args.check:
        assert json.loads(target.read_text(encoding="utf-8")) == result, "Receipt differs from fresh calculation"
        print("PASS: frozen inputs, 566 source triangles, 7 analytic edge samples, existing receipt reproduced")
    else:
        target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("Wrote " + str(target))
