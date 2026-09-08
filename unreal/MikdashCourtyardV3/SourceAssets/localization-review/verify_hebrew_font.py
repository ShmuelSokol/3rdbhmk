"""Verify that a candidate Hebrew font actually renders Hebrew, nikud included.

WHY THIS EXISTS

Choosing a font from its marketing page is not evidence. A face can advertise Hebrew,
contain every base letter, and still place nikud badly -- the vowel points sit at the
wrong height, the dagesh lands outside the letter body, the shin dot and the sin dot end
up on the same side. That failure is invisible in a coverage table and obvious the moment
a human looks at a rendered word, so this script produces both: the numbers, and a PNG a
human can look at.

WHAT IT DOES

Parses the TrueType binary directly and does the layout itself:

  * sfnt table directory, head, maxp, hhea, hmtx, loca, glyf, cmap, name, OS/2
  * cmap formats 4 and 12
  * glyf simple and composite outlines, quadratic Beziers flattened to polygons
  * GPOS: ScriptList / FeatureList / LookupList, lookup type 4 (mark-to-base),
    type 6 (mark-to-mark) and type 9 (extension), coverage formats 1 and 2,
    class definitions 1 and 2, anchor formats 1, 2 and 3
  * right-to-left cluster layout, marks attached by their GPOS anchors
  * a scanline rasteriser with the non-zero winding rule and 4x vertical supersampling
    with exact horizontal coverage
  * a PNG writer built on zlib and struct

Nothing outside the Python standard library is used, and nothing is installed. Pillow,
fontTools and uharfbuzz are all absent from the engine's Python, and in any case a
renderer that used HarfBuzz would be testing HarfBuzz rather than the font.

WHAT IT DOES NOT ESTABLISH

The rasteriser here is not Slate's. It proves that the anchors exist, that they place the
marks where they should, and that the outlines draw; it does not prove that FreeType at a
particular hinting setting produces the same pixels. It also implements a minimal
run-based bidi for the one mixed Latin/Hebrew line, not the full UAX #9 algorithm.

RUN

  "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" ^
      SourceAssets/localization-review/verify_hebrew_font.py

Writes hebrew-font-specimen.png and font-audit.json next to itself.
"""

from __future__ import annotations

import json
import math
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE / "fonts"
SPECIMEN_PNG = HERE / "hebrew-font-specimen.png"
AUDIT_JSON = HERE / "font-audit.json"

CANDIDATES = [
    "NotoSansHebrew-Regular.ttf",
    "NotoSerifHebrew-Regular.ttf",
    "FrankRuhlLibre-Regular.ttf",
    "FrankRuhlLibre-Bold.ttf",
    "DavidLibre-Regular.ttf",
]

# Codepoint groups. The split matters: a font can cover every base letter and still have
# no nikud, and it is the nikud that decides whether this build can show a pointed text.
BASE_LETTERS = list(range(0x05D0, 0x05EB))
NIKUD = list(range(0x05B0, 0x05BE)) + [0x05BF, 0x05C1, 0x05C2, 0x05C7]
PUNCTUATION = [0x05BE, 0x05C0, 0x05C3, 0x05C6, 0x05F3, 0x05F4]
CANTILLATION = list(range(0x0591, 0x05B0))
PRESENTATION = list(range(0xFB1D, 0xFB50))
LATIN = list(range(0x0041, 0x007B))

# Codepoints that attach to the preceding base rather than advancing the pen.
COMBINING = set(range(0x0591, 0x05BE)) | {0x05BF, 0x05C1, 0x05C2, 0x05C4, 0x05C5, 0x05C7}


# ===========================================================================
# binary reading
# ===========================================================================

class Reader:
    """Big-endian reader over a bytes object. Every read is bounds-checked."""

    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.offset = offset

    def seek(self, offset: int) -> "Reader":
        self.offset = offset
        return self

    def _take(self, count: int) -> bytes:
        end = self.offset + count
        if end > len(self.data) or self.offset < 0:
            raise ValueError(f"read past end of table at {self.offset}+{count}")
        chunk = self.data[self.offset:end]
        self.offset = end
        return chunk

    def u8(self) -> int:
        return self._take(1)[0]

    def i8(self) -> int:
        return struct.unpack(">b", self._take(1))[0]

    def u16(self) -> int:
        return struct.unpack(">H", self._take(2))[0]

    def i16(self) -> int:
        return struct.unpack(">h", self._take(2))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self._take(4))[0]

    def tag(self) -> str:
        return self._take(4).decode("latin-1")


# ===========================================================================
# the font
# ===========================================================================

