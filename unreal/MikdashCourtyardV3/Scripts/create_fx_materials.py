"""Offline generator for the Mikdash fire, smoke, ember and light-shaft effect set.

No Unreal, no network, no third-party modules. Standard library only, so it runs
under the system Python and under
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe"
identically.

    python Scripts/create_fx_materials.py --export
        Write the six data textures into SourceAssets/fx-review/textures/ and write
        SourceAssets/fx-review/fx-materials.json, the manifest that
        Scripts/release_fx.py consumes.

    python Scripts/create_fx_materials.py --verify
        Re-read the frozen PNGs, re-check their SHA-256 against the manifest, and
        re-derive every numeric parameter from the plume math. Exits non-zero on any
        mismatch. This is what proves the manifest and the bytes agree.

WHAT THIS IS
    A parameter and texture bakery. It derives the numbers that the material graph
    and the actor placement need from the same plume math the C++ runtime uses
    (Plugins/MikdashRuntime/Source/MikdashRuntime/Public/PlumeMath.h), mirrored below
    in Python and cross-checked against the values the standalone C++ test prints.
    It does not talk to the editor. Everything that touches a .umap lives in
    Scripts/release_fx.py.

WHAT IT IS NOT
    Not a fluid solver, not a combustion model, not a claim about how Temple smoke
    behaved. Colour, opacity, rise speed, particle size and duration are artistic
    choices; the research dossier
    C:/Mikdash/GitHub/3rdbhmk/unreal/Research/ketores-service-and-smoke.md says
    explicitly that the texts give qualitative behaviour and no measured values.

SOURCE CLAIMS DEPICTED HERE (recorded as claims, never as physics)
    FX-SRC-STRAIGHT   Avos 5:5 lists among the miracles of the Mikdash that the
                      column of smoke from the arrangement was not dispersed by the
                      wind. The outer altar column is therefore authored vertical at
                      every wind speed. FPlumeProfile::bStraightColumnInWind is the
                      switch, and PlumeMathTest.cpp asserts it returns exactly zero
                      lateral offset from 0 to 2000 cm/s. The physical bent-plume
                      path is kept live and separately tested so that nothing here
                      pretends the straight column is a fluid-dynamics result.
    FX-SRC-KETORES    Yoma 53a describes a stafflike column rising to the ceiling,
                      the smoke then spreading and descending until the chamber is
                      filled. The indoor plume follows that shape: a narrow column
                      (entrainment 0.06), ceiling impingement, radial ceiling jet,
                      then a descending layer. Rise velocity, layer depth and
                      durations are design values; the sugya gives none.
    FX-SRC-TAMID      Shemos 30:7-8 ties the daily incense to tending the lamps, and
                      Rambam Temidin uMusafin 3:1 puts it twice daily on the Golden
                      Altar in the Heikhal. The ketores plume is therefore an EVENT
                      with a beginning and an end, not a permanent emitter. Nothing
                      here schedules it; AMikdashServiceActor does, and
                      AMikdashFXDirector listens.
    FX-SRC-ESH-TAMID  Vayikra 6:6, a perpetual fire on the outer altar, never to go
                      out. The outer altar fire is the one effect authored as
                      continuous.
    FX-SRC-MENORAH    Shemos 27:20 and Vayikra 24:2 specify beaten olive oil for the
                      lamp. Olive oil on a wick, not a torch and not a bonfire: the
                      flame is authored at wick scale, and the flicker rate follows
                      from the wick diameter through the puffing correlation.

HONESTY ABOUT THE PUFFING CORRELATION
    f = 1.5 / sqrt(D_metres) is a widely restated empirical correlation for the
    puffing frequency of buoyant pool fires (Cetegen and Ahmed 1993 and later
    restatements). It is used here for one thing only: to make a 3.25 m fire
    arrangement flicker slowly and a 6 mm wick flicker fast, which is a real
    perceptual difference. It is not a claim that the Temple fire was a pool fire.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "SourceAssets" / "fx-review"
TEXTURES = REVIEW / "textures"
MANIFEST = REVIEW / "fx-materials.json"

SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Python mirror of Plugins/MikdashRuntime/Source/MikdashRuntime/Public/PlumeMath.h
#
# Kept deliberately small: only the entry points whose results end up baked into a
# material parameter or an actor transform. self_check() below reproduces the exact
# numbers PlumeMathTest.cpp prints, so a divergence between this mirror and the
# header is caught here rather than in the editor.
# ---------------------------------------------------------------------------

MAX_LENGTH_CM = 1.0e9
MAX_TIME_S = 1.0e6


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _finite(v: float, fallback: float = 0.0) -> float:
    return v if math.isfinite(v) else fallback


def _clamp_length(v: float) -> float:
    v = _finite(v, 0.0)
    return 0.0 if v < 0.0 else (MAX_LENGTH_CM if v > MAX_LENGTH_CM else v)


def _clamp_time(v: float) -> float:
    v = _finite(v, 0.0)
    return 0.0 if v < 0.0 else (MAX_TIME_S if v > MAX_TIME_S else v)


def plume_rise_speed_cms(profile: dict, height_cm: float) -> float:
    r0 = max(1.0, profile["sourceRadiusCm"])
    w0 = max(1.0, profile["riseSpeedCmS"])
    h = max(0.0, height_cm)
    return w0 * ((r0 / (r0 + h)) ** (1.0 / 3.0))


def plume_radius_cm(profile: dict, height_cm: float) -> float:
    r0 = max(1.0, profile["sourceRadiusCm"])
    alpha = _clamp(profile["entrainmentAlpha"], 0.0, 1.0)
    h = max(0.0, height_cm)
    max_r = max(r0, _clamp_length(profile["maxRadiusCm"]))
    return _clamp_length(_clamp(r0 + alpha * h, r0, max_r))


def plume_time_to_height_s(profile: dict, height_cm: float) -> float:
    r0 = max(1.0, profile["sourceRadiusCm"])
    w0 = max(1.0, profile["riseSpeedCmS"])
    h = max(0.0, height_cm)
    a43 = r0 ** (4.0 / 3.0)
    return _clamp_time(3.0 * ((r0 + h) ** (4.0 / 3.0) - a43) / (4.0 * w0 * r0 ** (1.0 / 3.0)))


def plume_height_at_age_cm(profile: dict, age_s: float) -> float:
    r0 = max(1.0, profile["sourceRadiusCm"])
    w0 = max(1.0, profile["riseSpeedCmS"])
    t = max(0.0, age_s)
    inner = r0 ** (4.0 / 3.0) + (4.0 / 3.0) * w0 * r0 ** (1.0 / 3.0) * t
    h = max(inner, 1e-12) ** 0.75 - r0
    return _clamp(_clamp_length(h), 0.0, _clamp_length(profile["maxHeightCm"]))


def plume_opacity(profile: dict, height_cm: float) -> float:
    r0 = max(1.0, profile["sourceRadiusCm"])
    r = max(r0, plume_radius_cm(profile, height_cm))
    ratio = r0 / r
    floor = _clamp(profile["minOpacity"], 0.0, 1.0)
    return _clamp(ratio * ratio, floor, 1.0)


def ceiling_impingement_time_s(profile: dict, room: dict) -> float:
    rise = room["ceilingZCm"] - room["sourceZCm"]
    if not rise > 0.0:
        return 0.0
    return plume_time_to_height_s(profile, rise)


def ceiling_spread_radius_cm(room: dict, t_s: float) -> float:
    t = max(0.0, t_s)
    tau = max(1e-3, room["spreadTimeConstantS"])
    max_r = _clamp_length(room["roomRadiusCm"])
    return _clamp(max_r * (1.0 - math.exp(-t / tau)), 0.0, max_r)


def ceiling_layer_depth_cm(room: dict, t_s: float) -> float:
    tau = max(1e-3, room["spreadTimeConstantS"])
    t = max(0.0, t_s - tau)
    fill = max(1e-3, room["fillTimeConstantS"])
    max_d = _clamp_length(room["maxLayerDepthCm"])
    return _clamp(max_d * (1.0 - math.exp(-t / fill)), 0.0, max_d)


def puffing_frequency_hz(diameter_cm: float) -> float:
    metres = max(1e-4, diameter_cm * 0.01)
    return _clamp(1.5 / math.sqrt(metres), 0.05, 60.0)


def ember_lognormal_quantile_s(profile: dict, p: float) -> float:
    """Lifetime at probability p of the ember burnout distribution."""
    z = _normal_quantile(p)
    life = profile["medianLifetimeS"] * math.exp(profile["logSigma"] * z)
    return _clamp(life, profile["minLifetimeS"], profile["maxLifetimeS"])


def _normal_quantile(p: float) -> float:
    """Acklam's probit, the same rational approximation the header uses."""
    p = _clamp(p, 1e-12, 1.0 - 1e-12)
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    p_low = 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    elif p <= 1.0 - p_low:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    return _clamp(x, -8.0, 8.0)


