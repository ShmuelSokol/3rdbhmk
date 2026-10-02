"""Offline validation counterexamples. No fixture output is live cooked evidence."""
import copy, json, tempfile, unittest
from pathlib import Path
import runner as r

class ResultTests(unittest.TestCase):
    def setUp(self):
        self.inputs=r.load(r.ROOT/'inputs.json')
        self.request={'descriptor':{'nonce':'n','manifest':'m','seal':'s','savePrefix':'fresh'}}
        self.result={'schema':1,'status':'diagnostic_observed','worldReady':False,
          'measuredCorrespondenceConditional':True,**self.request['descriptor'],
          'observation':{'map':self.inputs['map'],'residents':48,'agentIndex':0,'pose':0,'instance':0,
           'profile':1,'scale':1,'idle':True,'mesh':self.inputs['variants'][0]['mesh'],
           'evidence':self.inputs['evidence'],'origin':[0,0,-.1],
           'loadedProjectPackages':[self.inputs['map']],
           'capture':{'diagnosticOnly':True,'publishedEnumerationExhausted':False,'worldComplete':False,
            'obstaclesComplete':False,'observedEnumerationExhausted':True,'candidateCopyAvailable':True,
            'refusal':0,'agent':'1','incarnation':'1','profile':1,'payloadVisits':64,'nodeVisits':2,
            'boundsTests':4,'sourceFaceTests':3,'exhaustedMeshes':1,'candidateVertices':3,'candidateFaces':1,
            'walkingFilter':'fixture only','observedShapes':[]}}}
    def validate(self): return r.validate_result(self.result,self.request,self.inputs)
    def refusal(self,code):
        c=self.result['observation']['capture'];c.update(refusal=code,observedEnumerationExhausted=False,candidateCopyAvailable=False)
        c.pop('candidateVertices',None);c.pop('candidateFaces',None)
        return c
    def test_payload64_success(self): self.assertEqual(self.validate()['geometryRefusal'],0)
    def test_payload65_budget_retained(self):
        c=self.refusal(6);c['payloadVisits']=65
        self.assertEqual(self.validate()['geometryRefusal'],6)
        self.assertFalse(self.validate()['worldReady'])
    def test_payload65_nonbudget_rejected(self):
        for code in range(11):
            if code==6:continue
            self.setUp()
            c=self.result['observation']['capture'] if code==0 else self.refusal(code)
            c['payloadVisits']=65
            with self.subTest(code=code),self.assertRaises(ValueError):self.validate()
    def test_payload66_rejected(self):
        self.refusal(6)['payloadVisits']=66
        with self.assertRaises(ValueError):self.validate()
    def test_partial_budget_cannot_claim_exhaustion(self):
        self.refusal(6)['observedEnumerationExhausted']=True
        with self.assertRaises(ValueError):self.validate()
    def test_partial_budget_cannot_claim_copy(self):
        self.refusal(6)['candidateCopyAvailable']=True
        with self.assertRaises(ValueError):self.validate()
    def test_valid_shape_refusal(self):
        self.refusal(7)
        self.assertEqual(self.validate()['geometryRefusal'],7)
    def test_result_bindings(self):
        for key in self.request['descriptor']:
            self.setUp();self.result[key]='foreign'
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate()
    def test_no_readiness(self):
        self.result['worldReady']=True
        with self.assertRaises(ValueError):self.validate()
    def test_no_world_certificate(self):
        for key in ('publishedEnumerationExhausted','worldComplete','obstaclesComplete'):
            self.setUp();self.result['observation']['capture'][key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate()
    def test_unknown_owner(self):
        for key,value in [('map','/Game/Main'),('residents',49),('agentIndex',48),('scale',.96),('idle',False),('mesh','player'),('profile',4),('pose',1),('instance',1),('evidence','stale')]:
            self.setUp();self.result['observation'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate()
    def test_nonfinite_origin(self):
        self.result['observation']['origin'][1]=float('nan')
        with self.assertRaises(ValueError):self.validate()
    def test_foreign_package(self):
        self.result['observation']['loadedProjectPackages'].append('/Game/Main')
        with self.assertRaises(ValueError):self.validate()
    def test_duplicate_package(self):
        self.result['observation']['loadedProjectPackages']*=2
        with self.assertRaises(ValueError):self.validate()
    def test_shape_budget(self):
        self.result['observation']['capture']['observedShapes']=[{}]*33
        with self.assertRaises(ValueError):self.validate()
    def test_wrong_capture_owner(self):
        self.result['observation']['capture']['agent']='2'
        with self.assertRaises(ValueError):self.validate()
    def test_false_success_copy(self):
        self.result['observation']['capture']['candidateCopyAvailable']=False
        with self.assertRaises(ValueError):self.validate()

class FilesTests(unittest.TestCase):
    def test_exact_inventory_and_mutation(self):
        with tempfile.TemporaryDirectory(prefix='walking09-offline-') as d:
            p=Path(d);(p/'a').write_bytes(b'x');pins={'a':r.sha(p/'a')};r.exact_tree(p,pins)
            (p/'b').write_bytes(b'y')
            with self.assertRaises(ValueError):r.exact_tree(p,pins)
            (p/'b').unlink();(p/'a').write_bytes(b'z')
            with self.assertRaises(ValueError):r.exact_tree(p,pins)
    def test_escape(self):
        for path in ('../a','/a','a//b','a/./b','C:/x','a\\b'):
            with self.subTest(path=path),self.assertRaises(ValueError):r.relpath(r.ROOT,path)
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='walking09-offline-') as d:
            p=Path(d)/'r.json';r.write(p,{'a':1})
            with self.assertRaises(FileExistsError):r.write(p,{'a':2})
            self.assertEqual(r.load(p),{'a':1})
    def test_duplicate_json(self):
        with tempfile.TemporaryDirectory(prefix='walking09-offline-') as d:
            p=Path(d)/'x';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):r.load(p)
    def test_complete_inheritance_include(self):
        cpp=(r.ROOT/'ProbeProject/Source/CookedWorldProbe/Private/WalkingQuery.cpp').read_text()
        self.assertIn('#include "Physics/Experimental/PhysScene_Chaos.h"',cpp)
        build=(r.ROOT/'ProbeProject/Source/CookedWorldProbe/CookedWorldProbe.Build.cs').read_text()
        self.assertIn('NoPCHs',build);self.assertIn('bUseUnity = false',build)
    def test_actual_collector_budget_unchanged(self):
        cpp=(r.ROOT/'ProbeProject/Source/CookedWorldProbe/Private/CookedWorldPort.cpp').read_text()
        self.assertIn('Need(++Out.PayloadVisits<=64,ERefusal::Budget)',cpp)
        self.assertNotIn('PayloadVisits<=65',cpp)

if __name__=='__main__':unittest.main(verbosity=2)