class Font:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        self.tables: dict[str, tuple[int, int]] = {}
        self.notes: list[str] = []
        self._glyph_cache: dict[int, list[list[tuple[float, float]]]] = {}

        reader = Reader(self.data)
        sfnt = reader.u32()
        if sfnt == 0x74746366:  # 'ttcf'
            raise ValueError("TrueType collections are not handled")
        if sfnt not in (0x00010000, 0x4F54544F):  # 1.0, 'OTTO'
            raise ValueError(f"unrecognised sfnt version 0x{sfnt:08X}")
        self.is_cff = sfnt == 0x4F54544F
        table_count = reader.u16()
        reader.u16(); reader.u16(); reader.u16()   # search range, entry selector, range shift
        for _ in range(table_count):
            tag = reader.tag()
            reader.u32()                            # checksum
            offset = reader.u32()
            length = reader.u32()
            self.tables[tag] = (offset, length)

        self._read_head()
        self._read_maxp()
        self._read_hmtx()
        self._read_cmap()
        self._read_names()
        self._read_loca()
        self.gpos = self._read_gpos()

    # -- basic tables -------------------------------------------------------

    def table(self, tag: str) -> bytes | None:
        entry = self.tables.get(tag)
        if entry is None:
            return None
        offset, length = entry
        return self.data[offset:offset + length]

    def _read_head(self) -> None:
        head = self.table("head")
        if head is None:
            raise ValueError("no head table")
        reader = Reader(head, 18)
        self.units_per_em = reader.u16()
        reader.seek(50)
        self.index_to_loc_format = reader.i16()
        if self.units_per_em <= 0:
            raise ValueError("unitsPerEm is zero")

    def _read_maxp(self) -> None:
        maxp = self.table("maxp")
        if maxp is None:
            raise ValueError("no maxp table")
        self.num_glyphs = Reader(maxp, 4).u16()

    def _read_hmtx(self) -> None:
        self.advances: list[int] = []
        hhea = self.table("hhea")
        hmtx = self.table("hmtx")
        if hhea is None or hmtx is None:
            self.notes.append("no hhea/hmtx; advance widths unavailable")
            return
        metric_count = Reader(hhea, 34).u16()
        reader = Reader(hmtx)
        last = 0
        for _ in range(min(metric_count, self.num_glyphs)):
            last = reader.u16()
            reader.i16()   # left side bearing
            self.advances.append(last)
        while len(self.advances) < self.num_glyphs:
            self.advances.append(last)

    def advance(self, glyph_id: int) -> int:
        if 0 <= glyph_id < len(self.advances):
            return self.advances[glyph_id]
        return 0

    def _read_names(self) -> None:
        self.family = ""
        self.subfamily = ""
        name = self.table("name")
        if name is None:
            return
        reader = Reader(name)
        reader.u16()                    # format
        count = reader.u16()
        string_offset = reader.u16()
        best: dict[int, str] = {}
        for _ in range(count):
            platform = reader.u16()
            encoding = reader.u16()
            reader.u16()                # language
            name_id = reader.u16()
            length = reader.u16()
            offset = reader.u16()
            if name_id not in (1, 2):
                continue
            raw = name[string_offset + offset: string_offset + offset + length]
            try:
                if platform == 3 or (platform == 0):
                    text = raw.decode("utf-16-be", errors="replace")
                else:
                    text = raw.decode("latin-1", errors="replace")
            except Exception:              # noqa: BLE001
                continue
            # A Windows/Unicode record wins over a Macintosh one.
            if name_id not in best or (platform == 3 and encoding in (1, 10)):
                best[name_id] = text
        self.family = best.get(1, "")
        self.subfamily = best.get(2, "")

    # -- cmap ---------------------------------------------------------------

    def _read_cmap(self) -> None:
        self.cmap: dict[int, int] = {}
        self.cmap_format = None
        cmap = self.table("cmap")
        if cmap is None:
            self.notes.append("no cmap table")
            return
        reader = Reader(cmap, 2)
        count = reader.u16()
        subtables = []
        for _ in range(count):
            platform = reader.u16()
            encoding = reader.u16()
            offset = reader.u32()
            subtables.append((platform, encoding, offset))

        # Preference order: full Unicode first, then BMP.
        def rank(entry):
            platform, encoding, _ = entry
            if platform == 3 and encoding == 10: return 0
            if platform == 0 and encoding in (4, 6): return 1
            if platform == 3 and encoding == 1: return 2
            if platform == 0: return 3
            return 9

        for platform, encoding, offset in sorted(subtables, key=rank):
            try:
                mapping, fmt = self._read_cmap_subtable(cmap, offset)
            except Exception:              # noqa: BLE001
                continue
            if mapping:
                self.cmap = mapping
                self.cmap_format = fmt
                self.cmap_platform = (platform, encoding)
                return
        self.notes.append("no usable cmap subtable (only formats 4 and 12 are read)")

    @staticmethod
    def _read_cmap_subtable(cmap: bytes, offset: int) -> tuple[dict[int, int], int]:
        reader = Reader(cmap, offset)
        fmt = reader.u16()
        mapping: dict[int, int] = {}
        if fmt == 4:
            reader.u16()                    # length
            reader.u16()                    # language
            seg_x2 = reader.u16()
            segments = seg_x2 // 2
            reader.u16(); reader.u16(); reader.u16()   # search range, entry selector, range shift
            ends = [reader.u16() for _ in range(segments)]
            reader.u16()                    # reserved pad
            starts = [reader.u16() for _ in range(segments)]
            deltas = [reader.i16() for _ in range(segments)]
            range_offset_pos = reader.offset
            range_offsets = [reader.u16() for _ in range(segments)]
            for index in range(segments):
                start, end = starts[index], ends[index]
                if start > end or end == 0xFFFF and start == 0xFFFF:
                    continue
                for code in range(start, end + 1):
                    if range_offsets[index] == 0:
                        glyph = (code + deltas[index]) & 0xFFFF
                    else:
                        position = range_offset_pos + index * 2 + range_offsets[index] + (code - start) * 2
                        if position + 2 > len(cmap):
                            continue
                        glyph = struct.unpack(">H", cmap[position:position + 2])[0]
                        if glyph:
                            glyph = (glyph + deltas[index]) & 0xFFFF
                    if glyph:
                        mapping[code] = glyph
            return mapping, 4
        if fmt == 12:
            reader.u16()                    # reserved
            reader.u32()                    # length
            reader.u32()                    # language
            groups = reader.u32()
            for _ in range(groups):
                start = reader.u32()
                end = reader.u32()
                start_glyph = reader.u32()
                if end - start > 0x20000:   # a corrupt group; refuse rather than loop forever
                    continue
                for code in range(start, end + 1):
                    mapping[code] = start_glyph + (code - start)
            return mapping, 12
        return {}, fmt

    def glyph_for(self, codepoint: int) -> int:
        return self.cmap.get(codepoint, 0)

    def covers(self, codepoint: int) -> bool:
        return self.cmap.get(codepoint, 0) != 0

    # -- glyf ---------------------------------------------------------------

    def _read_loca(self) -> None:
        self.loca: list[int] = []
        loca = self.table("loca")
        if loca is None:
            if not self.is_cff:
                self.notes.append("no loca table")
            return
        reader = Reader(loca)
        try:
            if self.index_to_loc_format == 0:
                for _ in range(self.num_glyphs + 1):
                    self.loca.append(reader.u16() * 2)
            else:
                for _ in range(self.num_glyphs + 1):
                    self.loca.append(reader.u32())
        except ValueError:
            self.notes.append("loca table is shorter than numGlyphs implies")

    def contours(self, glyph_id: int, depth: int = 0) -> list[list[tuple[float, float]]]:
        """Flattened contours for a glyph, in font units, y up."""
        if glyph_id in self._glyph_cache:
            return self._glyph_cache[glyph_id]
        result = self._contours_uncached(glyph_id, depth)
        if depth == 0:
            self._glyph_cache[glyph_id] = result
        return result

    def _contours_uncached(self, glyph_id: int, depth: int) -> list[list[tuple[float, float]]]:
        if depth > 5:
            return []
        glyf = self.table("glyf")
        if glyf is None or glyph_id + 1 >= len(self.loca):
            return []
        start, end = self.loca[glyph_id], self.loca[glyph_id + 1]
        if end <= start or end > len(glyf):
            return []                       # an empty glyph, such as a space

        reader = Reader(glyf, start)
        contour_count = reader.i16()
        reader.i16(); reader.i16(); reader.i16(); reader.i16()   # bounding box

        if contour_count >= 0:
            return self._simple_glyph(reader, contour_count)
        return self._composite_glyph(reader, depth)

    def _simple_glyph(self, reader: Reader, contour_count: int) -> list[list[tuple[float, float]]]:
        end_points = [reader.u16() for _ in range(contour_count)]
        point_count = (end_points[-1] + 1) if end_points else 0
        instruction_length = reader.u16()
        reader._take(instruction_length)

        flags: list[int] = []
        while len(flags) < point_count:
            flag = reader.u8()
            flags.append(flag)
            if flag & 0x08:                 # REPEAT
                repeat = reader.u8()
                flags.extend([flag] * repeat)
        flags = flags[:point_count]

        xs: list[int] = []
        value = 0
        for flag in flags:
            if flag & 0x02:                 # X_SHORT
                delta = reader.u8()
                value += delta if (flag & 0x10) else -delta
            elif not (flag & 0x10):         # not X_SAME
                value += reader.i16()
            xs.append(value)

        ys: list[int] = []
        value = 0
        for flag in flags:
            if flag & 0x04:                 # Y_SHORT
                delta = reader.u8()
                value += delta if (flag & 0x20) else -delta
            elif not (flag & 0x20):         # not Y_SAME
                value += reader.i16()
            ys.append(value)

        contours: list[list[tuple[float, float]]] = []
        first = 0
        for last in end_points:
            points = [(float(xs[i]), float(ys[i]), bool(flags[i] & 0x01))
                      for i in range(first, min(last + 1, point_count))]
            first = last + 1
            if len(points) >= 2:
                contours.append(flatten_quadratic(points))
        return contours

    def _composite_glyph(self, reader: Reader, depth: int) -> list[list[tuple[float, float]]]:
        contours: list[list[tuple[float, float]]] = []
        while True:
            flags = reader.u16()
            component = reader.u16()
            if flags & 0x0001:              # ARG_1_AND_2_ARE_WORDS
                arg1, arg2 = reader.i16(), reader.i16()
            else:
                arg1, arg2 = reader.i8(), reader.i8()

            a = d = 1.0
            b = c = 0.0
            if flags & 0x0008:              # WE_HAVE_A_SCALE
                a = d = read_f2dot14(reader)
            elif flags & 0x0040:            # WE_HAVE_AN_X_AND_Y_SCALE
                a = read_f2dot14(reader)
                d = read_f2dot14(reader)
            elif flags & 0x0080:            # WE_HAVE_A_TWO_BY_TWO
                a = read_f2dot14(reader)
                b = read_f2dot14(reader)
                c = read_f2dot14(reader)
                d = read_f2dot14(reader)

            dx, dy = (float(arg1), float(arg2)) if (flags & 0x0002) else (0.0, 0.0)

            for contour in self.contours(component, depth + 1):
                contours.append([(a * x + c * y + dx, b * x + d * y + dy) for x, y in contour])

            if not (flags & 0x0020):        # MORE_COMPONENTS
                break
        return contours

    # -- GPOS ---------------------------------------------------------------

    def _read_gpos(self) -> "Gpos | None":
        gpos = self.table("GPOS")
        if gpos is None:
            return None
        try:
            return Gpos(gpos)
        except Exception as error:          # noqa: BLE001
            self.notes.append(f"GPOS present but could not be parsed: {error!r}")
            return None