def hash_u32(x: int) -> int:
    """MurmurHash3 finalizer, byte for byte the header's HashUint32."""
    x &= 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x7FEB352D) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 0x846CA68B) & 0xFFFFFFFF
    x ^= x >> 16
    return x


def hash_unit(seed: int, index: int, lane: int) -> float:
    a = hash_u32((seed * 0x9E3779B9 + 0x85EBCA6B) & 0xFFFFFFFF)
    b = (index * 0xC2B2AE35) & 0xFFFFFFFF
    c = hash_u32((lane * 0x27D4EB2F + 0x165667B1) & 0xFFFFFFFF)
    return hash_u32(a ^ b ^ c) / 4294967296.0


# ---------------------------------------------------------------------------
# Scene profiles. These are the same numbers as PlumeMathTest.cpp; if one changes,
# both change, and self_check() below fails loudly if they drift apart.
# ---------------------------------------------------------------------------

OUTER_ALTAR_PLUME = {
    "sourceRadiusCm": 250.0,
    "riseSpeedCmS": 340.0,
    "entrainmentAlpha": 0.10,
    "maxRadiusCm": 900.0,
    "maxHeightCm": 4200.0,
    "bendGain": 1.0,
    "straightColumnInWind": True,
    "minOpacity": 0.05,
}

KETORES_PLUME = {
    "sourceRadiusCm": 21.0,
    "riseSpeedCmS": 150.0,
    "entrainmentAlpha": 0.06,
    "maxRadiusCm": 180.0,
    "maxHeightCm": 1920.0,
    "bendGain": 1.0,
    "straightColumnInWind": False,
    "minOpacity": 0.08,
}

HEIKHAL_ROOM = {
    "sourceZCm": 1004.1666666666667,
    "ceilingZCm": 2925.0,
    "roomRadiusCm": 1050.0,
    "spreadTimeConstantS": 7.0,
    "fillTimeConstantS": 28.0,
    "maxLayerDepthCm": 950.0,
}

EMBER_PROFILE = {
    "medianLifetimeS": 1.6,
    "logSigma": 0.55,
    "minLifetimeS": 0.25,
    "maxLifetimeS": 8.0,
    "launchSpeedCmS": 220.0,
    "dragTimeConstantS": 1.1,
}

# Diameters of the burning region, not of the vessel that holds it.
ALTAR_FIRE_DIAMETER_CM = 325.0   # SM_2061..SM_2067 wood arrangement span in X
LAMP_WICK_DIAMETER_CM = 0.6      # design value: no source gives a wick thickness

# ---------------------------------------------------------------------------
# World anchors. Every one of these is read from a receipt or a manifest, never
# invented. The provenance string travels into fx-materials.json with the number.
# ---------------------------------------------------------------------------

FLOOR_Z = 925.0

ANCHORS = {
    "outerAltarCentre": {
        "value": [0.0, 0.0],
        "source": "SourceAssets/architecture-manifest.json, SM_0154..SM_0160: the "
                  "altar tiers are symmetric about the world origin in X and Y",
    },
    "outerAltarFireTopZ": {
        "value": 1091.1666870117188,
        "source": "SourceAssets/architecture-manifest.json, SM_2061..SM_2067 "
                  "detail_Altar_wood expectedBoundsUnrealCm max Z",
    },
    "outerAltarTierTopZ": {
        "value": 1066.6666984558105,
        "source": "SourceAssets/architecture-manifest.json, SM_0160 upper tier max Z",
    },
    "goldenAltarCentre": {
        "value": [-4650.0, 0.0, FLOOR_Z],
        "source": "ServiceScheduleMath.h Anchors::GoldenAltar; "
                  "release_scale_keilim.spec.json cluster",
    },
    "goldenAltarTopZ": {
        "value": 1004.1666666666667,
        "source": "PlumeMathTest.cpp HeikhalRoom(): 925 floor + 79.1667 altar height",
    },
    "heikhalCeilingZ": {
        "value": 2925.0,
        "source": "SM_0148_roof_Sanctuary_ceiling underside, per PlumeMathTest.cpp",
    },
    "menorahOrigin": {
        "value": [-5330.0, 315.17599868774414, FLOOR_Z],
        "source": "SourceAssets/vessels-review/MenorahV4/"
                  "native-import-20260908T030534818522Z.json readback location, yaw -90",
    },
    "menorahLampLocalXCm": {
        "value": [-45.045, -31.47, -16.5, 0.0, 16.5, 31.47, 45.045],
        "source": "SourceAssets/vessels-review/MenorahV4/geometry-manifest.json lamp_x_cm",
    },
    "menorahLampBowlLocalZCm": {
        "value": 143.94,
        "source": "geometry-manifest.json parameters.lamp_span[1]",
    },
    "menorahLidTopLocalZCm": {
        "value": 146.67,
        "source": "geometry-manifest.json parameters.lid_span[1] / finial_span[0]",
    },
    "menorahTopLocalZCm": {
        "value": 150.0,
        "source": "18 tefachim at the 50 cm amah; Rambam Beit HaBechirah 3:10",
    },
    "paroxesX": {
        "value": -5600.0,
        "source": "MikdashServiceActor.h: the paroches line enforced by the runtime",
    },
    "heikhalDoorwayX": {
        "value": -3450.0,
        "source": "ServiceScheduleMath.h Anchors::Doorway",
    },
}


def menorah_lamp_world_positions(local_z_cm: float) -> list:
    """Yaw -90 maps model local +X to world -Y, so the seven lamps run north-south.

    That orientation is the runtime's, recorded in ServiceScheduleMath.h against
    Rambam, Beit HaBechirah 3:8. The X positions are the photograph-calibrated,
    NON-uniform lamp centres from the MenorahV4 geometry manifest, not an even
    seven-way split: the middle branch pair is closer in than a 1:2:3 spacing.
    """
    ox, oy, oz = ANCHORS["menorahOrigin"]["value"]
    out = []
    for lx in ANCHORS["menorahLampLocalXCm"]["value"]:
        out.append([round(ox, 4), round(oy - lx, 4), round(oz + local_z_cm, 4)])
    return out


# ---------------------------------------------------------------------------
# PNG output. Colour type 2 (8-bit RGB), the same stdlib writer this project
# already uses in create_kotel_stone_v2.py. No alpha: every channel carries data,
# and an alpha channel would only invite a compressor to throw one away.
# ---------------------------------------------------------------------------

def write_png_rgb(path: Path, width: int, height: int, rows: list) -> str:
    """rows is a list of `height` bytearrays, each 3*width bytes. Returns SHA-256."""
    raw = bytearray()
    for row in rows:
        raw.append(0)          # filter type 0 (None); these are noise, filters do not help
        raw.extend(row)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack("!I", len(data)) + kind + data +
                struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return hashlib.sha256(png).hexdigest()


