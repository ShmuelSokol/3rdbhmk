"""Pure decision rules for world_sanity_scan.py. No `unreal` import, so they test offline.

Every rule takes plain numbers/strings and returns a finding dict or None. The Unreal
driver gathers the numbers; this file decides what counts as a leftover.
"""
import math
import re

# Gap between an object's bottom and the first surface below it, in cm.
FLOAT_TOLERANCE_CM = 5.0
# How far below the surface an object's bottom may sit before it reads as sunk.
# Walls and foundations are meant to go into the ground, so this applies only to
# objects shorter than SINK_MAX_HEIGHT_CM (stalls, arches, furniture, vessels).
SINK_TOLERANCE_CM = 8.0
SINK_MAX_HEIGHT_CM = 600.0
# Same mesh at the same place: position (cm), rotation (deg), scale (ratio).
DUP_POS_CM = 1.0
DUP_ROT_DEG = 1.0
DUP_SCALE = 0.01

# Things that are meant to be off the ground. Whole-word match on actor label,
# actor class, folder or mesh path (case-insensitive).
INTENDED_AIRBORNE = [
    "bird", "birds", "flock", "dove", "cloud", "clouds", "sky", "skysphere", "skyatmosphere",
    "sun", "moon", "light", "lamp", "lamps", "chandelier", "menorah", "paroches", "curtain",
    "roof", "roofs", "dome", "ceiling", "beam", "beams", "lintel", "arch", "arches",
    "camera", "volume", "fog", "smoke", "plume", "particle", "niagara", "label", "text",
    "sign", "signage", "wire", "cable", "banner", "awning", "balcony", "bridge",
    "antibird", "spike", "spikes", "fx", "decal",
]

# Names that usually mean an earlier build or a study. A hit is a lead, not a verdict.
LEGACY_WORDS = [
    "study", "studies", "legacy", "old", "deprecated", "unused", "backup", "bak", "copy",
    "test", "temp", "tmp", "placeholder", "proxy", "probe", "candidate", "review",
    "square", "squarewall", "plazav1", "osm", "v1", "v2", "draft", "wip",
]

_WORD_SPLIT = re.compile(r"[^a-z0-9]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def words(*texts):
    """Lower-case whole words from labels/paths, splitting CamelCase and separators."""
    out = set()
    for text in texts:
        if not text:
            continue
        for part in _WORD_SPLIT.split(_CAMEL.sub(" ", str(text)).lower()):
            if part:
                out.add(part)
    return out


def matched(word_set, vocabulary):
    return sorted(word_set.intersection(vocabulary))


def classify_support(bottom_z, top_z, surface_z, intended_airborne):
    """Decide floating / sunk / ok for one object.

    surface_z: Z of the first other surface found straight below the object's centre,
    traced from just above its top. None means nothing was found below at all.
    """
    height = max(0.0, top_z - bottom_z)
    if surface_z is None:
        if intended_airborne:
            return None
        return {"kind": "no_ground_below", "gap_cm": None, "height_cm": round(height, 1)}
    gap = bottom_z - surface_z
    if gap > FLOAT_TOLERANCE_CM and not intended_airborne:
        return {"kind": "floating", "gap_cm": round(gap, 1), "height_cm": round(height, 1)}
    if surface_z > top_z:
        return {"kind": "buried", "gap_cm": round(gap, 1), "height_cm": round(height, 1)}
    if -gap > SINK_TOLERANCE_CM and height <= SINK_MAX_HEIGHT_CM:
        return {"kind": "sunk", "gap_cm": round(gap, 1), "height_cm": round(height, 1)}
    return None


def _angle_delta(a, b):
    d = (a - b + 180.0) % 360.0 - 180.0
    return abs(d)


def same_placement(a, b):
    """a, b: dicts with mesh, loc(x,y,z), rot(pitch,yaw,roll), scale(x,y,z)."""
    if a["mesh"] != b["mesh"]:
        return False
    if any(abs(p - q) > DUP_POS_CM for p, q in zip(a["loc"], b["loc"])):
        return False
    if any(_angle_delta(p, q) > DUP_ROT_DEG for p, q in zip(a["rot"], b["rot"])):
        return False
    for p, q in zip(a["scale"], b["scale"]):
        base = max(abs(p), abs(q), 1e-6)
        if abs(p - q) / base > DUP_SCALE:
            return False
    return True


def duplicate_groups(placements):
    """Group placements that are the same mesh in the same place. Returns lists of ids.

    Placements are bucketed into 50 cm cells per mesh; each one is compared with its own
    and the 26 neighbouring cells, so a pair straddling a cell edge is still found.
    """
    cell = 50.0
    buckets = {}
    for item in placements:
        key = (item["mesh"],) + tuple(int(math.floor(v / cell)) for v in item["loc"])
        buckets.setdefault(key, []).append(item)
    parent = {item["id"]: item["id"] for item in placements}

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for key, bucket in buckets.items():
        mesh, cx, cy, cz = key
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    other = buckets.get((mesh, cx + dx, cy + dy, cz + dz))
                    if not other:
                        continue
                    for a in bucket:
                        for b in other:
                            if a["id"] < b["id"] and same_placement(a, b):
                                parent[root(b["id"])] = root(a["id"])
    groups = {}
    for item in placements:
        groups.setdefault(root(item["id"]), []).append(item["id"])
    return sorted((sorted(g) for g in groups.values() if len(g) > 1), key=lambda g: g[0])
