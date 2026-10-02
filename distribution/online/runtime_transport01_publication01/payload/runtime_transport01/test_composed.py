"""Actual composed source contracts, not a UE compiler substitute."""
import argparse,hashlib,json,unittest
from pathlib import Path
ROOT=None
P='P/Source/Receiver04Compile/Private/'
class ComposedTests(unittest.TestCase):
    def read(self,n):return (ROOT/n).read_text(encoding='utf-8')
    def test_module_dependency_exports_real_plugin_api(self):
        self.assertIn('"PixelStreaming2RTC"',self.read('P/Source/Receiver04Compile/Receiver04Compile.Build.cs'))
        self.assertIn('#include "MikdashOwnedRtc.h"',self.read(P+'Native/receiver04/Bootstrap.cpp'))
    def test_real_admission_lease_and_exact_authenticated_wire(self):
        s=self.read(P+'Native/receiver04/Bootstrap.cpp')
        for v in ['Admission->LiveLease()','P.process_generation!=Admission->Generation()',
                  'MikdashAttachOwnedRtc(Streamer,I','P.y>Admission->Deadline()',
                  'Owned->StartAuthenticatedMedia(P.owner,int32(P.x))','MakeShared<FActualRtcLease>']:
            self.assertIn(v,s)
        wire=self.read(P+'Native/receiver03/Wire.cpp')
        self.assertIn('TEXT("port"),TEXT("ticket"),TEXT("until")',wire)
    def test_flight_consumer_and_possession_binding_survive_composition(self):
        controller=self.read(P+'Native/receiver04/OnlineController.cpp')
        self.assertIn('FlightService->ConsumeFlight(*this)',controller)
        boot=self.read(P+'Native/receiver04/Bootstrap.cpp')
        self.assertIn('Commit',boot)
        self.assertIn('IsOwnedRouteLive()',boot)
        self.assertIn('Flight.Take(',self.read(P+'Native/receiver04/Authority.cpp'))
    def test_real_host_selection_not_affirmative_lease_provider(self):
        host=self.read('runtime_transport01/managed_host.py')
        for s in ['OwnedAllocator(spec,premise)','self.processes=TransportProcesses(',
                  'FlightStreams(self.processes)','FlightAuthority(self.core,streams,self.processes)',
                  'self.authority.lock=self.lock']:
            self.assertIn(s,host)
        application=self.read('runtime_transport01/application.py')
        self.assertIn("holder['server'].gateway.process_revoked(owner)",application)
        self.assertNotIn('lambda:True',application)
    def test_browser_entry_and_mount_failure_cleanup(self):
        entry=self.read('runtime_transport01/entry.mjs');main=self.read('browser/main.mjs')
        self.assertLess(entry.index("base+'/control'"),entry.index('mounted=mountWalkthrough'))
        self.assertIn('socket?.close()',entry)
        self.assertIn("catch { stop(); throw Error('Stream mount unavailable'); }",main)
        self.assertIn('finally { stream.disconnect(); }',main)
    def test_unchanged_resource_guards(self):
        s=self.read('Build-Reviewed.ps1')
        for v in ['-lt 9GB','-lt 2GB','[uint64]4GB','Get-CompileDeadlineDecision','StopWithinFiveSeconds']:
            self.assertIn(v,s)
    def test_no_automatic_native_or_listener_activation(self):
        app=self.read('runtime_transport01/application.py')
        self.assertNotIn('\n    host.prepare()',app)
        self.assertNotIn('\n    server.serve()',app)
        self.assertIn("self.listener.bind(('127.0.0.1',self.port))",self.read('runtime_transport01/server.py'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);a=p.parse_args();ROOT=a.root
    unittest.main(argv=['composed'],verbosity=2)