def read_png_rgb(path: Path):
    """Minimal reader for the files this script writes: RGB8, filter 0 only."""
    blob = path.read_bytes()
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path.name} is not a PNG")
    pos = 8
    width = height = 0
    idat = []
    while pos < len(blob):
        length = struct.unpack("!I", blob[pos:pos + 4])[0]
        kind = blob[pos + 4:pos + 8]
        data = blob[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, depth, colour = struct.unpack("!2I2B", data[:10])
            if depth != 8 or colour != 2:
                raise ValueError(f"{path.name} is not 8-bit RGB")
        elif kind == b"IDAT":
            idat.append(data)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(b"".join(idat))
    stride = width * 3
    rows = []
    for y in range(height):
        base = y * (stride + 1)
        if raw[base] != 0:
            raise ValueError(f"{path.name} row {y} uses filter {raw[base]}")
        rows.append(bytearray(raw[base + 1:base + 1 + stride]))
    return width, height, rows


# ---------------------------------------------------------------------------
# Tileable value noise.
#
# Deliberately value noise on an integer lattice whose period divides the image
# width, not Perlin or simplex: it wraps exactly, which is the whole point for a
# scrolling smoke card, and the lattice is a pure hash of (ix, iy, seed), so the
# same texture comes out of any machine.
# ---------------------------------------------------------------------------

_OCTAVE_CACHE: dict = {}


def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def octave_plane(width: int, height: int, period: int, seed: int) -> list:
    """One tileable value-noise plane at `period` lattice cells across the image."""
    key = (width, height, period, seed)
    cached = _OCTAVE_CACHE.get(key)
    if cached is not None:
        return cached

    lattice = [hash_unit(seed, iy * 8191 + ix, 0x4E4F4953)
               for iy in range(period) for ix in range(period)]

    # Per-axis index and weight tables, computed once instead of per pixel.
    sx = period / float(width)
    sy = period / float(height)
    ix0 = [0] * width
    ix1 = [0] * width
    fx = [0.0] * width
    for x in range(width):
        u = x * sx
        i0 = int(math.floor(u)) % period
        ix0[x] = i0
        ix1[x] = (i0 + 1) % period
        fx[x] = _smoothstep(u - math.floor(u))
    plane = []
    for y in range(height):
        v = y * sy
        j0 = int(math.floor(v)) % period
        j1 = (j0 + 1) % period
        fy = _smoothstep(v - math.floor(v))
        row0 = j0 * period
        row1 = j1 * period
        out = [0.0] * width
        for x in range(width):
            a = lattice[row0 + ix0[x]]
            b = lattice[row0 + ix1[x]]
            c = lattice[row1 + ix0[x]]
            d = lattice[row1 + ix1[x]]
            t = fx[x]
            top = a + (b - a) * t
            bot = c + (d - c) * t
            out[x] = top + (bot - top) * fy
        plane.append(out)
    _OCTAVE_CACHE[key] = plane
    return plane


def fbm(width: int, height: int, base_period: int, octaves: int, seed: int,
        gain: float = 0.5) -> list:
    """Sum of `octaves` tileable value-noise planes, normalised to [0,1]."""
    planes = []
    amp = 1.0
    total = 0.0
    period = base_period
    for k in range(octaves):
        planes.append((octave_plane(width, height, period, seed + k * 977), amp))
        total += amp
        amp *= gain
        period *= 2
    out = []
    inv = 1.0 / total
    for y in range(height):
        row = [0.0] * width
        for plane, a in planes:
            src = plane[y]
            for x in range(width):
                row[x] += src[x] * a
        for x in range(width):
            row[x] *= inv
        out.append(row)
    return out


def _b(v: float) -> int:
    return 0 if v <= 0.0 else (255 if v >= 1.0 else int(v * 255.0 + 0.5))


# ---------------------------------------------------------------------------
# Texture builders
# ---------------------------------------------------------------------------

def build_noise(size: int = 512) -> tuple:
    """Three independent tileable fBm fields, one per channel.

    R fine (period 32 base), G medium (8), B coarse (4). The material uses R to
    erode a card's edge, G to distort UVs and B to break up the large-scale shape,
    all from a single sample, which is one texture fetch instead of three.
    """
    r = fbm(size, size, 32, 3, 0x1101)
    g = fbm(size, size, 8, 4, 0x2202)
    b = fbm(size, size, 4, 4, 0x3303)
    rows = []
    for y in range(size):
        row = bytearray(size * 3)
        for x in range(size):
            i = x * 3
            row[i] = _b(r[y][x])
            row[i + 1] = _b(g[y][x])
            row[i + 2] = _b(b[y][x])
        rows.append(row)
    return size, size, rows, ("R fine fBm (32 cells), G medium (8), B coarse (4); "
                             "all three tile exactly")


def build_smoke(size: int = 512) -> tuple:
    """A smoke puff card.

    R  density: a soft radial puff multiplied by billowing fBm, so the silhouette is
       lumpy rather than a circle.
    G  erosion: an independent fBm used as the threshold in a masked dissolve, so a
       puff thins out unevenly as it ages instead of fading uniformly.
    B  a clean radial falloff with no noise, for the cases where a soft blob is
       wanted (the haze layers) and the lumps would read as dirt.
    """
    body = fbm(size, size, 6, 5, 0x5150)
    erode = fbm(size, size, 10, 4, 0x6260)
    rows = []
    c = (size - 1) * 0.5
    inv = 1.0 / c
    for y in range(size):
        row = bytearray(size * 3)
        dy = (y - c) * inv
        for x in range(size):
            dx = (x - c) * inv
            d = math.sqrt(dx * dx + dy * dy)
            radial = _clamp(1.0 - d, 0.0, 1.0)
            radial = radial * radial * (3.0 - 2.0 * radial)     # smoothstep shoulder
            lumpy = _clamp(radial * (0.45 + 1.15 * body[y][x]), 0.0, 1.0)
            i = x * 3
            row[i] = _b(lumpy)
            row[i + 1] = _b(erode[y][x])
            row[i + 2] = _b(radial)
        rows.append(row)
    return size, size, rows, ("R lumpy density, G erosion threshold, B clean radial "
                              "falloff; centred, not tileable by design")


def build_flame(size: int = 512) -> tuple:
    """A single upright flame card. V=0 is the TIP, V=1 is the BASE.

    That orientation is deliberate and is the one thing about this texture that is
    easy to get backwards: Unreal's V axis runs down the image, and a quad's V=0 edge
    is its top edge, so the flame tip has to live in image row 0. Baking it the other
    way up produces a flame that reads as a stalactite and looks, in a screenshot,
    almost right.

    R  body: a flame silhouette that necks at the wick, swells just above it and
       tapers to a point, warped by a vertically stretched fBm so the edge licks.
    G  erosion ramp: fBm biased toward the tip, so a masked-erosion dissolve eats the
       tip first and the base stays solid. This is what stops a flame card reading as
       a decal.
    B  core: the hot inner region, narrower than the body and dying out before the
       tip. The material uses it to push the emissive toward white at the centre and
       toward deep orange at the edge, which is the colour gradient a flame has.
    """
    lick = fbm(size, size, 8, 4, 0x464C41)
    rows = []
    for y in range(size):
        # v = 0 at the base, 1 at the tip, but written into the image bottom-up.
        v = 1.0 - y / float(size - 1)
        # Neck: a flame is pinched where it leaves the wick and swells above it.
        neck_t = _clamp(v / 0.18, 0.0, 1.0)
        neck = 0.55 + 0.45 * (neck_t * neck_t * (3.0 - 2.0 * neck_t))
        half = 0.40 * ((1.0 - v) ** 0.55) * neck
        core_half = half * 0.55
        core_fade = _clamp((0.88 - v) / 0.5, 0.0, 1.0)
        row = bytearray(size * 3)
        for x in range(size):
            u = x / float(size - 1) - 0.5
            # Warp the horizontal coordinate with the noise, more with height: the
            # flame leans and wavers as it rises instead of being mirror symmetric.
            warp = (lick[y][x] - 0.5) * 0.20 * v
            d = abs(u + warp)
            body = _clamp(1.0 - d / max(1e-4, half), 0.0, 1.0)
            body = body * body * (3.0 - 2.0 * body)
            core = _clamp(1.0 - d / max(1e-4, core_half), 0.0, 1.0)
            core = (core ** 1.8) * core_fade
            i = x * 3
            row[i] = _b(body)
            row[i + 1] = _b(_clamp(0.22 + 0.78 * lick[y][x] * (0.30 + 0.70 * v), 0.0, 1.0))
            row[i + 2] = _b(core)
        rows.append(row)
    return size, size, rows, ("R flame body, G tip-biased erosion ramp, B hot core; "
                              "V=0 is the tip and V=1 the base, matching a quad whose "
                              "V=0 edge is its top edge")


def build_ember(size: int = 64) -> tuple:
    """A single ember / spark point. R soft dot, G hard dot, B streak along V.

    Two hardnesses because a near ember wants a visible disc and a far one wants a
    point that does not shimmer; the material lerps between them on distance.
    """
    rows = []
    c = (size - 1) * 0.5
    inv = 1.0 / c
    for y in range(size):
        dy = (y - c) * inv
        row = bytearray(size * 3)
        for x in range(size):
            dx = (x - c) * inv
            d = math.sqrt(dx * dx + dy * dy)
            soft = _clamp(1.0 - d, 0.0, 1.0) ** 2.2
            hard = _clamp(1.0 - d * 2.2, 0.0, 1.0)
            hard = hard * hard * (3.0 - 2.0 * hard)
            streak = _clamp(1.0 - abs(dx) * 6.0, 0.0, 1.0) * _clamp(1.0 - abs(dy), 0.0, 1.0)
            i = x * 3
            row[i] = _b(soft)
            row[i + 1] = _b(hard)
            row[i + 2] = _b(streak)
        rows.append(row)
    return size, size, rows, "R soft dot, G hard dot, B vertical streak"


def build_mote(size: int = 64) -> tuple:
    """A dust mote: a very soft disc with a faint bright centre.

    Motes in a light shaft are out-of-focus specks, so the profile is Gaussian-ish
    rather than a hard sprite; a hard sprite aliases badly at the sizes these are
    drawn at.
    """
    rows = []
    c = (size - 1) * 0.5
    inv = 1.0 / c
    for y in range(size):
        dy = (y - c) * inv
        row = bytearray(size * 3)
        for x in range(size):
            dx = (x - c) * inv
            d2 = dx * dx + dy * dy
            soft = math.exp(-d2 * 6.0)
            glint = math.exp(-d2 * 26.0)
            i = x * 3
            row[i] = _b(soft)
            row[i + 1] = _b(glint)
            row[i + 2] = _b(_clamp(soft * 0.6 + glint * 0.4, 0.0, 1.0))
        rows.append(row)
    return size, size, rows, "R soft Gaussian disc, G tight glint, B blend of both"


def build_shaft(width: int = 256, height: int = 256) -> tuple:
    """A light-shaft card, U across the beam and V along it (V=0 at the window).

    R  cross-section: a soft falloff from the beam axis, squared so the beam has a
       bright core and a long faint skirt rather than a hard edge.
    G  length fade: full at the window, decaying along the beam, because a shaft is
       brightest where the air column is shortest and the scattering is fresh.
    B  fine drifting noise, so a still beam still has internal motion when the
       material panners it.
    """
    grain = fbm(width, height, 16, 3, 0x5348)
    rows = []
    for y in range(height):
        v = y / float(height - 1)
        length = math.exp(-2.1 * v)
        row = bytearray(width * 3)
        for x in range(width):
            u = abs(x / float(width - 1) - 0.5) * 2.0
            cross = _clamp(1.0 - u, 0.0, 1.0)
            cross = cross * cross
            i = x * 3
            row[i] = _b(cross)
            row[i + 1] = _b(length)
            row[i + 2] = _b(grain[y][x])
        rows.append(row)
    return width, height, rows, ("R beam cross-section, G length fade from the window, "
                                 "B tileable grain")


TEXTURE_BUILDERS = [
    ("T_FX_Noise_fBm_512", "T_FX_Noise_fBm_512.png", build_noise,
     "Shared noise for erosion, UV distortion and large-scale break-up."),
    ("T_FX_Smoke_Puff_512", "T_FX_Smoke_Puff_512.png", build_smoke,
     "Smoke puff card for the altar column, the ketores plume and the haze layers."),
    ("T_FX_Flame_Card_512", "T_FX_Flame_Card_512.png", build_flame,
     "Additive flame card for the outer altar fire and the seven lamps."),
    ("T_FX_Ember_64", "T_FX_Ember_64.png", build_ember,
     "Ember and spark point over the outer altar."),
    ("T_FX_DustMote_64", "T_FX_DustMote_64.png", build_mote,
     "Dust mote in the Heikhal light shafts."),
    ("T_FX_LightShaft_256", "T_FX_LightShaft_256.png", build_shaft,
     "Light-shaft beam card for the Heikhal."),
]


# ---------------------------------------------------------------------------
# Derivation of the numbers the material graph and the placement need
# ---------------------------------------------------------------------------

def derive_altar_column() -> dict:
    p = OUTER_ALTAR_PLUME
    top_h = p["maxHeightCm"]
    t_top = plume_time_to_height_s(p, top_h)
    r_base = plume_radius_cm(p, 0.0)
    r_top = plume_radius_cm(p, top_h)
    # The card is a vertical quad from the fire to the top of the drawn column. The
    # panner runs the smoke texture up it once per traverse time, so the apparent
    # rise speed on screen equals the modelled rise speed averaged over the height,
    # rather than an eyeballed scroll rate.
    scroll_v_per_s = 1.0 / t_top
    return {
        "columnHeightCm": round(top_h, 4),
        "baseWidthCm": round(2.0 * r_base, 4),
        "topWidthCm": round(2.0 * r_top, 4),
        "traverseSeconds": round(t_top, 6),
        "panSpeedV": round(scroll_v_per_s, 6),
        "meanRiseSpeedCmS": round(top_h / t_top, 4),
        "riseSpeedAtSourceCmS": round(plume_rise_speed_cms(p, 0.0), 4),
        "riseSpeedAtTopCmS": round(plume_rise_speed_cms(p, top_h), 4),
        "opacityAtBase": round(plume_opacity(p, 0.0), 6),
        "opacityAtTop": round(plume_opacity(p, top_h), 6),
        "puffingHz": round(puffing_frequency_hz(ALTAR_FIRE_DIAMETER_CM), 6),
        "profile": dict(p),
    }


def derive_ketores() -> dict:
    p = KETORES_PLUME
    room = HEIKHAL_ROOM
    impinge = ceiling_impingement_time_s(p, room)
    top_h = p["maxHeightCm"]
    return {
        "columnHeightCm": round(top_h, 4),
        "columnTopZCm": round(room["sourceZCm"] + top_h, 4),
        "ceilingZCm": room["ceilingZCm"],
        "clearanceUnderCeilingCm": round(room["ceilingZCm"] - (room["sourceZCm"] + top_h), 4),
        "baseWidthCm": round(2.0 * plume_radius_cm(p, 0.0), 4),
        "topWidthCm": round(2.0 * plume_radius_cm(p, top_h), 4),
        "impingementSeconds": round(impinge, 6),
        "panSpeedV": round(1.0 / plume_time_to_height_s(p, top_h), 6),
        "spreadRadiusAt30sCm": round(ceiling_spread_radius_cm(room, 30.0), 4),
        "spreadRadiusSaturatedCm": round(ceiling_spread_radius_cm(room, 400.0), 4),
        "layerDepthAt60sCm": round(ceiling_layer_depth_cm(room, 60.0), 4),
        "layerDepthSaturatedCm": round(ceiling_layer_depth_cm(room, 400.0), 4),
        "timing": {"emissionSeconds": 20.0, "accumulateSeconds": 45.0,
                   "dissipateSeconds": 60.0},
        "eventSeconds": round(impinge + 45.0 + 60.0, 4),
        "profile": dict(p),
        "room": dict(room),
    }


def derive_lamps() -> dict:
    f0 = puffing_frequency_hz(LAMP_WICK_DIAMETER_CM)
    local_z = ANCHORS["menorahLidTopLocalZCm"]["value"]
    positions = menorah_lamp_world_positions(local_z)
    light_z = ANCHORS["menorahOrigin"]["value"][2] + ANCHORS["menorahTopLocalZCm"]["value"]
    return {
        "wickDiameterCm": LAMP_WICK_DIAMETER_CM,
        "puffingHz": round(f0, 6),
        "flameHeightCm": 7.0,
        "flameWidthCm": 3.2,
        "flameLocalZCm": local_z,
        "flameLocalZAlternativeCm": ANCHORS["menorahLampBowlLocalZCm"]["value"],
        "positions": positions,
        "lightZCm": round(light_z, 4),
        "lightIntensityCandela": 1.4,
        "lightAttenuationRadiusCm": 260.0,
        "lightTemperatureK": 1850.0,
        "seedPerLamp": [int(hash_u32(0x4C414D50 + k) & 0x7FFFFFFF) for k in range(7)],
    }


def derive_embers() -> dict:
    e = EMBER_PROFILE
    return {
        "profile": dict(e),
        "lifetimeP05S": round(ember_lognormal_quantile_s(e, 0.05), 4),
        "lifetimeMedianS": round(ember_lognormal_quantile_s(e, 0.50), 4),
        "lifetimeP95S": round(ember_lognormal_quantile_s(e, 0.95), 4),
        "spawnRatePerSecond": 24.0,
        "maxAliveAtFullQuality": 96,
    }


def derive_budget() -> dict:
    """Card counts and the RTX 2070 estimate.

    The estimate is arithmetic on overdraw, not a measurement. A 2070 fills roughly
    1e11 shaded translucent pixels per second at this material complexity in the
    ballpark this project has been working in; the number that actually matters is
    the overdraw multiple, and it is kept under 3x screen area for the whole set at
    the intended 1080p/60 target. Anything here is a budget to check against a real
    capture, not a claim about frame time.
    """
    return {
        "targetResolution": [1920, 1080],
        "targetFps": 60,
        "fullDetailCm": 3000.0,
        "cutoffCm": 24000.0,
        "overdrawBudgetScreenAreas": 3.0,
        "rtx2070Estimate": {
            "status": "ARITHMETIC_NOT_A_CAPTURE",
            "translucentMs": "1.0 to 1.8",
            "translucentBasis": "The director holds total translucent overdraw to 3 "
                                "screen areas and lowers EffectsQuality when it does "
                                "not. 3 x 1920 x 1080 is 6.2 Mpixel of translucent "
                                "shading; these materials are two texture fetches and "
                                "about 30 ALU each, which a 2070 covers comfortably "
                                "inside 2 ms.",
            "dynamicLightsMs": "0.2 to 0.4",
            "dynamicLightsBasis": "Eight movable point lights, all shadowless: the "
                                  "altar fire plus one per lamp. The lamp lights reach "
                                  "260 cm, so each covers a small screen footprint. A "
                                  "shadow-casting flickering fire light would cost more "
                                  "than this whole set and is deliberately not used.",
            "realRisk": "Draw calls, not fill. 295 cards is the arithmetic worst case; "
                        "the altar group and the Heikhal group are 30 m apart and the "
                        "per-anchor distance quality means both are never at full "
                        "detail at once, so the practical range is 40 to 90 cards. "
                        "That is CPU-side and is what to watch on a capture.",
            "notMeasured": "Nobody has run this on a 2070. These are budgets to check a "
                           "capture against.",
        },
        "cards": {
            "outerAltarFire": {"min": 6, "max": 18},
            "outerAltarColumn": {"min": 4, "max": 14},
            "outerAltarEmbers": {"min": 0, "max": 96},
            "ketoresPlume": {"min": 4, "max": 16},
            "ketoresCeilingLayer": {"min": 2, "max": 8},
            "menorahFlames": {"min": 7, "max": 7},
            "heikhalShafts": {"min": 3, "max": 6},
            "heikhalMotes": {"min": 0, "max": 120},
            "courtHeatHaze": {"min": 2, "max": 5},
            "altarSmokeHaze": {"min": 2, "max": 6},
        },
    }


def source_claims() -> list:
    return [
        {"id": "FX-SRC-STRAIGHT", "class": "H",
         "claim": "The column of smoke from the arrangement was not dispersed by the wind.",
         "source": "Avos 5:5 (among the miracles of the Mikdash)",
         "depiction": "OuterAltarColumn is authored vertical at every wind speed. "
                      "This is a depiction of a cited claim, not a physical result; "
                      "the physical bent-plume path stays in PlumeMath.h and is "
                      "separately tested."},
        {"id": "FX-SRC-ESH-TAMID", "class": "Torah text",
         "claim": "A perpetual fire shall burn on the altar; it shall not go out.",
         "source": "Vayikra 6:6",
         "depiction": "The outer altar fire is the only continuous effect in the set."},
        {"id": "FX-SRC-KETORES", "class": "H",
         "claim": "A stafflike column rose to the ceiling, and the smoke then spread "
                  "and descended until the chamber was filled.",
         "source": "Yoma 53a:4-5, 11",
         "depiction": "Narrow indoor column (entrainment 0.06), ceiling impingement, "
                      "radial ceiling jet, descending layer. Velocities, depths and "
                      "durations are design values; the sugya gives none."},
        {"id": "FX-SRC-TAMID", "class": "H",
         "claim": "Incense twice daily on the Golden Altar in the Heikhal, tied to "
                  "tending the lamps.",
         "source": "Shemos 30:7-8; Rambam, Temidin uMusafin 3:1",
         "depiction": "The ketores plume is an event with a start and an end, driven "
                      "by AMikdashServiceActor through AMikdashFXDirector, not a "
                      "permanent emitter. Research dossier "
                      "Research/ketores-service-and-smoke.md is explicit that "
                      "'regular service' is not evidence for a continuous emitter."},
        {"id": "FX-SRC-MENORAH", "class": "Torah text",
         "claim": "Beaten olive oil for the light, to kindle a lamp continually.",
         "source": "Shemos 27:20; Vayikra 24:2",
         "depiction": "Wick-scale flames, warm and small, one small light each. Not "
                      "torch scale."},
        {"id": "FX-SRC-NEGATIVE", "class": "R",
         "claim": "The texts give qualitative behaviour and no measured colour, "
                  "opacity, rise velocity, particle size or persistence.",
         "source": "Research/ketores-service-and-smoke.md",
         "depiction": "Every colour, opacity, speed and duration in this manifest is "
                      "labelled a design value and none is presented as measured."},
    ]


def limitations() -> list:
    return [
        "The MenorahV4 model is the Temple Institute display vessel: each lamp bowl "
        "(local Z 142.17..143.94 cm) carries a decorative lid (143.745..146.67) and a "
        "finial (146.67..150). The model has no exposed wick. The flame is therefore "
        "authored at the lid crown, local Z 146.67, so that it reads as a lit lamp; "
        "lampFlameLocalZCm in the spec moves it back to the bowl rim if the menorah "
        "model is ever given open bowls. This is a modelling compromise, recorded, "
        "not a claim about the vessel.",
        "Heat shimmer, the light shafts and the heat haze are camera-facing "
        "translucent cards with a refraction/panner treatment, not a volumetric or a "
        "screen-space distortion pass. They read correctly from the reviewed visitor "
        "viewpoints and will not survive an arbitrary flythrough.",
        "The GPU numbers in this manifest are overdraw arithmetic, not a measured "
        "capture on an RTX 2070.",
        "Nothing here is rabbinic approval, and no part of this depicts the incense "
        "formula, maaleh ashan's botanical identity, or a rule about service.",
    ]


def build_manifest(textures: list) -> dict:
    altar = derive_altar_column()
    ketores = derive_ketores()
    lamps = derive_lamps()
    embers = derive_embers()
    budget = derive_budget()

    fire_x, fire_y = ANCHORS["outerAltarCentre"]["value"]
    fire_z = ANCHORS["outerAltarFireTopZ"]["value"]
    golden = ANCHORS["goldenAltarCentre"]["value"]
    golden_top = ANCHORS["goldenAltarTopZ"]["value"]

    effects = [
        {
            "id": "OuterAltarFire",
            "label": "Outer altar fire",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [fire_x, fire_y, round(fire_z, 4)],
            "material": "MI_FX_Flame_Altar",
            "cards": budget["cards"]["outerAltarFire"],
            "continuous": True,
            "sourceClaims": ["FX-SRC-ESH-TAMID"],
            "notes": "Additive flame cards sitting on the wood arrangement, "
                     f"{ALTAR_FIRE_DIAMETER_CM} cm across, flicker "
                     f"{altar['puffingHz']} Hz.",
        },
        {
            "id": "OuterAltarColumn",
            "label": "Outer altar smoke column",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [fire_x, fire_y, round(fire_z, 4)],
            "material": "MI_FX_Smoke_Column",
            "cards": budget["cards"]["outerAltarColumn"],
            "continuous": True,
            "sourceClaims": ["FX-SRC-STRAIGHT"],
            "columnTopZCm": round(fire_z + altar["columnHeightCm"], 4),
            "notes": "Vertical at every wind speed. Source claim, not physics.",
        },
        {
            "id": "OuterAltarEmbers",
            "label": "Outer altar embers",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [fire_x, fire_y, round(fire_z, 4)],
            "material": "MI_FX_Ember",
            "cards": budget["cards"]["outerAltarEmbers"],
            "continuous": True,
            "sourceClaims": [],
            "notes": "Log-normal burnout, median "
                     f"{embers['lifetimeMedianS']} s, 95th percentile "
                     f"{embers['lifetimeP95S']} s.",
        },
        {
            "id": "OuterAltarLight",
            "label": "Fire light on the surrounding stone",
            "actorClass": "PointLight",
            "location": [fire_x, fire_y, round(fire_z + 60.0, 4)],
            "material": None,
            "cards": {"min": 1, "max": 1},
            "continuous": True,
            "sourceClaims": [],
            "notes": "One movable point light, 2100 K, flickered by the same "
                     "FFlicker stream as the flame cards so light and flame agree.",
        },
        {
            "id": "AltarSmokeHaze",
            "label": "Faint smoke haze near the altar",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [fire_x, fire_y, round(fire_z + 250.0, 4)],
            "material": "MI_FX_Haze_Smoke",
            "cards": budget["cards"]["altarSmokeHaze"],
            "continuous": True,
            "sourceClaims": [],
            "notes": "Low-contrast depth-faded cards, opacity under 0.06.",
        },
        {
            "id": "KetoresPlume",
            "label": "Ketores plume on the golden altar",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [golden[0], golden[1], round(golden_top, 4)],
            "material": "MI_FX_Smoke_Ketores",
            "cards": budget["cards"]["ketoresPlume"],
            "continuous": False,
            "sourceClaims": ["FX-SRC-KETORES", "FX-SRC-TAMID"],
            "columnTopZCm": ketores["columnTopZCm"],
            "notes": "Event, not an emitter. Rises then spreads. "
                     f"Reaches the ceiling in {ketores['impingementSeconds']} s.",
        },
        {
            "id": "KetoresCeilingLayer",
            "label": "Ketores ceiling layer",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [golden[0], golden[1], round(HEIKHAL_ROOM["ceilingZCm"] - 40.0, 4)],
            "material": "MI_FX_Smoke_Ceiling",
            "cards": budget["cards"]["ketoresCeilingLayer"],
            "continuous": False,
            "sourceClaims": ["FX-SRC-KETORES"],
            "notes": "Spreads to "
                     f"{ketores['spreadRadiusSaturatedCm']} cm and descends to "
                     f"{ketores['layerDepthSaturatedCm']} cm. Stops at the ceiling; "
                     "it never leaves the roof.",
        },
        {
            "id": "MenorahFlames",
            "label": "Menorah seven lamps",
            "actorClass": "MikdashFXDirector-owned card group + 7 PointLights",
            "location": lamps["positions"],
            "material": "MI_FX_Flame_Lamp",
            "cards": budget["cards"]["menorahFlames"],
            "continuous": True,
            "sourceClaims": ["FX-SRC-MENORAH"],
            "notes": f"Wick {LAMP_WICK_DIAMETER_CM} cm, flicker "
                     f"{lamps['puffingHz']} Hz, {lamps['flameHeightCm']} cm tall, "
                     f"one {lamps['lightIntensityCandela']} cd light each.",
        },
        {
            "id": "HeikhalShafts",
            "label": "Light shafts in the Heikhal",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [-4400.0, 0.0, 2100.0],
            "material": "MI_FX_LightShaft",
            "cards": budget["cards"]["heikhalShafts"],
            "continuous": True,
            "sourceClaims": [],
            "notes": "Card beams from the Heikhal doorway wall toward the floor. "
                     "Design: the window arrangement is not settled, so the shaft "
                     "anchors are spec data and marked needs_review.",
            "needsReview": "Heikhal window positions are not settled in this build; "
                           "the shaft origins are authored, not derived from a "
                           "window mesh.",
        },
        {
            "id": "HeikhalMotes",
            "label": "Dust motes in the shafts",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [-4400.0, 0.0, 1700.0],
            "material": "MI_FX_DustMote",
            "cards": budget["cards"]["heikhalMotes"],
            "continuous": True,
            "sourceClaims": [],
            "notes": "Motes drift only inside the shaft volumes; outside them they "
                     "are invisible, which is what makes a shaft read as light.",
        },
        {
            "id": "CourtHeatHaze",
            "label": "Heat shimmer over the fire and haze over the courts at midday",
            "actorClass": "MikdashFXDirector-owned card group",
            "location": [[0.0, 0.0, 1420.0], [900.0, 0.0, 1030.0], [-600.0, 700.0, 1030.0],
                         [-600.0, -700.0, 1030.0], [1800.0, 0.0, 1060.0]],
            "material": "MI_FX_HeatHaze",
            "cards": budget["cards"]["courtHeatHaze"],
            "continuous": True,
            "sourceClaims": [],
            "notes": "Refraction-only cards. The first sits directly over the fire and "
                     "is the altar's own heat shimmer; it is always on, because a fire "
                     "is hot at any hour. The rest are the court haze and are scaled by "
                     "HeatHazeStrength, which the time-of-day system drives through "
                     "AMikdashFXDirector::SetHeatHazeStrength so this actor never reads "
                     "the clock itself.",
        },
    ]

    # The master materials declare exactly the parameters Scripts/release_fx.py's
    # graph builders create, at exactly the defaults those builders set. That is not
    # decoration: release_fx.py cross-checks every instance override against these
    # lists offline, and then again against the real material by readback, so a
    # parameter that exists here and not in the graph, or the other way round, is
    # caught before anything reaches the map. Several values repeat across materials
    # because SHARED graph helpers set them - VFlip, FXSeed, PanSpeedU/V, NoiseTiling,
    # ErosionBias, ErosionSoftness, FXFade. The per-effect tuning lives in the
    # instances, which are what the effects actually use.
    dyn = {"FXFade": 1.0, "FXErosion": 0.0, "FXSeed": 0.0, "FXAge": 0.0,
           "FXFlicker": 0.0, "VFlip": 0.0}
    scroll = {"PanSpeedU": 0.03, "PanSpeedV": 0.35, "NoiseTiling": 2.0}
    erode = {"ErosionBias": 0.40, "ErosionSoftness": 0.20}

    flame_scalars = dict(dyn)
    flame_scalars.update(scroll)
    flame_scalars.update(erode)
    flame_scalars.update({"FlickerDepth": 0.28, "CoreBoost": 3.2, "EmissiveScale": 24.0})

    smoke_scalars = dict(dyn)
    smoke_scalars.update(scroll)
    smoke_scalars.update(erode)
    smoke_scalars.update({"DistortStrength": 0.055, "OpacityScale": 0.55,
                          "OpacityFloor": 0.05, "DepthFadeDistance": 90.0})

    point_scalars = dict(dyn)
    point_scalars.update({"Hardness": 0.5, "EmissiveScale": 18.0})

    shaft_scalars = dict(dyn)
    shaft_scalars.update(scroll)
    shaft_scalars.update({"GrainStrength": 0.25, "EmissiveScale": 1.1,
                          "ViewFalloffPower": 2.5})

    haze_scalars = dict(dyn)
    haze_scalars.update(scroll)
    haze_scalars.update({"RefractionStrength": 1.012, "OpacityScale": 0.02})

    materials = [
        {
            "name": "M_FX_Flame",
            "package": "/Game/MikdashV3/FX/Materials",
            "domain": "Surface",
            "blendMode": "Additive",
            "shadingModel": "Unlit",
            "twoSided": True,
            "textures": {"FlameTex": "T_FX_Flame_Card_512", "NoiseTex": "T_FX_Noise_fBm_512"},
            "scalars": flame_scalars,
            "vectors": {
                "CoreColour": [1.0, 0.86, 0.56, 1.0],
                "EdgeColour": [1.0, 0.33, 0.06, 1.0],
            },
            "instances": [
                {"name": "MI_FX_Flame_Altar",
                 "scalars": {"EmissiveScale": 24.0, "PanSpeedV": 0.55, "NoiseTiling": 2.0,
                             "FlickerDepth": 0.28, "ErosionBias": 0.42,
                             "ErosionSoftness": 0.18},
                 "note": "The 3.25 m wood arrangement. The %.4f Hz puffing rate is "
                         "applied by the director, not by the material."
                         % altar["puffingHz"]},
                {"name": "MI_FX_Flame_Lamp",
                 "scalars": {"EmissiveScale": 9.0, "PanSpeedV": 1.9, "NoiseTiling": 6.0,
                             "FlickerDepth": 0.34, "ErosionBias": 0.30,
                             "ErosionSoftness": 0.16},
                 "vectors": {"CoreColour": [1.0, 0.90, 0.66, 1.0],
                             "EdgeColour": [1.0, 0.52, 0.16, 1.0]},
                 "note": "Wick scale: smaller, warmer, and flickering at %.3f Hz "
                         "against the altar's %.4f."
                         % (lamps["puffingHz"], altar["puffingHz"])},
            ],
        },
        {
            "name": "M_FX_Smoke",
            "package": "/Game/MikdashV3/FX/Materials",
            "domain": "Surface",
            "blendMode": "Translucent",
            "shadingModel": "Unlit",
            "twoSided": True,
            "textures": {"SmokeTex": "T_FX_Smoke_Puff_512", "NoiseTex": "T_FX_Noise_fBm_512"},
            "scalars": smoke_scalars,
            "scalarsNote": "DepthFadeDistance exists only if MaterialExpressionDepthFade "
                           "wired successfully. release_fx.py records which happened and "
                           "no instance overrides it.",
            "vectors": {
                "SmokeColour": [0.36, 0.34, 0.32, 1.0],
                "LitColour": [0.92, 0.62, 0.36, 1.0],
            },
            "instances": [
                {"name": "MI_FX_Smoke_Column",
                 "scalars": {"PanSpeedV": altar["panSpeedV"], "OpacityScale": 0.55,
                             "OpacityFloor": OUTER_ALTAR_PLUME["minOpacity"],
                             "NoiseTiling": 1.5, "DistortStrength": 0.055,
                             "ErosionBias": 0.50, "ErosionSoftness": 0.22},
                 "note": "PanSpeedV is 1 / %.3f s, the modelled time for a parcel to "
                         "cross the whole %.0f cm column, so the texture climbs at the "
                         "speed the plume model says it climbs rather than at a rate "
                         "someone liked the look of."
                         % (altar["traverseSeconds"], altar["columnHeightCm"])},
                {"name": "MI_FX_Smoke_Ketores",
                 "scalars": {"PanSpeedV": ketores["panSpeedV"], "OpacityScale": 0.42,
                             "NoiseTiling": 3.5, "DistortStrength": 0.028,
                             "OpacityFloor": KETORES_PLUME["minOpacity"],
                             "ErosionBias": 0.46, "ErosionSoftness": 0.20},
                 "vectors": {"SmokeColour": [0.78, 0.76, 0.72, 1.0],
                             "LitColour": [0.98, 0.92, 0.80, 1.0]},
                 "note": "Paler and finer than wood smoke, and narrow: Yoma 53a calls "
                         "the column stafflike."},
                {"name": "MI_FX_Smoke_Ceiling",
                 "scalars": {"PanSpeedV": 0.02, "PanSpeedU": 0.012, "OpacityScale": 0.30,
                             "NoiseTiling": 1.0, "OpacityFloor": 0.06,
                             "ErosionBias": 0.45, "ErosionSoftness": 0.30},
                 "vectors": {"SmokeColour": [0.80, 0.78, 0.74, 1.0]},
                 "note": "The layer under the roof: slow, wide, and never billboarded, "
                         "because a slab of smoke under a ceiling is a slab."},
                {"name": "MI_FX_Haze_Smoke",
                 "scalars": {"PanSpeedV": 0.012, "OpacityScale": 0.055, "NoiseTiling": 0.6,
                             "OpacityFloor": 0.01, "ErosionBias": 0.20,
                             "ErosionSoftness": 0.35},
                 "note": "Faint smoke haze near the altar, under 6% opacity on purpose."},
            ],
        },
        {
            "name": "M_FX_Point",
            "package": "/Game/MikdashV3/FX/Materials",
            "domain": "Surface",
            "blendMode": "Additive",
            "shadingModel": "Unlit",
            "twoSided": True,
            "textures": {"PointTex": "T_FX_Ember_64"},
            "scalars": point_scalars,
            "scalarsNote": "No PanSpeed and no NoiseTiling: a point sprite has no UV "
                           "motion of its own, so this material builds no scroll offset.",
            "vectors": {"Colour": [1.0, 0.46, 0.12, 1.0]},
            "instances": [
                {"name": "MI_FX_Ember",
                 "scalars": {"Hardness": 0.55, "EmissiveScale": 18.0},
                 "vectors": {"Colour": [1.0, 0.46, 0.12, 1.0]},
                 "note": "Log-normal burnout, median %.2f s, 95th percentile %.2f s."
                         % (embers["lifetimeMedianS"], embers["lifetimeP95S"])},
                {"name": "MI_FX_DustMote",
                 "textures": {"PointTex": "T_FX_DustMote_64"},
                 "scalars": {"Hardness": 0.15, "EmissiveScale": 1.6},
                 "vectors": {"Colour": [1.0, 0.94, 0.82, 1.0]},
                 "note": "Soft and dim. A mote is an out-of-focus speck, and a hard "
                         "sprite at this size aliases into sparkle."},
            ],
        },
        {
            "name": "M_FX_Shaft",
            "package": "/Game/MikdashV3/FX/Materials",
            "domain": "Surface",
            "blendMode": "Additive",
            "shadingModel": "Unlit",
            "twoSided": True,
            "textures": {"ShaftTex": "T_FX_LightShaft_256", "NoiseTex": "T_FX_Noise_fBm_512"},
            "scalars": shaft_scalars,
            "vectors": {"Colour": [1.0, 0.93, 0.78, 1.0]},
            "instances": [
                {"name": "MI_FX_LightShaft",
                 "scalars": {"EmissiveScale": 1.1, "GrainStrength": 0.25,
                             "ViewFalloffPower": 2.5, "PanSpeedV": 0.02,
                             "NoiseTiling": 0.8},
                 "note": "Brightness falls as |dot(view, card normal)| raised to "
                         "ViewFalloffPower, so the beam vanishes when you look along "
                         "it instead of becoming a visible sheet."},
            ],
        },
        {
            "name": "M_FX_HeatHaze",
            "package": "/Game/MikdashV3/FX/Materials",
            "domain": "Surface",
            "blendMode": "Translucent",
            "shadingModel": "Unlit",
            "twoSided": True,
            "refraction": True,
            "textures": {"NoiseTex": "T_FX_Noise_fBm_512"},
            "scalars": haze_scalars,
            "vectors": {},
            "instances": [
                {"name": "MI_FX_HeatHaze",
                 "scalars": {"RefractionStrength": 1.012, "OpacityScale": 0.02,
                             "NoiseTiling": 3.0, "PanSpeedV": 0.09},
                 "note": "Refraction only, essentially no opacity: shimmer, not fog."},
            ],
        },
    ]

    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "fx_material_manifest_generated",
        "generatedBy": "Scripts/create_fx_materials.py",
        "generatorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "mathHeader": "Plugins/MikdashRuntime/Source/MikdashRuntime/Public/PlumeMath.h",
        "mathTest": "Plugins/MikdashRuntime/Tests/PlumeMathTest.cpp",
        "honesty": "Colour, opacity, rise velocity, particle size and duration are "
                   "artistic choices. The straight smoke column is a depiction of a "
                   "cited claim (Avos 5:5), not a physical result. Nothing here is "
                   "rabbinic approval.",
        "sourceClaims": source_claims(),
        "anchors": ANCHORS,
        "textures": textures,
        "materials": materials,
        "derived": {
            "outerAltarColumn": altar,
            "ketores": ketores,
            "lamps": lamps,
            "embers": embers,
            "budget": budget,
        },
        "effects": effects,
        "limitations": limitations(),
    }


