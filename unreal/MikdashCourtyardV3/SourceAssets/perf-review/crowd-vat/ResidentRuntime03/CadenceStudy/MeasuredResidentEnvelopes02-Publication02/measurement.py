import gzip, hashlib, json, sys
from pathlib import Path
import numpy as np
import png16 as reader
HERE=Path(__file__).resolve().parent
ROOT=HERE
NUMERIC_CM=.001
SCALES=(.92,1.,1.08)
def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def extrema(points, margin=0.):
    p = np.asarray(points, dtype=float)
    require(p.ndim == 2 and p.shape[1] == 3 and len(p) > 0 and np.isfinite(p).all()
            and np.isfinite(margin) and margin >= 0, 'Invalid point/margin')
    return dict(radiusCm=float(np.linalg.norm(p[:, :2], axis=1).max() + margin),
                minZCm=float(p[:, 2].min() - margin), maxZCm=float(p[:, 2].max() + margin))


def union(rows):
    return dict(radiusCm=max(r['radiusCm'] for r in rows), minZCm=min(r['minZCm'] for r in rows),
                maxZCm=max(r['maxZCm'] for r in rows))


def scale_bound(bound, scale):
    require(np.isfinite(scale) and scale > 0, 'Invalid scale')
    r = {k: float(v * scale) for k, v in bound.items()}
    r.update(scale=scale, heightCm=r['maxZCm'] - r['minZCm'])
    r['capsuleCenterZCm'] = (r['maxZCm'] + r['minZCm']) / 2
    r['enclosingCapsuleHalfHeightCm'] = r['heightCm'] / 2 + r['radiusCm']
    return r


def vertex_ids(uv, layout):
    w, h, rows, frames = [layout[k] for k in ('width', 'height', 'rowsPerFrame', 'frames')]
    require(w > 0 and rows > 0 and frames > 0 and h == rows * frames, 'Invalid atlas layout')
    pixel = np.asarray(uv) * [w, h]
    require(np.isfinite(pixel).all(), 'Nonfinite UV')
    xy = np.floor(pixel).astype(np.int64)
    require(np.max(abs(pixel - xy - .5)) < .002 and np.min(xy) >= 0
            and np.max(xy[:, 0]) < w and np.max(xy[:, 1]) < rows, 'Non-centred/out-of-frame UV')
    ids = xy[:, 1] * w + xy[:, 0]
    require(len(np.unique(ids)) == len(ids), 'Duplicate vertex addresses')
    return ids


