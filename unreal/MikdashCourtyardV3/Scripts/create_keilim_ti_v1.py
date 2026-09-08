"""KeilimTIV1: shulchan lechem hapanim and the golden incense altar rebuilt to the shapes of the
Machon HaMikdash (Temple Institute) vessels, at the book's dimensions.

Offline only. --export writes SourceAssets/vessels-review/KeilimTIV1/: OBJ parts, per-vessel
calibration.json, geometry-manifest.json, front/side/oblique previews and a silhouette overlay
per vessel. No engine launch, no Content/ change, no map action. Native import and placement
live in Scripts/release_import_keilim_ti.py.

WHAT THE CALIBRATION IS, AND IS NOT
-----------------------------------
calibration-shulchan.json / calibration-altar.json record proportions MEASURED IN PIXELS
off one Temple Institute gallery photograph per vessel and then normalised. This is
PHOTOGRAPH-DERIVED PROPORTION, NOT A SURVEY of the physical vessels. The photographs are
single-viewpoint studio cut-outs with residual perspective; no scale bar, no measured drawing and
no permission-to-copy of the Institute's ornament design is claimed. Every number below is a
pixel reading that a reviewer can re-take from the same file, plus arithmetic. Where the book
(Lishchno Tidreshu, and the halachic sources it cites) gives a dimension, the BOOK wins and the
photograph only supplies the shape; those conflicts are listed explicitly in each calibration file.

Reference files (SourceAssets/reference-ti/, gitignored, owners' permission for project use):
  shulchan       original-showbread-table-gallery.jpg          1500 x 1000
  incense altar  original-golden-incense-altar-gallery.jpg     1500 x 1000
Cross-checked against wiki-<hebrew>.jpg detail shots and Illustrated-Tour boards in the same
folders (dossier.md sections 2 and 3).

BOOK DIMENSIONS KEPT (SourceAssets/vessels-review/book-keilim-review-20260907.md)
  p. 241  shulchan 2 x 1 amot, 3 amot high (Yechezkel 41:22) -> 100 x 50 x 150 cm at 50 cm/amah
  p. 250  12 loaves in two stacks of six; 28 kanim (3,3,3,3,2,0 per stack); 4 snifim supports,
          5 amot (250 cm) above the floor; bazichin on the table between the stacks, 2-tefach gap
  p. 255  incense altar 1 x 1 x 2 amot at the FIVE-tefach amah -> 41.667 x 41.667 x 83.333 cm

WHAT CHANGED FROM ShulchanV2 / IncenseAltarV2
  loaves     open-box teiva perutza with a warm matte bread material (was gold-coloured boxes)
  supports   TI's forked posts with six tiers of scroll brackets and cradled half-tubes
             (was four flat 5-tefach plates, which dominated the silhouette)
  crown      modelled ovolo/bead profile swept round the rim (was a crenellated block band)
  altar      TI's fluted corner horns, fluted pilasters, arcaded cornice frieze and pierced zer
             (was a crenellated band, no horns, no frieze); carrying poles dropped - the Temple's
             golden altar has no rings or poles (dossier section 3; TI's object has none)

Conventions: centimetres. Shulchan amah 50 cm (tefach 8.3333, etzba 2.0833); incense altar amah
41.6667 cm (5 tefachim of 8.3333). Canonical axes X east, +Y south (room side), Z up; every part
of a vessel shares one bottom-centre pivot on the floor. OBJ files are written for the legacy
Unreal OBJ importer adapter proven on this project (Y reflected, triangle winding reversed; the
importer reflects Y back) - same as create_shulchan_v2 / create_sanctuary_doors, and as recorded
in SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json.
"""
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/vessels-review/KeilimTIV1'
REF = ROOT / 'SourceAssets/reference-ti'
DEST = '/Game/MikdashV3/MaterialReview/KeilimTIV1'

AMAH = 50.0
TEFACH = AMAH / 6.0
ETZBA = TEFACH / 4.0
AMAH5 = 5 * TEFACH                      # the five-tefach amah of Eruvin 4a (book p. 255)

TRIANGLE_BUDGET = 250000


# =====================================================================================
# 1. PHOTOGRAPH CALIBRATION - raw pixel readings
# =====================================================================================
# Every entry is a pixel coordinate in the named file at its native resolution, read from the
# object mask (chroma = max(R,G,B) - min(R,G,B) >= 22, which separates the gold object from the
# neutral studio gradient and from the black caption text) and from ruled crops of the same file.
# y grows downward, as in the image.

ALTAR_PX = dict(
    image='incense-altar/original-golden-incense-altar-gallery.jpg',
    image_size=[1500, 1000],
    mask_rule='chroma >= 22 within x 430..930, y 0..900',
    mask_bbox=dict(x=[494, 876], y=[24, 887]),
    mask_area_px=299744,
    horn_top_y=22,                      # highest gold pixel of the left corner horn cap
    horn_cap_bottom_y=48,               # underside of the two-step horn cap / top of the fluted shaft
    crown_teeth_top_y=76,               # top of the crenellation teeth of the pierced zer
    crown_base_y=96,                    # zer sits on the top surface = top of the cornice
    cornice_bottom_y=176,               # arcade frieze band ends, plain body begins
    base_band_top_y=847,                # flute ends / panel frame bottom; plain base band below
    base_y=888,                         # lowest gold pixel (the altar stands on a museum plinth,
                                        # which is not in the cut-out)
    body_left_x=503, body_right_x=866,
    cornice_left_x=494, cornice_right_x=876,
    horn_shaft_x=[505, 570],            # left horn fluted shaft
    horn_cap_x=[500, 583],
    pilaster_left_x=[503, 576],
    panel_outer_x=[576, 789],
    panel_field_x=[581, 784],
    flute_pitch_x=14.3, flute_count=4,
    crown_tooth_pitch_x=11.2, crown_tooth_width_x=4.5,
    arch_count_per_face=7, arch_pitch_x=52.8,
    arch_motifs='alternating grape cluster / lily, grape at both ends (7 arches, so the pattern is symmetric)',
)

SHULCHAN_PX = dict(
    image='shulchan/original-showbread-table-gallery.jpg',
    image_size=[1500, 1000],
    mask_rule='chroma >= 22 within x 250..840, y 0..900',
    mask_bbox=dict(x=[296, 779], y=[22, 884]),
    mask_area_px=195535,
    post_top_y=24,                      # top of the snifim posts (highest bracket tier above it)
    floor_y=884,                        # underside of the snif base plates and the table feet
    table_top_y=508,                    # front top edge of the table slab
    slab_bottom_y=517,                  # underside of the slab fascia = top of the bead zer
    zer_bottom_y=535,                   # bottom of the doubled bead moulding
    misgeret_bottom_y=563,              # bottom of the vine/grape frame band
    apron_bottom_y=567,
    leg_top_y=570,
    table_left_x=295, table_right_x=783,
    leg_outer_x=293, leg_inner_top_x=355, leg_inner_bottom_x=345,
    foot_band_top_y=840,
    bracket_tier_center_y=[56, 136, 226, 313, 396, 470],
    bracket_span_x=185,                 # full left-to-right reach of one bracket tier
    post_shaft_w=20,
    post_center_x=[422, 655],
    stretcher_plate_y=[735, 780],
    base_plate_y=[828, 884],
    censer_x=[430, 460], censer_y=[452, 500],
)


def altar_calibration():
    p = ALTAR_PX
    h_total = p['base_y'] - p['horn_top_y']              # 866 px, horn tip to base
    h_box = p['base_y'] - p['crown_base_y']              # 792 px, base to the burning surface
    w_body = p['body_right_x'] - p['body_left_x']        # 363 px
    def fh(y):                                          # y -> fraction of overall height, from the top
        return round((y - p['horn_top_y']) / h_total, 5)
    def fw(px_):
        return round(px_ / h_total, 5)
    rows = [
        ('overall height (horn tip to base)', 1.0, 'normaliser: %d px' % h_total),
        ('body width (below the cornice)', fw(w_body), '%d px; body height / body width = %.3f' % (w_body, h_box / w_body)),
        ('cornice (arcade frieze) width', fw(p['cornice_right_x'] - p['cornice_left_x']), 'projects %.1f px each side' % ((p['cornice_right_x'] - p['cornice_left_x'] - w_body) / 2)),
        ('horn tip', fh(p['horn_top_y']), 'top of the image object'),
        ('horn cap underside / fluted shaft top', fh(p['horn_cap_bottom_y']), 'two-step abacus above a fluted shaft'),
        ('pierced zer: top of the crenellation teeth', fh(p['crown_teeth_top_y']), ''),
        ('pierced zer base = top surface = cornice top', fh(p['crown_base_y']), 'the 2-amot book height is taken TO HERE'),
        ('cornice (arcade frieze) bottom', fh(p['cornice_bottom_y']), 'band height %.4f of overall height' % ((p['cornice_bottom_y'] - p['crown_base_y']) / h_total)),
        ('panel field bottom / base band top', fh(p['base_band_top_y']), ''),
        ('base', 1.0, ''),
        ('horn fluted shaft width', fw(p['horn_shaft_x'][1] - p['horn_shaft_x'][0]), '%.3f of the body width' % ((p['horn_shaft_x'][1] - p['horn_shaft_x'][0]) / w_body)),
        ('horn cap width', fw(p['horn_cap_x'][1] - p['horn_cap_x'][0]), '%.3f of the body width' % ((p['horn_cap_x'][1] - p['horn_cap_x'][0]) / w_body)),
        ('pilaster strip width', fw(p['pilaster_left_x'][1] - p['pilaster_left_x'][0]), '%.3f of the body width; %d flutes at %.1f px pitch' % ((p['pilaster_left_x'][1] - p['pilaster_left_x'][0]) / w_body, p['flute_count'], p['flute_pitch_x'])),
        ('recessed panel field width', fw(p['panel_field_x'][1] - p['panel_field_x'][0]), '%.3f of the body width' % ((p['panel_field_x'][1] - p['panel_field_x'][0]) / w_body)),
        ('pierced zer height', fw(p['crown_base_y'] - p['crown_teeth_top_y']), '%d teeth per face at %.1f px pitch' % (round(w_body / p['crown_tooth_pitch_x']), p['crown_tooth_pitch_x'])),
    ]
    return dict(
        vessel='golden incense altar (mizbach haketores)',
        photograph=p['image'], photograph_size=p['image_size'],
        method=('Pixel positions read from the object mask (%s) of the named file plus ruled crops of the same file. '
                'Normalised by the overall photographed height (%d px) unless a row says otherwise. '
                'PHOTOGRAPH-DERIVED PROPORTION, NOT A SURVEY: one studio viewpoint, residual perspective on the corner '
                'horns (their side faces are partly visible), no scale bar, no measured drawing.' % (p['mask_rule'], h_total)),
        normalisers=dict(overall_height_px=h_total, base_to_top_surface_px=h_box, body_width_px=w_body,
                         photographed_height_over_width=round(h_box / w_body, 4)),
        pixel_readings=p,
        proportions=[dict(feature=f, normalised=v, note=n) for f, v, n in rows],
        book_vs_photograph=[
            'Book p. 255: 1 x 1 x 2 amot at the five-tefach amah = 41.667 x 41.667 x 83.333 cm. The photographed '
            'altar is base-to-top-surface / width = %.3f, i.e. about 9%% slimmer than the book\'s 2.000. The BOOK '
            'wins: the modelled box is 41.667 wide and 83.333 high to the burning surface, so the model is slightly '
            'squatter than the photograph.' % (h_box / w_body),
            'The pierced zer and the four horns stand ABOVE the burning surface in the photograph and are modelled '
            'that way, so the model is 83.333 + %.2f cm tall overall. Reading the 2 amot to the horn tips instead '
            'would make the body 1.66:1, further from the photograph; that reading is not used.'
            % ((p['crown_base_y'] - p['horn_top_y']) / h_box * (2 * AMAH5)),
            'Rings and poles: the Temple\'s golden altar has none (dossier section 3; the Institute\'s object has '
            'none). IncenseAltarV2 modelled poles; they are dropped here.',
        ],
    )