# ---------------------------------------------------------------------------
# self check
# ---------------------------------------------------------------------------

def self_check() -> list:
    """Reproduce numbers the C++ standalone test prints. A drift between this Python
    mirror and PlumeMath.h shows up here, not in the editor."""
    problems = []

    def near(name, got, want, tol):
        if not math.isfinite(got) or abs(got - want) > tol:
            problems.append(f"{name}: got {got!r}, expected {want} +/- {tol}")

    # PlumeMathTest.cpp: "column reaches the 2925 cm ceiling from the 1004.17 cm
    # altar top in 43.7999 s"
    near("ketores impingement", ceiling_impingement_time_s(KETORES_PLUME, HEIKHAL_ROOM),
         43.7999, 0.001)
    # "column top Z 2924.17 <= ceiling Z 2925"
    near("ketores column top Z",
         HEIKHAL_ROOM["sourceZCm"] + KETORES_PLUME["maxHeightCm"], 2924.1667, 0.001)
    # "altar 325 cm -> 0.83205 Hz, lamp 0.6 cm -> 19.3649 Hz"
    near("altar puffing", puffing_frequency_hz(ALTAR_FIRE_DIAMETER_CM), 0.83205, 1e-4)
    near("lamp puffing", puffing_frequency_hz(LAMP_WICK_DIAMETER_CM), 19.3649, 1e-3)
    # "opacity falls monotonically from 1 to 0.147929" for the altar profile at 4000 cm
    near("altar opacity at 4000 cm", plume_opacity(OUTER_ALTAR_PLUME, 4000.0),
         0.147929, 1e-5)
    # "spread saturates at 1050 / 1050 cm and the layer at 949.036 / 950 cm"
    near("ceiling spread at 200 s", ceiling_spread_radius_cm(HEIKHAL_ROOM, 200.0),
         1050.0, 1e-3)
    near("layer depth at 200 s", ceiling_layer_depth_cm(HEIKHAL_ROOM, 200.0),
         949.036, 0.01)
    # HashUint32 must be the header's, or the noise would differ between the offline
    # bake and any runtime that regenerates it.
    if hash_u32(0) != 0:
        problems.append(f"hash_u32(0) = {hash_u32(0)}, expected 0")
    if not 0.0 <= hash_unit(1, 2, 3) < 1.0:
        problems.append("hash_unit out of [0,1)")

    # The plume must never leave the drawn envelope: radius is capped, height is
    # capped, and the round trip h(t(h)) is the identity below the cap.
    for h in (0.0, 100.0, 1000.0, 4200.0):
        r = plume_radius_cm(OUTER_ALTAR_PLUME, h)
        if r > OUTER_ALTAR_PLUME["maxRadiusCm"] + 1e-9:
            problems.append(f"radius {r} exceeds cap at h={h}")
    for t in (0.5, 5.0, 20.0):
        h = plume_height_at_age_cm(OUTER_ALTAR_PLUME, t)
        if h < OUTER_ALTAR_PLUME["maxHeightCm"] - 1.0:
            back = plume_time_to_height_s(OUTER_ALTAR_PLUME, h)
            if abs(back - t) > 1e-6:
                problems.append(f"round trip t={t} -> h={h} -> {back}")

    # The lamps must sit on the menorah axis and inside its footprint.
    for k, p in enumerate(menorah_lamp_world_positions(146.67)):
        if abs(p[0] - (-5330.0)) > 1e-6:
            problems.append(f"lamp {k} X {p[0]} is off the menorah axis")
        if not 268.0 <= p[1] <= 362.0:
            problems.append(f"lamp {k} Y {p[1]} is outside the branch span")
    return problems


