# -*- coding: utf-8 -*-
"""GateSecurityV1: the modern security checkpoint that stands on the gate approaches --
walk-through metal detector arches, a bag-scanner table, belt stanchions, a guard booth, a
shoe rack, and signage in two forms (a tall post-mounted panel and a wall-mounted plate).

Offline only. --export writes SourceAssets/security-review/GateSecurityV1/: OBJ parts,
geometry-manifest.json and preview renders; and SourceAssets/security-review/signs/: the sign
face PNGs, a glyph-check receipt and a textured preview of each sign as it will appear on the
mesh. No engine launch, no Content/ change, no map action. Native import and placement live in
Scripts/release_gate_security.py.

WHAT IS ASSERTED AND WHAT IS ONLY DEPICTED
------------------------------------------
Two different kinds of thing stand at this gate. SourceAssets/security-review/sources.md marks
every claim certain / disputed / modern-staging; the short version:

  HALACHA, stated on the signage as a rule of the place, not as a request:
    * A person may not enter Har HaBayit wearing shoes. Mishnah Berachos 9:5; Rambam,
      Hilchos Beis HaBechira 7:2.
    * The Mount may not be used as a shortcut (kappandaria), and one may not spit there.
      Same mishnah, same halacha in Rambam.

  MODERN STAGING, asserted of nothing but today's Jerusalem:
    * The metal detector arches, the bag scanner, the stanchions, the booth and the guards.
    * The rule about telephones.
      These are modelled on the entrance procedure at the Har HaBayit and Kotel plaza
      approaches TODAY. No classical source describes anything of the kind, none is cited for
      them, and nothing here is a claim about the Temple or its courts.

  DEPICTED, NOT ASSERTED: every dimension of every object below. There is no measured drawing
  of a Jerusalem checkpoint in this project and none is claimed. The sizes are ordinary
  security-equipment sizes chosen so a 175 cm figure walks through an arch without stooping,
  reaches a table at waist height and reads a sign at eye level. They are staging, not survey.

TEXT
----
Trilingual Hebrew / English / Arabic, as real Jerusalem signage is. There is no PIL and no
numpy in the engine python, so this file carries its own TrueType reader and scanline
rasteriser and its own PNG writer, and it does its own Hebrew right-to-left ordering and its
own Arabic contextual shaping (the Unicode presentation forms of block FE70..FEFF, including
the lam-alef ligatures). The glyph check that proves the text is not mojibake is written to
signs/glyph-check.json and printed by --export; see verify_glyphs().

Conventions: centimetres. Canonical Unreal axes X east, +Y south, Z up. In the LOCAL frame of
every mesh here, +X is the direction of travel through the checkpoint (towards the gate), +Y is
to the traveller's right, and the pivot is on the floor at the object's footprint centre; the
placement script rotates the whole assembly to face each gate. OBJ files are written for the
legacy Unreal OBJ importer adapter proven on this project (Y reflected, triangle winding
reversed; the importer reflects Y back) -- the same adapter as create_keilim_ti_v1.py and
create_oldcity_facades.py, recorded in
SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json.
"""
import hashlib
import json
import math
import os
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/security-review/GateSecurityV1'
SIGNS = ROOT / 'SourceAssets/security-review/signs'
DEST = '/Game/MikdashV3/MaterialReview/GateSecurityV1'

TRIANGLE_BUDGET = 60000
FONT_DIR = Path(r'C:\Windows\Fonts')

# The one measurement that is not arbitrary: the project's amah, so the checkpoint can be
# reported in the same units as everything else in the map.
AMAH = 50.0


# =====================================================================================
# 1. TrueType reader (glyf/loca outlines, cmap 4 and 12, composite glyphs)
# =====================================================================================
class TrueType(object):
    def __init__(self, path):
        self.path = str(path)
        self.d = Path(path).read_bytes()
        d = self.d
        num = struct.unpack('>H', d[4:6])[0]
        self.tab = {}
        for i in range(num):
            tag, _cs, off, ln = struct.unpack('>4sIII', d[12 + 16 * i:28 + 16 * i])
            self.tab[tag.decode('latin1')] = (off, ln)
        for required in ('head', 'maxp', 'hhea', 'hmtx', 'loca', 'glyf', 'cmap'):
            assert required in self.tab, '%s has no %s table' % (path, required)
        ho = self.tab['head'][0]
        self.units = struct.unpack('>H', d[ho + 18:ho + 20])[0]
        self.index_to_loc = struct.unpack('>h', d[ho + 50:ho + 52])[0]
        mo = self.tab['maxp'][0]
        self.num_glyphs = struct.unpack('>H', d[mo + 4:mo + 6])[0]
        ao = self.tab['hhea'][0]
        self.ascent = struct.unpack('>h', d[ao + 4:ao + 6])[0]
        self.descent = struct.unpack('>h', d[ao + 6:ao + 8])[0]
        self.num_hmetrics = struct.unpack('>H', d[ao + 34:ao + 36])[0]
        n = self.num_glyphs + 1
        lo, _ln = self.tab['loca']
        if self.index_to_loc == 0:
            self.loca = [2 * x for x in struct.unpack('>%dH' % n, d[lo:lo + 2 * n])]
        else:
            self.loca = list(struct.unpack('>%dI' % n, d[lo:lo + 4 * n]))
        self._read_cmap()
        self._cache = {}

    def _read_cmap(self):
        d = self.d
        off = self.tab['cmap'][0]
        n = struct.unpack('>H', d[off + 2:off + 4])[0]
        sub4 = sub12 = None
        for i in range(n):
            pid, eid, so = struct.unpack('>HHI', d[off + 4 + 8 * i:off + 12 + 8 * i])
            base = off + so
            fmt = struct.unpack('>H', d[base:base + 2])[0]
            if fmt == 4 and (pid, eid) in ((3, 1), (0, 3), (0, 4)):
                sub4 = base
            elif fmt == 12 and (pid, eid) in ((3, 10), (0, 4), (0, 6)):
                sub12 = base
        self.cmap12 = self.cmap4 = None
        if sub12 is not None:
            groups = struct.unpack('>I', d[sub12 + 12:sub12 + 16])[0]
            self.cmap12 = [struct.unpack('>3I', d[sub12 + 16 + 12 * g:sub12 + 28 + 12 * g]) for g in range(groups)]
        if sub4 is not None:
            segx2 = struct.unpack('>H', d[sub4 + 6:sub4 + 8])[0]
            seg = segx2 // 2
            ends = struct.unpack('>%dH' % seg, d[sub4 + 14:sub4 + 14 + segx2])
            sp = sub4 + 16 + segx2
            starts = struct.unpack('>%dH' % seg, d[sp:sp + segx2])
            dp = sp + segx2
            deltas = struct.unpack('>%dh' % seg, d[dp:dp + segx2])
            rp = dp + segx2
            ranges = struct.unpack('>%dH' % seg, d[rp:rp + segx2])
            self.cmap4 = (seg, ends, starts, deltas, ranges, rp)
        assert self.cmap4 or self.cmap12, 'no usable cmap subtable in ' + self.path

    def gid(self, cp):
        if self.cmap12:
            for s, e, g in self.cmap12:
                if s <= cp <= e:
                    return g + (cp - s)
        if self.cmap4 and cp <= 0xffff:
            seg, ends, starts, deltas, ranges, rp = self.cmap4
            for i in range(seg):
                if ends[i] >= cp and starts[i] <= cp:
                    ro = ranges[i]
                    if ro == 0:
                        return (cp + deltas[i]) & 0xffff
                    addr = rp + i * 2 + ro + (cp - starts[i]) * 2
                    g = struct.unpack('>H', self.d[addr:addr + 2])[0]
                    return 0 if g == 0 else (g + deltas[i]) & 0xffff
        return 0

    def advance(self, gid):
        off = self.tab['hmtx'][0]
        i = min(gid, self.num_hmetrics - 1)
        return struct.unpack('>H', self.d[off + 4 * i:off + 4 * i + 2])[0]

    def contours(self, gid, depth=0):
        if gid in self._cache:
            return self._cache[gid]
        go = self.tab['glyf'][0]
        s, e = self.loca[gid], self.loca[gid + 1]
        if s >= e:
            self._cache[gid] = []
            return []
        d = self.d
        b = go + s
        nc = struct.unpack('>h', d[b:b + 2])[0]
        if nc < 0:
            out = [] if depth > 4 else self._composite(b + 10, depth)
            self._cache[gid] = out
            return out
        ends = struct.unpack('>%dH' % nc, d[b + 10:b + 10 + 2 * nc])
        p = b + 10 + 2 * nc
        p += 2 + struct.unpack('>H', d[p:p + 2])[0]
        npt = ends[-1] + 1
        flags = []
        while len(flags) < npt:
            f = d[p]
            p += 1
            flags.append(f)
            if f & 8:
                r = d[p]
                p += 1
                flags.extend([f] * r)
        flags = flags[:npt]
        xs, v = [], 0
        for f in flags:
            if f & 2:
                dx = d[p]
                p += 1
                v += dx if (f & 16) else -dx
            elif not (f & 16):
                v += struct.unpack('>h', d[p:p + 2])[0]
                p += 2
            xs.append(v)
        ys, v = [], 0
        for f in flags:
            if f & 4:
                dy = d[p]
                p += 1
                v += dy if (f & 32) else -dy
            elif not (f & 32):
                v += struct.unpack('>h', d[p:p + 2])[0]
                p += 2
            ys.append(v)
        out, st = [], 0
        for en in ends:
            out.append([(xs[i], ys[i], bool(flags[i] & 1)) for i in range(st, en + 1)])
            st = en + 1
        self._cache[gid] = out
        return out

    def _composite(self, p, depth):
        d = self.d
        out = []
        while True:
            flags, glyph_index = struct.unpack('>HH', d[p:p + 4])
            p += 4
            if flags & 1:
                a1, a2 = struct.unpack('>hh', d[p:p + 4])
                p += 4
            else:
                a1, a2 = struct.unpack('>bb', d[p:p + 2])
                p += 2
            sx = sy = 1.0
            s01 = s10 = 0.0
            if flags & 8:
                sx = sy = struct.unpack('>h', d[p:p + 2])[0] / 16384.0
                p += 2
            elif flags & 0x40:
                sx, sy = [x / 16384.0 for x in struct.unpack('>hh', d[p:p + 4])]
                p += 4
            elif flags & 0x80:
                sx, s01, s10, sy = [x / 16384.0 for x in struct.unpack('>4h', d[p:p + 8])]
                p += 8
            dx, dy = (a1, a2) if (flags & 2) else (0, 0)
            for c in self.contours(glyph_index, depth + 1):
                out.append([(x * sx + y * s10 + dx, x * s01 + y * sy + dy, on) for x, y, on in c])
            if not (flags & 0x20):
                break
        return out


def flatten_glyph(contours, steps=8):
    """Quadratic-bezier TrueType contours -> closed polylines."""
    polys = []
    for c in contours:
        if len(c) < 2:
            continue
        pts = list(c)
        start = next((i for i, p in enumerate(pts) if p[2]), None)
        if start is None:
            pts = [((pts[0][0] + pts[-1][0]) / 2.0, (pts[0][1] + pts[-1][1]) / 2.0, True)] + pts
            start = 0
        pts = pts[start:] + pts[:start]
        pts.append(pts[0])
        poly = [(pts[0][0], pts[0][1])]
        cur = (pts[0][0], pts[0][1])
        i = 1
        while i < len(pts):
            x, y, on = pts[i]
            if on:
                poly.append((x, y))
                cur = (x, y)
                i += 1
                continue
            ctrl = (x, y)
            if i + 1 < len(pts):
                nx, ny, non = pts[i + 1]
                end = (nx, ny) if non else ((ctrl[0] + nx) / 2.0, (ctrl[1] + ny) / 2.0)
                i += 2 if non else 1
            else:
                end = poly[0]
                i += 1
            for s in range(1, steps + 1):
                t = s / float(steps)
                u = 1.0 - t
                poly.append((u * u * cur[0] + 2 * u * t * ctrl[0] + t * t * end[0],
                             u * u * cur[1] + 2 * u * t * ctrl[1] + t * t * end[1]))
            cur = end
        polys.append(poly)
    return polys


# ---------------------------------------------------------------------------
# Arabic contextual shaping. Hebrew needs none (no joining forms); Arabic does.
# value = (isolated, final, initial, medial); None where the form does not exist,
# which is exactly what marks a right-joining letter.
# ---------------------------------------------------------------------------
ARABIC_FORMS = {
    0x0621: (0xFE80, None, None, None), 0x0622: (0xFE81, 0xFE82, None, None),
    0x0623: (0xFE83, 0xFE84, None, None), 0x0624: (0xFE85, 0xFE86, None, None),
    0x0625: (0xFE87, 0xFE88, None, None), 0x0626: (0xFE89, 0xFE8A, 0xFE8B, 0xFE8C),
    0x0627: (0xFE8D, 0xFE8E, None, None), 0x0628: (0xFE8F, 0xFE90, 0xFE91, 0xFE92),
    0x0629: (0xFE93, 0xFE94, None, None), 0x062A: (0xFE95, 0xFE96, 0xFE97, 0xFE98),
    0x062B: (0xFE99, 0xFE9A, 0xFE9B, 0xFE9C), 0x062C: (0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0),
    0x062D: (0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4), 0x062E: (0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8),
    0x062F: (0xFEA9, 0xFEAA, None, None), 0x0630: (0xFEAB, 0xFEAC, None, None),
    0x0631: (0xFEAD, 0xFEAE, None, None), 0x0632: (0xFEAF, 0xFEB0, None, None),
    0x0633: (0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4), 0x0634: (0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8),
    0x0635: (0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC), 0x0636: (0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0),
    0x0637: (0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4), 0x0638: (0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8),
    0x0639: (0xFEC9, 0xFECA, 0xFECB, 0xFECC), 0x063A: (0xFECD, 0xFECE, 0xFECF, 0xFED0),
    0x0641: (0xFED1, 0xFED2, 0xFED3, 0xFED4), 0x0642: (0xFED5, 0xFED6, 0xFED7, 0xFED8),
    0x0643: (0xFED9, 0xFEDA, 0xFEDB, 0xFEDC), 0x0644: (0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0),
    0x0645: (0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4), 0x0646: (0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8),
    0x0647: (0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC), 0x0648: (0xFEED, 0xFEEE, None, None),
    0x0649: (0xFEEF, 0xFEF0, None, None), 0x064A: (0xFEF1, 0xFEF2, 0xFEF3, 0xFEF4),
}
ARABIC_LAM_ALEF = {0x0622: (0xFEF5, 0xFEF6), 0x0623: (0xFEF7, 0xFEF8),
                   0x0625: (0xFEF9, 0xFEFA), 0x0627: (0xFEFB, 0xFEFC)}
