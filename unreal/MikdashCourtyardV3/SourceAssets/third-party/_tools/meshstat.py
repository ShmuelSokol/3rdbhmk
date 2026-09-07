"""Quick mesh stats for binary/ASCII STL, OBJ. Usage: python meshstat.py file [file...]"""
import sys, struct, os
import numpy as np

def read_stl(path):
    data = open(path, 'rb').read()
    is_ascii = data[:5].lower() == b'solid' and (len(data) < 84 or 84 + 50 * struct.unpack('<I', data[80:84])[0] != len(data))
    if not is_ascii:
        n = struct.unpack('<I', data[80:84])[0]
        rec = np.frombuffer(data, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]), count=n, offset=84)
        return rec['v'].reshape(-1, 3, 3).astype(np.float64)
    tris = []
    cur = []
    for line in data.decode('ascii', 'replace').splitlines():
        p = line.split()
        if p and p[0] == 'vertex':
            cur.append([float(p[1]), float(p[2]), float(p[3])])
            if len(cur) == 3:
                tris.append(cur); cur = []
    return np.array(tris, dtype=np.float64)

def read_obj_tris(path):
    vs = []; faces = []
    for line in open(path, 'r', errors='replace'):
        if line.startswith('v '):
            p = line.split(); vs.append([float(p[1]), float(p[2]), float(p[3])])
        elif line.startswith('f '):
            idx = [int(t.split('/')[0]) for t in line.split()[1:]]
            idx = [i - 1 if i > 0 else len(vs) + i for i in idx]
            for k in range(1, len(idx) - 1):
                faces.append([idx[0], idx[k], idx[k + 1]])
    vs = np.array(vs); faces = np.array(faces)
    return vs[faces]

def stats(tris):
    v = tris.reshape(-1, 3)
    mn = v.min(0); mx = v.max(0)
    return {'triangles': int(len(tris)), 'bbox_min': mn.round(4).tolist(), 'bbox_max': mx.round(4).tolist(), 'size': (mx - mn).round(4).tolist()}

if __name__ == '__main__':
    import json
    for f in sys.argv[1:]:
        t = read_stl(f) if f.lower().endswith('.stl') else read_obj_tris(f)
        print(f, json.dumps(stats(t)))