# ---------------------------------------------------------------------------

def do_export() -> int:
    problems = self_check()
    if problems:
        print("SELF CHECK FAILED before export:")
        for p in problems:
            print("  " + p)
        return 2

    TEXTURES.mkdir(parents=True, exist_ok=True)
    textures = []
    for name, filename, builder, purpose in TEXTURE_BUILDERS:
        w, h, rows, channels = builder()
        digest = write_png_rgb(TEXTURES / filename, w, h, rows)
        textures.append({
            "name": name,
            "file": f"SourceAssets/fx-review/textures/{filename}",
            "width": w, "height": h,
            "format": "PNG RGB8",
            "channels": channels,
            "purpose": purpose,
            "sha256": digest,
            "sizeBytes": (TEXTURES / filename).stat().st_size,
            # These are data masks, not photographs. sRGB on a mask is a gamma curve
            # applied to a number that is not a colour, and it is the single most
            # common cause of an effect that looks right offline and wrong in engine.
            "srgb": False,
            "compressionSettings": "TC_Masks",
            "mipGenSettings": "TMGS_SimpleAverage",
            # Only the noise wraps. It is the one texture sampled with a scrolling,
            # tiled UV, and it was built on a lattice whose period divides its width
            # so that it does. Everything else is a shape sampled once over 0..1: a
            # wrapping flame or beam profile would smear its far edge back over its
            # near one the moment a distortion pushed a UV past the border.
            "addressX": "TA_Wrap" if name == "T_FX_Noise_fBm_512" else "TA_Clamp",
            "addressY": "TA_Wrap" if name == "T_FX_Noise_fBm_512" else "TA_Clamp",
            "destination": "/Game/MikdashV3/FX/Textures",
        })
        print(f"  wrote {filename}  {w}x{h}  {digest[:16]}")

    manifest = build_manifest(textures)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  wrote {MANIFEST.relative_to(ROOT)}")
    print(f"self check: {len(problems)} problems")
    return 0