ARABIC_TRANSPARENT = set(range(0x064B, 0x0660)) | {0x0670, 0x0653, 0x0654, 0x0655}


def shape_arabic(text):
    """Logical Arabic text -> presentation-form codepoints, still in LOGICAL order."""
    src = [ord(c) for c in text if ord(c) not in ARABIC_TRANSPARENT]
    items = []
    i = 0
    while i < len(src):
        cp = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else None
        if cp == 0x0644 and nxt in ARABIC_LAM_ALEF:
            items.append(('LA', ARABIC_LAM_ALEF[nxt]))
            i += 2
            continue
        items.append(('CH', cp))
        i += 1
    out = []
    for k, (kind, val) in enumerate(items):
        prev = items[k - 1] if k > 0 else None
        nxt = items[k + 1] if k + 1 < len(items) else None
        prev_joins = False
        if prev and prev[0] == 'CH':
            f = ARABIC_FORMS.get(prev[1])
            prev_joins = bool(f and f[2])          # the previous letter has an initial form
        next_joins = False
        if nxt:
            if nxt[0] == 'LA':
                next_joins = True                  # the lam of the ligature joins backwards
            else:
                f = ARABIC_FORMS.get(nxt[1])
                next_joins = bool(f and f[1])      # the next letter has a final form
        if kind == 'LA':
            out.append(val[1] if prev_joins else val[0])
            continue
        f = ARABIC_FORMS.get(val)
        if not f:
            out.append(val)
            continue
        iso, fin, ini, med = f
        if prev_joins and next_joins and med:
            out.append(med)
        elif prev_joins and fin:
            out.append(fin)
        elif next_joins and ini:
            out.append(ini)
        else:
            out.append(iso)
    return out


# =====================================================================================
# 2. Canvas, PNG, and the scanline filler shared by glyphs and pictograms
# =====================================================================================
def fill_polys(polys, put, ss=4):
    """Non-zero-winding scanline fill with ss x ss supersampling. put(px, py, coverage)."""
    edges = []
    for poly in polys:
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            if y0 != y1:
                edges.append((x0, y0, x1, y1))
    if not edges:
        return
    ymin = min(min(e[1], e[3]) for e in edges)
    ymax = max(max(e[1], e[3]) for e in edges)
    cov = {}
    inc = 1.0 / (ss * ss)
    for sy in range(int(math.floor(ymin * ss)), int(math.ceil(ymax * ss)) + 1):
        y = (sy + 0.5) / ss
        xs = []
        for x0, y0, x1, y1 in edges:
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append((x0 + t * (x1 - x0), 1 if y1 > y0 else -1))
        if not xs:
            continue
        xs.sort()
        w = 0
        py = sy // ss
        for k in range(len(xs) - 1):
            w += xs[k][1]
            if w == 0:
                continue
            xa, xb = xs[k][0], xs[k + 1][0]
            for sx in range(int(math.floor(xa * ss)), int(math.ceil(xb * ss)) + 1):
                cx = (sx + 0.5) / ss
                if xa <= cx < xb:
                    key = (sx // ss, py)
                    cov[key] = cov.get(key, 0.0) + inc
    for (px, py), c in cov.items():
        put(px, py, min(1.0, c))


class Canvas(object):
    def __init__(self, w, h, bg=(255, 255, 255)):
        self.w, self.h = int(w), int(h)
        self.px = bytearray(bytes(bg) * (self.w * self.h))

    def blend(self, x, y, col, a):
        if a <= 0 or not (0 <= x < self.w and 0 <= y < self.h):
            return
        i = (y * self.w + x) * 3
        if a >= 1.0:
            self.px[i:i + 3] = bytes(col)
            return
        for k in range(3):
            self.px[i + k] = int(self.px[i + k] * (1.0 - a) + col[k] * a + 0.5)

    def sample(self, u, v):
        x = min(self.w - 1, max(0, int(u * self.w)))
        y = min(self.h - 1, max(0, int(v * self.h)))
        i = (y * self.w + x) * 3
        return (self.px[i], self.px[i + 1], self.px[i + 2])

    def fill(self, polys, col, alpha=1.0, ss=4):
        fill_polys(polys, lambda x, y, a: self.blend(x, y, col, a * alpha), ss)

    def rect(self, x0, y0, x1, y1, col, alpha=1.0):
        self.fill([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]], col, alpha)

    def round_rect(self, x0, y0, x1, y1, r, col, alpha=1.0, seg=8):
        r = min(r, (x1 - x0) / 2.0, (y1 - y0) / 2.0)
        pts = []
        for cx, cy, a0 in ((x1 - r, y1 - r, 0.0), (x0 + r, y1 - r, 90.0),
                           (x0 + r, y0 + r, 180.0), (x1 - r, y0 + r, 270.0)):
            for s in range(seg + 1):
                a = math.radians(a0 + 90.0 * s / seg)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.fill([pts], col, alpha)

    def disc(self, cx, cy, r, col, alpha=1.0, seg=48):
        self.fill([[(cx + r * math.cos(i * math.tau / seg), cy + r * math.sin(i * math.tau / seg))
                    for i in range(seg)]], col, alpha)

    def ring(self, cx, cy, r_out, r_in, col, alpha=1.0, seg=64):
        outer = [(cx + r_out * math.cos(i * math.tau / seg), cy + r_out * math.sin(i * math.tau / seg)) for i in range(seg)]
        inner = [(cx + r_in * math.cos(-i * math.tau / seg), cy + r_in * math.sin(-i * math.tau / seg)) for i in range(seg)]
        self.fill([outer, inner], col, alpha)

    def bar(self, x0, y0, x1, y1, width, col, alpha=1.0):
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / n * width / 2.0, dx / n * width / 2.0
        self.fill([[(x0 + ox, y0 + oy), (x1 + ox, y1 + oy), (x1 - ox, y1 - oy), (x0 - ox, y0 - oy)]], col, alpha)

    def png(self, path):
        def chunk(kind, data):
            return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
        scan = b''.join(b'\x00' + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3]) for y in range(self.h))
        Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'
                               + chunk(b'IHDR', struct.pack('!2I5B', self.w, self.h, 8, 2, 0, 0, 0))
                               + chunk(b'IDAT', zlib.compress(scan, 9)) + chunk(b'IEND', b''))
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# =====================================================================================
# 3. Text layout
# =====================================================================================
FONTS = {}


def font(name):
    if name not in FONTS:
        FONTS[name] = TrueType(FONT_DIR / name)
    return FONTS[name]


def layout(fnt, text, rtl=False, arabic=False):
    """logical text -> [(gid, advance_units, codepoint)] in VISUAL left-to-right order."""
    cps = shape_arabic(text) if arabic else [ord(c) for c in text]
    seq = [(fnt.gid(c), fnt.advance(fnt.gid(c)), c) for c in cps]
    return list(reversed(seq)) if rtl else seq


def text_width(fnt, text, size, rtl=False, arabic=False):
    return sum(a for _g, a, _c in layout(fnt, text, rtl, arabic)) * size / float(fnt.units)


def draw_text(cv, fnt, text, size, x, y, col=(0, 0, 0), rtl=False, arabic=False,
              anchor='center', max_width=None, ss=4):
    """Baseline at y. anchor is left / center / right in PAGE space. Returns (width, ink)."""
    seq = layout(fnt, text, rtl, arabic)
    s = size / float(fnt.units)
    total = sum(a for _g, a, _c in seq) * s
    if max_width and total > max_width:
        s *= max_width / total
        total = max_width
    pen = x - total / 2.0 if anchor == 'center' else (x - total if anchor == 'right' else x)
    ink = []
    for gid, adv, cp in seq:
        polys = flatten_glyph(fnt.contours(gid))
        if polys:
            tp = [[(pen + px * s, y - py * s) for px, py in p] for p in polys]
            xs = [q[0] for p in tp for q in p]
            ys = [q[1] for p in tp for q in p]
            ink.append(dict(cp=cp, gid=gid, x0=round(min(xs), 2), x1=round(max(xs), 2),
                            y0=round(min(ys), 2), y1=round(max(ys), 2)))
        elif cp != 0x20:
            ink.append(dict(cp=cp, gid=gid, x0=None, x1=None, y0=None, y1=None))
        fill_polys([[(pen + px * s, y - py * s) for px, py in p] for p in polys],
                   lambda px, py, a: cv.blend(px, py, col, a), ss)
        pen += adv * s
    return total, ink


# =====================================================================================
# 4. Pictograms. At the distance a sign is actually read these carry the message; the
#    text is the confirmation. All drawn as filled paths, no external art.
# =====================================================================================
RED = (196, 28, 28)
INK = (20, 22, 26)
WHITE = (255, 255, 255)


def _shoe(cv, cx, cy, s, col):
    """Side view of a shoe, toe to the left."""
    p = [(-1.00, 0.10), (-0.86, 0.32), (-0.60, 0.42), (-0.30, 0.44), (-0.08, 0.52),
         (0.18, 0.72), (0.42, 0.86), (0.62, 0.88), (0.72, 0.74), (0.74, 0.30),
         (0.80, 0.02), (0.86, -0.22), (0.80, -0.38), (0.30, -0.42), (-0.55, -0.42),
         (-0.92, -0.30), (-1.02, -0.10)]
    cv.fill([[(cx + x * s, cy - y * s) for x, y in p]], col)
    cv.fill([[(cx + x * s, cy - y * s) for x, y in
              [(-1.02, -0.42), (0.86, -0.42), (0.86, -0.60), (-0.98, -0.60)]]], col)   # sole
    cv.fill([[(cx + x * s, cy - y * s) for x, y in
              [(-0.05, 0.50), (0.34, 0.80), (0.30, 0.60), (-0.02, 0.38)]]], WHITE)     # laces gap


def _phone(cv, cx, cy, s, col):
    cv.round_rect(cx - 0.42 * s, cy - 0.82 * s, cx + 0.42 * s, cy + 0.82 * s, 0.12 * s, col)
    cv.round_rect(cx - 0.32 * s, cy - 0.62 * s, cx + 0.32 * s, cy + 0.58 * s, 0.04 * s, WHITE)
    cv.round_rect(cx - 0.12 * s, cy - 0.75 * s, cx + 0.12 * s, cy - 0.68 * s, 0.03 * s, WHITE)
    cv.disc(cx, cy + 0.70 * s, 0.07 * s, WHITE)


def _bag(cv, cx, cy, s, col):
    cv.round_rect(cx - 0.72 * s, cy - 0.22 * s, cx + 0.72 * s, cy + 0.70 * s, 0.10 * s, col)
    cv.ring(cx, cy - 0.24 * s, 0.34 * s, 0.24 * s, col)                    # handle
    cv.rect(cx - 0.40 * s, cy - 0.24 * s, cx + 0.40 * s, cy + 0.10 * s, col)
    cv.rect(cx - 0.72 * s, cy + 0.10 * s, cx + 0.72 * s, cy + 0.20 * s, WHITE)   # zip line


def _spit(cv, cx, cy, s, col):
    """A head in profile with three droplets leaving the mouth."""
    cv.disc(cx - 0.10 * s, cy - 0.10 * s, 0.52 * s, col)
    cv.fill([[(cx + x * s, cy - y * s) for x, y in
              [(0.34, 0.16), (0.60, 0.06), (0.60, -0.10), (0.34, -0.06)]]], col)   # nose
    cv.fill([[(cx + x * s, cy - y * s) for x, y in
              [(0.30, -0.22), (0.56, -0.24), (0.56, -0.34), (0.30, -0.34)]]], WHITE)  # mouth
    for k, (dx, dy, r) in enumerate(((0.78, -0.30, 0.10), (1.02, -0.38, 0.075), (1.22, -0.48, 0.055))):
        cv.disc(cx + dx * s, cy - dy * s, r * s, col)


def _shortcut(cv, cx, cy, s, col):
    """A straight arrow cutting through a bounded area: the kappandaria pictogram."""
    cv.ring(cx, cy, 0.78 * s, 0.62 * s, col, seg=4)                        # a square boundary
    cv.bar(cx - 0.95 * s, cy + 0.55 * s, cx + 0.80 * s, cy - 0.55 * s, 0.20 * s, col)
    head = [(0.98, 0.68), (0.52, 0.62), (0.72, 0.20)]
    cv.fill([[(cx + x * s, cy - y * s) for x, y in head]], col)