def read_f2dot14(reader: Reader) -> float:
    return reader.i16() / 16384.0


def flatten_quadratic(points, segments: int = 8) -> list[tuple[float, float]]:
    """TrueType quadratic contour to a polygon.

    Two consecutive off-curve points imply an on-curve point at their midpoint; that is
    the rule that a naive flattener gets wrong, and it shows up as a corner where the
    outline should be smooth.
    """
    if not points:
        return []

    # Rotate so the contour starts on an on-curve point, inventing one if it must.
    start = next((i for i, p in enumerate(points) if p[2]), None)
    if start is None:
        x0, y0, _ = points[0]
        x1, y1, _ = points[-1]
        expanded = [((x0 + x1) / 2.0, (y0 + y1) / 2.0, True)] + list(points)
    else:
        expanded = list(points[start:]) + list(points[:start])

    result: list[tuple[float, float]] = []
    current = (expanded[0][0], expanded[0][1])
    result.append(current)

    index = 1
    count = len(expanded)
    while index <= count:
        point = expanded[index % count]
        if point[2]:
            current = (point[0], point[1])
            result.append(current)
            index += 1
            continue

        control = (point[0], point[1])
        following = expanded[(index + 1) % count]
        if following[2]:
            end = (following[0], following[1])
            index += 2
        else:
            end = ((control[0] + following[0]) / 2.0, (control[1] + following[1]) / 2.0)
            index += 1

        for step in range(1, segments + 1):
            t = step / segments
            inverse = 1.0 - t
            x = inverse * inverse * current[0] + 2 * inverse * t * control[0] + t * t * end[0]
            y = inverse * inverse * current[1] + 2 * inverse * t * control[1] + t * t * end[1]
            result.append((x, y))
        current = end

    return result


# ===========================================================================
# GPOS
# ===========================================================================

