"""Independent surface checks for the frozen S5 artifacts (Python 3.12 + Shapely)."""
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Scripts'))
sys.path.insert(0, str(ROOT.parent/'S5Deps'))
from shapely.geometry import Point, Polygon
from release_precinct_terrain_cut import HeightField
from release_haram_precinct import obj_triangles
from verify_haram_wall_surfaces import verify as verify_wall_surface, retained_area, bary

OUT = ROOT/'SourceAssets/enclosure-review/HaramPrecinctV1'


class HaramSurfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((OUT/'plan.json').read_text())
        cls.ring = Polygon(cls.plan['ringCm'])

    def test_cut_preserves_outside_surface_and_clears_inside(self):
        original = HeightField()
        original.add(t['positions'] for t in json.loads((OUT/'native-terrain-source.json').read_text()))
        cut = HeightField()
        vertices = json.loads((OUT/'terrain-buffers.json').read_text())['positions']
        cut.add(vertices[i:i+3] for i in range(0,len(vertices),3))
        inside = outside = 0
        max_error = 0
        # Offset grid avoids the source tile's triangulation boundaries. This
        # independently samples the finished surface, not the clipping algorithm.
        for x in range(-39013,800,125):
            for y in range(-39907,0,125):
                old, new = original.height(x,y), cut.height(x,y)
                if old is None:
                    continue
                self.assertIsNotNone(new, (x,y,'new terrain hole'))
                if self.ring.contains(Point(x,y)):
                    self.assertLessEqual(new,.01,(x,y,new))
                    inside += 1
                else:
                    error = abs(old-new)
                    self.assertLess(error,.05,(x,y,old,new))
                    max_error = max(max_error,error)
                    outside += 1
        self.assertGreater(inside,100)
        self.assertGreater(outside,10000)
        print('Terrain stations:', inside, 'inside,', outside, 'outside; max outside error cm:', max_error)

    def test_access_and_paving_probes_match_actual_mesh_surfaces(self):
        surfaces = HeightField()
        for spec in self.plan['meshes']:
            if spec['name'].startswith(('SM_Haram_Deck_', 'SM_Haram_Access', 'SM_Haram_Thresholds')):
                surfaces.add(obj_triangles(OUT/spec['file']))
        self.assertGreater(len(self.plan['walkProbesCm']),60)
        for x,y,z in self.plan['walkProbesCm']:
            actual = surfaces.height(x,y)
            self.assertIsNotNone(actual)
            self.assertLess(abs(actual-z),.01,(x,y,z,actual))

    def test_access_shell_has_no_buried_shared_tread_faces(self):
        spec=next(s for s in self.plan['meshes'] if s['name'].startswith('SM_Haram_Access'))
        edges=Counter()
        for tri in obj_triangles(OUT/spec['file']):
            points=[tuple(round(v,5) for v in p) for p in tri]
            for a,b in zip(points,points[1:]+points[:1]):
                edges[(a,b)]+=1
        # A closed external shell has each directed edge exactly once and a
        # single reversed partner. Adjacent independent boxes fail this check.
        for (a,b),count in edges.items():
            self.assertEqual(count,1,(a,b,count))
            self.assertEqual(edges[(b,a)],1,(a,b))

    def test_wall_verifier_rejects_equal_area_overlap_and_missing_patch(self):
        original=dict(tid=0,positions=[[0.,0.,0.],[100.,0.,0.],[0.,100.,0.]],materialId=0,attrs={})
        verify_wall_surface([original],[original],[])
        half=dict(original,positions=[[0.,0.,0.],[100.,0.,0.],[0.,50.,0.]])
        with self.assertRaisesRegex(AssertionError,'Overlapping output fragments'):
            verify_wall_surface([original],[half,dict(half,tid=1)],[])

    def test_overlapping_gate_cutters_are_counted_once(self):
        gate=dict(positionCm=[0.,0.],tangent=[1.,0.],inward=[0.,1.],runCm=600.,thresholdZCm=.5)
        triangle=[[0.,0.,0.],[1000.,0.,0.],[0.,1000.,0.]]
        self.assertAlmostEqual(retained_area(triangle,[gate,gate]),500000.-242.*750.)

    def test_thin_triangle_uses_physical_edge_tolerance(self):
        triangle=[[0.,0.,0.],[100.,0.,0.],[0.,.01,0.]]
        self.assertIsNotNone(bary([50.,-.001,0.],triangle))
        self.assertIsNone(bary([50.,-.03,0.],triangle))

    def test_gate_headroom_through_wall_depth(self):
        # Low gates need masonry above a normal-height opening, not an opening
        # extending fourteen metres upward to the plateau.
        lintel_bottom = HeightField()
        lintel_bottom.add([[[x,y,-z] for x,y,z in triangle]
                          for triangle in obj_triangles(OUT/next(s['file'] for s in self.plan['meshes'] if s['name'].startswith('SM_Haram_Gates')))])
        treads = HeightField()
        treads.add(obj_triangles(OUT/next(s['file'] for s in self.plan['meshes'] if s['name'].startswith('SM_Haram_Access'))))
        for gate in self.plan['gates']:
            self.assertAlmostEqual(gate['lintelUndersideZCm']-gate['thresholdZCm'],480)
            self.assertLessEqual(gate['maxRiserCm'],18)
            self.assertLess(gate['projectionDistanceCm'],2000)
            self.assertGreater(gate['openingWidthCm'],200)
            for d in (1,144,287):
                for u in (-180,0,180):
                    x,y = [gate['positionCm'][i]+gate['inward'][i]*d+gate['tangent'][i]*u for i in range(2)]
                    ceiling, floor = lintel_bottom.height(x,y), treads.height(x,y)
                    self.assertIsNotNone(ceiling)
                    self.assertIsNotNone(floor)
                    self.assertGreater(-ceiling-floor,240,(gate['name'],d,u))


if __name__ == '__main__':
    unittest.main()
