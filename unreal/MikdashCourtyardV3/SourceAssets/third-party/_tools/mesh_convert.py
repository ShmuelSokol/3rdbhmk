"""Convert STL (binary/ASCII) or 3MF to Wavefront OBJ with per-face normals.

Usage:
  python mesh_convert.py in.stl out.obj [--scale S] [--name objname]
  python mesh_convert.py in.3mf out_prefix [--scale S]   (one OBJ per build item, transforms applied
                                                          minus the build-plate translation, i.e. each
                                                          part is re-based so its bbox min Z = 0 and XY centred)
Plain Python + numpy. Units are passed through unchanged unless --scale is given.
"""
import sys, struct, os, re, zipfile, io, argparse
import numpy as np

def read_stl(path):
    data = open(path, 'rb').read()
    n_hdr = struct.unpack('<I', data[80:84])[0] if len(data) >= 84 else -1
    if len(data) >= 84 and 84 + 50 * n_hdr == len(data):
        rec = np.frombuffer(data, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]), count=n_hdr, offset=84)
        return rec['v'].astype(np.float64).copy()
    vals = re.findall(rb'vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)', data)
    arr = np.array(vals, dtype=np.float64)
    return arr.reshape(-1, 3, 3)

def write_obj(path, tris, name='mesh', scale=1.0, comment=None):
    """tris: (N,3,3). Welds identical vertices, writes per-face normals."""
    tris = np.asarray(tris, dtype=np.float64) * scale
    flat = tris.reshape(-1, 3)
    uniq, inv = np.unique(flat.round(6), axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    e1 = tris[:, 1] - tris[:, 0]; e2 = tris[:, 2] - tris[:, 0]
    nrm = np.cross(e1, e2)
    ln = np.linalg.norm(nrm, axis=1); ln[ln == 0] = 1
    nrm = nrm / ln[:, None]
    with open(path, 'w', newline='\n') as f:
        if comment:
            for c in comment.splitlines():
                f.write('# %s\n' % c)
        f.write('o %s\n' % name)
        for v in uniq:
            f.write('v %.6f %.6f %.6f\n' % tuple(v))
        for n in nrm:
            f.write('vn %.6f %.6f %.6f\n' % tuple(n))
        for i, (a, b, c) in enumerate(inv, 1):
            f.write('f %d//%d %d//%d %d//%d\n' % (a + 1, i, b + 1, i, c + 1, i))
    return len(tris), len(uniq)

def _parse_3mf_mesh_xml(xml):
    """Return dict id -> (verts(N,3), tris(M,3)) and dict id -> [(child_id, path, T4x4)] for component objects."""
    meshes = {}; comps = {}
    for m in re.finditer(r'<object\s+([^>]*)>(.*?)</object>', xml, re.S):
        attrs = dict(re.findall(r'(\S+?)="([^"]*)"', m.group(1)))
        oid = attrs.get('id'); body = m.group(2)
        vs = re.findall(r'<vertex\s+x="([^"]+)"\s+y="([^"]+)"\s+z="([^"]+)"', body)
        ts = re.findall(r'<triangle\s+v1="(\d+)"\s+v2="(\d+)"\s+v3="(\d+)"', body)
        if ts:
            meshes[oid] = (np.array(vs, dtype=np.float64), np.array(ts, dtype=np.int64))
        cl = []
        for c in re.finditer(r'<component\s+([^>]*)/>', body):
            ca = dict(re.findall(r'(\S+?)="([^"]*)"', c.group(1)))
            cl.append((ca.get('objectid'), ca.get('p:path'), _t3mf(ca.get('transform'))))
        if cl:
            comps[oid] = cl
    return meshes, comps

def _t3mf(s):
    T = np.eye(4)
    if s:
        v = [float(x) for x in s.split()]
        M = np.array(v).reshape(4, 3)  # row-major 3x4: rows are basis vectors + translation (3MF spec)
        T[:3, :3] = M[:3].T
        T[:3, 3] = M[3]
    return T

def read_3mf(path):
    """Yield (item_index, item_name, tris(N,3,3)) with all transforms applied (world space, 3MF units)."""
    z = zipfile.ZipFile(path)
    root_name = [n for n in z.namelist() if n.lower().endswith('3dmodel.model') and n.lower().startswith('3d/')][0]
    root_xml = z.read(root_name).decode('utf-8', 'replace')
    unit = re.search(r'unit="(\w+)"', root_xml)
    unit = unit.group(1) if unit else 'millimeter'
    cache = {}
    def load(pth):
        key = pth.lstrip('/') if pth else root_name
        if key not in cache:
            names = {n.lower(): n for n in z.namelist()}
            cache[key] = _parse_3mf_mesh_xml(z.read(names[key.lower()]).decode('utf-8', 'replace'))
        return cache[key]
    def collect(oid, pth, T):
        meshes, comps = load(pth)
        out = []
        if oid in meshes:
            v, t = meshes[oid]
            vh = np.c_[v, np.ones(len(v))] @ T.T
            out.append(vh[:, :3][t])
        for cid, cpath, cT in comps.get(oid, []):
            out += collect(cid, cpath or pth, T @ cT)
        return out
    items = re.findall(r'<item\s+([^>]*)/>', root_xml)
    for i, it in enumerate(items):
        a = dict(re.findall(r'(\S+?)="([^"]*)"', it))
        T = _t3mf(a.get('transform'))
        parts = collect(a['objectid'], a.get('p:path'), T)
        if parts:
            yield i, a['objectid'], np.concatenate(parts), unit

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--name', default=None); ap.add_argument('--keep-placement', action='store_true')
    a = ap.parse_args()
    if a.src.lower().endswith('.stl'):
        tris = read_stl(a.src)
        n, nv = write_obj(a.dst, tris, a.name or os.path.splitext(os.path.basename(a.dst))[0], a.scale,
                          comment='converted from %s by mesh_convert.py, scale %g' % (os.path.basename(a.src), a.scale))
        print('%s: %d triangles, %d unique vertices -> %s' % (a.src, n, nv, a.dst))
    elif a.src.lower().endswith('.3mf'):
        for i, oid, tris, unit in read_3mf(a.src):
            if not a.keep_placement:
                mn = tris.reshape(-1, 3).min(0); mx = tris.reshape(-1, 3).max(0)
                tris = tris - np.array([(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]])
            out = '%s_item%d_obj%s.obj' % (a.dst, i, oid)
            n, nv = write_obj(out, tris, a.name or ('item%d' % i), a.scale,
                              comment='converted from %s (3MF unit=%s, build item %d object %s) by mesh_convert.py, scale %g' % (os.path.basename(a.src), unit, i, oid, a.scale))
            sz = (tris.reshape(-1, 3).max(0) - tris.reshape(-1, 3).min(0))
            print('%s item %d obj %s: %d triangles, %d verts, size %s %s -> %s' % (a.src, i, oid, n, nv, sz.round(2).tolist(), unit, out))