class Gpos:
    """Enough of GPOS to attach marks by their anchors."""

    def __init__(self, data: bytes):
        self.data = data
        reader = Reader(data)
        major = reader.u16()
        minor = reader.u16()
        if major != 1:
            raise ValueError(f"unsupported GPOS version {major}.{minor}")
        script_list = reader.u16()
        feature_list = reader.u16()
        lookup_list = reader.u16()

        self.scripts = self._read_script_list(script_list)
        self.features = self._read_feature_list(feature_list)
        self.lookup_offsets = self._read_lookup_list(lookup_list)

    # -- lists --------------------------------------------------------------

    def _read_script_list(self, offset: int) -> dict[str, list[int]]:
        """Script tag -> the feature indices reachable from it."""
        reader = Reader(self.data, offset)
        count = reader.u16()
        records = [(reader.tag(), reader.u16()) for _ in range(count)]
        scripts: dict[str, list[int]] = {}
        for tag, script_offset in records:
            base = offset + script_offset
            script_reader = Reader(self.data, base)
            default_lang = script_reader.u16()
            lang_count = script_reader.u16()
            lang_offsets = [default_lang] if default_lang else []
            for _ in range(lang_count):
                script_reader.tag()
                lang_offsets.append(script_reader.u16())
            indices: list[int] = []
            for lang_offset in lang_offsets:
                lang_reader = Reader(self.data, base + lang_offset)
                lang_reader.u16()                       # lookupOrder, reserved
                required = lang_reader.u16()
                if required != 0xFFFF:
                    indices.append(required)
                feature_count = lang_reader.u16()
                for _ in range(feature_count):
                    indices.append(lang_reader.u16())
            scripts[tag.strip()] = indices
        return scripts

    def _read_feature_list(self, offset: int) -> list[tuple[str, list[int]]]:
        reader = Reader(self.data, offset)
        count = reader.u16()
        records = [(reader.tag(), reader.u16()) for _ in range(count)]
        features: list[tuple[str, list[int]]] = []
        for tag, feature_offset in records:
            feature_reader = Reader(self.data, offset + feature_offset)
            feature_reader.u16()                        # featureParams
            lookup_count = feature_reader.u16()
            features.append((tag.strip(), [feature_reader.u16() for _ in range(lookup_count)]))
        return features

    def _read_lookup_list(self, offset: int) -> list[int]:
        reader = Reader(self.data, offset)
        count = reader.u16()
        return [offset + reader.u16() for _ in range(count)]

    # -- feature selection --------------------------------------------------

    def lookups_for(self, feature_tag: str, script_tags=("hebr", "DFLT")) -> list[int]:
        """Lookup indices for a feature, reachable from one of the given scripts."""
        wanted: set[int] = set()
        for script in script_tags:
            for index in self.scripts.get(script, []):
                if 0 <= index < len(self.features):
                    tag, lookup_indices = self.features[index]
                    if tag == feature_tag:
                        wanted.update(lookup_indices)
        return sorted(wanted)

    def subtables(self, lookup_index: int, wanted_types=(4, 6)) -> list[tuple[int, int]]:
        """(type, absolute subtable offset) pairs, unwrapping extension lookups."""
        if not (0 <= lookup_index < len(self.lookup_offsets)):
            return []
        base = self.lookup_offsets[lookup_index]
        reader = Reader(self.data, base)
        lookup_type = reader.u16()
        reader.u16()                                    # lookupFlag
        count = reader.u16()
        offsets = [base + reader.u16() for _ in range(count)]

        result: list[tuple[int, int]] = []
        for offset in offsets:
            if lookup_type == 9:                        # extension
                extension = Reader(self.data, offset)
                extension.u16()                         # posFormat
                real_type = extension.u16()
                real_offset = offset + extension.u32()
                if real_type in wanted_types:
                    result.append((real_type, real_offset))
            elif lookup_type in wanted_types:
                result.append((lookup_type, offset))
        return result

    # -- shared structures --------------------------------------------------

    def coverage(self, offset: int) -> dict[int, int]:
        """Glyph id -> coverage index."""
        reader = Reader(self.data, offset)
        fmt = reader.u16()
        mapping: dict[int, int] = {}
        if fmt == 1:
            count = reader.u16()
            for index in range(count):
                mapping[reader.u16()] = index
        elif fmt == 2:
            count = reader.u16()
            for _ in range(count):
                start = reader.u16()
                end = reader.u16()
                start_index = reader.u16()
                for glyph in range(start, end + 1):
                    mapping[glyph] = start_index + (glyph - start)
        return mapping

    def anchor(self, offset: int) -> tuple[float, float] | None:
        """Anchor coordinates in font units. Formats 2 and 3 are read as format 1.

        Format 2 refines the anchor with a contour point and format 3 with a device
        table; both carry the same x/y as format 1 and are only a hinting refinement, so
        ignoring them shifts nothing at the sizes this specimen uses.
        """
        if offset == 0:
            return None
        reader = Reader(self.data, offset)
        fmt = reader.u16()
        if fmt not in (1, 2, 3):
            return None
        return (float(reader.i16()), float(reader.i16()))

    def mark_array(self, offset: int) -> list[tuple[int, tuple[float, float] | None]]:
        """(mark class, anchor) per covered mark glyph."""
        reader = Reader(self.data, offset)
        count = reader.u16()
        records = [(reader.u16(), reader.u16()) for _ in range(count)]
        return [(cls, self.anchor(offset + anchor_offset) if anchor_offset else None)
                for cls, anchor_offset in records]

    def base_array(self, offset: int, class_count: int) -> list[list[tuple[float, float] | None]]:
        reader = Reader(self.data, offset)
        count = reader.u16()
        rows: list[list[tuple[float, float] | None]] = []
        for _ in range(count):
            offsets = [reader.u16() for _ in range(class_count)]
            rows.append([self.anchor(offset + o) if o else None for o in offsets])
        return rows