def _arch(cv, cx, cy, s, col):
    """A walk-through detector arch with a figure in it."""
    cv.rect(cx - 0.78 * s, cy - 0.80 * s, cx - 0.52 * s, cy + 0.85 * s, col)
    cv.rect(cx + 0.52 * s, cy - 0.80 * s, cx + 0.78 * s, cy + 0.85 * s, col)
    cv.rect(cx - 0.86 * s, cy - 1.00 * s, cx + 0.86 * s, cy - 0.80 * s, col)
    cv.disc(cx, cy - 0.34 * s, 0.16 * s, col)
    cv.round_rect(cx - 0.17 * s, cy - 0.16 * s, cx + 0.17 * s, cy + 0.50 * s, 0.10 * s, col)
    cv.rect(cx - 0.15 * s, cy + 0.50 * s, cx - 0.03 * s, cy + 0.85 * s, col)
    cv.rect(cx + 0.03 * s, cy + 0.50 * s, cx + 0.15 * s, cy + 0.85 * s, col)


def _camera(cv, cx, cy, s, col):
    cv.round_rect(cx - 0.80 * s, cy - 0.42 * s, cx + 0.80 * s, cy + 0.52 * s, 0.12 * s, col)
    cv.fill([[(cx + x * s, cy - y * s) for x, y in
              [(-0.42, 0.42), (-0.24, 0.64), (0.12, 0.64), (0.30, 0.42)]]], col)
    cv.ring(cx + 0.02 * s, cy + 0.05 * s, 0.34 * s, 0.20 * s, WHITE)


def _arrow(cv, cx, cy, s, col, direction=1.0):
    cv.bar(cx - direction * 0.70 * s, cy, cx + direction * 0.28 * s, cy, 0.34 * s, col)
    cv.fill([[(cx + direction * 0.86 * s, cy), (cx + direction * 0.22 * s, cy - 0.60 * s),
              (cx + direction * 0.22 * s, cy + 0.60 * s)]], col)


def _sock(cv, cx, cy, s, col):
    """A stockinged foot: what the shoe sign asks for, drawn as the permitted state."""
    p = [(-0.98, -0.18), (-0.86, 0.04), (-0.52, 0.16), (-0.20, 0.18), (0.06, 0.34),
         (0.28, 0.66), (0.46, 0.88), (0.66, 0.88), (0.74, 0.68), (0.72, 0.10),
         (0.78, -0.24), (0.62, -0.42), (-0.60, -0.42), (-0.96, -0.34)]
    cv.fill([[(cx + x * s, cy - y * s) for x, y in p]], col)
    for k in range(3):
        yy = cy - (0.62 - 0.16 * k) * s
        cv.bar(cx + 0.30 * s, yy, cx + 0.74 * s, yy - 0.06 * s, 0.055 * s, WHITE)


def prohibit(cv, cx, cy, s, thickness=0.16):
    """The red circle and bar, drawn OVER a pictogram."""
    cv.ring(cx, cy, s, s * (1.0 - thickness), RED, seg=96)
    cv.bar(cx - s * 0.72, cy + s * 0.72, cx + s * 0.72, cy - s * 0.72, s * thickness * 2.0, RED)


def permit(cv, cx, cy, s):
    """A green circle: the permitted counterpart of prohibit()."""
    cv.ring(cx, cy, s, s * 0.84, (26, 132, 62), seg=96)


# =====================================================================================
# 5. The signs themselves
# =====================================================================================
HE = font('arialbd.ttf')       # Arial Bold carries all of Hebrew and all Arabic form blocks
EN = font('arialbd.ttf')
AR = font('arialbd.ttf')
SMALL = font('arial.ttf')

# Hebrew source strings, as unicode escapes so no editor or transfer can mangle them.
H_REMOVE_SHOES = u'\u05d4\u05e1\u05e8 \u05e0\u05e2\u05dc\u05d9\u05da'
H_NO_SHOES = u'\u05d0\u05e1\u05d5\u05e8 \u05dc\u05d4\u05d9\u05db\u05e0\u05e1 \u05d1\u05e0\u05e2\u05dc\u05d9\u05d9\u05dd'
H_NO_PHONE = u'\u05d0\u05d9\u05df \u05dc\u05d4\u05e9\u05ea\u05de\u05e9 \u05d1\u05d8\u05dc\u05e4\u05d5\u05df'
H_HOLY_AREA = u'\u05d0\u05d6\u05d5\u05e8 \u05e7\u05d3\u05d5\u05e9'
H_NO_SHORTCUT = u'\u05d0\u05d9\u05df \u05dc\u05e2\u05e9\u05d5\u05ea\u05d5 \u05e7\u05e4\u05e0\u05d3\u05e8\u05d9\u05d0'
H_NO_SPIT = u'\u05d5\u05dc\u05d0 \u05d9\u05e8\u05d5\u05e7 \u05d1\u05d5'
H_BAGS = u'\u05d4\u05ea\u05d9\u05e7\u05d9\u05dd \u05e0\u05d1\u05d3\u05e7\u05d9\u05dd'
H_ENTRANCE = u'\u05db\u05e0\u05d9\u05e1\u05d4'
H_SECURITY = u'\u05d1\u05d9\u05e7\u05d5\u05e8\u05ea \u05d1\u05d9\u05d8\u05d7\u05d5\u05df'

A_REMOVE_SHOES = u'\u0627\u062e\u0644\u0639 \u062d\u0630\u0627\u0621\u0643'
A_NO_SHOES = u'\u0645\u0645\u0646\u0648\u0639 \u0627\u0644\u062f\u062e\u0648\u0644 \u0628\u0627\u0644\u0623\u062d\u0630\u064a\u0629'
A_NO_PHONE = u'\u0645\u0645\u0646\u0648\u0639 \u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0627\u0644\u0647\u0627\u062a\u0641'
A_HOLY_AREA = u'\u0645\u0646\u0637\u0642\u0629 \u0645\u0642\u062f\u0633\u0629'
A_NO_SHORTCUT = u'\u0645\u0645\u0646\u0648\u0639 \u0627\u0644\u0645\u0631\u0648\u0631 \u0639\u0628\u0631 \u0627\u0644\u0645\u0648\u0642\u0639'
A_NO_SPIT = u'\u0645\u0645\u0646\u0648\u0639 \u0627\u0644\u0628\u0635\u0642'
A_BAGS = u'\u062a\u0641\u062a\u064a\u0634 \u0627\u0644\u062d\u0642\u0627\u0626\u0628'
A_ENTRANCE = u'\u0645\u062f\u062e\u0644'
A_SECURITY = u'\u0627\u0644\u062a\u0641\u062a\u064a\u0634 \u0627\u0644\u0623\u0645\u0646\u064a'

CREAM = (243, 240, 233)
BAND_HALACHA = (23, 58, 106)      # deep blue: the two rules that come from the sources
BAND_MODERN = (58, 62, 68)        # graphite: the modern security notices
BAND_WAY = (26, 106, 84)          # green: wayfinding


def _band(cv, y0, y1, col, title_he, title_en, title_ar):
    cv.rect(0, y0, cv.w, y1, col)
    h = y1 - y0
    # Three scripts stacked in one band collide unless the metrics are budgeted explicitly.
    # y is the BASELINE. Arial caps rise about 0.72 of the em and Arabic ascenders about 0.85,
    # while Hebrew final letters and Arabic tails drop about 0.24 below. These three baselines
    # and sizes are the ones that leave daylight between every pair and still clear the band.
    draw_text(cv, HE, title_he, h * 0.32, cv.w * 0.5, y0 + h * 0.330, WHITE, rtl=True, max_width=cv.w * 0.88)
    draw_text(cv, EN, title_en, h * 0.215, cv.w * 0.5, y0 + h * 0.605, WHITE, max_width=cv.w * 0.88)
    draw_text(cv, AR, title_ar, h * 0.225, cv.w * 0.5, y0 + h * 0.875, WHITE, rtl=True, arabic=True, max_width=cv.w * 0.88)


def _rule_row(cv, y, h, pictogram, he, en, ar, mark='prohibit'):
    """One rule: pictogram on the right (RTL reading order), three lines of text to its left."""
    s = h * 0.30
    cx = cv.w - h * 0.52
    cy = y + h * 0.50
    pictogram(cv, cx, cy, s, INK)
    if mark == 'prohibit':
        prohibit(cv, cx, cy, h * 0.40)
    elif mark == 'permit':
        permit(cv, cx, cy, h * 0.40)
    right = cv.w - h * 1.06
    width = right - cv.w * 0.045
    draw_text(cv, HE, he, h * 0.27, right, y + h * 0.34, INK, rtl=True, anchor='right', max_width=width)
    draw_text(cv, EN, en, h * 0.21, right, y + h * 0.63, INK, anchor='right', max_width=width)
    draw_text(cv, AR, ar, h * 0.24, right, y + h * 0.92, INK, rtl=True, arabic=True, anchor='right', max_width=width)


def _footer(cv, y, lines, col=(96, 100, 108)):
    for i, line in enumerate(lines):
        draw_text(cv, SMALL, line, cv.h * 0.019, cv.w * 0.5, y + i * cv.h * 0.026, col, max_width=cv.w * 0.92)


def sign_shoes(w=1024, h=1536):
    cv = Canvas(w, h, CREAM)
    _band(cv, 0, h * 0.145, BAND_HALACHA, H_NO_SHOES, 'ENTERING IN SHOES IS PROHIBITED', A_NO_SHOES)
    _rule_row(cv, h * 0.165, h * 0.235, _shoe, H_REMOVE_SHOES, 'REMOVE YOUR SHOES', A_REMOVE_SHOES)
    _rule_row(cv, h * 0.420, h * 0.235, _sock, u'\u05d1\u05d2\u05e8\u05d1\u05d9\u05d9\u05dd \u05d1\u05dc\u05d1\u05d3',
              'STOCKINGED FEET ONLY', u'\u0628\u0627\u0644\u062c\u0648\u0627\u0631\u0628 \u0641\u0642\u0637', mark='permit')
    cv.rect(w * 0.06, h * 0.685, w * 0.94, h * 0.690, (200, 196, 186))
    draw_text(cv, HE, H_HOLY_AREA, h * 0.062, w * 0.5, h * 0.775, BAND_HALACHA, rtl=True, max_width=w * 0.9)
    draw_text(cv, EN, 'HOLY AREA', h * 0.044, w * 0.5, h * 0.828, BAND_HALACHA, max_width=w * 0.9)
    draw_text(cv, AR, A_HOLY_AREA, h * 0.050, w * 0.5, h * 0.884, BAND_HALACHA, rtl=True, arabic=True, max_width=w * 0.9)
    _footer(cv, h * 0.935, ['Mishnah Berachos 9:5  |  Rambam, Hilchos Beis HaBechira 7:2',
                            'A rule of the place. Not a request.'])
    return cv


def sign_reverence(w=1024, h=1536):
    cv = Canvas(w, h, CREAM)
    _band(cv, 0, h * 0.145, BAND_HALACHA, H_HOLY_AREA, 'HOLY AREA', A_HOLY_AREA)
    _rule_row(cv, h * 0.180, h * 0.215, _shortcut, H_NO_SHORTCUT, 'NO SHORTCUT THROUGH THE MOUNT', A_NO_SHORTCUT)
    _rule_row(cv, h * 0.420, h * 0.215, _spit, H_NO_SPIT, 'NO SPITTING', A_NO_SPIT)
    _rule_row(cv, h * 0.660, h * 0.215, _shoe, H_NO_SHOES, 'NO SHOES BEYOND THIS POINT', A_NO_SHOES)
    _footer(cv, h * 0.930, ['Mishnah Berachos 9:5  |  Rambam, Hilchos Beis HaBechira 7:2',
                            'Three of the reverences of the Mount, stated as rules of the place.'])
    return cv


def sign_security(w=1024, h=1536):
    cv = Canvas(w, h, CREAM)
    _band(cv, 0, h * 0.145, BAND_MODERN, H_SECURITY, 'SECURITY CHECK', A_SECURITY)
    _rule_row(cv, h * 0.180, h * 0.215, _phone, H_NO_PHONE, 'NO TELEPHONE USE', A_NO_PHONE)
    _rule_row(cv, h * 0.420, h * 0.215, _bag, H_BAGS, 'ALL BAGS ARE SEARCHED', A_BAGS, mark='none')
    _rule_row(cv, h * 0.660, h * 0.215, _arch, u'\u05e2\u05d1\u05d5\u05e8 \u05d3\u05e8\u05da \u05d4\u05de\u05d2\u05dc\u05d4',
              'PASS THROUGH THE DETECTOR', u'\u0627\u0645\u0631\u0631 \u0639\u0628\u0631 \u0627\u0644\u062c\u0647\u0627\u0632', mark='none')
    _footer(cv, h * 0.930, ['Modern staging. Entrance procedure as at the Har HaBayit and Kotel plaza approaches today.',
                            'No classical source. Nothing on this notice is a claim about the Temple.'])
    return cv


def sign_entrance(w=1024, h=640):
    cv = Canvas(w, h, CREAM)
    _band(cv, 0, h * 0.30, BAND_WAY, H_ENTRANCE, 'ENTRANCE', A_ENTRANCE)
    # prohibit()/permit() take the ring OUTER RADIUS, so a ring is 2s wide. At the old
    # 0.155 h radius the rings were 198 px across on a 151 px pitch and every one of them
    # cut into its neighbour. Pitch must exceed 2 * ring radius, with a little daylight.
    _arrow(cv, w * 0.130, h * 0.63, h * 0.155, BAND_WAY, direction=1.0)
    ring_r = h * 0.112
    for i, (pg, mark) in enumerate(((_arch, 'none'), (_bag, 'none'), (_shoe, 'prohibit'),
                                    (_phone, 'prohibit'), (_camera, 'permit'))):
        cx = w * (0.315 + 0.152 * i)
        pg(cv, cx, h * 0.63, h * 0.098, INK)
        if mark == 'prohibit':
            prohibit(cv, cx, h * 0.63, ring_r)
        elif mark == 'permit':
            permit(cv, cx, h * 0.63, ring_r)
    _footer(cv, h * 0.925, ['Wayfinding plate. Pictograms carry the message; text confirms it.'], (110, 114, 120))
    return cv


