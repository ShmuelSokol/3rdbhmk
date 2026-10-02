"""Checks real composed source; no UE emulation or C++ execution claim."""
from pathlib import Path
import argparse,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parent
P='P/Source/Receiver04Compile/Private/'
OUT={}
class Checks(unittest.TestCase):
    def src(self,n):return OUT[P+n].decode()
    def test_one_actual_pipe_reader(self):
        readers=[n for n,b in OUT.items() if n.startswith('P/Source/') and n.endswith('.cpp') and '::ReadFile(' in b.decode()]
        self.assertEqual([P+'runtime_candidate05/PrivateBootstrap.cpp'],readers)
        self.assertNotIn('GetStdHandle',self.src('Native/receiver04/Bootstrap.cpp'))
    def test_private_capability_mint(self):
        s=self.src('runtime_adoption01/ParsedAdmission.h')
        self.assertLess(s.index('FParsedAdmission(const Receiver03::Bootstrap&'),s.index('public:'))
        self.assertIn('friend bool Readiness01::Admit',s)
        self.assertIn('Current.Get()==&Lease.Get()',s)
        self.assertIn('const std::string ProcessGeneration',s)
        self.assertIn('friend class MikdashOnline::Receiver04::Bootstrap;',s)
    def test_mint_after_real_settings_validation(self):
        s=self.src('runtime_readiness01/ReadyOutput.cpp')
        self.assertLess(s.index('Settings05::AdmitPrivateV2'),s.index('new Adoption01::FParsedAdmission'))
        self.assertLess(s.index('if(!ExactLease.IsValid())return false'),s.index('new Adoption01::FParsedAdmission'))
        self.assertIn('return MoveTemp(Parsed)',s)
        self.assertIn('Out,D.generation,ExactLease.ToSharedRef()',s)
    def test_adoption_before_private_ack(self):
        s=self.src('runtime_candidate05/PrivateBootstrap.cpp')
        self.assertLess(s.index('FHost::AdmitStopped'),s.index('FHost::AdoptParsed'))
        self.assertLess(s.index('FHost::AdoptParsed'),s.index('Readiness01::SignalStopped'))
        self.assertIn('!Fresh(Provisioning->Deadline)||!Settings05::LeaseLive()',s)
    def test_registry_uses_actual_owned_receiver(self):
        s=self.src('runtime_candidate04/RegistryHost.cpp')
        self.assertIn('Host->AdoptionUsed=true',s);self.assertIn('const auto Owned=Host->Owned',s)
        self.assertIn('Owned->AdoptParsed(Parsed,Controller.Get(),Host->Gate)',s)
        s=self.src('runtime_candidate04/ServicedStoppedOwner.cpp')
        self.assertIn('Receiver->AdoptStopped(Parsed,C,S,Gate)',s)
        self.assertIn('AdoptionEstablished&&!Receiver->IsAdoptedStopped()',s)
    def test_real_authority_and_receiver_no_activation(self):
        s=self.src('Native/receiver04/Bootstrap.cpp')
        self.assertIn('MakeShared<Authority>(Parsed->Config()',s)
        self.assertIn('MakeUnique<Receiver>(*RetainedService)',s)
        for forbidden in ('Server->Start(', 'Server->Tick(', 'StartStreaming(', 'ConfigureRemote(', 'ParseBootstrap(', '::ReadFile('):self.assertNotIn(forbidden,s)
        self.assertIn('bool IsReady()const{return false;}',self.src('Native/receiver04/Bootstrap.h'))
    def test_settings_callback_then_fresh_ownership(self):
        s=self.src('Native/receiver04/Bootstrap.cpp')
        self.assertIn('Settings05::MakeOwnedSettingsCallback(Parsed->Identity(),C)',s)
        self.assertIn('if(!Settings()||!StillOwned())return false;',s)
        for token in ('ExpectedPawn->GetMovementComponent()==ExpectedMovement.Get()','ExpectedPawn->GetWorld()==ExpectedWorld.Get()','BootstrapTargetsValid(ExpectedController,ExpectedPawn,ExpectedInput','Lifecycle.Commit(Receiver03::QpcSeconds())'):
            self.assertIn(token,s)
        self.assertNotIn('return true;};',s)
    def test_retained_authority_reentry_and_cleanup(self):
        s=self.src('Native/receiver04/Bootstrap.cpp')
        self.assertIn('const auto RetainedService=Service',s)
        self.assertIn('if(!Bound||Stopping){RetainedService->Abort();Shutdown();return false;}',s)
        tail=s.split('bool Bootstrap::Shutdown()',1)[1]
        self.assertLess(tail.index('Service->Abort()'),tail.index('if(Busy)return false'))
        self.assertLess(tail.index('if(!Closed)return false'),tail.index('Admission.Reset()'))
    def test_peerless_maintenance(self):
        s=self.src('Native/receiver04/Bootstrap.cpp')
        self.assertIn('Retained->Maintain()',s);self.assertIn('AddRaw(this,&Bootstrap::Poll)',s)
        self.assertIn('Pawn->GetMovementComponent()==Movement.Get()',s)
    def test_pure_production_hook_and_fixture(self):
        h=self.src('runtime_adoption01/AdoptionState.h')
        for s in ('N<Last','N>=Until','Deadline>OwnerExpiry','State!=Phase::Empty','State!=Phase::Adopting'):
            self.assertIn(s,h)
        cpp=self.src('Native/receiver04/Bootstrap.cpp')
        for s in ('Lifecycle.Begin(', 'Lifecycle.Check(', 'Lifecycle.Commit(', 'Lifecycle.Abort()'):self.assertIn(s,cpp)
        self.assertIn('runtime_adoption01/AdoptionState.h',OUT['fixtures/AdoptionStateTests.cpp'].decode())
    def test_no_start_api_or_caller_settings_provider(self):
        h=self.src('Native/receiver04/Bootstrap.h')
        self.assertNotIn('bool Start(',h);self.assertNotIn('TFunction<bool',h)
    def test_guard_and_real_uht_sources_retained(self):
        s=OUT['Build-Reviewed.ps1'].decode()
        for x in ('9GB','4GB','2GB','StopWithinFiveSeconds'):self.assertIn(x,s)
        self.assertIn('OnlineController.generated.h',self.src('Native/receiver04/OnlineController.h'))
        self.assertIn('OnlineMovement.generated.h',self.src('Native/receiver04/OnlineMovement.h'))
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--base',type=Path);g.add_argument('--stage',type=Path);a=p.parse_args()
    if a.base:
        sys.path.insert(0,str(ROOT));import compose
        OUT=compose.build(a.base)
    else:
        m=json.loads((a.stage/'allowlist.json').read_bytes());OUT={}
        for e in m['entries']:
            b=(a.stage/e['path']).read_bytes()
            if hashlib.sha256(b).hexdigest()!=e['sha256']:raise ValueError('Stage changed')
            OUT[e['path']]=b
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    raise SystemExit(0 if result.wasSuccessful() else 1)