def shulchan_calibration():
    p = SHULCHAN_PX
    h_assembly = p['floor_y'] - p['post_top_y']          # 860 px
    h_table = p['floor_y'] - p['table_top_y']            # 376 px, floor to top surface
    l_table = p['table_right_x'] - p['table_left_x']     # 488 px, front face length
    def fa(y):
        return round((y - p['post_top_y']) / h_assembly, 5)
    def fl(px_):
        return round(px_ / l_table, 5)
    tiers = p['bracket_tier_center_y']
    pitch = (tiers[-1] - tiers[0]) / (len(tiers) - 1)
    rows = [
        ('overall assembly height (post tip to floor)', 1.0, 'normaliser: %d px' % h_assembly),
        ('table top surface', fa(p['table_top_y']), 'table height / table length = %.3f' % (h_table / l_table)),
        ('slab fascia bottom', fa(p['slab_bottom_y']), 'visible slab edge %.4f of the table length' % ((p['slab_bottom_y'] - p['table_top_y']) / l_table)),
        ('bead zer (crown) bottom', fa(p['zer_bottom_y']), 'doubled bead moulding, %.4f of the table length' % ((p['zer_bottom_y'] - p['slab_bottom_y']) / l_table)),
        ('misgeret (vine/grape frame band) bottom', fa(p['misgeret_bottom_y']), '%.4f of the table length' % ((p['misgeret_bottom_y'] - p['zer_bottom_y']) / l_table)),
        ('apron bottom / legs begin', fa(p['leg_top_y']), ''),
        ('snif stretcher plate, centre', fa(sum(p['stretcher_plate_y']) / 2), ''),
        ('snif base plate, top', fa(p['base_plate_y'][0]), ''),
        ('floor', 1.0, ''),
        ('table length (front face)', 1.0, 'normaliser: %d px' % l_table),
        ('leg width at the top', fl(p['leg_inner_top_x'] - p['leg_outer_x']), 'of the table length'),
        ('leg width at the foot', fl(p['leg_inner_bottom_x'] - p['leg_outer_x']), 'of the table length; the taper is slight and the inner edge is slightly concave'),
        ('snif post shaft width', fl(p['post_shaft_w']), 'square shaft with turned knops'),
        ('bracket tier pitch', fl(pitch), '%.1f px; six tiers, the lowest at the table surface' % pitch),
        ('bracket tier full span', fl(p['bracket_span_x']), 'scroll wings reach %.4f of the table length each side of the post' % (p['bracket_span_x'] / 2 / l_table)),
    ]
    return dict(
        vessel='shulchan lechem hapanim with its snifim, kanim and loaves',
        photograph=p['image'], photograph_size=p['image_size'],
        method=('Pixel positions read from the object mask (%s) of the named file plus ruled crops of the same file. '
                'Vertical features are normalised by the overall photographed height (%d px); horizontal features and '
                'the ornament band heights by the photographed table length (%d px), which the book fixes at 2 amot. '
                'PHOTOGRAPH-DERIVED PROPORTION, NOT A SURVEY: the studio view is slightly above and to the left of the '
                'front face, so the table top is foreshortened and the two posts of each stack separate in x; the '
                'front-face readings above are taken near the centre of the front face where that error is smallest.'
                % (p['mask_rule'], h_assembly, l_table)),
        normalisers=dict(assembly_height_px=h_assembly, table_height_px=h_table, table_length_px=l_table,
                         photographed_table_height_over_length=round(h_table / l_table, 4)),
        pixel_readings=p,
        proportions=[dict(feature=f, normalised=v, note=n) for f, v, n in rows],
        book_vs_photograph=[
            'Book p. 241 (Yechezkel 41:22): the table is 2 x 1 amot and THREE amot high = 100 x 50 x 150 cm. The '
            'photographed table is height / length = %.3f, i.e. the Institute built the 1.5-amah Mishkan height of '
            'Shemos 25:23. The BOOK wins: the model is 150 cm high, so its legs are about twice as long relative to '
            'the top as in the photograph. This is the single largest deliberate departure from the photograph.'
            % (h_table / l_table),
            'Because of that, the photographed ornament band heights (slab fascia, bead zer, vine misgeret) are '
            'normalised by the TABLE LENGTH, which both sources agree is 2 amot, not by the table height.',
            'Misgeret height: Shemos 25:25 gives one tefach (8.333 cm); the photograph gives %.2f cm at a 100 cm '
            'top. The book/Torah figure is used and the photograph\'s vine ornament is fitted into it.'
            % ((p['misgeret_bottom_y'] - p['zer_bottom_y']) / l_table * 100.0),
            'Six bracket tiers at the photographed pitch (%.4f of the table length = %.2f cm) is within 2%% of two '
            'tefachim (16.667 cm), which is also the loaf wall height of Menachos 96a; two tefachim is used, and the '
            'sixth tier then lands exactly on the book\'s 5-amot (250 cm) support height of p. 250.'
            % (pitch / l_table, pitch / l_table * 100.0),
            'Loaf walls: the brief quotes "walls 7 tefachim". Book p. 241 diagram 22:6 labels 7 ETZBAOS for the gap '
            'between the karnos tabs, not a wall height; Menachos 96a (R\' Meir) folds the 10-tefach loaf as '
            '2 + 6 + 2, so the walls are 2 tefachim. That reading (already taken by ShulchanV2) is kept.',
        ],
    )


# =====================================================================================
# 2. DIMENSIONS derived from the calibration + the book
# =====================================================================================
def altar_dims():
    p, c = ALTAR_PX, altar_calibration()
    h_box_px = c['normalisers']['base_to_top_surface_px']
    w_px = c['normalisers']['body_width_px']
    W = AMAH5                                            # 41.6667 cm, book p. 255
    H = 2 * AMAH5                                        # 83.3333 cm to the burning surface
    def z(y):                                            # photo y -> model z (0 at the base)
        return (p['base_y'] - y) / h_box_px * H
    def x(px_):                                          # photo px width -> model cm
        return px_ / w_px * W
    return dict(
        width=W, height_to_surface=H,
        base_band_h=z(p['base_band_top_y']),
        cornice_bottom_z=z(p['cornice_bottom_y']),
        cornice_h=H - z(p['cornice_bottom_y']),
        cornice_projection=x((p['cornice_right_x'] - p['cornice_left_x'] - w_px) / 2),
        crown_h=z(p['crown_teeth_top_y']) - H,
        crown_teeth_per_face=int(round(w_px / p['crown_tooth_pitch_x'])),
        horn_total_h=z(p['horn_top_y']) - H,
        horn_cap_h=z(p['horn_top_y']) - z(p['horn_cap_bottom_y']),
        horn_shaft_w=x(p['horn_shaft_x'][1] - p['horn_shaft_x'][0]),
        horn_cap_w=x(p['horn_cap_x'][1] - p['horn_cap_x'][0]),
        pilaster_w=x(p['pilaster_left_x'][1] - p['pilaster_left_x'][0]),
        panel_outer_w=x(p['panel_outer_x'][1] - p['panel_outer_x'][0]),
        panel_field_w=x(p['panel_field_x'][1] - p['panel_field_x'][0]),
        flutes=p['flute_count'],
        arches=p['arch_count_per_face'],
    )


_SHULCHAN_OVERRIDE = {}


def shulchan_dims():
    p, c = SHULCHAN_PX, shulchan_calibration()
    l_px = c['normalisers']['table_length_px']
    L, W, H = 2 * AMAH, 1 * AMAH, 3 * AMAH               # book p. 241
    def cm(px_):
        return px_ / l_px * L
    d = dict(
        length=L, width=W, height=H,
        slab_h=max(3.0, cm(p['slab_bottom_y'] - p['table_top_y']) + 1.5),
        zer_h=cm(p['zer_bottom_y'] - p['slab_bottom_y']),
        misgeret_h=TEFACH,                               # Shemos 25:25
        misgeret_photo_h=cm(p['misgeret_bottom_y'] - p['zer_bottom_y']),
        leg_top_w=cm(p['leg_inner_top_x'] - p['leg_outer_x']),
        leg_foot_w=cm(p['leg_inner_bottom_x'] - p['leg_outer_x']),
        post_w=cm(p['post_shaft_w']),
        post_top_z=5 * AMAH,                             # book p. 250: supports 5 amot above the floor
        tier_pitch=2 * TEFACH,                           # = the loaf wall height; photo gives cm(82.8)
        tier_pitch_photo=cm((p['bracket_tier_center_y'][-1] - p['bracket_tier_center_y'][0]) / 5),
        bracket_reach=cm(p['bracket_span_x'] / 2),
        stretcher_z=(p['floor_y'] - sum(p['stretcher_plate_y']) / 2) / c['normalisers']['table_height_px'] * H,
        base_plate_h=cm(p['floor_y'] - p['base_plate_y'][0]),
        loaf_x=5 * TEFACH,                               # 41.667, along the table length
        loaf_base_y=6 * TEFACH,                          # 50, across the table width
        loaf_wall_h=2 * TEFACH,                          # 16.667
        loaf_dough=0.5 * TEFACH,
        karnos_gap=7 * ETZBA,
        stack_gap=2 * TEFACH,
        rod_outer=1.5, rod_inner=1.0,
        ring_major=3.5, ring_minor=0.8,
        censer_r=6.5, censer_h=22.5,
    )
    d.update(_SHULCHAN_OVERRIDE)
    return d


# =====================================================================================
# 3. Geometry primitives (all closed, outward-wound)
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