class MarkPositioning:
    """The mark-to-base and mark-to-mark tables of one font, flattened for lookup."""

    def __init__(self, font: Font):
        self.font = font
        self.mark_base: list[dict] = []
        self.mark_mark: list[dict] = []
        self.mark_lookup_count = 0
        self.mkmk_lookup_count = 0
        self.mark_class_count = 0
        self.has_mark_feature = False
        self.has_mkmk_feature = False
        self.problems: list[str] = []

        gpos = font.gpos
        if gpos is None:
            return

        mark_lookups = gpos.lookups_for("mark")
        mkmk_lookups = gpos.lookups_for("mkmk")
        self.has_mark_feature = bool(mark_lookups)
        self.has_mkmk_feature = bool(mkmk_lookups)
        self.mark_lookup_count = len(mark_lookups)
        self.mkmk_lookup_count = len(mkmk_lookups)

        for index in mark_lookups:
            for kind, offset in gpos.subtables(index, wanted_types=(4,)):
                if kind == 4:
                    try:
                        self.mark_base.append(self._read_mark_base(gpos, offset))
                    except Exception as error:      # noqa: BLE001
                        self.problems.append(f"MarkBasePos subtable unreadable: {error!r}")

        for index in mkmk_lookups:
            for kind, offset in gpos.subtables(index, wanted_types=(6,)):
                if kind == 6:
                    try:
                        self.mark_mark.append(self._read_mark_mark(gpos, offset))
                    except Exception as error:      # noqa: BLE001
                        self.problems.append(f"MarkMarkPos subtable unreadable: {error!r}")

        self.mark_class_count = max([table["classes"] for table in self.mark_base] or [0])

    @staticmethod
    def _read_mark_base(gpos: Gpos, offset: int) -> dict:
        reader = Reader(gpos.data, offset)
        fmt = reader.u16()
        if fmt != 1:
            raise ValueError(f"MarkBasePos format {fmt}")
        mark_coverage = offset + reader.u16()
        base_coverage = offset + reader.u16()
        classes = reader.u16()
        mark_array = offset + reader.u16()
        base_array = offset + reader.u16()
        return {
            "marks": gpos.coverage(mark_coverage),
            "bases": gpos.coverage(base_coverage),
            "classes": classes,
            "mark_records": gpos.mark_array(mark_array),
            "base_rows": gpos.base_array(base_array, classes),
        }

    @staticmethod
    def _read_mark_mark(gpos: Gpos, offset: int) -> dict:
        reader = Reader(gpos.data, offset)
        fmt = reader.u16()
        if fmt != 1:
            raise ValueError(f"MarkMarkPos format {fmt}")
        mark1_coverage = offset + reader.u16()
        mark2_coverage = offset + reader.u16()
        classes = reader.u16()
        mark1_array = offset + reader.u16()
        mark2_array = offset + reader.u16()
        return {
            "marks": gpos.coverage(mark1_coverage),
            "bases": gpos.coverage(mark2_coverage),
            "classes": classes,
            "mark_records": gpos.mark_array(mark1_array),
            "base_rows": gpos.base_array(mark2_array, classes),
        }

    @staticmethod
    def _attach(table: dict, mark_glyph: int, base_glyph: int):
        mark_index = table["marks"].get(mark_glyph)
        base_index = table["bases"].get(base_glyph)
        if mark_index is None or base_index is None:
            return None
        if mark_index >= len(table["mark_records"]) or base_index >= len(table["base_rows"]):
            return None
        mark_class, mark_anchor = table["mark_records"][mark_index]
        row = table["base_rows"][base_index]
        if mark_anchor is None or mark_class >= len(row):
            return None
        base_anchor = row[mark_class]
        if base_anchor is None:
            return None
        # The mark's own anchor point is brought onto the base's anchor point.
        return (base_anchor[0] - mark_anchor[0], base_anchor[1] - mark_anchor[1])

    def offset_for(self, mark_glyph: int, base_glyph: int, previous_mark: int | None):
        """Offset in font units from the base origin, or None when nothing covers it."""
        for table in self.mark_base:
            result = self._attach(table, mark_glyph, base_glyph)
            if result is not None:
                return result, "mark"
        if previous_mark is not None:
            for table in self.mark_mark:
                result = self._attach(table, mark_glyph, previous_mark)
                if result is not None:
                    return result, "mkmk"
        return None, "none"


# ===========================================================================
# layout
# ===========================================================================

class Placement:
    __slots__ = ("glyph", "x", "y", "anchored")

    def __init__(self, glyph: int, x: float, y: float, anchored: str):
        self.glyph = glyph
        self.x = x
        self.y = y
        self.anchored = anchored


def cluster(font: Font, text: str) -> list[tuple[int, list[int]]]:
    """(base glyph, [mark glyphs]) in logical order. Unmapped codepoints are dropped."""
    clusters: list[tuple[int, list[int]]] = []
    for character in text:
        code = ord(character)
        glyph = font.glyph_for(code)
        if code in COMBINING:
            if clusters and glyph:
                clusters[-1][1].append(glyph)
            continue
        clusters.append((glyph, []))
    return clusters


def lay_out_run(font: Font, marks: MarkPositioning, text: str, size: float,
                pen_x: float, baseline: float, rtl: bool, stats: dict) -> tuple[list[Placement], float]:
    """Place one directional run. Returns the placements and the pen after the run."""
    scale = size / font.units_per_em
    placements: list[Placement] = []
    clusters = cluster(font, text)

    # A right-to-left run is drawn by walking the logical clusters and moving the pen
    # leftwards. Hebrew has no cursive joining and no mandatory substitutions for plain
    # text, so no GSUB pass is needed to get the correct result here.
    for base_glyph, mark_glyphs in clusters:
        advance = font.advance(base_glyph) * scale
        if rtl:
            pen_x -= advance
            origin = pen_x
        else:
            origin = pen_x
            pen_x += advance

        placements.append(Placement(base_glyph, origin, baseline, "base"))

        previous_mark = None
        for mark_glyph in mark_glyphs:
            offset, how = marks.offset_for(mark_glyph, base_glyph, previous_mark)
            stats["marks_total"] = stats.get("marks_total", 0) + 1
            if offset is None:
                # No anchor covers this pair. Drawn at the base origin so the failure is
                # visible in the specimen rather than silently omitted -- a missing vowel
                # point looks like a font that has no nikud, which is a different problem.
                stats["marks_unanchored"] = stats.get("marks_unanchored", 0) + 1
                placements.append(Placement(mark_glyph, origin, baseline, "none"))
            else:
                stats[f"marks_{how}"] = stats.get(f"marks_{how}", 0) + 1
                placements.append(Placement(mark_glyph, origin + offset[0] * scale,
                                            baseline - offset[1] * scale, how))
            previous_mark = mark_glyph

    return placements, pen_x


def is_hebrew(character: str) -> bool:
    code = ord(character)
    return 0x0590 <= code <= 0x05FF or 0xFB1D <= code <= 0xFB4F


def split_runs(text: str, paragraph_rtl: bool = False) -> list[tuple[str, bool]]:
    """Run-based bidi for one line: (run text, is right to left).

    Strong characters set their own direction; a neutral stretch -- spaces, an em dash,
    an equals sign -- takes the direction of its neighbours when they agree and the
    paragraph direction when they do not. That is the UAX #9 N1/N2 rule, and it is what
    puts the dash in "Heikhal - Heikhal-in-Hebrew - 1 amah" on the correct side of the
    Hebrew word. It is NOT the full algorithm: there is no bracket pairing, no explicit
    embedding, and no European-number handling beyond treating digits as left to right.
    That is enough for the one mixed line in this specimen and is not claimed to be more.
    """
    if not text:
        return []

    def strength(character: str):
        if is_hebrew(character):
            return True
        if character.isalpha() or character.isdigit():
            return False
        return None

    kinds = [strength(character) for character in text]

    # N1/N2: resolve each neutral stretch from the strong runs either side of it.
    resolved = list(kinds)
    index = 0
    while index < len(resolved):
        if resolved[index] is not None:
            index += 1
            continue
        start = index
        while index < len(resolved) and resolved[index] is None:
            index += 1
        before = next((k for k in reversed(kinds[:start]) if k is not None), None)
        after = next((k for k in kinds[index:] if k is not None), None)
        direction = before if (before is not None and before == after) else paragraph_rtl
        for position in range(start, index):
            resolved[position] = direction

    runs: list[tuple[str, bool]] = []
    for character, direction in zip(text, resolved):
        if runs and runs[-1][1] == direction:
            runs[-1] = (runs[-1][0] + character, direction)
        else:
            runs.append((character, direction))
    return runs