def derived_uv(ids, layout):
    # Local UE5.8 CreateUVChannel float expression; NOT a stored idle UV2 dump.
    w, h = layout['width'], layout['height']
    require(np.min(ids) >= 0 and np.max(ids) < w * layout['rowsPerFrame'], 'Vertex exceeds atlas capacity')
    return np.column_stack((np.float32(.5) / np.float32(w) + (ids % w).astype(np.float32) / np.float32(w),
                            np.float32(.5) / np.float32(h) + (ids // w).astype(np.float32) / np.float32(h)))


def sample_addresses(uv, layout, frame):
    # Explicit point, LOD0, Wrap sampling, including f1=N at the loop seam.
    v = (uv[:, 1].astype(np.float32) + np.float32(frame) / np.float32(layout['frames'])).astype(np.float32)
    x = np.floor(np.mod(uv[:, 0], 1.) * layout['width']).astype(np.int64)
    y = np.floor(np.mod(v, 1.) * layout['height']).astype(np.int64)
    return x, y


def decode_frame(texture, reference, ids, layout, frame):
    w, h, rows, frames = [layout[k] for k in ('width', 'height', 'rowsPerFrame', 'frames')]
    require(texture.shape == (h, w, 4) and h == frames * rows, 'Texture/layout differs')
    require(0 <= frame < frames, 'Frame outside clip')
    return reference + texture[ids // w + frame * rows, ids % w, :3] * layout['sizeBBox'] + layout['minBBox']


def measure_clip(reader, path, reference, ids, material_ids, layout, uv, native_pixels=None):
    texture = reader.png16(path)  # one texture, no frames x vertices arrays
    require(texture.shape == (layout['height'], layout['width'], 4), 'Wrong texture dimensions')
    digest = hashlib.sha256()
    # Rowwise conversion/hash avoids a second full RGBA16 image allocation.
    for row in texture:
        digest.update(np.rint(row * 65535).astype('>u2').tobytes())
    if native_pixels:
        require(digest.hexdigest() == native_pixels['decodedRGBA16BigEndianSha256'], 'Native decoded pixels differ')
        require(sha(path) == native_pixels['fileSha256'], 'Native PNG differs')
    by_material = {str(int(m)): [] for m in np.unique(material_ids)}
    frames = []
    witnesses = {}
    for frame in range(layout['frames']):
        x, y = sample_addresses(uv, layout, frame)
        require(np.array_equal(x, ids % layout['width'])
                and np.array_equal(y, ids // layout['width'] + frame * layout['rowsPerFrame']), 'Sampler address mismatch')
        p = decode_frame(texture, reference, ids, layout, frame)
        e = extrema(p)
        frames.append(e)
        for key, index in [('radiusCm', np.argmax(np.linalg.norm(p[:, :2], axis=1))),
                           ('minZCm', np.argmin(p[:, 2])), ('maxZCm', np.argmax(p[:, 2]))]:
            if key not in witnesses or (e[key] < witnesses[key]['value'] if key == 'minZCm' else e[key] > witnesses[key]['value']):
                witnesses[key] = dict(value=e[key], frame=frame, row=int(index), vertexId=int(ids[index]),
                                      material=int(material_ids[index]), pointCm=p[index].tolist())
        for m in by_material:
            by_material[m].append(extrema(p[material_ids == int(m)]))
    x, y = sample_addresses(uv, layout, layout['frames'])
    require(np.array_equal(x, ids % layout['width']) and np.array_equal(y, ids // layout['width']), 'Loop seam address differs')
    observed = union(frames)
    conservative = dict(radiusCm=observed['radiusCm'] + NUMERIC_CM,
                        minZCm=observed['minZCm'] - NUMERIC_CM, maxZCm=observed['maxZCm'] + NUMERIC_CM)
    return dict(frames=layout['frames'], width=layout['width'], height=layout['height'], rowsPerFrame=layout['rowsPerFrame'],
                observed=observed, conservative=conservative, perFrame=frames, witnesses=witnesses,
                materials={m: union(rows) for m, rows in by_material.items()},
                decodedRGBA16BigEndianSha256=digest.hexdigest(), pngSha256=sha(path),
                samplerAllFramesAndSeamChecked=True, uvChannel=layout['uvChannel'])


def measure_variant(reader, variant, config, item, native):
    binding=read(ROOT/item['bindings']);row=binding['row']
    fresh=dict(status=binding['freshStatus'],geometryDigest=binding['geometryDigest'])
    require(fresh['status']=='verified-fresh-candidate-not-rendered' and fresh['geometryDigest']['source']==fresh['geometryDigest']['candidate'],'Archived geometry proof differs')
    with gzip.open(ROOT / item['static'], 'rt') as f:
        static = json.load(f)
    require(static['fields'] == ['material', 'position', 'uv0', 'normal', 'vatUV'], 'Unexpected census format')
    reference = np.asarray([r[1] for r in static['rows']]); materials = np.asarray([r[0] for r in static['rows']])
    uvw = np.asarray([r[4] for r in static['rows']], dtype=np.float32)
    require(len(reference) == row['stats']['vertices'] and static['triangles'] == row['stats']['triangles'], 'Incomplete geometry')
    require(sorted(set(materials)) == list(range(6)), 'Missing full-body material slots')
    ids = vertex_ids(uvw, row['walkBake'])
    require(np.array_equal(np.sort(ids), np.arange(len(ids))), 'Vertex IDs are not a complete contiguous census')
    require(row['walkBake']['frames'] == 72 and row['idleBake']['frames'] == 192, 'Unexpected clips')
    require(np.max(abs(uvw - derived_uv(ids, row['walkBake']))) < 1e-7, 'Native UV1 differs from engine derivation')
    clips = {}
    for clip, uv in [('walk', uvw), ('idle', derived_uv(ids, row['idleBake']))]:
        layout = row[clip + 'Bake']; title = clip.title()
        require(layout['uvChannel'] == (1 if clip == 'walk' else 2), 'Wrong UV channel')
        require(np.all(np.isfinite(layout['sizeBBox'])) and np.min(layout['sizeBBox']) > 0, 'Invalid decode box')
        settings = row['textureSettings']['T_' + title + 'Position']
        require(settings['srgb'] == 'False' and 'TF_NEAREST' in settings['filter']
                and 'TMGS_NO_MIPMAPS' in settings['mip_gen_settings'], 'Unexpected sampler')
        for material in row['materialInstances'].values():
            require(material[title + 'MinBBox'] == layout['minBBox'] and material[title + 'SizeBBox'] == layout['sizeBBox']
                    and material[title + 'PositionTexture'] == row['textures'][title + 'Position'], 'Material decode/binding differs')
        pixels = None
        if clip == 'idle':
            n = next(n for n in native['textures'] if n['variant'] == variant)
            require(n['object'] == row['textures']['IdlePosition'], 'Wrong idle object')
            pixels = n['pixels']
        clips[clip] = measure_clip(reader, ROOT / item[clip + 'Position'], reference, ids, materials, layout, uv, pixels)
    combined = union([c['conservative'] for c in clips.values()])
    return dict(vertices=len(reference), triangles=static['triangles'], materialSlots=[int(m) for m in sorted(set(materials))],
                clips=clips, tightCombined=combined, scales=[scale_bound(combined, s) for s in SCALES],
                idleAddressEvidence='Source-derived VertexID mapping; not raw UV2 readback. Conditional on pinned bake preserving vertex IDs.',
                geometryReadbackDigest=fresh['geometryDigest']['candidate'])


def check_pins(config):
    for name,pin in config['inputs'].items():
        p=HERE/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Nonportable input')
        require(p.is_file() and p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256'],'Changed input: '+name)

def accepted_export(config):
    evidence=read(HERE/'evidence/accepted-export.json');w=evidence['wrapper'];n=evidence['native']
    require(evidence['historicalNativeSha256']==config['acceptedNativeSha256'] and evidence['historicalManifestSha256']==config['acceptedManifestSha256'],'Wrong historical identity')
    require(w['status']=='child_exited_zero' and w['exitCode']==0 and w['cleanupConfirmed'] and w['sourcePreserved'] and not w['slotBlocked'] and w['naturalDrainConfirmed'],'Failed wrapper')
    t=w['terminalPoll']
    require(t['rootExited'] and t['exitCode']==0 and t['activeProcesses']==0 and t['elapsedSeconds']<w['deadlineSeconds']-6 and w['finishedSeconds']<w['deadlineSeconds'],'Incomplete drain')
    require(n['status']=='idle_position_source_pixels_exported' and n['sourcePreserved'] and n['stagedPreserved'] and len(n['textures'])==2,'Incomplete archived export')
    return n

def run():
    config=read(HERE/'inputs.json');check_pins(config);native=accepted_export(config)
    actual={v:measure_variant(reader,v,config,item,native) for v,item in config['study13'].items()}
    require(actual==read(HERE/'evidence/original-results.json')['study13'],'Exact study13 recomputation differs')
    check_pins(config)
    return actual
