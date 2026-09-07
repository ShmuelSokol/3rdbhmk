"""Assemble SourceAssets/third-party/<slug>/ folders from downloaded files in _dl/.
Each folder gets: original mesh, converted OBJ(s), LICENSE.txt, provenance.json, preview image.
Run: python build_assets.py            (all assets)
     python build_assets.py slug ...   (subset)
"""
import os, sys, json, hashlib, shutil, datetime
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DL = os.path.join(ROOT, '_dl')
sys.path.insert(0, HERE)
import mesh_convert as mc


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def tri_stats(tris):
    v = tris.reshape(-1, 3); mn = v.min(0); mx = v.max(0)
    return {'triangles': int(len(tris)), 'bboxMin': mn.round(4).tolist(), 'bboxMax': mx.round(4).tolist(), 'size': (mx - mn).round(4).tolist()}


def rebase(tris):
    mn = tris.reshape(-1, 3).min(0); mx = tris.reshape(-1, 3).max(0)
    return tris - np.array([(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]])


NOW = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
CC_BY4 = ('Creative Commons Attribution 4.0 International (CC BY 4.0)', 'https://creativecommons.org/licenses/by/4.0/')
GPL3 = ('GNU General Public License v3.0 (GPL-3.0) - NOT a Creative Commons license; flagged for user decision', 'https://www.gnu.org/licenses/gpl-3.0.html')