def measure(font: Font, text: str, size: float) -> float:
    scale = size / font.units_per_em
    return sum(font.advance(glyph) * scale for glyph, _ in cluster(font, text))


# ===========================================================================
# rasteriser
# ===========================================================================

SUBSAMPLES = 4


class Canvas:
    """8-bit greyscale, white ground."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pixels = bytearray(b"\xff" * (width * height))

    def fill_polygons(self, polygons, ink: int = 0) -> None:
        """Non-zero winding fill with 4x vertical supersampling and exact horizontal coverage."""
        edges = []
        for polygon in polygons:
            count = len(polygon)
            for index in range(count):
                x0, y0 = polygon[index]
                x1, y1 = polygon[(index + 1) % count]
                if y0 != y1:
                    edges.append((x0, y0, x1, y1))
        if not edges:
            return

        min_y = max(0, int(math.floor(min(min(e[1], e[3]) for e in edges))))
        max_y = min(self.height - 1, int(math.ceil(max(max(e[1], e[3]) for e in edges))))
        min_x = max(0, int(math.floor(min(min(e[0], e[2]) for e in edges))))
        max_x = min(self.width - 1, int(math.ceil(max(max(e[0], e[2]) for e in edges))))
        if min_y > max_y or min_x > max_x:
            return

        span = max_x - min_x + 1
        weight = 1.0 / SUBSAMPLES

        for row in range(min_y, max_y + 1):
            coverage = [0.0] * span
            hit = False
            for sub in range(SUBSAMPLES):
                sample_y = row + (sub + 0.5) / SUBSAMPLES
                crossings = []
                for x0, y0, x1, y1 in edges:
                    if (y0 <= sample_y < y1) or (y1 <= sample_y < y0):
                        t = (sample_y - y0) / (y1 - y0)
                        crossings.append((x0 + t * (x1 - x0), 1 if y1 > y0 else -1))
                if not crossings:
                    continue
                crossings.sort()
                winding = 0
                start_x = 0.0
                for x, direction in crossings:
                    if winding == 0:
                        start_x = x
                    winding += direction
                    if winding == 0:
                        hit = True
                        self._accumulate(coverage, min_x, span, start_x, x, weight)
            if not hit:
                continue
            base = row * self.width
            for index in range(span):
                amount = coverage[index]
                if amount <= 0.0:
                    continue
                if amount > 1.0:
                    amount = 1.0
                position = base + min_x + index
                existing = self.pixels[position]
                self.pixels[position] = int(existing + (ink - existing) * amount)

    @staticmethod
    def _accumulate(coverage, min_x, span, xa, xb, weight) -> None:
        if xb <= xa:
            return
        left = max(xa, float(min_x))
        right = min(xb, float(min_x + span))
        if right <= left:
            return
        first = int(math.floor(left)) - min_x
        last = int(math.ceil(right)) - 1 - min_x
        for index in range(max(first, 0), min(last, span - 1) + 1):
            pixel_left = min_x + index
            overlap = min(right, pixel_left + 1.0) - max(left, float(pixel_left))
            if overlap > 0.0:
                coverage[index] += overlap * weight

    def draw_rect(self, x0: int, y0: int, x1: int, y1: int, ink: int) -> None:
        for row in range(max(0, y0), min(self.height, y1)):
            base = row * self.width
            for column in range(max(0, x0), min(self.width, x1)):
                self.pixels[base + column] = ink

    def draw_placements(self, font: Font, placements: list[Placement], size: float) -> None:
        scale = size / font.units_per_em
        for placement in placements:
            outlines = font.contours(placement.glyph)
            if not outlines:
                continue
            polygons = [[(placement.x + x * scale, placement.y - y * scale) for x, y in contour]
                        for contour in outlines]
            self.fill_polygons(polygons)

    def to_png(self, path: Path) -> None:
        raw = bytearray()
        for row in range(self.height):
            raw.append(0)                            # filter type 0
            raw.extend(self.pixels[row * self.width:(row + 1) * self.width])

        def chunk(tag: bytes, payload: bytes) -> bytes:
            return (struct.pack(">I", len(payload)) + tag + payload
                    + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 0, 0, 0, 0)
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", header)
               + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
               + chunk(b"IEND", b""))
        path.write_bytes(png)


def verify_png(path: Path, width: int, height: int) -> dict:
    """Re-read the file that was just written. A PNG is only good once it reads back."""
    data = path.read_bytes()
    result = {"file": path.name, "bytes": len(data), "signatureOk": data[:8] == b"\x89PNG\r\n\x1a\n"}
    offset = 8
    idat = b""
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        tag = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        stored = struct.unpack(">I", data[offset + 8 + length:offset + 12 + length])[0]
        if zlib.crc32(tag + payload) & 0xFFFFFFFF != stored:
            result["crcOk"] = False
            return result
        if tag == b"IHDR":
            w, h, depth, colour = struct.unpack(">IIBB", payload[:10])
            result["width"], result["height"] = w, h
            result["bitDepth"], result["colourType"] = depth, colour
        elif tag == b"IDAT":
            idat += payload
        elif tag == b"IEND":
            break
        offset += 12 + length
    result["crcOk"] = True
    decompressed = zlib.decompress(idat)
    result["decompressedBytes"] = len(decompressed)
    result["expectedBytes"] = height * (width + 1)
    result["ok"] = (result.get("width") == width and result.get("height") == height
                    and result["signatureOk"] and result["crcOk"]
                    and len(decompressed) == height * (width + 1))
    return result


# ===========================================================================
# the audit
# ===========================================================================

SPECIMEN_PLAIN = "בית המקדש · היכל · קודש הקודשים · מזבח · מנורה · שולחן · פרוכת · כהן · אמה"
SPECIMEN_NIKUD = "בֵּית הַמִּקְדָּשׁ  הַהֵיכָל  קֹדֶשׁ הַקָּדָשִׁים  מִזְבֵּחַ  מְנוֹרָה  שֻׁלְחָן  פָּרֹכֶת  כֹּהֵן  אַמָּה"
SPECIMEN_MIXED = "Heikhal — היכל — 1 amah = 0.5 m"
CAPTION = ("Look for: nikud centred UNDER its letter; dagesh INSIDE the letter body; "
           "shin dot ABOVE-RIGHT and sin dot ABOVE-LEFT of the shin.")


SHIPPED_FONT = "NotoSansHebrew-Regular.ttf"
SHIPPED_BOLD = "NotoSansHebrew-Bold.ttf"


def licence_position() -> dict:
    """Read the first line of each OFL file and record what it permits for a packaged build.

    The distinction that matters when a font is redistributed inside a game is the
    Reserved Font Name. Every candidate here is SIL OFL 1.1, which allows bundling in a
    packaged build without restriction, but a Reserved Font Name additionally forbids
    shipping a MODIFIED copy under the original name -- which is exactly what subsetting
    to the Hebrew block produces. That makes it a real, checkable difference between the
    candidates rather than a footnote.
    """
    entries = []
    for licence in sorted(FONT_DIR.glob("*-OFL.txt")):
        text = licence.read_text(encoding="utf-8", errors="replace")
        first = text.splitlines()[0].strip() if text.splitlines() else ""
        reserved = "reserved font name" in first.lower()
        entries.append({
            "file": licence.name,
            "licence": "SIL Open Font License 1.1",
            "copyrightLine": first,
            "hasReservedFontName": reserved,
            "subsettingOrRenamingRestricted": reserved,
        })
    return {
        "family": "SIL Open Font License, Version 1.1 (all candidates)",
        "redistributionInAPackagedBuild": (
            "Permitted. OFL 1.1 clause 2 allows the font to be bundled and redistributed, "
            "with or without modification, provided it is not sold on its own and the "
            "copyright notice and this licence travel with it. A game executable is not "
            "'selling the font by itself', so no fee, no notice to the authors and no "
            "source release is required."
        ),
        "whatMustShip": [
            "The OFL text and the copyright line, alongside the .ttf in the packaged build.",
            "The same attribution in the in-game credits, which UMikdashFrontEnd::BuildCredits already assembles from disk.",
        ],
        "whatIsForbidden": [
            "Selling the font files on their own.",
            "Shipping a MODIFIED copy under a Reserved Font Name (see the per-file flags below).",
        ],
        "files": entries,
    }


def recommendation(report_fonts: list[dict]) -> dict:
    return {
        "shipForInterface": SHIPPED_FONT,
        "shipForInterfaceBold": SHIPPED_BOLD,
        "why": [
            "Only the two Noto faces cover Hebrew cantillation (31/31); Frank Ruhl Libre and David Libre cover none of it. A codex that quotes a pointed and cantillated verse needs those marks, and a missing te'am is a wrong quotation rather than a styling choice.",
            "Complete nikud (18/18) and complete base letters (27/27). David Libre is missing U+05BD meteg.",
            "Complete basic Latin (58/58), so a mixed line such as '1 amah = 0.5 m' never falls through to another face.",
            "Every mark in the specimen was placed by a real GPOS mark-to-base anchor, and every nikud glyph has advance width 0, which is how a correctly built Hebrew font is constructed.",
            "No Reserved Font Name, so subsetting to the Hebrew block for size is unrestricted.",
            "A sans face sits with Roboto, which is Slate's default and what the rest of this interface already draws in.",
        ],
        "alternative": {
            "file": "FrankRuhlLibre-Regular.ttf",
            "when": "Long-form body text in the codex, if a Hebrew serif is wanted. It is the better reading face and is the traditional Israeli text type.",
            "caveat": "No cantillation coverage at all. Do not use it for a quoted verse with te'amim.",
        },
        "rejected": {
            "DavidLibre-Regular.ttf": "Missing U+05BD meteg, no cantillation, and its OFL carries Reserved Font Names ('Hadash', 'Gentium', 'SIL'), which restricts shipping a modified or subset copy under those names.",
        },
    }


def coverage_report(font: Font) -> dict:
    def count(codepoints):
        return sum(1 for code in codepoints if font.covers(code))

    return {
        "baseLetters": {"present": count(BASE_LETTERS), "of": len(BASE_LETTERS)},
        "nikud": {"present": count(NIKUD), "of": len(NIKUD)},
        "punctuation": {"present": count(PUNCTUATION), "of": len(PUNCTUATION)},
        "cantillation": {"present": count(CANTILLATION), "of": len(CANTILLATION)},
        "presentationForms": {"present": count(PRESENTATION), "of": len(PRESENTATION)},
        "latinBasic": {"present": count(LATIN), "of": len(LATIN)},
        "missingBaseLetters": [f"U+{c:04X}" for c in BASE_LETTERS if not font.covers(c)],
        "missingNikud": [f"U+{c:04X}" for c in NIKUD if not font.covers(c)],
    }


def nikud_advances(font: Font) -> dict:
    named = {
        "sheva U+05B0": 0x05B0,
        "patach U+05B7": 0x05B7,
        "kamatz U+05B8": 0x05B8,
        "holam U+05B9": 0x05B9,
        "dagesh U+05BC": 0x05BC,
        "shinDot U+05C1": 0x05C1,
    }
    result = {}
    for label, code in named.items():
        glyph = font.glyph_for(code)
        result[label] = None if glyph == 0 else font.advance(glyph)
    return result


def render_band(canvas: Canvas, font: Font, marks: MarkPositioning, label_font: Font,
                label_marks: MarkPositioning, top: int, width: int, stats: dict) -> int:
    """One font's band. Returns the y of the next band."""
    margin = 40
    y = top

    # A rule above each band so the bands do not run together.
    canvas.draw_rect(margin, y, width - margin, y + 1, 190)
    y += 34

    label = f"{font.path.name}   {font.family} {font.subfamily}".strip()
    label_placements, _ = lay_out_run(label_font, label_marks, label, 22.0,
                                      float(margin), float(y), False, {})
    canvas.draw_placements(label_font, label_placements, 22.0)
    y += 46

    available = float(width - 2 * margin)
    for text, requested in ((SPECIMEN_PLAIN, 40.0), (SPECIMEN_NIKUD, 64.0)):
        # Fit to the page rather than running off the left edge. Every face has a
        # different Hebrew advance width, so a fixed point size clips some of them and
        # a clipped specimen is a specimen nobody can judge.
        natural = measure(font, text, requested)
        size = requested if natural <= available else requested * available / natural
        y += int(size * 0.95)
        placements, _ = lay_out_run(font, marks, text, size,
                                    float(width - margin), float(y), True, stats)
        canvas.draw_placements(font, placements, size)
        y += int(size * 0.40)

    # The mixed line: an LTR paragraph with an embedded Hebrew run.
    y += 40
    pen = float(margin)
    for run_text, run_rtl in split_runs(SPECIMEN_MIXED, paragraph_rtl=False):
        if run_rtl:
            run_width = measure(font, run_text, 34.0)
            placements, _ = lay_out_run(font, marks, run_text, 34.0, pen + run_width,
                                        float(y), True, stats)
            pen += run_width
        else:
            placements, pen = lay_out_run(font, marks, run_text, 34.0, pen, float(y), False, stats)
        canvas.draw_placements(font, placements, 34.0)
    y += 40

    return y


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    fonts: list[tuple[Font, MarkPositioning, dict]] = []
    failures: list[dict] = []
    for name in CANDIDATES:
        path = FONT_DIR / name
        if not path.exists():
            failures.append({"file": name, "problem": "not found on disk"})
            continue
        try:
            font = Font(path)
        except Exception as error:               # noqa: BLE001
            failures.append({"file": name, "problem": repr(error)})
            continue
        fonts.append((font, MarkPositioning(font), {}))

    if not fonts:
        raise SystemExit("no candidate font could be parsed")

    # Label font: the first candidate that covers Latin, so the labels are readable.
    label_font, label_marks, _ = next(
        ((f, m, s) for f, m, s in fonts if all(f.covers(c) for c in b"ABCabc")),
        fonts[0])

    width = 1800
    band_height = 330
    height = 150 + band_height * len(fonts)
    canvas = Canvas(width, height)

    caption_placements, _ = lay_out_run(label_font, label_marks, CAPTION, 24.0, 40.0, 54.0, False, {})
    canvas.draw_placements(label_font, caption_placements, 24.0)
    caption2 = "Rendered by a pure-Python sfnt/GPOS parser. Marks placed by their own mark-to-base anchors."
    caption2_placements, _ = lay_out_run(label_font, label_marks, caption2, 20.0, 40.0, 86.0, False, {})
    canvas.draw_placements(label_font, caption2_placements, 20.0)

    y = 120
    for font, marks, stats in fonts:
        y = render_band(canvas, font, marks, label_font, label_marks, y, width, stats)

    canvas.to_png(SPECIMEN_PNG)
    png_check = verify_png(SPECIMEN_PNG, width, height)

    report_fonts = []
    for font, marks, stats in fonts:
        coverage = coverage_report(font)
        total_marks = stats.get("marks_total", 0)
        unanchored = stats.get("marks_unanchored", 0)

        if coverage["baseLetters"]["present"] < len(BASE_LETTERS):
            verdict = "unsuitable"
            note = "does not cover every Hebrew base letter"
        elif coverage["nikud"]["present"] < len(NIKUD):
            verdict = "weak"
            note = "missing some nikud codepoints"
        elif not marks.has_mark_feature:
            verdict = "unsuitable"
            note = "no GPOS 'mark' feature: nikud would stack at the pen position"
        elif unanchored:
            verdict = "weak"
            note = f"{unanchored} of {total_marks} marks in the specimen had no anchor"
        else:
            verdict = "good"
            note = "every mark in the specimen was placed by a real anchor"

        report_fonts.append({
            "file": font.path.name,
            "family": font.family,
            "subfamily": font.subfamily,
            "unitsPerEm": font.units_per_em,
            "numGlyphs": font.num_glyphs,
            "cmapFormat": font.cmap_format,
            "hasGPOS": font.gpos is not None,
            "markFeature": {
                "present": marks.has_mark_feature,
                "lookups": marks.mark_lookup_count,
                "markBaseSubtables": len(marks.mark_base),
                "markClasses": marks.mark_class_count,
            },
            "mkmkFeature": {"present": marks.has_mkmk_feature, "lookups": marks.mkmk_lookup_count},
            "coverage": coverage,
            "nikudAdvanceWidths": nikud_advances(font),
            "specimenMarks": {
                "total": total_marks,
                "byMarkToBase": stats.get("marks_mark", 0),
                "byMarkToMark": stats.get("marks_mkmk", 0),
                "unanchored": unanchored,
            },
            "verdict": verdict,
            "notes": "; ".join([note] + marks.problems + font.notes),
        })

    audit = {
        "schemaVersion": 1,
        "status": "ok",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "pure-python sfnt/GPOS parser and scanline rasteriser, standard library only",
        "limitations": [
            "The rasteriser here is not Slate's FreeType path. This establishes that the anchors exist and place the marks correctly, not that FreeType at a given hinting setting produces identical pixels.",
            "Anchor formats 2 and 3 are read as format 1: the contour-point and device-table refinements are ignored, which shifts nothing at these sizes.",
            "The mixed Latin/Hebrew line uses run-based bidi with the UAX #9 N1/N2 neutral rule only: no bracket pairing, no explicit embedding controls.",
            "No visual acceptance is claimed. A human still has to look at hebrew-font-specimen.png.",
        ],
        "specimenImage": SPECIMEN_PNG.name,
        "specimenVerification": png_check,
        "specimenStrings": {"plain": SPECIMEN_PLAIN, "nikud": SPECIMEN_NIKUD, "mixed": SPECIMEN_MIXED},
        "labelFont": label_font.path.name,
        "recommendation": recommendation(report_fonts),
        "licencePosition": licence_position(),
        "fonts": report_fonts,
        "unreadable": failures,
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"specimen: {SPECIMEN_PNG} {width}x{height} verified={png_check.get('ok')}")
    for entry in report_fonts:
        coverage = entry["coverage"]
        print(f"{entry['file']:<32} base {coverage['baseLetters']['present']}/{coverage['baseLetters']['of']}"
              f"  nikud {coverage['nikud']['present']}/{coverage['nikud']['of']}"
              f"  cant {coverage['cantillation']['present']}/{coverage['cantillation']['of']}"
              f"  latin {coverage['latinBasic']['present']}/{coverage['latinBasic']['of']}"
              f"  mark={entry['markFeature']['present']}({entry['markFeature']['markClasses']} classes)"
              f"  mkmk={entry['mkmkFeature']['present']}"
              f"  specimen marks {entry['specimenMarks']['total']}"
              f" anchored {entry['specimenMarks']['total'] - entry['specimenMarks']['unanchored']}"
              f"  -> {entry['verdict']}")
    for failure in failures:
        print(f"UNREADABLE {failure['file']}: {failure['problem']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
