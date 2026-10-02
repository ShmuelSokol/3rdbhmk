"""Offline actual-composed-source checks; no UE objects or mocks."""
from pathlib import Path
import ast,json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hashlib
class compose:
    sha=staticmethod(lambda b:hashlib.sha256(b).hexdigest())
    @staticmethod
    def build():
        root=Path(__file__).resolve().parent
        m=json.loads((root/"allowlist.json").read_text())
        return {e["path"]:(root/e["path"]).read_bytes() for e in m["entries"]}
class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.out=compose.build();cls.p='P/Source/Receiver04Compile/Private/'
    def text(self,n):return self.out[self.p+n].decode()
    def test_six_exact_gauss_outputs(self):
        pins=json.loads(self.out['settings05-overlay-pins.json'])
        self.assertEqual(6,len(pins))
        for n,h in pins.items():self.assertEqual(h,compose.sha(self.out[n]))
    def test_single_reader_v2(self):
        c=self.text('runtime_candidate05/PrivateBootstrap.cpp')
        self.assertIn('Settings05::AdmitPrivateV2(Body,Last,*Provisioning)',c)
        self.assertIn('Settings05::RevokeLease()',c)
        self.assertNotIn('Receiver->Start(',self.text('integration01/IntegrationModule.cpp'))
    def test_controller_real_lease_before_bind(self):
        c=self.text('Native/receiver04/OnlineController.cpp')
        self.assertLess(c.index('Settings05::FindLease(S->BoundOwner())'),c.index('Remote=MoveTemp(S)'))
        self.assertLess(c.index('Settings= MikdashOnline::Settings05'.replace('= ','=')) if False else c.index('Settings=MikdashOnline::Settings05::MakeOwnedSettingsCallback'),c.index('SettingsOwned=MoveTemp(Settings)'))
    def test_missing_lease_no_true(self):
        c=self.text('runtime_settings05/NativeLease.cpp')
        self.assertIn('if(!Lease.IsValid())return [](){return false;};',c)
        self.assertIn('Saves->SlotCount==int32(Slots)',c)
    def test_plugin_dependencies(self):
        enabled={x['Name'] for x in json.loads(self.out['P/Receiver04Compile.uproject'])['Plugins'] if x['Enabled']}
        self.assertTrue({'EnhancedInput','ControlRig','ControlRigSpline','FullBodyIK'}<=enabled)
    def test_real_data_pins(self):
        d=json.loads(self.out['dependency-evidence.json'])['runtimeDataPins']
        self.assertEqual(12,len(d))
        rules=self.out['P/Source/Receiver04Compile/Receiver04Compile.Build.cs'].decode()
        for n,h in d.items():
            self.assertEqual(h,compose.sha(self.out['P/'+n]));self.assertIn('$(ProjectDir)/'+n,rules)
    def test_registry_precedes_mutation(self):
        c=self.out['blueprint_validate.py'].decode()
        self.assertLess(c.index('dependency_result=preflight.validate(root)'),c.index("blueprint-attempt.json').open"))
        self.assertLess(c.index('dependency_result=preflight.validate(root)'),c.index('lib.reparent_blueprint'))
    def test_registry_real_and_bounded(self):
        c=self.out['dependency_preflight.py'].decode();ast.parse(c)
        for s in ('get_asset_registry()','get_dependencies(','include_soft_package_references=True','len(seen)>=20000','len(queue)>80000'):
            self.assertIn(s,c)
    def test_movement_fix_preserved(self):
        c=self.text('Native/receiver04/OnlineMovement.cpp')
        self.assertIn('const TSharedPtr<Authority> Service=Remote',c)
        tail=c.split('CharacterOwner->CheckJumpInput(Dt);',1)[1].split('bool UReceiver04DoveMovement::ValidRemote',1)[0]
        self.assertNotIn('Remote->',tail)
    def test_guard9_preserved(self):
        c=self.out['Build-Reviewed.ps1'].decode()
        for s in ('9GB','4GB','2GB','Get-CompileDeadlineDecision','StopWithinFiveSeconds'):self.assertIn(s,c)
    def test_no_compiled_binaries(self):
        for n in self.out:self.assertNotIn(Path(n).suffix.lower(),('.exe','.dll','.obj','.lib','.pdb'))
    def test_explicit_limits(self):
        c=json.loads(self.out['composition02.json'])
        self.assertFalse(c['nativeExecution']);self.assertIn('Receiver04 listener/media attachment still absent',c['ownership'])
if __name__=='__main__':unittest.main(verbosity=2)