SIGN_SET = {
    'Shoes':    dict(build=sign_shoes,    size=(1024, 1536), form='panel',
                     claim='halacha', role='sign_face',
                     says='Entering Har HaBayit in shoes is prohibited; stockinged feet only; holy area.'),
    'Reverence': dict(build=sign_reverence, size=(1024, 1536), form='panel',
                      claim='halacha', role='sign_face',
                      says='Holy area: no shortcut through the Mount, no spitting, no shoes.'),
    'Security': dict(build=sign_security, size=(1024, 1536), form='panel',
                     claim='modern-staging', role='sign_face',
                     says='No telephone use; all bags are searched; pass through the detector.'),
    'Entrance': dict(build=sign_entrance, size=(1024, 640), form='plate',
                     claim='modern-staging', role='sign_face',
                     says='Entrance this way; detector, bag search, no shoes, no phones, cameras permitted.'),
}


# =====================================================================================
# 6. The glyph check. This is the evidence that the text is real text and not mojibake.
# =====================================================================================
def verify_glyphs():
    """For every codepoint the signs use: does the font actually have a glyph, does that
    glyph have outline contours, and does a right-to-left run really lay out right to left?

    Returns a receipt and raises if any Hebrew or Arabic glyph is missing, so a font without
    Hebrew can never produce a shipped sign full of empty boxes."""
    hebrew = [H_REMOVE_SHOES, H_NO_SHOES, H_NO_PHONE, H_HOLY_AREA, H_NO_SHORTCUT, H_NO_SPIT,
              H_BAGS, H_ENTRANCE, H_SECURITY,
              u'\u05d1\u05d2\u05e8\u05d1\u05d9\u05d9\u05dd \u05d1\u05dc\u05d1\u05d3',
              u'\u05e2\u05d1\u05d5\u05e8 \u05d3\u05e8\u05da \u05d4\u05de\u05d2\u05dc\u05d4']
    arabic = [A_REMOVE_SHOES, A_NO_SHOES, A_NO_PHONE, A_HOLY_AREA, A_NO_SHORTCUT, A_NO_SPIT,
              A_BAGS, A_ENTRANCE, A_SECURITY,
              u'\u0628\u0627\u0644\u062c\u0648\u0627\u0631\u0628 \u0641\u0642\u0637',
              u'\u0627\u0645\u0631\u0631 \u0639\u0628\u0631 \u0627\u0644\u062c\u0647\u0627\u0632']
    rows = []
    missing = []
    empty = []
    for label, fnt in (('bold', HE), ('regular', SMALL)):
        for script, strings, arabic_flag in (('hebrew', hebrew, False), ('arabic', arabic, True)):
            seen = set()
            for text in strings:
                for cp in (shape_arabic(text) if arabic_flag else [ord(c) for c in text]):
                    if cp == 0x20 or cp in seen:
                        continue
                    seen.add(cp)
                    gid = fnt.gid(cp)
                    contours = len(fnt.contours(gid)) if gid else 0
                    rows.append(dict(font=os.path.basename(fnt.path), style=label, script=script,
                                     codepoint='U+%04X' % cp, glyphId=gid, contours=contours,
                                     advanceUnits=fnt.advance(gid) if gid else 0))
                    if gid == 0:
                        missing.append((os.path.basename(fnt.path), 'U+%04X' % cp))
                    elif contours == 0:
                        empty.append((os.path.basename(fnt.path), 'U+%04X' % cp))
    # ASCII must be present too, or the English lines are the mojibake.
    for cp in range(0x20, 0x7f):
        if HE.gid(cp) == 0:
            missing.append((os.path.basename(HE.path), 'U+%04X' % cp))

    # The direction test: lay out a Hebrew word and confirm that its FIRST logical letter
    # ends up as the RIGHTMOST ink on the page, and its last as the leftmost.
    probe = Canvas(600, 200, WHITE)
    _w, ink = draw_text(probe, HE, H_REMOVE_SHOES, 90, 300, 140, INK, rtl=True)
    placed = [row for row in ink if row['x0'] is not None]
    first_cp = ord(H_REMOVE_SHOES[0])
    last_cp = ord(H_REMOVE_SHOES[-1])
    first = next(r for r in placed if r['cp'] == first_cp)
    last = next(r for r in placed if r['cp'] == last_cp)
    first_centre = (first['x0'] + first['x1']) / 2.0
    last_centre = (last['x0'] + last['x1']) / 2.0
    rtl_ok = first_centre > last_centre
    rightmost = max(placed, key=lambda r: r['x1'])
    leftmost = min(placed, key=lambda r: r['x0'])

    # The Arabic shaping test: four known words whose forms are checked letter by letter.
    shaping = []
    for text, expect in (
            # akhla' -- alef isolated, khah initial, lam MEDIAL, ain final.
            (u'\u0627\u062e\u0644\u0639', [0xFE8D, 0xFEA7, 0xFEE0, 0xFECA]),
            # mintaqa -- meem/noon/tah initial-medial chain, qaf medial, teh marbuta final.
            (u'\u0645\u0646\u0637\u0642\u0629', [0xFEE3, 0xFEE8, 0xFEC4, 0xFED8, 0xFE94]),
            # al-ahdhiya -- SIX forms, not seven. The lam and the following alef-with-hamza
            # fuse into the single ligature U+FEF7, so no separate lam glyph is left to emit;
            # an earlier hand-written expectation here listed both and was wrong. The ligature
            # is isolated rather than final because the alef before it has no initial form and
            # so cannot join forward into it.
            (u'\u0627\u0644\u0623\u062d\u0630\u064a\u0629',
             [0xFE8D, 0xFEF7, 0xFEA3, 0xFEAC, 0xFEF3, 0xFE94]),
            # bila -- the other lam-alef branch: beh DOES join forward, so the plain lam-alef
            # ligature takes its FINAL form U+FEFC rather than the isolated U+FEFB.
            (u'\u0628\u0644\u0627', [0xFE91, 0xFEFC]),
            # maktab -- a fully connected four-letter run: initial, medial, medial, final.
            (u'\u0645\u0643\u062a\u0628', [0xFEE3, 0xFEDC, 0xFE98, 0xFE90])):
        got = shape_arabic(text)
        shaping.append(dict(text_codepoints=['U+%04X' % ord(c) for c in text],
                            shaped=['U+%04X' % c for c in got],
                            expected=['U+%04X' % c for c in expect],
                            matches=got == expect))

    receipt = dict(
        method=('Every codepoint the signs use is looked up in the font cmap, the glyph id is '
                'recorded, and the glyph outline is read out of the glyf table and counted. A '
                'glyph id of 0 is .notdef -- the empty box -- and a glyph with zero contours '
                'would print as blank. Both are refusals, not warnings.'),
        fontDirectory=str(FONT_DIR),
        fonts=[dict(file=os.path.basename(f.path), unitsPerEm=f.units, glyphCount=f.num_glyphs)
               for f in (HE, SMALL)],
        fontChoice=('Arial Bold. Checked against Segoe UI, David, Frank Ruehl, Times New Roman and '
                    'Tahoma: David and Frank Ruehl carry Hebrew but are missing 29 of the Arabic '
                    'presentation forms these signs need, so they were rejected. Arial, Segoe UI, '
                    'Times and Tahoma all pass; Arial Bold was taken for weight at distance.'),
        glyphs=rows,
        missingGlyphs=['%s %s' % m for m in missing],
        emptyGlyphs=['%s %s' % e for e in empty],
        rightToLeft=dict(
            probeString='+'.join('U+%04X' % ord(c) for c in H_REMOVE_SHOES),
            firstLogicalLetter='U+%04X' % first_cp, firstLetterCentrePx=round(first_centre, 2),
            lastLogicalLetter='U+%04X' % last_cp, lastLetterCentrePx=round(last_centre, 2),
            rightmostInkIsFirstLetter=rightmost['cp'] == first_cp,
            leftmostInkIsLastLetter=leftmost['cp'] == last_cp,
            pass_=rtl_ok,
            note=('A Hebrew run is laid out by reversing the glyph order, which is correct because '
                  'Hebrew needs no contextual shaping. The check is that the first letter of the '
                  'logical string is drawn furthest RIGHT on the page.')),
        arabicShaping=dict(
            method=('Arabic is shaped into the Unicode presentation forms of block FE70..FEFF by a '
                    'joining table in this file, then reversed like Hebrew. Five words are checked '
                    'form by form against hand-verified expected output.'),
            cases=shaping,
            allMatch=all(c['matches'] for c in shaping)),
    )
    assert not missing, 'font is missing glyphs, refusing to ship mojibake: %s' % missing[:12]
    assert not empty, 'font has empty glyphs for: %s' % empty[:12]
    assert rtl_ok, 'right-to-left layout failed the direction probe'
    assert receipt['arabicShaping']['allMatch'], 'Arabic contextual shaping produced the wrong forms'
    return receipt


# =====================================================================================
# 7. Geometry primitives (the create_keilim_ti_v1 / create_oldcity_facades set)
# =====================================================================================
def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def volume(v, f):
    t = 0.0
    for a, b, c in f:
        p, q, r = v[a], v[b], v[c]
        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
        t += sum(p[i] * n[i] for i in range(3))
    return t / 6.0


def orient(v, f):
    return (v, f) if volume(v, f) > 0 else (v, [(a, c, b) for a, b, c in f])


def closed(v, f):
    keys = [tuple(round(x, 6) for x in p) for p in v]
    e = {}
    for a, b, c in f:
        for i, j in ((a, b), (b, c), (c, a)):
            k = tuple(sorted((keys[i], keys[j])))
            e[k] = e.get(k, 0) + 1
    return all(n == 2 for n in e.values())


def consistently_oriented(v, f):
    """Every DIRECTED edge appears exactly once, so the two faces sharing an edge traverse it
    in opposite directions -- the actual definition of a coherently oriented surface.

    closed() cannot do this job: it counts undirected edges, so a face group whose winding is
    reversed still passes it. That is not hypothetical -- loft() shipped both of its end caps
    inverted and closed() reported the solid closed, orient() reported it positive, and the
    volume was silently a third of the truth. This is the check that catches it."""
    keys = [tuple(round(x, 6) for x in p) for p in v]
    directed = {}
    for a, b, c in f:
        for i, j in ((a, b), (b, c), (c, a)):
            key = (keys[i], keys[j])
            if key in directed:
                return False              # same directed edge twice: two faces wound alike
            directed[key] = True
    return all((b, a) in directed for a, b in directed)


