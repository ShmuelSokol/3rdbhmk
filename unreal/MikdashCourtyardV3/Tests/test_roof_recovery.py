"""Offline guard tests only; these do not establish Unreal/runtime acceptance."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'Scripts'/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
A=load('audit_legacy_roof_zones')
R=load('release_legacy_roof_zones')
PLAN=json.loads((ROOT/'SourceAssets/context-review/LegacyRoofZonesV1/legacy-roof-zones.json').read_text(encoding='utf-8-sig'))
class Props:
    def __init__(self,**values):self.values=values
    def get_editor_property(self,name):return self.values[name]

def enclosure():
    return Props(ExplicitHideLabels=sorted({o['buildingLabel'] for o in PLAN['owners'] if o['zone']=='precinct'}),
                 HideWhileWallStandsTags=['CityDetailZone_Precinct','OtherWallTag'],HideWhileModernCityStandsTags=['OtherModernTag'])

class GuardTests(unittest.TestCase):
    def test_real_plan_and_hashes(self):
        R.read_plan(ROOT/'SourceAssets/context-review/LegacyRoofZonesV1/legacy-roof-zones.json')
        R.validate_runtime_policy(enclosure(),PLAN)
    def test_duplicate_missing_indices_rejected(self):
        broken=copy.deepcopy(PLAN)
        broken['owners'][0]['sourceIndex']=broken['owners'][1]['sourceIndex']
        with self.assertRaises(RuntimeError):R.validate_plan(broken)
    def test_unresolved_and_invalid_zone_rejected(self):
        for mutation in ('unresolved','zone'):
            broken=copy.deepcopy(PLAN)
            if mutation=='unresolved':broken['unresolved']=[{'sourceIndex':0}]
            else:broken['owners'][0]['zone']='unknown'
            with self.assertRaises(RuntimeError):R.validate_plan(broken)
    def test_changed_building_policy_rejected(self):
        e=enclosure()
        e.values['ExplicitHideLabels']=[]
        with self.assertRaises(RuntimeError):R.validate_runtime_policy(e,PLAN)
    def test_conflicting_runtime_tags_rejected(self):
        for prop,tag in [('HideWhileModernCityStandsTags','CityDetailZone_Precinct'),
                         ('HideWhileWallStandsTags','CityDetailZone_Kept'),
                         ('HideWhileModernCityStandsTags','CityDetailZone_Kept'),
                         ('HideWhileWallStandsTags','LegacyRoofZonesV1')]:
            e=enclosure();e.values[prop].append(tag)
            with self.assertRaises(RuntimeError):R.validate_runtime_policy(e,PLAN)
    def test_original_visibility_and_inherited_tag_guards(self):
        actor=Props(tags=['OriginalImport'],hidden=False)
        comp=Props(visible=True,hidden_in_game=False)
        R.validate_original_visibility(actor,comp,enclosure())
        for target,prop,value in [(actor,'hidden',True),(comp,'visible',False),(comp,'hidden_in_game',True),(actor,'tags',['OtherWallTag']),(actor,'tags',['OtherModernTag'])]:
            old=target.values[prop];target.values[prop]=value
            with self.assertRaises(RuntimeError):R.validate_original_visibility(actor,comp,enclosure())
            target.values[prop]=old
    def test_bounding_box_is_not_triangle_support(self):
        tri=np.array([[0.,2.,0.],[10.,2.,0.],[0.,2.,10.]])
        self.assertTrue(A.point_on_triangle(1,1,tri))
        self.assertTrue(A.point_on_triangle(5,5,tri))
        self.assertFalse(A.point_on_triangle(9,9,tri))
        self.assertFalse(A.point_on_triangle(1,1,np.zeros((3,3))))
    def test_ambiguous_owners_refused(self):
        self.assertEqual(A.choose_owner(['Grid_A','Grid_A']),'Grid_A')
        self.assertIsNone(A.choose_owner(['Grid_A','Grid_B']))
        self.assertIsNone(A.choose_owner([]))

if __name__=='__main__':unittest.main(verbosity=2)
