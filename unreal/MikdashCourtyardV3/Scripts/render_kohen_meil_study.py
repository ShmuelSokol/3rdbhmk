"""Offline rest-pose silhouette comparison only; native material review remains owed."""
import argparse
from pathlib import Path
from measure_pilgrim_walk import read_glb, read_accessor, author
from render_face_v5 import render
from build_kohen_neck_tone_study import SOURCE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenMeilEaseV2'


def run(label):
    paths = {'before': SOURCE, 'candidate': OUT / 'SK_KohenGadol_MeilEase5_Study.glb',
             'layered-candidate': OUT / 'SK_KohenGadol_MeilEase5_LayeredStudy.glb'}
    for label, path in ((label, paths[label]),):
        destination = OUT / ('silhouette-' + label + '-offline.png')
        if destination.exists():
            raise FileExistsError('Fresh preview output required')
        doc, binary = read_glb(path)
        parts = []
        for mesh in doc['meshes']:
            for primitive in mesh['primitives']:
                attrs = primitive['attributes']
                indices = read_accessor(doc, binary, primitive['indices'])
                parts.append(dict(material=doc['materials'][primitive['material']]['name'],
                    vertices=[author(v) for v in read_accessor(doc, binary, attrs['POSITION'])],
                    normals=[(v[0], -v[2], v[1]) for v in read_accessor(doc, binary, attrs['NORMAL'])],
                    colours=read_accessor(doc, binary, attrs['COLOR_0']),
                    faces=[tuple(indices[i:i + 3]) for i in range(0, len(indices), 3)]))
        render(parts, destination, dist_m=2.1, yaw=.65, target=(0, 0, 90), width=600, height=900, ss=1)
        print(destination, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--view', choices=('before', 'candidate', 'layered-candidate'), required=True)
    run(parser.parse_args().view)
