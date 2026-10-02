"""Actual-source structural contracts only. No UE compile/runtime claim."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parent
C=(R/'RegistryHost.cpp').read_text()
H=(R/'RegistryHost.h').read_text()
M=(R/'RegistryHostModule.cpp').read_text()

class Contracts(unittest.TestCase):
    def test_single_process_owner(self):
        for s in ('TUniquePtr<FHost> Host;', 'if(EverStarted) return false;', 'EverStarted=true;', 'Host->AdmissionUsed=true;'):
            self.assertIn(s,C)
        self.assertNotIn('EverStarted=false;',C.split('bool FRegistryHost::Startup()')[1])
    def test_module_hooks(self):
        self.assertIn('StartupModule() override',M)
        self.assertIn('ShutdownModule() override',M)
        self.assertIn('SupportsDynamicReloading() override { return false; }',M)
    def test_no_connection_or_pointer_api(self):
        for s in ('StartStreaming(', 'SetConnectionURL(', 'Receiver->Start(', 'Bootstrap::Start('): self.assertNotIn(s,C+H+M)
        self.assertNotIn('IPixelStreaming2Streamer',H)
    def test_auto_start_read_only(self):
        for s in ('PixelStreaming2.InitializeDefaultStreamer','PixelStreaming2.AutoStartStream','Default->GetInt()==0&&Auto->GetInt()==0'):self.assertIn(s,C)
        self.assertNotIn('->Set(',C)
    def test_foreign_registry_refused(self):
        for s in ('Ids.Num()==0','Ids.Num()==1&&Ids[0]==Id','Id!=Host->Module->GetDefaultStreamerID()'):self.assertIn(s,C)
        self.assertNotIn('DeleteStreamer(',C)
    def test_actual_receiver_types_required(self):
        for s in ('Cast<AReceiver04Controller>', 'Cast<UReceiver04WalkerMovement>', 'Cast<UReceiver04DoveMovement>', 'C->PlayerInput', 'P->GetController()!=C'):self.assertIn(s,C)
    def test_gate_before_ready(self):
        body=C.split('bool FRegistryHost::AdmitStopped')[1].split('bool FRegistryHost::Shutdown')[0]
        self.assertLess(body.index('FOnlineInputGate::Install'),body.index('Host->Phase=State::StoppedReady'))
        self.assertIn('GetInputHandler().Pin()==Host->Gate',C)
    def test_real_owner_and_private_receiver(self):
        self.assertIn('using FOwner=FServicedStoppedOwner;',C)
        self.assertIn('MakeShared<Receiver04::Bootstrap>()',C)
    def test_bounded_idle(self):
        self.assertIn('Host->AdmissionEnd=N+5',C)
        self.assertIn('N>=Host->AdmissionEnd',C)
    def test_lifecycle_delegates(self):
        for s in ('OnBeginFrame','OnEnginePreExit','OnWorldCleanup'):
            self.assertIn(s+'.Add',C);self.assertIn(s+'.Remove',C)
    def test_quarantine_retention(self):
        body=C.split('bool FRegistryHost::Shutdown()')[1]
        self.assertLess(body.index('Host->Closing=true'),body.index('Host->Owned->Shutdown()'))
        self.assertLess(body.index('if(!Clean)'),body.index('Host->Owned.Reset()'))
        self.assertIn('if(Host->Phase==State::Quarantined) return false;',body)
    def test_late_module_guard(self):
        body=C.split('bool FRegistryHost::Shutdown()')[1]
        self.assertLess(body.index('LoadedModule()!=Host->Module'),body.index('Host->Owned->Shutdown()'))
    def test_child_hierarchy_in_actual_owner(self):
        owner=(R/'ServicedStoppedOwner.cpp').read_text()
        hierarchy=(R/'WindowHierarchy.h').read_text()
        self.assertIn('GetTopLevelWindows()',owner)
        self.assertIn('IsSoleChildlessWindow(Windows,Window.Pin())',owner)
        self.assertIn('Expected->GetChildWindows().Num()==0',hierarchy)
        self.assertNotIn('IsVisible',hierarchy)
        self.assertIn('Self->ScopeAndTime()&&Self->Lease.Prepare',owner)
        self.assertIn('if(ScopeAndTime()) Result=Lease.BorrowStopped',owner)
    def test_real_hierarchy_cases_staged(self):
        tests=(R/'WindowHierarchyTests.cpp').read_text()
        for text in ('Root->AddChildWindow(Child)','Child->AddChildWindow(Grandchild)',
                     'Child->SetVisibility(EVisibility::Hidden)','Roots.Add(Grandchild)'):
            self.assertIn(text,tests)
        self.assertNotIn('FSlateApplication::Get().AddWindow',tests)

if __name__=='__main__':unittest.main()