ASSETS = [
 dict(slug='menorah-temple-matankic-wikimedia', src='wm-menorah.stl', dst='Menorah.stl', preview='prev/wm-menorah-thumb.png',
      title='Menorah.stl - 3D printable model of the Menorah at the Temple in Jerusalem', author='Matankic (Wikimedia Commons user)',
      sourceUrl='https://commons.wikimedia.org/wiki/File:Menorah.stl', fileUrl='https://upload.wikimedia.org/wikipedia/commons/a/a3/Menorah.stl',
      licenseName='Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)', licenseUrl='https://creativecommons.org/licenses/by-sa/4.0/',
      unitsGuess='arbitrary Blender units (Blender 2.80 export); model is 11.02 units tall',
      targetCm={'height': 150},
      notes='Seven straight diagonal branches with knops (spheres), calyx cups and flower rims, hemispherical base; Rambam-style silhouette. Low-medium detail (16.7k tris), no textures. Uploaded 2020-06-19, "own work".'),
 dict(slug='menorah-titus-dahan-meir-printables', src='p1501834-menorah.stl', dst='menorah.stl', preview='prev/p1501834_0.png',
      title='The Menorah in the Temple in Jerusalem - based on the structure from the Arch of Triumph (Titus) in Rome', author='Dahan Meir (Printables user)',
      sourceUrl='https://www.printables.com/model/1501834-the-menorah-in-the-temple-in-jerusalem-based-on-th', fileUrl='Printables file id 6318696 (menorah.stl) via getDownloadLink API',
      licenseName=CC_BY4[0], licenseUrl=CC_BY4[1],
      unitsGuess='millimetres (3D-print STL, 209.8 mm tall incl. hexagonal stepped base)',
      targetCm={'height': 150},
      notes='Arch-of-Titus style: seven rounded arms with knop rings, two-tier hexagonal base. Medium detail (75k tris). Published 2025-12-03. Printables license field: "Creative Commons - Attribution".'),
 dict(slug='kohen-gadol-dahan-meir-printables', src='p1492176-High_jew_cohen_rep_by_prusa_X_collapse_EDges_sculp_density_dynpoto.stl', dst='high_priest.stl', preview='prev/p1492176_0.png', rebase=True,
      title='The High Priest who works in the Temple in Jerusalem (Kohen Gadol figure)', author='Dahan Meir (Printables user)',
      sourceUrl='https://www.printables.com/model/1492176-the-high-priest-who-works-in-the-temple-in-jerusal', fileUrl='Printables file id 6279128 via getDownloadLink API',
      licenseName=CC_BY4[0], licenseUrl=CC_BY4[1],
      unitsGuess='millimetres (figure 73.7 mm tall)',
      targetCm={'height': 175},
      notes='Standing bearded figure in robe with belt/sash, breastplate (choshen) on chest, turban (mitznefet) with forehead plate (tzitz). Sculpt quality moderate (73.6k tris, remeshed). Static pose, no rig, no textures. The OBJ was re-based (XY centred, feet at Z=0); the original STL is offset about 110 mm in -X. Published 2025-11-24.'),
 dict(slug='aron-ark-box-davidgra11-thingiverse', src='tv7391849-ark.3mf', dst='ark_of_the_covenant_flie.3mf', preview='prev/tv7391849_Screenshot_2026-08-04_115614.png', is3mf=True, itemNames={0: 'ark_box_with_poles', 1: 'ark_lid_with_keruvim'},
      title='Ark of the Covenant Box', author='davidgra11 (Thingiverse user; same design on Printables as "David graubart 11")',
      sourceUrl='https://www.thingiverse.com/thing:7391849', fileUrl='https://tv-zip.thingiverse.com/zip/7391849 (Thingiverse thing zip; LICENSE.txt inside states "licensed under cc-sa")',
      licenseName='Creative Commons Attribution-ShareAlike (Thingiverse license code "cc-sa"; version not stated in the zip - Thingiverse currently links CC BY-SA 4.0)', licenseUrl='https://creativecommons.org/licenses/by-sa/4.0/',
      unitsGuess='millimetres (3MF unit="millimeter", Bambu Studio 2.05 project; box+poles 54 x 123 x 49 mm, lid 46 x 82 x 38 mm)',
      targetCm={'bodyLength': 125, 'bodyWidth': 75, 'bodyHeight': 75},
      notes='Ornate box with carved panels, four rings and two carrying poles (poles along the long axis), separate lid (kaporet) with two kneeling winged keruvim facing each other. Designed as a storage box: lid has an inner lip. Two build items -> two OBJs: ark_box_with_poles and ark_lid_with_keruvim; each OBJ is re-based (XY centred, bottom at Z=0) because the 3MF stores them side-by-side on a print plate. High poly (715k + 287k tris). NOTE: the same author lists this model on Printables (model 1800658) as CC BY-NC; the Thingiverse copy carries CC BY-SA - keep this provenance with the asset. Published 2026-08.'),
 dict(slug='shulchan-showbread-soxfanjr-printables', src='p297007-table-of-showbread.stl', dst='table-of-showbread.stl', preview='prev/p297007_1.png',
      title='Table Of Showbread from Tabernacle', author='SoxfanJr (Printables user)',
      sourceUrl='https://www.printables.com/model/297007-table-of-showbread-from-tabernacle', fileUrl='https://files.printables.com/media/prints/297007/stls/2602699_81e8e834-aafe-4f64-9638-23a1b9e3291d/table-of-showbread.stl',
      licenseName='Creative Commons Zero 1.0 Universal / Public Domain Dedication (CC0 1.0) - Printables label "Creative Commons - Public Domain"', licenseUrl='https://creativecommons.org/publicdomain/zero/1.0/',
      unitsGuess='millimetres (Fusion 360 export; 30.7 x 80 x 40 mm)',
      targetCm={'length': 100, 'width': 50, 'height': 150},
      notes='Very crude placeholder: four-leg table, zigzag end frames, two short rods. 716 tris. No loaves. Only included because it is CC0; expect to replace or use as blockout only. Proportions do not match the book (needs non-uniform scaling).'),
 dict(slug='aron-ark-pazzah-mishkan-printables-GPL', src='p823701-ark-first2-low-vers-1.stl', dst='ark-first2-low-vers-1.stl', preview='prev/p823701_1.png',
      title='Ark of the Covenant from the Tabernacle of Moses / Mishkan', author='pazzah (Printables user); designed for pazzah by Bogdan Kukharenko, 3D artist',
      sourceUrl='https://www.printables.com/model/823701-ark-of-the-covenant-from-the-tabernacle-of-moses-m', fileUrl='Printables file id 3488348 via getDownloadLink API',
      licenseName=GPL3[0], licenseUrl=GPL3[1],
      unitsGuess="metres, 1 amah = 0.48 m (the author's companion set states '1 cubit = 480mm'; model 4.41 x 1.42 x 1.62 incl. poles/rings)",
      targetCm={'bodyLength': 125, 'bodyWidth': 75, 'bodyHeight': 75},
      notes='Box with crown (zer) of flame-like points around the top rim, two winged human-form keruvim (Chabad/Kehot interpretation), rings and long poles along the long axis. High poly (1.09M tris), no textures. Blender 3.4.1 export. LICENSE FLAG: GPL-3.0 is a free/copyleft license permitting redistribution and modification with attribution and license notice, but it is outside the approved CC0/CC-BY/CC-BY-SA list - user to decide before shipping.'),
 dict(slug='menorah-pazzah-mishkan-printables-GPL', src='p823646-menorah-200k.stl', dst='menorah-200k.stl', preview='prev/p823646_1.png',
      title='Menorah (Candelabrum) from the Tabernacle of Moses / Mishkan - "Menorah 200k.stl" (decimated)', author='pazzah (Printables user); designed for pazzah by Bogdan Kukharenko, 3D artist',
      sourceUrl='https://www.printables.com/model/823646-menorah-candelabrum-from-the-tabernacle-of-moses-m', fileUrl='Printables file id 3488158 via getDownloadLink API',
      licenseName=GPL3[0], licenseUrl=GPL3[1],
      unitsGuess='unclear; model is 100.4 units tall, 57.6 wide (Blender 3.4.1 export, centred on origin). The author also offers a "Scen 1 (144cm)" variant, so a 144-150 cm target is intended.',
      targetCm={'height': 150},
      notes='Rambam/Chabad-style menorah: straight diagonal branches, spherical knops, ribbed goblets, flower-petal cups, rectangular three-legged base. Medium-high detail (200k tris decimated from the full 143 MB mesh). LICENSE FLAG: GPL-3.0 (see ark note).'),
]