def box(center, size):
    hx, hy, hz = [s / 2.0 for s in size]
    cx, cy, cz = center
    v = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    f = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
         (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return orient(v, f)


def slab(x0, x1, y0, y1, z0, z1):
    return box(((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0), (x1 - x0, y1 - y0, z1 - z0))


def prism(polygon, z0, z1):
    """Vertical prism over a simple polygon [(x, y), ...], star-shaped from vertex 0."""
    n = len(polygon)
    v = [(x, y, z0) for x, y in polygon] + [(x, y, z1) for x, y in polygon]
    f = []
    for i in range(n):
        j = (i + 1) % n
        f += [(i, j, n + j), (i, n + j, n + i)]
    for i in range(1, n - 1):
        f += [(0, i, i + 1), (n, n + i + 1, n + i)]
    return orient(v, f)


def frame_prism(outer, inner, x0, x1):
    """A rectangular annulus in the YZ plane extruded along X: a tunnel hood, a sign frame.
    outer / inner are (y0, y1, z0, z1). Closed, genus 1."""
    oy0, oy1, oz0, oz1 = outer
    iy0, iy1, iz0, iz1 = inner
    assert oy0 < iy0 < iy1 < oy1 and oz0 < iz0 < iz1 < oz1, 'inner rectangle must sit inside the outer'
    ring_o = [(oy0, oz0), (oy1, oz0), (oy1, oz1), (oy0, oz1)]
    ring_i = [(iy0, iz0), (iy1, iz0), (iy1, iz1), (iy0, iz1)]
    v = []
    for x in (x0, x1):
        v += [(x, y, z) for y, z in ring_o]
        v += [(x, y, z) for y, z in ring_i]
    f = []
    for base, flip in ((0, False), (8, True)):
        for i in range(4):                                  # outer wall
            j = (i + 1) % 4
            a, b = base + i, base + j
            c, d = base + 4 + j, base + 4 + i
            f += [(a, b, c), (a, c, d)] if not flip else [(a, c, b), (a, d, c)]
    for i in range(4):                                      # outer skin, front to back
        j = (i + 1) % 4
        f += [(i, 8 + i, 8 + j), (i, 8 + j, j)]
    for i in range(4):                                      # inner skin (the bore)
        j = (i + 1) % 4
        f += [(4 + i, 12 + j, 12 + i), (4 + i, 4 + j, 12 + j)]
    return orient(v, f)


def revolve(profile, center, segments=20):
    """profile = [(r, z)] starting and ending at r == 0."""
    assert profile[0][0] == 0 and profile[-1][0] == 0
    cx, cy, cz = center
    v = [(cx, cy, cz + profile[0][1])]
    rings = []
    for r, z in profile[1:-1]:
        rings.append(len(v))
        for i in range(segments):
            a = i * math.tau / segments
            v.append((cx + r * math.cos(a), cy + r * math.sin(a), cz + z))
    top = len(v)
    v.append((cx, cy, cz + profile[-1][1]))
    f = []
    for i in range(segments):
        j = (i + 1) % segments
        f.append((0, rings[0] + j, rings[0] + i))
        f.append((top, rings[-1] + i, rings[-1] + j))
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            f += [(r0 + i, r0 + j, r1 + j), (r0 + i, r1 + j, r1 + i)]
    return orient(v, f)


def cylinder(center, radius, height, segments=16, axis='z'):
    prof = [(0.0, 0.0), (radius, 0.0), (radius, height), (0.0, height)]
    v, f = revolve(prof, (0.0, 0.0, 0.0), segments)
    cx, cy, cz = center
    if axis == 'z':
        v = [(x + cx, y + cy, z + cz) for x, y, z in v]
    elif axis == 'y':
        v = [(x + cx, z + cy, y + cz) for x, y, z in v]
    else:
        v = [(z + cx, x + cy, y + cz) for x, y, z in v]
    return orient(v, f)


def tube_along_y(center, r_out, r_in, y0, y1, segments=16):
    """A hollow tube running along Y: a conveyor roller, a stanchion collar.

    Four surfaces, and every one of them has to agree with its neighbours about which way is
    out: the outer skin (normal radially outward), the bore (normal radially INWARD, because
    the solid is the material between the radii), and the two annular end caps (-Y and +Y).
    An earlier version of this function shared the directed edge (i -> j) between the outer
    skin and the near cap, which means those two faces were wound the same way round rather
    than opposite; consistently_oriented() rejects that.

    Index convention below: A = outer at y0, B = bore at y0, C = outer at y1, D = bore at y1.
    """
    cx, cz = center
    n = segments
    ring = [(math.cos(k * math.tau / n), math.sin(k * math.tau / n)) for k in range(n)]
    v = []
    for radius, y in ((r_out, y0), (r_in, y0), (r_out, y1), (r_in, y1)):
        v += [(cx + radius * c, y, cz + radius * s_) for c, s_ in ring]
    f = []
    for i in range(n):
        j = (i + 1) % n
        a_i, a_j = i, j                       # outer, y0
        b_i, b_j = n + i, n + j               # bore,  y0
        c_i, c_j = 2 * n + i, 2 * n + j       # outer, y1
        d_i, d_j = 3 * n + i, 3 * n + j       # bore,  y1
        f += [(a_i, c_i, c_j), (a_i, c_j, a_j)]      # outer skin, normal outward
        f += [(a_i, a_j, b_j), (a_i, b_j, b_i)]      # cap at y0, normal -Y
        f += [(b_i, b_j, d_j), (b_i, d_j, d_i)]      # bore, normal towards the axis
        f += [(c_j, c_i, d_i), (c_j, d_i, d_j)]      # cap at y1, normal +Y
    return orient(v, f)


def loft(sections):
    """Loft closed rings of equal length: [(pts, z), ...] where pts = [(x, y), ...]."""
    m = len(sections[0][0])
    v = []
    for pts, z in sections:
        assert len(pts) == m
        v += [(x, y, z) for x, y in pts]
    f = []
    for s in range(len(sections) - 1):
        a0, b0 = s * m, (s + 1) * m
        for i in range(m):
            j = (i + 1) % m
            f += [(a0 + i, a0 + j, b0 + j), (a0 + i, b0 + j, b0 + i)]
    # The two end caps. Rings run counter-clockwise seen from +w, so the FAR cap keeps that
    # order (outward normal +w) and the NEAR cap must be reversed (outward normal -w).
    # Both were wound the wrong way round here, which no other check in this file could see:
    # closed() counts UNDIRECTED edges so a flipped cap still reads as closed, and orient()
    # only looks at the sign of the total volume, which stayed positive. The symptom was a
    # solid whose volume came out at a third of its true value and whose end caps would have
    # rendered inside-out in Unreal. consistently_oriented() below now catches it directly.
    top = len(sections) - 1
    for i in range(1, m - 1):
        f += [(0, i + 1, i), (top * m + i, top * m + i + 1, top * m)]
    return orient(v, f)


def ring_pts(hx, hy, corner=0.0, seg=3):
    """A rounded rectangle as a closed ring of points, for lofted posts and uprights."""
    if corner <= 0.0:
        return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    pts = []
    for cx, cy, a0 in ((hx - corner, hy - corner, 0.0), (-hx + corner, hy - corner, 90.0),
                       (-hx + corner, -hy + corner, 180.0), (hx - corner, -hy + corner, 270.0)):
        for s in range(seg + 1):
            a = math.radians(a0 + 90.0 * s / seg)
            pts.append((cx + corner * math.cos(a), cy + corner * math.sin(a)))
    return pts


def chamfered_post(cx, cy, hx, hy, z0, z1, corner=1.6):
    return loft([(ring_pts(hx, hy, corner), z0), (ring_pts(hx, hy, corner), z1)]) if False else \
        prism([(cx + x, cy + y) for x, y in ring_pts(hx, hy, corner)], z0, z1)


def rbox(x0, x1, y0, y1, z0, z1, corner=1.2, seg=3, chamfer=0.0, axis='z'):
    """A box with filleted edges along `axis` and an optional chamfer at each end.

    This is the workhorse of every mesh below. A security checkpoint is made of extruded
    aluminium and folded sheet, and neither has a truly sharp arris: the fillet is what catches
    the light and tells the eye the object is metal rather than a placeholder cube. `seg` sets
    the fillet tessellation, so it is also the density control for the whole file. Rings are
    built in the two axes that are not `axis` and stacked along `axis`, using the same axis
    convention as cylinder(). The result is closed and positively oriented, which write_obj
    asserts part by part."""
    lo = dict(x=x0, y=y0, z=z0)
    hi = dict(x=x1, y=y1, z=z1)
    ua, va = dict(z=('x', 'y'), y=('x', 'z'), x=('y', 'z'))[axis]
    u0, u1, v0, v1 = lo[ua], hi[ua], lo[va], hi[va]
    w0, w1 = lo[axis], hi[axis]
    hu, hv = (u1 - u0) / 2.0, (v1 - v0) / 2.0
    cu, cv = (u0 + u1) / 2.0, (v0 + v1) / 2.0
    lim = min(abs(hu), abs(hv))
    chamfer = max(0.0, min(chamfer, lim * 0.45, abs(w1 - w0) * 0.45))

    def ring(inset):
        c = 0.0 if corner <= 0.0 else max(0.02, min(corner, (lim - inset) * 0.9))
        return [(cu + p, cv + q) for p, q in ring_pts(hu - inset, hv - inset, c, seg)]

    if chamfer <= 1e-9:
        secs = [(ring(0.0), w0), (ring(0.0), w1)]
    else:
        secs = [(ring(chamfer), w0), (ring(0.0), w0 + chamfer),
                (ring(0.0), w1 - chamfer), (ring(chamfer), w1)]
    verts, faces = loft(secs)
    out = []
    for uu, vv, ww in verts:
        d = {ua: uu, va: vv, axis: ww}
        out.append((d['x'], d['y'], d['z']))
    return orient(out, faces)


def bolt(x, y, z, r=1.5, h=1.1, axis='z', seg=10):
    """A raised fastener head. Small, but there are many, and they read as machined."""
    return cylinder((x, y, z), r, h, seg, axis=axis)


# =====================================================================================
# 8. The meshes
# =====================================================================================
# Every number below is DEPICTED, not asserted: ordinary security-equipment sizes chosen so a
# 175 cm figure walks through without stooping and reads a sign at eye level.
ARCH = dict(clear_width=76.0, clear_height=200.0, upright_y=18.0, upright_x=22.0,
            upright_height=220.0, header_height=32.0, base_x=44.0, base_y=32.0, base_z=4.0)


def detector_arch_parts():
    """A walk-through metal detector: two pillars, a header, base plates with levelling feet,
    a control panel with its keypad, and the column of indicator lamps down each inner face."""
    a = ARCH
    inner = a['clear_width'] / 2.0
    outer = inner + a['upright_y']
    hx = a['upright_x'] / 2.0
    parts = []
    for side in (-1, 1):
        tag = 'L' if side < 0 else 'R'
        cy = side * (inner + a['upright_y'] / 2.0)
        y0, y1 = cy - a['upright_y'] / 2.0, cy + a['upright_y'] / 2.0
        parts.append(('Upright%s' % tag,
                      rbox(-hx, hx, y0, y1, a['base_z'], a['upright_height'],
                           corner=3.4, seg=6, chamfer=1.2)))
        parts.append(('BasePlate%s' % tag,
                      rbox(-a['base_x'] / 2.0, a['base_x'] / 2.0, cy - a['base_y'] / 2.0,
                           cy + a['base_y'] / 2.0, 0.0, a['base_z'], corner=2.6, seg=4, chamfer=0.9)))
        for fx in (-1, 1):
            for fy in (-1, 1):
                parts.append(('Foot%s%d%d' % (tag, fx > 0, fy > 0),
                              revolve([(0.0, 0.0), (3.2, 0.0), (3.4, 1.0), (2.0, 2.4), (0.0, 2.6)],
                                      (fx * (a['base_x'] / 2.0 - 6.0),
                                       cy + fy * (a['base_y'] / 2.0 - 6.0), 0.0), 14)))
        # the column of indicator lamps that lights as a person passes through
        for k in range(11):
            z = 40.0 + k * 14.5
            e0, e1 = sorted((side * (inner - 0.9), side * (inner + 0.7)))
            parts.append(('Indicator%s%02d' % (tag, k),
                          rbox(-6.0, 6.0, e0, e1, z, z + 8.4, corner=1.4, seg=3, chamfer=0.5)))
        for k in range(4):
            parts.append(('PillarBolt%s%d' % (tag, k),
                          bolt(hx - 0.2, cy - 5.0 + k * 3.4, a['base_z'] + 4.0, 1.5, 1.0, axis='x')))
    parts.append(('Header', rbox(-hx, hx, -outer, outer, a['upright_height'],
                                 a['upright_height'] + a['header_height'],
                                 corner=3.4, seg=6, chamfer=1.4)))
    parts.append(('HeaderCap', rbox(-hx - 1.6, hx + 1.6, -outer - 1.6, outer + 1.6,
                                    a['upright_height'] + a['header_height'],
                                    a['upright_height'] + a['header_height'] + 3.2,
                                    corner=2.2, seg=4, chamfer=1.0)))
    parts.append(('ControlPanel', rbox(-8.5, 8.5, outer, outer + 13.0, 117.0, 153.0,
                                       corner=2.0, seg=4, chamfer=1.0, axis='y')))
    parts.append(('ControlFace', rbox(-6.6, 6.6, outer + 12.6, outer + 14.4, 121.0, 149.0,
                                      corner=1.0, seg=3, axis='y')))
    for r in range(4):
        for c in range(3):
            parts.append(('Key%d%d' % (r, c),
                          cylinder((-4.2 + c * 4.2, outer + 14.4, 126.0 + r * 6.0),
                                   1.5, 0.9, 10, axis='y')))
    return parts


def bag_scanner_parts():
    """A bag scanner: a table on castors, a belt over its rollers, a shielded hood with hanging
    lead curtain strips at both mouths, and the operator's monitor on its stalk."""
    parts = []
    top_z, leg = 84.0, 7.0
    parts.append(('TableTop', rbox(-90.0, 90.0, -35.0, 35.0, top_z, top_z + 6.0,
                                   corner=2.4, seg=4, chamfer=1.2)))
    parts.append(('TableSkirt', rbox(-88.0, 88.0, -32.0, 32.0, top_z - 9.0, top_z,
                                     corner=1.6, seg=3, chamfer=0.8)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cxx, cyy = sx * 82.0, sy * 28.0
            parts.append(('Leg%d%d' % (sx > 0, sy > 0),
                          rbox(cxx - leg / 2.0, cxx + leg / 2.0, cyy - leg / 2.0, cyy + leg / 2.0,
                               3.2, top_z - 9.0, corner=1.4, seg=4, chamfer=0.8)))
            parts.append(('Castor%d%d' % (sx > 0, sy > 0),
                          revolve([(0.0, 0.0), (4.4, 0.0), (4.6, 1.2), (2.6, 3.0), (0.0, 3.4)],
                                  (cxx, cyy, 0.0), 14)))
    parts.append(('LegRail', rbox(-84.0, 84.0, -3.2, 3.2, 16.0, 22.0, corner=1.2, seg=3, chamfer=0.6)))
    parts.append(('Belt', rbox(-85.0, 85.0, -28.0, 28.0, top_z + 6.0, top_z + 10.2,
                               corner=1.0, seg=3, chamfer=0.5)))
    for k in range(11):
        x = -80.0 + k * 16.0
        parts.append(('Roller%02d' % k, tube_along_y((x, top_z + 8.1), 2.8, 1.3, -28.5, 28.5, 18)))
    hood_z0, hood_z1 = top_z + 10.2, top_z + 10.2 + 62.0
    parts.append(('Hood', frame_prism((-38.0, 38.0, hood_z0, hood_z1),
                                      (-31.0, 31.0, hood_z0 + 3.0, hood_z1 - 16.0), -34.0, 34.0)))
    parts.append(('HoodCap', rbox(-39.5, 39.5, -35.5, 35.5, hood_z1, hood_z1 + 3.4,
                                  corner=2.2, seg=4, chamfer=1.1)))
    for xx, sign in ((-34.0, -1.0), (34.0, 1.0)):
        for k in range(9):
            y0 = -30.0 + k * 6.8
            lo, hi = sorted((xx + sign * 0.4, xx + sign * 1.8))
            parts.append(('Curtain%s%d' % ('A' if sign < 0 else 'B', k),
                          rbox(lo, hi, y0, y0 + 5.6, hood_z0 + 6.0, hood_z1 - 18.0,
                               corner=0.8, seg=2, chamfer=0.4)))
    for k in range(6):
        parts.append(('HoodBolt%d' % k,
                      bolt(-34.6, -26.0 + k * 10.4, hood_z1 - 8.0, 1.4, 1.0, axis='x')))
    parts.append(('MonitorStalk', cylinder((78.0, 30.0, top_z + 6.0), 2.2, 44.0, 14)))
    parts.append(('Monitor', rbox(73.6, 76.8, 8.0, 52.0, top_z + 50.0, top_z + 78.0,
                                  corner=1.8, seg=4, chamfer=0.9, axis='x')))
    parts.append(('MonitorScreen', rbox(72.4, 73.8, 10.0, 50.0, top_z + 53.0, top_z + 75.0,
                                        corner=0.8, seg=2, axis='x')))
    return parts


def stanchion_parts(span_y=180.0):
    """A belt stanchion: a weighted cast base, a tapered post, the belt cassette at the top,
    and the belt itself sagging across to the next post in the line."""
    parts = []
    parts.append(('Base', revolve([(0.0, 0.0), (16.0, 0.0), (17.2, 1.0), (17.2, 2.6),
                                   (14.0, 4.2), (8.0, 5.0), (0.0, 5.2)], (0.0, 0.0, 0.0), 40)))
    parts.append(('BaseRing', revolve([(0.0, -0.6), (17.4, -0.6), (17.4, 0.4), (0.0, 0.4)],
                                      (0.0, 0.0, 0.0), 40)))
    parts.append(('Post', loft([(ring_pts(3.6, 3.6, 1.30, 6), 5.0),
                                (ring_pts(3.4, 3.4, 1.25, 6), 26.0),
                                (ring_pts(3.1, 3.1, 1.15, 6), 54.0),
                                (ring_pts(2.9, 2.9, 1.10, 6), 78.0),
                                (ring_pts(2.8, 2.8, 1.05, 6), 88.0)])))
    parts.append(('Cassette', rbox(-4.6, 4.6, -5.4, 5.4, 84.0, 96.0, corner=2.0, seg=5, chamfer=1.0)))
    parts.append(('Collar', revolve([(0.0, 96.0), (5.4, 96.0), (5.4, 98.0), (3.6, 100.4), (0.0, 100.8)],
                                    (0.0, 0.0, 0.0), 32)))
    for k in range(3):
        a = k * math.tau / 3.0
        parts.append(('BaseBolt%d' % k, bolt(11.0 * math.cos(a), 11.0 * math.sin(a), 4.6, 1.5, 0.9)))
    # the belt: a sagging strap paid out towards the next post in the line
    seg = 22
    v, f = [], []
    for k in range(seg + 1):
        t = k / float(seg)
        y = 6.0 + t * (span_y - 6.0)
        z = 88.0 - 5.5 * math.sin(math.pi * t)
        v += [(-0.75, y, z - 2.7), (0.75, y, z - 2.7), (0.75, y, z + 2.7), (-0.75, y, z + 2.7)]
    for k in range(seg):
        a0, b0 = k * 4, (k + 1) * 4
        for i in range(4):
            j = (i + 1) % 4
            f += [(a0 + i, a0 + j, b0 + j), (a0 + i, b0 + j, b0 + i)]
    f += [(0, 2, 1), (0, 3, 2)]
    last = seg * 4
    f += [(last, last + 1, last + 2), (last, last + 2, last + 3)]
    parts.append(('Belt', orient(v, f)))
    return parts


def booth_parts():
    """A guard booth: a plinth, four walls, a glazed service window with mullions, a panelled
    door with hinges and a lever handle, a counter shelf, ventilation louvres and a capped roof."""
    parts = []
    hx, hy, wall, wz = 92.0, 92.0, 7.0, 250.0
    parts.append(('Plinth', rbox(-hx - 4.0, hx + 4.0, -hy - 4.0, hy + 4.0, 0.0, 9.0,
                                 corner=3.0, seg=4, chamfer=1.4)))
    # the -X wall carries the service window, because that is the side the queue reaches first
    wy0, wy1, wz0, wz1 = -56.0, 56.0, 106.0, 186.0
    for nm, y0, y1, z0, z1 in (('WallFrontLow', -hy, hy, 9.0, wz0),
                               ('WallFrontHigh', -hy, hy, wz1, wz),
                               ('WallFrontLeft', -hy, wy0, wz0, wz1),
                               ('WallFrontRight', wy1, hy, wz0, wz1)):
        parts.append((nm, rbox(-hx, -hx + wall, y0, y1, z0, z1, corner=1.0, seg=2, chamfer=0.5)))
    parts.append(('WindowGlass', rbox(-hx + 2.6, -hx + 4.4, wy0, wy1, wz0, wz1,
                                      corner=0.8, seg=2, axis='x')))
    for k in range(3):
        yy = wy0 + (k + 1) * (wy1 - wy0) / 4.0
        parts.append(('Mullion%d' % k, rbox(-hx + 1.6, -hx + 5.4, yy - 1.4, yy + 1.4, wz0, wz1,
                                            corner=0.9, seg=3, chamfer=0.4)))
    parts.append(('WindowSill', rbox(-hx - 3.0, -hx + wall, wy0 - 3.0, wy1 + 3.0, wz0 - 3.2, wz0,
                                     corner=1.2, seg=3, chamfer=0.6)))
    parts.append(('Counter', rbox(-hx - 24.0, -hx + wall, wy0 - 6.0, wy1 + 6.0, wz0 - 9.0, wz0 - 3.2,
                                  corner=2.0, seg=4, chamfer=1.0)))
    for k in range(2):
        yy = -34.0 + k * 68.0
        parts.append(('CounterBracket%d' % k,
                      rbox(-hx - 20.0, -hx, yy - 1.6, yy + 1.6, wz0 - 26.0, wz0 - 9.0,
                           corner=0.8, seg=2, chamfer=0.4)))
    # the +Y wall carries the door
    dx0, dx1, dz1 = -34.0, 40.0, 208.0
    parts.append(('WallSideNearLeft', rbox(-hx, dx0, hy - wall, hy, 9.0, wz,
                                           corner=1.0, seg=2, chamfer=0.5)))
    parts.append(('WallSideNearRight', rbox(dx1, hx, hy - wall, hy, 9.0, wz,
                                            corner=1.0, seg=2, chamfer=0.5)))
    parts.append(('WallSideNearHead', rbox(dx0, dx1, hy - wall, hy, dz1, wz,
                                           corner=1.0, seg=2, chamfer=0.5)))
    parts.append(('Door', rbox(dx0 + 1.0, dx1 - 1.0, hy - wall + 1.2, hy - 1.4, 9.0, dz1 - 1.0,
                               corner=1.2, seg=3, chamfer=0.6)))
    for k in range(2):
        z0 = 24.0 + k * 88.0
        parts.append(('DoorPanel%d' % k, rbox(dx0 + 8.0, dx1 - 8.0, hy - 1.4, hy - 0.4,
                                              z0, z0 + 70.0, corner=1.6, seg=3, chamfer=0.5)))
    for k in range(3):
        parts.append(('Hinge%d' % k, cylinder((dx0 + 1.0, hy - 3.0, 30.0 + k * 72.0), 1.8, 9.0, 12)))
    parts.append(('Handle', cylinder((dx1 - 8.0, hy - 1.4, 104.0), 1.6, 6.0, 12, axis='y')))
    parts.append(('HandleLever', rbox(dx1 - 22.0, dx1 - 6.0, hy + 3.0, hy + 5.4, 102.4, 105.6,
                                      corner=1.1, seg=3, chamfer=0.5)))
    parts.append(('WallSideFar', rbox(-hx, hx, -hy, -hy + wall, 9.0, wz, corner=1.0, seg=2, chamfer=0.5)))
    parts.append(('WallBack', rbox(hx - wall, hx, -hy + wall, hy - wall, 9.0, wz,
                                   corner=1.0, seg=2, chamfer=0.5)))
    for k in range(7):
        z = 168.0 + k * 5.0
        parts.append(('Louvre%d' % k, rbox(hx - 0.4, hx + 2.2, -30.0, 30.0, z, z + 3.0,
                                           corner=0.7, seg=2, chamfer=0.3)))
    parts.append(('Roof', rbox(-hx - 12.0, hx + 12.0, -hy - 12.0, hy + 12.0, wz, wz + 9.0,
                               corner=4.0, seg=5, chamfer=2.0)))
    parts.append(('RoofLip', rbox(-hx - 14.0, hx + 14.0, -hy - 14.0, hy + 14.0, wz + 9.0, wz + 12.0,
                                  corner=4.5, seg=5, chamfer=1.4)))
    parts.append(('Lamp', rbox(-hx - 10.0, -hx + 6.0, -14.0, 14.0, wz - 5.0, wz,
                               corner=1.8, seg=4, chamfer=0.9)))
    parts.append(('LampLens', rbox(-hx - 9.0, -hx + 5.0, -12.0, 12.0, wz - 6.6, wz - 5.0,
                                   corner=1.4, seg=3, chamfer=0.5)))
    return parts


def shoe_rack_parts():
    """An open shoe rack: a toe kick on feet, five uprights, five shelves, cubby dividers,
    a back panel, a top rail and the numbered label plate over each bay."""
    parts = []
    hy, depth, height = 82.0, 38.0, 152.0
    hd = depth / 2.0
    parts.append(('ToeKick', rbox(-hd + 2.0, hd - 2.0, -hy, hy, 6.0, 15.0,
                                  corner=1.4, seg=3, chamfer=0.7)))
    for k in range(4):
        parts.append(('Foot%d' % k,
                      cylinder((0.0, -hy + 6.0 + k * (2.0 * hy - 12.0) / 3.0, 0.0), 3.2, 6.0, 12)))
    pitch = (2.0 * hy - 3.0) / 4.0
    for k in range(5):
        y = -hy + k * pitch
        parts.append(('Upright%d' % k, rbox(-hd, hd, y, y + 3.0, 15.0, height,
                                            corner=1.2, seg=4, chamfer=0.6)))
    shelf_pitch = (height - 15.0 - 3.0) / 4.0
    for k in range(5):
        z = 15.0 + k * shelf_pitch
        parts.append(('Shelf%d' % k, rbox(-hd, hd, -hy, hy, z, z + 3.0,
                                          corner=1.2, seg=4, chamfer=0.6)))
    # a divider halfway across each bay on the two lower shelves, so cubbies read as cubbies
    for s in range(2):
        z = 15.0 + s * shelf_pitch
        for k in range(4):
            y = -hy + 3.0 + k * pitch + pitch / 2.0
            parts.append(('Divider%d%d' % (s, k),
                          rbox(-hd + 3.0, hd - 2.0, y - 1.1, y + 1.1, z + 3.0, z + shelf_pitch,
                               corner=0.7, seg=2, chamfer=0.3)))
    parts.append(('Back', rbox(hd - 2.0, hd, -hy, hy, 15.0, height, corner=0.8, seg=2, chamfer=0.4)))
    parts.append(('TopRail', rbox(-hd - 1.5, hd + 1.5, -hy - 1.5, hy + 1.5, height, height + 4.0,
                                  corner=2.0, seg=4, chamfer=1.0)))
    for k in range(4):
        y = -hy + 3.0 + k * pitch
        parts.append(('LabelPlate%d' % k, rbox(-hd - 1.0, -hd, y + 6.0, y + pitch - 9.0,
                                               height - 18.0, height - 8.0,
                                               corner=1.0, seg=3, chamfer=0.4, axis='x')))
    return parts


SIGN_PANEL = dict(face_w=84.0, face_h=126.0, frame_w=92.0, frame_h=134.0,
                  frame_x=6.0, face_x=1.0, top_z=248.0, post_r=4.2, post_h=250.0)
SIGN_PLATE = dict(face_w=64.0, face_h=40.0, frame_w=70.0, frame_h=46.0,
                  frame_x=3.0, face_x=0.8, centre_z=155.0)


def _frame_rails(prefix, fy0, fy1, fz0, fz1, iy0, iy1, iz0, iz1, x0, x1, corner, seg, chamfer):
    """A picture frame built as four rails rather than one extruded annulus, so the frame has a
    rounded outer arris and reads as folded section at grazing angles."""
    return [
        (prefix + 'RailBottom', rbox(x0, x1, fy0, fy1, fz0, iz0, corner, seg, chamfer, axis='y')),
        (prefix + 'RailTop', rbox(x0, x1, fy0, fy1, iz1, fz1, corner, seg, chamfer, axis='y')),
        (prefix + 'RailLeft', rbox(x0, x1, fy0, iy0, iz0, iz1, corner, seg, chamfer, axis='z')),
        (prefix + 'RailRight', rbox(x0, x1, iy1, fy1, iz0, iz1, corner, seg, chamfer, axis='z')),
    ]


def sign_post_frame_parts():
    """The post-mounted panel: a tapered post on a bolted base flange, the frame, and the backer
    the printed face is bonded to."""
    s = SIGN_PANEL
    z1 = s['top_z']
    z0 = z1 - s['frame_h']
    iz0 = z0 + (s['frame_h'] - s['face_h']) / 2.0
    iz1 = z1 - (s['frame_h'] - s['face_h']) / 2.0
    iy0, iy1 = -s['face_w'] / 2.0, s['face_w'] / 2.0
    fy0, fy1 = -s['frame_w'] / 2.0, s['frame_w'] / 2.0
    fx0, fx1 = -s['frame_x'] / 2.0, s['frame_x'] / 2.0
    parts = [('Post', revolve([(0.0, 0.0), (6.4, 0.0), (6.4, 4.0), (s['post_r'] + 0.6, 7.0),
                               (s['post_r'], 40.0), (s['post_r'] - 0.5, s['post_h'] - 6.0),
                               (s['post_r'] - 0.5, s['post_h']), (0.0, s['post_h'] + 2.6)],
                              (0.0, 0.0, 0.0), 32)),
             ('BaseFlange', revolve([(0.0, 0.0), (11.0, 0.0), (11.0, 1.6), (7.5, 3.0), (0.0, 3.2)],
                                    (0.0, 0.0, 0.0), 28))]
    for k in range(4):
        a = k * math.tau / 4.0 + math.pi / 4.0
        parts.append(('FlangeBolt%d' % k, bolt(8.6 * math.cos(a), 8.6 * math.sin(a), 1.6, 1.5, 1.1)))
    parts += _frame_rails('Frame', fy0, fy1, z0, z1, iy0, iy1, iz0, iz1, fx0, fx1, 1.4, 4, 0.7)
    parts.append(('Backer', rbox(fx1 - 0.9, fx1 + 0.4, iy0, iy1, iz0, iz1,
                                 corner=0.8, seg=2, axis='x')))
    for sy in (-1, 1):
        parts.append(('Bracket%d' % (sy > 0), rbox(-1.8, 1.8, sy * 5.0 - 2.2, sy * 5.0 + 2.2,
                                                   z0 - 7.0, z0 + 9.0, corner=0.9, seg=3, chamfer=0.4)))
    return parts


def sign_post_face_parts():
    """The printed face alone, so the sign artwork gets its own material slot."""
    s = SIGN_PANEL
    z1 = s['top_z'] - (s['frame_h'] - s['face_h']) / 2.0
    z0 = z1 - s['face_h']
    return [('Face', slab(-s['frame_x'] / 2.0 - 0.6, -s['frame_x'] / 2.0 + 0.4,
                          -s['face_w'] / 2.0, s['face_w'] / 2.0, z0, z1))]


def sign_plate_frame_parts():
    """The wall-mounted plate: the same frame in miniature, on four standoffs."""
    s = SIGN_PLATE
    z0 = s['centre_z'] - s['frame_h'] / 2.0
    z1 = s['centre_z'] + s['frame_h'] / 2.0
    iz0 = s['centre_z'] - s['face_h'] / 2.0
    iz1 = s['centre_z'] + s['face_h'] / 2.0
    iy0, iy1 = -s['face_w'] / 2.0, s['face_w'] / 2.0
    fy0, fy1 = -s['frame_w'] / 2.0, s['frame_w'] / 2.0
    parts = _frame_rails('Frame', fy0, fy1, z0, z1, iy0, iy1, iz0, iz1,
                         0.0, s['frame_x'], 1.0, 4, 0.5)
    parts.append(('Backer', rbox(s['frame_x'] - 0.7, s['frame_x'], iy0, iy1, iz0, iz1,
                                 corner=0.6, seg=2, axis='x')))
    for sy in (-1, 1):
        for sz in (-1, 1):
            yy = sy * (s['frame_w'] / 2.0 - 3.0)
            zz = s['centre_z'] + sz * (s['frame_h'] / 2.0 - 3.0)
            parts.append(('Standoff%d%d' % (sy > 0, sz > 0),
                          cylinder((s['frame_x'], yy, zz), 1.3, 2.6, 14, axis='x')))
            parts.append(('Boss%d%d' % (sy > 0, sz > 0),
                          cylinder((-0.9, yy, zz), 1.9, 1.2, 16, axis='x')))
    return parts


def sign_plate_face_parts():
    s = SIGN_PLATE
    return [('Face', slab(-0.6, 0.4, -s['face_w'] / 2.0, s['face_w'] / 2.0,
                          s['centre_z'] - s['face_h'] / 2.0, s['centre_z'] + s['face_h'] / 2.0))]



def sign_face_uv(kind):
    """Planar UVs on the printed face.

    The face is the -X side of the panel, because a visitor walks in +X towards the gate and
    must read the sign as they approach. Looking along +X with +Z up, the viewer's right hand
    points along -Y, so u must GROW as y FALLS. v grows downward, which is the UE convention.
    A textured preview of each sign is rendered from the visitor's eye so that this is checked
    by eye and not only by argument."""
    if kind == 'panel':
        s = SIGN_PANEL
        z1 = s['top_z'] - (s['frame_h'] - s['face_h']) / 2.0
        y0, y1, zz0, zz1 = -s['face_w'] / 2.0, s['face_w'] / 2.0, z1 - s['face_h'], z1
    else:
        s = SIGN_PLATE
        y0, y1 = -s['face_w'] / 2.0, s['face_w'] / 2.0
        zz0, zz1 = s['centre_z'] - s['face_h'] / 2.0, s['centre_z'] + s['face_h'] / 2.0

    def uv(p):
        u = (y1 - p[1]) / (y1 - y0)
        v = (zz1 - p[2]) / (zz1 - zz0)
        return (min(1.0, max(0.0, u)), min(1.0, max(0.0, v)))
    return uv


MESHES = [
    dict(key='DetectorArch', build=detector_arch_parts, role='metal_brushed',
         what='Walk-through metal detector arch: two uprights, a header, base plates, a control panel and indicator strips.',
         claim='modern-staging'),
    dict(key='BagScanner', build=bag_scanner_parts, role='metal_brushed',
         what='Bag-scanner table with a conveyor, rollers, a shielded hood, hanging curtain strips and an operator monitor.',
         claim='modern-staging'),
    dict(key='Stanchion', build=stanchion_parts, role='metal_dark',
         what='Belt stanchion: weighted base, post, collar and a sagging belt spanning to the next post.',
         claim='modern-staging'),
    dict(key='Booth', build=booth_parts, role='painted_steel',
         what='Guard booth with a service window, a counter shelf, a door and an overhanging roof.',
         claim='modern-staging'),
    dict(key='ShoeRack', build=shoe_rack_parts, role='timber',
         what='Open shoe rack: five uprights, four rows of cubbies, a back panel, a toe kick and label plates.',
         claim='modern-staging-serving-a-halachic-rule'),
    dict(key='SignPostFrame', build=sign_post_frame_parts, role='metal_dark',
         what='Tall post-mounted sign: post, panel frame and backer.', claim='modern-staging'),
    dict(key='SignPostFace', build=sign_post_face_parts, role='sign_face', uv='panel',
         what='The printed face of the post-mounted panel; its own mesh so the artwork gets its own material.',
         claim='see the sign it carries'),
    dict(key='SignPlateFrame', build=sign_plate_frame_parts, role='metal_dark',
         what='Wall-mounted sign plate: frame, backer and four fixing bosses.', claim='modern-staging'),
    dict(key='SignPlateFace', build=sign_plate_face_parts, role='sign_face', uv='plate',
         what='The printed face of the wall-mounted plate.', claim='see the sign it carries'),
]


# =====================================================================================
# 9. OBJ export and readback
# =====================================================================================
def write_obj(name, parts, path, uv_kind=None):
    """OBJ for the legacy Unreal OBJ importer adapter: Y reflected, winding reversed.

    UVs: with uv_kind the face is mapped planar (a sign); otherwise the per-triangle local
    basis used by create_keilim_ti_v1, which tiles a material sensibly over arbitrary shapes."""
    uv_fn = sign_face_uv(uv_kind) if uv_kind else None
    lines = ['# GateSecurityV1 %s; Unreal legacy OBJ adapter (Y reflected, winding reversed)' % name,
             'o ' + name]
    index = 1
    allv = []
    checks = []
    for part, (vertices, faces) in parts:
        vol = volume(vertices, faces)
        assert vol > 0, 'inverted part ' + part
        assert closed(vertices, faces), 'open part ' + part
        assert consistently_oriented(vertices, faces), 'inconsistently wound part ' + part
        allv.extend(vertices)
        lines.append('g ' + part)
        for a, b, c in faces:
            src = [vertices[i] for i in (a, c, b)]
            p, q, r = [(v[0], -v[1], v[2]) for v in src]
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            length = math.sqrt(sum(x * x for x in ab))
            nl = math.sqrt(sum(x * x for x in n))
            assert nl > 1e-8 and length > 1e-8, 'degenerate triangle in ' + part
            for vv in (p, q, r):
                lines.append('v %.6f %.6f %.6f' % vv)
            if uv_fn:
                uvs = [uv_fn(v) for v in src]
            else:
                uvs = ((0, 0), (length / 10.0, 0),
                       (sum(ac[i] * ab[i] / length for i in range(3)) / 10.0, nl / length / 10.0))
            for uv in uvs:
                lines.append('vt %.6f %.6f' % uv)
            for _ in range(3):
                lines.append('vn %.6f %.6f %.6f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
        checks.append(dict(name=part, triangles=len(faces), closed=True,
                           consistentlyOriented=True, volume_cm3=round(vol, 4)))
    Path(path).write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(p[i] for p in allv) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    return dict(name=name, file=Path(path).name,
                sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                triangles=(index - 1) // 3, parts=len(parts),
                bounds_cm={k: [round(x, 5) for x in v] for k, v in bounds.items()},
                minimum_part_signed_volume_cm3=min(c['volume_cm3'] for c in checks),
                uv_mapping=('planar %s face' % uv_kind) if uv_kind else 'per-triangle local basis',
                part_checks=checks)


def readback(path, record):
    """Re-read the file we just wrote and re-derive every number in the record from it."""
    verts, normals, uvs, faces = [], [], [], []
    for line in Path(path).read_text().splitlines():
        c = line.split()
        if not c:
            continue
        if c[0] == 'v':
            verts.append(tuple(map(float, c[1:])))
        elif c[0] == 'vn':
            normals.append(tuple(map(float, c[1:])))
        elif c[0] == 'vt':
            uvs.append(tuple(map(float, c[1:])))
        elif c[0] == 'f':
            faces.append([tuple(int(x) - 1 for x in t.split('/')) for t in c[1:]])
    assert len(faces) == record['triangles'], (len(faces), record['triangles'])
    worst_normal = 0.0
    signed = 0.0
    for face in faces:
        assert len(face) == 3
        a, b, c = [verts[t[0]] for t in face]
        n = cross([b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)])
        nl = math.sqrt(sum(x * x for x in n)) or 1.0
        stored = normals[face[0][2]]
        worst_normal = max(worst_normal, max(abs(n[i] / nl - stored[i]) for i in range(3)))
        signed += sum(a[i] * n[i] for i in range(3))
    signed /= 6.0
    # bounds re-derived with Y reflected back, which is what the importer will produce
    back = [(x, -y, z) for x, y, z in verts]
    got = {k: [round(fn(p[i] for p in back), 5) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    assert got == record['bounds_cm'], (got, record['bounds_cm'])
    uv_min = [round(min(t[i] for t in uvs), 5) for i in range(2)] if uvs else None
    uv_max = [round(max(t[i] for t in uvs), 5) for i in range(2)] if uvs else None
    authored = round(sum(c['volume_cm3'] for c in record['part_checks']), 4)
    return dict(file=record['file'], triangles=len(faces), vertices=len(verts),
                worstStoredNormalError=round(worst_normal, 9),
                objSignedVolumeCm3=round(signed, 4),
                authoredSolidVolumeCm3=authored,
                objSignedVolumeIsPositiveAsExpected=signed > 0,
                objSignedVolumeMatchesAuthoredCm3=abs(signed - authored) < 0.05,
                boundsAfterUnreflectingY=got, uvRange=[uv_min, uv_max],
                note=('The OBJ carries TWO orientation flips -- Y is reflected and the triangle '
                      'winding is reversed -- and two flips cancel, so the signed volume of the '
                      'file itself, computed right-handed, is POSITIVE and equals the authored '
                      'solid volume exactly. An earlier version of this note claimed it should '
                      'be NEGATIVE, having counted only the reflection; the equality recorded '
                      'here is the evidence that it is not. The importer negates Y once more, '
                      'which leaves the stored triangle order correct for the left-handed face '
                      'normal cross(C-A, B-A) that Unreal uses. The native winding check in '
                      'release_gate_security.py is what confirms that in the engine, not this '
                      'file.'))


# =====================================================================================
# 10. Previews
# =====================================================================================
def render_geometry(geo, path, views, size=(1500, 520)):
    """Flat-shaded software orthographic previews. Not a native render, not an acceptance."""
    W, H = size
    cv = Canvas(W, H, (24, 27, 32))
    zbuf = [-1e18] * (W * H)
    cols = len(views)
    panel = W // cols
    role_colour = dict(metal_brushed=(176, 182, 190), metal_dark=(96, 100, 108),
                       painted_steel=(198, 194, 182), timber=(150, 112, 72),
                       sign_face=(232, 228, 218))
    for k, (yaw, pitch, scale, _label) in enumerate(views):
        u = (math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
        cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        cam = (-u[0] * cp, -u[1] * cp, -sp)
        right = cross((0.0, 0.0, 1.0), cam)
        rl = math.sqrt(sum(x * x for x in right)) or 1.0
        right = [x / rl for x in right]
        up = cross(cam, right)
        # Every mesh is authored about its own pivot, so drawing them unshifted piles them all
        # on one spot and the booth simply hides the rest. Lay them out in a row -- but the row
        # has to run along whatever direction is HORIZONTAL ON SCREEN in this particular view,
        # or a view that happens to look down the row sees one mesh and eight shadows. So the
        # offsets are computed per view, in projected space, along `right`.
        proj = {}
        for _nm, (_ps, _rl) in geo.items():
            ws = [sum(q[i] * right[i] for i in range(3)) for _pn, (_vv, _ff) in _ps for q in _vv]
            hs = [sum(q[i] * up[i] for i in range(3)) for _pn, (_vv, _ff) in _ps for q in _vv]
            proj[_nm] = (min(ws), max(ws), min(hs), max(hs))
        gap = 26.0
        cursor = 0.0
        offset = {}
        for _nm in geo:
            w0, w1, _h0, _h1 = proj[_nm]
            offset[_nm] = cursor - w0
            cursor += (w1 - w0) + gap
        row = cursor - gap
        for _nm in offset:
            offset[_nm] -= row / 2.0
        # Auto-fit: the row is over ten metres wide, so a hand-set scale either crops it or
        # leaves it a speck. `scale` from the caller survives as a fill fraction, not cm/px.
        margin = 18.0
        hspan = max(1e-6, max(p3[3] for p3 in proj.values()) - min(p3[2] for p3 in proj.values()))
        fit = min((panel - 2 * margin) / max(1e-6, row), (H - 2 * margin) / hspan) * min(1.0, scale / 1.55)
        x0 = k * panel + panel / 2.0
        base_y = H / 2.0 + (min(p3[2] for p3 in proj.values()) + max(p3[3] for p3 in proj.values())) / 2.0 * fit
        scale = fit
        light = (-0.42, -0.55, 0.72)
        for name, (parts, role) in geo.items():
            colour = role_colour.get(role, (180, 180, 180))
            dw = offset[name]
            for _pn, (v, f) in parts:
                pr = [((sum(p[i] * right[i] for i in range(3)) + dw) * scale + x0,
                       base_y - sum(p[i] * up[i] for i in range(3)) * scale,
                       -sum(p[i] * cam[i] for i in range(3))) for p in v]
                for a, b, c in f:
                    pa, pb, pc = v[a], v[b], v[c]
                    n = cross([pb[i] - pa[i] for i in range(3)], [pc[i] - pa[i] for i in range(3)])
                    nl = math.sqrt(sum(x * x for x in n)) or 1.0
                    shade = 0.34 + 0.66 * max(0.0, sum(n[i] * light[i] for i in range(3)) / nl)
                    col = tuple(min(255, int(x * shade)) for x in colour)
                    (ax, ay, ad), (bx, by, bd), (cx_, cy_, cd) = pr[a], pr[b], pr[c]
                    det = (by - cy_) * (ax - cx_) + (cx_ - bx) * (ay - cy_)
                    if abs(det) < 1e-9:
                        continue
                    ymin, ymax = max(0, int(min(ay, by, cy_))), min(H - 1, int(max(ay, by, cy_)) + 1)
                    xmin, xmax = max(k * panel, int(min(ax, bx, cx_))), min((k + 1) * panel - 1, int(max(ax, bx, cx_)) + 1)
                    for py in range(ymin, ymax + 1):
                        for px in range(xmin, xmax + 1):
                            w0 = ((by - cy_) * (px + .5 - cx_) + (cx_ - bx) * (py + .5 - cy_)) / det
                            if w0 < 0:
                                continue
                            w1 = ((cy_ - ay) * (px + .5 - cx_) + (ax - cx_) * (py + .5 - cy_)) / det
                            if w1 < 0 or w0 + w1 > 1:
                                continue
                            depth = w0 * ad + w1 * bd + (1 - w0 - w1) * cd
                            idx = py * W + px
                            if depth > zbuf[idx]:
                                zbuf[idx] = depth
                                cv.px[idx * 3:idx * 3 + 3] = bytes(col)
        for py in range(H):
            idx = py * W + k * panel
            cv.px[idx * 3:idx * 3 + 3] = bytes((56, 60, 66))
    return cv.png(path), [v[3] for v in views]


def render_sign_on_mesh(sign_canvas, parts, uv_kind, path, size=(560, 760)):
    """Render the printed face as a visitor approaching along +X actually sees it, sampling the
    sign PNG through the mesh UVs. This is the check that the artwork is not mirrored."""
    W, H = size
    cv = Canvas(W, H, (34, 38, 44))
    uv_fn = sign_face_uv(uv_kind)
    zbuf = [-1e18] * (W * H)
    tris = [(v, f) for _n, (v, f) in parts]
    allv = [p for v, _f in tris for p in v]
    zs = [p[2] for p in allv]
    ys = [p[1] for p in allv]
    scale = min(W * 0.86 / (max(ys) - min(ys)), H * 0.86 / (max(zs) - min(zs)))
    cy = (max(ys) + min(ys)) / 2.0
    cz = (max(zs) + min(zs)) / 2.0
    for v, f in tris:
        for a, b, c in f:
            pts = [v[a], v[b], v[c]]
            n = cross([pts[1][i] - pts[0][i] for i in range(3)], [pts[2][i] - pts[0][i] for i in range(3)])
            if n[0] >= 0:                       # only the -X facing side is visible to the visitor
                continue
            # the visitor looks along +X; their right hand is -Y, up is +Z
            scr = [(W / 2.0 - (p[1] - cy) * scale, H / 2.0 - (p[2] - cz) * scale, p[0]) for p in pts]
            uvs = [uv_fn(p) for p in pts]
            (ax, ay, ad), (bx, by, bd), (cx_, cy_, cd) = scr
            det = (by - cy_) * (ax - cx_) + (cx_ - bx) * (ay - cy_)
            if abs(det) < 1e-9:
                continue
            ymin, ymax = max(0, int(min(ay, by, cy_))), min(H - 1, int(max(ay, by, cy_)) + 1)
            xmin, xmax = max(0, int(min(ax, bx, cx_))), min(W - 1, int(max(ax, bx, cx_)) + 1)
            for py in range(ymin, ymax + 1):
                for px in range(xmin, xmax + 1):
                    w0 = ((by - cy_) * (px + .5 - cx_) + (cx_ - bx) * (py + .5 - cy_)) / det
                    if w0 < 0:
                        continue
                    w1 = ((cy_ - ay) * (px + .5 - cx_) + (ax - cx_) * (py + .5 - cy_)) / det
                    if w1 < 0 or w0 + w1 > 1:
                        continue
                    w2 = 1.0 - w0 - w1
                    depth = -(w0 * ad + w1 * bd + w2 * cd)
                    idx = py * W + px
                    if depth <= zbuf[idx]:
                        continue
                    zbuf[idx] = depth
                    u = w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]
                    vv = w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]
                    cv.px[idx * 3:idx * 3 + 3] = bytes(sign_canvas.sample(u, vv))
    return cv.png(path)


# =====================================================================================
# 11. Export
# =====================================================================================
def export(force=False):
    manifest_path = OUT / 'geometry-manifest.json'
    if manifest_path.exists() and not force:
        raise SystemExit('Frozen generation preserved: %s exists (use --force to regenerate)' % manifest_path)
    OUT.mkdir(parents=True, exist_ok=True)
    SIGNS.mkdir(parents=True, exist_ok=True)

    # ---- signs first: a font failure must stop the run before any OBJ is written ----
    glyphs = verify_glyphs()
    signs = {}
    for key, cfg in sorted(SIGN_SET.items()):
        w, h = cfg['size']
        canvas = cfg['build'](w, h)
        png = SIGNS / ('T_GateSecurityV1_Sign_%s.png' % key)
        sha = canvas.png(png)
        preview = SIGNS / ('preview-on-mesh-%s.png' % key)
        parts = sign_post_face_parts() if cfg['form'] == 'panel' else sign_plate_face_parts()
        pv_sha = render_sign_on_mesh(canvas, parts, cfg['form'], preview)
        signs[key] = dict(file=png.name, sha256=sha, pixels=[w, h], form=cfg['form'],
                          claim=cfg['claim'], says=cfg['says'],
                          previewOnMesh=preview.name, previewOnMeshSha256=pv_sha,
                          material_role=cfg['role'])
        print('  sign %-10s %4d x %4d  %s  %s' % (key, w, h, cfg['claim'], png.name))
    (SIGNS / 'glyph-check.json').write_text(json.dumps(glyphs, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')

    # ---- geometry ----
    geo = {}
    meshes = []
    readbacks = []
    for cfg in MESHES:
        name = 'SM_GateSecurityV1_' + cfg['key']
        parts = cfg['build']()
        record = write_obj(name, parts, OUT / (name + '.obj'), cfg.get('uv'))
        record['material_role'] = cfg['role']
        record['what'] = cfg['what']
        record['claim'] = cfg['claim']
        readbacks.append(readback(OUT / record['file'], record))
        meshes.append(record)
        geo[name] = (parts, cfg['role'])
        print('  %-38s %6d tris  %-14s %s' % (name, record['triangles'], cfg['role'],
                                              'x'.join('%.0f' % (record['bounds_cm']['max'][i] - record['bounds_cm']['min'][i])
                                                       for i in range(3)) + ' cm'))
    total = sum(m['triangles'] for m in meshes)
    assert total < TRIANGLE_BUDGET, (total, TRIANGLE_BUDGET)

    preview_sha, labels = render_geometry(
        geo, OUT / 'preview-gate-security.png',
        [(0.0, 12.0, 1.55, 'front, from the approach'),
         (55.0, 22.0, 1.55, 'oblique'),
         (90.0, 12.0, 1.55, 'side')])

    manifest = dict(
        status='OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING',
        namespace=DEST,
        script='Scripts/create_gate_security.py',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        amah_cm=AMAH,
        convention=('Centimetres. Canonical Unreal axes X east, +Y south, Z up. In each mesh LOCAL '
                    'frame +X is the direction of travel through the checkpoint, +Y is the '
                    "traveller's right, and the pivot is on the floor at the footprint centre; the "
                    'placement script rotates the assembly to face each gate. OBJ carries Y '
                    'reflected and triangle winding reversed for the legacy OBJ importer (the same '
                    'adapter as create_keilim_ti_v1 / create_oldcity_facades, recorded in '
                    'SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json); the '
                    'importer reflects Y back, so imported bounds must equal bounds_cm and the '
                    'signed volume in Unreal must be positive.'),
        whatIsAsserted=dict(
            halacha=['Entering Har HaBayit in shoes is prohibited (Mishnah Berachos 9:5; Rambam, '
                     'Hilchos Beis HaBechira 7:2). The signage states this as a rule of the place.',
                     'The Mount may not be used as a shortcut, and one may not spit there '
                     '(same mishnah). Both appear on the reverence panel.'],
            modernStaging=['Metal detector arches, the bag scanner, stanchions, the booth, the guards '
                           'and the telephone rule. Modelled on the entrance procedure at the Har '
                           'HaBayit and Kotel plaza approaches TODAY. No classical source, none cited.'],
            depictedNotAsserted=['Every dimension of every object here. There is no measured drawing of '
                                 'a Jerusalem checkpoint in this project and none is claimed; the sizes '
                                 'are ordinary security-equipment sizes chosen for a 175 cm figure.',
                                 'The pictograms are drawn fresh in this file. They are not traced from '
                                 'any signage, standard or photograph.',
                                 'The trilingual wording is written for this project. It is not a '
                                 'transcription of any sign that exists.'],
            fullTable='SourceAssets/security-review/sources.md'),
        signs=signs,
        signFolder='SourceAssets/security-review/signs',
        glyphCheck='SourceAssets/security-review/signs/glyph-check.json',
        glyphCheckSummary=dict(
            fonts=[f['file'] for f in glyphs['fonts']],
            codepointsChecked=len(glyphs['glyphs']),
            missingGlyphs=glyphs['missingGlyphs'],
            emptyGlyphs=glyphs['emptyGlyphs'],
            rightToLeftPass=glyphs['rightToLeft']['pass_'],
            arabicShapingPass=glyphs['arabicShaping']['allMatch']),
        meshes=meshes,
        readback=readbacks,
        total_triangles=total,
        triangle_budget=TRIANGLE_BUDGET,
        preview='preview-gate-security.png',
        preview_sha256=preview_sha,
        preview_views=labels,
        preview_limit=('Software orthographic previews with one flat colour per material role, and one '
                       'textured render of each sign face sampled through its own UVs from the visitor '
                       "eye. Neither is a native render, a material acceptance or a lighting review."),
        limitations=[
            'Offline only. Nothing here has been imported, placed, lit or seen in the engine.',
            'Materials are named roles, not assets. release_gate_security.py resolves each role to a '
            'material on disk and records which candidate it fell to.',
            'The sign faces carry planar UVs; the frames and everything else carry the per-triangle '
            'local basis of the keilim adapter, which tiles but does not unwrap. No lightmap UVs.',
            'The belt on a stanchion is a single sagging strip modelled at one fixed span; a different '
            'span needs a different mesh or a scale on Y, which will change the sag.',
            'No collision geometry is authored. The placement script sets a collision profile per '
            'group and lets Unreal build simple collision.',
        ],
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return manifest


def _main():
    if '--export' not in sys.argv:
        raise SystemExit('Explicit --export [--force]; offline only. '
                         'Native work is in Scripts/release_gate_security.py')
    report = export(force='--force' in sys.argv)
    g = report['glyphCheckSummary']
    print('glyph check: %d codepoints, %d missing, %d empty, RTL %s, Arabic shaping %s'
          % (g['codepointsChecked'], len(g['missingGlyphs']), len(g['emptyGlyphs']),
             'PASS' if g['rightToLeftPass'] else 'FAIL',
             'PASS' if g['arabicShapingPass'] else 'FAIL'))
    print('total triangles %d of %d' % (report['total_triangles'], report['triangle_budget']))
    print('manifest %s' % (OUT / 'geometry-manifest.json'))


if __name__ == '__main__':
    _main()