def do_verify() -> int:
    failures = []
    if not MANIFEST.exists():
        print("FAIL manifest missing; run --export")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        failures.append(f"schemaVersion {manifest.get('schemaVersion')} != {SCHEMA_VERSION}")

    for entry in manifest.get("textures", []):
        path = ROOT / entry["file"]
        if not path.exists():
            failures.append(f"{entry['name']}: file missing")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            failures.append(f"{entry['name']}: sha256 drifted")
            continue
        try:
            w, h, rows = read_png_rgb(path)
        except Exception as exc:                                 # noqa: BLE001
            failures.append(f"{entry['name']}: unreadable ({exc})")
            continue
        if (w, h) != (entry["width"], entry["height"]):
            failures.append(f"{entry['name']}: {w}x{h} != manifest")
            continue
        # A channel that is entirely flat means a builder silently produced nothing.
        for ch, label in ((0, "R"), (1, "G"), (2, "B")):
            lo, hi = 255, 0
            for y in range(0, h, max(1, h // 32)):
                row = rows[y]
                for x in range(0, w, max(1, w // 32)):
                    v = row[x * 3 + ch]
                    lo = min(lo, v)
                    hi = max(hi, v)
            if hi - lo < 8:
                failures.append(f"{entry['name']}.{label} is flat ({lo}..{hi})")
        print(f"  PASS {entry['name']}  {w}x{h}  {entry['sizeBytes']} bytes")

    problems = self_check()
    for p in problems:
        failures.append("math mirror: " + p)
    if not problems:
        print("  PASS plume math mirror agrees with PlumeMathTest.cpp values")

    # The derived numbers in the manifest must still fall out of the math.
    fresh = build_manifest(manifest["textures"])
    if fresh["derived"] != manifest["derived"]:
        failures.append("derived numbers no longer reproduce from the profiles")
    else:
        print("  PASS derived numbers reproduce")

    if failures:
        print()
        for f in failures:
            print("FAIL " + f)
        print(f"\n{len(failures)} failures")
        return 1
    print("\nverify: green")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true", help="write textures + manifest")
    parser.add_argument("--verify", action="store_true", help="re-read and re-check")
    args = parser.parse_args()
    if not args.export and not args.verify:
        parser.print_help()
        return 0
    rc = 0
    if args.export:
        rc = do_export()
        if rc:
            return rc
    if args.verify:
        rc = do_verify()
    return rc


if __name__ == "__main__":
    sys.exit(main())