def build(a):
    d = os.path.join(ROOT, a['slug']); os.makedirs(d, exist_ok=True)
    src = os.path.join(DL, a['src']); dst = os.path.join(d, a['dst'])
    shutil.copyfile(src, dst)
    files = [{'file': a['dst'], 'role': 'original', 'bytes': os.path.getsize(dst), 'sha256': sha256(dst)}]
    meshes = []
    hdr = '%s | %s | %s' % (a['title'], a['author'], a['licenseName'])
    if a.get('is3mf'):
        names = a.get('itemNames', {})
        for i, oid, tris, unit in mc.read_3mf(dst):
            tris = rebase(tris)
            name = names.get(i, 'item%d' % i)
            out = os.path.join(d, name + '.obj')
            mc.write_obj(out, tris, name, 1.0, comment='%s\nconverted from %s build item %d (3MF unit=%s), re-based: XY centred, min Z = 0' % (hdr, a['dst'], i, unit))
            st = tri_stats(tris)
            if i == 0:  # body length: extent of vertices in the lower quarter (below pole/ring height)
                v = tris.reshape(-1, 3); low = v[v[:, 2] < 0.25 * v[:, 2].max()]
                st['lowQuarterExtentXY_bodyEstimate'] = [float(round(low[:, 0].max() - low[:, 0].min(), 3)), float(round(low[:, 1].max() - low[:, 1].min(), 3))]
            meshes.append(dict(file=name + '.obj', **st))
            files.append({'file': name + '.obj', 'role': 'converted OBJ (per-face normals, welded verts)', 'bytes': os.path.getsize(out), 'sha256': sha256(out)})
    else:
        tris = mc.read_stl(dst)
        st_orig = tri_stats(tris)
        if a.get('rebase'):
            tris = rebase(tris)
        base = os.path.splitext(a['dst'])[0]
        out = os.path.join(d, base + '.obj')
        mc.write_obj(out, tris, base, 1.0, comment='%s\nconverted from %s, units unchanged%s' % (hdr, a['dst'], ' (re-based: XY centred, min Z = 0)' if a.get('rebase') else ''))
        st = tri_stats(tris); st['originalBbox'] = st_orig
        meshes.append(dict(file=base + '.obj', **st))
        files.append({'file': base + '.obj', 'role': 'converted OBJ (per-face normals, welded verts)', 'bytes': os.path.getsize(out), 'sha256': sha256(out)})
    if a.get('preview'):
        ext = os.path.splitext(a['preview'])[1].lower()
        shutil.copyfile(os.path.join(DL, a['preview']), os.path.join(d, 'preview' + ext))
    prov = dict(title=a['title'], author=a['author'], sourceUrl=a['sourceUrl'], fileUrl=a['fileUrl'], licenseName=a['licenseName'], licenseUrl=a['licenseUrl'],
                downloadedUtc=NOW, files=files, meshes=meshes, triangles=sum(m['triangles'] for m in meshes), unitsGuess=a['unitsGuess'],
                targetSizeCm_perBook=a['targetCm'], notes=a['notes'])
    json.dump(prov, open(os.path.join(d, 'provenance.json'), 'w'), indent=2)
    with open(os.path.join(d, 'LICENSE.txt'), 'w', newline='\n') as f:
        f.write('%s\nAuthor: %s\nSource: %s\n\nLicense: %s\nLicense URL: %s\n\nDownloaded %s for the Mikdash Courtyard walkthrough (non-commercial, freely shared).\n'
                'Attribution to give: "%s" by %s, %s, licensed %s (%s).\n' % (a['title'], a['author'], a['sourceUrl'], a['licenseName'], a['licenseUrl'], NOW,
                                                                             a['title'], a['author'], a['sourceUrl'], a['licenseName'].split(' - ')[0], a['licenseUrl']))
    return {'slug': a['slug'], 'licenseName': a['licenseName'], 'licenseUrl': a['licenseUrl'], 'sourceUrl': a['sourceUrl'], 'triangles': prov['triangles'],
            'meshes': [{'file': m['file'], 'size': m['size']} for m in meshes]}


if __name__ == '__main__':
    only = set(sys.argv[1:])
    manifest = []
    for a in ASSETS:
        if only and a['slug'] not in only:
            continue
        m = build(a)
        manifest.append(m)
        print(m['slug'], '|', m['triangles'], 'tris |', [(x['file'], x['size']) for x in m['meshes']])
    mp = os.path.join(ROOT, 'third-party-manifest.json')
    old = json.load(open(mp))['assets'] if os.path.exists(mp) else []
    merged = {x['slug']: x for x in old}
    for m in manifest:
        merged[m['slug']] = m
    json.dump({'generatedUtc': NOW, 'assets': list(merged.values())}, open(mp, 'w'), indent=2)
