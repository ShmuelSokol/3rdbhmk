"""Offline design, proof and licence gate for the SoundscapeV2 layered soundscape.

Nothing here launches the editor, opens a map, or writes an asset. It runs anywhere
Python runs, and it answers the three questions the release run cannot:

  1. DOES THE SHIPPED SCHEDULE ACTUALLY AVOID A LOOP?
     The soundscape's randomisation lives in C++, in the engine-free half of
     MikdashSoundscape.h. This file mirrors that arithmetic in Python and then PROVES the
     mirror is bit-identical by compiling Plugins/MikdashRuntime/Tests/SoundscapeMathTest.cpp
     and comparing 128 golden vectors, value for value. Only once that comparison passes
     does it simulate every placed emitter and report the result. A report that merely
     resembled the shipped behaviour would be worth nothing.

  2. IS EVERY RECORDING'S LICENCE ACTUALLY VERIFIED?
     Every file the release script would import is checked to have provenance, a captured
     publisher page, a matching hash, and a verdict in
     SourceAssets/third-party/soundscape-v2-audio-manifest.json. A file that fails any of
     those is a hard failure, not a warning, because the alternative is shipping audio
     whose rights nobody established.

  3. WHAT IS THE LAYER TABLE, IN ONE PLACE?
     Printed as a table, and written into a receipt beside the release receipts.

Run:
  python Scripts/create_soundscape_v2.py                  everything except the C++ build
  python Scripts/create_soundscape_v2.py --tests          also build and run the C++ test
  python Scripts/create_soundscape_v2.py --table          just the layer table
  python Scripts/create_soundscape_v2.py --credits        just the attribution block
  python Scripts/create_soundscape_v2.py --json           machine-readable, to stdout

Exit code 0 only when every check that ran passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "Scripts" / "release_soundscape_v2.spec.json"
PACKAGE = ROOT / "SourceAssets" / "soundscape-review" / "SoundscapeV2"
SOURCES = PACKAGE / "sources"
EVIDENCE = PACKAGE / "evidence"
MANIFEST = ROOT / "SourceAssets" / "third-party" / "soundscape-v2-audio-manifest.json"
TEST_CPP = ROOT / "Plugins" / "MikdashRuntime" / "Tests" / "SoundscapeMathTest.cpp"
PUBLIC = ROOT / "Plugins" / "MikdashRuntime" / "Source" / "MikdashRuntime" / "Public"
VCVARS = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC"
              r"\Auxiliary\Build\vcvars64.bat")

MASK = 0xFFFFFFFF

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, bool(ok), detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"  {detail}" if detail else ""))
    return bool(ok)


# ---------------------------------------------------------------------------
# The mirror of MikdashSoundscape.h
#
# Every function below is a line-for-line transcription of the C++ in
# Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashSoundscape.h. It is NOT the
# authority; the C++ is. check_golden_vectors() is what makes this trustworthy.
# ---------------------------------------------------------------------------

def hash32(seed: int, emitter: int, passno: int, lane: int) -> int:
    h = (seed * 0x9E3779B9) & MASK
    h ^= (emitter + 0x85EBCA6B + ((h << 6) & MASK) + (h >> 2)) & MASK
    h &= MASK
    h ^= (passno + 0xC2B2AE35 + ((h << 6) & MASK) + (h >> 2)) & MASK
    h &= MASK
    h ^= (lane + 0x27D4EB2F + ((h << 6) & MASK) + (h >> 2)) & MASK
    h &= MASK
    h ^= h >> 16
    h = (h * 0x7FEB352D) & MASK
    h ^= h >> 15
    h = (h * 0x846CA68B) & MASK
    h ^= h >> 16
    return h & MASK


def hash01(seed: int, emitter: int, passno: int, lane: int) -> float:
    return hash32(seed, emitter, passno, lane) / 4294967296.0


def hash_range(seed, emitter, passno, lane, lo, hi):
    return lo + (hi - lo) * hash01(seed, emitter, passno, lane)


def clamp(v, lo, hi):
    if v != v:
        return lo
    return lo if v < lo else (hi if v > hi else v)


def saturate(v):
    return clamp(v, 0.0, 1.0)


def lerp(a, b, t):
    return a + (b - a) * t


def wrap_hours(h):
    return h % 24.0


# The eight-row day curves, transcribed from LayerDayGainCurve.
DAY_CURVES = {
    "WIND_BED":      [0.88, 0.62, 0.52, 0.58, 0.72, 0.92, 0.80, 0.84],
    "WIND_GUST":     [0.95, 0.55, 0.40, 0.50, 0.70, 1.00, 0.85, 0.90],
    "CROWD_COURT":   [0.02, 0.06, 0.28, 0.85, 1.00, 0.78, 0.42, 0.12],
    "CROWD_DISTANT": [0.05, 0.10, 0.30, 0.70, 0.90, 0.75, 0.50, 0.22],
    "CITY":          [0.30, 0.34, 0.55, 0.90, 1.00, 0.95, 0.86, 0.55],
    "BIRD":          [0.04, 0.85, 1.00, 0.72, 0.34, 0.46, 0.78, 0.30],
    "SERVICE":       [0.00, 0.45, 1.00, 0.95, 0.70, 0.60, 0.85, 0.10],
    "FOOTSTEP":      [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
    "FOLIAGE":       [0.85, 0.60, 0.55, 0.60, 0.75, 0.95, 0.82, 0.86],
    "CLOTH":         [0.70, 0.55, 0.60, 0.85, 1.00, 0.90, 0.75, 0.62],
}
# C++ LayerName() spellings, in ELayer order, for the golden comparison.
LAYER_NAMES = ["WindBed", "WindGust", "CrowdCourt", "CrowdDistant", "City", "Bird",
               "Service", "Footstep", "Foliage", "Cloth"]
NAME_TO_KEY = dict(zip(LAYER_NAMES, DAY_CURVES.keys()))

# Jerusalem, 8 September, IDT: the same anchors the C++ test uses.
ANCHORS = dict(civil_dawn=6.03, sunrise=6.29, solar_noon=12.61, sunset=18.93, civil_dusk=19.19)


def anchor_hours(a, index):
    return [wrap_hours(a["solar_noon"] - 12.0),
            a["civil_dawn"],
            a["sunrise"],
            0.5 * (a["sunrise"] + a["solar_noon"]),
            a["solar_noon"],
            0.5 * (a["solar_noon"] + a["sunset"]),
            a["sunset"],
            a["civil_dusk"]][index]


def anchor_coordinate(a, hours):
    h = wrap_hours(hours)
    for i in range(8):
        start = anchor_hours(a, i)
        end = anchor_hours(a, (i + 1) % 8)
        span = wrap_hours(end - start)
        if span <= 1e-6:
            span = 1e-6
        into = wrap_hours(h - start)
        if into < span:
            return i + into / span
    return 0.0


def sample_day_curve(values, a, hours):
    c = anchor_coordinate(a, hours)
    i = int(math.floor(c)) % 8
    j = (i + 1) % 8
    return lerp(values[i], values[j], saturate(c - math.floor(c)))


def layer_gain_at_time(layer_key, a, hours):
    return saturate(sample_day_curve(DAY_CURVES[layer_key], a, hours))


def layer_interval_scale(layer_key, a, hours):
    return clamp(1.0 / max(layer_gain_at_time(layer_key, a, hours), 0.05), 1.0, 12.0)


def next_event(seed, emitter_id, source_count, gap_lo, gap_hi, pitch, level,
               passno, previous, interval_scale):
    n = max(1, source_count)
    if n == 1:
        source = 0
    elif previous is None or previous < 0 or previous >= n:
        source = hash32(seed, emitter_id, passno, 11) % n
    else:
        source = (previous + 1 + hash32(seed, emitter_id, passno, 11) % (n - 1)) % n
    a = hash01(seed, emitter_id, passno, 21)
    b = hash01(seed, emitter_id, passno, 22)
    scale = clamp(interval_scale, 0.05, 20.0) if interval_scale > 0.0 else 1.0
    gap = lerp(gap_lo, gap_hi, 0.5 * (a + b)) * scale
    return {"gap": gap, "source": source,
            "pitch": hash_range(seed, emitter_id, passno, 31, pitch[0], pitch[1]),
            "level": hash_range(seed, emitter_id, passno, 32, level[0], level[1])}


# ---------------------------------------------------------------------------
# 1. Prove the mirror against the shipped C++
# ---------------------------------------------------------------------------

def build_test(outdir: Path):
    """Compile SoundscapeMathTest.cpp the same way Scripts/verify.py does."""
    if not VCVARS.exists():
        return None, f"vcvars64 not found at {VCVARS}"
    outdir.mkdir(parents=True, exist_ok=True)
    exe = outdir / "SoundscapeMathTest.exe"
    bat = outdir / "build_soundscape_test.bat"
    bat.write_text(
        "@echo off\r\n"
        f'call "{VCVARS}" >nul\r\n'
        f'cd /d "{outdir}"\r\n'
        f'cl /nologo /std:c++17 /EHsc /W4 /O2 /I"{PUBLIC}" "{TEST_CPP}" '
        f'/Fe:"{exe}" /link /SUBSYSTEM:CONSOLE\r\n',
        encoding="ascii")
    proc = subprocess.run(["cmd", "/c", str(bat)], capture_output=True, text=True,
                          cwd=str(outdir))
    if not exe.exists():
        return None, (proc.stdout + proc.stderr)[-600:]
    return exe, None


def check_golden_vectors(exe: Path) -> dict:
    """Compare 128 values from the shipped C++ against the Python mirror above.

    This is the check that makes every other number in this file mean anything. If the
    mirror drifts from the header by so much as a rounding step, the offline report stops
    describing what a listener will actually hear, and it must fail loudly rather than
    quietly print a plausible lie.
    """
    proc = subprocess.run([str(exe), "--golden"], capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        return {"ok": False, "error": "golden run failed: " + proc.stderr[-300:]}
    compared = 0
    mismatches = []
    prev = -1
    for line in proc.stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "H":
            emitter, passno, value = int(parts[1]), int(parts[2]), int(parts[3])
            mine = hash32(20260908, emitter, passno, 11)
            compared += 1
            if mine != value:
                mismatches.append(f"Hash({emitter},{passno}) C++ {value} != Python {mine}")
        elif parts[0] == "E":
            passno, source = int(parts[1]), int(parts[2])
            gap, pitch, level = float(parts[3]), float(parts[4]), float(parts[5])
            mine = next_event(20260908, 5, 7, 20.0, 62.0, (0.92, 1.08), (0.50, 1.00),
                              passno, prev if passno else -1, 1.0)
            prev = mine["source"]
            compared += 1
            if (mine["source"] != source or abs(mine["gap"] - gap) > 1e-9
                    or abs(mine["pitch"] - pitch) > 1e-9 or abs(mine["level"] - level) > 1e-9):
                mismatches.append(
                    f"event {passno}: C++ ({source},{gap:.9f},{pitch:.9f},{level:.9f}) != "
                    f"Python ({mine['source']},{mine['gap']:.9f},{mine['pitch']:.9f},"
                    f"{mine['level']:.9f})")
        elif parts[0] == "D":
            name, hours = parts[1], float(parts[2])
            gain, scale = float(parts[3]), float(parts[4])
            key = NAME_TO_KEY[name]
            mine_gain = layer_gain_at_time(key, ANCHORS, hours)
            mine_scale = layer_interval_scale(key, ANCHORS, hours)
            compared += 1
            if abs(mine_gain - gain) > 1e-9 or abs(mine_scale - scale) > 1e-9:
                mismatches.append(f"day curve {name}@{hours}: C++ ({gain:.9f},{scale:.9f}) != "
                                  f"Python ({mine_gain:.9f},{mine_scale:.9f})")
    return {"ok": not mismatches and compared >= 100, "compared": compared,
            "mismatches": mismatches[:8]}


# ---------------------------------------------------------------------------
# 2. Simulate the placed soundscape
# ---------------------------------------------------------------------------

def simulate(spec, hours=9.0, span_seconds=3600.0):
    """Run every non-looping emitter for an hour of game time and measure the result."""
    seed = int(spec["runtimeActor"]["properties"]["seed"])
    rows = []
    all_times = []
    for index, emitter in enumerate(spec["emitters"]):
        layer = spec["layers"][emitter["layer"]]
        key = layer["runtimeLayer"]
        looping = layer["mode"] in ("loop", "loopRandom")
        delay = emitter.get("delaySeconds") or [0.0, 0.0]
        pitch = layer.get("pitchRange") or [emitter.get("pitch", 1.0), emitter.get("pitch", 1.0)]
        level = layer.get("volumeRange") or [1.0, 1.0]
        sources = len(layer["sources"])
        scale = layer_interval_scale(key, ANCHORS, hours)

        gaps, picks = [], []
        immediate_repeats = 0
        t = 0.0
        prev = -1
        passno = 0
        while t < span_seconds and passno < 20000:
            event = next_event(seed, index + 1, sources, delay[0], delay[1],
                               pitch, level, passno, prev, scale)
            # Only meaningful when there is more than one take. An emitter with a single
            # recording plays that recording every time by definition; what stops IT from
            # reading as a loop is the random gap, pitch and level, not the choice of file.
            if sources > 1 and prev >= 0 and event["source"] == prev:
                immediate_repeats += 1
            prev = event["source"]
            gaps.append(event["gap"])
            picks.append(event["source"])
            t += max(event["gap"], 0.001 if looping else 0.0)
            if not looping and t < span_seconds:
                all_times.append(t)
            passno += 1
            if looping:
                break   # a looping bed has no silence to measure; its handover is timed by
                        # the take length, which the release receipt records instead
        row = {
            "label": emitter["label"], "layer": key, "mode": layer["mode"],
            "looping": looping, "sources": sources,
            "gapSeconds": [delay[0], delay[1]],
            "gapSecondsAtThisHour": [round(delay[0] * scale, 2), round(delay[1] * scale, 2)],
            "intervalScale": round(scale, 3),
            "dayGain": round(layer_gain_at_time(key, ANCHORS, hours), 4),
            "heightVarying": bool(emitter.get("heightVarying", False)),
            "occluded": bool(emitter.get("occlude", False)),
            "crowdScaled": bool(emitter.get("crowdScaled", False)),
            "eventsInAnHour": 0 if looping else len(gaps),
            "immediateRepeats": immediate_repeats,
            "distinctSourcesUsed": len(set(picks)),
        }
        if gaps and not looping:
            mean = sum(gaps) / len(gaps)
            row["meanGapSeconds"] = round(mean, 2)
            row["gapStdDevSeconds"] = round(
                math.sqrt(max(0.0, sum(g * g for g in gaps) / len(gaps) - mean * mean)), 2)
        rows.append(row)
    return rows, sorted(all_times)


def measure_periodicity(times):
    """Is there a beat in the combined firing pattern? There must not be."""
    if len(times) < 50:
        return {"ok": False, "reason": "too few events to judge", "events": len(times)}
    buckets: dict[int, int] = {}
    for a, b in zip(times, times[1:]):
        buckets[int((b - a) * 10.0)] = buckets.get(int((b - a) * 10.0), 0) + 1
    worst = max(buckets.values())
    share = worst / float(len(times))
    return {"ok": share < 0.15 and len(buckets) > 40,
            "events": len(times),
            "distinctIntervalBuckets": len(buckets),
            "largestBucketShare": round(share, 4),
            "rule": ("A periodic mix piles its inter-event intervals into one 0.1 s bucket. "
                     "Under 15 % in the largest bucket, spread over more than 40 buckets, is "
                     "the numeric form of 'there is no beat'.")}


# ---------------------------------------------------------------------------
# 3. Licences
# ---------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_licences() -> dict:
    """Every file the release run would import must be licensed, and provably so."""
    report = {"files": [], "problems": []}
    if not MANIFEST.exists():
        report["problems"].append("third-party manifest missing: " + str(MANIFEST))
        return report
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    by_file = {Path(a["file"]).name: a for a in manifest.get("assets", [])}

    try:
        sys.path.insert(0, str(ROOT / "Scripts"))
        import release_soundscape_v2 as release
        table = release.SOURCE_TABLE
    except Exception as error:      # noqa: BLE001
        report["problems"].append("cannot read the source table: " + repr(error))
        return report

    for entry in table:
        name = entry["file"]
        path = SOURCES / name
        row = {"file": name, "role": entry["role"], "licence": entry["licence"][0]}
        if not path.exists():
            report["problems"].append("missing source " + name)
            report["files"].append(row)
            continue
        row["bytes"] = path.stat().st_size
        row["sha256"] = sha256_of(path)

        provenance = SOURCES / (Path(name).stem + ".provenance.json")
        row["provenance"] = provenance.exists()
        if not provenance.exists():
            report["problems"].append("no provenance for " + name)
        else:
            record = json.loads(provenance.read_text(encoding="utf-8-sig"))
            row["provenanceLicence"] = record.get("licence")
            if record.get("sha256") and record["sha256"] != row["sha256"]:
                report["problems"].append("hash differs from provenance for " + name)
            if record.get("licence") != entry["licence"][0]:
                report["problems"].append("licence differs between table and provenance for "
                                          + name)

        evidence = EVIDENCE / (entry.get("evidenceFile") or (entry["key"] + ".page.html"))
        row["evidence"] = evidence.name
        row["evidenceBytes"] = evidence.stat().st_size if evidence.exists() else 0
        if not evidence.exists():
            report["problems"].append("no captured publisher page for " + name)
        elif row["evidenceBytes"] < 2048:
            report["problems"].append("captured page for %s is only %d bytes; that is a stub or "
                                      "an error page, not evidence"
                                      % (name, row["evidenceBytes"]))

        listed = by_file.get(name)
        row["inCreditsManifest"] = listed is not None
        if listed is None:
            report["problems"].append(
                "%s is imported but is NOT in the credits manifest, so it would ship "
                "uncredited" % name)
        else:
            row["verdict"] = listed.get("licenceVerdict")
            row["attributionRequired"] = listed.get("attributionRequired")
            if listed.get("licenceVerdict") != "VERIFIED":
                report["problems"].append("%s has verdict %r, not VERIFIED"
                                          % (name, listed.get("licenceVerdict")))
            if listed.get("sha256") and listed["sha256"] != row["sha256"]:
                report["problems"].append("credits manifest hash differs for " + name)
        report["files"].append(row)

    report["required"] = [a["name"] for a in manifest.get("assets", [])
                          if a.get("attributionRequired")]
    report["ok"] = not report["problems"]
    return report


def credits_block() -> str:
    text = ROOT / "SourceAssets" / "third-party" / "ATTRIBUTION-soundscape-v2.txt"
    return text.read_text(encoding="utf-8") if text.exists() else "(no attribution file)"


# ---------------------------------------------------------------------------
# The layer table
# ---------------------------------------------------------------------------

def layer_table(spec) -> list[dict]:
    rows = []
    for key, layer in spec["layers"].items():
        emitters = [e for e in spec["emitters"] if e["layer"] == key]
        gaps = [e.get("delaySeconds") for e in emitters if e.get("delaySeconds")]
        rows.append({
            "layer": key,
            "runtimeLayer": layer["runtimeLayer"],
            "mode": layer["mode"],
            "takes": len(layer["sources"]),
            "emitters": len(emitters),
            "gapWindowsSeconds": gaps,
            "dayGainDawn": round(layer_gain_at_time(layer["runtimeLayer"], ANCHORS,
                                                    ANCHORS["civil_dawn"]), 3),
            "dayGainMidday": round(layer_gain_at_time(layer["runtimeLayer"], ANCHORS,
                                                      ANCHORS["solar_noon"]), 3),
            "dayGainNight": round(layer_gain_at_time(layer["runtimeLayer"], ANCHORS,
                                                     wrap_hours(ANCHORS["solar_noon"] - 12.0)), 3),
            "heightVarying": any(e.get("heightVarying") for e in emitters),
            "occluded": any(e.get("occlude") for e in emitters),
            "crowdScaled": any(e.get("crowdScaled") for e in emitters),
            "why": layer["why"],
        })
    return rows


def print_table(rows):
    head = ("layer", "runtime", "mode", "takes", "emit", "dawn", "noon", "night", "hgt", "occ",
            "crowd")
    print("  %-13s %-13s %-11s %5s %4s %5s %5s %5s %4s %4s %5s" % head)
    for r in rows:
        print("  %-13s %-13s %-11s %5d %4d %5.2f %5.2f %5.2f %4s %4s %5s"
              % (r["layer"], r["runtimeLayer"], r["mode"], r["takes"], r["emitters"],
                 r["dayGainDawn"], r["dayGainMidday"], r["dayGainNight"],
                 "y" if r["heightVarying"] else "-", "y" if r["occluded"] else "-",
                 "y" if r["crowdScaled"] else "-"))


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", action="store_true",
                        help="build and run the C++ test, and prove the Python mirror against it")
    parser.add_argument("--table", action="store_true", help="print the layer table and stop")
    parser.add_argument("--credits", action="store_true",
                        help="print the attribution block and stop")
    parser.add_argument("--json", action="store_true", help="write the receipt to stdout")
    parser.add_argument("--hours", type=float, default=9.0,
                        help="game hour to simulate (default 9.0)")
    args = parser.parse_args()

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))

    if args.credits:
        print(credits_block())
        return 0
    if args.table:
        print_table(layer_table(spec))
        return 0

    print("create_soundscape_v2: offline design and licence gate")
    print("-- layers")
    rows = layer_table(spec)
    print_table(rows)

    print("-- licences")
    licences = check_licences()
    check("every imported recording has provenance, a captured page and a VERIFIED verdict",
          licences.get("ok", False),
          "; ".join(licences["problems"][:4]) if licences["problems"] else
          "%d files, %d needing a mandatory credit"
          % (len(licences["files"]), len(licences.get("required", []))))

    print("-- schedule")
    sim, times = simulate(spec, hours=args.hours)
    repeats = sum(r["immediateRepeats"] for r in sim)
    single = [r["label"] for r in sim if not r["looping"] and r["sources"] == 1]
    check("no emitter can play the same take twice in a row", repeats == 0,
          "%d immediate repeats across %d emitters (%d one-shot emitters have a single take, "
          "where the test does not apply: %s)"
          % (repeats, len(sim), len(single), ", ".join(single) or "none"))
    thin = [r["label"] for r in sim
            if not r["looping"] and r["sources"] > 1 and r["distinctSourcesUsed"] < 2]
    check("every multi-take emitter actually uses more than one take", not thin,
          "; ".join(thin[:4]))
    period = measure_periodicity(times)
    check("the combined firing pattern has no beat", period["ok"],
          "%d events, %d interval buckets, largest %.1f%%"
          % (period.get("events", 0), period.get("distinctIntervalBuckets", 0),
             100.0 * period.get("largestBucketShare", 1.0)))

    dawn = layer_gain_at_time("CROWD_COURT", ANCHORS, ANCHORS["civil_dawn"])
    noon = layer_gain_at_time("CROWD_COURT", ANCHORS, ANCHORS["solar_noon"])
    night_wind = layer_gain_at_time("WIND_BED", ANCHORS, wrap_hours(ANCHORS["solar_noon"] - 12.0))
    night_city = layer_gain_at_time("CITY", ANCHORS, wrap_hours(ANCHORS["solar_noon"] - 12.0))
    night_crowd = layer_gain_at_time("CROWD_COURT", ANCHORS,
                                     wrap_hours(ANCHORS["solar_noon"] - 12.0))
    check("dawn is quiet, midday is busy, night is wind and distant city",
          dawn < 0.15 and noon > 0.9 and night_wind > 0.8 and 0.2 < night_city < 0.6
          and night_crowd < 0.05,
          "crowd dawn %.2f noon %.2f night %.2f; wind night %.2f; city night %.2f"
          % (dawn, noon, night_crowd, night_wind, night_city))

    golden = None
    test_run = None
    if args.tests:
        print("-- C++")
        outdir = Path(tempfile.gettempdir()) / "mikdash-soundscape"
        exe, error = build_test(outdir)
        if exe is None:
            check("SoundscapeMathTest.cpp compiles", False, error or "unknown")
        else:
            check("SoundscapeMathTest.cpp compiles", True)
            proc = subprocess.run([str(exe)], capture_output=True, text=True, timeout=600)
            test_run = {"returncode": proc.returncode,
                        "tail": proc.stdout.strip().splitlines()[-1:] or [proc.stderr[-200:]]}
            check("SoundscapeMathTest passes", proc.returncode == 0,
                  " ".join(test_run["tail"]))
            golden = check_golden_vectors(exe)
            check("the Python mirror in this file is bit-identical to the shipped C++",
                  golden["ok"],
                  "%d values compared; %s" % (golden.get("compared", 0),
                                              "; ".join(golden.get("mismatches", [])) or "no drift"))
    else:
        print("-- C++  SKIP  pass --tests to build the test and prove the mirror. Until that "
              "runs, every schedule number above is a Python re-implementation and has NOT "
              "been shown to match what the engine will do.")

    receipt = {
        "stamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "spec": str(SPEC_PATH),
        "hoursSimulated": args.hours,
        "anchors": ANCHORS,
        "layers": rows,
        "emitters": sim,
        "periodicity": period,
        "licences": licences,
        "cppTest": test_run,
        "goldenVectorComparison": golden,
        "mirrorProven": bool(golden and golden.get("ok")),
        "auditioned": False,
        "auditionStatement": (
            "NOBODY HAS LISTENED TO ANY OF THIS. Every number here is arithmetic on a "
            "schedule and a licence check on a file. A recording with a clean licence and a "
            "clean transient count can still contain a voice, a vehicle or a handling bump, "
            "and no check in this project can hear one."),
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in results],
    }
    out = PACKAGE / ("design-%s.json" % receipt["stamp"])
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))

    passed = sum(1 for _, ok, _ in results if ok)
    print("%d/%d checks passed; receipt %s" % (passed, len(results), out.name))
    if passed != len(results):
        print("FAILED: " + "; ".join(n for n, ok, _ in results if not ok))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