def box(center, size):
    hx, hy, hz = [s / 2.0 for s in size]
    cx, cy, cz = center
    v = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    f = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),
         (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),
         (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return orient(v, f)


def prism(polygon, z0, z1):
    """Vertical prism over a simple CCW polygon [(x, y), ...]."""
    n = len(polygon)
    v = [(x, y, z0) for x, y in polygon] + [(x, y, z1) for x, y in polygon]
    f = []
    for i in range(n):
        j = (i + 1) % n
        f += [(i, j, n + j), (i, n + j, n + i)]
    for i in range(1, n - 1):                            # fans; polygon must be convex-ish/star-shaped from 0
        f += [(0, i, i + 1), (n, n + i + 1, n + i)]
    return orient(v, f)


def plate(polygon, y0, y1):
    """Prism over a polygon in the XZ plane, extruded along Y (a flat bracket/leaf plate)."""
    n = len(polygon)
    v = [(x, y0, z) for x, z in polygon] + [(x, y1, z) for x, z in polygon]
    f = []
    for i in range(n):
        j = (i + 1) % n
        f += [(i, j, n + j), (i, n + j, n + i)]
    for i in range(1, n - 1):
        f += [(0, i, i + 1), (n, n + i + 1, n + i)]
    return orient(v, f)


def rect_sweep(center_xy, half_x, half_y, z0, profile):
    """Sweep a CLOSED cross-section [(outward_offset, dz), ...] around a rectangle: mouldings,
    cornices, plinths, bead crowns. Genus-1 closed surface, 8 triangles per profile segment."""
    cx, cy = center_xy
    n = len(profile)
    assert n >= 3
    v = []
    for dr, dz in profile:
        hx, hy = half_x + dr, half_y + dr
        assert hx > 0 and hy > 0, 'rect_sweep profile collapses the rectangle'
        v += [(cx - hx, cy - hy, z0 + dz), (cx + hx, cy - hy, z0 + dz),
              (cx + hx, cy + hy, z0 + dz), (cx - hx, cy + hy, z0 + dz)]
    f = []
    for i in range(n):
        j = (i + 1) % n
        for k in range(4):
            l = (k + 1) % 4
            f += [(i * 4 + k, i * 4 + l, j * 4 + l), (i * 4 + k, j * 4 + l, j * 4 + k)]
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
    top = len(sections) - 1
    for i in range(1, m - 1):
        f += [(0, i, i + 1), (top * m, top * m + i + 1, top * m + i)]
    return orient(v, f)


def torus(center, major, minor, axis='z', sm=20, sn=8):
    v = []
    for i in range(sm):
        a = i * math.tau / sm
        for j in range(sn):
            b = j * math.tau / sn
            r = major + minor * math.cos(b)
            u, w, hgt = r * math.cos(a), r * math.sin(a), minor * math.sin(b)
            p = (u, w, hgt) if axis == 'z' else ((u, hgt, w) if axis == 'y' else (hgt, u, w))
            v.append(tuple(center[k] + p[k] for k in range(3)))
    f = []
    for i in range(sm):
        for j in range(sn):
            a = i * sn + j
            b = ((i + 1) % sm) * sn + j
            c = ((i + 1) % sm) * sn + (j + 1) % sn
            d = i * sn + (j + 1) % sn
            f += [(a, c, b), (a, d, c)]
    return orient(v, f)


def revolve(profile, center, segments=24):
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


def tube_along(points, radius, segments=8, normal=(0.0, 1.0, 0.0)):
    """Round-section tube swept along a 3-D polyline; capped. Used for vine scrolls, tendrils and
    the interlaced stem of the altar panel."""
    pts = [p for i, p in enumerate(points) if i == 0 or any(abs(p[k] - points[i - 1][k]) > 1e-9 for k in range(3))]
    assert len(pts) >= 2
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = [pts[1][k] - p[k] for k in range(3)]
        elif i == len(pts) - 1:
            t = [p[k] - pts[-2][k] for k in range(3)]
        else:
            t = [pts[i + 1][k] - pts[i - 1][k] for k in range(3)]
        tl = math.sqrt(sum(x * x for x in t)) or 1.0
        t = [x / tl for x in t]
        u = cross(t, normal)
        ul = math.sqrt(sum(x * x for x in u))
        if ul < 1e-6:
            u = cross(t, (0.0, 0.0, 1.0))
            ul = math.sqrt(sum(x * x for x in u)) or 1.0
        u = [x / ul for x in u]
        w = cross(t, u)
        rings.append([tuple(p[k] + radius * (math.cos(a) * u[k] + math.sin(a) * w[k]) for k in range(3))
                      for a in [s * math.tau / segments for s in range(segments)]])
    v = [q for ring in rings for q in ring]
    f = []
    for s in range(len(rings) - 1):
        a0, b0 = s * segments, (s + 1) * segments
        for i in range(segments):
            j = (i + 1) % segments
            f += [(a0 + i, a0 + j, b0 + j), (a0 + i, b0 + j, b0 + i)]
    for i in range(1, segments - 1):
        f += [(0, i, i + 1)]
    last = (len(rings) - 1) * segments
    for i in range(1, segments - 1):
        f += [(last, last + i + 1, last + i)]
    return orient(v, f)


def half_tube(center, length, r_out, r_in, segments=8):
    """Half of a hollow tube - a split reed - running along Y, convex side up, closed shell.
    The half-annulus cap is triangulated as quads (a fan from one corner would be degenerate)."""
    cx, cy, cz = center
    outer = [(r_out * math.cos(t * math.pi / segments), r_out * math.sin(t * math.pi / segments)) for t in range(segments + 1)]
    inner = [(r_in * math.cos(t * math.pi / segments), r_in * math.sin(t * math.pi / segments)) for t in range(segments, -1, -1)]
    poly = outer + inner
    n = len(poly)
    v = []
    for y in (cy - length / 2.0, cy + length / 2.0):
        v += [(cx + x, y, cz + z) for x, z in poly]
    f = []
    for i in range(n):
        j = (i + 1) % n
        f += [(i, j, n + j), (i, n + j, n + i)]
    m = segments + 1
    for t in range(segments):
        o0, o1 = t, t + 1
        i1, i0 = m + (segments - t - 1), m + (segments - t)
        f += [(o0, o1, i1), (o0, i1, i0)]
        f += [(n + o0, n + i1, n + o1), (n + o0, n + i0, n + i1)]
    return orient(v, f)


def sphere(center, r, sm=8, sn=5):
    prof = [(0.0, -r)] + [(r * math.sin(math.pi * k / sn), -r * math.cos(math.pi * k / sn)) for k in range(1, sn)] + [(0.0, r)]
    return revolve(prof, center, sm)


# =====================================================================================
# 4. The golden incense altar
# =====================================================================================
def altar_parts(tune):
    d = altar_dims()
    W = d['width']
    H = d['height_to_surface']
    hw = W / 2.0
    parts = []
    add = lambda n, g: parts.append((n, g))

    base_h = d['base_band_h']
    corn_z = d['cornice_bottom_z']
    corn_h = d['cornice_h']
    proj = d['cornice_projection'] * tune['cornice_projection']
    pil_w = d['pilaster_w'] * tune['pilaster_w']
    panel_w = d['panel_field_w']
    panel_frame = (d['panel_outer_w'] - panel_w) / 2.0

    # --- body: a plain box from the base to the underside of the cornice
    add('Body', box((0, 0, corn_z / 2.0), (W, W, corn_z)))
    # base band: slight plinth projection at the foot
    add('BasePlinth', rect_sweep((0, 0), hw, hw, 0.0, [(0.0, 0.0), (0.45, 0.0), (0.45, base_h - 0.6), (0.0, base_h)]))

    # --- pilaster strips with flutes, at both edges of all four faces
    pz0, pz1 = base_h, corn_z
    for axis in (0, 1):
        for s in (-1, 1):
            for e in (-1, 1):
                cxy = [0.0, 0.0]
                cxy[axis] = s * (hw + 0.30)
                cxy[1 - axis] = e * (hw - pil_w / 2.0)
                size = [0.0, 0.0, pz1 - pz0]
                size[axis] = 0.60
                size[1 - axis] = pil_w
                add('Pilaster_%d%d%d' % (axis, s > 0, e > 0), box((cxy[0], cxy[1], (pz0 + pz1) / 2.0), size))
                for k in range(d['flutes']):
                    off = (k + 0.5 - d['flutes'] / 2.0) * (pil_w / d['flutes'])
                    fc = [0.0, 0.0]
                    fc[axis] = s * (hw + 0.62)
                    fc[1 - axis] = e * (hw - pil_w / 2.0) + off
                    fs = [0.0, 0.0, pz1 - pz0 - 2.2]
                    fs[axis] = 0.34
                    fs[1 - axis] = pil_w / d['flutes'] * 0.42
                    add('Flute_%d%d%d_%d' % (axis, s > 0, e > 0, k), box((fc[0], fc[1], (pz0 + pz1) / 2.0), fs))

    # --- recessed panel: a raised frame around a field carrying the lily/tendril stem
    fz0, fz1 = base_h + 1.2, corn_z - 1.2
    for axis in (0, 1):
        for s in (-1, 1):
            # frame: four bars around the field
            for bi, (lw, lh, lo, vo) in enumerate(((panel_w + 2 * panel_frame, panel_frame, 0.0, (fz1 - fz0) / 2.0 - panel_frame / 2.0),
                                                   (panel_w + 2 * panel_frame, panel_frame, 0.0, -(fz1 - fz0) / 2.0 + panel_frame / 2.0),
                                                   (panel_frame, fz1 - fz0, panel_w / 2.0 + panel_frame / 2.0, 0.0),
                                                   (panel_frame, fz1 - fz0, -(panel_w / 2.0 + panel_frame / 2.0), 0.0))):
                c = [0.0, 0.0]
                c[axis] = s * (hw + 0.28)
                c[1 - axis] = lo
                sz = [0.0, 0.0, lh]
                sz[axis] = 0.56
                sz[1 - axis] = lw
                add('PanelFrame_%d%d_%d' % (axis, s > 0, bi), box((c[0], c[1], (fz0 + fz1) / 2.0 + vo), sz))
            parts.extend(altar_panel_motif(axis, s, hw, fz0 + 2.0, fz1 - 2.0, panel_w - 2.0))

    # --- cornice: arcade frieze band with a moulded top and bottom rail
    add('Cornice', rect_sweep((0, 0), hw, hw, corn_z,
                              [(0.0, 0.0), (proj * 0.35, 0.6), (proj, 1.6), (proj, corn_h - 1.2),
                               (proj * 0.5, corn_h), (0.0, corn_h)]))
    arch_pitch = W / d['arches']
    for axis in (0, 1):
        for s in (-1, 1):
            for k in range(d['arches']):
                off = (k + 0.5 - d['arches'] / 2.0) * arch_pitch
                c = [0.0, 0.0]
                c[axis] = s * (hw + proj + 0.10)
                c[1 - axis] = off
                zc = corn_z + corn_h / 2.0 + 0.1
                add('Arch_%d%d_%d' % (axis, s > 0, k),
                    torus((c[0], c[1], zc), arch_pitch * 0.40, 0.42, 'x' if axis == 0 else 'y', 18, 6))
                if k % 2 == 0:                            # grape cluster
                    for gi, (gx, gz) in enumerate([(0, 0.9), (-0.62, 0.25), (0.62, 0.25), (-0.32, -0.45), (0.32, -0.45), (0, -1.1)]):
                        gc = [0.0, 0.0]
                        gc[axis] = s * (hw + proj + 0.25)
                        gc[1 - axis] = off + gx * arch_pitch * 0.20
                        add('Grape_%d%d_%d_%d' % (axis, s > 0, k, gi),
                            sphere((gc[0], gc[1], zc + gz * arch_pitch * 0.19), arch_pitch * 0.075, 7, 4))
                else:                                     # lily / fleur
                    for pi, (dx, dz, ln) in enumerate([(0.0, 0.0, 1.0), (-0.55, -0.15, 0.78), (0.55, -0.15, 0.78)]):
                        pc = [0.0, 0.0]
                        pc[axis] = s * (hw + proj + 0.22)
                        pc[1 - axis] = off + dx * arch_pitch * 0.20
                        pts = [(pc[0], pc[1], zc + (dz - 0.75) * arch_pitch * 0.22),
                               (pc[0], pc[1], zc + (dz + 0.10) * arch_pitch * 0.22),
                               (pc[0] + (dx * 0.5 * arch_pitch * 0.14 if axis == 1 else 0.0),
                                pc[1] + (dx * 0.5 * arch_pitch * 0.14 if axis == 0 else 0.0),
                                zc + (dz + 0.55 * ln) * arch_pitch * 0.22)]
                        add('Lily_%d%d_%d_%d' % (axis, s > 0, k, pi), tube_along(pts, arch_pitch * 0.055, 6))

    # --- top surface with the shallow central hollow for the coals
    add('TopSurface', box((0, 0, H - 0.9), (W, W, 1.8)))
    hollow = W * 0.34
    add('HollowRim', rect_sweep((0, 0), hollow / 2.0, hollow / 2.0, H - 0.5,
                                [(0.0, 0.0), (0.9, 0.0), (0.9, 0.5), (0.0, 0.5)]))

    # --- pierced zer: bottom rail, uprights (the piercings are the gaps), top rail, teeth
    cz0 = H
    crown_h = d['crown_h'] * tune['crown_h']
    rail = crown_h * 0.20
    inset = 0.6
    add('CrownRailLower', rect_sweep((0, 0), hw - inset, hw - inset, cz0,
                                     [(0.0, 0.0), (0.55, 0.0), (0.55, rail), (0.0, rail)]))
    add('CrownRailUpper', rect_sweep((0, 0), hw - inset, hw - inset, cz0 + crown_h - 2 * rail,
                                     [(0.0, 0.0), (0.55, 0.0), (0.55, rail), (0.0, rail)]))
    n_teeth = d['crown_teeth_per_face']
    pitch = W / n_teeth
    for axis in (0, 1):
        for s in (-1, 1):
            for k in range(n_teeth):
                off = (k + 0.5 - n_teeth / 2.0) * pitch
                if abs(off) > hw - inset - pitch * 0.5:
                    continue
                c = [0.0, 0.0]
                c[axis] = s * (hw - inset + 0.27)
                c[1 - axis] = off
                sz = [0.0, 0.0, crown_h - 3 * rail]
                sz[axis] = 0.54
                sz[1 - axis] = pitch * 0.40
                add('CrownPost_%d%d_%d' % (axis, s > 0, k), box((c[0], c[1], cz0 + rail + (crown_h - 3 * rail) / 2.0), sz))
                sz2 = list(sz)
                sz2[2] = rail * 1.1
                add('CrownTooth_%d%d_%d' % (axis, s > 0, k), box((c[0], c[1], cz0 + crown_h - rail * 0.45), sz2))

    # --- four fluted corner horns on the cornice
    hs = d['horn_shaft_w'] * tune['horn_shaft_w']
    hc = d['horn_cap_w'] * tune['horn_cap_w']
    shaft_h = d['horn_total_h'] - d['horn_cap_h']
    cap_h = d['horn_cap_h']
    ho = hw + proj - hc / 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * ho, sy * ho
            add('HornShaft_%d%d' % (sx > 0, sy > 0), box((cx, cy, H + shaft_h / 2.0), (hs, hs, shaft_h)))
            for axis in (0, 1):
                for s in (-1, 1):
                    for k in range(4):
                        off = (k + 0.5 - 2.0) * (hs / 4.0)
                        fc = [cx, cy]
                        fc[axis] += s * (hs / 2.0 + 0.16)
                        fc[1 - axis] += off
                        fs = [0.0, 0.0, shaft_h * 0.74]
                        fs[axis] = 0.30
                        fs[1 - axis] = hs / 4.0 * 0.42
                        add('HornFlute_%d%d_%d%d_%d' % (sx > 0, sy > 0, axis, s > 0, k),
                            box((fc[0], fc[1], H + shaft_h * 0.50), fs))
            add('HornCapLower_%d%d' % (sx > 0, sy > 0), box((cx, cy, H + shaft_h + cap_h * 0.30), (hc, hc, cap_h * 0.60)))
            add('HornCapUpper_%d%d' % (sx > 0, sy > 0), box((cx, cy, H + shaft_h + cap_h * 0.80), (hc * 0.82, hc * 0.82, cap_h * 0.40)))
    return parts


def altar_panel_motif(axis, s, hw, z0, z1, width):
    """The Institute's panel relief: two lobed leaves and a medallion at the top, a figure-of-eight
    interlace of tendrils, a lily at the centre and a knot at the foot. Modelled as round-section
    tendrils and shallow lobes, not traced from the photograph."""
    out = []
    h = z1 - z0
    depth = 0.75
    def P(u, t):
        """u across the panel (-1..1), t up the panel (0..1) -> world point on the face."""
        c = [0.0, 0.0]
        c[axis] = s * (hw + depth)
        c[1 - axis] = u * width / 2.0
        return (c[0], c[1], z0 + t * h)
    tag = '%d%d' % (axis, s > 0)
    r = width * 0.030

    # medallion near the top
    out.append(('Medallion_' + tag, torus(P(0.0, 0.845), width * 0.085, width * 0.028,
                                          'x' if axis == 0 else 'y', 16, 6)))
    out.append(('MedallionBoss_' + tag, sphere(P(0.0, 0.845), width * 0.045, 8, 5)))
    # two lobed leaves sweeping up and out
    for sgn in (-1, 1):
        pts = [P(0.0, 0.60), P(sgn * 0.18, 0.70), P(sgn * 0.48, 0.80), P(sgn * 0.62, 0.90), P(sgn * 0.50, 0.955), P(sgn * 0.26, 0.95)]
        out.append(('Leaf_%s_%d' % (tag, sgn > 0), tube_along(pts, r * 1.5, 7)))
        pts2 = [P(sgn * 0.10, 0.66), P(sgn * 0.34, 0.755), P(sgn * 0.50, 0.855), P(sgn * 0.44, 0.925)]
        out.append(('LeafInner_%s_%d' % (tag, sgn > 0), tube_along(pts2, r * 1.0, 6)))
    # figure-of-eight interlace: two mirrored ogee tendrils crossing at mid height
    for sgn in (-1, 1):
        pts = []
        for k in range(23):
            t = k / 22.0
            tt = 0.62 - t * 0.50                          # 0.62 down to 0.12
            u = sgn * 0.42 * math.sin(math.pi * t) * (1.0 if t < 0.5 else 1.0)
            u += sgn * 0.10 * math.sin(2 * math.pi * t)
            pts.append(P(u, tt))
        out.append(('Tendril_%s_%d' % (tag, sgn > 0), tube_along(pts, r, 7)))
        hook = [P(sgn * 0.30, 0.585), P(sgn * 0.38, 0.615), P(sgn * 0.33, 0.645), P(sgn * 0.25, 0.632)]
        out.append(('TendrilHook_%s_%d' % (tag, sgn > 0), tube_along(hook, r * 0.8, 6)))
    # central lily
    out.append(('LilyBud_' + tag, revolve([(0.0, -width * 0.10), (width * 0.055, -width * 0.05),
                                           (width * 0.062, 0.0), (width * 0.040, width * 0.06),
                                           (0.0, width * 0.10)], P(0.0, 0.365), 14)))
    for sgn in (-1, 1):
        pts = [P(0.0, 0.395), P(sgn * 0.13, 0.435), P(sgn * 0.20, 0.485)]
        out.append(('LilyPetal_%s_%d' % (tag, sgn > 0), tube_along(pts, r * 0.9, 6)))
    out.append(('LilyStem_' + tag, tube_along([P(0.0, 0.30), P(0.0, 0.50)], r * 0.7, 6)))
    # knot at the foot
    for sgn in (-1, 1):
        pts = []
        for k in range(19):
            t = k / 18.0
            a = t * math.tau
            out_u = sgn * (0.10 + 0.20 * math.cos(a))
            out_t = 0.075 + 0.055 * math.sin(a)
            pts.append(P(out_u, out_t))
        out.append(('Knot_%s_%d' % (tag, sgn > 0), tube_along(pts, r * 0.95, 7)))
    out.append(('KnotStem_' + tag, tube_along([P(0.0, 0.055), P(0.0, 0.30)], r * 0.9, 6)))
    return out


# =====================================================================================
# 5. The shulchan
# =====================================================================================
def stack_centers(d):
    return [-(d['loaf_x'] + d['stack_gap']) / 2.0, (d['loaf_x'] + d['stack_gap']) / 2.0]


def tier_z(d):
    return [d['height'] + k * d['tier_pitch'] for k in range(6)]


def rod_offsets():
    """(x offset from the stack centre, tier index) for the 14 kanim of one stack: the book's
    3, 3, 3, 3, 2, 0 (p. 250; Menachos 97a). Tier 0 (the table surface) carries none: the first
    loaf lies on the table."""
    out = []
    for tier, count in enumerate([0, 3, 3, 3, 3, 2]):
        xs = [-13.9, 0.0, 13.9] if count == 3 else ([-8.5, 8.5] if count == 2 else [])
        out += [(x, tier) for x in xs]
    return out


def shulchan_table_parts(tune):
    d = shulchan_dims()
    L, W, H = d['length'], d['width'], d['height']
    parts = []
    add = lambda n, g: parts.append((n, g))
    slab = d['slab_h']
    zer = d['zer_h'] * tune['zer_h']
    mis = d['misgeret_h']

    # top board
    add('TopSlab', box((0, 0, H - slab / 2.0), (L, W, slab)))
    # zer: a MODELLED PROFILE (cavetto - bead - bead - fillet) swept round the rim, as the
    # Institute's doubled bead moulding under the slab edge. Not a crenellated band.
    b = zer / 2.0
    prof = [(0.0, 0.0)]
    prof += [(0.30 + 0.62 * math.sin(math.pi * k / 8.0), b * k / 8.0) for k in range(1, 9)]
    prof += [(0.30 + 0.62 * math.sin(math.pi * k / 8.0), b + b * k / 8.0) for k in range(1, 9)]
    prof += [(0.20, zer + 0.35), (0.0, zer + 0.35)]
    add('ZerProfile', rect_sweep((0, 0), L / 2.0 - 0.2, W / 2.0 - 0.2, H - slab - zer - 0.35, prof))

    # misgeret: one-tefach frame below the slab, inset, carrying the vine
    inset = 1.6
    mz = H - slab - zer - 0.35 - mis
    add('Misgeret', rect_sweep((0, 0), L / 2.0 - inset, W / 2.0 - inset, mz,
                               [(0.0, 0.0), (0.9, 0.35), (0.9, mis - 0.35), (0.0, mis)]))
    add('MisgeretRail', rect_sweep((0, 0), L / 2.0 - inset, W / 2.0 - inset, mz - 1.1,
                                   [(0.0, 0.0), (1.15, 0.15), (1.15, 1.0), (0.0, 1.1)]))
    # vine scroll + grape clusters on the misgeret faces (the Institute's vocabulary, drawn fresh)
    for axis, half, span in ((0, L / 2.0 - inset + 0.9, W - 2 * inset), (1, W / 2.0 - inset + 0.9, L - 2 * inset)):
        for s in (-1, 1):
            n_wave = 8 if axis == 1 else 4
            pts = []
            steps = n_wave * 8
            for k in range(steps + 1):
                t = k / steps
                u = (t - 0.5) * span * 0.94
                zz = mz + mis / 2.0 + math.sin(t * n_wave * math.tau) * mis * 0.26
                c = [0.0, 0.0]
                c[axis] = s * half
                c[1 - axis] = u
                pts.append((c[0], c[1], zz))
            add('Vine_%d%d' % (axis, s > 0), tube_along(pts, 0.45, 6))
            for w in range(n_wave):
                u = ((w + 0.5) / n_wave - 0.5) * span * 0.94
                c = [0.0, 0.0]
                c[axis] = s * (half + 0.35)
                c[1 - axis] = u
                for gi, (gx, gz) in enumerate([(0.0, 0.30), (-0.55, -0.05), (0.55, -0.05), (-0.28, -0.55), (0.28, -0.55), (0.0, -1.05)]):
                    gc = list(c)
                    gc[1 - axis] += gx * mis * 0.13
                    add('Grape_%d%d_%d_%d' % (axis, s > 0, w, gi),
                        sphere((gc[0], gc[1], mz + mis * 0.42 + gz * mis * 0.14), mis * 0.055, 7, 4))

    # legs: TI's broad tapered pilasters, outer faces flush with the top, slightly concave inner edge
    lt = d['leg_top_w'] * tune['leg_top_w']
    lb = d['leg_foot_w'] * tune['leg_top_w']
    leg_top_z = mz - 1.1
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * (L / 2.0 - lt / 2.0)
            cy = sy * (W / 2.0 - lt / 2.0)
            secs = []
            for k in range(7):
                t = k / 6.0
                z = t * leg_top_z
                # width: wide at the top, waisted, slightly wider at the foot block
                w_ = lb + (lt - lb) * (t ** 1.35) - (lt - lb) * 0.22 * math.sin(math.pi * t)
                hx = w_ / 2.0
                # keep the OUTER faces flush and take the taper on the inner faces (as photographed)
                ox = sx * (L / 2.0 - w_ / 2.0)
                oy = sy * (W / 2.0 - w_ / 2.0)
                secs.append(([(ox - hx, oy - hx), (ox + hx, oy - hx), (ox + hx, oy + hx), (ox - hx, oy + hx)], z))
            add('Leg_%d%d' % (sx > 0, sy > 0), loft(secs))
            add('LegFoot_%d%d' % (sx > 0, sy > 0), box((sx * (L / 2.0 - lb / 2.0), sy * (W / 2.0 - lb / 2.0), 1.6), (lb + 1.6, lb + 1.6, 3.2)))
            # wheat-ear relief on the two outer faces
            for axis, sgn in ((0, sx), (1, sy)):
                half = (L / 2.0 if axis == 0 else W / 2.0)
                for e in range(7):
                    t = 0.20 + e * 0.085
                    c = [0.0, 0.0]
                    c[axis] = sgn * (half + 0.28)
                    c[1 - axis] = (cy if axis == 0 else cx) + (0.0)
                    zz = leg_top_z * (0.18 + e * 0.075)
                    add('Wheat_%d%d_%d%d_%d' % (sx > 0, sy > 0, axis, sgn > 0, e),
                        sphere((c[0], c[1], zz), 0.95, 6, 4))
                stem = [(0.0, 0.0), (0.0, 0.0)]
                c = [0.0, 0.0]
                c[axis] = sgn * (half + 0.20)
                c[1 - axis] = (cy if axis == 0 else cx)
                add('WheatStem_%d%d_%d%d' % (sx > 0, sy > 0, axis, sgn > 0),
                    tube_along([(c[0], c[1], leg_top_z * 0.14), (c[0], c[1], leg_top_z * 0.70)], 0.42, 6))
    return parts


def shulchan_ring_parts():
    d = shulchan_dims()
    L, W, H = d['length'], d['width'], d['height']
    mz = H - d['slab_h'] - d['zer_h'] - 0.35 - d['misgeret_h']
    z = mz + d['misgeret_h'] / 2.0
    reach = d['ring_major'] + d['ring_minor']
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(('Ring_%d%d' % (sx > 0, sy > 0),
                        torus((sx * (L / 2.0 - d['leg_top_w'] / 2.0), sy * (W / 2.0 + reach - 0.6), z),
                              d['ring_major'], d['ring_minor'], 'x', 20, 8)))
    return out


def bracket_outline(reach, height):
    """Half of a scroll bracket in the XZ plane (x from 0 outward), as the Institute's acanthus
    'ksavos': a rising volute with a lobed underside. Returned as a star-shaped polygon."""
    top = height * 0.5
    pts = [(0.0, -top * 0.55)]
    for k in range(11):                                   # lobed underside, dipping outward
        t = k / 10.0
        x = reach * t
        z = -top * (0.55 - 0.28 * math.sin(math.pi * t) - 0.15 * t)
        pts.append((x, z))
    pts.append((reach, top * 0.10))
    for k in range(9):                                    # volute curl at the outer end
        a = -math.pi * 0.5 + k / 8.0 * math.pi * 1.35
        pts.append((reach * (0.86 + 0.14 * math.cos(a)) - reach * 0.02,
                    top * (0.42 + 0.40 * math.sin(a))))
    for k in range(10, -1, -1):                           # top edge back to the post
        t = k / 10.0
        x = reach * t * 0.84
        z = top * (0.30 + 0.55 * (1.0 - t) ** 0.8 - 0.18 * math.sin(math.pi * t))
        pts.append((x, z))
    seen, clean = set(), []
    for p in pts:
        k = (round(p[0], 4), round(p[1], 4))
        if k not in seen:
            seen.add(k)
            clean.append(p)
    return clean


def shulchan_snifim_parts(tune):
    d = shulchan_dims()
    W = d['width']
    post_y = W / 2.0 + 8.0
    pw = d['post_w'] * tune['post_w']
    reach = d['bracket_reach'] * tune['bracket_reach']
    top = d['post_top_z']
    tiers = tier_z(d)
    out = []
    add = lambda n, g: out.append((n, g))
    for si, cx in enumerate(stack_centers(d)):
        for sy in (-1, 1):
            cy = sy * post_y
            tag = '%d%d' % (si, sy > 0)
            # base plate on the floor: moulded plate, long in X, shallow in Y (keeps the north-wall clearance)
            bh = d['base_plate_h']
            add('SnifBase_' + tag, rect_sweep((cx, cy), reach * 0.62, 6.0, 0.0,
                                              [(0.0, 0.0), (1.1, 0.0), (1.1, bh * 0.55), (0.0, bh)]))
            add('SnifBaseTop_' + tag, box((cx, cy, bh + 1.0), (reach * 1.05, 10.0, 2.0)))
            for sgn in (-1, 1):                            # scroll ends of the base plate
                add('SnifBaseScroll_%s_%d' % (tag, sgn > 0),
                    torus((cx + sgn * reach * 0.55, cy, bh * 0.55), 2.6, 1.0, 'y', 14, 6))
            # stretcher plate part way up
            sz = d['stretcher_z']
            add('SnifStretcher_' + tag, box((cx, cy, sz), (reach * 1.05, 4.0, 3.4)))
            add('SnifStretcherRail_' + tag, box((cx, cy, sz + 2.3), (reach * 1.15, 5.0, 1.2)))
            # square shaft with turned knops
            add('SnifShaft_' + tag, box((cx, cy, top / 2.0 + 1.0), (pw, pw, top - 2.0)))
            for k in range(9):
                zz = 6.0 + k * (top - 12.0) / 8.0
                add('SnifKnop_%s_%d' % (tag, k), revolve([(0.0, -pw * 0.42), (pw * 0.78, -pw * 0.12),
                                                          (pw * 0.80, pw * 0.10), (0.0, pw * 0.45)],
                                                         (cx, cy, zz), 12))
            # six tiers of forked scroll brackets, wings both sides of the post
            for t, z in enumerate(tiers):
                for sgn in (-1, 1):
                    poly = [(sgn * x, zz + d['tier_pitch'] * tune['bracket_z']) for x, zz
                            in bracket_outline(reach, d['tier_pitch'] * tune['bracket_h'])]
                    if sgn < 0:
                        poly = poly[::-1]
                    add('Bracket_%s_%d_%d' % (tag, t, sgn > 0), plate([(cx + x, z + zz) for x, zz in poly], cy - 1.1, cy + 1.1))
                add('BracketCollar_%s_%d' % (tag, t), box((cx, cy, z - d['tier_pitch'] * 0.12), (pw * 1.5, pw * 1.5, d['tier_pitch'] * 0.22)))
            # cradle prongs at the kanim seats
            for n, (x, tier) in enumerate(rod_offsets()):
                z = tiers[tier]
                for sgn in (-1, 1):
                    add('Prong_%s_%02d_%d' % (tag, n, sgn > 0),
                        box((cx + x + sgn * (d['rod_outer'] + 0.35), cy, z + d['rod_outer'] * 0.55), (0.7, 2.2, d['rod_outer'] * 1.5)))
    return out


def shulchan_kanim_parts():
    """28 half-tubes (split reeds), convex side up, running north-south between the two posts."""
    d = shulchan_dims()
    length = 2 * (d['width'] / 2.0 + 8.0) + d['post_w']
    ro, ri = d['rod_outer'], d['rod_inner']
    tiers = tier_z(d)
    out = []
    for si, cx in enumerate(stack_centers(d)):
        for n, (x, tier) in enumerate(rod_offsets()):
            out.append(('Kaneh_%d_%02d' % (si, n), half_tube((cx + x, 0.0, tiers[tier]), length, ro, ri, 8)))
    return out


def loaf_parts(stack_index):
    """Teiva perutza: the 10 x 5 tefach loaf of Menachos 96a folded 2 + 6 + 2, so it reads as an
    open box of bread - a flat cake with two upstanding walls carrying the karnos tabs."""
    d = shulchan_dims()
    cx = stack_centers(d)[stack_index]
    dough = d['loaf_dough']
    wall = d['loaf_wall_h']
    tab = (d['loaf_x'] - d['karnos_gap']) / 2.0
    out = []
    for k, z0 in enumerate(tier_z(d)):
        tag = 'Loaf%d' % (k + 1)
        # slightly domed base so it reads as baked bread rather than a plate
        secs = []
        for j in range(5):
            t = j / 4.0
            hx = d['loaf_x'] / 2.0 - 0.9 * (t ** 2)
            hy = d['loaf_base_y'] / 2.0 - 0.9 * (t ** 2)
            secs.append(([(cx - hx, -hy), (cx + hx, -hy), (cx + hx, hy), (cx - hx, hy)], z0 + t * dough))
        out.append(('%s_Base' % tag, loft(secs)))
        for sy in (-1, 1):
            y = sy * (d['loaf_base_y'] / 2.0 - dough / 2.0)
            for sx in (-1, 1):
                out.append(('%s_Karn_%d_%d' % (tag, sy > 0, sx > 0),
                            box((cx + sx * (d['loaf_x'] / 2.0 - tab / 2.0), y, z0 + dough + wall / 2.0), (tab, dough, wall))))
            out.append(('%s_Wall_%d' % (tag, sy > 0),
                        box((cx, y, z0 + dough + (wall - 1.6) / 2.0), (d['karnos_gap'] + 1.0, dough, wall - 1.6))))
    return out


def bazichin_parts():
    d = shulchan_dims()
    r, h = d['censer_r'], d['censer_h']
    prof = [(0, 0), (4.8, 0), (5.0, 0.8), (3.8, 1.3), (1.6, 1.8), (1.6, 5.0), (2.4, 6.0), (4.8, 8.0), (r, 11.0),
            (r, 13.6), (r - 0.3, 14.0), (r - 0.1, 14.6), (5.6, 16.4), (4.2, 18.4), (2.4, 19.6), (1.1, 20.2),
            (1.1, 21.6), (0.9, 22.0), (0, h)]
    return [('Bazich_%d' % (sy > 0), revolve(prof, (0.0, sy * 12.0, d['height']), 20)) for sy in (-1, 1)]


# =====================================================================================
# 6. Assemblies
# =====================================================================================
TUNE_ALTAR_BASE = dict(cornice_projection=1.0, pilaster_w=1.0, crown_h=1.0, horn_shaft_w=1.0, horn_cap_w=1.0)
TUNE_SHULCHAN_BASE = dict(zer_h=1.0, leg_top_w=1.0, post_w=1.0, bracket_reach=1.0,
                          bracket_h=0.95, bracket_z=0.0)

# Refinement schedule. Iteration 0 is the raw photograph calibration; 1 and 2 adjust only the
# parameters the calibration leaves loose (the photograph shows a corner, so widths that face the
# camera obliquely are the uncertain ones). Every iteration is scored against the photograph
# silhouette and all scores are recorded; the best-scoring iteration is exported.
ALTAR_ITERATIONS = [
    dict(name='iter0-raw-calibration', **TUNE_ALTAR_BASE),
    dict(name='iter1-wider-horns-and-cornice', **dict(TUNE_ALTAR_BASE, horn_cap_w=1.10, horn_shaft_w=1.06, cornice_projection=1.25)),
    dict(name='iter2-tall-crown', **dict(TUNE_ALTAR_BASE, horn_cap_w=1.10, horn_shaft_w=1.06, cornice_projection=1.25, crown_h=1.20)),
]
SHULCHAN_ITERATIONS = [
    dict(name='iter0-raw-calibration', **TUNE_SHULCHAN_BASE),
    dict(name='iter1-wider-legs-and-brackets', **dict(TUNE_SHULCHAN_BASE, leg_top_w=1.15, bracket_reach=1.10)),
    dict(name='iter2-heavier-posts', **dict(TUNE_SHULCHAN_BASE, leg_top_w=1.15, bracket_reach=1.10, post_w=1.25, zer_h=1.10)),
    dict(name='iter3-thin-bracket-band-and-lift', **dict(TUNE_SHULCHAN_BASE, leg_top_w=1.15, bracket_reach=1.10,
                                                         post_w=1.25, zer_h=1.10, bracket_h=0.60, bracket_z=0.45)),
    dict(name='iter4-calibrated-band-with-lift', **dict(TUNE_SHULCHAN_BASE, leg_top_w=1.15, bracket_reach=1.10,
                                                        post_w=1.30, zer_h=1.10, bracket_h=0.95, bracket_z=0.42)),
]
REFINEMENT_STOP = (
    'The sweep continued past iter4. Further IoU was available only by widening the snif posts to about 9 cm and the '
    'bracket wings to about 24 cm - roughly twice and 1.25 times the values measured off the photograph. Those gains '
    'come from filling the vertical gaps between the modelled bracket tiers, which in the photograph are filled by the '
    'SECOND post of each pair seen in perspective, not by wider parts. Fitting them would be fitting a viewpoint '
    'artefact, so the refinement was stopped at the calibrated widths.'
)


def altar_geometry(tune):
    return {'SM_KeilimTIV1_IncenseAltar': altar_parts(tune)}


def shulchan_geometry(tune):
    return {
        'SM_KeilimTIV1_Shulchan_Table': shulchan_table_parts(tune),
        'SM_KeilimTIV1_Shulchan_Rings': shulchan_ring_parts(),
        'SM_KeilimTIV1_Shulchan_Snifim': shulchan_snifim_parts(tune),
        'SM_KeilimTIV1_Shulchan_Kanim': shulchan_kanim_parts(),
        'SM_KeilimTIV1_Shulchan_LoavesWest': loaf_parts(0),
        'SM_KeilimTIV1_Shulchan_LoavesEast': loaf_parts(1),
        'SM_KeilimTIV1_Shulchan_Bazichin': bazichin_parts(),
    }


MATERIAL_ROLE = {
    'SM_KeilimTIV1_Shulchan_LoavesWest': 'bread',
    'SM_KeilimTIV1_Shulchan_LoavesEast': 'bread',
}


# =====================================================================================
# 7. Photograph silhouette and the overlap score
# =====================================================================================
def _bmp_of(rel_path):
    """Convert a reference JPEG to a temporary 24-bit BMP with System.Drawing. Nothing derived
    from the photograph is written into the repository."""
    src = REF / rel_path
    if not src.exists():
        raise SystemExit('reference photograph missing: %s' % src)
    cache = Path(tempfile.gettempdir()) / 'keilim-ti-photomask'
    cache.mkdir(parents=True, exist_ok=True)
    dst = cache / (hashlib.sha256(str(src).encode('utf-8')).hexdigest()[:16] + '.bmp')
    if not dst.exists():
        ps = ("Add-Type -AssemblyName System.Drawing; "
              "$i=[System.Drawing.Image]::FromFile('%s'); "
              "$b=New-Object System.Drawing.Bitmap $i.Width,$i.Height,([System.Drawing.Imaging.PixelFormat]::Format24bppRgb); "
              "$g=[System.Drawing.Graphics]::FromImage($b); $g.DrawImage($i,0,0,$i.Width,$i.Height); "
              "$b.Save('%s',[System.Drawing.Imaging.ImageFormat]::Bmp); $g.Dispose();$b.Dispose();$i.Dispose()"
              % (str(src).replace("'", "''"), str(dst).replace("'", "''")))
        subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return dst


def photo_mask(rel_path, window, chroma=22):
    """Threshold the photograph: chroma separates the gold object from the neutral studio gradient,
    its drop shadow and the black caption text. Returns (mask rows, bbox, area)."""
    data = _bmp_of(rel_path).read_bytes()
    off = struct.unpack_from('<I', data, 10)[0]
    w, hh = struct.unpack_from('<ii', data, 18)
    bpp = struct.unpack_from('<H', data, 28)[0]
    assert bpp == 24, bpp
    flip, h = hh > 0, abs(hh)
    stride = ((w * 3 + 3) // 4) * 4
    x0, x1, y0, y1 = window
    x1, y1 = min(x1, w), min(y1, h)
    rows = []
    xmin, xmax, ymin, ymax, area = 10 ** 9, -1, 10 ** 9, -1, 0
    for y in range(y0, y1):
        sy = (h - 1 - y) if flip else y
        base = off + sy * stride
        row = bytearray(x1 - x0)
        for x in range(x0, x1):
            b, g, r = data[base + x * 3], data[base + x * 3 + 1], data[base + x * 3 + 2]
            if max(r, g, b) - min(r, g, b) >= chroma:
                row[x - x0] = 1
                area += 1
                if x < xmin: xmin = x
                if x > xmax: xmax = x
                if y < ymin: ymin = y
                if y > ymax: ymax = y
        rows.append(row)
    return dict(rows=rows, window=[x0, x1, y0, y1], bbox=[xmin, ymin, xmax, ymax], area=area, size=[w, h])


def model_silhouette(geo, yaw, pitch, grid):
    """Orthographic binary silhouette of the assembly, rasterised into a grid of `grid` columns,
    auto-fitted to its own bounding box. Returns (mask rows, width, height)."""
    u = (math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cam = (-u[0] * cp, -u[1] * cp, -sp)
    right = cross((0.0, 0.0, 1.0), cam)
    rl = math.sqrt(sum(x * x for x in right)) or 1.0
    right = [x / rl for x in right]
    up = cross(cam, right)
    tris = []
    xs, zs = [], []
    for parts in geo.values():
        for _, (v, f) in parts:
            proj = [(sum(p[i] * right[i] for i in range(3)), sum(p[i] * up[i] for i in range(3))) for p in v]
            for a, b, c in f:
                tris.append((proj[a], proj[b], proj[c]))
            for sx, sz in proj:
                xs.append(sx)
                zs.append(sz)
    minx, maxx, minz, maxz = min(xs), max(xs), min(zs), max(zs)
    scale = (grid - 1) / max(maxx - minx, 1e-6)
    height = max(2, int(round((maxz - minz) * scale)) + 1)
    rows = [bytearray(grid) for _ in range(height)]
    for (ax, az), (bx, bz), (cx_, cz) in tris:
        px = [(ax - minx) * scale, (bx - minx) * scale, (cx_ - minx) * scale]
        py = [(maxz - az) * scale, (maxz - bz) * scale, (maxz - cz) * scale]
        det = (py[1] - py[2]) * (px[0] - px[2]) + (px[2] - px[1]) * (py[0] - py[2])
        if abs(det) < 1e-9:
            continue
        y0 = max(0, int(min(py)))
        y1 = min(height - 1, int(max(py)) + 1)
        x0 = max(0, int(min(px)))
        x1 = min(grid - 1, int(max(px)) + 1)
        for yy in range(y0, y1 + 1):
            row = rows[yy]
            for xx in range(x0, x1 + 1):
                w0 = ((py[1] - py[2]) * (xx + .5 - px[2]) + (px[2] - px[1]) * (yy + .5 - py[2])) / det
                if w0 < -1e-9:
                    continue
                w1 = ((py[2] - py[0]) * (xx + .5 - px[2]) + (px[0] - px[2]) * (yy + .5 - py[2])) / det
                if w1 < -1e-9 or w0 + w1 > 1 + 1e-9:
                    continue
                row[xx] = 1
    return rows, grid, height


def silhouette_score(geo, view, photo, grid=200, meshes=None):
    """Bounding-box aligned intersection over union between the model's orthographic silhouette and
    the thresholded photograph. Both masks are resampled onto one grid whose columns span the
    respective bounding boxes, so the comparison is of SHAPE and PROPORTION only, not of size or
    position in frame."""
    sub = geo if meshes is None else {k: v for k, v in geo.items() if k in meshes}
    rows, mw, mh = model_silhouette(sub, view[0], view[1], grid)
    px0, py0, px1, py1 = photo['bbox']
    pw, ph = px1 - px0 + 1, py1 - py0 + 1
    # common grid: `grid` columns, rows scaled by the PHOTOGRAPH's aspect (the model is stretched to
    # the photograph's bounding box, which is what "align by bounding box" means)
    gh = max(2, int(round(grid * ph / pw)))
    a = [bytearray(grid) for _ in range(gh)]
    b = [bytearray(grid) for _ in range(gh)]
    wx, wy = photo['window'][0], photo['window'][2]
    for j in range(gh):
        ry = a[j]
        rb = b[j]
        my = min(mh - 1, int(j * mh / gh))
        mrow = rows[my]
        pyy = py0 + int(j * ph / gh)
        prow = photo['rows'][pyy - wy]
        for i in range(grid):
            ry[i] = mrow[min(mw - 1, int(i * mw / grid))]
            rb[i] = prow[px0 + int(i * pw / grid) - wx]
    inter = union = 0
    for j in range(gh):
        ra, rb = a[j], b[j]
        for i in range(grid):
            if ra[i] and rb[i]:
                inter += 1
                union += 1
            elif ra[i] or rb[i]:
                union += 1
    return dict(iou=round(inter / union, 4) if union else 0.0, intersection_px=inter, union_px=union,
                grid=[grid, gh], model_only_px=sum(sum(1 for i in range(grid) if a[j][i] and not b[j][i]) for j in range(gh)),
                photo_only_px=sum(sum(1 for i in range(grid) if b[j][i] and not a[j][i]) for j in range(gh))), a, b


def write_overlay(path, a, b, title_rows=0):
    """Model silhouette vs photograph silhouette: red = photograph only, yellow = model only,
    warm grey = both. Only the binary outlines are drawn; no photographic content is stored."""
    gh, gw = len(a), len(a[0])
    scale = max(1, 900 // max(gw, gh))
    W, H = gw * scale, gh * scale
    rgb = bytearray([18, 20, 24] * (W * H))
    for j in range(gh):
        for i in range(gw):
            m, p = a[j][i], b[j][i]
            if not (m or p):
                continue
            col = (206, 176, 108) if (m and p) else ((196, 66, 60) if p else (232, 214, 90))
            for yy in range(j * scale, (j + 1) * scale):
                base = (yy * W + i * scale) * 3
                for xx in range(scale):
                    rgb[base + xx * 3:base + xx * 3 + 3] = bytes(col)
    _png(path, rgb, W, H)


def _png(path, rgb, W, H):
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    scan = b''.join(b'\x00' + bytes(rgb[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', W, H, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(scan, 9)) + chunk(b'IEND', b''))


# =====================================================================================
# 8. Preview renders
# =====================================================================================
def render_views(geo, path, views, size):
    W, H = size
    rgb = bytearray([22, 25, 30] * (W * H))
    zbuf = [-1e18] * (W * H)
    cols = len(views)
    panel = W // cols
    for k, (yaw, pitch, scale, _label) in enumerate(views):
        u = (math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
        cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        cam = (-u[0] * cp, -u[1] * cp, -sp)
        right = cross((0.0, 0.0, 1.0), cam)
        rl = math.sqrt(sum(x * x for x in right)) or 1.0
        right = [x / rl for x in right]
        up = cross(cam, right)
        x0 = k * panel + panel / 2.0
        base_y = H - 40
        light = (-0.35, -0.62, 0.70)
        for mesh, parts in geo.items():
            colour = (168, 112, 62) if MATERIAL_ROLE.get(mesh) == 'bread' else (216, 172, 82)
            for _, (v, f) in parts:
                pr = [(sum(p[i] * right[i] for i in range(3)) * scale + x0,
                       base_y - sum(p[i] * up[i] for i in range(3)) * scale,
                       -sum(p[i] * cam[i] for i in range(3))) for p in v]
                for a, b, c in f:
                    pa, pb, pc = v[a], v[b], v[c]
                    n = cross([pb[i] - pa[i] for i in range(3)], [pc[i] - pa[i] for i in range(3)])
                    ln = math.sqrt(sum(x * x for x in n)) or 1.0
                    shade = 0.40 + 0.60 * max(0.0, sum(n[i] * light[i] for i in range(3)) / ln)
                    col = bytes(min(255, int(x * shade)) for x in colour)
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
                                rgb[idx * 3:idx * 3 + 3] = col
        for py in range(H):
            idx = py * W + k * panel
            rgb[idx * 3:idx * 3 + 3] = bytes((58, 62, 68))
    _png(path, rgb, W, H)
    return [v[3] for v in views]


# =====================================================================================
# 9. OBJ export and readback
# =====================================================================================
def write_obj(name, parts, path):
    lines = ['# KeilimTIV1 %s; Unreal legacy OBJ adapter (Y reflected, winding reversed)' % name, 'o ' + name]
    index = 1
    allv = []
    checks = []
    for part, (vertices, faces) in parts:
        vol = volume(vertices, faces)
        assert vol > 0, 'inverted part ' + part
        assert closed(vertices, faces), 'open part ' + part
        allv.extend(vertices)
        lines.append('g ' + part)
        for a, b, c in faces:
            p, q, r = [(vertices[i][0], -vertices[i][1], vertices[i][2]) for i in (a, c, b)]
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            length = math.sqrt(sum(x * x for x in ab))
            nl = math.sqrt(sum(x * x for x in n))
            assert nl > 1e-8 and length > 1e-8, 'degenerate triangle in ' + part
            for vv in (p, q, r):
                lines.append('v %.6f %.6f %.6f' % vv)
            for uv in ((0, 0), (length / 10, 0), (sum(ac[i] * ab[i] / length for i in range(3)) / 10, nl / length / 10)):
                lines.append('vt %.6f %.6f' % uv)
            for _ in range(3):
                lines.append('vn %.6f %.6f %.6f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
        checks.append(dict(name=part, triangles=len(faces), closed=True, volume_cm3=round(vol, 4)))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(p[i] for p in allv) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    return dict(name=name, file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                triangles=(index - 1) // 3, parts=len(parts), material_role=MATERIAL_ROLE.get(name, 'gold'),
                bounds_cm=bounds, minimum_part_signed_volume_cm3=min(c['volume_cm3'] for c in checks),
                part_checks_sample=checks[:6], part_count=len(checks))


def readback(path, record):
    verts, normals, faces = [], [], []
    for line in path.read_text().splitlines():
        c = line.split()
        if not c:
            continue
        if c[0] == 'v':
            verts.append(tuple(map(float, c[1:])))
        elif c[0] == 'vn':
            normals.append(tuple(map(float, c[1:])))
        elif c[0] == 'f':
            faces.append([tuple(int(x) - 1 for x in t.split('/')) for t in c[1:]])
    assert len(faces) == record['triangles']
    worst = 0.0
    for face in faces:
        assert len(face) == 3
        a, b, c = [verts[t[0]] for t in face]
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cr = cross(ab, ac)
        area = math.sqrt(sum(x * x for x in cr))
        assert area > 1e-9
        dot = sum(cr[i] * normals[face[0][2]][i] for i in range(3)) / area
        worst = max(worst, abs(1.0 - dot))
    assert worst < 1e-4, worst
    canonical = [(x, -y, z) for x, y, z in verts]
    bounds = {k: [fn(v[i] for v in canonical) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    err = max(abs(bounds[k][i] - record['bounds_cm'][k][i]) for k in bounds for i in range(3))
    assert err < 1e-4, err
    fv = volume(verts, [tuple(t[0] for t in face) for face in faces])
    assert fv > 0, 'adapter sign unexpected for ' + path.name
    return dict(mesh=record['name'], triangles=len(faces), bounds_error_cm=round(err, 9),
                worst_normal_error=round(worst, 9), file_space_signed_volume_cm3=round(fv, 3),
                normals_and_uvs='PASS')


# =====================================================================================
# 10. Export
# =====================================================================================
VESSELS = {
    'shulchan': dict(
        label='shulchan lechem hapanim',
        build=shulchan_geometry, iterations=SHULCHAN_ITERATIONS, calibration=shulchan_calibration,
        photo=SHULCHAN_PX['image'], window=[250, 840, 0, 900],
        score_view=(0.0, 0.0),
        score_meshes=['SM_KeilimTIV1_Shulchan_Table', 'SM_KeilimTIV1_Shulchan_Rings',
                      'SM_KeilimTIV1_Shulchan_Snifim', 'SM_KeilimTIV1_Shulchan_Kanim',
                      'SM_KeilimTIV1_Shulchan_Bazichin'],
        score_meshes_note=('The Institute photographs the table WITHOUT bread on it, so the score compares the '
                           'GOLD METALWORK only (table, rings, snifim, kanim, bazichin). The twelve loaves are '
                           'excluded from the silhouette; scoring them against an empty frame would measure the '
                           'absence of bread, not the shape of the vessel. The full-assembly score is reported '
                           'separately as a diagnostic.'),
        views=[(0.0, 0.0, 2.45, 'front (south elevation, looking north; east to the right)'),
               (90.0, 0.0, 2.45, 'side (east elevation, looking west; north to the right)'),
               (33.0, 24.0, 2.15, 'oblique from the south-east above')],
        preview='keilim-ti-shulchan-preview.png', overlay='keilim-ti-shulchan-silhouette.png',
        overlay_shape='keilim-ti-shulchan-silhouette-tiheight.png',
        shape_variant=dict(
            override=dict(height=1.5 * AMAH, post_top_z=175.0),
            note=('Diagnostic only, never exported: the same model rebuilt at the height the Institute actually '
                  'built (1.5 amot, Shemos 25:23) with the supports scaled to match. It separates SHAPE fidelity '
                  'from the deliberate dimensional departure of the three-amah table of the book, and it is the score '
                  'the refinement iterations were driven by.'),
        ),
        preview_size=(1500, 760),
    ),
    'altar': dict(
        label='golden incense altar',
        build=altar_geometry, iterations=ALTAR_ITERATIONS, calibration=altar_calibration,
        photo=ALTAR_PX['image'], window=[430, 930, 0, 900],
        score_view=(0.0, 0.0),
        views=[(0.0, 0.0, 5.6, 'front (south elevation, looking north)'),
               (90.0, 0.0, 5.6, 'side (east elevation, looking west)'),
               (35.0, 22.0, 5.0, 'oblique from the south-east above')],
        preview='keilim-ti-altar-preview.png', overlay='keilim-ti-altar-silhouette.png',
        preview_size=(1400, 760),
    ),
}


def export(force=False, groups=('shulchan', 'altar')):
    manifest_path = OUT / 'geometry-manifest.json'
    if manifest_path.exists() and not force:
        raise SystemExit('Frozen generation preserved: %s exists (use --force to regenerate)' % manifest_path)
    OUT.mkdir(parents=True, exist_ok=True)
    vessels = {}
    meshes = []
    readbacks = []
    for key in groups:
        cfg = VESSELS[key]
        photo = photo_mask(cfg['photo'], cfg['window'])
        variant = cfg.get('shape_variant')
        iters = []
        best = None
        for it in cfg['iterations']:
            tune = {k: v for k, v in it.items() if k != 'name'}
            geo = cfg['build'](tune)
            built, a, b = silhouette_score(geo, cfg['score_view'], photo, meshes=cfg.get('score_meshes'))
            tris = sum(len(f) for parts in geo.values() for _, (_v, f) in parts)
            rec = dict(iteration=it['name'], tuning=tune, triangles=tris, as_built=built)
            target, pair = built['iou'], (a, b)
            spair = None
            if variant:
                _SHULCHAN_OVERRIDE.clear()
                _SHULCHAN_OVERRIDE.update(variant['override'])
                try:
                    shape, sa, sb = silhouette_score(cfg['build'](tune), cfg['score_view'], photo,
                                                     meshes=cfg.get('score_meshes'))
                finally:
                    _SHULCHAN_OVERRIDE.clear()
                rec['shape_variant'] = shape
                target, spair = shape['iou'], (sa, sb)
            iters.append(rec)
            print('  %-9s %-36s as-built IoU %.4f   scored IoU %.4f   (%d tris)'
                  % (key, it['name'], built['iou'], target, tris))
            if best is None or target > best[0]:
                best = (target, rec, geo, pair, spair, tune)
        target, rec, geo, pair, spair, tune = best
        write_overlay(OUT / cfg['overlay'], *pair)
        if spair:
            write_overlay(OUT / cfg['overlay_shape'], *spair)
        cal = cfg['calibration']()
        cal['silhouette_overlap'] = dict(
            method=('Both silhouettes are reduced to binary masks, each stretched to its own bounding box on a common '
                    '%d-column grid (the photograph fixes the grid aspect), then intersection over union. '
                    'This scores SHAPE AND PROPORTION only. It is not a fidelity measure of ornament, and the '
                    'photograph is a slightly oblique studio view, so a perfectly frontal model cannot reach 1.0.'
                    % rec['as_built']['grid'][0]),
            photograph=cfg['photo'],
            photograph_mask=dict(bbox=photo['bbox'], area_px=photo['area'], rule=SHULCHAN_PX['mask_rule'] if key == 'shulchan' else ALTAR_PX['mask_rule']),
            meshes_scored=cfg.get('score_meshes', 'all'),
            meshes_scored_note=cfg.get('score_meshes_note', ''),
            shape_variant_note=(variant or {}).get('note', 'not used for this vessel'),
            refinement_stopped_because=REFINEMENT_STOP if key == 'shulchan' else
                'The altar reached %.4f at iteration 0 from the raw calibration; the two later iterations moved it by '
                'less than 0.001, so the raw calibration is kept unless a later iteration wins outright.' % iters[0]['as_built']['iou'],
            iterations=iters, best=rec['iteration'],
            best_as_built_iou=rec['as_built']['iou'],
            best_shape_variant_iou=rec.get('shape_variant', {}).get('iou'),
            overlay=cfg['overlay'], overlay_shape_variant=cfg.get('overlay_shape'),
        )
        (OUT / ('calibration-%s.json' % key)).write_text(json.dumps(cal, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        for name, parts in geo.items():
            r = write_obj(name, parts, OUT / (name + '.obj'))
            r['vessel'] = key
            readbacks.append(readback(OUT / r['file'], r))
            meshes.append(r)
        labels = render_views(geo, OUT / cfg['preview'], cfg['views'], cfg['preview_size'])
        vessels[key] = dict(label=cfg['label'], tuning=tune, best_iteration=rec['iteration'],
                            as_built_iou=rec['as_built']['iou'],
                            shape_variant_iou=rec.get('shape_variant', {}).get('iou'),
                            iterations=iters, calibration_file='calibration-%s.json' % key,
                            preview=cfg['preview'], preview_views=labels, overlay=cfg['overlay'],
                            overlay_shape_variant=cfg.get('overlay_shape'),
                            meshes=list(geo), triangles=rec['triangles'])
    total = sum(m['triangles'] for m in meshes)
    assert total < TRIANGLE_BUDGET, (total, TRIANGLE_BUDGET)
    d_s, d_a = shulchan_dims(), altar_dims()
    manifest = dict(
        status='OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING', namespace=DEST,
        script='Scripts/create_keilim_ti_v1.py',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        amah_cm=AMAH, tefach_cm=TEFACH, etzba_cm=ETZBA, five_tefach_amah_cm=AMAH5,
        convention=('Canonical Unreal cm: X east, +Y south (room side), Z up; one bottom-centre pivot on the floor '
                    'for every part of a vessel. OBJ carries Y reflected and triangle winding reversed for the legacy '
                    'OBJ importer (same adapter as create_shulchan_v2 / create_sanctuary_doors and as recorded in '
                    'SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json); the importer reflects Y '
                    'back, so imported bounds must equal bounds_cm and UE signed volumes must be positive.'),
        reference=dict(
            folder='SourceAssets/reference-ti (gitignored; owners\' permission for project use, not for redistribution)',
            note=('Nothing derived from the photographs is written into the repository: the silhouette overlays are '
                  'binary masks of the thresholded outline only, produced at export time from a temporary BMP that is '
                  'left in the system temp folder, never in SourceAssets.'),
        ),
        shulchan_dimensions_cm={k: (round(v, 4) if isinstance(v, float) else v) for k, v in d_s.items()},
        altar_dimensions_cm={k: (round(v, 4) if isinstance(v, float) else v) for k, v in d_a.items()},
        book_dimensions_kept=[
            'shulchan 2 x 1 amot, 3 amot high (p. 241, Yechezkel 41:22) = 100 x 50 x 150 cm at 50 cm/amah',
            'twelve loaves in two stacks of six; 28 kanim as 3,3,3,3,2,0 per stack; four snifim; supports 5 amot '
            '(250 cm) above the floor; bazichin between the stacks with a 2-tefach gap (p. 250)',
            'incense altar 1 x 1 x 2 amot at the five-tefach amah (p. 255, Eruvin 4a) = 41.667 x 41.667 x 83.333 cm '
            'to the burning surface',
            'misgeret one tefach (Shemos 25:25); four rings at the legs against the misgeret (Shemos 25:26-27)',
        ],
        departures=[
            'The Institute built the 1.5-amah table of Shemos 25:23; the book takes Yechezkel 41:22 as three amot. '
            'The model is 150 cm high, so its legs are roughly twice as long relative to the top as in the '
            'photograph. This is the largest single difference and it is deliberate.',
            'The photographed altar is 2.18 : 1 base-to-surface over width; the book gives exactly 2 : 1. The model '
            'follows the book and is therefore about 9 per cent squatter than the photograph.',
            'The incense altar carries no rings and no poles (dossier section 3; the Institute\'s object has none). '
            'IncenseAltarV2 modelled poles and they are dropped.',
            'Ornament is drawn fresh in the Institute\'s vocabulary (vine and grape misgeret band, wheat-ear legs, '
            'acanthus scroll brackets, arcaded frieze of alternating grape clusters and lilies, lily-and-tendril '
            'panel stem, pierced crenellated zer). It is NOT traced, scanned or photogrammetrically copied from the '
            'photographs, and it is an interpretation, not a claim about the Temple vessels.',
            'The loaf walls are two tefachim with a seven-ETZBA karnos gap (book p. 241 diagram 22:6; Menachos 96a '
            'folds the 10-tefach loaf as 2 + 6 + 2). The brief\'s "walls 7 tefachim" reads the diagram label as '
            'tefachim; it is etzbaos.',
            'Six bracket tiers are modelled as photographed. The lowest tier is level with the table surface and '
            'carries no kaneh, because the first loaf of each stack lies on the table itself (p. 250).',
        ],
        vessels=vessels, total_triangles=total, triangle_budget=TRIANGLE_BUDGET,
        meshes=meshes, readback=readbacks,
        preview_limit=('Software orthographic previews with two illustrative flat colours (gold / bread). Not a '
                       'native render, not a material or lighting acceptance.'),
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return manifest


def _main():
    if '--export' not in sys.argv:
        raise SystemExit('Explicit --export [--force] [--groups=shulchan,altar]; offline only. '
                         'Native work is in Scripts/release_import_keilim_ti.py')
    groups = ('shulchan', 'altar')
    for a in sys.argv[1:]:
        if a.startswith('--groups='):
            groups = tuple(x.strip() for x in a.split('=', 1)[1].split(',') if x.strip())
    for g in groups:
        assert g in VESSELS, g
    report = export(force='--force' in sys.argv, groups=groups)
    for m in report['meshes']:
        print('%-40s %7d tris  %s' % (m['name'], m['triangles'], m['material_role']))
    print('total triangles', report['total_triangles'], 'of', report['triangle_budget'])
    for k, v in report['vessels'].items():
        print('%-9s best %-36s as-built IoU %.4f  shape-variant IoU %s'
              % (k, v['best_iteration'], v['as_built_iou'], v['shape_variant_iou']))


if __name__ == '__main__':
    _main()
